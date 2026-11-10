"""《小耳和阿卡》公众号 SVG v3 · 一幕一幕往下掉（按 方向/分镜v3.md）

    .venv/bin/python build3.py                → out/ 预览
    .venv/bin/python build3.py --update <id>  → 推草稿（不发布）

v3 的做法：
- 一条绝对时间线。每个会动的东西（小耳、阿卡、外套、鞋、手机、叶子）都是一条关键帧轨道 track()，
  keys = [(秒, x, y, 缩放, 角度, 透明度)]，所有动画 begin=0、dur=整条轨道长度、fill=freeze。互相对位精确到 0.1 秒。
- 小耳的下坠由 fall_path() 采样：位置按分段缓动（悬停→加速→减速对准落点）、S 形漂移、旋转函数、空中放大。
- 姿态按绝对时间切换；每个姿态内部 3 帧飘动翻页（大衣、头发在风里抖）。拖尾只留 1 份淡拷贝。
- 场景窗：她落进来那一刻窗里画面才亮（不会一人两份）；她离开时窗里画面压暗（人走了）。
- 页面一层一层推开：她领路，下一幕演到才露出来；一根细线索跟着她的轨迹画下去（窗里不画）。
"""
import sys, math, json, argparse
from pathlib import Path
from build import (HERE, TP, W, PAPER, INK, NIGHT, GREY, RUST, AKA, RED, GOLD, NIGHT_LINE, NIGHT_TXT, URL, E,
                   f, size, img, flip, say, appear, leaf, show_once, words_into_card, app_card,
                   outro, film_head, PREVIEW, push)

WX, WW, WH = 30, 690, 388
POSE_H = 300.0
LITE = True   # 手机内存：每个姿态 1 帧、场景窗 2 帧、翻页最多 2 帧
A = HERE / "assets"


def has(name):
    return (A / name).exists()


def pose_or(name, fallback):
    return name if has(f"{name}_0.png") else fallback


POSE_K = {"swA": 0.62, "swB": 0.9, "coatC": 0.95}   # 蜷成一团的姿态按人高画会偏大


def pose_wh(pose):
    iw, ih = size(f"{pose}_0.png")
    h = POSE_H * POSE_K.get(pose, 1.0)
    return h * iw / ih, h


def kt(ts, D):
    return ";".join(f(min(max(t / D, 0.0), 1.0)) for t in ts)


# ───────────────────────── 轨道 ─────────────────────────
def track(body, keys, op_scale=1.0):
    """keys = [(t, x, y, s, r, op)]，t 为文档绝对秒，必须递增。"""
    D = keys[-1][0] + 0.001
    ts = [k[0] for k in keys]
    if ts[0] > 0:  # 第一个关键帧之前保持初始状态
        keys = [(0.0,) + tuple(keys[0][1:])] + list(keys)
        ts = [0.0] + ts
    k = kt(ts, D)
    tr = ";".join(f"{f(x)} {f(y)}" for (_, x, y, _, _, _) in keys)
    sc = ";".join(f(s) for (_, _, _, s, _, _) in keys)
    ro = ";".join(f(r) for (_, _, _, _, r, _) in keys)
    op = ";".join(f(o * op_scale) for (*_, o) in keys)
    x0, y0, s0, r0, o0 = keys[0][1], keys[0][2], keys[0][3], keys[0][4], keys[0][5] * op_scale
    a = f'dur="{f(D)}s" begin="0s" fill="freeze"'
    return (f'<g opacity="{f(o0)}"><animate attributeName="opacity" values="{op}" keyTimes="{k}" {a}/>'
            f'<g transform="translate({f(x0)} {f(y0)})"><animateTransform attributeName="transform" type="translate" values="{tr}" keyTimes="{k}" {a}/>'
            f'<g transform="scale({f(s0)})"><animateTransform attributeName="transform" type="scale" values="{sc}" keyTimes="{k}" {a}/>'
            f'<g transform="rotate({f(r0)})"><animateTransform attributeName="transform" type="rotate" values="{ro}" keyTimes="{k}" {a}/>'
            f'{body}</g></g></g></g>')


def track2(body, keys):
    """轻量轨道：只动位置和透明度（飞字用）。"""
    D = keys[-1][0] + 0.001
    if keys[0][0] > 0:
        keys = [(0.0,) + tuple(keys[0][1:])] + list(keys)
    k = kt([kk[0] for kk in keys], D)
    tr = ";".join(f"{f(x)} {f(y)}" for (_, x, y, *_r) in keys)
    op = ";".join(f(kk[5]) for kk in keys)
    a = f'dur="{f(D)}s" begin="0s" fill="freeze"'
    return (f'<g opacity="{f(keys[0][5])}"><animate attributeName="opacity" values="{op}" keyTimes="{k}" {a}/>'
            f'<g transform="translate({f(keys[0][1])} {f(keys[0][2])})"><animateTransform attributeName="transform" type="translate" values="{tr}" keyTimes="{k}" {a}/>'
            f'{body}</g></g>')


def poses_body(spans, D):
    """spans = [(pose, t_on, t_off)] 绝对秒。每个姿态在自己的时段显示（离散切换），内部 3 帧飘动。"""
    out = []
    for pose, a, b in spans:
        w, h = pose_wh(pose)
        if LITE:
            fl = img(f"{pose}_0.png", -w / 2, -h / 2, w, h)
        else:
            frames = [f"{pose}_{k}.png" for k in range(3)]
            fl = flip(frames, -w / 2, -h / 2, w, h, [0, 1, 2, 1], fps=7)
        anim = (f'<animate attributeName="opacity" values="0;1;0" keyTimes="0;{f(a / D)};{f(min(b / D, 1))}" '
                f'dur="{f(D)}s" begin="0s" calcMode="discrete" fill="freeze"/>')
        out.append(f'<g opacity="0">{anim}{fl}</g>')
    return "".join(out)


def seg_ease(p0, p1, v, kind):
    if kind == "in":
        e = v * v
    elif kind == "out":
        e = 1 - (1 - v) * (1 - v)
    elif kind == "io":
        e = v * v * (3 - 2 * v)
    else:
        e = v
    return p0 + (p1 - p0) * e


def fall_path(a, b, t0, T, curve=None, drift=0.0, rot=None, bulge=0.12, n=18, op_in=0.25, op_out=0.4, fade_in=True):
    """a/b = dict(x,y,s,r)。curve = [(u, p, 缓动)]：u 时间进度 → p 位置进度。rot(u) → 额外角度。
    返回 (keys, pos(t))。"""
    curve = curve or [(0, 0, None), (1, 1, "io")]

    def prog(u):
        for (u0, p0, _), (u1, p1, kind) in zip(curve, curve[1:]):
            if u <= u1 + 1e-9:
                v = 0 if u1 == u0 else (u - u0) / (u1 - u0)
                return seg_ease(p0, p1, v, kind)
        return 1.0

    def state(u):
        p = prog(u)
        x = a["x"] + (b["x"] - a["x"]) * p + drift * math.sin(math.pi * u)
        if 0.08 < u < 0.92:                     # 空中别出页面左右边
            x = min(max(x, 150), W - 150)
        y = a["y"] + (b["y"] - a["y"]) * p
        s = a["s"] + (b["s"] - a["s"]) * p + bulge * math.sin(math.pi * u)
        r = a["r"] + (b["r"] - a["r"]) * p + (rot(u) if rot else 0)
        return x, y, s, r

    keys = []
    for i in range(n + 1):
        u = i / n
        t = t0 + T * u
        x, y, s, r = state(u)
        o = 1.0
        if fade_in and T * u < op_in:
            o = (T * u) / op_in
        if T * (1 - u) < op_out:
            o = min(o, (T * (1 - u)) / op_out)
        keys.append((t, x, y, s, r, o))

    def pos(t):
        u = min(max((t - t0) / T, 0), 1)
        return state(u)
    return keys, pos


def her(keys, spans, ghost=False):
    """小耳：姿态 + 轨道 + 一份淡拖尾。"""
    D = keys[-1][0] + 0.001
    body = poses_body(spans, D)
    out = ""
    if ghost:
        gk = [(k[0] + 0.09,) + tuple(k[1:]) for k in keys]
        gbody = poses_body([(p, a + 0.09, b + 0.09) for p, a, b in spans], gk[-1][0] + 0.001)
        out += track(gbody, gk, op_scale=0.14)
    return out + track(body, keys)


def gone(body, t, fade=0.3):
    """t 秒淡出（给下坠的人让路）。"""
    return f'<g><animate attributeName="opacity" values="1;0" begin="{f(t)}s" dur="{f(fade)}s" fill="freeze"/>{body}</g>'


def pop(keys, pos, times, k=1.06, d=0.16):
    """换姿态的那一刻缩放顶一下再回来，硬切读成「甩了一下」。只加关键帧，不加动画。"""
    out = list(keys)
    for ts in times:
        for tt, kk in ((ts, k), (ts + d, 1.0)):
            prev = max((q for q in out if q[0] <= tt), key=lambda q: q[0])
            nxt = min((q for q in out if q[0] > tt), key=lambda q: q[0])
            u = (tt - prev[0]) / (nxt[0] - prev[0])
            o = prev[5] + (nxt[5] - prev[5]) * u
            x, y, sc, r = pos(tt)
            if abs(prev[0] - tt) < 0.02:
                out.remove(prev)
            out.append((tt, x, y, sc * kk, r, o))
        out.sort(key=lambda q: q[0])
    return out


def idle(keys, t0, t1, period=1.1, ds=0.04, dr=4, hops=()):
    """阿卡原地等的时候：一鼓一鼓、左右歪头；hops 里的时刻原地蹦一下（说话的时候）。只加关键帧。"""
    assert not [k for k in keys if t0 < k[0] < t1], [k[0] for k in keys if t0 < k[0] < t1]
    base = max((k for k in keys if k[0] <= t0), key=lambda k: k[0])
    _, x, y, sc, r, o = base
    new, t, i = [], t0 + period / 2, 0
    hop_ts = sorted(h for h in hops if t0 < h < t1 - 0.3)
    while t < t1 - 0.05:
        if any(h - 0.1 < t < h + 0.4 for h in hop_ts):
            t += period / 2; i += 1; continue
        sg = 1 if i % 2 == 0 else -1
        new.append((t, x, y, sc * (1 + ds * sg), r + dr * sg, o))
        t += period / 2; i += 1
    for h in hop_ts:
        new += [(h, x, y, sc * 0.94, r, o), (h + 0.13, x, y - 18, sc * 1.05, r - 5, o), (h + 0.26, x, y, sc * 0.95, r, o), (h + 0.36, x, y, sc, r, o)]
    return sorted(list(keys) + new, key=lambda k: k[0])


_AKA_PARTS = None
_AKA_N = [0]


