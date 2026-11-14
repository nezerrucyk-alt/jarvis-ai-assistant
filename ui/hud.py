# -*- coding: utf-8 -*-
"""Floating HUD orb for JARVIS.

A frameless, always-on-top window that mirrors the assistant state
(idle / listening / thinking / speaking) with a small animated reactor.
The module only depends on Tk and never touches application internals.
"""
from __future__ import annotations

import math
import tkinter as tk
from typing import Callable, Optional

STATE_COLORS: dict[str, str] = {
    "idle": "#2F6B86",
    "listening": "#3FD8FF",
    "thinking": "#FFC24D",
    "speaking": "#62F5A5",
}
SIZE = 152
_BG_KEY = "#010203"


def state_from_status(text: str) -> str:
    """Maps a human-readable status line to a HUD state."""
    value = str(text or "").casefold()
    if any(word in value for word in ("говор", "speak", "відповіда")):
        return "speaking"
    if any(word in value for word in ("дума", "аналіз", "оброб", "think", "сканую")):
        return "thinking"
    if any(word in value for word in ("слуха", "listen", "запис")):
        return "listening"
    return "idle"


class HudOrb:
    """Small transparent orb; drag with the mouse, double-click to focus Jarvis."""

    def __init__(self, root: tk.Misc, on_click: Optional[Callable[[], None]] = None) -> None:
        self.root = root
        self.on_click = on_click
        self.state = "idle"
        self._phase = 0.0
        self._job: Optional[str] = None
        self._drag: Optional[tuple[int, int]] = None

        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        try:
            self.win.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.win.configure(bg=_BG_KEY)
        try:
            self.win.attributes("-transparentcolor", _BG_KEY)
        except tk.TclError:
            pass

        screen_w = self.win.winfo_screenwidth()
        screen_h = self.win.winfo_screenheight()
        self.win.geometry(
            f"{SIZE}x{SIZE}+{max(0, screen_w - SIZE - 36)}+{max(0, screen_h - SIZE - 110)}"
        )

        self.canvas = tk.Canvas(
            self.win, width=SIZE, height=SIZE, bg=_BG_KEY,
            highlightthickness=0, bd=0, cursor="hand2",
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<Double-Button-1>", self._on_double)
        self._tick()

    # ── state ────────────────────────────────────────────────────────────────
    def set_state(self, state: str) -> None:
        self.state = state if state in STATE_COLORS else "idle"

    # ── dragging / click ─────────────────────────────────────────────────────
    def _on_press(self, event: tk.Event) -> None:
        self._drag = (
            event.x_root - self.win.winfo_x(),
            event.y_root - self.win.winfo_y(),
        )

    def _on_drag(self, event: tk.Event) -> None:
        if self._drag is None:
            return
        x = event.x_root - self._drag[0]
        y = event.y_root - self._drag[1]
        try:
            self.win.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    def _on_double(self, _event: tk.Event) -> None:
        if self.on_click is not None:
            try:
                self.on_click()
            except Exception:  # noqa: BLE001 — UI callback must not break the orb
                pass

    # ── animation ────────────────────────────────────────────────────────────
    def _tick(self) -> None:
        try:
            self._draw()
        except tk.TclError:
            return
        try:
            self._job = self.root.after(45, self._tick)
        except tk.TclError:
            self._job = None

    def _draw(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        color = STATE_COLORS.get(self.state, STATE_COLORS["idle"])
        center = SIZE / 2
        pulse = math.sin(self._phase) * 3.0
        base = SIZE * 0.30
        for index, factor in enumerate((1.0, 0.78, 0.55)):
            radius = base * factor + (pulse if index == 0 else 0.0)
            canvas.create_oval(
                center - radius, center - radius,
                center + radius, center + radius,
                outline=color, width=2 if index == 0 else 1,
            )
        if self.state == "thinking":
            radius = base + 6
            start = (self._phase * 55) % 360
            canvas.create_arc(
                center - radius, center - radius,
                center + radius, center + radius,
                start=start, extent=100, style="arc", outline=color, width=3,
            )
        if self.state == "listening":
            radius = base * 1.18 + pulse * 2
            canvas.create_oval(
                center - radius, center - radius,
                center + radius, center + radius,
                outline=color, width=1,
            )
        inner = 6 + (4 if self.state in ("listening", "speaking") else 1)
        canvas.create_oval(
            center - inner, center - inner,
            center + inner, center + inner,
            fill=color, outline="",
        )
        self._phase += 0.18

    # ── teardown ─────────────────────────────────────────────────────────────
    def destroy(self) -> None:
        if self._job is not None:
            try:
                self.root.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        try:
            self.win.destroy()
        except tk.TclError:
            pass


__all__ = ["HudOrb", "STATE_COLORS", "SIZE", "state_from_status"]
