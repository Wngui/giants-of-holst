"""Blender: model the game's props from code, texture them with art/tex, bake each to one OBJ + image in props/.
  blender -b --python forge.py -- [name ...]      (no names = all; existing outputs are rebuilt)
Units are grid squares (1 = 5 ft), Z up in Blender (exported Y up). Origin = centre of the footprint, on the ground."""
import math, random, sys
from pathlib import Path
import bmesh, bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from bake import bake_objects          # noqa: E402
from textures import TEXTURES          # noqa: E402

OUT, TEX = ROOT / "props", ROOT / "art" / "tex"
H = 1.3          # storey height in squares


# ---------------------------------------------------------------- mesh helpers
class Asset:
    def __init__(self, seed=1):
        self.objs, self.rnd = [], random.Random(seed)

    def add(self, bm, mat, decal=False):
        me = bpy.data.meshes.new(mat)
        uv = bm.loops.layers.uv.new("tex")
        tile = TEXTURES[mat][0] or 1
        for f in bm.faces:   # box projection in world units; decals stretch 0..1 across each face
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            a, b = [(1, 2), (0, 2), (0, 1)][ax]
            co = [(l.vert.co[a], l.vert.co[b]) for l in f.loops]
            if decal or TEXTURES[mat][0] is None:
                lo = [min(c[i] for c in co) for i in (0, 1)]
                hi = [max(c[i] for c in co) for i in (0, 1)]
                for l, c in zip(f.loops, co):
                    u = (c[0] - lo[0]) / ((hi[0] - lo[0]) or 1)
                    l[uv].uv = (1 - u if (n[ax] < 0) != (ax == 1) else u, (c[1] - lo[1]) / ((hi[1] - lo[1]) or 1))
            else:
                for l, c in zip(f.loops, co):
                    l[uv].uv = (c[0] / tile, c[1] / tile)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(mat, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.data.materials.append(material(mat))
        for p in ob.data.polygons:
            p.use_smooth = False
        self.objs.append(ob)
        return ob

    # primitives: each makes one part with one material
    def box(self, size, loc, mat, rot=(0, 0, 0), decal=False):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1)
        bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
        place(bm, loc, rot)
        return self.add(bm, mat, decal)

    def cyl(self, r, h, loc, mat, segs=10, r2=None, rot=(0, 0, 0), caps=True):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=caps, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=h)
        bmesh.ops.translate(bm, vec=Vector((0, 0, h / 2)), verts=bm.verts)
        place(bm, loc, rot)
        return self.add(bm, mat)

    def lathe(self, profile, loc, mat, segs=12, rot=(0, 0, 0), cap_top=True, cap_bottom=True):
        """profile = [(radius, z), ...] bottom to top."""
        bm = bmesh.new()
        rings = [[bm.verts.new((r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs), z))
                  for i in range(segs)] for r, z in profile]
        for a, b in zip(rings, rings[1:]):
            for i in range(segs):
                j = (i + 1) % segs
                bm.faces.new((a[i], a[j], b[j], b[i]))
        if cap_bottom:
            bm.faces.new(list(reversed(rings[0])))
        if cap_top:
            bm.faces.new(rings[-1])
        bm.normal_update()
        place(bm, loc, rot)
        return self.add(bm, mat)

    def blob(self, r, loc, mat, scale=(1, 1, 1), jitter=0.15, subdiv=2, flat_bottom=None):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=r)
        for v in bm.verts:
            v.co *= 1 + self.rnd.uniform(-jitter, jitter)
            v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
            if flat_bottom is not None and v.co.z < flat_bottom:
                v.co.z = flat_bottom
        bm.normal_update()
        place(bm, loc, (self.rnd.uniform(0, 0.3), 0, self.rnd.uniform(0, 6.3)))
        return self.add(bm, mat)

    def prism(self, w, d, h, loc, mat, rot=(0, 0, 0)):
        """Triangular gable end: base w along x, apex h up, depth d along y."""
        bm = bmesh.new()
        f = [bm.verts.new(v) for v in ((-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (0, -d / 2, h))]
        b = [bm.verts.new(v) for v in ((-w / 2, d / 2, 0), (w / 2, d / 2, 0), (0, d / 2, h))]
        bm.faces.new(f)
        bm.faces.new(list(reversed(b)))
        for i in range(3):
            j = (i + 1) % 3
            bm.faces.new((f[j], f[i], b[i], b[j]))
        bm.normal_update()
        place(bm, loc, rot)
        return self.add(bm, mat)


def place(bm, loc, rot):
    m = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") \
        @ Matrix.Rotation(rot[0], 4, "X")
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)


