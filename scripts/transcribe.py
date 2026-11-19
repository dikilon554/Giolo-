#!/usr/bin/env python3
"""Расшифровка видео/аудио через GigaAM-v3 (e2e_rnnt, с пунктуацией).

Запуск:  /home/user/gigaam-venv/bin/python scripts/transcribe.py <файл> [<файл> ...]
Результат: public/transcripts/<имя>.json и <имя>.srt
Модель берётся из локальной проверенной копии MODEL_DIR (trust_remote_code
выполняет только modeling_gigaam.py оттуда).
"""
import json, os, re, subprocess, sys, tempfile
import numpy as np
import torch
from transformers import AutoModel

MODEL_DIR = os.environ.get("GIGAAM_DIR", "/home/user/gigaam-model")
OUT_DIR = "public/transcripts"
SR = 16000
MAX_SEG = 22.0   # сек, модель держит до ~25 с
MIN_SEG = 0.4


def load_wav(path):
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-f", "s16le",
           "-ac", "1", "-ar", str(SR), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def segments(wav):
    """Нарезка по паузам (энергия в окнах 30 мс), куски до MAX_SEG секунд."""
    win = int(0.03 * SR)
    n = len(wav) // win
    if n == 0:
        return []
    rms = np.sqrt((wav[: n * win].reshape(n, win) ** 2).mean(axis=1))
    thr = max(np.percentile(rms, 20) * 2.5, 0.006)
    voiced = rms > thr
    # закрываем короткие паузы (< 0.35 с), чтобы не рвать фразы
    gap = int(0.35 / 0.03)
    segs, start, last = [], None, None
    for i, v in enumerate(voiced):
        if v:
            if start is None:
                start = i
            elif i - last > gap:
                segs.append((start, last + 1)); start = i
            last = i
    if start is not None:
        segs.append((start, last + 1))
    out = []
    for s, e in segs:
        s, e = max(0, s * win - int(0.15 * SR)), min(len(wav), e * win + int(0.15 * SR))
        while e - s > MAX_SEG * SR:  # слишком длинный кусок режем на равные части
            k = int(np.ceil((e - s) / (MAX_SEG * SR)))
            step = (e - s) // k
            for j in range(k):
                out.append((s + j * step, s + (j + 1) * step))
            s = e
            break
        else:
            if e - s >= MIN_SEG * SR:
                out.append((s, e))
    return out


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"


def main(files):
    model = AutoModel.from_pretrained(MODEL_DIR, trust_remote_code=True).eval()
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in files:
        wav = load_wav(f)
        items = []
        for s, e in segments(wav):
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                path = tmp.name
            import soundfile as sf
            sf.write(path, wav[s:e], SR)
            with torch.no_grad():
                text = model.transcribe(path).strip()
            os.unlink(path)
            if text:
                items.append({"start": round(s / SR, 2), "end": round(e / SR, 2), "text": text})
        base = re.sub(r"[^\w.-]+", "_", os.path.splitext(os.path.basename(f))[0])
        with open(f"{OUT_DIR}/{base}.json", "w", encoding="utf-8") as fh:
            json.dump({"source": os.path.basename(f), "duration": round(len(wav) / SR, 2),
                       "segments": items}, fh, ensure_ascii=False, indent=2)
        with open(f"{OUT_DIR}/{base}.srt", "w", encoding="utf-8") as fh:
            for i, it in enumerate(items, 1):
                fh.write(f"{i}\n{srt_time(it['start'])} --> {srt_time(it['end'])}\n{it['text']}\n\n")
        print(f"{f}: {len(items)} фраз -> {OUT_DIR}/{base}.json|srt")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
