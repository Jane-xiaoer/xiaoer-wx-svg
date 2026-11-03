"""配置：公众号 AppID/Secret、DeepSeek key。谁用就填谁的。

读取顺序（先找到先用）：
  1. 环境变量 WX_APPID / WX_SECRET / DEEPSEEK_API_KEY
  2. ~/.config/wx-svg-motion/config.json（python3 motion/config.py --set 写的就是这里，权限 600）
不填也能用：生成的文章走粘贴台 https://svg.xiaoeromia.com/paste/ 一键复制，手动粘进公众号。
"""
import json
import os
from pathlib import Path

CONF = Path.home() / ".config/wx-svg-motion/config.json"
KEYS = ("wx_appid", "wx_secret", "deepseek_api_key")


def load():
    cfg = {}
    if CONF.exists():
        cfg.update({k: v for k, v in json.loads(CONF.read_text(encoding="utf-8")).items() if v})
    for k in KEYS:
        if os.environ.get(k.upper()):
            cfg[k] = os.environ[k.upper()]
    return cfg


def save(new):
    cur = json.loads(CONF.read_text(encoding="utf-8")) if CONF.exists() else {}
    cur.update({k: v.strip() for k, v in new.items() if k in KEYS and v and v.strip()})
    CONF.parent.mkdir(parents=True, exist_ok=True)
    CONF.write_text(json.dumps(cur, indent=2), encoding="utf-8")
    os.chmod(CONF, 0o600)


def status():
    """给设置页看：哪些填了（只露后 4 位）。"""
    c = load()
    return {k: (("…" + c[k][-4:]) if c.get(k) else "") for k in KEYS}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="保存公众号配置到本机（只存在你自己电脑上）")
    ap.add_argument("--set", nargs=2, action="append", metavar=("KEY", "VALUE"),
                    help="wx_appid / wx_secret / deepseek_api_key")
    a = ap.parse_args()
    if a.set:
        save(dict(a.set))
    print(json.dumps(status(), ensure_ascii=False, indent=1))
