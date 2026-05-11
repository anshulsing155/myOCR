"""
Streamlit UI for the OCR Document Intelligence Pipeline.

Run:
    streamlit run app.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

# ── make project-root imports work regardless of CWD ────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

import config  # noqa: E402  (creates input/output dirs)
from classification.doc_classifier import classify as classify_doc
from layout.layout_detector import detect_layout
from ocr.availability import local_ocr_status
from ocr.hybrid_runner import run_ocr
from parsers.aadhaar_parser import AadhaarParser
from parsers.bank_statement.bank_identifier import identify_bank
from parsers.bank_statement.bank_parser import (
    parse as parse_bank,
)
from parsers.driving_license_parser import DrivingLicenseParser
from parsers.eshram_parser import EshramParser
from parsers.generic_parser import GenericParser
from parsers.itr_parser import ItrParser
from parsers.pan_parser import PanParser
from parsers.salary_slip_parser import SalarySlipParser
from postprocessing.cleaner import build_table_rows, clean_text
from postprocessing.language_processor import (
    LANG_NAMES,
    get_translated_ocr,
    process_multilingual_ocr,
    summarise_languages,
)
from postprocessing.multipage import merge_multipage_tables
from postprocessing.spatial_table import reconstruct_table, split_page_ocr
from table.table_extractor import extract_table
from utils.helpers import (
    crop_region,
    draw_layout_debug,
    save_json,
    timestamp_filename,
)
from utils.pdf_to_image import pdf_to_images

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OCR Pipeline",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── custom CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* top header bar */
    .ocr-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.8rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .ocr-header h1 { color: #e94560; margin: 0; font-size: 1.9rem; }
    .ocr-header p  { color: #a8b2d8; margin: 0; font-size: 0.95rem; }

    /* metric cards */
    .metric-row { display: flex; gap: 0.75rem; margin-bottom: 1rem; flex-wrap: wrap; }
    .metric-card {
        background: #1e1e2e;
        border: 1px solid #2d2d44;
        border-radius: 10px;
        padding: 0.75rem 1.2rem;
        min-width: 110px;
        text-align: center;
    }
    .metric-card .val { font-size: 1.6rem; font-weight: 700; color: #e94560; }
    .metric-card .lbl { font-size: 0.72rem; color: #888; text-transform: uppercase; letter-spacing: .05em; }

    /* block type badge */
    .badge {
        display: inline-block;
        padding: 2px 9px;
        border-radius: 99px;
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: .05em;
    }
    .badge-text   { background:#1c3a1c; color:#5fdd5f; }
    .badge-title  { background:#3a1c1c; color:#dd5f5f; }
    .badge-table  { background:#1c2a3a; color:#5f9fdd; }
    .badge-list   { background:#2a1c3a; color:#af5fdd; }
    .badge-figure { background:#3a2a1c; color:#dda05f; }

    /* confidence bar */
    .conf-bar-wrap { height: 6px; background: #2d2d44; border-radius: 3px; margin-top: 4px; }
    .conf-bar      { height: 6px; border-radius: 3px; background: #e94560; }

    /* section divider */
    .section-sep { border-top: 1px solid #2d2d44; margin: 1rem 0; }

    /* document intelligence banner */
    .doc-intel-banner {
        background: #0f1e35;
        border: 1px solid #1a3a5c;
        border-radius: 10px;
        padding: 1rem 1.4rem;
        margin-bottom: 1.2rem;
        display: flex;
        align-items: center;
        gap: 1.2rem;
        flex-wrap: wrap;
    }
    .doc-intel-banner .doc-type {
        font-size: 1.15rem;
        font-weight: 700;
        color: #5fbfff;
        text-transform: uppercase;
        letter-spacing: .06em;
    }
    .doc-intel-banner .bank-tag {
        background: #1a3a1a;
        color: #5fdd8f;
        border-radius: 99px;
        padding: 3px 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .doc-intel-banner .conf-label {
        color: #888;
        font-size: 0.8rem;
    }
    .meta-table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; }
    .meta-table td { padding: 4px 8px; font-size: 0.85rem; color: #ccc; }
    .meta-table td:first-child { color: #888; font-size: 0.78rem; text-transform: uppercase; width: 160px; }

    /* Streamlit overrides */
    [data-testid="stSidebar"] { background: #0d0d1a; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── helpers ───────────────────────────────────────────────────────────────────

def bgr_to_pil(img: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def load_uploaded_file(uploaded_file) -> tuple[list[np.ndarray], str, str | None]:
    """
    Save upload to a temp file.
    Returns (images, file_type, pdf_path_or_None).

    file_type: "pdf_digital" | "pdf_scanned" | "pdf_mixed" | "image"
    pdf_path: kept on disk for pdfplumber; caller must delete it.
    """
    from utils.pdf_extractor import classify_pdf

    suffix = Path(uploaded_file.name).suffix.lower()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getbuffer())
    tmp.close()
    tmp_path = tmp.name

    if suffix == ".pdf":
        pdf_kind = classify_pdf(tmp_path)
        file_type = f"pdf_{pdf_kind}"
        images = pdf_to_images(tmp_path)      # always render images (for preview)
        return images, file_type, tmp_path    # keep tmp for pdfplumber
    else:
        img = cv2.imread(tmp_path)
        images = [img] if img is not None else []
        os.unlink(tmp_path)
        return images, "image", None


def _avg_conf(results: list[dict]) -> float:
    return sum(r["confidence"] for r in results) / len(results) if results else 0.0


def _is_fallback_layout(layout, image: np.ndarray) -> bool:
    """True when LayoutParser is unavailable and returned a single full-page block."""
    blocks = list(layout)
    if len(blocks) != 1 or blocks[0].type != "Text":
        return False
    h, w = image.shape[:2]
    x1, y1, x2, y2 = blocks[0].block.coordinates
    return x2 >= w * 0.9 and y2 >= h * 0.9


def process_page(
    image: np.ndarray,
    page_num: int,
    mode: str,
    show_debug: bool,
    bank_fast_mode: bool = False,
) -> dict:
    layout = detect_layout(image)
    debug_img = draw_layout_debug(image, layout) if show_debug else None

    page_result = {
        "page": page_num,
        "text_blocks": [],
        "tables": [],
        "_debug_img": debug_img,
        "_original_img": image,
    }

    if _is_fallback_layout(layout, image):
        _process_fullpage(image, mode, page_result, bank_fast_mode=bank_fast_mode)
    else:
        for block in layout:
            _process_block(image, block, mode, page_result)

    return page_result


def _process_block(image: np.ndarray, block, mode: str, page_result: dict) -> None:
    region = crop_region(image, block.block)   # always pass original color to OCR
    if block.type == "Table":
        raw_rows = extract_table(region)
        rows = build_table_rows(raw_rows)
        page_result["tables"].append({
            "bbox": list(block.block.coordinates),
            "rows": rows,
        })
    else:
        from ocr.paddle_engine import run_paddle_multilingual
        ocr_results, _lang = run_paddle_multilingual(region)
        if not ocr_results:
            ocr_results = run_ocr(region, mode=mode)
        ocr_results = process_multilingual_ocr(ocr_results)
        translated = get_translated_ocr(ocr_results)
        text = " ".join(clean_text(r["text"]) for r in translated)
        if text:
            blk: dict = {
                "type": block.type,
                "bbox": list(block.block.coordinates),
                "text": text,
                "confidence": round(_avg_conf(ocr_results), 3),
            }
            orig_items = [r for r in ocr_results if r.get("translated_text")]
            if orig_items:
                blk["original_text"] = " ".join(
                    clean_text(r.get("text", "")) for r in ocr_results
                )
                blk["detected_lang"] = next(
                    (r["detected_lang"] for r in ocr_results if r.get("detected_lang")), "en"
                )
                blk["lang_name"] = LANG_NAMES.get(blk["detected_lang"], "")
            page_result["text_blocks"].append(blk)
        # Always accumulate OCR results so classification works on LayoutParser pages
        page_result.setdefault("_ocr_results", []).extend(translated)
        # Merge lang summary
        _blk_lang = summarise_languages(ocr_results)
        existing = page_result.get("_lang_summary")
        if not existing:
            page_result["_lang_summary"] = _blk_lang
        elif _blk_lang.get("multilingual"):
            existing["multilingual"] = True
            for lang in _blk_lang.get("detected_languages", []):
                if lang not in existing.get("detected_languages", []):
                    existing.setdefault("detected_languages", []).append(lang)
            if _blk_lang.get("primary_language", "en") != "en":
                existing["primary_language"] = _blk_lang["primary_language"]


_BANK_STATEMENT_LANG_SUMMARY: dict = {
    "detected_languages": ["en"],
    "primary_language": "en",
    "multilingual": False,
    "translation_applied": False,
}


def _process_fullpage(
    image: np.ndarray,
    mode: str,
    page_result: dict,
    bank_fast_mode: bool = False,
) -> None:
    """
    Full-page OCR path (no LayoutParser).

    bank_fast_mode=True — bank statement: skip multilingual OCR and language
    detection; force spatial table reconstruction on every page including
    continuation pages that have no repeated column-header row.

    Image quality gate: if the image is already sharp and clean (good
    resolution scan or rendered PDF page), preprocessing is skipped to avoid
    adding artefacts.  Poor-quality images (blurry, noisy scans) are
    denoised + contrast-enhanced before OCR.
    """
    from utils.image_quality import maybe_preprocess
    image, _qi = maybe_preprocess(image)
    if _qi["quality"] == "poor":
        page_result["_image_quality"] = _qi

    h, w = image.shape[:2]

    if bank_fast_mode:
        from ocr.paddle_engine import run_paddle
        ocr_results = run_paddle(image)
        if not ocr_results:
            try:
                from ocr.tesseract_engine import run_tesseract
                ocr_results = run_tesseract(image)
            except Exception:
                pass
        if not ocr_results:
            return
        page_result["_ocr_results"] = ocr_results
        page_result["_lang_summary"] = _BANK_STATEMENT_LANG_SUMMARY
        # Force full-page table reconstruction — no column header required
        _, table_items = split_page_ocr(ocr_results, force_table=True)
        if table_items:
            raw_rows = reconstruct_table(table_items)
            if raw_rows:
                page_result["tables"].append(
                    {"bbox": [0, 0, w, h], "rows": build_table_rows(raw_rows)})
        return

    # ── Full multilingual path (ID docs, non-bank) ────────────────────────────
    from ocr.paddle_engine import run_paddle_multilingual
    ocr_results, _detected_lang = run_paddle_multilingual(image)

    if not ocr_results:
        try:
            from ocr.tesseract_engine import run_tesseract
            ocr_results = run_tesseract(image)
        except Exception:
            pass

    if not ocr_results:
        return

    # ── Language detection + translation ─────────────────────────────────────
    ocr_results = process_multilingual_ocr(ocr_results)
    page_result["_lang_summary"] = summarise_languages(ocr_results)

    # For document parsing: use translated text so classifiers/parsers get English
    translated_ocr = get_translated_ocr(ocr_results)

    # Store enriched OCR for downstream classification (translated version)
    page_result["_ocr_results"] = translated_ocr
    page_result["_ocr_results_original"] = ocr_results  # keep originals for display

    # Split: header items (above table) vs table items (from column-header row down)
    header_items, table_items = split_page_ocr(translated_ocr)

    # ── header / non-table text ──
    if header_items:
        header_text = " ".join(clean_text(r["text"]) for r in header_items)
        avg = _avg_conf(header_items)
        if header_text.strip():
            block: dict = {
                "type": "Text",
                "bbox": [0, 0, w, h],
                "text": header_text,
                "confidence": round(avg, 3),
            }
            # Surface original-language text if translation occurred
            orig_items = [r for r in page_result["_ocr_results_original"]
                          if r.get("translated_text")]
            if orig_items:
                orig_text = " ".join(
                    clean_text(r.get("text", "")) for r in
                    page_result["_ocr_results_original"]
                    if r in header_items or r.get("translated_text")
                )
                block["original_text"] = orig_text
                lang_summary = page_result["_lang_summary"]
                block["detected_lang"] = lang_summary.get("primary_language", "en")
                block["lang_name"] = LANG_NAMES.get(block["detected_lang"], "")
            page_result["text_blocks"].append(block)

    # ── table ──
    if table_items:
        raw_rows = reconstruct_table(table_items)
        if raw_rows:
            rows = build_table_rows(raw_rows)
            page_result["tables"].append({"bbox": [0, 0, w, h], "rows": rows})
    elif not header_items:
        # Entire page is just text (no table found at all)
        all_text = " ".join(clean_text(r["text"]) for r in translated_ocr)
        if all_text.strip():
            block = {
                "type": "Text",
                "bbox": [0, 0, w, h],
                "text": all_text,
                "confidence": round(_avg_conf(translated_ocr), 3),
            }
            lang_summary = page_result["_lang_summary"]
            if lang_summary.get("translation_applied"):
                orig_all = " ".join(
                    clean_text(r.get("text", "")) for r in ocr_results
                )
                block["original_text"] = orig_all
                block["detected_lang"] = lang_summary.get("primary_language", "en")
                block["lang_name"] = LANG_NAMES.get(block["detected_lang"], "")
            page_result["text_blocks"].append(block)


def _collect_digital_bank_rows(pages: list[dict]) -> list[dict]:
    """
    Collect normalised transaction rows from digital-extracted bank pages.

    extract_digital_page() already calls normalise_digital_bank_rows() on
    bank-like tables, so their rows have schema keys ("date", "balance", …).
    For any remaining col_N tables we normalise here.
    Skips non-transaction tables (e.g. Axis Bank charge-statement pages).
    """
    from utils.pdf_extractor import is_bank_transaction_table, normalise_digital_bank_rows

    _BANK_AMOUNT_KEYS = {"withdrawal", "deposit", "debit", "credit", "balance"}

    all_rows: list[dict] = []
    for p in pages:
        if p.get("_extraction") != "digital":
            continue
        for tbl in p.get("tables", []):
            raw_rows = tbl.get("rows", [])
            if not raw_rows:
                continue
            first_keys = set(raw_rows[0].keys())
            # Already-normalised table: keys are schema names
            if "date" in first_keys and first_keys & _BANK_AMOUNT_KEYS:
                all_rows.extend(raw_rows)
            # Still col_N: normalise now (shouldn't usually happen post-fix)
            elif is_bank_transaction_table(raw_rows):
                all_rows.extend(normalise_digital_bank_rows(raw_rows))
    return all_rows


def _parse_for_type(
    ocr: list[dict],
    doc_type: str,
    digital_rows: list[dict] | None = None,
) -> tuple[dict, str | None, str | None]:
    """Run the right parser for doc_type. Returns (extracted, bank_name, bank_code)."""
    bank_name = bank_code = None
    try:
        if doc_type == "bank_statement":
            bank_id = identify_bank(ocr)
            if bank_id:
                bank_name, bank_code = bank_id.name, bank_id.code
            extracted = parse_bank(ocr, bank_code=bank_code or "default",
                                   digital_rows=digital_rows or None)
        elif doc_type == "pan_card":
            extracted = PanParser().parse(ocr)
        elif doc_type == "aadhaar":
            extracted = AadhaarParser().parse(ocr)
        elif doc_type == "eshram":
            extracted = EshramParser().parse(ocr)
        elif doc_type == "itr":
            extracted = ItrParser().parse(ocr)
        elif doc_type == "salary_slip":
            extracted = SalarySlipParser().parse(ocr)
        elif doc_type == "driving_license":
            extracted = DrivingLicenseParser().parse(ocr)
        elif doc_type == "voter_id":
            from parsers.voter_id_parser import VoterIdParser
            extracted = VoterIdParser().parse(ocr)
        elif doc_type == "passport":
            from parsers.passport_parser import PassportParser
            extracted = PassportParser().parse(ocr)
        elif doc_type == "vehicle_rc":
            from parsers.vehicle_rc_parser import VehicleRcParser
            extracted = VehicleRcParser().parse(ocr)
        elif doc_type == "birth_certificate":
            from parsers.birth_certificate_parser import BirthCertificateParser
            extracted = BirthCertificateParser().parse(ocr)
        elif doc_type == "marriage_certificate":
            from parsers.marriage_certificate_parser import MarriageCertificateParser
            extracted = MarriageCertificateParser().parse(ocr)
        elif doc_type == "caste_certificate":
            from parsers.caste_certificate_parser import CasteCertificateParser
            extracted = CasteCertificateParser().parse(ocr)
        elif doc_type == "income_certificate":
            from parsers.income_certificate_parser import IncomeCertificateParser
            extracted = IncomeCertificateParser().parse(ocr)
        elif doc_type == "domicile_certificate":
            from parsers.domicile_certificate_parser import DomicileCertificateParser
            extracted = DomicileCertificateParser().parse(ocr)
        elif doc_type == "ration_card":
            from parsers.ration_card_parser import RationCardParser
            extracted = RationCardParser().parse(ocr)
        elif doc_type == "gst_certificate":
            from parsers.gst_certificate_parser import GstCertificateParser
            extracted = GstCertificateParser().parse(ocr)
        elif doc_type == "marksheet":
            from parsers.marksheet_parser import MarksheetParser
            extracted = MarksheetParser().parse(ocr)
        elif doc_type == "degree_certificate":
            from parsers.degree_certificate_parser import DegreeCertificateParser
            extracted = DegreeCertificateParser().parse(ocr)
        elif doc_type == "ayushman_card":
            from parsers.ayushman_card_parser import AyushmanCardParser
            extracted = AyushmanCardParser().parse(ocr)
        elif doc_type == "ppo":
            from parsers.ppo_parser import PpoParser
            extracted = PpoParser().parse(ocr)
        elif doc_type == "sale_deed":
            from parsers.realestate.sale_deed_parser import SaleDeedParser
            extracted = SaleDeedParser().parse(ocr)
        elif doc_type == "agreement_to_sale":
            from parsers.realestate.agreement_to_sale_parser import AgreementToSaleParser
            extracted = AgreementToSaleParser().parse(ocr)
        elif doc_type == "encumbrance_certificate":
            from parsers.realestate.encumbrance_certificate_parser import (
                EncumbranceCertificateParser,
            )
            extracted = EncumbranceCertificateParser().parse(ocr)
        elif doc_type == "property_tax_receipt":
            from parsers.realestate.property_tax_parser import PropertyTaxParser
            extracted = PropertyTaxParser().parse(ocr)
        elif doc_type == "khata":
            from parsers.realestate.khata_parser import KhataParser
            extracted = KhataParser().parse(ocr)
        elif doc_type == "mutation_certificate":
            from parsers.realestate.mutation_certificate_parser import MutationCertificateParser
            extracted = MutationCertificateParser().parse(ocr)
        elif doc_type == "land_record":
            from parsers.realestate.land_record_parser import LandRecordParser
            extracted = LandRecordParser().parse(ocr)
        elif doc_type == "rera_certificate":
            from parsers.realestate.rera_certificate_parser import ReraCertificateParser
            extracted = ReraCertificateParser().parse(ocr)
        elif doc_type == "occupancy_certificate":
            from parsers.realestate.occupancy_certificate_parser import OccupancyCertificateParser
            extracted = OccupancyCertificateParser().parse(ocr)
        elif doc_type == "possession_letter":
            from parsers.realestate.possession_letter_parser import PossessionLetterParser
            extracted = PossessionLetterParser().parse(ocr)
        elif doc_type == "power_of_attorney":
            from parsers.realestate.power_of_attorney_parser import PowerOfAttorneyParser
            extracted = PowerOfAttorneyParser().parse(ocr)
        elif doc_type == "lease_deed":
            from parsers.realestate.lease_deed_parser import LeaseDeedParser
            extracted = LeaseDeedParser().parse(ocr)
        elif doc_type == "gift_deed":
            from parsers.realestate.gift_deed_parser import GiftDeedParser
            extracted = GiftDeedParser().parse(ocr)
        elif doc_type == "partition_deed":
            from parsers.realestate.partition_deed_parser import PartitionDeedParser
            extracted = PartitionDeedParser().parse(ocr)
        elif doc_type == "mortgage_deed":
            from parsers.realestate.mortgage_deed_parser import MortgageDeedParser
            extracted = MortgageDeedParser().parse(ocr)
        elif doc_type == "estamp_certificate":
            from parsers.realestate.estamp_certificate_parser import EStampCertificateParser
            extracted = EStampCertificateParser().parse(ocr)
        elif doc_type == "property_valuation":
            from parsers.realestate.property_valuation_parser import PropertyValuationParser
            extracted = PropertyValuationParser().parse(ocr)
        elif doc_type == "home_loan_sanction":
            from parsers.realestate.home_loan_sanction_parser import HomeLoanSanctionParser
            extracted = HomeLoanSanctionParser().parse(ocr)
        elif doc_type == "legal_heir_certificate":
            from parsers.realestate.legal_heir_certificate_parser import LegalHeirCertificateParser
            extracted = LegalHeirCertificateParser().parse(ocr)
        else:
            extracted = GenericParser().parse(ocr, doc_type=doc_type)
    except Exception as exc:
        extracted = GenericParser().parse(ocr, doc_type=doc_type)
        extracted.setdefault("warnings", []).append(
            f"{doc_type} parser failed; returned generic extraction instead: {exc}"
        )
    return extracted, bank_name, bank_code


def run_document_intelligence(pages: list[dict]) -> dict:
    """
    Per-page classification + multi-document grouping.

    When all pages share the same doc type → single document result (backward compat).
    When pages have different doc types → 'documents' list, one entry per distinct type/group.
    Each page also gets its own 'doc_type' and 'extracted' stored back onto it.
    """
    if not pages:
        return {"doc_type": "other", "doc_confidence": 0.0,
                "bank_name": None, "bank_code": None, "extracted": {},
                "languages": {"detected_languages": ["en"], "primary_language": "en",
                              "multilingual": False, "translation_applied": False}}

    # ── Per-page classification ───────────────────────────────────────────────
    for p in pages:
        page_ocr = p.get("_ocr_results", [])
        if page_ocr:
            dc = classify_doc(page_ocr)
            p["_doc_type"]  = dc.type
            p["_doc_conf"]  = dc.confidence
        else:
            p["_doc_type"] = "other"
            p["_doc_conf"] = 0.0

    # ── Propagate bank_statement classification ───────────────────────────────
    # A bank statement spans multiple pages; pages with little text may be
    # misclassified as "other".  If any page is confidently bank_statement,
    # reclassify adjacent "other" pages as bank_statement too.
    bank_conf = max((p["_doc_conf"] for p in pages
                     if p.get("_doc_type") == "bank_statement"), default=0.0)
    if bank_conf >= 0.5:
        for p in pages:
            if p.get("_doc_type") == "other":
                p["_doc_type"] = "bank_statement"
                p["_doc_conf"] = bank_conf * 0.85

    # ── Propagate ID-document type to adjacent low-confidence pages ──────────
    # Aadhaar/PAN/etc. are 2-page front+back scans; the back page often has a
    # garbled UIDAI header that scores near-zero for aadhaar but accidentally
    # matches some other pattern (e.g. garbled "HP12A" → vehicle_rc).
    _ID_DOC_TYPES = {"aadhaar", "pan_card", "voter_id", "passport",
                     "driving_license", "eshram"}
    for i, p in enumerate(pages):
        if p.get("_doc_type") in _ID_DOC_TYPES and p.get("_doc_conf", 0) >= 0.15:
            for j in (i - 1, i + 1):
                if 0 <= j < len(pages):
                    adj = pages[j]
                    if (adj.get("_doc_conf", 0) < 0.15
                            and adj.get("_doc_type") not in _ID_DOC_TYPES):
                        adj["_doc_type"] = p["_doc_type"]
                        adj["_doc_conf"] = round(p["_doc_conf"] * 0.7, 3)

    # ── Aggregate language info ───────────────────────────────────────────────
    all_lang_summaries = [p.get("_lang_summary", {}) for p in pages if p.get("_lang_summary")]
    all_detected = list({lang for s in all_lang_summaries for lang in s.get("detected_languages", [])})
    primary_lang = next((s.get("primary_language") for s in all_lang_summaries
                         if s.get("primary_language") and s["primary_language"] != "en"), "en")
    lang_info = {
        "detected_languages": sorted(all_detected) if all_detected else ["en"],
        "primary_language": primary_lang,
        "multilingual": any(s.get("multilingual") for s in all_lang_summaries),
        "translation_applied": any(s.get("translation_applied") for s in all_lang_summaries),
    }

    # ── Group consecutive pages by doc type ──────────────────────────────────
    # e.g. [pan_card, aadhaar] → two groups; [aadhaar, aadhaar] → one group
    groups: list[dict] = []  # {"doc_type", "pages": [idx,...], "ocr": [...]}
    for p in pages:
        dt = p["_doc_type"]
        if groups and groups[-1]["doc_type"] == dt:
            groups[-1]["pages"].append(p["page"])
            groups[-1]["ocr"].extend(p.get("_ocr_results", []))
        else:
            groups.append({"doc_type": dt, "confidence": p["_doc_conf"],
                           "pages": [p["page"]], "ocr": list(p.get("_ocr_results", []))})

    # ── Single doc type → original simple output ──────────────────────────────
    unique_types = {g["doc_type"] for g in groups}
    if len(unique_types) == 1:
        g = groups[0]  # merge all OCR
        all_ocr = [r for p in pages for r in p.get("_ocr_results", [])]
        # For bank statements: use pre-structured digital tables when available
        digital_rows = _collect_digital_bank_rows(pages) if g["doc_type"] == "bank_statement" else None
        extracted, bank_name, bank_code = _parse_for_type(all_ocr, g["doc_type"],
                                                           digital_rows=digital_rows)
        # Store per-page extracted too
        for p in pages:
            page_ext, _, _ = _parse_for_type(p.get("_ocr_results", []), p["_doc_type"])
            p["_extracted"] = page_ext
        return {
            "doc_type":       g["doc_type"],
            "doc_confidence": g["confidence"],
            "bank_name":      bank_name,
            "bank_code":      bank_code,
            "languages":      lang_info,
            "extracted":      extracted,
        }

    # ── Multi-document PDF → return grouped structure ─────────────────────────
    documents = []
    for g in groups:
        group_pages = [p for p in pages if p.get("page") in g["pages"]]
        digital_rows = _collect_digital_bank_rows(group_pages) if g["doc_type"] == "bank_statement" else None
        extracted, bank_name, bank_code = _parse_for_type(g["ocr"], g["doc_type"],
                                                           digital_rows=digital_rows)
        doc_entry: dict = {
            "doc_type":   g["doc_type"],
            "confidence": round(g["confidence"], 3),
            "pages":      g["pages"],
            "extracted":  {k: v for k, v in extracted.items()
                           if k not in ("raw_text", "doc_type")},
        }
        if bank_name:
            doc_entry["bank_name"] = bank_name
            doc_entry["bank_code"] = bank_code
        documents.append(doc_entry)

    # Cross-reference PAN + Aadhaar fields (name, DOB) when both appear together
    from pipeline.document_pipeline import _crossref_identity_docs
    _crossref_identity_docs(documents)

    # Store per-page extracted
    for p in pages:
        page_ext, _, _ = _parse_for_type(p.get("_ocr_results", []), p["_doc_type"])
        p["_extracted"] = page_ext

    # Primary doc type = highest confidence group
    primary_group = max(groups, key=lambda g: g["confidence"])

    return {
        "doc_type":       "multi_document",
        "doc_confidence": round(primary_group["confidence"], 3),
        "bank_name":      None,
        "bank_code":      None,
        "languages":      lang_info,
        "documents":      documents,
        "extracted":      {},  # see 'documents' for per-type fields
    }


def result_to_json_export(pages: list[dict], doc_intel: dict | None = None) -> dict:
    """Strip internal UI keys before export."""
    clean_pages = []
    for p in pages:
        page_out: dict = {
            "page": p["page"],
            "extraction_method": p.get("_extraction", "ocr"),
            "text_blocks": p["text_blocks"],
            "tables": p["tables"],
        }
        if p.get("_lang_summary"):
            page_out["language"] = p["_lang_summary"]
        if p.get("_doc_type"):
            page_out["doc_type"] = p["_doc_type"]
            page_out["doc_confidence"] = round(p.get("_doc_conf", 0.0), 3)
        if p.get("_extracted"):
            page_out["extracted"] = {
                k: v for k, v in p["_extracted"].items()
                if k not in ("raw_text", "doc_type")
            }
        clean_pages.append(page_out)

    out: dict = {"pages": clean_pages}
    if doc_intel:
        is_multi = doc_intel.get("doc_type") == "multi_document"
        intel_out: dict = {
            k: v for k, v in doc_intel.items()
            if k not in ("extracted",)
        }
        if not is_multi:
            intel_out["extracted"] = {
                k: v for k, v in doc_intel.get("extracted", {}).items()
                if k != "raw_text"
            }
        out["document_intelligence"] = intel_out
    return out


# ── sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Pipeline Settings")
    st.divider()

    ocr_mode = st.selectbox(
        "OCR Engine Mode",
        options=["auto", "complex", "tesseract", "merge"],
        index=0,
        help=(
            "**auto** — Paddle first; falls back to Tesseract if confidence < 0.7\n\n"
            "**complex** — PaddleOCR only (best for dense / rotated text)\n\n"
            "**tesseract** — Tesseract only (faster, lower accuracy)\n\n"
            "**merge** — run both, keep higher-confidence result"
        ),
    )

    show_debug = st.toggle("Show layout detection overlay", value=False)

    st.divider()
    st.markdown("### 🗂️ Output")
    save_to_disk = st.toggle("Save JSON to outputs/", value=True)

    st.divider()
    st.markdown("### 🤖 AI Engine")
    _ai_engine = st.radio(
        "Select AI engine",
        options=["None (local OCR)", "Gemini", "Grok (xAI)"],
        index=0,
        help="Choose an AI Vision model to extract bank statement data",
    )

    ai_api_key  = ""
    ai_only     = False
    gemini_enabled = False
    gemini_api_key = ""
    gemini_only    = False

    if _ai_engine == "Gemini":
        gemini_enabled = True
        _default = os.environ.get("GEMINI_API_KEY", "")
        gemini_api_key = st.text_input(
            "Gemini API Key", value=_default, type="password", placeholder="AIza..."
        )
        ai_api_key = gemini_api_key
        ai_only = st.toggle(
            "Gemini only (skip local OCR)", value=False,
            help="Skip PaddleOCR/Tesseract — send pages straight to Gemini",
        )
        gemini_only = ai_only

    elif _ai_engine == "Grok (xAI)":
        _default = os.environ.get("GROK_API_KEY", "")
        ai_api_key = st.text_input(
            "Grok API Key", value=_default, type="password", placeholder="xai-..."
        )
        ai_only = st.toggle(
            "Grok only (skip local OCR)", value=False,
            help="Skip PaddleOCR/Tesseract — send pages straight to Grok",
        )

    st.divider()
    st.markdown(
        "<small style='color:#555'>PaddleOCR · Tesseract · OpenCV · LayoutParser · Gemini · Grok</small>",
        unsafe_allow_html=True,
    )

# ── main header ───────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="ocr-header">
        <div>
            <h1>🔍 OCR Document Intelligence</h1>
            <p>Upload a PDF or image → extract structured text &amp; tables → download JSON</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── file upload ───────────────────────────────────────────────────────────────

uploaded_file = st.file_uploader(
    "Drop a PDF or image here",
    type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"],
    help="Supported: PDF, PNG, JPG, JPEG, TIFF, BMP",
)

# reset state when a new file is uploaded
if "last_filename" not in st.session_state:
    st.session_state.last_filename = None

if uploaded_file and uploaded_file.name != st.session_state.last_filename:
    # Clean up previous temp PDF if any
    _old_pdf = st.session_state.get("pdf_path")
    if _old_pdf:
        try:
            os.unlink(_old_pdf)
        except Exception:
            pass
    st.session_state.pop("pages", None)
    st.session_state.pop("raw_images", None)
    st.session_state.pop("file_type", None)
    st.session_state.pop("pdf_path", None)
    st.session_state.last_filename = uploaded_file.name

# ── preview & run button ──────────────────────────────────────────────────────

if uploaded_file:
    # load images (cached in session state so we don't re-decode on every rerun)
    if "raw_images" not in st.session_state:
        with st.spinner("Loading file…"):
            imgs, ftype, pdf_path = load_uploaded_file(uploaded_file)
            st.session_state.raw_images = imgs
            st.session_state.file_type  = ftype
            st.session_state.pdf_path   = pdf_path

    raw_images: list[np.ndarray] = st.session_state.raw_images
    file_type:  str               = st.session_state.get("file_type", "image")
    pdf_path:   str | None        = st.session_state.get("pdf_path")
    n_pages = len(raw_images)
    _ocr_status = local_ocr_status()
    _local_ocr_ready = _ocr_status["paddle"] or _ocr_status["tesseract"]

    col_info, col_btn = st.columns([3, 1])
    with col_info:
        _ftype_label = {
            "pdf_digital": "Digital PDF (direct text)",
            "pdf_scanned": "Scanned PDF (OCR required)",
            "pdf_mixed":   "Mixed PDF (digital + scanned pages)",
            "image":       "Image",
        }.get(file_type, file_type)
        _ftype_color = "#5fdd8f" if "digital" in file_type else "#f0c060" if "mixed" in file_type else "#aaa"
        st.markdown(
            f"**{uploaded_file.name}** · {n_pages} page{'s' if n_pages != 1 else ''} · "
            f"{uploaded_file.size / 1024:.1f} KB &nbsp;&nbsp;"
            f'<span style="color:{_ftype_color};font-size:0.85rem">{_ftype_label}</span>',
            unsafe_allow_html=True,
        )
    with col_btn:
        run_clicked = st.button("▶ Run OCR Pipeline", type="primary", use_container_width=True)

    if file_type in {"pdf_scanned", "pdf_mixed", "image"} and not _local_ocr_ready and not ai_only:
        st.warning(
            "Local OCR engines are not available in this environment. "
            "Digital PDF pages can still work, but scanned PDFs/images need "
            "PaddleOCR or the Tesseract binary. Use AI-only mode or deploy on "
            "Python 3.12 with OCR dependencies installed."
        )

    if run_clicked:
        st.session_state.pop("pages", None)
        st.session_state.pop("doc_intel", None)
        pages: list[dict] = []

        progress_bar = st.progress(0, text="Starting pipeline…")
        status_area = st.empty()

        # ── AI-only fast path (Gemini or Grok — all document types) ─────────────
        if ai_only and ai_api_key:
            _engine_name = _ai_engine.split()[0]   # "Gemini" or "Grok"
            status_area.info(f"🤖 {_engine_name}: analysing document…")
            try:
                if _ai_engine == "Gemini":
                    from ocr.gemini_document_ocr import GeminiDocumentOCR
                    _ocr_engine = GeminiDocumentOCR(api_key=ai_api_key)
                else:
                    from ocr.grok_bank_ocr import GrokDocumentOCR
                    _ocr_engine = GrokDocumentOCR(api_key=ai_api_key)

                if not _ocr_engine.available:
                    st.error(f"{_engine_name} engine not available — check API key / dependencies.")
                else:
                    _airesult = _ocr_engine.extract(raw_images, doc_type="auto")

                    if "error" in _airesult:
                        st.error(f"{_engine_name} error: {_airesult['error']}")
                    else:
                        for i, img in enumerate(raw_images):
                            pages.append({
                                "page": i + 1,
                                "text_blocks": [],
                                "tables": [],
                                "_original_img": img,
                                "_debug_img": None,
                                "_extraction": _engine_name.lower(),
                            })
                        _detected_type = _airesult.get("doc_type", "unknown")
                        _extracted     = _airesult.get("extracted", {})
                        _t_elapsed     = _airesult.get("response_time_sec", 0)
                        _model_used    = _airesult.get("gemini_model") or _airesult.get("ai_model", "")
                        _txn_count     = _extracted.get(
                            "transaction_count",
                            len(_extracted.get("transactions", [])),
                        )
                        doc_intel = {
                            "doc_type":         _detected_type,
                            "doc_confidence":   _airesult.get("doc_confidence", 1.0),
                            "bank_name":        _extracted.get("bank_name"),
                            "bank_code":        None,
                            "languages": {
                                "detected_languages": ["en"],
                                "primary_language":   "en",
                                "multilingual":       False,
                                "translation_applied": False,
                            },
                            "extraction_engine": _engine_name.lower(),
                            "extracted":         _extracted,
                        }
                        # Multi-document PDFs: copy the documents list for display
                        if _detected_type == "multi_document" and "documents" in _airesult:
                            doc_intel["documents"] = _airesult["documents"]

                        progress_bar.progress(1.0, text="Done!")
                        if _detected_type == "multi_document":
                            _multi_docs = _airesult.get("documents", [])
                            _doc_names  = ", ".join(
                                d.get("doc_type", "?").replace("_", " ").title()
                                for d in _multi_docs
                            )
                            _ai_summary = (
                                f"✅ {_engine_name}: {len(_multi_docs)} documents — "
                                f"{_doc_names} · {len(raw_images)} page(s)"
                                f" in **{_t_elapsed:.2f}s**"
                            )
                        elif _txn_count:
                            _ai_summary = (
                                f"✅ {_engine_name}: {_detected_type.replace('_',' ').title()} — "
                                f"{_txn_count} transactions from {len(raw_images)} page(s)"
                                f" in **{_t_elapsed:.2f}s**"
                            )
                        else:
                            _ai_summary = (
                                f"✅ {_engine_name}: {_detected_type.replace('_',' ').title()}"
                                f" extracted from {len(raw_images)} page(s) in **{_t_elapsed:.2f}s**"
                            )
                        status_area.success(_ai_summary)
                        st.info(
                            f"⏱ Response time: **{_t_elapsed:.2f}s** · "
                            f"Pages: {len(raw_images)} · "
                            f"Document: {_detected_type.replace('_',' ').title()} · "
                            f"Model: {_model_used}"
                        )
                        if save_to_disk:
                            export = result_to_json_export(pages, doc_intel)
                            stem = Path(uploaded_file.name).stem
                            fname = timestamp_filename(stem)
                            saved = save_json(export, config.OUTPUT_DIR, fname)
                            st.caption(f"💾 Saved to `{saved}`")
                        st.session_state.pages = pages
                        st.session_state.doc_intel = doc_intel
            except Exception as _ae:
                st.error(f"{_engine_name} OCR failed: {_ae}")
            st.stop()
        # ── End AI-only path ──────────────────────────────────────────────────

        if file_type in {"pdf_scanned", "image"} and not _local_ocr_ready:
            st.error(
                "No local OCR engine is available for this file type. "
                "Scanned PDFs and images require PaddleOCR or Tesseract, or "
                "you can enable AI-only mode."
            )
            st.stop()

        from utils.pdf_extractor import detect_pdf_page_types, extract_digital_page

        # Determine per-page extraction method
        _page_types: list[str] = []
        if pdf_path and file_type != "image":
            _page_types = detect_pdf_page_types(pdf_path)
        else:
            _page_types = ["scanned"] * n_pages

        _known_doc_type: str | None = None   # set after page 1 classification
        _known_bank_code: str | None = None  # set after bank identified on page 1

        for i, image in enumerate(raw_images):
            frac = i / n_pages
            progress_bar.progress(frac, text=f"Processing page {i + 1} / {n_pages}…")

            _ptype = _page_types[i] if i < len(_page_types) else "scanned"
            _is_bank = _known_doc_type == "bank_statement"

            if _ptype == "digital":
                _mode_label = "direct text (no OCR)"
                status_area.info(f"📄 Page {i + 1} / {n_pages} — {_mode_label}…")
                page_result = extract_digital_page(
                    pdf_path, i, i + 1,
                    bank_code=_known_bank_code or "",
                )
                page_result["_original_img"] = image
                page_result["_debug_img"] = None
            else:
                _mode_label = "fast bank OCR" if _is_bank else "OCR"
                status_area.info(f"🔄 Page {i + 1} / {n_pages} — {_mode_label}…")
                page_result = process_page(
                    image, i + 1, ocr_mode, show_debug,
                    bank_fast_mode=_is_bank,
                )

            pages.append(page_result)

            # After page 1: peek at doc type + bank so remaining pages use fast path
            if i == 0 and _known_doc_type is None and page_result.get("_ocr_results"):
                _dc = classify_doc(page_result["_ocr_results"])
                if _dc.type == "bank_statement":
                    _known_doc_type = "bank_statement"
                    _bid = identify_bank(page_result["_ocr_results"])
                    if _bid:
                        _known_bank_code = _bid.code
                    if n_pages > 1:
                        _bank_label = f" ({_bid.name})" if _bid else ""
                        status_area.info(
                            f"🏦 Bank statement{_bank_label} detected — fast mode for "
                            f"remaining {n_pages - 1} page(s)."
                        )

        if n_pages > 1:
            pages = merge_multipage_tables(pages)

        # Document intelligence: classify + parse after all pages are done
        status_area.info("🧠 Running document classification…")
        doc_intel = run_document_intelligence(pages)

        # AI enrichment after classification (all document types)
        if ai_api_key and not ai_only:
            _engine_name  = _ai_engine.split()[0]
            _detected_doc = doc_intel.get("doc_type", "unknown")
            status_area.info(
                f"🤖 {_engine_name}: enriching "
                f"{_detected_doc.replace('_', ' ')} data…"
            )
            try:
                if _ai_engine == "Gemini":
                    from ocr.gemini_document_ocr import GeminiDocumentOCR
                    _enricher = GeminiDocumentOCR(api_key=ai_api_key)
                elif _ai_engine == "Grok (xAI)":
                    from ocr.grok_bank_ocr import GrokDocumentOCR
                    _enricher = GrokDocumentOCR(api_key=ai_api_key)
                else:
                    _enricher = None
                if _enricher and _enricher.available:
                    _bank_hint = doc_intel.get("bank_name") or doc_intel.get("bank_code") or ""
                    _ai_result = _enricher.extract(
                        raw_images,
                        doc_type=_detected_doc,
                        bank_hint=_bank_hint,
                    )
                    if "error" not in _ai_result:
                        if _ai_result.get("doc_type") == "multi_document":
                            doc_intel["doc_type"]   = "multi_document"
                            doc_intel["documents"]  = _ai_result.get("documents", [])
                            doc_intel["extracted"]  = {}
                        else:
                            _ai_extracted = _ai_result.get("extracted", {})
                            doc_intel.setdefault("extracted", {})
                            doc_intel["extracted"].update(_ai_extracted)
                            if not doc_intel.get("doc_confidence"):
                                doc_intel["doc_confidence"] = _ai_result.get("doc_confidence", 0.9)
                        doc_intel["extraction_engine"] = _engine_name.lower()
                    else:
                        st.warning(f"{_engine_name} extraction failed: {_ai_result['error']}")
            except Exception as _ae:
                st.warning(f"{_engine_name} OCR error: {_ae}")

        progress_bar.progress(1.0, text="Done!")
        _dig = sum(1 for t in _page_types if t == "digital")
        _scn = len(_page_types) - _dig
        _summary = f"✅ {n_pages} page(s) processed"
        if _dig and _scn:
            _summary += f" — {_dig} digital (direct), {_scn} scanned (OCR)"
        elif _dig:
            _summary += " — direct text extraction (no OCR needed)"
        status_area.success(_summary)

        if save_to_disk:
            export = result_to_json_export(pages, doc_intel)
            stem = Path(uploaded_file.name).stem
            fname = timestamp_filename(stem)
            saved = save_json(export, config.OUTPUT_DIR, fname)
            st.caption(f"💾 Saved to `{saved}`")

        st.session_state.pages = pages
        st.session_state.doc_intel = doc_intel

# ── results ───────────────────────────────────────────────────────────────────

if "pages" in st.session_state:
    pages: list[dict] = st.session_state.pages
    doc_intel: dict = st.session_state.get("doc_intel", {})

    # ── document intelligence banner ──────────────────────────────────────────
    if doc_intel:
        _lang_info    = doc_intel.get("languages", {})
        _primary_lang = _lang_info.get("primary_language", "en")
        _lang_name    = LANG_NAMES.get(_primary_lang, _primary_lang)
        _is_multilang = _lang_info.get("multilingual", False)
        _is_translated = _lang_info.get("translation_applied", False)
        _all_langs    = _lang_info.get("detected_languages", ["en"])
        _lang_display = " + ".join(LANG_NAMES.get(lang, lang) for lang in _all_langs if lang != "en")
        _lang_html = ""
        if _is_multilang or _primary_lang != "en":
            _lang_label = f"🌐 {_lang_display or _lang_name}"
            if _is_translated:
                _lang_label += " (translated)"
            _lang_html = f'<span class="bank-tag" style="background:#1a1a3a;color:#af8fff">{_lang_label}</span>'

        _is_multi_doc = doc_intel.get("doc_type") == "multi_document"

        if _is_multi_doc:
            # ── Multi-document: show each detected doc separately ─────────────
            _docs = doc_intel.get("documents", [])
            _doc_labels = " · ".join(
                f"{d['doc_type'].replace('_',' ').title()} (p{d['pages'][0]})"
                for d in _docs
            )
            st.markdown(
                f"""
                <div class="doc-intel-banner">
                    <div>
                        <div class="conf-label">Multi-Document PDF</div>
                        <div class="doc-type">{_doc_labels}</div>
                    </div>
                    {_lang_html}
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Show extracted fields per document in expandable sections
            for d in _docs:
                _dtype_label = d["doc_type"].replace("_", " ").title()
                _pages_label = ", ".join(f"p{pg}" for pg in d["pages"])
                _bank_tag = f"&nbsp;·&nbsp;🏦 {d['bank_name']}" if d.get("bank_name") else ""
                with st.expander(f"📄 {_dtype_label} ({_pages_label}){_bank_tag}", expanded=True):
                    _ext = {k: v for k, v in d.get("extracted", {}).items()
                            if k not in ("raw_text", "metadata", "transactions", "warnings")}
                    if _ext:
                        rows = "".join(
                            f"<tr><td>{k.replace('_',' ').title()}</td><td>{v}</td></tr>"
                            for k, v in _ext.items()
                        )
                        st.markdown(
                            f'<table class="meta-table">{rows}</table>',
                            unsafe_allow_html=True,
                        )
                    _meta = d.get("extracted", {}).get("metadata", {})
                    if _meta:
                        rows = "".join(
                            f"<tr><td>{k.replace('_',' ').title()}</td><td>{v}</td></tr>"
                            for k, v in _meta.items()
                        )
                        st.markdown(
                            f'<table class="meta-table">{rows}</table>',
                            unsafe_allow_html=True,
                        )
        else:
            # ── Single doc type ───────────────────────────────────────────────
            _dtype  = doc_intel.get("doc_type", "other").replace("_", " ").title()
            _dconf  = int(doc_intel.get("doc_confidence", 0) * 100)
            _bank   = doc_intel.get("bank_name", "")
            _engine = doc_intel.get("extraction_engine", "")
            _bank_html = (
                f'<span class="bank-tag">🏦 {_bank}</span>' if _bank else ""
            )
            if _engine in ("gemini", "grok"):
                _engine_label = "Gemini AI" if _engine == "gemini" else "Grok (xAI)"
                _bank_html += f' <span class="bank-tag" style="background:#1a2a1a;color:#7fff7f">🤖 {_engine_label}</span>'
            _meta = doc_intel.get("extracted", {}).get("metadata", {})
            _meta_rows_html = "".join(
                f"<tr><td>{k.replace('_', ' ').title()}</td><td>{v}</td></tr>"
                for k, v in _meta.items()
            )
            _meta_html = (
                f'<table class="meta-table">{_meta_rows_html}</table>'
                if _meta_rows_html else ""
            )
            _ext = {
                k: v for k, v in doc_intel.get("extracted", {}).items()
                if k not in ("doc_type", "raw_text", "metadata", "transactions",
                             "warnings", "text_items")
            }
            _field_rows = []
            for k, v in _ext.items():
                label = k.replace("_", " ").title()
                if isinstance(v, dict):
                    for sub_k, sub_v in v.items():
                        _field_rows.append(
                            f"<tr><td>&nbsp;&nbsp;{label} › {sub_k.replace('_',' ').title()}</td>"
                            f"<td>{sub_v}</td></tr>"
                        )
                else:
                    _field_rows.append(f"<tr><td>{label}</td><td>{v}</td></tr>")
            _fields_html = "".join(_field_rows)
            _fields_section = (
                f'<table class="meta-table">{_fields_html}</table>'
                if _fields_html else ""
            )
            _warns = doc_intel.get("extracted", {}).get("warnings", [])
            _warn_html = "".join(f"<li style='color:#f0c060'>{w}</li>" for w in _warns)

            st.markdown(
                f"""
                <div class="doc-intel-banner">
                    <div>
                        <div class="conf-label">Document Type</div>
                        <div class="doc-type">{_dtype}</div>
                        <div class="conf-label">Confidence: {_dconf}%</div>
                    </div>
                    {_bank_html}
                    {_lang_html}
                </div>
                {_meta_html}
                {_fields_section}
                {"<ul style='font-size:0.8rem;margin-top:0.5rem'>" + _warn_html + "</ul>" if _warn_html else ""}
                """,
                unsafe_allow_html=True,
            )

    # ── summary metrics ──
    total_tables = sum(len(p["tables"]) for p in pages)
    total_blocks = sum(len(p["text_blocks"]) for p in pages)
    total_words = sum(
        len(b["text"].split())
        for p in pages
        for b in p["text_blocks"]
    )

    st.markdown(
        f"""
        <div class="metric-row">
            <div class="metric-card"><div class="val">{len(pages)}</div><div class="lbl">Pages</div></div>
            <div class="metric-card"><div class="val">{total_blocks}</div><div class="lbl">Text blocks</div></div>
            <div class="metric-card"><div class="val">{total_tables}</div><div class="lbl">Tables</div></div>
            <div class="metric-card"><div class="val">{total_words}</div><div class="lbl">Words</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── AI-extracted transactions table ──
    _gemini_txns = doc_intel.get("extracted", {}).get("transactions") if doc_intel else None
    _ai_engine_used = doc_intel.get("extraction_engine", "") if doc_intel else ""
    if _gemini_txns and _ai_engine_used in ("gemini", "grok"):
        _ai_label = "Gemini AI" if _ai_engine_used == "gemini" else "Grok (xAI)"
        st.markdown(f"**🤖 {_ai_label} — Extracted Transactions**")
        _txn_count = doc_intel["extracted"].get("transaction_count", len(_gemini_txns))
        st.caption(f"{_txn_count} transactions extracted by {_ai_label}")
        df_txn = pd.DataFrame(_gemini_txns)
        st.dataframe(df_txn, use_container_width=True)

    # ── per-page tabs ──
    tab_labels = [f"Page {p['page']}" for p in pages]
    tabs = st.tabs(tab_labels)

    for tab, page in zip(tabs, pages):
        with tab:
            left, right = st.columns([1, 1], gap="large")

            # ── LEFT: image preview ──
            with left:
                st.markdown("**Document Preview**")
                display_img = page["_debug_img"] if show_debug and page["_debug_img"] is not None else page["_original_img"]
                st.image(bgr_to_pil(display_img), use_container_width=True)

                if show_debug:
                    st.caption("🟢 Text  🔴 Title  🔵 Table  🟠 Figure  🟣 List")

            # ── RIGHT: OCR results ──
            with right:
                # Extraction method badge
                _extr = page.get("_extraction", "ocr")
                if _extr == "digital":
                    st.markdown(
                        '<span class="badge" style="background:#0d2b1a;color:#5fdd8f">'
                        'Direct text extraction</span>',
                        unsafe_allow_html=True,
                    )

                # Page-level language tag
                page_lang = page.get("_lang_summary", {})
                if page_lang.get("multilingual") or page_lang.get("primary_language", "en") != "en":
                    _pl = page_lang.get("primary_language", "en")
                    _pn = LANG_NAMES.get(_pl, _pl)
                    _tr = " · translated" if page_lang.get("translation_applied") else ""
                    st.markdown(
                        f'<span class="badge" style="background:#1a1a3a;color:#af8fff">'
                        f'🌐 {_pn}{_tr}</span>',
                        unsafe_allow_html=True,
                    )

                # ─ text blocks ─
                text_blocks = page["text_blocks"]
                if text_blocks:
                    st.markdown("**Text Blocks**")
                    for blk in text_blocks:
                        btype = blk["type"]
                        badge_cls = f"badge-{btype.lower()}"
                        conf_pct = int(blk["confidence"] * 100)
                        conf_width = max(2, conf_pct)
                        lang_tag = (f" · {blk['lang_name']}" if blk.get("lang_name") else "")

                        with st.expander(
                            f"{btype} block — confidence {conf_pct}%{lang_tag}",
                            expanded=(btype == "Title"),
                        ):
                            st.markdown(
                                f'<span class="badge {badge_cls}">{btype}</span>'
                                f'<div class="conf-bar-wrap">'
                                f'<div class="conf-bar" style="width:{conf_width}%"></div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                            # Show translated (English) text
                            st.markdown(blk["text"])
                            # Show original Indian-language text if translated
                            if blk.get("original_text"):
                                st.caption(f"Original ({blk.get('lang_name','')}):")
                                st.markdown(
                                    f'<div style="color:#888;font-size:0.82rem;'
                                    f'border-left:2px solid #333;padding-left:8px">'
                                    f'{blk["original_text"]}</div>',
                                    unsafe_allow_html=True,
                                )
                            st.caption(
                                f"bbox: {[round(v) for v in blk['bbox']]}"
                            )
                else:
                    st.info("No text blocks detected on this page.")

                # ─ tables ─
                tables = page["tables"]
                if tables:
                    st.markdown("**Tables**")
                    for t_idx, tbl in enumerate(tables, 1):
                        rows = tbl["rows"]
                        st.markdown(
                            f'<span class="badge badge-table">Table {t_idx}</span>',
                            unsafe_allow_html=True,
                        )
                        if rows:
                            df = pd.DataFrame(rows)
                            st.dataframe(df, width="stretch")
                        else:
                            st.warning("Table detected but no cells extracted.")
                        st.caption(f"bbox: {[round(v) for v in tbl['bbox']]}")

    # ── JSON viewer + download ──
    st.divider()
    export_data = result_to_json_export(pages, doc_intel if doc_intel else None)
    json_str = json.dumps(export_data, indent=2, ensure_ascii=False)

    col_dl, col_view = st.columns([1, 3])
    with col_dl:
        stem = Path(st.session_state.last_filename or "result").stem
        st.download_button(
            label="⬇ Download JSON",
            data=json_str,
            file_name=timestamp_filename(stem),
            mime="application/json",
            use_container_width=True,
        )
    with col_view:
        with st.expander("View raw JSON output"):
            st.code(json_str, language="json")

elif not uploaded_file:
    # ── empty state ──
    st.markdown(
        """
        <div style="text-align:center; padding: 4rem 2rem; color: #555;">
            <div style="font-size: 4rem;">📄</div>
            <p style="font-size: 1.1rem; margin-top: 1rem;">
                Upload a PDF or image above to get started
            </p>
            <p style="font-size: 0.85rem; color: #444;">
                Supports PDFs, PNG, JPG, TIFF, BMP
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
