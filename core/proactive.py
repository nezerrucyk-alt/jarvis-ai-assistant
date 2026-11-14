# -*- coding: utf-8 -*-
"""Proactive briefing: weather, NBU rates, reminders and automations.

Network calls are isolated in ``fetch_weather`` / ``fetch_rates`` so the
formatting logic can be tested offline.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Iterable, Optional

logger = logging.getLogger("Jarvis.Proactive")

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
NBU_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange"
DEFAULT_CITY = "Київ"
DEFAULT_LAT = 50.4501
DEFAULT_LON = 30.5234

WEATHER_CODES: dict[int, str] = {
    0: "ясно",
    1: "переважно ясно",
    2: "мінлива хмарність",
    3: "похмуро",
    45: "туман",
    48: "крижаний туман",
    51: "легка мряка",
    53: "мряка",
    55: "сильна мряка",
    56: "крижана мряка",
    57: "сильна крижана мряка",
    61: "невеликий дощ",
    63: "дощ",
    65: "сильний дощ",
    66: "крижаний дощ",
    67: "сильний крижаний дощ",
    71: "невеликий сніг",
    73: "сніг",
    75: "сильний сніг",
    77: "снігові зерна",
    80: "короткочасна злива",
    81: "злива",
    82: "сильна злива",
    85: "снігопад",
    86: "сильний снігопад",
    95: "гроза",
    96: "гроза з градом",
    99: "сильна гроза з градом",
}

RATE_LABELS = {"USD": "USD", "EUR": "EUR", "PLN": "PLN"}


def _session(session):
    if session is not None:
        return session
    import requests  # noqa: PLC0415 — lazy, keeps import cost low

    return requests


def fetch_weather(
    latitude: float = DEFAULT_LAT,
    longitude: float = DEFAULT_LON,
    session=None,
    timeout: float = 8.0,
) -> Optional[dict[str, Any]]:
    """Returns parsed current weather or ``None`` when it is unavailable."""
    client = _session(session)
    try:
        response = client.get(
            WEATHER_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "auto",
                "forecast_days": 1,
            },
            timeout=timeout,
        )
        if getattr(response, "status_code", 200) != 200:
            return None
        return parse_weather(response.json())
    except Exception as exc:  # noqa: BLE001 — network must never kill a briefing
        logger.warning("Weather fetch failed: %s", exc)
        return None


def parse_weather(data: Any) -> Optional[dict[str, Any]]:
    if not isinstance(data, dict):
        return None
    current = data.get("current") or {}
    temperature = current.get("temperature_2m")
    if temperature is None:
        return None
    try:
        code = int(current.get("weather_code") or 0)
    except (TypeError, ValueError):
        code = 0
    daily = data.get("daily") or {}
    high = _first(daily.get("temperature_2m_max"))
    low = _first(daily.get("temperature_2m_min"))
    rain = _first(daily.get("precipitation_probability_max"))
    wind = current.get("wind_speed_10m")
    return {
        "temperature": round(float(temperature)),
        "code": code,
        "condition": WEATHER_CODES.get(code, "мінлива погода"),
        "wind": round(float(wind)) if isinstance(wind, (int, float)) else None,
        "high": round(float(high)) if isinstance(high, (int, float)) else None,
        "low": round(float(low)) if isinstance(low, (int, float)) else None,
        "rain": round(float(rain)) if isinstance(rain, (int, float)) else None,
    }


def fetch_rates(
    codes: Iterable[str] = ("USD", "EUR", "PLN"),
    session=None,
    timeout: float = 8.0,
) -> list[dict[str, Any]]:
    """Returns NBU rates for the requested currencies (empty list on failure)."""
    client = _session(session)
    try:
        response = client.get(NBU_URL, params={"json": ""}, timeout=timeout)
        if getattr(response, "status_code", 200) != 200:
            return []
        return parse_rates(response.json(), codes)
    except Exception as exc:  # noqa: BLE001
        logger.warning("NBU rates fetch failed: %s", exc)
        return []


def parse_rates(data: Any, codes: Iterable[str] = ("USD", "EUR", "PLN")) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        return []
    wanted_list = [str(code).upper() for code in codes]
    wanted = set(wanted_list)
    rates: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        code = str(item.get("cc") or "").upper()
        if code not in wanted:
            continue
        try:
            rate = float(item.get("rate"))
        except (TypeError, ValueError):
            continue
        rates.append({"code": code, "rate": rate, "name": str(item.get("txt") or code)})
    order = {code: index for index, code in enumerate(wanted_list)}
    rates.sort(key=lambda row: order.get(row["code"], 99))
    return rates


def _first(values: Any) -> Any:
    if isinstance(values, (list, tuple)) and values:
        return values[0]
    return None


def greeting_for(now: datetime) -> str:
    hour = now.hour
    if 5 <= hour < 11:
        return "Доброго ранку"
    if 11 <= hour < 17:
        return "Доброго дня"
    if 17 <= hour < 23:
        return "Доброго вечора"
    return "Доброї ночі"


def due_reminders(reminders: Iterable[dict[str, Any]], now: datetime) -> list[str]:
    texts: list[str] = []
    for item in reminders:
        if not isinstance(item, dict) or item.get("fired"):
            continue
        try:
            moment = datetime.fromisoformat(str(item.get("when") or ""))
        except ValueError:
            continue
        if moment.date() == now.date():
            text = str(item.get("text") or "").strip()
            if text:
                texts.append(text)
    return texts


def build_briefing(
    *,
    now: Optional[datetime] = None,
    city: str = DEFAULT_CITY,
    weather: Optional[dict[str, Any]] = None,
    rates: Optional[list[dict[str, Any]]] = None,
    reminders: Iterable[dict[str, Any]] = (),
    automations: Iterable[dict[str, Any]] = (),
    weather_failed: bool = False,
    rates_failed: bool = False,
) -> str:
    now = now or datetime.now()
    city = str(city or DEFAULT_CITY).strip() or DEFAULT_CITY
    lines = [
        f"{greeting_for(now)}, сер. Сьогодні {now.strftime('%d.%m.%Y')}.",
    ]

    if weather:
        line = f"За вікном у {city}: {weather['temperature']}°C, {weather['condition']}"
        if weather.get("high") is not None and weather.get("low") is not None:
            line += f"; вдень до {weather['high']}°C, вночі до {weather['low']}°C"
        if weather.get("wind") is not None:
            line += f", вітер {weather['wind']} км/год"
        if weather.get("rain") is not None:
            line += f", ймовірність опадів {weather['rain']}%"
        lines.append(line + ".")
    elif weather_failed:
        lines.append("Погоду отримати не вдалося — перевір з'єднання або координати.")

    if rates:
        chunks = [f"{row['code']} {row['rate']:.2f}" for row in rates]
        lines.append("Курс НБУ: " + " · ".join(chunks) + ".")
    elif rates_failed:
        lines.append("Курс НБУ зараз недоступний.")

    today = due_reminders(reminders, now)
    if today:
        shown = "; ".join(today[:5])
        extra = f" і ще {len(today) - 5}" if len(today) > 5 else ""
        lines.append(f"Нагадування на сьогодні: {shown}{extra}.")

    active = [
        item
        for item in automations
        if isinstance(item, dict) and item.get("enabled", True)
    ]
    if active:
        lines.append(f"Активних автоматизацій: {len(active)}.")

    lines.append("Система готова, сер.")
    return "\n".join(lines)


def collect_briefing(
    config: dict[str, Any],
    reminders: Iterable[dict[str, Any]] = (),
    automations: Iterable[dict[str, Any]] = (),
    now: Optional[datetime] = None,
    session=None,
) -> str:
    """Full briefing with live weather/rates; safe when offline."""
    now = now or datetime.now()
    city = str(config.get("briefing_city") or DEFAULT_CITY)
    try:
        latitude = float(config.get("briefing_lat") or DEFAULT_LAT)
        longitude = float(config.get("briefing_lon") or DEFAULT_LON)
    except (TypeError, ValueError):
        latitude, longitude = DEFAULT_LAT, DEFAULT_LON

    weather = fetch_weather(latitude, longitude, session=session)
    rates = fetch_rates(session=session)
    return build_briefing(
        now=now,
        city=city,
        weather=weather,
        rates=rates,
        reminders=reminders,
        automations=automations,
        weather_failed=weather is None,
        rates_failed=not rates,
    )


__all__ = [
    "DEFAULT_CITY",
    "DEFAULT_LAT",
    "DEFAULT_LON",
    "NBU_URL",
    "WEATHER_CODES",
    "WEATHER_URL",
    "build_briefing",
    "collect_briefing",
    "due_reminders",
    "fetch_rates",
    "fetch_weather",
    "greeting_for",
    "parse_rates",
    "parse_weather",
]
