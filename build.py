"""Build the TTS save.  python build.py <asset base url>
e.g. https://raw.githubusercontent.com/<user>/<repo>/<commit>/  -> writes art/out/*, Holst.json, GM_GUIDE.md"""
import hashlib, json, subprocess, sys, textwrap
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont
from content import HEROES, NPCS, SCENES, RULES, BATTLE_MUSIC, ITEMS, SKIES

ROOT = Path(__file__).parent
CONTROLLER = "901d00"       # GUID of the hidden object that runs game.lua
RAW, OUT = ROOT / "art" / "raw", ROOT / "art" / "out"
COLS, ROWS = 22, 22 / 1.5   # grid squares across/down the 3:2 scene art
TABLE_PX = (3400, 2000)     # custom rectangle table images are 17:10
ART_FRAC = 0.64             # share of the table width the scene art covers; the wooden border holds the player kits
# measured-at-load layout knobs, passed to game.lua (fractions of the table's measured width/depth)
LAYOUT = {"cols": COLS, "rows": ROWS, "art_w": ART_FRAC, "surface": 1.0,
          "kit_x": 0.41, "reveal": 7, "sheet_z": 0.30, "row_z": 0.12, "sheet_w": 0.16, "tile_unit": 2.0,
          "gm_hand": 12.5}   # GM hand zone, squares past the table's east edge (beyond the GM table)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif{}.ttf"
RGB = {"Red": (150, 35, 35), "Blue": (35, 70, 150), "Green": (35, 115, 55), "Purple": (100, 45, 135)}


def font(size, bold=False):
    return ImageFont.truetype(FONT.format("-Bold" if bold else ""), size)


def guid(*key):
    return hashlib.md5("/".join(map(str, key)).encode()).hexdigest()[:6]


def wrap(draw, xy, text, size, width, fill=(30, 20, 10), bold=False, spacing=6):
    f = font(size, bold)
    lines = [l for para in text.split("\n") for l in (textwrap.wrap(para, width) or [""])]
    draw.multiline_text(xy, "\n".join(lines), font=f, fill=fill, spacing=spacing)


# ---------------------------------------------------------------- images
def make_card(hero, i):
    title, text, _ = hero["cards"][i]
    col = RGB[hero["color"]]
    im = Image.new("RGB", (500, 700), col)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((12, 12, 488, 688), 18, fill=(236, 222, 190))
    d.text((250, 48), title, font=font(34, True), fill=col, anchor="mm")
    art = Image.open(RAW / f"card_{hero['key']}_{i}.png").convert("RGB").resize((460, 383))
    im.paste(art, (20, 82))
    d.rectangle((20, 82, 480, 465), outline=col, width=3)
    wrap(d, (32, 482), text, 24, 34)
    d.text((250, 668), "once per rest", font=font(18), fill=(110, 90, 60), anchor="mm")
    return im


