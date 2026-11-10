#!/usr/bin/env python3
"""生成演示站 site/dist：首页、粘贴台、每个模板的演示页、sitemap / robots / llms.txt。

  python3 site/build.py            # 先跑一遍各模板生成 out/，再拼站
  WXSVG_CASES=cases.json python3 site/build.py   # 另加首页「真实作品」栏（作品文件不进仓库）

cases.json：[{"slug","title","product","desc","article": 本地 article.html 路径, "t": 缩略图秒数,
             "link": 产品网址, "status": "live" | "soon", "files": [要一起放进作品目录的附件路径]}]，
             status=soon 的只显示「制作中」卡片。
部署：Vercel 静态站，根目录 site/dist（自己部署也行，纯静态）。
"""
import asyncio
import json
import os
import tempfile
import shutil
import subprocess
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DIST = HERE / "dist"
OUT = ROOT / "out"
BASE = "https://svg.xiaoeromia.com"
REPO = "https://github.com/Jane-xiaoer/xiaoer-wx-svg"
OMIA = "https://xiaoeromia.com"

# slug, 名称, 路线, 适合, 生成命令（相对仓库根）, 输出目录名, 缩略图截哪一秒
DEMOS = [
    ("isometric-journey", "等轴测旅程 · 3D", "等轴测旅程", "流程、路线、链路：Z 字公路串起一站站 2.5D 小场景，零件一块块拼起来，光点沿路跑；结尾带建议卡和工具墙",
     ["iso/iso_journey.py", "templates/storyboards/等轴测-小耳的四台电脑.json"], "等轴测-小耳的四台电脑", 40),
    ("fm-laundry", "等轴测 · 产品故事（带图片帧）", "等轴测旅程", "有真实 3D 资产或作品图的产品：浪漫开场问一句、角色说话泡泡、一站站真帧动画、作品一幅幅晾上绳子、点一下猜答案、结尾大网址",
     ["iso/iso_journey.py", "templates/storyboards/等轴测-小耳FM洗衣房.json", "--grow", "--speed", "0.8"], "等轴测-小耳FM洗衣房", 14),
    ("product-launch", "产品发布 · 8 屏", "套模板", "软件产品：一堆东西被吸成品牌、产品窗口长出来、数字滚动、价格卡",
     ["motion/make.py", "templates/storyboards/产品-Omia-8屏.json"], "产品-Omia-8屏", 70),
    ("hardware-app", "硬件 + App · 带互动", "套模板", "硬件产品：账单吐出来盖章、设备蓝牙同步、点一下开会字幕循环冒出",
     ["motion/make.py", "templates/storyboards/硬件加App-录音卡-带互动.json"], "硬件加App-录音卡-带互动", 70),
    ("methodology", "方法论 · 6 屏", "套模板", "方法、清单、教程：线稿自己画、三个大字砸下、要点卡片",
     ["motion/make.py", "templates/storyboards/方法论-番茄工作法.json"], "方法论-番茄工作法", 60),
    ("minimal", "最小示例 · 3 屏", "底层格式", "直接写元素和时间轴：画圈、放大、逐字出现，适合想自己从零搭的人",
     ["wxsvg.py", "templates/raw/最小示例-3屏.json"], "最小示例-3屏", 20),
]

