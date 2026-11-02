# -*- coding: utf-8 -*-
"""Рендер второй части «Дима и Глотун 2. Звонок». Тайминги — во времени исходной озвучки."""
import cairo, math, sys, random, subprocess
import render as R
from render import (W, H, FPS, PI, TAU, cl, sm, rng, lin, lerp, mix, hx, col, ell, rr, glow, font, onoma,
                    pop, path_poly, gear, drop_icon, bolt_icon, star_icon, burst, note_icon, bubble_icon,
                    glotun, ear, dima, dima_head, camera, shake_at, fly, dev2user, heart, NOTE_COLS)

START = 11.6            # вырезана служебная фраза в начале озвучки
OLD_END = 139.8
TOTAL_NEW = OLD_END - START


def to_old(tn):
    return tn + START


# ---------- новые значки ----------
def feather(c, x, y, s, a=1.0, rot=0.0):
    c.save()
    c.translate(x, y)
    c.rotate(rot - 0.6)
    col(c, '#c8945a', a)
    ell(c, 0, 0, s * 0.35, s)
    c.fill()
    col(c, '#7a5230', a)
    c.set_line_width(max(1, s * 0.08))
    c.move_to(0, s * 1.1)
    c.line_to(0, -s * 0.9)
    c.stroke()
    c.restore()


def horn(c, x, y, s, a=1.0, rot=0.0):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    col(c, '#ffcf3a', a)
    path_poly(c, [(-s, -s * 0.25), (-s * 0.2, -s * 0.25), (s, -s * 0.8), (s, s * 0.8), (-s * 0.2, s * 0.25), (-s, s * 0.25)])
    c.fill()
    col(c, '#c24a2a', a)
    c.arc(-s, 0, s * 0.38, 0, TAU)
    c.fill()
    c.restore()


def bell_icon(c, x, y, s, a=1.0, rot=0.0):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.new_path()
    c.move_to(-s * 0.9, s * 0.6)
    c.curve_to(-s * 0.7, s * 0.3, -s * 0.75, -s * 0.9, 0, -s * 0.95)
    c.curve_to(s * 0.75, -s * 0.9, s * 0.7, s * 0.3, s * 0.9, s * 0.6)
    c.close_path()
    col(c, '#ffc928', a)
    c.fill_preserve()
    col(c, '#9a6a00', a)
    c.set_line_width(max(1, s * 0.08))
    c.stroke()
    col(c, '#9a6a00', a)
    c.arc(0, s * 0.72, s * 0.2, 0, TAU)
    c.fill()
    col(c, '#ffffff', a * 0.6)
    ell(c, -s * 0.35, -s * 0.3, s * 0.1, s * 0.3)
    c.fill()
    c.restore()


KC2 = {'feather': hx('#ffd9a0'), 'honk': hx('#ffe14a'), 'bell': hx('#ffd23f'), 'drum': hx('#ff6f6f'),
       'plane': hx('#ffffff')}
_orig_item = R.item


def item2(c, kind, x, y, s, t, a=1.0, bright=1.0, clr=None):
    if kind not in KC2:
        return _orig_item(c, kind, x, y, s, t, a, bright, clr)
    if a <= 0.01:
        return
    cc = clr or KC2[kind]
    glow(c, x, y, s * 2.2, cc, 0.55 * a * bright)
    if kind == 'feather':
        feather(c, x, y, s * 0.9, a, math.sin(t * 2) * 0.3)
    elif kind == 'honk':
        horn(c, x, y, s * 0.85, a)
    elif kind == 'bell':
        bell_icon(c, x, y, s * 0.9, a, math.sin(t * 8) * 0.2)
    elif kind == 'drum':
        note_icon(c, x, y, s * 0.95, cc, a)


R.item = item2
item = item2


class Palette:
    """временно перекрасить Глотуна (седой) или Диму/детей"""

    def __init__(self, **kw):
        self.kw = kw

    def __enter__(self):
        self.old = {k: getattr(R, k) for k in self.kw}
        for k, v in self.kw.items():
            setattr(R, k, v)

    def __exit__(self, *a):
        for k, v in self.old.items():
            setattr(R, k, v)


GREY = dict(PURP=hx('#a3a3b4'), PURP_L=hx('#e4e4ee'), PURP_D=hx('#5f5f70'))
UNIFORM = dict(PJ=hx('#3b4f7a'), PJD=hx('#2a3858'), ROCKETS=False)


def plane(c, x, y, s, rot, a=1.0):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    path_poly(c, [(s, 0), (-s, -s * 0.5), (-s * 0.6, 0), (-s, s * 0.5)])
    col(c, '#ffffff', a)
    c.fill_preserve()
    col(c, '#8090a8', a)
    c.set_line_width(1.5)
    c.stroke()
    c.restore()


def notebook(c, x, y, s, rot, clr, a=1.0):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    col(c, clr, a)
    rr(c, -s, -s * 0.7, s * 2, s * 1.4, 3)
    c.fill()
    col(c, '#ffffff', a)
    c.rectangle(-s * 0.6, -s * 0.3, s * 1.2, s * 0.5)
    c.fill()
    c.restore()


def thought(c, x, y, w, h, a=1.0):
    col(c, '#ffffff', 0.92 * a)
    rr(c, x - w / 2, y - h / 2, w, h, h * 0.45)
    c.fill()
    c.arc(x - w * 0.3, y + h * 0.65, 10, 0, TAU)
    c.fill()
    c.arc(x - w * 0.38, y + h * 0.9, 6, 0, TAU)
    c.fill()


# ---------- Марья Иванна ----------
T_SKIN = hx('#f2c4a0')
T_HAIR = hx('#7a5a48')


