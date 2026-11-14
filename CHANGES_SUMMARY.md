# J.A.R.V.I.S. — що змінилося (версія 2.2.0)

Оновлено: 14.11.2026

## Головне в цьому білді

- Wake word «Hey Jarvis»: локальний openWakeWord, резервний VAD + Google STT, cooldown і до трьох реплік продовження без натискання кнопки.
- Повний офлайн-режим: Ollama для Brain, опційні whisper.cpp для STT і Piper для TTS; хмарні ключі ігноруються.
- Довготривала пам'ять із локальними хеш-embeddings `hash-v1` (384 виміри): до промпту потрапляють найрелевантніші записи, а не останні 30.
- Планові автоматизації: `once`, `daily`, `weekly`, `every`; дії `prompt` і `notify`; вікно менеджера й три інструменти. Без свавільного shell.
- Локальний marketplace плагінів: JSON-реєстр, перевірка SHA256, ліміт розміру, захист від path traversal і явне підтвердження.
- Вкладка «Кастомізація»: теми, пресети, порядок блоків, шрифти, анімації, живе прев'ю й редактор кастомного коду.
- Повний прогін тестів: **197 тестів OK**.
- Реліз: https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/tag/v2.2.0

## Попередній білд — 2.1.0

Оновлено: 11.11.2026

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
1. Живий тест мікрофона: «Hey Jarvis», поріг `wake_word_threshold`, cooldown і три репліки продовження.
2. Перевірити офлайн-режим на реальній Ollama; за бажанням підключити whisper.cpp/Piper.
3. Перевірити marketplace (встановлення/видалення, SHA256 mismatch) і автоматизації (once/daily/weekly/every).
4. Розібрати 10 Dependabot PR і оновити залежності, якщо CI зелений.
5. Home Assistant URL/токен, ротація ключа Ashna, Android CI, Intel macOS і комерційний підпис.

## Публікація
- Сайт: https://nezerrucyk-alt.github.io/jarvis-ai-assistant/
- Реліз: https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/tag/v2.2.0
- Ассети:
  - `JARVIS-Windows.exe` — Windows 10/11 x64, 98 732 260 байт, SHA256 `9970333DD0183D5EE64F8E448DAB3DCC8EE7DCD6B5CC4A6DAAFFC3C76528296A`.
  - `JARVIS-macOS.zip` — macOS 11+ Apple Silicon, 81 075 776 байт, SHA256 `3DD71456378108316122B3B0720085E70D75649C05B66529DE820BB087CB5D11`.
  - `JARVIS-Linux.tar.gz` — Linux x86_64, 110 618 107 байт, SHA256 `933D05E6E17FBDE348BC48FE711F4C3409215302F08D1068B06EC4C577BBF060`.
- `SHA256SUMS.txt` і GitHub build provenance опубліковані; атестації пройшли.
