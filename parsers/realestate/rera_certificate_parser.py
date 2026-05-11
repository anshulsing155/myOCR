"""RERA Registration Certificate parser — Real Estate Regulatory Authority."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser
from parsers.realestate._helpers import (
    DISTRICT_RE,
    PIN_RE,
    STATE_RE,
    norm_date,
    parse_area,
)

# RERA number patterns vary by state
_RERA_NO_RE    = re.compile(
    r"(?:rera\s*(?:registration\s*)?(?:no\.?|number)|registration\s*(?:no\.?|number))"
    r"[:\s]+([A-Z0-9/\-]+)",
    re.I,
)
_RERA_BARE_RE  = re.compile(
    r"\b(P\d{11}|UPRERAPRJ\d+|DLRERA\d{4}[A-Z]\d+|[A-Z]{2}RERA[A-Z0-9/\-]+)\b",
)
_PROJECT_RE    = re.compile(
    r"(?:project\s*name|name\s*of\s*(?:the\s*)?project)[:\s]+([A-Za-z0-9\s,\.\-&]+?)(?:\n|promoter|developer|location|address|\d{4})",
    re.I,
)
_PROMOTER_RE   = re.compile(
    r"(?:promoter(?:'s)?\s*name|developer(?:'s)?\s*name|name\s*of\s*(?:the\s*)?(?:promoter|developer))"
    r"[:\s]+([A-Za-z0-9\s,\.\-&]+?)(?:\n|address|project|rera|contact)",
    re.I,
)
_PROJ_ADDR_RE  = re.compile(
    r"(?:project\s*(?:address|location|site)|location\s*of\s*(?:the\s*)?project)"
    r"[:\s]+([A-Za-z0-9\s,/\-\.#]+?)(?:\n\n|district|state|\d{6}|promoter|rera)",
    re.I,
)
_REG_DATE_RE   = re.compile(
    r"(?:registration\s*date|date\s*of\s*registration|registered?\s*on)"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_EXPIRY_RE     = re.compile(
    r"(?:expiry\s*date|valid\s*(?:till|upto|until)|validity\s*date|registration\s*valid\s*(?:till|upto))"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_COMPLETION_RE = re.compile(
    r"(?:proposed\s*completion\s*date|completion\s*date|project\s*completion)"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_UNITS_RE      = re.compile(r"(?:total\s*(?:no\.?\s*of\s*)?units|number\s*of\s*units)[:\s]+(\d+)", re.I)
_TYPE_RE       = re.compile(r"(?:project\s*type|nature\s*of\s*project)[:\s]+(residential|commercial|mixed\s*use|plotted\s*development)", re.I)
_AUTHORITY_RE  = re.compile(r"(?:rera\s*authority|state\s*rera|authority\s*name)[:\s]+([A-Za-z\s]+?)(?:\n|website|reg|\d{4})", re.I)
_WEBSITE_RE    = re.compile(r"(?:rera\s*website|portal|website)[:\s]+((?:https?://)?[A-Za-z0-9.\-/]+\.gov\.in[A-Za-z0-9./]*)", re.I)


class ReraCertificateParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "rera_certificate"}

        m = _RERA_NO_RE.search(text) or _RERA_BARE_RE.search(text)
        if m:
            result["rera_number"] = m.group(1).strip()

        m = _PROJECT_RE.search(text)
        if m:
            result["project_name"] = m.group(1).strip().title()

        m = _PROMOTER_RE.search(text)
        if m:
            result["promoter_name"] = m.group(1).strip().title()

        m = _PROJ_ADDR_RE.search(text)
        if m:
            result["project_address"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = _REG_DATE_RE.search(text)
        if m:
            result["registration_date"] = norm_date(m.group(1))

        m = _EXPIRY_RE.search(text)
        if m:
            result["expiry_date"] = norm_date(m.group(1))

        m = _COMPLETION_RE.search(text)
        if m:
            result["completion_date"] = norm_date(m.group(1))

        m = _UNITS_RE.search(text)
        if m:
            result["total_units"] = m.group(1)

        area = parse_area(text)
        if area:
            result["project_area"] = area

        m = _TYPE_RE.search(text)
        if m:
            result["project_type"] = m.group(1).strip().title()

        m = _AUTHORITY_RE.search(text)
        if m:
            result["rera_authority"] = m.group(1).strip().title()

        m = _WEBSITE_RE.search(text)
        if m:
            result["rera_website"] = m.group(1).strip()

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
