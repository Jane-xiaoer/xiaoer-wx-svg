"""更多场景（录音卡那篇带出来的，任何题材都能用）。

receipt  账单从打印口吐出来 + 印章砸下
devices  几台设备蓝牙同步到电脑（波纹 + 飞数据点）
fanout   一段东西裂成很多张卡片飞到各自位置
live     现场会议：点一下开会 → 字幕循环冒出、声波跳、点「？」揭开说话人、划中一句飞进笔记
search   搜索框打字 → 结果落下（命中词高亮）→ 待办一条条打勾

互动的做法：公众号会删 id，所以「点 A 让 B 动」不行；只能「点到谁谁自己动」。
于是用「点一下揭开」：上面盖一层，点了它自己淡出并移走，露出下面一直在循环播放的内容；
不点的人过几秒也自动揭开（begin="click;Ns"）。
"""
import math

from scenes import (CN, MONO, SCREEN, EASE, anim, anim_tf, burst, draw, fade, float_loop, heading, n, need,
                    op, pop, rise, slam, slide_in, text, text_w, typed)


def acc2(th):
    return th.get("accent2", th["grey"])


def loop_show(body, t0, period, start, end, fadein=0.3, fadeout=0.4):
    """在一个循环周期里 start 秒出现、end 秒消失（相对周期）。"""
    k = lambda s: round(min(max(s / period, 0), 1), 4)  # noqa: E731
    kt = f"0;{k(start)};{k(start + fadein)};{k(end)};{k(end + fadeout)};1"
    return (f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="{kt}" '
            f'begin="{n(round(t0, 3))}s" dur="{n(period)}s" repeatCount="indefinite"/>{body}</g>')


def tap_cover(body, auto_at, hint=True):
    """点一下揭开：被点（或到 auto_at 秒）后自己淡出并移出画面，不再挡点击。"""
    return (f'<g><animate attributeName="opacity" values="1;0" begin="click;{n(round(auto_at, 2))}s" dur="0.45s" '
            f'fill="freeze" restart="never"/><g transform="translate(0 0)">'
            f'<animateTransform attributeName="transform" type="translate" values="0 0;3000 0" '
            f'begin="click+0.5s;{n(round(auto_at + 0.5, 2))}s" dur="0.01s" fill="freeze" restart="never"/>{body}</g></g>')


# ---------------------------------------------------------------- receipt

