"""Sale Deed / Conveyance Deed / Transfer Deed parser."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser
from parsers.realestate._helpers import (
    BOOK_RE,
    DISTRICT_RE,
    PIN_RE,
    REGN_NO_RE,
    SRO_RE,
    STAMP_RE,
    STATE_RE,
    SURVEY_RE,
    clean_amount,
    norm_date,
    parse_amount,
    parse_area,
)

_EXEC_DATE_RE  = re.compile(
    r"(?:executed?\s*(?:on|this)|execution\s*date|deed\s*dated?|this\s*deed\s*made)[:\s]*"
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.I,
)
_REG_DATE_RE   = re.compile(
    r"(?:registered?\s*on|registration\s*date|date\s*of\s*registration)[:\s]*"
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_SELLER_RE     = re.compile(
    r"(?:vendor|seller|transferor|executant|party\s*of\s*the\s*first\s*part)"
    r"[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|hereinafter|s/o|age|address|w/o|d/o|aged)",
    re.I,
)
_BUYER_RE      = re.compile(
    r"(?:vendee|buyer|purchaser|transferee|party\s*of\s*the\s*second\s*part)"
    r"[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|hereinafter|s/o|age|address|w/o|d/o|aged)",
    re.I,
)
_CONSID_RE     = re.compile(
    r"(?:sale\s*consideration|total\s*consideration|purchase\s*(?:price|consideration)|"
    r"consideration\s*amount)[:\s]*(?:rs\.?|inr|rupees?)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_CONSID_WORDS_RE = re.compile(
    r"(?:rs\.?|inr|rupees?)\s*([\d,]+(?:\.\d{1,2})?)\s*(?:\(|only|/-)",
    re.I,
)
_AREA_LABEL_RE = re.compile(
    r"(?:admeasuring|measuring|total\s*area|plinth\s*area|built[\s\-]up\s*area|"
    r"super\s*built[\s\-]up|carpet\s*area|site\s*area|land\s*area)[:\s]*",
    re.I,
)
_PROP_DESC_RE  = re.compile(
    r"(?:property\s*(?:described|situated|known\s*as|bearing)|"
    r"the\s*schedule\s*property|schedule\s*[\"\'A-Z]{0,3}\s*property|"
    r"the\s*said\s*property)[:\s]+([A-Za-z0-9\s,/\-\.#]+?)(?:\n\n|measuring|admeasuring|bounded)",
    re.I,
)


class SaleDeedParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "sale_deed"}

        m = REGN_NO_RE.search(text)
        if m:
            result["registration_number"] = m.group(1).strip()

        m = _EXEC_DATE_RE.search(text)
        if m:
            result["execution_date"] = norm_date(m.group(1))

        m = _REG_DATE_RE.search(text)
        if m:
            result["registration_date"] = norm_date(m.group(1))

        m = _SELLER_RE.search(text)
        if m:
            result["seller_name"] = m.group(1).strip().title()

        m = _BUYER_RE.search(text)
        if m:
            result["buyer_name"] = m.group(1).strip().title()

        # Sale consideration
        m = _CONSID_RE.search(text) or _CONSID_WORDS_RE.search(text)
        if m:
            result["sale_consideration"] = clean_amount(m.group(1))
        else:
            amt = parse_amount(text)
            if amt:
                result["sale_consideration"] = amt

        # Area
        area_m = _AREA_LABEL_RE.search(text)
        if area_m:
            segment = text[area_m.end(): area_m.end() + 100]
            area = parse_area(segment)
            if area:
                result["area"] = area

        # Property description
        m = _PROP_DESC_RE.search(text)
        if m:
            result["property_description"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = SURVEY_RE.search(text)
        if m:
            result["survey_plot_number"] = m.group(1).strip()

        m = STAMP_RE.search(text)
        if m:
            result["stamp_duty_paid"] = clean_amount(m.group(1))

        m = SRO_RE.search(text)
        if m:
            result["sub_registrar_office"] = m.group(1).strip().title()

        bm = BOOK_RE.search(text)
        if bm:
            result["book_number"]   = bm.group(1)
            result["volume_number"] = bm.group(2)
            result["page_number"]   = bm.group(3)

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
