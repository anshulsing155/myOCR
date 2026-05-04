"""Bank-specific column schemas and metadata patterns."""
from __future__ import annotations
import re

# ── per-bank column aliases ───────────────────────────────────────────────────
# Maps raw column header text → canonical schema key.
# These supplement (and override) the generic _BANK_COL_KEYWORDS in pdf_extractor.py
BANK_COL_ALIASES: dict[str, dict[str, str]] = {
    "sbi": {
        "txn date":             "date",
        "value date":           "value_date",
        "description":          "narration",
        "ref no./cheque no.":   "chq_ref_no",
        "ref no./cheque\nno.":  "chq_ref_no",
        "debit":                "withdrawal",
        "credit":               "deposit",
        "balance":              "balance",
    },
    "axis": {
        "tran date":   "date",
        "chq no":      "chq_ref_no",
        "particulars": "narration",
        "debit":       "withdrawal",
        "credit":      "deposit",
        "balance":     "balance",
        "init. br":    "init_br",
    },
    "hdfc": {
        "date":              "date",
        "narration":         "narration",
        "chq/ref no.":       "chq_ref_no",
        "chq./ref.no.":      "chq_ref_no",
        "value dt":          "value_date",
        "withdrawal amt.":   "withdrawal",
        "withdrawal amt":    "withdrawal",
        "deposit amt.":      "deposit",
        "deposit amt":       "deposit",
        "closing balance":   "balance",
    },
    "icici": {
        "transaction date": "date",
        "value date":        "value_date",
        "description":       "narration",
        "cheque number":     "chq_ref_no",
        "amount (inr)":      "amount",   # split later by debit/credit marker
        "balance (inr)":     "balance",
        "debit":             "withdrawal",
        "credit":            "deposit",
    },
    "kotak": {
        "transaction date": "date",
        "description":       "narration",
        "chq no":            "chq_ref_no",
        "debit":             "withdrawal",
        "credit":            "deposit",
        "balance":           "balance",
    },
    "pnb": {
        "posting date":  "date",
        "value date":    "value_date",
        "particulars":   "narration",
        "cheque no":     "chq_ref_no",
        "debit":         "withdrawal",
        "credit":        "deposit",
        "balance":       "balance",
    },
    "bob": {
        "transaction date": "date",
        "narration":         "narration",
        "chq no":            "chq_ref_no",
        "debit":             "withdrawal",
        "credit":            "deposit",
        "balance":           "balance",
    },
    "canara": {
        "date":          "date",
        "particulars":   "narration",
        "chq/ref no":    "chq_ref_no",
        "debit":         "withdrawal",
        "credit":        "deposit",
        "balance":       "balance",
    },
    "indusind": {
        "transaction date": "date",
        "value date":        "value_date",
        "description":       "narration",
        "chq no":            "chq_ref_no",
        "debit":             "withdrawal",
        "credit":            "deposit",
        "balance":           "balance",
    },
}

