# J.A.R.V.I.S. — що змінилося (версія 2.1.0)

Оновлено: 11.11.2026

## Головне в цьому білді

- Новий інтерфейс «Command Deck»: бокова навігація, reactor-hero, стрічка діалогу, черга завдань і нижній командний рядок. Мінімум 900×640, стандарт 1240×860.
- Нижній composer: `+` для файлів/скріншотів/буфера, вибір моделі, вибір режиму (додано «Макс»), «У чергу», стрілка надсилання; Enter / Shift+Enter / Ctrl+Enter.
- Вкладення до 8 файлів: зображення йдуть у vision-моделі, текстові файли — у контекст; назви зберігаються в історії.
- Черга промптів зі знімком моделі, режиму, озвучення й вкладень; наступне завдання стартує після завершення поточного.
- Нові прямі провайдери: OpenAI, Anthropic (нативний Messages API + tools), xAI, Moonshot/Kimi, Qwen/DashScope, Cursor (експериментальний OpenAI-сумісний endpoint).
- Налаштування й `selftest` розширено новими ключами; `core/config.py` і `core/model_router.py` синхронізовано.
- Додано `tests/test_17_providers_queue.py` (8 тестів). Повний прогін: 115 тестів, 2 давні failures у `test_15_security`, які відтворюються на HEAD `8d236b6`.
- Сайт оновлено новими скріншотами (Command Deck 1240×860, налаштування 700×980), цифрами 78 моделей / 16 провайдерів і chips.
- Windows-збірка: `dist/JARVIS.exe`, 89 567 989 байт, SHA256 `6D31F77B8EE221062CE728D6747A1C2E6213DBEEC40FE7532A86EAF40431A3EC`.
- macOS: `JARVIS-macOS.zip`, 75 728 703 байти, SHA256 `E8652BFD32E9338D316ACBE2E27B8329E3AC9804B539FF369105B4A0D5D19ABE`.
- Linux: `JARVIS-Linux.tar.gz`, 105 274 532 байти, SHA256 `928B932B8DBB9FD75CCA790DE063D36566A05938D4FA517EB48EE828553337F0`.
- Реліз: https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/tag/v2.1.0

## Попередній білд — 2.0.0

### Плагіни
- Система локальних плагінів: `%APPDATA%\Jarvis\plugins\*.py`.
- API: список `TOOLS` + `run(name, args, ctx)`, доступні `ctx.confirm`, `ctx.log`, `ctx.run`, `ctx.cfg`, `ctx.data_dir`.
- 5 стартових плагінів, 9 інструментів:
  - `quick_notes.py` — нотатки: додати, показати, шукати, видалити.
  - `weather.py` — погода й прогноз без API-ключа.
  - `currency.py` — курси НБУ та конвертація.
  - `pc_stats.py` — CPU, RAM, диск, аптайм, батарея, топ процесів.
  - `roblox_status.py` — живий статус Roblox через status.io.
- Гаряче перезавантаження командою `plugin_reload`.

### Виправлення
- Падіння на старті: `_ui_queue` тепер створюється до `PcTools` і завантаження плагінів.
- `modules/mobile_bridge.py`: правильний імпорт `hashes, serialization` з cryptography.
- Налаштування: прокручуваний діалог, закріплені кнопки ЗБЕРЕГТИ / СКАСУВАТИ.
- Статус Roblox переведено з неіснуючого `status.roblox.com/api/v2` на `https://api.status.io/1.0/status/59db90dbcdeb2f04dadcf16d`.
- У збірку додано `cryptography`, `psutil`, `pycaw`, `comtypes`.

### Кросплатформність
- Додано збірки для macOS (Apple Silicon, `.app` у `.zip`) і Linux (x86_64, один файл у `.tar.gz`).
- macOS: дані в `~/Library/Application Support/Jarvis`; Linux: `~/.local/share/Jarvis` (або `$XDG_DATA_HOME`).
- Глобальні гарячі клавіші, повне керування ПК, ґеймерський оверлей і Roblox Studio залишилися Windows-only; на macOS/Linux доступні чат, голос, плагіни, vision, переклад і Home Assistant.
- Linux: потрібні X11/XWayland і `libportaudio2`/`libasound2`; macOS: непідписаний `.app`, Gatekeeper обходиться через «Open» або `xattr`.
- `release.yml`: публікація релізу більше не блокується падінням Android; `pycaw`/`comtypes` стали Windows-only в `requirements.txt`.

