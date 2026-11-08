# Архітектура J.A.R.V.I.S.

Документ описує фактичний устрій проєкту в `корені репозиторію`: дві точки
входу (v1 та v2), рушії, інструменти, модель даних і модель потоків.
README з інструкціями запуску/збірки — [../README.md](../README.md).

---

## 1. Огляд

Проєкт містить **дві незалежні архітектури**, які живуть в одній теці та
ділять один файл налаштувань (`%APPDATA%\Jarvis\config.json`):

| | v1 — робочий застосунок | v2 — модульний «ULTIMATE» |
|---|---|---|
| Точка входу | `jarvis.py` | `main.py` |
| Розмір | ~4.4 тис. рядків, один файл | пакети `core/`, `agents/`, `ui/`, `memory/`, `modules/` |
| UI | Tk-вікно з реактором, сайдбаром історії, діалогами | Tk-Dashboard зі статусами агентів |
| LLM | `Brain` + `DIRECT_MODEL_CONFIG` + OpenRouter-фолбеки | `ModelRouter` з профілями задач |
| Інструменти | `PcTools` (17 інструментів) + Roblox Studio MCP | `agents/*` + `SecurityEngine` |
| Історія | `chats.json` (локальні JSON-файли) | SQLite `jarvis_ultimate.db` |
| Голос | `Voice` (edge-tts + pygame, fallback SAPI) / `Ears` (VAD + Google STT) | `modules/voice/` (у розробці) |
| Пакетування | `JARVIS.spec` → `JARVIS.exe` (onefile, GUI) | ще не пакетується |
| Статус | **готовий до використання** | каркас, триває наповнення |

---

## 2. Версія v1 (`jarvis.py`)

Монолітний Tk-застосунок. Нижче — логічні підсистеми, які всередині одного
файлу, але слабко зв'язані між собою.

### 2.1 Точка входу та життєвий цикл

```
main()
 ├─ DATA_DIR.mkdir(%APPDATA%\Jarvis)
 ├─ logging.basicConfig(FileHandler(jarvis.log) + StreamHandler)
 ├─ log "START exe=… prefix=… base_prefix=… requests=… cwd=…"
 ├─ sys.excepthook → logging.error("Unhandled exception", exc_info=…)
 ├─ if "--selftest": selftest() → return
 └─ JarvisApp(tk.Tk())  → root.mainloop()
```

* `APP_DIR = Path(__file__).resolve().parent` — каталог `jarvis.py`; в
  onefile-exe це тимчасова тека `%TEMP%\_MEI…`, тому `assets/` шукаються поруч
  із розпакованим exe, а не в теці запуску.
* `DATA_DIR = %APPDATA%\Jarvis` — єдине місце для конфігурації, історії, логів.
* `--selftest` перевіряє: конфіг, мікрофони (`sounddevice`), LLM (`Brain.ask`),
  інструмент `system_info`, TTS. Корисно для діагностики без запуску GUI.
* Глобальний `sys.excepthook` пише необроблені винятки в `jarvis.log`.

### 2.2 `Brain` — LLM-оркестрація і fallback-ланцюг

`Brain(cfg)` зберігає історію діалогу в пам'яті (`history`, для контексту
моделі) і виконує `ask(text, tool_runner=None)`.

**Каталоги моделей:**

* `DIRECT_MODEL_CONFIG` — прямі OpenAI-сумісні ендпоінти провайдерів:

  | Провайдер | Ключ у конфігу | Моделі (приклади) |
  |---|---|---|
  | xKiro | `xkiro_api_key` + `xkiro_backup_key` + `xkiro_keys[]` | `xkiro/qwen/qwen3.7-flash:free`, `…coder-plus`, `…qwen3.8-max`, `…deepseek-v4.1-flash` |
  | Google Gemini | `gemini_api_key` | `gemini-direct/gemini-3.8-flash`, `…3.5-flash-lite` |
  | Groq | `groq_api_key` | `groq-direct/openai/gpt-oss-20b`, `…120b`, `…qwen3.8-27b` |
  | DeepSeek | `deepseek_api_key` | `deepseek-direct/deepseek-chat` |
  | Cerebras | `cerebras_api_key` | `cerebras-direct/llama-3.3-70b` |
  | Mistral | `mistral_api_key` | `mistral-direct/mistral-small-latest` |
  | Together | `together_api_key` | `together-direct/…` |
  | Ashna | `ashna_api_key` | `ashna/…` (Kimi, GPT-Codex, DeepSeek, Claude) |

