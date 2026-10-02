"""Runs the TTS scripts against a stubbed TTS API (lupa): loader.lua from Holst.json downloads game.json,
spawns the controller (game.lua), whose scenes spawn NPCs running npc.lua. Each object script gets its own
environment, like in TTS. Catches Lua errors and logic slips before a trip to the TTS PC.  python test_lua.py"""
import json, os
dump = []
from lupa import LuaRuntime

save = json.load(open("Holst.json"))
game = json.load(open("game.json"))
controller_lua = open("controller.lua").read()
lua = LuaRuntime(unpack_returned_tuples=True)
g = lua.globals()
lua_type = lua.eval("type")


def to_lua(v):
    if isinstance(v, dict):
        return lua.table_from({k: to_lua(x) for k, x in v.items()})
    if isinstance(v, list):
        return lua.table_from([to_lua(x) for x in v])
    return v


def to_py(t):
    if lua_type(t) != "table":
        return t
    keys = list(t.keys())
    if keys and all(isinstance(k, int) for k in keys):
        return [to_py(t[k]) for k in sorted(keys)]
    return {k: to_py(t[k]) for k in keys}


g.JSON = to_lua({})
def decode(s):
    assert len(s) < 50_000, f"JSON.decode of {len(s)} chars: TTS takes minutes on this"
    return to_lua(json.loads(s))


g.JSON.decode = decode
g.JSON.encode = lambda t: json.dumps(to_py(t))
g.FILES = to_lua({"game.json": json.dumps(game), "controller.lua": controller_lua})

