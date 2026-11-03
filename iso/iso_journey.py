#!/usr/bin/env python3
"""等轴测旅程（3D 版）：一条 Z 字公路从上往下串起 N 个 2.5D 小场景，往下拉就把故事走完。

每到一站：底座侧滑进来 → 零件一块块掉下来拼好 → 信息卡滑出 → 公路往下一站画出去，
一个光点沿路跑过去，到了下一站再拼下一个。全程纯 SVG 动画，没有位图、没有 JS。

用法：
  python3 iso/iso_journey.py 分镜.json [--grow] [--speed 0.9] [--push] [--update MEDIA_ID] [-o 输出目录]
  --grow   页面跟着故事一屏屏长出来（默认整张长图一开始就在，读者往下拉看到正在拼的那一站）
分镜写法见 templates/storyboards/等轴测-*.json 和 iso/README.md。
"""
import argparse
import json
import math
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT), str(ROOT / "motion")]
import wxsvg  # noqa: E402
from isokit import C, EASE, Iso, appear, f, ft, shade  # noqa: E402
from models import MODELS, Builder  # noqa: E402
import fm_models  # noqa: E402,F401  序章 / 晾衣绳画廊 / 帧序列站点（小耳FM 洗衣房模板）

W = 1080
CN = "PingFang SC,Noto Sans CJK SC,Microsoft YaHei,sans-serif"
MONO = "SFMono-Regular,Menlo,Consolas,monospace"

PALETTES = {
    "paper": dict(bg="#F5F1E8", ink="#25343A", muted="#7C8782", rule="#D8D6CC", road="#E3DDCE", curb="#C9C1AE",
                  dash="#FFFDF6", card="#FFFFFF", cardline="#E1DDD2", shadow="#E6E0D2", plinth="#ECE5D6",
                  plinth_top="#F8F4EB", leaf="#7FA36A", trunk="#8A6A4A", paver="#E9E2D2", metal="#C9CED1",
                  screen="#22313A", dark="#3A4650", wood="#C59A6A", pillar="#D9D2C3", mug="#D9452B", red="#D9452B",
                  kinds=["#2F6D6A", "#4B8EA0", "#8A9A5B", "#B07D3E", "#C4553D", "#6D5D9A", "#3F7FB8", "#9A6B4F"]),
    "fm": dict(bg="#ECE4D5", ink="#2E2A26", muted="#8A7F73", rule="#D8CCB9", road="#E2D7C4", curb="#D3C6B1",
               dash="#F7F2E8", card="#FBF7F0", cardline="#E0D5C3", shadow="#DFD3C0", plinth="#E6DCCB",
               plinth_top="#F3EDE2", leaf="#A9B48F", trunk="#8A6A4A", paver="#E9E0D0", metal="#D8D0C2",
               screen="#47413A", dark="#3A332C", wood="#C9A27A", pillar="#DCD1BF", mug="#D0664E", red="#D0664E",
               kinds=["#D0664E", "#BE4F39", "#C9785F", "#A8573F", "#D0664E", "#BE4F39", "#C9785F", "#A8573F"]),
    "night": dict(bg="#141A1F", ink="#E9EEF0", muted="#8A979E", rule="#2C3740", road="#26313A", curb="#1B242B",
                  dash="#5B6B76", card="#1D262D", cardline="#2F3B44", shadow="#0E1317", plinth="#2A353E",
                  plinth_top="#34414B", leaf="#5E8C6A", trunk="#6B5440", paver="#3B4852", metal="#8D99A3",
                  screen="#0B1014", dark="#2B343C", wood="#8C6B4C", pillar="#4A5761", mug="#E0533D", red="#E0533D",
                  kinds=["#4FC3B0", "#6BA8F0", "#B5C46A", "#E0A64F", "#E86A50", "#A68BE8", "#5FB0E8", "#D9A07A"]),
}

HEAD = 520      # 抬头高度
GAP = 560       # 相邻两站的竖直距离
LX, RX = 270, 810  # 底座中心 x（左站 / 右站）
ROAD_W = 40
K = 1.25        # 小场景放大倍数


def cw(ch, size):
    return size if ord(ch) > 0x2E7F else size * 0.56


NO_HEAD = "，。、：；！？）」』”’,.;:!?)%"


