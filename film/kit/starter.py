"""起步工程：一支「她从早上掉到晚上」的小样，四幕，约 20 秒。不需要任何素材，第一次跑会自己画占位图。

    python3 starter.py                      # 生成 out/preview.html（双击打开看）、out/article.html
    python3 starter.py --push "标题"        # 传图 + 新建公众号草稿（要先设 WX_APPID / WX_SECRET，见 wxapi.py）
    python3 starter.py --update <media_id>  # 覆盖更新已有草稿

怎么用它开新项目：把整个 kit 目录拷到你的项目里，把 assets/ 里的占位图换成从片子里取的素材（文件名对上就行），
然后照着下面四幕的写法改时间、坐标、对白。每一幕的写法都是：先定这一幕在画布上的 y → 加东西 → 告诉「推开」这一幕什么时候露出来。
"""
import argparse, math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import svgkit as K
from svgkit import W, PAPER, INK, NIGHT, GREY, NIGHT_TXT, f

K.ASSETS = HERE / "assets"
OUT = HERE / "out"


# ───────────────────────── 占位素材（换成你自己的就删掉这段）─────────────────────────
def placeholder_assets():
    A = K.ASSETS; (A / "win").mkdir(parents=True, exist_ok=True)

    def blob(name, w, h, color, parts):
        if (A / name).exists():
            return
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        for kind, box, c in parts:
            getattr(d, kind)(box, fill=c or color)
        im.save(A / name)
    skin, coat, hair = (240, 205, 185, 255), (40, 40, 46, 255), (25, 25, 28, 255)
    blob("bed.png", 540, 200, None, [("rounded_rectangle", (0, 110, 540, 160), (150, 100, 70, 255)), ("rectangle", (0, 30, 22, 200), (150, 100, 70, 255)),
                                     ("rectangle", (518, 120, 540, 200), (150, 100, 70, 255)), ("rounded_rectangle", (30, 70, 500, 130), (160, 150, 110, 255)),
                                     ("ellipse", (40, 50, 110, 110), skin), ("ellipse", (30, 40, 100, 90), hair)])
    blob("fall_a.png", 220, 300, coat, [("ellipse", (80, 0, 140, 60), skin), ("ellipse", (75, -5, 135, 35), hair), ("rounded_rectangle", (60, 55, 160, 200), None),
                                        ("rectangle", (70, 195, 105, 300), (120, 120, 130, 255)), ("rectangle", (115, 195, 150, 290), (120, 120, 130, 255)),
                                        ("rectangle", (150, 0, 172, 90), None), ("ellipse", (148, -8, 174, 18), skin)])
    blob("fall_b.png", 300, 220, coat, [("ellipse", (0, 70, 60, 130), skin), ("ellipse", (-5, 65, 35, 125), hair), ("rounded_rectangle", (55, 60, 200, 150), None),
                                        ("rectangle", (195, 70, 300, 105), (120, 120, 130, 255)), ("rectangle", (195, 115, 290, 150), (120, 120, 130, 255)),
                                        ("rectangle", (80, 0, 105, 70), None)])
    blob("lying.png", 600, 150, coat, [("ellipse", (0, 40, 70, 110), skin), ("ellipse", (-5, 30, 45, 100), hair), ("rounded_rectangle", (60, 40, 380, 110), None),
                                       ("rectangle", (370, 60, 600, 110), (120, 120, 130, 255)), ("rectangle", (100, 100, 130, 150), None)])
    blob("mascot.png", 120, 150, (140, 178, 110, 255), [("polygon", [(18, 30), (30, 0), (48, 22)], (245, 225, 205, 255)), ("polygon", [(72, 22), (90, 0), (102, 30)], (245, 225, 205, 255)),
                                                         ("rounded_rectangle", (8, 18, 112, 150), None), ("rounded_rectangle", (26, 36, 94, 86), (250, 228, 212, 255)),
                                                         ("ellipse", (42, 54, 50, 62), (40, 25, 25, 255)), ("ellipse", (70, 54, 78, 62), (40, 25, 25, 255)),
                                                         ("ellipse", (55, 112, 65, 122), (200, 55, 45, 255))])
    for i in range(2):
        p = A / "win" / f"day_{i}.jpg"
        if not p.exists():
            im = Image.new("RGB", (600, 337), (214, 170, 110)); d = ImageDraw.Draw(im)
            d.rectangle((0, 230, 600, 337), fill=(150, 110, 70)); d.rectangle((380, 40, 560, 200), fill=(250, 225, 170))
            d.ellipse((150 + i * 14, 110, 210 + i * 14, 170), fill=(240, 205, 185)); d.rounded_rectangle((130 + i * 14, 165, 230 + i * 14, 300), 20, fill=(40, 40, 46))
            im.filter(ImageFilter.GaussianBlur(0.6)).save(p, quality=80)


