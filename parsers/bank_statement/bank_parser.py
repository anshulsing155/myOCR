"""Bank-statement-specific extractor: account metadata + transaction table."""
from __future__ import annotations

import re
from typing import Any

from postprocessing.spatial_table import (
    normalise_col_name,
    reconstruct_table,
    split_page_ocr,
    find_table_header_row,
    group_into_rows,
)
from postprocessing.cleaner import build_table_rows, clean_transaction_rows
from parsers.bank_statement.banks import (
    extract_bank_metadata, get_bank_schema, BANK_SCHEMAS,
)


# ── account-field regex ────────────────────────────────────────────────────────

# Flexible numeric + text dates: "01/09/2023" or "29 Sep 2023"
_DATE_PAT = (r"\d{1,2}(?:[/\-\.]\d{1,2}[/\-\.]\d{2,4}"
             r"|\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})")

_ACCT_NO_RE   = re.compile(
    r"(?:a/c|account|ac)\s*(?:no\.?|number)?\s*[:\-]?\s*(\d[\d\s\-]{5,20}\d)", re.I)
_IFSC_RE      = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")
_ACCT_NAME_RE = re.compile(
    r"(?:account[ \t]*(?:name|holder(?:[ \t]*name)?)|a/c[ \t]*name|name)[ \t]*[:\-][ \t]*"
    r"(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?)?[ \t]*([A-Za-z][A-Za-z ,\.]{2,50}?)[ \t]*$",
    re.I | re.MULTILINE)
_PERIOD_RE    = re.compile(
    rf"(?:from\s*[:\-]?\s*|(?:statement|period|for)\b[^\d]{{0,30}}?)"
    rf"({_DATE_PAT})\s*(?:to|[-–])\s*[:\-]?\s*({_DATE_PAT})",
    re.I)
# Use findall for balances — take the LAST match (avoids intermediate values)
_OPEN_BAL_RE  = re.compile(
    r"opening\s+balance\s*[:\-]?\s*([\d,]+\.?\d*)"
    r"|balance\s+as\s+on\s+[^:\n]+[:\s]+([\d,]+\.?\d*)",
    re.I)
_CLOSE_BAL_RE = re.compile(r"closing\s+balance\s*[:\-]?\s*([\d,]+\.?\d*)", re.I)
_BRANCH_RE    = re.compile(r"branch[ \t]*[:\-][ \t]*([A-Za-z][A-Za-z ,\.]{2,40}?)[ \t]*$",
                           re.I | re.MULTILINE)
_CUST_ID_RE   = re.compile(r"(?:customer|cif)\s*(?:id|no|number)?\s*[:\-]?\s*(\w{5,20})", re.I)
_PAN_RE       = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")
_MOBILE_RE    = re.compile(r"(?:mobile|phone|contact)\s*(?:no\.?|number)?\s*[:\-]?\s*(\d{10})", re.I)

# CID escape codes from pdfplumber (e.g. "(cid:9)" = tab)
_CID_RE = re.compile(r"\(cid:\d+\)")


def _clean_meta_text(text: str) -> str:
    """Strip PDF CID escape codes and normalise whitespace."""
    return _CID_RE.sub(" ", text)


def extract_account_metadata(
    ocr_results: list[dict],
    bank_code: str = "",
) -> dict[str, Any]:
    """Scan all OCR text for account-level fields.

    If bank_code is provided, bank-specific regex patterns from
    parsers.bank_statement.banks.schemas are applied on top of
    (and take precedence over) the generic patterns.
    """
    raw = "\n".join(r.get("text", "") for r in ocr_results)
    text = _clean_meta_text(raw)
    meta: dict[str, Any] = {}

    m = _ACCT_NO_RE.search(text)
    if m:
        meta["account_number"] = re.sub(r"\s+", "", m.group(1))

    m = _IFSC_RE.search(text)
    if m:
        meta["ifsc_code"] = m.group(1)

    m = _ACCT_NAME_RE.search(text)
    if m:
        meta["account_holder"] = m.group(1).strip()

    m = _PERIOD_RE.search(text)
    if m:
        meta["statement_from"] = m.group(1)
        meta["statement_to"]   = m.group(2)

    # Take last occurrence of opening/closing balance (more reliable)
    # _OPEN_BAL_RE has two capture groups — take the first non-empty from each match
    all_open_matches = _OPEN_BAL_RE.findall(text)
    all_open = [next((v for v in groups if v), "") for groups in all_open_matches]
    all_open = [v for v in all_open if v]
    if all_open:
        meta["opening_balance"] = all_open[-1].replace(",", "")

    all_close = _CLOSE_BAL_RE.findall(text)
    if all_close:
        # Filter out obvious noise (single/two-digit values like "01")
        valid = [v for v in all_close if len(re.sub(r"[^\d]", "", v)) >= 3]
        if valid:
            meta["closing_balance"] = valid[-1].replace(",", "")

    m = _BRANCH_RE.search(text)
    if m:
        meta["branch"] = m.group(1).strip()

    m = _CUST_ID_RE.search(text)
    if m:
        meta["customer_id"] = m.group(1)

    m = _PAN_RE.search(text)
    if m:
        meta["pan"] = m.group(1)

    m = _MOBILE_RE.search(text)
    if m:
        meta["mobile"] = m.group(1)

    # Merge bank-specific metadata (overrides generic patterns where both match)
    if bank_code:
        bank_specific = extract_bank_metadata(text, bank_code)
        meta.update(bank_specific)

    return meta


