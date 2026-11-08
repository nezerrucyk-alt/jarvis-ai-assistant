# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — головна точка входу модульної версії (v2).

Запуск: ``pythonw main.py`` (або ``Jarvis_Ultimate.bat``).

Що вміє цей застосунок:

* інтерфейс :class:`ui.dashboard.Dashboard` — чат, HUD ресурсів,
  EMERGENCY STOP, кнопка мікрофона та налаштувань;
* голосове введення: ``Dashboard → Ears.record/transcribe → Brain.process``;
* озвучення відповідей: :class:`modules.voice.Voice` (Edge TTS + резерв);
* швидкі дії на ПК через :class:`modules.computer_control.PcController`
  («відкрий youtube», «статус системи»);
* спільна конфігурація з ``jarvis.py``:
  ``%APPDATA%\\Jarvis\\config.json`` (редагується у вікні налаштувань).

Імпорт модуля не створює вікон, не пише у диск і не звертається до мережі —
уся ініціалізація відбувається у :func:`main` / :class:`JarvisUltimateApp`.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox
from typing import Any, Optional

from agents.coder_agent import CoderAgent
from agents.roblox_agent import RobloxAgent
from agents.system_agent import SystemAgent
from core.agent_manager import AgentManager
from core.brain import Brain
from core.config import (
    CONFIG_PATH,
    DATA_DIR,
    LOG_PATH,
    load_config,
    save_config,
)
from core.model_router import ModelRouter
from core.security_engine import SecurityEngine
from core.task_engine import TaskEngine
from memory.sqlite_store import SqliteStore
from modules.computer_control import PcController
from modules.voice import Ears, EarsError, Voice
from ui.dashboard import Dashboard
from ui.settings import SettingsWindow

logger = logging.getLogger("Jarvis.Main")

WELCOME_TEXT = (
    "Усі системи активовано, сер. Jarvis Ultimate готовий до роботи. "
    "Натисніть 🎙 для голосового запиту або напишіть повідомлення."
)


