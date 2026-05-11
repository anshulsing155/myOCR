"""Property Valuation Certificate / Market Value Certificate parser."""
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
)

_CERT_NO_RE    = re.compile(r"(?:certificate\s*(?:no\.?|number)|valuation\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)", re.I)
_VALUER_REG_RE = re.compile(r"(?:valuer\s*reg(?:istration)?\s*(?:no\.?|number)|ibbi\s*reg(?:istration)?)[:\s]+([A-Z0-9/\-]+)", re.I)
_PROP_ADDR_RE  = re.compile(
    r"(?:property\s*(?:address|details?|situated|description)|subject\s*property)"
    r"[:\s]+([A-Za-z0-9\s,/\-\.#]+?)(?:\n\n|district|state|\d{6}|area|valuation|market)",
    re.I,
)
_OWNER_RE      = re.compile(
    r"(?:owner(?:'s)?\s*name|name\s*of\s*(?:the\s*)?owner|applicant\s*name)"
    r"[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|address|property|valuation|purpose)",
    re.I,
)
_MKT_VALUE_RE  = re.compile(
    r"(?:market\s*value|fair\s*market\s*value|distress\s*value|"
    r"forced\s*sale\s*value|current\s*market\s*value)"
    r"[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_CIRCLE_RE     = re.compile(
    r"(?:ready\s*reckoner\s*(?:rate|value)|circle\s*rate|government\s*(?:rate|value)|"
    r"stamp\s*duty\s*value|guideline\s*value)"
    r"[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_PLOT_AREA_RE  = re.compile(
    r"(?:plot\s*area|land\s*area|site\s*area)"
    r"[:\s]*([\d,]+(?:\.\d+)?)\s*(sq\.?\s*(?:ft|meter|metre|yard)|sqft|sqmt)",
    re.I,
)
_BUA_RE        = re.compile(
    r"(?:built[\s\-]up\s*area|bua|super\s*built[\s\-]up|carpet\s*area|plinth\s*area)"
    r"[:\s]*([\d,]+(?:\.\d+)?)\s*(sq\.?\s*(?:ft|meter|metre|yard)|sqft|sqmt)",
    re.I,
)
_AGE_RE        = re.compile(r"(?:age\s*of\s*(?:the\s*)?(?:building|construction|property)|building\s*age)[:\s]+(\d+)\s*(?:years?)?", re.I)
_TYPE_RE       = re.compile(r"(?:type\s*of\s*property|property\s*type)[:\s]+(residential|commercial|industrial|agricultural|mixed|plot|flat|apartment|villa|bungalow|row\s*house|independent\s*house)", re.I)
_PURPOSE_RE    = re.compile(r"(?:purpose\s*of\s*valuation|valuation\s*purpose)[:\s]+([A-Za-z\s,/]+?)(?:\n|date|valuer)", re.I)
_VAL_DATE_RE   = re.compile(r"(?:valuation\s*date|date\s*of\s*valuation|inspection\s*date|valued\s*on)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})", re.I)
_VALUER_RE     = re.compile(r"(?:valuer(?:'s)?\s*name|name\s*of\s*(?:the\s*)?valuer|appraiser)[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|reg|qualification|date|sign)", re.I)
_BANK_RE       = re.compile(r"(?:bank|financial\s*institution|lender)[:\s]+([A-Za-z0-9\s,\.\-&]+?)(?:\n|branch|loan|property)", re.I)
_SURVEY_RE     = re.compile(r"(?:survey\s*(?:no\.?|number)|plot\s*(?:no\.?|number))[:\s]+([A-Z0-9/,\s]+?)(?:\n|area|dist|ward)", re.I)


class PropertyValuationParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "property_valuation"}

        m = _CERT_NO_RE.search(text)
        if m:
            result["certificate_number"] = m.group(1).strip()

        m = _VALUER_REG_RE.search(text)
        if m:
            result["valuer_registration_number"] = m.group(1).strip()

        m = _OWNER_RE.search(text)
        if m:
            result["owner_name"] = m.group(1).strip().title()

        m = _PROP_ADDR_RE.search(text)
        if m:
            result["property_address"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = _SURVEY_RE.search(text)
        if m:
            result["survey_plot_number"] = m.group(1).strip()

        m = _MKT_VALUE_RE.search(text)
        if m:
            result["market_value"] = clean_amount(m.group(1))

        m = _CIRCLE_RE.search(text)
        if m:
            result["circle_rate_value"] = clean_amount(m.group(1))

        m = _PLOT_AREA_RE.search(text)
        if m:
            result["plot_area"] = {"value": clean_amount(m.group(1)), "unit": m.group(2).strip()}

        m = _BUA_RE.search(text)
        if m:
            result["built_up_area"] = {"value": clean_amount(m.group(1)), "unit": m.group(2).strip()}

        m = _AGE_RE.search(text)
        if m:
            result["building_age_years"] = m.group(1)

        m = _TYPE_RE.search(text)
        if m:
            result["property_type"] = m.group(1).strip().title()

        m = _PURPOSE_RE.search(text)
        if m:
            result["valuation_purpose"] = m.group(1).strip().title()

        m = _VAL_DATE_RE.search(text)
        if m:
            result["valuation_date"] = norm_date(m.group(1))

        m = _VALUER_RE.search(text)
        if m:
            result["valuer_name"] = m.group(1).strip().title()

        m = _BANK_RE.search(text)
        if m:
            result["bank_name"] = m.group(1).strip().title()

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
