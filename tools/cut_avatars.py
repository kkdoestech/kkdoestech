"""Cut the three avatar characters out of their backgrounds.

Writes transparent PNGs to assets/avatars/{1,2,3}.png, which make_glitch.py uses.
Each source image needs its own technique:
  1.png - GrabCut inside a box around the character
  2.png - rembg (isnet-anime) matte, limited to a hand-drawn character outline
  3.png - colour key on the dark-teal backdrop

Usage:  python tools/cut_avatars.py <folder with 1.png 2.png 3.png>
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "assets" / "avatars"


def largest_component(mask):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    if n <= 1:
        return mask
    keep = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    return lab == keep


def fill_holes(mask):
    inv = (~mask).astype(np.uint8)
    n, lab = cv2.connectedComponents(inv)
    h, w = mask.shape
    edge = set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1])
    holes = ~np.isin(lab, list(edge)) & (inv > 0)
    return mask | holes


def cut_1(img):
    """GrabCut with the character's bounding box."""
    mask = np.zeros(img.shape[:2], np.uint8)
    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(img, mask, (138, 40, 148, 282), bgd, fgd, 8, cv2.GC_INIT_WITH_RECT)
    fg = np.isin(mask, (cv2.GC_FGD, cv2.GC_PR_FGD))
    return fill_holes(largest_component(fg))


def cut_2(img, rgb):
    """rembg matte, clipped to an outline of hat + body (drops pillars and the neighbour)."""
    from rembg import new_session, remove

    matte = np.array(remove(Image.fromarray(rgb), session=new_session("isnet-anime")))[:, :, 3]
    h, w = img.shape[:2]

    def shape(draw_fn):
        m = Image.new("L", (w, h), 0)
        draw_fn(ImageDraw.Draw(m))
        return np.array(m) > 0

    crown = shape(lambda d: d.polygon([(98, 18), (172, 34), (184, 90), (88, 90)], fill=255))
    brim = shape(lambda d: d.ellipse((26, 86, 240, 136), fill=255))
    head = shape(lambda d: (d.ellipse((58, 108, 217, 250), fill=255),
                            d.ellipse((48, 106, 94, 154), fill=255),
                            d.ellipse((184, 106, 228, 154), fill=255)))
    robe = shape(lambda d: d.polygon([(95, 244), (182, 244), (206, 264), (214, 300), (215, 440),
                                      (202, 474), (84, 474), (69, 440), (66, 300), (72, 264)], fill=255))
    fg = (matte > 110) & (crown | brim | head | robe)
    fg = fill_holes(largest_component(fg))

    # The brim is translucent gauze with the pillar showing through: make it plain dark.
    ring = brim & ~crown & ~head
    gray = rgb[ring].mean(axis=1, keepdims=True)
    rgb[ring] = (gray * 0.35 + 22).astype(np.uint8)
    fg |= ring

    # Drop leftover pillar (dusty pink) and vase (gold/cream) pixels elsewhere.
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(int)
    hue, sat, val = hsv[:, :, 0] * 2, hsv[:, :, 1] / 255, hsv[:, :, 2] / 255
    pillar = (hue >= 6) & (hue <= 30) & (sat > 0.2) & (sat < 0.62) & (val > 0.4)
    vase = (hue >= 34) & (hue <= 62) & (sat > 0.25) & (val > 0.5)
    fg &= ~((pillar | vase) & ~ring)
    fg = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    return largest_component(fg)


def cut_3(img):
    """Key out the dark-teal backdrop that touches the image border."""
    b, g, r = (img[:, :, i].astype(int) for i in range(3))
    teal = (g - r >= 7) & (b - r >= 7) & (np.maximum(np.maximum(r, g), b) < 90)
    teal = cv2.morphologyEx(teal.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lab = cv2.connectedComponents(teal)
    edge = (set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1])) - {0}
    bg = np.isin(lab, list(edge))
    # Eat the antialiased fringe between backdrop and outline.
    bg = cv2.dilate(bg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    return fill_holes(largest_component(~bg))


def save(rgb, fg, path):
    alpha = (fg * 255).astype(np.uint8)
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)  # soften the edge by ~1px
    im = Image.fromarray(np.dstack([rgb, alpha]), "RGBA")
    im.crop(im.getbbox()).save(path)


def main():
    src = Path(sys.argv[1])
    OUT.mkdir(parents=True, exist_ok=True)
    for n in (1, 2, 3):
        img = cv2.imread(str(src / f"{n}.png"))
        rgb = img[:, :, ::-1].copy()
        fg = {1: lambda: cut_1(img), 2: lambda: cut_2(img, rgb), 3: lambda: cut_3(img)}[n]()
        save(rgb, fg, OUT / f"{n}.png")
        print(f"wrote {OUT / f'{n}.png'}")


if __name__ == "__main__":
    main()
