"""Caste / Community / OBC Certificate parser."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

_CERT_NO_RE  = re.compile(
    r"(?:certificate\s*(?:no\.?|number)|ref(?:erence)?\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)",
    re.I
)
_NAME_LBL_RE = re.compile(
    r"(?:name\s*of\s*(?:the\s*)?applicant|applicant'?s?\s*name|(?:this\s*is\s*to\s*certify\s*that)\s+(?:shri|smt|kumari|mr\.?|ms\.?|mrs\.?)?\.?\s*)([A-Z][A-Za-z\s\.]+?)(?:\n|,|son|daughter|wife|s/o|d/o|w/o)",
    re.I
)
_RELATION_RE = re.compile(
    r"\b(?:s/o|d/o|w/o|son\s+of|daughter\s+of|wife\s+of)[:\s]+([A-Z][A-Za-z\s]+?)(?:\n|,|res|vill|dist)",
    re.I
)
_CASTE_RE    = re.compile(
    r"(?:belongs?\s*to|caste[:\s]+|community[:\s]+|sub[\s\-]caste[:\s]+)([A-Za-z\s\(\)]+?)(?:\n|which|and|,|cat)",
    re.I
)
_CATEGORY_RE = re.compile(
    r"\b(scheduled\s*caste|scheduled\s*tribe|other\s*backward\s*class|obc|sc\b|st\b|"
    r"ews|economically\s*weaker\s*section|general|open|bc[\s\-][a-e]|mbc|dnc)\b",
    re.I
)
_SUBCATEGORY_RE = re.compile(r"\b(creamy\s*layer|non[\s\-]creamy\s*layer|nco\b)\b", re.I)
_ISSUE_DATE_RE  = re.compile(
    r"(?:date\s*of\s*issue|issued?\s*on|issued?\s*date)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I
)
_VALID_RE    = re.compile(
    r"(?:valid\s*(?:till|upto|until)|expiry)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I
)
_DISTRICT_RE = re.compile(r"(?:district|dist\.?)[:\s]+([A-Za-z\s]+?)(?:\n|state|pin|taluk)", re.I)
_STATE_RE    = re.compile(
    r"\b(andhra\s*pradesh|arunachal\s*pradesh|assam|bihar|chhattisgarh|goa|gujarat|"
    r"haryana|himachal\s*pradesh|jharkhand|karnataka|kerala|madhya\s*pradesh|"
    r"maharashtra|manipur|meghalaya|mizoram|nagaland|odisha|punjab|rajasthan|"
    r"sikkim|tamil\s*nadu|telangana|tripura|uttar\s*pradesh|uttarakhand|west\s*bengal|"
    r"delhi|jammu\s*and\s*kashmir|ladakh)\b",
    re.I
)
_AUTHORITY_RE = re.compile(
    r"(?:issued?\s*by|issuing\s*authority)[:\s]+([A-Za-z\s,\.]+?)(?:\n|date|sign|stamp)",
    re.I
)

_CATEGORY_MAP = {
    "sc": "SC", "scheduled caste": "SC",
    "st": "ST", "scheduled tribe": "ST",
    "obc": "OBC", "other backward class": "OBC",
    "ews": "EWS", "economically weaker section": "EWS",
    "general": "General", "open": "General",
    "mbc": "MBC", "dnc": "DNC",
}


def _norm_date(raw: str) -> str:
    raw = raw.strip().replace("-", "/").replace(".", "/")
    parts = raw.split("/")
    if len(parts) == 3:
        d, m, y = parts
        if len(y) == 2:
            y = ("20" if int(y) < 50 else "19") + y
        return f"{d.zfill(2)}/{m.zfill(2)}/{y}"
    return raw


class CasteCertificateParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        lower = text.lower()
        result: dict[str, Any] = {"doc_type": "caste_certificate"}

        m = _CERT_NO_RE.search(text)
        if m:
            result["certificate_number"] = m.group(1).strip()

        m = _NAME_LBL_RE.search(text)
        if m:
            result["name"] = m.group(1).strip().title()

        m = _RELATION_RE.search(text)
        if m:
            result["relation_name"] = m.group(1).strip().title()

        m = _CASTE_RE.search(text)
        if m:
            result["caste"] = m.group(1).strip().title()

        m = _CATEGORY_RE.search(lower)
        if m:
            raw_cat = m.group(1).strip().lower()
            result["category"] = _CATEGORY_MAP.get(raw_cat, raw_cat.upper())

        m = _SUBCATEGORY_RE.search(lower)
        if m:
            result["sub_category"] = m.group(1).strip().title()

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

        m = _AUTHORITY_RE.search(text)
        if m:
            result["issued_by"] = m.group(1).strip().title()

        result["raw_text"] = text
        return result