def wrap(s, size, maxw):
    """按词换行：英文单词、数字、型号（Qwen3.5-9B、14.1、4K）不拆开；标点不进行首。"""
    import re
    toks = re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-+_/:@']*|\n|\s|.", s)
    lines, cur, w = [], "", 0
    for tk in toks:
        tw = sum(cw(c, size) for c in tk)
        if tk == "\n":
            lines.append(cur)
            cur, w = "", 0
            continue
        if tk in NO_HEAD and cur:  # 标点挤进上一行
            cur += tk
            w += tw
            continue
        if w + tw > maxw and cur:
            lines.append(cur.rstrip())
            cur, w = ("", 0) if tk.isspace() else (tk, tw)
            continue
        if tw > maxw:  # 超长单词：只好按字拆
            for c in tk:
                if w + cw(c, size) > maxw and cur:
                    lines.append(cur)
                    cur, w = "", 0
                cur += c
                w += cw(c, size)
            continue
        cur += tk
        w += tw
    if cur.strip():
        lines.append(cur.rstrip())
    return lines


def T(x, y, s, size, color, weight=400, anchor="start", font=CN, spacing=0):
    sp = f' letter-spacing="{f(spacing)}"' if spacing else ""
    return (f'<text x="{f(x)}" y="{f(y)}" fill="{color}" font-size="{f(size)}" font-weight="{weight}" '
            f'text-anchor="{anchor}" font-family="{font}"{sp}>{escape(s)}</text>')


def slide(body, at, dx=0, dy=24, dur=0.6):
    return (f'<g opacity="0" transform="translate({f(dx)} {f(dy)})">'
            f'<animate attributeName="opacity" values="0;1" begin="{ft(at)}s" dur="0.4s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" values="{f(dx)} {f(dy)};0 0" '
            f'begin="{ft(at)}s" dur="{ft(dur)}s" fill="freeze" {EASE}/>{body}</g>')


# ---------------------------------------------------------------- 公路

def legs(a, b):
    """a→b 的等轴测折线：沿地面两个方向走 X / Y / X（或 Y / X / Y），返回拐点列表。"""
    (x0, y0), (x1, y1) = a, b
    dx, dy = x1 - x0, y1 - y0
    # 主方向走两段，副方向走一段：主*2 - 副 = |dx|/C，主*2 + 副 = 2dy
    main2 = dy + abs(dx) / (2 * C)
    side = dy - abs(dx) / (2 * C)
    if side < 2:  # 刚好在一条等轴测斜线上（或太扁）：直接一段
        return [a, b]
    m = main2 / 2
    sx = 1 if dx > 0 else -1
    p1 = (x0 + sx * m * C, y0 + m * 0.5)
    p2 = (p1[0] - sx * side * C, p1[1] + side * 0.5)
    return [a, p1, p2, b]


def plen(ps):
    return sum(math.dist(ps[i], ps[i + 1]) for i in range(len(ps) - 1))


def road_leg(ps, at, dur, pal):
    """一段公路：路肩 + 路面用 dashoffset 画出来，中线虚线一截截亮。"""
    L = plen(ps)
    d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in ps)
    dc = "M" + " L".join(f"{f(x)} {f(y + 7)}" for x, y in ps)

    def draw(dd, color, w):
        return (f'<path d="{dd}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linejoin="round" '
                f'stroke-dasharray="{f(L + 2)} {f(L + 2)}" stroke-dashoffset="{f(L + 2)}">'
                f'<animate attributeName="stroke-dashoffset" values="{f(L + 2)};0" begin="{ft(at)}s" dur="{ft(dur)}s" fill="freeze"/></path>')

    out = [draw(dc, pal["curb"], ROAD_W), draw(d, pal["road"], ROAD_W)]
    # 中线：每 30px 一截，按距离依次亮起
    acc = 0
    for i in range(len(ps) - 1):
        (xa, ya), (xb, yb) = ps[i], ps[i + 1]
        seg = math.dist(ps[i], ps[i + 1])
        ux, uy = (xb - xa) / seg, (yb - ya) / seg
        s = 18
        while s + 12 < seg - 10:
            x1, y1 = xa + ux * s, ya + uy * s
            x2, y2 = xa + ux * (s + 12), ya + uy * (s + 12)
            t = at + dur * (acc + s) / L
            out.append(f'<path d="M{f(x1)} {f(y1)} L{f(x2)} {f(y2)}" stroke="{pal["dash"]}" stroke-width="2.5" opacity="0">'
                       f'<animate attributeName="opacity" values="0;1" begin="{ft(t)}s" dur="0.12s" fill="freeze"/></path>')
            s += 30
        acc += seg
    return "".join(out), L