lua.execute("""
log = {}
function broadcastToAll(m) log[#log+1] = m end
function broadcastToColor(m, c) log[#log+1] = c .. ": " .. m end
local _tonumber = tonumber
function tonumber(v, base)   -- MoonSharp (TTS) throws where real Lua returns nil when a base is given
  if base then assert(tostring(v):match("^%d+$"), "MoonSharp tonumber throws on " .. tostring(v)) end
  return _tonumber(v, base)
end
UIattr = {}
UI = { setAttribute = function(id, k, v) UIattr[id .. "." .. k] = tostring(v) end,
       setXml = function(x, assets)
         for _, a in ipairs(assets) do assert(a.name and a.url, "UI asset needs lowercase name/url") end
         UIxml, UIassets = x, assets
       end }
tabs = {}
-- a 70 x 41 custom table whose top sits at y = 1
Tables = { getTableObject = function() return { getBounds = function()
             return { center = Vector(0, 0.5, 0), size = Vector(70, 1, 41) } end } end,
           setCustomURL = function(u) tableURL = u end,
           getTable = function() return tableName end, setTable = function(n) tableName = n end }
tableName = "Table_RPG"   -- the published Holst.json still starts on the RPG table
-- hand zones are objects; the save brings one per seat colour, spawnObject({type = "HandTrigger"}) makes more
handzones = {}
function handZone(color, t)
  local h = {type = "Hand", color = color, pos = t.position, rot = t.rotation, scale = t.scale}
  function h.getValue() return h.color end
  function h.setValue(c) h.color = c end
  function h.setPosition(p) h.pos = p end
  function h.setRotation(r) h.rot = r end
  function h.setScale(s) h.scale = s end
  function h.getPosition() return {x = h.pos[1], y = h.pos[2], z = h.pos[3]} end
  function h.getRotation() return {x = h.rot[1], y = h.rot[2], z = h.rot[3]} end
  handzones[#handzones + 1] = h
  return h
end
for _, c in ipairs({"Red", "Blue", "Green", "Purple"}) do handZone(c, {position = {0, 4, 0}, rotation = {0, 0, 0}, scale = {11, 5, 4}}) end
Hands = { getHands = function() return handzones end }
function spawnObject(p)
  assert(p.type == "HandTrigger", p.type)
  local h = handZone(nil, p)
  if p.callback_function then p.callback_function(h) end
  return h
end
Notes = { getNotebookTabs = function() local r = {} for i, t in ipairs(tabs) do r[i] = {index = i - 1, title = t.title} end return r end,
          removeNotebookTab = function(i) table.remove(tabs, i + 1) end,
          addNotebookTab = function(t) tabs[#tabs + 1] = t end }
MusicPlayer = { setCurrentAudioclip = function(t) MusicPlayer.url = t.url end, pause = function() end,
                play = function() end, player_status = "Ready" }
Grid = {}
Wait = { time = function(f) f() end, frames = function(f) f() end, condition = function(f, c) if c() then f() end end }
WebRequest = { get = function(url, cb)
  requested = url
  local file = url:match("/main/([^?]+)%?t=%d+$")
  cb({ text = FILES[file], response_code = FILES[file] and 200 or 404, is_error = false })
end }
function Vector(x, y, z) return setmetatable({x=x, y=y, z=z}, {__add = function(a, b) return Vector(a.x+b.x, a.y+b.y, a.z+b.z) end}) end
objects = {}
function run(code, self)   -- a script with its own globals, falling back to the shared API
  local env = setmetatable({ self = self }, { __index = _G })
  assert(load(code, "script", "t", env))()
  return env
end
autoguid = 0
function makeObj(d)
  if not d.GUID then autoguid = autoguid + 1; d.GUID = "auto" .. autoguid end   -- TTS assigns one
  local o = {data = d, tags = {}, type = d.Name == "Deck" and "Deck" or (d.Name == "Card" and "Card" or "Other")}
  for _, t in ipairs(d.Tags or {}) do o.tags[t] = true end
  function o.getGUID() return d.GUID end
  function o.hasTag(t) return o.tags[t] == true end
  function o.removeTag(t) o.tags[t] = nil end
  function o.addTag(t) o.tags[t] = true end
  function o.getColorTint() return o.tint or {r = 1, g = 1, b = 1, a = 1} end
  function o.setColorTint(t) o.tint = t end
  function o.highlightOn() o.lit = true end
  function o.highlightOff() o.lit = false end
  function o.getLuaScript() return d.LuaScript or "" end
  function o.getRotation() return {x = 0, y = d.Transform and d.Transform.rotY or 0, z = 0} end
  function o.createButton(b) o.buttons = o.buttons or {}; o.buttons[#o.buttons + 1] = b end
  function o.editButton(e) for k, v in pairs(e) do if k ~= "index" then o.buttons[e.index + 1][k] = v end end end
  function o.getScale() local t = d.Transform or {} return {x = t.scaleX or 1, y = t.scaleY or 1, z = t.scaleZ or 1} end
  function o.addAttachment(r) o.attached = (o.attached or 0) + 1; objects[r.getGUID()] = nil end
  function o.setInvisibleTo(t) o.invisible = #t > 0 end
  function o.getPosition()
    local p = o.pos or {d.Transform.posX, d.Transform.posY, d.Transform.posZ}
    return {x = p[1], y = p[2], z = p[3]}
  end
  function o.destruct() objects[d.GUID] = nil end
  function o.setLock(v) o.locked = v end
  function o.setPositionSmooth(p) o.pos = p end
  function o.setRotation(r) end
  function o.setRotationSmooth(r) end
  function o.getObjects() return d.ContainedObjects end
  function o.getVar(k) return o.env and o.env[k] end
  function o.call(f, a) return o.env[f](a) end
  function o.deal(n, c)
    for _, cd in ipairs(d.ContainedObjects) do local k = makeObj(cd); k.inHand = c end
    objects[d.GUID] = nil
  end
  o.Counter = { setValue = function(v) o.counter = v end }
  o.UI = { setXml = function(x) o.xml = x end, setAttribute = function() end }
  o.RPGFigurine = { die = function() end, attack = function() end }
  objects[d.GUID] = o
  if d.LuaScript and d.LuaScript ~= "" then
    o.env = run(d.LuaScript, o)
    if o.env.onLoad then o.env.onLoad(d.LuaScriptState or "") end
  end
  return o
end
function spawnObjectData(p) local o = makeObj(p.data); if p.callback_function then p.callback_function(o) end; return o end
function getObjectFromGUID(g) return objects[g] end
function getObjectsWithTag(t) local r = {} for _, o in pairs(objects) do if o.hasTag(t) then r[#r+1] = o end end return r end
hotkeys = {}
function addHotkey(name, f) hotkeys[name] = f end
selected = {}
function emit(ev, ...)   -- universal events reach every script
  if loader[ev] then loader[ev](...) end
  for _, o in pairs(objects) do if o.env and o.env[ev] then o.env[ev](...) end end
end
seated = {}
Player = {}
for _, c in ipairs({"Red","Blue","Green","Purple","White","Black"}) do
  Player[c] = setmetatable({}, {__index = function(_, k)
    if k == "seated" then return seated[c] ~= nil end
    if k == "steam_name" then return seated[c] end
    if k == "getSelectedObjects" then return function() return selected end end
    if k == "getHandObjects" then return function() local r = {} for _, o in pairs(objects) do if o.inHand == c then r[#r+1] = o end end return r end end
  end})
end
function mkplayer(name, color)
  seated[color] = name
  local p = {color = color, steam_name = name}
  function p.changeColor(c) seated[p.color] = nil; seated[c] = name; p.color = c; emit("onPlayerChangeColor", c) end
  return p
end
""")

