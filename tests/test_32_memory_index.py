# -*- coding: utf-8 -*-
"""Tests for the local hashing memory index."""
from __future__ import annotations

import unittest

from core.memory_index import (
    DEFAULT_DIMENSIONS,
    EMBEDDING_VERSION,
    cosine,
    embed_text,
    ensure_embedding,
    ensure_embeddings,
    memory_prompt,
    rank_memories,
)


class EmbeddingTests(unittest.TestCase):
    def test_embedding_is_deterministic_and_normalized(self) -> None:
        first = embed_text("Люблю каву з молоком")
        second = embed_text("Люблю каву з молоком")
        self.assertEqual(first, second)
        self.assertEqual(len(first), DEFAULT_DIMENSIONS)
        norm = sum(value * value for value in first) ** 0.5
        self.assertAlmostEqual(norm, 1.0, places=6)

    def test_similar_texts_score_higher_than_unrelated(self) -> None:
        query = embed_text("мій улюблений напій — кава")
        related = embed_text("кава з молоком щоранку")
        unrelated = embed_text("налаштувати приватний сервер Roblox")
        self.assertGreater(cosine(query, related), cosine(query, unrelated))
        self.assertGreater(cosine(query, related), 0.08)

    def test_ukrainian_inflections_share_features(self) -> None:
        left = embed_text("зустріч з командою у понеділок")
        right = embed_text("зустрічі з командою")
        self.assertGreater(cosine(left, right), 0.2)

    def test_empty_text_is_zero_vector(self) -> None:
        vector = embed_text("")
        self.assertEqual(len(vector), DEFAULT_DIMENSIONS)
        self.assertTrue(all(value == 0.0 for value in vector))
        self.assertEqual(cosine(vector, vector), 0.0)

    def test_cosine_is_bounded(self) -> None:
        value = cosine(embed_text("alpha beta"), embed_text("alpha beta"))
        self.assertGreaterEqual(value, -1.0)
        self.assertLessEqual(value, 1.0)


class MemoryRankingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = [
            {"id": "1", "text": "Улюблена кава — лате без цукру"},
            {"id": "2", "text": "Приватний сервер Roblox для Break and Steal an Egg"},
            {"id": "3", "text": "День народження мами 12 травня"},
            {"id": "4", "text": "Робочий проєкт JARVIS на Python"},
        ]

    def test_relevant_memory_comes_first(self) -> None:
        ranked = rank_memories(self.records, "що я люблю пити зранку?")
        self.assertEqual(ranked[0]["id"], "1")

    def test_limit_is_respected(self) -> None:
        ranked = rank_memories(self.records, "Roblox", limit=1)
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["id"], "2")

    def test_empty_query_returns_recent_records(self) -> None:
        ranked = rank_memories(self.records, "", limit=2)
        self.assertEqual([item["id"] for item in ranked], ["3", "4"])

    def test_legacy_records_get_embeddings(self) -> None:
        legacy = [{"id": "old", "text": "старий запис без вектора"}]
        ensure_embeddings(legacy)
        self.assertEqual(legacy[0]["embedding_version"], EMBEDDING_VERSION)
        self.assertEqual(len(legacy[0]["embedding"]), DEFAULT_DIMENSIONS)

    def test_stale_embedding_is_recomputed(self) -> None:
        record = {"text": "оновлений текст", "embedding": [0.0], "embedding_version": "old"}
        ensure_embedding(record)
        self.assertEqual(record["embedding_version"], EMBEDDING_VERSION)
        self.assertEqual(len(record["embedding"]), DEFAULT_DIMENSIONS)

    def test_empty_records_are_ignored(self) -> None:
        ranked = rank_memories(
            [{"id": "blank", "text": "   "}, {"id": "ok", "text": "кава"}],
            "кава",
        )
        self.assertEqual([item["id"] for item in ranked], ["ok"])

    def test_prompt_contains_only_relevant_lines(self) -> None:
        prompt = memory_prompt(self.records, "Roblox сервер", limit=2)
        self.assertIn("Roblox", prompt)
        self.assertNotIn("День народження", prompt)
        self.assertTrue(prompt.startswith("- "))


if __name__ == "__main__":
    unittest.main()
