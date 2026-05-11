"""GST Registration Certificate parser — GSTIN / GST Identification Number."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

# GSTIN: 2-digit state code + PAN (10 chars) + 1 entity + 1 check + Z + 1 check
_GSTIN_RE     = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d][Z][A-Z\d])\b")
# Stop on newline (primary) or next field label word as a whole word (\b) to avoid
# stopping inside words like "registered", "legitimate", "stated", etc.
_LEGAL_RE     = re.compile(
    r"(?:legal\s*name\s*of\s*(?:the\s*)?business|legal\s*name|trade\s*name\s*of\s*prop)[:\s]+"
    r"([A-Za-z0-9\s&,\.\-]+?)(?:\n|\b(?:trade|reg(?:istration)?|gstin|taxpayer)\b)",
    re.I
)
_TRADE_RE     = re.compile(
    r"(?:trade\s*name)[:\s]+([A-Za-z0-9\s&,\.\-]+?)(?:\n|\b(?:legal|reg(?:istration)?|gstin)\b)",
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


# GSTIN first-2-digit state code → state name (as per GSTIN format)
_GSTIN_STATE_MAP: dict[int, str] = {
    1: "Jammu & Kashmir", 2: "Himachal Pradesh", 3: "Punjab", 4: "Chandigarh",
    5: "Uttarakhand", 6: "Haryana", 7: "Delhi", 8: "Rajasthan", 9: "Uttar Pradesh",
    10: "Bihar", 11: "Sikkim", 12: "Arunachal Pradesh", 13: "Nagaland",
    14: "Manipur", 15: "Mizoram", 16: "Tripura", 17: "Meghalaya",
    18: "Assam", 19: "West Bengal", 20: "Jharkhand", 21: "Odisha",
    22: "Chhattisgarh", 23: "Madhya Pradesh", 24: "Gujarat",
    26: "Daman & Diu / Dadra & Nagar Haveli", 27: "Maharashtra",
    28: "Andhra Pradesh", 29: "Karnataka", 30: "Goa", 31: "Lakshadweep",
    32: "Kerala", 33: "Tamil Nadu", 34: "Puducherry", 35: "Andaman & Nicobar",
    36: "Telangana", 37: "Andhra Pradesh (New)", 38: "Ladakh",
}


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
            state_name = _GSTIN_STATE_MAP.get(state_code)
            if state_name:
                result["gstin_state"] = state_name

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