# ───────────────────────── 正片 ─────────────────────────
def build():
    K.init_fonts()                         # 自动找系统里的中文字体；想指定就传 {"zh": "路径.ttf"}
    els, REV = [], []                      # els：顶层元素，顺序 = 叠放顺序；REV：[(秒, 露出到的 y)]
    add = els.append
    WX, WW, WH = 30, 690, 388              # 场景窗：左边距、宽、高（16:9）

    # ── 幕 0 题头（0–1s）
    add(K.appear(K.text("往下掉的一天", W / 2, 118, 52, anchor="middle", spacing=0.12), 0.2, 0.9))
    add(K.appear(K.text("从 07:40 到 01:20", W / 2, 166, 20, fill=GREY, anchor="middle", spacing=0.2), 0.6, 0.9))

    # ── 幕 1 床（1–6s）：厚涂的床和人 + 发丝线画的屋子
    LINE1 = 700                            # 第一幕的地面线
    bw, bh = 540, 540 * K.size("bed.png")[1] / K.size("bed.png")[0]
    add(K.ground(LINE1))
    add(K.text("07:40", 24, LINE1 + 32, 22, fill=GREY))
    # 她在呼吸：图的坐标写成相对地面线的，外面包一层以地面线为底的纵向缩放
    add(K.breathe(K.img("bed.png", 34, -bh + 3, bw, bh), LINE1))
    # 屋里其它东西用线画，并且自己画出来。床头柜 0 秒就画（它托着的东西如果一开始就在，柜子不能晚出现）
    nx0, nx1, ny = 590, 716, LINE1 - 66
    add(K.draw_on(f"M{nx0 - 8} {ny} H{nx1 + 8} M{nx0} {ny} V{LINE1} M{nx1} {ny} V{LINE1} M{nx0} {ny + 26} H{nx1}", 420, 0.0, 0.4, INK, 0.8, 1.4))
    add(K.draw_on("M640 216 H500 V366 H640 M580 216 V366 M500 291 H640", 1100, 0.3, 0.9, GREY, 0.5, 1.2))          # 墙上的窗：线画到窗帘就停
    add(K.draw_on("M484 204 H692 M650 204 Q632 270 644 322 Q650 356 634 384 M688 204 Q696 300 684 384 M634 384 H684", 760, 0.7, 0.8, GREY, 0.5, 1.2))
    # 小角色：蹲在床头 → 3 秒跳到床头柜上 → 原地一鼓一鼓，说话时蹦一下
    mb, mh = K.centered("mascot.png", 70)
    p_bed, p_stand = (64, LINE1 - bh * 0.85 - mh / 2), ((nx0 + nx1) / 2, ny - mh / 2)
    mk = [(0, *p_bed, 1, 0, 1), (2.9, *p_bed, 1, 0, 1)] + K.hop(p_bed, p_stand, 3.0, 0.45, height=110)[1:]
    mk += [(3.5, p_stand[0], p_stand[1] + 6, 1.05, 0, 1), (3.7, *p_stand, 1, 0, 1), (6.4, *p_stand, 1, 0, 1), (6.7, *p_stand, 1, 0, 0)]
    mk = K.idle(mk, 0.0, 2.9, period=1.3)
    mk = K.idle(mk, 3.7, 6.4, period=1.1, hops=(4.0, 5.5))
    add(K.track(mb, mk))
    add(K.appear(K.say("它", "起来。", 40, 262, name_color="#6E9A5B"), 4.0))
    add(K.appear(K.say("她", "五分钟……", 160, 312, px=24, name_color="#9A3B2A"), 4.8))
    add(K.appear(K.say("它", "九点有会。", 40, 368, name_color="#6E9A5B"), 5.5))
    FIRST = LINE1 + 90                     # 一打开就露出来的高度

    # ── 幕 2 下坠（6.5–10.5s）→ 幕 3 场景窗接住她
    WIN_Y = LINE1 + 1250
    start = dict(x=300, y=LINE1 - 130, s=1.0, r=0)
    top = dict(x=WX + 400, y=WIN_Y - 30, s=1.0, r=0)                     # 终点 = 窗顶边上方一点：她在这儿淡掉
    keys, pos = K.fall_path(start, top, 6.5, 4.0, curve=[(0, 0, None), (0.3, 0.1, "in"), (0.8, 0.75, None), (1, 1, "out")],
                            drift=140, rot=lambda u: 20 * math.sin(math.pi * u * 2), bulge=0.1, op_in=0.3, op_out=0.2)
    add(K.thread(keys))                                                  # 线索线先加 → 画在人下面
    body = K.poses([("fall_a.png", 190, 6.5, 8.5), ("fall_b.png", 250, 8.5, 10.6)])
    add(K.track(body, K.pop(keys, pos, [8.5])))                          # 8.5 秒换姿态，换的时候弹一下
    # 小角色跟着她：位置 = 她的位置 + 偏移
    fk = [(6.6, *p_stand, 1, 0, 0)] + [(t, pos(t)[0] - 150, pos(t)[1] - 120, 0.9, 12 * math.sin(t * 3), 1) for t in (7.0, 7.8, 8.6, 9.4, 10.0)]
    fk.append((10.5, WX + 300, WIN_Y + 60, 0.8, 0, 0))
    add(K.track(K.centered("mascot.png", 62)[0], fk))
    # 空中对白：摆在她旁边；每句至少比上一句低 60，不叠
    last = -999
    for t, line in [(7.2, "醒醒。"), (9.0, "外套。")]:
        x, y, *_ = pos(t)
        yy = max(y - 40, LINE1 + 175, last + 60); last = yy
        add(K.appear(K.say("它", line, x + 170 if x < W / 2 else x - 170, yy, name_color="#6E9A5B", anchor="start" if x < W / 2 else "end"), t))
    REV += [(k[0], k[2] + 560) for k in keys[2::2]]                      # 推开跟着她走：露出到她下面 560 的地方
    # 窗：10.0 描线 → 10.45 出图 → 10.55 一沉一弹 → 14.6 她走了，压暗
    add(K.window(WX, WIN_Y, WW, WH, "08:50 · 出门", ["win/day_0.jpg", "win/day_1.jpg"], t_on=10.45, frame_at=10.0, bounce=10.55, dim=(14.8, 0.25)))
    add(K.catch_dust(WX + 400, WIN_Y, 10.55))
    add(K.appear(K.say("她", "走了走了！", 40, WIN_Y + WH + 62, name_color="#9A3B2A"), 12.0))
    REV.append((10.4, WIN_Y + WH + 110))

    # ── 幕 4 硬边进夜 → 砸进发丝线沙发（14.5–20s）
    EDGE = WIN_Y + WH + 360                                              # 从这条线往下是夜
    els.insert(0, f'<rect x="0" y="{EDGE}" width="{W}" height="99999" fill="{NIGHT}"/>')   # 插在最前面 = 垫在最底下
    LINE2 = EDGE + 620                                                   # 沙发坐垫面
    lw = 600; lh = lw * K.size("lying.png")[1] / K.size("lying.png")[0]
    out_of_win = dict(x=WX + 415, y=WIN_Y + 250, s=1.0, r=0)
    land = dict(x=375, y=LINE2 - lh * 0.4, s=1.0, r=-80)
    k2, pos2 = K.fall_path(out_of_win, land, 14.5, 2.4, curve=[(0, 0, None), (1, 1, "in")], drift=-60, op_in=0.2, op_out=0)
    add(K.thread([k for k in k2 if k[2] < EDGE], GREY) + K.thread([k for k in k2 if k[2] >= EDGE - 2], NIGHT_TXT))   # 线过了硬边换成浅色
    add(K.track(K.poses([("fall_b.png", 250, 14.5, 16.95)]), k2[:-1] + [k2[-1][:5] + (0,)]))
    add(K.glow(375, LINE2 - 30, 300))
    add(K.sofa_lines(LINE2, 16.9, back=140))                             # 她砸下来那一刻，沙发自己画出来
    add(f'<line x1="84" y1="{LINE2}" x2="666" y2="{LINE2}" stroke="{NIGHT_TXT}" stroke-width="1.6" opacity="0.7"/>')
    # 落地：压扁回弹（以坐垫面为支点），身体下沿压在线上
    squash = ('<animateTransform attributeName="transform" type="scale" values="1 1;1.05 0.86;0.98 1.04;1 1" keyTimes="0;0.3;0.7;1" begin="16.9s" dur="0.4s"/>')
    add(K.show_once(f'<g transform="translate(375 {LINE2})"><g>{squash}{K.img("lying.png", -lw / 2, -lh * 0.72, lw, lh)}</g></g>', 16.9, None, fade=0.02))
    add(K.appear(K.say("它", "……又这样睡。", W - 40, LINE2 - 190, night=True, anchor="end", name_color="#8DB57A"), 18.0))
    add(K.appear(K.say("它", "都在。睡吧。", W - 40, LINE2 + 230, night=True, anchor="end", name_color="#8DB57A"), 19.2))
    REV += [(k[0], k[2] + 480) for k in k2[2::2]]
    H = int(LINE2 + 320)
    REV.append((17.0, H))
    return els, H, REV, FIRST


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--push"); ap.add_argument("--update"); ap.add_argument("--cover", default=str(OUT / "cover.jpg"))
    a = ap.parse_args()
    placeholder_assets()
    els, H, REV, FIRST = build()
    article = K.assemble(els, H, REV, FIRST, OUT, T=22)
    print("本地预览：", (OUT / "preview.html").as_uri())
    if a.push or a.update:
        import wxapi
        if not Path(a.cover).exists():
            raise SystemExit(f"还没有封面：先跑 python3 cover.py out/preview.html 3.5 392 生成 {a.cover}")
        tok = wxapi.token()
        art = wxapi.localize(article, HERE, OUT / "mmbiz.json", tok)
        mid = wxapi.save_draft(tok, art, a.push or "未命名", a.cover, update=a.update)
        (OUT / "media_id.txt").write_text(mid)
        print("草稿 media_id：", mid, "（已存到 out/media_id.txt，下次用 --update 覆盖它）")
        wxapi.check(tok, mid, art)


if __name__ == "__main__":
    main()
