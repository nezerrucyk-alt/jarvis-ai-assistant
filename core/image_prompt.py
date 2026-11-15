# -*- coding: utf-8 -*-
"""Turn a user's idea into a production prompt for gpt-image-1.

The chat model acts as a prompt engineer: it expands the idea into one
detailed English image prompt. If the model is unavailable or returns
something unusable, the original text is used unchanged.
"""
from __future__ import annotations

import logging
import re
from typing import Callable, Optional

logger = logging.getLogger("Jarvis.ImagePrompt")

MAX_PROMPT_CHARS = 1400

SYSTEM_PROMPT = (
    "You are a prompt engineer for OpenAI gpt-image-1. Rewrite the user's idea "
    "into ONE detailed image prompt in English. Include: subject and action, "
    "setting, art style, composition and camera, lighting, color palette and "
    "mood. Keep the user's intent exactly; do not add text, captions, logos, "
    "watermarks or UI. Avoid brand names. Output only the final prompt as one "
    "plain paragraph, no preamble, no quotes, no markdown, no explanations. "
    "Aim for 350-900 characters."
)

_PREFIX_RE = re.compile(
    r"^(?:prompt|image prompt|final prompt|osь prompt|ось промпт|промпт)\s*[:\-–]\s*",
    re.IGNORECASE,
)
_CHATTER_RE = re.compile(
    r"^(?:sure|here is|here's|ось|звичайно|гаразд)[^\n]{0,80}:\s*",
    re.IGNORECASE,
)


def clean_prompt(text: str) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    value = re.sub(r"```[a-zA-Z0-9_-]*\s*|\s*```", " ", value).strip()
    value = value.strip("\"'“”‘’ ")
    value = _CHATTER_RE.sub("", value).strip()
    value = _PREFIX_RE.sub("", value).strip()
    value = value.strip("\"'“”‘’ ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def enhance_prompt(
    prompt: str,
    complete: Callable[..., str],
    *,
    max_chars: int = MAX_PROMPT_CHARS,
    timeout: Optional[float] = None,
) -> str:
    """Returns a refined prompt or the original text when refinement fails."""
    original = str(prompt or "").strip()
    if not original:
        return original
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"User idea:\n{original}"},
    ]
    kwargs: dict = {"max_tokens": 500, "temperature": 0.7}
    if timeout is not None:
        kwargs["timeout"] = timeout
    try:
        raw = complete(messages, **kwargs)
    except Exception as exc:  # noqa: BLE001 — enhancement is best-effort
        logger.warning("Prompt enhancement failed: %s", exc)
        return original
    refined = clean_prompt(raw)
    if len(refined) < 20:
        return original
    if len(refined) > max_chars:
        cut = refined[:max_chars]
        refined = cut.rsplit(" ", 1)[0].strip() or cut
    return refined


__all__ = ["MAX_PROMPT_CHARS", "SYSTEM_PROMPT", "clean_prompt", "enhance_prompt"]
