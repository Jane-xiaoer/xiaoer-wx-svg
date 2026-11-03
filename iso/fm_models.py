"""小耳FM · 洗衣房旅程：用小耳FM 网站上的真 3D 洗衣机（截成帧）和真画（引擎逐帧渲出来的）做站点。

导入即注册进 models.MODELS：
  fm_washer  01 放歌：门开着唱片往里滑（循环）；点一下 → 盖层走开，下面是关门在洗的循环
  fm_done    02 洗完：门打开、六坨颜料滚出来，播一遍停在最后一帧
  fm_paint   03 一幅画随音乐长出来（帧叠加，长完停住）
gallery_block：落版前的「音乐馆」，同一首歌三种画法，各自循环生长。

帧路径相对文章输出目录（本地预览直接读；推送前换成 mmbiz 链接）。
公众号保留 <image href>、opacity 动画、begin="click"，都实测过。
"""
from isokit import appear, f, ft
from models import MODELS, label

CORAL = "#D0664E"
CORAL_D = "#BE4F39"
FRAME = "#3A332C"


def tap_cover(body, auto_at):
    """点一下揭开：被点（或到 auto_at 秒）后淡出并移走，不再挡点击。"""
    return (f'<g><animate attributeName="opacity" values="1;0" begin="click;{ft(auto_at)}s" dur="0.4s" '
            f'fill="freeze" restart="never"/><g transform="translate(0 0)">'
            f'<animateTransform attributeName="transform" type="translate" values="0 0;3000 0" '
            f'begin="click+0.45s;{ft(auto_at + 0.45)}s" dur="0.01s" fill="freeze" restart="never"/>{body}</g></g>')


def img(src, x, y, w, h):
    return (f'<image href="{src}" x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" '
            f'preserveAspectRatio="xMidYMid slice"/>')


def frames_once(frames, x, y, w, h, at, dur, fade=0.3):
    """依次亮起，后一帧盖前一帧，播完停在最后一帧。"""
    n = len(frames)
    out = []
    for i, src in enumerate(frames):
        ti = at + dur * i / max(n - 1, 1)
        out.append(f'<g opacity="0"><animate attributeName="opacity" values="0;1" begin="{ft(ti)}s" '
                   f'dur="{ft(fade)}s" fill="freeze"/>{img(src, x, y, w, h)}</g>')
    return "".join(out)


def frames_loop(frames, x, y, w, h, at, step, hold=0.0, fade=0.0, base=True):
    """循环播放：第 i 帧在 i*step 亮起，盖住前面；一轮结束（再停 hold 秒）全部收回，从第 0 帧重来。"""
    n = len(frames)
    period = n * step + hold
    out = [img(frames[0], x, y, w, h)] if base else []
    end = (n * step + hold - 0.001) / period
    for i, src in enumerate(frames[1:], 1):
        a = i * step / period
        b = min((i * step + max(fade, 0.001)) / period, end - 0.0005)
        out.append(f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0" '
                   f'keyTimes="0;{a:.4f};{b:.4f};{end:.4f};1" begin="{ft(at)}s" dur="{ft(period)}s" '
                   f'repeatCount="indefinite"/>{img(src, x, y, w, h)}</g>')
    return "".join(out)


def _box(b, w):
    """站点图片框：以底座中心为准，宽 w（屏幕像素，已抵消站点放大倍数）。"""
    cx, cy = b.iso.p(4, 4, 0)
    K = 1.25
    return cx, cy, w / K


def fm_washer(b, cover=(), wash=(), aspect=0.7875, auto=4.0, hint="点一下门 · 关上", say=""):
    cx, cy, w = _box(b, 560)
    h = w * aspect
    x, y = cx - w / 2, cy - h * 0.62
    t0 = b.t
    base = frames_loop(list(wash), x, y, w, h, t0, 0.17) if len(wash) > 1 else img(wash[0], x, y, w, h)
    b.parts.append(appear(base, t0, 0.5))
    hx, hy = cx - w * 0.08, y + h * 0.98
    pill = (f'<g transform="translate({f(hx)} {f(hy)})"><rect x="-62" y="-15" width="124" height="30" rx="15" fill="{CORAL}"/>'
            + label(hint, 0, 5, 13, "#FFFFFF", 700, "middle") +
            f'<animate attributeName="opacity" values="1;0.5;1" begin="{ft(t0)}s" dur="1.1s" repeatCount="indefinite"/></g>')
    top = frames_loop(list(cover), x, y, w, h, t0, 0.22, hold=0.9) + pill
    b.parts.append(appear(tap_cover(top, t0 + auto), t0, 0.5))
    _say(b, say, x, y, t0 + 0.8)
    b.t = t0 + auto + 2.2


