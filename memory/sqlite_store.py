# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — SQLite Unified Store.
Provides thread-safe persistent storage for chat history, memories, projects, and task logs.
"""

from __future__ import annotations
import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Optional

DEFAULT_DB_PATH = Path(os.environ.get("APPDATA", ".")) / "Jarvis" / "jarvis_ultimate.db"


class SqliteStore:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._get_conn() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                agent_name TEXT DEFAULT 'user',
                timestamp REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL DEFAULT 'general',
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                agent_name TEXT DEFAULT 'core',
                status TEXT NOT NULL,
                result TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                agent TEXT NOT NULL,
                level TEXT NOT NULL,
                details TEXT,
                timestamp REAL NOT NULL
            );
            """)

    # ── Messages ─────────────────────────────────────────────────────────────
    def add_message(self, session_id: str, role: str, content: str, agent_name: str = "core") -> None:
        with self._lock, self._get_conn() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, agent_name, timestamp) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, agent_name, time.time()),
            )

    def get_recent_messages(self, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock, self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT role, content, agent_name, timestamp FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in reversed(rows)]

    # ── Long-term Memories ───────────────────────────────────────────────────
    def set_memory(self, key: str, value: str, category: str = "general") -> None:
        now = time.time()
        with self._lock, self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO memories (key, value, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, category=excluded.category, updated_at=excluded.updated_at
                """,
                (key, value, category, now, now),
            )

    def get_memory(self, key: str) -> Optional[str]:
        with self._lock, self._get_conn() as conn:
            cur = conn.execute("SELECT value FROM memories WHERE key = ?", (key,))
            row = cur.fetchone()
            return row["value"] if row else None

    def list_memories(self, category: Optional[str] = None) -> list[dict[str, Any]]:
        with self._lock, self._get_conn() as conn:
            if category:
                cur = conn.execute(
                    "SELECT key, value, category, updated_at FROM memories WHERE category = ? ORDER BY updated_at DESC",
                    (category,),
                )
            else:
                cur = conn.execute("SELECT key, value, category, updated_at FROM memories ORDER BY updated_at DESC")
            return [dict(row) for row in cur.fetchall()]

    def delete_memory(self, key: str) -> bool:
        with self._lock, self._get_conn() as conn:
            cur = conn.execute("DELETE FROM memories WHERE key = ?", (key,))
            return cur.rowcount > 0
