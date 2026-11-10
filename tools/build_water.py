"""下潜开场结尾「出水」用的素材，全部提前渲染，网页只负责换帧、移动。输出到 img/entry/：
  crest/00…35.avif   水面线，36 帧循环（网页上 24 帧/秒，一圈 1.5 秒；波浪流动、浪花闪、气泡往上冒）。
                     上半是不透明的海水色，下半透明露出页面。网页上把它接在一整块海水色下面整体往上推，同时循环播放
  haze/00…47.avif    水膜上的雾，48 帧（网页上 14 帧/秒，约 3.4 秒）：雾一边往下流一边从上往下退掉，最后全透明
  film.avif          = haze 的第 0 帧，动画帧没加载完时的退路（静态图往下滑）
都是和 Triton 一样的两色颗粒（用户比较过写实光滑版，选了颗粒版）。"""
import os
import numpy as np
from PIL import Image
from build_images import OUT

DIR = os.path.join(OUT, 'entry')
SEA = np.array([8, 23, 58], float)       # --surface，开场最后的海水颜色
GLOW = np.array([150, 212, 255], float)  # --glow
HAZE = np.array([22, 48, 96], float)     # 水膜雾气的颜色
TAU = 2 * np.pi
rng = np.random.default_rng(7)


def lowfreq(h, w, cell):
    """平滑的低频噪声，0..1"""
    small = rng.random((h // cell + 3, w // cell + 3))
    im = Image.fromarray((small * 255).astype(np.uint8)).resize((w + 2 * cell, h + 2 * cell), Image.BICUBIC)
    return np.asarray(im, float)[cell:cell + h, cell:cell + w] / 255


def stamp(F, cx, cy, r, fn):
    """在 F 上以 (cx, cy) 为中心、半径 r 的范围里取 max(F, fn(距离/半径, dx, dy))"""
    h, w = F.shape
    x0, x1 = max(0, int(cx - r - 2)), min(w, int(cx + r + 3))
    y0, y1 = max(0, int(cy - r - 2)), min(h, int(cy + r + 3))
    if x0 >= x1 or y0 >= y1: return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    dx, dy = (xx - cx) / r, (yy - cy) / r
    F[y0:y1, x0:x1] = np.maximum(F[y0:y1, x0:x1], fn(np.hypot(dx, dy), dx, dy))


ring = lambda s: (lambda q, dx, dy: np.where(q < 1, np.exp(-((q - .8) / .2) ** 2) * np.clip(s - dy * .7, 0, 1), 0))
dot = lambda v: (lambda q, dx, dy: np.where(q < 1, v * (1 - q * .5), 0))


def fs(field):
    """Floyd–Steinberg：0..1 的密度 → 布尔颗粒"""
    return np.asarray(Image.fromarray((np.clip(field, 0, 1) * 255).astype(np.uint8)).convert('1'), bool)


def save(rgb, a, path, **kw):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), np.clip(a, 0, 1) * 255]).astype(np.uint8), 'RGBA')
    im.save(path, **kw)
    return os.path.getsize(path)


# ---------------- 水面线：24 帧循环 ----------------
# 所有随时间变化的量都用 t 的整数倍频率，最后一帧之后正好回到第 0 帧，循环无缝
CW, CH, CN = 1440, 300, 36
cx = np.arange(CW)
cy = np.arange(CH)[:, None]
bubbles = [(rng.uniform(0, CW), rng.random(), rng.uniform(1.5, 4.5), rng.uniform(50, 130)) for _ in range(140)]
drops = [(rng.uniform(0, CW), rng.random(), rng.uniform(1, 2.5), rng.uniform(30, 70)) for _ in range(60)]


def crest_edge(t):
    return (CH * .45 + 15 * np.sin(TAU * (2 * cx / CW - t)) + 8 * np.sin(TAU * (5 * cx / CW + 2 * t) + 2.1)
            + 4 * np.sin(TAU * (11 * cx / CW - 3 * t) + .4) + 2 * np.sin(TAU * (23 * cx / CW + 4 * t)))