def fm_done(b, frames=(), aspect=0.7875, dur=2.6, still=None, say=""):
    cx, cy, w = _box(b, 560)
    h = w * aspect
    x, y = cx - w / 2, cy - h * 0.62
    t0 = b.t
    first = img(still or frames[0], x, y, w, h)
    b.parts.append(appear(first + frames_once(list(frames), x, y, w, h, t0 + 0.5, dur, 0.18), t0, 0.5))
    _say(b, say, x, y, t0 + 0.5 + dur * 0.6)
    b.t = t0 + 0.5 + dur


def fm_frames(b, frames=(), mode="loop", step=0.18, still=None, aspect=0.7875, say="", hold=0.0, stay=3.2):
    """洗衣机帧站：loop 一直循环；once 播一遍停住（先显示 still）。"""
    cx, cy, w = _box(b, 560)
    h = w * aspect
    x, y = cx - w / 2, cy - h * 0.62
    t0 = b.t
    if mode == "once":
        body = img(still or frames[0], x, y, w, h) + frames_once(list(frames), x, y, w, h, t0 + 0.6, step * (len(frames) - 1), 0.18)
    else:
        body = frames_loop(list(frames), x, y, w, h, t0, step, hold=hold)
    b.parts.append(appear(body, t0, 0.5))
    _say(b, say, x, y, t0 + 0.7)
    b.t = t0 + stay


def fm_paint(b, frames=(), dur=7.0, name="", say=""):
    """一张画挂起来，随音乐一笔笔长出来（帧叠加，长完停住）。"""
    cx, cy, w = _box(b, 400)
    h = w * 4 / 3
    x, y = cx - w / 2, cy - h * 0.66
    t0 = b.t
    fr = (f'<rect x="{f(x - 6)}" y="{f(y - 6)}" width="{f(w + 12)}" height="{f(h + 12)}" fill="{FRAME}"/>'
          f'<rect x="{f(x + 10)}" y="{f(y + h + 10)}" width="{f(w)}" height="10" fill="#DDD3C2"/>'
          f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="#F7F2E8"/>')
    cap = label(name, cx, y + h + 44, 14, "#7C7268", 700, "middle") if name else ""
    b.parts.append(appear(fr + frames_once(list(frames), x, y, w, h, t0 + 0.4, dur) + cap, t0, 0.5))
    _say(b, say, x - 40, y - 64, t0 + 1.2)
    b.t = t0 + 2.0



# ---------------------------------------------------------------- 小耳（首页那颗戴耳机的头）+ 说话泡泡

HEAD_FRAMES = [f"head/jpg/look_{i:02d}.jpg" for i in range(16)]
CN = "PingFang SC,Noto Sans CJK SC,Microsoft YaHei,sans-serif"


def _tw(s, size):
    return sum(size if ord(c) > 0x2E7F else size * 0.56 for c in s)


def head(cx, cy, size, at, boing=True, step=0.13):
    """会左右张望的头；戳一下会 duang 一下（整组缩放，事件从图片冒泡到外层 g）。"""
    x, y = cx - size / 2, cy - size / 2
    body = frames_loop(HEAD_FRAMES, x, y, size, size, at, step, hold=0.6)
    sq = (f'<animateTransform attributeName="transform" type="scale" values="1 1;1.14 0.86;0.9 1.1;1.05 0.96;1 1" '
          f'keyTimes="0;0.2;0.45;0.7;1" begin="click" dur="0.7s"/>' if boing else "")
    inner = f'<g transform="translate({f(-cx)} {f(-cy - size * 0.3)})">{body}</g>'
    return (f'<g transform="translate({f(cx)} {f(cy + size * 0.3)})"><g>{sq}{inner}</g></g>')


def bubble(x, y, text, at, size=22, maxw=430, tail="left", fill="#FFFFFF", ink="#2E2A26"):
    """说话泡泡，左上角在 (x, y)；tail = left / down / right。逐行轻轻弹出来。"""
    from iso_journey import wrap
    lines = wrap(text, size, maxw)
    w = max(_tw(l, size) for l in lines) + 2 * 22
    h = len(lines) * size * 1.5 + 30
    if tail == "left":
        tp = f"M{f(x + 2)} {f(y + h * 0.55)} l-16 10 l16 -2Z"
    elif tail == "right":
        tp = f"M{f(x + w - 2)} {f(y + h * 0.55)} l16 10 l-16 -2Z"
    else:
        tp = f"M{f(x + 30)} {f(y + h - 2)} l-6 16 l18 -16Z"
    txt = "".join(f'<text x="{f(x + 22)}" y="{f(y + 15 + size * 1.08 + k * size * 1.5)}" fill="{ink}" font-size="{f(size)}" '
                  f'font-weight="600" font-family="{CN}">{escape_(l)}</text>' for k, l in enumerate(lines))
    shape = (f'<rect x="{f(x + 4)}" y="{f(y + 5)}" width="{f(w)}" height="{f(h)}" rx="{f(min(22, h / 2))}" fill="#DDD1BE"/>'
             f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(min(22, h / 2))}" fill="{fill}"/>'
             f'<path d="{tp}" fill="{fill}"/>')
    ox, oy = x + 20, y + h
    return (f'<g opacity="0"><animate attributeName="opacity" values="0;1" begin="{ft(at)}s" dur="0.25s" fill="freeze"/>'
            f'<g transform="translate({f(ox)} {f(oy)})"><g transform="scale(0.6)">'
            f'<animateTransform attributeName="transform" type="scale" values="0.6;1.06;1" keyTimes="0;0.6;1" '
            f'begin="{ft(at)}s" dur="0.4s" fill="freeze"/>'
            f'<g transform="translate({f(-ox)} {f(-oy)})">{shape}{txt}</g></g></g></g>'), w, h


