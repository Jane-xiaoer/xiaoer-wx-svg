"""让一张角色抠图「活」起来，但不重画它：切件 → 算厚度 → three.js 顶成立体摆动作 → 渲染成一帧帧透明 PNG。

    python3 character.py parts  rig.json      # 1. 按 rig.json 把抠图切成 身体 + 各部位，生成 <name>_parts.png 检查图
    python3 character.py render rig.json      # 2. 算厚度图 + three.js 渲染 rig.json 里定义的所有动作 → assets/<name>3d/

依赖：pip install pillow numpy scipy playwright && playwright install chromium。three.js 运行时从 jsdelivr 加载（要能上网；
走代理就设 HTTPS_PROXY）。没有显卡也行，用的是软件渲染。

rig.json 怎么写见同目录的 rig.example.json，每个字段的意思：
  image      角色抠图（透明底 PNG）。建议先缩到 240 宽左右，坐标好量。用 `python3 extract.py grid 图.png` 画出坐标网格再定下面的数。
  is_body    一句判断「这个像素是身体主色」的表达式，变量 r g b（0–255）。例：绿色的身体 "g > r + 12 and g > b + 25"。
  eyes       两只眼睛中心的坐标，眨眼用。没有眼睛或不想眨就写 []。
  parts      每个部位：
      poly    一个多边形，把这个部位圈进去（可以圈大一点）。
      pivot   它绕哪一点转（耳根、肩、脚踝）。
      mode    "color" = 只取多边形里「不是身体主色」的像素（耳朵这种颜色不同、长在身体外面的）；
              "cut"   = 多边形里的全拿走（手、脚这种和身体同色的）。
      fill    （cut 用）切走以后，身体上哪些位置要补成身体色：表达式，变量 x y。例："x >= 25" = 靠里的这一侧补上，靠外的留空。
      thick   [圆角半径, 最大厚度]，像素。身体 [78, 70]，耳朵 [10, 8]，手 [16, 14]，脚 [26, 22] 是一组好用的数。
      z       这一块离身体背面多远。身体 0，耳朵 3，手 4，脚 18。数越大转头时错位越明显，缝也越容易露。
  body_thick 身体的 [圆角半径, 最大厚度]。
  actions    动作表。每个动作 = {"fps": 每秒几帧, "frames": [一帧一个姿态]}。姿态里能写：
      ry 左右转头（度）  rx 点头  rz 歪  by 整体上下  sq 压扁（0.05 = 压 5%）  blink 1 = 闭眼
      部位名: 角度（名字以 L 结尾的部位：正 = 屏幕上顺时针；以 R 结尾的自动镜像。所以左右两边写同一个数就是对称动作）
  stills     单帧，同样是姿态。例：睡着的一帧 {"sleep": {"blink": 1, "earL": -48, "earR": -48}}。

经验（踩过的）：
- 手不要抬高。抠图里手往往是贴着身体的一小条，抬起来就是一根细棍或一张薄片，怎么加粗都不对。要活泼就动耳朵、蹦、转头、眨眼。
- 转头别超过 ±22 度，再大侧面就拉花了。
- 每一帧是一张图，会占图片数和正文体积。一个待机循环 12 帧、一个说话动作 6 帧就够。只用在角色停着被看的地方。
- 同一个角色在全篇的大小要一致。
"""
import asyncio, base64, io, json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

VW_PAD, SS = 140, 3          # 画布比角色每边多出 70 像素（耳朵、蹦起来要用）；3 倍超采样再缩小 = 抗锯齿


def load(rig_path):
    rig = json.loads(Path(rig_path).read_text(encoding="utf-8"))
    base = Path(rig_path).resolve().parent
    src = (base / rig["image"]).resolve()
    name = rig.get("name") or src.stem
    work = base / f"_{name}_rig"; work.mkdir(exist_ok=True)
    return rig, src, name, work


