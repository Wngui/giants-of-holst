"""CC0 kits -> TTS props: one .obj per prop (multi-piece prefabs merged) + one texture per kit.
Main kits: KayKit Medieval Hexagon + Dungeon Remastered (Kay Lousberg). Kenney Nature supplies the thrown log.
Each kit's scale is baked in so 1 model unit = 1 grid square; content.py scales are then plain multipliers.
Kits download to cache/ (gitignored); output lands in props/ (committed, served from GitHub).
Usage: python props.py"""
import io, math, subprocess, urllib.request, zipfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parent
CACHE, OUT = ROOT / "cache", ROOT / "props"
KAYKIT = "https://github.com/KayKit-Game-Assets/{}.git"
KITS = {  # name: (source, obj folder inside it, texture file, baked scale)
    "medieval": ("KayKit-Medieval-Hexagon-Pack-1.0", "addons/kaykit_medieval_hexagon_pack/Assets/obj",
                 "buildings/neutral/hexagons_medieval.png", 3.5),
    "dungeon": ("KayKit-Dungeon-Remastered-1.0", "addons/kaykit_dungeon_remastered/Assets/obj", "dungeon_texture.png", 0.45),
    "nature": ("https://kenney.nl/media/pages/assets/nature-kit/37ac38a37b-1677698939/kenney_nature-kit.zip",
               None, None, 1.0),
}
NATURE_COLOURS = {"woodBark": (96, 66, 44), "woodInner": (170, 140, 100)}   # Kenney's log, repainted to match


def cart():
    """Broken cart from medieval pieces: pallet bed, a crate and sacks on it, one wheel on, one lying off."""
    return [("medieval", "decoration/props/pallet", 0, 0.02, -0.15, 0, 1, 0),
            ("medieval", "decoration/props/pallet", 0, 0.02, 0.15, 0, 1, 0),
            ("medieval", "buildings/red/building_watermill_red_building_watermill_wheel_red", 0.17, 0.056, -0.05, 90, 0.2, 0),
            ("medieval", "buildings/red/building_watermill_red_building_watermill_wheel_red", 0.36, 0.01, 0.3, 30, 0.2, 90),
            ("medieval", "decoration/props/crate_long_A", 0, 0.1, 0.08, 20, 1, 0),
            ("medieval", "decoration/props/sack", -0.08, 0.1, -0.2, 50, 1, 0),
            ("medieval", "decoration/props/sack", -0.28, 0, -0.1, 10, 1, 0)]


