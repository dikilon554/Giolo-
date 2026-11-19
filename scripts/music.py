#!/usr/bin/env python3
"""Тёмный энергичный бит для рилса (128 BPM, ля минор, i–VI–VII–V), синтез на numpy, без семплов и лицензий.
0–1 такт: тревожный подъём (дрон + нарастающий шум), дальше «дроп»: бочка, клэп, хэты, 808-бас, тёмная арпа.
Запуск: python scripts/music.py <секунд> <out.wav> [drop_сек=1.875]"""
import sys, numpy as np, wave
SR, BPM = 44100, 128
dur = float(sys.argv[1]); out = sys.argv[2]
drop = float(sys.argv[3]) if len(sys.argv) > 3 else 60 / BPM * 4
n = int(dur * SR); beat = 60 / BPM; bar = beat * 4; s16 = beat / 4
rng = np.random.default_rng(11)
L_ = np.zeros(n); R_ = np.zeros(n)           # сухой микс (бочка, клэп, хэты)
M_ = np.zeros(n)                              # «качаемый» слой (бас, арпа, пэд) — приглушается бочкой

def put(buf, sig, t, g=1.0):
    i = int(t * SR)
    if i >= n or i < 0: return
    j = min(n, i + len(sig)); buf[i:j] += sig[:j - i] * g

def kick():
    tt = np.arange(int(0.36 * SR)) / SR
    f = 46 + 130 * np.exp(-tt * 34); ph = 2 * np.pi * np.cumsum(f) / SR
    k = np.sin(ph) * np.exp(-tt * 8.5)
    k += 0.35 * np.sin(2 * np.pi * 900 * tt) * np.exp(-tt * 150)       # щелчок
    return np.tanh(1.6 * k)
def clap():
    L = int(0.22 * SR); x = rng.standard_normal(L)
    x = np.diff(x, prepend=0)
    env = np.exp(-np.arange(L) / SR * 22)
    for d in (0.0, 0.012, 0.024): env[int(d * SR):int(d * SR) + 400] *= 1.6
    return x * env * 0.45
def hat(op=False, g=1.0):
    L = int((0.20 if op else 0.045) * SR); x = rng.standard_normal(L)
    x = np.diff(x, prepend=0); x = np.diff(x, prepend=0)
    return x * np.exp(-np.arange(L) / SR * (16 if op else 85)) * 0.32 * g
def sub808(freq, L):
    tt = np.arange(int(L * SR)) / SR
    f = freq * (1 + 0.7 * np.exp(-tt * 40)); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(2.2 * np.sin(ph) * np.exp(-tt * 3.2)) * 0.8
def dark_pluck(freq, L):
    tt = np.arange(int(L * SR)) / SR; s = 0
    for det in (0.994, 1.0, 1.006):
        for k in range(1, 9):
            s = s + np.sin(2 * np.pi * freq * det * k * tt) / k * np.exp(-tt * (6 + 14 * (k - 1) / 7))
    return s * 0.18
def pad(freqs, L):
    tt = np.arange(int(L * SR)) / SR; s = 0
    for f in freqs:
        for d in (-0.5, 0.5):
            s = s + np.sin(2 * np.pi * (f + d) * tt) + 0.5 * np.sin(2 * np.pi * 2 * (f + d) * tt) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.25 * tt))
    env = np.minimum(tt / 0.6, 1) * np.minimum((L - tt) / 0.6, 1)
    return s * env * 0.03

roots = [55.0, 43.65, 49.0, 41.2]                      # A F G E
chords = [(220, 261.63, 329.63), (174.61, 220, 261.63), (196, 246.94, 293.66), (164.81, 207.65, 246.94)]
pattern = [0, 2, 3, 6, 8, 10, 11, 14]                  # шаги 1/16 арпеджио в такте

# ---- подъём до дропа: дрон + нарастающий шум + тревожный свип
ni = int(drop * SR); tt = np.arange(ni) / SR
x = rng.standard_normal(ni); x = np.diff(x, prepend=0)
sweep = np.sin(2 * np.pi * np.cumsum(180 * (1 + 7 * (tt / drop) ** 2)) / SR) * (tt / drop) ** 2 * 0.25
put(M_, x * (tt / drop) ** 3 * 0.35 + sweep + np.sin(2 * np.pi * 55 * tt) * 0.35 * np.minimum(tt / 0.4, 1)
    + np.sin(2 * np.pi * 110.5 * tt) * 0.15 * (tt / drop), 0)
put(L_, sub808(55, 0.9), 0.0, 0.5)
put(L_, hat(True), drop - 0.5 * beat, 0.5)
for q in range(8): put(L_, clap() * (0.3 + 0.1 * q), drop - (8 - q) * s16 * 1.0, 0.45)   # маленький ролл

# ---- основная часть
t = drop; step = 0
while t < dur:
    bi = int((t - drop) // bar) % 4; pos = ((t - drop) % bar)
    b16 = int(round(pos / s16)) % 16; beat_i = b16 // 4
    if b16 % 4 == 0: put(L_, kick(), t, 0.95)
    if b16 in (4, 12): put(L_, clap(), t, 0.7)
    if b16 % 4 == 2: put(L_, hat(), t, 0.7)
    if b16 % 2 == 1: put(L_, hat(g=0.55), t, 0.5)
    if b16 == 14 and bi % 2 == 1: put(L_, hat(True), t, 0.5)
    if b16 in (0, 6, 10): put(M_, sub808(roots[bi] , 0.42 if b16 == 0 else 0.22), t, 0.85)
    if b16 in pattern:
        notes = chords[bi]; fr = notes[pattern.index(b16) % 3] * (2 if pattern.index(b16) % 2 else 1)
        put(M_, dark_pluck(fr, 0.28), t, 0.7)
    if b16 == 0: put(M_, pad(chords[bi], bar + 0.3), t, 1.0)
    # ролл на последней доле каждого 4-го такта
    if (int((t - drop) // bar) % 4 == 3) and b16 >= 12: put(L_, clap() * 0.7, t, 0.5)
    t += s16

# ---- сайдчейн от бочки на слое M_
duck = np.ones(n); tk = drop
while tk < dur:
    i = int(tk * SR); L = int(0.24 * SR)
    if i < n: duck[i:min(n, i + L)] = np.minimum(duck[i:min(n, i + L)], np.linspace(0.35, 1, min(L, n - i)) ** 1.4)
    tk += beat
mix = L_ + M_ * duck
mix = np.tanh(1.3 * mix)                                                 # мягкая «грязь»/склейка
fo = int(1.4 * SR); env = np.ones(n); env[-fo:] = np.linspace(1, 0, fo) ** 1.5; mix *= env
# псевдо-стерео: лёгкая задержка правого канала
d = int(0.011 * SR); left = mix; right = np.concatenate([np.zeros(d), mix[:-d]])
m = max(np.abs(left).max(), np.abs(right).max())
data = (np.stack([left, right], 1) / m * 0.9 * 32767).astype("<i2")
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data.tobytes())
print("ok", out, f"{dur:.1f} с, дроп на {drop:.2f} с")
