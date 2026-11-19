#!/usr/bin/env python3
"""Сборка рилса «Две крупности» по одобренному плану.

Запуск: /home/user/gigaam-venv/bin/python scripts/montage.py
Исходники не трогаются, всё пишется в монтаж_<дата>/.
"""
import json, os, subprocess, sys
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

FPS = 25
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = f"{ROOT}/исходники"
MAIN = f"{SRC}/ЭТО ВИДЕО НА МОНТАЖ"
OUT = f"{ROOT}/монтаж_2026-11-19"
FONT_B = f"{ROOT}/assets/fonts/Manrope_800ExtraBold.ttf"
W, H = 1080, 1920
os.makedirs(OUT, exist_ok=True)


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit("FFMPEG FAIL:\n" + " ".join(cmd)[:400] + "\n" + r.stderr[-2500:])
    return r


# ---------------------------------------------------------------- 1. резки
# тишина (silencedetect, -35 дБ) между фразами, сек
SIL = [(0, 0.318), (3.858, 4.519), (6.223, 6.452), (8.747, 9.413), (12.513, 13.143),
       (14.598, 14.869), (16.754, 17.091), (17.841, 18.215), (19.358, 19.697),
       (21.082, 21.634), (22.56, 22.927), (23.734, 24.116), (25.218, 25.778),
       (27.536, 27.893), (30.498, 31.067), (34.613, 34.855), (36.829, 37.207)]
KEEP = 0.15
TOTAL = 37.207
fr = lambda t: int(round(t * FPS))

cuts = [(0.0, 0.28)]                               # тишина в начале
for a, b in SIL[1:-1]:
    d = b - a
    ca, cb = a + (d - KEEP) / 2, b - (d - KEEP) / 2
    if cb - ca >= 0.05:
        cuts.append((ca, cb))
cuts.append((36.98, TOTAL))                        # тишина в конце
cuts_f = [(fr(a), fr(b)) for a, b in cuts]         # по кадрам
total_f = int(TOTAL * FPS)                         # 930 (последний неполный кадр отбрасываем)
cuts_f[-1] = (cuts_f[-1][0], total_f)

kept = []
pos = 0
for a, b in cuts_f:
    if a > pos:
        kept.append((pos, a))
    pos = b
if pos < total_f:
    kept.append((pos, total_f))


def new_f(t):
    """время в оригинале (сек) -> номер кадра в смонтированной шкале"""
    of = fr(t)
    removed = 0
    for a, b in cuts_f:
        if of >= b:
            removed += b - a
        elif of > a:
            removed += of - a
    return of - removed


NEW_TOTAL = sum(b - a for a, b in kept)
print(f"кусков: {len(kept)}, снято {total_f - NEW_TOTAL} кадр. ({(total_f-NEW_TOTAL)/FPS:.2f} с), итого {NEW_TOTAL} кадр. = {NEW_TOTAL/FPS:.2f} с")

# ---------------------------------------------------------------- 2. база (видео + звук без пауз)
base_v = f"{OUT}/base_video.mp4"
base_a = f"{OUT}/base_audio.wav"
if not os.path.exists(base_v):
    vf = ";".join(f"[0:v]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS[v{i}]" for i, (a, b) in enumerate(kept))
    vf += ";" + "".join(f"[v{i}]" for i in range(len(kept))) + f"concat=n={len(kept)}:v=1:a=0[out]"
    run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", MAIN, "-filter_complex", vf, "-map", "[out]",
         "-r", str(FPS), "-c:v", "libx264", "-crf", "8", "-preset", "fast", "-pix_fmt", "yuv420p", base_v])
if not os.path.exists(base_a):
    FD = 0.08  # затухание/нарастание 2 кадра в тишине, без перекрытия
    parts = []
    for i, (a, b) in enumerate(kept):
        s, e = a / FPS, b / FPS
        f = f"[0:a]atrim=start={s:.4f}:end={e:.4f},asetpts=PTS-STARTPTS"
        if i > 0:
            f += f",afade=t=in:st=0:d={FD}"
        if i < len(kept) - 1:
            f += f",afade=t=out:st={e - s - FD:.4f}:d={FD}"
        parts.append(f + f"[a{i}]")
    af = ";".join(parts) + ";" + "".join(f"[a{i}]" for i in range(len(kept))) + f"concat=n={len(kept)}:v=0:a=1[out]"
    run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", MAIN, "-filter_complex", af, "-map", "[out]",
         "-ar", "48000", "-ac", "2", base_a])

