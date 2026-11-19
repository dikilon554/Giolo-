#!/usr/bin/env python3
"""Рилс v2: динамичнее. Паузы 0.12 с, крупные планы в два размера с «наездом», субтитры-крупные слова (по 1–2),
баннер у плеча, новые вставки ChatGPT. Без музыки.
Запуск: /home/user/gigaam-venv/bin/python scripts/montage2.py
Исходники не трогаются, всё пишется в монтаж_2026-11-19/v2/.
"""
import json, os, subprocess, sys
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

FPS = 25
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = f"{ROOT}/исходники"
MAIN = f"{SRC}/ЭТО ВИДЕО НА МОНТАЖ"
OUT = f"{ROOT}/монтаж_2026-11-19/v2"
FONT_UB = f"{ROOT}/assets/fonts/Unbounded_900Black.ttf"
W, H = 1080, 1920
os.makedirs(OUT, exist_ok=True)


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit("FFMPEG FAIL:\n" + " ".join(map(str, cmd))[:500] + "\n" + r.stderr[-2500:])
    return r


# ------------------------------------------------------------ 1. резки (остаётся 0.12 с в каждой паузе)
SIL = [(0, 0.318), (3.858, 4.519), (6.223, 6.452), (8.747, 9.413), (12.513, 13.143),
       (14.598, 14.869), (16.754, 17.091), (17.841, 18.215), (19.358, 19.697),
       (21.082, 21.634), (22.56, 22.927), (23.734, 24.116), (25.218, 25.778),
       (27.536, 27.893), (30.498, 31.067), (34.613, 34.855), (36.829, 37.207)]
KEEP, TOTAL = 0.12, 37.207
fr = lambda t: int(round(t * FPS))
cuts = [(0.0, 0.28)]
for a, b in SIL[1:-1]:
    if (b - a) - KEEP >= 0.04:
        cuts.append((a + KEEP / 2, b - KEEP / 2))
cuts.append((36.98, TOTAL))
cuts_f = [(fr(a), fr(b)) for a, b in cuts]
total_f = int(TOTAL * FPS)
cuts_f[-1] = (cuts_f[-1][0], total_f)
kept, pos = [], 0
for a, b in cuts_f:
    if a > pos: kept.append((pos, a))
    pos = b
if pos < total_f: kept.append((pos, total_f))


def new_f(t):
    of, removed = fr(t), 0
    for a, b in cuts_f:
        if of >= b: removed += b - a
        elif of > a: removed += of - a
    return of - removed


NEW_TOTAL = sum(b - a for a, b in kept)
print(f"кусков {len(kept)}, снято {(total_f - NEW_TOTAL)/FPS:.2f} с, итого {NEW_TOTAL} кадр. = {NEW_TOTAL/FPS:.2f} с")

# ------------------------------------------------------------ 2. база без пауз
base_v, base_a = f"{OUT}/base_video.mp4", f"{OUT}/base_audio.wav"
if not os.path.exists(base_v):
    vf = ";".join(f"[0:v]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS[v{i}]" for i, (a, b) in enumerate(kept))
    vf += ";" + "".join(f"[v{i}]" for i in range(len(kept))) + f"concat=n={len(kept)}:v=1:a=0[out]"
    run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", MAIN, "-filter_complex", vf, "-map", "[out]", "-r", str(FPS),
         "-c:v", "libx264", "-crf", "8", "-preset", "fast", "-pix_fmt", "yuv420p", base_v])
if not os.path.exists(base_a):
    FD = 0.05  # затухание/нарастание внутри оставленных 0.06 с тишины, не задевая речь
    parts = []
    for i, (a, b) in enumerate(kept):
        s, e = a / FPS, b / FPS
        f = f"[0:a]atrim=start={s:.4f}:end={e:.4f},asetpts=PTS-STARTPTS"
        if i > 0: f += f",afade=t=in:st=0:d={FD}"
        if i < len(kept) - 1: f += f",afade=t=out:st={e - s - FD:.4f}:d={FD}"
        parts.append(f + f"[a{i}]")
    af = ";".join(parts) + ";" + "".join(f"[a{i}]" for i in range(len(kept))) + f"concat=n={len(kept)}:v=0:a=1[out]"
    run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", MAIN, "-filter_complex", af, "-map", "[out]", "-ar", "48000", "-ac", "2", base_a])

