-- RoughCut Launcher for DaVinci Resolve (Electron UI)
-- Merged version - electron app is in same folder
-- Version: 2.0.0

print("[RoughCut] Starting...")

-- Get Resolve
local resolve = nil
for i = 1, 5 do
    if _G.fusion and _G.fusion.GetResolve then
        local ok, r = pcall(function() return _G.fusion:GetResolve() end)
        if ok and r then resolve = r break end
    end
    local s = os.clock()
    while os.clock() - s < 0.2 do end
end

if not resolve then
    print("[RoughCut] ERROR: Cannot connect to Resolve")
    return
end

-- Find this script's directory
local scriptPath = debug.getinfo(1, "S").source
if scriptPath:sub(1, 1) == "@" then scriptPath = scriptPath:sub(2) end
scriptPath = scriptPath:gsub("\\", "/")

-- Remove filename to get directory
local scriptsDir = scriptPath:match("^(.+)/[^/]+$") or "."
print("[RoughCut] Scripts dir: " .. scriptsDir)

-- Electron app is in roughcut/electron/ subfolder
local electronPath = scriptsDir .. "/roughcut/electron"

-- Check for package.json
local f = io.open(electronPath .. "/package.json", "r")
if not f then
    print("[RoughCut] ERROR: Cannot find roughcut/electron/package.json")
    print("[RoughCut] Looked in: " .. electronPath)
    return
end
f:close()

print("[RoughCut] Found electron app")

-- Get project name
local projectName = "Unknown"
pcall(function()
    projectName = resolve:GetProjectManager():GetCurrentProject():GetName()
end)
print("[RoughCut] Project: " .. projectName)

-- Convert to Windows path
local winPath = electronPath:gsub("/", "\\")
local tempDir = (os.getenv("TEMP") or "C:\\Windows\\Temp"):gsub("/", "\\")
local timestamp = tostring(os.time())
local batchFile = tempDir .. "\\roughcut_" .. timestamp .. ".bat"

-- Delete any old batch files
os.execute('del "' .. tempDir .. '\\roughcut_*.bat" >nul 2>&1')

-- Create batch
local batchLines = {
    "@echo off",
    "echo [RC] Starting RoughCut...",
    "cd /d \"" .. winPath .. "\"",
    "if errorlevel 1 (echo [RC] ERROR: Cannot cd & pause & exit /b 1)",
    "echo [RC] In: %cd%",
    "if not exist node_modules\\.bin\\electron.cmd (",
    "  echo [RC] Installing deps...",
    "  call npm install",
    "  if errorlevel 1 (echo [RC] Install failed & pause & exit /b 1)",
    ")",
    "set ROUGHCUT_RESOLVE=1",
    "set ROUGHCUT_PROJECT=" .. projectName,
    "set PATH=%cd%\\node_modules\\.bin;%PATH%",
    "echo [RC] Launching...",
    "call npm run dev",
    "if errorlevel 1 (echo [RC] Failed & pause)",
    "exit"
}

local f = io.open(batchFile, "w")
if not f then
    print("[RoughCut] ERROR: Cannot write batch")
    return
end
for _, line in ipairs(batchLines) do
    f:write(line .. "\n")
end
f:close()

print("[RoughCut] Launching from: " .. batchFile)

-- Launch
os.execute('start "RoughCut" cmd /c "' .. batchFile .. '"')
print("[RoughCut] Window should appear")

-- Cleanup
os.execute('start /MIN cmd /c "ping -n 61 127.0.0.1 >nul & del \"' .. batchFile .. '\" 2>nul"')
