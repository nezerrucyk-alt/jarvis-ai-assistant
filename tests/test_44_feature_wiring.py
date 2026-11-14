# -*- coding: utf-8 -*-
"""App-level wiring for the new features (headless)."""
from __future__ import annotations

import unittest

from tests.helpers import JarvisAppEnv


class FeatureWiringTests(JarvisAppEnv):
    app_config = {
        "plugins_enabled": False,
        "mute": True,
        "greet": False,
        "clipboard_history": True,
        "watch_downloads": False,
        "telegram_enabled": False,
        "hud_enabled": False,
    }

    def test_new_tools_are_registered(self) -> None:
        app = self.make_app()
        names = {
            tool["function"]["name"]
            for tool in self.jarvis.TOOLS
            if isinstance(tool, dict)
        }
        for name in (
            "clipboard_history",
            "clipboard_copy",
            "organize_downloads",
            "daily_briefing",
        ):
            self.assertIn(name, names)

    def test_clipboard_tools_work(self) -> None:
        app = self.make_app()
        copied = app.tools.run("clipboard_copy", {"text": "тест буфера"})
        self.assertIn("скопійовано", copied.lower())
        app.clipboard_items = self.jarvis.clipboard_store.add_entry(
            [], "тест буфера"
        )
        history = app.tools.run("clipboard_history", {"query": "буфера"})
        self.assertIn("тест буфера", history)

    def test_organizer_preview_keeps_files(self) -> None:
        app = self.make_app()
        folder = self.tmp_dir / "Downloads"
        folder.mkdir()
        (folder / "photo.png").write_text("x", encoding="utf-8")
        result = app.tools.run("organize_downloads", {"folder": str(folder)})
        self.assertIn("photo.png", result)
        self.assertIn("apply=true", result)
        self.assertTrue((folder / "photo.png").exists())

    def test_daily_briefing_tool_uses_runner(self) -> None:
        app = self.make_app()
        app.tools.briefing_runner = lambda: "БРИФІНГ-ТЕСТ"
        self.assertEqual(app.tools.run("daily_briefing", {}), "БРИФІНГ-ТЕСТ")

    def test_sidebar_has_new_entries(self) -> None:
        app = self.make_app()
        for key in ("clipboard", "organizer", "briefing"):
            self.assertIn(key, self.jarvis.SIDEBAR_ITEMS)
            self.assertIn(key, app.sidebar_buttons)
            self.assertIn(key, self.jarvis.SIDEBAR_LABELS)

    def test_telegram_and_watcher_stay_off_by_default(self) -> None:
        app = self.make_app()
        self.assertIsNone(app._telegram_bot)
        self.assertIsNone(app._watch_thread)
        self.assertIsNone(app.hud)


if __name__ == "__main__":
    unittest.main()
