"""Shared utilities for all real-estate parsers."""
from __future__ import annotations

import re

# ── Date normalisation ────────────────────────────────────────────────────────
_MONTH_MAP = {
    "jan": "01", "january": "01", "feb": "02", "february": "02",
    "mar": "03", "march": "03",   "apr": "04", "april": "04",
    "may": "05",                   "jun": "06", "june": "06",
    "jul": "07", "july": "07",    "aug": "08", "august": "08",
    "sep": "09", "september": "09","oct": "10", "october": "10",
    "nov": "11", "november": "11", "dec": "12", "december": "12",
}


def norm_date(raw: str | None) -> str | None:
    if raw is None:
        return None
    raw = raw.strip()
    m = re.match(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", raw)
    if m:
        d, mon, y = m.groups()
        mn = _MONTH_MAP.get(mon.lower(), "00")
        return f"{d.zfill(2)}/{mn}/{y}"
    raw = raw.replace("-", "/").replace(".", "/")
    parts = raw.split("/")
    if len(parts) == 3:
        d, mn, y = parts
        if len(y) == 2:
            y = ("20" if int(y) < 50 else "19") + y
        return f"{d.zfill(2)}/{mn.zfill(2)}/{y}"
    return raw


# ── Amount parsing ────────────────────────────────────────────────────────────
_CRORE_RE  = re.compile(r"([\d,]+(?:\.\d+)?)\s*crore", re.I)
_LAKH_RE   = re.compile(r"([\d,]+(?:\.\d+)?)\s*lakh", re.I)
_AMOUNT_RE = re.compile(r"(?:rs\.?|inr|rupees?)[\.:\s]*([\d,]+(?:\.\d{1,2})?)", re.I)


def clean_amount(raw: str | None) -> str | None:
    if raw is None:
        return None
    return raw.strip().replace(",", "")


def parse_amount(text: str) -> str | None:
    """Return rupee amount as plain numeric string (handles lakh/crore words)."""
    m = _CRORE_RE.search(text)
    if m:
        val = float(m.group(1).replace(",", "")) * 1_00_00_000
        return str(int(val))
    m = _LAKH_RE.search(text)
    if m:
        val = float(m.group(1).replace(",", "")) * 1_00_000
        return str(int(val))
    m = _AMOUNT_RE.search(text)
    if m:
        return clean_amount(m.group(1))
    return None


# ── Area parsing ──────────────────────────────────────────────────────────────
_AREA_RE = re.compile(
    r"([\d,]+(?:\.\d+)?)\s*"
    r"(sq\.?\s*(?:ft|feet|yard|meter|metre|mt|mtr)|sqft|sqmt|sqyd|"
    r"acre|acres|hectare|hectares|guntha|gunta|cent|cents|"
    r"bigha|biswa|marla|kanal|ground|dismil|decimal|ankanam|"
    r"sq\.?\s*m\.?|sq\.?\s*y\.?)",
    re.I
)


def parse_area(text: str) -> dict | None:
    m = _AREA_RE.search(text)
    if m:
        return {"value": m.group(1).replace(",", ""), "unit": m.group(2).strip()}
    return None


# ── Party name extraction ─────────────────────────────────────────────────────
_PARTY_SPLIT_RE = re.compile(r"\band\b|\bhereinafter\b", re.I)


def extract_parties(label_re: re.Pattern, text: str, stop_re: re.Pattern) -> list[str]:
    """Extract one or more names following a label until a stop pattern."""
    m = label_re.search(text)
    if not m:
        return []
    segment = text[m.end():]
    stop = stop_re.search(segment)
    if stop:
        segment = segment[: stop.start()]
    raw = segment.strip().strip(":").strip()
    parts = [p.strip().title() for p in _PARTY_SPLIT_RE.split(raw) if p.strip()]
    return [p for p in parts if 2 <= len(p) <= 60 and not any(c.isdigit() for c in p[:3])]


# ── Shared regex constants ────────────────────────────────────────────────────
PIN_RE      = re.compile(r"\b(\d{6})\b")
STATE_RE    = re.compile(
    r"\b(andhra\s*pradesh|arunachal\s*pradesh|assam|bihar|chhattisgarh|goa|gujarat|"
    r"haryana|himachal\s*pradesh|jharkhand|karnataka|kerala|madhya\s*pradesh|"
    r"maharashtra|manipur|meghalaya|mizoram|nagaland|odisha|punjab|rajasthan|"
    r"sikkim|tamil\s*nadu|telangana|tripura|uttar\s*pradesh|uttarakhand|west\s*bengal|"
    r"delhi|jammu\s*and\s*kashmir|ladakh|chandigarh|puducherry|"
    r"andaman|lakshadweep|dadra)\b",
    re.I,
)
DISTRICT_RE = re.compile(r"(?:district|dist\.?)[:\s]+([A-Za-z\s]+?)(?:\n|state|pin|taluk)", re.I)
SRO_RE      = re.compile(
    r"(?:sub[\s\-]?registrar(?:'s)?\s*office|sro|office\s*of\s*sub[\s\-]?registrar)"
    r"[:\s,]+([A-Za-z\s,\-]+?)(?:\n|book|vol|doc|reg|\d{4})",
    re.I,
)
STAMP_RE    = re.compile(
    r"(?:stamp\s*duty\s*paid|stamp\s*duty|e[\s\-]?stamp)[:\s]+(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
REGN_NO_RE  = re.compile(
    r"(?:reg(?:istration)?\s*(?:no\.?|number)|doc(?:ument)?\s*(?:no\.?|number))"
    r"[:\s]+([A-Z0-9/\-]+)",
    re.I,
)
BOOK_RE     = re.compile(
    r"book\s*(?:no\.?|number)?[:\s]+(\d+).*?vol(?:ume)?[:\s]+(\d+).*?page[:\s]+(\d+)",
    re.I | re.S,
)
DATE_RE     = re.compile(r"\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b")
SURVEY_RE   = re.compile(
    r"(?:survey\s*(?:no\.?|number)|s\.?\s*no\.?|khasra\s*(?:no\.?|number)|"
    r"plot\s*(?:no\.?|number)|gat\s*(?:no\.?|number)|dag\s*(?:no\.?|number))"
    r"[:\s]+([A-Z0-9/,\s]+?)(?:\n|area|measuring|admeasuring|ward|dist)",
    re.I,
)
IFSC_RE     = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")
