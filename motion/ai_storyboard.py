#!/usr/bin/env python3
"""让任意模型写分镜：题材 + 资料 → 分镜 JSON（渲染试跑不过就把报错丢回去重写，最多 2 次）。

  python3 motion/ai_storyboard.py --topic "你的产品名" --facts 资料.md -o 分镜.json
  --model deepseek（默认）| local（本机 MLX 网关 qwen3.6:35b）| 任意 OpenAI 兼容：--base-url --api-key --model-name
  --theme ember   不填让模型自己挑
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PROVIDERS = {
    "deepseek": {"base": "https://api.deepseek.com", "key_env": "DEEPSEEK_API_KEY", "model": "deepseek-chat"},
    "local": {"base": "http://127.0.0.1:11434/v1", "key_env": None, "model": "qwen3.6:35b"},
}


def ssl_ctx():
    """本机 python.org 版 Python 没装根证书，用 certifi 的。"""
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def chat(base, key, model, messages):
    body = {"model": model, "messages": messages, "temperature": 0.7}
    if "deepseek" in base:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          **({"Authorization": f"Bearer {key}"} if key else {})})
    with urllib.request.urlopen(req, timeout=300, context=ssl_ctx() if base.startswith("https") else None) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def parse_json(s):
    s = re.sub(r"^```(?:json)?|```$", "", s.strip(), flags=re.M).strip()
    s = re.sub(r"<think>.*?</think>", "", s, flags=re.S).strip()
    i, j = s.find("{"), s.rfind("}")
    return json.loads(s[i:j + 1])


def lint(sb):
    """渲染能过但写得不好的地方，丢回给模型改。"""
    sc = sb.get("scenes", [])
    types = [s.get("type") for s in sc]
    errs = []
    for i in range(1, len(types)):
        if types[i] == types[i - 1]:
            errs.append(f"第 {i} 和第 {i + 1} 屏都是 {types[i]}，相邻两屏不要用同一种场景")
    for t in set(types):
        if types.count(t) > 2:
            errs.append(f"{t} 用了 {types.count(t)} 次，同一种场景最多 2 次")
    if len(sc) > 8:
        errs.append(f"写了 {len(sc)} 屏，最多 8 屏")
    for i, s in enumerate(sc, 1):
        if s.get("type") == "live" and not all(isinstance(x, list) and len(x) >= 2 and isinstance(x[0], int) for x in s.get("lines", [])):
            errs.append(f"第 {i} 屏 live 的 lines 要写成 [[说话人序号, 这句话], ...]")
        if s.get("type") == "window" and not s.get("window", {}).get("sidebar"):
            errs.append(f"第 {i} 屏 window 没有 sidebar；题材没有软件界面就别用 window")
    return "；".join(errs) or None


def try_build(sb):
    import make
    bad = lint(sb)
    if bad:
        return bad
    try:
        make.build(sb)
        return None
    except SystemExit as e:
        return str(e)
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}"


def write(topic, facts, theme, base, key, model, log=print):
    guide = (HERE / "STORYBOARD.md").read_text(encoding="utf-8")
    user = f"题材：{topic}\n" + (f"主题请用：{theme}\n" if theme else "") + f"\n资料（只能用这里的事实）：\n{facts}\n\n请输出分镜 JSON。"
    msgs = [{"role": "system", "content": guide}, {"role": "user", "content": user}]
    for attempt in range(4):
        log(f"  → {model} 写分镜（第 {attempt + 1} 次）…")
        raw = chat(base, key, model, msgs)
        try:
            sb = parse_json(raw)
            err = try_build(sb)
        except json.JSONDecodeError as e:
            sb, err = None, f"不是合法 JSON：{e}"
        if not err:
            if theme:
                sb["theme"] = theme
            return sb
        log(f"  ⚠️ {err}，让它改")
        msgs += [{"role": "assistant", "content": raw},
                 {"role": "user", "content": f"渲染报错：{err}\n请修正后重新输出完整 JSON。"}]
    raise SystemExit(f"模型 3 次都没写对，最后的错：{err}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True)
    ap.add_argument("--facts", help="资料文件（md/txt）；不填就只用题材")
    ap.add_argument("--theme")
    ap.add_argument("--model", default="deepseek", help="deepseek / local")
    ap.add_argument("--base-url")
    ap.add_argument("--api-key")
    ap.add_argument("--model-name")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    base, key, model = provider(a.model, a.base_url, a.api_key, a.model_name)
    facts = Path(a.facts).read_text(encoding="utf-8") if a.facts else ""
    sb = write(a.topic, facts, a.theme, base, key, model)
    Path(a.out).write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 分镜 → {a.out}（{len(sb['scenes'])} 屏，主题 {sb.get('theme')}）")



CHECK = """你是事实核查员。下面是一份资料和一份根据资料写的分镜 JSON。
找出分镜里**资料没有支持**的说法：编出来的数字、价格、功能、网址、夸大的表述。
演示用的示例文件名、示例表格内容不算问题。
只输出 JSON：{"issues": ["第几屏 · 哪个字段 · 原文 · 为什么不对", ...]}，没问题就输出 {"issues": []}。"""


def fact_check(sb, facts, base, key, model):
    if not facts.strip():
        return ["没给资料，无法核查：分镜里的事实全靠模型自己说，发之前务必人工看一遍"]
    raw = chat(base, key, model, [{"role": "system", "content": CHECK},
                                  {"role": "user", "content": f"资料：\n{facts}\n\n分镜：\n{json.dumps(sb, ensure_ascii=False)}"}])
    try:
        return list(parse_json(raw).get("issues", []))
    except (json.JSONDecodeError, AttributeError):
        return ["核查结果解析失败，请人工看一遍"]


def provider(name="deepseek", base_url=None, api_key=None, model_name=None):
    """返回 (base, key, model)。key 从 motion/config.py 读（谁用填谁的）。"""
    import config
    p = PROVIDERS.get(name, {})
    base = base_url or p.get("base")
    if not base:
        raise SystemExit(f"不认识的模型 {name}")
    key = api_key or (config.load().get("deepseek_api_key") if p.get("key_env") else None)
    if p.get("key_env") and not key:
        raise SystemExit("还没填 DeepSeek key：App 右上角「设置」里填（platform.deepseek.com 申请）")
    return base, key, model_name or p.get("model")


if __name__ == "__main__":
    main()
