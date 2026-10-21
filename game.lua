-- The Giants of Holst: GM panel, scene switching, class pick, rest.
-- Runs on the hidden controller object that loader.lua downloads and (re)spawns; the save file itself never changes.
-- build.py replaces the DATA line with the generated scene/hero data.
DATA = {} --@DATA@
VERSION = DATA.version

local scene, setupDone, hp = 1, {}, {}
local order, turn, searched = {}, 0, {}   -- initiative strip; containers already searched (by GUID)
local music, fighting = nil, false   -- the track playing; battle mode (grid, NPC bars, battle music)
local tints = {}   -- hidden objects' own tint (hide() makes them see-through for the GM)
local T, SQ   -- measured table: centre/top/width/depth, and world units per grid square

function onLoad(saved)
    local s = saved ~= "" and JSON.decode(saved) or {}
    MusicPlayer.repeat_track = true
    if Tables.getTable() ~= "Table_Custom" then   -- older saves start on the RPG table
        Tables.setTable("Table_Custom")
        Tables.setCustomURL(DATA.scenes[s.scene or 1].table)
        Wait.time(function() start(s) end, 1)
    else
        start(s)
    end
end

function start(s)
    measure()
    if s.version == VERSION then
        scene, setupDone, hp, turn, searched = s.scene, s.setupDone, s.hp or {}, s.turn or 0, s.searched or {}
        music, fighting = s.music, s.fighting or false
        Wait.frames(function() restore(s.order or {}) end, 10)   -- once every object has loaded
    else
        install(s.scene or 1)
    end
    Wait.frames(refreshPick, 15)   -- the loader has just set the UI XML; give TTS a moment to build it
    Wait.time(applyHands, 2, 15)
    Wait.time(storm, 20, -1)
    preload()   -- TTS resets hand zones a few seconds after the table switch: keep putting them back
end