# ---- loader: fresh save downloads and installs the game
assert save["ObjectStates"] == [] and "WebRequest.get" in save["LuaScript"]
g.loader = g.run(save["LuaScript"], None)
g.loader.onLoad("")
assert g.requested.startswith("https://raw.githubusercontent.com/Wngui/giants-of-holst/main/controller.lua?t=")
CTL = save["LuaScript"].split('CONTROLLER = "')[1][:6]
ctl = g.getObjectFromGUID(CTL)
assert ctl and ctl.getVar("VERSION") == game["version"]
c = ctl.env
assert 'onClick="%s/pick"' % CTL in g.UIxml
assert len(list(g.tabs.values())) == 1 + len(c.DATA.scenes)
count = lambda tag: len(list(g.getObjectsWithTag(tag).values()))
assert count("scene") == 0 and count("kit") == 20, (count("scene"), count("kit"))   # title: no props, 4 hero kits
assert g.tableURL.endswith("table_title.jpg") and g.tableName == "Table_Custom"
W, D, TOP = 70, 41, 1.0
L = to_py(c.DATA.layout)
SQ = W * L["art_w"] / L["cols"]
ART = (L["cols"] * SQ / 2, L["rows"] * SQ / 2)       # half-extents of the scene art on the table


def rect(o):
    t = o.data.Transform
    return t.posX, t.posZ, t.scaleX, t.scaleZ


# kits: on the table, above its surface, in the wooden border (not on the scene art), not on top of each other
boxes = []
for o in g.getObjectsWithTag("kit").values():
    t = o.data.Transform
    assert abs(t.posX) < W / 2 and abs(t.posZ) < D / 2 and t.posY >= TOP, (o.data.Nickname, t.posX, t.posZ)
    if o.data.Name == "Card" or any(k.startswith("fig_") for k in o.tags.keys()):
        continue
    hx, hz = (t.scaleX * L["tile_unit"] / 2, t.scaleX * L["tile_unit"] / 3) if o.data.Name == "Custom_Tile" else (0.8, 0.8)
    assert abs(t.posX) - hx > ART[0] or abs(t.posZ) - hz > ART[1], ("kit on the art", o.data.Nickname, t.posX, t.posZ)
    boxes.append((o.data.Nickname or o.data.Name, t.posX, t.posZ, hx, hz))
for i, a in enumerate(boxes):
    for b in boxes[i + 1:]:
        assert abs(a[1] - b[1]) >= a[3] + b[3] or abs(a[2] - b[2]) >= a[4] + b[4], ("kit overlap", a, b)
