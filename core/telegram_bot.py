# -*- coding: utf-8 -*-
"""Minimal Telegram long-polling bot (no extra dependencies).

Only one chat is allowed: the id from the settings. Everything else is
rejected with a hint, so a leaked bot token cannot be used to chat with the
assistant from another account.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

logger = logging.getLogger("Jarvis.Telegram")

API_ROOT = "https://api.telegram.org/bot{token}/{method}"
MAX_MESSAGE = 3900


class TelegramError(RuntimeError):
    """Telegram API or configuration error."""


class TelegramBot:
    def __init__(
        self,
        token: str,
        chat_id: str | int = "",
        handler: Optional[Callable[["TelegramBot", dict[str, Any]], None]] = None,
        session=None,
        timeout: int = 30,
    ) -> None:
        token = str(token or "").strip()
        if not token:
            raise TelegramError("Не вказано токен Telegram-бота.")
        self.token = token
        self.chat_id = str(chat_id or "").strip()
        self.handler = handler
        self.timeout = max(5, min(int(timeout), 55))
        if session is None:
            import requests  # noqa: PLC0415 — lazy import for tests

            session = requests.Session()
        self.session = session

    def _url(self, method: str) -> str:
        return API_ROOT.format(token=self.token, method=method)

    def _request(self, method: str, params: Optional[dict[str, Any]] = None, timeout: Optional[float] = None) -> Any:
        response = self.session.get(
            self._url(method),
            params=params or {},
            timeout=timeout or self.timeout + 10,
        )
        try:
            data = response.json()
        except Exception as exc:  # noqa: BLE001
            raise TelegramError(f"Некоректна відповідь Telegram: {exc}") from exc
        if not isinstance(data, dict) or not data.get("ok"):
            description = (data or {}).get("description") if isinstance(data, dict) else ""
            raise TelegramError(str(description or "Telegram API error"))
        return data.get("result")

    def get_me(self) -> dict[str, Any]:
        result = self._request("getMe", timeout=15)
        return result if isinstance(result, dict) else {}

    def send_message(self, text: str, chat_id: str | int = "") -> str:
        chat = str(chat_id or self.chat_id).strip()
        if not chat:
            raise TelegramError("Не вказано chat_id.")
        body = str(text or "").strip()
        if not body:
            return ""
        result = self._request(
            "sendMessage",
            {
                "chat_id": chat,
                "text": body[:MAX_MESSAGE],
                "disable_web_page_preview": True,
            },
        )
        if isinstance(result, dict):
            return str(result.get("message_id") or "")
        return ""

    def is_allowed(self, chat_id: str | int) -> bool:
        return bool(self.chat_id) and str(chat_id).strip() == self.chat_id

    @staticmethod
    def parse_updates(updates: Any) -> tuple[list[dict[str, Any]], Optional[int]]:
        if not isinstance(updates, list):
            return [], None
        messages: list[dict[str, Any]] = []
        last_id: Optional[int] = None
        for update in updates:
            if not isinstance(update, dict):
                continue
            raw_id = update.get("update_id")
            if isinstance(raw_id, int):
                last_id = raw_id if last_id is None else max(last_id, raw_id)
            message = update.get("message") or update.get("edited_message") or {}
            if not isinstance(message, dict):
                continue
            chat = message.get("chat") or {}
            chat_id = chat.get("id")
            text = message.get("text") or message.get("caption") or ""
            if chat_id is None or not str(text).strip():
                continue
            sender = message.get("from") or {}
            messages.append(
                {
                    "update_id": raw_id,
                    "chat_id": chat_id,
                    "text": str(text).strip(),
                    "username": str(sender.get("username") or sender.get("first_name") or ""),
                    "message_id": message.get("message_id"),
                }
            )
        return messages, last_id

    def poll_once(self, offset: Optional[int] = None) -> tuple[list[dict[str, Any]], Optional[int]]:
        params: dict[str, Any] = {
            "timeout": self.timeout,
            "allowed_updates": '["message"]',
        }
        if offset is not None:
            params["offset"] = offset
        result = self._request("getUpdates", params, timeout=self.timeout + 10)
        return self.parse_updates(result)

    def run_forever(self, stop_event: threading.Event) -> None:
        offset: Optional[int] = None
        while not stop_event.is_set():
            try:
                messages, last_id = self.poll_once(offset)
                if last_id is not None:
                    offset = last_id + 1
                for message in messages:
                    if not self.is_allowed(message["chat_id"]):
                        self._reject(message["chat_id"])
                        continue
                    if self.handler is None:
                        continue
                    try:
                        self.handler(self, message)
                    except Exception:  # noqa: BLE001 — one bad message must not stop the bot
                        logger.exception("Telegram handler failed")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Telegram polling failed: %s", exc)
                stop_event.wait(3.0)

    def _reject(self, chat_id: str | int) -> None:
        try:
            self.send_message(
                "Цей чат не дозволений. Додай свій chat id у Налаштуваннях Jarvis "
                f"(твій id: {chat_id}).",
                chat_id=chat_id,
            )
        except Exception:  # noqa: BLE001
            logger.debug("Telegram reject message failed", exc_info=True)

    def close(self) -> None:
        try:
            self.session.close()
        except Exception:  # noqa: BLE001
            pass


__all__ = ["API_ROOT", "MAX_MESSAGE", "TelegramBot", "TelegramError"]
