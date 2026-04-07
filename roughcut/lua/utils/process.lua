-- RoughCut Lua Subprocess Management Utilities
-- Provides cross-platform subprocess handling for Resolve Lua environment
-- Compatible with DaVinci Resolve's Lua scripting environment

local processUtils = {}

-- Platform detection (cached)
local isWindows = nil
local function detectWindows()
    if isWindows == nil then
        -- Check multiple indicators for Windows
        local osEnv = os.getenv("OS")
        local pathEnv = os.getenv("PATH")
        isWindows = (osEnv and osEnv:lower():find("windows")) or 
                   (pathEnv and pathEnv:find(";")) or
                   (package.config:sub(1,1) == "\\")
    end
    return isWindows
end

-- Enhanced shell escape that handles more dangerous characters
-- @param str String to escape
-- @return escaped string safe for shell
function processUtils.shellEscape(str)
    if not str then
        return ""
    end
    
    if detectWindows() then
        -- Windows escaping: wrap in quotes, escape existing quotes by doubling
        -- Also need to handle backslashes before quotes and percent signs (batch variables)
        str = str:gsub('%%', '%%%%')  -- Escape % as %% (batch variable expansion)
        str = str:gsub('\\"', '\\\\"')  -- Escape backslash-quote
        str = str:gsub('"', '""')  -- Double existing quotes
        return '"' .. str .. '"'
    else
        -- Unix escaping: wrap in single quotes (prevents all shell expansion)
        -- Replace embedded single quotes with '\'' (end quote, literal quote, start quote)
        -- This safely handles all special characters: $ ` " \ | & ; ( ) < > * ? [ ] { } #
        return "'" .. str:gsub("'", "'\"'\"'") .. "'"
    end
end

-- Execute a command and capture output
-- @param command Table of command arguments (e.g., {"python3", "--version"})
-- @param workingDir Optional working directory (string)
-- @param timeoutSeconds Optional timeout in seconds (default: 30)
-- @return table with success, exitCode, stdout, stderr, error
function processUtils.run(command, workingDir, timeoutSeconds)
    local result = {
        success = false,
        exitCode = -1,
        stdout = "",
        stderr = "",
        error = nil
    }
    
    if not command or #command == 0 then
        result.error = "No command provided"
        return result
    end
    
    -- Check if working directory exists first
    if workingDir then
        local dirExists = false
        
        -- Escape workingDir for safe shell usage
        local escapedDir = processUtils.shellEscape(workingDir)
        
        -- Try to list directory contents using dir command (Windows) or test -d (Unix)
        if detectWindows() then
            -- On Windows, use 'dir' command to check if directory exists
            local checkCmd = 'dir ' .. escapedDir .. ' /b >nul 2>&1'
            local ok = os.execute(checkCmd)
            dirExists = (ok == 0 or ok == true)
        else
            -- On Unix, use test -d with escaped path
            local checkCmd = 'test -d ' .. escapedDir
            local ok = os.execute(checkCmd)
            dirExists = (ok == 0 or ok == true)
        end
        
        if not dirExists then
            print("RoughCut: ERROR - Working directory does not exist: " .. workingDir)
            result.error = "Directory not found: " .. workingDir
            return result
        end
        
        print("RoughCut: Working directory verified: " .. workingDir)
    end
    
    -- Build command string with proper escaping to prevent injection
    local escapedCmd = {}
    for _, arg in ipairs(command) do
        table.insert(escapedCmd, processUtils.shellEscape(arg))
    end
    local cmdStr = table.concat(escapedCmd, " ")
    
    -- Add working directory if specified (with proper Windows handling)
    if workingDir then
        if detectWindows() then
            -- Use pushd/popd which handles spaces better on Windows
            -- Avoid outer quotes to prevent nested quote issues with io.popen
            cmdStr = string.format('cmd /c pushd %s && %s && popd', 
                processUtils.shellEscape(workingDir), cmdStr)
        else
            cmdStr = string.format("cd %s && %s", 
                processUtils.shellEscape(workingDir), cmdStr)
        end
    end
    
    -- Add stderr redirection to capture both streams (at the very end for Windows)
    cmdStr = cmdStr .. " 2>&1"
    
    -- Debug logging
    print("RoughCut: Executing: " .. cmdStr)
    
    -- Execute command with pcall for error handling
    local ok, handle = pcall(function()
        return io.popen(cmdStr, "r")
    end)
    
    if not ok or not handle then
        result.error = "Failed to execute command: " .. tostring(handle)
        return result
    end
    
    -- Read output
    local output = {}
    local startTime = os.time()
    local timeout = timeoutSeconds or 30
    
    -- Read line by line with timeout check
    while true do
        -- Check timeout
        if os.time() - startTime > timeout then
            result.error = "Command timed out after " .. timeout .. " seconds"
            pcall(function() handle:close() end)
            return result
        end
        
        -- Try to read a line
        local lineOk, line = pcall(function()
            return handle:read("*l")
        end)
        
        if not lineOk then
            result.error = "Error reading command output: " .. tostring(line)
            pcall(function() handle:close() end)
            return result
        end
        
        if not line then
            -- End of output
            break
        end
        
        table.insert(output, line)
    end
    
    -- Close handle
    local closeOk, closeResult = pcall(function()
        return handle:close()
    end)
    
    if not closeOk then
        result.error = "Error closing command handle: " .. tostring(closeResult)
        return result
    end
    
    -- io.popen on Lua 5.1 returns exit status differently
    -- closeResult could be nil, true, or exit code
    if closeResult == true or closeResult == nil then
        result.success = true
        result.exitCode = 0
    elseif type(closeResult) == "number" then
        result.exitCode = closeResult
        result.success = (closeResult == 0)
    else
        -- Try to parse exit code from string
        local exitCode = tonumber(tostring(closeResult):match("(%d+)$"))
        if exitCode then
            result.exitCode = exitCode
            result.success = (exitCode == 0)
        else
            result.success = true
            result.exitCode = 0
        end
    end
    
    result.stdout = table.concat(output, "\n")
    return result
end

-- Check if a command exists in PATH
-- @param command Command name to check (e.g., "python3")
-- @return boolean indicating if command is available
function processUtils.commandExists(command)
    if not command or command == "" then
        return false
    end
    
    local checkCmd
    -- Use detectWindows() function instead of undefined sys.platform
    if detectWindows() then
        checkCmd = {"where", command}
    else
        checkCmd = {"which", command}
    end
    
    local result = processUtils.run(checkCmd, nil, 5)
    return result.success and result.exitCode == 0
end

-- Get the directory of the current script
-- Uses debug info to determine script location
-- @return string path or nil
function processUtils.getScriptDirectory()
    local ok, info = pcall(function()
        return debug.getinfo(2, "S")
    end)
    
    if not ok or not info or not info.source then
        return nil
    end
    
    -- Extract directory from source path
    local source = info.source
    if source:sub(1, 1) == "@" then
        source = source:sub(2)
    end
    
    -- Find last path separator
    local lastSep = source:match(".*()[/\\]")
    if lastSep then
        return source:sub(1, lastSep - 1)
    end
    
    return nil
end

-- Escape a string for shell safety
-- @param str String to escape
-- @return escaped string
-- Execute Python script with arguments
-- @param scriptPath Path to Python script
-- @param args Table of arguments
-- @param workingDir Optional working directory
-- @param timeoutSeconds Optional timeout
-- @return table with success, exitCode, stdout, stderr, error
function processUtils.runPython(scriptPath, args, workingDir, timeoutSeconds)
    if not scriptPath then
        return {
            success = false,
            exitCode = -1,
            stdout = "",
            stderr = "",
            error = "No script path provided"
        }
    end
    
    -- Find Python executable (try both python3 and python)
    -- On Windows, 'python' is more common; on Unix, 'python3' is preferred
    local pythonCmd = nil
    if processUtils.commandExists("python3") then
        pythonCmd = "python3"
    elseif processUtils.commandExists("python") then
        pythonCmd = "python"
    else
        return {
            success = false,
            exitCode = -1,
            stdout = "",
            stderr = "",
            error = "Python not found (tried python3 and python)"
        }
    end
    
    -- Build command with escaped arguments
    local command = {pythonCmd, scriptPath}
    if args then
        for _, arg in ipairs(args) do
            table.insert(command, arg)
        end
    end
    
    return processUtils.run(command, workingDir, timeoutSeconds)
end

-- Spawn a long-running process and get handle for streaming output
-- @param command Table of command arguments
-- @param workingDir Optional working directory
-- @return table with handle, pid, error
function processUtils.spawn(command, workingDir)
    local result = {
        handle = nil,
        pid = nil,
        error = nil
    }
    
    if not command or #command == 0 then
        result.error = "No command provided"
        return result
    end
    
    -- Check if working directory exists first
    if workingDir then
        local dirExists = false
        
        -- Escape workingDir for safe shell usage
        local escapedDir = processUtils.shellEscape(workingDir)
        
        -- Try to list directory contents using dir command (Windows) or test -d (Unix)
        if detectWindows() then
            -- On Windows, use 'dir' command to check if directory exists
            local checkCmd = 'dir ' .. escapedDir .. ' /b >nul 2>&1'
            local ok = os.execute(checkCmd)
            dirExists = (ok == 0 or ok == true)
        else
            -- On Unix, use test -d with escaped path
            local checkCmd = 'test -d ' .. escapedDir
            local ok = os.execute(checkCmd)
            dirExists = (ok == 0 or ok == true)
        end
        
        if not dirExists then
            print("RoughCut: ERROR - Working directory does not exist: " .. workingDir)
            result.error = "Directory not found: " .. workingDir
            return result
        end
        
        print("RoughCut: Working directory verified: " .. workingDir)
    end
    
    -- Build command string with proper escaping
    local escapedCmd = {}
    for _, arg in ipairs(command) do
        table.insert(escapedCmd, processUtils.shellEscape(arg))
    end
    local cmdStr = table.concat(escapedCmd, " ")
    
    -- On Windows with workingDir, we need to handle the working directory
    -- Since io.popen doesn't support setting working directory directly,
    -- we prepend a cd command using cmd /c with proper escaping
    -- This is safer than changing global process state
    if workingDir and detectWindows() then
        -- Use cmd /c with pushd/popd which handles spaces and returns to original
        cmdStr = string.format('cmd /c pushd %s && %s && popd', 
            processUtils.shellEscape(workingDir), cmdStr)
    elseif workingDir then
        -- Unix - use cd && command
        cmdStr = string.format("cd %s && %s", 
            processUtils.shellEscape(workingDir), cmdStr)
    end
    
    -- Debug logging
    print("RoughCut: Spawning: " .. cmdStr)
    
    -- Open process for reading
    local ok, handle = pcall(function()
        return io.popen(cmdStr, "r")
    end)
    
    if not ok or not handle then
        result.error = "Failed to spawn process: " .. tostring(handle)
        return result
    end
    
    result.handle = handle
    result.pid = nil  -- Lua io.popen doesn't provide PID directly
    
    return result
end

-- Read a line from spawned process
-- @param handle Process handle from spawn()
-- @return line string or nil if EOF/error
function processUtils.readLine(handle)
    if not handle then
        return nil
    end
    
    local ok, line = pcall(function()
        return handle:read("*l")
    end)
    
    if not ok then
        return nil
    end
    
    return line
end

-- Close spawned process
-- @param handle Process handle from spawn()
-- @return table with success (boolean) and exitCode (number)
function processUtils.close(handle)
    if not handle then
        return { success = true, exitCode = 0 }
    end
    
    local ok, exitCode = pcall(function()
        return handle:close()
    end)
    
    -- io.popen close() returns exit status differently on various Lua versions
    -- It can return: true (success), nil, or a number (exit code)
    local result = { success = true, exitCode = 0 }
    
    if not ok then
        -- Error during close
        result.success = false
        result.exitCode = -1
    elseif type(exitCode) == "number" then
        result.exitCode = exitCode
        result.success = (exitCode == 0)
    elseif exitCode == nil or exitCode == true then
        -- Success or unknown - assume success
        result.success = true
        result.exitCode = 0
    else
        -- Try to parse from string
        local code = tonumber(tostring(exitCode):match("(%d+)$"))
        if code then
            result.exitCode = code
            result.success = (code == 0)
        else
            result.success = true
            result.exitCode = 0
        end
    end
    
    return result
end

-- Kill spawned process (if possible)
-- @param handle Process handle from spawn()
-- @return boolean indicating success
function processUtils.kill(handle)
    if not handle then
        return false
    end
    
    -- On Windows, we can't easily get the PID from io.popen handle
    -- But we can try to close the pipe and use taskkill if we had a PID
    -- For now, close the pipe which should cause the process to exit
    -- when it tries to write output
    
    -- Attempt to close first
    local closeResult = processUtils.close(handle)
    
    -- Note: Lua io.popen doesn't provide direct process killing capability
    -- A full implementation would require platform-specific code with PID tracking
    -- For Windows: use taskkill /F /PID <pid> or taskkill /F /IM <process_name>
    -- For Unix: use kill -9 <pid>
    
    -- Return whether close was successful as a proxy
    return closeResult.success
end

return processUtils
