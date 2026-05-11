import json
import os
from datetime import datetime

import cv2
import numpy as np


def crop_region(image: np.ndarray, bbox) -> np.ndarray:
    """Crop image to a bounding box. bbox can be (x1,y1,x2,y2) or a layoutparser Rectangle."""
    if hasattr(bbox, "coordinates"):
        x1, y1, x2, y2 = [int(v) for v in bbox.coordinates]
    else:
        x1, y1, x2, y2 = [int(v) for v in bbox]
    return image[y1:y2, x1:x2]


def save_json(data: dict | list, output_dir: str, filename: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def timestamp_filename(prefix: str, ext: str = "json") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.{ext}"


def draw_layout_debug(image: np.ndarray, layout) -> np.ndarray:
    """Draw coloured bounding boxes for each detected layout block."""
    colour_map = {
        "Text": (0, 255, 0),
        "Title": (255, 0, 0),
        "Table": (0, 0, 255),
        "Figure": (255, 165, 0),
        "List": (128, 0, 128),
    }
    debug = image.copy()
    for block in layout:
        colour = colour_map.get(block.type, (200, 200, 200))
        x1, y1, x2, y2 = [int(v) for v in block.block.coordinates]
        cv2.rectangle(debug, (x1, y1), (x2, y2), colour, 2)
        cv2.putText(debug, block.type, (x1, max(y1 - 5, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, colour, 2)
    return debug
