"""等轴测小场景零件库。每个模型都站在一块 8×8 的底座上，零件一块块掉下来拼成。

写新模型：def 名字(b): 用 b.iso 画、用 b.add(片段) 按顺序掉落；顶面高度 b.z（底座顶面）。
注册进 MODELS，分镜里 "model": "名字" 就能用。画的顺序 = 遮挡顺序：先后面（X+Y 小）再前面。
"""
import math

from isokit import appear, blink, bob, drop, f, ft, shade, spin

Z0 = 0.7  # 底座顶面高度


class Builder:
    def __init__(self, iso, t0, pal, accent, step=0.14):
        self.iso, self.t, self.pal, self.acc, self.step = iso, t0, pal, accent, step
        self.parts = []
        self.z = Z0

    def add(self, body, dy=-80, gap=None, dur=0.7):
        self.parts.append(drop(body, self.t, dy, dur=dur))
        self.t += self.step if gap is None else gap

    def fade(self, body, gap=None):
        self.parts.append(appear(body, self.t, 0.5))
        self.t += self.step if gap is None else gap

    @property
    def live(self):
        """循环动画的开始时间：当前零件落地之后。"""
        return self.t + 0.6

    def svg(self):
        return "".join(self.parts)


# ---------------------------------------------------------------- 通用小件

def platform(b):
    iso, p = b.iso, b.pal
    num = label(f"{b.no:02d}", 10, 14, 12, shade(p["plinth"], 0.62), 800, "start", True) if getattr(b, "no", 0) else ""
    base = iso.slab(0, 0, 0, 8, 8, Z0, p["plinth"], top=p["plinth_top"], deco_left=num)
    ground = shade(b.acc, 1.72)
    top = iso.slab(0.35, 0.35, Z0, 7.3, 7.3, 0.06, ground, edge=False)
    at = b.t
    b.parts.append(f'<g opacity="0" transform="translate(16 0)">'
                   f'<animate attributeName="opacity" values="0;1" begin="{ft(at)}s" dur="0.35s" fill="freeze"/>'
                   f'<animateTransform attributeName="transform" type="translate" values="16 0;-0.3 0;0 0" '
                   f'calcMode="spline" keyTimes="0;0.85;1" keySplines="0.22 0.75 0.25 1;0.25 0 0.5 1" '
                   f'begin="{ft(at)}s" dur="0.7s" fill="freeze"/>{base}{top}</g>')
    b.t += 0.3


def tree(b, X, Y, h=1.0, color=None):
    iso = b.iso
    g = color or b.pal["leaf"]
    z = b.z + 0.06
    trunk = iso.slab(X - 0.12, Y - 0.12, z, 0.24, 0.24, 0.5 * h, b.pal["trunk"], edge=False)
    crown = iso.slab(X - 0.5, Y - 0.5, z + 0.5 * h, 1.0, 1.0, 0.9 * h, g)
    cap = iso.slab(X - 0.3, Y - 0.3, z + 1.4 * h, 0.6, 0.6, 0.4 * h, shade(g, 1.15))
    b.add(trunk + crown + cap, dy=-50, gap=0.08)


def bush(b, X, Y, color=None):
    g = color or shade(b.pal["leaf"], 1.08)
    body = b.iso.slab(X - 0.4, Y - 0.4, b.z + 0.06, 0.8, 0.8, 0.45, g)
    b.add(body, dy=-30, gap=0.06)


def lamp(b, X, Y):
    iso = b.iso
    pole = iso.slab(X - 0.07, Y - 0.07, b.z + 0.06, 0.14, 0.14, 2.2, b.pal["dark"], edge=False)
    head = iso.slab(X - 0.25, Y - 0.25, b.z + 2.26, 0.5, 0.5, 0.25, "#F3D67A")
    b.add(pole + blink(head, b.live, 2.6, 0.55), dy=-40, gap=0.06)


def tile_path(b, cells):
    """底座上铺一条浅色小路（顶面格子）。"""
    iso = b.iso
    out = "".join(iso.slab(x + 0.05, y + 0.05, b.z + 0.06, 0.9, 0.9, 0.04, b.pal["paver"], edge=False) for x, y in cells)
    b.fade(out, gap=0.1)


