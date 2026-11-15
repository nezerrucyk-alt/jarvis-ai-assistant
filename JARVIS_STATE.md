# J.A.R.V.I.S. — стан проєкту та точка відновлення

Оновлено: 2026-11-15 (реліз 2.6.0). Поточна гілка: `main`, останній релізний
коміт: тег `v2.6.0`.

Версія в коді: **2.6.0** (`APP_VERSION`, `modules.__version__`).
Публічний реліз: **v2.6.0** (15.11.2026).

## Де що лежить

| Що | Шлях |
|---|---|
| Основний код | `C:\Users\nezer\Jarvis\jarvis.py` |
| Модулі | `C:\Users\nezer\Jarvis\modules\` |
| Віртуальне середовище | `C:\Users\nezer\Jarvis\.venv\` |
| Збірка | `C:\Users\nezer\Jarvis\dist\JARVIS.exe` |
| Робоча копія | `C:\Users\nezer\Jarvis\JARVIS.exe` |
| Конфіг і ключі | `C:\Users\nezer\AppData\Roaming\Jarvis\config.json` |
| Історія чатів | `C:\Users\nezer\AppData\Roaming\Jarvis\chats.json` |
| Пам'ять | `C:\Users\nezer\AppData\Roaming\Jarvis\memory.json` |
| Нагадування | `C:\Users\nezer\AppData\Roaming\Jarvis\reminders.json` |
| Автоматизації | `C:\Users\nezer\AppData\Roaming\Jarvis\automations.json` |
| Історія буфера | `C:\Users\nezer\AppData\Roaming\Jarvis\clipboard.json` |
| Кастомізація | `C:\Users\nezer\AppData\Roaming\Jarvis\customization.json` |
| Плагіни | `C:\Users\nezer\AppData\Roaming\Jarvis\plugins\` |
| Лог | `C:\Users\nezer\AppData\Roaming\Jarvis\jarvis.log` |
| Сайт | `C:\Users\nezer\Jarvis\website\` |
| Marketplace-реєстр | `C:\Users\nezer\Jarvis\assets\marketplace\registry.json` |
| Marketplace-плагіни | `C:\Users\nezer\Jarvis\assets\marketplace\plugins\` |
| GitHub-репозиторій | `nezerrucyk-alt/jarvis-ai-assistant` |
| GitHub Pages | `https://nezerrucyk-alt.github.io/jarvis-ai-assistant/` |
| Останній реліз | `https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/tag/v2.6.0` |
| Лог останньої збірки | `C:\Users\nezer\Jarvis\build_last.log` |
| Журнал змін | `C:\Users\nezer\Jarvis\CHANGES_SUMMARY.md` |
| Стан проєкту | `C:\Users\nezer\Jarvis\JARVIS_STATE.md` (цей файл) |

## Актуальний білд і реліз

Локальна збірка 2.6.0 (15.11.2026):

- `dist\JARVIS.exe` — 165 963 720 байт (158.3 МБ), змінено 15.11.2026 09:56,
  PE-підсистема 2 (GUI), SHA256
  `80eed566ab701eb3084190cc9b774f21936cf280d1d602dabf39ee2e5c8629b2`.
- Локальний розмір більший за релізний, бо у venv стоять `openWakeWord`,
  `onnxruntime`, `scikit-learn` і `scipy`; CI збирає без них.
- Копії збігаються з `dist`: `JARVIS.exe` у корені та
  `website\downloads\JARVIS.exe` (обидві ігноруються git).
- `build_exe.py --skip-desktop-copy --kill-running` пройшов: spec-контракт,
  свіжість, PE-заголовок і GUI-підсистема перевірені.
- Реліз v2.6.0 — у процесі публікації: тег `v2.6.0` запускає
  `.github/workflows/release.yml`, після CI сюди треба вписати розміри й
  SHA256 для Windows/macOS/Linux та `SHA256SUMS.txt`.
