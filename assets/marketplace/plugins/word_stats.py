# -*- coding: utf-8 -*-
"""Marketplace example: word and character statistics."""
from __future__ import annotations

import re

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "word_stats",
            "description": "Порахувати слова, символи та речення у тексті.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Текст для аналізу."}
                },
                "required": ["text"],
            },
        },
    }
]


def run(name: str, args: dict, ctx) -> str:
    if name != "word_stats":
        return f"Невідомий інструмент плагіна: {name}"
    text = str((args or {}).get("text") or "")
    words = re.findall(r"[^\W_]+", text, flags=re.UNICODE)
    sentences = [part for part in re.split(r"[.!?]+", text) if part.strip()]
    return (
        f"Слів: {len(words)}; символів: {len(text)}; "
        f"речень: {len(sentences)}; унікальних слів: {len({word.casefold() for word in words})}."
    )
