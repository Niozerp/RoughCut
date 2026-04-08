-- RoughCut Protocol Utility
-- Handles JSON-RPC communication with Python backend via stdout/stdin
-- Compatible with DaVinci Resolve's Lua scripting environment

local protocol = {}

-- Pending requests storage
local _pendingRequests = {}
local _requestCounter = 0

-- Logger (fallback if not available)
local logger = {
    info = function(msg) print("[Protocol] " .. tostring(msg)) end,
    error = function(msg) print("[Protocol Error] " .. tostring(msg)) end,
    debug = function(msg) end
}

-- Try to load the real logger
local ok, loggerModule = pcall(require, "utils.logger")
if ok and loggerModule then
    logger = loggerModule
end

--- Generate a unique request ID
-- @return string request ID
local function generateRequestId()
    _requestCounter = _requestCounter + 1
    return string.format("req_%d_%d", os.time(), _requestCounter)
end

--- Simple JSON encoding (basic implementation for Lua)
-- Handles strings, numbers, booleans, tables (arrays and objects)
-- @param data table to encode
-- @return string JSON string
function protocol.jsonEncode(data)
    if type(data) == "string" then
        -- Escape special characters
        local escaped = data:gsub('\\', '\\\\')
        escaped = escaped:gsub('"', '\\"')
        escaped = escaped:gsub('\n', '\\n')
        escaped = escaped:gsub('\r', '\\r')
        escaped = escaped:gsub('\t', '\\t')
        return '"' .. escaped .. '"'
    elseif type(data) == "number" then
        return tostring(data)
    elseif type(data) == "boolean" then
        return tostring(data)
    elseif type(data) == "nil" then
        return "null"
    elseif type(data) == "table" then
        -- Check if it's an array
        local isArray = true
        local maxIndex = 0
        for k, _ in pairs(data) do
            if type(k) ~= "number" or k < 1 then
                isArray = false
                break
            end
            if k > maxIndex then
                maxIndex = k
            end
        end
        
        -- Check for gaps in array indices
        if isArray then
            for i = 1, maxIndex do
                if data[i] == nil then
                    isArray = false
                    break
                end
            end
        end
        
        if isArray and maxIndex > 0 then
            -- Encode as array
            local parts = {}
            for i = 1, maxIndex do
                table.insert(parts, protocol.jsonEncode(data[i]))
            end
            return "[" .. table.concat(parts, ",") .. "]"
        else
            -- Encode as object
            local parts = {}
            for k, v in pairs(data) do
                if type(k) == "string" then
                    table.insert(parts, protocol.jsonEncode(k) .. ":" .. protocol.jsonEncode(v))
                end
            end
            return "{" .. table.concat(parts, ",") .. "}"
        end
    else
        return "null"
    end
end