# ---------------------------------------------------------------- 3. лицо (кроп для крупного плана)
cap = cv2.VideoCapture(MAIN)
det = cv2.FaceDetectorYN.create(f"{ROOT}/assets/models/face_detection_yunet_2023mar.onnx", "", (W, H), 0.7)
ey, cx, top = [], [], []
for t in (10.0, 10.8, 11.5, 12.0, 32.0, 32.8, 33.5, 34.2):
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, img = cap.read()
    if not ok:
        continue
    _, faces = det.detect(img)
    if faces is None:
        continue
    f = faces[0]
    ey.append((f[5] + f[7]) / 2); cx.append(f[0] + f[2] / 2); top.append(f[1])
cap.release()
EYE_Y, FACE_X, FACE_TOP = float(np.median(ey)), float(np.median(cx)), float(np.median(top))
CW, CH = 720, 1280
CROP_Y = int(round(min(max(EYE_Y - 0.36 * CH, 0), H - CH)))
CROP_X = int(round(min(max(FACE_X - CW / 2, 0), W - CW)))
print(f"лицо: глаза y={EYE_Y:.0f}, центр x={FACE_X:.0f}, верх лица y={FACE_TOP:.0f} -> кроп x={CROP_X}, y={CROP_Y}")

# ---------------------------------------------------------------- 4. раскладка по кадрам
mid = lambda i: (SIL[i][0] + SIL[i][1]) / 2           # середина паузы i (она сохраняется в центре остатка)
B = {"g1": mid(1), "g2": mid(2), "g3": mid(3), "g4": mid(4), "g7": mid(7), "g12": mid(12), "g14": mid(14), "g15": mid(15)}
segs = [  # (тип, orig_начало, orig_конец, параметры)
    ("wide", 0.0, B["g1"], {}),
    ("insert", B["g1"], B["g2"], {"file": "VID_20261118_221519_691.mp4"}),
    ("insert", B["g2"], B["g3"], {"file": "VID_20261118_221517_648.mp4"}),
    ("close", B["g3"], B["g4"], {}),
    ("wide", B["g4"], B["g7"], {}),
    ("insert", B["g7"], B["g12"], {"file": "VID_20261118_221528_160.mp4"}),
    ("insert", B["g12"], B["g14"], {"file": "VID_20261118_221530_395.mp4", "nosub": True}),
    ("close", B["g14"], B["g15"], {}),
    ("wide", B["g15"], TOTAL, {}),
]
S = []
for i, (kind, a, b, p) in enumerate(segs):
    f0 = 0 if i == 0 else S[-1]["f1"]
    f1 = NEW_TOTAL if i == len(segs) - 1 else new_f(b)
    S.append({"kind": kind, "f0": f0, "f1": f1, **p})
assert S[-1]["f1"] == NEW_TOTAL

for s in S:
    if s["kind"] == "insert":
        d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                  f"{SRC}/{s['file']}"], capture_output=True, text=True).stdout)
        need = (s["f1"] - s["f0"]) / FPS
        ratio = d / need
        s["speed"] = ratio if 0.85 <= ratio <= 1.35 else 1.0
        s["clip"] = d
        print(f"вставка {s['file'][:20]}: нужно {need:.2f} с, клип {d:.2f} с -> скорость x{s['speed']:.2f}"
              + (" (обрезаю хвост)" if s["speed"] == 1.0 and d > need else ""))
        assert s["speed"] != 1.0 or d >= need - 0.05, "вставка короче нужного"
    print(f"  {s['kind']:6} кадры {s['f0']:4}-{s['f1']:4} ({s['f0']/FPS:5.2f}-{s['f1']/FPS:5.2f} с)")

# ---------------------------------------------------------------- 5. склейка видео (общий / крупный / вставки)
stage2 = f"{OUT}/stage2.mp4"
inputs = ["-i", base_v]
parts = []
for i, s in enumerate(S):
    n = s["f1"] - s["f0"]
    if s["kind"] == "wide":
        parts.append(f"[0:v]trim=start_frame={s['f0']}:end_frame={s['f1']},setpts=PTS-STARTPTS,setsar=1[v{i}]")
    elif s["kind"] == "close":
        parts.append(f"[0:v]trim=start_frame={s['f0']}:end_frame={s['f1']},setpts=PTS-STARTPTS,"
                     f"crop={CW}:{CH}:{CROP_X}:{CROP_Y},scale={W}:{H}:flags=lanczos,unsharp=5:5:0.5:5:5:0,setsar=1[v{i}]")
    else:
        k = len(inputs) // 2
        inputs += ["-i", f"{SRC}/{s['file']}"]
        parts.append(f"[{k}:v]setpts=(PTS-STARTPTS)/{s['speed']:.5f},fps={FPS},trim=end_frame={n},setpts=PTS-STARTPTS,"
                     f"zscale=w={W}:h={H}:filter=lanczos:matrixin=470bg:matrix=709:rangein=tv:range=tv,"
                     f"format=yuv420p,setsar=1[v{i}]")
