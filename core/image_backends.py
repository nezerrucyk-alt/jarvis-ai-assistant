# -*- coding: utf-8 -*-
"""Image backends: local ComfyUI, free Pollinations, OpenAI and fallbacks."""
from __future__ import annotations

import json
import logging
import os
import random
import re
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote, urlparse

from core.image_gen import (
    DEFAULT_KEEP,
    ImageGenError,
    _prune,
    generate_image,
    save_image_bytes,
)

logger = logging.getLogger("Jarvis.ImageBackends")

BACKENDS = ("auto", "comfyui", "openai", "pollinations")
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"
DEFAULT_COMFY_URL = "http://127.0.0.1:8188"
DEFAULT_CHECKPOINT = "sd_xl_turbo_1.0_fp16.safetensors"
_COMFY_LOCK = threading.Lock()
_COMFY_PROCESS: Optional[subprocess.Popen] = None


def _requests():
    import requests  # noqa: PLC0415 — lazy import for tests

    return requests


def parse_size(size: str) -> tuple[int, int]:
    value = str(size or "").strip().lower()
    if value and value != "auto":
        match = re.match(r"^(\d{2,4})x(\d{2,4})$", value)
        if match:
            width = max(256, min(int(match.group(1)), 2048))
            height = max(256, min(int(match.group(2)), 2048))
            return width, height
    return 1024, 1024


def comfyui_workflow(
    prompt: str,
    *,
    checkpoint: str,
    width: int,
    height: int,
    steps: int = 6,
    cfg_value: float = 1.0,
    seed: Optional[int] = None,
    negative: str = "blurry, low quality, watermark, text",
) -> dict[str, Any]:
    seed = random.randint(1, 2**31 - 1) if seed is None else int(seed)
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": max(1, min(int(steps), 50)),
                "cfg": max(0.0, min(float(cfg_value), 20.0)),
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "jarvis-", "images": ["6", 0]},
        },
    }


def comfyui_available(url: str = DEFAULT_COMFY_URL, session=None, timeout: float = 2.0) -> bool:
    client = session or _requests()
    try:
        response = client.get(f"{url.rstrip('/')}/system_stats", timeout=timeout)
        return int(getattr(response, "status_code", 0) or 0) == 200
    except Exception:
        return False


