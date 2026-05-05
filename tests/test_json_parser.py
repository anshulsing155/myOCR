"""Tests for the Gemini JSON response parser."""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ocr.gemini_bank_ocr import _parse_gemini_json


def test_clean_fenced_json():
    raw = '```json\n{"bank_name": "HDFC", "transactions": [{"date": "01/10/2025"}]}\n```'
    result = _parse_gemini_json(raw)
    assert result["bank_name"] == "HDFC"
    assert len(result["transactions"]) == 1


def test_truncated_response():
    raw = '```json\n{"bank_name": "HDFC", "transactions": [{"date": "01/10/2025", "narration": "UPI"}, {"date": "02/10/2025", "narration": "TRUNC'
    result = _parse_gemini_json(raw)
    assert result.get("bank_name") == "HDFC"
    assert len(result.get("transactions", [])) >= 1


def test_no_fence():
    raw = '{"bank_name": "SBI", "transactions": []}'
    result = _parse_gemini_json(raw)
    assert result["bank_name"] == "SBI"
