"""PAN card parser — extract PAN number, name, father's name, DOB.

Layout of a physical PAN card (top → bottom):
  INCOME TAX DEPARTMENT / GOVT. OF INDIA
  [Photo]
  Permanent Account Number
  AAAAA9999A          ← PAN
  Name
  FIRST LAST          ← holder name (always ALL CAPS)
  Father's Name
  FIRST LAST          ← father's name (always ALL CAPS)
  Date of Birth
  DD/MM/YYYY          ← DOB

Extraction strategy: labeled regex first, positional heuristic fallback.
"""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

# ── Core patterns ─────────────────────────────────────────────────────────────

_PAN_RE = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")

# DOB: handles DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, with optional label
_DOB_LABELED_RE = re.compile(
    r"(?:date\s+of\s+birth|d\.?\s*o\.?\s*b\.?)\s*[:\-]?\s*"
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})",
    re.I,
)
_DOB_BARE_RE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")

# Father's name — explicit label variants
_FATHER_LABELED_RE = re.compile(
    r"(?:father['’s]*\s*(?:name)?|s/o|d/o|w/o|son\s+of|daughter\s+of|wife\s+of)"
    r"\s*[:\-]?\s*([A-Z][A-Za-z\s\.]{2,50}?)(?:\n|$)",
    re.I | re.MULTILINE,
)

# Name label on card (sometimes OCR'd as "Name" before the actual name)
_NAME_LABELED_RE = re.compile(
    r"(?:^|\n)\s*Name\s*[:\-]?\n?\s*([A-Z][A-Za-z\s\.]{2,50}?)(?:\n|$)",
    re.I | re.MULTILINE,
)

# Words to skip when doing positional name extraction
_SKIP_WORDS = {
    "INDIA", "GOVT", "GOVERNMENT", "INCOME", "TAX", "DEPARTMENT",
    "PERMANENT", "ACCOUNT", "NUMBER", "DATE", "BIRTH", "SIGNATURE",
    "INCOME TAX", "NAME", "FATHER",
}

# PAN card 4th char encodes card holder type:
# P=individual, C=company, H=HUF, F=firm, A=AOP, T=trust, B=BOI, L=local, J=artificial, G=govt
_PAN_TYPE = {
    "P": "Individual", "C": "Company", "H": "HUF",
    "F": "Firm", "A": "Association of Persons", "T": "Trust",
    "B": "Body of Individuals", "L": "Local Authority",
    "J": "Artificial Juridical Person", "G": "Government",
}


def _is_name_line(line: str) -> bool:
    """True if a line looks like a person/entity name: 2-5 words, alpha only."""
    words = line.strip().split()
    if not (2 <= len(words) <= 5):
        return False
    if not all(re.match(r"^[A-Za-z\.]+$", w) for w in words):
        return False
    if any(w.upper() in _SKIP_WORDS for w in words):
        return False
    if re.search(r"\d", line):
        return False
    return True


def _normalise_date(s: str) -> str:
    """Normalise date separators to DD/MM/YYYY."""
    return re.sub(r"[-\.]", "/", s)


class PanParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "pan_card"}

        # ── PAN number ────────────────────────────────────────────────────────
        m = _PAN_RE.search(text)
        if m:
            pan = m.group(1)
            result["pan_number"] = pan
            # Derive holder type from 4th character
            holder_char = pan[3] if len(pan) >= 4 else ""
            if holder_char in _PAN_TYPE:
                result["pan_holder_type"] = _PAN_TYPE[holder_char]

        # ── Date of birth ─────────────────────────────────────────────────────
        m = _DOB_LABELED_RE.search(text) or _DOB_BARE_RE.search(text)
        if m:
            result["date_of_birth"] = _normalise_date(m.group(1))

        # ── Father's name: labeled first ──────────────────────────────────────
        m = _FATHER_LABELED_RE.search(text)
        if m:
            result["father_name"] = m.group(1).strip().upper()

        # ── Name + positional father name ─────────────────────────────────────
        # Try explicit label first
        m = _NAME_LABELED_RE.search(text)
        if m:
            result["name"] = m.group(1).strip().upper()

        # Positional fallback: scan lines for name-like uppercase text
        # PAN card layout: holder name first, father name second
        name_lines: list[str] = []
        for line in text.splitlines():
            line = line.strip()
            # Skip very short lines and known header text
            if len(line) < 4 or "INCOME TAX" in line.upper() or "GOVT" in line.upper():
                continue
            if _is_name_line(line):
                name_lines.append(line.upper())
                if len(name_lines) == 2:
                    break

        if name_lines and "name" not in result:
            result["name"] = name_lines[0]
        if len(name_lines) >= 2 and "father_name" not in result:
            result["father_name"] = name_lines[1]

        result["raw_text"] = text
        return result
