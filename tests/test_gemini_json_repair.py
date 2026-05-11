import sys
sys.path.insert(0, '.')
from ocr.gemini_bank_ocr import _parse_gemini_json

# Simulate truncated response (no closing fence, JSON cut mid-string)
truncated = '```json\n{\n  "bank_name": "HDFC BANK",\n  "account_number": "50100349626986",\n  "transactions": [\n    {"date": "01/10/2025", "narration": "UPI-ARJUN TYAGI", "credit": "45000.00", "balance": "145080.51"},\n    {"date": "02/10/2025", "narration": "TRUNCATED'

result = _parse_gemini_json(truncated)
print("Parsed OK. Keys:", list(result.keys()))
print("Transactions extracted:", len(result.get("transactions", [])))
print("Account:", result.get("account_number"))
print("bank_name:", result.get("bank_name"))
