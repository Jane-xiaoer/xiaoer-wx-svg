"""改完以后自己看：把本地预览页在指定时刻的样子截下来，拼成一排。

用法：
    python3 frames.py <preview.html 路径> <输出前缀> <每排几张> t1 t2 t3 ...
    例：python3 frames.py out/preview.html out/chk/a 4 0.5 2.0 3.5 5.0

默认截「读者那一刻看到的画面」（已经推开的区域最底下一屏）。想盯着某一块看：
    Y0=3600 HH=500 python3 frames.py ...      # 固定截画布上 y=3600 起、500 高的一块（750 宽的坐标）
    SCALE=2.4 ...                              # 放大倍数（看遮挡、接缝、细线用 2–3）
    VH=700 ...                                 # 一屏多高（CSS 像素，手机大约 650–700）

为什么不直接在浏览器里看：动画是按时间走的，眼睛盯不住某一帧；截下来才能看清楚谁压着谁、哪里叠了、哪里有缝。
非整数 SCALE 截出来有时会看到一条横向细线，那是截图的假象；用 SCALE=3 再截一次，没有就是没事。
"""
import asyncio, os, sys
from pathlib import Path
from playwright.async_api import async_playwright
from PIL import Image, ImageDraw

page_path, out, per = Path(sys.argv[1]).resolve(), sys.argv[2], int(sys.argv[3])
ts = [float(x) for x in sys.argv[4:]]
SC, VH = float(os.environ.get("SCALE", "1.2")), int(os.environ.get("VH", "660"))
Y0, HH = os.environ.get("Y0"), os.environ.get("HH")
Path(out).parent.mkdir(parents=True, exist_ok=True)


async def main():
    ims = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 375, "height": 900}, device_scale_factor=SC)
        await pg.goto(page_path.as_uri()); await pg.wait_for_timeout(2500)
        await pg.evaluate("document.querySelector('.bar') && (document.querySelector('.bar').style.display='none')")
        for t in ts:
            await pg.evaluate(f"document.querySelectorAll('#art svg').forEach(s=>{{s.pauseAnimations();s.setCurrentTime({t})}})")
            await pg.wait_for_timeout(180)
            h = await pg.evaluate("document.querySelector('#art').getBoundingClientRect().height")
            y, hh = (float(Y0) / 2, float(HH) / 2) if Y0 else (max(0, h - VH), VH)
            tmp = out + "_tmp.png"
            await pg.screenshot(path=tmp, clip={"x": 0, "y": y, "width": 375, "height": hh}, full_page=True)
            ims.append((t, y * 2, h * 2, Image.open(tmp).convert("RGB")))
        await b.close()
    for k, i in enumerate(range(0, len(ims), per)):
        grp = ims[i:i + per]; w, h = grp[0][3].size
        sheet = Image.new("RGB", (len(grp) * (w + 8), h + 26), "white"); d = ImageDraw.Draw(sheet)
        for j, (t, y, H, im) in enumerate(grp):
            sheet.paste(im, (j * (w + 8), 26))
            d.text((j * (w + 8) + 4, 6), f"t={t}  y={y:.0f}-{y + im.size[1] * 2 / SC:.0f}  revealed={H:.0f}", fill=(200, 0, 0))
        name = f"{out}_{k:02d}.jpg"; sheet.save(name, quality=85); print(name)

asyncio.run(main())
