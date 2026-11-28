"""Фон студии из кадра ролика: убрать спикера (rembg) и впечатанный хук сверху, залить inpaint.
python cover_bg_video.py frame.png out.png [text_y0 text_y1] (в координатах кадра 720x1280)"""
import sys, numpy as np, cv2
from PIL import Image
from rembg import remove, new_session

src, out = sys.argv[1], sys.argv[2]
ty0, ty1 = (int(v) for v in sys.argv[3:5]) if len(sys.argv) > 4 else (80, 215)
im = Image.open(src).convert('RGB')
a = np.array(im)
m = np.array(remove(im, session=new_session('u2net_human_seg'), only_mask=True))
m = cv2.dilate((m > 30).astype(np.uint8) * 255, np.ones((15, 15), np.uint8))
# хук: белый текст + обводка + эмодзи в верхней полосе -> прямоугольник по найденному тексту
band = a[ty0:ty1].astype(int)
white = (band.min(-1) > 225)
ys, xs = np.where(white)
if len(xs):
    x0, x1, y0, y1 = xs.min() - 14, xs.max() + 40, ys.min() + ty0 - 12, ys.max() + ty0 + 14
    m[max(y0, 0):y1, max(x0, 0):x1] = 255
# низ кадра (микрофон, стол) всё равно закрыт человеком и плашкой — тоже в маску
m[int(a.shape[0] * 0.62):] = 255
big = cv2.resize(a, (1080, 1920), interpolation=cv2.INTER_LANCZOS4)
mb = cv2.resize(m, (1080, 1920), interpolation=cv2.INTER_NEAREST)
small = cv2.resize(big, (540, 960), interpolation=cv2.INTER_AREA)
ms = cv2.resize(mb, (540, 960), interpolation=cv2.INTER_NEAREST)
fill = cv2.inpaint(small, ms, 12, cv2.INPAINT_TELEA)
fill = cv2.GaussianBlur(cv2.resize(fill, (1080, 1920), interpolation=cv2.INTER_CUBIC), (0, 0), 5)
mf = cv2.GaussianBlur(mb, (0, 0), 6)[..., None] / 255.0
res = (big * (1 - mf) + fill * mf).astype(np.uint8)
Image.fromarray(res).save(out)
Image.fromarray(mb).save(out.replace('.png', '_mask.png'))
