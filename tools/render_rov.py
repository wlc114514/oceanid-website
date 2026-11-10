"""用 Blender 把 ROV 装配渲染成网站插图。

用法（在命令行里）：
  blender -b -P tools/render_rov.py -- <输出png> [宽] [高] [freestyle:1/0]
  blender -b -P tools/render_rov.py -- <输出文件夹> [宽] [高] [freestyle:1/0] <转盘张数> [只渲染哪几张，如 0,18,36]
    给了转盘张数时，整机绕竖直轴转一圈，每 360/张数 度输出一张 000.png、001.png …（相机和灯光不动）
    最后一个参数用来试取景：只渲染列出的那几张

STL 文件夹默认是 ~/Desktop/矢量八推/STL导出，可以用环境变量 ROV_STL_DIR 改。

做了三件事：
1. 导入 SolidWorks 按零件导出的 STL（坐标是整机装配坐标，直接就是对的位置）
2. 补上缺的部件：后舱 = 舱体3 以舱连接件为中心镜像一份；两个舱顶各补一块 5 mm 舱盖；爪子 + 舵机装在前端舵机打印件的竖板前面
3. 黑底、浅色材质 + 线稿（Freestyle），输出灰度图，之后用 build_images.py 染成网站的深蓝色
所有尺寸按 SolidWorks 的毫米、Y 轴朝上来写，最后整体转成 Blender 的 Z 轴朝上。
"""
import bpy, bmesh, sys, os, glob, math
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else 'rov.png')   # 转成绝对路径，不然 Blender 会把相对路径当成从盘符根目录算
W = int(argv[1]) if len(argv) > 1 else 2400
H = int(argv[2]) if len(argv) > 2 else 1800
FREESTYLE = (argv[3] != '0') if len(argv) > 3 else True
SPIN = int(argv[4]) if len(argv) > 4 else 0
ONLY = {int(k) for k in argv[5].split(',')} if len(argv) > 5 else None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASM_DIR = os.environ.get('ROV_STL_DIR') or os.path.join(os.path.expanduser('~'), 'Desktop', '矢量八推', 'STL导出')
CLAW_DIR = os.path.join(ROOT, 'assets', 'rov-cad', 'source')

# ---- 装配上的关键尺寸（SolidWorks 坐标，mm；+X 朝前，+Y 朝上）----
MIRROR_X = 246.6              # 舱连接件改 的中心面，后舱以此镜像
MOUNT_FACE_X = 423.8          # 舵机打印件 竖板的前表面
MOUNT_CENTER_Y = 37.6         # 竖板中心高度
MOUNT_CENTER_Z = 199.8        # 竖板左右居中（也是整机中线）
# 爪子文件自己的坐标系里：舵机背面在 z=0，爪子朝 +z 伸出；舵机 x 中心 22，y 中心 56.8
CLAW_CX, CLAW_CY = 22.0, 56.8

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def import_stl(path):
    bpy.ops.wm.stl_import(filepath=path, forward_axis='Y', up_axis='Z')  # 保持文件原坐标
    return bpy.context.selected_objects[0]

def transform_mesh(obj, mat, flip=False):
    me = obj.data
    me.transform(mat)
    if flip:  # 镜像后三角形朝向反了，翻回来
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me); bm.free()
    me.update()

parts = []
for p in sorted(glob.glob(os.path.join(ASM_DIR, '*.STL'))):
    o = import_stl(p)
    o.name = os.path.basename(p).split(' - ', 1)[-1][:-4]
    parts.append(o)

# 后舱：复制舱体3，以 x = MIRROR_X 为镜面
hull = next(o for o in parts if o.name.startswith('舱体3'))
rear = hull.copy(); rear.data = hull.data.copy(); rear.name = '舱体3-后舱(补)'
scene.collection.objects.link(rear)
transform_mesh(rear, Matrix.Translation((MIRROR_X, 0, 0)) @ Matrix.Scale(-1, 4, (1, 0, 0)) @ Matrix.Translation((-MIRROR_X, 0, 0)), flip=True)
parts.append(rear)

# 舱盖：舱体3 顶面是敞开的，原设计没有盖子模型，补一块 5 mm 平板（四角 R6）盖住开口，前后舱各一块
LID_T, LID_R = 5.0, 6.0
def make_lid(name, x0, x1, z0, z1, y0):
    pts = []
    for cx, cz, a0 in ((x1 - LID_R, z1 - LID_R, 0), (x0 + LID_R, z1 - LID_R, 90), (x0 + LID_R, z0 + LID_R, 180), (x1 - LID_R, z0 + LID_R, 270)):
        for k in range(7):
            a = math.radians(a0 + 15 * k)
            pts.append((cx + LID_R * math.cos(a), cz + LID_R * math.sin(a)))
    bm = bmesh.new()
    bottom = [bm.verts.new((x, y0, z)) for x, z in pts]
    top = [bm.verts.new((x, y0 + LID_T, z)) for x, z in pts]
    bm.faces.new(bottom[::-1]); bm.faces.new(top)
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((bottom[i], bottom[j], top[j], top[i]))
    bm.normal_update()
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); scene.collection.objects.link(o)
    return o

