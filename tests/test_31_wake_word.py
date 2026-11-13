# -*- coding: utf-8 -*-
"""Tests for the wake-word matcher, cooldown gate and listener lifecycle."""
from __future__ import annotations

import unittest

from modules.voice.wake import (
    WAKE_PHRASES,
    WakeGate,
    WakeWordListener,
    is_wake_phrase,
    normalize_wake_text,
)


class NormalizeWakeTextTests(unittest.TestCase):
    def test_lowercases_and_strips_punctuation(self) -> None:
        self.assertEqual(
            normalize_wake_text("  Hey, JARVIS!  "),
            "hey jarvis",
        )

    def test_keeps_cyrillic_and_apostrophes(self) -> None:
        self.assertEqual(
            normalize_wake_text("Джарвіс, відкрий Steam!"),
            "джарвіс відкрий steam",
        )
        self.assertEqual(normalize_wake_text("п'ять"), "п'ять")

    def test_collapses_whitespace(self) -> None:
        self.assertEqual(normalize_wake_text("hey\n\tjarvis"), "hey jarvis")


class WakePhraseTests(unittest.TestCase):
    def test_accepts_english_phrase_at_start(self) -> None:
        self.assertTrue(is_wake_phrase("Hey Jarvis, open Steam"))
        self.assertTrue(is_wake_phrase("OK Jarvis what time is it"))
        self.assertTrue(is_wake_phrase("jarvis"))

    def test_accepts_ukrainian_variants(self) -> None:
        for phrase in (
            "Джарвіс, відкрий Roblox Studio",
            "джарвис яка погода",
            "Жарвіс увімкни музику",
            "Гарвіс, ти тут?",
            "будь ласка, джарвіс, відкрий звіт",
        ):
            with self.subTest(phrase=phrase):
                self.assertTrue(is_wake_phrase(phrase))

    def test_rejects_unrelated_speech(self) -> None:
        self.assertFalse(is_wake_phrase(""))
        self.assertFalse(is_wake_phrase("відкрий Steam"))
        self.assertFalse(is_wake_phrase("яка сьогодні погода"))
        self.assertFalse(is_wake_phrase("це просто текст без звертання"))

    def test_phrase_must_be_near_the_start(self) -> None:
        self.assertFalse(
            is_wake_phrase(
                "я вчора довго думав про те, що сказав джарвіс учора ввечері"
            )
        )

    def test_custom_phrase_list(self) -> None:
        self.assertTrue(is_wake_phrase("комп'ютер, прокидайся", ["прокидайся"]))
        self.assertFalse(is_wake_phrase("комп'ютер, прокидайся", ["джарвіс"]))

    def test_default_phrases_are_not_empty(self) -> None:
        self.assertTrue(any(phrase.strip() for phrase in WAKE_PHRASES))


class WakeGateTests(unittest.TestCase):
    def test_cooldown_blocks_repeated_triggers(self) -> None:
        now = [100.0]
        gate = WakeGate(cooldown=2.0, clock=lambda: now[0])
        self.assertTrue(gate.allow())
        now[0] += 1.0
        self.assertFalse(gate.allow())
        now[0] += 1.0
        self.assertTrue(gate.allow())

    def test_reset_allows_immediately(self) -> None:
        now = [10.0]
        gate = WakeGate(cooldown=5.0, clock=lambda: now[0])
        self.assertTrue(gate.allow())
        self.assertFalse(gate.allow())
        gate.reset()
        self.assertTrue(gate.allow())

    def test_zero_cooldown_always_allows(self) -> None:
        gate = WakeGate(cooldown=0.0, clock=lambda: 1.0)
        self.assertTrue(gate.allow())
        self.assertTrue(gate.allow())


class WakeListenerLifecycleTests(unittest.TestCase):
    def test_detect_backend_returns_known_value(self) -> None:
        self.assertIn(
            WakeWordListener.detect_backend(),
            {"openwakeword", "stt"},
        )

    def test_stop_without_start_is_safe(self) -> None:
        listener = WakeWordListener({}, on_wake=lambda: None)
        listener.stop()

    def test_start_and_stop_with_fake_backend(self) -> None:
        listener = WakeWordListener({}, on_wake=lambda: None)
        listener._run = lambda: None  # type: ignore[method-assign]
        listener.start()
        listener.stop()
        self.assertTrue(listener._stop.is_set())


if __name__ == "__main__":
    unittest.main()
