"""Smoke tests for all Indian document parsers."""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _ocr(text: str) -> list[dict]:
    return [{"text": line, "confidence": 1.0, "bbox": [0, 0, 100, 20]}
            for line in text.strip().splitlines() if line.strip()]


# ── Identity documents ────────────────────────────────────────────────────────

def test_pan_parser():
    from parsers.pan_parser import PanParser
    ocr = _ocr("PERMANENT ACCOUNT NUMBER\nINCOME TAX DEPARTMENT\nABCDE1234F\nRAHUL SHARMA\nRAJESH SHARMA\nDOB 01/01/1990")
    result = PanParser().parse(ocr)
    assert result["doc_type"] == "pan_card"
    assert result.get("pan_number") == "ABCDE1234F"


def test_aadhaar_parser():
    from parsers.aadhaar_parser import AadhaarParser
    ocr = _ocr("AADHAAR\nGovernment of India\nRAHUL KUMAR\nDOB: 01/01/1990\nMale\n2345 6789 0123\nAddress: 123 Main Street Delhi 110001")
    result = AadhaarParser().parse(ocr)
    assert result["doc_type"] == "aadhaar"
    assert result.get("aadhaar_number") is not None


def test_voter_id_parser():
    from parsers.voter_id_parser import VoterIdParser
    ocr = _ocr("ELECTION COMMISSION OF INDIA\nElectors Photo Identity Card\nEPIC No: ABC1234567\nRAHUL KUMAR\nS/O RAJESH KUMAR\nMale\nPart No: 42\nDelhi 110001")
    result = VoterIdParser().parse(ocr)
    assert result["doc_type"] == "voter_id"
    assert result.get("epic_number") == "ABC1234567"


def test_passport_parser():
    from parsers.passport_parser import PassportParser
    ocr = _ocr("REPUBLIC OF INDIA\nPASSPORT\nPassport No: A1234567\nSurname: SHARMA\nGiven Name: RAHUL\nNationality: INDIAN\nDate of Birth: 01/01/1990\nSex: M\nDate of Issue: 01/01/2020\nDate of Expiry: 31/12/2030\nPlace of Issue: Delhi")
    result = PassportParser().parse(ocr)
    assert result["doc_type"] == "passport"
    assert result.get("passport_number") == "A1234567"


def test_driving_license_parser():
    from parsers.driving_license_parser import DrivingLicenseParser
    ocr = _ocr("DRIVING LICENCE\nINDIAN UNION\nDL No: DL0120100123456\nRAHUL KUMAR\nS/O RAJESH KUMAR\nBlood Group: B+\nLMV MCWG")
    result = DrivingLicenseParser().parse(ocr)
    assert result["doc_type"] == "driving_license"


# ── Financial documents ───────────────────────────────────────────────────────

def test_itr_parser():
    from parsers.itr_parser import ItrParser
    ocr = _ocr("INCOME TAX RETURN\nITR-1\nAssessment Year: 2024-25\nAcknowledgement Number: 123456789012345\nPAN: ABCDE1234F\nTotal Income: 500000\nTax Payable: 12500")
    result = ItrParser().parse(ocr)
    assert result["doc_type"] == "itr"


def test_salary_slip_parser():
    from parsers.salary_slip_parser import SalarySlipParser
    ocr = _ocr("SALARY SLIP\nEmployee Name: Rahul Kumar\nEmployee ID: EMP001\nDesignation: Engineer\nPay Period: January 2025\nBasic Salary: 30000\nHRA: 12000\nGross Salary: 50000\nProvident Fund: 3600\nNet Salary: 42000")
    result = SalarySlipParser().parse(ocr)
    assert result["doc_type"] == "salary_slip"


def test_salary_slip_parser_tolerates_incomplete_amount_labels():
    from parsers.salary_slip_parser import SalarySlipParser
    ocr = _ocr(
        "SALARY SLIP\n"
        "Employee Name: Rahul Kumar\n"
        "DA\n"
        "Provident Fund\n"
        "Net Salary: 42000"
    )
    result = SalarySlipParser().parse(ocr)
    assert result["doc_type"] == "salary_slip"
    assert result.get("net_salary") == "42000"


