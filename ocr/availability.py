from __future__ import annotations

import importlib.util
import os
import shutil


def paddle_available() -> bool:
    return importlib.util.find_spec("paddleocr") is not None


def tesseract_available() -> bool:
    env_cmd = os.environ.get("TESSERACT_CMD", "").strip()
    if env_cmd and os.path.exists(env_cmd):
        return True

    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\hp\miniforge3\Library\bin\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]
    if any(os.path.exists(path) for path in candidates):
        return True

    return shutil.which("tesseract") is not None


def local_ocr_status() -> dict[str, bool]:
    return {
        "paddle": paddle_available(),
        "tesseract": tesseract_available(),
    }
