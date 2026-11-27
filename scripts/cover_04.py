"""Обложка: человек (хромакей) на студийном фоне + плашка в 3 строки, без иконок.
python cover_04.py person.png out.jpg Hp dx dy"""
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from cover import W, H, WHITE, YELLOW, FONT, plate, text_line

D = os.path.join(os.path.dirname(__file__), '..', 'обложки_2026-11-27')
person_p, out = sys.argv[1], sys.argv[2]
Hp, dx, dy, y0 = (int(v) for v in sys.argv[3:7])

c = Image.open(f'{D}/слои/фон_студия.png').convert('RGB').filter(ImageFilter.GaussianBlur(2.2))
c = ImageEnhance.Brightness(c).enhance(0.92).convert('RGBA')
p = Image.open(person_p).convert('RGBA')
p = p.resize((round(p.width * Hp / p.height), Hp), Image.LANCZOS)
arr = np.array(p).astype(np.float32)
arr[..., 0] *= 1.05; arr[..., 2] *= 0.90
p = Image.fromarray(arr.clip(0, 255).astype(np.uint8), 'RGBA')
p = p.filter(ImageFilter.UnsharpMask(radius=1.5, percent=40, threshold=2))
p.putalpha(p.getchannel('A').filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8)))
px = (W - p.width) // 2 + dx
sh = Image.new('RGBA', c.size, (0, 0, 0, 0))
sh.paste((0, 0, 0, 50), (px, dy + 30), p.getchannel('A'))
c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(25)))
c.alpha_composite(p, (px, dy))
c = c.convert('RGB')

def fit(text, maxw, start):
    d = ImageDraw.Draw(c)
    for s in range(start, 30, -2):
        if d.textlength(text, font=ImageFont.truetype(FONT, s)) <= maxw: return s

s1, s2, s3 = fit('ТЫ СТАНЕШЬ ПЕРВЫМ', 930, 110), fit('МИЛЛИОНЕРОМ', 940, 160), fit('В СВОЕЙ СЕМЬЕ', 930, 110)
s1 = s3 = min(s1, s3)
y1 = int(y0 + 18 + s1 * 1.12 + s2 * 1.1 + s3 * 1.25 + 22)
plate(c, (35, y0, 1045, y1))
text_line(c, W / 2, y0 + 18, [('ТЫ СТАНЕШЬ ПЕРВЫМ', WHITE)], s1)
text_line(c, W / 2, y0 + 18 + s1 * 1.12, [('МИЛЛИОНЕРОМ', YELLOW)], s2)
text_line(c, W / 2, y0 + 18 + s1 * 1.12 + s2 * 1.1, [('В СВОЕЙ СЕМЬЕ', WHITE)], s3)
print('sizes', s1, s2, s3)
c.save(out, quality=100, subsampling=0)