- TikTok #5 лежить у `assets/social/tiktok-01-intro-final.mp4`
  (4 597 603 Б, 1080×1920, 25.0 с, H.264 + AAC) і завантажується в реліз
  як `JARVIS-TikTok-05.mp4` разом з обкладинкою.
- Рендери TikTok (`*.mp4`, `*.wav`, `*.png` у `assets/social`) не комітяться:
  у git живе лише `render_tiktok_01.py`, медіа їде в GitHub Release.
- Intel macOS і Android — необов'язкові, не блокують реліз.
- Windows/macOS непідписані; SmartScreen і Gatekeeper попереджають.

`website/index.html` оновлено на 2.6.0 / 15.11.2026: changelog 2.6.0, кнопки
ведуть на v2.6.0, п'яте TikTok-відео, секція відео з MP4 та посилання на
GitHub автора (`@nezerrucyk-alt`). Хеші й розміри в блоці перевірки
замінюються після публікації CI-релізу. JS і далі підтягує останній
non-prerelease реліз і віддає перевагу setup-ассету.

## Що нового у 2.6.0 (15.11.2026)

- Генерація зображень у чаті: `core/image_gen.py` + інструмент `generate_image`
  (OpenAI Images `gpt-image-1` / `gpt-image-1-mini`). Підтримка `b64_json` і URL,
  перевірка байтів через Pillow, атомарний запис у `%APPDATA%\Jarvis\images`.
- Налаштування `image_model`, `image_size`, `image_quality` у вікні налаштувань;
  інструмент доданий у `RESTRICTED_TOOL_NAMES`.
- `_answer` забирає згенеровані картинки з черги `take_generated_images()` і
  показує їх у чаті через `_log(image=...)`; історія зберігає шлях.
- `SYSTEM_PROMPT` навчає модель переписувати короткі запити в детальні промпти.
- Тести: **256 OK**, новий `tests/test_46_image_gen.py` (9 тестів).
- TikTok #5: `assets/social/tiktok-01-intro-final.mp4` — 1080×1920, 25.0 с,
  H.264 + AAC, процедурна музика; cover і endcard поруч.
- Сайт: changelog 2.6.0, docs-секція «Генерація зображень», roadmap 2.6.0,
  п'яте TikTok-відео, кнопки завантаження v2.6.0.

## Що нового у 2.3.0 (випущено 14.11.2026)

- Провайдери: свій OpenAI-сумісний endpoint (`custom_provider_name`,
  `custom_api_url`, `custom_api_key`, `custom_model`, `custom_vision`) і модель
  `custom/<model>`; у вікні налаштувань v2 тепер усі 16 ключів + «Вставити».
- Буфер обміну: локальна історія (до 120 записів, дедуп), вікно з пошуком,
  копіюванням, «Пояснити»/«Перекласти»; інструменти `clipboard_history`,
  `clipboard_copy`.
- Порядок файлів: сортування «Завантажень» за категоріями з dry-run і
  безпечним перейменуванням; вікно попереднього перегляду; інструмент
  `organize_downloads`.
- Проактивність: брифінг (погода Open-Meteo, курс НБУ, нагадування, активні
  автоматизації), дія автоматизації `briefing`, щоденний брифінг о 09:00;
  інструмент `daily_briefing`; стеження за «Завантаженнями».
- HUD: прозорий орб станів (idle/listening/thinking/speaking), перетягування,
  подвійний клік повертає вікно; вмикається в налаштуваннях.
- Telegram: long-polling бот, дозволений лише один chat id; команди `/status`,
  `/briefing`, `/ask`; інструменти ПК через Telegram вимкнені.
- Нові модулі: `core/clipboard_history.py`, `core/file_organizer.py`,
  `core/proactive.py`, `core/telegram_bot.py`, `ui/hud.py`.
- Тести: 242 OK (було 197), нові файли test_37–test_44.
- Білд: `dist\JARVIS.exe` — 151 008 930 байт, SHA256
  `F96A10CB2E2967CAAC3AAC545D165ED644747AAF5CE851D40DA641C40B42F545`
  (14.11.2026); скопійовано в `JARVIS.exe`.

## Соцмережі

