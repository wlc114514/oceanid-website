# Oceanid Robotics 官网

Oceanid Robotics（MATE ROV 比赛公司）的网站。纯 HTML/CSS/JS，没有构建步骤。

队员想交照片或改文字，看 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 本地预览

在项目根目录运行：

```
python -m http.server 8765 --bind 127.0.0.1
```

然后浏览器打开 http://localhost:8765 。

## 目录

| 路径 | 内容 |
|---|---|
| `index.html` | 页面。占位内容都包在 `<span class="ph">` 里，页面上显示成琥珀色虚线，上线前搜 `class="ph"` 全部替换 |
| `css/style.css` | 样式；文件开头的 `:root` 是配色和字体。改完把 `index.html` 里 `style.css?v=` 的数字加 1，不然浏览器可能用缓存里的旧样式 |
| `js/main.js` | 侧边深度计（页面从 200 m 开始，接着开场动画的 0–200 m）、手机菜单、复制邮箱按钮、图上的 i 提示 |
| `js/spin.js` | ROV 转盘：左右拖动切换预先渲染好的图 |
| `js/intro.js` | 下潜开场（第一次访问才播，网址加 `?intro` 可重看）。素材在 `img/entry/`：颗粒 Triton 由 `tools/build_entry.py` 生成，出水的水面线和雾（AVIF 序列帧）由 `tools/build_water.py` 生成；重新渲染后把 `intro.js` 开头的 `V` 加 1 |
| `img/` | 网页用图，全部由 `tools/` 里的脚本离线生成，浏览器里不做任何颗粒计算 |
| `img/dither/` | 抖动颗粒版画（两色 PNG），由 `tools/build_images.py` 生成 |
| `img/rov-spin/` | ROV 转盘的 72 张图（AVIF） |
| `fonts/` | 本地托管的开源字体：Big Shoulders Display、IBM Plex Sans、IBM Plex Mono（均为 SIL OFL 许可） |
| `photos/` | 队员交上来的真实照片原图，见 [CONTRIBUTING.md](CONTRIBUTING.md) |
| `assets/originals/` | 版画高清原图 + `credits.json`（出处） |
| `assets/myth-candidates/` | 备用的神话版画缩略图（48 张，CC0），`contact-sheet.png` 是总览 |
| `tools/` | 下载原图、处理图片、渲染 ROV 的脚本 |

版画全部来自 Rijksmuseum（经 Wikimedia Commons，CC0）。

没有放进仓库、只在维护者电脑上的东西：ROV 的 STL 设计文件和原始渲染（`assets/rov-cad/`）、首页选图时的对比稿、入口方案的样品页（`demos/`）。

## 许可

- 网站代码和脚本（HTML、CSS、JS、Python）：MIT，见 [LICENSE](LICENSE)
- `photos/` 里的照片**不在 MIT 范围内**：版权归拍摄者和 Oceanid Robotics 所有，未经同意请勿转载或使用
- 版画：Rijksmuseum 藏品，CC0（公有领域），出处见 `assets/originals/credits.json`
- 字体：SIL Open Font License 1.1，许可证全文在 `fonts/OFL-BigShouldersDisplay.txt` 和 `fonts/OFL-IBMPlex.txt`

## 抖动颗粒图是怎么显示的

一个颗粒 = 1 个 CSS 像素，所以这些图在页面上按固定尺寸显示、不跟着版面缩放（缩放会让颗粒糊掉或者粗细不匀）；容器比图小就居中裁掉两边。

每张图出四份：不带后缀的用于 100% / 200% / 300% 缩放的屏幕，`-d125`、`-d150`、`-d175` 用于 Windows 常见的 125% / 150% / 175% 缩放。页面用 `<picture>` 按屏幕缩放比例选图。

## 换图 / 加图

1. 下载高清原图：`python tools/fetch_hires.py assets/originals "File:<Commons 上的文件名>.jpg"`
2. 在 `tools/build_images.py` 开头的 `CLEAN`（干净版画）或 `DITHER`（抖动颗粒）里加一行。`DITHER` 要写清楚取景框和页面上的显示尺寸
3. `python tools/build_images.py`
4. 在页面里引用：干净版画是 `img/<名字>.webp`；抖动图照着 `index.html` 里现有的 `<picture>` 写，CSS 里把 `img` 的宽高设成同一个显示尺寸

## ROV 转盘渲染

需要 Blender 和 STL 设计文件（不在仓库里）。STL 文件夹默认是 `~/Desktop/矢量八推/STL导出`，可以用环境变量 `ROV_STL_DIR` 改；爪子和舵机的 STL 放在 `assets/rov-cad/source/`。后舱和爪子的补装方式写在 `tools/render_rov.py` 开头。

```
blender -b -P tools/render_rov.py -- assets/rov-cad/renders/spin 1800 1300 1 72
python tools/build_images.py
```

第一条渲染 72 张（每 5° 一张；脚本只用一半 CPU 线程，约一小时），第二条染色输出到 `img/rov-spin/`（AVIF 格式）。
取景是自动算的：按整机在所有角度下的真实轮廓放大到占画面 92% 并居中。想先看取景，在第一条命令最后加上要渲染的张数编号，比如 `0,18,36`，就只渲染这几张。

重新渲染后把 `index.html` 里 `rov-spin` 地址后面的 `?v=` 版本号加 1，不然浏览器可能还显示缓存里的旧图。