zones = {z.color: {"position": to_py(z.pos), "rotation": to_py(z.rot)} for z in g.handzones.values()}
assert len(zones) == len(g.handzones) == 5 and set(zones) == {"Red", "Blue", "Green", "Purple", "Black"}, zones
assert all(zones[c]["rotation"][1] == (0 if c in ("Red", "Blue") else 180) for c in ("Red", "Blue", "Green", "Purple"))   # facing their own seat
for col, t in zones.items():
    if col == "Black":   # the GM's hand lies past the GM table at the east end
        assert t["position"][0] > W / 2 + 10 * SQ, t
    else:   # along the bottom of the player's own sheet, on the table
        sheet = next(o for o in g.getObjectsWithTag("kit").values() if o.data.Name == "Custom_Tile"
                     and o.data.Nickname == to_py(c.DATA.heroes)[col]["name"])
        st = sheet.data.Transform
        assert abs(t["position"][0] - st.posX) < 1e-6, col
        assert abs(st.posZ) < abs(t["position"][2]) < D / 2, (col, st.posZ, t["position"][2])

scenes = to_py(c.DATA.scenes)
for i, s in enumerate(scenes, 1):
    c.setScene(i)
    assert count("scene") == len(s["spawns"]), (i, count("scene"))
    assert g.tableURL == s["table"]
    if os.environ.get("DUMP"):          # object list for preview.py (Blender)
        dump.append({"title": s["title"], "key": s["table"].rsplit("_", 1)[1][:-4], "objects": [
            {"name": o.data.Name, "nick": o.data.Nickname, "mesh": (to_py(o.data.CustomMesh) or {}).get("MeshURL", ""),
             "tex": (to_py(o.data.CustomMesh) or {}).get("DiffuseURL", ""), "t": to_py(o.data.Transform),
             "dead": bool(o.data.RPGdead)} for tag in ("scene", "gm", "gmscreen", "gmtable")
            for o in g.getObjectsWithTag(tag).values()] + [
            {"name": "hero", "nick": col, "t": {"posX": h.pos[1], "posY": h.pos[2], "posZ": h.pos[3]}}
            for col in ("Red", "Blue", "Green", "Purple") for h in g.getObjectsWithTag("fig_" + col).values()]})
    for o in g.getObjectsWithTag("scene").values():
        t = o.data.Transform
        assert "grid" not in dict(o.data), "grid must be stripped before spawnObjectData"
        if o.data.Name != "FogOfWar":
            assert abs(t.posX) <= ART[0] + 1e-6 and abs(t.posZ) <= ART[1] + 1e-6, (s["title"], o.data.Name, t.posX, t.posZ)
            assert t.posY >= TOP, (s["title"], o.data.Name)
            assert min(t.scaleX, t.scaleY, t.scaleZ) > 0, (s["title"], o.data.Name, "zero scale")
    assert g.MusicPlayer.url == s["music"]["url"]
    assert g.UIattr["sceneTitle.text"] == s["title"]
assert g.Grid.show_lines is False
c.musicBattle(); assert g.Grid.show_lines is True and abs(g.Grid.sizeX - SQ) < 1e-9   # Battle shows the grid
c.musicScene(); assert g.Grid.show_lines is False
fig = list(g.getObjectsWithTag("fig_Red").values())[0]
assert abs(fig.pos[3] - scenes[-1]["heroes"][0][1] * SQ) < 1e-9       # heroes moved to the last scene
if os.environ.get("DUMP"):
    json.dump({"W": W, "D": D, "TOP": TOP, "SQ": SQ, "scenes": dump}, open(os.environ["DUMP"], "w"))
