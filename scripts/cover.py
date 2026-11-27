"""Обложки рилсов: красная плашка + белый/жёлтый текст, 1080x1920."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sys, os

W, H = 1080, 1920
FONT = os.path.join(os.path.dirname(__file__), '..', 'assets', 'fonts', 'Montserrat_800ExtraBold.ttf')
WHITE, YELLOW = (255, 255, 255), (255, 226, 26)

def fit_photo(path, mirror=False):
    im = Image.open(path).convert('RGB')
    if mirror:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))

def plate(canvas, box, r=42):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    # тень
    sh = Image.new('L', canvas.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 14, x1, y1 + 14), r, fill=170)
    sh = sh.filter(ImageFilter.GaussianBlur(22))
    canvas.paste((0, 0, 0), (0, 0), sh)
    # вертикальный градиент красного
    g = Image.new('RGB', (w, h))
    gd = ImageDraw.Draw(g)
    for i in range(h):
        t = i / max(h - 1, 1)
        c = (int(242 - 40 * t), int(18 - 14 * t), int(14 - 10 * t))
        gd.line((0, i, w, i), fill=c)
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    canvas.paste(g, (x0, y0), m)
    # светлая кромка
    ImageDraw.Draw(canvas).rounded_rectangle(box, r, outline=(255, 90, 80), width=4)

def text_line(canvas, cx, y, parts, size):
    """parts: [(текст, цвет), ...] — строка по центру с тенью."""
    f = ImageFont.truetype(FONT, size)
    d = ImageDraw.Draw(canvas)
    widths = [d.textlength(t, font=f) for t, _ in parts]
    x = cx - sum(widths) / 2
    sh = Image.new('L', canvas.size, 0)
    sd = ImageDraw.Draw(sh)
    xx = x
    for (t, _), w in zip(parts, widths):
        sd.text((xx + 5, y + 7), t, font=f, fill=255); xx += w
    sh = sh.filter(ImageFilter.GaussianBlur(5))
    canvas.paste((60, 0, 0), (0, 0), sh)
    for (t, c), w in zip(parts, widths):
        d.text((x, y), t, font=f, fill=c, stroke_width=2, stroke_fill=(90, 0, 0)); x += w

if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    c = fit_photo(src)
    # плашка ровно поверх старой (в исходнике y≈730..900 из 1280)
    plate(c, (55, 1090, 1025, 1345))
    text_line(c, W / 2, 1105, [('$80 000', WHITE)], 118)
    text_line(c, W / 2, 1235, [('ЗА ', WHITE), ('9 МЕСЯЦЕВ', YELLOW)], 84)
    c.save(out, quality=100, subsampling=0)
