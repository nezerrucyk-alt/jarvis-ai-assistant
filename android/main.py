from __future__ import annotations

import hashlib
import hmac
import http.client
import json
import ssl
import threading
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.storage.jsonstore import JsonStore
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.utils import escape_markup

PROVIDERS = {
    "OpenRouter": ("https://openrouter.ai/api/v1/chat/completions", "openrouter/free"),
    "Google Gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "gemini-3.5-flash-lite"),
    "Groq": ("https://api.groq.com/openai/v1/chat/completions", "openai/gpt-oss-20b"),
    "DeepSeek": ("https://api.deepseek.com/v1/chat/completions", "deepseek-chat"),
    "Cerebras": ("https://api.cerebras.ai/v1/chat/completions", "llama-3.3-70b"),
    "Mistral": ("https://api.mistral.ai/v1/chat/completions", "mistral-small-latest"),
    "Together": ("https://api.together.xyz/v1/chat/completions", "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"),
}


class JarvisMobile(App):
    title = "J.A.R.V.I.S."

    def build(self):
        self.store = JsonStore(self.user_data_dir + "/settings.json")
        self.history = []
        if self.store.exists("chat"):
            try:
                self.history = self.store.get("chat").get("messages", [])[-60:]
            except Exception:
                self.history = []
        self.busy = False

        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        root.canvas.before.clear()
        self.mode = Spinner(text="Чат", values=("Чат", "Кодер"), size_hint_y=None, height=dp(44))
        self.mode.background_color = (0.08, 0.11, 0.17, 1)
        self.mode.color = (0.45, 0.87, 1, 1)
        root.add_widget(self.mode)

        self.route = Spinner(
            text="На телефоні · API-ключ",
            values=("На телефоні · API-ключ", "Через Jarvis на ПК"),
            size_hint_y=None, height=dp(44),
        )
        self.route.background_color = (0.08, 0.11, 0.17, 1)
        self.route.color = (0.45, 0.87, 1, 1)
        root.add_widget(self.route)

        self.chat_view = ScrollView(do_scroll_x=False)
        self.chat_label = Label(
            text="", markup=True, size_hint_y=None, halign="left", valign="top",
            color=(0.90, 0.93, 0.97, 1), padding=(dp(6), dp(8)),
        )
        self.chat_label.bind(
            width=lambda *_: self.chat_label.setter("text_size")(self.chat_label, (self.chat_label.width, None)),
            texture_size=lambda *_: setattr(self.chat_label, "height", self.chat_label.texture_size[1] + dp(20)),
        )
        self.chat_view.add_widget(self.chat_label)
        root.add_widget(self.chat_view)

        self.settings_button = Button(
            text="Налаштування", size_hint_y=None, height=dp(42),
            background_normal="", background_color=(0.10, 0.13, 0.20, 1),
        )
        self.settings_button.bind(on_release=self.toggle_settings)
        root.add_widget(self.settings_button)

        self.settings_panel = BoxLayout(
            orientation="vertical", spacing=dp(6), size_hint_y=None,
            height=0, opacity=0,
        )
        self.settings_panel.add_widget(Label(
            text="Для API-ключа використовується приватне сховище застосунку.",
            size_hint_y=None, height=dp(28), font_size=dp(12),
        ))
        self.provider = Spinner(
            text=self.store.get("settings").get("provider", "OpenRouter") if self.store.exists("settings") else "OpenRouter",
            values=tuple(PROVIDERS.keys()), size_hint_y=None, height=dp(40),
        )
        self.provider.bind(text=self.provider_changed)
        self.settings_panel.add_widget(self.provider)

        settings = self.store.get("settings") if self.store.exists("settings") else {}
        provider_default = PROVIDERS.get(self.provider.text, PROVIDERS["OpenRouter"])[1]
        self._previous_default = provider_default
        self.model = TextInput(
            text=settings.get("model", provider_default),
            hint_text="Модель (наприклад openrouter/free)",
            multiline=False, size_hint_y=None, height=dp(42),
        )
        self.settings_panel.add_widget(self.model)
        self.api_key = TextInput(
            text=settings.get("api_key", ""), hint_text="API-ключ провайдера",
            password=True, multiline=False, size_hint_y=None, height=dp(42),
        )
        self.settings_panel.add_widget(self.api_key)
        self.settings_panel.add_widget(Label(
            text="Комп’ютер: URL https://IP:8765, токен і SHA-256 від Jarvis на ПК.",
            size_hint_y=None, height=dp(34), font_size=dp(11),
        ))
        self.server_url = TextInput(
            text=settings.get("server_url", ""), hint_text="URL комп’ютера, наприклад https://192.168.1.10:8765",
            multiline=False, size_hint_y=None, height=dp(42),
        )
        self.settings_panel.add_widget(self.server_url)
        self.server_token = TextInput(
            text=settings.get("server_token", ""), hint_text="Токен підключення",
            password=True, multiline=False, size_hint_y=None, height=dp(42),
        )
        self.settings_panel.add_widget(self.server_token)
        self.server_fingerprint = TextInput(
            text=settings.get("server_fingerprint", ""), hint_text="SHA-256 сертифіката",
            multiline=False, size_hint_y=None, height=dp(42),
        )
        self.settings_panel.add_widget(self.server_fingerprint)
        clear_key = Button(
            text="Видалити API-ключ із телефона", size_hint_y=None, height=dp(38),
            background_normal="", background_color=(0.32, 0.13, 0.16, 1),
        )
        clear_key.bind(on_release=self.clear_key)
        self.settings_panel.add_widget(clear_key)
        root.add_widget(self.settings_panel)

        send_row = BoxLayout(size_hint_y=None, height=dp(92), spacing=dp(8))
        self.prompt = TextInput(
            hint_text="Напиши Jarvis…", multiline=True, size_hint_x=0.78,
            padding=(dp(10), dp(10)),
        )
        self.prompt.bind(on_text_validate=self.send_message)
        send_row.add_widget(self.prompt)
        self.send_button = Button(
            text="Надіслати", size_hint_x=0.22,
            background_normal="", background_color=(0.10, 0.42, 0.65, 1),
        )
        self.send_button.bind(on_release=self.send_message)
        send_row.add_widget(self.send_button)
        root.add_widget(send_row)

        self.status = Label(text="Готовий", size_hint_y=None, height=dp(24), font_size=dp(12))
        root.add_widget(self.status)
        self.refresh_chat()
        return root

    def provider_changed(self, _spinner, name):
        endpoint, model = PROVIDERS.get(name, PROVIDERS["OpenRouter"])
        self.endpoint = endpoint
        if hasattr(self, "model") and (not self.model.text or self.model.text == self._previous_default):
            self.model.text = model
        self._previous_default = model

    def toggle_settings(self, *_):
        shown = self.settings_panel.height > 0
        if shown:
            self.settings_panel.height = 0
            self.settings_panel.opacity = 0
            self.settings_button.text = "Налаштування"
        else:
            self.settings_panel.height = dp(420)
            self.settings_panel.opacity = 1
            self.settings_button.text = "Сховати налаштування"
        self.save_settings()

    def save_settings(self):
        endpoint = PROVIDERS.get(self.provider.text, PROVIDERS["OpenRouter"])[0]
        self.store.put("settings", provider=self.provider.text, endpoint=endpoint,
                       model=self.model.text.strip(), api_key=self.api_key.text,
                       server_url=self.server_url.text.strip(),
                       server_token=self.server_token.text.strip(),
                       server_fingerprint=self.server_fingerprint.text.strip().replace(":", "").upper())

    def clear_key(self, *_):
        self.api_key.text = ""
        self.save_settings()
        self.status.text = "API-ключ видалено"

    def refresh_chat(self):
        rows = []
        for item in self.history[-60:]:
            role = "Ти" if item.get("role") == "user" else "JARVIS"
            color = "78D7FF" if role == "JARVIS" else "AEB8C8"
            rows.append(f"[b][color={color}]{role}[/color][/b]\n{escape_markup(str(item.get('content', '')))}")
        self.chat_label.text = "\n\n".join(rows)
        Clock.schedule_once(lambda *_: setattr(self.chat_view, "scroll_y", 0), 0.1)

    def send_message(self, *_):
        text = self.prompt.text.strip()
        if not text or self.busy:
            return
        self.prompt.text = ""
        self.history.append({"role": "user", "content": text})
        self.refresh_chat()
        self.busy = True
        self.send_button.disabled = True
        self.status.text = "Jarvis думає…"
        self.save_settings()
        threading.Thread(target=self._request, args=(text,), daemon=True).start()

    def _request(self, text):
        try:
            if self.route.text == "Через Jarvis на ПК":
                reply = self._ask_desktop(text)
            else:
                reply = self._ask_provider(text)
            error = None
        except Exception as exc:
            reply = ""
            error = str(exc)
        Clock.schedule_once(lambda _dt: self._finish(reply, error), 0)

    def _ask_provider(self, text):
        settings = self.store.get("settings") if self.store.exists("settings") else {}
        endpoint = settings.get("endpoint", PROVIDERS["OpenRouter"][0])
        model = settings.get("model", PROVIDERS["OpenRouter"][1])
        api_key = settings.get("api_key", "")
        if not api_key:
            raise RuntimeError("Додай API-ключ у налаштуваннях.")
        mode = "coder" if self.mode.text == "Кодер" else "chat"
        system = (
            "Ти JARVIS, мобільний помічник. Відповідай українською, коротко й корисно."
            if mode == "chat" else
            "Ти JARVIS у режимі досвідченого програміста. Пояснюй рішення, показуй готовий код, враховуй помилки й безпеку. Відповідай українською."
        )
        messages = [{"role": "system", "content": system}]
        messages.extend(self.history[-30:])
        payload = json.dumps({
            "model": model, "messages": messages, "temperature": 0.5,
            "max_tokens": 1800 if mode == "coder" else 1000,
        }).encode("utf-8")
        req = urllib.request.Request(endpoint, data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
            "HTTP-Referer": "https://localhost/jarvis-mobile",
            "X-Title": "JARVIS Android",
        }, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                data = json.loads(response.read(2_000_000).decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read(1200).decode("utf-8", "replace")
            raise RuntimeError(f"API повернув HTTP {exc.code}: {detail}") from exc
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("Провайдер повернув порожню відповідь.")
        return str((choices[0].get("message") or {}).get("content", "")).strip()

    def _ask_desktop(self, text):
        settings = self.store.get("settings") if self.store.exists("settings") else {}
        raw_url = settings.get("server_url", "").strip()
        token = settings.get("server_token", "").strip()
        expected = settings.get("server_fingerprint", "").replace(":", "").upper()
        parsed = urlsplit(raw_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise RuntimeError("Вкажи HTTPS-адресу з Jarvis на ПК.")
        if not token or len(expected) != 64:
            raise RuntimeError("Додай токен і 64-символьний SHA-256 сертифіката.")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise RuntimeError("Адреса має містити лише HTTPS-хост і порт.")
        port = parsed.port or 443
        path = (parsed.path.rstrip("/") + "/api/chat")
        body = json.dumps({
            "text": text,
            "mode": "coder" if self.mode.text == "Кодер" else "chat",
            "history": self.history[-20:-1],
        }).encode("utf-8")
        context = ssl._create_unverified_context()
        conn = http.client.HTTPSConnection(parsed.hostname, port, context=context, timeout=90)
        try:
            conn.connect()
            certificate = conn.sock.getpeercert(binary_form=True)
            actual = hashlib.sha256(certificate).hexdigest().upper()
            if not hmac.compare_digest(actual, expected):
                raise RuntimeError("Сертифікат комп’ютера не збігається з відбитком. Перевір адресу й SHA-256.")
            conn.request("POST", path, body=body, headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            })
            response = conn.getresponse()
            data = json.loads(response.read(40_000).decode("utf-8"))
            if response.status != 200:
                raise RuntimeError(data.get("error", f"Jarvis повернув HTTP {response.status}."))
            return str(data.get("reply", "")).strip()
        finally:
            conn.close()

    def _finish(self, reply, error):
        self.busy = False
        self.send_button.disabled = False
        if error:
            self.history.append({"role": "assistant", "content": "Помилка: " + error})
            self.status.text = "Не вдалося отримати відповідь"
        else:
            self.history.append({"role": "assistant", "content": reply})
            self.status.text = "Готовий"
        self.history = self.history[-60:]
        self.store.put("chat", messages=self.history)
        self.refresh_chat()


if __name__ == "__main__":
    JarvisMobile().run()