def aka_img(w=70, which="aka_stand.png", wave=(), kick=(), rig=False):
    """阿卡：定稿抠图切成身体 + 耳朵 + 手（+ 脚），各自绕转轴小幅转动。
    平时：耳朵隔几秒抖一下、手轻轻一张一合、脚偶尔点一下；wave 里的时刻举一下手，kick 里的时刻轮流抬脚。"""
    global _AKA_PARTS
    iw, ih = size(which)
    h = w * ih / iw
    name = which[:-4]
    if _AKA_PARTS is None:
        pj = HERE / "assets/aka_parts.json"
        _AKA_PARTS = json.loads(pj.read_text()) if pj.exists() else {}
    if not rig or name not in _AKA_PARTS or not has(f"{name}_base.png"):
        return img(which, -w / 2, -h / 2, w, h), h
    k = w / iw
    _AKA_N[0] += 1
    ph = (_AKA_N[0] * 0.37) % 1.0          # 每只阿卡错开一点，不会同时抖
    out = img(f"{name}_base.png", -w / 2, -h / 2, w, h)
    for pn, pt in _AKA_PARTS[name]["parts"].items():
        bx_, by_, bw_, bh_ = pt["box"]; px, py = pt["pivot"]
        sg = 1 if pn.endswith("L") else -1
        an = ""
        if pn.startswith("ear"):
            d = 2.9 if sg > 0 else 3.7
            an += (f'<animateTransform attributeName="transform" type="rotate" values="0;0;{-13 * sg};{6 * sg};0" keyTimes="0;0.8;0.87;0.94;1" '
                   f'dur="{d}s" begin="{f(ph * d)}s" repeatCount="indefinite"/>')
        elif pn.startswith("arm"):
            d = 1.7 if sg > 0 else 2.1
            an += (f'<animateTransform attributeName="transform" type="rotate" values="0;{9 * sg};0" dur="{d}s" begin="{f(ph * d)}s" repeatCount="indefinite"/>')
            for i, t in enumerate(wave):
                a = 38 * sg
                an += (f'<animateTransform attributeName="transform" type="rotate" values="0;{a};{f(a * 0.55)};{a};0" '
                       f'begin="{f(t)}s" dur="0.62s"/>')
        elif pn.startswith("foot"):
            d = 4.3 if sg > 0 else 5.9
            an += (f'<animateTransform attributeName="transform" type="rotate" values="0;0;{10 * sg};0;{8 * sg};0" keyTimes="0;0.74;0.8;0.87;0.93;1" '
                   f'dur="{d}s" begin="{f(1 + ph * d)}s" repeatCount="indefinite"/>')
            for i, t in enumerate(kick):
                if (i % 2 == 0) == (sg > 0):
                    an += f'<animateTransform attributeName="transform" type="rotate" values="0;{18 * sg};0" begin="{f(t)}s" dur="0.24s"/>'
        out += (f'<g transform="translate({f((px - iw / 2) * k)} {f((py - ih / 2) * k)})"><g>{an}'
                + img(f"{name}_{pn}.png", (bx_ - px) * k, (by_ - py) * k, bw_ * k, bh_ * k) + '</g></g>')
    return out, h


def aka_3d(w, which="aka_squat.png", acts=(), step=1):
    """three.js 渲染的立体阿卡（work/aka3d/render.py）：平时放 idle（左右看、眨眼、抖耳朵），
    acts = [(动作, 开始秒, 结束秒)] 的时段换成挥手 / 跺脚。每一帧一张图，改 opacity 翻页。"""
    name = which[:-4]
    info = json.loads((HERE / f"assets/aka3d/{name}.json").read_text())
    iw, ih = info["size"]; vw, vh = info["view"]
    k = w / iw
    fw, fh = vw * k, vh * k
    def frames(an, begins):
        n, fps = info["actions"][an]["n"], info["actions"][an]["fps"]
        idx = list(range(0, n, step if an == "idle" else 1))
        m = len(idx); dur = m / (fps / (step if an == "idle" else 1))
        out = ""
        for j, fi in enumerate(idx):
            vals = ";".join("1" if q == j else "0" for q in range(m))
            an_ = ""
            for (b0, b1) in begins:
                rc = "indefinite" if b1 is None else str(max(1, math.ceil((b1 - b0) / dur)))
                an_ += f'<animate attributeName="opacity" values="{vals}" dur="{f(dur)}s" begin="{f(b0)}s" calcMode="discrete" repeatCount="{rc}"/>'
            out += img(f"aka3d/{name}_{an}_{fi}.png", -fw / 2, -fh / 2, fw, fh, ' opacity="0"', an_)
        return out
    acts = sorted(acts, key=lambda a: a[1])
    sets = "".join(f'<set attributeName="opacity" to="0" begin="{f(a)}s" fill="freeze"/><set attributeName="opacity" to="1" begin="{f(b)}s" fill="freeze"/>' for _, a, b in acts)
    out = f'<g>{sets}{frames("idle", [(0, None)])}</g>'
    for an in sorted(set(a[0] for a in acts)):
        iv = [(a, b) for nm, a, b in acts if nm == an]
        sets = "".join(f'<set attributeName="opacity" to="1" begin="{f(a)}s" fill="freeze"/><set attributeName="opacity" to="0" begin="{f(b)}s" fill="freeze"/>' for a, b in iv)
        out += f'<g opacity="0">{sets}{frames(an, iv)}</g>'
    return out, w * ih / iw


def prop_img(name, w):
    iw, ih = size(name)
    h = w * ih / iw
    return img(name, -w / 2, -h / 2, w, h)


def catch_dust(x, y, t, col):
    """窗接住她那一下，窗顶边两侧溅起的短线。"""
    return show_once("".join(f'<line x1="{f(x + d * 70)}" y1="{f(y - 14)}" x2="{f(x + d * 120)}" y2="{f(y - 30)}" '
                             f'stroke="{col}" stroke-width="1.6" stroke-linecap="round"/>' for d in (-1, 1, -1.5, 1.5)), t, t + 0.3, fade=0.12)


def hop(p0, p1, t0, T, height=70, n=10, spin=0.0, s0=1.0, s1=1.0, op=(1, 1)):
    """抛物线跳跃关键帧。"""
    ks = []
    for i in range(n + 1):
        u = i / n
        x = p0[0] + (p1[0] - p0[0]) * u
        y = p0[1] + (p1[1] - p0[1]) * u - height * 4 * u * (1 - u)
        ks.append((t0 + T * u, x, y, s0 + (s1 - s0) * u, spin * u, op[0] + (op[1] - op[0]) * u))
    return ks


def glow(cx, cy, r, color="#E9C98A", layers=28, op=0.012):
    return "".join(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r * (1 - i / layers * 0.92))}" fill="{color}" opacity="{op}"/>'
                   for i in range(layers))


# ───────────────────────── 场景窗 ─────────────────────────
def window(x, y, w, h, label, clips, t_on, night=False, dim=None, label_at=None, frame_at=None, bounce=None):
    """clips = [dict(name, n, a, b, mode='loop'|'once', fps)]：a~b 秒内显示。
    t_on：线框画出 + 画面亮起（她落进来的那一刻）。dim = (秒, 透明度)：她离开后压暗。"""
    lc = NIGHT_LINE if night else INK
    per = 2 * (w + h + 32)
    frame = (f'<rect x="{f(x - 8)}" y="{f(y - 8)}" width="{f(w + 16)}" height="{f(h + 16)}" fill="none" stroke="{lc}" stroke-width="1" '
             f'stroke-dasharray="{f(per)}" stroke-dashoffset="{f(per)}">'
             f'<animate attributeName="stroke-dashoffset" values="{f(per)};0" begin="{f(t_on if frame_at is None else frame_at)}s" dur="0.5s" fill="freeze"/></rect>')
    lab = show_once(TP.draw(label, x - 8, y - 24, 22, "light", fill=NIGHT_TXT if night else GREY), label_at or max(t_on - 0.5, 0))
    layers = ""
    for c in clips:
        n, fps = c["n"], c.get("fps", 6)
        n = min(n, 5)
        frames = [f"winL/{c['name']}_{k}.jpg" for k in range(n)]
        if LITE and not c.get("all"):
            frames = [frames[0], frames[-1]] if n > 1 else frames
            n = len(frames)
            fps = min(fps, 0.8) if c.get("mode", "loop") == "loop" else n / max(n / fps, 1.2)
        if c.get("mode", "loop") == "loop":
            order = list(range(n)) + list(range(n - 2, 0, -1))
            body = flip(frames, x, y, w, h, order, fps=fps, begin=f"{f(c['a'])}s")
        else:  # 播一遍，停在最后一帧
            dur = n / fps
            body = ""
            for k, fr in enumerate(frames):
                if k < n - 1:
                    vals, kts = "0;1;0", f"0;{f(k / n)};{f((k + 1) / n)}"
                else:
                    vals, kts = "0;1", f"0;{f(k / n)}"
                body += img(fr, x, y, w, h, ' opacity="0"',
                            f'<animate attributeName="opacity" values="{vals}" keyTimes="{kts}" dur="{f(dur)}s" begin="{f(c["a"])}s" calcMode="discrete" fill="freeze"/>')
        sets = f'<set attributeName="opacity" to="1" begin="{f(c["a"])}s" fill="freeze"/>'
        if c.get("b") is not None:
            sets += f'<set attributeName="opacity" to="0" begin="{f(c["b"])}s" fill="freeze"/>'
        layers += f'<g opacity="0">{sets}{body}</g>'
    fade = f'<animate attributeName="opacity" values="0;1" begin="{f(t_on)}s" dur="0.22s" fill="freeze"/>'
    veil = ""
    if dim:
        veil = (f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{NIGHT if night else PAPER}" opacity="0">'
                f'<animate attributeName="opacity" values="0;{dim[1]}" begin="{f(dim[0])}s" dur="0.4s" fill="freeze"/></rect>')
    out = frame + lab + f'<g opacity="0">{fade}{layers}</g>' + veil
    if bounce is not None:
        out = (f'<g><animateTransform attributeName="transform" type="translate" values="0 0;0 10;0 -3;0 0" keyTimes="0;0.35;0.7;1" '
               f'begin="{f(bounce)}s" dur="0.32s"/>{out}</g>')
    return out


def draw_on(d, L, t, dur=0.5, op=0.75, sw_=1.3, col=None):
    """一条发丝线，到 t 秒自己画出来。"""
    return (f'<path d="{d}" fill="none" stroke="{col or NIGHT_TXT}" stroke-width="{sw_}" stroke-linecap="round" stroke-linejoin="round" opacity="{op}" '
            f'stroke-dasharray="{L}" stroke-dashoffset="{L}"><animate attributeName="stroke-dashoffset" values="{L};0" begin="{f(t)}s" dur="{dur}s" fill="freeze"/></path>')


SOFA_SD, SOFA_SF = 104, 142                    # 坐垫厚、地面


