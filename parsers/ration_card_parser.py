"""Ration Card / PDS Card parser — state food & civil supplies department."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

_CARD_NO_RE   = re.compile(
    r"(?:ration\s*card\s*(?:no\.?|number)|card\s*(?:no\.?|number)|rc\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)",
    re.I
)
_CARD_TYPE_RE = re.compile(
    r"\b(apl|bpl|aay|antyodaya\s*anna\s*yojana|above\s*poverty\s*line|"
    r"below\s*poverty\s*line|phh|priority\s*household|sfss|nfsa|non[\s\-]nfsa)\b",
    re.I
)
_HEAD_RE      = re.compile(
    r"(?:head\s*of\s*(?:family|household)|head\s*name|card\s*holder)[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|husband|wife|s/o|d/o|age|address)",
    re.I
)
_SHOP_RE      = re.compile(r"(?:fair\s*price\s*shop|fps|shop\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-\s]+?)(?:\n|dealer)", re.I)
_ISSUE_DATE_RE = re.compile(
    r"(?:date\s*of\s*issue|issued?\s*on|issue\s*date)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I
)
_VALID_RE     = re.compile(
    r"(?:valid\s*(?:till|upto|until)|expiry)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I
)
_ADDRESS_RE   = re.compile(
    r"(?:address|house\s*(?:no\.?|number)|door\s*(?:no\.?|number))[:\s]+([A-Za-z0-9\s,/\-\.]+?)(?:\n\n|\d{6}|dist|state)",
    re.I
)
_DISTRICT_RE  = re.compile(r"(?:district|dist\.?)[:\s]+([A-Za-z\s]+?)(?:\n|state|pin|taluk)", re.I)
_STATE_RE     = re.compile(
    r"\b(andhra\s*pradesh|arunachal\s*pradesh|assam|bihar|chhattisgarh|goa|gujarat|"
    r"haryana|himachal\s*pradesh|jharkhand|karnataka|kerala|madhya\s*pradesh|"
    r"maharashtra|manipur|meghalaya|mizoram|nagaland|odisha|punjab|rajasthan|"
    r"sikkim|tamil\s*nadu|telangana|tripura|uttar\s*pradesh|uttarakhand|west\s*bengal|"
    r"delhi|jammu\s*and\s*kashmir|ladakh)\b",
    re.I
)
_PIN_RE       = re.compile(r"\b(\d{6})\b")

# Member row: name | relation | age | gender
_MEMBER_ROW_RE = re.compile(
    r"([A-Z][A-Za-z\s\.]{3,25})\s+\|\s*([A-Za-z\s/]+?)\s*\|\s*(\d{1,3})\s*\|\s*(M|F|Male|Female)",
    re.I
)

_TYPE_MAP = {
    "apl": "APL", "above poverty line": "APL",
    "bpl": "BPL", "below poverty line": "BPL",
    "aay": "AAY", "antyodaya anna yojana": "AAY",
    "phh": "PHH", "priority household": "PHH",
    "sfss": "SFSS", "nfsa": "NFSA",
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


class RationCardParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        lower = text.lower()
        result: dict[str, Any] = {"doc_type": "ration_card"}

        m = _CARD_NO_RE.search(text)
        if m:
            result["card_number"] = m.group(1).strip()

        m = _CARD_TYPE_RE.search(lower)
        if m:
            raw_type = m.group(1).strip().lower()
            result["card_type"] = _TYPE_MAP.get(raw_type, raw_type.upper())

        m = _HEAD_RE.search(text)
        if m:
            result["head_of_family"] = m.group(1).strip().title()

        m = _SHOP_RE.search(text)
        if m:
            result["shop_number"] = m.group(1).strip()

        m = _ISSUE_DATE_RE.search(text)
        if m:
            result["issue_date"] = _norm_date(m.group(1))

        m = _VALID_RE.search(text)
        if m:
            result["valid_upto"] = _norm_date(m.group(1))

        m = _ADDRESS_RE.search(text)
        if m:
            result["address"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = _DISTRICT_RE.search(text)
        if m:
            result["district"] = m.group(1).strip().title()

        m = _STATE_RE.search(text)
        if m:
            result["state"] = m.group(1).strip().title()

        m = _PIN_RE.search(text)
        if m:
            result["pin_code"] = m.group(1)

        # Family members
        members = []
        for row_m in _MEMBER_ROW_RE.finditer(text):
            members.append({
                "name":     row_m.group(1).strip().title(),
                "relation": row_m.group(2).strip(),
                "age":      row_m.group(3),
                "gender":   "Female" if row_m.group(4).upper().startswith("F") else "Male",
            })
        if members:
            result["family_members"] = members

        result["raw_text"] = text
        return result