function onSave()
    local saved = {}
    for _, e in ipairs(order) do
        local guids = {}
        for _, o in ipairs(e.objs) do if not o.isDestroyed() then guids[#guids + 1] = o.getGUID() end end
        saved[#saved + 1] = { name = e.name, roll = e.roll, hero = e.hero, art = e.art, guids = guids }
    end
    return JSON.encode({ version = VERSION, scene = scene, setupDone = setupDone, hp = hp, order = saved, turn = turn,
                         searched = searched, music = music, fighting = fighting })
end

-- Buttons, right-click menus and script visibility aren't kept in a save. Loading one (Ctrl+Z reloads the table too)
-- leaves objects bare, so they are put back on every object here, and the turn strip is redrawn.
function restore(saved)
    for _, o in ipairs(getObjectsWithTag("scene")) do
        if o.getName() == "Wicker Shield" then o.destruct() end   -- giveShield makes a fresh one that follows its giant
    end
    for _, o in ipairs(getAllObjects()) do
        decorate(o)
        if o.hasTag("hidden") then
            local t = o.getColorTint()
            tints[o.getGUID()] = { r = t.r, g = t.g, b = t.b, a = 1 }
            o.setInvisibleTo(PLAYERS)
        end
    end
    if music then play(music) end
    battle(fighting)
    order = {}
    for _, e in ipairs(saved) do
        e.objs = {}
        for _, g in ipairs(e.guids) do e.objs[#e.objs + 1] = getObjectFromGUID(g) end
        e.guids = nil
        order[#order + 1] = e
    end
    -- the loader resets the UI XML when its download lands: draw again for a few seconds
    -- ponytail: 10 s covers a slow GitHub fetch; a later fetch would blank the strip until the next turn
    Wait.time(function()
        refreshPick()
        drawTurns()
        UI.setAttribute("sceneTitle", "text", DATA.scenes[scene].title)
    end, 1, 10)
end

-- what each kind of object gets from the script when it spawns, and again after a reload
function decorate(o)
    if o.hasTag("trapgas") then                             -- the poison gas trap: the GM sets it off by hand
        o.addContextMenuItem("Release the gas", function(color)
            if color == "Black" then fxAt("gas_cloud", o.getPosition()) end
        end)
    end
    if o.hasTag("giant") then giantMenu(o) end
    if o.hasTag("shield") then giveShield(o) end
    if o.hasTag("search") then o.addContextMenuItem("Search", function(color) search(o, color) end) end
    if o.hasTag("fx") then o.interactable = false end      -- effects: no hover, no grabbing
    if o.hasTag("fxhide") then o.setInvisibleTo(ALL) end   -- sound-only effect: hide its carrier cube
    if o.hasTag("fxclear") then clearCube(o) end
    if o.hasTag("gm") then gmHide(o) end
    if o.hasTag("gmconsole") then console(o) end
    if o.hasTag("lootbag") then lootBag(o) end
    for _, color in ipairs(DATA.colors) do
        if o.hasTag("hp_" .. color) then hpShield(o, color, DATA.heroes[color].hp) end
    end
end

-- First load or a new version: fresh hero kits and notebook, same scene, re-deal to seated players.
function install(sceneIndex)
    for _, o in ipairs(getObjectsWithTag("kit")) do o.destruct() end
    for _, d in ipairs(DATA.kits) do
        local g = d.grid
        spawnObjectData({ data = placed(d), callback_function = function(o)
            decorate(o)
            -- the RPG thief spawns in its crouched sneak pose, which reads as stuck sitting: switch to its other mode
            -- ponytail: guess at what the mode toggle does; remove if the thief still (or now) sits
            if d.Name == "rpg_THIEF" and o.RPGFigurine then pcall(function() o.RPGFigurine.changeMode() end) end
        end })
    end
    -- GM desk: whatever still lies on it (tag "gm") and the screen are replaced; things handed out stay
    for _, tag in ipairs({ "gm", "gmscreen", "gmtable", "fxtest" }) do   -- fxtest: the old FX test cards, wherever they lie
        for _, o in ipairs(getObjectsWithTag(tag)) do o.destruct() end
    end
    for _, d in ipairs(DATA.gm) do
        spawnObjectData({ data = placed(d), callback_function = function(o)
            decorate(o)
        end })
    end
    -- the GM's hand: at the far side of the GM table, so "hover a bag/deck + number key" lands with the GM
    local tabs = Notes.getNotebookTabs()
    for i = #tabs, 1, -1 do Notes.removeNotebookTab(tabs[i].index) end
    for _, t in ipairs(DATA.notebook) do Notes.addNotebookTab(t) end
    setupDone = {}
    -- destroyed objects linger until the frame ends, so let the new kits settle before looking them up by tag
    Wait.frames(function()
        setScene(sceneIndex)
        for _, color in ipairs(DATA.colors) do onPlayerChangeColor(color) end
    end, 10)
end

-- Kit objects are found by tag, not GUID: respawning right after a destroy makes TTS hand out new GUIDs.
function kit(tag, typ)
    for _, o in ipairs(getObjectsWithTag(tag)) do
        if not typ or o.type == typ then return o end
    end
end

-- ---------------------------------------------------------------- layout
-- Sizes come from the real table, so nothing is placed off the edge or in mid-air.
function measure()
    local b = Tables.getTableObject().getBounds()
    local L = DATA.layout
    T = { cx = b.center.x, cz = b.center.z, top = b.center.y + b.size.y / 2,
          w = b.size.x * L.surface, d = b.size.z * L.surface }
    SQ = T.w * L.art_w / L.cols
end

function world(x, z, lift)
    return { T.cx + x * SQ, T.top + (lift or 0), T.cz + z * SQ }
end

-- each player's corner of the wooden border: Red bottom-left, Blue bottom-right, Green top-right, Purple top-left
function corner(color)
    local sx = (color == "Red" or color == "Purple") and -1 or 1
    local sz = (color == "Red" or color == "Blue") and -1 or 1
    return { x = T.cx + sx * T.w * DATA.layout.kit_x, sz = sz, ry = sz < 0 and 0 or 180, right = sz < 0 and 1 or -1 }
end

-- copy of a spawn with its "grid" placement turned into a world Transform
function placed(d)
    local o = {}
    for k, v in pairs(d) do o[k] = v end
    local g, t = d.grid, {}
    for k, v in pairs(d.Transform) do t[k] = v end
    o.grid, o.Transform = nil, t
    local L, p = DATA.layout, nil
    if g.role then                                    -- player kit in its corner
        local c, k = corner(g.color), SQ / 2
        local zs, zr = T.cz + c.sz * T.d * L.sheet_z, T.cz + c.sz * T.d * L.row_z
        local spots = { sheet = { 0, zs, 0.2 }, deck = { -4 * k, zr, 1 }, hp = { 0, zr, 0.3 },
                        d20 = { 4 * k, zr, 1 } }
        local s = spots[g.role]
        if g.role == "die" then   -- a row between the HP plaque and the sheet
            s = { (g.i - (g.n - 1) / 2) * 0.8 * SQ, T.cz + c.sz * T.d * L.dice_z, 1 }
        end
        p = { c.x + c.right * s[1], T.top + s[3], s[2] }
        t.rotY = c.ry
        if g.role == "deck" then                      -- same size as the GM's item cards (grid "tile" units: SQ / 2)
            for _, c in ipairs(d.ContainedObjects or {}) do
                c.Transform.scaleX, c.Transform.scaleY, c.Transform.scaleZ = SQ / 2, SQ / 2, SQ / 2
            end
            t.scaleX, t.scaleY, t.scaleZ = SQ / 2, SQ / 2, SQ / 2
        end
        if g.role == "d20" then                       -- players' own die: big enough to grab and read
            t.scaleX, t.scaleY, t.scaleZ = 1.8, 1.8, 1.8
        end
        if g.role == "die" then t.scaleX, t.scaleY, t.scaleZ = 1.3, 1.3, 1.3 end
        if g.role == "hp" then                        -- plaque 2.6 squares wide, turned to read from the seat
            t.scaleX, t.scaleY, t.scaleZ, t.rotY = SQ, SQ, SQ, c.ry + 180
        end
        if g.role == "sheet" then
            t.rotY = c.ry + 180                       -- tile images face the opposite way to hands
            local sc = T.w * L.sheet_w / L.tile_unit
            t.scaleX, t.scaleY, t.scaleZ = sc, 1, sc
        end
    else
        -- loose props drop a little, scenery spawns locked in place; figures are scaled to the grid (RPG kit figures fit a 2-unit square)
        p = world(g.x, g.z, g.ly and g.ly * SQ or g.lift or (g.k == "fig" and 1 or 0.3))
        for _, c in ipairs(g.inner and d.ContainedObjects or {}) do   -- coins etc. in bags: grid-sized too
            c.Transform.scaleX, c.Transform.scaleY, c.Transform.scaleZ = g.inner * SQ, g.inner * SQ, g.inner * SQ
        end
        local unit = (g.k == "model") and SQ or (g.k == "fx") and 1 or SQ / 2   -- effects: their own world size
        local s = g.s or { 1, 1, 1 }
        t.scaleX, t.scaleY, t.scaleZ = s[1] * unit, s[2] * unit, s[3] * unit
    end
    t.posX, t.posY, t.posZ = p[1], p[2], p[3]
    return o
end

-- ---------------------------------------------------------------- scenes
function onSceneButton(player, _, id)
    fadeToScene(tonumber(id:sub(7)))
end

-- GM scene buttons: everyone's screen fades to black, the scene switches in the dark, then fades back in
-- (the "fade" panel's show/hide animations, build.py)
function fadeToScene(i)
    UI.show("fade")
    Wait.time(function() setScene(i); viewAll(0) end, 0.2)   -- everyone's camera framed on the new scene, in the dark
    Wait.time(function() UI.hide("fade") end, 0.8)   -- a moment for the new table image and props to load
end

function setScene(i)
    tidy()
    pcall(function() Global.setDecals({}) end)   -- scorch marks belong to the old scene
    held = {}
    for _, o in ipairs(getObjectsWithTag("scene")) do o.destruct() end
    scene = i
    local s = DATA.scenes[i]
    Tables.setCustomURL(s.table)
    for _, d in ipairs(s.spawns) do
        spawnObjectData({ data = placed(d), callback_function = function(o)
            decorate(o)
            if o.hasTag("hidden") then
                o.setInvisibleTo(PLAYERS)
                Wait.frames(function() hide(o) end, 5)   -- tint/outline/bar once the figure and its script have loaded
            end
        end })
    end
    for n, color in ipairs(DATA.colors) do
        local fig = kit("fig_" .. color)
        if fig then
            local p = world(s.heroes[n][1], s.heroes[n][2], 1)
            fig.setPositionSmooth(p, false, true)
            if DATA.fog then Wait.frames(function() revealNear(p) end, 2) end   -- after the scene's NPCs have spawned
            fig.setRotationSmooth({ 0, 90, 0 })   -- face east, into the scene
        end
    end
    backdrop(s)
    highlightScene()
    UI.setAttribute("sceneTitle", "text", s.title)
    play(s.music)
    showGrid(false)   -- new scene, out of battle (its NPCs spawn with their bars off)
    broadcastToAll(s.title, { 0.94, 0.85, 0.63 })
end

-- Before a scene change: whatever lies on the map that isn't the scene's own (played cards, coins, items, dice...) goes
-- to a pile on the east border, between the two right-hand player kits. Hero figures stay (setScene moves them), and so
-- do the players' own dice and sheets; played hero cards go to the pile (REST returns them to hands).
local KEEP = { "scene", "fx", "fxcache", "gm", "gmtable", "gmscreen", "gmconsole", "loot" }   -- loot: the gold die
function onMap(q)
    return math.abs(q.x - T.cx) <= T.w * DATA.layout.art_w / 2 and math.abs(q.z - T.cz) <= DATA.layout.rows * SQ / 2
end

function tidy()
    local n = 0
    for _, o in ipairs(getObjects()) do
        local keep = o == self or o.type == "Hand" or o.type == "Scripting" or o.type == "Fog" or not onMap(o.getPosition())
        for _, tag in ipairs(KEEP) do keep = keep or o.hasTag(tag) end
        for _, c in ipairs(DATA.colors) do keep = keep or o.hasTag("fig_" .. c) end
        keep = keep or (o.hasTag("kit") and o.type ~= "Card" and o.type ~= "Deck")   -- a player's own d20/sheet stays
        if not keep then
            n = n + 1
            o.setPositionSmooth({ T.cx + T.w * DATA.layout.kit_x, T.top + 1 + n * 0.4, T.cz + ((n % 3) - 1) * SQ }, false, true)
        end
    end
end

-- ---------------------------------------------------------------- hidden enemies (instead of TTS's fog box)
PLAYERS = { "White", "Brown", "Red", "Orange", "Yellow", "Green", "Teal", "Blue", "Purple", "Pink", "Grey" }

-- Hidden from players; for the GM it turns see-through so it reads as hidden at a glance (no outline).
function hide(o)
    o.setInvisibleTo(PLAYERS)
    o.addTag("hidden")
    local t = o.getColorTint()
    tints[o.getGUID()] = tints[o.getGUID()] or t
    o.setColorTint({ r = t.r, g = t.g, b = t.b, a = 0.35 })
    if o.getLuaScript() ~= "" then o.call("setHidden", { hidden = true }) end   -- NPCs: bar GM-only too
end

function reveal(o)
    if o.hasTag("boss") and o.hasTag("hidden") then tremor(o.getPosition()) end   -- the chainmaster steps out: the ground shakes
    o.setInvisibleTo({})
    o.removeTag("hidden")
    if tints[o.getGUID()] then o.setColorTint(tints[o.getGUID()]) end
    if o.getLuaScript() ~= "" then o.call("setHidden", { hidden = false }) end
end

-- GM: select NPCs/props (or hover one) and toggle them hidden <-> shown. From either GM menu or the hotkey.
function toggleSelected(player, hovered)
    local list = Player.Black.getSelectedObjects()
    if #list == 0 and hovered then list = { hovered } end
    for _, o in ipairs(list) do
        if o.hasTag("hidden") then reveal(o) else hide(o) end
    end
end

-- NPCs tagged "manual" (Holst City's street kids) only show up when the GM presses their Reveal button
function revealAll()
    for _, o in ipairs(getObjectsWithTag("hidden")) do
        if not o.hasTag("manual") then reveal(o) end
    end
end

function revealNear(p)
    local r = DATA.layout.reveal * SQ
    for _, o in ipairs(getObjectsWithTag("hidden")) do
        local q = o.getPosition()
        if not o.hasTag("manual") and (q.x - p[1]) ^ 2 + (q.z - p[3]) ^ 2 <= r * r then reveal(o) end
    end
end

-- Players only handle their own things (hero, cards, sheet, HP, dice) and what the GM hands them (gold, items).
-- Scenery, NPCs and the GM table are the GM's: any player action on them is refused. Dice stay free to roll,
-- the Baron's Bones included. Returning false from onPlayerAction cancels the action in TTS.
function onPlayerAction(player, _, targets)
    if player.color == "Black" then return true end
    for _, o in ipairs(targets or {}) do
        local gmOnly = o.hasTag("scene") or o.hasTag("gm") or o.hasTag("gmtable") or o.hasTag("gmscreen")
        if gmOnly and o.type ~= "Dice" then return false end
        for _, c in ipairs(DATA.colors) do   -- another hero's figure, sheet or HP counter
            if c ~= player.color and (o.hasTag("fig_" .. c) or o.hasTag("sheet_" .. c) or o.hasTag("hp_" .. c)) then
                return false
            end
        end
    end
    return true
end

function onObjectDrop(player, o)
    cardPlayed(o)
    for _, color in ipairs(DATA.colors) do
        if o.hasTag("fig_" .. color) then
            local q = o.getPosition()
            if DATA.fog then revealNear({ q.x, q.y, q.z }) end
        end
    end
    -- GM desk: what the GM puts down on it disappears for players; what the GM puts anywhere else appears
    if player == "Black" then
        if onDesk(o.getPosition()) then
            if not o.hasTag("gm") then o.addTag("gm"); gmHide(o) end
        elseif o.hasTag("gm") then
            gmShow(o)
        end
    end
end

-- ---------------------------------------------------------------- particle effects (build.py FX)
-- An effect bundle spawned at a point; a one-shot fires its trigger once loaded and is removed after its lifetime.
-- Lasting ones (smoke cloud) are tagged "scene": the GM deletes them, or the next scene does.
function fxAt(name, p, quiet)   -- quiet: without its sound
    local f = DATA.fx[name]
    if not f or not T then return end
    if f.snd and not quiet then fxAt(f.snd, p) end
    if name == "fireball" then Wait.time(function() scorch(p) end, 0.8) end
    spawnObjectData({ data = { Name = "Custom_Assetbundle", Locked = true, Tooltip = false, Tags = { f.life and "fx" or "scene" },
        Transform = { posX = p.x, posY = T.top + f.lift * SQ, posZ = p.z, rotX = 0, rotY = 0, rotZ = 0,
                      scaleX = f.s, scaleY = f.s, scaleZ = f.s },
        CustomAssetbundle = { AssetbundleURL = f.url, AssetbundleSecondaryURL = "", MaterialIndex = 0, TypeIndex = 0,
                              LoopingEffectIndex = f.loop } },
        callback_function = function(o)
            if f.clear then clearCube(o) end
            if f.life then o.interactable = false end   -- lasting ones (smoke cloud) stay grabbable so the GM can delete them
            if f.hide then o.setInvisibleTo(ALL) end   -- sound-only bundle: its carrier cube stays out of sight
            if f.trig then
                local trig = type(f.trig) == "table" and f.trig[math.random(#f.trig)] or f.trig   -- a list: pick one
                Wait.condition(function() pcall(function() o.AssetBundle.playTriggerEffect(trig) end) end,
                               function() return o.isDestroyed() or not o.loading_custom end, 20)
            end
            if f.life then Wait.time(function() if not o.isDestroyed() then o.destruct() end end, f.life) end
        end })
end

ALL = { "White", "Brown", "Red", "Orange", "Yellow", "Green", "Teal", "Blue", "Purple", "Pink", "Grey", "Black" }

-- storm scenes: every 20 s, half the time, lightning: the table light flashes twice, the thunder follows
function storm()
    local s = DATA.scenes[scene]
    if s and s.storm and T and math.random() < 0.5 then
        flash()
        local p = { x = T.cx + (math.random() - 0.5) * 16 * SQ, z = T.cz + (math.random() - 0.5) * 10 * SQ }
        Wait.time(function() fxAt("thunder", p) end, 0.4 + math.random() * 1.2)
    end
end

function flash()
    pcall(function()
        local base = Lighting.light_intensity
        local function set(v) Lighting.light_intensity = v; Lighting.apply() end
        set(base * 3)
        Wait.time(function() set(base) end, 0.08)
        Wait.time(function() set(base * 2.2) end, 0.2)
        Wait.time(function() set(base) end, 0.3)
    end)
end

-- The effect pack's carrier cube shows while the bundle loads and until tint alpha 0 takes (the pack's advice; set too
-- early it doesn't stick). So: invisible to everyone until loaded, then alpha 0 and shown. Found with test cards A-G.
function clearCube(o)
    o.setInvisibleTo(ALL)
    Wait.condition(function()
        Wait.time(function()
            if o.isDestroyed() then return end
            o.setColorTint({ r = 1, g = 1, b = 1, a = 0 })
            o.setInvisibleTo({})
        end, 0.3)
    end, function() return o.isDestroyed() or not o.loading_custom end, 30)
end

-- One idle copy of every effect bundle under the table, invisible and silent, so later spawns come out of the cache
-- loaded at once (and their carrier cube can be cleared right away). The candle light is left out: it would shine.
-- Rebuilt on each load.
local IDLE = { [DATA.fx.fire.url] = 2, [DATA.fx.steam.url] = 2 }   -- "Fire Off" / "Steam Off"; the rest: 0, off/silent
function preload()
    for _, o in ipairs(getObjectsWithTag("fxcache")) do o.destruct() end
    local seen = { [DATA.fx.candle.url] = true }
    for _, f in pairs(DATA.fx) do
        if not seen[f.url] and f.url:match("^https?://") then
            seen[f.url] = true
            spawnObjectData({ data = { Name = "Custom_Assetbundle", Locked = true, Tooltip = false, Tags = { "fxcache" },
                Transform = { posX = T.cx, posY = T.top - 30, posZ = T.cz, rotX = 0, rotY = 0, rotZ = 0,
                              scaleX = 0.1, scaleY = 0.1, scaleZ = 0.1 },
                CustomAssetbundle = { AssetbundleURL = f.url, AssetbundleSecondaryURL = "", MaterialIndex = 0, TypeIndex = 0,
                                      LoopingEffectIndex = IDLE[f.url] or 0 } },
                callback_function = function(o) o.setInvisibleTo(ALL); o.interactable = false end })
        end
    end
end

-- for npc.lua: fx { name =, guid = }
function fx(p)
    local o = getObjectFromGUID(p.guid)
    if o then fxAt(p.name, o.getPosition()) end
end

-- a hero card or item put face up on the map plays its effect there, once until REST picks it up again
local played = {}
function cardPlayed(o)
    if o.type ~= "Card" or o.is_face_down or played[o.getGUID()] or o.hasTag("gm") then return end
    Wait.frames(function()   -- once it has settled: a card dropped into a hand (rearranging it) plays nothing
        if o.isDestroyed() or played[o.getGUID()] then return end
        for _, z in ipairs(o.getZones() or {}) do
            if z.type == "Hand" then return end
        end
        played[o.getGUID()] = true
        fxAt(DATA.card_fx[o.getName()] or "swirl_white", o.getPosition())
    end, 3)
end

-- ---------------------------------------------------------------- GM desk
function onDesk(q) return q.x > T.cx + T.w / 2 end

function gmHide(o) o.setInvisibleTo(PLAYERS) end

function gmShow(o)
    o.setInvisibleTo({})
    o.removeTag("gm")
end

-- GM controls: the floating panel again, as object buttons on the dice tray laid out bottom left of the red mat
-- (positions from build.py, in squares relative to the tray). The current scene's button is lit gold.
-- Clicks from anyone but Black are ignored (the tray is hidden from players anyway).
-- ponytail: BTN = button units per local unit of the host object (full width), read off one screenshot
BTN = 300
local sceneButton, panel = {}, nil
local BROWN, GOLD, CREAM, INK = { 0.23, 0.16, 0.1 }, { 0.85, 0.65, 0.2 }, { 0.94, 0.85, 0.63 }, { 0.12, 0.08, 0.05 }
function noop() end
addHotkey("Toggle visibility (GM)", function(color, hovered)
    if color == "Black" then toggleSelected(Player[color], hovered) end
end)

function console(o)
    panel = o
    o.clearButtons()
    for i, b in ipairs(DATA.gm_buttons) do
        local fn = "noop"
        if b.kind ~= "title" then
            fn = "gmButton" .. i
            _G[fn] = function(_, color)
                if color ~= "Black" then return end
                if b.scene then fadeToScene(b.scene) else _G[b.fn](Player[color]) end
            end
        end
        o.createButton({ click_function = fn, function_owner = self, label = b.label, position = { b.x, 0.06, b.z },
                         rotation = { 0, 90, 0 }, width = b.w * BTN - 15, height = 0.44 * BTN,
                         font_size = (b.kind == "title" and 0.2 or 0.15) * BTN,
                         color = b.kind == "title" and { 0.1, 0.08, 0.06 } or BROWN, font_color = CREAM })
        if b.scene then sceneButton[b.scene] = i - 1 end   -- createButton indices start at 0
    end
    highlightScene()
end

function highlightScene()
    if not panel then return end
    for sc, i in pairs(sceneButton) do
        local on = sc == scene
        panel.editButton({ index = i, color = on and GOLD or BROWN, font_color = on and INK or CREAM })
    end
end

-- ---------------------------------------------------------------- HP plaques (instead of TTS counters)
-- A plaque at each seat, one row: [-] [HP] [+] (right-click: 5 at a time). REST refills it.
local shields = {}
function hpShield(o, color, max)
    shields[color] = o
    o.clearButtons()
    hp[color] = hp[color] or max
    o.createButton({ click_function = "noop", function_owner = self, label = tostring(hp[color]),
                     position = { 0, 0.12, 0 }, width = 0, height = 0, font_size = 0.5 * BTN, font_color = { 1, 0.95, 0.85 } })
    for k, d in ipairs({ -1, 1 }) do
        local fn = "hp" .. color .. (d < 0 and "Down" or "Up")
        _G[fn] = function(_, who, alt)   -- only that hero's player (or the GM) changes their HP
            if who == color or who == "Black" then setHP(color, hp[color] + d * (alt and 5 or 1)) end
        end
        -- the plaque is turned 180 to face its player, so local +x is their left: "-" goes there. Each button fills its
        -- end of the plaque (0.48..1.3 from the middle) and a little past it: big targets
        o.createButton({ click_function = fn, function_owner = self, label = d < 0 and "-" or "+",
                         position = { -d * 0.9, 0.12, 0 }, width = 0.95 * BTN, height = 0.9 * BTN, font_size = 0.8 * BTN,
                         color = { 0.15, 0.1, 0.07 }, font_color = { 1, 0.95, 0.85 } })
    end
end

function setHP(color, v)
    local max = DATA.heroes[color].hp
    hp[color] = math.max(0, math.min(max, v))
    if shields[color] then shields[color].editButton({ index = 0, label = tostring(hp[color]) }) end
end

-- ---------------------------------------------------------------- hands
-- Each player's hand lies along the bottom edge of their own sheet (the edge nearest them), taken from where the
-- sheet actually is, so dealt cards always land at that player's kit.
function handAtSheet(color, sheet)
    local c, p = corner(color), sheet.getPosition()
    local half = T.w * DATA.layout.sheet_w / 3             -- half the sheet's depth: it is 3:2, sheet_w of the table wide
    setHand(color, p.x, T.top + 1, p.z + c.sz * (half + 2.2), c.ry, { T.w * DATA.layout.sheet_w, 5, 4 })
end

-- Hand zones are objects (type "Hand", getValue() = owner colour, Hands.getHands() lists them). TTS resets them all to
-- the table's default seat layout after the RPG -> custom table switch on load, a few seconds later, overwriting a
-- one-off placement (cards then landed at the default zones: Green's default is where Aldric's sheet is). So the
-- zones are re-applied (applyHands) for a while after loading, before dealing and before REST. Every zone of a colour
-- is moved (deal() goes to hand 1), and one is spawned for a colour that has none (the GM).
function handZones(color)   -- nil if the zone API fails
    local ok, r = pcall(function()
        local r = {}
        for _, h in ipairs(Hands.getHands()) do
            if h.getValue() == color then r[#r + 1] = h end
        end
        return r
    end)
    return ok and r or nil
end

function applyHands()
    for _, color in ipairs(DATA.colors) do
        local sheet = kit("sheet_" .. color)
        if sheet then handAtSheet(color, sheet) end
    end
    setHand("Black", T.cx + T.w / 2 + DATA.layout.gm_hand * SQ, T.top + 4, T.cz, 270, { 12, 5, 4 })
end

function setHand(color, x, y, z, ry, scale)
    if pcall(moveZones, color, x, y, z, ry, scale) then return end
    pcall(function()   -- fallback if the zone API fails (setHandTransform is world space too: the getter agrees)
        Player[color].setHandTransform({ position = { x, y, z }, rotation = { 0, ry, 0 }, scale = scale })
    end)
end

local spawning = {}
function moveZones(color, x, y, z, ry, scale)
    local zones = assert(handZones(color))
    if #zones == 0 and not spawning[color] then
        spawning[color] = true
        spawnObject({ type = "HandTrigger", position = { x, y, z }, rotation = { 0, ry, 0 }, scale = scale,
                      callback_function = function(h) h.setValue(color); spawning[color] = nil end })
    end
    for _, h in ipairs(zones) do
        h.setPosition({ x, y, z })
        h.setRotation({ 0, ry, 0 })
        h.setScale(scale)
    end
end

-- coins out of a desk pouch, a card off a desk deck: hidden like their container until the GM hands them out
-- The gold pouch: TTS's own "hover + number" deals that many to every seated player. The pouch's own onNumberTyped
-- (only an object's own handler can cancel that) calls this: the GM gets n coins in hand to give to the right player.
function pouchTyped(p)
    local o, n = p.o, p.n
    if p.color ~= "Black" then return end
    local zone = (handZones("Black") or {})[1]
    if not zone then return end
    local z = zone.getPosition()
    for i = 1, n do
        o.takeObject({ position = { z.x + (i - 1) * 0.3 - (n - 1) * 0.15, z.y + 1 + i * 0.2, z.z }, smooth = false })
    end
end

function onObjectLeaveContainer(container, o)
    if container.hasTag("gm") then
        o.addTag("gm")
        gmHide(o)
    end
end

-- ---------------------------------------------------------------- mood: 360 backdrop + light colour per scene
-- pcall: these TTS calls can't be tested here; a failure must never stop the scene switch
local light0
function backdrop(s)
    pcall(function() Backgrounds.setCustomURL(s.sky) end)
    pcall(function()
        light0 = light0 or Lighting.light_intensity
        Lighting.light_intensity = light0 * s.light[4]
        Lighting.setLightColor(Color(s.light[1], s.light[2], s.light[3]))
        Lighting.apply()
    end)
end

-- ---------------------------------------------------------------- music
function play(track)
    music = track
    MusicPlayer.setCurrentAudioclip({ url = track.url, title = track.title })
    Wait.condition(function() MusicPlayer.play() end, function() return MusicPlayer.player_status == "Ready" end, 20)
end

function musicScene() play(DATA.scenes[scene].music); battle(false) end
function musicBattle() play(DATA.battle); battle(true) end

-- battle mode: grid on the map and NPC health bars on
function battle(on)
    fighting = on
    showGrid(on)
    for _, o in ipairs(getObjectsWithTag("npc")) do o.call("setBattle", { on = on }) end
end

-- battle grid over the map: one cell per map square, integer map coordinates at cell centres
function showGrid(on)
    local set = { type = 1, sizeX = SQ, sizeY = SQ, offsetX = T.cx + SQ / 2, offsetY = 1, offsetZ = T.cz + SQ / 2,
                  thick_lines = false, opacity = 0.5, snapping = 0, show_lines = on }
    for _, k in ipairs({ "type", "sizeX", "sizeY", "offsetX", "offsetY", "offsetZ", "thick_lines", "opacity",
                         "snapping", "show_lines" }) do
        pcall(function() Grid[k] = set[k] end)   -- one unknown field must not stop the rest
    end
end

-- ---------------------------------------------------------------- class pick
function pick(player, _, id)
    local color = id:match("_(%a+)$")   -- pick_<colour> button or pickimg_<colour> portrait; Black = Game Master
    if Player[color].seated then
        broadcastToColor("That adventurer is taken, pick another.", player.color, { 1, 0.6, 0.2 })
        return
    end
    player.changeColor(color)
end

function onPlayerChangeColor(color)
    refreshPick()
    if DATA.heroes[color] and Player[color].seated and not setupDone[color] then
        setupDone[color] = true
        applyHands()
        Wait.frames(function() setupHero(color) end, 5)   -- zones moved first, then deal into them
    end
end

function onPlayerDisconnect() refreshPick() end

function refreshPick()
    local gm = Player.Black
    UI.setAttribute("pick_Black", "text", gm.seated and ("GM - " .. gm.steam_name) or "Game Master")
    UI.setAttribute("pick_Black", "interactable", gm.seated and "false" or "true")
    for _, color in ipairs(DATA.colors) do
        local h = DATA.heroes[color]
        local p = Player[color]
        UI.setAttribute("pick_" .. color, "text", p.seated and (h.short .. " - " .. p.steam_name) or h.short)
        UI.setAttribute("pick_" .. color, "interactable", p.seated and "false" or "true")
    end
end

-- Sheet, counter and d20 already sit at the seat; deal the 6 cards into the hand.
function setupHero(color)
    local h = DATA.heroes[color]
    local deck = kit("card_" .. color, "Deck")
    if deck then deck.deal(6, color) end
    broadcastToAll(Player[color].steam_name .. " is " .. h.name .. ".", { 0.94, 0.85, 0.63 })
end

-- ---------------------------------------------------------------- rest
-- Every played card goes back to its owner's hand, HP counters reset to max.
function rest()
    applyHands()
    for _, color in ipairs(DATA.colors) do
        local h = DATA.heroes[color]
        setHP(color, h.hp)
        if Player[color].seated then
            local inHand = {}
            for _, o in ipairs(Player[color].getHandObjects()) do inHand[o.getGUID()] = true end
            local hand = (handZones(color) or {})[1]
            for _, card in ipairs(getObjectsWithTag("card_" .. color)) do
                if hand and card.type == "Card" and not inHand[card.getGUID()] then
                    local p = hand.getPosition()
                    card.setRotation(hand.getRotation())
                    card.setPositionSmooth({ p.x, p.y + 2, p.z }, false, true)
                elseif card.type == "Deck" then
                    card.deal(#card.getObjects(), color)
                end
            end
        end
    end
    played = {}
    for _, color in ipairs(DATA.colors) do
        local fig = kit("fig_" .. color)
        if fig then fxAt("swirl_yellow", fig.getPosition()) end
    end
    broadcastToAll("REST: HP back to full, all cards return to your hand.", { 0.5, 0.9, 0.5 })
end

-- ---------------------------------------------------------------- turn order
-- GM "Initiative": each kind of visible, standing NPC that can fight rolls one d20 ("Giant x3"); all four heroes take
-- the face their own d20 shows right now (+ Agility). The strip on top shows the order, current turn lit (and its
-- figures highlighted); "Next turn" moves on, "End fight" clears it. Ties go to the heroes.
function initiative()
    musicBattle()   -- battle mode: battle music, grid, NPC health bars
    order, turn = {}, 0
    local kinds = {}
    for _, o in ipairs(getObjectsWithTag("npc")) do
        local i = not o.hasTag("hidden") and o.call("info")
        if i and i.fight and not i.down then
            local k = kinds[i.name]
            if not k then
                k = { name = i.name, roll = math.random(20), objs = {} }
                kinds[i.name] = k
                table.insert(order, k)
            end
            table.insert(k.objs, o)
        end
    end
    for _, color in ipairs(DATA.colors) do
        local d = kit("d20_" .. color)
        if d then   -- every hero, seated or not
            local h = DATA.heroes[color]
            table.insert(order, { name = h.short, roll = d.getValue() + h.agility, hero = true, art = h.art,
                                 objs = { kit("fig_" .. color) } })
        end
    end
    drawTurns()
end

-- a hero's d20 landing: natural 20 bursts, natural 1 fizzles
local rolling = {}
function onObjectRandomize(o, color)
    local d20 = false
    for _, c in ipairs(DATA.colors) do d20 = d20 or o.hasTag("d20_" .. c) end
    if not d20 or rolling[o] then return end   -- the other dice: a 1 on a d6 is no fumble
    rolling[o] = true   -- shaking fires this again and again: one reaction per landing
    Wait.condition(function()
        rolling[o] = nil
        if o.isDestroyed() then return end
        local v, q = o.getValue(), o.getPosition()
        local who = DATA.heroes[color] and DATA.heroes[color].short or color
        if v == 20 then
            fxAt("crit", q)
            broadcastToAll("NATURAL 20! " .. who .. " rolls a crit!", { 1, 0.85, 0.3 })
        elseif v == 1 then
            fxAt("puff", q, true); fxAt("crash", q)
            broadcastToAll("Natural 1... " .. who .. " fumbles.", { 0.7, 0.6, 0.55 })
        end
    end, function() return o.isDestroyed() or o.resting end, 10)
end

function nextTurn()
    if #order == 0 then return end
    turn = turn % #order + 1
    drawTurns()
    broadcastToAll(order[turn].name .. "'s turn", { 0.94, 0.85, 0.63 })
    if not order[turn].hero then   -- NPCs: poison bites, conditions remind and tick down (npc.lua)
        for _, o in ipairs(order[turn].objs) do
            if not o.isDestroyed() then o.call("startTurn") end
        end
    end
end

function endFight() order, turn = {}, 0; drawTurns(); musicScene() end   -- back to the scene's music, out of battle

function drawTurns()
    table.sort(order, function(a, b)
        if a.roll ~= b.roll then return a.roll > b.roll end
        if (a.hero or false) ~= (b.hero or false) then return a.hero or false end
        return a.name < b.name   -- a fixed order for ties: the strip must not reshuffle when redrawn
    end)
    for i, e in ipairs(order) do
        for _, o in ipairs(e.objs) do
            if not o.isDestroyed() then
                if i == turn then o.highlightOn({ 1, 0.8, 0.3 }) else o.highlightOff() end
            end
        end
    end
    -- the bottom strip: one portrait card per entry (hero portrait, NPC kind's portrait, or just the name)
    for k = 1, DATA.turn_slots do
        local e = order[k]
        UI.setAttribute("ts" .. k, "active", e and "true" or "false")
        if e then
            local art = e.hero and e.art or DATA.npc_art[e.name]
            UI.setAttribute("ts" .. k, "color", k == turn and "#d9a633" or "#1b1410ee")
            UI.setAttribute("ti" .. k, "image", art or "")
            UI.setAttribute("ti" .. k, "color", art and "#ffffff" or "#00000000")
            UI.setValue("tn" .. k, e.name .. (#e.objs > 1 and (" x" .. #e.objs) or "") .. "\n" .. e.roll)
        end
    end
    UI.setAttribute("turns", "width", math.min(#order, DATA.turn_slots) * 102)   -- cards keep their width: the strip fits them
    UI.setAttribute("turns", "active", #order > 0 and "true" or "false")
end

-- ---------------------------------------------------------------- tremor
-- Giant footsteps: two thuds and dust here and there, and every seated camera (the GM's too) swings to one shared view
-- and shakes: TTS has no camera shake, so this is lookAt() jittered. p: where the thuds sound (the chainmaster on his
-- reveal, the middle of the map from the GM panel's button).
-- ponytail: pitch/distance eyeballed, yaw 0 = the Red/Blue (south) side as the seats use it; tune CAM if the view is off
CAM = { pitch = 55, distance = 32, shake = 0.5 }
SHAKE = { "Red", "Blue", "Green", "Purple", "Black" }
function tremorButton() tremor({ x = T.cx, z = T.cz }) end   -- GM panel (it passes the clicking player)
function tremor(p)
    for step = 0, 1 do
        Wait.time(function()
            fxAt("thud", p)
            local half = T.w * DATA.layout.art_w / 2
            for _ = 1, 2 do
                fxAt("puff", { x = T.cx + (math.random() * 2 - 1) * half * 0.8, z = T.cz + (math.random() * 2 - 1) * DATA.layout.rows * SQ * 0.4 }, true)
            end
        end, step * 0.9)
    end
    -- everyone gets the same view: from the south edge between Wren's and Brannoc's seats, over the middle of the map
    for i = 0, 16 do   -- shakes twice (one per thud), dying away
        Wait.time(function() viewAll(i == 16 and 0 or (1 - (i % 8) / 8) * CAM.shake * SQ) end, i * 0.11)
    end
end

-- every seated camera to the shared view over the middle of the map, jittered by k (0: steady; scene changes use it)
function viewAll(k)
    for _, color in ipairs(SHAKE) do
        if Player[color].seated then
            Player[color].lookAt({ position = { T.cx + (math.random() - 0.5) * k, T.top, T.cz + (math.random() - 0.5) * k },
                                   pitch = CAM.pitch + (math.random() - 0.5) * k, yaw = 0, distance = CAM.distance })
        end
    end
end

-- ---------------------------------------------------------------- searching
-- Chests, barrels, crates and sacks without fixed loot: right-click > Search, once each, with the hero beside it.
function search(o, color)
    if o.isDestroyed() then return end
    local who = color == "Black" and "The GM" or (DATA.heroes[color] and DATA.heroes[color].short)
    if not who then return end
    local q, fig = o.getPosition(), kit("fig_" .. color)
    if color ~= "Black" then
        local f = fig and fig.getPosition()
        if not f or (f.x - q.x) ^ 2 + (f.z - q.z) ^ 2 > (2.5 * SQ) ^ 2 then
            broadcastToColor("Move your hero next to it first.", color, { 1, 0.6, 0.2 })
            return
        end
    end
    if searched[o.getGUID()] then
        broadcastToColor("Already searched: nothing more in there.", color, { 1, 0.6, 0.2 })
        return
    end
    searched[o.getGUID()] = true
    local item, text, gold, rare = rollLoot(false)
    broadcastToAll(who .. " searches the " .. (o.getName() ~= "" and o.getName():lower() or "container") .. ": " .. text,
                   { 0.94, 0.85, 0.63 })
    if rare then fxAt("burst_yellow", q) end   -- the rare finds sparkle
    -- the find itself, on the floor between the container and the hero: players drag it to their side of the table
    local f = fig and fig.getPosition() or { x = q.x + SQ, z = q.z }
    local d = math.sqrt((f.x - q.x) ^ 2 + (f.z - q.z) ^ 2)
    dropLoot(item, text, gold, d > 0.01 and { x = q.x + (f.x - q.x) / d * SQ, z = q.z + (f.z - q.z) / d * SQ } or { x = q.x + SQ, z = q.z })
end

-- one roll on the loot table (content.LOOT): item (false = nothing), announcement text, gold amount, rare?
-- something: reroll the "nothing" results (the GM's loot bag)
function rollLoot(something)
    local pool, total = {}, 0
    for _, l in ipairs(DATA.loot) do
        if not something or l[2][1][2] then pool[#pool + 1] = l; total = total + l[1] end
    end
    local r = math.random(total)
    for _, l in ipairs(pool) do
        r = r - l[1]
        if r <= 0 then
            local v, gold = l[2][math.random(#l[2])], math.random(2, 8)   -- one of the entry's variants
            return v[2], (v[1]:gsub("{gold}", tostring(gold))), gold, l[1] <= 3
        end
    end
end

-- the GM's loot bag (GM desk): Draw loot puts a random find from the search pool (never nothing) beside it, still
-- GM-only like everything on the desk; dragged off the desk it shows up for the players
function lootBag(o)
    _G.drawLoot = function(_, color)
        if color ~= "Black" then return end
        local item, text, gold = rollLoot(true)
        local q = o.getPosition()
        broadcastToColor("Loot Bag: " .. text, "Black", { 0.94, 0.85, 0.63 })
        dropLoot(item, text, gold, { x = q.x - SQ, z = q.z }, true)
    end
    o.clearButtons()
    o.createButton({ click_function = "drawLoot", function_owner = self, label = "Draw loot", position = { 0, 1.4, 0 },
                     rotation = { 0, 90, 0 }, width = 1.6 * BTN, height = 0.5 * BTN, font_size = 0.3 * BTN,
                     color = BROWN, font_color = CREAM })
end

-- what a search turns up, as a thing on the table: gold = the GM pouch's coins, an item card's name = a copy of that
-- card, anything else = a small loot sack (food: the ration model) named after it. Tagged "loot": players can
-- handle it and it doesn't count as scenery.
function dropLoot(item, text, gold, at, gm)   -- gm: on the GM desk, hidden from players like the rest of it
    if not item then return end
    local function spawn(src, scale, y, name, desc)
        local d = {}
        for k, v in pairs(src) do d[k] = v end
        d.GUID, d.Tags, d.Locked, d.Nickname, d.Description = nil, { "loot", gm and "gm" or nil }, false, name or src.Nickname, desc or src.Description
        d.s = nil
        d.Transform = { posX = at.x + (math.random() - 0.5) * SQ * 0.4, posY = T.top + y, posZ = at.z + (math.random() - 0.5) * SQ * 0.4,
                        rotX = 0, rotY = math.random(360), rotZ = 0, scaleX = scale, scaleY = scale, scaleZ = scale }
        spawnObjectData({ data = d, callback_function = function(o) if gm then gmHide(o) end end })
    end
    if item == "gold" then
        local coin
        for _, g in ipairs(DATA.gm) do if g.Nickname == "Gold Pouch" then coin = g.ContainedObjects[1] end end
        for n = 1, gold do spawn(coin, SQ, 1 + n * 0.3) end
        return
    end
    for _, g in ipairs(DATA.gm) do
        if g.Name == "Card" and g.Nickname == item then return spawn(g, SQ / 2, 1) end   -- the real item card
    end
    local m = DATA.loot_models[item] or DATA.loot_models.default
    spawn(m, m.s * SQ, 1, item, text:gsub("^%l", string.upper))
end

-- ---------------------------------------------------------------- scorch marks
-- a fireball leaves a burnt patch on the map (a decal: flat, no collision) until the scene changes
function scorch(p)
    pcall(function()
        Global.addDecal({ name = "scorch", url = DATA.scorch, position = { p.x, T.top + 0.03, p.z },
                          rotation = { 90, math.random(360), 0 }, scale = { 3 * SQ, 3 * SQ, 1 } })
    end)
end

-- ---------------------------------------------------------------- giant grab
-- GM right-clicks a giant: Grab nearest hero (within 6 squares, lifted up in its fist), then Throw (4-6 squares,
-- 2d6 damage) or Let go (they broke free). ponytail: hold height and throw distance eyeballed
held = {}   -- giant GUID -> hero colour (setScene empties it)
function giantMenu(o)
    o.addContextMenuItem("Grab nearest hero", function(c) if c == "Black" then grab(o) end end)
    o.addContextMenuItem("Throw the hero", function(c) if c == "Black" then throw(o) end end)
    o.addContextMenuItem("Let go", function(c) if c == "Black" then letGo(o) end end)
end

function grab(o)
    if held[o.getGUID()] then return end
    local p, best, bd = o.getPosition(), nil, (6 * SQ) ^ 2
    for _, color in ipairs(DATA.colors) do
        local f = kit("fig_" .. color)
        local q = f and f.getPosition()
        if q and (q.x - p.x) ^ 2 + (q.z - p.z) ^ 2 <= bd then best, bd = color, (q.x - p.x) ^ 2 + (q.z - p.z) ^ 2 end
    end
    if not best then return broadcastToColor("No hero within 6 squares.", "Black", { 1, 0.6, 0.2 }) end
    for _, c in pairs(held) do if c == best then return end end   -- already in another giant's fist
    held[o.getGUID()] = best
    local f, g = kit("fig_" .. best), o.getGUID()
    local fb = f.getBounds()
    local fr = math.max(fb.size.x, fb.size.z) / 2   -- the hero's own radius: held clear of the giant's body
    f.setLock(true)
    f.setPosition(fist(o, fr))   -- straight there: a smooth move could drag it through the giant
    fxAt("swipe", p)
    broadcastToAll(o.getName() .. " grabs " .. DATA.heroes[best].short .. "! Might DC 14 to break free.", { 0.9, 0.4, 0.3 })
    -- held: the hero stays in the fist, facing the giant, wherever the GM moves or turns it
    carry(o, f, function() return fist(o, fr), { 0, o.getRotation().y + 180, 0 } end, function() return held[g] == best end)
end

-- keeps f at at() (position, rotation) on holder o, 20 times a second, while keep() holds and both exist.
-- A carried thing also hides/shows with its holder.
function carry(o, f, at, keep)
    local id, hidden
    id = Wait.time(function()
        if o.isDestroyed() or f.isDestroyed() or not keep() then return Wait.stop(id) end
        local p, r = at()
        f.setPosition(p)
        f.setRotation(r)
        if hidden ~= o.hasTag("hidden") then
            hidden = o.hasTag("hidden")
            f.setInvisibleTo(hidden and PLAYERS or {})
        end
    end, 0.05, -1)
end

-- giants with a wicker shield carry it upright on their left, facing forward (the scene destroys it with them).
-- It has no collider near the table: a carried prop overlapping its giant would shove it around.
-- ponytail: size and placement eyeballed like the fist
function giveShield(o)
    local q, s = o.getPosition(), DATA.shield.scale * SQ
    local d = {}
    for k, v in pairs(DATA.shield.obj) do d[k] = v end
    d.Transform = { posX = q.x, posY = q.y + 3, posZ = q.z, rotX = 90, rotY = 0, rotZ = 0, scaleX = s, scaleY = s, scaleZ = s }
    spawnObjectData({ data = d, callback_function = function(sh)
        carry(o, sh, function()
            local b, fwd, rt = o.getBounds(), o.getTransformForward(), o.getTransformRight()
            local r = math.max(b.size.x, b.size.z) * 0.45
            return { b.center.x + (fwd.x * 1.0 - rt.x * 0.8) * r, b.center.y - b.size.y / 2 + b.size.y * 0.4,
                     b.center.z + (fwd.z * 1.0 - rt.z * 0.8) * r }, { 90, o.getRotation().y, 0 }
        end, function() return true end)
        -- its collider sits far below the table (build.py), so it can't be clicked: the GM removes it from the giant
        o.addContextMenuItem("Shield burned", function(c)
            if c == "Black" and not sh.isDestroyed() then
                sh.destruct()
                o.removeTag("shield")   -- a reload must not give it a new one
                broadcastToAll("The wicker shield goes up in flames!", { 1, 0.6, 0.2 })
            end
        end)
    end })
end

-- where the giant's fist is: in front of it at shoulder height, from its real size and facing. A held hero (radius fr)
-- hangs just outside the giant's footprint: the locked hero overlapping it would shove the giant across the table.
-- ponytail: 0.6 up of its bounds eyeballed; tune if the hero hangs too high or low
function fist(o, fr)
    local b, fwd = o.getBounds(), o.getTransformForward()
    local r = math.max(b.size.x, b.size.z) / 2 + (fr or 0) + 0.1 * SQ
    return { b.center.x + fwd.x * r, b.center.y - b.size.y / 2 + b.size.y * 0.6, b.center.z + fwd.z * r }
end

function throw(o)
    local color = held[o.getGUID()]
    if not color then return end
    held[o.getGUID()] = nil
    -- forward, up to 60 degrees either side: the hero flies away from the giant, never back through it
    local f, p, fwd, t, d = kit("fig_" .. color), o.getPosition(), o.getTransformForward(),
                            (math.random() - 0.5) * 2 * math.pi / 3, (4 + math.random() * 2) * SQ
    local dx, dz = fwd.x * math.cos(t) - fwd.z * math.sin(t), fwd.x * math.sin(t) + fwd.z * math.cos(t)
    local hx, hz = T.w * DATA.layout.art_w / 2 - SQ, DATA.layout.rows * SQ / 2 - SQ   -- land on the map
    local x = math.max(T.cx - hx, math.min(T.cx + hx, p.x + dx * d))
    local z = math.max(T.cz - hz, math.min(T.cz + hz, p.z + dz * d))
    f.setLock(false)
    f.setPositionSmooth({ x, T.top + 1, z }, false, false)
    fxAt("whoosh", p)
    Wait.time(function()
        local dmg = math.random(6) + math.random(6)
        fxAt("puff", { x = x, z = z }, true); fxAt("thud", { x = x, z = z })
        setHP(color, hp[color] - dmg)
        broadcastToAll(o.getName() .. " hurls " .. DATA.heroes[color].short .. " across the field: " .. dmg ..
                       " damage, prone.", { 0.9, 0.4, 0.3 })
    end, 0.8)
end

function letGo(o)
    local color = held[o.getGUID()]
    if not color then return end
    held[o.getGUID()] = nil
    local f = kit("fig_" .. color)
    local q = f.getPosition()
    f.setLock(false)
    f.setPosition({ q.x, T.top + 1, q.z })   -- dropped straight down from the fist, clear of the giant
    broadcastToAll(DATA.heroes[color].short .. " breaks free!", { 0.5, 0.9, 0.5 })
end