_mats = {}


def material(name):
    if name not in _mats:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        t = m.node_tree.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(str(TEX / f"{name}.png"), check_existing=True)
        m.node_tree.links.new(t.outputs[0], m.node_tree.nodes["Principled BSDF"].inputs[0])
        _mats[name] = m
    return _mats[name]


# ---------------------------------------------------------------- houses
def walls(a, w, d, z0, h, mat, t=0.14, jagged=None):
    """Four wall slabs around a w x d footprint; jagged=rng breaks the tops into ragged columns (ruins)."""
    for (cx, cy, lx, ly) in ((0, -d / 2, w, t), (0, d / 2, w, t), (-w / 2, 0, t, d - t), (w / 2, 0, t, d - t)):
        if not jagged:
            a.box((lx, ly, h), (cx, cy, z0 + h / 2), mat)
            continue
        # a random walk along the wall: mostly high near the corners, collapsed into gaps in places
        n = max(4, round(max(lx, ly) / 0.16))
        level = jagged.uniform(0.6, 1.0)
        for i in range(n):
            f = (i + 0.5) / n - 0.5
            level = min(1.0, max(0.05, level + jagged.gauss(0, 0.14) + (0.08 if abs(f) > 0.4 else -0.02)))
            hh = h * level
            sx, sy = (lx / n, ly) if lx > ly else (lx, ly / n)
            a.box((sx + 0.002, sy, hh), (cx + f * lx if lx > ly else cx, cy + f * ly if ly > lx else cy, z0 + hh / 2), mat)


def timber_frame(a, w, d, z0, h, rnd):
    t, o = 0.07, 0.075
    for side, (cx, cy, along) in enumerate(((0, -d / 2 - o, "x"), (0, d / 2 + o, "x"), (-w / 2 - o, 0, "y"), (w / 2 + o, 0, "y"))):
        L = w if along == "x" else d
        for z in (z0 + 0.04, z0 + h - 0.04):           # sill and top plates
            a.box((L + 0.1, t, t) if along == "x" else (t, L + 0.1, t), (cx, cy, z), "timber")
        n = max(2, round(L / 0.7))
        for i in range(n + 1):                           # posts
            p = -L / 2 + L * i / n
            a.box((t, t, h), (cx + p, cy, z0 + h / 2) if along == "x" else (cx, cy + p, z0 + h / 2), "timber")
        for i in range(n):                               # braces in some panels
            if rnd.random() < 0.45:
                p = -L / 2 + L * (i + 0.5) / n
                ang = math.atan2(h * 0.8, L / n) * rnd.choice((1, -1))
                ln = math.hypot(h * 0.8, L / n)
                if along == "x":
                    a.box((ln, t * 0.8, t), (cx + p, cy, z0 + h / 2), "timber", rot=(0, ang, 0))
                else:
                    a.box((t * 0.8, ln, t), (cx, cy + p, z0 + h / 2), "timber", rot=(ang, 0, 0))


def windows(a, w, d, z, rnd, door_side=-1):
    for side in (-1, 1):
        n = max(1, int(w / 1.0))
        for i in range(n):
            x = -w / 2 + w * (i + 0.5) / n
            if door_side == side and i == n // 2 and z < H:
                a.box((0.42, 0.05, 0.78), (x, side * (d / 2 + 0.08), 0.18 + 0.39), "door", decal=True)
            elif rnd.random() < 0.85:
                a.box((0.36, 0.05, 0.42), (x, side * (d / 2 + 0.08), z + 0.62), "window", decal=True)
    for side in (-1, 1):
        if d > 1.6 and rnd.random() < 0.7:
            a.box((0.05, 0.36, 0.42), (side * (w / 2 + 0.08), 0, z + 0.62), "window", decal=True)


