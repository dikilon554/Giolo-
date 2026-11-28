"""3D-объекты для обложек в стиле Forge Media: чёрный глянец + оранжевые акценты, прозрачный фон.

Запуск (Blender как модуль Python, отдельное окружение):
  uv venv -p 3.13 /home/user/bpy-venv && uv pip install -p /home/user/bpy-venv/bin/python bpy==5.2.5
  /home/user/bpy-venv/bin/python scripts/render3d.py snowflake question play hourglass

Результат: assets/cover/objects/<имя>.png (800×800, прозрачный фон), дальше — scripts/cover.py --obj <имя>:...
Новый объект = новая функция build_<имя>() ниже.
"""
import math
import sys
from pathlib import Path

import bpy  # noqa: E402  (bpy первым: он подключает bmesh и mathutils)
import bmesh
from mathutils import Euler, Vector

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets/cover/objects'
ORANGE = (1.0, 0.33, 0.02, 1)


# ---------- сцена ----------
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = 800
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    w = bpy.data.worlds.new('w'); sc.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.004, 0.003, 0.003, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
    return sc


def light(name, loc, energy, color, size):
    d = bpy.data.lights.new(name, 'AREA'); d.energy = energy; d.color = color; d.size = size
    o = bpy.data.objects.new(name, d); bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


def studio():
    light('key', (-3, -5, 4), 900, (1, 0.97, 0.94), 1.2)        # мягкий белый сверху-слева
    light('rimR', (4, 3, 1.5), 1500, (1, 0.45, 0.08), 1.5)    # оранжевый контур справа-сзади
    light('rimL', (-4, 2.5, 0.5), 800, (1, 0.5, 0.12), 1.2)   # оранжевый контур слева-сзади
    light('fill', (2, -5, -1), 60, (1, 0.9, 0.85), 4)        # чуть подсветить низ


def mat_black():
    m = bpy.data.materials.new('black'); m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (0.012, 0.012, 0.013, 1)
    p.inputs['Metallic'].default_value = 0.0
    p.inputs['Roughness'].default_value = 0.18
    p.inputs['Coat Weight'].default_value = 1.0
    p.inputs['Coat Roughness'].default_value = 0.05
    return m


def mat_orange(glow=0.35):
    m = bpy.data.materials.new('orange'); m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = ORANGE
    p.inputs['Metallic'].default_value = 0.3
    p.inputs['Roughness'].default_value = 0.3
    p.inputs['Emission Color'].default_value = ORANGE
    p.inputs['Emission Strength'].default_value = glow
    return m


