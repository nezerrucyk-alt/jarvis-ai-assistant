# -*- coding: utf-8 -*-
"""Tests for scheduled automations (pure scheduling logic)."""
from __future__ import annotations

import unittest
from datetime import datetime

from core.automations import (
    AutomationError,
    advance_automation,
    build_automation,
    describe_automation,
    due_automations,
    format_schedule,
    next_run,
    parse_schedule,
)


class ScheduleParsingTests(unittest.TestCase):
    def test_daily(self) -> None:
        self.assertEqual(
            parse_schedule("daily 09:30"),
            {"schedule": "daily", "time": "09:30"},
        )

    def test_weekly_with_ukrainian_day(self) -> None:
        parsed = parse_schedule("weekly пн 08:15")
        self.assertEqual(parsed["schedule"], "weekly")
        self.assertEqual(parsed["weekday"], 0)
        self.assertEqual(parsed["time"], "08:15")

    def test_interval_minutes_and_hours(self) -> None:
        self.assertEqual(
            parse_schedule("every 30m")["interval_minutes"], 30
        )
        self.assertEqual(
            parse_schedule("interval 2h")["interval_minutes"], 120
        )

    def test_once(self) -> None:
        parsed = parse_schedule("once 2030-01-02T03:04")
        self.assertEqual(parsed["schedule"], "once")
        self.assertEqual(parsed["when"], "2030-01-02T03:04")

    def test_invalid_schedules(self) -> None:
        for value in (
            "",
            "daily 25:00",
            "weekly someday 09:00",
            "every 1m",
            "sometimes",
            "once tomorrow",
        ):
            with self.subTest(value=value):
                with self.assertRaises(AutomationError):
                    parse_schedule(value)


class NextRunTests(unittest.TestCase):
    def test_daily_rolls_to_tomorrow(self) -> None:
        now = datetime(2026, 5, 1, 10, 0)
        record = {"schedule": "daily", "time": "09:00"}
        self.assertEqual(next_run(record, now), datetime(2026, 5, 2, 9, 0))

    def test_daily_keeps_today_if_future(self) -> None:
        now = datetime(2026, 5, 1, 8, 0)
        record = {"schedule": "daily", "time": "09:00"}
        self.assertEqual(next_run(record, now), datetime(2026, 5, 1, 9, 0))

    def test_weekly_rolls_to_next_week(self) -> None:
        now = datetime(2026, 5, 1, 10, 0)  # Friday
        record = {"schedule": "weekly", "weekday": 0, "time": "09:00"}
        self.assertEqual(next_run(record, now), datetime(2026, 5, 4, 9, 0))

    def test_interval_skips_missed_slots(self) -> None:
        now = datetime(2026, 5, 1, 12, 0)
        record = {
            "schedule": "interval",
            "interval_minutes": 30,
            "last_run": "2026-05-01T10:00",
        }
        self.assertEqual(next_run(record, now), datetime(2026, 5, 1, 12, 30))

    def test_once_in_the_past_is_none(self) -> None:
        now = datetime(2026, 5, 1, 12, 0)
        record = {"schedule": "once", "when": "2026-05-01T11:00"}
        self.assertIsNone(next_run(record, now))


class AutomationLifecycleTests(unittest.TestCase):
    def test_build_daily(self) -> None:
        created = datetime(2026, 5, 1, 8, 0)
        record = build_automation(
            "  Перевірити пошту  ", "daily 09:00", created_at=created
        )
        self.assertEqual(record["text"], "Перевірити пошту")
        self.assertEqual(record["action"], "prompt")
        self.assertEqual(record["next_run"], "2026-05-01T09:00")
        self.assertTrue(record["enabled"])

    def test_build_rejects_past_once(self) -> None:
        with self.assertRaises(AutomationError):
            build_automation(
                "старе",
                "once 2020-01-01T00:00",
                created_at=datetime(2026, 5, 1, 8, 0),
            )

    def test_build_rejects_empty_text_and_action(self) -> None:
        with self.assertRaises(AutomationError):
            build_automation("  ", "daily 09:00")
        with self.assertRaises(AutomationError):
            build_automation("текст", "daily 09:00", action="shell")

    def test_advance_daily_keeps_enabled(self) -> None:
        now = datetime(2026, 5, 1, 9, 0)
        record = {
            "schedule": "daily",
            "time": "09:00",
            "enabled": True,
            "next_run": "2026-05-01T09:00",
        }
        advance_automation(record, now)
        self.assertTrue(record["enabled"])
        self.assertEqual(record["next_run"], "2026-05-02T09:00")
        self.assertEqual(record["last_run"], "2026-05-01T09:00:00")

    def test_advance_once_disables(self) -> None:
        now = datetime(2026, 5, 1, 9, 0)
        record = {
            "schedule": "once",
            "when": "2026-05-01T09:00",
            "enabled": True,
            "next_run": "2026-05-01T09:00",
        }
        advance_automation(record, now)
        self.assertFalse(record["enabled"])
        self.assertIsNone(record["next_run"])

    def test_due_automations_only_returns_due_enabled(self) -> None:
        now = datetime(2026, 5, 1, 10, 0)
        records = [
            {"id": "a", "enabled": True, "next_run": "2026-05-01T09:00"},
            {"id": "b", "enabled": True, "next_run": "2026-05-01T11:00"},
            {"id": "c", "enabled": False, "next_run": "2026-05-01T09:00"},
        ]
        self.assertEqual([item["id"] for item in due_automations(records, now)], ["a"])

    def test_format_and_describe(self) -> None:
        daily = {"schedule": "daily", "time": "09:00", "text": "пошта"}
        self.assertIn("Щодня", format_schedule(daily))
        self.assertIn("надіслати запит", describe_automation(daily))
        notify = {"schedule": "weekly", "weekday": 2, "time": "18:00", "text": "вода", "action": "notify"}
        self.assertIn("Ср", format_schedule(notify))
        self.assertIn("нагадати", describe_automation(notify))


if __name__ == "__main__":
    unittest.main()
