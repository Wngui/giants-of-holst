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
G, U = 1.45, 1.25   # ground / upper storey height in squares (a person is ~1.2: doors 1.14)


# ---------------------------------------------------------------- mesh helpers
class Asset:
    def __init__(self, seed=1):
        self.objs, self.rnd = [], random.Random(seed)

    def add(self, bm, mat, decal=False, smooth=False):
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
            p.use_smooth = smooth
        self.objs.append(ob)
        return ob

    # primitives: each makes one part with one material
    def box(self, size, loc, mat, rot=(0, 0, 0), decal=False):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1)
        bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
        place(bm, loc, rot)
        return self.add(bm, mat, decal)

    def cyl(self, r, h, loc, mat, segs=10, r2=None, rot=(0, 0, 0), caps=True, smooth=False):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=caps, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=h)
        bmesh.ops.translate(bm, vec=Vector((0, 0, h / 2)), verts=bm.verts)
        if smooth and caps:   # caps stay flat: split them off so they don't smear the side normals
            bmesh.ops.split_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-6])
        place(bm, loc, rot)
        return self.add(bm, mat, smooth=smooth)

    def lathe(self, profile, loc, mat, segs=12, rot=(0, 0, 0), cap_top=True, cap_bottom=True, smooth=False):
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
        return self.add(bm, mat, smooth=smooth)

    def blob(self, r, loc, mat, scale=(1, 1, 1), jitter=0.15, subdiv=2, flat_bottom=None, lumps=0.0, cuts=0, smooth=False):
        """Lumpy sphere: jitter = per-vertex noise, lumps = smooth low-frequency bulges, cuts = flat cleavage planes."""
        rnd = self.rnd
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=r)
        waves = [(Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized() * rnd.uniform(1.5, 3.5) / r,
                  rnd.uniform(0, 6.3)) for _ in range(5)]
        planes = [(Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.uniform(-0.2, 1.2))).normalized(), r * rnd.uniform(0.7, 0.9))
                  for _ in range(cuts)]
        for v in bm.verts:
            v.co *= 1 + rnd.uniform(-jitter, jitter) + lumps * sum(math.sin(v.co.dot(k) + ph) for k, ph in waves) / 5
            for n, d in planes:
                v.co -= n * max(0.0, v.co.dot(n) - d)
            v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
            if flat_bottom is not None and v.co.z < flat_bottom:
                v.co.z = flat_bottom
        bm.normal_update()
        place(bm, loc, (rnd.uniform(0, 0.3), 0, rnd.uniform(0, 6.3)))
        return self.add(bm, mat, smooth=smooth)

    def wall_profile(self, L, t, tops, loc, rz, mat):
        """Wall slab L long (x), t thick, whose top follows heights `tops` sampled evenly along it (a broken wall)."""
        bm = bmesh.new()
        xs = [-L / 2 + L * i / (len(tops) - 1) for i in range(len(tops))]
        f = [(bm.verts.new((x, -t / 2, 0)), bm.verts.new((x, -t / 2, z))) for x, z in zip(xs, tops)]
        b = [(bm.verts.new((x, t / 2, 0)), bm.verts.new((x, t / 2, z))) for x, z in zip(xs, tops)]
        for i in range(len(xs) - 1):
            bm.faces.new((f[i][0], f[i + 1][0], f[i + 1][1], f[i][1]))
            bm.faces.new((b[i + 1][0], b[i][0], b[i][1], b[i + 1][1]))
            bm.faces.new((f[i][1], f[i + 1][1], b[i + 1][1], b[i][1]))
        bm.faces.new((b[0][0], f[0][0], f[0][1], b[0][1]))
        bm.faces.new((f[-1][0], b[-1][0], b[-1][1], f[-1][1]))
        bm.normal_update()
        place(bm, loc, (0, 0, rz))
        return self.add(bm, mat)

    def beam(self, p1, p2, t, mat):
        """Square beam of thickness t from point p1 to p2."""
        p1, p2 = Vector(p1), Vector(p2)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1)
        bmesh.ops.scale(bm, vec=Vector(((p2 - p1).length, t, t)), verts=bm.verts)
        m = Matrix.Translation((p1 + p2) / 2) @ Vector((1, 0, 0)).rotation_difference(p2 - p1).to_matrix().to_4x4()
        bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
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
def walls(a, w, d, z0, h, mat, t=0.14, broken=None):
    """Four wall slabs around a w x d footprint; broken=rng collapses each wall along a slope with ragged courses (ruins)."""
    for (cx, cy, lx, ly) in ((0, -d / 2, w, t), (0, d / 2, w, t), (-w / 2, 0, t, d - t), (w / 2, 0, t, d - t)):
        if not broken:
            a.box((lx, ly, h), (cx, cy, z0 + h / 2), mat)
            continue
        L = max(lx, ly)
        n = max(4, round(L / 0.22))
        lo, hi = sorted((broken.uniform(0.05, 0.4), broken.uniform(0.6, 1.0)))
        if broken.random() < 0.5:
            lo, hi = hi, lo
        walk, tops = 0, []
        for i in range(n + 1):   # the break slopes from one end down to the other, ragged, with the odd step
            walk = walk * 0.5 + broken.gauss(0, 0.09) + (broken.choice((-0.15, 0.15)) if broken.random() < 0.2 else 0)
            tops.append(h * min(1.0, max(0.05, lo + (hi - lo) * i / n + walk)))
        a.wall_profile(L, min(lx, ly), tops, (cx, cy, z0), 0 if lx > ly else math.pi / 2, mat)


