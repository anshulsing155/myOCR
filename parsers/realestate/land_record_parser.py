"""Land Record parser — Khasra/Khatauni (UP/Delhi), 7/12 Satbara (Maharashtra),
Jamabandi/Fard (Punjab/Haryana), RTC (Karnataka), Patta (TN/AP/TS)."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser
from parsers.realestate._helpers import (
    DISTRICT_RE,
    PIN_RE,
    STATE_RE,
    parse_area,
)

_KHASRA_RE   = re.compile(r"(?:khasra\s*(?:no\.?|number)|gata\s*(?:no\.?|number)|dag\s*(?:no\.?|number))[:\s]+([A-Z0-9/,\s]+?)(?:\n|area|land|khatauni|village)", re.I)
_GAT_RE      = re.compile(r"(?:gat\s*(?:no\.?|number)|s\.?\s*no\.?|survey\s*(?:no\.?|number))[:\s]+([A-Z0-9/,\s]+?)(?:\n|area|land|village)", re.I)
_KHATAUNI_RE = re.compile(r"(?:khatauni\s*(?:no\.?|number)|account\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)", re.I)
_PATTA_RE    = re.compile(r"(?:patta\s*(?:no\.?|number)|pattedar\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)", re.I)
_OWNER_RE    = re.compile(
    r"(?:khatedar|owner(?:'s)?\s*name|occupant|khatedaar|bhumiswami|pattadar\s*name|"
    r"ryot\s*name|name\s*of\s*(?:the\s*)?owner)[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|s/o|d/o|address|area|khasra|survey)",
    re.I,
)
_CULTIVATOR_RE = re.compile(
    r"(?:cultivator|tenant|adhiwasi|bataidar|name\s*of\s*cultivator)[:\s]+"
    r"([A-Z][A-Za-z\s\.]+?)(?:\n|area|khasra|village)",
    re.I,
)
_LAND_CLASS_RE = re.compile(
    r"(?:land\s*(?:type|class|classification|use|nature)|nature\s*of\s*land|chahi|"
    r"abi|barani|banjar|jungle)[:\s]+(irrigated|un[\s\-]?irrigated|dry|wet|"
    r"agricultural|residential|commercial|fallow|banjar|forest|chahi|abi|barani)",
    re.I,
)
_VILLAGE_RE  = re.compile(r"(?:village|gram|mauza|halqa|tanda)[:\s]+([A-Za-z\s]+?)(?:\n|tehsil|taluk|block|district)", re.I)
_TEHSIL_RE   = re.compile(r"(?:tehsil|taluk|taluka|mandal|block|hobli)[:\s]+([A-Za-z\s]+?)(?:\n|district|state)", re.I)
_FY_RE       = re.compile(r"(?:financial\s*year|fasli\s*year|year)[:\s]+(\d{4}[\-/]\d{2,4})", re.I)
_JAMABANDI_RE = re.compile(r"(?:jamabandi\s*(?:no\.?|number)|fard\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)", re.I)
_MUTATION_RE  = re.compile(r"(?:mutation\s*(?:no\.?|number)|intkaal\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)", re.I)

# Record type detection
_RECORD_TYPE_MAP = [
    (re.compile(r"\b(7[\s/]12|satbara|saat\s*baara)\b", re.I), "7/12 Extract"),
    (re.compile(r"\bjamabandi\b", re.I),                        "Jamabandi"),
    (re.compile(r"\bfard\b", re.I),                             "Fard"),
    (re.compile(r"\brtc\b|record\s*of\s*rights.*tenancy", re.I), "RTC"),
    (re.compile(r"\bpatta\b", re.I),                            "Patta"),
    (re.compile(r"\bkhatauni\b", re.I),                         "Khatauni"),
    (re.compile(r"\bkhasra\b", re.I),                           "Khasra"),
]


class LandRecordParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "land_record"}

        # Detect specific record type
        for pattern, label in _RECORD_TYPE_MAP:
            if pattern.search(text):
                result["record_type"] = label
                break

        # Survey / Khasra numbers
        m = _KHASRA_RE.search(text) or _GAT_RE.search(text)
        if m:
            result["survey_khasra_number"] = m.group(1).strip()

        m = _KHATAUNI_RE.search(text)
        if m:
            result["khatauni_number"] = m.group(1).strip()

        m = _PATTA_RE.search(text)
        if m:
            result["patta_number"] = m.group(1).strip()

        m = _JAMABANDI_RE.search(text)
        if m:
            result["jamabandi_number"] = m.group(1).strip()

        m = _MUTATION_RE.search(text)
        if m:
            result["mutation_number"] = m.group(1).strip()

        m = _OWNER_RE.search(text)
        if m:
            result["owner_name"] = m.group(1).strip().title()

        m = _CULTIVATOR_RE.search(text)
        if m:
            result["cultivator_name"] = m.group(1).strip().title()

        area = parse_area(text)
        if area:
            result["area"] = area

        m = _LAND_CLASS_RE.search(text)
        if m:
            result["land_classification"] = m.group(1).strip().title()

        m = _VILLAGE_RE.search(text)
        if m:
            result["village"] = m.group(1).strip().title()

        m = _TEHSIL_RE.search(text)
        if m:
            result["tehsil"] = m.group(1).strip().title()

        m = _FY_RE.search(text)
        if m:
            result["financial_year"] = m.group(1)

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
