-- RoughCut Lua UI Tests
-- Test suite for main window, navigation, and child windows
-- Compatible with both Resolve and standalone Lua environments
-- Version: 0.1.0

local tests = {}

-- Test results tracking
local testResults = {
    passed = 0,
    failed = 0,
    errors = {}
}

-- Mock UI Manager for testing outside Resolve
local function createMockUIManager()
    local mockWindows = {}
    local windowIdCounter = 0
    
    return {
        Add = function(self, config)
            windowIdCounter = windowIdCounter + 1
            local window = {
                id = config.id or ("MockWindow" .. windowIdCounter),
                type = config.type,
                children = {},
                visible = false,
                _config = config,
                
                Add = function(self, childConfig)
                    table.insert(self.children, childConfig)
                    return {
                        _config = childConfig,
                        Visible = true,
                        Text = childConfig.text or "",
                        Clicked = nil
                    }
                end,
                
                Show = function(self)
                    self.visible = true
                    return true
                end,
                
                Hide = function(self)
                    self.visible = false
                    return true
                end,
                
                Close = function(self)
                    self.visible = false
                    mockWindows[self.id] = nil
                    return true
                end
            }
            
            mockWindows[window.id] = window
            return window
        end,
        
        ShowMessageBox = function(self, message, title, button)
            print("[Mock MessageBox] " .. title .. ": " .. message)
            return "OK"
        end,
        
        _mockWindows = mockWindows
    }
end

-- Test assertion helper
local function assert(condition, message)
    if not condition then
        error(message or "Assertion failed", 2)
    end
end

-- Run a single test
local function runTest(testName, testFunc)
    print("\n[TEST] " .. testName)
    local ok, err = pcall(testFunc)
    
    if ok then
        testResults.passed = testResults.passed + 1
        print("  ✓ PASSED")
        return true
    else
        testResults.failed = testResults.failed + 1
        table.insert(testResults.errors, { name = testName, error = err })
        print("  ✗ FAILED: " .. tostring(err))
        return false
    end
end

-- ==================== TESTS ====================

