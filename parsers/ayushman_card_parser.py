"""Ayushman Bharat / PM-JAY Health Benefit Card parser."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

_CARD_ID_RE   = re.compile(
    r"(?:pmjay\s*id|beneficiary\s*id|health\s*id|card\s*(?:no\.?|number)|id\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)",
    re.I
)
_FAMILY_ID_RE = re.compile(r"(?:family\s*id|hhd?\s*id|household\s*id)[:\s]+([A-Z0-9/\-]+)", re.I)
_NAME_LBL_RE  = re.compile(
    r"(?:beneficiary\s*name|patient\s*name|name\s*of\s*beneficiary|name)[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|age|dob|gender|sex|relation|father|husband)",
    re.I
)
_AGE_RE       = re.compile(r"(?:age)[:\s]+(\d{1,3})\s*(?:yrs?\.?|years?)?", re.I)
_DOB_RE       = re.compile(r"(?:date\s*of\s*birth|dob)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})", re.I)
_GENDER_RE    = re.compile(r"(?:gender|sex)[:\s]*(male|female|transgender|m|f)", re.I)
_RELATION_RE  = re.compile(r"(?:relation(?:ship)?|relation\s*to\s*hoh)[:\s]+([A-Za-z\s]+?)(?:\n|beneficiary|name|age)", re.I)
_SCHEME_RE    = re.compile(
    r"\b(pmjay|pm[\s\-]jan[\s\-]arogya|ayushman\s*bharat|ab[\s\-]pmjay|"
    r"chiranjeevi|arogyasri|mahatma\s*jyotirao|bhamashah|cghs|esi)\b",
    re.I
)
_VALID_RE     = re.compile(
    r"(?:valid\s*(?:till|upto|until)|expiry|validity)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I
)
_HOSPITAL_LIMIT_RE = re.compile(r"(?:cover|benefit|sum\s*insured)[:\s]*(?:rs\.?|inr)?\s*([\d,]+)", re.I)
_STATE_RE     = re.compile(
    r"\b(andhra\s*pradesh|arunachal\s*pradesh|assam|bihar|chhattisgarh|goa|gujarat|"
    r"haryana|himachal\s*pradesh|jharkhand|karnataka|kerala|madhya\s*pradesh|"
    r"maharashtra|manipur|meghalaya|mizoram|nagaland|odisha|punjab|rajasthan|"
    r"sikkim|tamil\s*nadu|telangana|tripura|uttar\s*pradesh|uttarakhand|west\s*bengal|"
    r"delhi|jammu\s*and\s*kashmir|ladakh)\b",
    re.I
)
_DISTRICT_RE  = re.compile(r"(?:district|dist\.?)[:\s]+([A-Za-z\s]+?)(?:\n|state|pin)", re.I)


def _norm_date(raw: str) -> str:
    raw = raw.strip().replace("-", "/").replace(".", "/")
    parts = raw.split("/")
    if len(parts) == 3:
        d, m, y = parts
        if len(y) == 2:
            y = ("20" if int(y) < 50 else "19") + y
        return f"{d.zfill(2)}/{m.zfill(2)}/{y}"
    return raw


class AyushmanCardParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "ayushman_card", "scheme": "PM-JAY"}

        m = _CARD_ID_RE.search(text)
        if m:
            result["card_id"] = m.group(1).strip()

        m = _FAMILY_ID_RE.search(text)
        if m:
            result["family_id"] = m.group(1).strip()

        m = _NAME_LBL_RE.search(text)
        if m:
            result["beneficiary_name"] = m.group(1).strip().title()

        m = _AGE_RE.search(text)
        if m:
            result["age"] = m.group(1)

        m = _DOB_RE.search(text)
        if m:
            result["date_of_birth"] = _norm_date(m.group(1))

        m = _GENDER_RE.search(text)
        if m:
            g = m.group(1).lower()
            result["gender"] = "Female" if g in ("female", "f") else (
                "Transgender" if g == "transgender" else "Male"
            )

        m = _RELATION_RE.search(text)
        if m:
            result["relation"] = m.group(1).strip().title()

        m = _SCHEME_RE.search(text)
        if m:
            result["scheme"] = m.group(1).strip().upper()

        m = _VALID_RE.search(text)
        if m:
            result["valid_upto"] = _norm_date(m.group(1))

        m = _HOSPITAL_LIMIT_RE.search(text)
        if m:
            result["benefit_amount"] = m.group(1).replace(",", "")

        m = _DISTRICT_RE.search(text)
        if m:
            result["district"] = m.group(1).strip().title()

        m = _STATE_RE.search(text)
        if m:
            result["state"] = m.group(1).strip().title()

        result["raw_text"] = text
        return result
