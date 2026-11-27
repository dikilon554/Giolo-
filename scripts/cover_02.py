"""Обложка 02: YouTube + FV = YouTube-миллионеры 2027 (фото 1, зеркально)."""
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from cover import W, H, WHITE, YELLOW, plate, text_line

src, out = sys.argv[1], sys.argv[2]
orig = Image.open(src).convert('RGB').resize((W, H), Image.LANCZOS)
orig = orig.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
c = ImageOps.mirror(orig)

def shadow(box, r, off=12, blur=18, a=160):
    m = Image.new('L', c.size, 0)
    x0, y0, x1, y1 = box
    ImageDraw.Draw(m).rounded_rectangle((x0, y0 + off, x1, y1 + off), r, fill=a)
    c.paste((0, 0, 0), (0, 0), m.filter(ImageFilter.GaussianBlur(blur)))

# FV: незеркальная иконка из оригинала -> на место зеркальной
fv = orig.crop((150, 948, 468, 1254))
fvm = Image.new('L', fv.size, 0)
ImageDraw.Draw(fvm).rounded_rectangle((0, 0, fv.width - 1, fv.height - 1), 52, fill=255)
c.paste(fv, (1080 - 468, 948), fvm)

# YouTube-иконка поверх GPT (зеркальный GPT: x 108..435, y 942..1257)
yb = (104, 940, 440, 1262); r = 62
shadow(yb, r)
w, h = yb[2] - yb[0], yb[3] - yb[1]
g = Image.new('RGB', (w, h)); gd = ImageDraw.Draw(g)
for i in range(h):
    t = i / (h - 1); gd.line((0, i, w, i), fill=(int(255 - 35 * t), int(20 - 18 * t), int(20 - 18 * t)))
m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
c.paste(g, yb[:2], m)
d = ImageDraw.Draw(c)
d.rounded_rectangle(yb, r, outline=(255, 120, 110), width=4)
cx, cy = (yb[0] + yb[2]) / 2 + 10, (yb[1] + yb[3]) / 2
tri = [(cx - 52, cy - 68), (cx - 52, cy + 68), (cx + 70, cy)]
tm = Image.new('L', (c.width * 2, c.height * 2), 0)  # сглаженный треугольник
ImageDraw.Draw(tm).polygon([(x * 2, y * 2) for x, y in tri], fill=255)
tm = tm.filter(ImageFilter.GaussianBlur(5)).resize(c.size, Image.LANCZOS)
c.paste(WHITE, (0, 0), tm)

# аналитика: незеркальная карточка ниже плашки
card = orig.crop((30, 1275, 1050, 1677))
shadow((30, 1515, 1050, 1917), 24, off=10, blur=20, a=140)
cm = Image.new('L', card.size, 0)
ImageDraw.Draw(cm).rounded_rectangle((0, 0, card.width - 1, card.height - 1), 24, fill=255)
c.paste(card, (30, 1515), cm)

# плашка
plate(c, (25, 1270, 1055, 1525))
text_line(c, W / 2, 1282, [('= YOUTUBE-', WHITE)], 118)
text_line(c, W / 2, 1412, [('МИЛЛИОНЕРЫ ', WHITE), ('2027', YELLOW)], 82)
c.save(out, quality=100, subsampling=0)
