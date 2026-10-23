"""Generate assets/pulsar.gif: a spinning pulsar whose vortex sucks the avatars in,
with a wavy, glitching "thanks for visiting" message underneath.

Each avatar spirals inward, shrinking, stretching and glitching harder until it
vanishes into the core with a flash, then re-enters from the edge (seamless loop).

Needs the transparent cutouts in assets/avatars/ (see tools/cut_avatars.py).

Usage:  python tools/make_pulsar.py
"""

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from make_glitch import BLUE, GREEN, RED, WHITE, YELLOW, load_font, load_sprite, ramp, slice_sprite, tinted

W, H = 800, 360
CX, CY = W // 2, 150
BG = (8, 8, 12)
OUT = Path(__file__).resolve().parent.parent / "assets" / "pulsar.gif"

FRAMES = 48
FRAME_MS = 70
PULSES = 4           # core pulses per loop
BEAM_TURNS = 2       # full beam rotations per loop
VORTEX_TURNS = 1     # spiral-arm rotations per loop

# (file, height at the edge, start offset in the loop, starting angle, spiral turns while falling)
SPRITES = [
    ("1.png", 120, 0.0, 0.0, 1.75),
    ("2.png", 130, 1 / 3, 2.1, 1.5),
    ("3.png", 110, 2 / 3, 4.2, 2.0),
]

TEXT = "thanks for visiting · stay glitchy"
TEXT_Y = 312          # vertical centre of the message
TEXT_FONT = load_font(["consolab.ttf", "consola.ttf", "DejaVuSansMono-Bold.ttf"], 30)
GLITCH_CHARS = "#%&@$!?/<>01"

YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
DX, DY = XX - CX, YY - CY
R = np.sqrt(DX * DX + DY * DY) + 1e-3
THETA = np.arctan2(DY, DX)


def screen(base, rgb, a):
    add = rgb * a[..., None]
    return 255 - (255 - base) * (255 - add) / 255


def vortex(t):
    """Log-spiral arms swirling inward, white-hot near the core, red/blue further out."""
    spin = 2 * math.pi * VORTEX_TURNS * t / FRAMES
    arms = 0.5 + 0.5 * np.cos(3 * (THETA + 1.6 * np.log(R)) + 3 * spin)
    arms = arms ** 3
    falloff = np.exp(-R / 150) * np.clip((R - 10) / 25, 0, 1)
    a = np.clip(arms * falloff * 1.4, 0, 1)
    rgb = ramp(np.clip(R / 330, 0, 1), [(0, (255, 255, 255)), (0.12, (0, 168, 255)), (0.35, (255, 31, 61)),
                                        (0.7, (0, 71, 255)), (1, (10, 20, 60))])
    return rgb, a


def beams(t):
    """Two opposite lighthouse beams sweeping round."""
    ang = 2 * math.pi * BEAM_TURNS * t / FRAMES
    d = np.angle(np.exp(1j * (THETA - ang)))          # wrapped angle to beam 1
    d2 = np.angle(np.exp(1j * (THETA - ang - math.pi)))
    width = 0.05 + 0.6 / (R / 12 + 1)                 # wide at the core, narrow far out
    core = np.exp(-(d / width) ** 2) + np.exp(-(d2 / width) ** 2)
    a = np.clip(core * np.exp(-R / 260), 0, 1)
    rgb = ramp(np.clip(R / 400, 0, 1), [(0, (255, 255, 255)), (0.25, (120, 210, 255)), (1, (0, 71, 255))])
    return rgb, a


def core(t, flash):
    pulse = 0.75 + 0.25 * math.cos(2 * math.pi * PULSES * t / FRAMES)
    glow = np.exp(-(R / (18 + 10 * flash)) ** 2) * (pulse + flash)
    halo = np.exp(-R / (40 + 30 * flash)) * 0.55 * (pulse + flash)
    a = np.clip(glow + halo, 0, 1)
    rgb = ramp(np.clip(R / 90, 0, 1), [(0, (255, 255, 255)), (0.3, (200, 235, 255)), (1, (0, 120, 255))])
    return rgb, a


def stars(rng):
    return [(rng.uniform(0, 1), rng.uniform(0, 2 * math.pi), rng.choice([WHITE, BLUE, WHITE, YELLOW]))
            for _ in range(140)]


def spiral_point(p, a0, turns):
    """Position on an inward spiral; p=0 at the edge, p=1 in the core."""
    r = 360 * (1 - p) ** 1.4
    ang = a0 + 2 * math.pi * turns * p
    return CX + r * math.cos(ang), CY + r * math.sin(ang) * 0.55, ang


def scanlines():
    overlay = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(overlay)
    for y in range(0, H, 3):
        d.line([(0, y), (W, y)], fill=(200, 200, 200))
    return overlay


SCANLINES = scanlines()


