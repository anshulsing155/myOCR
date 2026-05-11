"""ITR acknowledgement parser — extract assessment year, income, tax details.

ITR digital-PDF table structure (pdfplumber):
  col_0: section label (often empty or rotated text)
  col_1: field label  ("Total Income", "Net tax payable", …)
  col_4: ROW NUMBER   (1, 2, 3, … — a sequential row index, NOT the value)
  col_5: value        ("6,96,740", "0", "(-) 16,500", …)

When these rows are flattened to text the line looks like:
    "Total Income 2 6,96,740"

The old regexes grabbed the row number ("2") instead of the value.
The fix: patterns that explicitly consume the row-number separator.
"""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

# ── helper patterns ─────────────────────────────────────────────────────────

# Mandatory row-number separator: " NN " (1–2 digit sequential index in table)
_ROW = r"\s+\d{1,2}\s+"
# Optional row-number separator (for text without row numbers, e.g. scanned)
_OPT_ROW = r"(?:\s+\d{1,2})?\s+"

# Indian amount: digits + optional Indian comma groups, optional decimal
_AMT = r"([\d,]+(?:\.\d+)?)"


# ── primary patterns (digital ITR table rows) ────────────────────────────────

_AY_RE           = re.compile(
    r"assessment\s+year\s*[:\-]?\s*(\d{4}\s*[-–]\s*\d{2,4})", re.I)
_PAN_RE          = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")
_ACK_RE          = re.compile(
    r"(?:e-?filing\s+)?acknowledgement\s*(?:no\.?|number)?\s*[:\-]?\s*(\d{15})", re.I)
_FILING_DATE_RE  = re.compile(
    r"date\s+of\s+filing\s*[:\-]\s*(\d{1,2}[-/\s]\w{3,9}[-/\s]\d{2,4})", re.I)
_FORM_RE         = re.compile(r"form\s+(?:no\.?|number)\s*[:\-]?\s*(ITR-\d+)", re.I)
_NAME_RE         = re.compile(
    r"(?:^|\n)\s*Name\s+([A-Za-z][A-Za-z\s\.]{2,60}?)(?:\n|$)", re.I | re.MULTILINE)

# Table-row aware (require row-number separator between label and value)
_GROSS_RE        = re.compile(r"gross\s+total\s+income" + _ROW + _AMT, re.I)
_TOTAL_INCOME_RE = re.compile(r"total\s+income" + _ROW + _AMT, re.I)
_NET_TAX_RE      = re.compile(r"net\s+tax\s+payable" + _ROW + _AMT, re.I)
_TAXES_PAID_RE   = re.compile(r"taxes?\s+paid" + _ROW + _AMT, re.I)
# "(7-8)" surrounds the row-num → use .*? to skip it
_REFUND_ROW_RE   = re.compile(
    r"refundable\b.*?" + _ROW + r"(?:\(-\)\s*)?" + _AMT, re.I)

# ── fallback patterns (scanned / plain OCR text, no row numbers) ─────────────

_GROSS_FB        = re.compile(r"gross\s+total\s+income\s*[:\-]?\s*" + _AMT, re.I)
_TOTAL_FB        = re.compile(r"total\s+income\s*[:\-]?\s*" + _AMT, re.I)
_NET_TAX_FB      = re.compile(r"net\s+tax\s+payable\s*[:\-]?\s*" + _AMT, re.I)
_REFUND_FB       = re.compile(r"refund(?:able|due|amount)?\s*[:\-]?\s*" + _AMT, re.I)
_TAXES_PAID_FB   = re.compile(r"taxes?\s+paid\s*[:\-]?\s*" + _AMT, re.I)


def _first(primary: re.Pattern, fallback: re.Pattern, text: str) -> str | None:
    """Try primary regex; fall back to secondary. Return cleaned amount or None."""
    m = primary.search(text) or fallback.search(text)
    return m.group(1).replace(",", "") if m else None


class ItrParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "itr"}

        # ── Scalar fields ──────────────────────────────────────────────────────
        m = _AY_RE.search(text)
        if m:
            result["assessment_year"] = re.sub(r"\s", "", m.group(1))

        m = _PAN_RE.search(text)
        if m:
            result["pan_number"] = m.group(1)

        m = _ACK_RE.search(text)
        if m:
            result["acknowledgement_number"] = m.group(1)

        m = _FILING_DATE_RE.search(text)
        if m:
            result["filing_date"] = m.group(1).strip()

        m = _FORM_RE.search(text)
        if m:
            result["form_number"] = m.group(1)

        m = _NAME_RE.search(text)
        if m:
            name = m.group(1).strip()
            # Drop anything that looks like an address or PAN leaking in
            if len(name) <= 60 and not re.search(r"\d", name):
                result["name"] = name

        # ── Numeric fields (table-row aware) ──────────────────────────────────
        val = _first(_GROSS_RE, _GROSS_FB, text)
        if val:
            result["gross_total_income"] = val

        val = _first(_TOTAL_INCOME_RE, _TOTAL_FB, text)
        if val:
            result["total_income"] = val

        val = _first(_NET_TAX_RE, _NET_TAX_FB, text)
        if val:
            result["net_tax_payable"] = val

        val = _first(_TAXES_PAID_RE, _TAXES_PAID_FB, text)
        if val:
            result["taxes_paid"] = val

        # Refund: check for "(-)" marker to confirm it's actually a refund
        m = _REFUND_ROW_RE.search(text) or _REFUND_FB.search(text)
        if m:
            refund_line = text[max(0, m.start() - 20): m.end()]
            is_refund = "(-)" in refund_line or "refundable" in refund_line.lower()
            if is_refund:
                result["refund_amount"] = m.group(1).replace(",", "")

        result["raw_text"] = text
        return result
