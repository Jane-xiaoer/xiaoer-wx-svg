"""品牌 VI 版积木：照着甲方 VI 做公众号动态长图时用。

和 iso_journey（彩色等轴测小场景）不同，这套是「编辑感 / 克制」的做法：
  · 只用淡入和描线，没有弹跳、缩放冲击、光扫（很多品牌 VI 明文禁止）
  · 照片做成「磨砂玻璃立板」：正面整幅磨砂 → 清晰窗 0.6s 由虚到实；顶面和侧面是玻璃厚度（斜二测）
  · 测点逐个出现（间隔 0.12s，每点 0.2s），连线在最后一点后 0.3s 内画出
  · 章节之间用品牌自己的图形当「路」，例：等轴测斜向的标尺测量线，毫米数往下接着数
  · 标题 / 英文 / 标注用 VI 字体转曲（textpath.py），正文用 <text> + 宋体兜底

用法：
    from vikit import VI
    vi = VI(palette={"bg": "#1D1A17", "text": "#ECE4D6", "line": "#D6C4A2", "muted": "#9A9285"},
            fonts={"zh": "NotoSerifSC-Light.ttf", "en": "CormorantGaramond-Light.ttf",
                   "eni": "CormorantGaramond-LightItalic.ttf", "mono": "IBMPlexMono-Light.ttf"},
            href=lambda name: f"https://mmbiz.qpic.cn/...{name}")   # 图片先用 wechat.upload_image 传图床
    svg = vi.glass("photo", x, y, w, h, at=1.0, rel=(0.1, 0.2, 0.8, 0.5))[0] + vi.divider(...)[0] + ...
字体自己准备（Google Fonts 下载，OFL 可商用），不随仓库分发。
"""
import math
from html import escape

from textpath import TextPath

C30 = math.cos(math.pi / 6)
EO = 'calcMode="spline" keyTimes="0;1" keySplines="0.2 0.7 0.2 1"'  # ease-out (.2,.7,.2,1)
SERIF = "'Noto Serif SC','Source Han Serif SC','Songti SC','STSong',serif"


