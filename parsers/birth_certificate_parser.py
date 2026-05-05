"""Birth Certificate parser — municipal / gram panchayat issuance."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

_CERT_NO_RE   = re.compile(
    r"(?:certificate\s*(?:no\.?|number)|reg(?:istration)?\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)",
    re.I
)
_DOB_LBL_RE   = re.compile(
    r"(?:date\s*of\s*birth|born\s*on|birth\s*date)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I
)
_REG_DATE_RE  = re.compile(
    r"(?:date\s*of\s*reg(?:istration)?|registration\s*date)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I
)
_FATHER_RE    = re.compile(r"(?:father'?s?\s*name|father)[:\s]+([A-Z][A-Za-z\s]+?)(?:\n|mother|dob)", re.I)
_MOTHER_RE    = re.compile(r"(?:mother'?s?\s*name|mother)[:\s]+([A-Z][A-Za-z\s]+?)(?:\n|father|dob|address)", re.I)
_CHILD_RE     = re.compile(r"(?:child'?s?\s*name|name\s*of\s*child|name)[:\s]+([A-Z][A-Za-z\s]+?)(?:\n|father|sex|gender|dob)", re.I)
_GENDER_RE    = re.compile(r"(?:sex|gender)[:\s]*(male|female|boy|girl|m|f)", re.I)
_PLACE_RE     = re.compile(r"(?:place\s*of\s*birth|born\s*at|hospital\s*name)[:\s]+([A-Za-z\s,]+?)(?:\n|date|dist)", re.I)
_DISTRICT_RE  = re.compile(r"(?:district|dist\.?)[:\s]+([A-Za-z\s]+?)(?:\n|state|pin)", re.I)
_STATE_RE     = re.compile(
    r"\b(andhra\s*pradesh|arunachal\s*pradesh|assam|bihar|chhattisgarh|goa|gujarat|"
    r"haryana|himachal\s*pradesh|jharkhand|karnataka|kerala|madhya\s*pradesh|"
    r"maharashtra|manipur|meghalaya|mizoram|nagaland|odisha|punjab|rajasthan|"
    r"sikkim|tamil\s*nadu|telangana|tripura|uttar\s*pradesh|uttarakhand|west\s*bengal|"
    r"delhi|jammu\s*and\s*kashmir|ladakh)\b",
    re.I
)
_PIN_RE = re.compile(r"\b(\d{6})\b")


def _norm_date(raw: str) -> str:
    raw = raw.strip().replace("-", "/").replace(".", "/")
    parts = raw.split("/")
    if len(parts) == 3:
        d, m, y = parts
        if len(y) == 2:
            y = ("20" if int(y) < 50 else "19") + y
        return f"{d.zfill(2)}/{m.zfill(2)}/{y}"
    return raw


class BirthCertificateParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "birth_certificate"}

        m = _CERT_NO_RE.search(text)
        if m:
            result["certificate_number"] = m.group(1).strip()

        m = _CHILD_RE.search(text)
        if m:
            result["child_name"] = m.group(1).strip().title()

        m = _FATHER_RE.search(text)
        if m:
            result["father_name"] = m.group(1).strip().title()

        m = _MOTHER_RE.search(text)
        if m:
            result["mother_name"] = m.group(1).strip().title()

        m = _DOB_LBL_RE.search(text)
        if m:
            result["date_of_birth"] = _norm_date(m.group(1))

        m = _REG_DATE_RE.search(text)
        if m:
            result["registration_date"] = _norm_date(m.group(1))

        m = _GENDER_RE.search(text)
        if m:
            g = m.group(1).lower()
            result["sex"] = "Female" if g in ("female", "girl", "f") else "Male"

        m = _PLACE_RE.search(text)
        if m:
            result["place_of_birth"] = m.group(1).strip().title()

        m = _DISTRICT_RE.search(text)
        if m:
            result["district"] = m.group(1).strip().title()

        m = _STATE_RE.search(text)
        if m:
            result["state"] = m.group(1).strip().title()

        m = _PIN_RE.search(text)
        if m:
            result["pin_code"] = m.group(1)

        result["raw_text"] = text
        return result