-- Test 1: Main Window Creation
function tests.testMainWindowCreation()
    local mainWindow = require("ui.main_window")
    local mockUI = createMockUIManager()
    
    local window = mainWindow.create(mockUI)
    
    assert(window ~= nil, "Main window should be created")
    assert(window.id == "RoughCutMainWindow", "Window should have correct ID")
    assert(window._config.title:find("RoughCut"), "Window should have RoughCut title")
    assert(window._config.width == 400, "Window should have correct width")
    assert(window._config.height == 500, "Window should have correct height")
    
    -- Check that header and footer elements were added
    assert(#window.children >= 4, "Window should have at least header, subtitle, spacer, and footer")
end

-- Test 2: Main Window Show/Hide/Close
function tests.testMainWindowLifecycle()
    local mainWindow = require("ui.main_window")
    local mockUI = createMockUIManager()
    
    local window = mainWindow.create(mockUI)
    
    -- Test show
    local showResult = mainWindow.show(window)
    assert(showResult == true, "Show should return true")
    assert(window.visible == true, "Window should be visible after show")
    
    -- Test hide
    local hideResult = mainWindow.hide(window)
    assert(hideResult == true, "Hide should return true")
    assert(window.visible == false, "Window should not be visible after hide")
    
    -- Test close
    local closeResult = mainWindow.close(window)
    assert(closeResult == true, "Close should return true")
end

-- Test 3: Main Window Error Handling
function tests.testMainWindowErrorHandling()
    local mainWindow = require("ui.main_window")
    
    -- Test with nil UI manager
    local window = mainWindow.create(nil)
    assert(window == nil, "Should return nil when UI manager is nil")
    
    -- Test show with nil window
    local showResult = mainWindow.show(nil)
    assert(showResult == false, "Show should return false for nil window")
    
    -- Test hide with nil window
    local hideResult = mainWindow.hide(nil)
    assert(hideResult == false, "Hide should return false for nil window")
    
    -- Test close with nil window
    local closeResult = mainWindow.close(nil)
    assert(closeResult == false, "Close should return false for nil window")
end

-- Test 4: Navigation Creation
function tests.testNavigationCreation()
    local navigation = require("ui.navigation")
    local mainWindow = require("ui.main_window")
    local mockUI = createMockUIManager()
    
    local window = mainWindow.create(mockUI)
    
    -- Set UI Manager for navigation
    navigation.setUIManager(mockUI)
    
    local result = navigation.create(window)
    assert(result == true, "Navigation creation should succeed")
end

-- Test 5: Navigation State Management
function tests.testNavigationState()
    local navigation = require("ui.navigation")
    local mainWindow = require("ui.main_window")
    local mockUI = createMockUIManager()
    
    local window = mainWindow.create(mockUI)
    navigation.setUIManager(mockUI)
    navigation.create(window)
    
    -- Initial state should be HOME
    assert(navigation.getCurrentState() == "home", "Initial state should be home")
    assert(navigation.isHome() == true, "isHome should return true initially")
    assert(navigation.isMainScreen() == true, "isMainScreen should return true initially")
    
    -- Test state transitions (mock navigation)
    navigation.handleNavigation("btnManageMedia")
    assert(navigation.getCurrentState() == "media_management", "State should be media_management after clicking Manage Media")
    assert(navigation.isHome() == false, "isHome should return false after navigation")
end

-- Test 6: Navigation Reset
function tests.testNavigationReset()
    local navigation = require("ui.navigation")
    local mainWindow = require("ui.main_window")
    local mockUI = createMockUIManager()
    
    local window = mainWindow.create(mockUI)
    navigation.setUIManager(mockUI)
    navigation.create(window)
    
    -- Navigate away from home
    navigation.handleNavigation("btnManageMedia")
    assert(navigation.isHome() == false, "Should not be home after navigation")
    
    -- Reset and verify
    navigation.reset()
    assert(navigation.getCurrentState() == "home", "State should reset to home")
    assert(navigation.isHome() == true, "isHome should return true after reset")
end

-- Test 7: Media Management Window Creation
function tests.testMediaManagementWindow()
    local mediaManagement = require("ui.media_management")
    local mockUI = createMockUIManager()
    local mockParent = { id = "ParentWindow" }
    
    local window = mediaManagement.create(mockUI, mockParent)
    
    assert(window ~= nil, "Media management window should be created")
    assert(window.id == "RoughCutMediaManagement", "Window should have correct ID")
    assert(window._config.title:find("Media Management"), "Window should have Media Management title")
end

-- Test 8: Format Management Window Creation
function tests.testFormatManagementWindow()
    local formatManagement = require("ui.format_management")
    local mockUI = createMockUIManager()
    local mockParent = { id = "ParentWindow" }
    
    local window = formatManagement.create(mockUI, mockParent)
    
    assert(window ~= nil, "Format management window should be created")
    assert(window.id == "RoughCutFormatManagement", "Window should have correct ID")
    assert(window._config.title:find("Format Management"), "Window should have Format Management title")
end

-- Test 9: Rough Cut Workflow Window Creation
function tests.testRoughCutWorkflowWindow()
    local roughCutWorkflow = require("ui.rough_cut_workflow")
    local mockUI = createMockUIManager()
    local mockParent = { id = "ParentWindow" }
    
    local window = roughCutWorkflow.create(mockUI, mockParent)
    
    assert(window ~= nil, "Rough cut workflow window should be created")
    assert(window.id == "RoughCutWorkflow", "Window should have correct ID")
    assert(window._config.title:find("Create Rough Cut"), "Window should have Create Rough Cut title")
end

-- Test 10: Child Windows Have Back Buttons
function tests.testChildWindowsBackButtons()
    local mockUI = createMockUIManager()
    local mockParent = { id = "ParentWindow" }
    
    -- Test media management
    local mediaManagement = require("ui.media_management")
    local mediaWindow = mediaManagement.create(mockUI, mockParent)
    local hasBackButton = false
    for _, child in ipairs(mediaWindow.children) do
        if child._config and child._config.id == "btnBackToMain" then
            hasBackButton = true
            break
        end
    end
    assert(hasBackButton, "Media management window should have back button")
    
    -- Test format management
    local formatManagement = require("ui.format_management")
    local formatWindow = formatManagement.create(mockUI, mockParent)
    hasBackButton = false
    for _, child in ipairs(formatWindow.children) do
        if child._config and child._config.id == "btnBackToMain" then
            hasBackButton = true
            break
        end
    end
    assert(hasBackButton, "Format management window should have back button")
    
    -- Test rough cut workflow
    local roughCutWorkflow = require("ui.rough_cut_workflow")
    local workflowWindow = roughCutWorkflow.create(mockUI, mockParent)
    hasBackButton = false
    for _, child in ipairs(workflowWindow.children) do
        if child._config and child._config.id == "btnBackToMain" then
            hasBackButton = true
            break
        end
    end
    assert(hasBackButton, "Rough cut workflow window should have back button")
end

-- Test 11: Main Window Footer
function tests.testMainWindowFooter()
    local mainWindow = require("ui.main_window")
    local mockUI = createMockUIManager()
    
    local window = mainWindow.create(mockUI)
    
    -- Check for footer elements (version info)
    local hasFooter = false
    for _, child in ipairs(window.children) do
        if child._config and child._config.id == "footerStatusLabel" then
            hasFooter = true
            -- Check that it contains version info
            assert(child._config.text:find("Version"), "Footer should contain version info")
            break
        end
    end
    assert(hasFooter, "Main window should have footer with status label")
end

-- Test 12: Navigation Button Configuration
function tests.testNavigationButtonConfig()
    local navigation = require("ui.navigation")
    local mainWindow = require("ui.main_window")
    local mockUI = createMockUIManager()
    
    local window = mainWindow.create(mockUI)
    navigation.setUIManager(mockUI)
    navigation.create(window)
    
    -- Check that all three navigation buttons were created
    -- The buttons are added as children with specific patterns
    local buttonCount = 0
    local hasManageMedia = false
    local hasManageFormats = false
    local hasCreateRoughCut = false
    
    for _, child in ipairs(window.children) do
        if child._config then
            if child._config.id == "btnManageMedia" then
                hasManageMedia = true
                buttonCount = buttonCount + 1
            elseif child._config.id == "btnManageFormats" then
                hasManageFormats = true
                buttonCount = buttonCount + 1
            elseif child._config.id == "btnCreateRoughCut" then
                hasCreateRoughCut = true
                buttonCount = buttonCount + 1
            end
        end
    end
    
    assert(buttonCount == 3, "Should have exactly 3 navigation buttons, found " .. buttonCount)
    assert(hasManageMedia, "Should have Manage Media button")
    assert(hasManageFormats, "Should have Manage Formats button")
    assert(hasCreateRoughCut, "Should have Create Rough Cut button")
end

-- Test 13: Child Window Show/Hide/Close
function tests.testChildWindowLifecycle()
    local mediaManagement = require("ui.media_management")
    local mockUI = createMockUIManager()
    local mockParent = { id = "ParentWindow", Show = function() return true end }
    
    local window = mediaManagement.create(mockUI, mockParent)
    
    -- Test show
    local showResult = mediaManagement.show()
    assert(showResult == true, "Show should return true")
    assert(window.visible == true, "Window should be visible after show")
    
    -- Test hide
    local hideResult = mediaManagement.hide()
    assert(hideResult == true, "Hide should return true")
    assert(window.visible == false, "Window should not be visible after hide")
    
    -- Test close
    local closeResult = mediaManagement.close()
    assert(closeResult == true, "Close should return true")
end

-- Test 14: Main Window Status Update
function tests.testMainWindowStatusUpdate()
    local mainWindow = require("ui.main_window")
    local mockUI = createMockUIManager()
    
    mainWindow.create(mockUI)
    
    -- Test updating status
    local updateResult = mainWindow.updateStatus("Processing...")
    assert(updateResult == true, "Status update should succeed")
end

-- ==================== TEST RUNNER ====================

-- Run all tests
function tests.runAll()
    print("\n" .. string.rep("=", 60))
    print("RoughCut Lua UI Test Suite")
    print(string.rep("=", 60))
    
    -- Clear previous results
    testResults = { passed = 0, failed = 0, errors = {} }
    
    -- Run each test
    runTest("Main Window Creation", tests.testMainWindowCreation)
    runTest("Main Window Lifecycle", tests.testMainWindowLifecycle)
    runTest("Main Window Error Handling", tests.testMainWindowErrorHandling)
    runTest("Navigation Creation", tests.testNavigationCreation)
    runTest("Navigation State Management", tests.testNavigationState)
    runTest("Navigation Reset", tests.testNavigationReset)
    runTest("Media Management Window", tests.testMediaManagementWindow)
    runTest("Format Management Window", tests.testFormatManagementWindow)
    runTest("Rough Cut Workflow Window", tests.testRoughCutWorkflowWindow)
    runTest("Child Windows Back Buttons", tests.testChildWindowsBackButtons)
    runTest("Main Window Footer", tests.testMainWindowFooter)
    runTest("Navigation Button Configuration", tests.testNavigationButtonConfig)
    runTest("Child Window Lifecycle", tests.testChildWindowLifecycle)
    runTest("Main Window Status Update", tests.testMainWindowStatusUpdate)
    
    -- Print summary
    print("\n" .. string.rep("=", 60))
    print("Test Summary")
    print(string.rep("=", 60))
    print("Passed: " .. testResults.passed)
    print("Failed: " .. testResults.failed)
    print("Total:  " .. (testResults.passed + testResults.failed))
    
    if testResults.failed > 0 then
        print("\nFailed Tests:")
        for _, error in ipairs(testResults.errors) do
            print("  - " .. error.name .. ": " .. error.error)
        end
    end
    
    print(string.rep("=", 60))
    
    return testResults.failed == 0
end

-- Run tests if executed directly
if arg and arg[0]:find("test_ui.lua") then
    tests.runAll()
end

return tests
