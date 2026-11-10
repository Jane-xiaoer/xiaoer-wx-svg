"""《小耳和阿卡》公众号 SVG · 往下掉的一天（方向 A+B）

    .venv/bin/python build.py            → out/long.svg、out/article.html、out/preview.html
    .venv/bin/python build.py --push     → 图片传 mmbiz、视频上传、推草稿（不发布）

公众号规矩：没有 id / fill-opacity 动画 / xlink:href / mask / clipPath / 滤镜 / 渐变 / style / JS。
动画按打开文章的时间走：开场（床、扎头发、插叶子）一次性演，其余每段都一直循环，读者什么时候滑到都是活的。
"失重"靠竖向空间编排：同一个人沿 S 线铺几个姿态，每个姿态 3 帧翻页（大衣、头发在风里抖）+ 原地慢转 + 上下浮 + 残影 + 速度线。
"""
import sys, json, math, argparse
from pathlib import Path
from PIL import Image
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(Path.home() / "projects/xiaoer-wx-svg-timeline/iso")]
from textpath import TextPath  # noqa: E402

TP = TextPath({"kai": str(Path.home() / "Library/Fonts/LXGWWenKai-Regular.ttf"),
               "song": str(HERE / "work/Songti_SC_Bold.ttf"),
               "light": str(HERE / "work/Songti_SC_Light.ttf")})

W = 750
PAPER, INK, NIGHT = "#F4F1EA", "#1C1E1C", "#191C1A"
GREY, RUST, AKA, RED, GOLD = "#8C877D", "#9A3B2A", "#6E9A5B", "#C8372D", "#C9A24A"
NIGHT_LINE, NIGHT_TXT = "#5E625C", "#D9D3C6"
URL = "luyinka.xiaoeromia.com"
E = 'calcMode="spline" keySplines="0.4 0 0.2 1"'


def f(v):
    return (f"{v:.2f}".rstrip("0").rstrip(".")) if isinstance(v, float) else str(v)


def size(name):
    return Image.open(HERE / "assets" / name).size


def img(href, x, y, w, h, extra="", inner=""):
    return f'<image href="assets/{href}" x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" preserveAspectRatio="none"{extra}>{inner}</image>'


def flip(frames, x, y, w, h, order, fps=6.0, begin="0s"):
    """几张图叠一起，按 order 轮流显示（discrete 改 opacity），无限循环。"""
    dur = len(order) / fps
    out = []
    for k, fr in enumerate(frames):
        vals = ";".join("1" if o == k else "0" for o in order)
        a = (f'<animate attributeName="opacity" values="{vals}" dur="{f(dur)}s" begin="{begin}" '
             f'calcMode="discrete" repeatCount="indefinite"/>')
        out.append(img(fr, x, y, w, h, f' opacity="{1 if order[0] == k else 0}"', a))
    return "".join(out)


def swing(body, cx, cy, deg=3.0, dur=3.2, bob=6.0, bdur=2.6, phase=0.0):
    """原地慢转 ±deg + 上下浮 bob：嵌两层 g，各自一个 animateTransform。"""
    b = f"-{f(phase)}s" if phase else "0s"
    return (f'<g transform="translate({f(cx)} {f(cy)})"><g>'
            f'<animateTransform attributeName="transform" type="translate" values="0 0;0 {f(bob)};0 0" '
            f'dur="{f(bdur)}s" begin="{b}" repeatCount="indefinite" calcMode="spline" keyTimes="0;0.5;1" '
            f'keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/><g>'
            f'<animateTransform attributeName="transform" type="rotate" values="{f(-deg)};{f(deg)};{f(-deg)}" '
            f'dur="{f(dur)}s" begin="{b}" repeatCount="indefinite" calcMode="spline" keyTimes="0;0.5;1" '
            f'keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>{body}</g></g></g>')


def speed_lines(cx, top, n=4, spread=150, length=120, color=INK, op=0.22, seed=0):
    """人物头顶几根竖向发丝线，虚线往上跑 = 空气往上冲。"""
    rnd = np.random.default_rng(seed)
    out = []
    for i in range(n):
        x = cx + (i - (n - 1) / 2) * spread / max(n - 1, 1) + rnd.uniform(-10, 10)
        L = length * rnd.uniform(0.6, 1.0)
        y0 = top - L - rnd.uniform(0, 40)
        d = rnd.uniform(0.7, 1.3)
        out.append(f'<line x1="{f(x)}" y1="{f(y0)}" x2="{f(x)}" y2="{f(y0 + L)}" stroke="{color}" stroke-width="1" '
                   f'opacity="{op}" stroke-dasharray="{f(L * 0.35)} {f(L * 0.65)}">'
                   f'<animate attributeName="stroke-dashoffset" values="0;{f(L)}" dur="{f(d)}s" repeatCount="indefinite"/></line>')
    return "".join(out)


def faller(pose, cx, cy, w, deg=3.0, phase=0.0, ghost=(0, -70), lines=True, night=False, rot=0.0):
    """一个下坠姿态：残影 + 3 帧翻页 + 转/浮 + 速度线。rot = 整体静态倾角。"""
    iw, ih = size(f"{pose}_0.png")
    h = w * ih / iw
    x0, y0 = -w / 2, -h / 2
    g = ""
    if ghost:
        gx, gy = ghost
        g += img(f"{pose}_0.png", x0 + gx, y0 + gy, w, h, ' opacity="0.10"')
        g += img(f"{pose}_0.png", x0 + gx * 2, y0 + gy * 2, w, h, ' opacity="0.045"')
    g += flip([f"{pose}_{k}.png" for k in range(3)], x0, y0, w, h, [0, 1, 2, 1], fps=6.5, begin=f"-{f(phase)}s")
    body = f'<g transform="rotate({f(rot)})">{g}</g>' if rot else g
    gl = glow(cx, cy, max(w, h) * 0.62) if night else ""
    sl = speed_lines(cx, cy - h / 2 + 10, color=NIGHT_TXT if night else INK, op=0.16 if night else 0.2,
                     seed=int(cx + cy)) if lines else ""
    return gl + sl + swing(body, cx, cy, deg=deg, phase=phase)


def glow(cx, cy, r, color="#E9C98A", layers=7, op=0.03):
    """灯下的一圈暖光：几层半透明圆叠出来（不用渐变）。"""
    return "".join(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r * (1 - i * 0.12))}" fill="{color}" opacity="{op}"/>' for i in range(layers))


def aka_tumble(cx, cy, w=78, dur=5.0, start=0.0, which="aka_stand.png", night=False, ccw=False):
    """阿卡在空中慢慢翻滚（定稿抠图，形状锁死，只做程序动画）。"""
    iw, ih = size(which)
    h = w * ih / iw
    a, b = (0, -360) if ccw else (0, 360)
    body = (f'<g><animateTransform attributeName="transform" type="rotate" values="{a};{b}" dur="{f(dur)}s" '
            f'begin="-{f(start)}s" repeatCount="indefinite"/>{img(which, -w / 2, -h / 2, w, h)}</g>')
    return swing(body, cx, cy, deg=0, bob=10, bdur=2.2, phase=start)


def say(who, text, x, y, size=31, night=False, anchor="start", name=True):
    """对白：小字人名 + 霞鹜文楷正文，全部转曲。"""
    col = NIGHT_TXT if night else INK
    nc = ({"阿卡": "#8DB57A", "小耳": "#C4705C"} if night else {"阿卡": AKA, "小耳": RUST}).get(who, GREY)
    out = ""
    tw = TP.width(text, size, "kai")
    nw = TP.width(who, 20, "light") + 12 if name else 0
    if anchor == "end":
        x -= tw + nw
    elif anchor == "middle":
        x -= (tw + nw) / 2
    if name:
        out += TP.draw(who, x, y - 3, 20, "light", fill=nc)
    out += TP.draw(text, x + nw, y, size, "kai", fill=col)
    return out


