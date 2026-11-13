# -*- coding: utf-8 -*-
"""Marketplace example: tiny local notes tool."""
from __future__ import annotations

import json
from pathlib import Path

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "quick_note_save",
            "description": "Зберегти коротку нотатку в локальний файл плагіна.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Текст нотатки."}
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "quick_note_list",
            "description": "Показати збережені нотатки плагіна.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

MAX_NOTES = 50


def _path(ctx) -> Path:
    return Path(ctx.data_dir) / "marketplace_notes.json"


def _load(ctx) -> list[str]:
    try:
        payload = json.loads(_path(ctx).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [str(item)[:500] for item in payload if str(item).strip()][-MAX_NOTES:]


def run(name: str, args: dict, ctx) -> str:
    if name == "quick_note_save":
        text = str((args or {}).get("text") or "").strip()[:500]
        if not text:
            return "Нотатка порожня."
        notes = _load(ctx)
        notes.append(text)
        _path(ctx).write_text(
            json.dumps(notes[-MAX_NOTES:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return f"Нотатку збережено. Усього: {len(notes[-MAX_NOTES:])}."
    if name == "quick_note_list":
        notes = _load(ctx)
        if not notes:
            return "Нотаток ще немає."
        return "Нотатки:\n" + "\n".join(
            f"{index}. {note}" for index, note in enumerate(notes, 1)
        )
    return f"Невідомий інструмент плагіна: {name}"