# ── bank-specific metadata patterns ──────────────────────────────────────────
BANK_METADATA_PATTERNS: dict[str, dict[str, str]] = {
    "sbi": {
        "account_number": r"account\s+number\s*[:\-\s]+(\d{8,20})",
        "account_holder": r"account\s+name\s*[:\-\s]+(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?)?\s*([A-Za-z][A-Za-z ,\.]{2,50}?)[ \t]*$",
        "ifsc_code":      r"i\.?f\.?s\.?c\.?\s*(?:code)?\s*[:\-\s]+([A-Z]{4}0[A-Z0-9]{6})",
        "branch":         r"branch\s*[:\-\s]+([A-Za-z][A-Za-z ,\.]{2,40}?)[ \t]*$",
        "cif_no":         r"cif\s*(?:no\.?|number)?\s*[:\-\s]+(\d{10,14})",
        "opening_balance":r"balance\s+as\s+on\s+[^:\n]+[:\s]+([\d,]+\.?\d*)",
    },
    "axis": {
        "account_number": r"account\s*(?:no\.?|number)?\s*[:\-\s]+(\d{8,20})",
        "account_holder": r"(?:name|account\s*name)\s*[:\-\s]+([A-Za-z][A-Za-z &,\.]{2,50}?)[ \t]*$",
        "ifsc_code":      r"ifsc\s*(?:code)?\s*[:\-\s]+([A-Z]{4}0[A-Z0-9]{6})",
        "customer_id":    r"customer\s*(?:id|no)\s*[:\-\s]+(\d{6,12})",
        "opening_balance":r"opening\s+balance\s*[:\-\s]*([\d,]+\.?\d*)",
        "closing_balance":r"closing\s+balance\s*[:\-\s]*([\d,]+\.?\d*)",
    },
    "hdfc": {
        "account_number": r"a/c\s*(?:no\.?|number)?\s*[:\-\s]+(\d{8,20})",
        "account_holder": r"(?:name|mr\.?|mrs\.?)\s*[:\-\s]*([A-Za-z][A-Za-z &,\.]{2,50}?)[ \t]*$",
        "ifsc_code":      r"ifsc\s*(?:code)?\s*[:\-\s]+([A-Z]{4}0[A-Z0-9]{6})",
        "branch":         r"branch\s*[:\-\s]+([A-Za-z][A-Za-z ,\.]{2,40}?)[ \t]*$",
        "opening_balance":r"opening\s+balance\s*[:\-\s]*([\d,]+\.?\d*)",
        "closing_balance":r"closing\s+balance\s*[:\-\s]*([\d,]+\.?\d*)",
    },
}

# ── canonical schema per bank ─────────────────────────────────────────────────
BANK_SCHEMAS: dict[str, list[str]] = {
    "sbi":      ["date", "value_date", "narration", "chq_ref_no", "withdrawal", "deposit", "balance"],
    "axis":     ["date", "chq_ref_no", "narration", "withdrawal", "deposit", "balance"],
    "hdfc":     ["date", "narration", "chq_ref_no", "value_date", "withdrawal", "deposit", "balance"],
    "icici":    ["date", "value_date", "narration", "chq_ref_no", "withdrawal", "deposit", "balance"],
    "kotak":    ["date", "narration", "chq_ref_no", "withdrawal", "deposit", "balance"],
    "pnb":      ["date", "value_date", "narration", "chq_ref_no", "withdrawal", "deposit", "balance"],
    "bob":      ["date", "narration", "chq_ref_no", "withdrawal", "deposit", "balance"],
    "canara":   ["date", "narration", "chq_ref_no", "withdrawal", "deposit", "balance"],
    "indusind": ["date", "value_date", "narration", "chq_ref_no", "withdrawal", "deposit", "balance"],
    "default":  ["date", "narration", "withdrawal", "deposit", "balance"],
}


def get_col_alias_map(bank_code: str) -> dict[str, str]:
    """Return column alias map for a specific bank (lowercased keys)."""
    return {k.lower(): v for k, v in BANK_COL_ALIASES.get(bank_code, {}).items()}


def normalise_col_for_bank(header_text: str, bank_code: str) -> str | None:
    """
    Map a column header string to canonical key using bank-specific aliases.
    Returns None if no match found (caller should fall back to generic mapping).
    """
    import re
    h = re.sub(r"\s+", " ", header_text.lower().strip())
    alias_map = get_col_alias_map(bank_code)
    # Exact match first
    if h in alias_map:
        return alias_map[h]
    # Partial match
    for alias, canonical in alias_map.items():
        if alias in h or h in alias:
            return canonical
    return None


def extract_bank_metadata(text: str, bank_code: str) -> dict:
    """Extract bank-specific metadata fields from raw text."""
    import re
    patterns = BANK_METADATA_PATTERNS.get(bank_code, {})
    result = {}
    for field, pattern in patterns.items():
        m = re.search(pattern, text, re.I | re.MULTILINE)
        if m:
            val = m.group(1).strip()
            # Clean commas from balance amounts
            if "balance" in field:
                val = val.replace(",", "")
            result[field] = val
    return result


def get_bank_schema(bank_code: str) -> list[str]:
    return BANK_SCHEMAS.get(bank_code, BANK_SCHEMAS["default"])