def appear(body, at, dur=0.6, dy=10):
    """开场一次性出现（之后不动）。"""
    return (f'<g opacity="0"><set attributeName="opacity" to="1" begin="{f(at)}s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" values="0 {f(dy)};0 0" begin="{f(at)}s" '
            f'dur="{f(dur)}s" fill="freeze" {E}/>{body}</g>')


def window(name, x, y, w, h, label, night=False, n=8):
    """场景窗：细线框 + 原片画面 8 帧往返循环 + 左上角时间小字。"""
    order = list(range(n)) + list(range(n - 2, 0, -1))
    fr = flip([f"win/{name}_{k}.jpg" for k in range(n)], x, y, w, h, order, fps=6)
    lc = NIGHT_LINE if night else INK
    frame = f'<rect x="{f(x - 8)}" y="{f(y - 8)}" width="{f(w + 16)}" height="{f(h + 16)}" fill="none" stroke="{lc}" stroke-width="1"/>'
    lab = TP.draw(label, x - 8, y - 22, 19, "light", fill=NIGHT_TXT if night else GREY)
    return frame + fr + lab


def leaf(x, y, s=1.0, rot=0):
    """金叶子（矢量，小耳左侧的发簪）。"""
    return (f'<g transform="translate({f(x)} {f(y)}) rotate({f(rot)}) scale({f(s)})">'
            f'<path d="M0 0 C6 -10 18 -14 30 -12 C24 -2 12 4 0 0 Z" fill="{GOLD}"/>'
            f'<path d="M2 -1 C10 -6 18 -9 27 -11" stroke="#8C6A22" stroke-width="1" fill="none"/>'
            f'<path d="M-6 3 L2 -1" stroke="{GOLD}" stroke-width="2.2" stroke-linecap="round"/></g>')


def bun_xy(name, bx, by, bw):
    """在床的抠图里找发髻顶点（她头顶最高处），换算成画布坐标。"""
    a = np.array(Image.open(HERE / "assets" / name).convert("RGBA"))[..., 3] > 120
    H, Wd = a.shape
    x_lo, x_hi = int(Wd * 0.22), int(Wd * 0.62)
    rows = np.where(a[:, x_lo:x_hi].any(1))[0]
    top = rows[0]
    xs = np.where(a[top + 6, x_lo:x_hi])[0] + x_lo
    k = bw / Wd
    return bx + xs.mean() * k, by + top * k


def app_card(x, y, w, rows, title, night=False, loop=9.0, kind="live", begin=0.0, gap=1.3):
    """简化版小耳录音卡界面（矢量，清楚、不糊）：话一句句掉进来。kind=todo 时是待办，勾自己画上。"""
    bg, bd, tx, sub = ("#FFFFFF", "#E3DED3", INK, GREY) if not night else ("#22261F", "#3C4139", NIGHT_TXT, "#8E9188")
    rh = 92
    h = 78 + rh * len(rows) + 24
    o = f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="18" fill="{bg}" stroke="{bd}" stroke-width="1"/>'
    # 头部：绿点 logo + 名字 + 录音红点
    o += f'<circle cx="{f(x + 34)}" cy="{f(y + 38)}" r="11" fill="{AKA}"/>'
    o += TP.draw("小耳录音卡", x + 54, y + 46, 23, "light", fill=tx)
    o += TP.draw(title, x + 54 + TP.width("小耳录音卡", 23, "light") + 14, y + 46, 19, "light", fill=sub)
    if kind == "live":
        o += (f'<circle cx="{f(x + w - 34)}" cy="{f(y + 38)}" r="7" fill="{RED}">'
              f'<animate attributeName="opacity" values="1;0.25;1" dur="1.6s" repeatCount="indefinite"/></circle>')
        o += TP.draw("录音中", x + w - 48, y + 45, 18, "light", fill=RED, anchor="end")
    o += f'<line x1="{f(x + 20)}" y1="{f(y + 66)}" x2="{f(x + w - 20)}" y2="{f(y + 66)}" stroke="{bd}" stroke-width="1"/>'
    for i, r in enumerate(rows):
        ry = y + 78 + i * rh + 34
        t0 = 0.4 + i * gap
        if kind == "live":
            tm, who, text = r
            pc = {"老板": "#B4553F", "小耳": AKA, "客户": "#7C7B8C"}[who]
            row = TP.draw(tm, x + 22, ry - 22, 16, "light", fill=sub)
            row += f'<rect x="{f(x + 22)}" y="{f(ry - 8)}" width="58" height="30" rx="15" fill="none" stroke="{pc}" stroke-width="1.2"/>'
            row += TP.draw(who, x + 51, ry + 13, 17, "light", fill=pc, anchor="middle")
            row += TP.draw(text, x + 94, ry + 15, 25, "kai", fill=tx)
            # 掉进来：从上面 -220 处、歪着、透明 → 落位；停住；循环末尾淡出
            k1, k2, k3, k4 = t0 / loop, (t0 + 0.9) / loop, (loop - 1.2) / loop, (loop - 0.6) / loop
            o += (f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;{f(k1)};{f(k1 + 0.02)};{f(k3)};{f(k4)};1" '
                  f'dur="{f(loop)}s" repeatCount="indefinite"/>'
                  f'<animateTransform attributeName="transform" type="translate" values="0 -230;0 -230;0 0;0 0" '
                  f'keyTimes="0;{f(k1)};{f(k2)};1" dur="{f(loop)}s" repeatCount="indefinite" calcMode="spline" '
                  f'keySplines="0 0 1 1;0.55 0 0.35 1.25;0 0 1 1"/><g>'
                  f'<animateTransform attributeName="transform" type="rotate" values="{-9 + 6 * i} {f(x + w / 2)} {f(ry)};{-9 + 6 * i} {f(x + w / 2)} {f(ry)};0 {f(x + w / 2)} {f(ry)};0 {f(x + w / 2)} {f(ry)}" '
                  f'keyTimes="0;{f(k1)};{f(k2)};1" dur="{f(loop)}s" repeatCount="indefinite"/>{row}</g></g>')
        else:
            text, = r
            bx, by = x + 30, ry - 12
            o += f'<rect x="{f(bx)}" y="{f(by)}" width="24" height="24" rx="5" fill="none" stroke="{sub}" stroke-width="1.2"/>'
            L = 30
            k1, k2, k3 = t0 / loop, (t0 + 0.5) / loop, (loop - 0.8) / loop
            o += (f'<path d="M{f(bx + 5)} {f(by + 12)} l6 6 l9 -12" fill="none" stroke="{AKA}" stroke-width="2.6" '
                  f'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{L}" stroke-dashoffset="{L}">'
                  f'<animate attributeName="stroke-dashoffset" values="{L};{L};0;0;{L}" keyTimes="0;{f(k1)};{f(k2)};{f(k3)};1" '
                  f'dur="{f(loop)}s" begin="{f(begin)}s" repeatCount="indefinite"/></path>')
            o += TP.draw(text, bx + 42, ry + 9, 25, "kai", fill=tx)
    return o, h


#  ───────────────────────── v2：真的往下掉（按时间） ─────────────────────────
#  每一段下坠 = 一个循环：起点 = 上一个场景里她的位置/大小/角度，终点 = 下一个场景里她的位置/大小/角度。
#  中间按 16 个采样点算：位置（smoothstep：中段最快，落点前减速好叠化）、缩放（空中放大）、旋转（翻滚，落点转正）、
#  透明度（起点从画面里的她淡出来，终点叠化进画面里的她）。姿态按进度切换，每个姿态内部 3 帧飘动翻页。
#  拖尾：同一套动画晚 0.07s / 0.14s 出发的两份淡拷贝 = 动态模糊。

