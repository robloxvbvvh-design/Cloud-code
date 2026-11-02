# -*- coding: utf-8 -*-
"""Рендер мультфильма «Дима и Глотун». Все тайминги — во времени исходной озвучки."""
import cairo, math, sys, random, subprocess

W, H, FPS = 1280, 720, 24
PI = math.pi
TAU = 2 * PI

# ---------- время ----------
CUT1 = (57.0, 58.38)      # вырезано «0:42»
CUT2 = (163.55, 165.62)   # вырезано «2:00. Титр.»
OFF1 = CUT1[1] - CUT1[0]
OFF2 = OFF1 + CUT2[1] - CUT2[0]
NEW_END1 = CUT1[0]
NEW_END2 = CUT2[0] - OFF1
OLD_END = 171.0
TOTAL_NEW = OLD_END - OFF2


def to_old(tn):
    if tn < NEW_END1:
        return tn
    if tn < NEW_END2:
        return tn + OFF1
    return tn + OFF2


# ---------- утилиты ----------
def cl(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def sm(x):
    x = cl(x)
    return x * x * (3 - 2 * x)


def rng(t, a, b):
    return sm((t - a) / (b - a)) if b != a else (1.0 if t >= a else 0.0)


def lin(t, a, b):
    return cl((t - a) / (b - a))


def lerp(a, b, k):
    return a + (b - a) * k


def mix(c1, c2, k):
    return tuple(lerp(a, b, k) for a, b in zip(c1, c2))


def hx(h):
    h = h.lstrip('#')
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


def col(c, clr, a=1.0):
    if isinstance(clr, str):
        clr = hx(clr)
    c.set_source_rgba(clr[0], clr[1], clr[2], a)


def ell(c, x, y, rx, ry):
    c.save()
    c.translate(x, y)
    c.scale(max(rx, 0.01), max(ry, 0.01))
    c.arc(0, 0, 1, 0, TAU)
    c.restore()


def rr(c, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -PI / 2, 0)
    c.arc(x + w - r, y + h - r, r, 0, PI / 2)
    c.arc(x + r, y + h - r, r, PI / 2, PI)
    c.arc(x + r, y + r, r, PI, 1.5 * PI)
    c.close_path()


def glow(c, x, y, r, clr, a):
    if a <= 0 or r <= 0:
        return
    if isinstance(clr, str):
        clr = hx(clr)
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, clr[0], clr[1], clr[2], a)
    g.add_color_stop_rgba(1, clr[0], clr[1], clr[2], 0)
    c.set_source(g)
    c.arc(x, y, r, 0, TAU)
    c.fill()


def font(c, size, bold=True):
    c.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL,
                       cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    c.set_font_size(size)


def onoma(c, s, x, y, size, fill='#ffd23f', stroke='#2b1240', rot=0.0, alpha=1.0, sc=1.0):
    if alpha <= 0.01 or sc <= 0.01:
        return
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(sc, sc)
    font(c, size)
    e = c.text_extents(s)
    c.move_to(-e.width / 2 - e.x_bearing, -e.height / 2 - e.y_bearing)
    c.text_path(s)
    col(c, stroke, alpha)
    c.set_line_width(size * 0.17)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.stroke_preserve()
    col(c, fill, alpha)
    c.fill()
    c.restore()


def pop(t, t0, dur=1.2):
    """масштаб и прозрачность «выскакивающей» надписи"""
    if t < t0 or t > t0 + dur:
        return 0.0, 0.0
    k = t - t0
    sc = min(1.0, k / 0.1) * (1 + 0.28 * math.exp(-6 * k) * math.sin(22 * k))
    a = 1 - lin(t, t0 + dur - 0.3, t0 + dur)
    return sc, a


def path_poly(c, pts):
    c.new_path()
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()


# ---------- значки звуков ----------
KCOL = {
    'tick': hx('#ffd24a'), 'drop': hx('#7fd0ff'), 'hum': hx('#9dff7a'), 'bolt': hx('#fff04a'),
    'squeak': hx('#ffb3e0'), 'bam': hx('#ff8a3a'), 'star': hx('#c8ffff'), 'bark': hx('#ff9c6b'),
}
NOTE_COLS = [hx(h) for h in ('#ff6fae', '#6fe0ff', '#ffe06f', '#9b8cff', '#7dff9b', '#ff9f5a')]


def gear(c, x, y, r, rot, clr, a=1.0):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    col(c, clr, a)
    for i in range(8):
        c.save()
        c.rotate(i * TAU / 8)
        c.rectangle(-r * 0.18, -r * 1.05, r * 0.36, r * 0.4)
        c.fill()
        c.restore()
    c.arc(0, 0, r * 0.78, 0, TAU)
    c.fill()
    col(c, '#5a3a10', a)
    c.arc(0, 0, r * 0.28, 0, TAU)
    c.fill()
    c.restore()


def drop_icon(c, x, y, s, clr, a=1.0):
    c.save()
    c.translate(x, y)
    c.new_path()
    c.move_to(0, -s)
    c.curve_to(s * 0.65, -s * 0.15, s * 0.65, s * 0.6, 0, s * 0.6)
    c.curve_to(-s * 0.65, s * 0.6, -s * 0.65, -s * 0.15, 0, -s)
    col(c, clr, a)
    c.fill()
    col(c, '#ffffff', a * 0.7)
    ell(c, -s * 0.18, s * 0.15, s * 0.1, s * 0.18)
    c.fill()
    c.restore()


def hum_icon(c, x, y, s, t, clr, a=1.0):
    c.save()
    c.translate(x, y)
    col(c, clr, a)
    c.set_line_width(max(1.5, s * 0.22))
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for k in (-1, 0, 1):
        c.new_path()
        for i in range(21):
            u = i / 20
            px = (u - 0.5) * s * 2.2
            py = k * s * 0.45 + math.sin(u * 10 + t * 9 + k) * s * 0.18
            (c.move_to if i == 0 else c.line_to)(px, py)
        c.stroke()
    c.restore()


def bolt_icon(c, x, y, s, rot, clr, a=1.0):
    pts = [(-0.15, -1), (0.45, -1), (0.1, -0.2), (0.5, -0.2), (-0.3, 1), (-0.05, 0.12), (-0.45, 0.12)]
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    path_poly(c, [(px * s, py * s) for px, py in pts])
    col(c, clr, a)
    c.fill_preserve()
    col(c, '#ff8a00', a)
    c.set_line_width(s * 0.08)
    c.stroke()
    c.restore()


def star_icon(c, x, y, r, rot, clr, a=1.0, n=5):
    pts = []
    for i in range(n * 2):
        ang = rot + i * PI / n - PI / 2
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((x + math.cos(ang) * rad, y + math.sin(ang) * rad))
    path_poly(c, pts)
    col(c, clr, a)
    c.fill_preserve()
    col(c, '#ffffff', a)
    c.set_line_width(max(1, r * 0.08))
    c.stroke()


def burst(c, x, y, r, rot, clr, a=1.0, n=12):
    pts = []
    for i in range(n * 2):
        ang = rot + i * PI / n
        rad = r if i % 2 == 0 else r * 0.68
        pts.append((x + math.cos(ang) * rad, y + math.sin(ang) * rad * 0.8))
    path_poly(c, pts)
    col(c, clr, a)
    c.fill_preserve()
    col(c, '#5a1a00', a)
    c.set_line_width(max(1, r * 0.06))
    c.stroke()


def note_icon(c, x, y, s, clr, a=1.0, rot=0.0):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    col(c, clr, a)
    c.save()
    c.translate(0, s * 0.55)
    c.rotate(-0.4)
    ell(c, 0, 0, s * 0.38, s * 0.27)
    c.fill()
    c.restore()
    c.set_line_width(max(1.2, s * 0.13))
    c.move_to(s * 0.32, s * 0.5)
    c.line_to(s * 0.32, -s * 0.75)
    c.curve_to(s * 0.6, -s * 0.5, s * 0.85, -s * 0.35, s * 0.62, -s * 0.05)
    c.stroke()
    c.restore()


def bubble_icon(c, x, y, r, clr, a=1.0):
    col(c, clr, a * 0.55)
    c.arc(x, y, r, 0, TAU)
    c.fill()
    col(c, '#ffffff', a)
    c.set_line_width(max(1, r * 0.12))
    c.arc(x, y, r, 0, TAU)
    c.stroke()
    ell(c, x - r * 0.35, y - r * 0.35, r * 0.18, r * 0.12)
    c.fill()


def item(c, kind, x, y, s, t, a=1.0, bright=1.0, clr=None):
    """один звук-светлячок"""
    if a <= 0.01:
        return
    clr = clr or KCOL.get(kind, (1, 1, 1))
    glow(c, x, y, s * 2.2, clr, 0.55 * a * bright)
    if kind == 'tick':
        gear(c, x, y, s * 0.8, t * 2.5, clr, a)
    elif kind == 'drop':
        drop_icon(c, x, y, s * 0.9, clr, a)
    elif kind == 'hum':
        hum_icon(c, x, y, s * 0.7, t, clr, a)
    elif kind == 'bolt':
        bolt_icon(c, x, y, s, 0.3, clr, a)
    elif kind == 'squeak':
        bubble_icon(c, x, y, s * 0.6, clr, a)
    elif kind == 'bam':
        burst(c, x, y, s * 0.9, t, clr, a, n=9)
    elif kind == 'star':
        star_icon(c, x, y, s * 0.9, t * 1.5, clr, a)
    elif kind == 'note':
        note_icon(c, x, y, s * 0.95, clr, a)
    elif kind == 'bark':
        burst(c, x, y, s * 0.85, 0.2, clr, a, n=7)
        onoma(c, 'гав', x, y, s * 0.55, '#ffffff', '#5a1a00', 0, a)


# ---------- Дима ----------
SKIN = hx('#f4c7a1')
SKIN_D = hx('#d99a72')
HAIR = hx('#4a2c1a')
PJ = hx('#3f6fd6')
PJD = hx('#2c4fa8')


