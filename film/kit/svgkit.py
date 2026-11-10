"""公众号竖向 SVG 动效长图 · 基础积木（不依赖任何私有工具）

依赖：pip install pillow numpy fonttools playwright && playwright install chromium

坐标：画布宽 W=750，往下是 y。时间：全篇一条绝对时间线，单位秒，从读者打开文章那一刻算 0。
所有函数返回一段 SVG 字符串，自己拼起来；最后交给 assemble() 生成预览页和正文。

公众号里不能用的：id、<style>、JS、mask、clipPath、滤镜、渐变、xlink:href。这里的函数都没用到它们。
iPhone 微信真机里不能用的：对 y / height 做 repeatCount="indefinite" 的 <animate>（整张图会不动）。
  循环动画只用 opacity / transform / stroke-dashoffset。
"""
import math, re, sys
from pathlib import Path
from PIL import Image

W = 750
PAPER, INK, NIGHT = "#F4F1EA", "#1C1E1C", "#191C1A"
GREY, NIGHT_LINE, NIGHT_TXT = "#8C877D", "#5E625C", "#D9D3C6"
EASE = 'calcMode="spline" keySplines="0.4 0 0.2 1"'

ASSETS = Path("assets")          # 起步工程里会改成项目自己的 assets 目录
_TP = None                       # textpath.TextPath 实例，init_fonts() 设置


def f(v):
    """数字转成短字符串（最多 2 位小数）。SVG 体积很敏感，所有坐标都过一遍它。"""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def size(name):
    """素材的像素宽高。"""
    with Image.open(ASSETS / name) as im:
        return im.size


def has(name):
    return (ASSETS / name).exists()