- Перше вертикальне TikTok-відео: `build\tiktok_unsloop\jarvis_tiktok_01.mp4`
  (1080×1920, 30 fps, 30.9 с, H.264 + AAC, озвучка edge-tts
  `uk-UA-OstapNeural`). Кадри — реальні скріншоти live-сайту і застосунку.
- Пайплайн: `build\tiktok_unsloop\capture_site.py` (Playwright, вертикальні
  кадри), `render.py` (PIL-кадри + ffmpeg з `imageio_ffmpeg`), `post.txt`,
  `cover.png`. Копії готового відео: `C:\Users\nezer\Downloads\JARVIS_TikTok_01*`.
- Концепція — анти-слоп у дусі референсу Unslop: без стокових 3D і градієнтів
  в оздобленні, великі підписи, чесні факти. Музику додавати в самому TikTok.
- Четверте відео (інструкція): `build	iktok_04\jarvis_tiktok_04.mp4` —
  24.6 с, сайт → реліз → інсталятор → застосунок; ассети
  `JARVIS-TikTok-04.mp4` і cover у релізі v2.4.1.
- Третє відео (2.4.0): `build	iktok_24\jarvis_tiktok_03.mp4` — 26.4 с,
  реальні кадри сайту німецькою/польською та застосунку з локалізованим
  меню; ассети `JARVIS-TikTok-03.mp4` і cover у релізі v2.4.0.
- Друге відео (2.3.0): `build\tiktok_23\jarvis_tiktok_02.mp4` — 1080×1920,
  31.2 с, сцени: 2.3.0, буфер обміну, брифінг, HUD, Telegram, CTA. Реальні
  вікна зняті `capture_features.py` (PrintWindow, демо-дані, без ключів),
  Telegram-чат — макет, бо бот ще не налаштований. Пост — `post.txt`.

## Що зроблено у 2.2.0 (Batch 1 + Batch 2)

### Сайт, SEO, інфраструктура (Batch 1, коміт `8259a81`)

- Преміум-редизайн: aurora-фон, скляна навігація, hero з orbit-кільцями,
  Command Deck, scroll-reveal, spotlight-картки, лічильники, TikTok.
- 3D-анімація логотипа JARVIS: повноекранний skippable-overlay, один раз за
  сесію на початку сторінки, повтор по кліку на логотип, поважає
  `prefers-reduced-motion`. Майстер: `assets/logo/`, веб-копії: `website/assets/`.
- Реальні відгуки через публічні GitHub issues з маркером
  `<!-- jarvis-review -->`: нік, оцінка 1–5, текст до 5000 символів, середній
  рейтинг, кеш 10 хвилин.
- Окрема сторінка `website/docs.html`: Plugin API, Android bridge, провайдери,
  Roblox MCP, Customize, безпека, troubleshooting; пошук «/» і scrollspy.
- Секція перевірки збірок: `SHA256SUMS.txt`, команди `Get-FileHash` /
  `shasum` / `sha256sum`, `gh attestation verify`, чесна примітка про
  відсутність комерційного підпису. `docs/CODE_SIGNING.md` виправлено:
  заявка SignPath **ще не подана**.
