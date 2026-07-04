from __future__ import annotations

import re


def normalize(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_key(text: str | None) -> str:
    return normalize(text).casefold()


def xpath_literal(text: str) -> str:
    if "'" not in text:
        return f"'{text}'"
    if '"' not in text:
        return f'"{text}"'
    return "concat(" + ", \"'\", ".join(f"'{part}'" for part in text.split("'")) + ")"


def digits_only(text: str | None) -> str:
    return re.sub(r"\D", "", text or "")