def dima_head(c, x, y, r, eyes=1.0, look=(0, 0), mouth='smile', mo=0.5, brows='n',
              cheeks=0.0, rot=0.0, happy_closed=False, blush=0.35):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    # уши
    for sx in (-1, 1):
        col(c, SKIN)
        ell(c, sx * r * 0.97, r * 0.08, r * 0.17, r * 0.24)
        c.fill()
        col(c, SKIN_D)
        ell(c, sx * r * 0.99, r * 0.08, r * 0.07, r * 0.12)
        c.fill()
    # голова
    rx = r * (1 + cheeks * 0.14)
    col(c, SKIN)
    ell(c, 0, 0, rx, r)
    c.fill()
    col(c, '#8a5236', 0.55)
    c.set_line_width(r * 0.035)
    ell(c, 0, 0, rx, r)
    c.stroke()
    # волосы
    pts = [(-1.04, -0.05), (-1.1, -0.5), (-0.82, -0.72), (-0.9, -1.05), (-0.5, -0.92), (-0.35, -1.25),
           (-0.02, -0.98), (0.22, -1.3), (0.42, -0.95), (0.82, -1.12), (0.78, -0.76), (1.12, -0.62),
           (1.04, -0.05)]
    c.new_path()
    c.move_to(pts[0][0] * r, pts[0][1] * r)
    for px, py in pts[1:]:
        c.line_to(px * r, py * r)
    c.curve_to(0.85 * r, -0.4 * r, 0.45 * r, -0.62 * r, 0.1 * r, -0.5 * r)
    c.curve_to(-0.2 * r, -0.62 * r, -0.75 * r, -0.45 * r, -1.04 * r, -0.05 * r)
    c.close_path()
    col(c, HAIR)
    c.fill()
    # румянец
    col(c, '#ff7a8a', blush)
    ell(c, -0.58 * r, 0.3 * r, 0.17 * r * (1 + cheeks * 0.4), 0.1 * r)
    c.fill()
    ell(c, 0.58 * r, 0.3 * r, 0.17 * r * (1 + cheeks * 0.4), 0.1 * r)
    c.fill()
    # глаза
    ey = -0.05 * r
    for sx in (-1, 1):
        ex = sx * 0.36 * r
        if happy_closed or eyes < 0.18:
            col(c, '#2a1a10')
            c.set_line_width(r * 0.07)
            c.set_line_cap(cairo.LINE_CAP_ROUND)
            c.new_path()
            if happy_closed:
                c.arc(ex, ey + 0.05 * r, 0.14 * r, PI * 1.1, PI * 1.9)
            else:
                c.move_to(ex - 0.15 * r, ey + 0.02 * r)
                c.curve_to(ex - 0.05 * r, ey + 0.08 * r, ex + 0.05 * r, ey + 0.08 * r, ex + 0.15 * r, ey + 0.02 * r)
            c.stroke()
        else:
            col(c, '#ffffff')
            ell(c, ex, ey, 0.2 * r, 0.25 * r * eyes)
            c.fill()
            c.save()
            ell(c, ex, ey, 0.2 * r, 0.25 * r * eyes)
            c.clip()
            col(c, '#2a1a10')
            c.arc(ex + look[0] * 0.08 * r, ey + look[1] * 0.08 * r, 0.11 * r, 0, TAU)
            c.fill()
            col(c, '#ffffff')
            c.arc(ex + look[0] * 0.08 * r + 0.04 * r, ey + look[1] * 0.08 * r - 0.05 * r, 0.035 * r, 0, TAU)
            c.fill()
            c.restore()
            col(c, '#2a1a10', 0.8)
            c.set_line_width(r * 0.03)
            ell(c, ex, ey, 0.2 * r, 0.25 * r * eyes)
            c.stroke()
    # брови
    col(c, HAIR)
    c.set_line_width(r * 0.07)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for sx in (-1, 1):
        bx = sx * 0.36 * r
        by = -0.4 * r
        if brows == 'up':
            by -= 0.1 * r
            c.move_to(bx - 0.15 * r, by + 0.03 * r)
            c.curve_to(bx - 0.05 * r, by - 0.05 * r, bx + 0.05 * r, by - 0.05 * r, bx + 0.15 * r, by + 0.03 * r)
        elif brows == 'worried':
            c.move_to(bx - sx * 0.15 * r, by - 0.08 * r)
            c.line_to(bx + sx * 0.15 * r, by + 0.03 * r)
        elif brows == 'angry':
            c.move_to(bx - sx * 0.15 * r, by + 0.06 * r)
            c.line_to(bx + sx * 0.15 * r, by - 0.04 * r)
        else:
            c.move_to(bx - 0.14 * r, by)
            c.curve_to(bx - 0.05 * r, by - 0.04 * r, bx + 0.05 * r, by - 0.04 * r, bx + 0.14 * r, by)
        c.stroke()
    # рот
    my = 0.45 * r
    c.set_line_width(r * 0.06)
    if mouth == 'smile':
        col(c, '#7a2a2a')
        c.new_path()
        c.arc(0, my - 0.12 * r, 0.22 * r, PI * 0.2, PI * 0.8)
        c.stroke()
    elif mouth == 'grin':
        c.new_path()
        c.move_to(-0.3 * r, my - 0.05 * r)
        c.curve_to(-0.2 * r, my + 0.3 * r, 0.2 * r, my + 0.3 * r, 0.3 * r, my - 0.05 * r)
        c.close_path()
        col(c, '#6a1f2a')
        c.fill_preserve()
        c.save()
        c.clip()
        col(c, '#ffffff')
        c.rectangle(-0.3 * r, my - 0.06 * r, 0.6 * r, 0.08 * r)
        c.fill()
        col(c, '#ff7f8f')
        ell(c, 0, my + 0.22 * r, 0.14 * r, 0.08 * r)
        c.fill()
        c.restore()
    elif mouth in ('o', 'scream'):
        big = 1.0 if mouth == 'scream' else 0.45
        rx_ = (0.12 + 0.24 * big) * r * (0.5 + 0.5 * mo)
        ry_ = (0.1 + 0.32 * big) * r * mo + 0.04 * r
        col(c, '#4a1520')
        ell(c, 0, my + ry_ * 0.3, rx_, ry_)
        c.fill()
        if mouth == 'scream':
            col(c, '#ff7f8f')
            ell(c, 0, my + ry_ * 0.9, rx_ * 0.6, ry_ * 0.35)
            c.fill()
    elif mouth == 'flat':
        col(c, '#7a2a2a')
        c.move_to(-0.15 * r, my)
        c.line_to(0.15 * r, my)
        c.stroke()
    elif mouth == 'pressed':
        col(c, '#7a2a2a')
        c.move_to(-0.08 * r, my)
        c.line_to(0.08 * r, my)
        c.stroke()
    elif mouth == 'worried':
        col(c, '#7a2a2a')
        c.new_path()
        for i in range(9):
            u = i / 8
            px = (u - 0.5) * 0.4 * r
            py = my + math.sin(u * TAU * 1.5) * 0.04 * r
            (c.move_to if i == 0 else c.line_to)(px, py)
        c.stroke()
    elif mouth == 'frown':
        col(c, '#7a2a2a')
        c.new_path()
        c.arc(0, my + 0.16 * r, 0.18 * r, PI * 1.2, PI * 1.8)
        c.stroke()
    c.restore()


def ik2(px, py, tx, ty, l1, l2, bend=1):
    dx, dy = tx - px, ty - py
    d = math.hypot(dx, dy)
    d = min(d, l1 + l2 - 0.01)
    d = max(d, abs(l1 - l2) + 0.01)
    a = math.atan2(dy, dx)
    cosb = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    b = math.acos(cl(cosb, -1, 1))
    ang = a + bend * b
    return px + math.cos(ang) * l1, py + math.sin(ang) * l1, px + math.cos(a) * d, py + math.sin(a) * d


def dima(c, x, y, s=1.0, face=1, eyes=1.0, look=(0, 0), mouth='smile', mo=0.5, brows='n', cheeks=0.0,
         armB=8, armF=8, tgtB=None, tgtF=None, legB=-4, legF=4, lean=0.0, bob=0.0, chest=1.0,
         holdF=None, holdB=None, head_rot=0.0, happy_closed=False, sit=0.0, crouch=0.0, harmonica=False,
         pocket=None):
    """Дима стоит, origin — между ступнями. Возвращает мировые координаты рта (в device-space)."""
    c.save()
    c.translate(x, y - bob)
    c.scale(s * face, s)
    c.rotate(lean * PI / 180)
    lift = sit * 105 + crouch * 40
    c.translate(0, lift)
    L1, L2 = 50, 50
    sh_y = -228

    def leg(px, ang, length=118):
        a = ang * PI / 180
        ex, ey = px + math.sin(a) * length, -120 + math.cos(a) * length
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.set_line_width(32)
        col(c, PJD)
        c.move_to(px, -120)
        c.line_to(ex, ey)
        c.stroke()
        col(c, SKIN)
        ell(c, ex + 6 * (1 if ang >= 0 else -1) * (0.3 if abs(ang) < 30 else 1), ey + 6, 19, 10)
        c.fill()

    def arm(px, ang, tgt, clr):
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.set_line_width(24)
        col(c, clr)
        if tgt is not None:
            ex_, ey_, hx_, hy_ = ik2(px, sh_y, tgt[0], tgt[1] + 0, L1, L2, bend=1 if px > 0 else -1)
            c.move_to(px, sh_y)
            c.line_to(ex_, ey_)
            c.line_to(hx_, hy_)
        else:
            a = ang * PI / 180
            hx_, hy_ = px + math.sin(a) * (L1 + L2), sh_y + math.cos(a) * (L1 + L2)
            c.move_to(px, sh_y)
            c.line_to(hx_, hy_)
        c.stroke()
        col(c, SKIN)
        c.arc(hx_, hy_, 14, 0, TAU)
        c.fill()
        return hx_, hy_

    # ноги
    if sit > 0.5:
        leg(-22, -78 - 6 * sit, 112)
        leg(22, 78 + 6 * sit, 112)
    else:
        leg(-16, legB - crouch * 25)
        leg(16, legF + crouch * 25)
    # задняя рука
    hb = arm(-42, armB, tgtB, PJD)
    # туловище
    c.save()
    c.translate(0, -180)
    c.scale(chest, 1 + (chest - 1) * 0.4)
    rr(c, -50, -72, 100, 145, 34)
    col(c, PJ)
    c.fill()
    # ракеты на пижаме
    for (rx_, ry_) in ((-22, -35), (20, 5), (-15, 40), (28, -45)):
        c.save()
        c.translate(rx_, ry_)
        c.rotate(-0.6)
        col(c, '#ffd24a')
        path_poly(c, [(0, -9), (5, 4), (-5, 4)])
        c.fill()
        col(c, '#ff6b4a')
        path_poly(c, [(-3, 4), (3, 4), (0, 9)])
        c.fill()
        c.restore()
    # пуговицы / карман
    col(c, '#ffffff', 0.85)
    for by in (-40, -12, 16):
        c.arc(0, by, 3.5, 0, TAU)
        c.fill()
    rr(c, 14, 8, 26, 22, 5)
    col(c, PJD)
    c.fill()
    c.restore()
    if pocket is not None:
        pocket(c)   # что-то в кармане (рисуется в локальных координатах)
    # передняя рука
    hf = arm(42, armF, tgtF, PJ)
    for hold, hpos in ((holdF, hf), (holdB, hb)):
        if hold == 'flash':
            col(c, '#555a66')
            rr(c, hpos[0] - 6, hpos[1] - 12, 34, 16, 5)
            c.fill()
            col(c, '#fff3b0')
            c.rectangle(hpos[0] + 26, hpos[1] - 13, 6, 18)
            c.fill()
        elif hold == 'pot':
            col(c, '#9aa3b0')
            ell(c, hpos[0], hpos[1] + 18, 34, 24)
            c.fill()
            col(c, '#c7ced8')
            ell(c, hpos[0], hpos[1] + 4, 34, 9)
            c.fill()
        elif hold == 'lid':
            col(c, '#c7ced8')
            ell(c, hpos[0], hpos[1], 36, 10)
            c.fill()
            col(c, '#6b7380')
            c.arc(hpos[0], hpos[1] - 10, 6, 0, TAU)
            c.fill()
    # голова
    dima_head(c, 0, -300, 60, eyes, look, mouth, mo, brows, cheeks, head_rot, happy_closed)
    if harmonica:
        rr(c, -36, -286, 72, 17, 4)
        col(c, '#cfd6df')
        c.fill()
        col(c, '#5c6470')
        for i in range(6):
            c.rectangle(-30 + i * 11, -280, 6, 5)
            c.fill()
    mouth_dev = c.user_to_device(0, -273)
    hf_dev = c.user_to_device(*hf)
    c.restore()
    return mouth_dev, hf_dev


# ---------- Глотун ----------
RIM_EARS = [(-168, 0.9), (-145, 1.05), (-120, 0.95), (-95, 1.1), (-70, 1.0), (-45, 1.05), (-18, 0.9)]
FACE_EARS = [(-0.45, -0.18, 1.0), (0.42, -0.22, 0.95), (-0.05, 0.05, 0.85), (0.12, -0.45, 0.8),
             (-0.28, -0.52, 0.75), (0.55, 0.18, 0.8), (-0.58, 0.22, 0.75), (0.28, 0.3, 0.7)]
PURP = hx('#9a54e6')
PURP_L = hx('#c9a2ff')
PURP_D = hx('#5b2b99')
REDC = hx('#ee4058')


def ear(c, x, y, L, rot, lean, red, squint=0.0, a=1.0):
    c.save()
    c.translate(x, y)
    c.rotate(rot + lean)
    k = 1 - 0.65 * squint
    col(c, mix(PURP_L, (1, .65, .65), red), a)
    ell(c, 0, -L * 0.45, L * 0.33, L * 0.5 * k)
    c.fill()
    col(c, mix(PURP_D, (.5, .1, .1), red), a)
    c.set_line_width(max(1, L * 0.06))
    ell(c, 0, -L * 0.45, L * 0.33, L * 0.5 * k)
    c.stroke()
    side = 1 if lean >= 0 else -1
    col(c, '#ff8fc4', a)
    ell(c, side * L * 0.07, -L * 0.45, L * 0.17, L * 0.32 * k)
    c.fill()
    col(c, '#7a2a6a', a * 0.8)
    c.set_line_width(max(1, L * 0.05))
    c.new_path()
    c.arc(side * L * 0.07, -L * 0.42, L * 0.08 * k + 0.5, -PI / 2, PI / 2)
    c.stroke()
    c.restore()


