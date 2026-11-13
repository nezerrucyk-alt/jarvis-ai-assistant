# -*- coding: utf-8 -*-
"""
J.A.R.V.I.S. — система кастомізації інтерфейсу.

Модуль не залежить від ``jarvis.py`` і не створює вікон під час імпорту.
Він відповідає за:

* збереження теми, шрифтів, макета й кастомного коду у
  ``%APPDATA%\\Jarvis\\customization.json``;
* перефарбовування вже створених Tkinter-віджетів без перезапуску;
* масштабування шрифтів;
* безпечне (наскільки це можливо в Tkinter) виконання користувацького
  коду для кастомного блоку інтерфейсу;
* готові пресети тем.

Користувацький код виконується локально з обмеженим набором builtins.
Це захист від випадкових помилок, а не повноцінна пісочниця: запускати
чужий код небезпечно.
"""

from __future__ import annotations

import builtins
import json
import math
import re
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import ttk
from typing import Any

# ── базова палітра Command Deck ──────────────────────────────────────────────

DEFAULT_THEME: dict[str, str] = {
    "bg": "#080B12",
    "panel": "#101725",
    "panel_alt": "#141D2E",
    "sidebar": "#0B101B",
    "line": "#22304A",
    "accent": "#5B8CFF",
    "accent_dim": "#93B4FF",
    "gold": "#E8C987",
    "text": "#F0F4FF",
    "muted": "#7F8CA6",
    "green": "#5AD1A0",
    "red": "#FF7A90",
}

THEME_LABELS: dict[str, str] = {
    "bg": "Головний фон",
    "panel": "Панелі",
    "panel_alt": "Вторинні панелі",
    "sidebar": "Бокова панель",
    "line": "Лінії та рамки",
    "accent": "Акцент",
    "accent_dim": "Акцент приглушений",
    "gold": "Попередження / золото",
    "text": "Основний текст",
    "muted": "Другорядний текст",
    "green": "Успіх / онлайн",
    "red": "Помилка / небезпека",
}

THEME_PRESETS: dict[str, dict[str, str]] = {
    "command": dict(DEFAULT_THEME),
    "midnight": {
        "bg": "#05070C",
        "panel": "#0B111C",
        "panel_alt": "#101A2B",
        "sidebar": "#070B13",
        "line": "#1D2B45",
        "accent": "#6EA8FF",
        "accent_dim": "#A9C6FF",
        "gold": "#F0D39A",
        "text": "#F4F7FF",
        "muted": "#7C89A3",
        "green": "#58E0A6",
        "red": "#FF8296",
    },
    "matrix": {
        "bg": "#040A07",
        "panel": "#091510",
        "panel_alt": "#0D1D16",
        "sidebar": "#050D09",
        "line": "#173527",
        "accent": "#35F0A0",
        "accent_dim": "#8CFFD0",
        "gold": "#E8D98A",
        "text": "#EFFFF6",
        "muted": "#7FA895",
        "green": "#5CFFB0",
        "red": "#FF7E8E",
    },
    "crimson": {
        "bg": "#0B0508",
        "panel": "#160A10",
        "panel_alt": "#211019",
        "sidebar": "#0D0609",
        "line": "#3A1626",
        "accent": "#FF4D6D",
        "accent_dim": "#FF9AAF",
        "gold": "#F2C879",
        "text": "#FFF3F6",
        "muted": "#A98290",
        "green": "#67E0A3",
        "red": "#FF5C7A",
    },
    "amber": {
        "bg": "#0C0905",
        "panel": "#171008",
        "panel_alt": "#22170B",
        "sidebar": "#0E0A06",
        "line": "#3A2A14",
        "accent": "#FFB347",
        "accent_dim": "#FFD59A",
        "gold": "#FFD98A",
        "text": "#FFF7EA",
        "muted": "#A89172",
        "green": "#8BE0A0",
        "red": "#FF8A7A",
    },
    "ice": {
        "bg": "#060B12",
        "panel": "#0D1622",
        "panel_alt": "#122033",
        "sidebar": "#080F18",
        "line": "#1E3550",
        "accent": "#7DE3FF",
        "accent_dim": "#B8F1FF",
        "gold": "#F0D89A",
        "text": "#F2FBFF",
        "muted": "#7E9AAF",
        "green": "#6BE8C0",
        "red": "#FF879B",
    },
}

