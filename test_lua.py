"""Runs global.lua and npc.lua from the built save against a stubbed TTS API (lupa).
Catches Lua errors and logic slips before a trip to the TTS PC.  python test_lua.py"""
import json
from lupa import LuaRuntime

save = json.load(open("Holst.json"))
lua = LuaRuntime(unpack_returned_tuples=True)
g = lua.globals()


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


lua_type = lua.eval("type")
g.JSON = to_lua({})
g.JSON.decode = lambda s: to_lua(json.loads(s))
g.JSON.encode = lambda t: json.dumps(to_py(t))

lua.execute("""
log = {}
function broadcastToAll(m) log[#log+1] = m end
function broadcastToColor(m, c) log[#log+1] = c .. ": " .. m end
UIattr = {}
UI = { setAttribute = function(id, k, v) UIattr[id .. "." .. k] = tostring(v) end }
MusicPlayer = { setCurrentAudioclip = function(t) MusicPlayer.url = t.url end, pause = function() end,
                play = function() end, player_status = "Ready" }
Wait = { time = function(f) f() end, condition = function(f, c) if c() then f() end end }
function Vector(x, y, z) return setmetatable({x=x, y=y, z=z}, {__add = function(a, b) return Vector(a.x+b.x, a.y+b.y, a.z+b.z) end}) end
objects = {}
function makeObj(d)
  local o = {data = d, tags = {}, type = d.Name == "Deck" and "Deck" or (d.Name == "Card" and "Card" or "Other"), dealt = {}}
  for _, t in ipairs(d.Tags or {}) do o.tags[t] = true end
  function o.getGUID() return d.GUID end
  function o.hasTag(t) return o.tags[t] == true end
  function o.destruct() objects[d.GUID] = nil end
  function o.setLock(v) o.locked = v end
  function o.setPositionSmooth(p) o.pos = p end
  function o.setRotation(r) end
  function o.setRotationSmooth(r) end
  function o.getObjects() return d.ContainedObjects end
  function o.deal(n, c)
    for _, cd in ipairs(d.ContainedObjects) do local k = makeObj(cd); k.inHand = c end
    objects[d.GUID] = nil
  end
  o.Counter = { setValue = function(v) o.counter = v end }
  objects[d.GUID] = o
  return o
end
function spawnObjectData(p) local o = makeObj(p.data); if p.callback_function then p.callback_function(o) end; return o end
function getObjectFromGUID(g) return objects[g] end
function getObjectsWithTag(t) local r = {} for _, o in pairs(objects) do if o.hasTag(t) then r[#r+1] = o end end return r end
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
  function p.changeColor(c) seated[p.color] = nil; seated[c] = name; p.color = c; onPlayerChangeColor(c) end
  return p
end
""")

for o in save["ObjectStates"]:
    g.makeObj(to_lua(o))
lua.execute(save["LuaScript"])
g.onLoad("")
count = lambda tag: len(list(g.getObjectsWithTag(tag).values()))
assert count("scene") == 1, count("scene")          # title: just the map

for i, s in enumerate(save["LuaScript"] and json.loads(save["LuaScript"].split("[==[")[1].split("]==]")[0])["scenes"], 1):
    g.setScene(i)
    assert count("scene") == len(s["spawns"]), (i, count("scene"))
    assert g.MusicPlayer.url == s["music"]["url"]
    assert g.UIattr["sceneTitle.text"] == s["title"]
g.revealAll()
assert count("fog") == 0

bob = g.mkplayer("bob", "White")
g.pick(bob, None, "pick_Red")
assert bob.color == "Red" and g.UIattr["pick_Red.interactable"] == "false"
hand = lambda c: len(list(g.Player[c].getHandObjects().values()))
assert hand("Red") == 6
eve = g.mkplayer("eve", "White")
g.pick(eve, None, "pick_Red")                        # taken -> refused
assert eve.color == "White" and "taken" in g.log[len(g.log)]

played = next(o for o in g.getObjectsWithTag("card_Red").values() if o.inHand == "Red")
played.inHand = None                                  # card played on the table
assert hand("Red") == 5
g.rest()
assert played.pos is not None                          # sent back toward the hand
assert "HP back to full" in g.log[len(g.log)]

# ---- npc.lua on a giant
giant = next(o for o in save["LuaScript"] and json.loads(save["LuaScript"].split("[==[")[1].split("]==]")[0])["scenes"][1]["spawns"]
             if o.get("Nickname") == "Giant raider")
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
scenes = json.loads(save["LuaScript"].split("[==[")[1].split("]==]")[0])["scenes"]
isolde = next(o for s in scenes for o in s["spawns"] if o.get("Nickname") == "Princess Isolde")
assert isolde["RPGdead"]
npc.execute("died, log = 0, {}")
ng.onLoad(isolde["LuaScriptState"])
ng.applyDamage(None, "-8")
assert ng.died == 1 and "gets back up" in ng.log[1] and ng.attrs["hp.text"].startswith("12/20")
ng.applyDamage(None, "3")
assert ng.died == 1                                      # still standing, no toggle
print("ok -", msgs[-1])