def crest_frame(t):
    edge = crest_edge(t)
    d = cy - edge[None, :]                       # >0：水面线下面（页面那侧）
    shimmer = .55 + .45 * np.sin(TAU * (17 * cx / CW + t)) * np.sin(TAU * (7 * cx / CW - 2 * t) + 1)
    foam = np.exp(-(d / 6) ** 2) * (.6 + .4 * shimmer) + np.exp(-((d + 12) / 14) ** 2) * .25 * shimmer
    sheet = np.where(d > 0, .18 * np.exp(-d / 40), 0)
    sp = np.zeros((CH, CW))
    for x0, ph, r, rise in bubbles:              # 气泡：在水里往上冒，越往上越小
        p = (ph + t) % 1
        x = x0 + 3 * np.sin(TAU * (p * 2 + ph))
        stamp(sp, x, edge[int(x0)] - 5 - p * rise, r * (1 - .6 * p), ring(.5 + .5 * (1 - p)))
    for x0, ph, r, fall in drops:                # 水面下挂着、往下掉的水点
        p = (ph + t) % 1
        stamp(sp, x0, edge[int(x0)] + 4 + p * fall, r, dot(.9 * (1 - p)))
    return np.clip(foam + sheet + sp, 0, 1), d < 0, d


# ---------------- 水膜上的雾：48 帧 ----------------
# 在 960×600 上模拟和出图（网页上用 pixelated 放大，颗粒约 1.5 像素，体积小一半多）
DN, DW, DH = 48, 960, 600
rngd = np.random.default_rng(11)
Yd, Xd = np.mgrid[0:DH, 0:DW].astype(float)
haze_tall = .5 + .2 * (lowfreq(DH * 2, DW, 110) - .5) + .1 * (lowfreq(DH * 2, DW, 30) - .5)   # 比画面高一倍，往下卷动 = 雾在流


def haze_frame(t):
    # 雾的退去线：整体往下走，同时几组正弦以不同速度左右流动
    front = ((-.2 + 1.45 * t ** 1.35) * DH + 22 * np.sin(TAU * 1.3 * Xd[0] / DW + 7 * t)
             + 10 * np.sin(TAU * 3.7 * Xd[0] / DW - 11 * t + 1) + 4 * np.sin(TAU * 9 * Xd[0] / DW + 17 * t))
    d = Yd - front[None, :]
    off = int(t * DH * .45)                                        # 雾的纹理往下流
    haze = haze_tall[DH - off:2 * DH - off] * np.clip(d / 90, 0, 1) * (1 - .4 * t)
    rim = np.exp(-((d - 8) / 10) ** 2) * .14                       # 退去线上一道很淡的水光
    end = np.clip((1 - t) / .08, 0, 1)                             # 最后几帧整体淡到全透明
    return haze * end, rim * end


if __name__ == '__main__':
    size = {}
    add = lambda k, n: size.__setitem__(k, size.get(k, 0) + n)
    for k in range(CN):
        light, above, d = crest_frame(k / CN)
        # 亮处抖成 GLOW 点；水面上方其余是不透明海水色，下方其余透明
        on = fs(light ** 1.1)
        add('crest', save(np.where(on[..., None], GLOW, SEA), np.where(on | above, 1., 0.),
                          os.path.join(DIR, 'crest', f'{k:02d}.avif'), quality=75, speed=6))

    T1, T2 = rngd.random((DH, DW)), rngd.random((DH, DW))     # 固定阈值：雾的颗粒跟着雾走，不会每帧乱闪
    for k in range(DN):
        haze, rim = haze_frame(k / (DN - 1))
        dots_r, dots_h = rim * 1.4 > T2, haze * .5 > T1
        rgb, a = np.where(dots_r[..., None], GLOW, HAZE), np.where(dots_r | dots_h, 1., 0.)
        add('haze', save(rgb, a, os.path.join(DIR, 'haze', f'{k:02d}.avif'), quality=70, speed=6))
        if k == 0: save(rgb, a, os.path.join(DIR, 'film.avif'), quality=70, speed=6)

    for k, v in size.items():
        print(k, v // 1024, 'KB')
