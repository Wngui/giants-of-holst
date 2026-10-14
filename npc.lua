-- NPC: healthbar everyone sees (in battle only), with HP written on it for the GM.
-- GM right-click menu: Take damage (negative heals; or hover and type a number), Reveal, and one entry per attack,
-- which rolls and whispers to the GM.
-- Def, movement and attacks are in the object's description (build.py).
-- ponytail: UI placement is eyeballed; if the bar sits oddly on a model, tweak UI_HEIGHT in build.py or UI_ROT here.
-- the bar stands upright and faces where the figure faces (its +z): Euler (90, -90, 90) in the object-UI frame
-- (x = object x, z = object down). "0 0 180" lay flat; "(yaw - 90) -90 90" stood up facing south.
UI_SCALE = "0.4 0.4 0.4"
UI_ROT = "90 -90 90"
local GM = "Black"   -- not "Host": the host sitting in a player seat would still see GM-only UI
local S
-- the panel is placed by its centre; put the health bar (its bottom row) at S.ui above the base, per model (build.py)
function uiPos() return string.format("0 0 %d", -math.floor((S.ui or 430) + 26 * 0.4 / 2)) end

function onLoad(saved)
    S = JSON.decode(saved)
    draw()
    self.addContextMenuItem("Take damage", function(color)
        if color ~= GM then return end
        Player[color].showInputDialog("Damage to " .. S.name .. " (negative heals)", "", function(text)
            -- MoonSharp's tonumber(s, 10) throws on "-5"/"", so pattern-check first and call it without a base
            local num = (text or ""):match("^%s*%+?(%-?%d+)%s*$")
            if num then hurt(tonumber(num)) end
        end)
    end)
    self.addContextMenuItem("Reveal", function(color) revealMe({ color = color }) end)
    for i, a in ipairs(S.attacks) do
        self.addContextMenuItem(a.name, function(color)
            if color == GM then attack({ color = color }, nil, "a" .. i) end
        end)
    end
end

function onNumberTyped(color, n)
    if color == GM then hurt(n) end
    return true
end

function onSave() return JSON.encode(S) end

function draw()
    -- the health bar right above the figure
    local x = { string.format(
        '<Panel position="%s" rotation="%s" scale="%s" width="300" height="26"><VerticalLayout spacing="4" childForceExpandHeight="false">',
        uiPos(), UI_ROT, UI_SCALE) }
    local off = S.battle and "" or ' active="false"'   -- bars only in battle (the GM's Battle button)
    x[#x + 1] = '<Panel preferredHeight="22"' .. off .. (S.hidden and ' visibility="' .. GM .. '"' or '') .. '>' ..
        '<ProgressBar id="bar" percentage="' .. pct() ..
        '" fillImageColor="#b8322a" color="#000000cc" showPercentageText="false"/>' ..
        '<Text id="hp" visibility="' .. GM .. '" fontSize="18" fontStyle="Bold" color="#ffffff" outline="#000000">' ..
        hpText() .. '</Text></Panel>'
    x[#x + 1] = '</VerticalLayout></Panel>'
    self.UI.setXml(table.concat(x))
end

function revealMe(player)
    if player.color == "Black" then getObjectFromGUID(S.ctl).call("revealGuid", { guid = self.getGUID() }) end
end

-- called by the controller: while hidden from players, the health bar is GM-only too
function setHidden(p)
    S.hidden = p.hidden
    draw()
end

-- called by the controller when the GM switches battle mode on/off
function setBattle(p)
    S.battle = p.on
    draw()
end

-- called by the controller's turn order
function info() return { name = S.name, fight = #S.attacks > 0, down = S.down or false } end

function pct() return math.floor(100 * S.hp / S.max) end
function hpText() return S.hp .. "/" .. S.max end

-- a particle effect on this NPC, spawned by the controller (game.lua fxAt)
function fx(name) getObjectFromGUID(S.ctl).call("fx", { name = name, guid = self.getGUID() }) end

function hurt(n)   -- negative heals; 0 HP plays the death animation (and healing stands it back up)
    if not n or n == 0 then return end
    fx(n > 0 and (S.hp - n <= 0 and S.hp > 0 and "puff" or "blood") or "swirl_green")
    S.hp = math.max(0, math.min(S.max, S.hp - n))
    self.UI.setAttribute("bar", "percentage", pct())
    self.UI.setAttribute("hp", "text", hpText())
    -- die() toggles the lying pose; S.down tracks it so figures that start lying (the princess) stand when healed
    local down = S.hp == 0
    if down ~= (S.down or false) then
        S.down = down
        if self.RPGFigurine then self.RPGFigurine.die() end
        broadcastToAll(S.name .. (down and " falls!" or " gets back up!"), { 0.9, 0.4, 0.3 })
    end
end

-- "2d8+4" -> total, "5,3 +4"
function roll(expr)
    local n, d, m = expr:match("^(%d+)d(%d+)([%+%-]?%d*)$")
    local total, parts = 0, {}
    for _ = 1, tonumber(n) do
        local r = math.random(tonumber(d))
        total = total + r
        parts[#parts + 1] = r
    end
    m = tonumber(m) or 0
    return total + m, "[" .. table.concat(parts, ",") .. "]" .. (m ~= 0 and string.format("%+d", m) or "")
end

function attack(player, _, id)
    local a = S.attacks[tonumber(id:sub(2))]
    local msg = S.name .. " - " .. a.name .. ": "
    local crit = false
    if a.hit then
        local d20 = math.random(20)
        crit = d20 == 20
        msg = msg .. (d20 + a.hit) .. " to hit (d20 " .. d20 .. (crit and " CRIT" or d20 == 1 and " FUMBLE" or "") .. ")  "
    end
    if a.dmg then
        local total, detail = roll(a.dmg)
        if crit then
            local extra = roll(a.dmg:gsub("[%+%-]%d+$", ""))
            total, detail = total + extra, detail .. " +crit " .. extra
        end
        msg = msg .. total .. (a.hit and " dmg " or " ") .. detail .. "  "
    end
    msg = msg .. "(" .. a.note .. ")"
    if a.hit and self.RPGFigurine then self.RPGFigurine.attack() end
    if crit then fx("crit") elseif a.hit then fx("swipe") end
    broadcastToColor(msg, "Black", { 1, 0.8, 0.4 })
    if player.color ~= "Black" then broadcastToColor(msg, player.color, { 1, 0.8, 0.4 }) end
end
