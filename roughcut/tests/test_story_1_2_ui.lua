-- RoughCut UI Tests for Story 1.2
-- Tests for main_window.lua and navigation.lua components
-- Run within DaVinci Resolve's Lua scripting environment

local mainWindow = require("ui.main_window")
local navigation = require("ui.navigation")

-- Test framework (simple version)
local tests = {}
local testResults = { passed = 0, failed = 0, errors = {} }

function tests.assertEquals(expected, actual, message)
    if expected ~= actual then
        local errorMsg = (message or "Assertion failed") .. 
                        ": Expected " .. tostring(expected) .. 
                        ", got " .. tostring(actual)
        table.insert(testResults.errors, errorMsg)
        testResults.failed = testResults.failed + 1
        return false
    end
    testResults.passed = testResults.passed + 1
    return true
end

function tests.assertTrue(value, message)
    return tests.assertEquals(true, value, message)
end

function tests.assertFalse(value, message)
    return tests.assertEquals(false, value, message)
end

function tests.assertNotNil(value, message)
    if value == nil then
        table.insert(testResults.errors, (message or "Value is nil"))
        testResults.failed = testResults.failed + 1
        return false
    end
    testResults.passed = testResults.passed + 1
    return true
end

-- Mock Resolve UI Manager for testing
local mockUiManager = {}
local mockWindows = {}
local mockWidgets = {}

function mockUiManager:Add(config)
    local widget = {
        type = config.type,
        id = config.id,
        text = config.text,
        visible = config.visible ~= false,
        height = config.height,
        Clicked = nil
    }
    
    -- Simulate widget methods
    widget.Show = function() widget.visible = true end
    widget.Hide = function() widget.visible = false end
    widget.Close = function() widget.visible = false end
    widget.Add = function(childConfig) 
        return mockUiManager:Add(childConfig)
    end
    
    table.insert(mockWidgets, widget)
    
    if config.type == "Window" then
        table.insert(mockWindows, widget)
    end
    
    return widget
end

