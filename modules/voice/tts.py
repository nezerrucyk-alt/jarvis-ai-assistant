# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — синтез мовлення (TTS).

Основний рушій — Edge TTS (нейронні голоси Microsoft) з відтворенням через
``pygame.mixer``. Якщо мережа, edge-tts або pygame недоступні, використовується
резервний синтез:

1. ``pyttsx3`` (у Windows — SAPI5, системний голос);
2. прямий ``System.Speech`` через PowerShell — остання спроба.

Модуль не виконує жодних дій під час імпорту: важкі залежності імпортуються
ліниво, аудіопристрій ініціалізується лише під час першого відтворення.
Клас :class:`Voice` потокобезпечний: одночасно звучить лише одне мовлення,
а :meth:`Voice.stop` можна викликати з GUI-потоку.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("Jarvis.Voice")

DEFAULT_LANGUAGE = "uk-UA"
MAX_SPEECH_CHARS = 700
EDGE_TIMEOUT_SECONDS = 45.0
TTS_RATE = 175

#: Голоси Edge TTS, доступні для вибору в налаштуваннях.
VOICES: tuple[str, ...] = (
    "uk-UA-OstapNeural",
    "uk-UA-PolinaNeural",
    "ru-RU-DmitryNeural",
    "ru-RU-SvetlanaNeural",
    "en-GB-RyanNeural",
    "en-GB-ThomasNeural",
    "en-GB-SoniaNeural",
    "en-US-GuyNeural",
)

#: Голос Edge TTS за замовчуванням для кожної мови інтерфейсу.
VOICE_BY_LANG: dict[str, str] = {
    "uk-UA": "uk-UA-OstapNeural",
    "ru-RU": "ru-RU-DmitryNeural",
    "en-US": "en-GB-RyanNeural",
    "en-GB": "en-GB-RyanNeural",
}

_PYGAME_LOCK = threading.RLock()
_PUNCT_RE = re.compile(r"[*_#>|~`]")
_EMOJI_RE = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u2B00-\u2BFF]")


class VoiceError(RuntimeError):
    """Помилка синтезу або відтворення мовлення."""