def screen_lines(w, h, at, color, bg, rows=5, pad=10, loop=True):
    """屏幕：深底 + 一行行代码条，长出来后循环重写。面局部像素坐标。"""
    out = [f'<rect x="0" y="0" width="{f(w)}" height="{f(h)}" fill="{bg}"/>']
    lh = (h - 2 * pad) / rows
    for k in range(rows):
        full = (w - 2 * pad) * (0.45 + 0.5 * ((k * 37) % 10) / 10)
        y = pad + k * lh + lh * 0.25
        c = color if k % 3 else shade(color, 1.35)
        anim = (f'<animate attributeName="width" values="0;{f(full)};{f(full)};0" keyTimes="0;0.35;0.85;1" '
                f'begin="{ft(at + k * 0.18)}s" dur="3.2s" repeatCount="indefinite"/>' if loop else
                f'<animate attributeName="width" values="0;{f(full)}" begin="{ft(at + k * 0.18)}s" dur="0.5s" fill="freeze"/>')
        out.append(f'<rect x="{f(pad)}" y="{f(y)}" width="0" height="{f(lh * 0.42)}" rx="2" fill="{c}">{anim}</rect>')
    return "".join(out)


def label(s, x, y, size, color, weight=700, anchor="start", mono=False):
    fam = "Menlo,Consolas,monospace" if mono else "PingFang SC,Noto Sans CJK SC,Microsoft YaHei,sans-serif"
    return (f'<text x="{f(x)}" y="{f(y)}" fill="{color}" font-size="{f(size)}" font-weight="{weight}" '
            f'text-anchor="{anchor}" font-family="{fam}">{s}</text>')


# ---------------------------------------------------------------- 模型

def archive(b):
    """共享记忆：一摞数据盘 + 头顶漂着几张档案卡。"""
    iso, p, a = b.iso, b.pal, b.acc
    platform(b)
    tile_path(b, [(5, 7), (5, 6), (6, 6), (6, 5)])
    tree(b, 1.2, 1.4)
    for k in range(3):
        z = b.z + 0.06 + k * 0.85
        disk = iso.cylinder(3.6, 3.6, z, 1.9, 0.7, p["metal"] if k % 2 else shade(p["metal"], 0.95))
        ring = iso.ellipse_top(3.6, 3.6, z + 0.7, 1.35, "none", a, 3)
        led = iso.on(iso.face_left(3.6 - 0.2, 3.6 + 1.85, z + 0.55), f'<circle cx="0" cy="0" r="4" fill="{a}"/>')
        b.add(disk + ring + blink(led, b.live, 1.1, 0.2, k * 0.3), gap=0.16)
    # 漂浮档案卡
    for k, (X, Y, Z) in enumerate([(2.2, 2.6, 4.2), (4.6, 2.2, 4.8), (3.0, 4.6, 5.3)]):
        card = iso.slab(X, Y, Z, 1.4, 1.0, 0.08, "#FFFFFF", edge=True,
                        deco_top=f'<rect x="5" y="5" width="22" height="3" fill="{a}"/><rect x="5" y="12" width="14" height="2" fill="{p["muted"]}"/>')
        b.add(bob(card, b.live, 7, 2.2 + k * 0.4), dy=-40, gap=0.1)
    tree(b, 6.6, 1.6, 0.8)
    tree(b, 1.4, 6.5, 0.9)
    lamp(b, 7.2, 3.2)


def laptop(b, chip="MLX", old=False):
    """笔记本：底座 + 立起的屏幕（代码条循环滚）+ 芯片牌。old=True 是小一号的旧机。"""
    iso, p, a = b.iso, b.pal, b.acc
    platform(b)
    tree(b, 0.9, 0.9, 0.8)
    k = 0.8 if old else 1.0
    w, d = 4.4 * k, 3.2 * k
    X, Y = 4 - w / 2, 4.2 - d / 2
    z = b.z + 0.06
    body = iso.slab(X, Y, z, w, d, 0.28, p["metal"],
                    deco_top="".join(f'<rect x="{f(8 + c * (w * 26 - 16) / 10)}" y="{f(8 + r * 11)}" width="{f((w * 26 - 16) / 10 - 3)}" height="8" rx="1.5" fill="{shade(p["metal"], 0.86)}"/>'
                                     for r in range(4) for c in range(10)))
    b.add(body)
    sh = 2.6 * k
    scr_w, scr_h = w * 26 - 18, sh * 26 - 16
    panel = iso.slab(X, Y - 0.16, z + 0.28, w, 0.16, sh, shade(p["metal"], 0.9),
                     deco_left=f'<g transform="translate(9 8)">{screen_lines(scr_w, scr_h, b.live, a, p["screen"], 6)}</g>')
    b.add(panel, dy=-110)
    if chip:
        badge = iso.slab(X + w + 0.4, Y + d - 1.2, z, 1.3, 1.3, 0.35, a,
                         deco_top=f'<g transform="translate(17 17) scale(1 1)">{label(chip, 0, 5, 11, "#FFFFFF", 800, "middle", True)}</g>')
        b.add(badge, dy=-60)
    tree(b, 7.0, 1.2, 0.8)
    bush(b, 6.9, 7.0)
    mug = iso.cylinder(1.6, 6.2, z, 0.35, 0.55, p["mug"])
    b.add(mug, dy=-40, gap=0.08)


