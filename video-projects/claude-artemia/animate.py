#!/usr/bin/env python3
"""3D pixel (voxel) animation for "Клод Код и Артемия".

Renders clips/scene_XX.mp4 at the exact scene lengths from storyboard.json
(run `vf.py tts` first so narration lengths are known), with lip-sync driven
by the narration loudness. Then `vf.py sfx` + `vf.py render` assemble the film.
"""
from __future__ import annotations

import json
import math
import random
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / ".claude/skills/video-forge/scripts"))
from vf import LEAD_IN, scene_duration  # noqa: E402

W, H, UP, FPS = 270, 480, 4, 24
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11)
FONT_BIG = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)

# --------------------------------------------------------------------------- #
# sprites
# --------------------------------------------------------------------------- #
CLAUDE = [
    ".ooooooooo.",
    ".ooooooooo.",
    "oo#ooooo#oo",
    "ooooooooooo",
    ".ooooooooo.",
    ".ooooooooo.",
    ".o.o...o.o.",
    ".o.o...o.o.",
]
CLAUDE_BLINK = [r.replace("#", "o") if i == 2 else r for i, r in enumerate(CLAUDE)]
CLAUDE_WALK = CLAUDE[:6] + ["o..o...o..o", "o..o...o..o"]

ARTEMIA = [
    "...hhhhhh...",
    "..hhhhhhhh..",
    ".hhhhhhhhhh.",
    ".hhhssssshh.",
    ".hssssssssh.",
    ".hseessees.h"[:12],
    ".hssssssssh.",
    ".hsssmmsssh.",
    ".hhssssssshh"[:12],
    ".hh.ssss.hh.",
    ".htttttttth.",
    "tttttttttttt",
    "tttttttttttt",
    "sttttottttts",
    "s.tttttttt.s",
    "s.tttttttt.s",
    "..kkkkkkkk..",
    "..jjjjjjjj..",
    "..jjj..jjj..",
    "..jjj..jjj..",
    "..jjj..jjj..",
    "..jjj..jjj..",
    ".wwww..wwww.",
]
ARTEMIA[5] = ".hseesseesh."


def artemia(mouth: str = "closed", eyes: str = "normal", arms: str = "down") -> list[str]:
    g = [list(r) for r in ARTEMIA]
    if mouth == "open":
        g[7] = list(".hssMMMMssh.")
        g[8] = list(".hhssMMsshh.")
    elif mouth == "O":
        g[7] = list(".hssMMMMssh.")
        g[8] = list(".hhsMMMMshh.")
    elif mouth == "smile":
        g[7] = list(".hsmssssmsh.")
        g[8] = list(".hhsmmmmshh.")
    if eyes == "wide":
        g[4] = list(".hseessees.h")
        g[4][11] = "."
        g[4] = list(".hseesseesh.")
    elif eyes == "blink":
        g[5] = list(".hssssssssh.")
        g[6] = list(".heesseessh.")
    if arms == "up":  # hands raised (surprise)
        for r in (13, 14, 15):
            g[r][0] = "."
            g[r][11] = "."
        for r in (9, 10, 11, 12):
            g[r][0] = "s" if r < 11 else "t"
            g[r][11] = "s" if r < 11 else "t"
    return ["".join(r) for r in g]


DINO_A = [
    "...........gggggg...",
    "..........ggEggggg..",
    "..........gggggggg..",
    "..........gggwwwww..",
    "..........gggg......",
    "g........gggggg.....",
    "gg......gggggggg....",
    "ggg....ggggggggg....",
    ".gggggggggggggggg...",
    "..ggggggggggggg.g...",
    "...gggggggggggg.....",
    "....gggggggggg......",
    ".....gg....gg.......",
    ".....gg....gg.......",
    "....ggg...ggg.......",
]
DINO_B = DINO_A[:12] + [
    "......gg..gg........",
    "......gg..gg........",
    ".....ggg.ggg........",
]
DINO_ROAR = [
    "...........gggggg...",
    "..........ggEggggg..",
    "..........gggggggg..",
    "..........gggw......",
    "..........ggg.......",
    "g........gggwwwww...",
] + DINO_A[6:]