def packet_motion(route, pal, accent):
    """光点：沿整条路跑，到站停下。route = [(t, x, y), ...] 按时间排好。"""
    t0, t1 = route[0][0], route[-1][0]
    dur = t1 - t0
    kt = ";".join(ft((t - t0) / dur) for t, _, _ in route)
    vals = ";".join(f"{f(x)} {f(y)}" for _, x, y in route)
    dot = (f'<path d="M0 -14 L12 -7 L12 4 L0 11 L-12 4 L-12 -7Z" fill="{accent}"/>'
           f'<path d="M0 -14 L12 -7 L0 0 L-12 -7Z" fill="{shade(accent, 1.4)}"/>'
           f'<path d="M0 0 L0 11 L12 4 L12 -7Z" fill="{shade(accent, 0.75)}"/>')
    halo = (f'<g transform="matrix(1 0 0 0.5 0 6)"><circle r="22" fill="none" stroke="{accent}" stroke-width="3">'
            f'<animate attributeName="opacity" values="0.9;0.1;0.9" begin="{ft(t0)}s" dur="1.2s" repeatCount="indefinite"/></circle></g>')
    return (f'<g opacity="0" transform="translate({f(route[0][1])} {f(route[0][2])})">'
            f'<animate attributeName="opacity" values="0;1" begin="{ft(t0)}s" dur="0.3s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" values="{vals}" keyTimes="{kt}" '
            f'begin="{ft(t0)}s" dur="{ft(dur)}s" fill="freeze"/>{halo}<g transform="translate(0 -12)">{dot}</g></g>')


# ---------------------------------------------------------------- 卡片

def card(x, y, w, stop, idx, color, pal, at):
    pad = 30
    body_lines = wrap(stop.get("body", ""), 22, w - 2 * pad)
    # 参数行：[["配置", "..."], ["模型", "..."], ["干活", "..."]]
    LW = 64
    specs = [(k, wrap(v, 19, w - 2 * pad - LW)) for k, v in stop.get("specs", [])]
    spec_h = (sum(len(v) * 29 + 12 for _, v in specs) + 22) if specs else 0
    h = 160 + len(body_lines) * 38 + spec_h + (58 if stop.get("en") else 16)
    head = f'{idx:02d} · {stop.get("kind", "")}'
    parts = [f'<rect x="{f(x + 8)}" y="{f(y + 10)}" width="{f(w)}" height="{f(h)}" rx="6" fill="{pal["shadow"]}"/>',
             f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="6" fill="{pal["card"]}" stroke="{pal["cardline"]}" stroke-width="1.5"/>',
             f'<rect x="{f(x)}" y="{f(y)}" width="6" height="{f(h)}" rx="3" fill="{color}"/>']
    inner = [T(x + pad, y + 44, head, 16, color, 700, font=MONO, spacing=1.5),
             T(x + pad, y + 92, stop["title"], 36, pal["ink"], 800)]
    if stop.get("place"):
        inner.append(T(x + pad, y + 126, stop["place"], 18, pal["muted"], 500))
    inner.append(f'<rect x="{f(x + pad)}" y="{f(y + 142)}" width="34" height="4" fill="{pal["red"]}"/>')
    for k, ln in enumerate(body_lines):
        inner.append(T(x + pad, y + 186 + k * 38, ln, 22, pal["ink"], 400))
    if specs:
        sy = y + 174 + len(body_lines) * 38
        inner.append(f'<path d="M{f(x + pad)} {f(sy)} H{f(x + w - pad)}" stroke="{pal["cardline"]}" stroke-width="1.5" stroke-dasharray="6 6"/>')
        sy += 38
        for k, (lab, vals) in enumerate(specs):
            row = T(x + pad, sy, lab, 14, color, 700, font=MONO, spacing=1)
            row += "".join(T(x + pad + LW, sy + j * 29, v, 19, pal["ink"], 400) for j, v in enumerate(vals))
            inner.append(row)
            sy += len(vals) * 29 + 12
    if stop.get("en"):
        inner.append(T(x + pad, y + h - 22, stop["en"], 13, pal["muted"], 600, font=MONO, spacing=2))
    sx = -28 if x > W / 2 else 28
    out = slide("".join(parts), at, dx=sx, dy=0, dur=0.6)
    out += "".join(appear(e, at + 0.25 + k * 0.08, 0.35) for k, e in enumerate(inner))
    return out, h


# ---------------------------------------------------------------- 组装

