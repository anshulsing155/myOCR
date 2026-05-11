"""Property Tax Receipt / House Tax Receipt parser."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser
from parsers.realestate._helpers import (
    DISTRICT_RE,
    PIN_RE,
    STATE_RE,
    clean_amount,
    norm_date,
)

_ASSESS_NO_RE  = re.compile(
    r"(?:assessment\s*(?:no\.?|number)|property\s*(?:id|no\.?|number|tax\s*no\.?)|"
    r"account\s*(?:no\.?|number)|ptin)[:\s]+([A-Z0-9/\-]+)",
    re.I,
)
_OWNER_RE      = re.compile(
    r"(?:owner(?:'s)?\s*name|name\s*of\s*(?:the\s*)?owner|assessee)[:\s]+"
    r"([A-Z][A-Za-z\s\.]+?)(?:\n|address|property|ward|zone|area)",
    re.I,
)
_PROP_ADDR_RE  = re.compile(
    r"(?:property\s*address|house\s*(?:no\.?|number)|door\s*(?:no\.?|number)|"
    r"plot\s*(?:no\.?|number))[:\s]+([A-Za-z0-9\s,/\-\.#]+?)(?:\n|ward|zone|\d{6}|owner)",
    re.I,
)
_ASSESS_YEAR_RE = re.compile(r"(?:assessment\s*year|financial\s*year|tax\s*year)[:\s]+(\d{4}[-\-]\d{2,4})", re.I)
_TAX_AMT_RE    = re.compile(
    r"(?:current\s*(?:year\s*)?tax|property\s*tax\s*(?:amount)?|annual\s*tax)"
    r"[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_ARREARS_RE    = re.compile(
    r"(?:arrears?|outstanding)[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_PENALTY_RE    = re.compile(
    r"(?:penalty|interest|fine)[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_TOTAL_RE      = re.compile(
    r"(?:total\s*(?:amount\s*)?(?:paid|payable|due)?|net\s*payable)"
    r"[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_RECEIPT_RE    = re.compile(r"(?:receipt\s*(?:no\.?|number)|txn\s*(?:no\.?|id))[:\s]+([A-Z0-9/\-]+)", re.I)
_PAY_DATE_RE   = re.compile(
    r"(?:payment\s*date|paid\s*on|date\s*of\s*payment)[:\s]*"
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_PAY_MODE_RE   = re.compile(r"(?:mode\s*of\s*payment|payment\s*mode|paid\s*via)[:\s]+(cash|cheque|online|upi|neft|rtgs|dd|card)", re.I)
_MUNICIPAL_RE  = re.compile(
    r"(municipal\s*corporation|municipal\s*council|gram\s*panchayat|"
    r"nagar\s*(?:panchayat|palika|nigam)|bbmp|mcgm|bmc|ndmc|sdmc|edmc|nmmc|"
    r"pmc|kmc|cmda|ghmc|vmrda)[A-Za-z\s,]*",
    re.I,
)
_WARD_RE       = re.compile(r"(?:ward\s*(?:no\.?|number)|zone)[:\s]+([A-Za-z0-9\s\-]+?)(?:\n|property|owner)", re.I)


class PropertyTaxParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "property_tax_receipt"}

        m = _ASSESS_NO_RE.search(text)
        if m:
            result["assessment_number"] = m.group(1).strip()

        m = _OWNER_RE.search(text)
        if m:
            result["owner_name"] = m.group(1).strip().title()

        m = _PROP_ADDR_RE.search(text)
        if m:
            result["property_address"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = _ASSESS_YEAR_RE.search(text)
        if m:
            result["assessment_year"] = m.group(1)

        m = _TAX_AMT_RE.search(text)
        if m:
            result["tax_amount"] = clean_amount(m.group(1))

        m = _ARREARS_RE.search(text)
        if m:
            result["arrears_amount"] = clean_amount(m.group(1))

        m = _PENALTY_RE.search(text)
        if m:
            result["penalty_amount"] = clean_amount(m.group(1))

        m = _TOTAL_RE.search(text)
        if m:
            total = clean_amount(m.group(1))
            result["total_paid"] = total
            result["total_amount"] = total

        m = _RECEIPT_RE.search(text)
        if m:
            result["receipt_number"] = m.group(1).strip()

        m = _PAY_DATE_RE.search(text)
        if m:
            result["payment_date"] = norm_date(m.group(1))

        m = _PAY_MODE_RE.search(text)
        if m:
            result["payment_mode"] = m.group(1).strip().title()

        m = _MUNICIPAL_RE.search(text)
        if m:
            result["municipal_body"] = m.group(0).strip().title()

        m = _WARD_RE.search(text)
        if m:
            result["ward"] = m.group(1).strip()

        m = DISTRICT_RE.search(text)
        if m:
            result["district"] = m.group(1).strip().title()

        m = STATE_RE.search(text)
        if m:
            result["state"] = m.group(1).strip().title()

        m = PIN_RE.search(text)
        if m:
            result["pin_code"] = m.group(1)

        result["raw_text"] = text
        return result
