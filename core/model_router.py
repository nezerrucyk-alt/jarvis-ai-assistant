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
        "openai-direct": {
            "url": "https://api.openai.com/v1/chat/completions",
            "key_field": "openai_api_key",
        },
        "anthropic-direct": {
            "url": "https://api.anthropic.com/v1/messages",
            "key_field": "anthropic_api_key",
            "api_style": "anthropic",
        },
        "xai-direct": {
            "url": "https://api.x.ai/v1/chat/completions",
            "key_field": "xai_api_key",
        },
        "moonshot-direct": {
            "url": "https://api.moonshot.ai/v1/chat/completions",
            "key_field": "moonshot_api_key",
        },
        "qwen-direct": {
            "url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            "key_field": "qwen_api_key",
        },
        "cursor": {
            "url": "https://api.cursor.com/v1/chat/completions",
            "key_field": "cursor_api_key",
            "url_field": "cursor_api_url",
            "model_field": "cursor_model",
        },
        "custom": {
            "url": "",
            "url_field": "custom_api_url",
            "key_field": "custom_api_key",
            "model_field": "custom_model",
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
        "chat": [
            "openai-direct/gpt-5.6-sol",
            "anthropic-direct/claude-sonnet-5.5",
            "xkiro/qwen/qwen3.7-flash:free",
            "groq-direct/openai/gpt-oss-20b",
            "gemini-direct/gemini-3.8-flash",
        ],
        "coding": [
            "openai-direct/gpt-5.3-codex",
            "anthropic-direct/claude-sonnet-5.5",
            "moonshot-direct/kimi-k2.7-code",
            "qwen-direct/qwen3-coder-plus",
            "xkiro/qwen/qwen3-coder-plus:free",
            "gemini-direct/gemini-3.8-flash",
        ],
        "reasoning": [
            "anthropic-direct/claude-opus-5.5",
            "openai-direct/gpt-6.1-sol",
            "xai-direct/grok-4.7",
            "xkiro/qwen/qwen3.8-max:free",
            "gemini-direct/gemini-3.8-flash",
        ],
        "fast": [
            "xai-direct/grok-4.7-fast",
            "anthropic-direct/claude-haiku-5",
            "xkiro/qwen/qwen3.7-flash:free",
            "groq-direct/openai/gpt-oss-20b",
            "gemini-direct/gemini-3.5-flash-lite",
        ],
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
            url = str(provider.get("url") or "")
            url_field = provider.get("url_field")
            if url_field:
                custom_url = str(self.config.get(url_field) or "").strip()
                if custom_url:
                    url = custom_url
            model_field = provider.get("model_field")
            if model_field:
                custom_model = str(self.config.get(model_field) or "").strip()
                if custom_model:
                    api_model = custom_model
            if not url:
                return []
            if not provider["key_field"]:
                return [(url, api_model, "ollama")]
            return [
                (url, api_model, key)
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

    @staticmethod
    def _anthropic_payload(
        model: str,
        messages: list[dict],
        tools: Optional[list[dict]],
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        """Перетворює OpenAI-style запит у формат Anthropic Messages API."""
        system_parts: list[str] = []
        converted: list[dict] = []
        for message in messages or []:
            role = str(message.get("role") or "")
            content = message.get("content")
            if role == "system":
                system_parts.append(str(content or ""))
                continue
            if role not in ("user", "assistant"):
                continue
            blocks: list[dict] = []
            if isinstance(content, str):
                if content:
                    blocks.append({"type": "text", "text": content})
            elif isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    if part.get("type") == "text" and part.get("text"):
                        blocks.append({"type": "text", "text": str(part["text"])})
                    elif part.get("type") == "image_url":
                        url = str((part.get("image_url") or {}).get("url") or "")
                        if url.startswith("data:") and "," in url:
                            header, data = url.split(",", 1)
                            media_type = header[5:].split(";", 1)[0] or "image/jpeg"
                            blocks.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": data,
                                },
                            })
            if not blocks:
                continue
            if converted and converted[-1]["role"] == role:
                converted[-1]["content"].extend(blocks)
            else:
                converted.append({"role": role, "content": blocks})
        while converted and converted[0]["role"] != "user":
            converted.pop(0)
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": converted,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        if tools:
            payload["tools"] = [
                {
                    "name": str((item.get("function") or {}).get("name") or ""),
                    "description": str(
                        (item.get("function") or {}).get("description") or ""
                    ),
                    "input_schema": (item.get("function") or {}).get("parameters")
                    or {"type": "object", "properties": {}},
                }
                for item in tools
                if str((item.get("function") or {}).get("name") or "").strip()
            ]
        return payload

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

                anthropic = model.startswith("anthropic-direct/")
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "JarvisUltimate/2.1",
                }
                if anthropic:
                    headers["x-api-key"] = api_key
                    headers["anthropic-version"] = "2023-06-01"
                elif api_key and api_key != "ollama":
                    headers["Authorization"] = f"Bearer {api_key}"

                if anthropic:
                    body = self._anthropic_payload(
                        api_model, messages, tools, max_tokens, temperature
                    )
                else:
                    body = {
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
                        if anthropic:
                            blocks = data.get("content") or []
                            text = "".join(
                                str(block.get("text") or "")
                                for block in blocks
                                if isinstance(block, dict)
                                and block.get("type") == "text"
                            ).strip()
                            return {
                                "content": text,
                                "tool_calls": [
                                    block for block in blocks
                                    if isinstance(block, dict)
                                    and block.get("type") == "tool_use"
                                ],
                                "model": model,
                            }
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