def build(sb, grow=False, lead=0.6):
    pal = dict(PALETTES[sb.get("palette", "paper")])
    stops = sb["stops"]
    kinds = []
    for s in stops:
        if s.get("kind") and s["kind"] not in kinds:
            kinds.append(s["kind"])
    kcol = {k: pal["kinds"][i % len(pal["kinds"])] for i, k in enumerate(kinds)}

    n = len(stops)
    CW = 440
    card_h = [card(0, 0, CW, s, i + 1, "#000000", pal, 0)[1] for i, s in enumerate(stops)]
    nodes = []  # 每站底座地面中心（公路节点）；卡片长了站距跟着拉开
    pro = None
    PRO_Y = HEAD - 30
    if sb.get("prologue"):
        pro = fm_models.prologue_block(sb["prologue"], PRO_Y, 1.4, pal)
    off = (pro[1] - PRO_Y + 60) if pro else 0
    cy = HEAD + 300 + off
    for i in range(n):
        cx = LX if i % 2 == 0 else RX
        if i:
            cy += max(GAP, card_h[i - 1] + 40)
        nodes.append((cx, cy))
    end_y = nodes[-1][1] + max(GAP, card_h[-1] + 80)
    H = end_y + 900  # 先估，落版排完再收

    back, mid, front, reveals = [], [], [], []
    accent0 = pal["kinds"][0]

    # ---- 抬头
    t = 0.3
    hd = [T(72, 92, sb.get("kicker", ""), 18, accent0, 600, font=MONO, spacing=2.4),
          T(72, 186, sb["headline"], 66, pal["ink"], 800),
          T(74, 250, sb.get("subtitle", ""), 32, accent0, 600)]
    for k, ln in enumerate(wrap(sb.get("intro", ""), 25, 820)):
        hd.append(T(74, 306 + k * 38, ln, 25, pal["muted"], 400))
    for k, e in enumerate(hd):
        front.append(slide(e, t + k * 0.12, dy=18))
    show_legend = sb.get("legend", True)
    if show_legend:
        front.append(appear(T(1008, 156, f"{n:02d}", 104, shade(accent0, 1.75) if sb.get("palette", "paper") == "paper" else pal["rule"], 800, "end", MONO), 0.6, 0.6))
        front.append(appear(T(1008, 198, "STOPS", 16, accent0, 600, "end", MONO, 2), 0.8))
    ry = 370 + 38 * max(0, len(wrap(sb.get("intro", ""), 25, 820)) - 1)
    front.append(f'<path d="M72 {f(ry)} H1008" stroke="{pal["rule"]}" stroke-width="1.5" stroke-dasharray="936" stroke-dashoffset="936">'
                 f'<animate attributeName="stroke-dashoffset" values="936;0" begin="0.7s" dur="0.9s" fill="freeze" {EASE}/></path>')
    lx = 74
    for k, kd in enumerate(kinds if show_legend else []):
        g = f'<circle cx="{f(lx)}" cy="{f(ry + 40)}" r="6" fill="{kcol[kd]}"/>' + T(lx + 14, ry + 47, kd, 19, pal["muted"], 500)
        front.append(appear(g, 1.0 + k * 0.1))
        lx += 40 + sum(cw(c, 19) for c in kd) + 24

    if pro:
        front.append(pro[0])
        if grow:
            reveals.extend((round(max(0.0, tt), 3), yy) for tt, yy in pro[3])
    # ---- 起点
    t_road = pro[2] if pro else 1.4
    start = (nodes[0][0] + 330, nodes[0][1] - 330 * 0.5 / C)
    seg, L = road_leg([start, nodes[0]], t_road, 0.9, pal)
    back.append(seg)
    pill = (f'<rect x="{f(start[0] - 52)}" y="{f(start[1] - 50)}" width="104" height="34" rx="17" fill="{accent0}"/>'
            + T(start[0], start[1] - 27, sb.get("start_label", "START"), 15, "#FFFFFF", 700, "middle", MONO, 2))
    front.append(slide(pill, t_road - 0.2, dy=-14))
    route = [(t_road, *start), (t_road + 0.9, *nodes[0])]

    # ---- 各站
    t_stop = t_road + 0.75
    times = []
    for i, s in enumerate(stops):
        color = kcol.get(s.get("kind"), accent0)
        cx, cy = nodes[i]
        iso = Iso(cx, cy - 4 * 26)  # 底座后角在节点正上方 104px
        b = Builder(iso, t_stop, pal, color)
        b.no = i + 1
        MODELS[s["model"]](b, **s.get("args", {}))
        mid.append(f'<g transform="translate({f(cx)} {f(cy)}) scale({K}) translate({f(-cx)} {f(-cy)})">{b.svg()}</g>')
        # 卡片在对面
        cw_ = CW
        cxk = 590 if cx < W / 2 else 50
        cyk = cy - 200
        ctext, ch = card(cxk, cyk, cw_, s, i + 1, color, pal, t_stop + 0.6)
        front.append(ctext)
        times.append(t_stop)
        if grow:
            reveals.append((round(max(0.0, t_stop - lead), 3), min(H, cy + 420)))
        # 去下一站（或终点）的路
        t_leave = max(b.t, t_stop + 1.6)
        nxt = nodes[i + 1] if i + 1 < n else (W / 2, end_y)
        ps = legs(nodes[i], nxt)
        seg, L = road_leg(ps, t_leave - 0.2, 0.25 + L_time(plen(ps)), pal)
        back.append(seg)
        travel = 0.35 + L_time(plen(ps))
        # 光点路线：先在本站停，再沿拐点走
        route.append((t_leave, *nodes[i]))
        acc = 0
        Lp = plen(ps)
        for j in range(1, len(ps)):
            acc += math.dist(ps[j - 1], ps[j])
            route.append((t_leave + travel * acc / Lp, *ps[j]))
        t_stop = t_leave + travel - 0.15

    # ---- 终点
    t_end = t_stop
    ex, ey = W / 2, end_y
    end_pill = (f'<rect x="{f(ex - 60)}" y="{f(ey - 17)}" width="120" height="34" rx="17" fill="{pal["ink"]}"/>'
                + T(ex, ey + 6, sb.get("end_label", "FINISH"), 15, pal["bg"], 700, "middle", MONO, 2))
    front.append(slide(end_pill, t_end, dy=-10))
    end = sb.get("end", {})
    ty = ey + 130
    t_gal = t_end
    if sb.get("gallery"):
        part, ty, t_gal = fm_models.gallery_block(sb["gallery"], ey + 110, t_end + 0.4, pal)
        front.append(part)
        if grow:
            reveals.append((round(max(0.0, t_end - lead), 3), int(ty + 200)))
        ty += 90
    fe = []
    if end.get("title"):
        for k, ln in enumerate(wrap(end["title"], 52, 900)):
            fe.append(T(W / 2, ty + k * 66, ln, 52, pal["ink"], 800, "middle"))
        ty += 66 * len(wrap(end["title"], 52, 900)) + 10
    for k, ln in enumerate(end.get("lines", [])):
        fe.append(T(W / 2, ty + 20 + k * 44, ln, 25, pal["muted"], 400, "middle"))
    ty += 20 + 44 * len(end.get("lines", []))
    if end.get("url"):
        # 大网址，中间一段用强调色，下面一条强调色短线
        pre, mid_, post = end["url"]
        tw = sum(cw(c, 64) for c in pre + mid_ + post)
        fe.append(f'<text x="{f(W / 2)}" y="{f(ty + 70)}" font-size="64" font-weight="800" text-anchor="middle" font-family="{MONO}" '
                  f'fill="{pal["ink"]}" letter-spacing="1">{escape(pre)}<tspan fill="{pal["red"]}">{escape(mid_)}</tspan>{escape(post)}</text>')
        fe.append(f'<rect x="{f(W / 2 - 60)}" y="{f(ty + 100)}" width="120" height="6" rx="3" fill="{pal["red"]}"/>')
        ty += 130
    for k, e in enumerate(fe):
        front.append(slide(e, t_gal + 0.4 + k * 0.15, dy=20))
    t_out = t_gal + 0.6 + 0.15 * len(fe)
    if sb.get("advice"):
        part, ty, t_out = advice_block(sb["advice"], ty + 110, t_out, pal, kcol, accent0)
        front.append(part)
        if grow:
            reveals.append((round(max(0.0, t_out - 2.0), 3), ty))
    if sb.get("tools"):
        part, ty, t_out = tools_block(sb["tools"], ty + 110, t_out, pal, accent0)
        front.append(part)
    tl_tail = []
    for k, ln in enumerate(sb.get("tail", [])):
        tl_tail.append(slide(T(W / 2, ty + 80 + k * 30, ln, 16, pal["muted"], 600, "middle", MONO, 1.5), t_out + k * 0.15, dy=14))
    front.extend(tl_tail)
    H = int(ty + 80 + 30 * len(sb.get("tail", [])) + 110)
    if grow:
        if sb.get("advice") or sb.get("tools"):
            reveals.append((round(max(0.0, t_end - lead), 3), min(H, int(end_y + 600))))
        reveals.append((round(max(0.0, t_out - 1.5), 3), H))
        reveals.sort()
    route.append((t_end + 0.3, ex, ey))

    packet = packet_motion(route, pal, accent0)
    body = "".join(back) + packet + "".join(mid) + "".join(front)
    spec = {"width": W, "height": H, "background": pal["bg"],
            "elements": [{"type": "raw", "svg": body}]}
    if grow:
        first = min(H, (PRO_Y + 700) if pro else nodes[0][1] + 420)
        spec["first_screen"] = first
        # wxsvg 的空画布宽度按「目标高 / 首屏高」算
        spec["reveals"] = [[t, y] for t, y in reveals if y > first]
    else:
        spec["first_screen"] = H
    long_svg, article = wxsvg.build(spec)
    article += appendix_html(sb)
    tl = {"stops": [{"title": s["title"], "start": round(t, 2), "y": nodes[i][1]} for i, (s, t) in enumerate(zip(stops, times))],
          "finish": round(t_end + 2.5, 2), "height": H}
    return long_svg, article, tl