CSS = """
:root{--paper:#F5F1E8;--ink:#25343A;--muted:#6F7B76;--line:#DCD6C8;--accent:#2F6D6A;--card:#fff}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font-family:-apple-system,"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;line-height:1.7}
a{color:var(--accent)}
.wrap{max-width:1120px;margin:0 auto;padding:0 20px}
.mono{font-family:"SFMono-Regular",Menlo,Consolas,monospace;letter-spacing:.14em;font-size:12px;color:var(--accent);text-transform:uppercase}
nav{display:flex;justify-content:space-between;align-items:center;padding:18px 0;border-bottom:1px solid var(--line)}
nav a{color:var(--ink);text-decoration:none;margin-left:20px;font-size:15px}
.btn{display:inline-block;padding:12px 22px;border-radius:6px;background:var(--accent);color:#fff;text-decoration:none;font-size:16px;border:0;cursor:pointer;font-family:inherit}
.btn.ghost{background:transparent;color:var(--ink);border:1px solid var(--line)}
.phone{width:375px;max-width:100%;background:#111;border-radius:30px;padding:12px;box-shadow:0 24px 60px rgba(37,52,58,.25)}
.screen{background:#fff;border-radius:20px;overflow:hidden;height:720px;overflow-y:auto}
.screen h1{font-size:19px;line-height:1.4;margin:0;padding:16px 16px 4px;color:#111}
.screen .meta{font-size:12px;color:#999;padding:0 16px 12px}
footer{border-top:1px solid var(--line);margin-top:80px;padding:28px 0 60px;color:var(--muted);font-size:14px}
"""

COPY_JS = """
function copyHtml(html,ok,fail){
  const done=()=>ok&&ok();
  if(navigator.clipboard&&window.ClipboardItem){
    navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([html],{type:'text/html'}),'text/plain':new Blob(['请在公众号编辑器里粘贴'],{type:'text/plain'})})]).then(done,()=>legacy());
  }else legacy();
  function legacy(){const box=document.createElement('div');box.contentEditable='true';box.style.cssText='position:fixed;left:-9999px;top:0;width:375px';
    box.innerHTML=html;document.body.appendChild(box);const r=document.createRange();r.selectNodeContents(box);
    const s=getSelection();s.removeAllRanges();s.addRange(r);const k=document.execCommand('copy');s.removeAllRanges();box.remove();k?done():(fail&&fail());}
}
"""


def head(title, desc, path, index=True, extra=""):
    robots = "index,follow" if index else "noindex,nofollow"
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer">
<meta name="robots" content="{robots}">
<title>{escape(title)}</title>
<meta name="description" content="{escape(desc)}">
<link rel="canonical" href="{BASE}{path}">
<meta property="og:title" content="{escape(title)}"><meta property="og:description" content="{escape(desc)}">
<meta property="og:site_name" content="小耳公众号SVG · Xiaoer Omia"><meta property="og:url" content="{BASE}{path}">
<meta property="og:image" content="{BASE}/og.jpg">
<style>{CSS}</style>{extra}</head><body>"""


NAV = f"""<div class="wrap"><nav><a href="/" style="margin:0;font-weight:700">小耳公众号SVG</a>
<span><a href="/#works">作品</a><a href="/#templates">模板</a><a href="/paste/">粘贴台</a><a href="{REPO}">GitHub</a><a href="{OMIA}">Xiaoer Omia</a></span></nav></div>"""

FOOT = f"""<footer><div class="wrap">小耳公众号SVG 由 <a href="{OMIA}">Xiaoer Omia</a> 出品。Xiaoer Omia：一个窗口打开 150 多种文件的万能阅读器。<br>
代码 MIT 开源：<a href="{REPO}">{REPO.replace("https://", "")}</a> · 推到草稿箱 ≠ 发布，发布永远由你自己点。</div></footer>"""


def demo_page(slug, name, route, fit, article, sb_path=""):
    title = f"{name} · 公众号 SVG 动效模板 · 小耳公众号SVG"
    desc = f"{name}：{fit}。纯 SVG，公众号原生支持，可一键复制到公众号编辑器。"
    return head(title, desc, f"/t/{slug}/") + NAV + f"""