fc = ";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(len(S))) + f"concat=n={len(S)}:v=1:a=0[out]"
run(["ffmpeg", "-nostdin", "-y", "-v", "error", *inputs, "-filter_complex", fc, "-map", "[out]", "-r", str(FPS),
     "-c:v", "libx264", "-crf", "10", "-preset", "fast", "-pix_fmt", "yuv420p", stage2])
print("склейка видео готова")

# ---------------------------------------------------------------- 6. карточки и субтитры (PNG)
def rounded(img, r, border=None):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], r, fill=255)
    out = img.convert("RGBA"); out.putalpha(m)
    if border:
        ImageDraw.Draw(out).rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], r, outline=border, width=2)
    return out

banner = rounded(Image.open(f"{SRC}/IMG_20261118_221512_290.jpg").convert("RGB").resize((1000, 245), Image.LANCZOS), 22, (244, 238, 228, 60))
chat = rounded(Image.open(f"{SRC}/chatgpt_logo.png").convert("RGB").resize((640, 360), Image.LANCZOS), 26, (244, 238, 228, 60))
banner.save(f"{OUT}/card_banner.png"); chat.save(f"{OUT}/card_chatgpt.png")
CARD_BOTTOM = 420                 # макушка на кадре ~y=450: карточки строго над головой
BANNER_Y = CARD_BOTTOM - 245
CHAT_Y = CARD_BOTTOM - 360

# слова + подгонка времени к настоящим границам фраз (Whisper плавает на ±0.3 с)
words = json.load(open(f"{ROOT}/монтаж_слова/ЭТО_ВИДЕО_НА_МОНТАЖ.words.json", encoding="utf-8"))["words"]
groups, cur = [], []
for w in words:
    cur.append(w)
    if w["word"][-1] in ".?!":
        groups.append(cur); cur = []
if cur:
    groups.append(cur)
assert len(groups) == 18, len(groups)
chunks = [[0, 1], [2], [3], [4], [5], [6], [7], [8], [9], [10], [11], [12], [13], [14, 15], [16], [17]]
speech = [(SIL[i][1], SIL[i + 1][0]) for i in range(len(SIL) - 1)]
assert len(chunks) == len(speech) == 16
for ch, (ta, tb) in zip(chunks, speech):
    ws = [w for g in ch for w in groups[g]]
    w0, w1 = ws[0]["start"], ws[-1]["end"]
    for w in ws:
        w["s"] = ta + (w["start"] - w0) * (tb - ta) / (w1 - w0)
        w["e"] = ta + (w["end"] - w0) * (tb - ta) / (w1 - w0)

# страницы субтитров: (группа, с слова, по слово, разметка; *красный*)
PAGES = [
    (0, 0, 3, "*20 000* долларов."), (1, 0, 5, "Вот столько зарабатывает этот канал."),
    (2, 0, 4, "Он набирает *миллионы* просмотров."), (3, 0, 8, "Вот сколько YouTube платит за *1 миллион* просмотров."),
    (4, 0, 13, "И что, если я скажу, что ты можешь делать *точно так же*?"),
    (5, 0, 2, "Открываешь *ChatGPT*."), (6, 0, 4, "Просишь написать *вирусный* сценарий."),
    (7, 0, 1, "Копируешь."), (8, 0, 3, "Заходишь в *Forge Vision*."),
    (9, 0, 3, "Вставляешь скопированный текст."), (10, 0, 2, "Выбираешь *формат*."),
    (11, 0, 2, "Выбираешь *стиль*."), (12, 0, 4, "И жмёшь на *кнопку*."),
    # группы 13-15 — отрезок готового ролика: по просьбе пользователя без субтитров
    (16, 0, 8, "И ты можешь попробовать сделать такое же видео"), (16, 8, 10, "*абсолютно бесплатно*."),
    (17, 0, 7, "Ссылка на софт *в шапке профиля*."),
]
font = ImageFont.truetype(FONT_B, 42)
RED, CREAM = (255, 61, 46, 255), (244, 238, 228, 255)