def gate(b, text="11434"):
    """一道门：两根柱 + 门楣写端口号，地上箭头穿门而过。"""
    iso, p, a = b.iso, b.pal, b.acc
    platform(b)
    z = b.z + 0.06
    arrows = "".join(f'<path d="M{f(14 + k * 34)} 8 l12 9 l-12 9" fill="none" stroke="{a}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" opacity="0.9">'
                     f'<animate attributeName="opacity" values="0.15;1;0.15" begin="{ft(b.t + 1.2 + k * 0.15)}s" dur="1.2s" repeatCount="indefinite"/></path>' for k in range(5))
    lane = iso.slab(0.6, 3.3, z, 6.8, 1.4, 0.03, p["paver"], edge=False, deco_top=f'<g transform="translate(0 2)">{arrows}</g>')
    b.fade(lane)
    tree(b, 1.2, 1.2)
    left = iso.slab(3.4, 2.4, z, 0.6, 0.6, 3.0, p["pillar"])
    b.add(left)
    right = iso.slab(3.4, 5.0, z, 0.6, 0.6, 3.0, p["pillar"])
    b.add(right)
    lintel = iso.slab(3.2, 2.2, z + 3.0, 1.0, 3.6, 0.7, a,
                      deco_right=label(text, 47, 14, 14, "#FFFFFF", 800, "middle", True))
    b.add(lintel, dy=-120)
    tree(b, 6.6, 1.4, 0.8)
    lamp(b, 1.2, 6.8)
    tree(b, 6.4, 6.6, 1.0)


def desktop(b, tag="RTX 5070"):
    """台式机：显示器（屏上一个方块在转）+ 机箱侧面风扇转、灯条呼吸。"""
    iso, p, a = b.iso, b.pal, b.acc
    platform(b)
    z = b.z + 0.06
    tree(b, 1.0, 1.2, 0.9)
    desk = iso.slab(0.6, 2.8, z, 4.0, 2.6, 0.22, p["wood"])
    b.add(desk)
    stand = iso.slab(2.4, 2.85, z + 0.22, 0.5, 0.35, 0.8, p["metal"])
    b.add(stand, dy=-50, gap=0.08)
    sw, sh = 3.6 * 26 - 16, 2.1 * 26 - 14
    cube = (f'<g transform="translate({f(sw / 2 + 8)} {f(sh / 2 + 7)})">'
            + spin(f'<path d="M0 -14 L13 -6 L13 8 L0 15 L-13 8 L-13 -6Z" fill="{a}"/><path d="M0 -14 L13 -6 L0 1 L-13 -6Z" fill="{shade(a, 1.35)}"/>'
                   f'<path d="M0 1 L0 15 L13 8 L13 -6Z" fill="{shade(a, 0.75)}"/>', 0, 0, b.live, 4.0)
            + '</g>')
    monitor = iso.slab(0.8, 3.2, z + 1.0, 3.6, 0.18, 2.1, p["dark"],
                       deco_left=f'<rect x="8" y="7" width="{f(sw)}" height="{f(sh)}" fill="{p["screen"]}"/>{cube}')
    b.add(monitor, dy=-110)
    kb = iso.slab(1.4, 4.1, z + 0.22, 2.4, 0.9, 0.12, p["metal"])
    b.add(kb, dy=-40, gap=0.08)
    d_ = 2.6
    fans = "".join(f'<g transform="translate({f(d_ * 13)} {f(46 + k * 34)})">'
                   + spin(f'<circle r="14" fill="{shade(p["dark"], 1.2)}"/>' + "".join(
                       f'<path d="M0 0 L{f(12 * math.cos(j * 2.094))} {f(12 * math.sin(j * 2.094))} '
                       f'L{f(12 * math.cos(j * 2.094 + 0.7))} {f(12 * math.sin(j * 2.094 + 0.7))}Z" fill="{a}"/>'
                       for j in range(3)), 0, 0, b.live, 0.9)
                   + '</g>' for k in range(3))
    strip = (f'<rect x="4" y="30" width="4" height="{f(4.6 * 26 - 38)}" fill="{a}">'
             f'<animate attributeName="opacity" values="1;0.3;1" begin="{ft(b.live)}s" dur="2s" repeatCount="indefinite"/></rect>')
    tower = iso.slab(5.4, 1.0, z, 1.4, d_, 4.6, p["dark"],
                     deco_right=label(tag, d_ * 13, 20, 11, a, 800, "middle", True) + fans + strip)
    b.add(tower, dy=-120)
    tree(b, 7.0, 6.6, 0.8)
    bush(b, 1.0, 7.0)


