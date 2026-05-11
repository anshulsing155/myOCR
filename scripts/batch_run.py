"""
Batch process all files in inputs/ using the full classification + parsing pipeline.

Strategy for speed:
  - Digital PDFs  → direct pdfplumber text extraction (instant, no OCR)
  - Scanned PDFs  → Tesseract (fast, skips heavy PaddleOCR server model)
  - Images        → Tesseract
  - Large files   → capped at first MAX_PAGES pages

Run from the project root:
    python -u scripts/batch_run.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import traceback
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(Path(__file__).parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from classification.doc_classifier import classify  # noqa: E402
from pipeline.document_pipeline import DocumentPipeline  # noqa: E402
from utils.pdf_to_image import pdf_to_images  # noqa: E402

INPUT_DIR  = "inputs"
OUTPUT_DIR = "outputs"
MAX_PAGES  = 5          # cap per document to keep runtime manageable
MAX_SIZE_MB = 15        # skip files larger than this (huge bank statements)
SUPPORTED  = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}

os.makedirs(OUTPUT_DIR, exist_ok=True)
pipeline = DocumentPipeline()


def _ocr_results_from_text(text: str) -> list[dict]:
    """Wrap plain text as a synthetic OCR result list (for digital PDFs)."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return [{"text": ln, "confidence": 1.0, "bbox": None} for ln in lines]


_TXN_DATE_RE = re.compile(
    r"^(?:\d{1,5}\s+)?"                                 # optional serial number
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}"           # DD/MM/YY or DD.MM.YYYY
    r"|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})",  # D Mon YYYY
    re.I,
)
_AMT_RE = re.compile(r"^[\d,]+\.\d{1,2}$")


_HEADER_SKIP_RE = re.compile(
    r"^(?:txn|value|date|narration|description|particulars|debit|credit|"
    r"balance|chq|ref|withdrawal|deposit|s\.?\s*no|cheque|transaction|"
    r"opening\s+balance|closing\s+balance|page\s+no|statement|"
    r"nomination|micr|cif\s*no|ifs\s*code|ifsc|\(magnetic|drawing\s+power|"
    r"interest\s+rate|mod\s+balance|account\s+(?:name|number|description|statement|branch)|"
    r"address\s*(?:\(cid)?|\(cid:|branch\s*(?:\(cid|:)|\([A-Z])",
    re.I,
)
# SBI split-date: "DD Mon DD Mon NARRATION AMOUNT BALANCE" (year on next line)
# Trailing \s+ is intentionally omitted so "29 SepTO..." (merged tokens) also matches.
_SPLIT_DATE_RE = re.compile(
    r"^(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"\s+\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
    re.I,
)
_YEAR_CONT_RE = re.compile(r"^(\d{4})\s+\d{4}")  # "YYYY YYYY ..."


def _build_txn_row(line_words: list, page_w: float,
                   date_str: str, pre_narr: list[str]) -> dict:
    """Construct a transaction dict from the matched line's words."""
    num_words = [
        w for w in line_words
        if re.match(r"^[\d,]+\.?\d*$", w["text"])
        and w["x0"] > page_w * 0.60
    ]
    text_words = [w for w in line_words if w not in num_words]
    balance = num_words[-1]["text"].replace(",", "") if num_words else ""
    amount  = num_words[-2]["text"].replace(",", "") if len(num_words) >= 2 else ""
    inline = re.sub(r"^" + re.escape(date_str) + r"\s*",
                    "", " ".join(w["text"] for w in text_words)).strip()
    inline = re.sub(r"^\d{1,5}\s*", "", inline).strip()
    # Strip value-date prefix left by SBI double-date format ("Oct 2023" or "Sep 29 SepTO")
    for _ in range(2):
        inline = re.sub(
            r"^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*(?:\s+\d+)?\s*",
            "", inline, flags=re.I,
        ).strip()
    narr = " ".join([ln for ln in pre_narr if ln] + ([inline] if inline else []))
    return {"date": date_str, "narration": narr,
            "debit": amount, "credit": "", "balance": balance}


