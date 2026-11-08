# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — Task Engine.
Manages decomposition, queueing, execution state, and tracking of autonomous tasks.
"""

from __future__ import annotations
import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


class TaskStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    id: str = field(default_factory=lambda: f"tsk_{uuid.uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    agent_name: str = "core"
    status: TaskStatus = TaskStatus.PENDING
    subtasks: list[Task] = field(default_factory=list)
    result: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "agent_name": self.agent_name,
            "status": self.status.value,
            "subtasks": [st.to_dict() for st in self.subtasks],
            "result": self.result,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TaskEngine:
    def __init__(self):
        self._tasks: dict[str, Task] = {}

    def create_task(self, title: str, description: str = "", agent_name: str = "core") -> Task:
        task = Task(title=title, description=description, agent_name=agent_name)
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def update_task_status(
        self, task_id: str, status: TaskStatus, result: Optional[str] = None
    ) -> Optional[Task]:
        task = self._tasks.get(task_id)
        if task:
            task.status = status
            task.updated_at = time.time()
            if result is not None:
                task.result = result
        return task

    def list_active_tasks(self) -> list[Task]:
        return [
            t for t in self._tasks.values()
            if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
        ]

    def list_all_tasks(self) -> list[Task]:
        return sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)
