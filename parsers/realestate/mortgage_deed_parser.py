"""Mortgage Deed / Deed of Hypothecation / Simple Mortgage parser."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser
from parsers.realestate._helpers import (
    norm_date, parse_area, clean_amount, PIN_RE, STATE_RE, DISTRICT_RE,
    SRO_RE, STAMP_RE, REGN_NO_RE, SURVEY_RE, IFSC_RE,
)

_DEED_TYPE_RE  = re.compile(
    r"\b(mortgage\s*deed|simple\s*mortgage|equitable\s*mortgage|usufructuary\s*mortgage|"
    r"deed\s*of\s*mortgage|hypothecation\s*(?:deed|agreement)|deed\s*of\s*hypothecation)\b",
    re.I,
)
_EXEC_DATE_RE  = re.compile(
    r"(?:executed?\s*(?:on|this)|this\s*deed\s*(?:is\s*)?(?:made|dated?))"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.I,
)
_REG_DATE_RE   = re.compile(
    r"(?:registered?\s*on|registration\s*date)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_MORTGAGOR_RE  = re.compile(
    r"(?:mortgagor|borrower|debtor|hypothecator|first\s*party)"
    r"[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|hereinafter|s/o|d/o|w/o|age|address|mortgagee)",
    re.I,
)
_MORTGAGEE_RE  = re.compile(
    r"(?:mortgagee|lender|creditor|bank|financial\s*institution|second\s*party)"
    r"[:\s]+([A-Za-z0-9\s,\.\-&]+?)(?:\n|hereinafter|address|loan|mortgagor|branch)",
    re.I,
)
_LOAN_AMT_RE   = re.compile(
    r"(?:loan\s*amount|principal\s*amount|sum\s*(?:of\s*)?(?:rs\.?|inr)?|"
    r"borrowed\s*(?:amount|sum)|sanctioned\s*amount)"
    r"[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_ROI_RE        = re.compile(
    r"(?:rate\s*of\s*interest|interest\s*rate|roi)[:\s]*([\d\.]+)\s*%",
    re.I,
)
_TENURE_RE     = re.compile(
    r"(?:repayment\s*period|loan\s*tenure|tenure|repayment\s*(?:in|over))"
    r"[:\s]+(\d+)\s*(months?|years?)",
    re.I,
)
_EMI_RE        = re.compile(
    r"(?:emi|monthly\s*instalment|equated\s*monthly)"
    r"[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_PROP_DESC_RE  = re.compile(
    r"(?:property\s*(?:described|situated|known\s*as|bearing|mortgaged)|"
    r"the\s*schedule\s*(?:property|premises)|mortgaged\s*property)"
    r"[:\s]+([A-Za-z0-9\s,/\-\.#]+?)(?:\n\n|measuring|bounded|stamp|loan)",
    re.I,
)
_EQUITABLE_RE  = re.compile(r"\bequitable\s*mortgage\b", re.I)
_BANK_ACC_RE   = re.compile(r"(?:account\s*(?:no\.?|number)|loan\s*account)[:\s]+(\d{8,18})", re.I)


class MortgageDeedParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "mortgage_deed"}

        m = _DEED_TYPE_RE.search(text)
        if m:
            result["deed_type"] = m.group(1).strip().title()

        result["equitable_mortgage"] = bool(_EQUITABLE_RE.search(text))

        m = REGN_NO_RE.search(text)
        if m:
            result["registration_number"] = m.group(1).strip()

        m = _EXEC_DATE_RE.search(text)
        if m:
            result["execution_date"] = norm_date(m.group(1))

        m = _REG_DATE_RE.search(text)
        if m:
            result["registration_date"] = norm_date(m.group(1))

        m = _MORTGAGOR_RE.search(text)
        if m:
            result["mortgagor_name"] = m.group(1).strip().title()

        m = _MORTGAGEE_RE.search(text)
        if m:
            result["mortgagee_name"] = m.group(1).strip().title()

        m = _LOAN_AMT_RE.search(text)
        if m:
            result["loan_amount"] = clean_amount(m.group(1))

        m = _ROI_RE.search(text)
        if m:
            result["interest_rate"] = m.group(1)

        m = _TENURE_RE.search(text)
        if m:
            result["repayment_period"] = f"{m.group(1)} {m.group(2)}"

        m = _EMI_RE.search(text)
        if m:
            result["emi_amount"] = clean_amount(m.group(1))

        m = _PROP_DESC_RE.search(text)
        if m:
            result["property_description"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = SURVEY_RE.search(text)
        if m:
            result["survey_plot_number"] = m.group(1).strip()

        area = parse_area(text)
        if area:
            result["area"] = area

        m = _BANK_ACC_RE.search(text)
        if m:
            result["loan_account_number"] = m.group(1)

        m = IFSC_RE.search(text)
        if m:
            result["ifsc_code"] = m.group(1)

        m = STAMP_RE.search(text)
        if m:
            result["stamp_duty"] = clean_amount(m.group(1))

        m = SRO_RE.search(text)
        if m:
            result["sub_registrar_office"] = m.group(1).strip().title()

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
