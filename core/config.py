# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — спільні шляхи та конфігурація модульного застосунку (v2).

Конфігурація — ТОЙ САМИЙ файл, що використовує ``jarvis.py`` (v1):

``%APPDATA%\\Jarvis\\config.json``

Тому обидві версії бачать однакові API-ключі, модель, мову, голос і режим
доступу. Схема :data:`DEFAULT_CONFIG` узгоджена з ``DEFAULT_CONFIG`` у
``jarvis.py`` (включно з ``xkiro_api_key``, ``xkiro_backup_key``,
``deepseek_api_key`` та іншими провайдерами).

Імпорт модуля не створює тек і не читає диск — лише обчислює шляхи.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from modules.voice.tts import VOICE_BY_LANG, VOICES

logger = logging.getLogger("Jarvis.Config")

APP_NAME = "Jarvis"
APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("APPDATA", str(APP_DIR))) / APP_NAME
CONFIG_PATH = DATA_DIR / "config.json"
LOG_PATH = DATA_DIR / "jarvis_ultimate.log"

#: Значення за замовчуванням — та сама схема, що й у ``jarvis.py``.
DEFAULT_CONFIG: dict[str, Any] = {
    # ── API-ключі провайдерів ──
    "openrouter_key": "",
    "gemini_api_key": "",
    "groq_api_key": "",
    "xkiro_api_key": "",
    "xkiro_backup_key": "",
    "deepseek_api_key": "",
    "cerebras_api_key": "",
    "mistral_api_key": "",
    "together_api_key": "",
    "ashna_api_key": "",
    "openai_api_key": "",
    "anthropic_api_key": "",
    "xai_api_key": "",
    "moonshot_api_key": "",
    "qwen_api_key": "",
    "cursor_api_key": "",
    "cursor_api_url": "https://api.cursor.com/v1/chat/completions",
    "cursor_model": "composer-2.5",
    "custom_provider_name": "Мій провайдер",
    "custom_api_url": "",
    "custom_api_key": "",
    "custom_model": "",
    "custom_vision": True,
    # ── модель та мовлення ──
    "model": "deepseek-direct/deepseek-chat",
    "language": "uk-UA",
    "voice": "uk-UA-OstapNeural",
    "mute": False,
    "always_on_top": False,
    "max_history": 12,
    "greet": True,
    # ── поведінка та доступ ──
    "full_access": True,
    "roblox_private_server": "https://www.roblox.com/private-server/configure/4284643793",
    "response_mode": "natural",
    "use_memory": False,
    "voice_hotkey": False,
    "wake_word": False,
    "wake_word_continuous": True,
    "wake_word_model": "hey_jarvis",
    "wake_word_threshold": 0.5,
    "wake_word_cooldown": 2.0,
    "offline_mode": False,
    "offline_model": "ollama/llama3.2",
    "offline_ollama_url": "http://127.0.0.1:11434/v1/chat/completions",
    "stt_backend": "auto",
    "tts_backend": "auto",
    "offline_stt_binary": "",
    "offline_stt_command": "",
    "offline_whisper_model": "",
    "offline_tts_binary": "",
    "offline_tts_command": "",
    "offline_piper_model": "",
    "clipboard_history": True,
    "clipboard_limit": 120,
    "watch_downloads": False,
    "watch_downloads_interval": 30,
    "briefing_city": "Київ",
    "briefing_lat": 50.45,
    "briefing_lon": 30.52,
    "briefing_time": "09:00",
    "hud_enabled": False,
    "telegram_enabled": False,
    "telegram_token": "",
    "telegram_chat_id": "",
}

#: Мови інтерфейсу/розпізнавання, доступні в налаштуваннях.
LANGUAGES: tuple[str, ...] = ("uk-UA", "ru-RU", "en-US")

#: Режими відповіді, доступні в налаштуваннях (ключ → підпис у GUI).
RESPONSE_MODES: dict[str, str] = {
    "natural": "Розмова",
    "brief": "Коротко",
    "detailed": "Докладно",
    "max": "Макс",
    "coding": "Код",
    "coder": "Кодер",
    "review": "Сувора оцінка",
}

