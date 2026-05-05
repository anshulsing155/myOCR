"""
Document Intelligence Pipeline orchestrator.

Flow per document:
    1. OCR   — PaddleOCR with automatic Tesseract fallback
    2. Classify — keyword scoring → doc_type + confidence
    3. Route — dispatches to the appropriate parser based on doc_type

Supported doc_types:
    bank_statement, pan_card, aadhaar, eshram, itr, salary_slip,
    voter_id, passport, vehicle_rc, birth_certificate, marriage_certificate,
    caste_certificate, income_certificate, domicile_certificate, ration_card,
    gst_certificate, marksheet, degree_certificate, ayushman_card, ppo,
    driving_license, invoice, property_doc,
    sale_deed, agreement_to_sale, encumbrance_certificate, property_tax_receipt,
    khata, mutation_certificate, land_record, rera_certificate,
    occupancy_certificate, possession_letter, power_of_attorney, lease_deed,
    gift_deed, partition_deed, mortgage_deed, estamp_certificate,
    property_valuation, home_loan_sanction, legal_heir_certificate, other
"""
from __future__ import annotations

import logging
from collections import Counter
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# ── OCR with fallback ─────────────────────────────────────────────────────────

def run_ocr_with_fallback(image: np.ndarray, mode: str = "auto") -> list[dict]:
    """
    Run PaddleOCR with multilingual support; fall back to Tesseract on failure.
    Returns OCR results with language/translation enrichment applied.
    """
    ocr_results: list[dict] = []
    detected_lang: str | None = None

    try:
        from ocr.paddle_engine import run_paddle_multilingual
        ocr_results, detected_lang = run_paddle_multilingual(image)
    except Exception as exc:
        logger.warning("PaddleOCR multilingual failed (%s) — trying Tesseract", exc)

    if not ocr_results:
        try:
            from ocr.tesseract_engine import run_tesseract
            ocr_results = run_tesseract(image)
        except Exception as exc:
            logger.warning("Tesseract also failed: %s", exc)

    if ocr_results:
        from postprocessing.language_processor import process_multilingual_ocr, get_translated_ocr
        ocr_results = process_multilingual_ocr(ocr_results)
        # Return translated version so parsers receive English text
        ocr_results = get_translated_ocr(ocr_results)

    return ocr_results


# ── pipeline ──────────────────────────────────────────────────────────────────

def _crossref_identity_docs(documents: list[dict]) -> None:
    """
    Post-processing for multi-document PDFs: cross-validate PAN + Aadhaar pairs.

    - DOB mismatch → warning on both docs
    - PAN name missing or low-confidence + Aadhaar name present → copy Aadhaar name to PAN
    - PAN name and Aadhaar name both present but share no words → flag PAN as low-confidence
      and attach Aadhaar name as a hint
    Modifies documents in-place; no-op when PAN or Aadhaar not found.
    """
    pan_doc = next((d for d in documents if d.get("doc_type") == "pan_card"), None)
    aad_doc = next((d for d in documents if d.get("doc_type") == "aadhaar"), None)
    if not pan_doc or not aad_doc:
        return

    pan_ext = pan_doc.setdefault("extracted", {})
    aad_ext = aad_doc.get("extracted", {})

    pan_name = pan_ext.get("name", "")
    aad_name = aad_ext.get("name", "")
    pan_dob  = pan_ext.get("date_of_birth", "")
    aad_dob  = aad_ext.get("date_of_birth", "")

    # DOB cross-check
    if pan_dob and aad_dob and pan_dob != aad_dob:
        msg = f"DOB mismatch: PAN={pan_dob}, Aadhaar={aad_dob}"
        pan_doc.setdefault("warnings", []).append(msg)
        aad_doc.setdefault("warnings", []).append(msg)

    # Name cross-reference
    if aad_name:
        if not pan_name or pan_ext.get("name_confidence") == "low":
            pan_ext["name"] = aad_name
            pan_ext["name_source"] = "aadhaar_cross_reference"
            pan_ext.pop("name_confidence", None)
        else:
            pan_words = set(pan_name.upper().split())
            aad_words = set(aad_name.upper().split())
            if not pan_words & aad_words:
                pan_ext["name_confidence"] = "low"
                pan_ext["name_aadhaar_hint"] = aad_name


