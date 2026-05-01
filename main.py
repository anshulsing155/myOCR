"""
OCR Pipeline — entry point.

Usage:
    python main.py --input inputs/statement.pdf
    python main.py --input inputs/scan.png --mode complex
    python main.py --input inputs/statement.pdf --debug
"""

import argparse
import json
import os
import sys

import cv2

from config import OUTPUT_DIR
from layout.layout_detector import detect_layout
from ocr.hybrid_runner import run_ocr
from postprocessing.cleaner import build_table_rows, clean_text
from preprocessing.preprocess import preprocess
from table.table_extractor import extract_table
from utils.helpers import crop_region, draw_layout_debug, save_json, timestamp_filename
from utils.pdf_to_image import pdf_to_images


def load_input(path: str) -> list:
    """Accept PDF or image file; always return a list of BGR numpy arrays."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return pdf_to_images(path)
    img = cv2.imread(path)
    if img is None:
        sys.exit(f"Cannot read image: {path}")
    return [img]


def process_page(image, page_num: int, mode: str, debug: bool) -> dict:
    processed = preprocess(image)
    layout = detect_layout(image)  # layout detection works better on original colour image

    if debug:
        debug_img = draw_layout_debug(image, layout)
        cv2.imwrite(os.path.join(OUTPUT_DIR, f"debug_page_{page_num}.png"), debug_img)

    page_result = {"page": page_num, "text_blocks": [], "tables": []}

    for block in layout:
        region = crop_region(processed, block.block)

        if block.type == "Table":
            raw_rows = extract_table(crop_region(image, block.block))
            rows = build_table_rows(raw_rows)
            page_result["tables"].append({"bbox": list(block.block.coordinates), "rows": rows})

        else:
            ocr_results = run_ocr(region, mode=mode)
            text = " ".join(clean_text(r["text"]) for r in ocr_results)
            if text:
                page_result["text_blocks"].append({
                    "type": block.type,
                    "bbox": list(block.block.coordinates),
                    "text": text,
                })

    return page_result


def run_pipeline(input_path: str, mode: str = "auto", debug: bool = False) -> dict:
    images = load_input(input_path)
    output = {"source": input_path, "pages": []}

    for i, image in enumerate(images, start=1):
        print(f"  Processing page {i}/{len(images)} …")
        page_result = process_page(image, i, mode, debug)
        output["pages"].append(page_result)

    filename = timestamp_filename(os.path.splitext(os.path.basename(input_path))[0])
    saved_path = save_json(output, OUTPUT_DIR, filename)
    print(f"  Saved → {saved_path}")
    return output


def main():
    parser = argparse.ArgumentParser(description="OCR Document Intelligence Pipeline")
    parser.add_argument("--input", required=True, help="Path to PDF or image file")
    parser.add_argument("--mode", default="auto",
                        choices=["auto", "complex", "tesseract", "merge"],
                        help="OCR engine mode (default: auto)")
    parser.add_argument("--debug", action="store_true",
                        help="Save layout debug images to outputs/")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f"Input file not found: {args.input}")

    print(f"Starting pipeline: {args.input}")
    result = run_pipeline(args.input, mode=args.mode, debug=args.debug)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
