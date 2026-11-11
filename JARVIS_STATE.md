# J.A.R.V.I.S. — стан проєкту та точка відновлення

Оновлено: 2026-11-11 (Command Deck / провайдери / черга)

## Де що лежить

| Що | Шлях |
|---|---|
| Основний код | `C:\Users\nezer\Jarvis\jarvis.py` |
| Модулі | `C:\Users\nezer\Jarvis\modules\` |
| Віртуальне середовище | `C:\Users\nezer\Jarvis\.venv\` |
| Збірка | `C:\Users\nezer\Jarvis\dist\JARVIS.exe` |
| Робоча копія | `C:\Users\nezer\Jarvis\JARVIS.exe` |
| Копія на робочому столі | `C:\Users\nezer\OneDrive\Desktop\JARVIS.exe` |
| Конфіг і ключі | `C:\Users\nezer\AppData\Roaming\Jarvis\config.json` |
| Історія чатів | `C:\Users\nezer\AppData\Roaming\Jarvis\chats.json` |
| Лог | `C:\Users\nezer\AppData\Roaming\Jarvis\jarvis.log` |
| Плагіни | `C:\Users\nezer\AppData\Roaming\Jarvis\plugins\` |
| Нотатки плагіна | `C:\Users\nezer\AppData\Roaming\Jarvis\notes.json` |
| Сайт | `C:\Users\nezer\Jarvis\website\` |
| Скріншоти й відео сайту | `C:\Users\nezer\Jarvis\website\assets\` |
| Генератор пояснювального відео | `C:\Users\nezer\AppData\Local\Temp\opencode\make_howto_video.py` (+ `howto_common.py`, `howto_scenes_a-d.py`) |
| GitHub-репозиторій | `nezerrucyk-alt/jarvis-ai-assistant` |
| GitHub Pages | `https://nezerrucyk-alt.github.io/jarvis-ai-assistant/` |
| GitHub Release | `https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/tag/v2.0.0` |
| GitHub Pages workflow | `C:\Users\nezer\Jarvis\.github\workflows\pages.yml` |
| Демо-профіль для скріншотів | `C:\Users\nezer\AppData\Local\Temp\opencode\jarvis_demo\Jarvis\` |
| Лог останньої збірки | `C:\Users\nezer\Jarvis\build_last.log` |
| Журнал змін | `C:\Users\nezer\Jarvis\CHANGES_SUMMARY.md` |

## Актуальний білд

Windows (локальна збірка):
- Файл: `C:\Users\nezer\Jarvis\dist\JARVIS.exe`
- Розмір: **89 523 472 байт** (85.4 MB)
- SHA256: **0D2AC79E449A4A63E8CEEC175006AE148A13733B19566497B01649DDEBCD53FA**
- Версія: 2.0.0 (з фічами оновлення/трею) від 10.11.2026
- Скопійований у `JARVIS.exe`, на робочий стіл і в `website\downloads\JARVIS.exe` (усі хеші збігаються).
- Запуск перевірено: 5 плагінів / 9 інструментів, трей активний, без traceback.

macOS і Linux (з GitHub Actions, реліз v2.0.0):
- `JARVIS-macOS.zip` — 75 877 396 байт, SHA256 `C1349A2A1990F65802B36A9F118BEE9CEAEDB1C8ADD1B391403A65062FE387B7`
- `JARVIS-Linux.tar.gz` — 105 176 023 байт, SHA256 `543687CD00A2B15D8119348DBCFE9A352BF544186C39C041DABA8D3C3B21AAA0`
- macOS: тільки Apple Silicon (arm64, M1–M4), `.app` без підпису.
- Linux: x86_64, один виконуваний файл `JARVIS`, потрібні X11/XWayland і аудіо-бібліотеки (`libportaudio2`, `libasound2`).

## Команда збірки

```powershell
cd C:\Users\nezer\Jarvis
& ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name JARVIS --icon "assets\jarvis.ico" --add-data "assets;assets" --collect-all edge_tts --collect-all pygame --collect-all speech_recognition --collect-all cryptography --collect-all psutil --collect-all pycaw --collect-all comtypes --collect-all pystray --hidden-import PIL.Image --hidden-import pystray._win32 --hidden-import modules.mobile_bridge --hidden-import modules.coding_workspace jarvis.py
```

Після збірки:
1. Закрити всі `JARVIS.exe` (onefile = батько + дитина).
2. Скопіювати `dist\JARVIS.exe` у `C:\Users\nezer\Jarvis\JARVIS.exe`, на робочий стіл і в `website\downloads\JARVIS.exe`.
3. Запустити, почекати 10–15 с, перевірити хвіст `jarvis.log`.
4. Оновити розмір і SHA256 у трьох картках завантаження на сайті (`website/index.html`, клас `platform-card`).

## Що вже зроблено

- Голосовий асистент: STT → LLM → TTS, чат, історія, багато моделей/провайдерів з failover.
- Керування ПК: команди PowerShell, файли, програми, гучність, медіа, вікна.
- Запуск програм за назвою: Start Menu, App Paths, реєстр, типові папки, транслітерація й fuzzy-пошук.
- Roblox Studio через офіційний `StudioMCP.exe` (stdio JSON-RPC).
- Vision (`Ctrl+Alt+S`) через xKiro Command A Vision.
- Переклад екрана (`Ctrl+Alt+T`) з overlay.
- Режим ґеймера й тихі підказки поверх гри.
- Smart Home через Home Assistant REST API (потрібно вписати URL і токен).
- Android bridge (`modules/mobile_bridge.py`) — виправлено імпорт cryptography.
- Налаштування: прокручуваний діалог, закріплені кнопки ЗБЕРЕГТИ/СКАСУВАТИ.
- 5 локальних плагінів: `quick_notes.py`, `weather.py`, `currency.py`, `pc_stats.py`, `roblox_status.py` (9 інструментів).
- Статус Roblox переведено на робочий status.io API.
- Виправлено порядок ініціалізації `_ui_queue`, через який застосунок падав під час завантаження плагінів.
- Інтерактивне оновлення: кнопка «⬆ Оновлення» / голос → перевірка GitHub Releases → діалог «Завантажити й перезавантажити?» → стрім-завантаження з перевіркою розміру/SHA256 → прихований PowerShell-updater (чекає виходу всіх `JARVIS.exe`, замінює exe з backup+rollback, запускає новий). Працює лише для exe; `.old` чиститься на старті.
- Автоперевірка оновлень на старті (9 с) + клікабельний банер у вікні (конфіг `auto_update_check`).
- Трей-іконка (pystray): закриття згортає у трей, меню «Відкрити / Перевірити оновлення / Вихід» (конфіг `minimize_to_tray`, graceful-fallback якщо pystray недоступний).
- Переклад екрана: 19 мов (було 4) — додано FR/ES/IT/PT/CS/SK/RO/BG/TR/NL/ZH/JA/KO.
- STT/TTS: 14 мов і 30 голосів edge_tts (було 3 мови / 8 голосів).
- Home Assistant: крім on/off/toggle/brightness/scene/script — клімат (set_temp, hvac), cover open/close/stop, lock/unlock, media play/pause/next/previous, vacuum_start/dock, camera.
- `check_update` інструмент для LLM + 27 регресійних тестів у `tests/test_16_updates_and_languages.py`.
- Сайт: темна тема, hero, можливості, провайдери, скріншоти, демо-відео, плагіни, changelog, інструкція, сценарії використання, FAQ, лічильник завантажень, UA/EN.
- Встановлення на сайті розділене на вкладки Windows / macOS / Linux: 3 кроки для Windows, 4 для macOS і Linux, окремі застереження (SmartScreen, Gatekeeper, X11/Wayland).
- Три картки завантаження з розмірами й копіюванням SHA256; посилання на релізні ассети підставляються з GitHub API, є fallback на `releases/latest/download/...`.
- Секцію вигаданих відгуків замінено на чесні «Сценарії використання» з посиланням на GitHub issues.
- Пояснювальне відео: `website/assets/how-it-works.mp4` (2:02, 1920×1080, 30 fps, H.264/AAC, ~7.4 MB, українська озвучка `uk-UA-OstapNeural`), постер `how-it-works-poster.jpg` (1920×1080, ~163 KB), субтитри `how-it-works.uk.vtt` / `how-it-works.en.vtt` (30/31 репліка, пропорційний таймінг).
- Секція `#demo` використовує нове відео з двома доріжками субтитрів; старий 30-секундний `demo.mp4` більше не підключений.
- Локальна перевірка сайту через Playwright: 1440×7801, усі секції рендеряться, 0 console errors, 0 failed requests, відео `readyState=4`, мобільна ширина 390 без горизонтального скролу, перемикання трьох вкладок ОС і правильні посилання на всі три ассети.
- Відео опубліковано на GitHub Pages (коміти `5b76d12`, `8d236b6`); live-перевірка: `readyState=4`, 1920×1080, 122.97 с, 2 доріжки субтитрів, EN-перемикач, мобільна 390 без overflow, 0 console errors.

