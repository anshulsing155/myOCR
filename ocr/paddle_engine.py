import logging
import traceback
import threading

import cv2
import numpy as np
from config import OCR_LANG, PADDLE_USE_ANGLE_CLS, PADDLE_DEVICE
from ocr.availability import paddle_available

logger = logging.getLogger(__name__)

_ocr = None
_init_failed = False           # True only after init fails; prevents re-init loops
_predict_lock = threading.Lock()  # PaddleOCR is not thread-safe in Streamlit
_consecutive_failures = 0
_MAX_CONSECUTIVE_FAILURES = 3  # Permanently disable after this many predict failures


def _get_ocr():
    global _ocr, _init_failed
    if _init_failed:
        return None
    if not paddle_available():
        _init_failed = True
        logger.info("PaddleOCR is not installed in this environment; using fallback OCR.")
        return None
    if _ocr is None:
        try:
            from paddleocr import PaddleOCR
            _ocr = PaddleOCR(
                lang=OCR_LANG,
                use_doc_orientation_classify=PADDLE_USE_ANGLE_CLS,
                use_doc_unwarping=False,
                device=PADDLE_DEVICE,
            )
        except Exception as exc:
            logger.warning("PaddleOCR failed to initialize: %s", exc)
            _init_failed = True
            return None
    return _ocr


# PaddleOCR's C++ text-detection predictor crashes ("Unknown exception") on
# very large images (e.g. A4 at 300 DPI = 2480×3509 px).  Cap at 1920 px on
# the long edge — still ~230 DPI, well above OCR quality requirements.
_MAX_PADDLE_DIM = 1920


def _ensure_bgr(image: np.ndarray) -> np.ndarray:
    """PaddleOCR v3 expects a 3-channel uint8 BGR numpy array, max 1920 px."""
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.ndim == 3 and image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    # Enforce uint8 — float images (0.0–1.0) must be scaled first
    if image.dtype != np.uint8:
        if image.max() <= 1.0:
            image = (image * 255).clip(0, 255).astype(np.uint8)
        else:
            image = image.clip(0, 255).astype(np.uint8)
    # Resize if the longest dimension exceeds the safe limit
    h, w = image.shape[:2]
    if max(h, w) > _MAX_PADDLE_DIM:
        scale = _MAX_PADDLE_DIM / max(h, w)
        image = cv2.resize(image, (int(w * scale), int(h * scale)),
                           interpolation=cv2.INTER_AREA)
    return image


def run_paddle(image: np.ndarray) -> list[dict]:
    """
    Returns list of dicts:
      { "text": str, "confidence": float, "bbox": [[x,y], ...] }
    Returns [] (no exception) when PaddleOCR is unavailable.
    """
    global _init_failed, _ocr, _consecutive_failures
    ocr = _get_ocr()
    if ocr is None:
        return []
    try:
        img = _ensure_bgr(image)
        with _predict_lock:
            raw = ocr.predict(img)
            # PaddleOCR 3.x predict() may return a generator — materialise it
            if not isinstance(raw, list):
                raw = list(raw)
        result = _parse_result(raw)
        _consecutive_failures = 0   # reset on success
        return result
    except Exception as exc:
        _consecutive_failures += 1
        logger.warning(
            "PaddleOCR predict failed (%d/%d): %s\n%s",
            _consecutive_failures, _MAX_CONSECUTIVE_FAILURES,
            exc, traceback.format_exc(),
        )
        # Predict failures are image-specific — don't permanently disable
        # PaddleOCR for the session.  Tesseract fallback handles this image;
        # PaddleOCR remains available for subsequent images.
        return []


_CONSONANTS = frozenset("bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ")


def _has_consonant_run(text: str, min_run: int = 5) -> bool:
    """Return True if text has ≥min_run consecutive consonants — impossible in real English."""
    run = 0
    for c in text:
        if c in _CONSONANTS:
            run += 1
            if run >= min_run:
                return True
        else:
            run = 0
    return False


def _ocr_noise_ratio(results: list[dict]) -> float:
    """
    Estimate the fraction of results that look like garbled non-Latin OCR.
    English OCR on Devanagari/Tamil/etc. produces sequences like
    "SHRGTRCTR", "af 3en", "HRT" — high consonant density, low vowel ratio,
    short fragments, lots of OCR noise characters.
    Returns 0.0 (clean) … 1.0 (all garbage).
    """
    if not results:
        return 0.0
    noise_count = 0
    for r in results:
        text = r.get("text", "").strip()
        if not text or len(text) < 2:
            continue
        alpha = [c for c in text if c.isalpha() and c.isascii()]
        if not alpha:
            continue
        vowels = sum(1 for c in alpha if c.lower() in "aeiou")
        consonants = len(alpha) - vowels
        vowel_ratio = vowels / len(alpha)
        conf = r.get("confidence", 1.0)
        # Garbled Devanagari: very few vowels, many consonants, low confidence
        if vowel_ratio < 0.1 and consonants >= 4 and conf < 0.85:
            noise_count += 1
    return noise_count / len(results)


