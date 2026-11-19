#!/usr/bin/env python3
"""Вставка для нового рилса: начало ролика «Бессмертный» (0–6.86 с), 1080x1920, субтитры как на вставке с динозаврами."""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = f"{ROOT}/исходники/anim_source.mp4"
OUT = f"{ROOT}/монтаж_2026-11-19/вставка"; os.makedirs(OUT, exist_ok=True)
FB = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
END = 6.86                      # речь кончается на 6.76 с, смена сцены на 7.0 с
W, H, SIZE = 1080, 1920, 64
CHUNKS = [(0.28, 1.38, "Что, если завтра"), (1.38, 2.65, "ты станешь бессмертным?"),
          (3.12, 4.11, "Тебя невозможно"), (4.11, 4.89, "убить ничем."), (5.70, 6.76, "Куда пойдёшь первым?")]
f = ImageFont.truetype(FB, SIZE); asc, desc = f.getmetrics(); th = asc + desc
CY = int(H * 0.91); PX, PY = 12, 9
inp = ["-i", SRC]; fc = ["[0:v]trim=0:%s,setpts=PTS-STARTPTS,scale=%d:%d:flags=lanczos,fps=25,format=yuv420p[v0]" % (END, W, H)]
last = "[v0]"
for i, (a, b, t) in enumerate(CHUNKS, 1):
    tw = f.getlength(t); pw, ph = int(tw + 2 * PX), int(th + 2 * PY)
    im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, pw - 1, ph - 1], fill=(0, 0, 0, 215)); d.text((PX, PY - 1), t, font=f, fill=(255, 255, 255, 255))
    p = f"{OUT}/plate_{i}.png"; im.save(p)
    inp += ["-i", p]
    fc.append(f"[{i}:v]format=rgba,scale=out_color_matrix=bt709:out_range=tv,format=yuva420p[p{i}]")
    fc.append(f"{last}[p{i}]overlay=(W-w)/2:{CY - ph // 2}:enable='between(t,{a},{b})'[o{i}]")
    last = f"[o{i}]"
fc.append(f"{last}setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv[vout]")
fc.append(f"[0:a]atrim=0:{END},asetpts=PTS-STARTPTS,afade=t=out:st={END - 0.15}:d=0.15[aout]")
out = f"{OUT}/бессмертный_вставка.mp4"
r = subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", *inp, "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
                    "-c:v", "libx264", "-profile:v", "high", "-b:v", "12M", "-maxrate", "16M", "-bufsize", "24M", "-preset", "medium",
                    "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", str(END), out], capture_output=True, text=True)
if r.returncode: sys.exit(r.stderr[-2000:])
print("ГОТОВО", out, f"{os.path.getsize(out)/1e6:.1f} МБ")