## Command Deck / нові провайдери (2.1.0)

- Новий UI «Command Deck»: темно-синій фон, бокова навігація 232 px, компактний reactor-hero, стрічка діалогу, черга завдань, нижній командний рядок. Мінімум 900×640, стандарт 1240×860.
- Нижній composer: `+` (файл / скріншот / буфер), модель, режим (додано «Макс»), «У чергу», стрілка надсилання. Enter — надіслати, Shift+Enter — новий рядок, Ctrl+Enter — у чергу.
- Вкладення: до 8 файлів; зображення стискаються в JPEG і йдуть як `image_url` (OpenAI) або base64-блок (Anthropic), текстові файли — у fenced-блок; назви зберігаються в історії чату.
- Черга: in-memory, знімок тексту/вкладень/моделі/режиму/озвучення; запускається після завершення поточної відповіді.
- Прямі провайдери: OpenAI (`gpt-6.1-sol`, `gpt-5.6-sol`, `gpt-5.3-codex`), Anthropic (`claude-opus-5.5`, `claude-sonnet-5.5`, `claude-haiku-5`, нативний Messages API + tool loop), xAI (`grok-4.7`, `grok-4.7-fast`), Moonshot (`kimi-k3`, `kimi-k2.7-code`), Qwen/DashScope (`qwen3.8-max`, `qwen3-coder-plus`, `qwen3-vl-plus`), Cursor (`composer-2.5`, експериментальний OpenAI-сумісний endpoint через `cursor_api_url`/`cursor_model`).
- Налаштування: додано поля ключів усіх нових провайдерів, Cursor URL/model, оновлено `selftest` і тест з’єднання.
- `core/config.py` і `core/model_router.py` синхронізовано: нові провайдери, `max` режим, Anthropic payload, Cursor endpoint/model.
- Додано `tests/test_17_providers_queue.py`: 8 тестів на провайдерів, Anthropic-конвертацію, vision/text-вкладення, чергу й модель/режим.
- Сайт оновлено: нові скріншоти Command Deck і налаштувань, 78 моделей, 16 провайдерів, нові chips, changelog 2.1.0.
- Windows-збірка: `dist/JARVIS.exe`, 89 567 989 байт, SHA256 `6D31F77B8EE221062CE728D6747A1C2E6213DBEEC40FE7532A86EAF40431A3EC`. Версія `APP_VERSION = "2.1.0"`.
- Реліз `v2.1.0`: https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/tag/v2.1.0
  - `JARVIS.exe` — 89 567 989 байт, SHA256 `6D31F77B8EE221062CE728D6747A1C2E6213DBEEC40FE7532A86EAF40431A3EC`.
  - `JARVIS-macOS.zip` — 75 728 703 байти, SHA256 `E8652BFD32E9338D316ACBE2E27B8329E3AC9804B539FF369105B4A0D5D19ABE`.
  - `JARVIS-Linux.tar.gz` — 105 274 532 байти, SHA256 `928B932B8DBB9FD75CCA790DE063D36566A05938D4FA517EB48EE828553337F0`.
