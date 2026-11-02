"""Visual styles for video-forge text scenes, so videos don't look copy-pasted.

Each style renders a whole scene clip (background, animated caption, decorations)
with Pillow. Inside a style every scene gets its own background, layout, entrance
animation and decorations, chosen by a seeded RNG: the same storyboard renders the
same way, a different title (or "seed") gives a different-looking video.

Styles:
  pixel    3D-pixel (voxel) world with the orange mascot; caption in pixel panels/bubbles
  neon     synthwave: dark sky, glowing sun, moving perspective grid, glowing text
  comic    halftone / burst backgrounds, tilted comic panels, action stars
  minimal  clean light backgrounds, big typography, wipe/slide reveals, accent shapes
"""
from __future__ import annotations

import hashlib
import math
import random
import subprocess
import textwrap
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

STYLES = ("pixel", "neon", "comic", "minimal")
LEAD_IN = 0.35

FONT_DIRS = ["/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/TTF/", "/Library/Fonts/", "C:/Windows/Fonts/"]


def _font(name: str, size: int, fallback: str | None = None) -> ImageFont.FreeTypeFont:
    for d in FONT_DIRS:
        p = Path(d) / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    if fallback:
        try:
            return ImageFont.truetype(fallback, size)
        except OSError:
            pass
    return ImageFont.load_default(size)


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def mix(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def ease_back(x):  # overshoot "pop"
    x = max(0.0, min(1.0, x))
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def vgrad(img, top, bottom, y0=0, y1=None, step=2):
    y1 = img.height if y1 is None else y1
    dr = ImageDraw.Draw(img)
    for y in range(y0, y1, step):
        dr.rectangle([0, y, img.width, y + step], fill=mix(top, bottom, (y - y0) / max(1, y1 - y0)))


def wrap(text, font, max_w, draw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def voice_levels(path: Path | None, d: float, fps: int) -> np.ndarray:
    rms = np.zeros(int(d * fps) + 3)
    if not path or not Path(path).exists():
        return rms
    with wave.open(str(path)) as w:
        sr = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    hop = max(1, sr // fps)
    off = int(LEAD_IN * fps)
    for i in range(len(a) // hop):
        if off + i < len(rms):
            rms[off + i] = float(np.sqrt(np.mean(a[i * hop:(i + 1) * hop] ** 2)))
    return rms / rms.max() if rms.max() > 0 else rms


# =========================================================================== #
# pixel style
# =========================================================================== #
MASCOT = [
    ".ooooooooo.",
    ".ooooooooo.",
    "oo#ooooo#oo",
    "ooooooooooo",
    ".ooooooooo.",
    ".ooooooooo.",
    ".o.o...o.o.",
    ".o.o...o.o.",
]
MASCOT_BLINK = [r.replace("#", "o") if i == 2 else r for i, r in enumerate(MASCOT)]
MASCOT_STEP = MASCOT[:6] + ["o..o...o..o", "o..o...o..o"]
MASCOT_WAVE = ["o.ooooooooo", "o.ooooooooo", "oo#ooooo#oo", ".oooooooooo"] + MASCOT[4:]
CACTUS = ["..G..", ".GG..", ".GG.G", "GGG.G", "GGGGG", ".GGG.", "..G..", "..G..", "..G.."]
TREE = ["..LLL..", ".LLLLL.", "LLLLLLL", "LLLLLLL", ".LLLLL.", "...T...", "...T...", "...T..."]
PIX_PAL = {"#": (20, 20, 20), "G": (70, 150, 70), "L": (60, 140, 70), "T": (110, 75, 50)}


def voxel(img, grid, x, y, b, d=None, flip=False, pal=None):
    """Sprite as extruded cubes: front face + lit top + shaded right side."""
    pal = pal or PIX_PAL
    d = b // 2 if d is None else d
    dr = ImageDraw.Draw(img)
    rows = [r[::-1] if flip else r for r in grid]
    x, y = int(round(x)), int(round(y))

    def filled(cx, cy):
        return 0 <= cy < len(rows) and 0 <= cx < len(rows[cy]) and rows[cy][cx] != "."

    cells = [(cx, cy, ch) for cy, r in enumerate(rows) for cx, ch in enumerate(r) if ch != "."]
    for cx, cy, ch in cells:
        c = pal[ch]
        px, py = x + cx * b, y + cy * b
        if d and not filled(cx, cy - 1):
            dr.polygon([(px, py), (px + d, py - d), (px + b + d - 1, py - d), (px + b - 1, py)], fill=shade(c, 1.3))
        if d and not filled(cx + 1, cy):
            dr.polygon([(px + b - 1, py), (px + b + d - 1, py - d), (px + b + d - 1, py + b - d - 1),
                        (px + b - 1, py + b - 1)], fill=shade(c, 0.6))
    for cx, cy, ch in cells:
        px, py = x + cx * b, y + cy * b
        dr.rectangle([px, py, px + b - 1, py + b - 1], fill=pal[ch])


def _pix_bg(img, kind, t, rng_seed, accent):
    w, h = img.size
    dr = ImageDraw.Draw(img)
    rnd = random.Random(rng_seed)
    ground = int(h * 0.75)
    if kind == "room":
        vgrad(img, (27, 22, 64), (52, 40, 110), 0, ground, 4)
        dr.rectangle([w * 0.55, 50, w * 0.92, 140], fill=(10, 12, 40), outline=(90, 80, 160), width=3)
        for i in range(12):
            x, y = rnd.randrange(int(w * 0.57), int(w * 0.9)), rnd.randrange(55, 135)
            c = int(150 + 100 * (0.5 + 0.5 * math.sin(t * 4 + i)))
            dr.point((x, y), fill=(c, c, c))
        for row in range(0, h - ground, 10):
            for col in range(0, w, 20):
                c = (60, 48, 110) if ((row // 10) + (col // 20)) % 2 == 0 else (48, 38, 92)
                dr.rectangle([col, ground + row, col + 19, ground + row + 9], fill=c)
    elif kind in ("desert", "sunset"):
        sky = ((255, 170, 90), (255, 225, 160)) if kind == "desert" else ((90, 60, 140), (255, 150, 110))
        vgrad(img, *sky, 0, ground, 4)
        cx, cy, r = int(w * 0.72), int(h * 0.2), 24
        for yy in range(-r, r + 1, 4):
            for xx in range(-r, r + 1, 4):
                if xx * xx + yy * yy <= r * r:
                    dr.rectangle([cx + xx, cy + yy, cx + xx + 3, cy + yy + 3], fill=(255, 235, 170))
        for base, amp, col, par in [(ground - 70, 16, (232, 160, 90), 0.3), (ground - 25, 12, (240, 185, 110), 0.6),
                                    (ground + 10, 8, (247, 205, 135), 1.0)]:
            for x in range(0, w, 3):
                y = base + amp * math.sin((x + t * 30 * par) * 0.03 + par * 5)
                dr.rectangle([x, int(y) // 3 * 3, x + 2, h], fill=col)
        voxel(img, CACTUS, w * 0.1 - t * 4, ground - 50, 4)
    elif kind == "space":
        vgrad(img, (5, 8, 30), (25, 12, 60), 0, h, 4)
        for i in range(70):
            x, y = rnd.randrange(w), rnd.randrange(h)
            c = int(120 + 135 * (0.5 + 0.5 * math.sin(t * 3 + i)))
            dr.rectangle([x, y, x + (i % 3 == 0), y + (i % 3 == 0)], fill=(c, c, min(255, c + 30)))
        pr, px, py = 34, int(w * 0.75), int(h * 0.22)
        for yy in range(-pr, pr + 1, 4):
            for xx in range(-pr, pr + 1, 4):
                if xx * xx + yy * yy <= pr * pr:
                    lit = 0.6 + 0.4 * (-(xx + yy) / (2 * pr) + 0.5)
                    dr.rectangle([px + xx, py + yy, px + xx + 3, py + yy + 3], fill=shade(accent, lit))
        dr.rectangle([0, ground, w, h], fill=(70, 70, 90))
        for x in range(0, w, 24):
            dr.rectangle([x + 6, ground + 6, x + 14, ground + 10], fill=(55, 55, 72))
    elif kind == "city":
        vgrad(img, (20, 24, 60), (70, 50, 110), 0, ground, 4)
        x = -int(t * 8) % 30 - 30
        while x < w:
            bw, bh = rnd.randrange(22, 44), rnd.randrange(60, 200)
            dr.rectangle([x, ground - bh, x + bw, ground], fill=(30, 30, 55))
            for wy in range(ground - bh + 6, ground - 6, 10):
                for wx in range(x + 4, x + bw - 4, 8):
                    if rnd.random() < 0.45:
                        dr.rectangle([wx, wy, wx + 3, wy + 4], fill=(255, 210, 110))
            x += bw + rnd.randrange(2, 8)
        dr.rectangle([0, ground, w, h], fill=(45, 45, 60))
        for x in range(-int(t * 60) % 40, w, 40):
            dr.rectangle([x, ground + 30, x + 20, ground + 33], fill=(230, 230, 230))
    elif kind == "forest":
        vgrad(img, (120, 190, 255), (200, 235, 255), 0, ground, 4)
        for i, (tx, s) in enumerate([(0.05, 5), (0.3, 4), (0.62, 6), (0.85, 4)]):
            voxel(img, TREE, w * tx, ground - len(TREE) * s, s)
        dr.rectangle([0, ground, w, h], fill=(95, 170, 80))
        for i in range(40):
            x, y = rnd.randrange(w), rnd.randrange(ground, h)
            dr.rectangle([x, y, x + 2, y + 3], fill=(70, 140, 60))
    elif kind == "ocean":
        vgrad(img, (110, 200, 255), (190, 235, 255), 0, ground - 40, 4)
        for k in range(8):
            yy = ground - 40 + k * 6
            for x in range(0, w, 4):
                y = yy + 2 * math.sin(x * 0.08 + t * 3 + k)
                dr.rectangle([x, int(y), x + 3, h], fill=mix((40, 120, 200), (20, 70, 150), k / 8))
        dr.rectangle([0, ground + 10, w, h], fill=(240, 215, 160))


def _pix_panel(img, lines, font, x, y, accent, progress, tail=None):
    dr = ImageDraw.Draw(img)
    dr.fontmode = "1"
    lh = font.size + 4
    tw = max(dr.textlength(l, font=font) for l in lines)
    bw, bh = int(tw) + 16, len(lines) * lh + 12
    x = max(4, min(img.width - bw - 4, int(x - bw / 2)))
    dr.rectangle([x + 4, y + 4, x + bw + 4, y + bh + 4], fill=(0, 0, 0))
    dr.rectangle([x, y, x + bw, y + bh], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    dr.rectangle([x + 2, y + 2, x + bw - 2, y + 5], fill=accent)
    if tail:
        tx = min(max(tail[0], x + 10), x + bw - 10)
        dr.polygon([(tx - 6, y + bh - 1), (tx + 6, y + bh - 1), tail], fill=(255, 255, 255), outline=(0, 0, 0))
        dr.line([(tx - 5, y + bh - 1), (tx + 5, y + bh - 1)], fill=(255, 255, 255), width=2)
    left = int(sum(len(l) for l in lines) * max(0.0, min(1.0, progress)) + 0.999)
    for i, l in enumerate(lines):
        dr.text((x + 8, y + 9 + i * lh), l[:max(0, left)], font=font, fill=(20, 20, 20))
        left -= len(l)
    return x, y, bw, bh


def render_pixel(ctx, t, f):
    W, H = ctx.W // 4, ctx.H // 4
    img = Image.new("RGB", (W, H))
    v = ctx.var
    _pix_bg(img, v["bg"], t, ctx.seed_int, ctx.accent)
    ground = int(H * 0.75)
    lvl = ctx.rms[min(f, len(ctx.rms) - 1)]
    b = v["size"]
    mw, mh = 11 * b, 8 * b
    action = v["action"]
    grid = MASCOT_BLINK if (t % 2.7) > 2.55 else MASCOT
    if action == "walk":
        mx = -mw + (W * 0.5 + mw / 2) * ease_out(t / 1.6)
        grid = MASCOT_STEP if int(t * 6) % 2 and t < 1.6 else grid
        my = ground - mh
    elif action == "jump":
        mx = W * v["mx"] - mw / 2
        my = ground - mh - abs(math.sin(t * 4)) * 26
    elif action == "peek":
        mx = W * v["mx"] - mw / 2
        my = ground - mh + (1 - ease_back(t / 0.6)) * (mh + 10)
    elif action == "dance":
        mx = W * v["mx"] - mw / 2 + math.sin(t * 5) * 12
        my = ground - mh - abs(math.sin(t * 10)) * 6
        grid = MASCOT_WAVE if int(t * 4) % 2 else grid
    else:  # talk
        mx = W * v["mx"] - mw / 2
        my = ground - mh - abs(math.sin(t * 9)) * 9 * lvl
    dr = ImageDraw.Draw(img, "RGBA")
    dr.ellipse([mx + 4, ground - 3, mx + mw, ground + 3], fill=(0, 0, 0, 70))
    pal = {"o": ctx.mascot, "#": (20, 20, 20)}
    voxel(img, grid, mx, my, b, pal=pal, flip=v["flip"])
    # particles
    rnd = random.Random(ctx.seed_int + 7)
    if v["particles"] == "sparkles":
        for i in range(14):
            x, y = rnd.randrange(W), rnd.randrange(int(H * 0.7))
            if (t * 3 + i * 0.37) % 1 < 0.5:
                dr.rectangle([x, y, x + 1, y + 1], fill=(255, 255, 220))
                dr.point([(x - 2, y), (x + 3, y), (x, y - 2), (x, y + 3)], fill=(255, 255, 220))
    elif v["particles"] == "confetti":
        for i in range(40):
            x = (rnd.randrange(W) + math.sin(t * 2 + i) * 8) % W
            y = (rnd.randrange(H) + t * (40 + i % 5 * 15)) % H
            dr.rectangle([x, y, x + 2, y + 2], fill=ctx.palette[i % len(ctx.palette)])
    elif v["particles"] == "snow":
        for i in range(40):
            x = (rnd.randrange(W) + math.sin(t + i) * 6) % W
            y = (rnd.randrange(H) + t * 25) % H
            dr.rectangle([x, y, x + 1, y + 1], fill=(255, 255, 255))
    # caption
    if ctx.caption:
        font = ctx.font_pixel
        lines = wrap(ctx.caption, font, W - 40, ImageDraw.Draw(img))
        prog = (t - 0.15) / 0.6 if v["enter"] == "type" else 1.0
        if v["layout"] == "bubble":
            top = my - (len(lines) * (font.size + 4) + 12) - 22
            _pix_panel(img, lines, font, mx + mw / 2, max(30, top), ctx.accent, prog, (mx + mw / 2, my - 4))
        else:
            ty = {"top": int(H * 0.1), "middle": int(H * 0.36)}[v["layout"]]
            if v["enter"] == "drop":
                ty = int(ty - (1 - ease_back((t - 0.1) / 0.5)) * (ty + 80))
            _pix_panel(img, lines, font, W / 2, ty, ctx.accent, prog)
    return img.resize((ctx.W, ctx.H), Image.NEAREST)


def vary_pixel(rng, idx, total, base):
    bgs = ["room", "desert", "space", "city", "forest", "ocean", "sunset"]
    action = rng.choice(["talk", "walk", "jump", "peek", "dance", "talk"])
    return {
        "bg": bgs[(base + idx * 3) % len(bgs)],
        "action": "dance" if idx == total - 1 else action,
        "mx": rng.choice([0.25, 0.3, 0.5, 0.7, 0.72]),
        "flip": rng.random() < 0.3,
        "size": rng.choice([5, 6, 6, 7]),
        "layout": rng.choice(["bubble", "bubble", "top", "middle"]),
        "enter": rng.choice(["type", "drop", "type"]),
        "particles": "confetti" if idx == total - 1 else rng.choice(["none", "sparkles", "none", "snow"]),
    }


# =========================================================================== #
# neon style
# =========================================================================== #
def vary_neon(rng, idx, total, base):
    return {"sun": rng.random() < 0.6, "grid_speed": rng.choice([0.6, 1.0, 1.6]),
            "pos": rng.choice([0.2, 0.24, 0.28]), "shape": rng.choice(["triangle", "ring", "none", "bars"]),
            "enter": rng.choice(["flicker", "slide", "zoom"]), "hue": (base + idx * 2) % 5}


def render_neon(ctx, t, f):
    W, H = ctx.W // 2, ctx.H // 2
    v = ctx.var
    c1 = ctx.palette[v["hue"] % len(ctx.palette)]
    c2 = ctx.palette[(v["hue"] + 2) % len(ctx.palette)]
    if "bg" not in ctx.cache:
        bg = Image.new("RGB", (W, H))
        vgrad(bg, (8, 4, 24), (40, 10, 60), 0, int(H * 0.6), 2)
        vgrad(bg, (10, 2, 20), (4, 0, 10), int(H * 0.6), H, 2)
        dr = ImageDraw.Draw(bg)
        rnd = random.Random(ctx.seed_int)
        for i in range(60):
            x, y = rnd.randrange(W), rnd.randrange(int(H * 0.55))
            dr.point((x, y), fill=(200, 200, 255))
        if v["sun"]:
            r, cx, cy = int(W * 0.28), W // 2, int(H * 0.5)
            sun = Image.new("L", (W, H), 0)
            ImageDraw.Draw(sun).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
            sd = ImageDraw.Draw(sun)
            for k in range(7):
                y = cy + int(r * 0.15) + k * int(r * 0.13)
                sd.rectangle([0, y, W, y + 2 + k], fill=0)
            col = Image.new("RGB", (W, H))
            vgrad(col, (255, 220, 90), (255, 40, 140), cy - r, cy + r, 2)
            bg.paste(col, (0, 0), sun)
            glow = sun.filter(ImageFilter.GaussianBlur(18)).point(lambda p: p * 0.6)
            bg.paste(Image.new("RGB", (W, H), (255, 80, 150)), (0, 0), glow)
            bg.paste(col, (0, 0), sun)
        ctx.cache["bg"] = bg
        # text layer with glow
        font = ctx.font_big(int(W * 0.11))
        tmp = ImageDraw.Draw(bg)
        lines = wrap(ctx.caption or "", font, W * 0.86, tmp)
        txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        td = ImageDraw.Draw(txt)
        lh = int(font.size * 1.15)
        y0 = int(H * v["pos"]) - len(lines) * lh // 2
        for i, l in enumerate(lines):
            lw = td.textlength(l, font=font)
            td.text(((W - lw) / 2, y0 + i * lh), l, font=font, fill=(255, 255, 255, 255))
        alpha = txt.split()[3]
        glow = Image.new("RGBA", (W, H), c1 + (0,))
        glow.putalpha(alpha.filter(ImageFilter.GaussianBlur(10)).point(lambda p: min(255, p * 2)))
        core = Image.new("RGBA", (W, H), mix(c1, (255, 255, 255), 0.7) + (0,))
        core.putalpha(alpha)
        ctx.cache["text"] = Image.alpha_composite(glow, core)
    img = ctx.cache["bg"].copy()
    dr = ImageDraw.Draw(img)
    hor = int(H * 0.6)
    # perspective grid
    off = (t * v["grid_speed"]) % 1
    for k in range(14):
        z = (k + off) / 14
        y = hor + int((H - hor) * z * z)
        dr.line([(0, y), (W, y)], fill=mix((40, 0, 60), c2, 0.3 + 0.7 * z), width=1 + int(z * 2))
    for k in range(-12, 13):
        dr.line([(W / 2 + k * 6, hor), (W / 2 + k * W * 0.16, H)], fill=shade(c2, 0.8), width=1)
    # floating shapes
    if v["shape"] != "none":
        for i in range(5):
            a = t * (0.5 + i * 0.2) + i
            x, y, s = W * (0.12 + 0.19 * i), H * 0.06 + 10 * math.sin(a), 8 + i * 2
            col = c1 if i % 2 else c2
            if v["shape"] == "triangle":
                pts = [(x + s * math.cos(a + k * 2.094), y + s * math.sin(a + k * 2.094)) for k in range(3)]
                dr.polygon(pts, outline=col, width=2)
            elif v["shape"] == "ring":
                dr.ellipse([x - s, y - s, x + s, y + s], outline=col, width=2)
            else:
                dr.rectangle([x - 2, H * 0.6 - 20 - 30 * abs(math.sin(a * 2)), x + 4, H * 0.6], fill=col)
    if ctx.caption:
        txt = ctx.cache["text"]
        e = v["enter"]
        if e == "flicker":
            on = t > 0.5 or int(t * 20) % 3 != 0
            if on:
                img.paste(txt, (0, 0), txt)
        elif e == "slide":
            dx = int((1 - ease_out(t / 0.5)) * -W)
            img.paste(txt, (dx, 0), txt)
        else:
            z = 0.6 + 0.4 * ease_back(t / 0.5)
            tw, th = int(W * z), int(H * z)
            small = txt.resize((tw, th))
            img.paste(small, ((W - tw) // 2, (H - th) // 2), small)
    # scanlines
    sl = ImageDraw.Draw(img, "RGBA")
    for y in range(0, H, 3):
        sl.line([(0, y), (W, y)], fill=(0, 0, 0, 40))
    return img.resize((ctx.W, ctx.H), Image.BILINEAR)


# =========================================================================== #
# comic style
# =========================================================================== #
def vary_comic(rng, idx, total, base):
    return {"bg": rng.choice(["dots", "burst", "dots", "stripes"]), "tilt": rng.uniform(-5, 5),
            "pos": rng.choice([0.25, 0.4, 0.55]), "star": rng.random() < 0.5, "color": (base + idx) % 6,
            "word": rng.choice(["ВАУ!", "БАМ!", "ОГО!", "ХОП!", "ДА!", "БУМ!"])}


def render_comic(ctx, t, f):
    W, H = ctx.W // 2, ctx.H // 2
    v = ctx.var
    col = ctx.palette[v["color"] % len(ctx.palette)]
    if "bg" not in ctx.cache:
        bg = Image.new("RGB", (W + 40, H + 40), mix(col, (255, 255, 255), 0.35))
        dr = ImageDraw.Draw(bg)
        if v["bg"] == "dots":
            for y in range(0, H + 40, 14):
                for x in range((y // 14) % 2 * 7, W + 40, 14):
                    r = 2 + 3 * (y / (H + 40))
                    dr.ellipse([x - r, y - r, x + r, y + r], fill=shade(col, 0.85))
        elif v["bg"] == "burst":
            cx, cy = (W + 40) / 2, (H + 40) * v["pos"]
            for k in range(24):
                a0, a1 = k * math.tau / 24, (k + 0.5) * math.tau / 24
                if k % 2 == 0:
                    dr.polygon([(cx, cy), (cx + 2000 * math.cos(a0), cy + 2000 * math.sin(a0)),
                                (cx + 2000 * math.cos(a1), cy + 2000 * math.sin(a1))], fill=shade(col, 0.85))
        else:
            for x in range(-H, W + 40, 26):
                dr.polygon([(x, 0), (x + 12, 0), (x + 12 + H, H + 40), (x + H, H + 40)], fill=shade(col, 0.88))
        ctx.cache["bg"] = bg
        # panel with caption
        font = ctx.font_big(int(W * 0.095))
        lines = wrap((ctx.caption or "").upper(), font, W * 0.72, dr)
        lh = int(font.size * 1.2)
        pw = int(max([dr.textlength(l, font=font) for l in lines] or [0]) + 40)
        ph = len(lines) * lh + 34
        panel = Image.new("RGBA", (pw + 12, ph + 12), (0, 0, 0, 0))
        pd = ImageDraw.Draw(panel)
        pd.rectangle([10, 10, pw + 10, ph + 10], fill=(0, 0, 0, 255))
        pd.rectangle([0, 0, pw, ph], fill=(255, 250, 230, 255), outline=(0, 0, 0, 255), width=5)
        for i, l in enumerate(lines):
            lw = pd.textlength(l, font=font)
            pd.text(((pw - lw) / 2, 17 + i * lh), l, font=font, fill=(20, 20, 20, 255))
        ctx.cache["panel"] = panel.rotate(v["tilt"], expand=True, resample=Image.BICUBIC)
        # action star
        sfont = ctx.font_big(int(W * 0.08))
        star = Image.new("RGBA", (int(W * 0.42), int(W * 0.42)), (0, 0, 0, 0))
        sd = ImageDraw.Draw(star)
        s2 = star.width / 2
        pts = [(s2 + (s2 if k % 2 == 0 else s2 * 0.55) * math.cos(k * math.pi / 9),
                s2 + (s2 if k % 2 == 0 else s2 * 0.55) * math.sin(k * math.pi / 9)) for k in range(18)]
        sd.polygon(pts, fill=(255, 220, 40, 255), outline=(0, 0, 0, 255), width=4)
        ww = sd.textlength(v["word"], font=sfont)
        sd.text((s2 - ww / 2, s2 - sfont.size * 0.6), v["word"], font=sfont, fill=(220, 30, 30, 255),
                stroke_width=2, stroke_fill=(0, 0, 0, 255))
        ctx.cache["star"] = star
    off = int(10 * math.sin(t * 0.8))
    img = ctx.cache["bg"].crop((20 + off, 20, 20 + off + W, 20 + H))
    if ctx.caption:
        p = ctx.cache["panel"]
        z = ease_back((t - 0.05) / 0.4)
        if z > 0.02:
            pw, ph = max(1, int(p.width * z)), max(1, int(p.height * z))
            pp = p.resize((pw, ph))
            img.paste(pp, ((W - pw) // 2, int(H * v["pos"] - ph / 2)), pp)
    if v["star"] and t > 0.35:
        s = ctx.cache["star"]
        z = ease_back((t - 0.35) / 0.35) * (1 + 0.04 * math.sin(t * 8))
        sw = max(1, int(s.width * z))
        ss = s.resize((sw, sw)).rotate(8 * math.sin(t * 3), resample=Image.BICUBIC)
        p = ctx.cache["panel"]
        img.paste(ss, (int(W * 0.58), int(H * v["pos"] + p.height / 2 - s.width * 0.15)), ss)
    dr = ImageDraw.Draw(img)
    dr.rectangle([0, 0, W - 1, H - 1], outline=(0, 0, 0), width=8)
    return img.resize((ctx.W, ctx.H), Image.BILINEAR)


# =========================================================================== #
# minimal style
# =========================================================================== #
def vary_minimal(rng, idx, total, base):
    return {"align": rng.choice(["left", "center", "left"]), "pos": rng.choice([0.3, 0.42, 0.55]),
            "shape": rng.choice(["circle", "bars", "dots", "corner"]), "dark": rng.random() < 0.25,
            "enter": rng.choice(["wipe", "rise", "words"]), "color": (base + idx) % 6}


def render_minimal(ctx, t, f):
    W, H = ctx.W // 2, ctx.H // 2
    v = ctx.var
    bgc, fg = ((22, 22, 26), (245, 245, 245)) if v["dark"] else ((246, 244, 239), (25, 25, 30))
    lum = lambda c: 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
    accs = [c for c in ctx.palette if (lum(c) > 110 if v["dark"] else lum(c) < 200)] or ctx.palette
    acc = accs[v["color"] % len(accs)]
    img = Image.new("RGB", (W, H), bgc)
    dr = ImageDraw.Draw(img)
    # accent shapes, slowly moving
    if v["shape"] == "circle":
        r = W * 0.45
        cx, cy = W * 0.85 + 10 * math.sin(t * 0.7), H * 0.15 + 10 * math.cos(t * 0.6)
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=mix(bgc, acc, 0.85))
    elif v["shape"] == "bars":
        for i in range(4):
            x = W * 0.08 + i * 22
            hgt = H * (0.12 + 0.05 * math.sin(t * 2 + i))
            dr.rectangle([x, H * 0.9 - hgt, x + 12, H * 0.9], fill=acc)
    elif v["shape"] == "dots":
        for i in range(6):
            for j in range(6):
                dr.ellipse([W * 0.7 + i * 16, H * 0.08 + j * 16 + 3 * math.sin(t * 2 + i + j),
                            W * 0.7 + i * 16 + 5, H * 0.08 + j * 16 + 5 + 3 * math.sin(t * 2 + i + j)], fill=acc)
    else:
        k = ease_out(t / 0.7)
        dr.polygon([(W, H), (W - W * 0.5 * k, H), (W, H - W * 0.5 * k)], fill=acc)
    if ctx.caption:
        font = ctx.font_big(int(W * 0.1))
        lines = wrap(ctx.caption, font, W * 0.8, dr)
        lh = int(font.size * 1.18)
        y0 = int(H * v["pos"]) - len(lines) * lh // 2
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        words_total = sum(len(l.split()) for l in lines)
        shown_words = words_total * ease_out(t / 0.8) if v["enter"] == "words" else words_total
        n = 0
        for i, l in enumerate(lines):
            lw = ld.textlength(l, font=font)
            x = W * 0.1 if v["align"] == "left" else (W - lw) / 2
            if v["enter"] == "words":
                ws = l.split()
                k = max(0, min(len(ws), int(shown_words - n + 0.999)))
                n += len(ws)
                l = " ".join(ws[:k])
            ld.text((x, y0 + i * lh), l, font=font, fill=fg + (255,))
        if v["enter"] == "wipe":
            k = ease_out(t / 0.6)
            mask = Image.new("L", (W, H), 0)
            ImageDraw.Draw(mask).rectangle([0, 0, int(W * k), H], fill=255)
            layer.putalpha(Image.composite(layer.split()[3], Image.new("L", (W, H), 0), mask))
            img.paste(layer, (0, 0), layer)
        elif v["enter"] == "rise":
            dy = int((1 - ease_out(t / 0.6)) * 40)
            a = layer.split()[3].point(lambda p: int(p * min(1.0, t / 0.4)))
            layer.putalpha(a)
            img.paste(layer, (0, dy), layer)
        else:
            img.paste(layer, (0, 0), layer)
        bx = W * 0.1 if v["align"] == "left" else W * 0.35
        dr.rectangle([bx, y0 + len(lines) * lh + 10, bx + W * 0.3 * ease_out((t - 0.2) / 0.6), y0 + len(lines) * lh + 16],
                     fill=acc)
    return img.resize((ctx.W, ctx.H), Image.BICUBIC)


# =========================================================================== #
# driver
# =========================================================================== #
PALETTES = [
    [(217, 119, 87), (255, 196, 61), (92, 200, 255), (140, 110, 255), (60, 210, 140), (255, 90, 140)],
    [(255, 64, 129), (0, 229, 255), (255, 214, 0), (124, 77, 255), (0, 230, 118), (255, 145, 0)],
    [(239, 71, 111), (255, 209, 102), (6, 214, 160), (17, 138, 178), (7, 59, 76), (247, 140, 107)],
    [(38, 70, 83), (42, 157, 143), (233, 196, 106), (244, 162, 97), (231, 111, 81), (120, 90, 200)],
    [(255, 111, 97), (107, 91, 149), (136, 176, 75), (247, 202, 201), (146, 168, 209), (149, 82, 81)],
]
RENDER = {"pixel": (render_pixel, vary_pixel), "neon": (render_neon, vary_neon),
          "comic": (render_comic, vary_comic), "minimal": (render_minimal, vary_minimal)}


class Ctx:
    pass


def render_scene(style: str, scene: dict, data: dict, idx: int, total: int, d: float, fps: int,
                 W: int, H: int, voice: Path | None, out: Path) -> Path:
    seed = str(data.get("seed", data.get("title", "")))
    sh = int(hashlib.md5(f"{seed}|{style}".encode()).hexdigest(), 16)
    ctx = Ctx()
    ctx.W, ctx.H = W, H
    ctx.seed_int = (sh + idx * 7919) % (2 ** 31)
    rng = random.Random(f"{seed}|{style}|{idx}")
    ctx.palette = [_hex(c) for c in data["style_palette"]] if data.get("style_palette") else PALETTES[sh % len(PALETTES)]
    ctx.accent = ctx.palette[0]
    ctx.mascot = _hex(data.get("mascot_color", "#D97757"))
    v = scene.get("visual", {})
    ctx.caption = v.get("caption") or ""
    render_fn, vary_fn = RENDER[style]
    ctx.var = vary_fn(rng, idx, total, sh % 97)
    ctx.var.update(v.get("style_options", {}))  # pin any variant choice, e.g. {"bg": "space"}
    ctx.rms = voice_levels(voice, d, fps)
    ctx.cache = {}
    ctx.font_pixel = _font("DejaVuSansMono-Bold.ttf", 16)
    fonts = {}
    ctx.font_big = lambda size: fonts.setdefault(size, _font("DejaVuSans-Bold.ttf", size))
    out.parent.mkdir(parents=True, exist_ok=True)
    n = int(round(d * fps)) + 2
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
         str(out)], stdin=subprocess.PIPE)
    for f in range(n):
        proc.stdin.write(render_fn(ctx, f / fps, f).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed while rendering style '{style}'")
    return out
