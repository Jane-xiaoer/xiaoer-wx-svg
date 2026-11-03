#!/usr/bin/env python3
"""分镜 JSON → 公众号动效文章（一条命令）。

  python3 motion/make.py 分镜.json                 生成 article.html / long.svg / preview.html / cover.jpg
  python3 motion/make.py 分镜.json --push          另外推进公众号草稿箱（新建一篇）
  python3 motion/make.py 分镜.json --push --update <media_id>   更新已有草稿

分镜格式见 motion/STORYBOARD.md。
"""
import argparse
import json
import os
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import scenes  # noqa: E402
import scenes_extra  # noqa: E402
import themes  # noqa: E402
import wxsvg  # noqa: E402

scenes.SCENES.update(scenes_extra.SCENES)


def build(sb):
    th = themes.get(sb.get("theme", "graphite-green"))
    items = sb.get("scenes") or sys.exit("分镜里没有 scenes")
    els, reveals, t = [], [], 0.0
    for k, sc in enumerate(items):
        kind = sc.get("type")
        if kind not in scenes.SCENES:
            sys.exit(f"第 {k + 1} 屏类型「{kind}」不存在，可选：{' / '.join(scenes.SCENES)}")
        if k:
            reveals.append([round(t - 0.4, 2), (k + 1) * scenes.SCREEN])
        part, dur = scenes.SCENES[kind](sc, k * scenes.SCREEN, t, th)
        els += part
        t += dur
    spec = {"width": scenes.W, "height": scenes.SCREEN * len(items), "first_screen": scenes.SCREEN,
            "background": th["bg"], "reveals": reveals, "reveal_dur": 0.9,
            "elements": [{"type": "raw", "svg": e} for e in els]}
    _, article = wxsvg.build(spec)
    tail = "".join(f'<p style="text-align:center;font-size:{14 if i == 0 else 12}px;color:#{"888" if i == 0 else "aaa"};'
                   f'margin:{24 if i == 0 else 0}px 0 {8 if i == 0 else 24}px;">{escape(line)}</p>'
                   for i, line in enumerate(sb.get("tail", [])[:2]))
    return article + tail, t, len(items), th


COVER = """<!doctype html><html><body style="margin:0;width:900px;height:383px;background:{bg};overflow:hidden">
<svg width="900" height="383" viewBox="0 0 900 383" xmlns="http://www.w3.org/2000/svg">
<path d="{grid}" stroke="{a}" stroke-width="1" opacity="0.08"/>
<circle cx="190" cy="191" r="150" fill="none" stroke="{a}" stroke-width="2" opacity="0.25"/>
<circle cx="190" cy="191" r="118" fill="none" stroke="{a}" stroke-width="2" opacity="0.45"/>
<circle cx="190" cy="191" r="86" fill="none" stroke="{a}" stroke-width="14"/>
<circle cx="206" cy="181" r="30" fill="{a}"/>
<text x="380" y="{by}" font-size="{bs}" font-weight="800" fill="{text}" font-family="PingFang SC">{brand}</text>
<text x="384" y="222" font-size="34" font-weight="700" fill="{a}" font-family="Menlo, PingFang SC">{slogan}</text>
<text x="384" y="282" font-size="{ts}" font-weight="600" fill="{text}" font-family="PingFang SC">{title}</text>
</svg></body></html>"""


def cover(sb, th, out):
    try:
        import asyncio
        from playwright.async_api import async_playwright
    except ImportError:
        print("⚠️ 没装 playwright，跳过封面；推送时用 --cover 指定一张 900×383 的图")
        return None
    first = next((s for s in sb["scenes"] if s.get("type") == "collapse"), {})
    brand = sb.get("brand") or first.get("brand", "")
    title = sb.get("cover_line") or sb.get("title", "")
    grid = "".join(f"M{x} 0V383" for x in range(0, 901, 40)) + "".join(f"M0 {y}H900" for y in range(0, 384, 40))
    html = COVER.format(bg=th["bg"], a=th["accent"], text=th["text"], grid=grid,
                        brand=escape(brand), bs=88 if len(brand) <= 6 else 64, by=168,
                        slogan=escape(sb.get("slogan") or first.get("slogan", "")),
                        title=escape(title), ts=30 if len(title) <= 16 else 24)
    page = out / "_cover.html"
    page.write_text(html, encoding="utf-8")

    async def shot():
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await b.new_page(viewport={"width": 900, "height": 383})
            await pg.goto(page.resolve().as_uri())
            await pg.screenshot(path=str(out / "cover.jpg"), type="jpeg", quality=92)
            await b.close()
    try:
        asyncio.run(shot())
    except Exception as e:  # 常见：没跑 python3 -m playwright install chromium
        print(f"⚠️ 封面没出成（{str(e).splitlines()[0][:80]}）。文章照常生成；要封面先跑 "
              "python3 -m playwright install chromium，或推送时 --cover 指定一张 900×383 的图")
        return None
    finally:
        page.unlink(missing_ok=True)
    return out / "cover.jpg"


def render(sb, out, cover_path=None):
    """生成 article.html / preview.html / cover.jpg，返回 (秒数, 屏数, KB, 封面路径)。"""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    article, total, screens, th = build(sb)
    title = sb.get("title", out.name)
    (out / "article.html").write_text(article, encoding="utf-8")
    (out / "preview.html").write_text(wxsvg.PREVIEW.format(
        title=escape(title), article=article.replace("</template", "<\\/template")), encoding="utf-8")
    cv = Path(cover_path) if cover_path else cover(sb, th, out)
    return total, screens, len(article.encode()) / 1024, cv


def push(sb, out, cover_path, update=None):
    """推进草稿箱（update 给 media_id 就更新），返回 media_id。用 motion/config.py 里配的公众号。"""
    import wechat
    out = Path(out)
    article = (out / "article.html").read_text(encoding="utf-8")
    mid = wechat.save_draft(article, sb.get("title", out.name), cover_path, sb.get("author", ""),
                            sb.get("digest", ""), update)
    (out / "media_id.txt").write_text(mid)
    return mid


def main():
    ap = argparse.ArgumentParser(description="分镜 JSON → 公众号动效文章")
    ap.add_argument("storyboard")
    ap.add_argument("-o", "--out")
    ap.add_argument("--push", action="store_true", help="推进公众号草稿箱")
    ap.add_argument("--update", help="更新这篇草稿（media_id），不新建")
    ap.add_argument("--cover", help="自己指定封面图")
    a = ap.parse_args()
    sp = Path(a.storyboard)
    sb = json.loads(sp.read_text(encoding="utf-8"))
    out = Path(a.out) if a.out else Path.cwd() / "out" / sp.stem
    total, screens, kb, cv = render(sb, out, a.cover)
    print(f"✅ {out}/  {screens} 屏 · {total:.0f} 秒 · {kb:.0f}KB")
    if kb > 1000:
        print("⚠️ 超过 1MB，公众号可能存不下，减几屏")
    if a.push:
        if not cv:
            sys.exit("没有封面，推送需要 --cover")
        mid = push(sb, out, cv, a.update)
        print(f"✅ 已进草稿箱 media_id={mid}")
        import wechat
        for tag, local, remote in wechat.check(mid, (out / "article.html").read_text(encoding="utf-8")):
            print(f"  {tag:18} 本地 {local:>5}  草稿 {remote:>5}{'  ⚠️ 被删了' if remote < local else ''}")


if __name__ == "__main__":
    main()
