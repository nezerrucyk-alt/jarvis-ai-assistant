# -*- coding: utf-8 -*-
"""Render the first J.A.R.V.I.S. TikTok video (1080x1920, 25 s).

The video is assembled from the existing 3D logo animation and UI
screenshots, with procedurally drawn captions, cards and a generated
soundtrack.  No external media beyond the repository assets is used.

Usage:
    python assets/social/render_tiktok_01.py            # full render
    python assets/social/render_tiktok_01.py --preview  # key frames only
"""
from __future__ import annotations

import math
import os
import random
import sys
import wave
from functools import lru_cache
from pathlib import Path

import imageio
import imageio.v3 as iio
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "website" / "assets"
OUT_DIR = ROOT / "assets" / "social"
LOGO_VIDEO = ROOT / "assets" / "logo" / "jarvis-logo-3d.mp4"

W, H = 1080, 1920
FPS = 30
DURATION = 25.0
TOTAL_FRAMES = int(FPS * DURATION)

# ── palette ─────────────────────────────────────────────────────────────────
BG = (5, 11, 24)
BG_BOTTOM = (7, 18, 38)
PANEL = (10, 23, 46)
PANEL_LIGHT = (14, 31, 58)
BORDER = (30, 53, 85)
BLUE = (77, 163, 255)
BLUE_DARK = (32, 103, 220)
CYAN = (140, 200, 255)
WHITE = (240, 244, 255)
MUTED = (150, 170, 200)
DIM = (96, 120, 155)
GREEN = (90, 209, 160)

FONT_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"
FONT_REG = r"C:\Windows\Fonts\segoeui.ttf"
FONT_LIGHT = r"C:\Windows\Fonts\segoeuisl.ttf"
FONT_TECH = r"C:\Windows\Fonts\bahnschrift.ttf"
FONT_MONO = r"C:\Windows\Fonts\consola.ttf"
FONT_MONO_B = r"C:\Windows\Fonts\consolab.ttf"


@lru_cache(maxsize=64)
def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


# ── small helpers ───────────────────────────────────────────────────────────
def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def ease_out(t: float) -> float:
    t = clamp(t)
    return 1.0 - (1.0 - t) ** 3


def ease_in_out(t: float) -> float:
    t = clamp(t)
    return t * t * (3.0 - 2.0 * t)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(a: tuple, b: tuple, t: float) -> tuple:
    t = clamp(t)
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def with_alpha(color: tuple, alpha: int) -> tuple:
    return (color[0], color[1], color[2], int(clamp(alpha, 0, 255)))


def text_width(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, tracking: float = 0) -> float:
    if not text:
        return 0.0
    width = sum(draw.textlength(ch, font=fnt) for ch in text)
    return width + tracking * (len(text) - 1)


def draw_tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill,
    tracking: float = 0,
) -> None:
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking


def draw_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill,
    cx: float,
    top: float,
    tracking: float = 0,
) -> float:
    width = text_width(draw, text, fnt, tracking)
    bbox = draw.textbbox((0, 0), text, font=fnt)
    draw_tracked(draw, (cx - width / 2, top - bbox[1]), text, fnt, fill, tracking)
    return top + (bbox[3] - bbox[1])


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    fnt: ImageFont.FreeTypeFont,
    max_width: float,
) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if draw.textlength(candidate, font=fnt) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_lines_centered(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    fnt: ImageFont.FreeTypeFont,
    fill,
    cx: float,
    top: float,
    line_gap: float = 6,
) -> float:
    y = top
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=fnt)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        draw.text((cx - width / 2 - bbox[0], y - bbox[1]), line, font=fnt, fill=fill)
        y += height + line_gap
    return y


def rounded_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[float, float, float, float],
    radius: int,
    fill,
    outline=None,
    width: int = 2,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


# ── background ──────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def background_base() -> Image.Image:
    top = np.array(BG, dtype=np.float32)
    bottom = np.array(BG_BOTTOM, dtype=np.float32)
    ramp = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None, None]
    arr = top[None, None, :] * (1 - ramp) + bottom[None, None, :] * ramp
    arr = np.repeat(arr, W, axis=1)
    base = Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-260, 120, 620, 1000), fill=(28, 92, 190, 46))
    gd.ellipse((620, 1040, 1380, 1840), fill=(16, 74, 160, 36))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    base = Image.alpha_composite(base, glow)

    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    for x in range(0, W + 1, 90):
        gd.line((x, 0, x, H), fill=(38, 72, 120, 22), width=1)
    for y in range(0, H + 1, 90):
        gd.line((0, y, W, y), fill=(38, 72, 120, 22), width=1)
    base = Image.alpha_composite(base, grid)

    # smooth radial vignette instead of hard concentric rectangles
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx = (xx - W * 0.5) / (W * 0.62)
    dy = (yy - H * 0.45) / (H * 0.62)
    distance = np.sqrt(dx * dx + dy * dy)
    vignette = np.clip((distance - 0.45) / 0.75, 0.0, 1.0) ** 1.5 * 0.62
    rgb = np.asarray(base.convert("RGB"), dtype=np.float32)
    rgb *= 1.0 - vignette[..., None]
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def add_particles(base: Image.Image, t: float, seed: int = 7) -> Image.Image:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    rng = random.Random(seed)
    for index in range(34):
        x = rng.uniform(40, W - 40)
        y0 = rng.uniform(0, H)
        speed = rng.uniform(6, 20)
        y = (y0 - speed * t) % H
        radius = rng.uniform(1.2, 3.2)
        alpha = int(30 + 40 * (0.5 + 0.5 * math.sin(t * 1.7 + index)))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(120, 180, 255, alpha))
    return Image.alpha_composite(base, layer)


def add_scanline(base: Image.Image, t: float) -> Image.Image:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    y = int((t * 130) % (H + 300)) - 150
    draw.rectangle((0, y, W, y + 2), fill=(90, 160, 255, 12))
    draw.rectangle((0, y + 2, W, y + 26), fill=(70, 130, 255, 3))
    return Image.alpha_composite(base, layer)


def base_frame(t: float) -> Image.Image:
    return add_particles(background_base(), t)