-- Test 1: Main Window Creation
function tests.testMainWindowCreate()
    mockWindows = {}
    mockWidgets = {}
    
    local window = mainWindow.create(mockUiManager)
    
    tests.assertNotNil(window, "Main window should be created")
    tests.assertEquals(1, #mockWindows, "Should create exactly one window")
    tests.assertEquals("RoughCutMainWindow", mockWindows[1].id, "Window ID should be set")
    tests.assertEquals("RoughCut - AI-Powered Rough Cut Generator", mockWindows[1].title, "Window title should be set")
end

-- Test 2: Main Window Show/Hide
function tests.testMainWindowShowHide()
    mockWindows = {}
    mockWidgets = {}
    
    local window = mainWindow.create(mockUiManager)
    
    tests.assertNotNil(window, "Window should be created")
    tests.assertFalse(window.visible, "Window should start hidden")
    
    local showResult = mainWindow.show(window)
    tests.assertTrue(showResult, "Show should return true")
    tests.assertTrue(window.visible, "Window should be visible after show")
    
    local hideResult = mainWindow.hide(window)
    tests.assertTrue(hideResult, "Hide should return true")
    tests.assertFalse(window.visible, "Window should be hidden after hide")
end

-- Test 3: Navigation Creation
function tests.testNavigationCreate()
    mockWindows = {}
    mockWidgets = {}
    
    local window = mainWindow.create(mockUiManager)
    local navResult = navigation.create(window)
    
    tests.assertTrue(navResult, "Navigation creation should return true")
    
    -- Count buttons (should have navigation buttons + return button)
    local buttonCount = 0
    for _, widget in ipairs(mockWidgets) do
        if widget.type == "Button" then
            buttonCount = buttonCount + 1
        end
    end
    
    -- 3 navigation buttons + 1 return button = 4 buttons
    tests.assertEquals(4, buttonCount, "Should create 4 buttons (3 nav + 1 return)")
end

-- Test 4: Navigation State Management
function tests.testNavigationState()
    mockWindows = {}
    mockWidgets = {}
    
    local window = mainWindow.create(mockUiManager)
    navigation.create(window)
    
    -- Initial state should be main
    tests.assertEquals("main", navigation.getCurrentScreen(), "Initial screen should be main")
    tests.assertTrue(navigation.isMainScreen(), "Should be on main screen initially")
    
    -- Simulate navigation to Manage Media
    navigation.handleNavigation("btnManageMedia")
    tests.assertEquals("btnManageMedia", navigation.getCurrentScreen(), "Screen should be btnManageMedia")
    tests.assertFalse(navigation.isMainScreen(), "Should not be on main screen")
    
    -- Return to main
    navigation.returnToMain()
    tests.assertEquals("main", navigation.getCurrentScreen(), "Screen should return to main")
    tests.assertTrue(navigation.isMainScreen(), "Should be on main screen after return")
end

-- Test 5: Error Handling - Nil UI Manager
function tests.testMainWindowNilUiManager()
    local window = mainWindow.create(nil)
    tests.assertEquals(nil, window, "Should return nil for nil UI manager")
end

-- Test 6: Error Handling - Nil Window for Navigation
function tests.testNavigationNilWindow()
    local result = navigation.create(nil)
    tests.assertFalse(result, "Should return false for nil window")
end

-- Test 7: Error Handling - Nil Window Operations
function tests.testMainWindowNilOperations()
    local showResult = mainWindow.show(nil)
    tests.assertFalse(showResult, "Show should return false for nil window")
    
    local hideResult = mainWindow.hide(nil)
    tests.assertFalse(hideResult, "Hide should return false for nil window")
    
    local closeResult = mainWindow.close(nil)
    tests.assertFalse(closeResult, "Close should return false for nil window")
end

-- Test 8: Navigation Reset
function tests.testNavigationReset()
    mockWindows = {}
    mockWidgets = {}
    
    local window = mainWindow.create(mockUiManager)
    navigation.create(window)
    
    -- Navigate away
    navigation.handleNavigation("btnCreateRoughCut")
    tests.assertFalse(navigation.isMainScreen(), "Should not be on main screen")
    
    -- Reset
    navigation.reset()
    tests.assertEquals("main", navigation.getCurrentScreen(), "Should be main after reset")
    tests.assertTrue(navigation.isMainScreen(), "isMainScreen should be true after reset")
end

-- Run all tests
function tests.runAll()
    print("\n" .. string.rep("=", 60))
    print("RoughCut UI Tests - Story 1.2: Scripts Menu Integration")
    print(string.rep("=", 60) .. "\n")
    
    local testFunctions = {
        { "testMainWindowCreate", tests.testMainWindowCreate },
        { "testMainWindowShowHide", tests.testMainWindowShowHide },
        { "testNavigationCreate", tests.testNavigationCreate },
        { "testNavigationState", tests.testNavigationState },
        { "testMainWindowNilUiManager", tests.testMainWindowNilUiManager },
        { "testNavigationNilWindow", tests.testNavigationNilWindow },
        { "testMainWindowNilOperations", tests.testMainWindowNilOperations },
        { "testNavigationReset", tests.testNavigationReset }
    }
    
    for _, testInfo in ipairs(testFunctions) do
        local name, func = testInfo[1], testInfo[2]
        local ok, err = pcall(func)
        
        if ok then
            print("✓ " .. name)
        else
            print("✗ " .. name .. " - ERROR: " .. tostring(err))
            testResults.failed = testResults.failed + 1
            table.insert(testResults.errors, name .. ": " .. tostring(err))
        end
    end
    
    print("\n" .. string.rep("-", 60))
    print("Results: " .. testResults.passed .. " passed, " .. testResults.failed .. " failed")
    print(string.rep("=", 60) .. "\n")
    
    if #testResults.errors > 0 then
        print("Errors:")
        for _, err in ipairs(testResults.errors) do
            print("  - " .. err)
        end
        print("")
    end
    
    return testResults.failed == 0
end

-- Execute tests
return tests.runAll()
