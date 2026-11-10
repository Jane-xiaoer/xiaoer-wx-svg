"""公众号官方接口：传图、传视频、存草稿、核对草稿。只用标准库。

准备（一次性）：
1. 公众号后台 → 设置与开发 → 基本配置：拿到 AppID、AppSecret；把你这台机器的出口 IP 加进「IP 白名单」
   （不知道出口 IP：curl ifconfig.me。报 40164 就是 IP 不在白名单，错误信息里会写出它看到的 IP）。
2. 设环境变量：export WX_APPID=wx... WX_SECRET=...
3. 如果你上网要走代理，而代理的出口 IP 才是白名单里的那个：export WX_PROXY=http://127.0.0.1:7890
   （只让这个脚本走代理，不受系统里别的代理变量影响）。

只存草稿，不发布。发布请自己在公众号后台点。
"""
import json, os, re, ssl, time, urllib.request
from pathlib import Path

API = "https://api.weixin.qq.com/cgi-bin"


def _open(req, timeout=120):
    px = os.environ.get("WX_PROXY")
    handlers = [urllib.request.ProxyHandler({"http": px, "https": px} if px else {}), urllib.request.HTTPSHandler(context=ssl.create_default_context())]
    for i in range(3):                        # 偶尔会 SSL EOF，等几秒重试
        try:
            with urllib.request.build_opener(*handlers).open(req, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == 2:
                raise
            time.sleep(5)


def _post(url, obj):
    # ensure_ascii=False 很重要：否则中文会变成 \uXXXX 存进草稿
    return _open(urllib.request.Request(url, data=json.dumps(obj, ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "application/json"}))


def token():
    a, s = os.environ.get("WX_APPID"), os.environ.get("WX_SECRET")
    if not a or not s:
        raise SystemExit("先设环境变量 WX_APPID 和 WX_SECRET")
    d = _open(urllib.request.Request(f"{API}/token?grant_type=client_credential&appid={a}&secret={s}"))
    if "access_token" not in d:
        raise SystemExit(f"拿 token 失败：{d}（40164 = 这台机器的出口 IP 不在公众号白名单里）")
    return d["access_token"]


def _multipart(field, path, ctype, extra=None):
    bd = "----b" + os.urandom(8).hex()
    body = (f'--{bd}\r\nContent-Disposition: form-data; name="{field}"; filename="{Path(path).name}"\r\nContent-Type: {ctype}\r\n\r\n').encode() + Path(path).read_bytes() + b"\r\n"
    for k, v in (extra or {}).items():
        body += f'--{bd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    return body + f"--{bd}--\r\n".encode(), {"Content-Type": f"multipart/form-data; boundary={bd}"}


def _ctype(path):
    return "image/png" if str(path).lower().endswith(".png") else "image/jpeg"


def upload_image(tok, path):
    """正文里用的图：传到图床，返回 https://mmbiz.qpic.cn/... 地址。单张 ≤ 1MB，只收 jpg / png。"""
    body, hd = _multipart("media", path, _ctype(path))
    d = _open(urllib.request.Request(f"{API}/media/uploadimg?access_token={tok}", data=body, headers=hd))
    if "url" not in d:
        raise SystemExit(f"传图失败 {path}: {d}")
    return d["url"].replace("http://", "https://")


def upload_cover(tok, path):
    """封面：传成永久素材，返回 media_id（存草稿时的 thumb_media_id）。建议 900×383。"""
    body, hd = _multipart("media", path, _ctype(path))
    d = _open(urllib.request.Request(f"{API}/material/add_material?access_token={tok}&type=image", data=body, headers=hd))
    if "media_id" not in d:
        raise SystemExit(f"传封面失败: {d}")
    return d["media_id"]


def upload_video(tok, path, title, intro=""):
    """视频传成永久素材，等转码完返回 (media_id, vid)。正文里用 video_iframe(vid, 封面地址) 嵌进去。"""
    body, hd = _multipart("media", path, "video/mp4", {"description": json.dumps({"title": title, "introduction": intro}, ensure_ascii=False)})
    d = _open(urllib.request.Request(f"{API}/material/add_material?access_token={tok}&type=video", data=body, headers=hd), timeout=600)
    if "media_id" not in d:
        raise SystemExit(f"传视频失败: {d}")
    for _ in range(30):                       # 转码要一会儿，vid 出来才能嵌
        info = _post(f"{API}/material/get_material?access_token={tok}", {"media_id": d["media_id"]})
        m = info.get("vid") or (re.search(r"apiv_\d+|wxv_\d+", json.dumps(info)) or [None])[0]
        if m:
            return d["media_id"], m
        time.sleep(6)
    raise SystemExit("视频转码一直没好，过几分钟再跑一次")


def video_iframe(vid, cover_url, ratio=16 / 9, w=1280):
    from urllib.parse import quote
    return (f'<iframe class="video_iframe rich_pages wx_video_iframe" data-vidtype="2" data-mpvid="{vid}" data-cover="{quote(cover_url, safe="")}" '
            f'data-ratio="{ratio}" data-w="{w}" data-src="https://mp.weixin.qq.com/mp/readtemplate?t=pages/video_player_tmpl&amp;action=mpvideo&amp;auto=0&amp;vid={vid}"></iframe>')


def localize(article, assets_root, cache_path, tok):
    """把正文里所有 href="assets/…" 换成图床地址。
    - 按「文件名 + 修改时间」缓存到 cache_path，没变的图不重传。
    - 同一张图在正文里出现多次时，每一处后面加不同的 ?v=n：iPhone 微信里同一个地址在一张 SVG 里出现多次，
      有的请求永远不结束，那张 SVG 的动画就不启动。图床会忽略多余的参数，返回的还是同一张图。"""
    cache_p = Path(cache_path)
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    for n in sorted(set(re.findall(r'href="(assets/[^"]+\.(?:jpe?g|png))"', article))):
        p = Path(assets_root) / n[len("assets/"):]
        key = f"{n}:{p.stat().st_mtime_ns}"
        if key not in cache:
            cache[key] = upload_image(tok, p)
            cache_p.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
            print("  上传", n, flush=True)
        article = article.replace(f'href="{n}"', f'href="{cache[key]}"')
    seen = {}

    def uniq(m):
        u = m.group(1); seen[u] = seen.get(u, 0) + 1
        return f'href="{u}&amp;v={seen[u]}"' if "?" in u else f'href="{u}?v={seen[u]}"'
    return re.sub(r'href="(https://mmbiz\.qpic\.cn/[^"]+)"', uniq, article)


def save_draft(tok, article, title, cover_path, author="", digest="", update=None):
    """存草稿。update = 已有草稿的 media_id 时是覆盖更新，否则新建。返回 media_id。
    常见报错：45002 = 正文太大（实测约 640KB 以内能过）；45166 之类 = 正文里有不允许的内容。"""
    art = {"title": title, "author": author, "digest": digest, "content": article,
           "thumb_media_id": upload_cover(tok, cover_path), "need_open_comment": 0, "only_fans_can_comment": 0}
    if update:
        d = _post(f"{API}/draft/update?access_token={tok}", {"media_id": update, "index": 0, "articles": art})
        if d.get("errcode"):
            raise SystemExit(f"更新草稿失败: {d}")
        return update
    d = _post(f"{API}/draft/add?access_token={tok}", {"articles": [art]})
    if "media_id" not in d:
        raise SystemExit(f"新建草稿失败: {d}")
    return d["media_id"]


TAGS = ["svg", "animate", "animateTransform", "set", "rect", "circle", "path", "image"]


def check(tok, media_id, local_article):
    """把草稿取回来，数一遍各种标签，和本地对比。公众号会悄悄删掉它不认的东西；数量一致才说明没被删。
    注意：取回来的属性名全是小写（attributename），所以按标签名数、不分大小写。"""
    d = _post(f"{API}/draft/get?access_token={tok}", {"media_id": media_id})
    remote = d["news_item"][0]["content"]
    rows = []
    for t in TAGS:
        lo = len(re.findall(rf"<{t}[\s>/]", local_article, re.I)); re_ = len(re.findall(rf"<{t}[\s>/]", remote, re.I))
        rows.append((t, lo, re_))
        print(f"  {t:<17} 本地 {lo:5d}  草稿 {re_:5d}{'' if lo == re_ else '  ⚠️ 被删了'}")
    return rows
