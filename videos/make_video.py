import os, math, random, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS

OUT = os.path.dirname(os.path.abspath(__file__))
TTS = os.path.join(OUT, "tts")
os.makedirs(TTS, exist_ok=True)
SR = 44100
W, H, FPS = 1280, 720, 24
random.seed(7); np.random.seed(7)

# ---------------------------------------------------------------- voices
def tts(text, name, pitch=1.0, tempo=1.0):
    mp3 = os.path.join(TTS, name + ".mp3")
    if not os.path.exists(mp3):
        gTTS(text, lang="ru").save(mp3)
    af = f"asetrate={int(24000*pitch)},aresample={SR},atempo={max(0.5,min(2.0,tempo/pitch)):.4f}"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp3, "-af", af, "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.float32).copy()
    # trim silence
    idx = np.where(np.abs(a) > 0.02)[0]
    if len(idx):
        a = a[max(0, idx[0]-500): idx[-1]+2000]
    return a / (np.abs(a).max() + 1e-9)

def kid_chorus(n_kids):
    out = None
    for i in range(n_kids):
        p = [1.35, 1.5, 1.42, 1.6, 1.28, 1.55][i % 6]
        c = tts("Я вайбкодер!", "kid", pitch=p, tempo=1.25)
        off = int(SR * 0.04 * i)
        c = np.concatenate([np.zeros(off), c])
        if out is None:
            out = c
        else:
            L = max(len(out), len(c))
            out = np.pad(out, (0, L-len(out))) + np.pad(c, (0, L-len(c)))
    return out / np.abs(out).max()

narr = lambda text, name: tts(text, name, pitch=0.92, tempo=1.18)

# ---------------------------------------------------------------- SFX
def t_arr(d): return np.arange(int(SR*d)) / SR

def env(n, a=0.01, r=0.1):
    e = np.ones(n); na, nr = int(SR*a), int(SR*r)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e

def lowpass(x, k):
    return np.convolve(x, np.ones(k)/k, mode="same")

def sfx_chirp():
    t = t_arr(0.12)
    f = 3000 + 2500*np.sin(np.pi*t/0.12)
    return np.sin(2*np.pi*np.cumsum(f)/SR) * env(len(t), 0.005, 0.04) * 0.5

def sfx_flap():
    n = int(SR*0.08)
    return lowpass(np.random.randn(n), 20) * env(n, 0.005, 0.06) * 0.8

def sfx_birds(d=2.5):
    out = np.zeros(int(SR*d))
    for _ in range(14):
        s = sfx_chirp(); p = random.randint(0, len(out)-len(s)-1); out[p:p+len(s)] += s*random.uniform(.4, 1)
    for _ in range(30):
        s = sfx_flap(); p = random.randint(0, len(out)-len(s)-1); out[p:p+len(s)] += s*random.uniform(.3, .8)
    return out

def sfx_glass():
    out = np.zeros(int(SR*1.2))
    n = int(SR*0.15)
    out[:n] += np.random.randn(n) * env(n, 0.001, 0.14) * 0.9
    for _ in range(25):
        f = random.uniform(2500, 7000); d = random.uniform(.05, .3)
        t = t_arr(d); s = np.sin(2*np.pi*f*t) * np.exp(-t*18) * 0.25
        p = random.randint(0, len(out)-len(s)-1); out[p:p+len(s)] += s
    return out

def sfx_siren(d=3.0):
    t = t_arr(d)
    f = 750 + 250*np.sign(np.sin(2*np.pi*1.5*t))
    return np.sin(2*np.pi*np.cumsum(f)/SR) * 0.35 * env(len(t), 0.2, 0.4)

def sfx_whoosh(d=1.5, down=True):
    t = t_arr(d)
    f = np.linspace(1800, 200, len(t)) if down else np.linspace(200, 1800, len(t))
    tone = np.sin(2*np.pi*np.cumsum(f)/SR) * 0.3
    noise = lowpass(np.random.randn(len(t)), 6) * 0.4
    return (tone + noise) * np.sin(np.pi*t/d)

def sfx_dog():
    out = np.zeros(int(SR*2.0))
    for k in range(3):
        t = t_arr(0.6)
        f = 500 + 300*np.sin(np.pi*t/0.6)
        s = (np.sin(2*np.pi*np.cumsum(f)/SR) + 0.3*np.sin(4*np.pi*np.cumsum(f)/SR)) * env(len(t), .05, .3) * .35
        p = int(SR*0.6*k); out[p:p+len(s)] += s
    return out

