"""Degree / Diploma Certificate parser — university / technical education board."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

_NAME_LBL_RE  = re.compile(
    r"(?:this\s+is\s+to\s+certify\s+that|awarded?\s+to|conferred?\s+(?:upon|on)|"
    r"name\s*of\s*(?:the\s*)?(?:student|candidate)|student[:\s]+|candidate[:\s]+)"
    r"\s*([A-Z][A-Za-z\s\.]+?)(?:\n|has|,|s/o|d/o|roll|enrol|reg|has\s+been)",
    re.I
)
_DEGREE_RE    = re.compile(
    r"(?:degree\s*of|bachelor\s*of|master\s*of|doctor\s*of|diploma\s*(?:in|of)|"
    r"awarded?\s+the\s+degree\s+of)\s+([A-Za-z\s\(\)&/,\.]+?)(?:\n|in\s|with|from|year|roll|\d{4})",
    re.I
)
_SPEC_RE      = re.compile(
    r"(?:in\s+the\s+(?:branch|field|stream|specialization|discipline)\s+of|specialization[:\s]+|branch[:\s]+)"
    r"([A-Za-z\s\(\)&/]+?)(?:\n|from|year|roll|\d{4}|with)",
    re.I
)
_UNIV_RE      = re.compile(
    r"(?:university\s*of|from\s*(?:the\s*)?|affiliated\s*to)\s*([A-Za-z\s]+?(?:university|institute|college|deemed|iit|nit|iim)[A-Za-z\s,]*?)(?:\n|in\s+the|\d{4}|year)",
    re.I
)
_INST_RE      = re.compile(
    r"(?:college\s*of|institute\s*of|institution[:\s]+|college[:\s]+)([A-Za-z\s,&\.]+?)(?:\n|university|year|\d{4})",
    re.I
)
_ROLL_RE      = re.compile(r"(?:roll\s*(?:no\.?|number)|exam\s*(?:no\.?|number))[:\s]+([A-Z0-9/]+)", re.I)
_ENROLL_RE    = re.compile(r"(?:enrol{1,2}ment\s*(?:no\.?|number)|admission\s*(?:no\.?|number))[:\s]+([A-Z0-9/]+)", re.I)
_YEAR_RE      = re.compile(r"(?:year\s*of\s*(?:passing|graduation|completion)|passed\s*in|year)[:\s]*(\d{4})", re.I)
_CLASS_RE     = re.compile(
    r"\b(first\s*class(?:\s*with\s*distinction)?|second\s*class|third\s*class|"
    r"distinction|merit|pass\s*class|honours?)\b",
    re.I
)
_CGPA_RE      = re.compile(r"(?:cgpa|gpa|grade\s*point\s*average)[:\s]*([\d\.]+)\s*(?:out\s*of\s*[\d\.]+)?", re.I)
_PERCENT_RE   = re.compile(r"(?:percentage|percent|marks\s*obtained)[:\s]*([\d\.]+)\s*%?", re.I)
_DOB_RE       = re.compile(r"(?:date\s*of\s*birth|dob)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})", re.I)
_CERT_NO_RE   = re.compile(r"(?:certificate\s*(?:no\.?|number)|degree\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)", re.I)
_ISSUE_DATE_RE = re.compile(r"(?:date\s*of\s*issue|convocation\s*date|issued?\s*on)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})", re.I)

_MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    "january": "01", "february": "02", "march": "03", "april": "04",
    "june": "06", "july": "07", "august": "08", "september": "09",
    "october": "10", "november": "11", "december": "12",
}


def _norm_date(raw: str) -> str:
    raw = raw.strip()
    m = re.match(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", raw)
    if m:
        d, mon, y = m.groups()
        mn = _MONTH_MAP.get(mon.lower(), "00")
        return f"{d.zfill(2)}/{mn}/{y}"
    raw = raw.replace("-", "/").replace(".", "/")
    parts = raw.split("/")
    if len(parts) == 3:
        d, mn, y = parts
        if len(y) == 2:
            y = ("20" if int(y) < 50 else "19") + y
        return f"{d.zfill(2)}/{mn.zfill(2)}/{y}"
    return raw


class DegreeCertificateParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "degree_certificate"}

        m = _CERT_NO_RE.search(text)
        if m:
            result["certificate_number"] = m.group(1).strip()

        m = _NAME_LBL_RE.search(text)
        if m:
            result["student_name"] = m.group(1).strip().title()

        m = _DEGREE_RE.search(text)
        if m:
            result["degree_name"] = m.group(1).strip().title()

        m = _SPEC_RE.search(text)
        if m:
            result["specialization"] = m.group(1).strip().title()

        m = _UNIV_RE.search(text)
        if m:
            result["university"] = m.group(1).strip().title()

        m = _INST_RE.search(text)
        if m:
            result["institution"] = m.group(1).strip().title()

        m = _ROLL_RE.search(text)
        if m:
            result["roll_number"] = m.group(1).strip()

        m = _ENROLL_RE.search(text)
        if m:
            result["enrollment_number"] = m.group(1).strip()

        m = _YEAR_RE.search(text)
        if m:
            result["year_of_passing"] = m.group(1)

        m = _CLASS_RE.search(text)
        if m:
            result["class_of_degree"] = m.group(1).strip().title()

        m = _CGPA_RE.search(text)
        if m:
            result["cgpa"] = m.group(1)

        m = _PERCENT_RE.search(text)
        if m:
            result["percentage"] = m.group(1)

        m = _DOB_RE.search(text)
        if m:
            result["date_of_birth"] = _norm_date(m.group(1))

        m = _ISSUE_DATE_RE.search(text)
        if m:
            result["issue_date"] = _norm_date(m.group(1))

        result["raw_text"] = text
        return result