* `MODELS` + `FALLBACK_MODELS` — каталог ID; `FALLBACK_MODELS` — пріоритетний
  список після вибраної моделі.
* OpenRouter (`https://openrouter.ai/api/v1/chat/completions`) — універсальний
  фолбек для будь-якого `vendor/model`, якщо є `openrouter_key`.

**Порядок кандидатів** (`_candidates`):

1. `model` з конфігу;
2. `FALLBACK_MODELS`;
3. решта `MODELS`;
4. для direct-моделей — **по одному кандидату на кожен доступний ключ**
   (ротація ключів поля + `xkiro_keys`);
5. «останній вдалий» `(model, key)` піднімається на початок;
6. ключі, що дали постійну помилку квоти (`_dead_keys`), пропускаються.

`ask()` перебирає кандидатів, доки хтось не відповість; помилки збираються і
пишуться в лог. Кожна відповідь супроводжується рядком
`Відповідь від <Provider> (<model>)`.

**Побудова запиту** (`_build_messages`):
`SYSTEM_PROMPT` + інструкція вибраного **режиму відповіді** + останні
`max_history` повідомлень + (за `use_memory`) збережена пам'ять + текст
користувача.

**Режими відповіді** (`RESPONSE_MODES`, ключ `response_mode`):

| Ключ | Назва в UI | max_tokens |
|---|---|---|
| `natural` | Розмова | 1100 |
| `brief` | Коротко | 500 |
| `detailed` | Докладно | 1800 |
| `coding` | Код | 1800 |
| `review` | Сувора оцінка | 1400 |

**Tool-calling loop** (`_ask_candidate`): до 4 кроків «модель → `tool_calls` →
`tool_runner` → результат у контекст → фінальна відповідь». Доступність
інструментів залежить від `full_access`:

