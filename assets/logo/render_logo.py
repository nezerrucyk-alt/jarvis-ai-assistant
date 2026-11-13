#!/usr/bin/env python3
"""Render a 5 second, 3D cartoon-style JARVIS logo animation.

Everything is drawn procedurally with Pillow so the result is deterministic
and can be re-rendered without any external 3D package.
"""
from __future__ import annotations

import argparse
import math
import random
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
FONT_PATH = ROOT / "fonts" / "TitanOne-Regular.ttf"

W, H = 1920, 1080
FPS = 30
DURATION = 5.0
NFRAMES = int(round(FPS * DURATION))

FINAL_FONT_SIZE = 340
FONT_SIZE = 900
SPRITE_SCALE = FINAL_FONT_SIZE / FONT_SIZE
TRACKING_FINAL = 22.0
TRACKING = TRACKING_FINAL / SPRITE_SCALE

WORD = "JARVIS"
LETTER_START = 0.18
LETTER_STAGGER = 0.145
POP_DURATION = 0.74

NAVY = (7, 20, 46)
BLUE = (47, 125, 255)
CYAN = (34, 211, 238)

BRAND_LETTERS = [
    (47, 125, 255),
    (43, 139, 255),
    (38, 158, 255),
    (32, 179, 249),
    (29, 199, 244),
    (34, 211, 238),
]

CONFETTI_COLORS = [
    (47, 125, 255),
    (34, 211, 238),
    (125, 211, 252),
    (167, 139, 250),
    (244, 114, 182),
    (251, 191, 36),
    (52, 211, 153),
    (255, 255, 255),
]


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else hi if v > hi else v


def mix(a, b, t: float):
    t = clamp(t)
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def lighten(c, t: float):
    return mix(c, (255, 255, 255), t)


def darken(c, t: float):
    return mix(c, (0, 0, 0), t)


def smoothstep(t: float) -> float:
    t = clamp(t)
    return t * t * (3.0 - 2.0 * t)


def ease_out_cubic(t: float) -> float:
    t = clamp(t)
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_back(t: float, c1: float = 2.3) -> float:
    t = clamp(t)
    c3 = c1 + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


def rgba(c, a: int = 255):
    return (int(c[0]), int(c[1]), int(c[2]), int(a))


def gradient_image(size, stops, y0: float, y1: float) -> Image.Image:
    """Vertical multi-stop gradient mapped from y0 to y1."""
    w, h = size
    ys = np.arange(h, dtype=np.float32)
    t = np.clip((ys - y0) / max(1.0, (y1 - y0)), 0.0, 1.0)
    out = np.zeros((h, 3), dtype=np.float32)
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        m = (t >= p0) & (t <= p1)
        if not np.any(m):
            continue
        local = (t[m] - p0) / max(1e-6, (p1 - p0))
        for ch in range(3):
            out[m, ch] = c0[ch] + (c1[ch] - c0[ch]) * local
    out = np.repeat(out[:, None, :], w, axis=1)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def radial_alpha(size, center, radii, power: float = 2.0) -> Image.Image:
    w, h = size
    cx, cy = center
    rx, ry = radii
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - cx) / max(1.0, rx)) ** 2 + ((yy - cy) / max(1.0, ry)) ** 2)
    a = np.clip(1.0 - d, 0.0, 1.0) ** power
    return Image.fromarray((a * 255).astype(np.uint8), "L")


# ---------------------------------------------------------------------------
# background
# ---------------------------------------------------------------------------

