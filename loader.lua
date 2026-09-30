-- Holst loader. This is the only script inside Holst.json and it never changes:
-- on every load it downloads the latest game.json from GitHub and installs it on a hidden controller object.
GAME_URL = "https://raw.githubusercontent.com/Wngui/giants-of-holst/main/game.json"
CONTROLLER = "--@CONTROLLER@"

function onLoad()
    -- the ?t= query skips GitHub's 5-minute CDN cache
    WebRequest.get(GAME_URL .. "?t=" .. os.time(), function(r)
        if r.is_error or r.response_code ~= 200 then
            broadcastToAll("Couldn't download the game from GitHub (" .. tostring(r.error or r.response_code) ..
                "). Using the copy saved in this file, if any.", { 1, 0.5, 0.3 })
            return
        end
        install(JSON.decode(r.text))
    end)
end

function install(game)
    UI.setXml(game.xml, game.assets)
    local ctl = getObjectFromGUID(CONTROLLER)
    local state = ""
    if ctl then
        if ctl.getVar("VERSION") == game.version then return end
        state = ctl.call("onSave") or ""
        ctl.destruct()
    end
    game.controller.LuaScriptState = state
    -- wait for the old controller to be gone so the new one keeps its GUID
    Wait.frames(function() spawnObjectData({ data = game.controller }) end, 2)
    broadcastToAll("The Giants of Holst: loaded version " .. game.version, { 0.94, 0.85, 0.63 })
end
