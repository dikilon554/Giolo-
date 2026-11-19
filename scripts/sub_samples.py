#!/usr/bin/env python3
"""Образец 2x2: четыре стиля субтитров на одном куске ролика (кадры 197-313 из v2/stage2.mp4)."""
import os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import *

OUT = f"{ROOT}/монтаж_2026-11-19/samples"; os.makedirs(OUT, exist_ok=True)
FA, FB = f"{ROOT}/assets/fonts/Unbounded_900Black.ttf", f"{ROOT}/assets/fonts/Manrope_800ExtraBold.ttf"
FS = f"{ROOT}/assets/fonts/Manrope_600SemiBold.ttf"
W, STRIP_H = 1080, 420
RED, WHITE, BLACK = (255, 61, 46), (255, 255, 255), (0, 0, 0)
F0, F1 = 197, 313
G = load_groups()
# слова образца: «И что, если я скажу, что ты можешь делать точно так же?» + «Открываешь ChatGPT.»
ws = [dict(w) for w in G[4]]
op = G[5]
ws.append({"word": "Открываешь", "f0": op[0]["f0"], "f1": op[0]["f1"]})
ws.append({"word": "ChatGPT.", "f0": op[1]["f0"], "f1": op[2]["f1"]})
KEY = {"точно", "так", "же?", "ChatGPT."}
disp = lambda w: w["word"]
key = lambda w: w["word"].lower() in {k.lower() for k in KEY}
txt = lambda w, up=False: (w["word"].rstrip(",.") .upper() if up else w["word"].rstrip(",."))