* `full_access: true` → усі `TOOLS`;
* `full_access: false` → лише «безпечний» набір `RESTRICTED_TOOL_NAMES`
  (пошук у вебі, пам'ять, нагадування, GitHub, скидання Roblox-сервера).

### 2.3 `PcTools` — інструменти та безпека

`PcTools(confirm, log, get_cfg)` — реєстр методів `_<tool_name>`; `run(name, args)`
викликає відповідний метод, ловить `TypeError` (неправильні аргументи) та інші
помилки, повертає текстовий результат для моделі.

| Інструмент | Призначення | Захист |
|---|---|---|
| `open_app` | відкрити сайт/застосунок за alias або URL (Chrome/Edge/notepad/calc/explorer/VSCode/…, YouTube/Google/GitHub/Telegram/… ) | `full_access` для desktop-застосунків |
| `run_powershell` | виконати PowerShell-команду | катастрофічні патерни блокуються; небезпечні — через підтвердження |
| `find_files` | пошук файлів за шаблоном | read-only, обмежена кількість |
| `read_file` | читання тексту (з обрізанням) | read-only |
| `write_file` | запис/допис файлу | підтвердження |
| `web_search` | пошук у вебі | read-only |
| `github_search`, `github_repo_info` | GitHub API | read-only |
| `memory_save/list/forget` | локальна пам'ять (`memory.json`) | паролі/ключі не зберігаються; ліміт 100 записів |
| `reminder_create/list/cancel` | нагадування (`reminders.json`) | ліміт 100 активних; час у майбутньому |
| `roblox_reset_server` | відкрити сторінку приватного сервера | підтвердження |
| `roblox_studio` | виклик інструмента Roblox Studio через MCP-міст | підтвердження |
| `system_info` | CPU/RAM/диск/ОС через `ctypes`/`wmic` | read-only |

Механізм підтвердження: `confirm(action, detail) -> bool` — у GUI це
модальне вікно «ПОТРІБЕН ДОЗВІЛ» з кнопками «ДОЗВОЛИТИ/ВІДМОВИТИСЬ»;
виклик із робочого потоку блокується на `threading.Event`, а вікно
показується в Tk-потоці через `root.after(0, …)`.

### 2.4 `StudioMCP` — міст до Roblox Studio MCP

Окремий клас-клієнт для локального **StudioMCP** (Roblox Studio MCP-сервер):

* пошук виконуваного файлу: змінна оточення `ROBLOX_STUDIO_MCP` → шлях до
  `.exe`/`.bat`; інакше `%LOCALAPPDATA%\Roblox\Versions\*\StudioMCP.exe`,
  `%LOCALAPPDATA%\Roblox\StudioMCP\**\StudioMCP.exe`, `…\mcp.bat`;
* запуск як підпроцесу, обмін **JSON-RPC по stdin/stdout** (`_exchange`);
  окремі daemon-потоки читають stdout (у `queue.Queue`) і stderr (у лог);
* `tool_names()`, `tool_schema(name)`, `call(tool, arguments)` — моделі
  надаються схеми MCP-інструментів, виклики проксуються в Studio;
* `first_studio_id()` — вибір першої відкритої Studio-сесії;
* синглтон `get_studio_bridge()/close_studio_bridge()`; коректне закриття
  підпроцесу під час виходу.

### 2.5 `Voice` — синтез мовлення (TTS)

```
speak(text) → for_speech(text) → edge-tts.Communicate(voice) → temp .mp3
            → pygame.mixer.music.play()  (стоп за потреби)
            → виняток/немає мережі → pyttsx3 (SAPI5) — fallback
```

* `for_speech()` чистить текст перед озвученням: Markdown, код-блоки, URL,
  зайві символи — щоб не читати «зворотні лапки» й «зірочки».
* `stop()` зупиняє відтворення (кнопка «СТОП», новий запит).
* `mute: true` у конфігу → TTS не запускається (кнопка «ЗВУК: ВИМК/УВІМК»).
* Голос і мова беруться з `voice` / `language`; типово `uk-UA-OstapNeural`.

### 2.6 `Ears` — розпізнавання мовлення (STT)

* Запис через `sounddevice.InputStream` (16 кГц, моно, float32, блоки 100 мс).
* **RMS-VAD**: перші 4 блоки — оцінка шуму, поріг `max(0.008, шум·2.5)`,
  тиша 1.2 с завершує запис; якщо мовлення не почалося за 6 с — `None`;
  жорсткий ліміт 20 с.
* `transcribe(raw, lang)` — `speech_recognition` + Google Web Speech;
  мова з конфігу (`uk-UA`), з фолбеками (напр. `ru-RU`).
* Помилки мікрофона перетворюються на `EarsError` з українським текстом.

### 2.7 Локальні сховища та модель даних

Усі файли — у `%APPDATA%\Jarvis`. JSON-сховища читаються/пишуться через
`load_local_records` / `save_local_records` під `LOCAL_STORE_LOCK` (RLock),
запис атомарний: `.tmp` → `Path.replace()`.

**`config.json`** — плоский словник (див. таблицю в README); при старті
`DEFAULT_CONFIG` зливається з файлом, відсутні ключі додаються; невідомі
зберігаються як є.

**`chats.json`** — список чатів, відсортований за `updated` (новіші перші):

```json
[
  {
    "id": "cht_1a2b3c4d5e",
    "title": "Нова розмова",
    "created": "2026-11-07T13:40:26",
    "updated": "2026-11-07T13:41:02",
    "messages": [
      {"who": "you",   "text": "привіт", "t": "2026-11-07T13:40:30"},
      {"who": "jarvis","text": "Вітаю, сер.", "t": "2026-11-07T13:40:31"},
      {"who": "sys",   "text": "…", "t": "…"}
    ]
  }
]
```

* `MAX_CHATS = 60` (зайві обрізаються), `MAX_CHAT_MESSAGES = 400` на чат;
* заголовок чату виводиться з першого повідомлення користувача;
* пошкоджений/відсутній файл не валить застосунок — історія починається з
  нуля (`load_local_records` повертає `[]` і пише помилку в лог);
* збереження дебаунситься (`_schedule_chats_save`) і примусово виконується
  під час перемикання чату/закриття вікна.

**`memory.json`** — список фактів:

```json
[{"id": "a1b2c3d4", "text": "…", "created_at": "2026-11-06T22:10:00"}]
```

**`reminders.json`** — список нагадувань:

```json
[{"id": "e5f6a7b8", "text": "…", "when": "2026-11-08T09:30", "fired": false}]
```

**`jarvis.log`** — формат `%(asctime)s %(levelname)s %(message)s`; на старті
пишеться рядок `START exe=<шлях> prefix=… base_prefix=… requests=… cwd=…`
(використовується для перевірки свіжості збірки).

### 2.8 UI (`JarvisApp`)

Одне Tk-вікно, темна тема (`BG/PANEL/CYAN/…`):

* **Реактор** — канвас із анімацією (`_animate` кожні 33 мс, `_draw_reactor`);
* **Сайдбар**: «＋ Нова розмова», «▤ Вся історія», «◇ Моя пам'ять»,
  «◷ Нагадування», «⚙ Налаштування», «◉ Голосовий режим»;
* **Сайдбар історії**: останні чати (`RECENT_CHATS_LIMIT = 3`), перемикання
  та видалення, повне вікно історії з пошуком;
* **Чат-лог**: репліки `you/jarvis/sys` з тегами та кольорами, автопрокрутка;
* **Поле вводу** + «Надіслати ↗», Enter — надіслати, Esc/«■ СТОП» — зупинити;
* **Статуси**: провайдер/модель, «СИСТЕМА ГОТОВА», доступ
  («ДОСТУП: ПОВНИЙ / ОБМЕЖЕНИЙ»), кнопки звуку й голосового режиму;
* **Діалоги**: налаштування (ключі, модель, мова, голос, тест з'єднання,
  завантаження безкоштовних моделей з OpenRouter), менеджер пам'яті
  (пошук/додавання/видалення), менеджер нагадувань, модальне підтвердження
  небезпечних дій;
* **Гаряча клавіша**: за `voice_hotkey: true` реєструється глобальний
  `Ctrl+Alt+J` (`RegisterHotKey` через `ctypes`/`user32`) → голосовий режим;
* **Quick actions** (`_quick_action`): «відкрий ютуб/хром/блокнот…»,
  «скинь сервер» — обробляються без звернення до LLM;
* **Буфер обміну**: Ctrl+C/V/X та контекстне меню в текстових полях.

### 2.9 Модель потоків (v1)

```
Tk main thread (root.mainloop)
 ├─ after(20/40)  → _drain_ui: виконує чергу UI-колбеків (`self.ui(...)`)
 ├─ after(33)     → _animate (реактор)
 ├─ after(150/2200/…) → відновлення чату, готовність, привітання
 ├─ after(15000)  → _check_reminders (переплановується)
 └─ after(0)      → показ модальних вікон (підтвердження, діалоги)

Робочі daemon-потоки:
 ├─ _text_cycle      — Brain.ask → лог → TTS
 ├─ _cycle           — Ears.record → transcribe → _answer
 ├─ _greet           — стартове вітання
 ├─ _global_hotkey_loop — RegisterHotKey + GetMessage
 └─ StudioMCP reader-потоки (stdout/stderr)
```

Правило: **будь-який доступ до Tk — лише з main thread**. Робочі потоки
публікують дії через `self.ui(fn, *args)` (черга + `root.after(40)`), а
результати підтверджень синхронізують через `threading.Event`. Файлові
сховища захищені `LOCK`/`RLock`; голос і запис можуть бути перервані
прапорцями (`stop flag` / `threading.Event`).

### 2.10 Пакетування (v1)

* `JARVIS.spec`: `Analysis(['jarvis.py'])` → `EXE(..., a.binaries, a.datas)`
  → **onefile**, `console=False` (GUI), `upx=True`, іконка
  `assets/jarvis.ico`, `datas assets → assets`;
  `collect_all('edge_tts' | 'pygame' | 'speech_recognition')`; решта
  залежностей (`pyttsx3`, `sounddevice`, `comtypes`, `tkinter`) — через
  штатні хуки `PyInstaller`/`pyinstaller-hooks-contrib`.
* Усі шляхи в spec — від `SPECPATH` (тека spec-файлу), тому збірка не
  залежить від робочого каталогу.
* `build_exe.py` керує збіркою: перевірка контракту → PyInstaller
  (`dist/`, `build/` у проєкті) → верифікація PE-підсистеми/розміру/свіжості
  → копіювання exe в корінь проєкту та `OneDrive\Desktop\JARVIS\`.
* Під час роботи onefile-exe `assets/` читаються з тимчасової теки
  розпакування, `%APPDATA%` — недоторканий (конфіг/логи переживають
  перезбірку).

---

## 3. Версія v2 — модульна (`main.py` + пакети)

Каркас «JARVIS ULTIMATE»: багатоагентна архітектура, де `Brain` координує
спеціалізованих агентів, а спільні сервіси винесені в окремі пакети.
Триває наповнення `modules/` (голос, керування ПК) та інтеграція в UI.

### 3.1 Компоненти

```
main.py
 ├─ %APPDATA%\Jarvis\config.json  (спільний з v1)
 ├─ SecurityEngine(confirm_callback=request_approval)
 ├─ ModelRouter(config)
 ├─ SqliteStore()                  → %APPDATA%\Jarvis\jarvis_ultimate.db
 ├─ TaskEngine()
 ├─ AgentManager() ── register CoderAgent / SystemAgent / RobloxAgent
 ├─ Brain(config, security, router, agents, tasks, store)
 └─ Dashboard(root, on_send, on_emergency_stop)
```

* **`core/security_engine.py`** — 3 рівні безпеки:
  `SAFE` (авто), `CONTROLLED` (лог/аудит), `APPROVAL` (явний дозвіл через
  callback); `trigger_emergency_stop()` / `reset_emergency_stop()` — глобальний
  стоп для всіх агентів; журнал аудиту в пам'яті.
* **`core/model_router.py`** — провайдери (`gemini`, `groq`, `xkiro`,
  `openrouter`, `ollama` локально) + `TASK_PROFILES` (`chat`, `coding`,
  `reasoning`, `fast`): для типу задачі — впорядкований список моделей,
  фолбеки й повторні спроби.
* **`core/task_engine.py`** — сутність `Task` (id, title, description, agent,
  статус `pending/in_progress/completed/failed`, результат) і реєстр задач.
* **`core/agent_manager.py`** — реєстрація агентів, `dispatch(name, task)`.
* **`core/brain.py`** — швидкі маршрути (Roblox-скидання, запит коду,
  діагностика системи) → відповідний агент; інакше — чат через `ModelRouter`
  з контекстом останніх повідомлень із `SqliteStore`.
* **`agents/`** — `BaseAgent` (+`AgentResponse`), `CoderAgent`,
  `SystemAgent` (метрики системи), `RobloxAgent` (Roblox Studio/сервер).
* **`ui/dashboard.py`** — `Dashboard`: чат-лог, статуси агентів, метрики,
  кнопка Emergency Stop, callback надсилання.
* **`memory/sqlite_store.py`** — thread-safe SQLite (`RLock`, timeout 15 с):
  таблиці `messages`, `memories`, `tasks`, `audit_logs`; API
  `add_message/get_recent_messages`, `set_memory/get_memory/list_memories/…`.
* **`modules/voice/`** — `tts.py` (edge-tts + pygame, fallback), `stt.py`
  (VAD + SpeechRecognition): перевикористовувані аналоги v1-рушіїв.
* **`modules/computer_control/`** — керування ПК (відкриття сайтів/програм,
  PowerShell із класифікацією safe/destructive, файли, скріншоти,
  клавіатура/миша, вікна) для агентів v2.

### 3.2 Потік обробки повідомлення (цільовий)

```
Dashboard.on_send(text)
   → main.handle_user_message(text)
       → Brain.process(text)
           ├─ emergency stop? → відмова
           ├─ швидкий маршрут (Roblox reset / код / діагностика)
           │     → TaskEngine.create_task → AgentManager.dispatch(agent)
           └─ інакше: SqliteStore.get_recent_messages → ModelRouter.complete
       → SqliteStore.add_message("assistant", reply)
       → Dashboard.post_message(...)
```

У поточному каркасі `main.py` обробка повідомлення виконується синхронно в
Tk-потоці (LLM-виклик блокує UI); фоновим є лише цикл метрик системи
(`poll_metrics`, `root.after` + `sleep`). Під час завершення v2 це місце
ймовірно переїде у робочий потік — як у v1 (`self.ui(...)` + черга).

### 3.3 Модель даних v2

`jarvis_ultimate.db` (SQLite):

| Таблиця | Призначення |
|---|---|
| `messages` | історія повідомлень за `session_id` (role, content, agent_name, timestamp) |
| `memories` | ключ-значення факти (`category`, `key UNIQUE`, `value`, `created_at`, `updated_at`) |
| `tasks` | задачі агентів |
| `audit_logs` | аудит дій (рівень безпеки, агент, деталі) |

`jarvis_ultimate.log` — окремий лог v2 (v1 і v2 не змішують логи).

---

## 4. Спільні контракти

* **Конфіг один**: `%APPDATA%\Jarvis\config.json`; v1 зливає його зі своїм
  `DEFAULT_CONFIG`, v2 має власний `load_config()` з іншими типовими
  значеннями — тому після перемикання версій частина ключів може
  відрізнятися (це відоме місце для уніфікації).
* **Ключі API** — лише локально, у відкритому вигляді; обидві версії
  використовують ті самі назви полів (`*_api_key`, `openrouter_key`).
* **Логи** — окремі, з `START`-рядком у v1.
* **Ассети** — `assets/jarvis.ico`, `assets/jarvis.png`; генеруються
  `make_icon.py`.

---

## 5. Відомі обмеження та ризики

1. **v2 незавершена**: мікрофон/TTS/ПК-дії ще інтегруються; `modules/`
   наповнюються. Для реальної роботи використовуйте v1.
2. **Синхронний LLM-виклик у v2** може «підвішувати» UI на час запиту.
3. **Один екземпляр на APPDATA**: одночасний запуск v1 і v2 ділять
   `config.json` (запис атомарний, але останній перемагає).
4. **Onefile-exe**: старт повільніший (розпакування), антивірус може
   реагувати на непідписаний exe.
5. **Edge-tts потребує інтернету**; без мережі залишається SAPI-fallback
   (менш природний голос).
6. **Google Web Speech** для STT потребує інтернету; офлайн-розпізнавання
   не підтримується.
7. **Історія чатів** зберігається лише в JSON (без шифрування) — особисті
   дані лежать у відкритому вигляді на диску.
8. **Roblox Studio MCP** залежить від наявності/оновлень StudioMCP.exe та
   MCP-плагіна в Roblox Studio; шлях можна перевизначити `ROBLOX_STUDIO_MCP`.