def facade(a, w, d, z0, h, rnd, framed, door=False, flowers=0.0):
    """One storey's walls dressed: posts split each wall into panels; a panel holds the door (front, ground floor),
    a window with sill (and maybe a flower box), a timber brace, or nothing. Front = -y."""
    t, o = 0.07, 0.075
    for cx, cy, along, s in ((0, -d / 2 - o, "x", -1), (0, d / 2 + o, "x", 1), (-w / 2 - o, 0, "y", -1), (w / 2 + o, 0, "y", 1)):
        L = w if along == "x" else d

        def put(p, z, ln, th, hg, mat, off=0.0, rot=0.0, decal=False):   # box at p along the wall, off = out from it
            if along == "x":
                return a.box((ln, th, hg), (cx + p, cy + s * off, z), mat, rot=(0, rot, 0), decal=decal)
            return a.box((th, ln, hg), (cx + s * off, cy + p, z), mat, rot=(rot, 0, 0), decal=decal)
        n = max(2, round(L / 0.75))
        pw = L / n
        if framed:
            for z in (z0 + 0.04, z0 + h - 0.04):
                put(0, z, L + 0.1, t, t, "timber")
            for i in range(n + 1):
                put(-L / 2 + pw * i, z0 + h / 2, t, t, h, "timber")
        for i in range(n):
            p = -L / 2 + pw * (i + 0.5)
            if door and along == "x" and s == -1 and i == n // 2:
                put(p, z0 + 0.57, 0.58, 0.03, 1.14, "door", decal=True)
                for q in (-0.33, 0.33):
                    put(p + q, z0 + 0.6, 0.08, 0.1, 1.2, "timber", 0.02)
                put(p, z0 + 1.22, 0.78, 0.12, 0.1, "timber", 0.02)
                put(p, z0 - 0.08, 0.8, 0.3, 0.1, "stone", 0.15)
                continue
            if along == "y" and (L < 1.6 or rnd.random() < 0.4):
                continue
            if rnd.random() < 0.8:
                zc = z0 + h * 0.58
                put(p, zc, 0.42, 0.03, 0.5, "window", decal=True)
                put(p, zc - 0.28, 0.54, 0.12, 0.05, "timber" if framed else "stone", 0.03)
                if not framed:
                    put(p, zc + 0.29, 0.54, 0.08, 0.08, "stone", 0.02)
                if rnd.random() < flowers:
                    put(p, zc - 0.36, 0.5, 0.14, 0.12, "planks", 0.08)
                    for k in range(5):
                        q = p - 0.2 + 0.1 * k
                        b = a.blob(0.07, (0, 0, 0), "leaves", jitter=0.2, subdiv=1)
                        b.location = (cx + q, cy + s * 0.15, zc - 0.27) if along == "x" else (cx + s * 0.15, cy + q, zc - 0.27)
                        f = a.blob(0.035, (0, 0, 0), rnd.choice(("cloth_red", "gold", "plaster_white")), jitter=0.2, subdiv=1)
                        f.location = b.location + Vector((0, 0, 0.05))
            elif framed and rnd.random() < 0.6:
                ang = math.atan2(h * 0.85, pw) * rnd.choice((1, -1))
                put(p, z0 + h / 2, math.hypot(h * 0.85, pw), t * 0.8, t, "timber", rot=ang if along == "x" else -ang)
        if framed:
            for i in range(n):   # sill rail under the windows
                put(-L / 2 + pw * (i + 0.5), z0 + h * 0.27, pw, t * 0.9, t * 0.8, "timber")