POSE_H = 300.0   # 所有下坠姿态统一按「人高 300」画，scale=1 就是场景窗里她的大小


def pose_wh(pose):
    iw, ih = size(f"{pose}_0.png")
    return POSE_H * iw / ih, POSE_H


def ss(u):
    return u * u * (3 - 2 * u)


def samples(a, b, T, n=16, drift=0.0, spin=0.0, bulge=0.18, gravity=1.0):
    """a/b = dict(x,y,s,r)。返回 [(t, x, y, s, r)]。gravity>1 时前段更慢后段更快（真摔下去，不叠化）。"""
    out = []
    for i in range(n + 1):
        u = i / n
        p = ss(u) if gravity == 1.0 else u ** gravity
        x = a["x"] + (b["x"] - a["x"]) * p + drift * math.sin(math.pi * u)
        y = a["y"] + (b["y"] - a["y"]) * p
        s = a["s"] + (b["s"] - a["s"]) * p + bulge * math.sin(math.pi * u)
        r = a["r"] + (b["r"] - a["r"]) * p + spin * math.sin(math.pi * u)
        out.append((T * u, x, y, s, r))
    return out


def kt(ts, P):
    return ";".join(f(min(max(t / P, 0.0), 1.0)) for t in ts)


def mover(body, smp, P, t0, begin, op_in=0.12, op_out=0.15, loop=True, keep_end=False):
    """把 body（以原点为中心）沿采样点移动。周期 P，下坠从 t0 开始，其余时间隐藏。"""
    T = smp[-1][0]
    ts = [0.0] + [t0 + s[0] for s in smp] + [P]
    first, last = smp[0], smp[-1]
    pts = [first] + list(smp) + [last]
    tr = ";".join(f"{f(p[1])} {f(p[2])}" for p in pts)
    sc = ";".join(f"{f(p[3])}" for p in pts)
    ro = ";".join(f"{f(p[4])}" for p in pts)
    k = kt(ts, P)
    rep = 'repeatCount="indefinite"' if loop else 'fill="freeze"'
    a, b = t0 + op_in * T, t0 + T - op_out * T
    end_op = "1" if keep_end else "0"
    ok = kt([0, t0, a, b, t0 + T, P], P)
    ov = f"0;0;1;1;{end_op};{end_op}"
    return (f'<g opacity="0"><animate attributeName="opacity" values="{ov}" keyTimes="{ok}" dur="{f(P)}s" begin="{begin}" {rep}/>'
            f'<g transform="translate({f(first[1])} {f(first[2])})"><animateTransform attributeName="transform" type="translate" values="{tr}" keyTimes="{k}" dur="{f(P)}s" begin="{begin}" {rep}/>'
            f'<g><animateTransform attributeName="transform" type="scale" values="{sc}" keyTimes="{k}" dur="{f(P)}s" begin="{begin}" {rep}/>'
            f'<g><animateTransform attributeName="transform" type="rotate" values="{ro}" keyTimes="{k}" dur="{f(P)}s" begin="{begin}" {rep}/>'
            f'{body}</g></g></g></g>')


def pose_stack(poses, switch, P, t0, T, begin, loop=True):
    """几个姿态叠在原点，按进度 switch（0~1 的切换点）离散切换；每个姿态内部 3 帧飘动。"""
    rep = 'repeatCount="indefinite"' if loop else 'fill="freeze"'
    out = []
    bounds = list(switch) + [1.0]
    for i, pose in enumerate(poses):
        w, h = pose_wh(pose)
        lo, hi = bounds[i], bounds[i + 1]
        times = [0, t0 + lo * T, t0 + hi * T]
        vals = ["1" if i == 0 else "0", "1", "0" if i < len(poses) - 1 else "1"]
        keyt = kt(times, P)
        anim = f'<animate attributeName="opacity" values="{";".join(vals)}" keyTimes="{keyt}" dur="{f(P)}s" begin="{begin}" calcMode="discrete" {rep}/>'
        fl = flip([f"{pose}_{k}.png" for k in range(3)], -w / 2, -h / 2, w, h, [0, 1, 2, 1], fps=7)
        out.append(f'<g opacity="{1 if i == 0 else 0}">{anim}{fl}</g>')
    return "".join(out)


def fall(poses, switch, a, b, T, P, t0=0.0, begin=0.0, drift=0.0, spin=0.0, bulge=0.15, ghosts=True,
         loop=True, keep_end=False, op_in=0.12, op_out=0.15, gravity=1.0, extra_body=""):
    smp = samples(a, b, T, drift=drift, spin=spin, bulge=bulge, gravity=gravity)
    out = ""
    copies = [(0.14, 0.08), (0.07, 0.18), (0.0, 1.0)] if ghosts else [(0.0, 1.0)]
    for dt, op in copies:
        bg = f"{f(begin + dt)}s"
        body = pose_stack(poses, switch, P, t0, T, bg, loop) + (extra_body if dt == 0 else "")
        m = mover(body, smp, P, t0, bg, op_in, op_out, loop, keep_end)
        out += m if op == 1.0 else f'<g opacity="{op}">{m}</g>'
    return out


def aka_fall(a, b, T, P, t0=0.0, begin=0.0, spin=360, which="aka_stand.png", w=80, loop=True, op_in=0.1, op_out=0.15,
             keep_end=False, drift=0.0):
    iw, ih = size(which)
    h = w * ih / iw
    body = img(which, -w / 2, -h / 2, w, h)
    smp = samples(a, b, T, drift=drift, spin=0, bulge=0.1)
    smp = [(t, x, y, s, r + spin * (t / T)) for (t, x, y, s, r) in smp]
    out = ""
    for dt, op in [(0.08, 0.15), (0.0, 1.0)]:
        m = mover(body, smp, P, t0, f"{f(begin + dt)}s", op_in, op_out, loop, keep_end)
        out += m if op == 1.0 else f'<g opacity="{op}">{m}</g>'
    return out


def words_into_card(lines, P, card, begin=0.0):
    """会议里几个人说的话：一个个汉字从说话人嘴边飞出，飘落进录音卡的那一行。
    lines = [(说话人嘴的位置 (x,y), 行起点 (x,y), 文字, 开始秒)]。每个字单独一个 path，动 transform + opacity。"""
    out = []
    for (mx, my), (rx, ry), text, st in lines:
        cx = rx
        for j, ch in enumerate(text):
            cw = TP.width(ch, 25, "kai")
            glyph = TP.draw(ch, 0, 0, 25, "kai", fill=INK)
            tx, ty = cx, ry
            cx += cw
            if not glyph:
                continue
            t_start = st + j * 0.07
            dur = 1.25
            # 路径：嘴边（小、歪）→ 往上飘一点 → 弧线落进行里
            sx, sy = mx + (j % 3 - 1) * 6, my
            midx, midy = (sx + tx) / 2 + 40 * math.sin(j), min(sy, ty) - 60 - 18 * (j % 4)
            ts = [0, t_start, t_start + dur * 0.45, t_start + dur, P - 0.7, P]
            vals_t = f"{f(sx)} {f(sy)};{f(sx)} {f(sy)};{f(midx)} {f(midy)};{f(tx)} {f(ty)};{f(tx)} {f(ty)};{f(tx)} {f(ty)}"
            vals_r = f"{(-30 + 17 * j) % 60 - 30};{(-30 + 17 * j) % 60 - 30};{(j * 23) % 40 - 20};0;0;0"
            vals_s = "0.5;0.5;0.8;1;1;1"
            vals_o = "0;0;1;1;1;0"
            k = kt(ts, P)
            out.append(
                f'<g opacity="0"><animate attributeName="opacity" values="{vals_o}" keyTimes="{k}" dur="{f(P)}s" begin="{f(begin)}s" repeatCount="indefinite"/>'
                f'<g><animateTransform attributeName="transform" type="translate" values="{vals_t}" keyTimes="{k}" dur="{f(P)}s" begin="{f(begin)}s" repeatCount="indefinite"/>'
                f'<g><animateTransform attributeName="transform" type="scale" values="{vals_s}" keyTimes="{k}" dur="{f(P)}s" begin="{f(begin)}s" repeatCount="indefinite"/>'
                f'<g><animateTransform attributeName="transform" type="rotate" values="{vals_r}" keyTimes="{k}" dur="{f(P)}s" begin="{f(begin)}s" repeatCount="indefinite"/>'
                f'{glyph}</g></g></g></g>')
    return "".join(out)


