# Examples

This directory contains anonymised JSON output samples showing the structure
returned by DocuSense for each supported document type.

All personal data in these examples is **synthetic** — names, numbers, and
addresses are fabricated and do not correspond to real individuals.

| File | Document Type |
|---|---|
| `bank_statement.json` | HDFC bank statement with transactions |
| `aadhaar.json` | Aadhaar card extraction |
| `pan_card.json` | PAN card extraction |
| `salary_slip.json` | Salary slip with earnings / deduction breakdown |
| `eshram.json` | eShram / UAN card extraction |

## Notes

- All parsers follow the same envelope: `doc_type`, `doc_confidence`,
  `extraction_method`, and `extracted` keys.
- Field availability depends on what is legible in the source document.
- Fields that cannot be extracted are omitted rather than set to `null`.
