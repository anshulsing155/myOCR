"""Marriage Certificate parser — registrar office / municipal issuance."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

_CERT_NO_RE   = re.compile(
    r"(?:certificate\s*(?:no\.?|number)|reg(?:istration)?\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)",
    re.I
)
_HUSBAND_RE   = re.compile(
    r"(?:groom'?s?\s*name|husband'?s?\s*name|bridegroom|name\s*of\s*(?:groom|husband))[:\s]+"
    r"([A-Z][A-Za-z\s]+?)(?:\n|wife|bride|date|age|dob|father)",
    re.I
)
_WIFE_RE      = re.compile(
    r"(?:bride'?s?\s*name|wife'?s?\s*name|name\s*of\s*(?:bride|wife))[:\s]+"
    r"([A-Z][A-Za-z\s]+?)(?:\n|husband|groom|date|age|dob|father)",
    re.I
)
_DOM_RE       = re.compile(
    r"(?:date\s*of\s*marriage|marriage\s*date|solemnized\s*on)[:\s]*"
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
    re.I
)
_REG_DATE_RE  = re.compile(
    r"(?:date\s*of\s*reg(?:istration)?|registration\s*date)[:\s]*"
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I
)
_PLACE_RE     = re.compile(
    r"(?:place\s*of\s*marriage|married\s*at|venue)[:\s]+([A-Za-z\s,]+?)(?:\n|date|dist)",
    re.I
)
_DISTRICT_RE  = re.compile(r"(?:district|dist\.?)[:\s]+([A-Za-z\s]+?)(?:\n|state|pin)", re.I)
_STATE_RE     = re.compile(
    r"\b(andhra\s*pradesh|arunachal\s*pradesh|assam|bihar|chhattisgarh|goa|gujarat|"
    r"haryana|himachal\s*pradesh|jharkhand|karnataka|kerala|madhya\s*pradesh|"
    r"maharashtra|manipur|meghalaya|mizoram|nagaland|odisha|punjab|rajasthan|"
    r"sikkim|tamil\s*nadu|telangana|tripura|uttar\s*pradesh|uttarakhand|west\s*bengal|"
    r"delhi|jammu\s*and\s*kashmir|ladakh)\b",
    re.I
)
_ACT_RE       = re.compile(r"(?:under\s+)([\w\s]+act[\s\d]*)", re.I)

_MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09",
    "oct": "10", "nov": "11", "dec": "12",
}


def _norm_date(raw: str) -> str:
    raw = raw.strip()
    m = re.match(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", raw)
    if m:
        d, mon, y = m.groups()
        mn = _MONTH_MAP.get(mon.lower(), "00")
        return f"{d.zfill(2)}/{mn}/{y}"
    raw = raw.replace("-", "/").replace(".", "/")
    parts = raw.split("/")
    if len(parts) == 3:
        d, mn, y = parts
        if len(y) == 2:
            y = ("20" if int(y) < 50 else "19") + y
        return f"{d.zfill(2)}/{mn.zfill(2)}/{y}"
    return raw


class MarriageCertificateParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "marriage_certificate"}

        m = _CERT_NO_RE.search(text)
        if m:
            result["certificate_number"] = m.group(1).strip()

        m = _HUSBAND_RE.search(text)
        if m:
            result["husband_name"] = m.group(1).strip().title()

        m = _WIFE_RE.search(text)
        if m:
            result["wife_name"] = m.group(1).strip().title()

        m = _DOM_RE.search(text)
        if m:
            result["date_of_marriage"] = _norm_date(m.group(1))

        m = _REG_DATE_RE.search(text)
        if m:
            result["registration_date"] = _norm_date(m.group(1))

        m = _PLACE_RE.search(text)
        if m:
            result["place_of_marriage"] = m.group(1).strip().title()

        m = _DISTRICT_RE.search(text)
        if m:
            result["district"] = m.group(1).strip().title()

        m = _STATE_RE.search(text)
        if m:
            result["state"] = m.group(1).strip().title()

        m = _ACT_RE.search(text)
        if m:
            result["act"] = m.group(1).strip().title()

        result["raw_text"] = text
        return result
