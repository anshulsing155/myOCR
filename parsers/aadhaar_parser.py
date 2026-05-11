"""Aadhaar card parser — extract Aadhaar number, name, DOB, gender, address.

Front of card:  Name, DOB/YOB, Gender, Aadhaar number (12 digits)
Back of card :  Address (with S/O, C/O, village, district, state, PIN),
                optionally VID (16 digits), issue date

Extraction strategy:
  - VID stripped from text before Aadhaar search (to avoid 12-of-16 match)
  - Multiple DOB label variants handled (garbled OCR: "/D", "OOB", etc.)
  - Address assembled from S/O line through to PIN code
  - Name: label-based first; positional fallback
"""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

# ── Aadhaar / VID ─────────────────────────────────────────────────────────────

# Aadhaar: 12 digits, optional whitespace/hyphen grouping (XXXX XXXX XXXX or XXXX-XXXX-XXXX or no sep)
# Exclude numbers starting with 0 or 1 (invalid Aadhaar prefixes per UIDAI spec)
_AADHAAR_RE = re.compile(r"\b([2-9]\d{3}[\s\-]*\d{4}[\s\-]*\d{4})\b")

# VID: 16 digits after explicit label
_VID_RE = re.compile(
    r"(?:vid|virtual\s*id(?:entity)?)\s*[:\s]\s*(\d(?:[\d\s\-]{14,22})\d)", re.I)
_VID_STRIP_RE = re.compile(
    r"(?:vid|virtual\s*id(?:entity)?)\s*[:\s]\s*[\d\s\-]{15,24}", re.I)

# ── Dates ─────────────────────────────────────────────────────────────────────

# DOB: handles explicit labels (incl. garbled "/DOB", "OOB", "D.O.B") + bare date
_DOB_RE = re.compile(
    r"(?:year\s+of\s+birth|date\s+of\s+birth|d\.?\s*o\.?\s*b\.?|dob|/d(?:ob)?|o{1,2}b)"
    r"[:\s/]*(\d{2}[/\-\.]\d{2}[/\-\.]\d{4}|\d{4})",
    re.I,
)
_BARE_DATE_RE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
_ISSUE_DATE_RE = re.compile(
    r"(?:issue\s*date|issued\s*on|valid\s*(?:from|date))\s*[:\s]*"
    r"(\d{2}[/\-\.]\d{2}[/\-\.]\d{4})",
    re.I,
)

# ── Personal ──────────────────────────────────────────────────────────────────

_GENDER_RE = re.compile(r"\b(male|female|transgender)\b", re.I)

# Name label on Aadhaar (front side usually has no label — pure positional)
# Back side of some variants has "Name:" explicitly
_NAME_LABEL_RE = re.compile(
    r"(?:^|\n)\s*(?:name|नाम)\s*[:\-]?\s*([A-Z][A-Za-z \.]{2,50}?)(?:\n|$)",
    re.I | re.MULTILINE,
)

# ── Address ───────────────────────────────────────────────────────────────────

# Explicit "Address:" label on back of Aadhaar — strong, unambiguous trigger
_ADDR_LABEL_RE = re.compile(r"^\s*(?:address|पता)\s*[:\-]?", re.I)

# Address trigger keywords — note: "\bpo\b" removed (too short, matches garbled OCR)
_ADDR_START_RE = re.compile(
    r"\b(?:s/o|d/o|w/o|c/o|h\.?\s*no|house\s*no|flat\s*no|plot\s*no|"
    r"village|vill\.?|post\s*(?:office|box)|dist(?:rict)?|tehsil|taluk|"
    r"near|ward|nagar|mohalla|street|road|lane|colony|sector|block)\b",
    re.I,
)

# Relative name: s/o, d/o, w/o followed by a name
_RELATIVE_RE = re.compile(
    r"(?:s/o|d/o|w/o|c/o|son\s+of|daughter\s+of|wife\s+of|care\s+of)"
    r"\s*[:\-]?\s*([A-Z][A-Za-z \.]{2,50}?)(?:[,\n]|$)",
    re.I | re.MULTILINE,
)

# PIN code (6-digit Indian postal code)
_PIN_RE = re.compile(r"\b(\d{6})\b")

# State names for extraction from address
_STATES = {
    "andhra pradesh","arunachal pradesh","assam","bihar","chhattisgarh",
    "goa","gujarat","haryana","himachal pradesh","jammu and kashmir",
    "jammu & kashmir","j&k","jharkhand","karnataka","kerala",
    "madhya pradesh","maharashtra","manipur","meghalaya","mizoram",
    "nagaland","odisha","punjab","rajasthan","sikkim","tamil nadu",
    "telangana","tripura","uttar pradesh","uttarakhand","west bengal",
    "delhi","chandigarh","puducherry","pondicherry",
    "andaman and nicobar","andaman & nicobar",
    "lakshadweep","dadra and nagar haveli","daman and diu","ladakh",
}
_STATE_RE = re.compile(
    r"\b(" + "|".join(re.escape(s) for s in _STATES) + r")\b", re.I)