def glotun(c, x, y, R, t, mouth=0.0, lean=0.0, perk=1.0, red=0.0, items=(), wob=1.0, legph=None,
           squint=0.0, alpha=0.9, sy=1.0, bright=1.0, item_speed=1.0, tongue=0.0, show_shadow=True):
    """origin — на полу под центром. Возвращает центр рта."""
    if R < 1:
        return (x, y)
    cx, cy = x, y - R * 0.82 * sy
    base = mix(PURP, REDC, red)
    dark = mix(PURP_D, hx('#7a1020'), red)
    if show_shadow:
        col(c, '#000000', 0.28)
        ell(c, x, y + 2, R * 0.95, R * 0.13)
        c.fill()
    # лапки
    for i in range(6):
        lx = x + (-0.62 + i * 0.248) * R
        lift = 0
        if legph is not None:
            lift = max(0.0, math.sin(legph + i * PI)) * R * 0.1
        col(c, dark)
        ell(c, lx, y - R * 0.07 - lift, R * 0.095, R * 0.11)
        c.fill()
    # уши по краю (за телом)
    for i, (ang, sz) in enumerate(RIM_EARS):
        th = ang * PI / 180
        px = cx + R * 0.98 * math.cos(th) * 1.05
        py = cy + R * 0.83 * sy * math.sin(th)
        L = R * 0.36 * sz * (0.55 + 0.45 * perk)
        wig = math.sin(t * 3.1 + i * 1.7) * 0.08 * (0.5 + perk)
        ear(c, px, py, L, th + PI / 2, lean * 0.8 + wig, red, squint * 0.5)
    # тело
    bottom = y - R * 0.06

    def body_path():
        c.new_path()
        N = 56
        for i in range(N + 1):
            th = TAU * i / N
            rad = R * (1 + wob * (0.035 * math.sin(3 * th + 2.1 * t) + 0.025 * math.sin(5 * th - 3.3 * t)))
            px = cx + rad * math.cos(th) * 1.05
            py = cy + rad * math.sin(th) * 0.85 * sy
            if py > bottom:
                py = bottom + (py - bottom) * 0.25
            (c.move_to if i == 0 else c.line_to)(px, py)
        c.close_path()

    body_path()
    g = cairo.RadialGradient(cx - R * 0.35, cy - R * 0.4 * sy, R * 0.1, cx, cy, R * 1.25)
    l = mix(base, (1, 1, 1), 0.35)
    g.add_color_stop_rgba(0, l[0], l[1], l[2], alpha)
    g.add_color_stop_rgba(0.6, base[0], base[1], base[2], alpha * 0.92)
    g.add_color_stop_rgba(1, dark[0], dark[1], dark[2], alpha)
    c.set_source(g)
    c.fill_preserve()
    col(c, dark, 0.9)
    c.set_line_width(max(1.5, R * 0.035))
    c.stroke()
    # звуки внутри
    c.save()
    body_path()
    c.clip()
    n = len(items)
    for i, it in enumerate(items):
        kind = it[0]
        clr = it[1] if len(it) > 1 else None
        phi = i * 2.39996 + t * 0.7 * item_speed
        rad = R * 0.55 * (0.35 + 0.65 * ((i * 0.618) % 1))
        px = cx + math.cos(phi) * rad
        py = cy + math.sin(phi) * rad * 0.7 * sy
        s = R * (0.17 if n < 8 else 0.13)
        item(c, kind, px, py, s, t + i, 0.95, bright, clr)
    c.restore()
    # блик
    col(c, '#ffffff', 0.22)
    ell(c, cx - R * 0.42, cy - R * 0.45 * sy, R * 0.22, R * 0.12 * sy)
    c.fill()
    # рот
    mx, my = cx, cy + R * 0.18 * sy
    if mouth > 0.02:
        rx_, ry_ = R * 0.78 * mouth, R * 0.55 * mouth * sy
        col(c, '#2a0f3a')
        ell(c, mx, my, rx_, ry_)
        c.fill()
        c.save()
        ell(c, mx, my, rx_, ry_)
        c.clip()
        col(c, '#ff6f9a')
        ell(c, mx, my + ry_ * 0.75, rx_ * 0.6, ry_ * 0.45)
        c.fill()
        c.restore()
    elif tongue > 0:
        col(c, '#ff6f9a')
        ell(c, mx, my, R * 0.12, R * 0.08 * tongue)
        c.fill()
    # уши на «лице»
    for i, (fx, fy, sz) in enumerate(FACE_EARS):
        px = cx + fx * R
        py = cy + fy * R * sy
        if mouth > 0.3 and abs(fx) < 0.45 and fy > -0.3:
            continue
        L = R * 0.27 * sz * (0.7 + 0.3 * perk)
        wig = math.sin(t * 2.6 + i * 2.3) * 0.1
        ear(c, px, py + L * 0.35, L, fx * 0.5, lean + wig, red, squint)
    return (mx, my)


# ---------- фоны ----------
BIG = (-400, -400, W + 800, H + 800)


def sky_rect(c, top, bottom):
    g = cairo.LinearGradient(0, -200, 0, H)
    g.add_color_stop_rgb(0, *hx(top))
    g.add_color_stop_rgb(1, *hx(bottom))
    c.set_source(g)
    c.rectangle(*BIG)
    c.fill()


def bedroom(c, t, door=0.0, clock_t=None):
    sky_rect(c, '#24306a', '#141a3c')
    # обои — звёздочки
    random.seed(7)
    col(c, '#ffffff', 0.05)
    for i in range(70):
        px, py = random.uniform(-200, W + 200), random.uniform(-100, 560)
        star_icon(c, px, py, 5, 0, (1, 1, 1), 0.05)
    # пол
    col(c, '#251d3e')
    c.rectangle(-400, 590, W + 800, 600)
    c.fill()
    col(c, '#32285a')
    c.rectangle(-400, 586, W + 800, 8)
    c.fill()
    # окно
    wx, wy, ww, wh = 880, 80, 250, 270
    col(c, '#3b3572')
    rr(c, wx - 14, wy - 14, ww + 28, wh + 28, 10)
    c.fill()
    g = cairo.LinearGradient(0, wy, 0, wy + wh)
    g.add_color_stop_rgb(0, *hx('#0b1240'))
    g.add_color_stop_rgb(1, *hx('#26307a'))
    c.set_source(g)
    c.rectangle(wx, wy, ww, wh)
    c.fill()
    c.save()
    c.rectangle(wx, wy, ww, wh)
    c.clip()
    glow(c, wx + 160, wy + 85, 110, hx('#fff6c8'), 0.35)
    col(c, '#fff6d0')
    c.arc(wx + 160, wy + 85, 36, 0, TAU)
    c.fill()
    col(c, '#e8dca8')
    c.arc(wx + 150, wy + 78, 7, 0, TAU)
    c.fill()
    c.arc(wx + 172, wy + 98, 5, 0, TAU)
    c.fill()
    random.seed(3)
    for i in range(14):
        sx_, sy_ = wx + random.uniform(5, ww - 5), wy + random.uniform(5, wh - 5)
        a = 0.5 + 0.5 * math.sin(t * 2 + i)
        col(c, '#ffffff', 0.4 + 0.5 * a)
        c.arc(sx_, sy_, 1.8, 0, TAU)
        c.fill()
    # дома за окном
    col(c, '#0a0e2a')
    for i, (bx, bh) in enumerate(((0, 70), (50, 110), (110, 80), (160, 130), (215, 90))):
        c.rectangle(wx + bx, wy + wh - bh, 48, bh)
        c.fill()
    col(c, '#ffd36a', 0.8)
    for (bx, by) in ((62, 190), (80, 220), (175, 170), (190, 205), (125, 230)):
        c.rectangle(wx + bx, wy + by, 7, 9)
        c.fill()
    c.restore()
    col(c, '#3b3572')
    c.rectangle(wx + ww / 2 - 5, wy, 10, wh)
    c.fill()
    c.rectangle(wx, wy + wh / 2 - 5, ww, 10)
    c.fill()
    # шторы
    for sx_ in (wx - 40, wx + ww + 10):
        g = cairo.LinearGradient(sx_, 0, sx_ + 30, 0)
        g.add_color_stop_rgb(0, *hx('#5a3a8a'))
        g.add_color_stop_rgb(1, *hx('#3d2766'))
        c.set_source(g)
        c.rectangle(sx_, wy - 30, 30, wh + 70)
        c.fill()
    # лунный луч
    col(c, '#b8d0ff', 0.07)
    path_poly(c, [(wx, wy + wh), (wx + ww, wy + wh), (wx + ww - 60, 720), (wx - 260, 720)])
    c.fill()
    # дверь справа
    dx = 1185
    col(c, '#2a2350')
    c.rectangle(dx, 210, 150, 380)
    c.fill()
    if door > 0:
        col(c, '#ffd88a', 0.9)
        c.rectangle(dx, 210, 14 * door + 4, 380)
        c.fill()
        col(c, '#ffd88a', 0.15 * door)
        path_poly(c, [(dx, 590), (dx + 18 * door, 590), (dx - 200 * door, 720), (dx - 380 * door, 720)])
        c.fill()
    col(c, '#4a3f80')
    c.rectangle(dx + 14 * door + 4, 210, 150, 380)
    c.fill()
    col(c, '#d8c060')
    c.arc(dx + 14 * door + 24, 410, 7, 0, TAU)
    c.fill()
    # кровать
    col(c, '#6b3f2a')
    rr(c, 70, 330, 46, 270, 12)
    c.fill()
    rr(c, 560, 450, 30, 150, 10)
    c.fill()
    col(c, '#7d4a32')
    c.rectangle(80, 520, 500, 40)
    c.fill()
    col(c, '#dfe6f5')
    rr(c, 110, 455, 460, 70, 18)
    c.fill()
    # тумбочка + будильник
    col(c, '#5a3524')
    rr(c, 620, 480, 120, 112, 8)
    c.fill()
    col(c, '#734630')
    c.rectangle(632, 520, 96, 4)
    c.fill()
    ct = t if clock_t is None else clock_t
    cxk, cyk = 680, 448
    col(c, '#d9473a')
    c.arc(cxk - 18, cyk - 26, 10, 0, TAU)
    c.fill()
    c.arc(cxk + 18, cyk - 26, 10, 0, TAU)
    c.fill()
    c.arc(cxk, cyk, 30, 0, TAU)
    c.fill()
    col(c, '#fff8e8')
    c.arc(cxk, cyk, 23, 0, TAU)
    c.fill()
    col(c, '#222222')
    c.set_line_width(3)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    a1 = math.floor(ct) * TAU / 60
    c.move_to(cxk, cyk)
    c.line_to(cxk + math.sin(a1) * 18, cyk - math.cos(a1) * 18)
    c.stroke()
    c.move_to(cxk, cyk)
    c.line_to(cxk + math.sin(1.6) * 12, cyk - math.cos(1.6) * 12)
    c.stroke()
    col(c, '#d9473a')
    c.rectangle(cxk - 26, cyk + 26, 8, 10)
    c.rectangle(cxk + 18, cyk + 26, 8, 10)
    c.fill()
    return (cxk, cyk)


def blanket(c, t, breathe=0.0):
    c.new_path()
    c.move_to(240, 470)
    top = 410 - breathe * 4
    c.curve_to(300, top - 15, 420, top + 5, 470, top)
    c.curve_to(520, top - 5, 560, 420, 575, 440)
    c.line_to(585, 560)
    c.line_to(225, 560)
    c.close_path()
    g = cairo.LinearGradient(0, 400, 0, 560)
    g.add_color_stop_rgb(0, *hx('#5b7fe0'))
    g.add_color_stop_rgb(1, *hx('#3b56b0'))
    c.set_source(g)
    c.fill()
    random.seed(11)
    for i in range(10):
        px, py = random.uniform(270, 560), random.uniform(440, 545)
        star_icon(c, px, py, 7, 0.3, hx('#ffe07a'), 0.8)
    col(c, '#ffffff', 0.85)
    c.set_line_width(10)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.move_to(248, 468)
    c.curve_to(300, top - 8, 420, top + 12, 470, top + 6)
    c.stroke()


def pillow(c):
    col(c, '#f2f4ff')
    ell(c, 180, 455, 82, 34)
    c.fill()
    col(c, '#c9cff0')
    c.set_line_width(3)
    ell(c, 180, 455, 82, 34)
    c.stroke()


