"""Обложка: человек (хромакей) в студии + красная плашка в N строк + карточка-доказательство.
Настройки — JSON-файл. Пример: обложки_2026-11-28/A.json"""
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cover import W, H, WHITE, YELLOW, FONT, plate, text_line

cfg = json.load(open(sys.argv[1])); base = os.path.dirname(os.path.abspath(sys.argv[1]))
P = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
COL = {'w': WHITE, 'y': YELLOW}

c = Image.open(P(cfg['bg'])).convert('RGB')
if cfg.get('mirror_bg'): c = c.transpose(Image.FLIP_LEFT_RIGHT)
c = ImageEnhance.Brightness(c.filter(ImageFilter.GaussianBlur(2.2))).enhance(0.92).convert('RGBA')

def card(spec):
    im = Image.open(P(spec['src'])).convert('RGB').crop(tuple(spec['crop']))
    w = spec['w']; im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2))
    r = 26; b = 8
    fr = Image.new('RGBA', (im.width + 2 * b, im.height + 2 * b), (0, 0, 0, 0))
    ImageDraw.Draw(fr).rounded_rectangle((0, 0, fr.width - 1, fr.height - 1), r + b, fill=(255, 255, 255, 255))
    m = Image.new('L', im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), r, fill=255)
    fr.paste(im, (b, b), m)
    fr = fr.rotate(spec.get('rot', 0), resample=Image.BICUBIC, expand=True)
    sh = Image.new('RGBA', c.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 150), (spec['x'] + 10, spec['y'] + 18), fr.getchannel('A'))
    c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(20)))
    c.alpha_composite(fr, (spec['x'], spec['y']))

for cs in cfg.get('cards_behind', []): card(cs)

p = Image.open(P(cfg['person'])).convert('RGBA')
Hp = cfg['hp']; p = p.resize((round(p.width * Hp / p.height), Hp), Image.LANCZOS)
if cfg.get('mirror_person'): p = p.transpose(Image.FLIP_LEFT_RIGHT)
arr = np.array(p).astype(np.float32); arr[..., 0] *= 1.05; arr[..., 2] *= 0.90
p = Image.fromarray(arr.clip(0, 255).astype(np.uint8), 'RGBA')
p = p.filter(ImageFilter.UnsharpMask(radius=1.5, percent=40, threshold=2))
p.putalpha(p.getchannel('A').filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8)))
px = (W - p.width) // 2 + cfg.get('dx', 0); dy = cfg.get('dy', 0)
sh = Image.new('RGBA', c.size, (0, 0, 0, 0)); sh.paste((0, 0, 0, 50), (px, dy + 30), p.getchannel('A'))
c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(25))); c.alpha_composite(p, (px, dy))

for cs in cfg.get('cards', []): card(cs)
c = c.convert('RGB'); d = ImageDraw.Draw(c)

def panel(sp):
    # скрин аналитики: src приводится к 1080x1920, потом crop, масштаб до w
    global c, d
    im = Image.open(P(sp['src'])).convert('RGB').resize((W, H), Image.LANCZOS).crop(tuple(sp['crop']))
    k = sp['w'] / im.width; im = im.resize((sp['w'], round(im.height * k)), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    x, y = sp['x'], sp['y']; r = 26
    m = Image.new('L', c.size, 0); ImageDraw.Draw(m).rounded_rectangle((x, y + 12, x + im.width, y + im.height + 12), r, fill=150)
    c.paste((0, 0, 0), (0, 0), m.filter(ImageFilter.GaussianBlur(20)))
    mm = Image.new('L', im.size, 0); ImageDraw.Draw(mm).rounded_rectangle((0, 0, im.width - 1, im.height - 1), r, fill=255)
    c.paste(im, (x, y), mm); d = ImageDraw.Draw(c)
    if 'hl' in sp:  # красный круг вокруг суммы дохода
        x0, y0, x1, y1 = [v * k for v in sp['hl']]
        box = (x + x0, y + y0, x + x1, y + y1)
        for wdt, col in [(16, (120, 0, 0)), (11, (235, 25, 35))]:
            d.ellipse(box, outline=col, width=wdt)
    return k

def arrow(pts, col=(255, 226, 26)):
    # толстая изогнутая стрелка (квадратичная кривая) с тёмной обводкой
    global c, d
    (x0, y0), (cx, cy), (x1, y1) = pts
    t = np.linspace(0, 1, 80)
    xs = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
    ys = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
    line = list(zip(xs, ys))
    ang = np.arctan2(ys[-1] - ys[-6], xs[-1] - xs[-6])
    L, Wd = 70, 44
    tip = (x1 + np.cos(ang) * 18, y1 + np.sin(ang) * 18)
    head = [tip, (x1 - np.cos(ang) * L + np.sin(ang) * Wd, y1 - np.sin(ang) * L - np.cos(ang) * Wd),
            (x1 - np.cos(ang) * L - np.sin(ang) * Wd, y1 - np.sin(ang) * L + np.cos(ang) * Wd)]
    body = line[:-8]
    for w_, cl, grow in [(34, (40, 10, 0), 8), (22, col, 0)]:
        d.line(body, fill=cl, width=w_, joint='curve')
        if grow:
            cxh, cyh = np.mean([h[0] for h in head]), np.mean([h[1] for h in head])
            hh = [(cxh + (hx - cxh) * 1.18, cyh + (hy - cyh) * 1.18) for hx, hy in head]
            d.polygon(hh, fill=cl)
        else:
            d.polygon(head, fill=cl)

if 'panel' in cfg: panel(cfg['panel'])

def fit(text, maxw, start):
    for s in range(start, 30, -2):
        if d.textlength(text, font=ImageFont.truetype(FONT, s)) <= maxw: return s

# строки: [[[текст, цвет], ...], макс_размер]
lines = []
for parts, mx in cfg['lines']:
    full = ''.join(t for t, _ in parts)
    lines.append(([(t, COL[k]) for t, k in parts], fit(full, 930, mx)))
y0 = cfg['plate_y']; y = y0 + 20
hgt = sum(s * 1.12 for _, s in lines) + 30
plate(c, (35, y0, 1045, int(y0 + hgt + 14)))
d = ImageDraw.Draw(c)
for parts, s in lines:
    text_line(c, W / 2, y, parts, s); y += s * 1.12
if 'arrow' in cfg: arrow(cfg['arrow'])
c.save(P(cfg['out']), quality=100, subsampling=0)
print('ok', [s for _, s in lines], 'plate', y0, int(y0 + hgt + 14))
