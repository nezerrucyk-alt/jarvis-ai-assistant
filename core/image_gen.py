# -*- coding: utf-8 -*-
"""OpenAI Images integration for J.A.R.V.I.S.

Text-to-image generation with ``gpt-image-1``. The module is independent of
Tkinter: it validates the prompt, calls the API, decodes the result, verifies
the bytes with Pillow and writes the image atomically to the output folder.
"""
from __future__ import annotations

import base64
import io
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("Jarvis.ImageGen")

API_URL = "https://api.openai.com/v1/images/generations"
DEFAULT_MODEL = "gpt-image-1"
MODELS: tuple[str, ...] = ("gpt-image-1", "gpt-image-1-mini")
SIZES: tuple[str, ...] = ("1024x1024", "1024x1536", "1536x1024", "auto")
QUALITIES: tuple[str, ...] = ("auto", "low", "medium", "high")
MAX_PROMPT_CHARS = 4000
DEFAULT_TIMEOUT = 300.0
DEFAULT_KEEP = 200


class ImageGenError(Exception):
    """User-facing image generation error."""


def _normalize(value: str, allowed: tuple[str, ...], default: str) -> str:
    candidate = str(value or "").strip().lower()
    return candidate if candidate in allowed else default


def _error_detail(response: Any) -> str:
    try:
        data = response.json()
    except Exception:
        return str(getattr(response, "text", "") or "")[:300]
    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict):
        message = str(error.get("message") or "").strip()
        code = str(error.get("code") or error.get("type") or "").strip()
        if message:
            return message + (f" ({code})" if code else "")
    return str(data)[:300]


_FALLBACK_HINTS = (
    "model", "quality", "output_format", "size", "unsupported",
    "not supported", "invalid value", "unknown parameter",
)


def _supports_fallback(detail: str) -> bool:
    text = str(detail or "").lower()
    return any(hint in text for hint in _FALLBACK_HINTS)


def _prune(folder: Path, keep: int) -> None:
    try:
        keep = int(keep)
    except (TypeError, ValueError):
        keep = DEFAULT_KEEP
    if keep <= 0:
        return
    files: list[Path] = []
    for pattern in ("jarvis-*.png", "jarvis-*.jpg", "jarvis-*.webp"):
        files.extend(folder.glob(pattern))
    files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    for old in files[keep:]:
        try:
            old.unlink()
        except OSError:
            pass


def save_image_bytes(raw: bytes, output_dir: Path, keep: int = DEFAULT_KEEP) -> Path:
    """Validate image bytes, save atomically and prune old JARVIS images."""
    try:
        fmt, _width, _height = _read_image(raw)
    except Exception as exc:
        raise ImageGenError("Отриманий файл не є зображенням.") from exc
    extension = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}.get(fmt, ".png")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = output_dir / f"jarvis-{stamp}-{uuid.uuid4().hex[:6]}{extension}"
    temp = target.with_suffix(target.suffix + ".tmp")
    try:
        temp.write_bytes(raw)
        temp.replace(target)
        _prune(output_dir, keep)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise ImageGenError(f"Не вдалося зберегти зображення: {exc}") from exc
    return target


def _read_image(raw: bytes) -> tuple[str, int, int]:
    """Validate image bytes and return (format, width, height)."""
    from PIL import Image

    with Image.open(io.BytesIO(raw)) as image:
        image.verify()
    with Image.open(io.BytesIO(raw)) as image:
        return (image.format or "PNG").upper(), image.width, image.height


