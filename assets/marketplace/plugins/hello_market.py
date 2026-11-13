# -*- coding: utf-8 -*-
"""Marketplace example: a friendly greeting tool."""
from __future__ import annotations

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "hello_market",
            "description": "Привітатися з користувачем і показати, що плагін працює.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Ім'я користувача (необов'язково).",
                    }
                },
            },
        },
    }
]


def run(name: str, args: dict, ctx) -> str:
    if name != "hello_market":
        return f"Невідомий інструмент плагіна: {name}"
    who = str((args or {}).get("name") or "сер").strip()[:40] or "сер"
    ctx.log("hello_market: привітання")
    return f"Привіт, {who}! Це приклад із локального marketplace JARVIS."
