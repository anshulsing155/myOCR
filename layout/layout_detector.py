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
    Returns a layoutparser Layout object.
    Each block has .type and .block.coordinates (x1, y1, x2, y2).
    Falls back to a single full-page 'Text' block if the model is unavailable.
    """
    try:
        model = _get_model()
        return model.detect(image)
    except RuntimeError:
        return _fallback_layout(image)


def _fallback_layout(image: np.ndarray):
    """Return a single block covering the whole image when layout model is absent."""
    import layoutparser as lp
    h, w = image.shape[:2]
    block = lp.Rectangle(0, 0, w, h)
    return lp.Layout([lp.TextBlock(block, type="Text")])
