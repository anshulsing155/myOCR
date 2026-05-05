"""Board Marksheet parser — CBSE, ICSE, NIOS, and state board results (Class X / XII)."""
from __future__ import annotations

import re
from typing import Any

from parsers.base_parser import BaseParser

_ROLL_RE      = re.compile(r"(?:roll\s*(?:no\.?|number)|roll)[:\s]+([A-Z0-9]+)", re.I)
_ENROLL_RE    = re.compile(r"(?:enrol{1,2}ment\s*(?:no\.?|number))[:\s]+([A-Z0-9/]+)", re.I)
_SCHOOL_RE    = re.compile(r"(?:school\s*name|name\s*of\s*school|institution)[:\s]+([A-Za-z\s,\.\-&]+?)(?:\n|district|class)", re.I)
_SCHOOL_CODE_RE = re.compile(r"(?:school\s*code|centre\s*(?:no\.?|number))[:\s]+([A-Z0-9]+)", re.I)
_BOARD_RE     = re.compile(
    r"\b(cbse|icse|cisce|nios|ssc|hsc|ignou|"
    r"board\s*of\s*(?:secondary|higher\s*secondary|intermediate)\s*education[A-Za-z\s]*)\b",
    re.I
)
_CLASS_RE     = re.compile(r"(?:class|standard|grade|examination)[:\s]*(x{1,3}|xii|xi|x|10th|12th|11th|9th)", re.I)
_YEAR_RE      = re.compile(r"(?:year\s*of\s*(?:passing|examination)|examination\s*year)[:\s]*(\d{4})", re.I)
_YEAR_BARE_RE = re.compile(r"\b(20\d{2}|19\d{2})\b")
_NAME_LBL_RE  = re.compile(r"(?:name\s*of\s*(?:the\s*)?(?:student|candidate)|candidate[:\s]+|student[:\s]+)([A-Z][A-Za-z\s\.]+?)(?:\n|roll|father|mother|dob|school)", re.I)
_FATHER_RE    = re.compile(r"(?:father'?s?\s*name|father)[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|mother|roll|school|dob)", re.I)
_MOTHER_RE    = re.compile(r"(?:mother'?s?\s*name|mother)[:\s]+([A-Z][A-Za-z\s\.]+?)(?:\n|father|roll|school|dob)", re.I)
_DOB_RE       = re.compile(r"(?:date\s*of\s*birth|dob)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})", re.I)
_PERCENT_RE   = re.compile(r"(?:percentage|percent|overall\s*%)[:\s]*([\d\.]+)\s*%?", re.I)
_CGPA_RE      = re.compile(r"(?:cgpa|gpa|grade\s*point)[:\s]*([\d\.]+)", re.I)
_GRADE_RE     = re.compile(r"(?:overall\s*grade|final\s*grade|result\s*grade)[:\s]*([A-F][+\-]?|[A-Z]{1,2}[1-9]?)", re.I)
_RESULT_RE    = re.compile(r"\b(pass|passed|fail|failed|compartment|withheld|absent)\b", re.I)
_DISTRICT_RE  = re.compile(r"(?:district|dist\.?)[:\s]+([A-Za-z\s]+?)(?:\n|state|pin)", re.I)
_STATE_RE     = re.compile(
    r"\b(andhra\s*pradesh|arunachal\s*pradesh|assam|bihar|chhattisgarh|goa|gujarat|"
    r"haryana|himachal\s*pradesh|jharkhand|karnataka|kerala|madhya\s*pradesh|"
    r"maharashtra|manipur|meghalaya|mizoram|nagaland|odisha|punjab|rajasthan|"
    r"sikkim|tamil\s*nadu|telangana|tripura|uttar\s*pradesh|uttarakhand|west\s*bengal|"
    r"delhi|jammu\s*and\s*kashmir|ladakh)\b",
    re.I
)

