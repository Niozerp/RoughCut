-- RoughCut Logger
-- Handles logging to ~/.roughcut/roughcut.log
-- Compatible with DaVinci Resolve's Lua scripting environment

local logger = {}

-- Log levels
local LOG_LEVELS = {
    DEBUG = 1,
    INFO = 2,
    WARNING = 3,
    ERROR = 4
}

-- Current log level
local currentLevel = LOG_LEVELS.INFO

-- Log file path
local LOG_DIR = nil
local LOG_FILE = nil
local isWindows = nil

-- Max log file size (10MB)
local MAX_LOG_SIZE = 10 * 1024 * 1024

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

-- Initialize logger
-- Sets up paths for the log directory and file
function logger.init()
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
        print("RoughCut: Warning - Could not determine home directory for logging")
        return false
    end
    
    -- Use platform-appropriate path separator
    local sep = getPathSeparator()
    LOG_DIR = home .. sep .. ".roughcut"
    LOG_FILE = LOG_DIR .. sep .. "roughcut.log"
    
    return true
end

-- Ensure log directory exists (cross-platform)
local function ensureLogDir()
    if not LOG_DIR then
        if not logger.init() then
            return false
        end
    end
    
    -- Create directory (platform-specific)
    if detectWindows() then
        -- Windows: mkdir without -p flag
        pcall(function()
            os.execute('mkdir "' .. LOG_DIR .. '" 2>nul')
        end)
    else
        -- Unix: mkdir -p
        pcall(function()
            os.execute('mkdir -p "' .. LOG_DIR .. '"')
        end)
    end
    
    return true
end

-- Get current timestamp
-- @return string formatted timestamp
local function getTimestamp()
    return os.date("%Y-%m-%d %H:%M:%S")
end

-- Check log file size and rotate if needed
local function checkLogRotation()
    local ok, file = pcall(function()
        return io.open(LOG_FILE, "r")
    end)
    
    if ok and file then
        local size = file:seek("end")
        file:close()
        
        if size > MAX_LOG_SIZE then
            -- Rotate log: move current to .old, start fresh
            local oldLog = LOG_FILE .. ".old"
            pcall(function()
                os.remove(oldLog)  -- Remove old backup if exists
                os.rename(LOG_FILE, oldLog)
            end)
        end
    end
end

-- Get log level name
-- @param level Number level
-- @return string level name
local function getLevelName(level)
    for name, val in pairs(LOG_LEVELS) do
        if val == level then
            return name
        end
    end
    return "UNKNOWN"
end

-- Set log level
-- @param level String level name (DEBUG, INFO, WARNING, ERROR)
function logger.setLevel(level)
    if LOG_LEVELS[level] then
        currentLevel = LOG_LEVELS[level]
    end
end

-- Write log entry
-- @param level Log level
-- @param message Log message
-- @return boolean indicating success
local function writeLog(level, message)
    if level < currentLevel then
        return true  -- Skip logging below current level
    end
    
    if not ensureLogDir() then
        return false
    end
    
    if not LOG_FILE then
        return false
    end
    
    -- Check if log rotation needed
    checkLogRotation()
    
    local timestamp = getTimestamp()
    local levelName = getLevelName(level)
    local logLine = string.format("[%s] [%s] %s\n", timestamp, levelName, tostring(message))
    
    -- Append to log file
    local ok, file = pcall(function()
        return io.open(LOG_FILE, "a")
    end)
    
    if not ok or not file then
        -- Log to console as fallback
        print("RoughCut: " .. logLine)
        return false
    end
    
    file:write(logLine)
    file:close()
    
    return true
end

-- Log debug message
-- @param message Message to log
function logger.debug(message)
    return writeLog(LOG_LEVELS.DEBUG, message)
end

-- Log info message
-- @param message Message to log
function logger.info(message)
    return writeLog(LOG_LEVELS.INFO, message)
end

-- Log warning message
-- @param message Message to log
function logger.warning(message)
    return writeLog(LOG_LEVELS.WARNING, message)
end

-- Log error message
-- @param message Message to log
function logger.error(message)
    return writeLog(LOG_LEVELS.ERROR, message)
end

-- Log installation event
-- @param event Event type (started, completed, cancelled, failed)
-- @param details Additional details
function logger.logInstallation(event, details)
    local message = "Installation " .. tostring(event)
    if details then
        message = message .. ": " .. tostring(details)
    end
    
    if event == "failed" or event == "cancelled" then
        return logger.error(message)
    elseif event == "completed" then
        return logger.info(message)
    else
        return logger.info(message)
    end
end

-- Get log file path
-- @return string path or nil
function logger.getLogPath()
    if not LOG_FILE then
        logger.init()
    end
    return LOG_FILE
end

-- Read recent log entries
-- @param count Number of entries to read (default: 50)
-- @return table of log lines
function logger.getRecentEntries(count)
    count = count or 50
    
    if not LOG_FILE then
        logger.init()
    end
    
    local ok, file = pcall(function()
        return io.open(LOG_FILE, "r")
    end)
    
    if not ok or not file then
        return {}
    end
    
    -- Read all lines
    local allLines = {}
    for line in file:lines() do
        table.insert(allLines, line)
    end
    
    file:close()
    
    -- Return last 'count' lines
    local startIndex = math.max(1, #allLines - count + 1)
    local recentLines = {}
    for i = startIndex, #allLines do
        table.insert(recentLines, allLines[i])
    end
    
    return recentLines
end

-- Clear log file
-- @return boolean indicating success
function logger.clear()
    if not LOG_FILE then
        logger.init()
    end
    
    local ok, file = pcall(function()
        return io.open(LOG_FILE, "w")
    end)
    
    if not ok or not file then
        return false
    end
    
    file:close()
    
    logger.info("Log cleared")
    return true
end

return logger
