"""Чистый фон студии: убрать человека со старой обложки.
Бока: полки повторяются вниз с периодом полки. Центр: стена заливается inpaint."""
import sys, numpy as np, cv2
from PIL import Image
from rembg import remove, new_session

src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('RGB').resize((1080, 1920), Image.LANCZOS)
im = im.transpose(Image.FLIP_LEFT_RIGHT)
a = np.array(im)
m = np.array(remove(im, session=new_session('u2net_human_seg'), only_mask=True))
m = cv2.dilate((m > 30).astype(np.uint8) * 255, np.ones((31, 31), np.uint8))

# стык прячем под полку: (колонки, с какой строки тянуть, период полки)
res = a.copy(); mm = m.copy()
for (x0, x1), Y0, P in [((0, 780), 524, 268), ((780, 1080), 516, 280)]:
    for y in range(Y0, 1920):     # тянем полки вниз, маска едет вместе с ними
        res[y, x0:x1] = res[y - P, x0:x1]
        mm[y, x0:x1] = mm[y - P, x0:x1]
small = cv2.resize(res, (540, 960), interpolation=cv2.INTER_AREA)
ms = cv2.resize(mm, (540, 960), interpolation=cv2.INTER_NEAREST)
fill = cv2.inpaint(small, ms, 15, cv2.INPAINT_TELEA)
fill = cv2.GaussianBlur(cv2.resize(fill, (1080, 1920), interpolation=cv2.INTER_CUBIC), (0, 0), 4)
mf = cv2.GaussianBlur(mm, (0, 0), 6)[..., None] / 255.0
res = (res * (1 - mf) + fill * mf).astype(np.uint8)
Image.fromarray(res).save(out)
