"""Agreement to Sale / Bainanama / MOU for Property parser."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser
from parsers.realestate._helpers import (
    DISTRICT_RE,
    PIN_RE,
    STATE_RE,
    SURVEY_RE,
    clean_amount,
    norm_date,
    parse_amount,
    parse_area,
)

_AGR_DATE_RE   = re.compile(
    r"(?:agreement\s*dated?|this\s*agreement\s*(?:is\s*)?made|entered\s*into\s*on)"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.I,
)
_VENDOR_RE     = re.compile(
    r"(?:vendor|seller|owner|first\s*party|party\s*no\.?\s*1)[:\s]+"
    r"([A-Z][A-Za-z\s\.]+?)(?:\n|hereinafter|s/o|d/o|w/o|age|address)",
    re.I,
)
_PURCHASER_RE  = re.compile(
    r"(?:purchaser|buyer|second\s*party|party\s*no\.?\s*2)[:\s]+"
    r"([A-Z][A-Za-z\s\.]+?)(?:\n|hereinafter|s/o|d/o|w/o|age|address)",
    re.I,
)
_PRICE_RE      = re.compile(
    r"(?:total\s*(?:sale\s*)?consideration|agreed\s*(?:sale\s*)?price|"
    r"purchase\s*price|total\s*amount)[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_ADVANCE_RE    = re.compile(
    r"(?:advance|token\s*amount|earnest\s*money|booking\s*amount)[:\s]*"
    r"(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_BALANCE_RE    = re.compile(
    r"(?:balance\s*amount|remaining\s*amount|balance\s*(?:sale\s*)?consideration)"
    r"[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_POSS_DATE_RE  = re.compile(
    r"(?:possession\s*(?:shall\s*be\s*given|date|on)|date\s*of\s*possession)"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.I,
)
_COMPLETION_RE = re.compile(
    r"(?:completion\s*(?:date|period)|sale\s*deed\s*(?:shall\s*be\s*)?executed)"
    r"[:\s]*(?:within\s+)?(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d+\s+(?:months?|days?|years?))",
    re.I,
)
_WITNESS_RE    = re.compile(
    r"(?:witness\s*(?:no\.?\s*\d+)?|witnessed\s*by)[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|sign|address)",
    re.I,
)


class AgreementToSaleParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "agreement_to_sale"}

        m = _AGR_DATE_RE.search(text)
        if m:
            result["agreement_date"] = norm_date(m.group(1))

        m = _VENDOR_RE.search(text)
        if m:
            result["vendor_name"] = m.group(1).strip().title()

        m = _PURCHASER_RE.search(text)
        if m:
            result["purchaser_name"] = m.group(1).strip().title()

        m = _PRICE_RE.search(text)
        if m:
            result["agreed_price"] = clean_amount(m.group(1))
        else:
            amt = parse_amount(text)
            if amt:
                result["agreed_price"] = amt

        m = _ADVANCE_RE.search(text)
        if m:
            result["advance_paid"] = clean_amount(m.group(1))

        m = _BALANCE_RE.search(text)
        if m:
            result["balance_amount"] = clean_amount(m.group(1))

        m = _POSS_DATE_RE.search(text)
        if m:
            result["possession_date"] = norm_date(m.group(1))

        m = _COMPLETION_RE.search(text)
        if m:
            result["completion_period"] = m.group(1).strip()

        area = parse_area(text)
        if area:
            result["area"] = area

        m = SURVEY_RE.search(text)
        if m:
            result["survey_plot_number"] = m.group(1).strip()

        witnesses = [m.group(1).strip().title() for m in _WITNESS_RE.finditer(text)]
        if witnesses:
            result["witnesses"] = witnesses

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