def teacher(c, x, y, s=1.0, mouth='smile', eyes=1.0, look=(0, 0), glasses_off=0.0, spiky=0.0,
            arms='down', t=0.0, pocket_open=0.0, old_glotun=0.0, lean=0.0, brows='n', walk=None):
    out = {}
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.rotate(lean * PI / 180)
    # ноги
    ph = walk if walk is not None else 0
    for sx, sg in ((-18, 1), (18, -1)):
        a = (math.sin(ph) * 18 * sg if walk is not None else 0) * PI / 180
        c.set_line_width(20)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        col(c, '#4a3a44')
        fx, fy = sx + math.sin(a) * 160, -170 + math.cos(a) * 160
        c.move_to(sx, -170)
        c.line_to(fx, fy)
        c.stroke()
        col(c, '#1e1a22')
        ell(c, fx + 8, fy + 4, 22, 9)
        c.fill()
    # юбка
    col(c, '#3d5a4a')
    path_poly(c, [(-50, -270), (50, -270), (78, -150), (-78, -150)])
    c.fill()
    # руки — задняя (правая для зрителя слева)
    sh_y = -392

    def arm(px, tgt, clr):
        ex, ey, hx_, hy_ = R.ik2(px, sh_y, tgt[0], tgt[1], 72, 70, bend=-1 if px > 0 else 1)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.set_line_width(22)
        col(c, clr)
        c.move_to(px, sh_y)
        c.line_to(ex, ey)
        c.line_to(hx_, hy_)
        c.stroke()
        col(c, T_SKIN)
        c.arc(hx_, hy_, 13, 0, TAU)
        c.fill()
        return hx_, hy_

    wob = math.sin(t * 22) * 14
    poses = {
        'down': ((-62, -250), (62, -250)),
        'tishe': ((-95, -470 + wob * 0.5), (95, -470 - wob * 0.5)),
        'wipe': ((-10 + wob, -330), (22 - wob, -330)),
        'hips': ((-82, -282), (82, -282)),
        'point': ((-170, -420), (68, -260)),
        'pocket': ((-62, -250), (58, -352)),
        'shrug': ((-110, -330), (110, -330)),
    }
    tl, tr = poses.get(arms, poses['down'])
    hl = arm(-58, tl, hx('#6e2232'))
    # туловище — пиджак
    col(c, '#8a2f3f')
    rr(c, -62, -410, 124, 150, 26)
    c.fill()
    col(c, '#f4efe6')
    path_poly(c, [(-20, -410), (20, -410), (0, -350)])
    c.fill()
    col(c, '#a8475a')
    path_poly(c, [(-22, -410), (-44, -405), (-8, -330)])
    c.fill()
    path_poly(c, [(22, -410), (44, -405), (8, -330)])
    c.fill()
    for by in (-320, -290):
        col(c, '#e8c060')
        c.arc(0, by, 4, 0, TAU)
        c.fill()
    # карман пиджака (с седым Глотуном)
    px0, py0 = 34, -362
    if old_glotun > 0:
        c.save()
        c.rectangle(-300, -900, 600, 900 + py0 + 2)
        c.clip()
        with Palette(**GREY):
            gy = py0 + 38 - 58 * old_glotun
            m = glotun(c, px0, gy, 30, t, perk=1.9, lean=-0.3 + math.sin(t * 1.5) * 0.2,
                       squint=0.3, items=[('note', hx('#d0d0e0'))], show_shadow=False, wob=0.6)
        c.restore()
        out['old'] = c.user_to_device(px0, gy - 40)
    col(c, '#6e2232')
    rr(c, px0 - 18, py0, 36, 28, 5)
    c.fill()
    c.save()
    c.translate(px0 - 18, py0)
    c.rotate(-1.9 * pocket_open)
    col(c, '#9a3a4c')
    rr(c, 0, -2, 36, 12, 4)
    c.fill()
    c.restore()
    # передняя рука
    hr = arm(58, tr, hx('#8a2f3f'))
    # шея и голова
    col(c, T_SKIN)
    c.rectangle(-12, -432, 24, 26)
    c.fill()
    hy = -470
    # причёска-пучок
    if spiky > 0:
        col(c, T_HAIR)
        for i in range(13):
            a = PI + i * PI / 12 + 0.0
            L = 70 + 40 * spiky * (0.6 + 0.4 * math.sin(i * 2.7))
            path_poly(c, [(math.cos(a - 0.12) * 40, hy - 10 + math.sin(a - 0.12) * 40),
                          (math.cos(a) * (40 + L * spiky), hy - 10 + math.sin(a) * (40 + L * spiky)),
                          (math.cos(a + 0.12) * 40, hy - 10 + math.sin(a + 0.12) * 40)])
            c.fill()
    bun = 1 - spiky
    if bun > 0.05:
        col(c, T_HAIR)
        c.arc(0, hy - 72, 30 * bun, 0, TAU)
        c.fill()
    col(c, T_SKIN)
    ell(c, 0, hy, 46, 52)
    c.fill()
    col(c, T_HAIR)
    c.new_path()
    c.arc(0, hy - 6, 49, PI * 1.02, PI * 1.98)
    c.curve_to(30, hy - 30, -10, hy - 42, -49, hy - 8)
    c.close_path()
    c.fill()
    # серёжки
    col(c, '#e8c060')
    c.arc(-46, hy + 18, 4, 0, TAU)
    c.arc(46, hy + 18, 4, 0, TAU)
    c.fill()
    # глаза
    for sx in (-1, 1):
        ex = sx * 18
        if eyes < 0.2:
            col(c, '#2a1a10')
            c.set_line_width(3.5)
            c.new_path()
            c.arc(ex, hy - 2, 7, PI * 1.1, PI * 1.9)
            c.stroke()
        else:
            col(c, '#ffffff')
            ell(c, ex, hy - 4, 8, 9 * eyes)
            c.fill()
            col(c, '#2a1a10')
            c.arc(ex + look[0] * 3, hy - 4 + look[1] * 3, 4.2, 0, TAU)
            c.fill()
    col(c, T_HAIR)
    c.set_line_width(3.5)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for sx in (-1, 1):
        if brows == 'up':
            c.move_to(sx * 8, hy - 26)
            c.line_to(sx * 28, hy - 24)
        elif brows == 'angry':
            c.move_to(sx * 8, hy - 18)
            c.line_to(sx * 28, hy - 24)
        else:
            c.move_to(sx * 8, hy - 21)
            c.line_to(sx * 28, hy - 21)
        c.stroke()
    # румянец
    col(c, '#ff7a8a', 0.3)
    ell(c, -28, hy + 12, 9, 5)
    c.fill()
    ell(c, 28, hy + 12, 9, 5)
    c.fill()
    # рот
    my = hy + 24
    c.set_line_width(3.5)
    col(c, '#8a2a3a')
    if mouth == 'smile':
        c.new_path()
        c.arc(0, my - 8, 12, PI * 0.2, PI * 0.8)
        c.stroke()
    elif mouth == 'grin':
        c.new_path()
        c.move_to(-14, my - 3)
        c.curve_to(-8, my + 12, 8, my + 12, 14, my - 3)
        c.close_path()
        c.fill()
    elif mouth in ('o', 'shout'):
        r_ = 5 if mouth == 'o' else 9 + 3 * abs(math.sin(t * 12))
        ell(c, 0, my, r_ * 0.8, r_)
        c.fill()
    elif mouth == 'flat':
        c.move_to(-9, my)
        c.line_to(9, my)
        c.stroke()
    # очки
    if glasses_off < 0.5:
        gx, gy = 0, hy - 4
        rot = 0.0 if spiky < 0.5 else 0.15
    else:
        gx, gy = (hl[0] + hr[0]) / 2, (hl[1] + hr[1]) / 2 - 6
        rot = 0.0
    c.save()
    c.translate(gx, gy)
    c.rotate(rot)
    col(c, '#3a2a2a')
    c.set_line_width(3)
    c.arc(-18, 0, 13, 0, TAU)
    c.stroke()
    c.arc(18, 0, 13, 0, TAU)
    c.stroke()
    c.move_to(-5, -1)
    c.line_to(5, -1)
    c.stroke()
    col(c, '#ffffff', 0.25)
    c.arc(-18, 0, 12, 0, TAU)
    c.arc(18, 0, 12, 0, TAU)
    c.fill()
    c.restore()
    # цепочка очков
    col(c, '#d8b050', 0.9)
    c.set_line_width(1.6)
    c.move_to(gx - 31, gy)
    c.curve_to(-50, hy + 60, 50, hy + 60, gx + 31, gy)
    c.stroke()
    out['mouth'] = c.user_to_device(0, my)
    c.restore()
    return out


# ---------- дети ----------
KIDS_BACK = [  # x, hair, shirt, girl, role
    (580, '#2a1a10', '#d9534f', True, 'shout'),
    (670, '#c86a2a', '#5cb85c', False, 'whistle'),
    (940, '#1a1a1a', '#f0ad4e', False, 'shout'),
    (1030, '#e0b050', '#9b59b6', True, 'shout'),
]
KIDS_FRONT = [
    (400, '#5a3a20', '#20a0b0', False, 'shout'),
    (500, '#2a1a10', '#e070a0', True, 'whistle'),
    (815, '#d0602a', '#4caf50', False, 'drum'),   # Петя
]
DIMA_X = 705
FB, FF = 548, 650          # пол заднего и переднего ряда
SB, SF = 0.6, 0.78


def kid(c, x, floor, s, hair, shirt, girl, t, mouth='smile', mo=0.5, eyes=1.0, look=(0, 0), brows='n',
        armF=10, armB=10, tgtF=None, tgtB=None, bob=0.0, sitting=True, legF=4, legB=-4, face=1, happy=False,
        head_rot=0.0):
    y = floor + (40 * s if sitting else 0)
    shirt_c = hx(shirt)
    with Palette(HAIR=hx(hair), PJ=shirt_c, PJD=mix(shirt_c, (0, 0, 0), 0.25), ROCKETS=False):
        if girl:
            hx_, hy_ = x, y - bob - 300 * s
            col(c, hair)
            for sx in (-1, 1):
                ell(c, hx_ + sx * 70 * s, hy_ + 10 * s, 20 * s, 26 * s)
                c.fill()
            col(c, '#ff5a8a')
            for sx in (-1, 1):
                c.arc(hx_ + sx * 58 * s, hy_ - 14 * s, 9 * s, 0, TAU)
                c.fill()
        c.save()
        if sitting:
            c.rectangle(-500, -500, W + 1000, floor - 60 * s + 500)
            c.clip()
        res = dima(c, x, y, s, face, eyes, look, mouth, mo, brows, 0, armB=armB, armF=armF, tgtF=tgtF, tgtB=tgtB,
                   bob=bob, legF=legF, legB=legB, happy_closed=happy, head_rot=head_rot)
        c.restore()
    return res