def gable_roof(a, w, d, z0, pitch=0.62, overhang=0.18, mat="roof"):
    rh = d / 2 * pitch * 1.6
    slope = math.hypot(d / 2 + overhang, rh + overhang * pitch)
    ang = math.atan2(rh, d / 2)
    for s in (-1, 1):
        a.box((w + 2 * overhang, slope, 0.09), (0, s * (d / 4 + overhang / 2 - 0.02), z0 + rh / 2 + 0.02), mat, rot=(-s * ang, 0, 0))
    for s in (-1, 1):
        a.prism(d, 0.12, rh, (s * (w / 2 - 0.06), 0, z0), "plaster", rot=(0, 0, math.pi / 2))
    a.box((w + 2 * overhang + 0.02, 0.1, 0.1), (0, 0, z0 + rh + 0.03), "timber")
    return rh


def house(seed=1, w=3.0, d=2.2, floors=2, style="timber", ruined=False, chimney=True):
    a = Asset(seed)
    rnd = a.rnd
    a.box((w + 0.16, d + 0.16, 0.18), (0, 0, 0.09), "stone")
    top = 0.18 + floors * H
    if ruined:
        jag = random.Random(seed * 7)
        walls(a, w, d, 0.18, H, "stone", jagged=jag if floors == 1 else None)
        if floors > 1:
            walls(a, w, d, 0.18 + H, H * (floors - 1), "plaster", jagged=jag)
        for _ in range(4):   # charred beams that fell in, and rubble
            a.box((rnd.uniform(1.2, w), 0.1, 0.1), (rnd.uniform(-0.4, 0.4), rnd.uniform(-d / 3, d / 3), rnd.uniform(0.3, 1.2)),
                  "charcoal", rot=(rnd.uniform(-0.3, 0.3), rnd.uniform(-0.6, 0.6), rnd.uniform(0, 3.1)))
        for _ in range(14):
            s = rnd.uniform(0.12, 0.28)
            a.box((s, s * 0.8, s * 0.6), (rnd.uniform(-w / 2.5, w / 2.5), rnd.uniform(-d / 2.5, d / 2.5), 0.2 + s * 0.3),
                  "stone", rot=(rnd.uniform(0, 1), rnd.uniform(0, 1), rnd.uniform(0, 3)))
        windows(a, w, d, 0.18, rnd)
        return a.objs
    for f in range(floors):
        z0 = 0.18 + f * H
        mat = "stone" if (style == "stone" or (f == 0 and style == "mixed")) else "plaster"
        walls(a, w, d, z0, H, mat)
        if mat == "plaster":
            timber_frame(a, w, d, z0, H, rnd)
        windows(a, w, d, z0, rnd)
    rh = gable_roof(a, w, d, top)
    if chimney:
        x = rnd.choice((-1, 1)) * w * 0.28
        a.box((0.3, 0.3, rh + 0.5), (x, d * 0.18, top + (rh + 0.5) / 2), "stone")
    return a.objs


def tavern():
    objs = house(seed=11, w=4.2, d=3.0, floors=2, style="mixed")
    a = Asset(12)
    a.box((0.06, 0.9, 0.06), (0, -1.5 - 0.45, 1.75), "iron")              # sign bracket
    a.box((0.55, 0.04, 0.42), (0, -1.5 - 0.75, 1.45), "sign", decal=True)
    return objs + a.objs


# ---------------------------------------------------------------- props
def barrel(seed=1, lying=False):
    a = Asset(seed)
    rot = (math.pi / 2, 0, 0) if lying else (0, 0, 0)
    loc = (0, 0.25, 0.21) if lying else (0, 0, 0)
    prof = [(0.17, 0), (0.205, 0.12), (0.215, 0.25), (0.205, 0.38), (0.17, 0.5)]
    a.lathe(prof, loc, "planks", segs=14, rot=rot)
    for z in (0.06, 0.44):
        r = 0.19 + 0.02 * (1 - abs(z - 0.25) / 0.25)
        a.lathe([(r, z - 0.02), (r + 0.012, z - 0.02), (r + 0.012, z + 0.02), (r, z + 0.02)], loc, "iron", segs=14, rot=rot,
                cap_top=False, cap_bottom=False)
    return a.objs


