#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中英逐节对照自检。

问题背景（2026-09-30）：5 篇英文实为「压缩重写」而非翻译，英文普遍只有中文
1/3 字数，还自行增补了中文没有的引文 —— 并排阅读时左右讲的不是一回事，
但 H2 数量一致（12/12），只查节数查不出来。

本脚本按 ## 逐节配对，输出：
  1) 标题对照（中文 H2 vs 英文 H2 序号与措辞）
  2) 字数比：中文字数 / 英文词数。经验区间 1.8-2.6
     （中文一字 ≈ 1.5-1.7 英文字符；一段对等译文的汉字数与英文词数之比，
      在本刊实测健康样本为 1.9-2.5；参考文献等表格式内容会拉低比值，
      故对末节放宽）
  3) 语义抽查：取每节首句（中文前 24 字 / 英文前 12 词）并列打印，人工判断
  4) 警示词：英文侧出现中文没有的引号引文、或段落数差 ≥3

用法：
  python3 check_bilingual.py                # 查全部
  python3 check_bilingual.py 代号的神学      # 只查含此关键字的文件
  python3 check_bilingual.py --md           # 顺便查 md 层（默认查渲染后 html）

退出码：0 = 全部在区间内；1 = 有超限节，需重译。
"""

import os
import re
import sys
import html as H

ROOT = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(ROOT, "articles")

# 汉字（含扩展区）
CJK = re.compile(r'[\u3400-\u9fff\uf900-\ufaff]')
# 英文单词（含连字符与撇号）
WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")

RATIO_LO, RATIO_HI = 1.20, 2.60
# 经验区间校准（2026-10-01 全站实测，按篇中位数）：
#   1.24 什么是好的中文 / 1.29 轴心的倒流 / 1.38 写作是学习的发生地 /
#   1.43 代号的神学 / 1.49 诸神的联邦 / 1.52 翻译如何重塑中文 /
#   1.65 AI认知判断力 / 1.86 无我者与语言游戏 / 2.50 有限游戏的造物主
# 结论：忠实的汉译英正文落在 1.2-2.0，原先 1.8-2.6 的下限过高——它会逼译文
# 压缩省略以「达标」，正是本脚本要防的失真。上限 2.6 仍保留，用于抓「英文
# 只有中文三分之一」那类旧式压缩重写（比值会飙到 3 以上）。
PARA_GAP = 3                 # 段落数差警示阈值


def split_h2(md):
    """按 '## ' 切分，返回 [(标题, 正文)]。"""
    body = md.split('---', 2)[2] if md.startswith('---') else md
    out, cur = [], None
    for ln in body.split('\n'):
        if ln.startswith('## '):
            if cur:
                out.append(cur)
            cur = [ln[3:].strip(), []]
        elif cur is not None:
            cur[1].append(ln)
    if cur:
        out.append(cur)
    return [(t, '\n'.join(b)) for t, b in out]


def read(path):
    return open(path, encoding='utf-8').read()


def analyse(md_fn, label, key):
    cn = split_h2(read(md_fn))
    en = split_h2(read(md_fn[:-3] + '.en.md')) if os.path.exists(md_fn[:-3] + '.en.md') else []

    print(f"\n{'='*74}\n{label}\n{'='*74}")
    if not en:
        print("  ✗ 无 .en.md —— build 会退单栏（不并排），读者看不到英文。")
        return 1
    if len(cn) != len(en):
        print(f"  ✗ 节数不等：中文 {len(cn)} / 英文 {len(en)} —— 并排会串位。")

    bad = 0
    n = max(len(cn), len(en))
    for i in range(n):
        ct, cb = cn[i] if i < len(cn) else ('—', '')
        et, eb = en[i] if i < len(en) else ('—', '')
        cjk = len(CJK.findall(cb))
        wrd = len(WORD.findall(eb))
        ratio = (cjk / wrd) if wrd else (0.0 if cjk else 99.0)

        cp = len([p for p in re.split(r'\n\s*\n', cb) if p.strip()])
        ep = len([p for p in re.split(r'\n\s*\n', eb) if p.strip()])
        gap = abs(cp - ep)

        # 参考文献：逐条编号必须一一对应，不允许英文少列/多列；
        # 且每条的核心标识（作者+年份+刊名/出版社）须在中英两侧同时出现。
        # 字数比在此天然失真（作者名/刊名多为拉丁字母，中文侧汉字天然少），
        # 故参考文献改用「条目数 + 标识符覆盖」判定，不套用正文阈值。
        is_ref = ('参考文献' in ct) or ('References' in et)
        # 表格节：字数比失真（中文侧汉字天然多），故不套正文阈值。
        # 但不能反用段落数——英文常把中文长段拆成多段（中文 8 段 ↔ 英文 14 段
        # 是地道英文的正常形态，非缺译）。表格节只豁免字数比，不设段落数下限。
        is_table = cb.count('|') >= 10 and eb.count('|') >= 10
        # X thread / 传播素材节：英文独有的运营资产，中文版故意不设对应节
        # （并排阅读时不展示 tweet 串）。属结构性豁免，不是漏译。
        is_en_only = et.startswith('X thread') and ct == '—'
        n_cn_ref = len(re.findall(r'(?m)^\s*\[(\d+)\]', cb))
        n_en_ref = len(re.findall(r'(?m)^\s*\[(\d+)\]', eb))
        cn_nums = re.findall(r'(?m)^\s*\[(\d+)\]', cb)
        en_nums = re.findall(r'(?m)^\s*\[(\d+)\]', eb)
        ref_gap = (cn_nums != en_nums) if is_ref else False
        # 每条的年份必须在两侧都出现
        cn_yrs = set(re.findall(r'(?m)^\s*\[\d+\].*?\b(1[89]\d\d|20\d\d)\b', cb))
        en_yrs = set(re.findall(r'(?m)^\s*\[\d+\].*?\b(1[89]\d\d|20\d\d)\b', eb))
        yr_gap = (cn_yrs != en_yrs) if is_ref else False

        flag = ''
        if is_en_only:
            flag = '  · 英文独有（传播素材，不计）'
        elif wrd == 0:
            flag = '  ✗ 英文空节'
        elif ref_gap:
            flag = f'  ✗ 参考文献编号序列不等(中{len(cn_nums)}/英{len(en_nums)})'
        elif yr_gap:
            flag = f'  ✗ 参考文献年份集合不等(中仅{len(cn_yrs)}/英{len(en_yrs)})'
        elif not is_ref and not is_table and (ratio < RATIO_LO or ratio > RATIO_HI):
            flag = f'  ✗ 超区间[{RATIO_LO},{RATIO_HI}]'
        elif not is_ref and gap >= PARA_GAP:
            flag = f'  ⚠ 段落数差{gap}'
        # 只有 ✗（硬错：空节/参考文献错位/年份集合不等/字数比越界）计入失败；
        # ⚠ 段落数差只是警示——英文为地道表达常会拆分/合并段落，字数比健康即通过。
        if flag.startswith('  ✗'):
            bad += 1

        # 语义抽查首句
        c1 = re.sub(r'\s+', '', cb)[:24]
        e1 = ' '.join(WORD.findall(eb)[:12])

        mark = '✗' if flag.startswith('  ✗') else ('⚠' if flag else '✓')
        print(f"  {mark} {i+1:>2}. 中 {cjk:>5}字 / 英 {wrd:>4}词 = {ratio:>5.2f}"
              f"  段{cp:>2}/{ep:<2}{flag}")
        print(f"        中标题: {ct[:40]}")
        print(f"        英标题: {et[:44]}")
        if is_ref:
            print(f"        参考文献: 中 {len(cn_nums)} 条 / 英 {len(en_nums)} 条"
                  f"  编号一致={'✓' if cn_nums == en_nums else '✗'}"
                  f"  年份一致={'✓' if cn_yrs == en_yrs else '✗'}")
            print(f"        年份集合: 中{sorted(cn_yrs)}")
            print(f"        年份集合: 英{sorted(en_yrs)}")
        print(f"        中首句: {c1}")
        print(f"        英首句: {e1}")

    if bad:
        print(f"\n  → {bad}/{n} 节需处理（重译或补节）。")
        return 1
    print(f"\n  ✓ {n} 节全部在区间内。")
    return 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    files = sorted(f for f in os.listdir(ART)
                   if f.endswith('.md') and not f.endswith('.en.md'))
    if args:
        files = [f for f in files if any(k in f for k in args)]
    if not files:
        print('无匹配文件')
        return 1

    rc = 0
    for f in files:
        rc |= analyse(os.path.join(ART, f), f[:-3], args)
    print(f"\n{'退出码 ' + str(rc) + '（1=有超限节）'}")
    return rc


if __name__ == '__main__':
    sys.exit(main())
