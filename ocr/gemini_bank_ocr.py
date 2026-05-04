"""Gemini-powered bank statement OCR.

Sends page images to Gemini Vision and returns structured JSON matching
the existing pipeline output format (account metadata + transactions table).

Usage:
    from ocr.gemini_bank_ocr import GeminiBankOCR
    ocr = GeminiBankOCR(api_key="...")
    result = ocr.extract(images)          # list of BGR numpy arrays
    result = ocr.extract_pdf(pdf_path)    # PDF file path
"""
from __future__ import annotations

import base64
import json
import logging
import re
import tempfile
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_GEMINI_MODEL = "gemini-2.5-flash"
_MAX_PAGES = 20  # Gemini handles up to 20 images well in one call

_EXTRACT_PROMPT = """\
You are a bank statement OCR expert. Analyse every page image provided and extract the following as valid JSON.

Return ONLY a JSON object with this exact structure (omit fields you cannot find):
{
  "bank_name": "...",
  "account_number": "...",
  "account_holder": "...",
  "ifsc_code": "...",
  "branch": "...",
  "statement_from": "DD/MM/YYYY",
  "statement_to": "DD/MM/YYYY",
  "opening_balance": "123456.78",
  "closing_balance": "123456.78",
  "customer_id": "...",
  "pan": "...",
  "mobile": "...",
  "transactions": [
    {
      "date": "DD/MM/YYYY",
      "narration": "...",
      "chq_ref": "...",
      "debit": "0.00",
      "credit": "0.00",
      "balance": "0.00"
    }
  ]
}

Rules:
- Extract ALL transactions visible across all pages — do not truncate.
- Dates must be DD/MM/YYYY. Convert "01 Jan 2024" → "01/01/2024".

CRITICAL — Indian number format:
  Indian bank statements use comma as a THOUSANDS SEPARATOR, NOT as a decimal point.
  Examples: "45,000.00" = 45000.00 (forty-five thousand)
            "1,40,000.00" = 140000.00 (one lakh forty thousand)
            "2,64,807.86" = 264807.86
            "1,45,080.51" = 145080.51
  The period (.) is ALWAYS the decimal separator.
  Output amounts as plain decimals — remove ALL commas, keep ALL digits before and after the decimal.
  NEVER truncate digits. "45,000.00" must become "45000.00", NOT "45.00".
  If a cell is blank/empty output "".

- narration: full transaction description text exactly as printed (may span multiple lines in PDF — join them).
- chq_ref: cheque number or UTR/reference number shown in that column, else "".
- Do NOT split one transaction row into multiple JSON objects.
- account_number: copy every digit exactly — do not shorten or guess.
- opening_balance: the balance BEFORE the first transaction. If not shown explicitly, leave it out.
- closing_balance: the balance on the LAST transaction row.
- pan: look for a 10-character alphanumeric code like BWHPT4999K in narrations or account details.
- Do NOT invent fields that are not visible in the document (e.g. mobile number).
- Return valid parseable JSON only. No markdown fences, no commentary.
"""


def _encode_image(img: np.ndarray, max_dim: int = 2400) -> tuple[bytes, str]:
    """Resize if huge, encode as PNG (lossless) for digit accuracy. Returns (png_bytes, mime_type)."""
    h, w = img.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LANCZOS4)
    ok, buf = cv2.imencode(".png", img, [cv2.IMWRITE_PNG_COMPRESSION, 1])
    if not ok:
        raise ValueError("Failed to encode image as PNG")
    return buf.tobytes(), "image/png"


def _parse_gemini_json(text: str) -> dict:
    """Extract JSON from Gemini response (strips markdown fences; repairs truncation)."""
    text = text.strip()

    # Strip opening ```json fence (with or without closing fence)
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text)
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Response may be truncated mid-string (e.g. inside a long narration).
    # Scan backwards over every } and try to close + parse from there.
    # The first position from the end that yields valid JSON is returned.
    positions = [i for i, c in enumerate(text) if c == "}"]
    for pos in reversed(positions):
        candidate = text[: pos + 1]
        open_b  = candidate.count("[") - candidate.count("]")
        open_br = candidate.count("{") - candidate.count("}")
        if open_b < 0 or open_br < 0:
            continue
        candidate += "]" * open_b + "}" * open_br
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise json.JSONDecodeError("Could not parse Gemini response", text, 0)


