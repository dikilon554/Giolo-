#!/usr/bin/env python3
"""Рилс №4 (задача «тысяча долларов за минуту»), монтаж по конкуренту: субтитры по одному слову, секундомер, музыка с начала. Основа reel3.py. Старое: Рилс №3 (канал «Записки выжившего»), свой динамичный монтаж без заголовка. База: reel_new.py. Старое описание: аватар (начало/середина/конец) + записи экрана + готовый ролик,
паузы 0.12 с, субтитры как у конкурента (сентенс-кейс, 2–4 слова, белый с обводкой, ~70 % высоты),
заголовок «Подработка ❌ / Forge Vision ✅», панель с цифрами, призыв в конце.
Запуск: /home/user/gigaam-venv/bin/python scripts/reel_new.py
Исходники не трогаются, результат в монтаж_2026-11-19/новый_рилс/."""
import json, os, re, subprocess, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FPS, W, H = 25, 1080, 1920
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AV = f"{ROOT}/исходники/рилс4/avatar4.mp4"
CL = f"{ROOT}/исходники/рилс4"
RESULT = f"{CL}/VID_20261121_154014_938.mp4"
OUT = f"{ROOT}/монтаж_2026-11-21/рилс4"; os.makedirs(OUT, exist_ok=True)
FM = f"{ROOT}/assets/fonts/Montserrat_800ExtraBold.ttf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit("FAIL:\n" + " ".join(map(str, cmd))[:600] + "\n" + r.stderr[-2500:])
    return r


# ----------------------------------------------------------------------- 1. паузы аватара (оставляем 0.12 с)
TOTAL = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", AV]).stdout)
r = run(["ffmpeg", "-nostdin", "-i", AV, "-af", "silencedetect=noise=-35dB:d=0.2", "-f", "null", "-"]).stderr
st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r)]
en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r)]
SIL = list(zip(st, en + [TOTAL] * (len(st) - len(en))))
KEEP = 0.12
fr = lambda t: int(round(t * FPS))
cuts = []
for a, b in SIL:
    d = b - a
    if a < 0.05: cuts.append((0.0, max(b - 0.10, 0.0))); continue
    if b >= TOTAL - 0.05: cuts.append((a + 0.15, TOTAL)); continue
    if d - KEEP >= 0.06: cuts.append((a + KEEP / 2, b - KEEP / 2))
cf = [(fr(a), fr(b)) for a, b in cuts]
total_f = int(TOTAL * FPS)
_wl = json.load(open(f"{ROOT}/монтаж_слова/avatar4.words.json", encoding="utf-8"))["words"][-1]["end"]
if cf[-1][1] < total_f - 3:                                   # хвост после последнего слова (тишина до конца файла)
    cf.append((fr(_wl + 0.15), total_f))
else:
    cf[-1] = (cf[-1][0], total_f)
kept, pos = [], 0
for a, b in cf:
    if a > pos: kept.append((pos, a))
    pos = b
if pos < total_f: kept.append((pos, total_f))
NEW_TOTAL = sum(b - a for a, b in kept)
print(f"резок {len(cf)}, снято {(total_f - NEW_TOTAL)/FPS:.2f} с, ролик {NEW_TOTAL} кадр. = {NEW_TOTAL/FPS:.2f} с")


def new_f(t):
    of, rem = fr(t), 0
    for a, b in cf:
        if of >= b: rem += b - a
        elif of > a: rem += of - a
    return of - rem


# ----------------------------------------------------------------------- 2. аватар без пауз (видео и звук)
base_v, base_a = f"{OUT}/base_avatar.mp4", f"{OUT}/base_audio.wav"
if not os.path.exists(base_v):
    vf = ";".join(f"[0:v]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS[v{i}]" for i, (a, b) in enumerate(kept))
    vf += ";" + "".join(f"[v{i}]" for i in range(len(kept))) + f"concat=n={len(kept)}:v=1:a=0,scale={W}:{H}:flags=lanczos[out]"
    run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", AV, "-filter_complex", vf, "-map", "[out]", "-r", str(FPS),
         "-c:v", "libx264", "-crf", "8", "-preset", "fast", "-pix_fmt", "yuv420p", base_v])
