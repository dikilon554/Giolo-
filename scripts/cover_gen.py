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
for parts, s in lines:
    text_line(c, W / 2, y, parts, s); y += s * 1.12
c.save(P(cfg['out']), quality=100, subsampling=0)
print('ok', [s for _, s in lines], 'plate', y0, int(y0 + hgt + 14))
