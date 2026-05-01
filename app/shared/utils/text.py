"""Text normalization helpers."""

from __future__ import annotations

import unicodedata
from typing import Any

from sqlalchemy import func

_GERMAN_TRANSLITERATION_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("ä", "ae"),
    ("ö", "oe"),
    ("ü", "ue"),
    ("ß", "ss"),
)


def normalize_german_text(value: str) -> str:
    text = unicodedata.normalize("NFC", value).casefold()
    for source, target in _GERMAN_TRANSLITERATION_REPLACEMENTS:
        text = text.replace(source, target)
    return text


def normalize_german_text_sql(expression: Any) -> Any:
    normalized = func.lower(expression)
    for source, target in _GERMAN_TRANSLITERATION_REPLACEMENTS:
        normalized = func.replace(normalized, source, target)
    return normalized