CAT_A = [
    "..........c.c.",
    "..........cccc",
    "c.........cEcc",
    ".c........cccp",
    "..cccccccccc..",
    "..cwcccccccc..",
    "..cccccccccc..",
    ".c.c.....c.c..",
    "c...c...c...c.",
]
CAT_B = CAT_A[:7] + [
    "...cc....cc...",
    "...cc....cc...",
]
CACTUS = [
    "..G..",
    ".GG..",
    ".GG.G",
    "GGG.G",
    "GGGGG",
    ".GGG.",
    "..G..",
    "..G..",
    "..G..",
]

PAL = {
    "o": (217, 119, 87), "#": (20, 20, 20),
    "h": (255, 122, 26), "s": (242, 194, 155), "e": (30, 28, 46), "m": (190, 80, 85),
    "M": (90, 20, 30), "t": (28, 28, 32), "k": (60, 50, 40), "j": (59, 108, 181),
    "w": (240, 240, 240), "g": (88, 160, 72), "E": (250, 220, 40), "c": (140, 140, 150),
    "p": (240, 140, 160), "G": (70, 150, 70),
}


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def voxel(img: Image.Image, grid: list[str], x: float, y: float, b: int, d: int | None = None,
          flip: bool = False, pal: dict | None = None, alpha_dim: float = 1.0) -> None:
    """Draw a sprite as extruded cubes: front face + lit top + shaded right side."""
    pal = pal or PAL
    d = b // 2 if d is None else d
    dr = ImageDraw.Draw(img)
    rows = [r[::-1] if flip else r for r in grid]
    x, y = int(round(x)), int(round(y))

    def filled(cx, cy):
        return 0 <= cy < len(rows) and 0 <= cx < len(rows[cy]) and rows[cy][cx] != "."

    cells = [(cx, cy, ch) for cy, r in enumerate(rows) for cx, ch in enumerate(r) if ch != "."]
    for cx, cy, ch in cells:  # faces first
        c = shade(pal[ch], alpha_dim)
        px, py = x + cx * b, y + cy * b
        if d and not filled(cx, cy - 1):
            dr.polygon([(px, py), (px + d, py - d), (px + b + d - 1, py - d), (px + b - 1, py)], fill=shade(c, 1.3))
        if d and not filled(cx + 1, cy):
            dr.polygon([(px + b - 1, py), (px + b + d - 1, py - d), (px + b + d - 1, py + b - d - 1),
                        (px + b - 1, py + b - 1)], fill=shade(c, 0.6))
    for cx, cy, ch in cells:  # fronts
        c = shade(pal[ch], alpha_dim)
        px, py = x + cx * b, y + cy * b
        dr.rectangle([px, py, px + b - 1, py + b - 1], fill=c)


