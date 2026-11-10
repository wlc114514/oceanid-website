"""入口样品用的抖动图，全部提前算好，网页只负责切换 / 遮罩。
输出到 img/entry/：
  triton-dNNNN.png  下潜开场：同一张 Triton，宽 NNNN 像素的抖动版（透明底），从粗到细依次显示，最后淡出露出 hero-triton.webp
  triton-torch.png  探照灯：大尺寸细颗粒版，网页上用一层带圆孔的暗幕盖住，光圈跟着鼠标走
裁切和 hero-triton.webp 完全一致（同一个 prep），所以几张图叠在一起能严丝合缝。"""
import os
from PIL import Image
from build_images import prep, OUT, NAVY, GLOW

DIR = os.path.join(OUT, 'entry')
GAMMA = 1.15                                # 和 js/dither.js 一致
ABYSS = (2, 6, 15)
LEVELS = [44, 88, 175, 350, 700, 1400]      # 下潜开场的六级颗粒，宽度翻倍 = 颗粒减半


def dither(g, width, paper):
    """缩到 width 宽 → Floyd–Steinberg 抖成两色 → 存成 2 色调色板 PNG（文件很小）"""
    g = g.resize((width, round(g.height * width / g.width)), Image.LANCZOS)
    g = g.point(lambda v: round(255 * (v / 255) ** GAMMA))
    bw = g.convert('1')                     # PIL 自带 Floyd–Steinberg
    p = bw.convert('L').point(lambda v: 1 if v else 0).convert('P')
    p.putpalette(list(paper) + [int(c) for c in GLOW] + [0] * 762)
    return p


if __name__ == '__main__':
    os.makedirs(DIR, exist_ok=True)
    src = prep('RP-P-OB-67.306', True, 3000)
    for w in LEVELS:
        # 透明底：颗粒直接浮在开场的海水颜色上（海水从浅蓝渐变到深蓝）
        dither(src, w, NAVY.astype(int)).save(os.path.join(DIR, f'triton-d{w:04d}.png'), optimize=True, transparency=0)
    dither(src, 1600, ABYSS).save(os.path.join(DIR, 'triton-torch.png'), optimize=True)
    for f in sorted(os.listdir(DIR)):
        print(f, os.path.getsize(os.path.join(DIR, f)) // 1024, 'KB')