def keg():
    a = Asset(3)
    objs = barrel(3, lying=True)
    for x in (-0.15, 0.15):
        a.box((0.08, 0.5, 0.12), (x, 0.25, 0.06), "timber")
    return objs + a.objs


def crate(seed=1, s=0.45):
    a = Asset(seed)
    a.box((s, s, s), (0, 0, s / 2), "planks")
    t = 0.05
    for x in (-1, 1):
        for y in (-1, 1):
            a.box((t, t, s + 0.01), (x * (s / 2 - t / 2 + 0.01), y * (s / 2 - t / 2 + 0.01), s / 2), "timber")
    for z in (t / 2, s - t / 2):
        a.box((s + 0.02, s + 0.02, t), (0, 0, z), "timber")
    return a.objs


def crates():
    objs = crate(1)
    for parts, loc, rz in ((crate(2, 0.4), (0.05, 0.02, 0.45), 0.3), (crate(4, 0.38), (0.48, -0.05, 0), -0.2)):
        for o in parts:
            o.location, o.rotation_euler = loc, (0, 0, rz)
        objs += parts
    return objs


def sack(seed=1):
    a = Asset(seed)
    a.blob(0.2, (0, 0, 0.14), "canvas", scale=(1, 0.75, 0.8), jitter=0.1, flat_bottom=-0.1)
    a.cyl(0.05, 0.08, (0, 0, 0.28), "canvas", segs=8, r2=0.07)
    return a.objs


def wheel(a, loc, rot, r=0.32):
    a.cyl(r, 0.05, loc, "iron", segs=16, rot=rot, caps=False)
    a.cyl(r - 0.02, 0.06, loc, "timber", segs=16, rot=rot, r2=r - 0.02)
    a.cyl(0.07, 0.12, loc, "timber", segs=8, rot=rot)
    return a


def cart(broken=False, seed=5):
    a = Asset(seed)
    rnd = a.rnd
    tilt = 0.32 if broken else 0
    z = 0.42
    bed = [a.box((1.3, 0.75, 0.06), (0, 0, z), "planks"),
           a.box((1.3, 0.05, 0.25), (0, -0.4, z + 0.15), "planks"), a.box((1.3, 0.05, 0.25), (0, 0.4, z + 0.15), "planks"),
           a.box((0.05, 0.75, 0.25), (-0.65, 0, z + 0.15), "planks"),
           a.box((1.0, 0.05, 0.05), (1.1, -0.25, z), "timber"), a.box((1.0, 0.05, 0.05), (1.1, 0.25, z), "timber"),
           a.box((0.06, 0.9, 0.06), (0, 0, z - 0.1), "iron")]
    if broken:
        for o in bed:
            o.rotation_euler = (tilt, 0, 0)
        wheel(a, (0, -0.47, 0.32), (math.pi / 2, 0, 0))
        wheel(a, (0.5, 0.9, 0.03), (0, 0, 0))                           # the other wheel lies in the mud
        for _ in range(3):
            a.box((rnd.uniform(0.4, 0.8), 0.12, 0.03), (rnd.uniform(-1, 1), rnd.uniform(0.6, 1.2), 0.02), "planks",
                  rot=(0, 0, rnd.uniform(0, 3)))
    else:
        for y in (-0.47, 0.47):
            wheel(a, (0, y, 0.32), (math.pi / 2, 0, 0))
    return a.objs


