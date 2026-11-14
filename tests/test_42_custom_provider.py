# -*- coding: utf-8 -*-
"""Custom OpenAI-compatible provider and settings parity."""
from __future__ import annotations

import unittest

from core.config import DEFAULT_CONFIG as CORE_DEFAULT_CONFIG
from core.config import MODEL_CHOICES
from core.model_router import ModelRouter
from tests.helpers import import_jarvis
from ui.settings import CUSTOM_FIELDS, KEY_FIELDS

PROVIDER_FIELDS = (
    "openrouter_key",
    "gemini_api_key",
    "groq_api_key",
    "xkiro_api_key",
    "deepseek_api_key",
    "cerebras_api_key",
    "mistral_api_key",
    "together_api_key",
    "ashna_api_key",
    "openai_api_key",
    "anthropic_api_key",
    "xai_api_key",
    "moonshot_api_key",
    "qwen_api_key",
    "cursor_api_key",
    "custom_api_key",
)


class CustomProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.jarvis = import_jarvis()

    def test_config_schema_has_every_provider(self) -> None:
        for field in PROVIDER_FIELDS:
            self.assertIn(field, self.jarvis.DEFAULT_CONFIG, field)
            self.assertIn(field, CORE_DEFAULT_CONFIG, field)
        self.assertTrue(CUSTOM_FIELDS)
        exposed = {field for field, _ in KEY_FIELDS}
        self.assertTrue(set(PROVIDER_FIELDS).issubset(exposed))

    def test_brain_resolves_custom_provider(self) -> None:
        cfg = dict(self.jarvis.DEFAULT_CONFIG)
        cfg.update(
            {
                "model": "custom/my-model",
                "custom_provider_name": "Proxy",
                "custom_api_url": "https://proxy.example/v1/chat/completions",
                "custom_api_key": "key-one, key-two",
                "custom_model": "real-model-id",
            }
        )
        brain = self.jarvis.Brain(cfg)
        candidates = [
            item
            for item in brain._candidates()
            if item["model"] == "custom/my-model"
        ]
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0]["url"], "https://proxy.example/v1/chat/completions")
        self.assertEqual(candidates[0]["api_model"], "real-model-id")
        self.assertEqual(candidates[0]["provider"], "Proxy")
        self.assertEqual({item["key"] for item in candidates}, {"key-one", "key-two"})

    def test_brain_skips_custom_without_url_or_key(self) -> None:
        cfg = dict(self.jarvis.DEFAULT_CONFIG)
        cfg["model"] = "custom/my-model"
        cfg["custom_api_url"] = ""
        cfg["custom_api_key"] = ""
        brain = self.jarvis.Brain(cfg)
        self.assertFalse(
            [item for item in brain._candidates() if item["model"] == "custom/my-model"]
        )

    def test_model_router_custom_endpoint(self) -> None:
        router = ModelRouter(
            {
                "custom_api_url": "https://api.example/v1/chat/completions",
                "custom_api_key": "k1;k2",
                "custom_model": "router-model",
            }
        )
        endpoints = router._resolve_endpoints("custom/whatever")
        self.assertEqual(
            endpoints,
            [
                ("https://api.example/v1/chat/completions", "router-model", "k1"),
                ("https://api.example/v1/chat/completions", "router-model", "k2"),
            ],
        )

    def test_model_choices_still_available(self) -> None:
        self.assertIn("openai-direct/gpt-6.1-sol", MODEL_CHOICES)


if __name__ == "__main__":
    unittest.main()
