#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""白石溪 / White Stone Spring — 品牌标识 v32（极简版）

方向（2026-10-01 Alex 批准）：
  保留：三色 #1A1A1A/#FFFFFF/#E03030、坎卦水波 ☵、红色点睛
  简化：
    1. 纯 flat —— 去掉 movable-type-edge 活字滤镜
    2. 英文换 Helvetica 大写疏排 "WHITE STONE SPRING"，I 顶红点延续灵感之火
    3. 中文版 / 英文版拆分，不再三层叠加
    4. 去印章形制 —— Xi 章改为 溪字极简几何；另附纯水波 favicon 候选
    5. 资产收敛：字标主版 / 反白版 / 小图标 / 单色版
输出到 assets/v32/，不覆盖 v31。
"""
import os
import math
from fontTools.ttLib import TTCollection
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import ControlBoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

ROOT = os.path.dirname(os.path.abspath(__file__))
CN_FONT = "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc"
CN_FACE = "Hiragino Mincho ProN W3"
EN_FONT = "/System/Library/Fonts/Helvetica.ttc"
EN_FACE = "Helvetica"

INK = "#1A1A1A"
WHITE = "#FFFFFF"
RED = "#E03030"

CN_SIZE = 56.0
CN_TRACKS = {"白": 12.0, "石": 14.0, "溪": 18.0}
EN_TEXT = "WHITE STONE SPRING"
EN_SIZE = 52.0
EN_TRACK = 12.0          # 疏排 ≈0.35em
EN_SPACE = 22.0

GAP_RATIO = 0.12
N_SAMPLES = 96


def _cn_face():
    for f in TTCollection(CN_FONT, lazy=False).fonts:
        if f["name"].getDebugName(4) == CN_FACE:
            return f
    raise SystemExit("CN face missing")


def _en_face():
    for f in TTCollection(EN_FONT, lazy=False).fonts:
        if f["name"].getDebugName(4) == EN_FACE:
            return f
    raise SystemExit("EN face missing")


def _glyph_d(face, ch, size):
    upm = face["head"].unitsPerEm
    gs = face.getGlyphSet()
    nm = face.getBestCmap().get(ord(ch))
    if nm is None:
        return None
    xf = Transform(size / upm, 0, 0, -size / upm, 0, size)
    pen = SVGPathPen(gs, ntos=lambda v: f"{v:.2f}")
    gs[nm].draw(TransformPen(pen, xf))
    return pen.getCommands(), face["hmtx"][nm][0] * size / upm


def _glyph_contours(face, ch, size):
    upm = face["head"].unitsPerEm
    gs = face.getGlyphSet()
    nm = face.getBestCmap().get(ord(ch))
    if nm is None:
        return []
    xf = Transform(size / upm, 0, 0, -size / upm, 0, size)
    rp = RecordingPen()
    gs[nm].draw(rp)
    contours, cur = [], []
    for op, args in rp.value:
        if op == "moveTo":
            if cur:
                contours.append(cur)
            cur = [("moveTo", args)]
        else:
            cur.append((op, args))
    if cur:
        contours.append(cur)
    out = []
    for ops in contours:
        pen = SVGPathPen(gs, ntos=lambda v: f"{v:.2f}")
        tp = TransformPen(pen, xf)
        for op, args in ops:
            getattr(tp, op)(*args)
        bp = ControlBoundsPen(gs)
        tp2 = TransformPen(bp, xf)
        for op, args in ops:
            getattr(tp2, op)(*args)
        out.append((pen.getCommands(), bp.bounds))
    return out


def _ink_union(ink, b):
    if b is None:
        return ink
    if ink is None:
        return b
    return (min(ink[0], b[0]), min(ink[1], b[1]),
            max(ink[2], b[2]), max(ink[3], b[3]))


def _cn_layout(face):
    items, x = [], 0.0
    ink = None
    for ch in "白石溪":
        g = _glyph_d(face, ch, CN_SIZE)
        if g is None:
            continue
        d, adv = g
        for _, bb in _glyph_contours(face, ch, CN_SIZE):
            if bb is None:
                continue
            ink = _ink_union(ink, (bb[0] + x, bb[1], bb[2] + x, bb[3]))
        items.append((d, x))
        x += adv + CN_TRACKS[ch]
    total_w = x - CN_TRACKS["溪"]
    return items, total_w, ink


def _en_caps_layout(face):
    """Helvetica 大写疏排；记录每个 I 的 stem 顶部位置用于红点。"""
    items, x = [], 0.0
    ink = None
    i_tops = []  # (cx, top_y) 局部坐标
    for ch in EN_TEXT:
        if ch == " ":
            x += EN_SPACE
            continue
        g = _glyph_d(face, ch, EN_SIZE)
        if g is None:
            continue
        d, adv = g
        top_y, top_cx = None, None
        for _, bb in _glyph_contours(face, ch, EN_SIZE):
            if bb is None:
                continue
            ink = _ink_union(ink, (bb[0] + x, bb[1], bb[2] + x, bb[3]))
            if ch == "I" and (top_y is None or bb[1] < top_y):
                top_y = bb[1]
                top_cx = x + (bb[0] + bb[2]) / 2.0
        if ch == "I" and top_y is not None:
            i_tops.append((top_cx, top_y))
        items.append((d, x))
        x += adv + EN_TRACK
    total_w = x - EN_TRACK
    return items, total_w, ink, i_tops


# ============ 坎卦 ☵ 母版（与 v31 同一套几何） ============
W_CANON = 1000.0
M = W_CANON / 24.0
PITCH = 1.618 * M
THICK_HERO = 0.50 * M
THICK_AUX = 0.20 * M
AMP_HERO = 0.30 * M
AMP_AUX = 0.38 * M


def _braun_ribbon(x0, x1, y, amp, thick, mirror=False, cycles=1.0, n=N_SAMPLES):
    top, bot = [], []
    for k in range(n + 1):
        t = k / n
        px = x0 + (x1 - x0) * t
        s = -1.0 if mirror else 1.0
        py = y + s * amp * math.sin(2.0 * math.pi * cycles * t)
        top.append((px, py - thick / 2.0))
        bot.append((px, py + thick / 2.0))
    pts = top + list(reversed(bot))
    d = [f"M {pts[0][0]:.2f} {pts[0][1]:.2f}"]
    for i in range(1, len(pts)):
        d.append(f"L {pts[i][0]:.2f} {pts[i][1]:.2f}")
    d.append("Z")
    return " ".join(d)


_half = 0.5 - GAP_RATIO / 2.0


def _kan_paths(thick_mul=1.0, amp_mul=1.0, pitch_mul=1.0):
    """坎卦 ☵：上爻断（阴）、中爻连（阳）、下爻断（阴）。
    返回 (top_l, top_r, mid, bot_l, bot_r)，上下两对断口对齐、垂直镜像。"""
    top_l = _braun_ribbon(0.0, W_CANON * _half, -PITCH * pitch_mul,
                          AMP_AUX * amp_mul, THICK_AUX * thick_mul)
    top_r = _braun_ribbon(W_CANON * (1.0 - _half), W_CANON, -PITCH * pitch_mul,
                          AMP_AUX * amp_mul, THICK_AUX * thick_mul)
    mid = _braun_ribbon(0.0, W_CANON, 0.0, AMP_HERO * amp_mul,
                        THICK_HERO * thick_mul, cycles=1.0)
    bot_l = _braun_ribbon(0.0, W_CANON * _half, PITCH * pitch_mul,
                          AMP_AUX * amp_mul, THICK_AUX * thick_mul, mirror=True)
    bot_r = _braun_ribbon(W_CANON * (1.0 - _half), W_CANON, PITCH * pitch_mul,
                          AMP_AUX * amp_mul, THICK_AUX * thick_mul, mirror=True)
    return top_l, top_r, mid, bot_l, bot_r


KAN = _kan_paths()


# 水纹纵向固定缩放（v31 视觉尺寸），横向撑满字宽 —— 三处水纹绝对一致
WAVE_SY = 0.42
def render_waves_flat(x, yin_axis_y, width, hero_c, base_c, aux_opacity=0.38,
                      kan=KAN):
    sx = width / W_CANON
    sy = WAVE_SY
    tl, tr, mid, bl, br = kan
    s = [f'<g transform="translate({x:.2f},{yin_axis_y:.2f}) scale({sx:.4f},{sy:.4f})">']
    s.append(f'  <path d="{tl}" fill="{base_c}" fill-opacity="{aux_opacity}"/>')
    s.append(f'  <path d="{tr}" fill="{base_c}" fill-opacity="{aux_opacity}"/>')
    s.append(f'  <path d="{mid}" fill="{hero_c}"/>')
    s.append(f'  <path d="{bl}" fill="{base_c}" fill-opacity="{aux_opacity}"/>')
    s.append(f'  <path d="{br}" fill="{base_c}" fill-opacity="{aux_opacity}"/>')
    s.append('</g>')
    return s


def _svg_wrap(W, H, title, label, body_lines):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.1f} {H:.1f}" '
        f'width="{W:.1f}" height="{H:.1f}" role="img" aria-label="{label}">\n'
        f'  <title>{title}</title>\n' + "\n".join(body_lines) + "\n</svg>\n")


def _palette(bg, mono=False):
    bg_fill = {"white": WHITE, "black": INK}[bg]
    if mono:
        text_c = INK if bg == "white" else WHITE
        return bg_fill, text_c, text_c, text_c
    text_c = INK if bg == "white" else WHITE
    aux_c = INK if bg == "white" else WHITE
    return bg_fill, text_c, RED, aux_c


def _wordmark(items, total_w, ink, bg, title, label, i_tops=None, mono=False):
    bg_fill, text_c, hero_c, aux_c = _palette(bg, mono)
    wave_w = total_w * 1.28
    sc = wave_w / W_CANON
    aux_h = (AMP_AUX * 0.30 + THICK_AUX / 2.0) * WAVE_SY

    pad_top = 20.0
    ink_h = ink[3] - ink[1]
    ty = pad_top - ink[1]
    baseline_y = pad_top + ink_h  # 字基线：立在红波上

    # 字立波上：红波（中爻）托住字基线，坎卦三线以红波为轴对称；
    # 波形与 logo 共用同一套标准参数（视觉识别一致性）
    red_half = (THICK_HERO * WAVE_SY) / 2.0
    yin_axis_y = baseline_y + red_half + 1.0
    kan = _kan_paths(amp_mul=0.30)
    bot_wave_bottom = yin_axis_y + PITCH * WAVE_SY + aux_h

    pad_bot = 20.0
    H = bot_wave_bottom + pad_bot
    W = wave_w + 40.0

    s = [f'<desc>White Stone Spring v32 minimal ({bg}).</desc>',
         f'<rect width="{W:.1f}" height="{H:.1f}" fill="{bg_fill}"/>']
    tx0 = (W - total_w) / 2.0
    for d, tx in items:
        s.append(f'<path d="{d}" transform="translate({tx0+tx:.1f},{ty:.1f})" fill="{text_c}"/>')
    if i_tops and not mono:
        r = EN_SIZE * 0.085
        gap = EN_SIZE * 0.12
        for cx, top_y in i_tops:
            s.append(f'<circle cx="{tx0+cx:.2f}" cy="{ty+top_y-gap-r:.2f}" r="{r:.2f}" fill="{RED}"/>')
    wave_x = (W - wave_w) / 2.0
    s.extend(render_waves_flat(wave_x, yin_axis_y, wave_w, hero_c, aux_c, kan=kan))
    return _svg_wrap(W, H, title, label, s)


def build_wordmark_cn(bg="white", mono=False):
    face = _cn_face()
    items, total_w, ink = _cn_layout(face)
    return _wordmark(items, total_w, ink, bg, "白石溪 White Stone Spring",
                     "白石溪", mono=mono)


def build_wordmark_en(bg="white"):
    face = _en_face()
    items, total_w, ink, i_tops = _en_caps_layout(face)
    return _wordmark(items, total_w, ink, bg, "White Stone Spring",
                     "White Stone Spring", i_tops=i_tops)


def _xi_layout(face, size=92.0, track=-3.0):
    """Xi 符号：Helvetica X + i。i 只画 stem，自带黑点去掉，点由红圆点单独画。
    寓意：X（大写）= 未知，i（小写）= 自我，红点 = 自我之上的灵感之火。"""
    items, x = [], 0.0
    ink = None
    i_dots = []  # (cx, cy, r) 全局局部坐标（已含 x 偏移）
    upm = face["head"].unitsPerEm
    for ch in "Xi":
        nm = face.getBestCmap().get(ord(ch))
        if nm is None:
            continue
        adv = face["hmtx"][nm][0] * size / upm
        if ch == "X":
            d, _ = _glyph_d(face, ch, size)
            for _, bb in _glyph_contours(face, ch, size):
                if bb is None:
                    continue
                ink = _ink_union(ink, (bb[0] + x, bb[1], bb[2] + x, bb[3]))
            items.append((d, x))
        else:
            # i：stem 用墨画，自带点跳过，红点单独画
            for cd, bb in _glyph_contours(face, ch, size):
                if bb is None:
                    continue
                h = bb[3] - bb[1]
                if h < size * 0.30:
                    cx = x + (bb[0] + bb[2]) / 2.0
                    cy = (bb[1] + bb[3]) / 2.0
                    r = h * 0.55
                    i_dots.append((cx, cy, r))
                    ink = _ink_union(ink, (cx - r, cy - r, cx + r, cy + r))
                else:
                    items.append((cd, x))
                    ink = _ink_union(ink, (bb[0] + x, bb[1], bb[2] + x, bb[3]))
        x += adv + track
    total_w = x - track
    return items, total_w, ink, i_dots, size


def build_logo_xi(bg="white"):
    """logo：Xi 符号立在红波上（v32 极简，无印章圈，flat）。
    水纹与字标绝对一致：同一套坎卦标准参数；Xi 基线立于红波（中爻）之上，
    下灰波断口落在字下空水面，可见。"""
    bg_fill, text_c, hero_c, aux_c = _palette(bg)
    S = 180.0
    face = _en_face()
    items, total_w, ink, i_dots, size = _xi_layout(face)
    ink_h = ink[3] - ink[1]

    wave_w = total_w * 1.30
    sc = wave_w / W_CANON
    aux_h = (AMP_AUX + THICK_AUX / 2.0) * sc

    # Xi 水平居中；基线立在红波上沿
    tx0 = (S - total_w) / 2.0
    red_half = (THICK_HERO * WAVE_SY) / 2.0
    baseline_y = S / 2.0 + ink_h * 0.18  # 视觉中心略下，留出波的空间
    ty = baseline_y - ink[3]
    yin_axis_y = baseline_y + red_half + 1.0
    kan = _kan_paths(amp_mul=0.30)

    s = [f'<desc>White Stone Spring v32 logo — Xi standing on water ({bg}).</desc>',
         f'<rect width="{S:.0f}" height="{S:.0f}" fill="{bg_fill}"/>']
    for d, tx in items:
        s.append(f'<path d="{d}" transform="translate({tx0+tx:.1f},{ty:.1f})" fill="{text_c}"/>')
    for cx, cy, r in i_dots:
        s.append(f'<circle cx="{tx0+cx:.2f}" cy="{ty+cy:.2f}" r="{r:.2f}" fill="{RED}"/>')
    wave_x = (S - wave_w) / 2.0
    s.extend(render_waves_flat(wave_x, yin_axis_y, wave_w, hero_c, aux_c, kan=kan))
    return _svg_wrap(S, S, "Xi · White Stone Spring", "Xi", s)


if __name__ == "__main__":
    out = {
        "v32_wordmark_cn_white.svg": build_wordmark_cn("white"),
        "v32_wordmark_cn_black.svg": build_wordmark_cn("black"),
        "v32_wordmark_en_white.svg": build_wordmark_en("white"),
        "v32_wordmark_en_black.svg": build_wordmark_en("black"),
        "v32_logo_xi_white.svg": build_logo_xi("white"),
        "v32_logo_xi_black.svg": build_logo_xi("black"),
        "v32_mono_black.svg": build_wordmark_cn("white", mono=True),
        "v32_mono_white.svg": build_wordmark_cn("black", mono=True),
    }
    assets = os.path.join(ROOT, "assets", "v32")
    os.makedirs(assets, exist_ok=True)
    for name, svg in out.items():
        dst = os.path.join(assets, name)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"{name} {os.path.getsize(dst)} B")
