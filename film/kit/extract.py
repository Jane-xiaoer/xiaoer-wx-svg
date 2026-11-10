"""从片子里取素材。需要 ffmpeg（brew install ffmpeg / apt install ffmpeg）。

    python3 extract.py sheet  片子.mp4 [开始秒] [时长] [每秒几张]     # 联系表：把一段片子拼成一张大图，找镜头用
    python3 extract.py frames 片子.mp4 名字 t1 t2 t3 ... [--w 600]    # 抽指定时刻的帧 → assets/win/名字_0.jpg …（场景窗用）
    python3 extract.py cutout 图.png 输出.png [--w 620]               # 抠掉背景（要 pip install rembg），再量化到 256 色
    python3 extract.py shrink assets/*.png                             # 把 RGBA 图量化到 256 色，体积小一半以上
    python3 extract.py grid   图.png                                   # 给一张图画上坐标网格（定切件位置、转轴、遮挡时用）

联系表上每格左上角有时间。先看联系表，再决定抽哪几秒；不要凭记忆猜镜头在哪。
"""
import subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw


def sheet(video, start=0, dur=None, fps=2, cols=8, cellw=300):
    video = Path(video)
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout or 0)
    start = float(start); dur = float(dur) if dur else total - start
    n = int(dur * float(fps)); rows = max(1, -(-n // cols))
    out = video.with_name(f"{video.stem}_sheet_{int(start)}s.jpg")
    vf = (f"fps={fps},scale={cellw}:-1,drawtext=text='%{{pts\\:hms\\:{start}}}':x=4:y=4:fontsize=14:fontcolor=white:box=1:boxcolor=black@0.6,"
          f"tile={cols}x{rows}")
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(dur), "-i", str(video), "-vf", vf, "-frames:v", "1", str(out)], capture_output=True, text=True)
    if r.returncode:        # 有的 ffmpeg 没编进 drawtext，就不打时间戳
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(dur), "-i", str(video), "-vf", f"fps={fps},scale={cellw}:-1,tile={cols}x{rows}", "-frames:v", "1", str(out)], check=True)
        print(f"（没打上时间戳：第 n 格 = {start} + n / {fps} 秒，从 0 数、从左到右、从上到下）")
    print(out, f"共 {n} 格，每格间隔 {1 / float(fps):.2f} 秒")


def frames(video, name, times, w=600, outdir="assets/win"):
    Path(outdir).mkdir(parents=True, exist_ok=True)
    for k, t in enumerate(times):
        tmp = Path(outdir) / f"_{name}_{k}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(video), "-frames:v", "1", str(tmp)], check=True)
        im = Image.open(tmp).convert("RGB"); im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        out = Path(outdir) / f"{name}_{k}.jpg"; im.save(out, quality=80, optimize=True, progressive=True); tmp.unlink()
        print(out, im.size, f"{out.stat().st_size / 1024:.0f}KB")


def quant(im):
    return im.convert("RGBA").quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)


def cutout(src, dst, w=None):
    try:
        from rembg import remove
    except ImportError:
        raise SystemExit("要先 pip install rembg（或者用任何抠图工具抠好，存成透明底 PNG，再用 shrink 压一下）")
    im = remove(Image.open(src).convert("RGBA"))
    bb = im.getbbox(); im = im.crop(bb)
    if w:
        im = im.resize((int(w), round(im.height * int(w) / im.width)), Image.LANCZOS)
    quant(im).save(dst, optimize=True); print(dst, im.size)


def shrink(files):
    for fn in files:
        a = Path(fn).stat().st_size; quant(Image.open(fn)).save(fn, optimize=True)
        print(fn, f"{a / 1024:.0f}KB → {Path(fn).stat().st_size / 1024:.0f}KB")


def grid(src, step=20, k=4):
    im = Image.open(src).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 0, 255, 255)); bg.alpha_composite(im)
    b = bg.resize((im.width * k, im.height * k), Image.LANCZOS); d = ImageDraw.Draw(b)
    for x in range(0, im.width, step):
        d.line([(x * k, 0), (x * k, b.height)], fill=(0, 0, 0, 255) if x % 100 == 0 else (255, 255, 255, 110)); d.text((x * k + 2, 2), str(x), fill=(0, 0, 0, 255))
    for y in range(0, im.height, step):
        d.line([(0, y * k), (b.width, y * k)], fill=(0, 0, 0, 255) if y % 100 == 0 else (255, 255, 255, 110)); d.text((2, y * k + 2), str(y), fill=(0, 0, 0, 255))
    out = Path(src).with_name(Path(src).stem + "_grid.png"); b.convert("RGB").save(out); print(out, "（洋红 = 透明；数字是原图像素坐标）")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    opt = {}
    while "--w" in a:
        i = a.index("--w"); opt["w"] = int(a[i + 1]); del a[i:i + 2]
    cmd = a[0]
    if cmd == "sheet":
        sheet(*a[1:])
    elif cmd == "frames":
        frames(a[1], a[2], a[3:], **opt)
    elif cmd == "cutout":
        cutout(a[1], a[2], **opt)
    elif cmd == "shrink":
        shrink(a[1:])
    elif cmd == "grid":
        grid(a[1])
    else:
        raise SystemExit(__doc__)
