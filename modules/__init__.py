# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — пакет прикладних модулів.

Містить незалежні від GUI модулі, які можна використовувати як у v1
(``jarvis.py``), так і в модульному застосунку v2 (``main.py``):

* :mod:`modules.voice` — синтез мовлення (TTS) і розпізнавання (STT);
* :mod:`modules.computer_control` — керування Windows: запуск програм,
  PowerShell з класифікацією безпеки, файли, мишка/клавіатура, вікна,
  знімки екрана.

Жодних дій під час імпорту пакет не виконує: усі важкі сторонні
залежності (edge-tts, pygame, sounddevice, SpeechRecognition, pyautogui,
pygetwindow) імпортуються ліниво — усередині відповідних методів.
"""

from __future__ import annotations

__all__ = ["computer_control", "voice"]
__version__ = "2.4.0"
