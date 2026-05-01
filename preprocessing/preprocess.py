import cv2
import numpy as np
from config import ADAPTIVE_BLOCK_SIZE, ADAPTIVE_C, MEDIAN_BLUR_KSIZE


def preprocess(image: np.ndarray) -> np.ndarray:
    """Full preprocessing pipeline: greyscale → denoise → threshold → deskew."""
    gray = _to_gray(image)
    denoised = cv2.medianBlur(gray, MEDIAN_BLUR_KSIZE)
    thresh = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        ADAPTIVE_BLOCK_SIZE,
        ADAPTIVE_C,
    )
    deskewed = _deskew(thresh)
    return deskewed


def _to_gray(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _deskew(image: np.ndarray) -> np.ndarray:
    """Rotate image to correct skew detected via Hough lines."""
    coords = np.column_stack(np.where(image > 0))
    if len(coords) < 10:
        return image
    angle = cv2.minAreaRect(coords)[-1]
    # minAreaRect returns angles in [-90, 0); normalise to [-45, 45]
    if angle < -45:
        angle = 90 + angle
    if abs(angle) < 0.5:
        return image
    h, w = image.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(image, M, (w, h),
                          flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)