# prefab name -> list of (kit, piece, x, y, z, rotY, scale, rotX) in the kit's native units
PREFABS = {"broken_cart": cart()}
M, D = "medieval", "dungeon"
FLATTEN = {"grate"}   # floor pieces whose detail sits in a pit below the floor: squash them onto the surface
SINGLES = {  # name -> (kit, piece path without .obj)
    "house_a": (M, "buildings/red/building_home_A_red"), "house_b": (M, "buildings/blue/building_home_B_blue"),
    "house_c": (M, "buildings/yellow/building_home_A_yellow"), "house_d": (M, "buildings/green/building_home_B_green"),
    "tavern": (M, "buildings/red/building_tavern_red"), "market": (M, "buildings/yellow/building_market_yellow"),
    "blacksmith": (M, "buildings/blue/building_blacksmith_blue"), "church": (M, "buildings/red/building_church_red"),
    "well": (M, "buildings/red/building_well_red"), "destroyed": (M, "buildings/neutral/building_destroyed"),
    "scaffolding": (M, "buildings/neutral/building_scaffolding"), "fence_wood": (M, "buildings/neutral/fence_wood_straight"),
    "fence_stone": (M, "buildings/neutral/fence_stone_straight"), "tent": (M, "decoration/props/tent"),
    "wheelbarrow": (M, "decoration/props/wheelbarrow"), "crate": (M, "decoration/props/crate_A_big"),
    "crate_long": (M, "decoration/props/crate_long_A"), "barrel": (M, "decoration/props/barrel"),
    "sack": (M, "decoration/props/sack"), "lumber": (M, "decoration/props/resource_lumber"),
    "stones": (M, "decoration/props/resource_stone"), "trees_large": (M, "decoration/nature/trees_B_large"),
    "trees_medium": (M, "decoration/nature/trees_A_medium"), "tree_a": (M, "decoration/nature/tree_single_A"),
    "tree_b": (M, "decoration/nature/tree_single_B"), "stump": (M, "decoration/nature/tree_single_A_cut"),
    "rock_a": (M, "decoration/nature/rock_single_A"), "rock_b": (M, "decoration/nature/rock_single_B"),
    "rock_c": (M, "decoration/nature/rock_single_C"), "rock_d": (M, "decoration/nature/rock_single_D"),
    "rock_e": (M, "decoration/nature/rock_single_E"), "hill": (M, "decoration/nature/hill_single_A"),
    "wall": (D, "wall"), "wall_broken": (D, "wall_broken"), "wall_arched": (D, "wall_arched"),
    "wall_door": (D, "wall_doorway_door"), "wall_half": (D, "wall_half"), "pillar": (D, "pillar"),
    "grate": (D, "floor_tile_big_grate"), "barrel_big": (D, "barrel_large"), "barrels": (D, "barrel_small_stack"),
    "keg": (D, "keg_decorated"), "chest_gold": (D, "chest_gold"), "chest": (D, "chest"), "coins": (D, "coin_stack_large"),
    "table_feast": (D, "table_medium_tablecloth_decorated_B"), "table_long": (D, "table_long_decorated_A"),
    "table_broken": (D, "table_long_broken"), "chair": (D, "chair"), "stool": (D, "stool"), "torch": (D, "torch_lit"),
    "rubble": (D, "rubble_large"), "rubble_half": (D, "rubble_half"), "banner": (D, "banner_patternA_red"),
    "bed": (D, "bed_floor"), "candles": (D, "candle_triple"), "crates": (D, "crates_stacked"), "box": (D, "box_large"),
    "trunk": (D, "trunk_large_A"), "shelves": (D, "shelves"),
    "log_large": ("nature", "log_large"),
}


def kit_dir(kit):
    src, sub, _, _ = KITS[kit]
    if src.startswith("http"):
        d = CACHE / kit
        if not d.exists():
            zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(src).read())).extractall(d)
        return next(d.glob("**/OBJ format"))
    d = CACHE / src
    if not d.exists():
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse", KAYKIT.format(src), str(d)], check=True)
        subprocess.run(["git", "-C", str(d), "sparse-checkout", "set", "--no-cone", f"/{sub}/**", "/LICENSE.txt"], check=True)
    return d / sub


def read_obj(path):
    """-> list of (material, face); face = [(pos, uv or None, normal)]."""
    v, vt, vn, faces, mat = [], [], [], [], None
    for line in path.read_text().splitlines():
        p = line.split()
        if not p:
            continue
        if p[0] == "v":
            v.append(tuple(map(float, p[1:4])))            # Kenney appends vertex colours; drop them
        elif p[0] == "vt":
            vt.append(tuple(map(float, p[1:3])))
        elif p[0] == "vn":
            vn.append(tuple(map(float, p[1:4])))
        elif p[0] == "usemtl":
            mat = p[1]
        elif p[0] == "f":
            face = []
            for c in p[1:]:
                a = (c.split("/") + ["", ""])[:3]
                face.append((v[int(a[0]) - 1], vt[int(a[1]) - 1] if a[1] else None, vn[int(a[2]) - 1] if a[2] else (0, 1, 0)))
            faces.append((mat, face))
    return faces


def read_mtl_colours(path):
    cols, cur = {}, None
    for line in path.read_text().splitlines():
        p = line.split()
        if p and p[0] == "newmtl":
            cur = p[1]
        elif p and p[0] == "Kd" and cur:
            cols[cur] = tuple(float(x) for x in p[1:4])
    return cols


def rot(p, ry, rx=0):
    y, z = p[1], p[2]
    if rx:
        c, s = math.cos(math.radians(rx)), math.sin(math.radians(rx))
        y, z = y * c - z * s, y * s + z * c
    c, s = math.cos(math.radians(ry)), math.sin(math.radians(ry))
    return (p[0] * c + z * s, y, -p[0] * s + z * c)


