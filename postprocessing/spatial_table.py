"""
Reconstruct table structure from OCR bounding boxes.

Uses spatial clustering on X/Y coordinates of each OCR text line instead of
OpenCV grid-line detection (which fails on borderless tables).
"""

from __future__ import annotations
import re
import statistics
from typing import Optional


# ── bbox helpers ──────────────────────────────────────────────────────────────

def _bbox_to_center(bbox) -> tuple[float, float, float, float]:
    """Return (cx, cy, width, height) for any bbox format."""
    if not bbox:
        return (0.0, 0.0, 0.0, 0.0)
    try:
        if isinstance(bbox[0], (list, tuple)):
            xs = [float(p[0]) for p in bbox]
            ys = [float(p[1]) for p in bbox]
            return (sum(xs) / len(xs), sum(ys) / len(ys),
                    max(xs) - min(xs), max(ys) - min(ys))
        if len(bbox) == 4:
            x1, y1, x2, y2 = (float(v) for v in bbox)
            if x2 > x1 and y2 > y1 and x2 <= x1 + 5000:
                return ((x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1)
            return (x1 + x2 / 2, y1 + y2 / 2, x2, y2)
    except (TypeError, IndexError, ValueError):
        pass
    return (0.0, 0.0, 0.0, 0.0)


# ── row grouping ──────────────────────────────────────────────────────────────

def group_into_rows(ocr_results: list[dict],
                    row_tolerance: float = 0.55) -> list[list[dict]]:
    """Group OCR items into rows by Y-coordinate; each row sorted left-to-right."""
    if not ocr_results:
        return []

    annotated = []
    for item in ocr_results:
        cx, cy, w, h = _bbox_to_center(item.get("bbox", []))
        x1 = cx - w / 2   # left edge
        annotated.append({**item, "_cx": cx, "_cy": cy, "_w": w, "_h": h, "_x1": x1})

    annotated.sort(key=lambda x: x["_cy"])
    rows: list[list[dict]] = []
    current = [annotated[0]]

    for item in annotated[1:]:
        ref = current[-1]
        row_h = max(item["_h"], ref["_h"], 1.0)
        if abs(item["_cy"] - ref["_cy"]) <= row_h * row_tolerance:
            current.append(item)
        else:
            rows.append(sorted(current, key=lambda x: x["_cx"]))
            current = [item]

    rows.append(sorted(current, key=lambda x: x["_cx"]))
    return rows


# ── column detection ──────────────────────────────────────────────────────────

def _detect_col_centers(rows: list[list[dict]],
                         n_cols: Optional[int] = None) -> list[float]:
    all_x = sorted({round(item["_cx"]) for row in rows for item in row})
    if not all_x:
        return []

    if n_cols is None:
        lengths = [len(r) for r in rows if len(r) >= 2]
        n_cols = int(statistics.median(lengths)) if lengths else 1

    n_cols = max(1, min(n_cols, 30))
    if len(all_x) <= n_cols:
        return [float(x) for x in all_x]

    gaps = sorted(
        ((all_x[i + 1] - all_x[i], i) for i in range(len(all_x) - 1)),
        reverse=True,
    )
    split_pts = sorted(g[1] + 1 for g in gaps[: n_cols - 1])

    centers, prev = [], 0
    for sp in split_pts + [len(all_x)]:
        cluster = all_x[prev:sp]
        centers.append(sum(cluster) / len(cluster))
        prev = sp
    return centers


def _assign_columns(row: list[dict], col_centers: list[float]) -> list[str]:
    cells = [""] * len(col_centers)
    for item in row:
        x = item["_cx"]
        nearest = min(range(len(col_centers)), key=lambda i: abs(col_centers[i] - x))
        text = item.get("text", "").strip()
        cells[nearest] = (cells[nearest] + " " + text).strip() if cells[nearest] else text
    return cells


def _get_col_boundaries(header_row: list[dict]) -> list[float]:
    """Left-edge X positions of each header item, sorted left-to-right."""
    return sorted(item["_x1"] for item in header_row)


def _assign_by_boundary(row: list[dict], boundaries: list[float],
                         tolerance: float = 20.0) -> list[str]:
    """
    Assign each item to a column by comparing its left edge (_x1) against
    the column left-edge boundaries extracted from the header row.

    This handles right-aligned numbers that share a column with a left-aligned
    header label: both have _x1 values within the same column's horizontal span.
    """
    cells = [""] * len(boundaries)
    for item in row:
        x1 = item["_x1"]
        col_idx = 0
        for j, bound in enumerate(boundaries):
            if x1 >= bound - tolerance:
                col_idx = j
        text = item.get("text", "").strip()
        cells[col_idx] = (cells[col_idx] + " " + text).strip() if cells[col_idx] else text
    return cells


# ── table-header detection ────────────────────────────────────────────────────
# Require "date" AND at least one of: amount word OR description word.
# This prevents the bank letterhead (which contains "No", "Ref" etc.) from
# being mistakenly treated as the table start.

_HDR_DATE   = frozenset(["date"])
_HDR_AMOUNT = frozenset(["withdrawal", "deposit", "balance", "amount",
                          "debit", "credit"])
_HDR_DESC   = frozenset(["narration", "description", "particulars",
                          "transaction", "details"])


def find_table_header_row(rows: list[list[dict]],
                           min_cols: int = 2) -> Optional[int]:
    """
    Return index of the actual column-header row (e.g. "Date | Narration |
    Withdrawal | Deposit | Balance"), or None.

    Strategy: scan each row's combined text.  A header row MUST contain
    "date" AND at least one amount/description keyword.  This avoids false
    positives on bank letterhead which contains "No", "Ref", etc.
    """
    for i, row in enumerate(rows):
        if len(row) < min_cols:
            continue
        combined = " ".join(item.get("text", "").lower() for item in row)

        if not any(kw in combined for kw in _HDR_DATE):
            continue
        if any(kw in combined for kw in _HDR_AMOUNT) or \
           any(kw in combined for kw in _HDR_DESC):
            return i

    return None


# ── column-name normalisation ─────────────────────────────────────────────────

_COL_NORM = [
    (re.compile(r"date\s+narration|date\s+particulars|date\s+description"),
     "date_narration"),
    (re.compile(r"withdrawal\s*(amt\.?|amount)?"), "withdrawal"),
    (re.compile(r"deposit\s*(amt\.?|amount)?"),    "deposit"),
    (re.compile(r"closing\s*balance|balance"),     "balance"),
    (re.compile(r"chq[\./]?ref[\./]?no\.?|cheque.*no|ref.*no"),
     "chq_ref_no"),
    (re.compile(r"value\s*date"),                  "value_date"),
    (re.compile(r"dr[\. ]+(withdrawal|amt)"),      "withdrawal"),
    (re.compile(r"cr[\. ]+(deposit|amt)"),         "deposit"),
    (re.compile(r"\bdate\b"),                      "date"),
    (re.compile(r"narration|particulars|description|details"), "narration"),
    (re.compile(r"debit"),                         "debit"),
    (re.compile(r"credit"),                        "credit"),
    (re.compile(r"\bsl[\. ]?no\.?\b|\bsi[\. ]?no\.?\b|\bsr[\. ]?no\.?\b"),
     "sl_no"),
]


def normalise_col_name(raw: str) -> str:
    s = raw.lower().strip()
    for pattern, replacement in _COL_NORM:
        if pattern.search(s):
            return replacement
    # fallback: keep as-is but clean punctuation/spaces
    return re.sub(r"[^\w]+", "_", s).strip("_") or raw


# ── continuation-row merging ──────────────────────────────────────────────────

_DATE_START_RE = re.compile(r"^\d{1,2}[/\-:\.]\d{1,2}[/\-:\.]\d{2,4}")


def merge_continuation_rows(rows: list[list[str]]) -> list[list[str]]:
    """
    Bank-statement transactions often wrap: the narration/reference text
    continues on the next physical line.  Merge those continuation lines
    into the preceding data row.

    A row is a continuation if its first cell does NOT start with a date
    pattern AND has no amount-like values in the right-hand columns.
    """
    if len(rows) < 2:
        return rows

    n_cols = max(len(r) for r in rows)
    # Determine which column index looks like a date column (first with dates)
    date_col = 0

    merged: list[list[str]] = [rows[0][:]]

    for row in rows[1:]:
        padded = row + [""] * max(0, n_cols - len(row))
        first_cell = padded[date_col].strip()

        is_continuation = (
            not _DATE_START_RE.match(first_cell)
            and not any(padded[c].strip() for c in range(2, n_cols))
        )

        if is_continuation and merged:
            # Append continuation text to the narration column of previous row
            prev = merged[-1][:]
            prev_narr = prev[1] if len(prev) > 1 else prev[0]
            cont_text = " ".join(c for c in padded if c.strip())
            if cont_text:
                if len(prev) > 1:
                    prev[1] = (prev_narr + " " + cont_text).strip()
                else:
                    prev[0] = (prev_narr + " " + cont_text).strip()
            merged[-1] = prev
        else:
            merged.append(padded)

    return merged


# ── public API ────────────────────────────────────────────────────────────────

def reconstruct_table(ocr_results: list[dict],
                       n_cols: Optional[int] = None) -> list[list[str]]:
    """Convert flat OCR results (with bbox) → 2-D table with continuation rows merged."""
    if not ocr_results:
        return []
    rows = group_into_rows(ocr_results)
    if not rows:
        return []

    # The first row (column-header) defines the canonical column layout.
    # Use left-edge boundaries from the header row for column assignment so that
    # right-aligned numeric values (whose center X drifts rightward) still land
    # in the correct column.
    header_row = rows[0]
    if n_cols is None:
        n_cols = len(header_row)

    boundaries = _get_col_boundaries(header_row)

    if len(boundaries) == n_cols:
        raw = [_assign_by_boundary(row, boundaries) for row in rows]
    else:
        # Fallback: gap-based center clustering
        col_centers = _detect_col_centers(rows, n_cols)
        if not col_centers:
            raw = [[item.get("text", "") for item in row] for row in rows]
        else:
            raw = [_assign_columns(row, col_centers) for row in rows]

    return merge_continuation_rows(raw)


def split_page_ocr(
    ocr_results: list[dict],
    force_table: bool = False,
) -> tuple[list[dict], list[dict]]:
    """
    Split OCR items into (header_items, table_items).
    header_items = everything above the column-header row.
    table_items  = column-header row + data rows.

    force_table=True  — skip column-header detection; treat entire page as table
                        (used for bank-statement continuation pages 2+).
    Returns (all, []) when no table header is detected and force_table is False.
    """
    if not ocr_results:
        return ocr_results, []

    rows = group_into_rows(ocr_results)

    if force_table:
        # Bank statement continuation: no column header on pages 2+.
        # Return all items as table; parser filters out letterhead rows.
        return [], ocr_results

    start = find_table_header_row(rows)

    if start is None:
        # Fallback: if most rows start with a date pattern it's a continuation page
        date_rows = sum(
            1 for row in rows
            if row and _DATE_START_RE.match(row[0].get("text", "").strip())
        )
        if len(rows) > 3 and date_rows / len(rows) >= 0.3:
            return [], ocr_results   # treat whole page as table
        return ocr_results, []

    header_items = [item for row in rows[:start] for item in row]
    table_items  = [item for row in rows[start:] for item in row]
    return header_items, table_items
