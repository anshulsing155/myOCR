# Contributing to myOCR

Thank you for your interest in contributing! This document covers how to add new parsers, banks, OCR engines, and other improvements.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Adding a New Document Parser](#adding-a-new-document-parser)
- [Adding a New Bank](#adding-a-new-bank)
- [Code Style](#code-style)
- [Submitting a Pull Request](#submitting-a-pull-request)

---

## Getting Started

1. Fork the repository and clone your fork
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes (see guidelines below)
4. Push and open a pull request against `main`

## Development Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## How to Contribute

- **Bug fixes** — open an issue first if the fix is non-trivial
- **New document types** — follow the parser pattern below
- **New banks** — add schema to `parsers/bank_statement/banks/schemas.py`
- **OCR improvements** — add engine wrappers under `ocr/`
- **Documentation** — always welcome

---

## Adding a New Document Parser

1. Create `parsers/my_doc_parser.py` inheriting from `BaseParser`:

```python
from parsers.base_parser import BaseParser

class MyDocParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict:
        text = " ".join(r["text"] for r in ocr_results)
        return {
            "doc_type": "my_doc",
            "field_name": self._extract_field(text),
            "raw_text": text,
        }
```

2. Register the doc type in `classification/doc_classifier.py` — add keyword patterns to `KEYWORD_SCORES`.

3. Wire up the parser in `pipeline/document_pipeline.py` — add a branch in the `process()` method.

4. Export from `parsers/__init__.py`.

---

## Adding a New Bank

Edit `parsers/bank_statement/banks/schemas.py` and add a new entry to `BANK_SCHEMAS`:

```python
"MY_BANK": BankSchema(
    name="My Bank",
    col_aliases={
        "date":        ["transaction date", "txn date", "value date"],
        "narration":   ["description", "particulars"],
        "debit":       ["withdrawal", "dr amount"],
        "credit":      ["deposit", "cr amount"],
        "balance":     ["closing balance", "running balance"],
    },
    meta_patterns={
        "account_number": [r"A/c\s*No\.?\s*[:\-]?\s*(\d[\d\s]+\d)"],
        "ifsc_code":      [r"IFSC\s*[:\-]?\s*([A-Z]{4}0[A-Z0-9]{6})"],
    },
),
```

Then add the bank keyword list in `parsers/bank_statement/bank_identifier.py`.

---

## Code Style

- **Python 3.10+** type hints on all public functions
- **No inline comments** unless the logic is non-obvious
- **No docstring novels** — one short line max per function if needed
- Keep each module focused; avoid cross-cutting concerns
- Do not hardcode paths — use environment variables or `config.py`

---

## Submitting a Pull Request

- Keep PRs focused — one feature or fix per PR
- Include a clear description of what changed and why
- If you changed parsing logic, include a sample input and the expected JSON output in the PR description
- Do not commit files from `inputs/` or `outputs/` — they may contain personal data
