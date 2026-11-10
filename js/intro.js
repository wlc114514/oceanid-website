// 下潜开场：海水从浅蓝变暗，深度计 0 → 200 m，Triton 从粗颗粒一级级变细，最后水面升上来、雾退掉，露出首页。
// 素材全是提前渲染好的：颗粒 Triton 由 tools/build_entry.py 生成，水面线和雾由 tools/build_water.py 生成；这里只按时间换图、移动位置。
// 播不播由 index.html <head> 里的小脚本决定（第一次访问才播，加 ?intro 强制重播），它会先给 <html> 加上 .diving。
(() => {
  const DEPTH = 200, DIVE_MS = 2800;
  const LEVELS = [44, 88, 175, 350, 700, 1400];

  const root = document.documentElement;
  const heroImg = document.querySelector('.hero-img');
  if (!root.classList.contains('diving')) return;
  if (!heroImg || scrollY > 0) { root.classList.remove('diving'); return; }
  try { localStorage.setItem('oceanid-dived', '1'); } catch {}
  const el = document.createElement('div');
  const asset = f => new URL('entry/' + f, heroImg.src);
  const V = '?v=4';   // 出水素材重新渲染后把数字加 1，免得浏览器用缓存里的旧图
  el.className = 'dive';
  el.innerHTML = `
    <img class="dive-film" src="${asset('film.avif') + V}" alt="" aria-hidden="true">
    <div class="dive-water" aria-hidden="true"><div class="dive-sea"></div><img class="dive-crest" src="${asset('crest/00.avif')}" alt=""></div>
    <div class="dive-read wrap" aria-hidden="true">
      <span class="num"><span data-n>0</span><small>m</small></span>
    </div>
    <div class="dive-stack" aria-hidden="true">${LEVELS.map(w =>
      `<img src="${asset(`triton-d${String(w).padStart(4, '0')}.png`)}" alt="" class="${w < 700 ? 'pix' : ''}">`).join('')}</div>
    <button class="dive-skip" type="button">Skip intro →</button>`;
  document.body.append(el);
  const num = el.querySelector('[data-n]');
  const stack = el.querySelector('.dive-stack'), imgs = [...el.querySelectorAll('img')];
  const levels = [...stack.children];
  const film = el.querySelector('.dive-film');

  const crest = el.querySelector('.dive-crest');

  // 出水的两段序列帧（AVIF），下潜那 3 秒里在后台加载：
  // 水面线 36 帧循环（24 帧/秒）；雾退掉 48 帧（14 帧/秒，约 3.4 秒）。没加载完就退回静态图（水面线不动、雾整张往下滑）
  function frames(dir, n, fps) {
    const list = Array(n);
    list.ready = 0;
    list.fps = fps;
    for (let i = 0; i < n; i++) {
      const im = new Image();
      im.src = asset(`${dir}/${String(i).padStart(2, '0')}.avif`) + V;
      im.decode().then(() => { list[i] = im; list.ready++; }, () => {});
    }
    return list;
  }
  const crestFrames = frames('crest', 36, 24), haze = frames('haze', 48, 14);
  const loaded = list => list.ready === list.length;
  // 按帧率换帧；loop = 循环播放直到元素被移除，否则播完调用 done
  function play(img, list, loop, done) {
    const t = performance.now();
    (function step(now) {
      if (!el.isConnected) return;
      let i = Math.floor((now - t) / 1000 * list.fps);
      if (i >= list.length) { if (!loop) return done(); i %= list.length; }
      if (img.src !== list[i].src) img.src = list[i].src;
      requestAnimationFrame(step);
    })(t);
  }

  // 桌面：颗粒图正好盖在首页大图的位置，最后淡出时像是「变清楚了」；手机：摆在读数下面
  function place() {
    const r = heroImg.getBoundingClientRect();
    const narrow = innerWidth <= 860;
    let x = r.left, y = r.top, w = r.width, h = r.height;
    if (narrow || r.bottom > innerHeight) {
      h = Math.min(innerHeight * .5, (innerWidth - 32) * 1589 / 1400);
      w = h * 1400 / 1589; x = (innerWidth - w) / 2; y = innerHeight - h - 70;
    }
    Object.assign(stack.style, { left: x + 'px', top: y + 'px', width: w + 'px', height: h + 'px' });
  }
  place();
  addEventListener('resize', place);

  let t0 = 0, raf = 0, timers = [], ended = false;
  function tick(t) {
    const p = Math.min(1, (t - t0) / DIVE_MS);
    const d = Math.round(DEPTH * (p * p * (3 - 2 * p)));
    num.textContent = d;
    if (p < 1) raf = requestAnimationFrame(tick);
  }
  function show(i) { levels.forEach((im, j) => im.classList.toggle('on', j === i)); }

  function start() {
    if (ended) return;
    el.classList.add('go');
    t0 = performance.now();
    raf = requestAnimationFrame(tick);
    // 颗粒六级，前几级换得快，细的停留久一点
    [150, 520, 900, 1300, 1750, 2250].forEach((ms, i) => timers.push(setTimeout(() => show(i), ms)));
    timers.push(setTimeout(finish, DIVE_MS + 350));
  }

  // 结尾「出水」：读数和 Triton 淡出 → 水面从底下升上来 → 水膜往下流走。用户跳过时（带事件参数）后半段快一点
  function finish(e) {
    if (ended) return;
    ended = true;
    const fast = !!e;
    timers.forEach(clearTimeout);
    cancelAnimationFrame(raf);
    if (!fast) num.textContent = DEPTH;
    removeEventListener('resize', place);
    ['keydown', 'wheel', 'touchstart'].forEach(ev => removeEventListener(ev, finish));
    el.classList.add('surfacing');
    setTimeout(() => {
      const anim = loaded(haze), lag = fast ? 700 : 1500;   // 水面线快到顶时，雾开始退
      if (anim) film.src = haze[0].src;            // 雾的第 0 帧 = 刚出水的样子
      if (loaded(crestFrames)) play(crest, crestFrames, true);
      el.style.setProperty('--rise', fast ? '1.2s' : '2.2s');
      el.classList.add('rise');
      root.classList.remove('diving');
      root.classList.add('arrived');
      setTimeout(() => {
        el.classList.add('drain');
        if (anim) play(film, haze, false, () => el.remove()); else { el.classList.add('static'); setTimeout(() => el.remove(), 2100); }
      }, lag);
    }, 300);
  }

  el.querySelector('.dive-skip').addEventListener('click', finish);
  ['keydown', 'wheel', 'touchstart'].forEach(ev => addEventListener(ev, finish, { passive: true }));

  // 等颗粒图都解码好再开始（最多等 1.2 秒），免得开场时图还是空的
  Promise.race([
    Promise.all(imgs.map(im => im.decode().catch(() => {}))),
    new Promise(r => setTimeout(r, 1200)),
  ]).then(() => requestAnimationFrame(start));
})();