def kitchen(c, t, fridge_light=1.0):
    sky_rect(c, '#1f3050', '#132036')
    # плитка
    col(c, '#ffffff', 0.04)
    c.set_line_width(2)
    for i in range(-5, 40):
        c.move_to(i * 48, -200)
        c.line_to(i * 48, 600)
    for j in range(-5, 16):
        c.move_to(-400, j * 48)
        c.line_to(W + 400, j * 48)
    c.stroke()
    # пол шахматкой
    for i in range(-10, 40):
        for j in range(0, 6):
            if (i + j) % 2 == 0:
                col(c, '#2a2a44')
            else:
                col(c, '#1c1c30')
            c.rectangle(i * 70 - 200, 610 + j * 50, 70, 50)
            c.fill()
    # шкафчики
    col(c, '#3a4a6a')
    c.rectangle(-300, 430, 700, 180)
    c.fill()
    col(c, '#4d5f86')
    c.rectangle(-300, 418, 710, 16)
    c.fill()
    for i in range(4):
        col(c, '#2f3d5a')
        rr(c, -270 + i * 165, 450, 150, 145, 6)
        c.fill()
        col(c, '#9fb0d0')
        c.rectangle(-270 + i * 165 + 120, 515, 6, 24)
        c.fill()
    col(c, '#3a4a6a')
    c.rectangle(-300, 110, 700, 160)
    c.fill()
    for i in range(4):
        col(c, '#2f3d5a')
        rr(c, -270 + i * 165, 125, 150, 130, 6)
        c.fill()
    # окно маленькое
    col(c, '#0b1240')
    rr(c, 470, 150, 160, 130, 6)
    c.fill()
    col(c, '#fff6d0', 0.9)
    c.arc(590, 185, 14, 0, TAU)
    c.fill()
    col(c, '#3a4a6a')
    c.set_line_width(8)
    rr(c, 470, 150, 160, 130, 6)
    c.stroke()
    # свет из холодильника
    fl = fridge_light
    glow(c, 965, 420, 420, hx('#fff0c0'), 0.22 * fl)
    col(c, '#fff0c0', 0.16 * fl)
    path_poly(c, [(860, 612), (1070, 612), (1250, 740), (600, 740)])
    c.fill()
    # холодильник
    col(c, '#a7b2c4')
    rr(c, 850, 160, 230, 455, 16)
    c.fill()
    col(c, '#fff4d6')
    rr(c, 866, 176, 198, 424, 8)
    c.fill()
    col(c, '#e7dcc0')
    for sy_ in (285, 395, 500):
        c.rectangle(866, sy_, 198, 6)
        c.fill()
    for (bx, by, bw, bh, cc) in ((880, 225, 26, 60, '#6fcf6f'), (915, 240, 30, 45, '#ff8a5a'),
                                  (980, 235, 50, 50, '#ffd24a'), (890, 340, 60, 55, '#e06fb0'),
                                  (970, 350, 70, 45, '#8ab0ff'), (900, 455, 40, 45, '#ff6060')):
        col(c, cc)
        rr(c, bx, by, bw, bh, 6)
        c.fill()
    # дверца
    col(c, '#c7d0de')
    path_poly(c, [(1080, 160), (1190, 130), (1190, 650), (1080, 615)])
    c.fill()
    col(c, '#8a96aa')
    c.rectangle(1100, 300, 8, 90)
    c.fill()


def hallway(c, t, scroll):
    sky_rect(c, '#283668', '#18204a')
    col(c, '#1d2652')
    c.rectangle(-400, 430, W + 800, 180)
    c.fill()
    col(c, '#36447a')
    c.rectangle(-400, 424, W + 800, 10)
    c.fill()
    # пол
    col(c, '#3a2a3e')
    c.rectangle(-400, 610, W + 800, 300)
    c.fill()
    col(c, '#2a1d2e')
    c.set_line_width(3)
    off = scroll % 120
    for i in range(-6, 20):
        x0 = i * 120 - off
        c.move_to(x0, 610)
        c.line_to(x0 - 60, 730)
    c.stroke()
    # двери и картины
    per = 700
    off = scroll % per
    for i in range(-2, 4):
        bx = i * per - off + 100
        col(c, '#4a3b7a')
        c.rectangle(bx, 260, 140, 350)
        c.fill()
        col(c, '#5c4b92')
        rr(c, bx + 15, 280, 110, 140, 6)
        c.fill()
        rr(c, bx + 15, 440, 110, 150, 6)
        c.fill()
        col(c, '#d8c060')
        c.arc(bx + 120, 450, 7, 0, TAU)
        c.fill()
        # картина
        px = bx + 350
        col(c, '#a8783a')
        c.rectangle(px, 180, 130, 100)
        c.fill()
        col(c, '#1d3a5a')
        c.rectangle(px + 10, 190, 110, 80)
        c.fill()
        col(c, '#ffd24a')
        c.arc(px + 90, 215, 10, 0, TAU)
        c.fill()
        col(c, '#2f6a3a')
        path_poly(c, [(px + 10, 270), (px + 50, 215), (px + 85, 270)])
        c.fill()
        # бра
        col(c, '#ffe6a0', 0.18)
        c.arc(px + 230, 230, 40, 0, TAU)
        c.fill()
        col(c, '#ffe6a0')
        ell(c, px + 230, 230, 14, 18)
        c.fill()


def bathroom(c, t, door_open=0.0, shake=(0, 0), brush=None):
    sky_rect(c, '#1f4a5a', '#123040')
    col(c, '#ffffff', 0.06)
    c.set_line_width(2)
    for i in range(-10, 40):
        c.move_to(i * 56, -300)
        c.line_to(i * 56, 625)
    for j in range(-8, 13):
        c.move_to(-400, j * 56)
        c.line_to(W + 400, j * 56)
    c.stroke()
    # пол
    for i in range(-10, 40):
        for j in range(0, 5):
            col(c, '#2a3a4a' if (i + j) % 2 else '#33495a')
            c.rectangle(i * 64 - 200, 625 + j * 44, 64, 44)
            c.fill()
    # маленькое окошко
    col(c, '#0b1240')
    rr(c, 800, 90, 120, 100, 6)
    c.fill()
    col(c, '#5a8a9a')
    c.set_line_width(8)
    rr(c, 800, 90, 120, 100, 6)
    c.stroke()
    # ванна
    col(c, '#d4e2e8')
    rr(c, 20, 470, 320, 130, 40)
    c.fill()
    col(c, '#b8c9d2')
    c.rectangle(10, 462, 340, 18)
    c.fill()
    for fx in (60, 300):
        col(c, '#c9a24a')
        ell(c, fx, 612, 16, 14)
        c.fill()
    col(c, '#8fd3ff', 0.5)
    c.rectangle(30, 478, 300, 8)
    c.fill()
    # уточка
    col(c, '#ffd24a')
    ell(c, 250, 460, 22, 15)
    c.fill()
    c.arc(262, 442, 11, 0, TAU)
    c.fill()
    col(c, '#ff8a3a')
    path_poly(c, [(271, 440), (284, 444), (271, 448)])
    c.fill()
    # раковина и зеркало
    mx_, my_ = 560 + shake[0], 200 + shake[1]
    col(c, '#8fb5c0')
    rr(c, mx_ - 10, my_ - 10, 160, 150, 14)
    c.fill()
    g = cairo.LinearGradient(mx_, my_, mx_ + 140, my_ + 130)
    g.add_color_stop_rgb(0, *hx('#b8e0ee'))
    g.add_color_stop_rgb(1, *hx('#5a8aa0'))
    c.set_source(g)
    rr(c, mx_, my_, 140, 130, 10)
    c.fill()
    col(c, '#ffffff', 0.4)
    c.set_line_width(6)
    c.move_to(mx_ + 25, my_ + 60)
    c.line_to(mx_ + 60, my_ + 25)
    c.stroke()
    # полка + стакан со щёткой
    col(c, '#c9d6dc')
    c.rectangle(545, 360, 170, 10)
    c.fill()
    col(c, '#8fd3ff')
    rr(c, 600, 330, 26, 30, 4)
    c.fill()
    bx, by, br = (612, 330, 0.2) if brush is None else brush
    c.save()
    c.translate(bx, by)
    c.rotate(br)
    col(c, '#ff6f9a')
    rr(c, -3, -40, 6, 42, 3)
    c.fill()
    col(c, '#ffffff')
    c.rectangle(-5, -46, 10, 9)
    c.fill()
    c.restore()
    col(c, '#d4e2e8')
    path_poly(c, [(560, 420), (700, 420), (680, 470), (580, 470)])
    c.fill()
    col(c, '#b8c9d2')
    c.rectangle(615, 470, 30, 155)
    c.fill()
    # дверь
    dx = 1060
    col(c, '#163040')
    c.rectangle(dx, 250, 170, 375)
    c.fill()
    if door_open > 0:
        g = cairo.LinearGradient(dx, 0, dx + 170, 0)
        g.add_color_stop_rgb(0, *hx('#fff1c4'))
        g.add_color_stop_rgb(1, *hx('#ffd67a'))
        c.set_source(g)
        c.rectangle(dx, 250, 170 * door_open, 375)
        c.fill()
    col(c, '#6a4a3a')
    c.rectangle(dx + 170 * door_open, 250, 170 * (1 - door_open) + 0.01, 375)
    c.fill()
    if door_open < 0.6:
        col(c, '#7d5a48')
        rr(c, dx + 20 + 170 * door_open, 270, max(1, 130 * (1 - door_open)), 150, 6)
        c.fill()
        rr(c, dx + 20 + 170 * door_open, 440, max(1, 130 * (1 - door_open)), 160, 6)
        c.fill()
        col(c, '#d8c060')
        c.arc(dx + 25 + 170 * door_open, 450, 7, 0, TAU)
        c.fill()
    col(c, '#4a6a7a')
    c.rectangle(dx - 12, 238, 194, 14)
    c.rectangle(dx - 12, 238, 14, 390)
    c.rectangle(dx + 168, 238, 14, 390)
    c.fill()


# ---------- субтитры и плашки ----------
SUBS = [
    (0.0, 3.7, "Ночь. Дима спит. Дом, как всегда, шумит:"),
    (3.7, 7.5, "тикает будильник, капает кран, гудит холодильник."),
    (7.9, 11.9, "Но вот звуки начинают пропадать. Один… за другим."),
    (12.3, 15.7, "Тик… тик… т…  Тишина."),
    (16.3, 20.3, "Дима открывает глаза и щёлкает пальцами. Щелчка нет."),
    (20.5, 21.7, "— Чего?.."),
    (23.5, 26.4, "Дима крадётся на кухню. Холодильник открыт."),
    (26.6, 31.6, "А перед ним сидит… что-то. Фиолетовое. Дрожащее."),
    (31.8, 35.2, "Вместо глаз — уши. Десятки ушей."),
    (35.3, 38.8, "А внутри него светятся звуки, как светлячки в банке."),
    (38.9, 41.6, "Все ушки разом поворачиваются к Диме."),
    (43.3, 45.4, "Дима набирает воздуха и…"),
    (45.4, 46.6, "— А-А-А-А!"),
    (46.6, 47.4, "ХАП!"),
    (47.5, 51.6, "Тварь проглотила крик. Целиком. И тихонько икнула."),
    (51.7, 54.8, "Дима пробует ещё раз — выходит только писк."),
    (54.8, 56.9, "ХАП. И его тоже."),
    (60.2, 62.9, "Дима бежит! Тварь скачет следом."),
    (62.9, 65.3, "Падает стул — БАМ! — ХАП!"),
    (65.4, 70.0, "Дима лупит кастрюлями — ДЗЫНЬ! — ХАП! ДЗЫНЬ! — ХАП!"),
    (70.1, 75.7, "И с каждым звуком тварь становится больше. С кота. С собаку. С кресло."),
    (75.9, 79.5, "Дима прячется в ванной. Но желе просачивается под дверь."),
    (79.6, 83.5, "Тварь нависает над ним, огромная, до самого потолка…"),
    (83.6, 88.9, "…и ласково бодает его лбом. Как кот, который просит добавки."),
    (91.0, 94.9, "Так вот оно что. Он не злой. Он просто голодный."),
    (95.4, 100.0, "Дима достаёт губную гармошку. Играет он, честно говоря, ужасно."),
    (100.4, 101.5, "Фьююю-иии…"),
    (101.8, 107.4, "Но тварь слушает. И глотает каждую ноту — бережно, как конфету."),
    (107.7, 113.0, "Внутри неё загораются огоньки. Ванная превращается в настоящую дискотеку."),
    (113.1, 116.3, "Дима решает назвать его Глотуном."),
    (117.6, 122.8, "Только Глотун всё раздувается… и раздувается… и краснеет."),
    (122.9, 124.3, "— Нет-нет-нет-нет…"),
    (124.4, 125.6, "БУУУУРП!"),
    (125.8, 130.7, "ТИК-ТАК! КАП-КАП! ЖЖЖЖ! ГАВ! А-А-А-А! БАМ! ДЗЫНЬ! ФЬЮЮЮ!"),
    (131.0, 137.0, "Все звуки разом вылетают на свободу. Дрожат стёкла. На улице воет сигнализация."),
    (137.1, 141.2, "А Глотун сдувается до размера хомячка. И смущённо икает."),
    (142.5, 144.4, "В коридоре загорается свет."),
    (144.7, 147.6, "— Дима! Три часа ночи! Что тут происходит?!"),
    (147.8, 149.6, "— Я… репетировал?"),
    (149.7, 151.1, "— Марш спать!"),
    (152.6, 157.3, "Дима ложится. Из кармана пижамы выглядывают три фиолетовых ушка."),
    (157.4, 159.0, "— И чтобы ни звука!"),
    (159.0, 159.8, "ХАП."),
    (159.8, 163.5, "С тех пор у Димы дома всегда очень тихо."),
    (167.7, 168.6, "Ик."),
]
BANNERS = [(0.2, "Тишина"), (21.96, "Светлячок в желе"), (41.84, "Проглоченный крик"),
           (58.4, "Погоня без звука"), (89.32, "Он просто голодный"), (116.46, "Отрыжка"),
           (141.36, "Мама"), (151.34, "Новый друг")]


