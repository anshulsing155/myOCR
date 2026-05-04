import sys, json
sys.path.insert(0, '.')
from ocr.gemini_bank_ocr import _parse_gemini_json

# Test 1: clean JSON with fences
t1 = "```json\n{\"bank_name\": \"HDFC\", \"transactions\": [{\"date\": \"01/10/2025\", \"narration\": \"UPI\", \"balance\": \"145000.00\"}]}\n```"
r1 = _parse_gemini_json(t1)
print("Test 1 (clean fences):", r1['bank_name'], "txns:", len(r1['transactions']))

# Test 2: truncated mid-string inside narration (no closing fence)
t2 = "```json\n{\"bank_name\": \"HDFC\", \"account_number\": \"50100349626986\", \"transactions\": [{\"date\": \"01/10/2025\", \"narration\": \"UPI-ARJUN\", \"balance\": \"145080.51\"}, {\"date\": \"02/10/2025\", \"narration\": \"TRUNCATED MID"
r2 = _parse_gemini_json(t2)
print("Test 2 (truncated):", r2.get('bank_name'), "txns:", len(r2.get('transactions', [])))
assert r2.get('bank_name') == 'HDFC', f"Expected HDFC, got {r2.get('bank_name')}"
assert len(r2.get('transactions', [])) >= 1, "Expected at least 1 transaction"

# Test 3: no fence, complete JSON
t3 = "{\"bank_name\": \"SBI\", \"transactions\": []}"
r3 = _parse_gemini_json(t3)
print("Test 3 (no fence):", r3['bank_name'])

print("All tests PASSED")
