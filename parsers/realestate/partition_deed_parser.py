"""Partition Deed / Relinquishment Deed parser."""
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

_DEED_TYPE_RE  = re.compile(
    r"\b(partition\s*deed|deed\s*of\s*partition|relinquishment\s*deed|"
    r"deed\s*of\s*relinquishment|release\s*deed|settlement\s*deed|family\s*settlement)\b",
    re.I,
)
_EXEC_DATE_RE  = re.compile(
    r"(?:executed?\s*(?:on|this)|this\s*deed\s*(?:is\s*)?(?:made|dated?))"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.I,
)
_REG_DATE_RE   = re.compile(
    r"(?:registered?\s*on|registration\s*date)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_PARTY_RE      = re.compile(
    r"(?:party\s*(?:no\.?\s*\d+|of\s*the\s*(?:first|second|third)\s*part)|"
    r"co[\s\-]owner|co[\s\-]sharer)[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|hereinafter|s/o|d/o|w/o|age|address)",
    re.I,
)
_RELIQ_RE      = re.compile(
    r"(?:relinquishing|releasing|giving\s*up)\s*(?:his|her|their)?\s*(?:share|right|interest)"
    r"[:\s]+(\d+/\d+|(?:\d+(?:\.\d+)?)%?)",
    re.I,
)
_PROP_DESC_RE  = re.compile(
    r"(?:property\s*(?:described|situated|known\s*as|bearing)|the\s*schedule\s*property|"
    r"the\s*said\s*property|joint\s*property)[:\s]+([A-Za-z0-9\s,/\-\.#]+?)(?:\n\n|measuring|bounded|stamp)",
    re.I,
)
_SHARE_RE      = re.compile(
    r"([A-Z][A-Za-z\s\.]{5,30})\s*[-:]\s*(\d+/\d+|(?:\d+(?:\.\d+)?)%)\s*share",
    re.I,
)
_CONSID_RE     = re.compile(
    r"(?:consideration|amount\s*paid|payment)[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)


class PartitionDeedParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "partition_deed"}

        m = _DEED_TYPE_RE.search(text)
        if m:
            result["deed_type"] = m.group(1).strip().title()

        m = REGN_NO_RE.search(text)
        if m:
            result["registration_number"] = m.group(1).strip()

        m = _EXEC_DATE_RE.search(text)
        if m:
            result["execution_date"] = norm_date(m.group(1))

        m = _REG_DATE_RE.search(text)
        if m:
            result["registration_date"] = norm_date(m.group(1))

        # All parties
        parties = [m.group(1).strip().title() for m in _PARTY_RE.finditer(text)]
        if parties:
            result["parties"] = parties

        # Per-party shares
        shares = {m.group(1).strip().title(): m.group(2) for m in _SHARE_RE.finditer(text)}
        if shares:
            result["shares"] = shares

        m = _RELIQ_RE.search(text)
        if m:
            result["relinquished_share"] = m.group(1)

        m = _PROP_DESC_RE.search(text)
        if m:
            result["property_description"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = SURVEY_RE.search(text)
        if m:
            result["survey_plot_number"] = m.group(1).strip()

        area = parse_area(text)
        if area:
            result["area"] = area

        m = _CONSID_RE.search(text)
        if m:
            result["consideration"] = clean_amount(m.group(1))

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
