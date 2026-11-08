# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — Coder Agent.
Generates code, debugs errors, refactors existing scripts, and explains complex architectures.
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import Any, Optional
from agents.base_agent import BaseAgent, AgentResponse
from core.security_engine import SecurityLevel
from core.task_engine import Task


class CoderAgent(BaseAgent):
    SYSTEM_PROMPT = """Ти — Coder Agent у системі JARVIS ULTIMATE.
Твоя спеціалізація:
- Написання надійного, чистого та типізованого коду (Python, Luau для Roblox, TypeScript, PowerShell).
- Пошук помилок та оптимізація.
- Дотримання модульності та архітектурних патернів.
- Завжди оформлюй код у блоках з вказівкою мови, наприклад ```python ... ``` або ```lua ... ```.
- Коментуй лише важливі та неочевидні ділянки.
"""

    def __init__(self, security_engine, model_router):
        super().__init__(
            name="Coder",
            role="Software Engineer & Architect",
            description="Генерує код, шукає та виправляє баги, створює структури проєктів.",
            security_engine=security_engine,
            model_router=model_router,
        )

    def execute(self, task: Task, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        self.logger.info("Executing coding task: %s", task.title)
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Завдання: {task.title}\nДеталі: {task.description}"},
        ]

        try:
            resp = self.router.complete(messages, task_type="coding", max_tokens=2200)
            code_text = resp["content"]

            artifacts = []
            target_file = (context or {}).get("target_file")
            if target_file and "```" in code_text:
                blocks = re.findall(r"```(?:\w+)?\n(.*?)```", code_text, flags=re.DOTALL)
                if blocks:
                    primary_code = blocks[0].strip()
                    path = Path(target_file)
                    level = SecurityLevel.APPROVAL if path.exists() else SecurityLevel.CONTROLLED
                    if self.authorize_action(
                        f"Запис коду у {path.name}", f"Шлях: {path}\nРозмір: {len(primary_code)} байт", level
                    ):
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(primary_code, encoding="utf-8")
                        artifacts.append(str(path))
                        self.logger.info("Saved code artifact: %s", path)

            return AgentResponse(
                success=True,
                output=code_text,
                artifacts=artifacts,
                metadata={"model_used": resp.get("model")},
            )
        except Exception as exc:
            self.logger.exception("CoderAgent failed: %s", exc)
            return AgentResponse(success=False, output="", error=str(exc))