# ------------------------------------------------------------ 3. лицо
cap = cv2.VideoCapture(MAIN)
det = cv2.FaceDetectorYN.create(f"{ROOT}/assets/models/face_detection_yunet_2023mar.onnx", "", (W, H), 0.7)
ey, cx = [], []
for t in (10.0, 10.8, 11.5, 12.0, 32.0, 32.8, 33.5, 34.2):
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, img = cap.read()
    if not ok: continue
    _, faces = det.detect(img)
    if faces is None: continue
    ey.append((faces[0][5] + faces[0][7]) / 2); cx.append(faces[0][0] + faces[0][2] / 2)
cap.release()
EYE_Y, FACE_X = float(np.median(ey)), float(np.median(cx))
EYE_T = 0.36 * H          # глаза в крупном плане — на 36 % высоты кадра
print(f"лицо: глаза y={EYE_Y:.0f}, x={FACE_X:.0f}")

# ------------------------------------------------------------ 4. слова и подгонка к реальным границам фраз
words = json.load(open(f"{ROOT}/монтаж_слова/ЭТО_ВИДЕО_НА_МОНТАЖ.words.json", encoding="utf-8"))["words"]
groups, cur = [], []
for w in words:
    cur.append(w)
    if w["word"][-1] in ".?!": groups.append(cur); cur = []
if cur: groups.append(cur)
assert len(groups) == 18
chunks = [[0, 1], [2], [3], [4], [5], [6], [7], [8], [9], [10], [11], [12], [13], [14, 15], [16], [17]]
speech = [(SIL[i][1], SIL[i + 1][0]) for i in range(len(SIL) - 1)]
for ch, (ta, tb) in zip(chunks, speech):
    ws = [w for g in ch for w in groups[g]]
    w0, w1 = ws[0]["start"], ws[-1]["end"]
    for w in ws:
        w["s"] = ta + (w["start"] - w0) * (tb - ta) / (w1 - w0)
        w["e"] = ta + (w["end"] - w0) * (tb - ta) / (w1 - w0)

# ------------------------------------------------------------ 5. раскладка кадров
mid = lambda i: (SIL[i][0] + SIL[i][1]) / 2
T = {k: mid(i) for k, i in dict(g1=1, g2=2, g3=3, g4=4, g5=5, g6=6, g7=7, g12=12, g14=14, g15=15).items()}
T_PROMPT_END = 16.35                           # переход «запрос» -> «копируешь» (на слове «сценарий»)
T_Q = groups[4][5]["s"]                        # «что ты можешь…»: меняем размер крупного плана
T_C = groups[16][8]["s"]                       # «абсолютно бесплатно»: меняем размер крупного плана
LEAD = 3                                       # вставка входит на 3 кадра раньше слова
BANNER_ORIG = 2.8                              # начало жеста пальцем (оригинал, с)

segs = [
    ("wide", 0.0, T["g1"], {"name": "хук"}),
    ("insert", T["g1"], T["g2"], {"file": "VID_20261118_221519_691.mp4", "lead": True}),
    ("insert", T["g2"], T["g3"], {"file": "VID_20261118_221517_648.mp4", "lead": True}),
    ("close", T["g3"], T_Q, {"z": 1.35}),
    ("close", T_Q, T["g4"], {"z": 1.7}),
    ("wide", T["g4"], T["g5"], {"name": "chatgpt-карточка"}),
    ("insert", T["g5"], T_PROMPT_END, {"file": "VID_20261119_111646_050.mp4", "lead": True, "fit": True}),
    ("insert", T_PROMPT_END, T["g7"], {"file": "VID_20261119_111645_166.mp4", "ss": 1.0, "fit": True}),
    ("insert", T["g7"], T["g12"], {"file": "VID_20261118_221528_160.mp4", "lead": True, "fit": True}),
    ("insert", T["g12"], T["g14"], {"file": "VID_20261118_221530_395.mp4", "lead": True, "fit": True, "nosub": True}),
    ("close", T["g14"], T_C, {"z": 1.35}),
    ("close", T_C, T["g15"], {"z": 1.7}),
    ("wide", T["g15"], TOTAL, {"name": "финал"}),
]
S = []
for i, (kind, a, b, p) in enumerate(segs):
    f0 = 0 if i == 0 else S[-1]["f1"]
    f1 = NEW_TOTAL if i == len(segs) - 1 else new_f(b)
    S.append({"kind": kind, "f0": f0, "f1": f1, **p})
