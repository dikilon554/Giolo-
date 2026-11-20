#!/usr/bin/env python3
"""«Ожившее фото»: из статичной сцены делаем анимацию — объёмный параллакс по карте глубины, плавный наезд,
пылинки в луче света, мерцание света окна, субтитры с «выскакиванием».
Запуск: /home/user/gigaam-venv/bin/python scripts/animate_still.py
Результат: монтаж_2026-11-19/вставка/бессмертный_без_плашки.mp4 (исходник не трогается)."""
import os, subprocess, sys
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = f"{ROOT}/исходники/anim_source.mp4"
OUT = f"{ROOT}/монтаж_2026-11-19/вставка"; os.makedirs(OUT, exist_ok=True)
FB = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
W, H, FPS = 1080, 1920, 25
END = 6.88                                  # речь кончается на 6.76 с, смена сцены на 7.0 с
N = int(round(END * FPS))
CHUNKS = []   # без субтитров: в рилсе поверх идут свои субтитры

# ---- 1. исходный кадр (сцена неподвижна: берём кадр с 3.0 с, цвет как в плеере для HD без тега — bt709)
still_png = f"{OUT}/_still.png"
subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-ss", "3.0", "-i", SRC, "-frames:v", "1", "-vf",
                f"scale={W}:{H}:flags=lanczos:in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24", still_png], check=True)
img = np.array(Image.open(still_png).convert("RGB"))

# ---- 2. карта глубины (Depth Anything V2 Small), сглаженная, чтобы не рвало края
depth_npy = f"{OUT}/_depth.npy"
if not os.path.exists(depth_npy):
    os.environ.setdefault("HF_HOME", "/home/user/hf-cache"); os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    from transformers import pipeline
    pipe = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device=-1)
    dd = np.array(pipe(Image.fromarray(img))["depth"]).astype(np.float32)
    np.save(depth_npy, (dd - dd.min()) / (dd.max() - dd.min() + 1e-6))
d = np.load(depth_npy).astype(np.float32)
d = cv2.resize(d, (W, H), interpolation=cv2.INTER_CUBIC)
d = cv2.bilateralFilter(d, 9, 0.08, 15); d = cv2.GaussianBlur(d, (0, 0), 3.0)
D0 = 0.62                                   # глубина «неподвижной плоскости» (около персонажа)
ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)

# ---- 3. пылинки
rng = np.random.default_rng(5)
P = 56
px, py = rng.uniform(0, W, P), rng.uniform(0, H, P)
pz = rng.uniform(0.0, 1.0, P)               # «глубина» частицы
pr = rng.uniform(2.2, 6.5, P) * (0.6 + 0.8 * pz)
pa = rng.uniform(0.25, 0.65, P)
pph = rng.uniform(0, 6.28, P)
pv = rng.uniform(14, 34, P) * (0.4 + 0.9 * pz)      # скорость подъёма, px/с
sprite = {}
def get_sprite(r):
    k = int(round(r * 2)) / 2
    if k not in sprite:
        s = int(k * 5) | 1; g = np.zeros((s, s), np.float32); c = s // 2
        yy, xx = np.mgrid[0:s, 0:s]; g = np.exp(-(((xx - c) ** 2 + (yy - c) ** 2) / (2 * (k * 0.9) ** 2))).astype(np.float32)
        sprite[k] = g
    return sprite[k]

# ---- 4. субтитры: плашки как на вставке с динозаврами
SIZE, PX_, PY_ = 64, 12, 9
fnt = ImageFont.truetype(FB, SIZE); asc, desc = fnt.getmetrics(); th = asc + desc
CY = int(H * 0.91)
plates = []
for a, b, t in CHUNKS:
    tw = fnt.getlength(t); pw, ph = int(tw + 2 * PX_), int(th + 2 * PY_)
    im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, pw - 1, ph - 1], fill=(0, 0, 0, 215)); dr.text((PX_, PY_ - 1), t, font=fnt, fill=(255, 255, 255, 255))
    plates.append((a, b, np.array(im).astype(np.float32)))

