import re
from config import AMOUNT_REGEX, DATE_REGEX


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    # remove non-printable characters
    text = re.sub(r"[^\x20-\x7E]", "", text)
    return text.strip()


def extract_amount(text: str) -> str | None:
    match = re.search(AMOUNT_REGEX, text.replace(",", ""))
    return match.group() if match else None


def extract_date(text: str) -> str | None:
    match = re.search(DATE_REGEX, text)
    return match.group() if match else None


def is_valid_date(text: str) -> bool:
    return bool(re.search(DATE_REGEX, text))


def build_table_rows(raw_rows: list[list[str]], schema: list[str] | None = None) -> list[dict]:
    """
    Map a 2-D list of cell strings to a list of dicts.

    If schema is provided (e.g. ["date", "description", "debit", "credit", "balance"])
    it is used as column names; otherwise columns are named col_0, col_1, …
    """
    if not raw_rows:
        return []

    # auto-detect header row if first row looks like text labels
    header = schema
    start = 0
    if header is None:
        first = raw_rows[0]
        if all(not extract_amount(c) and not is_valid_date(c) for c in first):
            header = [c.lower().strip() or f"col_{i}" for i, c in enumerate(first)]
            start = 1
        else:
            header = [f"col_{i}" for i in range(len(first))]

    rows = []
    for raw in raw_rows[start:]:
        # pad / trim to match header length
        padded = raw + [""] * max(0, len(header) - len(raw))
        row = {header[i]: clean_text(padded[i]) for i in range(len(header))}
        rows.append(row)

    return rows
