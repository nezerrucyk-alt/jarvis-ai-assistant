# -*- coding: utf-8 -*-
"""Спільні утиліти регресійних тестів JARVIS (лише stdlib).

* жодних мережевих/аудіо-викликів і видимих вікон;
* усі шляхи даних jarvis.py підмінюються тимчасовим каталогом;
* тихий лог (INFO/WARNING застосунку не засмічують вивід тестів).
"""
from __future__ import annotations

import ast
import json
import logging
import sys
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from typing import Any, Optional
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Тести мають бути тихими: приглушуємо INFO/WARNING/ERROR застосунку.
logging.disable(logging.CRITICAL)

JARVIS_PATH_VARS = (
    "DATA_DIR",
    "CONFIG_PATH",
    "LOG_PATH",
    "MEMORY_PATH",
    "REMINDERS_PATH",
    "AUTOMATIONS_PATH",
    "CHATS_PATH",
    "CUSTOMIZATION_PATH",
    "ICON_PATH",
)

TEST_CONFIG: dict[str, Any] = {
    "mute": True,
    "greet": False,
    "voice_hotkey": False,
    "always_on_top": False,
    "model": "xkiro/qwen/qwen3.7-flash:free",
    "language": "uk-UA",
    "voice": "uk-UA-OstapNeural",
    "use_memory": False,
    "full_access": True,
    "response_mode": "natural",
}


def import_jarvis():
    """Імпортує jarvis.py (шлях проєкту вже в sys.path)."""
    import jarvis  # noqa: PLC0415 — ліниво, щоб тести могли керувати sys.path

    return jarvis


def install_temp_paths(jarvis_module, tmp_dir: Path, config: Optional[dict] = None) -> dict:
    """Підмінює всі шляхи даних jarvis.py на тимчасовий каталог.

    Повертає збережені оригінальні значення для tearDown.
    """
    saved = {name: getattr(jarvis_module, name) for name in JARVIS_PATH_VARS if hasattr(jarvis_module, name)}
    tmp_dir = Path(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    jarvis_module.DATA_DIR = tmp_dir
    jarvis_module.CONFIG_PATH = tmp_dir / "config.json"
    jarvis_module.LOG_PATH = tmp_dir / "jarvis.log"
    jarvis_module.MEMORY_PATH = tmp_dir / "memory.json"
    jarvis_module.REMINDERS_PATH = tmp_dir / "reminders.json"
    jarvis_module.AUTOMATIONS_PATH = tmp_dir / "automations.json"
    jarvis_module.CHATS_PATH = tmp_dir / "chats.json"
    jarvis_module.CUSTOMIZATION_PATH = tmp_dir / "customization.json"
    jarvis_module.ICON_PATH = tmp_dir / "missing_icon.ico"  # не читаємо реальну іконку

    cfg = dict(TEST_CONFIG)
    cfg.update(config or {})
    jarvis_module.CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False), encoding="utf-8"
    )
    return saved


def restore_paths(jarvis_module, saved: dict) -> None:
    for name, value in saved.items():
        setattr(jarvis_module, name, value)


def pump(root: tk.Tk, milliseconds: int = 450) -> None:
    """Прокручує події Tk невеликими квантами (замість mainloop)."""
    deadline = time.monotonic() + milliseconds / 1000.0
    while time.monotonic() < deadline:
        try:
            root.update()
        except tk.TclError:
            return
        time.sleep(0.01)


def install_after_tracker(root: tk.Tk) -> list[str]:
    """Обгортає root.after, щоб скасувати всі таймери перед destroy.

    Інакше Tcl друкує «invalid command name ... ("after" script)», коли
    таймер спрацьовує після знищення Tk-інтерпретатора.
    """
    ids: list[str] = []
    original_after = root.after

    def tracked_after(ms, func=None, *args):  # type: ignore[no-untyped-def]
        if func is None:
            return original_after(ms)
        after_id = original_after(ms, func, *args)
        ids.append(after_id)
        return after_id

    root.after = tracked_after  # type: ignore[assignment]
    return ids


def cancel_after_ids(root: tk.Tk, ids: list[str]) -> None:
    for after_id in list(ids):
        try:
            root.after_cancel(after_id)
        except Exception:  # noqa: BLE001 — таймер уже міг спрацювати
            pass
    ids.clear()


def close_app(app) -> None:
    """Коректно закриває JarvisApp (зберігає чати, зупиняє мовлення)."""
    if app is None:
        return
    root = getattr(app, "root", None)
    ids = getattr(app, "_test_after_ids", None)
    if root is not None and ids:
        cancel_after_ids(root, ids)
    try:
        app._on_close()
    except Exception:  # noqa: BLE001 — закриття не повинно валити тест
        pass


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def chat_message_texts(chat: dict) -> list[str]:
    return [
        str(item.get("text", ""))
        for item in (chat.get("messages") or [])
        if isinstance(item, dict)
    ]