def test_gst_certificate_parser():
    from parsers.gst_certificate_parser import GstCertificateParser
    ocr = _ocr("GST Registration Certificate\nGoods and Services Tax\nGSTIN: 07ABCDE1234F1Z5\nLegal Name of Business: ABC Traders\nTrade Name: ABC\nConstitution of Business: Proprietorship\nDate of Registration: 01/07/2017\nStatus: Active")
    result = GstCertificateParser().parse(ocr)
    assert result["doc_type"] == "gst_certificate"
    assert result.get("gstin") == "07ABCDE1234F1Z5"


def test_ppo_parser():
    from parsers.ppo_parser import PpoParser
    ocr = _ocr("PENSION PAYMENT ORDER\nPPO No: 12345678901234\nName of Pensioner: RAJESH KUMAR\nDesignation: Assistant Director\nDate of Retirement: 31/03/2020\nMonthly Pension: 45000\nBank Account: 12345678901234\nIFSC: SBIN0001234")
    result = PpoParser().parse(ocr)
    assert result["doc_type"] == "ppo"
    assert result.get("ppo_number") is not None


# ── Certificate documents ─────────────────────────────────────────────────────

def test_birth_certificate_parser():
    from parsers.birth_certificate_parser import BirthCertificateParser
    ocr = _ocr("BIRTH CERTIFICATE\nCertificate No: BC/2025/12345\nChild's Name: RAHUL KUMAR\nDate of Birth: 15/06/2000\nSex: Male\nFather's Name: RAJESH KUMAR\nMother's Name: SUNITA DEVI\nPlace of Birth: AIIMS Delhi\nDistrict: New Delhi\nState: Delhi")
    result = BirthCertificateParser().parse(ocr)
    assert result["doc_type"] == "birth_certificate"
    assert result.get("certificate_number") == "BC/2025/12345"


def test_marriage_certificate_parser():
    from parsers.marriage_certificate_parser import MarriageCertificateParser
    ocr = _ocr("MARRIAGE CERTIFICATE\nCertificate No: MC/2023/456\nGroom's Name: RAHUL KUMAR\nBride's Name: PRIYA SHARMA\nDate of Marriage: 15/02/2023\nPlace of Marriage: New Delhi\nDistrict: New Delhi\nState: Delhi")
    result = MarriageCertificateParser().parse(ocr)
    assert result["doc_type"] == "marriage_certificate"
    assert result.get("husband_name") is not None


def test_caste_certificate_parser():
    from parsers.caste_certificate_parser import CasteCertificateParser
    ocr = _ocr("CASTE CERTIFICATE\nThis is to certify that Rahul Kumar S/O Rajesh Kumar\nbelongs to Scheduled Caste (SC) category\nIssue Date: 01/01/2024\nDistrict: New Delhi\nState: Delhi\nIssued By: Tehsildar North")
    result = CasteCertificateParser().parse(ocr)
    assert result["doc_type"] == "caste_certificate"
    assert result.get("category") == "SC"


def test_income_certificate_parser():
    from parsers.income_certificate_parser import IncomeCertificateParser
    ocr = _ocr("INCOME CERTIFICATE\nThis certifies that Rahul Kumar S/O Rajesh Kumar\nAnnual Income: Rs. 2,50,000 per annum\nDate of Issue: 01/01/2024\nDistrict: New Delhi\nState: Delhi\nIssued By: Tehsildar")
    result = IncomeCertificateParser().parse(ocr)
    assert result["doc_type"] == "income_certificate"
    assert result.get("annual_income") is not None


def test_domicile_certificate_parser():
    from parsers.domicile_certificate_parser import DomicileCertificateParser
    ocr = _ocr("DOMICILE CERTIFICATE\nThis certifies that Rahul Kumar S/O Rajesh Kumar\nPermanent Resident of Delhi\nAddress: 123 Main Street, Delhi\nDate of Issue: 01/01/2024\nDistrict: New Delhi\nState: Delhi")
    result = DomicileCertificateParser().parse(ocr)
    assert result["doc_type"] == "domicile_certificate"


