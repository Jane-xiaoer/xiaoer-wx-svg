#!/usr/bin/env python3
"""把生成好的文章送到粘贴台：https://svg.xiaoeromia.com/paste/ → 预览 → 一键复制 → 粘进公众号编辑器。

  python3 tools/paste.py out/xxx/article.html          # 打开浏览器
  python3 tools/paste.py out/xxx/article.html --print  # 只打印链接

文章压缩后放在网址的 # 后面：# 后面的内容浏览器不会发给服务器，文章不会上传到任何地方。
太大（压缩后超过约 1.5MB）就改成在粘贴台里拖入 article.html 文件。
"""
import argparse
import base64
import subprocess
import sys
import webbrowser
import zlib
from pathlib import Path

PASTE = "https://svg.xiaoeromia.com/paste/"
LIMIT = 1_500_000


def link(html, base=PASTE):
    c = zlib.compressobj(9, zlib.DEFLATED, -15)  # deflate-raw，浏览器用 DecompressionStream 解
    raw = c.compress(html.encode("utf-8")) + c.flush()
    return base + "#z=" + base64.urlsafe_b64encode(raw).decode().rstrip("=")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("article")
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--base", default=PASTE, help="粘贴台地址（自己部署时改）")
    a = ap.parse_args()
    p = Path(a.article)
    html = p.read_text(encoding="utf-8")
    if "file://" in html or 'href="assets/' in html:
        print("⚠️ 文章里有本地图片：粘进公众号会丢。先填公众号 AppID 用 --push 把图传到微信图床，或换不带照片的模板。")
    url = link(html, a.base)
    if len(url) > LIMIT:
        print(f"文章太大（链接 {len(url) // 1024}KB），请打开 {a.base} 把这个文件拖进去：\n  {p.resolve()}")
        if not a.print:
            webbrowser.open(a.base)
            if sys.platform == "darwin":
                subprocess.run(["open", "-R", str(p.resolve())])
        return
    if a.print:
        print(url)
    else:
        webbrowser.open(url)
        print(f"✅ 已在浏览器打开粘贴台（链接 {len(url) // 1024}KB）。点「复制到公众号」，去公众号编辑器里粘贴。")


if __name__ == "__main__":
    main()