# fog of war is off: every living NPC in Holst City starts hidden (see-through for the GM);
# the GM selects some and toggles them hidden and back
c.setScene(2)
objs = list(g.getObjectsWithTag("scene").values())
giants = [o for o in objs if o.data.Name == "rpg_CYCLOP"]
kids = [o for o in objs if o.data.Nickname == "Street kid"]
gm_bar = 'visibility="Black" percentage'
assert giants and kids and all(o.invisible and o.tint.a < 1 and o.lit and gm_bar in o.xml for o in giants + kids)
hero = list(g.getObjectsWithTag("fig_Red").values())[0]
g.selected = lua.table_from(giants)
c.toggleSelected(g.Player.Black)
assert not any(o.invisible or o.lit for o in giants)   # the GM shows them...
c.toggleSelected(g.Player.Black)                       # ...and hides them again
assert all(o.invisible and o.hasTag("hidden") and o.lit and o.tint.a < 1 and gm_bar in o.xml for o in giants)
gp = giants[0].getPosition()
hero.pos = lua.table_from([gp.x + 1, gp.y, gp.z])
c.onObjectDrop("Red", hero)
assert giants[0].invisible                           # walking up no longer reveals anything
g.selected = lua.table_from([])
c.hotkeys["Toggle visibility (GM)"]("Black", giants[0])   # hotkey on the hovered giant
assert not giants[0].invisible and not giants[0].lit and giants[0].tint.a == 1 and gm_bar not in giants[0].xml
c.hotkeys["Toggle visibility (GM)"]("Red", giants[1])     # players can't
assert giants[1].invisible
g.selected = lua.table_from(giants[1:])
c.toggleSelected(g.Player.Black)
assert not any(o.invisible for o in giants) and all(o.invisible for o in kids)
# GM desk: off the table's east edge and hidden from players; the screen on the table's east border, seen by all
desk = list(g.getObjectsWithTag("gm").values())
screen = list(g.getObjectsWithTag("gmscreen").values())
gmtable = list(g.getObjectsWithTag("gmtable").values())
assert len(gmtable) == 1 and not gmtable[0].invisible and abs(gmtable[0].data.Transform.posY - TOP) < 0.05   # level with the table
assert len(desk) == len(c.DATA.gm) - 2 and all(o.invisible for o in desk), [o.data.Nickname for o in desk if not o.invisible]
assert all(o.data.Transform.posX > W / 2 for o in desk), [(o.data.Nickname, o.data.Transform.posX) for o in desk]
assert len(screen) == 1 and not screen[0].invisible and screen[0].data.Transform.posX > W / 2   # on the GM table
board = list(g.getObjectsWithTag("gmconsole").values())[0]
assert len(board.buttons) == len(c.DATA.gm_buttons)
fn = board.buttons[2].click_function                 # title, then scene 1
g.UIattr["sceneTitle.text"] = ""
c[fn](board, "Red")                                  # players can't press GM buttons
assert g.UIattr["sceneTitle.text"] == ""
c[fn](board, "Black")
assert g.UIattr["sceneTitle.text"] == scenes[0]["title"]
lit = [i for i in range(1, len(board.buttons) + 1) if to_py(board.buttons[i].color) == [0.85, 0.65, 0.2]]
assert lit == [2], lit                               # only the current scene's button is lit
# bases: heroes tinted their seat colour
assert all(o.data.ColorDiffuse.r > 0.5 for o in g.getObjectsWithTag("fig_Red").values())
# HP shields: -, +, right-click = 5, clamped to 0..max, REST refills
shield = list(g.getObjectsWithTag("hp_Red").values())[0]
assert shield.buttons[1].label == "18"
down, up = shield.buttons[2].click_function, shield.buttons[3].click_function
c[down](shield, "Red", False); c[down](shield, "Red", True)
assert shield.buttons[1].label == "12"
c[up](shield, "Red", True); c[up](shield, "Red", True)
assert shield.buttons[1].label == "18"
pouch = next(o for o in desk if o.data.Name == "Infinite_Bag")
assert pouch.data.ContainedObjects[1].Transform.scaleX == SQ          # coins inside sized to the grid
card = next(o for o in desk if o.data.Name == "Card")
card.pos = lua.table_from([0, TOP, 0])
c.onObjectDrop("Red", card)                          # a player can't hand things out
assert card.invisible
c.onObjectDrop("Black", card)                        # GM puts it on the table -> everyone sees it
assert not card.invisible and not card.hasTag("gm")
card.pos = lua.table_from([W / 2 + 5 * SQ, TOP, 0])
c.onObjectDrop("Black", card)                        # and back on the desk -> GM-only again
assert card.invisible and card.hasTag("gm")
taken = []
pouch.takeObject = lambda p: taken.append(to_py(p)["position"])
c.pouchTyped(to_lua({"o": pouch, "color": "Black", "n": 5})); assert len(taken) == 5     # GM: 5 coins to the GM hand
gmz = next(z for z in g.Hands.getHands().values() if z.getValue() == "Black").getPosition()
assert all(abs(t[2] - gmz.z) < 1e-6 for t in taken)
taken.clear()
c.pouchTyped(to_lua({"o": pouch, "color": "Red", "n": 3})); assert not taken            # nobody else draws from it
coin = g.makeObj(to_lua({"Name": "Custom_Model", "GUID": "c01n00", "Transform": {"posX": W / 2 + 5, "posY": 2, "posZ": 0}}))
c.onObjectLeaveContainer(pouch, coin)
assert coin.invisible and coin.hasTag("gm")
assert all(s["sky"].endswith(".jpg") and len(s["light"]) == 4 for s in scenes)