def receipt(d, y, t, th):
    a, tx_, g = th["accent"], th["text"], th["grey"]
    items = need(d, "items", "receipt")[:6]
    paper, ink, faint = "#f4efe6", "#2a2622", "#8a8075"
    x0, w = 200, 680
    slot = y + 430
    h = 300 + len(items) * 92
    body = [f'<path d="M{x0} {slot}H{x0 + w}V{slot + h}' +
            "".join(f"L{x0 + w - (k + 0.5) * w / 17:.0f} {slot + h + (14 if k % 2 == 0 else 0)}" for k in range(17)) +
            f'L{x0} {slot + h}Z" fill="{paper}"/>',
            text(540, slot + 90, d.get("receipt_title", "账单"), 40, ink, 800, font=MONO, maxw=w - 60),
            f'<path d="M{x0 + 40} {slot + 130}H{x0 + w - 40}" stroke="{faint}" stroke-width="3" stroke-dasharray="10 10"/>']
    for k, it in enumerate(items):
        name, note = (list(it) + [""])[:2] if isinstance(it, list) else (it, "")
        iy = slot + 200 + k * 92
        body.append(text(x0 + 50, iy, name, 34, ink, 600, "start", maxw=380))
        body.append(text(x0 + w - 50, iy, note, 30, faint, 500, "end", MONO, maxw=220))
    ty = slot + 200 + len(items) * 92
    body.append(f'<path d="M{x0 + 40} {ty - 40}H{x0 + w - 40}" stroke="{faint}" stroke-width="3" stroke-dasharray="10 10"/>')
    if d.get("total"):
        body.append(text(x0 + 50, ty + 20, d["total"][0], 36, ink, 800, "start", maxw=300) +
                    text(x0 + w - 50, ty + 20, d["total"][1], 34, ink, 800, "end", MONO, maxw=300))
    dur = 2.4
    out = [f'<g transform="translate(0 {-h})">{anim_tf("translate", f"0 {-h}", "0 0", t + 0.6, dur)}{"".join(body)}</g>',
           f'<rect x="0" y="{y}" width="1080" height="{slot - y}" fill="{th["bg"]}"/>',
           f'<rect x="150" y="{slot - 24}" width="780" height="44" rx="22" fill="{th["deep"]}" stroke="{th["line"]}" stroke-width="2"/>',
           f'<rect x="180" y="{slot - 6}" width="720" height="8" rx="4" fill="{th["bg"]}"/>']
    out += heading(d, y, t, th, 150, 260)
    # 印章：旋转的双框 + 大字
    st = d.get("stamp", "¥0")
    cx, cy = 600, slot + h * 0.55
    seal = (f'<g transform="rotate(-14 {cx} {cy})" opacity="0.93">'
            f'<rect x="{cx - 230}" y="{cy - 140}" width="460" height="280" rx="34" fill="none" stroke="{a}" stroke-width="10"/>'
            f'<rect x="{cx - 206}" y="{cy - 116}" width="412" height="232" rx="24" fill="none" stroke="{a}" stroke-width="4"/>'
            + text(cx, cy + 50, st, 150, a, 900, font=MONO, maxw=380)
            + (text(cx, cy + 100, d["stamp_sub"], 30, a, 800, maxw=360) if d.get("stamp_sub") else "") + "</g>")
    ts = t + 0.6 + dur + 0.4
    out.append(slam(seal, cx, cy, ts, 0.4, 2.6))
    out.append(burst(cx, cy, ts + 0.35, a, r=120, scale=3.2, width=5, dur=0.9))
    caps = d.get("captions", [])[:3]
    styles = [(46, tx_, 800), (34, a, 600), (28, g, 400)]
    for k, c in enumerate(caps):
        size, col, wt = styles[k]
        out.append(rise(text(540, y + 1500 + k * 90, c, size, col, wt), ts + 0.9 + k * 0.4, 0.6, 40))
    return out, max(8.0, ts - t + 2.6)


# ---------------------------------------------------------------- devices

def _card_device(x, y, w, h, col):
    """卡片录音卡：圆角机身 + 一排麦克风孔 + 指示灯 + 磁吸圈。"""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="38" fill="none" stroke="{col}" stroke-width="5"/>'
            + "".join(f'<circle cx="{x + w / 2 - 48 + k * 24}" cy="{y + 60}" r="5" fill="{col}"/>' for k in range(5))
            + f'<circle cx="{x + w / 2}" cy="{y + h * 0.58}" r="{w * 0.24:.0f}" fill="none" stroke="{col}" stroke-width="4" opacity="0.6"/>'
            + f'<circle cx="{x + w / 2}" cy="{y + h * 0.58}" r="{w * 0.1:.0f}" fill="none" stroke="{col}" stroke-width="3" opacity="0.4"/>'
            + f'<rect x="{x + w - 56}" y="{y + 40}" width="26" height="10" rx="5" fill="{col}"/>')


def _bean_device(x, y, w, h, col):
    """豆子形录音设备：胶囊机身 + 一颗按键。"""
    r = h / 2
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="none" stroke="{col}" stroke-width="5"/>'
            f'<circle cx="{x + r}" cy="{y + r}" r="{r * 0.36:.0f}" fill="none" stroke="{col}" stroke-width="4"/>'
            + "".join(f'<path d="M{x + w * 0.5 + k * 26} {y + r - 24}v48" stroke="{col}" stroke-width="5" stroke-linecap="round" opacity="0.7"/>' for k in range(4)))


