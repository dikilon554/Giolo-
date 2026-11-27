#!/usr/bin/env python3
"""Рилс №15 («Человечек в шапке»): без лица, только голос аватара + моушн-графика Pillow на светлом фоне (веер превью, счётчики, плашки «День», столбики, слайды, таймер),
заставка Forge Vision из рилса Шукура, записи экрана, готовый ролик, плашка подарков, демо CTA, музыка. Основа reel14.py (паузы, слова, звук)."""
import json, os, re, subprocess, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FPS, W, H = 25, 1080, 1920
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CL = f"{ROOT}/исходники/рилс15"
AV = f"{CL}/VID_20261127_164722_198.mp4"
SH = f"{ROOT}/исходники/рилс14/рилс_шукура"
DEMO = f"{ROOT}/исходники/рилс14/СТА ПОД РИЛСЫ"; DEMO_D = 4.082
OUT = f"{ROOT}/монтаж_2026-11-27/рилс15"; os.makedirs(OUT, exist_ok=True)
AS = f"{OUT}/assets"
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
_wl = json.load(open(f"{ROOT}/монтаж_слова/VID_20261127_164722_198.words.json", encoding="utf-8"))["words"][-1]["end"]
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
words = json.load(open(f"{ROOT}/монтаж_слова/VID_20261127_164722_198.words.json", encoding="utf-8"))["words"]
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

# ----------------------------------------------------------------------- 4. раскладка сцен (по новому времени)
bd = lambda a, b: (eT(a) + sT(b)) / 2
SC = [  # имя, граница конца (между словами a и b)
    ("fan", bd(15, 16)), ("sub", bd(22, 23)), ("grid", bd(34, 35)), ("bars", bd(40, 41)), ("slides", bd(53, 54)),
    ("splash", bd(63, 64)), ("styles60", bd(72, 73)), ("vstyle", bd(82, 83)), ("vtext", bd(95, 96)), ("vready", bd(106, 107)),
    ("gift", bd(111, 112)), ("demo", None)]
S = []
for k, (nm, b) in enumerate(SC):
    f0 = 0 if k == 0 else S[-1]["f1"]; f1 = NEW_TOTAL if b is None else new_f(b)
    S.append({"nm": nm, "f0": f0, "f1": f1})
for sc in S: print(f"  {sc['nm']:9} {sc['f0']:4}-{sc['f1']:4} ({sc['f0']/FPS:5.2f}-{sc['f1']/FPS:5.2f} с, {(sc['f1']-sc['f0'])/FPS:.2f})")
SCN = {sc["nm"]: sc for sc in S}

# ----------------------------------------------------------------------- 5. графика
NAVY, RED, BLUE, WHITE, GRAY = (18, 28, 64, 255), (232, 49, 46, 255), (26, 92, 214, 255), (255, 255, 255, 255), (120, 130, 150, 255)
eo = lambda u: 1 - (1 - min(max(u, 0), 1)) ** 3
def eb(u):
    u = min(max(u, 0), 1); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2
_fc = {}
def fnt(sz):
    if sz not in _fc: _fc[sz] = ImageFont.truetype(FM, sz)
    return _fc[sz]
