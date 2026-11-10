"""把 assets/originals 里的版画处理成网页用图，输出到 img/。全部离线算好，浏览器里不做任何颗粒计算。
A（干净版画）：反相 + 染深蓝，存 WebP。
B（抖动颗粒）：裁边/反相/对比度 → Floyd–Steinberg 抖动成两色 PNG，输出到 img/dither/。
   每张图按页面上的显示尺寸（CSS 像素）出图，一个颗粒 = 1 个 CSS 像素，页面上不缩放、只裁切。
   Windows 常见的 125% / 150% / 175% 缩放各出一份（-d125 / -d150 / -d175），让颗粒正好落在屏幕像素上；
   页面用 <picture> 按屏幕缩放比例选图，其余情况（100%、200%、300%）用不带后缀的那张。
ROV 转盘：assets/rov-cad/renders/spin/*.png → 染色 → img/rov-spin/*.avif"""
import os
import numpy as np
from PIL import Image, ImageOps, ImageFilter, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, OUT = os.path.join(ROOT, 'assets', 'originals'), os.path.join(ROOT, 'img')
NAVY, GLOW = (5, 13, 32), (150, 212, 255)   # 底色（和首页大图的暗部一致）、版画墨色
CARD_INK = (96, 150, 210)                   # 任务难点卡片上的版画：比 GLOW 暗一档，不抢 ROV 的戏

# A：(原图编号, 输出名, 是否反相, 输出宽度)
CLEAN = [
    ('RP-P-OB-67.306', 'hero-triton', True, 1400),
]
# B：(原图编号, 输出名, 是否反相, 四边各裁掉的比例[左,上,右,下], 墨色, [(显示宽, 显示高) …], 椭圆蒙版)
#    取景框和显示尺寸比例不一样时，居中裁切到显示尺寸
DITHER = [
    ('RP-P-OB-10.470', 'oceanus', True, (0, 0, 0, 0), GLOW, [(360, 478), (300, 398)], True),
    ('RP-P-2015-17-124-3', 'jonah-whale', True, (.04, .40, .04, .16), CARD_INK, [(560, 240)], False),
    ('RP-P-OB-29.395', 'ship-storm', True, (0, .06, 0, .30), CARD_INK, [(560, 240)], False),
    ('RP-P-1964-2468', 'sea-horse', True, (.09, .13, .09, .17), CARD_INK, [(560, 240)], False),   # 裁到印版边框线以内
]
DENSITIES = [1, 1.25, 1.5, 1.75]   # 屏幕缩放比例
GAMMA = 1.15                       # >1 让画面整体更暗、颗粒更稀

def plate(g):
    # 找印版范围，裁掉四周白纸和博物馆的标签
    a = np.asarray(g.filter(ImageFilter.GaussianBlur(8)), float)
    m = a < np.percentile(a, 95) - 35
    cols = np.where(m.mean(0) > .04)[0]; rows = np.where(m.mean(1) > .04)[0]
    pad = int(.015 * g.width)
    return g.crop((cols[0] + pad, rows[0] + pad, cols[-1] - pad, rows[-1] - pad))

def prep(key, invert, width, extra=(0, 0, 0, 0), oval=False):
    """裁边 → 对比度 → 反相 → 纸色压黑 → 缩放，返回灰度图（亮 = 线条）"""
    g = plate(Image.open(os.path.join(SRC, key + '.jpg')).convert('L'))
    l, t, r, b = extra
    g = g.crop((int(g.width * l), int(g.height * t), int(g.width * (1 - r)), int(g.height * (1 - b))))
    g = ImageOps.autocontrast(g, cutoff=1)
    if invert: g = ImageOps.invert(g)
    # 纸色（反相后是最常见的暗色调）压成纯黑，免得背景发灰
    hist = np.bincount(np.asarray(g).ravel(), minlength=256)
    paper = int(np.argmax(hist[:160]))
    g = g.point(lambda v: max(0, round((v - paper) * 255 / (255 - paper))))
    if oval:  # 椭圆画面：椭圆以外的四角涂黑，不然纸纹会抖出杂点
        mask = Image.new('L', g.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, g.width - 1, g.height - 1), fill=255)
        g = Image.composite(g, Image.new('L', g.size, 0), mask)
    width = min(width, g.width)
    return g.resize((width, round(g.height * width / g.width)), Image.LANCZOS)

