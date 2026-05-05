"""PPO (Pension Payment Order) parser — central / state government pension."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

# PPO number formats: 12 digits (CPAO/EPFO) or alphanumeric (state govts)
_PPO_RE       = re.compile(r"(?:ppo\s*(?:no\.?|number)|pension\s*payment\s*order\s*(?:no\.?|number))[:\s]+([A-Z0-9/\-]+)", re.I)
_PPO_BARE_RE  = re.compile(r"\bPPO[:\s]+([A-Z0-9/\-]{6,20})\b")
_NAME_LBL_RE  = re.compile(
    r"(?:name\s*of\s*(?:the\s*)?pensioner|pensioner'?s?\s*name|pensioner)[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|designation|department|dob|date\s*of)",
    re.I
)
_DESIGNATION_RE = re.compile(r"(?:designation|post|rank)[:\s]+([A-Za-z\s,\.\-]+?)(?:\n|department|ministry|date|dob)", re.I)
_DEPARTMENT_RE  = re.compile(r"(?:department|ministry|office)[:\s]+([A-Za-z\s,\.\-&]+?)(?:\n|date|dob|desg|pay)", re.I)
_DOB_RE       = re.compile(r"(?:date\s*of\s*birth|dob)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})", re.I)
_RETIRE_DATE_RE = re.compile(r"(?:date\s*of\s*retirement|date\s*of\s*superannuation|retired\s*on)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})", re.I)
_PENSION_RE   = re.compile(
    r"(?:basic\s*pension|monthly\s*pension|pension\s*amount|net\s*pension|gross\s*pension)[:\s]+"
    r"(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I
)
_COMMUTED_RE  = re.compile(r"(?:commuted\s*pension|commuted\s*value)[:\s]+(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_GRATUITY_RE  = re.compile(r"(?:gratuity|death\s*cum\s*retirement\s*gratuity|dcrg)[:\s]+(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_BANK_ACC_RE  = re.compile(r"(?:bank\s*account|account\s*(?:no\.?|number))[:\s]+(\d{8,18})", re.I)
_IFSC_RE      = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")
_BANK_RE      = re.compile(r"(?:bank\s*name|name\s*of\s*bank)[:\s]+([A-Za-z\s&,\.]+?)(?:\n|branch|ifsc|account)", re.I)
_BRANCH_RE    = re.compile(r"(?:branch\s*(?:name|address)?)[:\s]+([A-Za-z\s,\.]+?)(?:\n|ifsc|account|\d{6})", re.I)
_FAMILY_RE    = re.compile(r"(?:family\s*pension|family\s*pensioner)[:\s]+([A-Za-z\s\.]+?)(?:\n|amount|date|rs\.?)", re.I)
_PAN_RE       = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")
_TYPE_RE      = re.compile(
    r"(?:type\s*of\s*pension)[:\s]+(superannuation|voluntary|invalid|family|compulsory|"
    r"compassionate|ews|ex[\s\-]gratia)",
    re.I
)


def _norm_date(raw: str) -> str:
    raw = raw.strip().replace("-", "/").replace(".", "/")
    parts = raw.split("/")
    if len(parts) == 3:
        d, m, y = parts
        if len(y) == 2:
            y = ("20" if int(y) < 50 else "19") + y
        return f"{d.zfill(2)}/{m.zfill(2)}/{y}"
    return raw


def _clean_amount(raw: str) -> str:
    return raw.strip().replace(",", "")


class PpoParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "ppo"}

        m = _PPO_RE.search(text) or _PPO_BARE_RE.search(text)
        if m:
            result["ppo_number"] = m.group(1).strip()

        m = _NAME_LBL_RE.search(text)
        if m:
            result["pensioner_name"] = m.group(1).strip().title()

        m = _DESIGNATION_RE.search(text)
        if m:
            result["designation"] = m.group(1).strip().title()

        m = _DEPARTMENT_RE.search(text)
        if m:
            result["department"] = m.group(1).strip().title()

        m = _TYPE_RE.search(text)
        if m:
            result["pension_type"] = m.group(1).strip().title()

        m = _DOB_RE.search(text)
        if m:
            result["date_of_birth"] = _norm_date(m.group(1))

        m = _RETIRE_DATE_RE.search(text)
        if m:
            result["date_of_retirement"] = _norm_date(m.group(1))

        m = _PENSION_RE.search(text)
        if m:
            result["monthly_pension"] = _clean_amount(m.group(1))

        m = _COMMUTED_RE.search(text)
        if m:
            result["commuted_pension"] = _clean_amount(m.group(1))

        m = _GRATUITY_RE.search(text)
        if m:
            result["gratuity"] = _clean_amount(m.group(1))

        m = _BANK_ACC_RE.search(text)
        if m:
            result["bank_account"] = m.group(1).strip()

        m = _IFSC_RE.search(text)
        if m:
            result["ifsc_code"] = m.group(1)

        m = _BANK_RE.search(text)
        if m:
            result["bank_name"] = m.group(1).strip().title()

        m = _BRANCH_RE.search(text)
        if m:
            result["branch"] = m.group(1).strip().title()

        m = _FAMILY_RE.search(text)
        if m:
            result["family_pensioner"] = m.group(1).strip().title()

        m = _PAN_RE.search(text)
        if m:
            result["pan_number"] = m.group(1)

        result["raw_text"] = text
        return result