<div class="wrap" style="display:grid;grid-template-columns:400px 1fr;gap:48px;padding-top:36px;align-items:start" id="g">
<div><div class="phone"><div class="screen" id="screen"><h1>{escape(name)}</h1><div class="meta">演示 · 动画从打开那一刻开始</div><div id="art"></div></div></div>
<p style="text-align:center"><button class="btn ghost" onclick="replay()">重播</button></p></div>
<div><div class="mono">{escape(route)}</div><h2 style="font-size:34px;margin:6px 0 10px">{escape(name)}</h2>
<p style="color:var(--muted);font-size:17px">{escape(fit)}</p>
<p><button class="btn" id="cp" onclick="cp()">复制这个演示到公众号</button> <span id="msg" style="color:var(--accent)"></span></p>
<h3 style="margin-top:40px">想用这个模板做你自己的内容</h3>
<p>把仓库交给你的 AI agent（Claude Code、Codex、Cursor……），说：</p>
<pre id="ask" style="white-space:pre-wrap;background:#fff;border:1px solid var(--line);border-radius:6px;padding:14px;font-size:14px">用 {REPO} 的「{escape(route)}」{f"（照 {escape(sb_path)} 改）" if sb_path else ""}给我做一篇公众号 SVG 动效长图，题材是：____，资料在：____</pre>
<p><button class="btn ghost" onclick="cpText()">复制这句话</button> <a class="btn ghost" href="{REPO}">去 GitHub</a></p>
</div></div>
<template id="src">{article.replace("</template", "<\\\\/template")}</template>
<script>{COPY_JS}
const src=document.getElementById('src').innerHTML.trim();
function replay(){{const a=document.getElementById('art');a.innerHTML='';document.getElementById('screen').scrollTop=0;requestAnimationFrame(()=>a.innerHTML=src);}}
function cp(){{copyHtml(src,()=>msg.textContent='已复制，去公众号编辑器里粘贴',()=>msg.textContent='复制失败，换 Chrome 再试');}}
function cpText(){{navigator.clipboard.writeText(document.getElementById('ask').textContent);msg.textContent='已复制这句话';}}
if(innerWidth<900)document.getElementById('g').style.gridTemplateColumns='1fr';
replay();</script>""" + "<div class='wrap'>" + FOOT + "</div></body></html>"


def case_page(c, article):
    title = f"{c['title']} · {c['product']} · 小耳公众号SVG 真实作品"
    desc = f"{c['product']}：{c['desc']}。用小耳公众号SVG 做的真实公众号动效长图。"
    return head(title, desc, f"/work/{c['slug']}/") + NAV + f"""
<div class="wrap" style="display:grid;grid-template-columns:400px 1fr;gap:48px;padding-top:36px;align-items:start" id="g">
<div><div class="phone"><div class="screen" id="screen"><h1>{escape(c['title'])}</h1><div class="meta">真实作品 · 动画从打开那一刻开始</div><div id="art"></div></div></div>
<p style="text-align:center"><button class="btn ghost" onclick="replay()">重播</button></p></div>
<div><div class="mono">REAL WORK · {escape(c['product'])}</div><h2 style="font-size:34px;margin:6px 0 10px">{escape(c['title'])}</h2>
<p style="color:var(--muted);font-size:17px">{escape(c['desc'])}</p>
<p>这是小耳自己的产品，文章原样放在这里，和发进公众号的是同一份。</p>
<p>{f'<a class="btn" href="{escape(c["link"])}">去看{escape(c["product"])}</a> ' if c.get("link") else ""}<a class="btn ghost" href="/#templates">用模板做你自己的</a></p>
</div></div>
<template id="src">{article.replace("</template", "<\\\\/template")}</template>
<script>const src=document.getElementById('src').innerHTML.trim();
function replay(){{const a=document.getElementById('art');a.innerHTML='';document.getElementById('screen').scrollTop=0;requestAnimationFrame(()=>a.innerHTML=src);}}
if(innerWidth<900)document.getElementById('g').style.gridTemplateColumns='1fr';
replay();</script>""" + "<div class='wrap'>" + FOOT + "</div></body></html>"


def cases_section(cases):
    if not cases:
        return ""
    def card(c):
        if c.get("status") == "soon":
            return f"""<div style="background:#fff;border:1px dashed var(--line);border-radius:10px;overflow:hidden">
<div style="aspect-ratio:4/5;display:flex;align-items:center;justify-content:center;background:var(--paper);color:var(--muted);font-size:15px">制作中</div>
<div style="padding:14px 16px 18px"><div class="mono">{escape(c['product'])}</div><div style="font-size:19px;font-weight:700;margin:4px 0">{escape(c['title'])}</div>
<div style="color:var(--muted);font-size:14px">{escape(c['desc'])}</div></div></div>"""
        return f"""<a href="/work/{c['slug']}/" style="text-decoration:none;color:inherit;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden;display:block">