for i in range(1, len(S)):                      # вставка раньше слова на LEAD кадров
    if S[i].get("lead"):
        S[i]["f0"] -= LEAD; S[i - 1]["f1"] -= LEAD
for s in S:
    assert s["f1"] > s["f0"]
    if s["kind"] == "insert":
        d = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{SRC}/{s['file']}"]).stdout)
        d -= s.get("ss", 0.0)
        need = (s["f1"] - s["f0"]) / FPS
        ratio = d / need
        s["speed"] = ratio if (s.get("fit") or 0.85 <= ratio <= 1.35) else 1.0
        print(f"  вставка {s['file'][:22]}: нужно {need:.2f} с, клип {d:.2f} с -> x{s['speed']:.2f}")
    print(f"  {s['kind']:6} {s['f0']:4}-{s['f1']:4} ({s['f0']/FPS:5.2f}-{s['f1']/FPS:5.2f} с) {s.get('z','')}")

# ------------------------------------------------------------ 6. крупные планы с «наездом» (точный субпиксельный кроп через OpenCV)
def render_close(idx, s):
    out = f"{OUT}/close_{idx}.mp4"
    n = s["f1"] - s["f0"]
    dec = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-i", base_v, "-vf",
                            f"select='between(n,{s['f0']},{s['f1']-1})',setpts=N/{FPS}/TB,"
                            "scale=in_range=tv:out_range=pc:in_color_matrix=bt709,format=rgb24",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-vf", "scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p",
                            "-c:v", "libx264", "-crf", "8", "-preset", "fast", out], stdin=subprocess.PIPE)
    fs = W * H * 3
    for k in range(n):
        buf = dec.stdout.read(fs)
        if len(buf) < fs: break
        img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        e = k / FPS
        z = s["z"] * (1 + 0.07 * max(0.0, 1 - e / 0.16) ** 2)     # наезд 7 % за 0.16 с (ease-out)
        M = np.float32([[z, 0, W / 2 - FACE_X * z], [0, z, EYE_T - EYE_Y * z]])
        enc.stdin.write(cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE).tobytes())
    enc.stdin.close(); enc.wait(); dec.stdout.close(); dec.wait()
    return out

for i, s in enumerate(S):
    if s["kind"] == "close":
        s["clip"] = render_close(i, s)
print("крупные планы готовы")

# ------------------------------------------------------------ 7. склейка видео
stage2 = f"{OUT}/stage2.mp4"
inputs, parts = ["-i", base_v], []
for i, s in enumerate(S):
    n = s["f1"] - s["f0"]
    if s["kind"] == "wide":
        parts.append(f"[0:v]trim=start_frame={s['f0']}:end_frame={s['f1']},setpts=PTS-STARTPTS,setsar=1[v{i}]")
    elif s["kind"] == "close":
        k = len(inputs) // 2; inputs += ["-i", s["clip"]]
        parts.append(f"[{k}:v]trim=end_frame={n},setpts=PTS-STARTPTS,unsharp=5:5:0.5:5:5:0,setsar=1[v{i}]")
    else:
        k = len(inputs) // 2; inputs += ["-i", f"{SRC}/{s['file']}"]
        ss = f"trim=start={s['ss']},setpts=PTS-STARTPTS," if s.get("ss") else ""
        parts.append(f"[{k}:v]{ss}setpts=(PTS-STARTPTS)/{s['speed']:.5f},fps={FPS},trim=end_frame={n},setpts=PTS-STARTPTS,"
                     f"zscale=w={W}:h={H}:filter=lanczos:matrixin=470bg:matrix=709:rangein=tv:range=tv,format=yuv420p,setsar=1[v{i}]")
fc = ";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(len(S))) + f"concat=n={len(S)}:v=1:a=0[out]"
run(["ffmpeg", "-nostdin", "-y", "-v", "error", *inputs, "-filter_complex", fc, "-map", "[out]", "-r", str(FPS),
     "-c:v", "libx264", "-crf", "10", "-preset", "fast", "-pix_fmt", "yuv420p", stage2])
