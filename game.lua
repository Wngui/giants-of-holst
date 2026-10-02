-- The Giants of Holst: GM panel, scene switching, class pick, rest.
-- Runs on the hidden controller object that loader.lua downloads and (re)spawns; the save file itself never changes.
-- build.py replaces the DATA line with the generated scene/hero data.
DATA = {} --@DATA@
VERSION = DATA.version

local scene, setupDone, hp = 1, {}, {}
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
        scene, setupDone, hp = s.scene, s.setupDone, s.hp or {}
    else
        install(s.scene or 1)
    end
    Wait.frames(refreshPick, 15)   -- the loader has just set the UI XML; give TTS a moment to build it
end

function onSave()
    return JSON.encode({ version = VERSION, scene = scene, setupDone = setupDone, hp = hp })
end

-- First load or a new version: fresh hero kits and notebook, same scene, re-deal to seated players.
function install(sceneIndex)
    for _, o in ipairs(getObjectsWithTag("kit")) do o.destruct() end
    for _, d in ipairs(DATA.kits) do
        local g = d.grid
        spawnObjectData({ data = placed(d), callback_function = function(o)
            if g.ring then addRing(o, g.ring) end
            if g.role == "hp" then hpShield(o, g.color, g.max) end
        end })
    end
    -- GM desk: whatever still lies on it (tag "gm") and the screen are replaced; things handed out stay
    for _, tag in ipairs({ "gm", "gmscreen", "gmtable" }) do
        for _, o in ipairs(getObjectsWithTag(tag)) do o.destruct() end
    end
    for _, d in ipairs(DATA.gm) do
        spawnObjectData({ data = placed(d), callback_function = function(o)
            if o.hasTag("gm") then gmHide(o) end
            if o.hasTag("gmconsole") then console(o) end
        end })
    end
    for _, color in ipairs(DATA.colors) do
        local c = corner(color)
        Player[color].setHandTransform({ position = { c.x, T.top + 4, T.cz + c.sz * (T.d / 2 + 4) },
                                         rotation = { 0, c.ry, 0 }, scale = { 12, 5, 4 } })
    end
    -- the GM's hand: at the far side of the GM table, so "hover a bag/deck + number key" lands with the GM
    pcall(function()
        Player.Black.setHandTransform({ position = { T.cx + T.w / 2 + DATA.layout.gm_hand * SQ, T.top + 4, T.cz },
                                        rotation = { 0, 270, 0 }, scale = { 12, 5, 4 } })
    end)
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
        p = { c.x + c.right * s[1], T.top + s[3], s[2] }
        t.rotY = c.ry
        if g.role == "hp" then t.scaleX, t.scaleY, t.scaleZ = SQ * 1.2, SQ * 1.2, SQ * 1.2 end   -- shield ~2.4 squares
        if g.role == "sheet" then
            t.rotY = c.ry + 180                       -- tile images face the opposite way to hands
            local sc = T.w * L.sheet_w / L.tile_unit
            t.scaleX, t.scaleY, t.scaleZ = sc, 1, sc
        end
    else
        -- props drop a little and get pinned; figures are scaled to the grid (RPG kit figures fit a 2-unit square)
        p = world(g.x, g.z, g.ly and g.ly * SQ or g.lift or (g.k == "fig" and 1 or 0.3))
        for _, c in ipairs(g.inner and d.ContainedObjects or {}) do   -- coins etc. in bags: grid-sized too
            c.Transform.scaleX, c.Transform.scaleY, c.Transform.scaleZ = g.inner * SQ, g.inner * SQ, g.inner * SQ
        end
        local unit = (g.k == "model") and SQ or SQ / 2
        local s = g.s or { 1, 1, 1 }
        t.scaleX, t.scaleY, t.scaleZ = s[1] * unit, s[2] * unit, s[3] * unit
    end
    t.posX, t.posY, t.posZ = p[1], p[2], p[3]
    return o
end

-- ---------------------------------------------------------------- scenes
function onSceneButton(player, _, id)
    setScene(tonumber(id:sub(7)))
end

function setScene(i)
    for _, o in ipairs(getObjectsWithTag("scene")) do o.destruct() end
    scene = i
    local s = DATA.scenes[i]
    Tables.setCustomURL(s.table)
    for _, d in ipairs(s.spawns) do
        local ring, rs = d.grid.ring, d.grid.ring_s
        spawnObjectData({ data = placed(d), callback_function = function(o)
            if ring then addRing(o, ring, rs) end
            -- let props settle on the table, then pin them
            if o.hasTag("pin") then Wait.time(function() o.setLock(true) end, 1.5) end
            if o.hasTag("hidden") then hide(o) end
        end })
    end
    for n, color in ipairs(DATA.colors) do
        local fig = kit("fig_" .. color)
        if fig then
            local p = world(s.heroes[n][1], s.heroes[n][2], 1)
            fig.setPositionSmooth(p, false, true)
            Wait.frames(function() revealNear(p) end, 2)   -- after the scene's NPCs have spawned
            fig.setRotationSmooth({ 0, 90, 0 })   -- face east, into the scene
        end
    end
    backdrop(s)
    highlightScene()
    UI.setAttribute("sceneTitle", "text", s.title)
    play(s.music)
    broadcastToAll(s.title, { 0.94, 0.85, 0.63 })
end

