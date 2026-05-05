import os
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
if _TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD

# Resolve tessdata: env var → common locations
if not os.environ.get("TESSDATA_PREFIX"):
    _DATA_CANDIDATES = [
        r"C:\Program Files\Tesseract-OCR\tessdata",
        r"C:\Users\hp\miniforge3\share\tessdata",
        "/usr/share/tesseract-ocr/4.00/tessdata",
        "/usr/local/share/tessdata",
    ]
    _tessdata = next((p for p in _DATA_CANDIDATES if os.path.isdir(p)), "")
    if _tessdata:
        os.environ["TESSDATA_PREFIX"] = _tessdata


def run_tesseract(image: np.ndarray) -> list[dict]:
    """
    Returns list of dicts (one per word):
      { "text": str, "confidence": float, "bbox": [x, y, w, h] }
    """
    data = pytesseract.image_to_data(
        image,
        lang=TESSERACT_LANG,
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
