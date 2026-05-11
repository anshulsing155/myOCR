"""Legal Heir Certificate / Succession Certificate / Survivorship Certificate parser."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser
from parsers.realestate._helpers import (
    DISTRICT_RE,
    PIN_RE,
    STATE_RE,
    norm_date,
)

_CERT_TYPE_RE  = re.compile(
    r"\b(legal\s*heir\s*certificate|succession\s*certificate|survivorship\s*certificate|"
    r"heirship\s*certificate|legal\s*heirship\s*certificate)\b",
    re.I,
)
_CERT_NO_RE    = re.compile(r"(?:certificate\s*(?:no\.?|number)|case\s*(?:no\.?|number)|ref(?:erence)?\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)", re.I)
_DECEASED_RE   = re.compile(
    r"(?:late|deceased|departed)\s*(?:shri|smt|shrimati|mr\.?|mrs\.?|ms\.?)?\s*"
    r"([A-Z][A-Za-z\s\.]+?)(?:\n|who\s*died|s/o|d/o|w/o|age|date\s*of\s*death|died\s*on)",
    re.I,
)
_DECEASED_NAME_RE = re.compile(
    r"(?:name\s*of\s*(?:the\s*)?deceased|deceased(?:'s)?\s*name)[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|date|age|address)",
    re.I,
)
_DOD_RE        = re.compile(
    r"(?:date\s*of\s*death|died\s*on|death\s*date|expired\s*on)"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.I,
)
_PLACE_DEATH_RE = re.compile(r"(?:place\s*of\s*death|died\s*at)[:\s]+([A-Za-z\s,]+?)(?:\n|date|legal|heir)", re.I)
_ISSUE_DATE_RE  = re.compile(r"(?:issued?\s*(?:on|date)|date\s*of\s*issue)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})", re.I)
_AUTHORITY_RE  = re.compile(
    r"(?:issued?\s*by|issuing\s*authority|revenue\s*officer|tehsildar|court|municipal)[:\s]+"
    r"([A-Za-z\s,\.]+?)(?:\n|date|sign|seal|stamp)",
    re.I,
)
# Heir row: name | relation | age [| share]
_HEIR_ROW_RE   = re.compile(
    r"(\d+\.?\s+)?([A-Z][A-Za-z\s\.]{3,30})\s+"
    r"(son|daughter|wife|husband|mother|father|brother|sister|grandson|granddaughter|"
    r"legal\s*heir|dependent|widow|widower)"
    r"(?:\s+(\d{1,3})(?:\s*(?:years?|yrs?))?)?"
    r"(?:\s+([0-9/]+\s*(?:share)?))?",
    re.I,
)
_ADDRESS_RE    = re.compile(
    r"(?:address|residence|residing\s*at|permanent\s*address)[:\s]+"
    r"([A-Za-z0-9\s,/\-\.]+?)(?:\n\n|\d{6}|state|district|deceased|legal)",
    re.I,
)


class LegalHeirCertificateParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "legal_heir_certificate"}

        m = _CERT_TYPE_RE.search(text)
        if m:
            result["certificate_type"] = m.group(1).strip().title()

        m = _CERT_NO_RE.search(text)
        if m:
            result["certificate_number"] = m.group(1).strip()

        # Deceased person's name
        m = _DECEASED_NAME_RE.search(text) or _DECEASED_RE.search(text)
        if m:
            result["deceased_name"] = m.group(1).strip().title()

        m = _DOD_RE.search(text)
        if m:
            result["date_of_death"] = norm_date(m.group(1))

        m = _PLACE_DEATH_RE.search(text)
        if m:
            result["place_of_death"] = m.group(1).strip().title()

        m = _ISSUE_DATE_RE.search(text)
        if m:
            result["issue_date"] = norm_date(m.group(1))

        m = _AUTHORITY_RE.search(text)
        if m:
            result["issued_by"] = m.group(1).strip().title()

        m = _ADDRESS_RE.search(text)
        if m:
            result["address"] = re.sub(r"\s+", " ", m.group(1)).strip()

        # Legal heirs
        heirs = []
        for hm in _HEIR_ROW_RE.finditer(text):
            heir: dict[str, str] = {
                "name":     hm.group(2).strip().title(),
                "relation": hm.group(3).strip().title(),
            }
            if hm.group(4):
                heir["age"] = hm.group(4).strip()
            if hm.group(5):
                heir["share"] = hm.group(5).strip()
            if len(heir["name"]) >= 3:
                heirs.append(heir)
        if heirs:
            result["legal_heirs"] = heirs

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
