"""配色主题。所有场景只读这里的色值，换主题 = 换一整套颜色。

字段：
  bg 底色 · panel 面板 · deep 更深的面（影子/代码块/终端）· line 分隔线和柱子底
  accent 主强调色 · accent_dim 强调色压暗一档（亮底主题用来写字）· on_accent 强调色块上的字
  text 主文字 · grey 次要文字 · grid 网格透明度
  win_dark / win_light 产品窗口的暗/亮两套皮肤（换肤场景从 light 换到 dark）
  swatches 换肤场景里展示的 7 个色点
"""

_SWATCH = ["#4d88ff", "#7BC043", "#2ec4c4", "#9b7bff", "#ff9f43", "#ff5a5f", "#9aa0a6"]


def _win(bg, panel, deep, text, sub, line, edge):
    return {"bg": bg, "panel": panel, "deep": deep, "text": text, "sub": sub, "line": line, "edge": edge}


THEMES = {
    # Omia 那篇：石墨 + 品牌绿
    "graphite-green": {
        "bg": "#232629", "panel": "#2b2e33", "deep": "#1a1c1f", "line": "#3a3e45",
        "accent": "#7BC043", "accent_dim": "#5f9a30", "on_accent": "#1a1c1f",
        "text": "#e9ecef", "grey": "#8d949c", "grid": 0.04,
        "win_dark": _win("#2b2e33", "#31353b", "#25282c", "#e6e9ed", "#8d949c", "#3d424a", "#3a3f46"),
        "win_light": _win("#E0E5EC", "#e7ebf1", "#d3d9e2", "#2b2e33", "#6b7480", "#c9d0da", "#f4f7fb"),
        "swatches": _SWATCH,
    },
    # 炭黑 + 余烬橙：暖、热烈
    "ember": {
        "bg": "#1f1a17", "panel": "#2a231f", "deep": "#15110f", "line": "#3d332d",
        "accent": "#ff7a3d", "accent_dim": "#d95f24", "on_accent": "#1f1a17",
        "text": "#f3ece6", "grey": "#a3958a", "grid": 0.05,
        "win_dark": _win("#2a231f", "#322a25", "#211b18", "#f3ece6", "#a3958a", "#463a33", "#40352f"),
        "win_light": _win("#efe6dd", "#f5ede5", "#e2d6ca", "#2a231f", "#7a6b60", "#dccdbf", "#fbf6f1"),
        "swatches": ["#ff7a3d", "#ffb347", "#ff5a5f", "#e8c07d", "#c97b63", "#9b7bff", "#a3958a"],
    },
    # 暖纸 + 朱红：亮底，克制、像印刷品
    "paper-red": {
        "bg": "#f3efe6", "panel": "#fbf8f2", "deep": "#e4ddd0", "line": "#ddd5c6",
        "accent": "#d9452b", "accent_dim": "#b8361f", "on_accent": "#fbf8f2", "light": True,
        "text": "#2a2622", "grey": "#857c71", "grid": 0.06,
        "win_dark": _win("#2b2724", "#34302c", "#221f1c", "#f1ece5", "#9c9388", "#46403a", "#3e3833"),
        "win_light": _win("#fbf8f2", "#f3eee5", "#e8e1d4", "#2a2622", "#857c71", "#e0d8ca", "#ffffff"),
        "swatches": ["#d9452b", "#e8a33d", "#3f7d5a", "#2f5d8a", "#7a4e9c", "#c2577a", "#857c71"],
    },
    # 墨黑 + 金：高级、发布会感
    "ink-gold": {
        "bg": "#121212", "panel": "#1c1c1c", "deep": "#0a0a0a", "line": "#2e2b25",
        "accent": "#d4af37", "accent_dim": "#a8892a", "on_accent": "#121212",
        "text": "#f2efe8", "grey": "#9a9488", "grid": 0.05,
        "win_dark": _win("#1c1c1c", "#232220", "#151514", "#f2efe8", "#9a9488", "#34312b", "#2f2c27"),
        "win_light": _win("#ece7dc", "#f4f0e8", "#ddd6c8", "#1c1c1c", "#6f685c", "#d6cfc0", "#faf7f1"),
        "swatches": ["#d4af37", "#e8d48b", "#b87333", "#c0c0c0", "#8c6d46", "#f2efe8", "#9a9488"],
    },
    # 鼠尾草绿 + 珊瑚粉：小耳录音卡少女风的暗色版，温柔但有亮点
    "sage-coral": {
        "bg": "#1b211e", "panel": "#242c27", "deep": "#141917", "line": "#34403a",
        "accent": "#ff8a7a", "accent_dim": "#e86b5b", "accent2": "#a8c3a0", "on_accent": "#1b211e",
        "text": "#f1f0ea", "grey": "#94a39a", "grid": 0.05,
        "win_dark": _win("#242c27", "#2b342f", "#1e2521", "#f1f0ea", "#94a39a", "#3a4740", "#34403a"),
        "win_light": _win("#eef1ea", "#f6f7f2", "#e1e7dc", "#242c27", "#6f7d74", "#d5ddd0", "#ffffff"),
        "swatches": ["#ff8a7a", "#a8c3a0", "#f7c59f", "#9fc5c9", "#c9a7d8", "#f2e394", "#94a39a"],
    },
    # 夜紫：科技、梦幻
    "violet-night": {
        "bg": "#17142a", "panel": "#211d38", "deep": "#0f0d1d", "line": "#332e52",
        "accent": "#a78bfa", "accent_dim": "#8b6cf0", "on_accent": "#17142a",
        "text": "#ece9fb", "grey": "#9690b8", "grid": 0.05,
        "win_dark": _win("#211d38", "#282342", "#1a1730", "#ece9fb", "#9690b8", "#3a3460", "#353057"),
        "win_light": _win("#e6e3f5", "#eeebfa", "#d9d4ee", "#211d38", "#6c668e", "#cfc9e8", "#f7f6fd"),
        "swatches": ["#a78bfa", "#f472b6", "#22d3ee", "#facc15", "#34d399", "#fb7185", "#9690b8"],
    },
}


def get(name):
    if name not in THEMES:
        raise SystemExit(f"没有主题「{name}」，可选：{' / '.join(THEMES)}")
    return THEMES[name]
