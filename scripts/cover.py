#!/usr/bin/env python3
"""Обложка к посту Telegram-канала Forge Media в едином стиле (правила: знания/обложки.md).

Шаблон один и тот же: фон с обложки «3 функции» (оранжевые полосы, сетка), логотип FM слева сверху,
заголовок в две строки (белая + оранжевая), тёмная плашка с подписью, эмодзи Apple как 3D-предметы.
Меняются только тексты и эмодзи.

Пример:
  python3 scripts/cover.py --out посты/2026-11-30_обложка.jpg \
      --line1 "УЮТНЫЕ ЗИМНИЕ" --line2 "ИСТОРИИ" --plate "тренд |ДЕКАБРЯ" \
      --emoji coffee:1120:420:230 --emoji snowflake:1150:140:110:15 \
      --emoji snowflake:120:610:120:-10 --emoji snowflake:1060:615:80:25

--plate: «белая часть |оранжевая часть». --emoji: имя:x:y:размер[:угол], имена — файлы в assets/cover/emoji/
(эмодзи Apple 64 px; лучше качество — положить PNG крупнее с тем же именем).
"""
import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / 'assets'
W, H = 1280, 720
F_TITLE = str(A / 'fonts/Montserrat_900Black_full.ttf')
SQUEEZE = 0.74                      # сужение заголовка по ширине, как в эталоне
WHITE, ORANGE = (255, 255, 255), (255, 140, 30)
ORANGE_TOP, ORANGE_BOT = (255, 176, 64), (255, 92, 0)


def grad(size, top, bot):
    w, h = size
    g = Image.new('RGB', (1, h))
    for y in range(h):
        k = y / max(h - 1, 1)
        g.putpixel((0, y), tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3)))
    return g.resize((w, h))


def background():
    bg = Image.open(A / 'cover/bg_base.png').convert('RGB')
    grid = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(grid)
    for x in range(-10, W, 46):
        d.line([(x, 0), (x, H)], fill=255)
    for y in range(-10, H, 46):
        d.line([(0, y), (W, y)], fill=255)
    fade = Image.new('L', (W, H), 0)
    ImageDraw.Draw(fade).ellipse([150, 60, 1130, 660], fill=255)
    grid = ImageChops.multiply(grid, fade.filter(ImageFilter.GaussianBlur(90))).point(lambda v: int(v * 0.10))
    bg.paste((90, 80, 75), (0, 0), grid)
    noise = Image.effect_noise((W, H), 14).convert('RGB')
    return Image.blend(bg, ImageChops.add(bg, noise, scale=8), 0.4)


def emoji(img, name, cx, cy, size, angle=0):
    e = Image.open(A / f'cover/emoji/{name}.png').convert('RGBA').resize((size, size), Image.LANCZOS)
    if angle:
        e = e.rotate(angle, Image.BICUBIC, expand=True)
    e = e.filter(ImageFilter.UnsharpMask(2, 60, 2))
    x, y = int(cx - e.width / 2), int(cy - e.height / 2)
    sh = Image.new('L', img.size, 0)
    sh.paste(e.getchannel('A'), (x + 8, y + 14))
    img.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.6)))
    img.paste(e, (x, y), e)


def text_layer(text, size, top, bot):
    f = ImageFont.truetype(F_TITLE, size)
    l, t, r, b = f.getbbox(text)
    w, h = r - l + 20, b - t + 20
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).text((10 - l, 10 - t), text, font=f, fill=255)
    mask = mask.resize((int(w * SQUEEZE), h), Image.LANCZOS)
    return grad(mask.size, top, bot), mask


def paste_title(img, col, mask, cx, y, glow):
    x = int(cx - mask.width / 2)
    sh = Image.new('L', img.size, 0)
    sh.paste(mask, (x + 4, y + 8))
    img.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.85)))
    if glow:  # лёгкое тёплое свечение только у оранжевой строки
        gl = Image.new('L', img.size, 0)
        gl.paste(mask, (x, y))
        img.paste((255, 110, 10), (0, 0), gl.filter(ImageFilter.GaussianBlur(26)).point(lambda v: int(v * 0.22)))
    img.paste(col, (x, y), mask)


def fit_size(text, max_w, start=200):  # 200 — потолок, чтобы короткие слова не были огромными
    s = start
    while s > 40:
        l, _, r, _ = ImageFont.truetype(F_TITLE, s).getbbox(text)
        if (r - l) * SQUEEZE <= max_w:
            return s
        s -= 4
    return s


def plate(img, white, orange, cx, cy):
    f = ImageFont.truetype(F_TITLE, 50)
    parts = [(white.strip().upper(), WHITE), (orange.strip().upper(), ORANGE)]
    parts = [p for p in parts if p[0]]
    widths = [f.getbbox(t)[2] - f.getbbox(t)[0] for t, _ in parts]
    gap = 18
    pw, ph = sum(widths) + gap * (len(parts) - 1) + 110, 88
    x0, y0 = int(cx - pw / 2), int(cy - ph / 2)
    gl = Image.new('L', img.size, 0)
    ImageDraw.Draw(gl).rounded_rectangle([x0, y0, x0 + pw, y0 + ph], 18, outline=255, width=6)
    img.paste((255, 110, 10), (0, 0), gl.filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * 0.25)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], 18, fill=(14, 12, 11), outline=(120, 90, 70), width=2)
    d.line([(x0 + 30, y0 + ph), (x0 + pw - 30, y0 + ph)], fill=(255, 130, 40), width=2)
    x = x0 + 55
    for (t, c), w in zip(parts, widths):
        d.text((x, cy), t, font=f, fill=c, anchor='lm')
        x += w + gap


def make(line1, line2, plate_text, objects, out):
    img = background()
    for o in objects:
        emoji(img, *o)
    side = any(o[1] > 1000 and o[3] >= 180 for o in objects)  # крупный предмет справа → текст левее
    max_w, cx = (860, 560) if side else (1000, W // 2)
    s = min(fit_size(line1, max_w), fit_size(line2, max_w))
    c1, m1 = text_layer(line1, s, (255, 255, 255), (205, 205, 205))
    c2, m2 = text_layer(line2, s, ORANGE_TOP, ORANGE_BOT)
    gap = -int(s * 0.16)
    y1 = int((H - (m1.height + m2.height + gap + 115)) / 2) + 10
    paste_title(img, c1, m1, cx, y1, False)
    paste_title(img, c2, m2, cx, y1 + m1.height + gap, True)
    if plate_text:
        white, _, orange = plate_text.partition('|')
        plate(img, white, orange, cx, y1 + m1.height + m2.height + gap + 70)
    logo = Image.open(A / 'cover/fm_logo.png')
    img.paste(logo, (30, 30), logo)
    img.save(out, quality=93)
    print(f'Обложка: {out}')


def parse_emoji(s):
    p = s.split(':')
    return (p[0], int(p[1]), int(p[2]), int(p[3]), float(p[4]) if len(p) > 4 else 0)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Обложка поста Forge Media')
    ap.add_argument('--line1', required=True, help='белая строка заголовка')
    ap.add_argument('--line2', required=True, help='оранжевая строка заголовка')
    ap.add_argument('--plate', default='', help='подпись на плашке: «белое |ОРАНЖЕВОЕ»')
    ap.add_argument('--emoji', action='append', default=[], help='имя:x:y:размер[:угол]')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    make(a.line1, a.line2, a.plate, [parse_emoji(e) for e in a.emoji], a.out)