def section_head(y, kicker, title, sub, pal, accent, at):
    out = [slide(T(72, y, kicker, 16, accent, 700, font=MONO, spacing=2.4), at, dy=14),
           slide(T(72, y + 62, title, 46, pal["ink"], 800), at + 0.12, dy=16)]
    h = 62
    for k, ln in enumerate(wrap(sub or "", 23, 930)):
        out.append(slide(T(72, y + 108 + k * 34, ln, 23, pal["muted"], 400), at + 0.24 + k * 0.08, dy=14))
        h = 108 + k * 34
    out.append(f'<path d="M72 {f(y + h + 34)} H1008" stroke="{pal["rule"]}" stroke-width="1.5" stroke-dasharray="936" stroke-dashoffset="936">'
               f'<animate attributeName="stroke-dashoffset" values="936;0" begin="{ft(at + 0.3)}s" dur="0.8s" fill="freeze" {EASE}/></path>')
    return "".join(out), y + h + 34


def advice_block(adv, y, at, pal, kcol, accent):
    """建议：大号序号 + 一句结论 + 一两行为什么。items = [["结论", "为什么"], ...]"""
    head, y = section_head(y, adv.get("kicker", "ADVICE"), adv["title"], adv.get("sub"), pal, accent, at)
    out = [head]
    t = at + 0.7
    y += 30
    for k, (title, why) in enumerate(adv["items"]):
        col = pal["kinds"][k % len(pal["kinds"])]
        lines = wrap(why, 21, 800)
        h = 74 + len(lines) * 32 + 26
        g = (f'<rect x="72" y="{f(y)}" width="936" height="{f(h)}" rx="6" fill="{pal["card"]}" stroke="{pal["cardline"]}" stroke-width="1.5"/>'
             + T(104, y + 60, f"{k + 1:02d}", 40, shade(col, 1.0), 800, font=MONO)
             + T(190, y + 50, title, 27, pal["ink"], 800)
             + "".join(T(190, y + 88 + j * 32, ln, 21, pal["muted"], 400) for j, ln in enumerate(lines)))
        out.append(slide(g, t, dx=0, dy=26))
        t += 0.35
        y += h + 18
    return "".join(out), y, t


