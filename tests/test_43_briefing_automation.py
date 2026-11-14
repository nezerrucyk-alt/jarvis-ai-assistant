# -*- coding: utf-8 -*-
"""Briefing automations and the new action type."""
from __future__ import annotations

import unittest
from datetime import datetime

from core.automations import (
    ACTIONS,
    AutomationError,
    build_automation,
    describe_automation,
)


class BriefingAutomationTests(unittest.TestCase):
    def test_action_is_supported(self) -> None:
        self.assertIn("briefing", ACTIONS)
        record = build_automation(
            "Ранковий брифінг",
            "daily 09:00",
            action="briefing",
            automation_id="briefing-daily",
            created_at=datetime(2026, 11, 14, 8, 0),
        )
        self.assertEqual(record["action"], "briefing")
        self.assertIn("брифінг", describe_automation(record))

    def test_briefing_still_validates_schedule(self) -> None:
        with self.assertRaises(AutomationError):
            build_automation("x", "daily 25:00", action="briefing")

    def test_unknown_action_rejected(self) -> None:
        with self.assertRaises(AutomationError):
            build_automation("x", "daily 09:00", action="shell")


if __name__ == "__main__":
    unittest.main()