if not os.path.exists(base_a):
    FD, parts = 0.05, []
    for i, (a, b) in enumerate(kept):
        s, e = a / FPS, b / FPS
        f = f"[0:a]atrim=start={s:.4f}:end={e:.4f},asetpts=PTS-STARTPTS"
        if i > 0: f += f",afade=t=in:st=0:d={FD}"
        if i < len(kept) - 1: f += f",afade=t=out:st={e - s - FD:.4f}:d={FD}"
        parts.append(f + f"[a{i}]")
    af = ";".join(parts) + ";" + "".join(f"[a{i}]" for i in range(len(kept))) + f"concat=n={len(kept)}:v=0:a=1[out]"
    run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", AV, "-filter_complex", af, "-map", "[out]", "-ar", "48000", "-ac", "2", base_a])

# ----------------------------------------------------------------------- 3. слова: Whisper -> реальное время (по границам тишины)
words = json.load(open(f"{ROOT}/монтаж_слова/avatar4.words.json", encoding="utf-8"))["words"]
r2 = run(["ffmpeg", "-nostdin", "-i", AV, "-af", "silencedetect=noise=-32dB:d=0.12", "-f", "null", "-"]).stderr
st2 = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r2)]
en2 = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r2)]
SIL2 = list(zip(st2, en2 + [TOTAL] * (len(st2) - len(en2))))      # мягче, чем для резки: только для привязки слов ко времени
X, Y = [0.0], [0.0]
for a, b in SIL2:
    ends = np.array([w["end"] for w in words])
    k = int(np.argmin(np.abs(ends - a)))
    if abs(ends[k] - a) < 0.8 and k + 1 < len(words) and a > 0.05:
        X += [words[k]["end"], words[k + 1]["start"]]; Y += [a, b]
    elif a < 0.05:
        X += [words[0]["start"], words[0]["start"] + 0.0001]; Y += [0.0, b]
X.append(words[-1]["end"]); Y.append(TOTAL)
pairs = sorted(zip(X, Y)); XX, YY = [], []
for x, y in pairs:                                       # оставляем только монотонные якоря
    if not XX or (x > XX[-1] and y > YY[-1]): XX.append(x); YY.append(y)
warp = lambda t: float(np.interp(t, XX, YY))
for w in words: w["s"], w["e"] = warp(w["start"]), warp(w["end"])
sT, eT = (lambda i: words[i]["s"]), (lambda i: words[i]["e"])
print(f"якорей времени: {len(XX)}")

# ----------------------------------------------------------------------- 4. раскладка блоков (по новому времени)
bd = lambda a, b: (eT(a) + sT(b)) / 2                    # граница между фразами = середина паузы
LEAD = 3
blocks = [  # (тип, t0, t1, параметры)
    ("avatar", 0.0, bd(6, 7), {"zoom": 1.12, "name": "watch"}),
    ("clip", bd(6, 7), bd(11, 12), {"file": "VID_20261121_153952_184.mp4", "lead": True, "cy": 1500}),
    ("clip", bd(11, 12), bd(19, 20), {"file": "VID_20261121_153951_913.mp4", "cy": 1500}),
    ("avatar", bd(19, 20), bd(23, 24), {"zoom": 1.0, "name": "chatgpt"}),
    ("clip", bd(23, 24), bd(33, 34), {"file": "VID_20261121_154001_330.mp4", "lead": True, "cy": 1700}),
    ("clip", bd(33, 34), bd(36, 37), {"file": "VID_20261121_154000_994.mp4", "ss": 0.6, "cy": 1700}),
    ("clip", bd(36, 37), bd(52, 53), {"file": "VID_20261121_154009_969.mp4", "lead": True, "cy": 1760}),
    ("result", bd(52, 53), bd(63, 64), {"lead": True, "cy": 1560, "speed": 1.2}),
    ("avatar", bd(63, 64), bd(68, 69), {"zoom": 1.0}),
    ("avatar", bd(68, 69), bd(82, 83), {"zoom": 1.12}),
    ("avatar", bd(82, 83), bd(86, 87), {"zoom": 1.0}),
    ("clip", bd(86, 87), bd(96, 97), {"file": "VID_20261121_154019_791.mp4", "lead": True, "cy": 1700}),
    ("avatar", bd(96, 97), bd(99, 100), {"zoom": 1.12}),
    ("avatar", bd(99, 100), TOTAL, {"zoom": 1.0, "name": "end"}),
]
B = []
for i, (kind, a, b, p) in enumerate(blocks):
    f0 = 0 if i == 0 else B[-1]["f1"]
    f1 = NEW_TOTAL if i == len(blocks) - 1 else new_f(b)
    B.append({"kind": kind, "f0": f0, "f1": f1, **p})
