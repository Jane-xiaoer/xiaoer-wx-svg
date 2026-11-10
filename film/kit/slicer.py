"""把一张很长的 SVG 按纵向切成多张短的。

为什么要切：iPhone 微信跑不动一张几千高、几百个动画的 SVG（动画不启动或很卡）。切成 800–1000 高一张就没事。
怎么切：用无头浏览器把每个顶层元素在整条时间线上「到过的纵向范围」量出来，然后在目标高度附近找一条
「被它切到的元素字节数最少」的横线切开。被切到的元素两边各放一份（各自被 viewBox 裁掉一半；时间线一样，所以接缝处是连着的）。

三个容易踩的坑（都踩过）：
1. 带 translate 动画的元素必须写初始 transform。不写的话它起飞前停在 (0,0)，量出来的范围是「页面顶 → 终点」，会被收进每一张切片。
2. 选缝要按字节数，不是按个数。一张转曲文字很多的卡片被切到，就整块重复一遍，正文直接超限。
3. 选缝时判断「会不会被重复」的边界要和实际收元素的边界一样（这里都是 +4 / -2），差几个单位也会重复。
"""
import json, re, subprocess, sys
from pathlib import Path

MEASURE = r'''
import asyncio, json, sys
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width':750,'height':1000})
        await pg.goto(sys.argv[1]); await pg.wait_for_timeout(1500)
        r = await pg.evaluate("""(T)=>{const s=document.querySelector('svg'); s.pauseAnimations();
          const kids=[...s.children], vb=s.viewBox.baseVal, lo=kids.map(()=>1e9), hi=kids.map(()=>-1e9);
          for(let t=0;t<=T;t+=0.1){ s.setCurrentTime(t); const R=s.getBoundingClientRect(), k=vb.height/R.height;
            kids.forEach((c,i)=>{const r=c.getBoundingClientRect(); if(r.width===0&&r.height===0) return;
              lo[i]=Math.min(lo[i],(r.top-R.top)*k); hi[i]=Math.max(hi[i],(r.bottom-R.top)*k);});}
          return {n:kids.length, lo, hi};}""", float(sys.argv[2]))
        print(json.dumps(r)); await b.close()
asyncio.run(main())
'''


def children(svg):
    """把 <svg>…</svg> 拆成 (开头标签, [顶层子元素字符串])。"""
    m = re.match(r'(<svg[^>]*>)(.*)</svg>\s*$', svg, re.S)
    head, body = m.group(1), m.group(2)
    out, depth, start = [], 0, None
    for mt in re.finditer(r'<(/?)([a-zA-Z]+)[^>]*?(/?)>', body):
        close, selfc = mt.group(1) == "/", mt.group(3) == "/"
        if depth == 0 and not close:
            start = mt.start()
            if selfc:
                out.append(body[start:mt.end()]); continue
            depth = 1; continue
        if close:
            depth -= 1
            if depth == 0:
                out.append(body[start:mt.end()])
        elif not selfc:
            depth += 1
    return head, out


def measure(svg, T, work):
    work = Path(work); work.mkdir(parents=True, exist_ok=True)
    page = work / "_measure.html"
    import svgkit
    page.write_text('<!doctype html><body style="margin:0;width:750px">' + svg.replace('href="assets/', f'href="{svgkit.ASSETS.resolve().as_uri()}/') + '</body>', encoding="utf-8")
    py = work / "_measure_run.py"; py.write_text(MEASURE)
    r = subprocess.run([sys.executable, str(py), page.as_uri(), str(T)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("量元素范围失败（要先 pip install playwright && playwright install chromium）：\n" + r.stderr[-800:])
    return json.loads(r.stdout)


def split(svg, H, T=80, target=850, slack=260, work="out"):
    """返回 (切片字符串列表, [(起, 止, 元素数, 图片数, 动画数, KB)])。target：每张大概多高；slack：允许上下浮动多少去找好切的地方。"""
    head, kids = children(svg)
    m = measure(svg, T, work)
    assert m["n"] == len(kids), (m["n"], len(kids))
    span = list(zip(m["lo"], m["hi"]))
    full = {i for i, (lo, hi) in enumerate(span) if lo <= 1 and hi >= H - 1}          # 底色之类，每张都要

    def weight(y):       # 在 y 处切一刀，会被重复一份的字节数
        return sum(len(kids[i]) for i, (lo, hi) in enumerate(span) if i not in full and lo < y + 4 and hi > y - 2)

    cuts, y = [0], 0
    while H - y > target + slack:
        best = min(range(int(y + target - slack), int(y + target + slack), 2), key=lambda c: (weight(c) // 2000, abs(c - y - target)))
        cuts.append(best); y = best
    cuts.append(H)
    vb = re.search(r'viewBox="0 0 (\d+) ', head).group(1)
    out, info = [], []
    for a, b in zip(cuts, cuts[1:]):
        sel = "".join(k for i, k in enumerate(kids) if span[i][0] < b + 4 and span[i][1] > a - 2)
        ov = 2 if b < H else 0        # 往下多画 2 单位，再用负 margin 收回：手机上小数像素不会露出一条缝
        h2 = head.replace(f'viewBox="0 0 {vb} {H}"', f'viewBox="0 {a} {vb} {b - a + ov}"')
        if ov:
            h2 = h2.replace('style="', f'style="margin-bottom:-{ov / int(vb) * 100:.4f}%;', 1)
        s = h2 + sel + "</svg>"
        out.append(s)
        info.append((a, b, sel.count("<g") + sel.count("<path") + sel.count("<image"), sel.count("<image"),
                     sel.count("<animate") + sel.count("<set"), len(s.encode()) / 1024))
    return out, info
