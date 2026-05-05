"""Encumbrance Certificate (EC) parser — Sub-Registrar Office."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser
from parsers.realestate._helpers import (
    norm_date, clean_amount,
    PIN_RE, STATE_RE, DISTRICT_RE, SRO_RE, SURVEY_RE, DATE_RE,
)

_EC_NO_RE      = re.compile(
    r"(?:ec\s*(?:no\.?|number)|encumbrance\s*(?:no\.?|number)|certificate\s*(?:no\.?|number))"
    r"[:\s]+([A-Z0-9/\-]+)",
    re.I,
)
_PERIOD_FROM_RE = re.compile(
    r"(?:from\s*(?:date)?|period\s*from)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_PERIOD_TO_RE  = re.compile(
    r"(?:to\s*(?:date)?|period\s*to|upto)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_ISSUE_DATE_RE = re.compile(
    r"(?:issued?\s*on|date\s*of\s*issue|issue\s*date)[:\s]*"
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_NIL_RE        = re.compile(r"\bnil\s*encumbrance\b|\bno\s*encumbrance\b", re.I)
_ENCUMB_ROW_RE = re.compile(
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\s+"       # date
    r"([A-Za-z\s]+?)\s+"                                 # nature (sale/mortgage/etc.)
    r"([A-Z][A-Za-z\s\.]+?)\s+"                          # party name
    r"(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",         # amount
    re.I,
)
_PROP_RE       = re.compile(
    r"(?:property\s*(?:details?|description|address|bearing)|door\s*(?:no\.?|number))"
    r"[:\s]+([A-Za-z0-9\s,/\-\.#]+?)(?:\n|survey|khasra|area|period)",
    re.I,
)


class EncumbranceCertificateParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "encumbrance_certificate"}

        m = _EC_NO_RE.search(text)
        if m:
            result["certificate_number"] = m.group(1).strip()

        m = _PERIOD_FROM_RE.search(text)
        if m:
            result["period_from"] = norm_date(m.group(1))

        m = _PERIOD_TO_RE.search(text)
        if m:
            result["period_to"] = norm_date(m.group(1))

        m = _ISSUE_DATE_RE.search(text)
        if m:
            result["issue_date"] = norm_date(m.group(1))

        result["nil_encumbrance"] = bool(_NIL_RE.search(text))

        m = _PROP_RE.search(text)
        if m:
            result["property_details"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = SURVEY_RE.search(text)
        if m:
            result["survey_plot_number"] = m.group(1).strip()

        m = SRO_RE.search(text)
        if m:
            result["sub_registrar_office"] = m.group(1).strip().title()

        encumbrances = []
        for em in _ENCUMB_ROW_RE.finditer(text):
            encumbrances.append({
                "date":   norm_date(em.group(1)),
                "nature": em.group(2).strip().title(),
                "party":  em.group(3).strip().title(),
                "amount": clean_amount(em.group(4)),
            })
        if encumbrances:
            result["encumbrances"] = encumbrances

        m = DISTRICT_RE.search(text)
        if m:
            result["district"] = m.group(1).strip().title()

        m = STATE_RE.search(text)
        if m:
            result["state"] = m.group(1).strip().title()

        result["raw_text"] = text
        return result