_SKIP_WORDS = {
    "UNIQUE","IDENTIFICATION","AUTHORITY","INDIA","GOVERNMENT","AADHAAR",
    "AADHAR","ENROLMENT","ADDRESS","MINISTRY","LABOUR","LABOR","EMPLOYMENT",
    "NATIONAL","DEPARTMENT","OF","THE","AND","FOR","TO","BY","IN","WITH",
    "GOVT","QR","CODE","PHOTOGRAPH","SIGNATURE","VID","VIRTUAL","MALE",
    "FEMALE","TRANSGENDER","DATE","BIRTH","DOB","GENDER",
}
_SKIP_PHRASES = {
    "government of india","unique identification","ministry of",
    "aadhaar card","aadhar card","date of birth","year of birth",
    "my aadhaar","download aadhaar",
}

_CONSONANTS = frozenset("bcdfghjklmnpqrstvwxyz")


def _is_garbled(word: str) -> bool:
    alpha = [c.lower() for c in word if c.isalpha() and c.isascii()]
    if not alpha:
        return False
    vowels = sum(1 for c in alpha if c in "aeiou")
    # Short all-consonant words ("HRH", "TRT") are garbled OCR artifacts
    if len(alpha) <= 3 and vowels == 0:
        return True
    # 3-char words starting with 2 consecutive consonants ("Gwe", "Kws") are garbled
    if len(alpha) == 3 and alpha[0] not in "aeiou" and alpha[1] not in "aeiou":
        return True
    if len(alpha) < 4:
        return False
    run = max_run = 0
    for c in alpha:
        run = (run + 1) if c in _CONSONANTS else 0
        max_run = max(max_run, run)
    return (vowels / len(alpha)) < 0.20 or max_run >= 5


def _normalise_date(s: str) -> str:
    return re.sub(r"[-\.]", "/", s)


class AadhaarParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "aadhaar"}

        # ── VID (extract first; strip so it can't pollute Aadhaar match) ──────
        m = _VID_RE.search(text)
        if m:
            vid = re.sub(r"[\s\-]", "", m.group(1))
            if len(vid) == 16:
                result["vid"] = vid
        text_clean = _VID_STRIP_RE.sub("", text)

        # ── Aadhaar number ────────────────────────────────────────────────────
        m = _AADHAAR_RE.search(text_clean)
        if m:
            digits = re.sub(r"\s", "", m.group(1))
            result["aadhaar_number"] = f"{digits[:4]} {digits[4:8]} {digits[8:]}"

        # ── Date of birth ─────────────────────────────────────────────────────
        m = _DOB_RE.search(text) or _BARE_DATE_RE.search(text)
        if m:
            result["date_of_birth"] = _normalise_date(m.group(1))

        # ── Gender ────────────────────────────────────────────────────────────
        m = _GENDER_RE.search(text)
        if m:
            result["gender"] = m.group(1).capitalize()

        # ── Issue date ────────────────────────────────────────────────────────
        m = _ISSUE_DATE_RE.search(text)
        if m:
            result["issue_date"] = _normalise_date(m.group(1))

        # ── Relative name (S/O, D/O etc.) ─────────────────────────────────────
        m = _RELATIVE_RE.search(text)
        if m:
            result["relation_name"] = m.group(1).strip()

        # ── Address ───────────────────────────────────────────────────────────
        address_lines: list[str] = []
        collecting = False
        for line in text.splitlines():
            line = line.strip()
            if not line:
                if collecting and address_lines:
                    break
                continue
            if not collecting:
                # Explicit "Address:" label takes priority over keyword heuristics
                label_m = _ADDR_LABEL_RE.match(line)
                if label_m:
                    collecting = True
                    rest = line[label_m.end():].strip()
                    if rest:
                        address_lines.append(rest)
                    continue
                if _ADDR_START_RE.search(line):
                    collecting = True
            if collecting:
                # Another address label while collecting → restart from here.
                # This handles translated Hindi "address:" → English "Address:"
                # appearing on the same back page for bilingual Aadhaar cards.
                label_m2 = _ADDR_LABEL_RE.match(line)
                if label_m2:
                    address_lines.clear()
                    rest = line[label_m2.end():].strip()
                    if rest:
                        address_lines.append(rest)
                    continue
                digits = re.sub(r"\D", "", line)
                # Stop at the Aadhaar number line: must be exactly 12 digits AND
                # match the Aadhaar pattern (avoids stopping at +91-XXXXXXXXXX phone lines)
                if len(digits) >= 12 and _AADHAAR_RE.search(line):
                    break
                address_lines.append(line)
                if len(address_lines) >= 10:
                    break

        if address_lines:
            addr = " ".join(address_lines)
            result["address"] = re.sub(r"\s+", " ", addr).strip()

            # Extract PIN code from address
            pin_m = _PIN_RE.search(addr)
            if pin_m:
                result["pin_code"] = pin_m.group(1)

            # Extract state from address
            state_m = _STATE_RE.search(addr)
            if state_m:
                result["state"] = state_m.group(1).title()

        # ── Name ─────────────────────────────────────────────────────────────
        # Build a set of words to never accept as the holder's name:
        # the relation_name lines and any S/O prefix lines already extracted.
        _relation_words: set[str] = set()
        if result.get("relation_name"):
            _relation_words = {w.upper() for w in result["relation_name"].split()}

        # Try label-based first
        m = _NAME_LABEL_RE.search(text)
        if m:
            name_candidate = re.sub(r"\s+", " ", m.group(1)).strip()
            if not any(_is_garbled(w) for w in name_candidate.split()):
                result["name"] = name_candidate
        else:
            # Positional: first 2-5 word title-case / upper-case line that
            # doesn't look like an org header or garbled OCR.
            # Only scan lines BEFORE the DOB/gender/address block to avoid
            # picking up father's name or address text as the holder name.
            lines_before_dob: list[str] = []
            for line in text.splitlines():
                stripped = line.strip()
                # Stop collecting candidate lines once we hit DOB or gender
                if re.search(r"\b(date\s+of\s+birth|dob|d\.o\.b|year\s+of\s+birth|"
                             r"male|female|transgender|address|s/o|d/o|w/o)\b",
                             stripped, re.I):
                    break
                lines_before_dob.append(stripped)

            # If DOB-stop didn't help (scan entire text as fallback), use all lines
            candidate_lines = lines_before_dob if lines_before_dob else text.splitlines()

            def _valid_name_line(ln: str) -> bool:
                """Return True if ln passes all name-candidate checks."""
                ln = ln.strip()
                if not ln:
                    return False
                ws = ln.split()
                if not all(w[0].isalpha() for w in ws if w):
                    return False
                if not all(len(w) >= 2 for w in ws):
                    return False
                if not ws[0][0].isupper():
                    return False
                if any(w.upper() in _SKIP_WORDS for w in ws):
                    return False
                if any(p in ln.lower() for p in _SKIP_PHRASES):
                    return False
                if re.search(r"\d|[/\\@#$%&*:]", ln):
                    return False
                if any(_is_garbled(w) for w in ws):
                    return False
                if _relation_words and {w.upper() for w in ws} == _relation_words:
                    return False
                if re.match(r"[AEIOUaeiou]{2}", ws[0]):
                    return False
                if len(ln) > 50:
                    return False
                return True

            stripped_candidates = [ln.strip() for ln in candidate_lines]

            # First pass: try single-line 2-5 word names
            for line in stripped_candidates:
                words = line.split()
                if 2 <= len(words) <= 5 and _valid_name_line(line):
                    result["name"] = line
                    break

            # Second pass: merge two adjacent single-word lines (Tesseract splits name across lines)
            if "name" not in result:
                for i in range(len(stripped_candidates) - 1):
                    combined = stripped_candidates[i] + " " + stripped_candidates[i + 1]
                    if combined.count(" ") <= 4 and _valid_name_line(combined):
                        result["name"] = combined
                        break

        # Fallback: full-text scan for "Firstname Lastname" when all OCR is one line
        if "name" not in result:
            for m in re.finditer(
                r'\b([A-Z][a-z]{1,20}(?:[ \t]+[A-Z][a-z]{1,20}){1,2})\b', text
            ):
                candidate = re.sub(r"\s+", " ", m.group(1)).strip()
                words = candidate.split()
                if any(w.upper() in _SKIP_WORDS for w in words):
                    continue
                if any(p in candidate.lower() for p in _SKIP_PHRASES):
                    continue
                if any(_is_garbled(w) for w in words):
                    continue
                # Skip relation name
                if _relation_words and {w.upper() for w in words} == _relation_words:
                    continue
                result["name"] = candidate
                break

        # Strip trailing OCR punctuation noise from name ("Tyag!" → "Tyag")
        if result.get("name"):
            result["name"] = re.sub(r"[^A-Za-z\s]+$", "", result["name"]).strip()

        result["raw_text"] = text
        return result
