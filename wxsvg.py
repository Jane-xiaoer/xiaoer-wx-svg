#!/usr/bin/env python3
"""公众号「自己长出来」的 SVG 时间轴文章生成器。

用法：python3 wxsvg.py script.json [-o out目录]
产出：
  long.svg      整张长图（带全部动画），可单独检查
  article.html  贴进公众号的片段（零高容器 + 长图 + 逐段拉长的空画布）
  preview.html  手机宽度预览页，带「重播」和「复制到公众号」按钮

原理：公众号删 JS / <style>，但保留 SVG 自带动画（animate / animateTransform）。
长图放在高度为 0 的容器里盖在页面上；下面一个透明空画布按时间点变宽，
宽高比固定所以高度跟着变，页面就一段段把长图露出来。
"""
import argparse
import json
import math
import sys
from html import escape
from pathlib import Path

EASE = 'calcMode="spline" keyTimes="0;1" keySplines="0.42 0 0.58 1"'


def num(v):
    return f"{v:g}" if isinstance(v, (int, float)) else str(v)


def attrs(d):
    return " ".join(f'{k}="{escape(num(v), quote=True)}"' for k, v in d.items() if v is not None)


# ---------- 动画片段 ----------

def anim(attr, frm, to, at, dur, extra=""):
    return (f'<animate attributeName="{attr}" values="{num(frm)};{num(to)}" begin="{num(at)}s" '
            f'dur="{num(dur)}s" fill="freeze" {EASE}{extra}/>')


def anim_tf(kind, frm, to, at, dur):
    return (f'<animateTransform attributeName="transform" type="{kind}" values="{frm};{to}" '
            f'begin="{num(at)}s" dur="{num(dur)}s" fill="freeze" {EASE}/>')


def char_w(ch, size):
    """估字宽：全角字 = 字号，半角约 0.58 字号（等宽字体 0.6）。逐字打字定位用。"""
    return size if ord(ch) > 0x2E7F else size * 0.58


def stroke_len(el):
    t = el["type"]
    if t == "line":
        return math.hypot(el["x2"] - el["x1"], el["y2"] - el["y1"])
    if t == "rect":
        return 2 * (el["w"] + el["h"])
    if t == "circle":
        return 2 * math.pi * el["r"]
    return 100  # path 用 pathLength="100"


# ---------- 图形 ----------

def shape(el, font, inner=""):
    t = el["type"]
    color = el.get("color", "#ffffff")
    common = {"opacity": el.get("opacity_from", 0) if el.get("fx", "fade") != "none" else None}
    if t == "text":
        lines = str(el["text"]).split("\n")
        size = el.get("size", 48)
        lh = el.get("line_height", 1.4) * size
        a = {"x": el["x"], "y": el["y"], "font-size": size, "fill": color,
             "font-family": el.get("font", font), "font-weight": el.get("weight", 400),
             "text-anchor": {"left": "start", "center": "middle", "right": "end"}.get(el.get("align", "center")),
             "letter-spacing": el.get("spacing"), **common}
        if el.get("fx") == "type":
            # 逐字出现：每个字单独一个 <text>，靠 opacity 淡入。
            # 微信会删 fill-opacity 动画（实测），tspan 方案在公众号里字永远是隐形的。
            step = el.get("step", 0.06)
            a.update({"opacity": 0, "text-anchor": "start"})
            out, i = [], 0
            for n, line in enumerate(lines):
                widths = [char_w(ch, size) for ch in line]
                total = sum(widths)
                x0 = {"left": el["x"], "right": el["x"] - total}.get(el.get("align", "center"), el["x"] - total / 2)
                for ch, w in zip(line, widths):
                    if ch.strip():
                        b = {**a, "x": round(x0, 1), "y": round(el["y"] + n * lh, 1)}
                        out.append(f'<text {attrs(b)}>{escape(ch)}'
                                   f'{anim("opacity", 0, 1, round(el["at"] + i * step, 3), 0.15)}</text>')
                    x0 += w
                    i += 1
            return f'<g>{"".join(out)}{inner}</g>'
        spans = "".join(f'<tspan x="{num(el["x"])}" dy="{num(lh if n else 0)}">{escape(l)}</tspan>'
                        for n, l in enumerate(lines))
        return f'<text {attrs(a)}>{spans}{inner}</text>'

    paint = {"fill": el.get("fill", "none" if el.get("fx") == "draw" else color),
             "stroke": el.get("stroke", color if el.get("fx") == "draw" or t in ("line", "path") else None),
             "stroke-width": el.get("stroke_width", 4 if el.get("fx") == "draw" or t in ("line", "path") else None),
             "stroke-linecap": "round" if t in ("line", "path") else None, **common}
    if el.get("fx") == "draw":
        L = stroke_len(el)
        paint.update({"opacity": None, "stroke-dasharray": round(L, 2), "stroke-dashoffset": round(L, 2)})
        if t == "path":
            paint["pathLength"] = 100
    if t == "rect":
        g = {"x": el["x"], "y": el["y"], "width": el["w"], "height": el["h"], "rx": el.get("radius")}
    elif t == "circle":
        g = {"cx": el["x"], "cy": el["y"], "r": el["r"]}
    elif t == "line":
        g = {"x1": el["x1"], "y1": el["y1"], "x2": el["x2"], "y2": el["y2"]}
    elif t == "path":
        g = {"d": el["d"]}
    elif t == "image":
        g = {"x": el["x"], "y": el["y"], "width": el["w"], "height": el["h"], "href": el["src"],
             "preserveAspectRatio": "xMidYMid slice"}
        paint = common
    else:
        sys.exit(f"不认识的元素类型：{t}")
    tag = {"rect": "rect", "circle": "circle", "line": "line", "path": "path", "image": "image"}[t]
    return f'<{tag} {attrs({**g, **paint})}>{inner}</{tag}>'


