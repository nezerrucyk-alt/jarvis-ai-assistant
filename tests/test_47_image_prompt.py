# -*- coding: utf-8 -*-
"""Chat-model prompt engineering for gpt-image-1."""
from __future__ import annotations

import unittest

from core.image_prompt import clean_prompt, enhance_prompt


class PromptCleanTests(unittest.TestCase):
    def test_strips_fences_quotes_and_labels(self) -> None:
        raw = '```text\nPrompt: "A cozy night dev room, neon, cinematic."\n```'
        self.assertEqual(
            clean_prompt(raw), "A cozy night dev room, neon, cinematic."
        )

    def test_strips_chatter(self) -> None:
        raw = "Sure! Here is the prompt: a yellow hoodie hero at a desk."
        self.assertEqual(
            clean_prompt(raw), "a yellow hoodie hero at a desk."
        )

    def test_collapses_whitespace(self) -> None:
        self.assertEqual(clean_prompt("  a\n\n b\t c  "), "a b c")


class PromptEnhanceTests(unittest.TestCase):
    def test_uses_refined_prompt(self) -> None:
        seen: list[list[dict]] = []

        def complete(messages, **kwargs):
            seen.append(messages)
            return "Cinematic 3D render of a developer in a yellow hoodie, neon room, soft grain."

        result = enhance_prompt("намалюй кота", complete)
        self.assertTrue(result.startswith("Cinematic 3D"))
        self.assertEqual(seen[0][0]["role"], "system")
        self.assertIn("намалюй кота", seen[0][1]["content"])

    def test_falls_back_on_error(self) -> None:
        def complete(messages, **kwargs):
            raise RuntimeError("no provider")

        self.assertEqual(enhance_prompt("намалюй кота", complete), "намалюй кота")

    def test_falls_back_on_tiny_answer(self) -> None:
        self.assertEqual(
            enhance_prompt("намалюй кота", lambda *a, **k: "ok"), "намалюй кота"
        )

    def test_caps_length(self) -> None:
        long_text = "word " * 200

        result = enhance_prompt("idea", lambda *a, **k: long_text, max_chars=60)
        self.assertLessEqual(len(result), 60)
        self.assertFalse(result.endswith(" "))


if __name__ == "__main__":
    unittest.main()
