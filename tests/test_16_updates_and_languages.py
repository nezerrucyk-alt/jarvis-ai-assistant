# -*- coding: utf-8 -*-
"""Регресія для мов перекладу екрана та безпечного check-for-updates (без мережі)."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import import_jarvis


class VersionHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.jarvis = import_jarvis()

    def test_version_tuple_strips_prefix(self) -> None:
        self.assertEqual(self.jarvis._version_tuple("v2.0.0"), (2, 0, 0))
        self.assertEqual(self.jarvis._version_tuple("2.1"), (2, 1))
        self.assertEqual(self.jarvis._version_tuple(""), (0,))

    def test_is_newer_version(self) -> None:
        cases = (
            ("2.1.0", "2.0.0", True),
            ("2.0.1", "2.0.0", True),
            ("2.0.0", "2.0.0", False),
            ("2.0", "2.0.0", False),
            ("2.10.0", "2.9.0", True),
            ("3.0.0", "2.9.9", True),
            ("1.9.9", "2.0.0", False),
        )
        for latest, current, expected in cases:
            with self.subTest(latest=latest, current=current):
                self.assertEqual(self.jarvis.is_newer_version(latest, current), expected)


class TranslationTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.jarvis = import_jarvis()

    def test_default_is_ukrainian(self) -> None:
        self.assertEqual(
            self.jarvis.JarvisApp._translation_target("переклади екран"),
            ("українську", "УКРАЇНСЬКА"),
        )

    def test_new_languages(self) -> None:
        cases = (
            ("переклади на французьку", ("французьку", "FRANÇAIS")),
            ("translate to japanese", ("японську", "日本語")),
            ("іспанською будь ласка", ("іспанську", "ESPAÑOL")),
            ("на німецьку", ("німецьку", "DEUTSCH")),
            ("переклади китайською", ("китайську", "中文")),
            ("translate to korean", ("корейську", "한국어")),
            ("на чеську", ("чеську", "ČEŠTINA")),
        )
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(self.jarvis.JarvisApp._translation_target(text), expected)

    def test_existing_languages_still_work(self) -> None:
        self.assertEqual(
            self.jarvis.JarvisApp._translation_target("на англійську"),
            ("англійську", "ENGLISH"),
        )
        self.assertEqual(
            self.jarvis.JarvisApp._translation_target("польською"),
            ("польську", "POLSKI"),
        )


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._payload


class _FakeTools:
    update_runner = None

    def log(self, *_args, **_kwargs) -> None:
        pass


class CheckUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.jarvis = import_jarvis()
        self.fake = _FakeTools()

    def test_tool_is_registered(self) -> None:
        names = {
            tool.get("function", {}).get("name")
            for tool in self.jarvis.TOOLS
        }
        self.assertIn("check_update", names)
        self.assertTrue(hasattr(self.jarvis.PcTools, "_check_update"))

    def test_reports_newer_release(self) -> None:
        payload = {
            "tag_name": "v9.9.9",
            "html_url": "https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/tag/v9.9.9",
            "assets": [
                {"name": "JARVIS.exe", "browser_download_url": "https://github.com/x/JARVIS.exe"},
            ],
        }
        with mock.patch("requests.get", return_value=_FakeResponse(200, payload)):
            result = self.jarvis.PcTools._check_update(self.fake)
        self.assertIn("9.9.9", result)
        self.assertIn("нова версія", result)
        self.assertIn("https://github.com/x/JARVIS.exe", result)

    def test_finds_windows_suffixed_asset(self) -> None:
        payload = {
            "tag_name": "v9.9.9",
            "html_url": "https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/tag/v9.9.9",
            "assets": [
                {
                    "name": "JARVIS-Windows.exe",
                    "browser_download_url": "https://github.com/x/JARVIS-Windows.exe",
                    "size": 1234,
                    "digest": "sha256:" + "a" * 64,
                },
            ],
        }
        with mock.patch("requests.get", return_value=_FakeResponse(200, payload)):
            info = self.jarvis.fetch_latest_release_info()
        self.assertEqual(info["asset_url"], "https://github.com/x/JARVIS-Windows.exe")
        self.assertEqual(info["asset_size"], 1234)
        self.assertEqual(info["asset_sha256"], "a" * 64)

    def test_prefers_plain_exe_when_both_exist(self) -> None:
        payload = {
            "tag_name": "v9.9.9",
            "html_url": "https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/tag/v9.9.9",
            "assets": [
                {"name": "JARVIS-Windows.exe", "browser_download_url": "https://github.com/x/win.exe"},
                {"name": "JARVIS.exe", "browser_download_url": "https://github.com/x/plain.exe"},
            ],
        }
        with mock.patch("requests.get", return_value=_FakeResponse(200, payload)):
            info = self.jarvis.fetch_latest_release_info()
        self.assertEqual(info["asset_url"], "https://github.com/x/plain.exe")

    def test_reports_current_when_same(self) -> None:
        payload = {
            "tag_name": "v" + self.jarvis.APP_VERSION,
            "html_url": "https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/latest",
        }
        with mock.patch("requests.get", return_value=_FakeResponse(200, payload)):
            result = self.jarvis.PcTools._check_update(self.fake)
        self.assertIn("актуальна", result)

    def test_handles_no_releases(self) -> None:
        with mock.patch("requests.get", return_value=_FakeResponse(404)):
            result = self.jarvis.PcTools._check_update(self.fake)
        self.assertIn("Опублікованих релізів ще немає", result)

    def test_triggers_interactive_runner_when_newer(self) -> None:
        captured = {}

        class _RunnerTools(_FakeTools):
            def update_runner(self, info) -> None:
                captured["info"] = info

        payload = {
            "tag_name": "v9.9.9",
            "html_url": "https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/tag/v9.9.9",
            "assets": [{"name": "JARVIS.exe", "browser_download_url": "https://github.com/x/JARVIS.exe"}],
        }
        with mock.patch("requests.get", return_value=_FakeResponse(200, payload)):
            result = self.jarvis.PcTools._check_update(_RunnerTools())
        self.assertIn("9.9.9", captured.get("info", {}).get("latest", ""))
        self.assertIn("вікно оновлення", result)


class FetchReleaseInfoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.jarvis = import_jarvis()

    def test_parses_asset_size_and_digest(self) -> None:
        payload = {
            "tag_name": "v9.9.9",
            "html_url": "https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/tag/v9.9.9",
            "assets": [
                {"name": "other.zip", "browser_download_url": "https://github.com/x/other.zip"},
                {
                    "name": "JARVIS.exe",
                    "browser_download_url": "https://github.com/x/JARVIS.exe",
                    "size": 12345,
                    "digest": "sha256:ABCDEF",
                },
            ],
        }
        with mock.patch("requests.get", return_value=_FakeResponse(200, payload)):
            info = self.jarvis.fetch_latest_release_info()
        self.assertTrue(info["ok"])
        self.assertTrue(info["is_newer"])
        self.assertEqual(info["latest"], "9.9.9")
        self.assertEqual(info["asset_url"], "https://github.com/x/JARVIS.exe")
        self.assertEqual(info["asset_size"], 12345)
        self.assertEqual(info["asset_sha256"], "abcdef")

    def test_rejects_non_github_page(self) -> None:
        payload = {"tag_name": "v9.9.9", "html_url": "https://evil.example/x"}
        with mock.patch("requests.get", return_value=_FakeResponse(200, payload)):
            info = self.jarvis.fetch_latest_release_info()
        self.assertFalse(info["ok"])

    def test_network_error_is_reported(self) -> None:
        with mock.patch("requests.get", side_effect=RuntimeError("offline")):
            info = self.jarvis.fetch_latest_release_info()
        self.assertFalse(info["ok"])
        self.assertIn("Не вдалося перевірити оновлення", info["error"])


class VerifyDownloadedExeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.jarvis = import_jarvis()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "JARVIS.exe"
        self.data = b"jarvis-binary-content" * 100
        self.path.write_bytes(self.data)
        self.sha = hashlib.sha256(self.data).hexdigest()

    def test_accepts_matching_size_and_hash(self) -> None:
        ok, _ = self.jarvis.verify_downloaded_exe(self.path, len(self.data), self.sha)
        self.assertTrue(ok)

    def test_accepts_when_hash_unknown(self) -> None:
        ok, _ = self.jarvis.verify_downloaded_exe(self.path, len(self.data), "")
        self.assertTrue(ok)

    def test_rejects_size_mismatch(self) -> None:
        ok, why = self.jarvis.verify_downloaded_exe(self.path, len(self.data) + 1, self.sha)
        self.assertFalse(ok)
        self.assertIn("Розмір", why)

    def test_rejects_hash_mismatch(self) -> None:
        ok, why = self.jarvis.verify_downloaded_exe(self.path, len(self.data), "0" * 64)
        self.assertFalse(ok)
        self.assertIn("SHA256", why)


class UpdaterScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.jarvis = import_jarvis()

    def test_script_waits_swaps_and_rolls_back(self) -> None:
        script = self.jarvis.UPDATER_SCRIPT
        self.assertIn("Get-Process -Name 'JARVIS'", script)
        self.assertIn("Move-Item", script)
        self.assertIn("Start-Process", script)
        self.assertIn(".old", script)
        self.assertIn("catch", script)


class HomeAssistantActionTests(unittest.TestCase):
    """Мапінг дій smart_home → сервіси HA. Мережа повністю замокана."""

    def setUp(self) -> None:
        self.jarvis = import_jarvis()
        self.states = [
            {"entity_id": "light.kitchen", "state": "on",
             "attributes": {"friendly_name": "Кухня світло"}},
            {"entity_id": "climate.office", "state": "heat",
             "attributes": {"friendly_name": "Офіс клімат"}},
            {"entity_id": "cover.blind", "state": "closed", "attributes": {}},
            {"entity_id": "lock.front", "state": "locked", "attributes": {}},
            {"entity_id": "media_player.tv", "state": "idle", "attributes": {}},
            {"entity_id": "vacuum.roomba", "state": "docked", "attributes": {}},
            {"entity_id": "camera.door", "state": "idle",
             "attributes": {"friendly_name": "Двері", "entity_picture": "/api/camera_proxy/camera.door"}},
        ]
        self.tools = self.jarvis.PcTools.__new__(self.jarvis.PcTools)
        self.tools.get_cfg = lambda: {
            "home_assistant_url": "http://ha.local:8123",
            "home_assistant_token": "test-token",
        }
        self.tools.log = lambda *_a, **_k: None

    def _run(self, action, entity, value=""):
        get_resp = _FakeResponse(200, self.states)
        post_resp = _FakeResponse(200, {})
        with mock.patch("requests.get", return_value=get_resp), \
                mock.patch("requests.post", return_value=post_resp) as post_mock:
            result = self.jarvis.PcTools._smart_home(self.tools, action, entity, value)
        return result, post_mock

    def _service(self, post_mock):
        args, kwargs = post_mock.call_args
        url = args[0]
        service = url.split("/api/services/", 1)[1]
        return service, kwargs.get("json")

    def test_set_temperature(self) -> None:
        result, post = self._run("set_temp", "climate.office", "22.5")
        service, payload = self._service(post)
        self.assertEqual(service, "climate/set_temperature")
        self.assertEqual(payload["temperature"], 22.5)
        self.assertIn("Готово", result)

    def test_hvac_mode(self) -> None:
        _, post = self._run("hvac", "climate.office", "cool")
        service, payload = self._service(post)
        self.assertEqual(service, "climate/set_hvac_mode")
        self.assertEqual(payload["hvac_mode"], "cool")

    def test_open_cover(self) -> None:
        _, post = self._run("open", "cover.blind")
        self.assertEqual(self._service(post)[0], "cover/open_cover")

    def test_lock(self) -> None:
        _, post = self._run("lock", "lock.front")
        self.assertEqual(self._service(post)[0], "lock/lock")

    def test_media_pause(self) -> None:
        _, post = self._run("pause", "media_player.tv")
        self.assertEqual(self._service(post)[0], "media_player/media_pause")

    def test_vacuum_dock(self) -> None:
        _, post = self._run("vacuum_dock", "vacuum.roomba")
        self.assertEqual(self._service(post)[0], "vacuum/return_to_base")

    def test_brightness(self) -> None:
        _, post = self._run("brightness", "light.kitchen", "40")
        service, payload = self._service(post)
        self.assertEqual(service, "light/turn_on")
        self.assertEqual(payload["brightness_pct"], 40)

    def test_camera_returns_state_without_post(self) -> None:
        result, post = self._run("camera", "camera.door")
        self.assertIn("камера", result)
        self.assertIn("http://ha.local:8123/api/camera_proxy/camera.door", result)
        post.assert_not_called()

    def test_invalid_temperature_is_rejected(self) -> None:
        result, post = self._run("set_temp", "climate.office", "гаряче")
        self.assertIn("температуру числом", result)
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()