def f(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def ft(v):
    return f"{max(v, 0):.3f}".rstrip("0").rstrip(".") or "0"


class VI:
    def __init__(self, palette, fonts, href=None, width=1080, margin=96):
        self.p = {"bg": "#1D1A17", "text": "#ECE4D6", "line": "#D6C4A2", "muted": "#9A9285",
                  "panel": "#2A2520", "panel2": "#3A332C", "side": "#25211D", **palette}
        self.tp = TextPath(fonts)
        self.href = href or (lambda name: name)
        self.W, self.M = width, margin

    # ------------------------------------------------ 动画：只有淡入和描线
    def fade(self, body, at, dur=0.6, to=1):
        return (f'<g opacity="0"><animate attributeName="opacity" values="0;{to}" begin="{ft(at)}s" dur="{ft(dur)}s" '
                f'fill="freeze" {EO}/>{body}</g>')

    def line(self, pts, at=None, dur=0.6, color=None, w=1.2, op=0.8, dash=None):
        color = color or self.p["line"]
        d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts)
        if at is None:
            da = f' stroke-dasharray="{dash}"' if dash else ""
            return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" opacity="{op}"{da}/>'
        L = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)) + 1
        return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" opacity="{op}" '
                f'stroke-dasharray="{f(L)} {f(L)}" stroke-dashoffset="{f(L)}">'
                f'<animate attributeName="stroke-dashoffset" values="{f(L)};0" begin="{ft(at)}s" dur="{ft(dur)}s" fill="freeze" {EO}/></path>')

    def point(self, x, y, at, key=False):
        c = self.p["line"]
        body = (f'<circle cx="{f(x)}" cy="{f(y)}" r="9" fill="none" stroke="{c}" stroke-width="1.4"/>'
                f'<circle cx="{f(x)}" cy="{f(y)}" r="2.2" fill="{c}"/>') if key else \
            f'<circle cx="{f(x)}" cy="{f(y)}" r="3.6" fill="{c}"/>'
        return self.fade(body, at, 0.2)

    def points(self, pts, at, keys=(), connect=True, dash="4 6"):
        """测点逐个出现（间隔 0.12s），最后一点后 0.3s 内画出虚线连线。返回 (svg, 结束时间)。"""
        out = [self.point(x, y, at + k * 0.12, k in keys) for k, (x, y) in enumerate(pts)]
        t = at + 0.12 * (len(pts) - 1) + 0.2
        if connect and len(pts) > 1:
            out.append(self.fade(self.line(pts, None, None, 1, 0.7, dash), t, 0.3))
        return "".join(out), t + 0.3

    # ------------------------------------------------ 文字
    def zh(self, s, x, y, size, fill=None, anchor="start", sp=0.04, key="zh"):
        return self.tp.draw(s, x, y, size, key, fill or self.p["text"], anchor, sp)

    def en(self, s, x, y, size, fill=None, anchor="start", sp=0.0, italic=False):
        return self.tp.draw(s, x, y, size, "eni" if italic else "en", fill or self.p["text"], anchor, sp)

    def mono(self, s, x, y, size=14, fill=None, anchor="start", sp=0.2):
        return self.tp.draw(s, x, y, size, "mono", fill or self.p["muted"], anchor, sp)

    def body(self, s, x, y, size=24, fill=None, anchor="start", maxw=None, lh=1.75):
        from iso_journey import wrap
        lines = wrap(s, size, maxw or (self.W - 2 * self.M))
        fill = fill or self.p["text"]
        out = "".join(f'<text x="{f(x)}" y="{f(y + k * size * lh)}" fill="{fill}" font-size="{size}" font-weight="300" '
                      f'letter-spacing="{f(size * 0.05)}" text-anchor="{anchor}" font-family="{SERIF}">{escape(ln)}</text>'
                      for k, ln in enumerate(lines))
        return out, len(lines) * size * lh

    # ------------------------------------------------ 3D（斜二测：深度往右上 30°）
    def obox(self, x, y, w, h, d, at):
        """细线底座：面淡入，边描出来。(x,y) 是正面左上角，d 是深度像素。"""
        p, dx, dy = self.p, d * C30, d * 0.5
        faces = (f'<path d="M{f(x)} {f(y)}H{f(x + w)}L{f(x + w + dx)} {f(y - dy)}H{f(x + dx)}Z" fill="{p["panel2"]}"/>'
                 f'<path d="M{f(x + w)} {f(y)}L{f(x + w + dx)} {f(y - dy)}V{f(y + h - dy)}L{f(x + w)} {f(y + h)}Z" fill="{p["side"]}"/>'
                 f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{p["panel"]}"/>')
        edges = (self.line([(x, y + h), (x, y), (x + dx, y - dy), (x + w + dx, y - dy), (x + w + dx, y + h - dy), (x + w, y + h), (x, y + h)], at, 0.8, None, 1, 0.55) +
                 self.line([(x, y), (x + w, y), (x + w + dx, y - dy)], at + 0.1, 0.6, None, 1, 0.55) +
                 self.line([(x + w, y), (x + w, y + h)], at + 0.2, 0.4, None, 1, 0.55))
        return self.fade(faces, at, 0.6) + edges

    def glass(self, name, x, y, w, h, at, rel, depth=22, frame=True):
        """磨砂玻璃立板。需要两张图：<name>_blur.jpg（整幅磨砂）和 <name>_win.jpg（清晰窗那一块）。
        rel = 清晰窗在整幅里的 (x, y, w, h) 比例。返回 (svg, 窗的像素框)。"""
        dx, dy = depth * C30, depth * 0.5
        thick = (f'<path d="M{f(x)} {f(y)}H{f(x + w)}L{f(x + w + dx)} {f(y - dy)}H{f(x + dx)}Z" fill="#4A4239" opacity="0.85"/>'
                 f'<path d="M{f(x + w)} {f(y)}L{f(x + w + dx)} {f(y - dy)}V{f(y + h - dy)}L{f(x + w)} {f(y + h)}Z" fill="#332D27" opacity="0.9"/>')
        img = f'<image href="{self.href(name + "_blur.jpg")}" x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" preserveAspectRatio="none"/>'
        wx, wy, ww, wh = x + rel[0] * w, y + rel[1] * h, rel[2] * w, rel[3] * h
        win = f'<image href="{self.href(name + "_win.jpg")}" x="{f(wx)}" y="{f(wy)}" width="{f(ww)}" height="{f(wh)}" preserveAspectRatio="none"/>'
        cut = (f'<rect x="{f(wx)}" y="{f(wy)}" width="{f(ww)}" height="{f(wh)}" fill="none" stroke="#FFFFFF" stroke-width="1.2" opacity="0">'
               f'<animate attributeName="opacity" values="0;0.3;0.7" keyTimes="0;0.01;1" begin="{ft(at + 0.5)}s" dur="0.6s" fill="freeze"/></rect>')
        out = self.fade(thick + img, at, 0.6) + self.fade(win, at + 0.5, 0.6) + cut
        if frame:
            out += self.line([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)], at, 0.8, None, 1, 0.5)
            out += self.line([(x, y), (x + dx, y - dy), (x + w + dx, y - dy), (x + w + dx, y + h - dy), (x + w, y + h)], at + 0.2, 0.6, None, 1, 0.4)
        return out, (wx, wy, ww, wh)

    def divider(self, y, left_to_right, at, mm0=0, span=560, ticks=50):
        """章节之间的等轴测斜向标尺：刻度逐格亮，一个关键测点沿线走过去。返回 (svg, 占的高度, 下一段起始毫米数)。"""
        M, W, c = self.M, self.W, self.p["line"]
        L = span / C30
        x0 = M + 40 if left_to_right else W - M - 40
        sx = 1 if left_to_right else -1
        x1, y1 = x0 + sx * span, y + L * 0.5
        ux, uy = sx * C30, 0.5
        nx, ny = (0.5, -C30) if left_to_right else (-0.5, -C30)
        out = [self.line([(x0, y), (x1, y1)], at, 1.2, None, 1.2, 0.75)]
        step = L / ticks
        for k in range(ticks + 1):
            px, py = x0 + ux * k * step, y + uy * k * step
            h = 16 if k % 10 == 0 else (10 if k % 5 == 0 else 5)
            t = at + 1.2 * k / ticks
            out.append(self.fade(f'<path d="M{f(px)} {f(py)}L{f(px + nx * h)} {f(py + ny * h)}" stroke="{c}" stroke-width="1" opacity="0.6"/>', t, 0.2))
            if k % 10 == 0:
                out.append(self.fade(self.mono(f"{mm0 + k}", px + nx * 34, py + ny * 34 + 4, 12, None, "middle", 0.1), t, 0.3))
        out.append(self.point(x0, y, at, True))
        out.append(self.fade(self.mono("mm", x1 + sx * 22, y1 + 5, 12, None, "middle", 0.1), at + 1.2))
        out.append(f'<g opacity="0" transform="translate({f(x0)} {f(y)})">'
                   f'<animate attributeName="opacity" values="0;1" begin="{ft(at)}s" dur="0.2s" fill="freeze"/>'
                   f'<animateTransform attributeName="transform" type="translate" values="{f(x0)} {f(y)};{f(x1)} {f(y1)}" '
                   f'begin="{ft(at)}s" dur="1.2s" fill="freeze" {EO}/>'
                   f'<circle r="9" fill="{self.p["bg"]}" stroke="{c}" stroke-width="1.4"/><circle r="2.2" fill="{c}"/></g>')
        return "".join(out), L * 0.5, mm0 + ticks


def frost_pair(src, crop, win, out_prefix, width=900, blur=0.011):
    """从一张照片做出玻璃立板要的两张图：整幅磨砂 + 清晰窗。crop / win 是像素框 (x0,y0,x1,y1)。返回 rel。"""
    from PIL import Image, ImageFilter
    im = Image.open(src).convert("RGB")
    whole = im.crop(crop)
    rel = ((win[0] - crop[0]) / whole.width, (win[1] - crop[1]) / whole.height,
           (win[2] - win[0]) / whole.width, (win[3] - win[1]) / whole.height)
    b = whole.filter(ImageFilter.GaussianBlur(whole.width * blur))
    b = Image.blend(b, Image.new("RGB", b.size, (236, 228, 214)), 0.07)

    def save(img, path, w):
        if img.width > w:
            img = img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)
        img.save(path, quality=84, optimize=True)
    save(b, f"{out_prefix}_blur.jpg", width)
    save(im.crop(win), f"{out_prefix}_win.jpg", round(width * rel[2]) + 40)
    return tuple(round(v, 4) for v in rel)