def top_of(o):
    vs = [v.co for v in o.data.vertices]
    return min(v.x for v in vs), max(v.x for v in vs), min(v.z for v in vs), max(v.z for v in vs), max(v.y for v in vs)

for h, label in ((hull, '前舱盖(补)'), (rear, '后舱盖(补)')):
    x0, x1, z0, z1, ytop = top_of(h)
    parts.append(make_lid(label, x0, x1, z0, z1, ytop))

# 爪子 + 舵机：绕 Y 轴转 90°，让爪子方向 (+z) 变成整机前方 (+X)，再贴到竖板前面
rot = Matrix(((0, 0, 1, 0), (0, 1, 0, 0), (-1, 0, 0, 0), (0, 0, 0, 1)))  # (x,y,z) -> (z, y, -x)
place = (Matrix.Translation((MOUNT_FACE_X, MOUNT_CENTER_Y, MOUNT_CENTER_Z)) @ rot
         @ Matrix.Translation((-CLAW_CX, -CLAW_CY, 0)))
# 两片爪子文件各自导出时齿朝外；左右互换位置（各移 28 mm）让带齿的一面相对
JAW_SWAP = {'快拆机械爪1.0': 0, '爪子3': 28.0, '爪子4': -28.0}
for name, dx in JAW_SWAP.items():
    o = import_stl(os.path.join(CLAW_DIR, name + '.STL'))
    o.name = name + '(补)'
    transform_mesh(o, place @ Matrix.Translation((dx, 0, 0)))
    parts.append(o)

# 整体：毫米 -> 米，Y 朝上 -> Z 朝上
to_blender = Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Scale(0.001, 4)
for o in parts:
    transform_mesh(o, to_blender)
    for poly in o.data.polygons:
        poly.use_smooth = False

# 中心和大小
pts = [v.co for o in parts for v in o.data.vertices]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center, radius = (lo + hi) / 2, (hi - lo).length / 2
print('整机尺寸 (m):', tuple(round(x, 3) for x in (hi - lo)))

# 材质：浅灰哑光，透明件（玻璃）单独处理
mat = bpy.data.materials.new('clay'); mat.use_nodes = True
bsdf = mat.node_tree.nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (0.8, 0.82, 0.85, 1)
bsdf.inputs['Roughness'].default_value = 0.55
glass = bpy.data.materials.new('glass'); glass.use_nodes = True
gb = glass.node_tree.nodes['Principled BSDF']
gb.inputs['Base Color'].default_value = (0.6, 0.7, 0.8, 1)
gb.inputs['Alpha'].default_value = 0.25
for o in parts:
    o.data.materials.clear()
    o.data.materials.append(glass if '玻璃' in o.name and '压板' not in o.name else mat)

# 世界：纯黑
world = bpy.data.worlds.new('w'); scene.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0, 0, 0, 1)

