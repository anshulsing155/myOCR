"""eShram / UAN card parser — extract UAN, name, DOB, gender, occupation, address.

eShram card layout:
  - UAN (12 digits in 4-4-4 format, labelled)
  - Name
  - Father/Husband name
  - Date of Birth
  - Gender
  - Blood Group
  - Occupation
  - Contact number
  - Current Address (multi-line, ends at PIN code)
  - Registration date
"""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

# ── UAN ───────────────────────────────────────────────────────────────────────
_UAN_RE = re.compile(
    r"(?:universal\s*account\s*number|uan)\s*[:\-]?\s*(\d{4}[\s\-]?\d{4}[\s\-]?\d{4})",
    re.I,
)
# Bare 12-digit fallback near UAN label
_UAN_BARE_RE = re.compile(r"\bUAN\b[^\d]{0,25}(\d{4}[\s\-]?\d{4}[\s\-]?\d{4})", re.I)

# ── Dates ─────────────────────────────────────────────────────────────────────
_DATE_PAT = r"\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4}"
_DOB_RE = re.compile(
    r"(?:date\s+of\s+birth|d\.?\s*o\.?\s*b\.?|dob|yob|year\s+of\s+birth)"
    r"\s*[:\-]?\s*(" + _DATE_PAT + r"|\d{4})",
    re.I,
)
_REG_DATE_RE = re.compile(
    r"(?:registration\s*date|registered\s*on|reg\.?\s*date)\s*[:\-]?\s*(" + _DATE_PAT + r")",
    re.I,
)

# ── Personal fields ───────────────────────────────────────────────────────────
_GENDER_RE = re.compile(r"\b(male|female|transgender)\b", re.I)

# Blood group: handles A+, B-, O+VE, AB-VE, A+ VE, B - VE
_BLOOD_RE = re.compile(
    r"blood\s*(?:group|type|grp)?\s*[:\-]?\s*"
    r"(A|B|AB|O)\s*([+\-])\s*(?:VE|ve|positive|negative|pos|neg)?",
    re.I,
)

_PHONE_RE = re.compile(
    r"(?:contact|mobile|phone|mob\.?)\s*(?:no\.?|number)?\s*[:\-]?\s*(\+?91[-\s]?\d{10}|\d{10})",
    re.I,
)

# Relation: father/husband name
_RELATION_RE = re.compile(
    r"(?:father[''s]*\s*name|husband[''s]*\s*name|f/o|h/o|s/o|d/o|w/o|shri|smt\.?)\s*[:\-]?\s*"
    r"([A-Z][A-Za-z\s\.]{2,50}?)(?:\n|$)",
    re.I | re.MULTILINE,
)

_NAME_LABEL_RE = re.compile(
    r"^(?:name|full\s*name|worker\s*name)\s*[:\-]?\s*([A-Z][A-Za-z\s\.]{2,50}?)(?:\n|$)",
    re.I | re.MULTILINE,
)

_OCC_RE = re.compile(
    r"occupation\s*[:\-]?\s*([A-Za-z][A-Za-z,\s]{2,60}?)(?:\n|$)",
    re.I | re.MULTILINE,
)

# ── Address ───────────────────────────────────────────────────────────────────
# Colon/dash is optional — some OCR outputs drop the punctuation after the label
_ADDR_START_RE = re.compile(
    r"(?:current\s*address|address|permanent\s*address|addr\.?)\s*[:\-]?",
    re.I,
)
_PIN_RE = re.compile(r"\b(\d{6})\b")
_STATE_NAMES = {
    "andhra pradesh","arunachal pradesh","assam","bihar","chhattisgarh",
    "goa","gujarat","haryana","himachal pradesh","jammu and kashmir",
    "jharkhand","karnataka","kerala","madhya pradesh","maharashtra",
    "manipur","meghalaya","mizoram","nagaland","odisha","punjab",
    "rajasthan","sikkim","tamil nadu","telangana","tripura",
    "uttar pradesh","uttarakhand","west bengal","delhi","chandigarh",
}
_STATE_RE = re.compile(
    r"\b(" + "|".join(re.escape(s) for s in _STATE_NAMES) + r")\b", re.I)

# ── Name skip words ───────────────────────────────────────────────────────────
_SKIP = {
    "INDIA","GOVT","GOVERNMENT","MINISTRY","LABOUR","LABOR","EMPLOYMENT",
    "ESHRAM","SHRAM","CARD","UNIVERSAL","ACCOUNT","NUMBER","SERVICES",
    "AUTHORITY","UNORGANISED","UNORGANIZED","WORKER","WORKERS","NATIONAL",
    "GENDER","MALE","FEMALE","TRANSGENDER","BLOOD","GROUP","OCCUPATION",
    "ADDRESS","CONTACT","MOBILE","DATE","BIRTH","DOB","OF","AND","FOR",
    "THE","CSC","CENTRE","CENTER","REGISTRATION",
}


def _clean_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    return digits[-10:] if len(digits) >= 10 else digits