def find_unresolved_self_attrs(
    source: str, class_names: tuple[str, ...] = ("JarvisApp",)
) -> dict[str, dict[str, list[int]]]:
    """AST-перевірка: кожен `self.X`, який читається, має бути десь визначений.

    Повертає {клас: {атрибут: [рядки]}} для «зависших» звернень.
    """
    tree = ast.parse(source)
    problems: dict[str, dict[str, list[int]]] = {}

    class Collector(ast.NodeVisitor):
        def __init__(self) -> None:
            self.defs: set[str] = set()
            self.methods: set[str] = set()
            self.class_attrs: set[str] = set()
            self.loads: dict[str, list[int]] = {}

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.methods.add(item.name)
                elif isinstance(item, (ast.Assign, ast.AnnAssign)):
                    targets = item.targets if isinstance(item, ast.Assign) else [item.target]
                    for target in targets:
                        if isinstance(target, ast.Name):
                            self.class_attrs.add(target.id)
            for child in node.body:
                self.visit(child)

        def visit_Assign(self, node: ast.Assign) -> None:
            for target in node.targets:
                self._collect_target(target)
            self.generic_visit(node)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            self._collect_target(node.target)
            self.generic_visit(node)

        def visit_AugAssign(self, node: ast.AugAssign) -> None:
            self._collect_target(node.target)
            self.generic_visit(node)

        def _collect_target(self, node: ast.AST) -> None:
            for sub in ast.walk(node):
                if (
                    isinstance(sub, ast.Attribute)
                    and isinstance(sub.value, ast.Name)
                    and sub.value.id == "self"
                ):
                    self.defs.add(sub.attr)

        def visit_Attribute(self, node: ast.Attribute) -> None:
            if (
                isinstance(node.value, ast.Name)
                and node.value.id == "self"
                and isinstance(node.ctx, ast.Load)
            ):
                self.loads.setdefault(node.attr, []).append(node.lineno)
            self.generic_visit(node)

    for item in ast.walk(tree):
        if isinstance(item, ast.ClassDef) and item.name in class_names:
            collector = Collector()
            collector.visit(item)
            missing = {
                attr: sorted(set(lines))
                for attr, lines in collector.loads.items()
                if attr not in collector.defs
                and attr not in collector.methods
                and attr not in collector.class_attrs
                and attr != "__class__"
            }
            if missing:
                problems[item.name] = missing
    return problems


class JarvisAppEnv(unittest.TestCase):
    """База headless-тестів JarvisApp: tempfile-шляхи + withdrawn Tk-root."""

    app_config: Optional[dict] = None

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="jarvis_tests_")
        self.addCleanup(self._tmp.cleanup)
        self.tmp_dir = Path(self._tmp.name)

        self.jarvis = import_jarvis()
        self._saved_paths = install_temp_paths(self.jarvis, self.tmp_dir, self.app_config)
        self.addCleanup(restore_paths, self.jarvis, self._saved_paths)

        # Не тягнемо pygame і не чіпаємо аудіо при закритті застосунку.
        self._voice_stop_patch = mock.patch.object(self.jarvis.Voice, "stop", lambda self: None)
        self._voice_stop_patch.start()
        self.addCleanup(self._voice_stop_patch.stop)

        self._app = None

    def tearDown(self) -> None:
        app, self._app = self._app, None
        close_app(app)

    # ── допоміжні методи ────────────────────────────────────────────────────
    def rewrite_config(self, **changes: Any) -> None:
        cfg = dict(TEST_CONFIG)
        cfg.update(changes)
        self.jarvis.CONFIG_PATH.write_text(
            json.dumps(cfg, ensure_ascii=False), encoding="utf-8"
        )

    def make_app(self, wait_ms: int = 450):
        root = tk.Tk()
        root.withdraw()
        after_ids = install_after_tracker(root)
        app = self.jarvis.JarvisApp(root)
        app._test_after_ids = after_ids  # для скасування таймерів у tearDown
        self._app = app
        pump(root, wait_ms)
        return app

    def close_current_app(self) -> None:
        app, self._app = self._app, None
        close_app(app)

    @staticmethod
    def log_text(app) -> str:
        return app.log.get("1.0", "end")

    def saved_chats(self):
        return read_json(self.jarvis.CHATS_PATH)

    def make_chat(self, question: str, answer: str):
        """Додає в поточний чат репліку користувача й асистента."""
        app = self._app
        app._log("you", question)
        app._log("jarvis", answer)
        return app.current_chat