def _detect_script_from_image(image: np.ndarray) -> str | None:
    """
    Lightweight image-level script detection using pixel distribution.
    Indian scripts have characteristic connected-component densities.
    Returns a PaddleOCR lang code ('hi', 'ta', etc.) or None if Latin.

    Strategy: run a tiny Tesseract OSD (orientation+script detection)
    if available, otherwise fall back to None (use noise-ratio heuristic).
    """
    try:
        import pytesseract
        osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
        script = osd.get("script", "").lower()
        _OSD_MAP = {
            "devanagari": "hi",
            "bengali":    "bn",
            "tamil":      "ta",
            "telugu":     "te",
            "kannada":    "kn",
            "malayalam":  "ml",
            "gujarati":   "gu",
            "gurmukhi":   "pa",
        }
        return _OSD_MAP.get(script)
    except Exception:
        return None


def _merge_ocr_results(
    english: list[dict],
    regional: list[dict],
    iou_threshold: float = 0.3,
) -> list[dict]:
    """
    Merge English and Regional OCR results for bilingual documents (e.g. Aadhaar).

    Strategy:
    - For each regional result, if it overlaps significantly with an English
      result that has LOW confidence (< 0.75), replace with regional result.
    - English-only results (no overlap with regional) are kept as-is.
    - Regional results with no overlap added as new items.

    This preserves English text (account numbers, names in Latin) while
    replacing garbled Devanagari with proper Hindi OCR.
    """
    def _bbox_xyxy(bbox) -> tuple[float, float, float, float] | None:
        if not bbox:
            return None
        try:
            if isinstance(bbox[0], (list, tuple)):
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                return min(xs), min(ys), max(xs), max(ys)
            if len(bbox) == 4:
                x1, y1, x2, y2 = bbox
                if x2 > x1 and y2 > y1:
                    return x1, y1, x2, y2
        except Exception:
            pass
        return None

    def _iou(a, b) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0
        inter = (ix2 - ix1) * (iy2 - iy1)
        area_a = (ax2 - ax1) * (ay2 - ay1)
        area_b = (bx2 - bx1) * (by2 - by1)
        union = area_a + area_b - inter
        return inter / union if union > 0 else 0.0

    merged = list(english)
    english_boxes = [_bbox_xyxy(r.get("bbox")) for r in english]
    used_regional: set[int] = set()

    for i, eng in enumerate(merged):
        ea = english_boxes[i]
        if ea is None:
            continue
        if eng.get("confidence", 1.0) >= 0.75:
            continue  # English result is good, keep it
        # Find best-overlapping regional result
        best_j, best_iou = -1, iou_threshold
        for j, reg in enumerate(regional):
            if j in used_regional:
                continue
            ra = _bbox_xyxy(reg.get("bbox"))
            if ra is None:
                continue
            score = _iou(ea, ra)
            if score > best_iou:
                best_iou, best_j = score, j
        if best_j >= 0:
            merged[i] = regional[best_j]
            used_regional.add(best_j)

    # Append regional results that had no English overlap (new lines)
    for j, reg in enumerate(regional):
        if j not in used_regional:
            merged.append(reg)

    return merged


