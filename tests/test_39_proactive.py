# -*- coding: utf-8 -*-
"""Proactive briefing: parsers, reminders and offline-safe formatting."""
from __future__ import annotations

import unittest
from datetime import datetime

from core.proactive import (
    NBU_URL,
    WEATHER_URL,
    build_briefing,
    collect_briefing,
    due_reminders,
    greeting_for,
    parse_rates,
    parse_weather,
)

WEATHER_SAMPLE = {
    "current": {"temperature_2m": -1.4, "weather_code": 1, "wind_speed_10m": 12.6},
    "daily": {
        "temperature_2m_max": [2.2],
        "temperature_2m_min": [-4.1],
        "precipitation_probability_max": [15],
    },
}

RATES_SAMPLE = [
    {"cc": "USD", "rate": 41.234, "txt": "Долар США"},
    {"cc": "EUR", "rate": 44.812, "txt": "Євро"},
    {"cc": "PLN", "rate": 10.215, "txt": "Польський злотий"},
    {"cc": "GBP", "rate": 52.0, "txt": "Фунт"},
]


class _Response:
    def __init__(self, payload, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class _Session:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(url)
        if url == WEATHER_URL:
            return _Response(WEATHER_SAMPLE)
        if url == NBU_URL:
            return _Response(RATES_SAMPLE)
        return _Response({}, 404)


class ProactiveTests(unittest.TestCase):
    def test_parse_weather(self) -> None:
        parsed = parse_weather(WEATHER_SAMPLE)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["temperature"], -1)
        self.assertEqual(parsed["condition"], "переважно ясно")
        self.assertEqual(parsed["high"], 2)
        self.assertEqual(parsed["low"], -4)
        self.assertEqual(parsed["rain"], 15)

    def test_parse_weather_missing_current(self) -> None:
        self.assertIsNone(parse_weather({}))
        self.assertIsNone(parse_weather([]))

    def test_parse_rates_order_and_filter(self) -> None:
        parsed = parse_rates(RATES_SAMPLE)
        self.assertEqual([row["code"] for row in parsed], ["USD", "EUR", "PLN"])
        self.assertAlmostEqual(parsed[0]["rate"], 41.234)

    def test_greeting_boundaries(self) -> None:
        self.assertEqual(greeting_for(datetime(2026, 1, 1, 6)), "Доброго ранку")
        self.assertEqual(greeting_for(datetime(2026, 1, 1, 12)), "Доброго дня")
        self.assertEqual(greeting_for(datetime(2026, 1, 1, 19)), "Доброго вечора")
        self.assertEqual(greeting_for(datetime(2026, 1, 1, 2)), "Доброї ночі")

    def test_due_reminders_today_only(self) -> None:
        now = datetime(2026, 11, 14, 8, 0)
        reminders = [
            {"text": "подзвонити", "when": "2026-11-14T10:00", "fired": False},
            {"text": "вже було", "when": "2026-11-14T07:00", "fired": True},
            {"text": "завтра", "when": "2026-11-15T09:00", "fired": False},
            {"text": "зламане", "when": "not-a-date", "fired": False},
        ]
        self.assertEqual(due_reminders(reminders, now), ["подзвонити"])

    def test_build_briefing_full(self) -> None:
        text = build_briefing(
            now=datetime(2026, 11, 14, 8, 0),
            city="Київ",
            weather=parse_weather(WEATHER_SAMPLE),
            rates=parse_rates(RATES_SAMPLE),
            reminders=[
                {"text": "подзвонити", "when": "2026-11-14T10:00", "fired": False}
            ],
            automations=[{"enabled": True}, {"enabled": False}],
        )
        self.assertIn("Доброго ранку", text)
        self.assertIn("14.11.2026", text)
        self.assertIn("Київ", text)
        self.assertIn("Курс НБУ: USD 41.23 · EUR 44.81 · PLN 10.21", text)
        self.assertIn("подзвонити", text)
        self.assertIn("Активних автоматизацій: 1", text)

    def test_build_briefing_reports_failures(self) -> None:
        text = build_briefing(
            now=datetime(2026, 11, 14, 12, 0),
            weather=None,
            rates=[],
            weather_failed=True,
            rates_failed=True,
        )
        self.assertIn("Погоду отримати не вдалося", text)
        self.assertIn("Курс НБУ зараз недоступний", text)

    def test_collect_briefing_with_fake_session(self) -> None:
        session = _Session()
        text = collect_briefing(
            {"briefing_city": "Київ", "briefing_lat": 50.45, "briefing_lon": 30.52},
            now=datetime(2026, 11, 14, 8, 0),
            session=session,
        )
        self.assertEqual(session.calls, [WEATHER_URL, NBU_URL])
        self.assertIn("переважно ясно", text)
        self.assertIn("USD 41.23", text)


if __name__ == "__main__":
    unittest.main()
