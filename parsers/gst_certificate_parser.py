"""GST Registration Certificate parser — GSTIN / GST Identification Number."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

# GSTIN: 2-digit state code + PAN (10 chars) + 1 entity + 1 check + Z + 1 check
_GSTIN_RE     = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d][Z][A-Z\d])\b")
_LEGAL_RE     = re.compile(
    r"(?:legal\s*name\s*of\s*(?:the\s*)?business|legal\s*name|trade\s*name\s*of\s*prop)[:\s]+([A-Za-z0-9\s&,\.\-]+?)(?:\n|trade|reg|gstin|state)",
    re.I
)
_TRADE_RE     = re.compile(
    r"(?:trade\s*name)[:\s]+([A-Za-z0-9\s&,\.\-]+?)(?:\n|legal|reg|gstin|state)",
    re.I
)
_TYPE_RE      = re.compile(
    r"(?:constitution\s*of\s*business|taxpayer\s*type|type\s*of\s*taxpayer)[:\s]+"
    r"(proprietorship|partnership|private\s*limited|public\s*limited|llp|huf|trust|"
    r"society|government|regular|composition|input\s*service\s*distributor|isd)",
    re.I
)
_REG_DATE_RE  = re.compile(
    r"(?:date\s*of\s*registration|reg(?:istration)?\s*date|liability\s*date)[:\s]*"
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I
)
_CANCEL_DATE_RE = re.compile(
    r"(?:date\s*of\s*cancellation)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I
)
_STATE_RE     = re.compile(
    r"(?:state[:\s]+|place\s*of\s*business[:\s]+)?(andhra\s*pradesh|arunachal\s*pradesh|"
    r"assam|bihar|chhattisgarh|goa|gujarat|haryana|himachal\s*pradesh|jharkhand|"
    r"karnataka|kerala|madhya\s*pradesh|maharashtra|manipur|meghalaya|mizoram|nagaland|"
    r"odisha|punjab|rajasthan|sikkim|tamil\s*nadu|telangana|tripura|uttar\s*pradesh|"
    r"uttarakhand|west\s*bengal|delhi|jammu\s*and\s*kashmir|ladakh)",
    re.I
)
_STATUS_RE    = re.compile(r"(?:gstin\s*status|status)[:\s]+(active|inactive|cancelled|suspended)", re.I)
_ADDRESS_RE   = re.compile(
    r"(?:principal\s*place\s*of\s*business|place\s*of\s*business|address)[:\s]+"
    r"([A-Za-z0-9\s,/\-\.]+?)(?:\n\n|\d{6}|state|nature)",
    re.I
)
_PIN_RE       = re.compile(r"\b(\d{6})\b")
_NATURE_RE    = re.compile(
    r"(?:nature\s*of\s*(?:core\s*)?business\s*activity)[:\s]+([A-Za-z\s,;]+?)(?:\n\n|hsn|sac|\d)",
    re.I
)


def _norm_date(raw: str) -> str:
    raw = raw.strip().replace("-", "/").replace(".", "/")
    parts = raw.split("/")
    if len(parts) == 3:
        d, m, y = parts
        if len(y) == 2:
            y = ("20" if int(y) < 50 else "19") + y
        return f"{d.zfill(2)}/{m.zfill(2)}/{y}"
    return raw


class GstCertificateParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "gst_certificate"}

        m = _GSTIN_RE.search(text)
        if m:
            gstin = m.group(1)
            result["gstin"] = gstin
            # Decode state code from first 2 digits
            state_code = int(gstin[:2])
            result["gstin_state_code"] = str(state_code).zfill(2)

        m = _LEGAL_RE.search(text)
        if m:
            result["legal_name"] = m.group(1).strip()

        m = _TRADE_RE.search(text)
        if m:
            result["trade_name"] = m.group(1).strip()

        m = _TYPE_RE.search(text)
        if m:
            result["taxpayer_type"] = m.group(1).strip().title()

        m = _REG_DATE_RE.search(text)
        if m:
            result["registration_date"] = _norm_date(m.group(1))

        m = _CANCEL_DATE_RE.search(text)
        if m:
            result["cancellation_date"] = _norm_date(m.group(1))

        m = _STATUS_RE.search(text)
        if m:
            result["status"] = m.group(1).strip().title()

        m = _STATE_RE.search(text)
        if m:
            result["state"] = m.group(1).strip().title()

        m = _ADDRESS_RE.search(text)
        if m:
            result["place_of_business"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = _PIN_RE.search(text)
        if m:
            result["pin_code"] = m.group(1)

        m = _NATURE_RE.search(text)
        if m:
            result["nature_of_business"] = m.group(1).strip().title()

        result["raw_text"] = text
        return result
