# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — Agent Manager.
Orchestrates agent lifecycles, handles routing, and monitors execution.
"""

from __future__ import annotations
import logging
from typing import Any, Optional
from agents.base_agent import BaseAgent, AgentResponse
from core.task_engine import Task, TaskStatus

logger = logging.getLogger("Jarvis.AgentManager")


class AgentManager:
    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.name.lower()] = agent
        logger.info("Registered agent: %s (%s)", agent.name, agent.role)

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        return self._agents.get(name.lower())

    def list_agents(self) -> list[dict[str, str]]:
        return [
            {"name": ag.name, "role": ag.role, "description": ag.description}
            for ag in self._agents.values()
        ]

    def dispatch(self, agent_name: str, task: Task, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        agent = self.get_agent(agent_name)
        if not agent:
            err = f"Agent '{agent_name}' not found."
            logger.error(err)
            return AgentResponse(success=False, output="", error=err)

        logger.info("Dispatching task '%s' to agent [%s]", task.title, agent.name)
        task.status = TaskStatus.IN_PROGRESS
        try:
            resp = agent.execute(task, context)
            task.status = TaskStatus.COMPLETED if resp.success else TaskStatus.FAILED
            task.result = resp.output or resp.error
            return resp
        except Exception as exc:
            logger.exception("Agent %s failed unexpectedly: %s", agent_name, exc)
            task.status = TaskStatus.FAILED
            task.result = str(exc)
            return AgentResponse(success=False, output="", error=str(exc))