-- ---------------------------------------------------------------- hidden enemies (instead of TTS's fog box)
PLAYERS = { "White", "Brown", "Red", "Orange", "Yellow", "Green", "Teal", "Blue", "Purple", "Pink", "Grey" }

function hide(o)
    o.setInvisibleTo(PLAYERS)
    o.call("setHidden", { hidden = true })
end

function reveal(o)
    o.setInvisibleTo({})
    o.removeTag("hidden")
    o.call("setHidden", { hidden = false })
end

function revealAll()
    for _, o in ipairs(getObjectsWithTag("hidden")) do reveal(o) end
end

function revealNear(p)
    local r = DATA.layout.reveal * SQ
    for _, o in ipairs(getObjectsWithTag("hidden")) do
        local q = o.getPosition()
        if (q.x - p[1]) ^ 2 + (q.z - p[3]) ^ 2 <= r * r then reveal(o) end
    end
end

function onObjectDrop(player, o)
    for _, color in ipairs(DATA.colors) do
        if o.hasTag("fig_" .. color) then
            local q = o.getPosition()
            revealNear({ q.x, q.y, q.z })
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

function console(o)
    panel = o
    for i, b in ipairs(DATA.gm_buttons) do
        local fn = "noop"
        if b.kind ~= "title" then
            fn = "gmButton" .. i
            _G[fn] = function(_, color)
                if color ~= "Black" then return end
                if b.scene then setScene(b.scene) else _G[b.fn]() end
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

-- ---------------------------------------------------------------- HP shields (instead of TTS counters)
-- A shield at each seat: big number, - and + (right-click: 5 at a time). REST refills it.
local shields = {}
function hpShield(o, color, max)
    shields[color] = o
    hp[color] = hp[color] or max
    o.createButton({ click_function = "noop", function_owner = self, label = tostring(hp[color]),
                     position = { 0, 0.2, 0 }, width = 0, height = 0, font_size = 0.32 * BTN, font_color = { 1, 0.95, 0.85 } })
    for k, d in ipairs({ -1, 1 }) do
        local fn = "hp" .. color .. (d < 0 and "Down" or "Up")
        _G[fn] = function(_, _, alt) setHP(color, hp[color] + d * (alt and 5 or 1)) end
        o.createButton({ click_function = fn, function_owner = self, label = d < 0 and "-" or "+",
                         position = { d * 0.62, 0.2, 0 }, width = 0.16 * BTN, height = 0.16 * BTN, font_size = 0.2 * BTN,
                         color = { 0.15, 0.1, 0.07 }, font_color = { 1, 0.95, 0.85 } })
    end
end

function setHP(color, v)
    local max = DATA.heroes[color].hp
    hp[color] = math.max(0, math.min(max, v))
    if shields[color] then shields[color].editButton({ index = 0, label = tostring(hp[color]) }) end
end

-- ---------------------------------------------------------------- coloured bases
-- A thin ring round each figure's base, attached so it moves with it: hero = seat colour, notable NPC = gold,
-- everyone else dark. ponytail: RING (ring radius per unit of figure scale) is a guess at the RPG kit's base size
RING = 0.95
function addRing(o, rgb, size)
    Wait.time(function()
        if o == nil then return end
        local p, sc = o.getPosition(), o.getScale().x * RING * (size or 1)
        spawnObjectData({ data = { Name = "Custom_Model", CustomMesh = DATA.ring, Locked = false,
                                   ColorDiffuse = { r = rgb[1], g = rgb[2], b = rgb[3] },
                                   Transform = { posX = p.x, posY = p.y, posZ = p.z, rotX = 0, rotY = 0, rotZ = 0,
                                                 scaleX = sc, scaleY = sc, scaleZ = sc } },
                          callback_function = function(r)
                              o.addAttachment(r)
                              if o.hasTag("hidden") then o.setInvisibleTo(PLAYERS) end   -- still hidden as one piece
                          end })
    end, 2)
end

-- coins out of a desk pouch, a card off a desk deck: hidden like their container until the GM hands them out
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
    MusicPlayer.setCurrentAudioclip({ url = track.url, title = track.title })
    Wait.condition(function() MusicPlayer.play() end, function() return MusicPlayer.player_status == "Ready" end, 20)
end

function musicScene() play(DATA.scenes[scene].music) end
function musicBattle() play(DATA.battle) end
function musicStop() MusicPlayer.pause() end

-- ---------------------------------------------------------------- class pick
function pick(player, _, id)
    local color = id:sub(6)   -- a hero's seat colour, or Black for the Game Master
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
        setupHero(color)
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
    for _, color in ipairs(DATA.colors) do
        local h = DATA.heroes[color]
        setHP(color, h.hp)
        if Player[color].seated then
            local inHand = {}
            for _, o in ipairs(Player[color].getHandObjects()) do inHand[o.getGUID()] = true end
            local hand = Player[color].getHandTransform()
            for _, card in ipairs(getObjectsWithTag("card_" .. color)) do
                if card.type == "Card" and not inHand[card.getGUID()] then
                    card.setRotation(hand.rotation)
                    card.setPositionSmooth(hand.position + Vector(0, 2, 0), false, true)
                elseif card.type == "Deck" then
                    card.deal(#card.getObjects(), color)
                end
            end
        end
    end
    broadcastToAll("REST: HP back to full, all cards return to your hand.", { 0.5, 0.9, 0.5 })
end
