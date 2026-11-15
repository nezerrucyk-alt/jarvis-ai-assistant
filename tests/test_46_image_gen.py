# -*- coding: utf-8 -*-
"""OpenAI image generation: client, payload and PcTools integration."""
from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core.image_gen import (
    DEFAULT_MODEL,
    ImageGenError,
    generate_image,
)
from tests.helpers import import_jarvis, install_temp_paths, restore_paths


def png_bytes(color: tuple[int, int, int] = (10, 20, 30)) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buffer, format="PNG")
    return buffer.getvalue()


class FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        payload=None,
        content: bytes = b"",
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.content = content
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class ImageGenClientTests(unittest.TestCase):
    def test_empty_prompt_and_missing_key_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ImageGenError):
                generate_image("   ", api_key="sk-test", output_dir=Path(tmp))
            with self.assertRaises(ImageGenError) as ctx:
                generate_image("кіт", api_key="", output_dir=Path(tmp))
            self.assertIn("OPENAI", str(ctx.exception))

    def test_b64_response_is_saved_as_png(self) -> None:
        import base64

        calls: list[dict] = []

        def fake_post(url, headers=None, json=None, timeout=None):
            calls.append({"url": url, "headers": headers, "json": json})
            return FakeResponse(
                payload={"data": [{"b64_json": base64.b64encode(png_bytes()).decode()}]}
            )

        with tempfile.TemporaryDirectory() as tmp:
            path = generate_image(
                "  a cat astronaut  ",
                api_key="sk-test",
                output_dir=Path(tmp) / "images",
                post=fake_post,
            )
            self.assertTrue(path.is_file())
            self.assertEqual(path.suffix, ".png")
            self.assertTrue(path.name.startswith("jarvis-"))
            payload = calls[0]["json"]
            self.assertEqual(payload["prompt"], "a cat astronaut")
            self.assertEqual(payload["model"], DEFAULT_MODEL)
            self.assertEqual(payload["size"], "1024x1024")
            self.assertEqual(payload["quality"], "auto")
            self.assertEqual(payload["n"], 1)
            self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer sk-test")

    def test_invalid_model_size_and_quality_fall_back(self) -> None:
        captured: dict = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured.update(json or {})
            return FakeResponse(
                payload={"data": [{"b64_json": __import__("base64").b64encode(png_bytes()).decode()}]}
            )

        with tempfile.TemporaryDirectory() as tmp:
            generate_image(
                "постер",
                api_key="sk-test",
                output_dir=Path(tmp),
                model="dall-e-3",
                size="999x999",
                quality="ultra",
                post=fake_post,
            )
        self.assertEqual(captured["model"], DEFAULT_MODEL)
        self.assertEqual(captured["size"], "1024x1024")
        self.assertEqual(captured["quality"], "auto")

    def test_too_long_prompt_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ImageGenError) as ctx:
                generate_image(
                    "x" * 4001, api_key="sk-test", output_dir=Path(tmp)
                )
            self.assertIn("занадто довгий", str(ctx.exception))

    def test_429_is_retried_then_succeeds(self) -> None:
        import base64

        calls: list[int] = []

        def fake_post(url, headers=None, json=None, timeout=None):
            calls.append(1)
            if len(calls) == 1:
                return FakeResponse(
                    status_code=429, payload={"error": {"message": "rate"}}
                )
            return FakeResponse(
                payload={"data": [{"b64_json": base64.b64encode(png_bytes()).decode()}]}
            )

        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "core.image_gen.time.sleep"
        ):
            path = generate_image(
                "кіт", api_key="sk-test", output_dir=Path(tmp), post=fake_post
            )
            self.assertTrue(path.is_file())
        self.assertEqual(len(calls), 2)

    def test_400_unsupported_param_retries_with_minimal_payload(self) -> None:
        import base64

        payloads: list[dict] = []

        def fake_post(url, headers=None, json=None, timeout=None):
            payloads.append(dict(json or {}))
            if len(payloads) == 1:
                return FakeResponse(
                    status_code=400,
                    payload={"error": {"message": "Unknown parameter: quality"}},
                )
            return FakeResponse(
                payload={"data": [{"b64_json": base64.b64encode(png_bytes()).decode()}]}
            )

        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "core.image_gen.time.sleep"
        ):
            generate_image(
                "кіт", api_key="sk-test", output_dir=Path(tmp),
                model="gpt-image-1-mini", quality="high", post=fake_post,
            )
        self.assertEqual(payloads[1]["model"], DEFAULT_MODEL)
        self.assertNotIn("quality", payloads[1])
        self.assertNotIn("output_format", payloads[1])

    def test_old_images_are_pruned(self) -> None:
        import base64
        import os

        def fake_post(url, headers=None, json=None, timeout=None):
            return FakeResponse(
                payload={"data": [{"b64_json": base64.b64encode(png_bytes()).decode()}]}
            )

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "images"
            folder.mkdir()
            for index in range(4):
                old = folder / f"jarvis-old{index}.png"
                old.write_bytes(png_bytes())
                stamp = 1_700_000_000 - index * 100
                os.utime(old, (stamp, stamp))
            generate_image(
                "кіт", api_key="sk-test", output_dir=folder,
                keep=2, post=fake_post,
            )
            self.assertEqual(len(list(folder.glob("jarvis-*"))), 2)

    def test_401_and_429_have_friendly_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for status, fragment in ((401, "ключ"), (429, "частоту")):
                def fake_post(url, headers=None, json=None, timeout=None, status=status):
                    return FakeResponse(status_code=status, payload={"error": {"message": "nope"}})

                with self.assertRaises(ImageGenError) as ctx:
                    generate_image(
                        "кіт", api_key="sk-test", output_dir=Path(tmp), post=fake_post
                    )
                self.assertIn(fragment, str(ctx.exception))

    def test_url_response_is_downloaded(self) -> None:
        def fake_post(url, headers=None, json=None, timeout=None):
            return FakeResponse(payload={"data": [{"url": "https://example.test/img.png"}]})

        def fake_get(url, timeout=None):
            return FakeResponse(content=png_bytes())

        with tempfile.TemporaryDirectory() as tmp:
            path = generate_image(
                "кіт",
                api_key="sk-test",
                output_dir=Path(tmp),
                post=fake_post,
                get=fake_get,
            )
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 0)

    def test_non_image_payload_is_rejected(self) -> None:
        import base64

        def fake_post(url, headers=None, json=None, timeout=None):
            return FakeResponse(
                payload={"data": [{"b64_json": base64.b64encode(b"not an image").decode()}]}
            )

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ImageGenError):
                generate_image(
                    "кіт", api_key="sk-test", output_dir=Path(tmp), post=fake_post
                )


class PcToolsImageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.jarvis = import_jarvis()
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp.name)
        self.saved = install_temp_paths(
            self.jarvis, self.tmp_dir, {"openai_api_key": "sk-test"}
        )
        self.cfg = self.jarvis.load_config()
        self.tools = self.jarvis.PcTools(
            lambda action, detail: False,
            lambda text: None,
            get_cfg=lambda: self.cfg,
        )

    def tearDown(self) -> None:
        restore_paths(self.jarvis, self.saved)
        self.tmp.cleanup()

    def test_tool_is_registered_and_allowed_in_restricted_mode(self) -> None:
        names = [tool["function"]["name"] for tool in self.jarvis.TOOLS]
        self.assertIn("generate_image", names)
        self.assertIn("generate_image", self.jarvis.RESTRICTED_TOOL_NAMES)
        self.assertIn("generate_image", self.jarvis.SYSTEM_PROMPT)

    def test_generate_image_queues_path_and_passes_settings(self) -> None:
        self.cfg["image_model"] = "gpt-image-1-mini"
        self.cfg["image_size"] = "1024x1536"
        self.cfg["image_quality"] = "high"
        target = self.tmp_dir / "images" / "result.png"
        with mock.patch.object(
            self.jarvis.image_gen, "generate_image", return_value=target
        ) as generator:
            result = self.tools.run("generate_image", {"prompt": "нічне місто"})
        self.assertIn("Зображення згенеровано", result)
        self.assertEqual(self.tools.take_generated_images(), [str(target)])
        self.assertEqual(self.tools.take_generated_images(), [])
        kwargs = generator.call_args.kwargs
        self.assertEqual(kwargs["api_key"], "sk-test")
        self.assertEqual(kwargs["output_dir"], self.tmp_dir / "images")
        self.assertEqual(kwargs["model"], "gpt-image-1-mini")
        self.assertEqual(kwargs["size"], "1024x1536")
        self.assertEqual(kwargs["quality"], "high")

    def test_prompt_enhancer_is_used(self) -> None:
        self.cfg["image_prompt_enhance"] = True
        target = self.tmp_dir / "images" / "enhanced.png"
        tools = self.jarvis.PcTools(
            lambda action, detail: False,
            lambda text: None,
            get_cfg=lambda: self.cfg,
            prompt_enhancer=lambda prompt: "DETAILED: " + prompt,
        )
        with mock.patch.object(
            self.jarvis.image_gen, "generate_image", return_value=target
        ) as generator:
            result = tools.run("generate_image", {"prompt": "кіт"})
        self.assertIn("чат-моделлю", result)
        self.assertEqual(generator.call_args.args[0], "DETAILED: кіт")

    def test_generate_image_error_is_returned_without_queueing(self) -> None:
        with mock.patch.object(
            self.jarvis.image_gen,
            "generate_image",
            side_effect=self.jarvis.image_gen.ImageGenError("немає ключа"),
        ):
            result = self.tools.run("generate_image", {"prompt": "кіт"})
        self.assertIn("немає ключа", result)
        self.assertEqual(self.tools.take_generated_images(), [])


if __name__ == "__main__":
    unittest.main()
