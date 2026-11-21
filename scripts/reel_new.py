#!/usr/bin/env python3
"""Новый рилс по монтажу конкурента: аватар (начало/середина/конец) + записи экрана + готовый ролик,
паузы 0.12 с, субтитры как у конкурента (сентенс-кейс, 2–4 слова, белый с обводкой, ~70 % высоты),
заголовок «Подработка ❌ / Forge Vision ✅», панель с цифрами, призыв в конце.
Запуск: /home/user/gigaam-venv/bin/python scripts/reel_new.py
Исходники не трогаются, результат в монтаж_2026-11-19/новый_рилс/."""
import json, os, re, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FPS, W, H = 25, 1080, 1920
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AV = f"{ROOT}/исходники/новый_рилс/avatar.mp4"
CL = f"{ROOT}/исходники/новый_рилс"
RESULT = f"{ROOT}/монтаж_2026-11-19/вставка/бессмертный_без_плашки.mp4"
OUT = f"{ROOT}/монтаж_2026-11-19/новый_рилс"; os.makedirs(OUT, exist_ok=True)
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
total_f = int(TOTAL * FPS); cf[-1] = (cf[-1][0], total_f)
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
words = json.load(open(f"{ROOT}/монтаж_слова/avatar.words.json", encoding="utf-8"))["words"]
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
    ("avatar", 0.0, bd(14, 15), {"name": "start"}),
    ("clip", bd(14, 15), sT(18), {"file": "VID_20261119_181205_083.mp4", "lead": True}),
    ("clip", sT(18), sT(26), {"file": "VID_20261119_181204_519.mp4"}),
    ("clip", sT(26), bd(30, 31), {"file": "VID_20261119_181204_353.mp4"}),
    ("clip", bd(30, 31), sT(38), {"file": "VID_20261119_181215_394.mp4", "lead": True, "cy": 1570}),
    ("clip", sT(38), bd(42, 43), {"file": "VID_20261119_181215_423.mp4", "cy": 1700}),
    ("avatar", bd(42, 43), bd(58, 59), {}),
    ("clip", bd(58, 59), bd(79, 80), {"file": "VID_20261119_181223_536.mp4", "lead": True, "cy": 1690}),
    ("result", bd(79, 80), bd(89, 90), {"lead": True}),
    ("avatar", bd(89, 90), bd(110, 111), {}),
    ("clip", bd(110, 111), bd(124, 125), {"file": "VID_20261119_181229_546.mp4", "lead": True}),
    ("avatar", bd(124, 125), TOTAL, {"name": "end"}),
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
        d = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{CL}/{bl['file']}"]).stdout)
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
        parts.append(f"[{k}:v]trim=end_frame={n},setpts=PTS-STARTPTS,scale={W}:{H}:flags=lanczos,format=yuv420p,setsar=1[v{i}]")
    else:
        k = len(inputs) // 2; inputs += ["-i", f"{CL}/{bl['file']}"]
        parts.append(f"[{k}:v]setpts=(PTS-STARTPTS)/{bl['speed']:.5f},fps={FPS},tpad=stop_mode=clone:stop_duration=3,trim=end_frame={n},"
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
            return bl.get("cy", 1344)                           # ~70 % высоты, как у конкурента
    return 1344


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
title = text_layer(["Подработка", "Forge Vision"], 66, 6, emojis=["❌", "✅"])

# субтитры: (слова от, до, текст)
CAPS = [
    (0, 2, "Каждый день,"), (2, 4, "каждую неделю,"), (4, 6, "каждый месяц"),
    (6, 9, "Тебе не нужно"), (9, 11, "искать подработку,"), (11, 13, "просто сделай"), (13, 15, "вот это"),
    (15, 18, "Зайди на YouTube"), (18, 21, "и поищи вирусные"), (21, 24, "видео в стиле"), (24, 26, "«что если»"),
    (26, 28, "Посмотри, сколько"), (28, 31, "они набирают просмотров"),
    (31, 34, "Вот сколько YouTube"), (34, 38, "платит за миллион просмотров,"), (38, 41, "а вот столько"), (41, 43, "платит TikTok"),
    (43, 46, "И вот как"), (46, 49, "ты можешь сделать"), (49, 52, "то же самое,"), (52, 54, "чтобы получить"),
    (54, 57, "выплаты на всех"), (57, 59, "этих платформах"),
    (59, 62, "Зайди в софт"), (62, 64, "Forge Vision,"), (64, 67, "вставь этот текст,"), (67, 69, "выбери формат,"),
    (69, 72, "который тебе нужен,"), (72, 76, "и выбери этот стиль"),
    (76, 79, "И просто нажми"), (79, 80, "«Сгенерировать»"),
    (80, 84, "И через несколько минут"), (84, 87, "ты получишь видео"), (87, 90, "прямо как это"),
    (90, 92, "Остаётся только"), (92, 95, "выставить этот ролик"), (95, 99, "на YouTube и TikTok,"), (99, 102, "чтобы собрать охваты"),
    (102, 106, "И это не обязательно"), (106, 108, "должна быть"), (108, 111, "именно эта ниша"),
    (111, 114, "Ты можешь делать"), (114, 117, "ролики с абсолютно"), (117, 119, "разными стилями"),
    (119, 122, "В Forge Vision"), (122, 125, "их больше 50"),
    (125, 127, "Хочешь сделать"), (127, 130, "такой же контент?"),
    (130, 133, "Забирай демо-доступ"), (133, 135, "по ссылке"), (135, 138, "в шапке профиля"),
]
cap_img = {}
caps = []
for k, (i0, i1, t) in enumerate(CAPS):
    f0 = new_f(sT(i0)); nxt = CAPS[k + 1] if k + 1 < len(CAPS) else None
    f1 = new_f(sT(nxt[0])) if (nxt and nxt[0] == i1 and sT(nxt[0]) - eT(i1 - 1) < 0.4) else new_f(eT(i1 - 1))
    caps.append([f0, max(f1, f0 + 2), t])
for a, b in zip(caps, caps[1:]):
    if a[1] > b[0]: a[1] = b[0]
text_layer_cache = {}
for _, _, t in caps:
    if t not in text_layer_cache:
        lyr = text_layer([t], 54, 5, width=W); text_layer_cache[t] = lyr.crop((0, 0, W, 54 + 40 + 20))
CAPH = 54 + 60
cta = text_layer([[("Демо-доступ", GREEN)], [("в шапке профиля", WHITE)]], 72, 6)
cta_f0 = new_f(sT(125))
panel_t = {k: sT(i) for k, i in dict(day=0, week=2, month=4, job=6).items()}
f_panel_end = next(bl for bl in B if bl.get("name") == "start")["f1"]
title_end = f_panel_end

CARD = (35, 668, 305, 808)               # над кончиком пальца (палец поднят слева от головы, кончик ≈ x300, y850–950)
TAIL_X = 290                              # куда «показывает» хвостик карточки
card_end = new_f(sT(8))                     # держим до «нужно»: 11 250 $ успевает дойти и прочитаться


def lerp_int(a, b, u): return int(round(a + (b - a) * min(max(u, 0), 1)))
def fmt(n): return f"{n:,}".replace(",", " ")


def fit(text, maxw, size):
    while fnt(size).getlength(text) > maxw and size > 30: size -= 2
    return fnt(size)


def draw_card(img, f):
    t = f / FPS
    life_in = min(1.0, (t - 0.05) / 0.14); life_out = min(1.0, max(0.0, (card_end - f) / FPS / 0.14))
    al, sc = min(life_in, life_out), 0.88 + 0.12 * max(min(life_in, 1.0), 0)
    w_, h_ = CARD[2] - CARD[0], CARD[3] - CARD[1]
    layer = Image.new("RGBA", (w_, h_ + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    d.rounded_rectangle([0, 0, w_ - 1, h_ - 1], 24, fill=(188, 217, 245, 255), outline=(255, 255, 255, 140), width=3)
    tx = TAIL_X - CARD[0]
    d.polygon([(tx - 18, h_ - 3), (tx + 18, h_ - 3), (tx, h_ + 24)], fill=(188, 217, 245, 255))   # хвостик на палец
    if t < panel_t["week"]:
        big, small = f"{lerp_int(354, 375, (t - 0.1) / 0.3)} $", None
    elif t < panel_t["month"]:
        big, small = f"{fmt(lerp_int(1300, 2625, (t - panel_t['week']) / 0.3))} $", "375 $ × 7"
    else:
        big, small = f"{fmt(lerp_int(6954, 11250, (t - panel_t['month']) / 0.3))} $", "375 $ × 30"
    fb = fit("11 250 $", w_ - 30, 78)
    if small:
        d.text((w_ / 2, h_ * 0.24), small, font=fit(small, w_ - 50, 32), fill=(60, 80, 105, 255), anchor="mm")
        d.text((w_ / 2, h_ * 0.62), big, font=fb, fill=(15, 15, 15, 255), anchor="mm")
    else:
        d.text((w_ / 2, h_ * 0.5), big, font=fit("375 $", w_ - 30, 84), fill=(15, 15, 15, 255), anchor="mm")
    if sc < 1: layer = layer.resize((int(layer.size[0] * sc), int(layer.size[1] * sc)), Image.LANCZOS)
    if al < 1:
        arr = np.array(layer); arr[..., 3] = (arr[..., 3] * al).astype(np.uint8); layer = Image.fromarray(arr)
    # якорь — кончик хвостика (TAIL_X, CARD[3]+26)
    ax, ay = TAIL_X, CARD[3] + 24
    img.alpha_composite(layer, (int(ax - (tx * sc)), int(ay - layer.size[1])))


def faded(im, al):
    a = np.array(im); a[..., 3] = (a[..., 3] * al).astype(np.uint8); return Image.fromarray(a)


def paste_center(img, lyr, cx, cy):
    """вставка с центром в (cx, cy); если слой шире кадра — обрезаем по бокам"""
    if lyr.size[0] > W:
        x0 = (lyr.size[0] - W) // 2; lyr = lyr.crop((x0, 0, x0 + W, lyr.size[1]))
    img.alpha_composite(lyr, (cx - lyr.size[0] // 2, cy - lyr.size[1] // 2))


def frame_overlay(f):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if f < title_end:
        al = min(1.0, (f / FPS + 0.04) / 0.12)
        img.alpha_composite(title if al >= 1 else faded(title, al), (0, 270))
    if f < card_end:
        draw_card(img, f)
    for f0, f1, t in caps:
        if f0 <= f < f1:
            e = (f - f0) / FPS; sc = 1 + 0.10 * (1 - min(e / 0.10, 1)) ** 2
            lyr = text_layer_cache[t]
            if sc > 1.001: lyr = lyr.resize((int(W * sc), int(lyr.size[1] * sc)), Image.LANCZOS)
            paste_center(img, lyr, W // 2, cy_for(f))
            break
    if f >= cta_f0:
        e = (f - cta_f0) / FPS; sc = 1 + 0.20 * (1 - min(e / 0.13, 1)) ** 2
        c = cta if sc <= 1.001 else cta.resize((int(W * sc), int(cta.size[1] * sc)), Image.LANCZOS)
        paste_center(img, c, W // 2, 1000)
    return img


# ----------------------------------------------------------------------- 7. наложение + звук + экспорт
vid = f"{OUT}/video_noaudio.mp4"
dur = NEW_TOTAL / FPS
enc = subprocess.Popen(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", stage2,
                        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-filter_complex", "[1:v]format=rgba,scale=out_color_matrix=bt709:out_range=tv,format=yuva420p[o];"
                        "[0:v][o]overlay=0:0:format=auto,setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv[v]",
                        "-map", "[v]", "-r", str(FPS), "-c:v", "libx264", "-profile:v", "high", "-b:v", "20M", "-maxrate", "24M",
                        "-bufsize", "40M", "-preset", "medium", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
                        "-color_trc", "bt709", "-t", f"{dur:.3f}", vid], stdin=subprocess.PIPE)
for f in range(NEW_TOTAL):
    enc.stdin.write(frame_overlay(f).tobytes())
enc.stdin.close(); enc.wait()
print("наложение готово")

# музыка: трек пользователя (если есть), иначе синтезированный запасной
TRACK = f"{ROOT}/исходники/музыка/music_source.mp4"
MIX_DB = float(os.environ.get("MIX_DB", "-11"))
if os.path.exists(TRACK):
    music = f"{OUT}/music_track.wav"
    START = float(os.environ.get("TRACK_START", "0"))           # откуда брать трек (с); 0 = его собственное нарастание
    run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-ss", f"{START}", "-i", TRACK, "-t", f"{dur + 0.5:.2f}", "-vn", "-ac", "2", "-ar", "44100", music])
    final = f"{OUT}/рилс_новый_v3_трек.mp4"
else:
    music = f"{OUT}/music.wav"
    run([sys.executable, f"{ROOT}/scripts/music_hype.py", f"{dur + 0.5:.2f}", music])
    final = f"{OUT}/рилс_новый_v2_музыка.mp4"
af = (f"[1:a]afade=t=out:st={dur - 1.4:.2f}:d=1.4,volume={MIX_DB}dB[m];[2:a]asplit=2[v][vs];"
      "[m][vs]sidechaincompress=threshold=0.035:ratio=4:attack=12:release=240[md];"
      "[v][md]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", vid, "-i", music, "-i", base_a, "-filter_complex", af, "-map", "0:v", "-map", "[a]",
     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{dur:.3f}", final])
json.dump({"caps": [[a / FPS, b / FPS, t] for a, b, t in caps], "blocks": B},
          open(f"{OUT}/timeline.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ГОТОВО:", final, f"{os.path.getsize(final)/1e6:.1f} МБ, {dur:.2f} с")
