# -*- coding: utf-8 -*-
"""Sorts a folder (Downloads by default) into category subfolders.

``plan`` is always a dry run: it only lists what would move. ``apply_plan``
performs the moves (or simulates them) and never overwrites existing files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Optional

CATEGORIES: dict[str, frozenset[str]] = {
    "Images": frozenset(
        {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico", ".heic", ".avif"}
    ),
    "Documents": frozenset(
        {
            ".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".xls", ".xlsx",
            ".ods", ".csv", ".ppt", ".pptx", ".odp", ".epub", ".djvu",
        }
    ),
    "Video": frozenset(
        {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv", ".mpg", ".mpeg", ".m4v"}
    ),
    "Audio": frozenset({".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".wma"}),
    "Archives": frozenset({".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"}),
    "Code": frozenset(
        {
            ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".html", ".css", ".scss",
            ".c", ".h", ".cpp", ".hpp", ".cs", ".java", ".go", ".rs", ".sh", ".ps1",
            ".yml", ".yaml", ".toml", ".sql", ".lua",
        }
    ),
    "Installers": frozenset({".exe", ".msi", ".msix", ".appx", ".apk", ".dmg", ".deb", ".rpm"}),
}

PARTIAL_SUFFIXES = (".crdownload", ".part", ".download", ".tmp", ".opdownload")
DEFAULT_LIMIT = 500


class FileOrganizerError(ValueError):
    """Invalid folder or plan."""


def category_for(name: str) -> str:
    suffix = Path(str(name or "")).suffix.lower()
    for category, extensions in CATEGORIES.items():
        if suffix in extensions:
            return category
    return "Other"


def is_partial(name: str) -> bool:
    lower = str(name or "").casefold()
    return any(lower.endswith(suffix) for suffix in PARTIAL_SUFFIXES)


def plan(folder: str | Path, limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    """Lists files that would move; folders, hidden and partial files are skipped."""
    root = Path(folder).expanduser()
    if not root.is_dir():
        raise FileOrganizerError(f"Папка не знайдена: {root}")
    try:
        limit = max(1, min(int(limit), 5000))
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT

    moves: list[dict[str, Any]] = []
    try:
        entries = sorted(root.iterdir(), key=lambda p: p.name.casefold())
    except OSError as exc:
        raise FileOrganizerError(f"Не вдалося прочитати папку: {exc}") from exc

    for entry in entries:
        if len(moves) >= limit:
            break
        try:
            if not entry.is_file():
                continue
        except OSError:
            continue
        if entry.name.startswith(".") or is_partial(entry.name):
            continue
        category = category_for(entry.name)
        target = root / category / entry.name
        if entry.parent == target.parent:
            continue
        try:
            size = entry.stat().st_size
        except OSError:
            size = 0
        moves.append(
            {
                "source": str(entry),
                "target": str(target),
                "category": category,
                "size": size,
            }
        )
    return moves


def unique_path(path: str | Path) -> Path:
    """Returns ``path`` or a ``name (2).ext`` variant that does not exist yet."""
    target = Path(path)
    if not target.exists():
        return target
    for index in range(2, 1000):
        candidate = target.with_name(f"{target.stem} ({index}){target.suffix}")
        if not candidate.exists():
            return candidate
    raise FileOrganizerError(f"Не вдалося підібрати вільне ім'я для {target.name}")


def apply_plan(moves: Iterable[dict[str, Any]], dry_run: bool = True) -> dict[str, Any]:
    """Moves planned files; with ``dry_run`` only reports what would happen."""
    moved: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    for move in moves:
        raw_source = str((move or {}).get("source") or "")
        raw_target = str((move or {}).get("target") or "")
        if not raw_source or not raw_target:
            skipped.append(raw_source or "?")
            continue
        source = Path(raw_source)
        target = Path(raw_target)
        try:
            if not source.is_file():
                skipped.append(source.name)
                continue
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                final = unique_path(target)
                source.rename(final)
                moved.append(f"{source.name} → {final.parent.name}/{final.name}")
            else:
                moved.append(f"{source.name} → {target.parent.name}/{target.name}")
        except OSError as exc:
            errors.append(f"{source.name}: {exc}")

    return {
        "dry_run": bool(dry_run),
        "moved": moved,
        "skipped": skipped,
        "errors": errors,
    }


def snapshot(folder: str | Path) -> dict[str, tuple[int, int]]:
    """Returns ``{path: (mtime_ns, size)}`` for regular files in the folder."""
    root = Path(folder).expanduser()
    result: dict[str, tuple[int, int]] = {}
    try:
        entries = root.iterdir()
    except OSError:
        return result
    for entry in entries:
        try:
            if not entry.is_file():
                continue
            stat = entry.stat()
        except OSError:
            continue
        result[str(entry)] = (stat.st_mtime_ns, stat.st_size)
    return result


def new_files(
    previous: dict[str, tuple[int, int]],
    current: Optional[dict[str, tuple[int, int]]] = None,
) -> list[str]:
    """Returns freshly appeared or finished files since the previous snapshot."""
    current = current if current is not None else previous
    fresh: list[str] = []
    for path, meta in current.items():
        if is_partial(path) or Path(path).name.startswith("."):
            continue
        if previous.get(path) != meta:
            fresh.append(path)
    return sorted(fresh, key=str.casefold)


__all__ = [
    "CATEGORIES",
    "DEFAULT_LIMIT",
    "FileOrganizerError",
    "apply_plan",
    "category_for",
    "is_partial",
    "new_files",
    "plan",
    "snapshot",
    "unique_path",
]
