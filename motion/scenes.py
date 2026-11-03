"""场景模板库：每个场景 = 一屏（1080×1920），只填文案，坐标/节奏/配色全自动。

每个场景函数签名：scene(d, y, t, th) -> (svg 片段列表, 时长秒)
  d  分镜里这一屏的字段   y  这一屏顶部坐标   t  这一屏开始的秒数   th  主题色
只用微信实测保留的动画属性：opacity / transform / stroke-dashoffset / width。
"""
import math
import random
import re
from html import escape

W, SCREEN = 1080, 1920
CN = "'PingFang SC', 'Noto Sans SC', 'Microsoft YaHei', sans-serif"
MONO = "Menlo, 'JetBrains Mono', Consolas, monospace"
EASE = 'calcMode="spline" keyTimes="0;1" keySplines="0.42 0 0.58 1"'
POP = 'calcMode="spline" keyTimes="0;0.7;1" keySplines="0.3 0 0.4 1;0.5 0 0.5 1"'


def n(v):
    return f"{v:g}" if isinstance(v, float) else str(v)


# ---------- 动画积木 ----------

def anim(attr, frm, to, at, dur):
    return (f'<animate attributeName="{attr}" values="{n(frm)};{n(to)}" begin="{n(round(at, 3))}s" '
            f'dur="{n(dur)}s" fill="freeze" {EASE}/>')


def anim_tf(kind, frm, to, at, dur):
    return (f'<animateTransform attributeName="transform" type="{kind}" values="{frm};{to}" '
            f'begin="{n(round(at, 3))}s" dur="{n(dur)}s" fill="freeze" {EASE}/>')


def op(frm, to, at, dur=0.6):
    return anim("opacity", frm, to, at, dur)


def flip(at, to):
    return (f'<animate attributeName="opacity" values="{1 - to};{to}" begin="{n(round(at, 3))}s" '
            f'dur="0.01s" fill="freeze"/>')


def fade(body, at, dur=0.6, out=None):
    o = op(1, 0, out, 0.4) if out is not None else ""
    return f'<g opacity="0">{op(0, 1, at, dur)}{o}{body}</g>'


def rise(body, at, dur=0.8, d=70):
    return (f'<g opacity="0">{op(0, 1, at, dur)}<g transform="translate(0 {d})">'
            f'{anim_tf("translate", f"0 {d}", "0 0", at, dur)}{body}</g></g>')


def scaled(body, cx, cy, inner):
    return (f'<g transform="translate({n(cx)} {n(cy)})">{inner}'
            f'<g transform="translate({n(-cx)} {n(-cy)})">{body}</g></g>')


def pop(body, cx, cy, at, dur=0.7, s0=0.2, peak=1.12):
    """弹出：放大过头一点再回来。"""
    return (f'<g opacity="0">{op(0, 1, at, dur * 0.5)}<g transform="translate({n(cx)} {n(cy)})">'
            f'<g transform="scale({n(s0)})"><animateTransform attributeName="transform" type="scale" '
            f'values="{n(s0)};{n(peak)};1" begin="{n(round(at, 3))}s" dur="{n(dur)}s" fill="freeze" {POP}/>'
            f'<g transform="translate({n(-cx)} {n(-cy)})">{body}</g></g></g></g>')


def slam(body, cx, cy, at, dur=0.45, s0=2.4):
    return (f'<g opacity="0">{op(0, 1, at, dur * 0.6)}<g transform="translate({n(cx)} {n(cy)})">'
            f'<g transform="scale({n(s0)})">{anim_tf("scale", n(s0), 1, at, dur)}'
            f'<g transform="translate({n(-cx)} {n(-cy)})">{body}</g></g></g></g>')


def slide_in(body, at, dx=-60, dur=0.7):
    return (f'<g opacity="0">{op(0, 1, at, dur)}<g transform="translate({dx} 0)">'
            f'{anim_tf("translate", f"{dx} 0", "0 0", at, dur)}{body}</g></g>')


def float_loop(body, at, amp=14, period=2.6):
    return (f'<g><animateTransform attributeName="transform" type="translate" values="0 0;0 {-amp};0 0" '
            f'begin="{n(round(at, 3))}s" dur="{n(period)}s" repeatCount="indefinite"/>{body}</g>')


def spin_loop(body, cx, cy, at, period=8):
    return (f'<g><animateTransform attributeName="transform" type="rotate" '
            f'values="0 {n(cx)} {n(cy)};360 {n(cx)} {n(cy)}" begin="{n(round(at, 3))}s" dur="{n(period)}s" '
            f'repeatCount="indefinite"/>{body}</g>')


# ---------- 文字（自动缩字号，别让模型写长了溢出） ----------

def text_w(s, size, font=CN):
    if font == MONO:
        return len(s) * size * 0.6
    return sum(size if ord(c) > 0x2E7F else size * 0.32 if c == " " else size * 0.58 for c in s)


def fit(s, size, maxw, font=CN, floor=0.6):
    w = text_w(s, size, font)
    if w <= maxw:
        return size
    return max(size * floor, size * maxw / w)


def text(x, y, s, size, color, weight=400, anchor="middle", font=CN, maxw=960):
    s = str(s)
    size = fit(s, size, maxw, font)
    return (f'<text x="{n(round(x, 1))}" y="{n(round(y, 1))}" font-size="{n(round(size, 1))}" fill="{color}" '
            f'font-weight="{weight}" text-anchor="{anchor}" font-family="{font}">{escape(s)}</text>')