class DocumentPipeline:
    """
    Stateless pipeline.

    Single-page:  call process()
    Multi-page:   call process_pages() — combines all pages into one result
    """

    def process(
        self,
        image: np.ndarray,
        ocr_mode: str = "auto",
        force_doc_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Process one page image.

        Returns:
            ocr_results     — raw OCR items (text/confidence/bbox)
            doc_type        — detected document category
            doc_confidence  — classification confidence (0-1)
            bank_name       — e.g. "HDFC Bank"  (bank statements only)
            bank_code       — e.g. "hdfc"        (bank statements only)
            extracted       — parser output (transactions/metadata or fields)
        """
        ocr_results = run_ocr_with_fallback(image, mode=ocr_mode)

        if force_doc_type:
            doc_type, doc_conf = force_doc_type, 1.0
        else:
            from classification.doc_classifier import classify
            dc = classify(ocr_results)
            doc_type, doc_conf = dc.type, dc.confidence

        result: dict[str, Any] = {
            "ocr_results":    ocr_results,
            "doc_type":       doc_type,
            "doc_confidence": doc_conf,
            "bank_name":      None,
            "bank_code":      None,
            "extracted":      {},
        }

        result["extracted"] = self._route(ocr_results, doc_type, result)

        # Language summary for this page
        from postprocessing.language_processor import summarise_languages
        result["languages"] = summarise_languages(ocr_results)

        return result

    def _route(
        self,
        ocr_results: list[dict],
        doc_type: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        if doc_type == "bank_statement":
            from parsers.bank_statement.bank_identifier import identify_bank
            from parsers.bank_statement.bank_parser import parse as bank_parse
            bank_id = identify_bank(ocr_results)
            if bank_id:
                result["bank_name"] = bank_id.name
                result["bank_code"] = bank_id.code
            bank_code = bank_id.code if bank_id else "default"
            return bank_parse(ocr_results, bank_code=bank_code)

        if doc_type == "pan_card":
            from parsers.pan_parser import PanParser
            return PanParser().parse(ocr_results)

        if doc_type == "aadhaar":
            from parsers.aadhaar_parser import AadhaarParser
            return AadhaarParser().parse(ocr_results)

        if doc_type == "eshram":
            from parsers.eshram_parser import EshramParser
            return EshramParser().parse(ocr_results)

        if doc_type == "itr":
            from parsers.itr_parser import ItrParser
            return ItrParser().parse(ocr_results)

        if doc_type == "salary_slip":
            from parsers.salary_slip_parser import SalarySlipParser
            return SalarySlipParser().parse(ocr_results)

        if doc_type == "driving_license":
            from parsers.driving_license_parser import DrivingLicenseParser
            return DrivingLicenseParser().parse(ocr_results)

        if doc_type == "voter_id":
            from parsers.voter_id_parser import VoterIdParser
            return VoterIdParser().parse(ocr_results)

        if doc_type == "passport":
            from parsers.passport_parser import PassportParser
            return PassportParser().parse(ocr_results)

        if doc_type == "vehicle_rc":
            from parsers.vehicle_rc_parser import VehicleRcParser
            return VehicleRcParser().parse(ocr_results)

        if doc_type == "birth_certificate":
            from parsers.birth_certificate_parser import BirthCertificateParser
            return BirthCertificateParser().parse(ocr_results)

        if doc_type == "marriage_certificate":
            from parsers.marriage_certificate_parser import MarriageCertificateParser
            return MarriageCertificateParser().parse(ocr_results)

        if doc_type == "caste_certificate":
            from parsers.caste_certificate_parser import CasteCertificateParser
            return CasteCertificateParser().parse(ocr_results)

        if doc_type == "income_certificate":
            from parsers.income_certificate_parser import IncomeCertificateParser
            return IncomeCertificateParser().parse(ocr_results)

        if doc_type == "domicile_certificate":
            from parsers.domicile_certificate_parser import DomicileCertificateParser
            return DomicileCertificateParser().parse(ocr_results)

        if doc_type == "ration_card":
            from parsers.ration_card_parser import RationCardParser
            return RationCardParser().parse(ocr_results)

        if doc_type == "gst_certificate":
            from parsers.gst_certificate_parser import GstCertificateParser
            return GstCertificateParser().parse(ocr_results)

        if doc_type == "marksheet":
            from parsers.marksheet_parser import MarksheetParser
            return MarksheetParser().parse(ocr_results)

        if doc_type == "degree_certificate":
            from parsers.degree_certificate_parser import DegreeCertificateParser
            return DegreeCertificateParser().parse(ocr_results)

        if doc_type == "ayushman_card":
            from parsers.ayushman_card_parser import AyushmanCardParser
            return AyushmanCardParser().parse(ocr_results)

        if doc_type == "ppo":
            from parsers.ppo_parser import PpoParser
            return PpoParser().parse(ocr_results)

        if doc_type == "sale_deed":
            from parsers.realestate.sale_deed_parser import SaleDeedParser
            return SaleDeedParser().parse(ocr_results)

        if doc_type == "agreement_to_sale":
            from parsers.realestate.agreement_to_sale_parser import AgreementToSaleParser
            return AgreementToSaleParser().parse(ocr_results)

        if doc_type == "encumbrance_certificate":
            from parsers.realestate.encumbrance_certificate_parser import EncumbranceCertificateParser
            return EncumbranceCertificateParser().parse(ocr_results)

        if doc_type == "property_tax_receipt":
            from parsers.realestate.property_tax_parser import PropertyTaxParser
            return PropertyTaxParser().parse(ocr_results)

        if doc_type == "khata":
            from parsers.realestate.khata_parser import KhataParser
            return KhataParser().parse(ocr_results)

        if doc_type == "mutation_certificate":
            from parsers.realestate.mutation_certificate_parser import MutationCertificateParser
            return MutationCertificateParser().parse(ocr_results)

        if doc_type == "land_record":
            from parsers.realestate.land_record_parser import LandRecordParser
            return LandRecordParser().parse(ocr_results)

        if doc_type == "rera_certificate":
            from parsers.realestate.rera_certificate_parser import ReraCertificateParser
            return ReraCertificateParser().parse(ocr_results)

        if doc_type == "occupancy_certificate":
            from parsers.realestate.occupancy_certificate_parser import OccupancyCertificateParser
            return OccupancyCertificateParser().parse(ocr_results)

        if doc_type == "possession_letter":
            from parsers.realestate.possession_letter_parser import PossessionLetterParser
            return PossessionLetterParser().parse(ocr_results)

        if doc_type == "power_of_attorney":
            from parsers.realestate.power_of_attorney_parser import PowerOfAttorneyParser
            return PowerOfAttorneyParser().parse(ocr_results)

        if doc_type == "lease_deed":
            from parsers.realestate.lease_deed_parser import LeaseDeedParser
            return LeaseDeedParser().parse(ocr_results)

        if doc_type == "gift_deed":
            from parsers.realestate.gift_deed_parser import GiftDeedParser
            return GiftDeedParser().parse(ocr_results)

        if doc_type == "partition_deed":
            from parsers.realestate.partition_deed_parser import PartitionDeedParser
            return PartitionDeedParser().parse(ocr_results)

        if doc_type == "mortgage_deed":
            from parsers.realestate.mortgage_deed_parser import MortgageDeedParser
            return MortgageDeedParser().parse(ocr_results)

        if doc_type == "estamp_certificate":
            from parsers.realestate.estamp_certificate_parser import EStampCertificateParser
            return EStampCertificateParser().parse(ocr_results)

        if doc_type == "property_valuation":
            from parsers.realestate.property_valuation_parser import PropertyValuationParser
            return PropertyValuationParser().parse(ocr_results)

        if doc_type == "home_loan_sanction":
            from parsers.realestate.home_loan_sanction_parser import HomeLoanSanctionParser
            return HomeLoanSanctionParser().parse(ocr_results)

        if doc_type == "legal_heir_certificate":
            from parsers.realestate.legal_heir_certificate_parser import LegalHeirCertificateParser
            return LegalHeirCertificateParser().parse(ocr_results)

        from parsers.generic_parser import GenericParser
        return GenericParser().parse(ocr_results, doc_type=doc_type)

    def process_pages(
        self,
        images: list[np.ndarray],
        ocr_mode: str = "auto",
    ) -> dict[str, Any]:
        """
        Process all pages; combine into one document-level result.
        Supports multi-document PDFs where different pages have different doc types.
        """
        if not images:
            return {}

        page_results = [self.process(img, ocr_mode) for img in images]

        # ── Aggregate language info ───────────────────────────────────────────
        all_langs = list({
            l for p in page_results
            for l in p.get("languages", {}).get("detected_languages", [])
        })
        primary_lang = next(
            (p["languages"]["primary_language"] for p in page_results
             if p.get("languages", {}).get("primary_language", "en") != "en"),
            "en"
        )
        lang_info = {
            "detected_languages": sorted(all_langs) if all_langs else ["en"],
            "primary_language": primary_lang,
            "multilingual": any(p.get("languages", {}).get("multilingual")
                                for p in page_results),
            "translation_applied": any(p.get("languages", {}).get("translation_applied")
                                       for p in page_results),
        }

        # ── Group consecutive pages by doc type ───────────────────────────────
        groups: list[dict] = []
        for i, p in enumerate(page_results):
            dt = p["doc_type"]
            if groups and groups[-1]["doc_type"] == dt:
                groups[-1]["page_indices"].append(i)
            else:
                groups.append({"doc_type": dt, "doc_confidence": p["doc_confidence"],
                               "page_indices": [i]})

        unique_types = {g["doc_type"] for g in groups}

        # ── Single doc type → merged result ──────────────────────────────────
        if len(unique_types) == 1:
            doc_type = groups[0]["doc_type"]
            bank_name = next((p["bank_name"] for p in page_results if p.get("bank_name")), None)
            bank_code = next((p["bank_code"] for p in page_results if p.get("bank_code")), None)

            if doc_type == "bank_statement":
                all_txns: list[dict] = []
                metadata: dict = {}
                warnings: list[str] = []
                for p in page_results:
                    ext = p.get("extracted", {})
                    all_txns.extend(ext.get("transactions", []))
                    metadata.update(ext.get("metadata", {}))
                    warnings.extend(ext.get("warnings", []))
                seen: set = set()
                unique_txns: list[dict] = []
                for row in all_txns:
                    key = tuple(sorted(row.items()))
                    if key not in seen:
                        seen.add(key)
                        unique_txns.append(row)
                extracted: dict[str, Any] = {
                    "metadata": metadata, "transactions": unique_txns, "warnings": warnings}
            else:
                # Combine all OCR and re-parse for best field coverage
                all_ocr = [r for p in page_results for r in p.get("ocr_results", [])]
                extracted = self._route(all_ocr, doc_type, {
                    "bank_name": bank_name, "bank_code": bank_code})

            return {
                "doc_type":     doc_type,
                "bank_name":    bank_name,
                "bank_code":    bank_code,
                "pages":        len(images),
                "languages":    lang_info,
                "extracted":    extracted,
                "page_results": page_results,
            }

        # ── Multi-document PDF → grouped structure ────────────────────────────
        documents: list[dict] = []
        for g in groups:
            group_ocr = [r for i in g["page_indices"]
                         for r in page_results[i].get("ocr_results", [])]
            dummy: dict = {}
            group_extracted = self._route(group_ocr, g["doc_type"], dummy)
            doc_entry: dict[str, Any] = {
                "doc_type":   g["doc_type"],
                "confidence": round(g["doc_confidence"], 3),
                "pages":      [i + 1 for i in g["page_indices"]],
                "extracted":  {k: v for k, v in group_extracted.items()
                               if k not in ("raw_text", "doc_type")},
            }
            if dummy.get("bank_name"):
                doc_entry["bank_name"] = dummy["bank_name"]
                doc_entry["bank_code"] = dummy["bank_code"]
            documents.append(doc_entry)

        _crossref_identity_docs(documents)

        primary_group = max(groups, key=lambda g: g["doc_confidence"])
        return {
            "doc_type":     "multi_document",
            "doc_confidence": round(primary_group["doc_confidence"], 3),
            "pages":        len(images),
            "languages":    lang_info,
            "documents":    documents,
            "extracted":    {},
            "page_results": page_results,
        }