def sofa_lines(L2, t, xl=84, xr=666, aw=54, back=112):
    """发丝线沙发：L2 = 坐垫面。靠背、两个扶手、坐垫前沿和中缝、腿、地面，依次画出来。"""
    SD, SF = SOFA_SD, SOFA_SF
    al, ar = xl - aw, xr + aw
    m = (xl + xr) / 2
    return (draw_on(f"M{xl} {f(L2)} V{f(L2 - back + 28)} Q{xl} {f(L2 - back)} {xl + 28} {f(L2 - back)} H{xr - 28} Q{xr} {f(L2 - back)} {xr} {f(L2 - back + 28)} V{f(L2)}", 900, t, 0.6)
            + draw_on(f"M{xl} {f(L2 + SD)} H{al + 10} Q{al} {f(L2 + SD)} {al} {f(L2 + SD - 10)} V{f(L2 - 46)} Q{al} {f(L2 - 62)} {al + 16} {f(L2 - 62)} H{xl - 16} Q{xl} {f(L2 - 62)} {xl} {f(L2 - 46)} V{f(L2 + SD)}", 520, t + 0.05, 0.5)
            + draw_on(f"M{xr} {f(L2 + SD)} H{ar - 10} Q{ar} {f(L2 + SD)} {ar} {f(L2 + SD - 10)} V{f(L2 - 46)} Q{ar} {f(L2 - 62)} {ar - 16} {f(L2 - 62)} H{xr + 16} Q{xr} {f(L2 - 62)} {xr} {f(L2 - 46)} V{f(L2 + SD)}", 520, t + 0.1, 0.5)
            + draw_on(f"M{xl} {f(L2 + SD)} H{xr} M{f(m)} {f(L2 + 8)} V{f(L2 + SD)}", 700, t + 0.2, 0.5, op=0.6)
            + draw_on(f"M{xl - 22} {f(L2 + SD)} V{f(L2 + SF)} M{xr + 22} {f(L2 + SD)} V{f(L2 + SF)}", 90, t + 0.4, 0.3)
            + draw_on(f"M24 {f(L2 + SF)} H{W - 24}", 720, t + 0.3, 0.6, op=0.4, sw_=1))


def hug_body(x, y, w):
    """结尾：她搂着阿卡。层次 = 补好臂弯的底图 → 阿卡 → 下面那只手臂（压住它的脚）→ 两只手（绕手腕转到阿卡身上）。
    素材和位置都由 work/hug_fill.py 生成（assets/hug.json）。"""
    cfg = json.loads((HERE / "assets/hug.json").read_text())
    k = w / 640
    hh = w * size("hugP_base.png")[1] / size("hugP_base.png")[0]
    aw = cfg["aka_w"]
    dx, dy = 0.0, 0.3375 * aw                # 红点相对阿卡中心
    aka = (img("aka3d/aka_squat_sleep.png", -aw * 380 / 480, -aw * 400 / 480, aw * 380 / 240, aw * 400 / 240)
           + f'<circle cx="{f(dx)}" cy="{f(dy)}" r="3.4" fill="{RED}"><animate attributeName="opacity" values="1;0.2;1" dur="2.4s" begin="0s" repeatCount="indefinite"/></circle>'
           + f'<g transform="translate({f(dx)} {f(dy)})"><g>'
             f'<animateTransform attributeName="transform" type="scale" values="1;4.6" dur="2.4s" begin="0s" repeatCount="indefinite"/>'
             f'<circle cx="0" cy="0" r="3" fill="none" stroke="{RED}" stroke-width="0.4" opacity="0">'
             f'<animate attributeName="opacity" values="0.7;0" dur="2.4s" begin="0s" repeatCount="indefinite"/></circle></g></g>')
    r0 = cfg["aka_rot"]
    out = (img("hugP_base.png", 0, 0, 640, 169)
           + f'<g transform="translate({cfg["aka_c"][0]} {cfg["aka_c"][1]})"><g transform="rotate({r0})">'
             f'<animateTransform attributeName="transform" type="rotate" values="{r0};{r0 + 1.5};{r0}" dur="3.6s" begin="0s" repeatCount="indefinite"/>{aka}</g></g>'
           + img("hugP_armLow.png", 0, 0, 640, 169))
    for hn in ("handL", "handR"):
        h = cfg[hn]; x0, y0, x1, y1 = h["box"]
        out += (f'<g transform="translate({h["shift"][0]} {h["shift"][1]}) rotate({h["rot"]} {h["pivot"][0]} {h["pivot"][1]})">'
                + img(f"hugP_{hn}.png", x0 - 2, y0 - 2, x1 - x0 + 4, y1 - y0 + 4) + '</g>')
    return f'<g transform="translate({f(x)} {f(y)}) scale({f(k)})">{out}</g>'


def pillow(x0, x1, base, h, night=True):
    """发丝线画的枕头（底色稍亮一点，压在线上）。"""
    m = (x0 + x1) / 2
    d = (f"M{f(x0 + 6)} {f(base)} Q{f(x0 - 10)} {f(base - h * 0.55)} {f(x0 + 22)} {f(base - h * 0.9)} "
         f"Q{f(m)} {f(base - h * 1.12)} {f(x1 - 22)} {f(base - h * 0.9)} Q{f(x1 + 10)} {f(base - h * 0.55)} {f(x1 - 6)} {f(base)} Z")
    crease = f"M{f(x0 + 34)} {f(base - h * 0.62)} Q{f(m)} {f(base - h * 0.5)} {f(x1 - 40)} {f(base - h * 0.66)}"
    return (f'<path d="{d}" fill="#474C46" stroke="{NIGHT_TXT}" stroke-width="1.3" stroke-linejoin="round" opacity="0.85"/>'
            f'<path d="{crease}" fill="none" stroke="{NIGHT_TXT}" stroke-width="1" stroke-linecap="round" opacity="0.45"/>')


def inside_any(x, y, rects, pad=6):
    return any(rx - pad <= x <= rx + rw + pad and ry - pad <= y <= ry + rh + pad for rx, ry, rw, rh in rects)


def thread_path(keys, rects, color, op=0.75):
    """线索：她的轨迹，按时间同步画出；落在场景窗里的部分不画（分段）。"""
    out = []
    segs, cur = [], []
    for k in keys:
        if inside_any(k[1], k[2], rects):
            if len(cur) > 1:
                segs.append(cur)
            cur = []
        else:
            cur.append(k)
    if len(cur) > 1:
        segs.append(cur)
    for sg in segs:
        L = [0.0]
        for p, q in zip(sg, sg[1:]):
            L.append(L[-1] + math.hypot(q[1] - p[1], q[2] - p[2]))
        tot = L[-1]
        if tot < 20:
            continue
        t0, t1 = sg[0][0], sg[-1][0]
        D = t1 + 0.001
        ts = [0.0] + [k[0] for k in sg]
        offs = [tot] + [tot - l for l in L]
        d = "M" + " L".join(f"{f(k[1])} {f(k[2])}" for k in sg)
        out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.4" opacity="{op}" stroke-linecap="round" '
                   f'stroke-dasharray="{f(tot)} {f(tot + 10)}" stroke-dashoffset="{f(tot)}">'
                   f'<animate attributeName="stroke-dashoffset" values="{";".join(f(o) for o in offs)}" keyTimes="{kt(ts, D)}" '
                   f'dur="{f(D)}s" begin="0s" fill="freeze"/></path>')
    return "".join(out)


def say_at(who, text, x, y, t, night=False, anchor="start", size_=31, name=True, small=False):
    if small:
        size_ = 24
    return appear(say(who, text, x, y, size=size_, night=night, anchor=anchor, name=name), t)


