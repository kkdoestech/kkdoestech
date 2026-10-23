"""Generate assets/glitch.gif: three avatars glitching in orbit around a black hole.

Palette: black space, blue/red chromatic split, white/yellow hot accretion disk,
with small green and yellow noise accents.

Needs the transparent cutouts in assets/avatars/ (see tools/cut_avatars.py).

Usage:  python tools/make_glitch.py
"""

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H = 800, 340
CX, CY = W // 2, H // 2
BG = (8, 8, 12)
WHITE = (255, 255, 255)
BLUE = (0, 168, 255)
DEEP_BLUE = (0, 71, 255)
RED = (255, 31, 61)
GREEN = (57, 255, 20)
YELLOW = (255, 211, 0)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "glitch.gif"
AVATARS = ROOT / "assets" / "avatars"

FRAMES = 60          # one full loop; all motion uses whole-number frequencies so it loops seamlessly
FRAME_MS = 70
HORIZON = 50         # event-horizon radius (px)
DISK_RX, DISK_TILT = 225, 0.2
OUTLINE_PX = 4       # black border around each avatar (hides cut-out scraps)

# (file, front height px, orbit radius x, orbit radius y, starting angle, wobble (amp, freq, phase))
SPRITES = [
    ("1.png", 130, 300, 72, 0.0, (14, 3, 0.5)),
    ("2.png", 140, 260, 64, 2 * math.pi / 3, (18, 2, 1.9)),
    ("3.png", 118, 330, 80, 4 * math.pi / 3, (12, 4, 3.1)),
]


def load_font(names, size):
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


TAG_FONT = load_font(["consola.ttf", "DejaVuSansMono.ttf"], 16)


# ---------- avatars ----------

def load_sprite(name, height):
    """Avatar at 2x its largest on-screen size, with a black border round its silhouette."""
    im = Image.open(AVATARS / name).convert("RGBA")
    big = height * 2
    im = im.resize((round(im.width * big / im.height), big), Image.LANCZOS)
    pad = OUTLINE_PX * 2 + 2
    canvas = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    canvas.alpha_composite(im, (pad, pad))
    alpha = canvas.getchannel("A").point(lambda a: 255 if a > 40 else 0)
    border = alpha.filter(ImageFilter.MaxFilter(OUTLINE_PX * 4 + 1)).filter(ImageFilter.GaussianBlur(1))
    out = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    out.putalpha(border)
    out.alpha_composite(canvas)
    return out


def scaled(sprite, height):
    return sprite.resize((max(1, round(sprite.width * height / sprite.height)), height), Image.LANCZOS)


def tinted(sprite, color, strength=0.8):
    ghost = Image.new("RGBA", sprite.size, color + (0,))
    ghost.putalpha(sprite.getchannel("A").point(lambda a: int(a * strength)))
    return ghost


def slice_sprite(sprite, rng, count, max_shift):
    out = sprite.copy()
    for _ in range(count):
        y0 = rng.randint(0, max(0, sprite.height - 6))
        strip = sprite.crop((0, y0, sprite.width, min(sprite.height, y0 + rng.randint(4, 16))))
        out.paste((0, 0, 0, 0), (0, y0, sprite.width, y0 + strip.height))
        out.paste(strip, (rng.randint(-max_shift, max_shift), y0), strip)
    return out


# ---------- black hole ----------

YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
DX, DY = XX - CX, YY - CY


def ramp(t, stops):
    """Piecewise-linear colour ramp; t in [0, 1], stops = [(pos, (r, g, b)), ...]."""
    out = np.zeros(t.shape + (3,), np.float32)
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        m = (t >= p0) & (t <= p1)
        k = ((t - p0) / (p1 - p0))[m][:, None]
        out[m] = np.array(c0) * (1 - k) + np.array(c1) * k
    return out


DISK_STOPS = [(0.0, (255, 255, 255)), (0.18, (255, 211, 0)), (0.45, (255, 31, 61)),
              (0.75, (0, 71, 255)), (1.0, (0, 30, 90))]


