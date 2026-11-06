#!/usr/bin/env python3
"""Встроенный генератор видео «Ии Матвей ТТ».

Сам строит кадры (сцены с анимированным фоном, частицами, подписью и
персонажем), склеивает их с плавными переходами и кодирует в mp4 через
ffmpeg. Качество до 4K, длительность до 30 секунд, звук по желанию.

Использование: render.py '<json-конфиг>'
Прогресс печатается строками вида  PROGRESS 0.42
"""
import hashlib
import json
import math
import random
import re
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FPS = 24
XFADE = 0.7  # секунд на переход между сценами


def hsv(h, s, v):
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    r, g, b = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i % 6]
    return np.array([r, g, b], dtype=np.float32)


class Scene:
    def __init__(self, idx, caption, rng, w, h):
        self.idx, self.caption, self.w, self.h = idx, caption, w, h
        base = rng.random()
        self.cols = [hsv(base + k * 0.18, 0.75, 0.95 - 0.2 * k) for k in range(3)]
        self.freq = [rng.uniform(1.5, 4.0) for _ in range(4)]
        self.speed = [rng.uniform(0.2, 0.7) for _ in range(3)]
        n = rng.randint(18, 34)
        self.parts = [
            dict(x=rng.random(), y=rng.random(), r=rng.uniform(0.01, 0.05),
                 vx=rng.uniform(-0.05, 0.05), vy=rng.uniform(-0.12, -0.02),
                 ph=rng.random() * 6.28, a=rng.randint(60, 150))
            for _ in range(n)
        ]
        self.motion = rng.choice(["orbit", "zoom", "sweep"])
        sw, sh = 160, int(160 * h / w) or 90
        yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        self.gx, self.gy = xx / sw, yy / sh

    def background(self, t):
        gx, gy, f, s = self.gx, self.gy, self.freq, self.speed
        a = np.sin(gx * f[0] * 3 + t * s[0] * 3) + np.sin(gy * f[1] * 3 - t * s[1] * 3)
        b = np.sin((gx + gy) * f[2] * 2 + t * s[2] * 2)
        c = np.sin(np.hypot(gx - 0.5, gy - 0.5) * f[3] * 6 - t * 1.4)
        m = (a + b + c) / 6 + 0.5
        m = np.clip(m, 0, 1)[..., None]
        k = (np.sin(gx * 3 + t * 0.3)[..., None] * 0.5 + 0.5)
        col = (self.cols[0] * (1 - m) + self.cols[1] * m) * (1 - k * 0.4) + self.cols[2] * k * 0.4
        col = np.clip(col * 255, 0, 255).astype(np.uint8)
        return Image.fromarray(col).resize((self.w, self.h), Image.BICUBIC)

    def frame(self, t, dur, font, char):
        w, h = self.w, self.h
        img = self.background(t)
        over = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        for p in self.parts:
            x = ((p["x"] + p["vx"] * t) % 1.0) * w
            y = ((p["y"] + p["vy"] * t) % 1.0) * h
            r = p["r"] * min(w, h) * (1 + 0.25 * math.sin(t * 2 + p["ph"]))
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, p["a"]))
        over = over.filter(ImageFilter.GaussianBlur(max(1, w // 400)))
        img = Image.alpha_composite(img.convert("RGBA"), over)

        prog = t / max(dur, 0.01)
        if char is not None:
            ch_h = h * (0.55 + 0.05 * math.sin(t * 2))
            if self.motion == "zoom":
                ch_h *= 0.8 + 0.4 * prog
            sc = ch_h / char.height
            c = char.resize((max(1, int(char.width * sc)), max(1, int(ch_h))), Image.BICUBIC)
            if self.motion == "orbit":
                cx = w * (0.5 + 0.18 * math.cos(t * 0.9))
                cy = h * (0.5 + 0.06 * math.sin(t * 1.8))
            elif self.motion == "sweep":
                cx = w * (0.2 + 0.6 * prog)
                cy = h * (0.5 + 0.05 * math.sin(t * 3))
            else:
                cx, cy = w * 0.5, h * 0.5 + h * 0.03 * math.sin(t * 2)
            angle = 4 * math.sin(t * 1.3)
            c = c.rotate(angle, expand=True, resample=Image.BICUBIC)
            shadow = Image.new("RGBA", c.size, (0, 0, 0, 0))
            shadow.putalpha(c.getchannel("A").point(lambda v: v * 0.35))
            img.alpha_composite(shadow, (int(cx - c.width / 2 + 8), int(cy - c.height / 2 + 12)))
            img.alpha_composite(c, (int(cx - c.width / 2), int(cy - c.height / 2)))

        # подпись сцены
        if self.caption:
            alpha = min(1.0, t / 0.6, max(0.0, (dur - t) / 0.6))
            tx = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            td = ImageDraw.Draw(tx)
            lines = wrap(self.caption, font, td, w * 0.86)
            lh = font.size * 1.25
            y0 = h - lh * len(lines) - h * 0.07 - (1 - alpha) * 20
            for i, ln in enumerate(lines):
                tw = td.textlength(ln, font=font)
                x = (w - tw) / 2
                y = y0 + i * lh
                td.text((x + 2, y + 3), ln, font=font, fill=(0, 0, 0, int(160 * alpha)))
                td.text((x, y), ln, font=font, fill=(255, 255, 255, int(255 * alpha)))
            img = Image.alpha_composite(img, tx)
        return img.convert("RGB")


def wrap(text, font, d, maxw):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=font) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines[:3]


def split_captions(prompt, n):
    parts = [p.strip() for p in re.split(r"[.!?;\n]+", prompt) if p.strip()]
    if not parts:
        parts = [prompt.strip()]
    while len(parts) < n:  # режем длинные фразы по словам
        parts.sort(key=len, reverse=True)
        words = parts[0].split()
        if len(words) < 4:
            break
        mid = len(words) // 2
        parts[0:1] = [" ".join(words[:mid]), " ".join(words[mid:])]
    if len(parts) > n:
        k = len(parts) / n
        parts = [" ".join(parts[int(i * k):int((i + 1) * k)]) for i in range(n)]
    out = []
    for i in range(n):
        out.append(parts[i % len(parts)] if parts else "")
    return out


def audio_filter(seed, dur):
    rng = random.Random(seed)
    root = rng.choice([110.0, 123.47, 130.81, 146.83, 164.81])
    ratios = rng.choice([[1, 1.2, 1.5, 2], [1, 1.25, 1.5, 1.875], [1, 1.125, 1.5, 2.25]])
    parts = []
    for i, r in enumerate(ratios):
        f = root * r * (2 if i > 1 else 1)
        lfo = rng.uniform(0.1, 0.4)
        parts.append(f"0.11*sin(2*PI*{f:.2f}*t)*(0.65+0.35*sin(2*PI*{lfo:.2f}*t+{i}))")
    expr = "+".join(parts)
    fade = min(1.5, dur / 4)
    return (f"aevalsrc={expr}|{expr}:s=44100:d={dur}",
            f"afade=t=in:d={fade},afade=t=out:st={max(0, dur - fade):.2f}:d={fade}")


def main():
    cfg = json.loads(sys.argv[1])
    prompt = cfg["prompt"]
    dur = max(1, min(30, float(cfg["duration"])))
    out_h = int(cfg["height"])
    vertical = cfg.get("aspect") == "9:16"
    out_w = int(round(out_h * 9 / 16 / 2)) * 2 if vertical else int(round(out_h * 16 / 9 / 2)) * 2
    out_h_even = out_h + (out_h % 2)
    ow, oh = (out_w, out_h_even)
    if vertical:
        w, h = 540, 960
    else:
        w, h = 960, 540

    seed = int(hashlib.sha256(prompt.encode()).hexdigest()[:12], 16) ^ int(cfg.get("seed", 0))
    rng = random.Random(seed)

    char = None
    if cfg.get("character"):
        try:
            char = Image.open(cfg["character"]).convert("RGBA")
            char.thumbnail((1200, 1200))
        except Exception as e:  # noqa: BLE001
            print(f"WARN не удалось открыть персонажа: {e}", flush=True)

    n_scenes = max(1, round(dur / 5))
    scene_len = dur / n_scenes
    caps = split_captions(prompt, n_scenes)
    scenes = [Scene(i, caps[i], rng, w, h) for i in range(n_scenes)]
    font = ImageFont.truetype(FONT, max(18, w // 24))

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-"]
    with_audio = bool(cfg.get("audio"))
    if with_audio:
        src, af = audio_filter(seed, dur)
        cmd += ["-f", "lavfi", "-i", src]
    cmd += ["-vf", f"scale={ow}:{oh}:flags=lanczos,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS)]
    if with_audio:
        cmd += ["-af", af, "-c:a", "aac", "-b:a", "160k", "-shortest"]
    cmd += ["-t", f"{dur}", "-movflags", "+faststart", cfg["out"]]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    total = int(dur * FPS)
    try:
        for fi in range(total):
            T = fi / FPS
            si = min(int(T // scene_len), n_scenes - 1)
            t = T - si * scene_len
            frame = scenes[si].frame(t, scene_len, font, char)
            if si + 1 < n_scenes and t > scene_len - XFADE:
                k = (t - (scene_len - XFADE)) / XFADE
                nxt = scenes[si + 1].frame(0.0, scene_len, font, char)
                frame = Image.blend(frame, nxt, k)
            ff.stdin.write(frame.tobytes())
            if fi % 6 == 0:
                print(f"PROGRESS {fi / total:.3f}", flush=True)
        ff.stdin.close()
    except BrokenPipeError:
        pass
    code = ff.wait()
    if code != 0:
        print("ERROR ffmpeg завершился с ошибкой", flush=True)
        sys.exit(1)
    print("PROGRESS 1.0", flush=True)


if __name__ == "__main__":
    main()