#: Моделі, які пропонуються у випадаючому списку налаштувань.
#: Будь-який інший ідентифікатор можна вписати вручну.
MODEL_CHOICES: tuple[str, ...] = (
    # Прямі провайдери (див. core.model_router.ModelRouter)
    "deepseek-direct/deepseek-chat",
    "deepseek-direct/deepseek-reasoner",
    "xkiro/qwen/qwen3.7-flash:free",
    "xkiro/qwen/qwen3-coder-plus:free",
    "xkiro/qwen/qwen3.8-max:free",
    "xkiro/qwen/qwen3.7-max:free",
    "xkiro/qwen/qwen3.7-plus:free",
    "xkiro/qwen/qwen3.6-max-preview:free",
    "xkiro/qwen/qwen3.6-plus:free",
    "xkiro/qwen/qwen3.5-397b-a17b:free",
    "xkiro/cohere/north-mini-code",
    "xkiro/mistralai/codestral-2508",
    "xkiro/mistralai/devstral-medium",
    "xkiro/deepseek/deepseek-v4.1-flash",
    "xkiro/deepseek/deepseek-v4-pro-0813",
    "xkiro/moonshotai/kimi-k2.8-preview-agent",
    "xkiro/moonshotai/kimi-k3-agent",
    "xkiro/anthropic/claude-sonnet-5",
    "xkiro/openai/gpt-5.6-sol",
    "xkiro/openai/gpt-6.1-sol",
    "xkiro/x-ai/grok-4.7",
    "groq-direct/openai/gpt-oss-20b",
    "groq-direct/openai/gpt-oss-120b",
    "groq-direct/qwen/qwen3.8-27b",
    "ollama/llama3.2",
    "ollama/qwen2.5:7b",
    "ollama/gemma3:4b",
    "gemini-direct/gemini-3.8-flash",
    "gemini-direct/gemini-3.5-flash-lite",
    "openai-direct/gpt-6.1-sol",
    "openai-direct/gpt-5.6-sol",
    "openai-direct/gpt-5.3-codex",
    "anthropic-direct/claude-opus-5.5",
    "anthropic-direct/claude-sonnet-5.5",
    "anthropic-direct/claude-haiku-5",
    "xai-direct/grok-4.7",
    "xai-direct/grok-4.7-fast",
    "moonshot-direct/kimi-k3",
    "moonshot-direct/kimi-k2.7-code",
    "qwen-direct/qwen3.8-max",
    "qwen-direct/qwen3-coder-plus",
    "qwen-direct/qwen3-vl-plus",
    "cursor/composer-2.5",
    "cerebras-direct/llama-3.3-70b",
    "mistral-direct/mistral-small-latest",
    "together-direct/llama-3.3-70b",
    "ashna/auto",
    "ashna/deepseek-v4.1-flash",
    "ashna/deepseek-v4-pro",
    "ashna/gpt-6-luna",
    "ashna/gpt-5.3-codex",
    "ashna/gpt-5.2-codex",
    "ashna/claude-sonnet-5",
    "ashna/claude-opus-5",
    "ashna/glm-5.3",
    "ashna/kimi-k2.7-code",
    # OpenRouter (використовує openrouter_key)
    "openrouter/auto-code",
    "openrouter/free",
    "qwen/qwen3-coder",
    "qwen/qwen3-coder-next",
    "qwen/qwen3-coder-flash",
    "deepseek/deepseek-v4.1-flash",
    "deepseek/deepseek-v4-pro",
    "moonshotai/kimi-k2.7-code",
    "moonshotai/kimi-k3",
    "openai/gpt-5.3-codex",
    "openai/gpt-5.2-codex",
    "mistralai/codestral-2508",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3.5-lightning:free",
    "anthropic/claude-opus-5.5",
    "anthropic/claude-sonnet-5.5",
)


def load_config() -> dict[str, Any]:
    """
    Читає спільний ``config.json`` та доповнює його значеннями за замовчуванням.

    Відсутній або пошкоджений файл не є помилкою: повертаються типові
    значення. Невідомі ключі з файлу зберігаються без змін.
    """
    config: dict[str, Any] = dict(DEFAULT_CONFIG)
    try:
        if CONFIG_PATH.is_file():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                config.update(data)
            else:
                logger.warning("config.json має неочікуваний формат — використовую типові.")
    except Exception:
        logger.exception("Не вдалося прочитати config.json — використовую типові значення.")

    if not config.get("roblox_private_server"):
        config["roblox_private_server"] = DEFAULT_CONFIG["roblox_private_server"]
    return config


def save_config(config: dict[str, Any]) -> None:
    """
    Атомарно записує конфігурацію у спільний ``config.json``.

    Використовує тимчасовий файл і ``Path.replace``, щоб не пошкодити
    конфіг при раптовому завершенні процесу.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = CONFIG_PATH.with_suffix(".tmp")
    tmp_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp_path.replace(CONFIG_PATH)


def update_config(changes: dict[str, Any]) -> dict[str, Any]:
    """Читає конфіг, застосовує зміни, зберігає і повертає оновлений словник."""
    config = load_config()
    config.update(changes or {})
    save_config(config)
    return config


__all__ = [
    "APP_DIR",
    "APP_NAME",
    "CONFIG_PATH",
    "DATA_DIR",
    "DEFAULT_CONFIG",
    "LANGUAGES",
    "LOG_PATH",
    "MODEL_CHOICES",
    "RESPONSE_MODES",
    "VOICE_BY_LANG",
    "VOICES",
    "load_config",
    "save_config",
    "update_config",
]