def gable_roof(a, w, d, z0, mat="roof", pitch=1.0, eave=0.28, verge=0.22, gable="plaster"):
    """Pitched roof over a w x d top, ridge along x, with gable walls, ridge cap and eave overhangs. Returns its height."""
    rh = d / 2 * pitch
    ang = math.atan2(rh, d / 2)
    th = 0.22 if mat == "thatch" else 0.08
    run = (d / 2 + eave) / math.cos(ang) + 0.04
    for s in (-1, 1):
        r = run / 2 - 0.04
        a.box((w + 2 * verge, run, th), (0, s * (r * math.cos(ang) + th / 2 * math.sin(ang)),
                                        z0 + rh - r * math.sin(ang) + th / 2 * math.cos(ang)), mat, rot=(-s * ang, 0, 0))
        if mat == "thatch":   # rounded eave: thatch is a thick soft blanket, not a board
            r = run - 0.04
            a.cyl(th * 0.55, w + 2 * verge, (-(w / 2 + verge), s * (r * math.cos(ang) + th / 2 * math.sin(ang)),
                  z0 + rh - r * math.sin(ang) + th / 2 * math.cos(ang)), mat, segs=10, rot=(0, math.pi / 2, 0), smooth=True)
    for s in (-1, 1):
        a.prism(d, 0.12, rh, (s * (w / 2 - 0.06), 0, z0), gable, rot=(0, 0, math.pi / 2))
        if gable == "plaster":
            a.box((0.07, 0.07, rh * 0.9), (s * (w / 2 + 0.01), 0, z0 + rh * 0.45), "timber")
            a.box((0.07, d * 0.5, 0.07), (s * (w / 2 + 0.01), 0, z0 + rh * 0.48), "timber")
    if mat == "thatch":
        a.cyl(0.16, w + 2 * verge, (-(w / 2 + verge), 0, z0 + rh + 0.06), "thatch", segs=10, rot=(0, math.pi / 2, 0), smooth=True)
    else:
        a.box((w + 2 * verge + 0.02, 0.14, 0.12), (0, 0, z0 + rh + 0.06), "timber" if mat == "roof" else mat)
    return rh


def house(seed=1, w=3.0, d=2.2, floors=2, style="timber", ruined=False, chimney=True, roof="roof", plaster="plaster",
          front=False, jetty=0.2, annex=0, flowers=0.35):
    """Town house: stone plinth, ground storey G, upper storeys U each jettied out `jetty` over the street sides,
    pitched roof (front=True turns its gable to the street), exterior chimney stack, optional lean-to (annex=-1/1)."""
    a = Asset(seed)
    rnd = a.rnd
    a.box((w + 0.2, d + 0.2, 0.14), (0, 0, 0.07), "stone")
    if ruined:
        return ruin(a, w, d, floors, seed)
    z0, dd = 0.14, d
    for f in range(floors):
        h = G if f == 0 else U
        if f and jetty:
            for x in [-w / 2 + 0.06 + (w - 0.12) * i / round(w / 0.32) for i in range(round(w / 0.32) + 1)]:
                for s in (-1, 1):
                    a.box((0.08, jetty + 0.14, 0.09), (x, s * (dd / 2 + jetty / 2), z0 - 0.04), "timber")
            dd += 2 * jetty
        mat = "stone" if (style == "stone" or (f == 0 and style == "mixed")) else plaster
        walls(a, w, dd, z0, h, mat)
        facade(a, w, dd, z0, h, rnd, framed=mat != "stone", door=f == 0, flowers=flowers if f else flowers / 3)
        z0 += h
    r = Asset(seed + 50)
    rw, rd = (dd, w) if front else (w, dd)
    rh = gable_roof(r, rw, rd, z0, roof, pitch=(0.8 if rd > 3 else 1.1) if roof == "thatch" else 1.0,
                    gable="stone" if style == "stone" else plaster)
    for o in r.objs:
        o.rotation_euler.z = math.pi / 2 if front else 0
    a.objs += r.objs
    if chimney:
        s = rnd.choice((-1, 1))
        y = rnd.uniform(-0.2, 0.2) * d
        top = z0 + (rh * 0.4 if front else rh) + 0.45
        a.box((0.55, 0.5, G + 0.14), (s * (w / 2 + 0.2), y, (G + 0.14) / 2), "stone")
        a.box((0.42, 0.4, top), (s * (w / 2 + 0.17), y, top / 2), "stone")
        a.box((0.52, 0.5, 0.08), (s * (w / 2 + 0.17), y, top), "stone")
        for k in (-0.09, 0.09):
            a.cyl(0.055, 0.16, (s * (w / 2 + 0.17), y + k, top + 0.04), "shingle", segs=8, r2=0.045)
    if annex:
        aw, ad, ah = 0.95, d * 0.7, 0.95
        x = annex * (w / 2 + aw / 2 + 0.07)
        walls(a, aw, ad, 0.14, ah, "planks")
        for o in a.objs[-4:]:
            o.location.x += x
        ang = math.atan2(0.35, aw)
        a.box((math.hypot(aw + 0.2, 0.4), ad + 0.3, 0.07), (x, 0, 0.14 + ah + 0.2), "shingle" if roof == "roof" else roof,
              rot=(0, annex * ang, 0))
        a.box((0.5, 0.03, 0.85), (x, -ad / 2 - 0.08, 0.14 + 0.43), "door", decal=True)
    return a.objs


