"""Indian Passport parser."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

# Passport number: letter (A/B/C/E/F/G/H/J-N/P/R-Z) + 7 digits
_PASSPORT_RE  = re.compile(r"\b([A-PR-WY][0-9]{7})\b")
_DOB_LBL_RE   = re.compile(
    r"(?:date\s*of\s*birth|dob|d\.o\.b|birth)[^\d]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{2}\s*[A-Z]{3}\s*\d{4})",
    re.I
)
_ISSUE_RE     = re.compile(
    r"(?:date\s*of\s*issue|issued?\s*on|issue\s*date)[^\d]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{2}\s*[A-Z]{3}\s*\d{4})",
    re.I
)
_EXPIRY_RE    = re.compile(
    r"(?:date\s*of\s*expiry|expiry|valid\s*(?:till|until|upto))[^\d]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{2}\s*[A-Z]{3}\s*\d{4})",
    re.I
)
_GENDER_RE    = re.compile(r"\b(male|female|m|f)\b", re.I)
_NATIONALITY_RE = re.compile(r"(?:nationality)[:\s]+([A-Z]+)", re.I)
_PLACE_BIRTH_RE = re.compile(r"(?:place\s*of\s*birth)[:\s]+([A-Za-z\s,]+?)(?:\n|date)", re.I)
_PLACE_ISSUE_RE = re.compile(r"(?:place\s*of\s*issue)[:\s]+([A-Za-z\s,]+?)(?:\n|date)", re.I)
_FILE_NO_RE   = re.compile(r"\bfile\s*(?:no\.?|number)?[:\s]+([A-Z0-9/]+)\b", re.I)
# MRZ: two lines of 44 chars with < delimiters
_MRZ_LINE_RE  = re.compile(r"([A-Z0-9<]{20,44})")

_MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


def _norm_date(raw: str) -> str:
    raw = raw.strip()
    # "15 JAN 2025" or "15/01/2025" or "15-01-2025"
    m = re.match(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", raw)
    if m:
        d, mon, y = m.groups()
        month_num = _MONTH_MAP.get(mon.lower(), mon)
        return f"{d.zfill(2)}/{month_num}/{y}"
    raw = raw.replace("-", "/").replace(".", "/")
    parts = raw.split("/")
    if len(parts) == 3:
        d, mn, y = parts
        if len(y) == 2:
            y = ("20" if int(y) < 50 else "19") + y
        return f"{d.zfill(2)}/{mn.zfill(2)}/{y}"
    return raw


class PassportParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "passport", "nationality": "INDIAN"}

        # Passport number
        m = _PASSPORT_RE.search(text)
        if m:
            result["passport_number"] = m.group(1)

        # Dates
        for field, pattern in [
            ("date_of_birth", _DOB_LBL_RE),
            ("date_of_issue", _ISSUE_RE),
            ("date_of_expiry", _EXPIRY_RE),
        ]:
            m = pattern.search(text)
            if m:
                result[field] = _norm_date(m.group(1))

        # Gender
        m = _GENDER_RE.search(text)
        if m:
            g = m.group(1).upper()
            result["sex"] = "F" if g in ("F", "FEMALE") else "M"

        # Places
        m = _PLACE_BIRTH_RE.search(text)
        if m:
            result["place_of_birth"] = m.group(1).strip().title()
        m = _PLACE_ISSUE_RE.search(text)
        if m:
            result["place_of_issue"] = m.group(1).strip().title()

        # Nationality override
        m = _NATIONALITY_RE.search(text)
        if m:
            result["nationality"] = m.group(1).strip().upper()

        # File number
        m = _FILE_NO_RE.search(text)
        if m:
            result["file_number"] = m.group(1).strip()

        # MRZ lines (top-2 longest all-caps lines with < chars)
        mrz_candidates = [l.strip() for l in text.splitlines()
                          if re.match(r"^[A-Z0-9<]{15,}", l.strip())]
        if len(mrz_candidates) >= 2:
            result["mrz_line1"] = mrz_candidates[0]
            result["mrz_line2"] = mrz_candidates[1]
            # Parse name from MRZ line 1: P<IND<SURNAME<<GIVEN<<
            mrz1 = mrz_candidates[0]
            if mrz1.startswith("P<") or mrz1.startswith("P<IND"):
                name_part = mrz1[5:]  # skip P<IND
                parts = name_part.split("<<", 1)
                if len(parts) == 2:
                    surname = parts[0].replace("<", " ").strip().title()
                    given   = parts[1].replace("<", " ").strip().title()
                    result["surname"]    = surname
                    result["given_name"] = given
                    result["name"]       = f"{given} {surname}".strip()

        # Fallback name from labeled text
        if "name" not in result:
            for line in text.splitlines():
                words = line.strip().split()
                if (2 <= len(words) <= 4
                        and all(w.replace(".", "").isalpha() for w in words)
                        and all(w.isupper() for w in words)):
                    result["name"] = line.strip().title()
                    break

        result["raw_text"] = text
        return result
