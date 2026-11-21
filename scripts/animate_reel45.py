#!/usr/bin/env python3
"""«Что если Земля остановится на секунду» (45 с, 3 картинки): оживляем слайд-шоу под голос диктора.
Сцены и стыки как в исходнике: Земля 0–22.96, человек на улице 22.52–40.64, улица с урной 40.20–конец (наплывы 0.44 с).
Земля: вращение из одной картинки (≈23°, от −12° до +11°), торможение на «остановилась», кольцо-таймер на «одну секунду»,
наезд на «представь», поток звёзд на «1670 км/ч», жёсткая остановка на «резко» (ударная волна, тряска, вспышка), падающие звёзды.
Человек: параллакс слоями (фон / дерево / человек, маски GrabCut), качание листвы, толчок камеры на «понесёт», дрожь и пыль
на «небоскрёбы…руины…сметут», затишье на «атмосферой», порыв ветра с листьями на «воздух».
Улица: урна раскачивается и подпрыгивает, бумажки трепещут, листья и пыль летят к горизонту, удар на «уничтожать».
Все добавленные цвета сняты с исходника (kmeans). Карты глубины нет (HF закрыт) — слои вместо неё.
Запуск: python scripts/animate_reel45.py SRC.mp4 OUT.mp4 [--preview 3.4,13,30,42 PREVIEW_DIR]"""
import os, subprocess, sys
import cv2, numpy as np

SRC, OUT = sys.argv[1], sys.argv[2]
PREVIEW = None
if "--preview" in sys.argv:
    i = sys.argv.index("--preview"); PREVIEW = [float(x) for x in sys.argv[i + 1].split(",")]; PDIR = sys.argv[i + 2]
    os.makedirs(PDIR, exist_ok=True)
W, H, FPS = 1080, 1920, 25
DUR = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", SRC],
                           capture_output=True, text=True).stdout)
N = int(DUR * FPS)
AB0, AB1, BC0, BC1 = 22.52, 22.96, 40.20, 40.64          # наплывы исходника (замер разницы кадров)
rng = np.random.default_rng(7)
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)


def still(t):
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", str(t), "-i", SRC, "-frames:v", "1", "-vf",
                        f"scale={W}:{H}:flags=lanczos:in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24",
                        "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(r, np.uint8).reshape(H, W, 3).copy()


def smooth(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)
def ease_out(x): return 1 - (1 - np.clip(x, 0, 1)) ** 3
def ease_io(x): return 0.5 - 0.5 * np.cos(np.pi * np.clip(x, 0, 1))


def palette(pix, k):
    _, lab, c = cv2.kmeans(pix.reshape(-1, 3).astype(np.float32), k, None, (3, 20, 1.0), 3, cv2.KMEANS_PP_CENTERS)
    cnt = np.bincount(lab.ravel(), minlength=k); return c[np.argsort(-cnt)]


def grabcut(img, rect, it=6):
    m = np.zeros((H, W), np.uint8); b = np.zeros((1, 65)); f = np.zeros((1, 65))
    cv2.grabCut(cv2.cvtColor(img, cv2.COLOR_RGB2BGR), m, rect, b, f, it, cv2.GC_INIT_WITH_RECT)
    return np.where((m == 1) | (m == 3), 255, 0).astype(np.uint8)


def biggest(m):
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    return ((lab == 1 + np.argmax(st[1:, 4])) * 255).astype(np.uint8) if n > 1 else m


SPR = {}
def blob(r, soft):
    """мягкий/плоский кружок: soft=0.75 — свечение (фотореализм), soft=0.25 — плоская точка (мультяшный стиль)"""
    key = (round(r * 4) / 4, soft)
    if key not in SPR:
        k = key[0]; s = int(k * 6) | 1; c = s // 2; yy, xx = np.mgrid[0:s, 0:s]
        d = np.sqrt((xx - c) ** 2 + (yy - c) ** 2) / max(k, 0.5)
        SPR[key] = (np.exp(-(d ** 2) / (2 * 0.75 ** 2)) if soft > 0.5 else np.clip((1.05 - d) / soft, 0, 1)).astype(np.float32)
    return SPR[key]


