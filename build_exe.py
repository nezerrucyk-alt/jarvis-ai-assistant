#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Збірка JARVIS.exe з jarvis.py через PyInstaller (spec-файл JARVIS.spec).

Приклади:
    .venv\\Scripts\\python.exe build_exe.py
    .venv\\Scripts\\python.exe build_exe.py --check
    .venv\\Scripts\\python.exe build_exe.py --skip-desktop-copy
    .venv\\Scripts\\python.exe build_exe.py --kill-running

Що робить скрипт:
  1. Перевіряє оточення: наявність jarvis.py / JARVIS.spec / assets, версію
     PyInstaller, контракт spec-файлу (onefile + console=False + collect_all).
  2. Запускає `python -m PyInstaller --noconfirm --clean --distpath dist
     --workpath build JARVIS.spec` з кореня проєкту.
  3. Перевіряє результат: файл існує, розмір > 60 МБ, валідний PE-заголовок,
     підсистема Windows GUI (2), а не консоль (3), свіжий таймстемп.
  4. Копіює dist\\JARVIS.exe -> <проєкт>\\JARVIS.exe та
     -> C:\\Users\\<user>\\OneDrive\\Desktop\\JARVIS\\JARVIS.exe.
  5. Друкує розміри, таймстемпи, sha256 і результат перевірки копій.

Режим onefile/console=False задається JARVIS.spec: PyInstaller забороняє
makespec-прапорці (--onefile, --windowed, --icon, --name) разом зі .spec,
тому ці параметри саме spec-driven, а не CLI.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ── шляхи проєкту ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
SPEC_PATH = PROJECT_ROOT / "JARVIS.spec"
ENTRY_SCRIPT = PROJECT_ROOT / "jarvis.py"
ASSETS_DIR = PROJECT_ROOT / "assets"
ICON_PATH = ASSETS_DIR / "jarvis.ico"

DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
BUILT_EXE = DIST_DIR / "JARVIS.exe"

PROJECT_EXE = PROJECT_ROOT / "JARVIS.exe"
WEBSITE_EXE = PROJECT_ROOT / "website" / "downloads" / "JARVIS.exe"

# OneDrive може називатися по-різному / лежати в іншому місці — дозволяємо
# перевизначити через змінні оточення, але типово беремо стандартний шлях.
ONEDRIVE_ROOT = Path(os.environ.get("JARVIS_ONEDRIVE_ROOT", Path.home() / "OneDrive"))
DESKTOP_EXE_DIR = Path(
    os.environ.get("JARVIS_DESKTOP_DIR", ONEDRIVE_ROOT / "Desktop" / "JARVIS")
)
DESKTOP_EXE = DESKTOP_EXE_DIR / "JARVIS.exe"

VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"

MIN_EXE_BYTES = 60 * 1024 * 1024  # sanity-check: робочий exe завжди > 60 МБ
PYINSTALLER_TIMEOUT_SEC = 3000    # 50 хв — запобіжник від вічного зависання

SUBSYSTEM_GUI = 2      # IMAGE_SUBSYSTEM_WINDOWS_GUI — те, що нам потрібно
SUBSYSTEM_CONSOLE = 3  # IMAGE_SUBSYSTEM_WINDOWS_CUI


