// 深度计：页面各区块用 data-depth 标出对应深度，滚动时在相邻区块之间按比例插值
(() => {
  const MAX = 11000; // 刻度底端，略深于挑战者深渊
  const ZONES = [[200, 'Epipelagic'], [1000, 'Mesopelagic'], [4000, 'Bathypelagic'], [6000, 'Abyssopelagic'], [Infinity, 'Hadalpelagic']];
  const zoneOf = d => ZONES.find(([limit]) => d < limit)[1];
  const fmt = new Intl.NumberFormat('en-US');

  const stops = [...document.querySelectorAll('[data-depth]')];
  const depthOuts = document.querySelectorAll('[data-depth-out]');
  const zoneOut = document.querySelector('[data-zone-out]');
  const mark = document.querySelector('.gauge-mark');
  const read = document.querySelector('.gauge-read');

  let points = [];
  function measure() {
    points = stops
      .map(el => ({ y: el.getBoundingClientRect().top + scrollY, d: +el.dataset.depth }))
      .sort((a, b) => a.y - b.y);
  }

  function update() {
    const doc = document.documentElement;
    let depth;
    if (scrollY + innerHeight >= doc.scrollHeight - 4) {
      depth = points[points.length - 1].d; // 滚到底就是最深处
    } else {
      // 读数取屏幕上方 40% 处的位置；页面顶部那一段逐渐过渡过去，保证没滚动时正好是第一个区块的深度（200 m，接着开场动画）
      const y = scrollY + Math.min(scrollY, innerHeight * 0.4);
      depth = points[0].d;
      for (let k = 0; k < points.length; k++) {
        const a = points[k], b = points[k + 1];
        if (y < a.y) break;
        depth = b ? a.d + (b.d - a.d) * Math.min(1, (y - a.y) / (b.y - a.y)) : a.d;
      }
    }
    depth = Math.round(depth);
    depthOuts.forEach(el => { el.textContent = fmt.format(depth); });
    if (zoneOut) zoneOut.textContent = depth >= 10900 ? 'Challenger Deep' : zoneOf(depth);
    const pct = (depth / MAX) * 100 + '%';
    if (mark) mark.style.top = pct;
    if (read) read.style.top = pct;
  }

  let ticking = false;
  const onScroll = () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => { ticking = false; update(); });
  };
  addEventListener('scroll', onScroll, { passive: true });
  addEventListener('resize', () => { measure(); update(); });
  addEventListener('load', () => { measure(); update(); });
  measure();
  update();
})();

// 复制邮箱：图标按钮，复制成功后图标变成对勾，旁边的状态文字（读屏软件也会读出来）显示 Copied
document.querySelectorAll('[data-copy]').forEach(btn => {
  const status = btn.parentElement.querySelector('[data-copy-status]');
  btn.addEventListener('click', async () => {
    const target = document.getElementById(btn.dataset.copy);
    const text = target.textContent.trim();
    try {
      await navigator.clipboard.writeText(text);
      btn.classList.add('done');
      if (status) status.textContent = 'Copied';
    } catch {
      // 剪贴板不可用时，选中文字让用户自己复制
      const range = document.createRange();
      range.selectNodeContents(target);
      const sel = getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      if (status) status.textContent = 'Press Ctrl+C';
    }
    setTimeout(() => { btn.classList.remove('done'); if (status) status.textContent = ''; }, 1800);
  });
});

// 手机菜单：点按钮展开/收起导航；点了链接、按 Esc、点别处都会收起
(() => {
  const top = document.querySelector('.top'), btn = document.querySelector('.menu-btn');
  if (!top || !btn) return;
  const set = open => { top.classList.toggle('open', open); btn.setAttribute('aria-expanded', open); };
  btn.addEventListener('click', () => set(!top.classList.contains('open')));
  top.querySelectorAll('.nav a').forEach(a => a.addEventListener('click', () => set(false)));
  addEventListener('keydown', e => { if (e.key === 'Escape') set(false); });
  addEventListener('click', e => { if (!top.contains(e.target)) set(false); });
})();

// 图上的 i：触屏没有悬停，点一下显示/收起说明；按 Esc 或点别处收起
document.querySelectorAll('.info').forEach(btn => {
  const set = open => btn.setAttribute('aria-expanded', open);
  btn.addEventListener('click', () => set(btn.getAttribute('aria-expanded') !== 'true'));
  addEventListener('keydown', e => { if (e.key === 'Escape') set(false); });
  addEventListener('click', e => { if (e.target !== btn) set(false); });
});
