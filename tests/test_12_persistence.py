# -*- coding: utf-8 -*-
"""Регресії збереження даних v1: .bak-копія, збереження пошкоджених файлів, mute TTS."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import PROJECT_ROOT  # noqa: F401 — додає корінь проєкту в sys.path

import jarvis


class LocalStoreSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="jarvis_store_")
        self.addCleanup(self._tmp.cleanup)
        self.tmp_dir = Path(self._tmp.name)

    def test_save_local_records_creates_bak_backup(self) -> None:
        target = self.tmp_dir / "records.json"
        first = [{"id": "1", "text": "перший"}]
        second = [{"id": "2", "text": "другий"}]

        original_data_dir = jarvis.DATA_DIR
        jarvis.DATA_DIR = self.tmp_dir
        try:
            jarvis.save_local_records(target, first)
            self.assertTrue(target.is_file())
            jarvis.save_local_records(target, second)
        finally:
            jarvis.DATA_DIR = original_data_dir

        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), second)
        backup = target.with_name(target.name + ".bak")
        self.assertTrue(backup.is_file(), "попередня версія має зберігатися як .bak")
        self.assertEqual(json.loads(backup.read_text(encoding="utf-8")), first)

    def test_corrupt_store_is_preserved_as_corrupt_copy(self) -> None:
        target = self.tmp_dir / "chats.json"
        target.write_text("{ пошкоджений json", encoding="utf-8")
        records = jarvis.load_local_records(target)
        self.assertEqual(records, [])
        corrupt_copy = target.with_name(target.name + ".corrupt")
        self.assertTrue(corrupt_copy.is_file(), "пошкоджений файл має зберігатися як .corrupt")
        self.assertFalse(target.exists())

    def test_missing_store_returns_empty_list(self) -> None:
        self.assertEqual(jarvis.load_local_records(self.tmp_dir / "absent.json"), [])


class VoiceMuteRegressionTests(unittest.TestCase):
    def test_muted_voice_returns_without_network(self) -> None:
        voice = jarvis.Voice({"mute": True})
        self.assertIsNone(voice.speak("цей текст не має озвучуватись"))

    def test_voice_has_timeout_and_lock(self) -> None:
        voice = jarvis.Voice({"mute": False})
        self.assertGreater(jarvis.Voice.TTS_TIMEOUT, 0)
        self.assertTrue(hasattr(voice, "_lock"))


class StartupHardeningApiTests(unittest.TestCase):
    def test_single_instance_api_exists(self) -> None:
        self.assertTrue(callable(getattr(jarvis, "acquire_single_instance", None)))

    def test_selftest_and_main_exist(self) -> None:
        self.assertTrue(callable(jarvis.selftest))
        self.assertTrue(callable(jarvis.main))


if __name__ == "__main__":
    unittest.main()
