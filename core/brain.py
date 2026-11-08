# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — центральний мозок та оркестратор.

Керує багатоагентним плануванням, маршрутизацією моделей, пам'яттю та
виконанням задач. Окрім розмовного конвеєра, швидко обробляє прості дії на ПК
(«відкрий youtube», «статус системи») через :class:`PcController`, не
витрачаючи запит до LLM.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from core.agent_manager import AgentManager
from core.model_router import ModelRouter
from core.security_engine import SecurityEngine, SecurityLevel
from core.task_engine import TaskEngine
from memory.sqlite_store import SqliteStore

logger = logging.getLogger("Jarvis.Brain")


class Brain:
    """Оркестратор: швидкі дії на ПК, агенти та розмовна модель."""

    SYSTEM_INSTRUCTIONS = """Ти — J.A.R.V.I.S. (Just A Rather Very Intelligent System) ULTIMATE.
Центральний інтелект і координатор автономної багатоагентної системи.

Твої принципи:
1. Ти керуєш командою агентів: Coder (програмування), System (керування ОС і діагностика), Roblox (Roblox Studio та сервери).
2. Спілкуйся спокійно, впевнено, з легкою інтелігентною манерою, як Джарвіс.
3. Якщо користувач просить написати код, створити проєкт чи перевірити систему — формулюй чітке завдання та залучай потрібного спеціалізованого агента.
4. Для швидких питань відповідай прямо й змістовно.
"""

    ROBLOX_RESET_PATTERNS = re.compile(
        r"(?i)(?:/reset\s*server|/resetserver|ресетни сервер|перезапусти сервер|рестарт сервера|скинь сервер)"
    )

    #: «відкрий youtube», «запусти блокнот», «open vscode» …
    QUICK_OPEN_PATTERNS = re.compile(
        r"(?i)^\s*(?:відкрий|відкрити|відкривай|запусти|запустити|open|launch|start)\s+(.+)$"
    )

    #: «статус пк», «системна інформація», «скільки ram», «system info» …
    SYSTEM_INFO_PATTERNS = re.compile(
        r"(?i)(?:^|\b)(?:"
        r"статус\s+(?:пк|системи|комп['’]?ютера)|"
        r"системна\s+інформація|"
        r"інформація\s+про\s+(?:пк|систему|комп['’]?ютер)|"
        r"характеристики\s+(?:пк|комп['’]?ютера|системи)|"
        r"скільки\s+(?:ram|озу|пам['’]?яті|вільної\s+пам['’]?яті)|"
        r"навантаження\s+(?:пк|системи)|"
        r"system\s*(?:info|information|status)|"
        r"pc\s*(?:info|status)|"
        r"systeminfo"
        r")\b"
    )

    def __init__(
        self,
        config: dict,
        security_engine: SecurityEngine,
        model_router: ModelRouter,
        agent_manager: AgentManager,
        task_engine: TaskEngine,
        store: SqliteStore,
        pc_controller: Optional[Any] = None,
    ):
        self.config = config
        self.security = security_engine
        self.router = model_router
        self.agents = agent_manager
        self.tasks = task_engine
        self.store = store
        self.pc = pc_controller

    # ── обробка запиту ───────────────────────────────────────────────────────
    def process(self, text: str, session_id: str = "default") -> str:
        """Обробляє введення користувача: швидкі дії або багатоагентний конвеєр."""
        text = (text or "").strip()
        if not text:
            return "Слухаю вас, сер."

        if self.security.is_stopped:
            return (
                "Сер, зараз активована екстрена зупинка — усі дії заблоковано. "
                "Натисніть «EMERGENCY STOP» ще раз, щоб розблокувати систему."
            )

        self.store.add_message(session_id, "user", text, agent_name="user")

        # 1. Швидкі дії на ПК без запиту до LLM
        quick_reply = self._try_quick_action(text)
        if quick_reply is not None:
            self.store.add_message(session_id, "assistant", quick_reply, agent_name="pc")
            return quick_reply

        # 2. Перезапуск приватного сервера Roblox
        if self.ROBLOX_RESET_PATTERNS.search(text):
            task = self.tasks.create_task("Перезапуск приватного сервера Roblox", text, "roblox")
            resp = self.agents.dispatch("roblox", task)
            reply = resp.output if resp.success else f"Сер, не вдалося перезапустити сервер: {resp.error}"
            self.store.add_message(session_id, "assistant", reply, agent_name="roblox")
            return reply

        # 3. Явні запити на генерацію коду
        if re.search(r"(?i)(?:напиши|створи|згенеруй|зроби)\s+(?:код|скрипт|функцію|проєкт|модуль)", text):
            task = self.tasks.create_task("Генерація коду", text, "coder")
            resp = self.agents.dispatch("coder", task)
            reply = resp.output if resp.success else f"Сер, сталася помилка під час створення коду: {resp.error}"
            self.store.add_message(session_id, "assistant", reply, agent_name="coder")
            return reply

        # 4. Діагностика системи через System-агента
        if re.search(r"(?i)(?:статус пк|ресурси|навантаження|пам'ять ram|система)", text):
            task = self.tasks.create_task("Діагностика системи", text, "system")
            resp = self.agents.dispatch("system", task)
            reply = resp.output if resp.success else f"Сер, помилка отримання метрик: {resp.error}"
            self.store.add_message(session_id, "assistant", reply, agent_name="system")
            return reply

        # 5. Звичайна розмова з контекстом пам'яті
        recent = self.store.get_recent_messages(session_id, limit=8)
        messages = [{"role": "system", "content": self.SYSTEM_INSTRUCTIONS}]
        for message in recent:
            messages.append({"role": message["role"], "content": message["content"]})

        try:
            result = self.router.complete(messages, task_type="chat")
            reply = result["content"]
            self.store.add_message(session_id, "assistant", reply, agent_name="brain")
            return reply
        except Exception as exc:
            logger.exception("Brain reasoning error: %s", exc)
            return f"Сер, виникла затримка зв'язку з моделлю: {exc}"

    # ── швидкі дії на ПК ─────────────────────────────────────────────────────
    def _try_quick_action(self, text: str) -> Optional[str]:
        """
        Розпізнає прості команди керування ПК і виконує їх через PcController.

        Повертає текст відповіді або ``None``, якщо це не швидка дія (тоді
        запит іде далі — до агентів/моделі).
        """
        if self.pc is None:
            return None
        stripped = text.strip()

        open_match = self.QUICK_OPEN_PATTERNS.match(stripped)
        if open_match:
            target = open_match.group(1).strip().strip("\"'\u00ab\u00bb")
            target = re.sub(
                r"(?i)[\s,]+(?:мені|будь\s+ласка|please)\s*$", "", target
            ).strip()
            target = re.sub(r"(?i)\s+(?:у|в)\s+браузер[іe]\s*$", "", target).strip()
            target = re.sub(r"(?i)\s+in\s+(?:the\s+)?browser\s*$", "", target).strip()
            if not target:
                return None
            try:
                known = bool(self.pc.is_known_target(target))
            except Exception:
                known = False
            if not known:
                return None
            resolved, kind = self.pc.resolve_target(target)
            if kind == "app" and not self.config.get("full_access", True):
                return "Сер, запуск програм вимкнено в налаштуваннях доступу."
            self.security.authorize(
                "Відкриття об'єкта",
                f"Ціль: {target} → {resolved}",
                SecurityLevel.CONTROLLED,
                agent_name="brain",
            )
            return self.pc.open_app(resolved)

        if self.SYSTEM_INFO_PATTERNS.search(stripped):
            self.security.authorize(
                "Системна діагностика",
                "PcController.system_info()",
                SecurityLevel.SAFE,
                agent_name="brain",
            )
            return self.pc.system_info()

        return None
