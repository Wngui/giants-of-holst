-- NPC: healthbar everyone sees; HP, damage box and attack buttons only the GM (Black seat / host) sees.
-- Damage box: "12" or "+12" deals damage, "-5" heals. Attack buttons roll and whisper the result to the GM.
-- ponytail: UI placement is eyeballed; if the bar sits oddly on a model, tweak UI_HEIGHT in build.py or UI_ROT here.
UI_SCALE = "0.4 0.4 0.4"
-- the bar stands upright and faces where the figure faces (its +z): Euler (90, -90, 90) in the object-UI frame
-- (x = object x, z = object down). "0 0 180" lay flat; "(yaw - 90) -90 90" stood up facing south.
UI_ROT = "90 -90 90"
local GM = "Black"   -- not "Host": the host sitting in a player seat would still see GM-only UI
local S
-- the panel is placed by its centre; put the health bar (its bottom row) at S.ui above the base, per model (build.py)
function uiPos() return string.format("0 0 %d", -math.floor((S.ui or 430) + (60 + 44 * #S.attacks) * 0.4 / 2)) end

function onLoad(saved)
    S = JSON.decode(saved)
    draw()
end

function onSave() return JSON.encode(S) end

function draw()
    -- top to bottom: attack buttons and HP/damage (GM only), then the health bar right above the figure
    local x = { string.format(
        '<Panel position="%s" rotation="%s" scale="%s" width="300" height="%d"><VerticalLayout spacing="4" childForceExpandHeight="false">',
        uiPos(), UI_ROT, UI_SCALE, 60 + 44 * #S.attacks) }
    for i, a in ipairs(S.attacks) do
        x[#x + 1] = '<Button id="a' .. i .. '" onClick="attack" visibility="' .. GM ..
            '" preferredHeight="40" fontSize="16" colors="#3a2a1a|#5a4028|#2a1a0a|#3a2a1a" textColor="#f0d9a0">' ..
            a.name .. '</Button>'
    end
    x[#x + 1] = '<HorizontalLayout visibility="' .. GM .. '" preferredHeight="34" spacing="4">' ..
        '<Text id="hp" fontSize="18" color="#ffffff" outline="#000000">' .. hpText() .. '</Text>' ..
        '<InputField id="dmg" placeholder="dmg" onEndEdit="applyDamage" fontSize="18"/></HorizontalLayout>'
    x[#x + 1] = '<ProgressBar id="bar" preferredHeight="22"' .. (S.hidden and ' visibility="' .. GM .. '"' or '') ..
        ' percentage="' .. pct() ..
        '" fillImageColor="#b8322a" color="#000000cc" showPercentageText="false"/>'
    x[#x + 1] = '</VerticalLayout></Panel>'
    self.UI.setXml(table.concat(x))
end

-- called by the controller: while hidden from players, the health bar is GM-only too
function setHidden(p)
    S.hidden = p.hidden
    draw()
end

function pct() return math.floor(100 * S.hp / S.max) end
function hpText() return S.hp .. "/" .. S.max .. "  Def " .. S.def end

function applyDamage(player, value)
    -- MoonSharp's tonumber(s, 10) throws on "-5"/"", so pattern-check first and call it without a base
    local num = (value or ""):match("^%s*%+?(%-?%d+)%s*$")
    local n = num and tonumber(num)
    if not n or n == 0 then return end
    S.hp = math.max(0, math.min(S.max, S.hp - n))
    self.UI.setAttribute("bar", "percentage", pct())
    self.UI.setAttribute("hp", "text", hpText())
    self.UI.setAttribute("dmg", "text", "")
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
    broadcastToColor(msg, "Black", { 1, 0.8, 0.4 })
    if player.color ~= "Black" then broadcastToColor(msg, player.color, { 1, 0.8, 0.4 }) end
end
