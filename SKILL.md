---
name: xiaoer-wx-svg
description: 公众号 SVG 动效长图（小耳公众号SVG · Xiaoer Omia 出品）——把一个题材做成微信公众号里「会自己动、往下拉一屏屏长出来」的纯 SVG 长图：线稿自己画、数字滚动、大字砸下、等轴测 3D 小场景一块块拼起来、按品牌 VI 做的磨砂玻璃窗由虚到实。没有视频、GIF 和 JS，公众号原生支持。可以推进用户自己公众号的草稿箱，也可以不填任何 key，用粘贴台一键复制到公众号编辑器。触发词：公众号SVG、公众号动效、动效长图、会动的公众号、SVG 推文、等轴测长图、3D 公众号、往下拉的叙事长图、品牌 VI 公众号。
---

# 小耳公众号SVG（xiaoer-wx-svg）

你（agent）要帮用户做一篇公众号 SVG 动效长图。仓库根目录就是本文件所在目录，下面的命令都在这里执行。

## 0. 安装（第一次）

```bash
pip install -r requirements.txt
python3 -m playwright install chromium   # 只用来出封面图和截帧检查；装不上也能生成文章
```

## 1. 先问清楚（一次问完，别挤牙膏）

1. **题材**：做什么？产品、活动、流程、品牌故事……
2. **事实资料**：官网链接、文档、产品说明。**只用这里面的事实。**
3. **形式**：给用户看下面「四条路」，帮他挑一条，或者你根据题材推荐。
4. **怎么交付**：
   - 有公众号 **AppID / AppSecret**：直接推进他自己的草稿箱。
   - 没有，或者不想给：生成后用**粘贴台**一键复制，手动粘进公众号编辑器。
5. 有没有品牌 VI、Logo、主色？有 VI 就走品牌 VI 版。
6. 产品**网站上有 3D 模型 / 动画**，或者手上有一组作品图、渲染图？有就推荐「带图片帧的产品故事」。

## 2. 四条路

| 路 | 适合 | 怎么做 | 说明 |
|---|---|---|---|
| **套模板** | 产品介绍、工具、方法论、日常稿 | 照 `motion/STORYBOARD.md` 写分镜 JSON → `python3 motion/make.py 分镜.json` | 14 种场景、6 套配色，每屏 7–11 秒 |
| **等轴测旅程（3D）** | 有先后的流程、路线、链路、几站串起来的故事 | 照 `iso/README.md` 写分镜 → `python3 iso/iso_journey.py 分镜.json [--grow]` | Z 字公路串起 N 个 2.5D 小场景，光点沿路跑；结尾可以加「建议卡」和「工具墙」 |
| **带图片帧的产品故事（3D）** | 对方网站上有 3D 模型或动画，或手上有作品图 / 渲染图（要 AppID 传图床） | **先读 `docs/web-to-frames.md`**：`tools/web_frames.py capture` 从网站截帧 → `compose` 合成并自动分段 → 照 `templates/storyboards/等轴测-小耳FM洗衣房.json` 改分镜 → `iso_journey.py --grow --speed 0.8` | 浪漫开场问一句、角色说话泡泡、产品真帧在动、作品一幅幅晾上绳子、点一下猜答案、结尾大网址。语气像聊天，站点上不写小字 |
| **品牌 VI 版** | 用户给了 VI 手册的品牌稿 | 先读 VI 的动态原则、禁用页、合规页，再用 `iso/vikit.py` 写一个专用脚本 | 磨砂玻璃立板、清晰窗由虚到实、标尺测量线、VI 字体转曲 |

**分镜一定从样例改**：`templates/storyboards/` 里找最像的一份复制过来改。每屏换什么场景、写什么字，按题材来定，别每篇都一个顺序。

## 3. 铁律

- **事实只来自用户给的资料。** 不编数字、不编功能、不编价格。写完把文中**每一条事实性说法**列成清单给用户逐条确认。
- 只用公众号保留的东西，先读 `docs/wechat-svg-rules.md`。要点：**没有 id、没有 fill-opacity 动画、没有 xlink:href、没有滤镜 / 渐变 / mask / clipPath / style / JS**；互动只能「点一下揭开」。
- 照片必须先传到**微信图床**（要 AppID）。没有 AppID 就别用带照片的玩法，粘进公众号图会丢。
- 文章控制在 1MB 以内。
- **推到草稿箱 ≠ 发布。** 永远不要替用户发布。
- 用户的 AppSecret 只存在他自己电脑上（`motion/config.py`），不要写进文件、日志或别的地方。

## 4. 生成后自检

```bash
open out/<名字>/preview.html          # 浏览器里看，「重播」从头播
cat out/<名字>/timeline.json          # 每屏 / 每站几秒开始
python3 tools/frames.py out/<名字>/preview.html out/<名字>/frames.png 7.6,0 13.6,1 21.8,2
```

- `frames.py` 的参数是「秒,屏」：秒从 `timeline.json` 里取（想看第 N 屏画完的样子，填第 N+1 屏的开始秒数）；屏按 1080×1920 一屏，从 0 数，可以写小数。等轴测是一张长图，「屏」不等于「站」，先截 0、1、2 看位置再调。
- 用你的看图能力看截图：字有没有挤、有没有压到图、下一屏是不是提前长出来、画面跟题材搭不搭。
- 节奏：两条路都能加 `--speed`（0.85 = 快 15%，1.2 = 慢 20%）。
- 画面和题材对不上（比如讲咖啡却出现机柜、声波），宁可换场景或按第 6 节做新的，别硬凑。

## 5. 交付

**A. 有 AppID：推草稿箱**

```bash
python3 motion/config.py --set wx_appid 你的AppID --set wx_secret 你的AppSecret   # 只存本机，权限 600
python3 motion/make.py 分镜.json --push          # 等轴测：python3 iso/iso_journey.py 分镜.json --push
```

第一次推会提示「IP 不在白名单」：让用户去公众号后台 → 设置与开发 → 开发接口管理 → IP 白名单，加上报错里的那个 IP。
推完会打印「本地 / 草稿」标签数对照表，**数字不一致就说明被删了**，要告诉用户。
然后告诉用户：草稿箱里有了，用「预览」发到手机看，满意再自己群发。

**B. 没有 AppID：粘贴台**

```bash
python3 tools/paste.py out/<名字>/article.html
```

会在浏览器打开 https://svg.xiaoeromia.com/paste/ 。文章放在网址 `#` 后面，不会上传。
没有图形界面（服务器、远程环境）就加 `--print` 只打印链接，链接很长：存成文件交给用户，或者让用户打开粘贴台、把 `out/<名字>/article.html` 拖进去。告诉用户：
1. 点「复制到公众号」
2. 公众号后台 →「新的创作」→「文章」，在正文里粘贴（Ctrl/⌘ + V）
3. 填标题、上传封面（`out/<名字>/cover.jpg`），点「预览」发到手机检查，再群发

## 6. 想要新画面

- 套模板缺场景：在 `motion/scenes_extra.py` 写 `def 场景(d, y, t, th) -> (片段列表, 秒数)`，注册进 `SCENES`，再在 `motion/STORYBOARD.md` 补字段表。
- 等轴测缺模型：在 `iso/models.py` 加一个函数，注册进 `MODELS`（写法见 `iso/README.md`：先画后面再画前面，面上内容用 `deco_*`）。
- 做好的新模板欢迎提 PR：https://github.com/Jane-xiaoer/xiaoer-wx-svg

模板和粘贴台都在更新：`git pull` 就能拿到新模板。模板演示见 https://svg.xiaoeromia.com