# players can't touch scenery or NPCs (GM only), but can roll any dice and handle their own kit
red, gmp = to_lua({"color": "Red"}), to_lua({"color": "Black"})
barrel = g.makeObj(to_lua({"Name": "Custom_Model", "GUID": "ba44e1", "Tags": ["scene"]}))
die = g.makeObj(to_lua({"Name": "Die_6", "GUID": "d1e600", "Tags": ["scene"]}))
die.type = "Dice"
assert c.onPlayerAction(red, "PickUp", to_lua([giants[0]])) is False and c.onPlayerAction(red, "PickUp", to_lua([barrel])) is False
assert c.onPlayerAction(gmp, "PickUp", to_lua([giants[0]])) is True
assert c.onPlayerAction(red, "PickUp", to_lua([die])) is True and c.onPlayerAction(red, "PickUp", to_lua([hero])) is True
blue = to_lua({"color": "Blue"})
assert c.onPlayerAction(blue, "PickUp", to_lua([hero])) is False                # other heroes' kit is off limits
assert c.onPlayerAction(gmp, "PickUp", to_lua([hero])) is True
red_hp = lambda: json.loads(c.onSave())["hp"]["Red"]
before = red_hp()
c.hpRedDown(None, "Blue", False); assert red_hp() == before                    # nor their HP buttons
c.hpRedDown(None, "Red", False); assert red_hp() == before - 1
c.setHP("Red", before)

sheet = [o for o in g.getObjectsWithTag("kit").values() if o.data.Name == "Custom_Tile" and "Wren" in o.data.Nickname][0]
assert sheet.data.Transform.rotY == 180, "Red's sheet faces the player (tile images are flipped vs hands)"

gm = g.mkplayer("gm", "White")
c.pick(gm, None, "pick_Black")                       # the Game Master option
assert gm.color == "Black" and g.UIattr["pick_Black.interactable"] == "false"
bob = g.mkplayer("bob", "White")
c.pick(bob, None, "pickimg_Red")                     # clicking the portrait works too
assert bob.color == "Red" and g.UIattr["pick_Red.interactable"] == "false"
hand = lambda col: len(list(g.Player[col].getHandObjects().values()))
assert hand("Red") == 6
eve = g.mkplayer("eve", "White")
c.pick(eve, None, "pick_Red")                        # taken -> refused
assert eve.color == "White" and "taken" in g.log[len(g.log)]

played = next(o for o in g.getObjectsWithTag("card_Red").values() if o.inHand == "Red")
played.inHand = None                                  # card played on the table
assert hand("Red") == 5
c[down](shield, "Red", True)
c.rest()
assert shield.buttons[1].label == "18"
assert played.pos is not None                          # sent back toward the hand
assert "HP back to full" in g.log[len(g.log)]

# ---- same version on reload: nothing reinstalled
ctl.marker = "original"
g.loader.onLoad("")
assert g.getObjectFromGUID(CTL).marker == "original"

