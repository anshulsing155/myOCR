"""Validate Gemini extraction — upload HDFC _2.pdf to inputs/ then run this."""
import sys, json, os, glob
sys.path.insert(0, '.')

# Find PDF
candidates = (
    glob.glob("inputs/*.pdf") +
    glob.glob("inputs/**/*.pdf", recursive=True) +
    [r"c:\Users\hp\Desktop\HDFC _2.pdf",
     r"c:\Users\hp\Downloads\HDFC _2.pdf"]
)
pdf_path = next((p for p in candidates if os.path.exists(p)), None)

if not pdf_path:
    print("PDF not found. Copy HDFC _2.pdf into the inputs/ folder and re-run.")
    sys.exit(1)

from ocr.gemini_bank_ocr import GeminiBankOCR
from utils.pdf_to_image import pdf_to_images

print(f"Using: {pdf_path}")
images = pdf_to_images(pdf_path)
print(f"Pages: {len(images)}")

api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    print("Set GEMINI_API_KEY environment variable and re-run.")
    sys.exit(1)
ocr = GeminiBankOCR(api_key=api_key)
result = ocr.extract(images, bank_hint="HDFC")

if "error" in result:
    print(f"ERROR: {result['error']}")
    sys.exit(1)

print(f"Response time: {result.get('response_time_sec')}s\n")

EXPECTED_META = {
    "account_number": "50100349626986",
    "account_holder": "ARJUN TYAGI",
    "ifsc_code":      "HDFC0009671",
    "customer_id":    "139167491",
    "pan":            "BWHPT4999K",
    "statement_from": "01/10/2025",
    "statement_to":   "02/04/2026",
    "closing_balance": "264807.86",
}

print("--- METADATA ---")
all_pass = True
for field, expected in EXPECTED_META.items():
    got = str(result.get(field, "")).strip()
    ok = expected.lower() in got.lower()
    status = "PASS" if ok else "FAIL"
    if not ok: all_pass = False
    print(f"  [{status}] {field:<20} expected={expected:<20} got={got}")

# Transaction spot-checks (ground truth from PDF)
EXPECTED_TXNS = [
    # (date_prefix, type, amount, balance)
    ("01/10/2025", "credit", 45000.00, 145080.51),
    ("02/10/2025", "debit",    320.00, 145400.51),  # UPI-MAMTA (deposit 320)
    ("04/10/2025", "debit",   2000.00, None),        # ACH D-INDIAN CLEARING (any)
    ("04/10/2025", "credit", 100000.00, 230843.51),  # UPI-BINDU TYAGI
    ("04/10/2025", "credit",  40000.00, 270843.51),  # NEFT CR-NIRDOSH
    ("05/10/2025", "debit",    9230.00, 261613.51),  # ACH D-HDFC
    ("05/10/2025", "debit",   16951.00, 244662.51),  # EMI
    ("05/10/2025", "credit",   8500.00, 253162.51),  # UPI-AMRESH
    ("06/10/2025", "credit",  12760.00, 265267.86),  # NEFT ITDTAX
    ("06/10/2025", "debit",      40.00, 264807.86),  # UPI-PINKI (last)
]

print("\n--- TRANSACTION SPOT-CHECKS ---")
txns = result.get("transactions", [])
print(f"  Extracted: {len(txns)}  Expected: 27")
for date, typ, amt, bal in EXPECTED_TXNS:
    col = "credit" if typ == "credit" else "debit"
    match = next(
        (t for t in txns
         if t.get("date", "").startswith(date[:8])
         and abs(float(t.get(col, "0") or 0) - amt) < 1.0),
        None
    )
    if match:
        bal_ok = True
        if bal is not None:
            bal_ok = abs(float(match.get("balance", "0") or 0) - bal) < 1.0
        status = "PASS" if bal_ok else "FAIL (bal)"
        if not bal_ok: all_pass = False
        print(f"  [{status}] {date} {typ} {amt:>12.2f}  bal={match.get('balance')}")
    else:
        all_pass = False
        print(f"  [FAIL] {date} {typ} {amt:>12.2f}  — NOT FOUND")

print(f"\n{'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED'}")

# Save result
with open("outputs/_validation_result.json", "w") as f:
    json.dump(result, f, indent=2)
print("Full result saved to outputs/_validation_result.json")