def cut_parts(rig_path):
    rig, src, name, work = load(rig_path)
    im = Image.open(src).convert("RGBA"); a = np.array(im); h, w = a.shape[:2]
    r, g, b = (a[..., i].astype(int) for i in range(3))
    body = eval(rig["is_body"], {"np": np}, {"r": r, "g": g, "b": b}) & (a[..., 3] > 128)
    body_col = np.median(a[body][:, :3], axis=0).astype(np.uint8)
    base = a.copy(); meta = {"size": [w, h], "parts": {}}
    yy, xx = np.mgrid[0:h, 0:w]
    top = np.where(body.any(axis=0), body.argmax(axis=0), h)                 # 每一列最上面的身体像素
    for pn, sp in rig["parts"].items():
        m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).polygon([tuple(p) for p in sp["poly"]], fill=255); m = np.array(m) > 0
        if sp.get("mode", "cut") == "color":
            sel = m & ~body & (a[..., 3] > 0)
            sel = (np.array(Image.fromarray((sel * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))) > 0) & m     # 往身体里多带一圈，转起来不露缝
            inside = yy >= top[None, :]                                       # 落在身体轮廓里的补身体色，外面的留空
        else:
            sel = m & (a[..., 3] > 0)
            inside = eval(sp.get("fill", "False"), {"np": np}, {"x": xx, "y": yy}) & np.ones((h, w), bool)
        piece = np.zeros_like(a); piece[sel] = a[sel]
        ys, xs = np.where(sel); x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        Image.fromarray(piece[y0:y1, x0:x1]).save(work / f"{pn}.png")
        base[sel & inside, :3] = body_col; base[sel & inside, 3] = 255; base[sel & ~inside, 3] = 0
        meta["parts"][pn] = dict(box=[int(x0), int(y0), int(x1 - x0), int(y1 - y0)], pivot=sp["pivot"], thick=sp.get("thick", [12, 10]), z=sp.get("z", 4))
    Image.fromarray(base).save(work / "base.png")
    (work / "parts.json").write_text(json.dumps(meta))
    # 检查图：左 = 切完的身体；中 = 拼回去（应该和原图一样）；右 = 每块转 25 度（看缝和转轴对不对）
    def comp(ang):
        c = Image.new("RGBA", (w + 80, h + 80), (245, 242, 235, 255)); c.alpha_composite(Image.open(work / "base.png"), (40, 40))
        for pn, p in meta["parts"].items():
            layer = Image.new("RGBA", c.size, (0, 0, 0, 0)); layer.alpha_composite(Image.open(work / f"{pn}.png"), (40 + p["box"][0], 40 + p["box"][1]))
            sg = 1 if pn.endswith("L") else -1
            c.alpha_composite(layer.rotate(-ang * sg, center=(40 + p["pivot"][0], 40 + p["pivot"][1]), resample=Image.BICUBIC))
        return c
    b0 = Image.new("RGBA", (w + 80, h + 80), (245, 242, 235, 255)); b0.alpha_composite(Image.open(work / "base.png"), (40, 40))
    sheet = Image.new("RGB", ((w + 80) * 3, h + 80))
    for i, t in enumerate([b0, comp(0), comp(25)]):
        sheet.paste(t.convert("RGB"), (i * (w + 80), 0))
    out = work.parent / f"{name}_parts.png"; sheet.save(out); print("检查图：", out)
    return rig, src, name, work, meta


def depth_maps(rig, src, work, meta):
    """每一块的厚度图：离轮廓越远越厚，边缘是圆的。顺手把透明处的颜色填成最近的不透明像素（否则贴图插值后边缘发黑）。"""
    from scipy.ndimage import distance_transform_edt, gaussian_filter, binary_dilation
    w, h = meta["size"]
    full = np.array(Image.open(src).convert("RGBA"))[..., 3] > 100
    items = {"base": dict(box=[0, 0, w, h], pivot=[w / 2, h / 2], thick=rig.get("body_thick", [78, 70]), z=0)}; items.update(meta["parts"])
    tex = {}
    for pn, p in items.items():
        im = Image.open(work / f"{pn}.png").convert("RGBA"); arr = np.array(im); op = arr[..., 3] > 100
        sil = full if pn == "base" else op                                    # 身体的厚度按完整轮廓算，切走手脚的缺口不该凹进去
        d = distance_transform_edt(np.pad(sil, 2))[2:-2, 2:-2]
        R, T = p["thick"]; u = np.clip(d / R, 0, 1)
        z = gaussian_filter(np.sqrt(1 - (1 - u) ** 2) * T, 1.5)
        if pn == "base":                                                      # 缺口往里多留 7 像素，转头时缝里不露底
            grow = binary_dilation(op, iterations=7) & full & ~op; arr[grow, 3] = 255
        idx = distance_transform_edt(~op, return_distances=False, return_indices=True)
        arr[..., :3] = arr[idx[0], idx[1], :3]
        def uri(a_):
            buf = io.BytesIO(); Image.fromarray(a_).save(buf, "PNG"); return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        tex[pn] = uri(arr); tex[pn + "_d"] = uri(np.clip(z / 80 * 255, 0, 255).astype(np.uint8))
    return items, tex


