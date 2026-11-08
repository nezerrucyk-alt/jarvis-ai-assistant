# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — голосовий модуль (TTS + STT).

Публічний API:

* :class:`modules.voice.tts.Voice` (аліас ``TTS``) — синтез мовлення;
* :class:`modules.voice.stt.Ears` (аліас ``STT``) — запис і розпізнавання;
* :func:`modules.voice.tts.for_speech` — очищення тексту для озвучення;
* :func:`modules.voice.stt.has_input_device` / ``list_input_devices`` —
  перевірка доступності мікрофона.

Імпорт модуля не відкриває аудіопристроїв і не звертається до мережі.
"""

from __future__ import annotations

from modules.voice.stt import (
    Ears,
    EarsError,
    STT,
    has_input_device,
    list_input_devices,
    resolve_default_input,
)
from modules.voice.tts import (
    TTS,
    VOICE_BY_LANG,
    VOICES,
    Voice,
    VoiceError,
    for_speech,
)

__all__ = [
    "Ears",
    "EarsError",
    "STT",
    "TTS",
    "VOICES",
    "VOICE_BY_LANG",
    "Voice",
    "VoiceError",
    "for_speech",
    "has_input_device",
    "list_input_devices",
    "resolve_default_input",
]