def tools_block(tools, y, at, pal, accent):
    """拿去用的工具：两列小卡，名字（等宽）+ 标签（星数 / 类型）+ 一两行说明。"""
    head, y = section_head(y, tools.get("kicker", "TOOLS"), tools["title"], tools.get("sub"), pal, accent, at)
    out = [head]
    t = at + 0.7
    y += 30
    colw, gap = 459, 18
    items = tools["items"]
    for r in range(0, len(items), 2):
        row = items[r:r + 2]
        hs = [118 + len(wrap(it["desc"], 19, colw - 56)) * 28 for it in row]
        h = max(hs)
        for c, it in enumerate(row):
            x = 72 + c * (colw + gap)
            col = pal["kinds"][(r + c) % len(pal["kinds"])]
            lines = wrap(it["desc"], 19, colw - 56)
            name = it["name"]
            nsize = 21 if len(name) <= 26 else 18
            g = (f'<rect x="{f(x)}" y="{f(y)}" width="{colw}" height="{f(h)}" rx="6" fill="{pal["card"]}" stroke="{pal["cardline"]}" stroke-width="1.5"/>'
                 f'<rect x="{f(x)}" y="{f(y)}" width="{colw}" height="5" rx="2" fill="{col}"/>'
                 + T(x + 28, y + 46, name, nsize, pal["ink"], 800, font=MONO)
                 + (T(x + colw - 26, y + 80, it["tag"], 15, col, 700, "end", MONO, 1) if it.get("tag") else "")
                 + (T(x + 28, y + 80, it["kind"], 15, pal["muted"], 600) if it.get("kind") else "")
                 + "".join(T(x + 28, y + 114 + j * 28, ln, 19, pal["ink"], 400) for j, ln in enumerate(lines)))
            out.append(slide(g, t, dy=24))
            t += 0.18
        y += h + gap
    if tools.get("footnote"):
        for k, ln in enumerate(wrap(tools["footnote"], 19, 930)):
            out.append(appear(T(72, y + 30 + k * 28, ln, 19, pal["muted"], 400), t + 0.2))
        y += 30 + 28 * len(wrap(tools["footnote"], 19, 930))
    return "".join(out), y, t + 0.3


