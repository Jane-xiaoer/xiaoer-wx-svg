"""公众号官方 API（独立版，不依赖别的工具）：拿 token、传封面、建/改草稿、拉回草稿。"""
import json
import os
import re
import ssl
import urllib.request
from pathlib import Path

import config

API = "https://api.weixin.qq.com/cgi-bin"


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _call(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=30, context=_ctx()) as r:
        return json.loads(r.read())


def token():
    c = config.load()
    if not c.get("wx_appid") or not c.get("wx_secret"):
        raise SystemExit("还没填公众号 AppID / AppSecret：App 右上角「设置」里填")
    d = _call(f"{API}/token?grant_type=client_credential&appid={c['wx_appid']}&secret={c['wx_secret']}")
    if "access_token" in d:
        return d["access_token"]
    code = d.get("errcode")
    if code == 40164:
        ip = re.search(r"invalid ip ([\d.]+)", d.get("errmsg", ""))
        raise SystemExit(f"公网 IP {ip.group(1) if ip else '?'} 不在白名单：公众号后台 → 设置与开发 → 开发接口管理 → IP 白名单，加上它")
    if code in (40125, 40001):
        raise SystemExit("AppSecret 不对：公众号后台 → 开发接口管理 重置后，到「设置」里重新填")
    if code == 40013:
        raise SystemExit("AppID 不对，到「设置」里检查")
    raise SystemExit(f"拿 token 失败：{d}")


def _multipart(path, kind="image/jpeg"):
    bd = "----b" + os.urandom(8).hex()
    body = (f'--{bd}\r\nContent-Disposition: form-data; name="media"; filename="{Path(path).name}"\r\n'
            f"Content-Type: {kind}\r\n\r\n").encode() + Path(path).read_bytes() + f"\r\n--{bd}--\r\n".encode()
    return body, {"Content-Type": f"multipart/form-data; boundary={bd}"}


def upload_cover(tok, path):
    body, h = _multipart(path)
    d = _call(f"{API}/material/add_material?access_token={tok}&type=image", body, h)
    if "media_id" not in d:
        raise SystemExit(f"封面上传失败：{d}")
    return d["media_id"]


def upload_image(tok, path):
    """正文里用的图（截图等）→ mmbiz 链接。SVG 里用 <image href=...>，别用 xlink:href（会被删）。"""
    kind = "image/png" if str(path).lower().endswith(".png") else "image/jpeg"
    body, h = _multipart(path, kind)
    d = _call(f"{API}/media/uploadimg?access_token={tok}", body, h)
    if "url" not in d:
        raise SystemExit(f"图片上传失败：{d}")
    return d["url"].replace("http://", "https://")


def save_draft(html, title, cover, author="", digest="", update=None):
    tok = token()
    art = {"title": title, "author": author, "digest": digest, "content": html,
           "thumb_media_id": upload_cover(tok, cover), "need_open_comment": 1}
    if update:
        d = _call(f"{API}/draft/update?access_token={tok}",
                  json.dumps({"media_id": update, "index": 0, "articles": art}, ensure_ascii=False).encode())
        if d.get("errcode") == 0:
            return update
    else:
        d = _call(f"{API}/draft/add?access_token={tok}", json.dumps({"articles": [art]}, ensure_ascii=False).encode())
        if d.get("media_id"):
            return d["media_id"]
    raise SystemExit(f"草稿保存失败：{d}")


def get_draft(media_id):
    d = _call(f"{API}/draft/get?access_token={token()}", json.dumps({"media_id": media_id}).encode())
    if "news_item" not in d:
        raise SystemExit(f"拉草稿失败：{d}")
    return d["news_item"][0]["content"]


TAGS = ("svg", "animate", "animateTransform", "set", "text", "rect", "circle", "path", "image")


def check(media_id, local_html):
    """拉回草稿，比对标签数，看有没有被微信删掉的。返回 [(标签, 本地, 草稿)]。"""
    from collections import Counter
    remote = get_draft(media_id)

    def cnt(h):
        c = Counter(t.lower() for t in re.findall(r"<([a-zA-Z]+)[\s>/]", h))
        return {t: c.get(t.lower(), 0) for t in TAGS}
    lo, re_ = cnt(local_html), cnt(remote)
    return [(t, lo[t], re_[t]) for t in TAGS if lo[t]]