def wrap(c, text, maxw):
    words = text.split(' ')
    lines, cur = [], ''
    for w_ in words:
        test = (cur + ' ' + w_).strip()
        if c.text_extents(test).x_advance > maxw and cur:
            lines.append(cur)
            cur = w_
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def draw_subs(c, t):
    for a, b, s in SUBS:
        if a <= t < b:
            al = min(1, (t - a) / 0.15, (b - t) / 0.15)
            font(c, 30, True)
            lines = wrap(c, s, 1080)
            lh = 40
            total = lh * len(lines)
            y0 = H - 22 - total
            maxw = max(c.text_extents(l).x_advance for l in lines)
            col(c, '#000000', 0.45 * al)
            rr(c, W / 2 - maxw / 2 - 18, y0 - 8, maxw + 36, total + 14, 12)
            c.fill()
            for i, l in enumerate(lines):
                e = c.text_extents(l)
                c.move_to(W / 2 - e.x_advance / 2, y0 + 30 + i * lh)
                c.text_path(l)
                col(c, '#000000', 0.9 * al)
                c.set_line_width(5)
                c.set_line_join(cairo.LINE_JOIN_ROUND)
                c.stroke_preserve()
                col(c, '#ffffff', al)
                c.fill()
            break


def draw_banner(c, t):
    for t0, s in BANNERS:
        if t0 <= t < t0 + 2.6:
            k = t - t0
            slide = sm(k / 0.35) * (1 - sm((k - 2.2) / 0.4))
            font(c, 28, True)
            e = c.text_extents(s)
            bw = e.x_advance + 44
            x0 = -bw + slide * (bw + 30)
            col(c, '#2b1240', 0.85)
            rr(c, x0, 28, bw, 52, 14)
            c.fill()
            col(c, '#ffd23f')
            rr(c, x0, 28, 8, 52, 4)
            c.fill()
            c.move_to(x0 + 24, 64)
            col(c, '#ffffff')
            c.show_text(s)


# ---------- камера ----------
def camera(c, cx, cy, z, shake=(0, 0)):
    c.translate(W / 2 + shake[0], H / 2 + shake[1])
    c.scale(z, z)
    c.translate(-cx, -cy)


def shake_at(t, t0, dur, amp):
    if t < t0 or t > t0 + dur:
        return (0, 0)
    k = 1 - (t - t0) / dur
    return (math.sin(t * 61) * amp * k, math.cos(t * 47) * amp * k)


def fly(t, t0, t1, p0, p1, arc=0.0):
    k = sm((t - t0) / (t1 - t0))
    x = lerp(p0[0], p1[0], k)
    y = lerp(p0[1], p1[1], k) - math.sin(k * PI) * arc
    return x, y, k


def dev2user(c, p):
    return c.device_to_user(*p)


def zzz(c, x, y, t):
    for i in range(3):
        ph = (t * 0.5 + i / 3) % 1
        onoma(c, 'z', x + ph * 60 + i * 6, y - ph * 90, 22 + ph * 18, '#d8e4ff', '#2b3270', 0.2, (1 - ph) * 0.9)


# ================= СЦЕНЫ =================
def scene_bedroom_night(c, t):
    z = lerp(1.0, 1.12, rng(t, 0, 21))
    camera(c, lerp(640, 520, rng(t, 0, 21)), lerp(360, 380, rng(t, 0, 21)), z)
    clock = bedroom(c, t, door=0.25, clock_t=t if t < 14 else 14)
    pillow(c)
    eyes = rng(t, 16.7, 17.05)
    look = (0, 0)
    if t > 18.6:
        look = (lerp(0, 1, rng(t, 18.6, 19.2)), -0.3)
    brows = 'up' if t > 16.8 else 'n'
    mouth = 'smile' if t < 14.5 else ('flat' if t < 20.6 else 'o')
    dima_head(c, 185, 418, 50, eyes=eyes, look=look, mouth=mouth, mo=0.3, brows=brows, rot=-0.12)
    blanket(c, t, math.sin(t * 1.5))
    if t < 9.0:
        zzz(c, 225, 360, t)
    # тиканье
    ticks = [0.5 + i for i in range(12)] + [12.52, 13.28, 14.0]
    for t0 in ticks:
        a = t - t0
        if 0 <= a < 1.6:
            if t0 < 9.0:
                x, y = clock[0] + 20 + a * 25, clock[1] - 40 - a * 55
                al = 1 - lin(a, 1.0, 1.6)
                s = 1
            else:
                x, y, k = fly(t, t0, t0 + 1.1, (clock[0] + 20, clock[1] - 40), (1190, 400), 60)
                al = 1 - lin(a, 0.9, 1.1)
                s = 1 - 0.6 * k
            if t0 == 14.0:
                al *= 1 - lin(a, 0.15, 0.3)
            item(c, 'tick', x, y, 16 * s, t, al)
            onoma(c, 'тик' if t0 != 14.0 else 'т…', x + 30, y - 10, 20 * s, '#ffd24a', '#3a2a10', -0.15, al)
    # кап
    for i in range(6):
        t0 = 5.2 + i * 1.25
        a = t - t0
        if t0 < 11.4 and 0 <= a < 1.4:
            if t0 < 9.0:
                x, y = 1150 - a * 30, 470 - a * 20
                al = 1 - lin(a, 0.9, 1.4)
            else:
                x, y, k = fly(t, t0, t0 + 1.0, (1150, 470), (1215, 420), 30)
                al = 1 - lin(a, 0.8, 1.0)
            item(c, 'drop', x, y, 14, t, al)
            onoma(c, 'кап', x - 34, y - 6, 18, '#7fd0ff', '#10304a', 0.1, al)
    # гул холодильника
    if 6.2 < t < 10.6:
        al = rng(t, 6.2, 6.6) * (1 - rng(t, 9.6, 10.4))
        k = rng(t, 9.6, 10.4)
        item(c, 'hum', lerp(1120, 1205, k), lerp(330, 360, k), 20 * (1 - 0.5 * k), t, al)
        onoma(c, 'ж-ж-ж', 1100 - 40 * (1 - k), 290, 18, '#9dff7a', '#1a3a10', 0, al * (1 - k))
    # щелчок пальцами
    if 17.3 < t < 20.2:
        a = rng(t, 17.3, 17.6) * (1 - rng(t, 19.8, 20.2))
        col(c, SKIN, a)
        c.arc(262, 398, 14, 0, TAU)
        c.fill()
        if t > 17.8:
            k = lin(t, 17.8, 18.8)
            c.set_dash([6, 7])
            col(c, '#ffffff', 0.6 * (1 - k))
            c.set_line_width(3)
            c.arc(262, 398, 20 + 50 * k, 0, TAU)
            c.stroke()
            c.set_dash([])
            onoma(c, '(щёлк?)', 330, 330, 22, '#9aa4c8', '#1d2350', -0.1, 0.8 * (1 - lin(t, 19.3, 20.0)))
    if 20.6 < t < 21.9:
        sc, al = pop(t, 20.6, 1.3)
        col(c, '#ffffff', 0.85 * al)
        rr(c, 230, 300, 120, 48, 16)
        c.fill()
        font(c, 22, True)
        col(c, '#2b3270', al)
        c.move_to(246, 332)
        c.show_text('Чего?..')
    # «тишина» — синий фильтр
    sil = rng(t, 14.3, 15.0)
    if sil > 0:
        col(c, '#0a1030', 0.25 * sil)
        c.rectangle(*BIG)
        c.fill()


def kitchen_scene(c, t):
    # камера
    zoom = 1.0 + 0.35 * rng(t, 31.6, 33.0) * (1 - rng(t, 38.4, 39.6))
    ccx = lerp(640, 900, rng(t, 31.6, 33.0) * (1 - rng(t, 38.4, 39.6)))
    ccy = lerp(360, 470, rng(t, 31.6, 33.0) * (1 - rng(t, 38.4, 39.6)))
    sh = shake_at(t, 45.5, 1.2, 7)
    camera(c, ccx, ccy + 40, zoom, sh)
    kitchen(c, t)
    # состояние Глотуна
    items = [('tick',), ('drop',), ('hum',)]
    if t > 46.7:
        items.append(('bolt',))
    if t > 54.9:
        items.append(('squeak',))
    lean = 0.45 if t < 39.0 else lerp(0.45, -0.7, rng(t, 39.0, 40.6))
    wob = 1.0 + 2.2 * rng(t, 30.4, 31.0) * (1 - rng(t, 31.8, 32.5))
    jx = math.sin(t * 40) * 3 * rng(t, 30.4, 31.0) * (1 - rng(t, 31.8, 32.5))
    perk = 1.0 + 0.4 * math.sin(t * 6) * rng(t, 31.9, 32.3) * (1 - rng(t, 34.8, 35.2))
    bright = 1.0 + 0.8 * rng(t, 35.4, 36.2) * (0.6 + 0.4 * math.sin(t * 5)) * (1 - rng(t, 38.6, 39.2))
    mouth = 0.0
    mouth = max(mouth, rng(t, 46.25, 46.62) * (1 - rng(t, 46.7, 47.1)))
    mouth = max(mouth, 0.65 * rng(t, 54.55, 54.82) * (1 - rng(t, 54.9, 55.2)))
    squint = rng(t, 47.2, 47.6) * (1 - rng(t, 50.5, 50.8))
    hop = math.sin(lin(t, 50.78, 51.1) * PI) * 22
    gx, gy = 965 + jx, 640 - hop
    gm = glotun(c, gx, gy, 74, t, mouth=mouth, lean=lean, perk=perk, items=items, wob=wob,
                bright=bright, squint=squint)
    if 50.78 < t < 51.8:
        sc, al = pop(t, 50.78, 1.0)
        onoma(c, 'ик', gx + 70, gy - 190, 26, '#ffd0f0', '#3a1050', 0.2, al, sc)
    # Дима
    if t < 23.6:
        dx = -120
    else:
        dx = lerp(-120, 380, rng(t, 23.6, 26.6))
    walking = 23.6 < t < 26.6
    ph = t * 7
    legF = 22 * math.sin(ph) if walking else 4
    legB = -22 * math.sin(ph) if walking else -4
    bob = abs(math.sin(ph)) * 6 if walking else 0
    eyes, mouth_d, mo, brows, look = 1.0, 'flat', 0.4, 'n', (1, 0)
    cheeks, chest, armF, armB, tgtF = 0.0, 1.0, 75, 12, None
    holdF = 'flash'
    lean_d = 0
    if t > 27.4:
        brows, mouth_d, mo = 'up', 'o', 0.5
    if t > 39.0:
        brows, mouth_d, mo, eyes = 'up', 'o', 0.8, 1.1
    if 43.3 < t < 45.45:
        k = rng(t, 43.3, 44.8)
        chest = 1 + 0.25 * k
        cheeks = k
        mouth_d = 'pressed'
        bob = 10 * k
    if 45.45 < t < 46.8:
        mouth_d, mo, brows = 'scream', 1.0, 'up'
        armF, armB = 150, 150
        holdF = None
        eyes = 0.15
    if 46.8 < t < 51.6:
        mouth_d, mo, brows, eyes = 'o', 0.6, 'worried', 1.1
        armF = 40
        holdF = None
    if 51.6 < t < 53.4:
        tgtF = (10, -248)
        holdF = None
        mouth_d, mo, brows = 'worried', 0.4, 'worried'
        look = (0, 0.6)
    if 53.4 < t < 54.9:
        mouth_d, mo, brows = 'o', 0.7, 'up'
        holdF = None
        armF = 30
    if t > 54.9:
        mouth_d, brows, eyes, holdF = 'frown', 'worried', 1.1, None
        armF, armB = 20, 20
    mouth_dev, hand_dev = dima(c, dx, 640, 0.95, 1, eyes, look, mouth_d, mo, brows, cheeks,
                               armB=armB, armF=armF, tgtF=tgtF, legB=legB, legF=legF, bob=bob,
                               chest=chest, holdF=holdF, lean=lean_d)
    mouth_w = dev2user(c, mouth_dev)
    hand_w = dev2user(c, hand_dev)
    # луч фонарика
    if holdF == 'flash' and t > 23.4:
        hx_, hy_ = hand_w[0] + 32, hand_w[1] - 4
        tgt_y = 560 if t > 27.4 else 600
        g = cairo.LinearGradient(hx_, hy_, hx_ + 560, tgt_y)
        g.add_color_stop_rgba(0, 1, 0.97, 0.75, 0.45)
        g.add_color_stop_rgba(1, 1, 0.97, 0.75, 0.0)
        c.set_source(g)
        path_poly(c, [(hx_, hy_ - 6), (hx_ + 600, tgt_y - 140), (hx_ + 600, tgt_y + 120), (hx_, hy_ + 6)])
        c.fill()
    # крик-молния
    if 45.5 < t < 46.7:
        x, y, k = fly(t, 45.5, 46.62, (mouth_w[0] + 30, mouth_w[1]), gm, 50)
        bolt_icon(c, x, y, 34 - 14 * k, 0.4 + t * 3, KCOL['bolt'])
        glow(c, x, y, 60, KCOL['bolt'], 0.5)
    sc, al = pop(t, 45.5, 1.3)
    onoma(c, 'А-А-А-А!', mouth_w[0] + 40, mouth_w[1] - 120, 54, '#fff04a', '#5a2a00', -0.12, al, sc)
    sc, al = pop(t, 46.66, 1.1)
    onoma(c, 'ХАП!', gx, gy - 230, 64, '#ff8fd0', '#2b1240', 0.1, al, sc)
    # писк
    if 53.6 < t < 54.85:
        x, y, k = fly(t, 53.6, 54.82, (mouth_w[0] + 20, mouth_w[1]), gm, 40)
        bubble_icon(c, x, y, 9, KCOL['squeak'])
        onoma(c, 'пи', x, y - 22, 16, '#ffd0f0', '#3a1050', 0, 0.9)
    sc, al = pop(t, 54.84, 1.0)
    onoma(c, 'ХАП!', gx - 10, gy - 220, 48, '#ff8fd0', '#2b1240', -0.1, al, sc)


