# -*- coding: utf-8 -*-
"""v2 (модульний застосунок): імпорт main, headless Dashboard і JarvisUltimateApp.

УВАГА: APPDATA перенаправляється у тимчасовий каталог **до** імпорту main,
щоб жоден тест не торкався реального %APPDATA%\\Jarvis.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import tkinter as tk

from tests.helpers import pump

_TMP_APPDATA = tempfile.mkdtemp(prefix="jarvis_v2_appdata_")
_OLD_APPDATA = os.environ.get("APPDATA")
os.environ["APPDATA"] = _TMP_APPDATA

import main  # noqa: E402  (імпорт після підміни APPDATA — навмисно)


def tearDownModule() -> None:
    if _OLD_APPDATA is None:
        os.environ.pop("APPDATA", None)
    else:
        os.environ["APPDATA"] = _OLD_APPDATA
    shutil.rmtree(_TMP_APPDATA, ignore_errors=True)


class ModularAppTests(unittest.TestCase):
    def _write_test_config(self) -> None:
        config = dict(main.load_config())
        config.update(
            {
                "mute": True,
                "greet": False,
                "voice_hotkey": False,
                "always_on_top": False,
                "use_memory": False,
            }
        )
        main.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        main.CONFIG_PATH.write_text(
            json.dumps(config, ensure_ascii=False), encoding="utf-8"
        )

    def test_main_imports_and_uses_temp_appdata(self) -> None:
        self.assertIsNotNone(main)
        self.assertTrue(str(main.DATA_DIR).startswith(_TMP_APPDATA), str(main.DATA_DIR))
        self.assertTrue(str(main.CONFIG_PATH).startswith(_TMP_APPDATA), str(main.CONFIG_PATH))
        self.assertTrue(hasattr(main, "JarvisUltimateApp"))
        self.assertTrue(hasattr(main, "Dashboard"))
        self.assertTrue(hasattr(main, "main"))

    def test_dashboard_constructs_withdrawn_root(self) -> None:
        root = tk.Tk()
        root.withdraw()
        try:
            dashboard = main.Dashboard(
                root=root,
                on_send_callback=lambda text: None,
                on_emergency_stop_callback=lambda: None,
            )
            pump(root, 250)
            self.assertEqual(root.state(), "withdrawn")
            dashboard.post_message("J.A.R.V.I.S.", "тестове повідомлення", tag="jarvis")
            pump(root, 250)
            self.assertIn("тестове повідомлення", dashboard.chat_text.get("1.0", "end"))
            self.assertTrue(hasattr(dashboard, "btn_stop"))
            self.assertTrue(hasattr(dashboard, "chat_text"))
            dashboard.stop()
        finally:
            try:
                root.destroy()
            except tk.TclError:
                pass

    def test_dashboard_mic_button_only_with_callback(self) -> None:
        root = tk.Tk()
        root.withdraw()
        try:
            dashboard = main.Dashboard(
                root=root,
                on_send_callback=lambda text: None,
                on_mic_callback=lambda: None,
                on_settings_callback=lambda: None,
            )
            pump(root, 150)
            self.assertIsNotNone(dashboard.mic_btn)
            self.assertIsNotNone(dashboard.on_mic)
            self.assertIsNotNone(dashboard.on_settings)
            dashboard.stop()
        finally:
            try:
                root.destroy()
            except tk.TclError:
                pass

    def test_full_app_constructs_and_handles_message(self) -> None:
        self._write_test_config()
        root = tk.Tk()
        root.withdraw()
        app = None
        try:
            app = main.JarvisUltimateApp(root, config=main.load_config())
            pump(root, 350)
            self.assertIsNotNone(app.dashboard)
            self.assertIsNotNone(app.brain)
            self.assertIsNotNone(app.store)
            self.assertIsNotNone(app.voice)
            self.assertIsNotNone(app.ears)
            self.assertIsNotNone(app.pc)

            class StubBrain:
                def process(self, text: str, session_id: str = "default") -> str:
                    return "stub-reply"

            app.brain = StubBrain()
            app.handle_user_message("привіт")
            pump(root, 600)
            self.assertIn("stub-reply", app.dashboard.chat_text.get("1.0", "end"))

            app.handle_emergency_stop()
            self.assertTrue(app.security.is_stopped)
            app.handle_emergency_stop()
            self.assertFalse(app.security.is_stopped)

            app.open_settings()
            pump(root, 250)
            self.assertIsNotNone(app._settings_window)
            app._settings_window.destroy()
            pump(root, 100)
        finally:
            if app is not None:
                try:
                    app.shutdown()
                except Exception:  # noqa: BLE001 — завершення не має валити тест
                    pass
            try:
                root.destroy()
            except tk.TclError:
                pass


if __name__ == "__main__":
    unittest.main()