def build_background() -> Image.Image:
    bw, bh = 2400, 1500
    # soft pastel four-corner gradient
    corners = np.array(
        [
            [244, 239, 255],  # top-left lavender
            [226, 243, 255],  # top-right baby blue
            [255, 233, 245],  # bottom-left pink
            [226, 252, 246],  # bottom-right mint
        ],
        dtype=np.float32,
    )
    yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
    tx = (xx / (bw - 1))[:, :, None]
    ty = (yy / (bh - 1))[:, :, None]
    top = corners[0] * (1 - tx) + corners[1] * tx
    bottom = corners[2] * (1 - tx) + corners[3] * tx
    arr = top * (1 - ty) + bottom * ty

    # very subtle grain so the gradient does not band after encoding
    rng = np.random.default_rng(7)
    arr += rng.normal(0.0, 2.1, (bh, bw, 1)).astype(np.float32)

    bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    blobs = [
        ((300, 280), (500, 410), (188, 160, 255), 108),
        ((2080, 230), (590, 440), (140, 198, 255), 112),
        ((1870, 1240), (590, 460), (255, 158, 208), 84),
        ((400, 1260), (520, 420), (150, 242, 214), 78),
        ((1170, 100), (460, 320), (255, 236, 178), 72),
        ((1210, 810), (560, 390), (204, 229, 255), 58),
    ]
    blob_layer = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blob_layer)
    for (cx, cy), (rx, ry), col, alpha in blobs:
        bd.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=rgba(col, alpha))
    blob_layer = blob_layer.filter(ImageFilter.GaussianBlur(132))
    bg.alpha_composite(blob_layer)

    # gentle vignette
    vig = radial_alpha((bw, bh), (bw / 2, bh / 2), (bw * 0.70, bh * 0.70), 2.6)
    dark = Image.new("RGBA", (bw, bh), (20, 35, 80, 0))
    dark.putalpha(vig.point(lambda v: int((255 - v) * 0.07)))
    bg.alpha_composite(dark)
    return bg