def escape_(s):
    from html import escape
    return escape(s)


def _say(b, text, x, y, at):
    """站点上：小头像 + 泡泡，放在图片左上方。"""
    if not text:
        return
    hs = 74
    b.parts.append(appear(head(x + hs / 2 - 6, y + hs / 2 - 34, hs, at, boing=False, step=0.16), at, 0.3))
    bub, _, _ = bubble(x + hs + 8, y - 50, text, at + 0.2, size=17, maxw=300)
    b.parts.append(bub)


# ---------------------------------------------------------------- 开场：浪漫的铺垫

def prologue_block(pr, y, at, pal):
    """开场：小耳打招呼 → 大问题 → 四个「有的歌……」小画 → 「所以我做了一台洗衣机」。
    返回 (svg, 新 y, 结束时间, reveals[(t, y)])"""
    from iso_journey import T, W, slide, wrap
    out, rev = [], []
    t = at
    # 1 小耳 + 招呼
    hs = 300
    out.append(appear(head(W / 2 - 150, y + hs / 2, hs, t), t, 0.6))
    out.append(appear(f'<text x="{f(W / 2 - 150)}" y="{f(y + hs + 34)}" fill="{pal["muted"]}" font-size="16" text-anchor="middle" '
                      f'font-family="{CN}" letter-spacing="2">戳戳我</text>', t + 1.2, 0.4))
    bub, bw, bh = bubble(W / 2 + 20, y + 60, pr["hello"], t + 0.8, size=26, maxw=330)
    out.append(bub)
    y += hs + 90
    t += 2.2
    rev.append((t - 1.0, y + 420))
    # 2 大问题，一行行
    for k, (ln, size, col, wt) in enumerate(pr["question"]):
        out.append(slide(T(W / 2, y + size, ln, size, pal[col] if col in pal else col, wt, "middle"), t, dy=18, dur=0.7))
        y += size * 1.45
        t += 0.9
    y += 70
    t += 0.4
    # 3 有的歌……（画在左右交替，字在另一边）
    for k, g in enumerate(pr["glimpses"]):
        rev.append((t - 0.8, y + 460))
        pw, ph = 300, 400
        left = k % 2 == 0
        px = 96 if left else W - 96 - pw
        fr = (f'<rect x="{f(px + 8)}" y="{f(y + 10)}" width="{pw}" height="{ph}" fill="#DDD3C2"/>'
              f'<rect x="{f(px - 6)}" y="{f(y - 6)}" width="{pw + 12}" height="{ph + 12}" fill="{FRAME}"/>'
              f'<rect x="{f(px)}" y="{f(y)}" width="{pw}" height="{ph}" fill="#F7F2E8"/>'
              + frames_loop(list(g["frames"]), px, y, pw, ph, t + 0.4, 0.42, hold=2.0, fade=0.25))
        out.append(slide(fr, t, dx=-30 if left else 30, dy=0, dur=0.7))
        tx = px + pw + 56 if left else 96
        lines = wrap(g["text"], 30, W - pw - 96 - 56 - 96)
        ty = y + ph / 2 - len(lines) * 24 + 30
        for j, ln in enumerate(lines):
            out.append(slide(T(tx, ty + j * 48, ln, 30, pal["ink"], 600), t + 0.5 + j * 0.25, dy=14))
        y += ph + 90
        t += 2.4
    # 4 所以……
    rev.append((t - 0.8, y + 520))
    for k, (ln, size, col, wt) in enumerate(pr["so"]):
        out.append(slide(T(W / 2, y + size, ln, size, pal[col] if col in pal else col, wt, "middle"), t, dy=18, dur=0.7))
        y += size * 1.5
        t += 0.9
    y += 30
    hs2 = 170
    out.append(appear(head(W / 2 - 180, y + hs2 / 2, hs2, t), t, 0.5))
    bub, _, _ = bubble(W / 2 - 80, y + 20, pr["so_say"], t + 0.5, size=24, maxw=380)
    out.append(bub)
    y += hs2 + 60
    t += 1.6
    if pr.get("why"):
        rev.append((t - 0.8, y + 420))
        for ln, size, col, wt in pr["why"]:
            out.append(slide(T(W / 2, y + size, ln, size, pal[col] if col in pal else col, wt, "middle"), t, dy=18, dur=0.7))
            y += size * 1.5
            t += 0.9
        y += 20
        out.append(appear(head(W / 2 + 190, y + hs2 / 2, hs2, t), t, 0.5))
        bub, bw, _ = bubble(W / 2 - 300, y + 20, pr["why_say"], t + 0.5, size=24, maxw=380, tail="right")
        out.append(bub)
        y += hs2 + 60
        t += 2.0
    return "".join(out), y, t, rev