def ruin(a, w, d, floors, seed):
    """Burnt-out house: walls collapsed along slopes, one gable end still standing, charred rafters hanging off it."""
    rnd, jag = a.rnd, random.Random(seed * 7)
    top = 0.14 + G + U * (floors - 1)
    walls(a, w, d, 0.14, G, "stone", broken=jag if floors == 1 else None)
    if floors > 1:
        walls(a, w, d, 0.14 + G, U * (floors - 1), "plaster", broken=jag)
    s = rnd.choice((-1, 1))
    rh = d / 2
    a.box((0.16, d, top - 0.14), (s * w / 2, 0, (top + 0.14) / 2), "stone")
    a.prism(d, 0.16, rh, (s * w / 2, 0, top), "stone", rot=(0, 0, math.pi / 2))
    a.box((w - 0.2, d - 0.2, 0.03), (0, 0, 0.15), "charcoal")
    for k in range(5):   # rafters: hooked over the gable, broken off or slumped to the floor
        y = (k / 4 - 0.5) * d * 0.8
        z = top + rh * (1 - abs(y) / (d / 2))
        end = (s * w / 2 - s * rnd.uniform(0.8, w * 0.9), y + rnd.uniform(-0.3, 0.3),
               rnd.choice((0.2, z - rnd.uniform(0.4, 1.0))))
        a.beam((s * (w / 2 - 0.05), y, z - 0.05), end, 0.09, "charcoal")
    for _ in range(18):
        sz = rnd.uniform(0.1, 0.3)
        x, y = rnd.uniform(-w / 2.2, w / 2.2), rnd.uniform(-d / 2 - 0.6, d / 3)
        a.box((sz, sz * 0.8, sz * 0.6), (x, y, 0.14 + sz * 0.3), "stone", rot=(rnd.uniform(0, 1), rnd.uniform(0, 1), rnd.uniform(0, 3)))
    a.box((0.6, 1.0, 0.05), (rnd.uniform(-w / 4, w / 4), -0.2, 0.2), "planks", rot=(0.15, 0.1, rnd.uniform(0, 3)))
    return a.objs


def tavern():
    objs = house(seed=11, w=4.2, d=2.8, floors=3, style="mixed", roof="thatch", plaster="plaster_white", flowers=0.6)
    a = Asset(12)
    a.box((0.06, 0.9, 0.06), (1.0, -1.4 - 0.2 - 0.45, 2.2), "iron")              # sign bracket over the street
    a.box((0.04, 0.04, 0.3), (1.0, -1.4 - 0.2 - 0.75, 2.02), "iron")
    a.box((0.55, 0.04, 0.42), (1.0, -1.4 - 0.2 - 0.75, 1.65), "sign", decal=True)
    for x in (-0.6, 0.6):   # lanterns either side of the door
        a.box((0.12, 0.12, 0.18), (x - 0.0, -1.4 - 0.25, 1.25), "flame")
        a.box((0.16, 0.16, 0.04), (x, -1.4 - 0.25, 1.36), "iron")
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
    """Boulder: lumpy smooth body with a few flat cleavage faces, sunk into the ground, plus a couple of loose stones."""
    a = Asset(seed)
    a.blob(0.5 * size, (0, 0, 0.22 * size * tall), "rock", scale=(1, 0.85, 0.8 * tall), jitter=0.03, subdiv=3,
           lumps=0.25, cuts=6, smooth=True, flat_bottom=-0.22 * size * tall)
    for _ in range(2):
        t = a.rnd.uniform(0, 6.3)
        a.blob(0.09 * size, (0.5 * size * math.cos(t), 0.45 * size * math.sin(t), 0.02), "rock", jitter=0.05, subdiv=2,
               lumps=0.2, cuts=2, smooth=True, scale=(1, 0.8, 0.6), flat_bottom=-0.02)
    return a.objs


def pine(seed=1, h=2.6):
    """Fir: trunk with root flare and six drooping tiers whose rims are cut into branch tips."""
    a = Asset(seed)
    rnd = a.rnd
    a.lathe([(0.16, 0), (0.1, 0.12), (0.08, h * 0.4), (0.03, h * 0.95)], (0, 0, 0), "bark", segs=8, smooth=True)
    tiers = 6
    for i in range(tiers):
        f = i / (tiers - 1)
        r, z, th = 0.72 * (1 - f * 0.8), h * (0.22 + 0.62 * f), h * (0.26 - 0.08 * f)
        segs = 14
        prof = []
        bm = bmesh.new()
        tip = bm.verts.new((0, 0, z + th))
        rim = []
        for k in range(segs):
            t = 2 * math.pi * (k + rnd.uniform(-0.2, 0.2)) / segs
            rr = r * (1.0 if k % 2 == 0 else 0.72) * rnd.uniform(0.85, 1.1)
            rim.append(bm.verts.new((rr * math.cos(t), rr * math.sin(t), z - (0.08 if k % 2 == 0 else 0.0) * h / 2.6)))
        inner = [bm.verts.new((v.co.x * 0.55, v.co.y * 0.55, z + 0.05)) for v in rim]
        for k in range(segs):
            j = (k + 1) % segs
            bm.faces.new((rim[k], rim[j], tip))
            bm.faces.new((inner[j], inner[k], tip))   # underside, so the tier isn't hollow from below
            bm.faces.new((rim[j], rim[k], inner[k], inner[j]))
        bm.normal_update()
        place(bm, (0, 0, 0), (0, 0, rnd.uniform(0, 1)))
        a.add(bm, "pine", smooth=True)
    return a.objs


