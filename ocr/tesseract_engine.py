import os
import shutil

import numpy as np
import pytesseract

from config import TESSERACT_LANG

# Resolve tesseract binary: env var → common install locations → let pytesseract find it
_TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "")
if not _TESSERACT_CMD:
    _CANDIDATES = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\hp\miniforge3\Library\bin\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]
    _TESSERACT_CMD = next((p for p in _CANDIDATES if os.path.exists(p)), "")
    if not _TESSERACT_CMD:
        _TESSERACT_CMD = shutil.which("tesseract") or ""
if _TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD

# Resolve tessdata: env var → common locations
if not os.environ.get("TESSDATA_PREFIX"):
    _DATA_CANDIDATES = [
        r"C:\Program Files\Tesseract-OCR\tessdata",
        r"C:\Users\hp\miniforge3\share\tessdata",
        "/usr/share/tesseract-ocr/4.00/tessdata",
        "/usr/share/tesseract-ocr/5/tessdata",
        "/usr/share/tesseract-ocr/tessdata",
        "/usr/local/share/tessdata",
    ]
    _tessdata = next((p for p in _DATA_CANDIDATES if os.path.isdir(p)), "")
    if _tessdata:
        os.environ["TESSDATA_PREFIX"] = _tessdata


# Mapping from PaddleOCR lang code → Tesseract lang string (always paired with eng)
_TESS_LANG_MAP: dict[str, str] = {
    "hi": "hin+eng",
    "mr": "mar+eng",
    "bn": "ben+eng",
    "ta": "tam+eng",
    "te": "tel+eng",
    "kn": "kan+eng",
    "ml": "mal+eng",
    "gu": "guj+eng",
    "pa": "pan+eng",
    "ur": "urd+eng",
    "or": "ori+eng",
}


def _tess_data(image: np.ndarray, lang: str) -> list[dict]:
    data = pytesseract.image_to_data(
        image,
        lang=lang,
        output_type=pytesseract.Output.DICT,
    )
    results = []
    for i, text in enumerate(data["text"]):
        text = text.strip()
        conf = int(data["conf"][i])
        if not text or conf < 0:
            continue
        results.append({
            "text": text,
            "confidence": round(conf / 100, 4),
            "bbox": [data["left"][i], data["top"][i], data["width"][i], data["height"][i]],
        })
    return results


def run_tesseract(image: np.ndarray) -> list[dict]:
    """Run Tesseract with the configured default language (English)."""
    return _tess_data(image, TESSERACT_LANG)


def run_tesseract_lang(image: np.ndarray, paddle_lang: str) -> list[dict]:
    """
    Run Tesseract with the Indian-script language that corresponds to the given
    PaddleOCR language code.  Falls back to English-only if the lang pack is
    not installed or the call fails.
    """
    tess_lang = _TESS_LANG_MAP.get(paddle_lang, TESSERACT_LANG)
    try:
        return _tess_data(image, tess_lang)
    except Exception:
        return _tess_data(image, TESSERACT_LANG)
