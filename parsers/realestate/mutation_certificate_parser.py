"""Mutation Certificate / Dakhil Kharij / Intkal / Jamabandi Mutation parser."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser
from parsers.realestate._helpers import (
    norm_date, parse_area, PIN_RE, STATE_RE, DISTRICT_RE, SURVEY_RE,
)

_MUT_NO_RE     = re.compile(
    r"(?:mutation\s*(?:no\.?|number)|dakhil\s*kharij\s*(?:no\.?|number)|"
    r"intkal\s*(?:no\.?|number)|case\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)",
    re.I,
)
_PREV_OWNER_RE = re.compile(
    r"(?:previous\s*owner|old\s*owner|khatedar|previous\s*occupant|transferor|"
    r"name\s*of\s*(?:the\s*)?deceased)[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|new|present|address|s/o)",
    re.I,
)
_NEW_OWNER_RE  = re.compile(
    r"(?:new\s*owner|present\s*owner|transferee|new\s*khatedar|name\s*of\s*(?:the\s*)?applicant)"
    r"[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|address|s/o|d/o|w/o|father|relation|area)",
    re.I,
)
_MUT_DATE_RE   = re.compile(
    r"(?:mutation\s*date|date\s*of\s*mutation|mutated\s*on)[:\s]*"
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_ORDER_DATE_RE = re.compile(
    r"(?:order\s*date|date\s*of\s*order|approved\s*on)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_REASON_RE     = re.compile(
    r"(?:reason\s*for\s*mutation|cause\s*of\s*mutation|mutation\s*type)[:\s]+"
    r"(sale|purchase|gift|inheritance|will|partition|court\s*decree|exchange|mortgage|rectification)",
    re.I,
)
_VILLAGE_RE    = re.compile(r"(?:village|gram|mauza)[:\s]+([A-Za-z\s]+?)(?:\n|tehsil|taluk|dist|halqa)", re.I)
_TEHSIL_RE     = re.compile(r"(?:tehsil|taluka|taluk|mandal|block)[:\s]+([A-Za-z\s]+?)(?:\n|district|state)", re.I)
_PROP_TYPE_RE  = re.compile(r"(?:property\s*type|land\s*type|nature\s*of\s*land)[:\s]+(residential|agricultural|commercial|industrial|vacant\s*land|plot)", re.I)
_PATWARI_RE    = re.compile(r"(?:patwari|revenue\s*officer|tehsildar)[:\s]+([A-Za-z\s\.]+?)(?:\n|sign|date|seal)", re.I)


class MutationCertificateParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "mutation_certificate"}

        m = _MUT_NO_RE.search(text)
        if m:
            result["mutation_number"] = m.group(1).strip()

        m = _PREV_OWNER_RE.search(text)
        if m:
            result["previous_owner"] = m.group(1).strip().title()

        m = _NEW_OWNER_RE.search(text)
        if m:
            result["new_owner"] = m.group(1).strip().title()

        m = _MUT_DATE_RE.search(text)
        if m:
            result["mutation_date"] = norm_date(m.group(1))

        m = _ORDER_DATE_RE.search(text)
        if m:
            result["order_date"] = norm_date(m.group(1))

        m = _REASON_RE.search(text)
        if m:
            result["mutation_reason"] = m.group(1).strip().title()

        area = parse_area(text)
        if area:
            result["area"] = area

        m = SURVEY_RE.search(text)
        if m:
            result["survey_khasra_number"] = m.group(1).strip()

        m = _VILLAGE_RE.search(text)
        if m:
            result["village"] = m.group(1).strip().title()

        m = _TEHSIL_RE.search(text)
        if m:
            result["tehsil"] = m.group(1).strip().title()

        m = _PROP_TYPE_RE.search(text)
        if m:
            result["property_type"] = m.group(1).strip().title()

        m = _PATWARI_RE.search(text)
        if m:
            result["revenue_officer"] = m.group(1).strip().title()

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
