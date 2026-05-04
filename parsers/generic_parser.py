"""Fallback parser for invoice, salary slip, property documents, or unknown types."""
from __future__ import annotations

from typing import Any

from parsers.base_parser import BaseParser


class GenericParser(BaseParser):
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        texts = [
            r.get("text", "").strip()
            for r in ocr_results
            if r.get("text", "").strip()
        ]
        return {
            "doc_type": kwargs.get("doc_type", "other"),
            "raw_text": "\n".join(texts),
            "text_items": texts,
        }
