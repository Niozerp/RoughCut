-- RoughCut Installation Progress Dialog
-- Displays installation progress with step indicators and cancel button
-- Compatible with DaVinci Resolve's Lua scripting environment

local installDialog = {}

-- Dialog configuration
local DIALOG_CONFIG = {
    title = "RoughCut - Installing Python Backend",
    width = 450,
    height = 350,
    id = "RoughCutInstallDialog"
}

-- UI element references
local windowRef = nil
local progressBarRef = nil
local statusLabelRef = nil
local stepLabelRef = nil
local timeLabelRef = nil
local cancelButtonRef = nil
local uiManagerRef = nil

-- State tracking
local isCancelled = false
local startTime = nil
local currentStep = 0
local totalSteps = 5

-- Callback function for cancel action
local onCancelCallback = nil

-- Create the installation progress dialog
-- @param uiManager Resolve UI Manager instance
-- @return window table or nil on error
function installDialog.create(uiManager)
    if not uiManager then
        print("RoughCut: Error - UI Manager required for install dialog")
        return nil
    end
    
    uiManagerRef = uiManager
    isCancelled = false
    startTime = os.time()
    currentStep = 0
    
    -- Create window
    local ok, window = pcall(function()
        return uiManager:Add({
            type = "Window",
            id = DIALOG_CONFIG.id,
            title = DIALOG_CONFIG.title,
            width = DIALOG_CONFIG.width,
            height = DIALOG_CONFIG.height,
            spacing = 15,
            padding = 20
        })
    end)
    
    if not ok or not window then
        print("RoughCut: Error - Failed to create install dialog")
        return nil
    end
    
    windowRef = window
    
    -- Add header label
    local okHeader, headerLabel = pcall(function()
        return window:Add({
            type = "Label",
            text = "Setting up RoughCut Python Backend",
            font = { size = 16, bold = true },
            alignment = { alignHCenter = true }
        })
    end)
    
    if not okHeader then
        print("RoughCut: Warning - Could not add install dialog header")
    end
    
    -- Add status label
    local okStatus, statusLabel = pcall(function()
        return window:Add({
            type = "Label",
            id = "StatusLabel",
            text = "Checking Python installation...",
            font = { size = 12 },
            alignment = { alignHCenter = true }
        })
    end)
    
    if okStatus then
        statusLabelRef = statusLabel
    else
        print("RoughCut: Warning - Could not add status label")
    end
    
    -- Add step counter label
    local okStep, stepLabel = pcall(function()
        return window:Add({
            type = "Label",
            id = "StepLabel",
            text = "Step 1 of 5",
            font = { size = 11 },
            alignment = { alignHCenter = true }
        })
    end)
    
    if okStep then
        stepLabelRef = stepLabel
    else
        print("RoughCut: Warning - Could not add step label")
    end
    
    -- Add progress bar
    local okProgress, progressBar = pcall(function()
        return window:Add({
            type = "ProgressBar",
            id = "InstallProgressBar",
            minimum = 0,
            maximum = 100,
            value = 0,
            width = 400
        })
    end)
    
    if okProgress then
        progressBarRef = progressBar
    else
        print("RoughCut: Warning - Could not add progress bar")
    end
    
    -- Add time elapsed label
    local okTime, timeLabel = pcall(function()
        return window:Add({
            type = "Label",
            id = "TimeLabel",
            text = "Time elapsed: 0s",
            font = { size = 10 },
            alignment = { alignHCenter = true }
        })
    end)
    
    if okTime then
        timeLabelRef = timeLabel
    else
        print("RoughCut: Warning - Could not add time label")
    end
    
    -- Add estimated time remaining label
    local okEta, etaLabel = pcall(function()
        return window:Add({
            type = "Label",
            id = "EtaLabel",
            text = "Estimated time remaining: calculating...",
            font = { size = 10, italic = true },
            alignment = { alignHCenter = true }
        })
    end)
    
    if not okEta then
        print("RoughCut: Warning - Could not add ETA label")
    end
    
    -- Add cancel button
    local okCancel, cancelButton = pcall(function()
        return window:Add({
            type = "Button",
            id = "CancelButton",
            text = "Cancel Installation",
            width = 150,
            alignment = { alignHCenter = true }
        })
    end)
    
    if okCancel then
        cancelButtonRef = cancelButton
        -- Set up cancel button callback
        local okClick, _ = pcall(function()
            cancelButton.Clicked = function()
                isCancelled = true
                if onCancelCallback then
                    onCancelCallback()
                end
                print("RoughCut: Installation cancelled by user")
            end
        end)
        
        if not okClick then
            print("RoughCut: Warning - Could not set cancel button callback")
        end
    else
        print("RoughCut: Warning - Could not add cancel button")
    end
    
    print("RoughCut: Install dialog created successfully")
    return window
end

