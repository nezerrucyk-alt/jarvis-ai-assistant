# -*- coding: utf-8 -*-
"""
J.A.R.V.I.S. — графічний редактор кастомізації Command Deck.

Вікно дозволяє без редагування файлів змінювати:

* кольори всіх ролей теми та готові пресети;
* родину й масштаб шрифтів;
* видимість і порядок блоків головної області та бокової панелі;
* анімації, плавну появу вікна, ефект друку й компактний режим;
* власний Tkinter-код із живим прев'ю;
* всю конфігурацію через JSON (імпорт / експорт).

Діалог не зберігає нічого сам: він передає дані застосунку через
``preview_customization`` та ``apply_customization_data``. Це дозволяє
показувати зміни в реальному часі й коректно відкочувати їх при закритті.
"""

from __future__ import annotations

import json
import logging
import math
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk
from typing import Any

from core.customization import (
    DEFAULT_CUSTOM_CODE,
    MAIN_BLOCK_LABELS,
    MAIN_BLOCKS,
    PRESET_LABELS,
    SIDEBAR_ITEMS,
    SIDEBAR_LABELS,
    THEME_LABELS,
    THEME_PRESETS,
    default_customization,
    derive_theme,
    normalize_color,
    normalize_customization,
    render_custom_code,
)

logger = logging.getLogger("Jarvis.Customize")


