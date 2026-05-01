import os

# --- Input / Output ---
INPUT_DIR = "inputs"
OUTPUT_DIR = "outputs"

# --- PDF rendering ---
PDF_DPI = 300

# --- Preprocessing ---
ADAPTIVE_BLOCK_SIZE = 11
ADAPTIVE_C = 2
MEDIAN_BLUR_KSIZE = 3

# --- OCR ---
OCR_LANG = "en"
OCR_MODE = "auto"   # "auto" | "complex" | "tesseract"
PADDLE_USE_ANGLE_CLS = True
PADDLE_USE_GPU = False

# --- Table detection ---
H_KERNEL_WIDTH = 40
V_KERNEL_HEIGHT = 40

# --- Post-processing ---
AMOUNT_REGEX = r"\d[\d,]*\.\d{2}"
DATE_REGEX = r"\d{2}[\/\-]\d{2}[\/\-]\d{4}"

# --- Layout ---
LAYOUT_MODEL = "lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config"
LAYOUT_SCORE_THRESHOLD = 0.5

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
