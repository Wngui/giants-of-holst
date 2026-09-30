"""Kenney CC0 kits -> TTS props: one .obj per prop (multi-piece prefabs merged) + one texture per kit.
Kits download to cache/ (gitignored); output lands in props/ (committed, served from GitHub).
TTS ignores .mtl files, so the nature kit's flat material colours are baked into a small palette texture.
Usage: python props.py"""
import io, math, random, urllib.request, zipfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parent
CACHE, OUT = ROOT / "cache", ROOT / "props"
KITS = {
    "town": "https://kenney.nl/media/pages/assets/fantasy-town-kit/efe948d309-1754222374/kenney_fantasy-town-kit_2.0.zip",
    "survival": "https://kenney.nl/media/pages/assets/survival-kit/4065a8185b-1712149243/kenney_survival-kit.zip",
    "graveyard": "https://kenney.nl/media/pages/assets/graveyard-kit/ba8d4b4517-1760691807/kenney_graveyard-kit_5.0.zip",
    "nature": "https://kenney.nl/media/pages/assets/nature-kit/37ac38a37b-1677698939/kenney_nature-kit.zip",
}
PALETTE_CELL = 8   # px per nature material colour
# the nature kit is bright and teal; repaint it in the muted dark-fantasy look of the rest of the game (sRGB)
NATURE_COLOURS = {"leafsDark": (46, 78, 44), "leafsGreen": (56, 90, 50), "woodBarkDark": (74, 52, 36),
                  "woodBark": (96, 66, 44), "woodInner": (170, 140, 100), "grass": (72, 80, 62),
                  "dirt": (98, 92, 86), "stone": (120, 120, 118), "_defaultMat": (100, 100, 100)}


def ruin(w, d, seed, wood=False):
    """Roofless ruined house, w x d tiles: walls round the edge, some windows, a door, broken bits, rubble inside."""
    rnd = random.Random(seed)
    m = "wall-wood" if wood else "wall"
    parts, edges = [], []
    for i in range(w):
        edges += [(i, 0, 90), (i, d - 1, -90)]           # south (-z) and north (+z) walls
    for j in range(d):
        edges += [(0, j, 180), (w - 1, j, 0)]            # west and east walls
    door = rnd.randrange(len(edges))
    for n, (i, j, rot) in enumerate(edges):
        piece = (f"{m}-door" if n == door else
                 rnd.choice([f"{m}-broken", f"{m}-broken", f"{m}-window-shutters", m, m]))
        x, z = i - (w - 1) / 2, j - (d - 1) / 2
        parts.append(("town", piece, x, 0, z, rot))
        if piece == m and rnd.random() < 0.35:            # a few walls keep a second storey
            parts.append(("town", f"{m}-broken", x, 1, z, rot))
    for _ in range(w * d // 2):
        parts.append(("town", "planks-half", rnd.uniform(-w / 3, w / 3), 0, rnd.uniform(-d / 3, d / 3), rnd.choice([0, 90, 30])))
    return parts


# prefab name -> list of (kit, piece, x, y, z, rotY degrees); single pieces use their own name
PREFABS = {
    "ruin_2x2": ruin(2, 2, 1), "ruin_3x2": ruin(3, 2, 2), "ruin_2x3": ruin(2, 3, 3, wood=True),
    "ruin_3x3": ruin(3, 3, 4, wood=True), "ruin_4x2": ruin(4, 2, 5),
    "broken_cart": [("town", "cart", 0, 0, 0, 0), ("town", "wheel", 0.55, 0, 0.75, 70),
                    ("town", "planks-half", -0.6, 0, -0.5, 25)],
}
SINGLES = {  # name -> (kit, piece)
    "cart": ("town", "cart"), "fence": ("town", "fence"), "fence_broken": ("town", "fence-broken"),
    "rock_town": ("town", "rock-large"), "stall": ("town", "stall-red"), "lantern": ("town", "lantern"),
    "tent": ("survival", "tent-canvas"), "campfire": ("survival", "campfire-pit"), "bedroll": ("survival", "bedroll"),
    "crate": ("survival", "box-large"), "barrel_s": ("survival", "barrel"), "signpost": ("survival", "signpost"),
    "stone_wall": ("graveyard", "stone-wall"), "stone_wall_broken": ("graveyard", "stone-wall-damaged"),
    "stone_wall_curve": ("graveyard", "stone-wall-curve"), "debris": ("graveyard", "debris"),
    "debris_wood": ("graveyard", "debris-wood"), "rubble": ("graveyard", "rocks"), "skeleton": ("graveyard", "character-skeleton"),
    "pine": ("nature", "tree_pineTallA"), "pine_b": ("nature", "tree_pineDefaultA"), "oak": ("nature", "tree_oak_dark"),
    "log_large": ("nature", "log_large"), "stump": ("nature", "stump_old"), "bush": ("nature", "plant_bushLarge"),
    "rock_big": ("nature", "rock_largeA"), "rock_tall": ("nature", "rock_tallA"), "rock_small": ("nature", "rock_smallA"),
    "cliff": ("nature", "cliff_block_rock"), "cliff_half": ("nature", "cliff_half_rock"),
    "cliff_corner": ("nature", "cliff_corner_rock"), "cave_mouth": ("nature", "cliff_cave_rock"),
    "campfire_cold": ("nature", "campfire_stones"),
}


def kit_dir(kit):
    d = CACHE / kit
    if not d.exists():
        zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(KITS[kit]).read())).extractall(d)
    return next(d.glob("**/OBJ format"))


