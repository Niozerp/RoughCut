-- RoughCut launcher for DaVinci Resolve.
-- Launches the built Electron app in Resolve attach mode.

local function file_exists(path)
    local handle = io.open(path, "r")
    if handle then
        handle:close()
        return true
    end
    return false
end

local function shell_escape_unix(value)
    return tostring(value):gsub("'", [["'"']])
end

print("[RoughCut] Starting Resolve launcher...")

local resolve = nil
for _ = 1, 5 do
    if _G.fusion and _G.fusion.GetResolve then
        local ok, result = pcall(function()
            return _G.fusion:GetResolve()
        end)
        if ok and result then
            resolve = result
            break
        end
    end
end

if not resolve then
    print("[RoughCut] Resolve scripting API is not available.")
    return
end

local script_path = debug.getinfo(1, "S").source
if script_path:sub(1, 1) == "@" then
    script_path = script_path:sub(2)
end

script_path = script_path:gsub("\\", "/")
local scripts_dir = script_path:match("^(.+)/[^/]+$") or "."
local package_root = scripts_dir .. "/roughcut"
local electron_path = package_root .. "/electron"
local bootstrap_script = package_root .. "/scripts/bootstrap_launch.py"

local package_json = electron_path .. "/package.json"

if not file_exists(package_json) then
    print("[RoughCut] Cannot find roughcut/electron/package.json")
    print("[RoughCut] Re-run install.bat or install.sh to bootstrap RoughCut.")
    return
end

if not file_exists(bootstrap_script) then
    print("[RoughCut] Cannot find roughcut/scripts/bootstrap_launch.py")
    print("[RoughCut] Re-run install.bat or install.sh to restore the launch bootstrap.")
    return
end

local project_name = "Unknown Project"
pcall(function()
    project_name = resolve:GetProjectManager():GetCurrentProject():GetName()
end)

local path_separator = package.config:sub(1, 1)
local is_windows = path_separator == "\\"

if is_windows then
    local working_dir = package_root:gsub("/", "\\")
    local bootstrap_path = bootstrap_script:gsub("/", "\\")
    local safe_project = tostring(project_name):gsub('"', "'")
    local command = 'cd /d "' .. working_dir .. '" && ' ..
        '(py -3 "' .. bootstrap_path .. '" --mode resolve --project-name "' .. safe_project .. '" ' ..
        '|| python "' .. bootstrap_path .. '" --mode resolve --project-name "' .. safe_project .. '")'

    os.execute(command)
else
    local command = 'cd "' .. package_root .. '" && ' ..
        '(python3 "' .. bootstrap_script .. '" --mode resolve --project-name \'' ..
        shell_escape_unix(project_name) .. '\' ' ..
        '|| python "' .. bootstrap_script .. '" --mode resolve --project-name \'' ..
        shell_escape_unix(project_name) .. '\')'

    os.execute(command)
end

print("[RoughCut] Launch request sent.")