_tc = {}
def text_img(t, sz, fill, stroke=0, sfill=(255, 255, 255, 255)):
    k = (t, sz, fill, stroke, sfill)
    if k not in _tc:
        f = fnt(sz); w = int(f.getlength(t)) + 2 * stroke + 20; h = int(sz * 1.4) + 2 * stroke
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ImageDraw.Draw(im).text((w // 2, h // 2), t, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=sfill)
        _tc[k] = im.crop(im.getbbox())
    return _tc[k]
def pill(t, sz, bg, fg=WHITE, px=34, py=18, r=None):
    k = ("pill", t, sz, bg, fg, px, py)
    if k not in _tc:
        f = fnt(sz); w = int(f.getlength(t)) + 2 * px; h = int(sz * 1.0) + 2 * py; r = r or h // 2
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); d.rounded_rectangle([0, 0, w - 1, h - 1], r, fill=bg); d.text((w // 2, h // 2 + 2), t, font=f, fill=fg, anchor="mm")
        _tc[k] = im
    return _tc[k]
def emoji_img(ch, px):
    im = Image.new("RGBA", (160, 140), (0, 0, 0, 0)); ImageDraw.Draw(im).text((8, 4), ch, font=ImageFont.truetype(EMOJI, 109), embedded_color=True)
    im = im.crop(im.getbbox()); return im.resize((int(im.size[0] * px / im.size[1]), px), Image.LANCZOS)
def rounded(im, r):
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, im.size[0] - 1, im.size[1] - 1], r, fill=255)
    o = im.convert("RGBA"); o.putalpha(m); return o
def card(path_or_im, size, r=26, shadow=True):
    im = Image.open(path_or_im).convert("RGB") if isinstance(path_or_im, str) else path_or_im.convert("RGB")
    im = rounded(im.resize(size, Image.LANCZOS), r)
    if not shadow: return im
    pad = 40; o = Image.new("RGBA", (size[0] + 2 * pad, size[1] + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", o.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([pad, pad + 14, pad + size[0], pad + 14 + size[1]], r, fill=(20, 30, 70, 70))
    o = Image.alpha_composite(o, sh.filter(ImageFilter.GaussianBlur(14))); o.alpha_composite(im, (pad, pad)); return o
def put(img, lyr, cx, cy, sc=1.0, al=1.0, rot=0.0):
    if al <= 0 or sc <= 0.01: return
    if abs(sc - 1) > 0.004: lyr = lyr.resize((max(1, int(lyr.size[0] * sc)), max(1, int(lyr.size[1] * sc))), Image.BICUBIC if sc > 1 else Image.LANCZOS)
    if abs(rot) > 0.05: lyr = lyr.rotate(rot, resample=Image.BICUBIC, expand=True)
    if al < 0.999:
        a = np.array(lyr); a[..., 3] = (a[..., 3] * al).astype(np.uint8); lyr = Image.fromarray(a)
    img.alpha_composite(lyr, (int(cx - lyr.size[0] / 2), int(cy - lyr.size[1] / 2)))

# фон: светлый градиент и мягкие «пузырьки», медленный дрейф вверх
rng = np.random.default_rng(15)
_bgbase = np.zeros((H, W, 3), np.float32); yy = np.linspace(0, 1, H)[:, None]
_bgbase[:] = (np.array([243, 246, 251]) * (1 - yy[..., None]) + np.array([232, 238, 248]) * yy[..., None])
_bub = Image.new("RGBA", (W, H * 2), (0, 0, 0, 0)); _bd = ImageDraw.Draw(_bub)
for _ in range(34):
    x, y, r = rng.uniform(0, W), rng.uniform(0, H * 2), rng.uniform(14, 70); c = (120, 160, 235) if rng.random() < .7 else (235, 120, 120)
    _bd.ellipse([x - r, y - r, x + r, y + r], fill=c + (26,), outline=c + (55,), width=2)
_bub = _bub.filter(ImageFilter.GaussianBlur(1.2))
_bg0 = Image.fromarray(_bgbase.astype(np.uint8)).convert("RGBA")
def light_bg(f):
    im = _bg0.copy(); off = int((f * 1.6) % H); im.alpha_composite(_bub.crop((0, off, W, off + H))); return im

def ld(n): return Image.open(f"{AS}/{n}.png").convert("RGB")
TH = {k: ld("th_" + k) for k in ["480_470_2", "480_470_1", "480_142_2", "480_142_1", "480_142_0", "480_470_0", "822_500_1", "126_525_1"]}
SLIDES = [f"{CL}/IMG_20261127_{n}.jpg" for n in ["164627_748", "164627_759", "164627_786", "164627_824", "164627_894", "164628_445", "164628_451", "164628_555", "164628_655", "164632_054"]]
SL_CARDS = [card(p, (980, 639)) for p in SLIDES]
_h = Image.open(f"{CL}/IMG_20261127_164631_748.jpg").convert("RGB").crop((15, 277, 172, 434))
AVATAR = Image.new("RGBA", (157, 157), (0, 0, 0, 0)); _m = Image.new("L", (157, 157), 0); ImageDraw.Draw(_m).ellipse([0, 0, 156, 156], fill=255); AVATAR.paste(_h.convert("RGBA"), (0, 0), _m)

def sc_fan(img, t, d):
    ks = ["480_142_2", "480_142_1", "480_470_2", "480_470_1", "480_142_0"]
    shrink = eo((t - 1.3) / 0.5)
    for i, k in enumerate(ks):
        u = eo((t - 0.08 * i) / 0.55)
        ang = (i - 2) * 12 * u; cx = 540 + (i - 2) * 125 * u; cy0 = 600 - 150 * shrink + abs(i - 2) * 20 * u
        cy = cy0 + (1 - u) * 1100
        put(img, card(TH[k], (560, 315), 22), cx, cy, 0.95 - 0.10 * shrink, 1, -ang)
    if t > 1.1:
        u = eb((t - 1.1) / 0.45); put(img, text_img("31", 360, RED), 540, 960, u)
        put(img, text_img("МУЛЬТИКОВ", 112, NAVY), 540, 1220, eb((t - 1.4) / 0.4))
def sc_sub(img, t, d):
    u = eb(t / 0.5); put(img, card(Image.new("RGB", (940, 300), (255, 255, 255)), (940, 300), 40), 540, 400, u)
    put(img, AVATAR, 230, 400, u * 1.1); put(img, text_img("Beanie Survives", 66, NAVY), 640, 372, u); put(img, text_img("@BeanieSurvives", 38, GRAY), 592, 450, u)
    v = int(114000 * eo((t - 0.5) / 1.6)); s = f"{v:,}".replace(",", " ")
    if t > 0.5:
        put(img, text_img(s, 250, BLUE), 540, 840, eb((t - 0.5) / 0.4)); put(img, text_img("ПОДПИСЧИКОВ", 104, NAVY), 540, 1090, eb((t - 0.9) / 0.4))
def sc_grid(img, t, d):
    ks = ["822_500_1", "480_470_1", "480_142_1", "480_470_2", "480_142_0", "480_470_0"]
    for i, k in enumerate(ks):
        cx = 25 + 250 + (i % 2) * 530; cy = 150 + 140 + (i // 2) * 320 + 90
        u = eb((t - 0.1 * i) / 0.45); put(img, card(TH[k], (500, 281), 22), cx, cy, u)
    for i, (txt, fr) in enumerate([("ДЕНЬ 1", .30), ("ДЕНЬ 60", .52), ("ДЕНЬ 120", .74)]):
        pos = [(0, 0), (1, 0), (0, 1)][i]; ks_i = i; cx = 25 + 125 + (ks_i % 2) * 530 + 40; cy = 150 + 140 + (ks_i // 2) * 320 + 90 + 100
        if t > fr * d: put(img, pill(txt, 54, RED, px=36, py=20), cx + 70, cy, eb((t - fr * d) / 0.35) * 1.15)
def sc_bars(img, t, d):
    put(img, text_img("ЦИФРЫ", 110, RED), 540, 170, eb(t / 0.4))
    rows = [("480_470_2", 3000, "3 МЛН"), ("480_470_1", 1100, "1,1 МЛН"), ("480_142_2", 912, "912 ТЫС."), ("480_142_1", 662, "662 ТЫС."), ("480_142_0", 549, "549 ТЫС.")]
    for i, (k, v, lab) in enumerate(rows):
        t0 = 0.35 + 0.3 * i; y = 360 + i * 210
        put(img, card(TH[k], (300, 169), 18), 60 + 150, y + 84, eb((t - t0) / 0.4))
        w = max(70, int(380 * v / 3000 * eo((t - t0 - 0.15) / 0.7)))
        if t > t0 + 0.1:
            im = Image.new("RGBA", (w, 96), (0, 0, 0, 0)); ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, 95], 24, fill=BLUE if i else RED); img.alpha_composite(im, (390, y + 36))
            put(img, text_img(lab, 64, NAVY), 390 + w + 20 + text_img(lab, 64, NAVY).size[0] / 2, y + 84, eb((t - t0 - 0.5) / 0.3))
def sc_slides(img, t, d):
    n = len(SL_CARDS); iv = max(0.4, (d - 0.3) / n); k = min(int(t / iv), n - 1); u = (t - k * iv) / 0.14
    cx = 540 + (1 - eo(u)) * 1000 if k > 0 else 540
    put(img, SL_CARDS[k], cx, 640)
    if t > 0.3 * d:
        put(img, pill("БЕЗ АНИМАЦИИ —", 60, RED, px=44, py=22), 540, 1130, eb((t - 0.3 * d) / 0.3)); put(img, pill("ТОЛЬКО КАРТИНКИ", 60, RED, px=44, py=22), 540, 1250, eb((t - 0.3 * d - 0.15) / 0.3))
def sc_timer(img, t, d):
    put(img, text_img("ЗА", 100, NAVY), 540, 360, eb(t / 0.3))
    v = 600 * eo(t / max(d * 0.8, 0.1)); txt = f"{int(v // 60):02d}:{int(v % 60):02d}"
    box = Image.new("RGBA", (800, 300), (0, 0, 0, 0)); ImageDraw.Draw(box).rounded_rectangle([0, 0, 799, 299], 60, fill=NAVY, outline=RED, width=8)
    put(img, box, 540, 700, eb(t / 0.4)); put(img, text_img(txt, 190, WHITE), 540, 700, eb(t / 0.4))
    put(img, text_img("МИНУТ", 130, RED), 540, 1040, eb((t - 0.3) / 0.4))
_st = None
def sc_s60(img, t, d):
    global _st
    if _st is None:
        fr = run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", "0.9", "-i", f"{CL}/VID_20261127_164637_466.mp4", "-frames:v", "1", f"{OUT}/_st.png"]); _st = Image.open(f"{OUT}/_st.png").convert("RGB").crop((0, 150, 720, 646))
        _st = card(_st, (900, 620), 34)
    put(img, text_img("60+", 400, BLUE), 540, 330, eb(t / 0.45)); put(img, text_img("СТИЛЕЙ", 120, NAVY), 540, 610, eb((t - 0.2) / 0.4))
    put(img, _st, 540, 1090, eb((t - 0.4) / 0.5))
def sc_gift(img, t, d):
    put(img, emoji_img("\U0001F381", 320), 540, 330, eb(t / 0.5) * (1 + 0.04 * np.sin(t * 6)))
    put(img, pill("ПОДАРКИ ПЕРВЫМ", 80, RED, px=50, py=26), 540, 690, eb((t - 0.2) / 0.4)); put(img, pill("ПОЛЬЗОВАТЕЛЯМ", 80, RED, px=50, py=26), 540, 830, eb((t - 0.35) / 0.4))
    put(img, pill("ПРОМОКОДЫ", 66, BLUE, px=40, py=20), 540, 1000, eb((t - 0.12 * d - 0.5) / 0.4)); put(img, pill("БЕСПЛАТНЫЙ ДОСТУП", 66, BLUE, px=40, py=20), 540, 1120, eb((t - 0.30 * d - 0.5) / 0.4))
    put(img, text_img("ссылка в шапке профиля".upper(), 56, NAVY), 540, 1260, eb((t - 0.5 * d - 0.5) / 0.4))

# ----------------------------------------------------------------------- 6. видео-вставки (поток кадров ffmpeg)
class Feed:
    def __init__(self, path, n, ss=0.0, end=None, speed=1.0, extra="", pad=True):
        cs = run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=color_space", "-of", "csv=p=0", path]).stdout.strip()
        mi = "709" if cs in ("bt709", "", "unknown") else "470bg"
        tr = f"trim=start={ss}" + (f":end={end}" if end else "")
        vf = (f"{tr},setpts=PTS-STARTPTS,setpts=PTS/{speed:.5f},fps={FPS},tpad=stop_mode=clone:stop_duration=4,trim=end_frame={n},setpts=PTS-STARTPTS,"
              f"zscale=filter=lanczos:matrixin={mi}:matrix=709:rangein=tv:range=tv,scale=w='if(gt(a,{W}/{H}),{W},-2)':h='if(gt(a,{W}/{H}),-2,{H})':flags=lanczos,"
              f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0b0b0b," + (extra + "," if extra else "") + "scale=in_range=tv:out_range=pc:in_color_matrix=bt709,format=rgb24")
        self.p = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    def read(self):
        b = self.p.stdout.read(W * H * 3)
        return np.frombuffer(b, np.uint8).reshape(H, W, 3) if len(b) == W * H * 3 else None
    def close(self): self.p.stdout.close(); self.p.wait()
def clipdur(p): return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).stdout)
def auto_speed(avail, need): return min(1.0, max(0.8, avail / need))
BOX = "drawbox=x=0:y=1440:w=1080:h=130:color=black:t=fill"
FEEDS = {}
def mk_feeds():
    n = lambda nm: SCN[nm]["f1"] - SCN[nm]["f0"]
    n6 = int(n("splash") * 0.52); n7 = int(n("styles60") * 0.5)
    FEEDS["splash"] = (n6, dict(path=SH, n=n6, ss=12.46, end=13.76, speed=auto_speed(1.30, n6 / FPS), extra=BOX))
    FEEDS["styles60"] = (n7, dict(path=SH, n=n7, ss=13.76, end=16.60, speed=auto_speed(2.84, n7 / FPS), extra=BOX))
    for nm, fn, ss in [("vstyle", "VID_20261127_164637_466.mp4", 0.0), ("vtext", "VID_20261127_164641_661.mp4", 0.0), ("vready", "VID_20261127_164648_205.mp4", 0.0)]:
        p = f"{CL}/{fn}"; FEEDS[nm] = (n(nm), dict(path=p, n=n(nm), ss=ss, speed=auto_speed(clipdur(p) - ss, n(nm) / FPS)))
    FEEDS["demo"] = (n("demo"), dict(path=DEMO, n=n("demo"), speed=DEMO_D / (n("demo") / FPS)))
mk_feeds()
for k, (nn, kw) in FEEDS.items(): print(f"  видео {k:9} кадров {nn} скорость x{kw['speed']:.3f}")

# ----------------------------------------------------------------------- 7. субтитры
KEYS = {"30", "110", "тысяч", "сотни", "анимации", "10", "60", "зомби", "промокоды", "бесплатный", "доступ", "мультиков", "подписчиков", "forge vision"}
REPL = {"ютуб": "YouTube", "-апокалипсисе": "апокалипсисе"}
MERGE = {14: (14, 15, "зомби-апокалипсисе"), 58: (58, 59, "Forge Vision")}
caps = []; i = 0
while i < len(words):
    i1, txt = i, re.sub(r"[.,?!«»]", "", words[i]["word"]).strip()
    if i in MERGE: _, i1, txt = MERGE[i]
    if not txt: i += 1; continue
    show = REPL.get(txt.lower(), txt); key = txt.lower() in KEYS
    f0 = new_f(sT(i)); last = i1; nxt = i1 + 1
    f1 = new_f(sT(nxt)) if (nxt < len(words) and sT(nxt) - eT(last) < 0.3) else new_f(eT(last))
    caps.append([f0, max(f1, f0 + 2), show.upper(), key]); i = i1 + 1
for a_, b_ in zip(caps, caps[1:]):
    if a_[1] > b_[0]: a_[1] = b_[0]
def draw_cap(img, f, dark, cy):
    for f0, f1, t, k in caps:
        if f0 <= f < f1:
            e = (f - f0) / FPS; sc = 1 + 0.16 * (1 - min(e / 0.10, 1)) ** 2
            fill = RED if k else (WHITE if dark else NAVY); sf = (0, 0, 0, 255) if dark else (255, 255, 255, 255)
            put(img, text_img(t, 76, fill, 8, sf), 540, cy, sc); return

# ----------------------------------------------------------------------- 8. рендер
vid = f"{OUT}/video_noaudio.mp4"; dur = NEW_TOTAL / FPS
enc = subprocess.Popen(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-vf", "scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd,format=yuv420p",
                        "-r", str(FPS), "-c:v", "libx264", "-profile:v", "high", "-b:v", "20M", "-maxrate", "24M", "-bufsize", "40M", "-preset", "medium",
                        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-t", f"{dur:.3f}", vid], stdin=subprocess.PIPE)
LIGHT = {"fan": sc_fan, "sub": sc_sub, "grid": sc_grid, "bars": sc_bars, "slides": sc_slides}
feed = None; feed_nm = None
for f in range(NEW_TOTAL):
    sc = next(s_ for s_ in S if s_["f0"] <= f < s_["f1"]); nm = sc["nm"]; t = (f - sc["f0"]) / FPS; d = (sc["f1"] - sc["f0"]) / FPS
    use_feed = nm in FEEDS and (f - sc["f0"]) < FEEDS[nm][0]
    if use_feed:
        if feed_nm != nm: feed = Feed(**FEEDS[nm][1]); feed_nm = nm
        fr = feed.read()
        if fr is None: fr = last_fr
        last_fr = fr; img = Image.fromarray(fr).convert("RGBA"); dark = True; cy = 1700
        if nm == "demo": cy = 1860
    else:
        if feed is not None and feed_nm == nm: feed.close(); feed = None; feed_nm = None
        img = light_bg(f); dark = False; cy = 1500
        if nm in LIGHT: LIGHT[nm](img, t, d)
        elif nm == "splash": sc_timer(img, t - FEEDS["splash"][0] / FPS, d - FEEDS["splash"][0] / FPS)
        elif nm == "styles60": sc_s60(img, t - FEEDS["styles60"][0] / FPS, d - FEEDS["styles60"][0] / FPS)
        elif nm == "gift": sc_gift(img, t, d)
    draw_cap(img, f, dark, cy)
    enc.stdin.write(np.asarray(img.convert("RGB"), np.uint8).tobytes())
enc.stdin.close(); enc.wait()
print("наложение готово")

_d = SCN["demo"]; SR_ = 44100; spd = FEEDS["demo"][1]["speed"]
CLICKS = f"{OUT}/clicks.wav"; CLICKS_T = [2.18, 3.52]
_tr = np.zeros(int((dur + 0.5) * SR_), np.float32); _rng = np.random.default_rng(4)
for _tc_ in CLICKS_T:
    _p = int((_d["f0"] / FPS + _tc_ / spd) * SR_); _t = np.arange(int(0.12 * SR_)) / SR_
    _c = (np.sin(2 * np.pi * 1600 * _t) * np.exp(-_t * 110) + 0.7 * np.sin(2 * np.pi * 420 * _t) * np.exp(-_t * 60) + 0.5 * _rng.standard_normal(len(_t)) * np.exp(-_t * 500))
    _tr[_p:_p + len(_c)] += (_c / np.abs(_c).max() * 0.55).astype(np.float32)
import wave as _w
with _w.open(CLICKS, "wb") as _f:
    _f.setnchannels(2); _f.setsampwidth(2); _f.setframerate(SR_); _f.writeframes((np.stack([_tr, _tr], 1) * 32767).astype("<i2").tobytes())

TRACK = os.environ.get("TRACK", f"{ROOT}/исходники/пак_музыки/100ТРЕКОВ/88) Tak Tak Funk - Tazty  9am3X.mp3")
MIX_DB = float(os.environ.get("MIX_DB", "-13")); music = f"{OUT}/music_track.wav"
run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-ss", "0", "-i", TRACK, "-t", f"{dur + 0.5:.2f}", "-vn", "-ac", "2", "-ar", "44100", music])
final = f"{OUT}/рилс15_v1.mp4"
af = (f"[1:a]highpass=f=55,afade=t=in:st=0:d=0.06,afade=t=out:st={dur - 1.4:.2f}:d=1.4,volume={MIX_DB}dB[m];[3:a]volume=-4dB[c];[2:a]asplit=2[v][vs];"
      "[m][vs]sidechaincompress=threshold=0.02:ratio=8:attack=8:release=300[md];"
      "[v][md][c]amix=inputs=3:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.89:level=disabled[a]")
run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", vid, "-i", music, "-i", base_a, "-i", CLICKS, "-filter_complex", af, "-map", "0:v", "-map", "[a]",
     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{dur:.3f}", final])
json.dump({"caps": [[a / FPS, b / FPS, t] for a, b, t, k in caps], "scenes": S}, open(f"{OUT}/timeline.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ГОТОВО:", final, f"{os.path.getsize(final)/1e6:.1f} МБ, {dur:.2f} с")
