# -*- coding: utf-8 -*-
"""
JARVIS ULTIMATE — керування комп'ютером (Windows).

Головний клас — :class:`PcController`. Він уміє:

* відкривати сайти та програми за людино-зрозумілими аліасами
  (``youtube``, ``notepad``, ``vscode``, ``ютуб``, ``калькулятор`` …);
* виконувати PowerShell-команди з класифікацією ризику: безпечні
  (``Get-*``, ``dir``, ``ipconfig``, ``systeminfo`` …) виконуються одразу,
  небезпечні (``rm``, ``del``, ``format``, ``shutdown``, ``taskkill``, запис
  у реєстр …) потребують підтвердження через callback, а катастрофічні
  (форматування дисків, ``diskpart`` …) блокуються завжди;
* шукати, читати й записувати файли (запис — лише з підтвердженням);
* збирати інформацію про систему (ОС, CPU, RAM, диск, uptime);
* робити знімки екрана, керувати мишкою/клавіатурою, вікнами.

Callback підтвердження має сигнатуру ``confirm(action: str, details: str) -> bool``.
Якщо callback не задано, будь-яка потенційно небезпечна дія відхиляється з
українським повідомленням. Усі публічні методи повертають текст і не кидають
винятків; жодних дій під час імпорту модуль не виконує.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("Jarvis.PcControl")

ConfirmCallback = Callable[[str, str], bool]
LogCallback = Callable[[str], None]

# ── класифікація PowerShell-команд ───────────────────────────────────────────
#: Безпечні команди: лише читання/діагностика. Виконуються без підтвердження.
SAFE_START = re.compile(
    r"(?i)^\s*(?:get-[a-z]+|test-path|resolve-path|select-[a-z]+|where-object|"
    r"sort-object|measure-object|format-(?:table|list|wide)|convertto-[a-z]+|"
    r"convertfrom-[a-z]+|out-string|out-host|write-output|write-host|"
    r"\bdir\b|\bls\b|\bgci\b|\becho\b|\btype\b|systeminfo|ipconfig|\bping\b|"
    r"tasklist|whoami|hostname|get-date|get-psdrive|get-childitem|get-content|"
    r"get-process|get-service|get-volume|get-disk|get-ciminstance|get-computerinfo|"
    r"get-netipaddress|get-netadapter|nslookup|tracert|\barp\b|netstat|\bver\b|"
    r"set-location|\bcd\b|\bpwd\b|get-item|get-itemproperty|get-filehash|get-acl|"
    r"compare-object|group-object|get-help|get-command|get-module|get-variable|"
    r"get-location|get-host|get-culture|get-uiculture|get-timezone|get-hotfix|"
    r"get-eventlog|get-winevent|get-random|get-member|get-unique|start-sleep)\b"
)

#: Команди, дозволені як наступні ланки конвеєра (лише читання/форматування).
SAFE_PIPE_CMDLETS = re.compile(
    r"(?i)^\s*(?:select-object|where-object|sort-object|measure-object|"
    r"format-(?:table|list|wide|custom|hex)|convertto-[a-z]+|convertfrom-[a-z]+|"
    r"out-string|out-host|get-member|get-unique|group-object|compare-object|"
    r"select-string|split-object|join-string)\b"
)

#: Токени, що перетворюють «читальну» команду на виконання довільного коду.
BLOCKED_TOKENS = re.compile(
    r"(?i)(?:[;`]|\$\(|\{|\}|&&|\|\||>|<|"
    r"\bstart-job\b|\bstart-threadjob\b|\bregister-scheduledtask\b|"
    r"(?:download|upload)(?:string|file|data|values?)\b|"
    r"\bnew-object\b|\badd-type\b|\bscriptblock\b|\bexecutioncontext\b|"
    r"\.\s*(?:delete|remove|write|move|copy|rename|create|open|invoke|unlink)\s*\()"
)

#: Ознаки секретів: такі команди/файли завжди вимагають підтвердження.
SENSITIVE_HINTS = re.compile(
    r"(?i)(?:config\.json|credentials?|\.env\b|id_rsa|id_ed25519|\.pem\b|"
    r"\.key\b|\.pfx\b|\.p12\b|passwo?rd|passw|secret|token|api[_-]?key|"
    r"%appdata%\\jarvis|appdata\\roaming\\jarvis)"
)

#: Небезпечні команди: змінюють систему/файли. Потребують підтвердження.
DANGEROUS = re.compile(
    r"(?i)(remove-item|\brm\b|\bdel\b|\berase\b|\brmdir\b|\brd\b|format-volume|"
    r"diskpart|clear-disk|initialize-disk|set-item|new-item|"
    r"copy-item|move-item|rename-item|clear-content|set-content|add-content|out-file|"
    r"set-acl|takeown|icacls|attrib|\breg\b|regedit|schtasks|\bsc\b|"
    r"net\s+(user|localgroup|share)|shutdown|restart-computer|stop-computer|"
    r"stop-process|\bkill\b|taskkill|stop-service|set-service|start-service|new-service|"
    r"remove-service|set-executionpolicy|set-mppreference|netsh|bcdedit|cipher|"
    r"manage-bde|vssadmin|wbadmin|wmic\b|invoke-expression|\biexec\b|invoke-webrequest|"
    r"\biwr\b|invoke-restmethod|\bcurl\b|\bwget\b|\bstart-process\b|\bstart\b(?!-)|"
    r"\bpowershell\b|\bpwsh\b|\bcmd\b|wscript|cscript|mshta|rundll32|regsvr32|setx|"
    r"set-itemproperty|new-itemproperty|remove-itemproperty|rename-computer|"
    r"add-computer|remove-computer|enable-psremoting|winrm|enable-windowsoptionalfeature|"
    r"disable-windowsoptionalfeature|\bdism\b|winget\s+(install|uninstall|upgrade)|"
    r"choco\s+(install|uninstall|upgrade)|python\b|node\b|pip\b|npm\b|"
    r"clear-recyclebin|\bri\b|\bmv\b|\bcp\b|\bren\b|\bmove\b|\bcopy\b|new-object|"
    r"add-type|start-bitstransfer|bitsadmin|certutil|msiexec|\[(?:system\.)?io\.file\]|"
    r"::delete|::writealltext|::writeallbytes|::move|::copy)"
)

#: Катастрофічні команди: блокуються завжди, без можливості підтвердження.
CATASTROPHIC: tuple[str, ...] = (
    r"(?i)\bformat(?:-volume)?\b[^\n]*\b[a-z]:",
    r"(?i)\bformat-volume\b",
    r"(?i)\bdiskpart\b",
    r"(?i)\bclear-disk\b",
    r"(?i)\binitialize-disk\b",
    r"(?i)\bbcdedit\b",
    r"(?i)\bvssadmin\b[^\n]*delete",
    r"(?i)\bwbadmin\b[^\n]*delete",
    r"(?i)\bcipher\b[^\n]*/w",
    r"(?i)\bmanage-bde\b[^\n]*-off",
    r"(?i)(?:remove-item|\bdel\b|\berase\b|\brd\b|\brmdir\b)[^\n]*\b[a-z]:[\\/]?(?=\s|$|[\"'])",
    r"(?i)(?:remove-item|\bdel\b|\berase\b|\brd\b|\brmdir\b)[^\n]*(?:\\windows\\|\\system32\b|\$env:(?:systemroot|windir))",
)

RISK_SAFE = "safe"
RISK_DANGEROUS = "dangerous"
RISK_CATASTROPHIC = "catastrophic"

# ── аліаси сайтів та програм ─────────────────────────────────────────────────
#: Людино-зрозумілі назви сайтів → URL.
SITE_ALIASES: dict[str, str] = {
    "youtube": "https://www.youtube.com",
    "ютуб": "https://www.youtube.com",
    "ютюб": "https://www.youtube.com",
    "google": "https://www.google.com",
    "гугл": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "chatgpt": "https://chatgpt.com",
    "чатгпт": "https://chatgpt.com",
    "openrouter": "https://openrouter.ai",
    "github": "https://github.com",
    "гітхаб": "https://github.com",
    "telegram": "https://web.telegram.org",
    "телеграм": "https://web.telegram.org",
    "discord": "https://discord.com/app",
    "діскорд": "https://discord.com/app",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "tiktok": "https://www.tiktok.com",
    "spotify": "https://open.spotify.com",
    "спотіфай": "https://open.spotify.com",
    "netflix": "https://www.netflix.com",
    "twitch": "https://www.twitch.tv",
    "roblox": "https://www.roblox.com",
    "роблокс": "https://www.roblox.com",
    "steam": "https://store.steampowered.com",
    "стім": "https://store.steampowered.com",
    "reddit": "https://www.reddit.com",
    "wikipedia": "https://uk.wikipedia.org",
    "вікіпедія": "https://uk.wikipedia.org",
}

#: Людино-зрозумілі назви програм → команда/шлях/протокол.
APP_ALIASES: dict[str, str] = {
    "chrome": "chrome",
    "хром": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "браузер": "https://www.google.com",
    "notepad": "notepad.exe",
    "блокнот": "notepad.exe",
    "calculator": "calc.exe",
    "калькулятор": "calc.exe",
    "paint": "mspaint.exe",
    "пайнт": "mspaint.exe",
    "маляр": "mspaint.exe",
    "explorer": "explorer.exe",
    "проводник": "explorer.exe",
    "vscode": "code",
    "vs code": "code",
    "код": "code",
    "terminal": "wt.exe",
    "термінал": "wt.exe",
    "cmd": "cmd.exe",
    "командний рядок": "cmd.exe",
    "powershell": "powershell.exe",
    "discord": "discord://",
    "telegram desktop": "tg://",
    "steam": "steam://open/main",
    "spotify": "spotify:",
    "vlc": "vlc.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "task manager": "taskmgr.exe",
    "диспетчер задач": "taskmgr.exe",
    "camera": "microsoft.windows.camera:",
    "камера": "microsoft.windows.camera:",
    "settings": "ms-settings:",
    "параметри": "ms-settings:",
    "налаштування": "ms-settings:",
    "store": "ms-windows-store:",
    "магазин": "ms-windows-store:",
    "photos": "ms-photos:",
    "фото": "ms-photos:",
    "calculator app": "calculator:",
    "alarms": "ms-clock:",
    "годинник": "ms-clock:",
}

#: Голі назви відомих програм, які можна запускати без підтвердження.
KNOWN_EXECUTABLES: frozenset[str] = frozenset({
    "chrome", "msedge", "code", "notepad", "calc", "mspaint", "explorer",
    "wt", "cmd", "powershell", "pwsh", "vlc", "winword", "excel",
    "taskmgr", "discord", "steam", "spotify",
})

#: Шляхи до встановленого Chrome (розгортаються під час виклику).
CHROME_PATH_CANDIDATES: tuple[str, ...] = (
    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
    r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
    r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
)

#: Розпізнавання доменного імені (для «відкрий example.com»).
_DOMAIN_RE = re.compile(
    r"(?:https?://)?(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:[a-z]{2,24})"
    r"(?::\d{1,5})?(?:/\S*)?",
    re.IGNORECASE,
)
_URL_SCHEME_RE = re.compile(r"(?i)^(?:https?://|file://)")


def normalize_alias(value: str) -> str:
    """Нормалізує назву аліаса: нижній регістр, без пробілів, дефісів і підкреслень."""
    return re.sub(r"[\s\-_]+", "", str(value or "").lower().strip())


def classify_command(command: str) -> str:
    """
    Класифікує PowerShell-команду.

    Повертає одне зі значень :data:`RISK_SAFE`, :data:`RISK_DANGEROUS`,
    :data:`RISK_CATASTROPHIC`. Порожня команда вважається небезпечною
    (її однаково не буде виконано). Функція не виконує жодних команд.

    «Безпечною» вважається лише команда, що є чистим ланцюжком read-only
    cmdlet'ів: без script-блоків, ;, підстановок, перенаправлень і викликів
    довільних методів. Це закриває обхід на кшталт
    ``Get-ChildItem ... | ForEach-Object { $_.Delete() }``.
    """
    text = str(command or "").strip()
    if not text:
        return RISK_DANGEROUS
    if any(re.search(pattern, text) for pattern in CATASTROPHIC):
        return RISK_CATASTROPHIC
    if DANGEROUS.search(text) or BLOCKED_TOKENS.search(text):
        return RISK_DANGEROUS
    if SENSITIVE_HINTS.search(text):
        return RISK_DANGEROUS
    segments = [segment.strip() for segment in text.split("|")]
    if not segments or len(segments) > 8:
        return RISK_DANGEROUS
    if not SAFE_START.match(segments[0]):
        return RISK_DANGEROUS
    for segment in segments[1:]:
        if not SAFE_PIPE_CMDLETS.match(segment):
            return RISK_DANGEROUS
    return RISK_SAFE


class PcController:
    """
    Керування Windows: програми, PowerShell, файли, мишка/клавіатура, вікна.

    :param confirm: callback підтвердження ``confirm(action, details) -> bool``.
        ``None`` означає, що небезпечні дії заборонені.
    :param log: callback журналювання дій (необов'язковий).
    :param config: словник налаштувань JARVIS (використовується ``full_access``).
    """

    SITE_ALIASES = SITE_ALIASES
    APP_ALIASES = APP_ALIASES
    SAFE_START = SAFE_START
    DANGEROUS = DANGEROUS
    CATASTROPHIC = CATASTROPHIC

    TOOL_METHODS: dict[str, str] = {
        "run_powershell": "run_powershell",
        "open_app": "open_app",
        "open_site": "open_site",
        "find_files": "find_files",
        "read_file": "read_file",
        "write_file": "write_file",
        "system_info": "system_info",
        "screenshot": "screenshot",
        "click": "click",
        "mouse_click": "click",
        "move": "move",
        "mouse_move": "move",
        "type_text": "type_text",
        "hotkey": "hotkey",
        "list_windows": "list_windows",
        "activate_window": "activate_window",
        "scroll": "scroll",
    }

    def __init__(
        self,
        confirm: Optional[ConfirmCallback] = None,
        log: Optional[LogCallback] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> None:
        self.confirm = confirm
        self.log = log if log is not None else (lambda message: logger.info("%s", message))
        self.config: dict[str, Any] = config if config is not None else {}

    # ── службові методи ──────────────────────────────────────────────────────
    @property
    def has_confirm_callback(self) -> bool:
        """Чи налаштовано діалог підтвердження."""
        return self.confirm is not None

    @staticmethod
    def classify_command(command: str) -> str:
        """Повертає рівень ризику команди (``safe`` / ``dangerous`` / ``catastrophic``)."""
        return classify_command(command)

    @classmethod
    def is_safe_command(cls, command: str) -> bool:
        """Чи є команда безпечною для автоматичного виконання."""
        return classify_command(command) == RISK_SAFE

    @classmethod
    def is_catastrophic(cls, command: str) -> bool:
        """Чи є команда катастрофічною (блокується завжди)."""
        return classify_command(command) == RISK_CATASTROPHIC

    def _write_log(self, message: str) -> None:
        try:
            self.log(str(message))
        except Exception:
            logger.debug("Не вдалося записати лог дії", exc_info=True)

    def _ask_confirm(self, action: str, details: str) -> bool:
        """Питає підтвердження; за відсутності callback або помилки — відмова."""
        if self.confirm is None:
            return False
        try:
            return bool(self.confirm(action, details))
        except Exception:
            logger.exception("Діалог підтвердження впав")
            return False

    # ── PowerShell ───────────────────────────────────────────────────────────
    def run_powershell(self, command: str, timeout_sec: int = 30) -> str:
        """
        Виконує PowerShell-команду з урахуванням рівня ризику.

        Безпечні команди виконуються одразу, небезпечні — лише після
        підтвердження, катастрофічні блокуються. Повертає текстовий
        результат (``exit=…``, stdout, stderr) або українське повідомлення
        про відмову/помилку.
        """
        command = str(command or "").strip()
        if not command:
            return "Порожня команда, сер."
        risk = classify_command(command)

        if risk == RISK_CATASTROPHIC:
            self._write_log(f"⛔ Заблоковано катастрофічну команду: {command[:180]}")
            return "⛔ Заблоковано: ця команда може знищити систему, сер."

        if risk == RISK_DANGEROUS:
            if self.confirm is None:
                self._write_log(f"⛔ Відхилено без підтвердження: {command[:180]}")
                return (
                    "⛔ Дію не виконано: вона потребує підтвердження користувача, "
                    "але діалог підтвердження недоступний."
                )
            if not self._ask_confirm("Виконати команду PowerShell?", command):
                return "Користувач відмовився виконувати команду."

        code, stdout, stderr = self._execute_powershell(command, timeout_sec)
        parts = [f"exit={code}"]
        if stdout:
            parts.append("STDOUT:\n" + stdout)
        if stderr:
            parts.append("STDERR:\n" + stderr)
        if code != 0 and not stdout and not stderr:
            parts.append("(без виводу)")
        text = "\n".join(parts)
        if len(text) > 7000:
            text = text[:7000] + "\n… (обрізано)"
        summary = (stdout or stderr or "").replace("\n", " ")[:200]
        self._write_log(f"✓ exit={code}: {summary}".rstrip())
        return text

    def _execute_powershell(self, command: str, timeout_sec: int) -> tuple[int, str, str]:
        """Запускає PowerShell і повертає ``(exit_code, stdout, stderr)`` без винятків."""
        try:
            timeout = max(5, min(120, int(timeout_sec or 30)))
        except (TypeError, ValueError):
            timeout = 30
        wrapped = (
            "$ProgressPreference='SilentlyContinue'; "
            "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
            "$OutputEncoding=[System.Text.Encoding]::UTF8; " + command
        )
        self._write_log(f"⚙ PowerShell: {command[:300]}")
        try:
            proc = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    wrapped,
                ],
                capture_output=True,
                timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired:
            return (-1, "", f"Команда не завершилася за {timeout} секунд.")
        except Exception as exc:
            logger.exception("Не вдалося запустити PowerShell")
            return (-1, "", f"Не вдалося запустити PowerShell: {exc}")
        stdout = proc.stdout.decode("utf-8", "replace").strip()
        stderr = proc.stderr.decode("utf-8", "replace").strip()
        return (proc.returncode, stdout, stderr)

    # ── програми та сайти ────────────────────────────────────────────────────
    @staticmethod
    def _find_start_menu_app(name: str) -> Optional[str]:
        """Resolve an exact display name from installed Start Menu shortcuts."""
        wanted = normalize_alias(Path(name).stem)
        if not wanted:
            return None
        roots = (
            Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
            Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        )
        for root in roots:
            if not root.is_dir():
                continue
            try:
                for shortcut in root.rglob("*.lnk"):
                    if normalize_alias(shortcut.stem) == wanted:
                        return str(shortcut)
            except OSError:
                continue
        return None

    def is_known_target(self, target: str) -> bool:
        """
        Чи розпізнає контролер ціль (аліас, URL, домен або наявний шлях).

        Використовується швидкими діями, щоб не перехоплювати в LLM звичайні
        фрази на кшталт «відкрий мені двері».
        """
        raw = str(target or "").strip().strip("\"'\u00ab\u00bb")
        if not raw:
            return False
        if " " in raw:
            if self._find_start_menu_app(raw):
                return True
            # шляхи з пробілами дозволені
            expanded = Path(os.path.expandvars(os.path.expanduser(raw)))
            try:
                if expanded.exists():
                    return True
            except OSError:
                pass
            return False
        low = raw.lower()
        normalized = normalize_alias(low)
        if normalized in {normalize_alias(key) for key in SITE_ALIASES}:
            return True
        if normalized in {normalize_alias(key) for key in APP_ALIASES}:
            return True
        if self._find_start_menu_app(raw):
            return True
        if _URL_SCHEME_RE.match(raw):
            return True
        try:
            if Path(os.path.expandvars(os.path.expanduser(raw))).exists():
                return True
        except OSError:
            pass
        if _DOMAIN_RE.fullmatch(raw):
            return True
        return False

    def resolve_target(self, target: str) -> tuple[str, str]:
        """
        Розпізнає ціль відкриття.

        Повертає ``(значення, тип)``, де тип — ``"site"`` (відкрити в
        браузері), ``"app"`` (запустити програму/протокол) або ``"file"``
        (відкрити наявний файл/теку). Функція не виконує зовнішніх дій.
        """
        raw = str(target or "").strip().strip("\"'\u00ab\u00bb")
        if not raw:
            return ("", "app")

        low = raw.lower()
        normalized = normalize_alias(low)

        sites = {normalize_alias(key): value for key, value in SITE_ALIASES.items()}
        if normalized in sites:
            return (sites[normalized], "site")

        apps = {normalize_alias(key): value for key, value in APP_ALIASES.items()}
        if normalized in apps:
            value = apps[normalized]
            if _URL_SCHEME_RE.match(value):
                return (value, "site")
            if value == "chrome":
                return (self._find_chrome() or value, "app")
            return (value, "app")

        if _URL_SCHEME_RE.match(raw):
            return (raw, "site")

        shortcut = self._find_start_menu_app(raw)
        if shortcut:
            return (shortcut, "app")

        expanded = Path(os.path.expandvars(os.path.expanduser(raw)))
        try:
            if expanded.exists():
                return (str(expanded), "file")
        except OSError:
            pass

        if _DOMAIN_RE.fullmatch(raw) and " " not in raw:
            return (("https://" + raw) if not low.startswith(("http://", "https://")) else raw, "site")

        return (raw, "app")

    @staticmethod
    def _find_chrome() -> Optional[str]:
        """Шукає встановлений Chrome у типових місцях."""
        for template in CHROME_PATH_CANDIDATES:
            candidate = os.path.expandvars(template)
            if "%" in candidate:
                continue
            try:
                if Path(candidate).is_file():
                    return candidate
            except OSError:
                continue
        return None

    def open_app(self, target: str) -> str:
        """
        Відкриває сайт, програму, файл або теку.

        Розуміє аліаси (``youtube``, ``notepad``, ``ютуб`` …), доменні імена
        (``example.com`` → ``https://example.com``), URL і шляхи.
        """
        target = str(target or "").strip().strip("\"'\u00ab\u00bb")
        if not target:
            return "Не вказано, що відкривати, сер."

        resolved, kind = self.resolve_target(target)
        if not resolved:
            return "Не вказано, що відкривати, сер."

        normalized = normalize_alias(target)
        known = normalized in {normalize_alias(key) for key in SITE_ALIASES} or normalized in {
            normalize_alias(key) for key in APP_ALIASES
        }
        if not known and kind != "site":
            if kind == "app" and resolved.lower().endswith(".lnk"):
                known = True
            # Відомі системні програми (notepad.exe тощо) та URL-протоколи
            # (discord://, steam://) не потребують зайвого діалогу.
            if shutil.which(resolved):
                known = True
            elif (
                not re.search(r"[\\/]", resolved)
                and resolved.lower() in KNOWN_EXECUTABLES
            ):
                known = True
            elif re.match(r"(?i)^[a-z][a-z0-9+.-]*:(?://|$)", str(target)):
                known = True
        if kind != "site" and not known:
            # Довільний файл/виконуваний файл — лише з дозволу користувача.
            if not self._ask_confirm(
                "Відкрити файл або програму?",
                f"{resolved}\n\nЦе не відомий Jarvis додаток чи сайт.",
            ):
                return "Користувач відмовився відкривати цей об'єкт, сер."

        self._write_log(f"⚙ Відкриваю: {resolved}")
        if kind == "site":
            try:
                import webbrowser

                webbrowser.open(resolved)
                return f"Відкрив: {resolved}"
            except Exception as exc:
                logger.warning("Не вдалося відкрити сайт %s: %s", resolved, exc)

        startfile = getattr(os, "startfile", None)
        if startfile is not None:
            try:
                startfile(resolved)  # type: ignore[misc]
                return f"Відкрив: {resolved}"
            except OSError:
                logger.debug("os.startfile не знайшов %s", resolved)
            except Exception as exc:
                logger.warning("Помилка запуску %s: %s", resolved, exc)

        executable = shutil.which(resolved)
        if executable:
            try:
                subprocess.Popen(
                    [executable],
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                return f"Запустив: {executable}"
            except Exception as exc:
                return f"Не вдалося запустити {target}: {exc}"

        if kind == "file":
            return f"Не вдалося відкрити файл: {resolved}"
        return f"Не знайшов програму або файл: {resolved}"

    def open_site(self, site: str) -> str:
        """Відкриває сайт у браузері; приймає аліас, домен або URL."""
        resolved, kind = self.resolve_target(site)
        if not resolved:
            return "Не вказано сайт, сер."
        if kind != "site":
            return f"Не знаю такого сайту: {site}. Вкажіть назву або адресу сайту."
        return self.open_app(resolved)

    # ── файли ────────────────────────────────────────────────────────────────
    def search_files(self, pattern: str = "*", root: str = "", limit: int = 20) -> list[str]:
        """
        Шукає файли за шаблоном під текою.

        Повертає список шляхів (можливо порожній), ніколи не кидає винятків.
        """
        try:
            pattern = str(pattern or "").strip() or "*"
            base = Path(
                os.path.expandvars(os.path.expanduser(str(root or "").strip() or str(Path.home())))
            )
            if not base.exists() or not base.is_dir():
                return []
            try:
                limit_value = max(1, min(50, int(limit or 20)))
            except (TypeError, ValueError):
                limit_value = 20

            found: list[str] = []
            deadline = time.monotonic() + 12.0
            for path in base.rglob(pattern):
                if len(found) >= limit_value or time.monotonic() > deadline:
                    break
                try:
                    if path.is_file():
                        found.append(str(path))
                except OSError:
                    continue
            return found
        except Exception:
            logger.exception("Пошук файлів не вдався")
            return []

    def find_files(self, pattern: str = "*", root: str = "", limit: int = 20) -> str:
        """Шукає файли й повертає текстовий результат для LLM/користувача."""
        pattern = str(pattern or "").strip() or "*"
        root_display = str(root or "").strip() or str(Path.home())
        self._write_log(f"⚙ Пошук: {pattern} у {root_display}")
        found = self.search_files(pattern, root, limit)
        if not found:
            return "Нічого не знайдено."
        return "\n".join(found)

    @staticmethod
    def _is_sensitive_path(path: Path) -> bool:
        """Чи стосується шлях секретів/конфігурації Jarvis або інших ключів."""
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        try:
            data_dir = (Path(os.environ.get("APPDATA", "")) / "Jarvis").resolve()
            if resolved == data_dir or data_dir in resolved.parents:
                return True
        except OSError:
            pass
        return bool(SENSITIVE_HINTS.search(str(path)))

    def read_file(self, path: str, max_chars: int = 4000) -> str:
        """Читає текстовий файл (з обмеженням довжини) або повертає причину відмови."""
        raw = str(path or "").strip().strip("\"'")
        if not raw:
            return "Не вказано шлях до файлу, сер."
        file_path = Path(os.path.expandvars(os.path.expanduser(raw)))
        try:
            if not file_path.exists():
                return f"Файл не знайдено: {file_path}"
            if not file_path.is_file():
                return f"Це не файл: {file_path}"
        except OSError as exc:
            return f"Не вдалося перевірити файл: {exc}"

        if self._is_sensitive_path(file_path):
            if not self._ask_confirm(
                "Прочитати потенційно конфіденційний файл?",
                f"{file_path}\n\nФайл може містити API-ключі, паролі або особисті дані.",
            ):
                return "Користувач відмовився читати цей файл, сер."

        try:
            limit = max(200, min(12000, int(max_chars or 4000)))
        except (TypeError, ValueError):
            limit = 4000
        try:
            with file_path.open("rb") as handle:
                data = handle.read(limit * 4 + 1)
        except Exception as exc:
            return f"Не вдалося прочитати файл: {exc}"

        if b"\x00" in data[:1000]:
            return "Це бінарний файл, сер."
        text = data.decode("utf-8", "replace")
        if len(text) > limit:
            text = text[:limit] + "\n… (обрізано)"
        return f"{file_path}\n\n{text}"

    def write_file(self, path: str, content: str = "", append: bool = False) -> str:
        """
        Записує текстовий файл.

        Потребує підтвердження користувача; без callback запис відхиляється.
        Запис у ``C:\\Windows`` заборонено.
        """
        raw = str(path or "").strip().strip("\"'")
        if not raw:
            return "Не вказано шлях до файлу, сер."
        file_path = Path(os.path.expandvars(os.path.expanduser(raw)))
        lowered = str(file_path).replace("/", "\\").lower()
        if "\\windows\\" in lowered:
            return "Запис у C:\\Windows заблоковано, сер."

        if self.confirm is None:
            return (
                "⛔ Дію не виконано: запис файла потребує підтвердження користувача, "
                "але діалог підтвердження недоступний."
            )
        text = str(content or "")
        preview = text[:1200]
        if not self._ask_confirm("Записати файл на диск?", f"{file_path}\n\n{preview}"):
            return "Користувач відмовився записувати файл."

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            with file_path.open(mode, encoding="utf-8") as handle:
                handle.write(text)
        except Exception as exc:
            return f"Не вдалося записати файл: {exc}"
        self._write_log(f"✓ Записано: {file_path}")
        return f"Записано: {file_path} ({len(text)} символів)"

    # ── інформація про систему ───────────────────────────────────────────────
    def system_info(self) -> str:
        """Збирає зведення про систему: ОС, CPU, RAM, диск, uptime."""
        lines: list[str] = []
        try:
            lines.append(f"Комп'ютер: {os.environ.get('COMPUTERNAME', '?')}")
            lines.append(f"Користувач: {os.environ.get('USERNAME', '?')}")
        except Exception:
            pass

        try:
            if sys.platform == "win32":
                version = sys.getwindowsversion()
                windows_name = "11" if version.build >= 22000 else "10"
                lines.append(f"ОС: Windows {windows_name} (build {version.build})")
            else:
                lines.append(f"ОС: {sys.platform} (керування розраховане на Windows)")
        except Exception:
            lines.append("ОС: Windows (версію визначити не вдалося)")

        try:
            cpu_count = os.cpu_count() or 0
            lines.append(f"Процесор: {cpu_count} логічних ядер")
        except Exception:
            pass

        try:
            import ctypes
            from ctypes import wintypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", wintypes.DWORD),
                    ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            memory = MEMORYSTATUSEX()
            memory.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
            total_gb = memory.ullTotalPhys / 1024 ** 3
            free_gb = memory.ullAvailPhys / 1024 ** 3
            lines.append(
                f"RAM: {total_gb:.1f} ГБ всього, {free_gb:.1f} ГБ вільно "
                f"({memory.dwMemoryLoad}% зайнято)"
            )
        except Exception:
            logger.debug("Не вдалося отримати інформацію про RAM", exc_info=True)

        try:
            anchor = Path.home().anchor or "C:\\"
            disk = shutil.disk_usage(anchor)
            lines.append(
                f"Диск {anchor.rstrip(chr(92)) or anchor}: "
                f"{disk.free / 1024 ** 3:.1f} ГБ вільно з {disk.total / 1024 ** 3:.1f} ГБ"
            )
        except Exception:
            logger.debug("Не вдалося отримати інформацію про диск", exc_info=True)

        try:
            if sys.platform == "win32":
                import ctypes

                kernel32 = ctypes.windll.kernel32
                kernel32.GetTickCount64.restype = ctypes.c_ulonglong
                uptime_seconds = int(kernel32.GetTickCount64() / 1000)
                days, remainder = divmod(uptime_seconds, 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes = remainder // 60
                lines.append(f"Uptime: {days} дн {hours} год {minutes} хв")
        except Exception:
            logger.debug("Не вдалося отримати uptime", exc_info=True)

        return "\n".join(lines) if lines else "Не вдалося отримати інформацію про систему, сер."

    # ── екран, мишка, клавіатура ─────────────────────────────────────────────
    def screenshot(self, path: str = "", region: Optional[tuple[int, int, int, int]] = None) -> str:
        """Робить знімок екрана (або області) і повертає шлях до файлу."""
        try:
            import pyautogui  # type: ignore[import-not-found]
        except Exception as exc:
            return f"Модуль pyautogui недоступний: {exc}"

        try:
            raw = str(path or "").strip()
            if raw:
                target = Path(os.path.expandvars(os.path.expanduser(raw)))
            else:
                target = (
                    Path(tempfile.gettempdir())
                    / "jarvis_screenshots"
                    / f"screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            image = pyautogui.screenshot(region=tuple(region) if region else None)
            image.save(str(target))
            self._write_log(f"📸 Знімок екрана: {target}")
            return f"Знімок екрана збережено: {target}"
        except Exception as exc:
            logger.exception("Не вдалося зробити знімок екрана")
            return f"Не вдалося зробити знімок екрана: {exc}"

    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left", clicks: int = 1) -> str:
        """Клікає мишею у вказаній точці (або в поточній позиції курсора)."""
        try:
            import pyautogui  # type: ignore[import-not-found]

            safe_button = str(button or "left").lower()
            if safe_button not in {"left", "right", "middle"}:
                return "Невідома кнопка миші. Дозволено: left, right, middle."
            try:
                click_count = max(1, min(3, int(clicks or 1)))
            except (TypeError, ValueError):
                click_count = 1
            if x is None or y is None:
                pyautogui.click(button=safe_button, clicks=click_count)
                return "Клікнув у поточній позиції курсора."
            pyautogui.click(int(x), int(y), button=safe_button, clicks=click_count)
            return f"Клікнув: ({int(x)}, {int(y)}), кнопка {safe_button}."
        except Exception as exc:
            logger.exception("Не вдалося клікнути мишею")
            return f"Не вдалося клікнути: {exc}"

    def move(self, x: int, y: int, duration: float = 0.2) -> str:
        """Переміщує курсор миші у вказану точку."""
        try:
            import pyautogui  # type: ignore[import-not-found]

            safe_duration = max(0.0, min(2.0, float(duration or 0.2)))
            pyautogui.moveTo(int(x), int(y), duration=safe_duration)
            return f"Перемістив курсор у ({int(x)}, {int(y)})."
        except Exception as exc:
            logger.exception("Не вдалося перемістити курсор")
            return f"Не вдалося перемістити курсор: {exc}"

    def scroll(self, clicks: int = 0) -> str:
        """Прокручує колесо миші на ``clicks`` кроків (додатне — вгору)."""
        try:
            import pyautogui  # type: ignore[import-not-found]

            pyautogui.scroll(int(clicks or 0))
            return f"Прокрутив на {int(clicks or 0)} кроків."
        except Exception as exc:
            logger.exception("Не вдалося прокрутити")
            return f"Не вдалося прокрутити: {exc}"

    def type_text(self, text: str, interval: float = 0.02) -> str:
        """Вводить текст у активне вікно (Unicode — через буфер обміну і Ctrl+V)."""
        value = str(text or "")
        if not value:
            return "Немає тексту для введення, сер."
        try:
            import pyautogui  # type: ignore[import-not-found]

            if value.isascii():
                safe_interval = max(0.0, min(0.2, float(interval or 0.02)))
                pyautogui.write(value, interval=safe_interval)
                return f"Ввів текст ({len(value)} символів)."
            # pyautogui не вміє друкувати кирилицю — використовуємо буфер обміну.
            if self._set_clipboard(value):
                pyautogui.hotkey("ctrl", "v")
                return f"Ввів текст через буфер обміну ({len(value)} символів)."
            return "Не вдалося ввести не-ASCII текст: буфер обміну недоступний."
        except Exception as exc:
            logger.exception("Не вдалося ввести текст")
            return f"Не вдалося ввести текст: {exc}"

    def _set_clipboard(self, text: str) -> bool:
        """Кладе текст у буфер обміну Windows через PowerShell (без сторонніх пакетів)."""
        escaped = str(text).replace("'", "''")[:4000]
        try:
            proc = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    f"Set-Clipboard -Value '{escaped}'",
                ],
                capture_output=True,
                timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return proc.returncode == 0
        except Exception:
            logger.debug("Не вдалося покласти текст у буфер обміну", exc_info=True)
            return False

    def hotkey(self, *keys: str) -> str:
        """Натискає комбінацію клавіш, наприклад ``"ctrl+c"`` або ``("ctrl", "shift", "esc")``."""
        try:
            import pyautogui  # type: ignore[import-not-found]

            parts: list[str] = []
            for key in keys:
                parts.extend(part for part in re.split(r"[+\s]+", str(key).strip()) if part)
            if not parts:
                return "Не вказано комбінацію клавіш, сер."
            pyautogui.hotkey(*parts)
            return "Натиснув: " + " + ".join(parts)
        except Exception as exc:
            logger.exception("Не вдалося натиснути комбінацію клавіш")
            return f"Не вдалося натиснути комбінацію: {exc}"

    # ── вікна ────────────────────────────────────────────────────────────────
    def list_windows(self) -> str:
        """Повертає список заголовків відкритих вікон."""
        try:
            import pygetwindow as gw  # type: ignore[import-not-found]

            titles = [
                str(window.title).strip()
                for window in gw.getAllWindows()
                if str(getattr(window, "title", "") or "").strip()
            ]
        except Exception as exc:
            logger.exception("Не вдалося отримати список вікон")
            return f"Не вдалося отримати список вікон: {exc}"
        if not titles:
            return "Відкритих вікон не знайдено."
        return "\n".join(f"{index}. {title}" for index, title in enumerate(titles[:30], start=1))

    def activate_window(self, title: str) -> str:
        """Активує вікно за назвою (перше знайдене)."""
        query = str(title or "").strip()
        if not query:
            return "Не вказано назву вікна, сер."
        try:
            import pygetwindow as gw  # type: ignore[import-not-found]

            matches = list(gw.getWindowsWithTitle(query) or [])
        except Exception as exc:
            logger.exception("Не вдалося знайти вікно")
            return f"Не вдалося знайти вікно: {exc}"
        if not matches:
            return f"Вікно з назвою «{query}» не знайдено."
        window = matches[0]
        try:
            if getattr(window, "isMinimized", False):
                window.restore()
            window.activate()
            return f"Активував вікно: {getattr(window, 'title', query)}"
        except Exception as exc:
            logger.exception("Не вдалося активувати вікно")
            return f"Не вдалося активувати вікно: {exc}"

    # ── універсальний виклик (для Brain / LLM-tools) ─────────────────────────
    def run(self, name: str, args: Optional[dict[str, Any]] = None) -> str:
        """Викликає інструмент за назвою зі словником аргументів; повертає текст."""
        method_name = self.TOOL_METHODS.get(str(name or "").strip())
        if method_name is None:
            return f"Невідомий інструмент: {name}"
        payload = args if isinstance(args, dict) else {}
        try:
            return str(getattr(self, method_name)(**payload))
        except TypeError as exc:
            return f"Неправильні аргументи для {name}: {exc}"
        except Exception:
            logger.exception("Інструмент %s не вдався", name)
            return f"Помилка інструмента {name}, сер."


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
