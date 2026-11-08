# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — System Agent.
Monitors Windows system health, manages running processes, and runs PowerShell commands.
"""

from __future__ import annotations
import logging
import os
import re
import subprocess
import time
from typing import Any, Optional
from agents.base_agent import BaseAgent, AgentResponse
from core.security_engine import SecurityLevel
from core.task_engine import Task


class SystemAgent(BaseAgent):
    SAFE_COMMANDS = re.compile(
        r"(?i)^\s*(?:get-[a-z]+|test-path|dir\b|ls\b|echo\b|systeminfo|ipconfig|whoami|hostname|uptime)\b"
    )

    def __init__(self, security_engine, model_router):
        super().__init__(
            name="System",
            role="OS Controller & Diagnostics",
            description="Керує Windows, виконує перевірені команди, відстежує ресурси ПК.",
            security_engine=security_engine,
            model_router=model_router,
        )

    def get_system_metrics(self) -> dict[str, Any]:
        """Gathers fast system diagnostics."""
        metrics: dict[str, Any] = {
            "os": "Windows",
            "hostname": os.environ.get("COMPUTERNAME", "PC"),
            "username": os.environ.get("USERNAME", "User"),
        }
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            total_gb = stat.ullTotalPhys / (1024 ** 3)
            avail_gb = stat.ullAvailPhys / (1024 ** 3)
            used_gb = total_gb - avail_gb
            metrics["ram_total_gb"] = round(total_gb, 1)
            metrics["ram_used_gb"] = round(used_gb, 1)
            metrics["ram_load_pct"] = stat.dwMemoryLoad
        except Exception:
            pass
        return metrics

    def run_powershell(self, command: str, timeout_sec: int = 30) -> tuple[int, str, str]:
        cmd = (command or "").strip()
        is_safe = bool(self.SAFE_COMMANDS.match(cmd))
        level = SecurityLevel.SAFE if is_safe else SecurityLevel.APPROVAL

        if not self.authorize_action(f"PowerShell: {cmd[:60]}", cmd, level):
            return (-1, "", "Дію заблоковано користувачем або системою безпеки.")

        wrapped = f"$OutputEncoding=[System.Text.Encoding]::UTF8; {cmd}"
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", wrapped],
                capture_output=True,
                timeout=timeout_sec,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            stdout = proc.stdout.decode("utf-8", "replace").strip()
            stderr = proc.stderr.decode("utf-8", "replace").strip()
            return (proc.returncode, stdout, stderr)
        except Exception as exc:
            return (-1, "", str(exc))

    def execute(self, task: Task, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        self.logger.info("Executing system task: %s", task.title)
        cmd = (context or {}).get("command")
        if cmd:
            code, out, err = self.run_powershell(cmd)
            res = out if code == 0 else f"Exit code {code}\nSTDOUT: {out}\nSTDERR: {err}"
            return AgentResponse(success=(code == 0), output=res, error=err if code != 0 else None)

        metrics = self.get_system_metrics()
        info_lines = [
            f"💻 ПК: {metrics.get('hostname')} (Користувач: {metrics.get('username')})",
            f"🧠 RAM: {metrics.get('ram_used_gb')}/{metrics.get('ram_total_gb')} ГБ ({metrics.get('ram_load_pct')}%)",
        ]
        return AgentResponse(success=True, output="\n".join(info_lines), metadata=metrics)
