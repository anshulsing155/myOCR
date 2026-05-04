"""Indian Driving Licence parser.

Extracts:
  dl_number, issuing_state, name, date_of_birth, relation_name,
  address, blood_group, organ_donor, vehicle_classes,
  issue_date, validity_nt, validity_tr, date_of_first_issue, issued_by
"""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

# ── DL number ─────────────────────────────────────────────────────────────────
# State(2) + District(2) + optional separator + Year(4) + Serial(7) = 15 digits
_DL_RE = re.compile(
    r"\b([A-Z]{2}[-\s]?\d{2}\s+\d{4}\d{7})\b"            # "UP61 20130002817"
    r"|\b([A-Z]{2}[-\s]?\d{2}[-\s]\d{4}[-\s]\d{7})\b"    # "UP-61-2013-0002817"
    r"|\b([A-Z]{2}\d{13})\b",                              # compact 15-digit
)

# ── Date patterns ─────────────────────────────────────────────────────────────
_DP = r"\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}"

# DL cards put "Issue Date   Validity (NT)" as a two-column header;
# dates appear on the NEXT line side-by-side → parse together
_DATE_BLOCK_RE = re.compile(
    r"issue\s+date.*?validity\s*\(nt\)[^\n]*\n\s*"
    r"(" + _DP + r")\s+(" + _DP + r")",
    re.I,
)
_ISSUE_RE      = re.compile(r"issue\s+date\s*[:\-]?\s*(" + _DP + r")", re.I)
_VALIDITY_NT   = re.compile(r"validity\s*\(nt\)\s*[:\-]?\s*\n?\s*(" + _DP + r")", re.I)
_VALIDITY_TR   = re.compile(r"validity\s*\(tr\)\s*[:\-]?\s*\n?\s*(" + _DP + r")", re.I)
# Date of First Issue often in parens: "(04-03-2013)"
_FIRST_ISSUE   = re.compile(
    r"date\s+of\s+first\s+issue[^\n]*\n?\s*\(?\s*(" + _DP + r")\)?", re.I)
_DOB_RE        = re.compile(
    r"(?:date\s+of\s+birth|d\.?\s*o\.?\s*b\.?|dob)\s*[:\-]?\s*(" + _DP + r")", re.I)

# ── Personal fields ───────────────────────────────────────────────────────────
_NAME_RE = re.compile(
    r"(?:^|\n)\s*(?:name\s*[:\-]?\s*)([A-Z][A-Za-z\s\.]{2,50}?)"
    r"(?=\s+(?:blood|organ|date|dob|son|daughter|wife|address|\d)|\n|$)",
    re.I | re.MULTILINE,
)
# "Son/Daughter/Wife of:" or just "S/o:"
_RELATION_RE = re.compile(
    r"(?:son\s*/\s*daughter\s*/\s*wife\s+of|s/o|d/o|w/o|so of|do of)\s*[:\-]?\s*"
    r"([A-Z][A-Za-z\s\.]{2,50}?)(?:\n|$)",
    re.I | re.MULTILINE,
)
# Blood group: A+, B-, O+VE, AB-VE, A+ VE
_BLOOD_RE = re.compile(
    r"blood\s*(?:group|type|grp)?\s*[:\-]?\s*(A|B|AB|O)\s*([+\-])\s*(?:VE|ve)?",
    re.I,
)
_ORGAN_RE = re.compile(r"organ\s+donor\s*[:\-]?\s*([YyNn](?:es|o)?)", re.I)
_ISSUED_BY_RE = re.compile(
    r"issued\s+by\s*[:\-]?\s*([A-Za-z][A-Za-z\s]{2,40}?)(?:\n|$)",
    re.I | re.MULTILINE,
)

# ── Vehicle class ─────────────────────────────────────────────────────────────
# Common Indian DL vehicle class codes
_VEHICLE_CLASS_RE = re.compile(
    r"\b(LMV|MCWG|MCWOG|MGV|HGV|HMV|LDRXCV|TRANS|NT|TR|LMV-NT|LMV-TR)\b",
    re.I,
)
_VEHICLE_AUTH_RE = re.compile(
    r"(?:authorised\s*(?:to\s*drive)?|vehicle\s*class|class\s*of\s*vehicle)[:\s]*"
    r"((?:LMV|MCWG|MCWOG|MGV|HGV|HMV|TRANS|NT|TR|LMV-NT|LMV-TR)"
    r"(?:[,/\s]+(?:LMV|MCWG|MCWOG|MGV|HGV|HMV|TRANS|NT|TR|LMV-NT|LMV-TR))*)",
    re.I,
)

# ── Address ───────────────────────────────────────────────────────────────────
_ADDR_RE = re.compile(
    r"address\s*[:\-]?\s*(.+?)(?=\n(?:date|son|daughter|organ|blood|issued|validity|class|\Z)|\Z)",
    re.I | re.DOTALL,
)
_PIN_RE = re.compile(r"\b(\d{6})\b")

