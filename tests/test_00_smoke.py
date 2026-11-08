# -*- coding: utf-8 -*-
"""Smoke-тести: компіляція всього коду, імпорт jarvis.py, відсутність «завислих» self.*."""
from __future__ import annotations

import unittest

from tests.helpers import PROJECT_ROOT, find_unresolved_self_attrs, import_jarvis

SKIP_DIRS = {".venv", "__pycache__", "_archive", "build", "dist", ".git", "tests"}


class CompileAndImportTests(unittest.TestCase):
    def test_all_project_python_files_compile(self) -> None:
        py_files = [
            path
            for path in PROJECT_ROOT.rglob("*.py")
            if not any(part in SKIP_DIRS for part in path.relative_to(PROJECT_ROOT).parts)
        ]
        self.assertGreaterEqual(len(py_files), 15, f"знайдено лише {len(py_files)} .py файлів")
        for path in py_files:
            with self.subTest(file=str(path.relative_to(PROJECT_ROOT))):
                source = path.read_text(encoding="utf-8")
                compile(source, str(path), "exec")  # SyntaxError -> тест падає

    def test_jarvis_imports_and_exposes_api(self) -> None:
        jarvis = import_jarvis()
        for name in (
            "JarvisApp", "PcTools", "Voice", "Ears", "Brain", "StudioMCP",
            "load_config", "save_config", "load_local_records", "save_local_records",
            "for_speech", "selftest", "main", "CHATS_PATH", "MAX_CHATS",
        ):
            self.assertTrue(hasattr(jarvis, name), f"jarvis.py не має {name}")

    def test_no_unresolved_self_references(self) -> None:
        source = (PROJECT_ROOT / "jarvis.py").read_text(encoding="utf-8")
        problems = find_unresolved_self_attrs(
            source,
            ("JarvisApp", "Brain", "PcTools", "Voice", "Ears", "StudioMCP"),
        )
        self.assertEqual(problems, {}, f"невизначені self.*: {problems}")

    def test_jarvis_import_does_not_create_gui_or_network(self) -> None:
        jarvis = import_jarvis()
        # імпорт модуля не запускає mainloop і не створює Tk-вікон
        self.assertIsNone(getattr(jarvis, "_STUDIO_BRIDGE", None))


if __name__ == "__main__":
    unittest.main()