def server(b, slots=6):
    """机柜：一格格插槽亮灯，旁边一条隧道管通向外面。"""
    iso, p, a = b.iso, b.pal, b.acc
    platform(b)
    z = b.z + 0.06
    tree(b, 1.0, 1.2)
    pipe = iso.slab(0.4, 5.2, z, 3.6, 0.8, 0.8, p["pillar"],
                    deco_top="".join(f'<rect x="{f(8 + k * 22)}" y="6" width="10" height="9" rx="2" fill="{a}" opacity="0.2">'
                                     f'<animate attributeName="opacity" values="0.15;1;0.15" begin="{ft(b.t + 1.5 + k * 0.12)}s" dur="1.4s" repeatCount="indefinite"/></rect>'
                                     for k in range(4)))
    b.add(pipe)
    rack_h = 0.62 * slots
    leds = "".join(blink(f'<rect x="{f(10 + j * 9)}" y="{f(8 + k * 0.62 * 26)}" width="5" height="5" fill="{a if (j + k) % 3 else "#E7C76A"}"/>',
                         b.t + 1.2, 0.9 + 0.17 * ((k * 3 + j) % 5), 0.15, 0.1 * j)
                   for k in range(slots) for j in range(3))
    slats = "".join(f'<rect x="4" y="{f(4 + k * 0.62 * 26)}" width="{f(2.4 * 26 - 8)}" height="{f(0.62 * 26 - 6)}" rx="2" fill="{shade(p["dark"], 1.25)}"/>' for k in range(slots))
    rack = iso.slab(4.4, 2.0, z, 2.4, 2.4, rack_h, p["dark"], deco_left=slats + leds,
                    deco_right="".join(f'<rect x="6" y="{f(8 + k * 0.62 * 26)}" width="{f(2.4 * 26 - 12)}" height="3" fill="{shade(p["dark"], 1.4)}"/>' for k in range(slots)))
    b.add(rack, dy=-130)
    tree(b, 1.4, 3.2, 0.7)
    tree(b, 6.8, 6.4, 0.9)
    bush(b, 5.4, 7.0)


def checklist(b, chip=None, items=4):
    """旧笔记本 + 一块清单板，勾一个个打上。"""
    iso, p, a = b.iso, b.pal, b.acc
    laptop(b, chip=chip, old=True)
    z = b.z + 0.06
    rows = []
    for k in range(items):
        y = 18 + k * 24
        rows.append(f'<rect x="12" y="{f(y - 9)}" width="13" height="13" rx="2" fill="none" stroke="{p["muted"]}" stroke-width="2"/>'
                    f'<rect x="32" y="{f(y - 5)}" width="{f(30 + (k * 13) % 20)}" height="5" fill="{p["muted"]}"/>'
                    f'<path d="M14 {f(y - 3)} l4 5 l8 -10" fill="none" stroke="{a}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" '
                    f'stroke-dasharray="20" stroke-dashoffset="20"><animate attributeName="stroke-dashoffset" values="20;0" begin="{ft(b.t + 0.9 + k * 0.45)}s" dur="0.3s" fill="freeze"/></path>')
    board = iso.slab(6.3, 0.6, z, 0.2, 3.6, 4.2, "#FFFFFF", deco_right=f'<g transform="translate(0 6)">{"".join(rows)}</g>')
    b.add(board, dy=-110)


