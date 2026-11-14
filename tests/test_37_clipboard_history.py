# -*- coding: utf-8 -*-
"""Clipboard history helpers."""
from __future__ import annotations

import unittest
from datetime import datetime

from core.clipboard_history import (
    add_entry,
    clean_text,
    make_entry,
    remove_entry,
    search,
)


class ClipboardHistoryTests(unittest.TestCase):
    def test_clean_text_strips_and_caps(self) -> None:
        self.assertEqual(clean_text("  hello\x00  "), "hello")
        self.assertEqual(clean_text(None), "")
        self.assertEqual(len(clean_text("x" * 50_000)), 20_000)

    def test_make_entry_rejects_empty(self) -> None:
        self.assertIsNone(make_entry(""))
        self.assertIsNone(make_entry("   "))

    def test_add_entry_keeps_newest_first_and_dedupes(self) -> None:
        items: list[dict] = []
        items = add_entry(items, "one", now=datetime(2026, 1, 1, 10, 0, 0))
        items = add_entry(items, "two", now=datetime(2026, 1, 1, 10, 1, 0))
        items = add_entry(items, "one", now=datetime(2026, 1, 1, 10, 2, 0))
        self.assertEqual([row["text"] for row in items], ["one", "two"])

    def test_limit_is_respected(self) -> None:
        items: list[dict] = []
        for index in range(20):
            items = add_entry(items, f"line {index}", limit=12)
        self.assertEqual(len(items), 12)
        self.assertEqual(items[0]["text"], "line 19")

    def test_search_is_case_insensitive(self) -> None:
        items = add_entry([], "Привіт Світ")
        self.assertEqual(len(search(items, "світ")), 1)
        self.assertEqual(len(search(items, "нема")), 0)
        self.assertEqual(len(search(items, "")), 1)

    def test_remove_entry(self) -> None:
        items = add_entry([], "value")
        self.assertEqual(remove_entry(items, items[0]["id"]), [])


if __name__ == "__main__":
    unittest.main()