# ───────────────────────── 构建 ─────────────────────────
def build():
    bg_els, els, top_els = [], [], []
    add = els.append
    rects = []          # 场景窗矩形（线索不画进去）
    REV = []            # (秒, 页面推到的 y)
    her_keys_all = []   # 线索用
    S_A, S_B = pose_or("swA", "st3"), pose_or("swB", "st3")
    S_C = pose_or("coatC", "st1")

    # ── 幕 0 题头
    add(appear(TP.draw("小耳和阿卡的一天", W / 2, 118, 52, "song", fill=INK, anchor="middle", spacing=0.12), 0.2, 0.9))
    add(appear(TP.draw("第一回 · 从 07:40 到 01:20", W / 2, 166, 20, "light", fill=GREY, anchor="middle", spacing=0.2), 0.6, 0.9))
    add(f'<g><set attributeName="opacity" to="0" begin="0.05s" fill="freeze"/>'
        + TP.draw("正在把这一天装进来……", W / 2, 166, 20, "light", fill=GREY, anchor="middle", spacing=0.15) + '</g>')

    # ── 幕 1 闹钟响，她不起（1.0–6.0）
    LINE1 = 700
    bw = 540
    bh = bw * size("bed_lying.png")[1] / size("bed_lying.png")[0]
    bx, by = 34, LINE1 - bh + 3
    add(f'<line x1="24" y1="{LINE1}" x2="{W - 24}" y2="{LINE1}" stroke="{INK}" stroke-width="2"/>')
    add(TP.draw("07:40", 24, LINE1 + 32, 22, "light", fill=GREY))
    bed_states = [("bed_lying", 0, 2.0)]
    if has("bed_reach.png"):
        bed_states += [("bed_reach", 2.0, 2.6), ("bed_lying", 2.6, None)]
    else:
        bed_states[0] = ("bed_lying", 0, None)
    bed = ""
    for name, a, b in bed_states:
        inner = ""
        if a:
            inner += f'<animate attributeName="opacity" values="0;1" begin="{a}s" dur="0.15s" fill="freeze"/>'
        if b:
            inner += f'<animate attributeName="opacity" values="1;0" begin="{b}s" dur="0.15s" fill="freeze"/>'
        bed += img(f"{name}.png", bx, by - LINE1, bw, bh, ' opacity="0"' if a else "", inner)
    # 她在呼吸：以床脚线为底，纵向轻轻起伏
    add(f'<g transform="translate(0 {LINE1})"><g><animateTransform attributeName="transform" type="scale" values="1 1;1 1.012;1 1" '
        f'dur="3.2s" begin="0s" repeatCount="indefinite"/>{bed}</g></g>')
    # 屋里的东西用发丝线画：床头柜、墙上的窗和窗帘、床下的拖鞋（人和床是厚涂，其余是手稿线）
    nx0, nx1, ny = 590, 716, LINE1 - 66
    room = (draw_on(f"M{nx0 - 8} {ny} H{nx1 + 8} M{nx0} {ny} V{LINE1} M{nx1} {ny} V{LINE1} M{nx0} {ny + 26} H{nx1} M{(nx0 + nx1) // 2 - 9} {ny + 13} H{(nx0 + nx1) // 2 + 9}", 420, 0.0, 0.4, op=0.8, sw_=1.4, col=INK)
            + draw_on(f"M640 216 H500 V366 H640 M580 216 V366 M500 291 H640", 1100, 0.3, 0.9, op=0.5, sw_=1.2, col=GREY)
            + draw_on(f"M484 204 H692 M650 204 Q632 270 644 322 Q650 356 634 384 M688 204 Q696 300 684 384 M634 384 H684 M664 206 Q668 300 660 382", 760, 0.7, 0.8, op=0.5, sw_=1.2, col=GREY)
            + draw_on(f"M488 366 H640", 220, 0.9, 0.4, op=0.5, sw_=1.2, col=GREY)
            + draw_on(f"M300 {LINE1 - 3} Q300 {LINE1 - 15} 322 {LINE1 - 15} Q346 {LINE1 - 15} 350 {LINE1 - 3} M312 {LINE1 - 14} Q318 {LINE1 - 6} 330 {LINE1 - 3} "
                      "", 130, 1.0, 0.4, op=0.75, sw_=1.3, col=INK)
            + f'<g transform="translate(8 2) rotate(-12 385 {LINE1 - 3})">'
            + draw_on(f"M362 {LINE1 - 3} Q362 {LINE1 - 13} 382 {LINE1 - 13} Q404 {LINE1 - 13} 408 {LINE1 - 3} M373 {LINE1 - 12} Q379 {LINE1 - 6} 390 {LINE1 - 3}", 130, 1.15, 0.4, op=0.75, sw_=1.3, col=INK) + '</g>')
    add(room)
    # 闹钟
    T_R0, T_R1 = 1.0, 3.25
    cw_ = 108
    chh = cw_ * size("clock.png")[1] / size("clock.png")[0]
    NS = 66                                    # 床头柜高
    ccx, ccy = 652, LINE1 - NS - chh / 2
    nr = int((T_R1 - T_R0) / 0.32)
    add(f'<g transform="translate({f(ccx)} {f(ccy)})"><g><animateTransform attributeName="transform" type="translate" values="0 0;0 -7;0 0;0 -4;0 0" '
        f'begin="{T_R0}s" dur="0.24s" repeatCount="{int((T_R1 - T_R0) / 0.24)}"/><g><animateTransform attributeName="transform" type="rotate" '
        f'values="0;-9;8;-10;9;-8;10;-7;0" begin="{T_R0}s" dur="0.32s" repeatCount="{nr}"/>{img("clock.png", -cw_ / 2, -chh / 2, cw_, chh)}</g></g></g>')
    for i in range(5):
        for side in (-1, 1):
            r = 20 + i * 10
            x0, y0 = ccx + side * (cw_ / 2 - 6), ccy - chh * 0.28
            d = f"M{f(x0 + side * r * 0.35)} {f(y0 - r * 0.8)} Q{f(x0 + side * r)} {f(y0)} {f(x0 + side * r * 0.35)} {f(y0 + r * 0.8)}"
            add(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="1" stroke-linecap="round" opacity="0">'
                f'<animate attributeName="opacity" values="0;0.8;0" begin="{f(T_R0 + i * 0.07)}s" dur="0.36s" repeatCount="{int((T_R1 - T_R0 - i * 0.07) / 0.36)}"/></path>')
    for j, ch in enumerate("铃铃铃铃铃铃"):
        g = TP.draw(ch, 0, 0, 22 if ch != "—" else 16, "light", fill=GREY)
        add(f'<g transform="translate({500 + j * 26} {f(LINE1 - NS - chh - 44 - (j % 2) * 12)})" opacity="0">'
            f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.06;0.97;1" begin="{f(T_R0 + j * 0.12)}s" dur="{f(T_R1 - T_R0 - j * 0.12)}s" fill="freeze"/>'
            f'<g><animateTransform attributeName="transform" type="translate" values="0 0;-2 -3;3 1;-1 2;0 0" dur="0.2s" begin="{T_R0}s" repeatCount="11"/>{g}</g></g>')
    # 阿卡：床头板蹲着 → 烦（低头）→ 跳上闹钟一屁股坐停 → 跳到枕边踩她脑袋 4 下 → 之后每 6 秒踩一下
    sq_w = 74
    sq_body, sq_h = aka_3d(sq_w, "aka_squat.png", acts=[("wave", 3.5, 4.25), ("stomp", 5.0, 6.2), ("wave", 7.0, 7.75), ("wave", 10.6, 11.35)])
    p_hb = (bx + bw * 0.055, by + bh * 0.34 - sq_h / 2 + 4)
    p_clock = (ccx - 4, ccy - chh / 2 - sq_h / 2 + 8)
    p_pillow = (bx + bw * 0.22, by + bh * 0.42 - sq_h / 2)
    ak = [(0, p_hb[0], p_hb[1], 1, 0, 1), (1.5, p_hb[0], p_hb[1], 1, 0, 1), (1.7, p_hb[0], p_hb[1], 1, -6, 1), (2.9, p_hb[0], p_hb[1], 1, -6, 1)]
    ak += hop(p_hb, p_clock, 3.0, 0.45, height=110)[1:]
    ak += [(3.5, p_clock[0], p_clock[1] + 6, 1.05, 0, 1), (4.4, p_clock[0], p_clock[1], 1, 0, 1)]
    ak += hop(p_clock, p_pillow, 4.5, 0.45, height=90)[1:]
    for i in range(4):   # 踩 4 下
        t = 5.0 + i * 0.3
        ak += [(t + 0.15, p_pillow[0], p_pillow[1] + 10, 1.04, 0, 1), (t + 0.3, p_pillow[0], p_pillow[1], 1, 0, 1)]
    ak += [(11.0, p_pillow[0], p_pillow[1], 1, 0, 1), (11.3, p_pillow[0], p_pillow[1], 1, 0, 0)]  # 第二幕起它在窗里
    ak = idle(ak, 3.5, 4.4, period=0.5, dr=5)
    ak = idle(ak, 6.2, 11.0, period=1.3, hops=(7.0, 10.6))
    add(track(sq_body, ak))
    # 闹钟被坐停那一下：小抖一下 + 一道短横线
    imp = "".join(f'<line x1="{f(ccx + d * 52)}" y1="{f(ccy - chh * 0.42)}" x2="{f(ccx + d * 74)}" y2="{f(ccy - chh * 0.48)}" stroke="{INK}" stroke-width="1.6" stroke-linecap="round"/>' for d in (-1, 1))
    add(show_once(imp, 3.45, 3.75, fade=0.1))
    add(say_at("阿卡", "起来。", 40, 262, 3.5))
    add(appear(say("小耳", "五分钟……", 160, 312, size=24, name=True).replace(f'fill="{INK}"', f'fill="{GREY}"'), 4.0))
    add(say_at("阿卡", "九点有会。", 40, 368, 5.5))
    REV.append((0.0, LINE1 + 90))

    # ── 幕 2 阿卡扎头发、插叶子（6.0–11.5）
    HAIR_Y = LINE1 + 150
    rects.append((WX, HAIR_Y, WW, WH))
    REV.append((6.0, HAIR_Y + WH + 90))
    add(window(WX, HAIR_Y, WW, WH, "07:52 · 再睡要迟到了",
               [dict(name="hair", n=8, a=6.4, b=9.8, mode="once", fps=3.1), dict(name="wake", n=6, a=9.8, b=None, mode="once", fps=6)],
               t_on=6.2, dim=(11.6, 0.25)))
    # 叶子：右上角飘下来，转两圈插进发髻
    lx, ly = WX + 262, HAIR_Y + 158
    lk = [(8.5, W - 70, HAIR_Y - 90, 1, -200, 0), (8.6, W - 70, HAIR_Y - 90, 1, -200, 1)]
    for i in range(1, 11):
        u = i / 10
        lk.append((8.6 + 0.8 * u, W - 70 + (lx - W + 70) * (1 - (1 - u) ** 2) + 30 * math.sin(math.pi * u * 2),
                   HAIR_Y - 90 + (ly - HAIR_Y + 90) * u, 1 - 0.55 * u, -200 + 200 * u, 1))
    lk += [(9.8, lx, ly, 0.45, 0, 1), (9.85, lx, ly, 0.45, 0, 0)]
    add(track(leaf(0, 0, 2.0, -35), lk))
    burst = "".join(f'<line x1="{f(lx + 8 + 16 * math.cos(a))}" y1="{f(ly - 6 + 16 * math.sin(a))}" x2="{f(lx + 8 + 28 * math.cos(a))}" '
                    f'y2="{f(ly - 6 + 28 * math.sin(a))}" stroke="{GOLD}" stroke-width="1.8" stroke-linecap="round"/>' for a in [-2.4, -1.6, -0.8, 0.1])
    add(show_once(burst, 9.4, 9.75, fade=0.12))
    add(say_at("阿卡", "别动。", 40, HAIR_Y + WH + 58, 7.0))
    shout = TP.draw("啊！", 0, 0, 44, "kai", fill=INK)
    add(f'<g transform="translate({WX + 470} {HAIR_Y + 70})" opacity="0"><set attributeName="opacity" to="1" begin="10.0s" fill="freeze"/>'
        f'<animate attributeName="opacity" values="1;0.35" begin="11.6s" dur="0.4s" fill="freeze"/>'
        f'<g><animateTransform attributeName="transform" type="translate" values="0 0;-3 2;3 -2;-2 -1;0 0" begin="10.0s" dur="0.2s" repeatCount="2"/>{shout}</g></g>')
    add(say_at("阿卡", "早说了。", 40, HAIR_Y + WH + 110, 10.6))

    # ── 幕 3 第一次下坠：空中穿衣（11.5–18.2）
    DOOR_Y = HAIR_Y + WH + 1150
    wake_spot = dict(x=WX + 380, y=HAIR_Y + 200, s=1.12, r=0)
    door_spot = dict(x=WX + 400, y=DOOR_Y - 30, s=1.0, r=0)       # 落到窗顶边就消失，窗接住她
    T3, t3 = 6.7, 11.5

    def rot3(u):
        t = T3 * u
        wob = 6 * math.sin(2 * math.pi * t / 1.4) * (1 if t < 2.0 else 0.3)
        flipc = 90 * math.sin(math.pi * min(max((t - 3.0) / 1.6, 0), 1)) if t > 3.0 else 0
        return wob + flipc
    k3, pos3 = fall_path(wake_spot, door_spot, t3, T3,
                         curve=[(0, 0, None), (2.0 / T3, 0.11, "in"), (5.0 / T3, 0.66, None), (1, 1, "out")],
                         drift=150, rot=rot3, bulge=0.1, op_in=0.3, op_out=0.2)
    spans3 = [(S_A, t3, t3 + 2.0), (S_B, t3 + 2.0, t3 + 3.0), (S_C, t3 + 3.0, t3 + 3.8), ("st1", t3 + 3.8, t3 + 4.3),
              ("bp_fall1", t3 + 4.3, t3 + 5.1), ("st2", t3 + 5.1, t3 + 5.7), ("st4", t3 + 5.7, t3 + T3 + 0.1)]
    add(her(pop(k3, pos3, [t3 + 2.0, t3 + 3.0, t3 + 3.8, t3 + 4.3, t3 + 5.1, t3 + 5.7]), spans3))
    her_keys_all.append(k3)
    # 阿卡：从窗里她肩头跳出，在她上方 60px 抱着外套跟着掉 → 甩外套 → 翻滚 → 俯冲接鞋 → 送手机 → 落进玄关长凳
    akw = 64
    a_body, a_h = aka_img(akw)

    def near(t, dx, dy):
        x, y, s, r = pos3(t)
        return x + dx, y + dy
    ka = []
    for t in [11.8, 12.3, 12.8, 13.3, 13.5]:
        x, y = near(t, -70, -190)
        ka.append((t, x, y, 1, 8 * math.sin(t * 3), 1 if t > 11.8 else 0))
    for i, t in enumerate([13.9, 14.3, 14.7]):      # 甩完外套，往旁边翻滚一圈
        x, y = near(t, -150, -120)
        ka.append((t, x, y, 1, 120 * (i + 1), 1))
    for t in [15.1, 15.5]:
        x, y = near(t, -120, -60)
        ka.append((t, x, y, 1, 360, 1))
    x, y = near(15.9, -20, -175)                    # 一爪按住被风掀起的叶子
    ka.append((15.9, x, y, 1, 350, 1))
    x, y = near(16.2, -50, -170)
    ka.append((16.2, x, y, 1, 360, 1))
    for t in [16.6, 17.0]:                          # 抱着手机追上来
        x, y = near(t, 110, -40)
        ka.append((t, x, y, 1, 360, 1))
    x, y = near(17.3, 120, -60)
    ka.append((17.3, x, y, 1, 360, 1))
    bench = (WX + 300, DOOR_Y + 292)
    ka += [(17.9, bench[0], bench[1] - 10, 0.8, 360, 1), (18.4, bench[0], bench[1], 0.75, 360, 0)]
    add(track(a_body, ka))
    # 外套：跟着阿卡 → 13.5 甩出 → 14.5 碰到她（她换成半穿外套的姿态）
    if has("prop_coat.png"):
        kc = [(t, x + 10, y + 30, 0.55, r, o if t >= 13.3 else 0) for (t, x, y, s, r, o) in ka if t <= 13.5]
        tx, ty = near(14.5, 0, 0)[0], near(14.5, 0, 0)[1]
        x0, y0 = kc[-1][1], kc[-1][2]
        for i in range(1, 7):
            u = i / 6
            kc.append((13.5 + u, x0 + (tx - x0) * u, y0 + (ty - y0) * u - 50 * math.sin(math.pi * u), 0.55 + 0.35 * u, 200 * u, 1))
        kc.append((14.52, tx, ty, 0.9, 200, 0))
        add(track(prop_img("prop_coat.png", 260), kc))
    # 叶子：15.4 被风从发髻上掀起来 → 15.9 阿卡一爪按住 → 16.2 按回发髻
    lf = []
    for t, dx, dy in [(15.35, -14, -128), (15.45, -14, -128), (15.65, 30, -200), (15.9, -10, -185), (16.2, -14, -130)]:
        x, y = near(t, dx, dy)
        lf.append((t, x, y, 1.6, (t - 15.35) * 500, 0 if t == 15.35 else 1))
    x, y = near(16.35, -14, -128)
    lf.append((16.35, x, y, 1.6, 0, 0))
    add(track(leaf(0, 0, 1.0, -35), lf))
    # 手机：16.6 阿卡抱着 → 17.25 塞到她手里
    if has("prop_phone.png"):
        kp = [(t, x + 26, y + 14, 0.8, 0, (1 if t >= 16.6 else 0)) for (t, x, y, s, r, o) in ka if 16.2 <= t <= 18.4]
        kp[-1] = kp[-1][:5] + (0,)
        add(track(prop_img("prop_phone.png", 80), kp))
    # 空中对白（跟着她走的一侧摆）
    moved = 0
    last_yy = -999
    for t, who, text in [(12.3, "阿卡", "醒醒。"), (14.5, "阿卡", "外套。"), (15.9, "阿卡", "叶子。"), (18.0, "阿卡", "卡。")]:
        x, y, s, r = pos3(t)
        right = x < W / 2
        yy = max(y - 40, HAIR_Y + WH + 175, last_yy + 60)      # 不和上一句叠在一起
        last_yy = yy
        if DOOR_Y - 60 < yy < DOOR_Y + WH + 30:      # 别压进玄关窗：挪到窗上方，依次错开一行
            yy = DOOR_Y - 122 + 52 * moved
            moved += 1
        off = 230 if text == "外套。" else 170
        add(say_at(who, text, (x + off) if right else (x - off), yy, t, anchor="start" if right else "end"))
    REV += [(k[0], k[2] + 560) for k in k3[2::2]]

    # ── 幕 4 玄关（18.2–23.0）+ 镜子小窗
    rects.append((WX, DOOR_Y, WW, WH))
    MX, MY, MW, MH = W - 40 - 300, DOOR_Y + WH + 38, 300, 400
    add(window(WX, DOOR_Y, WW, WH, "08:50 · 玄关",
               [dict(name="doorB", n=4, a=18.15, b=23.2, mode="once", fps=1.0), dict(name="empty", n=6, a=23.2, b=None, mode="loop", fps=4)],
               t_on=18.15, frame_at=17.6, bounce=18.25))
    add(catch_dust(WX + 400, DOOR_Y, 18.25, INK))
    # 镜子：从右边滑进来；23.2 淡出（人走了）
    mirror = (f'<rect x="{MX - 8}" y="{MY - 8}" width="{MW + 16}" height="{MH + 16}" fill="none" stroke="{INK}" stroke-width="1"/>'
              + f'<path d="M{MX + 30} {MY + MH + 8} V{MY + MH + 28} M{MX + MW - 30} {MY + MH + 8} V{MY + MH + 28} M{MX - 14} {MY + MH + 28} H{MX + MW + 14}" fill="none" stroke="{INK}" stroke-width="1.3" stroke-linecap="round"/>'
              + flip([f"winL/mirror_{k}.jpg" for k in (0, 4)], MX, MY, MW, MH, [0, 1], fps=0.8, begin="20.0s"))
    add(f'<g opacity="0"><set attributeName="opacity" to="1" begin="20.0s" fill="freeze"/>'
        f'<animate attributeName="opacity" values="1;0" begin="23.2s" dur="0.5s" fill="freeze"/>'
        f'<animateTransform attributeName="transform" type="translate" values="120 0;0 0" begin="20.0s" dur="0.45s" fill="freeze" {E}/>'
        f'{mirror}</g>')
    add(say_at("阿卡", "慢死了。", 40, DOOR_Y + WH + 60, 19.5))
    add(say_at("小耳", "走了走了！", 40, DOOR_Y + WH + 112, 21.5))
    REV.append((20.0, MY + MH + 90))

    # ── 幕 5 门关上，人没了 → 第二次下坠（23.0–25.8）
    MEET_Y = MY + MH + 440
    door_out = dict(x=WX + 415, y=DOOR_Y + 250, s=1.05, r=0)
    seat_meet = dict(x=WX + 585, y=MEET_Y + 255, s=1.25, r=0)
    meet_top = dict(x=WX + 585, y=MEET_Y - 30, s=1.0, r=0)
    k5, pos5 = fall_path(door_out, meet_top, 23.0, 2.8, drift=-60, rot=lambda u: 25 * math.sin(math.pi * u * 2), bulge=0.12, op_in=0.2, op_out=0.2)
    add(her(pop(k5, pos5, [23.6, 24.4, 25.2]), [("st4", 23.0, 23.6), ("st1", 23.6, 24.4), ("st2", 24.4, 25.2), ("st4", 25.2, 25.9)]))
    her_keys_all.append(k5)
    ka5 = [(23.0, WX + 393, DOOR_Y + 105, 0.9, 0, 0)]
    for t in [23.2, 23.8, 24.4, 25.0, 25.6]:
        x, y, s, r = pos5(t)
        ka5.append((t, x - 175, y - 150 * s, 0.85, -20, 1))
    ka5.append((25.85, WX + 528, MEET_Y + 222, 0.85, 0, 0))
    add(track(aka_img(60, "aka_squat.png")[0], ka5))
    add(say_at("阿卡", "还剩七分钟。", 40, (DOOR_Y + WH + MEET_Y) / 2 + 60, 24.0))
    kx, ky, kr = 104, (DOOR_Y + WH + MEET_Y) / 2 + 140, 38
    ticks = " ".join(f"M{f(kx + (kr - 6) * math.sin(math.radians(a)))} {f(ky - (kr - 6) * math.cos(math.radians(a)))} L{f(kx + (kr - 1) * math.sin(math.radians(a)))} {f(ky - (kr - 1) * math.cos(math.radians(a)))}" for a in range(0, 360, 30))
    hh = math.radians(266.5)
    add(draw_on(f"M{kx} {f(ky - kr)} A{kr} {kr} 0 1 1 {f(kx - 0.1)} {f(ky - kr)}", 245, 24.1, 0.5, op=0.75, sw_=1.3, col=GREY)
        + draw_on(ticks, 6, 24.4, 0.2, op=0.7, sw_=1.2, col=GREY)
        + draw_on(f"M{kx} {f(ky)} L{f(kx + 20 * math.sin(hh))} {f(ky - 20 * math.cos(hh))}", 22, 24.5, 0.2, op=0.9, sw_=1.8, col=INK)
        + f'<g transform="translate({kx} {f(ky)})"><g transform="rotate(318)"><animateTransform attributeName="transform" type="rotate" values="318;318;327;324" keyTimes="0;0.4;0.8;1" begin="24.5s" dur="0.5s" fill="freeze"/>'
        + draw_on(f"M0 0 V{-(kr - 9)}", 30, 24.5, 0.2, op=0.9, sw_=1.4, col=INK) + '</g></g>')
    add(say_at("小耳", "来得及！", 40, MEET_Y - 90, 25.0))
    REV += [(k[0], k[2] + 460) for k in k5[2::2]]

    # ── 幕 6 会议（25.6–）
    rects.append((WX, MEET_Y, WW, WH))
    add(window(WX, MEET_Y, WW, WH, "09:00 · 春季展主视觉讨论", [dict(name="meet", n=8, a=25.75, b=None, mode="loop", fps=6)],
               t_on=25.75, dim=(39.5, 0.25), frame_at=25.2, bounce=25.85))
    add(catch_dust(WX + 585, MEET_Y, 25.85, INK))
    # 谁在说话：三个人嘴边轮流闪一组发丝声纹（位置就是后面飞字的起点）
    for (mx_, my_), tv in zip([(WX + 345, MEET_Y + 205), (WX + 525, MEET_Y + 178), (WX + 268, MEET_Y + 215)], [27.2, 28.3, 29.4]):
        for j, rr in enumerate((11, 19, 27)):
            a0, a1 = math.radians(-125), math.radians(-55)
            d_ = (f"M{f(mx_ + rr * math.cos(a0))} {f(my_ - 6 + rr * math.sin(a0))} "
                  f"A{rr} {rr} 0 0 1 {f(mx_ + rr * math.cos(a1))} {f(my_ - 6 + rr * math.sin(a1))}")
            add(f'<path d="{d_}" fill="none" stroke="#FFF3D6" stroke-width="2.4" stroke-linecap="round" opacity="0">'
                f'<animate attributeName="opacity" values="0;1;0" begin="{f(tv + j * 0.1)}s" dur="0.8s" fill="freeze"/></path>')
    add(show_once(say("阿卡", "你听，我记。", 300, MEET_Y + WH + 70), 26.8, 30.7))

    # ── 幕 7 字飘进录音卡（30.5–36.0）
    S2X, S2Y = WX + 10, MEET_Y + WH + 34
    rects.append((S2X, S2Y, 240, 240))
    add(window(S2X, S2Y, 240, 240, "", [dict(name="s2", n=8, a=30.5, b=None, mode="loop", fps=5)], t_on=30.5))
    CARD_Y = MEET_Y + WH + 320
    cx0, cw0 = 40, 670
    rows = [("09:02", "老板", "今天主要定一下春季展的主视觉。", (WX + 345, MEET_Y + 205), 31.0),
            ("09:03", "小耳", "我先把三个方向的草图过一遍。", (WX + 525, MEET_Y + 178), 32.8),
            ("09:03", "客户", "我们更喜欢第二版的颜色。", (WX + 268, MEET_Y + 215), 34.6)]
    rh, head, summ = 96, 80, 160
    ch_ = head + rh * len(rows) + summ
    grow_t = [0, 30.5] + [r[4] + 0.95 for r in rows] + [36.3, 36.7]
    grow_h = [head + 10, head + 10] + [head + rh * (i + 1) + 10 for i in range(len(rows))] + [head + rh * len(rows) + 10, ch_]
    Dg = grow_t[-1] + 0.001
    card = (f'<rect x="{cx0}" y="{CARD_Y}" width="{cw0}" height="{grow_h[0]}" rx="20" fill="#FFFFFF" stroke="#E3DED3" stroke-width="1">'
            f'<animate attributeName="height" values="{";".join(f(h) for h in grow_h)}" keyTimes="{kt(grow_t, Dg)}" dur="{f(Dg)}s" begin="0s" fill="freeze" '
            f'calcMode="spline" keySplines="{";".join(["0.4 0 0.2 1"] * (len(grow_t) - 1))}"/></rect>'
            f'<circle cx="{cx0 + 34}" cy="{CARD_Y + 40}" r="11" fill="{AKA}"/>'
            + TP.draw("小耳录音卡", cx0 + 54, CARD_Y + 48, 24, "light", fill=INK)
            + TP.draw("· 现场会议", cx0 + 54 + TP.width("小耳录音卡", 24, "light") + 14, CARD_Y + 48, 19, "light", fill=GREY)
            + f'<line x1="{cx0 + 20}" y1="{CARD_Y + 70}" x2="{cx0 + cw0 - 20}" y2="{CARD_Y + 70}" stroke="#E3DED3" stroke-width="1"/>')
    # 录音中：红点 + 跳动的小波形（31.0 起）
    rec = (f'<circle cx="{cx0 + cw0 - 30}" cy="{CARD_Y + 40}" r="7" fill="{RED}"><animate attributeName="opacity" values="1;0.25;1" dur="1.6s" repeatCount="indefinite"/></circle>'
           + TP.draw("录音中", cx0 + cw0 - 44, CARD_Y + 47, 18, "light", fill=RED, anchor="end"))
    for i in range(5):
        bx_ = cx0 + cw0 - 150 + i * 9
        # iPhone 微信：y / height 的循环动画会让整张 svg 的时钟不启动（真机实测），改成 transform 缩放
        rec += (f'<g transform="translate({bx_ + 2} {CARD_Y + 40})"><g transform="scale(1 0.3)">'
                f'<animateTransform attributeName="transform" type="scale" values="1 0.3;1 1;1 0.45;1 0.8;1 0.3" dur="{0.7 + i * 0.13:.2f}s" begin="0s" repeatCount="indefinite"/>'
                f'<rect x="-2" y="-10" width="4" height="20" rx="2" fill="{RED}" opacity="0.55"/></g></g>')
    card += show_once(rec, 30.9, 36.3)
    card += show_once(f'<circle cx="{cx0 + cw0 - 112}" cy="{CARD_Y + 40}" r="7" fill="{AKA}"/>'
                      + TP.draw("已整理", cx0 + cw0 - 30, CARD_Y + 47, 18, "light", fill=AKA, anchor="end"), 36.6)
    lines = []
    for i, (tm, who, text, mouth, st) in enumerate(rows):
        ry = CARD_Y + head + i * rh + 40
        pc = {"老板": "#B4553F", "小耳": AKA, "客户": "#7C7B8C"}[who]
        tag = (TP.draw(tm, cx0 + 22, ry - 24, 19, "light", fill=GREY)
               + f'<rect x="{cx0 + 22}" y="{f(ry - 8)}" width="60" height="32" rx="16" fill="none" stroke="{pc}" stroke-width="1.3"/>'
               + TP.draw(who, cx0 + 52, ry + 14, 18, "light", fill=pc, anchor="middle"))
        card += show_once(tag, st + 1.3)
        lines.append((mouth, (cx0 + 96, ry + 18), text, st))
    # 阿卡整理
    sy0 = CARD_Y + head + rh * len(rows) + 8
    summary = (f'<line x1="{cx0 + 20}" y1="{sy0}" x2="{cx0 + cw0 - 20}" y2="{sy0}" stroke="#E3DED3" stroke-width="1" stroke-dasharray="4 4"/>'
               + TP.draw("阿卡整理", cx0 + 22, sy0 + 40, 19, "light", fill=AKA))
    card += show_once(summary, 36.4)
    for i, t in enumerate(["主视觉：用第二版的配色", "待办：周五前三张图给客户"]):
        yy = sy0 + 82 + i * 46
        L = 30
        card += show_once(f'<path d="M{cx0 + 26} {yy - 8} l7 7 l11 -14" fill="none" stroke="{AKA}" stroke-width="2.8" stroke-linecap="round" '
                          f'stroke-linejoin="round" stroke-dasharray="{L}" stroke-dashoffset="{L}">'
                          f'<animate attributeName="stroke-dashoffset" values="{L};0" begin="{36.8 + i * 0.6}s" dur="0.4s" fill="freeze"/></path>'
                          + TP.draw(t, cx0 + 60, yy, 25, "kai", fill=INK), 36.7 + i * 0.6)

    # ── 幕 9 她离开会议 → 从卡片后面穿过 → 过硬边 → 出租车（39.5–43.0）
    LIDX, LIDW, LIDH = 40, 340, 191
    LID_Y = CARD_Y + ch_ + 84
    EDGE = LID_Y + LIDH + 150
    TAXI_Y = EDGE + 260
    bg_els.append(f'<rect x="0" y="{EDGE}" width="{W}" height="99999" fill="{NIGHT}"/>')
    seat_taxi = dict(x=WX + 250, y=TAXI_Y + 360, s=1.5, r=90)
    taxi_top = dict(x=WX + 250, y=TAXI_Y - 30, s=1.0, r=90)      # 小样：落到窗顶边就消失，窗接住她
    k9, pos9 = fall_path(dict(seat_meet, s=1.0), taxi_top, 39.5, 3.5,
                         curve=[(0, 0, None), (0.55, 0.62, "in"), (1, 1, "in")], drift=0, bulge=0.08, op_in=0.3, op_out=0.2)
    her9 = her(pop(k9, pos9, [40.0, 41.0]), [("st4", 39.5, 40.0), ("st2", 40.0, 41.0), ("st3", 41.0, 43.1)])
    her_keys_all.append(k9)
    rects.append((WX, TAXI_Y, WW, WH))
    add(window(WX, TAXI_Y, WW, WH, "20:10 · 回家路上", [dict(name="taxi", n=8, a=42.3, b=None, mode="loop", fps=6)],
               t_on=42.85, night=True, dim=(45.7, 0.45), frame_at=42.4, bounce=43.0))
    add(show_once("".join(f'<line x1="{f(WX + 250 + d * 70)}" y1="{TAXI_Y - 14}" x2="{f(WX + 250 + d * 120)}" y2="{TAXI_Y - 30}" '
                          f'stroke="{NIGHT_TXT}" stroke-width="1.6" stroke-linecap="round"/>' for d in (-1, 1, -1.5, 1.5)), 43.0, 43.3, fade=0.12))
    REV.append((42.8, TAXI_Y + WH + 110))
    # 车在开：后窗掠过三道暖色流光
    for i, (ln, yy_) in enumerate([(60, 58), (40, 84), (70, 108)]):
        add(f'<g opacity="0"><animate attributeName="opacity" values="0;0.5;0" begin="{f(43.0 + i * 0.3)}s" dur="0.9s" repeatCount="3"/>'
            f'<g transform="translate({WX + WW - ln - 10} {TAXI_Y + yy_})"><animateTransform attributeName="transform" type="translate" values="{WX + WW - ln - 10} {TAXI_Y + yy_};{WX + 320} {TAXI_Y + yy_}" '
            f'begin="{f(43.0 + i * 0.3)}s" dur="0.9s" repeatCount="3"/>'
            f'<line x1="0" y1="0" x2="{ln}" y2="0" stroke="#F0B46A" stroke-width="2" stroke-linecap="round"/></g></g>')
    add(her9)                     # 卡片后画 → 卡片盖住她 = 从界面后面穿过
    add(card)
    rects.append((LIDX, LID_Y, LIDW, LIDH))
    add(window(LIDX, LID_Y, LIDW, LIDH, "19:50 · 下班", [dict(name="lid", n=4, a=38.9, b=None, mode="once", fps=6, all=True)],
               t_on=38.6, dim=(40.4, 0.25)))
    REV.append((38.5, LID_Y + LIDH + 50))
    for (mx, my), (rx, ry), text, st in lines:
        cxp = rx
        for j, chh_ in enumerate(text):
            cw_c = TP.width(chh_, 32, "kai")
            g = TP.draw(chh_, 0, 0, 32, "kai", fill=INK)
            tx_, ty_ = cxp, ry
            cxp += cw_c
            if not g:
                continue
            ta = st + j * 0.075
            lane_x = W - 30
            k_ = [(ta, mx, my, 0.6, (j * 37) % 50 - 25, 0), (ta + 0.08, mx, my, 0.6, (j * 37) % 50 - 25, 0.8),
                  (ta + 0.45, max((mx + lane_x) / 2, 540), (my + ty_) / 2 - 30, 0.75, (j * 23) % 30 - 15, 0.8),
                  (ta + 0.8, lane_x, ty_ - 6, 0.8, 0, 0.85),
                  (ta + 1.15, tx_, ty_, 1.0, 0, 1.0)]
            add(track2(g, k_))
    REV += [(30.5, CARD_Y + head + 60)] + [(r[4] + 1.2, CARD_Y + head + rh * (i + 1) + 60) for i, r in enumerate(rows)] + [(36.3, CARD_Y + ch_ + 120)]
    # 阿卡：36.0 从会议窗跳到卡片右上角 → 点头 → 39.7 跟着她掉，倒挂拽她领子 → 43.0 落到出租车她肩上
    a2w = 64
    a2body, a2h = aka_img(a2w)
    p_meet_aka = (WX + 528, MEET_Y + 222)
    p_card = (cx0 + cw0 - 64, CARD_Y - a2h / 2 + 6)
    kk = [(35.9, p_meet_aka[0], p_meet_aka[1], 0.9, 0, 0), (36.0, p_meet_aka[0], p_meet_aka[1], 0.9, 0, 1)]
    kk += hop(p_meet_aka, p_card, 36.0, 0.8, height=80, s0=0.9, s1=1.0)[1:]
    kk += [(36.9, p_card[0], p_card[1] + 5, 0.9, 0, 1), (37.02, p_card[0], p_card[1], 1.04, 0, 1), (37.12, p_card[0], p_card[1], 1, 0, 1)]
    for i in range(2):  # 点两下头
        kk += [(38.0 + i * 0.4, p_card[0], p_card[1], 1, -8, 1), (38.2 + i * 0.4, p_card[0], p_card[1], 1, 4, 1)]
    kk.append((39.7, p_card[0], p_card[1], 1, 0, 1))
    kk = idle(kk, 37.12, 38.0, period=0.6)
    kk = idle(kk, 38.6, 39.7, period=0.7)
    kk.append((39.95, p_card[0] - 40, p_card[1] + 30, 0.9, 40, 0))          # 一头扎到卡片后面
    for t in [40.3, 40.7, 41.0, 41.3, 41.7, 42.0, 42.3, 42.5]:
        x, y, s, r = pos9(t)
        vis = (y - 120 * s) > CARD_Y + ch_ + 70 and t < 42.5
        kk.append((t, x + 140, y - 120 * s, 1, 180 if t >= 41.0 else 90, 1 if vis else 0))
    add(track(a2body, kk))
    add(gone(say_at("阿卡", "记好了。", W - 150, CARD_Y - 34, 38.0, anchor="end"), 39.5))
    add(gone(say_at("小耳", "……啊？", 300, S2Y + 150, 38.8), 39.5))
    add(say_at("小耳", "好累……", 40, EDGE - 60, 39.8))
    add(say_at("小耳", "……到家叫我。", 40, TAXI_Y + WH + 62, 43.5, night=True))
    add(say_at("阿卡", "哼。", W - 40, TAXI_Y + WH + 62, 44.3, night=True, anchor="end"))
    zz = TP.draw("z", 0, 0, 26, "kai", fill=NIGHT_TXT)
    add(f'<g opacity="0"><set attributeName="opacity" to="1" begin="44.9s" fill="freeze"/><g transform="translate({WX + 400} {TAXI_Y + 190})"><animateTransform attributeName="transform" type="translate" '
        f'values="{WX + 400} {TAXI_Y + 190};{WX + 420} {TAXI_Y + 140}" dur="1.6s" begin="44.9s" repeatCount="indefinite"/>'
        f'<g><animate attributeName="opacity" values="0;1;0" dur="1.6s" begin="44.9s" repeatCount="indefinite"/>{zz}</g></g></g>')
    REV += [(k[0], k[2] + 480) for k in k9[2::2]]
    REV.append((39.3, EDGE + 200))

    # ── 幕 10 到家（45.0–48.0）
    HOME_Y = TAXI_Y + WH + 400
    home_door = dict(x=WX + 565, y=HOME_Y + 228, s=0.98, r=0)
    home_top = dict(x=WX + 565, y=HOME_Y - 30, s=0.98, r=0)
    k10, pos10 = fall_path(dict(x=seat_taxi["x"], y=seat_taxi["y"], s=1.4, r=0), home_top, 45.6, 1.0, drift=100, bulge=0.08, op_in=0.2, op_out=0.2)
    add(her(k10, [("st3", 45.6, 46.1), ("st4", 46.1, 46.7)]))
    her_keys_all.append(k10)
    rects.append((WX, HOME_Y, WW, WH))
    add(window(WX, HOME_Y, WW, WH, "22:40 · 到家", [dict(name="home", n=5, a=46.55, b=None, mode="once", fps=3.0)],
               t_on=46.55, night=True, dim=(48.1, 0.45), frame_at=46.05, bounce=46.65))
    add(catch_dust(WX + 565, HOME_Y, 46.65, NIGHT_TXT))
    ka10 = [(45.6, WX + 372, TAXI_Y + 218, 0.9, 0, 0)]
    for t in [45.8, 46.1, 46.4]:
        x, y, s, r = pos10(t)
        ka10.append((t, x + 130, y - 120, 0.85, 0, 1))
    ka10.append((46.7, WX + 585, HOME_Y + 148, 0.7, 0, 0))
    add(track(aka_img(60, "aka_squat.png")[0], ka10))
    add(say_at("阿卡", "鞋。", W - 40, HOME_Y + WH + 62, 47.0, night=True, anchor="end"))
    add(say_at("小耳", "呼……", 40, HOME_Y + WH + 62, 47.6, night=True))
    REV += [(k[0], k[2] + 440) for k in k10[2::2]]
    REV.append((46.0, HOME_Y + WH + 110))

    # ── 幕 11 砸进沙发（48.0–52.5）
    sw = 620
    SOFA_IMG = "sofaP_0.png" if has("sofaP_0.png") else "barN_0.png"
    sh = sw * size(SOFA_IMG)[1] / size(SOFA_IMG)[0]
    ON = SOFA_IMG.startswith("sofaP")          # 身体下沿压在线上，手和衣摆垂到线下
    SOFA_Y = HOME_Y + WH + 330 + (0.23 * sh if ON else 0)
    base = (0.47 if ON else 405 / 432) * sh
    LINE2 = SOFA_Y + base
    sx0 = 50
    T_LAND = 48.8
    add(glow(sx0 + sw * 0.35, SOFA_Y + sh * 0.45, sw * 0.5))
    add(f'<path d="M84 {f(LINE2)} H160 C200 {f(LINE2)} 210 {f(LINE2 + 9)} 250 {f(LINE2 + 9)} H370 C410 {f(LINE2 + 9)} 420 {f(LINE2)} 460 {f(LINE2)} H666" fill="none" stroke="{NIGHT_TXT}" stroke-width="1.6" opacity="0.7"/>')
    add(draw_on(f"M496 {f(LINE2 + 6)} l26 8 M548 {f(LINE2 + 5)} l32 9 M606 {f(LINE2 + 6)} l24 7", 34, 49.0, 0.3, op=0.4, sw_=1.2))
    # 沙发：她砸下来那一刻，发丝线自己画出来（线 = 坐垫面）
    SD, SF = SOFA_SD, SOFA_SF
    L2 = LINE2
    sofa = sofa_lines(LINE2, 48.8, back=142)
    add(sofa)
    land = dict(x=sx0 + sw * 0.32, y=SOFA_Y + sh * 0.42, s=0.95, r=-6)
    k11, pos11 = fall_path(dict(x=WX + 390, y=HOME_Y + 250, s=0.9, r=-35), land, 48.0, 0.8,
                           curve=[(0, 0, None), (1, 1, "in")], drift=0, bulge=0.04, op_in=0.15, op_out=0)
    add(her(k11, [("st2", 48.0, 48.85)]))
    her_keys_all.append(k11)
    sq = (f'<animateTransform attributeName="transform" type="scale" values="1 1;1 1;1.05 0.86;0.98 1.04;1 1" '
          f'keyTimes="0;{f(T_LAND / (T_LAND + 0.4))};{f((T_LAND + 0.1) / (T_LAND + 0.4))};{f((T_LAND + 0.25) / (T_LAND + 0.4))};1" dur="{f(T_LAND + 0.4)}s" fill="freeze"/>')
    bar = img(SOFA_IMG, -sw / 2, -base + 16, sw, sh)
    add(show_once(f'<g transform="translate({f(sx0 + sw / 2)} {f(LINE2)})"><g>{sq}{bar}</g></g>', T_LAND, None, fade=0.02))
    dust = "".join(f'<line x1="{f(sx0 + sw * 0.4 + d * 120)}" y1="{f(LINE2 - 6)}" x2="{f(sx0 + sw * 0.4 + d * 175)}" y2="{f(LINE2 - 16)}" '
                   f'stroke="{NIGHT_TXT}" stroke-width="1.6" stroke-linecap="round"/>' for d in (-1, 1, -1.4, 1.4))
    add(show_once(dust, T_LAND, T_LAND + 0.3, fade=0.12))
    # 两只鞋弹飞：一只弹上去落在线左边；一只掉出横杠往下掉，落到台灯窗旁边
    DESK_Y = LINE2 + 142 + 290
    if False and has("prop_shoe.png"):          # 她是穿着鞋倒下的（图里脚上有鞋），不再另外弹两只出来；鞋由阿卡收拾，结尾摆在沙发脚边
        sb = prop_img("prop_shoe.png", 64)
        fx, fy = sx0 + sw * 0.62, LINE2 - 40
        s1 = hop((fx, fy), (150, LINE2 + SF - 14), 49.0, 0.8, height=150, spin=-300)
        s1 = [(t, x, y, s, r, 1 if i else 0) for i, (t, x, y, s, r, o) in enumerate(s1)]
        add(track(sb, s1))
        s2 = hop((fx + 20, fy), (sx0 + sw * 0.74, LINE2 + SF - 12), 49.05, 0.75, height=120, spin=200)
        s2 = [(t, x, y, s, r, 1 if i else 0) for i, (t, x, y, s, r, o) in enumerate(s2)]
        add(track(sb, s2))
    # 阿卡：被甩出 → 后空翻落在她背旁边的线上 → 「又这样睡」→ 拽毯子 → 跳下横杠 → 掉进台灯窗
    a3w = 70
    a3body, a3h = aka_3d(a3w, "aka_stand.png", acts=[("wave", 50.5, 51.25), ("wave", 52.0, 52.4)], step=2)
    p_line = (693, LINE2 - 62 - a3h / 2 + 4)        # 站在右扶手上
    x0, y0, _, _ = pos11(48.5)
    ka11 = [(48.0, WX + 300, HOME_Y + 230, 0.8, 0, 0), (48.4, x0, y0 - 120, 0.9, 0, 1)]
    ka11.append((48.8, x0 + 60, LINE2 - 160, 0.9, 0, 1))
    ka11 += hop((x0 + 60, LINE2 - 160), p_line, 48.85, 0.55, height=120, spin=-360)[1:]
    ka11 += [(49.47, p_line[0], p_line[1] + 5, 0.9, -360, 1), (49.6, p_line[0], p_line[1], 1, -360, 1)]
    ka11 = idle(ka11, 49.6, 51.2, period=0.9, hops=(50.5,))
    ka11 += [(51.2, p_line[0], p_line[1], 1, -360, 1), (51.5, p_line[0] + 14, p_line[1], 1, -375, 1), (51.9, p_line[0], p_line[1], 1, -360, 1)]
    aka_desk = (WX + 460, DESK_Y + 232)
    ka11 += [(52.3, p_line[0], p_line[1], 1, -360, 1)]
    ka11 += [(t, x, y, sc, r - 360, o) for (t, x, y, sc, r, o) in hop(p_line, aka_desk, 52.4, 1.5, height=80, spin=-360, s0=1, s1=1.3, op=(1, 1))[1:]]
    ka11.append((54.2, aka_desk[0], aka_desk[1], 1.3, -720, 0))
    add(track(a3body, ka11))
    if has("prop_blanket2.png") or has("prop_blanket.png"):
        BKX, BKY = sx0 + sw * 0.63, LINE2 - 14
        bk = [(51.2, p_line[0] - 30, p_line[1], 0.3, 0, 0), (51.3, p_line[0] - 30, p_line[1], 0.3, 0, 1),
              (51.9, BKX, BKY, 1.0, 3, 1)]
        add(track(prop_img("prop_blanket2.png" if has("prop_blanket2.png") else "prop_blanket.png", 340), bk + [(60.0, BKX, BKY, 1.0, 3, 1)], op_scale=1.0))
    add(say_at("阿卡", "……又这样睡。", W - 40, SOFA_Y - 40, 50.5, night=True, anchor="end"))
    add(say_at("阿卡", "我去收拾。", 40, LINE2 + SF + 70, 52.0, night=True))
    REV += [(k[0], k[2] + 420) for k in k11[2::2]]
    REV.append((49.0, LINE2 + SF + 110))

    # ── 幕 12 阿卡收拾（52.5–57.0）
    rects.append((WX, DESK_Y, WW, WH))
    add(window(WX, DESK_Y, WW, WH, "01:20 · 她睡着以后",
               [dict(name="desk22", n=6, a=53.5, b=56.0, mode="loop", fps=5), dict(name="desk", n=8, a=56.0, b=None, mode="loop", fps=6)],
               t_on=53.5, night=True))
    REV.append((52.4, DESK_Y + WH + 60))
    ty = DESK_Y + WH + 80
    todo, th = app_card(40, ty, 670, [("第二版颜色延展到三张主视觉",), ("周五前回客户",), ("买猫粮（阿卡加的）",)],
                        "· 待办", night=True, loop=400.0, kind="todo", begin=54.2, gap=0.7)
    add(show_once(todo, 54.4))
    add(say_at("阿卡", "整理好了。", W - 40, ty + th + 58, 56.5, night=True, anchor="end"))
    REV.append((54.3, ty + th + 110))

    # ── 幕 13 梦里搂住（57.5–）
    y = ty + th + 200
    lw = 640
    HUG = has("hugP_0.png")
    lh = lw * size("hugP_0.png" if HUG else "land_0.png")[1] / size("hugP_0.png" if HUG else "land_0.png")[0]
    LINE3 = y + (161 / 169 if HUG else 276 / 326) * lh
    add(sofa_lines(LINE3, 57.7, xl=62, xr=688, aw=44))
    end_body = (glow(55 + lw * 0.33, y + lh * 0.5, lw * 0.5)
                + pillow(84, 256, LINE3, 82)
                + f'<g transform="translate(0 {f(LINE3)})"><g><animateTransform attributeName="transform" type="scale" values="1 1;1 1.012;1 1" '
                  f'dur="3.6s" begin="0s" repeatCount="indefinite"/>'
                + (hug_body(55, y - LINE3, lw) if HUG else flip([f"land_{k}.png" for k in (0, 4)], 55, y - LINE3, lw, lh, [0, 1], fps=0.6))
                + '</g></g>'
                + f'<line x1="24" y1="{f(LINE3)}" x2="{W - 24}" y2="{f(LINE3)}" stroke="{NIGHT_TXT}" stroke-width="1.6" opacity="0.7"/>'.replace('x1="24"', 'x1="62"').replace(f'x2="{W - 24}"', 'x2="688"'))
    add(show_once(end_body, 57.5, None, fade=0.8))
    if has("prop_shoe.png"):                    # 「我去收拾。」的交代：两只鞋并排摆在沙发脚边
        shw = 64; shh = shw * size("prop_shoe.png")[1] / size("prop_shoe.png")[0]
        add(show_once(img("prop_shoe.png", 548, LINE3 + SOFA_SF - shh + 1, shw, shh) + img("prop_shoe.png", 600, LINE3 + SOFA_SF - shh + 1, shw, shh), 58.1, None, fade=0.4))
    z3 = TP.draw("z", 0, 0, 26, "kai", fill=NIGHT_TXT)
    add(f'<g opacity="0"><set attributeName="opacity" to="1" begin="59.0s" fill="freeze"/><g transform="translate(190 {f(LINE3 - 174)})"><animateTransform attributeName="transform" type="translate" '
        f'values="190 {f(LINE3 - 174)};214 {f(LINE3 - 232)}" dur="2.4s" begin="59.0s" repeatCount="indefinite"/>'
        f'<g><animate attributeName="opacity" values="0;1;0" dur="2.4s" begin="59.0s" repeatCount="indefinite"/>{z3}</g></g></g>')
    add(say_at("小耳", "今天说了啥……", 40, LINE3 + SOFA_SF + 62, 58.3, night=True))
    add(say_at("阿卡", "都在。睡吧。", W - 40, LINE3 + SOFA_SF + 114, 59.5, night=True, anchor="end"))
    H = int(LINE3 + SOFA_SF + 290)
    REV.append((57.4, H))

    # 线索（夜里那段用浅色）：画在背景（硬边）之上、所有窗和人之下
    thread = ""
    for ks in her_keys_all[:-1]:
        def hand(k):                           # 她举起的那只手：身体中心往上、稍偏右，跟着身体一起转
            sc = k[3]                           # 不跟着身体转，线才是顺的
            return (k[0], k[1] + 30 * sc, k[2] - 128 * sc) + tuple(k[3:])
        ks = [hand(k) for k in ks]
        day = [k for k in ks if k[2] < EDGE]
        night = [k for k in ks if k[2] >= EDGE - 2]
        if len(day) > 1:
            thread += thread_path(day, rects, GREY, 0.7)
        if len(night) > 1:
            thread += thread_path(night, rects, NIGHT_TXT, 0.45)
    # 左侧刻度
    ruler = [f'<line x1="12" y1="230" x2="12" y2="{H - 40}" stroke="{GREY}" stroke-width="1" opacity="0.6"/>']
    for yy in range(240, H - 40, 32):
        ruler.append(f'<line x1="12" y1="{yy}" x2="{18 if (yy // 32) % 4 else 23}" y2="{yy}" stroke="{GREY}" stroke-width="1" opacity="0.6"/>')
    body = "".join(bg_els) + "".join(ruler) + thread + "".join(els) + "".join(top_els)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" style="display:block;width:100%;line-height:0;">'
           f'<rect x="0" y="0" width="{W}" height="{H}" fill="{PAPER}"/>{body}</svg>')
    REV = sorted(REV)
    mono, best = [], 0
    for t, yv in REV:
        yv = min(yv, H)
        if yv > best + 1:
            best = yv
            mono.append((round(t, 2), round(yv)))
    import os
    if os.environ.get("YS"):
        print(dict(LINE1=LINE1, HAIR=HAIR_Y, DOOR=DOOR_Y, MEET=MEET_Y, CARD=CARD_Y, EDGE=EDGE, TAXI=TAXI_Y, HOME=HOME_Y,
                   SOFA=round(SOFA_Y), DESK=round(DESK_Y), LINE3=round(LINE3), H=H))
    return svg, H, mono, LINE1 + 90, 62.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--update")
    ap.add_argument("--novideo", action="store_true")
    a = ap.parse_args()
    svg, H, REV, FIRST, S_FILM = build()
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    total = H + 150 + W * 9 / 16 + 420
    REV = REV + [(S_FILM, total)]
    steps, prev, raw = [], 100.0, []
    for i, (t, y) in enumerate(REV):
        nxt = REV[i + 1][0] if i + 1 < len(REV) else t + 1.2
        dur = max(0.2, min(nxt - t, 1.2))
        pct = round(y / FIRST * 100, 3)
        if pct <= prev:
            continue
        raw.append((t, dur, prev, pct, nxt - t <= 1.2))   # 最后一项：这一步和下一步首尾相接
        prev = pct
    for i, (t, dur, p0, p1, joined) in enumerate(raw):
        before = i > 0 and raw[i - 1][4]
        if before and joined:
            ease = ""                                                           # 一串的中间：匀速
        elif joined:
            ease = ' calcMode="spline" keyTimes="0;1" keySplines="0.4 0 1 1"'   # 一串的第一步：缓入
        elif before:
            ease = ' calcMode="spline" keyTimes="0;1" keySplines="0 0 0.2 1"'   # 一串的最后一步：缓出
        else:
            ease = ' calcMode="spline" keyTimes="0;1" keySplines="0.4 0 0.2 1"'
        steps.append(f'<animate attributeName="width" values="{f(p0)}%;{f(p1)}%" begin="{f(t)}s" dur="{f(dur)}s" '
                     f'fill="freeze" restart="never"{ease}/>')
    import re as _re
    refs = sorted(set(_re.findall(r'href="(assets/[^"]+)"', svg)))
    wait = "".join(f'<image href="{r}" x="0" y="0" width="1" height="1" opacity="0"/>' for r in refs)
    canvas = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {FIRST}" width="100%" '
              f'style="display:block;max-width:none!important;pointer-events:none;">{"".join(steps)}{wait}</svg>')
    sys.path.insert(0, str(HERE / "work"))
    import slice as _sl
    parts, info = _sl.split(svg, H)
    for a0, b0, n, cr, im, an in info:
        print(f"  切片 {a0:5.0f}–{b0:5.0f}  元素 {n:3d}  跨缝 {cr}  图 {im:2d}  动画 {an}")
    inner = "".join(parts) + film_head() + ("" if a.novideo else "{{VIDEO}}") + outro()
    article = (f'<section style="overflow:hidden;line-height:0;text-align:center;background-color:{NIGHT};">'
               f'<section style="height:0;overflow:visible;line-height:0;width:100%;">{inner}</section>{canvas}</section>')
    (out / "long.svg").write_text(svg, encoding="utf-8")
    (out / "article.html").write_text(article, encoding="utf-8")
    video_local = '<video src="../work/film_wx.mp4" controls playsinline style="display:block;width:100%;background:#000"></video>'
    pv = article.replace('href="assets/', 'href="../assets/').replace("{{VIDEO}}", video_local)
    (out / "preview.html").write_text(PREVIEW.format(article=pv), encoding="utf-8")
    kb = len(article.encode()) / 1024
    print(f"✅ v3 高 {H} · 正文 {kb:.0f}KB · 图片引用 {article.count('<image')} 处 · 推开 {len(steps)} 步")
    if a.push or a.update:
        push(article, out, a.update)


if __name__ == "__main__":
    main()
