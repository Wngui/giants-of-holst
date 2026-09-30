"""Build the TTS save.  python build.py <asset base url>
e.g. https://raw.githubusercontent.com/<user>/<repo>/<commit>/  -> writes art/out/*, Holst.json, GM_GUIDE.md"""
import hashlib, json, sys, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from content import HEROES, NPCS, SCENES, RULES, BATTLE_MUSIC

ROOT = Path(__file__).parent
CONTROLLER = "901d00"       # GUID of the hidden object that runs game.lua
RAW, OUT = ROOT / "art" / "raw", ROOT / "art" / "out"
COLS, ROWS = 22, 22 / 1.5   # grid squares across/down the 3:2 scene art
TABLE_PX = (3400, 2000)     # custom rectangle table images are 17:10
ART_FRAC = 0.64             # share of the table width the scene art covers; the wooden border holds the player kits
# measured-at-load layout knobs, passed to game.lua (fractions of the table's measured width/depth)
LAYOUT = {"cols": COLS, "rows": ROWS, "art_w": ART_FRAC, "surface": 1.0,
          "kit_x": 0.41, "sheet_z": 0.30, "row_z": 0.12, "sheet_w": 0.16, "tile_unit": 2.0}
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
    im = Image.new("RGB", (1500, 1000), (236, 222, 190))
    d = ImageDraw.Draw(im)
    col = RGB[hero["color"]]
    d.rectangle((0, 0, 1499, 999), outline=col, width=16)
    im.paste(Image.open(RAW / f"portrait_{hero['key']}.png").convert("RGB").resize((540, 540)), (30, 30))
    d.text((600, 40), hero["name"], font=font(56, True), fill=col)
    wrap(d, (600, 120), hero["blurb"], 28, 52)
    for n, (label, val) in enumerate([("HP", hero["hp"]), ("DEFENSE", hero["defense"])]):
        x = 600 + n * 260
        d.rounded_rectangle((x, 200, x + 230, 330), 14, outline=col, width=5)
        d.text((x + 115, 230), label, font=font(26, True), fill=col, anchor="mm")
        d.text((x + 115, 290), str(val), font=font(56, True), fill=(30, 20, 10), anchor="mm")
    stats = "    ".join(f"{k} {v:+d}" for k, v in hero["stats"].items())
    d.text((600, 360), stats, font=font(36, True), fill=(30, 20, 10))
    d.text((600, 430), "ATTACKS  (d20 + bonus vs Defense)", font=font(26, True), fill=col)
    for n, (name, bonus, dmg, note) in enumerate(hero["attacks"]):
        d.text((600, 475 + n * 45), f"{name}: {bonus:+d} to hit, {dmg} damage  ({note})", font=font(24), fill=(30, 20, 10))
    wrap(d, (40, 600), RULES, 24, 105, spacing=8)
    return im


