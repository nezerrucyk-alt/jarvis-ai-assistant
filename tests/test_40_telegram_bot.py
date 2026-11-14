# -*- coding: utf-8 -*-
"""Telegram bot: parsing, allow-list and polling loop."""
from __future__ import annotations

import threading
import unittest

from core.telegram_bot import TelegramBot, TelegramError


class _Response:
    def __init__(self, payload) -> None:
        self._payload = payload
        self.status_code = 200

    def json(self):
        return self._payload


class _Session:
    def __init__(self, result=None) -> None:
        self.result = result if result is not None else {"message_id": 1}
        self.calls: list[dict] = []
        self.closed = False

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params or {}, "timeout": timeout})
        return _Response({"ok": True, "result": self.result})

    def close(self) -> None:
        self.closed = True


class TelegramTests(unittest.TestCase):
    def test_token_required(self) -> None:
        with self.assertRaises(TelegramError):
            TelegramBot("")

    def test_parse_updates(self) -> None:
        updates = [
            {
                "update_id": 10,
                "message": {
                    "message_id": 1,
                    "chat": {"id": 777},
                    "from": {"username": "owner"},
                    "text": "  привіт  ",
                },
            },
            {"update_id": 11, "message": {"chat": {"id": 777}, "text": ""}},
            {"update_id": 12},
        ]
        messages, last_id = TelegramBot.parse_updates(updates)
        self.assertEqual(last_id, 12)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["chat_id"], 777)
        self.assertEqual(messages[0]["text"], "привіт")
        self.assertEqual(messages[0]["username"], "owner")

    def test_is_allowed(self) -> None:
        bot = TelegramBot("token", chat_id="777", session=_Session())
        self.assertTrue(bot.is_allowed(777))
        self.assertFalse(bot.is_allowed(888))
        self.assertFalse(TelegramBot("token", chat_id="", session=_Session()).is_allowed(1))

    def test_send_message_uses_configured_chat(self) -> None:
        session = _Session()
        bot = TelegramBot("secret-token", chat_id="777", session=session)
        bot.send_message("x" * 5000)
        call = session.calls[0]
        self.assertIn("secret-token", call["url"])
        self.assertTrue(call["url"].endswith("/sendMessage"))
        self.assertEqual(call["params"]["chat_id"], "777")
        self.assertEqual(len(call["params"]["text"]), 3900)

    def test_send_without_chat_raises(self) -> None:
        bot = TelegramBot("token", chat_id="", session=_Session())
        with self.assertRaises(TelegramError):
            bot.send_message("hello")

    def test_run_forever_handles_allowed_chat_and_stops(self) -> None:
        session = _Session()
        handled: list[str] = []
        bot = TelegramBot(
            "token",
            chat_id="777",
            handler=lambda _bot, message: handled.append(message["text"]),
            session=session,
        )
        stop = threading.Event()
        calls = {"count": 0}

        def poll_once(offset=None):
            calls["count"] += 1
            if calls["count"] == 1:
                return (
                    [
                        {
                            "chat_id": 777,
                            "text": "привіт",
                            "username": "owner",
                        },
                        {"chat_id": 999, "text": "чужий"},
                    ],
                    20,
                )
            stop.set()
            return [], None

        bot.poll_once = poll_once  # type: ignore[assignment]
        bot.run_forever(stop)
        self.assertEqual(handled, ["привіт"])
        self.assertTrue(any("999" in str(call["params"].get("chat_id")) for call in session.calls))

    def test_reject_disallowed_chat(self) -> None:
        session = _Session()
        bot = TelegramBot("token", chat_id="777", session=session)
        bot._reject(999)
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(session.calls[0]["params"]["chat_id"], "999")


if __name__ == "__main__":
    unittest.main()