PRESET_LABELS: dict[str, str] = {
    "command": "Command Deck",
    "midnight": "Midnight",
    "matrix": "Matrix",
    "crimson": "Crimson",
    "amber": "Amber",
    "ice": "Ice",
}

# ── макет ────────────────────────────────────────────────────────────────────

MAIN_BLOCKS: tuple[str, ...] = (
    "topbar", "hero", "log", "queue", "custom", "composer", "footer",
)
MAIN_BLOCK_LABELS: dict[str, str] = {
    "topbar": "Верхня панель",
    "hero": "Hero-блок",
    "log": "Стрічка діалогу",
    "queue": "Черга завдань",
    "custom": "Кастомний блок",
    "composer": "Командний рядок",
    "footer": "Футер",
}
SIDEBAR_ITEMS: tuple[str, ...] = (
    "voice", "scan", "translate", "new_chat",
    "settings", "customize", "update", "memory", "reminders", "gaming",
    "history",
)
SIDEBAR_LABELS: dict[str, str] = {
    "voice": "Голосовий режим",
    "scan": "Сканувати екран",
    "translate": "Перекласти екран",
    "new_chat": "Нова розмова",
    "settings": "Налаштування",
    "customize": "Кастомізація",
    "update": "Оновлення",
    "memory": "Моя пам'ять",
    "reminders": "Нагадування",
    "gaming": "Режим ґеймера",
    "history": "Вся історія",
}

DEFAULT_LAYOUT: dict[str, Any] = {
    "main_order": list(MAIN_BLOCKS),
    "main_visible": {key: True for key in MAIN_BLOCKS},
    "sidebar_enabled": True,
    "sidebar_order": list(SIDEBAR_ITEMS),
    "sidebar_visible": {key: True for key in SIDEBAR_ITEMS},
    "animations": True,
    "window_fade": True,
    "typewriter": True,
    "reactor_glow": True,
    "compact": False,
}

DEFAULT_FONTS: dict[str, Any] = {
    "family": "",
    "scale": 1.0,
}

DEFAULT_CUSTOM_CODE = """# Доступні: tk, ttk, parent, colors, root, math
# Поверни віджет або створи його всередині parent.
def build(parent, colors):
    card = tk.Frame(parent, bg=colors["panel"])
    tk.Label(
        card, text="CUSTOM MODULE", bg=colors["panel"],
        fg=colors["accent"], font=("Consolas", 8, "bold"),
    ).pack(anchor="w", padx=14, pady=(12, 2))
    tk.Label(
        card, text="Цей блок створено твоїм кодом.",
        bg=colors["panel"], fg=colors["text"],
        font=("Segoe UI", 10),
    ).pack(anchor="w", padx=14, pady=(0, 12))
    return card
"""


# ── кольори ──────────────────────────────────────────────────────────────────

_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def normalize_color(value: Any, fallback: str | None = None) -> str | None:
    """Повертає ``#RRGGBB`` у нижньому регістрі або fallback."""
    text = str(value or "").strip()
    if not _COLOR_RE.match(text):
        return fallback
    if len(text) == 4:
        text = "#" + "".join(ch * 2 for ch in text[1:])
    return text.lower()


def _rgb(color: str) -> tuple[int, int, int]:
    color = normalize_color(color, "#000000") or "#000000"
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, int(round(v)))) for v in rgb))


def blend(first: str, second: str, amount: float) -> str:
    """Лінійно змішує два кольори; ``amount=0`` — перший, ``1`` — другий."""
    amount = max(0.0, min(1.0, float(amount)))
    a, b = _rgb(first), _rgb(second)
    return _hex(tuple(a[i] + (b[i] - a[i]) * amount for i in range(3)))


def derive_theme(theme: dict[str, Any] | None) -> dict[str, str]:
    """Доповнює базову тему похідними кольорами для реактора й рамок."""
    base = dict(DEFAULT_THEME)
    for key, value in (theme or {}).items():
        color = normalize_color(value)
        if key in base and color:
            base[key] = color
    base["line_deep"] = blend(base["bg"], base["accent"], 0.16)
    base["line_bright"] = blend(base["bg"], base["accent"], 0.30)
    base["muted_dim"] = blend(base["bg"], base["muted"], 0.62)
    base["text_bright"] = blend(base["text"], "#ffffff", 0.45)
    base["ring_1"] = blend(base["bg"], base["accent"], 0.10)
    base["ring_2"] = blend(base["bg"], base["accent"], 0.18)
    base["ring_3"] = blend(base["bg"], base["accent"], 0.28)
    base["accent_soft"] = blend(base["panel"], base["accent"], 0.20)
    base["gold_soft"] = blend(base["panel"], base["gold"], 0.18)
    return base