def well():
    a = Asset(7)
    a.lathe([(0.34, 0), (0.46, 0), (0.46, 0.5), (0.34, 0.5), (0.34, 0.1)], (0, 0, 0), "stone", segs=14, cap_top=False,
            cap_bottom=False)
    a.cyl(0.36, 0.05, (0, 0, 0.3), "charcoal", segs=14)
    for x in (-0.42, 0.42):
        a.box((0.08, 0.08, 1.1), (x, 0, 0.55), "timber")
    a.box((0.95, 0.06, 0.06), (0, 0, 0.95), "timber")
    for s in (-1, 1):
        a.box((1.2, 0.55, 0.05), (0, s * 0.2, 1.12), "roof", rot=(-s * 0.6, 0, 0))
    a.lathe([(0.07, 0), (0.09, 0.14)], (0, 0, 0.6), "planks", segs=8)
    return a.objs


def stall():
    a = Asset(8)
    for x in (-0.7, 0.7):
        for y in (-0.4, 0.4):
            a.box((0.07, 0.07, 1.25 if y > 0 else 1.0), (x, y, (1.25 if y > 0 else 1.0) / 2), "timber")
    a.box((1.5, 0.85, 0.07), (0, 0, 0.6), "planks")
    a.box((1.5, 0.05, 0.6), (0, -0.43, 0.3), "planks")
    a.box((1.7, 1.05, 0.04), (0, 0, 1.17), "cloth_red", rot=(0.28, 0, 0))
    for i in range(4):
        a.blob(0.08, (-0.5 + i * 0.33, 0.1, 0.7), "leaves", jitter=0.1, subdiv=1)
    return a.objs


def rubble(seed=1, spread=0.9):
    a = Asset(seed)
    rnd = a.rnd
    for _ in range(16):
        s = rnd.uniform(0.1, 0.3)
        a.box((s, s * 0.8, s * 0.6), (rnd.gauss(0, spread / 2.5), rnd.gauss(0, spread / 2.5), s * 0.3), "stone",
              rot=(rnd.uniform(0, 1), rnd.uniform(0, 1), rnd.uniform(0, 3)))
    for _ in range(3):
        a.box((rnd.uniform(0.5, 0.9), 0.08, 0.08), (rnd.gauss(0, 0.3), rnd.gauss(0, 0.3), 0.08), "charcoal",
              rot=(0, rnd.uniform(-0.3, 0.3), rnd.uniform(0, 3)))
    return a.objs


def grate():
    a = Asset(9)
    s, t = 1.4, 0.12
    for x, y, lx, ly in ((0, -s / 2, s, t), (0, s / 2, s, t), (-s / 2, 0, t, s), (s / 2, 0, t, s)):
        a.box((lx, ly, 0.05), (x, y, 0.025), "stone")
    a.box((s - t, s - t, 0.01), (0, 0, 0.005), "charcoal")
    for i in range(7):
        p = -s / 2 + t + (s - 2 * t) * (i + 0.5) / 7
        a.box((0.04, s - t, 0.04), (p, 0, 0.03), "iron")
        a.box((s - t, 0.04, 0.035), (0, p, 0.025), "iron")
    return a.objs


def rock(seed=1, size=1.0, tall=1.0):
    a = Asset(seed)
    a.blob(0.5 * size, (0, 0, 0.25 * size * tall), "rock", scale=(1, 0.85, 0.75 * tall), jitter=0.22, subdiv=2,
           flat_bottom=-0.25 * size * tall)
    return a.objs


def pine(seed=1, h=2.6):
    a = Asset(seed)
    a.cyl(0.09, h * 0.35, (0, 0, 0), "bark", segs=7, r2=0.06)
    for i, (r, z) in enumerate(((0.6, 0.25), (0.48, 0.45), (0.34, 0.63), (0.2, 0.8))):
        a.cyl(r, h * 0.3, (0, 0, h * z), "pine", segs=9, r2=0.02, rot=(0, 0, a.rnd.uniform(0, 1)))
    return a.objs


def oak(seed=1, h=2.2):
    a = Asset(seed)
    a.cyl(0.13, h * 0.55, (0, 0, 0), "bark", segs=8, r2=0.09)
    rnd = a.rnd
    for _ in range(5):
        a.blob(rnd.uniform(0.4, 0.6), (rnd.uniform(-0.35, 0.35), rnd.uniform(-0.35, 0.35), h * rnd.uniform(0.6, 0.85)),
               "leaves", jitter=0.18, subdiv=2)
    return a.objs