# ── mark ────────────────────────────────────────────────────────────────────
def hex_points(cx: float, cy: float, radius: float, rotation: float = -math.pi / 2) -> list[tuple[float, float]]:
    return [
        (
            cx + radius * math.cos(rotation + i * math.pi / 3),
            cy + radius * math.sin(rotation + i * math.pi / 3),
        )
        for i in range(6)
    ]


def draw_hex_mark(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    radius: float,
    color: tuple,
    width: int,
    gap_edge: int = 0,
) -> None:
    points = hex_points(cx, cy, radius)
    for index in range(6):
        p1 = points[index]
        p2 = points[(index + 1) % 6]
        if index == gap_edge:
            start = (lerp(p1[0], p2[0], 0.18), lerp(p1[1], p2[1], 0.18))
            end = (lerp(p1[0], p2[0], 0.78), lerp(p1[1], p2[1], 0.78))
            draw.line((start, end), fill=color, width=width)
        else:
            draw.line((p1, p2), fill=color, width=width)
    # inner core: a smaller hexagon and a glowing dot
    inner = hex_points(cx, cy, radius * 0.46)
    draw.line(inner + [inner[0]], fill=color, width=max(2, width - 2))
    core = radius * 0.14
    draw.ellipse((cx - core, cy - core, cx + core, cy + core), fill=color)


