"""e-Stamp Certificate / Stamp Duty Receipt / Franking Certificate parser."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser
from parsers.realestate._helpers import norm_date, clean_amount, STATE_RE

# e-Stamp number: IN-XX followed by digits+chars (SHCIL format)
_CERT_NO_RE    = re.compile(
    r"(?:certificate\s*(?:no\.?|number)|estamp\s*(?:no\.?|number)|"
    r"stamp\s*certificate\s*(?:no\.?|number))[:\s]+([A-Z0-9\-/]+)",
    re.I,
)
_ESTAMP_BARE_RE = re.compile(r"\bIN[\-]?[A-Z]{2}\d{17,}\b")
_GRN_RE        = re.compile(r"(?:grn|grn\s*(?:no\.?|number)|reference\s*(?:no\.?|number))[:\s]+([A-Z0-9\-/]+)", re.I)
_PURCHASER_RE  = re.compile(
    r"(?:purchaser(?:'s)?\s*name|purchased\s*by|name\s*of\s*(?:the\s*)?purchaser|first\s*party)"
    r"[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|second\s*party|description|amount|date|grn)",
    re.I,
)
_SECOND_PARTY_RE = re.compile(
    r"(?:second\s*party|payee|in\s*favour\s*of)[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|description|amount|date|grn|first\s*party)",
    re.I,
)
_DESC_RE       = re.compile(
    r"(?:description\s*of\s*document|purpose|article\s*(?:no\.?|number)|"
    r"reason\s*for\s*stamp\s*duty)[:\s]+([A-Za-z\s,\-/\d]+?)(?:\n\n|stamp\s*duty|amount|issued)",
    re.I,
)
_ARTICLE_RE    = re.compile(r"(?:article\s*(?:no\.?|number)?)[:\s]+(\d+[A-Z]?)", re.I)
_AMOUNT_RE     = re.compile(
    r"(?:stamp\s*duty\s*amount|stamp\s*duty\s*(?:amount\s*)?paid|amount\s*of\s*stamp\s*duty|"
    r"stamp\s*duty)[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_ISSUE_DATE_RE = re.compile(
    r"(?:issued?\s*(?:on|date)|certificate\s*issued?\s*on|date\s*of\s*issue)"
    r"[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    re.I,
)
_ISSUE_TIME_RE = re.compile(r"(?:time|issued?\s*at)[:\s]*(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)", re.I)
_VENDOR_RE     = re.compile(r"(?:vendor|authorized\s*vendor|issued?\s*(?:through|by))[:\s]+([A-Za-z0-9\s,\.\-&]+?)(?:\n|grn|cert|date)", re.I)
_PROP_DESC_RE  = re.compile(r"(?:property\s*(?:details?|description|address))[:\s]+([A-Za-z0-9\s,/\-\.#]+?)(?:\n\n|\d{6}|purchaser|amount)", re.I)


class EStampCertificateParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "estamp_certificate"}

        cert_m = _CERT_NO_RE.search(text)
        bare_m = _ESTAMP_BARE_RE.search(text)
        if cert_m:
            result["certificate_number"] = cert_m.group(1).strip()
        elif bare_m:
            result["certificate_number"] = bare_m.group(0).strip()

        m = _GRN_RE.search(text)
        if m:
            result["grn_number"] = m.group(1).strip()

        m = _PURCHASER_RE.search(text)
        if m:
            result["purchaser_name"] = m.group(1).strip().title()

        m = _SECOND_PARTY_RE.search(text)
        if m:
            result["second_party_name"] = m.group(1).strip().title()

        m = _DESC_RE.search(text)
        if m:
            result["stamp_description"] = re.sub(r"\s+", " ", m.group(1)).strip().title()

        m = _ARTICLE_RE.search(text)
        if m:
            result["article_number"] = m.group(1).strip()

        m = _AMOUNT_RE.search(text)
        if m:
            result["stamp_duty_amount"] = clean_amount(m.group(1))

        m = _ISSUE_DATE_RE.search(text)
        if m:
            result["issue_date"] = norm_date(m.group(1))

        m = _ISSUE_TIME_RE.search(text)
        if m:
            result["issue_time"] = m.group(1).strip()

        m = _VENDOR_RE.search(text)
        if m:
            result["vendor_name"] = m.group(1).strip().title()

        m = _PROP_DESC_RE.search(text)
        if m:
            result["property_description"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = STATE_RE.search(text)
        if m:
            result["state"] = m.group(1).strip().title()

        result["raw_text"] = text
        return result