def oak(seed=1, h=2.2):
    """Broadleaf: flared trunk forking into three limbs, a canopy of lumpy leaf clusters around them."""
    a = Asset(seed)
    rnd = a.rnd
    a.lathe([(0.24, 0), (0.15, 0.15), (0.12, h * 0.45), (0.1, h * 0.55)], (0, 0, 0), "bark", segs=9, smooth=True)
    tips = []
    for k in range(3):
        t = 2 * math.pi * k / 3 + rnd.uniform(-0.4, 0.4)
        tip = (0.5 * math.cos(t), 0.5 * math.sin(t), h * rnd.uniform(0.7, 0.8))
        a.beam((0, 0, h * 0.5), tip, 0.09, "bark")
        tips.append(tip)
    for k in range(9):
        x, y, z = tips[k % 3] if k < 6 else (0, 0, h * 0.85)
        a.blob(rnd.uniform(0.38, 0.52), (x + rnd.uniform(-0.2, 0.2), y + rnd.uniform(-0.2, 0.2), z + rnd.uniform(-0.05, 0.25)),
               "leaves", jitter=0.06, subdiv=3, lumps=0.3, smooth=True, scale=(1, 1, 0.8))
    return a.objs


def stump(seed=1):
    a = Asset(seed)
    a.lathe([(0.3, 0), (0.21, 0.08), (0.18, 0.3)], (0, 0, 0), "bark", segs=10, cap_top=False, cap_bottom=False, smooth=True)
    a.cyl(0.17, 0.01, (0, 0, 0.3), "woodend", segs=10)
    return a.objs


def trunk(seed=1, length=5.0):
    """A whole felled tree thrown across the road: tapering trunk, root plate, branch stubs."""
    a = Asset(seed)
    rnd = a.rnd
    a.lathe([(0.34, 0), (0.3, 0.4), (0.25, length * 0.5), (0.16, length)], (-length / 2, 0, 0.3), "bark", segs=12,
            rot=(0, math.pi / 2, 0), smooth=True, cap_top=False)
    a.cyl(0.16, 0.01, (length / 2, 0, 0.3), "woodend", segs=12, rot=(0, math.pi / 2, 0))
    for k in range(7):   # roots splayed from the base
        t = 2 * math.pi * k / 7 + rnd.uniform(-0.2, 0.2)
        a.beam((-length / 2 + 0.1, 0, 0.3), (-length / 2 - 0.35, 0.65 * math.cos(t), 0.3 + 0.6 * math.sin(t)), 0.1, "bark")
    a.blob(0.45, (-length / 2 - 0.15, 0, 0.3), "dirt_road", scale=(0.4, 1, 1), jitter=0.15, subdiv=2, smooth=True)
    for k in range(5):   # snapped-off branches
        x = -length / 2 + length * (0.35 + 0.13 * k)
        side = rnd.choice((-1, 1))
        a.beam((x, 0, 0.3), (x + 0.4, side * rnd.uniform(0.5, 0.9), 0.3 + rnd.uniform(0.0, 0.5)), 0.08, "bark")
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
    a.prism(w * 0.98, 0.03, h * 0.98, (0, d / 2 - 0.02, 0), "canvas")              # closed back
    a.box((w * 0.9, d * 0.8, 0.02), (0, 0.05, 0.01), "cloth_red")                  # bedding inside
    for s in (-1, 1):   # guy ropes and pegs
        a.beam((0, s * (d / 2 + 0.02), h), (0, s * (d / 2 + 0.45), 0.02), 0.015, "planks")
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
        a.box((3.0, 0.22, 0.06), (0, -0.6 + i * 0.24, 0.22), "planks", rot=(0, 0, rnd.uniform(-0.04, 0.04)))
    for y in (-0.5, 0.5):   # stringers resting on the channel kerbs
        a.box((3.0, 0.08, 0.1), (0, y, 0.14), "timber")
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
    for (x, y, r, h) in ((0, 0, 0.32, 1.4), (0.3, 0.12, 0.18, 0.75), (-0.2, 0.22, 0.12, 0.45)):
        prof = [(r * k, h * z) for k, z in ((1.25, 0), (1.0, 0.08), (0.75, 0.3), (0.5, 0.55), (0.28, 0.8), (0.04, 1.0))]
        a.lathe(prof, (x, y, 0), "rock", segs=10, smooth=True, rot=(a.rnd.uniform(-0.12, 0.12), a.rnd.uniform(-0.12, 0.12), 0))
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