def disk_layer(t, front):
    """Accretion disk (tilted ellipse). front=True gives the half nearer the viewer."""
    u, v = DX, DY / DISK_TILT
    r = np.sqrt(u * u + v * v)
    theta = np.arctan2(v, u)
    rn = (r - HORIZON * 1.3) / (DISK_RX - HORIZON * 1.3)
    inside = (rn >= 0) & (rn <= 1)
    spin = 2 * math.pi * t / FRAMES
    streaks = 0.65 + 0.35 * np.sin(5 * theta - 2 * spin + 8 * rn) * np.sin(3 * theta + spin + 3)
    doppler = 1 + 0.45 * np.cos(theta + math.pi)          # left side (approaching) brighter
    falloff = np.clip(1 - rn, 0, 1) ** 0.8 * np.clip(rn * 6, 0, 1)
    a = np.where(inside, falloff * streaks * doppler, 0)
    a = np.where((DY > 0) == front, a, 0)
    rgb = ramp(np.clip(rn, 0, 1), DISK_STOPS) * np.clip(doppler, 0.6, 1.3)[..., None]
    return rgb, np.clip(a, 0, 1)


def halo_layer(t):
    """Lensed photon ring hugging the horizon, brighter over the top (light bent from the far disk)."""
    R = np.sqrt(DX * DX + DY * DY)
    ang = np.arctan2(DY, DX)
    rn = (R - HORIZON) / 32
    band = np.exp(-((rn - 0.25) ** 2) / 0.08) * (R > HORIZON)
    top = 0.55 + 0.45 * np.clip(-np.sin(ang), 0, 1)
    shimmer = 0.85 + 0.15 * np.sin(4 * ang + 2 * math.pi * 3 * t / FRAMES)
    a = np.clip(band * top * shimmer, 0, 1)
    rgb = ramp(np.clip(rn, 0, 1), [(0, (255, 255, 255)), (0.3, (255, 211, 0)), (0.6, (255, 31, 61)), (1, (0, 71, 255))])
    return rgb, a


def over(base, rgb, a):
    return base * (1 - a[..., None]) + rgb * a[..., None]


def screen(base, rgb, a):
    add = rgb * a[..., None]
    return 255 - (255 - base) * (255 - add) / 255


def stars(rng):
    pts = [(rng.randint(0, W - 1), rng.randint(0, H - 1), rng.choice([WHITE, BLUE, WHITE, YELLOW]),
            rng.randint(0, FRAMES - 1)) for _ in range(90)]
    return pts


# ---------- frame composition ----------

def scanlines():
    overlay = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(overlay)
    for y in range(0, H, 3):
        d.line([(0, y), (W, y)], fill=(200, 200, 200))
    return overlay


SCANLINES = scanlines()


def frame_slices(img, rng, count, max_shift):
    out = img.copy()
    for _ in range(count):
        y0 = rng.randint(0, H - 6)
        strip = img.crop((0, y0, W, min(H, y0 + rng.randint(3, 24))))
        out.paste(ImageChops.offset(strip, rng.randint(-max_shift, max_shift), 0), (0, y0))
    return out


def glitch_levels(rng):
    """Mostly calm, with a few short bursts of heavy glitching."""
    levels = [0] * FRAMES
    for start in (8, 27, 46):
        for k in range(rng.randint(3, 5)):
            levels[(start + k) % FRAMES] = rng.choice([2, 3, 3])
    for k in rng.sample(range(FRAMES), 8):
        levels[k] = max(levels[k], 1)
    return levels


