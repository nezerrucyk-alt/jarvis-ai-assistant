# -*- coding: utf-8 -*-
"""Tests for offline model routing in Brain."""
from __future__ import annotations

import unittest

from tests.helpers import import_jarvis


class OfflineRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.jarvis = import_jarvis()
        self.brain = object.__new__(self.jarvis.Brain)
        self.brain._last_good = None
        self.brain._dead_keys = set()

    def candidates(self, **cfg) -> list[dict]:
        self.brain.cfg = {
            "model": "openai-direct/gpt-6.1-sol",
            "openrouter_key": "or-key",
            "openai_api_key": "sk-test",
            **cfg,
        }
        return self.brain._candidates()

    def test_offline_mode_only_uses_ollama(self) -> None:
        candidates = self.candidates(offline_mode=True)
        self.assertTrue(candidates)
        self.assertTrue(
            all(item["provider"] == "Ollama · локально" for item in candidates)
        )
        self.assertFalse(any(item["key"] for item in candidates))

    def test_offline_mode_accepts_custom_model_name(self) -> None:
        candidates = self.candidates(
            offline_mode=True, offline_model="ollama/my-model:7b"
        )
        self.assertEqual(candidates[0]["model"], "ollama/my-model:7b")
        self.assertEqual(candidates[0]["api_model"], "my-model:7b")

    def test_offline_mode_respects_custom_ollama_url(self) -> None:
        candidates = self.candidates(
            offline_mode=True,
            offline_ollama_url="http://127.0.0.1:9999/v1/chat/completions",
        )
        self.assertEqual(
            candidates[0]["url"],
            "http://127.0.0.1:9999/v1/chat/completions",
        )

    def test_offline_vision_filter_keeps_only_vision_models(self) -> None:
        candidates = self.candidates(offline_mode=True)
        vision = self.brain._candidates(needs_vision=True)
        self.assertTrue(vision)
        self.assertTrue(all(item["vision"] for item in vision))
        self.assertGreaterEqual(len(candidates), len(vision))

    def test_online_mode_still_uses_cloud_keys(self) -> None:
        candidates = self.candidates(offline_mode=False)
        providers = {item["provider"] for item in candidates}
        self.assertIn("OpenRouter", providers)
        self.assertIn("OpenAI", providers)

    def test_vision_hint_helper(self) -> None:
        self.assertTrue(self.jarvis.ollama_model_supports_vision("ollama/gemma3:4b"))
        self.assertTrue(self.jarvis.ollama_model_supports_vision("llava:13b"))
        self.assertFalse(self.jarvis.ollama_model_supports_vision("ollama/llama3.2"))
        self.assertFalse(self.jarvis.ollama_model_supports_vision(""))


if __name__ == "__main__":
    unittest.main()
