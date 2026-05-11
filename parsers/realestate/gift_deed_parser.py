"""Gift Deed parser — property gifted without monetary consideration."""
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
    parse_area,
)

_EXEC_DATE_RE  = re.compile(
    r"(?:executed?\s*(?:on|this)|this\s*(?:gift\s*)?deed\s*(?:is\s*)?(?:made|dated?))"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.I,
)
_REG_DATE_RE   = re.compile(
    r"(?:registered?\s*on|registration\s*date)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_DONOR_RE      = re.compile(
    r"(?:donor|giftor|settlor|transferor|first\s*party)"
    r"[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|hereinafter|s/o|d/o|w/o|age|address|donee|donee)",
    re.I,
)
_DONEE_RE      = re.compile(
    r"(?:donee|giftee|recipient|transferee|second\s*party)"
    r"[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|hereinafter|s/o|d/o|w/o|age|address|donor)",
    re.I,
)
_RELATION_RE   = re.compile(
    r"(?:relation(?:ship)?\s*(?:of\s*donee\s*with\s*donor|between\s*parties))"
    r"[:\s]+(son|daughter|wife|husband|brother|sister|mother|father|nephew|niece|relative|friend)",
    re.I,
)
_PROP_DESC_RE  = re.compile(
    r"(?:property\s*(?:described|situated|known\s*as|bearing)|the\s*schedule\s*property|gift\s*property)"
    r"[:\s]+([A-Za-z0-9\s,/\-\.#]+?)(?:\n\n|measuring|admeasuring|bounded|stamp|witness|market)",
    re.I,
)
_MKT_VALUE_RE  = re.compile(
    r"(?:market\s*value|value\s*of\s*(?:the\s*)?property|consideration\s*value)"
    r"[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_POSSESSION_RE = re.compile(
    r"(?:possession\s*(?:delivered|handed|given)\s*on|date\s*of\s*possession)"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)


class GiftDeedParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "gift_deed"}

        m = REGN_NO_RE.search(text)
        if m:
            result["registration_number"] = m.group(1).strip()

        m = _EXEC_DATE_RE.search(text)
        if m:
            result["execution_date"] = norm_date(m.group(1))

        m = _REG_DATE_RE.search(text)
        if m:
            result["registration_date"] = norm_date(m.group(1))

        m = _DONOR_RE.search(text)
        if m:
            result["donor_name"] = m.group(1).strip().title()

        m = _DONEE_RE.search(text)
        if m:
            result["donee_name"] = m.group(1).strip().title()

        m = _RELATION_RE.search(text)
        if m:
            result["relationship"] = m.group(1).strip().title()

        m = _PROP_DESC_RE.search(text)
        if m:
            result["property_description"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = SURVEY_RE.search(text)
        if m:
            result["survey_plot_number"] = m.group(1).strip()

        area = parse_area(text)
        if area:
            result["area"] = area

        m = _MKT_VALUE_RE.search(text)
        if m:
            result["market_value"] = clean_amount(m.group(1))

        m = _POSSESSION_RE.search(text)
        if m:
            result["possession_date"] = norm_date(m.group(1))

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
