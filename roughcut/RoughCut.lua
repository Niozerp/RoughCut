-- RoughCut Launcher for DaVinci Resolve (Electron UI Only)
-- Version: 1.0.9 - Working PATH Fix

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

-- Find electron app
local scriptPath = debug.getinfo(1, "S").source
if scriptPath:sub(1, 1) == "@" then scriptPath = scriptPath:sub(2) end
scriptPath = scriptPath:gsub("\\", "/")
local scriptsDir = scriptPath:match("^(.*)/") or "."

local electronPath = scriptsDir .. "/roughcut-electron"
if not io.open(electronPath .. "/package.json", "r") then
    electronPath = scriptsDir .. "/../roughcut-electron"
end

if not io.open(electronPath .. "/package.json", "r") then
    print("[RoughCut] ERROR: Cannot find roughcut-electron")
    return
end

print("[RoughCut] Found: " .. electronPath)

-- Convert path
local winPath = electronPath:gsub("/", "\\")
local tempDir = (os.getenv("TEMP") or "C:\\Windows\\Temp"):gsub("/", "\\")

-- Get project name
local projectName = "Unknown"
pcall(function()
    projectName = resolve:GetProjectManager():GetCurrentProject():GetName()
end)
print("[RoughCut] Project: " .. projectName)

-- Create batch with unique name (avoid stale files)
local timestamp = tostring(os.time())
local batchFile = tempDir .. "\\roughcut_" .. timestamp .. ".bat"

-- Delete any old roughcut_*.bat files (cleanup)
os.execute('del "' .. tempDir .. '\\roughcut_*.bat" >nul 2>&1')

local batchLines = {
    "@echo off",
    "echo [RC] Starting...",
    "cd /d \"" .. winPath .. "\"",
    "if errorlevel 1 (echo [RC] CD failed & pause & exit /b 1)",
    "echo [RC] Dir: %cd%",
    "if not exist node_modules\\.bin (",
    "  echo [RC] First run - installing dependencies...",
    "  call npm install",
    "  if errorlevel 1 (echo [RC] npm install failed & pause & exit /b 1)",
    ")",
    "set ROUGHCUT_RESOLVE=1",
    "set ROUGHCUT_PROJECT=" .. projectName,
    "echo [RC] Adding node_modules\\.bin to PATH...",
    "set PATH=%cd%\\node_modules\\.bin;%PATH%",
    "echo [RC] Running npm run dev...",
    "call npm run dev",
    "if errorlevel 1 (echo [RC] npm failed: %errorlevel% & pause)",
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

print("[RoughCut] Launching...")

-- Launch with start command
os.execute('start "RoughCut" cmd /c "' .. batchFile .. '"')

print("[RoughCut] Window should appear")

-- Cleanup this batch file after delay
os.execute('start /MIN cmd /c "ping -n 31 127.0.0.1 >nul & del \"' .. batchFile .. '\" 2>nul & del ' .. tempDir .. '\\roughcut_*.log 2>nul"')
