"""Voter ID (EPIC) card parser — Election Commission of India."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

# EPIC number: 3-letter state code + 7 digits (some states use 2+7 or ECI format)
_EPIC_RE    = re.compile(r"\b([A-Z]{2,3}\d{7})\b")
_DOB_LBL_RE = re.compile(
    r"(?:date\s*of\s*birth|dob|d\.o\.b|born\s*on)[^\d]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})", re.I
)
_DOB_BARE_RE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
_DATE_RE     = re.compile(r"\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b")
_GENDER_RE   = re.compile(r"\b(male|female|transgender|mahila|purush)\b", re.I)
_AGE_RE      = re.compile(r"\bage[:\s]*(\d{2,3})\b", re.I)
_PIN_RE      = re.compile(r"\b(\d{6})\b")
_PART_RE     = re.compile(r"part\s*(?:no\.?|number)?[:\s]*(\d+)", re.I)
_RELATION_RE = re.compile(
    r"\b(?:s/o|d/o|w/o|h/o|son\s+of|daughter\s+of|wife\s+of|husband\s+of|"
    r"father[:\s]+|mother[:\s]+|guardian[:\s]+)\s*:?\s*([A-Z][A-Za-z\s]+?)(?:\n|$|\d)",
    re.I
)
_STATES = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
    "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya",
    "mizoram", "nagaland", "odisha", "punjab", "rajasthan", "sikkim",
    "tamil nadu", "telangana", "tripura", "uttar pradesh", "uttarakhand",
    "west bengal", "delhi", "jammu and kashmir", "ladakh",
    "andaman and nicobar", "chandigarh", "dadra", "lakshadweep", "puducherry",
}
_SKIP_WORDS = {
    "election", "commission", "india", "voter", "identity", "card", "photo",
    "government", "state", "elector", "eci", "serial", "epic",
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


def _clean_name(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().title()


class VoterIdParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        lower = text.lower()
        result: dict[str, Any] = {"doc_type": "voter_id"}

        # EPIC number
        m = _EPIC_RE.search(text)
        if m:
            result["epic_number"] = m.group(1)

        # Gender
        m = _GENDER_RE.search(lower)
        if m:
            g = m.group(1).lower()
            result["gender"] = "Female" if g in ("female", "mahila") else (
                "Transgender" if g == "transgender" else "Male"
            )

        # Age
        m = _AGE_RE.search(text)
        if m:
            result["age"] = m.group(1)

        # DOB
        m = _DOB_LBL_RE.search(text)
        raw_dob = m.group(1) if m else None
        if not raw_dob:
            m = _DOB_BARE_RE.search(text)
            raw_dob = m.group(1) if m else None
        if raw_dob:
            result["date_of_birth"] = _norm_date(raw_dob)

        # Relation name (father/husband)
        m = _RELATION_RE.search(text)
        if m:
            result["relation_name"] = _clean_name(m.group(1))

        # Part number
        m = _PART_RE.search(text)
        if m:
            result["part_number"] = m.group(1)

        # PIN and state from address lines
        pin_m = _PIN_RE.search(text)
        if pin_m:
            result["pin_code"] = pin_m.group(1)
        for state in _STATES:
            if state in lower:
                result["state"] = state.title()
                break

        # Address: lines after "address" keyword until PIN
        addr_lines: list[str] = []
        in_addr = False
        for line in text.splitlines():
            ll = line.strip().lower()
            if not ll:
                continue
            if re.search(r"\baddress\b", ll):
                in_addr = True
                continue
            if in_addr:
                if _PIN_RE.search(line):
                    addr_lines.append(line.strip())
                    break
                addr_lines.append(line.strip())
        if addr_lines:
            result["address"] = " ".join(addr_lines)

        # Name — positional: 2–4 uppercase words, not in skip words
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for line in lines:
            words = line.split()
            if (2 <= len(words) <= 4
                    and all(w.replace(".", "").isalpha() for w in words)
                    and all(w.isupper() for w in words)
                    and not any(w.lower() in _SKIP_WORDS for w in words)
                    and line != result.get("relation_name", "").upper()):
                result["name"] = _clean_name(line)
                break

        result["raw_text"] = text
        return result