def typed(x, y, s, size, at, color, step=0.07, font=MONO, weight=700, anchor="middle", maxw=960):
    """逐字打出（每字一个 <text> 动 opacity；微信删 fill-opacity 动画）。英文单词整词出现。"""
    s = str(s)
    size = fit(s, size, maxw, font)
    units = re.findall(r"[A-Za-z0-9.@:/_-]+|.", s)

    def uw(u):
        if font == MONO:
            return len(u) * size * 0.6
        return text_w(u, size, font)
    ws = [uw(u) for u in units]
    x0 = {"middle": x - sum(ws) / 2, "start": x, "end": x - sum(ws)}[anchor]
    out = []
    for i, (u, cw) in enumerate(zip(units, ws)):
        if u.strip():
            parts = list(u) if font == MONO else [u]
            for k, c in enumerate(parts):
                cx = x0 + k * size * 0.6
                out.append(f'<text x="{n(round(cx, 1))}" y="{n(round(y, 1))}" font-size="{n(round(size, 1))}" '
                           f'fill="{color}" font-weight="{weight}" font-family="{font}" opacity="0">{escape(c)}'
                           f'{op(0, 1, at + (i + k * 0.6) * step, 0.12)}</text>')
        x0 += cw
    return "".join(out)


# ---------- 图形积木 ----------

def draw(d, at, dur, color, width=4, glow=True):
    """描线 + 一层宽而淡的光晕（微信删滤镜，只能叠两根线）。"""
    def one(w, o):
        return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{n(w)}" stroke-linecap="round" '
                f'stroke-linejoin="round" opacity="{n(o)}" pathLength="100" stroke-dasharray="100" '
                f'stroke-dashoffset="100">{anim("stroke-dashoffset", 100, 0, at, dur)}</path>')
    return (one(width * 4, 0.16) if glow else "") + one(width, 1)


def burst(cx, cy, at, color, r=60, scale=9, width=4, dur=1.3):
    return (f'<g transform="translate({n(cx)} {n(cy)})"><g transform="scale(1)">'
            f'<animateTransform attributeName="transform" type="scale" values="1;{n(scale)}" '
            f'begin="{n(round(at, 3))}s" dur="{n(dur)}s" fill="freeze" {EASE}/>'
            f'<circle cx="0" cy="0" r="{n(r)}" fill="none" stroke="{color}" stroke-width="{n(round(width / scale * 3, 2))}" '
            f'opacity="0"><animate attributeName="opacity" values="0;0.9;0" keyTimes="0;0.1;1" '
            f'begin="{n(round(at, 3))}s" dur="{n(dur)}s" fill="freeze"/></circle></g></g>')


def grid(y0, y1, th, step=120):
    d = "".join(f"M{x} {y0}V{y1}" for x in range(0, W + 1, step))
    d += "".join(f"M0 {y}H{W}" for y in range(y0, y1 + 1, step))
    return f'<path d="{d}" stroke="{th["accent"]}" stroke-width="1.5" opacity="{th["grid"]}" fill="none"/>'


def logo(cx, cy, r, th):
    """通用标：一个环 + 偏心的点。"""
    a = th["accent"]
    return (f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" fill="none" stroke="{a}" stroke-width="{n(r * 0.16)}"/>'
            f'<circle cx="{n(cx + r * 0.18)}" cy="{n(cy - r * 0.12)}" r="{n(r * 0.34)}" fill="{a}"/>')


def chip(cx, cy, label, th, w=None, size=36, font=MONO):
    w = w or text_w(label, size, font) + 60
    return (f'<rect x="{n(round(cx - w / 2, 1))}" y="{n(round(cy - 38, 1))}" width="{n(round(w, 1))}" height="76" rx="38" '
            f'fill="{th["panel"]}" stroke="{th["accent"]}" stroke-width="3"/>'
            + text(cx, cy + 13, label, size, th["text"], 600, font=font, maxw=w - 30))


def heading(d, y, t, th, ky=150, hy=255):
    out = []
    if d.get("kicker"):
        out.append(fade(text(540, y + ky, d["kicker"], 34, th["accent"], 700), t))
    if d.get("title"):
        out.append(rise(text(540, y + hy, d["title"], 66, th["text"], 800, maxw=980), t + 0.2))
    return out


def gear_path(cx, cy, r_out, r_in, teeth):
    pts = []
    for i in range(teeth * 4):
        a = 2 * math.pi * i / (teeth * 4)
        r = r_out if i % 4 in (1, 2) else r_in
        pts.append(f"{cx + r * math.cos(a):.1f} {cy + r * math.sin(a):.1f}")
    return "M" + "L".join(pts) + "Z"


def need(d, key, kind):
    if key not in d:
        raise SystemExit(f"场景 {kind} 缺字段「{key}」")
    return d[key]


# ---------- 产品窗口 ----------

def win_shell(x, y, w, h, sk, th, tab):
    return (f'<rect x="{x + 14}" y="{y + 22}" width="{w}" height="{h}" rx="34" fill="{th["deep"]}" opacity="0.55"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="34" fill="{sk["bg"]}" stroke="{sk["edge"]}" stroke-width="2"/>'
            + "".join(f'<circle cx="{x + 40 + k * 26}" cy="{y + 38}" r="8" fill="{sk["sub"]}" opacity="0.55"/>' for k in range(3))
            + text(x + 130, y + 46, tab, 22, sk["sub"], 500, "start", MONO, maxw=w - 400))


def win_toolbar(x, y, w, sk):
    return "".join(f'<rect x="{x + w - 70 - k * 52}" y="{y + 22}" width="36" height="32" rx="10" fill="{sk["panel"]}"/>'
                   for k in range(4))


