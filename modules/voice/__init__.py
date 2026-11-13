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
from modules.voice.wake import (
    WAKE_PHRASES,
    WakeGate,
    WakeWordListener,
    is_wake_phrase,
    normalize_wake_text,
)
from modules.voice.offline import (
    OfflineVoiceError,
    capabilities as offline_capabilities,
    stt_available as offline_stt_available,
    synthesize as offline_synthesize,
    transcribe as offline_transcribe,
    tts_available as offline_tts_available,
)

__all__ = [
    "Ears",
    "EarsError",
    "OfflineVoiceError",
    "STT",
    "TTS",
    "VOICES",
    "VOICE_BY_LANG",
    "Voice",
    "VoiceError",
    "WAKE_PHRASES",
    "WakeGate",
    "WakeWordListener",
    "for_speech",
    "has_input_device",
    "is_wake_phrase",
    "list_input_devices",
    "normalize_wake_text",
    "offline_capabilities",
    "offline_stt_available",
    "offline_synthesize",
    "offline_transcribe",
    "offline_tts_available",
    "resolve_default_input",
]