<img src="/work/{c['slug']}/thumb.jpg" alt="{escape(c['title'])} 截图" loading="lazy" style="display:block;width:100%;aspect-ratio:4/5;object-fit:cover;object-position:top;background:#eee">
<div style="padding:14px 16px 18px"><div class="mono">{escape(c['product'])}</div><div style="font-size:19px;font-weight:700;margin:4px 0">{escape(c['title'])}</div>
<div style="color:var(--muted);font-size:14px">{escape(c['desc'])}</div></div></a>"""
    return f"""<div class="wrap" id="works" style="padding-top:80px"><div class="mono">REAL WORK</div><h2 style="font-size:34px;margin:6px 0 8px">真实作品</h2>
<p style="color:var(--muted);margin:0 0 24px">小耳自己的产品，用这套工具做的真实公众号文章。</p>
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:20px">{"".join(card(c) for c in cases)}</div></div>
"""


def paste_page():
    title = "粘贴台：把 SVG 动效长图一键复制到公众号 · 小耳公众号SVG"
    desc = "把 AI agent 生成的公众号 SVG 动效文章放进来预览，一键复制，粘贴到公众号编辑器就能发布。文章只在你的浏览器里，不上传。"
    return head(title, desc, "/paste/") + NAV + """
<div class="wrap" style="padding-top:28px">
<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;position:sticky;top:0;background:var(--paper);padding:12px 0;z-index:5;border-bottom:1px solid var(--line)">
<button class="btn" id="cp" onclick="cp()" disabled>复制到公众号</button>
<button class="btn ghost" onclick="replay()">重播</button>
<label class="btn ghost" style="cursor:pointer">打开 article.html<input type="file" accept=".html,.htm" id="file" hidden></label>
<span id="msg" style="color:var(--accent)"></span></div>
<div id="warn" style="display:none;margin-top:14px;padding:12px 14px;border:1px solid #d9a441;background:#fff8ea;border-radius:6px;font-size:14px"></div>
<div id="drop" style="margin-top:24px;border:2px dashed var(--line);border-radius:10px;padding:60px 20px;text-align:center;color:var(--muted)">
<p style="font-size:18px;margin:0 0 6px">把 agent 生成的 <b>article.html</b> 拖到这里</p>
<p style="margin:0">或者让 agent 运行 <code>python3 tools/paste.py out/…/article.html</code>，会自动带着文章打开本页。文章只在你的浏览器里，不会上传。</p></div>
<div style="display:flex;justify-content:center;margin-top:24px"><div class="phone" id="ph" style="display:none"><div class="screen" id="screen"><div id="art"></div></div></div></div>
<ol style="max-width:640px;margin:36px auto 0;font-size:16px;color:var(--muted)">
<li>点「复制到公众号」</li><li>公众号后台 →「新的创作」→「文章」，在正文里按 Ctrl / ⌘ + V</li>
<li>填标题、上传封面，点「预览」发到手机检查，再群发</li></ol></div>
<script>""" + COPY_JS + r"""
let src='';
function show(html){src=html.trim();document.getElementById('drop').style.display='none';document.getElementById('ph').style.display='block';
  document.getElementById('cp').disabled=false;
  const w=document.getElementById('warn');
  if(/file:\/\/|href="(?!https?:)[^"]+\.(jpe?g|png|gif|webp)"/i.test(src)){w.style.display='block';w.textContent='⚠️ 文章里有本地图片，粘进公众号会丢失。请先在 agent 里填公众号 AppID，用 --push 把图片传到微信图床。';}
  replay();}
