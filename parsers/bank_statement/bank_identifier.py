"""Identify which bank issued a bank statement from OCR text.

Two-phase detection:
  Phase 1 — IFSC prefix (definitive: maps 4-letter code → bank)
  Phase 2 — keyword frequency scoring (handles cases without visible IFSC)
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import NamedTuple


class BankID(NamedTuple):
    name: str   # canonical name, e.g. "HDFC Bank"
    code: str   # short code,      e.g. "hdfc"


# ── IFSC prefix → bank (authoritative) ────────────────────────────────────────
# First 4 chars of any IFSC code uniquely identify the bank.
_IFSC_PREFIX: dict[str, BankID] = {
    "HDFC": BankID("HDFC Bank",             "hdfc"),
    "SBIN": BankID("State Bank of India",   "sbi"),
    "ICIC": BankID("ICICI Bank",            "icici"),
    "UTIB": BankID("Axis Bank",             "axis"),
    "KKBK": BankID("Kotak Mahindra Bank",   "kotak"),
    "PUNB": BankID("Punjab National Bank",  "pnb"),
    "BARB": BankID("Bank of Baroda",        "bob"),
    "CNRB": BankID("Canara Bank",           "canara"),
    "UBIN": BankID("Union Bank of India",   "union"),
    "BKID": BankID("Bank of India",         "boi"),
    "IBKL": BankID("IDBI Bank",             "idbi"),
    "YESB": BankID("Yes Bank",              "yes"),
    "INDB": BankID("IndusInd Bank",         "indusind"),
    "FDRL": BankID("Federal Bank",          "federal"),
    "RATN": BankID("RBL Bank",              "rbl"),
    "IDIB": BankID("Indian Bank",           "indian"),
    "CBIN": BankID("Central Bank of India", "central"),
    "IOBA": BankID("Indian Overseas Bank",  "iob"),
    "UCBA": BankID("UCO Bank",              "uco"),
    "BDBL": BankID("Bandhan Bank",          "bandhan"),
    "AUBL": BankID("AU Small Finance Bank", "au"),
    "AIRP": BankID("Airtel Payments Bank",  "airtel"),
    "PYTM": BankID("Paytm Payments Bank",   "paytm"),
}

_IFSC_RE = re.compile(r"\b([A-Z]{4})0[A-Z0-9]{6}\b")

# Matches IFSC codes that are explicitly labeled (e.g. "IFSC Code: SBIN0001234").
# These are the bank's OWN code — far more reliable than IFSCs embedded in
# transaction narrations like "NEFT*HDFC0004989*CompanyName".
_LABELED_IFSC_RE = re.compile(
    r"(?:i\.?f\.?s\.?c\.?\s*(?:code)?|ifs\s*code|ifsc\s*(?:code)?)"
    r"\s*[:\-]?\s*([A-Z]{4}0[A-Z0-9]{6})\b",
    re.IGNORECASE,
)


# ── Phase 2: keyword scoring ───────────────────────────────────────────────────
# (keyword, weight)  — matched case-insensitively against full OCR text.
# High weights for explicit bank name mentions; lower for shared abbreviations.
_BANK_KEYWORDS: list[tuple[list[tuple[str, float]], BankID]] = [
    ([("hdfc bank",                    4.0),
      ("housing development finance",  3.0),
      (r"\bhdfc\b",                    1.5)],
     BankID("HDFC Bank", "hdfc")),

    ([("state bank of india",  4.0),
      ("sbi bank",             3.0),
      (r"\bsbin\b",            2.0),
      (r"\bsbi\b",             1.5)],
     BankID("State Bank of India", "sbi")),

    ([("icici bank",   4.0),
      (r"\bicici\b",   2.0)],
     BankID("ICICI Bank", "icici")),

    ([("axis bank",    4.0),
      (r"\butib\b",    2.0),
      (r"\baxis\b",    1.5)],
     BankID("Axis Bank", "axis")),

    ([("kotak mahindra bank", 4.0),
      ("kotak mahindra",      3.0),
      ("kotak bank",          3.0),
      (r"\bkotak\b",          1.5)],
     BankID("Kotak Mahindra Bank", "kotak")),

    ([("punjab national bank", 4.0),
      (r"\bpnb\b",             2.0)],
     BankID("Punjab National Bank", "pnb")),

    ([("bank of baroda",  4.0),
      (r"\bbob\b",         1.5)],
     BankID("Bank of Baroda", "bob")),

    ([("canara bank",   4.0)],
     BankID("Canara Bank", "canara")),

    ([("union bank of india", 4.0),
      ("union bank",           3.0)],
     BankID("Union Bank of India", "union")),

    ([("bank of india",  4.0),
      (r"\bboi\b",        1.5)],
     BankID("Bank of India", "boi")),

    ([("idbi bank",   4.0),
      (r"\bidbi\b",    2.0)],
     BankID("IDBI Bank", "idbi")),

    ([("yes bank",  4.0)],
     BankID("Yes Bank", "yes")),

    ([("indusind bank", 4.0),
      ("indusind",       2.0)],
     BankID("IndusInd Bank", "indusind")),

    ([("federal bank", 4.0)],
     BankID("Federal Bank", "federal")),

    ([("rbl bank",   4.0),
      (r"\brbl\b",    2.0)],
     BankID("RBL Bank", "rbl")),

    ([("indian bank",   4.0)],
     BankID("Indian Bank", "indian")),

    ([("central bank of india",  4.0)],
     BankID("Central Bank of India", "central")),

    ([("indian overseas bank", 4.0),
      (r"\biob\b",              2.0)],
     BankID("Indian Overseas Bank", "iob")),

    ([("uco bank",  4.0)],
     BankID("UCO Bank", "uco")),

    ([("bandhan bank",  4.0)],
     BankID("Bandhan Bank", "bandhan")),

    ([("au small finance",   4.0),
      (r"\bau bank\b",        3.0)],
     BankID("AU Small Finance Bank", "au")),
]

# Pre-compile keyword patterns
_COMPILED_KW: list[tuple[list[tuple[re.Pattern, float]], BankID]] = [
    ([(re.compile(kw, re.IGNORECASE), w) for kw, w in kws], bid)
    for kws, bid in _BANK_KEYWORDS
]


def _header_text(ocr_results: list[dict], max_items: int = 20) -> str:
    """Return text from the first N OCR items (likely the document header)."""
    return " ".join(r.get("text", "") for r in ocr_results[:max_items])


def identify_bank(ocr_results: list[dict]) -> BankID | None:
    """Return the best-matching BankID for the given OCR results, or None."""
    full_text   = " ".join(r.get("text", "") for r in ocr_results)
    header_text = _header_text(ocr_results)
    return _identify(full_text, header_text)


def identify_bank_from_text(text: str) -> BankID | None:
    return _identify(text, text[:2000])


def _identify(full_text: str, header_text: str) -> BankID | None:
    # ── Phase 1a: Labeled IFSC (highest priority — definitively the bank's own code) ──
    # "IFSC Code: SBIN0001234" can only be the account's own bank code.
    # Unlabeled IFSCs found in narrations (e.g. "NEFT*HDFC0004989*…") are
    # counterparty codes that must NOT override this.
    labeled_votes: dict[str, int] = defaultdict(int)
    for m in _LABELED_IFSC_RE.finditer(full_text):
        prefix = m.group(1)[:4].upper()
        if prefix in _IFSC_PREFIX:
            labeled_votes[prefix] += 20

    if labeled_votes:
        best_prefix = max(labeled_votes, key=lambda k: labeled_votes[k])
        return _IFSC_PREFIX[best_prefix]

    # ── Phase 1b: Unlabeled IFSC prefix voting ────────────────────────────────
    # Only trust when a single bank dominates (≥60%) — counterparty IFSCs in
    # narrations spread votes across many banks and fail this threshold.
    ifsc_votes: dict[str, int] = defaultdict(int)
    for m in _IFSC_RE.finditer(full_text):
        prefix = m.group(1)
        if prefix in _IFSC_PREFIX:
            # Header section gets 3× weight; body (narrations) gets 0.5×
            weight = 3 if m.start() < 2000 else 0.5
            ifsc_votes[prefix] += weight

    if ifsc_votes:
        best_prefix = max(ifsc_votes, key=lambda k: ifsc_votes[k])
        total = sum(ifsc_votes.values())
        if ifsc_votes[best_prefix] / total >= 0.6:
            return _IFSC_PREFIX[best_prefix]

    # ── Phase 2: keyword frequency scoring ────────────────────────────────────
    scores: dict[str, float] = defaultdict(float)
    for patterns, bank_id in _COMPILED_KW:
        for pat, weight in patterns:
            # Match in header → 2× boost
            if pat.search(header_text):
                scores[bank_id.code] += weight * 2
            elif pat.search(full_text):
                scores[bank_id.code] += weight

    if not scores:
        return None

    best_code = max(scores, key=lambda k: scores[k])
    best_score = scores[best_code]

    # Require minimum score to avoid false positives on incidental mentions
    if best_score < 3.0:
        return None

    # Find the BankID for the winning code
    for _, bank_id in _COMPILED_KW:
        if bank_id.code == best_code:
            return bank_id

    return None
