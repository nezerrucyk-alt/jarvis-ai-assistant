# -*- coding: utf-8 -*-
"""Тести modules/: імпорт, чисті функції, аліаси, класифікація команд, підтвердження."""
from __future__ import annotations

import sys
import unittest
from unittest import mock

import modules

HEAVY_MODULES = ("pygame", "sounddevice", "edge_tts", "pyautogui", "pygetwindow", "speech_recognition")


class ModulesImportTests(unittest.TestCase):
    def test_modules_package(self) -> None:
        self.assertEqual(modules.__version__, "2.0.0")

    def test_voice_exports(self) -> None:
        from modules.voice import (
            VOICE_BY_LANG,
            VOICES,
            Ears,
            EarsError,
            Voice,
            VoiceError,
            for_speech,
            has_input_device,
            list_input_devices,
        )

        self.assertTrue(callable(for_speech))
        self.assertTrue(VOICE_BY_LANG)
        self.assertTrue(VOICES)
        for obj in (Voice, Ears, EarsError, VoiceError, has_input_device, list_input_devices):
            self.assertIsNotNone(obj)

    def test_computer_control_exports(self) -> None:
        from modules.computer_control import (
            APP_ALIASES,
            RISK_CATASTROPHIC,
            RISK_DANGEROUS,
            RISK_SAFE,
            SITE_ALIASES,
            PcController,
            classify_command,
            normalize_alias,
        )

        self.assertTrue(SITE_ALIASES)
        self.assertTrue(APP_ALIASES)
        self.assertEqual({RISK_SAFE, RISK_DANGEROUS, RISK_CATASTROPHIC}, {"safe", "dangerous", "catastrophic"})
        self.assertTrue(callable(classify_command))
        self.assertTrue(callable(normalize_alias))
        self.assertTrue(callable(PcController))

    def test_import_is_lazy_no_audio_network_libs(self) -> None:
        import modules.computer_control  # noqa: F401
        import modules.voice  # noqa: F401

        for name in HEAVY_MODULES:
            self.assertNotIn(name, sys.modules, f"{name} імпортований передчасно")


class ForSpeechTests(unittest.TestCase):
    def setUp(self) -> None:
        from modules.voice import for_speech

        self.for_speech = for_speech

    def test_strips_code_fences(self) -> None:
        result = self.for_speech("```python\nprint('hi')\n```")
        self.assertNotIn("```", result)
        self.assertNotIn("print", result)

    def test_strips_markdown_links_and_markers(self) -> None:
        self.assertEqual(self.for_speech("**жирний**"), "жирний")
        self.assertEqual(self.for_speech("[посилання](https://example.com)"), "посилання")

    def test_strips_emoji(self) -> None:
        self.assertEqual(self.for_speech("Привіт! 😀 Як справи?"), "Привіт! Як справи?")

    def test_caps_length(self) -> None:
        self.assertLessEqual(len(self.for_speech("а" * 5000)), 700)

    def test_empty_input(self) -> None:
        self.assertEqual(self.for_speech(""), "")
        self.assertEqual(self.for_speech(None), "")


class AliasResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        from modules.computer_control import PcController

        self.pc = PcController(confirm=None)

    def test_site_aliases(self) -> None:
        self.assertEqual(self.pc.resolve_target("youtube"), ("https://www.youtube.com", "site"))
        self.assertEqual(self.pc.resolve_target("ютуб"), ("https://www.youtube.com", "site"))
        self.assertEqual(self.pc.resolve_target("github"), ("https://github.com", "site"))

    def test_app_aliases(self) -> None:
        self.assertEqual(self.pc.resolve_target("notepad"), ("notepad.exe", "app"))
        self.assertEqual(self.pc.resolve_target("блокнот"), ("notepad.exe", "app"))
        self.assertEqual(self.pc.resolve_target("калькулятор"), ("calc.exe", "app"))

    def test_domain_is_opened_as_site(self) -> None:
        self.assertEqual(self.pc.resolve_target("google.com"), ("https://google.com", "site"))

    def test_unknown_target(self) -> None:
        self.assertFalse(self.pc.is_known_target("невідомапрограмабезшляху"))
        self.assertFalse(self.pc.is_known_target(""))

    def test_normalize_alias(self) -> None:
        from modules.computer_control import normalize_alias

        self.assertEqual(normalize_alias("Vs Code"), "vscode")
        self.assertEqual(normalize_alias("  Google Chrome "), "googlechrome")


class CommandClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        from modules.computer_control import classify_command

        self.classify = classify_command

    def test_safe_commands(self) -> None:
        from modules.computer_control import RISK_SAFE

        for command in ("Get-Process", "get-date", "dir", "systeminfo", "Get-ChildItem C:\\temp"):
            with self.subTest(command=command):
                self.assertEqual(self.classify(command), RISK_SAFE)

    def test_dangerous_commands(self) -> None:
        from modules.computer_control import RISK_DANGEROUS

        for command in (
            "Remove-Item C:\\temp\\x -Recurse -Force",
            "Stop-Process -Name chrome",
            "Set-Content C:\\temp\\x.txt hello",
            "shutdown /s /t 0",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.classify(command), RISK_DANGEROUS)

    def test_catastrophic_commands(self) -> None:
        from modules.computer_control import RISK_CATASTROPHIC

        for command in (
            "Format-Volume -DriveLetter C",
            "diskpart",
            "Remove-Item C:\\ -Recurse -Force",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.classify(command), RISK_CATASTROPHIC)

    def test_empty_command_is_dangerous(self) -> None:
        from modules.computer_control import RISK_DANGEROUS

        self.assertEqual(self.classify(""), RISK_DANGEROUS)
        self.assertEqual(self.classify("   "), RISK_DANGEROUS)

    def test_object_method_mutations_are_not_safe(self) -> None:
        """Регресія (аудит P1-1): $_.Delete()/MoveTo() не мають класифікуватись як safe."""
        from modules.computer_control import RISK_DANGEROUS

        command = "Get-ChildItem C:\\temp -Recurse | ForEach-Object { $_.Delete() }"
        self.assertEqual(self.classify(command), RISK_DANGEROUS)

    def test_start_job_web_download_is_not_safe(self) -> None:
        """Регресія (аудит P1-1): Start-Job + .NET WebClient не має бути safe."""
        from modules.computer_control import RISK_DANGEROUS

        command = (
            "Get-Process; Start-Job -ScriptBlock { "
            "([System.Net.WebClient]::new()).DownloadString('http://127.0.0.1/x') }"
        )
        self.assertEqual(self.classify(command), RISK_DANGEROUS)

    def test_pipe_to_destructive_cmdlet_is_dangerous(self) -> None:
        from modules.computer_control import RISK_DANGEROUS

        self.assertEqual(
            self.classify("Get-ChildItem C:\\temp | Remove-Item -Force"),
            RISK_DANGEROUS,
        )


class ConfirmationFlowTests(unittest.TestCase):
    """Небезпечні команди не мають виконуватися без підтвердження (без реальних команд)."""

    DANGEROUS = "Remove-Item C:\\temp\\x -Recurse -Force"

    def test_dangerous_command_requires_confirmation_and_does_not_execute(self) -> None:
        from modules.computer_control import PcController

        pc = PcController(confirm=lambda action, details: False, log=lambda message: None)
        with mock.patch.object(
            PcController, "_execute_powershell", return_value=(0, "SHOULD-NOT-RUN", "")
        ) as execute_mock:
            result = pc.run_powershell(self.DANGEROUS)
        execute_mock.assert_not_called()
        self.assertIn("відмовився", result.lower())

    def test_approved_dangerous_command_executes(self) -> None:
        from modules.computer_control import PcController

        pc = PcController(confirm=lambda action, details: True, log=lambda message: None)
        with mock.patch.object(
            PcController, "_execute_powershell", return_value=(0, "ok", "")
        ) as execute_mock:
            result = pc.run_powershell(self.DANGEROUS)
        execute_mock.assert_called_once()
        self.assertIn("exit=0", result)

    def test_no_confirmation_callback_refuses(self) -> None:
        from modules.computer_control import PcController

        pc = PcController(confirm=None, log=lambda message: None)
        with mock.patch.object(
            PcController, "_execute_powershell", return_value=(0, "SHOULD-NOT-RUN", "")
        ) as execute_mock:
            result = pc.run_powershell(self.DANGEROUS)
        execute_mock.assert_not_called()
        self.assertIn("потребує підтвердження", result.lower())

    def test_catastrophic_blocked_even_with_confirmation(self) -> None:
        from modules.computer_control import PcController

        pc = PcController(confirm=lambda action, details: True, log=lambda message: None)
        with mock.patch.object(
            PcController, "_execute_powershell", return_value=(0, "ok", "")
        ) as execute_mock:
            result = pc.run_powershell("Format-Volume -DriveLetter C")
        execute_mock.assert_not_called()
        self.assertIn("Заблоковано", result)

    def test_safe_command_executes_without_confirmation(self) -> None:
        from modules.computer_control import PcController

        confirm_calls: list[str] = []

        def confirm(action: str, details: str) -> bool:
            confirm_calls.append(action)
            return True

        pc = PcController(confirm=confirm, log=lambda message: None)
        with mock.patch.object(
            PcController, "_execute_powershell", return_value=(0, "ok", "")
        ) as execute_mock:
            result = pc.run_powershell("Get-Process")
        self.assertEqual(confirm_calls, [])
        execute_mock.assert_called_once()
        self.assertIn("exit=0", result)


class VoiceMuteTests(unittest.TestCase):
    def test_mute_disables_speech_without_audio(self) -> None:
        from modules.voice import Voice

        voice = Voice({"mute": True})
        self.assertTrue(voice.muted)
        self.assertFalse(voice.speak("тест озвучення"))

    def test_set_mute_toggle(self) -> None:
        from modules.voice import Voice

        voice = Voice({"mute": False})
        voice.set_mute(True)
        self.assertTrue(voice.muted)
        voice.set_mute(False)
        self.assertFalse(voice.muted)

    def test_ears_construction_is_offline(self) -> None:
        from modules.voice import Ears

        ears = Ears({"language": "uk-UA"})
        self.assertEqual(ears.language, "uk-UA")


if __name__ == "__main__":
    unittest.main()