def gallery_block(g, y, at, pal):
    """晾画：一根根晾衣绳拉出来，画一幅幅沿绳滑进来夹住、晃一晃、慢慢显影（像洗照片晾干）。
    最后小耳出来说一句。返回 (svg, 新 y, 结束时间)。"""
    from iso_journey import MONO, W, T, appear as _ap, section_head, slide  # noqa: 延迟导入
    head_, y = section_head(y, g.get("kicker", "THE GALLERY"), g["title"], g.get("sub"), pal, CORAL, at)
    out = [head_]
    t = at + 0.7
    works = g["works"]
    per = g.get("per_line", 3)
    pw, gapx = 268, 63
    ph = pw * 4 / 3
    x0 = (W - per * pw - (per - 1) * gapx) / 2
    sag = 34
    y += 90
    for r in range(0, len(works), per):
        ry = y
        # 两根杆 + 绳子（画出来）
        poles = (f'<rect x="18" y="{f(ry - 14)}" width="10" height="{f(ph + 120)}" rx="3" fill="#B9A991"/>'
                 f'<rect x="{W - 28}" y="{f(ry - 14)}" width="10" height="{f(ph + 120)}" rx="3" fill="#B9A991"/>')
        out.append(slide(poles, t, dy=-20, dur=0.5))
        L = W
        rope = (f'<path d="M23 {f(ry)} Q{f(W / 2)} {f(ry + 2 * sag)} {f(W - 23)} {f(ry)}" fill="none" stroke="#8C7F6C" stroke-width="2.4" '
                f'stroke-dasharray="{L} {L}" stroke-dashoffset="{L}"><animate attributeName="stroke-dashoffset" values="{L};0" '
                f'begin="{ft(t + 0.2)}s" dur="0.8s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.4 0 0.2 1"/></path>')
        out.append(rope)
        t += 1.0
        for c, wk in enumerate(works[r:r + per]):
            x = x0 + c * (pw + gapx)
            tt = (x + pw / 2 - 23) / (W - 46)
            top = ry + 4 * sag * tt * (1 - tt) + 2
            px, py = x + pw / 2, top
            sheet = (f'<rect x="{f(x + 7)}" y="{f(top + 9)}" width="{pw}" height="{f(ph)}" fill="#D9CDB9"/>'
                     f'<rect x="{f(x - 6)}" y="{f(top - 4)}" width="{pw + 12}" height="{f(ph + 12)}" fill="#FBF8F2"/>'
                     f'<rect x="{f(x)}" y="{f(top + 2)}" width="{pw}" height="{f(ph)}" fill="#F3EDE2"/>'
                     + frames_loop(list(wk["frames"]), x, top + 2, pw, ph, t + 1.0, g.get("step", 0.42), hold=2.6, fade=0.3)
                     + "".join(f'<rect x="{f(x + u - 7)}" y="{f(top - 18)}" width="14" height="30" rx="3" fill="{CORAL}"/>'
                               f'<rect x="{f(x + u - 2)}" y="{f(top - 14)}" width="4" height="22" fill="{CORAL_D}"/>' for u in (34, pw - 34))
                     + T(px, top + ph + 52, wk["name"], 24, pal["ink"], 800, "middle")
                     + T(px, top + ph + 82, wk.get("note", ""), 16, pal["muted"], 500, "middle"))
            dx = -(x + pw + 40)
            sway = (f'<g><animateTransform attributeName="transform" type="rotate" values="-1 {f(px)} {f(py)};1 {f(px)} {f(py)};-1 {f(px)} {f(py)}" '
                    f'calcMode="spline" keyTimes="0;0.5;1" keySplines="0.42 0 0.58 1;0.42 0 0.58 1" begin="{ft(t + 1.6 + c * 0.3)}s" dur="{ft(3.2 + c * 0.4)}s" repeatCount="indefinite"/>'
                    f'{sheet}</g>')
            land = (f'<g><animateTransform attributeName="transform" type="rotate" values="9 {f(px)} {f(py)};-5 {f(px)} {f(py)};2 {f(px)} {f(py)};0 {f(px)} {f(py)}" '
                    f'keyTimes="0;0.35;0.7;1" begin="{ft(t)}s" dur="1.4s" fill="freeze"/>{sway}</g>')
            out.append(f'<g opacity="0" transform="translate({f(dx)} 0)">'
                       f'<animate attributeName="opacity" values="0;1" begin="{ft(t)}s" dur="0.2s" fill="freeze"/>'
                       f'<animateTransform attributeName="transform" type="translate" values="{f(dx)} 0;0 0" begin="{ft(t)}s" dur="0.75s" '
                       f'fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.2 0.7 0.3 1"/>{land}</g>')
            t += 0.55
        y += ph + 190
        t += 0.3
    t += 0.6
    if g.get("guess"):
        q, ans, ans2 = g["guess"]
        y += 50
        out.append(slide(T(W / 2, y + 10, q, 40, pal["ink"], 800, "middle"), t, dy=16))
        y += 60
        ansg = (T(W / 2, y + 70, ans, 64, CORAL, 800, "middle") + T(W / 2, y + 122, ans2, 24, pal["muted"], 500, "middle"))
        out.append(_ap(ansg, t + 0.3))
        cov = (f'<rect x="{f(W / 2 - 330)}" y="{f(y)}" width="660" height="150" rx="24" fill="#E3D8C6"/>'
               f'<rect x="{f(W / 2 - 150)}" y="{f(y + 48)}" width="300" height="56" rx="28" fill="{CORAL}"/>'
               + T(W / 2, y + 85, "点一下，看答案", 24, "#FFFFFF", 700, "middle"))
        out.append(_ap(tap_cover(cov, t + 4.0), t + 0.3))
        y += 210
        t += 4.8
    if g.get("credit"):
        out.append(_ap(T(W / 2, y - 30, g["credit"], 15, pal["muted"], 500, "middle", MONO, 0.5), t))
    if g.get("outro_say"):
        hs = 220
        y += 40
        out.append(_ap(head(W / 2 - 170, y + hs / 2, hs, t + 0.4), t + 0.4, 0.5))
        bub, _, _ = bubble(W / 2 - 40, y + 30, g["outro_say"], t + 1.0, size=26, maxw=380)
        out.append(bub)
        y += hs + 20
        t += 1.6
    return "".join(out), y, t

MODELS.update({"fm_frames": fm_frames, "fm_washer": fm_washer, "fm_done": fm_done, "fm_paint": fm_paint})
