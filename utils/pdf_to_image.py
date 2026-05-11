import io

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from config import PDF_DPI


def pdf_to_images(pdf_path: str) -> list[np.ndarray]:
    """Return one BGR numpy array per page."""
    doc = fitz.open(pdf_path)
    images = []

    for page in doc:
        pix = page.get_pixmap(dpi=PDF_DPI)
        img_bytes = pix.pil_tobytes(format="PNG")
        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        images.append(np.array(pil_img)[:, :, ::-1])  # RGB → BGR for OpenCV

    doc.close()
    return images
