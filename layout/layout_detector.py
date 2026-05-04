import numpy as np
from config import LAYOUT_MODEL, LAYOUT_SCORE_THRESHOLD

_model = None


def _get_model():
    global _model
    if _model is None:
        try:
            import layoutparser as lp
            _model = lp.Detectron2LayoutModel(
                LAYOUT_MODEL,
                extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", LAYOUT_SCORE_THRESHOLD],
                label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"},
            )
        except Exception as e:
            raise RuntimeError(
                "LayoutParser / Detectron2 not installed. "
                "Run: pip install layoutparser[layoutmodels] detectron2\n"
                f"Original error: {e}"
            )
    return _model


def detect_layout(image: np.ndarray):
    """
    Returns a Layout-like object (list of blocks with .type and .block.coordinates).
    Falls back to a single full-page 'Text' block when the model is unavailable.
    """
    try:
        model = _get_model()
        return model.detect(image)
    except RuntimeError:
        return _minimal_layout(image)


# ── pure-Python fallback (no layoutparser required) ───────────────────────────

class _Rect:
    """Minimal stand-in for layoutparser Rectangle."""
    def __init__(self, x1, y1, x2, y2):
        self.coordinates = (x1, y1, x2, y2)


class _Block:
    """Minimal stand-in for layoutparser TextBlock."""
    def __init__(self, rect, block_type: str):
        self.block = rect
        self.type = block_type


class _Layout(list):
    """Minimal stand-in for layoutparser Layout (just a list of blocks)."""


def _minimal_layout(image: np.ndarray) -> _Layout:
    """Return a single block covering the whole image."""
    h, w = image.shape[:2]
    return _Layout([_Block(_Rect(0, 0, w, h), "Text")])
