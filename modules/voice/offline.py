# -*- coding: utf-8 -*-
"""Offline speech backends for JARVIS.

JARVIS can use local binaries instead of cloud services:

* **STT** — ``whisper.cpp`` (``whisper-cli``) with a ``ggml-*.bin`` model;
* **TTS** — `Piper <https://github.com/rhasspy/piper>`_ with an ``.onnx``
  voice model.

Nothing is downloaded automatically: the user points the config at existing
binaries and models.  This keeps the application honest about disk usage and
avoids surprise network traffic.  When a backend is missing, callers fall back
to Google STT / Edge TTS unless ``offline_mode`` is enabled, in which case they
raise a clear error instead of silently going online.

Only the standard library is used here, so importing this module is cheap and
safe in tests.
"""
from __future__ import annotations

import logging
import os
import shlex
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("Jarvis.OfflineVoice")

DEFAULT_STT_TIMEOUT = 120.0
DEFAULT_TTS_TIMEOUT = 90.0
MAX_TEXT = 2000

_LANG_MAP = {
    "uk-ua": "uk",
    "uk": "uk",
    "ru-ru": "ru",
    "ru": "ru",
    "en-us": "en",
    "en-gb": "en",
    "en": "en",
    "de-de": "de",
    "de": "de",
    "fr-fr": "fr",
    "fr": "fr",
    "es-es": "es",
    "es": "es",
    "it-it": "it",
    "it": "it",
    "pl-pl": "pl",
    "pl": "pl",
}


class OfflineVoiceError(RuntimeError):
    """Offline STT/TTS is not configured or failed."""


def _clean_path(value: Any) -> Optional[Path]:
    text = str(value or "").strip().strip('"')
    if not text:
        return None
    path = Path(os.path.expandvars(os.path.expanduser(text)))
    return path


def _find_binary(names: list[str], explicit: Any = "") -> Optional[str]:
    explicit_path = _clean_path(explicit)
    if explicit_path and explicit_path.is_file():
        return str(explicit_path)
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _stt_binary(cfg: dict[str, Any]) -> Optional[str]:
    return _find_binary(
        ["whisper-cli", "whisper-cli.exe", "whisper.cpp", "main.exe"],
        cfg.get("offline_stt_binary"),
    )


def _tts_binary(cfg: dict[str, Any]) -> Optional[str]:
    return _find_binary(
        ["piper", "piper.exe"],
        cfg.get("offline_tts_binary"),
    )


def _stt_model(cfg: dict[str, Any]) -> Optional[Path]:
    path = _clean_path(cfg.get("offline_whisper_model"))
    return path if path and path.is_file() else None


def _tts_model(cfg: dict[str, Any]) -> Optional[Path]:
    path = _clean_path(cfg.get("offline_piper_model"))
    return path if path and path.is_file() else None


def language_code(language: str) -> str:
    value = str(language or "uk-UA").strip().lower()
    return _LANG_MAP.get(value, value.split("-")[0] or "uk")


def stt_available(cfg: dict[str, Any]) -> bool:
    return bool(_stt_binary(cfg) and _stt_model(cfg))


def tts_available(cfg: dict[str, Any]) -> bool:
    return bool(_tts_binary(cfg) and _tts_model(cfg))


def capabilities(cfg: dict[str, Any]) -> dict[str, Any]:
    """Return a small status dict for the settings UI and diagnostics."""
    stt_bin = _stt_binary(cfg)
    tts_bin = _tts_binary(cfg)
    whisper_model = _stt_model(cfg)
    piper_model = _tts_model(cfg)
    return {
        "stt_available": bool(stt_bin and whisper_model),
        "tts_available": bool(tts_bin and piper_model),
        "stt_binary": stt_bin or "",
        "tts_binary": tts_bin or "",
        "whisper_model": str(whisper_model or ""),
        "piper_model": str(piper_model or ""),
    }


def _write_wav(raw: bytes, sample_rate: int, path: Path) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(int(sample_rate))
        handle.writeframes(raw)