def stump(seed=1):
    a = Asset(seed)
    a.cyl(0.2, 0.3, (0, 0, 0), "bark", segs=10, r2=0.17, caps=False)
    a.cyl(0.17, 0.01, (0, 0, 0.3), "woodend", segs=10)
    return a.objs


def log(seed=1, length=1.0):
    a = Asset(seed)
    a.cyl(0.2, length, (-length / 2, 0, 0.2), "bark", segs=10, rot=(0, math.pi / 2, 0), caps=False)
    for x in (-length / 2, length / 2):
        a.cyl(0.2, 0.01, (x, 0, 0.2), "woodend", segs=10, rot=(0, math.pi / 2, 0))
    return a.objs


def lumber():
    a = Asset(4)
    objs = []
    for i, (y, z) in enumerate(((-0.2, 0), (0, 0), (0.2, 0), (-0.1, 0.17), (0.1, 0.17))):
        for o in log(10 + i, 1.4):
            o.location = (0, y, z * 1.0)
            o.scale = (1, 0.45, 0.45)
            objs.append(o)
    return objs


def wall_segment(kind="plain", seed=1):
    """Dungeon wall, 1.8 long (x), 0.35 thick, 1.6 high."""
    a = Asset(seed)
    if kind == "broken":
        rnd = a.rnd
        for i in range(6):
            hh = 1.6 * rnd.uniform(0.3, 1.0)
            a.box((0.3, 0.35, hh), (-0.75 + i * 0.3, 0, hh / 2), "bricks")
        return a.objs
    a.box((1.8, 0.35, 1.6), (0, 0, 0.8), "bricks")
    a.box((1.86, 0.42, 0.1), (0, 0, 1.63), "stone")
    if kind == "door":
        a.box((0.7, 0.04, 1.15), (0, -0.2, 0.58), "door_iron", decal=True)
    return a.objs


def pillar():
    a = Asset(2)
    a.box((0.55, 0.55, 0.15), (0, 0, 0.075), "stone")
    a.cyl(0.2, 1.4, (0, 0, 0.15), "bricks", segs=10)
    a.box((0.5, 0.5, 0.12), (0, 0, 1.6), "stone")
    return a.objs


def tent(seed=1):
    a = Asset(seed)
    w, d, h = 1.3, 1.4, 0.95
    ang = math.atan2(h, w / 2)
    ln = math.hypot(h, w / 2)
    for s in (-1, 1):
        a.box((0.03, d, ln), (s * w / 4, 0, h / 2), "canvas", rot=(0, s * (math.pi / 2 - ang) * -1, 0))
    for y in (-d / 2, d / 2):
        a.cyl(0.03, h + 0.05, (0, y, 0), "timber", segs=6)
    a.box((0.04, d + 0.1, 0.04), (0, 0, h), "timber")
    return a.objs


def bedroll(seed=1):
    a = Asset(seed)
    a.box((0.45, 1.0, 0.06), (0, 0, 0.03), "canvas")
    a.cyl(0.09, 0.45, (-0.225, 0.42, 0.09), "cloth_red", segs=8, rot=(0, math.pi / 2, 0))
    return a.objs


def brazier():
    a = Asset(3)
    for i in range(3):
        t = 2 * math.pi * i / 3
        a.box((0.04, 0.04, 0.7), (0.15 * math.cos(t), 0.15 * math.sin(t), 0.35), "iron", rot=(0.2 * math.sin(t), -0.2 * math.cos(t), 0))
    a.lathe([(0.08, 0.62), (0.26, 0.72), (0.28, 0.8)], (0, 0, 0), "iron", segs=12, cap_top=False)
    a.blob(0.18, (0, 0, 0.85), "charcoal", scale=(1, 1, 0.4), jitter=0.2, subdiv=1)
    a.cyl(0.18, 0.4, (0, 0, 0.84), "flame", segs=7, r2=0.01)
    return a.objs