def win_sidebar(x, y, h, sk, th, items, sel=0):
    a = th["accent"]
    out = [f'<rect x="{x + 22}" y="{y + 78}" width="250" height="{h - 100}" rx="24" fill="{sk["panel"]}"/>',
           f'<rect x="{x + 40}" y="{y + 98}" width="214" height="42" rx="21" fill="{sk["deep"]}"/>',
           text(x + 62, y + 127, "搜索…", 20, sk["sub"], 400, "start")]
    for k, f in enumerate(items[:9]):
        fy = y + 196 + k * 50
        if k == sel:
            out.append(f'<rect x="{x + 36}" y="{fy - 30}" width="222" height="44" rx="14" fill="{a}" opacity="0.2"/>')
        out.append(text(x + 58, fy, f, 22, a if k == sel else sk["text"], 600 if k == sel else 400, "start", maxw=190))
    return "".join(out)


def win_doc(x0, y0, w, sk, th, doc):
    a = th["accent"]
    out = [text(x0, y0, doc.get("title", ""), 40, sk["text"], 800, "start", maxw=w)]
    if doc.get("meta"):
        out.append(text(x0, y0 + 46, doc["meta"], 22, a, 700, "start", maxw=w))
    for k, lw in enumerate([1.0, 0.92, 0.66]):
        out.append(f'<rect x="{x0}" y="{y0 + 84 + k * 30}" width="{w * lw:.0f}" height="12" rx="6" fill="{sk["line"]}"/>')
    rows = (doc.get("table") or [])[:4]
    ty = y0 + 190
    if rows:
        cols = max(len(r) for r in rows)
        out.append(f'<rect x="{x0}" y="{ty}" width="{w}" height="{46 * len(rows) + 16}" rx="16" fill="{sk["panel"]}"/>')
        for r, row in enumerate(rows):
            for c, cell in enumerate(row[:cols]):
                out.append(text(x0 + 24 + c * w / cols, ty + 44 + r * 46, cell, 22,
                                sk["sub"] if r == 0 else (a if c == cols - 1 else sk["text"]),
                                700 if r == 0 else 400, "start", MONO if c else CN, maxw=w / cols - 30))
        cy = ty + 46 * len(rows) + 46
    else:
        for k, lw in enumerate([0.95, 0.88, 0.94, 0.6, 0.9, 0.8]):
            out.append(f'<rect x="{x0}" y="{ty + k * 34}" width="{w * lw:.0f}" height="12" rx="6" fill="{sk["line"]}"/>')
        cy = ty + 6 * 34 + 30
    out.append(f'<rect x="{x0}" y="{cy}" width="{w}" height="150" rx="16" fill="{sk["deep"]}"/>')
    for k, (p, q) in enumerate([(0.28, 0.4), (0.18, 0.52), (0.36, 0.3)]):
        out.append(f'<rect x="{x0 + 26}" y="{cy + 32 + k * 36}" width="{w * p:.0f}" height="12" rx="6" fill="{a}" opacity="0.75"/>'
                   f'<rect x="{x0 + 40 + w * p:.0f}" y="{cy + 32 + k * 36}" width="{w * q:.0f}" height="12" rx="6" '
                   f'fill="{sk["sub"]}" opacity="0.6"/>')
    return "".join(out)


def window(x, y, w, h, sk, th, win, with_side=True):
    tab = win.get("tab", "untitled")
    body = win_shell(x, y, w, h, sk, th, tab)
    if with_side:
        body += win_toolbar(x, y, w, sk) + win_sidebar(x, y, h, sk, th, win.get("sidebar", []), win.get("selected", 0))
    return body + win_doc(x + 320, y + 140, w - 380, sk, th, win.get("doc", {}))


def terminal(x, y, w, h, th, title):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="26" fill="{th["deep"]}" stroke="{th["line"]}" stroke-width="2"/>'
            + "".join(f'<circle cx="{x + 34 + k * 24}" cy="{y + 34}" r="7" fill="{th["grey"]}" opacity="0.5"/>' for k in range(3))
            + text(x + w / 2, y + 42, title, 24, th["grey"], 600, font=MONO, maxw=w - 200))


# ======================================================================
# 场景
# ======================================================================

