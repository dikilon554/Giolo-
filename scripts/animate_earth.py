#!/usr/bin/env python3
"""«Земля остановилась»: оживляем статичную картинку Земли и привязываем анимацию к озвучке.
0–1.9 с шар вращается, 1.9–2.7 тормозит («остановилась»), ударная волна + тряска, 3.0–4.0 кольцо-таймер на 1 секунду,
спокойная часть с падающей звездой, с 6.6 с вращение возобновляется.
Запуск: /home/user/gigaam-venv/bin/python scripts/animate_earth.py
Результат: монтаж_2026-11-19/вставка/земля_анимация.mp4 (исходник не трогается)."""
import os, subprocess
import cv2, numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = f"{ROOT}/исходники/earth_source.mp4"
OUT = f"{ROOT}/монтаж_2026-11-19/вставка"; os.makedirs(OUT, exist_ok=True)
W, H, FPS = 1080, 1920, 25
DUR = 7.04
N = int(round(DUR * FPS))

# ---------------------------------------------------------------- 1. кадр и шар
still = f"{OUT}/_earth_still.png"
subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-ss", "1.0", "-i", SRC, "-frames:v", "1", "-vf",
                f"scale={W}:{H}:flags=lanczos:in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24", still], check=True)
img = np.array(Image.open(still).convert("RGB")).astype(np.float32)
g = img.mean(2).astype(np.uint8)
m = cv2.morphologyEx((g > 70).astype(np.uint8) * 255, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
(cx, cy), R0 = cv2.minEnclosingCircle(max(cs, key=cv2.contourArea))
R = R0 * 0.965
print(f"шар: центр ({cx:.0f},{cy:.0f}), радиус {R:.0f}")

# рабочий прямоугольник вокруг шара
pad = 8
x1, x2 = max(0, int(cx - R - pad)), min(W, int(cx + R + pad))
y1, y2 = max(0, int(cy - R - pad)), min(H, int(cy + R + pad))
ys, xs = np.mgrid[y1:y2, x1:x2].astype(np.float32)
nx, ny = (xs - cx) / R, (ys - cy) / R
r2 = nx ** 2 + ny ** 2; inside = r2 < 1.0
nz = np.sqrt(np.clip(1 - r2, 0, 1))
Pn = np.stack([nx, ny, nz], -1)
# освещение (гладкая яркость) и «альбедо»
Lum = img.mean(2); mk = np.zeros((H, W), np.float32); mk[y1:y2, x1:x2] = inside
Sh_full = cv2.GaussianBlur(Lum * mk, (0, 0), R * 0.20) / np.maximum(cv2.GaussianBlur(mk, (0, 0), R * 0.20), 1e-3)
alb = img / np.maximum(Sh_full, 12)[..., None]
albB = cv2.GaussianBlur(alb, (0, 0), R * 0.035)                 # для размытия растянутого края
Sh = Sh_full[y1:y2, x1:x2]
edge = (np.clip((1 - np.sqrt(r2)) * R / 10, 0, 1) * inside)[..., None]
ALPHA = 12.0                                                    # наклон оси


def rotm(theta_deg):
    a, t = np.deg2rad(ALPHA), np.deg2rad(theta_deg)
    k = np.array([np.sin(a), -np.cos(a), 0.0])
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * (K @ K)


def smooth(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)
def ease_out(x): return 1 - (1 - np.clip(x, 0, 1)) ** 3


def sphere(theta):
    P = Pn @ rotm(theta).T
    px, py = P[..., 0], P[..., 1]; rr = np.sqrt(px ** 2 + py ** 2)
    s = np.where(rr > 0.985, 0.985 / np.maximum(rr, 1e-6), 1.0)
    mx, my = (px * s * R + cx).astype(np.float32), (py * s * R + cy).astype(np.float32)
    A1 = cv2.remap(alb, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    A2 = cv2.remap(albB, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    w = smooth((rr - 0.88) / 0.10)[..., None]                   # у края — размытая текстура (меньше «полос»)
    return (A1 * (1 - w) + A2 * w) * Sh[..., None]


# ---------------------------------------------------------------- 2. расписание вращения (по словам озвучки)
T_STOP0, T_STOP1 = 1.9, 2.7       # «остановилась»
T_TIMER0, T_TIMER1 = 3.0, 4.0     # «всего на одну секунду»
T_RESTART0, T_RESTART1 = 6.6, 7.04
ts = np.arange(N + 1) / FPS
v = np.zeros_like(ts)
for i, t in enumerate(ts):
    if t < T_STOP0: v[i] = 9.0
    elif t < T_STOP1: v[i] = 9.0 * (1 - (t - T_STOP0) / (T_STOP1 - T_STOP0)) ** 2
    elif t < T_RESTART0: v[i] = 0.0
    else: v[i] = 6.0 * smooth((t - T_RESTART0) / (T_RESTART1 - T_RESTART0))
theta_arr = np.cumsum(v) / FPS
print(f"поворот за ролик: {theta_arr[N]:.1f}°")
gate = np.where(ts < 2.0, 1.0, np.where(ts < 2.7, 1 - (ts - 2.0) / 0.7, np.where(ts < 6.6, 0.0, np.clip((ts - 6.6) / 0.3, 0, 1))))
phi_arr = np.cumsum(gate) / FPS                                  # «фаза мерцания»: на остановке звёзды замирают

# ---------------------------------------------------------------- 3. звёзды, кольца, падающая звезда
rng = np.random.default_rng(21)
NS = 240
sx, sy = rng.uniform(0, W, NS), rng.uniform(0, H, NS)
sr = rng.uniform(0.7, 1.7, NS); sb = rng.uniform(0.35, 1.0, NS)
sf = rng.uniform(1.5, 4.5, NS); sp = rng.uniform(0, 6.28, NS); spar = rng.uniform(0.2, 1.0, NS)
sprites = {}
def spr(r):
    k = round(r * 4) / 4
    if k not in sprites:
        s = int(k * 6) | 1; c = s // 2; yy, xx = np.mgrid[0:s, 0:s]
        sprites[k] = np.exp(-(((xx - c) ** 2 + (yy - c) ** 2) / (2 * (k * 0.75) ** 2))).astype(np.float32)
    return sprites[k]

YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
RHO = np.sqrt((XX - cx) ** 2 + (YY - cy) ** 2) / R0               # расстояние от центра в радиусах шара
ANG = (np.arctan2(YY - cy, XX - cx) + np.pi / 2) % (2 * np.pi)    # 0 = сверху, по часовой
outside = smooth((RHO - 1.0) / 0.03)                             # звёзды только вне планеты


def ring(rho0, width, color, gain):
    return (np.exp(-((RHO - rho0) / width) ** 2) * gain)[..., None] * np.array(color, np.float32)


def shooting(t):
    """падающая звезда 4.7–5.35 с: сверху справа налево вниз, мимо планеты"""
    u = (t - 4.7) / 0.65
    if not (0 <= u <= 1): return None
    p0, p1 = np.array([1040.0, 120.0]), np.array([470.0, 360.0]); d = (p1 - p0) / np.linalg.norm(p1 - p0)
    head = p0 + (p1 - p0) * ease_out(u * 0.9 + 0.1 * u)
    life = np.sin(np.pi * u) ** 0.8
    lay = np.zeros((H, W, 3), np.float32)
    for j in range(34):
        pos = head - d * j * 7.0; a = life * (1 - j / 34) ** 1.6; r = 3.2 * (1 - j / 45)
        x0, y0 = int(pos[0]), int(pos[1]); s = spr(max(r, 0.8)); sh, sw = s.shape
        xa, ya = x0 - sw // 2, y0 - sh // 2
        if xa < 0 or ya < 0 or xa + sw > W or ya + sh > H: continue
        lay[ya:ya + sh, xa:xa + sw] += s[..., None] * a * np.array([235, 245, 255], np.float32)
    return lay


# ---------------------------------------------------------------- 4. кодирование
out = f"{OUT}/земля_анимация.mp4"
enc = subprocess.Popen([
    "ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", SRC, "-filter_complex",
    "[0:v]scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd,format=yuv420p[v]",
    "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-profile:v", "high", "-b:v", "14M", "-maxrate", "18M", "-bufsize", "28M",
    "-preset", "medium", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
    "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{DUR}", out], stdin=subprocess.PIPE)

for k in range(N):
    t = k / FPS
    frame = img.copy()
    # шар (вращение)
    sph = sphere(theta_arr[k])
    reg = frame[y1:y2, x1:x2]
    frame[y1:y2, x1:x2] = reg * (1 - edge) + sph * edge
    # звёзды (мерцают, на остановке замирают; дрейф против вращения)
    st = np.zeros((H, W, 3), np.float32)
    for i in range(NS):
        X = (sx[i] - spar[i] * 2.6 * theta_arr[k]) % W; Y = sy[i]
        tw = 0.55 + 0.45 * np.sin(sp[i] + sf[i] * phi_arr[k] * 2.0)
        s = spr(sr[i]); sh, sw = s.shape; xa, ya = int(X) - sw // 2, int(Y) - sh // 2
        if xa < 0 or ya < 0 or xa + sw > W or ya + sh > H: continue
        st[ya:ya + sh, xa:xa + sw] += s[..., None] * sb[i] * tw * np.array([225, 235, 255], np.float32)
    frame += st * outside[..., None] * 0.9
    # дыхание атмосферы + вспышка на остановке
    breathe = 0.10 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.45 * t)) if (T_STOP1 < t < T_RESTART0) else 0.04
    flash = 0.9 * np.exp(-(t - T_STOP1) / 0.16) if t >= T_STOP1 else 0.0
    frame += ring(1.0, 0.05, (255, 205, 150), (breathe + flash) * (0.6 + 0.4 * (RHO > 1.0)))
    # ударная волна на остановке
    if t >= T_STOP1:
        for dly, amp in ((0.0, 0.95), (0.14, 0.45)):
            u = (t - T_STOP1 - dly) / 0.85
            if 0 <= u <= 1:
                frame += ring(1.0 + 1.5 * ease_out(u), 0.018 + 0.03 * u, (215, 235, 255), amp * (1 - u) ** 1.6)
    # кольцо-таймер на 1 секунду (3.0–4.0 с)
    tick_a = smooth((t - 2.85) / 0.2) * (1 - smooth((t - 4.2) / 0.25))
    if tick_a > 0:
        p = np.clip((t - T_TIMER0) / (T_TIMER1 - T_TIMER0), 0, 1)
        arc = (ANG <= p * 2 * np.pi).astype(np.float32)
        gain = 1.0 + 2.2 * np.exp(-max(t - T_TIMER1, 0) / 0.10) * (t >= T_TIMER1)
        base_ring = np.exp(-((RHO - 1.12) / 0.0085) ** 2)
        glow = np.exp(-((RHO - 1.12) / 0.03) ** 2) * 0.35
        frame += ((base_ring * arc * 0.95 + glow * arc * 0.7 + base_ring * 0.10) * gain * tick_a)[..., None] * np.array([185, 225, 255], np.float32)
        tick = ((np.abs(((ANG / (2 * np.pi)) * 60 + 0.5) % 1.0 - 0.5) < 0.05) & (RHO > 1.155) & (RHO < 1.19)).astype(np.float32)
        frame += (tick * 0.45 * tick_a)[..., None] * np.array([200, 230, 255], np.float32)
    # падающая звезда
    sh_ = shooting(t)
    if sh_ is not None: frame += sh_
    # общий кадр: наезд 1.0 -> 1.07 к центру шара + тряска в момент остановки
    z = 1.0 + 0.07 * smooth(t / DUR)
    te = t - T_STOP1
    sx_ = sy_ = 0.0
    if 0 <= te < 0.45:
        dec = np.exp(-te * 11); sx_ = 11 * dec * np.sin(2 * np.pi * 21 * te); sy_ = 8 * dec * np.sin(2 * np.pi * 17 * te + 1.0)
    M = np.float32([[z, 0, (1 - z) * cx + sx_], [0, z, (1 - z) * cy + sy_]])
    frame = np.clip(frame, 0, 255)
    frame = cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    if 0 <= te < 0.12: frame = frame * (1 + 0.10 * np.exp(-te / 0.05))
    enc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait()
print("ГОТОВО", out, f"{os.path.getsize(out)/1e6:.1f} МБ, {N} кадров")