def generate_image(
    prompt: str,
    *,
    api_key: str,
    output_dir: Path,
    model: str = DEFAULT_MODEL,
    size: str = "1024x1024",
    quality: str = "auto",
    timeout: float = DEFAULT_TIMEOUT,
    keep: int = DEFAULT_KEEP,
    post: Optional[Callable[..., Any]] = None,
    get: Optional[Callable[..., Any]] = None,
) -> Path:
    """Generate one image and save it under *output_dir*.

    Raises :class:`ImageGenError` with a message that can be shown to the user.
    """
    prompt = str(prompt or "").strip()
    if not prompt:
        raise ImageGenError("Опис зображення порожній — напиши, що саме намалювати.")
    if len(prompt) > MAX_PROMPT_CHARS:
        raise ImageGenError(
            f"Опис занадто довгий ({len(prompt)} символів). "
            f"Максимум {MAX_PROMPT_CHARS} — склади коротший промпт."
        )

    api_key = str(api_key or "").strip()
    if not api_key:
        raise ImageGenError(
            "Для генерації зображень потрібен OpenAI API ключ. "
            "Додай його в Налаштуваннях → OPENAI API · GPT / CODEX."
        )

    model = str(model or DEFAULT_MODEL).strip()
    if model not in MODELS:
        model = DEFAULT_MODEL
    size = _normalize(size, SIZES, "1024x1024")
    quality = _normalize(quality, QUALITIES, "auto")

    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "n": 1,
        "output_format": "png",
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    poster = post
    if poster is None:
        import requests

        poster = requests.post

    def send(body: dict[str, Any]):
        return poster(API_URL, headers=headers, json=body, timeout=(10, timeout))

    response = None
    for attempt in range(2):
        try:
            response = send(payload)
        except Exception as exc:
            if attempt == 0:
                time.sleep(1.0)
                continue
            raise ImageGenError(f"Не вдалося зв'язатися з OpenAI Images: {exc}") from exc
        status = int(getattr(response, "status_code", 0) or 0)
        if status < 400:
            break
        detail = _error_detail(response)
        if status == 429 and attempt == 0:
            retry_after = (getattr(response, "headers", None) or {}).get("Retry-After")
            try:
                delay = min(max(float(retry_after), 0.5), 5.0)
            except (TypeError, ValueError):
                delay = 2.0
            time.sleep(delay)
            continue
        if status >= 500 and attempt == 0:
            time.sleep(1.5)
            continue
        if status == 400 and attempt == 0 and _supports_fallback(detail):
            payload = {
                "model": DEFAULT_MODEL,
                "prompt": prompt,
                "size": "1024x1024" if size == "auto" else size,
                "n": 1,
            }
            continue
        break

    status = int(getattr(response, "status_code", 0) or 0) if response is not None else 0
    if status >= 400:
        detail = _error_detail(response)
        if status == 401:
            raise ImageGenError(
                "OpenAI не прийняв API ключ (401). Перевір ключ у налаштуваннях."
            )
        if status == 429:
            raise ImageGenError(
                "OpenAI обмежив частоту або квоту (429). Спробуй пізніше."
            )
        if status == 400:
            raise ImageGenError(f"OpenAI відхилив запит (400): {detail}")
        raise ImageGenError(f"OpenAI Images повернув помилку {status}: {detail}")

    try:
        data = response.json()
        item = (data.get("data") or [])[0]
    except Exception as exc:
        raise ImageGenError("OpenAI Images повернув неочікувану відповідь.") from exc

    if item.get("b64_json"):
        try:
            raw = base64.b64decode(str(item["b64_json"]))
        except Exception as exc:
            raise ImageGenError("Не вдалося декодувати зображення від OpenAI.") from exc
    elif item.get("url"):
        getter = get
        if getter is None:
            import requests

            getter = requests.get
        try:
            download = getter(str(item["url"]), timeout=(10, 60))
            download.raise_for_status()
            raw = download.content
        except Exception as exc:
            raise ImageGenError(f"Не вдалося завантажити зображення: {exc}") from exc
    else:
        raise ImageGenError("OpenAI не повернув ні base64, ні URL зображення.")

    path = save_image_bytes(raw, output_dir, keep)
    logger.info("Generated OpenAI image %s (%s)", path, model)
    return path