def _laptop(cx, y, w, col, sub):
    h = w * 0.58
    x = cx - w / 2
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h:.0f}" rx="22" fill="none" stroke="{col}" stroke-width="5"/>'
            f'<path d="M{x - 70} {y + h + 26:.0f}H{x + w + 70}L{x + w + 30} {y + h + 6:.0f}H{x - 30}Z" fill="none" stroke="{col}" stroke-width="5" stroke-linejoin="round"/>'
            f'<rect x="{cx - 40}" y="{y + h + 8:.0f}" width="80" height="10" rx="5" fill="{sub}"/>')


def _waves(cx, cy, t, col, period=2.4):
    """蓝牙波纹：三圈弧线循环向外扩。"""
    out = []
    for k in range(3):
        arc = f'<path d="M{cx - 40} {cy - 30}A50 50 0 0 1 {cx + 40} {cy - 30}" fill="none" stroke="{col}" stroke-width="4" stroke-linecap="round"/>'
        out.append(f'<g opacity="0"><animate attributeName="opacity" values="0;0.9;0" begin="{n(round(t + k * period / 3, 2))}s" '
                   f'dur="{period}s" repeatCount="indefinite"/><g transform="translate({cx} {cy})"><g transform="scale(1)">'
                   f'<animateTransform attributeName="transform" type="scale" values="0.6;2.2" begin="{n(round(t + k * period / 3, 2))}s" '
                   f'dur="{period}s" repeatCount="indefinite"/><g transform="translate({-cx} {-cy})">{arc}</g></g></g></g>')
    return "".join(out)


def _packets(x0, y0, x1, y1, t, col, count=4, period=1.8):
    """数据点从 (x0,y0) 循环飞到 (x1,y1)。"""
    out = []
    for k in range(count):
        b = round(t + k * period / count, 2)
        out.append(f'<g opacity="0"><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.8;1" begin="{b}s" '
                   f'dur="{period}s" repeatCount="indefinite"/><g><animateTransform attributeName="transform" type="translate" '
                   f'values="0 0;{x1 - x0:.0f} {y1 - y0:.0f}" begin="{b}s" dur="{period}s" repeatCount="indefinite"/>'
                   f'<rect x="{x0 - 9}" y="{y0 - 9}" width="18" height="18" rx="5" fill="{col}"/></g></g>')
    return "".join(out)


def devices(d, y, t, th):
    a, b2, tx_, g = th["accent"], acc2(th), th["text"], th["grey"]
    out = heading(d, y, t, th, 150, 260)
    devs = need(d, "devices", "devices")[:2]
    slots = [(120, y + 400, 300, 420, "card"), (640, y + 500, 340, 200, "bean")]
    for k, (dv, (x, yy, w, h, kind)) in enumerate(zip(devs, slots)):
        kind = dv.get("shape", kind)
        col = a if k == 0 else b2
        shape = _card_device(x, yy, w, h, col) if kind == "card" else _bean_device(x, yy, w, h, col)
        at = t + 0.6 + k * 0.9
        out.append(pop(shape, x + w / 2, yy + h / 2, at, 0.7, 0.5, 1.06))
        ly = max(yy + h, y + 820) + 70
        out.append(fade(text(x + w / 2, ly, dv.get("name", ""), 36, tx_, 700, maxw=440), at + 0.4))
        if dv.get("sub"):
            out.append(fade(text(x + w / 2, ly + 52, dv["sub"], 26, g, 400, maxw=440), at + 0.6))
        if dv.get("tag"):
            tw = text_w(dv["tag"], 44, MONO) + 60
            tag = (f'<path d="M{x + w - 30} {yy - 30}h{tw:.0f}l34 38l-34 38h-{tw:.0f}Z" fill="{col}"/>'
                   f'<circle cx="{x + w - 6}" cy="{yy + 8}" r="8" fill="{th["bg"]}"/>'
                   + text(x + w - 30 + tw / 2 + 10, yy + 23, dv["tag"], 44, th["on_accent"], 900, font=MONO, maxw=tw))
            out.append(float_loop(pop(tag, x + w + tw / 2, yy + 8, at + 0.9, 0.5, 0.3, 1.2), at + 1.5, 6, 2.4))
        out.append(fade(_waves(x + w / 2, yy - 10, at + 1.2, col), at + 1.2, 0.3))
    lap_y = y + 1110
    tgt = d.get("target", {})
    out.append(rise(_laptop(540, lap_y, 440, tx_, g), t + 2.4, 0.8, 50))
    out.append(_packets(270, y + 820, 500, lap_y + 120, t + 3.2, a))
    out.append(_packets(810, y + 700, 580, lap_y + 120, t + 3.6, b2))
    for k, ln in enumerate(tgt.get("lines", [])[:3]):
        out.append(loop_show(text(360, lap_y + 70 + k * 56, ln, 28, tx_ if k == 0 else g, 600 if k == 0 else 400, "start", maxw=370),
                             t + 3.4, 6.0, 0.4 + k * 0.9, 5.2))
    if tgt.get("name"):
        out.append(fade(text(540, lap_y + 380, tgt["name"], 38, tx_, 700), t + 3.0))
    for k, c in enumerate(d.get("captions", [])[:2]):
        out.append(fade(text(540, y + 1600 + k * 80, c, 36 if k == 0 else 30, a if k == 0 else g, 700 if k == 0 else 400), t + 4.2 + k * 0.4))
    return out, 8.4