def table_round():
    a = Asset(4)
    a.cyl(0.55, 0.06, (0, 0, 0.5), "planks", segs=16)
    a.cyl(0.56, 0.42, (0, 0, 0.1), "cloth_red", segs=16, r2=0.56, caps=False)
    a.cyl(0.08, 0.5, (0, 0, 0), "timber", segs=8)
    for i in range(3):
        t = 2 * math.pi * i / 3 + 0.4
        a.cyl(0.03, 0.12, (0.28 * math.cos(t), 0.28 * math.sin(t), 0.56), "plaster", segs=6)
        a.cyl(0.012, 0.03, (0.28 * math.cos(t), 0.28 * math.sin(t), 0.68), "flame", segs=5, r2=0.001)
    return a.objs


def chair(seed=1, throne=False):
    a = Asset(seed)
    s, back = (0.55, 1.2) if throne else (0.38, 0.8)
    for x in (-1, 1):
        for y in (-1, 1):
            a.box((0.05, 0.05, 0.42), (x * (s / 2 - 0.03), y * (s / 2 - 0.03), 0.21), "timber")
    a.box((s, s, 0.05), (0, 0, 0.44), "planks")
    a.box((s, 0.06, back - 0.44), (0, s / 2 - 0.03, 0.44 + (back - 0.44) / 2), "planks")
    if throne:
        a.box((s - 0.08, s - 0.1, 0.06), (0, -0.02, 0.49), "cloth_red")
        a.box((s - 0.1, 0.04, back - 0.6), (0, s / 2 - 0.08, 0.55 + (back - 0.6) / 2), "cloth_red")
        for x in (-1, 1):
            a.box((0.06, s, 0.06), (x * s / 2, 0, 0.7), "timber")
            a.blob(0.06, (x * s / 2, s / 2, back), "gold", jitter=0.05, subdiv=1)
    return a.objs


def chest(seed=1, gold=False):
    a = Asset(seed)
    a.box((0.6, 0.4, 0.32), (0, 0, 0.16), "planks")
    a.cyl(0.2, 0.6, (-0.3, 0, 0.32), "planks", segs=10, rot=(0, math.pi / 2, 0))
    for x in (-0.22, 0.22):
        a.box((0.05, 0.42, 0.34), (x, 0, 0.17), "iron")
        a.cyl(0.205, 0.05, (x - 0.025, 0, 0.32), "iron", segs=10, rot=(0, math.pi / 2, 0))
    a.box((0.08, 0.03, 0.1), (0, -0.21, 0.3), "gold" if gold else "iron")
    return a.objs


def coins(seed=1):
    a = Asset(seed)
    rnd = a.rnd
    a.cyl(0.32, 0.14, (0, 0, 0), "gold", segs=12, r2=0.05)
    for _ in range(10):
        a.cyl(0.04, 0.012, (rnd.uniform(-0.45, 0.45), rnd.uniform(-0.45, 0.45), 0), "gold", segs=8)
    return a.objs


def banner():
    a = Asset(5)
    a.cyl(0.03, 1.9, (0, 0, 0), "timber", segs=6)
    a.box((0.7, 0.04, 0.04), (0, 0, 1.75), "timber")
    a.box((0.6, 0.02, 1.0), (0, -0.03, 1.22), "banner", decal=True)
    return a.objs


def bridge():
    a = Asset(6)
    rnd = a.rnd
    for i in range(6):
        a.box((2.6, 0.22, 0.06), (0, -0.6 + i * 0.24, 0.05), "planks", rot=(0, 0, rnd.uniform(-0.04, 0.04)))
    for y in (-0.5, 0.5):
        a.box((2.6, 0.08, 0.08), (0, y, 0.0), "timber")
    return a.objs


def campfire_cold():
    a = Asset(7)
    for i in range(9):
        t = 2 * math.pi * i / 9
        a.blob(0.09, (0.3 * math.cos(t), 0.3 * math.sin(t), 0.04), "rock", jitter=0.25, subdiv=1)
    for i in range(3):
        a.cyl(0.05, 0.45, (0, 0, 0.04), "charcoal", segs=6, rot=(0, math.pi / 2 - 0.2, i * 2.1))
    a.cyl(0.22, 0.02, (0, 0, 0), "charcoal", segs=10)
    return a.objs