# ───────────────────────── 文字 ─────────────────────────
FONT_CANDIDATES = [
    "~/Library/Fonts/LXGWWenKai-Regular.ttf",                 # 霞鹜文楷（推荐，免费可商用）
    "/System/Library/Fonts/Supplemental/Songti.ttc",          # macOS 宋体
    "/System/Library/Fonts/STHeiti Medium.ttc",               # macOS 黑体
    "C:/Windows/Fonts/simkai.ttf", "C:/Windows/Fonts/msyh.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc", "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]


def init_fonts(fonts=None):
    """fonts = {"名字": "字体文件路径"}。不给就自动找一个系统里的中文字体，名字叫 "zh"。
    公众号不能加载自定义字体，所以字要转成曲线（<path>）才能保证每台手机上长得一样。"""
    global _TP
    from textpath import TextPath
    if not fonts:
        for c in FONT_CANDIDATES:
            p = Path(c).expanduser()
            if p.exists():
                fonts = {"zh": str(p)}
                break
        else:
            raise SystemExit("没找到中文字体：给 init_fonts({'zh': '你的字体.ttf'}) 传一个路径")
    _TP = TextPath(fonts)
    return _TP


def text(s, x, y, px, font="zh", fill=INK, anchor="start", spacing=0.0):
    """一行字转成曲线。y 是基线。anchor = start / middle / end。"""
    return _TP.draw(s, x, y, px, font, fill=fill, anchor=anchor, spacing=spacing)


def text_width(s, px, font="zh", spacing=0.0):
    return _TP.width(s, px, font, spacing)


def say(who, line, x, y, px=31, night=False, anchor="start", name_color=None, font="zh", name_font=None):
    """一句对白：前面小字人名，后面正文。"""
    col = NIGHT_TXT if night else INK
    nf = name_font or font
    nw = text_width(who, 20, nf) + 12 if who else 0
    tw = text_width(line, px, font)
    if anchor == "end":
        x -= tw + nw
    elif anchor == "middle":
        x -= (tw + nw) / 2
    out = text(who, x, y - 3, 20, nf, fill=name_color or GREY) if who else ""
    return out + text(line, x + nw, y, px, font, fill=col)


# ───────────────────────── 图片和出现方式 ─────────────────────────
def img(name, x, y, w, h, extra="", inner=""):
    """一张图。name 相对 assets/。推草稿时 href 会被换成公众号图床地址。"""
    return f'<image href="assets/{name}" x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" preserveAspectRatio="none"{extra}>{inner}</image>'


def centered(name, w):
    """以 (0,0) 为中心的一张图，配合 track() 用。返回 (svg, 高)。"""
    iw, ih = size(name)
    h = w * ih / iw
    return img(name, -w / 2, -h / 2, w, h), h


def show_once(body, t_on, t_off=None, fade=0.3):
    """t_on 秒淡入；t_off 秒淡出（None = 一直留着）。"""
    a = f'<animate attributeName="opacity" values="0;1" begin="{f(t_on)}s" dur="{f(fade)}s" fill="freeze"/>'
    if t_off is not None:
        a += f'<animate attributeName="opacity" values="1;0" begin="{f(t_off)}s" dur="{f(fade)}s" fill="freeze"/>'
    return f'<g opacity="0">{a}{body}</g>'


def appear(body, at, dur=0.6, dy=10):
    """at 秒出现，同时从下面 dy 处浮上来。对白用这个。"""
    return (f'<g opacity="0"><set attributeName="opacity" to="1" begin="{f(at)}s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" values="0 {f(dy)};0 0" begin="{f(at)}s" '
            f'dur="{f(dur)}s" fill="freeze" {EASE}/>{body}</g>')


def flip(frames, x, y, w, h, order, fps=6.0, begin=0.0, loop=True):
    """几张图叠在一起，按 order 轮流显示（翻页动画）。loop=False 播一遍停在最后一帧。
    每一帧是一张图：帧数直接吃图片数，手机上一个画面 2–4 帧就够。"""
    n = len(order)
    dur = n / fps
    out = ""
    for k, fr in enumerate(frames):
        if loop:
            vals = ";".join("1" if o == k else "0" for o in order)
            a = f'<animate attributeName="opacity" values="{vals}" dur="{f(dur)}s" begin="{f(begin)}s" calcMode="discrete" repeatCount="indefinite"/>'
        else:
            vals = ";".join("1" if o == k else "0" for o in order) + (";1" if order[-1] == k else ";0")
            kts = ";".join(f(i / n) for i in range(n)) + ";1"
            a = f'<animate attributeName="opacity" values="{vals}" keyTimes="{kts}" dur="{f(dur)}s" begin="{f(begin)}s" calcMode="discrete" fill="freeze"/>'
        out += img(fr, x, y, w, h, ' opacity="0"', a)
    return f'<g opacity="0"><set attributeName="opacity" to="1" begin="{f(begin)}s" fill="freeze"/>{out}</g>'


def breathe(body, base_y, amount=0.012, dur=3.2):
    """呼吸：以 base_y 那条横线为底，纵向轻轻起伏。body 里的坐标要写成相对 base_y 的（y - base_y）。
    注意：这是 iPhone 上安全的写法（scale）。不要用 <animate attributeName="y"> 做起伏。"""
    return (f'<g transform="translate(0 {f(base_y)})"><g><animateTransform attributeName="transform" type="scale" '
            f'values="1 1;1 {f(1 + amount)};1 1" dur="{f(dur)}s" begin="0s" repeatCount="indefinite"/>{body}</g></g>')


def glow(cx, cy, r, color="#E9C98A", layers=28, op=0.012):
    """一团柔光（没有渐变可用，拿很多层半透明的圆叠出来）。层数少会看到一圈一圈的台阶。"""
    return "".join(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r * (i + 1) / layers)}" fill="{color}" opacity="{op}"/>' for i in range(layers))


# ───────────────────────── 关键帧轨道 ─────────────────────────
def _kt(ts, D):
    return ";".join(f(min(max(t / D, 0.0), 1.0)) for t in ts)


def track(body, keys):
    """最重要的一个函数。让 body 沿一串关键帧走。
    keys = [(秒, x, y, 缩放, 角度, 透明度), ...]，秒必须递增。body 要以 (0,0) 为中心画（用 centered()）。
    四层 <g> 分别管透明度、位置、缩放、旋转，所以旋转和缩放都绕着 body 自己的中心。
    最外层写了初始 transform：不写的话，元素在第一个关键帧之前停在 (0,0)，切片时会被收进每一张。"""
    D = keys[-1][0] + 0.001
    if keys[0][0] > 0:
        keys = [(0.0,) + tuple(keys[0][1:])] + list(keys)
    k = _kt([kk[0] for kk in keys], D)
    tr = ";".join(f"{f(x)} {f(y)}" for (_, x, y, _, _, _) in keys)
    sc = ";".join(f(s) for (_, _, _, s, _, _) in keys)
    ro = ";".join(f(r) for (_, _, _, _, r, _) in keys)
    op = ";".join(f(o) for (*_, o) in keys)
    _, x0, y0, s0, r0, o0 = keys[0]
    a = f'dur="{f(D)}s" begin="0s" fill="freeze"'
    return (f'<g opacity="{f(o0)}"><animate attributeName="opacity" values="{op}" keyTimes="{k}" {a}/>'
            f'<g transform="translate({f(x0)} {f(y0)})"><animateTransform attributeName="transform" type="translate" values="{tr}" keyTimes="{k}" {a}/>'
            f'<g transform="scale({f(s0)})"><animateTransform attributeName="transform" type="scale" values="{sc}" keyTimes="{k}" {a}/>'
            f'<g transform="rotate({f(r0)})"><animateTransform attributeName="transform" type="rotate" values="{ro}" keyTimes="{k}" {a}/>'
            f'{body}</g></g></g></g>')