def sfx_horn(d=0.6):
    t = t_arr(d)
    s = np.sign(np.sin(2*np.pi*330*t)) + np.sign(np.sin(2*np.pi*415*t))
    return lowpass(s, 8) * 0.25 * env(len(t), 0.01, 0.05)

def sfx_screech(d=2.4):
    t = t_arr(d)
    f = 1900 + 300*np.sin(2*np.pi*3*t) + 150*np.random.randn(len(t)).cumsum()/np.sqrt(np.arange(1, len(t)+1))
    s = np.sin(2*np.pi*np.cumsum(f)/SR) * 0.45 + np.random.randn(len(t))*0.12
    return s * env(len(t), 0.05, 0.2)

def sfx_crash():
    d = 2.8; t = t_arr(d)
    boom = np.sin(2*np.pi*np.cumsum(np.linspace(90, 30, len(t)))/SR) * np.exp(-t*2.5)
    noise = np.random.randn(len(t)) * np.exp(-t*3.5)
    metal = sum(np.sin(2*np.pi*f*t)*np.exp(-t*random.uniform(3, 6)) for f in [430, 620, 910, 1350, 1990]) * 0.15
    out = boom*0.9 + noise*0.7 + metal
    g = sfx_glass(); out[int(SR*.1):int(SR*.1)+len(g)] += g
    return out

def sfx_boing():
    t = t_arr(0.5)
    f = 300 + 200*np.sin(2*np.pi*12*t)*np.exp(-t*4)
    return np.sin(2*np.pi*np.cumsum(f)/SR) * env(len(t), .005, .1) * .4

# ---------------------------------------------------------------- timeline
STAGES = [
    (90,      "Девяносто децибел. Как газонокосилка. Водитель тяжело вздыхает.", None),
    (120,     "Сто двадцать децибел. Бабушка на остановке уронила пирожки.", "grandma"),
    (200,     "Двести децибел. Все птицы в округе улетели.", "birds"),
    (1000,    "Тысяча децибел! Трескаются стёкла, воют собаки.", "glass"),
    (10000,   "Десять тысяч децибел! Соседний город вызвал полицию.", "police"),
    (100000,  "Сто тысяч децибел! Спутники сбиваются с орбиты.", "satellite"),
    (1000000, "Миллион децибел!!! Луна просит сделать потише.", "moon"),
]

events = []   # (start, audio, gain, subtitle, speaker)
visual = []   # (start, name)
t = 0.5
intro = narr("Обычное утро. Дети едут в школу на автобусе.", "n_intro")
events.append((t, intro, 0.9, "Обычное утро. Дети едут в школу на автобусе.", "Рассказчик")); t += len(intro)/SR + 0.4

stage_times = []
for i, (db, line, vis) in enumerate(STAGES):
    stage_times.append(t)
    ch = kid_chorus(2 + i)
    drive = 1 + i*1.6
    ch = np.tanh(ch*drive) / np.tanh(drive)     # louder = more distorted
    gain = 0.30 + i*0.1
    events.append((t, ch, gain, "Я ВАЙБКОДЕР!" + "!"*i, "Дети"))
    t += len(ch)/SR + 0.15
    if vis: visual.append((t, vis))
    nl = narr(line, f"n_stage{i}")
    events.append((t, nl, 0.9, line, "Рассказчик"))
    t += len(nl)/SR + 0.3

drift_t = t + 0.2
driver = tts("Эль дрифта!", "driver", pitch=0.72, tempo=1.0)
events.append((drift_t, driver, 1.0, "ЭЛЬ ДРИФТА!", "Водитель"))
screech_t = drift_t + len(driver)/SR + 0.05
crash_t = screech_t + 2.4
outro_t = crash_t + 2.6
outro = narr("Все живы. Но вайбкод не сохранился.", "n_outro")
events.append((outro_t, outro, 0.9, "Все живы. Но вайбкод не сохранился.", "Рассказчик"))
end_t = outro_t + len(outro)/SR + 2.2
TOTAL = end_t
print("duration", TOTAL)

# ---------------------------------------------------------------- audio mix
N = int(SR*TOTAL) + SR
mix = np.zeros(N)
def put(at, sig, g=1.0):
    p = int(at*SR); e = min(N, p+len(sig)); mix[p:e] += sig[:e-p]*g