def center(el):
    t = el["type"]
    if t in ("rect", "image"):
        return el["x"] + el["w"] / 2, el["y"] + el["h"] / 2
    if t == "line":
        return (el["x1"] + el["x2"]) / 2, (el["y1"] + el["y2"]) / 2
    return el.get("cx", el.get("x", 0)), el.get("cy", el.get("y", 0))


def element(el, font):
    if el["type"] == "raw":
        # 手写的 SVG 片段原样放进去（复杂图形用）。只用微信保留的动画属性：
        # opacity / transform / stroke-dashoffset / width
        return el["svg"]
    fx = el.get("fx", "fade")
    at = el.get("at", 0)
    dur = el.get("dur", 0.8)
    out = el.get("out")
    fade_in = anim("opacity", 0, 1, at, dur) if fx in ("fade", "rise", "zoom") else ""
    fade_out = anim("opacity", 1, 0, out, el.get("out_dur", 0.5)) if out is not None else ""
    if fx == "draw":
        L = round(stroke_len(el), 2)
        body = shape(el, font, anim("stroke-dashoffset", L, 0, at, dur) + fade_out)
        return body
    if fx in ("none", "type"):
        return shape(el, font, fade_out)
    body = shape(el, font, fade_in + fade_out)
    if fx == "rise":
        d = el.get("distance", 60)
        return (f'<g transform="translate(0 {num(d)})">{anim_tf("translate", f"0 {num(d)}", "0 0", at, dur)}'
                f'{body}</g>')
    if fx == "zoom":
        cx, cy = center(el)
        s = el.get("from_scale", 0.6)
        return (f'<g transform="translate({num(cx)} {num(cy)})"><g transform="scale({num(s)})">'
                f'{anim_tf("scale", num(s), 1, at, dur)}'
                f'<g transform="translate({num(-cx)} {num(-cy)})">{body}</g></g></g>')
    return body


def loop(el, inner):
    """可选的循环小动效：float 上下浮动 / pulse 呼吸 / spin 旋转。"""
    kind = el.get("loop")
    if not kind:
        return inner
    p = el.get("loop_period", 3)
    begin = num(el.get("at", 0) + el.get("dur", 0.8))
    if kind == "float":
        a = el.get("loop_amp", 12)
        m = (f'<animateTransform attributeName="transform" type="translate" values="0 0;0 {-a};0 0" '
             f'begin="{begin}s" dur="{num(p)}s" repeatCount="indefinite"/>')
        return f'<g>{m}{inner}</g>'
    cx, cy = center(el)
    if kind == "spin":
        m = (f'<animateTransform attributeName="transform" type="rotate" values="0 {num(cx)} {num(cy)};'
             f'360 {num(cx)} {num(cy)}" begin="{begin}s" dur="{num(p)}s" repeatCount="indefinite"/>')
        return f'<g>{m}{inner}</g>'
    if kind == "pulse":
        m = (f'<animateTransform attributeName="transform" type="scale" values="1;1.06;1" '
             f'begin="{begin}s" dur="{num(p)}s" repeatCount="indefinite"/>')
        return (f'<g transform="translate({num(cx)} {num(cy)})"><g>{m}'
                f'<g transform="translate({num(-cx)} {num(-cy)})">{inner}</g></g></g>')
    sys.exit(f"不认识的 loop：{kind}")


# ---------- 组装 ----------