def background_frame(master: Image.Image, zoom: float, ox: float, oy: float) -> Image.Image:
    mw, mh = master.size
    cw = int(round(W / zoom))
    ch = int(round(H / zoom))
    cx = int(round(mw / 2 + ox))
    cy = int(round(mh / 2 + oy))
    x0 = max(0, min(mw - cw, cx - cw // 2))
    y0 = max(0, min(mh - ch, cy - ch // 2))
    crop = master.crop((x0, y0, x0 + cw, y0 + ch))
    return crop.resize((W, H), Image.LANCZOS)


# ---------------------------------------------------------------------------
# letter sprites
# ---------------------------------------------------------------------------

@dataclass
class LetterSprite:
    ch: str
    image: Image.Image
    shadow: Image.Image
    anchor_x: float
    anchor_y: float
    center_x: float
    baseline_y: float
    width: float


def make_shadow(mask: Image.Image, blur: float = 18.0, alpha: float = 0.52) -> Image.Image:
    sh = Image.new("RGBA", mask.size, (8, 18, 44, 0))
    m = mask.filter(ImageFilter.GaussianBlur(blur))
    sh.putalpha(m.point(lambda v: int(v * alpha)))
    return sh


def make_letter_sprite(ch: str, font: ImageFont.FreeTypeFont, base, outline_w: int = 20,
                       depth_x: int = 22, depth_y: int = 52) -> LetterSprite:
    adv = font.getlength(ch)
    left, top, right, bottom = font.getbbox(ch, anchor="ls")
    pad = 150
    w = int(math.ceil(pad + adv + pad + depth_x + outline_w * 2))
    baseline = pad - top
    h = int(math.ceil(baseline + bottom + pad + depth_y + outline_w * 2))
    ax = pad + adv / 2.0
    ay = baseline

    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.text((pad, baseline), ch, font=font, fill=255, anchor="ls")

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # far silhouette / outline of the extrusion
    d.text((pad + depth_x, baseline + depth_y), ch, font=font,
           fill=rgba(NAVY), anchor="ls", stroke_width=outline_w, stroke_fill=rgba(NAVY))

    # side wall, far to near
    far = darken(base, 0.72)
    near = darken(base, 0.48)
    steps = 52
    for i in range(steps, 0, -1):
        f = i / steps
        ox = depth_x * f
        oy = depth_y * f
        col = mix(far, near, f)
        d.text((pad + ox, baseline + oy), ch, font=font, fill=rgba(col), anchor="ls")

    # front outline
    d.text((pad, baseline), ch, font=font, fill=rgba(NAVY), anchor="ls",
           stroke_width=outline_w, stroke_fill=rgba(NAVY))

    ink_top = baseline + top
    ink_bottom = baseline + bottom
    ink_h = max(1.0, ink_bottom - ink_top)
    stops = [
        (0.00, lighten(base, 0.34)),
        (0.18, lighten(base, 0.16)),
        (0.42, base),
        (0.76, darken(base, 0.16)),
        (1.00, darken(base, 0.40)),
    ]
    grad = gradient_image((w, h), stops, ink_top, ink_bottom)

    front = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    front.paste(grad, (0, 0), mask)

    # broad soft gloss across the upper-left of the letter
    gloss = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(gloss)
    gcx = pad + adv * 0.36
    gcy = ink_top + ink_h * 0.17
    grx = max(10.0, adv * 0.56)
    gry = max(8.0, ink_h * 0.21)
    gd.ellipse((gcx - grx, gcy - gry, gcx + grx, gcy + gry), fill=255)
    gloss = gloss.filter(ImageFilter.GaussianBlur(26))
    gloss = ImageChops.multiply(gloss, mask)
    white = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    white.putalpha(gloss.point(lambda v: int(v * 0.42)))
    front.alpha_composite(white)

    # tight specular spot
    spec = Image.new("L", (w, h), 0)
    sd = ImageDraw.Draw(spec)
    scx = pad + adv * 0.25
    scy = ink_top + ink_h * 0.12
    srx = max(6.0, adv * 0.10)
    sry = max(4.0, ink_h * 0.045)
    sd.ellipse((scx - srx, scy - sry, scx + srx, scy + sry), fill=255)
    spec = spec.filter(ImageFilter.GaussianBlur(7))
    spec = ImageChops.multiply(spec, mask)
    spec_white = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    spec_white.putalpha(spec.point(lambda v: int(v * 0.85)))
    front.alpha_composite(spec_white)

    # cool bounce light near the bottom
    bounce = Image.new("L", (w, h), 0)
    bd = ImageDraw.Draw(bounce)
    bcx = pad + adv * 0.52
    bcy = ink_bottom - ink_h * 0.10
    brx = max(8.0, adv * 0.34)
    bry = max(4.0, ink_h * 0.09)
    bd.ellipse((bcx - brx, bcy - bry, bcx + brx, bcy + bry), fill=255)
    bounce = bounce.filter(ImageFilter.GaussianBlur(18))
    bounce = ImageChops.multiply(bounce, mask)
    bounce_col = Image.new("RGBA", (w, h), rgba(lighten(base, 0.45), 0))
    bounce_col.putalpha(bounce.point(lambda v: int(v * 0.42)))
    front.alpha_composite(bounce_col)

    # inner rim light along top-left edge
    eroded = mask.filter(ImageFilter.MinFilter(13))
    edge = ImageChops.subtract(mask, eroded)
    rim_mask = ImageChops.offset(edge, -4, -6)
    rim_mask = ImageChops.multiply(rim_mask, mask).filter(ImageFilter.GaussianBlur(1.4))
    rim = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    rim.putalpha(rim_mask.point(lambda v: int(v * 0.55)))
    front.alpha_composite(rim)

    # inner shadow along bottom-right edge
    shade_mask = ImageChops.offset(edge, 4, 6)
    shade_mask = ImageChops.multiply(shade_mask, mask).filter(ImageFilter.GaussianBlur(2.0))
    shade = Image.new("RGBA", (w, h), (5, 14, 36, 0))
    shade.putalpha(shade_mask.point(lambda v: int(v * 0.55)))
    front.alpha_composite(shade)

    layer.alpha_composite(front)
    shadow = make_shadow(mask)

    return LetterSprite(
        ch=ch,
        image=layer,
        shadow=shadow,
        anchor_x=ax,
        anchor_y=ay,
        center_x=0.0,
        baseline_y=0.0,
        width=adv * SPRITE_SCALE,
    )


def build_letters() -> list[LetterSprite]:
    font = ImageFont.truetype(str(FONT_PATH), FONT_SIZE)
    sprites = [make_letter_sprite(ch, font, BRAND_LETTERS[i]) for i, ch in enumerate(WORD)]

    advances = [font.getlength(ch) * SPRITE_SCALE for ch in WORD]
    total = sum(advances) + TRACKING_FINAL * (len(WORD) - 1)
    pen = W / 2.0 - total / 2.0

    # vertical placement: centre the ink box of the whole word
    _, top, _, bottom = font.getbbox(WORD, anchor="ls")
    ink_top = top * SPRITE_SCALE
    ink_bottom = bottom * SPRITE_SCALE
    baseline = H / 2.0 - (ink_top + ink_bottom) / 2.0

    for sp, adv in zip(sprites, advances):
        sp.center_x = pen + adv / 2.0
        sp.baseline_y = baseline
        pen += adv + TRACKING_FINAL
    return sprites


# ---------------------------------------------------------------------------
# animation state
# ---------------------------------------------------------------------------

@dataclass
class LetterState:
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation: float = 0.0
    offset_y: float = 0.0
    alpha: float = 1.0


def letter_state(t: float, i: int) -> LetterState:
    start = LETTER_START + i * LETTER_STAGGER
    p = clamp((t - start) / POP_DURATION)
    if p <= 0.0:
        return LetterState(scale_x=0.0, scale_y=0.0, alpha=0.0)

    s = ease_out_back(p, 2.15)
    stretch = 0.20 * math.sin(math.pi * p) * (1.0 - p)
    squash = 0.10 * math.exp(-((p - 0.80) / 0.075) ** 2)
    sx = s * (1.0 - 0.55 * stretch) * (1.0 + squash)
    sy = s * (1.0 + stretch) * (1.0 - squash * 0.85)

    # a small entrance tilt that unwinds as the letter lands
    start_rot = (-9.0 if i % 2 == 0 else 9.0)
    rot = start_rot * (1.0 - ease_out_back(p, 1.6))

    # playful wave once the word is complete
    env = smoothstep((t - 1.62) / 0.22) * (1.0 - smoothstep((t - 2.62) / 0.48))
    if env > 0.0:
        phase = 2.0 * math.pi * 2.35 * (t - 1.62) - i * 0.62
        rot += 4.8 * env * math.sin(phase)
        sy += 0.045 * env * math.sin(phase + math.pi / 2.0)
        sx -= 0.030 * env * math.sin(phase + math.pi / 2.0)

    y = -34.0 * (1.0 - ease_out_cubic(p))
    if env > 0.0:
        y += 7.0 * env * math.sin(phase + math.pi / 2.0)

    alpha = clamp(p * 4.0)
    return LetterState(scale_x=sx, scale_y=sy, rotation=rot, offset_y=y, alpha=alpha)


@dataclass
class CameraState:
    scale: float
    rotation: float
    ox: float
    oy: float


CAMERA_KEYS = [
    (0.0, 0.920, -1.30, 0.0, 18.0),
    (1.2, 0.955, -0.55, 0.0, 10.0),
    (2.4, 0.982, 0.30, 0.0, 4.0),
    (3.6, 0.996, 0.08, 0.0, 0.0),
    (4.3, 1.000, 0.00, 0.0, 0.0),
]


def camera_at(t: float) -> CameraState:
    t = min(t, 4.3)
    for i in range(len(CAMERA_KEYS) - 1):
        t0, s0, r0, x0, y0 = CAMERA_KEYS[i]
        t1, s1, r1, x1, y1 = CAMERA_KEYS[i + 1]
        if t <= t1:
            f = smoothstep((t - t0) / max(1e-6, (t1 - t0)))
            return CameraState(
                s0 + (s1 - s0) * f,
                r0 + (r1 - r0) * f,
                x0 + (x1 - x0) * f,
                y0 + (y1 - y0) * f,
            )
    _, s, r, x, y = CAMERA_KEYS[-1]
    return CameraState(s, r, x, y)


def camera_point(x: float, y: float, cam: CameraState):
    dx = x - W / 2.0
    dy = y - H / 2.0
    ang = math.radians(cam.rotation)
    cos_a = math.cos(ang)
    sin_a = math.sin(ang)
    rx = dx * cos_a + dy * sin_a
    ry = -dx * sin_a + dy * cos_a
    return W / 2.0 + rx * cam.scale + cam.ox, H / 2.0 + ry * cam.scale + cam.oy


def transformed_sprite(sprite: Image.Image, ax: float, ay: float, sx: float, sy: float,
                       angle: float, alpha: float):
    sw = max(1, int(round(sprite.width * sx)))
    sh = max(1, int(round(sprite.height * sy)))
    img = sprite.resize((sw, sh), Image.LANCZOS)
    if alpha < 0.999:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))

    nax = ax * sx
    nay = ay * sy
    if abs(angle) > 0.01:
        img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
        w0, h0 = sw, sh
        w1, h1 = img.size
        cx0, cy0 = w0 / 2.0, h0 / 2.0
        dx = nax - cx0
        dy = nay - cy0
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        nax = w1 / 2.0 + dx * cos_a + dy * sin_a
        nay = h1 / 2.0 - dx * sin_a + dy * cos_a
    return img, nax, nay


# ---------------------------------------------------------------------------
# effects
# ---------------------------------------------------------------------------

@dataclass
class Sparkle:
    t0: float
    x: float
    y: float
    r: float
    color: tuple
    life: float
    rot: float
    spin: float
    drift_x: float
    drift_y: float


@dataclass
class Confetto:
    t0: float
    x: float
    y: float
    vx: float
    vy: float
    size: float
    color: tuple
    shape: int
    rot: float
    spin: float
    life: float
    gravity: float


def make_star_sprite(color, r: int = 72) -> Image.Image:
    size = r * 2 + 28
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = size / 2.0
    pts = []
    for i in range(8):
        ang = -math.pi / 2 + i * math.pi / 4
        rr = r if i % 2 == 0 else r * 0.16
        pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    d.polygon(pts, fill=rgba(color, 255))
    glow = img.filter(ImageFilter.GaussianBlur(10))
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.alpha_composite(glow)
    out.alpha_composite(glow)
    core = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cd = ImageDraw.Draw(core)
    cd.polygon(pts, fill=(255, 255, 255, 235))
    cd.ellipse((cx - r * 0.12, cy - r * 0.12, cx + r * 0.12, cy + r * 0.12),
               fill=(255, 255, 255, 255))
    out.alpha_composite(core)
    return out


def build_effects(letters: list[LetterSprite]):
    rng = random.Random(20261112)
    sparkles: list[Sparkle] = []
    confetti: list[Confetto] = []

    for i, sp in enumerate(letters):
        start = LETTER_START + i * LETTER_STAGGER
        for _ in range(4):
            ang = rng.uniform(-math.pi, math.pi)
            dist = rng.uniform(70, 165)
            sparkles.append(Sparkle(
                t0=start + rng.uniform(0.18, 0.40),
                x=sp.center_x + math.cos(ang) * dist,
                y=sp.baseline_y - 120 + math.sin(ang) * dist * 0.65,
                r=rng.uniform(9, 19),
                color=rng.choice([(255, 255, 255), CYAN, (125, 211, 252), (255, 255, 255), (196, 181, 253)]),
                life=rng.uniform(0.45, 0.85),
                rot=rng.uniform(0, 360),
                spin=rng.uniform(-160, 160),
                drift_x=rng.uniform(-16, 16),
                drift_y=rng.uniform(-24, -4),
            ))
        # confetti pop from each letter
        for _ in range(9):
            ang = rng.uniform(-math.pi * 0.92, -math.pi * 0.08)
            speed = rng.uniform(250, 620)
            confetti.append(Confetto(
                t0=start + rng.uniform(0.12, 0.26),
                x=sp.center_x + rng.uniform(-35, 35),
                y=sp.baseline_y - 100 + rng.uniform(-45, 35),
                vx=math.cos(ang) * speed,
                vy=math.sin(ang) * speed,
                size=rng.uniform(7, 15),
                color=rng.choice(CONFETTI_COLORS),
                shape=rng.randrange(3),
                rot=rng.uniform(0, 360),
                spin=rng.uniform(-540, 540),
                life=rng.uniform(1.0, 1.7),
                gravity=rng.uniform(620, 980),
            ))

    # final burst when the word is complete
    for _ in range(46):
        ang = rng.uniform(0, math.pi * 2)
        speed = rng.uniform(260, 760)
        confetti.append(Confetto(
            t0=1.42 + rng.uniform(0.0, 0.10),
            x=W / 2 + rng.uniform(-240, 240),
            y=H / 2 - 40 + rng.uniform(-60, 70),
            vx=math.cos(ang) * speed,
            vy=math.sin(ang) * speed - 130,
            size=rng.uniform(6, 14),
            color=rng.choice(CONFETTI_COLORS),
            shape=rng.randrange(3),
            rot=rng.uniform(0, 360),
            spin=rng.uniform(-620, 620),
            life=rng.uniform(1.1, 1.9),
            gravity=rng.uniform(620, 980),
        ))

    # ambient sparkles around the lockup
    for _ in range(14):
        t0 = rng.uniform(0.9, 3.5)
        sparkles.append(Sparkle(
            t0=t0,
            x=rng.uniform(300, W - 300),
            y=rng.uniform(260, H - 210),
            r=rng.uniform(5, 12),
            color=rng.choice([(255, 255, 255), CYAN, (147, 197, 253), (233, 213, 255)]),
            life=rng.uniform(0.5, 1.0),
            rot=rng.uniform(0, 360),
            spin=rng.uniform(-120, 120),
            drift_x=rng.uniform(-10, 10),
            drift_y=rng.uniform(-18, -3),
        ))
    return sparkles, confetti


STAR_SPRITES = {
    (255, 255, 255): make_star_sprite((255, 255, 255)),
    CYAN: make_star_sprite(CYAN),
    (125, 211, 252): make_star_sprite((125, 211, 252)),
    (196, 181, 253): make_star_sprite((196, 181, 253)),
}


def draw_sparkles(frame: Image.Image, sparkles: list[Sparkle], t: float):
    for s in sparkles:
        age = t - s.t0
        if age < 0 or age > s.life:
            continue
        f = age / s.life
        grow = ease_out_back(clamp(age / 0.22), 1.7)
        fade = 1.0 - smoothstep((f - 0.55) / 0.45)
        alpha = clamp(grow * fade)
        if alpha <= 0.01:
            continue
        r = max(2, int(round(s.r * (0.55 + 0.65 * grow))))
        sprite = STAR_SPRITES.get(s.color, STAR_SPRITES[(255, 255, 255)])
        img = sprite.resize((r * 2 + 12, r * 2 + 12), Image.LANCZOS)
        img = img.rotate(s.rot + s.spin * age, resample=Image.BICUBIC, expand=True)
        if alpha < 0.999:
            img = img.copy()
            img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
        x = s.x + s.drift_x * age
        y = s.y + s.drift_y * age
        frame.alpha_composite(img, (int(round(x - img.width / 2)), int(round(y - img.height / 2))))


def draw_confetti(frame: Image.Image, confetti: list[Confetto], t: float):
    for c in confetti:
        age = t - c.t0
        if age < 0 or age > c.life:
            continue
        f = age / c.life
        fade = 1.0 - smoothstep((f - 0.62) / 0.38)
        alpha = int(255 * clamp(fade))
        if alpha <= 3:
            continue
        x = c.x + c.vx * age
        y = c.y + c.vy * age + 0.5 * c.gravity * age * age
        ang = math.radians(c.rot + c.spin * age)
        s = c.size
        if c.shape == 0:  # circle
            d = ImageDraw.Draw(frame)
            d.ellipse((x - s / 2, y - s / 2, x + s / 2, y + s / 2), fill=rgba(c.color, alpha))
        elif c.shape == 1:  # strip
            ca, sa = math.cos(ang), math.sin(ang)
            hw, hh = s * 0.32, s * 0.95
            pts = [
                (x + (-hw * ca - -hh * sa), y + (-hw * sa + -hh * ca)),
                (x + (hw * ca - -hh * sa), y + (hw * sa + -hh * ca)),
                (x + (hw * ca - hh * sa), y + (hw * sa + hh * ca)),
                (x + (-hw * ca - hh * sa), y + (-hw * sa + hh * ca)),
            ]
            ImageDraw.Draw(frame).polygon(pts, fill=rgba(c.color, alpha))
        else:  # rounded square
            ca, sa = math.cos(ang), math.sin(ang)
            hw = hh = s * 0.55
            pts = [
                (x + (-hw * ca - -hh * sa), y + (-hw * sa + -hh * ca)),
                (x + (hw * ca - -hh * sa), y + (hw * sa + -hh * ca)),
                (x + (hw * ca - hh * sa), y + (hw * sa + hh * ca)),
                (x + (-hw * ca - hh * sa), y + (-hw * sa + hh * ca)),
            ]
            ImageDraw.Draw(frame).polygon(pts, fill=rgba(c.color, alpha))


# ---------------------------------------------------------------------------
# frame composition
# ---------------------------------------------------------------------------

def build_glow() -> Image.Image:
    size = 1100
    a = radial_alpha((size, size), (size / 2, size / 2), (size * 0.5, size * 0.5), 2.4)
    glow = Image.new("RGBA", (size, size), (235, 248, 255, 0))
    glow.putalpha(a.point(lambda v: int(v * 0.42)))
    return glow


def build_floor_shadow() -> Image.Image:
    # generous transparent margin so the blur cannot be clipped into a box
    w, h = 1800, 520
    img = Image.new("RGBA", (w, h), (18, 36, 80, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((250, 150, w - 250, h - 150), fill=(18, 36, 80, 255))
    img = img.filter(ImageFilter.GaussianBlur(62))
    img.putalpha(img.getchannel("A").point(lambda v: int(v * 0.26)))
    return img


def compose_frame(t: float, bg_master: Image.Image, letters: list[LetterSprite],
                  sparkles: list[Sparkle], confetti: list[Confetto],
                  glow: Image.Image, floor_shadow: Image.Image) -> Image.Image:
    cam = camera_at(t)
    bg_zoom = 1.0 + (cam.scale - 1.0) * 0.55
    frame = background_frame(bg_master, bg_zoom, -cam.ox * 0.55, -cam.oy * 0.55).convert("RGBA")

    # soft halo behind the lockup
    pulse = 0.0
    for i in range(len(letters)):
        st = letter_state(t, i)
        if 0 < st.alpha < 1:
            pulse += math.sin(st.alpha * math.pi) * 0.5
    g = glow.copy()
    ga = int(150 + 30 * min(1.0, pulse))
    g.putalpha(g.getchannel("A").point(lambda v: int(v * (ga / 150.0))))
    gs = int(g.width * cam.scale * 1.12)
    g = g.resize((gs, gs), Image.LANCZOS)
    gx, gy = camera_point(W / 2, H / 2 + 10, cam)
    frame.alpha_composite(g, (int(gx - gs / 2), int(gy - gs / 2)))

    # floor shadow under the whole word (fades in while the word builds)
    word_alpha = smoothstep(t / 1.25)
    if word_alpha > 0.001:
        fs_scale = cam.scale * (0.84 + 0.16 * word_alpha)
        fs = floor_shadow.resize(
            (int(floor_shadow.width * fs_scale), int(floor_shadow.height * fs_scale)),
            Image.LANCZOS,
        )
        fs = fs.copy()
        fs.putalpha(fs.getchannel("A").point(lambda v: int(v * word_alpha)))
        fx, fy = camera_point(W / 2, H / 2 + 235, cam)
        frame.alpha_composite(fs, (int(fx - fs.width / 2), int(fy - fs.height / 2)))

    # shadows first
    for i, sp in enumerate(letters):
        st = letter_state(t, i)
        if st.alpha <= 0.001 or st.scale_x <= 0.001 or st.scale_y <= 0.001:
            continue
        sx = st.scale_x * SPRITE_SCALE
        sy = st.scale_y * SPRITE_SCALE
        img, nax, nay = transformed_sprite(sp.shadow, sp.anchor_x, sp.anchor_y, sx * 1.02, sy * 0.98,
                                           st.rotation + cam.rotation, st.alpha * 0.95)
        px, py = camera_point(sp.center_x, sp.baseline_y + st.offset_y + 26, cam)
        frame.alpha_composite(img, (int(round(px - nax)), int(round(py - nay))))

    # letters
    drawn = []
    for i, sp in enumerate(letters):
        st = letter_state(t, i)
        if st.alpha <= 0.001 or st.scale_x <= 0.001 or st.scale_y <= 0.001:
            continue
        sx = st.scale_x * SPRITE_SCALE
        sy = st.scale_y * SPRITE_SCALE
        img, nax, nay = transformed_sprite(sp.image, sp.anchor_x, sp.anchor_y, sx, sy,
                                           st.rotation + cam.rotation, st.alpha)
        px, py = camera_point(sp.center_x, sp.baseline_y + st.offset_y, cam)
        frame.alpha_composite(img, (int(round(px - nax)), int(round(py - nay))))
        drawn.append((i, sp, st, px, py, sx, sy, img, nax, nay))

    # specular sweep across the finished word
    shine_p = clamp((t - 3.05) / 0.95)
    if 0.0 < shine_p < 1.0:
        band_x = -260 + (W + 520) * ease_in_out_cubic(shine_p)
        for i, sp, st, px, py, sx, sy, img, nax, nay in drawn:
            if t < 1.55:
                continue
            # local x of the band inside this transformed sprite
            lx = band_x - (px - nax)
            if lx < -120 or lx > img.width + 120:
                continue
            band = Image.new("L", img.size, 0)
            bd = ImageDraw.Draw(band)
            width = 90
            slant = 120
            bd.polygon(
                [(lx - width, 0), (lx + width, 0),
                 (lx + width + slant, img.height), (lx - width + slant, img.height)],
                fill=255,
            )
            band = band.filter(ImageFilter.GaussianBlur(26))
            band = ImageChops.multiply(band, img.getchannel("A"))
            shine = Image.new("RGBA", img.size, (255, 255, 255, 0))
            shine.putalpha(band.point(lambda v: int(v * 0.40)))
            frame.alpha_composite(shine, (int(round(px - nax)), int(round(py - nay))))

    draw_confetti(frame, confetti, t)
    draw_sparkles(frame, sparkles, t)
    return frame.convert("RGB")


# ---------------------------------------------------------------------------
# entry points
# ---------------------------------------------------------------------------

def render_still(out: Path, t: float = 4.9):
    print("building background...")
    bg = build_background()
    print("building letter sprites...")
    letters = build_letters()
    sparkles, confetti = build_effects(letters)
    glow = build_glow()
    floor_shadow = build_floor_shadow()
    print(f"composing still at t={t:.2f}s...")
    frame = compose_frame(t, bg, letters, sparkles, confetti, glow, floor_shadow)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.save(out, quality=95)
    print("saved", out)


def render_video(out: Path, limit: int | None = None):
    import imageio_ffmpeg
    total = NFRAMES if limit is None else min(NFRAMES, limit)

    print("building background...")
    bg = build_background()
    print("building letter sprites...")
    letters = build_letters()
    sparkles, confetti = build_effects(letters)
    glow = build_glow()
    floor_shadow = build_floor_shadow()

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-",
        "-an",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
        "-movflags", "+faststart",
        str(out),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for n in range(total):
            t = n / FPS
            frame = compose_frame(t, bg, letters, sparkles, confetti, glow, floor_shadow)
            proc.stdin.write(frame.tobytes())
            if n % 15 == 0:
                print(f"  frame {n:03d}/{total}  t={t:.2f}s", flush=True)
        proc.stdin.close()
    finally:
        stderr = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
        code = proc.wait()
    if code != 0:
        print(stderr[-4000:], file=sys.stderr)
        raise SystemExit(f"ffmpeg failed with code {code}")
    print("saved", out)

    # poster from the final still
    if limit is None:
        poster = out.with_name(out.stem + "-poster.png")
        render_still(poster, 4.9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=str, default="")
    ap.add_argument("--t", type=float, default=4.9)
    ap.add_argument("--out", type=str, default=str(ROOT / "jarvis-logo-3d.mp4"))
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    if args.still:
        render_still(Path(args.still), args.t)
    else:
        render_video(Path(args.out), args.limit or None)


if __name__ == "__main__":
    main()
