"""Khata Certificate / Khata Extract / A-Khata / B-Khata parser (Karnataka & others)."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser
from parsers.realestate._helpers import (
    norm_date, parse_area, clean_amount, PIN_RE, STATE_RE, DISTRICT_RE,
)

_KHATA_NO_RE   = re.compile(
    r"(?:khata\s*(?:no\.?|number)|katha\s*(?:no\.?|number)|property\s*(?:no\.?|number))"
    r"[:\s]+([A-Z0-9/\-]+)",
    re.I,
)
_OWNER_RE      = re.compile(
    r"(?:owner(?:'s)?\s*name|name\s*of\s*(?:the\s*)?owner|khatedaar\s*name)"
    r"[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|address|khata|property|ward|zone|site)",
    re.I,
)
_PROP_ID_RE    = re.compile(r"(?:property\s*(?:id|identification)|pid)[:\s]+([A-Z0-9/\-]+)", re.I)
_PROP_ADDR_RE  = re.compile(
    r"(?:property\s*address|site\s*(?:no\.?|number)|door\s*(?:no\.?|number))"
    r"[:\s]+([A-Za-z0-9\s,/\-\.#]+?)(?:\n|ward|zone|survey|\d{6}|owner)",
    re.I,
)
_SURVEY_RE     = re.compile(
    r"(?:rev(?:enue)?\s*survey\s*(?:no\.?|number)|rs\s*(?:no\.?|number)|"
    r"survey\s*(?:no\.?|number))[:\s]+([A-Z0-9/,\s]+?)(?:\n|area|site|ward)",
    re.I,
)
_WARD_RE       = re.compile(r"(?:ward\s*(?:no\.?|number)|zone\s*(?:no\.?|number))[:\s]+([A-Za-z0-9\s\-]+?)(?:\n|property|khata)", re.I)
_SITE_AREA_RE  = re.compile(
    r"(?:site\s*area|plot\s*area|land\s*area|total\s*area)[:\s]*"
    r"([\d,]+(?:\.\d+)?)\s*(?:sq\.?\s*(?:ft|meter|metre|mt|yard)|sqmt|sqft)",
    re.I,
)
_BUA_RE        = re.compile(
    r"(?:built[\s\-]up\s*area|bua|floor\s*area|plinth\s*area)[:\s]*"
    r"([\d,]+(?:\.\d+)?)\s*(?:sq\.?\s*(?:ft|meter|metre|mt)|sqmt|sqft)",
    re.I,
)
_ISSUE_DATE_RE = re.compile(
    r"(?:issued?\s*on|date\s*of\s*issue|issue\s*date)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_MUNICIPAL_RE  = re.compile(
    r"(bbmp|bruhat\s*bengaluru|municipal\s*corporation|nagar\s*(?:palika|nigam|panchayat)|"
    r"gram\s*panchayat|town\s*panchayat|cantonment\s*board)[A-Za-z\s,]*",
    re.I,
)
_KHATA_TYPE_RE = re.compile(r"\b([AB][\s\-]khata|a[\s\-]?khata|b[\s\-]?khata)\b", re.I)
_USE_RE        = re.compile(r"(?:use\s*of\s*property|land\s*use|nature\s*of\s*use)[:\s]+(residential|commercial|industrial|mixed|agricultural)", re.I)


class KhataParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "khata"}

        m = _KHATA_NO_RE.search(text)
        if m:
            result["khata_number"] = m.group(1).strip()

        m = _OWNER_RE.search(text)
        if m:
            result["owner_name"] = m.group(1).strip().title()

        m = _PROP_ID_RE.search(text)
        if m:
            result["property_id"] = m.group(1).strip()

        m = _PROP_ADDR_RE.search(text)
        if m:
            result["property_address"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = _SURVEY_RE.search(text)
        if m:
            result["revenue_survey_number"] = m.group(1).strip()

        m = _WARD_RE.search(text)
        if m:
            result["ward"] = m.group(1).strip()

        m = _SITE_AREA_RE.search(text)
        if m:
            result["site_area_sqft"] = clean_amount(m.group(1))

        m = _BUA_RE.search(text)
        if m:
            result["built_up_area_sqft"] = clean_amount(m.group(1))

        m = _ISSUE_DATE_RE.search(text)
        if m:
            result["issue_date"] = norm_date(m.group(1))

        m = _MUNICIPAL_RE.search(text)
        if m:
            result["municipal_body"] = m.group(0).strip().title()

        m = _KHATA_TYPE_RE.search(text)
        if m:
            result["khata_type"] = m.group(1).upper().replace(" ", "-")

        m = _USE_RE.search(text)
        if m:
            result["property_use"] = m.group(1).strip().title()

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
