#!/usr/bin/env python3
"""Сетка битов трека: BPM, фаза первого удара и старт для рилса (удар около 12 с).
Запуск: python scripts/track_beats.py <трек.mp4> <out.json>"""
import sys, subprocess, json, numpy as np, wave, tempfile, os
src, out = sys.argv[1], sys.argv[2]
tmp = tempfile.mktemp(suffix=".wav")
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "22050", tmp], check=True)
w = wave.open(tmp); sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768; os.unlink(tmp)
n, hop = 1024, 128; win = np.hanning(n); fr = np.fft.rfftfreq(n, 1 / sr); fps = sr / hop
S = np.array([np.abs(np.fft.rfft(x[i:i + n] * win)) for i in range(0, len(x) - n, hop)])
bass, hi = S[:, (fr >= 40) & (fr < 180)].sum(1), S[:, (fr >= 3000) & (fr < 9000)].sum(1)
on = lambda e: (lambda o: o - o.mean())(np.maximum(np.diff(np.log1p(e * 40)), 0))
o = on(bass) + 0.5 * on(hi); best = None
for bpm in np.arange(122.0, 125.0, 0.02):
    T = 60 / bpm * fps
    for ph in np.arange(0, T, 0.5):
        sc = o[(np.arange(ph, len(o) - 1, T)).astype(int)].sum()
        if best is None or sc > best[0]: best = (sc, bpm, ph / fps)
_, bpm, b0 = best; T = 60 / bpm
json.dump({"bpm": float(bpm), "b0": float(b0), "start": float(b0 + np.ceil((12.0 - b0) / T) * T)}, open(out, "w"))
print(f"BPM {bpm:.2f}, старт трека {b0 + np.ceil((12.0 - b0) / T) * T:.3f} с")
