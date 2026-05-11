# Installation Guide — DocuSense

## 1. Clone the repository

```bash
git clone https://github.com/anshulsing155/DocuSense.git
cd DocuSense
```

## 2. Create a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS
```

## 3. Install base dependencies

```bash
pip install -r requirements.txt
```

## 4. Tesseract (Windows)

Download the installer from: https://github.com/UB-Mannheim/tesseract/wiki  
Add the install path (e.g. `C:\Program Files\Tesseract-OCR`) to your PATH.

On Linux/macOS:
```bash
sudo apt install tesseract-ocr   # Ubuntu/Debian
brew install tesseract           # macOS
```

## 5. Detectron2 (for LayoutParser — optional)

Detectron2 has no pre-built Windows wheel — use the CPU build:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install 'git+https://github.com/facebookresearch/detectron2.git'
```
If Detectron2 is unavailable the pipeline falls back to treating the whole page as a single text block.

## 6. Environment / API keys

Copy the example env file and fill in your keys:
```bash
cp .env.example .env
```

| Variable | Required for |
|---|---|
| `GEMINI_API_KEY` | Google Gemini Vision AI bank extraction |
| `GROK_API_KEY` | xAI Grok Vision AI bank extraction |

## 7. Verify

```bash
python -c "from paddleocr import PaddleOCR; print('PaddleOCR OK')"
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

## 8. Run — Web UI (recommended)

```bash
streamlit run app.py
```
Opens at http://localhost:8501 automatically.

## 9. Run — CLI (headless / scripting)

```bash
# Using the installed entry point:
docsense --input inputs/statement.pdf --debug

# Or directly:
python main.py --input inputs/statement.pdf --debug
```
