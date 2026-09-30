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
hands = {}
Notes = { getNotebookTabs = function() local r = {} for i, t in ipairs(tabs) do r[i] = {index = i - 1, title = t.title} end return r end,
          removeNotebookTab = function(i) table.remove(tabs, i + 1) end,
          addNotebookTab = function(t) tabs[#tabs + 1] = t end }
MusicPlayer = { setCurrentAudioclip = function(t) MusicPlayer.url = t.url end, pause = function() end,
                play = function() end, player_status = "Ready" }
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
function makeObj(d)
  local o = {data = d, tags = {}, type = d.Name == "Deck" and "Deck" or (d.Name == "Card" and "Card" or "Other")}
  for _, t in ipairs(d.Tags or {}) do o.tags[t] = true end
  function o.getGUID() return d.GUID end
  function o.hasTag(t) return o.tags[t] == true end
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
    if k == "getHandObjects" then return function() local r = {} for _, o in pairs(objects) do if o.inHand == c then r[#r+1] = o end end return r end end
    if k == "getHandTransform" then return function() return {position = Vector(0, 0, 0), rotation = {0, 0, 0}} end end
    if k == "setHandTransform" then return function(t) hands[c] = t end end
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
assert set(to_py(g.hands).keys()) == {"Red", "Blue", "Green", "Purple"}
for col, t in to_py(g.hands).items():
    assert abs(t["position"][2]) > D / 2, (col, "hand zone should sit past the table edge")

scenes = to_py(c.DATA.scenes)
for i, s in enumerate(scenes, 1):
    c.setScene(i)
    assert count("scene") == len(s["spawns"]), (i, count("scene"))
    assert g.tableURL == s["table"]
    if os.environ.get("DUMP"):          # object list for preview.py (Blender)
        dump.append({"title": s["title"], "key": s["table"].rsplit("_", 1)[1][:-4], "objects": [
            {"name": o.data.Name, "nick": o.data.Nickname, "mesh": (to_py(o.data.CustomMesh) or {}).get("MeshURL", ""),
             "tex": (to_py(o.data.CustomMesh) or {}).get("DiffuseURL", ""), "t": to_py(o.data.Transform),
             "dead": bool(o.data.RPGdead)} for o in g.getObjectsWithTag("scene").values()] + [
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
fig = list(g.getObjectsWithTag("fig_Red").values())[0]
assert abs(fig.pos[3] - scenes[-1]["heroes"][0][1] * SQ) < 1e-9       # heroes moved to the last scene
if os.environ.get("DUMP"):
    json.dump({"W": W, "D": D, "TOP": TOP, "SQ": SQ, "scenes": dump}, open(os.environ["DUMP"], "w"))
c.revealAll()
assert count("fog") == 0

bob = g.mkplayer("bob", "White")
c.pick(bob, None, "pick_Red")
assert bob.color == "Red" and g.UIattr["pick_Red.interactable"] == "false"
hand = lambda col: len(list(g.Player[col].getHandObjects().values()))
assert hand("Red") == 6
eve = g.mkplayer("eve", "White")
c.pick(eve, None, "pick_Red")                        # taken -> refused
assert eve.color == "White" and "taken" in g.log[len(g.log)]

played = next(o for o in g.getObjectsWithTag("card_Red").values() if o.inHand == "Red")
played.inHand = None                                  # card played on the table
assert hand("Red") == 5
c.rest()
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
assert len(list(g.tabs.values())) == 1 + len(scenes)

# ---- npc.lua on a giant
giant = next(o for o in scenes[1]["spawns"] if o.get("Nickname") == "Giant raider")
npc = LuaRuntime(unpack_returned_tuples=True)
ng = npc.globals()
ng.JSON = npc.table_from({})
ng.JSON.decode = lambda s: npc.table_from({k: (npc.table_from([npc.table_from(a) for a in v]) if k == "attacks" else v)
                                          for k, v in json.loads(s).items()})
npc.execute("""
log, attrs, died, swung = {}, {}, 0, 0
self = { UI = { setXml = function(x) xml = x end, setAttribute = function(i, k, v) attrs[i .. "." .. k] = tostring(v) end },
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
assert "ProgressBar" in ng.xml and ng.xml.count("<Button") == 3
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
