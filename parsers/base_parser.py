"""Abstract base class for all document parsers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseParser(ABC):
    @abstractmethod
    def parse(self, ocr_results: list[dict], **kwargs) -> dict[str, Any]:
        """
        Args:
            ocr_results: list of {text, confidence, bbox} dicts
            **kwargs: extra context passed by the pipeline

        Returns:
            Structured dict — must always include {"doc_type": str}
        """
