# -*- coding: utf-8 -*-
"""Headless-конструкція JarvisApp: withdrawn Tk-root + тимчасові шляхи даних."""
from __future__ import annotations

from core.customization import load_customization
from tests.helpers import JarvisAppEnv, pump


class JarvisAppConstructTests(JarvisAppEnv):
    def test_constructs_headlessly_without_exceptions(self) -> None:
        app = self.make_app()
        self.assertIsInstance(app.cfg, dict)
        self.assertIsInstance(app.chats, list)
        self.assertIsInstance(app.current_chat, dict)
        self.assertTrue(app.root.winfo_exists())

    def test_window_is_hidden(self) -> None:
        app = self.make_app()
        self.assertEqual(app.root.state(), "withdrawn")
        self.assertFalse(app.root.winfo_ismapped())

    def test_customization_applies_and_persists(self) -> None:
        app = self.make_app()
        data = dict(app.customization)
        data["theme"] = dict(data["theme"])
        data["theme"]["bg"] = "#010203"
        data["theme"]["sidebar"] = "#040506"
        data["layout"] = dict(data["layout"])
        data["layout"]["sidebar_enabled"] = False
        saved = app.apply_customization_data(data, persist=True)
        self.assertEqual(saved["theme"]["bg"], "#010203")
        self.assertEqual(app.theme["bg"], "#010203")
        self.assertEqual(app.sidebar.cget("bg"), "#040506")
        self.assertEqual(app.sidebar.winfo_manager(), "")
        self.assertTrue(self.jarvis.CUSTOMIZATION_PATH.is_file())
        loaded = load_customization(self.jarvis.CUSTOMIZATION_PATH)
        self.assertEqual(loaded["theme"]["bg"], "#010203")
        self.assertFalse(loaded["layout"]["sidebar_enabled"])

    def test_expected_widgets_exist(self) -> None:
        app = self.make_app()
        for attr in (
            "log", "entry", "reactor", "history_list", "new_chat_btn",
            "side_voice_btn", "mute_btn", "access_label", "chat_title_label",
            "provider_chip", "status", "mic_btn", "mode_var", "speak_var",
        ):
            self.assertTrue(hasattr(app, attr), f"відсутній віджет/атрибут {attr}")

    def test_initial_system_greeting_rendered(self) -> None:
        app = self.make_app()
        text = self.log_text(app).lower()
        self.assertIn("j.a.r.v.i.s.", text)
        self.assertIn("онлайн", text)

    def test_data_paths_are_inside_tempdir(self) -> None:
        app = self.make_app()
        for attr in ("CONFIG_PATH", "CHATS_PATH", "MEMORY_PATH", "REMINDERS_PATH", "LOG_PATH"):
            path = getattr(self.jarvis, attr)
            self.assertEqual(path.parent, self.tmp_dir, f"{attr} поза tempdir: {path}")

    def test_updates_do_not_raise_and_animation_runs(self) -> None:
        app = self.make_app(wait_ms=300)
        # реактор малюється у _animate; переконаємось, що canvas живий
        pump(app.root, 250)
        self.assertTrue(app.reactor.winfo_exists())
        self.assertTrue(len(app.reactor.find_all()) > 0)

    def test_new_chat_button_handler_does_not_crash(self) -> None:
        app = self.make_app()
        first = app.current_chat
        app.new_chat_btn.invoke()
        pump(app.root, 100)
        self.assertIsNotNone(app.current_chat)
        self.assertNotEqual(app.current_chat.get("id"), first.get("id"))


if __name__ == "__main__":
    import unittest

    unittest.main()