for i in range(1, len(B)):
    if B[i].get("lead"): B[i]["f0"] -= LEAD; B[i - 1]["f1"] -= LEAD
for bl in B:
    if bl["kind"] == "clip":
        d = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{CL}/{bl['file']}"]).stdout) - bl.get("ss", 0.0)
        need = (bl["f1"] - bl["f0"]) / FPS; ratio = d / need
        bl["speed"] = ratio if 0.8 <= ratio <= 1.5 else (0.8 if ratio < 0.8 else 1.0)
        bl["note"] = f"клип {d:.2f} с, нужно {need:.2f} с -> x{bl['speed']:.2f}" + (" +стоп-кадр" if ratio < 0.8 else (" (хвост обрезан)" if ratio > 1.5 else ""))
    print(f"  {bl['kind']:7} {bl['f0']:4}-{bl['f1']:4} ({bl['f0']/FPS:5.2f}-{bl['f1']/FPS:5.2f} с) {bl.get('note','')} {bl.get('file','')[-12:]}")

# ----------------------------------------------------------------------- 5. склейка видео (аватар / записи экрана / результат)
stage2 = f"{OUT}/stage2.mp4"
inputs, parts = ["-i", base_v], []
for i, bl in enumerate(B):
    n = bl["f1"] - bl["f0"]
    if bl["kind"] == "avatar":
        parts.append(f"[0:v]trim=start_frame={bl['f0']}:end_frame={bl['f1']},setpts=PTS-STARTPTS,setsar=1[v{i}]")
    elif bl["kind"] == "result":
        k = len(inputs) // 2; inputs += ["-i", RESULT]
        parts.append(f"[{k}:v]setpts=(PTS-STARTPTS)/{bl.get('speed', 1.0)},fps={FPS},trim=end_frame={n},setpts=PTS-STARTPTS,scale={W}:{H}:flags=lanczos,format=yuv420p,setsar=1[v{i}]")
    else:
        k = len(inputs) // 2; inputs += ["-i", f"{CL}/{bl['file']}"]
        ss_ = f"trim=start={bl['ss']},setpts=PTS-STARTPTS," if bl.get("ss") else ""
        parts.append(f"[{k}:v]{ss_}setpts=(PTS-STARTPTS)/{bl['speed']:.5f},fps={FPS},tpad=stop_mode=clone:stop_duration=3,trim=end_frame={n},"
                     f"setpts=PTS-STARTPTS,zscale=w={W}:h=-2:filter=lanczos:matrixin=470bg:matrix=709:rangein=tv:range=tv,"
                     f"pad={W}:{H}:0:(oh-ih)/2:color=0x0b0b0b,format=yuv420p,setsar=1[v{i}]")
fc = ";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(len(B))) + f"concat=n={len(B)}:v=1:a=0[out]"
run(["ffmpeg", "-nostdin", "-y", "-v", "error", *inputs, "-filter_complex", fc, "-map", "[out]", "-r", str(FPS),
     "-c:v", "libx264", "-crf", "10", "-preset", "fast", "-pix_fmt", "yuv420p", stage2])
print("склейка готова")

# ----------------------------------------------------------------------- 6. графика: заголовок, цифры, субтитры, призыв
def cy_for(frame):
    for bl in B:
        if bl["f0"] <= frame < bl["f1"]:
            return bl.get("cy", 1100)                           # ~57 % высоты, как у конкурента (одно слово над грудью)
    return 1100


def fnt(size): return ImageFont.truetype(FM, size)


def emoji_img(ch, px):
    f = ImageFont.truetype(EMOJI, 109)
    im = Image.new("RGBA", (160, 140), (0, 0, 0, 0)); ImageDraw.Draw(im).text((8, 4), ch, font=f, embedded_color=True)
    bb = im.getbbox(); im = im.crop(bb)
    return im.resize((int(im.size[0] * px / im.size[1]), px), Image.LANCZOS)


