"""封面：从本地预览截一帧，裁成 900×383（公众号头图比例 2.35:1）。

    python3 cover.py <preview.html> <第几秒> <从画布哪个 y 开始裁> [输出 out/cover.jpg]
    例：python3 cover.py out/preview.html 3.5 392

裁的高度固定是 319（750 宽下的 2.35:1）。挑时刻的讲究：
- 主角色要睁着眼、站稳、不在做大动作的那一帧（眨眼帧、挥手帧截出来会很怪）。
- 正文里修过的素材（比如补了缺口的床）封面也会跟着变；所以改了开头就重截一次封面。封面是单独上传的图，不会自己更新。
- 公众号列表里标题会压在封面左下角，重要的东西别放那儿。
"""
import asyncio, sys
from pathlib import Path
from playwright.async_api import async_playwright
from PIL import Image

page, T, Y0 = Path(sys.argv[1]).resolve(), float(sys.argv[2]), float(sys.argv[3])
out = Path(sys.argv[4]) if len(sys.argv) > 4 else page.parent / "cover.jpg"


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 375, "height": 900}, device_scale_factor=4)
        await pg.goto(page.as_uri()); await pg.wait_for_timeout(2500)
        await pg.evaluate("document.querySelector('.bar') && (document.querySelector('.bar').style.display='none')")
        await pg.evaluate(f"document.querySelectorAll('#art svg').forEach(s=>{{s.pauseAnimations();s.setCurrentTime({T})}})")
        await pg.wait_for_timeout(500)
        await pg.screenshot(path=str(out.with_suffix(".src.png")), clip={"x": 0, "y": Y0 / 2, "width": 375, "height": 159.5}, full_page=True)
        await b.close()

asyncio.run(main())
Image.open(out.with_suffix(".src.png")).convert("RGB").resize((900, 383), Image.LANCZOS).save(out, quality=90)
print(out)