def _run(command: list[str], *, timeout: float, stdin: Optional[str] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        input=stdin.encode("utf-8") if stdin is not None else None,
        capture_output=True,
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def transcribe(
    raw_pcm: bytes,
    sample_rate: int,
    cfg: dict[str, Any],
    language: str = "uk-UA",
) -> str:
    """Transcribe 16-bit mono PCM with whisper.cpp.

    Raises :class:`OfflineVoiceError` with an actionable message when the
    binary or model is missing, the process fails or the output is empty.
    """
    if not raw_pcm:
        return ""
    binary = _stt_binary(cfg)
    model = _stt_model(cfg)
    if not binary or not model:
        raise OfflineVoiceError(
            "Локальний STT не налаштований. Вкажи offline_stt_binary "
            "(whisper-cli) і offline_whisper_model (ggml-*.bin) у налаштуваннях."
        )

    language_code_value = language_code(language)
    with tempfile.TemporaryDirectory(prefix="jarvis_whisper_") as tmp:
        wav_path = Path(tmp) / "input.wav"
        output_base = Path(tmp) / "output"
        _write_wav(raw_pcm, sample_rate, wav_path)

        template = str(cfg.get("offline_stt_command") or "").strip()
        if template:
            try:
                command = [
                    part.strip('"').format(
                        wav=str(wav_path),
                        model=str(model),
                        lang=language_code_value,
                        output=str(output_base),
                    )
                    for part in shlex.split(template, posix=False)
                ]
            except (KeyError, ValueError) as exc:
                raise OfflineVoiceError(
                    f"Помилка в offline_stt_command: {exc}"
                ) from exc
            command[0] = command[0].strip('"')
        else:
            command = [
                binary,
                "-m", str(model),
                "-f", str(wav_path),
                "-l", language_code_value,
                "-nt",
                "-otxt",
                "-of", str(output_base),
            ]

        try:
            result = _run(command, timeout=DEFAULT_STT_TIMEOUT)
        except subprocess.TimeoutExpired as exc:
            raise OfflineVoiceError("whisper.cpp не встиг розпізнати фразу.") from exc
        except OSError as exc:
            raise OfflineVoiceError(f"Не вдалося запустити whisper.cpp: {exc}") from exc

        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", "replace").strip()[:300]
            raise OfflineVoiceError(
                f"whisper.cpp завершився з кодом {result.returncode}: {detail}"
            )

        text_path = output_base.with_suffix(".txt")
        if text_path.is_file():
            text = text_path.read_text(encoding="utf-8", errors="replace").strip()
        else:
            text = result.stdout.decode("utf-8", "replace").strip()
        text = " ".join(text.split())
        if not text:
            raise OfflineVoiceError("whisper.cpp не розпізнав мовлення.")
        return text


def synthesize(text: str, cfg: dict[str, Any], output_path: Path) -> Path:
    """Synthesize ``text`` to ``output_path`` with Piper."""
    text = " ".join(str(text or "").split())[:MAX_TEXT]
    if not text:
        raise OfflineVoiceError("Порожній текст для локального TTS.")
    binary = _tts_binary(cfg)
    model = _tts_model(cfg)
    if not binary or not model:
        raise OfflineVoiceError(
            "Локальний TTS не налаштований. Вкажи offline_tts_binary (piper) "
            "і offline_piper_model (.onnx) у налаштуваннях."
        )

    output_path = Path(output_path)
    template = str(cfg.get("offline_tts_command") or "").strip()
    if template:
        try:
            command = [
                part.strip('"').format(
                    model=str(model),
                    output=str(output_path),
                    text=text,
                )
                for part in shlex.split(template, posix=False)
            ]
        except (KeyError, ValueError) as exc:
            raise OfflineVoiceError(
                f"Помилка в offline_tts_command: {exc}"
            ) from exc
        command[0] = command[0].strip('"')
        stdin = None
    else:
        command = [
            binary,
            "--model", str(model),
            "--output_file", str(output_path),
        ]
        stdin = text

    try:
        result = _run(command, timeout=DEFAULT_TTS_TIMEOUT, stdin=stdin)
    except subprocess.TimeoutExpired as exc:
        raise OfflineVoiceError("Piper не встиг синтезувати мовлення.") from exc
    except OSError as exc:
        raise OfflineVoiceError(f"Не вдалося запустити Piper: {exc}") from exc

    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()[:300]
        raise OfflineVoiceError(
            f"Piper завершився з кодом {result.returncode}: {detail}"
        )
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise OfflineVoiceError("Piper не створив аудіофайл.")
    return output_path


__all__ = [
    "DEFAULT_STT_TIMEOUT",
    "DEFAULT_TTS_TIMEOUT",
    "OfflineVoiceError",
    "capabilities",
    "language_code",
    "stt_available",
    "synthesize",
    "transcribe",
    "tts_available",
]