def cover(g, w, h):
    """缩放到刚好盖住 w×h，居中裁掉多出来的部分"""
    s = max(w / g.width, h / g.height)
    g = g.resize((max(w, round(g.width * s)), max(h, round(g.height * s))), Image.LANCZOS)
    x, y = (g.width - w) // 2, (g.height - h) // 2
    return g.crop((x, y, x + w, y + h))

def dither(g):
    """蛇形扫描的 Floyd–Steinberg：误差按 7/16、3/16、5/16、1/16 分给周围像素。返回 0/1 数组"""
    h, w = g.height, g.width
    lum = (np.asarray(g, float) / 255) ** GAMMA
    rows = [list(r) for r in lum] + [[0.0] * w]
    for y in range(h):
        row, nxt = rows[y], rows[y + 1]
        d = -1 if y % 2 else 1
        for k in range(w):
            x = k if d == 1 else w - 1 - k
            v = 1.0 if row[x] >= .5 else 0.0
            e = row[x] - v
            row[x] = v
            xn, xp = x + d, x - d
            if 0 <= xn < w:
                row[xn] += e * .4375; nxt[xn] += e * .0625
            if 0 <= xp < w: nxt[xp] += e * .1875
            nxt[x] += e * .3125
    return np.array(rows[:h], np.uint8)

def suffix(d):
    return '' if d == 1 else f'-d{round(d * 100)}'

def main():
    for key, name, invert, width in CLEAN:
        g = prep(key, invert, width)
        a = np.clip((np.asarray(g, float) / 255 - .08) / .8, 0, 1) ** 1.3
        navy, glow = np.array(NAVY, float), np.array(GLOW, float)
        Image.fromarray((navy + (glow - navy) * a[..., None]).astype(np.uint8)).save(
            os.path.join(OUT, name + '.webp'), quality=88, method=6)
        print(name, g.size)

    os.makedirs(os.path.join(OUT, 'dither'), exist_ok=True)
    for key, name, invert, crop, ink, sizes, oval in DITHER:
        g = prep(key, invert, 2400, crop, oval)
        for w, h in sizes:
            for d in DENSITIES:
                dot = int(d + .5)   # 每个颗粒占几个屏幕像素
                bits = dither(cover(g, round(w * d / dot), round(h * d / dot)))
                im = Image.fromarray(bits, 'P')
                im.putpalette(list(NAVY) + list(ink))
                tag = f'-{w}' if len(sizes) > 1 else ''
                im.save(os.path.join(OUT, 'dither', f'{name}{tag}{suffix(d)}.png'), optimize=True, bits=1)
        print(name, sizes)

    # ROV 转盘：assets/rov-cad/renders/spin/000.png … → img/rov-spin/000.avif …（同样染成 A 风格）
    # 用 AVIF：体积是 WebP 的一半，画质肉眼无差别
    SPIN_DIR = os.path.join(ROOT, 'assets', 'rov-cad', 'renders', 'spin')
    frames = sorted(f for f in os.listdir(SPIN_DIR) if f.endswith('.png')) if os.path.isdir(SPIN_DIR) else []
    if frames:
        os.makedirs(os.path.join(OUT, 'rov-spin'), exist_ok=True)
        navy, glow = np.array(NAVY, float), np.array(GLOW, float)
        for f in frames:
            r = np.asarray(Image.open(os.path.join(SPIN_DIR, f)).convert('I;16'), float) / 65535
            a = np.clip(r / .92, 0, 1) ** 1.1
            Image.fromarray((navy + (glow - navy) * a[..., None]).astype(np.uint8)).save(
                os.path.join(OUT, 'rov-spin', f[:-4] + '.avif'), quality=55, speed=6)
        print('rov-spin', len(frames), '张')

if __name__ == '__main__':
    main()