def poses(spans):
    """同一条轨道上按时间换姿态。spans = [(图片名, 宽, 开始秒, 结束秒), ...]。返回放进 track() 的 body。"""
    D = max(b for *_, b in spans) + 0.001
    out = ""
    for name, w, a, b in spans:
        body, _ = centered(name, w)
        out += (f'<g opacity="0"><animate attributeName="opacity" values="0;1;0" keyTimes="0;{f(a / D)};{f(min(b / D, 1))}" '
                f'dur="{f(D)}s" begin="0s" calcMode="discrete" fill="freeze"/>{body}</g>')
    return out


def _ease(p0, p1, v, kind):
    e = v * v if kind == "in" else 1 - (1 - v) ** 2 if kind == "out" else v * v * (3 - 2 * v) if kind == "io" else v
    return p0 + (p1 - p0) * e


def fall_path(a, b, t0, T, curve=None, drift=0.0, rot=None, bulge=0.1, n=18, op_in=0.25, op_out=0.2):
    """一次下坠的关键帧。a / b = dict(x, y, s, r) 起点和终点；t0 开始秒，T 时长。
    curve = [(时间进度, 位置进度, 缓动)]，缓动 = None 匀速 / "in" 越来越快 / "out" 越来越慢 / "io"。
      例：[(0,0,None),(0.3,0.1,"in"),(1,1,"in")] = 前 30% 时间只走 10%（起步慢），之后加速。
    drift：中途往旁边飘多少（正 = 右）。rot(u)：额外的角度。bulge：中途放大多少（离镜头近的感觉）。
    op_in / op_out：头尾各用多少秒淡入淡出。落进场景窗时 op_out 取 0.2，人到窗顶边就消失。
    返回 (keys, pos)。pos(t) 给出任意时刻的 (x, y, s, r)，跟着她走的东西（角色、对白、线头）用它算位置。"""
    curve = curve or [(0, 0, None), (1, 1, "io")]

    def prog(u):
        for (u0, p0, _), (u1, p1, kind) in zip(curve, curve[1:]):
            if u <= u1 + 1e-9:
                return _ease(p0, p1, 0 if u1 == u0 else (u - u0) / (u1 - u0), kind)
        return 1.0

    def state(u):
        p = prog(u)
        x = a["x"] + (b["x"] - a["x"]) * p + drift * math.sin(math.pi * u)
        if 0.08 < u < 0.92:
            x = min(max(x, 150), W - 150)                      # 空中别出页面左右边
        return (x, a["y"] + (b["y"] - a["y"]) * p, a["s"] + (b["s"] - a["s"]) * p + bulge * math.sin(math.pi * u),
                a["r"] + (b["r"] - a["r"]) * p + (rot(u) if rot else 0))

    keys = []
    for i in range(n + 1):
        u = i / n
        o = 1.0
        if op_in and T * u < op_in:
            o = T * u / op_in
        if op_out and T * (1 - u) < op_out:
            o = min(o, T * (1 - u) / op_out)
        keys.append((t0 + T * u,) + state(u) + (o,))
    return keys, (lambda t: state(min(max((t - t0) / T, 0), 1)))


def hop(p0, p1, t0, T, height=70, n=10, spin=0.0, s0=1.0, s1=1.0):
    """小角色从 p0 跳到 p1 的抛物线关键帧（接在 track 的 keys 里）。"""
    return [(t0 + T * i / n, p0[0] + (p1[0] - p0[0]) * i / n,
             p0[1] + (p1[1] - p0[1]) * i / n - height * 4 * (i / n) * (1 - i / n),
             s0 + (s1 - s0) * i / n, spin * i / n, 1) for i in range(n + 1)]


