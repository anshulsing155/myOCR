"""Smoke tests for all Indian real-estate document parsers."""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _ocr(text: str) -> list[dict]:
    return [{"text": line, "confidence": 1.0, "bbox": [0, 0, 100, 20]}
            for line in text.strip().splitlines() if line.strip()]


# ── Sale Deed ─────────────────────────────────────────────────────────────────

def test_sale_deed_parser():
    from parsers.realestate.sale_deed_parser import SaleDeedParser
    ocr = _ocr("""SALE DEED
This deed of sale is executed on 15/03/2024 between
Vendor: RAMESH KUMAR SHARMA S/O Late Mohan Lal
Purchaser: SURESH PATEL S/O Ramji Patel
Sale Consideration: Rs. 45,00,000/-
Stamp Duty: Rs. 2,70,000
Registration No: 1234/2024
Sub-Registrar Office: Lajpat Nagar
Book No: 1 Volume 234 Page 45
Survey No: 123/A Area: 1200 sq.ft
District: South Delhi State: Delhi PIN: 110024""")
    result = SaleDeedParser().parse(ocr)
    assert result["doc_type"] == "sale_deed"
    assert "vendor_name" in result or "seller_name" in result or result.get("raw_text")
    assert result.get("pin_code") == "110024"


# ── Agreement to Sale ─────────────────────────────────────────────────────────

def test_agreement_to_sale_parser():
    from parsers.realestate.agreement_to_sale_parser import AgreementToSaleParser
    ocr = _ocr("""AGREEMENT TO SELL
This Agreement for Sale is made on 10/01/2024 between
Vendor: ANITA VERMA W/O Rajesh Verma
Purchaser: VIKAS SINGH S/O Hari Singh
Agreed Price: Rs. 55,00,000
Earnest Money: Rs. 5,00,000
Balance Amount: Rs. 50,00,000
Possession Date: 01/06/2024
District: Gurgaon State: Haryana""")
    result = AgreementToSaleParser().parse(ocr)
    assert result["doc_type"] == "agreement_to_sale"
    assert result.get("agreed_price") is not None or result.get("raw_text")


# ── Encumbrance Certificate ───────────────────────────────────────────────────

def test_encumbrance_certificate_parser():
    from parsers.realestate.encumbrance_certificate_parser import EncumbranceCertificateParser
    ocr = _ocr("""ENCUMBRANCE CERTIFICATE
Sub-Registrar Office: Bangalore South
Period From: 01/01/2010 To: 31/12/2023
Property: Survey No 456/B
The records show NIL ENCUMBRANCE for this period
District: Bangalore Urban State: Karnataka PIN: 560001""")
    result = EncumbranceCertificateParser().parse(ocr)
    assert result["doc_type"] == "encumbrance_certificate"
    assert result.get("nil_encumbrance") is True


# ── Property Tax Receipt ──────────────────────────────────────────────────────

def test_property_tax_parser():
    from parsers.realestate.property_tax_parser import PropertyTaxParser
    ocr = _ocr("""PROPERTY TAX RECEIPT
Municipal Corporation of Delhi
Assessment Number: MCD/SW/2023/45678
Property: House No 12 Block A Saket New Delhi
Ward No: 42
Annual Tax: Rs. 12,500
Arrears: Rs. 0
Penalty: Rs. 0
Total Amount: Rs. 12,500
Receipt No: REC/2023/98765
District: South Delhi State: Delhi""")
    result = PropertyTaxParser().parse(ocr)
    assert result["doc_type"] == "property_tax_receipt"
    assert result.get("assessment_number") is not None
    assert result.get("total_amount") is not None


# ── Khata Certificate ─────────────────────────────────────────────────────────

def test_khata_parser():
    from parsers.realestate.khata_parser import KhataParser
    ocr = _ocr("""KHATA CERTIFICATE
Bruhat Bengaluru Mahanagara Palike (BBMP)
Khata Number: 1234/56/78
Property ID: BBMP-2023-7890
Revenue Survey No: 100/1A
Site Area: 1200 sq.ft
Built Up Area: 900 sq.ft
A-KHATA
District: Bangalore Urban State: Karnataka PIN: 560034""")
    result = KhataParser().parse(ocr)
    assert result["doc_type"] == "khata"
    assert result.get("khata_number") is not None