def ease_io(u): return 0.5 - 0.5 * np.cos(np.pi * np.clip(u, 0, 1))
def ease_out(u): return 1 - (1 - np.clip(u, 0, 1)) ** 3

# ---- 5. кодирование: сырой RGB -> H.264 bt709, звук из исходника (с коротким затуханием)
out = f"{OUT}/бессмертный_без_плашки.mp4"
enc = subprocess.Popen([
    "ffmpeg", "-nostdin", "-y", "-v", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", SRC,
    "-filter_complex",
    "[0:v]scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd,format=yuv420p[v];"
    f"[1:a]atrim=0:{END},asetpts=PTS-STARTPTS,afade=t=out:st={END-0.10:.2f}:d=0.10[a]",
    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-profile:v", "high", "-b:v", "14M", "-maxrate", "18M", "-bufsize", "28M",
    "-preset", "medium", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{END}", out], stdin=subprocess.PIPE)

A = 14.0                                    # амплитуда параллакса, px
for k in range(N):
    t = k / FPS; u = t / END
    z = 1.0 + 0.12 * ease_io(u)                              # плавный наезд на 12 %
    dx = -A * np.cos(np.pi * u)                              # камера плывёт слева направо
    mx = (xs - W / 2) / z + W / 2 - (d - D0) * dx
    my = (ys - H / 2) / z + H / 2
    mx, my = mx.astype(np.float32), my.astype(np.float32)
    frame = cv2.remap(img, mx, my, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    # мерцание света окна (слева): мягкое, 2–3 %
    wm = np.exp(-(((xs - 250) / 330) ** 2 + ((ys - 760) / 520) ** 2))
    fl = 1.0 + (0.030 * np.sin(2 * np.pi * 0.7 * t + 1.0) + 0.016 * np.sin(2 * np.pi * 2.1 * t)) * wm
    frame *= fl[..., None]
    # пылинки (аддитивно, тёплый белый)
    for i in range(P):
        X = px[i] + 22 * np.sin(2 * np.pi * (0.12 * t) + pph[i])
        Y = (py[i] - pv[i] * t) % H
        shift = (pz[i] - D0) * dx
        x = (X + shift - W / 2) * z + W / 2; y = (Y - H / 2) * z + H / 2
        r = pr[i] * z; s = get_sprite(r); sh, sw = s.shape
        x0, y0 = int(x - sw // 2), int(y - sh // 2)
        if x0 < 0 or y0 < 0 or x0 + sw > W or y0 + sh > H: continue
        tw_ = 0.65 + 0.35 * np.sin(2 * np.pi * (0.5 * t + pph[i]))
        al = pa[i] * tw_ * min(1.0, t / 0.4)
        frame[y0:y0 + sh, x0:x0 + sw] += s[..., None] * al * np.array([255, 238, 205], np.float32)
    frame = np.clip(frame, 0, 255)
    # субтитры: выскакивают 110 % -> 100 % за 0.12 с
    for a, b, pl in plates:
        if a <= t < b:
            e = t - a
            sc = 1.0 + 0.10 * (1 - ease_out(e / 0.12)); al = min(1.0, (e + 1 / FPS) / 0.06)
            pw0, ph0 = pl.shape[1], pl.shape[0]
            pw1, ph1 = int(pw0 * sc), int(ph0 * sc)
            pr_ = cv2.resize(pl, (pw1, ph1), interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_CUBIC)
            x0, y0 = (W - pw1) // 2, CY - ph1 // 2
            alpha = (pr_[..., 3:4] / 255.0) * al
            frame[y0:y0 + ph1, x0:x0 + pw1] = frame[y0:y0 + ph1, x0:x0 + pw1] * (1 - alpha) + pr_[..., :3] * alpha
    enc.stdin.write(frame.astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait()
print("ГОТОВО", out, f"{os.path.getsize(out)/1e6:.1f} МБ, {N} кадров")