function replay(){if(!src)return;const a=document.getElementById('art');a.innerHTML='';document.getElementById('screen').scrollTop=0;requestAnimationFrame(()=>a.innerHTML=src);}
function cp(){copyHtml(src,()=>msg.textContent='已复制，去公众号编辑器里粘贴',()=>msg.textContent='复制失败，换 Chrome / Edge 再试');}
async function fromHash(){const m=location.hash.match(/z=([A-Za-z0-9_-]+)/);if(!m)return;
  try{let b=m[1].replace(/-/g,'+').replace(/_/g,'/');while(b.length%4)b+='=';
    const bytes=Uint8Array.from(atob(b),c=>c.charCodeAt(0));
    const ds=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
    show(await new Response(ds).text());}catch(e){msg.textContent='链接里的文章读不出来：'+e;}}
function readFile(f){const r=new FileReader();r.onload=()=>show(r.result);r.readAsText(f,'utf-8');}
document.getElementById('file').onchange=e=>e.target.files[0]&&readFile(e.target.files[0]);
const d=document.getElementById('drop');['dragover','dragenter'].forEach(k=>addEventListener(k,e=>{e.preventDefault();d.style.borderColor='#2F6D6A';}));
addEventListener('drop',e=>{e.preventDefault();const f=e.dataTransfer.files[0];f&&readFile(f);});
fromHash();
</script>""" + "<div class='wrap'>" + FOOT + "</div></body></html>"


def index_page(cards, hero_article, cases=()):
    title = "小耳公众号SVG：让公众号文章自己动起来 · 免费开源 · Xiaoer Omia"
    desc = "纯 SVG 公众号动效长图：往下拉一屏屏长出来，线稿自己画、数字滚动、等轴测 3D 小场景一块块拼起来。没有视频和代码，公众号原生支持。交给你的 AI agent 就能做，一键复制到公众号。"
    ld = json.dumps({"@context": "https://schema.org", "@type": "SoftwareApplication", "name": "小耳公众号SVG（xiaoer-wx-svg）",
                     "applicationCategory": "DesignApplication", "operatingSystem": "macOS, Windows, Linux",
                     "offers": {"@type": "Offer", "price": "0", "priceCurrency": "CNY"}, "url": BASE, "sameAs": [REPO],
                     "publisher": {"@type": "Organization", "name": "Xiaoer Omia", "url": OMIA}, "description": desc}, ensure_ascii=False)
    grid = "".join(f"""<a href="/t/{s}/" style="text-decoration:none;color:inherit;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden;display:block">
<img src="/t/{s}/thumb.jpg" alt="{escape(n)} 演示截图" loading="lazy" style="display:block;width:100%;aspect-ratio:4/5;object-fit:cover;object-position:top;background:#eee">
<div style="padding:14px 16px 18px"><div class="mono">{escape(r)}</div><div style="font-size:19px;font-weight:700;margin:4px 0">{escape(n)}</div>
<div style="color:var(--muted);font-size:14px">{escape(fit)}</div></div></a>""" for s, n, r, fit in cards)
    ask = f"用 {REPO} 给我做一篇公众号 SVG 动效长图，题材是：____，资料在：____"
    return head(title, desc, "/", extra=f'<script type="application/ld+json">{ld}</script>') + NAV + f"""
<div class="wrap" style="display:grid;grid-template-columns:1fr 400px;gap:56px;padding-top:56px;align-items:center" id="hero">
<div><div class="mono">FREE · OPEN SOURCE · FOR YOUR AI AGENT</div>
<h1 style="font-size:52px;line-height:1.2;margin:10px 0 16px">让公众号文章<br>自己动起来</h1>
<p style="font-size:19px;color:var(--muted)">纯 SVG 动效长图：往下拉，一屏屏长出来。线稿自己画、数字滚动、3D 小场景一块块拼好。<br>没有视频、没有 GIF、没有一行代码在跑，公众号原生支持。</p>
<p style="font-size:17px">交给你的 AI agent（Claude Code、Codex、Cursor……），它会问你题材和资料，生成、自检，然后推进你的草稿箱，或者在这里一键复制。</p>
<p><a class="btn" href="#start">开始用</a> <a class="btn ghost" href="#templates">看模板</a> <a class="btn ghost" href="{REPO}">GitHub</a></p></div>
<div><div class="phone"><div class="screen" id="screen"><h1>一句话，走过小耳的四台电脑（3D版）</h1><div class="meta">真实演示 · 往下滑</div><div id="art"></div></div></div></div></div>