--- Simple JSON parsing (basic implementation for Lua)
-- @param jsonString string to parse
-- @return table parsed data or nil on error
function protocol.jsonDecode(jsonString)
    if not jsonString or jsonString == "" then
        return nil
    end
    
    -- Very basic JSON parser - handles simple objects and arrays
    -- For production, consider using a proper JSON library
    local result = {}
    
    -- Trim whitespace
    jsonString = jsonString:gsub("^%s*", ""):gsub("%s*$", "")
    
    -- Check if it's an object
    if jsonString:sub(1, 1) == "{" and jsonString:sub(-1) == "}" then
        -- Remove outer braces
        local content = jsonString:sub(2, -2)
        
        -- Simple key-value parsing (doesn't handle nested structures well)
        -- This is a basic implementation - for complex JSON, use proper parser
        for key, value in content:gmatch('"([^"]+)":%s*([^,]+)') do
            -- Try to parse value
            value = value:gsub("^%s*", ""):gsub("%s*$", "")
            
            if value:sub(1, 1) == '"' and value:sub(-1) == '"' then
                -- String value
                result[key] = value:sub(2, -2):gsub('\\"', '"'):gsub('\\\\', '\\')
            elseif value == "true" then
                result[key] = true
            elseif value == "false" then
                result[key] = false
            elseif value == "null" then
                result[key] = nil
            elseif tonumber(value) then
                result[key] = tonumber(value)
            else
                result[key] = value
            end
        end
    elseif jsonString:sub(1, 1) == "[" and jsonString:sub(-1) == "]" then
        -- Array - basic parsing
        local content = jsonString:sub(2, -2)
        local index = 1
        for value in content:gmatch("([^,]+)") do
            value = value:gsub("^%s*", ""):gsub("%s*$", "")
            if value:sub(1, 1) == '"' and value:sub(-1) == '"' then
                result[index] = value:sub(2, -2)
            elseif value == "true" then
                result[index] = true
            elseif value == "false" then
                result[index] = false
            elseif tonumber(value) then
                result[index] = tonumber(value)
            else
                result[index] = value
            end
            index = index + 1
        end
    end
    
    return result
end

--- Send a request to the Python backend
-- Uses JSON-RPC format over stdout/stdin
-- @param method string method name to call
-- @param params table parameters for the method
-- @param callback function(response) callback for async response (optional)
-- @return boolean success
function protocol.sendRequest(method, params, callback)
    if not method then
        logger.error("Cannot send request: method is nil")
        return false
    end
    
    local requestId = generateRequestId()
    
    local request = {
        jsonrpc = "2.0",
        method = method,
        params = params or {},
        id = requestId
    }
    
    -- Store callback for async response
    if callback then
        _pendingRequests[requestId] = {
            callback = callback,
            timestamp = os.time()
        }
    end
    
    -- Encode and send
    local ok, jsonRequest = pcall(protocol.jsonEncode, request)
    if not ok then
        logger.error("Failed to encode request: " .. tostring(jsonRequest))
        return false
    end
    
    -- Send via stdout (Python backend reads from our stdout)
    local sendOk, sendErr = pcall(function()
        io.write(jsonRequest .. "\n")
        io.flush()
    end)
    
    if not sendOk then
        logger.error("Failed to send request: " .. tostring(sendErr))
        _pendingRequests[requestId] = nil
        return false
    end
    
    logger.debug("Sent request: " .. method .. " (id: " .. requestId .. ")")
    return true
end

--- Handle a response from the Python backend
-- This should be called by the main loop when responses are received
-- @param responseString string JSON response from Python
function protocol.handleResponse(responseString)
    if not responseString or responseString == "" then
        return
    end
    
    local ok, response = pcall(protocol.jsonDecode, responseString)
    if not ok or not response then
        logger.error("Failed to parse response: " .. tostring(response))
        return
    end
    
    local requestId = response.id
    if not requestId then
        logger.error("Response missing request ID")
        return
    end
    
    local pending = _pendingRequests[requestId]
    if pending and pending.callback then
        -- Call the callback
        local cbOk, cbErr = pcall(pending.callback, response)
        if not cbOk then
            logger.error("Callback error for request " .. requestId .. ": " .. tostring(cbErr))
        end
        
        -- Clean up
        _pendingRequests[requestId] = nil
    else
        logger.debug("No pending callback for request: " .. requestId)
    end
end

--- Clean up old pending requests (call periodically)
-- @param maxAgeSeconds number maximum age before cleanup (default 300 = 5 minutes)
function protocol.cleanupOldRequests(maxAgeSeconds)
    maxAgeSeconds = maxAgeSeconds or 300
    local now = os.time()
    local toRemove = {}
    
    for id, pending in pairs(_pendingRequests) do
        if now - pending.timestamp > maxAgeSeconds then
            table.insert(toRemove, id)
        end
    end
    
    for _, id in ipairs(toRemove) do
        logger.debug("Cleaning up stale request: " .. id)
        _pendingRequests[id] = nil
    end
end

--- Check if there are pending requests
-- @return boolean
function protocol.hasPendingRequests()
    for _ in pairs(_pendingRequests) do
        return true
    end
    return false
end

--- Get count of pending requests
-- @return number
function protocol.getPendingRequestCount()
    local count = 0
    for _ in pairs(_pendingRequests) do
        count = count + 1
    end
    return count
end

return protocol