def idle(keys, t0, t1, period=1.1, ds=0.04, dr=4, hops=()):
    """角色原地等着的时候别僵着：(t0, t1) 之间加一鼓一鼓、左右歪头；hops 里的时刻原地蹦一下（说话的时候）。
    只加关键帧，不增加任何动画标签。要求 (t0, t1) 之间原来没有关键帧。"""
    assert not [k for k in keys if t0 < k[0] < t1]
    _, x, y, sc, r, o = max((k for k in keys if k[0] <= t0), key=lambda k: k[0])
    new, t, i = [], t0 + period / 2, 0
    hs = sorted(h for h in hops if t0 < h < t1 - 0.3)
    while t < t1 - 0.05:
        if not any(h - 0.1 < t < h + 0.4 for h in hs):
            sg = 1 if i % 2 == 0 else -1
            new.append((t, x, y, sc * (1 + ds * sg), r + dr * sg, o))
        t += period / 2; i += 1
    for h in hs:
        new += [(h, x, y, sc * 0.94, r, o), (h + 0.13, x, y - 18, sc * 1.05, r - 5, o), (h + 0.26, x, y, sc * 0.95, r, o), (h + 0.36, x, y, sc, r, o)]
    return sorted(list(keys) + new, key=lambda k: k[0])


def pop(keys, pos, times, k=1.06, d=0.16):
    """换姿态的那一刻整体放大一下再回弹，换图就不生硬。times = 换姿态的时刻。"""
    out = list(keys)
    for t in times:
        x, y, s, r = pos(t + d / 2)
        out.append((t + d / 2, x, y, s * k, r, 1))
    return sorted(out, key=lambda kk: kk[0])


# ───────────────────────── 发丝线手稿 ─────────────────────────
def draw_on(d, length, t, dur=0.5, color=INK, op=0.75, sw=1.3):
    """一条线到 t 秒自己画出来。d = 路径；length = 路径大概多长（宁大勿小，小了画不完）。
    线宽：近处的东西 1.3–1.4、深色；远处的 1.2、浅灰。"""
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" opacity="{op}" '
            f'stroke-dasharray="{length}" stroke-dashoffset="{length}"><animate attributeName="stroke-dashoffset" values="{length};0" '
            f'begin="{f(t)}s" dur="{dur}s" fill="freeze"/></path>')


def ground(y, x0=24, x1=W - 24, color=INK, sw=2):
    """一条地面线。人、床、柜子都站在它上面。"""
    return f'<line x1="{x0}" y1="{f(y)}" x2="{x1}" y2="{f(y)}" stroke="{color}" stroke-width="{sw}"/>'


def sofa_lines(L, t, xl=84, xr=666, aw=54, back=112, seat=104, floor=142, color=NIGHT_TXT):
    """发丝线沙发，L = 坐垫面的 y。靠背、两个扶手、坐垫前沿和中缝、腿、地面，从 t 秒起依次画出来。"""
    al, ar, m = xl - aw, xr + aw, (xl + xr) / 2
    D = lambda d, n, tt, du=0.5, o=0.75, s=1.3: draw_on(d, n, tt, du, color, o, s)
    return (D(f"M{xl} {f(L)} V{f(L - back + 28)} Q{xl} {f(L - back)} {xl + 28} {f(L - back)} H{xr - 28} Q{xr} {f(L - back)} {xr} {f(L - back + 28)} V{f(L)}", 900, t, 0.6)
            + D(f"M{xl} {f(L + seat)} H{al + 10} Q{al} {f(L + seat)} {al} {f(L + seat - 10)} V{f(L - 46)} Q{al} {f(L - 62)} {al + 16} {f(L - 62)} H{xl - 16} Q{xl} {f(L - 62)} {xl} {f(L - 46)} V{f(L + seat)}", 520, t + 0.05)
            + D(f"M{xr} {f(L + seat)} H{ar - 10} Q{ar} {f(L + seat)} {ar} {f(L + seat - 10)} V{f(L - 46)} Q{ar} {f(L - 62)} {ar - 16} {f(L - 62)} H{xr + 16} Q{xr} {f(L - 62)} {xr} {f(L - 46)} V{f(L + seat)}", 520, t + 0.1)
            + D(f"M{xl} {f(L + seat)} H{xr} M{f(m)} {f(L + 8)} V{f(L + seat)}", 700, t + 0.2, 0.5, 0.6)
            + D(f"M{xl - 22} {f(L + seat)} V{f(L + floor)} M{xr + 22} {f(L + seat)} V{f(L + floor)}", 90, t + 0.4, 0.3)
            + D(f"M24 {f(L + floor)} H{W - 24}", 720, t + 0.3, 0.6, 0.4, 1))


