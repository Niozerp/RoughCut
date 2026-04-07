-- RoughCut Launcher for DaVinci Resolve
-- This is the ONLY script that should be in the Resolve Scripts folder
-- Version: 0.3.5

print("[RoughCut Launcher] Starting...")

-- Get Resolve with retry logic using scriptapp (works in Fusion/Utility context)
local function getResolveWithRetry(maxAttempts, delayMs)
    for i = 1, maxAttempts do
        -- Try scriptapp first (most reliable for Utility scripts)
        if _G.scriptapp then
            local ok, result = pcall(function() return _G.scriptapp("Resolve") end)
            if ok and result ~= nil then
                print("[RoughCut Launcher] Got Resolve via scriptapp on attempt " .. i)
                return result
            end
        end
        
        -- Try bmd.scriptapp
        if _G.bmd and _G.bmd.scriptapp then
            local ok, result = pcall(function() return _G.bmd.scriptapp("Resolve") end)
            if ok and result ~= nil then
                print("[RoughCut Launcher] Got Resolve via bmd.scriptapp on attempt " .. i)
                return result
            end
        end
        
        -- Try getting Resolve through Fusion
        if _G.fusion and _G.fusion.GetResolve then
            local ok, result = pcall(function() return _G.fusion:GetResolve() end)
            if ok and result ~= nil then
                print("[RoughCut Launcher] Got Resolve via fusion:GetResolve() on attempt " .. i)
                return result
            end
        end
        
        print("[RoughCut Launcher] Attempt " .. i .. "/" .. maxAttempts .. " failed, waiting...")
        
        -- Small delay using a busy-wait
        local start = os.clock()
        while os.clock() - start < (delayMs / 1000) do
            -- busy wait
        end
    end
    
    return nil
end

-- Get the directory where THIS script is located (the Scripts folder)
local function getScriptsDirectory()
    local scriptPath = debug.getinfo(1, "S").source
    if scriptPath:sub(1, 1) == "@" then
        scriptPath = scriptPath:sub(2)
    end
    -- Normalize to forward slashes for cross-platform compatibility
    scriptPath = scriptPath:gsub("\\", "/")
    -- Get the directory containing this script
    local dir = scriptPath:match("^(.*)/") or "."
    print("[RoughCut Launcher] Scripts directory: " .. dir)
    return dir
end

-- Try multiple possible locations for RoughCut modules
local function findRoughCutModules()
    local scriptsDir = getScriptsDirectory()
    local possiblePaths = {
        -- Option 1: roughcut/lua/ folder in same directory as this script
        { path = scriptsDir .. "/roughcut/lua", testFile = "/roughcut_main.lua" },
        -- Option 2: roughcut/lua/ in parent of scripts (development layout)
        { path = scriptsDir .. "/../roughcut/lua", testFile = "/roughcut_main.lua" },
        -- Option 3: Direct roughcut subfolder (legacy)
        { path = scriptsDir .. "/roughcut", testFile = "/roughcut_main.lua" },
    }
    
    for _, option in ipairs(possiblePaths) do
        local path = option.path:gsub("//", "/")
        local testFile = path .. option.testFile
        
        print("[RoughCut Launcher] Checking: " .. testFile)
        
        -- Check if file exists using io.open
        local f = io.open(testFile, "r")
        if f then
            f:close()
            print("[RoughCut Launcher] Found modules at: " .. path)
            return path
        end
    end
    
    print("[RoughCut Launcher] Could not find roughcut_main.lua in any expected location")
    return nil
end

-- Show error dialog to user
local function showError(message)
    local ok, resolve = pcall(function() return Resolve() end)
    if ok and resolve then
        -- Use fu.UIManager (Fusion's UIManager) instead of resolve:GetUIManager()
        local ok_ui, uiManager = pcall(function() 
            if fu and fu.UIManager then
                return fu.UIManager
            elseif fusion and fusion.UIManager then
                return fusion.UIManager
            end
            return nil
        end)
        if ok_ui and uiManager then
            pcall(function()
                uiManager:ShowMessageBox(
                    message .. "\n\nPlease ensure RoughCut is properly installed.\nSee README.md for installation instructions.",
                    "RoughCut - Installation Error",
                    "OK"
                )
            end)
        end
    end
    -- Also print to console
    print("[RoughCut Error] " .. message)
end

-- Main launcher
local function launchRoughCut()
    -- Step 1: Find the RoughCut modules
    local modulesPath = findRoughCutModules()
    
    if not modulesPath then
        showError(
            "Could not find RoughCut modules.\n\n" ..
            "Expected to find 'roughcut/lua/roughcut_main.lua' in one of these locations:\n" ..
            "- In the same folder as RoughCut.lua\n" ..
            "- In a 'roughcut/lua/' subfolder\n\n" ..
            "Current scripts folder: " .. getScriptsDirectory()
        )
        return false
    end
    
    -- Step 2: Get Resolve API using scriptapp (works in Fusion/Utility context)
    print("[RoughCut Launcher] Connecting to DaVinci Resolve...")
    local resolve = getResolveWithRetry(5, 200)  -- 5 attempts, 200ms between each
    
    if not resolve then
        showError("Could not connect to DaVinci Resolve.\n\nMake sure:\n1. DaVinci Resolve is running\n2. A project is open\n3. You're running this from Workspace > Scripts menu")
        return false
    end
    
    print("[RoughCut Launcher] Connected to Resolve successfully")
    
    -- Step 3: Add the modules path to Lua's search path
    -- Format: path/?.lua;path/?/init.lua
    local pathTemplate = modulesPath .. "/?.lua;" .. modulesPath .. "/?/init.lua"
    package.path = pathTemplate .. ";" .. package.path
    
    print("[RoughCut Launcher] Added to package.path: " .. pathTemplate)
    
    -- Step 4: Load the RoughCut main module
    print("[RoughCut Launcher] Loading roughcut_main module...")
    local ok, roughcut_module = pcall(function()
        return require("roughcut_main")
    end)
    
    if not ok then
        showError(
            "Failed to load RoughCut module.\n\n" ..
            "Error: " .. tostring(roughcut_module) .. "\n\n" ..
            "Tried to load from: " .. modulesPath
        )
        return false
    end
    
    -- Step 5: Call the launch function, passing Resolve
    print("[RoughCut Launcher] Calling launch function...")
    if roughcut_module and roughcut_module.launch then
        local launch_ok = roughcut_module.launch(resolve)
        if not launch_ok then
            showError("RoughCut failed to launch. Check the console for details.")
            return false
        end
    else
        showError("RoughCut module does not have a launch function. Installation may be corrupted.")
        return false
    end
    
    print("[RoughCut Launcher] Launch successful")
    return true
end

-- Entry point - Resolve runs this when user selects from Scripts menu
local success = launchRoughCut()

if not success then
    -- Try to show error in Resolve
    local ok, resolve = pcall(function() return Resolve() end)
    if ok and resolve then
        -- Use fu.UIManager (Fusion's UIManager) instead of resolve:GetUIManager()
        local ok_ui, uiManager = pcall(function() 
            if fu and fu.UIManager then
                return fu.UIManager
            elseif fusion and fusion.UIManager then
                return fusion.UIManager
            end
            return nil
        end)
        if ok_ui and uiManager then
            pcall(function()
                uiManager:ShowMessageBox(
                    "RoughCut failed to start.\n\nPlease check the Resolve console (Workspace > Console) for error details.",
                    "RoughCut - Error",
                    "OK"
                )
            end)
        end
    end
end