def r_growth(t):
    steps = [(0, 62), (63.26, 70), (66.52, 80), (68.12, 92), (71.58 + 1.4, 112), (72.48 + 1.4, 150), (73.5 + 1.4, 205)]
    R = steps[0][1]
    for i in range(1, len(steps)):
        t0, v = steps[i]
        prev = steps[i - 1][1]
        if t >= t0:
            k = lin(t, t0, t0 + 0.35)
            ov = math.sin(k * PI) * 0.12 * (v - prev)
            R = lerp(prev, v, sm(k)) + ov
    return R


def hallway_scene(c, t):
    # прокрутка
    def speed(tt):
        return 460 * rng(tt, 60.0, 60.6) * (1 - rng(tt, 63.9, 64.9))
    # интеграл скорости — грубо
    scroll = 0.0
    tt = 58.4
    step = 1 / 48
    while tt < t:
        scroll += speed(tt) * step
        tt += step
    sh = shake_at(t, 64.1, 0.6, 8)
    sh2 = shake_at(t, 67.22, 0.4, 5)
    sh3 = shake_at(t, 68.6, 0.4, 5)
    camera(c, 640, 400, 1.0, (sh[0] + sh2[0] + sh3[0], sh[1] + sh2[1] + sh3[1]))
    hallway(c, t, scroll)
    floor = 650
    # стул
    hit = 63.0
    stool_x = 840 + (hit - t) * 460 if t < hit else None
    if t >= hit:
        # после удара: летит назад вместе с прокруткой
        s_hit = 0.0
        tt = 58.4
        while tt < hit:
            s_hit += speed(tt) * step
            tt += step
        stool_x = 840 - (scroll - s_hit) - 60 * rng(t, hit, hit + 0.5)
    rot = 0 if t < hit else -1.5 * rng(t, hit, hit + 0.6)
    lift = 0 if t < hit else math.sin(lin(t, hit, hit + 0.6) * PI) * 70
    if stool_x is not None and -200 < stool_x < 1500 and t < 64.75:
        c.save()
        c.translate(stool_x, floor - lift)
        c.rotate(rot)
        col(c, '#a0623a')
        c.rectangle(-45, -95, 90, 16)
        c.fill()
        c.set_line_width(10)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        for lx in (-35, 35):
            c.move_to(lx, -80)
            c.line_to(lx * 1.15, 0)
        c.stroke()
        c.restore()
    # Глотун
    R = r_growth(t)
    gx = 300 if t < 60.0 else 300
    if t < 60.2:
        gx = lerp(-150, 290, rng(t, 58.4, 60.0))
    if t > 64.8:
        gx = lerp(300, 470, rng(t, 64.8, 75.5))
    moving = t < 64.6 or 70 < t < 75.6
    legph = t * 14 if moving else None
    hop = abs(math.sin(t * 7)) * 18 if moving else 0
    items = [('tick',), ('drop',), ('hum',), ('bolt',), ('squeak',)]
    if t > 63.3:
        items.append(('bam',))
    if t > 66.55:
        items.append(('star',))
    if t > 68.15:
        items.append(('star',))
    mouth = 0
    for th_ in (63.26, 66.52, 68.12):
        mouth = max(mouth, rng(t, th_ - 0.3, th_) * (1 - rng(t, th_ + 0.05, th_ + 0.35)))
    gm = glotun(c, gx, floor - hop, R, t, mouth=mouth, lean=0.5, items=items, legph=legph)
    # Дима
    ph = t * 13
    running = 60.0 < t < 64.6
    face = 1
    dx = 760
    eyes, mouth_d, mo, brows, look = 1.1, 'o', 0.7, 'up', (-1, 0)
    armF, armB, legF, legB, bob, lean = 10, 10, 4, -4, 0, 0
    holdF = holdB = None
    tgtF = tgtB = None
    if t < 60.0:
        face = 1
        look = (-1, 0)
        mouth_d = 'scream'
        mo = 0.5
        dx = lerp(560, 760, rng(t, 58.4, 60.0))
        ph = t * 13
        legF, legB = 35 * math.sin(ph), -35 * math.sin(ph)
        armF, armB = -40 * math.sin(ph), 40 * math.sin(ph)
        bob = abs(math.sin(ph)) * 10
    if running:
        legF, legB = 42 * math.sin(ph), -42 * math.sin(ph)
        armF, armB = -50 * math.sin(ph), 50 * math.sin(ph)
        bob = abs(math.sin(ph)) * 12
        lean = 10
        if 62.95 < t < 63.6:
            lean = 10 + 15 * math.sin(lin(t, 62.95, 63.6) * PI)
            mouth_d, mo = 'scream', 0.6
    if t >= 64.6:
        face = -1
        look = (1, 0)
        holdF, holdB = 'lid', 'pot'
        if t < 65.4:
            armF, armB = 60, 60
        else:
            clash = 0
            for tc in (65.82, 67.2):
                clash = max(clash, math.exp(-((t - tc) / 0.18) ** 2))
            tgtF = (lerp(95, 40, clash), -200)
            tgtB = (lerp(-95, 30, clash), -190)
            mouth_d, mo, brows = 'grin', 0.5, 'angry'
        if t > 69.9:
            holdF = holdB = None
            tgtF = tgtB = None
            armF, armB = 30, 30
            mouth_d, mo, brows = 'o', 0.8, 'up'
            dx = lerp(760, 930, rng(t, 70.0, 75.3))
            if t > 75.2:
                face = 1
                dx = lerp(930, 1500, rng(t, 75.25, 75.9))
                ph = t * 14
                legF, legB = 42 * math.sin(ph), -42 * math.sin(ph)
                armF, armB = -50 * math.sin(ph), 50 * math.sin(ph)
    mdev, hdev = dima(c, dx, floor, 0.9, face, eyes, look, mouth_d, mo, brows, 0, armB=armB, armF=armF,
                      tgtF=tgtF, tgtB=tgtB, legB=legB, legF=legF, bob=bob, lean=lean, holdF=holdF, holdB=holdB)
    hand_w = dev2user(c, hdev)
    # БАМ
    if 64.1 <= t < 64.7 and stool_x is not None:
        pass
    sc, al = pop(t, 64.1, 0.6)
    if al > 0:
        bx_, by_ = gx + 120, floor - 150
        burst(c, bx_, by_, 70 * sc, t, KCOL['bam'], al)
        onoma(c, 'БАМ!', bx_, by_, 40, '#ffffff', '#5a1a00', -0.1, al, sc)
    if 64.65 < t < 64.7 + 0.5:
        pass
    if 64.6 < t < 64.66 + 0.1:
        pass
    # облачко БАМ летит в рот
    if 64.4 <= t < 64.66:
        x, y, k = fly(t, 64.4, 64.66, (gx + 120, floor - 150), gm, 20)
        burst(c, x, y, 40 * (1 - k * 0.6), t, KCOL['bam'], 0.9)
    sc, al = pop(t, 64.66, 0.9)
    onoma(c, 'ХАП!', gx, floor - R * 1.9 - 60, 52, '#ff8fd0', '#2b1240', 0.1, al, sc)
    # ДЗЫНЬ
    for tz, th_ in ((65.82, 66.52), (67.2, 68.12)):
        sc, al = pop(t, tz, 0.7)
        if al > 0 and t < th_ - 0.25:
            star_icon(c, hand_w[0] - 30, hand_w[1] - 20, 44 * sc, t * 3, KCOL['star'], al)
            onoma(c, 'ДЗЫНЬ!', hand_w[0] - 30, hand_w[1] - 100, 40, '#c8ffff', '#0a3a4a', 0.12, al, sc)
        if tz + 0.2 < t < th_:
            x, y, k = fly(t, tz + 0.2, th_, (hand_w[0] - 30, hand_w[1] - 20), gm, 60)
            star_icon(c, x, y, 34 - 14 * k, t * 4, KCOL['star'], 0.95)
            glow(c, x, y, 50, KCOL['star'], 0.4)
        sc, al = pop(t, th_, 0.8)
        onoma(c, 'ХАП!', gx, floor - R * 1.9 - 60, 46, '#ff8fd0', '#2b1240', -0.1, al, sc)
    # подписи роста
    for t0, s in ((72.98, 'С КОТА!'), (73.88, 'С СОБАКУ!'), (74.9, 'С КРЕСЛО!')):
        sc, al = pop(t, t0, 0.95 if t0 < 74 else 1.0)
        onoma(c, s, gx + R * 0.2, floor - R * 1.95 - 40, 44, '#ffd23f', '#2b1240', -0.08, al, sc)


def bath_items(t):
    items = [('tick',), ('drop',), ('hum',), ('bolt',), ('squeak',), ('bam',), ('star',), ('star',)]
    for i, tn in enumerate(note_times()):
        if t > tn + NOTE_FLY:
            items.append(('note', NOTE_COLS[i % len(NOTE_COLS)]))
    return items


NOTE_FLY = 1.1


def note_times():
    return [103.0 + i * 0.55 for i in range(16)]


