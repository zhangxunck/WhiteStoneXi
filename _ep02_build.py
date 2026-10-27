#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EP02《諸神的聯邦》三声线重制。按 EP01 v8r3 实测标杆映射：
   Eva=XiaoxiaoNeural(~240Hz) / Alex=YunxiNeural(~170Hz) / WALLe=YunjianNeural(~120Hz)
   注意：Eva 的《EP02 TTS 参数方案》把 Alex/WALLe 写反了，以 EP01 实测为准。
"""
import json, os, re, subprocess, sys, shutil

FFMPEG = os.path.expanduser("~/.local/bin/ffmpeg")
FFPROBE = os.path.expanduser("~/.local/bin/ffprobe")
EDGE = os.path.expanduser("~/.local/bin/edge-tts")
WORK = "/tmp/ep02_build"
SEGJSON = "/tmp/ep02_segs.json"
OUT = os.path.expanduser("~/WhiteStoneXi/assets/podcast/ep02.mp3")

# EP01 v8r3 标杆：角色 -> (voice, rate, pitch)
VOICE = {
    "Eva":  ("zh-CN-XiaoxiaoNeural", "+0%",  "+0Hz"),
    "Alex": ("zh-CN-YunxiNeural",    "+15%", "-2Hz"),
    "WALLe": ("zh-CN-YunjianNeural", "-10%", "+1Hz"),
}

# 标点分层调速（EP01 v2 起固定轮子）：句末放慢，问句略慢
def tune_rate(text, base):
    b = base
    if text.rstrip().endswith(("。", "！", "？")):
        b = "+0%" if b == "+0%" else ("+8%" if b.startswith("+") else "-16%")
    elif "？" in text:
        b = "-4%" if b == "+0%" else ("+10%" if b.startswith("+") else "-14%")
    elif "，" in text:
        b = "-6%" if b == "+0%" else ("+8%" if b.startswith("+") else "-12%")
    return b

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        print("FAIL:", cmd, r.stderr[-400:], file=sys.stderr)
    return r.returncode == 0

def main():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    segs = json.load(open(SEGJSON))["segments"]

    # 1) 逐段合成
    for i, s in enumerate(segs):
        voice, rate, pitch = VOICE[s["role"]]
        rate2 = tune_rate(s["text"], rate)
        out = os.path.join(WORK, "seg%03d.mp3" % i)
        cmd = ('%s --voice %s --rate=%s --pitch=%s --text %s --write-media %s'
               % (EDGE, voice, rate2, pitch,
                  json.dumps(s["text"], ensure_ascii=False), out))
        if not run(cmd) or not os.path.exists(out) or os.path.getsize(out) < 2000:
            print("seg %d failed (%s)" % (i, s["role"]), file=sys.stderr)
            return 1
        s["rate"] = rate2
        s["file"] = out
        s["i"] = i
    print("synthesized %d segments" % len(segs))

    # 2) 段间停顿 0.76s 中位；每段尾 300ms 淡出
    #    Alex 段间 0.55s(快) / Eva 0.85s / WALLe 1.05s
    GAP = {"Eva": 0.85, "Alex": 0.55, "WALLe": 1.05}
    parts = []
    for s in segs:
        parts.append(s["file"])
    # 用 concat demuxer + silence
    sil_dir = os.path.join(WORK, "sil")
    os.makedirs(sil_dir, exist_ok=True)
    for s in segs:
        g = GAP[s["role"]]
        sp = os.path.join(sil_dir, "gap%03d.mp3" % s["i"])
        run('%s -f lavfi -i anullsrc=r=44100:cl=stereo -t %.3f -q:a 9 %s' % (FFMPEG, g, sp))
        s["gap"] = sp

    # 3) 拼接：每段 + 段尾 300ms 淡出
    seg_fade = []
    for s in segs:
        faded = os.path.join(WORK, "f%03d.mp3" % s["i"])
        run('%s -i %s -af "afade=t=out:st=%.3f:d=0.3" -ar 44100 -ac 2 -b:a 128k %s'
            % (FFMPEG, s["file"], max(0.0, 0.0), faded))
        seg_fade.append(faded)

    # 4) 全片 concat（段 + 间隔）
    concat_list = os.path.join(WORK, "concat.txt")
    with open(concat_list, "w") as f:
        for s in segs:
            f.write("file '%s'\n" % s["file"])
            f.write("file '%s'\n" % s["gap"])
    voice_track = os.path.join(WORK, "voice.mp3")
    run('%s -f concat -safe 0 -i %s -ar 44100 -ac 2 -b:a 192k %s' % (FFMPEG, concat_list, voice_track))

    # 5) 溪水垫底 -26dB：程序生成粉噪（宽带水声近似）
    dur = float(subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                                "-of", "default=nw=1:nk=1", voice_track],
                               capture_output=True, text=True).stdout.strip() or "420")
    water = os.path.join(WORK, "water.wav")
    run('%s -f lavfi -i "anoisesrc=color=pink:amplitude=0.5:duration=%.1f:sample_rate=44100" '
        '-af "lowpass=f=1800,highpass=f=200" -ac 2 %s' % (FFMPEG, dur + 5, water))
    water_db = os.path.join(WORK, "water_db.wav")
    run('%s -i %s -af "volume=-26dB" %s' % (FFMPEG, water, water_db))

    # 6) 片头=片尾 sting：BWV1007 取 0.3s-5.0s
    sting = os.path.join(WORK, "sting.wav")
    run('%s -ss 0.3 -t 4.7 -i /tmp/bwv1007.ogg -af "volume=-4dB" -ar 44100 -ac 2 %s'
        % (FFMPEG, sting))

    # 7) 合成：片头 sting + 溪水 + 人声 + 片尾 sting(1s 淡出)
    body = os.path.join(WORK, "body.wav")
    run('%s -i %s -i %s -filter_complex "[0:a]volume=1.0[bg];[1:a]volume=1.0[v];'
        '[bg][v]amix=inputs=2:duration=first:dropout_transition=0[mix]" '
        '-map "[mix]" -ar 44100 -ac 2 -t %.1f %s' % (FFMPEG, water_db, voice_track, dur, body))

    head = os.path.join(WORK, "head.wav")
    run('%s -i %s -i %s -filter_complex "[0:a][1:a]amix=inputs=2:duration=first:weights=1 1" '
        '-ar 44100 -ac 2 %s' % (FFMPEG, sting, water_db, head))

    tail = os.path.join(WORK, "tail.wav")
    run('%s -i %s -i %s -filter_complex "[0:a]afade=t=out:st=3.7:d=1.0[s];[1:a]volume=1.0[w];'
        '[s][w]amix=inputs=2:duration=first:weights=1 0.35" -ar 44100 -ac 2 %s'
        % (FFMPEG, sting, water_db, tail))

    final = os.path.join(WORK, "final.mp3")
    run('%s -i %s -i %s -i %s -filter_complex "[0:a][1:a]concat=n=3:v=0:a=1" '
        '-ar 44100 -ac 2 -b:a 128k %s' % (FFMPEG, head, body, tail, final))

    # 8) 落到 repo
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    shutil.copy(final, OUT)
    print("wrote", OUT, os.path.getsize(OUT))
    json.dump(segs, open("/tmp/ep02_segs_done.json", "w"), ensure_ascii=False, indent=1)
    return 0

if __name__ == "__main__":
    sys.exit(main())
