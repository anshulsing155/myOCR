"""Universal Gemini Vision OCR — supports every Indian document type."""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_GEMINI_MODEL = "gemini-2.5-flash"
_MAX_PAGES = 20

# ── Universal extraction prompt ───────────────────────────────────────────────

_UNIVERSAL_PROMPT = """\
You are a document intelligence expert specialising in Indian official documents.

Analyse the provided image(s) and return ONLY a valid JSON object.

Output structure:
{
  "doc_type": "<type from list below>",
  "doc_confidence": <0.0-1.0>,
  "extracted": { ...all visible fields... }
}

Supported doc_type values (pick the best match):
  pan_card | aadhaar | driving_licence | voter_id | passport | vehicle_rc |
  ration_card | eshram | ayushman_card |
  bank_statement | salary_slip | itr | gst_certificate | ppo | invoice |
  birth_certificate | marriage_certificate | caste_certificate |
  income_certificate | domicile_certificate | marksheet | degree_certificate |
  sale_deed | agreement_to_sale | gift_deed | mortgage_deed | lease_deed |
  partition_deed | power_of_attorney | encumbrance_certificate |
  rera_certificate | property_tax_receipt | property_valuation |
  khata_certificate | land_record | possession_letter | mutation_certificate |
  occupancy_certificate | legal_heir_certificate | home_loan_sanction |
  estamp_certificate | unknown

━━━━━━ GENERAL RULES ━━━━━━
• Dates → DD/MM/YYYY
• Amounts → plain decimal, no commas ("1,45,000" → "145000.00")
• Preserve Aadhaar masking ("XXXX XXXX 1234")
• Omit fields not visible in the document — do NOT invent values
• Return valid JSON only — no markdown fences, no commentary

━━━━━━ FIELD SCHEMAS BY TYPE ━━━━━━

pan_card →
  pan_number, name, father_name, date_of_birth,
  holder_type (individual | company | huf | firm)

aadhaar →
  aadhaar_number, vid, name, date_of_birth, gender,
  address, pin_code, state

driving_licence →
  dl_number, name, date_of_birth, date_of_issue, valid_till,
  vehicle_classes (list), blood_group, address, state

voter_id →
  epic_number, name, father_husband_name, date_of_birth, gender,
  address, constituency, state

passport →
  passport_number, surname, given_name, nationality, date_of_birth, sex,
  place_of_birth, date_of_issue, place_of_issue, valid_till,
  father_name, mother_name, mrz_line1, mrz_line2

vehicle_rc →
  registration_number, owner_name, chassis_number, engine_number,
  class_of_vehicle, fuel_type, date_of_registration, valid_till, rto_code, address

ration_card →
  card_number, category (AAY | BPL | PHH | APL), head_of_family,
  address, total_units, members (list of names)

eshram →
  uan, name, date_of_birth, gender, blood_group, occupation,
  contact_number, address, pin_code, state, registration_date

ayushman_card →
  beneficiary_id, name, age, gender, family_id, state, scheme_name

bank_statement →
  bank_name, account_number, account_holder, ifsc_code, branch,
  statement_from, statement_to, opening_balance, closing_balance,
  transactions (list: date, narration, chq_ref, debit, credit, balance),
  transaction_count
  CRITICAL — Indian number format: comma is a THOUSANDS separator, NOT decimal.
  "45,000.00" = 45000 · "1,40,000.00" = 140000
  Output amounts as plain decimals, remove ALL commas, keep the decimal point.

salary_slip →
  employee_name, employee_id, month, designation, department, location,
  pan, pf_account, bank_account, ifsc_code,
  earnings (dict: component → amount),
  deductions (dict: component → amount),
  gross_salary, total_deductions, net_salary

itr →
  pan, assessment_year, acknowledgement_number, name, filing_date,
  gross_total_income, total_income, taxable_income,
  tax_payable, interest, total_tax, taxes_paid, refund

gst_certificate →
  gstin, legal_name, trade_name, taxpayer_type, state, pin_code,
  date_of_registration, principal_place_of_business, nature_of_business

ppo →
  ppo_number, pensioner_name, designation, department, date_of_retirement,
  pension_type, basic_pension, bank_name, account_number, ifsc_code

invoice →
  seller_name, seller_gstin, buyer_name, buyer_gstin,
  invoice_number, invoice_date, place_of_supply,
  items (list: description, hsn_sac, qty, rate, amount),
  subtotal, cgst, sgst, igst, total_amount

birth_certificate →
  name, date_of_birth, sex, place_of_birth, father_name, mother_name,
  registration_number, registration_date, issuing_authority

marriage_certificate →
  bride_name, groom_name, bride_dob, groom_dob, date_of_marriage,
  place_of_marriage, registration_number, registration_date, issuing_authority

degree_certificate →
  student_name, degree, specialisation, institution, university,
  year_of_passing, roll_number

marksheet →
  student_name, roll_number, board, class, year,
  subjects (dict: subject → marks), total_marks, percentage, result

income_certificate →
  name, date_of_birth, address, annual_income, financial_year,
  certificate_number, issuing_authority, issue_date

caste_certificate →
  name, date_of_birth, caste, sub_caste,
  category (SC | ST | OBC | General), father_name, address,
  certificate_number, issuing_authority, issue_date

domicile_certificate →
  name, date_of_birth, permanent_address, state,
  certificate_number, issuing_authority, issue_date

sale_deed | agreement_to_sale | gift_deed | mortgage_deed | lease_deed |
partition_deed | power_of_attorney →
  parties (list: name, role, address), property_description, survey_number,
  area, consideration_amount, stamp_duty, registration_date,
  registration_number, sro

encumbrance_certificate →
  property_description, survey_number, owner_name, period_from, period_to,
  encumbrances (list: date, nature, parties, amount)

rera_certificate →
  project_name, developer_name, rera_number, project_type,
  location, completion_date, registration_date

property_tax_receipt →
  property_id, owner_name, property_address, ward,
  tax_amount, payment_date, period_from, period_to, receipt_number

property_valuation →
  property_address, survey_number, owner_name,
  valuation_amount, purpose, valuer_name, valuation_date

khata_certificate →
  khata_number, owner_name, property_details, ward, municipality, area, site_number

land_record →
  survey_number, owner_name, area, land_use, taluk, district,
  type (jamabandi | 7-12 | patta | rdc | khatauni | khasra)

possession_letter →
  buyer_name, developer_name, project_name, unit_number,
  possession_date, consideration_paid, balance_due, address

mutation_certificate →
  mutation_number, previous_owner, new_owner, property_reference,
  mutation_date, issuing_authority

occupancy_certificate →
  building_name, developer_name, location, authority,
  certificate_number, issue_date, completion_date

legal_heir_certificate →
  deceased_name, deceased_dob, date_of_death,
  heirs (list: name, relation, dob),
  certificate_number, issuing_authority, issue_date

home_loan_sanction →
  borrower_name, co_borrower, lender_name, loan_amount, loan_type,
  tenure_months, interest_rate, emi, property_address, sanction_date

estamp_certificate →
  stamp_number, purchaser_name, first_party, second_party,
  purpose, stamp_duty_amount, issue_date, state

━━━━━━ MULTI-DOCUMENT PDFs ━━━━━━
If pages contain DIFFERENT document types (e.g. page 1 = PAN card, page 2 = Aadhaar),
return ALL of them using this array format:
{
  "documents": [
    { "doc_type": "pan_card",  "doc_confidence": 1.0,  "pages": [1], "extracted": {...} },
    { "doc_type": "aadhaar",   "doc_confidence": 0.98, "pages": [2], "extracted": {...} }
  ]
}
Use the "documents" array ONLY when genuinely different document types are on separate pages.
For a single document type (even spanning many pages), use the standard single-document format.
"""

