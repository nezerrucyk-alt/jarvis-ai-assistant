# J.A.R.V.I.S. — що змінилося (версія 2.0.0)

Оновлено: 10.11.2026

## Головне в цьому білді

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

### Сайт
- Повністю переписаний `website/index.html` + `assets/styles.css` + `assets/app.js`.
- Розділи: hero, статистика, можливості, провайдери, скріншоти, демо-відео, плагіни, changelog, встановлення, відгуки, завантаження/Pro, FAQ, footer, JSON-LD.
- Перемикач UA/EN, мобільне меню, lightbox для скріншотів, копіювання SHA256.
- Лічильник завантажень через GitHub Releases API; локальний fallback — `downloads/JARVIS.exe`.
- Демо-ролик 30 с, 1280×720, H.264: `website/assets/demo.mp4`, постер `demo-poster.jpg`.
- Свіжі скріншоти головного вікна (1180×820) і налаштувань (700×980) з актуального білда.

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
3. За бажанням: автооновлення exe, більше мов, Pro-сторінка.

## Публікація
- Сайт: https://nezerrucyk-alt.github.io/jarvis-ai-assistant/
- Реліз: https://github.com/nezerrucyk-alt/jarvis-ai-assistant/releases/tag/v2.0.0
- Ассет: `JARVIS.exe` (89 393 601 байт), прикріплений до релізу v2.0.0.