# ---------------------------------------------------------------- fanout

def fanout(d, y, t, th):
    a, b2, tx_, g = th["accent"], acc2(th), th["text"], th["grey"]
    out = heading(d, y, t, th, 150, 260)
    sy = y + 400
    bars = "".join(f'<rect x="{300 + k * 20}" y="{sy - (10 + 34 * abs(math.sin(k * 0.9)) * (1 - abs(k - 12) / 14)):.0f}" '
                   f'width="10" height="{2 * (10 + 34 * abs(math.sin(k * 0.9)) * (1 - abs(k - 12) / 14)):.0f}" rx="5" fill="{a}"/>'
                   for k in range(25))
    src = (f'<rect x="250" y="{sy - 60}" width="580" height="120" rx="60" fill="{th["panel"]}" stroke="{a}" stroke-width="3"/>{bars}'
           + text(540, sy + 110, d.get("source", ""), 30, g, 500))
    out.append(pop(src, 540, sy, t + 0.5, 0.6, 0.6, 1.05))
    items = need(d, "items", "fanout")[:10]
    split = t + 1.6
    out.append(burst(540, sy, split, a, r=80, scale=5, width=4))
    for k, it in enumerate(items):
        name, outp = (list(it) + [""])[:2]
        cx, cy = 90 + (k % 2) * 460, y + 600 + (k // 2) * 172
        card = (f'<rect x="{cx}" y="{cy}" width="440" height="150" rx="26" fill="{th["panel"]}" stroke="{th["line"]}" stroke-width="2"/>'
                f'<rect x="{cx}" y="{cy + 30}" width="8" height="90" rx="4" fill="{a if k % 2 == 0 else b2}"/>'
                + text(cx + 40, cy + 66, name, 36, tx_, 800, "start", maxw=370)
                + text(cx + 40, cy + 116, "→ " + outp, 28, a if k % 2 == 0 else b2, 600, "start", maxw=380))
        mx, my = cx + 220, cy + 75
        at = split + 0.08 * k
        out.append(f'<g opacity="0">{op(0, 1, at, 0.3)}<g transform="translate({540 - mx:.0f} {sy - my:.0f})">'
                   f'{anim_tf("translate", f"{540 - mx:.0f} {sy - my:.0f}", "0 0", at, 0.8)}'
                   f'<g transform="translate({mx} {my})"><g transform="scale(0.2)">{anim_tf("scale", 0.2, 1, at, 0.8)}'
                   f'<g transform="translate({-mx} {-my})">{card}</g></g></g></g></g>')
    for k, c in enumerate(d.get("captions", [])[:2]):
        out.append(fade(text(540, y + 1520 + k * 80, c, 36 if k == 0 else 30, tx_ if k == 0 else g, 700 if k == 0 else 400),
                        split + 1.4 + k * 0.4))
    if d.get("note"):
        out.append(fade(f'<rect x="120" y="{y + 1700}" width="840" height="96" rx="48" fill="{a}" opacity="0.14"/>'
                        + text(540, y + 1762, d["note"], 32, a, 700, maxw=780), split + 2.2))
    return out, 8.0


# ---------------------------------------------------------------- live（可以点）

def live(d, y, t, th):
    a, b2, tx_, g = th["accent"], acc2(th), th["text"], th["grey"]
    sk = th["win_dark"]
    out = heading(d, y, t, th, 150, 255)
    x, wy, w, h = 50, y + 330, 980, 1040
    speakers = need(d, "speakers", "live")
    spk_col = [a, b2, g, "#f7c59f"]
    lines = need(d, "lines", "live")[:5]
    period = 2.0 * len(lines) + 4.0
    lt = t + 0.6
    # 窗口外壳 + 录音中 + 声波
    win = (f'<rect x="{x + 14}" y="{wy + 22}" width="{w}" height="{h}" rx="34" fill="{th["deep"]}" opacity="0.55"/>'
           f'<rect x="{x}" y="{wy}" width="{w}" height="{h}" rx="34" fill="{sk["bg"]}" stroke="{sk["edge"]}" stroke-width="2"/>'
           f'<path d="M{x + 600} {wy + 150}V{wy + h - 30}" stroke="{sk["line"]}" stroke-width="2"/>'
           + text(x + 630, wy + 200, d.get("note_title", "我的笔记"), 30, sk["text"], 800, "start", maxw=320))
    out.append(fade(win, t + 0.3, 0.5))
    rec = (f'<circle cx="{x + 50}" cy="{wy + 62}" r="12" fill="#ff5a5f"><animate attributeName="opacity" values="1;0.2;1" '
           f'begin="{n(t)}s" dur="1.2s" repeatCount="indefinite"/></circle>'
           + text(x + 76, wy + 73, d.get("status", "录音中"), 28, sk["text"], 700, "start", maxw=200))
    out.append(fade(rec, t + 0.3))
    wave = []
    for k in range(28):
        bx = x + 330 + k * 22
        cy = wy + 62
        hgt = 10 + 30 * abs(math.sin(k * 1.3))
        vals = ";".join(f"1 {v:.2f}" for v in (0.3, 1.0, 0.5, 0.85, 0.3))
        wave.append(f'<g transform="translate({bx} {cy})"><g><animateTransform attributeName="transform" type="scale" '
                    f'values="{vals}" begin="{n(round(t + k * 0.07, 2))}s" dur="1.4s" repeatCount="indefinite"/>'
                    f'<rect x="-4" y="{-hgt:.0f}" width="8" height="{2 * hgt:.0f}" rx="4" fill="{a}"/></g></g>')
    out.append(fade("".join(wave), t + 0.3))
    if d.get("system_audio"):
        out.append(fade(f'<rect x="{x + 30}" y="{wy + 100}" width="{text_w(d["system_audio"], 24) + 40:.0f}" height="40" rx="20" '
                        f'fill="{b2}" opacity="0.18"/>' + text(x + 50, wy + 128, d["system_audio"], 24, b2, 700, "start", maxw=520), t + 0.5))
    # 字幕：循环一句句冒出来（像在实时转）
    tap_hint = []
    for k, ln in enumerate(lines):
        si, s = ln[0], ln[1]
        ly = wy + 200 + k * 160
        col = spk_col[si % len(spk_col)]
        name = speakers[si]
        cw = text_w(name, 24) + 36
        chip = (f'<rect x="{x + 30}" y="{ly - 30}" width="{cw:.0f}" height="40" rx="20" fill="{col}" opacity="0.22"/>'
                + text(x + 30 + cw / 2, ly - 2, name, 24, col, 800, maxw=cw))
        row = chip + text(x + 30, ly + 56, s, 32, sk["text"], 500, "start", maxw=540)
        if k == d.get("highlight", -1):
            row = (f'<rect x="{x + 18}" y="{ly + 16}" width="{min(text_w(s, 32), 540) + 24:.0f}" height="56" rx="12" fill="{a}" opacity="0.2"/>' + row)
        out.append(loop_show(row, lt, period, k * 2.0, period - 1.0))
        if ln[2:] and ln[2] == "?":
            # 说话人没认出来：盖一个「？」，点一下（或过一会儿）揭开名字
            cover = (f'<rect x="{x + 26}" y="{ly - 34}" width="{max(cw, 70) + 8:.0f}" height="48" rx="24" fill="{sk["bg"]}"/>'
                     f'<rect x="{x + 30}" y="{ly - 30}" width="{max(cw, 70):.0f}" height="40" rx="20" fill="none" stroke="{tx_}" '
                     f'stroke-width="2" stroke-dasharray="6 5"/>' + text(x + 30 + max(cw, 70) / 2, ly - 2, "？点我", 22, tx_, 800, maxw=cw + 20))
            tap_hint.append(tap_cover(float_loop(cover, t + 1, 3, 1.6), t + 9.0 + k * 0.6))
    out += tap_hint
    # 笔记：划中的那句飞进来，然后「顺一下」
    for k, nt in enumerate(d.get("notes", [])[:4]):
        nyy = wy + 270 + k * 110
        item = (f'<rect x="{x + 625}" y="{nyy - 40}" width="330" height="86" rx="16" fill="{sk["panel"]}"/>'
                + text(x + 645, nyy + 12, nt, 26, sk["text"], 600, "start", maxw=300))
        out.append(slide_in(item, t + 3.0 + k * 1.6, 60, 0.6))
    if d.get("tidy"):
        tb = (f'<rect x="{x + 625}" y="{wy + h - 120}" width="330" height="76" rx="38" fill="{a}"/>'
              + text(x + 790, wy + h - 70, d["tidy"], 28, th["on_accent"], 800, maxw=300))
        out.append(pop(tb, x + 790, wy + h - 82, t + 3.0 + 1.6 * len(d.get("notes", [])[:4]), 0.5))
    # 最上面一层：「点一下 · 开会」
    if d.get("button"):
        bx, by = 540, wy + h / 2
        cov = (f'<rect x="{x}" y="{wy}" width="{w}" height="{h}" rx="34" fill="{th["bg"]}" opacity="0.94"/>'
               f'<g transform="translate({bx} {by})"><g><animateTransform attributeName="transform" type="scale" values="1;1.08;1" '
               f'begin="{n(t)}s" dur="1.6s" repeatCount="indefinite"/>'
               f'<circle cx="0" cy="0" r="150" fill="{a}"/>'
               f'<circle cx="0" cy="0" r="190" fill="none" stroke="{a}" stroke-width="4" opacity="0.4"/>'
               + text(0, 18, d["button"], 50, th["on_accent"], 900, maxw=260) + '</g></g>'
               + text(bx, by + 290, d.get("button_hint", "点一下试试 · 不点也会自己开始"), 30, g, 500))
        out.append(tap_cover(cov, t + d.get("auto_start", 5.0)))
    for k, c in enumerate(d.get("captions", [])[:3]):
        out.append(fade(text(540, y + 1470 + k * 80, c, 34 if k == 0 else 30, tx_ if k == 0 else g, 700 if k == 0 else 400),
                        t + 6.0 + k * 0.5))
    return out, 11.0


# ---------------------------------------------------------------- search

def search(d, y, t, th):
    a, b2, tx_, g = th["accent"], acc2(th), th["text"], th["grey"]
    out = heading(d, y, t, th, 150, 255)
    sy = y + 400
    box = (f'<rect x="90" y="{sy - 55}" width="900" height="110" rx="55" fill="{th["panel"]}" stroke="{a}" stroke-width="3"/>'
           f'<circle cx="160" cy="{sy - 6}" r="22" fill="none" stroke="{a}" stroke-width="5"/>'
           f'<path d="M176 {sy + 10}l20 20" stroke="{a}" stroke-width="6" stroke-linecap="round"/>')
    out.append(pop(box, 540, sy, t + 0.4, 0.5, 0.8, 1.03))
    q = need(d, "query", "search")
    out.append(typed(220, sy + 14, q, 40, t + 0.9, tx_, 0.12, CN, 600, "start", 720))
    tq = t + 0.9 + len(q) * 0.12 + 0.3
    for k, r in enumerate(d.get("results", [])[:2]):
        title, snip = (list(r) + [""])[:2]
        ry = sy + 130 + k * 190
        parts = snip.split(q) if q in snip else [snip]
        seg, xx = [], 130
        for i, p in enumerate(parts):
            if p:
                seg.append(text(xx, ry + 120, p, 30, g, 400, "start", maxw=800))
                xx += text_w(p, 30)
            if i < len(parts) - 1:
                qw = text_w(q, 30)
                seg.append(f'<rect x="{xx - 4:.0f}" y="{ry + 88}" width="{qw + 8:.0f}" height="44" rx="8" fill="{a}" opacity="0.25"/>'
                           + text(xx, ry + 120, q, 30, a, 800, "start"))
                xx += qw
        card = (f'<rect x="90" y="{ry}" width="900" height="160" rx="26" fill="{th["panel"]}" stroke="{th["line"]}" stroke-width="2"/>'
                + text(130, ry + 62, title, 34, tx_, 800, "start", maxw=800) + "".join(seg))
        out.append(rise(card, tq + k * 0.3, 0.6, 50))
    ask = d.get("ask")
    t2 = tq + 1.2
    if ask:
        aw = min(text_w(ask[0], 32) + 70, 900)
        bub = (f'<rect x="{990 - aw:.0f}" y="{y + 920}" width="{aw:.0f}" height="90" rx="45" fill="{a}"/>'
               + text(990 - aw / 2, y + 977, ask[0], 32, th["on_accent"], 700, maxw=aw - 40))
        out.append(slide_in(bub, t2, 60, 0.5))
        if ask[1:]:
            ans = (f'<rect x="90" y="{y + 1040}" width="620" height="110" rx="26" fill="{th["panel"]}" stroke="{b2}" stroke-width="3"/>'
                   f'<path d="M130 {y + 1095}h40m-14 -14l14 14l-14 14" stroke="{b2}" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
                   + text(195, y + 1106, ask[1], 30, tx_, 700, "start", maxw=490))
            out.append(slide_in(ans, t2 + 0.9, -60, 0.5))
    t3 = t2 + 1.8
    for k, td in enumerate(d.get("todos", [])[:4]):
        ty = y + 1260 + k * 110
        box = (f'<rect x="110" y="{ty - 36}" width="56" height="56" rx="14" fill="none" stroke="{tx_}" stroke-width="4"/>'
               + text(200, ty + 6, td, 34, tx_, 500, "start", maxw=760))
        out.append(rise(box, t3 + k * 0.3, 0.5, 30))
        at = t3 + 1.4 + k * 0.5
        out.append(draw(f"M124 {ty - 8}l14 16l26 -30", at, 0.35, a, 7, glow=False))
        out.append(draw(f"M200 {ty - 6}H{min(200 + text_w(td, 34), 960):.0f}", at + 0.25, 0.4, g, 3, glow=False))
    if d.get("caption"):
        out.append(fade(text(540, y + 1760, d["caption"], 30, g), t3 + 3.6))
    return out, max(8.0, t3 - t + 4.2)


SCENES = {"receipt": receipt, "devices": devices, "fanout": fanout, "live": live, "search": search}