### Сайт
- Повністю переписаний `website/index.html` + `assets/styles.css` + `assets/app.js`.
- Розділи: hero, статистика, можливості, провайдери, скріншоти, демо-відео, плагіни, changelog, встановлення, сценарії використання, завантаження/Pro, FAQ, footer, JSON-LD.
- Встановлення розділене на вкладки Windows / macOS / Linux з покроковими інструкціями й застереженнями для кожної ОС.
- Три картки завантаження з розмірами, SHA256 і копіюванням у буфер; посилання підтягуються з GitHub Releases API з fallback на `releases/latest/download/...`.
- Перемикач UA/EN, мобільне меню, lightbox для скріншотів.
- Преміум-редизайн: aurora-фон, скляна навігація, hero з tilt-мокапом і orbit-кільцями, окрема секція `#deck` з макетом Command Deck (черга, composer, модель/режим), scroll-reveal, spotlight-картки, анімовані лічильники, рекомендована ОС, копіювання коду плагіна, прогрес скролу, кнопка «вгору».
- У футері — блок «Соцмережі творця» з TikTok `@nezer_kicc`; посилання також у JSON-LD `sameAs`.
- Лічильник завантажень через GitHub Releases API; локальний fallback — `downloads/JARVIS.exe`.
- Пояснювальне відео 2:02, 1920×1080, 30 fps, H.264/AAC: `website/assets/how-it-works.mp4`; постер `how-it-works-poster.jpg`.
- Українська озвучка `uk-UA-OstapNeural`, тиха фонова музика, 10 сцен: голос і чат, фейловер провайдерів, керування ПК, Roblox Studio, зір екрана й переклад, плагіни, приватність, платформи, фінал.
- Субтитри `how-it-works.uk.vtt` і `how-it-works.en.vtt` — окремі речення з пропорційним таймінгом; обидві доріжки підключені до `<video>`.
- Старий 30-секундний `demo.mp4` / `demo-poster.jpg` лишилися в assets як архів, але сайт на них більше не посилається.
- Свіжі скріншоти головного вікна (1180×820) і налаштувань (700×980) з актуального білда.
- Вигадані відгуки замінено на чесні «Сценарії використання».

### Збірка
- `dist\JARVIS.exe`, `--onefile --windowed`.
- Розмір: 89 393 601 байт.
- SHA256: `1465CCC7AFF82355953E47E319FCACE1FA512BD2358C3C82B71B771073A190DB`.
- Скопійовано в `C:\Users\nezer\Jarvis\JARVIS.exe`, на робочий стіл і в `website\downloads\JARVIS.exe`.
- Перевірено запуск: 5 плагінів / 9 інструментів, без `ModuleNotFoundError`.

## Важливо
- **Ключ Ashna був показаний у чаті — його треба відкликати й згенерувати новий.** Зовнішній Ashna API потребує платного плану; Jarvis автоматично перемикається на xKiro.
- Плагіни не вбудовані в exe — вони читаються з `%APPDATA%\Jarvis\plugins` під час старту або після `plugin_reload`.
- Конфіг, чати та плагіни живуть у `%APPDATA%\Jarvis`, тому заміна exe не стирає дані.
- Home Assistant ще не підключений: потрібно вписати URL і токен у Налаштуваннях.

## Що далі
1. Підключити Home Assistant і протестувати на реальному інстансі.
2. Відкликати старий ключ Ashna.
3. Додати Intel-збірку macOS (зараз лише Apple Silicon).
4. За бажанням: Pro-сторінка, автооновлення exe.

## Публікація
- Сайт: https://nezerrucyk-alt.github.io/jarvis-ai-assistant/
- Реліз: https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/tag/v2.0.0
- Ассети:
  - `JARVIS.exe` — Windows 10/11 x64, 89 393 601 байт, SHA256 `1465CCC7AFF82355953E47E319FCACE1FA512BD2358C3C82B71B771073A190DB`.
  - `JARVIS-macOS.zip` — macOS 11+ Apple Silicon, 75 877 396 байт, SHA256 `C1349A2A1990F65802B36A9F118BEE9CEAEDB1C8ADD1B391403A65062FE387B7`.
  - `JARVIS-Linux.tar.gz` — Linux x86_64, 105 176 023 байт, SHA256 `543687CD00A2B15D8119348DBCFE9A352BF544186C39C041DABA8D3C3B21AAA0`.
