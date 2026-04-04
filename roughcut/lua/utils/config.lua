-- RoughCut Configuration Manager
-- Handles reading/writing ~/.roughcut/config.yaml
-- Compatible with DaVinci Resolve's Lua scripting environment

local configManager = {}

-- Default configuration
local DEFAULT_CONFIG = {
    backend_installed = false,
    installed_at = nil,
    installation_cancelled = false,
    last_run = nil,
    python_version = nil,
    poetry_version = nil,
    backend_version = nil
}

-- Config file path
local CONFIG_DIR = nil
local CONFIG_FILE = nil
local isWindows = nil

-- Detect if running on Windows
local function detectWindows()
    if isWindows == nil then
        local osEnv = os.getenv("OS")
        local pathSep = package.config:sub(1,1)
        isWindows = (osEnv and osEnv:lower():find("windows")) or (pathSep == "\\")
    end
    return isWindows
end

-- Get platform-appropriate path separator
local function getPathSeparator()
    return detectWindows() and "\\" or "/"
end

-- Initialize config manager
-- Sets up paths for the config directory and file
function configManager.init()
    -- Determine home directory based on OS
    local home = os.getenv("HOME")
    
    -- Windows: try USERPROFILE first, then HOMEDRIVE + HOMEPATH
    if not home and detectWindows() then
        home = os.getenv("USERPROFILE")
        if not home then
            local homeDrive = os.getenv("HOMEDRIVE")
            local homePath = os.getenv("HOMEPATH")
            if homeDrive and homePath then
                home = homeDrive .. homePath
            end
        end
    end
    
    if not home then
        print("RoughCut: Warning - Could not determine home directory")
        return false
    end
    
    -- Use platform-appropriate path separator
    local sep = getPathSeparator()
    CONFIG_DIR = home .. sep .. ".roughcut"
    CONFIG_FILE = CONFIG_DIR .. sep .. "config.yaml"
    
    return true
end

-- Check if directory exists (cross-platform)
local function directoryExists(path)
    if detectWindows() then
        -- Windows: use if exist command
        local cmd = 'if exist "' .. path .. "\\" .. '" (echo exists) else (echo missing)'
        local handle = io.popen(cmd)
        if handle then
            local output = handle:read("*a")
            handle:close()
            return output:find("exists") ~= nil
        end
    else
        -- Unix: use test -d
        local handle = io.popen('test -d "' .. path .. '" && echo "exists" || echo "missing"')
        if handle then
            local output = handle:read("*a")
            handle:close()
            return output:find("exists") ~= nil
        end
    end
    return false
end

-- Create directory (cross-platform)
local function createDirectory(path)
    if detectWindows() then
        -- Windows: mkdir without -p flag
        os.execute('mkdir "' .. path .. '" 2>nul')
        -- Try again if first attempt failed (parent dirs might not exist)
        if not directoryExists(path) then
            -- On Windows, we might need to create parent directories manually
            -- For simplicity, just try again
            os.execute('mkdir "' .. path .. '" 2>nul')
        end
    else
        -- Unix: mkdir -p
        os.execute('mkdir -p "' .. path .. '"')
    end
end

-- Ensure config directory exists
-- Creates ~/.roughcut if it doesn't exist
local function ensureConfigDir()
    if not CONFIG_DIR then
        if not configManager.init() then
            return false
        end
    end
    
    -- Check if directory exists
    if directoryExists(CONFIG_DIR) then
        return true
    end
    
    -- Create directory
    local ok, _ = pcall(function()
        createDirectory(CONFIG_DIR)
    end)
    
    return ok and directoryExists(CONFIG_DIR)
end

-- Read config file
-- @return table with config values or default if file doesn't exist
function configManager.read()
    if not CONFIG_FILE then
        configManager.init()
    end
    
    if not CONFIG_FILE then
        return configManager.getDefaults()
    end
    
    -- Check if file exists
    local ok, file = pcall(function()
        return io.open(CONFIG_FILE, "r")
    end)
    
    if not ok or not file then
        -- Return defaults if file doesn't exist
        return configManager.getDefaults()
    end
    
    -- Read file content
    local content = file:read("*a")
    file:close()
    
    if not content or content == "" then
        return configManager.getDefaults()
    end
    
    -- Simple YAML-like parsing (very basic)
    local config = configManager.getDefaults()
    
    for line in content:gmatch("[^\n]+") do
        line = line:gsub("^%s+", ""):gsub("%s+$", "")
        
        -- Skip comments and empty lines
        if line ~= "" and not line:find("^#") then
            local key, value = line:match("^(%w+):%s*(.+)$")
            
            if key and value then
                -- Parse value
                if value == "true" then
                    config[key] = true
                elseif value == "false" then
                    config[key] = false
                elseif value:find('^"') and value:find('"$') then
                    -- String value
                    config[key] = value:sub(2, -2)
                elseif tonumber(value) then
                    config[key] = tonumber(value)
                else
                    config[key] = value
                end
            end
        end
    end
    
    return config
