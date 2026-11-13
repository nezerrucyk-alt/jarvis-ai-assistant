# -*- coding: utf-8 -*-
"""Local long-term memory index for JARVIS.

The index uses a deterministic hashing embedder: words, word bigrams and
character trigrams are hashed into a fixed-size vector with signed buckets.
This is not a neural embedding model, but it gives useful lexical-semantic
retrieval (inflections, typos and shared roots) without downloading a model,
without network access and without extra dependencies.

Records are plain dicts stored in ``memory.json``.  :func:`ensure_embeddings`
adds an ``embedding`` field to old records, so existing user memories keep
working after an upgrade.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Iterable, Optional

EMBEDDING_VERSION = "hash-v1"
DEFAULT_DIMENSIONS = 384
DEFAULT_LIMIT = 8
MIN_SCORE = 0.03

_WORD_RE = re.compile(r"[0-9a-z\u00c0-\u024f\u0400-\u04ff']+", re.IGNORECASE)
_SPACE_RE = re.compile(r"\s+")


def _stable_hash(value: str) -> int:
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(str(text or "").lower())


def _features(text: str) -> Iterable[tuple[str, float]]:
    words = _words(text)
    for word in words:
        yield f"w:{word}", 1.0
        padded = f"^{word}$"
        for size in (3, 4):
            for index in range(max(0, len(padded) - size + 1)):
                yield f"c:{padded[index:index + size]}", 0.28
    for left, right in zip(words, words[1:]):
        yield f"b:{left} {right}", 0.55


def embed_text(text: str, dimensions: int = DEFAULT_DIMENSIONS) -> list[float]:
    """Return a normalized hashing embedding for ``text``.

    The result is deterministic across processes and Python versions because
    it uses BLAKE2b instead of the randomized built-in ``hash``.
    """
    dimensions = max(16, int(dimensions))
    vector = [0.0] * dimensions
    for feature, weight in _features(text):
        value = _stable_hash(feature)
        index = value % dimensions
        sign = 1.0 if (value >> 63) & 1 else -1.0
        vector[index] += sign * weight
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 1e-12:
        return vector
    return [value / norm for value in vector]


def cosine(left: Iterable[float], right: Iterable[float]) -> float:
    """Cosine similarity for two embedding vectors."""
    a = list(left)
    b = list(right)
    if not a or not b:
        return 0.0
    size = min(len(a), len(b))
    if size == 0:
        return 0.0
    dot = sum(a[index] * b[index] for index in range(size))
    norm_a = math.sqrt(sum(value * value for value in a[:size]))
    norm_b = math.sqrt(sum(value * value for value in b[:size]))
    if norm_a <= 1e-12 or norm_b <= 1e-12:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


def record_text(record: dict[str, Any]) -> str:
    return _SPACE_RE.sub(" ", str(record.get("text") or "")).strip()


def ensure_embedding(
    record: dict[str, Any],
    dimensions: int = DEFAULT_DIMENSIONS,
) -> dict[str, Any]:
    """Attach a fresh embedding to ``record`` when it is missing or stale."""
    text = record_text(record)
    embedding = record.get("embedding")
    valid = (
        record.get("embedding_version") == EMBEDDING_VERSION
        and isinstance(embedding, list)
        and len(embedding) == dimensions
        and text
    )
    if not valid:
        record["embedding"] = embed_text(text, dimensions) if text else []
        record["embedding_version"] = EMBEDDING_VERSION
    return record


def ensure_embeddings(
    records: Iterable[dict[str, Any]],
    dimensions: int = DEFAULT_DIMENSIONS,
) -> list[dict[str, Any]]:
    """Return the same records with embeddings attached in place."""
    result = list(records)
    for record in result:
        ensure_embedding(record, dimensions)
    return result


def rank_memories(
    records: Iterable[dict[str, Any]],
    query: str,
    *,
    limit: int = DEFAULT_LIMIT,
    min_score: float = MIN_SCORE,
    dimensions: int = DEFAULT_DIMENSIONS,
) -> list[dict[str, Any]]:
    """Rank memories by similarity to ``query``.

    When the query is empty, the most recent records are returned.  Records
    below ``min_score`` are treated as weak matches: if none pass the
    threshold, the closest positively-scored records are returned instead of
    injecting nothing into the prompt.
    """
    items = [record for record in records if record_text(record)]
    if not items:
        return []
    limit = max(1, int(limit))
    query = _SPACE_RE.sub(" ", str(query or "")).strip()
    if not query:
        return items[-limit:]

    query_vector = embed_text(query, dimensions)
    scored: list[tuple[float, int, dict[str, Any]]] = []
    for position, record in enumerate(items):
        ensure_embedding(record, dimensions)
        score = cosine(query_vector, record.get("embedding") or [])
        scored.append((score, position, record))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)

    relevant = [record for score, _, record in scored if score >= min_score][:limit]
    if relevant:
        return relevant
    return [record for score, _, record in scored if score > 0][:limit]


def memory_prompt(
    records: Iterable[dict[str, Any]],
    query: str,
    *,
    limit: int = DEFAULT_LIMIT,
    max_chars: int = 400,
    dimensions: int = DEFAULT_DIMENSIONS,
) -> str:
    """Build a prompt block with the most relevant memories."""
    selected = rank_memories(
        records,
        query,
        limit=limit,
        dimensions=dimensions,
    )
    lines = []
    for record in selected:
        text = record_text(record)[:max_chars]
        if text:
            lines.append(f"- {text}")
    return "\n".join(lines)


__all__ = [
    "DEFAULT_DIMENSIONS",
    "DEFAULT_LIMIT",
    "EMBEDDING_VERSION",
    "MIN_SCORE",
    "cosine",
    "embed_text",
    "ensure_embedding",
    "ensure_embeddings",
    "memory_prompt",
    "rank_memories",
    "record_text",
]