def stamp(lay, x, y, s, col, a):
    sh, sw = s.shape; xa, ya = int(x) - sw // 2, int(y) - sh // 2
    if xa < 0 or ya < 0 or xa + sw > W or ya + sh > H: return
    lay[ya:ya + sh, xa:xa + sw] = lay[ya:ya + sh, xa:xa + sw] * (1 - s[..., None] * a) + s[..., None] * a * col


def affine(frame, z, cx, cy, dx=0.0, dy=0.0):
    M = np.float32([[z, 0, (1 - z) * cx + dx], [0, z, (1 - z) * cy + dy]])
    return cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def shake(t, hits, amp, decay=9.0, fx=21, fy=17):
    sx = sy = 0.0
    for th in hits:
        te = t - th
        if 0 <= te < 0.6:
            d = np.exp(-te * decay); sx += amp * d * np.sin(2 * np.pi * fx * te); sy += amp * 0.75 * d * np.sin(2 * np.pi * fy * te + 1)
    return sx, sy


# ======================================================================= A. ЗЕМЛЯ
imgA = still(10.0).astype(np.float32)
g = imgA.mean(2).astype(np.uint8)
m = cv2.morphologyEx((g > 70).astype(np.uint8) * 255, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
(cx, cy), R0 = cv2.minEnclosingCircle(max(cs, key=cv2.contourArea)); R = R0 * 0.965
print(f"шар: ({cx:.0f},{cy:.0f}) R={R:.0f}")
pad = 8
x1, x2, y1, y2 = max(0, int(cx - R - pad)), min(W, int(cx + R + pad)), max(0, int(cy - R - pad)), min(H, int(cy + R + pad))
ys, xs = np.mgrid[y1:y2, x1:x2].astype(np.float32)
nx, ny = (xs - cx) / R, (ys - cy) / R; r2 = nx ** 2 + ny ** 2; inside = r2 < 1
Pn = np.stack([nx, ny, np.sqrt(np.clip(1 - r2, 0, 1))], -1)
Lum = imgA.mean(2); mk = np.zeros((H, W), np.float32); mk[y1:y2, x1:x2] = inside
Sh_full = cv2.GaussianBlur(Lum * mk, (0, 0), R * 0.2) / np.maximum(cv2.GaussianBlur(mk, (0, 0), R * 0.2), 1e-3)
alb = imgA / np.maximum(Sh_full, 12)[..., None]; albB = cv2.GaussianBlur(alb, (0, 0), R * 0.035)
Sh = Sh_full[y1:y2, x1:x2]; edge = (np.clip((1 - np.sqrt(r2)) * R / 10, 0, 1) * inside)[..., None]


def rotm(th, a=12.0):
    a, t = np.deg2rad(a), np.deg2rad(th); k = np.array([np.sin(a), -np.cos(a), 0.0])
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * (K @ K)


def sphere(th):
    P = Pn @ rotm(th).T; px, py = P[..., 0], P[..., 1]; rr = np.sqrt(px ** 2 + py ** 2)
    s = np.where(rr > 0.985, 0.985 / np.maximum(rr, 1e-6), 1.0)
    mx, my = (px * s * R + cx).astype(np.float32), (py * s * R + cy).astype(np.float32)
    A1 = cv2.remap(alb, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    A2 = cv2.remap(albB, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    w = smooth((rr - 0.88) / 0.10)[..., None]
    return (A1 * (1 - w) + A2 * w) * Sh[..., None]


# расписание по словам: «остановилась» 1.96, «секунду» 3.52, «представь» 8.52, «со скоростью» 12.48, «резко» 16.77
T_S1, T_S1e, T_HIT = 1.96, 2.76, 17.17
ts = np.arange(N + 2) / FPS
v = np.zeros_like(ts); sp = np.zeros_like(ts)              # v — °/с шара, sp — px/с потока звёзд
for i, t in enumerate(ts):
    if t < T_S1: v[i], sp[i] = 5.0, 14
    elif t < T_S1e: u = (t - T_S1) / 0.8; v[i], sp[i] = 5.0 * (1 - u) ** 2, 14 * (1 - u) ** 2
    elif t < 4.5: v[i] = sp[i] = 0
    elif t < 10.7: e = smooth((t - 4.5) / 0.8); v[i], sp[i] = 0.9 * e, 5 * e
    elif t < 16.77: e = smooth((t - 10.7) / 1.8); v[i], sp[i] = 0.9 + 0.45 * e, 5 + 55 * e
    elif t < T_HIT: u = (t - 16.77) / 0.4; v[i], sp[i] = 1.35 * (1 - u) ** 2, 60 * (1 - u) ** 2
    else: v[i] = sp[i] = 0
theta = np.cumsum(v) / FPS; theta -= theta[-1] / 2 + 0.5   # симметрично вокруг исходного ракурса
drift = np.cumsum(sp) / FPS
gateA = np.clip(sp / 14, 0, 1) * 0.6 + 0.4
phiA = np.cumsum(gateA) / FPS
print(f"поворот шара: {theta[0]:.1f}° → {theta[-1]:.1f}°")

bgA = palette(imgA[(Lum < 60)], 6)                        # цвета фона — для звёзд берём самый светлый из космоса
NS = 260
ssx, ssy = rng.uniform(0, W, NS), rng.uniform(0, H, NS)
ssr = rng.uniform(0.7, 1.6, NS); ssb = rng.uniform(0.25, 0.75, NS); ssf = rng.uniform(1.5, 4.5, NS)
ssp = rng.uniform(0, 6.28, NS); spar = rng.uniform(0.25, 1.0, NS)
RHO = np.sqrt((XX - cx) ** 2 + (YY - cy) ** 2) / R0
ANG = (np.arctan2(YY - cy, XX - cx) + np.pi / 2) % (2 * np.pi)
outside = smooth((RHO - 1.0) / 0.03)
_gm = (RHO > 0.89) & (RHO < 0.95) & (imgA[..., 0] > imgA[..., 2] + 15) & (Lum > 100)   # тёплый ореол у края шара
GLOW = np.median(imgA[_gm], 0).astype(np.float32)          # цвет свечения атмосферы с исходника
STAR = np.array([225, 232, 250], np.float32)
print("свечение атмосферы:", GLOW.astype(int))


def ring(rho0, width, color, gain):
    return (np.exp(-((RHO - rho0) / width) ** 2) * gain)[..., None] * np.asarray(color, np.float32)


SHOOT = [(18.1, (1040, 160), (430, 420)), (19.35, (1060, 1500), (560, 1760)), (20.6, (980, 70), (520, 260))]


def shooting(lay, t):
    for t0, p0, p1 in SHOOT:
        u = (t - t0) / 0.65
        if not (0 <= u <= 1): continue
        p0, p1 = np.array(p0, float), np.array(p1, float); d = (p1 - p0) / np.linalg.norm(p1 - p0)
        head = p0 + (p1 - p0) * ease_out(u); life = np.sin(np.pi * u) ** 0.8
        for j in range(34):
            pos = head - d * j * 7.0; a = life * (1 - j / 34) ** 1.6
            s = blob(max(3.2 * (1 - j / 45), 0.8), 1); sh, sw = s.shape; xa, ya = int(pos[0]) - sw // 2, int(pos[1]) - sh // 2
            if 0 <= xa and 0 <= ya and xa + sw <= W and ya + sh <= H:
                lay[ya:ya + sh, xa:xa + sw] += s[..., None] * a * STAR


def zoomA(t):
    z = 1.0 + 0.04 * smooth(t / 8.4)
    z += 0.09 * ease_io((t - 8.44) / 1.9)
    z += 0.012 * smooth((t - 10.4) / 6.8)
    z -= 0.075 * ease_io((t - 17.8) / 5.0)
    return z


def frameA(k):
    t = k / FPS; f = imgA.copy()
    f[y1:y2, x1:x2] = f[y1:y2, x1:x2] * (1 - edge) + sphere(theta[k]) * edge
    st = np.zeros((H, W, 3), np.float32)
    for i in range(NS):
        X = (ssx[i] - spar[i] * drift[k]) % W
        tw = 0.55 + 0.45 * np.sin(ssp[i] + ssf[i] * phiA[k] * 2)
        s = blob(ssr[i], 1); sh, sw = s.shape; xa, ya = int(X) - sw // 2, int(ssy[i]) - sh // 2
        if 0 <= xa and 0 <= ya and xa + sw <= W and ya + sh <= H:
            st[ya:ya + sh, xa:xa + sw] += s[..., None] * ssb[i] * tw * STAR
    # на потоке звёзд — лёгкий «смаз» вдоль движения (как у длинной выдержки)
    if sp[k] > 20:
        L = int(1 + sp[k] / 12); ker = np.zeros((1, 2 * L + 1), np.float32); ker[0, L:] = 1 / (L + 1)
        st = cv2.filter2D(st, -1, ker) * (1 + L * 0.35)
    f += st * outside[..., None] * 0.9
    breathe = 0.05 + 0.05 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.45 * t)) * (T_S1e < t < 4.5)
    flash = 0.35 * np.exp(-(t - T_S1e) / 0.16) * (t >= T_S1e) + 0.9 * np.exp(-(t - T_HIT) / 0.16) * (t >= T_HIT)
    f += ring(1.0, 0.05, GLOW, (breathe + flash) * (0.6 + 0.4 * (RHO > 1.0)))
    for dly, amp in ((0.0, 0.95), (0.14, 0.45)):            # ударная волна на «резко … остановится»
        u = (t - T_HIT - dly) / 0.85
        if 0 <= u <= 1: f += ring(1.0 + 1.5 * ease_out(u), 0.018 + 0.03 * u, GLOW * 0.5 + STAR * 0.5, amp * (1 - u) ** 1.6)
    ta = smooth((t - 2.85) / 0.2) * (1 - smooth((t - 4.2) / 0.25))   # кольцо-таймер «всего на одну секунду»
    if ta > 0:
        p = np.clip((t - 3.0) / 1.0, 0, 1); arc = (ANG <= p * 2 * np.pi).astype(np.float32)
        gain = 1.0 + 2.2 * np.exp(-max(t - 4.0, 0) / 0.10) * (t >= 4.0)
        base = np.exp(-((RHO - 1.12) / 0.0085) ** 2); glow = np.exp(-((RHO - 1.12) / 0.03) ** 2) * 0.35
        col = GLOW * 0.35 + STAR * 0.65
        f += ((base * arc * 0.95 + glow * arc * 0.7 + base * 0.10) * gain * ta)[..., None] * col
        tick = ((np.abs(((ANG / (2 * np.pi)) * 60 + 0.5) % 1 - 0.5) < 0.05) & (RHO > 1.155) & (RHO < 1.19)).astype(np.float32)
        f += (tick * 0.45 * ta)[..., None] * col
    shooting(f, t)
    sx, sy = shake(t, [T_HIT], 11, 11)
    f = affine(np.clip(f, 0, 255), zoomA(t), cx, cy, sx, sy)
    te = t - T_HIT
    if 0 <= te < 0.12: f *= 1 + 0.10 * np.exp(-te / 0.05)
    return f


# ======================================================================= B. ЧЕЛОВЕК НА УЛИЦЕ
imgB = still(30.0)
manM = grabcut(imgB, (int(W * .30), int(H * .27), int(W * .42), int(H * .66)))
treeM = grabcut(imgB, (0, int(H * .18), int(W * .45), int(H * .62)))
treeM[cv2.dilate(manM, np.ones((25, 25), np.uint8)) > 0] = 0
hsvB = cv2.cvtColor(imgB, cv2.COLOR_RGB2HSV)
leaf = ((treeM > 0) & (hsvB[..., 0] > 25) & (hsvB[..., 0] < 50) & (hsvB[..., 1] > 60)).astype(np.uint8) * 255
LEAF = palette(imgB[leaf > 0], 3)
GROUND = palette(imgB[int(H * .80):, :][::4, ::4], 4)
DUST = GROUND[np.argsort(-GROUND.sum(1))][:2]               # светлые цвета тротуара — пыль
DUST[1] = DUST[0] * 0.85 + DUST[1] * 0.15
print("листва:", LEAF.astype(int).tolist(), "пыль:", DUST.astype(int).tolist())
manA = cv2.GaussianBlur(manM.astype(np.float32) / 255, (0, 0), 1.0)[..., None]
bgB = cv2.inpaint(imgB, cv2.dilate(manM, np.ones((21, 21), np.uint8)), 9, cv2.INPAINT_TELEA).astype(np.float32)
imgBf = imgB.astype(np.float32)
# псевдоглубина фона: небо/дома 0.15, земля 0.3→1.0 к низу, дерево 0.65
dB = np.full((H, W), 0.15, np.float32)
dB = np.maximum(dB, np.clip((YY - 1250) / (H - 1250), 0, 1) * 0.7 + 0.3 * (YY > 1250))
dB = np.where(treeM > 0, 0.65, dB); dB = cv2.GaussianBlur(dB, (0, 0), 10)
D_MAN = 0.8
tree_top = np.where(treeM.any(1))[0]; tt0, tt1 = (tree_top[0], tree_top[-1]) if len(tree_top) else (0, H)
leafW = cv2.GaussianBlur(leaf.astype(np.float32) / 255, (0, 0), 12) * np.clip((tt1 - YY) / max(tt1 - tt0, 1), 0, 1) ** 1.2
mcx, mcy = W * 0.51, H * 0.62                               # центр человека (для наезда)
T0B = AB0
HITS_B = [30.06, 32.10, 33.90]                               # «разрушаться», «руины», «сметут»

ND = 140
dX, dY0 = rng.uniform(0, W, ND), rng.uniform(80, 1050, ND)
dT0 = rng.uniform(29.0, 34.0, ND); dV = rng.uniform(60, 160, ND); dR = rng.uniform(4.0, 10.0, ND)
dA = rng.uniform(0.35, 0.7, ND); dC = rng.integers(0, 2, ND)
NL = 80                                                     # листья/пыль ветра: справа налево
lY = rng.uniform(150, 1750, NL); lV = rng.uniform(650, 1250, NL); lT0 = np.concatenate([rng.uniform(39.15, 40.2, 30), rng.uniform(40.2, 44.6, NL - 30)])
lPh = rng.uniform(0, 6.28, NL); lSz = rng.uniform(10, 19, NL); lC = rng.integers(0, 3, NL); lKind = rng.uniform(0, 1, NL)


def wind(t):
    return smooth((t - 39.15) / 0.35)


def leaf_sprite(sz, ang, col):
    s = int(sz * 2.4) | 1; im = np.zeros((s, s), np.float32)
    cv2.ellipse(im, (s // 2, s // 2), (int(sz), max(2, int(sz * 0.42))), np.rad2deg(ang), 0, 360, 1.0, -1, cv2.LINE_AA)
    return im, col


def flyers(lay, t, y_shift=0.0):
    w = wind(t)
    if w <= 0: return
    for i in range(NL):
        tt = t - lT0[i]
        if tt < 0: continue
        x = W + 40 - lV[i] * tt * w
        if x < -40: continue
        y = lY[i] + y_shift + 40 * np.sin(2 * np.pi * 1.3 * tt + lPh[i]) - 60 * tt
        if lKind[i] < 0.65:
            im, col = leaf_sprite(lSz[i], lPh[i] + 7 * tt, LEAF[lC[i]])
        else:
            im, col = blob(lSz[i] * 0.35, 0.25), DUST[lC[i] % 2]
        stamp(lay, x, y, im, col, 0.92)


def frameB(k):
    t = k / FPS; u = (t - T0B) / (BC1 - T0B)
    sw = (2.2 + 3.0 * smooth((t - 29.0) / 1.0) * (1 - smooth((t - 35.5) / 0.6)) + 7.0 * wind(t))
    wx = sw * np.sin(2 * np.pi * 0.9 * t + YY * 0.006 + XX * 0.003) * leafW
    wy = 0.35 * sw * np.sin(2 * np.pi * 1.3 * t + XX * 0.01) * leafW
    camx = -12 * np.cos(np.pi * u)                           # камера плывёт слева направо
    mx = (XX - wx - (dB - D_MAN) * camx).astype(np.float32); my = (YY - wy).astype(np.float32)
    f = cv2.remap(bgB, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    man = cv2.warpAffine(imgBf, np.float32([[1, 0, 0], [0, 1, 0]]), (W, H))       # человек — неподвижная плоскость
    ma = manA
    f = f * (1 - ma) + man * ma
    # пыль с домов
    if 28.9 < t < 36.5:
        fade = 1 - smooth((t - 35.4) / 1.0)
        for i in range(ND):
            tt = t - dT0[i]
            if tt < 0: continue
            y = dY0[i] + dV[i] * tt + 45 * tt * tt; x = dX[i] + 10 * np.sin(2 * np.pi * 0.6 * tt + i)
            if y > H: continue
            stamp(f, x, y, blob(dR[i], 0.25), DUST[dC[i]], dA[i] * fade * min(1, tt / 0.3))
    flyers(f, t)
    # камера: медленный наезд, толчок на «понесёт вперёд», затишье к небу на «атмосферой»
    z = 1.03 + 0.03 * smooth(u) + 0.035 * ease_out((t - 26.3) / 0.55) - 0.012 * ease_io((t - 28.4) / 1.5)
    dy = 70 * ease_io((t - 36.1) / 2.6) * (1 - ease_io((t - 39.2) / 0.9))
    tr = smooth((t - 29.0) / 0.4) * (1 - smooth((t - 35.3) / 0.5))
    sx = 2.5 * tr * np.sin(2 * np.pi * 13 * t) + 1.5 * wind(t) * np.sin(2 * np.pi * 7 * t)
    sy = 2.0 * tr * np.sin(2 * np.pi * 17 * t + 1)
    hx, hy = shake(t, HITS_B, 10, 7)
    return affine(np.clip(f, 0, 255), z, mcx, mcy, sx + hx, sy + hy + dy)


# ======================================================================= C. УЛИЦА С УРНОЙ
imgC = still(43.0)
can = grabcut(imgC, (425, 1085, 290, 365), 8)
hsvC = cv2.cvtColor(imgC, cv2.COLOR_RGB2HSV)
beige = (hsvC[..., 0] >= 8) & (hsvC[..., 0] <= 26) & (hsvC[..., 1] > 35) & (hsvC[..., 2] > 150)
can[beige & (YY > 1250)] = 0
can = cv2.morphologyEx(can, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)); can = biggest(can)
can = cv2.morphologyEx(can, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
ys_, xs_ = np.where(can > 0); ccx, ccy = xs_.mean(), ys_.max() - 30          # ось качания — у дна урны
bgC = cv2.inpaint(imgC, cv2.dilate(can, np.ones((13, 13), np.uint8)), 7, cv2.INPAINT_TELEA).astype(np.float32)
imgCf = imgC.astype(np.float32); canA = cv2.GaussianBlur(can.astype(np.float32) / 255, (0, 0), 0.8)
DEB = [(560, 955, 20), (615, 980, 28), (695, 945, 22), (642, 1015, 14), (585, 1045, 18), (480, 1045, 18), (455, 1120, 16)]
dph = rng.uniform(0, 6.28, (len(DEB), 2)); dfr = rng.uniform(2.5, 4.5, len(DEB))
T0C = BC0; HITS_C = [41.60, 43.36]                           # «чудовищные», «уничтожать»
hcx, hcy = W * 0.5, H * 0.55


def frameC(k):
    t = k / FPS; w = wind(t)
    a = (1.2 + 3.0 * smooth((t - 41.4) / 0.5) + 2.5 * smooth((t - 43.2) / 0.3))     # амплитуда, градусы
    # бумажки трепещут: локальная мягкая деформация (вместе с ближайшим фоном, без дыр)
    wx = np.zeros((H, W), np.float32); wy = np.zeros((H, W), np.float32)
    for j, (x, y, r) in enumerate(DEB):
        x0, x1_, y0, y1_ = x - 3 * r, x + 3 * r, y - 3 * r, y + 3 * r
        gw = np.exp(-(((XX[y0:y1_, x0:x1_] - x) ** 2 + (YY[y0:y1_, x0:x1_] - y) ** 2) / (2 * r * r)))
        amp = 0.25 * r * (0.6 + 0.4 * a / 6.7)
        wx[y0:y1_, x0:x1_] += gw * (amp * np.sin(2 * np.pi * dfr[j] * t + dph[j, 0]) - 0.15 * r * w)
        wy[y0:y1_, x0:x1_] += gw * amp * 0.7 * np.sin(2 * np.pi * dfr[j] * 1.3 * t + dph[j, 1])
    mx, my = (XX - wx).astype(np.float32), (YY - wy).astype(np.float32)
    f = cv2.remap(bgC, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    src = cv2.remap(imgCf, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    # урна: качание вокруг дна + подскок
    ang = a * np.sin(2 * np.pi * 2.1 * (t - T0C)) + 1.5 * a / 6.7 * np.sin(2 * np.pi * 5.3 * t)
    bob = -(2 + 6 * a / 6.7) * abs(np.sin(2 * np.pi * 1.6 * (t - T0C)))
    M = cv2.getRotationMatrix2D((float(ccx), float(ccy)), float(ang), 1.0); M[1, 2] += bob
    cimg = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    ca = cv2.warpAffine(canA, M, (W, H), flags=cv2.INTER_LINEAR)[..., None]
    f = f * (1 - ca) + cimg * ca
    flyers(f, t, y_shift=-120)
    z = 1.0 + 0.06 * smooth((t - T0C) / (DUR - T0C))
    hx, hy = shake(t, HITS_C, 6, 8); hx2, hy2 = shake(t, [43.36], 7, 6, 15, 12)
    gust = 1.8 * w * np.sin(2 * np.pi * 6 * t)
    return affine(np.clip(f, 0, 255), z, hcx, hcy, hx + hx2 + gust, hy + hy2)


# ======================================================================= сборка
def render(k):
    t = k / FPS
    if t < AB0: return frameA(k)
    if t < AB1: a = (t - AB0) / (AB1 - AB0); return frameA(k) * (1 - a) + frameB(k) * a
    if t < BC0: return frameB(k)
    if t < BC1: a = (t - BC0) / (BC1 - BC0); return frameB(k) * (1 - a) + frameC(k) * a
    return frameC(k)


if PREVIEW:
    for t in PREVIEW:
        k = int(round(t * FPS)); a = still(t); b = np.clip(render(k), 0, 255).astype(np.uint8)
        cv2.imwrite(f"{PDIR}/before_after_{t:05.2f}.png", cv2.cvtColor(np.hstack([a, b]), cv2.COLOR_RGB2BGR))
    sys.exit()

enc = subprocess.Popen([
    "ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", SRC, "-filter_complex",
    "[0:v]scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd,format=yuv420p[v];"
    "[1:a]aresample=48000,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-profile:v", "high", "-b:v", "14M", "-maxrate", "18M", "-bufsize", "28M",
    "-preset", "medium", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{N / FPS:.3f}", OUT], stdin=subprocess.PIPE)
for k in range(N):
    enc.stdin.write(np.clip(render(k), 0, 255).astype(np.uint8).tobytes())
    if k % 100 == 0: print(f"кадр {k}/{N}", flush=True)
enc.stdin.close(); enc.wait()
print("ГОТОВО", OUT, f"{os.path.getsize(OUT) / 1e6:.1f} МБ, {N} кадров")
