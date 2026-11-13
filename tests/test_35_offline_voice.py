# -*- coding: utf-8 -*-
"""Tests for offline whisper.cpp / Piper backends."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from modules.voice.offline import (
    OfflineVoiceError,
    capabilities,
    language_code,
    stt_available,
    synthesize,
    transcribe,
    tts_available,
)


class DetectionTests(unittest.TestCase):
    def test_language_code(self) -> None:
        self.assertEqual(language_code("uk-UA"), "uk")
        self.assertEqual(language_code("ru-RU"), "ru")
        self.assertEqual(language_code("en-US"), "en")
        self.assertEqual(language_code("pt-BR"), "pt")
        self.assertEqual(language_code(""), "uk")

    def test_missing_paths_mean_unavailable(self) -> None:
        cfg = {
            "offline_stt_binary": "C:/definitely/missing/whisper-cli.exe",
            "offline_whisper_model": "C:/definitely/missing/model.bin",
            "offline_tts_binary": "C:/definitely/missing/piper.exe",
            "offline_piper_model": "C:/definitely/missing/voice.onnx",
        }
        with mock.patch("modules.voice.offline.shutil.which", return_value=None):
            self.assertFalse(stt_available(cfg))
            self.assertFalse(tts_available(cfg))
            caps = capabilities(cfg)
        self.assertFalse(caps["stt_available"])
        self.assertFalse(caps["tts_available"])
        self.assertEqual(caps["stt_binary"], "")
        self.assertEqual(caps["tts_binary"], "")

    def test_existing_files_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "whisper-cli.exe"
            model = root / "ggml-base.bin"
            binary.write_bytes(b"")
            model.write_bytes(b"")
            cfg = {
                "offline_stt_binary": str(binary),
                "offline_whisper_model": str(model),
            }
            self.assertTrue(stt_available(cfg))

    def test_unconfigured_backends_raise_actionable_errors(self) -> None:
        with mock.patch("modules.voice.offline.shutil.which", return_value=None):
            with self.assertRaises(OfflineVoiceError) as stt_error:
                transcribe(b"\x00\x00" * 32, 16000, {})
            with self.assertRaises(OfflineVoiceError) as tts_error:
                synthesize("привіт", {}, Path("out.wav"))
        self.assertIn("offline_stt_binary", str(stt_error.exception))
        self.assertIn("offline_tts_binary", str(tts_error.exception))


class CommandTests(unittest.TestCase):
    def test_transcribe_uses_command_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "whisper-cli.exe"
            model = root / "ggml.bin"
            script = root / "fake_whisper.py"
            binary.write_bytes(b"")
            model.write_bytes(b"")
            script.write_text(
                "import pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "out = pathlib.Path(args[args.index('--out') + 1])\n"
                "out.with_suffix('.txt').write_text('привіт з офлайну', encoding='utf-8')\n",
                encoding="utf-8",
            )
            cfg = {
                "offline_stt_binary": str(binary),
                "offline_whisper_model": str(model),
                "offline_stt_command": (
                    f'"{sys.executable}" "{script}" --out {{output}}'
                ),
            }
            text = transcribe(b"\x00\x00" * 64, 16000, cfg, "uk-UA")
        self.assertEqual(text, "привіт з офлайну")

    def test_transcribe_reports_nonzero_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "whisper-cli.exe"
            model = root / "ggml.bin"
            script = root / "fail.py"
            binary.write_bytes(b"")
            model.write_bytes(b"")
            script.write_text("import sys; sys.exit(3)\n", encoding="utf-8")
            cfg = {
                "offline_stt_binary": str(binary),
                "offline_whisper_model": str(model),
                "offline_stt_command": f'"{sys.executable}" "{script}"',
            }
            with self.assertRaises(OfflineVoiceError) as ctx:
                transcribe(b"\x00\x00" * 64, 16000, cfg)
        self.assertIn("кодом 3", str(ctx.exception))

    def test_synthesize_writes_audio_via_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "piper.exe"
            model = root / "voice.onnx"
            script = root / "fake_piper.py"
            output = root / "out.wav"
            binary.write_bytes(b"")
            model.write_bytes(b"")
            script.write_text(
                "import pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "out = pathlib.Path(args[args.index('--out') + 1])\n"
                "out.write_bytes(b'RIFF-fake')\n",
                encoding="utf-8",
            )
            cfg = {
                "offline_tts_binary": str(binary),
                "offline_piper_model": str(model),
                "offline_tts_command": (
                    f'"{sys.executable}" "{script}" --out {{output}}'
                ),
            }
            result = synthesize("привіт", cfg, output)
            self.assertEqual(result, output)
            self.assertEqual(output.read_bytes(), b"RIFF-fake")

    def test_synthesize_rejects_empty_text(self) -> None:
        with self.assertRaises(OfflineVoiceError):
            synthesize("   ", {}, Path("out.wav"))


if __name__ == "__main__":
    unittest.main()
