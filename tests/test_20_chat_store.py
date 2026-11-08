# -*- coding: utf-8 -*-
"""Чат-сховище JarvisApp: створення, збереження, перемикання, видалення, відновлення."""
from __future__ import annotations

import json
import unittest
from unittest import mock

from tests.helpers import JarvisAppEnv, pump


class ChatStoreTests(JarvisAppEnv):
    # ── початковий стан ──────────────────────────────────────────────────────
    def test_fresh_start_creates_chat_with_sys_greeting(self) -> None:
        app = self.make_app()
        self.assertEqual(len(app.chats), 1)
        chat = app.current_chat
        self.assertIsInstance(chat, dict)
        self.assertEqual(chat.get("title"), "Нова розмова")
        self.assertEqual(len(chat.get("messages") or []), 1)
        first = chat["messages"][0]
        self.assertEqual(first["who"], "sys")
        self.assertIn("онлайн", first["text"])

    def test_missing_chats_json_creates_fresh_chat(self) -> None:
        self.assertFalse(self.jarvis.CHATS_PATH.exists())
        app = self.make_app()
        self.assertIsInstance(app.current_chat, dict)

    def test_chats_json_schema_matches_contract(self) -> None:
        app = self.make_app()
        app._log("you", "Тестове питання")
        app._log("jarvis", "Тестова відповідь")
        app._flush_chats_save()
        data = self.saved_chats()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        chat = data[0]
        for key in ("id", "title", "created", "updated", "messages"):
            self.assertIn(key, chat, f"у chats.json немає ключа {key}")
        self.assertIsInstance(chat["messages"], list)
        for message in chat["messages"]:
            self.assertIn("who", message)
            self.assertIn("text", message)
            self.assertIn("t", message)
            self.assertIn(message["who"], ("you", "jarvis", "sys"))

    # ── запис повідомлень і заголовок ───────────────────────────────────────
    def test_log_appends_to_current_chat_and_flushes(self) -> None:
        app = self.make_app()
        before = len(app.current_chat["messages"])
        app._log("you", "Привіт, як справи?")
        app._log("jarvis", "Все добре, сер.")
        self.assertEqual(len(app.current_chat["messages"]), before + 2)
        app._flush_chats_save()
        data = self.saved_chats()
        texts = [m["text"] for m in data[0]["messages"]]
        self.assertIn("Привіт, як справи?", texts)
        self.assertIn("Все добре, сер.", texts)

    def test_title_derived_from_first_user_message(self) -> None:
        app = self.make_app()
        app._log("you", "Привіт, як справи?")
        self.assertEqual(app.current_chat.get("title"), "Привіт, як справи?")
        app._log("jarvis", "Добре!")
        app._log("you", "Ще одне повідомлення")
        self.assertEqual(
            app.current_chat.get("title"),
            "Привіт, як справи?",
            "заголовок не має змінюватися після першої репліки",
        )

    # ── нова розмова / перемикання / видалення ──────────────────────────────
    def test_new_conversation_saves_previous(self) -> None:
        app = self.make_app()
        first = self.make_chat("Питання першої розмови", "Відповідь першої розмови")
        first_id = first["id"]
        app._new_conversation()
        pump(app.root, 100)
        self.assertNotEqual(app.current_chat["id"], first_id)
        app._flush_chats_save()
        data = self.saved_chats()
        saved_first = next((c for c in data if c.get("id") == first_id), None)
        self.assertIsNotNone(saved_first, "попередня розмова не збережена")
        self.assertGreaterEqual(len(saved_first["messages"]), 3)

    def test_switch_chat_restores_log_and_brain_history(self) -> None:
        app = self.make_app()
        first = self.make_chat("Питання A", "Відповідь A")
        app._new_conversation()
        pump(app.root, 100)
        self.make_chat("Питання B", "Відповідь B")

        self.assertTrue(app._switch_chat(first))
        pump(app.root, 100)
        text = self.log_text(app)
        self.assertIn("Питання A", text)
        self.assertIn("Відповідь A", text)
        self.assertNotIn("Питання B", text)
        self.assertNotIn("Відповідь B", text)

        history = app.brain.history
        self.assertEqual([item["role"] for item in history], ["user", "assistant"])
        self.assertEqual(history[0]["content"], "Питання A")
        self.assertEqual(history[1]["content"], "Відповідь A")

    def test_switch_to_current_chat_is_noop_success(self) -> None:
        app = self.make_app()
        self.assertTrue(app._switch_chat(app.current_chat))
        self.assertEqual(app.current_chat["id"], app.chats[0]["id"])

    def test_delete_current_chat_falls_back_to_another(self) -> None:
        app = self.make_app()
        first = self.make_chat("Питання A", "Відповідь A")
        first_id = first["id"]
        app._new_conversation()
        second = self.make_chat("Питання B", "Відповідь B")
        second_id = second["id"]

        self.assertTrue(app._switch_chat(first))
        app._delete_chat(app.current_chat)
        pump(app.root, 100)
        self.assertIsNotNone(app.current_chat)
        self.assertEqual(app.current_chat["id"], second_id)
        self.assertIn("Питання B", self.log_text(app))
        app._flush_chats_save()
        data = self.saved_chats()
        self.assertTrue(all(chat.get("id") != first_id for chat in data))

    def test_delete_last_chat_creates_fresh_chat(self) -> None:
        app = self.make_app()
        only = self.make_chat("Єдина розмова", "Єдина відповідь")
        only_id = only["id"]
        app._delete_chat(app.current_chat)
        pump(app.root, 100)
        self.assertIsNotNone(app.current_chat)
        self.assertNotEqual(app.current_chat["id"], only_id)
        self.assertEqual(len(app.chats), 1)

    def test_busy_guards_switch_and_new_conversation(self) -> None:
        app = self.make_app()
        first = self.make_chat("Питання A", "Відповідь A")
        app._new_conversation()
        pump(app.root, 100)
        app.busy.set()
        try:
            self.assertFalse(app._switch_chat(first))
            count_before = len(app.chats)
            app._new_conversation()
            self.assertEqual(len(app.chats), count_before)
        finally:
            app.busy.clear()

    # ── стійкість до пошкоджених даних ──────────────────────────────────────
    def test_corrupt_chats_json_tolerated(self) -> None:
        self.jarvis.CHATS_PATH.write_text("{ це не json", encoding="utf-8")
        app = self.make_app()
        self.assertIsInstance(app.current_chat, dict)
        self.assertGreaterEqual(len(app.chats), 1)

    def test_wrong_json_type_chats_tolerated(self) -> None:
        self.jarvis.CHATS_PATH.write_text('{"not": "a list"}', encoding="utf-8")
        app = self.make_app()
        self.assertIsInstance(app.current_chat, dict)

    # ── збереження під час закриття та між запусками ────────────────────────
    def test_close_flushes_unsaved_messages(self) -> None:
        app = self.make_app()
        app._log("you", "Повідомлення перед закриттям")
        # навмисно не викликаємо _flush_chats_save — _on_close мусить зберегти
        self.close_current_app()
        data = self.saved_chats()
        texts = [m.get("text") for chat in data for m in chat.get("messages", [])]
        self.assertIn("Повідомлення перед закриттям", texts)

    def test_chats_persist_between_two_instances(self) -> None:
        app = self.make_app()
        app._log("you", "Розмова, що переживе перезапуск")
        app._log("jarvis", "Збережено.")
        chat_id = app.current_chat["id"]
        self.close_current_app()

        app2 = self.make_app()
        self.assertEqual(app2.current_chat["id"], chat_id)
        self.assertIn("Розмова, що переживе перезапуск", self.log_text(app2))
        history = app2.brain.history
        self.assertEqual([item["role"] for item in history], ["user", "assistant"])

    def test_max_chats_limit_trimmed_on_save(self) -> None:
        app = self.make_app()
        with mock.patch.object(self.jarvis, "MAX_CHATS", 2):
            for index in range(3):
                self.make_chat(f"Питання {index}", f"Відповідь {index}")
                app._new_conversation()
                pump(app.root, 100)
            app._flush_chats_save()
            app._save_chats()
            self.assertEqual(len(app.chats), 2)
            self.assertEqual(len(self.saved_chats()), 2)


if __name__ == "__main__":
    unittest.main()
