import numpy as np
import pytesseract
from config import OCR_LANG


def run_tesseract(image: np.ndarray) -> list[dict]:
    """
    Returns list of dicts (one per word):
      { "text": str, "confidence": float, "bbox": [x, y, w, h] }
    """
    data = pytesseract.image_to_data(
        image,
        lang=OCR_LANG,
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
