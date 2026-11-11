# -*- coding: utf-8 -*-
"""Прямі провайдери, вкладення та черга завдань Command Deck."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import JarvisAppEnv


class DirectProviderTests(JarvisAppEnv):
    app_config = {
        "plugins_enabled": False,
        "mute": True,
        "greet": False,
        "response_mode": "max",
    }

    def test_new_direct_models_are_registered(self) -> None:
        expected = {
            "openai-direct/gpt-6.1-sol",
            "anthropic-direct/claude-opus-5.5",
            "xai-direct/grok-4.7",
            "moonshot-direct/kimi-k3",
            "qwen-direct/qwen3.8-max",
            "cursor/composer-2.5",
        }
        self.assertTrue(expected.issubset(self.jarvis.DIRECT_MODEL_CONFIG))
        anthropic = self.jarvis.DIRECT_MODEL_CONFIG[
            "anthropic-direct/claude-opus-5.5"
        ]
        self.assertEqual(anthropic.get("api_style"), "anthropic")
        self.assertTrue(anthropic.get("vision"))
        self.assertIn("max", self.jarvis.RESPONSE_MODES)
        self.assertEqual(self.jarvis.RESPONSE_MODES["max"]["label"], "Макс")

    def test_anthropic_blocks_and_role_merge(self) -> None:
        blocks = self.jarvis.Brain._anthropic_blocks(
            [
                {"type": "text", "text": "привіт"},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64,AAAA"},
                },
            ]
        )
        self.assertEqual(blocks[0], {"type": "text", "text": "привіт"})
        self.assertEqual(blocks[1]["type"], "image")
        self.assertEqual(blocks[1]["source"]["media_type"], "image/png")
        self.assertEqual(blocks[1]["source"]["data"], "AAAA")

        merged = self.jarvis.Brain._merge_anthropic_messages(
            [
                {"role": "assistant", "content": [{"type": "text", "text": "x"}]},
                {"role": "user", "content": [{"type": "text", "text": "a"}]},
                {"role": "user", "content": [{"type": "text", "text": "b"}]},
            ]
        )
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["role"], "user")
        self.assertEqual(len(merged[0]["content"]), 2)

    def test_candidates_resolve_cursor_endpoint_and_vision(self) -> None:
        cfg = dict(self.jarvis.DEFAULT_CONFIG)
        cfg.update(
            {
                "cursor_api_key": "cursor-key",
                "cursor_api_url": "https://proxy.example/v1/chat/completions",
                "cursor_model": "custom-composer",
                "anthropic_api_key": "anthropic-key",
                "model": "cursor/composer-2.5",
            }
        )
        brain = self.jarvis.Brain(cfg)
        cursor = [
            candidate
            for candidate in brain._candidates()
            if candidate["model"] == "cursor/composer-2.5"
        ]
        self.assertTrue(cursor)
        self.assertEqual(
            cursor[0]["url"], "https://proxy.example/v1/chat/completions"
        )
        self.assertEqual(cursor[0]["api_model"], "custom-composer")

        anthropic = [
            candidate
            for candidate in brain._candidates(needs_vision=True)
            if candidate["model"] == "anthropic-direct/claude-opus-5.5"
        ]
        self.assertTrue(anthropic)
        self.assertEqual(anthropic[0]["api_style"], "anthropic")
        self.assertTrue(anthropic[0]["vision"])

    def test_build_messages_embeds_text_and_image_attachments(self) -> None:
        cfg = dict(self.jarvis.DEFAULT_CONFIG)
        cfg["response_mode"] = "max"
        brain = self.jarvis.Brain(cfg)

        messages, mode = brain._build_messages(
            "Що тут?",
            [
                {
                    "kind": "text",
                    "name": "example.py",
                    "text": "print('hello')",
                }
            ],
        )
        self.assertEqual(mode["label"], "Макс")
        self.assertIn("[ВКЛАДЕНИЙ ФАЙЛ: example.py]", messages[-1]["content"])
        self.assertIn("print('hello')", messages[-1]["content"])

        from PIL import Image

        with tempfile.TemporaryDirectory(prefix="jarvis_attach_") as tmp:
            image_path = Path(tmp) / "tiny.png"
            Image.new("RGB", (2, 2), (10, 20, 30)).save(image_path)
            messages, _ = brain._build_messages(
                "Опиши зображення",
                [
                    {
                        "kind": "image",
                        "name": "tiny.png",
                        "path": str(image_path),
                    }
                ],
            )
        content = messages[-1]["content"]
        self.assertIsInstance(content, list)
        self.assertEqual(content[0]["type"], "text")
        self.assertEqual(content[1]["type"], "image_url")
        self.assertTrue(content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))


class CommandDeckQueueTests(JarvisAppEnv):
    app_config = {
        "plugins_enabled": False,
        "mute": True,
        "greet": False,
        "response_mode": "natural",
        "model": "anthropic-direct/claude-sonnet-5.5",
    }

    def _write_composer(self, app, text: str) -> None:
        app._on_entry_focus_in()
        app.entry.delete("1.0", "end")
        app.entry.insert("1.0", text)

    def test_enqueue_while_busy_keeps_snapshot_and_clears_composer(self) -> None:
        app = self.make_app()
        app.busy.set()
        self._write_composer(app, "  Перевір чергу  ")
        app._enqueue_current()
        self.assertEqual(len(app.prompt_queue), 1)
        item = app.prompt_queue[0]
        self.assertEqual(item["text"], "Перевір чергу")
        self.assertEqual(item["model"], app.cfg.get("model"))
        self.assertEqual(item["mode"], "natural")
        self.assertEqual(app._composer_text(), "")
        self.assertFalse(app.attach_panel.winfo_ismapped())
        app.busy.clear()

    def test_send_while_busy_enqueues_instead_of_starting_thread(self) -> None:
        app = self.make_app()
        app.busy.set()
        self._write_composer(app, "Завдання в чергу")
        app._on_send()
        self.assertEqual(len(app.prompt_queue), 1)
        self.assertEqual(app.prompt_queue[0]["text"], "Завдання в чергу")
        app.busy.clear()

    def test_apply_queue_context_restores_model_and_mode(self) -> None:
        app = self.make_app()
        app._apply_queue_context(
            {
                "model": "openai-direct/gpt-5.3-codex",
                "mode": "max",
            }
        )
        self.assertEqual(app.cfg["model"], "openai-direct/gpt-5.3-codex")
        self.assertEqual(app.cfg["response_mode"], "max")
        self.assertEqual(app.mode_var.get(), "Макс")
        self.assertIn("GPT-5.3 Codex", app.model_var.get())

    def test_render_queue_updates_counter_and_removes_item(self) -> None:
        app = self.make_app()
        app.prompt_queue.extend(
            [
                {"text": "Перше", "attachments": [], "model": "", "mode": ""},
                {"text": "Друге", "attachments": [], "model": "", "mode": ""},
            ]
        )
        app._render_queue()
        self.assertEqual(app.queue_count_label.cget("text"), "2")
        app._remove_queue_item(0)
        self.assertEqual(app.queue_count_label.cget("text"), "1")
        app._clear_queue()
        self.assertEqual(app.prompt_queue, [])
        self.assertEqual(app.queue_count_label.cget("text"), "0")


if __name__ == "__main__":
    unittest.main()
