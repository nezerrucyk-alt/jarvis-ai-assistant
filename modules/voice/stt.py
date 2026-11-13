# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — розпізнавання мовлення (STT).

Запис із мікрофона виконується через ``sounddevice`` (16 кГц, моно, float32),
з автоматичним калібруванням шуму за RMS і голосовою активацією (VAD):
запис починається, коли рівень сигналу перевищує поріг, і завершується після
періоду тиші або після максимальної тривалості. Розпізнавання — Google Web
Speech через ``SpeechRecognition``: основна мова з конфігу (``uk-UA``),
за потреби — резервна (``ru-RU``).

Модуль не робить мережевих чи аудіовикликів під час імпорту: ``numpy``,
``sounddevice`` і ``speech_recognition`` імпортуються ліниво.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

logger = logging.getLogger("Jarvis.STT")

DEFAULT_LANGUAGE = "uk-UA"
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_BLOCK_SECONDS = 0.1
DEFAULT_SILENCE_SECONDS = 1.2
DEFAULT_MAX_RECORD_SECONDS = 20.0
DEFAULT_START_TIMEOUT_SECONDS = 6.0
CALIBRATION_BLOCKS = 4
MIN_THRESHOLD = 0.008
DEFAULT_THRESHOLD = 0.012
THRESHOLD_MULTIPLIER = 2.5

#: Резервна мова розпізнавання, якщо основна не дала результату.
LANGUAGE_FALLBACK: dict[str, str] = {
    "uk-UA": "ru-RU",
    "ru-RU": "uk-UA",
}


class EarsError(RuntimeError):
    """Помилка запису або розпізнавання мовлення (повідомлення — українською)."""


def _load_audio_libs() -> tuple[Any, Any]:
    """Ліниво імпортує numpy і sounddevice, перетворюючи ImportError на EarsError."""
    try:
        import numpy as np  # type: ignore[import-not-found]
        import sounddevice as sd  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover — залежність є в requirements.txt
        raise EarsError(
            "Сер, не встановлено модулі запису звуку (numpy / sounddevice). "
            "Перевстановіть JARVIS або виконайте pip install -r requirements.txt."
        ) from exc
    return np, sd


def list_input_devices() -> list[dict[str, Any]]:
    """
    Повертає список доступних пристроїв введення звуку.

    Кожен елемент: ``{"index", "name", "channels", "samplerate"}``.
    Якщо аудіопідсистема недоступна — кидає :class:`EarsError`.
    """
    _, sd = _load_audio_libs()
    try:
        devices = sd.query_devices()
    except Exception as exc:
        raise EarsError(
            "Сер, не вдалося отримати список аудіопристроїв. "
            "Перевірте звукові драйвери та налаштування Windows."
        ) from exc

    result: list[dict[str, Any]] = []
    for index, device in enumerate(devices):
        try:
            channels = int(device.get("max_input_channels", 0) or 0)
        except (TypeError, ValueError):
            continue
        if channels <= 0:
            continue
        result.append(
            {
                "index": index,
                "name": str(device.get("name") or f"Пристрій {index}"),
                "channels": channels,
                "samplerate": device.get("default_samplerate"),
            }
        )
    return result


def has_input_device() -> bool:
    """Перевіряє, чи є в системі хоч один пристрій введення звуку."""
    try:
        return bool(list_input_devices())
    except EarsError:
        return False


def resolve_default_input(sd_module: Any) -> dict[str, Any]:
    """Перевіряє і повертає параметри типового мікрофона або кидає :class:`EarsError`."""
    try:
        query = sd_module.query_devices(kind="input")
    except Exception as exc:
        raise EarsError(
            "Сер, мікрофон не знайдено. Підключіть мікрофон і перевірте "
            "налаштування звуку Windows."
        ) from exc
    try:
        channels = int(query.get("max_input_channels", 0) or 0)
    except (TypeError, ValueError):
        channels = 0
    if channels <= 0:
        raise EarsError(
            "Сер, типовий пристрій введення звуку не має мікрофона. "
            "Виберіть інший пристрій у налаштуваннях звуку."
        )
    return query


