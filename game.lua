-- The Giants of Holst: GM panel, scene switching, class pick, rest.
-- Runs on the hidden controller object that loader.lua downloads and (re)spawns; the save file itself never changes.
-- build.py replaces the DATA line with the generated scene/hero data.
DATA = {} --@DATA@
VERSION = DATA.version

local scene, setupDone = 1, {}
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
        scene, setupDone = s.scene, s.setupDone
    else
        install(s.scene or 1)
    end
    Wait.frames(refreshPick, 15)   -- the loader has just set the UI XML; give TTS a moment to build it
end

function onSave()
    return JSON.encode({ version = VERSION, scene = scene, setupDone = setupDone })
end

-- First load or a new version: fresh hero kits and notebook, same scene, re-deal to seated players.
function install(sceneIndex)
    for _, o in ipairs(getObjectsWithTag("kit")) do o.destruct() end
    for _, d in ipairs(DATA.kits) do spawnObjectData({ data = placed(d) }) end
    -- GM desk: whatever still lies on it (tag "gm") and the screen are replaced; things handed out stay
    for _, tag in ipairs({ "gm", "gmscreen" }) do
        for _, o in ipairs(getObjectsWithTag(tag)) do o.destruct() end
    end
    for _, d in ipairs(DATA.gm) do
        spawnObjectData({ data = placed(d), callback_function = function(o)
            if o.hasTag("gm") then gmHide(o) end
        end })
    end
    for _, color in ipairs(DATA.colors) do
        local c = corner(color)
        Player[color].setHandTransform({ position = { c.x, T.top + 4, T.cz + c.sz * (T.d / 2 + 4) },
                                         rotation = { 0, c.ry, 0 }, scale = { 12, 5, 4 } })
    end
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
        local spots = { sheet = { 0, zs, 0.2 }, deck = { -3 * k, zr, 1 }, counter = { 0.5 * k, zr, 0.5 },
                        d20 = { 3 * k, zr, 1 } }
        local s = spots[g.role]
        p = { c.x + c.right * s[1], T.top + s[3], s[2] }
        t.rotY = c.ry
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
        spawnObjectData({ data = placed(d), callback_function = function(o)
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
    local color = id:sub(6)
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
        local counter = kit("counter_" .. color)
        if counter then counter.Counter.setValue(h.hp) end
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
