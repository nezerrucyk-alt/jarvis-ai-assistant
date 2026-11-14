# J.A.R.V.I.S. — стан проєкту та точка відновлення

Оновлено: 2026-11-14. Поточна гілка: `main`, останній відомий коміт: `3258ae8`
(Batch 2: offline mode, memory embeddings, automations and marketplace).

Версія в коді: **2.2.0** (`APP_VERSION`, `modules.__version__`).
Публічний реліз: **v2.1.0** — v2.2.0 ще не зібраний і не опублікований.

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
| Кастомізація | `C:\Users\nezer\AppData\Roaming\Jarvis\customization.json` |
| Плагіни | `C:\Users\nezer\AppData\Roaming\Jarvis\plugins\` |
| Лог | `C:\Users\nezer\AppData\Roaming\Jarvis\jarvis.log` |
| Сайт | `C:\Users\nezer\Jarvis\website\` |
| Marketplace-реєстр | `C:\Users\nezer\Jarvis\assets\marketplace\registry.json` |
| Marketplace-плагіни | `C:\Users\nezer\Jarvis\assets\marketplace\plugins\` |
| GitHub-репозиторій | `nezerrucyk-alt/jarvis-ai-assistant` |
| GitHub Pages | `https://nezerrucyk-alt.github.io/jarvis-ai-assistant/` |
| Останній реліз | `https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/tag/v2.1.0` |
| Лог останньої збірки | `C:\Users\nezer\Jarvis\build_last.log` |
| Журнал змін | `C:\Users\nezer\Jarvis\CHANGES_SUMMARY.md` |
| Стан проєкту | `C:\Users\nezer\Jarvis\JARVIS_STATE.md` (цей файл) |

## Актуальний білд і реліз

Опублікований v2.1.0 (станом на 2026-11-14):

- Windows `JARVIS.exe` — 89 567 989 байт,
  SHA256 `6D31F77B8EE221062CE728D6747A1C2E6213DBEEC40FE7532A86EAF40431A3EC`.
- macOS `JARVIS-macOS.zip` — 75 728 703 байти,
  SHA256 `E8652BFD32E9338D316ACBE2E27B8329E3AC9804B539FF369105B4A0D5D19ABE`.
- Linux `JARVIS-Linux.tar.gz` — 105 274 532 байти,
  SHA256 `928B932B8DBB9FD75CCA790DE063D36566A05938D4FA517EB48EE828553337F0`.
- macOS: Apple Silicon; Intel-збірка додана в матрицю, але артефакту ще немає.
- Windows/macOS непідписані; SmartScreen і Gatekeeper попереджають.

`website/index.html` має статичні fallback-значення 2.1.0 / 11.11.2026.
JS підтягує останній non-prerelease реліз GitHub; після публікації v2.2.0
сторінка автоматично покаже 2.2.0, але статичні хеші треба оновити вручну.

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
- `release.yml`: `SHA256SUMS.txt`, `actions/attest-build-provenance@v2`,
  Intel macOS (`macos-13`), Android experimental з `continue-on-error`.
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
  → **197 тестів OK** (2026-11-14).
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
- Live-сайт після деплою `3258ae8`: картки офлайн/пам'ять/автоматизації/
  marketplace, FAQ і docs-секції присутні.

## Стан CI

- `Publish download site` для `3258ae8` — success, сайт задеплоєно.
- `Tests` для `3258ae8` був у черзі й скасований (не через падіння тестів;
  перед ним у черзі було 10 Dependabot-прогонів). Потрібен повторний прогін
  після наступного коміту.
- `058b54a`: Pages — success, Tests — cancelled (те саме).
- Dependabot відкрив 10 PR: pillow, sounddevice, numpy, requests, pyttsx3,
  actions/attest-build-provenance, configure-pages, setup-node,
  github-script, upload-pages-artifact. Їх треба перевірити окремо.

## Що ще зробити

1. Дочекатися зеленого `Tests` на Windows для останнього коміту.
2. Зібрати v2.2.0 Windows `.exe`, перевірити запуск і оновити:
   `APP_VERSION` уже 2.2.0; розмір/SHA256/дату в трьох картках сайту;
   статичні fallback-версії; JSON-LD `softwareVersion`.
3. Запустити `release.yml` (тег `v2.2.0`), дочекатися Windows/macOS/Linux
   артефактів, `SHA256SUMS.txt` і GitHub attestations.
4. Перевірити live-сайт після релізу: версія, дата, посилання, хеші.
5. Живий тест мікрофона: «Hey Jarvis», поріг `wake_word_threshold`,
   cooldown, 3 репліки продовження. Без openWakeWord — перевірити STT fallback.
6. Перевірити офлайн-режим на реальній Ollama; за бажанням підключити
   whisper.cpp/Piper і протестувати голос без інтернету.
7. Перевірити marketplace: встановлення/видалення прикладів, SHA256 mismatch,
   локальний `.py`.
8. Перевірити автоматизації: once/daily/weekly/every, prompt/notify,
   перезапуск Jarvis, пропущені слоти.
9. Розібрати Dependabot PR і оновити залежності, якщо CI зелений.
10. Home Assistant URL/токен — досі не налаштовано.
11. Відкликати/перегенерувати ключ Ashna, який був показаний у чаті.
12. Android APK CI — експериментальний, зеленої збірки немає.
13. Intel macOS — артефакт ще не опублікований.
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
- `release.yml`: Android не блокує публікацію desktop-ассетів завдяки
  `if: always() && needs.desktop.result == 'success'`.
- `requirements.txt`: `pycaw`/`comtypes` лише для Windows.
- Відгуки: унікальна марка `<!-- jarvis-review -->`, GitHub Issues API без
  токена (60 запитів/год), кеш 10 хв.

## Команда збірки Windows

```powershell
cd C:\Users\nezer\Jarvis
& ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name JARVIS --icon "assets\jarvis.ico" --add-data "assets;assets" --collect-all edge_tts --collect-all pygame --collect-all speech_recognition --collect-all cryptography --collect-all psutil --collect-all pycaw --collect-all comtypes --collect-all pystray --hidden-import PIL.Image --hidden-import pystray._win32 --hidden-import modules.mobile_bridge --hidden-import modules.coding_workspace jarvis.py
```

Після збірки: закрити всі `JARVIS.exe`, скопіювати `dist\JARVIS.exe` у
`JARVIS.exe` і `website\downloads\JARVIS.exe`, запустити й перевірити хвіст
`jarvis.log`, оновити розмір/SHA256/дату на сайті.