# ── bank-specific column schemas ───────────────────────────────────────────────
# Backwards-compatible alias — authoritative source is parsers.bank_statement.banks.schemas
_BANK_SCHEMAS: dict[str, list[str]] = BANK_SCHEMAS


def get_schema(bank_code: str) -> list[str]:
    return get_bank_schema(bank_code)


# ── column-header detection from raw 2-D table ────────────────────────────────

_HDR_KEYWORDS = {
    "date", "narration", "particulars", "description", "details",
    "withdrawal", "deposit", "balance", "debit", "credit",
    "chq", "ref", "no", "amount", "dr", "cr", "value",
    "transaction", "init", "remarks",
}


def _looks_like_header(row: list[str]) -> bool:
    """True if most non-empty cells look like column labels (not dates/amounts)."""
    non_empty = [c for c in row if c.strip()]
    if not non_empty:
        return False
    label_count = sum(
        1 for c in non_empty
        if any(kw in c.lower() for kw in _HDR_KEYWORDS)
        and not re.search(r"\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}", c)
    )
    return label_count / len(non_empty) >= 0.5


def _remap_columns(
    rows: list[dict],
    bank_code: str,
) -> tuple[list[dict], list[str]]:
    """
    Try to rename generic col_0/col_1/... keys to schema-aligned names.
    Returns (remapped_rows, warnings).
    """
    if not rows:
        return rows, []

    schema = get_schema(bank_code)
    first_keys = list(rows[0].keys())

    # Already has named columns matching the schema → nothing to do
    norm_keys = {normalise_col_name(k) for k in first_keys}
    if any(s in norm_keys for s in ["date", "narration", "debit", "credit",
                                     "withdrawal", "deposit", "balance"]):
        return rows, []

    # All keys are generic col_N → try to map by position
    if all(re.match(r"col_\d+", k) for k in first_keys):
        n = len(first_keys)
        # Pad schema to match column count
        if n <= len(schema):
            mapping = {f"col_{i}": schema[i] for i in range(n)}
        else:
            # More columns than schema — pad with generic names
            mapping = {f"col_{i}": (schema[i] if i < len(schema) else f"col_{i}")
                       for i in range(n)}
        remapped = [{mapping.get(k, k): v for k, v in row.items()} for row in rows]
        return remapped, []

    # Partial mismatch → warn only
    missing = [s for s in schema if s not in norm_keys]
    warnings = []
    if missing:
        warnings.append(
            f"Expected columns not found for {bank_code.upper()}: {missing}"
        )
    return rows, warnings


def validate_and_relabel(
    rows: list[dict],
    bank_code: str,
) -> tuple[list[dict], list[str]]:
    """Check required columns; attempt remapping generic col_N names; return warnings."""
    rows, warnings = _remap_columns(rows, bank_code)
    if not rows or warnings:
        return rows, warnings

    schema = get_schema(bank_code)
    norm_detected = {normalise_col_name(c) for c in rows[0].keys()}
    missing = [s for s in schema if s and s not in norm_detected]
    if missing:
        warnings.append(
            f"Expected columns not found for {bank_code.upper()}: {missing}"
        )
    return rows, warnings


def _filter_empty_rows(rows: list[dict]) -> list[dict]:
    """Drop rows where all values are empty."""
    return [r for r in rows if any(v.strip() for v in r.values())]


def _fix_swapped_narration(rows: list[dict]) -> list[dict]:
    """
    Detect and swap chq_no ↔ narration when OCR spatial assignment places
    the long narration text in the chq_no column (common in Axis Bank
    where Chq No is empty for UPI transactions and narration starts at
    the same X-position).
    """
    if not rows:
        return rows
    chq_col = next((c for c in ("chq_no", "chq_ref_no") if c in rows[0]), None)
    narr_col = "narration"
    if not chq_col or narr_col not in rows[0]:
        return rows
    narr_empty = sum(1 for r in rows if not r.get(narr_col, "").strip())
    chq_long   = sum(1 for r in rows if len(r.get(chq_col, "")) > 30)
    if len(rows) > 0 and narr_empty / len(rows) > 0.8 and chq_long / len(rows) > 0.5:
        fixed = []
        for r in rows:
            nr = dict(r)
            nr[narr_col] = r.get(chq_col, "")
            nr[chq_col]  = ""
            fixed.append(nr)
        return fixed
    return rows


def parse(
    ocr_results: list[dict],
    bank_code: str = "default",
    n_cols: int | None = None,
    digital_rows: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Full bank-statement parse: metadata + transactions.

    digital_rows: pre-structured rows from pdfplumber digital extraction.
    When provided, skip spatial OCR reconstruction (which fails for digital
    pages because all items share the same full-page bbox).
    """
    metadata = extract_account_metadata(ocr_results, bank_code=bank_code)

    if digital_rows:
        rows = _filter_empty_rows(digital_rows)
        rows = clean_transaction_rows(rows)
        rows, warnings = validate_and_relabel(rows, bank_code)
    else:
        header_items, table_items = split_page_ocr(ocr_results)
        source = table_items if table_items else ocr_results
        raw_rows = reconstruct_table(source, n_cols=n_cols)
        rows = build_table_rows(raw_rows) if raw_rows else []
        rows = _filter_empty_rows(rows)
        rows, warnings = validate_and_relabel(rows, bank_code)
        rows = _fix_swapped_narration(rows)

    return {
        "doc_type":     "bank_statement",
        "metadata":     metadata,
        "transactions": rows,
        "warnings":     warnings,
    }
