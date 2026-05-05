# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

## [1.2.0] — 2026-05-05

### Added
- **19 real-estate document parsers** covering the full Indian property transaction lifecycle:
  - Transactional: Sale Deed, Agreement to Sale, Gift Deed, Partition Deed, Lease Deed, Mortgage Deed
  - Financial: Home Loan Sanction Letter, Property Valuation Certificate, e-Stamp Certificate, Property Tax Receipt
  - Legal/Title: Encumbrance Certificate, Legal Heir Certificate, Power of Attorney, Mutation Certificate
  - Land Records: Jamabandi/7-12/RTC/Patta/Khatauni/Khasra (auto-detected), Khata Certificate
  - Builder/Project: RERA Certificate, Occupancy Certificate, Possession Letter
- Real-estate shared helper module (`parsers/realestate/_helpers.py`) with `norm_date`, `parse_amount`, `parse_area`, `clean_amount`, `extract_parties` and compiled regex constants for PIN, State, District, SRO, Stamp Duty, IFSC, Survey/Plot numbers
- Two-phase classifier updated with all 19 real-estate doc types (keyword scores + structural regex patterns)
- Pipeline `_route()` and app `_parse_for_type()` wired to all 19 new parsers
- 39 new pytest tests (20 parser smoke tests + 19 classifier integration tests) in `tests/test_realestate_parsers.py`

## [1.1.0] — 2026-05-05

### Added
- **14 Indian identity and certificate parsers**:
  - Identity: Voter ID, Passport, Vehicle RC
  - Health/Social: Ayushman Bharat (PM-JAY) Card, eShram Card
  - Certificates: Birth, Marriage, Caste/Community, Income, Domicile
  - Financial: GST Registration Certificate, Pension Payment Order (PPO)
  - Education: Marksheet (CBSE/ICSE/State Boards), Degree Certificate
  - Government: Ration Card (AAY/BPL/PHH)
- Classifier `_SIGNATURES` and `_PATTERN_SCORES` updated for all 14 new types
- Pipeline and Streamlit UI wired to all 14 new parsers
- 24 new pytest tests covering all new parsers + classifier integration
- xAI Grok Vision AI integration for bank statement extraction (`ocr/grok_bank_ocr.py`)
- Automatic PaddleOCR/Tesseract OCR availability detection (`ocr/availability.py`)

## [1.0.0] — 2026-05-05

### Added
- Multi-engine OCR pipeline: PaddleOCR v3 + Tesseract with confidence-based fallback
- Support for 10+ Indian scripts (Devanagari, Bengali, Tamil, Telugu, Kannada, Malayalam, Gujarati, Punjabi, Odia, Urdu)
- Vision AI integration: Google Gemini 2.5 Flash for bank statement extraction
- Document classification with two-phase scoring (keyword + structural patterns)
- Parsers for: Bank Statement, PAN Card, Aadhaar, Driving Licence, eShram, ITR, Salary Slip, Invoice (Generic)
- Bank identification and schema mapping for 9 Indian banks (HDFC, SBI, ICICI, Axis, Kotak, PNB, Bank of Baroda, Canara, IndusInd)
- Spatial table reconstruction from raw OCR bounding boxes
- Multi-page PDF handling with continuation table merging
- Digital PDF extraction path via pdfplumber (no OCR for native-text PDFs)
- Language detection, script identification, and Google Translate integration
- Streamlit web UI with drag-and-drop upload and live JSON preview
- CLI (`main.py`) for headless/scripted processing
- Image quality assessment to conditionally skip preprocessing
- GitHub Actions CI: lint (ruff) + test jobs on push/PR to main
- MIT licence, pyproject.toml packaging, python-dotenv config