def ensure_comfyui(cfg: dict, wait_seconds: float = 240.0) -> bool:
    """Starts the bundled ComfyUI server if it is not running yet."""
    url = str(cfg.get("comfyui_url") or DEFAULT_COMFY_URL)
    if comfyui_available(url):
        return True
    if not cfg.get("comfyui_autostart", True):
        return False
    directory = Path(str(cfg.get("comfyui_dir") or ""))
    python_candidates = (
        directory / "venv" / "Scripts" / "python.exe",
        directory / "python_embeded" / "python.exe",
    )
    main_candidates = (
        directory / "ComfyUI" / "main.py",
        directory / "main.py",
    )
    python = next((item for item in python_candidates if item.is_file()), None)
    main = next((item for item in main_candidates if item.is_file()), None)
    if python is None or main is None:
        logger.warning("ComfyUI not found at %s", directory)
        return False
    portable = python.name == "python.exe" and "python_embeded" in str(python)
    global _COMFY_PROCESS
    with _COMFY_LOCK:
        if _COMFY_PROCESS is None or _COMFY_PROCESS.poll() is not None:
            port = urlparse(url).port or 8188
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            logger.info("Starting ComfyUI on port %s", port)
            args = [str(python), "-s", str(main), "--lowvram", "--port", str(port)]
            if portable:
                args.insert(3, "--windows-standalone-build")
            _COMFY_PROCESS = subprocess.Popen(
                args,
                cwd=str(directory),
                creationflags=flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if comfyui_available(url, timeout=2.0):
            return True
        time.sleep(2.0)
    return False


def generate_comfyui(
    prompt: str,
    *,
    output_dir: Path,
    url: str = DEFAULT_COMFY_URL,
    checkpoint: str = DEFAULT_CHECKPOINT,
    width: int = 1024,
    height: int = 1024,
    steps: int = 6,
    cfg_value: float = 1.0,
    seed: Optional[int] = None,
    timeout: float = 300.0,
    keep: int = DEFAULT_KEEP,
    session=None,
    poll_interval: float = 1.0,
    comfy_output_dir: Optional[str] = None,
) -> Path:
    client = session or _requests()
    base = url.rstrip("/")
    workflow = comfyui_workflow(
        prompt, checkpoint=checkpoint, width=width, height=height,
        steps=steps, cfg_value=cfg_value, seed=seed,
    )
    try:
        response = client.post(
            f"{base}/prompt",
            json={"prompt": workflow, "client_id": uuid.uuid4().hex},
            timeout=(10, 30),
        )
    except Exception as exc:
        raise ImageGenError(f"ComfyUI недоступний: {exc}") from exc
    if int(getattr(response, "status_code", 0) or 0) != 200:
        detail = str(getattr(response, "text", "") or "")[:300]
        raise ImageGenError(f"ComfyUI відхилив запит: {detail}")
    try:
        prompt_id = str(response.json().get("prompt_id") or "")
    except Exception as exc:
        raise ImageGenError("ComfyUI повернув неочікувану відповідь.") from exc
    if not prompt_id:
        raise ImageGenError("ComfyUI не повернув prompt_id.")

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            history = client.get(f"{base}/history/{prompt_id}", timeout=(10, 30))
            data = history.json() if int(getattr(history, "status_code", 0) or 0) == 200 else {}
        except Exception as exc:
            logger.warning("ComfyUI history failed: %s", exc)
            data = {}
        entry = data.get(prompt_id) if isinstance(data, dict) else None
        if entry:
            for node in (entry.get("outputs") or {}).values():
                images = node.get("images") or []
                if not images:
                    continue
                image = images[0]
                params = {
                    "filename": image.get("filename") or "",
                    "subfolder": image.get("subfolder") or "",
                    "type": image.get("type") or "output",
                }
                try:
                    download = client.get(f"{base}/view", params=params, timeout=(10, 90))
                except Exception as exc:
                    raise ImageGenError(f"Не вдалося забрати зображення з ComfyUI: {exc}") from exc
                if int(getattr(download, "status_code", 0) or 0) != 200:
                    raise ImageGenError("ComfyUI не віддав зображення.")
                path = save_image_bytes(download.content, output_dir, keep)
                if comfy_output_dir:
                    _prune(Path(comfy_output_dir), keep)
                return path
        time.sleep(max(0.0, poll_interval))
    raise ImageGenError(f"ComfyUI не завершив генерацію за {int(timeout)} с.")


def generate_pollinations(
    prompt: str,
    *,
    output_dir: Path,
    width: int = 1024,
    height: int = 1024,
    model: str = "flux",
    timeout: float = 180.0,
    keep: int = DEFAULT_KEEP,
    seed: Optional[int] = None,
    session=None,
) -> Path:
    client = session or _requests()
    params = {
        "width": width,
        "height": height,
        "model": model or "flux",
        "nologo": "true",
    }
    seed = random.randint(1, 2**31 - 1) if seed is None else int(seed)
    params["seed"] = seed
    url = POLLINATIONS_URL + quote(prompt, safe="")
    try:
        response = client.get(url, params=params, timeout=(10, timeout))
    except Exception as exc:
        raise ImageGenError(f"Безкоштовна хмара недоступна: {exc}") from exc
    status = int(getattr(response, "status_code", 0) or 0)
    if status != 200:
        raise ImageGenError(f"Безкоштовна хмара повернула HTTP {status}.")
    return save_image_bytes(response.content, output_dir, keep)


def backend_chain(cfg: dict) -> list[str]:
    backend = str(cfg.get("image_backend") or "auto").strip().lower()
    if backend in ("comfyui", "openai", "pollinations"):
        return [backend]
    chain = ["comfyui"]
    if str(cfg.get("openai_api_key") or "").strip():
        chain.append("openai")
    if cfg.get("image_allow_public_fallback"):
        chain.append("pollinations")
    return chain


def generate_with_backend(
    prompt: str,
    *,
    cfg: dict,
    output_dir: Path,
    size: str = "1024x1024",
    quality: str = "auto",
    keep: int = DEFAULT_KEEP,
    session=None,
) -> tuple[Path, str]:
    width, height = parse_size(size)
    chain = backend_chain(cfg)
    if not chain:
        raise ImageGenError(
            "Немає доступного бекенду. Увімкни ComfyUI, додай OpenAI ключ "
            "або дозволь безкоштовну хмару в налаштуваннях."
        )
    errors: list[str] = []
    for name in chain:
        try:
            if name == "comfyui":
                url = str(cfg.get("comfyui_url") or DEFAULT_COMFY_URL)
                if cfg.get("comfyui_autostart", True):
                    ensure_comfyui(cfg)
                path = generate_comfyui(
                    prompt,
                    output_dir=output_dir,
                    url=url,
                    checkpoint=str(
                        cfg.get("comfyui_checkpoint") or DEFAULT_CHECKPOINT
                    ),
                    width=width,
                    height=height,
                    steps=int(cfg.get("comfyui_steps") or 6),
                    cfg_value=float(cfg.get("comfyui_cfg") or 1.0),
                    keep=keep,
                    session=session,
                    comfy_output_dir=cfg.get("comfyui_output_dir") or None,
                )
                return path, "ComfyUI"
            if name == "openai":
                path = generate_image(
                    prompt,
                    api_key=str(cfg.get("openai_api_key") or ""),
                    output_dir=output_dir,
                    model=str(cfg.get("image_model") or "gpt-image-1"),
                    size=size if size in ("1024x1024", "1024x1536", "1536x1024", "auto") else "1024x1024",
                    quality=quality,
                    keep=keep,
                )
                return path, "OpenAI"
            if name == "pollinations":
                path = generate_pollinations(
                    prompt,
                    output_dir=output_dir,
                    width=width,
                    height=height,
                    model=str(cfg.get("pollinations_model") or "flux"),
                    keep=keep,
                    session=session,
                )
                return path, "Pollinations"
        except Exception as exc:  # noqa: BLE001 — try the next backend
            logger.warning("Image backend %s failed: %s", name, exc)
            errors.append(f"{name}: {exc}")
    raise ImageGenError(
        "Не вдалося згенерувати зображення. " + " | ".join(errors[-3:])
    )


__all__ = [
    "BACKENDS",
    "DEFAULT_CHECKPOINT",
    "DEFAULT_COMFY_URL",
    "POLLINATIONS_URL",
    "backend_chain",
    "comfyui_available",
    "comfyui_workflow",
    "ensure_comfyui",
    "generate_comfyui",
    "generate_pollinations",
    "generate_with_backend",
    "parse_size",
]