def run_paddle_multilingual(image: np.ndarray) -> tuple[list[dict], str | None]:
    """
    Smart multilingual OCR for Indian documents.

    Detection strategy (in order):
      1. Tesseract OSD script detection (image-level, most reliable)
      2. English OCR noise ratio heuristic (garbled Devanagari → high noise)
      3. Unicode script chars in OCR output (visible Indian chars)

    For bilingual documents (Aadhaar, PAN, etc.) that mix Hindi + English,
    we merge both OCR passes: English results for Latin text, regional results
    for Indian-script text.

    Returns (merged_ocr_results, detected_lang_code_or_None).
    """
    from postprocessing.language_processor import detect_script, detect_language

    # First pass: English model
    english_results = run_paddle(image)
    if not english_results:
        return [], None

    # ── Script detection (image-level first) ──────────────────────────────────
    detected_lang = _detect_script_from_image(image)

    if detected_lang is None:
        # Heuristic 1: noise ratio (vowel-poor words with low confidence)
        noise = _ocr_noise_ratio(english_results)
        if noise >= 0.15:
            detected_lang = "hi"
            logger.debug("Noise ratio %.2f → assuming Indian script", noise)

    if detected_lang is None:
        # Heuristic 2: long consonant run (e.g. "SHRGTRCTR") — impossible in English
        combined_text = " ".join(r.get("text", "") for r in english_results)
        if _has_consonant_run(combined_text, min_run=5):
            detected_lang = "hi"
            logger.debug("Long consonant run detected → assuming Indian script")

    if detected_lang is None:
        # Heuristic 3: Unicode Indian-script chars visible in text
        combined = " ".join(r.get("text", "") for r in english_results)
        script, paddle_code = detect_script(combined)
        if script:
            lang, lang_conf = detect_language(combined)
            detected_lang = lang if lang_conf >= 0.3 else paddle_code

    # Heuristic 4 (low avg confidence) removed: it triggered Hindi OCR on blurry
    # English documents (bank statements, salary slips) causing degraded results.
    # The three heuristics above (OSD + noise ratio + consonant run) already cover
    # all real Indian-script cases reliably.

    if detected_lang is None:
        return english_results, None

    # ── Regional OCR pass (Tesseract avoids dual-Paddle-instance conflict) ────
    from ocr.tesseract_engine import run_tesseract_lang
    regional_results = run_tesseract_lang(image, detected_lang)
    if not regional_results:
        return english_results, detected_lang

    # ── Merge: keep English text, replace garbled parts with regional ─────────
    # Check if regional OCR also found any visible Indian-script chars
    regional_text = " ".join(r.get("text", "") for r in regional_results)
    _, regional_paddle = detect_script(regional_text)

    if regional_paddle:
        # Truly bilingual output from regional model — do full merge
        merged = _merge_ocr_results(english_results, regional_results)
        # Re-detect language from merged regional text
        lang, lang_conf = detect_language(regional_text)
        if lang_conf >= 0.3:
            detected_lang = lang
        return merged, detected_lang
    else:
        # Regional model gave only Latin/digits (couldn't read the script either).
        # This means the document is actually in English — reset detected_lang so
        # the language processor doesn't incorrectly tag it as Hindi/regional.
        # Prefer whichever pass has higher average confidence.
        avg_en = sum(r["confidence"] for r in english_results) / len(english_results)
        avg_re = sum(r["confidence"] for r in regional_results) / len(regional_results)
        return (regional_results if avg_re > avg_en else english_results), None


def _parse_result(raw) -> list[dict]:
    """Handle both v2 (list-of-lists) and v3 (OCRResult objects / generators)."""
    results = []
    if raw is None:
        return results
    # Materialise any generator so we can index safely
    if not isinstance(raw, list):
        try:
            raw = list(raw)
        except Exception:
            return results
    if not raw:
        return results

    first = raw[0]
    if first is None:
        return results

    if isinstance(first, list):
        for line in first:
            if not line or len(line) != 2:
                continue
            bbox, text_conf = line
            if isinstance(text_conf, (list, tuple)) and len(text_conf) == 2:
                text, conf = text_conf
                results.append({
                    "text": str(text),
                    "confidence": round(float(conf), 4),
                    "bbox": bbox,
                })
        return results

    # v3 format: list of OCRResult objects
    for item in raw:
        if item is None:
            continue
        if isinstance(item, dict):
            _extract_v3_dict(item, results)
        elif hasattr(item, "rec_texts"):
            polys  = getattr(item, "dt_polys",   []) or []
            texts  = getattr(item, "rec_texts",  []) or []
            scores = getattr(item, "rec_scores", []) or []
            for text, conf, bbox in zip(texts, scores, polys):
                bbox_list = bbox.tolist() if hasattr(bbox, "tolist") else list(bbox)
                results.append({
                    "text": str(text),
                    "confidence": round(float(conf), 4),
                    "bbox": bbox_list,
                })
        else:
            try:
                for sub in item:
                    if sub and len(sub) == 2:
                        bbox, (text, conf) = sub
                        results.append({
                            "text": str(text),
                            "confidence": round(float(conf), 4),
                            "bbox": bbox,
                        })
            except (TypeError, ValueError):
                pass

    return results


def _extract_v3_dict(item: dict, results: list) -> None:
    texts  = item.get("rec_texts") or item.get("text", [])
    scores = item.get("rec_scores") or item.get("confidence", [])
    polys  = item.get("dt_polys") or item.get("bbox", [])
    if isinstance(texts, str):
        results.append({
            "text": texts,
            "confidence": round(float(scores) if scores else 0.0, 4),
            "bbox": polys,
        })
        return
    for text, conf, bbox in zip(texts, scores, polys):
        bbox_list = bbox.tolist() if hasattr(bbox, "tolist") else list(bbox)
        results.append({
            "text": str(text),
            "confidence": round(float(conf), 4),
            "bbox": bbox_list,
        })
