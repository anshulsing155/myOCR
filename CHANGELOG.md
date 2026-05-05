# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

## [1.0.0] — 2026-05-05

### Added
- Multi-engine OCR pipeline: PaddleOCR v3 + Tesseract with confidence-based fallback
- Support for 10+ Indian scripts (Devanagari, Bengali, Tamil, Telugu, Kannada, Malayalam, Gujarati, Punjabi, Odia, Urdu)
- Vision AI integration: Google Gemini 2.5 Flash and xAI Grok for bank statement extraction
- Document classification with two-phase scoring (keyword + structural patterns)
- Parsers for: Bank Statement, PAN Card, Aadhaar, Driving Licence, eShram, ITR, Salary Slip, Generic
- Bank identification and schema mapping for 9 Indian banks (HDFC, SBI, ICICI, Axis, Kotak, PNB, Bank of Baroda, Canara, IndusInd)
- Spatial table reconstruction from raw OCR bounding boxes
- Multi-page PDF handling with continuation table merging
- Digital PDF extraction path via pdfplumber (no OCR for native-text PDFs)
- Language detection, script identification, and Google Translate integration
- Streamlit web UI with drag-and-drop upload and live JSON preview
- CLI (`main.py`) for headless/scripted processing
- Image quality assessment to conditionally skip preprocessing
