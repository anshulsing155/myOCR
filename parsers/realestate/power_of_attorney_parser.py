"""Power of Attorney (General / Special / Specific) parser."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser
from parsers.realestate._helpers import (
    DISTRICT_RE,
    PIN_RE,
    REGN_NO_RE,
    SRO_RE,
    STAMP_RE,
    STATE_RE,
    SURVEY_RE,
    clean_amount,
    norm_date,
)

_POA_TYPE_RE   = re.compile(
    r"\b(general\s*power\s*of\s*attorney|special\s*power\s*of\s*attorney|"
    r"specific\s*power\s*of\s*attorney|irrevocable\s*power\s*of\s*attorney|gpa|spa)\b",
    re.I,
)
_EXEC_DATE_RE  = re.compile(
    r"(?:executed?\s*(?:on|this)|this\s*power\s*of\s*attorney\s*(?:is\s*)?(?:made|dated?))"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.I,
)
_REG_DATE_RE   = re.compile(
    r"(?:registered?\s*on|registration\s*date)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_PRINCIPAL_RE  = re.compile(
    r"(?:principal|grantor|donor|constituted\s*attorney\s*by|executant|i\s*/\s*we)"
    r"[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|hereinafter|s/o|d/o|w/o|age|aged|address|resident)",
    re.I,
)
_ATTORNEY_RE   = re.compile(
    r"(?:attorney|agent|donee|constituted\s*attorney\s*as|second\s*party)"
    r"[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|hereinafter|s/o|d/o|w/o|age|aged|address|resident)",
    re.I,
)
_POWERS_RE     = re.compile(
    r"(?:powers?\s*(?:granted|conferred|given)|do\s*hereby\s*authorise|hereby\s*authorise)"
    r"[:\s]+([A-Za-z\s,;:\n]+?)(?:\n{2,}|stamp|witness|sign|registration|in\s*witness)",
    re.I,
)
_VALIDITY_RE   = re.compile(
    r"(?:valid\s*(?:till|upto|until|for)|validity\s*period)"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d+\s*(?:years?|months?))",
    re.I,
)
_PROP_DESC_RE  = re.compile(
    r"(?:property\s*(?:described|situated|known\s*as|bearing)|the\s*schedule\s*property)"
    r"[:\s]+([A-Za-z0-9\s,/\-\.#]+?)(?:\n\n|measuring|bounded|stamp|witness)",
    re.I,
)


class PowerOfAttorneyParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "power_of_attorney"}

        m = _POA_TYPE_RE.search(text)
        if m:
            result["poa_type"] = m.group(1).strip().upper().replace(" ", "_")

        m = REGN_NO_RE.search(text)
        if m:
            result["registration_number"] = m.group(1).strip()

        m = _EXEC_DATE_RE.search(text)
        if m:
            result["execution_date"] = norm_date(m.group(1))

        m = _REG_DATE_RE.search(text)
        if m:
            result["registration_date"] = norm_date(m.group(1))

        m = _PRINCIPAL_RE.search(text)
        if m:
            result["principal_name"] = m.group(1).strip().title()

        m = _ATTORNEY_RE.search(text)
        if m:
            result["attorney_name"] = m.group(1).strip().title()

        m = _POWERS_RE.search(text)
        if m:
            raw_powers = re.sub(r"\s+", " ", m.group(1)).strip()
            result["powers_granted"] = raw_powers[:500]

        m = _VALIDITY_RE.search(text)
        if m:
            result["validity"] = m.group(1).strip()

        m = _PROP_DESC_RE.search(text)
        if m:
            result["property_description"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = SURVEY_RE.search(text)
        if m:
            result["survey_plot_number"] = m.group(1).strip()

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
