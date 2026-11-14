# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — вікно налаштувань модульного застосунку (v2).

Редагує ТОЙ САМИЙ файл, що й ``jarvis.py``:
``%APPDATA%\\Jarvis\\config.json`` — схема полів узгоджена з
:data:`core.config.DEFAULT_CONFIG` (модель, API-ключі всіх провайдерів,
мова, голос, режим доступу, параметри Roblox тощо).

Вікно не зберігає файл самостійно: воно збирає значення й передає їх
callback-у ``on_save(config)``, який вирішує, як записати конфігурацію.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Optional

from core.config import (
    CONFIG_PATH,
    LANGUAGES,
    MODEL_CHOICES,
    RESPONSE_MODES,
    VOICE_BY_LANG,
    VOICES,
)
from ui.theme import (
    BG_DARK,
    BG_INPUT,
    BG_PANEL,
    BG_SIDEBAR,
    BORDER,
    FONT_BADGE,
    FONT_BODY,
    FONT_MONO,
    FONT_TITLE,
    GOLD_WARN,
    GREEN_OK,
    RED_ACCENT,
    RED_DEEP,
    TEXT_DIM,
    TEXT_MUTED,
    TEXT_PRIMARY,
)

#: Поля API-ключів: (ключ у config.json, підпис у GUI).
KEY_FIELDS: tuple[tuple[str, str], ...] = (
    ("openrouter_key", "OpenRouter API-ключ"),
    ("xkiro_api_key", "xKiro API-ключ"),
    ("xkiro_backup_key", "xKiro резервний ключ"),
    ("groq_api_key", "Groq API-ключ"),
    ("gemini_api_key", "Gemini API-ключ"),
    ("deepseek_api_key", "DeepSeek API-ключ"),
    ("cerebras_api_key", "Cerebras API-ключ"),
    ("mistral_api_key", "Mistral API-ключ"),
    ("together_api_key", "Together API-ключ"),
    ("ashna_api_key", "Ashna API-ключ"),
    ("openai_api_key", "OpenAI API-ключ"),
    ("anthropic_api_key", "Anthropic API-ключ"),
    ("xai_api_key", "xAI (Grok) API-ключ"),
    ("moonshot_api_key", "Moonshot (Kimi) API-ключ"),
    ("qwen_api_key", "Qwen / DashScope API-ключ"),
    ("cursor_api_key", "Cursor API-ключ"),
    ("custom_api_key", "Свій провайдер · API-ключ"),
)

#: Поля свого OpenAI-сумісного провайдера (URL і модель не секретні).
CUSTOM_FIELDS: tuple[tuple[str, str], ...] = (
    ("custom_provider_name", "Назва"),
    ("custom_api_url", "URL · /v1/chat/completions"),
    ("custom_model", "Модель (напр. gpt-4o-mini)"),
)

RESPONSE_MODE_BY_LABEL: dict[str, str] = {
    label: key for key, label in RESPONSE_MODES.items()
}