def _normalise_date(s: str) -> str:
    return re.sub(r"[-\.]", "/", s)


class EshramParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "eshram"}

        # ── UAN ───────────────────────────────────────────────────────────────
        m = _UAN_RE.search(text) or _UAN_BARE_RE.search(text)
        if m:
            result["uan"] = re.sub(r"[\s\-]", "", m.group(1))

        # ── DOB ───────────────────────────────────────────────────────────────
        m = _DOB_RE.search(text)
        if m:
            result["date_of_birth"] = _normalise_date(m.group(1))

        # ── Gender ────────────────────────────────────────────────────────────
        m = _GENDER_RE.search(text)
        if m:
            result["gender"] = m.group(1).capitalize()

        # ── Blood group ───────────────────────────────────────────────────────
        m = _BLOOD_RE.search(text)
        if m:
            grp = m.group(1).upper()
            sign = "+" if m.group(2) == "+" else "-"
            result["blood_group"] = f"{grp}{sign}"

        # ── Occupation ────────────────────────────────────────────────────────
        m = _OCC_RE.search(text)
        if m:
            result["occupation"] = m.group(1).strip().rstrip(",")

        # ── Contact ───────────────────────────────────────────────────────────
        m = _PHONE_RE.search(text)
        if m:
            result["contact_number"] = _clean_phone(m.group(1))

        # ── Relation (father/husband) ─────────────────────────────────────────
        m = _RELATION_RE.search(text)
        if m:
            result["relation_name"] = m.group(1).strip()

        # ── Registration date ─────────────────────────────────────────────────
        m = _REG_DATE_RE.search(text)
        if m:
            result["registration_date"] = _normalise_date(m.group(1))

        # ── Address ───────────────────────────────────────────────────────────
        addr_lines: list[str] = []
        collecting = False
        for line in text.splitlines():
            line = line.strip()
            if not line:
                if collecting and addr_lines:
                    break
                continue
            if _ADDR_START_RE.search(line):
                collecting = True
                # Address might be on the same line after the label
                after = re.split(r"(?:address|addr\.?)\s*[:\-]", line, flags=re.I, maxsplit=1)
                if len(after) > 1 and after[1].strip():
                    addr_lines.append(after[1].strip())
                continue
            if collecting:
                # Stop at another labeled field
                if re.match(r"(?:gender|blood|occupation|contact|mobile|uan|registration)", line, re.I):
                    break
                addr_lines.append(line)
                if len(addr_lines) >= 5:
                    break

        if addr_lines:
            addr = " ".join(addr_lines)
            result["address"] = re.sub(r"\s+", " ", addr).strip()
            pin_m = _PIN_RE.search(addr)
            if pin_m:
                result["pin_code"] = pin_m.group(1)
            state_m = _STATE_RE.search(addr)
            if state_m:
                result["state"] = state_m.group(1).title()

        # ── Name ─────────────────────────────────────────────────────────────
        # Labeled approach first ("Name: Ramesh Kumar")
        m = _NAME_LABEL_RE.search(text)
        if m:
            candidate = m.group(1).strip()
            if not any(w.upper() in _SKIP for w in candidate.split()):
                result["name"] = candidate

        def _plausible_name_word(w: str) -> bool:
            """Return True if w looks like a valid Indian name component."""
            alpha = [c.lower() for c in w if c.isalpha()]
            if len(alpha) < 2:
                return False
            # 3-char words: reject if last 2 are both consonants (e.g. "Uld", "Gld")
            VOWELS = set("aeiou")
            if len(alpha) == 3 and alpha[-1] not in VOWELS and alpha[-2] not in VOWELS:
                return False
            return True

        # Bilingual OCR pattern: "7AH/Name\n:\n<Hindi>\n/\nFirstname\nLastname"
        # A lone "/" line separates Hindi script from the English transliteration.
        if "name" not in result:
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if line.strip() != "/":
                    continue
                # Collect consecutive Title-case single words after the "/"
                candidates: list[str] = []
                for j in range(i + 1, min(i + 5, len(lines))):
                    word = lines[j].strip()
                    if (re.match(r"^[A-Z][a-z]{1,25}$", word)
                            and word.upper() not in _SKIP
                            and _plausible_name_word(word)):
                        candidates.append(word)
                    else:
                        break
                if 2 <= len(candidates) <= 4:
                    result["name"] = " ".join(candidates)
                    break

        # Positional fallback: first 2-5 uppercase word line not matching skip words
        if "name" not in result:
            for line in text.splitlines():
                line = line.strip()
                words = line.split()
                if not (2 <= len(words) <= 5):
                    continue
                if not all(w[0].isalpha() and w[0].isupper() for w in words if w):
                    continue
                if any(w.upper() in _SKIP for w in words):
                    continue
                if re.search(r"\d|[:/\\@#$%&*\-]", line):
                    continue
                if len(line) > 45:
                    continue
                result["name"] = line
                break

        result["raw_text"] = text
        return result
