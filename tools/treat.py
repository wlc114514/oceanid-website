import sys, os
import numpy as np
from PIL import Image, ImageOps, ImageFilter
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
NAVY = np.array([5, 14, 36], float); GLOW = np.array([150, 215, 255], float)
W = 1200  # 处理宽度：网页里显示 600px，按 2 倍屏做

def plate(g):
    # 找版画印版的范围，裁掉四周白纸
    a = np.asarray(g.filter(ImageFilter.GaussianBlur(8)), float)
    paper = np.percentile(a, 95)
    m = a < paper - 35
    cols = np.where(m.mean(0) > .04)[0]; rows = np.where(m.mean(1) > .04)[0]
    x0, x1, y0, y1 = cols[0], cols[-1], rows[0], rows[-1]
    pad = int(.015 * g.width)
    return g.crop((x0 + pad, y0 + pad, x1 - pad, y1 - pad))

def tint(a):  # a: 0..1 亮度 → 深蓝..浅蓝
    a = a[..., None]
    return Image.fromarray((NAVY + (GLOW - NAVY) * a).astype(np.uint8))

for n, invert in (('2', True), ('4', True), ('5', False)):
    g = plate(Image.open(os.path.join(src, f'h{n}.jpg')).convert('L'))
    g = ImageOps.autocontrast(g, cutoff=1)
    if invert: g = ImageOps.invert(g)
    g = g.resize((W, int(g.height * W / g.width)), Image.LANCZOS)
    a = np.asarray(g, float) / 255
    if not invert: a = a ** 1.7  # 黑底原图：压暗背景
    # A 干净版画：加一点对比曲线，让线条更利落
    tint(np.clip((a - .08) / .8, 0, 1) ** 1.3).save(f'{out}/{n}-A.png')
    # B 细颗粒抖动（Floyd–Steinberg，1 像素一个点）
    d = np.asarray(Image.fromarray((a ** 1.2 * 255).astype(np.uint8)).convert('1'), float)
    tint(d).save(f'{out}/{n}-B.png')
    # C 扫描线：每 4 行一条，亮的地方线粗、暗的地方线细
    P = 4; h = a.shape[0] // P * P
    band = a[:h].reshape(-1, P, W).mean(1)                 # 每条带的平均亮度
    thick = band[:, None, :] * P                           # 线宽（像素，可带小数）
    yy = np.arange(P)[None, :, None] + .5
    cov = np.clip(thick / 2 - np.abs(yy - P / 2) + .5, 0, 1)  # 线居中，边缘抗锯齿
    tint(cov.reshape(h, W) ** .9).save(f'{out}/{n}-C.png')
print('done')
