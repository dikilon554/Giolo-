#!/usr/bin/env python3
"""Рилс №13 («Первый миллионер»-аватар с новым хуком 7 с: хук-аватар + основной аватар без первого предложения, затемнение аватара, окна над головой, вставки на весь экран, готовый ролик «Маяк» со звуком, демо CTA). Основа reel12.py и reel9.py. Старое: Рилс №12 («Такие ролики»: хук с окном-роликом «Sarah» со звуком, плашка на хуке, окна-скриншоты дохода, экраны на весь экран, результат «Mona» со звуком, демо CTA). Основа reel11.py. Старое: Рилс №11 («Тот самый друг, 30 тысяч»: хук-плашка, вставки на весь экран после хука, горизонтальный готовый ролик без вшитых субтитров, музыка с начала, демо CTA). Основа reel10.py. Старое: Рилс №10 («Удалю через сутки»: без музыки; плашки-картинки над головой; вставки на весь экран; демо CTA). Основа reel9.py. Старое: Рилс №9 («Первый миллионер»: аватар одним планом, вставки маленькими окнами над головой, выплаты и демо на весь экран). Основа reel8.py. Старое: Рилс №8 («10 тысяч долларов в месяц, ролики без лица», плашка на хуке, музыка с начала, CTA-демо). Основа reel7.py. Старое: Рилс №7 («Свой кусок», YouTube-миллионеры 2027; плашка с логотипами на хуке, плашка дохода, CTA-демо). Основа reel5.py. Старое: Рилс №5 («Хочешь зарабатывать на YouTube, но не хочешь показывать лицо?»; без таймера, белая футболка → серая), CTA демо + клики. Основа reel4_cta.py. Старое: Рилс №4 (задача «тысяча долларов за минуту»), монтаж по конкуренту: субтитры по одному слову, секундомер, музыка с начала. Основа reel3.py. Старое: Рилс №3 (канал «Записки выжившего»), свой динамичный монтаж без заголовка. База: reel_new.py. Старое описание: аватар (начало/середина/конец) + записи экрана + готовый ролик,
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
AV = f"{ROOT}/монтаж_2026-11-26/рилс13/avatar_combined.mp4"
CL = f"{ROOT}/исходники/рилс13"
RESULT = None
GRADE = "eq=brightness=-0.20:contrast=1.22:saturation=0.72:gamma=0.80,colorbalance=rs=-0.05:bs=0.08:rm=-0.04:bm=0.06,vignette=PI/3.8"   # затемнение аватара как у конкурента (вариант B, как в рилсе 9)
OUT = f"{ROOT}/монтаж_2026-11-26/рилс13"; os.makedirs(OUT, exist_ok=True)
FM = f"{ROOT}/assets/fonts/Montserrat_800ExtraBold.ttf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit("FAIL:\n" + " ".join(map(str, cmd))[:600] + "\n" + r.stderr[-2500:])
    return r



# ----------------------------------------------------------------------- 0. склейка аватара: новый хук (7 с) + основной без первого предложения
HOOK_V = f"{CL}/VID_20261126_200050_565.mp4"
MAIN_V = f"{CL}/Как делать видео для YouTube без лица_1080p.mp4"
COMB_W = f"{OUT}/avatar_combined.words.json"
HOOK_END = 6.38                                       # звук хука кончается на 6,38 с (картинка в файле длиннее на 0,8 с)
if not (os.path.exists(AV) and os.path.exists(COMB_W)):
    _m = json.load(open(f"{CL}/монтаж_слова/Как_делать_видео_для_YouTube_без_лица_1080p.words.json", encoding="utf-8"))["words"]
    _h = json.load(open(f"{CL}/монтаж_слова/VID_20261126_200050_565.words.json", encoding="utf-8"))["words"]
    assert _m[14]["word"].startswith("семье") and _m[15]["word"] == "Ты", (_m[14]["word"], _m[15]["word"])
    _rr = run(["ffmpeg", "-nostdin", "-i", MAIN_V, "-af", "silencedetect=noise=-35dB:d=0.2", "-f", "null", "-"]).stderr
    _sa = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", _rr)]; _sb = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", _rr)]
    _mid0 = (_m[14]["end"] + _m[15]["start"]) / 2
    _cut = next(((a + b) / 2 for a, b in zip(_sa, _sb) if a <= _mid0 <= b), _mid0)       # середина паузы между «семье.» и «Ты»
    print(f"основной аватар: убираю 0–{_cut:.2f} с (первое предложение), хук {HOOK_END} с")
    fc0 = (f"[0:v]trim=0:{HOOK_END},setpts=PTS-STARTPTS,scale={W}:{H}:flags=lanczos,fps={FPS},setsar=1,format=yuv420p[hv];"
           f"[1:v]trim=start={_cut:.4f},setpts=PTS-STARTPTS,fps={FPS},setsar=1,format=yuv420p[mv];"
           f"[0:a]atrim=0:{HOOK_END},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo[ha];"
           f"[1:a]atrim=start={_cut:.4f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo[ma];"
           "[hv][ha][mv][ma]concat=n=2:v=1:a=1[v][a]")
    run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", HOOK_V, "-i", MAIN_V, "-filter_complex", fc0, "-map", "[v]", "-map", "[a]", "-r", str(FPS),
         "-c:v", "libx264", "-crf", "8", "-preset", "fast", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
         "-c:a", "aac", "-b:a", "320k", AV])
    _shift = HOOK_END - _cut
    _w = [dict(w) for w in _h] + [{**w, "start": w["start"] + _shift, "end": w["end"] + _shift} for w in _m[15:]]
    json.dump({"words": _w}, open(COMB_W, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"слов в склейке: {len(_w)} (хук {len(_h)} + основной {len(_m) - 15})")

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
_wl = json.load(open(COMB_W, encoding="utf-8"))["words"][-1]["end"]
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
words = json.load(open(COMB_W, encoding="utf-8"))["words"]
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
blocks = [  # слова: индексы avatar_combined.words.json (хук 0–14, дальше те же, что в основном файле)
    ("avatar", 0.0, bd(64, 65), {"zoom": 1.0, "name": "hook"}),
    ("clip", bd(64, 65), bd(71, 72), {"file": "VID_20261126_200821_159.mp4", "ss": 0.3, "speed": 1.0, "cy": 1700}),
    ("clip", bd(71, 72), bd(74, 75), {"file": "ЗАХОД В CHATGPT", "ss": 0.5, "speed": "auto", "cy": 1700}),
    ("clip", bd(74, 75), bd(83, 84), {"file": "VID_20261126_200821_519.mp4", "ss": 0.0, "speed": "auto", "cy": 1700}),
    ("clip", bd(83, 84), bd(84, 85), {"file": "VID_20261126_200820_994.mp4", "ss": 0.5, "speed": 1.0, "cy": 1700}),
    ("clip", bd(84, 85), bd(96, 97), {"file": "VID_20261126_200820_982.mp4", "ss": 0.0, "speed": "auto", "cy": 1700}),
    ("clip", bd(96, 97), bd(99, 100), {"file": "VID_20261126_200821_012.mp4", "ss": "end", "speed": 1.0, "cy": 1700}),
    ("readyh", bd(99, 100), bd(112, 113), {"file": "VID_20261126_200255_476.mp4", "ss": 0.5, "speed": 1.0, "cy": 1560, "crop": "crop=960:720:160:0", "audio": False}),   # «Маяк» без звука (решение пользователя)
    ("readyh", bd(112, 113), bd(121, 122), {"file": "VID_20261126_200242_076.mp4", "ss": "end", "speed": 1.0, "cy": 1500, "crop": "crop=810:395:205:360"}),
    ("avatar", bd(121, 122), bd(133, 134), {"zoom": 1.0, "name": "stop"}),
    ("demo", bd(133, 134), TOTAL, {"cy": 1856}),
]
# маленькие окна над головой (как у конкурента): (файл, ss, speed, crop x,y,w,h в исходнике, размер окна, t0, t1)
WINS = [
    ("СКОЛЬКО ЮТУБ ПЛАТИТ",   0.4, 1.00, (0, 400, 720, 300), (700, 292), bd(49, 50), bd(57, 58)),
    ("VID_20261126_205601_609.mp4", 0.05, 1.00, (0, 410, 1080, 450), (700, 292), bd(57, 58), bd(64, 65)),   # просмотры ролика (8 362 461): вставка пользователя вместо выплат TikTok
]
B = []
for i, (kind, a, b, p) in enumerate(blocks):
    f0 = 0 if i == 0 else B[-1]["f1"]
    f1 = NEW_TOTAL if i == len(blocks) - 1 else new_f(b)
    B.append({"kind": kind, "f0": f0, "f1": f1, **p})
for bl in B:
    if bl["kind"] in ("clip", "readyh"):
        d = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{CL}/{bl['file']}"]).stdout)
        need = (bl["f1"] - bl["f0"]) / FPS
        if bl.get("ss") == "end": bl["ss"] = max(0.0, d - need - 0.02)
        avail = d - bl.get("ss", 0.0); ratio = avail / need
        if bl.get("speed") == "auto": bl["speed"] = min(1.0, max(0.8, ratio))
        bl["note"] = f"клип {d:.2f} с, с {bl['ss']:.2f}, нужно {need:.2f} с -> x{bl['speed']:.3f}" + (" +стоп-кадр" if ratio / bl["speed"] < 0.995 else "")
    print(f"  {bl['kind']:7} {bl['f0']:4}-{bl['f1']:4} ({bl['f0']/FPS:5.2f}-{bl['f1']/FPS:5.2f} с) {bl.get('note','')} {bl.get('file','')[-12:]}")

DEMO = f"{CL}/СТА ПОД РИЛСЫ"; DEMO_D = 4.082
CLICKS_T = [2.18, 3.52]                       # моменты тапов в демо (с): тап по ссылке и «Продолжить»/START BOT
for bl in B:
    if bl["kind"] == "demo":
        bl["speed"] = DEMO_D / ((bl["f1"] - bl["f0"]) / FPS)          # демо ложится на CTA ровно
        print(f"  демо {bl['f0']/FPS:.2f}-{bl['f1']/FPS:.2f} с, скорость x{bl['speed']:.3f}")

# ----------------------------------------------------------------------- 5. склейка видео (аватар / записи экрана / результат)
stage2 = f"{OUT}/stage2.mp4"
inputs, parts = ["-i", base_v], []
for i, bl in enumerate(B):
    n = bl["f1"] - bl["f0"]
    if bl["kind"] == "avatar":
        parts.append(f"[0:v]trim=start_frame={bl['f0']}:end_frame={bl['f1']},setpts=PTS-STARTPTS,{GRADE},setsar=1[v{i}]")
    elif bl["kind"] == "demo":
        k = len(inputs) // 2; inputs += ["-i", DEMO]
        parts.append(f"[{k}:v]setpts=(PTS-STARTPTS)/{bl['speed']:.5f},fps={FPS},trim=end_frame={n},setpts=PTS-STARTPTS,"
                     f"scale={W}:-2:flags=lanczos,pad={W}:{H}:0:(oh-ih)/2:color=0x0b0b0b,format=yuv420p,setsar=1[v{i}]")
    elif bl["kind"] == "readyh":
        k = len(inputs) // 2; _rp = f"{CL}/{bl['file']}"; inputs += ["-i", _rp]
        _cs = run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=color_space", "-of", "csv=p=0", _rp]).stdout.strip()
        _mi = "709" if _cs in ("bt709", "", "unknown") else "470bg"
        parts.append(f"[{k}:v]trim=start={bl.get('ss', 0.0)},setpts=PTS-STARTPTS,setpts=PTS/{bl.get('speed', 1.0)},fps={FPS},trim=end_frame={n},setpts=PTS-STARTPTS,"
                     f"zscale=filter=lanczos:matrixin={_mi}:matrix=709:rangein=tv:range=tv,{bl.get('crop', 'crop=1280:612:0:0')},format=yuv420p,split[ra][rb];"
                     f"[rb]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},gblur=sigma=40,eq=brightness=-0.28[rbg];"
                     f"[ra]scale={W}:-2:flags=lanczos[rfg];[rbg][rfg]overlay=(W-w)/2:(H-h)/2,format=yuv420p,setsar=1[v{i}]")
    elif bl["kind"] == "result":
        k = len(inputs) // 2; inputs += ["-i", RESULT]
        parts.append(f"[{k}:v]trim=start={bl.get('ss', 0.0)},setpts=PTS-STARTPTS,setpts=PTS/{bl.get('speed', 1.0)},fps={FPS},trim=end_frame={n},setpts=PTS-STARTPTS,"
                     f"scale=-2:{H}:flags=lanczos,crop={W}:{H}:x='(in_w-{W})*(0.27+0.30*(3*pow(min(t/{n / FPS:.3f},1),2)-2*pow(min(t/{n / FPS:.3f},1),3)))':y=0,format=yuv420p,setsar=1[v{i}]")
    else:
        k = len(inputs) // 2; inputs += ["-i", f"{CL}/{bl['file']}"]
        _cs = run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=color_space", "-of", "csv=p=0", f"{CL}/{bl['file']}"]).stdout.strip()
        _mi = "709" if _cs in ("bt709", "", "unknown") else "470bg"
        ss_ = f"trim=start={bl['ss']},setpts=PTS-STARTPTS," if bl.get("ss") else ""
        parts.append(f"[{k}:v]{ss_}setpts=(PTS-STARTPTS)/{bl['speed']:.5f},fps={FPS},tpad=stop_mode=clone:stop_duration=3,trim=end_frame={n},"
                     f"setpts=PTS-STARTPTS,zscale=filter=lanczos:matrixin={_mi}:matrix=709:rangein=tv:range=tv,scale=w='if(gt(a,{W}/{H}),{W},-2)':h='if(gt(a,{W}/{H}),-2,{H})':flags=lanczos,"
                     f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0b0b0b,format=yuv420p,setsar=1[v{i}]")
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
    im = Image.new("RGBA", (160 * max(1, len(ch)), 140), (0, 0, 0, 0)); ImageDraw.Draw(im).text((8, 4), ch, font=f, embedded_color=True)
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
KEYS = {"зарабатывать", "миллион", "просмотров", "сам", "бесплатный", "демо", "доступ", "выплаты"}
EXCL = set()
PROPER = {"YouTube", "ChatGPT", "Forge", "Vision"}
REPL = {"forgevision": "Forge Vision", "-видео": "видео", "-доступ": "доступ", "шорцах": "шортсах"}
MERGE = {i_: (i_, i_ + 1, "ChatGPT") for i_ in range(len(words) - 1) if words[i_]["word"].lower().startswith("чат") and words[i_ + 1]["word"].upper().startswith("GPT")}
cap_img = {}
YEL = (255, 214, 10, 255)
caps = []                                              # [f0, f1, текст, жёлтый?]
i = 0
while i < len(words):
    i1, txt = i, re.sub(r"[.,?!«»]", "", words[i]["word"]).strip()
    if i in MERGE: _, i1, txt = MERGE[i]; i1 = i1
    if not txt or i in EXCL: i += 1; continue
    key = txt.lower() in KEYS
    show = txt if txt in PROPER else REPL.get(txt.lower(), txt.lower())
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
cta_txt = "Демо-доступ — ссылка в шапке профиля"
_fz = 52
while fnt(_fz).getlength(cta_txt) > 960: _fz -= 2
cta = text_layer([[(cta_txt, YEL)]], _fz, 6)
cta_f0 = 10 ** 9; CTA_Y = 300; CTA_Y_DEMO = 70      # плашки «Демо-доступ» нет: по решению пользователя
def rcard(path, size, r=22):
    im = Image.open(path).convert("RGB").resize(size, Image.LANCZOS)
    m = Image.new("L", size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], r, fill=255)
    o = im.convert("RGBA"); o.putalpha(m); ImageDraw.Draw(o).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], r, outline=(244, 238, 228, 90), width=2)
    return o


def rounded(im, r):
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, im.size[0] - 1, im.size[1] - 1], r, fill=255)
    o = im.convert("RGBA"); o.putalpha(m); return o


hook_full = text_layer([[("Ты можешь зарабатывать", (255, 255, 255, 255))], [("на YouTube", (255, 255, 255, 255))]], 62, 7, emojis=[None, "🙌"], gap=1.2)
_hb = next(bl for bl in B if bl.get("name") == "hook")
bl_hook = {"f0": 0, "f1": _hb["f1"]}              # плашка на аватаре до вставок; на время окон прячется (как в рилсе 9)
HOOK_POS = (0, 70)



def decode_win(spec):
    fname, ss, spd, crop, (ww, wh), t0, t1 = spec
    f0, f1 = new_f(t0), new_f(t1); n = f1 - f0
    src = f"{CL}/{fname}"
    cs = run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=color_space", "-of", "csv=p=0", src]).stdout.strip()
    mi = "709" if cs in ("bt709", "", "unknown") else "470bg"
    cr = f"crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]}"
    vf = (f"trim=start={ss},setpts=PTS-STARTPTS,setpts=PTS/{spd},fps={FPS},tpad=stop_mode=clone:stop_duration=2,trim=end_frame={n},setpts=PTS-STARTPTS,"
          f"zscale=filter=lanczos:matrixin={mi}:matrix=709:rangein=tv:range=tv,{cr},scale={ww}:{wh}:flags=lanczos,"
          "scale=in_range=tv:out_range=pc:in_color_matrix=bt709,format=rgb24")
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", src, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    arr = np.frombuffer(raw[: n * ww * wh * 3], np.uint8).reshape(-1, wh, ww, 3)
    return f0, f1, arr


win_data = [decode_win(sp) for sp in WINS]
for sp, (f0, f1, arr) in zip(WINS, win_data):
    print(f"  окно {sp[0][-14:]:14} {f0/FPS:5.2f}-{f1/FPS:5.2f} с, кадров {len(arr)}/{f1-f0}, скорость x{sp[2]}")
WIN_BOTTOM = 445
_masks = {}


def win_mask(ww, wh, r=18):
    k = (ww, wh)
    if k not in _masks:
        m = Image.new("L", (ww, wh), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, ww - 1, wh - 1], r, fill=255)
        b = Image.new("L", (ww, wh), 0); ImageDraw.Draw(b).rounded_rectangle([0, 0, ww - 1, wh - 1], r, outline=255, width=3)
        _masks[k] = (np.asarray(m, np.float32)[..., None] / 255.0, np.asarray(b, np.float32)[..., None] / 255.0)
    return _masks[k]


def active_win(f):
    for (f0, f1, arr) in win_data:
        if f0 <= f < f1: return f0, f1, arr
    return None


def draw_win(base, f):
    aw = active_win(f)
    if aw is None: return
    f0, f1, arr = aw
    i = min(f - f0, len(arr) - 1)
    ww, wh = arr.shape[2], arr.shape[1]
    al = max(0.0, min(1.0, (f - f0 + 1) / (0.12 * FPS), (f1 - f) / (0.10 * FPS)))
    m, bd_ = win_mask(ww, wh)
    x0, y0 = (W - ww) // 2, max(6, WIN_BOTTOM - wh)
    reg = base[y0:y0 + wh, x0:x0 + ww].astype(np.float32)
    win = arr[i].astype(np.float32)
    win = win * (1 - bd_ * 0.45) + 255 * bd_ * 0.45
    base[y0:y0 + wh, x0:x0 + ww] = (reg * (1 - m * al) + win * (m * al)).astype(np.uint8)


def card_alpha(f, f0, f1):
    return min(1.0, (f - f0 + 1) / (0.14 * FPS), (f1 - f) / (0.12 * FPS))


bl_watch = None
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
    return                                      # таймера в этом рилсе нет (хук другой)
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
    if bl_hook["f0"] <= f < bl_hook["f1"] and active_win(f) is None and any(bl["kind"] == "avatar" and bl["f0"] <= f < bl["f1"] for bl in B):
        e = (f - bl_hook["f0"]) / FPS; sc = 1 + 0.12 * (1 - min(e / 0.16, 1)) ** 2
        hh = hook_full if sc <= 1.001 else hook_full.resize((int(W * sc), int(hook_full.size[1] * sc)), Image.LANCZOS)
        img.alpha_composite(faded(hh, max(0.0, card_alpha(f, bl_hook["f0"], bl_hook["f1"]))), ((W - hh.size[0]) // 2, 130))
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
        paste_center(img, c, W // 2, CTA_Y if f < next(bl for bl in B if bl["kind"] == "demo")["f0"] else CTA_Y_DEMO)
    return img


# ----------------------------------------------------------------------- 7. наложение, динамика, звук, экспорт
vid = f"{OUT}/video_noaudio.mp4"
dur = NEW_TOTAL / FPS
BEAT, START = 1.0, 0.0
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
    draw_win(base, f)
    ov = frame_overlay(f); bb = ov.getbbox()
    if bb:
        a_ = np.asarray(ov.crop(bb)); al = a_[..., 3:4].astype(np.float32) / 255.0
        reg = base[bb[1]:bb[3], bb[0]:bb[2]].astype(np.float32)
        base[bb[1]:bb[3], bb[0]:bb[2]] = (reg * (1 - al) + a_[..., :3].astype(np.float32) * al).astype(np.uint8)
    enc.stdin.write(base.tobytes())
enc.stdin.close(); enc.wait(); dec.stdout.close(); dec.wait()
print("наложение готово")

_d = next(bl for bl in B if bl["kind"] == "demo"); SR_ = 44100
CLICKS = f"{OUT}/clicks.wav"
_tr = np.zeros(int((dur + 0.5) * SR_), np.float32); _rng = np.random.default_rng(4)
for _tc in CLICKS_T:
    _p = int((_d["f0"] / FPS + _tc / _d["speed"]) * SR_); _t = np.arange(int(0.12 * SR_)) / SR_
    _c = (np.sin(2 * np.pi * 1600 * _t) * np.exp(-_t * 110) + 0.7 * np.sin(2 * np.pi * 420 * _t) * np.exp(-_t * 60) + 0.5 * _rng.standard_normal(len(_t)) * np.exp(-_t * 500))
    _tr[_p:_p + len(_c)] += (_c / np.abs(_c).max() * 0.55).astype(np.float32)
import wave as _w
with _w.open(CLICKS, "wb") as _f:
    _f.setnchannels(2); _f.setsampwidth(2); _f.setframerate(SR_); _f.writeframes((np.stack([_tr, _tr], 1) * 32767).astype("<i2").tobytes())
print("клики на", [round(_d["f0"] / FPS + t / _d["speed"], 2) for t in CLICKS_T], "с")

# музыка: трек пользователя (тот же, что в рилсах 7 и 9) с самого начала, чуть тише голоса, сайдчейн на речи
TRACK = f"{CL}/track_new_185720_832.mp4"                 # «Insensible Aminos» (подтверждено пользователем)
MIX_DB = float(os.environ.get("MIX_DB", "-13"))
music = f"{OUT}/music_track.wav"
run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-ss", "0", "-i", TRACK, "-t", f"{dur + 0.5:.2f}", "-vn", "-ac", "2", "-ar", "44100", music])
final = f"{OUT}/рилс13_v3.mp4"
# звук роликов: «Маяк» на весь экран (со своей дорожкой), ниже голоса аватара; запись YouTube Studio без звука
CLIP_DB = float(os.environ.get("CLIP_DB", "-8"))
segs = [(f"{CL}/{bl['file']}", bl["ss"], bl["f0"] / FPS, (bl["f1"] - bl["f0"]) / FPS, bl["speed"]) for bl in B if bl.get("audio")]
cin, cf_ = [], []
for k_, (pth, ss_, t0_, d_, sp_) in enumerate(segs):
    cin += ["-i", pth]
    cf_.append(f"[{k_}:a]atrim=start={ss_:.3f}:duration={d_ * sp_:.3f},asetpts=PTS-STARTPTS,atempo={sp_:.4f},aformat=sample_rates=48000:channel_layouts=stereo,"
               f"afade=t=in:st=0:d=0.08,afade=t=out:st={max(d_ - 0.18, 0):.3f}:d=0.18,adelay={int(t0_ * 1000)}|{int(t0_ * 1000)}[s{k_}]")
cf_.append(f"[s0]apad=whole_dur={dur + 0.5:.2f}[o]")
clipaud = f"{OUT}/clip_audio.wav"
if segs:
    run(["ffmpeg", "-nostdin", "-y", "-v", "error", *cin, "-filter_complex", ";".join(cf_), "-map", "[o]", "-ar", "48000", "-ac", "2", clipaud])
else:                                                # роликов со звуком нет: тихая дорожка нужной длины
    run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{dur + 0.5:.2f}", clipaud])
af = (f"[1:a]highpass=f=55,afade=t=in:st=0:d=0.06,afade=t=out:st={dur - 1.4:.2f}:d=1.4,volume={MIX_DB}dB[m];[3:a]volume=-4dB[c];"
      f"[4:a]volume={CLIP_DB}dB[ca0];[2:a]asplit=2[v][vs];"
      "[ca0]asplit=2[ca][cak];"
      "[vs][cak]amix=inputs=2:normalize=0:duration=first[key];"
      "[m][key]sidechaincompress=threshold=0.02:ratio=8:attack=8:release=300[md];"
      "[v][md][c][ca]amix=inputs=4:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.89:level=disabled[a]")
run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", vid, "-i", music, "-i", base_a, "-i", CLICKS, "-i", clipaud, "-filter_complex", af, "-map", "0:v", "-map", "[a]",
     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{dur:.3f}", final])
json.dump({"caps": [[a / FPS, b / FPS, t] for a, b, t, k in caps], "blocks": B},
          open(f"{OUT}/timeline.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ГОТОВО:", final, f"{os.path.getsize(final)/1e6:.1f} МБ, {dur:.2f} с")
