# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — Base Agent Interface.
Standard contract for all specialized agents in the multi-agent ecosystem.
"""

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from core.security_engine import SecurityEngine, SecurityLevel
from core.task_engine import Task


@dataclass
class AgentResponse:
    success: bool
    output: str
    artifacts: list[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    def __init__(
        self,
        name: str,
        role: str,
        description: str,
        security_engine: SecurityEngine,
        model_router: Any,
    ):
        self.name = name
        self.role = role
        self.description = description
        self.security = security_engine
        self.router = model_router
        self.logger = logging.getLogger(f"Jarvis.Agent.{name}")

    def authorize_action(
        self, action_name: str, details: str, level: SecurityLevel = SecurityLevel.SAFE
    ) -> bool:
        """Helper to query the central Security Engine."""
        return self.security.authorize(
            action_name=action_name,
            details=details,
            level=level,
            agent_name=self.name,
        )

    @abstractmethod
    def execute(self, task: Task, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        """Processes the assigned task and returns a standardized AgentResponse."""
        pass