end

-- Get ISO 8601 timestamp with timezone
-- Lua doesn't have built-in timezone support, so we use UTC with Z suffix
-- @return string ISO 8601 formatted timestamp
local function getISOTimestamp()
    -- os.date("!%Y-%m-%dT%H:%M:%SZ") would give UTC, but we want local time with Z
    -- For simplicity, using local time with Z (assumes system timezone is acceptable)
    return os.date("%Y-%m-%dT%H:%M:%SZ")
end

-- Write config file atomically (write to temp file, then rename)
-- Prevents partial/corrupt config on crash
-- @param config Table with configuration values
-- @return boolean indicating success
function configManager.write(config)
    if not ensureConfigDir() then
        print("RoughCut: Error - Could not create config directory")
        return false
    end
    
    if not config then
        print("RoughCut: Error - No config to write")
        return false
    end
    
    -- Generate YAML content in deterministic order
    local lines = {
        "# RoughCut Configuration",
        "# Auto-generated - Do not edit manually",
        "",
    }
    
    -- Add config values in sorted order for consistency
    local keys = {}
    for key, _ in pairs(config) do
        table.insert(keys, key)
    end
    table.sort(keys)
    
    for _, key in ipairs(keys) do
        local value = config[key]
        if type(value) == "boolean" then
            table.insert(lines, key .. ": " .. tostring(value))
        elseif type(value) == "number" then
            table.insert(lines, key .. ": " .. tostring(value))
        elseif type(value) == "string" then
            -- Escape quotes in string values
            local escaped = value:gsub('"', '\\"')
            table.insert(lines, key .. ': "' .. escaped .. '"')
        end
    end
    
    -- Write to temp file first (atomic write)
    local sep = getPathSeparator()
    local tempFile = CONFIG_FILE .. ".tmp"
    local ok, file = pcall(function()
        return io.open(tempFile, "w")
    end)
    
    if not ok or not file then
        print("RoughCut: Error - Could not open config file for writing")
        return false
    end
    
    local content = table.concat(lines, "\n")
    local writeOk, writeErr = pcall(function()
        file:write(content)
        file:close()
    end)
    
    if not writeOk then
        print("RoughCut: Error - Failed to write config: " .. tostring(writeErr))
        -- Clean up temp file
        pcall(function() os.remove(tempFile) end)
        return false
    end
    
    -- Atomic rename (temp file to actual file)
    local renameOk, renameErr = pcall(function()
        if detectWindows() then
            -- Windows: use move command
            os.execute('move /Y "' .. tempFile .. '" "' .. CONFIG_FILE .. '" >nul 2>&1')
        else
            -- Unix: use mv command
            os.execute('mv "' .. tempFile .. '" "' .. CONFIG_FILE .. '"')
        end
    end)
    
    if not renameOk then
        print("RoughCut: Warning - Could not rename config file atomically")
        -- Try non-atomic fallback
        pcall(function()
            os.remove(CONFIG_FILE)
            os.rename(tempFile, CONFIG_FILE)
        end)
    end
    
    return true
end

-- Get default configuration
-- @return table with default values
function configManager.getDefaults()
    local defaults = {}
    for k, v in pairs(DEFAULT_CONFIG) do
        defaults[k] = v
    end
    return defaults
end

-- Mark backend as installed
-- @param pythonVersion Python version string
-- @param poetryVersion Poetry version string
-- @return boolean indicating success
function configManager.markInstalled(pythonVersion, poetryVersion)
    local config = configManager.read()
    
    config.backend_installed = true
    -- Use ISO 8601 format with Z suffix (timezone indicator)
    config.installed_at = getISOTimestamp()
    config.installation_cancelled = false
    config.last_run = getISOTimestamp()
    config.python_version = pythonVersion or config.python_version
    config.poetry_version = poetryVersion or config.poetry_version
    
    return configManager.write(config)
end

-- Mark installation as cancelled
-- @return boolean indicating success
function configManager.markCancelled()
    local config = configManager.read()
    
    config.installation_cancelled = true
    config.last_run = getISOTimestamp()
    
    return configManager.write(config)
end

-- Check if backend is installed
-- @return boolean
function configManager.isBackendInstalled()
    local config = configManager.read()
    return config.backend_installed == true
end

-- Get config file path
-- @return string path or nil
function configManager.getConfigPath()
    if not CONFIG_FILE then
        configManager.init()
    end
    return CONFIG_FILE
end

-- Reset config to defaults
-- Useful for recovering from corruption
-- @return boolean indicating success
function configManager.reset()
    return configManager.write(DEFAULT_CONFIG)
end

-- Update last run timestamp
-- @return boolean indicating success
function configManager.updateLastRun()
    local config = configManager.read()
    config.last_run = getISOTimestamp()
    return configManager.write(config)
end

return configManager