# ---- new version pushed: controller replaced, scene kept, kits respawned, Red re-dealt, no duplicates
c.setScene(3)
game["version"] = "newer"
g.FILES = to_lua({"game.json": json.dumps(game),
                  "controller.lua": controller_lua.replace("VERSION = DATA.version", 'VERSION = "newer"')})
g.loader.onLoad("")
ctl2 = g.getObjectFromGUID(CTL)
assert ctl2.marker is None and ctl2.getVar("VERSION") == "newer"
assert g.UIattr["sceneTitle.text"] == scenes[2]["title"]
assert count("kit") == 25 and hand("Red") == 6 and count("card_Red") == 6, (count("kit"), hand("Red"))  # Red deck dealt: 20 - 1 + 6
assert len(g.handzones) == 5   # the GM's spawned hand zone is reused, not duplicated
assert len(list(g.tabs.values())) == 1 + len(scenes)

# ---- npc.lua on a giant
giant = next(o for o in scenes[1]["spawns"] if o.get("Nickname") == "Giant" and o["Name"] == "rpg_CYCLOP")
npc = LuaRuntime(unpack_returned_tuples=True)
ng = npc.globals()
ng.JSON = npc.table_from({})
ng.JSON.decode = lambda s: npc.table_from({k: (npc.table_from([npc.table_from(a) for a in v]) if k == "attacks" else v)
                                          for k, v in json.loads(s).items()})
npc.execute("""
log, attrs, died, swung = {}, {}, 0, 0
self = { UI = { setXml = function(x) xml = x end, setAttribute = function(i, k, v) attrs[i .. "." .. k] = tostring(v) end },
         getRotation = function() return { x = 0, y = 270, z = 0 } end,
         RPGFigurine = { die = function() died = died + 1 end, attack = function() swung = swung + 1 end } }
function broadcastToAll(m) log[#log+1] = m end
function broadcastToColor(m, c) log[#log+1] = c .. ": " .. m end
-- MoonSharp (TTS) throws where real Lua returns nil when a base is given
local _tonumber = tonumber
function tonumber(v, base)
  if base then assert(tostring(v):match("^%d+$"), "MoonSharp tonumber throws on " .. tostring(v)) end
  return _tonumber(v, base)
end
""")
npc.execute(giant["LuaScript"])
ng.onLoad(giant["LuaScriptState"])
assert "ProgressBar" in ng.xml and ng.xml.count("<Button") == len(json.loads(giant["LuaScriptState"])["attacks"])
assert 'rotation="90 -90 90"' in ng.xml            # upright bar facing the way the figure faces
ng.applyDamage(None, "+12")
assert ng.attrs["bar.percentage"] == "80" and ng.attrs["hp.text"].startswith("48/60")
ng.applyDamage(None, "100")
assert ng.died == 1 and "falls" in ng.log[1]
ng.applyDamage(None, "-10")
assert ng.died == 2 and ng.attrs["hp.text"].startswith("10/60")
for junk in ("abc", "", " ", "--3", None):              # ignored, no error
    ng.applyDamage(None, junk)
assert ng.attrs["hp.text"].startswith("10/60")
for _ in range(200):
    ng.attack(npc.table_from({"color": "Black"}), None, "a1")
msgs = list(ng.log.values())
assert all("to hit" in m and "dmg" in m for m in msgs[2:]) and ng.swung == 200
for n in range(20):
    t, detail = ng.roll("2d8+4")
    assert 6 <= t <= 20 and detail.endswith("+4")

# princess starts lying down at 4 HP; healing stands her up (one die() toggle), not the other way round
isolde = next(o for s in scenes for o in s["spawns"] if o.get("Nickname") == "Princess Isolde")
assert isolde["RPGdead"]
npc.execute("died, log = 0, {}")
ng.onLoad(isolde["LuaScriptState"])
ng.applyDamage(None, "-8")
assert ng.died == 1 and "gets back up" in ng.log[1] and ng.attrs["hp.text"].startswith("12/20")
ng.applyDamage(None, "3")
assert ng.died == 1                                      # still standing, no toggle
print("ok -", msgs[-1])