class JarvisUltimateApp:
    """
    Модульний застосунок JARVIS ULTIMATE: збирає ядро, агентів, голос і GUI.

    Параметри ``store``/``router``/``security``/``voice``/``ears``/``pc``/
    ``brain`` необов'язкові й дозволяють підмінити залежності в тестах, не
    роблячи мережевих чи аудіовикликів.
    """

    def __init__(
        self,
        root: tk.Tk,
        config: Optional[dict[str, Any]] = None,
        *,
        store: Optional[SqliteStore] = None,
        router: Optional[ModelRouter] = None,
        security: Optional[SecurityEngine] = None,
        voice: Optional[Voice] = None,
        ears: Optional[Ears] = None,
        pc: Optional[PcController] = None,
        brain: Optional[Brain] = None,
    ) -> None:
        self.root = root
        self.config: dict[str, Any] = config if config is not None else load_config()
        self._shutdown = threading.Event()
        self._mic_lock = threading.Lock()
        self._settings_window: Optional[SettingsWindow] = None
        self._metrics_lock = threading.Lock()
        self._latest_metrics: dict[str, Any] = {}
        self._metrics_after_id: Optional[str] = None

        # ── ядро ─────────────────────────────────────────────────────────────
        self.security = security or SecurityEngine(confirm_callback=self.request_approval)
        self.router = router or ModelRouter(self.config)
        self.store = store or SqliteStore()
        self.tasks = TaskEngine()
        self.agents = AgentManager()

        self.coder = CoderAgent(self.security, self.router)
        self.sys_agent = SystemAgent(self.security, self.router)
        self.roblox = RobloxAgent(self.security, self.router, self.config)
        for agent in (self.coder, self.sys_agent, self.roblox):
            self.agents.register_agent(agent)

        self.pc = pc or PcController(
            confirm=self.request_approval,
            log=self._tool_log,
            config=self.config,
        )
        self.brain = brain or Brain(
            config=self.config,
            security_engine=self.security,
            model_router=self.router,
            agent_manager=self.agents,
            task_engine=self.tasks,
            store=self.store,
            pc_controller=self.pc,
        )
        self.voice = voice or Voice(self.config)
        self.ears = ears or Ears(self.config)

        # ── інтерфейс ────────────────────────────────────────────────────────
        self.dashboard = Dashboard(
            root=self.root,
            on_send_callback=self.handle_user_message,
            on_mic_callback=self.handle_mic,
            on_emergency_stop_callback=self.handle_emergency_stop,
            on_settings_callback=self.open_settings,
        )
        self._apply_window_options()
        self._sync_agent_indicators()
        self._start_metrics_loop()
        self._post_welcome()

    # ── сервісні методи ──────────────────────────────────────────────────────
    def _apply_window_options(self) -> None:
        try:
            self.root.attributes("-topmost", bool(self.config.get("always_on_top")))
        except tk.TclError:
            logger.debug("Не вдалося застосувати always_on_top")

    def _sync_agent_indicators(self) -> None:
        for name in ("brain", "coder", "system", "roblox"):
            self.dashboard.update_agent_status(name, True)

    def _tool_log(self, message: str) -> None:
        """Журналює дії інструментів; блокування показує і в чаті."""
        text = str(message or "")
        logger.info("TOOL: %s", text)
        if text.startswith("⛔") and getattr(self, "dashboard", None) is not None:
            self.dashboard.post_message("СИСТЕМА", text, tag="sys")

    def _post_welcome(self) -> None:
        self.dashboard.post_message("J.A.R.V.I.S.", WELCOME_TEXT, tag="jarvis")
        if self.config.get("greet", True) and not self.config.get("mute"):
            threading.Thread(
                target=self._speak,
                args=(WELCOME_TEXT,),
                name="jarvis-greet",
                daemon=True,
            ).start()

    def _start_metrics_loop(self) -> None:
        threading.Thread(
            target=self._metrics_worker,
            name="jarvis-metrics",
            daemon=True,
        ).start()
        # HUD оновлюється з GUI-потоку; фоновий потік лише збирає метрики.
        self._refresh_metrics_ui()

    def _metrics_worker(self) -> None:
        """Фонове збирання метрик системи (без жодних Tk-викликів)."""
        while not self._shutdown.is_set():
            try:
                metrics = self.sys_agent.get_system_metrics()
                ram_text = (
                    f"RAM: {metrics.get('ram_used_gb', 0)}/"
                    f"{metrics.get('ram_total_gb', 0)} ГБ "
                    f"({metrics.get('ram_load_pct', 0)}%)"
                )
                with self._metrics_lock:
                    self._latest_metrics["ram_text"] = ram_text
            except Exception:
                logger.debug("Не вдалося отримати системні метрики", exc_info=True)
            self._shutdown.wait(4.0)

    def _refresh_metrics_ui(self) -> None:
        """Оновлює HUD з GUI-потоку (раз на секунду); безпечно після закриття вікна."""
        if self._shutdown.is_set():
            return
        try:
            with self._metrics_lock:
                ram_text = str(self._latest_metrics.get("ram_text") or "")
            if ram_text:
                model_name = str(self.config.get("model", "")).split("/")[-1] or "—"
                self.dashboard.update_metrics(ram_text, f"Модель: {model_name}")
            self._metrics_after_id = self.root.after(1000, self._refresh_metrics_ui)
        except tk.TclError:
            self._metrics_after_id = None

    # ── обробка повідомлень ──────────────────────────────────────────────────
    def handle_user_message(self, text: str) -> None:
        """Обробляє текстове повідомлення: Brain → чат → озвучення."""
        text = (text or "").strip()
        if not text or self._shutdown.is_set():
            return
        self.dashboard.update_agent_status("brain", True)
        try:
            reply = self.brain.process(text)
        except Exception as exc:
            logger.exception("Помилка Brain.process")
            reply = f"Сер, сталася помилка обробки запиту: {exc}"
        reply = str(reply or "…")
        self.dashboard.post_message("J.A.R.V.I.S.", reply, tag="jarvis")
        self.dashboard.update_agent_status("brain", True)
        self._speak(reply)

    def _speak(self, text: str) -> None:
        """Озвучує текст, якщо звук увімкнено; ніколи не кидає винятків."""
        if self._shutdown.is_set() or self.config.get("mute"):
            return
        try:
            self.voice.speak(str(text or ""))
        except Exception:
            logger.exception("Не вдалося озвучити відповідь")

    # ── мікрофон ─────────────────────────────────────────────────────────────
    def handle_mic(self) -> None:
        """Кнопка мікрофона: запускає запис/розпізнавання у фоні."""
        if self._shutdown.is_set():
            return
        thread = threading.Thread(
            target=self._mic_worker,
            name="jarvis-mic",
            daemon=True,
        )
        thread.start()

    def _mic_worker(self) -> None:
        if not self._mic_lock.acquire(blocking=False):
            self.dashboard.post_message("СИСТЕМА", "Я вже слухаю, сер.", tag="sys")
            return
        try:
            self.dashboard.set_busy(True)
            self.dashboard.update_agent_status("brain", False)
            self.dashboard.post_message("СИСТЕМА", "🎙 Слухаю…", tag="sys")
            try:
                raw = self.ears.record()
            except EarsError as exc:
                self.dashboard.post_message("СИСТЕМА", str(exc), tag="sys")
                return
            if not raw:
                self.dashboard.post_message(
                    "СИСТЕМА", "Нічого не почув, сер. Спробуйте ще раз.", tag="sys"
                )
                return
            try:
                text = self.ears.transcribe(raw, self.config.get("language"))
            except EarsError as exc:
                self.dashboard.post_message("СИСТЕМА", str(exc), tag="sys")
                return
            if not text:
                self.dashboard.post_message(
                    "СИСТЕМА", "Не вдалося розпізнати мовлення, сер.", tag="sys"
                )
                return
            self.dashboard.post_message("Ви", text, tag="you")
            self.handle_user_message(text)
        except Exception:
            logger.exception("Помилка голосового введення")
            self.dashboard.post_message(
                "СИСТЕМА", "Помилка мікрофона, сер. Деталі — у логі.", tag="sys"
            )
        finally:
            self.dashboard.update_agent_status("brain", True)
            self.dashboard.set_busy(False)
            self._mic_lock.release()

    # ── аварійна зупинка / скидання ──────────────────────────────────────────
    def handle_emergency_stop(self) -> None:
        """
        Кнопка EMERGENCY STOP працює як перемикач.

        Перше натискання — зупиняє всі дії та мовлення; повторне — скидає
        блокування і повертає систему в робочий стан.
        """
        if self.security.is_stopped:
            self.security.reset_emergency_stop()
            self.dashboard.update_agent_status("brain", True)
            self.dashboard.post_message(
                "СИСТЕМА",
                "✅ Екстрену зупинку скасовано. Система знову активна, сер.",
                tag="sys",
            )
            return

        self.security.trigger_emergency_stop()
        try:
            self.ears.stop()
        except Exception:
            logger.debug("Не вдалося зупинити запис мікрофона", exc_info=True)
        try:
            self.voice.stop()
        except Exception:
            logger.debug("Не вдалося зупинити мовлення", exc_info=True)
        self.dashboard.update_agent_status("brain", False)
        self.dashboard.post_message(
            "СИСТЕМА",
            "🚨 Екстрена зупинка! Усі дії заблоковано. "
            "Натисніть EMERGENCY STOP ще раз, щоб розблокувати.",
            tag="sys",
        )

    # ── налаштування ─────────────────────────────────────────────────────────
    def open_settings(self) -> None:
        """Відкриває вікно редагування спільного ``config.json``."""
        existing = self._settings_window
        if existing is not None:
            try:
                if existing.win.winfo_exists():
                    existing.win.lift()
                    existing.win.focus_force()
                    return
            except tk.TclError:
                pass
            self._settings_window = None
        try:
            fresh_config = load_config()
            self._settings_window = SettingsWindow(
                self.root,
                config=fresh_config,
                on_save=self._apply_config,
            )
        except Exception:
            logger.exception("Не вдалося відкрити вікно налаштувань")
            self.dashboard.post_message(
                "СИСТЕМА", "Не вдалося відкрити вікно налаштувань, сер.", tag="sys"
            )

    def _apply_config(self, new_config: dict[str, Any]) -> None:
        """Зберігає налаштування у спільний config.json і застосовує їх на льоту."""
        save_config(new_config)
        self.config.clear()
        self.config.update(new_config)
        self._apply_window_options()
        logger.info("Конфігурацію збережено: %s", CONFIG_PATH)

    # ── підтвердження небезпечних дій ────────────────────────────────────────
    def request_approval(self, action: str, details: str) -> bool:
        """Діалог підтвердження для SecurityEngine/PcController (з будь-якого потоку)."""
        if self._shutdown.is_set():
            return False

        def _ask() -> bool:
            try:
                return bool(
                    messagebox.askyesno(
                        title=f"J.A.R.V.I.S. · {action}",
                        message=f"{details}\n\nПідтверджуєте виконання цієї дії?",
                        parent=self.root,
                    )
                )
            except tk.TclError:
                return False

        if threading.current_thread() is threading.main_thread():
            return _ask()

        answer: dict[str, bool] = {"ok": False}
        state: dict[str, bool] = {"expired": False}
        event = threading.Event()

        def _show() -> None:
            # Якщо Lead уже дочекався таймауту — пізній діалог не показуємо.
            if event.is_set() or state["expired"] or self._shutdown.is_set():
                return
            answer["ok"] = _ask()
            event.set()

        try:
            self.root.after(0, _show)
        except tk.TclError:
            return False
        deadline = time.monotonic() + 60.0
        while not event.is_set() and time.monotonic() < deadline:
            if self._shutdown.is_set():
                return False
            event.wait(0.2)
        if not event.is_set():
            state["expired"] = True
            logger.warning("Діалог підтвердження не дочекався відповіді за 60 с")
            return False
        return bool(answer["ok"])

    # ── завершення ───────────────────────────────────────────────────────────
    def shutdown(self) -> None:
        """Коректно зупиняє фонові процеси й закриває допоміжні вікна."""
        self._shutdown.set()
        after_id = self._metrics_after_id
        self._metrics_after_id = None
        if after_id is not None:
            try:
                self.root.after_cancel(after_id)
            except tk.TclError:
                pass
        dashboard = getattr(self, "dashboard", None)
        if dashboard is not None:
            try:
                dashboard.stop()
            except Exception:
                logger.debug("Не вдалося зупинити чергу UI", exc_info=True)
        for name in ("ears", "voice"):
            target = getattr(self, name, None)
            stop = getattr(target, "stop", None)
            if callable(stop):
                try:
                    stop()
                except Exception:
                    logger.debug("Не вдалося зупинити %s", name, exc_info=True)
        if self._settings_window is not None:
            try:
                self._settings_window.destroy()
            except Exception:
                logger.debug("Не вдалося закрити вікно налаштувань", exc_info=True)
            self._settings_window = None


