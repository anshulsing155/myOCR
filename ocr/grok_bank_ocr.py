"""Grok (xAI) powered bank statement OCR.

Uses xAI's OpenAI-compatible API with vision capability.
Returns structured JSON matching the existing pipeline output format.

Usage:
    from ocr.grok_bank_ocr import GrokBankOCR
    ocr = GrokBankOCR(api_key="xai-...")
    result = ocr.extract(images)       # list of BGR numpy arrays
    result = ocr.extract_pdf(pdf_path) # PDF file path
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import time
from typing import Any

import cv2
import numpy as np

# Reuse shared prompt and helpers from gemini module
from ocr.gemini_bank_ocr import (
    _EXTRACT_PROMPT,
    _parse_gemini_json,
    _normalise_result,
    _encode_image,
    _MAX_PAGES,
)

logger = logging.getLogger(__name__)

_XAI_BASE_URL  = "https://api.x.ai/v1"
_GROK_MODEL    = "grok-2-vision-1212"  # vision-capable model


class GrokBankOCR:
    """Grok (xAI) powered bank statement extractor."""

    def __init__(self, api_key: str, model: str = _GROK_MODEL):
        self._api_key = api_key
        self._model   = model
        try:
            import requests  # noqa: F401 — just verify it's available
            self._available = bool(api_key)
        except ImportError:
            logger.error("requests library not available")
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def extract(self, images: list[np.ndarray], bank_hint: str = "") -> dict[str, Any]:
        """Extract bank statement data from a list of BGR numpy arrays."""
        if not self._available:
            return {"error": "GrokBankOCR not available (missing api_key or requests)"}
        if not images:
            return {"error": "No images provided"}

        import requests

        pages = images[:_MAX_PAGES]

        # Build content list: [image, image, ..., text_prompt]
        content: list[dict] = []
        for i, img in enumerate(pages):
            try:
                img_bytes, mime = _encode_image(img)
                b64 = base64.b64encode(img_bytes).decode()
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                })
            except Exception as exc:
                logger.warning("Failed to encode page %d: %s", i + 1, exc)

        if not content:
            return {"error": "All images failed to encode"}

        prompt = _EXTRACT_PROMPT
        if bank_hint:
            prompt += f"\n\nHint: this is a {bank_hint.upper()} bank statement."
        content.append({"type": "text", "text": prompt})

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "max_tokens": 16000,
        }

        t0 = time.perf_counter()
        try:
            resp = requests.post(
                f"{_XAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=300,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as exc:
            body = exc.response.text[:300]
            logger.error("Grok HTTP error %s: %s", exc.response.status_code, body)
            if exc.response.status_code == 403 and "credits" in body.lower():
                return {"error": "No credits on xAI account. Add credits at console.x.ai then retry."}
            if exc.response.status_code == 400 and "not found" in body.lower():
                return {"error": f"Model '{self._model}' not found. Check model name at docs.x.ai"}
            return {"error": f"HTTP {exc.response.status_code}: {body}"}
        except Exception as exc:
            logger.error("Grok API error: %s", exc)
            return {"error": str(exc)}

        elapsed = round(time.perf_counter() - t0, 2)
        logger.info("Grok response: %.2fs | pages=%d", elapsed, len(pages))

        raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not raw_text:
            return {"error": "Empty response from Grok"}

        try:
            raw_json = _parse_gemini_json(raw_text)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Grok JSON: %s\nRaw: %s", exc, raw_text[:500])
            return {"error": f"JSON parse failed: {exc}", "raw_response": raw_text}

        result = _normalise_result(raw_json)
        result["ai_model"]          = self._model
        result["pages_processed"]   = len(pages)
        result["response_time_sec"] = elapsed
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

_instance: GrokBankOCR | None = None


def get_grok_ocr(api_key: str = "") -> GrokBankOCR | None:
    global _instance
    if not api_key:
        api_key = os.environ.get("GROK_API_KEY", "")
    if not api_key:
        return None
    if _instance is None:
        _instance = GrokBankOCR(api_key=api_key)
    return _instance