def build_images():
    OUT.mkdir(parents=True, exist_ok=True)
    for h in HEROES:
        sheet = Image.new("RGB", (1500, 1400))
        for i in range(6):
            sheet.paste(make_card(h, i), ((i % 3) * 500, (i // 3) * 700))
        sheet.save(OUT / f"cards_{h['key']}.jpg", quality=90)
        make_sheet(h).save(OUT / f"sheet_{h['key']}.jpg", quality=90)
        Image.open(RAW / f"portrait_{h['key']}.png").convert("RGB").resize((256, 256)).save(OUT / f"portrait_{h['key']}.jpg")
    Image.open(RAW / "card_back.png").convert("RGB").resize((500, 700)).save(OUT / "card_back.jpg", quality=90)
    wood = Image.open(RAW / "table_wood.png").convert("RGB").resize(TABLE_PX)
    aw = int(TABLE_PX[0] * ART_FRAC)
    ah = int(aw / 1.5)
    for s in SCENES:
        im = Image.open(RAW / f"map_{s['key']}.png").convert("RGB")
        if s["key"] == "title":
            d = ImageDraw.Draw(im)
            d.text((768, 470), s["title"], font=font(110, True), fill=(250, 235, 200), anchor="mm",
                   stroke_width=6, stroke_fill=(40, 20, 10))
        table = wood.copy()
        x0, y0 = (TABLE_PX[0] - aw) // 2, (TABLE_PX[1] - ah) // 2
        ImageDraw.Draw(table).rectangle((x0 - 14, y0 - 14, x0 + aw + 13, y0 + ah + 13), fill=(150, 115, 50))
        table.paste(im.resize((aw, ah), Image.LANCZOS), (x0, y0))
        table.save(OUT / f"table_{s['key']}.jpg", quality=85)


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


def tile(url, transform, **kw):
    transform["scaleY"] = 1.0   # keep tiles thin; scale only stretches X/Z
    return obj("Custom_Tile", transform, CustomImage={
        "ImageURL": url, "ImageSecondaryURL": "", "ImageScalar": 1.0, "WidthScale": 0.0,
        "CustomTile": {"Type": 0, "Thickness": 0.2, "Stackable": False, "Stretch": False}}, **kw)


# Everything on the table is positioned by grid square; game.lua measures the table at load and turns
# "grid" into a world transform (TTS table sizes aren't documented, guessing them made things fall off).
def npc(key, x, z, n, scene, hp=None):
    t = NPCS[key]
    hp = hp or t["hp"]
    attacks = [dict(name=a, hit=b, dmg=c, note=d) for a, b, c, d in t["attacks"]]
    ry = (270.0 if x > 0 else 90.0) + (180.0 if t.get("flip") else 0.0)   # flip: model faces backwards
    o = obj(t["fig"], tf(ry=ry), GUID=guid(scene, key, n), Nickname=t["name"], Tags=["scene"], GMNotes=t["notes"],
            grid={"x": x, "z": z, "k": "fig"})
    if t.get("dead"):
        o["RPGdead"] = True
    if t.get("tint"):
        o["ColorDiffuse"] = dict(zip("rgb", t["tint"]))
    if attacks or not t.get("dead"):   # corpses and carcasses are props, everyone else gets a healthbar
        o["LuaScript"] = (ROOT / "npc.lua").read_text()
        o["LuaScriptState"] = json.dumps({"name": t["name"], "hp": t.get("start_hp", hp), "max": hp,
                                          "def": t["defense"], "down": bool(t.get("dead")), "attacks": attacks})
    return o


def prop(spec, n, scene, base, textures):
    name, x, z, *rest = spec
    rot, scale = (list(rest) + [0, 1][len(rest):])[:2]      # optional rot, scale
    s = list(scale) if isinstance(scale, (list, tuple)) else [scale] * 3
    common = dict(GUID=guid(scene, "prop", n), Tags=["scene", "pin"], Tooltip=False)
    if name.startswith("Tileset_"):                       # built-in TTS tileset piece
        return obj(name, tf(ry=rot), grid={"x": x, "z": z, "k": "builtin", "s": s}, **common)
    return obj("Custom_Model", tf(ry=rot), grid={"x": x, "z": z, "k": "model", "s": s}, Nickname="", **common,
               CustomMesh={"MeshURL": f"{base}props/{name}.obj", "DiffuseURL": f"{base}props/{textures[name]}",
                           "NormalURL": "", "ColliderURL": f"{base}props/collider_flat.obj", "Convex": True,
                           "MaterialIndex": 1, "TypeIndex": 0, "CastShadows": True})


def scene_data(s, base, textures):
    spawns = []
    if s["fog"]:
        spawns.append(obj("FogOfWar", tf(), GUID=guid(s["key"], "fog"), Tags=["scene", "fog"],
                          FogOfWar={"HideGmPointer": False, "HideObjects": True, "Height": 1.0}, grid={"k": "fog"}))
    for n, spec in enumerate(s.get("props", [])):
        spawns.append(prop(spec, n, s["key"], base, textures))
    for n, spec in enumerate(s["npcs"]):
        spawns.append(npc(*spec[:3], n, s["key"], *spec[3:]))
    if s["key"] == "den":   # Baron's Bones dice on the gambling table
        spawns += [obj("Die_6", tf(), GUID=guid("den", "die", i), Tags=["scene"], grid={"x": -0.6 + 0.6 * i, "z": 0, "k": "fig"})
                   for i in range(3)]
    return dict(title=s["title"], spawns=spawns, heroes=[[x, z] for x, z in s["heroes"]],
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
    return [
        obj(h["fig"], tf(), GUID=guid(c, "fig"), Nickname=h["name"], Tags=["kit", f"fig_{c}"],
            FogOfWarRevealer={"Active": True, "Range": 10.0, "Color": "All"},
            grid={"x": SCENES[0]["heroes"][n][0], "z": SCENES[0]["heroes"][n][1], "k": "fig"}),
        tile(f"{base}art/out/sheet_{h['key']}.jpg", tf(), GUID=guid(c, "sheet"), Nickname=h["name"], Locked=True,
             Tags=["kit"], grid={"role": "sheet", "color": c}),
        obj("Counter", tf(), GUID=guid(c, "counter"), Nickname=f"{h['name']} HP", Counter={"value": h["hp"]},
            Tags=["kit", f"counter_{c}"], grid={"role": "counter", "color": c}),
        obj("Die_20", tf(), GUID=guid(c, "d20"), Tags=["kit"], ColorDiffuse=colour, grid={"role": "d20", "color": c}),
        obj("Deck", tf(rz=180.0), GUID=guid(c, "deck"), Nickname=f"{h['name']} cards", DeckIDs=ids,
            CustomDeck={str(n + 1): cdeck}, ContainedObjects=cards, Tags=["kit", f"card_{c}"], Hands=True,
            grid={"role": "deck", "color": c}),
    ]


def xml_ui(base):
    btn = 'fontSize="16" preferredHeight="34" colors="#3a2a1a|#5a4028|#2a1a0a|#3a2a1a" textColor="#f0d9a0"'
    on = f'onClick="{CONTROLLER}/'   # UI lives in Global, handlers live on the controller object
    scenes = "".join(f'<Button id="scene_{i + 1}" {on}onSceneButton" {btn}>{s["title"]}</Button>'
                     for i, s in enumerate(SCENES))
    gm = f"""<Panel id="gm" visibility="Black|Host" rectAlignment="UpperRight" offsetXY="-10 -80" width="260"
 height="{80 + 38 * (len(SCENES) + 4)}" color="#1b1410ee" padding="8 8 8 8">
<VerticalLayout spacing="4" childForceExpandHeight="false">
<Text id="sceneTitle" fontSize="18" color="#f0d9a0" fontStyle="Bold" preferredHeight="40">GM</Text>
{scenes}
<HorizontalLayout spacing="4" preferredHeight="34"><Button {on}musicScene" {btn}>Scene music</Button>
<Button {on}musicBattle" {btn}>Battle</Button><Button {on}musicStop" {btn}>Stop</Button></HorizontalLayout>
<Button {on}revealAll" {btn}>Reveal all fog</Button>
<Button {on}rest" {btn}>REST (cards + full HP)</Button>
</VerticalLayout></Panel>"""
    picks = "".join(f"""<VerticalLayout spacing="4"><Image image="portrait_{h['key']}" preserveAspect="true"/>
<Button id="pick_{h['color']}" {on}pick" {btn}>{h['name'].split(' the ')[0]}</Button></VerticalLayout>"""
                    for h in HEROES)
    pick = f"""<Panel id="pick" visibility="White|Brown|Orange|Yellow|Teal|Pink|Grey" rectAlignment="UpperCenter"
 offsetXY="0 -60" width="760" height="260" color="#1b1410ee" padding="10 10 10 10">
<VerticalLayout spacing="6"><Text fontSize="24" color="#f0d9a0" fontStyle="Bold" preferredHeight="36">Choose your adventurer</Text>
<HorizontalLayout spacing="10">{picks}</HorizontalLayout></VerticalLayout></Panel>"""
    # Lua's UI.setXml wants lowercase name/url (the save-file format's Name/URL gives a null-reference error)
    assets = [{"name": f"portrait_{h['key']}", "url": f"{base}art/out/portrait_{h['key']}.jpg"} for h in HEROES]
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
           "- Fog: heroes reveal around themselves. Use TTS's own fog tool or *Reveal all fog* for set pieces.",
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
            "3. Click each scene: map + NPCs + fog + music change.",
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
                scenes=[scene_data(s, base, textures) for s in SCENES],
                battle=dict(url=f"{base}music/{BATTLE_MUSIC}", title="Battle!"))
    # any change to data (incl. npc.lua inside spawns) or to game.lua gives a new version -> clients reinstall
    data["version"] = hashlib.md5((json.dumps(data, sort_keys=True) + (ROOT / "game.lua").read_text()).encode()).hexdigest()[:8]
    # DATA goes in as a Lua table literal: TTS's JSON.decode takes minutes on a payload this size
    lua = (ROOT / "game.lua").read_text().replace("DATA = {} --@DATA@", "DATA = " + lua_lit(data))
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