def build(spec):
    W = spec.get("width", 1080)
    H = spec["height"]
    first = spec.get("first_screen", 1920)
    font = spec.get("font", "'PingFang SC', 'Noto Sans SC', 'Microsoft YaHei', sans-serif")
    bg = spec.get("background", "#000000")
    els = "".join(loop(e, element(e, font)) for e in spec["elements"])
    long_svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
                f'style="display:block;width:100%;line-height:0;">'
                f'<rect x="0" y="0" width="{W}" height="{H}" fill="{bg}"/>{els}</svg>')

    # 空画布：宽度百分比 = 目标高度 / 首屏高度 × 100%
    reveals = sorted(spec.get("reveals", []))
    if reveals and reveals[-1][1] > H:
        sys.exit(f"reveals 最后拉到 {reveals[-1][1]}，超过长图高度 {H}")
    rd = spec.get("reveal_dur", 0.6)
    steps, prev = [], 100.0
    for t, y in reveals:
        pct = round(y / first * 100, 3)
        steps.append(f'<animate attributeName="width" values="{num(prev)}%;{num(pct)}%" begin="{num(t)}s" '
                     f'dur="{num(rd)}s" fill="freeze" restart="never" {EASE}/>')
        prev = pct
    canvas = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {first}" width="100%" '
              f'style="display:block;max-width:none!important;pointer-events:none;">{"".join(steps)}</svg>')

    article = (
        f'<section style="overflow:hidden;line-height:0;text-align:center;background-color:{bg};">'
        f'<section style="height:0;overflow:visible;line-height:0;width:100%;">{long_svg}</section>'
        f'{canvas}</section>')
    return long_svg, article


PREVIEW = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} 预览</title>
<style>
  body{{margin:0;background:#e9e9ec;font-family:-apple-system,'PingFang SC',sans-serif;}}
  .bar{{position:sticky;top:0;z-index:9;display:flex;gap:8px;justify-content:center;padding:10px;
        background:#fff;border-bottom:1px solid #ddd;}}
  button{{font-size:14px;padding:6px 14px;border-radius:6px;border:1px solid #bbb;background:#fafafa;cursor:pointer;}}
  #msg{{font-size:13px;color:#555;align-self:center;}}
  .phone{{width:375px;max-width:100%;margin:16px auto;background:#fff;box-shadow:0 4px 24px rgba(0,0,0,.12);}}
  .phone h1{{font-size:20px;padding:16px 16px 8px;margin:0;}}
  .phone .meta{{font-size:13px;color:#888;padding:0 16px 16px;}}
  .tail{{padding:24px 16px;font-size:14px;color:#888;}}
</style></head><body>
<div class="bar"><button onclick="replay()">重播</button>
<button onclick="copyIt()">复制到公众号</button><span id="msg"></span></div>
<div class="phone"><h1>{title}</h1><div class="meta">预览 · 动画从打开页面那一刻开始计时</div>
<div id="art"></div><div class="tail">（正文结束）</div></div>
<template id="src">{article}</template>
<script>
const src=document.getElementById('src').innerHTML;
function replay(){{const a=document.getElementById('art');a.innerHTML='';
  requestAnimationFrame(()=>{{a.innerHTML=src;}});}}
async function copyIt(){{const m=document.getElementById('msg');
  try{{await navigator.clipboard.write([new ClipboardItem({{
    'text/html':new Blob([src],{{type:'text/html'}}),'text/plain':new Blob([src],{{type:'text/plain'}})}})]);
    m.textContent='已复制，去公众号编辑器里粘贴';}}catch(e){{m.textContent='复制失败：'+e;}}}}
replay();
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser(description="公众号 SVG 时间轴文章生成器")
    ap.add_argument("script", help="脚本 JSON")
    ap.add_argument("-o", "--out", help="输出目录（默认：脚本同名文件夹）")
    a = ap.parse_args()
    sp = Path(a.script)
    spec = json.loads(sp.read_text(encoding="utf-8"))
    out = Path(a.out) if a.out else Path.cwd() / "out" / sp.stem
    out.mkdir(parents=True, exist_ok=True)
    long_svg, article = build(spec)
    (out / "long.svg").write_text(long_svg, encoding="utf-8")
    (out / "article.html").write_text(article, encoding="utf-8")
    title = escape(spec.get("title", sp.stem))
    (out / "preview.html").write_text(
        PREVIEW.format(title=title, article=article.replace("</template", "<\\/template")), encoding="utf-8")
    kb = len(article.encode()) / 1024
    print(f"✅ {out}/  article.html {kb:.0f}KB · {len(spec['elements'])} 个元素 · {len(spec.get('reveals', []))} 次拉长")
    if kb > 1000:
        print("⚠️ 超过 1MB，公众号可能存不下，删减元素或拆成两篇")


if __name__ == "__main__":
    main()