PAGE = r"""<!doctype html><body style="margin:0;background:transparent"><canvas id="c"></canvas>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.min.js"}}</script>
<script type="module">
import * as THREE from 'three';
const SIZE = __SIZE__, PARTS = __PARTS__, TEX = __TEX__, EYES = __EYES__, VW = __VW__, VH = __VH__, SS = __SS__;
const cv = document.getElementById('c');
const R = new THREE.WebGLRenderer({canvas: cv, alpha: true, antialias: true, preserveDrawingBuffer: true, premultipliedAlpha: false});
R.setSize(VW * SS, VH * SS, false); R.setClearColor(0x000000, 0);
const cam = new THREE.OrthographicCamera(-VW / 2, VW / 2, VH / 2, -VH / 2, -1000, 1000); cam.position.z = 500;
const scene = new THREE.Scene(), [W, H] = SIZE;
const load = (u) => new Promise(r => new THREE.TextureLoader().load(u, t => { t.colorSpace = THREE.NoColorSpace; t.minFilter = THREE.LinearFilter; r(t); }));
const root = new THREE.Group(); scene.add(root); const body = new THREE.Group(); root.add(body);
const G = {}, U = {blink: {value: 0}};
const eA = new THREE.Vector2(...(EYES[0] || [-99, -99])), eB = new THREE.Vector2(...(EYES[1] || [-99, -99]));
async function build() {
  for (const [pn, pt] of Object.entries(PARTS)) {
    const [bx, by, bw, bh] = pt.box, [px, py] = pt.pivot;
    const map = await load(TEX[pn]), dm = await load(TEX[pn + '_d']);
    const geo = new THREE.PlaneGeometry(bw, bh, Math.max(8, Math.round(bw / 3)), Math.max(8, Math.round(bh / 3)));
    // 不打光：直接用贴图的颜色，保住原画的笔触。顶点按厚度图往前顶。眨眼 = 把眼睛那一小块换成旁边的肤色，再画一道弧。
    const mat = new THREE.ShaderMaterial({side: THREE.DoubleSide,
      uniforms: {map: {value: map}, dm: {value: dm}, blink: U.blink, isBase: {value: pn === 'base' ? 1 : 0}, size: {value: new THREE.Vector2(W, H)}, eyeA: {value: eA}, eyeB: {value: eB}},
      vertexShader: `uniform sampler2D dm; varying vec2 vUv; void main(){ vUv = uv; float z = texture2D(dm, uv).r * 80.0;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position.xy, z, 1.0); }`,
      fragmentShader: `uniform sampler2D map; uniform float blink, isBase; uniform vec2 size, eyeA, eyeB; varying vec2 vUv;
        void main(){ vec4 c = texture2D(map, vUv); if (c.a < 0.5) discard;
          if (isBase > 0.5 && blink > 0.5) { vec2 p = vec2(vUv.x, 1.0 - vUv.y) * size;
            for (int k = 0; k < 2; k++) { vec2 e = k == 0 ? eyeA : eyeB; vec2 q = p - e;
              if (length(q / vec2(13.0, 13.0)) < 1.0) { c.rgb = texture2D(map, vec2(e.x / size.x, 1.0 - (e.y - 22.0) / size.y)).rgb;
                float arc = q.y - 1.0 + q.x * q.x * 0.035; if (abs(arc) < 1.5 && abs(q.x) < 10.0) c.rgb = vec3(0.24, 0.14, 0.13); } } }
          gl_FragColor = vec4(c.rgb, 1.0); }`});
    const mesh = new THREE.Mesh(geo, mat), piv = new THREE.Group();
    piv.position.set(px - W / 2, H / 2 - py, pt.z || 0); mesh.position.set(bx + bw / 2 - px, py - (by + bh / 2), 0);
    piv.add(mesh); body.add(piv); G[pn] = piv;
  }
}
const d2r = Math.PI / 180;
window.pose = (p) => {
  const g = (k) => p[k] || 0, sq = g('sq');
  root.position.set(0, -H / 2 + g('by'), 0); root.scale.set(1 + sq * 0.6, 1 - sq, 1);        // 压扁以脚底为支点
  body.position.set(0, H / 2, 0); body.rotation.set(g('rx') * d2r, g('ry') * d2r, -g('rz') * d2r);
  for (const pn of Object.keys(G)) if (pn !== 'base') G[pn].rotation.z = -g(pn) * (pn.endsWith('L') ? 1 : -1) * d2r;
  U.blink.value = g('blink'); R.render(scene, cam); return cv.toDataURL('image/png');
};
build().then(() => { window.ready = true; });
</script></body>"""


