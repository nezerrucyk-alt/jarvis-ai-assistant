# -*- coding: utf-8 -*-
"""Interface translations for the JARVIS desktop shell.

Covers the sidebar, main status lines and the interface-language selector.
Deep dialogs stay Ukrainian for now; AI replies already mirror the user.
"""
from __future__ import annotations

from typing import Any

UI_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("uk", "Українська"),
    ("en", "English"),
    ("pl", "Polski"),
    ("de", "Deutsch"),
    ("es", "Español"),
    ("fr", "Français"),
)

SIDEBAR_KEYS: tuple[str, ...] = (
    "voice", "scan", "translate", "new_chat", "clipboard", "briefing",
    "settings", "customize", "update", "memory", "reminders", "automations",
    "organizer", "plugins", "gaming", "history",
)

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "uk": {
        "sidebar.voice": "Голосовий режим",
        "sidebar.scan": "Сканувати екран",
        "sidebar.translate": "Перекласти екран",
        "sidebar.new_chat": "Нова розмова",
        "sidebar.clipboard": "Буфер обміну",
        "sidebar.briefing": "Ранковий брифінг",
        "sidebar.settings": "Налаштування",
        "sidebar.customize": "Кастомізація",
        "sidebar.update": "Оновлення",
        "sidebar.memory": "Моя пам'ять",
        "sidebar.reminders": "Нагадування",
        "sidebar.automations": "Автоматизації",
        "sidebar.organizer": "Порядок файлів",
        "sidebar.plugins": "Плагіни",
        "sidebar.gaming": "Режим ґеймера",
        "sidebar.history": "Вся історія",
        "status.ready": "Готовий, сер.",
        "status.thinking": "Думаю…",
        "status.speaking": "Говорю…",
        "status.listening": "Слухаю…",
        "status.system_ready": "СИСТЕМА ГОТОВА",
        "status.access_full": "ДОСТУП: ПОВНИЙ",
        "status.access_limited": "ДОСТУП: ОБМЕЖЕНИЙ",
        "status.sound_on": "Звук: увімкнено",
        "status.sound_off": "Звук: вимкнено",
        "settings.ui_language": "Мова інтерфейсу",
    },
    "en": {
        "sidebar.voice": "Voice mode",
        "sidebar.scan": "Scan screen",
        "sidebar.translate": "Translate screen",
        "sidebar.new_chat": "New chat",
        "sidebar.clipboard": "Clipboard",
        "sidebar.briefing": "Morning briefing",
        "sidebar.settings": "Settings",
        "sidebar.customize": "Customize",
        "sidebar.update": "Updates",
        "sidebar.memory": "My memory",
        "sidebar.reminders": "Reminders",
        "sidebar.automations": "Automations",
        "sidebar.organizer": "File organizer",
        "sidebar.plugins": "Plugins",
        "sidebar.gaming": "Gamer mode",
        "sidebar.history": "All chats",
        "status.ready": "Ready, sir.",
        "status.thinking": "Thinking…",
        "status.speaking": "Speaking…",
        "status.listening": "Listening…",
        "status.system_ready": "SYSTEM READY",
        "status.access_full": "ACCESS: FULL",
        "status.access_limited": "ACCESS: LIMITED",
        "status.sound_on": "Sound: on",
        "status.sound_off": "Sound: off",
        "settings.ui_language": "Interface language",
    },
    "pl": {
        "sidebar.voice": "Tryb głosowy",
        "sidebar.scan": "Skanuj ekran",
        "sidebar.translate": "Przetłumacz ekran",
        "sidebar.new_chat": "Nowa rozmowa",
        "sidebar.clipboard": "Schowek",
        "sidebar.briefing": "Poranny briefing",
        "sidebar.settings": "Ustawienia",
        "sidebar.customize": "Personalizacja",
        "sidebar.update": "Aktualizacje",
        "sidebar.memory": "Moja pamięć",
        "sidebar.reminders": "Przypomnienia",
        "sidebar.automations": "Automatyzacje",
        "sidebar.organizer": "Porządek plików",
        "sidebar.plugins": "Wtyczki",
        "sidebar.gaming": "Tryb gracza",
        "sidebar.history": "Cała historia",
        "status.ready": "Gotowy, sir.",
        "status.thinking": "Myślę…",
        "status.speaking": "Mówię…",
        "status.listening": "Słucham…",
        "status.system_ready": "SYSTEM GOTOWY",
        "status.access_full": "DOSTĘP: PEŁNY",
        "status.access_limited": "DOSTĘP: OGRANICZONY",
        "status.sound_on": "Dźwięk: wł.",
        "status.sound_off": "Dźwięk: wył.",
        "settings.ui_language": "Język interfejsu",
    },
    "de": {
        "sidebar.voice": "Sprachmodus",
        "sidebar.scan": "Bildschirm scannen",
        "sidebar.translate": "Bildschirm übersetzen",
        "sidebar.new_chat": "Neuer Chat",
        "sidebar.clipboard": "Zwischenablage",
        "sidebar.briefing": "Morgen-Briefing",
        "sidebar.settings": "Einstellungen",
        "sidebar.customize": "Anpassen",
        "sidebar.update": "Updates",
        "sidebar.memory": "Mein Gedächtnis",
        "sidebar.reminders": "Erinnerungen",
        "sidebar.automations": "Automatisierungen",
        "sidebar.organizer": "Dateien sortieren",
        "sidebar.plugins": "Plugins",
        "sidebar.gaming": "Gamer-Modus",
        "sidebar.history": "Alle Chats",
        "status.ready": "Bereit, Sir.",
        "status.thinking": "Denke nach…",
        "status.speaking": "Spreche…",
        "status.listening": "Höre zu…",
        "status.system_ready": "SYSTEM BEREIT",
        "status.access_full": "ZUGRIFF: VOLL",
        "status.access_limited": "ZUGRIFF: BEGRENZT",
        "status.sound_on": "Ton: an",
        "status.sound_off": "Ton: aus",
        "settings.ui_language": "Oberflächensprache",
    },
    "es": {
        "sidebar.voice": "Modo de voz",
        "sidebar.scan": "Escanear pantalla",
        "sidebar.translate": "Traducir pantalla",
        "sidebar.new_chat": "Nuevo chat",
        "sidebar.clipboard": "Portapapeles",
        "sidebar.briefing": "Informe matutino",
        "sidebar.settings": "Ajustes",
        "sidebar.customize": "Personalizar",
        "sidebar.update": "Actualizaciones",
        "sidebar.memory": "Mi memoria",
        "sidebar.reminders": "Recordatorios",
        "sidebar.automations": "Automatizaciones",
        "sidebar.organizer": "Organizador de archivos",
        "sidebar.plugins": "Plugins",
        "sidebar.gaming": "Modo gamer",
        "sidebar.history": "Todo el historial",
        "status.ready": "Listo, señor.",
        "status.thinking": "Pensando…",
        "status.speaking": "Hablando…",
        "status.listening": "Escuchando…",
        "status.system_ready": "SISTEMA LISTO",
        "status.access_full": "ACCESO: TOTAL",
        "status.access_limited": "ACCESO: LIMITADO",
        "status.sound_on": "Sonido: activado",
        "status.sound_off": "Sonido: desactivado",
        "settings.ui_language": "Idioma de la interfaz",
    },
    "fr": {
        "sidebar.voice": "Mode vocal",
        "sidebar.scan": "Scanner l'écran",
        "sidebar.translate": "Traduire l'écran",
        "sidebar.new_chat": "Nouvelle conversation",
        "sidebar.clipboard": "Presse-papiers",
        "sidebar.briefing": "Briefing du matin",
        "sidebar.settings": "Paramètres",
        "sidebar.customize": "Personnaliser",
        "sidebar.update": "Mises à jour",
        "sidebar.memory": "Ma mémoire",
        "sidebar.reminders": "Rappels",
        "sidebar.automations": "Automatisations",
        "sidebar.organizer": "Rangement des fichiers",
        "sidebar.plugins": "Extensions",
        "sidebar.gaming": "Mode gamer",
        "sidebar.history": "Tout l'historique",
        "status.ready": "Prêt, monsieur.",
        "status.thinking": "Je réfléchis…",
        "status.speaking": "Je parle…",
        "status.listening": "J'écoute…",
        "status.system_ready": "SYSTÈME PRÊT",
        "status.access_full": "ACCÈS : COMPLET",
        "status.access_limited": "ACCÈS : LIMITÉ",
        "status.sound_on": "Son : activé",
        "status.sound_off": "Son : désactivé",
        "settings.ui_language": "Langue de l'interface",
    },
}