class CustomizeDialog:
    """Окреме вікно кастомізації, прив'язане до ``JarvisApp``."""

    PAGE_LABELS = (
        ("theme", "ТЕМА"),
        ("layout", "МАКЕТ"),
        ("code", "КОД"),
        ("animations", "АНІМАЦІЇ"),
        ("json", "JSON"),
    )

    def __init__(self, app) -> None:
        self.app = app
        self.original = normalize_customization(
            getattr(app, "customization", {}) or {}
        )
        self.data = normalize_customization(self.original)
        self.theme = derive_theme(self.data.get("theme"))
        self.dirty = False
        self._closed = False
        self._live_job: str | None = None
        self._code_job: str | None = None
        self._anim_job: str | None = None
        self._anim_t = 0.0
        self._active_page = "theme"
        self._json_dirty = False

        self._ttk_style = ttk.Style(app.root)
        try:
            self._ttk_theme = self._ttk_style.theme_use()
        except tk.TclError:
            self._ttk_theme = None
        try:
            self._ttk_style.theme_use("clam")
        except tk.TclError:
            pass

        self.bg = self.theme["bg"]
        self.panel = self.theme["panel"]
        self.panel_alt = self.theme["panel_alt"]
        self.line = self.theme["line"]
        self.accent = self.theme["accent"]
        self.accent_dim = self.theme["accent_dim"]
        self.text = self.theme["text"]
        self.muted = self.theme["muted"]
        self.green = self.theme["green"]
        self.red = self.theme["red"]

        self._build()
        self._load_data_into_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(60, self._animate_demo)

    # ── побудова вікна ───────────────────────────────────────────────────────
    def _build(self) -> None:
        self.root = tk.Toplevel(self.app.root)
        self.root.title("Кастомізація J.A.R.V.I.S.")
        self.root.geometry("1120x780")
        self.root.minsize(900, 640)
        self.root.configure(bg=self.bg)
        self.root.transient(self.app.root)
        try:
            self.root.grab_set()
        except tk.TclError:
            pass
        # Діалог має власну палітру й не перефарбовується разом із JARVIS.
        self.root._theme_skip = True
        self.root._font_skip = True

        header = tk.Frame(self.root, bg=self.bg)
        header.pack(fill="x", padx=22, pady=(16, 6))
        tk.Label(
            header, text="✦  КАСТОМІЗАЦІЯ", bg=self.bg, fg=self.accent_dim,
            font=("Consolas", 10, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header,
            text=(
                "Тема, шрифти, макет, анімації та власний код — "
                "без редагування файлів. Зміни зберігаються у "
                "customization.json."
            ),
            bg=self.bg, fg=self.muted, font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(3, 0))

        tabs = tk.Frame(self.root, bg=self.bg)
        tabs.pack(fill="x", padx=22, pady=(8, 0))
        self.tab_buttons: dict[str, tk.Button] = {}
        for key, label in self.PAGE_LABELS:
            button = tk.Button(
                tabs, text=label, command=lambda k=key: self._show_page(k),
                bg=self.bg, fg=self.muted, activebackground=self.panel_alt,
                activeforeground=self.accent, relief="flat", bd=0,
                font=("Consolas", 8, "bold"), padx=14, pady=7,
                cursor="hand2", highlightthickness=0,
            )
            button.pack(side="left", padx=(0, 4))
            self.tab_buttons[key] = button

        tk.Frame(self.root, bg=self.line, height=1).pack(
            fill="x", padx=22, pady=(8, 0)
        )

        self._build_footer()

        self.pages_host = tk.Frame(self.root, bg=self.bg)
        self.pages_host.pack(fill="both", expand=True, padx=22, pady=(10, 0))
        self.pages: dict[str, tk.Frame] = {}
        for key, _label in self.PAGE_LABELS:
            page = tk.Frame(self.pages_host, bg=self.bg)
            self.pages[key] = page
        self._build_theme_page(self.pages["theme"])
        self._build_layout_page(self.pages["layout"])
        self._build_code_page(self.pages["code"])
        self._build_animations_page(self.pages["animations"])
        self._build_json_page(self.pages["json"])
        self._show_page("theme")

    def _build_footer(self) -> None:
        footer = tk.Frame(self.root, bg=self.bg)
        footer.pack(side="bottom", fill="x", padx=22, pady=14)
        tk.Frame(self.root, bg=self.line, height=1).pack(
            side="bottom", fill="x", padx=22
        )
        self.status_label = tk.Label(
            footer, text="Готово", bg=self.bg, fg=self.muted,
            font=("Segoe UI", 8), anchor="w",
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        tk.Button(
            footer, text="СКАСУВАТИ", command=self._cancel,
            bg=self.panel, fg=self.muted, activebackground=self.panel_alt,
            activeforeground=self.text, relief="flat", bd=0,
            font=("Consolas", 8, "bold"), padx=14, pady=8, cursor="hand2",
        ).pack(side="right", padx=(8, 0))
        tk.Button(
            footer, text="ЗБЕРЕГТИ Й ЗАСТОСУВАТИ", command=self._save,
            bg=self.accent, fg=self.bg, activebackground=self.accent_dim,
            activeforeground=self.bg, relief="flat", bd=0,
            font=("Consolas", 8, "bold"), padx=18, pady=8, cursor="hand2",
        ).pack(side="right", padx=(8, 0))
        tk.Button(
            footer, text="ЗАКРИТИ", command=self.close,
            bg=self.bg, fg=self.muted, activebackground=self.panel,
            activeforeground=self.text, relief="flat", bd=0,
            font=("Consolas", 8), padx=12, pady=8, cursor="hand2",
        ).pack(side="right")

    def _scrollable(self, parent: tk.Misc) -> tk.Frame:
        shell = tk.Frame(parent, bg=self.bg)
        shell.pack(fill="both", expand=True)
        canvas = tk.Canvas(shell, bg=self.bg, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=self.bg)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def sync(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(window_id, width=canvas.winfo_width())

        def wheel(event) -> None:
            canvas.yview_scroll(-3 if event.delta > 0 else 3, "units")

        inner.bind("<Configure>", sync)
        canvas.bind("<Configure>", sync)
        canvas.bind(
            "<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", wheel)
        )
        canvas.bind(
            "<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>")
        )
        self.root.bind(
            "<Destroy>",
            lambda _e: canvas.unbind_all("<MouseWheel>"),
            add="+",
        )
        return inner

    def _card(self, parent: tk.Misc, title: str = "") -> tk.Frame:
        card = tk.Frame(
            parent, bg=self.panel, highlightthickness=1,
            highlightbackground=self.line,
        )
        if title:
            tk.Label(
                card, text=title, bg=self.panel, fg=self.accent_dim,
                font=("Consolas", 8, "bold"), anchor="w",
            ).pack(fill="x", padx=14, pady=(10, 4))
        return card

    # ── тема ─────────────────────────────────────────────────────────────────
    def _build_theme_page(self, page: tk.Frame) -> None:
        inner = self._scrollable(page)

        presets = tk.Frame(inner, bg=self.bg)
        presets.pack(fill="x", pady=(0, 10))
        tk.Label(
            presets, text="ПРЕСЕТИ", bg=self.bg, fg=self.muted,
            font=("Consolas", 8, "bold"),
        ).pack(side="left", padx=(0, 10))
        for key, label in PRESET_LABELS.items():
            colors = THEME_PRESETS.get(key, {})
            button = tk.Button(
                presets, text=label,
                command=lambda k=key: self._apply_preset(k),
                bg=colors.get("panel", self.panel),
                fg=colors.get("text", self.text),
                activebackground=colors.get("accent", self.accent),
                activeforeground=colors.get("bg", self.bg),
                relief="flat", bd=0, font=("Segoe UI", 8),
                padx=10, pady=5, cursor="hand2",
            )
            button.pack(side="left", padx=(0, 5))

        body = tk.Frame(inner, bg=self.bg)
        body.pack(fill="both", expand=True)
        left = self._card(body, "КОЛЬОРИ ТЕМИ")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right = tk.Frame(body, bg=self.bg)
        right.pack(side="left", fill="both", expand=True)

        self._color_vars: dict[str, tk.StringVar] = {}
        self._swatch_buttons: dict[str, tk.Button] = {}
        for role, label in THEME_LABELS.items():
            row = tk.Frame(left, bg=self.panel)
            row.pack(fill="x", padx=12, pady=3)
            tk.Label(
                row, text=label, bg=self.panel, fg=self.text,
                font=("Segoe UI", 9), anchor="w", width=24,
            ).pack(side="left")
            variable = tk.StringVar(value=self.data["theme"].get(role, ""))
            self._color_vars[role] = variable
            entry = tk.Entry(
                row, textvariable=variable, width=10, bg=self.panel_alt,
                fg=self.text, insertbackground=self.accent, relief="flat",
                font=("Consolas", 9), justify="center",
            )
            entry.pack(side="right", padx=(6, 0), ipady=3)
            entry.bind("<Return>", lambda _e, r=role: self._on_color_entry(r))
            entry.bind("<FocusOut>", lambda _e, r=role: self._on_color_entry(r))
            swatch = tk.Button(
                row, text="", width=4,
                command=lambda r=role: self._choose_color(r),
                bg=self.data["theme"].get(role, self.panel),
                activebackground=self.data["theme"].get(role, self.panel),
                relief="flat", bd=1, cursor="hand2",
            )
            swatch.pack(side="right", padx=(6, 0), ipady=2)
            self._swatch_buttons[role] = swatch

        tk.Label(
            left,
            text=(
                "Клікни на кольоровий квадрат, щоб відкрити палітру. "
                "Hex-код можна вписати вручну."
            ),
            bg=self.panel, fg=self.muted, font=("Segoe UI", 8),
            justify="left", wraplength=460,
        ).pack(anchor="w", padx=14, pady=(8, 12))

        preview = self._card(right, "ЖИВИЙ ПЕРЕГЛЯД")
        preview.pack(fill="x")
        preview_body = tk.Frame(preview, bg=self.panel)
        preview_body.pack(fill="x", padx=14, pady=(2, 12))
        self.preview_canvas = tk.Canvas(
            preview_body, width=74, height=74, bg=self.bg,
            highlightthickness=0, bd=0,
        )
        self.preview_canvas.pack(side="left", padx=(0, 12))
        preview_text = tk.Frame(preview_body, bg=self.panel)
        preview_text.pack(side="left", fill="x", expand=True)
        self.preview_title = tk.Label(
            preview_text, text="J.A.R.V.I.S.  /  COMMAND DECK",
            bg=self.panel, fg=self.accent_dim, font=("Consolas", 7, "bold"),
        )
        self.preview_title.pack(anchor="w")
        self.preview_hero = tk.Label(
            preview_text, text="Чим допомогти, сер?", bg=self.panel,
            fg=self.text, font=("Segoe UI", 14, "bold"),
        )
        self.preview_hero.pack(anchor="w", pady=(2, 1))
        self.preview_body = tk.Label(
            preview_text,
            text="Голос, чат, ПК, Roblox Studio і багато моделей.",
            bg=self.panel, fg=self.muted, font=("Segoe UI", 8),
        )
        self.preview_body.pack(anchor="w")
        self.preview_button = tk.Button(
            preview_text, text="КОМАНДНИЙ РЯДОК", bg=self.accent,
            fg=self.bg, activebackground=self.accent_dim,
            activeforeground=self.bg, relief="flat", bd=0,
            font=("Consolas", 7, "bold"), padx=10, pady=4,
        )
        self.preview_button.pack(anchor="w", pady=(7, 0))
        self.preview_line = tk.Frame(preview, bg=self.line, height=2)
        self.preview_line.pack(fill="x", padx=14, pady=(0, 10))

        fonts = self._card(right, "ШРИФТИ")
        fonts.pack(fill="x", pady=(10, 0))
        font_row = tk.Frame(fonts, bg=self.panel)
        font_row.pack(fill="x", padx=14, pady=(2, 6))
        tk.Label(
            font_row, text="Родина", bg=self.panel, fg=self.text,
            font=("Segoe UI", 9), width=10, anchor="w",
        ).pack(side="left")
        families = sorted(
            {str(name) for name in tkfont.families(self.root) if str(name)},
            key=str.lower,
        )
        self.font_family_var = tk.StringVar()
        style = ttk.Style(self.root)
        style.configure(
            "Jarvis.TCombobox",
            fieldbackground=self.panel_alt,
            background=self.panel_alt,
            foreground=self.text,
            arrowcolor=self.accent,
            bordercolor=self.line,
            lightcolor=self.line,
            darkcolor=self.line,
            selectbackground=self.panel_alt,
            selectforeground=self.text,
        )
        style.map(
            "Jarvis.TCombobox",
            fieldbackground=[("readonly", self.panel_alt)],
            foreground=[("readonly", self.text)],
            background=[("active", self.panel_alt)],
        )
        style.configure(
            "TScrollbar",
            background=self.panel_alt,
            troughcolor=self.bg,
            arrowcolor=self.muted,
            bordercolor=self.line,
            lightcolor=self.panel_alt,
            darkcolor=self.panel_alt,
        )
        style.map(
            "TScrollbar",
            background=[("active", self.line)],
            arrowcolor=[("active", self.accent)],
        )
        self.font_family_combo = ttk.Combobox(
            font_row, textvariable=self.font_family_var,
            values=["За замовчуванням", *families],
            state="readonly", font=("Segoe UI", 9),
            style="Jarvis.TCombobox",
        )
        self.font_family_combo.pack(side="left", fill="x", expand=True)
        self.font_family_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self._on_font_change()
        )

        scale_row = tk.Frame(fonts, bg=self.panel)
        scale_row.pack(fill="x", padx=14, pady=(0, 2))
        tk.Label(
            scale_row, text="Масштаб", bg=self.panel, fg=self.text,
            font=("Segoe UI", 9), width=10, anchor="w",
        ).pack(side="left")
        self.font_scale_var = tk.DoubleVar(value=1.0)
        self.font_scale_canvas = tk.Canvas(
            scale_row, height=24, bg=self.panel, highlightthickness=0, bd=0,
            cursor="hand2",
        )
        self.font_scale_canvas.pack(side="left", fill="x", expand=True)
        self.font_scale_canvas.bind(
            "<Configure>", lambda _e: self._draw_font_slider()
        )
        self.font_scale_canvas.bind("<Button-1>", self._on_slider_press)
        self.font_scale_canvas.bind("<B1-Motion>", self._on_slider_press)
        self.font_scale_label = tk.Label(
            scale_row, text="100%", bg=self.panel, fg=self.accent_dim,
            font=("Consolas", 8), width=6, anchor="e",
        )
        self.font_scale_label.pack(side="right")
        self.font_sample = tk.Label(
            fonts, text="J.A.R.V.I.S. — Приклад тексту 0123456789",
            bg=self.panel, fg=self.text, font=("Segoe UI", 11),
            anchor="w",
        )
        self.font_sample.pack(fill="x", padx=14, pady=(6, 4))
        tk.Label(
            fonts,
            text="Шрифт застосовується до всього Command Deck.",
            bg=self.panel, fg=self.muted, font=("Segoe UI", 8),
        ).pack(anchor="w", padx=14, pady=(0, 12))

        tips = self._card(right, "ЩО МОЖНА ЗМІНИТИ")
        tips.pack(fill="x", pady=(10, 0))
        for line in (
            "12 кольорів теми та 6 готових пресетів",
            "родину й масштаб шрифтів усього інтерфейсу",
            "видимість і порядок блоків головної області",
            "порядок і видимість пунктів бокової панелі",
            "анімації, появу вікна, друк і компактний режим",
            "власний Tkinter-код із живим прев'ю",
        ):
            tk.Label(
                tips, text=f"•  {line}", bg=self.panel, fg=self.muted,
                font=("Segoe UI", 8), anchor="w",
            ).pack(fill="x", padx=14, pady=1)
        tk.Frame(tips, bg=self.panel, height=8).pack()

        live_row = tk.Frame(inner, bg=self.bg)
        live_row.pack(fill="x", pady=(10, 0))
        self.live_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            live_row, text="Живий перегляд у JARVIS (без збереження)",
            variable=self.live_var, command=self._on_live_toggle,
            bg=self.bg, fg=self.muted, selectcolor=self.panel_alt,
            activebackground=self.bg, activeforeground=self.accent,
            font=("Segoe UI", 8), anchor="w",
        ).pack(side="left")

    def _apply_preset(self, key: str) -> None:
        preset = THEME_PRESETS.get(key)
        if not preset:
            return
        self.data["theme"].update(preset)
        self.theme = derive_theme(self.data["theme"])
        self._refresh_theme_page()
        self._mark_dirty()
        self._live_apply()

    def _choose_color(self, role: str) -> None:
        _rgb, color = colorchooser.askcolor(
            color=self.data["theme"].get(role, "#000000"),
            parent=self.root,
            title=f"Колір: {THEME_LABELS.get(role, role)}",
        )
        if not color:
            return
        normalized = normalize_color(color)
        if not normalized:
            return
        self.data["theme"][role] = normalized
        self._color_vars[role].set(normalized)
        self.theme = derive_theme(self.data["theme"])
        self._refresh_theme_page()
        self._mark_dirty()
        self._live_apply()

    def _on_color_entry(self, role: str) -> None:
        variable = self._color_vars.get(role)
        if variable is None:
            return
        color = normalize_color(variable.get())
        if not color:
            variable.set(self.data["theme"].get(role, ""))
            self._set_status("Невірний hex-код. Приклад: #5B8CFF", self.red)
            return
        if self.data["theme"].get(role) == color:
            return
        self.data["theme"][role] = color
        self.theme = derive_theme(self.data["theme"])
        self._refresh_theme_page()
        self._mark_dirty()
        self._live_apply()

    def _refresh_theme_page(self) -> None:
        for role, variable in self._color_vars.items():
            color = self.data["theme"].get(role, "")
            variable.set(color)
            swatch = self._swatch_buttons.get(role)
            if swatch is not None:
                try:
                    swatch.configure(bg=color, activebackground=color)
                except tk.TclError:
                    pass
        self._refresh_preview()
        self._refresh_font_sample()

    def _refresh_preview(self) -> None:
        theme = self.theme
        try:
            self.preview_title.configure(
                bg=theme["panel"], fg=theme["accent_dim"]
            )
            self.preview_hero.configure(bg=theme["panel"], fg=theme["text"])
            self.preview_body.configure(bg=theme["panel"], fg=theme["muted"])
            self.preview_button.configure(
                bg=theme["accent"], fg=theme["bg"],
                activebackground=theme["accent_dim"],
                activeforeground=theme["bg"],
            )
            self.preview_line.configure(bg=theme["line"])
        except tk.TclError:
            return
        canvas = self.preview_canvas
        canvas.configure(bg=theme["bg"])
        canvas.delete("all")
        cx = cy = 37
        for radius, color in (
            (30, theme["ring_1"]),
            (23, theme["ring_2"]),
            (16, theme["ring_3"]),
        ):
            canvas.create_oval(
                cx - radius, cy - radius, cx + radius, cy + radius,
                outline=color, width=2,
            )
        canvas.create_oval(
            cx - 9, cy - 9, cx + 9, cy + 9,
            outline=theme["accent"], width=2,
        )
        canvas.create_oval(
            cx - 4, cy - 4, cx + 4, cy + 4,
            fill=theme["accent"], outline="",
        )

    def _draw_font_slider(self) -> None:
        canvas = getattr(self, "font_scale_canvas", None)
        if canvas is None:
            return
        try:
            width = max(80, canvas.winfo_width())
        except tk.TclError:
            return
        canvas.delete("all")
        y = 12
        x0, x1 = 10, width - 10
        canvas.create_rectangle(
            x0, y - 3, x1, y + 3, fill=self.panel_alt, outline=""
        )
        try:
            value = float(self.font_scale_var.get())
        except (TypeError, ValueError):
            value = 1.0
        ratio = max(0.0, min(1.0, (value - 0.75) / (1.4 - 0.75)))
        knob = x0 + ratio * (x1 - x0)
        canvas.create_rectangle(
            x0, y - 3, knob, y + 3, fill=self.accent, outline=""
        )
        canvas.create_oval(
            knob - 7, y - 7, knob + 7, y + 7,
            fill=self.accent_dim, outline=self.panel, width=2,
        )

    def _on_slider_press(self, event) -> None:
        canvas = self.font_scale_canvas
        width = max(80, canvas.winfo_width())
        x0, x1 = 10, width - 10
        ratio = (event.x - x0) / max(1, x1 - x0)
        ratio = max(0.0, min(1.0, ratio))
        value = 0.75 + ratio * (1.4 - 0.75)
        value = round(value / 0.05) * 0.05
        self.font_scale_var.set(round(value, 2))
        self._draw_font_slider()
        self._on_font_change()

    def _on_font_change(self) -> None:
        selected = self.font_family_var.get().strip()
        family = "" if selected in ("", "За замовчуванням") else selected
        try:
            scale = round(float(self.font_scale_var.get()), 2)
        except (TypeError, ValueError):
            scale = 1.0
        self.data["fonts"]["family"] = family
        self.data["fonts"]["scale"] = max(0.75, min(1.40, scale))
        self.font_scale_label.configure(
            text=f"{int(round(self.data['fonts']['scale'] * 100))}%"
        )
        self._draw_font_slider()
        self._refresh_font_sample()
        self._mark_dirty()
        self._live_apply()

    def _refresh_font_sample(self) -> None:
        family = self.data["fonts"].get("family") or "Segoe UI"
        scale = float(self.data["fonts"].get("scale") or 1.0)
        size = max(8, int(round(11 * scale)))
        try:
            self.font_sample.configure(font=(family, size))
        except tk.TclError:
            pass

    def _on_live_toggle(self) -> None:
        if self.live_var.get():
            self._live_apply()

    # ── макет ────────────────────────────────────────────────────────────────
    def _build_layout_page(self, page: tk.Frame) -> None:
        inner = self._scrollable(page)
        top = tk.Frame(inner, bg=self.bg)
        top.pack(fill="x", pady=(0, 10))
        self.sidebar_enabled_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            top, text="Показувати бокову панель", variable=self.sidebar_enabled_var,
            command=self._on_sidebar_enabled, bg=self.bg, fg=self.text,
            selectcolor=self.panel_alt, activebackground=self.bg,
            activeforeground=self.accent, font=("Segoe UI", 9), anchor="w",
        ).pack(side="left")
        self.compact_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            top, text="Компактний режим (без hero і футера)",
            variable=self.compact_var, command=self._on_compact,
            bg=self.bg, fg=self.text, selectcolor=self.panel_alt,
            activebackground=self.bg, activeforeground=self.accent,
            font=("Segoe UI", 9), anchor="w",
        ).pack(side="left", padx=(20, 0))
        tk.Button(
            top, text="СКИНУТИ МАКЕТ", command=self._reset_layout,
            bg=self.panel, fg=self.muted, activebackground=self.panel_alt,
            activeforeground=self.text, relief="flat", bd=0,
            font=("Consolas", 7, "bold"), padx=10, pady=5, cursor="hand2",
        ).pack(side="right")

        columns = tk.Frame(inner, bg=self.bg)
        columns.pack(fill="both", expand=True)
        main_card = self._card(columns, "ГОЛОВНІ БЛОКИ")
        main_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.main_list_frame = tk.Frame(main_card, bg=self.panel)
        self.main_list_frame.pack(fill="both", expand=True, padx=10, pady=(2, 10))
        tk.Label(
            main_card,
            text="Порядок зверху вниз. Стрілки змінюють позицію блоку.",
            bg=self.panel, fg=self.muted, font=("Segoe UI", 8),
        ).pack(anchor="w", padx=14, pady=(0, 10))

        side_card = self._card(columns, "БОКОВА ПАНЕЛЬ")
        side_card.pack(side="left", fill="both", expand=True)
        self.sidebar_list_frame = tk.Frame(side_card, bg=self.panel)
        self.sidebar_list_frame.pack(
            fill="both", expand=True, padx=10, pady=(2, 10)
        )
        tk.Label(
            side_card,
            text=(
                "Порядок діє в межах секцій CORE / SYSTEM / RECENT. "
                "Секції залишаються на своїх місцях."
            ),
            bg=self.panel, fg=self.muted, font=("Segoe UI", 8),
            justify="left", wraplength=420,
        ).pack(anchor="w", padx=14, pady=(0, 10))

    def _refresh_layout_rows(self) -> None:
        layout = self.data["layout"]
        self.sidebar_enabled_var.set(bool(layout.get("sidebar_enabled", True)))
        self.compact_var.set(bool(layout.get("compact", False)))

        self._main_vars: dict[str, tk.BooleanVar] = {}
        for child in self.main_list_frame.winfo_children():
            child.destroy()
        order = layout.get("main_order") or list(MAIN_BLOCKS)
        for index, key in enumerate(order):
            if key not in MAIN_BLOCKS:
                continue
            row = tk.Frame(self.main_list_frame, bg=self.panel)
            row.pack(fill="x", pady=2)
            variable = tk.BooleanVar(
                value=bool(layout.get("main_visible", {}).get(key, True))
            )
            self._main_vars[key] = variable
            tk.Checkbutton(
                row, text=MAIN_BLOCK_LABELS.get(key, key), variable=variable,
                command=lambda k=key: self._on_main_visibility(k),
                bg=self.panel, fg=self.text, selectcolor=self.panel_alt,
                activebackground=self.panel, activeforeground=self.accent,
                font=("Segoe UI", 9), anchor="w",
            ).pack(side="left", fill="x", expand=True)
            tk.Button(
                row, text="↑", command=lambda k=key: self._move_main(k, -1),
                state="normal" if index > 0 else "disabled",
                bg=self.panel, fg=self.muted, activebackground=self.panel_alt,
                activeforeground=self.accent, relief="flat", bd=0,
                font=("Segoe UI", 9), width=2, cursor="hand2",
            ).pack(side="right")
            tk.Button(
                row, text="↓",
                command=lambda k=key: self._move_main(k, 1),
                state="normal" if index < len(order) - 1 else "disabled",
                bg=self.panel, fg=self.muted, activebackground=self.panel_alt,
                activeforeground=self.accent, relief="flat", bd=0,
                font=("Segoe UI", 9), width=2, cursor="hand2",
            ).pack(side="right")

        self._sidebar_vars: dict[str, tk.BooleanVar] = {}
        for child in self.sidebar_list_frame.winfo_children():
            child.destroy()
        order = layout.get("sidebar_order") or list(SIDEBAR_ITEMS)
        for index, key in enumerate(order):
            if key not in SIDEBAR_ITEMS:
                continue
            row = tk.Frame(self.sidebar_list_frame, bg=self.panel)
            row.pack(fill="x", pady=2)
            variable = tk.BooleanVar(
                value=bool(layout.get("sidebar_visible", {}).get(key, True))
            )
            self._sidebar_vars[key] = variable
            tk.Checkbutton(
                row, text=SIDEBAR_LABELS.get(key, key), variable=variable,
                command=lambda k=key: self._on_sidebar_visibility(k),
                bg=self.panel, fg=self.text, selectcolor=self.panel_alt,
                activebackground=self.panel, activeforeground=self.accent,
                font=("Segoe UI", 9), anchor="w",
            ).pack(side="left", fill="x", expand=True)
            tk.Button(
                row, text="↑",
                command=lambda k=key: self._move_sidebar(k, -1),
                state="normal" if index > 0 else "disabled",
                bg=self.panel, fg=self.muted, activebackground=self.panel_alt,
                activeforeground=self.accent, relief="flat", bd=0,
                font=("Segoe UI", 9), width=2, cursor="hand2",
            ).pack(side="right")
            tk.Button(
                row, text="↓",
                command=lambda k=key: self._move_sidebar(k, 1),
                state="normal" if index < len(order) - 1 else "disabled",
                bg=self.panel, fg=self.muted, activebackground=self.panel_alt,
                activeforeground=self.accent, relief="flat", bd=0,
                font=("Segoe UI", 9), width=2, cursor="hand2",
            ).pack(side="right")

    def _on_main_visibility(self, key: str) -> None:
        variable = self._main_vars.get(key)
        if variable is None:
            return
        self.data["layout"].setdefault("main_visible", {})[key] = bool(
            variable.get()
        )
        self._mark_dirty()
        self._live_apply()

    def _on_sidebar_visibility(self, key: str) -> None:
        variable = self._sidebar_vars.get(key)
        if variable is None:
            return
        self.data["layout"].setdefault("sidebar_visible", {})[key] = bool(
            variable.get()
        )
        self._mark_dirty()
        self._live_apply()

    def _move_main(self, key: str, delta: int) -> None:
        order = self.data["layout"].setdefault(
            "main_order", list(MAIN_BLOCKS)
        )
        self._move_key(order, key, delta)
        self._refresh_layout_rows()
        self._mark_dirty()
        self._live_apply()

    def _move_sidebar(self, key: str, delta: int) -> None:
        order = self.data["layout"].setdefault(
            "sidebar_order", list(SIDEBAR_ITEMS)
        )
        self._move_key(order, key, delta)
        self._refresh_layout_rows()
        self._mark_dirty()
        self._live_apply()

    @staticmethod
    def _move_key(order: list[str], key: str, delta: int) -> None:
        try:
            index = order.index(key)
        except ValueError:
            return
        target = index + delta
        if 0 <= target < len(order):
            order[index], order[target] = order[target], order[index]

    def _on_sidebar_enabled(self) -> None:
        self.data["layout"]["sidebar_enabled"] = bool(
            self.sidebar_enabled_var.get()
        )
        self._mark_dirty()
        self._live_apply()

    def _on_compact(self) -> None:
        self.data["layout"]["compact"] = bool(self.compact_var.get())
        self._mark_dirty()
        self._live_apply()

    def _reset_layout(self) -> None:
        defaults = default_customization()["layout"]
        for key in (
            "main_order", "main_visible", "sidebar_enabled", "sidebar_order",
            "sidebar_visible", "compact",
        ):
            self.data["layout"][key] = defaults[key]
        self._refresh_layout_rows()
        self._mark_dirty()
        self._live_apply()

    # ── код ──────────────────────────────────────────────────────────────────
    def _build_code_page(self, page: tk.Frame) -> None:
        body = tk.Frame(page, bg=self.bg)
        body.pack(fill="both", expand=True)

        left = self._card(body, "РЕДАКТОР КОДУ")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        editor_shell = tk.Frame(left, bg=self.panel)
        editor_shell.pack(fill="both", expand=True, padx=12, pady=(2, 8))
        self.code_text = tk.Text(
            editor_shell, bg=self.panel_alt, fg=self.text,
            insertbackground=self.accent, selectbackground=self.accent,
            selectforeground=self.bg, relief="flat", bd=0,
            font=("Consolas", 9), wrap="none", undo=True,
        )
        code_scroll = ttk.Scrollbar(
            editor_shell, orient="vertical", command=self.code_text.yview
        )
        self.code_text.configure(yscrollcommand=code_scroll.set)
        code_scroll.pack(side="right", fill="y")
        self.code_text.pack(side="left", fill="both", expand=True)
        self.code_text.bind("<KeyRelease>", self._schedule_code_preview)
        self.code_text.bind("<<Paste>>", self._schedule_code_preview)

        code_buttons = tk.Frame(left, bg=self.panel)
        code_buttons.pack(fill="x", padx=12, pady=(0, 6))
        for label, command in (
            ("ПРИКЛАД", self._insert_example),
            ("ОЧИСТИТИ", self._clear_code),
            ("ПРЕВ'Ю", self._refresh_code_preview),
        ):
            tk.Button(
                code_buttons, text=label, command=command,
                bg=self.panel_alt, fg=self.muted,
                activebackground=self.line, activeforeground=self.accent,
                relief="flat", bd=0, font=("Consolas", 7, "bold"),
                padx=9, pady=5, cursor="hand2",
            ).pack(side="left", padx=(0, 5))
        self.code_enabled_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            code_buttons, text="Увімкнути в JARVIS",
            variable=self.code_enabled_var, command=self._on_code_enabled,
            bg=self.panel, fg=self.text, selectcolor=self.panel_alt,
            activebackground=self.panel, activeforeground=self.accent,
            font=("Segoe UI", 8),
        ).pack(side="right")
        tk.Label(
            left,
            text=(
                "Код виконується локально з обмеженими builtins. Це захист "
                "від випадкових помилок, а не повна пісочниця: не вставляй "
                "чужий код без перевірки."
            ),
            bg=self.panel, fg=self.muted, font=("Segoe UI", 8),
            justify="left", wraplength=520,
        ).pack(anchor="w", padx=14, pady=(0, 10))

        right = tk.Frame(body, bg=self.bg)
        right.pack(side="left", fill="both", expand=True)
        preview_card = self._card(right, "ПОПЕРЕДНІЙ ПЕРЕГЛЯД")
        preview_card.pack(fill="both", expand=True)
        self.code_preview = tk.Frame(
            preview_card, bg=self.panel, highlightthickness=1,
            highlightbackground=self.line,
        )
        self.code_preview.pack(fill="both", expand=True, padx=12, pady=(2, 8))
        self.code_preview._theme_skip = True
        self.code_preview._font_skip = True
        self.code_status = tk.Label(
            preview_card, text="Прев'ю оновлюється автоматично.",
            bg=self.panel, fg=self.muted, font=("Segoe UI", 8), anchor="w",
        )
        self.code_status.pack(fill="x", padx=14, pady=(0, 10))

    def _insert_example(self) -> None:
        self.code_text.delete("1.0", "end")
        self.code_text.insert("1.0", DEFAULT_CUSTOM_CODE)
        self._schedule_code_preview()

    def _clear_code(self) -> None:
        self.code_text.delete("1.0", "end")
        self._refresh_code_preview()

    def _on_code_enabled(self) -> None:
        self.data["custom_code_enabled"] = bool(self.code_enabled_var.get())
        self._mark_dirty()
        self._live_apply()

    def _schedule_code_preview(self, _event=None) -> None:
        if self._closed:
            return
        if self._code_job is not None:
            try:
                self.root.after_cancel(self._code_job)
            except tk.TclError:
                pass
        self._code_job = self.root.after(850, self._refresh_code_preview)

    def _refresh_code_preview(self) -> bool:
        if self._closed:
            return False
        self._code_job = None
        code = self.code_text.get("1.0", "end-1c")
        self.data["custom_code"] = code
        host = self.code_preview
        for child in host.winfo_children():
            child.destroy()
        if not code.strip():
            self.code_status.configure(
                text="Порожній код — блок буде приховано.", fg=self.muted
            )
            return True
        try:
            render_custom_code(code, host, self.theme, self.root)
        except Exception as exc:  # noqa: BLE001 — показуємо помилку користувачу
            for child in host.winfo_children():
                child.destroy()
            tk.Label(
                host, text=f"{type(exc).__name__}: {exc}",
                bg=self.panel, fg=self.red, font=("Consolas", 8),
                justify="left", anchor="nw", wraplength=440,
            ).pack(fill="both", expand=True, padx=10, pady=10)
            self.code_status.configure(text="Помилка у коді", fg=self.red)
            return False
        self.code_status.configure(text="Прев'ю оновлено", fg=self.green)
        return True

    # ── анімації ─────────────────────────────────────────────────────────────
    def _build_animations_page(self, page: tk.Frame) -> None:
        inner = self._scrollable(page)
        self.animation_vars: dict[str, tk.BooleanVar] = {}
        descriptions = {
            "animations": (
                "Головний перемикач",
                "Реактор, акцентна лінія та індикатор стану рухаються.",
            ),
            "window_fade": (
                "Плавна поява вікна",
                "JARVIS проявляється з прозорості під час запуску.",
            ),
            "typewriter": (
                "Ефект друку в чаті",
                "Нові повідомлення плавно з'являються замість різкого стрибка.",
            ),
            "reactor_glow": (
                "Світіння реактора",
                "Пульсація ядра та орбітальні частинки.",
            ),
            "compact": (
                "Компактний режим",
                "Приховує hero-блок і футер, залишаючи чат і командний рядок.",
            ),
        }
        for key, (title, description) in descriptions.items():
            card = self._card(inner)
            card.pack(fill="x", pady=(0, 8))
            row = tk.Frame(card, bg=self.panel)
            row.pack(fill="x", padx=14, pady=10)
            variable = tk.BooleanVar(
                value=bool(self.data["layout"].get(key, True))
            )
            self.animation_vars[key] = variable
            tk.Checkbutton(
                row, text=title, variable=variable,
                command=lambda k=key: self._on_animation_toggle(k),
                bg=self.panel, fg=self.text, selectcolor=self.panel_alt,
                activebackground=self.panel, activeforeground=self.accent,
                font=("Segoe UI", 10, "bold"), anchor="w",
            ).pack(anchor="w")
            tk.Label(
                row, text=description, bg=self.panel, fg=self.muted,
                font=("Segoe UI", 8), anchor="w",
            ).pack(anchor="w", padx=(24, 0), pady=(2, 0))

        demo_card = self._card(inner, "ДЕМО")
        demo_card.pack(fill="x", pady=(2, 0))
        self.anim_canvas = tk.Canvas(
            demo_card, height=90, bg=self.panel_alt,
            highlightthickness=0, bd=0,
        )
        self.anim_canvas.pack(fill="x", padx=14, pady=(2, 12))

    def _on_animation_toggle(self, key: str) -> None:
        variable = self.animation_vars.get(key)
        if variable is None:
            return
        self.data["layout"][key] = bool(variable.get())
        self._mark_dirty()
        self._live_apply()

    def _animate_demo(self) -> None:
        if self._closed:
            return
        self._anim_t += 0.06
        canvas = getattr(self, "anim_canvas", None)
        if canvas is not None:
            try:
                width = max(120, canvas.winfo_width())
                height = max(60, canvas.winfo_height())
                canvas.delete("all")
                enabled = bool(
                    self.data.get("layout", {}).get("animations", True)
                )
                phase = self._anim_t if enabled else 0.0
                cx = width / 2
                cy = height / 2
                for index, radius in enumerate((34, 25, 16)):
                    offset = (
                        math.sin(phase * 1.8 + index) * 4 if enabled else 0
                    )
                    canvas.create_oval(
                        cx - radius - offset, cy - radius - offset,
                        cx + radius + offset, cy + radius + offset,
                        outline=self.theme["accent_dim"]
                        if index == 0 else self.theme["line"],
                        width=2,
                    )
                core = 7 + (math.sin(phase * 3.2) * 2 if enabled else 0)
                canvas.create_oval(
                    cx - core, cy - core, cx + core, cy + core,
                    fill=self.theme["accent"], outline="",
                )
                canvas.create_text(
                    width - 14, 12, anchor="ne",
                    text="ANIMATIONS ON" if enabled else "ANIMATIONS OFF",
                    fill=self.theme["muted"], font=("Consolas", 7),
                )
            except tk.TclError:
                pass
        self._anim_job = self.root.after(50, self._animate_demo)

    # ── JSON ─────────────────────────────────────────────────────────────────
    def _build_json_page(self, page: tk.Frame) -> None:
        inner = self._scrollable(page)
        card = self._card(inner, "КОНФІГУРАЦІЯ JSON")
        card.pack(fill="both", expand=True)
        self.json_text = tk.Text(
            card, bg=self.panel_alt, fg=self.text, insertbackground=self.accent,
            selectbackground=self.accent, selectforeground=self.bg,
            relief="flat", bd=0, font=("Consolas", 8), wrap="none",
        )
        scroll = ttk.Scrollbar(
            card, orient="vertical", command=self.json_text.yview
        )
        self.json_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y", padx=(0, 12), pady=(2, 8))
        self.json_text.pack(
            side="left", fill="both", expand=True, padx=(12, 0), pady=(2, 8)
        )
        self.json_text.bind(
            "<KeyRelease>", lambda _e: setattr(self, "_json_dirty", True)
        )

        buttons = tk.Frame(inner, bg=self.bg)
        buttons.pack(fill="x", pady=(10, 0))
        for label, command in (
            ("ЗАСТОСУВАТИ JSON", self._apply_json_text),
            ("ІМПОРТ З ФАЙЛУ", self._import_json),
            ("ЕКСПОРТ У ФАЙЛ", self._export_json),
            ("СКИНУТИ ВСЕ", self._reset_all),
        ):
            tk.Button(
                buttons, text=label, command=command,
                bg=self.panel, fg=self.muted,
                activebackground=self.panel_alt, activeforeground=self.accent,
                relief="flat", bd=0, font=("Consolas", 7, "bold"),
                padx=12, pady=7, cursor="hand2",
            ).pack(side="left", padx=(0, 6))
        tk.Label(
            inner,
            text=(
                "JSON-редактор зручний для резервних копій і перенесення "
                "теми на інший ПК. Після «Застосувати JSON» натисни "
                "«Зберегти й застосувати»."
            ),
            bg=self.bg, fg=self.muted, font=("Segoe UI", 8),
            justify="left", wraplength=760,
        ).pack(anchor="w", pady=(10, 0))

    def _refresh_json_text(self) -> None:
        if not hasattr(self, "json_text"):
            return
        self.json_text.delete("1.0", "end")
        self.json_text.insert(
            "1.0", json.dumps(self.data, ensure_ascii=False, indent=2)
        )
        self._json_dirty = False

    def _apply_json_text(self) -> None:
        try:
            raw = json.loads(self.json_text.get("1.0", "end-1c"))
        except json.JSONDecodeError as exc:
            messagebox.showerror(
                "Кастомізація", f"Невалідний JSON:\n{exc}", parent=self.root
            )
            return
        self.data = normalize_customization(raw)
        self._load_data_into_ui()
        self._mark_dirty()
        self._live_apply()
        self._set_status("JSON застосовано до попереднього перегляду", self.green)

    def _import_json(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Імпорт кастомізації",
            filetypes=(("JSON", "*.json"), ("Усі файли", "*.*")),
        )
        if not path:
            return
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 — показуємо причину
            messagebox.showerror(
                "Кастомізація", f"Не вдалося прочитати файл:\n{exc}",
                parent=self.root,
            )
            return
        self.data = normalize_customization(raw)
        self._load_data_into_ui()
        self._mark_dirty()
        self._live_apply()
        self._set_status(f"Імпортовано: {Path(path).name}", self.green)

    def _export_json(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Експорт кастомізації",
            defaultextension=".json",
            initialfile="jarvis-customization.json",
            filetypes=(("JSON", "*.json"), ("Усі файли", "*.*")),
        )
        if not path:
            return
        try:
            Path(path).write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Кастомізація", f"Не вдалося зберегти файл:\n{exc}",
                parent=self.root,
            )
            return
        self._set_status(f"Експортовано: {Path(path).name}", self.green)

    def _reset_all(self) -> None:
        if not messagebox.askyesno(
            "Кастомізація",
            "Скинути тему, шрифти, макет, анімації та код до стандартних?",
            parent=self.root,
        ):
            return
        self.data = default_customization()
        self._load_data_into_ui()
        self._mark_dirty()
        self._live_apply()
        self._set_status("Стандартні налаштування відновлено", self.green)

    # ── службові методи ──────────────────────────────────────────────────────
    def _load_data_into_ui(self) -> None:
        self.theme = derive_theme(self.data.get("theme"))
        for role, variable in self._color_vars.items():
            variable.set(self.data["theme"].get(role, ""))
        family = self.data["fonts"].get("family") or "За замовчуванням"
        self.font_family_var.set(family)
        self.font_scale_var.set(float(self.data["fonts"].get("scale") or 1.0))
        self.font_scale_label.configure(
            text=f"{int(round(float(self.data['fonts'].get('scale') or 1.0) * 100))}%"
        )
        self._draw_font_slider()
        self.code_text.delete("1.0", "end")
        self.code_text.insert("1.0", str(self.data.get("custom_code") or ""))
        self.code_enabled_var.set(bool(self.data.get("custom_code_enabled")))
        self._refresh_layout_rows()
        for key, variable in self.animation_vars.items():
            variable.set(bool(self.data["layout"].get(key, True)))
        self._refresh_json_text()
        self._refresh_theme_page()
        self._refresh_code_preview()

    def _show_page(self, key: str) -> None:
        if key not in self.pages:
            return
        self._active_page = key
        for page_key, page in self.pages.items():
            try:
                page.pack_forget()
            except tk.TclError:
                pass
        self.pages[key].pack(fill="both", expand=True)
        for tab_key, button in self.tab_buttons.items():
            active = tab_key == key
            try:
                button.configure(
                    bg=self.panel if active else self.bg,
                    fg=self.accent if active else self.muted,
                )
            except tk.TclError:
                pass
        if key == "json" and not self._json_dirty:
            self._refresh_json_text()

    def _mark_dirty(self) -> None:
        self.dirty = True
        self._set_status("Є незбережені зміни", self.accent_dim)

    def _set_status(self, text: str, color: str | None = None) -> None:
        try:
            self.status_label.configure(text=text, fg=color or self.muted)
        except tk.TclError:
            pass

    def _live_apply(self) -> None:
        if not getattr(self, "live_var", None) or not self.live_var.get():
            return
        if self._closed:
            return
        if self._live_job is not None:
            try:
                self.root.after_cancel(self._live_job)
            except tk.TclError:
                pass
        self._live_job = self.root.after(90, self._do_live_apply)

    def _do_live_apply(self) -> None:
        self._live_job = None
        if self._closed:
            return
        try:
            self.app.preview_customization(self.data)
        except Exception:
            logger.exception("Живий перегляд кастомізації не вдався")

    def _save(self) -> None:
        self.data["custom_code"] = self.code_text.get("1.0", "end-1c")
        self.data["custom_code_enabled"] = bool(self.code_enabled_var.get())
        if self.data["custom_code_enabled"] and not self._refresh_code_preview():
            messagebox.showerror(
                "Кастомізація",
                "Кастомний код містить помилку. Виправ її або вимкни код "
                "перед збереженням.",
                parent=self.root,
            )
            return
        try:
            saved = self.app.apply_customization_data(self.data, persist=True)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Кастомізація", f"Не вдалося зберегти:\n{exc}",
                parent=self.root,
            )
            return
        self.data = normalize_customization(saved)
        self.original = normalize_customization(saved)
        self.dirty = False
        self._refresh_json_text()
        self._set_status("Збережено у customization.json", self.green)

    def _cancel(self) -> None:
        self._restore_original()
        self.dirty = False
        self._destroy()

    def _restore_original(self) -> None:
        try:
            self.app.preview_customization(self.original)
        except Exception:
            logger.exception("Не вдалося відкотити кастомізацію")

    def close(self) -> None:
        if self._closed:
            return
        if self.dirty:
            if not messagebox.askyesno(
                "Кастомізація",
                "Є незбережені зміни. Закрити без збереження?",
                parent=self.root,
            ):
                return
        self._restore_original()
        self._destroy()

    def _destroy(self) -> None:
        if self._closed:
            return
        self._closed = True
        for attribute in ("_live_job", "_code_job", "_anim_job"):
            job = getattr(self, attribute, None)
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
                setattr(self, attribute, None)
        try:
            self.root.grab_release()
        except tk.TclError:
            pass
        try:
            if getattr(self.app, "_customize_dialog", None) is self:
                self.app._customize_dialog = None
        except Exception:
            pass
        if self._ttk_theme:
            try:
                self._ttk_style.theme_use(self._ttk_theme)
            except tk.TclError:
                pass
        try:
            self.root.destroy()
        except tk.TclError:
            pass


__all__ = ["CustomizeDialog"]