# ── нормалізація та збереження ───────────────────────────────────────────────

def default_customization() -> dict[str, Any]:
    """Свіжа конфігурація кастомізації."""
    return {
        "version": 1,
        "theme": dict(DEFAULT_THEME),
        "fonts": dict(DEFAULT_FONTS),
        "layout": {
            "main_order": list(DEFAULT_LAYOUT["main_order"]),
            "main_visible": dict(DEFAULT_LAYOUT["main_visible"]),
            "sidebar_enabled": True,
            "sidebar_order": list(DEFAULT_LAYOUT["sidebar_order"]),
            "sidebar_visible": dict(DEFAULT_LAYOUT["sidebar_visible"]),
            "animations": True,
            "window_fade": True,
            "typewriter": True,
            "reactor_glow": True,
            "compact": False,
        },
        "custom_code": DEFAULT_CUSTOM_CODE,
        "custom_code_enabled": False,
    }


def _normalize_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on", "так"}:
            return True
        if lowered in {"0", "false", "no", "off", "ні"}:
            return False
    return fallback


def normalize_customization(data: Any) -> dict[str, Any]:
    """Приводить довільний словник до безпечної схеми."""
    result = default_customization()
    if not isinstance(data, dict):
        return result

    theme = data.get("theme")
    if isinstance(theme, dict):
        for key in DEFAULT_THEME:
            color = normalize_color(theme.get(key))
            if color:
                result["theme"][key] = color

    fonts = data.get("fonts")
    if isinstance(fonts, dict):
        family = str(fonts.get("family") or "").strip()[:80]
        result["fonts"]["family"] = family
        try:
            scale = float(fonts.get("scale", 1.0))
        except (TypeError, ValueError):
            scale = 1.0
        result["fonts"]["scale"] = max(0.75, min(1.40, round(scale, 2)))

    layout = data.get("layout")
    if isinstance(layout, dict):
        order = layout.get("main_order")
        if isinstance(order, list):
            seen: list[str] = []
            for key in order:
                key = str(key)
                if key in MAIN_BLOCKS and key not in seen:
                    seen.append(key)
            for key in MAIN_BLOCKS:
                if key not in seen:
                    seen.append(key)
            result["layout"]["main_order"] = seen

        sidebar_order = layout.get("sidebar_order")
        if isinstance(sidebar_order, list):
            seen_sidebar: list[str] = []
            for key in sidebar_order:
                key = str(key)
                if key in SIDEBAR_ITEMS and key not in seen_sidebar:
                    seen_sidebar.append(key)
            for key in SIDEBAR_ITEMS:
                if key not in seen_sidebar:
                    seen_sidebar.append(key)
            result["layout"]["sidebar_order"] = seen_sidebar

        for group, defaults in (
            ("main_visible", DEFAULT_LAYOUT["main_visible"]),
            ("sidebar_visible", DEFAULT_LAYOUT["sidebar_visible"]),
        ):
            values = layout.get(group)
            if isinstance(values, dict):
                for key, fallback in defaults.items():
                    result["layout"][group][key] = _normalize_bool(
                        values.get(key), fallback
                    )

        result["layout"]["sidebar_enabled"] = _normalize_bool(
            layout.get("sidebar_enabled"), True
        )
        for key in ("animations", "window_fade", "typewriter", "reactor_glow", "compact"):
            result["layout"][key] = _normalize_bool(
                layout.get(key), DEFAULT_LAYOUT[key]
            )

    code = data.get("custom_code")
    if isinstance(code, str):
        result["custom_code"] = code[:24000]
    result["custom_code_enabled"] = _normalize_bool(
        data.get("custom_code_enabled"), False
    )
    return result


def load_customization(path: Path) -> dict[str, Any]:
    """Читає файл кастомізації; пошкоджений файл не ламає запуск."""
    try:
        if Path(path).is_file():
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
            return normalize_customization(raw)
    except Exception:
        pass
    return default_customization()