def appendix_html(sb):
    """SVG 里的字复制不了：正文末尾再放一份能复制的纯文字清单（仓库名、建议）。"""
    tools = sb.get("tools")
    if not tools:
        return ""
    p = 'style="margin:0 0 10px;font-size:15px;line-height:1.75;color:#3d4a50;"'
    rows = [f'<p style="margin:28px 0 12px;font-size:17px;font-weight:700;color:#25343A;">{escape(tools.get("appendix_title", "文中工具清单（可复制）"))}</p>']
    for it in tools["items"]:
        link = it.get("repo", "")
        rows.append(f'<p {p}><strong>{escape(it["name"])}</strong>{"　" + escape(link) if link else ""}<br/>{escape(it["desc"])}</p>')
    return f'<section style="padding:8px 16px 24px;">{"".join(rows)}</section>'


def L_time(px):
    """公路画多快：每秒约 900px，最少 0.6 秒。"""
    return max(0.6, px / 900)


def scale_times(html, k):
    """整体时间轴乘 k：begin 里的秒数（含 click;Ns）和 dur 都乘，keyTimes 是比例不动。"""
    import re
    num = lambda m: f"{float(m.group(1)) * k:.3f}".rstrip("0").rstrip(".") + "s"  # noqa: E731
    html = re.sub(r'(begin=")([^"]+)(")', lambda m: m.group(1) + re.sub(r"([0-9]*\.?[0-9]+)s", num, m.group(2)) + m.group(3), html)
    return re.sub(r'dur="([0-9]*\.?[0-9]+)s"', lambda m: 'dur="' + num(m) + '"', html)