def show_once(body, t_on, t_off=None, fade=0.3):
    """一次性：t_on 出现，t_off 消失（None = 一直留着）。"""
    a = f'<animate attributeName="opacity" values="0;1" begin="{f(t_on)}s" dur="{f(fade)}s" fill="freeze"/>'
    if t_off is not None:
        a += f'<animate attributeName="opacity" values="1;0" begin="{f(t_off)}s" dur="{f(fade)}s" fill="freeze"/>'
    return f'<g opacity="0">{a}{body}</g>'


def loop_show(body, P, t_on, t_off, begin=0.0, fade=0.35):
    """在周期里 t_on 出现、t_off 消失。"""
    ts = [0, max(t_on - 0.001, 0), t_on + 0.001, t_off, min(t_off + fade, P), P]
    return (f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="{kt(ts, P)}" dur="{f(P)}s" '
            f'begin="{f(begin)}s" repeatCount="indefinite"/>{body}</g>')


def build():
    els = []
    add = els.append

    # ───────── 0 题头 ─────────
    add(appear(TP.draw("小耳和阿卡", W / 2, 118, 58, "song", fill=INK, anchor="middle", spacing=0.12), 0.2, 0.9))
    add(appear(TP.draw("第一回 · 掉下去的一天", W / 2, 166, 20, "light", fill=GREY, anchor="middle", spacing=0.2), 0.6, 0.9))

    # ───────── 1 闹钟巨响 → 小懒鬼起床 → 阿卡扎丸子头、插叶子 → 一起掉下去 ─────────
    LINE1 = 720
    bw = 540
    bh = bw * size("bed_messy.png")[1] / size("bed_messy.png")[0]
    bx, by = 36, LINE1 - bh + 3
    add(f'<line x1="24" y1="{LINE1}" x2="{W - 24}" y2="{LINE1}" stroke="{INK}" stroke-width="2"/>')
    T_RING0, T_RING1 = 0.5, 3.0
    T_SIT, T_HALF, T_BUN, T_LEAF, T_GO = 3.0, 4.6, 6.0, 6.5, 8.2
    S_W, S_B, S_C, S_TODO, S_END, S_FILM = 11.6, 21.0, 27.4, 35.0, 38.6, 42.0   # 一幕一幕

    def bedimg(name, on, off=None):
        inner = f'<animate attributeName="opacity" values="0;1" begin="{on}s" dur="0.3s" fill="freeze"/>' if on else ""
        if off:
            inner += f'<animate attributeName="opacity" values="1;0" begin="{off}s" dur="0.3s" fill="freeze"/>'
        return img(f"bed_{name}.png", bx, by, bw, bh, "" if not on else ' opacity="0"', inner)
    add(bedimg("lying", 0, T_SIT))
    add(bedimg("messy", T_SIT, T_HALF))
    add(bedimg("half", T_HALF, T_BUN))
    add(bedimg("bun", T_BUN, T_GO))
    add(bedimg("empty", T_GO))

    # 闹钟：站在横杠上，响的时候猛震 + 往上跳 + 声波 + 「铃——」
    cw_ = 112
    chh = cw_ * size("clock.png")[1] / size("clock.png")[0]
    ccx, ccy = 655, LINE1 - chh / 2
    shake = (f'<animateTransform attributeName="transform" type="rotate" values="0;-9;8;-10;9;-8;10;-7;0" '
             f'begin="{T_RING0}s" dur="0.32s" repeatCount="{int((T_RING1 - T_RING0) / 0.32)}"/>')
    hop = (f'<animateTransform attributeName="transform" type="translate" values="0 0;0 -7;0 0;0 -4;0 0" '
           f'begin="{T_RING0}s" dur="0.24s" repeatCount="{int((T_RING1 - T_RING0) / 0.24)}"/>')
    add(f'<g transform="translate({f(ccx)} {f(ccy)})"><g>{hop}<g>{shake}{img("clock.png", -cw_ / 2, -chh / 2, cw_, chh)}</g></g></g>')
    waves = ""
    for i in range(3):
        for side in (-1, 1):
            r = 26 + i * 16
            x0 = ccx + side * (cw_ / 2 - 6)
            y0 = ccy - chh * 0.28
            d = f"M{f(x0 + side * r * 0.35)} {f(y0 - r * 0.8)} Q{f(x0 + side * r)} {f(y0)} {f(x0 + side * r * 0.35)} {f(y0 + r * 0.8)}"
            waves += (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="2" stroke-linecap="round" opacity="0">'
                      f'<animate attributeName="opacity" values="0;0.85;0" begin="{f(T_RING0 + i * 0.12)}s" dur="0.5s" repeatCount="{int((T_RING1 - T_RING0) / 0.5)}"/></path>')
    add(waves)
    ring = ""
    for j, ch in enumerate("铃铃铃——"):
        g = TP.draw(ch, 0, 0, 44 if ch != "—" else 30, "kai", fill=INK)
        x = 470 + j * 44
        ring += (f'<g transform="translate({x} {f(LINE1 - chh - 40 - (j % 2) * 16)})" opacity="0">'
                 f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.08;0.85;1" begin="{f(T_RING0 + j * 0.12)}s" dur="{f(T_RING1 - T_RING0 - j * 0.12)}s" fill="freeze"/>'
                 f'<g><animateTransform attributeName="transform" type="translate" values="0 0;-2 -3;3 1;-1 2;0 0" dur="0.2s" begin="{T_RING0}s" repeatCount="12"/>{g}</g></g>')
    add(ring)

    # 阿卡：床头板 → 跳到她枕边戳她 → 跳到她脑后扎头发 → 扔叶子 → 跟她一起掉下去
    hx, hy = bun_xy("bed_bun.png", bx, by, bw)
    aw = 80
    ah = aw * size("aka_stand.png")[1] / size("aka_stand.png")[0]
    p_hb = (bx + bw * 0.05, by + bh * 0.12)                   # 床头板顶
    p_pil = (bx + bw * 0.36, by + bh * 0.42)                 # 她枕边（被子上）
    p_hair = (hx - 50, hy + 88)                               # 她脑后，贴着头发
    seq = [(0, p_hb), (1.0, p_hb), (1.45, p_pil), (3.2, p_pil), (3.7, p_hair), (T_GO + 0.3, p_hair)]
    D = T_GO + 0.3
    vals, keys = [], []
    for i, (t, p) in enumerate(seq):
        if i and seq[i - 1][1] != p:   # 跳跃：中间加一个高点
            tm = (seq[i - 1][0] + t) / 2
            vals.append(f"{f((seq[i - 1][1][0] + p[0]) / 2)} {f(min(seq[i - 1][1][1], p[1]) - 70)}")
            keys.append(tm / D)
        vals.append(f"{f(p[0])} {f(p[1])}")
        keys.append(t / D)
    aka_body = img("aka_stand.png", -aw / 2, -ah, aw, ah)
    poke = (f'<animateTransform attributeName="transform" type="translate" values="0 0;0 -14;0 0" begin="1.6s" dur="0.32s" repeatCount="4"/>')
    work = (f'<animateTransform attributeName="transform" type="rotate" values="0;-10;8;-7;9;-5;0" begin="3.8s" dur="0.75s" repeatCount="3"/>')
    add(f'<g transform="translate({f(p_hb[0])} {f(p_hb[1])})" opacity="1">'
        f'<animate attributeName="opacity" values="1;0" begin="{T_GO + 0.3}s" dur="0.05s" fill="freeze"/>'
        f'<animateTransform attributeName="transform" type="translate" values="{";".join(vals)}" keyTimes="{";".join(f(k) for k in keys)}" dur="{f(D)}s" fill="freeze"/>'
        f'<g>{poke}<g>{work}{aka_body}</g></g></g>')
    # 叶子
    lx, ly = hx - 12, hy + 10
    add(f'<g opacity="0"><set attributeName="opacity" to="1" begin="{T_LEAF}s" fill="freeze"/>'
        f'<set attributeName="opacity" to="0" begin="{T_GO}s" fill="freeze"/>'
        f'<animateTransform attributeName="transform" type="translate" values="{f(p_hair[0] - lx + 10)} {f(p_hair[1] - ly - ah * 0.6)};{f((p_hair[0] - lx) / 2)} -60;0 0" '
        f'keyTimes="0;0.5;1" begin="{T_LEAF}s" dur="0.7s" fill="freeze" calcMode="spline" keySplines="0.2 0 0.6 1;0.4 0 0.2 1"/>'
        f'<g><animateTransform attributeName="transform" type="rotate" values="-300 {f(lx)} {f(ly)};0 {f(lx)} {f(ly)}" begin="{T_LEAF}s" dur="0.7s" fill="freeze" {E}/>'
        f'{leaf(lx, ly, 0.9, -35)}</g></g>')
    burst = "".join(f'<line x1="{f(lx + 8 + 16 * math.cos(a))}" y1="{f(ly - 6 + 16 * math.sin(a))}" '
                    f'x2="{f(lx + 8 + 28 * math.cos(a))}" y2="{f(ly - 6 + 28 * math.sin(a))}" stroke="{GOLD}" stroke-width="1.6" stroke-linecap="round"/>'
                    for a in [-2.4, -1.6, -0.8, 0.1])
    add(f'<g opacity="0"><animate attributeName="opacity" values="0;1;0" begin="{T_LEAF + 0.68}s" dur="0.5s" fill="freeze"/>{burst}</g>')
    # 对白
    add(appear(say("阿卡", "小懒鬼，起床啦。", 40, 268), 1.5))
    add(appear(say("小耳", "五分钟……", 330, 318), 2.3))
    add(appear(say("阿卡", "别动，扎头发。", 400, 268 + 0), 3.9))
    add(appear(say("阿卡", "好了。出门！", 420, 318 + 52), T_LEAF + 0.9))

    # ───────── 2 会议窗（她和阿卡掉进她的座位） ─────────
    WX, WW, WH = 30, 690, 388
    MEET_Y = LINE1 + 760
    seat_meet = dict(x=WX + 570, y=MEET_Y + 268, s=1.0, r=0)
    aka_meet = dict(x=WX + 528, y=MEET_Y + 222, s=1.0, r=0)
    bed_her = dict(x=bx + bw * 0.34, y=by + bh * 0.45, s=0.62, r=0)
    bed_aka = dict(x=p_hair[0], y=p_hair[1] - ah / 2, s=1.0, r=0)
    add(window("meet", WX, MEET_Y, WW, WH, "14:30 · 春季展主视觉讨论"))
    # 第一次：起床后一起掉下去（一次性），掉进会议座位
    add(fall(["st1", "bp_fall1", "st2", "st4"], [0, 0.22, 0.5, 0.8], bed_her, seat_meet, 3.2, 3.2, begin=T_GO,
             drift=170, spin=40, bulge=0.2, loop=False, op_in=0.03, op_out=0.14))
    add(aka_fall(bed_aka, aka_meet, 3.2, 3.2, begin=T_GO + 0.2, w=60, spin=720, loop=False, drift=-120, op_in=0.03))
    add(appear(say("阿卡", "九点的会。", 40, LINE1 + 300), T_GO + 0.5))
    add(appear(say("阿卡", "还剩七分钟。", 40, LINE1 + 342, name=False), T_GO + 1.0))
    add(appear(say("小耳", "来得及！", W - 40, LINE1 + 560, anchor="end"), T_GO + 1.8))

    # ───────── 3 话飘进录音卡 + 阿卡整理 ─────────
    CARD_Y = MEET_Y + WH + 170
    cx0, cw0 = 40, 670
    rows = [("14:30", "老板", "今天主要定一下春季展的主视觉。", (WX + 345, MEET_Y + 205)),
            ("14:30", "小耳", "我先把三个方向的草图过一遍。", (WX + 525, MEET_Y + 178)),
            ("14:31", "客户", "我们更喜欢第二版的颜色。", (WX + 268, MEET_Y + 215))]
    P_W = 11.0
    rh = 92
    head = 78
    summ = 150
    ch_ = head + rh * len(rows) + summ
    # 她循环离开会议（从座位出来、穿到卡片后面、过硬边、掉进出租车）—— 先画，卡片盖在上面 = 从界面后面穿过去
    EDGE = CARD_Y + ch_ + 330
    TAXI_Y = EDGE + 230
    seat_taxi = dict(x=WX + 280, y=TAXI_Y + 280, s=1.0, r=360)
    aka_taxi = dict(x=WX + 372, y=TAXI_Y + 218, s=1.0, r=0)
    # 卡片底
    card = (f'<rect x="{cx0}" y="{CARD_Y}" width="{cw0}" height="{ch_}" rx="18" fill="#FFFFFF" stroke="#E3DED3" stroke-width="1"/>'
            f'<circle cx="{cx0 + 34}" cy="{CARD_Y + 38}" r="11" fill="{AKA}"/>'
            + TP.draw("小耳录音卡", cx0 + 54, CARD_Y + 46, 23, "light", fill=INK)
            + TP.draw("· 现场会议", cx0 + 54 + TP.width("小耳录音卡", 23, "light") + 14, CARD_Y + 46, 19, "light", fill=GREY)
            + f'<circle cx="{cx0 + cw0 - 34}" cy="{CARD_Y + 38}" r="7" fill="{RED}"><animate attributeName="opacity" values="1;0.25;1" dur="1.6s" repeatCount="indefinite"/></circle>'
            + TP.draw("录音中", cx0 + cw0 - 48, CARD_Y + 45, 18, "light", fill=RED, anchor="end")
            + f'<line x1="{cx0 + 20}" y1="{CARD_Y + 66}" x2="{cx0 + cw0 - 20}" y2="{CARD_Y + 66}" stroke="#E3DED3" stroke-width="1"/>')
    lines = []
    for i, (tm, who, text, mouth) in enumerate(rows):
        ry = CARD_Y + head + i * rh + 34
        st = 0.6 + i * 2.2
        pc = {"老板": "#B4553F", "小耳": AKA, "客户": "#7C7B8C"}[who]
        tag = (TP.draw(tm, cx0 + 22, ry - 22, 16, "light", fill=GREY)
               + f'<rect x="{cx0 + 22}" y="{f(ry - 8)}" width="58" height="30" rx="15" fill="none" stroke="{pc}" stroke-width="1.2"/>'
               + TP.draw(who, cx0 + 51, ry + 13, 17, "light", fill=pc, anchor="middle"))
        card += loop_show(tag, P_W, st, P_W - 0.7, begin=S_W)
        lines.append((mouth, (cx0 + 94, ry + 15), text, st + 0.1))
    # 阿卡整理：最后一句落完，阿卡跳上卡片右上角，下面长出「阿卡整理」两条
    sy0 = CARD_Y + head + rh * len(rows) + 10
    t_sum = 0.6 + 2 * 2.2 + 2.2
    summary = (f'<line x1="{cx0 + 20}" y1="{sy0}" x2="{cx0 + cw0 - 20}" y2="{sy0}" stroke="#E3DED3" stroke-width="1" stroke-dasharray="4 4"/>'
               + TP.draw("阿卡整理", cx0 + 22, sy0 + 38, 18, "light", fill=AKA))
    items = ["主视觉：用第二版的配色", "待办：周五前把三张图给客户"]
    for i, t in enumerate(items):
        yy = sy0 + 76 + i * 44
        L = 30
        summary += (f'<path d="M{cx0 + 26} {yy - 8} l7 7 l11 -14" fill="none" stroke="{AKA}" stroke-width="2.6" stroke-linecap="round" '
                    f'stroke-linejoin="round" stroke-dasharray="{L}" stroke-dashoffset="{L}">'
                    f'<animate attributeName="stroke-dashoffset" values="{L};{L};0;0" keyTimes="{kt([0, t_sum + 0.5 + i * 0.5, t_sum + 0.9 + i * 0.5, P_W], P_W)}" dur="{f(P_W)}s" begin="{f(S_W)}s" repeatCount="indefinite"/></path>'
                    + TP.draw(t, cx0 + 60, yy, 23, "kai", fill=INK))
    card += loop_show(summary, P_W, t_sum + 0.3, P_W - 0.7, begin=S_W)
    # 阿卡从会议窗里跳出来落到卡片右上角，整理完跳回去
    aka_card = dict(x=cx0 + cw0 - 60, y=CARD_Y - 30, s=1.0, r=0)
    aka_hop_out = aka_fall(aka_meet, aka_card, 0.9, P_W, t0=t_sum - 0.6, begin=S_W, w=64, spin=0, loop=False, op_out=0.03)
    # 卡片右上角的阿卡（落下之后站着、点点头），周期末尾淡出
    a_w = 64
    a_h = a_w * size("aka_stand.png")[1] / size("aka_stand.png")[0]
    nod = f'<animateTransform attributeName="transform" type="rotate" values="0;-8;0;6;0" dur="0.9s" repeatCount="indefinite"/>'
    aka_on_card = show_once(f'<g transform="translate({f(aka_card["x"])} {f(aka_card["y"] + a_h / 2)})"><g>{nod}{img("aka_stand.png", -a_w / 2, -a_h, a_w, a_h)}</g></g>',
                            S_W + t_sum + 0.3, None, fade=0.05)

    # 夜色硬边 + 出租车窗先画（在她下面）：她从会议座位出来 → 从卡片后面穿过 → 过硬边 → 落进出租车座位叠化
    add(f'<rect x="0" y="{EDGE}" width="{W}" height="99999" fill="{NIGHT}"/>')
    add(appear(say("小耳", "好累……", 40, EDGE - 70), S_B + 1.6))
    add(window("taxi", WX, TAXI_Y, WW, WH, "20:10 · 回家路上", night=True))
    add(appear(say("小耳", "……到家叫我。", 40, TAXI_Y + WH + 60, night=True), S_B + 4.6))
    add(appear(say("阿卡", "哼。", W - 40, TAXI_Y + WH + 60, night=True, anchor="end"), S_B + 5.6))
    P_B = 7.5
    add(fall(["st4", "st2", "st3"], [0, 0.18, 0.62], seat_meet, seat_taxi, 4.4, P_B, begin=S_B, loop=False,
             drift=150, spin=0, bulge=0.25, op_in=0.12))
    add(card)
    add(words_into_card(lines, P_W, card, begin=S_W))
    add(aka_hop_out)
    add(aka_on_card)
    add(appear(say("阿卡", "你听，我记。", 40, MEET_Y + WH + 64), S_W + 0.2))

    # ───────── 5 从出租车掉到沙发：砸下去那一刻变成瘫着 ─────────
    sw = 620
    sh = sw * size("barN_0.png")[1] / size("barN_0.png")[0]
    SOFA_Y = TAXI_Y + WH + 420
    base = 405 / 432 * sh
    LINE2 = SOFA_Y + base
    sx0 = 50
    add(f'<line x1="24" y1="{f(LINE2)}" x2="{W - 24}" y2="{f(LINE2)}" stroke="{NIGHT_TXT}" stroke-width="1.6" opacity="0.7"/>')
    P_C = 9.0
    T_FALL = 2.4
    land = dict(x=sx0 + sw * 0.42, y=SOFA_Y + sh * 0.45, s=0.95, r=-8)
    add(glow(sx0 + sw * 0.45, SOFA_Y + sh * 0.5, sw * 0.55))
    add(fall(["st3", "bp_fall3", "st2"], [0, 0.3, 0.68], dict(x=seat_taxi["x"], y=seat_taxi["y"], s=1.0, r=0), land,
             T_FALL, P_C, begin=S_C, drift=-120, spin=70, bulge=0.15, op_in=0.15, op_out=0.06, gravity=1.6, loop=False))
    # 落地：沙发上的她（周期里 T_FALL 出现，压扁回弹，最后淡出）
    sq = (f'<animateTransform attributeName="transform" type="scale" values="1 1;1 1;1.05 0.86;0.98 1.04;1 1;1 1" '
          f'keyTimes="{kt([0, T_FALL, T_FALL + 0.1, T_FALL + 0.25, T_FALL + 0.4, P_C], P_C)}" dur="{f(P_C)}s" begin="{f(S_C)}s" fill="freeze"/>')
    bar = flip([f"barN_{k}.png" for k in range(6)], -sw / 2, -base, sw, sh, [0, 1, 2, 3, 4, 5, 4, 3, 2, 1], fps=4)
    add(show_once(f'<g transform="translate({f(sx0 + sw / 2)} {f(LINE2)})"><g>{sq}{bar}</g></g>', S_C + T_FALL, None, fade=0.02))
    # 落地的一下：两道短横线往外弹
    dust = "".join(f'<line x1="{f(sx0 + sw * 0.5 + d * 120)}" y1="{f(LINE2 - 6)}" x2="{f(sx0 + sw * 0.5 + d * 175)}" y2="{f(LINE2 - 16)}" '
                   f'stroke="{NIGHT_TXT}" stroke-width="1.6" stroke-linecap="round"/>' for d in (-1, 1, -1.4, 1.4))
    add(show_once(dust, S_C + T_FALL, S_C + T_FALL + 0.25, fade=0.15))
    # 阿卡：从出租车她肩上一起掉 → 落在她旁边的线上 → 「又这样睡」→ 跳下去 → 掉进台灯窗
    a_w2 = 76
    a_h2 = a_w2 * size("aka_stand.png")[1] / size("aka_stand.png")[0]
    aka_line = dict(x=sx0 + sw * 0.83 + 34, y=LINE2 - a_h2 / 2, s=1.0, r=0)
    add(aka_fall(aka_taxi, aka_line, T_FALL, P_C, t0=0.15, begin=S_C, w=a_w2, spin=360, op_out=0.02, loop=False))
    DESK_Y = LINE2 + 330
    aka_desk = dict(x=WX + 420, y=DESK_Y + 268, s=1.05, r=0)
    T_JUMP = 5.4
    add(window("desk", WX, DESK_Y, WW, WH, "01:20 · 她睡着以后", night=True))
    add(show_once(img("aka_stand.png", aka_line["x"] - a_w2 / 2, aka_line["y"] - a_h2 / 2, a_w2, a_h2), S_C + T_FALL + 0.15, S_C + T_JUMP, fade=0.01))
    add(aka_fall(dict(aka_line), aka_desk, 2.0, P_C, t0=T_JUMP, begin=S_C, w=a_w2, spin=-360, drift=-160, op_in=0.0, op_out=0.2, loop=False))
    add(show_once(say("阿卡", "……又这样睡。", W - 40, SOFA_Y - 46, night=True, anchor="end"), S_C + T_FALL + 0.6))
    add(show_once(say("阿卡", "我去收拾。", 40, LINE2 + 120, night=True), S_C + T_JUMP - 0.6))

    # ───────── 6 台灯下：阿卡整理 ─────────
    y = DESK_Y + WH + 70
    todo, th = app_card(40, y, 670, [("把第二版颜色延展到三张主视觉",), ("周五前回客户",), ("买猫粮（阿卡加的）",)],
                        "· 待办", night=True, loop=8.0, kind="todo", begin=S_TODO)
    add(todo)
    add(appear(say("阿卡", "整理好了。", W - 40, y + th + 56, night=True, anchor="end"), S_TODO + 3.2))
    TODO_END = y + th + 100
    y += th + 200

    # ───────── 7 梦里搂住（整篇唯一静下来的地方） ─────────
    lw = 640
    lh = lw * size("land_0.png")[1] / size("land_0.png")[0]
    LINE3 = y + 276 / 326 * lh
    add(glow(55 + lw * 0.35, y + lh * 0.5, lw * 0.5))
    add(f'<line x1="24" y1="{f(LINE3)}" x2="{W - 24}" y2="{f(LINE3)}" stroke="{NIGHT_TXT}" stroke-width="1.6" opacity="0.7"/>')
    add(flip([f"land_{k}.png" for k in range(8)], 55, y, lw, lh, list(range(8)) + list(range(6, 0, -1)), fps=4))
    add(appear(say("小耳", "今天都说了什么来着。", 40, LINE3 + 70, night=True), S_END + 1.4))
    add(appear(say("阿卡", "都在。睡吧。", W - 40, LINE3 + 120, night=True, anchor="end"), S_END + 2.8))
    H = int(LINE3 + 330)

    # ───────── 线索 + 一层一层推开 ─────────
    #  线索：她每一段第一次下坠的轨迹，一根细线跟着她画出来（dashoffset 按采样点同步），把几幕串起来。
    #  推开：页面高度跟着她的 y 往下长（她领路），每一幕演完才露出下一幕。
    segs = [  # (起点, 终点, 时长, 开始秒, drift, gravity, 领先距离, 这一段最多推到哪)
        (bed_her, seat_meet, 3.2, T_GO, 170, 1.0, 440, MEET_Y + WH + 110),
        (seat_meet, seat_taxi, 4.4, S_B, 150, 1.0, 480, TAXI_Y + WH + 110),
        (dict(x=seat_taxi["x"], y=seat_taxi["y"], s=1, r=0), land, T_FALL, S_C, -120, 1.6, 440, LINE2 + 170),
        (dict(aka_line), aka_desk, 2.0, S_C + T_JUMP, -160, 1.0, 340, DESK_Y + WH + 60),
    ]
    REV = [(0.0, LINE1 + 80)]
    thread = []
    for a, b, T, t0, drift, grav, lead, cap in segs:
        smp = samples(a, b, T, drift=drift, gravity=grav)
        pts = [(x, y) for (_, x, y, _, _) in smp]
        L = [0.0]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            L.append(L[-1] + math.hypot(x2 - x1, y2 - y1))
        tot = L[-1]
        d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts)
        offs = ";".join(f(tot - l) for l in L)
        kts = ";".join(f(t / T) for (t, *_r) in smp)
        thread.append(f'<path d="{d}" fill="none" stroke="{GREY}" stroke-width="1.3" opacity="0.75" stroke-linecap="round" '
                      f'stroke-dasharray="{f(tot)} {f(tot + 10)}" stroke-dashoffset="{f(tot)}">'
                      f'<animate attributeName="stroke-dashoffset" values="{offs}" keyTimes="{kts}" begin="{f(t0)}s" dur="{f(T)}s" fill="freeze"/></path>')
        for (t, x, y, _s, _r) in smp[2::2]:
            REV.append((t0 + t, min(y + lead, cap)))
        REV.append((t0 + T + 0.2, cap))
    # 卡片、待办、结尾、片尾
    REV.append((S_W + 0.3, CARD_Y + ch_ + 70))
    REV.append((S_TODO, TODO_END))
    H_ = int(LINE3 + 330)
    REV.append((S_END, H_))
    REV = sorted(REV)
    mono, best = [], 0
    for t, y in REV:          # 只往下长，不回缩
        if y > best + 1:
            best = y
            mono.append((round(t, 2), round(y)))
    els.insert(0, "".join(thread))

    # 左侧时间刻度
    ruler = [f'<line x1="12" y1="230" x2="12" y2="{H - 40}" stroke="{GREY}" stroke-width="0.8" opacity="0.45"/>']
    for ty in range(240, H - 40, 32):
        ruler.append(f'<line x1="12" y1="{ty}" x2="{17 if (ty // 32) % 4 else 21}" y2="{ty}" stroke="{GREY}" stroke-width="0.8" opacity="0.45"/>')
    els.insert(0, "".join(ruler))
    els.append(TP.draw("07:40", 24, LINE1 - 8, 14, "light", fill=GREY))

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" style="display:block;width:100%;line-height:0;">'
           f'<rect x="0" y="0" width="{W}" height="{H}" fill="{PAPER}"/>{"".join(els)}</svg>')
    return svg, H, mono, LINE1 + 80, S_FILM