async def render(rig_path):
    import os
    from playwright.async_api import async_playwright
    rig, src, name, work, meta = cut_parts(rig_path)
    items, tex = depth_maps(rig, src, work, meta)
    w, h = meta["size"]; VW, VH = w + VW_PAD, h + VW_PAD - 48
    out_w = int(rig.get("out_width", round(VW * 0.6)))
    html = (PAGE.replace("__SIZE__", json.dumps([w, h])).replace("__PARTS__", json.dumps(items)).replace("__TEX__", json.dumps(tex))
            .replace("__EYES__", json.dumps(rig.get("eyes", []))).replace("__VW__", str(VW)).replace("__VH__", str(VH)).replace("__SS__", str(SS)))
    page_f = work / "_page.html"; page_f.write_text(html)
    out = (Path(rig_path).resolve().parent / rig.get("out_dir", f"assets/{name}3d")); out.mkdir(parents=True, exist_ok=True)
    px = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"], **({"proxy": {"server": px}} if px else {}))
        pg = await b.new_page(); await pg.goto(page_f.as_uri())
        await pg.wait_for_function("window.ready === true", timeout=60000)

        async def shot(pose, path, scale=1):
            data = await pg.evaluate("p => window.pose(p)", pose)
            im = Image.open(io.BytesIO(base64.b64decode(data.split(",")[1]))).convert("RGBA")
            im.resize((out_w * scale, round(out_w * scale * VH / VW)), Image.LANCZOS).save(path, optimize=True)
        info = dict(view=[VW, VH], size=[w, h], actions={}, stills=list(rig.get("stills", {})))
        for an, ac in rig.get("actions", {}).items():
            for i, fr in enumerate(ac["frames"]):
                await shot(fr, out / f"{name}_{an}_{i}.png")
            info["actions"][an] = dict(n=len(ac["frames"]), fps=ac.get("fps", 6))
        for sn, fr in rig.get("stills", {}).items():
            await shot(fr, out / f"{name}_{sn}.png", scale=2)
        await b.close()
    (out / f"{name}.json").write_text(json.dumps(info))
    # 联系表：每个动作一排
    rows = [(an, n["n"]) for an, n in info["actions"].items()]
    if rows:
        fw, fh = out_w, round(out_w * VH / VW)
        sheet = Image.new("RGB", (fw * max(n for _, n in rows), fh * len(rows)), (245, 242, 235))
        for r_, (an, n) in enumerate(rows):
            for i in range(n):
                im = Image.open(out / f"{name}_{an}_{i}.png"); sheet.paste(im, (i * fw, r_ * fh), im)
        sheet.save(out.parent / f"{name}_actions.png"); print("动作联系表：", out.parent / f"{name}_actions.png")
    print("帧在：", out, info)


def svg_frames(name, w, acts=(), step=1, assets_dir="assets", sub=None):
    """在页面里用这些帧：返回 (svg, 角色高)。body 以 (0,0) 为中心，放进 svgkit.track()。
    平时循环播 idle；acts = [(动作名, 开始秒, 结束秒)] 的时段换成那个动作。step=2 = idle 只用一半的帧（省图片数）。"""
    import math, svgkit as K
    sub = sub or f"{name}3d"
    info = json.loads((Path(assets_dir) / sub / f"{name}.json").read_text())
    iw, ih = info["size"]; vw, vh = info["view"]; k = w / iw; fw, fh = vw * k, vh * k

    def frames(an, spans):
        n, fps = info["actions"][an]["n"], info["actions"][an]["fps"]
        st = step if an == "idle" else 1
        idx = list(range(0, n, st)); m = len(idx); dur = m / (fps / st); out = ""
        for j, fi in enumerate(idx):
            vals = ";".join("1" if q == j else "0" for q in range(m)); an_ = ""
            for b0, b1 in spans:
                rc = "indefinite" if b1 is None else str(max(1, math.ceil((b1 - b0) / dur)))
                an_ += f'<animate attributeName="opacity" values="{vals}" dur="{K.f(dur)}s" begin="{K.f(b0)}s" calcMode="discrete" repeatCount="{rc}"/>'
            out += K.img(f"{sub}/{name}_{an}_{fi}.png", -fw / 2, -fh / 2, fw, fh, ' opacity="0"', an_)
        return out
    acts = sorted(acts, key=lambda a: a[1])
    sets = "".join(f'<set attributeName="opacity" to="0" begin="{K.f(a)}s" fill="freeze"/><set attributeName="opacity" to="1" begin="{K.f(b)}s" fill="freeze"/>' for _, a, b in acts)
    out = f'<g>{sets}{frames("idle", [(0, None)])}</g>'
    for an in sorted(set(a[0] for a in acts)):
        iv = [(a, b) for nm, a, b in acts if nm == an]
        sets = "".join(f'<set attributeName="opacity" to="1" begin="{K.f(a)}s" fill="freeze"/><set attributeName="opacity" to="0" begin="{K.f(b)}s" fill="freeze"/>' for a, b in iv)
        out += f'<g opacity="0">{sets}{frames(an, iv)}</g>'
    return out, w * ih / iw


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    if sys.argv[1] == "parts":
        cut_parts(sys.argv[2])
    elif sys.argv[1] == "render":
        asyncio.run(render(sys.argv[2]))
    else:
        raise SystemExit(__doc__)