def text_layer(lines, size, stroke, shadow=True, colors=None, emojis=None, gap=1.25, width=W):
    """строки по центру: [(текст, цвет)], эмодзи справа от строки"""
    f = fnt(size); lh = int(size * gap); h = lh * len(lines) + 40
    base = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", (width, h), (0, 0, 0, 0)); top = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    for i, ln in enumerate(lines):
        segs = ln if isinstance(ln, list) else [(ln, (255, 255, 255, 255))]
        em = emojis[i] if emojis else None
        e_im = emoji_img(em, int(size * 0.92)) if em else None
        tw = sum(f.getlength(t) for t, _ in segs) + (e_im.size[0] + size * 0.22 if e_im else 0)
        x = (width - tw) / 2; y = 20 + i * lh
        for t, c in segs:
            ImageDraw.Draw(sh).text((x, y + 5), t, font=f, fill=(0, 0, 0, 255), stroke_width=stroke + 1, stroke_fill=(0, 0, 0, 255))
            ImageDraw.Draw(top).text((x, y), t, font=f, fill=c, stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
            x += f.getlength(t)
        if e_im:
            ex, ey = int(x + size * 0.22), int(y + size * 0.1)
            for L in (sh, top):
                L.paste(e_im, (ex, ey), e_im)
    sh = sh.filter(ImageFilter.GaussianBlur(5)); a = np.array(sh); a[..., 3] = (a[..., 3] * 0.55).astype(np.uint8)
    return Image.alpha_composite(Image.fromarray(a), top)


WHITE, GREEN = (255, 255, 255, 255), (60, 220, 110, 255)


# субтитры: (слова от, до, текст)
KEYS = {"тысячу", "долларов", "7", "дней", "монетизация", "бесплатный", "демо", "доступ", "минуту"}
PROPER = {"YouTube", "GPT", "Forge", "Vision"}
MERGE = {22: (22, 23, "ChatGPT")}                     # «чат GPT» -> «ChatGPT»
cap_img = {}
YEL = (255, 214, 10, 255)
caps = []                                              # [f0, f1, текст, жёлтый?]
i = 0
while i < len(words):
    i1, txt = i, re.sub(r"[.,?!«»]", "", words[i]["word"]).strip()
    if i in MERGE: _, i1, txt = MERGE[i]; i1 = i1
    if not txt: i += 1; continue
    key = txt.lower() in KEYS
    show = txt if (txt in PROPER or txt == "ChatGPT") else txt.lower()
    f0 = new_f(sT(i)); last = i1 if i in MERGE else i
    nxt = i1 + 1
    f1 = new_f(sT(nxt)) if (nxt < len(words) and sT(nxt) - eT(last) < 0.3) else new_f(eT(last))
    caps.append([f0, max(f1, f0 + 2), show, key])
    i = i1 + 1
for a_, b_ in zip(caps, caps[1:]):
    if a_[1] > b_[0]: a_[1] = b_[0]
text_layer_cache = {}
for _, _, t, k in caps:
    if (t, k) not in text_layer_cache:
        lyr = text_layer([[(t, YEL if k else (255, 255, 255, 255))]], 84, 8, width=W); text_layer_cache[(t, k)] = lyr.crop((0, 0, W, 84 + 40 + 24))
cta = text_layer([[("Бесплатный", YEL)], [("демо-доступ", YEL)], [("в шапке профиля", (255, 255, 255, 255))]], 72, 6)
cta_f0 = new_f(sT(100))
def rcard(path, size, r=22):
    im = Image.open(path).convert("RGB").resize(size, Image.LANCZOS)
    m = Image.new("L", size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], r, fill=255)
    o = im.convert("RGBA"); o.putalpha(m); ImageDraw.Draw(o).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], r, outline=(244, 238, 228, 90), width=2)
    return o