# ── запуск ───────────────────────────────────────────────────────────────────
def _configure_logging() -> None:
    """Налаштовує логування у ``%APPDATA%\\Jarvis\\jarvis_ultimate.log`` (ліниво)."""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    try:
        file_handler = logging.FileHandler(str(LOG_PATH), encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except OSError:
        pass
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)


def main() -> None:
    """Точка входу: створює Tk-вікно, застосунок і запускає головний цикл."""
    _configure_logging()
    logger.info("=== JARVIS ULTIMATE (v2) START ===")

    def _excepthook(exc_type, exc_value, exc_tb) -> None:
        logger.critical("Необроблений виняток", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = _excepthook

    root = tk.Tk()
    root.report_callback_exception = lambda exc_type, exc_value, exc_tb: logger.error(
        "Помилка Tk-колбека", exc_info=(exc_type, exc_value, exc_tb)
    )
    app: Optional[JarvisUltimateApp] = None
    try:
        app = JarvisUltimateApp(root)
        root.mainloop()
    except Exception as exc:
        logger.exception("Критична помилка JARVIS ULTIMATE")
        try:
            messagebox.showerror(
                "J.A.R.V.I.S.",
                f"Критична помилка: {exc}\nДеталі — у %APPDATA%\\Jarvis\\jarvis_ultimate.log",
                parent=root,
            )
        except Exception:
            pass
    finally:
        if app is not None:
            app.shutdown()
        try:
            root.destroy()
        except tk.TclError:
            pass
        logger.info("=== JARVIS ULTIMATE (v2) STOP ===")


if __name__ == "__main__":
    main()
