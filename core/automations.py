# -*- coding: utf-8 -*-
"""Scheduled automations for JARVIS.

An automation is a small local record with a prompt or a notification and a
schedule.  The scheduler itself lives in ``jarvis.py`` and calls
:func:`due_automations` / :func:`advance_automation`; this module stays pure so
it can be tested without Tk, network or a running application.

Supported schedules::

    once 2026-12-31T23:59
    daily 09:00
    weekly mon 09:00
    every 30m
    interval 2h

Actions: ``prompt`` (send text to the assistant), ``notify`` (desktop
notification + voice) and ``briefing`` (proactive summary with weather,
NBU rates and today's reminders).  Dangerous shell commands are intentionally
not an action: automations must not gain the ability to run arbitrary code
while the user is away.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Iterable, Optional

MAX_AUTOMATIONS = 100
MAX_TEXT = 500
MIN_INTERVAL_MINUTES = 5
MAX_INTERVAL_MINUTES = 7 * 24 * 60
ACTIONS = ("prompt", "notify", "briefing")
SCHEDULES = ("once", "daily", "weekly", "interval")

_WEEKDAYS = {
    "mon": 0, "monday": 0, "пн": 0, "понеділок": 0, "понедельник": 0,
    "tue": 1, "tuesday": 1, "вт": 1, "вівторок": 1, "вторник": 1,
    "wed": 2, "wednesday": 2, "ср": 2, "середа": 2, "среда": 2,
    "thu": 3, "thursday": 3, "чт": 3, "четвер": 3,
    "fri": 4, "friday": 4, "пт": 4, "пʼятниця": 4, "п'ятниця": 4, "пятница": 4,
    "sat": 5, "saturday": 5, "сб": 5, "субота": 5, "суббота": 5,
    "sun": 6, "sunday": 6, "нд": 6, "неділя": 6, "воскресенье": 6,
}
_WEEKDAY_LABELS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд")
_TIME_RE = re.compile(r"^([01]?\d|2[0-3])[:.]([0-5]\d)$")
_INTERVAL_RE = re.compile(r"^(\d{1,5})\s*(m|min|хв|h|год|г)?$", re.IGNORECASE)


class AutomationError(ValueError):
    """Invalid automation definition."""


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_time(value: str) -> tuple[int, int]:
    match = _TIME_RE.match(_clean(value))
    if not match:
        raise AutomationError("Час має бути у форматі HH:MM, наприклад 09:30.")
    return int(match.group(1)), int(match.group(2))


def parse_weekday(value: str) -> int:
    key = _clean(value).lower().replace("’", "ʼ")
    if key in _WEEKDAYS:
        return _WEEKDAYS[key]
    raise AutomationError(
        "День тижня не розпізнано. Використай mon/tue/wed/thu/fri/sat/sun "
        "або пн/вт/ср/чт/пт/сб/нд."
    )


def parse_schedule(value: str) -> dict[str, Any]:
    """Parse a human-readable schedule into normalized fields."""
    raw = _clean(value)
    lowered = raw.lower()
    if not raw:
        raise AutomationError("Вкажи розклад: once, daily, weekly або every.")
    if lowered.startswith("once"):
        when_text = raw[4:].strip()
        try:
            when = datetime.fromisoformat(when_text)
        except ValueError as exc:
            raise AutomationError(
                "Для once потрібен час у форматі YYYY-MM-DDTHH:MM."
            ) from exc
        return {"schedule": "once", "when": when.isoformat(timespec="minutes")}
    if lowered.startswith("daily"):
        hour, minute = parse_time(raw[5:].strip())
        return {
            "schedule": "daily",
            "time": f"{hour:02d}:{minute:02d}",
        }
    if lowered.startswith("weekly"):
        parts = raw[6:].strip().split()
        if len(parts) != 2:
            raise AutomationError(
                "Для weekly вкажи день і час: weekly mon 09:00."
            )
        weekday = parse_weekday(parts[0])
        hour, minute = parse_time(parts[1])
        return {
            "schedule": "weekly",
            "weekday": weekday,
            "time": f"{hour:02d}:{minute:02d}",
        }
    if lowered.startswith(("every", "interval")):
        text = raw.split(maxsplit=1)[1] if " " in raw else ""
        match = _INTERVAL_RE.match(text.strip())
        if not match:
            raise AutomationError("Інтервал має бути у форматі every 30m або every 2h.")
        amount = int(match.group(1))
        unit = (match.group(2) or "m").lower()
        minutes = amount * 60 if unit in {"h", "год", "г"} else amount
        if minutes < MIN_INTERVAL_MINUTES:
            raise AutomationError(
                f"Мінімальний інтервал — {MIN_INTERVAL_MINUTES} хвилин."
            )
        if minutes > MAX_INTERVAL_MINUTES:
            raise AutomationError("Максимальний інтервал — 7 днів.")
        return {"schedule": "interval", "interval_minutes": minutes}
    raise AutomationError(
        "Невідомий розклад. Приклади: once 2026-12-31T23:59, "
        "daily 09:00, weekly mon 09:00, every 30m."
    )


def format_schedule(record: dict[str, Any]) -> str:
    kind = str(record.get("schedule") or "")
    if kind == "once":
        return f"Одноразово · {str(record.get('when', '')).replace('T', ' ')}"
    if kind == "daily":
        return f"Щодня · {record.get('time', '?')}"
    if kind == "weekly":
        weekday = int(record.get("weekday", 0)) % 7
        return f"Щотижня · {_WEEKDAY_LABELS[weekday]} {record.get('time', '?')}"
    if kind == "interval":
        minutes = int(record.get("interval_minutes", 0))
        if minutes % 60 == 0 and minutes >= 60:
            return f"Кожні {minutes // 60} год"
        return f"Кожні {minutes} хв"
    return kind or "?"


def next_run(record: dict[str, Any], now: Optional[datetime] = None) -> Optional[datetime]:
    """Return the next due time, or ``None`` for an expired one-off task."""
    now = now or datetime.now()
    kind = str(record.get("schedule") or "")
    if kind == "once":
        try:
            due = datetime.fromisoformat(str(record.get("when") or ""))
        except ValueError:
            return None
        return due if due > now else None
    if kind == "daily":
        try:
            hour, minute = parse_time(str(record.get("time") or ""))
        except AutomationError:
            return None
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate
    if kind == "weekly":
        try:
            hour, minute = parse_time(str(record.get("time") or ""))
            weekday = int(record.get("weekday", 0)) % 7
        except (AutomationError, TypeError, ValueError):
            return None
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        days_ahead = (weekday - now.weekday()) % 7
        candidate += timedelta(days=days_ahead)
        if candidate <= now:
            candidate += timedelta(days=7)
        return candidate
    if kind == "interval":
        minutes = int(record.get("interval_minutes", 0) or 0)
        if minutes <= 0:
            return None
        base_text = record.get("last_run") or record.get("created_at")
        try:
            base = datetime.fromisoformat(str(base_text)) if base_text else now
        except ValueError:
            base = now
        candidate = base + timedelta(minutes=minutes)
        while candidate <= now:
            candidate += timedelta(minutes=minutes)
        return candidate
    return None


def build_automation(
    text: str,
    schedule: str,
    *,
    action: str = "prompt",
    automation_id: str = "",
    created_at: Optional[datetime] = None,
) -> dict[str, Any]:
    """Validate input and return a ready-to-save automation record."""
    text = _clean(text)[:MAX_TEXT]
    if not text:
        raise AutomationError("Текст автоматизації порожній.")
    action = _clean(action).lower() or "prompt"
    if action not in ACTIONS:
        raise AutomationError("Дія має бути prompt, notify або briefing.")
    fields = parse_schedule(schedule)
    created = created_at or datetime.now()
    record: dict[str, Any] = {
        "id": automation_id or "",
        "text": text,
        "action": action,
        "enabled": True,
        "last_run": None,
        "created_at": created.isoformat(timespec="seconds"),
        **fields,
    }
    due = next_run(record, created)
    if due is None:
        raise AutomationError("Час автоматизації вже минув.")
    record["next_run"] = due.isoformat(timespec="minutes")
    return record


def due_automations(
    records: Iterable[dict[str, Any]],
    now: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """Return enabled automations whose ``next_run`` is due."""
    now = now or datetime.now()
    due: list[dict[str, Any]] = []
    for record in records:
        if not record.get("enabled", True):
            continue
        raw = record.get("next_run")
        if not raw:
            computed = next_run(record, now)
            if computed is None:
                continue
            raw = computed.isoformat(timespec="minutes")
            record["next_run"] = raw
        try:
            moment = datetime.fromisoformat(str(raw))
        except ValueError:
            continue
        if moment <= now:
            due.append(record)
    return due


def advance_automation(
    record: dict[str, Any],
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Mark a fired automation and compute its next occurrence."""
    now = now or datetime.now()
    record["last_run"] = now.isoformat(timespec="seconds")
    if record.get("schedule") == "once":
        record["enabled"] = False
        record["next_run"] = None
        return record
    upcoming = next_run(record, now)
    record["next_run"] = (
        upcoming.isoformat(timespec="minutes") if upcoming is not None else None
    )
    if upcoming is None:
        record["enabled"] = False
    return record


def describe_automation(record: dict[str, Any]) -> str:
    action = {
        "prompt": "надіслати запит",
        "notify": "нагадати",
        "briefing": "брифінг",
    }.get(str(record.get("action") or "prompt"), "надіслати запит")
    status = "" if record.get("enabled", True) else " · вимкнено"
    return (
        f"[{record.get('id', '?')}] {format_schedule(record)} · {action}: "
        f"{record.get('text', '')}{status}"
    )


__all__ = [
    "ACTIONS",
    "AutomationError",
    "MAX_AUTOMATIONS",
    "SCHEDULES",
    "advance_automation",
    "build_automation",
    "describe_automation",
    "due_automations",
    "format_schedule",
    "next_run",
    "parse_schedule",
    "parse_time",
    "parse_weekday",
]