def bathroom_scene(c, t):
    floor = 640
    # камера и тряска
    sh = (0, 0)
    for a, b, amp in ((124.44, 2.0, 14), (125.8, 5.0, 5), (131.0, 3.2, 6)):
        s_ = shake_at(t, a, b, amp)
        sh = (sh[0] + s_[0], sh[1] + s_[1])
    z = 1.0
    ccx, ccy = 640, 395
    if 79.6 < t < 89.2:
        z = 1.0 + 0.06 * rng(t, 79.6, 83.5)
    camera(c, ccx, ccy, z, sh)
    door_open = 0.0
    if t > 142.7:
        door_open = 0.55 * rng(t, 142.7, 143.8)
    # зубная щётка
    brush = None
    if t > 133.9:
        k = lin(t, 133.9, 134.6)
        if k < 1:
            brush = (612 + 60 * k, 330 + 280 * k * k, 0.2 + 5 * k)
        else:
            brush = (672, 622, 1.57)
    mshake = (math.sin(t * 50) * 4, 0) if 133.5 < t < 137 else (0, 0)
    bathroom(c, t, door_open, mshake, brush)
    # сигнализация в окне
    if 135.9 < t < 138.5:
        f = 1 if int(t * 6) % 2 == 0 else 0
        glow(c, 860, 140, 120, hx('#ff3a3a') if f else hx('#3a6aff'), 0.7)
        sc, al = pop(t, 135.98, 2.4)
        onoma(c, 'УИУ-УИУ!', 860, 230, 28, '#ffffff', '#5a0a1a', 0.08, al, sc)
    # диско-огни
    disco = rng(t, 107.7, 109.0) * (1 - rng(t, 116.4, 117.6))
    if disco > 0:
        c.save()
        c.set_operator(cairo.OPERATOR_ADD)
        for i in range(7):
            ang = t * (0.6 + i * 0.13) + i * 1.3
            px = 640 + math.cos(ang) * 520
            py = 300 + math.sin(ang * 1.3) * 220
            glow(c, px, py, 130, NOTE_COLS[i % 6], 0.35 * disco)
        c.restore()

    # ---------- Глотун ----------
    items = bath_items(t)
    R, gx, sy, mouth, lean, perk, red, wob, squint, alpha = 0, 760, 1.0, 0.0, -0.5, 1.0, 0.0, 1.0, 0.0, 0.9
    bright, item_speed, tongue = 1.0, 1.0, 0.0
    show_g = True
    gy = floor
    if t < 77.6:
        show_g = False
    elif t < 79.7:
        show_g = False
    elif t < 81.4:
        k = rng(t, 79.7, 81.4)
        R = lerp(60, 235, k)
        sy = lerp(0.25, 1.0, k)
        gx = lerp(1000, 760, k)
    elif t < 89.2:
        R = 235
        k = rng(t, 83.6, 85.0)
        gx = lerp(760, 690, k) + math.sin(max(0, t - 85.2) * 7) * 14 * rng(t, 85.2, 85.6) * (1 - rng(t, 88.2, 88.8))
        lean = -0.6
        squint = rng(t, 84.2, 84.8)
    elif t < 116.4:
        R = 225
        gx = 760 + math.sin(t * 2.4) * 18 * rng(t, 101.8, 103)
        perk = 1.0 + 0.35 * rng(t, 101.84, 102.4)
        lean = -0.5 + math.sin(t * 2.4) * 0.3 * rng(t, 101.8, 103)
        squint = 0.6 * rng(t, 104, 105) * (1 - rng(t, 113, 113.5))
        bright = 1 + 0.6 * disco
        # открывает рот на ноты
        for tn in note_times():
            ta = tn + NOTE_FLY
            mouth = max(mouth, 0.35 * rng(t, ta - 0.25, ta) * (1 - rng(t, ta + 0.02, ta + 0.2)))
        if 100.9 < t < 101.9:
            mouth = 0
    elif t < 137.1:
        swell = rng(t, 117.6, 122.6)
        R = lerp(225, 268, swell)
        red = rng(t, 119.5, 122.0)
        wob = 1 + 2.5 * swell
        gx = 760 + math.sin(t * 30) * 5 * swell
        item_speed = 1 + 6 * swell
        perk = 1 + 0.5 * swell
        squint = 0
        if t > 124.3:
            mouth = rng(t, 124.25, 124.5) * (1 - 0.5 * rng(t, 125.3, 126)) * (1 - rng(t, 130.4, 131.2))
            items = [] if t > 124.6 else items
            red = red * (1 - rng(t, 124.5, 126))
            wob = 1.5
            item_speed = 1
    elif t < 140.9:
        k = rng(t, 137.1, 139.6)
        R = lerp(268, 26, k)
        items = []
        red = 0
        hop = math.sin(lin(t, 139.76, 140.1) * PI) * 26
        gy = floor - hop
        squint = 0.4
        perk = 1.2
    elif t < 142.4:
        R = 26
        items = []
        # прыгает в карман Диме
        p0 = (760, floor)
        p1 = (420 + 25, floor - 125)
        x, y, k = fly(t, 141.2, 142.2, p0, p1, 160)
        gx, gy = x, y
        if k >= 1:
            show_g = False
    else:
        show_g = False

    # лужа под дверью
    if 77.6 < t < 81.4:
        k = rng(t, 77.6, 79.4)
        k2 = rng(t, 79.7, 80.6)
        pcx = lerp(1110, 1000, k)
        prx = lerp(30, 150, k) * (1 - k2)
        if prx > 1:
            col(c, PURP, 0.85)
            ell(c, pcx, floor - 8, prx, 16 * (0.4 + 0.6 * k))
            c.fill()
            for i in range(3):
                if t > 78.3 + i * 0.25:
                    kk = rng(t, 78.3 + i * 0.25, 78.7 + i * 0.25)
                    ear(c, pcx - 60 + i * 55, floor - 12, 34 * kk * (1 - k2), 0.0, -0.4 + math.sin(t * 4 + i) * 0.2, 0)
    gm = (gx, floor - 200)
    if show_g and R > 0:
        gm = glotun(c, gx, gy, R, t, mouth=mouth, lean=lean, perk=perk, red=red, items=items, wob=wob,
                    squint=squint, alpha=alpha, sy=sy, bright=bright, item_speed=item_speed)
    # сердечки при «бодании»
    if 85.2 < t < 89.2:
        for i in range(5):
            ph = ((t - 85.2) * 0.6 + i / 5) % 1
            hx_, hy_ = 520 + i * 25 + math.sin(ph * 6 + i) * 10, 330 - ph * 200
            heart(c, hx_, hy_, 12 + 6 * (i % 2), (1 - ph) * rng(t, 85.2, 85.8))

    # ---------- Дима ----------
    face = 1
    dx = 360
    eyes, mouth_d, mo, brows, look = 1.0, 'o', 0.6, 'up', (1, 0)
    armF, armB, legF, legB, bob, lean_d = 10, 10, 4, -4, 0, 0
    tgtF = tgtB = None
    crouch, sit = 0.0, 0.0
    harm = False
    happy = False
    head_rot = 0.0
    if t < 77.0:
        face = -1
        dx = lerp(1060, 360, rng(t, 75.9, 76.9))
        ph = t * 14
        legF, legB = 42 * math.sin(ph), -42 * math.sin(ph)
        armF, armB = -50 * math.sin(ph), 50 * math.sin(ph)
        bob = abs(math.sin(ph)) * 12
        mouth_d = 'scream'
    elif t < 79.6:
        look = (1, 0.3)
        bob = abs(math.sin(t * 9)) * 3
        mouth_d, mo = 'o', 0.5
        brows = 'worried'
    elif t < 85.4:
        crouch = rng(t, 80.0, 80.6)
        tgtF = (40, -330)
        tgtB = (-40, -330)
        eyes = 0.1
        mouth_d = 'worried'
        brows = 'worried'
        bob = math.sin(t * 30) * 2
    elif t < 89.2:
        crouch = 1 - rng(t, 86.5, 87.5)
        eyes = 1.15
        look = (1, -0.4)
        mouth_d, mo, brows = ('o', 0.5, 'up') if t < 87.4 else ('smile', 0.5, 'n')
        armF, armB = 25, 25
    elif t < 116.4:
        look = (1, -0.4)
        brows = 'n'
        mouth_d = 'smile'
        if 89.3 < t < 92.4:
            mouth_d, mo, brows = 'o', 0.5, 'up'
        if 95.8 < t < 96.7:
            armF = lerp(10, 30, rng(t, 95.8, 96.2))
        if t > 96.6:
            k = rng(t, 96.6, 97.6)
            tgtF = (lerp(70, 34, k), lerp(-130, -278, k))
            tgtB = (lerp(-70, -34, k), lerp(-130, -278, k))
            harm = k > 0.95
            if harm:
                mouth_d = 'pressed'
                cheeks = 0
        if 99.2 < t < 100.4:
            brows = 'worried'
        if t > 107.7:
            bob = abs(math.sin(t * 5.2)) * 10
            head_rot = math.sin(t * 5.2) * 0.08
        if 113.2 < t < 116.4:
            pass
    elif t < 141.2:
        look = (1, -0.4)
        tgtF = (34, -278)
        tgtB = (-34, -278)
        harm = True
        mouth_d = 'pressed'
        brows = 'worried' if t > 119 else 'n'
        eyes = 1.0 + 0.15 * rng(t, 119, 121)
        if t > 122.9:
            harm = False
            tgtF = (90, -200)
            tgtB = (-90, -200)
            mouth_d, mo = 'worried', 0.5
            head_rot = math.sin(t * 16) * 0.12 * (1 - rng(t, 123.8, 124.2))
        if t > 124.4:
            k = 1 - rng(t, 126.0, 127.5)
            lean_d = -14 * k
            eyes = 0.1 if k > 0.5 else 1.1
            mouth_d, mo = 'o', 0.8
            head_rot = 0
            tgtF = (lerp(90, 60, 1 - k), -230)
            tgtB = (lerp(-90, -60, 1 - k), -230)
            brows = 'up'
            look = (0.6 * math.sin(t * 2), -0.6)
        if t > 137.2:
            look = (1, 0.6)
            mouth_d, mo = 'o', 0.4
        if t > 140.2:
            sit = rng(t, 140.2, 141.0)
            tgtF = tgtB = None
            armF, armB = 30, 30
    else:
        sit = 1.0
        look = (1, 0)
        armF, armB = 30, 30
        mouth_d = 'smile'
        if t > 142.7:
            look = (1, -0.2)
            mouth_d, mo, brows = 'o', 0.4, 'up'
        if t > 147.8:
            mouth_d, happy, brows = 'grin', True, 'n'
            head_rot = math.sin(t * 3) * 0.05
            tgtF = (70, -260)
            armB = 25
        if t > 149.7:
            mouth_d, happy, brows = 'frown', False, 'worried'
            tgtF = None

    def pocket_fn(cc):
        if t > 142.2 and t < 151.3:
            # три ушка торчат из кармана
            pk = rng(t, 142.6, 143.0) * (1 - rng(t, 143.4, 143.7))
            if pk > 0:
                for i in range(3):
                    ear(cc, 18 + i * 9, -172, 14 * pk, 0, -0.2 + i * 0.2, 0)

    mdev, hdev = dima(c, dx, floor, 0.95, face, eyes, look, mouth_d, mo, brows, 0, armB=armB, armF=armF,
                      tgtF=tgtF, tgtB=tgtB, legB=legB, legF=legF, bob=bob, lean=lean_d, crouch=crouch,
                      sit=sit, harmonica=harm, happy_closed=happy, head_rot=head_rot, pocket=pocket_fn)
    mouth_w = dev2user(c, mdev)
    # гармошка падает
    if 122.95 < t < 124.4:
        k = lin(t, 122.95, 123.45)
        x = mouth_w[0] + 10 * k
        y = mouth_w[1] + (floor - mouth_w[1] - 10) * k * k
        c.save()
        c.translate(x, y)
        c.rotate(k * 3)
        rr(c, -34, -8, 68, 16, 4)
        col(c, '#cfd6df')
        c.fill()
        c.restore()
    if 91.0 < t < 92.6:
        sc, al = pop(t, 91.05, 1.5)
        onoma(c, '!', mouth_w[0], mouth_w[1] - 150, 70, '#ffd23f', '#2b1240', 0.1, al, sc)
    # фальшивая нота
    if 100.4 < t < 102.2:
        k = lin(t, 100.4, 102.2)
        c.set_line_width(6)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        col(c, '#ff9fd8', 1 - k)
        c.new_path()
        for i in range(30):
            u = i / 29
            px = mouth_w[0] + 40 + u * 260 * (0.3 + k)
            py = mouth_w[1] - 20 + math.sin(u * 18 + t * 10) * 14 * (1 + u) - u * 60
            (c.move_to if i == 0 else c.line_to)(px, py)
        c.stroke()
        onoma(c, 'фьююю-иии…', mouth_w[0] + 170, mouth_w[1] - 120, 30, '#ff9fd8', '#3a1050', -0.15, 1 - k)
    # ноты летят в рот
    for i, tn in enumerate(note_times()):
        if tn < t < tn + NOTE_FLY:
            x, y, k = fly(t, tn, tn + NOTE_FLY, (mouth_w[0] + 40, mouth_w[1] - 10), gm, 90)
            clr = NOTE_COLS[i % len(NOTE_COLS)]
            glow(c, x, y, 34, clr, 0.6)
            note_icon(c, x, y, 26 - 8 * k, clr, 1, math.sin(t * 6 + i) * 0.3)
    # имя
    if 113.1 < t < 116.6:
        sc, al = pop(t, 113.15, 3.4)
        onoma(c, 'ГЛОТУН', 760, 110, 64, '#c9a2ff', '#2b1240', -0.05, al, sc)
        for i in range(6):
            a_ = t * 2 + i * TAU / 6
            star_icon(c, 760 + math.cos(a_) * 200, 110 + math.sin(a_) * 50, 9, t, hx('#ffe07a'), al)
    # БУРП и вылетающие звуки
    sc, al = pop(t, 124.44, 1.8)
    onoma(c, 'БУУУУРП!', 640, 140, 96, '#9dff7a', '#1a3a10', -0.06, al, sc)
    outs = [(125.82, 'tick', 'ТИК-ТАК!', -2.6), (126.38, 'drop', 'КАП-КАП!', -1.9), (126.9, 'hum', 'ЖЖЖЖ!', -0.4),
            (127.5, 'bark', 'ГАВ!', -2.2), (127.92, 'bolt', 'А-А-А-А!', -1.0), (128.68, 'bam', 'БАМ!', -2.9),
            (129.34, 'star', 'ДЗЫНЬ!', -0.7), (130.06, 'note', 'ФЬЮЮЮ!', -1.5)]
    if 124.4 < t < 138.5:
        whirl = rng(t, 130.8, 132.0)
        fade = 1 - rng(t, 137.2, 138.4)
        mouth_c = gm
        for j, (t0, kind, label, ang) in enumerate(outs):
            if t < t0:
                continue
            a = t - t0
            d = 460 * (1 - math.exp(-a * 2.2))
            px = mouth_c[0] + math.cos(ang) * d * 1.2
            py = mouth_c[1] + math.sin(ang) * d * 0.7
            # вихрь по комнате
            wa = t * 1.6 + j * TAU / len(outs)
            wx = 640 + math.cos(wa) * 470
            wy = 330 + math.sin(wa) * 190
            px = lerp(px, wx, whirl)
            py = lerp(py, wy, whirl)
            clr = NOTE_COLS[j % 6] if kind == 'note' else None
            item(c, kind, px, py, 32, t + j, fade, 1.2, clr)
            lsc, lal = pop(t, t0, 1.6)
            onoma(c, label, px, py - 55, 34, '#ffffff', '#2b1240', math.sin(j) * 0.2, lal * fade, lsc)
        # плюс ноты из живота — вихрь
        for i in range(10):
            a = t - 124.5
            if a < 0:
                break
            ang = -PI / 2 + (i - 4.5) * 0.35
            d = 520 * (1 - math.exp(-a * 3))
            px = mouth_c[0] + math.cos(ang) * d
            py = mouth_c[1] + math.sin(ang) * d * 0.6
            wa = t * 1.6 + PI / 10 + i * TAU / 10
            px = lerp(px, 640 + math.cos(wa) * 380, whirl)
            py = lerp(py, 330 + math.sin(wa) * 150, whirl)
            note_icon(c, px, py, 22, NOTE_COLS[i % 6], 0.9 * fade, t * 3 + i)
    if 139.76 < t < 140.9:
        sc, al = pop(t, 139.76, 1.1)
        onoma(c, 'ик', gx + 40, gy - 90, 24, '#ffd0f0', '#3a1050', 0.2, al, sc)
    # мама — свет и тень
    if t > 143.2:
        k = rng(t, 143.2, 143.9)
        mx0 = 1060 + 60
        c.save()
        # тень на полу и стене
        col(c, '#0a0814', 0.55 * k)
        path_poly(c, [(mx0, 625), (mx0 + 50, 625), (mx0 - 300 * k, 760), (mx0 - 520 * k, 760)])
        c.fill()
        # силуэт в дверях
        col(c, '#140c1c', 0.95 * k)
        sx0 = mx0 + 30
        ell(c, sx0, 330, 34, 40)
        c.fill()
        # растрёпанная причёска
        for i in range(9):
            a_ = PI + i * PI / 8
            ell(c, sx0 + math.cos(a_) * 38, 318 + math.sin(a_) * 34, 16, 14)
            c.fill()
        path_poly(c, [(sx0 - 40, 370), (sx0 + 40, 370), (sx0 + 60, 620), (sx0 - 60, 620)])
        c.fill()
        # руки
        c.set_line_width(18)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        if t < 149.6:
            c.move_to(sx0 - 38, 390)
            c.line_to(sx0 - 75, 450)
            c.line_to(sx0 - 40, 490)
            c.move_to(sx0 + 38, 390)
            c.line_to(sx0 + 75, 450)
            c.line_to(sx0 + 40, 490)
        else:
            c.move_to(sx0 + 38, 390)
            c.line_to(sx0 + 75, 450)
            c.line_to(sx0 + 40, 490)
            c.move_to(sx0 - 38, 390)
            c.line_to(sx0 - 140, 360)
        c.stroke()
        c.restore()
        if 144.8 < t < 147.6:
            sc, al = pop(t, 144.8, 2.8)
            onoma(c, 'ДИМА!', sx0 - 140, 240, 46, '#ffffff', '#3a0a0a', -0.1, al, sc)
        if 149.75 < t < 151.3:
            sc, al = pop(t, 149.75, 1.55)
            onoma(c, 'МАРШ СПАТЬ!', sx0 - 230, 250, 42, '#ffffff', '#3a0a0a', 0.05, al, sc)
    if 147.9 < t < 149.6:
        # капля пота
        col(c, '#9fd8ff')
        drop_icon(c, mouth_w[0] + 55, mouth_w[1] - 85, 12, hx('#9fd8ff'))