# ══════════════════════════════════════════════════════════════════════════════
#  Допоміжні функції
# ══════════════════════════════════════════════════════════════════════════════
def configure_stdio() -> None:
    """UTF-8 для stdout/stderr, щоб український текст не ламався в консолі."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


def human_size(num_bytes: int) -> str:
    """Людяний розмір файлу: 77419727 -> '73.8 МБ'."""
    size = float(num_bytes)
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if size < 1024.0 or unit == "ГБ":
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} ГБ"


def sha256_of(path: Path) -> str:
    """SHA-256 файлу (потоково, щоб не тримати 77 МБ у пам'яті)."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pe_subsystem(path: Path) -> int | None:
    """Повертає PE-підсистему exe (2 = GUI, 3 = консоль) або None."""
    try:
        with path.open("rb") as fh:
            dos_header = fh.read(0x40)
            if len(dos_header) < 0x40 or dos_header[:2] != b"MZ":
                return None
            e_lfanew = int.from_bytes(dos_header[0x3C:0x40], "little")
            fh.seek(e_lfanew)
            # 4 (PE\0\0) + 20 (COFF) + 68 (OptionalHeader до Subsystem) + 2
            header = fh.read(4 + 20 + 68 + 2)
            if len(header) < 4 + 20 + 70 or header[:4] != b"PE\x00\x00":
                return None
            return int.from_bytes(header[24 + 68:24 + 70], "little")
    except OSError:
        return None


@dataclass
class FileState:
    """Стан одного файлу-артефакту для підсумкового звіту."""

    path: Path
    exists: bool = False
    size: int = 0
    mtime: datetime | None = None
    sha256: str = ""
    subsystem: int | None = None
    error: str = ""

    @classmethod
    def read(cls, path: Path, with_hash: bool = True) -> "FileState":
        state = cls(path=path)
        try:
            stat = path.stat()
        except FileNotFoundError:
            return state
        except OSError as exc:
            state.error = str(exc)
            return state
        state.exists = True
        state.size = stat.st_size
        state.mtime = datetime.fromtimestamp(stat.st_mtime)
        if with_hash:
            try:
                state.sha256 = sha256_of(path)
            except OSError as exc:
                state.error = str(exc)
        state.subsystem = pe_subsystem(path)
        return state

    def lines(self) -> list[str]:
        """Рядки для друку."""
        if not self.exists:
            return [f"  {self.path} — НЕМАЄ"]
        when = self.mtime.strftime("%Y-%m-%d %H:%M:%S") if self.mtime else "?"
        out = [
            f"  {self.path}",
            f"    розмір: {self.size:,} B ({human_size(self.size)}), "
            f"змінено: {when}, PE-підсистема: {self._subsystem_label()}",
        ]
        if self.sha256:
            out.append(f"    sha256: {self.sha256}")
        if self.error:
            out.append(f"    ПОМИЛКА: {self.error}")
        return out

    def _subsystem_label(self) -> str:
        if self.subsystem == SUBSYSTEM_GUI:
            return "2 (GUI, без консолі)"
        if self.subsystem == SUBSYSTEM_CONSOLE:
            return "3 (КОНСОЛЬ — це помилка для GUI-застосунку)"
        if self.subsystem is None:
            return "невідомо (не PE?)"
        return str(self.subsystem)


# ══════════════════════════════════════════════════════════════════════════════
#  Перевірка оточення і spec-контракту
# ══════════════════════════════════════════════════════════════════════════════
def check_spec_contract() -> list[str]:
    """Статично перевіряє JARVIS.spec на критичні властивості збірки."""
    if not SPEC_PATH.is_file():
        return [f"не знайдено spec-файл: {SPEC_PATH}"]

    text = SPEC_PATH.read_text(encoding="utf-8")
    problems: list[str] = []

    required = {
        r"collect_all\(\s*['\"]edge_tts['\"]\s*\)": "collect_all('edge_tts')",
        r"collect_all\(\s*['\"]pygame['\"]\s*\)": "collect_all('pygame')",
        r"collect_all\(\s*['\"]speech_recognition['\"]\s*\)": (
            "collect_all('speech_recognition')"
        ),
        r"console\s*=\s*False": "console=False (GUI без консольного вікна)",
        r"upx\s*=\s*True": "upx=True",
        r"name\s*=\s*['\"]JARVIS['\"]": "name='JARVIS'",
    }
    for pattern, label in required.items():
        if not re.search(pattern, text):
            problems.append(f"spec не містить: {label}")

    if re.search(r"console\s*=\s*True", text):
        problems.append("spec містить console=True — застосунок має бути windowed")

    if "COLLECT(" in text:
        problems.append(
            "spec містить COLLECT(...): це onedir-збірка, а не onefile"
        )

    if not re.search(r"\bSPECPATH\b", text):
        problems.append(
            "spec не використовує SPECPATH — шляхи можуть залежати від cwd"
        )

    return problems


def check_environment() -> tuple[list[str], list[str]]:
    """Повертає (помилки, попередження) для оточення збірки."""
    errors: list[str] = []
    warnings: list[str] = []

    if not ENTRY_SCRIPT.is_file():
        errors.append(f"немає точки входу: {ENTRY_SCRIPT}")
    if not SPEC_PATH.is_file():
        errors.append(f"немає spec-файлу: {SPEC_PATH}")
    if not ASSETS_DIR.is_dir():
        errors.append(f"немає каталогу ассетів: {ASSETS_DIR}")
    elif not ICON_PATH.is_file():
        warnings.append(
            f"немає іконки {ICON_PATH} — exe збереться з дефолтною іконкою"
        )

    try:
        import PyInstaller  # noqa: PLC0415 — перевірка вже в цьому інтерпретаторі

        pyi_version = PyInstaller.__version__
    except Exception as exc:  # pragma: no cover — залежить від оточення
        errors.append(
            f"PyInstaller не імпортується в {sys.executable}: {exc}\n"
            f"    підказка: запустіть через {VENV_PYTHON}"
        )
        pyi_version = "?"
    else:
        print(f"  PyInstaller: {pyi_version} (Python {sys.version.split()[0]})")

    if VENV_PYTHON.is_file():
        try:
            same = Path(sys.executable).resolve() == VENV_PYTHON.resolve()
        except OSError:
            same = False
        if not same:
            warnings.append(
                f"запущено не інтерпретатором .venv: {sys.executable}\n"
                f"    рекомендовано: {VENV_PYTHON} build_exe.py"
            )

    errors.extend(check_spec_contract())
    return errors, warnings


# ══════════════════════════════════════════════════════════════════════════════
#  Запущені процеси JARVIS.exe (щоб не отримати PermissionError при копіюванні)
# ══════════════════════════════════════════════════════════════════════════════
def running_jarvis_pids() -> list[int]:
    """PID-и запущених JARVIS.exe (лише Windows; інакше порожній список)."""
    if os.name != "nt":
        return []
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq JARVIS.exe", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    pids: list[int] = []
    for line in (proc.stdout or "").splitlines():
        cells = [cell.strip().strip('"') for cell in line.split(",")]
        if len(cells) > 1 and cells[0].lower() == "jarvis.exe":
            try:
                pids.append(int(cells[1]))
            except ValueError:
                continue
    return pids


def kill_jarvis(pids: list[int]) -> None:
    """Завершує процеси JARVIS.exe за PID (Windows taskkill)."""
    for pid in pids:
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            pass
    if pids:
        time.sleep(2.0)  # даємо ОС звільнити файлові блокування


# ══════════════════════════════════════════════════════════════════════════════
#  Збірка
# ══════════════════════════════════════════════════════════════════════════════
def build_command() -> list[str]:
    """Команда PyInstaller.

    --onefile/--console свідомо НЕ передаються: це makespec-опції, а PyInstaller
    відмовляється приймати їх разом зі .spec (режим заданий у spec-файлі).
    --distpath/--workpath тримають dist/ і build/ усередині проєкту.
    """
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--log-level",
        "INFO",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        str(SPEC_PATH),
    ]


