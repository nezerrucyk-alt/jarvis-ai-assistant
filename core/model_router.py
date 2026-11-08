# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — AI Model Router.
Intelligently selects and queries models based on task nature:
- Coding: high-context coding models
- Reasoning: structured step-by-step thinking models
- Fast/Conversational: low-latency models (Groq / Gemini Flash)
- Local: Ollama fallback if available
Supports automatic fallback and retry mechanisms.
"""

from __future__ import annotations
import json
import logging
import re
import time
from typing import Any, Optional
import requests

logger = logging.getLogger("Jarvis.ModelRouter")


class ModelRouter:
    DIRECT_PROVIDERS = {
        "gemini-direct": {
            "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            "key_field": "gemini_api_key",
        },
        "groq-direct": {
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "key_field": "groq_api_key",
        },
        "xkiro": {
            "url": "https://api.xkiro.com/v1/chat/completions",
            "key_field": "xkiro_api_key",
        },
        "deepseek-direct": {
            "url": "https://api.deepseek.com/v1/chat/completions",
            "key_field": "deepseek_api_key",
        },
        "cerebras-direct": {
            "url": "https://api.cerebras.ai/v1/chat/completions",
            "key_field": "cerebras_api_key",
        },
        "mistral-direct": {
            "url": "https://api.mistral.ai/v1/chat/completions",
            "key_field": "mistral_api_key",
        },
        "together-direct": {
            "url": "https://api.together.xyz/v1/chat/completions",
            "key_field": "together_api_key",
        },
        "ashna": {
            "url": "https://api.ashna.ai/v1/api/chat/completions",
            "key_field": "ashna_api_key",
        },
        "openrouter": {
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "key_field": "openrouter_key",
        },
        "ollama": {
            "url": "http://127.0.0.1:11434/v1/chat/completions",
            "key_field": "",
        },
    }

    TASK_PROFILES = {
        "chat": ["xkiro/qwen/qwen3.7-flash:free", "groq-direct/openai/gpt-oss-20b", "gemini-direct/gemini-3.8-flash"],
        "coding": ["xkiro/qwen/qwen3-coder-plus:free", "gemini-direct/gemini-3.8-flash", "groq-direct/openai/gpt-oss-20b"],
        "reasoning": ["xkiro/qwen/qwen3.8-max:free", "gemini-direct/gemini-3.8-flash", "groq-direct/openai/gpt-oss-120b"],
        "fast": ["xkiro/qwen/qwen3.7-flash:free", "groq-direct/openai/gpt-oss-20b", "gemini-direct/gemini-3.5-flash-lite"],
    }

    def __init__(self, config: dict):
        self.config = config

    @staticmethod
    def _split_keys(value) -> list[str]:
        """Розділяє ключі, введені через кому/пробіл/крапку з комою або списком."""
        chunks = (
            list(value)
            if isinstance(value, (list, tuple))
            else re.split(r"[\s,;]+", str(value or ""))
        )
        keys: list[str] = []
        for chunk in chunks:
            key = str(chunk).strip()
            if key and key not in keys:
                keys.append(key)
        return keys

    def _keys_for(self, key_field: str) -> list[str]:
        """Повертає всі ключі провайдера (поле + резервні для xKiro)."""
        keys = self._split_keys(self.config.get(key_field) or "")
        if key_field == "xkiro_api_key":
            extras = [
                self.config.get("xkiro_backup_key"),
                *(self.config.get("xkiro_keys") or []),
            ]
            for value in extras:
                for key in self._split_keys(value):
                    if key not in keys:
                        keys.append(key)
        return keys

    def _resolve_endpoints(self, model_id: str) -> list[tuple[str, str, str]]:
        """Returns list of (endpoint_url, api_model_name, api_key) to try."""
        for prefix, provider in self.DIRECT_PROVIDERS.items():
            # OpenRouter отримує повний id моделі як є (напр. "openrouter/auto-code").
            if prefix == "openrouter" or not model_id.startswith(prefix + "/"):
                continue
            api_model = model_id.split("/", 1)[1]
            if not provider["key_field"]:
                return [(provider["url"], api_model, "ollama")]
            return [
                (provider["url"], api_model, key)
                for key in self._keys_for(provider["key_field"])
            ]
        return [
            (self.DIRECT_PROVIDERS["openrouter"]["url"], model_id, key)
            for key in self._keys_for("openrouter_key")
        ]

    def select_model(self, task_type: str = "chat") -> str:
        """Determines best active model for task type based on configured keys."""
        preferred = self.config.get("model")
        if preferred:
            return preferred

        candidates = self.TASK_PROFILES.get(task_type, self.TASK_PROFILES["chat"])
        for candidate in candidates:
            endpoints = self._resolve_endpoints(candidate)
            for _, _, key in endpoints:
                if key or candidate.startswith("ollama/"):
                    return candidate

        return "groq-direct/openai/gpt-oss-20b"

    def complete(
        self,
        messages: list[dict],
        task_type: str = "chat",
        tools: Optional[list[dict]] = None,
        max_tokens: int = 1500,
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        """
        Executes a completion request with fallback on failure.
        Returns a dict: {"content": str, "tool_calls": list, "model": str}
        """
        primary_model = self.select_model(task_type)
        fallback_models = [
            m for m in [
                "xkiro/qwen/qwen3.7-flash:free",
                "groq-direct/openai/gpt-oss-20b",
                "gemini-direct/gemini-3.8-flash",
            ]
            if m != primary_model
        ]
        models_to_try = [primary_model] + fallback_models

        last_error = None
        for model in models_to_try:
            endpoints = self._resolve_endpoints(model)
            for idx, (url, api_model, api_key) in enumerate(endpoints):
                if not api_key and not model.startswith("ollama/"):
                    continue

                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "JarvisUltimate/2.0",
                }
                if api_key and api_key != "ollama":
                    headers["Authorization"] = f"Bearer {api_key}"

                body: dict[str, Any] = {
                    "model": api_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
                if tools:
                    body["tools"] = tools
                    body["tool_choice"] = "auto"

                try:
                    resp = requests.post(url, headers=headers, json=body, timeout=45)
                    if resp.status_code == 200:
                        if idx > 0 and model.startswith("xkiro/"):
                            logger.info("Backup xKiro key promoted to primary.")
                            self.config["xkiro_api_key"] = api_key
                        data = resp.json()
                        choice = data.get("choices", [{}])[0]
                        msg = choice.get("message", {})
                        return {
                            "content": (msg.get("content") or "").strip(),
                            "tool_calls": msg.get("tool_calls") or [],
                            "model": model,
                        }
                    elif resp.status_code in (429, 402, 403):
                        logger.warning(
                            "Model %s with key #%s returned %s (quota/rate-limit). Failing over...",
                            model, idx + 1, resp.status_code
                        )
                        last_error = f"HTTP {resp.status_code}: {resp.text[:120]}"
                        continue
                    else:
                        logger.warning(
                            "Model %s returned code %s: %s",
                            model,
                            resp.status_code,
                            resp.text[:200],
                        )
                        last_error = f"HTTP {resp.status_code}: {resp.text[:120]}"
                except Exception as exc:
                    logger.warning("Error querying model %s (key #%s): %s", model, idx + 1, exc)
                    last_error = str(exc)

        raise RuntimeError(f"All model candidates failed. Last error: {last_error}")
