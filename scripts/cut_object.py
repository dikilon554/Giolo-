import sys, numpy as np, onnxruntime as ort
from PIL import Image, ImageDraw
S = sys.argv[1]
sess = ort.InferenceSession(f'{S}/rmbg/birefnet.onnx')
def cut(src, box, out):
    im = Image.open(f'{S}/covers_src/{src}').convert('RGB')
    im = im.resize((1280, int(im.height * 1280 / im.width)))
    c = im.crop(box)
    x = np.asarray(c.resize((1024, 1024), Image.BILINEAR), dtype=np.float32) / 255
    x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    y = sess.run(None, {'input_image': x.transpose(2, 0, 1)[None].astype(np.float32)})[0][0, 0]
    y = 1 / (1 + np.exp(-y)) if y.min() < 0 or y.max() > 1 else y
    m = Image.fromarray((np.clip(y, 0, 1) * 255).astype('uint8')).resize(c.size, Image.BILINEAR)
    c.putalpha(m)
    bb = m.point(lambda v: 255 if v > 40 else 0).getbbox()
    c = c.crop(bb) if bb else c
    c.save(f'{S}/objs/{out}.png'); return c
import os; os.makedirs(f'{S}/objs', exist_ok=True)
jobs = {
 'coin_f':      ('05.jpg', (1035, 15, 1200, 165)),
 'coin_f_2':    ('05.jpg', (145, 400, 295, 535)),
 'servers':     ('05.jpg', (1085, 315, 1280, 620)),
 'youtube':     ('11.jpg', (975, 245, 1265, 510)),
 'youtube_2':   ('06.jpg', (840, 270, 1220, 520)),
 'trophy':      ('10.jpg', (930, 120, 1280, 600)),
 'trophy_2':    ('09.jpg', (930, 100, 1280, 620)),
 'gear':        ('07.jpg', (150, 175, 315, 310)),
 'pen':         ('08.jpg', (1000, 400, 1280, 720)),
 'coins_rub':   ('04.jpg', (1180, 130, 1280, 280)),
 'people':      ('05.jpg', (840, 470, 1160, 720)),
}
outs = [(k, cut(*v, k)) for k, v in jobs.items()]
W = 330; sheet = Image.new('RGB', (W * 4, W * 3), 'white')
for i, (k, c) in enumerate(outs):
    t = Image.new('RGB', (W - 10, W - 10)); d = ImageDraw.Draw(t)
    for yy in range(0, W, 20):
        for xx in range(0, W, 20): d.rectangle([xx, yy, xx + 19, yy + 19], fill=(200, 200, 200) if (xx + yy) // 20 % 2 else (240, 240, 240))
    cc = c.copy(); cc.thumbnail((W - 30, W - 40)); t.paste(cc, (10, 25), cc); ImageDraw.Draw(t).text((5, 5), k, fill='red')
    sheet.paste(t, ((i % 4) * W + 5, (i // 4) * W + 5))
sheet.save(f'{S}/objs/sheet.jpg')
