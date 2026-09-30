-- Holst loader. This is the only script inside Holst.json and it never changes:
-- on every load it downloads the latest game from GitHub and installs it on a hidden controller object.
-- game.json is small (version + UI); controller.lua is plain Lua, so nothing big goes through JSON.decode.
BASE = "https://raw.githubusercontent.com/Wngui/giants-of-holst/main/"
CONTROLLER = "--@CONTROLLER@"

-- the ?t= query skips GitHub's 5-minute CDN cache
function fetch(file, cb)
    WebRequest.get(BASE .. file .. "?t=" .. os.time(), function(r)
        if r.is_error or r.response_code ~= 200 then
            broadcastToAll("Couldn't download " .. file .. " from GitHub (" .. tostring(r.error or r.response_code) ..
                "). Using the copy saved in this file, if any.", { 1, 0.5, 0.3 })
            return
        end
        cb(r.text)
    end)
end

function onLoad()
    broadcastToAll("The Giants of Holst: downloading the latest version...", { 0.94, 0.85, 0.63 })
    fetch("game.json", function(text)
        local game = JSON.decode(text)
        UI.setXml(game.xml, game.assets)
        local ctl = getObjectFromGUID(CONTROLLER)
        if ctl and ctl.getVar("VERSION") == game.version then return end
        fetch("controller.lua", function(code) install(game.version, code) end)
    end)
end

function install(version, code)
    local ctl = getObjectFromGUID(CONTROLLER)
    local state = ""
    if ctl then
        state = ctl.call("onSave") or ""
        ctl.destruct()
    end
    -- wait for the old controller to be gone so the new one keeps its GUID
    Wait.frames(function()
        spawnObjectData({ data = {
            Name = "BlockSquare", GUID = CONTROLLER, Nickname = "Game controller (don't delete)", Locked = true,
            Transform = { posX = 0, posY = -3, posZ = 0, rotX = 0, rotY = 0, rotZ = 0, scaleX = 0.5, scaleY = 0.5, scaleZ = 0.5 },
            LuaScript = code, LuaScriptState = state,
        } })
        broadcastToAll("The Giants of Holst: version " .. version .. " ready.", { 0.94, 0.85, 0.63 })
    end, 2)
end
