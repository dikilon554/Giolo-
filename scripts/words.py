#!/usr/bin/env python3
"""Пословная расшифровка для скиллов монтажа (faster-whisper, large-v3-turbo).

Запуск: /home/user/gigaam-venv/bin/python scripts/words.py <файл> [<файл> ...]
Результат: монтаж_слова/<имя>.words.json — [{"word","start","end"}] в секундах.
Помни: время слов неточное (±120 мс), резать нужно в тишине между фразами.
"""
import json, os, re, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel

MODEL_DIR = os.environ.get("WHISPER_DIR", "/home/user/whisper-model")
OUT_DIR = "монтаж_слова"


def load_audio(path, sr=16000):
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-f", "s16le",
           "-ac", "1", "-ar", str(sr), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def main(files):
    model = WhisperModel(MODEL_DIR, device="cpu", compute_type="int8")
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in files:
        audio = load_audio(f)
        segs, info = model.transcribe(audio, language="ru", word_timestamps=True,
                                      vad_filter=True, beam_size=5)
        words = [{"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)}
                 for s in segs for w in (s.words or [])]
        base = re.sub(r"[^\w.-]+", "_", os.path.splitext(os.path.basename(f))[0])
        with open(f"{OUT_DIR}/{base}.words.json", "w", encoding="utf-8") as fh:
            json.dump({"source": os.path.basename(f), "duration": round(len(audio) / 16000, 2),
                       "words": words}, fh, ensure_ascii=False, indent=1)
        print(f"{f}: {len(words)} слов -> {OUT_DIR}/{base}.words.json")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
