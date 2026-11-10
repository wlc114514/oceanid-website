"""从 index.html 生成两个入口样品页到 demos/（首页本身不动）。index.html 改了以后重跑一次即可。
  demos/entry-torch.html  1. 探照灯：首屏换成黑底 + 跟着鼠标走的光圈
  demos/entry-dive.html   2. 下潜开场：首页不变，打开时先播 3 秒多的下潜动画"""
import os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()

# 样品在 demos/ 里，资源路径都要往上一级
src = re.sub(r'(src|href|data-pattern)="(img|js|css|fonts)/', r'\1="../\2/', src)

BAR = '''<nav class="demo-bar" aria-label="Demo switcher">
  <b>DEMO</b>
  <a href="entry-torch.html"{t}>1 · Searchlight</a>
  <a href="entry-dive.html"{d}>2 · Descent</a>
  <a href="../index.html">Current site</a>{extra}
</nav>
'''
CUR = ' aria-current="page"'

TORCH_HERO = '''<section class="hero torch" data-depth="0">
    <div class="torch-art">
      <div class="torch-view">
        <img src="../img/entry/triton-torch.png" width="1600" height="1816" alt="Engraving of Triton kneeling in the sea, blowing into a conch shell" draggable="false">
        <div class="torch-dark"></div>
      </div>
      <span class="label torch-hint" aria-hidden="true"><span class="h-mouse">◎ Move to light the deep</span><span class="h-touch">◎ Touch &amp; hold</span></span>
      <p class="label torch-cap"><b>FIG. 01 — Triton, herald of the sea.</b> Rijksmuseum, RP-P-OB-67.306 (CC0)</p>
    </div>
    <div class="wrap">
      \\1
    </div>
  </section>'''


def page(html, name, title, extra_head, extra_body, bar):
    html = html.replace('<title>Oceanid Robotics</title>', f'<title>{title}</title>')
    html = html.replace('</head>', extra_head + '</head>')
    html = html.replace('</body>', bar + extra_body + '</body>')
    open(os.path.join(ROOT, 'demos', name), 'w', encoding='utf-8').write(html)
    print('demos/' + name)


# 1. 探照灯：把首页那一节整个换掉，文字原样保留
hero = re.compile(r'<section class="hero" data-depth="0">\s*<div class="wrap">\s*(<div class="hero-copy">.*?</div>\s*</div>)\s*<figure class="fig">.*?</figure>\s*</div>\s*</section>', re.S)
assert hero.search(src), 'index.html 的首页结构变了，改一下 build_demos.py 里的正则'
torch = hero.sub(TORCH_HERO, src)
page(torch, 'entry-torch.html', 'Oceanid Robotics — Searchlight demo',
     '<link rel="stylesheet" href="demo.css">\n', '<script src="torch.js"></script>\n',
     BAR.format(t=CUR, d='', extra=''))

# 2. 下潜开场：页面不变，只加开场脚本
dive = src.replace('<body>', '<body class="dive-page">')
page(dive, 'entry-dive.html', 'Oceanid Robotics — Descent demo',
     '<link rel="stylesheet" href="demo.css">\n', '<script src="dive.js"></script>\n',
     BAR.format(t='', d=CUR, extra='\n  <button type="button" onclick="location.reload()">↻ Replay</button>'))
