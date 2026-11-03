# 等轴测旅程（3D 版）

一条 Z 字公路从上往下串起 N 个 2.5D 小场景。往下拉，跟着一个光点走完整个故事：
每到一站，底座侧滑进来，零件一块块掉下来拼好，信息卡滑出；公路往下一站画出去，光点跑过去，到了再拼下一个。
纯 SVG 动画，没有位图，没有 JS，也没有 id。8 站大约 190KB、30 秒。

参考：「红色运营宝典」《看！宝岛台湾！（3D版）》（20 个地标，1080×11519，约 67 秒，3MB，作为 `<img>` 的 mmbiz_svg 贴进正文）。
我们走**内联 SVG**（`wxsvg` 的零高容器），能用 `--grow` 让页面一屏屏长出来，也能接「点一下揭开」。

## 用法

```bash
python3 iso/iso_journey.py templates/storyboards/等轴测-小耳的四台电脑.json            # 整张长图一开始就在（像参考那样）
python3 iso/iso_journey.py 分镜.json --grow        # 页面跟着故事一屏屏长出来
python3 iso/iso_journey.py 分镜.json --speed 1.2   # 慢 20%（数字 >1 变慢）
python3 iso/iso_journey.py 分镜.json --push        # 推草稿箱 + 拉回比对标签（不发布）
python3 iso/iso_journey.py 分镜.json --update <media_id>
```

产物在 `out/<分镜文件名>/`：`long.svg`、`article.html`、`preview.html`（浏览器打开看）、`cover.jpg`、`timeline.json`（每站几秒开始）、`media_id.txt`。

## 分镜字段

```json
{
  "title": "推文标题", "digest": "摘要", "palette": "paper | night",
  "kicker": "顶上一行英文小字", "headline": "大标题（3D版）", "subtitle": "一条路，走过 N 个站",
  "intro": "一两句导语（自动换行）", "start_label": "START", "end_label": "FINISH",
  "stops": [
    {"kind": "分类（同类同色，自动进图例）", "title": "站名", "place": "灰色小字",
     "body": "正文，最多 60 字（事实不够就写短，别凑）", "en": "ENGLISH LABEL", "model": "laptop", "args": {"chip": "MLX"}}
  ],
  "end": {"title": "落版大字", "lines": ["一两行小字"]},
  "advice": {"kicker": "IF YOU WANT ONE", "title": "想自己搭一套？6 条建议", "sub": "一句副标",
             "items": [["一句结论", "为什么（一两行）"]]},
  "tools": {"kicker": "TAKE IT", "title": "拿去就能用", "sub": "一句副标",
            "items": [{"name": "仓库名", "tag": "★ 1089", "kind": "Claude skill", "repo": "github.com/…", "desc": "一两行说明"}],
            "footnote": "卡片下面一行小字", "appendix_title": "文中工具清单（可复制）"},
  "tail": ["最底下一行等宽小字"]
}
```

- 每站可加 `"specs": [["配置", "…"], ["模型", "…"], ["干活", "…"]]`：卡片里虚线下面的参数行，标签用强调色。卡片变长了，站距会自动拉开。
- `advice`：结尾的建议卡（大号序号 + 结论 + 为什么）。**只写自己真踩过的坑**。
- `tools`：结尾的两列工具墙。星数写当天用 `gh repo list` 查到的数，footnote 里注明日期。
  有 `tools` 就会在 SVG 下面加一段**能复制的纯文字清单**（SVG 里的字复制不了，读者要靠这段去搜仓库）。
- 换行按词：英文、数字、型号（Qwen3.5-9B、14.1、4K）不会被拆开，标点不会落到行首。

- 6–10 站最好。超过 12 站页面会很长，读者拉不到底。
- kind 最多 8 种颜色，超出会循环。
- **事实只写查实的**，跟其他模板一样。

## 模型库（`iso/models.py`）

| model | 画面 | args |
|---|---|---|
| `archive` | 一摞数据盘（灯闪）+ 头顶漂档案卡 | — |
| `laptop` | 笔记本，屏上代码条循环重写 + 芯片牌 | `chip`：字符串，牌子上的字（≤4 字符；`""` = 不放牌）；`old`：布尔，小一号的旧机 |
| `gate` | 两柱一楣的门，楣上写字，地上箭头穿门流过 | `text`：字符串，楣上的字（≤6 字符）。**最中性的模型**，什么题材都能用来写一个关键数 |
| `desktop` | 台式机：显示器里方块在转，机箱风扇转、灯条呼吸 | `tag`：字符串，机箱侧面的字（≤8 字符） |
| `server` | 机柜，一格格灯闪 + 隧道管里光点流动 | `slots`：整数，机柜格数（默认 6） |
| `checklist` | 旧笔记本 + 清单板，勾一个个打上 | `items`：整数，打几个勾（默认 4）；`chip` 同 laptop |
| `antenna` | 信号塔一节节长高，塔顶红灯闪，脚下波纹扩散 | — |
| `mailbox` | 信箱，信封一封封掉进去，小旗立起 | `flag`：字符串，箱子上的字（≤2 字） |

现在的模型偏科技（电脑、机房、信号）。**题材对不上时**（咖啡、旅行、餐饮……）：只有一两站用中性的 `gate`，其余按下面「加一个新模型」现做（一个模型通常就是 3–6 个长方体），别拿电脑类模型硬凑，读者会被误导。

通用小件：`tree` / `bush` / `lamp` / `tile_path`（铺路砖），每个模型都可以加。

### 加一个新模型

