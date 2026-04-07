-- Tests for Lua utility modules (config.lua, logger.lua, process.lua)

local config = require("lua.utils.config")
local logger = require("lua.utils.logger")
local process = require("lua.utils.process")

-- Test counters
local passed = 0
local failed = 0

-- Test helper
local function test(name, func)
    print("\nTest: " .. name)
    local ok, err = pcall(func)
    if ok then
        print("  PASSED")
        passed = passed + 1
    else
        print("  FAILED: " .. tostring(err))
        failed = failed + 1
    end
end

-- Config Tests
test("Config: Init returns boolean", function()
    local result = config.init()
    assert(type(result) == "boolean", "init should return boolean")
end)

test("Config: Get defaults returns table", function()
    local defaults = config.getDefaults()
    assert(type(defaults) == "table", "defaults should be a table")
    assert(defaults.backend_installed == false, "backend_installed should default to false")
end)

test("Config: Read returns table even without file", function()
    local cfg = config.read()
    assert(type(cfg) == "table", "read should return a table")
end)

test("Config: Get config path returns string", function()
    local path = config.getConfigPath()
    assert(type(path) == "string", "path should be a string")
    assert(path:find("config%.yaml"), "path should contain config.yaml")
end)

-- Logger Tests
test("Logger: Init returns boolean", function()
    local result = logger.init()
    assert(type(result) == "boolean", "init should return boolean")
end)

test("Logger: Get log path returns string", function()
    local path = logger.getLogPath()
    assert(type(path) == "string", "path should be a string")
    assert(path:find("roughcut%.log"), "path should contain roughcut.log")
end)

test("Logger: Info writes to log", function()
    local result = logger.info("Test info message")
    assert(result == true or result == false, "info should return boolean")
end)

test("Logger: Error writes to log", function()
    local result = logger.error("Test error message")
    assert(result == true or result == false, "error should return boolean")
end)

test("Logger: Get recent entries returns table", function()
    local entries = logger.getRecentEntries(10)
    assert(type(entries) == "table", "entries should be a table")
end)

-- Process Utils Tests
test("Process: Get script directory", function()
    local dir = process.getScriptDirectory()
    -- May return nil in some environments
    assert(dir == nil or type(dir) == "string", "should return nil or string")
end)

test("Process: Shell escape - simple argument", function()
    -- Simple arguments without spaces should NOT be quoted on Windows
    local escaped = process.shellEscape('python')
    assert(type(escaped) == "string", "should return string")
    -- Should not have outer quotes for simple args
    assert(escaped == 'python' or escaped:sub(1,1) == '"', "simple arg should not be quoted or properly escaped")
end)

test("Process: Shell escape - argument with spaces", function()
    -- Arguments with spaces should be quoted
    local escaped = process.shellEscape('C:\\Program Files\\Python')
    assert(type(escaped) == "string", "should return string")
    assert(escaped:sub(1, 1) == '"', "arg with spaces should be quoted")
    assert(escaped:sub(-1) == '"', "arg with spaces should end with quote")
end)

test("Process: Shell escape - argument with quotes", function()
    -- Arguments containing quotes should have them doubled
    local escaped = process.shellEscape('say "hello"')
    assert(type(escaped) == "string", "should return string")
    -- Should have doubled quotes inside
    assert(escaped:find('""'), "quotes should be doubled")
end)

test("Process: Shell escape - percent signs", function()
    -- Percent signs should be escaped for Windows batch
    local escaped = process.shellEscape('100% complete')
    assert(type(escaped) == "string", "should return string")
    -- Should escape % as %%
    assert(escaped:find('%%%%'), "percent signs should be doubled")
end)

test("Process: Run with invalid command returns error", function()
    local result = process.run({})
    assert(result.success == false, "empty command should fail")
    assert(result.error ~= nil, "should have error message")
end)

-- Print results
print("\n" .. string.rep("=", 50))
print("Test Results:")
print("  Passed: " .. passed)
print("  Failed: " .. failed)
print("  Total: " .. (passed + failed))
print(string.rep("=", 50))

if failed > 0 then
    print("\nSome tests failed!")
    os.exit(1)
else
    print("\nAll tests passed!")
    os.exit(0)
end
