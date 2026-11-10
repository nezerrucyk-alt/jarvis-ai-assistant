# J.A.R.V.I.S. — стан проєкту та точка відновлення

Оновлено: 2026-11-10 (вечір)

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
| Скріншоти й демо сайту | `C:\Users\nezer\Jarvis\website\assets\` |
| Генератор демо-відео | `C:\Users\nezer\AppData\Local\Temp\opencode\make_demo.py` |
| GitHub-репозиторій | `nezerrucyk-alt/jarvis-ai-assistant` |
| GitHub Pages | `https://nezerrucyk-alt.github.io/jarvis-ai-assistant/` |
| GitHub Release | `https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/tag/v2.0.0` |
| GitHub Pages workflow | `C:\Users\nezer\Jarvis\.github\workflows\pages.yml` |
| Демо-профіль для скріншотів | `C:\Users\nezer\AppData\Local\Temp\opencode\jarvis_demo\Jarvis\` |
| Лог останньої збірки | `C:\Users\nezer\Jarvis\build_last.log` |
| Журнал змін | `C:\Users\nezer\Jarvis\CHANGES_SUMMARY.md` |

## Актуальний білд

- Файл: `C:\Users\nezer\Jarvis\dist\JARVIS.exe`
- Розмір: **89 393 601 байт** (89.4 MB)
- SHA256: **1465CCC7AFF82355953E47E319FCACE1FA512BD2358C3C82B71B771073A190DB**
- Версія: 2.0.0 від 10.11.2026
- Скопійований у `JARVIS.exe`, на робочий стіл і в `website\downloads\JARVIS.exe`.

## Команда збірки

```powershell
cd C:\Users\nezer\Jarvis
& ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name JARVIS --icon "assets\jarvis.ico" --add-data "assets;assets" --collect-all edge_tts --collect-all pygame --collect-all speech_recognition --collect-all cryptography --collect-all psutil --collect-all pycaw --collect-all comtypes --hidden-import modules.mobile_bridge --hidden-import modules.coding_workspace jarvis.py
```

Після збірки:
1. Закрити всі `JARVIS.exe` (onefile = батько + дитина).
2. Скопіювати `dist\JARVIS.exe` у `C:\Users\nezer\Jarvis\JARVIS.exe`, на робочий стіл і в `website\downloads\JARVIS.exe`.
3. Запустити, почекати 10–15 с, перевірити хвіст `jarvis.log`.
4. Оновити розмір і SHA256 на сайті (`website/index.html`, блок `download-info`).

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
- Сайт: темна тема, hero, можливості, провайдери, скріншоти, демо-відео, плагіни, changelog, інструкція, відгуки, FAQ, лічильник завантажень, UA/EN.
- Демо-відео: `website/assets/demo.mp4` (30 с, 1280×720, H.264, ~4.8 MB), постер `demo-poster.jpg`.
- Локальна перевірка сайту через Playwright: 1440×7801, усі секції рендеряться, 0 console errors, 0 failed requests, відео `readyState=4`, мобільна ширина 390 без горизонтального скролу.

## Що ще зробити

1. Підключити Home Assistant (URL + токен) і протестувати на реальному інстансі.
2. Відкликати/перегенерувати ключ Ashna, який був показаний у чаті.
3. За бажанням: автооновлення exe, більше мов перекладу, Pro-сторінка.

## Важливі нюанси

- Плагіни не вбудовані в exe: вони читаються з `%APPDATA%\Jarvis\plugins` під час старту або після `plugin_reload`.
- `status.roblox.com/api/v2/...` не існує; робочий endpoint — `https://api.status.io/1.0/status/59db90dbcdeb2f04dadcf16d`.
- PowerShell у консолі плутає кирилицю; логи читати через Python з `encoding="utf-8"`.
- Перед заміною exe зупиняти всі процеси `JARVIS.exe` (onefile запускає батька й дитину).
- Для скріншотів використовувати `PrintWindow(hwnd, memdc, 1 | 2)`: `ImageGrab` ловить інші вікна, якщо Jarvis перекритий.
- GitHub Pages workflow підставляє `__GITHUB_REPOSITORY__` в `index.html`; прямі посилання на релізи будуються з цього рядка, локально JS падає на `nezerrucyk-alt/jarvis-ai-assistant`.
- `website/downloads/JARVIS.exe` ігнорується git (`.gitignore`), тому 89 MB не потраплять у репозиторій.
- Демо-відео згенеровано скриптом `make_demo.py` з реальних скріншотів; для перегенерації потрібні `imageio`, `imageio-ffmpeg`, `numpy`.
