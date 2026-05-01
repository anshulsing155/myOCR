import cv2
import numpy as np
from config import OCR_LANG, PADDLE_USE_ANGLE_CLS, PADDLE_DEVICE

_ocr = None


def _get_ocr():
    global _ocr
    if _ocr is None:
        from paddleocr import PaddleOCR
        # use_doc_unwarping=False: we already deskew; unwarping model requires 3-ch and
        # would crash on any grayscale crop passed from our preprocessing pipeline.
        _ocr = PaddleOCR(
            lang=OCR_LANG,
            use_doc_orientation_classify=PADDLE_USE_ANGLE_CLS,
            use_doc_unwarping=False,
            device=PADDLE_DEVICE,
        )
    return _ocr


def _ensure_bgr(image: np.ndarray) -> np.ndarray:
    """PaddleOCR v3 always expects a 3-channel BGR image."""
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image


def run_paddle(image: np.ndarray) -> list[dict]:
    """
    Returns list of dicts:
      { "text": str, "confidence": float, "bbox": [[x,y], ...] }
    Compatible with PaddleOCR v2 and v3.
    """
    ocr = _get_ocr()
    raw = ocr.predict(_ensure_bgr(image))  # use predict() directly; ocr() is deprecated in v3
    return _parse_result(raw)


def _parse_result(raw) -> list[dict]:
    """Handle both v2 (list-of-lists) and v3 (OCRResult objects) return formats."""
    results = []
    if not raw:
        return results

    # v2 format: [[  [bbox, (text, conf)], ... ]]
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
        # dict-like (some v3 builds return plain dicts)
        if isinstance(item, dict):
            _extract_v3_dict(item, results)
        # attribute-based OCRResult
        elif hasattr(item, "rec_texts"):
            polys = getattr(item, "dt_polys", []) or []
            texts = getattr(item, "rec_texts", []) or []
            scores = getattr(item, "rec_scores", []) or []
            for text, conf, bbox in zip(texts, scores, polys):
                bbox_list = bbox.tolist() if hasattr(bbox, "tolist") else list(bbox)
                results.append({
                    "text": str(text),
                    "confidence": round(float(conf), 4),
                    "bbox": bbox_list,
                })
        # fallback: try iterating sub-items
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
    texts = item.get("rec_texts") or item.get("text", [])
    scores = item.get("rec_scores") or item.get("confidence", [])
    polys = item.get("dt_polys") or item.get("bbox", [])
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
