"""Salary slip / payslip parser — extract employee details and complete pay breakdown.

Handles common formats:
  - Label: Value pairs  ("Basic Salary: 25,000")
  - Table rows          ("Basic Salary  |  25,000  |  HRA  |  5,000")
  - Compact lines       ("Basic 25000 HRA 5000 Conveyance 1200")
"""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

# ── Employee details ──────────────────────────────────────────────────────────

_EMP_NAME_RE  = re.compile(
    r"(?:employee|emp\.?)\s*name\s*[:\-]?\s*([A-Za-z][A-Za-z\s\.]{2,50}?)(?:\n|$)",
    re.I | re.MULTILINE)
_EMP_ID_RE    = re.compile(
    r"(?:employee|emp\.?)\s*(?:id|code|no\.?|number)\s*[:\-]?\s*(\w{2,20})", re.I)
_DESIG_RE     = re.compile(
    r"designation\s*[:\-]?\s*([A-Za-z][A-Za-z\s\./\-]{2,50}?)(?:\n|$)",
    re.I | re.MULTILINE)
_DEPT_RE      = re.compile(
    r"department\s*[:\-]?\s*([A-Za-z][A-Za-z\s\./&\-]{2,50}?)(?:\n|$)",
    re.I | re.MULTILINE)
_LOC_RE       = re.compile(
    r"(?:location|branch|office)\s*[:\-]?\s*([A-Za-z][A-Za-z\s\.,]{2,40}?)(?:\n|$)",
    re.I | re.MULTILINE)
_EMPLOYER_RE  = re.compile(
    r"(?:employer|company|organisation|organization|firm)\s*(?:name)?\s*[:\-]?\s*"
    r"([A-Za-z][A-Za-z\s\.,&\(\)]{2,60}?)(?:\n|$)",
    re.I | re.MULTILINE)
_PERIOD_RE    = re.compile(
    r"(?:pay\s*(?:period|month)|for\s*the\s*month(?:\s*of)?|salary\s*(?:month|for)|"
    r"month\s*of|payroll\s*(?:period|month))\s*[:\-]?\s*"
    r"([A-Za-z]+[\s\-]\d{4}|\d{1,2}[/\-]\d{4}|[A-Za-z]+\s+\d{4})",
    re.I)
_WORKING_DAYS_RE = re.compile(
    r"(?:working|paid|present)\s*days?\s*[:\-]?\s*(\d{1,2}(?:\.\d)?)", re.I)
_LEAVES_RE    = re.compile(
    r"(?:leave|absent|loss\s*of\s*pay|lop)\s*(?:days?)?\s*[:\-]?\s*(\d{1,2}(?:\.\d)?)", re.I)

# ── Identity numbers ──────────────────────────────────────────────────────────

_PAN_RE       = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")
_PF_ACC_RE    = re.compile(
    r"(?:pf|provident\s*fund)\s*(?:acc(?:ount)?\.?|no\.?|number)?\s*[:\-]?\s*([\w/\-]{5,30})", re.I)
_UAN_RE       = re.compile(
    r"(?:uan|universal\s*account\s*(?:number|no\.?))\s*[:\-]?\s*(\d{12})", re.I)
_ESIC_RE_NUM  = re.compile(
    r"(?:esic|esi)\s*(?:no\.?|number|code)?\s*[:\-]?\s*(\d{10,17})", re.I)
_BANK_ACC_RE  = re.compile(
    r"(?:bank\s*a(?:/c|ccount)|a/c\s*(?:no\.?|number))\s*[:\-]?\s*(\d{8,18})", re.I)
_BANK_NAME_RE = re.compile(
    r"bank\s*name\s*[:\-]?\s*([A-Za-z][A-Za-z\s\.&]{2,40}?)(?:\n|$)",
    re.I | re.MULTILINE)
_IFSC_RE      = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")

# ── Amount pattern ────────────────────────────────────────────────────────────
# Matches Indian amounts like 25,000 / 25000 / 25,000.00
_AMT = r"([\d,]+(?:\.\d{1,2})?)"


def _amt(pattern: str, flags: int = re.I) -> re.Pattern:
    return re.compile(r"(?:" + pattern + r")\s*[:\-]?\s*" + _AMT, flags)


# ── Earnings ──────────────────────────────────────────────────────────────────

_BASIC_RE      = _amt(r"basic\s*(?:salary|pay)?")
_HRA_RE        = _amt(r"\bhra\b")
_DA_RE         = _amt(r"\bda\b|dearness\s*allowance")
_LTA_RE        = _amt(r"\blta\b|leave\s*travel\s*allow(?:ance)?")
_CONV_RE       = _amt(r"conveyance\s*(?:allow(?:ance)?)?|transport\s*allow(?:ance)?")
_SPECIAL_RE    = _amt(r"special\s*allow(?:ance)?")
_MED_RE        = _amt(r"medical\s*allow(?:ance)?")
_BONUS_RE      = _amt(r"\bbonus\b(?!\s*(?:deduction|recover))")
_OTHER_EARN_RE = _amt(r"other\s*allow(?:ance)?|miscellaneous\s*allow(?:ance)?")
_GROSS_RE      = re.compile(
    r"gross\s*(?:salary|pay|earnings?|ctc)?\s*[:\-]?\s*" + _AMT, re.I)

