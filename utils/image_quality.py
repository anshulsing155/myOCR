"""
Image quality assessment for OCR preprocessing gate.

If an image is already sharp and clean, preprocessing (denoising, contrast
enhancement) would add latency with no benefit and can even introduce
artefacts that hurt OCR accuracy.  This module measures quality and applies
preprocessing only when needed.

Thresholds (tunable via assess_image_quality arguments):
  blur_threshold  — Laplacian variance; > threshold means image is sharp
  noise_threshold — std-dev of high-freq noise layer; < threshold means clean
"""
from __future__ import annotations

import cv2
import numpy as np


def assess_image_quality(
    image: np.ndarray,
    blur_threshold: float = 100.0,
    noise_threshold: float = 8.0,
) -> dict:
    """
    Measure blur and noise of an image.

    Returns:
      blur_score   — Laplacian variance (higher = sharper)
      noise_score  — std-dev of high-frequency noise layer (lower = cleaner)
      quality      — "good" (skip preprocessing) | "poor" (preprocess first)
    """
    if image is None or image.size == 0:
        return {"blur_score": 0.0, "noise_score": 100.0, "quality": "poor"}

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image

    # Blur: Laplacian variance — blurry images have low variance
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # Noise: std-dev of the difference between original and a soft Gaussian blur
    blurred = cv2.GaussianBlur(gray.astype(np.float32), (5, 5), 0)
    noise_score = float(np.std(gray.astype(np.float32) - blurred))

    is_sharp = blur_score >= blur_threshold
    is_clean = noise_score < noise_threshold
    quality = "good" if is_sharp and is_clean else "poor"

    return {
        "blur_score":  round(blur_score, 2),
        "noise_score": round(noise_score, 2),
        "quality":     quality,
    }


def preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
    """
    Enhance a low-quality image before OCR.

    Steps (only applied for poor-quality images):
      1. Non-local means denoising — reduces sensor/scan noise
      2. CLAHE on L channel — restores contrast without over-brightening
    """
    if image.ndim == 2:
        img = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        img = image.copy()

    # Denoising (h=10 is a balanced strength; increase for very noisy scans)
    img = cv2.fastNlMeansDenoisingColored(img, None, h=10, hColor=10,
                                          templateWindowSize=7, searchWindowSize=21)

    # CLAHE contrast enhancement on luminance only
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    lum, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    img = cv2.cvtColor(cv2.merge([clahe.apply(lum), a, b]), cv2.COLOR_LAB2BGR)

    return img


def maybe_preprocess(image: np.ndarray, **quality_kwargs) -> tuple[np.ndarray, dict]:
    """
    Assess quality and preprocess only if needed.

    Returns (processed_image, quality_info).
    Use quality_info["quality"] == "good" to know preprocessing was skipped.
    """
    qi = assess_image_quality(image, **quality_kwargs)
    if qi["quality"] == "poor":
        return preprocess_for_ocr(image), qi
    return image, qi