def run_pyinstaller() -> float:
    """Запускає PyInstaller; повертає тривалість у секундах."""
    cmd = build_command()
    print("\n[2/5] Збірка PyInstaller…")
    print("  команда: " + " ".join(f'"{part}"' if " " in part else part for part in cmd))
    print(f"  cwd: {PROJECT_ROOT}\n")

    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            timeout=PYINSTALLER_TIMEOUT_SEC,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        print(
            f"\n[ПОМИЛКА] PyInstaller не завершився за "
            f"{PYINSTALLER_TIMEOUT_SEC} с: {exc}"
        )
        raise SystemExit(1)
    duration = time.monotonic() - started

    if proc.returncode != 0:
        print(f"\n[ПОМИЛКА] PyInstaller завершився з кодом {proc.returncode}")
        print("  повний лог — вище; також див. build\\JARVIS\\warn-JARVIS.txt")
        raise SystemExit(1)

    print(f"\n  збірка завершена за {duration:.1f} с")
    return duration


def verify_artifact(build_started: float) -> FileState:
    """Перевіряє свіжозібраний dist\\JARVIS.exe. Кидає SystemExit при проблемах."""
    print("\n[3/5] Перевірка зібраного exe…")
    state = FileState.read(BUILT_EXE)

    problems: list[str] = []
    if not state.exists:
        problems.append(f"не створено файл {BUILT_EXE}")
    else:
        if state.size < MIN_EXE_BYTES:
            problems.append(
                f"розмір {state.size:,} B ({human_size(state.size)}) "
                f"менший за очікуваний мінімум {MIN_EXE_BYTES:,} B — "
                f"схоже, збірка неповна"
            )
        if state.subsystem != SUBSYSTEM_GUI:
            problems.append(
                f"PE-підсистема = {state.subsystem} ({state._subsystem_label()}): "
                f"очікувалась GUI (2)"
            )
        if state.mtime is not None:
            age = time.time() - state.mtime.timestamp()
            if age > 3600:
                problems.append(
                    f"файл не свіжий: змінено {state.mtime:%Y-%m-%d %H:%M:%S} "
                    f"({age / 60:.0f} хв тому)"
                )
        if state.mtime is not None and state.mtime.timestamp() < build_started - 10:
            problems.append(
                "таймстемп exe старіший за початок збірки — "
                "PyInstaller не перезаписав файл?"
            )

    for line in state.lines():
        print(line)

    if problems:
        print("\n[ПОМИЛКА] Зібраний exe не пройшов перевірку:")
        for problem in problems:
            print(f"  • {problem}")
        raise SystemExit(1)

    print("  [OK] exe валідний, свіжий, GUI-підсистема")
    return state