# ── Deductions ────────────────────────────────────────────────────────────────

_PF_AMT_RE     = _amt(r"(?:employee\s*)?p\.?\s*f\.?|provident\s*fund")
_ESIC_AMT_RE   = _amt(r"\besic\b|\besi\b")
_TDS_RE        = _amt(r"\btds\b|income\s*tax\s*(?:deduction)?")
_PT_RE         = _amt(r"professional\s*tax|\bpt\b")
_ADV_RE        = _amt(r"advance\s*(?:recovery|deduction)?|salary\s*advance")
_LOP_AMT_RE    = _amt(r"loss\s*of\s*pay|lop\s*deduction")
_TOTAL_DED_RE  = re.compile(
    r"total\s*deductions?\s*[:\-]?\s*" + _AMT, re.I)

# ── Net / CTC ────────────────────────────────────────────────────────────────

_NET_RE = re.compile(
    r"net\s*(?:salary|pay|amount\s*payable|take\s*home)\s*[:\-]?\s*" + _AMT, re.I)
_CTC_RE = re.compile(r"(?:annual\s*)?ctc\s*[:\-]?\s*" + _AMT, re.I)


def _ca(v: str | None) -> str | None:
    """Clean amount string: remove commas and extra spaces."""
    if v is None:
        return None
    return v.replace(",", "").strip()


def _first(text: str, *patterns: re.Pattern) -> str | None:
    for p in patterns:
        m = p.search(text)
        if m:
            value = _ca(m.group(1) if m.lastindex else None)
            if value:
                return value
    return None


class SalarySlipParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "salary_slip"}

        # ── Employee info ─────────────────────────────────────────────────────
        m = _EMP_NAME_RE.search(text)
        if m:
            result["employee_name"] = m.group(1).strip()

        m = _EMP_ID_RE.search(text)
        if m:
            result["employee_id"] = m.group(1).strip()

        m = _DESIG_RE.search(text)
        if m:
            result["designation"] = m.group(1).strip()

        m = _DEPT_RE.search(text)
        if m:
            result["department"] = m.group(1).strip()

        m = _LOC_RE.search(text)
        if m:
            result["location"] = m.group(1).strip()

        m = _EMPLOYER_RE.search(text)
        if m:
            result["employer"] = m.group(1).strip()

        m = _PERIOD_RE.search(text)
        if m:
            result["pay_period"] = m.group(1).strip()

        m = _WORKING_DAYS_RE.search(text)
        if m:
            result["working_days"] = m.group(1)

        m = _LEAVES_RE.search(text)
        if m:
            result["leave_days"] = m.group(1)

        # ── Identity numbers ──────────────────────────────────────────────────
        m = _PAN_RE.search(text)
        if m:
            result["pan"] = m.group(1)

        m = _PF_ACC_RE.search(text)
        if m:
            result["pf_account"] = m.group(1).strip()

        m = _UAN_RE.search(text)
        if m:
            result["uan"] = m.group(1)

        m = _ESIC_RE_NUM.search(text)
        if m:
            result["esic_number"] = m.group(1)

        m = _BANK_ACC_RE.search(text)
        if m:
            result["bank_account"] = m.group(1)

        m = _BANK_NAME_RE.search(text)
        if m:
            result["bank_name"] = m.group(1).strip()

        m = _IFSC_RE.search(text)
        if m:
            result["ifsc_code"] = m.group(1)

        # ── Earnings ──────────────────────────────────────────────────────────
        earnings: dict[str, str] = {}
        fields = [
            ("basic",        _BASIC_RE),
            ("hra",          _HRA_RE),
            ("da",           _DA_RE),
            ("lta",          _LTA_RE),
            ("conveyance",   _CONV_RE),
            ("special_allowance", _SPECIAL_RE),
            ("medical_allowance", _MED_RE),
            ("bonus",        _BONUS_RE),
            ("other_allowance", _OTHER_EARN_RE),
        ]
        for key, pat in fields:
            v = _first(text, pat)
            if v:
                earnings[key] = v

        m = _GROSS_RE.search(text)
        if m:
            earnings["gross"] = _ca(m.group(1))
        if earnings:
            result["earnings"] = earnings

        # ── Deductions ────────────────────────────────────────────────────────
        deductions: dict[str, str] = {}
        ded_fields = [
            ("provident_fund", _PF_AMT_RE),
            ("esic",           _ESIC_AMT_RE),
            ("tds",            _TDS_RE),
            ("professional_tax", _PT_RE),
            ("advance_recovery", _ADV_RE),
            ("loss_of_pay",    _LOP_AMT_RE),
        ]
        for key, pat in ded_fields:
            v = _first(text, pat)
            if v:
                deductions[key] = v

        m = _TOTAL_DED_RE.search(text)
        if m:
            deductions["total"] = _ca(m.group(1))
        if deductions:
            result["deductions"] = deductions

        # ── Net / CTC ─────────────────────────────────────────────────────────
        v = _first(text, _NET_RE)
        if v:
            result["net_salary"] = v

        v = _first(text, _CTC_RE)
        if v:
            result["ctc"] = v

        result["raw_text"] = text
        return result