for st, a, g, *_ in events:
    put(st, a, g)

# engine hum, rising rumble with loudness stage
tt = np.arange(N)/SR
engine = (np.sin(2*np.pi*55*tt) + 0.5*np.sin(2*np.pi*110*tt)) * (0.6+0.4*np.sin(2*np.pi*7*tt))
engine += lowpass(np.random.randn(N), 40) * 2
eg = np.full(N, 0.06); eg[int(crash_t*SR):] = 0
mix += engine * eg
# background kid chatter gets louder each stage
for i, st in enumerate(stage_times):
    nxt = stage_times[i+1] if i+1 < len(stage_times) else drift_t
    seg = lowpass(np.random.randn(int((nxt-st)*SR)), 12) * (0.02 + 0.03*i) * (1+np.sin(2*np.pi*4*np.arange(int((nxt-st)*SR))/SR)*0.5)
    put(st, seg)
    if i >= 3:  # rumble
        r = int((nxt-st)*SR)
        put(st, np.sin(2*np.pi*40*np.arange(r)/SR) * 0.06*(i-2))

vt = dict((n, s) for s, n in visual)
put(vt["grandma"], sfx_boing(), 0.8)
put(vt["birds"]-0.3, sfx_birds(), 0.8)
put(vt["glass"]-0.2, sfx_glass(), 0.9); put(vt["glass"]+0.8, sfx_dog(), 0.6)
put(vt["police"]-0.2, sfx_siren(3.5), 0.6)
put(vt["satellite"]-0.2, sfx_whoosh(2.0), 0.7)
put(vt["moon"]-0.2, sfx_whoosh(1.2, down=False), 0.5)
put(drift_t-0.7, sfx_horn(), 0.6)
put(screech_t, sfx_screech(), 0.8)
put(crash_t, sfx_crash(), 1.0)
put(crash_t+1.5, sfx_boing(), 0.5)

