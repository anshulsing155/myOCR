"""
Classify a document by type using two-phase scoring on OCR text:
  Phase 1 — keyword frequency scoring
  Phase 2 — structural regex patterns (PAN number, Aadhaar 12-digit, IFSC, etc.)

Supported types:
    bank_statement, pan_card, aadhaar, eshram, itr, invoice, salary_slip,
    property_doc, driving_license, voter_id, passport, vehicle_rc,
    birth_certificate, marriage_certificate, caste_certificate,
    income_certificate, domicile_certificate, ration_card, gst_certificate,
    marksheet, degree_certificate, ayushman_card, ppo,
    sale_deed, agreement_to_sale, encumbrance_certificate, property_tax_receipt,
    khata, mutation_certificate, land_record, rera_certificate,
    occupancy_certificate, possession_letter, power_of_attorney, lease_deed,
    gift_deed, partition_deed, mortgage_deed, estamp_certificate,
    property_valuation, home_loan_sanction, legal_heir_certificate, other
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import NamedTuple


class DocClass(NamedTuple):
    type: str
    confidence: float  # 0.0 – 1.0


# ── Phase 1: keyword tables ────────────────────────────────────────────────────
# All keys lowercased; matched against lowercased text.
_SIGNATURES: dict[str, list[tuple[str, float]]] = {
    "bank_statement": [
        ("account statement",      3.0),
        ("statement of account",   3.0),
        ("bank statement",         3.0),
        ("ifsc",                   2.0),
        ("micr",                   2.0),
        ("account number",         1.5),
        ("opening balance",        2.0),
        ("closing balance",        2.0),
        ("withdrawal",             1.5),
        ("deposit",                1.0),
        ("cheque",                 1.0),
        ("transaction",            1.0),
        ("balance",                0.5),
        ("chq",                    0.5),
        ("neft",                   1.5),
        ("rtgs",                   1.5),
        ("imps",                   1.5),
        ("upi",                    0.8),
    ],
    "pan_card": [
        ("permanent account number", 5.0),
        ("income tax department",    4.0),
        # "govt. of india" / "government of india" intentionally NOT here —
        # both PAN and Aadhaar share that phrase; PAN-specific phrases above are enough
        ("date of birth",            1.5),
        ("father",                   1.5),
        ("signature",                0.5),
    ],
    "aadhaar": [
        ("aadhaar",                          5.0),
        ("aadhar",                           5.0),
        ("unique identification authority",  4.0),
        ("uidai",                            4.0),
        ("enrolment no",                     2.0),
        ("enrolment",                        1.5),
        ("vid",                              3.0),   # was 1.0
        ("government of india",              1.0),   # shared but slight aadhaar signal
        ("date of birth",                    1.0),
    ],
    "itr": [
        ("income tax return",        5.0),
        ("itr",                      2.5),
        ("assessment year",          3.0),
        ("gross total income",       3.0),
        ("total income",             2.0),
        ("tax payable",              2.0),
        ("challan",                  2.0),
        ("deductions",               1.5),
        ("acknowledgement number",   2.0),
        ("form 16",                  2.0),
    ],
    "invoice": [
        ("tax invoice",        4.0),
        ("invoice no",         3.0),
        ("purchase order",     4.0),
        ("po number",          3.0),
        ("gstin",              3.0),
        ("gst",                1.5),
        ("bill to",            2.0),
        ("ship to",            1.5),
        ("amount due",         2.0),
        ("subtotal",           1.5),
        ("invoice",            1.0),
        ("expected delivery",  2.0),
        ("vendor",             1.0),
        ("hsn",                1.5),
        ("sac",                1.0),
    ],
    "salary_slip": [
        ("salary slip",      5.0),
        ("pay slip",         5.0),
        ("payslip",          5.0),
        ("basic salary",     3.0),
        ("hra",              2.0),
        ("provident fund",   2.0),
        ("pf",               1.5),
        ("gross salary",     3.0),
        ("net salary",       3.0),
        ("esic",             2.0),
        ("tds",              1.5),
        ("pay period",       2.0),
        ("employee id",      2.0),
        ("employer",         1.5),
    ],
    "property_doc": [
        ("sale deed",      5.0),
        ("sub-registrar",  4.0),
        ("stamp duty",     3.0),
        ("survey number",  2.5),
        ("plot no",        2.0),
        ("khata",          2.0),
        ("land",           1.5),
        ("registration",   1.5),
        ("conveyance",     2.0),
    ],
    "eshram": [
        ("eshram",                           6.0),
        ("e-shram",                          6.0),
        ("eshram card",                      6.0),
        ("universal account number",         5.0),
        ("ministry of labour",               4.0),
        ("ministry of labor",                4.0),
        ("unorganised workers",              3.0),
        ("unorganized workers",              3.0),
        ("csc centre",                       2.0),
        ("eshram.gov.in",                    3.0),
        ("eshramcare",                       3.0),
        ("blood group",                      1.0),
        ("occupation",                       0.5),
    ],
    "driving_license": [
        ("driving licence",                  6.0),
        ("driving license",                  6.0),
        ("indian union driving",             6.0),
        ("motor vehicles act",               4.0),
        ("son/daughter/wife of",             4.0),
        ("validity(nt)",                     4.0),
        ("validity(tr)",                     4.0),
        ("validity (nt)",                    4.0),
        ("validity (tr)",                    4.0),
        ("organ donor",                      3.0),
        ("date of first issue",              3.0),
        ("issued by",                        2.0),
        ("blood group",                      1.0),
    ],
    "voter_id": [
        ("election commission of india",     6.0),
        ("electors photo identity card",     6.0),
        ("epic",                             4.0),
        ("electoral roll",                   3.0),
        ("polling station",                  3.0),
        ("part no",                          2.0),
        ("assembly constituency",            3.0),
        ("parliamentary constituency",       2.0),
        ("voter",                            2.0),
        ("elector",                          2.0),
    ],
    "passport": [
        ("republic of india",                3.0),
        ("passport",                         5.0),
        ("place of birth",                   2.0),
        ("place of issue",                   2.0),
        ("date of expiry",                   3.0),
        ("date of issue",                    1.5),
        ("nationality",                      2.0),
        ("type of passport",                 3.0),
        ("ministry of external affairs",     4.0),
        ("emigration check",                 3.0),
    ],
    "vehicle_rc": [
        ("registration certificate",         5.0),
        ("motor vehicles act",               3.0),
        ("vahan",                            4.0),
        ("chassis no",                       3.0),
        ("engine no",                        3.0),
        ("insurance validity",               3.0),
        ("fitness validity",                 3.0),
        ("registered owner",                 3.0),
        ("fuel type",                        2.0),
        ("vehicle class",                    2.0),
        ("reg. no",                          2.0),
        ("seating capacity",                 2.0),
    ],
    "birth_certificate": [
        ("birth certificate",                6.0),
        ("certificate of birth",             6.0),
        ("date of birth",                    2.0),
        ("place of birth",                   2.0),
        ("father's name",                    2.0),
        ("mother's name",                    2.0),
        ("municipal corporation",            2.5),
        ("gram panchayat",                   2.0),
        ("birth registration",               3.0),
        ("born on",                          1.5),
    ],
    "marriage_certificate": [
        ("marriage certificate",             6.0),
        ("certificate of marriage",          6.0),
        ("date of marriage",                 4.0),
        ("groom",                            2.0),
        ("bride",                            2.0),
        ("husband",                          2.0),
        ("wife",                             2.0),
        ("marriage registration",            3.0),
        ("solemnized",                       3.0),
        ("hindu marriage act",               4.0),
        ("special marriage act",             4.0),
    ],
    "caste_certificate": [
        ("caste certificate",                6.0),
        ("community certificate",            5.0),
        ("scheduled caste",                  4.0),
        ("scheduled tribe",                  4.0),
        ("other backward class",             4.0),
        ("obc",                              3.0),
        ("belongs to",                       2.0),
        ("social category",                  3.0),
        ("creamy layer",                     3.0),
        ("non-creamy layer",                 3.0),
        ("tahsildar",                        2.0),
        ("revenue department",               2.0),
    ],
    "income_certificate": [
        ("income certificate",               6.0),
        ("annual income",                    4.0),
        ("per annum",                        3.0),
        ("income per annum",                 4.0),
        ("income from all sources",          4.0),
        ("revenue officer",                  2.0),
        ("tehsildar",                        2.0),
        ("income proof",                     3.0),
        ("yearly income",                    3.0),
    ],
    "domicile_certificate": [
        ("domicile certificate",             6.0),
        ("residence certificate",            5.0),
        ("permanent resident",               4.0),
        ("state of domicile",                5.0),
        ("bonafide resident",                4.0),
        ("domicile",                         3.0),
        ("residing in",                      2.0),
        ("resident of",                      2.0),
    ],
    "ration_card": [
        ("ration card",                      6.0),
        ("public distribution system",       5.0),
        ("pds",                              3.0),
        ("fair price shop",                  4.0),
        ("antyodaya anna yojana",            5.0),
        ("aay",                              3.0),
        ("bpl",                              3.0),
        ("apl",                              2.5),
        ("phh",                              3.0),
        ("priority household",               3.0),
        ("food and civil supplies",          3.0),
        ("nfsa",                             3.0),
    ],
    "gst_certificate": [
        ("goods and services tax",           4.0),
        ("central goods",                    3.0),
        ("state goods",                      3.0),
        ("gst registration",                 5.0),
        ("registration certificate",         2.0),
        ("legal name of business",           3.0),
        ("trade name",                       2.0),
        ("taxpayer type",                    3.0),
        ("constitution of business",         3.0),
        ("principal place of business",      3.0),
        ("nature of business",               2.0),
    ],
    "marksheet": [
        ("mark sheet",                       5.0),
        ("statement of marks",               5.0),
        ("cbse",                             4.0),
        ("icse",                             4.0),
        ("board of secondary education",     4.0),
        ("examination result",               3.0),
        ("class x",                          3.0),
        ("class xii",                        3.0),
        ("10th",                             2.0),
        ("12th",                             2.0),
        ("roll number",                      2.0),
        ("marks obtained",                   3.0),
        ("pass/fail",                        2.0),
        ("result",                           1.0),
        ("grade",                            1.0),
    ],
    "degree_certificate": [
        ("degree certificate",               5.0),
        ("bachelor of",                      5.0),
        ("master of",                        5.0),
        ("doctor of",                        5.0),
        ("diploma in",                       4.0),
        ("university",                       2.0),
        ("conferred",                        4.0),
        ("awarded the degree",               5.0),
        ("convocation",                      4.0),
        ("chancellor",                       3.0),
        ("this is to certify",               1.5),
        ("year of passing",                  2.0),
    ],
    "ayushman_card": [
        ("ayushman bharat",                  6.0),
        ("pmjay",                            6.0),
        ("pradhan mantri jan arogya",        6.0),
        ("pm-jan arogya yojana",             6.0),
        ("health benefit package",           4.0),
        ("beneficiary",                      2.0),
        ("empanelled hospital",              3.0),
        ("family id",                        2.0),
        ("pm jay",                           5.0),
    ],
    "ppo": [
        ("pension payment order",            6.0),
        ("ppo",                              4.0),
        ("pensioner",                        3.0),
        ("cpao",                             4.0),
        ("central pension",                  4.0),
        ("date of retirement",               3.0),
        ("commuted pension",                 4.0),
        ("gratuity",                         2.0),
        ("dcrg",                             3.0),
        ("superannuation",                   3.0),
        ("epfo",                             3.0),
        ("monthly pension",                  4.0),
        ("family pension",                   3.0),
    ],
    # ── Real-estate documents ──────────────────────────────────────────────────
    "sale_deed": [
        ("sale deed",                        8.0),
        ("deed of sale",                     7.0),
        ("vendor",                           2.0),
        ("purchaser",                        2.0),
        ("sub-registrar",                    4.0),
        ("stamp duty",                       3.0),
        ("registration fee",                 3.0),
        ("absolute sale",                    5.0),
        ("consideration",                    2.0),
        ("conveyance deed",                  6.0),
        ("book no",                          1.5),
        ("page no",                          1.0),
    ],
    "agreement_to_sale": [
        ("agreement to sell",                8.0),
        ("agreement for sale",               8.0),
        ("memorandum of understanding",      5.0),
        ("earnest money",                    5.0),
        ("advance payment",                  3.0),
        ("balance amount",                   2.0),
        ("vendor",                           2.0),
        ("purchaser",                        2.0),
        ("possession",                       2.0),
        ("agreed price",                     4.0),
    ],
    "encumbrance_certificate": [
        ("encumbrance certificate",          9.0),
        ("nil encumbrance",                  8.0),
        ("no encumbrance",                   6.0),
        ("encumbrance",                      4.0),
        ("sub-registrar",                    3.0),
        ("search period",                    5.0),
        ("mortgage",                         2.0),
        ("charge",                           1.5),
    ],
    "property_tax_receipt": [
        ("property tax",                     6.0),
        ("house tax",                        6.0),
        ("municipal tax",                    5.0),
        ("assessment number",                5.0),
        ("municipal corporation",            3.0),
        ("nagar palika",                     4.0),
        ("nagar nigam",                      4.0),
        ("ward no",                          2.0),
        ("tax receipt",                      5.0),
        ("annual tax",                       4.0),
        ("penalty",                          1.5),
    ],
    "khata": [
        ("khata certificate",                8.0),
        ("khata extract",                    7.0),
        ("khata number",                     6.0),
        ("khata",                            4.0),
        ("bbmp",                             5.0),
        ("bruhat bengaluru",                 5.0),
        ("a-khata",                          6.0),
        ("b-khata",                          6.0),
        ("revenue survey",                   3.0),
        ("site area",                        2.0),
    ],
    "mutation_certificate": [
        ("mutation certificate",             8.0),
        ("mutation number",                  7.0),
        ("mutation",                         4.0),
        ("transfer of ownership",            6.0),
        ("previous owner",                   5.0),
        ("new owner",                        5.0),
        ("reason for mutation",              6.0),
        ("tehsildar",                        2.0),
        ("village",                          1.5),
    ],
    "land_record": [
        ("7/12 extract",                     9.0),
        ("satbara",                          9.0),
        ("jamabandi",                        9.0),
        ("fard jamabandi",                   9.0),
        ("record of rights",                 7.0),
        ("rtc extract",                      8.0),
        ("pahani",                           7.0),
        ("patta",                            6.0),
        ("khatauni",                         7.0),
        ("khasra",                           5.0),
        ("survey number",                    2.5),
        ("cultivator",                       3.0),
        ("land classification",              4.0),
        ("revenue village",                  4.0),
    ],
    "rera_certificate": [
        ("rera registration",                9.0),
        ("real estate regulatory authority", 8.0),
        ("rera number",                      8.0),
        ("rera",                             5.0),
        ("project registration",             4.0),
        ("promoter",                         3.0),
        ("completion date",                  2.0),
        ("carpet area",                      2.0),
    ],
    "occupancy_certificate": [
        ("occupancy certificate",            9.0),
        ("completion certificate",           7.0),
        ("commencement certificate",         7.0),
        ("oc certificate",                   7.0),
        ("building completion",              6.0),
        ("fit for occupation",               7.0),
        ("building plan",                    2.5),
        ("approved plan",                    3.0),
        ("total floors",                     3.0),
    ],
    "possession_letter": [
        ("possession letter",                9.0),
        ("letter of possession",             8.0),
        ("handover",                         5.0),
        ("handing over",                     5.0),
        ("possession date",                  6.0),
        ("unit no",                          2.5),
        ("tower",                            2.0),
        ("flat no",                          2.5),
        ("booking amount",                   3.0),
    ],
    "power_of_attorney": [
        ("power of attorney",                9.0),
        ("general power of attorney",        9.0),
        ("special power of attorney",        8.0),
        ("gpa",                              5.0),
        ("spa",                              4.0),
        ("attorney",                         4.0),
        ("principal",                        2.0),
        ("do and execute",                   5.0),
        ("authorize",                        2.0),
    ],
    "lease_deed": [
        ("lease deed",                       9.0),
        ("leave and licence",                8.0),
        ("lease agreement",                  8.0),
        ("lessor",                           5.0),
        ("lessee",                           5.0),
        ("monthly rent",                     4.0),
        ("security deposit",                 4.0),
        ("lock-in period",                   5.0),
        ("rent escalation",                  5.0),
        ("notice period",                    3.0),
    ],
    "gift_deed": [
        ("gift deed",                        9.0),
        ("deed of gift",                     8.0),
        ("donor",                            5.0),
        ("donee",                            5.0),
        ("gift",                             3.0),
        ("out of love and affection",        7.0),
        ("without consideration",            6.0),
        ("gifted",                           3.0),
    ],
    "partition_deed": [
        ("partition deed",                   9.0),
        ("deed of partition",                8.0),
        ("relinquishment deed",              8.0),
        ("family settlement",                7.0),
        ("equal share",                      5.0),
        ("undivided share",                  6.0),
        ("partition",                        3.0),
        ("relinquish",                       4.0),
    ],
    "mortgage_deed": [
        ("mortgage deed",                    9.0),
        ("deed of mortgage",                 8.0),
        ("hypothecation",                    7.0),
        ("mortgagor",                        6.0),
        ("mortgagee",                        6.0),
        ("equitable mortgage",               7.0),
        ("simple mortgage",                  7.0),
        ("loan amount",                      2.5),
        ("rate of interest",                 2.0),
    ],
    "estamp_certificate": [
        ("e-stamp",                          9.0),
        ("estamp",                           9.0),
        ("stamp certificate",                7.0),
        ("shcil",                            7.0),
        ("stamp duty paid",                  5.0),
        ("grn",                              3.0),
        ("purchaser",                        2.0),
        ("authorized vendor",                5.0),
        ("stock holding corporation",        7.0),
    ],
    "property_valuation": [
        ("valuation certificate",            8.0),
        ("market value",                     5.0),
        ("fair market value",                7.0),
        ("ready reckoner rate",              7.0),
        ("circle rate",                      6.0),
        ("valuation report",                 7.0),
        ("ibbi",                             5.0),
        ("registered valuer",                6.0),
        ("distress value",                   6.0),
        ("forced sale value",                6.0),
    ],
    "home_loan_sanction": [
        ("loan sanction letter",             9.0),
        ("sanction letter",                  7.0),
        ("home loan",                        6.0),
        ("housing loan",                     6.0),
        ("sanctioned amount",                6.0),
        ("rate of interest",                 2.0),
        ("emi",                              3.0),
        ("processing fee",                   4.0),
        ("loan tenure",                      5.0),
        ("hdfc",                             2.0),
        ("sbi",                              2.0),
        ("lic housing",                      4.0),
    ],
    "legal_heir_certificate": [
        ("legal heir certificate",           9.0),
        ("succession certificate",           8.0),
        ("heirship certificate",             8.0),
        ("survivorship certificate",         8.0),
        ("legal heir",                       5.0),
        ("deceased",                         4.0),
        ("date of death",                    4.0),
        ("heirs",                            3.0),
        ("tahsildar",                        2.0),
    ],
}

_MAX_KW_SCORE = {k: sum(w for _, w in v) for k, v in _SIGNATURES.items()}


# ── Phase 2: structural pattern scores ────────────────────────────────────────
# Patterns that give strong structural evidence of a document type.
# Applied on ORIGINAL CASE text so PAN/IFSC patterns match correctly.
_PATTERN_SCORES: list[tuple[re.Pattern, str, float]] = [
    # eShram UAN: exactly 12 digits in 4-4-4 spaced format preceded by "UAN" label
    # Must be checked BEFORE generic Aadhaar pattern to avoid false positives
    (re.compile(r"\bUAN\b.*?\b\d{4}\s\d{4}\s\d{4}\b", re.I | re.S), "eshram", 8.0),
    # eShram domain / care email
    (re.compile(r"eshram\.gov\.in|eshramcare", re.I),                  "eshram", 5.0),
    # Aadhaar 12-digit number in "XXXX XXXX XXXX" display format
    (re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b"), "aadhaar", 5.0),
    # Aadhaar VID 16-digit
    (re.compile(r"\bVID\b", re.I),                        "aadhaar",        3.0),
    # Gender on Aadhaar card
    (re.compile(r"\b(FEMALE|MALE)\b"),                    "aadhaar",        2.0),
    # PAN number: AAAAA9999A format
    (re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),           "pan_card",       5.0),
    # IFSC code: ABCD0XXXXXX
    (re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),            "bank_statement", 3.0),
    # Long account numbers (11–18 digits, no spaces)
    (re.compile(r"\b\d{11,18}\b"),                        "bank_statement", 1.0),
    # ITR acknowledgement: 15-digit number
    (re.compile(r"\b\d{15}\b"),                           "itr",            2.0),
    # GSTIN: 15-char alphanumeric with digits in specific positions
    (re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d][Z][A-Z\d]\b"), "invoice", 3.0),
    # Indian DL number: StateCode(2) + DistrictCode(2) + Year(4) + Serial(7)
    (re.compile(r"\b[A-Z]{2}[-\s]?\d{2}[-\s]?\d{4}[-\s]?\d{7}\b"), "driving_license", 5.0),
    # Voter ID EPIC number: explicit "EPIC" label near 2-3 letters + 7 digits pattern
    # (bare alphanumeric is too broad — matches DL state codes, bank codes, etc.)
    (re.compile(r"\bEPIC\b.*?\b[A-Z]{2,3}\d{7}\b|\b[A-Z]{2,3}\d{7}\b.*?\bEPIC\b", re.I | re.S), "voter_id", 5.0),
    # Standalone EPIC pattern only when near electoral roll keywords
    (re.compile(r"\belectors?\s+photo\s+identity\b|\belectoral\s+roll\b", re.I), "voter_id", 5.0),
    # Election Commission of India label — strongest signal
    (re.compile(r"election\s*commission\s*of\s*india", re.I),        "voter_id",        6.0),
    # Indian Passport number: letter + 7 digits PRECEDED by "Passport No" label to avoid false positives
    (re.compile(r"passport\s*(?:no\.?|number)[:\s]*[A-PR-WY]\d{7}", re.I), "passport", 6.0),
    # MRZ line (machine-readable zone): 20+ uppercase + digits + '<'
    (re.compile(r"\bP<IND[A-Z<]{10,}"),                              "passport",        6.0),
    # Bare passport number only as a secondary signal (weight reduced to avoid false positives)
    (re.compile(r"\b[A-PR-WY]\d{7}\b"),                              "passport",        2.0),
    # Vehicle registration number: state-code(2) + district(2) + series + number
    (re.compile(r"\b[A-Z]{2}\s*\d{1,2}\s*[A-Z]{1,3}\s*\d{1,4}\b"), "vehicle_rc",      4.0),
    # Chassis number: 17-char VIN
    (re.compile(r"\b[A-Z0-9]{17}\b"),                                "vehicle_rc",      2.0),
    # Birth certificate keyword
    (re.compile(r"birth\s*certificate", re.I),                       "birth_certificate", 6.0),
    # Marriage certificate keyword
    (re.compile(r"marriage\s*certificate", re.I),                    "marriage_certificate", 6.0),
    # Caste certificate patterns
    (re.compile(r"caste\s*certificate|community\s*certificate", re.I), "caste_certificate", 6.0),
    (re.compile(r"\b(SC|ST|OBC|EWS)\b"),                             "caste_certificate", 2.0),
    # Income certificate
    (re.compile(r"income\s*certificate", re.I),                      "income_certificate", 6.0),
    # Domicile certificate
    (re.compile(r"domicile\s*certificate|residence\s*certificate", re.I), "domicile_certificate", 6.0),
    # Ration card
    (re.compile(r"ration\s*card", re.I),                             "ration_card",     6.0),
    (re.compile(r"\b(APL|BPL|AAY|PHH|NFSA)\b"),                     "ration_card",     3.0),
    # GST certificate — GSTIN already covered in invoice; add GST registration label
    (re.compile(r"gst\s*registration\s*certificate", re.I),          "gst_certificate", 6.0),
    # Marksheet patterns
    (re.compile(r"mark\s*sheet|statement\s*of\s*marks", re.I),       "marksheet",       5.0),
    # Degree certificate
    (re.compile(r"degree\s*certificate|bachelor\s*of|master\s*of|doctor\s*of", re.I), "degree_certificate", 4.0),
    (re.compile(r"conferred|awarded\s*the\s*degree", re.I),          "degree_certificate", 4.0),
    # Ayushman Bharat / PM-JAY
    (re.compile(r"ayushman\s*bharat|pmjay|pradhan\s*mantri\s*jan\s*arogya", re.I), "ayushman_card", 6.0),
    # PPO / Pension Payment Order
    (re.compile(r"pension\s*payment\s*order|ppo\s*no", re.I),        "ppo",             6.0),
    (re.compile(r"\bCPAO\b|\bEPFO\b"),                               "ppo",             4.0),
    # ── Real-estate document structural patterns ──────────────────────────────
    (re.compile(r"sale\s*deed|deed\s*of\s*sale|conveyance\s*deed", re.I), "sale_deed", 8.0),
    (re.compile(r"agreement\s*(?:to\s*sell|for\s*sale)|memorandum\s*of\s*understanding", re.I), "agreement_to_sale", 7.0),
    (re.compile(r"encumbrance\s*certificate|nil\s*encumbrance", re.I), "encumbrance_certificate", 8.0),
    (re.compile(r"property\s*tax|house\s*tax|assessment\s*(?:no|number)", re.I), "property_tax_receipt", 5.0),
    (re.compile(r"khata\s*(?:certificate|extract|number)|a[\-\s]khata|b[\-\s]khata|\bbbmp\b", re.I), "khata", 7.0),
    (re.compile(r"mutation\s*(?:certificate|number|entry)|transfer\s*of\s*ownership", re.I), "mutation_certificate", 7.0),
    (re.compile(r"7/12\s*extract|satbara|jamabandi|fard\s*jamabandi|rtc\s*extract|pahani\b|khatauni\b", re.I), "land_record", 8.0),
    (re.compile(r"\bRERA\b.*?(?:registration|number|no\.?)|real\s*estate\s*regulatory", re.I), "rera_certificate", 8.0),
    # RERA number formats across states
    (re.compile(r"\bP\d{11}\b|UPRERAPRJ\d+|DLRERA\d+|HRERA\d+|TNRERA\d+", re.I), "rera_certificate", 6.0),
    (re.compile(r"occupancy\s*certificate|completion\s*certificate|commencement\s*certificate", re.I), "occupancy_certificate", 8.0),
    (re.compile(r"possession\s*letter|letter\s*of\s*possession|handing\s*over", re.I), "possession_letter", 8.0),
    (re.compile(r"power\s*of\s*attorney|general\s*power\s*of\s*attorney|special\s*power\s*of\s*attorney", re.I), "power_of_attorney", 9.0),
    (re.compile(r"lease\s*deed|leave\s*and\s*licen[cs]e|lease\s*agreement", re.I), "lease_deed", 8.0),
    (re.compile(r"gift\s*deed|deed\s*of\s*gift", re.I), "gift_deed", 9.0),
    (re.compile(r"partition\s*deed|relinquishment\s*deed|family\s*settlement", re.I), "partition_deed", 8.0),
    (re.compile(r"mortgage\s*deed|deed\s*of\s*(?:mortgage|hypothecation)|equitable\s*mortgage", re.I), "mortgage_deed", 8.0),
    # e-Stamp certificate number: IN-XX + digits
    (re.compile(r"\bIN[\-]?[A-Z]{2}\d{17,}\b"), "estamp_certificate", 8.0),
    (re.compile(r"e[\-\s]?stamp\s*certificate|shcil|stock\s*holding\s*corporation", re.I), "estamp_certificate", 7.0),
    (re.compile(r"valuation\s*(?:certificate|report)|market\s*value|ready\s*reckoner\s*rate|circle\s*rate", re.I), "property_valuation", 6.0),
    (re.compile(r"loan\s*sanction\s*letter|sanction\s*letter|home\s*loan.*?sanction|housing\s*loan.*?sanction", re.I), "home_loan_sanction", 8.0),
    (re.compile(r"legal\s*heir\s*certificate|succession\s*certificate|heirship\s*certificate|survivorship\s*certificate", re.I), "legal_heir_certificate", 9.0),
]


def classify(ocr_results: list[dict]) -> DocClass:
    """Classify document type from a list of OCR result dicts."""
    original_text = " ".join(r.get("text", "") for r in ocr_results)
    return classify_text(original_text)


def classify_text(text: str) -> DocClass:
    """Classify document type from a raw text string."""
    scores: dict[str, float] = defaultdict(float)
    lower = text.lower()

    # Phase 1: keyword scoring
    for doc_type, keywords in _SIGNATURES.items():
        for kw, weight in keywords:
            if kw in lower:
                scores[doc_type] += weight

    # Phase 2: structural pattern scoring (original case)
    for pattern, doc_type, weight in _PATTERN_SCORES:
        if pattern.search(text):
            scores[doc_type] += weight

    if not scores:
        return DocClass("other", 0.0)

    best_type = max(scores, key=lambda k: scores[k])
    raw_score = scores[best_type]

    # Normalise: sum of keyword max + structural max per type
    kw_max  = _MAX_KW_SCORE.get(best_type, 0.0)
    pat_max = sum(w for _, t, w in _PATTERN_SCORES if t == best_type)
    max_possible = kw_max + pat_max
    confidence = min(1.0, raw_score / max_possible) if max_possible > 0 else 0.0

    # Require the winner to score at least 6% of its maximum
    if confidence < 0.06:
        return DocClass("other", 0.0)

    return DocClass(best_type, round(confidence, 3))