def canvas(): return Image.new("RGBA", (W, STRIP_H), (0, 0, 0, 0))
def ease(x): return 1 - (1 - min(max(x, 0), 1)) ** 3
def paste_scaled(strip, im, sc, al=1.0):
    bb = im.getbbox()
    if not bb: return strip
    sc = min(sc, (W - 24) / (bb[2] - bb[0]))
    im2 = im if sc == 1 else im.resize((int(im.size[0] * sc), int(im.size[1] * sc)), Image.LANCZOS)
    if al < 1:
        a = np.array(im2); a[..., 3] = (a[..., 3] * al).astype(np.uint8); im2 = Image.fromarray(a)
    strip.paste(im2, ((W - im2.size[0]) // 2, (STRIP_H - im2.size[1]) // 2), im2); return strip

def draw_line(d, toks, font, y, colors, sw=0, sp=None, alpha=None):
    sp = sp or font.getlength(" ") * 1.0
    ws_ = [font.getlength(t) for t in toks]; tot = sum(ws_) + sp * (len(toks) - 1); x = (W - tot) / 2
    pos = []
    for t, w_, c in zip(toks, ws_, colors):
        d.text((x, y), t, font=font, fill=c, stroke_width=sw, stroke_fill=BLACK); pos.append((x, w_)); x += w_ + sp
    return pos

# ---------- A: крупные слова (как сейчас): 1–2 слова, Unbounded
A_GR = [(0, 2), (2, 4), (4, 5), (5, 7), (7, 9), (9, 10), (10, 12), (12, 13), (13, 14)]
def styleA(k):
    for a, b in A_GR:
        g = ws[a:b]; t0, t1 = g[0]["f0"], (ws[b]["f0"] if b < len(ws) else g[-1]["f1"])
        if t0 <= k < t1:
            toks = [txt(w, True) for w in g]
            f = ImageFont.truetype(FA, 104)
            while sum(f.getlength(t) for t in toks) + 28 * (len(toks) - 1) > 960: f = ImageFont.truetype(FA, f.size - 4)
            im = canvas(); d = ImageDraw.Draw(im)
            draw_line(d, toks, f, STRIP_H / 2 - f.size * 0.6, [RED if key(w) else WHITE for w in g], sw=9, sp=28)
            e = (k - t0) / FPS
            return paste_scaled(canvas(), im, 1 + 0.25 * (1 - ease(e / 0.13)) ** 1, min(1, (e + 0.04) / 0.06))
    return canvas()

# ---------- B: по одному слову (спокойнее, Manrope, строчные)
def styleB(k):
    for i, w in enumerate(ws):
        t0, t1 = w["f0"], (ws[i + 1]["f0"] if i + 1 < len(ws) else w["f1"])
        if t0 <= k < t1:
            f = ImageFont.truetype(FB, 112); t = txt(w)
            im = canvas(); d = ImageDraw.Draw(im)
            tw = f.getlength(t); d.text(((W - tw) / 2, STRIP_H / 2 - 70), t, font=f, fill=RED if key(w) else WHITE, stroke_width=7, stroke_fill=BLACK)
            e = (k - t0) / FPS
            return paste_scaled(canvas(), im, 1 + 0.16 * (1 - ease(e / 0.1)), min(1, (e + 0.04) / 0.05))
    return canvas()

# ---------- C / D: фраза целиком, подсветка текущего слова
PH = [(0, 5), (5, 9), (9, 12), (12, 14)]       # куски по смыслу
def phrase(k, mode):
    for a, b in PH:
        g = ws[a:b]; t0 = g[0]["f0"]; t1 = ws[b]["f0"] if b < len(ws) else g[-1]["f1"]
        if not (t0 <= k < t1): continue
        size = 72 if mode == "C" else 66
        f = ImageFont.truetype(FB if mode == "C" else FS, size)
        toks = [txt(w) for w in g]; sp = size * 0.3
        lines, line = [], []
        for t in toks:
            tl = sum(f.getlength(x) for x in line) + sp * len(line) + f.getlength(t)
            if line and tl > 900: lines.append(line); line = []
            line.append(t)
        lines.append(line)
        cur = max([i for i, w in enumerate(g) if w["f0"] <= k] or [0])
        im = canvas(); d = ImageDraw.Draw(im)
        lh = int(size * 1.45); y = STRIP_H / 2 - lh * len(lines) / 2 + (size * 0.1 if mode == "C" else 40); n = 0
        for ln in lines:
            tw = sum(f.getlength(t) for t in ln) + sp * (len(ln) - 1); x = (W - tw) / 2
            for t in ln:
                w_ = f.getlength(t)
                active, spoken = n == cur, n < cur
                if mode == "C":
                    if active:
                        d.rounded_rectangle([x - 16, y - 4, x + w_ + 16, y + size * 1.18], 18, fill=RED + (255,))
                    col = (255, 255, 255, 255) if (active or spoken) else (255, 255, 255, 140)
                    d.text((x, y), t, font=f, fill=col, stroke_width=3, stroke_fill=(0, 0, 0, 200 if (active or spoken) else 110))
                else:
                    col = RED + (255,) if active else ((255, 255, 255, 255) if spoken else (255, 255, 255, 170))
                    d.text((x, y), t, font=f, fill=col)
                x += w_ + sp; n += 1
            y += lh
        e = (k - t0) / FPS
        al = min(1, (e + 0.04) / 0.1)
        if al < 1:
            a_ = np.array(im); a_[..., 3] = (a_[..., 3] * al).astype(np.uint8); im = Image.fromarray(a_)
        return im
    return canvas()

STY = {"A": (styleA, 1250), "B": (styleB, 1250), "C": (lambda k: phrase(k, "C"), 1400), "D": (lambda k: phrase(k, "D"), 1500)}
for nm, (fn, cy) in STY.items():
    dd = f"{OUT}/{nm}"; os.makedirs(dd, exist_ok=True)
    for k in range(F0, F1):
        fn(k).save(f"{dd}/s_{k - F0:04d}.png")
GH = 740
g = np.zeros((GH, W, 4), np.uint8); g[..., 3] = (185 * (np.linspace(0, 1, GH) ** 1.6)).astype(np.uint8)[:, None]
Image.fromarray(g).save(f"{OUT}/grad.png")
print("полосы готовы")
lab = {"A": "A  крупные слова (сейчас)", "B": "B  по одному слову", "C": "C  караоке-фраза", "D": "D  минимализм"}
inp, fc = [], []
for i, nm in enumerate("ABCD"):
    cy = STY[nm][1]
    inp += ["-i", f"{ROOT}/монтаж_2026-11-19/v2/stage2.mp4", "-framerate", "25", "-i", f"{OUT}/{nm}/s_%04d.png"]
    fc.append(f"[{2*i}:v]trim=start_frame={F0}:end_frame={F1},setpts=PTS-STARTPTS[b{i}]")
    fc.append(f"[{2*i+1}:v]format=rgba,scale=out_color_matrix=bt709:out_range=tv,format=yuva420p[s{i}]")
    if nm == "D":
        inp += ["-i", f"{OUT}/grad.png"]
        fc.append("[8:v]format=rgba,scale=out_color_matrix=bt709:out_range=tv,format=yuva420p[g]")
        fc.append(f"[b{i}][g]overlay=0:{1920 - GH}:shortest=0[b{i}g]")
        base = f"b{i}g"
    else:
        base = f"b{i}"
    fc.append(f"[{base}][s{i}]overlay=0:{cy - STRIP_H // 2}:shortest=1,scale=540:960,"
              f"drawtext=fontfile={FB}:text='{lab[nm]}':x=14:y=14:fontsize=30:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=8[v{i}]")
fc.append("[v0][v1][v2][v3]xstack=inputs=4:layout=0_0|540_0|0_960|540_960[out]")
subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", *inp, "-filter_complex", ";".join(fc), "-map", "[out]", "-r", "25",
                "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-pix_fmt", "yuv420p", f"{OUT}/стили_субтитров_2x2.mp4"], check=True)
print("ГОТОВО", f"{OUT}/стили_субтитров_2x2.mp4")
