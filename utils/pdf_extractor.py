"""
Direct text extraction from digital (non-scanned) PDFs.

Detection strategy:
  - Open with PyMuPDF; count characters per page
  - Pages with > MIN_TEXT_CHARS embedded chars → "digital"
  - Pages with ≤ MIN_TEXT_CHARS → "scanned" (image-based, needs OCR)

Extraction strategy (digital pages):
  - pdfplumber for table detection + structured text (best layout fidelity)
  - PyMuPDF as fallback for plain text

Output format mirrors the OCR pipeline's page_result dict so callers
can treat digital and scanned pages identically.
"""
from __future__ import annotations

import re
from typing import Any

MIN_TEXT_CHARS = 50   # chars threshold to classify a page as digital


# ── PDF type detection ────────────────────────────────────────────────────────

def detect_pdf_page_types(pdf_path: str) -> list[str]:
    """
    Return list of page types (one per page): "digital" or "scanned".
    """
    import fitz
    doc = fitz.open(pdf_path)
    types: list[str] = []
    for page in doc:
        text = page.get_text("text").strip()
        types.append("digital" if len(text) >= MIN_TEXT_CHARS else "scanned")
    doc.close()
    return types


def classify_pdf(pdf_path: str) -> str:
    """
    Returns "digital", "scanned", or "mixed".
    """
    page_types = detect_pdf_page_types(pdf_path)
    if not page_types:
        return "scanned"
    digital = sum(1 for t in page_types if t == "digital")
    scanned = len(page_types) - digital
    if scanned == 0:
        return "digital"
    if digital == 0:
        return "scanned"
    return "mixed"


# ── OCR-compatible result builder ─────────────────────────────────────────────

def _make_ocr_item(text: str, bbox: list, confidence: float = 1.0) -> dict:
    return {"text": text.strip(), "confidence": confidence, "bbox": bbox}


# ── pdfplumber table extraction ───────────────────────────────────────────────

def _plumber_tables(plumber_page) -> list[dict]:
    """Extract tables from a pdfplumber page as list of {rows: [[cell,...]]}."""
    results = []
    try:
        tables = plumber_page.extract_tables()
        for tbl in tables:
            if not tbl:
                continue
            # Filter completely empty rows
            rows = [
                [cell.strip() if cell else "" for cell in row]
                for row in tbl
                if any(cell and cell.strip() for cell in row)
            ]
            if rows:
                results.append({"rows": rows})
    except Exception:
        pass
    return results


def _plumber_text_blocks(plumber_page) -> list[dict]:
    """
    Extract non-table text from a pdfplumber page as a list of OCR-compatible
    items. Uses word-level bounding boxes from pdfplumber for spatial fidelity.
    """
    items: list[dict] = []
    try:
        words = plumber_page.extract_words(use_text_flow=True, keep_blank_chars=False)
        for w in words:
            bbox = [w["x0"], w["top"], w["x1"], w["bottom"]]
            items.append(_make_ocr_item(w["text"], bbox))
    except Exception:
        # Fallback: get raw text as single item
        text = plumber_page.extract_text() or ""
        if text.strip():
            w, h = plumber_page.width, plumber_page.height
            items.append(_make_ocr_item(text, [0, 0, w, h]))
    return items


# ── Per-page digital extraction ───────────────────────────────────────────────

