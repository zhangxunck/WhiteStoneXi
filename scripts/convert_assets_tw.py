#!/usr/bin/env python3
"""白石溪 配图书（HTML/SVG）简->繁转换：只转标签外文本 + <text> 内容 + <style> 块。
保留属性、URL、<style> 内 CSS、代码。幂等（繁体已是则不变）。"""
import os, re, glob
from opencc import OpenCC

ROOT = os.path.dirname(os.path.abspath(__file__))
cc = OpenCC("s2tw")

def strip_tags(text):
    """转标签外文本，保留 <style> 块原样、HTML 标签原样。"""
    styles = []
    def grab(m):
        styles.append(m.group(0)); return "\x00%d\x00" % (len(styles) - 1)
    text = re.sub(r"<style>.*?</style>", grab, text, flags=re.S)
    parts = re.split(r"(<[^>]*>)", text)
    out = []
    for i, p in enumerate(parts):
        out.append(p if i % 2 == 1 else cc.convert(p))
    text = "".join(out)
    for idx, s in enumerate(styles):
        text = text.replace("\x00%d\x00" % idx, s)
    return text

changed = []
for f in glob.glob(os.path.join(ROOT, "assets/*.html")):
    raw = open(f, encoding="utf-8").read()
    new = strip_tags(raw)
    if new != raw:
        open(f, "w", encoding="utf-8").write(new)
        changed.append(os.path.basename(f))
    else:
        print("no-change", os.path.basename(f))

# SVG：只转 <text> 内容 与 <style> 块
for f in glob.glob(os.path.join(ROOT, "assets/*.svg")):
    raw = open(f, encoding="utf-8").read()
    new = re.sub(r"(<text[^>]*>)(.*?)(</text>)",
                 lambda m: m.group(1) + cc.convert(m.group(2)) + m.group(3),
                 raw, flags=re.S)
    new = re.sub(r"(<style>)(.*?)(</style>)",
                 lambda m: m.group(1) + cc.convert(m.group(2)) + m.group(3),
                 new, flags=re.S)
    if new != raw:
        open(f, "w", encoding="utf-8").write(new)
        changed.append(os.path.basename(f))
    else:
        print("no-change", os.path.basename(f))

print("converted:", *changed, sep="\n  ")
if not changed:
    print("all assets already traditional")