def stalagmite(seed=1):
    a = Asset(seed)
    a.cyl(0.3, 1.3, (0, 0, 0), "rock", segs=7, r2=0.03, rot=(a.rnd.uniform(-0.1, 0.1), a.rnd.uniform(-0.1, 0.1), 0))
    a.cyl(0.18, 0.7, (0.28, 0.1, 0), "rock", segs=6, r2=0.02)
    return a.objs


def grove(kind, n, seed=3):
    """A clump of trees as one prop (fewer objects on the TTS table)."""
    rnd, objs = random.Random(seed), []
    for i in range(n):
        parts = kind(seed + i, rnd.uniform(2.2, 3.2)) if kind is pine else kind(seed + i, rnd.uniform(1.8, 2.4))
        x, y = (0, 0) if i == 0 else (rnd.uniform(-1.1, 1.1), rnd.uniform(-1.1, 1.1))
        for o in parts:
            o.location = (x, y, 0)
        objs += parts
    return objs


def fence():
    a = Asset(8)
    for x in (-0.9, 0, 0.9):
        a.box((0.07, 0.07, 0.6), (x, 0, 0.3), "timber")
    for z in (0.2, 0.45):
        a.box((1.9, 0.04, 0.08), (0, 0, z), "planks")
    return a.objs


ASSETS = {
    "house_a": lambda: house(1, 3.0, 2.2, 2, "timber"), "house_b": lambda: house(2, 2.6, 2.0, 2, "mixed"),
    "house_c": lambda: house(3, 3.4, 2.4, 1, "stone"), "house_d": lambda: house(4, 2.4, 2.4, 2, "timber"),
    "tavern": tavern, "ruin_a": lambda: house(5, 3.0, 2.4, 2, ruined=True), "ruin_b": lambda: house(6, 3.6, 2.2, 2, ruined=True),
    "ruin_c": lambda: house(7, 2.4, 2.2, 1, ruined=True),
    "barrel": barrel, "keg": keg, "crate": crate, "crates": crates, "sack": sack, "cart": cart,
    "broken_cart": lambda: cart(broken=True), "well": well, "stall": stall, "rubble": rubble, "grate": grate,
    "rock_a": lambda: rock(1), "rock_b": lambda: rock(2, 1.3, 1.4), "rock_c": lambda: rock(3, 0.7),
    "rock_d": lambda: rock(4, 1.6, 0.8), "rock_e": lambda: rock(5, 1.1, 1.8),
    "pine": pine, "pine_b": lambda: pine(2, 3.2), "oak": oak, "stump": stump, "log_large": lambda: log(1, 1.0),
    "lumber": lumber, "wall": wall_segment, "wall_broken": lambda: wall_segment("broken"),
    "wall_door": lambda: wall_segment("door"), "pillar": pillar, "tent": tent, "bed": bedroll, "torch": brazier,
    "table_feast": table_round, "chair": chair, "throne": lambda: chair(2, throne=True), "chest": chest,
    "chest_gold": lambda: chest(2, gold=True), "coins": coins, "banner": banner, "bridge": bridge,
    "campfire_cold": campfire_cold, "stalagmite": stalagmite, "fence": fence,
    "pines": lambda: grove(pine, 5), "oaks": lambda: grove(oak, 4),
}

if __name__ == "__main__":
    names = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    textures = {}
    tex_list = OUT / "textures.txt"
    if tex_list.exists():
        textures = dict(l.split() for l in tex_list.read_text().splitlines() if l.strip())
    for name in names or ASSETS:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        _mats.clear()
        for old in OUT.glob(f"{name}.*"):
            old.unlink()
        textures[name] = bake_objects(name, ASSETS[name](), OUT)
        tex_list.write_text("".join(f"{n} {t}\n" for n, t in sorted(textures.items())))