```python
def 名字(b, 参数=默认):
    iso, p, a = b.iso, b.pal, b.acc      # 投影、配色、本站强调色
    platform(b)                          # 先放底座
    z = b.z + 0.06                       # 底座顶面
    b.add(iso.slab(X, Y, z, w, d, h, 颜色, deco_left=..., deco_right=..., deco_top=...))  # 掉下来一块
    ...
MODELS["名字"] = 名字
```

- 坐标：X 往右下、Y 往左下、Z 往上；底座 8×8 格，1 格 26px（整站再放大 1.25 倍）。
- **画的顺序就是遮挡顺序**：先画后面的（X+Y 小），再画前面的。树挡住机器多半就是顺序错了。
- `deco_left/right/top` 是贴在面上的 2D 片段（面上的像素坐标，u 往右、v 往下）：屏幕、窗户、文字、风扇都这样贴。
- 循环动画（闪、转、浮）的开始时间用 `b.live`，即上一个零件落地之后。
- 积木在 `iso/isokit.py`：`box/slab`、`cylinder`、`ellipse_top`，以及 `drop/appear/blink/spin/bob`。

## 带图片帧的产品故事（`iso/fm_models.py`）

样例：`templates/storyboards/等轴测-小耳FM洗衣房.json`（小耳FM：把一首歌洗成一幅画）。适合手上有**真实 3D 资产或作品图**的产品：
把产品网页里的 3D 模型、App 渲染出来的画逐帧截成 jpg，拼成会动的站点。

```bash
python3 iso/iso_journey.py templates/storyboards/等轴测-小耳FM洗衣房.json --grow --speed 0.8
```

在上面字段基础上多了：

| 字段 | 作用 |
|---|---|
| `"palette": "fm"` | 奶油底 + 珊瑚红 |
| `"assets": "文件夹名"` | 图片放在分镜旁边这个子文件夹里，分镜里只写相对路径（`washer/jpg/open.jpg`） |
| `"character": ["role/a.jpg", …]` | 开场和泡泡旁边的角色：一组帧会循环（左右张望），1 张就是静止的；不填用小耳 |
| `"legend": false` | 不显示右上角「N STOPS」和分类图例 |
| `"prologue"` | 开场：`hello` 角色招呼 → `question` 几行大问题 → `glimpses` 左右交替的小画 + 一句话 → `so` / `so_say` → 可选 `why` / `why_say` 一问一答 |
| `"gallery"` | 路走完后的晾衣绳：`works` 每幅 `{name, note, frames}`，三幅一根绳，画沿绳滑进来、夹子夹住、一直轻轻晃，夹好后逐帧显影；可选 `guess`（问题 + 点一下看答案，不点几秒后自动揭开）、`credit`、`outro_say` |
| `"end": {"url": ["前段", "红色段", "后段"]}` | 结尾大网址，中间一段用强调色，下面一道短线 |

站点模型（`model` 填这些名字）：

| 模型 | 用途 | 主要参数 |
|---|---|---|
| `fm_washer` | 能点的一站：`cover` 帧循环 + 「点一下」药丸，点了（或 `auto` 秒后）换成 `wash` | `cover`, `wash`, `hint`, `say`, `aspect` |
| `fm_frames` | 一串帧循环或播一次（洗衣机转） | `frames`, `mode: loop/once`, `step`, `stay`, `say` |
| `fm_done` | 先停在 `still`，再把 `frames` 播一次停在最后一帧 | `frames`, `still`, `dur`, `say` |
| `fm_paint` | 带画框的一幅画，逐帧长出来 | `frames`, `dur`, `name`, `say` |

`say` 是旁边角色的一句话泡泡。角色默认是 `head/jpg/look_00..15.jpg` 16 帧循环摇头，点一下会弹一下；用 `character` 换成你自己的（产品吉祥物、logo、产品本身都行）。
帧图建议：站点 560 宽 jpg（底色铺成和 `bg` 一样，阴影边缘羽化），画 450×600，每张十几 KB。整篇 129 张图约 3.4MB，正文 HTML 不到 200KB。

`--push` 会先把所有相对路径图片传到你公众号的图床（`media/uploadimg`），缓存在 `out/<分镜名>/mmbiz.json`，再换链接推草稿；推送版另存 `article.mmbiz.html`。

## 公众号实测（2026-11-02）

推草稿再拉回来比对：`transform="matrix(...)"`（贴面用）45/45 保留，animate 533/533，animateTransform 106/106，
`repeatCount`、`keySplines`、`calcMode` 全部保留（微信把属性名改成小写，不影响播放）。

## 品牌 VI 版（`iso/vikit.py`）

甲方给了 VI 手册就照 VI 做，别套彩色等轴测。`vikit.VI` 提供：磨砂玻璃立板 `glass()`、细线底座 `obox()`、
等轴测斜向标尺 `divider()`、测点 `points()`、VI 字体转曲 `zh()/en()/mono()`；`frost_pair()` 从照片做出磨砂图 + 清晰窗。

做之前先读 VI 的三页：**动态原则、禁用、合规**。常见要求（以某医美品牌为例）：
- 禁止弹跳、缩放冲击、光扫、粒子 → 只淡入和描线；标题和法定提示首帧就在、不动
- 窗由虚到实 0.6s，ease-out(.2,.7,.2,1)；测点间隔 0.12s，连线在最后一点后 0.3s 内画出
- 照片不做等轴测斜切（人脸会变形），做成玻璃立板
- 医疗器械类：文末放注册证号、广告审查批准文号、「禁忌内容或者注意事项详见说明书」；禁用词逐条查
- Logo 原件常带 clipPath，公众号会删 → 渲染成透明 PNG 当图片
- 带照片就必须先 `wechat.upload_image` 传到微信图床，`<image href>` 用 mmbiz 链接（实测保留）
