# 小耳公众号SVG · xiaoer-wx-svg

**让公众号文章自己动起来。** 纯 SVG 动效长图：往下拉，一屏屏长出来。线稿自己画、数字滚动、等轴测 3D 小场景一块块拼好、品牌照片从磨砂到清晰。没有视频、没有 GIF、没有一行代码在跑，公众号原生支持。

👉 演示和模板：**https://svg.xiaoeromia.com** · 粘贴台：**https://svg.xiaoeromia.com/paste/**

由 [Xiaoer Omia](https://xiaoeromia.com) 出品。

## 怎么用：交给你的 AI agent

这个仓库本身就是一个 **Agent Skill**（入口 [`SKILL.md`](SKILL.md)），Claude Code、Codex、Cursor 这类 agent 都能直接用。

```bash
# Claude Code
git clone https://github.com/Jane-xiaoer/xiaoer-wx-svg ~/.claude/skills/xiaoer-wx-svg
# 其他 agent：clone 到任意位置，让它先读 SKILL.md
```

然后跟 agent 说：

> 用 xiaoer-wx-svg 给我做一篇公众号 SVG 动效长图，题材是：____，资料在：____

agent 会问你题材、资料、选哪种形式，生成后自己截帧检查，把文中每一条事实列出来让你确认，最后：

- **填了公众号 AppID**：直接推进你自己的草稿箱，并拉回来比对有没有被删东西；
- **不想填**：打开粘贴台，一键复制，粘进公众号编辑器。

发布永远由你自己点。

## 四条路

| | 适合 | 入口 |
|---|---|---|
| **套模板** | 产品介绍、工具、方法论、日常稿 | `motion/make.py` + [`motion/STORYBOARD.md`](motion/STORYBOARD.md)（14 种场景、6 套配色） |
| **等轴测旅程（3D）** | 流程、路线、链路、几站串起来的故事 | `iso/iso_journey.py` + [`iso/README.md`](iso/README.md) |
| **品牌 VI 版** | 甲方给了 VI 的品牌稿 | `iso/vikit.py`（磨砂玻璃立板、清晰窗由虚到实、标尺测量线、VI 字体转曲） |
| **片子改编（视频 → 长图）** | 已经有一支成片，想让它在公众号里打开就自己往下演 | [`film/README.md`](film/README.md)：七步流程 + 八份分步文档 + 自带工具包（`film/kit/starter.py` 不要素材就能跑通）。[成品在线看](https://svg.xiaoeromia.com/work/xiaoer-aka/) |

分镜样例在 `templates/storyboards/`，找最像的一份改。

## 自己跑

```bash
pip install -r requirements.txt
python3 -m playwright install chromium        # 可选：封面图和截帧

python3 motion/make.py templates/storyboards/方法论-番茄工作法.json       # → out/方法论-番茄工作法/preview.html
python3 iso/iso_journey.py templates/storyboards/等轴测-小耳的四台电脑.json
python3 iso/iso_journey.py templates/storyboards/等轴测-小耳FM洗衣房.json --grow --speed 0.8   # 带真图片帧的产品故事
python3 tools/paste.py out/方法论-番茄工作法/article.html                 # 打开粘贴台，一键复制

# 推进你自己的草稿箱
python3 motion/config.py --set wx_appid 你的AppID --set wx_secret 你的AppSecret
python3 motion/make.py 分镜.json --push
```

推送需要把你电脑的公网 IP 加进公众号后台的 IP 白名单（第一次推会提示是哪个 IP）。

## 最值钱的部分：公众号到底会删什么

[`docs/wechat-svg-rules.md`](docs/wechat-svg-rules.md)：所有 id、fill-opacity 动画、xlink:href、滤镜、渐变、mask、clipPath、style、JS 都会被删；插音频整篇拒收；animate、animateTransform、点击触发、微信图床图片会保留……每一条都是推进草稿箱、再拉回来逐个标签比对出来的。

## 加模板

- 新场景：`motion/scenes_extra.py`，注册进 `SCENES`，补 `motion/STORYBOARD.md`
- 新 3D 模型：`iso/models.py`，注册进 `MODELS`
- 欢迎提 PR。模板持续更新，`git pull` 就能拿到。

## 许可

代码 MIT。示例分镜文案 © Jane-xiaoer，见 [`NOTICE.md`](NOTICE.md)。

---

**English**: Animated, pure-SVG long-form posts for WeChat Official Accounts. Content grows screen by screen as readers scroll: self-drawing line art, counters, isometric 3D scenes. No video, no JS. Ships as an Agent Skill (`SKILL.md`) for Claude Code / Codex / Cursor. Push to your own WeChat draft box, or copy with one click via the paste station at https://svg.xiaoeromia.com/paste/. Includes a tested list of what WeChat strips from SVG. Made by [Xiaoer Omia](https://xiaoeromia.com). MIT.
