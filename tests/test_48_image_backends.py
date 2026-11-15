# -*- coding: utf-8 -*-
"""Local ComfyUI and free cloud image backends."""
from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core.image_backends import (
    backend_chain,
    comfyui_workflow,
    ensure_comfyui,
    generate_comfyui,
    generate_pollinations,
    generate_with_backend,
    parse_size,
)
from core.image_gen import ImageGenError


def png_bytes() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (90, 20, 140)).save(buffer, format="PNG")
    return buffer.getvalue()


class Resp:
    def __init__(self, status_code=200, payload=None, content=b"", text=""):
        self.status_code = status_code
        self._payload = payload
        self.content = content
        self.text = text

    def json(self):
        return self._payload


class ComfySession:
    def __init__(self):
        self.posts: list[dict] = []
        self.views: list[dict] = []

    def post(self, url, json=None, timeout=None):
        self.posts.append(json or {})
        return Resp(200, {"prompt_id": "p1"})

    def get(self, url, params=None, timeout=None):
        if "/history/" in url:
            return Resp(
                200,
                {
                    "p1": {
                        "outputs": {
                            "7": {
                                "images": [
                                    {"filename": "jarvis-00001_.png", "subfolder": "", "type": "output"}
                                ]
                            }
                        }
                    }
                },
            )
        if "/view" in url:
            self.views.append(params or {})
            return Resp(200, content=png_bytes())
        return Resp(404)


class PollSession:
    def __init__(self):
        self.url = ""
        self.params: dict = {}

    def get(self, url, params=None, timeout=None):
        self.url = url
        self.params = params or {}
        return Resp(200, content=png_bytes())


class BackendTests(unittest.TestCase):
    def test_parse_size(self) -> None:
        self.assertEqual(parse_size("1024x1536"), (1024, 1536))
        self.assertEqual(parse_size("auto"), (1024, 1024))
        self.assertEqual(parse_size("bad"), (1024, 1024))

    def test_workflow_has_prompt_and_settings(self) -> None:
        workflow = comfyui_workflow(
            "neon cat", checkpoint="model.safetensors",
            width=1024, height=1536, steps=8, cfg_value=1.0,
        )
        self.assertEqual(workflow["1"]["inputs"]["ckpt_name"], "model.safetensors")
        self.assertEqual(workflow["2"]["inputs"]["text"], "neon cat")
        self.assertEqual(workflow["4"]["inputs"]["width"], 1024)
        self.assertEqual(workflow["4"]["inputs"]["height"], 1536)
        self.assertEqual(workflow["5"]["inputs"]["steps"], 8)

    def test_comfyui_generation(self) -> None:
        session = ComfySession()
        with tempfile.TemporaryDirectory() as tmp:
            path = generate_comfyui(
                "neon cat",
                output_dir=Path(tmp),
                checkpoint="model.safetensors",
                width=1024,
                height=1024,
                session=session,
                poll_interval=0,
            )
            self.assertTrue(path.is_file())
        self.assertEqual(session.posts[0]["prompt"]["2"]["inputs"]["text"], "neon cat")
        self.assertEqual(session.views[0]["filename"], "jarvis-00001_.png")

    def test_pollinations_generation(self) -> None:
        session = PollSession()
        with tempfile.TemporaryDirectory() as tmp:
            path = generate_pollinations(
                "кіт у неоні", output_dir=Path(tmp),
                width=1024, height=1536, session=session,
            )
            self.assertTrue(path.is_file())
        self.assertIn("image.pollinations.ai/prompt/", session.url)
        self.assertIn("%D0%BA", session.url)
        self.assertEqual(session.params["width"], 1024)
        self.assertEqual(session.params["height"], 1536)

    def test_backend_chain(self) -> None:
        self.assertEqual(backend_chain({"image_backend": "comfyui"}), ["comfyui"])
        self.assertEqual(
            backend_chain(
                {"image_backend": "auto", "openai_api_key": "sk", "image_allow_public_fallback": True}
            ),
            ["comfyui", "openai", "pollinations"],
        )
        self.assertEqual(
            backend_chain({"image_backend": "auto", "openai_api_key": ""}),
            ["comfyui"],
        )

    def test_auto_falls_back_to_public_cloud(self) -> None:
        cfg = {
            "image_backend": "auto",
            "openai_api_key": "",
            "image_allow_public_fallback": True,
            "comfyui_autostart": False,
            "comfyui_url": "http://127.0.0.1:9",
            "comfyui_checkpoint": "model.safetensors",
            "comfyui_steps": 6,
            "comfyui_cfg": 1.0,
        }
        target = Path("fallback.png")
        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "core.image_backends.generate_comfyui",
            side_effect=ImageGenError("down"),
        ), mock.patch(
            "core.image_backends.generate_pollinations", return_value=target
        ):
            path, backend = generate_with_backend(
                "cat", cfg=cfg, output_dir=Path(tmp)
            )
        self.assertEqual(path, target)
        self.assertEqual(backend, "Pollinations")

    def test_ensure_comfyui_without_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(
                ensure_comfyui(
                    {
                        "comfyui_url": "http://127.0.0.1:9",
                        "comfyui_dir": tmp,
                        "comfyui_autostart": True,
                    },
                    wait_seconds=0.1,
                )
            )


if __name__ == "__main__":
    unittest.main()