def mat_color(rgb, rough=0.2, metal=0.0, coat=0.6, glow=0.0, name='c'):
    """Материал в естественном цвете предмета (снег — голубой, YouTube — красный, дерево — коричневое…)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*rgb, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['Coat Weight'].default_value = coat
    p.inputs['Coat Roughness'].default_value = 0.05
    if glow:
        p.inputs['Emission Color'].default_value = (*rgb, 1)
        p.inputs['Emission Strength'].default_value = glow
    return m


ICE = (0.05, 0.32, 1.0)
ICE_LIGHT = (0.45, 0.78, 1.0)
YT_RED = (0.75, 0.01, 0.01)
WHITE = (0.92, 0.92, 0.92)
WOOD = (0.07, 0.025, 0.007)
SAND = (0.9, 0.42, 0.08)


def mat_glass():
    m = bpy.data.materials.new('glass'); m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (0.9, 0.9, 0.95, 1)
    p.inputs['Roughness'].default_value = 0.02
    p.inputs['Transmission Weight'].default_value = 1.0
    p.inputs['IOR'].default_value = 1.45
    return m


def frame_and_render(objs, name, rot=(math.radians(12), math.radians(-22), 0), lens=85):
    root = bpy.data.objects.new('root', None); bpy.context.scene.collection.objects.link(root)
    for o in objs:
        o.parent = root
    root.rotation_euler = Euler(rot)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type in ('MESH', 'FONT', 'CURVE') for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center, size = (lo + hi) / 2, max((hi - lo).x, (hi - lo).z)
    root.location -= center
    cam_d = bpy.data.cameras.new('cam'); cam_d.lens = lens
    cam = bpy.data.objects.new('cam', cam_d); bpy.context.scene.collection.objects.link(cam)
    dist = size * 1.3 * lens / 36
    cam.location = (0, -dist, 0); cam.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = cam
    studio()
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(OUT / f'{name}.png')
    bpy.ops.render.render(write_still=True)
    print('Готово:', OUT / f'{name}.png')


def bevel(o, width, seg=4):
    m = o.modifiers.new('bevel', 'BEVEL'); m.width = width; m.segments = seg; m.limit_method = 'ANGLE'
    return m


# ---------- объекты ----------
def build_snowflake():
    """Снежинка: чёрный глянец, сглаженные грани, оранжевый центр."""
    bm = bmesh.new()

    def bar(length, width, angle, offset=(0, 0)):
        r = bmesh.ops.create_cube(bm, size=1.0)
        vs = r['verts']
        bmesh.ops.scale(bm, vec=(length, width, 0.16), verts=vs)
        bmesh.ops.translate(bm, vec=(length / 2, 0, 0), verts=vs)
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Euler((0, 0, angle)).to_matrix(), verts=vs)
        bmesh.ops.translate(bm, vec=(offset[0], offset[1], 0), verts=vs)

    for k in range(6):
        a = k * math.pi / 3
        bar(1.0, 0.13, a)
        for t, L in ((0.45, 0.36), (0.72, 0.24)):
            px, py = t * math.cos(a), t * math.sin(a)
            bar(L, 0.1, a + math.radians(45), (px, py))
            bar(L, 0.1, a - math.radians(45), (px, py))
    me = bpy.data.meshes.new('snow'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('snow', me); bpy.context.scene.collection.objects.link(o)
    bevel(o, 0.035, 4)
    o.data.materials.append(mat_color(ICE, rough=0.12, coat=1.0, glow=0.12, name='ice'))
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.16, depth=0.2, location=(0, 0, 0.02))
    hub = bpy.context.active_object; bevel(hub, 0.03, 3); hub.data.materials.append(mat_color(ICE_LIGHT, rough=0.1, coat=1.0, glow=0.15, name='ice2'))
    for x in (o, hub):  # поставить лицом к камере (плоскость XZ)
        x.rotation_euler = (math.radians(90), 0, 0)
    return [o, hub], dict(rot=(math.radians(-14), 0, math.radians(-24)))


def build_question():
    """Знак вопроса: чёрный глянец, оранжевая точка (отдельный объект)."""
    bpy.ops.object.text_add(); t = bpy.context.active_object
    t.data.font = bpy.data.fonts.load(str(ROOT / 'assets/fonts/InterDisplay-Black.otf'))
    t.data.body = '?'; t.data.extrude = 0.1; t.data.bevel_depth = 0.022; t.data.bevel_resolution = 4
    t.data.align_x = 'CENTER'; t.data.align_y = 'CENTER'
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.separate(type='LOOSE'); bpy.ops.object.mode_set(mode='OBJECT')
    parts = sorted(bpy.context.selected_objects, key=lambda o: len(o.data.vertices))
    for i, o in enumerate(parts):
        o.data.materials.clear()
        o.data.materials.append(mat_orange() if i == 0 else mat_black())  # меньший островок — точка
        o.rotation_euler = (math.radians(90), 0, 0)
        bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_smooth()
    return parts, dict(rot=(math.radians(10), 0, math.radians(-38)))


def build_play():
    """Кнопка Play в стиле бренда: чёрная скруглённая плитка, оранжевый треугольник."""
    bpy.ops.mesh.primitive_cube_add(size=1); b = bpy.context.active_object
    b.scale = (1.5, 0.38, 1.05); bpy.ops.object.transform_apply(scale=True)
    bevel(b, 0.17, 10); b.data.materials.append(mat_color(YT_RED, rough=0.18, coat=1.0, name='red')); bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_cylinder_add(vertices=3, radius=0.34, depth=0.14, location=(0.05, -0.2, 0),
                                        rotation=(math.radians(90), math.radians(90), 0))
    tri = bpy.context.active_object; bevel(tri, 0.05, 6); tri.data.materials.append(mat_color(WHITE, rough=0.25, coat=0.5, name='white'))
    bpy.ops.object.shade_smooth()
    return [b, tri], dict(rot=(math.radians(10), 0, math.radians(-24)))


def build_hourglass():
    """Песочные часы: чёрные крышки и стойки, стекло, оранжевый «песок»."""
    objs = []
    for z in (1.0, -1.0):
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.62, depth=0.14, location=(0, 0, z))
        c = bpy.context.active_object; bevel(c, 0.04, 4); c.data.materials.append(mat_color(WOOD, rough=0.35, coat=0.8, name='wood')); objs.append(c)
    for k in range(3):
        a = k * 2 * math.pi / 3 + 0.4
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.04, depth=2.0, location=(0.5 * math.cos(a), 0.5 * math.sin(a), 0))
        s = bpy.context.active_object; s.data.materials.append(mat_color(WOOD, rough=0.35, coat=0.8, name='wood2')); objs.append(s)
    bm = bmesh.new()  # стекло — тело вращения
    prof = [(0.03, 0), (0.18, 0.12), (0.42, 0.45), (0.47, 0.75), (0.4, 0.93)]
    vs = [bm.verts.new((r, 0, -z)) for r, z in reversed(prof)] + [bm.verts.new((r, 0, z)) for r, z in prof[1:]]
    for a, b2 in zip(vs, vs[1:]):
        bm.edges.new((a, b2))
    bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], angle=2 * math.pi, steps=64, axis=(0, 0, 1), cent=(0, 0, 0))
    me = bpy.data.meshes.new('glass'); bm.to_mesh(me); bm.free()
    g = bpy.data.objects.new('glass', me); bpy.context.scene.collection.objects.link(g)
    g.data.materials.append(mat_glass()); objs.append(g)
    bpy.context.view_layer.objects.active = g; g.select_set(True); bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=0.4, radius2=0.03, depth=0.42, location=(0, 0, -0.68))
    sand = bpy.context.active_object; sand.data.materials.append(mat_color(SAND, rough=0.8, coat=0, name='sand')); objs.append(sand)
    bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=0.03, radius2=0.3, depth=0.3, location=(0, 0, 0.32))
    top = bpy.context.active_object; top.data.materials.append(mat_color(SAND, rough=0.8, coat=0, name='sand2')); objs.append(top)
    return objs, dict(rot=(math.radians(6), 0, math.radians(15)), lens=70)


if __name__ == '__main__':
    for name in sys.argv[1:]:
        reset()
        objs, opts = globals()[f'build_{name}']()
        frame_and_render(objs, name, **opts)