{cases_section(cases)}<div class="wrap" id="start" style="padding-top:80px"><div class="mono">HOW</div><h2 style="font-size:34px;margin:6px 0 24px">三步</h2>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px" class="three">
<div style="background:#fff;border:1px solid var(--line);border-radius:10px;padding:22px"><b style="font-size:30px;color:var(--accent)">01</b><h3>把仓库交给 agent</h3>
<pre id="ask" style="white-space:pre-wrap;font-size:13px;background:var(--paper);padding:10px;border-radius:6px">{escape(ask)}</pre><button class="btn ghost" onclick="navigator.clipboard.writeText(document.getElementById('ask').textContent);this.textContent='已复制'">复制这句话</button></div>
<div style="background:#fff;border:1px solid var(--line);border-radius:10px;padding:22px"><b style="font-size:30px;color:var(--accent)">02</b><h3>agent 问你、生成、自检</h3>
<p style="color:var(--muted)">题材、资料、选哪种形式。事实只用你给的资料，写完把每一条事实列出来让你确认。</p></div>
<div style="background:#fff;border:1px solid var(--line);border-radius:10px;padding:22px"><b style="font-size:30px;color:var(--accent)">03</b><h3>进草稿箱，或一键复制</h3>
<p style="color:var(--muted)">填了公众号 AppID 就直接推进你的草稿箱；不想填就用<a href="/paste/">粘贴台</a>一键复制，粘进公众号编辑器。发布永远由你自己点。</p></div></div></div>

<div class="wrap" id="templates" style="padding-top:80px"><div class="mono">TEMPLATES</div><h2 style="font-size:34px;margin:6px 0 8px">模板</h2>
<p style="color:var(--muted);margin:0 0 24px">持续更新。<code>git pull</code> 就能拿到新模板，也欢迎提 PR。</p>
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:20px">{grid}</div></div>

