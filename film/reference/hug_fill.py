# 结尾「搂着阿卡」：要服帖 = 她的手真的压在阿卡身上。
# 做法：把 hugP_0.png 里两只手按肤色切出来（hugP_handL/R.png），原位置和臂弯的洞一起用毛衣颜色补上（hugP_base.png，
# 带阿卡的接触影）；页面里的层次 = hugP_base → 阿卡 → 两只手（绕手腕转一点，搭到阿卡头上和身侧）。
# 下面这组数 build3.hug_body 也在用（写到 assets/hug.json）。
import sys, json
from pathlib import Path
from PIL import Image, ImageFilter
import numpy as np
from scipy.ndimage import label, binary_dilation, gaussian_filter
A = Path(__file__).resolve().parent.parent / "assets"
SRC = Path(__file__).resolve().parent / "_旧hugP_0_漏边.png"
CFG = dict(aka_w=82, aka_c=[233, 88], aka_rot=-8,
           handL=dict(box=[168, 8, 226, 68], pivot=[219, 22], rot=-17, shift=[2, 5]),      # 上面那只手：指尖往下压到阿卡头上
           handR=dict(box=[266, 38, 306, 112], pivot=[287, 104], rot=-13, shift=[-5, 0]))  # 右边那只手：往里扣住阿卡身侧

def skin(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (a[..., 3] > 128) & (r > 150) & (g > 105) & (b > 90) & (r - b < 110)

def diffuse(a, mask_fill, src):
    out = np.zeros_like(a[..., :3]); wsum = np.zeros(a.shape[:2])
    for sig, wt in [(3, 8.0), (8, 2.0), (20, 1.0), (45, 0.5)]:
        w = gaussian_filter(src.astype(float), sig)
        for c in range(3):
            out[..., c] += wt * gaussian_filter(a[..., c] * src, sig)
        wsum += wt * w
    return out / np.maximum(wsum, 1e-6)[..., None]

def run():
    im = Image.open(SRC).convert("RGBA"); a = np.array(im).astype(float)
    cut = int(round(161 / 169 * a.shape[0])) + 1; a[cut:, :, 3] = 0          # 坐垫线以下的残边
    H, W = a.shape[:2]
    tr = a[..., 3] < 128
    lab, n = label(tr); hole = None
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if ys.min() > 0 and xs.min() > 0 and ys.max() < H - 1 and xs.max() < W - 1 and len(ys) > 2000:
            hole = lab == i
    sk = skin(a); hands = np.zeros((H, W), bool); pieces = {}
    for hn in ("handL", "handR"):
        x0, y0, x1, y1 = CFG[hn]["box"]
        m = np.zeros((H, W), bool); m[y0:y1, x0:x1] = sk[y0:y1, x0:x1]
        lb, k = label(m)
        if k > 1:                                            # 只留最大的一块
            m = lb == (1 + np.argmax([np.sum(lb == j) for j in range(1, k + 1)]))
        m = binary_dilation(m, iterations=1) & ~tr & ~hole
        pc = np.zeros_like(a); pc[m] = a[m]
        Image.fromarray(pc[y0 - 2:y1 + 2, x0 - 2:x1 + 2].astype(np.uint8)).save(A / f"hugP_{hn}.png")
        pieces[hn] = Image.fromarray(pc.astype(np.uint8)); hands |= m
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    sweater = (~tr) & ~binary_dilation(hands, iterations=2) & (r > g + 30) & (r < 190) & (g < 110)
    region = hole | binary_dilation(hands, iterations=2)
    ring = binary_dilation(region, iterations=14) & sweater
    fill = diffuse(a, region, ring)
    # 右手原来压着袖子和毯子的交界：那一块用周围所有不是手的像素来补（袖子归袖子、毯子归毯子）
    x0, y0, x1, y1 = CFG["handR"]["box"]
    hd = binary_dilation(hands, iterations=5)
    rr = np.zeros((H, W), bool); rr[y0 - 6:y1 + 6, x0 - 6:x1 + 6] = hd[y0 - 6:y1 + 6, x0 - 6:x1 + 6]
    rr &= ~hole & ~tr
    src_r = binary_dilation(rr, iterations=6) & ~tr & ~hd
    out = np.zeros_like(a[..., :3]); ws = np.zeros((H, W))
    for sig, wt in [(1.5, 8.0), (4, 1.0)]:
        ws += wt * gaussian_filter(src_r.astype(float), sig)
        for c in range(3):
            out[..., c] += wt * gaussian_filter(a[..., c] * src_r, sig)
    fill_r = out / np.maximum(ws, 1e-6)[..., None]
    fill[rr] = fill_r[rr]
    aka = Image.open(A / "aka3d/aka_squat_sleep.png").convert("RGBA")
    k = CFG["aka_w"] / 240; cw, ch = round(380 * k), round(400 * k)
    aka = aka.resize((cw, ch), Image.LANCZOS).rotate(-CFG["aka_rot"], resample=Image.BICUBIC)
    ax, ay = CFG["aka_c"][0] - cw // 2, CFG["aka_c"][1] - ch // 2
    sh = Image.new("L", (W, H), 0); sh.paste(aka.split()[3], (ax + 2, ay + 4))
    shadow = np.array(sh.filter(ImageFilter.GaussianBlur(5))) / 255.0
    base = a.copy()
    grow = binary_dilation(region, iterations=2) & (~tr | hole)
    f2 = fill * (0.96 - 0.32 * shadow)[..., None]
    base[grow, :3] = f2[grow]; base[grow, 3] = 255
    Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).save(A / "hugP_base.png")
    # 下面那只手臂单独一层，盖在阿卡脚上
    low = np.zeros_like(a); m = (~tr) & ~hands; m[:112] = False; m[:, :150] = False; m[:, 305:] = False
    low[m] = a[m]
    Image.fromarray(low.astype(np.uint8)).save(A / "hugP_armLow.png")
    pieces["armLow"] = Image.fromarray(low.astype(np.uint8))
    (A / "hug.json").write_text(json.dumps(CFG))
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)), aka, (ax, ay), pieces

if __name__ == "__main__":
    base, aka, (ax, ay), pieces = run()
    if len(sys.argv) > 1:
        c = Image.new("RGBA", base.size, (40, 34, 32, 255)); c.alpha_composite(base); c.alpha_composite(aka, (ax, ay))
        c.alpha_composite(pieces.pop("armLow"))
        for hn, pc in pieces.items():
            h = CFG[hn]
            pc = pc.rotate(-h["rot"], center=tuple(h["pivot"]), resample=Image.BICUBIC, translate=tuple(h["shift"]))
            # 手底下一点影子
            shd = Image.new("RGBA", base.size, (30, 10, 8, 0)); shd.putalpha(pc.split()[3].filter(ImageFilter.GaussianBlur(2.5)).point(lambda v: int(v * 0.45)))
            c.alpha_composite(shd, (1, 2)); c.alpha_composite(pc)
        c.crop((110, 0, 400, 169)).resize((290 * 4, 169 * 4), Image.LANCZOS).convert("RGB").save(sys.argv[1])