_STATUS_KEYS = {
    "Готовий, сер.": "status.ready",
    "Думаю…": "status.thinking",
    "Говорю…": "status.speaking",
    "Слухаю…": "status.listening",
    "СИСТЕМА ГОТОВА": "status.system_ready",
    "ДОСТУП: ПОВНИЙ": "status.access_full",
    "ДОСТУП: ОБМЕЖЕНИЙ": "status.access_limited",
    "Звук: увімкнено": "status.sound_on",
    "Звук: вимкнено": "status.sound_off",
}


def normalize_language(lang: Any) -> str:
    code = str(lang or "uk").strip().lower()
    return code if code in _TRANSLATIONS else "uk"


def t(key: str, lang: str = "uk") -> str:
    table = _TRANSLATIONS.get(normalize_language(lang)) or {}
    return table.get(key) or _TRANSLATIONS["uk"].get(key) or key


def sidebar_labels(lang: str = "uk") -> dict[str, str]:
    return {key: t(f"sidebar.{key}", lang) for key in SIDEBAR_KEYS}


def translate_status(text: str, lang: str = "uk") -> str:
    key = _STATUS_KEYS.get(str(text or "").strip())
    return t(key, lang) if key else str(text)


__all__ = [
    "SIDEBAR_KEYS",
    "UI_LANGUAGES",
    "normalize_language",
    "sidebar_labels",
    "t",
    "translate_status",
]
