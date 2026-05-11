"""
Validate Gemini bank statement extraction against known ground-truth.

Usage:
    Copy a bank statement PDF into inputs/, then run:
        GEMINI_API_KEY=your-key python scripts/validate_gemini.py inputs/statement.pdf HDFC
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ocr.gemini_bank_ocr import GeminiBankOCR
from utils.pdf_to_image import pdf_to_images


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Gemini OCR extraction")
    parser.add_argument("pdf", nargs="?", help="Path to the PDF file")
    parser.add_argument("bank", nargs="?", default="", help="Bank hint (e.g. HDFC, SBI)")
    args = parser.parse_args()

    pdf_path = args.pdf
    if not pdf_path:
        candidates = glob.glob("inputs/*.pdf") + glob.glob("inputs/**/*.pdf", recursive=True)
        pdf_path = next((p for p in candidates if os.path.exists(p)), None)
    if not pdf_path or not os.path.exists(pdf_path):
        print("PDF not found. Pass a path as argument or copy a PDF into inputs/")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("Set GEMINI_API_KEY environment variable and re-run.")
        sys.exit(1)

    print(f"Using: {pdf_path}")
    images = pdf_to_images(pdf_path)
    print(f"Pages: {len(images)}")

    ocr = GeminiBankOCR(api_key=api_key)
    result = ocr.extract(images, bank_hint=args.bank)

    if "error" in result:
        print(f"ERROR: {result['error']}")
        sys.exit(1)

    print(f"Response time: {result.get('response_time_sec')}s\n")
    print(f"Bank:           {result.get('bank_name')}")
    print(f"Account:        {result.get('account_number')}")
    print(f"Holder:         {result.get('account_holder')}")
    print(f"Period:         {result.get('statement_from')} — {result.get('statement_to')}")
    print(f"Transactions:   {len(result.get('transactions', []))}")
    print(f"Closing bal:    {result.get('closing_balance')}")

    out_path = os.path.join("outputs", "_validation_result.json")
    os.makedirs("outputs", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nFull result saved to {out_path}")


if __name__ == "__main__":
    main()