chatlogo = rcard(f"{ROOT}/исходники/chatgpt_logo.png", (480, 270), 24)
bl_chat = next(bl for bl in B if bl.get("name") == "chatgpt")
CHAT_POS = (300, 150)
bl_watch = next(bl for bl in B if bl.get("name") == "watch")
T_RUN0 = new_f(sT(7))                       # секундомер запускается на «Сначала я зайду на YouTube»
T_WAIT0 = new_f(sT(53))                     # «Немного жду»: счётчик разгоняется
T_STOP = new_f(eT(57))                      # на «И вот он» замирает ровно на 01:00.00
HUD_END = new_f(eT(63)) + 6
fw_big, fw_small = fnt(104), fnt(46)


def card_alpha(f, f0, f1):
    return min(1.0, (f - f0 + 1) / (0.14 * FPS), (f1 - f) / (0.12 * FPS))


def watch_value(f):
    if f < T_WAIT0: return max(0.0, (f - T_RUN0) / FPS)
    base = (T_WAIT0 - T_RUN0) / FPS
    if f >= T_STOP: return 60.0
    u = (f - T_WAIT0) / (T_STOP - T_WAIT0)
    return base + (60.0 - base) * u * u                      # ускорение: «немного подождали до минуты»


def draw_watch(img, f):
    """секундомер как у конкурента: карточка над головой -> крупный счётчик в правом верхнем углу; на «И вот он» ровно 01:00.00"""
    if f >= HUD_END: return
    t = watch_value(f)
    txt = f"{int(t // 60):02d}:{int(t % 60):02d}.{int((t * 100) % 100):02d}"
    frozen = f >= T_STOP
    u = min(1.0, max(0.0, (f - T_RUN0 + 4) / (0.35 * FPS)))
    u = u * u * (3 - 2 * u)
    big, small = (440, 150), (390, 124)
    pop = 1.0 + (0.16 * max(0.0, 1 - (f - T_STOP) / (0.3 * FPS)) if frozen else 0.0)
    w_, h_ = int((big[0] + (small[0] - big[0]) * u) * pop), int((big[1] + (small[1] - big[1]) * u) * pop)
    cx_ = int(540 + (835 - 540) * u); cy_ = int(290 + (100 - 290) * u)
    al = min(1.0, (f + 1) / (0.14 * FPS)) * (1.0 if f < HUD_END - 6 else (HUD_END - f) / 6.0)
    layer = Image.new("RGBA", (w_, h_), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    col = (28, 28, 30, 238); edge = (60, 220, 110, 255) if frozen else (255, 255, 255, 90)
    d.rounded_rectangle([0, 0, w_ - 1, h_ - 1], int(h_ * 0.28), fill=col, outline=edge, width=5 if frozen else 3)
    d.text((w_ / 2, h_ / 2 + 2), txt, font=fnt(int(h_ * 0.54)), fill=(60, 220, 110, 255) if frozen else (255, 255, 255, 255), anchor="mm")
    if al < 1:
        arr = np.array(layer); arr[..., 3] = (arr[..., 3] * max(al, 0)).astype(np.uint8); layer = Image.fromarray(arr)
    img.alpha_composite(layer, (cx_ - w_ // 2, cy_ - h_ // 2))


def faded(im, al):
    a = np.array(im); a[..., 3] = (a[..., 3] * al).astype(np.uint8); return Image.fromarray(a)


def paste_center(img, lyr, cx, cy):
    """вставка с центром в (cx, cy); если слой шире кадра — обрезаем по бокам"""
    if lyr.size[0] > W:
        x0 = (lyr.size[0] - W) // 2; lyr = lyr.crop((x0, 0, x0 + W, lyr.size[1]))
    img.alpha_composite(lyr, (cx - lyr.size[0] // 2, cy - lyr.size[1] // 2))


def frame_overlay(f):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if bl_chat["f0"] <= f < bl_chat["f1"]:
        img.alpha_composite(faded(chatlogo, max(0.0, card_alpha(f, bl_chat["f0"], bl_chat["f1"]))), CHAT_POS)
    draw_watch(img, f)
    for f0, f1, t, k in caps:
        if f0 <= f < f1:
            e = (f - f0) / FPS; sc = 1 + 0.18 * (1 - min(e / 0.10, 1)) ** 2
            lyr = text_layer_cache[(t, k)]
            if sc > 1.001: lyr = lyr.resize((int(W * sc), int(lyr.size[1] * sc)), Image.LANCZOS)
            paste_center(img, lyr, W // 2, cy_for(f))
            break
    if f >= cta_f0:
        e = (f - cta_f0) / FPS; sc = 1 + 0.20 * (1 - min(e / 0.13, 1)) ** 2
        c = cta if sc <= 1.001 else cta.resize((int(W * sc), int(cta.size[1] * sc)), Image.LANCZOS)
        paste_center(img, c, W // 2, 300)
    return img


# ----------------------------------------------------------------------- 7. наложение, динамика, звук, экспорт
vid = f"{OUT}/video_noaudio.mp4"
dur = NEW_TOTAL / FPS
TRACK = f"{ROOT}/исходники/музыка/daphni_poly.mp4"
BEAT, START = 60 / 118.1, 0.0
PULSE = float(os.environ.get("PULSE", "0"))                      # зумы по битам убраны по просьбе                  # «пульс» картинки на каждый удар (доля масштаба)

# смена крупности на аватаре: чётные фразы 1.0x, нечётные 1.10x (мгновенно, без анимированного зума)
punch = np.ones(NEW_TOTAL)
for bl in B:
    if bl["kind"] == "avatar": punch[bl["f0"]:bl["f1"]] = bl.get("zoom", 1.0)


def zoom(img, z):
    if z <= 1.0005: return img
    return cv2.warpAffine(img, np.float32([[z, 0, (1 - z) * W / 2], [0, z, (1 - z) * 930]]), (W, H), flags=cv2.INTER_LINEAR)


dec = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-i", stage2, "-vf",
                        "scale=in_range=tv:out_range=pc:in_color_matrix=bt709,format=rgb24", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-vf", "scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd,format=yuv420p",
                        "-r", str(FPS), "-c:v", "libx264", "-profile:v", "high", "-b:v", "20M", "-maxrate", "24M", "-bufsize", "40M",
                        "-preset", "medium", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-t", f"{dur:.3f}", vid], stdin=subprocess.PIPE)
fsz = W * H * 3
for f in range(NEW_TOTAL):
    buf = dec.stdout.read(fsz)
    if len(buf) < fsz: break
    base = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    t = f / FPS; dt = t % BEAT
    z = punch[f] * (1 + PULSE * np.exp(-dt / 0.11))              # удар -> резкий «прыжок» масштаба, затухает за ~0.2 с
    base = zoom(base, z).copy()
    ov = frame_overlay(f); bb = ov.getbbox()
    if bb:
        a_ = np.asarray(ov.crop(bb)); al = a_[..., 3:4].astype(np.float32) / 255.0
        reg = base[bb[1]:bb[3], bb[0]:bb[2]].astype(np.float32)
        base[bb[1]:bb[3], bb[0]:bb[2]] = (reg * (1 - al) + a_[..., :3].astype(np.float32) * al).astype(np.uint8)
    enc.stdin.write(base.tobytes())
enc.stdin.close(); enc.wait(); dec.stdout.close(); dec.wait()
print("наложение готово")

# музыка: DAPHNI «Poly» с самого начала ролика (как у конкурента), чуть тише голоса, сайдчейн на речи
MIX_DB = float(os.environ.get("MIX_DB", "-12"))
music = f"{OUT}/music_track.wav"
run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-ss", f"{START:.3f}", "-i", TRACK, "-t", f"{dur + 0.5:.2f}", "-vn", "-ac", "2", "-ar", "44100", music])
final = f"{OUT}/рилс4_v2.mp4"
af = (f"[1:a]highpass=f=35,afade=t=in:st=0:d=0.03,afade=t=out:st={dur - 1.4:.2f}:d=1.4,volume={MIX_DB}dB[m];[2:a]asplit=2[v][vs];"
      "[m][vs]sidechaincompress=threshold=0.02:ratio=8:attack=8:release=300[md];"
      "[v][md]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", vid, "-i", music, "-i", base_a, "-filter_complex", af, "-map", "0:v", "-map", "[a]",
     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{dur:.3f}", final])
json.dump({"caps": [[a / FPS, b / FPS, t] for a, b, t, k in caps], "blocks": B},
          open(f"{OUT}/timeline.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ГОТОВО:", final, f"{os.path.getsize(final)/1e6:.1f} МБ, {dur:.2f} с")