<div class="wrap" style="padding-top:80px"><div class="mono">TESTED</div><h2 style="font-size:34px;margin:6px 0 12px">公众号会悄悄删掉什么，我们一条条试过</h2>
<p style="color:var(--muted);max-width:760px">所有 id、fill-opacity 动画、xlink:href、滤镜、渐变、mask、clipPath、style、JS 都会被删；插音频整篇拒收。保留的是 animate、animateTransform、点击触发、微信图床图片……每一条都是推进草稿箱再拉回来逐个标签比对出来的。</p>
<p><a class="btn ghost" href="{REPO}/blob/main/docs/wechat-svg-rules.md">看完整规矩表</a></p></div>
<template id="src">{hero_article.replace("</template", "<\\\\/template")}</template>
<script>const src=document.getElementById('src').innerHTML.trim();document.getElementById('art').innerHTML=src;
if(innerWidth<900){{document.getElementById('hero').style.gridTemplateColumns='1fr';document.querySelector('.three').style.gridTemplateColumns='1fr';}}</script>
<div class="wrap">{FOOT}</div></body></html>"""


def with_mmbiz(article, sbdir, assets):
    """模板带本地图片时，演示页换成微信图床链接（模板文件夹里的 mmbiz.json）：页面能看，复制进公众号也不丢图。"""
    if not assets:
        return article
    mp = sbdir / assets / "mmbiz.json"
    if not mp.exists():
        return article
    pre = assets.rstrip("/") + "/"
    for rel, url in json.loads(mp.read_text(encoding="utf-8")).items():
        article = article.replace(f'href="{pre}{rel}"', f'href="{url}"')
    return article


async def thumbs(jobs):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1350})
        tmp = Path(tempfile.mkdtemp()) / "thumb.html"
        for article, t, dest, base in jobs:
            # 临时页放系统临时目录，<base> 指回分镜目录，相对路径的图片才截得到
            tmp.write_text(f'<!doctype html><base href="{Path(base).resolve().as_uri()}/"><body style="margin:0;width:1080px">{article}</body>',
                           encoding="utf-8")
            await pg.goto(tmp.as_uri())
            await pg.wait_for_load_state("load")
            await pg.wait_for_timeout(300)
            await pg.evaluate(f"document.querySelectorAll('svg').forEach(s=>{{s.pauseAnimations();s.setCurrentTime({t})}})")
            await pg.wait_for_timeout(200)
            await pg.screenshot(path=str(dest), type="jpeg", quality=82, clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
        await b.close()


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "paste").mkdir(parents=True)
    cards, jobs, urls = [], [], ["/", "/paste/"]
    hero = None
    for slug, name, route, fit, cmd, outname, t in DEMOS:
        subprocess.run([sys.executable, *cmd], cwd=ROOT, check=True, capture_output=True)
        art = (OUT / outname / "article.html").read_text(encoding="utf-8")
        sbdir = (ROOT / cmd[1]).parent
        web = with_mmbiz(art, sbdir, json.loads((ROOT / cmd[1]).read_text(encoding="utf-8")).get("assets"))
        d = DIST / "t" / slug
        d.mkdir(parents=True)
        (d / "index.html").write_text(demo_page(slug, name, route, fit, web, cmd[1]), encoding="utf-8")
        jobs.append((art, t, d / "thumb.jpg", sbdir))
        cards.append((slug, name, route, fit))
        urls.append(f"/t/{slug}/")
        if slug == "isometric-journey":
            hero = art
    cases = json.loads(Path(os.environ["WXSVG_CASES"]).read_text(encoding="utf-8")) if os.environ.get("WXSVG_CASES") else []
    for c in cases:
        if c.get("status") == "soon":
            continue
        art = Path(c["article"]).expanduser().read_text(encoding="utf-8")
        d = DIST / "work" / c["slug"]
        d.mkdir(parents=True)
        for fpath in c.get("files", []):          # 作品自带的附件（比如片尾的视频），原样放进作品目录
            shutil.copy(Path(fpath).expanduser(), d / Path(fpath).name)
        (d / "index.html").write_text(case_page(c, art), encoding="utf-8")
        jobs.append((art, c.get("t", 60), d / "thumb.jpg", Path(c["article"]).expanduser().parent))
        urls.append(f"/work/{c['slug']}/")
    asyncio.run(thumbs(jobs))
    shutil.copy(DIST / "t" / "isometric-journey" / "thumb.jpg", DIST / "og.jpg")
    (DIST / "index.html").write_text(index_page(cards, hero, cases), encoding="utf-8")
    (DIST / "paste" / "index.html").write_text(paste_page(), encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    (DIST / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                      + "".join(f"<url><loc>{BASE}{u}</loc></url>" for u in urls) + "</urlset>\n")
    (DIST / "llms.txt").write_text(f"""# 小耳公众号SVG（xiaoer-wx-svg）· Xiaoer Omia 出品

> 免费开源的微信公众号 SVG 动效长图工具。交给 AI agent（Claude Code / Codex / Cursor），生成往下拉一屏屏长出来的纯 SVG 动效文章，推进公众号草稿箱或用粘贴台一键复制。

- 仓库与 Agent Skill：{REPO}（SKILL.md）
- 粘贴台（一键复制到公众号编辑器，文章不上传）：{BASE}/paste/
- 公众号 SVG 实测规矩（会被删什么、保留什么）：{REPO}/blob/main/docs/wechat-svg-rules.md
- 片子改编（把一支成片改成打开就自己往下演的长图，含 iPhone 微信真机的坑、切片、角色立体帧）：{REPO}/tree/main/film
- 模板：{", ".join(f"{n}（{BASE}/t/{s}/）" for s, n, _, _ in cards)}
- 出品方：Xiaoer Omia（{OMIA}），一个窗口打开 150 多种文件的万能阅读器。
""", encoding="utf-8")
    print(f"✅ {DIST}  {len(urls)} 页")


if __name__ == "__main__":
    main()
