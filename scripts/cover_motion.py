"""Обложка в стиле моушена (светлый фон, кружки, синие/красные цифры, красные таблетки), без аватара."""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import sys, os, random
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, '..', 'assets', 'fonts', 'Montserrat_800ExtraBold.ttf')
W, H = 1080, 1920
RED, BLUE, NAVY, WHITE = (214, 29, 45), (31, 93, 206), (17, 26, 57), (255, 255, 255)

frame, logo, out = sys.argv[1], sys.argv[2], sys.argv[3]

# фон: как в видео — светлый холодный градиент + размытые красные/синие кружки
c = Image.new('RGB', (W, H)); d = ImageDraw.Draw(c)
for y in range(H):
    t = y / H; d.line((0, y, W, y), fill=(int(243 - 12 * t), int(246 - 6 * t), int(251 - 4 * t)))
dots = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(dots)
random.seed(7)
for _ in range(38):
    r = random.randint(14, 48); x, y = random.randint(0, W), random.randint(0, H)
    col = random.choice([(220, 60, 70), (70, 120, 220), (180, 190, 220)])
    dd.ellipse((x - r, y - r, x + r, y + r), fill=col + (random.randint(18, 40),))
c.paste(dots.filter(ImageFilter.GaussianBlur(6)), (0, 0), dots.filter(ImageFilter.GaussianBlur(6)))

# веер превью из кадра видео, края растворяются в фоне
fan = Image.open(frame).convert('RGB').crop((0, 120, 720, 520)).resize((1080, 600), Image.LANCZOS)
fan = fan.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2))
m = Image.new('L', fan.size, 0); ImageDraw.Draw(m).rectangle((40, 30, 1040, 570), fill=255)
c.paste(fan, (0, 150), m.filter(ImageFilter.GaussianBlur(28)))

d = ImageDraw.Draw(c)
def F(s): return ImageFont.truetype(FONT, s)
def center(parts, y, size):
    f = F(size); ws = [d.textlength(t, font=f) for t, _ in parts]; x = (W - sum(ws)) / 2
    for (t, col), w in zip(parts, ws):
        d.text((x, y), t, font=f, fill=col); x += w

center([('114 000', BLUE)], 760, 210)
center([('ПОДПИСЧИКОВ', NAVY)], 1000, 112)
center([('ЗА ', NAVY), ('31', RED), (' МУЛЬТИК', NAVY)], 1140, 100)

def pill(text, cy, size=58):
    f = F(size); w = d.textlength(text, font=f); h = size * 1.45
    x0, x1 = (W - w) / 2 - 38, (W + w) / 2 + 38
    d.rounded_rectangle((x0, cy - h / 2, x1, cy + h / 2), h / 2, fill=RED)
    d.text((W / 2, cy), text, font=f, fill=WHITE, anchor='mm')
pill('БЕЗ АНИМАЦИИ —', 1345)
pill('ТОЛЬКО КАРТИНКИ', 1450)

# знак Forge Vision внизу
S = 96
lg = Image.open(logo).convert('RGB').crop((60, 60, 1220, 1220)).resize((S, S), Image.LANCZOS)
lm = Image.new('L', (S, S), 0); ImageDraw.Draw(lm).rounded_rectangle((0, 0, S - 1, S - 1), 22, fill=255)
f = F(52); tw = d.textlength('Forge Vision', font=f); x0 = (W - (S + 22 + tw)) / 2; y0 = 1570
c.paste(lg, (int(x0), y0), lm)
d.text((x0 + S + 22, y0 + S / 2), 'Forge Vision', font=f, fill=NAVY, anchor='lm')
c.save(out, quality=100, subsampling=0)
