import cv2
import numpy as np

from config import H_KERNEL_WIDTH, V_KERNEL_HEIGHT
from ocr.hybrid_runner import run_ocr


def extract_table(image: np.ndarray) -> list[list[str]]:
    """
    Full table pipeline:
      1. Detect grid lines
      2. Find cell bounding boxes
      3. OCR each cell
      4. Return 2-D list of strings (rows × cols)
    """
    cells = detect_cells(image)
    if not cells:
        return []
    return _ocr_cells(image, cells)


def detect_cells(image: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Return sorted list of (x1, y1, x2, y2) cell bounding boxes."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    h_lines = _detect_lines(binary, "horizontal")
    v_lines = _detect_lines(binary, "vertical")

    grid = cv2.add(h_lines, v_lines)
    contours, _ = cv2.findContours(grid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    cells = []
    img_area = image.shape[0] * image.shape[1]
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        # filter out noise (too small) and the full-table outline (too large)
        if area < 400 or area > img_area * 0.9:
            continue
        cells.append((x, y, x + w, y + h))

    # sort top-to-bottom, left-to-right
    cells.sort(key=lambda c: (c[1], c[0]))
    return cells


def _detect_lines(binary: np.ndarray, direction: str) -> np.ndarray:
    if direction == "horizontal":
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (H_KERNEL_WIDTH, 1))
    else:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, V_KERNEL_HEIGHT))
    return cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)


def _ocr_cells(image: np.ndarray, cells: list[tuple]) -> list[list[str]]:
    """Group cells into rows by Y proximity, OCR each, return 2-D list."""
    rows: list[list[tuple]] = []
    current_row: list[tuple] = []
    row_y = None

    for cell in cells:
        x1, y1, x2, y2 = cell
        mid_y = (y1 + y2) / 2
        if row_y is None or abs(mid_y - row_y) > 10:
            if current_row:
                rows.append(sorted(current_row, key=lambda c: c[0]))
            current_row = [cell]
            row_y = mid_y
        else:
            current_row.append(cell)
    if current_row:
        rows.append(sorted(current_row, key=lambda c: c[0]))

    table: list[list[str]] = []
    for row in rows:
        row_texts = []
        for x1, y1, x2, y2 in row:
            cell_img = image[y1:y2, x1:x2]
            ocr_results = run_ocr(cell_img, mode="complex")
            text = " ".join(r["text"] for r in ocr_results).strip()
            row_texts.append(text)
        table.append(row_texts)

    return table
