"""Blender: bake textured models into TTS-ready props: one .obj + one diffuse image each.
TTS custom models take a single texture, so each model is re-unwrapped into an atlas and its base colour baked in,
with ambient occlusion multiplied in (TTS lighting is flat) and alpha kept as a cutout (TTS honours PNG alpha).
Used by forge.py (our own models); can also bake glTF kits:
  blender -b --python bake.py -- <jobs.json> <out_dir>
jobs.json: {"name": [[gltf_path, x, y, z, rotY_deg, scale], ...], ...}  (several parts = merged prefab)"""
import json, math, sys
from pathlib import Path
import bpy


def import_gltf_parts(parts):
    objs = []
    for path, x, y, z, rot, scale in parts:
        bpy.ops.import_scene.gltf(filepath=path)
        for o in bpy.context.selected_objects:
            if o.parent is None:      # glTF is Y-up; Blender is Z-up: place in Blender space (x, -z, y)
                o.location = (x, -z, y)
                o.rotation_euler.z += math.radians(rot)
                o.scale = [s * scale for s in o.scale]
        objs += [o for o in bpy.context.selected_objects if o.type == "MESH"]
    return objs


def bake_objects(name, objs, out, size=1024, ao=0.55):
    """Join objs, give them an atlas UV, bake colour (x AO) + alpha into <out>/<name>.png|jpg and export <name>.obj."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.convert(target="MESH")              # apply modifiers, drop armatures
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    src = ob.data.uv_layers.active.name if ob.data.uv_layers else None   # the texture UVs stay as bake source
    atlas = ob.data.uv_layers.new(name="atlas")
    ob.data.uv_layers.active = atlas
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")

    def target(image):
        for mat in ob.data.materials:
            if not mat or not mat.use_nodes:
                continue
            nt = mat.node_tree
            t = nt.nodes.get("bake_target")
            if not t:
                if src:   # texture nodes read the original UVs explicitly; the bake writes through "atlas"
                    uvn = nt.nodes.new("ShaderNodeUVMap")
                    uvn.uv_map = src
                    for n in nt.nodes:
                        if n.type == "TEX_IMAGE" and not n.inputs["Vector"].is_linked:
                            nt.links.new(uvn.outputs[0], n.inputs["Vector"])
                t = nt.nodes.new("ShaderNodeTexImage")
                t.name = "bake_target"
            t.image = image
            nt.nodes.active = t

    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    s.render.bake.margin = 4
    s.render.bake.use_pass_direct = False
    s.render.bake.use_pass_indirect = False
    colour = bpy.data.images.new(name, size, size, alpha=True)
    target(colour)
    s.cycles.samples = 1
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, uv_layer="atlas")
    px = list(colour.pixels)
    if ao:
        occl = bpy.data.images.new(name + "_ao", size, size)
        target(occl)
        s.cycles.samples = 32
        bpy.ops.object.bake(type="AO", uv_layer="atlas")
        aox = list(occl.pixels)
        for c in range(3):
            px[c::4] = [v * (1 - ao + ao * a) for v, a in zip(px[c::4], aox[0::4])]
    # alpha: route each material's alpha (if any) into an emission and bake that
    has_alpha = False
    for mat in ob.data.materials:
        if not mat or not mat.use_nodes:
            continue
        nt = mat.node_tree
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        outn = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
        emit = nt.nodes.new("ShaderNodeEmission")
        if bsdf and bsdf.inputs["Alpha"].is_linked:
            nt.links.new(bsdf.inputs["Alpha"].links[0].from_socket, emit.inputs["Color"])
            has_alpha = True
        else:
            emit.inputs["Color"].default_value = (1, 1, 1, 1)
        if outn:
            nt.links.new(emit.outputs[0], outn.inputs["Surface"])
    if has_alpha:
        alpha = bpy.data.images.new(name + "_a", size, size)
        target(alpha)
        s.cycles.samples = 1
        bpy.ops.object.bake(type="EMIT", uv_layer="atlas")
        px[3::4] = [1.0 if a > 0.5 else 0.0 for a in list(alpha.pixels)[0::4]]   # TTS cutout: on or off
    else:
        px[3::4] = [1.0] * (size * size)
    colour.pixels = px
    ext = "png" if has_alpha else "jpg"                 # opaque props ship as small JPEGs
    colour.filepath_raw = str(out / f"{name}.{ext}")
    colour.file_format = "PNG" if has_alpha else "JPEG"
    colour.save()
    for uv in list(ob.data.uv_layers):
        if uv.name != "atlas":
            ob.data.uv_layers.remove(uv)
    # triangulated: TTS seemed to drop faces with more than 4 corners (coin tops, the tray's felt)
    bpy.ops.wm.obj_export(filepath=str(out / f"{name}.obj"), export_selected_objects=True, export_materials=False, export_triangulated_mesh=True,
                          forward_axis="NEGATIVE_Z", up_axis="Y", export_normals=True, export_uv=True)
    print("baked", name, len(ob.data.polygons), "faces", ext)
    return f"{name}.{ext}"


if __name__ == "__main__":
    jobs_path, out = sys.argv[sys.argv.index("--") + 1:][:2]
    for name, parts in json.load(open(jobs_path)).items():
        if not list(Path(out).glob(f"{name}.obj")):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bake_objects(name, import_gltf_parts(parts), out)