def save_customization(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    """Атомарно зберігає нормалізовану кастомізацію."""
    normalized = normalize_customization(data)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(target)
    return normalized


# ── перефарбовування Tkinter ─────────────────────────────────────────────────

WIDGET_COLOR_OPTIONS = (
    "background",
    "foreground",
    "activebackground",
    "activeforeground",
    "selectbackground",
    "selectforeground",
    "highlightbackground",
    "highlightcolor",
    "insertbackground",
    "troughcolor",
    "disabledforeground",
)

ROLE_BY_DEFAULT: dict[str, str] = {
    "#080b12": "bg",
    "#101725": "panel",
    "#141d2e": "panel_alt",
    "#0b101b": "sidebar",
    "#22304a": "line",
    "#5b8cff": "accent",
    "#93b4ff": "accent_dim",
    "#e8c987": "gold",
    "#f0f4ff": "text",
    "#7f8ca6": "muted",
    "#5ad1a0": "green",
    "#ff7a90": "red",
    "#1b2a4a": "line_deep",
    "#2b3b66": "line_bright",
    "#3a465c": "muted_dim",
    "#eaf0ff": "text_bright",
    "#1e2540": "ring_1",
    "#273156": "ring_2",
    "#35447a": "ring_3",
}


def _role_for_color(
    value: Any, mapping: dict[str, str] | None = None
) -> str | None:
    color = normalize_color(value)
    if not color:
        return None
    return (mapping or ROLE_BY_DEFAULT).get(color)


def apply_theme(
    widget: tk.Misc,
    theme: dict[str, str],
    previous: dict[str, str] | None = None,
) -> None:
    """Рекурсивно перефарбовує віджет і його дітей під нову тему.

    ``previous`` — попередня тема. Вона потрібна, щоб повторні зміни теми
    працювали: віджети вже мають кольори попередньої теми, а не стандартні.
    """
    if getattr(widget, "_theme_skip", False):
        return
    mapping = dict(ROLE_BY_DEFAULT)
    if isinstance(previous, dict):
        for role, value in previous.items():
            color = normalize_color(value)
            if color and role in theme:
                mapping.setdefault(color, role)
    try:
        keys = set(widget.keys())
    except (tk.TclError, AttributeError):
        return

    updates: dict[str, str] = {}
    for option in WIDGET_COLOR_OPTIONS:
        if option not in keys:
            continue
        try:
            old = widget.cget(option)
        except tk.TclError:
            continue
        role = _role_for_color(old, mapping)
        if role and theme.get(role):
            updates[option] = theme[role]
    if updates:
        try:
            widget.configure(**updates)
        except tk.TclError:
            pass

    if isinstance(widget, tk.Text):
        for tag, role in (("you", "gold"), ("jarvis", "text"), ("sys", "muted")):
            try:
                widget.tag_configure(tag, foreground=theme[role])
            except tk.TclError:
                pass
        try:
            widget.tag_configure(
                "sel", background=theme["accent"], foreground=theme["bg"]
            )
        except tk.TclError:
            pass

    if isinstance(widget, tk.Canvas):
        for item in widget.find_all():
            for option in ("fill", "outline"):
                try:
                    old = widget.itemcget(item, option)
                except tk.TclError:
                    continue
                role = _role_for_color(old, mapping)
                if role and theme.get(role):
                    try:
                        widget.itemconfigure(item, **{option: theme[role]})
                    except tk.TclError:
                        pass

    try:
        children = widget.winfo_children()
    except tk.TclError:
        return
    for child in children:
        apply_theme(child, theme, previous)


def _scaled_font(
    spec: Any, family: str, scale: float
) -> tuple[str, int, str] | None:
    try:
        actual = tkfont.Font(font=spec).actual()
    except Exception:
        return None
    size = int(actual.get("size") or 9)
    if size < 0:
        size = -max(6, int(round(abs(size) * scale)))
    else:
        size = max(6, int(round(size * scale)))
    styles: list[str] = []
    if actual.get("weight") == "bold":
        styles.append("bold")
    if actual.get("slant") == "italic":
        styles.append("italic")
    if actual.get("underline"):
        styles.append("underline")
    if actual.get("overstrike"):
        styles.append("overstrike")
    name = family or str(actual.get("family") or "Segoe UI")
    return (name, size, *styles)


def apply_fonts(widget: tk.Misc, family: str = "", scale: float = 1.0) -> None:
    """Масштабує шрифти віджетів і тегів Text."""
    if getattr(widget, "_font_skip", False):
        return
    try:
        keys = set(widget.keys())
    except (tk.TclError, AttributeError):
        return

    if "font" in keys:
        try:
            spec = getattr(widget, "_base_font_spec", None)
            if spec is None:
                spec = widget.cget("font")
                widget._base_font_spec = spec
        except tk.TclError:
            spec = None
        if spec:
            new_font = _scaled_font(spec, family, float(scale))
            if new_font:
                try:
                    widget.configure(font=new_font)
                except tk.TclError:
                    pass

    if isinstance(widget, tk.Text):
        base_fonts = getattr(widget, "_base_tag_fonts", None)
        if base_fonts is None:
            base_fonts = {}
            widget._base_tag_fonts = base_fonts
        for tag in ("you", "jarvis", "sys"):
            try:
                spec = base_fonts.get(tag)
                if spec is None:
                    spec = widget.tag_cget(tag, "font")
                    base_fonts[tag] = spec
            except tk.TclError:
                continue
            if not spec:
                continue
            new_font = _scaled_font(spec, family, float(scale))
            if new_font:
                try:
                    widget.tag_configure(tag, font=new_font)
                except tk.TclError:
                    pass

    try:
        children = widget.winfo_children()
    except tk.TclError:
        return
    for child in children:
        apply_fonts(child, family, scale)


# ── кастомний код ────────────────────────────────────────────────────────────

_SAFE_BUILTIN_NAMES = (
    "abs", "all", "any", "bool", "dict", "enumerate", "Exception",
    "float", "format", "getattr", "hasattr", "int", "isinstance", "len",
    "list", "max", "min", "print", "range", "repr", "reversed", "round",
    "set", "setattr", "slice", "sorted", "str", "sum", "tuple", "type",
    "ValueError", "TypeError", "KeyError", "IndexError", "RuntimeError",
    "zip",
)
SAFE_BUILTINS: dict[str, Any] = {
    name: getattr(builtins, name) for name in _SAFE_BUILTIN_NAMES
}


def custom_code_namespace(
    parent: tk.Misc, colors: dict[str, str], root: tk.Misc | None = None
) -> dict[str, Any]:
    """Готує безпечний namespace для користувацького коду."""
    return {
        "__builtins__": dict(SAFE_BUILTINS),
        "tk": tk,
        "ttk": ttk,
        "parent": parent,
        "colors": dict(colors),
        "root": root or parent,
        "math": math,
    }


def render_custom_code(
    code: str,
    parent: tk.Misc,
    colors: dict[str, str],
    root: tk.Misc | None = None,
) -> tk.Widget | None:
    """
    Виконує код у ``parent``.

    Контракт: код може створити віджети безпосередньо в ``parent`` або
    визначити ``build(parent, colors)``, який повертає віджет.
    Винятки пробрасуються назовні, щоб діалог показав помилку.
    """
    for child in parent.winfo_children():
        child.destroy()
    source = str(code or "").strip()
    if not source:
        return None
    namespace = custom_code_namespace(parent, colors, root)
    exec(compile(source, "<jarvis-custom>", "exec"), namespace)  # noqa: S102
    builder = namespace.get("build")
    if callable(builder):
        result = builder(parent, colors)
        if isinstance(result, tk.Widget):
            result.pack(fill="both", expand=True)
            return result
    return None


__all__ = [
    "DEFAULT_CUSTOM_CODE",
    "DEFAULT_FONTS",
    "DEFAULT_LAYOUT",
    "DEFAULT_THEME",
    "MAIN_BLOCKS",
    "MAIN_BLOCK_LABELS",
    "PRESET_LABELS",
    "SIDEBAR_ITEMS",
    "SIDEBAR_LABELS",
    "THEME_LABELS",
    "THEME_PRESETS",
    "apply_fonts",
    "apply_theme",
    "blend",
    "default_customization",
    "derive_theme",
    "load_customization",
    "normalize_color",
    "normalize_customization",
    "render_custom_code",
    "save_customization",
]
