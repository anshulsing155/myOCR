"""Vehicle Registration Certificate (RC) parser — Ministry of Road Transport."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

# Reg number: state(2) + district(2) + series(1-2 letters) + number(4 digits)
_REG_RE       = re.compile(r"\b([A-Z]{2}[\s\-]?\d{1,2}[\s\-]?[A-Z]{1,3}[\s\-]?\d{1,4})\b")
_CHASSIS_RE   = re.compile(r"(?:chassis\s*(?:no\.?|number)?)[:\s]+([A-Z0-9]{10,20})", re.I)
_ENGINE_RE    = re.compile(r"(?:engine\s*(?:no\.?|number)?)[:\s]+([A-Z0-9]{6,20})", re.I)
_DATE_RE      = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
_REG_DATE_RE  = re.compile(
    r"(?:reg(?:istration)?\s*date|date\s*of\s*reg(?:istration)?)[:\s]+(\d{2}/\d{2}/\d{4})",
    re.I
)
_INSUR_RE     = re.compile(
    r"(?:insurance\s*(?:valid(?:ity)?|expiry|upto)?)[:\s]+(\d{2}/\d{2}/\d{4})",
    re.I
)
_FITNESS_RE   = re.compile(
    r"(?:fitness\s*(?:valid(?:ity)?|upto|expiry)?)[:\s]+(\d{2}/\d{2}/\d{4})",
    re.I
)
_TAX_RE       = re.compile(
    r"(?:tax\s*(?:valid(?:ity)?|upto|expiry|paid\s*upto)?)[:\s]+(\d{2}/\d{2}/\d{4})",
    re.I
)
_FUEL_RE      = re.compile(
    r"(?:fuel\s*type|propulsion)[:\s]+(petrol|diesel|cng|electric|hybrid|lpg|ethanol)",
    re.I
)
_COLOR_RE     = re.compile(r"(?:colour|color)[:\s]+([A-Za-z/]+)", re.I)
_CLASS_RE     = re.compile(
    r"(?:vehicle\s*class|class\s*of\s*vehicle)[:\s]+([A-Za-z0-9\s/]+?)(?:\n|seating)",
    re.I
)
_SEATING_RE   = re.compile(r"(?:seating\s*capacity|seats?)[:\s]+(\d+)", re.I)
_MAKER_RE     = re.compile(r"(?:maker|manufacturer|make)[:\s]+([A-Za-z0-9\s]+?)(?:\n|model)", re.I)
_MODEL_RE     = re.compile(r"(?:model)[:\s]+([A-Za-z0-9\s\-]+?)(?:\n|year|fuel)", re.I)
_OWNER_RE     = re.compile(r"(?:owner(?:'s)?\s*name|registered\s*owner)[:\s]+([A-Z][A-Za-z\s]+?)(?:\n|address|s/o|w/o|d/o)", re.I)
_PIN_RE       = re.compile(r"\b(\d{6})\b")
_PUCC_RE      = re.compile(r"(?:pucc?\s*(?:valid|expiry|upto)?)[:\s]+(\d{2}/\d{2}/\d{4})", re.I)


class VehicleRcParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "vehicle_rc"}

        # Registration number
        m = _REG_RE.search(text)
        if m:
            result["registration_number"] = re.sub(r"[\s\-]", "", m.group(1))

        # Owner name
        m = _OWNER_RE.search(text)
        if m:
            result["owner_name"] = m.group(1).strip().title()

        # Technical details
        for field, pattern in [
            ("chassis_number", _CHASSIS_RE),
            ("engine_number",  _ENGINE_RE),
            ("fuel_type",      _FUEL_RE),
            ("color",          _COLOR_RE),
            ("vehicle_class",  _CLASS_RE),
            ("seating_capacity", _SEATING_RE),
            ("maker",          _MAKER_RE),
            ("model",          _MODEL_RE),
        ]:
            m = pattern.search(text)
            if m:
                result[field] = m.group(1).strip().upper() if field in (
                    "chassis_number", "engine_number"
                ) else m.group(1).strip().title()

        # Dates
        for field, pattern in [
            ("registration_date", _REG_DATE_RE),
            ("insurance_upto",    _INSUR_RE),
            ("fitness_upto",      _FITNESS_RE),
            ("tax_upto",          _TAX_RE),
            ("pucc_upto",         _PUCC_RE),
        ]:
            m = pattern.search(text)
            if m:
                result[field] = m.group(1)

        # PIN from address
        m = _PIN_RE.search(text)
        if m:
            result["pin_code"] = m.group(1)

        result["raw_text"] = text
        return result
