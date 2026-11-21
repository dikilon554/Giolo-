#!/usr/bin/env python3
"""Рилс №3 (канал «Записки выжившего»), свой динамичный монтаж без заголовка. База: reel_new.py. Старое описание: аватар (начало/середина/конец) + записи экрана + готовый ролик,
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
AV = f"{ROOT}/исходники/рилс3/avatar3.mp4"
CL = f"{ROOT}/исходники/рилс3"
RESULT = f"{CL}/VID_20261121_143255_332.mp4"
OUT = f"{ROOT}/монтаж_2026-11-21/рилс3"; os.makedirs(OUT, exist_ok=True)
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
_wl = json.load(open(f"{ROOT}/монтаж_слова/avatar3.words.json", encoding="utf-8"))["words"][-1]["end"]
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
words = json.load(open(f"{ROOT}/монтаж_слова/avatar3.words.json", encoding="utf-8"))["words"]
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
blocks = [  # (тип, t0, t1, параметры); zoom — крупность аватара (смена по фразам, не по битам)
    ("avatar", 0.0, bd(8, 9), {"zoom": 1.12}),
    ("avatar", bd(8, 9), bd(18, 19), {"zoom": 1.0, "name": "banner"}),
    ("clip", bd(18, 19), bd(22, 23), {"file": "VID_20261121_143240_647.mp4", "lead": True}),
    ("clip", bd(22, 23), bd(30, 31), {"file": "VID_20261121_143240_637.mp4", "lead": True, "cy": 1790}),
    ("avatar", bd(30, 31), bd(37, 38), {"zoom": 1.12}),
    ("avatar", bd(37, 38), bd(40, 41), {"zoom": 1.0, "name": "chatgpt"}),
    ("clip", bd(40, 41), bd(44, 45), {"file": "VID_20261121_143244_719.mp4", "lead": True, "cy": 1680}),
    ("clip", bd(44, 45), bd(45, 46), {"file": "VID_20261121_143243_838.mp4", "ss": 1.0, "cy": 1680}),
    ("clip", bd(45, 46), bd(59, 60), {"file": "VID_20261121_143247_780.mp4", "lead": True, "cy": 1690}),
    ("result", bd(59, 60), bd(66, 67), {"lead": True}),
    ("avatar", bd(66, 67), bd(73, 74), {"zoom": 1.12}),
    ("avatar", bd(73, 74), TOTAL, {"zoom": 1.0, "name": "end"}),
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
        parts.append(f"[{k}:v]fps={FPS},trim=end_frame={n},setpts=PTS-STARTPTS,scale={W}:{H}:flags=lanczos,format=yuv420p,setsar=1[v{i}]")
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


# субтитры: (слова от, до, текст)
CAPS = [
    (0, 3, "Никогда не думал,"), (3, 6, "что так легко"), (6, 9, "можно зарабатывать деньги"),
    (9, 11, "Сейчас покажу,"), (11, 14, "как этот канал"), (14, 17, "зарабатывает тысячи долларов"), (17, 19, "каждый месяц"),
    (19, 21, "Он набирает"), (21, 23, "миллионы просмотров"),
    (23, 26, "Вот сколько YouTube"), (26, 28, "платит за"), (28, 31, "один миллион просмотров"),
    (31, 34, "И ты можешь"), (34, 38, "делать точно так же"),
    (38, 41, "Открываешь ChatGPT"),
    (41, 43, "Просишь написать"), (43, 45, "вирусный сценарий"),
    (45, 46, "Копируешь"),
    (46, 49, "Заходишь в Forge Vision"),
    (49, 52, "Вставляешь скопированный текст"),
    (52, 54, "Выбираешь формат"), (54, 56, "Выбираешь стиль"), (56, 60, "И жмёшь на кнопку"),
    (67, 71, "Выставляешь его на YouTube"), (71, 74, "И собираешь просмотры"),
    (74, 78, "И ты можешь попробовать"), (78, 81, "сделать такое же"), (81, 83, "видео бесплатно"),
    (83, 87, "Ссылка в шапке профиля"),
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
cta_f0 = new_f(sT(83))
def rcard(path, size, r=22):
    im = Image.open(path).convert("RGB").resize(size, Image.LANCZOS)
    m = Image.new("L", size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], r, fill=255)
    o = im.convert("RGBA"); o.putalpha(m); ImageDraw.Draw(o).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], r, outline=(244, 238, 228, 90), width=2)
    return o


_b = Image.open(f"{CL}/IMG_20261121_143230_904.jpg").convert("RGB").crop((0, 0, 1050, 365)); _b.save(f"{OUT}/_banner_crop.png")
banner = rcard(f"{OUT}/_banner_crop.png", (620, 216))
chatlogo = rcard(f"{ROOT}/исходники/chatgpt_logo.png", (640, 360), 26)
bl_ban = next(bl for bl in B if bl.get("name") == "banner"); bl_chat = next(bl for bl in B if bl.get("name") == "chatgpt")
BAN_POS, CHAT_POS = (230, 196), (220, 60)


def card_alpha(f, f0, f1):
    return min(1.0, (f - f0 + 1) / (0.14 * FPS), (f1 - f) / (0.12 * FPS))


def faded(im, al):
    a = np.array(im); a[..., 3] = (a[..., 3] * al).astype(np.uint8); return Image.fromarray(a)


def paste_center(img, lyr, cx, cy):
    """вставка с центром в (cx, cy); если слой шире кадра — обрезаем по бокам"""
    if lyr.size[0] > W:
        x0 = (lyr.size[0] - W) // 2; lyr = lyr.crop((x0, 0, x0 + W, lyr.size[1]))
    img.alpha_composite(lyr, (cx - lyr.size[0] // 2, cy - lyr.size[1] // 2))


def frame_overlay(f):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for bl_, im_, pos in ((bl_ban, banner, BAN_POS), (bl_chat, chatlogo, CHAT_POS)):
        if bl_["f0"] <= f < bl_["f1"]:
            img.alpha_composite(faded(im_, max(0.0, card_alpha(f, bl_["f0"], bl_["f1"]))), pos)
    for f0, f1, t in caps:
        if f0 <= f < f1:
            e = (f - f0) / FPS; sc = 1 + 0.16 * (1 - min(e / 0.12, 1)) ** 2
            lyr = text_layer_cache[t]
            if sc > 1.001: lyr = lyr.resize((int(W * sc), int(lyr.size[1] * sc)), Image.LANCZOS)
            paste_center(img, lyr, W // 2, cy_for(f))
            break
    if f >= cta_f0:
        e = (f - cta_f0) / FPS; sc = 1 + 0.20 * (1 - min(e / 0.13, 1)) ** 2
        c = cta if sc <= 1.001 else cta.resize((int(W * sc), int(cta.size[1] * sc)), Image.LANCZOS)
        paste_center(img, c, W // 2, 330)
    return img


# ----------------------------------------------------------------------- 7. наложение, динамика, звук, экспорт
vid = f"{OUT}/video_noaudio.mp4"
dur = NEW_TOTAL / FPS
TRACK = f"{ROOT}/исходники/музыка/music_source.mp4"
beats_json = f"{OUT}/beats.json"
if os.path.exists(TRACK) and not os.path.exists(beats_json):
    run([sys.executable, f"{ROOT}/scripts/track_beats.py", TRACK, beats_json])
bj = json.load(open(beats_json)) if os.path.exists(beats_json) else {"bpm": 123.0, "b0": 0.0, "start": 0.0}
BEAT = 60 / bj["bpm"]
START = float(os.environ.get("TRACK_START", bj["start"]))        # трек стартует на ударе -> удары в ролике: k * BEAT
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

# музыка: начинается ПОСЛЕ слов «просто сделай вот это» (на первой записи экрана), на ударе; тише и не перебивает голос
MIX_DB = float(os.environ.get("MIX_DB", "-9.5"))
t_m = next(bl for bl in B if bl["kind"] == "clip")["f0"] / FPS        # момент вступления музыки = начало первой записи экрана
if os.path.exists(TRACK):
    music = f"{OUT}/music_track.wav"
    run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-ss", f"{START:.3f}", "-i", TRACK, "-t", f"{dur - t_m + 0.5:.2f}", "-vn", "-ac", "2", "-ar", "44100", music])
    final = f"{OUT}/рилс3_v2.mp4"
else:
    music = f"{OUT}/music.wav"
    run([sys.executable, f"{ROOT}/scripts/music_hype.py", f"{dur - t_m + 0.5:.2f}", music])
    final = f"{OUT}/рилс_новый_v2_музыка.mp4"
ms = int(round(t_m * 1000))
af = ("[1:a]highpass=f=40,equalizer=f=60:t=o:w=1.2:g=-2,equalizer=f=2500:t=o:w=1.5:g=3,equalizer=f=5000:t=o:w=2:g=3,highshelf=f=8000:g=7,"
      "acompressor=threshold=-20dB:ratio=3:attack=4:release=90:makeup=4,"
      f"afade=t=in:st=0:d=0.06,afade=t=out:st={dur - t_m - 1.4:.2f}:d=1.4,volume={MIX_DB}dB,adelay={ms}|{ms}[m];[2:a]asplit=2[v][vs];"
      "[m][vs]sidechaincompress=threshold=0.04:ratio=4:attack=12:release=240[md];"
      "[v][md]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", vid, "-i", music, "-i", base_a, "-filter_complex", af, "-map", "0:v", "-map", "[a]",
     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{dur:.3f}", final])
print(f"музыка вступает на {t_m:.2f} с")
json.dump({"caps": [[a / FPS, b / FPS, t] for a, b, t in caps], "blocks": B},
          open(f"{OUT}/timeline.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ГОТОВО:", final, f"{os.path.getsize(final)/1e6:.1f} МБ, {dur:.2f} с")