def for_speech(text: str) -> str:
    """
    Готує текст для озвучення: прибирає markdown, код, посилання й емодзі.

    Повертає чистий текст, обрізаний до :data:`MAX_SPEECH_CHARS` символів.
    """
    cleaned = str(text or "")
    if not cleaned:
        return ""
    cleaned = re.sub(r"```.*?```", " ", cleaned, flags=re.S)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", cleaned)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = _PUNCT_RE.sub("", cleaned)
    cleaned = _EMOJI_RE.sub("", cleaned)
    cleaned = re.sub(r"(?m)^\s*[-+•]\s+", "", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()
    return cleaned[:MAX_SPEECH_CHARS]


class Voice:
    """
    Синтез мовлення з Edge TTS і резервними рушіями.

    ``config`` — той самий словник налаштувань, що й у ``jarvis.py``
    (використовуються ключі ``mute``, ``voice``, ``language``). Словник
    зберігається за посиланням, тому зміни в налаштуваннях діють одразу.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        self.config: dict[str, Any] = config if config is not None else {}
        self._speak_lock = threading.Lock()
        self._stop = threading.Event()
        self._speaking = False
        self._engine: Any = None
        self._pygame_ok = False

    # ── налаштування ─────────────────────────────────────────────────────────
    @property
    def muted(self) -> bool:
        """Чи вимкнено озвучення (ключ ``mute`` у конфігу)."""
        return bool(self.config.get("mute"))

    @property
    def is_speaking(self) -> bool:
        """Чи триває мовлення прямо зараз."""
        return self._speaking

    def set_config(self, config: dict[str, Any]) -> None:
        """Замінює словник налаштувань (наприклад, після редагування)."""
        self.config = config if config is not None else {}

    def set_mute(self, mute: bool) -> None:
        """Вмикає або вимикає озвучення; при вимкненні зупиняє поточне мовлення."""
        self.config["mute"] = bool(mute)
        if mute:
            self.stop()

    def current_voice(self) -> str:
        """Повертає ім'я голосу Edge TTS з урахуванням мови інтерфейсу."""
        configured = str(self.config.get("voice") or "").strip()
        if configured:
            return configured
        language = str(self.config.get("language") or DEFAULT_LANGUAGE)
        return VOICE_BY_LANG.get(language, VOICE_BY_LANG[DEFAULT_LANGUAGE])

    # ── керування ────────────────────────────────────────────────────────────
    def stop(self) -> None:
        """
        Зупиняє поточне мовлення.

        Безпечно викликати з будь-якого потоку, зокрема з GUI: метод не
        чекає завершення ``speak``, а лише сигналізує про зупинку та глушить
        активний аудіопотік.
        """
        self._stop.set()
        # pygame імпортуємо лише якщо він уже завантажений (не тягнемо важкий
        # модуль лише заради зупинки мовлення, якого не було).
        pygame_module = sys.modules.get("pygame")
        if pygame_module is not None:
            try:
                if pygame_module.mixer.get_init():
                    pygame_module.mixer.music.stop()
            except Exception:
                pass
        engine = self._engine
        if engine is not None:
            try:
                engine.stop()
            except Exception:
                logger.debug("Не вдалося зупинити pyttsx3", exc_info=True)

    def close(self) -> None:
        """Звільняє ресурси (еквівалент :meth:`stop`)."""
        self.stop()

    # ── публічний API ────────────────────────────────────────────────────────
    def speak(self, text: str, *, voice: Optional[str] = None) -> bool:
        """
        Озвучує текст.

        Повертає ``True``, якщо мовлення відтворено; ``False`` — якщо текст
        порожній, увімкнено ``mute``, мовлення зупинено або всі рушії
        недоступні. Ніколи не кидає винятків (помилки лише журналюються).
        """
        if self.muted:
            return False
        clean = for_speech(text)
        if not clean:
            return False

        with self._speak_lock:
            self._stop.clear()
            self._speaking = True
            selected_voice = (voice or self.current_voice()).strip() or self.current_voice()
            audio_path = Path(tempfile.gettempdir()) / (
                f"jarvis_tts_{os.getpid()}_{uuid.uuid4().hex[:8]}.mp3"
            )
            try:
                try:
                    self._generate_edge(clean, selected_voice, audio_path)
                except Exception as exc:
                    logger.warning(
                        "Edge TTS недоступний (%s); використовую резервний синтез.", exc
                    )
                    if self._stop.is_set():
                        return False
                    return self._fallback_speak(clean)

                if self._stop.is_set():
                    return False
                try:
                    self._play(audio_path)
                except Exception as exc:
                    logger.warning(
                        "Відтворення через pygame не вдалося (%s); резервний синтез.", exc
                    )
                    if self._stop.is_set():
                        return False
                    return self._fallback_speak(clean)
                return not self._stop.is_set()
            finally:
                self._speaking = False
                try:
                    audio_path.unlink(missing_ok=True)
                except OSError:
                    logger.debug("Не вдалося видалити тимчасовий файл %s", audio_path)

    def speak_async(self, text: str, *, voice: Optional[str] = None) -> threading.Thread:
        """Озвучує текст у фоновому потоці (щоб не блокувати GUI)."""
        thread = threading.Thread(
            target=self._speak_worker,
            args=(text,),
            kwargs={"voice": voice},
            name="jarvis-tts",
            daemon=True,
        )
        thread.start()
        return thread

    def _speak_worker(self, text: str, *, voice: Optional[str] = None) -> None:
        try:
            self.speak(text, voice=voice)
        except Exception:  # pragma: no cover — speak() сам не кидає винятків
            logger.exception("Помилка фонового озвучення")

    # ── Edge TTS ─────────────────────────────────────────────────────────────
    def _generate_edge(self, text: str, voice: str, path: Path) -> None:
        """Синтезує мовлення Edge TTS у тимчасовий mp3-файл."""

        async def _save() -> None:
            import edge_tts  # type: ignore[import-not-found]

            communicator = edge_tts.Communicate(text, voice, rate="+0%", pitch="-2Hz")
            await asyncio.wait_for(communicator.save(str(path)), timeout=EDGE_TIMEOUT_SECONDS)

        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is None:
            asyncio.run(_save())
            return

        # Виклик зсередини активного event loop (наприклад, з async-коду):
        # виконуємо синтез в окремому потоці з власним циклом подій.
        errors: list[BaseException] = []

        def _runner() -> None:
            try:
                asyncio.run(_save())
            except BaseException as exc:  # noqa: BLE001 — переносимо помилку в основний потік
                errors.append(exc)

        worker = threading.Thread(target=_runner, name="jarvis-edge-tts", daemon=True)
        worker.start()
        worker.join(EDGE_TIMEOUT_SECONDS + 10.0)
        if worker.is_alive():
            raise VoiceError("Edge TTS не встиг синтезувати мовлення")
        if errors:
            raise errors[0]

    def _play(self, path: Path) -> None:
        """Відтворює mp3-файл через pygame.mixer, поважаючи сигнал зупинки."""
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        import pygame  # type: ignore[import-not-found]

        with _PYGAME_LOCK:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
                self._pygame_ok = True
            try:
                pygame.mixer.music.load(str(path))
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    if self._stop.is_set():
                        break
                    time.sleep(0.05)
            finally:
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    logger.debug("pygame.mixer.music.stop() не вдався", exc_info=True)

    # ── резервний синтез ─────────────────────────────────────────────────────
    def _fallback_speak(self, text: str) -> bool:
        """Резервний синтез: pyttsx3 (SAPI5), інакше System.Speech через PowerShell."""
        if self.muted or self._stop.is_set():
            return False
        try:
            import pyttsx3  # type: ignore[import-not-found]

            engine = pyttsx3.init()
            engine.setProperty("rate", TTS_RATE)
            self._configure_sapi_voice(engine)
            self._engine = engine
            try:
                if self._stop.is_set():
                    return False
                engine.say(text)
                engine.runAndWait()
            finally:
                self._engine = None
                try:
                    engine.stop()
                except Exception:
                    logger.debug("pyttsx3 engine.stop() не вдався", exc_info=True)
            return not self._stop.is_set()
        except Exception:
            logger.exception("Резервний синтез pyttsx3 недоступний; пробую System.Speech.")

        return self._sapi_speak(text)

    def _configure_sapi_voice(self, engine: Any) -> None:
        """Намагається підібрати системний голос pyttsx3 під мову конфігу."""
        language = str(self.config.get("language") or DEFAULT_LANGUAGE).strip().lower()
        if not language:
            return
        prefix = language.split("-")[0]
        try:
            voices = engine.getProperty("voices") or []
        except Exception:
            return
        for item in voices:
            try:
                names: list[str] = []
                for value in getattr(item, "languages", None) or []:
                    if isinstance(value, bytes):
                        names.append(value.decode("utf-8", "ignore"))
                    else:
                        names.append(str(value))
                names.append(str(getattr(item, "name", "") or ""))
                haystack = " ".join(names).lower()
                if prefix and (prefix in haystack or language in haystack):
                    engine.setProperty("voice", item.id)
                    return
            except Exception:
                continue

    def _sapi_speak(self, text: str) -> bool:
        """Остання спроба: озвучення через System.Speech у PowerShell."""
        if os.name != "nt":
            return False
        if self.muted or self._stop.is_set():
            return False
        escaped = str(text).replace("'", "''")[:MAX_SPEECH_CHARS]
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$synth.Rate = 0; "
            f"$synth.Speak('{escaped}');"
        )
        try:
            proc = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                ],
                capture_output=True,
                timeout=EDGE_TIMEOUT_SECONDS + 30.0,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if proc.returncode != 0:
                logger.warning(
                    "System.Speech завершився з кодом %s: %s",
                    proc.returncode,
                    proc.stderr.decode("utf-8", "replace")[:200],
                )
            return proc.returncode == 0 and not self._stop.is_set()
        except Exception:
            logger.exception("Озвучення через System.Speech не вдалося")
            return False


#: Зручний аліас для коду, який очікує назву «TTS».
TTS = Voice

__all__ = [
    "DEFAULT_LANGUAGE",
    "MAX_SPEECH_CHARS",
    "TTS",
    "VOICES",
    "VOICE_BY_LANG",
    "Voice",
    "VoiceError",
    "for_speech",
]
