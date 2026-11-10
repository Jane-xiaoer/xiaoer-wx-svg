"""真机上某一幕不动时的排除法。

思路：把不动的那张切片拿出来，做成几个版本（原样 / 去掉某一类东西），每个版本顶上放一根一直在走的红条，
一起推成一篇测试草稿，发到手机上看「哪几根红条在走」。红条不走 = 这个版本的时钟没启动。一次就能定位是哪类东西惹的祸。

    python3 phone_test.py out/article.html <第几张切片，从 0 数> [--push "手机测试"]

不加 --push 只生成 out/phone_test.html，可以先在电脑上打开看红条都在走。
版本：1 原样  2 去掉对 y / height 的循环动画  3 去掉全部图片  4 去掉全部 <path>（转曲的字和线）  5 去掉全部循环动画
已知结论（iPhone 微信）：版本 2 能走而版本 1 不走 → 就是 y / height 的循环动画，改成 animateTransform scale。
"""
import re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def bar(i, y0, w=750):
    return (f'<rect x="0" y="{y0}" width="{w}" height="26" fill="#eee"/><rect x="0" y="{y0}" width="0" height="26" fill="#E0503F">'
            f'<animate attributeName="width" values="0;{w}" dur="4s" repeatCount="indefinite"/></rect>'
            + "".join(f'<circle cx="{20 + k * 26}" cy="{y0 + 13}" r="8" fill="#222"/>' for k in range(i)))   # 几个黑点 = 第几个版本


def variants(svg):
    yield 1, svg
    yield 2, re.sub(r'<animate attributeName="(?:y|height)"[^>]*repeatCount="indefinite"[^>]*/>', "", svg)
    yield 3, re.sub(r"<image[^>]*?(?:/>|>.*?</image>)", "", svg, flags=re.S)
    yield 4, re.sub(r"<path[^>]*?(?:/>|>.*?</path>)", "", svg, flags=re.S)
    yield 5, re.sub(r'<animate(?:Transform)?[^>]*repeatCount="indefinite"[^>]*/>', "", svg)


def main():
    art = Path(sys.argv[1]).read_text(encoding="utf-8")
    svgs = re.findall(r"<svg.*?</svg>", art, re.S)
    svg = svgs[int(sys.argv[2])]
    y0 = float(re.search(r'viewBox="0 (\S+) ', svg).group(1))
    out = ""
    for i, v in variants(svg):
        v = re.sub(r"(<svg[^>]*>)", lambda m: m.group(1) + bar(i, y0), v, count=1)
        out += f'<section style="line-height:0;margin-bottom:24px;">{v}</section>'
    out_p = Path(sys.argv[1]).parent / "phone_test.html"
    import svgkit
    out_p.write_text("<!doctype html><meta charset=utf-8><body style='margin:0;max-width:430px'>" + out.replace('href="assets/', f'href="{(Path(sys.argv[1]).parent.parent / "assets").resolve().as_uri()}/'), encoding="utf-8")
    print(out_p, "（黑点个数 = 版本号）")
    if "--push" in sys.argv:
        import wxapi
        title = sys.argv[sys.argv.index("--push") + 1]
        tok = wxapi.token()
        body = wxapi.localize(out, Path(sys.argv[1]).parent.parent, Path(sys.argv[1]).parent / "mmbiz.json", tok)
        print("测试草稿：", wxapi.save_draft(tok, body, title, str(Path(sys.argv[1]).parent / "cover.jpg"), digest="诊断用，别发"))


if __name__ == "__main__":
    main()
