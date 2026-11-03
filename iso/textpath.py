"""文字转曲线：用品牌字体把字直接画成 <path>，公众号里不用装字体也是 VI 字形。

公众号不让用 @font-face / <style>，系统字体又各家不同；标题、英文、等宽标注这种字少的地方转曲最稳。
正文字多就别转（体积大），用 <text> 加宋体兜底。

用法：
    tp = TextPath({"serif": "NotoSerifSC-Light.ttf", "en": "CormorantGaramond-Light.ttf"})
    svg = tp.draw("源生胶元", x, y, 92, "serif", fill="#ECE4D6", anchor="start", spacing=0.08)
    w = tp.width("源生胶元", 92, "serif", spacing=0.08)
"""
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont


import re

_TOK = re.compile(r"[MLHVCQTZ]|-?\d*\.?\d+(?:e-?\d+)?", re.I)


def relative(d, prec):
    """绝对坐标路径 → 相对坐标 + 取整，体积能小一半以上。"""
    toks = _TOK.findall(d)
    out, i, cx, cy, sx, sy, cmd = [], 0, 0.0, 0.0, 0.0, 0.0, None
    fmt = (lambda v: str(int(round(v)))) if prec == 0 else (lambda v: (f"{v:.{prec}f}".rstrip("0").rstrip(".") or "0"))
    # 用「量化后的当前点」做相对，避免误差累积
    qx = qy = 0.0

    def q(v):
        return round(v, prec) if prec else round(v)
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz":
                out.append("z")
                qx, qy = sx, sy
                continue
        n = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "Q": 4, "T": 2}[cmd.upper()]
        vals = [float(v) for v in toks[i:i + n]]
        i += n
        if cmd == "H":
            nx = q(vals[0])
            out.append("h" + fmt(nx - qx))
            qx = nx
        elif cmd == "V":
            ny = q(vals[0])
            out.append("v" + fmt(ny - qy))
            qy = ny
        else:
            pts = [(q(vals[k]), q(vals[k + 1])) for k in range(0, n, 2)]
            rel = " ".join(f"{fmt(x - qx)} {fmt(y - qy)}" for x, y in pts)
            out.append(cmd.lower() + rel.replace(" -", "-"))
            qx, qy = pts[-1]
            if cmd == "M":
                sx, sy = qx, qy
                cmd = "L"  # M 后面跟的坐标按 L 处理
    return "".join(out)


class TextPath:
    def __init__(self, fonts, lining=True):
        self.f = {}
        for k, path in fonts.items():
            ft = TTFont(path, lazy=True)
            order = set(ft.getGlyphOrder())
            cmap = dict(ft.getBestCmap())
            if lining:  # 有 .lf 齐线数字就用（Cormorant 默认是老式数字，3 会掉到基线下）
                for c in "0123456789":
                    alt = cmap.get(ord(c), "") + ".lf"
                    if alt in order:
                        cmap[ord(c)] = alt
            self.f[k] = (ft, ft.getGlyphSet(), cmap, ft["hmtx"], ft["head"].unitsPerEm)
        self.cache = {}

    def _glyph(self, key, ch):
        ft, gs, cmap, hmtx, upm = self.f[key]
        name = cmap.get(ord(ch))
        if name is None:
            return None, upm * 0.5
        return name, hmtx[name][0]

    def width(self, s, size, key, spacing=0.0):
        upm = self.f[key][4]
        return sum(self._glyph(key, c)[1] for c in s) * size / upm + spacing * size * max(len(s) - 1, 0)

    def draw(self, s, x, y, size, key, fill="#000", anchor="start", spacing=0.0, opacity=None):
        ft, gs, cmap, hmtx, upm = self.f[key]
        w = self.width(s, size, key, spacing)
        if anchor == "middle":
            x -= w / 2
        elif anchor == "end":
            x -= w
        k = size / upm
        pen = SVGPathPen(gs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
        cx = x
        for c in s:
            name, adv = self._glyph(key, c)
            if name and c.strip():
                gs[name].draw(TransformPen(pen, (k, 0, 0, -k, cx, y)))
            cx += adv * k + spacing * size
        d = pen.getCommands()
        if not d:
            return ""
        d = relative(d, 0 if (size >= 26 and key.startswith("zh")) else 1)
        op = f' opacity="{opacity}"' if opacity is not None else ""
        return f'<path d="{d}" fill="{fill}"{op}/>'
