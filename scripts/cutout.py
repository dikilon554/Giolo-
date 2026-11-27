"""Вырезать человека с хромакея -> RGBA PNG.
Зелёный ключ даёт альфу; rembg только отсекает не-зелёный мусор вдали от человека;
цвет на полупрозрачной кромке берётся изнутри (без серого ореола от фона)."""
import sys, numpy as np, cv2
from PIL import Image
from rembg import remove, new_session

src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('RGB')
a = np.array(im)
f = a.astype(np.float32); r, g, b = f[..., 0], f[..., 1], f[..., 2]
diff = g - np.maximum(r, b)
alpha = 1 - np.clip((diff - 8) / 22, 0, 1)
seg = np.array(remove(im, session=new_session('u2net_human_seg'), only_mask=True))
seg = cv2.dilate((seg > 60).astype(np.uint8), np.ones((21, 21), np.uint8))
seg = cv2.GaussianBlur(seg.astype(np.float32), (0, 0), 5)
alpha = np.clip(alpha * np.clip(seg * 1.5, 0, 1), 0, 1)
# убрать мелкие дыры/точки
alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
alpha = np.clip((alpha - 0.3) / 0.7, 0, 1)  # срезать дымку над плечами
# цвет кромки: всё, что не уверенно-внутри, перекрашиваем из соседей изнутри
inside = (alpha > 0.97).astype(np.uint8)
band = ((alpha > 0.01) & (inside == 0)).astype(np.uint8)
band = cv2.dilate(band, np.ones((3, 3), np.uint8)) & (1 - inside)
fixed = cv2.inpaint(a, band * 255, 4, cv2.INPAINT_TELEA)
# лёгкий despill внутри (рефлексы зелёного на коже/футболке)
ff = fixed.astype(np.float32)
lim = (ff[..., 0] + ff[..., 2]) / 2 + 8
ff[..., 1] = np.minimum(ff[..., 1], lim)
rgba = np.dstack([ff, alpha * 255]).clip(0, 255).astype(np.uint8)
Image.fromarray(rgba, 'RGBA').save(out)
