# -*- coding: utf-8 -*-
"""Tests for the local plugin marketplace."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.marketplace import (
    MarketplaceError,
    install_plugin,
    installed_files,
    load_registry,
    registry_for_display,
    sha256_bytes,
    uninstall_plugin,
    validate_entry,
)

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / "assets" / "marketplace"


def entry_for(data: bytes, **overrides) -> dict:
    entry = {
        "id": "test-plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "test",
        "author": "tests",
        "file": "test_plugin.py",
        "sha256": sha256_bytes(data),
        "tags": ["test"],
    }
    entry.update(overrides)
    return entry


class RegistryTests(unittest.TestCase):
    def test_bundled_registry_is_valid_and_hashes_match(self) -> None:
        entries = load_registry(MARKETPLACE / "registry.json")
        self.assertGreaterEqual(len(entries), 3)
        for entry in entries:
            with self.subTest(plugin=entry["id"]):
                data = (MARKETPLACE / "plugins" / entry["file"]).read_bytes()
                self.assertEqual(sha256_bytes(data), entry["sha256"])

    def test_rejects_bad_id_and_file(self) -> None:
        data = b"TOOLS = []\n"
        for overrides in (
            {"id": "../evil"},
            {"file": "../evil.py"},
            {"file": "evil.txt"},
            {"sha256": "not-a-hash"},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(MarketplaceError):
                    validate_entry(entry_for(data, **overrides))

    def test_load_registry_rejects_duplicates(self) -> None:
        data = b"TOOLS = []\n"
        payload = {
            "plugins": [
                entry_for(data),
                entry_for(data),
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(MarketplaceError):
                load_registry(path)


class InstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = b"TOOLS = []\n\ndef run(name, args, ctx):\n    return 'ok'\n"
        self.entry = entry_for(self.data)

    def test_install_and_uninstall(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugins = Path(tmp) / "plugins"
            target = install_plugin(self.entry, self.data, plugins)
            self.assertTrue(target.is_file())
            self.assertIn("test_plugin.py", installed_files(plugins))
            uninstall_plugin("test_plugin.py", plugins)
            self.assertFalse(target.exists())

    def test_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(MarketplaceError):
                install_plugin(self.entry, b"tampered", Path(tmp))

    def test_existing_plugin_needs_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugins = Path(tmp)
            install_plugin(self.entry, self.data, plugins)
            with self.assertRaises(MarketplaceError):
                install_plugin(self.entry, self.data, plugins)
            target = install_plugin(self.entry, self.data, plugins, overwrite=True)
            self.assertEqual(target.read_bytes(), self.data)

    def test_oversized_plugin_is_rejected(self) -> None:
        big = b"#" * (512 * 1024 + 1)
        entry = entry_for(big)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(MarketplaceError):
                install_plugin(entry, big, Path(tmp))

    def test_uninstall_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(MarketplaceError):
                uninstall_plugin("../config.json", Path(tmp))

    def test_display_marks_installed(self) -> None:
        displayed = registry_for_display([self.entry], {"test_plugin.py"})
        self.assertTrue(displayed[0]["installed"])
        self.assertNotIn("installed", self.entry)


if __name__ == "__main__":
    unittest.main()
