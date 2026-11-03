"""用法：python3 frames.py preview.html out.png 秒,屏 秒,屏 ...  —— 把 SVG 时间轴跳到指定秒截图拼一张。"""
import sys,asyncio
from playwright.async_api import async_playwright
from PIL import Image
async def main(src,dst,shots):
    async with async_playwright() as p:
        b=await p.chromium.launch()
        pg=await b.new_page(viewport={'width':375,'height':760},device_scale_factor=2)
        await pg.goto('file://'+src); await pg.wait_for_timeout(300)
        ims=[]
        for t,scr in shots:
            await pg.evaluate(f"document.querySelectorAll('#art svg').forEach(s=>{{s.pauseAnimations();s.setCurrentTime({t})}})")
            await pg.wait_for_timeout(120)
            top=await pg.evaluate("document.getElementById('art').getBoundingClientRect().top+scrollY")
            h=375*1920/1080
            f=dst+f'.{t}.png'
            await pg.screenshot(path=f,full_page=True,clip={'x':0,'y':top+scr*h,'width':375,'height':h})
            ims.append(Image.open(f))
        await b.close()
    w,h=ims[0].size
    cols=min(len(ims),6); rows=(len(ims)+cols-1)//cols
    sheet=Image.new('RGB',(cols*(w+16),rows*(h+16)),'white')
    for i,im in enumerate(ims): sheet.paste(im,((i%cols)*(w+16),(i//cols)*(h+16)))
    sheet.resize((sheet.width//2,sheet.height//2)).save(dst)
shots=[tuple(float(x) if '.' in x else int(x) for x in a.split(',')) for a in sys.argv[3:]]
asyncio.run(main(sys.argv[1],sys.argv[2],shots))