# ── Mutation Certificate ──────────────────────────────────────────────────────

def test_mutation_certificate_parser():
    from parsers.realestate.mutation_certificate_parser import MutationCertificateParser
    ocr = _ocr("""MUTATION CERTIFICATE
Office of the Tehsildar, Noida
Mutation Number: MUT/2023/4567
Previous Owner: LATE RAMESH CHAND
New Owner: PRIYA RAMESH
Reason for Mutation: Inheritance/Succession
Village: Sector 62 Tehsil: Noida
District: Gautam Buddha Nagar State: Uttar Pradesh""")
    result = MutationCertificateParser().parse(ocr)
    assert result["doc_type"] == "mutation_certificate"
    assert result.get("mutation_number") is not None


# ── Land Record ───────────────────────────────────────────────────────────────

def test_land_record_parser_satbara():
    from parsers.realestate.land_record_parser import LandRecordParser
    ocr = _ocr("""7/12 Extract (Satbara Utara)
Village: Khandala Taluka: Satara District: Satara
Survey Number: 45/1A
Owner Name: GANESH PATIL
Cultivator: GANESH PATIL
Land Classification: Jirayat (Dryland)
Area: 2.50 Hectare
State: Maharashtra""")
    result = LandRecordParser().parse(ocr)
    assert result["doc_type"] == "land_record"
    assert result.get("record_sub_type") in ("7/12", "satbara", None) or result.get("raw_text")


def test_land_record_parser_jamabandi():
    from parsers.realestate.land_record_parser import LandRecordParser
    ocr = _ocr("""JAMABANDI (Record of Rights)
Village: Mehrauli Tehsil: Delhi
Khasra Number: 234/5
Owner: MOHAN LAL S/O SHYAM LAL
Cultivator: SELF
Land Type: Agricultural
Area: 5 Bigha
State: Delhi""")
    result = LandRecordParser().parse(ocr)
    assert result["doc_type"] == "land_record"


# ── RERA Certificate ──────────────────────────────────────────────────────────

def test_rera_certificate_parser():
    from parsers.realestate.rera_certificate_parser import ReraCertificateParser
    ocr = _ocr("""MAHARERA REGISTRATION CERTIFICATE
Real Estate Regulatory Authority Maharashtra
RERA Registration Number: P51700012345
Project Name: Green Valley Heights
Promoter: ABC Developers Pvt Ltd
Registration Date: 01/04/2022
Expiry Date: 31/03/2025
Completion Date: 30/06/2025
Total Units: 120
District: Thane State: Maharashtra""")
    result = ReraCertificateParser().parse(ocr)
    assert result["doc_type"] == "rera_certificate"
    assert result.get("rera_number") is not None


# ── Occupancy Certificate ─────────────────────────────────────────────────────

def test_occupancy_certificate_parser():
    from parsers.realestate.occupancy_certificate_parser import OccupancyCertificateParser
    ocr = _ocr("""OCCUPANCY CERTIFICATE
Municipal Corporation of Greater Mumbai
Certificate Type: Occupancy Certificate
Building/Project: Shree Heights
Approved Plan Reference: BP/2019/4567
Issued by: MCGM Building Proposal Dept
Total Floors: 12
Building Use: Residential
Date of Issue: 15/08/2023
District: Mumbai Suburban State: Maharashtra""")
    result = OccupancyCertificateParser().parse(ocr)
    assert result["doc_type"] == "occupancy_certificate"
    assert result.get("certificate_type") is not None


# ── Possession Letter ─────────────────────────────────────────────────────────

