"""
Classify a document by type using two-phase scoring on OCR text:
  Phase 1 — keyword frequency scoring
  Phase 2 — structural regex patterns (PAN number, Aadhaar 12-digit, IFSC, etc.)

Supported types:
    bank_statement, pan_card, aadhaar, eshram, itr, invoice,
    salary_slip, property_doc, other
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import NamedTuple


class DocClass(NamedTuple):
    type: str
    confidence: float  # 0.0 – 1.0


# ── Phase 1: keyword tables ────────────────────────────────────────────────────
# All keys lowercased; matched against lowercased text.
_SIGNATURES: dict[str, list[tuple[str, float]]] = {
    "bank_statement": [
        ("account statement",      3.0),
        ("statement of account",   3.0),
        ("bank statement",         3.0),
        ("ifsc",                   2.0),
        ("micr",                   2.0),
        ("account number",         1.5),
        ("opening balance",        2.0),
        ("closing balance",        2.0),
        ("withdrawal",             1.5),
        ("deposit",                1.0),
        ("cheque",                 1.0),
        ("transaction",            1.0),
        ("balance",                0.5),
        ("chq",                    0.5),
        ("neft",                   1.5),
        ("rtgs",                   1.5),
        ("imps",                   1.5),
        ("upi",                    0.8),
    ],
    "pan_card": [
        ("permanent account number", 5.0),
        ("income tax department",    4.0),
        # "govt. of india" / "government of india" intentionally NOT here —
        # both PAN and Aadhaar share that phrase; PAN-specific phrases above are enough
        ("date of birth",            1.5),
        ("father",                   1.5),
        ("signature",                0.5),
    ],
    "aadhaar": [
        ("aadhaar",                          5.0),
        ("aadhar",                           5.0),
        ("unique identification authority",  4.0),
        ("uidai",                            4.0),
        ("enrolment no",                     2.0),
        ("enrolment",                        1.5),
        ("vid",                              3.0),   # was 1.0
        ("government of india",              1.0),   # shared but slight aadhaar signal
        ("date of birth",                    1.0),
    ],
    "itr": [
        ("income tax return",        5.0),
        ("itr",                      2.5),
        ("assessment year",          3.0),
        ("gross total income",       3.0),
        ("total income",             2.0),
        ("tax payable",              2.0),
        ("challan",                  2.0),
        ("deductions",               1.5),
        ("acknowledgement number",   2.0),
        ("form 16",                  2.0),
    ],
    "invoice": [
        ("tax invoice",        4.0),
        ("invoice no",         3.0),
        ("purchase order",     4.0),
        ("po number",          3.0),
        ("gstin",              3.0),
        ("gst",                1.5),
        ("bill to",            2.0),
        ("ship to",            1.5),
        ("amount due",         2.0),
        ("subtotal",           1.5),
        ("invoice",            1.0),
        ("expected delivery",  2.0),
        ("vendor",             1.0),
        ("hsn",                1.5),
        ("sac",                1.0),
    ],
    "salary_slip": [
        ("salary slip",      5.0),
        ("pay slip",         5.0),
        ("payslip",          5.0),
        ("basic salary",     3.0),
        ("hra",              2.0),
        ("provident fund",   2.0),
        ("pf",               1.5),
        ("gross salary",     3.0),
        ("net salary",       3.0),
        ("esic",             2.0),
        ("tds",              1.5),
        ("pay period",       2.0),
        ("employee id",      2.0),
        ("employer",         1.5),
    ],
    "property_doc": [
        ("sale deed",      5.0),
        ("sub-registrar",  4.0),
        ("stamp duty",     3.0),
        ("survey number",  2.5),
        ("plot no",        2.0),
        ("khata",          2.0),
        ("land",           1.5),
        ("registration",   1.5),
        ("conveyance",     2.0),
    ],
    "eshram": [
        ("eshram",                           6.0),
        ("e-shram",                          6.0),
        ("eshram card",                      6.0),
        ("universal account number",         5.0),
        ("ministry of labour",               4.0),
        ("ministry of labor",                4.0),
        ("unorganised workers",              3.0),
        ("unorganized workers",              3.0),
        ("csc centre",                       2.0),
        ("eshram.gov.in",                    3.0),
        ("eshramcare",                       3.0),
        ("blood group",                      1.0),
        ("occupation",                       0.5),
    ],
    "driving_license": [
        ("driving licence",                  6.0),
        ("driving license",                  6.0),
        ("indian union driving",             6.0),
        ("motor vehicles act",               4.0),
        ("son/daughter/wife of",             4.0),
        ("validity(nt)",                     4.0),
        ("validity(tr)",                     4.0),
        ("validity (nt)",                    4.0),
        ("validity (tr)",                    4.0),
        ("organ donor",                      3.0),
        ("date of first issue",              3.0),
        ("issued by",                        2.0),
        ("blood group",                      1.0),
    ],
}

_MAX_KW_SCORE = {k: sum(w for _, w in v) for k, v in _SIGNATURES.items()}


# ── Phase 2: structural pattern scores ────────────────────────────────────────
# Patterns that give strong structural evidence of a document type.
# Applied on ORIGINAL CASE text so PAN/IFSC patterns match correctly.
_PATTERN_SCORES: list[tuple[re.Pattern, str, float]] = [
    # eShram UAN: exactly 12 digits in 4-4-4 spaced format preceded by "UAN" label
    # Must be checked BEFORE generic Aadhaar pattern to avoid false positives
    (re.compile(r"\bUAN\b.*?\b\d{4}\s\d{4}\s\d{4}\b", re.I | re.S), "eshram", 8.0),
    # eShram domain / care email
    (re.compile(r"eshram\.gov\.in|eshramcare", re.I),                  "eshram", 5.0),
    # Aadhaar 12-digit number in "XXXX XXXX XXXX" display format
    (re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b"), "aadhaar", 5.0),
    # Aadhaar VID 16-digit
    (re.compile(r"\bVID\b", re.I),                        "aadhaar",        3.0),
    # Gender on Aadhaar card
    (re.compile(r"\b(FEMALE|MALE)\b"),                    "aadhaar",        2.0),
    # PAN number: AAAAA9999A format
    (re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),           "pan_card",       5.0),
    # IFSC code: ABCD0XXXXXX
    (re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),            "bank_statement", 3.0),
    # Long account numbers (11–18 digits, no spaces)
    (re.compile(r"\b\d{11,18}\b"),                        "bank_statement", 1.0),
    # ITR acknowledgement: 15-digit number
    (re.compile(r"\b\d{15}\b"),                           "itr",            2.0),
    # GSTIN: 15-char alphanumeric with digits in specific positions
    (re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d][Z][A-Z\d]\b"), "invoice", 3.0),
    # Indian DL number: StateCode(2) + DistrictCode(2) + Year(4) + Serial(7)
    (re.compile(r"\b[A-Z]{2}[-\s]?\d{2}[-\s]?\d{4}[-\s]?\d{7}\b"), "driving_license", 5.0),
]


def classify(ocr_results: list[dict]) -> DocClass:
    """Classify document type from a list of OCR result dicts."""
    original_text = " ".join(r.get("text", "") for r in ocr_results)
    return classify_text(original_text)


def classify_text(text: str) -> DocClass:
    """Classify document type from a raw text string."""
    scores: dict[str, float] = defaultdict(float)
    lower = text.lower()

    # Phase 1: keyword scoring
    for doc_type, keywords in _SIGNATURES.items():
        for kw, weight in keywords:
            if kw in lower:
                scores[doc_type] += weight

    # Phase 2: structural pattern scoring (original case)
    for pattern, doc_type, weight in _PATTERN_SCORES:
        if pattern.search(text):
            scores[doc_type] += weight

    if not scores:
        return DocClass("other", 0.0)

    best_type = max(scores, key=lambda k: scores[k])
    raw_score = scores[best_type]

    # Normalise: sum of keyword max + structural max per type
    kw_max  = _MAX_KW_SCORE.get(best_type, 0.0)
    pat_max = sum(w for _, t, w in _PATTERN_SCORES if t == best_type)
    max_possible = kw_max + pat_max
    confidence = min(1.0, raw_score / max_possible) if max_possible > 0 else 0.0

    # Require the winner to score at least 6% of its maximum
    if confidence < 0.06:
        return DocClass("other", 0.0)

    return DocClass(best_type, round(confidence, 3))