def make_sheet(hero):
    """Page 1 (front): the character. Page 2 (tile back, flip it): the D20 LITE rules."""
    im = Image.new("RGB", (1500, 1000), (236, 222, 190))
    d = ImageDraw.Draw(im)
    col = RGB[hero["color"]]
    ink = (30, 20, 10)
    d.rectangle((0, 0, 1499, 999), outline=col, width=16)
    im.paste(Image.open(RAW / f"portrait_{hero['key']}.png").convert("RGB").resize((430, 430)), (36, 36))
    d.rectangle((36, 36, 466, 466), outline=col, width=4)
    d.text((500, 40), hero["name"], font=font(54, True), fill=col)
    wrap(d, (500, 112), "\u201c" + hero["blurb"] + "\u201d", 27, 58, fill=(90, 70, 50))
    boxes = [("HP", str(hero["hp"]), 190), ("DEFENSE", str(hero["defense"]), 190)] + \
            [(k.upper(), f"{v:+d}", 150) for k, v in hero["stats"].items()]
    x = 500
    for label, val, w in boxes:
        d.rounded_rectangle((x, 180, x + w, 300), 14, outline=col, width=5)
        d.text((x + w // 2, 205), label, font=font(22, True), fill=col, anchor="mm")
        d.text((x + w // 2, 262), val, font=font(50, True), fill=ink, anchor="mm")
        x += w + 18
    d.text((500, 330), "ATTACKS", font=font(26, True), fill=col)
    for n, (name, bonus, dmg, note) in enumerate(hero["attacks"]):
        d.text((500, 368 + n * 40), f"{name}: {bonus:+d} to hit, {dmg} damage  ({note})", font=font(24), fill=ink)
    y = 500
    for title, body in (("TRAITS", "\n".join("\u2022 " + t for t in hero["traits"])), ("BACKGROUND", hero["background"]),
                        ("GEAR", hero["gear"])):
        d.text((40, y), title, font=font(28, True), fill=col)
        lines = [l for para in body.split("\n") for l in textwrap.wrap(para, 92, subsequent_indent="  " if title == "TRAITS" else "")]
        d.multiline_text((40, y + 40), "\n".join(lines), font=font(27), fill=ink, spacing=9)
        y += 40 + len(lines) * 37 + 30
    d.text((750, 968), "Flip the sheet for the D20 LITE rules", font=font(20), fill=(110, 90, 60), anchor="mm")
    return im


def rules_page(col):
    """The sheet's back: D20 LITE rules laid out as headed boxes, plus the difficulty badges."""
    im = Image.new("RGB", (1500, 1000), (236, 222, 190))
    d = ImageDraw.Draw(im)
    ink = (30, 20, 10)
    d.rectangle((0, 0, 1499, 999), outline=col, width=16)
    d.text((750, 70), "D20 LITE", font=font(72, True), fill=col, anchor="mm")
    d.text((750, 128), "how to play", font=font(28), fill=(110, 90, 60), anchor="mm")
    sections = []
    for line in RULES.splitlines()[1:]:
        if line.startswith(" ") and sections:
            sections[-1][1] += " " + line.strip()
        else:
            head, _, body = line.partition(":")
            sections.append([head.strip(), body.strip()])
    for n, (head, body) in enumerate(sections):
        x, y = (60 if n % 2 == 0 else 770), 180 + (n // 2) * 245
        d.rounded_rectangle((x, y, x + 670, y + 225), 16, outline=col, width=3, fill=(244, 236, 214))
        d.text((x + 24, y + 18), head.upper(), font=font(28, True), fill=col)
        wrap(d, (x + 24, y + 62), body[:1].upper() + body[1:], 24, 52, fill=ink, spacing=7)
    x0 = 770 if len(sections) % 2 else 60   # free slot: the difficulty badges
    y0 = 180 + (len(sections) // 2) * 245
    d.text((x0 + 24, y0 + 18), "DIFFICULTY", font=font(28, True), fill=col)
    for n, (label, dc) in enumerate((("Easy", 10), ("Hard", 14), ("Heroic", 18))):
        cx = x0 + 110 + n * 220
        d.ellipse((cx - 70, y0 + 66, cx + 70, y0 + 206), outline=col, width=6, fill=(244, 236, 214))
        d.text((cx, y0 + 125), str(dc), font=font(56, True), fill=ink, anchor="mm")
        d.text((cx, y0 + 178), label, font=font(22, True), fill=col, anchor="mm")
    return im


GOLD = (120, 88, 36)


def make_item_card(i):
    title, text, _, _ = ITEMS[i]
    im = Image.new("RGB", (500, 700), GOLD)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((12, 12, 488, 688), 18, fill=(236, 222, 190))
    d.text((250, 48), title, font=font(30 if len(title) > 18 else 34, True), fill=GOLD, anchor="mm")
    im.paste(Image.open(RAW / f"item_{i}.png").convert("RGB").resize((460, 383)), (20, 82))
    d.rectangle((20, 82, 480, 465), outline=GOLD, width=3)
    wrap(d, (32, 482), text, 24, 34)
    d.text((250, 668), "magic item", font=font(18), fill=(110, 90, 60), anchor="mm")
    return im


def text_panel(title, body, size=(1000, 1500), fs=30):
    """Parchment panel with a heading and wrapped text (GM screen inside)."""
    im = Image.new("RGB", size, (236, 222, 190))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, size[0] - 1, size[1] - 1), outline=GOLD, width=14)
    d.text((size[0] // 2, 70), title, font=font(52, True), fill=GOLD, anchor="mm")
    wrap(d, (50, 130), body, fs, int((size[0] - 100) / (fs * 0.55)), spacing=10)
    return im


def screen_panels():
    rules = RULES.split("\n", 1)[1]
    foes = "\n".join(f"{t['name']}: HP {t['hp']}, Def {t['defense']}. " +
                     "; ".join(f"{a} {'+%d' % b if b is not None else ''} {c or ''}".replace("  ", " ") for a, b, c, _ in t["attacks"])
                     for t in NPCS.values() if t["attacks"])
    items = "\n".join(f"{n}{' (x%d)' % k if k > 1 else ''}: {x}" for n, x, _, k in ITEMS)
    return [("How to play", rules, 36), ("Foes", foes, 33), ("Magic items", items, 36)]


def sky(key):
    """Scene backdrop as a 360 panorama: left/right edges made to wrap, top and bottom faded so the poles don't pinch."""
    im = Image.open(upscaled(f"sky_{key}")).convert("RGB")
    w, h = im.size
    shifted = ImageChops.offset(im, w // 2, 0)
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    edge = int(w * 0.12)
    for x in range(edge):
        v = int(255 * (1 - x / edge) ** 1.5)
        d.line((x, 0, x, h), fill=v)
        d.line((w - 1 - x, 0, w - 1 - x, h), fill=v)
    im = Image.composite(shifted, im, mask)
    for band, rows in (("top", range(int(h * 0.14))), ("bottom", range(h - 1, h - 1 - int(h * 0.16), -1))):
        y0 = rows[0]
        ref = im.crop((0, y0, w, y0 + 1) if band == "top" else (0, y0 - 1, w, y0)).resize((1, 1)).getpixel((0, 0))
        for i, y in enumerate(rows):
            k = 1 - i / len(rows)
            row = im.crop((0, y, w, y + 1))
            im.paste(Image.blend(row, Image.new("RGB", (w, 1), ref), k ** 1.4), (0, y))
    return im


def gm_pdf(text, out):
    """GM guide as a book: plain text pages (headings bold), for TTS's in-game PDF reader."""
    W, H, M = 1240, 1754, 90
    pages, y, page = [], H, None
    for raw in text.splitlines():
        if raw.startswith("```"):
            continue
        head = raw.startswith("#")
        line = raw.lstrip("#").strip().replace("**", "").replace("*", "").replace("`", "")
        fs = 38 if raw.startswith("# ") else 32 if head else 24
        for part in textwrap.wrap(line, int((W - 2 * M) / (fs * 0.52)), subsequent_indent="   ") or [""]:
            if y + fs * 1.5 > H - M:
                page = Image.new("RGB", (W, H), (244, 236, 214))
                pages.append(page)
                y = M
            ImageDraw.Draw(page).text((M, y), part, font=font(fs, head), fill=(40, 28, 16))
            y += int(fs * (1.9 if head else 1.45))
    pages[0].save(out, save_all=True, append_images=pages[1:], resolution=150)
    return len(pages)


def build_images():
    OUT.mkdir(parents=True, exist_ok=True)
    for h in HEROES:
        sheet = Image.new("RGB", (1500, 1400))
        for i in range(6):
            sheet.paste(make_card(h, i), ((i % 3) * 500, (i // 3) * 700))
        sheet.save(OUT / f"cards_{h['key']}.jpg", quality=90)
        make_sheet(h).save(OUT / f"sheet_{h['key']}.jpg", quality=90)
        rules_page(RGB[h["color"]]).save(OUT / f"rules_{h['key']}.jpg", quality=90)
        Image.open(RAW / f"portrait_{h['key']}.png").convert("RGB").resize((256, 256)).save(OUT / f"portrait_{h['key']}.jpg")
    Image.open(RAW / "card_back.png").convert("RGB").resize((500, 700)).save(OUT / "card_back.jpg", quality=90)
    items = Image.new("RGB", (2000, 1400))
    for i in range(len(ITEMS)):
        items.paste(make_item_card(i), ((i % 4) * 500, (i // 4) * 700))
    items.save(OUT / "items.jpg", quality=90)
    Image.open(RAW / "portrait_gm.png").convert("RGB").resize((256, 256)).save(OUT / "portrait_gm.jpg", quality=90)
    art = Image.open(upscaled("screen_art")).convert("RGB")
    pw = art.width // 3
    for i, (title, body, fs) in enumerate(screen_panels()):
        art.crop((i * pw, 0, (i + 1) * pw, art.height)).resize((1000, 1500), Image.LANCZOS).save(OUT / f"screen_front_{i}.jpg", quality=88)
        text_panel(title, body, fs=fs).save(OUT / f"screen_back_{i}.jpg", quality=90)
    for key in SKIES:
        sky(key).save(OUT / f"sky_{key}.jpg", quality=85)
    wood = Image.open(RAW / "table_wood.png").convert("RGB").resize(TABLE_PX)
    aw = int(TABLE_PX[0] * ART_FRAC)
    ah = int(aw / 1.5)
    for s in SCENES:
        src = "map_title" if s["key"] == "title" else f"ground_{s['key']}"
        im = Image.open(upscaled(src)).convert("RGB")
        if s["key"] == "title":
            d = ImageDraw.Draw(im)
            d.text((768, 470), s["title"], font=font(110, True), fill=(250, 235, 200), anchor="mm",
                   stroke_width=6, stroke_fill=(40, 20, 10))
        table = wood.copy()
        x0, y0 = (TABLE_PX[0] - aw) // 2, (TABLE_PX[1] - ah) // 2
        ImageDraw.Draw(table).rectangle((x0 - 14, y0 - 14, x0 + aw + 13, y0 + ah + 13), fill=(150, 115, 50))
        table.paste(im.resize((aw, ah), Image.LANCZOS), (x0, y0))   # downscale from the 2x upscale: stays sharp
        table.save(OUT / f"table_{s['key']}.jpg", quality=85)


def upscaled(name):
    """2x waifu2x copy of art/raw/<name>.png (cached in art/raw/up/), so the table art is sharp, not stretched."""
    out = RAW / "up" / f"{name}.png"
    if not out.exists():
        out.parent.mkdir(exist_ok=True)
        nunif = ROOT.parent.parent / "tools" / "nunif"
        subprocess.run([str(nunif / ".venv/bin/python"), "-m", "waifu2x.cli", "-m", "noise_scale2x", "-n", "1",
                        "--style", "art", "-i", str(RAW / f"{name}.png"), "-o", str(out.parent)], cwd=nunif, check=True)
    return out


# ---------------------------------------------------------------- TTS objects
def tf(x=0.0, y=1.0, z=0.0, ry=0.0, s=1.0, rz=0.0):
    return {"posX": x, "posY": y, "posZ": z, "rotX": 0.0, "rotY": ry, "rotZ": rz, "scaleX": s, "scaleY": s, "scaleZ": s}


def obj(name, transform, **kw):
    o = {"Name": name, "Transform": transform, "Nickname": "", "Description": "", "GMNotes": "",
         "ColorDiffuse": {"r": 1.0, "g": 1.0, "b": 1.0}, "Locked": False, "Grid": False, "Snap": True,
         "Autoraise": True, "Sticky": True, "Tooltip": True, "HideWhenFaceDown": False, "Hands": False,
         "LuaScript": "", "LuaScriptState": "", "XmlUI": "", "Tags": []}
    o.update(kw)
    return o


def mesh(base, name, **kw):
    """CustomMesh block for one of our baked props."""
    return {"MeshURL": f"{base}props/{name}.obj", "DiffuseURL": f"{base}props/{TEXTURES[name]}", "NormalURL": "",
            "ColliderURL": "", "Convex": True, "MaterialIndex": 1, "TypeIndex": 0, "CastShadows": True} | kw


def tile(url, transform, **kw):
    transform["scaleY"] = 1.0   # keep tiles thin; scale only stretches X/Z
    return obj("Custom_Tile", transform, CustomImage={
        "ImageURL": url, "ImageSecondaryURL": "", "ImageScalar": 1.0, "WidthScale": 0.0,
        "CustomTile": {"Type": 0, "Thickness": 0.2, "Stackable": False, "Stretch": False}}, **kw)


# Everything on the table is positioned by grid square; game.lua measures the table at load and turns
# "grid" into a world transform (TTS table sizes aren't documented, guessing them made things fall off).
# per RPG kit model: health bar height above the base (object-UI units), read off screenshots (thralls were right)
UI_HEIGHT = {"rpg_CYCLOP": 540, "rpg_GHOUL": 230, "rpg_KOBOLD": 230, "rpg_RAT": 130, "rpg_WOLF": 150}
BLACK, GOLD_BASE = [0.05, 0.05, 0.05], [0.85, 0.65, 0.15]


def npc(key, x, z, n, scene, hp=None):
    t = NPCS[key]
    hp = hp or t["hp"]
    attacks = [dict(name=a, hit=b, dmg=c, note=d) for a, b, c, d in t["attacks"]]
    ry = (270.0 if x > 0 else 90.0) + (180.0 if t.get("flip") else 0.0)   # flip: model faces backwards
    o = obj(t["fig"], tf(ry=ry), GUID=guid(scene, key, n), Nickname=t["name"], Tags=["scene"], GMNotes=t["notes"],
            grid={"x": x, "z": z, "k": "fig", "s": [t.get("scale", 1)] * 3})
    # an RPG figure's tint colours its base: black, gold for notable NPCs, or the NPC's own base colour
    o["ColorDiffuse"] = dict(zip("rgb", t.get("base") or (GOLD_BASE if t.get("notable") else BLACK)))
    if t.get("dead"):
        o["RPGdead"] = True
    if attacks or not t.get("dead"):   # corpses and carcasses are props, everyone else gets a healthbar
        o["LuaScript"] = (ROOT / "npc.lua").read_text()
        o["LuaScriptState"] = json.dumps({"name": t["name"], "hp": t.get("start_hp", hp), "max": hp,
                                          "def": t["defense"], "down": bool(t.get("dead")), "attacks": attacks,
                                          "ui": UI_HEIGHT.get(t["fig"], 330), "ctl": CONTROLLER})
    return o


# small props are loose physics objects (knock them over, push them about); everything else is scenery, spawned
# locked in place with its own mesh as collider so figures and dice stop at walls instead of passing through
LOOSE = ("barrel", "keg", "crate", "crates", "sack", "chest", "chest_gold", "coins", "chair", "goods", "door_smashed",
         "wicker_shield", "giant_club", "lumber", "torch", "candelabra", "hoard", "hoard_b")


def prop(spec, n, scene, base, textures):
    name, x, z, *rest = spec
    rot, scale = (list(rest) + [0, 1][len(rest):])[:2]      # optional rot, scale
    s = list(scale) if isinstance(scale, (list, tuple)) else [scale] * 3
    loose = name in LOOSE
    common = dict(GUID=guid(scene, "prop", n), Tags=["scene"], Tooltip=False, Locked=not loose)
    if name.startswith("Tileset_"):                       # built-in TTS tileset piece
        return obj(name, tf(ry=rot), grid={"x": x, "z": z, "k": "builtin", "s": s}, **common)
    return obj("Custom_Model", tf(ry=rot), grid={"x": x, "z": z, "k": "model", "s": s, "lift": 0.3 if loose else 0},
               Nickname="", **common, CustomMesh=mesh(base, name, Convex=loose))   # non-convex mesh: locked only


FOG = False   # hidden enemies revealed by walking near: off for now, the GM toggles visibility by hand


def scene_data(s, base, textures):
    spawns = []
    for n, spec in enumerate(s.get("props", [])):
        spawns.append(prop(spec, n, s["key"], base, textures))
    for n, spec in enumerate(s["npcs"]):
        o = npc(*spec[:3], n, s["key"], *spec[3:])
        if FOG and s["fog"] and o["LuaScript"]:   # living NPCs stay invisible to players until a hero comes near
            o["Tags"] = o["Tags"] + ["hidden"]
        if spec[0] in s.get("stealth", ()):   # ...or until the GM reveals them by hand
            o["Tags"] = o["Tags"] + ["manual"]
        spawns.append(o)
    if s["key"] == "den":   # Baron's Bones dice on the gambling table
        spawns += [obj("Die_6_Rounded", tf(ry=30.0 * i), GUID=guid("den", "die", i), Tags=["scene"], Nickname="Baron's Bones",
                       ColorDiffuse={"r": 0.06, "g": 0.06, "b": 0.06},     # black, white pips: readable from across the table
                       grid={"x": -0.45 + 0.45 * i, "z": 0, "k": "fig", "s": [1.3, 1.3, 1.3], "lift": 4}) for i in range(3)]
    _, rgb, bright = SKIES[s["key"]]
    return dict(title=s["title"], spawns=spawns, heroes=[[x, z] for x, z in s["heroes"]],
                sky=f"{base}art/out/sky_{s['key']}.jpg", light=[*rgb, bright],
                table=f"{base}art/out/table_{s['key']}.jpg", music=dict(url=f"{base}music/{s['music']}", title=s["title"]))


def hero_objects(h, n, base):
    """Figure plus sheet/counter/d20/deck; game.lua puts the kit in the player's corner of the table ("role")."""
    c = h["color"]
    face = f"{base}art/out/cards_{h['key']}.jpg"
    cdeck = {"FaceURL": face, "BackURL": f"{base}art/out/card_back.jpg", "NumWidth": 3, "NumHeight": 2,
             "BackIsHidden": True, "UniqueBack": False, "Type": 0}
    ids = [(n + 1) * 100 + i for i in range(6)]
    cards = [obj("Card", tf(), CardID=cid, Hands=True, Nickname=title, Description=text, Tags=["kit", f"card_{c}"],
                 CustomDeck={str(n + 1): cdeck}, GUID=guid(c, "card", i))
             for i, (cid, (title, text, _)) in enumerate(zip(ids, h["cards"]))]
    colour = dict(zip("rgb", [v / 255 for v in RGB[c]]))
    sheet = tile(f"{base}art/out/sheet_{h['key']}.jpg", tf(), GUID=guid(c, "sheet"), Nickname=h["name"], Locked=False,
                 Tags=["kit", f"sheet_{c}"], grid={"role": "sheet", "color": c})
    sheet["CustomImage"]["ImageSecondaryURL"] = f"{base}art/out/rules_{h['key']}.jpg"   # flip: page 2
    return [
        obj(h["fig"], tf(), GUID=guid(c, "fig"), Nickname=h["name"], Tags=["kit", f"fig_{c}"],
            ColorDiffuse=dict(zip("rgb", [round(min(1, v / 255 * 1.4), 2) for v in RGB[c]])),   # base in seat colour
            grid={"x": SCENES[0]["heroes"][n][0], "z": SCENES[0]["heroes"][n][1], "k": "fig"}),
        sheet,
        obj("Custom_Model", tf(), GUID=guid(c, "hp"), Nickname=f"{h['name']} HP", Locked=False, Tags=["kit", f"hp_{c}"],
            CustomMesh=mesh(base, "hp_plaque"), grid={"role": "hp", "color": c, "max": h["hp"]}),
        obj("Die_20", tf(), GUID=guid(c, "d20"), Tags=["kit"], ColorDiffuse=colour, grid={"role": "d20", "color": c}),
        obj("Deck", tf(rz=180.0), GUID=guid(c, "deck"), Nickname=f"{h['name']} cards", DeckIDs=ids,
            CustomDeck={str(n + 1): cdeck}, ContainedObjects=cards, Tags=["kit", f"card_{c}"], Hands=True,
            grid={"role": "deck", "color": c}),
    ]


# GM table: past the main table's east edge, the GM sits east looking west (top = west, right = north).
# Everything on it is GM-only (tag "gm") except the table itself and the screen. Cards ry 90 read upright for the GM.
TEXTURES = dict(l.split() for l in (ROOT / "props" / "textures.txt").read_text().splitlines())   # prop -> baked image
EDGE = COLS / ART_FRAC / 2          # main table half-width in grid squares
GM_GAP = -0.4                       # GM table's inner edge vs the main table edge (negative: tucked under its rim)
X0 = EDGE + GM_GAP                  # GM table inner edge; it is 10.4 squares deep (x) and 20.8 wide (z)
DIE_COLOURS = {"Die_4": (0.55, 0.06, 0.08), "Die_6": (0.55, 0.06, 0.08), "Die_8": (0.55, 0.06, 0.08),
               "Die_10": (0.55, 0.06, 0.08), "Die_12": (0.55, 0.06, 0.08), "Die_20": (0.85, 0.62, 0.12)}
TRAY = (7.2, -7.5)                  # dice tray, from X0; it also carries the GM control panel's buttons
# GM control panel, like the floating one: bottom left of the red mat as the GM sees it (GM looks west, so "down" is
# +x and "left" is -z). Rows run down the mat; each entry: label, what it does, its row, and its slot in a 3-wide row.
PANEL_Z, PANEL_X0, ROW = -3.0, 4.2, 0.52
GM_BUTTONS = ([dict(label="Game Master", row=0, kind="title")] +
              [dict(label=s["title"], scene=i + 1, row=i + 1) for i, s in enumerate(SCENES)] +
              [dict(label=t, fn=f, row=len(SCENES) + 1, slot=k) for k, (f, t) in
               enumerate((("musicScene", "Scene music"), ("musicBattle", "Battle"), ("musicStop", "Stop")))] +
              [dict(label="Toggle visibility (selected)", fn="toggleSelected", row=len(SCENES) + 2),
               dict(label="REST (cards + full HP)", fn="rest", row=len(SCENES) + 3)])
for b in GM_BUTTONS:
    b["x"] = round(TRAY[0] - (PANEL_X0 + ROW * b["row"]), 2)   # mirrored: rows came out bottom-to-top in TTS
    b["z"] = round(PANEL_Z + (b["slot"] - 1) * 1.1 - TRAY[1] if "slot" in b else PANEL_Z - TRAY[1], 2)
    b["w"] = 1.0 if "slot" in b else 3.2



def gm_objects(base):
    gm = dict(Tags=["gm"])
    def model(name, **kw):
        kw.setdefault("Nickname", name.replace("_", " ").title())
        return obj("Custom_Model", tf(), CustomMesh={
            "MeshURL": f"{base}props/{name}.obj", "DiffuseURL": f"{base}props/{TEXTURES[name]}", "NormalURL": "",
            "ColliderURL": "", "Convex": kw.pop("convex", True), "MaterialIndex": 2 if name == "coin" else 1,
            "TypeIndex": 0, "CastShadows": True}, **kw)
    out = [model("gm_table", GUID=guid("gm", "table"), Nickname="GM table", Locked=True, Tags=["gmtable"],
                 grid={"x": X0 + 5.2, "z": 0, "k": "model", "lift": -0.02}),            # a hair low: no flicker at the seam
           model("gm_screen", GUID=guid("gm", "screen"), Nickname="GM screen", Locked=True, Tags=["gmscreen"],
                 grid={"x": X0 + 1.0, "z": 0, "k": "model", "lift": 0}),
           model("dice_tray", GUID=guid("gm", "tray"), Nickname="Dice tray", Locked=True, convex=False,
                 Tags=["gm", "gmconsole"], grid={"x": X0 + TRAY[0], "z": TRAY[1], "k": "model", "lift": 0}),
           model("gm_board", GUID=guid("gm", "board"), Nickname="GM controls", Locked=True, **gm,
                 grid={"x": X0 + PANEL_X0 + ROW * (len(SCENES) + 3) / 2, "z": PANEL_Z, "k": "model", "lift": 0}),
           obj("Custom_PDF", tf(ry=90.0), GUID=guid("gm", "book"), Nickname="GM guide", **gm,
               CustomPDF={"PDFUrl": f"{base}art/out/gm_guide.pdf", "PDFPassword": "", "PDFPage": 0, "PDFPageOffset": 0},
               grid={"x": X0 + 2.6, "z": -6.9, "k": "tile", "s": [1.8, 1, 1.8]})]
    for n, (die, rgb) in enumerate(DIE_COLOURS.items()):
        out.append(obj(die, tf(), GUID=guid("gm", "die", n), Nickname="GM " + die.replace("Die_", "d"), **gm,
                       ColorDiffuse=dict(zip("rgb", rgb)),
                       grid={"x": X0 + TRAY[0] - 0.6 + 0.6 * (n % 3), "z": TRAY[1] - 0.45 + 0.9 * (n // 3), "k": "tile",
                             "s": [1, 1, 1], "lift": 1.5}))
    deck = {"FaceURL": f"{base}art/out/items.jpg", "BackURL": f"{base}art/out/card_back.jpg", "NumWidth": 4,
            "NumHeight": 2, "BackIsHidden": True, "UniqueBack": False, "Type": 0}
    spots = [(X0 + x, z) for x in (1.3, 3.4, 5.5) for z in (3.9, 5.4, 6.9, 8.4)]   # tight block, top right
    cards = [(i, name, text) for i, (name, text, _, k) in enumerate(ITEMS) for _ in range(k)]
    for n, ((i, name, text), (x, z)) in enumerate(zip(cards, spots)):
        out.append(obj("Card", tf(ry=90.0), CardID=900 + i, Nickname=name, Description=text, CustomDeck={"9": deck},
                       GUID=guid("gm", "item", n), Hands=True, **gm, grid={"x": x, "z": z, "k": "tile", "s": [1, 1, 1]}))
    coin = model("coin", Nickname="Gold coin", Hands=True)
    out.append(obj("Infinite_Bag", tf(), GUID=guid("gm", "gold"), Nickname="Gold pouch", ColorDiffuse={"r": 0.45, "g": 0.3, "b": 0.18},
                   Description="Endless gold. Hover and press a number: that many coins go to your hand.", **gm,
                   ContainedObjects=[coin], grid={"x": X0 + 7.8, "z": 6.9, "k": "tile", "s": [1.8, 1.8, 1.8], "inner": 1.0}))
    return out


def xml_ui(base):
    btn = 'fontSize="16" preferredHeight="34" colors="#3a2a1a|#5a4028|#2a1a0a|#3a2a1a" textColor="#f0d9a0"'
    on = f'onClick="{CONTROLLER}/'   # UI lives in Global, handlers live on the controller object
    scenes = "".join(f'<Button id="scene_{i + 1}" {on}onSceneButton" {btn}>{s["title"]}</Button>'
                     for i, s in enumerate(SCENES))
    gm = f"""<Panel id="gm" visibility="Black" rectAlignment="UpperRight" offsetXY="-10 -80" width="260"
 height="{80 + 38 * (len(SCENES) + 4)}" color="#1b1410ee" padding="8 8 8 8">
<VerticalLayout spacing="4" childForceExpandHeight="false">
<Text id="sceneTitle" fontSize="18" color="#f0d9a0" fontStyle="Bold" preferredHeight="40">GM</Text>
{scenes}
<HorizontalLayout spacing="4" preferredHeight="34"><Button {on}musicScene" {btn}>Scene music</Button>
<Button {on}musicBattle" {btn}>Battle</Button><Button {on}musicStop" {btn}>Stop</Button></HorizontalLayout>
<Button {on}toggleSelected" {btn}>Toggle visibility (selected)</Button>
<Button {on}rest" {btn}>REST (cards + full HP)</Button>
</VerticalLayout></Panel>"""
    picks = "".join(f"""<VerticalLayout spacing="4"><Image image="portrait_{h['key']}" preserveAspect="true"/>
<Button id="pick_{h['color']}" {on}pick" {btn}>{h['name'].split(' the ')[0]}</Button></VerticalLayout>"""
                    for h in HEROES)
    picks += f"""<VerticalLayout spacing="4"><Image image="portrait_gm" preserveAspect="true"/>
<Button id="pick_Black" {on}pick" {btn}>Game Master</Button></VerticalLayout>"""
    pick = f"""<Panel id="pick" visibility="White|Brown|Orange|Yellow|Teal|Pink|Grey" rectAlignment="UpperCenter"
 offsetXY="0 -60" width="940" height="260" color="#1b1410ee" padding="10 10 10 10">
<VerticalLayout spacing="6"><Text fontSize="24" color="#f0d9a0" fontStyle="Bold" preferredHeight="36">Choose your adventurer</Text>
<HorizontalLayout spacing="10">{picks}</HorizontalLayout></VerticalLayout></Panel>"""
    # Lua's UI.setXml wants lowercase name/url (the save-file format's Name/URL gives a null-reference error)
    assets = [{"name": f"portrait_{h['key']}", "url": f"{base}art/out/portrait_{h['key']}.jpg"} for h in HEROES] + [
        {"name": "portrait_gm", "url": f"{base}art/out/portrait_gm.jpg"}]
    return gm + pick, assets


def lua_lit(v):
    """Python data -> Lua table constructor (string keys always bracketed, so {"1": ...} stays a string key)."""
    if isinstance(v, dict):
        return "{" + ",".join(f"[{lua_lit(str(k))}]={lua_lit(x)}" for k, x in v.items() if x is not None) + "}"
    if isinstance(v, (list, tuple)):
        assert None not in v, "nil inside a Lua array would cut it short"
        return "{" + ",".join(lua_lit(x) for x in v) + "}"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    out = json.dumps(v, ensure_ascii=False)   # raw UTF-8; \n \t \" \\ mean the same in Lua
    assert "\\u" not in out, f"control character in {v!r}: Lua has no \\uXXXX escape"
    return out


def gm_guide():
    out = ["# The Giants of Holst - GM guide\n", "## Setup\n",
           "- Host the game and take the **Black (Game Master)** seat. The GM panel (top right) is only visible to Black/host.",
           "- Players join and click their adventurer on the pick panel. Their seat changes, cards are dealt automatically.",
           "- NPC controls (HP, damage box, attack buttons) float over each NPC, GM-only. Type `12` (or `+12`) to hurt, `-5` to heal.",
           "- Attack buttons whisper the roll to you (Black). Crits add an extra set of damage dice.",
           "- Hiding things: select NPCs or props (drag a box) and press *Toggle visibility (selected)* in a GM menu, or",
           "  bind the *Toggle visibility (GM)* hotkey (Options > Game Keys). Hidden things vanish for players and show",
           "  see-through with an outline for you. Press again to show them.",
           "- The same text as below sits in the Notebook (GM-only tabs).\n",
           "## Rules\n", "```", RULES, "```\n", "## Heroes\n"]
    for h in HEROES:
        out.append(f"**{h['name']}** ({h['color']}) HP {h['hp']}, Def {h['defense']}, "
                   + ", ".join(f"{k} {v:+d}" for k, v in h["stats"].items()))
        out += [f"- Card *{t}*: {x}" for t, x, _ in h["cards"]] + [""]
    out.append("## NPCs\n")
    for t in NPCS.values():
        atk = "; ".join(f"{a} ({'+%d' % b if b is not None else 'no roll'}, {c or '-'}, {d})" for a, b, c, d in t["attacks"])
        out.append(f"- **{t['name']}** HP {t['hp']}, Def {t['defense']}. {atk}. {t['notes']}")
    for s in SCENES:
        out += [f"\n## {s['title']}\n", "```", s["notes"], "```"]
    out += ["\n## First-run checklist\n",
            "1. Load save as host in Black. GM panel top right, title map with 4 heroes.",
            "2. Second client picks Thief: moves to Red, gets 6 cards; button shows as taken.",
            "3. Click each scene: table image, props, NPCs and music change; enemies are invisible to players until near.",
            "4. On a giant: type 20 in the damage box -> bar drops. Attack button -> roll whispered to you.",
            "5. Play a card onto the table, press REST -> card returns to hand, counters reset.",
            "6. If things sit off the art or the kits overlap it: LAYOUT in build.py; health bars: UI_POS in npc.lua.",
            "",
            "Updates: Holst.json is only a loader. It downloads game.json + controller.lua from GitHub on every load, so pushed fixes",
            "arrive without replacing the save. Offline, a save you made yourself keeps the last version it loaded."]
    return "\n".join(out) + "\n"


def main(base):
    build_images()
    textures = dict(l.split() for l in (ROOT / "props" / "textures.txt").read_text().splitlines())
    heroes, kits = {}, []
    for n, h in enumerate(HEROES):
        kits += hero_objects(h, n, base)
        heroes[h["color"]] = dict(name=h["name"], short=h["name"].split(" the ")[0], hp=h["hp"])
    notebook = [dict(title="Rules", body=RULES, color="Grey")] + \
               [dict(title=s["title"], body=s["notes"], color="Black") for s in SCENES]
    data = dict(colors=[h["color"] for h in HEROES], heroes=heroes, kits=kits, notebook=notebook, layout=LAYOUT,
                gm=gm_objects(base), gm_buttons=GM_BUTTONS, fog=FOG,
                scenes=[scene_data(s, base, textures) for s in SCENES],
                battle=dict(url=f"{base}music/{BATTLE_MUSIC}", title="Battle!"))
    # any change to data (incl. npc.lua inside spawns) or to game.lua gives a new version -> clients reinstall
    data["version"] = hashlib.md5((json.dumps(data, sort_keys=True) + (ROOT / "game.lua").read_text()).encode()).hexdigest()[:8]
    # DATA goes in as a Lua table literal: TTS's JSON.decode takes minutes on a payload this size
    lua = (ROOT / "game.lua").read_text().replace("DATA = {} --@DATA@", "DATA = " + lua_lit(data))
    print("GM guide book:", gm_pdf(gm_guide(), OUT / "gm_guide.pdf"), "pages")
    xml, assets = xml_ui(base)
    (ROOT / "controller.lua").write_text(lua)
    (ROOT / "game.json").write_text(json.dumps(dict(version=data["version"], xml=xml, assets=assets)))

    if "--save" not in sys.argv:
        print("wrote controller.lua version", data["version"], "-", len(kits), "kit objects,",
              sum(len(s["spawns"]) for s in data["scenes"]), "scene spawns (Holst.json untouched; --save rebuilds it)")
        (ROOT / "GM_GUIDE.md").write_text(gm_guide())
        return
    # Holst.json: just the loader. Only rebuild/redistribute it if loader.lua changes: game.lua switches to the
    # custom table, moves the hands and swaps the table image itself, so older copies of the save keep working.
    hands = [{"Color": c, "Transform": tf(x, 4.0, z, ry=0.0 if z < 0 else 180.0) | {"scaleX": 11.0, "scaleY": 5.0, "scaleZ": 4.0}}
             for c, x, z in [("Red", -25, -25), ("Blue", 25, -25), ("Green", 25, 25), ("Purple", -25, 25)]]
    save = {"SaveName": "The Giants of Holst", "GameMode": "The Giants of Holst", "Gravity": 0.5, "PlayArea": 0.5,
            "Date": "", "Table": "Table_Custom", "TableURL": f"{base}art/out/table_title.jpg", "Sky": "Sky_Museum",
            "Note": "", "Rules": RULES, "XmlUI": "",
            "LuaScript": (ROOT / "loader.lua").read_text().replace("--@CONTROLLER@", CONTROLLER), "LuaScriptState": "",
            "Grid": {"Type": 0, "Lines": False, "Color": {"r": 0, "g": 0, "b": 0}, "Opacity": 0.75, "ThickLines": False,
                     "Snapping": False, "Offset": False, "BothSnapping": False, "xSize": 2.0, "ySize": 2.0,
                     "PosOffset": {"x": 0.0, "y": 1.0, "z": 0.0}},
            "Hands": {"Enable": True, "DisableUnused": False, "Hiding": 0, "HandTransforms": hands},
            "TabStates": {}, "ObjectStates": [], "VersionNumber": "v13.2.2"}
    (ROOT / "Holst.json").write_text(json.dumps(save, indent=1))
    (ROOT / "GM_GUIDE.md").write_text(gm_guide())
    print("wrote controller.lua version", data["version"], "-", len(kits), "kit objects,",
          sum(len(s["spawns"]) for s in data["scenes"]), "scene spawns")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args[0] if args else (ROOT.resolve().as_uri() + "/"))