# ══════════════════════════════════════════════════════════════════════════════
#  Копіювання артефактів
# ══════════════════════════════════════════════════════════════════════════════
def _copy_once(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def copy_artifacts(
    built: FileState,
    source: Path,
    targets: list[Path],
    running_pids: list[int],
    kill_running: bool,
) -> tuple[dict[Path, FileState], list[str]]:
    """Копіює exe у цілі та повертає (стани, помилки)."""
    states: dict[Path, FileState] = {}
    errors: list[str] = []

    for target in targets:
        print(f"\n  копіюю -> {target}")
        copied_ok = False
        for attempt in (1, 2):
            try:
                _copy_once(source, target)
                copied_ok = True
                break
            except PermissionError as exc:
                if attempt == 1 and running_pids and kill_running:
                    print(
                        f"  файл зайнятий (PID {running_pids}) — "
                        f"завершую JARVIS.exe (--kill-running)"
                    )
                    kill_jarvis(running_pids)
                    running_pids = []
                    continue
                hint = ""
                if running_pids:
                    hint = (
                        f" Запущений JARVIS.exe (PID {', '.join(map(str, running_pids))}) "
                        f"блокує файл: закрийте його або запустіть скрипт з --kill-running."
                    )
                errors.append(f"{target}: {exc}.{hint}")
                break
            except OSError as exc:
                errors.append(f"{target}: {exc}")
                break

        if copied_ok:
            state = FileState.read(target)
            states[target] = state
            problems = _check_copy(built, state)
            if problems:
                errors.extend(f"{target}: {problem}" for problem in problems)
            else:
                print("    [OK] копія збігається з dist-збіркою (розмір + sha256)")
        else:
            states[target] = FileState.read(target, with_hash=False)

    return states, errors


def _check_copy(built: FileState, copied: FileState) -> list[str]:
    """Перевіряє, що копія ідентична зібраному файлу."""
    problems: list[str] = []
    if not copied.exists:
        return ["копія не створена"]
    if copied.size != built.size:
        problems.append(
            f"розмір копії {copied.size:,} B != оригіналу {built.size:,} B"
        )
    if built.sha256 and copied.sha256 and built.sha256 != copied.sha256:
        problems.append("sha256 копії не збігається з dist-збіркою")
    return problems


# ══════════════════════════════════════════════════════════════════════════════
#  Дружній вивід
# ══════════════════════════════════════════════════════════════════════════════
def _print_list(title: str, lines: list[str]) -> None:
    if not lines:
        return
    print(f"\n{title}")
    for line in lines:
        print(f"  • {line}")


def print_existing_artifacts() -> None:
    """Показує поточні exe (для --check і для історії)."""
    print("\nІснуючі артефакти:")
    for path in (BUILT_EXE, PROJECT_EXE, DESKTOP_EXE):
        for line in FileState.read(path, with_hash=False).lines():
            print(line)


# ══════════════════════════════════════════════════════════════════════════════
#  Основні режими
# ══════════════════════════════════════════════════════════════════════════════
def run_check() -> int:
    """Режим --check: лише перевірка оточення/spec, без збірки."""
    print("=" * 78)
    print(" JARVIS build — перевірка оточення (без збірки)")
    print("=" * 78)
    print(f"  проєкт:     {PROJECT_ROOT}")
    print(f"  spec:       {SPEC_PATH}")
    print(f"  точка входу:{ENTRY_SCRIPT}")

    print("\n[1/2] Перевірка файлів, PyInstaller і spec-контракту…")
    errors, warnings = check_environment()

    _print_list("Попередження:", warnings)
    _print_list("Помилки:", errors)

    print("\n[2/2] Існуючі артефакти:")
    current = FileState.read(PROJECT_EXE, with_hash=False)
    for line in current.lines():
        print(line)
    desktop = FileState.read(DESKTOP_EXE, with_hash=False)
    print(f"  OneDrive-копія: {desktop.path} — "
          f"{'є, ' + human_size(desktop.size) if desktop.exists else 'НЕМАЄ'}")

    print("\n" + "=" * 78)
    if errors:
        print(f" РЕЗУЛЬТАТ: ПОМИЛКИ ({len(errors)}) — збірка неможлива")
        print("=" * 78)
        return 2
    print(" РЕЗУЛЬТАТ: OK — можна запускати збірку без --check")
    print("=" * 78)
    return 0


def run_build(args: argparse.Namespace) -> int:
    """Повний цикл: перевірка -> PyInstaller -> верифікація -> копіювання."""
    print("=" * 78)
    print(" JARVIS build — збірка JARVIS.exe (onefile, GUI)")
    print("=" * 78)
    print(f"  проєкт: {PROJECT_ROOT}")

    # ── 1. перевірки ─────────────────────────────────────────────────────────
    print("\n[1/5] Перевірка оточення та spec-контракту…")
    errors, warnings = check_environment()
    _print_list("Попередження:", warnings)
    if errors:
        _print_list("Помилки:", errors)
        print("\n[ПОМИЛКА] Оточення не готове до збірки.")
        return 2

    if DIST_DIR.exists():
        print(f"  dist: {DIST_DIR}")
    if BUILD_DIR.exists():
        print(f"  build: {BUILD_DIR} (--clean перебудує)")

    # ── 2. збірка ────────────────────────────────────────────────────────────
    build_started = time.time()
    duration = run_pyinstaller()

    # ── 3. верифікація зібраного exe ─────────────────────────────────────────
    built = verify_artifact(build_started)

    # ── 4. копіювання ────────────────────────────────────────────────────────
    print("\n[4/5] Копіювання exe у цільові місця…")
    running_pids = running_jarvis_pids()
    if running_pids:
        print(
            f"  УВАГА: знайдено запущені JARVIS.exe (PID: "
            f"{', '.join(map(str, running_pids))})"
        )
    else:
        print("  запущених JARVIS.exe немає")

    targets = [PROJECT_EXE, WEBSITE_EXE]
    if args.skip_desktop_copy:
        print("  OneDrive-копію пропущено (--skip-desktop-copy)")
    else:
        targets.append(DESKTOP_EXE)

    states, copy_errors = copy_artifacts(
        built=built,
        source=BUILT_EXE,
        targets=targets,
        running_pids=running_pids,
        kill_running=args.kill_running,
    )

    # ── 5. підсумок ──────────────────────────────────────────────────────────
    print("\n" + "=" * 78)
    print(" ПІДСУМОК")
    print("=" * 78)
    print(f"  час збірки: {duration:.1f} с ({duration / 60:.1f} хв)")
    print(f"  dist\\JARVIS.exe:")
    for line in built.lines():
        print(f"  {line}")

    print("\n  Копії:")
    for target, state in states.items():
        for line in state.lines():
            print(f"  {line}")

    if copy_errors:
        _print_list("Помилки копіювання:", copy_errors)
        print("\n[ПОМИЛКА] Збірка є, але копіювання не завершене повністю.")
        return 1

    print(
        "\n[OK] Готово: свіжий JARVIS.exe зібрано, перевірено та скопійовано "
        "в усі цільові місця."
    )
    print("     Тестовий запуск вручну: Start-Process <шлях>\\JARVIS.exe")
    print("=" * 78)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Збірка JARVIS.exe через PyInstaller (spec-driven onefile/GUI).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="лише перевірити оточення і spec, нічого не збирати",
    )
    parser.add_argument(
        "--skip-desktop-copy",
        action="store_true",
        help="не копіювати exe у OneDrive Desktop\\JARVIS",
    )
    parser.add_argument(
        "--kill-running",
        action="store_true",
        help="завершити запущені JARVIS.exe, якщо вони блокують файл при копіюванні",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    args = parse_args(argv)
    try:
        if args.check:
            return run_check()
        return run_build(args)
    except SystemExit as exc:  # verify_artifact/run_pyinstaller кидають SystemExit(1)
        return int(exc.code) if isinstance(exc.code, int) else 1
    except KeyboardInterrupt:
        print("\n[ПЕРЕРВАНО] Збірку скасовано користувачем.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