def door_smashed():
    """A house door ripped out whole and dropped in the street, cracked, with splinters and a torn-off hinge."""
    a = Asset(21)
    rnd = a.rnd
    a.box((0.58, 1.14, 0.06), (0, 0, 0.05), "door", rot=(0.06, -0.08, 0.2), decal=True)
    for _ in range(6):
        a.box((rnd.uniform(0.15, 0.45), 0.05, 0.03), (rnd.uniform(-0.6, 0.6), rnd.uniform(-0.8, 0.8), 0.02), "planks",
              rot=(0, 0, rnd.uniform(0, 3)))
    a.box((0.25, 0.05, 0.02), (0.45, 0.55, 0.02), "iron", rot=(0, 0, 0.7))
    return a.objs


def wicker_shield():
    """A giant's round wicker shield, bigger than a door, dropped and stamped on: rim, cross staves, a split side."""
    a = Asset(22)
    rnd = a.rnd
    R = 1.0
    a.lathe([(R, 0), (R * 0.75, 0.1), (R * 0.4, 0.16), (0.01, 0.18)], (0, 0, 0.04), "wicker", segs=24, smooth=True)
    a.lathe([(R - 0.04, 0), (R + 0.03, 0.02), (R + 0.03, 0.07), (R - 0.04, 0.08)], (0, 0, 0.0), "timber", segs=24,
            cap_top=False, cap_bottom=False)
    for t in (0.3, 0.3 + math.pi / 2):
        a.box((2 * R * 0.95, 0.07, 0.05), (0, 0, 0.17), "timber", rot=(0, 0, t))
    a.cyl(0.18, 0.08, (0, 0, 0.19), "iron", segs=12, r2=0.12)
    for _ in range(7):   # snapped staves sticking out of the split
        t = rnd.uniform(-0.5, 0.5)
        a.beam((R * 0.7 * math.cos(t), R * 0.7 * math.sin(t), 0.1),
               ((R + rnd.uniform(0.15, 0.45)) * math.cos(t), (R + rnd.uniform(0.15, 0.45)) * math.sin(t), rnd.uniform(0.05, 0.3)),
               0.035, "wicker")
    return a.objs