def test_ration_card_parser():
    from parsers.ration_card_parser import RationCardParser
    ocr = _ocr("RATION CARD\nPublic Distribution System\nCard Number: DL/APL/2024/12345\nCard Type: APL\nHead of Family: RAJESH KUMAR\nFair Price Shop: FPS/123\nIssue Date: 01/01/2020\nAddress: 123 Main Street, Delhi 110001\nState: Delhi")
    result = RationCardParser().parse(ocr)
    assert result["doc_type"] == "ration_card"
    assert result.get("card_type") == "APL"


# ── Educational documents ─────────────────────────────────────────────────────

def test_marksheet_parser():
    from parsers.marksheet_parser import MarksheetParser
    ocr = _ocr("MARK SHEET\nCBSE\nClass X\nRoll Number: 1234567\nStudent Name: RAHUL KUMAR\nFather's Name: RAJESH KUMAR\nYear of Passing: 2020\nMathematics 95 100 A1\nScience 88 100 A2\nEnglish 82 100 B1\nPercentage: 88.5%\nResult: Pass")
    result = MarksheetParser().parse(ocr)
    assert result["doc_type"] == "marksheet"
    assert result.get("board_name") == "CBSE"


def test_degree_certificate_parser():
    from parsers.degree_certificate_parser import DegreeCertificateParser
    ocr = _ocr("DEGREE CERTIFICATE\nThis is to certify that RAHUL KUMAR\nhas been awarded the degree of Bachelor of Technology\nin the branch of Computer Science\nfrom Delhi Technological University\nYear of Passing: 2022\nClass: First Class\nCGPA: 8.5")
    result = DegreeCertificateParser().parse(ocr)
    assert result["doc_type"] == "degree_certificate"
    assert result.get("degree_name") is not None


# ── Health / Social documents ─────────────────────────────────────────────────

def test_ayushman_card_parser():
    from parsers.ayushman_card_parser import AyushmanCardParser
    ocr = _ocr("AYUSHMAN BHARAT\nPM-JAY\nPradhan Mantri Jan Arogya Yojana\nBeneficiary Name: RAHUL KUMAR\nFamily ID: AB/DL/123456\nAge: 35\nGender: Male\nState: Delhi\nValid Till: 31/12/2025")
    result = AyushmanCardParser().parse(ocr)
    assert result["doc_type"] == "ayushman_card"
    assert result.get("beneficiary_name") is not None


# ── Vehicle documents ─────────────────────────────────────────────────────────

def test_vehicle_rc_parser():
    from parsers.vehicle_rc_parser import VehicleRcParser
    ocr = _ocr("Registration Certificate\nMotor Vehicles Act\nReg. No: DL01AB1234\nOwner's Name: RAJESH KUMAR\nChassis No: MA3EURB1S00123456\nEngine No: K12MN1234567\nFuel Type: Petrol\nVehicle Class: Motor Car\nSeating Capacity: 5\nInsurance Validity: 31/12/2025")
    result = VehicleRcParser().parse(ocr)
    assert result["doc_type"] == "vehicle_rc"
    assert result.get("registration_number") is not None


# ── Classifier integration ────────────────────────────────────────────────────

def test_classifier_voter_id():
    from classification.doc_classifier import classify_text
    dc = classify_text("ELECTION COMMISSION OF INDIA Electors Photo Identity Card EPIC No ABC1234567")
    assert dc.type == "voter_id"


def test_classifier_passport():
    from classification.doc_classifier import classify_text
    dc = classify_text("REPUBLIC OF INDIA PASSPORT Date of Expiry 31/12/2030 Ministry of External Affairs")
    assert dc.type == "passport"


def test_classifier_gst():
    from classification.doc_classifier import classify_text
    dc = classify_text("GST Registration Certificate Goods and Services Tax GSTIN 07ABCDE1234F1Z5 Legal Name of Business")
    assert dc.type == "gst_certificate"


def test_classifier_ayushman():
    from classification.doc_classifier import classify_text
    dc = classify_text("AYUSHMAN BHARAT PMJAY Pradhan Mantri Jan Arogya Yojana Beneficiary Name")
    assert dc.type == "ayushman_card"


def test_classifier_ppo():
    from classification.doc_classifier import classify_text
    dc = classify_text("PENSION PAYMENT ORDER PPO No 1234567 Pensioner Name Date of Retirement Monthly Pension CPAO")
    assert dc.type == "ppo"