# soft limiter -> safe volume (the decibels are only on screen!)
mix = np.tanh(mix*1.2)
mix = mix / np.abs(mix).max() * 0.89
pcm = (mix*32767).astype(np.int16)
wav = os.path.join(OUT, "audio.wav")
with wave.open(wav, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

# ---------------------------------------------------------------- graphics
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
F_SUB = ImageFont.truetype(FB, 34)
F_SPK = ImageFont.truetype(FB, 24)
F_DB = ImageFont.truetype(FB, 40)
F_BIG = ImageFont.truetype(FB, 120)
F_MID = ImageFont.truetype(FB, 60)
F_SM = ImageFont.truetype(FB, 20)

SPK_COL = {"Рассказчик": (255, 255, 255), "Дети": (255, 220, 60), "Водитель": (255, 90, 90)}

def stage_at(t):
    s = -1
    for i, st in enumerate(stage_times):
        if t >= st: s = i
    return s

def db_value(t):
    s = stage_at(t)
    if s < 0: return 70
    if t >= drift_t: return STAGES[-1][0]
    prev = 70 if s == 0 else STAGES[s-1][0]
    k = min(1, (t-stage_times[s])/0.6)
    return int(prev + (STAGES[s][0]-prev)*k)

def draw_bus(t, s, open_mouth, cracked):
    bw, bh = 560, 250
    L = Image.new("RGBA", (bw+40, bh+60), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    d.rounded_rectangle([10, 20, bw, bh], 30, fill=(250, 200, 30), outline=(60, 40, 0), width=5)
    d.rectangle([10, 170, bw, 185], fill=(30, 30, 30))
    d.text((40, 190), "ШКОЛЬНЫЙ", fill=(40, 30, 0), font=F_SM)
    # windscreen + driver
    d.rounded_rectangle([bw-90, 45, bw-15, 150], 10, fill=(170, 220, 255), outline=(60, 40, 0), width=4)
    d.ellipse([bw-75, 75, bw-40, 110], fill=(240, 190, 150)); d.rectangle([bw-80, 70, bw-35, 80], fill=(30, 60, 140))
    # windows with kids
    skin = [(255, 214, 170), (200, 150, 110), (240, 190, 150), (150, 100, 70), (255, 225, 190)]
    hair = [(80, 50, 20), (20, 20, 20), (200, 150, 40), (120, 40, 20), (20, 20, 20)]
    for i in range(5):
        x0 = 40 + i*92
        d.rounded_rectangle([x0, 45, x0+78, 150], 10, fill=(170, 220, 255), outline=(60, 40, 0), width=4)
        bob = math.sin(t*(8+s*2)+i*1.7) * (3 + max(s, 0)*1.5)
        cx, cy = x0+39, 112+bob
        d.ellipse([cx-24, cy-26, cx+24, cy+22], fill=skin[i])
        d.chord([cx-25, cy-30, cx+25, cy+5], 180, 360, fill=hair[i])
        d.ellipse([cx-12, cy-8, cx-4, cy], fill=(0, 0, 0)); d.ellipse([cx+4, cy-8, cx+12, cy], fill=(0, 0, 0))
        if open_mouth:
            m = 6 + max(s, 0)*2 + 3*abs(math.sin(t*20+i))
            d.ellipse([cx-9, cy+4, cx+9, cy+4+m], fill=(120, 0, 0))
        else:
            d.arc([cx-9, cy, cx+9, cy+12], 20, 160, fill=(80, 0, 0), width=3)
        if cracked:
            rnd = random.Random(i)
            for _ in range(6):
                a = rnd.uniform(0, 2*math.pi); r = rnd.uniform(25, 60)
                d.line([x0+30, 70, x0+30+r*math.cos(a), 70+r*math.sin(a)], fill=(255, 255, 255), width=2)
    # wheels
    for wx in (110, bw-120):
        d.ellipse([wx-40, bh-40, wx+40, bh+40], fill=(30, 30, 30))
        d.ellipse([wx-16, bh-16, wx+16, bh+16], fill=(170, 170, 170))
        a = t*12
        d.line([wx, bh, wx+16*math.cos(a), bh+16*math.sin(a)], fill=(60, 60, 60), width=4)
    d.ellipse([bw-12, 160, bw+8, 180], fill=(255, 255, 200))
    return L

def draw_text_outline(d, xy, text, font, fill, anchor="mm", stroke=4):
    d.text(xy, text, font=font, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0))

def wrap(text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        test = (cur+" "+w_).strip()
        if font.getlength(test) <= maxw: cur = test
        else: lines.append(cur); cur = w_
    lines.append(cur); return lines

birds0 = [(random.uniform(150, 1150), random.uniform(0, 1)) for _ in range(12)]

def frame(t):
    s = stage_at(t)
    night = min(1, max(0, (t-stage_times[-1])/1.0)) if t < crash_t+0.5 else 1
    sky = tuple(int(a*(1-night)+b*night) for a, b in zip((135, 200, 250), (30, 30, 80)))
    img = Image.new("RGB", (W, H), sky)
    d = ImageDraw.Draw(img)
    moving = t < crash_t
    scroll = (min(t, crash_t) * 420)
    # sun / moon
    if "moon" in vt and t >= vt["moon"]:
        k = min(1, (t-vt["moon"])/0.8)
        mx, my = 1050, int(-80 + 200*k)
        d.ellipse([mx-70, my-70, mx+70, my+70], fill=(245, 245, 210))
        d.ellipse([mx-35, my-25, mx-20, my-10], fill=(80, 80, 80)); d.ellipse([mx+20, my-25, mx+35, my-10], fill=(80, 80, 80))
        d.arc([mx-30, my+10, mx+30, my+45], 200, 340, fill=(80, 80, 80), width=5)
        d.text((mx-150, my+80), "ТИШЕ!!!", font=F_MID, fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))
    else:
        d.ellipse([1080, 40, 1180, 140], fill=(255, 230, 80))
    # satellite
    if "satellite" in vt and vt["satellite"] <= t < vt["satellite"]+4:
        k = (t-vt["satellite"])/4
        sx, sy = 200 + 900*k, 60 + 180*k*k
        ang = t*6
        d.rectangle([sx-15, sy-10, sx+15, sy+10], fill=(190, 190, 190))
        for sgn in (-1, 1):
            px = sx + sgn*45*math.cos(ang); py = sy + sgn*45*math.sin(ang)
            d.line([sx, sy, px, py], fill=(40, 60, 160), width=14)
        d.line([sx-40, sy-30, sx-90, sy-60], fill=(255, 140, 0), width=4)
    # hills
    for i in range(-1, 5):
        x = (i*400 - scroll*0.2) % 1800 - 300
        d.ellipse([x, 380, x+500, 640], fill=(90, 170, 80))
    # city on fire? police lights
    if "police" in vt and t >= vt["police"] and t < crash_t:
        on = int(t*6) % 2
        d.rectangle([0, 0, W, 12], fill=(255, 0, 0) if on else (0, 80, 255))
    # ground & road
    d.rectangle([0, 470, W, H], fill=(70, 150, 60))
    d.rectangle([0, 520, W, 650], fill=(60, 60, 65))
    for i in range(-1, 12):
        x = (i*160 - scroll) % (W+160) - 160
        d.rectangle([x, 580, x+80, 590], fill=(240, 240, 240))
    # telephone poles with birds
    for i in range(-1, 4):
        x = (i*450 - scroll*0.9) % (W+450) - 200
        d.rectangle([x, 300, x+10, 520], fill=(110, 70, 40)); d.rectangle([x-30, 310, x+40, 318], fill=(110, 70, 40))
    d.line([0, 314, W, 314], fill=(40, 40, 40), width=2)
    # birds
    bstart = vt.get("birds", 1e9)
    for (bx, ph) in birds0:
        if t < bstart:
            if t > 2:
                d.ellipse([bx-10, 300, bx+10, 314], fill=(40, 40, 50))
        else:
            k = t - bstart + ph*0.3
            if k < 0: d.ellipse([bx-10, 300, bx+10, 314], fill=(40, 40, 50)); continue
            x = bx + 160*k*(1 if bx > 640 else -1); y = 307 - 220*k - 40*k*k
            flap = 12*math.sin(t*25+ph*10)
            d.line([x-18, y-flap, x, y, x+18, y-flap], fill=(40, 40, 50), width=4)
    # grandma at stop
    if "grandma" in vt and vt["grandma"]-1.5 <= t < vt["grandma"]+5:
        gx = 1100 - (t-(vt["grandma"]-1.5))*300
        d.rectangle([gx-60, 380, gx+60, 390], fill=(30, 90, 160)); d.rectangle([gx-5, 390, gx+5, 520], fill=(100, 100, 100))
        d.text((gx-48, 381), "ОСТАНОВКА", font=ImageFont.truetype(FB, 12), fill=(255, 255, 255))
        d.ellipse([gx+20, 410, gx+50, 440], fill=(240, 200, 170)); d.chord([gx+16, 404, gx+54, 440], 180, 360, fill=(200, 60, 120))
        d.polygon([(gx+35, 440), (gx+10, 515), (gx+60, 515)], fill=(140, 60, 120))
        if t >= vt["grandma"]:
            k = t - vt["grandma"]
            for j in range(4):
                py = min(512, 455 + 200*k*k + j*3); px = gx + 5 + j*14
                d.ellipse([px-8, py-6, px+8, py+6], fill=(210, 150, 60))
    # wall at the end
    if t >= screech_t:
        wx = W - 120
        d.rectangle([wx, 380, W, 650], fill=(150, 70, 50))
        for r in range(380, 650, 30):
            off = 0 if (r//30) % 2 else 25
            for c in range(wx+off-50, W, 50):
                d.rectangle([c, r, c+48, r+28], outline=(110, 50, 35), width=2)
    # bus
    open_mouth = any(sp == "Дети" and st <= t < st+len(a)/SR for st, a, g, txt, sp in events)
    bus = draw_bus(t, s, open_mouth, cracked=("glass" in vt and t >= vt["glass"]))
    bx, by, ang = 330, 300, 0
    if t >= screech_t:
        k = min(1, (t-screech_t)/2.4)
        ang = -75*k*k
        bx = 330 + 300*k*k
        by = 300 - 20*math.sin(k*math.pi)
    if t >= crash_t:
        ang = -75 + 8*math.exp(-(t-crash_t)*3)*math.sin((t-crash_t)*25)
        bx = 630
    rb = bus.rotate(ang, expand=True, resample=Image.BICUBIC)
    img.paste(rb, (int(bx - (rb.width-bus.width)/2), int(by - (rb.height-bus.height)/2)), rb)
    # tire smoke
    if screech_t <= t < crash_t+1.5:
        rnd = random.Random(int(t*FPS))
        for _ in range(12):
            x = rnd.uniform(300, 900); y = rnd.uniform(540, 640); r = rnd.uniform(15, 45)
            d.ellipse([x-r, y-r, x+r, y+r], fill=(200, 200, 200))
    # crash
    if crash_t <= t < outro_t + 1:
        k = t - crash_t
        if k < 0.15:
            img.paste((255, 255, 255), [0, 0, W, H])
        cx, cy = 1050, 420
        rnd = random.Random(3)
        pts = []
        for j in range(24):
            a = j/24*2*math.pi; r = (160 if j % 2 else 80) * min(1, k*4)
            pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
        d.polygon(pts, fill=(255, 200, 0), outline=(255, 60, 0))
        if k < 2.3:
            draw_text_outline(d, (640, 200), "БАБАХ!!!", F_BIG, (255, 60, 0), stroke=8)
        for j in range(5):
            a = t*3 + j*2*math.pi/5
            sx = 760 + 90*math.cos(a); sy = 300 + 25*math.sin(a)
            draw_text_outline(d, (sx, sy), "★", F_DB, (255, 255, 120), stroke=2)
    # dB meter
    if t < crash_t:
        dbv = db_value(t)
        frac = min(1, math.log10(max(dbv, 70)/70) / math.log10(1000000/70))
        d.rounded_rectangle([20, 20, 470, 120], 14, fill=(20, 20, 20), outline=(255, 255, 255), width=3)
        d.text((40, 30), "ГРОМКОСТЬ", font=F_SM, fill=(200, 200, 200))
        col = (60, 220, 60) if frac < .35 else (255, 200, 0) if frac < .7 else (255, 40, 40)
        d.rectangle([40, 85, 40+int(410*max(frac, .03)), 108], fill=col)
        d.rectangle([40, 85, 450, 108], outline=(150, 150, 150), width=2)
        d.text((40, 48), f"{dbv:,} дБ".replace(",", " "), font=ImageFont.truetype(FB, 32), fill=col)
    # subtitles
    cur = None
    for st, a, g, txt, sp in events:
        if st <= t < st + len(a)/SR + 0.35: cur = (txt, sp)
    if cur:
        txt, sp = cur
        lines = wrap(txt, F_SUB, 1100)
        y0 = H - 40 - 44*len(lines)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        od.rounded_rectangle([120, y0-42, W-120, H-20], 16, fill=(0, 0, 0, 150))
        img.paste(ov, (0, 0), ov); d = ImageDraw.Draw(img)
        d.text((W//2, y0-22), sp, font=F_SPK, fill=SPK_COL[sp], anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0))
        for j, ln in enumerate(lines):
            d.text((W//2, y0+12+44*j), ln, font=F_SUB, fill=SPK_COL[sp], anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))
    # title & end
    if t < 0.5 + 2.5 and t > 0:
        draw_text_outline(d, (640, 250), "ВАЙБКОДЕРЫ В АВТОБУСЕ", F_MID, (255, 230, 60), stroke=6)
    if t >= end_t - 1.8:
        a = min(1, (t-(end_t-1.8))/0.5)
        ov = Image.new("RGB", (W, H), (0, 0, 0))
        img = Image.blend(img, ov, a*0.85)
        d = ImageDraw.Draw(img)
        draw_text_outline(d, (640, 340), "КОНЕЦ", F_BIG, (255, 255, 255), stroke=6)
    # screen shake
    amp = 0
    if 0 <= s and t < screech_t:
        amp = [0, 1, 3, 6, 10, 15, 22][s] if any(sp == "Дети" and st <= t < st+len(a)/SR+0.2 for st, a, g, txt, sp in events) else [0, 0, 1, 2, 4, 6, 9][s]
    if crash_t <= t < crash_t+1.2:
        amp = 30*(1-(t-crash_t)/1.2)
    if amp:
        dx, dy = random.randint(-int(amp), int(amp)+1), random.randint(-int(amp), int(amp)+1)
        img = img.transform(img.size, Image.AFFINE, (1, 0, dx, 0, 1, dy), fillcolor=(0, 0, 0))
    return img

mp4 = os.path.join(OUT, "vibecoders_bus.mp4")
p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                      "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
                      "-c:a", "aac", "-b:a", "160k", "-shortest", mp4], stdin=subprocess.PIPE)
nf = int(TOTAL*FPS)
for i in range(nf):
    p.stdin.write(frame(i/FPS).tobytes())
p.stdin.close(); p.wait()
print("done", mp4)
