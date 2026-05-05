"""Lease Deed / Leave & License Agreement / Rental Agreement parser."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser
from parsers.realestate._helpers import (
    norm_date, parse_area, clean_amount, PIN_RE, STATE_RE, DISTRICT_RE,
    SRO_RE, STAMP_RE, REGN_NO_RE,
)

_DEED_TYPE_RE  = re.compile(
    r"\b(lease\s*deed|lease\s*agreement|leave\s*(?:and|&)\s*license\s*agreement|"
    r"rental\s*agreement|rent\s*agreement|tenancy\s*agreement)\b",
    re.I,
)
_EXEC_DATE_RE  = re.compile(
    r"(?:executed?\s*(?:on|this)|this\s*(?:deed|agreement)\s*(?:is\s*)?(?:made|dated?))"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.I,
)
_REG_DATE_RE   = re.compile(
    r"(?:registered?\s*on|registration\s*date)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_LESSOR_RE     = re.compile(
    r"(?:lessor|landlord|licensor|owner|first\s*party)"
    r"[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|hereinafter|s/o|d/o|w/o|age|address|lessee)",
    re.I,
)
_LESSEE_RE     = re.compile(
    r"(?:lessee|tenant|licensee|second\s*party)"
    r"[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|hereinafter|s/o|d/o|w/o|age|address|lessor)",
    re.I,
)
_PROP_ADDR_RE  = re.compile(
    r"(?:property\s*(?:address|situated|known\s*as|premises)|leased\s*premises|"
    r"the\s*said\s*premises)[:\s]+([A-Za-z0-9\s,/\-\.#]+?)(?:\n\n|district|state|\d{6}|lease|term)",
    re.I,
)
_PERIOD_RE     = re.compile(
    r"(?:lease\s*period|rental\s*period|tenancy\s*period|term\s*of\s*(?:lease|tenancy))"
    r"[:\s]+(\d+)\s*(months?|years?)",
    re.I,
)
_START_DATE_RE = re.compile(
    r"(?:commencement\s*date|from\s*(?:the\s*)?date|lease\s*(?:starts?|begins?|commences?)\s*(?:from|on))"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_END_DATE_RE   = re.compile(
    r"(?:expiry\s*date|end\s*date|termination\s*date|valid\s*(?:till|upto|until))"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_RENT_RE       = re.compile(
    r"(?:monthly\s*rent|monthly\s*rental|rent\s*per\s*month|rent\s*amount)"
    r"[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_DEPOSIT_RE    = re.compile(
    r"(?:security\s*deposit|interest\s*free\s*deposit|refundable\s*deposit)"
    r"[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_LOCKIN_RE     = re.compile(r"(?:lock[\s\-]?in\s*period)[:\s]+(\d+)\s*(months?|years?)", re.I)
_NOTICE_RE     = re.compile(r"(?:notice\s*period)[:\s]+(\d+)\s*(months?|days?|years?)", re.I)
_ESCALATION_RE = re.compile(r"(?:rent\s*(?:escalation|increment|increase))[:\s]+(\d+)\s*%", re.I)
_MAINTENANCE_RE = re.compile(
    r"(?:maintenance\s*charges?|maintenance\s*fee)"
    r"[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)


class LeaseDeedParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "lease_deed"}

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

        m = _LESSOR_RE.search(text)
        if m:
            result["lessor_name"] = m.group(1).strip().title()

        m = _LESSEE_RE.search(text)
        if m:
            result["lessee_name"] = m.group(1).strip().title()

        m = _PROP_ADDR_RE.search(text)
        if m:
            result["property_address"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = _PERIOD_RE.search(text)
        if m:
            result["lease_period"] = f"{m.group(1)} {m.group(2)}"

        m = _START_DATE_RE.search(text)
        if m:
            result["commencement_date"] = norm_date(m.group(1))

        m = _END_DATE_RE.search(text)
        if m:
            result["expiry_date"] = norm_date(m.group(1))

        m = _RENT_RE.search(text)
        if m:
            result["monthly_rent"] = clean_amount(m.group(1))

        m = _DEPOSIT_RE.search(text)
        if m:
            result["security_deposit"] = clean_amount(m.group(1))

        m = _LOCKIN_RE.search(text)
        if m:
            result["lock_in_period"] = f"{m.group(1)} {m.group(2)}"

        m = _NOTICE_RE.search(text)
        if m:
            result["notice_period"] = f"{m.group(1)} {m.group(2)}"

        m = _ESCALATION_RE.search(text)
        if m:
            result["rent_escalation_percent"] = m.group(1)

        m = _MAINTENANCE_RE.search(text)
        if m:
            result["maintenance_charges"] = clean_amount(m.group(1))

        area = parse_area(text)
        if area:
            result["area"] = area

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