def outro():
    """片尾落版（单独一块小 SVG，接在视频下面）。"""
    Ho = 420
    o = f'<rect width="{W}" height="{Ho}" fill="{NIGHT}"/>'
    # 线索线从上面画下来，落进红点，红点才亮
    o += (f'<path d="M{W / 2} 0 V62" fill="none" stroke="{NIGHT_TXT}" stroke-width="1.3" stroke-linecap="round" opacity="0.7" stroke-dasharray="62" stroke-dashoffset="62">'
          f'<animate attributeName="stroke-dashoffset" values="62;0" begin="0.4s" dur="0.6s" fill="freeze"/></path>')
    o += (f'<g opacity="0"><set attributeName="opacity" to="1" begin="1.0s" fill="freeze"/><circle cx="{W / 2}" cy="70" r="8" fill="{RED}"><animate attributeName="opacity" values="1;0.3;1" dur="2s" begin="1.0s" repeatCount="indefinite"/></circle></g>')
    o += TP.draw("录下来，整理好", W / 2, 150, 34, "kai", fill=NIGHT_TXT, anchor="middle", spacing=0.1)
    o += TP.draw("小耳和阿卡 · 小耳录音卡", W / 2, 205, 19, "light", fill="#9A9C94", anchor="middle", spacing=0.15)
    o += f'<line x1="{W / 2 - 120}" y1="250" x2="{W / 2 + 120}" y2="250" stroke="{NIGHT_LINE}" stroke-width="1"/>'
    o += TP.draw(URL, W / 2, 306, 36, "light", fill="#E0503F", anchor="middle", spacing=0.04)
    o += TP.draw("长按复制网址，在浏览器打开", W / 2, 352, 20, "light", fill="#8E9188", anchor="middle")
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {Ho}" style="display:block;width:100%;line-height:0;">{o}</svg>'