def draw_sprite(img, sprite, ghosts, cx, cy, level, rng):
    split = [3, 6, 10, 16][level]
    dx = rng.randint(split // 2 + 1, split)
    body = sprite
    if level >= 2:
        cx += rng.randint(-25, 25)  # jittery jump
        body = slice_sprite(sprite, rng, 3 + level * 2, 6 * level)
    x, y = int(cx - sprite.width / 2), int(cy - sprite.height / 2)
    img.alpha_composite(ghosts[0], (x + dx, y + rng.randint(-2, 2)))
    img.alpha_composite(ghosts[1], (x - dx, y + rng.randint(-2, 2)))
    img.alpha_composite(body, (x, y))


def main():
    rng = random.Random(1337)
    sprites = [(load_sprite(f, h), h, rx, ry, a0, wob) for f, h, rx, ry, a0, wob in SPRITES]
    levels = glitch_levels(rng)
    starfield = stars(rng)
    halo = [None] * FRAMES

    frames = []
    for i, level in enumerate(levels):
        # Space + stars.
        sky = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(sky)
        for sx, sy, col, ph in starfield:
            if (i + ph) % 20 < 17:
                d.point((sx, sy), fill=col)
        cursor = "_" if (i // 4) % 2 == 0 else " "
        d.text((18, 14), f"> online{cursor}", font=TAG_FONT, fill=GREEN)
        d.text((W - 110, 14), "// glitch", font=TAG_FONT, fill=YELLOW)
        d.rectangle((14, H - 18, 120, H - 15), fill=RED)
        d.rectangle((W - 120, H - 18, W - 14, H - 15), fill=DEEP_BLUE)

        # Where is each avatar this frame? Depth from orbit angle: sin > 0 = in front.
        placed = []
        for sprite, h, rx, ry, a0, (wa, wf, wp) in sprites:
            ang = a0 + 2 * math.pi * i / FRAMES
            depth = math.sin(ang)
            cx = CX + rx * math.cos(ang)
            cy = CY + ry * depth + wa * math.sin(2 * math.pi * wf * i / FRAMES + wp)
            height = int(h * (0.72 + 0.28 * (depth + 1) / 2))
            near = math.hypot(cx - CX, (cy - CY) * 2) < 180  # crossing the hole -> extra glitch
            lvl = min(3, level + (2 if near else 0))
            s = scaled(sprite, height)
            if depth < 0:  # far side: dimmer
                s = Image.merge("RGBA", [*(c.point(lambda v: int(v * (0.6 + 0.4 * (1 + depth)))) for c in s.split()[:3]),
                                         s.getchannel("A")])
            placed.append((depth, s, cx, cy, lvl))
        placed.sort(key=lambda p: p[0])

        # Layering: back avatars -> far disk -> halo -> horizon -> near disk -> front avatars.
        canvas = sky.convert("RGBA")
        for depth, s, cx, cy, lvl in placed:
            if depth < 0:
                draw_sprite(canvas, s, (tinted(s, RED), tinted(s, BLUE)), cx, cy, lvl, rng)

        base = np.asarray(canvas.convert("RGB"), np.float32)
        rgb, a = disk_layer(i, front=False)
        base = screen(base, rgb, a)
        if halo[i % FRAMES] is None:
            halo[i % FRAMES] = halo_layer(i)
        base = screen(base, *halo[i % FRAMES])
        base[np.sqrt(DX * DX + DY * DY) < HORIZON] = 0
        rgb, a = disk_layer(i, front=True)
        base = over(base, rgb, a)
        bh = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
        glow = bh.filter(ImageFilter.GaussianBlur(10))
        bh = ImageChops.screen(bh, ImageChops.multiply(glow, Image.new("RGB", (W, H), (110, 110, 130))))

        canvas = bh.convert("RGBA")
        for depth, s, cx, cy, lvl in placed:
            if depth >= 0:
                draw_sprite(canvas, s, (tinted(s, RED), tinted(s, BLUE)), cx, cy, lvl, rng)

        out = canvas.convert("RGB")
        if level:
            out = frame_slices(out, rng, [0, 2, 5, 8][level], [0, 10, 30, 60][level])
            d = ImageDraw.Draw(out)
            for _ in range([0, 2, 5, 9][level]):
                bx, by = rng.randint(0, W - 40), rng.randint(0, H - 10)
                d.rectangle((bx, by, bx + rng.randint(6, 60), by + rng.randint(2, 8)),
                            fill=rng.choice([GREEN, YELLOW, RED, BLUE, WHITE]))
        out = ImageChops.multiply(out, SCANLINES)
        frames.append(out.quantize(colors=192, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=[FRAME_MS if lvl < 2 else 55 for lvl in levels],
        loop=0,
        optimize=True,
    )
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB, {len(frames)} frames)")


if __name__ == "__main__":
    main()