class SettingsWindow:
    """Просте вікно редагування спільної конфігурації JARVIS."""

    def __init__(
        self,
        parent: tk.Misc,
        config: dict[str, Any],
        on_save: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> None:
        self.parent = parent
        self.config = dict(config or {})
        self.on_save = on_save
        self._key_vars: dict[str, tk.StringVar] = {}
        self._key_entries: list[tk.Entry] = []
        self._mode_labels = list(RESPONSE_MODES.values())
        self._mode_by_label = dict(RESPONSE_MODE_BY_LABEL)

        self.win = tk.Toplevel(parent)
        self.win.title("J.A.R.V.I.S. ULTIMATE · НАЛАШТУВАННЯ")
        self.win.configure(bg=BG_DARK)
        self.win.geometry("820x760")
        self.win.minsize(700, 560)
        try:
            self.win.transient(parent)
        except tk.TclError:
            pass
        self.win.protocol("WM_DELETE_WINDOW", self.destroy)
        self.win.bind("<Escape>", lambda _event: self.destroy())

        self._build()

    # ── побудова інтерфейсу ──────────────────────────────────────────────────
    def _build(self) -> None:
        header = tk.Frame(self.win, bg=BG_DARK, padx=18, pady=12)
        header.pack(fill="x")
        tk.Label(
            header,
            text="НАЛАШТУВАННЯ J.A.R.V.I.S.",
            font=FONT_TITLE,
            fg=RED_ACCENT,
            bg=BG_DARK,
        ).pack(anchor="w")
        tk.Label(
            header,
            text=str(CONFIG_PATH),
            font=FONT_MONO,
            fg=TEXT_DIM,
            bg=BG_DARK,
        ).pack(anchor="w")

        body_shell = tk.Frame(self.win, bg=BG_DARK)
        body_shell.pack(fill="both", expand=True)
        canvas = tk.Canvas(body_shell, bg=BG_DARK, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(body_shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        body = tk.Frame(canvas, bg=BG_DARK, padx=18)
        body_id = canvas.create_window((0, 0), window=body, anchor="nw")

        def sync_scroll(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(body_id, width=canvas.winfo_width())

        def on_wheel(event) -> None:
            canvas.yview_scroll(-3 if event.delta > 0 else 3, "units")

        body.bind("<Configure>", sync_scroll)
        canvas.bind("<Configure>", sync_scroll)
        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", on_wheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))
        self.win.bind(
            "<Destroy>", lambda _e: canvas.unbind_all("<MouseWheel>"), add="+"
        )

        # ── модель і мовлення ────────────────────────────────────────────────
        main_section = tk.Frame(body, bg=BG_SIDEBAR, padx=14, pady=10)
        main_section.pack(fill="x", pady=(0, 8))

        current_model = str(self.config.get("model") or "")
        model_choices = list(MODEL_CHOICES)
        if current_model and current_model not in model_choices:
            model_choices.insert(0, current_model)
        self._model_var = tk.StringVar(
            value=current_model or "deepseek-direct/deepseek-chat"
        )
        self._add_row(
            main_section,
            "Модель ШІ",
            lambda row: self._make_combo(row, model_choices, self._model_var, 54),
        )

        language = str(self.config.get("language") or "uk-UA")
        self._language_var = tk.StringVar(
            value=language if language in LANGUAGES else LANGUAGES[0]
        )
        self._add_row(
            main_section,
            "Мова інтерфейсу",
            lambda row: self._make_combo(
                row, list(LANGUAGES), self._language_var, 18, readonly=True
            ),
        )

        voice = str(self.config.get("voice") or VOICE_BY_LANG.get(language, VOICES[0]))
        self._voice_var = tk.StringVar(value=voice)
        self._add_row(
            main_section,
            "Голос Edge TTS",
            lambda row: self._make_combo(
                row, list(VOICES), self._voice_var, 32, readonly=True
            ),
        )

        mode = str(self.config.get("response_mode") or "natural")
        mode_label = RESPONSE_MODES.get(mode, RESPONSE_MODES["natural"])
        self._mode_var = tk.StringVar(value=mode_label)
        self._add_row(
            main_section,
            "Режим відповіді",
            lambda row: self._make_combo(
                row, self._mode_labels, self._mode_var, 24, readonly=True
            ),
        )

        self._max_history_var = tk.StringVar(
            value=str(self.config.get("max_history") or 12)
        )
        self._add_row(main_section, "Контекст", self._make_history_row)

        self._roblox_var = tk.StringVar(
            value=str(self.config.get("roblox_private_server") or "")
        )
        self._add_row(
            main_section,
            "Приватний сервер Roblox",
            lambda row: self._make_entry(row, self._roblox_var),
        )

        # ── прапорці поведінки ───────────────────────────────────────────────
        flags_frame = tk.Frame(body, bg=BG_PANEL, padx=12, pady=8)
        flags_frame.pack(fill="x", pady=(0, 8))
        self._mute_var = tk.BooleanVar(value=bool(self.config.get("mute")))
        self._full_access_var = tk.BooleanVar(
            value=bool(self.config.get("full_access", True))
        )
        self._always_on_top_var = tk.BooleanVar(
            value=bool(self.config.get("always_on_top"))
        )
        self._greet_var = tk.BooleanVar(value=bool(self.config.get("greet", True)))
        self._use_memory_var = tk.BooleanVar(
            value=bool(self.config.get("use_memory"))
        )
        for text, variable in (
            ("Без звуку (mute)", self._mute_var),
            ("Повний доступ до ПК", self._full_access_var),
            ("Вікно поверх інших", self._always_on_top_var),
            ("Вітатися під час запуску", self._greet_var),
            ("Передавати пам'ять моделі", self._use_memory_var),
        ):
            tk.Checkbutton(
                flags_frame,
                text=text,
                variable=variable,
                font=FONT_BODY,
                fg=TEXT_PRIMARY,
                bg=BG_PANEL,
                activebackground=BG_PANEL,
                activeforeground=RED_ACCENT,
                selectcolor=BG_DARK,
                highlightthickness=0,
                bd=0,
                anchor="w",
            ).pack(side="left", padx=(0, 14))

        # ── API-ключі ────────────────────────────────────────────────────────
        keys_header = tk.Frame(body, bg=BG_DARK)
        keys_header.pack(fill="x")
        tk.Label(
            keys_header,
            text="API-КЛЮЧІ ПРОВАЙДЕРІВ",
            font=FONT_BADGE,
            fg=GOLD_WARN,
            bg=BG_DARK,
        ).pack(side="left")
        self._show_keys_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            keys_header,
            text="Показати ключі",
            variable=self._show_keys_var,
            command=self._toggle_keys,
            font=("Segoe UI", 8),
            fg=TEXT_MUTED,
            bg=BG_DARK,
            activebackground=BG_DARK,
            activeforeground=RED_ACCENT,
            selectcolor=BG_DARK,
            highlightthickness=0,
            bd=0,
        ).pack(side="right")

        keys_frame = tk.Frame(body, bg=BG_PANEL, padx=10, pady=8)
        keys_frame.pack(fill="x", pady=(2, 8))
        keys_frame.columnconfigure(0, weight=1)
        keys_frame.columnconfigure(1, weight=1)

        def paste_key(entry: tk.Entry) -> None:
            try:
                value = self.win.clipboard_get().strip()
            except tk.TclError:
                return
            if not value:
                return
            if entry.selection_present():
                entry.delete("sel.first", "sel.last")
            entry.insert("insert", value)

        for index, (key, label) in enumerate(KEY_FIELDS):
            cell = tk.Frame(keys_frame, bg=BG_PANEL)
            cell.grid(row=index // 2, column=index % 2, sticky="ew", padx=4, pady=3)
            tk.Label(
                cell,
                text=label,
                font=("Segoe UI", 8),
                fg=TEXT_MUTED,
                bg=BG_PANEL,
                anchor="w",
            ).pack(fill="x")
            variable = tk.StringVar(value=str(self.config.get(key) or ""))
            row = tk.Frame(cell, bg=BG_PANEL)
            row.pack(fill="x")
            key_entry = tk.Entry(
                row,
                textvariable=variable,
                show="\u2022",
                bg=BG_INPUT,
                fg=TEXT_PRIMARY,
                insertbackground=RED_ACCENT,
                relief="flat",
                bd=0,
                font=FONT_MONO,
            )
            key_entry.pack(side="left", fill="x", expand=True, ipady=4)
            tk.Button(
                row,
                text="Вставити",
                command=lambda entry=key_entry: paste_key(entry),
                bg=BG_PANEL,
                fg=RED_ACCENT,
                activebackground=BORDER,
                activeforeground=TEXT_PRIMARY,
                relief="flat",
                bd=0,
                font=("Segoe UI", 7),
                padx=6,
            ).pack(side="left", padx=(4, 0))
            self._key_vars[key] = variable
            self._key_entries.append(key_entry)

        # ── свій OpenAI-сумісний провайдер ───────────────────────────────────
        tk.Label(
            body,
            text="СВІЙ OPENAI-СУМІСНИЙ ПРОВАЙДЕР",
            font=FONT_BADGE,
            fg=GOLD_WARN,
            bg=BG_DARK,
        ).pack(anchor="w", pady=(2, 2))
        custom_frame = tk.Frame(body, bg=BG_PANEL, padx=10, pady=8)
        custom_frame.pack(fill="x", pady=(0, 8))
        self._custom_vars: dict[str, tk.StringVar] = {}
        for field, label in CUSTOM_FIELDS:
            row = tk.Frame(custom_frame, bg=BG_PANEL)
            row.pack(fill="x", pady=2)
            tk.Label(
                row,
                text=label,
                width=30,
                anchor="w",
                font=("Segoe UI", 8),
                fg=TEXT_MUTED,
                bg=BG_PANEL,
            ).pack(side="left")
            variable = tk.StringVar(value=str(self.config.get(field) or ""))
            entry = tk.Entry(
                row,
                textvariable=variable,
                bg=BG_INPUT,
                fg=TEXT_PRIMARY,
                insertbackground=RED_ACCENT,
                relief="flat",
                bd=0,
                font=FONT_MONO,
            )
            entry.pack(side="left", fill="x", expand=True, ipady=4)
            self._custom_vars[field] = variable
        tk.Label(
            custom_frame,
            text="Щоб використати — вкажи модель як custom/<model> (напр. custom/gpt-4o-mini).",
            font=("Segoe UI", 8),
            fg=TEXT_DIM,
            bg=BG_PANEL,
        ).pack(anchor="w", pady=(3, 0))

        # ── нові можливості ─────────────────────────────────────────────────
        features_frame = tk.Frame(body, bg=BG_PANEL, padx=12, pady=8)
        features_frame.pack(fill="x", pady=(0, 8))
        self._clipboard_var = tk.BooleanVar(
            value=bool(self.config.get("clipboard_history", True))
        )
        self._watch_downloads_var = tk.BooleanVar(
            value=bool(self.config.get("watch_downloads"))
        )
        self._hud_var = tk.BooleanVar(value=bool(self.config.get("hud_enabled")))
        self._telegram_var = tk.BooleanVar(
            value=bool(self.config.get("telegram_enabled"))
        )
        for text, variable in (
            ("Історія буфера обміну", self._clipboard_var),
            ("Стежити за папкою «Завантаження»", self._watch_downloads_var),
            ("HUD-орб на екрані", self._hud_var),
            ("Telegram-бот", self._telegram_var),
        ):
            tk.Checkbutton(
                features_frame,
                text=text,
                variable=variable,
                font=FONT_BODY,
                fg=TEXT_PRIMARY,
                bg=BG_PANEL,
                activebackground=BG_PANEL,
                activeforeground=RED_ACCENT,
                selectcolor=BG_DARK,
                highlightthickness=0,
                bd=0,
                anchor="w",
            ).pack(side="left", padx=(0, 12))

        extra_frame = tk.Frame(body, bg=BG_PANEL, padx=10, pady=8)
        extra_frame.pack(fill="x", pady=(0, 8))
        self._telegram_token_var = tk.StringVar(
            value=str(self.config.get("telegram_token") or "")
        )
        self._telegram_chat_var = tk.StringVar(
            value=str(self.config.get("telegram_chat_id") or "")
        )
        self._briefing_city_var = tk.StringVar(
            value=str(self.config.get("briefing_city") or "Київ")
        )
        self._briefing_time_var = tk.StringVar(
            value=str(self.config.get("briefing_time") or "09:00")
        )
        for label, variable, secret in (
            ("Telegram · токен", self._telegram_token_var, True),
            ("Telegram · chat id", self._telegram_chat_var, False),
            ("Брифінг · місто", self._briefing_city_var, False),
            ("Брифінг · час", self._briefing_time_var, False),
        ):
            row = tk.Frame(extra_frame, bg=BG_PANEL)
            row.pack(fill="x", pady=2)
            tk.Label(
                row,
                text=label,
                width=30,
                anchor="w",
                font=("Segoe UI", 8),
                fg=TEXT_MUTED,
                bg=BG_PANEL,
            ).pack(side="left")
            entry = tk.Entry(
                row,
                textvariable=variable,
                show="\u2022" if secret else "",
                bg=BG_INPUT,
                fg=TEXT_PRIMARY,
                insertbackground=RED_ACCENT,
                relief="flat",
                bd=0,
                font=FONT_MONO,
            )
            entry.pack(side="left", fill="x", expand=True, ipady=4)
            if secret:
                self._key_entries.append(entry)

        # ── кнопки ───────────────────────────────────────────────────────────
        buttons = tk.Frame(self.win, bg=BG_DARK, padx=18, pady=12)
        buttons.pack(fill="x")
        tk.Button(
            buttons,
            text="ЗБЕРЕГТИ",
            font=FONT_BADGE,
            bg=RED_DEEP,
            fg=TEXT_PRIMARY,
            activebackground=RED_ACCENT,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=22,
            pady=8,
            command=self._save,
        ).pack(side="right")
        tk.Button(
            buttons,
            text="СКАСУВАТИ",
            font=FONT_BADGE,
            bg=BG_PANEL,
            fg=TEXT_MUTED,
            activebackground=BORDER,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            padx=16,
            pady=8,
            command=self.destroy,
        ).pack(side="right", padx=(0, 8))
        tk.Label(
            buttons,
            text="Зміни зберігаються у спільний config.json (v1 і v2).",
            font=("Segoe UI", 8),
            fg=GREEN_OK,
            bg=BG_DARK,
        ).pack(side="left")

    def _add_row(
        self,
        parent: tk.Frame,
        label: str,
        builder: Callable[[tk.Frame], tk.Widget],
    ) -> tk.Widget:
        """Додає рядок «підпис — віджет»; ``builder`` створює віджет у рядку."""
        row = tk.Frame(parent, bg=BG_SIDEBAR)
        row.pack(fill="x", pady=3)
        tk.Label(
            row,
            text=label,
            width=24,
            anchor="w",
            font=FONT_BODY,
            fg=TEXT_MUTED,
            bg=BG_SIDEBAR,
        ).pack(side="left")
        widget = builder(row)
        widget.pack(side="left", fill="x", expand=True)
        return widget

    def _make_combo(
        self,
        parent: tk.Frame,
        values: list[str],
        variable: tk.StringVar,
        width: int,
        readonly: bool = False,
    ) -> ttk.Combobox:
        combo = ttk.Combobox(
            parent,
            textvariable=variable,
            values=values,
            width=width,
            state="readonly" if readonly else "normal",
        )
        try:
            style = ttk.Style()
            style.configure(
                "TCombobox",
                fieldbackground=BG_INPUT,
                background=BG_PANEL,
                foreground=TEXT_PRIMARY,
            )
        except tk.TclError:
            pass
        return combo

    def _make_entry(self, parent: tk.Frame, variable: tk.StringVar) -> tk.Entry:
        return tk.Entry(
            parent,
            textvariable=variable,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            insertbackground=RED_ACCENT,
            relief="flat",
            bd=0,
            font=FONT_MONO,
        )

    def _make_history_row(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg=BG_SIDEBAR)
        entry = tk.Entry(
            frame,
            textvariable=self._max_history_var,
            width=8,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            insertbackground=RED_ACCENT,
            relief="flat",
            bd=0,
            font=FONT_MONO,
        )
        entry.pack(side="left", ipady=3)
        tk.Label(
            frame,
            text="  повідомлень історії (1–50)",
            font=("Segoe UI", 8),
            fg=TEXT_DIM,
            bg=BG_SIDEBAR,
        ).pack(side="left")
        return frame

    def _toggle_keys(self) -> None:
        show = "" if self._show_keys_var.get() else "\u2022"
        for entry in self._key_entries:
            try:
                entry.config(show=show)
            except tk.TclError:
                pass

    # ── збирання та збереження ───────────────────────────────────────────────
    def collect(self) -> dict[str, Any]:
        """Збирає відредаговану конфігурацію (зберігаючи невідомі ключі)."""
        config = dict(self.config)

        model = self._model_var.get().strip()
        if model:
            config["model"] = model

        config["language"] = self._language_var.get().strip() or "uk-UA"
        config["voice"] = self._voice_var.get().strip() or VOICE_BY_LANG.get(
            config["language"], VOICES[0]
        )
        config["response_mode"] = self._mode_by_label.get(
            self._mode_var.get().strip(), "natural"
        )
        try:
            history = int(self._max_history_var.get().strip())
        except (TypeError, ValueError):
            history = 12
        config["max_history"] = max(1, min(50, history))
        config["roblox_private_server"] = self._roblox_var.get().strip() or str(
            self.config.get("roblox_private_server") or ""
        )
        for key, _ in KEY_FIELDS:
            variable = self._key_vars.get(key)
            if variable is not None:
                config[key] = variable.get().strip()
        for field, _ in CUSTOM_FIELDS:
            variable = self._custom_vars.get(field)
            if variable is not None:
                config[field] = variable.get().strip()
        config["clipboard_history"] = bool(self._clipboard_var.get())
        config["watch_downloads"] = bool(self._watch_downloads_var.get())
        config["hud_enabled"] = bool(self._hud_var.get())
        config["telegram_enabled"] = bool(self._telegram_var.get())
        config["telegram_token"] = self._telegram_token_var.get().strip()
        config["telegram_chat_id"] = self._telegram_chat_var.get().strip()
        config["briefing_city"] = self._briefing_city_var.get().strip() or "Київ"
        config["briefing_time"] = self._briefing_time_var.get().strip() or "09:00"
        config["mute"] = bool(self._mute_var.get())
        config["full_access"] = bool(self._full_access_var.get())
        config["always_on_top"] = bool(self._always_on_top_var.get())
        config["greet"] = bool(self._greet_var.get())
        config["use_memory"] = bool(self._use_memory_var.get())
        return config

    def _save(self) -> None:
        try:
            new_config = self.collect()
            if self.on_save is not None:
                self.on_save(new_config)
        except Exception as exc:  # pragma: no cover — захист від збоїв UI
            try:
                messagebox.showerror(
                    "J.A.R.V.I.S.",
                    f"Не вдалося зберегти налаштування: {exc}",
                    parent=self.win,
                )
            except tk.TclError:
                pass
            return
        self.destroy()

    # ── закриття ─────────────────────────────────────────────────────────────
    def destroy(self) -> None:
        """Закриває вікно; безпечно викликати повторно."""
        try:
            self.win.grab_release()
        except tk.TclError:
            pass
        try:
            self.win.destroy()
        except tk.TclError:
            pass


__all__ = ["CUSTOM_FIELDS", "KEY_FIELDS", "RESPONSE_MODE_BY_LABEL", "SettingsWindow"]
