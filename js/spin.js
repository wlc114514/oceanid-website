// ROV 转盘预览：预先渲染好一圈的图片，左右拖动时按拖动距离切换图片
// 用法：<div class="spin" data-frames="72" data-pattern="img/rov-spin/{n}.webp"><img src="…/000.webp"><span class="spin-hint"></span></div>
(() => {
  document.querySelectorAll('.spin').forEach(box => {
    const N = +box.dataset.frames;
    const src = n => box.dataset.pattern.replace('{n}', String(n).padStart(3, '0'));
    const img = box.querySelector('img');
    const hint = box.querySelector('.spin-hint');
    const frames = new Array(N);
    let loaded = 0, current = 0;

    // 滚动到附近时才在后台加载其余图片，不拖慢首页
    function preload() {
      for (let i = 0; i < N; i++) {
        const im = new Image();
        im.src = src(i);
        im.decode().then(() => {
          frames[i] = im; // 只记下加载成功的角度，失败的拖到时会跳过
          loaded++;
          if (hint && !box.classList.contains('touched')) {
            hint.textContent = loaded < N ? `${loaded}/${N}` : '⟷';
          }
        }, () => {});
      }
    }
    const io = new IntersectionObserver(entries => {
      if (entries.some(e => e.isIntersecting)) { io.disconnect(); preload(); }
    }, { rootMargin: '600px 0px' });
    io.observe(box);

    function show(i) {
      i = ((i % N) + N) % N;
      if (i === current) return;
      // 还没加载好的角度先跳过，等加载完再显示
      if (!frames[i]) return;
      current = i;
      img.src = frames[i].src;
    }

    // 拖过整张图的宽度 = 转一整圈
    let startX = 0, startFrame = 0, dragging = false;
    box.addEventListener('pointerdown', e => {
      dragging = true;
      startX = e.clientX;
      startFrame = current;
      box.setPointerCapture(e.pointerId);
      box.classList.add('dragging', 'touched');
    });
    box.addEventListener('pointermove', e => {
      if (!dragging) return;
      const perFrame = box.clientWidth / N;
      show(startFrame + Math.round((e.clientX - startX) / perFrame));
    });
    const end = () => { dragging = false; box.classList.remove('dragging'); };
    box.addEventListener('pointerup', end);
    box.addEventListener('pointercancel', end);

    // 键盘：左右方向键每次转 10°
    box.addEventListener('keydown', e => {
      const step = Math.max(1, Math.round(N / 36));
      if (e.key === 'ArrowRight') show(current + step);
      else if (e.key === 'ArrowLeft') show(current - step);
      else return;
      e.preventDefault();
      box.classList.add('touched');
    });
  });
})();
