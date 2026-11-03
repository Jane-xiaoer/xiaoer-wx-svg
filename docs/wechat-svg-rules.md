# 公众号 SVG 实测规矩

每一条都是**推进草稿箱、再用接口拉回来逐个标签比对**得出来的（2026-10 到 2026-11）。公众号会悄悄删东西，不报错。

## 会保留 ✅

| 东西 | 说明 |
|---|---|
| `<animate>` | opacity / transform / stroke-dashoffset / width / height / x / y / fill / d 都能动 |
| `<animateTransform>` | translate / rotate / scale |
| `<set>` | |
| `begin="click"`、`touchstart`、`click;3s`、`click+0.5s` | 只能「点到谁，谁自己动」 |
| `calcMode="spline"`、`keySplines`、`keyTimes`、`repeatCount` | 属性名会被改成小写，不影响播放，比对时别当成被删 |
| 静态 `transform="matrix(…)"` | 等轴测贴面靠它，实测 45/45 |
| `<image href="https://mmbiz.qpic.cn/…">` | 内联 SVG 里的图片，实测 18/18；`preserveAspectRatio` 也保留 |
| CSS `background-image`、`<img>` | 正文图先用 `media/uploadimg` 拿 mmbiz 链接 |
| 视频 | `<iframe class="video_iframe" data-mpvid="…">`，vid 从 `material/get_material` 拿 |

## 会被删 / 拒收 ❌

| 东西 | 后果 / 绕法 |
|---|---|
| **所有 `id`** | 「点 A 让 B 动」做不了 → 用「点一下揭开」：上面盖一层，被点后自己淡出并移走 |
| `fill-opacity` 动画 | tspan 逐字打字会永远隐形 → 每个字单独一个 `<text>` 动 opacity |
| `xlink:href` | 用 `href` |
| 滤镜、渐变、mask、clipPath、`<style>`、JS | 模糊要预先做成图片；渐变用多层半透明色块叠；Logo 带 clipPath 就渲染成透明 PNG |
| 音频 `<mpvoice>` | **整篇拒收（45166）** → 声音只能放进视频 |
| `@font-face` | 用不了自定义字体 → 标题转曲（`iso/textpath.py`），正文用系统字体兜底 |

## 其他

- 动画从**读者打开文章那一刻**开始计时，没法跟滚动位置同步；SVG 和声音也没法同步。
- 「页面一屏屏长出来」：长图放在高度为 0 的容器里，下面一个透明画布按时间变宽、高度跟着变（`wxsvg.py`）。
- 正文太大存不下：控制在 1MB 以内（转曲的字是大头，`textpath` 已转相对坐标并取整）。
- 推送不要走会把 HTML 洗一遍的发布工具（pandoc / sanitize 会毁 SVG），用 `motion/wechat.py` 直接调官方接口。
- 公众号接口要把**你电脑的公网 IP** 加进白名单：后台 → 设置与开发 → 开发接口管理 → IP 白名单。
- 粘贴：从网页复制 `text/html` 到公众号编辑器，秀米 / 135 都是这么做的。外链图片在 SVG 里不会被编辑器转存，所以照片要先进微信图床。
- **推到草稿箱 ≠ 发布**，发布永远由人自己点。