def _pdf_bank_rows(path: str) -> list[dict]:
    """
    Extract bank transaction rows from a digital PDF using word-level positions.
    Handles:
      • DD/MM/YY, DD.MM.YYYY  (HDFC/ICICI style)
      • D Mon YYYY            (SBI single-digit-day style)
      • DD Mon DD Mon NARR + YYYY YYYY ... (SBI split-date style for double-digit days)
      • Serial-prefixed rows  (ICICI: "19 20.10.2025 300.00 462088.51")
    """
    from collections import defaultdict

    import pdfplumber

    rows: list[dict] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:MAX_PAGES]:
            words = page.extract_words(x_tolerance=4, y_tolerance=4)
            if not words:
                continue
            page_w = float(page.width or 600)

            # Group words by quantised Y position (8px buckets)
            y_groups: dict[int, list] = defaultdict(list)
            for w in words:
                bucket = round(w["top"] / 8) * 8
                y_groups[bucket].append(w)

            sorted_keys = sorted(y_groups)
            pending_row: dict | None = None
            pre_narr_lines: list[str] = []

            idx = 0
            while idx < len(sorted_keys):
                y_key = sorted_keys[idx]
                line_words = sorted(y_groups[y_key], key=lambda w: w["x0"])
                line_text = " ".join(w["text"] for w in line_words)

                # ── SBI split-date: "DD Mon DD Mon NARR AMT BAL" ──────────────
                sd_m = _SPLIT_DATE_RE.match(line_text)
                if sd_m:
                    # Look ahead for the year continuation line
                    year_str = ""
                    year_narr = ""
                    if idx + 1 < len(sorted_keys):
                        next_words = sorted(y_groups[sorted_keys[idx + 1]],
                                            key=lambda w: w["x0"])
                        next_text  = " ".join(w["text"] for w in next_words)
                        ym = _YEAR_CONT_RE.match(next_text)
                        if ym:
                            year_str = ym.group(1)
                            # Capture any narration sitting after "YYYY YYYY" on the year line
                            year_narr = re.sub(r"^\d{4}\s+\d{4}\s*", "", next_text).strip()
                            idx += 1  # consume the year line

                    day, mon = sd_m.group(1), sd_m.group(2)
                    date_str = f"{day} {mon} {year_str}".strip()
                    if pending_row is not None:
                        rows.append(pending_row)
                    pending_row = _build_txn_row(line_words, page_w, date_str, pre_narr_lines)
                    if year_narr:
                        pending_row["narration"] = (
                            pending_row["narration"] + " " + year_narr).strip()
                    pre_narr_lines = []
                    idx += 1
                    continue

                # ── Normal date match ─────────────────────────────────────────
                if _TXN_DATE_RE.match(line_text):
                    if pending_row is not None:
                        rows.append(pending_row)
                    date_str = _TXN_DATE_RE.match(line_text).group(1)
                    pending_row = _build_txn_row(line_words, page_w, date_str, pre_narr_lines)
                    pre_narr_lines = []

                else:
                    cont = line_text.strip()
                    if not cont or _HEADER_SKIP_RE.match(cont) or "(cid:" in cont:
                        pass
                    elif pending_row is not None:
                        pending_row["narration"] = (
                            pending_row["narration"] + " " + cont).strip()
                    else:
                        pre_narr_lines.append(cont)
                        pre_narr_lines = pre_narr_lines[-3:]

                idx += 1

            if pending_row is not None:
                rows.append(pending_row)
    return rows


def process_digital_pdf(path: str) -> dict:
    """Extract text directly from a digital PDF using pdfplumber (no OCR)."""
    import pdfplumber
    all_ocr: list[dict] = []
    with pdfplumber.open(path) as pdf:
        pages = pdf.pages[:MAX_PAGES]
        for page in pages:
            text = page.extract_text() or ""
            all_ocr.extend(_ocr_results_from_text(text))

    dc = classify(all_ocr)

    # For bank statements: use spatial word extraction to reconstruct transaction rows
    if dc.type == "bank_statement":
        from parsers.bank_statement.bank_identifier import identify_bank
        from parsers.bank_statement.bank_parser import (
            parse as bank_parse,
        )
        bank_id = identify_bank(all_ocr)
        bank_code = bank_id.code if bank_id else "default"
        digital_rows = _pdf_bank_rows(path)
        extracted = bank_parse(all_ocr, bank_code=bank_code, digital_rows=digital_rows or None)
    else:
        extracted = pipeline._route(all_ocr, dc.type, {})

    return {
        "doc_type": dc.type,
        "doc_confidence": round(dc.confidence, 3),
        "extraction_method": "digital_pdf",
        "extracted": extracted,
    }


def process_with_tesseract(images: list[np.ndarray]) -> dict:
    """OCR images with Tesseract, then classify + parse."""
    from ocr.tesseract_engine import run_tesseract
    all_ocr: list[dict] = []
    for img in images[:MAX_PAGES]:
        results = run_tesseract(img)
        all_ocr.extend(results)

    if not all_ocr:
        return {"doc_type": "other", "doc_confidence": 0.0,
                "extraction_method": "tesseract_ocr", "extracted": {}}

    dc = classify(all_ocr)
    extracted = pipeline._route(all_ocr, dc.type, {})
    return {
        "doc_type": dc.type,
        "doc_confidence": round(dc.confidence, 3),
        "extraction_method": "tesseract_ocr",
        "extracted": extracted,
    }