def heart(c, x, y, s, a):
    if a <= 0:
        return
    c.save()
    c.translate(x, y)
    c.new_path()
    c.move_to(0, s * 0.35)
    c.curve_to(-s, -s * 0.3, -s * 0.5, -s, 0, -s * 0.45)
    c.curve_to(s * 0.5, -s, s, -s * 0.3, 0, s * 0.35)
    col(c, '#ff6f9a', a)
    c.fill()
    c.restore()


def bedroom_end(c, t):
    z = lerp(1.05, 1.28, rng(t, 151.3, 163.5))
    camera(c, lerp(560, 380, rng(t, 151.3, 163.5)), lerp(380, 420, rng(t, 151.3, 163.5)), z)
    bedroom(c, t, door=0.5, clock_t=t)
    pillow(c)
    giggle = rng(t, 159.6, 160.0)
    eyes = 1.0
    happy = giggle > 0.5
    mouth = 'smile'
    if happy:
        mouth = 'grin'
    look = (1, 0.3)
    if 157.4 < t < 159.3:
        look = (1, -0.2)
    rot = -0.12 + math.sin(t * 18) * 0.04 * giggle
    dima_head(c, 185, 418, 50, eyes=eyes, look=look, mouth=mouth, mo=0.3, brows='n', rot=rot, happy_closed=happy)
    blanket(c, t, math.sin(t * 1.5))
    # малыш Глотун в «кармане» — выглядывает из-под одеяла
    k = rng(t, 154.9, 155.6)
    if k > 0:
        c.save()
        c.rectangle(250, 200, 300, 222 - 8)
        c.clip()
        mouth = rng(t, 158.85, 159.08) * (1 - rng(t, 159.15, 159.4)) * 0.8
        glotun(c, 330, 440 - 34 * k, 30, t, mouth=mouth, lean=0.5 if t < 157.4 else 0.8, perk=1.1,
               items=[('note', NOTE_COLS[0])] if t > 159.1 else [], show_shadow=False,
               squint=0.6 * rng(t, 159.4, 159.8))
        c.restore()
    # лента с маминой фразой
    if 157.5 < t < 159.15:
        x, y, kk = fly(t, 157.5, 159.1, (1180, 380), (335, 395), 80)
        sc = 1 - 0.85 * kk
        glow(c, x, y, 120 * sc + 20, hx('#ffd88a'), 0.5)
        onoma(c, 'И ЧТОБЫ НИ ЗВУКА!', x, y, 34, '#fff1c4', '#3a2a10', -0.1 + kk * 0.3, 1, sc)
    sc, al = pop(t, 159.1, 0.9)
    onoma(c, 'хап', 330, 340, 24, '#ff8fd0', '#2b1240', 0.1, al, sc)
    # будильник снова тикает
    if t > 160.0:
        for i in range(4):
            t0 = 160.2 + i * 1.0
            a = t - t0
            if 0 <= a < 1.4:
                x, y = 700 + a * 25, 408 - a * 50
                al = 1 - lin(a, 0.8, 1.4)
                item(c, 'tick', x, y, 14, t, al)
                onoma(c, 'тик', x + 26, y - 8, 18, '#ffd24a', '#3a2a10', -0.15, al)


def title_scene(c, t):
    sky_rect(c, '#1b1640', '#07081a')
    random.seed(5)
    for i in range(90):
        px, py = random.uniform(0, W), random.uniform(0, H)
        a = 0.4 + 0.6 * abs(math.sin(t * 1.5 + i))
        col(c, '#ffffff', a * 0.7)
        c.arc(px, py, random.uniform(0.8, 2.2), 0, TAU)
        c.fill()
    sc = sm((t - 165.62) / 0.6)
    onoma(c, 'ДИМА И ГЛОТУН', W / 2, 270, 92, '#ffd23f', '#2b1240', 0, sc, 0.6 + 0.4 * sc)
    hop = math.sin(lin(t, 167.85, 168.2) * PI) * 40
    glotun(c, W / 2, 520 - hop, 60, t, items=[('note', NOTE_COLS[1]), ('tick',), ('star',)], lean=0, perk=1.1,
           alpha=0.92 * sc)
    sc2, al = pop(t, 167.88, 1.4)
    onoma(c, 'ик', W / 2 + 90, 400, 32, '#ffd0f0', '#3a1050', 0.2, al, sc2)


SCENES = [
    (0.0, 21.9, scene_bedroom_night),
    (21.9, 58.38, kitchen_scene),
    (58.38, 75.9, hallway_scene),
    (75.9, 151.3, bathroom_scene),
    (151.3, 165.62, bedroom_end),
    (165.62, 999, title_scene),
]
CUTS = [(21.9, 21.9), (57.0, 58.38), (75.9, 75.9), (151.3, 151.3), (163.55, 165.62)]


def fade_amount(t):
    a = 0.0
    for e, s in CUTS:
        if e - 0.35 < t <= e:
            a = max(a, (t - (e - 0.35)) / 0.35)
        if s <= t < s + 0.35:
            a = max(a, 1 - (t - s) / 0.35)
    if t < 0.6:
        a = max(a, 1 - t / 0.6)
    if t > OLD_END - 0.8:
        a = max(a, (t - (OLD_END - 0.8)) / 0.8)
    return cl(a)


def render_frame(surf, t):
    c = cairo.Context(surf)
    c.set_source_rgb(0, 0, 0)
    c.paint()
    for a, b, fn in SCENES:
        if a <= t < b:
            c.save()
            fn(c, t)
            c.restore()
            break
    # виньетка
    g = cairo.RadialGradient(W / 2, H / 2, H * 0.45, W / 2, H / 2, H * 0.95)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.45)
    c.set_source(g)
    c.paint()
    draw_banner(c, t)
    draw_subs(c, t)
    f = fade_amount(t)
    if f > 0:
        c.set_source_rgba(0, 0, 0, f)
        c.paint()


def main():
    mode = sys.argv[1]
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    if mode == 'still':
        for ts in sys.argv[3:]:
            t = float(ts)
            render_frame(surf, t)
            surf.write_to_png(f"{sys.argv[2]}/still_{t:07.2f}.png")
        return
    out = sys.argv[2]
    f0, f1 = int(sys.argv[3]), int(sys.argv[4])
    p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                          '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    for f in range(f0, f1):
        t = to_old(f / FPS)
        render_frame(surf, t)
        surf.flush()
        p.stdin.write(bytes(surf.get_data()))
    p.stdin.close()
    p.wait()


if __name__ == '__main__':
    main()
