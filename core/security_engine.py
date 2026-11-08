# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — Security Engine.
Enforces 3-tier safety boundaries: Safe, Controlled, and Approval.
Provides Emergency Stop control across all running tasks.
"""

from __future__ import annotations
import enum
import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger("Jarvis.Security")


class SecurityLevel(enum.Enum):
    SAFE = "safe"              # Auto-executed (read, inspect, calculate)
    CONTROLLED = "controlled"  # Logged & auditable (create files, open sites)
    APPROVAL = "approval"      # Requires explicit user authorization (delete, kill, run scripts)


class SecurityEngine:
    def __init__(self, confirm_callback: Optional[Callable[[str, str], bool]] = None):
        self._confirm_callback = confirm_callback
        self._emergency_stop = threading.Event()
        self._audit_log: list[dict] = []
        self._lock = threading.Lock()

    def set_confirm_callback(self, callback: Callable[[str, str], bool]) -> None:
        self._confirm_callback = callback

    @property
    def is_stopped(self) -> bool:
        return self._emergency_stop.is_set()

    def trigger_emergency_stop(self) -> None:
        """Immediately halts all active agent operations."""
        self._emergency_stop.set()
        logger.warning("🚨 EMERGENCY STOP TRIGGERED! All running tasks must abort.")

    def reset_emergency_stop(self) -> None:
        self._emergency_stop.clear()
        logger.info("✓ Emergency stop cleared. Operations resumed.")

    def authorize(
        self,
        action_name: str,
        details: str,
        level: SecurityLevel,
        agent_name: str = "core",
    ) -> bool:
        """
        Validates whether an action is permitted under the current security context.
        Returns True if allowed, False otherwise.
        """
        if self.is_stopped:
            logger.warning("Action '%s' blocked by Emergency Stop.", action_name)
            return False

        with self._lock:
            self._audit_log.append({
                "action": action_name,
                "agent": agent_name,
                "level": level.value,
                "details": details[:300],
            })

        if level == SecurityLevel.SAFE:
            return True

        if level == SecurityLevel.CONTROLLED:
            logger.info("AUDIT [%s] by %s: %s", action_name, agent_name, details[:120])
            return True

        if level == SecurityLevel.APPROVAL:
            logger.info("APPROVAL REQUEST [%s] by %s", action_name, agent_name)
            if not self._confirm_callback:
                logger.warning("No confirmation callback configured; denying approval.")
                return False
            try:
                allowed = self._confirm_callback(
                    f"Дозвіл на дію: {action_name} ({agent_name})",
                    details
                )
                logger.info("APPROVAL RESULT: %s", "GRANTED" if allowed else "DENIED")
                return bool(allowed)
            except Exception as exc:
                logger.exception("Confirmation dialog failed: %s", exc)
                return False

        return False