- Повний прогін тестів: 115 тестів, 2 давні failures у `test_15_security` (перевірки `os.startfile` і тексту відмови `_write_file`), які відтворюються на HEAD `8d236b6`. Тест версії `modules` оновлено під 2.1.0.

## Що ще зробити

1. Підключити Home Assistant (URL + токен) і протестувати на реальному інстансі.
2. Відкликати/перегенерувати ключ Ashna, який був показаний у чаті.
3. Додати Intel-збірку macOS (зараз лише Apple Silicon) або позначити це на сайті ще помітніше.
4. Перевірити новий `release.yml` на наступному тегу: публікація має спрацьовувати навіть якщо Android падає.
5. Апдейтер, трей, автоперевірка, мови й HA вже у зібраному білді (Windows). Для публікації релізу — перезібрати macOS/Linux через GitHub Actions і закомітити `jarvis.py` + тести.
6. Реліз `v2.1.0` створено, усі три ассети завантажено. Залишилось задеплоїти оновлений сайт (пуш `main`) і перевірити live-версію.

## Важливі нюанси

- Плагіни не вбудовані в exe: вони читаються з `%APPDATA%\Jarvis\plugins` під час старту або після `plugin_reload`.
- `status.roblox.com/api/v2/...` не існує; робочий endpoint — `https://api.status.io/1.0/status/59db90dbcdeb2f04dadcf16d`.
- PowerShell у консолі плутає кирилицю; логи читати через Python з `encoding="utf-8"`.
- Перед заміною exe зупиняти всі процеси `JARVIS.exe` (onefile запускає батька й дитину).
- Для скріншотів використовувати `PrintWindow(hwnd, memdc, 1 | 2)`: `ImageGrab` ловить інші вікна, якщо Jarvis перекритий.
- GitHub Pages workflow підставляє `__GITHUB_REPOSITORY__` в `index.html`; прямі посилання на релізи будуються з цього рядка, локально JS падає на `nezerrucyk-alt/jarvis-ai-assistant`.
- `website/downloads/JARVIS.exe` ігнорується git (`.gitignore`), тому 89 MB не потраплять у репозиторій.
- `.github/workflows/release.yml`: `publish` тепер має `if: always() && ... && needs.desktop.result == 'success'`, тому падіння Android не блокує публікацію desktop-ассетів.
- `requirements.txt`: `pycaw` і `comtypes` позначені `; sys_platform == "win32"`, щоб не ламати Linux/macOS-збірки.
- macOS і Linux не мають глобальних гарячих клавіш, повного керування ПК, ґеймерського оверлею та Roblox Studio — це лише Windows. Решта (чат, голос, плагіни, vision, переклад, Home Assistant) працює всюди.
- Пояснювальне відео генерується скриптами `make_howto_video.py` + `howto_common.py` + `howto_scenes_a-d.py`; потрібні `edge-tts`, `imageio-ffmpeg`, `Pillow`, `numpy`. TTS кешується в `howto_build\voice_*.mp3`, запускати треба з `C:\Users\nezer\AppData\Local\Temp\opencode`, щоб знайшлися сусідні модулі.
