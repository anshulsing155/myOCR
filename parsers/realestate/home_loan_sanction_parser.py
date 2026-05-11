"""Home Loan / Property Loan Sanction Letter parser."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser
from parsers.realestate._helpers import (
    DISTRICT_RE,
    IFSC_RE,
    PIN_RE,
    STATE_RE,
    clean_amount,
    norm_date,
    parse_area,
)

_LOAN_ACC_RE   = re.compile(r"(?:loan\s*account\s*(?:no\.?|number)|account\s*(?:no\.?|number)|loan\s*(?:no\.?|number|id))[:\s]+([A-Z0-9/\-]+)", re.I)
_APPLICANT_RE  = re.compile(
    r"(?:applicant(?:'s)?\s*name|borrower(?:'s)?\s*name|name\s*of\s*(?:the\s*)?(?:applicant|borrower)|dear)"
    r"[:\s]+(?:mr\.?|ms\.?|mrs\.?|shri|smt\.?)?\s*([A-Z][A-Za-z\s\.]+?)(?:\n|co[\s\-]applicant|address|property|loan|dear)",
    re.I,
)
_CO_APPL_RE    = re.compile(
    r"(?:co[\s\-]applicant(?:'s)?\s*name|co[\s\-]borrower(?:'s)?\s*name)"
    r"[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|address|property|loan)",
    re.I,
)
_PROP_ADDR_RE  = re.compile(
    r"(?:property\s*(?:address|details?|described)|collateral\s*(?:property|security))"
    r"[:\s]+([A-Za-z0-9\s,/\-\.#]+?)(?:\n\n|district|state|\d{6}|loan|emi|tenure)",
    re.I,
)
_LOAN_AMT_RE   = re.compile(
    r"(?:sanctioned\s*(?:loan\s*)?amount|loan\s*amount\s*(?:sanctioned|approved)|"
    r"amount\s*(?:sanctioned|approved)|loan\s*amount)"
    r"[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_ROI_RE        = re.compile(r"(?:rate\s*of\s*interest|interest\s*rate|roi|applicable\s*rate)[:\s]*([\d\.]+)\s*%(?:\s*(?:p\.?a\.?|per\s*annum))?", re.I)
_LOAN_TYPE_RE  = re.compile(r"(?:type\s*of\s*(?:loan|interest)|interest\s*type)[:\s]+(fixed|floating|hybrid|semi[\s\-]?fixed)", re.I)
_TENURE_RE     = re.compile(r"(?:loan\s*tenure|repayment\s*period|tenure|repayment\s*in)[:\s]+(\d+)\s*(months?|years?)", re.I)
_EMI_RE        = re.compile(r"(?:emi|monthly\s*instalment|equated\s*monthly)[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_PRE_EMI_RE    = re.compile(r"(?:pre[\s\-]?emi|pre[\s\-]emi\s*(?:amount|interest))[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_PROCESSING_RE = re.compile(r"(?:processing\s*fee|processing\s*charges?)[:\s]*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_SANCTION_DATE_RE = re.compile(r"(?:sanction\s*date|date\s*of\s*sanction|sanctioned?\s*on)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})", re.I)
_VALIDITY_RE   = re.compile(r"(?:validity\s*(?:of\s*sanction|date|period)|valid\s*(?:till|upto|until))[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d+\s*(?:months?|days?))", re.I)
_BANK_RE       = re.compile(r"((?:hdfc|sbi|icici|axis|kotak|pnb|bob|canara|idbi|lic|bajaj|indiabulls|tata\s*capital|l&t\s*finance|pnb\s*housing|lic\s*housing)[A-Za-z\s]*(?:bank|finance|limited|ltd\.?|housing)?)", re.I)
_BRANCH_RE     = re.compile(r"(?:branch\s*(?:name|address)?|issuing\s*branch)[:\s]+([A-Za-z\s,\.]+?)(?:\n|ifsc|loan|sanction|property)", re.I)
_BANK_ACC_RE   = re.compile(r"(?:disbursement\s*account|credit\s*account)[:\s]+(\d{8,18})", re.I)
_CONDITIONS_RE = re.compile(r"(?:terms?\s*(?:and\s*)?conditions?|special\s*conditions?)[:\s]*\n+((?:[^\n]+\n){1,10})", re.I)


class HomeLoanSanctionParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "home_loan_sanction"}

        m = _LOAN_ACC_RE.search(text)
        if m:
            result["loan_account_number"] = m.group(1).strip()

        m = _APPLICANT_RE.search(text)
        if m:
            result["applicant_name"] = m.group(1).strip().title()

        m = _CO_APPL_RE.search(text)
        if m:
            result["co_applicant_name"] = m.group(1).strip().title()

        m = _PROP_ADDR_RE.search(text)
        if m:
            result["property_address"] = re.sub(r"\s+", " ", m.group(1)).strip()

        m = _LOAN_AMT_RE.search(text)
        if m:
            result["loan_amount"] = clean_amount(m.group(1))

        m = _ROI_RE.search(text)
        if m:
            result["interest_rate"] = m.group(1)

        m = _LOAN_TYPE_RE.search(text)
        if m:
            result["loan_type"] = m.group(1).strip().title()

        m = _TENURE_RE.search(text)
        if m:
            result["tenure"] = f"{m.group(1)} {m.group(2)}"

        m = _EMI_RE.search(text)
        if m:
            result["emi_amount"] = clean_amount(m.group(1))

        m = _PRE_EMI_RE.search(text)
        if m:
            result["pre_emi_amount"] = clean_amount(m.group(1))

        m = _PROCESSING_RE.search(text)
        if m:
            result["processing_fee"] = clean_amount(m.group(1))

        m = _SANCTION_DATE_RE.search(text)
        if m:
            result["sanction_date"] = norm_date(m.group(1))

        m = _VALIDITY_RE.search(text)
        if m:
            result["validity"] = m.group(1).strip()

        m = _BANK_RE.search(text)
        if m:
            result["bank_name"] = m.group(1).strip().title()

        m = _BRANCH_RE.search(text)
        if m:
            result["branch_name"] = m.group(1).strip().title()

        m = _BANK_ACC_RE.search(text)
        if m:
            result["disbursement_account"] = m.group(1)

        m = IFSC_RE.search(text)
        if m:
            result["ifsc_code"] = m.group(1)

        area = parse_area(text)
        if area:
            result["property_area"] = area

        m = _CONDITIONS_RE.search(text)
        if m:
            result["key_conditions"] = re.sub(r"\s+", " ", m.group(1)).strip()[:400]

        m = DISTRICT_RE.search(text)
        if m:
            result["district"] = m.group(1).strip().title()

        m = STATE_RE.search(text)
        if m:
            result["state"] = m.group(1).strip().title()

        m = PIN_RE.search(text)
        if m:
            result["pin_code"] = m.group(1)

        result["raw_text"] = text
        return result