def _normalise_amount(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).replace(",", "").strip()
    # Keep only digits and one decimal point
    s = re.sub(r"[^\d\.]", "", s)
    return s


def _normalise_result(raw: dict) -> dict:
    """Clean up Gemini output to match pipeline conventions."""
    result = {"doc_type": "bank_statement"}

    scalar_fields = [
        "bank_name", "account_number", "account_holder", "ifsc_code",
        "branch", "statement_from", "statement_to", "customer_id", "pan", "mobile",
    ]
    for f in scalar_fields:
        if raw.get(f):
            result[f] = str(raw[f]).strip()

    for bal in ("opening_balance", "closing_balance"):
        if raw.get(bal):
            result[bal] = _normalise_amount(raw[bal])

    transactions = raw.get("transactions") or []
    cleaned = []
    for txn in transactions:
        if not isinstance(txn, dict):
            continue
        row: dict[str, str] = {}
        for k, v in txn.items():
            key = k.lower().strip().replace(" ", "_")
            val = str(v).strip() if v is not None else ""
            # Normalise amount columns
            if key in ("debit", "credit", "balance", "withdrawal", "deposit"):
                val = _normalise_amount(v)
            row[key] = val
        if any(row.values()):
            cleaned.append(row)

    if cleaned:
        result["transactions"] = cleaned
        result["transaction_count"] = len(cleaned)

    return result


class GeminiBankOCR:
    """Gemini-powered bank statement extractor."""

    def __init__(self, api_key: str, model: str = _GEMINI_MODEL):
        try:
            import google.genai as genai
            from google.genai import types as genai_types
            self._client = genai.Client(api_key=api_key)
            self._types = genai_types
            self._model = model
            self._available = True
        except ImportError:
            logger.error("google-genai not installed. Run: pip install google-genai")
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def extract(self, images: list[np.ndarray], bank_hint: str = "") -> dict[str, Any]:
        """Extract bank statement data from a list of BGR numpy arrays."""
        if not self._available:
            return {"error": "google-genai not available"}
        if not images:
            return {"error": "No images provided"}

        pages = images[:_MAX_PAGES]
        parts: list = []

        for i, img in enumerate(pages):
            try:
                img_bytes, mime = _encode_image(img)
                parts.append(
                    self._types.Part.from_bytes(data=img_bytes, mime_type=mime)
                )
            except Exception as exc:
                logger.warning("Failed to encode page %d: %s", i + 1, exc)

        if not parts:
            return {"error": "All images failed to encode"}

        prompt = _EXTRACT_PROMPT
        if bank_hint:
            prompt += f"\n\nHint: this is a {bank_hint.upper()} bank statement."
        parts.append(prompt)

        import time as _time
        _t0 = _time.perf_counter()
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=parts,
                config=self._types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=65536,
                    thinking_config=self._types.ThinkingConfig(thinking_budget=0),
                ),
            )
            raw_text = response.text
        except Exception as exc:
            logger.error("Gemini API error: %s", exc)
            return {"error": str(exc)}
        _elapsed = round(_time.perf_counter() - _t0, 2)
        logger.info("Gemini response: %.2fs | pages=%d", _elapsed, len(pages))

        try:
            raw_json = _parse_gemini_json(raw_text)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Gemini JSON: %s\nRaw: %s", exc, raw_text[:500])
            return {"error": f"JSON parse failed: {exc}", "raw_response": raw_text}

        result = _normalise_result(raw_json)
        result["gemini_model"] = self._model
        result["pages_processed"] = len(pages)
        result["response_time_sec"] = _elapsed
        return result

    def extract_pdf(self, pdf_path: str, bank_hint: str = "") -> dict[str, Any]:
        """Extract bank statement data from a PDF file."""
        from utils.pdf_to_image import pdf_to_images
        try:
            images = pdf_to_images(pdf_path)
        except Exception as exc:
            return {"error": f"PDF rendering failed: {exc}"}
        return self.extract(images, bank_hint=bank_hint)


# ── Singleton factory ─────────────────────────────────────────────────────────

_instance: GeminiBankOCR | None = None


def get_gemini_ocr(api_key: str = "") -> GeminiBankOCR | None:
    """Return a cached GeminiBankOCR instance, or None if no API key."""
    global _instance
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None
    if _instance is None or not _instance.available:
        _instance = GeminiBankOCR(api_key=api_key)
    return _instance