def giant_club():
    """A giant's club dropped in the street: a stripped tree bole, iron-banded and studded at the head."""
    a = Asset(23)
    L = 2.4
    a.lathe([(0.1, 0), (0.12, 0.6), (0.2, 1.6), (0.3, 2.2), (0.22, L)], (-L / 2, 0, 0.25), "bark", segs=12,
            rot=(0, math.pi / 2, 0), smooth=True)
    for x in (0.45, 0.85):
        a.cyl(0.31 if x > 0.6 else 0.26, 0.08, (x, 0, 0.25), "iron", segs=12, rot=(0, math.pi / 2, 0))
    for k in range(10):
        t = 2 * math.pi * k / 5 + (k // 5) * 0.6
        x = 0.62 + (k // 5) * 0.32
        a.cyl(0.04, 0.12, (x, 0.27 * math.cos(t), 0.25 + 0.27 * math.sin(t)), "iron", segs=6, r2=0.0, rot=(-t + math.pi / 2, 0, 0))
    return a.objs


def goods(seed=31):
    """A market stall's goods spilled in the street: baskets (one tipped over), cabbages, apples, a split sack, cloth."""
    a = Asset(seed)
    rnd = a.rnd
    basket = [(0.16, 0), (0.22, 0.05), (0.25, 0.22), (0.23, 0.22), (0.2, 0.05), (0.01, 0.04)]
    a.lathe(basket, (-0.35, 0.2, 0), "wicker", segs=14, cap_top=False, cap_bottom=True)
    a.lathe(basket, (0.25, -0.1, 0.25), "wicker", segs=14, rot=(math.pi / 2 - 0.2, 0, 1.2), cap_top=False)
    for _ in range(7):
        a.blob(0.09, (rnd.uniform(-0.6, 0.6), rnd.uniform(-0.55, 0.45), 0.08), "leaves", jitter=0.1, subdiv=2, lumps=0.2, smooth=True)
    for _ in range(14):
        x, y = rnd.uniform(-0.2, 0.9), rnd.uniform(-0.7, 0.3)
        a.blob(0.04, (x, y, 0.035), rnd.choice(("cloth_red", "cloth_red", "gold")), jitter=0.05, subdiv=1, smooth=True)
    a.blob(0.22, (-0.5, -0.4, 0.1), "canvas", scale=(1.2, 0.75, 0.5), jitter=0.1, smooth=True, flat_bottom=-0.08)
    a.box((0.8, 0.6, 0.01), (0.3, 0.45, 0.01), "cloth_red", rot=(0, 0, 0.4))
    return a.objs


def rug():
    """Three stolen rugs on top of each other, under the Baron's table."""
    a = Asset(33)
    for k, (w, d, t, mat) in enumerate(((3.6, 2.6, 0.2, "cloth_red"), (2.6, 3.2, -0.35, "banner"), (2.2, 1.6, 0.9, "cloth_red"))):
        z = 0.006 + 0.008 * k
        a.box((w, d, 0.006), (0, 0, z), mat, rot=(0, 0, t), decal=mat == "banner")
        for s in (-1, 1):   # gold border bands
            a.box((w, 0.08, 0.004), (s * (d / 2 - 0.06) * -math.sin(t), s * (d / 2 - 0.06) * math.cos(t), z + 0.004), "gold", rot=(0, 0, t))
    return a.objs


def kerb():
    """Stone edging of the sewer channel, 1.8 long."""
    a = Asset(34)
    a.box((1.8, 0.35, 0.16), (0, 0, 0.08), "stone")
    a.box((1.8, 0.04, 0.2), (0, 0.17, -0.02), "sewer_stone")
    return a.objs


def fence():
    a = Asset(8)
    for x in (-0.9, 0, 0.9):
        a.box((0.07, 0.07, 0.6), (x, 0, 0.3), "timber")
    for z in (0.2, 0.45):
        a.box((1.9, 0.04, 0.08), (0, 0, z), "planks")
    return a.objs


def throne_dais():
    """The Bandit Baron's seat: a three-step round stone dais with a gold trim, a tall stone throne in red velvet
    with gold finials and a crest, and coins spilling down the steps."""
    a = Asset(21)
    for r, h in ((1.35, 0.12), (1.05, 0.24), (0.75, 0.36)):
        a.cyl(r, h, (0, 0, 0), "stone", segs=24)
        a.cyl(r + 0.01, 0.03, (0, 0, h - 0.03), "gold", segs=24, caps=False)
    z = 0.36
    a.box((0.8, 0.7, 0.45), (0, 0.05, z + 0.225), "stone")
    a.box((0.72, 0.6, 0.08), (0, 0, z + 0.49), "cloth_red")
    a.box((0.9, 0.14, 1.5), (0, 0.38, z + 0.75), "stone")
    a.box((0.7, 0.04, 1.15), (0, 0.3, z + 0.95), "cloth_red")
    for x in (-1, 1):
        a.box((0.12, 0.7, 0.32), (x * 0.42, 0.05, z + 0.6), "stone")
        a.blob(0.08, (x * 0.42, -0.28, z + 0.8), "gold", jitter=0.05, subdiv=1)
        a.cyl(0.06, 0.3, (x * 0.4, 0.38, z + 1.5), "gold", segs=8, r2=0.01)
    a.prism(0.6, 0.15, 0.32, (0, 0.38, z + 1.5), "gold")
    rnd = a.rnd
    for _ in range(14):   # coins spilling down the front steps
        t = rnd.uniform(-1.0, 1.0) - math.pi / 2
        r = rnd.uniform(0.8, 1.3)
        a.cyl(0.05, 0.015, (r * math.cos(t), r * math.sin(t), 0.12 if r > 1.05 else 0.24), "gold", segs=8)
    return a.objs


def candelabra():
    """Tall iron candle stand: tripod foot, stem, a ring of five candles."""
    a = Asset(22)
    for i in range(3):
        t = 2 * math.pi * i / 3
        a.beam((0, 0, 0.2), (0.22 * math.cos(t), 0.22 * math.sin(t), 0.0), 0.035, "iron")
    a.cyl(0.025, 1.3, (0, 0, 0.15), "iron", segs=6)
    a.cyl(0.26, 0.03, (0, 0, 1.4), "iron", segs=12, r2=0.2)
    for i in range(5):
        t = 2 * math.pi * i / 5
        x, y = (0.2 * math.cos(t), 0.2 * math.sin(t)) if i else (0, 0)
        h = 0.18 if i else 0.26
        a.cyl(0.03, h, (x, y, 1.43), "plaster", segs=6)
        a.cyl(0.022, 0.07, (x, y, 1.43 + h), "flame", segs=5, r2=0.001)
    return a.objs


def hoard(seed=23):
    """A heap of loot: a mound of gold, an open chest brimming with it, goblets, a crown and loose coins."""
    a = Asset(seed)
    rnd = a.rnd
    a.blob(0.7, (0, 0, 0), "gold", scale=(1, 0.8, 0.5), jitter=0.06, subdiv=2, flat_bottom=0, smooth=True)
    a.box((0.6, 0.4, 0.32), (0.55, 0.4, 0.16), "planks")
    a.box((0.55, 0.35, 0.06), (0.55, 0.4, 0.33), "gold")
    a.box((0.6, 0.05, 0.4), (0.55, 0.64, 0.45), "planks", rot=(0.45, 0, 0))
    for x in (0.35, 0.75):
        a.box((0.05, 0.42, 0.34), (x, 0.4, 0.17), "iron")
    for _ in range(3):   # goblets on the slopes
        t = rnd.uniform(0, 2 * math.pi)
        a.lathe([(0.05, 0), (0.02, 0.03), (0.015, 0.11), (0.06, 0.2)], (0.62 * math.cos(t), 0.5 * math.sin(t), 0.02),
                "gold", segs=10, cap_top=False)
    a.cyl(0.11, 0.08, (-0.05, -0.05, 0.33), "gold", segs=8, caps=False)   # crown on top
    for i in range(5):
        t = 2 * math.pi * i / 5
        a.cyl(0.015, 0.06, (-0.05 + 0.11 * math.cos(t), -0.05 + 0.11 * math.sin(t), 0.41), "cloth_red", segs=4, r2=0.001)
    for _ in range(12):
        t = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0.75, 1.05)
        a.cyl(0.045, 0.012, (r * math.cos(t), r * 0.8 * math.sin(t), 0), "gold", segs=8)
    return a.objs


def wall_sconce():
    """Dungeon wall (as wall_segment) with a stone buttress and a burning sconce on each face."""
    a = Asset(24)
    a.box((1.8, 0.35, 1.6), (0, 0, 0.8), "bricks")
    a.box((1.86, 0.42, 0.1), (0, 0, 1.63), "stone")
    a.box((0.45, 0.5, 1.75), (0, 0, 0.875), "stone")
    for s in (-1, 1):
        a.box((0.05, 0.16, 0.05), (0, s * 0.31, 1.12), "iron")
        a.cyl(0.07, 0.1, (0, s * 0.4, 1.1), "iron", segs=8, r2=0.1)
        a.cyl(0.07, 0.22, (0, s * 0.4, 1.2), "flame", segs=6, r2=0.005)
    return a.objs


ASSETS = {
    "house_a": lambda: house(1, 3.0, 2.2, 2, "timber"),
    "house_b": lambda: house(2, 2.6, 2.0, 2, "mixed", roof="shingle", plaster="plaster_white", front=True),
    "house_c": lambda: house(3, 3.4, 2.4, 1, "stone", roof="thatch", annex=-1),
    "house_d": lambda: house(4, 2.4, 2.4, 2, "timber", front=True, plaster="plaster_rose"),
    "tavern": tavern, "ruin_a": lambda: house(5, 3.0, 2.4, 2, ruined=True), "ruin_b": lambda: house(6, 3.6, 2.2, 2, ruined=True),
    "ruin_c": lambda: house(7, 2.4, 2.2, 1, ruined=True),
    "barrel": barrel, "keg": keg, "crate": crate, "crates": crates, "sack": sack, "cart": cart,
    "broken_cart": lambda: cart(broken=True), "well": well, "stall": stall, "rubble": rubble, "grate": grate,
    "rock_a": lambda: rock(1), "rock_b": lambda: rock(2, 1.3, 1.4), "rock_c": lambda: rock(3, 0.7),
    "rock_d": lambda: rock(4, 1.6, 0.8), "rock_e": lambda: rock(5, 1.1, 1.8),
    "pine": pine, "pine_b": lambda: pine(2, 3.2), "oak": oak, "stump": stump, "log_large": trunk,
    "lumber": lumber, "wall": wall_segment, "wall_broken": lambda: wall_segment("broken"),
    "wall_door": lambda: wall_segment("door"), "pillar": pillar, "tent": tent, "bed": bedroll, "torch": brazier,
    "table_feast": table_round, "chair": chair, "throne": lambda: chair(2, throne=True), "chest": chest,
    "chest_gold": lambda: chest(2, gold=True), "coins": coins, "banner": banner, "bridge": bridge,
    "campfire_cold": campfire_cold, "stalagmite": stalagmite, "fence": fence,
    "pines": lambda: grove(pine, 5), "oaks": lambda: grove(oak, 4),
    "door_smashed": door_smashed, "wicker_shield": wicker_shield, "giant_club": giant_club, "goods": goods, "rug": rug,
    "kerb": kerb, "house_e": lambda: house(13, 2.2, 2.6, 3, "timber", front=True, roof="shingle", plaster="plaster_rose"),
    "house_f": lambda: house(14, 3.2, 2.2, 1, "stone", roof="thatch", annex=1, flowers=0.6),
    "throne_dais": throne_dais, "candelabra": candelabra, "hoard": hoard, "hoard_b": lambda: hoard(29),
    "wall_sconce": wall_sconce,
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
        big = name.startswith(("house", "tavern", "ruin"))   # buildings: 2k atlas keeps their texel density near the props'
        textures[name] = bake_objects(name, ASSETS[name](), OUT, size=2048 if big else 1024)
        tex_list.write_text("".join(f"{n} {t}\n" for n, t in sorted(textures.items())))