def antenna(b):
    """信号塔：塔身一节节长高，塔顶灯闪，脚下波纹一圈圈扩散，两侧小碟朝外。"""
    iso, p, a = b.iso, b.pal, b.acc
    platform(b)
    z = b.z + 0.06
    tree(b, 1.0, 1.2)
    tree(b, 6.6, 1.6, 0.8)
    pad = iso.slab(2.6, 2.6, z, 2.8, 2.8, 0.3, p["pillar"])
    b.add(pad)
    rings = "".join(
        f'<g transform="{iso.face_top(4, 4, z + 0.32)}"><g opacity="0">'
        f'<animateTransform attributeName="transform" type="scale" values="0.5;2.6" begin="{ft(b.live + k * 0.9)}s" dur="2.7s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="0.9;0" begin="{ft(b.live + k * 0.9)}s" dur="2.7s" repeatCount="indefinite"/>'
        f'<circle r="34" fill="none" stroke="{a}" stroke-width="2.5"/></g></g>' for k in range(3))
    b.parts.append(rings)
    for k in range(6):
        wk = 1.5 - k * 0.2
        seg = iso.slab(4 - wk / 2, 4 - wk / 2, z + 0.3 + k * 0.8, wk, wk, 0.8,
                       p["metal"] if k % 2 else a,
                       deco_left=f'<path d="M3 3 L{f(wk * 26 - 3)} {f(0.8 * 26 - 3)} M{f(wk * 26 - 3)} 3 L3 {f(0.8 * 26 - 3)}" stroke="{shade(p["metal"], 0.7)}" stroke-width="1"/>')
        b.add(seg, dy=-70, gap=0.1)
    top_z = z + 0.3 + 6 * 0.8
    dish_l = iso.slab(3.0, 4.4, z + 3.0, 0.9, 0.2, 0.9, "#FFFFFF")
    dish_r = iso.slab(4.6, 3.2, z + 2.2, 0.2, 0.9, 0.9, "#FFFFFF")
    b.add(dish_l + dish_r, dy=-50)
    light = iso.on(iso.face_top(4, 4, top_z), f'<circle r="7" fill="#E0533D"/>')
    b.add(blink(light, b.live, 1.0, 0.15), dy=-40)
    tree(b, 1.4, 6.6, 1.0)
    bush(b, 6.8, 6.8)


def mailbox(b, flag="草稿"):
    """信箱：立柱 + 箱子，信封一封封掉进去，小旗子立起来（但没寄出）。"""
    iso, p, a = b.iso, b.pal, b.acc
    platform(b)
    z = b.z + 0.06
    tree(b, 1.0, 1.2)
    tile_path(b, [(4, 7), (4, 6), (4, 5)])
    post = iso.slab(3.7, 3.4, z, 0.5, 0.5, 2.0, p["wood"])
    b.add(post)
    box = iso.slab(2.9, 2.8, z + 2.0, 2.2, 1.6, 1.3, a,
                   deco_left=f'<rect x="10" y="12" width="{f(2.2 * 26 - 20)}" height="5" rx="2" fill="{shade(a, 0.6)}"/>'
                             + label(flag, 2.2 * 13, 32, 11, "#FFFFFF", 800, "middle"))
    b.add(box, dy=-110)
    # 信封：从上方落进投信口，落到一半消失
    for k in range(3):
        at = b.t + 0.5 + k * 0.5
        env = iso.slab(3.3, 3.2, z + 3.9, 1.2, 0.8, 0.06, "#FFFFFF",
                       deco_top=f'<path d="M0 0 L{f(1.2 * 13)} {f(0.8 * 13)} L{f(1.2 * 26)} 0" fill="none" stroke="{p["muted"]}" stroke-width="1.5"/>')
        b.parts.append(f'<g opacity="0" transform="translate(0 -60)">'
                       f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.2;0.75;1" begin="{ft(at)}s" dur="0.9s" fill="freeze"/>'
                       f'<animateTransform attributeName="transform" type="translate" values="0 -60;0 26" begin="{ft(at)}s" dur="0.9s" fill="freeze"/>'
                       f'{env}</g>')
    # 小旗
    fl = (iso.slab(5.1, 3.4, z + 2.2, 0.12, 0.12, 1.4, p["dark"]) +
          iso.slab(5.1, 3.0, z + 3.2, 0.06, 0.5, 0.4, "#E0533D", edge=False))
    b.t += 1.6
    b.add(fl, dy=-30)
    tree(b, 6.8, 1.4, 0.8)
    lamp(b, 6.8, 4.2)
    bush(b, 1.2, 6.8)


MODELS = {
    "archive": archive, "laptop": laptop, "gate": gate, "desktop": desktop, "server": server,
    "checklist": checklist, "antenna": antenna, "mailbox": mailbox,
}
