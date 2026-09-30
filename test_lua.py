"""Runs the TTS scripts against a stubbed TTS API (lupa): loader.lua from Holst.json downloads game.json,
spawns the controller (game.lua), whose scenes spawn NPCs running npc.lua. Each object script gets its own
environment, like in TTS. Catches Lua errors and logic slips before a trip to the TTS PC.  python test_lua.py"""
import json
from lupa import LuaRuntime

save = json.load(open("Holst.json"))
game = json.load(open("game.json"))
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
g.JSON.decode = lambda s: to_lua(json.loads(s))
g.JSON.encode = lambda t: json.dumps(to_py(t))
g.GAME_TEXT = json.dumps(game)

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
       setXml = function(x, assets) UIxml, UIassets = x, assets end }
tabs = {}
Notes = { getNotebookTabs = function() local r = {} for i, t in ipairs(tabs) do r[i] = {index = i - 1, title = t.title} end return r end,
          removeNotebookTab = function(i) table.remove(tabs, i + 1) end,
          addNotebookTab = function(t) tabs[#tabs + 1] = t end }
MusicPlayer = { setCurrentAudioclip = function(t) MusicPlayer.url = t.url end, pause = function() end,
                play = function() end, player_status = "Ready" }
Wait = { time = function(f) f() end, frames = function(f) f() end, condition = function(f, c) if c() then f() end end }
WebRequest = { get = function(url, cb) requested = url; cb({ text = GAME_TEXT, response_code = 200, is_error = false }) end }
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
assert g.requested.startswith("https://raw.githubusercontent.com/Wngui/giants-of-holst/main/game.json?t=")
ctl = g.getObjectFromGUID(game["controller"]["GUID"])
assert ctl and ctl.getVar("VERSION") == game["version"]
c = ctl.env
assert 'onClick="%s/pick"' % game["controller"]["GUID"] in g.UIxml
assert len(list(g.tabs.values())) == 1 + len(c.DATA.scenes)
count = lambda tag: len(list(g.getObjectsWithTag(tag).values()))
assert count("scene") == 1 and count("kit") == 20, (count("scene"), count("kit"))   # title map + 4 hero kits

scenes = json.loads(game["controller"]["LuaScript"].split("[==[")[1].split("]==]")[0])["scenes"]
for i, s in enumerate(scenes, 1):
    c.setScene(i)
    assert count("scene") == len(s["spawns"]), (i, count("scene"))
    assert g.MusicPlayer.url == s["music"]["url"]
    assert g.UIattr["sceneTitle.text"] == s["title"]
fig = list(g.getObjectsWithTag("fig_Red").values())[0]
assert fig.pos[3] == scenes[-1]["heroes"][0][2]                       # heroes moved to the last scene
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
assert g.getObjectFromGUID(game["controller"]["GUID"]).marker == "original"

# ---- new version pushed: controller replaced, scene kept, kits respawned, Red re-dealt, no duplicates
c.setScene(3)
game["version"] = "newer"
game["controller"]["LuaScript"] = game["controller"]["LuaScript"].replace(
    'VERSION = DATA.version', 'VERSION = "newer"')
g.GAME_TEXT = json.dumps(game)
g.loader.onLoad("")
ctl2 = g.getObjectFromGUID(game["controller"]["GUID"])
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
