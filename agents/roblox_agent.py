# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — Roblox Agent.
Specializes in Roblox Studio workflows, Luau game mechanics, and Private Server administration.
"""

from __future__ import annotations
import os
import webbrowser
from typing import Any, Optional
from urllib.parse import urlparse
from agents.base_agent import BaseAgent, AgentResponse
from core.security_engine import SecurityLevel
from core.task_engine import Task


class RobloxAgent(BaseAgent):
    def __init__(self, security_engine, model_router, config: dict):
        super().__init__(
            name="Roblox",
            role="Game Mechanics & Studio Specialist",
            description="Створює Luau-скрипти для Roblox Studio, керує приватними серверами та механіками.",
            security_engine=security_engine,
            model_router=model_router,
        )
        self.config = config

    def reset_private_server(self, custom_url: str = "") -> tuple[bool, str]:
        url = (custom_url or self.config.get("roblox_private_server") or "").strip()
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url

        parsed = urlparse(url)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname not in {"roblox.com", "www.roblox.com"}
            or not parsed.path.startswith("/private-server/configure/")
        ):
            return (
                False,
                "Вкажіть посилання на сторінку конфігурації приватного сервера у форматі:\n"
                "https://www.roblox.com/private-server/configure/<id>",
            )

        if not self.authorize_action(
            "Відкрити сторінку приватного сервера Roblox",
            f"Посилання: {url}\n\nНа сторінці натисніть «Shutdown All Servers».",
            SecurityLevel.APPROVAL,
        ):
            return (False, "Дію скасовано користувачем.")

        try:
            webbrowser.open(url)
            return (True, f"Сторінку приватного сервера відкрито: {url}")
        except Exception as exc:
            return (False, f"Не вдалося відкрити браузер: {exc}")

    def execute(self, task: Task, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        title = task.title.lower()
        if "ресет" in title or "сервер" in title or "restart" in title:
            success, msg = self.reset_private_server((context or {}).get("url", ""))
            return AgentResponse(success=success, output=msg, error=None if success else msg)

        messages = [
            {
                "role": "system",
                "content": (
                    "Ти — Roblox Agent. Пиши надійний, оптимізований Luau-код "
                    "для Roblox Studio з суворою типізацією (--!strict), "
                    "роботою через Services (Players, ReplicatedStorage, TweenService) та безпечними RemoteEvent."
                ),
            },
            {"role": "user", "content": f"{task.title}\n{task.description}"},
        ]
        try:
            resp = self.router.complete(messages, task_type="coding", max_tokens=2000)
            return AgentResponse(success=True, output=resp["content"])
        except Exception as exc:
            return AgentResponse(success=False, output="", error=str(exc))
