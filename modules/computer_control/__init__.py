# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — модуль керування комп'ютером (Windows).

Публічний API:

* :class:`modules.computer_control.tools.PcController` — відкриття програм і
  сайтів, PowerShell із класифікацією безпеки, файли, система, екран,
  мишка/клавіатура, вікна;
* :func:`modules.computer_control.tools.classify_command` — чиста функція
  класифікації ризику PowerShell-команди (``safe`` / ``dangerous`` /
  ``catastrophic``);
* :data:`modules.computer_control.tools.SITE_ALIASES` та
  :data:`modules.computer_control.tools.APP_ALIASES` — словники аліасів.

Імпорт модуля не виконує жодних системних дій: ``pyautogui``, ``pygetwindow``
і ``PIL`` імпортуються ліниво, усередині відповідних методів.
"""

from __future__ import annotations

from modules.computer_control.tools import (
    APP_ALIASES,
    CATASTROPHIC,
    DANGEROUS,
    PcController,
    RISK_CATASTROPHIC,
    RISK_DANGEROUS,
    RISK_SAFE,
    SAFE_START,
    SITE_ALIASES,
    classify_command,
    normalize_alias,
)

__all__ = [
    "APP_ALIASES",
    "CATASTROPHIC",
    "DANGEROUS",
    "PcController",
    "RISK_CATASTROPHIC",
    "RISK_DANGEROUS",
    "RISK_SAFE",
    "SAFE_START",
    "SITE_ALIASES",
    "classify_command",
    "normalize_alias",
]