def collapse(d, y, t, th):
    """开场：一堆标签乱糟糟弹出 → 全吸进中心 → 品牌落地 + 口号逐字打出。"""
    tags = need(d, "tags", "collapse")[:16]
    a, tx_, g = th["accent"], th["text"], th["grey"]
    out = [fade(grid(y, y + SCREEN, th), t + 0.1, 1.2)]
    if d.get("intro"):
        out.append(fade(text(540, y + 230, d["intro"], 54, tx_, 700), t + 0.3, 0.6, out=t + 3.1))
    if d.get("intro_sub"):
        out.append(fade(text(540, y + 300, d["intro_sub"], 36, g), t + 0.8, 0.6, out=t + 3.1))
    order = list(range(len(tags)))
    random.Random(7).shuffle(order)
    cols = 4
    size, gap = 170, 40
    rows = math.ceil(len(tags) / cols)
    x0, y0 = 140, y + 420 + (4 - rows) * (size + gap) / 2
    cx, cy = 540, y + 900
    for k, i in enumerate(order):
        name = str(tags[i])
        hot = i % 5 == 0
        col, edge = (a, a) if hot else (g, th["line"])
        x, yy = x0 + (i % cols) * (size + gap), y0 + (i // cols) * (size + gap)
        tx, ty = x + size / 2, yy + size / 2
        tile = (f'<rect x="{x}" y="{n(yy)}" width="{size}" height="{size}" rx="40" fill="{th["panel"]}" stroke="{edge}" '
                f'stroke-width="4"/><rect x="{x + 28}" y="{n(yy + 28)}" width="44" height="10" rx="5" fill="{col}" opacity="0.7"/>'
                + text(tx, ty + 30, name, 40, col, 800, font=MONO if name.isascii() else CN, maxw=size - 24))
        sa = t + 3.3 + k * 0.025
        sucked = (f'<g opacity="1"><animate attributeName="opacity" values="1;0" begin="{n(round(sa + 0.35, 3))}s" '
                  f'dur="0.3s" fill="freeze"/><g transform="translate(0 0)">'
                  f'{anim_tf("translate", "0 0", f"{n(cx - tx)} {n(round(cy - ty, 1))}", sa, 0.6)}'
                  + scaled(tile, tx, ty, f'<g transform="scale(1)">{anim_tf("scale", 1, 0.15, sa, 0.6)}')
                  + '</g></g></g>')
        out.append(pop(sucked, tx, ty, t + 0.5 + k * 0.13, 0.5, 0.3, 1.15))
    for j in range(3):
        out.append(burst(cx, cy, t + 3.95 + j * 0.18, a, r=70, scale=8 - j * 1.5))
    out.append(pop(logo(cx, cy, 150, th), cx, cy, t + 4.0, 0.8, 0.1, 1.18))
    out.append(float_loop(fade(logo(cx, cy, 150, th), t + 4.8, 0.01), t + 5.0, 10, 3.2))
    out.append(rise(text(540, y + 1240, need(d, "brand", "collapse"), 150, tx_, 800, maxw=980), t + 4.5, 0.8))
    if d.get("slogan"):
        mono = str(d["slogan"]).isascii()
        out.append(typed(540, y + 1350, d["slogan"], 64 if mono else 56, t + 5.2, a, font=MONO if mono else CN))
    if d.get("tagline"):
        out.append(fade(text(540, y + 1470, d["tagline"], 48, tx_, 600), t + 6.2))
    if d.get("subline"):
        out.append(fade(text(540, y + 1545, d["subline"], 34, g), t + 6.6))
    out.append(float_loop(fade(text(540, y + 1780, "继续往下 ↓", 34, a, 600), t + 7.0), t + 7.2, 14, 1.6))
    return out, 7.6


def window_scene(d, y, t, th):
    """产品窗口浮现：先只有内容，侧栏和工具栏随后滑出。"""
    sk = th["win_light"] if d.get("skin", "light" if th.get("light") else "dark") == "light" else th["win_dark"]
    win = need(d, "window", "window")
    out = heading(d, y, t, th, 160, 260)
    x, wy, w, h = 60, y + 360, 960, 880
    out.append(pop(win_shell(x, wy, w, h, sk, th, win.get("tab", "untitled"))
                   + win_doc(x + 320, wy + 140, w - 380, sk, th, win.get("doc", {})), 540, wy + h / 2, t + 0.7, 0.8, 0.86, 1.02))
    out.append(draw(f"M{x + 40} {wy + h + 50}H{x + w - 40}", t + 1.4, 1.0, th["accent"], 4))
    out.append(slide_in(win_sidebar(x, wy, h, sk, th, win.get("sidebar", []), win.get("selected", 0)), t + 3.0))
    out.append(fade(win_toolbar(x, wy, w, sk), t + 3.2, 0.5))
    caps = d.get("captions", [])[:3]
    styles = [(40, th["text"], 600), (36, th["accent"], 600), (32, th["grey"], 400)]
    for k, c in enumerate(caps):
        size, col, wt = styles[k]
        out.append(fade(text(540, y + 1420 + k * 90, c, size, col, wt), t + 1.8 + k * 1.2))
    return out, 8.0


def counter(d, y, t, th):
    """大数字从 0 滚上去 + 周围漂浮标签 + 一组柱子画出来。"""
    a, tx_ = th["accent"], th["text"]
    out = [fade(grid(y, y + SCREEN, th), t - 0.4, 1.0)]
    if d.get("kicker"):
        out.append(fade(text(540, y + 170, d["kicker"], 36, a, 700), t))
    target = int(need(d, "number", "counter"))
    digits = len(str(target))
    size = 320 if digits <= 3 else 260 if digits == 4 else 200
    step = max(1, target // 25)
    vals = sorted(set(list(range(0, target + 1, step)) + [target]))
    dt = 1.6 / len(vals)
    ny = y + 620
    for i, v in enumerate(vals):
        on, off = t + 0.3 + i * dt, t + 0.3 + (i + 1) * dt
        anims = flip(on, 1) + (flip(off, 0) if v != target else "")
        out.append(f'<text x="540" y="{ny}" font-size="{size}" fill="{tx_}" font-weight="800" text-anchor="middle" '
                   f'font-family="{MONO}" opacity="0">{v}{anims}</text>')
    done = t + 0.3 + len(vals) * dt
    if d.get("suffix"):
        sx = 540 + digits * size * 0.3 + 40
        out.append(pop(text(sx, ny - 165, d["suffix"], 160, a, 800, font=MONO), sx, ny - 215, done, 0.5, 0.2, 1.4))
    for j in range(2):
        out.append(burst(540, ny - 110, done + j * 0.15, a, r=90, scale=6, width=3))
    if d.get("caption"):
        out.append(fade(text(540, ny + 250, d["caption"], 46, tx_, 600), done + 0.2))
    tags = d.get("tags", [])[:10]
    for i, tag in enumerate(tags):
        ang = -math.pi / 2 + 2 * math.pi * i / max(len(tags), 1)
        tx, ty = 540 + 450 * math.cos(ang), ny - 130 + 250 * math.sin(ang)
        c = chip(tx, ty, tag, th, size=30, font=MONO if str(tag).isascii() else CN)
        out.append(float_loop(pop(c, tx, ty, t + 0.2 + i * 0.12, 0.5, 0.3), done + i * 0.2, 10, 2.4 + i % 3 * 0.4))
    bars = d.get("bars", [])[:6]
    if bars:
        top = max(float(b[1]) for b in bars) or 1
        by = y + 1080
        for i, (name, val) in enumerate(bars):
            at = done + 0.6 + i * 0.3
            ry = by + i * 140
            length = 760 * float(val) / top
            out.append(fade(text(160, ry, name, 38, tx_, 600, "start", maxw=560)
                            + text(920, ry, val, 38, a, 800, "end", MONO, maxw=200), at, 0.4))
            out.append(f'<path d="M160 {ry + 40}H920" stroke="{tx_}" stroke-width="14" stroke-linecap="round" opacity="0.08"/>')
            out.append(draw(f"M160 {ry + 40}H{160 + max(length, 14):.0f}", at + 0.1, 0.9, a, 14))
    return out, max(7.4, done - t + 0.6 + len(bars) * 0.3 + 1.2)


def blueprint(d, y, t, th):
    """线稿自己画出来：art 选 house（建筑立面）/ device（设备卡片）/ wave（声波）+ 下方一个转动的零件。"""
    a, tx_ = th["accent"], th["text"]
    out = heading(d, y, t, th, 150, 260)
    px, py, pw, ph = 90, y + 360, 900, 860
    gpath = "".join(f"M{gx} {py + 30}V{py + ph - 30}" for gx in range(px + 30, px + pw - 29, 50))
    gpath += "".join(f"M{px + 30} {gy}H{px + pw - 30}" for gy in range(py + 30, py + ph - 29, 50))
    out.append(fade(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="24" fill="{th["panel"]}"/>'
                    f'<path d="{gpath}" stroke="{a}" stroke-width="1.5" opacity="0.09" fill="none"/>', t + 0.4, 0.8))
    out.append(draw(f"M{px} {py + 24}V{py}H{px + 24}M{px + pw - 24} {py}H{px + pw}V{py + 24}"
                    f"M{px + pw} {py + ph - 24}V{py + ph}H{px + pw - 24}M{px + 24} {py + ph}H{px}V{py + ph - 24}",
                    t + 0.5, 0.6, a, 4, glow=False))
    t0 = t + 1.0
    art = d.get("art", "house")
    if art == "house":
        gx0, gx1, gy = px + 120, px + pw - 120, py + 680
        wx0, wx1, wy = gx0 + 60, gx1 - 60, gy - 300
        lines = [(f"M{gx0 - 40} {gy}H{gx1 + 40}", 0.6, 5), (f"M{wx0} {gy}V{wy}H{wx1}V{gy}", 1.0, 5),
                 (f"M{wx0 - 40} {wy}L{(wx0 + wx1) / 2} {wy - 190}L{wx1 + 40} {wy}Z", 0.9, 5),
                 (f"M{(wx0 + wx1) / 2 - 55} {gy}V{gy - 180}H{(wx0 + wx1) / 2 + 55}V{gy}", 0.6, 4),
                 (f"M{wx0 + 60} {wy + 70}h130v110h-130ZM{wx0 + 125} {wy + 70}v110", 0.6, 3),
                 (f"M{wx1 - 190} {wy + 70}h130v110h-130ZM{wx1 - 125} {wy + 70}v110", 0.6, 3),
                 (f"M{wx1 - 150} {wy - 60}v-110h60v70", 0.5, 4)]
        dims = (wx0, wx1, gy, wy - 190)
    elif art == "device":
        # 一张卡片设备：圆角机身 + 麦克风孔 + 按键 + 指示灯
        bx0, bx1, by0, by1 = px + 200, px + pw - 200, py + 140, py + 700
        lines = [(f"M{bx0 + 60} {by0}H{bx1 - 60}A60 60 0 0 1 {bx1} {by0 + 60}V{by1 - 60}A60 60 0 0 1 {bx1 - 60} {by1}"
                  f"H{bx0 + 60}A60 60 0 0 1 {bx0} {by1 - 60}V{by0 + 60}A60 60 0 0 1 {bx0 + 60} {by0}Z", 1.2, 5),
                 (f"M{bx0 + 40} {by0 + 40}h{bx1 - bx0 - 80}v260h-{bx1 - bx0 - 80}Z", 0.8, 3),
                 ("".join(f"M{(bx0 + bx1) / 2 - 60 + k * 30} {by0 + 380}v4" for k in range(5)), 0.4, 8),
                 (f"M{(bx0 + bx1) / 2 + 60} {by0 + 470}A60 60 0 1 1 {(bx0 + bx1) / 2 - 60} {by0 + 470}"
                  f"A60 60 0 1 1 {(bx0 + bx1) / 2 + 60} {by0 + 470}", 0.7, 5),
                 (f"M{bx1 - 70} {by0 + 330}h20", 0.3, 10)]
        dims = (bx0, bx1, by1 + 0, by0)
    else:  # wave：声波
        cyw = py + 430
        pts = []
        for k in range(61):
            xx = px + 80 + k * (pw - 160) / 60
            amp = 220 * math.exp(-((k - 30) / 14) ** 2) * (0.55 + 0.45 * math.sin(k * 1.7))
            pts.append(f"{xx:.0f} {cyw - amp:.0f}" if k % 2 else f"{xx:.0f} {cyw + amp:.0f}")
        lines = [(f"M{px + 60} {cyw}H{px + pw - 60}", 0.6, 2), ("M" + "L".join(pts), 1.8, 5)]
        dims = (px + 80, px + pw - 80, py + 720, cyw - 240)
    for i, (dd, dur, w) in enumerate(lines):
        out.append(draw(dd, t0 + i * 0.45, dur, a, w))
    x0, x1, gy, ytop = dims
    dy = gy + 80
    td = t0 + len(lines) * 0.45 + 0.2
    out.append(draw(f"M{x0} {gy + 30}V{dy + 20}M{x1} {gy + 30}V{dy + 20}M{x0} {dy}H{x1}"
                    f"M{x0 + 14} {dy - 14}L{x0} {dy}L{x0 + 14} {dy + 14}M{x1 - 14} {dy - 14}L{x1} {dy}L{x1 - 14} {dy + 14}",
                    td, 0.8, tx_, 2.5, glow=False))
    if d.get("dim_w"):
        out.append(fade(text((x0 + x1) / 2, dy - 18, d["dim_w"], 32, tx_, 700, font=MONO), td + 0.6))
    hx = x1 + 60 if art != "house" else px + pw - 100
    out.append(draw(f"M{hx} {gy}V{ytop}M{hx - 14} {gy - 14}L{hx} {gy}L{hx + 14} {gy - 14}"
                    f"M{hx - 14} {ytop + 14}L{hx} {ytop}L{hx + 14} {ytop + 14}", td + 0.3, 0.8, tx_, 2.5, glow=False))
    if d.get("dim_h"):
        out.append(fade(text(hx - 22, (gy + ytop) / 2, d["dim_h"], 32, tx_, 700, "end", MONO), td + 0.9))
    if d.get("badge"):
        out.append(pop(chip(540, py + 800, d["badge"], th, None, 32, CN), 540, py + 800, td + 1.2, 0.6))
    gcx, gcy = 540, y + 1520
    tg = t + 5.2
    gear = draw(gear_path(gcx, gcy, 190, 160, 14), tg, 1.4, a, 5)
    gear += draw(f"M{gcx + 60} {gcy}A60 60 0 1 1 {gcx - 60} {gcy}A60 60 0 1 1 {gcx + 60} {gcy}", tg + 0.6, 0.8, a, 5)
    gear += draw(f"M{gcx} {gcy - 125}V{gcy - 75}M{gcx} {gcy + 75}V{gcy + 125}M{gcx - 125} {gcy}H{gcx - 75}"
                 f"M{gcx + 75} {gcy}H{gcx + 125}", tg + 1.0, 0.5, a, 4, glow=False)
    out.append(spin_loop(gear, gcx, gcy, tg + 1.5, 10))
    if d.get("caption"):
        out.append(fade(text(540, y + 1810, d["caption"], 42, tx_, 600), tg + 1.2))
    return out, 8.2


def trio(d, y, t, th):
    """三个大字砸下来 + 一条流水线（光点来回跑）+ 几行说明 + 一把锁。"""
    a, tx_, g = th["accent"], th["text"], th["grey"]
    out = [fade(grid(y, y + SCREEN, th), t - 0.4, 1.0)]
    items = need(d, "items", "trio")[:3]
    for i, it in enumerate(items):
        cx = 200 + i * 340
        at = t + i * 0.45
        big = it.get("big", "")
        out.append(slam(text(cx, y + 420, big, 240 if len(big) <= 1 else 130, tx_, 800, maxw=320), cx, y + 340, at))
        out.append(burst(cx, y + 340, at + 0.4, a, r=100, scale=2.6, width=4, dur=0.9))
        if it.get("en"):
            out.append(fade(text(cx, y + 520, it["en"], 38, a, 700, font=MONO, maxw=320), at + 0.4))
        if it.get("sub"):
            out.append(fade(text(cx, y + 585, it["sub"], 34, g, maxw=320), at + 0.6))
    flow = d.get("flow", [])[:3]
    ty = y + 860
    t2 = t + 2.2
    if len(flow) == 3:
        xs = [200, 540, 880]
        for i, (x, lab) in enumerate(zip(xs, flow)):
            out.append(pop(chip(x, ty, lab, th, 230, 34, MONO if str(lab).isascii() else CN), x, ty, t2 + i * 0.5, 0.5))
        for i in range(2):
            p, q = xs[i] + 115, xs[i + 1] - 115
            out.append(draw(f"M{p + 6} {ty}H{q - 6}M{q - 22} {ty - 14}L{q - 6} {ty}L{q - 22} {ty + 14}",
                            t2 + 0.3 + i * 0.5, 0.4, a, 4, glow=False))
        dot = (f'<circle cx="{xs[0]}" cy="{ty + 60}" r="12" fill="{a}"/>'
               f'<circle cx="{xs[0]}" cy="{ty + 60}" r="26" fill="{a}" opacity="0.25"/>')
        out.append(fade(f'<g><animateTransform attributeName="transform" type="translate" '
                        f'values="0 0;{xs[2] - xs[0]} 0;{xs[2] - xs[0]} 0" keyTimes="0;0.8;1" begin="{n(round(t2 + 1.6, 3))}s" '
                        f'dur="2s" repeatCount="indefinite"/>{dot}</g>', t2 + 1.6, 0.3))
    for i, r in enumerate(d.get("rows", [])[:3]):
        out.append(rise(text(540, y + 1080 + i * 90, r, 38, tx_, 500), t2 + 1.8 + i * 0.3, 0.6, 40))
    lx, ly = 540, y + 1520
    tl = t + 5.4
    if not (d.get("lock_title") or d.get("lock_sub") or d.get("lock")):  # 锁只给隐私 / 安全 / 本地题材，没填就不画
        return out, 7.6
    out.append(draw(f"M{lx - 90} {ly - 20}h180v170h-180Z", tl, 0.7, a, 6))
    out.append(draw(f"M{lx - 55} {ly - 20}V{ly - 80}A55 55 0 0 1 {lx + 55} {ly - 80}V{ly - 20}", tl + 0.4, 0.6, a, 6))
    out.append(pop(f'<circle cx="{lx}" cy="{ly + 55}" r="18" fill="{a}"/>', lx, ly + 55, tl + 0.9, 0.4))
    if d.get("lock_title"):
        out.append(fade(text(540, ly + 250, d["lock_title"], 46, tx_, 700), tl + 1.0))
    if d.get("lock_sub"):
        out.append(fade(text(540, ly + 320, d["lock_sub"], 34, g), tl + 1.3))
    return out, 7.6


def agent(d, y, t, th):
    """终端里打一句指令 → 光点跑进窗口 → 窗口里划中的那句被改写 + 4 张能力卡。"""
    a, tx_, g = th["accent"], th["text"], th["grey"]
    sk = th["win_dark"]
    out = heading(d, y, t, th, 150, 250)
    tx, ty, tw = 90, y + 330, 900
    out.append(pop(terminal(tx, ty, tw, 250, th, d.get("terminal", "agent")), 540, ty + 125, t + 0.6, 0.6, 0.9, 1.03))
    out.append(typed(tx + 40, ty + 130, "› " + need(d, "prompt", "agent"), 36, t + 1.2, tx_, 0.08, CN, 600, "start", 820))
    if d.get("reply"):
        out.append(fade(text(tx + 40, ty + 200, "✓ " + d["reply"], 30, a, 600, "start", maxw=820), t + 4.2))
    out.append(draw(f"M540 {ty + 260}V{ty + 350}", t + 2.6, 0.5, a, 4))
    out.append(fade(f'<g><animateTransform attributeName="transform" type="translate" values="0 0;0 90" '
                    f'begin="{n(round(t + 3.0, 3))}s" dur="0.9s" repeatCount="indefinite"/>'
                    f'<circle cx="540" cy="{ty + 260}" r="10" fill="{a}"/></g>', t + 3.0, 0.2, out=t + 5.4))
    wx, wy, ww, wh = 90, y + 700, 900, 560
    body = win_shell(wx, wy, ww, wh, sk, th, d.get("doc_tab", "untitled")) + \
        text(wx + 60, wy + 140, d.get("doc_title", ""), 40, sk["text"], 800, "start", maxw=780)
    for k, lw in enumerate([0.86, 0.7]):
        body += f'<rect x="{wx + 60}" y="{wy + 190 + k * 34}" width="{(ww - 120) * lw:.0f}" height="12" rx="6" fill="{sk["line"]}"/>'
    body += f'<rect x="{wx + 48}" y="{wy + 268}" width="{ww - 96}" height="76" rx="14" fill="{a}" opacity="0.18"/>'
    for k, lw in enumerate([0.92, 0.8, 0.5]):
        body += f'<rect x="{wx + 60}" y="{wy + 380 + k * 34}" width="{(ww - 120) * lw:.0f}" height="12" rx="6" fill="{sk["line"]}"/>'
    out.append(pop(body, 540, wy + wh / 2, t + 0.9, 0.7, 0.9, 1.02))
    old = text(wx + 72, wy + 318, need(d, "before", "agent"), 34, sk["text"], 500, "start", maxw=ww - 150)
    new = text(wx + 72, wy + 318, need(d, "after", "agent"), 34, a, 700, "start", maxw=ww - 150)
    out.append(f'<g opacity="0">{op(0, 1, t + 1.2, 0.5)}{op(1, 0, t + 3.6, 0.4)}{old}</g>')
    out.append(fade(new, t + 3.9, 0.5))
    out.append(burst(wx + ww - 80, wy + 306, t + 3.9, a, r=30, scale=3, width=3, dur=0.8))
    for k, ab in enumerate(d.get("abilities", [])[:4]):
        head, sub = (ab + [""])[:2] if isinstance(ab, list) else (ab, "")
        cx, cy = 90 + (k % 2) * 460, y + 1330 + (k // 2) * 170
        card = (f'<rect x="{cx}" y="{cy}" width="440" height="150" rx="24" fill="{th["panel"]}" stroke="{th["line"]}" stroke-width="2"/>'
                f'<circle cx="{cx + 40}" cy="{cy + 56}" r="9" fill="{a}"/>'
                + text(cx + 64, cy + 66, head, 32, tx_, 700, "start", maxw=350)
                + text(cx + 40, cy + 116, sub, 26, g, 400, "start", maxw=370))
        out.append(rise(card, t + 5.0 + k * 0.25, 0.6, 40))
    for k, line in enumerate(d.get("footer", [])[:2]):
        out.append(fade(text(540, y + 1720 + k * 70, line, 30 if k == 0 else 28, tx_ if k == 0 else g, 600 if k == 0 else 400),
                        t + 6.2 + k * 0.4))
    return out, 8.8


def skin(d, y, t, th):
    """一句话换肤：亮色窗口 → 一道光扫过 → 暗色窗口 + 一排色点。"""
    a, tx_, g = th["accent"], th["text"], th["grey"]
    out = heading(d, y, t, th, 150, 250)
    tx, ty, tw = 140, y + 320, 800
    if d.get("prompt"):  # 没有「一句话换肤」这个功能就不放终端
        out.append(pop(terminal(tx, ty, tw, 150, th, d.get("terminal", "agent")), 540, ty + 75, t + 0.5, 0.5, 0.9, 1.03))
        out.append(typed(tx + 40, ty + 112, "› " + d["prompt"], 34, t + 1.0, tx_, 0.08, CN, 600, "start", 720))
    elif d.get("subtitle"):
        out.append(fade(text(540, ty + 110, d["subtitle"], 38, g, 500), t + 0.6))
    win = d.get("window", {})
    x, wy, w, h = 60, y + 560, 960, 880
    sw = t + 3.0
    out.append(pop(window(x, wy, w, h, th["win_light"], th, win), 540, wy + h / 2, t + 0.6, 0.7, 0.9, 1.02))
    out.append(fade(window(x, wy, w, h, th["win_dark"], th, win), sw, 1.1))
    out.append(f'<g opacity="0"><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.8;1" '
               f'begin="{n(round(sw, 3))}s" dur="1.2s" fill="freeze"/><g transform="translate(0 0)">'
               f'{anim_tf("translate", "0 0", f"{w - 20} 0", sw, 1.2)}'
               f'<rect x="{x + 4}" y="{wy + 10}" width="30" height="{h - 20}" rx="15" fill="{a}" opacity="0.25"/>'
               f'<rect x="{x + 15}" y="{wy + 10}" width="8" height="{h - 20}" rx="4" fill="{a}"/></g></g>')
    out.append(draw(f"M{x + 40} {wy + h + 50}H{x + w - 40}", sw + 0.8, 1.0, a, 4))
    if d.get("caption"):
        out.append(fade(text(540, y + 1600, d["caption"], 34, tx_, 600), sw + 1.0))
    if d.get("swatches", True):
        for k, c in enumerate(th["swatches"][:7]):
            cx = 540 + (k - 3) * 84
            ring = f'<circle cx="{cx}" cy="{y + 1700}" r="30" fill="none" stroke="{tx_}" stroke-width="3"/>' if k == 1 else ""
            out.append(pop(f'<circle cx="{cx}" cy="{y + 1700}" r="22" fill="{c}"/>{ring}', cx, y + 1700, sw + 1.4 + k * 0.1, 0.4))
    if d.get("footnote"):
        out.append(fade(text(540, y + 1790, d["footnote"], 30, g), sw + 2.2))
    return out, 8.4


def statement(d, y, t, th):
    """万能一屏：大标题 + 中间一个大符号/大字（带光环）+ 几行逐条出现的要点。"""
    a, tx_, g = th["accent"], th["text"], th["grey"]
    out = [fade(grid(y, y + SCREEN, th), t - 0.4, 1.0)] + heading(d, y, t, th, 200, 320)
    cy = y + 760
    mark = d.get("mark")
    for j in range(3):
        out.append(burst(540, cy, t + 0.9 + j * 0.2, a, r=80, scale=4.5 - j, width=3, dur=1.4))
    if mark:
        out.append(pop(f'<circle cx="540" cy="{cy}" r="230" fill="{th["panel"]}" stroke="{a}" stroke-width="4"/>'
                       + text(540, cy + (70 if len(str(mark)) <= 2 else 40), mark, 200 if len(str(mark)) <= 2 else 110, a, 800,
                              font=MONO if str(mark).isascii() else CN, maxw=400), 540, cy, t + 0.8, 0.8, 0.3, 1.1))
    else:
        out.append(pop(logo(540, cy, 200, th), 540, cy, t + 0.8, 0.8, 0.2, 1.12))
    pts = d.get("points", [])[:5]
    for k, p in enumerate(pts):
        py = y + 1140 + k * 120
        row = (f'<rect x="120" y="{py - 62}" width="840" height="96" rx="24" fill="{th["panel"]}"/>'
               f'<circle cx="172" cy="{py - 14}" r="10" fill="{a}"/>' + text(206, py, p, 36, tx_, 600, "start", maxw=720))
        out.append(slide_in(row, t + 1.8 + k * 0.35, -50, 0.6))
    return out, max(6.0, 2.4 + len(pts) * 0.35 + 1.0)


def price(d, y, t, th):
    """价格卡收尾 + 网址逐字打出 + 标。"""
    a, tx_, g = th["accent"], th["text"], th["grey"]
    out = [fade(grid(y, y + SCREEN, th), t - 0.4, 1.0)] + heading(d, y, t + 0.3, th, 200, 310)
    cards = need(d, "cards", "price")[:2]
    xs = [90, 560] if len(cards) == 2 else [325]
    lines_n = max(len(c.get("items", [])) for c in cards)
    ch = 400 + lines_n * 80
    for k, (c, x) in enumerate(zip(cards, xs)):
        hot = c.get("highlight", k == len(cards) - 1 and len(cards) > 1)
        cy0 = y + 460
        body = (f'<rect x="{x + 12}" y="{cy0 + 18}" width="430" height="{ch}" rx="36" fill="{th["deep"]}" opacity="0.6"/>'
                f'<rect x="{x}" y="{cy0}" width="430" height="{ch}" rx="36" fill="{th["panel"]}" '
                f'stroke="{a if hot else th["line"]}" stroke-width="{4 if hot else 2}"/>'
                + text(x + 215, cy0 + 90, c.get("name", ""), 40, tx_, 700, maxw=380)
                + text(x + 215, cy0 + 250, c.get("price", ""), 130, a if hot else tx_, 800, font=MONO, maxw=390))
        for j, it in enumerate(c.get("items", [])[:5]):
            body += text(x + 215, cy0 + 380 + j * 80, it, 32, g, maxw=390)
        if c.get("badge"):
            bw = text_w(c["badge"], 30) + 60
            body += (f'<rect x="{x + 215 - bw / 2:.0f}" y="{cy0 - 28}" width="{bw:.0f}" height="56" rx="28" fill="{a}"/>'
                     + text(x + 215, cy0 + 11, c["badge"], 30, th["on_accent"], 800))
        out.append(pop(body, x + 215, cy0 + ch / 2, t + 1.2 + k * 0.4, 0.7, 0.6, 1.05))
    if d.get("note"):
        out.append(fade(text(540, y + 1300, d["note"], 34, g), t + 2.2))
    if d.get("url"):
        out.append(typed(540, y + 1450, d["url"], 64, t + 2.6, a, 0.06))
        out.append(draw(f"M{540 - text_w(d['url'], 64, MONO) / 2 - 20:.0f} {y + 1485}H{540 + text_w(d['url'], 64, MONO) / 2 + 20:.0f}",
                        t + 3.6, 0.6, a, 4))
    out.append(float_loop(pop(logo(540, y + 1660, 70, th), 540, y + 1660, t + 4.0, 0.6), t + 4.6, 8, 3))
    if d.get("footer"):
        out.append(fade(text(540, y + 1830, d["footer"], 30, g, 600, font=MONO if str(d["footer"]).isascii() else CN), t + 4.4))
    return out, 6.0


SCENES = {"collapse": collapse, "window": window_scene, "counter": counter, "blueprint": blueprint,
          "trio": trio, "agent": agent, "skin": skin, "statement": statement, "price": price}