# ── State code → full name ─────────────────────────────────────────────────────
_STATE = {
    "AP":"Andhra Pradesh","AR":"Arunachal Pradesh","AS":"Assam",
    "BR":"Bihar","CG":"Chhattisgarh","GA":"Goa","GJ":"Gujarat",
    "HR":"Haryana","HP":"Himachal Pradesh","JK":"Jammu & Kashmir",
    "JH":"Jharkhand","KA":"Karnataka","KL":"Kerala","MP":"Madhya Pradesh",
    "MH":"Maharashtra","MN":"Manipur","ML":"Meghalaya","MZ":"Mizoram",
    "NL":"Nagaland","OD":"Odisha","PB":"Punjab","RJ":"Rajasthan",
    "SK":"Sikkim","TN":"Tamil Nadu","TS":"Telangana","TR":"Tripura",
    "UP":"Uttar Pradesh","UK":"Uttarakhand","WB":"West Bengal",
    "AN":"Andaman & Nicobar","CH":"Chandigarh","DL":"Delhi",
    "DN":"Dadra & Nagar Haveli","DD":"Daman & Diu",
    "LD":"Lakshadweep","PY":"Puducherry",
}


def _nd(s: str) -> str:
    """Normalise date separators to DD/MM/YYYY."""
    parts = re.split(r"[-\./]", s)
    if len(parts) == 3:
        d, mo, y = parts
        if len(y) == 2:
            y = "20" + y if int(y) < 50 else "19" + y
        return f"{d.zfill(2)}/{mo.zfill(2)}/{y}"
    return s


class DrivingLicenseParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "driving_license"}

        # ── DL number + issuing state ──────────────────────────────────────────
        m = _DL_RE.search(text)
        if m:
            raw = next(g for g in m.groups() if g)
            dl = re.sub(r"[\s\-]+", " ", raw.strip()).upper()
            result["dl_number"] = dl
            code = raw[:2].upper().replace("-", "").replace(" ", "")
            if code in _STATE:
                result["issuing_state"] = _STATE[code]

        # ── Dates (two-column header block first) ──────────────────────────────
        mb = _DATE_BLOCK_RE.search(text)
        if mb:
            result["issue_date"]  = _nd(mb.group(1))
            result["validity_nt"] = _nd(mb.group(2))
        else:
            mi = _ISSUE_RE.search(text)
            if mi:
                result["issue_date"] = _nd(mi.group(1))
            mn = _VALIDITY_NT.search(text)
            if mn:
                result["validity_nt"] = _nd(mn.group(1))

        m = _VALIDITY_TR.search(text)
        if m:
            result["validity_tr"] = _nd(m.group(1))

        m = _FIRST_ISSUE.search(text)
        if m:
            result["date_of_first_issue"] = _nd(m.group(1))

        m = _DOB_RE.search(text)
        if m:
            result["date_of_birth"] = _nd(m.group(1))

        # ── Personal ──────────────────────────────────────────────────────────
        m = _NAME_RE.search(text)
        if m:
            result["name"] = m.group(1).strip()

        m = _RELATION_RE.search(text)
        if m:
            result["relation_name"] = m.group(1).strip()

        m = _BLOOD_RE.search(text)
        if m:
            sign = "+" if m.group(2) == "+" else "-"
            result["blood_group"] = m.group(1).upper() + sign

        m = _ORGAN_RE.search(text)
        if m:
            result["organ_donor"] = "Yes" if m.group(1).upper().startswith("Y") else "No"

        # ── Vehicle classes ───────────────────────────────────────────────────
        m = _VEHICLE_AUTH_RE.search(text)
        if m:
            classes = re.split(r"[,/\s]+", m.group(1).upper().strip())
            result["vehicle_classes"] = [c for c in classes if c]
        else:
            classes = _VEHICLE_CLASS_RE.findall(text)
            if classes:
                result["vehicle_classes"] = list(dict.fromkeys(c.upper() for c in classes))

        # ── Issued by ─────────────────────────────────────────────────────────
        m = _ISSUED_BY_RE.search(text)
        if m:
            issued = m.group(1).strip()
            if len(issued) >= 3 and not re.search(r"\d", issued):
                result["issued_by"] = issued

        # ── Address ───────────────────────────────────────────────────────────
        m = _ADDR_RE.search(text)
        if m:
            addr = re.sub(r"\s+", " ", m.group(1)).strip()
            if 5 <= len(addr) <= 200:
                result["address"] = addr
                pin_m = _PIN_RE.search(addr)
                if pin_m:
                    result["pin_code"] = pin_m.group(1)

        result["raw_text"] = text
        return result
