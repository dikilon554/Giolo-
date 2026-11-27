"""Обложка: настоящий человек (хромакей) на студийном фоне + YouTube + FV + плашка + аналитика.
python cover_03.py person.png out.jpg [scale_h] [x_shift]"""
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from cover import W, H, WHITE, YELLOW, plate, text_line

D = os.path.join(os.path.dirname(__file__), '..', 'обложки_2026-11-27')
person_p, out = sys.argv[1], sys.argv[2]
Hp = int(sys.argv[3]) if len(sys.argv) > 3 else 1636
dx = int(sys.argv[4]) if len(sys.argv) > 4 else 0
dy = int(sys.argv[5]) if len(sys.argv) > 5 else 0

c = Image.open(f'{D}/слои/фон_студия.png').convert('RGB').filter(ImageFilter.GaussianBlur(2.2))
c = ImageEnhance.Brightness(c).enhance(0.92).convert('RGBA')

# человек: тёплая коррекция под свет студии
p = Image.open(person_p).convert('RGBA')
p = p.resize((round(p.width * Hp / p.height), Hp), Image.LANCZOS)
arr = np.array(p).astype(np.float32)
arr[..., 0] *= 1.05; arr[..., 1] *= 1.00; arr[..., 2] *= 0.90
p = Image.fromarray(arr.clip(0, 255).astype(np.uint8), 'RGBA')
p = p.filter(ImageFilter.UnsharpMask(radius=1.5, percent=40, threshold=2))
# подрезать серую кромку от хромакея
p.putalpha(p.getchannel('A').filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8)))
px = (W - p.width) // 2 + dx
# тень за человеком — отделяет от фона
sh = Image.new('RGBA', c.size, (0, 0, 0, 0))
sh.paste((0, 0, 0, 50), (px, dy + 30), p.getchannel('A'))
c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(25)))
c.alpha_composite(p, (px, dy))
c = c.convert('RGB')

def shadow(box, r, off=12, blur=18, a=160):
    m = Image.new('L', c.size, 0)
    x0, y0, x1, y1 = box
    ImageDraw.Draw(m).rounded_rectangle((x0, y0 + off, x1, y1 + off), r, fill=a)
    c.paste((0, 0, 0), (0, 0), m.filter(ImageFilter.GaussianBlur(blur)))

def rmask(size, r):
    m = Image.new('L', size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), r, fill=255); return m

S, R, Y = 320, 64, 925
yb = (100, Y, 100 + S, Y + S); fb = (W - 100 - S, Y, W - 100, Y + S)
# YouTube
shadow(yb, R)
g = Image.new('RGB', (S, S)); gd = ImageDraw.Draw(g)
for i in range(S):
    t = i / (S - 1); gd.line((0, i, S, i), fill=(int(255 - 35 * t), int(22 - 18 * t), int(22 - 18 * t)))
c.paste(g, yb[:2], rmask((S, S), R))
ImageDraw.Draw(c).rounded_rectangle(yb, R, outline=(255, 120, 110), width=4)
cx, cy = yb[0] + S / 2 + 10, yb[1] + S / 2
tm = Image.new('L', (W * 2, H * 2), 0)
ImageDraw.Draw(tm).polygon([((cx - 52) * 2, (cy - 68) * 2), ((cx - 52) * 2, (cy + 68) * 2), ((cx + 70) * 2, cy * 2)], fill=255)
c.paste(WHITE, (0, 0), tm.filter(ImageFilter.GaussianBlur(5)).resize(c.size, Image.LANCZOS))
# FV — из чистого логотипа
shadow(fb, R)
fv = Image.open(f'{D}/исходники/logo_FV.jpg').convert('RGB').crop((60, 60, 1220, 1220)).resize((S, S), Image.LANCZOS)
c.paste(fv, fb[:2], rmask((S, S), R))
ImageDraw.Draw(c).rounded_rectangle(fb, R, outline=(214, 172, 92), width=5)
# плюс
d = ImageDraw.Draw(c); pc = (W / 2, Y + S / 2)
for (w_, h_), col in [((92, 30), (0, 0, 0)), ((86, 24), WHITE)]:
    pass
shp = Image.new('L', c.size, 0); sd = ImageDraw.Draw(shp)
for bx in [(pc[0] - 46, pc[1] - 13 + 6, pc[0] + 46, pc[1] + 13 + 6), (pc[0] - 13, pc[1] - 46 + 6, pc[0] + 13, pc[1] + 46 + 6)]:
    sd.rounded_rectangle(bx, 6, fill=150)
c.paste((0, 0, 0), (0, 0), shp.filter(ImageFilter.GaussianBlur(8)))
for bx in [(pc[0] - 46, pc[1] - 13, pc[0] + 46, pc[1] + 13), (pc[0] - 13, pc[1] - 46, pc[0] + 13, pc[1] + 46)]:
    d.rounded_rectangle(bx, 6, fill=WHITE)

# аналитика из старой обложки (незеркальная)
orig = Image.open(f'{D}/исходники/01_FV_plus_GPT.jpg').convert('RGB').resize((W, H), Image.LANCZOS)
card = orig.crop((30, 1275, 1050, 1677))
shadow((30, 1515, 1050, 1917), 24, off=10, blur=20, a=140)
c.paste(card, (30, 1515), rmask(card.size, 24))

plate(c, (25, 1270, 1055, 1525))
text_line(c, W / 2, 1282, [('= YOUTUBE-', WHITE)], 118)
text_line(c, W / 2, 1412, [('МИЛЛИОНЕРЫ ', WHITE), ('2027', YELLOW)], 82)
c.save(out, quality=100, subsampling=0)