def desk(c, cx, floor, s, w=230):
    top = floor - 112 * s
    col(c, '#8a5a32')
    c.rectangle(cx - w / 2 * s, top, w * s, 112 * s)
    c.fill()
    col(c, '#b07a48')
    rr(c, cx - (w / 2 + 8) * s, top - 12 * s, (w + 16) * s, 16 * s, 4 * s)
    c.fill()
    col(c, '#6e4626')
    c.rectangle(cx - w / 2 * s + 10 * s, top + 25 * s, w * s - 20 * s, 6 * s)
    c.fill()
    return top - 12 * s


# ---------- фоны ----------
def classroom_bg(c, t, bell_shake=0.0):
    g = cairo.LinearGradient(0, -200, 0, 600)
    g.add_color_stop_rgb(0, *hx('#f6e7c8'))
    g.add_color_stop_rgb(1, *hx('#ead6ae'))
    c.set_source(g)
    c.rectangle(-400, -400, W + 800, 1200)
    c.fill()
    col(c, '#9cc3a8')
    c.rectangle(-400, 400, W + 800, 160)
    c.fill()
    col(c, '#7aa58a')
    c.rectangle(-400, 396, W + 800, 8)
    c.fill()
    # пол
    col(c, '#c89a64')
    c.rectangle(-400, 555, W + 800, 400)
    c.fill()
    col(c, '#b0824e')
    c.set_line_width(2)
    for i in range(-10, 30):
        c.move_to(i * 90, 555)
        c.line_to(i * 90 - 120, 760)
    c.stroke()
    # окно слева
    for wx in (-180, -20):
        col(c, '#ffffff')
        rr(c, wx, 70, 140, 280, 6)
        c.fill()
        g = cairo.LinearGradient(0, 80, 0, 340)
        g.add_color_stop_rgb(0, *hx('#8fd3ff'))
        g.add_color_stop_rgb(1, *hx('#d8f2ff'))
        c.set_source(g)
        c.rectangle(wx + 10, 80, 120, 260)
        c.fill()
        col(c, '#ffffff')
        c.rectangle(wx + 66, 80, 8, 260)
        c.fill()
    # солнечные полосы
    col(c, '#fff6c0', 0.18)
    path_poly(c, [(130, 80), (130, 340), (520, 560), (420, 80)])
    c.fill()
    # доска
    col(c, '#8a5a32')
    rr(c, 290, 80, 560, 250, 8)
    c.fill()
    col(c, '#2f5d46')
    c.rectangle(304, 94, 532, 222)
    c.fill()
    col(c, '#ffffff', 0.85)
    font(c, 34, False)
    c.move_to(330, 140)
    c.show_text('3 «Б»')
    c.move_to(560, 140)
    c.show_text('2 + 2 = 4')
    c.move_to(330, 200)
    c.show_text('Классная работа')
    font(c, 26, False)
    c.move_to(330, 255)
    c.show_text('Тише едешь — дальше будешь')
    col(c, '#b07a48')
    c.rectangle(290, 322, 560, 14)
    c.fill()
    col(c, '#ffffff')
    c.rectangle(360, 316, 30, 7)
    c.fill()
    # плакат
    col(c, '#ffffff')
    rr(c, 880, 110, 150, 190, 6)
    c.fill()
    for i, cc in enumerate(('#ff6f6f', '#6fbfff', '#ffd23f', '#7ddf7d')):
        col(c, cc)
        c.arc(920 + (i % 2) * 70, 160 + (i // 2) * 80, 24, 0, TAU)
        c.fill()
    # часы
    col(c, '#ffffff')
    c.arc(1060, 70, 30, 0, TAU)
    c.fill()
    col(c, '#333333')
    c.set_line_width(3)
    c.arc(1060, 70, 30, 0, TAU)
    c.stroke()
    c.move_to(1060, 70)
    c.line_to(1060, 50)
    c.move_to(1060, 70)
    c.line_to(1075, 76)
    c.stroke()
    # дверь
    col(c, '#9a6a40')
    c.rectangle(1100, 230, 150, 330)
    c.fill()
    col(c, '#b0804e')
    rr(c, 1115, 250, 120, 130, 6)
    c.fill()
    rr(c, 1115, 395, 120, 145, 6)
    c.fill()
    col(c, '#e0c060')
    c.arc(1120, 400, 7, 0, TAU)
    c.fill()
    # звонок над дверью
    bx, by = 1175, 180
    col(c, '#555555')
    c.rectangle(bx - 4, by - 42, 8, 16)
    c.fill()
    c.save()
    c.translate(bx, by)
    c.rotate(math.sin(t * 60) * 0.15 * bell_shake)
    col(c, '#d8d8d8')
    c.arc(0, 0, 34, PI, TAU)
    c.line_to(34, 8)
    c.line_to(-34, 8)
    c.close_path()
    c.fill()
    col(c, '#9a9a9a')
    c.set_line_width(3)
    c.stroke()
    c.restore()
    if bell_shake > 0:
        col(c, '#ffd23f', 0.7 * bell_shake)
        c.set_line_width(4)
        for i in range(3):
            r_ = 48 + i * 16 + (t * 80) % 16
            c.new_path()
            c.arc(bx, by - 4, r_, PI * 1.1, PI * 1.9)
            c.stroke()
    return (bx, by)


def street_bg(c, t):
    g = cairo.LinearGradient(0, -100, 0, 520)
    g.add_color_stop_rgb(0, *hx('#7cc8ff'))
    g.add_color_stop_rgb(1, *hx('#dff4ff'))
    c.set_source(g)
    c.rectangle(-400, -400, W + 800, 1200)
    c.fill()
    glow(c, 1120, 90, 160, hx('#fff2a0'), 0.6)
    col(c, '#fff3a8')
    c.arc(1120, 90, 46, 0, TAU)
    c.fill()
    for i, (cx_, cy_) in enumerate(((200, 90), (620, 60), (900, 140))):
        x_ = (cx_ + t * 12) % 1500 - 100
        col(c, '#ffffff', 0.9)
        for dx, dy, r_ in ((0, 0, 30), (32, -10, 36), (66, 2, 28), (32, 12, 30)):
            c.arc(x_ + dx, cy_ + dy, r_, 0, TAU)
            c.fill()
    # дома
    houses = [(-40, 200, '#f4a259'), (170, 150, '#8cc6a8'), (380, 230, '#e77f7f'), (640, 170, '#a99be0'),
              (850, 210, '#f2cf5b'), (1060, 160, '#7fb3e0')]
    for hxp, hh, cc in houses:
        col(c, cc)
        c.rectangle(hxp, 520 - hh - 120, 190, hh + 120)
        c.fill()
        col(c, mix(hx(cc), (0, 0, 0), 0.3))
        path_poly(c, [(hxp - 12, 520 - hh - 120), (hxp + 95, 520 - hh - 190), (hxp + 202, 520 - hh - 120)])
        c.fill()
        col(c, '#ffffff', 0.85)
        for wy in range(520 - hh - 95, 470, 70):
            for wx in (hxp + 25, hxp + 110):
                c.rectangle(wx, wy, 50, 40)
                c.fill()
    # дерево
    col(c, '#7a5230')
    c.rectangle(600, 300, 26, 230)
    c.fill()
    c.set_line_width(10)
    c.move_to(613, 360)
    c.line_to(700, 300)
    c.stroke()
    col(c, '#5fb85a')
    for dx, dy, r_ in ((0, 0, 80), (-60, 30, 60), (60, 30, 60), (0, -50, 60)):
        c.arc(613 + dx, 250 + dy, r_, 0, TAU)
        c.fill()
    # дорога
    col(c, '#6a6f7a')
    c.rectangle(-400, 520, W + 800, 90)
    c.fill()
    col(c, '#ffffff', 0.8)
    for i in range(-2, 16):
        c.rectangle(i * 120, 562, 60, 6)
        c.fill()
    # тротуар
    col(c, '#c9c4bb')
    c.rectangle(-400, 610, W + 800, 300)
    c.fill()
    col(c, '#b0aa9e')
    c.set_line_width(2)
    for i in range(-4, 20):
        c.move_to(i * 100, 610)
        c.line_to(i * 100 - 40, 760)
    c.stroke()
    col(c, '#9a948a')
    c.rectangle(-400, 606, W + 800, 8)
    c.fill()


def sparrow(c, x, y, t, surprised=False):
    col(c, '#8a6a4a')
    ell(c, x, y, 20, 15)
    c.fill()
    c.arc(x + 14, y - 12, 10, 0, TAU)
    c.fill()
    col(c, '#e8d8c0')
    ell(c, x + 4, y + 4, 12, 8)
    c.fill()
    col(c, '#ffb03a')
    path_poly(c, [(x + 23, y - 13), (x + 32, y - 10), (x + 23, y - 8)])
    c.fill()
    col(c, '#1a1a1a')
    c.arc(x + 17, y - 14, 2.4, 0, TAU)
    c.fill()
    col(c, '#6a4a2a')
    path_poly(c, [(x - 18, y - 2), (x - 34, y - 8), (x - 30, y + 4)])
    c.fill()
    if surprised:
        onoma(c, '?', x + 10, y - 45, 26, '#ffffff', '#3a2a10', 0.1, 1)


def car(c, x, y, t):
    c.save()
    c.translate(x, y)
    col(c, '#e04a4a')
    rr(c, -110, -50, 220, 50, 16)
    c.fill()
    rr(c, -65, -92, 120, 50, 18)
    c.fill()
    col(c, '#bfe6ff')
    rr(c, -55, -84, 48, 36, 8)
    c.fill()
    rr(c, 2, -84, 44, 36, 8)
    c.fill()
    col(c, '#ffe38a')
    ell(c, -108, -30, 8, 10)
    c.fill()
    for wx in (-65, 65):
        col(c, '#222222')
        c.arc(wx, 0, 24, 0, TAU)
        c.fill()
        col(c, '#bbbbbb')
        c.arc(wx, 0, 10, 0, TAU)
        c.fill()
    c.restore()


# ---------- субтитры / плашки ----------
SUBS2 = [
    (11.8, 16.9, "Утро. Дима идёт в школу. А из кармана торчат три фиолетовых ушка."),
    (17.2, 20.1, "Чирик! Хап. Би-би! Хап."),
    (20.4, 23.5, "— Глотун, — шепчет Дима, — сиди тихо!"),
    (23.7, 24.3, "Ик."),
    (24.5, 31.3, "Третий «Б» — самый шумный класс в школе. Кто-то кричит. Кто-то свистит. Летают самолётики."),
    (31.4, 35.2, "А Петя барабанит линейками по парте. Тра-та-та-там!"),
    (35.4, 38.6, "— Тише! — просит Марья Иванна. — Ти-ше!"),
    (38.9, 40.6, "Но её никто не слышит."),
    (40.9, 46.9, "Глотун высовывается из кармана. Ушки дрожат. Столько звуков! Настоящий обед!"),
    (47.5, 53.3, "Хап — и нет крика. Хап — и нет свиста. Хап — и Петин барабан молчит."),
    (53.6, 54.2, "Тишина."),
    (54.2, 58.7, "Марья Иванна снимает очки. Протирает. Снова надевает."),
    (59.0, 60.7, "— Вот это дисциплина!"),
    (61.0, 66.0, "Только Глотун теперь размером с рюкзак. Он прячется под партой и довольно урчит."),
    (66.4, 67.9, "И тут звенит звонок."),
    (68.2, 69.9, "Дзы… Хап!"),
    (69.9, 71.2, "Класс замирает."),
    (71.4, 75.3, "— Звонка не было, — улыбается Марья Иванна. — Продолжаем урок!"),
    (75.7, 79.1, "Дима хватается за голову. Звонок надо вернуть!"),
    (79.3, 82.6, "И он вспоминает: если Глотуна перекормить…"),
    (82.7, 86.8, "— Кричите, — шепчет Дима. — Все вместе! На счёт три!"),
    (87.1, 89.3, "Раз, два, три!"),
    (89.4, 90.6, "— А-А-А-А-А!"),
    (90.8, 94.6, "Глотун глотает. Раздувается. Краснеет…"),
    (95.0, 96.0, "БУУУУРП!"),
    (96.0, 99.7, "Тра-та-та-там! Фьють! Би-би! Чирик!"),
    (99.8, 102.4, "И громче всего — ДЗЫ-Ы-Ы-ЫНЬ!"),
    (102.5, 107.2, "Тетради летят под потолок. А причёска Марьи Иванны встаёт дыбом."),
    (107.4, 110.1, "— Перемена-а-а! — и класс вылетает за дверь."),
    (110.2, 115.6, "В классе остаются только Дима, Марья Иванна и маленький смущённый Глотун."),
    (115.9, 119.7, "— Это… мой друг, — говорит Дима. — Он не нарочно."),
    (120.1, 126.5, "Марья Иванна долго смотрит на Глотуна. А потом улыбается и приоткрывает карман своего пиджака."),
    (126.8, 131.3, "Оттуда выглядывает старенький седой Глотун с очень большими ушами."),
    (131.6, 135.1, "— Только не корми его после шести, — шепчет Марья Иванна."),
    (135.2, 136.8, "Ик. Ик."),
]
BANNERS2 = [(11.8, "Утро"), (24.4, "Шумный класс"), (40.8, "Обед для Глотуна"), (61.0, "Съеденный звонок"),
            (75.6, "План Димы"), (95.0, "Отрыжка"), (107.4, "Перемена"), (120.0, "Сюрприз")]


# ---------- сцена: улица ----------
def street(c, t):
    _dx = lerp(150, 700, lin(t, 11.6, 20.4))
    camera(c, cl(_dx + 120, 560, 760), 440, 1.22)
    street_bg(c, t)
    # воробей на ветке
    sparrow(c, 690, 286, t, surprised=18.2 < t < 20.0)
    # машина
    cx_ = lerp(1550, -350, lin(t, 17.9, 20.4))
    car(c, cx_, 592, t)
    # Дима
    if t < 20.4:
        dx = lerp(150, 700, lin(t, 11.6, 20.4))
        walking = True
    elif t < 23.95:
        dx = 700
        walking = False
    else:
        dx = lerp(700, 760, lin(t, 23.95, 24.3))
        walking = True
    ph = t * 8
    legF = 24 * math.sin(ph) if walking else 4
    legB = -24 * math.sin(ph) if walking else -4
    armF = -22 * math.sin(ph) if walking else 10
    armB = 22 * math.sin(ph) if walking else 10
    bob = abs(math.sin(ph)) * 6 if walking else 0
    look = (1, 0)
    mouth, mo, brows = 'smile', 0.5, 'n'
    tgtF = None
    if 20.4 < t < 23.95:
        look = (0.6, 1)
        mouth, mo = 'o', 0.35
        brows = 'worried' if t < 22.5 else 'n'
        tgtF = (14, -230) if 22.5 < t < 23.4 else None   # палец у губ
        if tgtF:
            mouth = 'pressed'
    # рюкзак
    s = 0.95
    col(c, '#ff8a3a')
    rr(c, dx - 82 * s, 650 - 250 * s - bob, 46 * s, 130 * s, 12)
    c.fill()
    col(c, '#d0662a')
    rr(c, dx - 86 * s, 650 - 190 * s - bob, 30 * s, 50 * s, 8)
    c.fill()
    mouth_store = {}

    def pocket_fn(cc):
        R_ = 16
        gm = 0.0
        for th in (18.12, 19.64):
            gm = max(gm, rng(t, th - 0.3, th) * (1 - rng(t, th + 0.05, th + 0.3)))
        hop = math.sin(lin(t, 23.8, 24.1) * PI) * 10
        cc.save()
        cc.rectangle(-200, -600, 400, 600 - 172)
        cc.clip()
        items = []
        if t > 18.15:
            items.append(('feather',))
        if t > 19.65:
            items.append(('honk',))
        m = glotun(cc, 27, -158 - hop, R_, t, mouth=gm * 0.9, lean=0.5 if t < 20.4 else -0.2, perk=1.2,
                   items=items, show_shadow=False)
        cc.restore()
        mouth_store['m'] = cc.user_to_device(27, -170)

    with Palette(**UNIFORM):
        mdev, hdev = dima(c, dx, 650, s, 1, 1.0, look, mouth, mo, brows, 0, armB=armB, armF=armF, tgtF=tgtF,
                          legB=legB, legF=legF, bob=bob, pocket=pocket_fn)
    pm = dev2user(c, mouth_store['m'])
    # чирик
    sc, al = pop(t, 17.36, 1.0)
    onoma(c, 'ЧИРИК!', 720, 230, 34, '#ffd9a0', '#5a3a10', -0.1, al, sc)
    if 17.4 < t < 18.12:
        x, y, k = fly(t, 17.4, 18.12, (705, 270), pm, 40)
        item(c, 'feather', x, y, 16 - 6 * k, t)
    sc, al = pop(t, 18.12, 0.8)
    onoma(c, 'хап', pm[0] + 20, pm[1] - 50, 24, '#ff8fd0', '#2b1240', 0.1, al, sc)
    # би-би
    sc, al = pop(t, 18.82, 0.9)
    onoma(c, 'БИ-БИ!', cx_ - 40, 470, 40, '#ffe14a', '#5a3a00', 0.1, al, sc)
    if 18.9 < t < 19.64:
        x, y, k = fly(t, 18.9, 19.64, (cx_ - 100, 540), pm, 60)
        item(c, 'honk', x, y, 20 - 8 * k, t)
    sc, al = pop(t, 19.64, 0.8)
    onoma(c, 'хап', pm[0] + 20, pm[1] - 50, 24, '#ff8fd0', '#2b1240', -0.1, al, sc)
    # шёпот
    if 22.5 < t < 23.7:
        sc, al = pop(t, 22.5, 1.2)
        onoma(c, 'ш-ш-ш…', dx + 80, 650 - 330, 24, '#ffffff', '#2b3270', -0.1, al * 0.9, sc)
    sc, al = pop(t, 23.8, 0.6)
    onoma(c, 'ик', pm[0] + 26, pm[1] - 40, 22, '#ffd0f0', '#3a1050', 0.2, al, sc)


# ---------- сцена: класс ----------
CAM_KEYS = [
    (24.3, 650, 410, 1.1),
    (40.7, 735, 470, 1.7),
    (47.2, 640, 420, 1.12),
    (53.9, 280, 330, 1.55),
    (60.9, 760, 470, 1.45),
    (66.3, 700, 400, 1.05),
    (71.3, 300, 350, 1.4),
    (75.6, 720, 430, 1.6),
    (82.6, 650, 410, 1.1),
    (110.3, 660, 380, 1.15),
    (119.9, 650, 370, 1.3),
    (131.5, 650, 370, 1.3),
]


def cam_at(t):
    cx, cy, z = CAM_KEYS[0][1:]
    for tk, kx, ky, kz in CAM_KEYS[1:]:
        if t >= tk:
            k = sm((t - tk) / 0.9)
            cx, cy, z = lerp(cx, kx, k), lerp(cy, ky, k), lerp(z, kz, k)
    return cx, cy, z


def glotun_state(t):
    """размер и положение Глотуна в классе"""
    st = {}
    if t < 60.8:
        st['where'] = 'pocket'
        Rl = 16
        for th, v in ((47.62, 22), (49.26, 28), (51.02, 34)):
            if t > th:
                Rl = lerp(Rl, v, sm((t - th) / 0.3))
        st['R'] = Rl
    elif t < 61.6:
        st['where'] = 'jump'
    elif t < 89.6:
        st['where'] = 'desk'
        st['R'] = 58
        st['x'] = 845
    elif t < 102.2:
        st['where'] = 'aisle'
        st['x'] = lerp(845, 985, rng(t, 89.6, 90.4))
        Rg = 58
        Rg = lerp(Rg, 150, rng(t, 90.8, 94.2))
        if t > 101.7:
            Rg = lerp(Rg, 16, rng(t, 101.9, 102.2))
        st['R'] = Rg
    else:
        st['where'] = 'aisle'
        st['x'] = 985
        st['R'] = lerp(150, 16, rng(t, 101.9, 106.0)) if t < 106 else 16
        if t > 110.0:
            st['where'] = 'ondesk'
    return st


def classroom(c, t):
    cx, cy, z = cam_at(t)
    sh = (0, 0)
    for a, d, amp in ((95.1, 2.0, 12), (101.64, 1.8, 16), (89.5, 1.2, 5)):
        s_ = shake_at(t, a, d, amp)
        sh = (sh[0] + s_[0], sh[1] + s_[1])
    camera(c, cx, cy, z, sh)
    bell_shake = rng(t, 66.6, 66.9) * (1 - rng(t, 68.6, 69.0))
    bell = classroom_bg(c, t, bell_shake)

    noisy = t < 53.7
    shout_on = t < 47.62
    whistle_on = t < 49.26
    drum_on = t < 51.02
    frozen = 53.7 < t < 66.6
    scream_all = 89.4 < t < 90.7
    run = t > 107.5
    hopeful = 66.6 < t < 69.9
    sad = 71.5 < t < 82.6
    gst = glotun_state(t)

    def kid_pose(i, role, floor, s, x):
        p = dict(mouth='smile', mo=0.5, eyes=1.0, look=(0, 0), brows='n', armF=10, armB=10, tgtF=None, tgtB=None,
                 bob=0.0, happy=False, head_rot=0.0)
        if noisy:
            ph = t * 9 + i * 1.7
            if role == 'shout':
                p.update(mouth='scream', mo=0.5 + 0.5 * abs(math.sin(ph)), bob=abs(math.sin(ph)) * 6,
                         armF=120 + 30 * math.sin(ph), armB=120 - 30 * math.sin(ph), brows='up')
            elif role == 'whistle':
                p.update(mouth='o', mo=0.3, head_rot=math.sin(ph) * 0.1, armF=150, tgtF=None)
            elif role == 'drum':
                a_ = math.sin(t * 18)
                p.update(mouth='grin', tgtF=(60, -140 - 40 * max(0, a_)), tgtB=(-60, -140 - 40 * max(0, -a_)),
                         happy=True, bob=abs(a_) * 4)
            if t > 47.6 and role == 'shout':
                p.update(brows='worried')
            if t > 49.3 and role == 'whistle':
                p.update(brows='worried')
            if t > 51.0 and role == 'drum':
                p.update(happy=False, mouth='o', brows='up')
        if frozen:
            p.update(mouth='o', mo=0.35, brows='up', look=(-0.8, 0) if 53.9 < t < 61 else (0, 0))
        if hopeful:
            p.update(mouth='grin', look=(1, -0.6), brows='up')
        if 69.9 < t < 71.5:
            p.update(mouth='o', mo=0.4, look=(1, -0.6), brows='up')
        if sad:
            p.update(mouth='frown', brows='worried', look=(-0.6, 0))
        if 82.7 < t < 89.4:
            p.update(mouth='o', mo=0.3, look=(1 if x < DIMA_X else -1, 0.2), brows='up')
        if scream_all:
            p.update(mouth='scream', mo=1.0, armF=140, armB=140, brows='up', bob=abs(math.sin(t * 20)) * 5)
        if 90.7 < t < 95.0:
            p.update(mouth='o', mo=0.6, look=(1, -0.3), brows='up')
        if 95.0 < t < 107.4:
            p.update(mouth='o', mo=0.8, eyes=1.15, brows='up', look=(1, -0.5))
        return p

    def draw_kids(lst, floor, s, row):
        for i, (x, hair, shirt, girl, role) in enumerate(lst):
            if run:
                continue
            p = kid_pose(i + row * 10, role, floor, s, x)
            kid(c, x, floor, s, hair, shirt, girl, t, **p)
            # линейки у Пети
            if role == 'drum' and t < 53.7:
                pass

    # задний ряд
    draw_kids(KIDS_BACK, FB, SB, 0)
    desk(c, 625, FB, SB, 250)
    desk(c, 985, FB, SB, 250)
    # учительница
    tx = 220
    walk = None
    if t > 110.4:
        tx = lerp(220, 575, rng(t, 110.4, 113.0))
        if t < 113.0:
            walk = t * 7
    tp = dict(mouth='flat', eyes=1.0, look=(1, 0), glasses_off=0.0, spiky=0.0, arms='down', brows='n')
    if t < 35.4:
        tp.update(mouth='flat', arms='hips', brows='angry')
    if 35.4 < t < 38.7:
        tp.update(mouth='shout', arms='tishe', brows='angry')
    if 38.7 < t < 53.7:
        tp.update(mouth='flat', arms='hips', brows='angry', eyes=0.7)
    if 53.7 < t < 59.0:
        tp.update(mouth='o', brows='up', look=(1, 0))
        if 54.9 < t < 58.6:
            tp.update(glasses_off=1.0, arms='wipe', eyes=0.15 if t < 57.7 else 1.0)
    if 59.0 < t < 66.4:
        tp.update(mouth='grin', arms='shrug' if t < 61 else 'down', eyes=0.1 if t < 60.5 else 1.0, brows='n')
    if 66.4 < t < 71.3:
        tp.update(mouth='smile', look=(1, -0.5))
    if 71.3 < t < 82.6:
        tp.update(mouth='grin' if t < 74.3 else 'smile', arms='point' if t > 74.3 else 'down', look=(1, 0))
    if 82.6 < t < 95.0:
        tp.update(mouth='o', look=(1, 0), brows='up' if t > 89.4 else 'n')
    if t > 95.0:
        tp.update(mouth='o', brows='up', eyes=1.2, look=(1, -0.4), arms='shrug' if t < 107 else 'down')
    if t > 104.3:
        tp['spiky'] = rng(t, 104.3, 104.7)
    if t > 110.2:
        tp.update(mouth='flat', eyes=1.0, brows='n', arms='down', look=(1, 0.3))
    if t > 120.0:
        tp.update(look=(1, 0.6), mouth='flat', arms='down')
    if t > 123.3:
        tp.update(mouth='smile')
    if t > 124.3:
        tp.update(arms='pocket')
    if t > 128.5:
        tp.update(arms='down', mouth='grin')
    if t > 131.6:
        tp.update(mouth='o' if int(t * 6) % 2 else 'smile', look=(1, 0.4))
    pocket_open = rng(t, 124.4, 125.4)
    old_g = rng(t, 126.7, 127.6)
    tout = teacher(c, tx, 600, 0.98, t=t, walk=walk, pocket_open=pocket_open, old_glotun=old_g, **tp)
    tm = dev2user(c, tout['mouth'])
    # «тише» тонет в шуме
    for t0 in (35.5, 37.84):
        sc, al = pop(t, t0, 1.0)
        onoma(c, 'тише…', tm[0] + 70, tm[1] - 40 - 20 * (t - t0), 22 * (1.2 - 0.6 * lin(t, t0, t0 + 1)), '#9a9aaa',
              '#ffffff', 0.1, al * 0.9, sc)
    # передний ряд
    draw_kids(KIDS_FRONT[:2], FF, SF, 1)
    # Глотун за партой
    gpos = {}

    def draw_g_world(x, floor, Rg, mouth=0.0, red=0.0, items=(), squint=0.0, wob=1.0):
        gpos['m'] = glotun(c, x, floor, Rg, t, mouth=mouth, red=red, items=items, squint=squint, wob=wob,
                           lean=-0.4, perk=1.1, item_speed=1 + 5 * red)

    g_items = [('feather',), ('honk',)]
    if t > 47.62:
        g_items.append(('bolt',))
    if t > 49.26:
        g_items.append(('note', NOTE_COLS[1]))
    if t > 51.02:
        g_items.append(('drum',))
    if t > 69.18:
        g_items.append(('bell',))
    if t > 90.0:
        g_items += [('bolt',), ('bolt',), ('bolt',)]
    if t > 95.1:
        g_items = []
    g_mouth = 0.0
    for th, mx in ((69.18, 0.8), (90.2, 0.9)):
        g_mouth = max(g_mouth, mx * rng(t, th - 0.4, th) * (1 - rng(t, th + 0.1, th + 0.4)))
    if gst['where'] == 'desk':
        draw_g_world(gst['x'], FF, gst['R'], mouth=g_mouth, items=g_items, squint=0.6 if 62 < t < 66.5 else 0)
    # Дима
    d = dict(mouth='smile', mo=0.5, eyes=1.0, look=(0.5, 0), brows='n', armF=10, armB=10, tgtF=None, tgtB=None)
    if t < 40.7:
        d.update(mouth='flat', brows='worried', look=(-1, 0), tgtF=(55, -150), tgtB=(-55, -150))
    elif t < 47.5:
        d.update(mouth='o', mo=0.4, look=(0.4, 1), brows='up')
    elif t < 53.7:
        d.update(mouth='o', mo=0.5, brows='up', look=(-1, 0))
    elif t < 66.4:
        d.update(mouth='smile', look=(-1, 0))
    elif t < 70.0:
        d.update(mouth='grin', look=(1, -0.6), brows='up')
    elif t < 75.6:
        d.update(mouth='o', mo=0.6, look=(1, 0.6), brows='up')
    elif t < 82.6:
        d.update(mouth='worried', brows='worried', tgtF=(66, -330), tgtB=(-66, -330), look=(0, -1))
    elif t < 89.4:
        d.update(mouth='o' if int(t * 5) % 2 else 'pressed', mo=0.4, look=(-1, -0.3), brows='up',
                 tgtF=(70, -300) if t < 86.8 else None, armF=150 if t > 86.8 else 10)
    elif t < 90.7:
        d.update(mouth='scream', mo=1.0, armF=150, armB=150, brows='up')
    elif t < 95.0:
        d.update(mouth='o', mo=0.6, look=(1, -0.3), brows='up')
    elif t < 110.2:
        d.update(mouth='o', mo=0.8, eyes=0.15 if t < 96.5 else 1.1, look=(1, -0.5), brows='up')
    else:
        d.update(mouth='smile', look=(-1, -0.4))
        if 115.9 < t < 119.7:
            d.update(mouth='o' if int(t * 6) % 2 else 'smile', mo=0.35, brows='worried', tgtF=(72, -200))
        if t > 126.8:
            d.update(mouth='o', mo=0.6, brows='up', eyes=1.15)
        if t > 131.6:
            d.update(mouth='grin', brows='n', eyes=1.0, happy=True)
    pocket_store = {}

    def pocket_fn(cc):
        if gst['where'] != 'pocket':
            return
        Rl = gst['R']
        pm_ = 0.0
        for th in (47.62, 49.26, 51.02):
            pm_ = max(pm_, rng(t, th - 0.3, th) * (1 - rng(t, th + 0.05, th + 0.3)))
        rise = 0.0 if t < 40.9 else rng(t, 40.9, 41.6)
        cc.save()
        cc.rectangle(-200, -600, 400, 600 - 172)
        cc.clip()
        items = [('feather',), ('honk',)]
        if t > 47.62:
            items.append(('bolt',))
        if t > 49.26:
            items.append(('note', NOTE_COLS[1]))
        if t > 51.02:
            items.append(('drum',))
        perk = 1.0 + 0.6 * rng(t, 43.2, 43.6) * (1 - rng(t, 46.8, 47.4))
        wob = 1 + 1.5 * rng(t, 43.2, 43.6) * (1 - rng(t, 44.4, 45))
        m = glotun(cc, 27, -158 - (Rl * 0.3 + 6) * rise + 6, Rl, t, mouth=pm_ * 0.9, lean=-0.4, perk=perk,
                   items=items, show_shadow=False, wob=wob, squint=0.5 if 53.7 < t < 60 else 0)
        cc.restore()
        pocket_store['m'] = cc.user_to_device(*m)

    with Palette(**UNIFORM):
        kid_res = None
        c.save()
        c.rectangle(-500, -500, W + 1000, FF - 60 * SF + 500)
        c.clip()
        happy = d.pop('happy', False)
        mdev, hdev = dima(c, DIMA_X, FF + 40 * SF, SF, 1, d['eyes'], d['look'], d['mouth'], d['mo'], d['brows'], 0,
                          armB=d['armB'], armF=d['armF'], tgtF=d['tgtF'], tgtB=d['tgtB'], pocket=pocket_fn,
                          happy_closed=happy)
        c.restore()
    dmouth = dev2user(c, mdev)
    pm = dev2user(c, pocket_store['m']) if 'm' in pocket_store else None
    # Петя
    draw_kids(KIDS_FRONT[2:], FF, SF, 2)
    # линейки Пети
    if not run:
        petx = KIDS_FRONT[2][0]
        if t < 53.7:
            a_ = math.sin(t * 18)
            for sgn, k in ((1, max(0, a_)), (-1, max(0, -a_))):
                hx0 = petx + sgn * 60 * SF
                hy0 = FF + 40 * SF - (140 + 40 * k) * SF
                col(c, '#e8c060')
                c.set_line_width(5)
                c.move_to(hx0, hy0)
                c.line_to(hx0 + sgn * 10, hy0 + 40 * SF)
                c.stroke()
    top_front = desk(c, DIMA_X + 55, FF, SF, 290)
    desk(c, 450, FF, SF, 250)
    # прыжок из кармана под парту
    if gst['where'] == 'jump':
        x, y, k = fly(t, 60.8, 61.6, (DIMA_X + 22, FF - 150), (845, FF), 90)
        glotun(c, x, y, lerp(28, 58, k), t, items=g_items, lean=-0.3)
    # Глотун в проходе / на парте
    if gst['where'] == 'aisle':
        red = rng(t, 91.4, 94.0) * (1 - rng(t, 95.2, 96.4))
        mouth = g_mouth
        if t > 94.95:
            mouth = rng(t, 94.95, 95.15) * (1 - 0.5 * rng(t, 96, 97)) * (1 - rng(t, 101.0, 101.6))
            mouth = max(mouth, 0.9 * rng(t, 101.3, 101.6) * (1 - rng(t, 101.9, 102.3)))
        draw_g_world(gst['x'], FF + 6, gst['R'], mouth=mouth, red=red, items=g_items,
                     wob=1 + 2 * red, squint=0.5 if t > 106 else 0)
    if gst['where'] == 'ondesk':
        hop = 0.0
        for th in (135.28,):
            hop = max(hop, math.sin(lin(t, th, th + 0.3) * PI) * 16)
        gx_ = lerp(985, DIMA_X + 120, rng(t, 110.0, 111.2))
        gy_ = lerp(FF + 6, top_front, rng(t, 110.0, 111.2)) - math.sin(lin(t, 110.0, 111.2) * PI) * 80 - hop
        gpos['m'] = glotun(c, gx_, gy_, 20, t, lean=-0.6, perk=1.1, squint=0.4 if t < 126.7 else 0.0,
                           items=[('note', NOTE_COLS[2])])
        if 110.5 < t < 115.6:
            heart(c, gx_ + 18, gy_ - 50, 8, 0.0)
    # ---- эффекты ----
    # шум класса
    if noisy and t < 53.7:
        for i in range(14):
            src = i % 3
            if src == 0 and not shout_on:
                continue
            if src == 1 and not whistle_on:
                continue
            if src == 2 and not drum_on:
                continue
            ph = (t * 0.7 + i * 0.137) % 1
            if src == 0:
                xs = [580, 940, 1030, 400][i % 4]
                ys = FB - 230 if i % 4 != 3 else FF - 230
                item(c, 'bolt', xs + ph * 40 * (1 if i % 2 else -1), ys - ph * 120, 14, t, 1 - ph)
            elif src == 1:
                xs = [670, 500][i % 2]
                ys = FB - 200 if i % 2 == 0 else FF - 240
                item(c, 'note', xs + ph * 50, ys - ph * 120, 14, t, 1 - ph, 1, NOTE_COLS[i % 6])
            else:
                item(c, 'drum', 815 + ph * 60, FF - 200 - ph * 120, 14, t, 1 - ph)
        # самолётики
        for i in range(3):
            ph = t * (0.35 + i * 0.08) + i * 0.4
            px = 640 + math.cos(ph * 2) * (380 - i * 60)
            py = 230 + math.sin(ph * 3) * 60 + i * 40
            plane(c, px, py, 18, math.atan2(math.cos(ph * 3) * 180, -math.sin(ph * 2) * 760), 1.0)
        for t0, s_, x_, y_ in ((25.9, 'А-А-А!', 430, 200), (28.0, 'Э-ЭЙ!', 850, 230), (29.1, 'ФЬЮ-ФЬЮ!', 560, 260),
                               (34.08, 'ТРА-ТА-ТА-ТАМ!', 900, 330), (31.0, 'ХА-ХА!', 760, 210),
                               (39.0, 'А-А-А!', 470, 300), (44.5, 'ФЬЮ!', 520, 250), (45.4, 'БАМ-БАМ!', 880, 340)):
            sc, al = pop(t, t0, 1.3)
            onoma(c, s_, x_, y_, 30, '#ffffff', '#2b1240', math.sin(t0) * 0.2, al, sc)
    # звуки летят в карман
    if pm is not None:
        for t0, th, kind, src in ((47.0, 47.62, 'bolt', (580, FB - 260)), (48.7, 49.26, 'note', (670, FB - 230)),
                                  (50.4, 51.02, 'drum', (870, FF - 230))):
            if t0 < t < th:
                x, y, k = fly(t, t0, th, src, pm, 60)
                item(c, kind, x, y, 20 - 8 * k, t, 1, 1, NOTE_COLS[1] if kind == 'note' else None)
            sc, al = pop(t, th, 0.7)
            onoma(c, 'ХАП!', pm[0] + 10, pm[1] - 50, 30, '#ff8fd0', '#2b1240', 0.1, al, sc)
    # тишина: значок и блёстки дисциплины
    if 59.1 < t < 61.0:
        for i in range(6):
            a_ = t * 2 + i * TAU / 6
            star_icon(c, tm[0] + math.cos(a_) * 90, tm[1] - 30 + math.sin(a_) * 40, 9, t, hx('#ffe07a'),
                      1 - lin(t, 60.4, 61.0))
    if 62.0 < t < 66.4 and 'm' in gpos:
        onoma(c, 'мрр…', 900, FF - 150, 22, '#c9a2ff', '#2b1240', -0.1, 0.8 * rng(t, 62.5, 63.0) * (1 - rng(t, 65.8, 66.3)))
    # звонок
    sc, al = pop(t, 66.74, 1.6)
    onoma(c, 'ДЗЫ…', bell[0] - 70, bell[1] - 40, 34, '#ffd23f', '#5a3a00', -0.1, al, sc)
    if 68.3 < t < 69.18 and 'm' in gpos:
        x, y, k = fly(t, 68.3, 69.18, (bell[0], bell[1] + 30), gpos['m'], 90)
        item(c, 'bell', x, y, 26 - 10 * k, t)
    sc, al = pop(t, 69.18, 0.9)
    if 'm' in gpos:
        onoma(c, 'ХАП!', gpos['m'][0], gpos['m'][1] - 120, 40, '#ff8fd0', '#2b1240', 0.1, al, sc)
    # мысли Димы
    if 77.5 < t < 82.6:
        k = rng(t, 77.5, 77.9) * (1 - rng(t, 82.2, 82.6))
        bx_, by_ = dmouth[0] + 110, dmouth[1] - 150
        thought(c, bx_, by_, 140, 90, k)
        if t < 79.3:
            bell_icon(c, bx_, by_, 26, k)
            onoma(c, '?', bx_ + 45, by_ - 20, 26, '#ff6f6f', '#ffffff', 0, k)
        else:
            glotun(c, bx_ - 10, by_ + 30, 26, t, red=1.0, mouth=0.8, show_shadow=False)
            onoma(c, 'БУРП', bx_ + 30, by_ - 22, 18, '#9dff7a', '#1a3a10', 0.1, k)
    if 82.7 < t < 84.3:
        sc, al = pop(t, 82.76, 1.5)
        onoma(c, 'Кричите!', dmouth[0] - 90, dmouth[1] - 120, 24, '#ffffff', '#2b3270', -0.1, al * 0.9, sc)
    for t0, s_ in ((87.2, 'РАЗ'), (87.9, 'ДВА'), (88.56, 'ТРИ!')):
        sc, al = pop(t, t0, 0.7)
        onoma(c, s_, 640, 230, 80, '#ffd23f', '#2b1240', 0, al, sc)
    if scream_all:
        sc, al = pop(t, 89.45, 1.3)
        onoma(c, 'А-А-А-А-А!', 640, 200, 84, '#fff04a', '#5a2a00', -0.05, al, sc)
    if 89.6 < t < 90.25 and 'm' in gpos:
        for i, src in enumerate(((580, FB - 260), (940, FB - 260), (1030, FB - 260), (400, FF - 260), (500, FF - 260),
                                 (815, FF - 260), (DIMA_X, FF - 260))):
            x, y, k = fly(t, 89.6 + i * 0.05, 90.2, src, gpos['m'], 50)
            bolt_icon(c, x, y, 20 - 8 * k, 0.4, R.KCOL['bolt'])
    # БУРП
    sc, al = pop(t, 95.1, 1.6)
    onoma(c, 'БУУУУРП!', 640, 150, 92, '#9dff7a', '#1a3a10', -0.06, al, sc)
    outs = [(95.2, 'bolt', 'А-А-А!', -2.4), (96.14, 'drum', 'ТРА-ТА-ТА-ТАМ!', -1.9), (97.4, 'note', 'ФЬЮТЬ!', -2.8),
            (98.12, 'honk', 'БИ-БИ!', -1.2), (98.94, 'feather', 'ЧИРИК!', -0.6)]
    if 95.1 < t < 107.5 and 'm' in gpos:
        mc = gpos['m']
        for j, (t0, kind, label, ang) in enumerate(outs):
            if t < t0:
                continue
            a = t - t0
            dd = 520 * (1 - math.exp(-a * 2.2))
            px = mc[0] + math.cos(ang) * dd * 1.3
            py = mc[1] + math.sin(ang) * dd * 0.6
            fade = 1 - lin(t, 103.0, 104.5)
            item(c, kind, px, py, 30, t + j, fade, 1.2, NOTE_COLS[j] if kind == 'note' else None)
            lsc, lal = pop(t, t0, 1.6)
            onoma(c, label, px, py - 55, 32, '#ffffff', '#2b1240', math.sin(j) * 0.2, lal * fade, lsc)
    # ДЗЫНЬ
    if 101.6 < t < 104.5:
        k = lin(t, 101.64, 104.5)
        bx_, by_ = 640, 330
        for i in range(5):
            r_ = ((t - 101.64) * 500 + i * 120) % 900
            col(c, '#ffd23f', 0.6 * (1 - r_ / 900) * (1 - k))
            c.set_line_width(10)
            c.arc(bx_, by_, r_, 0, TAU)
            c.stroke()
        bell_icon(c, bx_, by_, 70 * min(1, (t - 101.64) / 0.15), 1 - lin(t, 103.6, 104.5), math.sin(t * 30) * 0.25)
    sc, al = pop(t, 101.64, 2.2)
    onoma(c, 'ДЗЫ-Ы-Ы-ЫНЬ!', 640, 170, 88, '#ffd23f', '#5a2a00', 0.04, al, sc)
    # тетради
    if 102.4 < t < 112:
        random.seed(21)
        for i in range(12):
            x0 = random.uniform(380, 980)
            y0 = random.choice((FB - 70, FF - 90))
            clr = random.choice(('#ff6f6f', '#6fbfff', '#7ddf7d', '#ffd23f', '#c9a2ff'))
            k = rng(t, 102.5 + i * 0.05, 103.8 + i * 0.05)
            fall = max(0, t - 105.5) * 60
            x = x0 + math.sin(t * 2 + i) * 30
            y = lerp(y0, 40 + (i % 4) * 20, k) + fall
            if y < 720:
                notebook(c, x, y, 18, t * (2 + i % 3) + i, clr, 1 - lin(t, 110, 112))
    # перемена: дети убегают
    if run and t < 110.6:
        sc, al = pop(t, 107.6, 2.0)
        onoma(c, 'ПЕРЕМЕНА-А-А!', 640, 190, 70, '#7ddf7d', '#1a3a10', -0.05, al, sc)
        k = lin(t, 107.6, 110.0)
        allk = [(x, FB, SB, h, sh_, g) for (x, h, sh_, g, r) in KIDS_BACK] + \
               [(x, FF, SF, h, sh_, g) for (x, h, sh_, g, r) in KIDS_FRONT]
        for i, (x, fl, s, h, sh_, g) in enumerate(allk):
            kk = cl(k * 1.3 - i * 0.05)
            xx = lerp(x, 1330, kk)
            ph = t * 14 + i
            if xx < 1320:
                kid(c, xx, fl, s, h, sh_, g, t, mouth='grin', sitting=False, legF=40 * math.sin(ph),
                    legB=-40 * math.sin(ph), armF=-50 * math.sin(ph), armB=50 * math.sin(ph),
                    bob=abs(math.sin(ph)) * 10, happy=True)
    # финал: ик-ик
    if 'm' in gpos and gst['where'] == 'ondesk':
        sc, al = pop(t, 135.28, 1.0)
        onoma(c, 'ик', gpos['m'][0] + 30, gpos['m'][1] - 70, 24, '#ffd0f0', '#3a1050', 0.2, al, sc)
    if 'old' in tout:
        op = dev2user(c, tout['old'])
        sc, al = pop(t, 136.1, 1.0)
        onoma(c, 'ик', op[0] + 40, op[1] - 30, 22, '#e4e4ee', '#3a3a4a', -0.2, al, sc)
    if 131.6 < t < 135.2:
        sc, al = pop(t, 131.65, 3.5)
        col(c, '#ffffff', 0.9 * al)
        rr(c, tm[0] - 300, tm[1] - 50, 250, 70, 20)
        c.fill()
        font(c, 20, True)
        col(c, '#5a2a3a', al)
        c.move_to(tm[0] - 286, tm[1] - 20)
        c.show_text('Только не корми')
        c.move_to(tm[0] - 286, tm[1] + 4)
        c.show_text('его после шести…')


def title2(c, t):
    R.sky_rect(c, '#1b1640', '#07081a')
    random.seed(5)
    for i in range(90):
        px, py = random.uniform(0, W), random.uniform(0, H)
        a = 0.4 + 0.6 * abs(math.sin(t * 1.5 + i))
        col(c, '#ffffff', a * 0.7)
        c.arc(px, py, random.uniform(0.8, 2.2), 0, TAU)
        c.fill()
    k = sm((t - 136.8) / 0.6)
    onoma(c, 'ДИМА И ГЛОТУН 2', W / 2, 220, 84, '#ffd23f', '#2b1240', 0, k, 0.6 + 0.4 * k)
    onoma(c, 'Звонок', W / 2, 310, 50, '#c9a2ff', '#2b1240', 0, k, 0.6 + 0.4 * k)
    glotun(c, W / 2 - 90, 540, 55, t, items=[('bell',), ('note', NOTE_COLS[0])], lean=0.4, alpha=0.92 * k)
    with Palette(**GREY):
        glotun(c, W / 2 + 90, 540, 55, t, items=[('note', hx('#d0d0e0'))], lean=-0.4, perk=1.9, alpha=0.92 * k)


def fade2(t):
    a = 0.0
    for e in (24.3, 136.8):
        if e - 0.35 < t <= e:
            a = max(a, (t - (e - 0.35)) / 0.35)
        if e <= t < e + 0.35:
            a = max(a, 1 - (t - e) / 0.35)
    if t < START + 0.6:
        a = max(a, 1 - (t - START) / 0.6)
    if t > OLD_END - 0.8:
        a = max(a, (t - (OLD_END - 0.8)) / 0.8)
    return cl(a)


R.SUBS = SUBS2
R.BANNERS = BANNERS2


def render_frame(surf, t):
    c = cairo.Context(surf)
    c.set_source_rgb(0, 0, 0)
    c.paint()
    c.save()
    if t < 24.3:
        street(c, t)
    elif t < 136.8:
        classroom(c, t)
    else:
        title2(c, t)
    c.restore()
    g = cairo.RadialGradient(W / 2, H / 2, H * 0.5, W / 2, H / 2, H * 1.0)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.35)
    c.set_source(g)
    c.paint()
    R.draw_banner(c, t)
    R.draw_subs(c, t)
    f = fade2(t)
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
            surf.write_to_png(f"{sys.argv[2]}/s2_{t:07.2f}.png")
        return
    out = sys.argv[2]
    f0, f1 = int(sys.argv[3]), int(sys.argv[4])
    p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                          '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    for f in range(f0, f1):
        render_frame(surf, to_old(f / FPS))
        surf.flush()
        p.stdin.write(bytes(surf.get_data()))
    p.stdin.close()
    p.wait()


if __name__ == '__main__':
    main()