# Subject row: subject name | marks obtained | max marks | grade
_SUBJECT_ROW_RE = re.compile(
    r"([A-Za-z\s\(\)/&]{3,35})\s+(\d{1,3}(?:\.\d)?)\s+(\d{1,3})\s+([A-F][+\-]?|[A-Z][1-9]?)",
    re.I
)
_SUBJECT_ROW2_RE = re.compile(
    r"([A-Za-z\s\(\)/&]{3,35})\s+(\d{1,3}(?:\.\d)?)\s*/\s*(\d{1,3})",
    re.I
)

_CLASS_MAP = {"x": "10", "10th": "10", "xii": "12", "12th": "12", "xi": "11"}


def _norm_date(raw: str) -> str:
    raw = raw.strip().replace("-", "/").replace(".", "/")
    parts = raw.split("/")
    if len(parts) == 3:
        d, m, y = parts
        if len(y) == 2:
            y = ("20" if int(y) < 50 else "19") + y
        return f"{d.zfill(2)}/{m.zfill(2)}/{y}"
    return raw


class MarksheetParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        text = "\n".join(r.get("text", "") for r in ocr_results)
        result: dict[str, Any] = {"doc_type": "marksheet"}

        m = _ROLL_RE.search(text)
        if m:
            result["roll_number"] = m.group(1).strip()

        m = _ENROLL_RE.search(text)
        if m:
            result["enrollment_number"] = m.group(1).strip()

        m = _NAME_LBL_RE.search(text)
        if m:
            result["student_name"] = m.group(1).strip().title()

        m = _FATHER_RE.search(text)
        if m:
            result["father_name"] = m.group(1).strip().title()

        m = _MOTHER_RE.search(text)
        if m:
            result["mother_name"] = m.group(1).strip().title()

        m = _DOB_RE.search(text)
        if m:
            result["date_of_birth"] = _norm_date(m.group(1))

        m = _SCHOOL_RE.search(text)
        if m:
            result["school_name"] = m.group(1).strip().title()

        m = _SCHOOL_CODE_RE.search(text)
        if m:
            result["school_code"] = m.group(1).strip()

        m = _BOARD_RE.search(text)
        if m:
            result["board_name"] = m.group(1).strip().upper()

        m = _CLASS_RE.search(text)
        if m:
            raw_class = m.group(1).lower()
            result["class"] = _CLASS_MAP.get(raw_class, raw_class)

        m = _YEAR_RE.search(text)
        if not m:
            m = _YEAR_BARE_RE.search(text)
        if m:
            result["year_of_passing"] = m.group(1)

        m = _PERCENT_RE.search(text)
        if m:
            result["percentage"] = m.group(1)

        m = _CGPA_RE.search(text)
        if m:
            result["cgpa"] = m.group(1)

        m = _GRADE_RE.search(text)
        if m:
            result["overall_grade"] = m.group(1)

        m = _RESULT_RE.search(text)
        if m:
            result["result"] = m.group(1).title()

        m = _DISTRICT_RE.search(text)
        if m:
            result["district"] = m.group(1).strip().title()

        m = _STATE_RE.search(text)
        if m:
            result["state"] = m.group(1).strip().title()

        # Subject-wise marks
        subjects: list[dict] = []
        for sm in _SUBJECT_ROW_RE.finditer(text):
            subj_name = sm.group(1).strip()
            if len(subj_name) < 3 or any(skip in subj_name.lower() for skip in ("total", "grand", "aggregate", "overall")):
                continue
            subjects.append({
                "subject":      subj_name.title(),
                "marks":        sm.group(2),
                "max_marks":    sm.group(3),
                "grade":        sm.group(4),
            })
        if not subjects:
            for sm in _SUBJECT_ROW2_RE.finditer(text):
                subj_name = sm.group(1).strip()
                if len(subj_name) < 3:
                    continue
                subjects.append({
                    "subject":   subj_name.title(),
                    "marks":     sm.group(2),
                    "max_marks": sm.group(3),
                })
        if subjects:
            result["subjects"] = subjects

        result["raw_text"] = text
        return result
