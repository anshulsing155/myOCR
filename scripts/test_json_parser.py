"""
Quick sanity-check for the Gemini JSON parser (no API key needed).

Usage:
    python scripts/test_json_parser.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ocr.gemini_bank_ocr import _parse_gemini_json


def run_tests() -> None:
    # Clean JSON with markdown fences
    t1 = '```json\n{"bank_name": "HDFC", "transactions": [{"date": "01/10/2025", "narration": "UPI", "balance": "145000.00"}]}\n```'
    r1 = _parse_gemini_json(t1)
    assert r1["bank_name"] == "HDFC", f"Test 1 failed: {r1}"
    assert len(r1["transactions"]) == 1
    print("PASS  Test 1: clean fences")

    # Truncated mid-string (no closing fence)
    t2 = '```json\n{"bank_name": "HDFC", "account_number": "50100349626986", "transactions": [{"date": "01/10/2025", "narration": "UPI-ARJUN", "balance": "145080.51"}, {"date": "02/10/2025", "narration": "TRUNCATED MID'
    r2 = _parse_gemini_json(t2)
    assert r2.get("bank_name") == "HDFC", f"Test 2 failed: {r2}"
    assert len(r2.get("transactions", [])) >= 1
    print("PASS  Test 2: truncated response")

    # No fence, complete JSON
    t3 = '{"bank_name": "SBI", "transactions": []}'
    r3 = _parse_gemini_json(t3)
    assert r3["bank_name"] == "SBI"
    print("PASS  Test 3: no fence")

    print("\nAll tests passed.")


if __name__ == "__main__":
    run_tests()