print("склейка готова")

# ------------------------------------------------------------ 8. карточки
def rounded(img, r, border=None):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], r, fill=255)
    o = img.convert("RGBA"); o.putalpha(m)
    if border: ImageDraw.Draw(o).rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], r, outline=border, width=2)
    return o

ban_src = Image.open(f"{SRC}/IMG_20261118_221512_290.jpg").convert("RGB").crop((0, 0, 700, 314))   # аватар, имя, ник, подписчики
BAN_W, BAN_H = 380, int(380 * 314 / 700)
banner = rounded(ban_src.resize((BAN_W, BAN_H), Image.LANCZOS), 18, (244, 238, 228, 70))
BAN_X, BAN_Y = 690, 540                         # справа от головы, над плечом: сюда он показывает пальцем
chat = rounded(Image.open(f"{SRC}/chatgpt_logo.png").convert("RGB").resize((640, 360), Image.LANCZOS), 26, (244, 238, 228, 70))
banner.save(f"{OUT}/card_banner.png"); chat.save(f"{OUT}/card_chatgpt.png")
CHAT_X, CHAT_Y = 220, 60

# ------------------------------------------------------------ 9. субтитры «крупные слова»: все слова по 1–2
# (группа речи, с слова, по слово, [(текст, красный?)...])
R, N = 1, 0
SUBS = [
    (0, 0, 3, [("20 000", R), ("ДОЛЛАРОВ", N)]),
    (1, 0, 2, [("ВОТ", N), ("СТОЛЬКО", N)]), (1, 2, 3, [("ЗАРАБАТЫВАЕТ", N)]), (1, 3, 5, [("ЭТОТ", N), ("КАНАЛ", R)]),
    (2, 0, 2, [("ОН", N), ("НАБИРАЕТ", N)]), (2, 2, 3, [("МИЛЛИОНЫ", R)]), (2, 3, 4, [("ПРОСМОТРОВ", N)]),
    (3, 0, 2, [("ВОТ", N), ("СКОЛЬКО", N)]), (3, 2, 3, [("YOUTUBE", N)]), (3, 3, 5, [("ПЛАТИТ", N), ("ЗА", N)]),
    (3, 5, 7, [("1 МИЛЛИОН", R)]), (3, 7, 8, [("ПРОСМОТРОВ", N)]),
    (4, 0, 2, [("И", N), ("ЧТО,", N)]), (4, 2, 4, [("ЕСЛИ", N), ("Я", N)]), (4, 4, 5, [("СКАЖУ,", N)]),
    (4, 5, 7, [("ЧТО", N), ("ТЫ", N)]), (4, 7, 9, [("МОЖЕШЬ", N), ("ДЕЛАТЬ", N)]), (4, 9, 10, [("ТОЧНО", R)]), (4, 10, 12, [("ТАК", N), ("ЖЕ?", N)]),
    (5, 0, 1, [("ОТКРЫВАЕШЬ", N)]), (5, 1, 3, [("CHATGPT", R)]),
    (6, 0, 2, [("ПРОСИШЬ", N), ("НАПИСАТЬ", N)]), (6, 2, 3, [("ВИРУСНЫЙ", R)]), (6, 3, 4, [("СЦЕНАРИЙ", N)]),
    (7, 0, 1, [("КОПИРУЕШЬ", N)]),
    (8, 0, 2, [("ЗАХОДИШЬ", N), ("В", N)]), (8, 2, 3, [("FORGE VISION", R)]),
    (9, 0, 1, [("ВСТАВЛЯЕШЬ", N)]), (9, 1, 2, [("СКОПИРОВАННЫЙ", N)]), (9, 2, 3, [("ТЕКСТ", N)]),
    (10, 0, 1, [("ВЫБИРАЕШЬ", N)]), (10, 1, 2, [("ФОРМАТ", R)]),
    (11, 0, 1, [("ВЫБИРАЕШЬ", N)]), (11, 1, 2, [("СТИЛЬ", R)]),
    (12, 0, 2, [("И", N), ("ЖМЁШЬ", N)]), (12, 2, 4, [("НА", N), ("КНОПКУ", R)]),
    # группы 13–15 — готовый ролик: по просьбе пользователя без субтитров
    (16, 0, 2, [("И", N), ("ТЫ", N)]), (16, 2, 3, [("МОЖЕШЬ", N)]), (16, 3, 4, [("ПОПРОБОВАТЬ", N)]), (16, 4, 5, [("СДЕЛАТЬ", N)]),
    (16, 5, 7, [("ТАКОЕ", N), ("ЖЕ", N)]), (16, 7, 8, [("ВИДЕО", N)]), (16, 8, 9, [("АБСОЛЮТНО", N)]), (16, 9, 10, [("БЕСПЛАТНО", R)]),
    (17, 0, 2, [("ССЫЛКА", N), ("НА", N)]), (17, 2, 4, [("СОФТ", N), ("В", N)]), (17, 4, 6, [("ШАПКЕ", R), ("ПРОФИЛЯ", R)]),
]
RED, WHITE, BLACK = (255, 61, 46, 255), (255, 255, 255, 255), (0, 0, 0, 255)
STRIP_W, STRIP_H = W, 380
MAXW = 960


