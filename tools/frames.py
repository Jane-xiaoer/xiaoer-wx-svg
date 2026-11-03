"""截帧检查：把 SVG 时间轴跳到指定秒数，截某一屏，拼成一张图。

  python3 tools/frames.py out/<名字>/preview.html out/<名字>/frames.png 秒,屏 秒,屏 ...

- 秒：看 out/<名字>/timeline.json（每屏 / 每站几秒开始）。想看某屏画完的样子，填「下一屏开始的秒数」。
- 屏：按 1080×1920 一屏切，从 0 数，可以写小数（1.5 = 第 2 屏下半到第 3 屏上半）。
  等轴测是一整张长图，「屏」不等于「站」：大约每 0.3 屏一站，先截 0、1、2 看位置再调。
- 同一个秒数可以截多张；中间图放在系统临时目录，不会留在 out/ 里。
"""
import asyncio
import sys
import tempfile
from pathlib import Path

from playwright.async_api import async_playwright
from PIL import Image


async def main(src, dst, shots):
    tmp = Path(tempfile.mkdtemp(prefix="frames-"))
    files = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 375, "height": 760}, device_scale_factor=2)
        await pg.goto(src if "://" in src else Path(src).resolve().as_uri())
        await pg.wait_for_timeout(300)
        for i, (t, scr) in enumerate(shots):
            await pg.evaluate(f"document.querySelectorAll('#art svg').forEach(s=>{{s.pauseAnimations();s.setCurrentTime({t})}})")
            await pg.wait_for_timeout(120)
            top = await pg.evaluate("document.getElementById('art').getBoundingClientRect().top+scrollY")
            h = 375 * 1920 / 1080
            f = tmp / f"{i:02d}.png"
            await pg.screenshot(path=str(f), full_page=True, clip={"x": 0, "y": top + scr * h, "width": 375, "height": h})
            files.append(f)
        await b.close()
    ims = [Image.open(f) for f in files]
    w, h = ims[0].size
    cols = min(len(ims), 6)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (w + 16), rows * (h + 16)), "white")
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * (w + 16), (i // cols) * (h + 16)))
    sheet.resize((sheet.width // 2, sheet.height // 2)).save(dst)
    print(f"✅ {dst}  {len(ims)} 张")


if __name__ == "__main__":
    shots = [tuple(float(x) for x in a.split(",")) for a in sys.argv[3:]]
    asyncio.run(main(sys.argv[1], sys.argv[2], shots))
