# -*- coding: utf-8 -*-
"""Wake-word detection for JARVIS.

The preferred backend is `openWakeWord <https://github.com/dscripka/openWakeWord>`_:
it runs a small ONNX model locally, so «Hey Jarvis» works without internet.
If openWakeWord is not installed, the listener falls back to the existing
VAD + Google STT pipeline and matches the wake phrase in the transcript.
The fallback needs internet and only wakes the assistant; the command is
recorded afterwards.

Audio and ML libraries are imported lazily, so importing this module is cheap
and safe in tests.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

logger = logging.getLogger("Jarvis.Wake")

SAMPLE_RATE = 16000
CHUNK_SECONDS = 0.08
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_SECONDS)
DEFAULT_MODEL = "hey_jarvis"
DEFAULT_THRESHOLD = 0.5
DEFAULT_COOLDOWN = 2.0

#: Phrases accepted by the STT fallback. The list intentionally includes
#: common Ukrainian/Russian transliterations and mis-hearings.
WAKE_PHRASES: tuple[str, ...] = (
    "hey jarvis",
    "hi jarvis",
    "ok jarvis",
    "okay jarvis",
    "jarvis",
    "джарвіс",
    "джарвис",
    "жарвіс",
    "жарвис",
    "гарвіс",
    "гарвис",
    "джарвісе",
    "джарвисе",
)


def normalize_wake_text(text: str) -> str:
    """Lowercase, strip punctuation and collapse whitespace."""
    value = str(text or "").lower().replace("’", "'").replace("`", "'")
    value = re.sub(r"[^\w\s']", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def is_wake_phrase(
    text: str,
    phrases: Iterable[str] = WAKE_PHRASES,
    head_words: int = 5,
) -> bool:
    """Return True when a wake phrase appears near the start of ``text``.

    Looking only at the first few words avoids waking on a sentence that
    merely mentions Jarvis later (for example a review or a quoted reply).
    """
    value = normalize_wake_text(text)
    if not value:
        return False
    head = " ".join(value.split()[:head_words])
    return any(
        normalize_wake_text(phrase) in head
        for phrase in phrases
        if str(phrase).strip()
    )


class WakeGate:
    """Small cooldown gate that is easy to test with a fake clock."""

    def __init__(
        self,
        cooldown: float = DEFAULT_COOLDOWN,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.cooldown = max(0.0, float(cooldown))
        self._clock = clock
        self._last = 0.0
        self._lock = threading.Lock()

    def allow(self) -> bool:
        now = self._clock()
        with self._lock:
            if now - self._last < self.cooldown:
                return False
            self._last = now
            return True

    def reset(self) -> None:
        with self._lock:
            self._last = 0.0


class WakeWordListener:
    """Background wake-word listener with a graceful STT fallback."""

    def __init__(
        self,
        cfg: dict,
        on_wake: Callable[[], None],
        should_pause: Optional[Callable[[], bool]] = None,
        log: Optional[Callable[[str], None]] = None,
        model_dir: Optional[Path] = None,
    ) -> None:
        self.cfg = cfg
        self.on_wake = on_wake
        self.should_pause = should_pause or (lambda: False)
        self.log = log or (lambda message: logger.info(message))
        self.model_dir = Path(model_dir) if model_dir else None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._gate = WakeGate(
            float(cfg.get("wake_word_cooldown", DEFAULT_COOLDOWN))
        )
        self.backend = self.detect_backend()

    # ── lifecycle ────────────────────────────────────────────────────────────
    @staticmethod
    def detect_backend() -> str:
        """Return ``openwakeword`` when the offline backend is usable."""
        try:
            import openwakeword  # noqa: F401
            import onnxruntime  # noqa: F401
        except Exception:
            return "stt"
        return "openwakeword"

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="JarvisWakeWord",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is None or thread is threading.current_thread():
            return
        thread.join(timeout=2.5)
        self._thread = None

    # ── main loop ────────────────────────────────────────────────────────────
    def _run(self) -> None:
        backend = self.detect_backend()
        self.backend = backend
        if backend == "openwakeword":
            try:
                self._run_openwakeword()
                return
            except Exception as exc:
                logger.exception("openWakeWord failed; falling back to STT")
                self.log(
                    "openWakeWord не запустився "
                    f"({exc}). Перемикаюся на резервний STT."
                )
        self._run_stt()

    def _run_openwakeword(self) -> None:
        import numpy as np
        import sounddevice as sd

        model = self._load_openwakeword_model()
        threshold = max(
            0.05,
            min(0.99, float(self.cfg.get("wake_word_threshold", DEFAULT_THRESHOLD))),
        )
        self.log("Wake word: openWakeWord, модель «Hey Jarvis». Скажи «Hey Jarvis».")

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=CHUNK_SAMPLES,
        ) as stream:
            while not self._stop.is_set():
                data, _ = stream.read(CHUNK_SAMPLES)
                if self.should_pause():
                    continue
                scores = model.predict(data[:, 0])
                score = max((float(value) for value in scores.values()), default=0.0)
                if score < threshold:
                    continue
                if not self._gate.allow():
                    continue
                self._trigger()
                try:
                    model.reset()
                except Exception:
                    logger.debug("openWakeWord reset failed", exc_info=True)
                # Let the GUI set ``busy`` before the next chunk is processed.
                time.sleep(0.35)
                while not self._stop.is_set() and self.should_pause():
                    time.sleep(0.1)

    def _load_openwakeword_model(self):
        from openwakeword.model import Model
        from openwakeword.utils import download_models

        model_name = str(self.cfg.get("wake_word_model") or DEFAULT_MODEL)
        model_dir = self.model_dir
        if model_dir is None:
            model_dir = Path.home() / ".cache" / "jarvis" / "wakeword"
        model_dir.mkdir(parents=True, exist_ok=True)

        model_path = self._find_model(model_dir, model_name, ".onnx")
        melspec = model_dir / "melspectrogram.onnx"
        embedding = model_dir / "embedding_model.onnx"
        if model_path is None or not melspec.exists() or not embedding.exists():
            self.log("Завантажую модель wake word (один раз, ~7 МБ)…")
            download_models([model_name], target_directory=str(model_dir))
            model_path = self._find_model(model_dir, model_name, ".onnx")
        if model_path is None:
            raise RuntimeError(f"модель {model_name} не знайдена після завантаження")
        if not melspec.exists() or not embedding.exists():
            raise RuntimeError("службові моделі openWakeWord не завантажилися")

        return Model(
            wakeword_models=[str(model_path)],
            inference_framework="onnx",
            melspec_model_path=str(melspec),
            embedding_model_path=str(embedding),
        )

    @staticmethod
    def _find_model(directory: Path, name: str, suffix: str) -> Optional[Path]:
        matches = sorted(directory.glob(f"{name}*{suffix}"))
        return matches[0] if matches else None

    def _run_stt(self) -> None:
        from modules.voice.stt import Ears, EarsError

        ears = Ears(self.cfg)
        self.log(
            "Wake word: резервний STT. Скажи «Hey Jarvis» "
            "(потрібен інтернет)."
        )
        language = str(self.cfg.get("language") or "uk-UA")
        failures = 0

        while not self._stop.is_set():
            if self.should_pause():
                time.sleep(0.2)
                continue
            try:
                raw = ears.record(self._stop)
                if not raw or self._stop.is_set():
                    continue
                text = ears.transcribe(raw, language)
                failures = 0
            except EarsError as exc:
                failures += 1
                if failures in (1, 5):
                    self.log(f"Wake word STT: {exc}")
                time.sleep(min(5.0, 1.5 * failures))
                continue
            except Exception as exc:
                logger.exception("Wake word STT failed")
                self.log(f"Wake word STT: {exc}")
                time.sleep(3.0)
                continue

            if text and is_wake_phrase(text) and self._gate.allow():
                self._trigger()
                time.sleep(0.35)
                while not self._stop.is_set() and self.should_pause():
                    time.sleep(0.1)

    def _trigger(self) -> None:
        self.log("Почув «Hey Jarvis» — слухаю команду.")
        try:
            self.on_wake()
        except Exception:
            logger.exception("Wake-word callback failed")
