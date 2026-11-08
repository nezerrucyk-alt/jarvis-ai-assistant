#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Генерує arc-reactor іконку assets/jarvis.ico для J.A.R.V.I.S."""

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 512
BG = (5, 8, 13, 255)
CYAN = (57, 215, 255, 255)
CYAN_DIM = (26, 111, 134, 255)
WHITE = (234, 255, 255, 255)
GOLD = (242, 193, 78, 255)


def make(size: int = SIZE) -> Image.Image:
    img = Image.new("RGBA", (size, size), BG)
    d = ImageDraw.Draw(img)
    cx = cy = size / 2
    u = size / 512.0

    # зовнішні кільця
    for radius, color, width in (
        (235 * u, (7, 34, 44, 255), 10 * u),
        (215 * u, (10, 49, 64, 255), 8 * u),
        (196 * u, CYAN_DIM, 6 * u),
    ):
        d.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            outline=color,
            width=max(1, int(width)),
        )

    # сегменти реактора
    seg_r = 176 * u
    box = (cx - seg_r, cy - seg_r, cx + seg_r, cy + seg_r)
    for k in range(12):
        start = k * 30 + 4
        d.arc(box, start=start, end=start + 20, fill=CYAN, width=max(2, int(9 * u)))

    # внутрішні кільця
    d.ellipse(
        (cx - 118 * u, cy - 118 * u, cx + 118 * u, cy + 118 * u),
        outline=CYAN_DIM,
        width=max(1, int(5 * u)),
    )
    d.ellipse(
        (cx - 100 * u, cy - 100 * u, cx + 100 * u, cy + 100 * u),
        outline=CYAN,
        width=max(1, int(3 * u)),
    )

    # трикутна котушка
    tri = [
        (cx, cy - 78 * u),
        (cx - 68 * u, cy + 48 * u),
        (cx + 68 * u, cy + 48 * u),
    ]
    d.polygon(tri, outline=CYAN, width=max(2, int(7 * u)))

    # ядро
    d.ellipse(
        (cx - 34 * u, cy - 34 * u, cx + 34 * u, cy + 34 * u),
        fill=CYAN,
    )
    d.ellipse(
        (cx - 14 * u, cy - 14 * u, cx + 14 * u, cy + 14 * u),
        fill=WHITE,
    )

    # золоті відблиски
    d.arc(
        (cx - 215 * u, cy - 215 * u, cx + 215 * u, cy + 215 * u),
        start=200,
        end=250,
        fill=GOLD,
        width=max(1, int(4 * u)),
    )
    return img


def main() -> None:
    out_dir = Path(__file__).resolve().parent / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)

    img = make()
    png = out_dir / "jarvis.png"
    img.save(png)

    ico = out_dir / "jarvis.ico"
    img.save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("OK:", png)
    print("OK:", ico)


if __name__ == "__main__":
    main()
