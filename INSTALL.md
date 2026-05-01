# Installation Guide

## 1. Create a virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
```

## 2. Install base dependencies
```bash
pip install -r requirements.txt
```

## 3. Tesseract (Windows)
Download the installer from: https://github.com/UB-Mannheim/tesseract/wiki
Add the install path (e.g. `C:\Program Files\Tesseract-OCR`) to your PATH.

## 4. Detectron2 (for LayoutParser)
Detectron2 has no pre-built Windows wheel — use the CPU build:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install 'git+https://github.com/facebookresearch/detectron2.git'
```
If Detectron2 is unavailable the pipeline falls back to treating the whole page as a single text block.

## 5. Verify
```bash
python -c "from paddleocr import PaddleOCR; print('PaddleOCR OK')"
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

## 6. Run — Web UI (recommended)
```bash
streamlit run app.py
```
Opens at http://localhost:8501 automatically.

## 7. Run — CLI (headless / scripting)
```bash
python main.py --input inputs/statement.pdf --debug
```