def write_obj(path, faces, uv_of):
    lines, n = ["# The Giants of Holst prop, from CC0 kits by KayKit (Kay Lousberg) and Kenney"], 0
    for mat, face in faces:
        for pos, uv, nrm in face:
            u, w = uv_of(mat, uv)
            lines += [f"v {pos[0]:.4f} {pos[1]:.4f} {pos[2]:.4f}", f"vt {u:.4f} {w:.4f}", f"vn {nrm[0]:.4f} {nrm[1]:.4f} {nrm[2]:.4f}"]
        lines.append("f " + " ".join(f"{i}/{i}/{i}" for i in range(n + 1, n + len(face) + 1)))
        n += len(face)
    path.write_text("\n".join(lines) + "\n")


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.obj"):
        old.unlink()
    jobs = dict(PREFABS)
    jobs.update({name: [(kit, piece, 0, 0, 0, 0, 1, 0)] for name, (kit, piece) in SINGLES.items()})
    for kit, (_, _, tex, _) in KITS.items():
        if tex:
            Image.open(kit_dir(kit) / tex).convert("RGB").save(OUT / f"tex_{kit}.png")
    # Kenney nature has flat material colours: bake them into a small palette texture
    cols = {}
    for parts in jobs.values():
        for kit, piece, *_ in parts:
            if kit == "nature":
                cols.update(read_mtl_colours(kit_dir("nature") / f"{piece}.mtl"))
    names = sorted(cols)
    pal = Image.new("RGB", (8 * len(names), 8))
    cell = {}
    for i, nm in enumerate(names):
        pal.paste(NATURE_COLOURS.get(nm) or tuple(int(c * 255) for c in cols[nm]), (i * 8, 0, i * 8 + 8, 8))
        cell[nm] = ((i + 0.5) / len(names), 0.5)
    pal.save(OUT / "tex_nature.png")

    textures = {}
    for name, parts in jobs.items():
        kits = {k for k, *_ in parts}
        assert len(kits) == 1, f"{name}: one texture per prop, got {kits}"
        kit = kits.pop()
        k = KITS[kit][3]
        faces = []
        for _, piece, x, y, z, ry, s, rx in parts:
            for mat, face in read_obj((kit_dir(kit) / f"{piece}.obj").resolve()):
                faces.append((mat, [(tuple(k * (a * s + b) for a, b in zip(rot(p, ry, rx), (x, y, z))), uv, rot(nr, ry, rx))
                                    for p, uv, nr in face]))
        if name in FLATTEN:
            lo = min(p[1] for _, f in faces for p, *_ in f)
            hi = max(p[1] for _, f in faces for p, *_ in f)
            faces = [(m, [((p[0], 0.05 * (p[1] - lo) / (hi - lo), p[2]), uv, nr) for p, uv, nr in f]) for m, f in faces]
        uv_of = (lambda mat, uv: cell[mat]) if kit == "nature" else (lambda mat, uv: uv or (0.5, 0.5))
        write_obj(OUT / f"{name}.obj", faces, uv_of)
        textures[name] = f"tex_{kit}.png"
    for stale in ("tex_town.png", "tex_survival.png", "tex_graveyard.png"):
        (OUT / stale).unlink(missing_ok=True)
    # thin slab collider for every prop: figures can stand among props instead of on top of a hull
    (OUT / "collider_flat.obj").write_text("\n".join(
        [f"v {x} {y} {z}" for x in (-0.5, 0.5) for y in (0, 0.02) for z in (-0.5, 0.5)] +
        ["f 1 3 7 5", "f 2 6 8 4", "f 1 5 6 2", "f 3 4 8 7", "f 1 2 4 3", "f 5 7 8 6"]) + "\n")
    (OUT / "textures.txt").write_text("".join(f"{n} {t}\n" for n, t in sorted(textures.items())))
    print(len(textures), "props written to", OUT)


if __name__ == "__main__":
    main()