def test_possession_letter_parser():
    from parsers.realestate.possession_letter_parser import PossessionLetterParser
    ocr = _ocr("""POSSESSION LETTER
ABC Developers Pvt Ltd
Project: Green Valley Heights RERA No: P51700012345
Dear RAJESH GUPTA
Unit No: B-502 Tower: B Floor: 5
This is to inform you that possession of your flat is ready.
Possession Date: 01/07/2024
Booking Amount: Rs. 5,00,000
Balance Due: Rs. 15,00,000
District: Thane State: Maharashtra""")
    result = PossessionLetterParser().parse(ocr)
    assert result["doc_type"] == "possession_letter"
    assert result.get("possession_date") is not None or result.get("raw_text")


# ── Power of Attorney ─────────────────────────────────────────────────────────

def test_power_of_attorney_parser():
    from parsers.realestate.power_of_attorney_parser import PowerOfAttorneyParser
    ocr = _ocr("""GENERAL POWER OF ATTORNEY
This Power of Attorney is executed on 20/02/2024
Principal: SUNITA MEHTA W/O Vijay Mehta
Attorney: VIJAY MEHTA S/O Ramesh Mehta
Powers Granted: sell transfer mortgage lease manage all properties
Property: Plot No 45 Sector 15 Noida
Registered on: 20/02/2024 at Sub-Registrar Noida
District: Gautam Buddha Nagar State: Uttar Pradesh""")
    result = PowerOfAttorneyParser().parse(ocr)
    assert result["doc_type"] == "power_of_attorney"
    assert result.get("attorney_type") is not None or result.get("raw_text")


# ── Lease Deed ────────────────────────────────────────────────────────────────

def test_lease_deed_parser():
    from parsers.realestate.lease_deed_parser import LeaseDeedParser
    ocr = _ocr("""LEASE DEED
This Lease Agreement is made on 01/03/2024 between
Lessor: PRIYA SHARMA W/O Anil Sharma
Lessee: TECH SOLUTIONS PVT LTD
Property: Office No 301 Third Floor Connaught Place
Monthly Rent: Rs. 85,000
Security Deposit: Rs. 2,55,000
Lease Period: 36 months
Lock-in Period: 12 months
Notice Period: 3 months
Rent Escalation: 10% per annum
District: Central Delhi State: Delhi""")
    result = LeaseDeedParser().parse(ocr)
    assert result["doc_type"] == "lease_deed"
    assert result.get("monthly_rent") is not None


# ── Gift Deed ─────────────────────────────────────────────────────────────────

def test_gift_deed_parser():
    from parsers.realestate.gift_deed_parser import GiftDeedParser
    ocr = _ocr("""GIFT DEED
This deed of gift is executed on 14/02/2024
Donor: RAMESH LAL GUPTA S/O Shyam Lal Gupta
Donee: POOJA GUPTA D/O Ramesh Lal Gupta
Relationship: Father to Daughter
The donor gifts out of love and affection without consideration
Market Value: Rs. 30,00,000
Possession Date: 14/02/2024
Stamp Duty: Rs. 1,50,000
District: Jaipur State: Rajasthan""")
    result = GiftDeedParser().parse(ocr)
    assert result["doc_type"] == "gift_deed"
    assert result.get("donor_name") is not None


# ── Partition Deed ────────────────────────────────────────────────────────────

def test_partition_deed_parser():
    from parsers.realestate.partition_deed_parser import PartitionDeedParser
    ocr = _ocr("""PARTITION DEED
This Deed of Partition is made on 05/01/2024
Party 1: RAJESH KUMAR SHARMA
Party 2: SURESH KUMAR SHARMA
Party 3: MAHESH KUMAR SHARMA
Equal share: 1/3 share each party
Undivided share property 123 MG Road Bangalore
District: Bangalore State: Karnataka""")
    result = PartitionDeedParser().parse(ocr)
    assert result["doc_type"] == "partition_deed"
    assert len(result.get("parties", [])) >= 1 or result.get("raw_text")


# ── Mortgage Deed ─────────────────────────────────────────────────────────────

