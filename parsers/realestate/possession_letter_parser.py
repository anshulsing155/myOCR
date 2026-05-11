"""Possession Letter / Allotment Letter / Offer of Possession parser."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser
from parsers.realestate._helpers import (
    DISTRICT_RE,
    PIN_RE,
    STATE_RE,
    clean_amount,
    norm_date,
    parse_area,
)

_LETTER_NO_RE  = re.compile(r"(?:letter\s*(?:no\.?|number|ref)|ref(?:erence)?\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)", re.I)
_PROJECT_RE    = re.compile(
    r"(?:project\s*name|name\s*of\s*(?:the\s*)?project|scheme\s*name)"
    r"[:\s]+([A-Za-z0-9\s,\.\-&]+?)(?:\n|unit|flat|tower|block|buyer|phase)",
    re.I,
)
_DEVELOPER_RE  = re.compile(
    r"(?:developer(?:'s)?\s*name|builder(?:'s)?\s*name|promoter\s*name)"
    r"[:\s]+([A-Za-z0-9\s,\.\-&]+?)(?:\n|project|unit|flat|address|contact)",
    re.I,
)
_BUYER_RE      = re.compile(
    r"(?:buyer(?:'s)?\s*name|allottee(?:'s)?\s*name|purchaser(?:'s)?\s*name|customer\s*name)"
    r"[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|unit|flat|plot|address|booking|contact|s/o|d/o|w/o)",
    re.I,
)
_UNIT_RE       = re.compile(
    r"(?:unit\s*(?:no\.?|number)|flat\s*(?:no\.?|number)|apartment\s*(?:no\.?|number)|"
    r"plot\s*(?:no\.?|number)|villa\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)",
    re.I,
)
_TOWER_RE      = re.compile(r"(?:tower|block|wing)[:\s]+([A-Z0-9\s]+?)(?:\n|floor|flat|unit)", re.I)
_FLOOR_RE      = re.compile(r"(?:floor\s*(?:no\.?|number)|on\s*the\s*\d+(?:st|nd|rd|th)\s*floor)[:\s]+(\d+|[A-Za-z]+)", re.I)
_POSS_DATE_RE  = re.compile(
    r"(?:date\s*of\s*possession|possession\s*date|possession\s*(?:shall\s*be\s*given|offered|handed)\s*on)"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.I,
)
_AMOUNT_RE     = re.compile(
    r"(?:balance\s*amount\s*(?:payable|due)|outstanding\s*amount|amount\s*due)"
    r"[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_RERA_RE       = re.compile(r"(?:rera\s*(?:no\.?|number|reg))[:\s]+([A-Z0-9/\-]+)", re.I)
_BOOKING_NO_RE = re.compile(r"(?:booking\s*(?:no\.?|number)|customer\s*(?:id|no\.?))[:\s]+([A-Z0-9/\-]+)", re.I)


class PossessionLetterParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "possession_letter"}

        m = _LETTER_NO_RE.search(text)
        if m:
            result["letter_number"] = m.group(1).strip()

        m = _PROJECT_RE.search(text)
        if m:
            result["project_name"] = m.group(1).strip().title()

        m = _DEVELOPER_RE.search(text)
        if m:
            result["developer_name"] = m.group(1).strip().title()

        m = _BUYER_RE.search(text)
        if m:
            result["buyer_name"] = m.group(1).strip().title()

        m = _UNIT_RE.search(text)
        if m:
            result["unit_number"] = m.group(1).strip()

        m = _TOWER_RE.search(text)
        if m:
            result["tower_block"] = m.group(1).strip()

        m = _FLOOR_RE.search(text)
        if m:
            result["floor"] = m.group(1).strip()

        m = _POSS_DATE_RE.search(text)
        if m:
            result["possession_date"] = norm_date(m.group(1))

        m = _AMOUNT_RE.search(text)
        if m:
            result["amount_due"] = clean_amount(m.group(1))

        area = parse_area(text)
        if area:
            result["area"] = area

        m = _RERA_RE.search(text)
        if m:
            result["rera_number"] = m.group(1).strip()

        m = _BOOKING_NO_RE.search(text)
        if m:
            result["booking_number"] = m.group(1).strip()

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
