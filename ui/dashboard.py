# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — Dashboard GUI.
Cyberpunk Minimalist Interface: Black, Dark Gray, and Deep Red HUD styling.
"""

from __future__ import annotations
import logging
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

from ui.theme import (
    BG_DARK, BG_PANEL, BG_INPUT, BG_SIDEBAR, BORDER,
    RED_ACCENT, RED_GLOW, RED_DEEP, RED_MUTED,
    CYAN_STATUS, GOLD_WARN, GREEN_OK, GRAY_INACTIVE,
    TEXT_PRIMARY, TEXT_MUTED, TEXT_DIM,
    FONT_TITLE, FONT_SUBTITLE, FONT_BODY, FONT_MONO, FONT_BADGE,
)

logger = logging.getLogger("Jarvis.Dashboard")


class Dashboard:
    def __init__(
        self,
        root: tk.Tk,
        on_send_callback: Callable[[str], None],
        on_mic_callback: Optional[Callable[[], None]] = None,
        on_emergency_stop_callback: Optional[Callable[[], None]] = None,
        on_settings_callback: Optional[Callable[[], None]] = None,
    ):
        self.root = root
        self.on_send = on_send_callback
        self.on_mic = on_mic_callback
        self.on_emergency_stop = on_emergency_stop_callback
        self.on_settings = on_settings_callback

        self._ui_queue: queue.Queue = queue.Queue()
        self._is_busy = False
        self._destroyed = False
        self._after_id: Optional[str] = None

        self._init_window()
        self._build_layout()
        self._process_queue()

    def _init_window(self) -> None:
        self.root.title("J.A.R.V.I.S. ULTIMATE // Autonomous Command Center")
        self.root.geometry("1040x680")
        self.root.minsize(860, 560)
        self.root.configure(bg=BG_DARK)

    def _build_layout(self) -> None:
        # Main Layout Container
        self.mic_btn: Optional[tk.Button] = None
        self.main_container = tk.Frame(self.root, bg=BG_DARK)
        self.main_container.pack(fill="both", expand=True)

        # ── Sidebar (Left) ────────────────────────────────────────────────────
        self.sidebar = tk.Frame(self.main_container, bg=BG_SIDEBAR, width=240, bd=0)
        self.sidebar.pack(side="left", fill="y", padx=(0, 1))

        # Brand Title
        brand_frame = tk.Frame(self.sidebar, bg=BG_SIDEBAR, padx=16, pady=20)
        brand_frame.pack(fill="x")
        tk.Label(
            brand_frame, text="J.A.R.V.I.S.", font=FONT_TITLE, fg=RED_ACCENT, bg=BG_SIDEBAR
        ).pack(anchor="w")
        tk.Label(
            brand_frame, text="ULTIMATE · CORE v2.0", font=("Consolas", 8, "bold"), fg=TEXT_DIM, bg=BG_SIDEBAR
        ).pack(anchor="w")

        # Divider
        tk.Frame(self.sidebar, bg=BORDER, height=1).pack(fill="x", padx=12, pady=4)

        # Active Agents Section
        agents_frame = tk.Frame(self.sidebar, bg=BG_SIDEBAR, padx=16, pady=12)
        agents_frame.pack(fill="x")
        tk.Label(
            agents_frame, text="АКТИВНІ АГЕНТИ", font=("Segoe UI", 8, "bold"), fg=RED_GLOW, bg=BG_SIDEBAR
        ).pack(anchor="w", pady=(0, 8))

        self.agent_labels: dict[str, tk.Label] = {}
        agents_list = [
            ("Brain", "Головний мозок"),
            ("Coder", "Програміст"),
            ("System", "Керування ПК"),
            ("Roblox", "Roblox Studio"),
        ]
        for name, role in agents_list:
            row = tk.Frame(agents_frame, bg=BG_PANEL, padx=8, pady=6)
            row.pack(fill="x", pady=2)
            lbl = tk.Label(row, text="●", font=("Segoe UI", 8), fg=GREEN_OK, bg=BG_PANEL)
            lbl.pack(side="left", padx=(0, 6))
            tk.Label(row, text=name, font=FONT_SUBTITLE, fg=TEXT_PRIMARY, bg=BG_PANEL).pack(side="left")
            tk.Label(row, text=f"({role})", font=("Segoe UI", 8), fg=TEXT_DIM, bg=BG_PANEL).pack(side="left", padx=4)
            self.agent_labels[name.lower()] = lbl

        # System Metrics HUD
        metrics_frame = tk.Frame(self.sidebar, bg=BG_SIDEBAR, padx=16, pady=16)
        metrics_frame.pack(fill="x")
        tk.Label(
            metrics_frame, text="СИСТЕМА ТА РЕСУРСИ", font=("Segoe UI", 8, "bold"), fg=RED_GLOW, bg=BG_SIDEBAR
        ).pack(anchor="w", pady=(0, 6))

        self.ram_label = tk.Label(metrics_frame, text="RAM: Опитування...", font=FONT_MONO, fg=TEXT_MUTED, bg=BG_SIDEBAR)
        self.ram_label.pack(anchor="w")

        self.model_badge = tk.Label(metrics_frame, text="Модель: Groq OSS 20B", font=FONT_MONO, fg=CYAN_STATUS, bg=BG_SIDEBAR)
        self.model_badge.pack(anchor="w", pady=(4, 0))

        # Bottom Actions (Emergency Stop + Settings)
        bottom_frame = tk.Frame(self.sidebar, bg=BG_SIDEBAR, padx=16, pady=18)
        bottom_frame.pack(side="bottom", fill="x")

        self.btn_stop = tk.Button(
            bottom_frame,
            text="🚨 EMERGENCY STOP",
            font=FONT_BADGE,
            bg=RED_DEEP,
            fg=TEXT_PRIMARY,
            activebackground=RED_ACCENT,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=12,
            pady=8,
            command=self._handle_stop,
        )
        self.btn_stop.pack(fill="x", pady=(0, 8))

        if self.on_settings:
            btn_settings = tk.Button(
                bottom_frame,
                text="⚙ НАЛАШТУВАННЯ",
                font=("Segoe UI", 8, "bold"),
                bg=BG_PANEL,
                fg=TEXT_MUTED,
                activebackground=BORDER,
                relief="flat",
                bd=0,
                pady=6,
                command=self.on_settings,
            )
            btn_settings.pack(fill="x")

        # ── Main Content Area (Right) ─────────────────────────────────────────
        self.content_area = tk.Frame(self.main_container, bg=BG_DARK)
        self.content_area.pack(side="left", fill="both", expand=True)

        # Chat Log
        self.chat_container = tk.Frame(self.content_area, bg=BG_DARK, padx=18, pady=14)
        self.chat_container.pack(fill="both", expand=True)

        self.chat_text = tk.Text(
            self.chat_container,
            bg=BG_PANEL,
            fg=TEXT_PRIMARY,
            insertbackground=RED_ACCENT,
            relief="flat",
            bd=0,
            font=FONT_BODY,
            wrap="word",
            padx=14,
            pady=12,
        )
        self.chat_text.pack(fill="both", expand=True)
        self.chat_text.tag_configure("you", foreground=CYAN_STATUS, font=FONT_SUBTITLE)
        self.chat_text.tag_configure("jarvis", foreground=TEXT_PRIMARY)
        self.chat_text.tag_configure("agent", foreground=RED_ACCENT, font=FONT_SUBTITLE)
        self.chat_text.tag_configure("sys", foreground=GOLD_WARN, font=FONT_MONO)
        self.chat_text.config(state="disabled")

        # Input Area (Bottom)
        self.input_frame = tk.Frame(self.content_area, bg=BG_DARK, padx=18, pady=8)
        self.input_frame.pack(fill="x")

        self.input_box = tk.Frame(self.input_frame, bg=BG_INPUT, highlightbackground=BORDER, highlightthickness=1)
        self.input_box.pack(fill="x")

        self.entry = tk.Entry(
            self.input_box,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            insertbackground=RED_ACCENT,
            relief="flat",
            bd=0,
            font=FONT_BODY,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=12, pady=10)
        self.entry.bind("<Return>", lambda e: self._handle_send())

        if self.on_mic:
            self.mic_btn = tk.Button(
                self.input_box,
                text="🎙",
                font=("Segoe UI", 12),
                bg=BG_INPUT,
                fg=RED_ACCENT,
                activebackground=RED_MUTED,
                activeforeground=RED_ACCENT,
                relief="flat",
                bd=0,
                padx=10,
                command=self.on_mic,
            )
            self.mic_btn.pack(side="right")

        self.send_btn = tk.Button(
            self.input_box,
            text="НАДІСЛАТИ",
            font=FONT_BADGE,
            bg=RED_DEEP,
            fg=TEXT_PRIMARY,
            activebackground=RED_ACCENT,
            relief="flat",
            bd=0,
            padx=16,
            pady=8,
            command=self._handle_send,
        )
        self.send_btn.pack(side="right", padx=(0, 4))

    def _handle_send(self) -> None:
        text = self.entry.get().strip()
        if not text or self._is_busy:
            return
        self.entry.delete(0, tk.END)
        self.post_message("Ви", text, tag="you")
        self.set_busy(True)
        threading.Thread(target=self._run_send_worker, args=(text,), daemon=True).start()

    def _run_send_worker(self, text: str) -> None:
        try:
            self.on_send(text)
        finally:
            self._ui_queue.put(lambda: self.set_busy(False))

    def _handle_stop(self) -> None:
        """Передає натискання EMERGENCY STOP застосунку (він вирішує: стоп чи скидання)."""
        if self.on_emergency_stop:
            self.on_emergency_stop()
        else:
            self.post_message(
                "СИСТЕМА",
                "🚨 Активовано екстрену зупинку! Усі задачі зупинено.",
                tag="sys",
            )

    def post_message(self, sender: str, text: str, tag: str = "jarvis") -> None:
        def _append():
            self.chat_text.config(state="normal")
            self.chat_text.insert(tk.END, f"\n{sender}:\n", tag)
            self.chat_text.insert(tk.END, f"{text}\n\n", "jarvis" if tag in ("you", "agent") else tag)
            self.chat_text.see(tk.END)
            self.chat_text.config(state="disabled")

        self._ui_queue.put(_append)

    def set_busy(self, busy: bool) -> None:
        """Вмикає/вимикає стан «зайнято»; безпечно викликати з робочого потоку."""
        if threading.current_thread() is not threading.main_thread():
            self._ui_queue.put(lambda: self.set_busy(busy))
            return
        self._is_busy = busy
        state = "disabled" if busy else "normal"
        try:
            self.send_btn.config(state=state)
            if self.mic_btn is not None:
                self.mic_btn.config(state=state)
        except tk.TclError:
            logger.debug("Віджет уже знищено — стан «зайнято» не оновлено")

    def update_agent_status(self, name: str, active: bool) -> None:
        """Оновлює індикатор агента (можна викликати з будь-якого потоку)."""

        def _apply() -> None:
            label = self.agent_labels.get(name.lower())
            if label is not None:
                try:
                    label.config(fg=GREEN_OK if active else GRAY_INACTIVE)
                except tk.TclError:
                    pass

        self._ui_queue.put(_apply)

    def update_metrics(self, ram_text: str, model_text: str) -> None:
        """Оновлює HUD ресурсів (можна викликати з будь-якого потоку)."""

        def _apply() -> None:
            try:
                self.ram_label.config(text=ram_text)
                self.model_badge.config(text=model_text)
            except tk.TclError:
                pass

        self._ui_queue.put(_apply)

    def _process_queue(self) -> None:
        if self._destroyed:
            return
        try:
            while True:
                fn = self._ui_queue.get_nowait()
                try:
                    fn()
                except tk.TclError:
                    logger.debug("Віджет знищено під час обробки черги UI")
                except Exception:
                    logger.exception("Помилка обробника черги UI")
        except queue.Empty:
            pass
        try:
            self._after_id = self.root.after(30, self._process_queue)
        except tk.TclError:
            # Вікно вже закрите — черга більше не потрібна.
            self._after_id = None

    def stop(self) -> None:
        """Зупиняє періодичну обробку черги (викликається під час завершення)."""
        self._destroyed = True
        after_id = self._after_id
        self._after_id = None
        if after_id is not None:
            try:
                self.root.after_cancel(after_id)
            except tk.TclError:
                pass