class Ears:
    """
    Запис і розпізнавання мовлення.

    ``config`` — словник налаштувань (використовується ключ ``language``).
    Запис потокобезпечний: одночасно може тривати лише один запис, а
    :meth:`Ears.stop` достроково перериває активний запис.
    """

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        *,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        block_seconds: float = DEFAULT_BLOCK_SECONDS,
        silence_seconds: float = DEFAULT_SILENCE_SECONDS,
        max_record_seconds: float = DEFAULT_MAX_RECORD_SECONDS,
        start_timeout_seconds: float = DEFAULT_START_TIMEOUT_SECONDS,
        calibration_blocks: int = CALIBRATION_BLOCKS,
        min_threshold: float = MIN_THRESHOLD,
    ) -> None:
        self.config: dict[str, Any] = config if config is not None else {}
        self.sample_rate = int(sample_rate)
        self.block_seconds = float(block_seconds)
        self.silence_seconds = float(silence_seconds)
        self.max_record_seconds = float(max_record_seconds)
        self.start_timeout_seconds = float(start_timeout_seconds)
        self.calibration_blocks = max(1, int(calibration_blocks))
        self.min_threshold = float(min_threshold)

        self._lock = threading.Lock()
        self._active_cancel: Optional[threading.Event] = None
        self._recording = False

    # ── налаштування / стан ──────────────────────────────────────────────────
    @property
    def language(self) -> str:
        """Мова розпізнавання з конфігу (типово ``uk-UA``)."""
        language = str(self.config.get("language") or DEFAULT_LANGUAGE).strip()
        return language or DEFAULT_LANGUAGE

    @property
    def is_recording(self) -> bool:
        """Чи триває запис прямо зараз."""
        return self._recording

    def set_config(self, config: dict[str, Any]) -> None:
        """Замінює словник налаштувань."""
        self.config = config if config is not None else {}

    def stop(self) -> None:
        """
        Достроково зупиняє активний запис.

        Безпечно викликати з будь-якого потоку; якщо запису немає — нічого
        не відбувається.
        """
        cancel = self._active_cancel
        if cancel is not None:
            cancel.set()

    # ── запис ────────────────────────────────────────────────────────────────
    def record(self, cancel: Optional[threading.Event] = None) -> Optional[bytes]:
        """
        Записує фразу з мікрофона.

        Повертає ``bytes`` у форматі PCM int16 (16 кГц, моно) або ``None``,
        якщо мовлення не виявлено / запис скасовано. У разі проблем із
        мікрофоном кидає :class:`EarsError` з українським повідомленням.
        """
        if not self._lock.acquire(blocking=False):
            raise EarsError("Сер, я вже слухаю. Зачекайте завершення запису.")
        self._recording = True
        self._active_cancel = cancel if cancel is not None else threading.Event()
        try:
            return self._record_impl(self._active_cancel)
        finally:
            self._recording = False
            self._active_cancel = None
            self._lock.release()

    def _record_impl(self, cancel: threading.Event) -> Optional[bytes]:
        np, sd = _load_audio_libs()
        resolve_default_input(sd)

        block = max(0.02, self.block_seconds)
        frames_per_block = max(1, int(self.sample_rate * block))
        frames: list[Any] = []
        noise: list[float] = []
        started = False
        silent_seconds = 0.0
        threshold = DEFAULT_THRESHOLD
        started_at = time.monotonic()

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=frames_per_block,
            ) as stream:
                while True:
                    if cancel.is_set():
                        return None

                    data, overflowed = stream.read(frames_per_block)
                    if overflowed:
                        logger.debug("Аудіобуфер переповнено — частину звуку втрачено")
                    block_data = np.asarray(data, dtype="float32")
                    frames.append(block_data.copy())
                    if not block_data.size:
                        continue
                    rms = float(np.sqrt(np.mean(np.square(block_data))))

                    # Калібрування рівня шуму на перших блоках.
                    if len(noise) < self.calibration_blocks:
                        noise.append(rms)
                        if len(noise) == self.calibration_blocks:
                            average = sum(noise) / len(noise)
                            threshold = max(self.min_threshold, average * THRESHOLD_MULTIPLIER)
                        continue

                    if rms > threshold:
                        started = True
                        silent_seconds = 0.0
                    elif started:
                        silent_seconds += block
                        if silent_seconds >= self.silence_seconds:
                            break

                    elapsed = time.monotonic() - started_at
                    if not started and elapsed > self.start_timeout_seconds:
                        return None
                    if elapsed > self.max_record_seconds:
                        break
        except EarsError:
            raise
        except Exception as exc:
            logger.exception("Запис із мікрофона не вдався")
            raise EarsError(
                "Сер, мікрофон недоступний. Перевірте, чи його не зайняла інша програма."
            ) from exc

        if not frames or not started:
            return None
        audio = np.concatenate(frames, axis=0)
        audio = np.clip(audio, -1.0, 1.0)
        return (audio * 32767.0).astype("int16").tobytes()

    # ── розпізнавання ────────────────────────────────────────────────────────
    def transcribe(self, raw: bytes, language: Optional[str] = None) -> str:
        """
        Розпізнає записаний PCM int16 (16 кГц, моно) у текст.

        Спочатку пробує основну мову, потім резервну (``uk-UA`` → ``ru-RU``).
        Повертає порожній рядок, якщо мовлення не розпізнано; у разі помилки
        сервісу кидає :class:`EarsError`.

        Backend вибирається ключем ``stt_backend``: ``auto`` (типово),
        ``google`` або ``offline``. У режимі ``offline_mode`` хмарний STT
        не використовується взагалі.
        """
        if not raw:
            return ""
        language_code = (language or self.language or DEFAULT_LANGUAGE).strip()
        backend = str(self.config.get("stt_backend") or "auto").strip().lower()
        offline_mode = bool(self.config.get("offline_mode"))

        if backend == "offline" or (backend == "auto" and offline_mode):
            try:
                from modules.voice.offline import transcribe as offline_transcribe

                return offline_transcribe(
                    raw, self.sample_rate, self.config, language_code
                )
            except Exception as exc:
                if offline_mode or backend == "offline":
                    raise EarsError(
                        "Сер, офлайн-розпізнавання недоступне. "
                        f"Перевір whisper.cpp і модель: {exc}"
                    ) from exc
                logger.warning("Офлайн-STT недоступний (%s); пробую Google.", exc)

        try:
            import speech_recognition as sr  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover — залежність є в requirements.txt
            raise EarsError(
                "Сер, не встановлено пакет SpeechRecognition. "
                "Перевстановіть JARVIS або виконайте pip install -r requirements.txt."
            ) from exc

        audio = sr.AudioData(raw, self.sample_rate, 2)
        recognizer = sr.Recognizer()

        languages = [language_code]
        fallback = LANGUAGE_FALLBACK.get(language_code)
        if fallback and fallback != language_code:
            languages.append(fallback)

        for code in languages:
            try:
                text = recognizer.recognize_google(audio, language=code)
            except sr.UnknownValueError:
                continue
            except sr.RequestError as exc:
                logger.exception("Сервіс Google STT недоступний")
                if backend == "auto" and not offline_mode:
                    try:
                        from modules.voice.offline import (
                            stt_available,
                            transcribe as offline_transcribe,
                        )

                        if stt_available(self.config):
                            return offline_transcribe(
                                raw, self.sample_rate, self.config, language_code
                            )
                    except Exception as offline_exc:
                        logger.warning(
                            "Резервний офлайн-STT теж не спрацював: %s",
                            offline_exc,
                        )
                raise EarsError(
                    "Сер, сервіс розпізнавання мовлення недоступний. "
                    "Перевірте інтернет-з'єднання або налаштуйте офлайн-STT."
                ) from exc
            except Exception as exc:
                logger.exception("Помилка розпізнавання мовлення")
                raise EarsError(f"Сер, сталася помилка розпізнавання: {exc}") from exc
            if text and text.strip():
                return text.strip()
        return ""

    def listen(self, cancel: Optional[threading.Event] = None) -> str:
        """
        Записує фразу й повертає розпізнаний текст (``""``, якщо тиша).

        Кидає :class:`EarsError`, якщо мікрофон недоступний або сервіс
        розпізнавання не відповідає.
        """
        raw = self.record(cancel=cancel)
        if raw is None:
            return ""
        return self.transcribe(raw)


#: Зручний аліас для коду, який очікує назву «STT».
STT = Ears

__all__ = [
    "CALIBRATION_BLOCKS",
    "DEFAULT_LANGUAGE",
    "DEFAULT_SAMPLE_RATE",
    "Ears",
    "EarsError",
    "LANGUAGE_FALLBACK",
    "STT",
    "has_input_device",
    "list_input_devices",
    "resolve_default_input",
]
