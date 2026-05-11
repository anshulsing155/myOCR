"""Occupancy Certificate / Completion Certificate / Commencement Certificate parser."""
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

_CERT_NO_RE    = re.compile(
    r"(?:certificate\s*(?:no\.?|number)|oc\s*(?:no\.?|number)|cc\s*(?:no\.?|number))"
    r"[:\s]+([A-Z0-9/\-]+)",
    re.I,
)
_CERT_TYPE_RE  = re.compile(
    r"\b(occupancy\s*certificate|completion\s*certificate|commencement\s*certificate|"
    r"part\s*occupancy\s*certificate|provisional\s*oc|no\s*objection\s*certificate)\b",
    re.I,
)
_PROJECT_RE    = re.compile(
    r"(?:project\s*name|building\s*name|name\s*of\s*(?:the\s*)?(?:project|building))"
    r"[:\s]+([A-Za-z0-9\s,\.\-&]+?)(?:\n|owner|developer|address|survey|plot)",
    re.I,
)
_OWNER_RE      = re.compile(
    r"(?:owner(?:'s)?\s*name|developer(?:'s)?\s*name|builder\s*name|applicant\s*name)"
    r"[:\s]+([A-Z][A-Za-z\s\.&]+?)(?:\n|address|property|oc|cc|certificate|plot)",
    re.I,
)
_PROP_ADDR_RE  = re.compile(
    r"(?:property\s*(?:address|details?)|site\s*address|premises\s*(?:address|details?))"
    r"[:\s]+([A-Za-z0-9\s,/\-\.#]+?)(?:\n\n|district|state|\d{6}|developer|owner)",
    re.I,
)
_PLAN_REF_RE   = re.compile(
    r"(?:approved\s*plan\s*(?:no\.?|number|ref)|sanctioned\s*plan\s*(?:no\.?|number))"
    r"[:\s]+([A-Z0-9/\-]+)",
    re.I,
)
_ISSUE_DATE_RE = re.compile(
    r"(?:issued?\s*on|date\s*of\s*issue|issue\s*date|certificate\s*date)"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_AUTHORITY_RE  = re.compile(
    r"(?:issuing\s*authority|issued?\s*by|municipal\s*(?:corporation|council)|bbmp|"
    r"ulb|panchayat|planning\s*authority)[:\s]*([A-Za-z\s,\.]+?)(?:\n|sign|date|seal|stamp)",
    re.I,
)
_FLOORS_RE     = re.compile(r"(?:no\.?\s*of\s*floors?|total\s*floors?|floor\s*count)[:\s]+(\d+)", re.I)
_USE_RE        = re.compile(r"(?:use\s*of\s*building|purpose|occupancy\s*type)[:\s]+(residential|commercial|industrial|mixed|institutional)", re.I)
_RERA_RE       = re.compile(r"(?:rera\s*(?:no\.?|number|reg))[:\s]+([A-Z0-9/\-]+)", re.I)


class OccupancyCertificateParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "occupancy_certificate"}

        m = _CERT_NO_RE.search(text)
        if m:
            result["certificate_number"] = m.group(1).strip()

        m = _CERT_TYPE_RE.search(text)
        if m:
            result["certificate_type"] = m.group(1).strip().title()

        m = _PROJECT_RE.search(text)
        if m:
            result["project_name"] = m.group(1).strip().title()

        m = _OWNER_RE.search(text)
        if m:
            result["owner_developer_name"] = m.group(1).strip().title()

        m = _PROP_ADDR_RE.search(text)
        if m:
            result["property_address"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = _PLAN_REF_RE.search(text)
        if m:
            result["approved_plan_number"] = m.group(1).strip()

        m = _ISSUE_DATE_RE.search(text)
        if m:
            result["issue_date"] = norm_date(m.group(1))

        m = _AUTHORITY_RE.search(text)
        if m:
            result["issuing_authority"] = m.group(1).strip().title()

        m = _FLOORS_RE.search(text)
        if m:
            result["total_floors"] = m.group(1)

        area = parse_area(text)
        if area:
            result["total_area"] = area

        m = _USE_RE.search(text)
        if m:
            result["building_use"] = m.group(1).strip().title()

        m = _RERA_RE.search(text)
        if m:
            result["rera_number"] = m.group(1).strip()

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
