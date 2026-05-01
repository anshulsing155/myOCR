import re
from config import AMOUNT_REGEX, DATE_REGEX


# ── basic text cleaning ───────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\x20-\x7E]", "", text)
    return text.strip()


# ── date handling ─────────────────────────────────────────────────────────────

def normalize_date(text: str) -> str:
    """
    Fix common OCR date misreads:
      02/10:25  →  02/10/25
      02-10-25  →  02/10/25
      02.10.25  →  02/10/25
    Handles both 2-digit and 4-digit years.
    """
    return re.sub(
        r"(\d{1,2})[:/\-\.](\d{1,2})[:/\-\.](\d{2,4})",
        lambda m: f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{m.group(3)}",
        text,
    )


def extract_date(text: str) -> str | None:
    text = normalize_date(text)
    match = re.search(DATE_REGEX, text)
    return match.group() if match else None


def is_valid_date(text: str) -> bool:
    return bool(re.search(DATE_REGEX, normalize_date(text)))


# ── amount handling ───────────────────────────────────────────────────────────

# Common OCR substitutions in digit fields
_DIGIT_MAP = str.maketrans("OolISBs", "0011585")


def clean_amount(text: str) -> str | None:
    """
    Normalize OCR-mangled financial amounts.

    Handles:  ,320(0)  →  320.0
              207.00)  →  207.00
              1,00,000 →  100000
              -170,00  →  -170.00  (European decimal)
    Returns a plain decimal string, or None if no number found.
    """
    if not text:
        return None
    t = re.sub(r"\s+", "", text).translate(_DIGIT_MAP)
    # (digits) → -digits  (parenthesis = negative in accounting)
    t = re.sub(r"\((\d[\d,\.]*)\)", r"-\1", t)
    # strip stray trailing/leading parentheses and other junk
    t = re.sub(r"[()CR\s]", "", t)
    # extract the numeric part
    m = re.search(r"-?\d[\d,\.]*", t)
    if not m:
        return None
    num = m.group().replace(",", "")
    # guard against things like "1.2.3"
    if num.count(".") > 1:
        num = num.replace(".", "", num.count(".") - 1)
    return num


def extract_amount(text: str) -> str | None:
    cleaned = clean_amount(text)
    if cleaned and re.search(r"\d+\.\d{2}$", cleaned):
        return cleaned
    # fallback to original regex
    match = re.search(AMOUNT_REGEX, (text or "").replace(",", ""))
    return match.group() if match else None


# ── row / table cleaning ──────────────────────────────────────────────────────

_DATE_KEYS    = {"date", "value", "valuedate", "value_date", "txndate"}
_AMOUNT_KEYS  = {"amount", "withdrawal", "deposit", "balance",
                 "debit", "credit", "dr", "cr", "closing", "opening",
                 "withdrawalamt", "depositamt"}


def clean_transaction_rows(rows: list[dict]) -> list[dict]:
    """
    Apply field-type-aware cleaning to a list of transaction row dicts.
    Date fields: normalize_date
    Amount fields: clean_amount (keep original if parsing fails)
    All fields: clean_text
    """
    cleaned = []
    for row in rows:
        new_row = {}
        for k, v in row.items():
            k_norm = re.sub(r"[\s/\.\-_]+", "", k.lower())
            val = clean_text(str(v)) if v else ""
            if any(dk in k_norm for dk in _DATE_KEYS):
                val = normalize_date(val)
            elif any(ak in k_norm for ak in _AMOUNT_KEYS):
                cleaned_amt = clean_amount(val)
                val = cleaned_amt if cleaned_amt is not None else val
            new_row[k] = val
        cleaned.append(new_row)
    return cleaned


# ── table builder ─────────────────────────────────────────────────────────────

def build_table_rows(raw_rows: list[list[str]],
                     schema: list[str] | None = None) -> list[dict]:
    """
    Map a 2-D list of cell strings to a list of dicts.

    Auto-detects a header row if the first row looks like text labels.
    Normalises column names and applies clean_transaction_rows().
    """
    if not raw_rows:
        return []

    from postprocessing.spatial_table import normalise_col_name

    header = schema
    start = 0
    if header is None:
        first = raw_rows[0]
        if all(not extract_amount(c) and not is_valid_date(c) for c in first):
            header = [normalise_col_name(c) or f"col_{i}"
                      for i, c in enumerate(first)]
            start = 1
        else:
            header = [f"col_{i}" for i in range(len(first))]

    # Deduplicate column names (e.g. two "col_0")
    seen: dict[str, int] = {}
    deduped = []
    for name in header:
        if name in seen:
            seen[name] += 1
            deduped.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 0
            deduped.append(name)
    header = deduped

    rows = []
    for raw in raw_rows[start:]:
        padded = raw + [""] * max(0, len(header) - len(raw))
        row = {header[i]: clean_text(padded[i]) for i in range(len(header))}
        rows.append(row)

    return clean_transaction_rows(rows)
