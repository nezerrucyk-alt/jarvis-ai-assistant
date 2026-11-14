# -*- coding: utf-8 -*-
"""Local clipboard history helpers.

Pure data functions (no Tk, no disk I/O) shared by the desktop UI and the
assistant tools, so they can be unit-tested without a running application.
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Iterable, Optional

MAX_TEXT = 20_000
DEFAULT_LIMIT = 120


def clean_text(value: Any) -> str:
    """Normalises clipboard text: strips NULs and caps the stored length."""
    return str(value or "").replace("\x00", "").strip()[:MAX_TEXT]


def make_entry(text: Any, now: Optional[datetime] = None) -> Optional[dict[str, Any]]:
    cleaned = clean_text(text)
    if not cleaned:
        return None
    moment = (now or datetime.now()).isoformat(timespec="seconds")
    digest = hashlib.blake2b(
        f"{moment}|{cleaned}".encode("utf-8"), digest_size=6
    ).hexdigest()
    return {"id": digest, "text": cleaned, "ts": moment}


def add_entry(
    items: Iterable[dict[str, Any]],
    text: Any,
    now: Optional[datetime] = None,
    limit: int = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Puts the text on top, drops older copies of the same text, caps the list."""
    rows = [item for item in items if isinstance(item, dict) and item.get("text")]
    entry = make_entry(text, now)
    if entry is None:
        return rows
    rows = [item for item in rows if str(item.get("text")) != entry["text"]]
    rows.insert(0, entry)
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT
    return rows[: max(10, min(limit, 1000))]


def search(
    items: Iterable[dict[str, Any]],
    query: str = "",
    limit: int = 20,
) -> list[dict[str, Any]]:
    needle = str(query or "").strip().casefold()
    rows = [item for item in items if isinstance(item, dict) and item.get("text")]
    if needle:
        rows = [item for item in rows if needle in str(item["text"]).casefold()]
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 20
    return rows[: max(1, min(limit, 200))]


def remove_entry(items: Iterable[dict[str, Any]], entry_id: str) -> list[dict[str, Any]]:
    return [
        item
        for item in items
        if isinstance(item, dict) and str(item.get("id")) != str(entry_id)
    ]


__all__ = [
    "DEFAULT_LIMIT",
    "MAX_TEXT",
    "add_entry",
    "clean_text",
    "make_entry",
    "remove_entry",
    "search",
]