def is_digital_pdf(path: str) -> bool:
    try:
        import fitz
        doc = fitz.open(path)
        chars = sum(len(p.get_text("text").strip()) for p in doc)
        doc.close()
        return chars > 200
    except Exception:
        return False


def load_images(path: str) -> list:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return pdf_to_images(path)
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Cannot read image: {path}")
    return [img]


def summarise(obj):
    """Strip raw_text / page_results / ocr_results from result dicts."""
    if isinstance(obj, dict):
        return {k: summarise(v) for k, v in obj.items()
                if k not in ("raw_text", "page_results", "ocr_results")}
    if isinstance(obj, list):
        return [summarise(i) for i in obj]
    return obj


# ── collect input files ───────────────────────────────────────────────────────
files = sorted(
    p for p in Path(INPUT_DIR).iterdir()
    if p.suffix.lower() in SUPPORTED
)

print(f"Found {len(files)} file(s) in {INPUT_DIR}/")
print("=" * 70)

results_summary: list[dict] = []

for fpath in files:
    fname = fpath.name
    size_mb = fpath.stat().st_size / (1024 * 1024)
    print(f"\n[{fname}]  ({size_mb:.1f} MB)", flush=True)

    entry: dict = {"file": fname, "size_mb": round(size_mb, 1), "status": "ok"}

    try:
        ext = fpath.suffix.lower()

        if size_mb > MAX_SIZE_MB:
            # For very large files, only process first MAX_PAGES pages
            print(f"   NOTE: large file — capping at {MAX_PAGES} pages", flush=True)

        if ext == ".pdf" and is_digital_pdf(str(fpath)):
            result = process_digital_pdf(str(fpath))
        else:
            images = load_images(str(fpath))
            result = process_with_tesseract(images)

        compact = summarise(result)
        entry["doc_type"]          = compact.get("doc_type", "?")
        entry["confidence"]        = compact.get("doc_confidence", "?")
        entry["extraction_method"] = compact.get("extraction_method", "?")
        entry["extracted"]         = compact.get("extracted", {})

        # Save per-file JSON
        out_name = fpath.stem.replace(" ", "_") + "_result.json"
        out_path = Path(OUTPUT_DIR) / out_name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(compact, f, indent=2, ensure_ascii=False, default=str)

        print(f"   doc_type  : {entry['doc_type']}  (conf={entry['confidence']}, method={entry['extraction_method']})", flush=True)
        ext_keys = [k for k in entry["extracted"] if k not in ("raw_text", "doc_type")]
        if ext_keys:
            print(f"   fields    : {', '.join(ext_keys)}", flush=True)

        # Print key extracted values
        ex = entry["extracted"]
        for key in ("pan_number", "aadhaar_number", "name", "date_of_birth",
                    "gstin", "uan", "employee_name", "net_salary",
                    "pan_holder_type", "gender", "address", "state"):
            if key in ex and ex[key]:
                val = str(ex[key])
                if len(val) > 80:
                    val = val[:77] + "..."
                print(f"   {key:<18}: {val}", flush=True)

        # Bank statement transaction count
        if "transactions" in ex:
            print(f"   transactions      : {len(ex['transactions'])}", flush=True)
        if "metadata" in ex:
            meta = ex["metadata"]
            for mk in ("account_number", "account_holder", "bank_name", "opening_balance", "closing_balance"):
                if mk in meta and meta[mk]:
                    print(f"   meta.{mk:<14}: {meta[mk]}", flush=True)

        print(f"   saved     : {out_path}", flush=True)

    except Exception as exc:
        entry["status"] = "error"
        entry["error"]  = str(exc)
        print(f"   ERROR: {exc}", flush=True)
        traceback.print_exc()

    results_summary.append(entry)

# ── write summary ─────────────────────────────────────────────────────────────
summary_path = Path(OUTPUT_DIR) / "_batch_summary.json"
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(results_summary, f, indent=2, ensure_ascii=False, default=str)

print("\n" + "=" * 70)
print(f"Done. Summary -> {summary_path}")
ok  = sum(1 for r in results_summary if r["status"] == "ok")
err = sum(1 for r in results_summary if r["status"] == "error")
print(f"  OK: {ok}   Errors: {err}")