# 相机：右前上方 3/4 视角，长焦减少透视变形
cam_data = bpy.data.cameras.new('cam'); cam_data.lens = 70
cam = bpy.data.objects.new('cam', cam_data); scene.collection.objects.link(cam); scene.camera = cam
direction = Vector((1.0, -0.95, 0.62)).normalized()
cam_data.clip_end = 100
scene.render.resolution_x, scene.render.resolution_y = W, H
from bpy_extras.object_utils import world_to_camera_view
corners = [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
if SPIN:
    corners = [center + Matrix.Rotation(2 * math.pi * k / SPIN, 3, 'Z') @ (c - center) for k in range(SPIN) for c in corners]
dist = radius * 4
for _ in range(30):  # 调整距离，让整机占画面约 86%
    cam.location = center + direction * dist
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    uv = [world_to_camera_view(scene, cam, c) for c in corners]
    extent = max(max(abs(p.x - .5) for p in uv) * 2, max(abs(p.y - .5) for p in uv) * 2)
    dist *= extent / 0.86

# 紧凑取景：上面按包围盒八个角估出来的距离偏保守（整机实际只占画面七成，而且偏下）。
# 相机位置不动（透视不变），改用全部顶点在所有转盘角度下的真实投影范围：调焦距放大到占画面 FILL，调 shift 居中
import numpy as np
FILL = 0.92
def all_verts():
    out = []
    for o in parts:
        a = np.empty(len(o.data.vertices) * 3, 'f'); o.data.vertices.foreach_get('co', a)
        out.append(a.reshape(-1, 3))
    grid = 0.002  # 合并到 2 mm 网格，减少点数
    return np.unique(np.round(np.concatenate(out) / grid).astype(np.int32), axis=0) * grid
V, C = all_verts(), np.array(center)
inv = np.array(cam.matrix_world.inverted())
lo_a = lo_b = 1e9; hi_a = hi_b = -1e9
for k in range(SPIN or 1):
    rz = np.array(Matrix.Rotation(2 * math.pi * k / (SPIN or 1), 3, 'Z'))
    pc = ((V - C) @ rz.T + C) @ inv[:3, :3].T + inv[:3, 3]
    a, b = pc[:, 0] / -pc[:, 2], pc[:, 1] / -pc[:, 2]   # 相机坐标系里的正切值：a 向右，b 向上
    lo_a, hi_a, lo_b, hi_b = min(lo_a, a.min()), max(hi_a, a.max()), min(lo_b, b.min()), max(hi_b, b.max())
zoom = FILL / max(hi_a - lo_a, (hi_b - lo_b) * W / H)   # 焦距 ÷ 传感器宽度
cam_data.sensor_fit = 'HORIZONTAL'
cam_data.lens = zoom * cam_data.sensor_width
cam_data.shift_x, cam_data.shift_y = zoom * (lo_a + hi_a) / 2, zoom * (lo_b + hi_b) / 2
bpy.context.view_layer.update()
print(f'取景：{len(V)} 个点，焦距 {cam_data.lens:.1f} mm，shift ({cam_data.shift_x:.4f}, {cam_data.shift_y:.4f})，'
      f'整机占画面 宽 {zoom * (hi_a - lo_a):.0%} 高 {zoom * (hi_b - lo_b) * W / H:.0%}', flush=True)

# 灯光：主光 + 轮廓光
def light(name, loc, energy, size):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = energy; ld.size = size
    lo_ = bpy.data.objects.new(name, ld); scene.collection.objects.link(lo_)
    lo_.location = center + Vector(loc)
    lo_.rotation_euler = (center - lo_.location).to_track_quat('-Z', 'Y').to_euler()
light('key', (0.6, -1.2, 1.4), 30, 1.2)
light('rim', (-1.4, 0.8, 0.6), 22, 0.8)
light('fill', (1.2, 0.6, -0.3), 6, 1.5)

# 渲染设置
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 48
scene.render.threads_mode = 'FIXED'
scene.render.threads = max(1, (os.cpu_count() or 8) // 2)   # 只用一半线程（约等于物理核心数），别把机器跑满
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.film_transparent = False
scene.view_settings.view_transform = 'Standard'
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'BW'
scene.render.image_settings.color_depth = '16'
scene.render.filepath = OUT

if FREESTYLE:
    scene.render.use_freestyle = True
    scene.render.line_thickness_mode = 'ABSOLUTE'
    scene.render.line_thickness = 1.4 * W / 2400
    vl = scene.view_layers[0]
    ls = vl.freestyle_settings.linesets[0] if vl.freestyle_settings.linesets else vl.freestyle_settings.linesets.new('lines')
    ls.select_by_visibility = True
    ls.select_silhouette = ls.select_border = ls.select_crease = True
    vl.freestyle_settings.crease_angle = math.radians(140)
    if ls.linestyle is None:
        ls.linestyle = bpy.data.linestyles.new('line')
    ls.linestyle.color = (1, 1, 1)

if not SPIN:
    bpy.ops.render.render(write_still=True)
    print('已输出', OUT)
else:
    # 所有零件挂到中心的空物体上，转空物体
    pivot = bpy.data.objects.new('pivot', None); scene.collection.objects.link(pivot)
    pivot.location = center
    for o in parts:
        o.parent = pivot
        o.matrix_parent_inverse = Matrix.Translation(center).inverted()  # 网格本身就是世界坐标，抵消掉空物体的位置
    os.makedirs(OUT, exist_ok=True)
    for k in range(SPIN):
        if ONLY is not None and k not in ONLY: continue
        pivot.rotation_euler = (0, 0, 2 * math.pi * k / SPIN)  # 逆时针（俯视），近处那面往画面右边走
        scene.render.filepath = os.path.join(OUT, f'{k:03d}.png')
        bpy.ops.render.render(write_still=True)
        print(f'转盘 {k + 1}/{SPIN}', flush=True)