def cover(long_svg, t, y_center, out_path, base=None):
    """封面 900×383：1080 宽下跳到 t 秒，截以 y_center 为中心的一条横带（中间截图放系统临时目录）。"""
    import asyncio
    import tempfile
    from playwright.async_api import async_playwright
    from PIL import Image
    band_h = 1080 * 383 / 900
    png = Path(tempfile.mkdtemp()) / "cover.png"

    async def go():
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await b.new_page(viewport={"width": 1080, "height": 1200}, device_scale_factor=1)
            if base:  # 有相对路径图片：临时页放系统临时目录，<base> 指回分镜所在目录
                tmp = png.parent / "cover.html"
                tmp.write_text(f'<!doctype html><base href="{Path(base).resolve().as_uri()}/">'
                               f'<body style="margin:0;width:1080px">{long_svg}</body>', encoding="utf-8")
                await pg.goto(tmp.as_uri())
                await pg.wait_for_load_state("load")
            else:
                await pg.set_content(f'<!doctype html><body style="margin:0;width:1080px">{long_svg}</body>')
            await pg.evaluate(f"document.querySelectorAll('svg').forEach(s=>{{s.pauseAnimations();s.setCurrentTime({t})}})")
            await pg.wait_for_timeout(200)
            await pg.screenshot(path=str(png), full_page=True,
                                clip={"x": 0, "y": max(0, y_center - band_h / 2), "width": 1080, "height": band_h})
            await b.close()
    asyncio.run(go())
    Image.open(png).convert("RGB").resize((900, 383), Image.LANCZOS).save(out_path, quality=92)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard")
    ap.add_argument("-o", "--out")
    ap.add_argument("--grow", action="store_true", help="页面一屏屏长出来")
    ap.add_argument("--speed", type=float, default=1.0, help="整体时间乘数，0.85 = 快 15%%")
    ap.add_argument("--push", action="store_true", help="推到公众号草稿箱（不发布）")
    ap.add_argument("--update", help="更新已有草稿 media_id")
    a = ap.parse_args()
    sbp = Path(a.storyboard)
    sb = json.loads(sbp.read_text(encoding="utf-8"))
    long_svg, article, tl = build(sb, grow=a.grow)
    if sb.get("assets"):  # 图片放在分镜旁边的子文件夹里：相对路径统一加前缀
        import re
        pre = sb["assets"].rstrip("/") + "/"
        fix = lambda h: re.sub(r'href="(?!https?:|data:|#|/)([^"]+\.(?:jpg|jpeg|png|gif))"', lambda m: f'href="{pre}{m.group(1)}"', h)
        long_svg, article = fix(long_svg), fix(article)
    if a.speed != 1.0:
        long_svg, article = scale_times(long_svg, a.speed), scale_times(article, a.speed)
        for s in tl["stops"]:
            s["start"] = round(s["start"] * a.speed, 2)
        tl["finish"] = round(tl["finish"] * a.speed, 2)
    out = (Path(a.out) if a.out else Path.cwd() / "out" / sbp.stem).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "long.svg").write_text(long_svg, encoding="utf-8")
    (out / "article.html").write_text(article, encoding="utf-8")
    title = sb.get("title", sb["headline"])
    prev = wxsvg.PREVIEW.format(title=escape(title), article=article.replace("</template", "<\\/template"))
    if sbp.parent.resolve() != out:  # 图片路径相对分镜目录写的：预览页指回那里
        prev = prev.replace("<head>", f'<head><base href="{sbp.parent.resolve().as_uri()}/">', 1)
    (out / "preview.html").write_text(prev, encoding="utf-8")
    # 封面：第 2 站拼好时截一条
    k = min(1, len(tl["stops"]) - 1)
    cy = tl["stops"][k].get("y", HEAD + 300 + k * GAP)
    try:
        cover(long_svg, tl["stops"][k]["start"] + 2.6 * a.speed, cy - 40, out / "cover.jpg", base=sbp.parent)
    except Exception as e:  # 常见：没跑 python3 -m playwright install chromium
        print(f"⚠️ 封面没出成（{str(e).splitlines()[0][:80]}）。文章照常生成；要封面先跑 python3 -m playwright install chromium")
    kb = len(article.encode()) / 1024
    tl["article_kb"] = round(kb, 1)
    (out / "timeline.json").write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ {out}  {len(tl['stops'])} 站 · {tl['finish']:.1f}s · 高 {tl['height']} · {kb:.0f}KB")
    for s in tl["stops"]:
        print(f"  {s['start']:6.2f}s  {s['title']}")
    if kb > 1000:
        print("⚠️ 超过 1MB，公众号可能吃不下")
    if a.push or a.update:
        import wechat
        import re
        # 正文里的本地图（href="xx/yy.jpg"）→ 先传 mmbiz 再换链接，缓存在作品目录 mmbiz.json
        rel = sorted(set(re.findall(r'href="(?!https?:|data:|#)([^"]+\.(?:jpg|jpeg|png|gif))"', article)))
        if rel:
            base = sbp.parent.resolve()
            cache_p = out / "mmbiz.json"
            cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
            tok = wechat.token()
            for n in rel:
                key = f"{n}:{(base / n).stat().st_mtime_ns}"
                if key not in cache:
                    cache[key] = wechat.upload_image(tok, base / n)
                    print("上传", n, flush=True)
                    cache_p.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
                article = article.replace(f'href="{n}"', f'href="{cache[key]}"')
            (out / "article.mmbiz.html").write_text(article, encoding="utf-8")
            print(f"图片 {len(rel)} 张已换成 mmbiz")
        mid = wechat.save_draft(article, title, str(out / "cover.jpg"), sb.get("author", ""),
                                sb.get("digest", ""), update=a.update)
        (out / "media_id.txt").write_text(mid, encoding="utf-8")
        print("草稿 media_id:", mid)
        for tg, lo, re_ in wechat.check(mid, article):
            print(f"  {tg:<17} 本地 {lo:5d}  草稿 {re_:5d}{'' if lo == re_ else '  ⚠️'}")


if __name__ == "__main__":
    main()
