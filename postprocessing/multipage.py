"""
Multi-page table merging.

Bank statements spread a single transaction table across many pages.
Each page repeats the bank header + sometimes the column header, then
continues with data rows.  This module merges those into one table.
"""

from __future__ import annotations

import copy


def _col_keys(rows: list[dict]) -> tuple[str, ...]:
    return tuple(rows[0].keys()) if rows else ()


def _is_header_row(row: dict, reference_keys: tuple) -> bool:
    """True if row looks like a repeated column header (values match keys)."""
    if not reference_keys:
        return False
    values = [str(v).strip().lower() for v in row.values()]
    keys = [k.strip().lower() for k in reference_keys]
    # header row: cell values match or are substrings of column names
    matches = sum(v == k or v in k or k in v for v, k in zip(values, keys))
    return matches >= len(reference_keys) // 2


def merge_multipage_tables(pages: list[dict]) -> list[dict]:
    """
    If page N ends with a table and page N+1 starts with a table having the
    same column count, treat them as one continued table.

    Removes the merged table from subsequent pages so the UI shows one unified
    table on page 1 (or whichever page the table first appears).
    """
    if len(pages) < 2:
        return pages

    result = copy.deepcopy(pages)

    i = 0
    while i < len(result) - 1:
        curr_tbls = result[i].get("tables", [])
        next_tbls = result[i + 1].get("tables", [])

        if not curr_tbls or not next_tbls:
            i += 1
            continue

        last = curr_tbls[-1]
        first = next_tbls[0]
        last_rows: list[dict] = last.get("rows", [])
        next_rows: list[dict] = first.get("rows", [])

        if not last_rows or not next_rows:
            i += 1
            continue

        last_keys = _col_keys(last_rows)
        next_keys = _col_keys(next_rows)

        # Same column structure → merge
        if last_keys == next_keys:
            # Skip repeated header row on the next page
            data_rows = next_rows
            if data_rows and _is_header_row(data_rows[0], last_keys):
                data_rows = data_rows[1:]

            last["rows"] = last_rows + data_rows

            # Remove merged table from next page
            result[i + 1]["tables"] = next_tbls[1:]

        i += 1

    return result
