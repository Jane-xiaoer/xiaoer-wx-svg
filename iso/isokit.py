"""等轴测（isometric）积木：投影、长方体三色面、在面上贴 2D 内容、零件掉落拼装动画。

只用公众号保留的东西：path / rect / circle / text / g(transform=matrix) + animate(opacity) / animateTransform。
没有 id、渐变、滤镜、mask、fill-opacity 动画。

坐标：X 往右下、Y 往左下、Z 往上；1 格 = S 像素。
"""
import math

C = math.cos(math.pi / 6)  # 0.866
S = 26                     # 每格像素
DROP_EASE = 'calcMode="spline" keyTimes="0;0.8;1" keySplines="0.22 0.75 0.25 1;0.25 0 0.5 1"'
EASE = 'calcMode="spline" keyTimes="0;1" keySplines="0.42 0 0.58 1"'


def f(v):
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return "0" if s == "-0" else s


def ft(v):
    return f"{max(v, 0):.3f}".rstrip("0").rstrip(".") or "0"


def shade(hexc, k):
    """k<1 变暗，k>1 往白提亮。"""
    h = hexc.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if k <= 1:
        r, g, b = (round(c * k) for c in (r, g, b))
    else:
        t = min(k - 1, 1)
        r, g, b = (round(c + (255 - c) * t) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def pts(ps):
    return " ".join(f"{f(x)} {f(y)}" for x, y in ps)


def poly(ps, fill, stroke=None, sw=1):
    st = f' stroke="{stroke}" stroke-width="{f(sw)}" stroke-linejoin="round"' if stroke else ""
    return f'<path d="M{pts(ps)}Z" fill="{fill}"{st}/>'


# ---------------------------------------------------------------- 动画

def appear(body, at, dur=0.35):
    return (f'<g opacity="0"><animate attributeName="opacity" values="0;1" begin="{ft(at)}s" dur="{ft(dur)}s" '
            f'fill="freeze"/>{body}</g>')


def drop(body, at, dy=-70, dx=0, dur=0.7):
    """零件从上方掉下来，落地有一点点回弹。"""
    return (f'<g opacity="0" transform="translate({f(dx)} {f(dy)})">'
            f'<animate attributeName="opacity" values="0;1" begin="{ft(at)}s" dur="0.3s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" values="{f(dx)} {f(dy)};'
            f'{f(-dx * 0.02)} {f(-dy * 0.03)};0 0" {DROP_EASE} begin="{ft(at)}s" dur="{ft(dur)}s" fill="freeze"/>'
            f'{body}</g>')


def blink(body, at, period=1.4, lo=0.25, phase=0.0):
    return (f'<g><animate attributeName="opacity" values="1;{lo};1" begin="{ft(at + phase)}s" dur="{ft(period)}s" '
            f'repeatCount="indefinite"/>{body}</g>')


def spin(body, cx, cy, at, period=1.6):
    return (f'<g><animateTransform attributeName="transform" type="rotate" values="0 {f(cx)} {f(cy)};360 {f(cx)} {f(cy)}" '
            f'begin="{ft(at)}s" dur="{ft(period)}s" repeatCount="indefinite"/>{body}</g>')


def bob(body, at, amp=6, period=2.4):
    return (f'<g><animateTransform attributeName="transform" type="translate" values="0 0;0 {f(-amp)};0 0" '
            f'calcMode="spline" keyTimes="0;0.5;1" keySplines="0.42 0 0.58 1;0.42 0 0.58 1" '
            f'begin="{ft(at)}s" dur="{ft(period)}s" repeatCount="indefinite"/>{body}</g>')


# ---------------------------------------------------------------- 投影

class Iso:
    """一个局部等轴测坐标系，原点 (ox, oy) 是 (0,0,0) 在屏幕上的位置。"""

    def __init__(self, ox, oy, s=S):
        self.ox, self.oy, self.s = ox, oy, s

    def p(self, X, Y, Z=0):
        s = self.s
        return (self.ox + (X - Y) * C * s, self.oy + (X + Y) * 0.5 * s - Z * s)

    # 面上的局部 2D 坐标（单位：像素），u 往右、v 往下
    def face_top(self, X, Y, Z):
        e = self.p(X, Y, Z)
        return f"matrix({f(C)} 0.5 {f(-C)} 0.5 {f(e[0])} {f(e[1])})"

    def face_left(self, X, Y, Z):
        """Y 朝前的面（屏幕左下那面），原点 = 该面左上角 (X, Y, Z)。u 沿 +X。"""
        e = self.p(X, Y, Z)
        return f"matrix({f(C)} 0.5 0 1 {f(e[0])} {f(e[1])})"

    def face_right(self, X, Y, Z):
        """X 朝前的面（屏幕右下那面），原点 = 该面左上角 (X, Y, Z)，u 沿 -Y。"""
        e = self.p(X, Y, Z)
        return f"matrix({f(C)} -0.5 0 1 {f(e[0])} {f(e[1])})"

    def on(self, matrix, body):
        return f'<g transform="{matrix}">{body}</g>'

    def box(self, X, Y, Z, w, d, h, color, top=None, left=None, right=None, edge=True,
            deco_top="", deco_left="", deco_right=""):
        """长方体：顶面亮、左面中、右面暗。deco_* 是贴在对应面上的 2D 片段（面局部像素坐标）。"""
        P = self.p
        t = top or shade(color, 1.0)
        l_ = left or shade(color, 0.86)
        r = right or shade(color, 0.72)
        ec = shade(color, 0.6) if edge else None
        s = self.s
        out = [
            poly([P(X, Y + d, Z + h), P(X + w, Y + d, Z + h), P(X + w, Y + d, Z), P(X, Y + d, Z)], l_, ec, 0.8),
            poly([P(X + w, Y + d, Z + h), P(X + w, Y, Z + h), P(X + w, Y, Z), P(X + w, Y + d, Z)], r, ec, 0.8),
            poly([P(X, Y, Z + h), P(X + w, Y, Z + h), P(X + w, Y + d, Z + h), P(X, Y + d, Z + h)], t, ec, 0.8),
        ]
        if deco_left:
            out.append(self.on(self.face_left(X, Y + d, Z + h), deco_left))
        if deco_right:
            out.append(self.on(self.face_right(X + w, Y + d, Z + h), deco_right))
        if deco_top:
            out.append(self.on(self.face_top(X, Y, Z + h), deco_top))
        return "".join(out), (w * s, d * s, h * s)

    def slab(self, X, Y, Z, w, d, h, color, **kw):
        return self.box(X, Y, Z, w, d, h, color, **kw)[0]

    def ellipse_top(self, X, Y, Z, r, fill, stroke=None, sw=2, extra=""):
        """顶面上的圆（看上去是椭圆）。r 单位：格。"""
        st = f' stroke="{stroke}" stroke-width="{f(sw)}"' if stroke else ""
        return self.on(self.face_top(X, Y, Z), f'<circle cx="0" cy="0" r="{f(r * self.s)}" fill="{fill}"{st}>{extra}</circle>')

    def cylinder(self, X, Y, Z, r, h, color, n=20):
        """竖着的圆柱（树干、塔身、灯柱）。X,Y 是底面圆心。"""
        P = self.p
        top = [P(X + r * math.cos(a), Y + r * math.sin(a), Z + h) for a in (2 * math.pi * k / n for k in range(n))]
        # 侧面只画朝前的半圈：-45°（屏幕右）到 135°（屏幕左）
        a0, a1 = -math.pi / 4, 3 * math.pi / 4
        side_top = [P(X + r * math.cos(a), Y + r * math.sin(a), Z + h) for a in [a0 + (a1 - a0) * k / 12 for k in range(13)]]
        side_bot = [P(X + r * math.cos(a), Y + r * math.sin(a), Z) for a in [a1 - (a1 - a0) * k / 12 for k in range(13)]]
        # 右半圈暗、左半圈中
        mid_t = side_top[6:]
        mid_b = side_bot[:7]
        return (poly(side_top[:7] + side_bot[6:], shade(color, 0.74)) +
                poly(mid_t + mid_b, shade(color, 0.88)) +
                poly(top, color))
