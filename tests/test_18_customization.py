# -*- coding: utf-8 -*-
"""Тести системи кастомізації: схема, кольори, шрифти, код і збереження."""
from __future__ import annotations

import tempfile
import tkinter as tk
import tkinter.font as tkfont
import unittest
from pathlib import Path

from core.customization import (
    DEFAULT_THEME,
    MAIN_BLOCKS,
    THEME_PRESETS,
    apply_fonts,
    apply_theme,
    default_customization,
    derive_theme,
    load_customization,
    normalize_customization,
    render_custom_code,
    save_customization,
)


class CustomizationSchemaTests(unittest.TestCase):
    def test_default_contains_new_layout_fields(self) -> None:
        data = default_customization()
        self.assertEqual(data["layout"]["main_order"], list(MAIN_BLOCKS))
        self.assertIn("topbar", data["layout"]["main_order"])
        self.assertTrue(data["layout"]["sidebar_enabled"])
        self.assertIn("sidebar_order", data["layout"])
        self.assertFalse(data["custom_code_enabled"])

    def test_defaults_are_independent(self) -> None:
        first = default_customization()
        first["theme"]["accent"] = "#000000"
        first["layout"]["main_order"].reverse()
        second = default_customization()
        self.assertEqual(second["theme"]["accent"], DEFAULT_THEME["accent"])
        self.assertEqual(second["layout"]["main_order"], list(MAIN_BLOCKS))

    def test_normalize_clamps_and_deduplicates(self) -> None:
        data = normalize_customization(
            {
                "theme": {"accent": "#ABCDEF", "bg": "not-a-color"},
                "fonts": {"family": "  Consolas  ", "scale": 99},
                "layout": {
                    "main_order": ["footer", "footer", "unknown", "log"],
                    "sidebar_order": ["history", "history", "voice"],
                    "sidebar_enabled": "off",
                    "main_visible": {"hero": 0},
                    "animations": "no",
                },
                "custom_code": "x" * 50000,
                "custom_code_enabled": "yes",
            }
        )
        self.assertEqual(data["theme"]["accent"], "#abcdef")
        self.assertEqual(data["theme"]["bg"], DEFAULT_THEME["bg"])
        self.assertEqual(data["fonts"]["family"], "Consolas")
        self.assertEqual(data["fonts"]["scale"], 1.4)
        self.assertEqual(data["layout"]["main_order"][0], "footer")
        self.assertEqual(data["layout"]["main_order"].count("footer"), 1)
        self.assertEqual(data["layout"]["main_order"][-1], "composer")
        self.assertEqual(data["layout"]["sidebar_order"][0], "history")
        self.assertEqual(data["layout"]["sidebar_order"].count("history"), 1)
        self.assertFalse(data["layout"]["sidebar_enabled"])
        self.assertFalse(data["layout"]["main_visible"]["hero"])
        self.assertFalse(data["layout"]["animations"])
        self.assertTrue(data["custom_code_enabled"])
        self.assertEqual(len(data["custom_code"]), 24000)

    def test_save_and_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jarvis_custom_") as tmp:
            path = Path(tmp) / "customization.json"
            data = default_customization()
            data["theme"]["accent"] = "#12ab34"
            data["layout"]["compact"] = True
            saved = save_customization(path, data)
            loaded = load_customization(path)
            self.assertTrue(path.is_file())
            self.assertEqual(saved["theme"]["accent"], "#12ab34")
            self.assertEqual(loaded["theme"]["accent"], "#12ab34")
            self.assertTrue(loaded["layout"]["compact"])

    def test_corrupt_file_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jarvis_custom_") as tmp:
            path = Path(tmp) / "customization.json"
            path.write_text("{not json", encoding="utf-8")
            data = load_customization(path)
            self.assertEqual(data["theme"], DEFAULT_THEME)

    def test_derive_theme_adds_derived_roles(self) -> None:
        theme = derive_theme(THEME_PRESETS["ice"])
        for key in (
            "line_deep", "line_bright", "muted_dim", "text_bright",
            "ring_1", "ring_2", "ring_3", "accent_soft", "gold_soft",
        ):
            self.assertRegex(theme[key], r"^#[0-9a-f]{6}$")


class CustomizationTkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.configure(bg=DEFAULT_THEME["bg"])
        self.frame = tk.Frame(self.root, bg=DEFAULT_THEME["panel"])
        self.frame.pack()
        self.label = tk.Label(
            self.frame,
            text="test",
            bg=DEFAULT_THEME["bg"],
            fg=DEFAULT_THEME["text"],
            font=("Segoe UI", 10),
        )
        self.label.pack()

    def tearDown(self) -> None:
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def test_theme_can_be_changed_repeatedly(self) -> None:
        matrix = derive_theme(THEME_PRESETS["matrix"])
        apply_theme(self.root, matrix, derive_theme(DEFAULT_THEME))
        self.assertEqual(
            self.frame.cget("bg"), THEME_PRESETS["matrix"]["panel"].lower()
        )
        self.assertEqual(
            self.label.cget("bg"), THEME_PRESETS["matrix"]["bg"].lower()
        )
        self.assertEqual(
            self.label.cget("fg"), THEME_PRESETS["matrix"]["text"].lower()
        )

        crimson = derive_theme(THEME_PRESETS["crimson"])
        apply_theme(self.root, crimson, matrix)
        self.assertEqual(
            self.frame.cget("bg"), THEME_PRESETS["crimson"]["panel"].lower()
        )
        self.assertEqual(
            self.label.cget("bg"), THEME_PRESETS["crimson"]["bg"].lower()
        )
        self.assertEqual(
            self.label.cget("fg"), THEME_PRESETS["crimson"]["text"].lower()
        )

    def test_theme_skip_protects_widget_subtree(self) -> None:
        self.frame._theme_skip = True
        matrix = derive_theme(THEME_PRESETS["matrix"])
        apply_theme(self.root, matrix, derive_theme(DEFAULT_THEME))
        self.assertEqual(self.frame.cget("bg"), DEFAULT_THEME["panel"])
        self.assertEqual(self.label.cget("bg"), DEFAULT_THEME["bg"])

    def test_font_scale_roundtrip_uses_base_size(self) -> None:
        apply_fonts(self.root, "", 1.2)
        scaled = int(tkfont.Font(font=self.label.cget("font")).actual()["size"])
        self.assertEqual(scaled, 12)
        apply_fonts(self.root, "", 1.0)
        restored = int(
            tkfont.Font(font=self.label.cget("font")).actual()["size"]
        )
        self.assertEqual(restored, 10)

    def test_render_custom_code_builds_widget(self) -> None:
        host = tk.Frame(self.root)
        code = (
            "def build(parent, colors):\n"
            "    return tk.Label(parent, text='ok', bg=colors['panel'])\n"
        )
        widget = render_custom_code(code, host, derive_theme(DEFAULT_THEME))
        self.assertIsNotNone(widget)
        self.assertEqual(len(host.winfo_children()), 1)

    def test_render_custom_code_reports_errors(self) -> None:
        host = tk.Frame(self.root)
        with self.assertRaises(NameError):
            render_custom_code("unknown_name()", host, derive_theme(DEFAULT_THEME))


if __name__ == "__main__":
    unittest.main()
