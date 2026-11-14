# -*- coding: utf-8 -*-
"""Interface translations for the desktop shell."""
from __future__ import annotations

import unittest

from core.i18n import (
    UI_LANGUAGES,
    normalize_language,
    sidebar_labels,
    t,
    translate_status,
)
from tests.helpers import JarvisAppEnv


class I18nTests(unittest.TestCase):
    def test_languages(self) -> None:
        codes = [code for code, _ in UI_LANGUAGES]
        self.assertEqual(codes, ["uk", "en", "pl", "de", "es", "fr"])

    def test_sidebar_translated(self) -> None:
        uk = sidebar_labels("uk")
        de = sidebar_labels("de")
        self.assertEqual(uk["voice"], "Голосовий режим")
        self.assertEqual(de["voice"], "Sprachmodus")
        self.assertEqual(de["clipboard"], "Zwischenablage")
        self.assertEqual(sidebar_labels("pl")["new_chat"], "Nowa rozmowa")
        self.assertEqual(sidebar_labels("fr")["settings"], "Paramètres")

    def test_status_translation(self) -> None:
        self.assertEqual(translate_status("Думаю…", "de"), "Denke nach…")
        self.assertEqual(translate_status("Готовий, сер.", "es"), "Listo, señor.")
        self.assertEqual(translate_status("Щось інше", "de"), "Щось інше")

    def test_normalize(self) -> None:
        self.assertEqual(normalize_language("FR"), "fr")
        self.assertEqual(normalize_language("xx"), "uk")
        self.assertEqual(normalize_language(None), "uk")
        self.assertEqual(t("sidebar.history", "pl"), "Cała historia")


class AppLanguageTests(JarvisAppEnv):
    app_config = {
        "plugins_enabled": False,
        "mute": True,
        "greet": False,
        "clipboard_history": False,
        "ui_language": "de",
    }

    def test_german_sidebar_and_status(self) -> None:
        app = self.make_app()
        self.assertIn("Sprachmodus", app.side_voice_btn.cget("text"))
        self.assertIn("Zwischenablage", app.clipboard_btn.cget("text"))
        app.set_status("Думаю…")
        self.assertIn("Denke", app.status.cget("text"))


if __name__ == "__main__":
    unittest.main()
