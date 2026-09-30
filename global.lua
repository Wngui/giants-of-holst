-- The Giants of Holst: GM panel, scene switching, class pick, rest.
-- build.py replaces the DATA line with the generated scene/hero data.
DATA = {} --@DATA@

local scene, setupDone = 1, {}

function onLoad(saved)
    local s = saved ~= "" and JSON.decode(saved) or nil
    if s then
        scene, setupDone = s.scene, s.setupDone
    else
        setScene(1)
    end
    MusicPlayer.repeat_track = true
    refreshPick()
end

function onSave()
    return JSON.encode({ scene = scene, setupDone = setupDone })
end

-- ---------------------------------------------------------------- scenes
function onSceneButton(player, _, id)
    setScene(tonumber(id:sub(7)))
end

function setScene(i)
    for _, o in ipairs(getObjectsWithTag("scene")) do o.destruct() end
    scene = i
    local s = DATA.scenes[i]
    for _, d in ipairs(s.spawns) do
        spawnObjectData({ data = d, callback_function = function(o)
            -- let maps settle on the table, then pin them
            if o.hasTag("pin") then Wait.time(function() o.setLock(true) end, 1.5) end
        end })
    end
    for n, color in ipairs(DATA.colors) do
        local fig = getObjectFromGUID(DATA.heroes[color].fig)
        if fig then fig.setPositionSmooth(s.heroes[n], false, true) end
    end
    UI.setAttribute("sceneTitle", "text", s.title)
    play(s.music)
    broadcastToAll(s.title, { 0.94, 0.85, 0.63 })
end

function revealAll()
    for _, o in ipairs(getObjectsWithTag("fog")) do o.destruct() end
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
        broadcastToColor("That adventurer is taken, pick another.", player.color, "Orange")
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
    local deck = getObjectFromGUID(h.deck)
    if deck then deck.deal(6, color) end
    broadcastToAll(Player[color].steam_name .. " is " .. h.name .. ".", color)
end

-- ---------------------------------------------------------------- rest
-- Every played card goes back to its owner's hand, HP counters reset to max.
function rest()
    for _, color in ipairs(DATA.colors) do
        local h = DATA.heroes[color]
        local counter = getObjectFromGUID(h.counter)
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