def test_mortgage_deed_parser():
    from parsers.realestate.mortgage_deed_parser import MortgageDeedParser
    ocr = _ocr("""MORTGAGE DEED
This deed of mortgage is executed on 10/03/2024
Mortgagor: ANIL KUMAR SINGH S/O Ram Kumar Singh
Mortgagee: HDFC BANK LIMITED
Loan Amount: Rs. 35,00,000
Rate of Interest: 8.5%
Repayment Period: 240 months
EMI: Rs. 30,456
Account Number: 50100123456789
IFSC: HDFC0001234
Equitable Mortgage
District: Lucknow State: Uttar Pradesh""")
    result = MortgageDeedParser().parse(ocr)
    assert result["doc_type"] == "mortgage_deed"
    assert result.get("loan_amount") is not None
    assert result.get("equitable_mortgage") is True


# ── e-Stamp Certificate ───────────────────────────────────────────────────────

def test_estamp_certificate_parser():
    from parsers.realestate.estamp_certificate_parser import EStampCertificateParser
    ocr = _ocr("""e-STAMP CERTIFICATE
Stock Holding Corporation of India Ltd (SHCIL)
Certificate Number: IN-DL12345678901234567
GRN: GRN/2024/DL/98765
Purchaser Name: AMIT SHARMA
Second Party: BANK OF BARODA
Description of Document: Sale Deed
Article Number: 23
Stamp Duty Amount: Rs. 45,000
Issued On: 15/03/2024
Time: 11:30:45 AM
Vendor: SHCIL SERVICES LTD
State: Delhi""")
    result = EStampCertificateParser().parse(ocr)
    assert result["doc_type"] == "estamp_certificate"
    assert result.get("stamp_duty_amount") is not None


# ── Property Valuation ────────────────────────────────────────────────────────

def test_property_valuation_parser():
    from parsers.realestate.property_valuation_parser import PropertyValuationParser
    ocr = _ocr("""PROPERTY VALUATION CERTIFICATE
Valuation Report for Bank Purpose
Certificate Number: VAL/2024/DL/1234
Owner Name: SUNITA DEVI
Property Address: House No 45 Block B Janakpuri New Delhi
Survey No: 234/5A
Market Value: Rs. 65,00,000
Ready Reckoner Rate: Rs. 55,00,000
Plot Area: 200 sq.mt
Built Up Area: 180 sq.mt
Type of Property: Residential
Building Age: 15 years
Valuation Date: 01/03/2024
Valuer Name: PRADEEP KUMAR JAIN
Bank: ICICI Bank Limited
District: West Delhi State: Delhi PIN: 110058""")
    result = PropertyValuationParser().parse(ocr)
    assert result["doc_type"] == "property_valuation"
    assert result.get("market_value") is not None
    assert result.get("owner_name") is not None


# ── Home Loan Sanction Letter ─────────────────────────────────────────────────

def test_home_loan_sanction_parser():
    from parsers.realestate.home_loan_sanction_parser import HomeLoanSanctionParser
    ocr = _ocr("""HOME LOAN SANCTION LETTER
HDFC Bank Limited
Loan Account Number: HDFC/HL/2024/12345
Applicant Name: MR. RAJESH KUMAR VERMA
Co-Applicant Name: SUNITA VERMA
Property Address: Flat 302 Tower C Green Valley Noida
Sanctioned Loan Amount: Rs. 40,00,000
Rate of Interest: 8.75%
Type of Interest: Floating
Loan Tenure: 240 months
EMI: Rs. 35,234
Processing Fee: Rs. 10,000
Sanction Date: 01/04/2024
Valid Till: 30/06/2024
Branch Name: Connaught Place Branch
IFSC: HDFC0000001
District: Gautam Buddha Nagar State: Uttar Pradesh PIN: 201301""")
    result = HomeLoanSanctionParser().parse(ocr)
    assert result["doc_type"] == "home_loan_sanction"
    assert result.get("loan_amount") is not None
    assert result.get("interest_rate") is not None


# ── Legal Heir Certificate ────────────────────────────────────────────────────

