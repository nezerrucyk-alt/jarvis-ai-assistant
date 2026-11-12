# -*- coding: utf-8 -*-
"""Регресії безпеки v1 PcTools: класифікація команд, підтвердження, захист файлів.

Жодна реальна PowerShell-команда не виконується: subprocess.run підмінюється.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import PROJECT_ROOT  # noqa: F401 — додає корінь проєкту в sys.path

import jarvis


class _FakeProc:
    def __init__(self, stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _tools(confirm_result: bool = False):
    calls: list[tuple[str, str]] = []

    def confirm(action: str, detail: str) -> bool:
        calls.append((action, detail))
        return confirm_result

    return jarvis.PcTools(confirm, lambda text: None), calls


class PcToolsClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tools, _ = _tools()

    def test_safe_read_only_commands(self) -> None:
        for command in (
            "Get-Process",
            "get-date",
            "dir",
            "systeminfo",
            "Get-ChildItem C:\\temp",
            "Get-Content C:\\temp\\notes.txt | Select-Object -First 5",
        ):
            with self.subTest(command=command):
                self.assertTrue(self.tools._is_safe(command), command)

    def test_dangerous_commands(self) -> None:
        for command in (
            "Remove-Item C:\\temp\\x -Recurse -Force",
            "Stop-Process -Name chrome",
            "Set-Content C:\\temp\\x.txt hello",
            "shutdown /s /t 0",
        ):
            with self.subTest(command=command):
                self.assertFalse(self.tools._is_safe(command), command)

    def test_bypass_attempts_blocked(self) -> None:
        """Регресія аудиту P1-1: обхід через .NET-методи/Start-Job/ланцюжки."""
        for command in (
            "Get-ChildItem C:\\temp -Recurse | ForEach-Object { $_.Delete() }",
            "Get-ChildItem C:\\temp | ForEach-Object { $_.MoveTo('C:\\temp2') }",
            "Get-Process; Start-Job -ScriptBlock { ([System.Net.WebClient]::new()).DownloadString('http://127.0.0.1/x') }",
            "Get-ChildItem C:\\temp | Remove-Item -Force",
            "Get-Content C:\\Users\\nezer\\.ssh\\id_rsa",
        ):
            with self.subTest(command=command):
                self.assertFalse(self.tools._is_safe(command), command)

    def test_catastrophic_commands(self) -> None:
        for command in (
            "Format-Volume -DriveLetter C",
            "diskpart",
            "Remove-Item C:\\ -Recurse -Force",
        ):
            with self.subTest(command=command):
                self.assertTrue(self.tools._catastrophic(command), command)


class PcToolsPowerShellFlowTests(unittest.TestCase):
    def test_safe_command_runs_without_confirmation(self) -> None:
        tools, calls = _tools(confirm_result=False)
        with mock.patch("jarvis.subprocess.run", return_value=_FakeProc()) as run_mock:
            result = tools._run_powershell("Get-Process")
        self.assertEqual(calls, [])
        run_mock.assert_called_once()
        self.assertIn("exit=0", result)

    def test_dangerous_command_requires_confirmation_and_is_refused(self) -> None:
        tools, calls = _tools(confirm_result=False)
        with mock.patch("jarvis.subprocess.run", return_value=_FakeProc()) as run_mock:
            result = tools._run_powershell("Remove-Item C:\\temp\\x -Recurse -Force")
        self.assertTrue(calls, "мав бути запит підтвердження")
        run_mock.assert_not_called()
        self.assertIn("відмовився", result.lower())

    def test_approved_dangerous_command_runs(self) -> None:
        tools, calls = _tools(confirm_result=True)
        with mock.patch("jarvis.subprocess.run", return_value=_FakeProc()) as run_mock:
            result = tools._run_powershell("Remove-Item C:\\temp\\x -Recurse -Force")
        self.assertTrue(calls)
        run_mock.assert_called_once()
        self.assertIn("exit=0", result)

    def test_catastrophic_blocked_even_if_confirmed(self) -> None:
        tools, calls = _tools(confirm_result=True)
        with mock.patch("jarvis.subprocess.run", return_value=_FakeProc()) as run_mock:
            result = tools._run_powershell("Format-Volume -DriveLetter C")
        self.assertEqual(calls, [])
        run_mock.assert_not_called()
        self.assertIn("Заблоковано", result)


class FileToolSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="jarvis_sec_")
        self.addCleanup(self._tmp.cleanup)
        self.tmp_dir = Path(self._tmp.name)

    def test_sensitive_file_requires_confirmation(self) -> None:
        path = self.tmp_dir / "config.json"
        path.write_text('{"demo": 1}', encoding="utf-8")
        tools, calls = _tools(confirm_result=False)
        result = tools._read_file(str(path))
        self.assertTrue(calls, "для конфіденційного файлу мав бути запит підтвердження")
        self.assertIn("відмовився", result.lower())

        allowed, allowed_calls = _tools(confirm_result=True)
        result_ok = allowed._read_file(str(path))
        self.assertTrue(allowed_calls)
        self.assertIn('"demo": 1', result_ok)

    def test_regular_file_read_without_confirmation(self) -> None:
        path = self.tmp_dir / "notes.txt"
        path.write_text("привіт, сер", encoding="utf-8")
        tools, calls = _tools(confirm_result=False)
        result = tools._read_file(str(path))
        self.assertEqual(calls, [])
        self.assertIn("привіт, сер", result)

    def test_unknown_target_requires_confirmation(self) -> None:
        tools, calls = _tools(confirm_result=False)
        with mock.patch("jarvis.os.startfile", create=True) as startfile_mock:
            result = tools._open_app("C:\\Downloads\\some_unknown_tool.exe")
        self.assertTrue(calls, "невідомий шлях має питати підтвердження")
        startfile_mock.assert_not_called()
        self.assertIn("відмовився", result.lower())

    def test_known_site_alias_opens_without_confirmation(self) -> None:
        tools, calls = _tools(confirm_result=False)
        # Ізолюємо від реального Start Menu: на машині може бути PWA «YouTube»,
        # і тоді відкриється застосунок, а не сайт.
        with (
            mock.patch.object(jarvis.PcTools, "_get_start_apps", return_value=[]),
            mock.patch.object(jarvis.PcTools, "_get_registry_apps", return_value=[]),
            mock.patch.object(jarvis.PcTools, "_common_app_paths", return_value=""),
            mock.patch("jarvis.shutil.which", return_value=None),
            mock.patch("webbrowser.open") as browser_mock,
        ):
            result = tools._open_app("youtube")
        self.assertEqual(calls, [])
        browser_mock.assert_called_once_with("https://www.youtube.com")
        self.assertIn("Відкрив", result)

    def test_write_file_requires_confirmation(self) -> None:
        target = self.tmp_dir / "sample.txt"
        denied, denied_calls = _tools(confirm_result=False)
        result = denied._write_file(str(target), "дані")
        self.assertTrue(denied_calls)
        self.assertFalse(target.exists())
        self.assertIn("скасовано", result.lower())

        allowed, allowed_calls = _tools(confirm_result=True)
        result_ok = allowed._write_file(str(target), "дані")
        self.assertTrue(allowed_calls)
        self.assertEqual(target.read_text(encoding="utf-8"), "дані")
        self.assertIn("Записано", result_ok)


if __name__ == "__main__":
    unittest.main()