def render_group(toks):
    """слова 1–2 шт. большими буквами; не влезает в 960 px — уменьшаем, потом ставим в две строки"""
    lines = size = None
    for size in range(112, 55, -4):                         # 1) обе (или одна) слов в одну строку
        f = ImageFont.truetype(FONT_UB, size); sp = size * 0.30
        ws = [f.getlength(t) for t, _ in toks]
        if sum(ws) + sp * (len(toks) - 1) <= MAXW:
            lines = [list(zip(toks, ws))]; break
    if lines is None or (len(toks) > 1 and size < 88):       # 2) слишком мелко — по слову в строку, крупнее
        for size in range(112, 55, -4):
            f = ImageFont.truetype(FONT_UB, size); sp = size * 0.30
            ws = [f.getlength(t) for t, _ in toks]
            if max(ws) <= MAXW:
                lines = [[(t, w)] for t, w in zip(toks, ws)]; break
    sw = max(5, int(size * 0.085)); lh = int(size * 1.18)
    img = Image.new("RGBA", (STRIP_W, STRIP_H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    y0 = STRIP_H / 2 - lh * len(lines) / 2
    for li, ln in enumerate(lines):
        tw = sum(w for _, w in ln) + sp * (len(ln) - 1); x = (STRIP_W - tw) / 2
        for (t, red), w in ln:
            d.text((x, y0 + li * lh), t, font=f, fill=RED if red else WHITE, stroke_width=sw, stroke_fill=BLACK)
            x += w + sp
    return img


# время показа групп (оригинал -> новые кадры)
glist = []
for k, (g, i0, i1, toks) in enumerate(SUBS):
    ws = groups[g][i0:i1]
    t0, t1 = ws[0]["s"], ws[-1]["e"]
    nxt = SUBS[k + 1] if k + 1 < len(SUBS) else None
    if nxt and nxt[0] == g and nxt[1] == i1:
        t1 = groups[g][i1]["s"]                       # без мигания: до начала следующей группы той же фразы
    glist.append([new_f(t0), new_f(t1), toks])
for a, b in zip(glist, glist[1:]):
    if a[1] > b[0]: a[1] = b[0]
print(f"групп субтитров: {len(glist)}")

STR = f"{OUT}/strips"; os.makedirs(STR, exist_ok=True)
blank = Image.new("RGBA", (STRIP_W, STRIP_H), (0, 0, 0, 0)); blank.save(f"{STR}/blank.png")
for k in range(NEW_TOTAL):
    p = f"{STR}/s_{k:04d}.png"
    if os.path.lexists(p): os.remove(p)
    os.link(f"{STR}/blank.png", p)
for f0, f1, toks in glist:
    base_img = render_group(toks)
    bb = base_img.getbbox(); sc_max = (W - 24) / (bb[2] - bb[0])       # на пике «выскакивания» не вылезаем за кадр
    for k in range(f0, min(f1, NEW_TOTAL)):
        e = (k - f0) / FPS
        sc = min(1 + 0.25 * max(0.0, 1 - e / 0.13) ** 3, sc_max)      # выскакивает со 125 % до 100 % за 0.13 с
        al = min(1.0, (e + 1 / FPS) / 0.06)
        im = base_img if sc == 1 else base_img.resize((int(STRIP_W * sc), int(STRIP_H * sc)), Image.LANCZOS)
        fr_img = Image.new("RGBA", (STRIP_W, STRIP_H), (0, 0, 0, 0))
        fr_img.paste(im, ((STRIP_W - im.size[0]) // 2, (STRIP_H - im.size[1]) // 2), im)
        if al < 1:
            a_ = np.array(fr_img); a_[..., 3] = (a_[..., 3] * al).astype(np.uint8); fr_img = Image.fromarray(a_)
        p = f"{STR}/s_{k:04d}.png"; os.remove(p); fr_img.save(p)

# высота надписи по частям ролика (обходит руки: хук — ниже рук, финал — выше руки)
def cy_for(frame):
    for s in S:
        if s["f0"] <= frame < s["f1"]:
            if s["kind"] == "wide" and s.get("name") == "хук": return 1450
            if s["kind"] == "wide" and s.get("name") == "финал": return 1170
    return 1250
ycuts, prev = [], None
for k in range(NEW_TOTAL):
    c = cy_for(k)
    if c != prev: ycuts.append((k, c)); prev = c
yexpr = str(ycuts[-1][1] - STRIP_H // 2)
for k, c in reversed(ycuts[:-1]):
    pass
yexpr = ""
for idx in range(len(ycuts) - 1, -1, -1):
    k, c = ycuts[idx]
    yexpr = str(c - STRIP_H // 2) if idx == len(ycuts) - 1 else f"if(lt(n,{ycuts[idx+1][0]}),{c - STRIP_H // 2},{yexpr})"

# ------------------------------------------------------------ 10. наложение, звук, экспорт
dur = NEW_TOTAL / FPS
b0 = new_f(BANNER_ORIG); b1 = S[0]["f1"]
c0, c1 = S[5]["f0"], S[5]["f1"]
inp = ["-i", stage2,
       "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", f"{OUT}/card_banner.png",
       "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", f"{OUT}/card_chatgpt.png",
       "-framerate", str(FPS), "-start_number", "0", "-i", f"{STR}/s_%04d.png"]
conv = "format=rgba,scale=out_color_matrix=bt709:out_range=tv,format=yuva420p"
fp = [f"[1:v]{conv},fade=t=in:st={b0/FPS:.3f}:d=0.14:alpha=1,fade=t=out:st={b1/FPS - 0.1:.3f}:d=0.1:alpha=1[p1]",
      f"[2:v]{conv},fade=t=in:st={c0/FPS:.3f}:d=0.16:alpha=1,fade=t=out:st={c1/FPS - 0.12:.3f}:d=0.12:alpha=1[p2]",
      f"[3:v]{conv}[p3]",
      f"[0:v][p1]overlay={BAN_X}:{BAN_Y}:enable='between(n,{b0},{b1 - 1})'[o1]",
      f"[o1][p2]overlay={CHAT_X}:{CHAT_Y}:enable='between(n,{c0},{c1 - 1})'[o2]",
      f"[o2][p3]overlay=0:'{yexpr}':shortest=1[o3]",
      "[o3]setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv[vout]"]
vid = f"{OUT}/video_final_noaudio.mp4"
run(["ffmpeg", "-nostdin", "-y", "-v", "error", *inp, "-filter_complex", ";".join(fp), "-map", "[vout]", "-r", str(FPS),
     "-c:v", "libx264", "-profile:v", "high", "-b:v", "20M", "-maxrate", "24M", "-bufsize", "40M", "-preset", "medium",
     "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-t", f"{dur:.3f}", vid])
print("наложение готово")

m = run(["ffmpeg", "-nostdin", "-i", base_a, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"]).stderr
j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
      f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
final = f"{OUT}/рилс_две-крупности_v2.mp4"
run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", vid, "-i", base_a, "-af", ln, "-map", "0:v", "-map", "1:a",
     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", final])
json.dump([(a / FPS, b / FPS, " ".join(t for t, _ in toks)) for a, b, toks in glist], open(f"{OUT}/subs.json", "w"), ensure_ascii=False, indent=1)
print("ГОТОВО:", final, f"{os.path.getsize(final)/1e6:.1f} МБ, {dur:.2f} с")
