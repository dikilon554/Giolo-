#!/usr/bin/env python3
"""Динамичный hype/house-бит ~123 BPM под монтаж «как у конкурента» (синтез на numpy, без семплов и лицензий).
Рисунок: кик по четвертям, хлопок на 2 и 4, офф-бит хэты, синкопированный саб-бас, мидовая «щипковая» арпа.
Нарастание энергии: тихо в начале, к ~12 с полный бит (как у конкурента).
Запуск: python scripts/music_hype.py <секунд> <out.wav>"""
import sys, numpy as np, wave
SR, BPM = 44100, 123
dur = float(sys.argv[1]); out = sys.argv[2]
n = int(dur * SR); beat = 60 / BPM; s16 = beat / 4; bar = beat * 4
rng = np.random.default_rng(3)
D = np.zeros(n)          # сухие ударные (кик, хлопок, хэты)
M = np.zeros(n)          # «качаемый» слой (бас, арпа, пэд)
ss = lambda x: np.clip(x, 0, 1) ** 2 * (3 - 2 * np.clip(x, 0, 1))
ramp = lambda t, a, b, lo=0.0, hi=1.0: lo + (hi - lo) * ss((t - a) / (b - a))

def put(buf, sig, t, g=1.0):
    i = int(t * SR)
    if 0 <= i < n: j = min(n, i + len(sig)); buf[i:j] += sig[:j - i] * g

def kick():
    tt = np.arange(int(0.34 * SR)) / SR; f = 46 + 120 * np.exp(-tt * 32); ph = 2 * np.pi * np.cumsum(f) / SR
    k = np.sin(ph) * np.exp(-tt * 9) + 0.3 * np.sin(2 * np.pi * 900 * tt) * np.exp(-tt * 160)
    return np.tanh(1.5 * k)
def clap():
    L = int(0.20 * SR); x = np.diff(rng.standard_normal(L), prepend=0); env = np.exp(-np.arange(L) / SR * 24)
    for d in (0.0, 0.011, 0.023): env[int(d * SR):int(d * SR) + 350] *= 1.5
    return x * env * 0.5
def hat(op=False):
    L = int((0.21 if op else 0.04) * SR); x = np.diff(np.diff(rng.standard_normal(L), prepend=0), prepend=0)
    return x * np.exp(-np.arange(L) / SR * (15 if op else 95)) * (0.30 if op else 0.26)
def sub(freq, L):
    tt = np.arange(int(L * SR)) / SR; f = freq * (1 + 0.5 * np.exp(-tt * 45)); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(2.0 * np.sin(ph) * np.exp(-tt * 4.0)) * 0.8
def pluck(freq, L=0.22):
    tt = np.arange(int(L * SR)) / SR; s = 0
    for det in (0.995, 1.005):
        for k in range(1, 8): s = s + np.sin(2 * np.pi * freq * det * k * tt) / k * np.exp(-tt * (8 + 14 * (k - 1) / 6))
    return s * 0.16
def pad(freqs, L):
    tt = np.arange(int(L * SR)) / SR; s = 0
    for f in freqs:
        for d in (-0.5, 0.5): s = s + np.sin(2 * np.pi * (f + d) * tt) + 0.4 * np.sin(2 * np.pi * 2 * (f + d) * tt)
    return s * np.minimum(tt / 0.4, 1) * np.minimum((L - tt) / 0.4, 1) * 0.028

roots = [55.0, 43.65, 65.41, 49.0]                         # Am F C G
chords = [(220, 261.63, 329.63), (174.61, 220, 261.63), (261.63, 329.63, 392.0), (196, 246.94, 293.66)]
KICK = {0, 4, 8, 12}; CLAP = {4, 12}; OPEN = {2, 6, 10, 14}; BASS = {0: 0.34, 3: 0.14, 7: 0.16, 10: 0.14, 15: 0.12}; ARP = (0, 3, 6, 9, 12, 15)
k_ = kick(); c_ = clap()
t, step = 0.0, 0
while t < dur:
    bi = int(t // bar) % 4; b16 = step % 16
    kg = ramp(t, 0, 10, 0.35, 1.0); hg = ramp(t, 0, 8, 0.5, 1.0); cg = ramp(t, 5, 9); bg = ramp(t, 2.5, 11); ag = ramp(t, 6, 14)
    if b16 in KICK: put(D, k_, t, 0.95 * kg)
    if b16 in CLAP: put(D, c_, t, 0.7 * cg)
    if b16 in OPEN: put(D, hat(True), t, 1.35 * hg)
    elif b16 % 2 == 1: put(D, hat(False), t, 1.0 * hg)
    if b16 in BASS: put(M, sub(roots[bi], BASS[b16]), t, 0.6 * bg)
    if b16 in ARP: put(M, pluck(chords[bi][(ARP.index(b16)) % 3] * 2), t, 0.8 * ag)
    if b16 == 0: put(M, pad(chords[bi], bar + 0.3), t, 0.7)
    t += s16; step += 1
duck = np.ones(n); tk = 0.0
while tk < dur:
    i = int(tk * SR); L = int(0.22 * SR)
    if i < n: seg = np.linspace(0.38, 1, min(L, n - i)) ** 1.4; duck[i:i + len(seg)] = np.minimum(duck[i:i + len(seg)], seg)
    tk += beat
mix = np.tanh(1.25 * (D + M * duck))
fo = int(1.0 * SR); env = np.ones(n); env[-fo:] = np.linspace(1, 0, fo); mix *= env
d = int(0.010 * SR); left = mix; right = np.concatenate([np.zeros(d), mix[:-d]])
m = max(np.abs(left).max(), np.abs(right).max())
data = (np.stack([left, right], 1) / m * 0.9 * 32767).astype("<i2")
with wave.open(out, "wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data.tobytes())
print("ok", out, f"{dur:.1f} с, {BPM} BPM")
