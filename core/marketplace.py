# -*- coding: utf-8 -*-
"""Local plugin marketplace helpers.

The marketplace is deliberately boring: a JSON registry, plain ``.py`` files
and SHA256 checksums.  There is no server, no auto-update daemon and no silent
installation.  The UI shows the code size and hash, asks for confirmation and
only then copies the file into the user's plugins folder.

Plugins are trusted local code.  A checksum proves that the file matches the
registry, not that the code is safe; the confirmation dialog says so.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

MAX_PLUGIN_BYTES = 512 * 1024
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,40}$")
_FILE_RE = re.compile(r"^[A-Za-z0-9_.-]+\.py$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class MarketplaceError(ValueError):
    """Invalid registry entry or unsafe plugin file."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Validate one registry entry and return a normalized copy."""
    if not isinstance(entry, dict):
        raise MarketplaceError("Запис реєстру має бути об'єктом.")
    plugin_id = str(entry.get("id") or "").strip().lower()
    if not _ID_RE.match(plugin_id):
        raise MarketplaceError(f"Некоректний id плагіна: {plugin_id!r}.")
    name = str(entry.get("name") or "").strip()
    if not name or len(name) > 80:
        raise MarketplaceError(f"Некоректна назва плагіна {plugin_id!r}.")
    filename = str(entry.get("file") or "").strip()
    if not _FILE_RE.match(filename) or "/" in filename or "\\" in filename:
        raise MarketplaceError(f"Небезпечне ім'я файлу для {plugin_id!r}.")
    digest = str(entry.get("sha256") or "").strip().lower()
    if not _HASH_RE.match(digest):
        raise MarketplaceError(f"Некоректний SHA256 для {plugin_id!r}.")
    version = str(entry.get("version") or "1.0.0").strip()[:20]
    description = str(entry.get("description") or "").strip()[:400]
    author = str(entry.get("author") or "JARVIS community").strip()[:80]
    tags = entry.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    return {
        "id": plugin_id,
        "name": name,
        "version": version,
        "description": description,
        "author": author,
        "file": filename,
        "sha256": digest,
        "tags": [str(tag)[:24] for tag in tags[:8]],
    }


def load_registry(path: Path | str) -> list[dict[str, Any]]:
    """Load and validate a JSON registry file."""
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MarketplaceError(f"Реєстр плагінів не знайдено: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise MarketplaceError(f"Не вдалося прочитати реєстр плагінів: {exc}") from exc
    entries = payload.get("plugins") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        raise MarketplaceError("Реєстр має містити список plugins.")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in entries:
        normalized = validate_entry(entry)
        if normalized["id"] in seen:
            raise MarketplaceError(f"Дубльований id у реєстрі: {normalized['id']}.")
        seen.add(normalized["id"])
        result.append(normalized)
    return result


def installed_files(plugins_dir: Path | str) -> set[str]:
    directory = Path(plugins_dir)
    if not directory.is_dir():
        return set()
    return {path.name for path in directory.glob("*.py") if path.is_file()}


def install_plugin(
    entry: dict[str, Any],
    source: bytes,
    plugins_dir: Path | str,
    *,
    overwrite: bool = False,
) -> Path:
    """Verify ``source`` against the entry hash and copy it to ``plugins_dir``."""
    normalized = validate_entry(entry)
    if len(source) > MAX_PLUGIN_BYTES:
        raise MarketplaceError("Файл плагіна завеликий (максимум 512 КБ).")
    actual = sha256_bytes(source)
    if actual != normalized["sha256"]:
        raise MarketplaceError(
            "SHA256 не збігається. Файл пошкоджено або реєстр застарів."
        )
    directory = Path(plugins_dir)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / normalized["file"]
    if target.exists() and not overwrite:
        raise MarketplaceError(f"Плагін {target.name} уже встановлено.")
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_bytes(source)
    temporary.replace(target)
    return target


def uninstall_plugin(filename: str, plugins_dir: Path | str) -> Path:
    if not _FILE_RE.match(str(filename)):
        raise MarketplaceError("Небезпечне ім'я файлу.")
    target = Path(plugins_dir) / filename
    if not target.is_file():
        raise MarketplaceError(f"Плагін {filename} не знайдено.")
    target.unlink()
    return target


def registry_for_display(
    entries: Iterable[dict[str, Any]],
    installed: set[str],
) -> list[dict[str, Any]]:
    result = []
    for entry in entries:
        item = dict(entry)
        item["installed"] = entry["file"] in installed
        result.append(item)
    return result


__all__ = [
    "MAX_PLUGIN_BYTES",
    "MarketplaceError",
    "install_plugin",
    "installed_files",
    "load_registry",
    "registry_for_display",
    "sha256_bytes",
    "uninstall_plugin",
    "validate_entry",
]