@lru_cache(maxsize=16)
def mark_image(radius: int, color: tuple, glow: bool = True) -> Image.Image:
    pad = int(radius * 0.55) if glow else int(radius * 0.1)
    size = int(radius * 2 + pad * 2)
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx = cy = size / 2
    if glow:
        halo = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        hd = ImageDraw.Draw(halo)
        draw_hex_mark(hd, cx, cy, radius, with_alpha(color, 110), max(6, radius // 18))
        halo = halo.filter(ImageFilter.GaussianBlur(radius * 0.09))
        layer = Image.alpha_composite(layer, halo)
        layer = Image.alpha_composite(layer, halo)
    draw = ImageDraw.Draw(layer)
    draw_hex_mark(draw, cx, cy, radius, with_alpha(color, 255), max(3, radius // 26))
    return layer


# ── window with a screenshot ────────────────────────────────────────────────
def fit_crop(image: Image.Image, aspect: float) -> Image.Image:
    w, h = image.size
    current = w / h
    if current > aspect:
        new_w = int(h * aspect)
        left = (w - new_w) // 2
        return image.crop((left, 0, left + new_w, h))
    new_h = int(w / aspect)
    top = (h - new_h) // 2
    return image.crop((0, top, w, top + new_h))


def crop_zoom(image: Image.Image, zoom: float, focus: tuple[float, float]) -> Image.Image:
    if zoom <= 1.0001:
        return image
    w, h = image.size
    cw, ch = w / zoom, h / zoom
    cx, cy = focus[0] * w, focus[1] * h
    left = clamp(cx - cw / 2, 0, w - cw)
    top = clamp(cy - ch / 2, 0, h - ch)
    return image.crop((int(left), int(top), int(left + cw), int(top + ch)))


def screenshot_window(
    path: Path,
    width: int,
    height: int,
    title: str,
    zoom: float = 1.0,
    focus: tuple[float, float] = (0.5, 0.5),
) -> Image.Image:
    bar = 52
    area_w, area_h = width, height - bar
    source = fit_crop(Image.open(path).convert("RGB"), area_w / area_h)
    source = crop_zoom(source, zoom, focus).resize((area_w, area_h), Image.LANCZOS)

    panel = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    rounded_panel(draw, (0, 0, width - 1, height - 1), 22, PANEL + (255,), BORDER + (255,), 2)
    draw.rounded_rectangle((1, 1, width - 2, bar), radius=20, fill=PANEL_LIGHT + (255,))
    draw.rectangle((1, bar - 14, width - 2, bar), fill=PANEL_LIGHT + (255,))
    for index, color in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        cx = 26 + index * 24
        draw.ellipse((cx - 6, bar / 2 - 6, cx + 6, bar / 2 + 6), fill=color + (255,))
    title_font = font(FONT_MONO, 20)
    draw.text((112, bar / 2 - 11), title, font=title_font, fill=DIM + (255,))

    mask = Image.new("L", (area_w, area_h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, area_w, area_h), radius=20, fill=255, corners=(False, False, True, True))
    panel.paste(source, (0, bar), mask)
    draw = ImageDraw.Draw(panel)
    draw.line((0, bar, width, bar), fill=BORDER + (255,), width=1)
    return panel


def paste_with_glow(
    base: Image.Image,
    layer: Image.Image,
    position: tuple[int, int],
    glow_color: tuple = BLUE,
    glow_alpha: int = 80,
    glow_radius: int = 34,
) -> Image.Image:
    halo = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    mask = layer.getchannel("A")
    halo.paste(with_alpha(glow_color, glow_alpha), (0, 0), mask)
    halo = halo.filter(ImageFilter.GaussianBlur(glow_radius))
    position = (int(position[0]), int(position[1]))
    base.alpha_composite(halo, position)
    base.alpha_composite(layer, position)
    return base


# ── text blocks ─────────────────────────────────────────────────────────────
def kicker(draw: ImageDraw.ImageDraw, text: str, cx: float, y: float, color=BLUE, size: int = 26) -> None:
    fnt = font(FONT_TECH, size)
    draw_centered(draw, text.upper(), fnt, color + (255,), cx, y, tracking=6)


def headline(
    draw: ImageDraw.ImageDraw,
    text: str,
    cx: float,
    top: float,
    size: int = 84,
    color=WHITE,
    max_width: float = 920,
    line_gap: int = 4,
    accent: str | None = None,
) -> float:
    fnt = font(FONT_BOLD, size)
    lines = wrap_text(draw, text, fnt, max_width)
    if accent:
        # draw the accent word in blue inside the last line by splitting it
        pass
    return draw_lines_centered(draw, lines, fnt, color + (255,), cx, top, line_gap)


def draw_headline_accent(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    fnt: ImageFont.FreeTypeFont,
    cx: float,
    top: float,
    accent: str,
    line_gap: int = 4,
) -> float:
    y = top
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=fnt)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        x = cx - width / 2 - bbox[0]
        if accent and accent in line:
            before, _, after = line.partition(accent)
            bx = x
            if before:
                draw.text((bx, y - bbox[1]), before, font=fnt, fill=WHITE + (255,))
                bx += draw.textlength(before, font=fnt)
            draw.text((bx, y - bbox[1]), accent, font=fnt, fill=BLUE + (255,))
            bx += draw.textlength(accent, font=fnt)
            if after:
                draw.text((bx, y - bbox[1]), after, font=fnt, fill=WHITE + (255,))
        else:
            draw.text((x, y - bbox[1]), line, font=fnt, fill=WHITE + (255,))
        y += height + line_gap
    return y


def fade_layer(layer: Image.Image, alpha: float) -> Image.Image:
    if alpha >= 0.999:
        return layer
    result = layer.copy()
    result.putalpha(result.getchannel("A").point(lambda value: int(value * clamp(alpha))))
    return result


# ── segment: hook (0–3 s) ───────────────────────────────────────────────────
def render_hook(t: float) -> Image.Image:
    frame = base_frame(t)
    local = clamp(t / 3.0)
    zoom = 1.0 + 0.035 * ease_in_out(local)

    # slow rotating hexagon behind the text
    mark_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    md = ImageDraw.Draw(mark_layer)
    draw_hex_mark(md, W / 2, 1120, 330, (60, 120, 210, 26), 3)
    draw_hex_mark(md, W / 2, 1120, 210, (60, 120, 210, 18), 2)
    angle = t * 0.12
    for index in range(3):
        a = angle + index * 2 * math.pi / 3
        x = W / 2 + 330 * math.cos(a)
        y = 1120 + 330 * math.sin(a)
        md.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(90, 160, 255, 70))
    frame.alpha_composite(mark_layer)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    kicker(draw, "J.A.R.V.I.S. · AI-АСИСТЕНТ", W / 2, 360)
    fnt = font(FONT_BOLD, 92)
    lines = wrap_text(draw, "А що, якби ти мав власного J.A.R.V.I.S.?", fnt, 900)
    y = 470 + 30 * (1 - ease_out(clamp(t / 0.55)))
    draw_headline_accent(draw, lines, fnt, W / 2, y, "J.A.R.V.I.S.?", 8)

    body = font(FONT_REG, 38)
    draw_centered(
        draw,
        "Голос. ПК. Roblox. 78 моделей.",
        body,
        MUTED + (255,),
        W / 2,
        860,
    )

    pills = ["ГОЛОС", "ПК", "ROBLOX STUDIO", "78 МОДЕЛЕЙ"]
    pill_font = font(FONT_TECH, 25)
    widths = [text_width(draw, text, pill_font, 3) + 44 for text in pills]
    total = sum(widths) + 14 * (len(pills) - 1)
    x = W / 2 - total / 2
    for index, (text, width) in enumerate(zip(pills, widths)):
        appear = clamp((t - 0.55 - index * 0.12) / 0.35)
        if appear <= 0:
            continue
        alpha = int(255 * ease_out(appear))
        y_off = 18 * (1 - ease_out(appear))
        box = (x, 1030 + y_off, x + width, 1082 + y_off)
        draw.rounded_rectangle(box, radius=26, fill=(16, 35, 64, int(alpha * 0.9)), outline=(45, 90, 150, alpha), width=1)
        draw_centered(draw, text, pill_font, (160, 200, 245, alpha), x + width / 2, 1044 + y_off, tracking=3)
        x += width + 14

    draw.text((70, 1500), "01 / 05", font=font(FONT_MONO, 24), fill=(90, 120, 160, 200))
    draw.text((W - 70, 1500), "TIKTOK DEMO", font=font(FONT_MONO, 24), fill=(90, 120, 160, 200), anchor="ra")

    frame.alpha_composite(fade_layer(overlay, clamp(t / 0.35)))
    if zoom > 1.001:
        frame = frame.resize((int(W * zoom), int(H * zoom)), Image.LANCZOS)
        left = (frame.width - W) // 2
        top = (frame.height - H) // 2
        frame = frame.crop((left, top, left + W, top + H))
    return frame


# ── segment: logo (3–8 s) ───────────────────────────────────────────────────
LOGO_CARD_TOP = 540
LOGO_CARD_W = 1080
LOGO_CARD_H = 608


@lru_cache(maxsize=1)
def logo_card_glow() -> Image.Image:
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (-12, LOGO_CARD_TOP - 12, W + 11, LOGO_CARD_TOP + LOGO_CARD_H + 11),
        radius=46,
        fill=255,
    )
    glow = Image.new("RGBA", (W, H), with_alpha(BLUE, 0))
    glow.putalpha(mask.point(lambda value: int(value * 0.45)))
    return glow.filter(ImageFilter.GaussianBlur(64))


def logo_background(frame_rgb: np.ndarray) -> Image.Image:
    src = Image.fromarray(frame_rgb).convert("RGB")
    scale = max(W / src.width, H / src.height)
    big = src.resize((math.ceil(src.width * scale), math.ceil(src.height * scale)), Image.BILINEAR)
    left = (big.width - W) // 2
    top = (big.height - H) // 2
    big = big.crop((left, top, left + W, top + H))
    small = big.resize((W // 6, H // 6), Image.BILINEAR).filter(ImageFilter.GaussianBlur(9))
    big = small.resize((W, H), Image.BILINEAR)
    big = Image.blend(big, Image.new("RGB", (W, H), (4, 9, 20)), 0.86)
    return Image.alpha_composite(big.convert("RGBA"), Image.new("RGBA", (W, H), (12, 36, 72, 34)))


def render_logo_frame(frame_rgb: np.ndarray, local: float) -> Image.Image:
    frame = logo_background(frame_rgb)
    frame = Image.alpha_composite(frame, logo_card_glow())

    src = Image.fromarray(frame_rgb).convert("RGB")
    fg = src.resize((LOGO_CARD_W, LOGO_CARD_H), Image.LANCZOS)
    zoom = 1.0 + 0.045 * ease_in_out(clamp(local / 5.0))
    if zoom > 1.001:
        nw, nh = int(LOGO_CARD_W * zoom), int(LOGO_CARD_H * zoom)
        fg = fg.resize((nw, nh), Image.LANCZOS)
        left = (nw - LOGO_CARD_W) // 2
        top = (nh - LOGO_CARD_H) // 2
        fg = fg.crop((left, top, left + LOGO_CARD_W, top + LOGO_CARD_H))

    mask = Image.new("L", (LOGO_CARD_W, LOGO_CARD_H), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, LOGO_CARD_W - 1, LOGO_CARD_H - 1), radius=34, fill=255
    )
    fg = fg.convert("RGBA")
    fg.putalpha(mask)
    frame.alpha_composite(fg, (0, LOGO_CARD_TOP))
    ImageDraw.Draw(frame).rounded_rectangle(
        (0, LOGO_CARD_TOP, W - 1, LOGO_CARD_TOP + LOGO_CARD_H - 1),
        radius=34,
        outline=(90, 150, 230, 150),
        width=2,
    )

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    intro = ease_out(clamp((local - 0.1) / 0.5))
    if intro > 0:
        draw_centered(
            draw,
            "J.A.R.V.I.S. · БРЕНД-ІНТРО",
            font(FONT_TECH, 24),
            with_alpha(BLUE, int(220 * intro)),
            W / 2,
            410,
            tracking=6,
        )

    caption_in = ease_out(clamp((local - 0.55) / 0.5))
    if caption_in > 0:
        alpha = int(255 * caption_in)
        draw_centered(
            draw,
            "Твій AI-асистент для ПК",
            font(FONT_BOLD, 44),
            WHITE + (alpha,),
            W / 2,
            1215,
        )
        draw_centered(
            draw,
            "J.A.R.V.I.S. · v2.6.0",
            font(FONT_MONO, 26),
            with_alpha(DIM, alpha),
            W / 2,
            1292,
        )

    bar_y = 1378
    draw.rounded_rectangle((W / 2 - 180, bar_y, W / 2 + 180, bar_y + 4), radius=2, fill=(36, 64, 104, 200))
    filled = clamp(local / 5.0)
    if filled > 0:
        draw.rounded_rectangle(
            (W / 2 - 180, bar_y, W / 2 - 180 + 360 * filled, bar_y + 4),
            radius=2,
            fill=BLUE + (230,),
        )

    frame.alpha_composite(overlay)
    return frame


# ── segment: command deck (8–12 s) ──────────────────────────────────────────
def render_command(t: float) -> Image.Image:
    frame = base_frame(8 + t)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    appear = ease_out(clamp(t / 0.55))
    kicker(draw, "COMMAND DECK", W / 2, 185 - 16 * (1 - appear))
    headline(draw, "Один командний центр", W / 2, 232 - 16 * (1 - appear), size=78, max_width=940)

    zoom = 1.0 + 0.045 * ease_in_out(clamp(t / 4.0))
    window = screenshot_window(
        ASSETS / "screenshot-main.png",
        940,
        704,
        "J.A.R.V.I.S. / COMMAND DECK",
        zoom=zoom,
        focus=(0.55, 0.45),
    )
    y = 450 + 28 * (1 - appear)
    paste_with_glow(frame, window, (70, y), glow_alpha=70, glow_radius=38)

    caption_in = ease_out(clamp((t - 0.45) / 0.45))
    if caption_in > 0:
        draw_centered(
            draw,
            "Голос, чат, ПК і Roblox Studio — в одному вікні.",
            font(FONT_REG, 32),
            with_alpha(MUTED, int(255 * caption_in)),
            W / 2,
            1192,
        )

    chips = ["ГОЛОС", "ROBLOX STUDIO", "78 МОДЕЛЕЙ"]
    chip_font = font(FONT_TECH, 24)
    widths = [text_width(draw, text, chip_font, 3) + 40 for text in chips]
    total = sum(widths) + 14 * (len(chips) - 1)
    x = W / 2 - total / 2
    for index, (text, width) in enumerate(zip(chips, widths)):
        alpha = int(255 * clamp((t - 0.6 - index * 0.14) / 0.4))
        if alpha <= 0:
            continue
        draw.rounded_rectangle(
            (x, 1262, x + width, 1308),
            radius=23,
            fill=(12, 27, 52, int(alpha * 0.92)),
            outline=(45, 90, 150, alpha),
            width=1,
        )
        draw_centered(draw, text, chip_font, (160, 200, 245, alpha), x + width / 2, 1273, tracking=3)
        x += width + 14

    frame.alpha_composite(fade_layer(overlay, clamp(t / 0.35)))
    return frame


# ── segment: voice + models (12–15 s) ───────────────────────────────────────
def render_voice(t: float) -> Image.Image:
    frame = base_frame(12 + t)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    appear = ease_out(clamp(t / 0.5))
    kicker(draw, "ГОЛОС + МОДЕЛІ", W / 2, 220 - 16 * (1 - appear))
    headline(draw, "Скажи — і воно зробить", W / 2, 270 - 16 * (1 - appear), size=76, max_width=940)

    panel = (70, 500, 1010, 1000)
    rounded_panel(draw, panel, 28, (9, 21, 42, 245), (30, 56, 92, 255), 2)

    # mic with pulsing rings
    cx, cy = 190, 700
    for index in range(3):
        radius = 62 + index * 24 + 8 * math.sin(t * 4 + index)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=(70, 140, 240, 50 - index * 12), width=2)
    draw.ellipse((cx - 54, cy - 54, cx + 54, cy + 54), fill=(16, 42, 82, 255), outline=(60, 120, 210, 255), width=2)
    draw.rounded_rectangle((cx - 13, cy - 28, cx + 13, cy + 8), radius=13, fill=BLUE + (255,))
    draw.arc((cx - 24, cy - 12, cx + 24, cy + 34), 0, 180, fill=BLUE + (255,), width=4)
    draw.line((cx, cy + 34, cx, cy + 46), fill=BLUE + (255,), width=4)

    # waveform
    bars = 42
    start_x = 300
    bar_w = 7
    gap = 9
    base_y = 700
    for index in range(bars):
        envelope = math.sin(math.pi * index / (bars - 1)) ** 0.7
        wave = abs(math.sin(index * 0.42 + t * 7.5)) * 0.7 + 0.3
        height = 10 + 92 * envelope * wave
        color = lerp_color(BLUE, CYAN, index / (bars - 1))
        x = start_x + index * (bar_w + gap)
        draw.rounded_rectangle(
            (x, base_y - height / 2, x + bar_w, base_y + height / 2),
            radius=3,
            fill=with_alpha(color, 235),
        )

    # command typewriter
    command = "«Відкрий Roblox Studio»"
    typed = int(clamp((t - 0.55) / 1.0) * len(command))
    cmd_font = font(FONT_BOLD, 40)
    draw.text((110, 820), command[:typed], font=cmd_font, fill=WHITE + (255,))
    if typed < len(command) and int(t * 3) % 2 == 0:
        cursor_x = 110 + draw.textlength(command[:typed], font=cmd_font)
        draw.rectangle((cursor_x + 3, 824, cursor_x + 6, 872), fill=BLUE + (255,))

    if t > 1.75:
        response_alpha = int(255 * clamp((t - 1.75) / 0.35))
        draw.ellipse((112, 910, 126, 924), fill=GREEN + (response_alpha,))
        draw.text((140, 898), "JARVIS: Готово, сер.", font=font(FONT_REG, 34), fill=(160, 220, 200, response_alpha))

    # chips
    chips = ["78 моделей", "16 провайдерів", "авто-failover"]
    chip_font = font(FONT_TECH, 24)
    widths = [text_width(draw, text, chip_font, 2) + 40 for text in chips]
    total = sum(widths) + 14 * (len(chips) - 1)
    x = W / 2 - total / 2
    for index, (text, width) in enumerate(zip(chips, widths)):
        alpha = int(255 * clamp((t - 0.3 - index * 0.14) / 0.35))
        if alpha <= 0:
            continue
        draw.rounded_rectangle(
            (x, 1050, x + width, 1102),
            radius=26,
            fill=(16, 35, 64, int(alpha * 0.9)),
            outline=(45, 90, 150, alpha),
            width=1,
        )
        draw_centered(draw, text, chip_font, (160, 200, 245, alpha), x + width / 2, 1064, tracking=2)
        x += width + 14

    # model dropdown mock
    model_box = (70, 1140, 1010, 1240)
    draw.rounded_rectangle(model_box, radius=20, fill=(9, 21, 42, 245), outline=(38, 68, 110, 255), width=2)
    draw.text((100, 1160), "МОДЕЛЬ", font=font(FONT_MONO, 20), fill=DIM + (255,))
    draw.text((100, 1192), "Qwen 3.7 Flash", font=font(FONT_REG, 34), fill=WHITE + (255,))
    draw.polygon(((930, 1188), (950, 1188), (940, 1202)), fill=BLUE + (255,))
    draw.text((760, 1192), "78 доступно", font=font(FONT_TECH, 24), fill=CYAN + (255,))

    note_in = ease_out(clamp((t - 0.9) / 0.45))
    if note_in > 0:
        draw_centered(
            draw,
            "Провайдер випав? Автоматично перемикається на інший.",
            font(FONT_REG, 30),
            with_alpha(MUTED, int(235 * note_in)),
            W / 2,
            1278,
        )

    frame.alpha_composite(fade_layer(overlay, clamp(t / 0.3)))
    return frame


# ── segment: customization (15–18 s) ────────────────────────────────────────
def render_custom(t: float) -> Image.Image:
    frame = base_frame(15 + t)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    appear = ease_out(clamp(t / 0.5))
    kicker(draw, "КАСТОМІЗАЦІЯ", W / 2, 200 - 16 * (1 - appear))
    headline(draw, "Інтерфейс під себе", W / 2, 246 - 16 * (1 - appear), size=80, max_width=920)

    # crossfade from layout editor to code editor
    switch = clamp((t - 1.5) / 0.45)
    if switch < 1.0:
        window_a = screenshot_window(
            ASSETS / "screenshot-customize.png",
            940,
            660,
            "J.A.R.V.I.S. / КАСТОМІЗАЦІЯ · ТЕМА",
            zoom=1.0 + 0.03 * clamp(t / 3),
            focus=(0.45, 0.4),
        )
        paste_with_glow(frame, window_a, (70, 480), glow_alpha=55, glow_radius=34)
    if switch > 0.0:
        window_b = screenshot_window(
            ASSETS / "screenshot-customize-code.png",
            940,
            660,
            "J.A.R.V.I.S. / КАСТОМІЗАЦІЯ · КОД",
            zoom=1.0 + 0.03 * clamp(t / 3),
            focus=(0.45, 0.45),
        )
        window_b = fade_layer(window_b, switch)
        paste_with_glow(frame, window_b, (70, 480), glow_alpha=int(55 * switch), glow_radius=34)

    caption_font = font(FONT_REG, 32)
    caption_lines = wrap_text(
        draw,
        "Теми, шрифти, порядок блоків і власний код — без редагування файлів.",
        caption_font,
        900,
    )
    draw_lines_centered(draw, caption_lines, caption_font, MUTED + (255,), W / 2, 1180, 6)

    # small tab indicators, centred
    tabs = ["ТЕМА", "МАКЕТ", "КОД", "АНІМАЦІЇ", "JSON"]
    tab_font = font(FONT_TECH, 22)
    tab_widths = [text_width(draw, text, tab_font, 2) for text in tabs]
    total = sum(tab_widths) + 44 * (len(tabs) - 1)
    x = W / 2 - total / 2
    for index, (text, width) in enumerate(zip(tabs, tab_widths)):
        active = (index == 0 and switch < 0.5) or (index == 2 and switch >= 0.5)
        color = BLUE if active else DIM
        draw.text((x, 1310), text, font=tab_font, fill=color + (255,))
        if active:
            draw.rectangle((x, 1342, x + width, 1345), fill=BLUE + (255,))
        x += width + 44

    frame.alpha_composite(fade_layer(overlay, clamp(t / 0.3)))
    return frame


# ── segment: feature grid (18–20 s) ─────────────────────────────────────────
def draw_feature_icon(draw: ImageDraw.ImageDraw, kind: str, cx: float, cy: float, color: tuple) -> None:
    if kind == "memory":
        draw.rounded_rectangle((cx - 26, cy - 20, cx + 26, cy + 20), radius=6, outline=color, width=3)
        draw.rounded_rectangle((cx - 12, cy - 9, cx + 12, cy + 9), radius=3, outline=color, width=2)
        for offset in (-18, -6, 6, 18):
            draw.line((cx + offset, cy - 30, cx + offset, cy - 20), fill=color, width=3)
            draw.line((cx + offset, cy + 20, cx + offset, cy + 30), fill=color, width=3)
    elif kind == "clock":
        draw.ellipse((cx - 28, cy - 28, cx + 28, cy + 28), outline=color, width=3)
        draw.line((cx, cy, cx, cy - 17), fill=color, width=3)
        draw.line((cx, cy, cx + 13, cy + 8), fill=color, width=3)
    elif kind == "plug":
        draw.rounded_rectangle((cx - 16, cy - 20, cx + 16, cy + 16), radius=5, outline=color, width=3)
        draw.line((cx - 9, cy - 20, cx - 9, cy - 32), fill=color, width=3)
        draw.line((cx + 9, cy - 20, cx + 9, cy - 32), fill=color, width=3)
        draw.line((cx, cy + 16, cx, cy + 32), fill=color, width=3)
    elif kind == "roblox":
        draw.rounded_rectangle((cx - 28, cy - 28, cx + 28, cy + 28), radius=6, outline=color, width=3)
        draw.rectangle((cx - 8, cy - 8, cx + 8, cy + 8), fill=color)
    elif kind == "image":
        draw.rounded_rectangle((cx - 30, cy - 24, cx + 30, cy + 24), radius=5, outline=color, width=3)
        draw.ellipse((cx + 8, cy - 16, cx + 20, cy - 4), fill=color)
        draw.line(
            (
                cx - 24, cy + 18,
                cx - 8, cy - 2,
                cx + 4, cy + 10,
                cx + 14, cy - 2,
                cx + 24, cy + 8,
            ),
            fill=color,
            width=3,
            joint="curve",
        )


def render_features(t: float) -> Image.Image:
    frame = base_frame(18 + t)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    appear = ease_out(clamp(t / 0.45))
    kicker(draw, "ЩЕ ВСЕРЕДИНІ", W / 2, 210 - 14 * (1 - appear))
    headline(draw, "Не просто чат", W / 2, 258 - 14 * (1 - appear), size=82, max_width=920)

    cards = [
        ("memory", "Пам'ять", "пам'ятає факти", 70, 500),
        ("clock", "Автоматизації", "за розкладом", 550, 500),
        ("image", "Картинки", "генерація з OpenAI", 70, 830),
        ("roblox", "Roblox Studio", "MCP-контроль", 550, 830),
    ]
    for index, (kind, title, subtitle, x, y) in enumerate(cards):
        progress = clamp((t - 0.12 - index * 0.14) / 0.5)
        if progress <= 0:
            continue
        scale = 0.86 + 0.14 * ease_out(progress)
        card = Image.new("RGBA", (460, 300), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        rounded_panel(cd, (0, 0, 459, 299), 24, (10, 23, 46, 245), (32, 58, 96, 255), 2)
        draw_feature_icon(cd, kind, 70, 82, BLUE)
        cd.text((70, 140), title, font=font(FONT_BOLD, 42), fill=WHITE + (255,))
        cd.text((70, 200), subtitle, font=font(FONT_REG, 30), fill=MUTED + (255,))
        cd.line((70, 252, 390, 252), fill=(40, 70, 110, 255), width=1)
        cd.text((70, 266), "0" + str(index + 1), font=font(FONT_MONO, 18), fill=DIM + (255,))

        card = card.resize((int(460 * scale), int(300 * scale)), Image.LANCZOS)
        card = fade_layer(card, progress)
        px = int(x + (460 - card.width) / 2)
        py = int(y + (300 - card.height) / 2)
        frame.alpha_composite(card, (px, py))

    note_in = ease_out(clamp((t - 0.8) / 0.5))
    if note_in > 0:
        draw_centered(
            draw,
            "Пам'ять, автоматизації та картинки — все в одному місці.",
            font(FONT_REG, 32),
            with_alpha(MUTED, int(240 * note_in)),
            W / 2,
            1225,
        )

    frame.alpha_composite(fade_layer(overlay, clamp(t / 0.3)))
    return frame


# ── segment: stats (20–22 s) ────────────────────────────────────────────────
def render_stats(t: float) -> Image.Image:
    frame = base_frame(20 + t)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    kicker(draw, "ОДИН АСИСТЕНТ", W / 2, 300)
    rows = [
        ("78", "моделей", BLUE),
        ("16", "провайдерів", WHITE),
        ("1", "асистент", BLUE),
    ]
    y = 470
    for index, (number, label, color) in enumerate(rows):
        progress = clamp((t - 0.05 - index * 0.16) / 0.55)
        if progress <= 0:
            continue
        offset = 60 * (1 - ease_out(progress))
        alpha = int(255 * ease_out(progress))
        num_font = font(FONT_TECH, 210)
        label_font = font(FONT_REG, 46)
        draw.text((410, y + offset), number, font=num_font, fill=with_alpha(color, alpha), anchor="ra")
        draw.text((480, y + 78 + offset), label, font=label_font, fill=with_alpha(MUTED, alpha))
        if index < 2:
            draw.line((120, y + 310 + offset, W - 120, y + 310 + offset), fill=(35, 65, 105, alpha // 2), width=1)
        y += 340

    draw_centered(
        draw,
        "Без прив'язки до одного API.",
        font(FONT_REG, 36),
        MUTED + (255,),
        W / 2,
        1440,
    )

    frame.alpha_composite(fade_layer(overlay, clamp(t / 0.25)))
    return frame


# ── segment: end card (22–25 s) ─────────────────────────────────────────────
def render_end(t: float) -> Image.Image:
    frame = base_frame(22 + t)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # orbit rings
    for index, radius in enumerate((390, 470, 550)):
        alpha = 30 - index * 6
        draw_hex_mark(draw, W / 2, 650, radius, (60, 120, 210, alpha), 2, gap_edge=index % 6)

    mark_progress = clamp(t / 0.7)
    scale = 0.82 + 0.18 * ease_out(mark_progress)
    mark = mark_image(190, BLUE, glow=True)
    mark = mark.resize((int(mark.width * scale), int(mark.height * scale)), Image.LANCZOS)
    mark = fade_layer(mark, mark_progress)
    frame.alpha_composite(mark, (int(W / 2 - mark.width / 2), int(650 - mark.height / 2)))

    word_progress = clamp((t - 0.35) / 0.55)
    if word_progress > 0:
        word_font = font(FONT_TECH, 104)
        word = "J.A.R.V.I.S."
        width = text_width(draw, word, word_font, 10)
        alpha = int(255 * ease_out(word_progress))
        draw_tracked(draw, (W / 2 - width / 2, 920 + 20 * (1 - ease_out(word_progress))), word, word_font, WHITE + (alpha,), 10)

    if t > 0.65:
        alpha = int(255 * clamp((t - 0.65) / 0.4))
        draw_centered(draw, "Твій AI-асистент для ПК", font(FONT_REG, 40), with_alpha(MUTED, alpha), W / 2, 1060)

    if t > 0.85:
        alpha = int(255 * clamp((t - 0.85) / 0.4))
        box = (W / 2 - 190, 1150, W / 2 + 190, 1210)
        draw.rounded_rectangle(box, radius=30, fill=(16, 45, 90, int(alpha * 0.55)), outline=with_alpha(BLUE, alpha), width=2)
        draw_centered(draw, "ВЖЕ ДОСТУПНО", font(FONT_TECH, 26), with_alpha(CYAN, alpha), W / 2, 1167, tracking=4)

    if t > 1.0:
        alpha = int(255 * clamp((t - 1.0) / 0.4))
        draw_centered(
            draw,
            "nezerrucyk-alt.github.io/jarvis-ai-assistant",
            font(FONT_MONO, 26),
            with_alpha(BLUE, alpha),
            W / 2,
            1260,
        )

    if t > 1.2:
        alpha = int(210 * clamp((t - 1.2) / 0.4))
        draw_centered(
            draw,
            "Посилання — в описі",
            font(FONT_REG, 30),
            with_alpha(DIM, alpha),
            W / 2,
            1350,
        )

    # thin animated progress line at the very bottom
    progress = clamp(t / 3.0)
    draw.rectangle((70, 1500, 70 + (W - 140) * progress, 1503), fill=(40, 90, 160, 180))

    frame.alpha_composite(fade_layer(overlay, clamp(t / 0.25)))
    return frame


# ── transitions ─────────────────────────────────────────────────────────────
def apply_flash(frame: Image.Image, local: float, duration: float = 0.12) -> Image.Image:
    if local >= duration:
        return frame
    alpha = int(110 * (1 - local / duration))
    flash = Image.new("RGBA", (W, H), (150, 200, 255, alpha))
    return Image.alpha_composite(frame, flash)


# ── audio ───────────────────────────────────────────────────────────────────
def note_freq(note: str) -> float:
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    if note[-1].isdigit():
        octave = int(note[-1])
        name = note[:-1]
    else:
        octave = 4
        name = note
    return 440.0 * (2 ** ((names[name] + (octave - 4) * 12 - 9) / 12))


def synth_track(path: Path, duration: float = DURATION, sr: int = 44100) -> None:
    rng = np.random.default_rng(42)
    samples = int(duration * sr)
    mix = np.zeros((samples, 2), dtype=np.float32)
    t = np.arange(samples, dtype=np.float32) / sr

    def add(signal: np.ndarray, start: float, gain: float = 1.0, pan: float = 0.0) -> None:
        start_index = int(start * sr)
        end_index = min(samples, start_index + len(signal))
        if start_index >= samples:
            return
        chunk = signal[: end_index - start_index]
        left = gain * (1.0 - max(0.0, pan))
        right = gain * (1.0 + min(0.0, pan))
        mix[start_index:end_index, 0] += chunk * left
        mix[start_index:end_index, 1] += chunk * right

    def env_adsr(length: int, attack: float, decay: float, sustain: float, release: float) -> np.ndarray:
        a = int(attack * sr)
        d = int(decay * sr)
        r = int(release * sr)
        s = max(0, length - a - d - r)
        env = np.concatenate(
            [
                np.linspace(0, 1, max(1, a), dtype=np.float32),
                np.linspace(1, sustain, max(1, d), dtype=np.float32),
                np.full(max(1, s), sustain, dtype=np.float32),
                np.linspace(sustain, 0, max(1, r), dtype=np.float32),
            ]
        )
        return env[:length]

    def sine(freq: float, length: int) -> np.ndarray:
        tt = np.arange(length, dtype=np.float32) / sr
        return np.sin(2 * np.pi * freq * tt).astype(np.float32)

    def saw(freq: float, length: int) -> np.ndarray:
        tt = np.arange(length, dtype=np.float32) / sr
        value = 2.0 * (tt * freq - np.floor(0.5 + tt * freq))
        return value.astype(np.float32)

    # chord progression: Am, F, C, G (2 s each)
    chords = [
        ("A2", ["A2", "C3", "E3", "A3"]),
        ("F2", ["F2", "A2", "C3", "F3"]),
        ("C3", ["C3", "E3", "G3", "C4"]),
        ("G2", ["G2", "B2", "D3", "G3"]),
    ]
    bar = 2.0
    bars = int(math.ceil(duration / bar))
    for bar_index in range(bars):
        root, notes = chords[bar_index % 4]
        start = bar_index * bar

        # pad
        length = int(bar * sr)
        pad = np.zeros(length, dtype=np.float32)
        for note in notes:
            pad += sine(note_freq(note) * 0.5, length) * 0.5
            pad += saw(note_freq(note) * 0.5, length) * 0.08
        pad *= env_adsr(length, 0.35, 0.4, 0.55, 0.5)
        add(pad, start, gain=0.055, pan=-0.15)

        # bass
        bass = sine(note_freq(root) / 2, length) * 0.8 + sine(note_freq(root), length) * 0.2
        bass *= env_adsr(length, 0.01, 0.12, 0.5, 0.3)
        add(bass, start, gain=0.16)

        # arpeggio 8ths
        pattern = [notes[0], notes[2], notes[1], notes[3], notes[2], notes[1], notes[3], notes[2]]
        for step, note in enumerate(pattern):
            step_len = int(0.25 * sr)
            tone = sine(note_freq(note) * 2, step_len) * 0.7 + saw(note_freq(note) * 2, step_len) * 0.15
            tone *= env_adsr(step_len, 0.005, 0.08, 0.15, 0.12)
            add(tone, start + step * 0.25, gain=0.06, pan=0.25 if step % 2 else -0.25)

    # drums from 3 s to 22 s
    beat = 0.5
    for index in range(int(22.0 / beat)):
        start = index * beat
        if start < 3.0 or start >= 22.0:
            continue
        # kick
        length = int(0.22 * sr)
        tt = np.arange(length, dtype=np.float32) / sr
        freq = 130 * np.exp(-tt * 18) + 42
        kick = np.sin(2 * np.pi * np.cumsum(freq) / sr).astype(np.float32)
        kick *= np.exp(-tt * 14)
        add(kick, start, gain=0.34)
        # clap on 2 and 4
        if index % 4 in (1, 3):
            length = int(0.16 * sr)
            noise = rng.normal(0, 1, length).astype(np.float32)
            noise = np.diff(noise, prepend=0) * 0.5
            noise *= np.exp(-np.arange(length) / (0.03 * sr))
            add(noise, start, gain=0.12, pan=0.05)
        # hi-hat on offbeat
        if index % 2 == 1:
            length = int(0.06 * sr)
            noise = rng.normal(0, 1, length).astype(np.float32)
            noise = np.diff(noise, prepend=0)
            noise *= np.exp(-np.arange(length) / (0.012 * sr))
            add(noise, start, gain=0.06, pan=-0.2)

    # riser into the stats section
    riser_start = 21.2
    riser_len = int(0.8 * sr)
    noise = rng.normal(0, 1, riser_len).astype(np.float32)
    noise = np.diff(noise, prepend=0)
    ramp = np.linspace(0, 1, riser_len, dtype=np.float32) ** 2
    add(noise * ramp, riser_start, gain=0.10)

    # impact at 22.0
    impact_len = int(1.2 * sr)
    tt = np.arange(impact_len, dtype=np.float32) / sr
    impact = np.sin(2 * np.pi * (70 * np.exp(-tt * 5) + 35) * tt) * np.exp(-tt * 3)
    add(impact.astype(np.float32), 22.0, gain=0.22)

    # final shimmer
    shimmer_len = int(2.8 * sr)
    shimmer = np.zeros(shimmer_len, dtype=np.float32)
    for note in ["A4", "C5", "E5", "A5"]:
        shimmer += sine(note_freq(note), shimmer_len) * 0.25
    shimmer *= env_adsr(shimmer_len, 0.5, 0.4, 0.5, 1.2)
    add(shimmer, 22.0, gain=0.045, pan=0.1)

    # global fades
    fade_in = int(0.4 * sr)
    fade_out = int(1.8 * sr)
    mix[:fade_in] *= np.linspace(0, 1, fade_in, dtype=np.float32)[:, None]
    mix[-fade_out:] *= np.linspace(1, 0, fade_out, dtype=np.float32)[:, None]

    peak = float(np.max(np.abs(mix))) or 1.0
    mix = mix / peak * 0.88
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sr)
        handle.writeframes(pcm.tobytes())


# ── main render ─────────────────────────────────────────────────────────────
def frame_at(time_seconds: float) -> Image.Image:
    t = clamp(time_seconds, 0, DURATION - 1e-4)
    if t < 3.0:
        return apply_flash(render_hook(t), t)
    if t < 8.0:
        local = t - 3.0
        frame_index = int(local * FPS)
        rgb = iio.imread(LOGO_VIDEO, index=frame_index)
        return apply_flash(render_logo_frame(rgb, local), local)
    if t < 12.0:
        return apply_flash(render_command(t - 8.0), t - 8.0)
    if t < 15.0:
        return apply_flash(render_voice(t - 12.0), t - 12.0)
    if t < 18.0:
        return apply_flash(render_custom(t - 15.0), t - 15.0)
    if t < 20.0:
        return apply_flash(render_features(t - 18.0), t - 18.0)
    if t < 22.0:
        return apply_flash(render_stats(t - 20.0), t - 20.0)
    return apply_flash(render_end(t - 22.0), t - 22.0)


def render_previews() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for seconds in (1.5, 5.5, 9.5, 13.8, 16.6, 19.2, 21.2, 24.2):
        frame = frame_at(seconds).convert("RGB")
        path = OUT_DIR / f"preview-{seconds:04.1f}.png"
        frame.save(path)
        print("preview", path)


def render_video() -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    video_path = OUT_DIR / "tiktok-01-intro.mp4"
    audio_path = OUT_DIR / "tiktok-01-audio.wav"
    final_path = OUT_DIR / "tiktok-01-intro-final.mp4"

    print("synth audio…")
    synth_track(audio_path)
    print("render video…")

    logo_frames = iio.imiter(LOGO_VIDEO)
    logo_start = int(3.0 * FPS)
    logo_end = int(8.0 * FPS)
    writer = imageio.get_writer(
        video_path,
        fps=FPS,
        codec="libx264",
        quality=8,
        pixelformat="yuv420p",
        macro_block_size=1,
        output_params=["-crf", "20", "-preset", "medium", "-movflags", "+faststart"],
    )
    try:
        for index in range(TOTAL_FRAMES):
            t = index / FPS
            if logo_start <= index < logo_end:
                rgb = next(logo_frames)
                frame = render_logo_frame(rgb, t - 3.0)
                frame = apply_flash(frame, t - 3.0)
            else:
                frame = frame_at(t)
            writer.append_data(np.asarray(frame.convert("RGB")))
            if index % 75 == 0:
                print(f"  {index}/{TOTAL_FRAMES} ({t:.1f}s)")
    finally:
        writer.close()

    # mux audio with the ffmpeg binary shipped by imageio-ffmpeg
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(final_path),
    ]
    import subprocess

    subprocess.run(command, check=True)
    print("video", final_path)
    return final_path


def render_cover() -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame = frame_at(2.65).convert("RGB")
    path = OUT_DIR / "tiktok-01-cover.png"
    frame.save(path)
    print("cover", path)
    endcard = frame_at(24.4).convert("RGB")
    endcard_path = OUT_DIR / "tiktok-01-endcard.png"
    endcard.save(endcard_path)
    print("endcard", endcard_path)
    return path


if __name__ == "__main__":
    if "--preview" in sys.argv:
        render_previews()
    elif "--cover" in sys.argv:
        render_cover()
    else:
        render_video()
        render_cover()
