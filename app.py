"""
Streamlit UI for the OCR Document Intelligence Pipeline.

Run:
    streamlit run app.py
"""

import io
import json
import os
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

# ── make project-root imports work regardless of CWD ────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

import config  # noqa: E402  (creates input/output dirs)
from layout.layout_detector import detect_layout
from ocr.hybrid_runner import run_ocr
from postprocessing.cleaner import build_table_rows, clean_text
from preprocessing.preprocess import preprocess
from table.table_extractor import extract_table
from utils.helpers import (
    crop_region,
    draw_layout_debug,
    save_json,
    timestamp_filename,
)
from utils.pdf_to_image import pdf_to_images

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OCR Pipeline",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── custom CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* top header bar */
    .ocr-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.8rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .ocr-header h1 { color: #e94560; margin: 0; font-size: 1.9rem; }
    .ocr-header p  { color: #a8b2d8; margin: 0; font-size: 0.95rem; }

    /* metric cards */
    .metric-row { display: flex; gap: 0.75rem; margin-bottom: 1rem; flex-wrap: wrap; }
    .metric-card {
        background: #1e1e2e;
        border: 1px solid #2d2d44;
        border-radius: 10px;
        padding: 0.75rem 1.2rem;
        min-width: 110px;
        text-align: center;
    }
    .metric-card .val { font-size: 1.6rem; font-weight: 700; color: #e94560; }
    .metric-card .lbl { font-size: 0.72rem; color: #888; text-transform: uppercase; letter-spacing: .05em; }

    /* block type badge */
    .badge {
        display: inline-block;
        padding: 2px 9px;
        border-radius: 99px;
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: .05em;
    }
    .badge-text   { background:#1c3a1c; color:#5fdd5f; }
    .badge-title  { background:#3a1c1c; color:#dd5f5f; }
    .badge-table  { background:#1c2a3a; color:#5f9fdd; }
    .badge-list   { background:#2a1c3a; color:#af5fdd; }
    .badge-figure { background:#3a2a1c; color:#dda05f; }

    /* confidence bar */
    .conf-bar-wrap { height: 6px; background: #2d2d44; border-radius: 3px; margin-top: 4px; }
    .conf-bar      { height: 6px; border-radius: 3px; background: #e94560; }

    /* section divider */
    .section-sep { border-top: 1px solid #2d2d44; margin: 1rem 0; }

    /* Streamlit overrides */
    [data-testid="stSidebar"] { background: #0d0d1a; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── helpers ───────────────────────────────────────────────────────────────────

def bgr_to_pil(img: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def load_uploaded_file(uploaded_file) -> list[np.ndarray]:
    """Save upload to a temp file, return BGR numpy arrays per page."""
    suffix = Path(uploaded_file.name).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    if suffix == ".pdf":
        images = pdf_to_images(tmp_path)
    else:
        img = cv2.imread(tmp_path)
        images = [img] if img is not None else []

    os.unlink(tmp_path)
    return images


def process_page(image: np.ndarray, page_num: int, mode: str, show_debug: bool) -> dict:
    processed = preprocess(image)
    layout = detect_layout(image)

    debug_img = draw_layout_debug(image, layout) if show_debug else None

    page_result = {
        "page": page_num,
        "text_blocks": [],
        "tables": [],
        "_debug_img": debug_img,
        "_original_img": image,
    }

    for block in layout:
        region = crop_region(processed, block.block)

        if block.type == "Table":
            raw_rows = extract_table(crop_region(image, block.block))
            rows = build_table_rows(raw_rows)
            page_result["tables"].append({
                "bbox": list(block.block.coordinates),
                "rows": rows,
            })
        else:
            ocr_results = run_ocr(region, mode=mode)
            text = " ".join(clean_text(r["text"]) for r in ocr_results)
            avg_conf = (
                sum(r["confidence"] for r in ocr_results) / len(ocr_results)
                if ocr_results else 0.0
            )
            if text:
                page_result["text_blocks"].append({
                    "type": block.type,
                    "bbox": list(block.block.coordinates),
                    "text": text,
                    "confidence": round(avg_conf, 3),
                })

    return page_result


def result_to_json_export(pages: list[dict]) -> dict:
    """Strip internal UI keys before export."""
    clean_pages = []
    for p in pages:
        clean_pages.append({
            "page": p["page"],
            "text_blocks": p["text_blocks"],
            "tables": p["tables"],
        })
    return {"pages": clean_pages}


# ── sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Pipeline Settings")
    st.divider()

    ocr_mode = st.selectbox(
        "OCR Engine Mode",
        options=["auto", "complex", "tesseract", "merge"],
        index=0,
        help=(
            "**auto** — Paddle first; falls back to Tesseract if confidence < 0.7\n\n"
            "**complex** — PaddleOCR only (best for dense / rotated text)\n\n"
            "**tesseract** — Tesseract only (faster, lower accuracy)\n\n"
            "**merge** — run both, keep higher-confidence result"
        ),
    )

    show_debug = st.toggle("Show layout detection overlay", value=False)

    st.divider()
    st.markdown("### 🗂️ Output")
    save_to_disk = st.toggle("Save JSON to outputs/", value=True)

    st.divider()
    st.markdown(
        "<small style='color:#555'>PaddleOCR · Tesseract · OpenCV · LayoutParser</small>",
        unsafe_allow_html=True,
    )

# ── main header ───────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="ocr-header">
        <div>
            <h1>🔍 OCR Document Intelligence</h1>
            <p>Upload a PDF or image → extract structured text &amp; tables → download JSON</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── file upload ───────────────────────────────────────────────────────────────

uploaded_file = st.file_uploader(
    "Drop a PDF or image here",
    type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"],
    help="Supported: PDF, PNG, JPG, JPEG, TIFF, BMP",
)

# reset state when a new file is uploaded
if "last_filename" not in st.session_state:
    st.session_state.last_filename = None

if uploaded_file and uploaded_file.name != st.session_state.last_filename:
    st.session_state.pop("pages", None)
    st.session_state.pop("raw_images", None)
    st.session_state.last_filename = uploaded_file.name

# ── preview & run button ──────────────────────────────────────────────────────

if uploaded_file:
    # load images (cached in session state so we don't re-decode on every rerun)
    if "raw_images" not in st.session_state:
        with st.spinner("Loading file…"):
            st.session_state.raw_images = load_uploaded_file(uploaded_file)

    raw_images: list[np.ndarray] = st.session_state.raw_images
    n_pages = len(raw_images)

    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.markdown(
            f"**{uploaded_file.name}** · {n_pages} page{'s' if n_pages != 1 else ''} · "
            f"{uploaded_file.size / 1024:.1f} KB"
        )
    with col_btn:
        run_clicked = st.button("▶ Run OCR Pipeline", type="primary", use_container_width=True)

    if run_clicked:
        st.session_state.pop("pages", None)  # clear previous results
        pages: list[dict] = []

        progress_bar = st.progress(0, text="Starting pipeline…")
        status_area = st.empty()

        for i, image in enumerate(raw_images):
            frac = i / n_pages
            progress_bar.progress(frac, text=f"Processing page {i + 1} / {n_pages}…")
            status_area.info(f"🔄 Page {i + 1}: preprocessing → layout → OCR…")

            page_result = process_page(image, i + 1, ocr_mode, show_debug)
            pages.append(page_result)

        progress_bar.progress(1.0, text="Done!")
        status_area.success(f"✅ Finished — {n_pages} page(s) processed.")

        if save_to_disk:
            export = result_to_json_export(pages)
            stem = Path(uploaded_file.name).stem
            fname = timestamp_filename(stem)
            saved = save_json(export, config.OUTPUT_DIR, fname)
            st.caption(f"💾 Saved to `{saved}`")

        st.session_state.pages = pages

# ── results ───────────────────────────────────────────────────────────────────

if "pages" in st.session_state:
    pages: list[dict] = st.session_state.pages

    # ── summary metrics ──
    total_tables = sum(len(p["tables"]) for p in pages)
    total_blocks = sum(len(p["text_blocks"]) for p in pages)
    total_words = sum(
        len(b["text"].split())
        for p in pages
        for b in p["text_blocks"]
    )

    st.markdown(
        f"""
        <div class="metric-row">
            <div class="metric-card"><div class="val">{len(pages)}</div><div class="lbl">Pages</div></div>
            <div class="metric-card"><div class="val">{total_blocks}</div><div class="lbl">Text blocks</div></div>
            <div class="metric-card"><div class="val">{total_tables}</div><div class="lbl">Tables</div></div>
            <div class="metric-card"><div class="val">{total_words}</div><div class="lbl">Words</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── per-page tabs ──
    tab_labels = [f"Page {p['page']}" for p in pages]
    tabs = st.tabs(tab_labels)

    for tab, page in zip(tabs, pages):
        with tab:
            left, right = st.columns([1, 1], gap="large")

            # ── LEFT: image preview ──
            with left:
                st.markdown("**Document Preview**")
                display_img = page["_debug_img"] if show_debug and page["_debug_img"] is not None else page["_original_img"]
                st.image(bgr_to_pil(display_img), use_container_width=True)

                if show_debug:
                    st.caption("🟢 Text  🔴 Title  🔵 Table  🟠 Figure  🟣 List")

            # ── RIGHT: OCR results ──
            with right:
                # ─ text blocks ─
                text_blocks = page["text_blocks"]
                if text_blocks:
                    st.markdown("**Text Blocks**")
                    for blk in text_blocks:
                        btype = blk["type"]
                        badge_cls = f"badge-{btype.lower()}"
                        conf_pct = int(blk["confidence"] * 100)
                        conf_width = max(2, conf_pct)

                        with st.expander(
                            f"{btype} block — confidence {conf_pct}%",
                            expanded=(btype == "Title"),
                        ):
                            st.markdown(
                                f'<span class="badge {badge_cls}">{btype}</span>'
                                f'<div class="conf-bar-wrap">'
                                f'<div class="conf-bar" style="width:{conf_width}%"></div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                            st.markdown(blk["text"])
                            st.caption(
                                f"bbox: {[round(v) for v in blk['bbox']]}"
                            )
                else:
                    st.info("No text blocks detected on this page.")

                # ─ tables ─
                tables = page["tables"]
                if tables:
                    st.markdown("**Tables**")
                    for t_idx, tbl in enumerate(tables, 1):
                        rows = tbl["rows"]
                        st.markdown(
                            f'<span class="badge badge-table">Table {t_idx}</span>',
                            unsafe_allow_html=True,
                        )
                        if rows:
                            df = pd.DataFrame(rows)
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.warning("Table detected but no cells extracted.")
                        st.caption(f"bbox: {[round(v) for v in tbl['bbox']]}")

    # ── JSON viewer + download ──
    st.divider()
    export_data = result_to_json_export(pages)
    json_str = json.dumps(export_data, indent=2, ensure_ascii=False)

    col_dl, col_view = st.columns([1, 3])
    with col_dl:
        stem = Path(st.session_state.last_filename or "result").stem
        st.download_button(
            label="⬇ Download JSON",
            data=json_str,
            file_name=timestamp_filename(stem),
            mime="application/json",
            use_container_width=True,
        )
    with col_view:
        with st.expander("View raw JSON output"):
            st.code(json_str, language="json")

elif not uploaded_file:
    # ── empty state ──
    st.markdown(
        """
        <div style="text-align:center; padding: 4rem 2rem; color: #555;">
            <div style="font-size: 4rem;">📄</div>
            <p style="font-size: 1.1rem; margin-top: 1rem;">
                Upload a PDF or image above to get started
            </p>
            <p style="font-size: 0.85rem; color: #444;">
                Supports PDFs, PNG, JPG, TIFF, BMP
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