def thread(keys, color=GREY, op=0.7, dx=30, dy=-128):
    """线索线：沿着一次下坠的关键帧画一条发丝线，随着人往下掉逐段画出来。
    线头落在「身体中心 + (dx, dy) × 缩放」（她举起的手）。不要让它跟着身体旋转，否则线会折成锯齿。"""
    pts = [(k[0], k[1] + dx * k[3], k[2] + dy * k[3]) for k in keys]
    d = "M" + " L".join(f"{f(x)} {f(y)}" for _, x, y in pts)
    L = int(sum(math.hypot(b[1] - a[1], b[2] - a[2]) for a, b in zip(pts, pts[1:]))) + 10
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1" opacity="{op}" stroke-dasharray="{L}" stroke-dashoffset="{L}">'
            f'<animate attributeName="stroke-dashoffset" values="{L};0" begin="{f(pts[0][0])}s" dur="{f(pts[-1][0] - pts[0][0])}s" fill="freeze"/></path>')


# ───────────────────────── 场景窗 ─────────────────────────
def window(x, y, w, h, label, frames, t_on, frame_at=None, bounce=None, dim=None, night=False, fps=1.0, loop=True, font="zh"):
    """一个细线框的场景窗，里面放片子里抽出来的帧。
    frames：图片名列表（相对 assets/）。手机内存有限，一个窗 2 帧（首尾）就够；需要看清动作的 3–4 帧。
    t_on：画面亮起的时刻（= 人落到窗顶边的时刻）。frame_at：线框开始描的时刻（比 t_on 早 0.5 秒左右）。
    bounce：窗被人砸到、一沉一弹的时刻（t_on + 0.1）。dim = (秒, 透明度)：人走了以后盖一层底色压暗，纸白段 0.25、夜段 0.45。
    规则：下坠的人不要画进窗里（窗里的画面本身有她，会出现两个她）；让她在窗顶边淡掉，由窗「接住」。"""
    lc = NIGHT_LINE if night else INK
    per = 2 * (w + h + 32)
    fa = t_on if frame_at is None else frame_at
    out = (f'<rect x="{f(x - 8)}" y="{f(y - 8)}" width="{f(w + 16)}" height="{f(h + 16)}" fill="none" stroke="{lc}" stroke-width="1" '
           f'stroke-dasharray="{f(per)}" stroke-dashoffset="{f(per)}"><animate attributeName="stroke-dashoffset" values="{f(per)};0" '
           f'begin="{f(fa)}s" dur="0.5s" fill="freeze"/></rect>')
    if label:
        out += show_once(text(label, x - 8, y - 24, 22, font, fill=NIGHT_TXT if night else GREY), max(fa - 0.3, 0))
    order = list(range(len(frames))) + (list(range(len(frames) - 2, 0, -1)) if loop else [])
    pics = flip(frames, x, y, w, h, order, fps=fps, begin=t_on, loop=loop) if len(frames) > 1 else img(frames[0], x, y, w, h)
    out += f'<g opacity="0"><animate attributeName="opacity" values="0;1" begin="{f(t_on)}s" dur="0.22s" fill="freeze"/>{pics}</g>'
    if dim:
        out += (f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{NIGHT if night else PAPER}" opacity="0">'
                f'<animate attributeName="opacity" values="0;{dim[1]}" begin="{f(dim[0])}s" dur="0.4s" fill="freeze"/></rect>')
    if bounce is not None:
        out = (f'<g><animateTransform attributeName="transform" type="translate" values="0 0;0 10;0 -3;0 0" keyTimes="0;0.35;0.7;1" '
               f'begin="{f(bounce)}s" dur="0.32s"/>{out}</g>')
    return out


def catch_dust(x, y, t, color=INK):
    """窗接住人的那一下，窗顶边两侧溅起的四根短线。x = 她落下来的横坐标，y = 窗顶。"""
    return show_once("".join(f'<line x1="{f(x + d * 70)}" y1="{f(y - 14)}" x2="{f(x + d * 120)}" y2="{f(y - 30)}" stroke="{color}" '
                             f'stroke-width="1.6" stroke-linecap="round"/>' for d in (-1, 1, -1.5, 1.5)), t, t + 0.3, fade=0.12)


