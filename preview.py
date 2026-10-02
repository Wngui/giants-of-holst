"""Render every scene the way game.lua lays it out, to check props/figures before a trip to TTS.
  DUMP=/tmp/scenes.json .venv/bin/python test_lua.py
  blender -b --python preview.py -- /tmp/scenes.json <out_dir>
Axes follow TTS/Unity: world (x, y, z) -> Blender (x, z, y); OBJ meshes are x-mirrored on import like Unity does.
Figures are stand-in cylinders (red enemies, green heroes, grey others); built-in tileset pieces are brown boxes."""
import json, math, sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parent
dump, out = sys.argv[sys.argv.index("--") + 1:][:2]
data = json.load(open(dump))
Path(out).mkdir(parents=True, exist_ok=True)


def material(name, image=None, colour=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if colour:   # workbench TEXTURE mode only shows image colours, so paint a 1-pixel image
        img = bpy.data.images.new(name, 1, 1)
        img.pixels = [*colour, 1]
        image, colour = img, None
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    if image:
        n = m.node_tree.nodes.new("ShaderNodeTexImage")
        n.image = image if isinstance(image, bpy.types.Image) else bpy.data.images.load(str(image), check_existing=True)
        n.interpolation = "Closest"
        m.node_tree.links.new(n.outputs[0], bsdf.inputs[0])
    else:
        bsdf.inputs[0].default_value = (*colour, 1)
    return m


meshes = {}


def obj_mesh(path):
    if path not in meshes:
        v, vt, vn, faces = [], [], [], []
        for line in open(path):
            p = line.split()
            if p and p[0] == "v":
                x, y, z = map(float, p[1:4])
                v.append((-x, z, y))
            elif p and p[0] == "vt":
                vt.append(tuple(map(float, p[1:3])))
            elif p and p[0] == "vn":
                x, y, z = map(float, p[1:4])
                vn.append((-x, z, y))
            elif p and p[0] == "f":
                faces.append([tuple(int(i) - 1 if i else None for i in (c.split("/") + ["", ""])[:3]) for c in p[1:]])
        me = bpy.data.meshes.new(Path(path).stem)
        me.from_pydata(v, [], [[c[0] for c in f] for f in faces])   # x-mirror + y/z swap is a rotation: winding stays
        uv = me.uv_layers.new()
        k = 0
        for f in faces:
            for _, t, _ in f:
                uv.data[k].uv = vt[t] if t is not None else (0, 0)
                k += 1
        if vn:   # the OBJ's own normals (smooth or flat), as TTS shades it
            me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
            me.normals_split_custom_set([vn[n] for f in faces for _, _, n in f])
        meshes[path] = me
    return meshes[path]


def place(o, t, scale=True):
    o.location = (t["posX"], t["posZ"], t.get("posY", 1))
    o.rotation_euler = (0, 0, -math.radians(t.get("rotY", 0)))
    if scale:
        o.scale = (t.get("scaleX", 1), t.get("scaleZ", 1), t.get("scaleY", 1))


for sc in data["scenes"]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    meshes.clear()   # the reset above deletes them
    s = bpy.context.scene
    W, D, TOP, SQ = data["W"], data["D"], data["TOP"], data["SQ"]
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, TOP))
    table = bpy.context.object
    table.scale = (W, D, 1)
    table.data.materials.append(material("table", ROOT / "art/out" / f"table_{sc['key']}.jpg"))
    for o in sc["objects"]:
        t = o["t"]
        if o["name"] == "FogOfWar":
            continue
        if o["name"] == "Custom_Model":
            me = obj_mesh(ROOT / "props" / Path(o["mesh"]).name)
            ob = bpy.data.objects.new(o["nick"] or me.name, me)
            s.collection.objects.link(ob)
            if not me.materials:
                me.materials.append(material(Path(o["tex"]).name, ROOT / "props" / Path(o["tex"]).name))
            place(ob, t)
            ob.location.z = TOP
        elif o["name"].startswith("Tileset_"):
            bpy.ops.mesh.primitive_cube_add(size=0.6 * SQ)
            ob = bpy.context.object
            place(ob, t, scale=False)
            ob.location.z = TOP + 0.3 * SQ
            ob.data.materials.append(material("builtin", colour=(0.45, 0.28, 0.12)))
        else:   # figures and dice
            enemy = o["name"] == "hero" and False or any(w in (o["nick"] or "") for w in ("giant", "Giant", "Cyclops", "Grask", "rat", "thrall", "bruiser"))
            colour = (0.1, 0.8, 0.2) if o["name"] == "hero" else (0.85, 0.15, 0.1) if enemy else (0.6, 0.6, 0.6)
            h = 0.25 * SQ if o.get("dead") else (1.6 if "rpg_CYCLOP" == o["name"] else 0.9) * SQ
            r = (0.55 if o["name"] == "rpg_CYCLOP" else 0.3) * SQ
            if o["name"].startswith("Die"):
                h, r = 0.25 * SQ, 0.15 * SQ
            bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=(t["posX"], t["posZ"], TOP + h / 2))
            bpy.context.object.data.materials.append(material("fig" + str(colour), colour=colour))
    views = [("persp", (0, -D * 0.95, D * 0.85), (math.radians(47), 0, 0), False), ("top", (0, 0, 60), (0, 0, 0), True)]
    if any(o["nick"] == "GM table" for o in sc["objects"]):   # the GM's seat, east, looking west over the GM table
        views.append(("gm", (W / 2 + 17 * SQ, 0, TOP + 11 * SQ), (math.radians(52), 0, math.radians(90)), False))
    for name, loc, rot, ortho in views:
        cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        s.collection.objects.link(cam)
        cam.location, cam.rotation_euler = loc, rot
        if ortho:
            cam.data.type, cam.data.ortho_scale = "ORTHO", W * 1.02
        else:
            cam.data.lens = 30
        s.camera = cam
        s.render.engine = "BLENDER_WORKBENCH"
        s.display.shading.color_type = "TEXTURE"
        s.display.shading.light = "STUDIO"
        s.display.shading.show_shadows = True
        s.render.resolution_x, s.render.resolution_y = (1360, 800)
        s.render.filepath = str(Path(out) / f"{sc['key']}_{name}.png")
        bpy.ops.render.render(write_still=True)
print("previews written to", out)
