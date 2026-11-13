from pathlib import Path
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_logo as R

T = 4.9
letters = R.build_letters()
cam = R.camera_at(T)
canvas = Image.new("RGBA", (R.W, R.H), (0, 0, 0, 0))

for i, sp in enumerate(letters):
    st = R.letter_state(T, i)
    sx = st.scale_x * R.SPRITE_SCALE
    sy = st.scale_y * R.SPRITE_SCALE
    img, nax, nay = R.transformed_sprite(
        sp.shadow, sp.anchor_x, sp.anchor_y, sx * 1.02, sy * 0.98,
        st.rotation + cam.rotation, st.alpha * 0.95,
    )
    px, py = R.camera_point(sp.center_x, sp.baseline_y + st.offset_y + 26, cam)
    canvas.alpha_composite(img, (int(round(px - nax)), int(round(py - nay))))

for i, sp in enumerate(letters):
    st = R.letter_state(T, i)
    sx = st.scale_x * R.SPRITE_SCALE
    sy = st.scale_y * R.SPRITE_SCALE
    img, nax, nay = R.transformed_sprite(
        sp.image, sp.anchor_x, sp.anchor_y, sx, sy,
        st.rotation + cam.rotation, st.alpha,
    )
    px, py = R.camera_point(sp.center_x, sp.baseline_y + st.offset_y, cam)
    canvas.alpha_composite(img, (int(round(px - nax)), int(round(py - nay))))

out = Path(__file__).with_name("jarvis-logo-3d-transparent.png")
canvas.save(out)

bbox = canvas.getbbox()
pad = 36
crop = canvas.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad),
                    min(R.W, bbox[2] + pad), min(R.H, bbox[3] + pad)))
mark = Path(__file__).with_name("jarvis-logo-3d-mark.png")
crop.save(mark)
print("saved", out, canvas.size)
print("saved", mark, crop.size)

# preview on a dark navy card
prev = Image.new("RGBA", (crop.width + 120, crop.height + 120), (7, 18, 40, 255))
prev.alpha_composite(crop, (60, 60))
prev.convert("RGB").save(Path(__file__).with_name("jarvis-logo-3d-mark-preview.png"))