-- Show the installation dialog
-- @return boolean indicating success
function installDialog.show()
    if not windowRef then
        print("RoughCut: Error - Cannot show install dialog, not created")
        return false
    end
    
    local ok, _ = pcall(function()
        windowRef:Show()
    end)
    
    if not ok then
        print("RoughCut: Error - Failed to show install dialog")
        return false
    end
    
    return true
end

-- Hide the installation dialog
-- @return boolean indicating success
function installDialog.hide()
    if not windowRef then
        print("RoughCut: Error - Cannot hide install dialog, not created")
        return false
    end
    
    local ok, _ = pcall(function()
        windowRef:Hide()
    end)
    
    if not ok then
        print("RoughCut: Error - Failed to hide install dialog")
        return false
    end
    
    return true
end

-- Close and destroy the installation dialog
-- @return boolean indicating success
function installDialog.close()
    if not windowRef then
        return true  -- Already closed
    end
    
    local ok, _ = pcall(function()
        windowRef:Close()
    end)
    
    if not ok then
        print("RoughCut: Warning - Error closing install dialog")
    end
    
    -- Clear references
    windowRef = nil
    progressBarRef = nil
    statusLabelRef = nil
    stepLabelRef = nil
    timeLabelRef = nil
    cancelButtonRef = nil
    
    return true
end

-- Update progress display
-- @param currentStep Current step number (1-based)
-- @param totalSteps Total number of steps
-- @param stepName Human-readable step description
-- @param percent Completion percentage (0-100)
-- @return boolean indicating success
function installDialog.updateProgress(currentStep, totalSteps, stepName, percent)
    if not windowRef then
        return false
    end
    
    -- Update step label
    if stepLabelRef then
        local ok, _ = pcall(function()
            stepLabelRef.Text = string.format("Step %d of %d", currentStep, totalSteps)
        end)
        if not ok then
            print("RoughCut: Warning - Could not update step label")
        end
    end
    
    -- Update status label with step name
    if statusLabelRef then
        local ok, _ = pcall(function()
            statusLabelRef.Text = stepName or "Processing..."
        end)
        if not ok then
            print("RoughCut: Warning - Could not update status label")
        end
    end
    
    -- Update progress bar
    if progressBarRef then
        local ok, _ = pcall(function()
            progressBarRef.Value = math.max(0, math.min(100, percent or 0))
        end)
        if not ok then
            print("RoughCut: Warning - Could not update progress bar")
        end
    end
    
    -- Update time elapsed
    if timeLabelRef and startTime then
        local elapsed = os.time() - startTime
        local ok, _ = pcall(function()
            timeLabelRef.Text = string.format("Time elapsed: %ds", elapsed)
        end)
        if not ok then
            print("RoughCut: Warning - Could not update time label")
        end
    end
    
    return true
end

-- Check if installation was cancelled
-- @return boolean indicating if cancelled
function installDialog.isCancelled()
    return isCancelled
end

-- Set cancel callback function
-- @param callback Function to call when cancel button is clicked
function installDialog.setCancelCallback(callback)
    onCancelCallback = callback
end

-- Reset cancellation state
function installDialog.resetCancel()
    isCancelled = false
end

-- Get current installation state
-- @return table with state information
function installDialog.getState()
    return {
        isCancelled = isCancelled,
        elapsedSeconds = startTime and (os.time() - startTime) or 0,
        currentStep = currentStep,
        totalSteps = totalSteps
    }
end

-- Enable or disable cancel button
-- @param enabled Boolean indicating if button should be enabled
function installDialog.setCancelEnabled(enabled)
    if cancelButtonRef then
        local ok, _ = pcall(function()
            cancelButtonRef.Enabled = enabled
        end)
        if not ok then
            print("RoughCut: Warning - Could not update cancel button state")
        end
    end
end

-- Update dialog text to show completion
function installDialog.showCompletion()
    if statusLabelRef then
        local ok, _ = pcall(function()
            statusLabelRef.Text = "Installation complete!"
        end)
        if not ok then
            print("RoughCut: Warning - Could not update completion status")
        end
    end
    
    if progressBarRef then
        local ok, _ = pcall(function()
            progressBarRef.Value = 100
        end)
        if not ok then
            print("RoughCut: Warning - Could not set final progress")
        end
    end
    
    -- Disable cancel button
    installDialog.setCancelEnabled(false)
end

-- Update dialog to show error state
-- @param errorMessage Error message to display
function installDialog.showError(errorMessage)
    if statusLabelRef then
        local ok, _ = pcall(function()
            statusLabelRef.Text = "Error: " .. (errorMessage or "Installation failed")
        end)
        if not ok then
            print("RoughCut: Warning - Could not update error status")
        end
    end
    
    -- Enable cancel button (now acts as "Close")
    if cancelButtonRef then
        local ok, _ = pcall(function()
            cancelButtonRef.Text = "Close"
        end)
        if not ok then
            print("RoughCut: Warning - Could not update cancel button text")
        end
    end
end

return installDialog
