import numpy as np
from config import OCR_MODE
from ocr.paddle_engine import run_paddle
from ocr.tesseract_engine import run_tesseract

CONFIDENCE_THRESHOLD = 0.7


def run_ocr(image: np.ndarray, mode: str = OCR_MODE) -> list[dict]:
    """
    mode="auto"       — try Paddle; fall back to Tesseract if avg confidence is low
    mode="complex"    — Paddle only
    mode="tesseract"  — Tesseract only
    mode="merge"      — run both, keep higher-confidence result per region
    """
    if mode == "complex":
        return run_paddle(image)
    if mode == "tesseract":
        return run_tesseract(image)
    if mode == "merge":
        return _merge(image)
    # auto
    results = run_paddle(image)
    if _avg_confidence(results) < CONFIDENCE_THRESHOLD:
        results = run_tesseract(image)
    return results


def _avg_confidence(results: list[dict]) -> float:
    if not results:
        return 0.0
    return sum(r["confidence"] for r in results) / len(results)


def _merge(image: np.ndarray) -> list[dict]:
    """Run both engines; return whichever has higher average confidence."""
    paddle_results = run_paddle(image)
    tess_results = run_tesseract(image)
    if _avg_confidence(paddle_results) >= _avg_confidence(tess_results):
        return paddle_results
    return tess_results