def plate(markup):
    # слово = набор кусочков (текст, цвет); пробел только между словами, пунктуация остаётся у слова
    toks, cur, red = [], [], False
    for ch in markup:
        if ch == "*":
            red = not red
        elif ch.isspace():
            if cur:
                toks.append(cur); cur = []
        else:
            if cur and cur[-1][1] == (RED if red else CREAM):
                cur[-1] = (cur[-1][0] + ch, cur[-1][1])
            else:
                cur.append((ch, RED if red else CREAM))
    if cur:
        toks.append(cur)
    maxw, sp = 900, font.getlength(" ")
    lines, line, lw = [], [], 0
    for t in toks:
        tw = sum(font.getlength(x[0]) for x in t)
        if line and lw + sp + tw > maxw:
            lines.append((line, lw)); line, lw = [], 0
        lw += (sp if line else 0) + tw; line.append((t, tw))
    lines.append((line, lw))
    # две строки ровнее: если вторая очень короткая — не трогаем (по смыслу), просто центрируем
    lh = 56
    pw = int(max(l[1] for l in lines)) + 2 * 30 + 8
    ph = lh * len(lines) + 2 * 18
    img = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    m = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, pw - 1, ph - 1], 14, fill=255)
    layer = Image.new("RGBA", (pw, ph), (12, 11, 11, 219))        # #0c0b0b, ~86 %
    ImageDraw.Draw(layer).rectangle([0, 0, 5, ph], fill=RED)       # красная полоса слева
    img.paste(layer, (0, 0), m)
    d = ImageDraw.Draw(img)
    for li, (ln, lw) in enumerate(lines):
        x = 8 + (pw - 8 - lw) / 2
        for segs, tw in ln:
            xx = x
            for txt, col in segs:
                d.text((xx, 18 + li * lh + 2), txt, font=font, fill=col)
                xx += font.getlength(txt)
            x += tw + sp
    return img

SUB_BOTTOM = 1574        # ~18 % от низа, над зоной интерфейса
overlays = []            # (png, x, y, f0, f1, fade)
overlays.append((f"{OUT}/card_banner.png", 40, BANNER_Y, new_f(groups[1][0]["s"] if "s" in groups[1][0] else 2.1), S[0]["f1"], True))
overlays.append((f"{OUT}/card_chatgpt.png", 220, CHAT_Y, S[4]["f0"], S[4]["f1"], True))
page_info = []
for n, (g, i0, i1, mk) in enumerate(PAGES):
    ws = groups[g][i0:i1]
    f0, f1 = new_f(ws[0]["s"]), new_f(ws[-1]["e"])
    im = plate(mk)
    p = f"{OUT}/sub_{n:02d}.png"; im.save(p)
    overlays.append((p, (W - im.size[0]) // 2, SUB_BOTTOM - im.size[1], f0, f1, False))
    page_info.append((mk.replace("*", ""), f0 / FPS, f1 / FPS))
json.dump(page_info, open(f"{OUT}/subs.json", "w"), ensure_ascii=False, indent=1)
print(f"карточки: баннер y={BANNER_Y}, ChatGPT y={CHAT_Y}; страниц субтитров: {len(PAGES)}")

# ---------------------------------------------------------------- 7. наложение, звук, экспорт
dur = NEW_TOTAL / FPS
inp = ["-i", stage2]
fp, last = [], "[0:v]"
for k, (png, x, y, f0, f1, fade) in enumerate(overlays, 1):
    inp += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", png]
    chain = f"[{k}:v]format=rgba,scale=out_color_matrix=bt709:out_range=tv,format=yuva420p"
    if fade:
        chain += f",fade=t=in:st={f0/FPS:.3f}:d=0.16:alpha=1,fade=t=out:st={f1/FPS - 0.16:.3f}:d=0.16:alpha=1"
    fp.append(chain + f"[p{k}]")
    fp.append(f"{last}[p{k}]overlay={x}:{y}:enable='between(n,{f0},{f1 - 1})'[o{k}]")
    last = f"[o{k}]"
fp.append(f"{last}setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv[vout]")
vid = f"{OUT}/video_final_noaudio.mp4"
run(["ffmpeg", "-nostdin", "-y", "-v", "error", *inp, "-filter_complex", ";".join(fp), "-map", "[vout]",
     "-r", str(FPS), "-c:v", "libx264", "-profile:v", "high", "-b:v", "20M", "-maxrate", "24M", "-bufsize", "40M",
     "-preset", "medium", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
     "-color_trc", "bt709", "-t", f"{dur:.3f}", vid])
print("наложение готово")

# громкость ≈ −14 LUFS (двухпроходная)
m = run(["ffmpeg", "-nostdin", "-i", base_a, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"]).stderr
j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
      f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
final = f"{OUT}/рилс_две-крупности_v1.mp4"
run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", vid, "-i", base_a, "-af", ln, "-map", "0:v", "-map", "1:a",
     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", final])
print("ГОТОВО:", final, f"{os.path.getsize(final)/1e6:.1f} МБ, {dur:.2f} с")