def film_head():
    Hh = 150
    o = f'<rect width="{W}" height="{Hh}" fill="{NIGHT}"/>'
    o += f'<line x1="{W / 2}" y1="0" x2="{W / 2}" y2="50" stroke="{NIGHT_LINE}" stroke-width="1"/>'
    o += TP.draw("这一天，完整版", W / 2, 100, 26, "kai", fill=NIGHT_TXT, anchor="middle", spacing=0.1)
    o += TP.draw("《小耳和阿卡》第一集 · 96 秒", W / 2, 134, 20, "light", fill="#8E9188", anchor="middle")
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {Hh}" style="display:block;width:100%;line-height:0;">{o}</svg>'


PREVIEW = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>小耳和阿卡 预览</title>
<style>body{{margin:0;background:#ddd}} #art{{max-width:430px;margin:0 auto;background:#fff}}
.bar{{position:sticky;top:0;z-index:9;text-align:center;padding:8px;background:#fff;border-bottom:1px solid #ccc}}
button{{font-size:14px;padding:5px 12px}}</style></head><body>
<div class="bar"><button onclick="document.querySelectorAll('#art svg').forEach(s=>s.setCurrentTime(0))">重播</button></div>
<div id="art">{article}</div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--update")
    a = ap.parse_args()
    svg, H, REV, FIRST, S_FILM = build()
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    video_local = '<video src="../work/film_wx.mp4" controls playsinline style="display:block;width:100%;background:#000"></video>'
    sec = lambda inner: f'<section style="line-height:0;background-color:{NIGHT};">{inner}</section>'
    VIDEO_H = W * 9 / 16
    total = H + 150 + VIDEO_H + 420
    REV = REV + [(S_FILM, total)]
    steps, prev = [], 100.0
    for i, (t, y) in enumerate(REV):
        nxt = REV[i + 1][0] if i + 1 < len(REV) else t + 1.2
        dur = max(0.25, min(nxt - t, 1.2))
        pct = round(y / FIRST * 100, 3)
        if pct <= prev:
            continue
        steps.append(f'<animate attributeName="width" values="{f(prev)}%;{f(pct)}%" begin="{f(t)}s" dur="{f(dur)}s" '
                     f'fill="freeze" restart="never" calcMode="spline" keyTimes="0;1" keySplines="0.4 0 0.2 1"/>')
        prev = pct
    canvas = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {FIRST}" width="100%" '
              f'style="display:block;max-width:none!important;pointer-events:none;">{"".join(steps)}</svg>')
    inner = svg + film_head() + "{{VIDEO}}" + outro()
    article = (f'<section style="overflow:hidden;line-height:0;text-align:center;background-color:{NIGHT};">'
               f'<section style="height:0;overflow:visible;line-height:0;width:100%;">{inner}</section>{canvas}</section>')
    (out / "long.svg").write_text(svg, encoding="utf-8")
    (out / "article.html").write_text(article, encoding="utf-8")
    pv = article.replace('href="assets/', 'href="../assets/').replace("{{VIDEO}}", video_local)
    (out / "preview.html").write_text(PREVIEW.format(article=pv), encoding="utf-8")
    kb = len(article.encode()) / 1024
    print(f"✅ 高 {H} · 正文 {kb:.0f}KB · 图片引用 {article.count('<image')} 处")
    if a.push or a.update:
        push(article, out, a.update)


def push(article, out, update=None):
    import re, os, time
    sys.path[:0] = [str(Path.home() / "projects/xiaoer-wx-svg-timeline/motion")]
    import wechat
    tok = wechat.token()
    cache_p = out / "mmbiz.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    rel = sorted(set(re.findall(r'href="(assets/[^"]+\.(?:jpg|png))"', article)))
    for n in rel:
        p = HERE / n
        key = f"{n}:{p.stat().st_mtime_ns}"
        if key not in cache:
            cache[key] = wechat.upload_image(tok, p)
            cache_p.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
            print("上传", n, flush=True)
        article = article.replace(f'href="{n}"', f'href="{cache[key]}"')
    print(f"图片 {len(rel)} 张 → mmbiz")
    # iOS 微信：同一图片地址在一个 svg 里出现多次，有的请求永远不结束 → svg 不触发 load → 动画时钟不启动。
    # 每一处引用都加不同的 &v=n，让每个 <image> 是独立地址（mmbiz 忽略多余参数，返回同一张图）。
    seen = {}
    def _uniq(m):
        u = m.group(1); seen[u] = seen.get(u, 0) + 1
        return f'href="{u}&amp;v={seen[u]}"' if "?" in u else f'href="{u}?v={seen[u]}"'
    article = re.sub(r'href="(https://mmbiz\.qpic\.cn/[^"]+)"', _uniq, article)
    print(f"图片引用 {sum(seen.values())} 处，全部改成独立地址")
    # 视频：永久素材 → vid → 公众号视频标签
    film = HERE / "work/film_wx.mp4"
    vkey = f"video:{film.stat().st_mtime_ns}"
    if vkey not in cache:
        bd = "----b" + os.urandom(8).hex()
        desc = json.dumps({"title": "小耳和阿卡 第一集", "introduction": "小耳录音卡 · 录下来，整理好"}, ensure_ascii=False)
        body = (f'--{bd}\r\nContent-Disposition: form-data; name="media"; filename="film.mp4"\r\nContent-Type: video/mp4\r\n\r\n').encode() \
            + film.read_bytes() + (f'\r\n--{bd}\r\nContent-Disposition: form-data; name="description"\r\n\r\n{desc}\r\n--{bd}--\r\n').encode()
        req = wechat.urllib.request.Request(f"{wechat.API}/material/add_material?access_token={tok}&type=video", data=body,
                                            headers={"Content-Type": f"multipart/form-data; boundary={bd}"}, method="POST")
        with wechat.urllib.request.urlopen(req, timeout=300, context=wechat._ctx()) as r:
            d = json.loads(r.read())
        print("视频素材:", d)
        if "media_id" not in d:
            raise SystemExit("视频上传失败")
        mid = d["media_id"]
        info = {}
        for _ in range(20):  # 转码要一会儿，vid 出来才能嵌
            info = wechat._call(f"{wechat.API}/material/get_material?access_token={tok}", json.dumps({"media_id": mid}).encode())
            if info.get("vid") or "apiv_" in json.dumps(info):
                break
            time.sleep(6)
        print("get_material:", {k: (v if len(str(v)) < 120 else str(v)[:120]) for k, v in info.items()})
        vid = info.get("vid") or re.search(r"apiv_\d+", json.dumps(info)).group(0)
        cover = wechat.upload_image(tok, HERE / "work/film_cover.jpg")
        cache[vkey] = {"media_id": mid, "vid": vid, "cover": cover}
        cache_p.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    v = cache[vkey]
    from urllib.parse import quote
    iframe = (f'<iframe class="video_iframe rich_pages wx_video_iframe" data-vidtype="2" data-mpvid="{v["vid"]}" '
              f'data-cover="{quote(v["cover"], safe="")}" data-ratio="1.7777777777777777" data-w="1280" '
              f'data-src="https://mp.weixin.qq.com/mp/readtemplate?t=pages/video_player_tmpl&amp;action=mpvideo&amp;auto=0&amp;vid={v["vid"]}"></iframe>')
    article = article.replace("{{VIDEO}}", f'<section style="text-align:center;background-color:{NIGHT};">{iframe}</section>')
    (out / "article.mmbiz.html").write_text(article, encoding="utf-8")
    mid = wechat.save_draft(article, "小耳和阿卡｜她在睡，它在记", str(HERE / "out/cover.jpg"), "小耳",
                            "往下滑，跟她过完这一天。", update=update)
    (out / "media_id.txt").write_text(mid, encoding="utf-8")
    print("草稿 media_id:", mid)
    for tg, lo, re_ in wechat.check(mid, article):
        print(f"  {tg:<17} 本地 {lo:5d}  草稿 {re_:5d}{'' if lo == re_ else '  ⚠️'}")


if __name__ == "__main__":
    main()