def falling_sprite(base, height, p, ang, rng):
    """Avatar shrunk, stretched toward the core and spun, plus its red/blue ghosts."""
    h = max(6, int(height * (1 - p) ** 0.8 * (1 + 0.9 * p)))      # stretched tall...
    w = max(4, int(base.width * height / base.height * (1 - p) ** 0.8 * (1 - 0.6 * p)))  # ...and thin
    s = base.resize((w, h), Image.LANCZOS)
    level = 0 if p < 0.35 else 1 if p < 0.6 else 2 if p < 0.8 else 3
    if level >= 2:
        s = slice_sprite(s, rng, 2 + level * 2, max(2, w // 4))
    s = s.rotate(-math.degrees(ang) + 90 + 120 * p, resample=Image.BICUBIC, expand=True)
    fade = min(1.0, p / 0.08) * min(1.0, (1 - p) / 0.06)  # fade in at the edge, out in the core
    if fade < 1:
        s.putalpha(s.getchannel("A").point(lambda v: int(v * fade)))
    split = [2, 4, 7, 11][level]
    return s, tinted(s, RED), tinted(s, BLUE), split


def draw_message(img, t, glitch, rng):
    """Wavy message with red/blue ghosts; letters scramble while the pulsar is feeding."""
    widths = [TEXT_FONT.getlength(ch) for ch in TEXT]
    x = (W - sum(widths)) / 2
    split = 2 + int(6 * glitch)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for k, (ch, w) in enumerate(zip(TEXT, widths)):
        y = TEXT_Y + 7 * math.sin(2 * math.pi * 2 * t / FRAMES - k * 0.45) - 17
        if ch != " " and rng.random() < 0.01 + 0.2 * glitch:
            ch = rng.choice(GLITCH_CHARS)
        jitter = rng.randint(-split, split) if glitch > 0.3 else 0
        d.text((x + 2, y + 2), ch, font=TEXT_FONT, fill=(0, 0, 0, 255))           # shadow
        d.text((x + split + jitter, y), ch, font=TEXT_FONT, fill=RED + (200,))
        d.text((x - split + jitter, y), ch, font=TEXT_FONT, fill=BLUE + (200,))
        d.text((x + jitter, y), ch, font=TEXT_FONT, fill=YELLOW if ch == "·" else WHITE)
        x += w
    if (t // 4) % 2 == 0:  # blinking cursor
        d.text((x + 4, TEXT_Y - 17), "_", font=TEXT_FONT, fill=GREEN)
    img.alpha_composite(layer)


def main():
    rng = random.Random(4242)
    sprites = [(load_sprite(f, h), h, off, a0, turns) for f, h, off, a0, turns in SPRITES]
    starfield = stars(rng)

    frames = []
    for i in range(FRAMES):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        # Stars spiralling inward on the same flow as the avatars.
        for p0, a0, col in starfield:
            p = (p0 + i / FRAMES) % 1
            x, y, _ = spiral_point(p, a0, 1.0)
            x2, y2, _ = spiral_point(max(0, p - 0.02), a0, 1.0)
            d.line([(x2, y2), (x, y)], fill=col if p < 0.85 else WHITE)

        progress = [((i / FRAMES + off) % 1) for _, _, off, _, _ in sprites]

        base = np.asarray(img, np.float32)
        base = screen(base, *vortex(i))
        base = screen(base, *beams(i))
        canvas = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")

        # Avatars, farthest-out first so the ones nearest the core draw on top.
        order = sorted(zip(sprites, progress), key=lambda sp: sp[1])
        for (sprite, h, off, a0, turns), p in order:
            x, y, ang = spiral_point(p, a0, turns)
            s, red, blue, split = falling_sprite(sprite, h, p, ang, rng)
            dx = rng.randint(split // 2 + 1, split)
            px, py = int(x - s.width / 2), int(y - s.height / 2)
            canvas.alpha_composite(red, (px + dx, py + rng.randint(-2, 2)))
            canvas.alpha_composite(blue, (px - dx, py + rng.randint(-2, 2)))
            canvas.alpha_composite(s, (px, py))

        swallow = max((p - 0.9) / 0.1 for p in progress if p > 0.9) if max(progress) > 0.9 else 0.0
        draw_message(canvas, i, swallow, rng)
        base = np.asarray(canvas.convert("RGB"), np.float32)
        base = screen(base, *core(i, swallow))
        out = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
        glow = out.filter(ImageFilter.GaussianBlur(8))
        out = ImageChops.screen(out, ImageChops.multiply(glow, Image.new("RGB", (W, H), (90, 90, 110))))

        # Screen-wide glitch while something is being swallowed.
        if swallow > 0.3:
            for _ in range(int(2 + 6 * swallow)):
                y0 = rng.randint(0, H - 6)
                strip = out.crop((0, y0, W, min(H, y0 + rng.randint(3, 18))))
                out.paste(ImageChops.offset(strip, rng.randint(-40, 40), 0), (0, y0))
            dr = ImageDraw.Draw(out)
            for _ in range(int(3 * swallow) + 1):
                bx, by = rng.randint(0, W - 40), rng.randint(0, H - 10)
                dr.rectangle((bx, by, bx + rng.randint(6, 50), by + rng.randint(2, 6)),
                             fill=rng.choice([GREEN, YELLOW, RED, BLUE]))
        out = ImageChops.multiply(out, SCANLINES)
        frames.append(out.quantize(colors=80, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))

    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=FRAME_MS, loop=0, optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB, {len(frames)} frames)")


if __name__ == "__main__":
    main()
