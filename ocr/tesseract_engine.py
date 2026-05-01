import os
import numpy as np
import pytesseract
from config import TESSERACT_LANG

# Point pytesseract at the conda-installed binary if it isn't already on PATH
_CONDA_TESS = r"C:\Users\hp\miniforge3\Library\bin\tesseract.exe"
if os.path.exists(_CONDA_TESS):
    pytesseract.pytesseract.tesseract_cmd = _CONDA_TESS

# Tell Tesseract where its language data lives
_CONDA_TESSDATA = r"C:\Users\hp\miniforge3\share\tessdata"
if os.path.isdir(_CONDA_TESSDATA) and not os.environ.get("TESSDATA_PREFIX"):
    os.environ["TESSDATA_PREFIX"] = _CONDA_TESSDATA


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
