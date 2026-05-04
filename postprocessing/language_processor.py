"""
Indian language detection, translation, and intelligent field mapping.

Pipeline per OCR result:
  1. detect_script()  — which Unicode script block dominates (Devanagari, Tamil, …)
  2. detect_language() — fine-grained language code via fast_langdetect (hi/mr/bn/ta…)
  3. translate_to_english() — Google Translate via deep_translator (cached)
  4. process_multilingual_ocr() — enrich a list of OCR dicts with lang/translation

The translated text is stored alongside the original so parsers can use it while
the UI still shows what was actually on the document.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Any

# ── Unicode script ranges for Indian scripts ──────────────────────────────────
_SCRIPT_RANGES: list[tuple[range, str, str]] = [
    # (codepoint range, script_name, paddle_lang_code)
    (range(0x0900, 0x0980), "devanagari", "hi"),   # Hindi, Marathi, Sanskrit, Nepali
    (range(0x0980, 0x0A00), "bengali",    "bn"),   # Bengali, Assamese
    (range(0x0A00, 0x0A80), "gurmukhi",   "pa"),   # Punjabi
    (range(0x0A80, 0x0B00), "gujarati",   "gu"),   # Gujarati
    (range(0x0B00, 0x0B80), "odia",       "or"),   # Odia
    (range(0x0B80, 0x0C00), "tamil",      "ta"),   # Tamil
    (range(0x0C00, 0x0C80), "telugu",     "te"),   # Telugu
    (range(0x0C80, 0x0D00), "kannada",    "kn"),   # Kannada
    (range(0x0D00, 0x0D80), "malayalam",  "ml"),   # Malayalam
    (range(0x0600, 0x0700), "arabic",     "ur"),   # Urdu (Arabic script)
]

# Language code → readable name
LANG_NAMES: dict[str, str] = {
    "hi": "Hindi",
    "mr": "Marathi",
    "bn": "Bengali",
    "as": "Assamese",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "or": "Odia",
    "ur": "Urdu",
    "sa": "Sanskrit",
    "ne": "Nepali",
    "en": "English",
    "unknown": "Unknown",
}

# Devanagari script is shared by Hindi *and* Marathi — fast_langdetect can
# distinguish them, but both can be translated from 'hi' source.
_MARATHI_AS_HINDI = {"mr", "sa", "ne"}

# Languages we skip translation for (already English or Latin-based)
_SKIP_TRANSLATE = {"en", "unknown"}


# ── script detection ──────────────────────────────────────────────────────────

def detect_script(text: str) -> tuple[str, str] | tuple[None, None]:
    """
    Count Indian-script codepoints and return (script_name, paddle_lang_code)
    for the dominant script, or (None, None) if text is mostly Latin.
    """
    counts: dict[str, int] = {}
    for ch in text:
        cp = ord(ch)
        for r, script, _ in _SCRIPT_RANGES:
            if cp in r:
                counts[script] = counts.get(script, 0) + 1
                break

    if not counts:
        return None, None

    dominant = max(counts, key=lambda k: counts[k])
    total = sum(counts.values())
    latin_count = sum(1 for ch in text if ch.isascii() and ch.isalpha())

    # Only treat as Indian-language if at least 15% of alpha chars are that script
    alpha_total = total + latin_count
    if alpha_total == 0 or total / alpha_total < 0.15:
        return None, None

    paddle_code = next(code for _, s, code in _SCRIPT_RANGES if s == dominant)
    return dominant, paddle_code


def has_indian_script(text: str) -> bool:
    script, _ = detect_script(text)
    return script is not None


# ── language identification ────────────────────────────────────────────────────

def detect_language(text: str) -> tuple[str, float]:
    """
    Detect language using fast_langdetect.
    Returns (lang_code, confidence).  Falls back to (script-based guess, 0.5)
    if fast_langdetect is unavailable or text too short.
    """
    clean = text.strip()
    if not clean or len(clean) < 5:
        return "unknown", 0.0

    try:
        from fast_langdetect import detect
        result = detect(clean, low_memory=True)
        lang = result.get("lang", "unknown")
        score = float(result.get("score", 0.0))
        return lang, score
    except Exception:
        pass

    # Fallback: script-based
    _, paddle_code = detect_script(clean)
    if paddle_code:
        return paddle_code, 0.5
    return "unknown", 0.0


# ── translation ───────────────────────────────────────────────────────────────

@lru_cache(maxsize=512)
def _translate_cached(text: str, source_lang: str) -> str:
    """Translate text to English; cached to avoid redundant network calls."""
    try:
        from deep_translator import GoogleTranslator
        # Marathi, Sanskrit, Nepali all use Devanagari — translate as Hindi
        src = "hi" if source_lang in _MARATHI_AS_HINDI else source_lang
        result = GoogleTranslator(source=src, target="en").translate(text)
        return result or text
    except Exception:
        return text


def translate_to_english(text: str, source_lang: str) -> str:
    """
    Translate `text` from `source_lang` to English.
    Returns the original text unchanged if translation fails or is unnecessary.
    """
    if not text or not text.strip():
        return text
    if source_lang in _SKIP_TRANSLATE:
        return text
    return _translate_cached(text.strip(), source_lang)


# ── OCR result enrichment ─────────────────────────────────────────────────────

def _split_mixed_text(text: str) -> tuple[str, str]:
    """
    Split a mixed-script text into (indian_part, latin_part).
    Useful when a single OCR line has e.g. "Account No खाता संख्या 12345".
    """
    indian_chars, latin_chars = [], []
    for ch in text:
        if ord(ch) > 0x07FF and not ch.isascii():  # non-ASCII
            indian_chars.append(ch)
        elif ch.isalpha():
            latin_chars.append(ch)
        # keep digits/punct in latin
    return "".join(indian_chars), "".join(latin_chars)


def process_ocr_item(item: dict) -> dict:
    """
    Enrich a single OCR result dict with language/translation info.

    Input:  {"text": "...", "confidence": 0.9, "bbox": [...]}
    Output: same dict + optional keys:
              "detected_lang"     — ISO 639-1 code e.g. "hi"
              "lang_name"         — e.g. "Hindi"
              "lang_confidence"   — 0–1 score from fast_langdetect
              "translated_text"   — English translation (only when != original)
    """
    text = item.get("text", "")
    if not text or not text.strip():
        return item

    script, _ = detect_script(text)
    if not script:
        return item  # already Latin/English — no processing needed

    lang, lang_conf = detect_language(text)
    translated = translate_to_english(text, lang)

    # Normalise Devanagari variants so display always shows "Hindi"
    display_lang = _normalise_lang(lang)

    enriched = dict(item)
    enriched["detected_lang"] = display_lang
    enriched["lang_name"] = LANG_NAMES.get(display_lang, display_lang)
    enriched["lang_confidence"] = round(lang_conf, 3)
    if translated and translated != text:
        enriched["translated_text"] = translated
    return enriched


def process_multilingual_ocr(ocr_results: list[dict]) -> list[dict]:
    """
    Process a list of OCR result dicts.
    Returns enriched list — only items with Indian script are translated.
    Items that are already Latin/English are returned unchanged (fast path).
    """
    return [process_ocr_item(item) for item in ocr_results]


# ── document-level language summary ───────────────────────────────────────────

# Devanagari-script languages that are functionally identical for OCR/translation
# fast_langdetect often returns "mr" for Hindi government text — normalise to "hi"
_DEVANAGARI_NORMALISE: dict[str, str] = {"mr": "hi", "sa": "hi", "ne": "hi"}


def _normalise_lang(lang: str) -> str:
    """Normalise Devanagari-family detections to 'hi' for consistent display."""
    return _DEVANAGARI_NORMALISE.get(lang, lang)


def summarise_languages(ocr_results: list[dict]) -> dict[str, Any]:
    """
    Compute a language summary over all OCR results.

    Returns:
        {
          "detected_languages": ["hi", "en"],   # all unique langs found
          "primary_language":   "hi",           # most common non-English lang,
                                                  or "en" if fully English
          "multilingual":       True/False,
          "translation_applied": True/False,
        }
    """
    lang_counts: dict[str, int] = {}
    has_translation = False

    for item in ocr_results:
        lang = item.get("detected_lang")
        if lang:
            # Normalise Devanagari variants (mr/sa/ne → hi)
            lang = _normalise_lang(lang)
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        if item.get("translated_text"):
            has_translation = True

    # Count Latin items as "en"
    for item in ocr_results:
        if not item.get("detected_lang"):
            lang_counts["en"] = lang_counts.get("en", 0) + 1

    if not lang_counts:
        return {
            "detected_languages": ["en"],
            "primary_language": "en",
            "multilingual": False,
            "translation_applied": False,
        }

    all_langs = sorted(lang_counts, key=lambda k: lang_counts[k], reverse=True)
    non_en = [l for l in all_langs if l != "en"]
    primary = non_en[0] if non_en else "en"

    return {
        "detected_languages": all_langs,
        "primary_language": primary,
        "multilingual": len(set(all_langs) - {"en"}) > 0,
        "translation_applied": has_translation,
    }


# ── translated OCR for parsers ─────────────────────────────────────────────────

def get_translated_ocr(ocr_results: list[dict]) -> list[dict]:
    """
    Return OCR results where each item's "text" is replaced by its
    "translated_text" (if available), suitable for feeding into parsers.
    """
    translated = []
    for item in ocr_results:
        if item.get("translated_text"):
            new_item = dict(item)
            new_item["text"] = item["translated_text"]
            translated.append(new_item)
        else:
            translated.append(item)
    return translated
