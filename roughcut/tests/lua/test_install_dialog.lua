-- Tests for install_dialog.lua
-- These tests validate the installation dialog UI component

local installDialog = require("ui.install_dialog")

-- Mock UI Manager for testing
local MockUIManager = {}
MockUIManager.__index = MockUIManager

function MockUIManager.new()
    local self = setmetatable({}, MockUIManager)
    self.windows = {}
    self.elements = {}
    return self
end

function MockUIManager:Add(config)
    local window = {
        type = config.type,
        id = config.id,
        elements = {},
        visible = false,
        closed = false
    }
    
    window.Add = function(self, elemConfig)
        local element = {
            type = elemConfig.type,
            id = elemConfig.id,
            text = elemConfig.text,
            value = elemConfig.value,
            enabled = true,
            clicked = nil
        }
        table.insert(self.elements, element)
        return element
    end
    
    window.Show = function(self)
        self.visible = true
    end
    
    window.Hide = function(self)
        self.visible = false
    end
    
    window.Close = function(self)
        self.closed = true
    end
    
    table.insert(self.windows, window)
    return window
end

-- Test 1: Dialog creation
local function testDialogCreation()
    print("Test 1: Dialog creation...")
    
    local mockUI = MockUIManager.new()
    local window = installDialog.create(mockUI)
    
    if not window then
        print("  FAILED: Window not created")
        return false
    end
    
    if window.id ~= "RoughCutInstallDialog" then
        print("  FAILED: Wrong window ID: " .. tostring(window.id))
        return false
    end
    
    if #window.elements < 6 then
        print("  FAILED: Expected at least 6 elements, got " .. #window.elements)
        return false
    end
    
    print("  PASSED")
    return true
end

-- Test 2: Show/Hide functionality
local function testShowHide()
    print("Test 2: Show/Hide functionality...")
    
    local mockUI = MockUIManager.new()
    local window = installDialog.create(mockUI)
    
    if not installDialog.show() then
        print("  FAILED: Show failed")
        return false
    end
    
    if not window.visible then
        print("  FAILED: Window not visible after show")
        return false
    end
    
    if not installDialog.hide() then
        print("  FAILED: Hide failed")
        return false
    end
    
    if window.visible then
        print("  FAILED: Window still visible after hide")
        return false
    end
    
    print("  PASSED")
    return true
end

-- Test 3: Progress updates
local function testProgressUpdates()
    print("Test 3: Progress updates...")
    
    local mockUI = MockUIManager.new()
    installDialog.create(mockUI)
    
    local result = installDialog.updateProgress(2, 5, "Installing dependencies...", 40)
    if not result then
        print("  FAILED: Update progress returned false")
        return false
    end
    
    print("  PASSED")
    return true
end

-- Test 4: Cancel functionality
local function testCancelFunctionality()
    print("Test 4: Cancel functionality...")
    
    local mockUI = MockUIManager.new()
    installDialog.create(mockUI)
    
    if installDialog.isCancelled() then
        print("  FAILED: Cancelled flag should be false initially")
        return false
    end
    
    installDialog.resetCancel()
    
    if installDialog.isCancelled() then
        print("  FAILED: Cancelled flag should still be false after reset")
        return false
    end
    
    print("  PASSED")
    return true
end

-- Test 5: State tracking
local function testStateTracking()
    print("Test 5: State tracking...")
    
    local mockUI = MockUIManager.new()
    installDialog.create(mockUI)
    
    local state = installDialog.getState()
    
    if state.isCancelled == nil then
        print("  FAILED: isCancelled not in state")
        return false
    end
    
    if state.elapsedSeconds == nil then
        print("  FAILED: elapsedSeconds not in state")
        return false
    end
    
    print("  PASSED")
    return true
end

-- Test 6: Dialog close
local function testDialogClose()
    print("Test 6: Dialog close...")
    
    local mockUI = MockUIManager.new()
    local window = installDialog.create(mockUI)
    
    if not installDialog.close() then
        print("  FAILED: Close failed")
        return false
    end
    
    if not window.closed then
        print("  FAILED: Window not marked as closed")
        return false
    end
    
    print("  PASSED")
    return true
end

-- Test 7: Error without UI manager
local function testErrorWithoutUIManager()
    print("Test 7: Error handling without UI manager...")
    
    local window = installDialog.create(nil)
    if window then
        print("  FAILED: Should return nil without UI manager")
        return false
    end
    
    print("  PASSED")
    return true
end

-- Test 8: Completion display
local function testCompletionDisplay()
    print("Test 8: Completion display...")
    
    local mockUI = MockUIManager.new()
    installDialog.create(mockUI)
    
    installDialog.showCompletion()
    
    -- Should not throw errors
    print("  PASSED")
    return true
end

-- Test 9: Error display
local function testErrorDisplay()
    print("Test 9: Error display...")
    
    local mockUI = MockUIManager.new()
    installDialog.create(mockUI)
    
    installDialog.showError("Test error message")
    
    -- Should not throw errors
    print("  PASSED")
    return true
end

-- Run all tests
local function runAllTests()
    print("\n=== Running Install Dialog Tests ===\n")
    
    local tests = {
        testDialogCreation,
        testShowHide,
        testProgressUpdates,
        testCancelFunctionality,
        testStateTracking,
        testDialogClose,
        testErrorWithoutUIManager,
        testCompletionDisplay,
        testErrorDisplay
    }
    
    local passed = 0
    local failed = 0
    
    for _, test in ipairs(tests) do
        local success, result = pcall(test)
        if success and result then
            passed = passed + 1
        else
            failed = failed + 1
            if not success then
                print("  ERROR: " .. tostring(result))
            end
        end
    end
    
    print("\n=== Test Results ===")
    print("Passed: " .. passed .. "/" .. #tests)
    print("Failed: " .. failed .. "/" .. #tests)
    
    if failed == 0 then
        print("\nAll tests passed!")
        return 0
    else
        print("\nSome tests failed!")
        return 1
    end
end

-- Execute tests if run directly
if arg and arg[0]:match("test_install_dialog%.lua$") then
    os.exit(runAllTests())
end

return {
    runAllTests = runAllTests
}