def read_obj(path):
    """-> list of faces; each face = [(pos, uv or None, normal)] plus material name."""
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


def rot_y(p, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return (p[0] * c + p[2] * s, p[1], -p[0] * s + p[2] * c)


def write_obj(path, faces, uv_of):
    lines, n = ["# The Giants of Holst prop, from Kenney CC0 kits (www.kenney.nl)"], 0
    for mat, face in faces:
        for pos, uv, nrm in face:
            u, w = uv_of(mat, uv)
            lines += [f"v {pos[0]:.4f} {pos[1]:.4f} {pos[2]:.4f}", f"vt {u:.4f} {w:.4f}", f"vn {nrm[0]:.4f} {nrm[1]:.4f} {nrm[2]:.4f}"]
        lines.append("f " + " ".join(f"{i}/{i}/{i}" for i in range(n + 1, n + len(face) + 1)))
        n += len(face)
    path.write_text("\n".join(lines) + "\n")


def main():
    OUT.mkdir(exist_ok=True)
    jobs = {name: parts for name, parts in PREFABS.items()}
    jobs.update({name: [(kit, piece, 0, 0, 0, 0)] for name, (kit, piece) in SINGLES.items()})
    # nature palette: every material colour used by any nature piece, one cell each
    nature_cols = {}
    for parts in jobs.values():
        for kit, piece, *_ in parts:
            if kit == "nature":
                nature_cols.update(read_mtl_colours(kit_dir("nature") / f"{piece}.mtl"))
    names = sorted(nature_cols)
    side = math.ceil(math.sqrt(len(names)))
    pal = Image.new("RGB", (side * PALETTE_CELL, side * PALETTE_CELL))
    cell = {}
    for i, nm in enumerate(names):
        cx, cy = i % side, i // side
        pal.paste(NATURE_COLOURS.get(nm) or tuple(int(c * 255) for c in nature_cols[nm]),
                  (cx * PALETTE_CELL, cy * PALETTE_CELL, (cx + 1) * PALETTE_CELL, (cy + 1) * PALETTE_CELL))
        cell[nm] = ((cx + 0.5) / side, 1 - (cy + 0.5) / side)
    pal.save(OUT / "tex_nature.png")
    for kit in ("town", "survival", "graveyard"):
        Image.open(kit_dir(kit) / "Textures" / "colormap.png").convert("RGB").save(OUT / f"tex_{kit}.png")

    textures = {}
    for name, parts in jobs.items():
        kits = {k for k, *_ in parts}
        assert len(kits) == 1, f"{name}: one texture per prop, got {kits}"
        kit = kits.pop()
        faces = []
        for _, piece, x, y, z, rot in parts:
            for mat, face in read_obj(kit_dir(kit) / f"{piece}.obj"):
                faces.append((mat, [(tuple(a + b for a, b in zip(rot_y(p, rot), (x, y, z))), uv, rot_y(nr, rot))
                                    for p, uv, nr in face]))
        uv_of = (lambda mat, uv: cell[mat]) if kit == "nature" else (lambda mat, uv: uv)
        write_obj(OUT / f"{name}.obj", faces, uv_of)
        textures[name] = f"tex_{kit}.png"
    # thin slab collider for every prop: figures can stand in ruins/among trees instead of on top of a hull
    (OUT / "collider_flat.obj").write_text("\n".join(
        [f"v {x} {y} {z}" for x in (-0.5, 0.5) for y in (0, 0.02) for z in (-0.5, 0.5)] +
        ["f 1 3 7 5", "f 2 6 8 4", "f 1 5 6 2", "f 3 4 8 7", "f 1 2 4 3", "f 5 7 8 6"]) + "\n")
    (OUT / "textures.txt").write_text("".join(f"{n} {t}\n" for n, t in sorted(textures.items())))
    print(len(textures), "props written to", OUT)


if __name__ == "__main__":
    main()