# ── Shared helpers ────────────────────────────────────────────────────────────

def _encode_image(img: np.ndarray, max_dim: int = 2400) -> tuple[bytes, str]:
    import cv2  # lazy: only needed when Vision AI path is active
    h, w = img.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)),
                         interpolation=cv2.INTER_LANCZOS4)
    ok, buf = cv2.imencode(".png", img, [cv2.IMWRITE_PNG_COMPRESSION, 1])
    if not ok:
        raise ValueError("Failed to encode image as PNG")
    return buf.tobytes(), "image/png"


def _parse_response(text: str) -> dict:
    """Parse JSON from AI response; recovers from truncation."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    positions = [i for i, c in enumerate(text) if c == "}"]
    for pos in reversed(positions):
        candidate = text[: pos + 1]
        open_b  = candidate.count("[") - candidate.count("]")
        open_br = candidate.count("{") - candidate.count("}")
        if open_b < 0 or open_br < 0:
            continue
        candidate += "]" * open_b + "}" * open_br
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise json.JSONDecodeError("Could not parse AI response", text, 0)


def _clean_amounts(extracted: dict) -> dict:
    """Strip thousand-separator commas from known amount fields."""
    _amount_keys = {
        "gross_salary", "net_salary", "total_deductions", "tax_payable",
        "taxes_paid", "refund", "basic_pension", "stamp_duty",
        "stamp_duty_amount", "consideration_amount", "valuation_amount",
        "loan_amount", "emi", "opening_balance", "closing_balance",
        "subtotal", "total_amount",
    }
    for key in _amount_keys:
        if key in extracted:
            extracted[key] = str(extracted[key]).replace(",", "").strip()
    for txn in extracted.get("transactions", []):
        for fld in ("debit", "credit", "balance"):
            if fld in txn:
                txn[fld] = str(txn[fld]).replace(",", "").strip()
    for item in extracted.get("items", []):
        for fld in ("rate", "amount"):
            if fld in item:
                item[fld] = str(item[fld]).replace(",", "").strip()
    return extracted


# ── Main class ────────────────────────────────────────────────────────────────

class GeminiDocumentOCR:
    """Universal Gemini Vision extractor — any Indian document type."""

    def __init__(self, api_key: str, model: str = _GEMINI_MODEL):
        self._model = model
        try:
            import google.genai as genai
            from google.genai import types as genai_types
            self._client    = genai.Client(api_key=api_key)
            self._types     = genai_types
            self._available = True
        except ImportError:
            logger.error("google-genai not installed. Run: pip install google-genai")
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def extract(
        self,
        images: list[np.ndarray],
        doc_type: str = "auto",
        **context: Any,
    ) -> dict[str, Any]:
        """Extract structured data from document image(s).

        Args:
            images:   BGR numpy arrays, one per page.
            doc_type: "auto" — Gemini detects the type and extracts;
                      or pass an explicit type to guide extraction.
            context:  Optional hints — bank_hint="HDFC", etc.

        Returns standard envelope:
            { doc_type, doc_confidence, extraction_method, extracted,
              gemini_model, pages_processed, response_time_sec }
        """
        if not self._available:
            return {"error": "google-genai not available"}
        if not images:
            return {"error": "No images provided"}

        t0    = time.perf_counter()
        pages = images[:_MAX_PAGES]

        prompt = _UNIVERSAL_PROMPT
        if doc_type != "auto":
            readable = doc_type.replace("_", " ")
            prompt += (
                f'\n\nIMPORTANT: This document is a {readable}. '
                f'Set "doc_type" to "{doc_type}" in the response.'
            )
        if context.get("bank_hint"):
            prompt += f"\nBank hint: this is a {context['bank_hint'].upper()} bank statement."

        parts: list = []
        for i, img in enumerate(pages):
            try:
                img_bytes, mime = _encode_image(img)
                parts.append(
                    self._types.Part.from_bytes(data=img_bytes, mime_type=mime)
                )
            except Exception as exc:
                logger.warning("Page %d encode failed: %s", i + 1, exc)

        if not parts:
            return {"error": "All pages failed to encode"}
        parts.append(prompt)

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=parts,
                config=self._types.GenerateContentConfig(
                    temperature=0,
                    max_output_tokens=8192,
                ),
            )
            raw_text = response.text
        except Exception as exc:
            logger.error("Gemini API error: %s", exc)
            return {"error": str(exc)}

        elapsed = round(time.perf_counter() - t0, 2)

        try:
            result = _parse_response(raw_text)
        except json.JSONDecodeError as exc:
            return {"error": f"JSON parse failed: {exc}", "raw_response": raw_text[:500]}

        # ── Multi-document response ────────────────────────────────────────────
        if "documents" in result and isinstance(result["documents"], list):
            docs = result["documents"]
            for d in docs:
                d["extracted"] = _clean_amounts(d.get("extracted", {}))
                if d.get("doc_type") == "bank_statement":
                    txns = d["extracted"].get("transactions", [])
                    d["extracted"].setdefault("transaction_count", len(txns))
                d.setdefault("pages", [])
                d.setdefault("doc_confidence", 0.9)
            return {
                "doc_type":          "multi_document",
                "doc_confidence":    max((d["doc_confidence"] for d in docs), default=0.9),
                "extracted":         {},
                "documents":         docs,
                "extraction_method": "gemini_vision",
                "gemini_model":      self._model,
                "pages_processed":   len(pages),
                "response_time_sec": elapsed,
            }

        # ── Single-document response ───────────────────────────────────────────
        extracted = _clean_amounts(result.get("extracted", {}))
        if result.get("doc_type") == "bank_statement":
            txns = extracted.get("transactions", [])
            extracted.setdefault("transaction_count", len(txns))

        result["extracted"]         = extracted
        result.setdefault("doc_confidence", 0.9)
        result.setdefault("doc_type", doc_type if doc_type != "auto" else "unknown")
        result["extraction_method"] = "gemini_vision"
        result["gemini_model"]      = self._model
        result["pages_processed"]   = len(pages)
        result["response_time_sec"] = elapsed
        return result

    def extract_pdf(
        self,
        pdf_path: str,
        doc_type: str = "auto",
        **context: Any,
    ) -> dict[str, Any]:
        from utils.pdf_to_image import pdf_to_images
        try:
            images = pdf_to_images(pdf_path)
        except Exception as exc:
            return {"error": f"PDF rendering failed: {exc}"}
        if not images:
            return {"error": f"No pages rendered from {pdf_path}"}
        return self.extract(images, doc_type=doc_type, **context)
