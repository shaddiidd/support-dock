from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Iterable, List, Optional, Sequence

from openai import OpenAI

from app.core.config import get_settings

logger = logging.getLogger("support_dock.retrieval")

try:
    from langdetect import DetectorFactory

    DetectorFactory.seed = 0
except Exception:
    pass

ARABIC_SCRIPT = re.compile(r"[\u0600-\u06FF]")
LATIN_LETTERS = re.compile(r"[A-Za-z]")
CJK_SCRIPT = re.compile(r"[\u4E00-\u9FFF]")
CYRILLIC_SCRIPT = re.compile(r"[\u0400-\u04FF]")

LANGUAGE_ALIASES = {
    "zh-cn": "zh",
    "zh-tw": "zh",
    "zh-hans": "zh",
    "zh-hant": "zh",
    "iw": "he",
    "in": "id",
    "ji": "yi",
}

LANGUAGE_NAMES = {
    "ar": "Arabic",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fa": "Persian",
    "fr": "French",
    "he": "Hebrew",
    "hi": "Hindi",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "nl": "Dutch",
    "pl": "Polish",
    "pt": "Portuguese",
    "ru": "Russian",
    "tr": "Turkish",
    "ur": "Urdu",
    "zh": "Chinese",
}

# Short English questions are often mislabeled as these by langdetect.
LANGDETECT_NOISE = {
    "af",
    "ca",
    "cy",
    "da",
    "et",
    "fi",
    "hr",
    "id",
    "lt",
    "lv",
    "no",
    "sk",
    "sl",
    "so",
    "sq",
    "sw",
    "tl",
}


def normalize_language(code: Optional[str]) -> str:
    raw = (code or "").strip().lower().replace("_", "-")
    if not raw:
        return "en"
    raw = LANGUAGE_ALIASES.get(raw, raw)
    primary = raw.split("-", 1)[0]
    return (LANGUAGE_ALIASES.get(primary, primary) or "en")[:16]


def language_name(code: str) -> str:
    normalized = normalize_language(code)
    return LANGUAGE_NAMES.get(normalized, normalized)


def unique_languages(codes: Iterable[Optional[str]]) -> List[str]:
    found = {normalize_language(code) for code in codes if code}
    return sorted(found)


def majority_language(codes: Sequence[str], fallback: str = "en") -> str:
    cleaned = [normalize_language(code) for code in codes if code]
    if not cleaned:
        return fallback
    return Counter(cleaned).most_common(1)[0][0]


def detect_language(text: str) -> str:
    sample = " ".join((text or "").split()[:120])
    if not sample.strip():
        return "en"

    arabic = len(ARABIC_SCRIPT.findall(sample))
    latin = len(LATIN_LETTERS.findall(sample))
    cjk = len(CJK_SCRIPT.findall(sample))
    cyrillic = len(CYRILLIC_SCRIPT.findall(sample))

    if arabic >= 3 and arabic >= latin:
        return "ar"
    if cjk >= 4 and cjk >= latin and cjk >= cyrillic:
        detected = _langdetect(sample)
        return detected if detected in {"zh", "ja", "ko"} else "zh"
    if cyrillic >= 8 and cyrillic > latin:
        return "ru"

    return _langdetect(sample)


def translate_query(text: str, target_language: str) -> str:
    settings = get_settings()
    if not settings.openai_api_key.strip():
        return ""
    target = normalize_language(target_language)
    name = language_name(target)
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_chat_model,
            temperature=0,
            max_tokens=220,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Translate the user's search query into {name}. "
                        "Return only the translated query, with no quotes or explanation. "
                        "Keep it a concise search query, not an answer."
                    ),
                },
                {"role": "user", "content": text.strip()},
            ],
        )
        translated = (response.choices[0].message.content or "").strip()
        return translated.strip("\"'")
    except Exception:
        logger.exception("Failed to translate search query into %s", target)
        return ""


def _langdetect(sample: str) -> str:
    try:
        from langdetect import detect_langs

        ranked = sorted(detect_langs(sample), key=lambda item: item.prob, reverse=True)
        if not ranked:
            return "en"
        top_code = normalize_language(ranked[0].lang)
        english = next(
            (item for item in ranked if normalize_language(item.lang) == "en"),
            None,
        )
        latin_only = bool(LATIN_LETTERS.search(sample)) and not (
            ARABIC_SCRIPT.search(sample)
            or CJK_SCRIPT.search(sample)
            or CYRILLIC_SCRIPT.search(sample)
        )
        if latin_only and top_code in LANGDETECT_NOISE:
            return "en"
        if latin_only and english and english.prob >= 0.25:
            return "en"
        return top_code
    except Exception:
        return "en"