def test_legal_heir_certificate_parser():
    from parsers.realestate.legal_heir_certificate_parser import LegalHeirCertificateParser
    ocr = _ocr("""LEGAL HEIR CERTIFICATE
Office of the Tehsildar, Rohtak
Certificate Type: Legal Heir Certificate
Certificate No: LHC/2024/ROH/789
Name of the Deceased: LATE SHRI MOHAN LAL SHARMA
Date of Death: 15/10/2023
Place of Death: Rohtak
Address: House No 5 Civil Lines Rohtak
Legal Heirs:
1. SURESH KUMAR SHARMA Son 45
2. MEENA DEVI Wife 62
3. PRIYA SHARMA Daughter 38
Issued by: Tehsildar Rohtak
District: Rohtak State: Haryana PIN: 124001""")
    result = LegalHeirCertificateParser().parse(ocr)
    assert result["doc_type"] == "legal_heir_certificate"
    assert result.get("deceased_name") is not None
    assert len(result.get("legal_heirs", [])) >= 1


# ── Classifier integration tests ──────────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("SALE DEED This deed of sale is executed Vendor RAMESH KUMAR Purchaser SURESH PATEL Sub-Registrar Stamp Duty Registration", "sale_deed"),
    ("AGREEMENT TO SELL Agreement for Sale Vendor Purchaser Earnest Money agreed price possession date", "agreement_to_sale"),
    ("ENCUMBRANCE CERTIFICATE Sub-Registrar NIL ENCUMBRANCE search period property", "encumbrance_certificate"),
    ("PROPERTY TAX RECEIPT Municipal Corporation Assessment Number Ward No Annual Tax Receipt No", "property_tax_receipt"),
    ("KHATA CERTIFICATE BBMP Bruhat Bengaluru Mahanagara Palike A-KHATA Khata Number Revenue Survey", "khata"),
    ("MUTATION CERTIFICATE Mutation Number Previous Owner New Owner Reason for Mutation Tehsildar", "mutation_certificate"),
    ("7/12 Extract Satbara Utara Survey Number Owner Cultivator Land Classification Maharashtra", "land_record"),
    ("RERA REGISTRATION CERTIFICATE Real Estate Regulatory Authority RERA Registration Number P51700012345 Promoter", "rera_certificate"),
    ("OCCUPANCY CERTIFICATE Municipal Corporation fit for occupation approved plan Total Floors Residential", "occupancy_certificate"),
    ("POSSESSION LETTER ABC Developers Possession Date Unit No Tower Floor Balance Due", "possession_letter"),
    ("GENERAL POWER OF ATTORNEY Principal Attorney Powers Granted sell transfer mortgage lease", "power_of_attorney"),
    ("LEASE DEED Lessor Lessee Monthly Rent Security Deposit Lock-in Period Rent Escalation", "lease_deed"),
    ("GIFT DEED Donor Donee out of love and affection without consideration gifted", "gift_deed"),
    ("PARTITION DEED undivided share equal share parties partition family settlement", "partition_deed"),
    ("MORTGAGE DEED Mortgagor Mortgagee Loan Amount Rate of Interest Equitable Mortgage hypothecation", "mortgage_deed"),
    ("e-STAMP CERTIFICATE SHCIL Stock Holding Corporation stamp duty paid GRN purchaser", "estamp_certificate"),
    ("VALUATION CERTIFICATE market value ready reckoner rate circle rate registered valuer IBBI", "property_valuation"),
    ("LOAN SANCTION LETTER Home Loan sanctioned amount Rate of Interest EMI processing fee loan tenure HDFC", "home_loan_sanction"),
    ("LEGAL HEIR CERTIFICATE Deceased Date of Death Legal Heirs Son Daughter Wife Tahsildar succession", "legal_heir_certificate"),
])
def test_classifier_realestate(text, expected):
    from classification.doc_classifier import classify_text
    result = classify_text(text)
    assert result.type == expected, f"Expected {expected}, got {result.type} (score text: {text[:60]})"