def shadow(img, cx, y, w):
    dr = ImageDraw.Draw(img, "RGBA")
    dr.ellipse([cx - w // 2, y - 3, cx + w // 2, y + 3], fill=(0, 0, 0, 70))


def vgrad(img, top, bottom, y0=0, y1=H, step=4):
    dr = ImageDraw.Draw(img)
    for y in range(y0, y1, step):
        f = (y - y0) / max(1, y1 - y0)
        dr.rectangle([0, y, W, y + step], fill=tuple(int(a + (b - a) * f) for a, b in zip(top, bottom)))


def bubble(img, text_lines, x, y, tail_x, tail_y, progress=1.0):
    """Pixel speech bubble with a type-on effect (progress 0..1 of characters)."""
    total = sum(len(l) for l in text_lines)
    shown = int(total * max(0.0, min(1.0, progress)) + 0.999)
    dr = ImageDraw.Draw(img)
    dr.fontmode = "1"
    lw = max(dr.textlength(l, font=FONT) for l in text_lines)
    bw, bh = int(lw) + 14, len(text_lines) * 14 + 10
    x = max(4, min(W - bw - 4, x - bw // 2))
    dr.rectangle([x + 3, y + 3, x + bw + 3, y + bh + 3], fill=(0, 0, 0))
    dr.rectangle([x, y, x + bw, y + bh], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    tx = min(max(tail_x, x + 8), x + bw - 8)
    dr.polygon([(tx - 5, y + bh - 1), (tx + 5, y + bh - 1), (tail_x, tail_y)], fill=(255, 255, 255), outline=(0, 0, 0))
    dr.line([(tx - 4, y + bh - 1), (tx + 4, y + bh - 1)], fill=(255, 255, 255), width=2)
    left = shown
    for i, l in enumerate(text_lines):
        part = l[:max(0, left)]
        left -= len(l)
        dr.text((x + 7, y + 5 + i * 14), part, font=FONT, fill=(20, 20, 20))


def name_tag(img, text, x, y, color):
    dr = ImageDraw.Draw(img)
    dr.fontmode = "1"
    w = int(dr.textlength(text, font=FONT)) + 8
    dr.rectangle([x - w // 2, y, x + w // 2, y + 14], fill=color)
    dr.text((x - w // 2 + 4, y + 1), text, font=FONT, fill=(255, 255, 255))


def stars(img, t, seed=1, n=60, ymax=H):
    rnd = random.Random(seed)
    dr = ImageDraw.Draw(img)
    for i in range(n):
        x, y = rnd.randrange(W), rnd.randrange(ymax)
        tw = 0.5 + 0.5 * math.sin(t * 3 + i)
        c = int(120 + 135 * tw)
        dr.rectangle([x, y, x + 1, y + 1], fill=(c, c, min(255, c + 30)))


def flash(img, a):
    if a <= 0:
        return img
    return Image.blend(img, Image.new("RGB", img.size, (255, 255, 255)), min(1.0, a))


def fade_black(img, a):
    if a <= 0:
        return img
    return Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), min(1.0, a))


def shake(img, amt):
    if amt <= 0:
        return img
    dx, dy = random.randint(-amt, amt), random.randint(-amt, amt)
    out = img.copy()  # keep edges filled instead of black bars
    out.paste(img, (dx, dy))
    return out


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


# --------------------------------------------------------------------------- #
# backgrounds
# --------------------------------------------------------------------------- #
def bg_room(img, t):
    vgrad(img, (27, 22, 64), (52, 40, 110), 0, 340)
    dr = ImageDraw.Draw(img)
    # window with stars
    dr.rectangle([150, 50, 250, 140], fill=(10, 12, 40), outline=(90, 80, 160), width=3)
    rnd = random.Random(3)
    for i in range(14):
        x, y = rnd.randrange(155, 245), rnd.randrange(55, 135)
        c = int(150 + 100 * (0.5 + 0.5 * math.sin(t * 4 + i)))
        dr.rectangle([x, y, x, y], fill=(c, c, c))
    dr.line([(200, 50), (200, 140)], fill=(90, 80, 160), width=2)
    dr.line([(150, 95), (250, 95)], fill=(90, 80, 160), width=2)
    # desk + monitor with a terminal prompt
    voxel(img, ["dddddddddddd", ".d........d.", ".d........d.", ".d........d."], 14, 250, 6, 3,
          pal={"d": (110, 80, 60)})
    dr.rectangle([28, 196, 98, 246], fill=(18, 18, 24), outline=(70, 70, 90), width=3)
    dr.fontmode = "1"
    dr.text((34, 202), "> claude", font=FONT, fill=(217, 119, 87))
    if int(t * 2) % 2 == 0:
        dr.rectangle([34, 222, 40, 232], fill=(217, 119, 87))
    # floor
    for row in range(0, 160, 10):
        for col in range(0, W, 20):
            c = (60, 48, 110) if ((row // 10) + (col // 20)) % 2 == 0 else (48, 38, 92)
            dr.rectangle([col, 340 + row, col + 19, 340 + row + 9], fill=c)


def bg_desert(img, t, sky=((255, 170, 90), (255, 225, 160)), sun=(255, 240, 180), scroll=0.0, cacti=True):
    vgrad(img, sky[0], sky[1], 0, 300)
    dr = ImageDraw.Draw(img)
    cx, cy, r = 195, 95, 26
    for y in range(-r, r + 1, 4):
        for x in range(-r, r + 1, 4):
            if x * x + y * y <= r * r:
                dr.rectangle([cx + x, cy + y, cx + x + 3, cy + y + 3], fill=sun)
    layers = [(250, 18, 0.010, (232, 160, 90), 0.3), (300, 14, 0.016, (240, 185, 110), 0.6),
              (350, 10, 0.022, (247, 205, 135), 1.0)]
    for base, amp, freq, col, par in layers:
        for x in range(0, W, 3):
            y = base + amp * math.sin((x + scroll * 40 * par) * freq * 6.28 / 3 + par * 5)
            dr.rectangle([x, int(y) // 3 * 3, x + 2, H], fill=col)
    if cacti:
        for i, (cx0, cy0, b) in enumerate([(30, 268, 4), (230, 300, 5), (120, 245, 3)]):
            voxel(img, CACTUS, cx0 - scroll * 12 * (b / 5), cy0, b)


# --------------------------------------------------------------------------- #
# scenes  (each returns a W x H RGB image for time t)
# --------------------------------------------------------------------------- #
class Ctx:
    def __init__(self, scene, project):
        self.d = scene_duration(scene)
        self.vd = float(scene.get("voice_duration") or 0)
        self.rms = np.zeros(int(self.d * FPS) + 2)
        if scene.get("voice_file"):
            with wave.open(str(project / scene["voice_file"])) as w:
                sr = w.getframerate()
                a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
            hop = sr // FPS
            off = int(LEAD_IN * FPS)
            for i in range(len(a) // hop):
                if off + i < len(self.rms):
                    self.rms[off + i] = float(np.sqrt(np.mean(a[i * hop:(i + 1) * hop] ** 2)))
            if self.rms.max() > 0:
                self.rms /= self.rms.max()

    def talk(self, f):
        return self.rms[min(f, len(self.rms) - 1)]

    def speech_progress(self, t):
        return (t - LEAD_IN) / max(0.1, self.vd * 0.9)


def scene1(t, f, c: Ctx):
    img = Image.new("RGB", (W, H))
    bg_room(img, t)
    lvl = c.talk(f)
    hop = abs(math.sin(t * 9)) * 10 * lvl
    pop_in = ease_out(t / 0.35)
    cy = 352 - 8 * 6 - hop
    shadow(img, 40 + 33, 356, 60)
    grid = CLAUDE_BLINK if (t % 2.6) > 2.45 else CLAUDE
    voxel(img, grid, 40, cy + (1 - pop_in) * 60, 6)
    shadow(img, 170 + 36, 356, 64)
    blink = (t % 3.1) > 2.95
    voxel(img, artemia(eyes="blink" if blink else "normal"), 170, 352 - 23 * 6 + math.sin(t * 2) * 1.2, 6)
    name_tag(img, "Клод Код", 73, 362, (217, 119, 87))
    name_tag(img, "Артемия", 206, 362, (200, 90, 20))
    if t > LEAD_IN - 0.1:
        bubble(img, ["Эй! Хочешь, чтобы я", "протестировал видео", "и мои навыки?"], 84, 226, 74, 300,
               c.speech_progress(t))
    return img


def scene2(t, f, c: Ctx):
    img = Image.new("RGB", (W, H))
    bg_room(img, t)
    lvl = c.talk(f)
    # portal opens from 1.2s, swallows heroes 2.2..2.9s, white flash at the end
    p_open = ease_out((t - 1.2) / 0.8)
    suck = max(0.0, min(1.0, (t - 2.2) / 0.7))
    dr = ImageDraw.Draw(img)
    pcx, pcy = 135, 250
    if p_open > 0:
        rmax = 70 * p_open
        for k in range(10, 0, -1):
            r = rmax * k / 10
            hue = (k * 37 + t * 400) % 360
            col = tuple(int(150 + 100 * math.sin(math.radians(hue + o))) for o in (0, 120, 240))
            dr.ellipse([pcx - r, pcy - r * 1.3, pcx + r, pcy + r * 1.3], outline=col, width=4)
        rnd = random.Random(int(t * 24))
        for _ in range(30):
            a = rnd.uniform(0, 6.28)
            rr = rnd.uniform(0, rmax)
            x, y = pcx + math.cos(a + t * 5) * rr, pcy + math.sin(a + t * 5) * rr * 1.3
            dr.rectangle([x, y, x + 2, y + 2], fill=(255, 255, 255))

    def pull(x, y):
        return x + (pcx - x) * suck, y + (pcy - y) * suck

    cx, cy = pull(40, 352 - 48 + math.sin(t * 7) * 2)
    b = max(1, int(round(6 * (1 - suck))))
    if b > 0 and suck < 0.97:
        voxel(img, CLAUDE, cx, cy, b)
        mouth = "open" if lvl > 0.25 else "smile"
        ax, ay = pull(170, 352 - 138)
        voxel(img, artemia(mouth=mouth, arms="up" if 0.3 < t < 1.2 else "down"), ax, ay, b)
    if t < 1.2:
        name_tag(img, "Артемия", 206, 362, (200, 90, 20))
        if t > LEAD_IN - 0.1:
            bubble(img, ["Давай!"], 206, 160, 206, 208, c.speech_progress(t))
    img = flash(img, (t - (c.d - 0.45)) / 0.45)
    return img


def scene3(t, f, c: Ctx):
    img = Image.new("RGB", (W, H))
    bg_desert(img, t, scroll=t)
    land = 0.75
    groundy = 420
    for (gx, grid, b, delay) in [(60, CLAUDE, 5, 0.0), (160, None, 5, 0.12)]:
        tt = t - delay
        fall = min(1.0, max(0.0, tt / land))
        hgt = 8 * b if grid else 23 * b
        y = groundy - hgt - (1 - fall ** 2) * 500
        if tt > land:  # bounce
            y -= abs(math.sin((tt - land) * 9)) * 14 * math.exp(-(tt - land) * 4)
        shadow(img, gx + (55 if grid else 30), groundy + 2, 50)
        if grid:
            voxel(img, CLAUDE_WALK if tt > 1.6 and int(tt * 6) % 2 else CLAUDE, gx, y, b)
        else:
            look = tt > 2.2 and int(tt) % 2 == 0
            voxel(img, artemia(mouth="O" if 1.0 < tt < 1.8 else "closed"), gx, y, b, flip=look)
    # landing dust
    if land < t < land + 0.8:
        dr = ImageDraw.Draw(img)
        k = (t - land) / 0.8
        for i in range(14):
            a = i / 14 * math.pi
            r = 10 + 60 * k
            x, y = 135 + math.cos(a) * r * (1.6 if i % 2 else 1), groundy - math.sin(a) * r * 0.3
            s = int(6 * (1 - k)) + 1
            dr.rectangle([x, y, x + s, y + s], fill=(250, 220, 170))
    img = shake(img, 3 if land < t < land + 0.2 else 0)
    img = flash(img, 1 - t / 0.35)
    return fade_black(img, (t - (c.d - 0.3)) / 0.3)


def scene4(t, f, c: Ctx):
    img = Image.new("RGB", (W, H))
    vgrad(img, (5, 8, 30), (20, 10, 50))
    stars(img, t, seed=7, n=80)
    dr = ImageDraw.Draw(img)
    for r in range(150, 0, -15):  # soft glow
        g = int(18 * (1 - r / 150))
        dr.ellipse([135 - r, 240 - r, 135 + r, 240 + r], fill=(5 + g, 8 + g, 30 + g * 2))
    pairs = [((255, 90, 90), (90, 200, 255)), ((255, 210, 60), (120, 230, 120))]
    items = []
    n = 20
    spin = t * 2.2
    for i in range(n):
        y = 45 + i * 20.5
        ph = spin + i * 0.42
        x1, z1 = math.sin(ph), math.cos(ph)
        cola, colb = pairs[i % 2]
        for k in range(1, 8):  # rung
            u = k / 8
            x = x1 * (1 - 2 * u)
            z = z1 * (1 - 2 * u)
            items.append((z, 135 + x * 80, y, 6, cola if u < 0.5 else colb))
        items.append((z1, 135 + x1 * 80, y, 12, (120, 200, 255)))
        items.append((-z1, 135 - x1 * 80, y, 12, (255, 130, 200)))
    for z, x, y, s, col in sorted(items):
        sz = int(s * (0.75 + 0.35 * (z + 1) / 2))
        lit = 0.55 + 0.45 * (z + 1) / 2
        g = [ "x" ]
        voxel(img, g, x - sz / 2, y - sz / 2, sz, max(1, sz // 3), pal={"x": shade(col, lit)})
    img = fade_black(img, 1 - t / 0.35)
    return fade_black(img, (t - (c.d - 0.3)) / 0.3)


def scene5(t, f, c: Ctx):
    img = Image.new("RGB", (W, H))
    bg_desert(img, t, sky=((240, 120, 90), (255, 200, 140)), sun=(255, 220, 150), cacti=False)
    groundy = 430
    # rock + hiding heroes on the right
    peek = 4 * math.sin(t * 3)
    voxel(img, artemia(mouth="O", eyes="normal"), 205, groundy - 23 * 3 - 18 + max(0, peek), 3)
    voxel(img, CLAUDE, 236, groundy - 24 - 14 + max(0, -peek), 3)
    voxel(img, ["..rrrrr...", ".rrrrrrrr.", "rrrrrrrrrr", "rrrrrrrrrr"], 196, groundy - 26, 7,
          pal={"r": (150, 110, 90)})
    # dino walks left -> right (steps every 0.6s, roar at 2.1..3.0)
    step = int((t + 0.0) / 0.6)
    roaring = 2.1 < t < 3.0
    x = -150 + (t if t < 2.1 else 2.1 + max(0, t - 3.0)) * 62
    bob = 3 if (t % 0.6) < 0.3 else 0
    grid = DINO_ROAR if roaring else (DINO_A if step % 2 == 0 else DINO_B)
    shadow(img, x + 75, groundy + 2, 120)
    voxel(img, grid, x, groundy - 15 * 7 - bob, 7)
    st = t % 0.6
    amt = 4 if (st > 0.27 and st < 0.42 and not roaring) else (3 if roaring else 0)
    if roaring:
        dr = ImageDraw.Draw(img)
        for k in range(3):
            r = 20 + ((t - 2.1) * 120 + k * 25) % 75
            hx, hy = x + 135, groundy - 15 * 7 + 30
            dr.arc([hx - r, hy - r, hx + r, hy + r], -40, 40, fill=(255, 255, 255), width=2)
    return fade_black(shake(img, amt), (t - (c.d - 0.25)) / 0.25)


def scene6(t, f, c: Ctx):
    img = Image.new("RGB", (W, H))
    bg_desert(img, t, sky=((120, 170, 255), (255, 220, 170)), sun=(255, 250, 210), scroll=t * 0.3)
    groundy = 430
    turn = t > 1.25
    voxel(img, artemia(mouth="O" if t > 1.0 else "closed"), 175, groundy - 23 * 4, 4, flip=turn)
    voxel(img, CLAUDE, 120, groundy - 8 * 4 - abs(math.sin(t * 10)) * 4, 4, flip=turn)
    cx = -80 + t * 190
    grid = CAT_A if int(t * 14) % 2 == 0 else CAT_B
    dr = ImageDraw.Draw(img)
    for i in range(6):  # speed lines + dust
        ly = groundy - 40 + i * 6
        dr.line([(cx - 40 - i * 7, ly), (cx - 8, ly)], fill=(255, 255, 255), width=1)
        dx = cx - 10 - i * 12
        s = max(1, 6 - i)
        dr.rectangle([dx, groundy - s, dx + s, groundy], fill=(250, 225, 180))
    voxel(img, grid, cx, groundy - 9 * 5 - (3 if grid is CAT_A else 0), 5)
    return fade_black(img, (t - (c.d - 0.2)) / 0.2)


def scene7(t, f, c: Ctx):
    big = Image.new("RGB", (W, H))
    bg_desert(big, t, sky=((90, 60, 140), (255, 150, 110)), sun=(255, 200, 120), cacti=True)
    lvl = c.talk(f)
    # tiny cat zooming by in the background
    bx = -40 + (t % 3.4) * 140
    voxel(big, CAT_A if int(t * 14) % 2 else CAT_B, bx, 300, 2)
    mouth = "O" if lvl > 0.15 else ("O" if t < LEAD_IN else "smile")
    voxel(big, artemia(mouth=mouth, eyes="normal", arms="up" if t > 0.2 else "down"), 75, 470 - 23 * 10, 10)
    voxel(big, CLAUDE, 12, 470 - 8 * 4 - abs(math.sin(t * 8)) * 18, 4)
    dr = ImageDraw.Draw(big)
    dr.fontmode = "1"
    if t > 0.25:  # surprise marks
        for k, (mx, my) in enumerate([(70, 205), (200, 195), (225, 225)]):
            if int(t * 6 + k) % 3:
                dr.text((mx, my), "!", font=FONT_BIG, fill=(255, 255, 255))
    if t > LEAD_IN - 0.1:
        bubble(big, ["Ни фига себе!"], 135, 186, 140, 236, c.speech_progress(t))
    # slow push-in
    z = 1 + 0.08 * ease_out(t / c.d)
    cw, ch = int(W / z), int(H / z)
    img = big.crop(((W - cw) // 2, (H - ch) // 2, (W - cw) // 2 + cw, (H - ch) // 2 + ch)).resize((W, H), Image.NEAREST)
    img = shake(img, 2 if 0.25 < t < 0.45 else 0)
    return fade_black(img, (t - (c.d - 0.6)) / 0.6)


SCENES = [scene1, scene2, scene3, scene4, scene5, scene6, scene7]


def render(idx: int, scene: dict, project: Path) -> None:
    c = Ctx(scene, project)
    out = project / scene["visual"]["source"]
    out.parent.mkdir(parents=True, exist_ok=True)
    n = int(round(c.d * FPS)) + 2
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W * UP}x{H * UP}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
         str(out)], stdin=subprocess.PIPE)
    random.seed(idx)
    for f in range(n):
        img = SCENES[idx](f / FPS, f, c).resize((W * UP, H * UP), Image.NEAREST)
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"  clip {out.name}: {n / FPS:.2f}s")


def main():
    project = HERE
    data = json.loads((project / "storyboard.json").read_text(encoding="utf-8"))
    only = {int(x) for x in sys.argv[1].split(",")} if len(sys.argv) > 1 else None
    for i, s in enumerate(data["scenes"]):
        if only and i + 1 not in only:
            continue
        render(i, s, project)


if __name__ == "__main__":
    main()
