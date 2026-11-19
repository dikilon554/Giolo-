#!/usr/bin/env python3
"""Простой минималистичный бит (118 BPM, ля минор), синтез на numpy, без внешних семплов и лицензий.
Запуск: python scripts/music.py <секунд> <out.wav>"""
import sys, numpy as np, wave
SR, BPM = 44100, 118
dur = float(sys.argv[1]); out = sys.argv[2]
n = int(dur * SR); t = np.arange(n) / SR
beat = 60 / BPM; rng = np.random.default_rng(7)
mix_l = np.zeros(n); mix_r = np.zeros(n)

def add(sig, start, gain=1.0, pan=0.0):
    i = int(start * SR); j = min(n, i + len(sig))
    if i >= n: return
    mix_l[i:j] += sig[:j-i] * gain * (1 - max(pan, 0)); mix_r[i:j] += sig[:j-i] * gain * (1 + min(pan, 0))

def kick():
    tt = np.arange(int(0.32 * SR)) / SR
    f = 48 + 90 * np.exp(-tt * 28); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-tt * 9) * (1 - np.exp(-tt * 900))
def hat(open_=False):
    L = int((0.22 if open_ else 0.05) * SR); x = rng.standard_normal(L)
    x = np.diff(x, prepend=0); x = np.diff(x, prepend=0)       # высокочастотный шум
    return x * np.exp(-np.arange(L) / SR * (14 if open_ else 70)) * 0.35
def clap():
    L = int(0.18 * SR); x = rng.standard_normal(L)
    x = np.convolve(x, np.ones(6) / 6, mode="same")
    return x * np.exp(-np.arange(L) / SR * 24) * 0.5
def pluck(freq, L=0.45):
    tt = np.arange(int(L * SR)) / SR
    s = sum(np.sin(2 * np.pi * freq * k * tt) / k for k in (1, 2, 3)) * np.exp(-tt * 7)
    return s * 0.32
def pad(freqs, L):
    tt = np.arange(int(L * SR)) / SR; s = 0
    for f in freqs:
        for d in (-0.4, 0.4):
            s = s + np.sin(2 * np.pi * (f + d) * tt) + 0.4 * np.sin(2 * np.pi * (2 * f + d) * tt)
    env = np.minimum(tt / 0.8, 1) * np.minimum((L - tt) / 0.8, 1)
    return s * env * 0.035

A2, C3, E3, G3 = 110.0, 130.81, 164.81, 196.0
bar = beat * 4
chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (196.0, 246.94, 293.66), (164.81, 207.65, 246.94)]
bass_notes = [55.0, 43.65, 49.0, 41.2]
nb = int(dur / beat) + 1
for b in range(nb):
    ts = b * beat; bar_i = (b // 4) % 4; intro = ts < bar * 1.0
    if not intro:
        add(kick(), ts, 0.95)
        add(hat(), ts + beat / 2, 0.55, 0.3); add(hat(), ts + beat / 4, 0.25, -0.3); add(hat(), ts + 3 * beat / 4, 0.25, 0.3)
        if b % 4 == 3: add(hat(True), ts + beat / 2, 0.4, 0.2)
    if b % 2 == 1 and not intro: add(clap(), ts, 0.6)
    # бас: короткий ритм
    if not intro:
        for k, off in enumerate((0.5, 0.75)):
            add(pluck(bass_notes[bar_i], 0.28) * 1.6, ts + off * beat, 0.5)
    # мягкая «арпа»
    ch = chords[bar_i]
    add(pluck(ch[b % 3] * 2, 0.35), ts + beat * 0.25, 0.4, -0.25)
for bi in range(int(dur / bar) + 1):
    add(pad(chords[bi % 4], bar + 0.4), bi * bar, 1.0)

# сайдчейн «качает» от бочки
duck = np.ones(n)
for b in range(nb):
    if b * beat < bar: continue
    i = int(b * beat * SR); L = int(0.28 * SR)
    if i < n: duck[i:min(n, i + L)] *= np.linspace(0.45, 1, min(L, n - i)) ** 1.5
pads_only = None
mix_l, mix_r = mix_l * (0.55 + 0.45 * duck), mix_r * (0.55 + 0.45 * duck)
# затухание в конце
fo = int(1.5 * SR); env = np.ones(n); env[-fo:] = np.linspace(1, 0, fo); mix_l *= env; mix_r *= env
m = max(np.abs(mix_l).max(), np.abs(mix_r).max()); mix_l, mix_r = mix_l / m * 0.9, mix_r / m * 0.9
data = (np.stack([mix_l, mix_r], 1) * 32767).astype("<i2")
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data.tobytes())
print("ok", out, f"{dur:.1f} с")
