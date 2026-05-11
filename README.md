# DocuSense — Indian Document Intelligence Pipeline

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/anshulsing155/DocuSense/actions/workflows/ci.yml/badge.svg)](https://github.com/anshulsing155/DocuSense/actions)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)](https://streamlit.io)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

> **Upload a PDF or image — get structured JSON in seconds.**
>
> DocuSense is a production-ready OCR pipeline purpose-built for Indian financial and
> identity documents: bank statements, PAN cards, Aadhaar, salary slips, ITR,
> driving licences, eShram cards, GST certificates, and 40+ more document types.

---

## Table of Contents

- [Features](#features)
- [Supported Documents](#supported-documents)
- [Supported Banks](#supported-banks)
- [Supported Languages](#supported-languages)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Output Format](#output-format)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Security](#security)
- [FAQ](#faq)
- [License](#license)

---

## Features

| Category | Capability |
|---|---|
| **OCR Engines** | PaddleOCR (primary) + Tesseract (fallback) with confidence-based routing |
| **Vision AI** | Google Gemini 2.5 Flash and xAI Grok for high-accuracy bank statement extraction |
| **Indian Scripts** | Devanagari, Bengali, Tamil, Telugu, Kannada, Malayalam, Gujarati, Punjabi, Odia, Urdu |
| **Bilingual Docs** | Auto-detects and merges English + regional language OCR results |
| **Document Types** | 40+ Indian document types with dedicated field-level parsers |
| **Bank Support** | HDFC, SBI, ICICI, Axis, Kotak, PNB, Bank of Baroda, Canara, IndusInd |
| **Digital PDFs** | pdfplumber fast-path — no OCR needed for native-text PDFs |
| **Spatial Tables** | Recovers tabular data from raw OCR bounding boxes |
| **Multi-page** | Merges continuation tables, handles mixed-type PDFs |
| **Image Quality** | Auto-assesses sharpness/contrast and skips preprocessing for clean scans |
| **Web UI** | Drag-and-drop Streamlit interface with live JSON preview and download |
| **CLI** | Headless processing for scripting, batch jobs, and automation |
| **Python API** | Importable pipeline for embedding in your own applications |

---

## Supported Documents

### Identity & Government

| Document | Key Fields Extracted |
|---|---|
| **Aadhaar Card** | Aadhaar number (masked/full), VID, name, DOB, gender, address, PIN code, state |
| **PAN Card** | PAN number, holder type (individual/company), name, father's name, DOB |
| **Driving Licence** | DL number, issue/expiry dates, vehicle classes, blood group, address |
| **Voter ID** | EPIC number, name, father/husband name, address, polling station |
| **Passport** | Passport number, surname, given name, nationality, DOB, place of issue, validity |
| **Vehicle RC** | Registration number, owner name, chassis, engine, class, fuel type, validity |
| **Ration Card** | Card number, category (AAY/BPL/PHH), head of family, member count |
| **eShram Card** | UAN, name, DOB, gender, blood group, occupation, contact, address, state |
| **Ayushman Card** | Beneficiary ID, name, age, family ID, scheme details |

### Financial

| Document | Key Fields Extracted |
|---|---|
| **Bank Statement** | Account number, IFSC, holder name, period, opening/closing balance, full transaction table |
| **Salary Slip** | Employee info, designation, PAN, PF account, earnings breakdown, deductions, net salary |
| **ITR Acknowledgement** | PAN, assessment year, acknowledgement number, total income, taxes paid, refund |
| **GST Certificate** | GSTIN, legal/trade name, taxpayer type, state, principal place of business, date |
| **Pension Payment Order (PPO)** | PPO number, pensioner name, pension type, basic pension, bank details |
| **Invoice / Bill** | Seller/buyer GSTIN, line items with HSN/SAC, GST breakdown, totals |

### Real Estate (19 subtypes)

| Document | Description |
|---|---|
| Sale Deed | Parties, property schedule, stamp duty, registration, sale consideration |
| Agreement to Sale | Parties, property, advance amount, possession date |
| Gift Deed | Donor, donee, property schedule, relationship |
| Mortgage Deed | Mortgagor, mortgagee, loan amount, interest, property details |
| Lease Deed | Lessor, lessee, rent, lease period, property details |
| Partition Deed | Co-owners, shares, property description |
| Power of Attorney | Principal, agent, property details, scope |
| Encumbrance Certificate | EC period, property details, transaction history |
| RERA Certificate | Project name, developer, registration number, completion date |
| Property Tax Receipt | Property ID, owner, tax amount, payment period |
| Property Valuation Report | Property details, valuation amount, valuer info |
| Khata Certificate | Khata number, owner, property details, municipality |
| Land Record (Jamabandi/7-12/Patta/RTC) | Survey/plot number, owner, area, land use, revenue details |
| Possession Letter | Buyer, builder, property, possession date, amount paid |
| Mutation Certificate | Mutation number, previous/new owner, property reference |
| Occupancy Certificate | Building, developer, authority, completion date |
| Legal Heir Certificate | Deceased, legal heirs, relationship, issuing authority |
| Home Loan Sanction Letter | Borrower, lender, loan amount, tenure, ROI, EMI |
| e-Stamp Certificate | Stamp number, purchaser, purpose, stamp duty paid |

### Education & Other

| Document | Key Fields Extracted |
|---|---|
| **Marksheet** | Student name, roll number, school/board, subject-wise marks, result |
| **Degree Certificate** | Student name, degree, specialisation, institution, year of passing |
| **Birth Certificate** | Name, DOB, place of birth, parents, registration number |
| **Caste Certificate** | Name, caste/subcaste, category (SC/ST/OBC), issuing authority |
| **Domicile Certificate** | Name, DOB, permanent address, state, issuing authority |
| **Income Certificate** | Name, annual income, issuing authority, validity |
| **Marriage Certificate** | Bride/groom names, DOB, date of marriage, registration number |

---

## Supported Banks

DocuSense extracts complete transaction tables and account metadata from 9 major Indian banks:

| Bank | Statement Format | Digital PDF | OCR/Scanned | Supported Metadata |
|---|---|---|---|---|
| **HDFC Bank** | Table rows, multi-page | Yes | Yes | Account number, IFSC, holder name, period, balances |
| **State Bank of India (SBI)** | Double-date format (txn + value date) | Yes | Yes | Account number, IFSC, CIF, branch, MOD balance |
| **ICICI Bank** | Narration-first rows | Yes | Yes | Account number, IFSC, holder name, address |
| **Axis Bank** | Standard table | Yes | Yes | Account number, IFSC, customer ID |
| **Kotak Mahindra** | Standard table | Yes | Yes | Account number, IFSC |
| **Punjab National Bank (PNB)** | Standard table | Yes | Yes | Account number, IFSC, branch |
| **Bank of Baroda** | Standard table | Yes | Yes | Account number, IFSC |
| **Canara Bank** | Standard table | Yes | Yes | Account number, IFSC |
| **IndusInd Bank** | Standard table | Yes | Yes | Account number, IFSC |

**Bank statement extraction path:**

```
Digital PDF  -->  pdfplumber fast-path  -->  spatial column reconstruction  -->  JSON
Scanned PDF  -->  PaddleOCR / Tesseract  -->  spatial column reconstruction  -->  JSON
Complex/Mixed  -->  Gemini 2.5 Flash or Grok Vision AI  -->  JSON
```

---

## Supported Languages

DocuSense processes documents in **10 Indian scripts** plus English:

| Script | Language(s) | Tesseract Code | PaddleOCR |
|---|---|---|---|
| **Latin** | English | `eng` | Yes |
| **Devanagari** | Hindi, Marathi, Sanskrit, Nepali | `hin`, `mar` | Yes |
| **Bengali** | Bengali, Assamese | `ben` | Yes |
| **Tamil** | Tamil | `tam` | Yes |
| **Telugu** | Telugu | `tel` | Yes |
| **Kannada** | Kannada | `kan` | Yes |
| **Malayalam** | Malayalam | `mal` | Yes |
| **Gujarati** | Gujarati | `guj` | Yes |
| **Punjabi** | Punjabi (Gurmukhi) | `pan` | Yes |
| **Odia** | Odia | `ori` | Yes |
| **Urdu** | Urdu (Nastaliq) | `urd` | Yes |

Bilingual documents (e.g., Hindi+English Aadhaar) are handled with per-block language detection and automatic translation via Google Translate.

---

## Architecture

```
Input (PDF / Image)
       |
       +-- Is digital PDF? --> pdfplumber text extraction (instant, no OCR)
       |
       +-- Image / Scanned PDF
               |
               +- 1. Image Quality     sharpness + contrast assessment
               +- 2. Preprocessing     grayscale -> denoise -> threshold -> deskew
               +- 3. Layout Detection  LayoutParser / Detectron2 (optional)
               +- 4. OCR              PaddleOCR + Tesseract, confidence-based fallback
               |                       OR Vision AI (Gemini / Grok) for complex docs
               +- 5. Language Det.    per-block detection + translation metadata
               +- 6. Classification   keyword scoring + structural pattern matching
               +- 7. Parser           document-type-specific field extraction
                       |
                       +--> Structured JSON output
```

**Confidence-based OCR routing:**

```
PaddleOCR result
    |
    confidence >= threshold?  --> accept
    |
    no --> Tesseract fallback
               |
               compare word-level confidence scores
               |
               merge best-confidence tokens from both engines
               |
               --> final OCR result
```

**Bank statement digital fast-path:**

```
Digital PDF -> pdfplumber extract_words() -> spatial column reconstruction
           -> bank identifier -> bank-specific schema -> transactions + metadata
```

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/anshulsing155/DocuSense.git
cd DocuSense

# 2. Install
pip install -r requirements.txt

# 3. Configure (Windows: point to Tesseract; optionally add AI API keys)
cp .env.example .env
# edit .env

# 4. Launch the web UI
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501), upload a document, download JSON.

---

## Installation

### Prerequisites

| Dependency | Install |
|---|---|
| **Python 3.10+** | [python.org](https://www.python.org/downloads/) |
| **Tesseract OCR** | [Windows](https://github.com/UB-Mannheim/tesseract/wiki) · Ubuntu: `sudo apt install tesseract-ocr` · macOS: `brew install tesseract` |
| **Tesseract lang packs** | Ubuntu: `sudo apt install tesseract-ocr-hin tesseract-ocr-ben tesseract-ocr-tam` (and others) |
| **PaddleOCR** | Installed automatically via `pip install -r requirements.txt` |
| **Detectron2** *(optional)* | Required only for layout detection — see below |

### Step-by-Step

```bash
# Clone
git clone https://github.com/anshulsing155/DocuSense.git
cd DocuSense

# Virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

# Core dependencies
pip install -r requirements.txt

# Optional: Detectron2 layout detection (Linux/macOS only)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install "git+https://github.com/facebookresearch/detectron2.git"

# Environment configuration
cp .env.example .env
# Edit .env — set TESSERACT_CMD on Windows, add AI API keys if needed
```

### Environment Variables

| Variable | Description | Required |
|---|---|---|
| `TESSERACT_CMD` | Full path to `tesseract.exe` | Only if not on PATH (Windows) |
| `TESSDATA_PREFIX` | Path to tessdata language folder | Only if non-standard install |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/) API key | For Gemini OCR mode |
| `GROK_API_KEY` | xAI API key | For Grok OCR mode |

---

## Usage

### Web UI

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. Features:

- Drag-and-drop PDF or image upload (JPEG, PNG, TIFF, PDF)
- Automatic document type detection
- Live JSON preview with syntax highlighting
- Per-page language detection and translation metadata
- Optional layout detection visualisation
- Vision AI toggle (Gemini / Grok) for complex bank statements
- One-click JSON download

### CLI

```bash
python main.py --input document.pdf
python main.py --input statement.pdf --mode tesseract
python main.py --input document.pdf --mode auto --debug
```

| Flag | Values | Default | Description |
|---|---|---|---|
| `--input` | file path | *(required)* | PDF or image file |
| `--mode` | `auto` `complex` `tesseract` `merge` | `auto` | OCR engine selection |
| `--debug` | — | off | Save layout visualisation images to `outputs/` |

### Batch Processing

```bash
python scripts/batch_run.py
```

Processes every supported file in `inputs/`, writes per-file JSON to `outputs/`,
and writes a combined summary to `outputs/_batch_summary.json`.

### Python API

```python
from pipeline.document_pipeline import DocumentPipeline
from utils.pdf_to_image import pdf_to_images

pipeline = DocumentPipeline()
images = pdf_to_images("statement.pdf")
result = pipeline.process_pages(images)

print(result["doc_type"])           # "bank_statement"
print(result["account_number"])     # "XXXXXXXXXXXX"
print(len(result["transactions"]))  # 127
```

### Vision AI (high-accuracy bank statements)

```python
import os
from ocr.gemini_bank_ocr import GeminiBankOCR

ocr = GeminiBankOCR(api_key=os.environ["GEMINI_API_KEY"])
result = ocr.extract_pdf("statement.pdf", bank_hint="HDFC")
print(result["transactions"])
```

```python
from ocr.grok_bank_ocr import GrokBankOCR

ocr = GrokBankOCR(api_key=os.environ["GROK_API_KEY"])
result = ocr.extract_pdf("statement.pdf")
```

---

## Configuration

All defaults live in [`config.py`](config.py):

| Setting | Default | Description |
|---|---|---|
| `OCR_MODE` | `"auto"` | `auto` = PaddleOCR then Tesseract fallback; `complex` = PaddleOCR only; `merge` = both engines merged |
| `PADDLE_DEVICE` | `"cpu"` | Set to `"gpu"` for CUDA acceleration |
| `PDF_DPI` | `300` | DPI for PDF-to-image rendering |
| `TESSERACT_LANG` | `"eng"` | Default Tesseract language code |
| `LAYOUT_SCORE_THRESHOLD` | `0.5` | Minimum confidence for layout detection blocks |
| `MAX_PAGES` | `5` | Maximum PDF pages processed per document |

---

## Output Format

All parsers return a consistent JSON envelope. Full annotated examples are in [`examples/`](examples/).

```json
{
  "doc_type":          "...",
  "doc_confidence":    0.92,
  "extraction_method": "digital_pdf | tesseract_ocr | paddle_ocr | gemini_vision",
  "extracted":         { ... }
}
```

### Bank Statement

```json
{
  "doc_type": "bank_statement",
  "doc_confidence": 0.95,
  "extraction_method": "digital_pdf",
  "extracted": {
    "bank_name": "HDFC",
    "account_number": "XXXXXXXXXXXX",
    "account_holder": "Example User",
    "ifsc_code": "HDFC0001234",
    "statement_from": "01/10/2025",
    "statement_to": "31/03/2026",
    "opening_balance": "10000.00",
    "closing_balance": "25000.00",
    "transactions": [
      {
        "date": "05/10/2025",
        "narration": "UPI/CR/123456/EXAMPLE PAYMENT",
        "credit": "5000.00",
        "debit": "",
        "balance": "15000.00"
      }
    ]
  }
}
```

### Aadhaar Card

```json
{
  "doc_type": "aadhaar",
  "doc_confidence": 0.91,
  "extraction_method": "tesseract_ocr",
  "extracted": {
    "aadhaar_number": "XXXX XXXX XXXX",
    "name": "Example Name",
    "date_of_birth": "01/01/1990",
    "gender": "Male",
    "address": "123 Example Street, City",
    "pin_code": "110001",
    "state": "Delhi"
  }
}
```

### PAN Card

```json
{
  "doc_type": "pan_card",
  "doc_confidence": 0.94,
  "extraction_method": "tesseract_ocr",
  "extracted": {
    "pan_number": "ABCDE1234F",
    "name": "EXAMPLE NAME",
    "father_name": "EXAMPLE FATHER NAME",
    "date_of_birth": "01/01/1990",
    "holder_type": "individual"
  }
}
```

### Salary Slip

```json
{
  "doc_type": "salary_slip",
  "doc_confidence": 0.88,
  "extraction_method": "digital_pdf",
  "extracted": {
    "employee_name": "Example Employee",
    "employee_id": "EMP001",
    "month": "March 2026",
    "designation": "Software Engineer",
    "pan": "ABCDE1234F",
    "earnings": {
      "basic": "40000",
      "hra": "16000",
      "da": "2000",
      "special_allowance": "5000"
    },
    "deductions": {
      "pf": "4800",
      "professional_tax": "200",
      "income_tax": "0"
    },
    "gross_salary": "63000",
    "total_deductions": "5000",
    "net_salary": "58000"
  }
}
```

---

## Project Structure

```
DocuSense/
├── app.py                      # Streamlit web UI
├── main.py                     # CLI entry point
├── config.py                   # Global configuration
├── requirements.txt            # Runtime dependencies
├── requirements-dev.txt        # Dev / test dependencies
├── pyproject.toml
│
├── ocr/                        # OCR engine wrappers
│   ├── availability.py         # Runtime engine detection
│   ├── hybrid_runner.py        # Multi-engine routing with confidence fallback
│   ├── paddle_engine.py        # PaddleOCR (10+ Indian scripts)
│   ├── tesseract_engine.py     # Tesseract fallback
│   ├── gemini_bank_ocr.py      # Google Gemini 2.5 Flash Vision extraction
│   └── grok_bank_ocr.py        # xAI Grok Vision extraction
│
├── parsers/                    # Field extractors (one per document type)
│   ├── bank_statement/
│   │   ├── bank_identifier.py  # Bank name detection from OCR text
│   │   ├── bank_parser.py      # Metadata + transaction table extraction
│   │   └── banks/schemas.py    # Per-bank column aliases + date format schemas
│   ├── realestate/             # 19 real estate document parsers
│   │   └── _helpers.py         # Shared helpers: norm_date, parse_amount, extract_parties
│   ├── aadhaar_parser.py
│   ├── pan_parser.py
│   ├── salary_slip_parser.py
│   ├── driving_license_parser.py
│   ├── eshram_parser.py
│   ├── itr_parser.py
│   ├── gst_certificate_parser.py
│   └── ... (20+ more parsers)
│
├── classification/             # Two-phase document type classifier
│   └── doc_classifier.py       # Keyword + structural pattern scoring
│
├── layout/                     # LayoutParser / Detectron2 wrapper
│   └── layout_detector.py
│
├── pipeline/                   # End-to-end document processing orchestrator
│   └── document_pipeline.py
│
├── preprocessing/              # Image preparation
│   └── preprocess.py           # Grayscale, denoise, threshold, deskew
│
├── postprocessing/             # Post-OCR text processing
│   ├── cleaner.py              # Text normalization, table row cleanup
│   ├── language_processor.py   # Language detection + translation
│   ├── multipage.py            # Multi-page table continuation merging
│   └── spatial_table.py        # Table reconstruction from bounding boxes
│
├── table/
│   └── table_extractor.py      # Grid-line-based table cell extraction
│
├── utils/
│   ├── helpers.py              # crop_region, save_json, timestamp_filename
│   ├── image_quality.py        # Sharpness + contrast assessment
│   ├── pdf_extractor.py        # Digital PDF text extraction (pdfplumber)
│   └── pdf_to_image.py         # PDF-to-image rendering (PyMuPDF)
│
├── scripts/
│   ├── batch_run.py            # Batch-process all files in inputs/
│   └── validate_gemini.py      # Gemini extraction accuracy validation
│
├── tests/                      # Pytest test suite
│   ├── test_parsers.py         # Parser + classifier integration tests
│   ├── test_realestate_parsers.py
│   └── test_json_parser.py     # Gemini JSON response parser tests
│
├── examples/                   # Anonymised output examples (JSON)
├── inputs/                     # Place your documents here (gitignored)
└── outputs/                    # Results written here (gitignored)
```

---

## Troubleshooting

### Tesseract not found

```
TesseractNotFoundError: tesseract is not installed or it's not in your PATH
```

**Fix:** Set `TESSERACT_CMD` in your `.env` file:
```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

---

### PaddleOCR model download fails

PaddleOCR downloads model files on first run (~300 MB). If this fails due to network restrictions:

```bash
# Disable PaddleOCR and use Tesseract only
OCR_MODE=tesseract python main.py --input document.pdf
```

---

### Bank statement extracts 0 transactions

1. **Check if it is a digital PDF:** Run `python -c "import pdfplumber; p=pdfplumber.open('statement.pdf'); print(p.pages[0].extract_text()[:200])"` — if text appears, the digital path should work.
2. **Try Vision AI mode:** In the Streamlit UI, toggle "Gemini OCR" for complex or scanned statements.
3. **Check `MAX_PAGES` in `config.py`** — default is 5; increase if your statement has more pages.
4. **Bank not recognized:** Open `parsers/bank_statement/bank_identifier.py` and add your bank's header keywords.

---

### Aadhaar / PAN shows garbled text

- Ensure the Indian language Tesseract packs are installed (`tesseract-ocr-hin`, etc.)
- Use `--mode complex` to force PaddleOCR (better for Indian scripts)
- If the scan is very low quality, try the Gemini Vision AI path

---

### Large PDF is slow

- `MAX_PAGES` in `config.py` caps processing at 5 pages by default — increase as needed
- Use `PADDLE_DEVICE=gpu` if a CUDA GPU is available
- For digital PDFs the pdfplumber fast-path runs in under 1 second per page regardless of page count

---

## Roadmap

### In Progress
- [ ] Credit card statement support (HDFC, ICICI, SBI Card)
- [ ] Form 16 / Form 26AS parser
- [ ] Cheque leaf extraction

### Planned
- [ ] REST API server (`fastapi` wrapper around `DocumentPipeline`)
- [ ] Docker image with all dependencies pre-installed
- [ ] PAN + Aadhaar cross-validation (name/DOB consistency check)
- [ ] Confidence scores per extracted field (not just per document)
- [ ] Support for regional language bank statements (SBI Hindi statements)
- [ ] Webhook / callback support for async processing

### Completed
- [x] 9 Indian bank statement parsers with digital PDF fast-path
- [x] 19 real estate document parsers
- [x] 14 identity and certificate parsers
- [x] Google Gemini 2.5 Flash Vision AI integration
- [x] xAI Grok Vision AI integration
- [x] Streamlit web UI with live JSON preview
- [x] PaddleOCR + Tesseract confidence-based fallback
- [x] 10+ Indian script support (Devanagari, Bengali, Tamil, Telugu, …)
- [x] Multi-page PDF handling with continuation table merging

---

## Contributing

Contributions are very welcome! Ways to help:

- **New parser** — Add a dedicated parser for an unsupported document type
- **Bank schema** — Extend `parsers/bank_statement/banks/schemas.py` for a new bank
- **OCR improvements** — Better preprocessing, deskewing, or confidence tuning
- **Tests** — Add coverage using anonymised / synthetic test data
- **Documentation** — Improve setup guides or add more usage examples

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

> **Privacy rule:** never commit real identity or financial documents.
> Use anonymised or synthetically generated test data only.

---

## Security

DocuSense handles sensitive personal and financial data. Please:

- Never commit documents to the repository — `inputs/` and `outputs/` are gitignored
- Store API keys in `.env`, never in source code
- Use synthetic Aadhaar / PAN numbers in tests (pattern-valid, not real)
- Report security issues privately — see [SECURITY.md](SECURITY.md) for the disclosure policy

---

## FAQ

**Q: Does DocuSense send my documents to any external service?**

Only if you explicitly enable Vision AI mode (Gemini or Grok). The default OCR path (PaddleOCR + Tesseract) runs entirely on your local machine. No data leaves your system unless you opt in to Vision AI.

---

**Q: Can I use DocuSense for Aadhaar/PAN verification?**

DocuSense extracts fields from document images — it does not verify against any government database. It is an OCR/parsing tool, not an identity verification service. For KYC/verification, use the official UIDAI / NSDL APIs.

---

**Q: My bank is not in the supported list. What should I do?**

1. Open `parsers/bank_statement/bank_identifier.py` and add your bank's name + header keywords.
2. Open `parsers/bank_statement/banks/schemas.py` and add a `BankSchema` with column aliases matching your bank's statement format.
3. Test with a sample statement and open a PR — contributions are welcome!

---

**Q: How accurate is the OCR?**

For **digital PDFs** (native-text, not scanned): near-perfect extraction via pdfplumber.

For **scanned documents**: accuracy depends heavily on scan quality. 300 DPI, good lighting, and minimal skew typically yield >95% field-level accuracy. For complex or low-quality scans, the Gemini Vision AI path produces significantly better results.

---

**Q: How do I process documents in bulk?**

```bash
# Copy all documents to inputs/
cp *.pdf inputs/

# Run batch processing
python scripts/batch_run.py

# Results in outputs/, summary in outputs/_batch_summary.json
```

---

**Q: Can I embed DocuSense in my own application?**

Yes — import `DocumentPipeline` directly:

```python
from pipeline.document_pipeline import DocumentPipeline

pipeline = DocumentPipeline()
result = pipeline.process_file("path/to/document.pdf")
```

---

## License

[MIT](LICENSE) © 2026 Anshul Singh

---

## Acknowledgements

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — multilingual OCR engine with Indian script support
- [Tesseract](https://github.com/tesseract-ocr/tesseract) — open-source OCR engine
- [pdfplumber](https://github.com/jsvine/pdfplumber) — digital PDF text and table extraction
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) — high-quality PDF-to-image rendering
- [Streamlit](https://streamlit.io) — web UI framework
- [LayoutParser](https://layout-parser.github.io/) — document layout analysis with Detectron2
- [Google Gemini](https://deepmind.google/technologies/gemini/) — Vision AI for complex document extraction
- [xAI Grok](https://x.ai/) — Vision AI alternative
