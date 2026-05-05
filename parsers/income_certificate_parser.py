"""Income Certificate parser — tehsildar / revenue department issuance."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

_CERT_NO_RE   = re.compile(
    r"(?:certificate\s*(?:no\.?|number)|ref(?:erence)?\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)",
    re.I
)
_NAME_LBL_RE  = re.compile(
    r"(?:name\s*of\s*(?:the\s*)?applicant|applicant'?s?\s*name|certify\s+that\s+(?:shri|smt|kumari|mr\.?|ms\.?|mrs\.?)?\.?\s*)([A-Z][A-Za-z\s\.]+?)(?:\n|,|son|daughter|s/o|d/o|w/o|age|residing)",
    re.I
)
_RELATION_RE  = re.compile(
    r"\b(?:s/o|d/o|w/o|son\s+of|daughter\s+of|wife\s+of|father[:\s]+)[:\s]+([A-Z][A-Za-z\s]+?)(?:\n|,|age|res|vill|dist)",
    re.I
)
_INCOME_RE    = re.compile(
    r"(?:annual\s*income|yearly\s*income|income\s*per\s*annum|income)[:\s]+"
    r"(?:rs\.?|inr|rupees?)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I
)
_INCOME_WORDS_RE = re.compile(
    r"(?:rs\.?|inr|rupees?)\s*([\d,]+(?:\.\d{1,2})?)\s*(?:per\s*annum|p\.?a\.?|yearly|annually)",
    re.I
)
_PURPOSE_RE   = re.compile(
    r"(?:purpose|for\s*the\s*purpose\s*of)[:\s]+([A-Za-z\s,]+?)(?:\n|date|issued)",
    re.I
)
_ISSUE_DATE_RE = re.compile(
    r"(?:date\s*of\s*issue|issued?\s*on|date)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I
)
_VALID_RE     = re.compile(
    r"(?:valid\s*(?:till|upto|until|for)|validity)[:\s]*([A-Za-z0-9\s/\-]+?)(?:\n|date|from)",
    re.I
)
_DISTRICT_RE  = re.compile(r"(?:district|dist\.?)[:\s]+([A-Za-z\s]+?)(?:\n|state|pin|tehsil)", re.I)
_STATE_RE     = re.compile(
    r"\b(andhra\s*pradesh|arunachal\s*pradesh|assam|bihar|chhattisgarh|goa|gujarat|"
    r"haryana|himachal\s*pradesh|jharkhand|karnataka|kerala|madhya\s*pradesh|"
    r"maharashtra|manipur|meghalaya|mizoram|nagaland|odisha|punjab|rajasthan|"
    r"sikkim|tamil\s*nadu|telangana|tripura|uttar\s*pradesh|uttarakhand|west\s*bengal|"
    r"delhi|jammu\s*and\s*kashmir|ladakh)\b",
    re.I
)
_AUTHORITY_RE = re.compile(
    r"(?:issued?\s*by|issuing\s*authority|tehsildar|revenue)[:\s]+([A-Za-z\s,\.]+?)(?:\n|date|sign)",
    re.I
)
_ADDRESS_RE   = re.compile(r"(?:res(?:iding|ident)?\s*(?:at|of)|address|village|vill\.?)[:\s]+([A-Za-z0-9\s,/\-\.]+?)(?:\n\n|\d{6}|dist)", re.I)


def _norm_date(raw: str | None) -> str | None:
    if raw is None:
        return None
    raw = raw.strip().replace("-", "/").replace(".", "/")
    parts = raw.split("/")
    if len(parts) == 3:
        d, m, y = parts
        if len(y) == 2:
            y = ("20" if int(y) < 50 else "19") + y
        return f"{d.zfill(2)}/{m.zfill(2)}/{y}"
    return raw


def _clean_amount(raw: str | None) -> str | None:
    if raw is None:
        return None
    return raw.strip().replace(",", "")


class IncomeCertificateParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "income_certificate"}

        m = _CERT_NO_RE.search(text)
        if m:
            result["certificate_number"] = m.group(1).strip()

        m = _NAME_LBL_RE.search(text)
        if m:
            result["name"] = m.group(1).strip().title()

        m = _RELATION_RE.search(text)
        if m:
            result["relation_name"] = m.group(1).strip().title()

        # Annual income — prefer labelled, fallback to per-annum context
        m = _INCOME_RE.search(text) or _INCOME_WORDS_RE.search(text)
        if m:
            result["annual_income"] = _clean_amount(m.group(1))

        m = _PURPOSE_RE.search(text)
        if m:
            result["purpose"] = m.group(1).strip().title()

        m = _ISSUE_DATE_RE.search(text)
        if m:
            result["issue_date"] = _norm_date(m.group(1))

        m = _VALID_RE.search(text)
        if m:
            result["valid_upto"] = m.group(1).strip()

        m = _ADDRESS_RE.search(text)
        if m:
            result["address"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = _DISTRICT_RE.search(text)
        if m:
            result["district"] = m.group(1).strip().title()

        m = _STATE_RE.search(text)
        if m:
            result["state"] = m.group(1).strip().title()

        m = _AUTHORITY_RE.search(text)
        if m:
            result["issued_by"] = m.group(1).strip().title()

        result["raw_text"] = text
        return result