# ───────────────────────── 组装：推开 + 切片 + 预览 ─────────────────────────
PREVIEW = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>预览</title>
<style>body{{margin:0;background:#ddd}} #art{{max-width:430px;margin:0 auto;background:#fff}}
.bar{{position:sticky;top:0;z-index:9;text-align:center;padding:8px;background:#fff;border-bottom:1px solid #ccc}}
button{{font-size:14px;padding:5px 12px}}</style></head><body>
<div class="bar"><button onclick="document.querySelectorAll('#art svg').forEach(s=>s.setCurrentTime(0))">重播</button></div>
<div id="art">{article}</div></body></html>"""


def reveal_canvas(rev, first, refs=()):
    """「推开」：页面按时间自己往下长，读者不用滑。
    原理：外层 section 高度为 0、内容溢出显示；后面跟一张空白 SVG（canvas），它的宽度按时间从 100% 变大，
    高度跟着等比变大，把外层撑高，于是下面的内容一点点露出来。
    rev = [(秒, 露出到的 y), ...]；first = 一开始就露出的高度。
    refs：全部图片的地址。放成 1×1 的隐藏图，让 canvas 等图片都加载完才开始走（否则页面先推开、画面还没出来）。
    连续的几步之间走匀速，一串的第一步缓入、最后一步缓出，这样不会一顿一顿。"""
    raw, prev = [], 100.0
    rev = sorted(rev)
    for i, (t, y) in enumerate(rev):
        nxt = rev[i + 1][0] if i + 1 < len(rev) else t + 1.2
        pct = round(y / first * 100, 3)
        if pct <= prev:
            continue
        raw.append((t, max(0.2, min(nxt - t, 1.2)), prev, pct, nxt - t <= 1.2))
        prev = pct
    steps = ""
    for i, (t, dur, p0, p1, joined) in enumerate(raw):
        before = i > 0 and raw[i - 1][4]
        ks = None if (before and joined) else "0.4 0 1 1" if joined else "0 0 0.2 1" if before else "0.4 0 0.2 1"
        ease = f' calcMode="spline" keyTimes="0;1" keySplines="{ks}"' if ks else ""
        steps += f'<animate attributeName="width" values="{f(p0)}%;{f(p1)}%" begin="{f(t)}s" dur="{f(dur)}s" fill="freeze" restart="never"{ease}/>'
    wait = "".join(f'<image href="{r}" x="0" y="0" width="1" height="1" opacity="0"/>' for r in refs)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {first}" width="100%" '
            f'style="display:block;max-width:none!important;pointer-events:none;">{steps}{wait}</svg>')


def assemble(elements, H, rev, first, out_dir, bg=PAPER, tail="", T=80, slice_target=850):
    """把一串顶层元素拼成正文。
    elements：顶层 SVG 片段的列表（顺序 = 叠放顺序，后面的盖住前面的）。H：画布总高。
    rev / first：见 reveal_canvas。tail：接在长图后面的东西（视频占位 {{VIDEO}}、落版 SVG）。
    T：全片多少秒（切片时要把整条时间线量一遍）。
    产物：out_dir/long.svg（整张）、article.html（要推的正文）、preview.html（本地预览，双击打开）。"""
    import slicer
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" '
            f'style="display:block;max-width:none!important;background-color:{bg};">')
    svg = head + f'<rect x="0" y="0" width="{W}" height="{H}" fill="{bg}"/>' + "".join(elements) + "</svg>"
    (out / "long.svg").write_text(svg, encoding="utf-8")
    parts, info = slicer.split(svg, H, T=T, target=slice_target, work=out)
    for a0, b0, n, im, an, kb in info:
        print(f"  切片 {a0:5.0f}–{b0:5.0f}  元素 {n:3d}  图 {im:2d}  动画 {an:3d}  {kb:.0f}KB")
    refs = sorted(set(re.findall(r'href="(assets/[^"]+)"', svg)))
    rev = [(t, min(y, H)) for t, y in rev]            # 推开不能超过画布高度，否则底下会露出一截底色
    canvas = reveal_canvas(rev, first, refs)
    article = (f'<section style="overflow:hidden;line-height:0;text-align:center;background-color:{bg};">'
               f'<section style="height:0;overflow:visible;line-height:0;width:100%;">{"".join(parts)}{tail}</section>{canvas}</section>')
    (out / "article.html").write_text(article, encoding="utf-8")
    (out / "preview.html").write_text(PREVIEW.format(article=article.replace('href="assets/', f'href="{ASSETS.resolve().as_uri()}/')), encoding="utf-8")
    kb = len(article.encode()) / 1024
    warn = "  ⚠️ 超过 640KB，公众号会拒收（45002）" if kb > 640 else ""
    print(f"✅ 高 {H} · 正文 {kb:.0f}KB · 图片引用 {article.count('<image')} 处{warn}")
    return article
