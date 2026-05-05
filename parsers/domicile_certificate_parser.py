"""Domicile / Residence Certificate parser."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

_CERT_NO_RE   = re.compile(
    r"(?:certificate\s*(?:no\.?|number)|ref(?:erence)?\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)",
    re.I
)
_NAME_LBL_RE  = re.compile(
    r"(?:name\s*of\s*(?:the\s*)?applicant|this\s+is\s+to\s+certify\s+that\s+(?:shri|smt|kumari|mr\.?|ms\.?)?\s*)([A-Z][A-Za-z\s\.]+?)(?:\n|,|son|daughter|s/o|d/o|w/o|age|is\s+a|has\s+been|resident)",
    re.I
)
_DOB_RE       = re.compile(
    r"(?:date\s*of\s*birth|dob)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I
)
_RELATION_RE  = re.compile(
    r"\b(?:s/o|d/o|w/o|son\s+of|daughter\s+of|wife\s+of|father[:\s]+)[:\s]+([A-Z][A-Za-z\s]+?)(?:\n|,|age|res|dist)",
    re.I
)
_PERIOD_RE    = re.compile(
    r"(?:resident\s*(?:of|since|for)|residing\s*(?:in|at|since))[:\s]+(?:last\s+)?(\d+\s*year|since\s*\d{4})",
    re.I
)
_ADDRESS_RE   = re.compile(
    r"(?:permanent\s*address|present\s*address|address|residence|residing\s*at)[:\s]+"
    r"([A-Za-z0-9\s,/\-\.]+?)(?:\n\n|\d{6}|dist|state)",
    re.I
)
_ISSUE_DATE_RE = re.compile(
    r"(?:date\s*of\s*issue|issued?\s*on)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I
)
_VALID_RE     = re.compile(
    r"(?:valid\s*(?:till|upto|until))[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I
)
_DISTRICT_RE  = re.compile(r"(?:district|dist\.?)[:\s]+([A-Za-z\s]+?)(?:\n|state|pin|tehsil)", re.I)
_STATE_RE     = re.compile(
    r"\b(andhra\s*pradesh|arunachal\s*pradesh|assam|bihar|chhattisgarh|goa|gujarat|"
    r"haryana|himachal\s*pradesh|jharkhand|karnataka|kerala|madhya\s*pradesh|"
    r"maharashtra|manipur|meghalaya|mizoram|nagaland|odisha|punjab|rajasthan|"
    r"sikkim|tamil\s*nadu|telangana|tripura|uttar\s*pradesh|uttarakhand|west\s*bengal|"
    r"delhi|jammu\s*and\s*kashmir|ladakh)\b",
    re.I
)
_AUTHORITY_RE = re.compile(
    r"(?:issued?\s*by|tehsildar|district\s*collector)[:\s]+([A-Za-z\s,\.]+?)(?:\n|date|sign|seal)",
    re.I
)
_PIN_RE       = re.compile(r"\b(\d{6})\b")


def _norm_date(raw: str) -> str:
    raw = raw.strip().replace("-", "/").replace(".", "/")
    parts = raw.split("/")
    if len(parts) == 3:
        d, m, y = parts
        if len(y) == 2:
            y = ("20" if int(y) < 50 else "19") + y
        return f"{d.zfill(2)}/{m.zfill(2)}/{y}"
    return raw


class DomicileCertificateParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "domicile_certificate"}

        m = _CERT_NO_RE.search(text)
        if m:
            result["certificate_number"] = m.group(1).strip()

        m = _NAME_LBL_RE.search(text)
        if m:
            result["name"] = m.group(1).strip().title()

        m = _DOB_RE.search(text)
        if m:
            result["date_of_birth"] = _norm_date(m.group(1))

        m = _RELATION_RE.search(text)
        if m:
            result["relation_name"] = m.group(1).strip().title()

        m = _PERIOD_RE.search(text)
        if m:
            result["residency_period"] = m.group(1).strip()

        m = _ADDRESS_RE.search(text)
        if m:
            result["address"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = _ISSUE_DATE_RE.search(text)
        if m:
            result["issue_date"] = _norm_date(m.group(1))

        m = _VALID_RE.search(text)
        if m:
            result["valid_upto"] = _norm_date(m.group(1))

        m = _DISTRICT_RE.search(text)
        if m:
            result["district"] = m.group(1).strip().title()

        m = _STATE_RE.search(text)
        if m:
            result["state"] = m.group(1).strip().title()

        m = _PIN_RE.search(text)
        if m:
            result["pin_code"] = m.group(1)

        m = _AUTHORITY_RE.search(text)
        if m:
            result["issued_by"] = m.group(1).strip().title()

        result["raw_text"] = text
        return result