def extract_digital_page(
    pdf_path: str,
    page_index: int,
    page_num: int,
    bank_code: str = "",
) -> dict[str, Any]:
    """
    Extract text and tables from a single digital PDF page.
    Returns a page_result dict compatible with the OCR pipeline.

    bank_code: optional bank identifier forwarded to normalise_digital_bank_rows
               so bank-specific column aliases are applied during extraction.
    """
    import pdfplumber

    page_result: dict[str, Any] = {
        "page":         page_num,
        "text_blocks":  [],
        "tables":       [],
        "_extraction":  "digital",
        "_lang_summary": {
            "detected_languages": ["en"],
            "primary_language":   "en",
            "multilingual":       False,
            "translation_applied": False,
        },
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_index >= len(pdf.pages):
                return page_result
            pl_page = pdf.pages[page_index]

            # ── Tables ────────────────────────────────────────────────────────
            tbls = _plumber_tables(pl_page)
            for tbl in tbls:
                raw_rows = [
                    {f"col_{j}": cell for j, cell in enumerate(row)}
                    for row in tbl["rows"]
                ]
                # Normalise column names for bank transaction tables
                if is_bank_transaction_table(raw_rows):
                    raw_rows = normalise_digital_bank_rows(raw_rows, bank_code=bank_code)
                page_result["tables"].append({
                    "bbox": [0, 0, int(pl_page.width), int(pl_page.height)],
                    "rows": raw_rows,
                })

            # ── Text (words not inside table bboxes) ──────────────────────────
            # Crop away table regions first
            if tbls:
                try:
                    tbl_bboxes = [t.bbox for t in pl_page.find_tables()]
                    # Exclude words inside any table bbox
                    words = [
                        w for w in pl_page.extract_words(use_text_flow=True)
                        if not _inside_any(w, tbl_bboxes)
                    ]
                except Exception:
                    words = pl_page.extract_words(use_text_flow=True) or []
            else:
                words = pl_page.extract_words(use_text_flow=True) or []

            if words:
                # Group words into line-level text blocks by Y coordinate
                lines = _group_words_into_lines(words)
                for line_text, bbox in lines:
                    if line_text.strip():
                        page_result["text_blocks"].append({
                            "type":       "Text",
                            "bbox":       bbox,
                            "text":       line_text,
                            "confidence": 1.0,
                        })

            # Build _ocr_results (OCR-compatible items for classifiers/parsers)
            ocr_items: list[dict] = []
            # Text from text blocks
            for blk in page_result["text_blocks"]:
                ocr_items.append(_make_ocr_item(blk["text"], blk["bbox"]))
            # Text from tables (flattened)
            for tbl in page_result["tables"]:
                for row in tbl["rows"]:
                    row_text = " ".join(str(v) for v in row.values() if v)
                    if row_text.strip():
                        ocr_items.append(_make_ocr_item(row_text, tbl["bbox"]))
            page_result["_ocr_results"] = ocr_items

    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Digital extraction failed p%d: %s", page_num, exc)

    return page_result


def _inside_any(word: dict, bboxes: list) -> bool:
    wx0, wy0, wx1, wy1 = word["x0"], word["top"], word["x1"], word["bottom"]
    for bb in bboxes:
        bx0, by0, bx1, by1 = bb
        if wx0 >= bx0 - 2 and wy0 >= by0 - 2 and wx1 <= bx1 + 2 and wy1 <= by1 + 2:
            return True
    return False


def _group_words_into_lines(
    words: list[dict],
    y_tol: float = 3.0,
) -> list[tuple[str, list]]:
    """Cluster words by Y-position into lines; return (text, bbox) pairs."""
    if not words:
        return []
    sorted_words = sorted(words, key=lambda w: (round(w["top"] / y_tol), w["x0"]))
    lines: list[tuple[str, list]] = []
    cur_words: list[dict] = [sorted_words[0]]

    for w in sorted_words[1:]:
        prev = cur_words[-1]
        if abs(w["top"] - prev["top"]) <= y_tol * 2:
            cur_words.append(w)
        else:
            lines.append(_words_to_line(cur_words))
            cur_words = [w]
    lines.append(_words_to_line(cur_words))
    return lines


def _words_to_line(words: list[dict]) -> tuple[str, list]:
    text = " ".join(w["text"] for w in words)
    x0 = min(w["x0"] for w in words)
    y0 = min(w["top"] for w in words)
    x1 = max(w["x1"] for w in words)
    y1 = max(w["bottom"] for w in words)
    return text, [x0, y0, x1, y1]


# ── Bank statement table normalisation ────────────────────────────────────────

# Matches numeric dates (01/09/2023) and text dates (29 Sep 2023)
_DATE_RE = re.compile(
    r"\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b"
    r"|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b",
    re.I,
)
_AMOUNT_RE = re.compile(r"[\d,]+\.\d{2}")

# value_date MUST come before date — "Value Date" contains "date" as a substring
_BANK_COL_KEYWORDS: dict[str, list[str]] = {
    "value_date":  ["value date", "val date", "val. date"],
    "date":        ["tran date", "txn date", "trans date", "transaction date",
                    "posting date", "date"],
    "narration":   ["narration", "description", "particulars", "details",
                    "transaction desc", "transaction detail"],
    "chq_ref_no":  ["chq/ref", "chq no", "ref no", "cheque no", "chq.", "ref.",
                    "chq", "ref", "cheque", "reference"],
    "withdrawal":  ["withdrawal", "debit", "dr", "amount dr"],
    "deposit":     ["deposit", "credit", "cr", "amount cr"],
    "balance":     ["balance", "closing"],
}

_META_ROW_RE = re.compile(
    r"^(?:opening|closing)\s+balance|^total\b|^brought\s+forward|"
    r"^carried\s+forward|^b/f\b|^c/f\b",
    re.I,
)

# Default column schemas by column count (used when no header row present)
_DEFAULT_SCHEMAS: dict[int, list[str]] = {
    7: ["date", "value_date", "narration", "chq_ref_no", "withdrawal", "deposit", "balance"],
    6: ["date", "narration", "chq_ref_no", "withdrawal", "deposit", "balance"],
    5: ["date", "narration", "withdrawal", "deposit", "balance"],
}


def _normalise_cell(val) -> str:
    """Normalise a table cell: collapse any whitespace (handles multi-line pdfplumber cells)."""
    return re.sub(r"\s+", " ", str(val)).strip() if val is not None else ""


def _is_meta_row(row: dict) -> bool:
    """True if first non-empty cell is an opening/closing balance or total row."""
    first_nonempty = next((_normalise_cell(v) for v in row.values()
                           if _normalise_cell(v)), "")
    return bool(_META_ROW_RE.match(first_nonempty))


def _is_header_row(row: dict) -> bool:
    """True when a row looks like column labels (no dates, no amounts)."""
    values = [_normalise_cell(v) for v in row.values() if _normalise_cell(v)]
    return bool(values) and not any(
        _DATE_RE.search(v) or _AMOUNT_RE.search(v) for v in values
    )


def _map_col_name(header_text: str) -> str:
    """Map a column header string to a bank schema key via keyword matching."""
    h = re.sub(r"\s+", " ", header_text.lower().strip())
    for schema_key, keywords in _BANK_COL_KEYWORDS.items():
        if any(kw in h for kw in keywords):
            return schema_key
    return re.sub(r"[^\w]+", "_", h).strip("_") or "col"


def is_bank_transaction_table(rows: list[dict]) -> bool:
    """
    Return True if this table looks like a bank transaction table.
    Must have a date column AND at least one debit/credit/balance column.
    Used to exclude charge-statement or fee tables from transaction extraction.
    """
    if not rows:
        return False
    first_vals = [re.sub(r"\s+", " ", str(v).lower().strip())
                  for v in rows[0].values() if v]
    combined = " ".join(first_vals)
    has_date = "date" in combined
    has_amount_col = any(kw in combined for kw in
                         ["debit", "credit", "withdrawal", "deposit", "balance", "dr", "cr"])
    return has_date and has_amount_col


def normalise_digital_bank_rows(rows: list[dict], bank_code: str = "") -> list[dict]:
    """
    Map generic col_N keys → bank schema keys by matching the header row text.

    When bank_code is provided, bank-specific column aliases from
    parsers.bank_statement.banks.schemas are tried first before falling
    back to the generic _BANK_COL_KEYWORDS keyword matching.

    Handles:
    - pdfplumber multi-line cells ("Value\\nDate" → "value date")
    - Repeated header rows on continuation pages
    - Meta rows (OPENING BALANCE, CLOSING BALANCE, totals)
    - Tables with no header row (positional mapping by column count)
    Drops the header row and returns only clean data rows.
    """
    if not rows:
        return rows

    # Lazy import to avoid circular dependency at module load time
    _normalise_col_for_bank = None
    if bank_code:
        try:
            from parsers.bank_statement.banks import normalise_col_for_bank as _ncfb
            _normalise_col_for_bank = _ncfb
        except ImportError:
            pass

    def _resolve_col(header_text: str) -> str:
        """Try bank-specific alias first, then fall back to generic keyword match."""
        if _normalise_col_for_bank is not None:
            result = _normalise_col_for_bank(header_text, bank_code)
            if result is not None:
                return result
        return _map_col_name(header_text)

    first = rows[0]
    is_col_n = any(k.startswith("col_") for k in first)

    if is_col_n:
        if not _is_header_row(first):
            # Continuation page with no header — map by position
            n = len(first)
            schema = _DEFAULT_SCHEMAS.get(n, [f"col_{i}" for i in range(n)])
            mapping = {f"col_{i}": (schema[i] if i < len(schema) else f"col_{i}")
                       for i in range(n)}
        else:
            mapping = {k: _resolve_col(str(v)) for k, v in first.items()}

        rows_to_process = rows if not _is_header_row(first) else rows[1:]
    else:
        # Keys are already named (e.g. from a prior normalisation pass)
        mapping = {k: _resolve_col(k) for k in first}
        rows_to_process = rows

    result: list[dict] = []
    for row in rows_to_process:
        mapped = {mapping.get(k, k): _normalise_cell(v) for k, v in row.items()}
        if _is_meta_row(mapped):
            continue
        row_text = " ".join(v for v in mapped.values() if v)
        if _DATE_RE.search(row_text) or _AMOUNT_RE.search(row_text):
            result.append(mapped)
    return result
