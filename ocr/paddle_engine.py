import numpy as np
from config import OCR_LANG, PADDLE_USE_ANGLE_CLS, PADDLE_USE_GPU

_ocr = None


def _get_ocr():
    global _ocr
    if _ocr is None:
        from paddleocr import PaddleOCR
        _ocr = PaddleOCR(
            use_angle_cls=PADDLE_USE_ANGLE_CLS,
            lang=OCR_LANG,
            use_gpu=PADDLE_USE_GPU,
            show_log=False,
        )
    return _ocr


def run_paddle(image: np.ndarray) -> list[dict]:
    """
    Returns list of dicts:
      { "text": str, "confidence": float, "bbox": [[x,y], ...] }
    """
    ocr = _get_ocr()
    raw = ocr.ocr(image, cls=PADDLE_USE_ANGLE_CLS)
    results = []
    if not raw or not raw[0]:
        return results
    for line in raw[0]:
        bbox, (text, conf) = line
        results.append({"text": text, "confidence": round(conf, 4), "bbox": bbox})
    return results
