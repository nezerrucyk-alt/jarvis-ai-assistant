# -*- coding: utf-8 -*-
"""HUD state mapping (no Tk windows are created here)."""
from __future__ import annotations

import unittest

from ui.hud import STATE_COLORS, state_from_status


class HudStateTests(unittest.TestCase):
    def test_states_exist(self) -> None:
        self.assertEqual(
            set(STATE_COLORS), {"idle", "listening", "thinking", "speaking"}
        )

    def test_mapping(self) -> None:
        self.assertEqual(state_from_status("Слухаю…"), "listening")
        self.assertEqual(state_from_status("Думаю…"), "thinking")
        self.assertEqual(state_from_status("Аналізую екран…"), "thinking")
        self.assertEqual(state_from_status("Говорю…"), "speaking")
        self.assertEqual(state_from_status("Готовий, сер."), "idle")
        self.assertEqual(state_from_status(""), "idle")


if __name__ == "__main__":
    unittest.main()