- `website/roadmap.html`: випущене / у роботі / заплановано / заблоковане.
- `sitemap.xml`, `robots.txt`, canonical, OG/Twitter-обкладинка, FAQ JSON-LD.
- CI: `tests.yml` (Windows обов'язковий, macOS/Linux advisory), `pip-audit`,
  `review-triage.yml`, Dependabot, `SECURITY.md`.
- `release.yml`: `SHA256SUMS.txt`, `actions/attest-build-provenance@v4`,
  Intel macOS (`macos-15-intel`), Android experimental з `continue-on-error`.
- Автооновлення приймає і `JARVIS-Windows.exe`, і `JARVIS.exe`.

### Голос і офлайн (Batch 2)

- Wake word «Hey Jarvis»: `modules/voice/wake.py`.
  - Основний бекенд — openWakeWord (офлайн), модель `hey_jarvis_v0.1.onnx`
    завантажується в `DATA_DIR/wakeword`.
  - Без openWakeWord — резервний VAD + Google STT (потрібен інтернет).
  - `WakeGate`: нормалізація тексту, фрази, cooldown, пауза під час відповіді.
  - Після відповіді — до 3 реплік продовження без натискання кнопки.
  - Налаштування: `wake_word`, `wake_word_continuous`, `wake_word_model`,
    `wake_word_threshold`, `wake_word_cooldown`.
  - `requirements-wake.txt` — опційний extra; у основний `requirements.txt`
    openWakeWord не входить, тому зібраний exe використовує STT fallback.
- Офлайн-режим: `modules/voice/offline.py`.
  - whisper.cpp (`whisper-cli`) для STT, Piper для TTS; шляхи задаються
    вручну, нічого не завантажується автоматично.
  - `stt_backend` / `tts_backend`: `auto`, `google`/`offline`.
  - В офлайн-режимі хмарні STT/TTS не використовуються.
  - Brain у `offline_mode` ходить лише до Ollama; будь-яка назва
    `ollama/<model>` приймається, URL — `offline_ollama_url`.
  - Vision-моделі Ollama визначаються евристично за назвою
    (`llava`, `moondream`, `gemma3`, `qwen2-vl` тощо).
  - Якщо Ollama/модель недоступні — зрозуміла помилка, без тихого fallback
    у хмару.

### Пам'ять, автоматизації, marketplace (Batch 2)

- `core/memory_index.py`: локальні детерміновані хеш-embeddings `hash-v1`
  (384 виміри, BLAKE2b, слова + біграми + триграми). Косинусна схожість,
  топ-8 релевантних записів у промпті замість останніх 30. Без мережі й
  без завантаження нейромережі. Старі записи отримують embedding автоматично.
  У менеджері пам'яті є семантичний пошук.
- `core/automations.py`: розклади `once YYYY-MM-DDTHH:MM`, `daily 09:00`,
  `weekly mon 09:00`, `every 30m`; дії `prompt` і `notify`; ліміт 100 задач,
  текст до 500 символів, інтервал 5 хв – 7 днів. Планувальник — у процесі
  Jarvis кожні 20 с, без фонового демона. Інструменти:
  `automation_create`, `automation_list`, `automation_cancel`.
  Вікно менеджера — бічна панель «Автоматизації».
- `core/marketplace.py`: локальний JSON-реєстр, перевірка id/назви/файлу/
  SHA256, ліміт 512 КБ, захист від path traversal, атомарне копіювання,
  явне підтвердження. Вікно «Плагіни»: встановити / видалити / свій `.py` /
  папка / перезавантажити. Сервера й авто-встановлення немає.
- `assets/marketplace/registry.json` + 3 приклади: `hello_market.py`,
  `quick_note.py`, `word_stats.py`. Хеші збігаються.
- `.gitattributes`: `assets/marketplace/plugins/*.py -text`, щоб Windows
  checkout не змінював байти й SHA256 не ламався.

### Налаштування, UI, документація

- Вкладка «Кастомізація»: теми, пресети, порядок/видимість блоків, шрифти,
  анімації, живе прев'ю, редактор кастомного коду з прев'ю. Зберігається в
  `customization.json`, застосовується без перезапуску. `SYSTEM_PROMPT`
  знає про цю вкладку й не має казати, що її не існує.
- Нові пункти бічної панелі: «Автоматизації», «Плагіни»; додано в
  `core/customization.py`.
- Налаштування: чекбокс офлайн-режиму, поле моделі, URL Ollama, вибір
  STT/TTS-бекенду, шляхи до whisper.cpp/Piper і моделей, кнопка «Перевірити».
- `SYSTEM_PROMPT` оновлено: пам'ять із embeddings, автоматизації,
  marketplace, офлайн-режим, нові інструменти.
- Сайт: 4 нові картки можливостей, 5 нових пунктів changelog 2.2.0,
  FAQ + FAQ JSON-LD, docs-секції `#offline`, `#automations`, `#marketplace`,
  roadmap Batch 2 у «у роботі».

## Тести та перевірки

- Повний прогін: `.\.venv\Scripts\python.exe -m unittest discover -s tests`
  → **242 тести OK** (2026-11-14).
- Нові тести:
  - `tests/test_31_wake_word.py` — 15 тестів.
  - `tests/test_32_memory_index.py` — 12 тестів.
  - `tests/test_33_automations.py` — 17 тестів.
  - `tests/test_34_marketplace.py` — 9 тестів.
  - `tests/test_35_offline_voice.py` — 8 тестів.
  - `tests/test_36_offline_routing.py` — 6 тестів.
- `tests/test_10_jarvis_app.py`: headless-перевірка, що діалог налаштувань
  містить офлайн-контроли.
- Website audit: `.\.venv\Scripts\python.exe build\check_website.py`
  → 1440 і 390 px, 0 JS/console errors, 0 горизонтального overflow,
  docs search працює. Звіт: `build/webcheck/report.json`.
- HTML/JSON-LD: без дублів `id`, валідний JSON-LD на index/docs/roadmap.
- `node --check website/assets/app.js` — OK; YAML workflows — OK.
- Live-сайт після деплою `fe9e7f4`: версія 2.2.0, дата 14.11.2026,
  посилання `v2.2.0`, нові SHA256, roadmap із «2.2.0 · випущено»;
  плейсхолдери `__GITHUB_REPOSITORY__` / `__SITE_URL__` замінені.

## Стан CI

- `Cross-platform release` для `c7f04bb` (тег `v2.2.0`): job
  `Publish GitHub release` — **success**, Windows/macOS/Linux зібрано,
  `SHA256SUMS.txt` і GitHub build provenance/атестації створені. Сам run
  пізніше скасовано, бо необов'язковий Intel-джоб завис на `macos-13`.
- Перший прогін `c313b52` опублікував реліз, але впав на атестації:
  бракувало дозволу `attestations: write`. Виправлено в `c7f04bb`.
- `release.yml` більше не чекає на Android/Intel: `publish` має
  `needs: [desktop]`, тому необов'язкові job не блокують реліз.
  Intel-джоб переведено на підтримуваний `macos-15-intel`.
- `Tests` для `c9828b9`: Windows — success, Website syntax — success,
  Dependency audit — success; Ubuntu — advisory failure, macOS — у процесі.
- Dependabot: усі 10 PR розібрано. Злито pillow 13, sounddevice 0.5.6,
  requests 2.34.2, pyttsx3 2.99 і п'ять GitHub Actions bump-ів
  (attest v4, setup-node v7, github-script v9, configure-pages v6,
  upload-pages-artifact v5). PR із numpy 2.5.4 закрито: він вимагає
  Python >=3.12, а матриця збірок на Python 3.11.

## Що ще зробити

1. ~~Зібрати й опублікувати v2.2.0~~ — зроблено 14.11.2026.
2. ~~Оновити статичні версії/дати/хеші/посилання на сайті~~ — зроблено.
3. ~~Додати `attestations: write` і прибрати блокування релізу Android/Intel~~
   — зроблено в `c7f04bb`.
4. ~~Перевірити live-сайт після деплою~~ — версія, дата, посилання, хеші
   й roadmap перевірені 14.11.2026.
5. Живий тест мікрофона: «Hey Jarvis», поріг `wake_word_threshold`,
   cooldown, 3 репліки продовження. Без openWakeWord — перевірити STT fallback.
6. Перевірити офлайн-режим на реальній Ollama; за бажанням підключити
   whisper.cpp/Piper і протестувати голос без інтернету.
7. Перевірити marketplace: встановлення/видалення прикладів, SHA256 mismatch,
   локальний `.py`.
8. Перевірити автоматизації: once/daily/weekly/every, prompt/notify,
   перезапуск Jarvis, пропущені слоти.
9. ~~Розібрати Dependabot PR~~ — 7 злито, 3 закрито; numpy 2.5.x відкладено
   до переходу збірок на Python 3.12.
10. Home Assistant URL/токен — досі не налаштовано.
11. Відкликати/перегенерувати ключ Ashna, який був показаний у чаті.
12. Android APK CI — експериментальний, зеленої збірки немає.
13. Intel macOS — артефакт ще не опублікований (окремий необов'язковий job).
14. Комерційний підпис — немає; заявка SignPath не подана.

## Важливі нюанси

- PowerShell у консолі плутає кирилицю; логи/JSON читати Python-ом з
  `encoding="utf-8"`, файли писати через write-tool або UTF-8 Python.
- Перед заміною exe зупиняти всі `JARVIS.exe` (onefile = батько + дитина).
- Плагіни не вбудовані в exe: читаються з `%APPDATA%\Jarvis\plugins` під час
  старту або після `plugin_reload`.
- Marketplace-хеші чутливі до байтів: не редагувати файли плагінів без
  перегенерації `registry.json`; `.gitattributes` зберігає LF.
- `render_custom_code` обмежений, але це не повноцінна пісочниця.
- Автоматизації працюють лише коли Jarvis відкритий; фонового сервісу немає.
- Офлайн-режим не завантажує whisper.cpp/Piper; без них — лише текст.
- openWakeWord не входить у основний `requirements.txt`; для офлайн wake word
  треба `pip install -r requirements-wake.txt`.
- GitHub Pages підставляє `__GITHUB_REPOSITORY__` / `__SITE_URL__` у
  HTML/XML/TXT через `pages.yml`; локально JS має fallback.
- `website/downloads/JARVIS.exe` ігнорується git.
- macOS/Linux: чат, голос, плагіни, vision, переклад, Home Assistant;
  повне керування ПК, глобальні гарячі клавіші, ґеймерський оверлей і
  Roblox Studio — лише Windows.
- `release.yml`: `publish` має `needs: [desktop]` і умову
  `if: always() && needs.desktop.result == 'success'`; Android та Intel macOS
  не блокують реліз. Intel-джоб тепер на `macos-15-intel` (старий `macos-13`
  більше не доступний). Для атестацій потрібен дозвіл `attestations: write`.
- Windows-ассет релізу називається `JARVIS-Windows.exe`; автооновлення
  приймає і його, і `JARVIS.exe` (другий має пріоритет).
- `requirements.txt`: `pycaw`/`comtypes` лише для Windows.
- Відгуки: унікальна марка `<!-- jarvis-review -->`, GitHub Issues API без
  токена (60 запитів/год), кеш 10 хв.

## Команда збірки Windows

```powershell
cd C:\Users\nezer\Jarvis
& ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name JARVIS --icon "assets\jarvis.ico" --add-data "assets;assets" --collect-all edge_tts --collect-all pygame --collect-all speech_recognition --collect-all pyttsx3 --collect-all cryptography --collect-all psutil --collect-all pycaw --collect-all comtypes --collect-all pystray --hidden-import PIL.Image --hidden-import pystray._win32 --hidden-import modules.mobile_bridge --hidden-import modules.coding_workspace --hidden-import modules.voice.offline --hidden-import core.automations --hidden-import core.marketplace --hidden-import core.memory_index jarvis.py
```

Після збірки: закрити всі `JARVIS.exe`, скопіювати `dist\JARVIS.exe` у
`JARVIS.exe` і `website\downloads\JARVIS.exe`, запустити й перевірити хвіст
`jarvis.log`, оновити розмір/SHA256/дату на сайті.

Інсталятор Windows (Inno Setup 6):

```powershell
cd C:\Users\nezer\Jarvis
New-Item -ItemType Directory -Force installer\payload | Out-Null
Copy-Item dist\JARVIS.exe installer\payload\JARVIS-Windows.exe
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer\JARVIS.iss
```

Результат — `dist\JARVIS-Setup.exe`; ассет заливається в реліз через GitHub API,
`installer/payload/` у git ігнорується. Інсталятор не має build provenance —
його перевіряють лише за SHA256.
