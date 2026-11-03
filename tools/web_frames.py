"""把网页里的 3D 模型 / 动画截成一串帧，再铺底色、羽化阴影、裁好，给等轴测「带图片帧」的站点用。

两步：

  python3 tools/web_frames.py capture 配置.json 素材/raw        # 开浏览器，按配置一步步操作、截图（透明底 png）
  python3 tools/web_frames.py compose 素材/raw 素材/jpg --bg "#ECE4D5" --width 560

capture 配置（JSON，字段都可省略，除了 url）：

  {
    "url": "https://你的网站/",
    "viewport": [1000, 900],         // 截图画布大小。主体被裁到边 → 开大这里，别缩相机
    "webgl": true,                   // three.js / WebGL 页面必开（无头浏览器用软件渲染）
    "element": "#canvas3d",          // 只截这个元素；不填 = 截整个视口
    "transparent": true,             // 透明底（配合 hide_others，阴影才能羽化）
    "hide_others": true,             // 把 element 以外的网页元素都藏起来、背景改透明
    "patch_url": "**/index.html",    // 想改页面源码时：匹配哪个请求
    "patch": [["原文", "替换成"]],     // 例：把相机挂到 window 上、把动画等待时间拉长
    "wait": 2500,                    // 打开后先等多久（毫秒），等模型加载完
    "camera": {                      // 可选：锁定 three.js 相机（页面会自己改视角时必须锁）
      "camera": "window.__cam", "target": "window.__ctl.target", "controls": "window.__ctl",
      "dir": [1, 0.816, 1], "dist": 26, "fov": 25, "shift": [-0.95, -0.3, 0]
    },
    "probe": "JSON.stringify(window.app.state)",   // 可选：每张图截的时候顺便记一下页面状态
    "steps": [
      {"js": "document.querySelector('#start').click()", "wait": 800},
      {"shot": "closed"},
      {"js": "app.open()", "wait": 1500}, {"shot": "open"},
      {"seq": "put", "count": 8, "every": 150},     // 连拍：8 张，每张隔 150ms
      {"js": "app.play()"},
      {"seq": "seq", "seconds": 26}                 // 连拍：尽量快地拍满 26 秒
    ]
  }

capture 结束会写 raw/capture.json：每张图的拍摄时间（秒）和 probe 结果。
compose 会写 jpg/frames.json：每张图和上一张差多少（motion，0 = 完全没动），
自动分出「静止 / 局部在动 / 大动作」三种段，再拼一张带编号的总览图 jpg/_sheet.jpg。
看不了图的模型就看 frames.json 挑帧：运动段 = 在转 / 在开门，静止段 = 停住的那一刻。
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

STILL, BIG = 0.035, 1.0   # motion 分档：< 0.035 静止；< 1 局部在动（滚筒里在转、灯在闪）；≥ 1 大动作（开门、转身）
GL_ARGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]

HIDE_JS = """(sel)=>{
  const keep = sel ? document.querySelector(sel) : null;
  document.documentElement.style.background='transparent'; document.body.style.background='transparent';
  if(!keep) return 'no element';
  for(const el of document.querySelectorAll('body *')){ if(el!==keep && !el.contains(keep) && !keep.contains(el)) el.style.visibility='hidden'; }
  for(let el=keep; el; el=el.parentElement){ el.style.background='transparent'; }
  return 'ok';
}"""

CAM_JS = """(o)=>{
  const c = eval(o.camera), t = eval(o.target);
  if(!c || !t) return 'camera/target not found: '+o.camera+' / '+o.target;
  const s = o.shift || [0,0,0]; t.x += s[0]; t.y += s[1]; t.z += s[2];
  const d = o.dir || [1,0.816,1], n = Math.hypot(d[0],d[1],d[2]), k = (o.dist||20)/n;
  const pos = t.clone(); pos.x += d[0]*k; pos.y += d[1]*k; pos.z += d[2]*k;
  if(o.controls){ try{ eval(o.controls).enabled=false; }catch(e){} }  // 关掉鼠标拖动，不然它会和锁相机抢
  (function lock(){ c.position.copy(pos); c.lookAt(t); if(o.fov){ c.fov=o.fov; } c.updateProjectionMatrix(); requestAnimationFrame(lock); })();
  return 'locked';
}"""


async def capture(cfg, out):
    from playwright.async_api import async_playwright
    out.mkdir(parents=True, exist_ok=True)
    log = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=GL_ARGS if cfg.get("webgl", True) else [])
        vw, vh = cfg.get("viewport", [1000, 900])
        pg = await b.new_page(viewport={"width": vw, "height": vh})
        pg.on("pageerror", lambda e: print("  页面报错:", str(e)[:120]))
        if cfg.get("patch"):
            async def rw(route):
                r = await route.fetch()
                body = await r.text()
                for a, z in cfg["patch"]:
                    if a not in body:
                        print(f"  ⚠️ patch 没找到原文：{a[:60]}")
                    body = body.replace(a, z, 1)
                await route.fulfill(response=r, body=body)
            await pg.route(cfg.get("patch_url", "**/*.html"), rw)
        await pg.goto(cfg["url"], wait_until="load")
        await pg.wait_for_timeout(cfg.get("wait", 2500))
        el = cfg.get("element")
        if cfg.get("hide_others", True):
            print("  隐藏其它元素:", await pg.evaluate(HIDE_JS, el))
        target = pg.locator(el).first if el else None
        transparent = cfg.get("transparent", True)
        t0 = time.time()

        async def shot(name):
            path = out / f"{name}.png"
            if target:
                await target.screenshot(path=str(path), omit_background=transparent)
            else:
                await pg.screenshot(path=str(path), omit_background=transparent)
            rec = {"name": name, "t": round(time.time() - t0, 2)}
            if cfg.get("probe"):
                try:
                    rec["probe"] = await pg.evaluate(cfg["probe"])
                except Exception as e:  # noqa: BLE001
                    rec["probe"] = f"error: {str(e)[:60]}"
            log.append(rec)

        for st in cfg.get("steps", [{"shot": "frame"}]):
            if "js" in st:
                if st["js"] == "@camera":
                    print("  相机:", await pg.evaluate(CAM_JS, cfg["camera"]))
                else:
                    await pg.evaluate(st["js"])
            if "camera" in st:
                print("  相机:", await pg.evaluate(CAM_JS, st["camera"]))
            if st.get("wait"):
                await pg.wait_for_timeout(st["wait"])
            if "shot" in st:
                await shot(st["shot"])
            if "seq" in st:
                if "count" in st:
                    for i in range(st["count"]):
                        await shot(f"{st['seq']}_{i:03d}")
                        await pg.wait_for_timeout(st.get("every", 150))
                else:
                    i, s0 = 0, time.time()
                    while time.time() - s0 < st.get("seconds", 5):
                        await shot(f"{st['seq']}_{i:03d}")
                        i += 1
                        if st.get("every"):
                            await pg.wait_for_timeout(st["every"])
        await b.close()
    (out / "capture.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ {len(log)} 张 → {out}（拍摄时间和状态在 capture.json）")


def compose(src, dst, bg="#ECE4D5", width=560, margin=24, feather=90, quality=82, crop=None):
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat
    files = sorted(f for f in src.glob("*.png"))
    cap = src / "capture.json"
    if cap.exists():  # 按拍摄顺序排，别按文件名
        order = {r["name"]: k for k, r in enumerate(json.loads(cap.read_text(encoding="utf-8")))}
        files.sort(key=lambda f: order.get(f.stem, 1e9))
    if not files:
        sys.exit(f"{src} 里没有 png")
    dst.mkdir(parents=True, exist_ok=True)
    ims = [Image.open(f).convert("RGBA") for f in files]
    W0, H0 = ims[0].size
    has_alpha = any(im.getchannel("A").getextrema()[0] < 250 for im in ims)
    warn = set()
    if crop:
        box = tuple(crop)
    elif has_alpha:
        bb = None
        for f, im in zip(files, ims):
            a = im.getchannel("A")
            solid = a.point(lambda v: 255 if v > 200 else 0).getbbox()
            if solid:
                for side, hit in (("左", solid[0] <= 1), ("上", solid[1] <= 1), ("右", solid[2] >= W0 - 1), ("下", solid[3] >= H0 - 1)):
                    if hit:
                        warn.add((side, f.stem))
            b = a.point(lambda v: 255 if v > 8 else 0).getbbox()
            if b:
                bb = b if bb is None else (min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3]))
        bb = bb or (0, 0, W0, H0)
        box = (max(0, bb[0] - margin), max(0, bb[1] - margin), min(W0, bb[2] + margin), min(H0, bb[3] + margin))
    else:
        box = (0, 0, W0, H0)
    W, H = box[2] - box[0], box[3] - box[1]
    m = Image.new("L", (W, H), 0)
    pad = min(feather, W // 4, H // 4)
    ImageDraw.Draw(m).rectangle((pad, pad, W - pad, H - pad), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(pad / 2))
    oh = round(H * width / W)
    meta, prev, outs = [], None, []
    for f, im in zip(files, ims):
        im = im.crop(box)
        if has_alpha:
            a = im.getchannel("A")
            solid = a.point(lambda v: 255 if v > 200 else 0)  # 主体不渐隐，只羽化半透明的阴影
            im.putalpha(ImageChops.lighter(ImageChops.multiply(a, m), solid))
        base = Image.new("RGBA", im.size, bg)
        base.alpha_composite(im)
        rgb = base.resize((width, oh), Image.LANCZOS).convert("RGB")
        out = dst / f"{f.stem}.jpg"
        rgb.save(out, quality=quality)
        small = rgb.resize((200, round(200 * oh / width))).convert("L")
        mo = 0.0 if prev is None else round(ImageStat.Stat(ImageChops.difference(small, prev)).mean[0] / 2.55, 3)
        prev = small
        meta.append({"name": f.stem, "motion": mo, "kb": round(out.stat().st_size / 1024, 1)})
        outs.append(rgb)
    # 静止段 / 运动段（同一前缀的连拍里分）
    kinds = ["静止" if r["motion"] < STILL else "局部在动" if r["motion"] < BIG else "大动作" for r in meta]
    for k in range(1, len(kinds) - 1):  # 夹在同一种中间的单张，算进两边（去抖）
        if kinds[k - 1] == kinds[k + 1] != kinds[k] and kinds[k] != "大动作":
            kinds[k] = kinds[k - 1]
    segs, cur = [], None
    for r, kind in zip(meta, kinds):
        if cur and cur["kind"] == kind:
            cur["to"] = r["name"]
            cur["n"] += 1
        else:
            cur = {"kind": kind, "from": r["name"], "to": r["name"], "n": 1}
            segs.append(cur)
    info = {"aspect": round(oh / width, 4), "size": [width, oh], "crop": list(box), "bg": bg,
            "frames": meta, "segments": segs,
            "edge_warnings": sorted(f"{s}:{n}" for s, n in warn)}
    (dst / "frames.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    # 总览图
    cols, tw = 10, 140
    th = round(tw * oh / width)
    sheet = Image.new("RGB", (cols * tw, ((len(outs) + cols - 1) // cols) * (th + 18)), "white")
    d = ImageDraw.Draw(sheet)
    for k, (r, im) in enumerate(zip(meta, outs)):
        x, y = (k % cols) * tw, (k // cols) * (th + 18)
        sheet.paste(im.resize((tw, th)), (x, y + 18))
        d.text((x + 3, y + 3), f"{r['name']}  {r['motion']}", fill="black")
    sheet.save(dst / "_sheet.jpg", quality=80)
    tot = sum(r["kb"] for r in meta)
    print(f"✅ {len(meta)} 张 → {dst}  {width}×{oh}（aspect {info['aspect']}）共 {tot:.0f}KB")
    for s in segs:
        print(f"  {s['kind']:<5} {s['from']} … {s['to']}（{s['n']} 张）")
    if warn:
        sides = sorted({s for s, _ in warn})
        print(f"⚠️ 主体碰到截图边缘（{'、'.join(sides)}），被裁掉了一块：capture 配置里把 viewport 开大（或调 camera.shift），重拍。"
              f"例：{sorted(warn)[0][1]}")
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("capture", help="按配置开网页截帧")
    c.add_argument("config")
    c.add_argument("out")
    k = sp.add_parser("compose", help="铺底色、羽化、裁剪、压成 jpg，写 frames.json")
    k.add_argument("src")
    k.add_argument("dst")
    k.add_argument("--bg", default="#ECE4D5", help="底色，跟分镜 palette 的 bg 一样")
    k.add_argument("--width", type=int, default=560, help="输出宽（站点 560，画 450）")
    k.add_argument("--margin", type=int, default=24)
    k.add_argument("--feather", type=int, default=90, help="阴影羽化宽度（像素）")
    k.add_argument("--quality", type=int, default=82)
    k.add_argument("--crop", type=int, nargs=4, help="手动裁剪框 x0 y0 x1 y1（同一套帧必须用同一个框）")
    a = ap.parse_args()
    if a.cmd == "capture":
        asyncio.run(capture(json.loads(Path(a.config).read_text(encoding="utf-8")), Path(a.out)))
    else:
        compose(Path(a.src), Path(a.dst), a.bg, a.width, a.margin, a.feather, a.quality, a.crop)


if __name__ == "__main__":
    main()
