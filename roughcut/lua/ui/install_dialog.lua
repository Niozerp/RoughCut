-- RoughCut Installation Progress Dialog
-- Displays installation progress with step indicators and cancel button
-- Compatible with DaVinci Resolve's Lua scripting environment
-- Uses correct Fusion UI API with bmd.UIDispatcher

local installDialog = {}

-- Dialog configuration
local DIALOG_CONFIG = {
    title = "RoughCut - Installing Python Backend",
    width = 450,
    height = 350,
    id = "RoughCutInstallDialog"
}

-- UI references
local winRef = nil
local uiRef = nil
local dispRef = nil

-- Reset dialog state to prevent pollution between installations
local function resetDialogState()
    winRef = nil
    uiRef = nil
    dispRef = nil
    isCancelled = false
    startTime = nil
    currentStep = 0
    onCancelCallback = nil
end

-- Widget IDs for event handling
local WIDGET_IDS = {
    cancelButton = "CancelButton",
    headerLabel = "HeaderLabel",
    statusLabel = "StatusLabel",
    stepLabel = "StepLabel",
    progressSlider = "ProgressSlider",
    timeLabel = "TimeLabel",
    etaLabel = "EtaLabel"
}

-- State tracking
local isCancelled = false
local startTime = nil
local currentStep = 0
local totalSteps = 6

-- Callback function for cancel action
local onCancelCallback = nil

-- Create the installation progress dialog
-- @param uiManager Resolve UI Manager instance (fu.UIManager)
-- @return window table or nil on error
function installDialog.create(uiManager)
    if not uiManager then
        print("RoughCut: Error - UI Manager required for install dialog")
        return nil
    end
    
    -- Check if bmd is available
    if not bmd then
        print("RoughCut: Error - bmd module not available (required for UIDispatcher)")
        resetDialogState()
        return nil
    end
    
    uiRef = uiManager
    isCancelled = false
    startTime = os.time()
    currentStep = 0
    
    -- Create the UIDispatcher - THIS IS REQUIRED!
    local ok, disp = pcall(function()
        return bmd.UIDispatcher(uiManager)
    end)
    
    if not ok or not disp then
        print("RoughCut: Error - Failed to create UIDispatcher: " .. tostring(disp))
        resetDialogState()
        return nil
    end
    
    dispRef = disp
    
    -- Create window using disp:AddWindow() with nested UI layout
    local ok2, win = pcall(function()
        return disp:AddWindow({
            ID = DIALOG_CONFIG.id,
            WindowTitle = DIALOG_CONFIG.title,
            Geometry = {100, 100, DIALOG_CONFIG.width, DIALOG_CONFIG.height},
            
            -- Main vertical layout with all children defined declaratively
            uiManager:VGroup{
                ID = "MainLayout",
                Spacing = 15,
                Weight = 1.0,
                
                -- Header label
                uiManager:Label{
                    ID = WIDGET_IDS.headerLabel,
                    Text = "Setting up RoughCut Python Backend",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 16px; font-weight: bold;"
                },
                
                -- Status label
                uiManager:Label{
                    ID = WIDGET_IDS.statusLabel,
                    Text = "Checking Python installation...",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 12px;"
                },
                
                -- Step counter label
                uiManager:Label{
                    ID = WIDGET_IDS.stepLabel,
                    Text = "Step 1 of 6",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 11px;"
                },
                
                -- Progress slider (disabled to look like progress bar)
                uiManager:Slider{
                    ID = WIDGET_IDS.progressSlider,
                    Minimum = 0,
                    Maximum = 100,
                    Value = 0,
                    Weight = 0.0,
                    Enabled = false  -- Makes it look like a progress bar
                },
                
                -- Time elapsed label
                uiManager:Label{
                    ID = WIDGET_IDS.timeLabel,
                    Text = "Time elapsed: 0s",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 10px;"
                },
                
                -- ETA label
                uiManager:Label{
                    ID = WIDGET_IDS.etaLabel,
                    Text = "Estimated time remaining: calculating...",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 10px; font-style: italic;"
                },
                
                -- Spacer to push button to bottom
                uiManager:Label{
                    ID = "Spacer",
                    Text = "",
                    Weight = 1.0
                },
                
                -- Horizontal group for button (centered)
                uiManager:HGroup{
                    ID = "ButtonGroup",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    
                    -- Cancel button
                    uiManager:Button{
                        ID = WIDGET_IDS.cancelButton,
                        Text = "Cancel Installation",
                        Weight = 0.0,
                        MinimumSize = {150, 30}
                    }
                }
            }
        })
    end)
    
    if not ok2 or not win then
        print("RoughCut: Error - Failed to create install dialog window: " .. tostring(win))
        resetDialogState()
        return nil
    end
    
    winRef = win
    
    -- Set up event handler for cancel button using window.On table
    -- Fusion uses win.On.ElementID.EventName pattern
    win.On = win.On or {}
    win.On[WIDGET_IDS.cancelButton] = win.On[WIDGET_IDS.cancelButton] or {}
    win.On[WIDGET_IDS.cancelButton].Clicked = function(ev)
        isCancelled = true
        if onCancelCallback then
            onCancelCallback()
        end
        print("RoughCut: Installation cancelled by user")
    end
    
    print("RoughCut: Install dialog created successfully")
    return win
end

-- Show the installation dialog (non-modal)
-- @return boolean indicating success
function installDialog.show()
    if not winRef then
        print("RoughCut: Error - Cannot show install dialog, not created")
        return false
    end
    
    local ok, _ = pcall(function()
        winRef:Show()
    end)
    
    if not ok then
        print("RoughCut: Error - Failed to show install dialog")
        return false
    end
    
    -- NOTE: We do NOT call disp:RunLoop() here because this is a non-blocking dialog.
    -- The installation runs in the background while the dialog is shown.
    -- The calling code is responsible for periodically calling updateProgress()
    -- and checking isCancelled() during the installation process.
    
    return true
end

-- Hide the installation dialog
-- @return boolean indicating success
function installDialog.hide()
    if not winRef then
        print("RoughCut: Error - Cannot hide install dialog, not created")
        return false
    end
    
    local ok, _ = pcall(function()
        winRef:Hide()
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
    if not winRef then
        return true  -- Already closed
    end
    
    -- Exit the dispatcher loop if it was running (for modal usage)
    if dispRef then
        local ok, _ = pcall(function()
            dispRef:ExitLoop()
        end)
        if not ok then
            -- ExitLoop might fail if not running, that's ok
        end
    end
    
    -- Close the window
    local ok, _ = pcall(function()
        winRef:Close()
    end)
    
    if not ok then
        print("RoughCut: Warning - Error closing install dialog")
    end
    
    -- Clear all references using reset function
    resetDialogState()
    
    return true
end

-- Update progress display
-- @param stepNum Current step number (1-based)
-- @param totalStepCount Total number of steps
-- @param stepName Human-readable step description
-- @param percent Completion percentage (0-100)
-- @return boolean indicating success
function installDialog.updateProgress(stepNum, totalStepCount, stepName, percent)
    if not winRef then
        return false
    end
    
    currentStep = stepNum
    totalSteps = totalStepCount
    
    -- Update step label via window's child reference
    if winRef.On then
        local ok, _ = pcall(function()
            -- Access through the window's FindChild or direct reference if available
            -- In this API pattern, we can update via winRef's On table or FindChild
            local label = winRef:FindChild(WIDGET_IDS.stepLabel)
            if label then
                label.Text = string.format("Step %d of %d", stepNum, totalStepCount)
            end
        end)
        if not ok then
            -- Fallback: try direct property access
            local ok2, _ = pcall(function()
                if winRef[WIDGET_IDS.stepLabel] then
                    winRef[WIDGET_IDS.stepLabel].Text = string.format("Step %d of %d", stepNum, totalStepCount)
                end
            end)
            if not ok2 then
                print("RoughCut: Warning - Could not update step label")
            end
        end
    end
    
    -- Update status label
    local ok, _ = pcall(function()
        local label = winRef:FindChild(WIDGET_IDS.statusLabel)
        if label then
            label.Text = stepName or "Processing..."
        end
    end)
    if not ok then
        local ok2, _ = pcall(function()
            if winRef[WIDGET_IDS.statusLabel] then
                winRef[WIDGET_IDS.statusLabel].Text = stepName or "Processing..."
            end
        end)
        if not ok2 then
            print("RoughCut: Warning - Could not update status label")
        end
    end
    
    -- Update progress slider
    local ok, _ = pcall(function()
        local slider = winRef:FindChild(WIDGET_IDS.progressSlider)
        if slider then
            slider.Value = math.max(0, math.min(100, percent or 0))
        end
    end)
    if not ok then
        local ok2, _ = pcall(function()
            if winRef[WIDGET_IDS.progressSlider] then
                winRef[WIDGET_IDS.progressSlider].Value = math.max(0, math.min(100, percent or 0))
            end
        end)
        if not ok2 then
            print("RoughCut: Warning - Could not update progress slider")
        end
    end
    
    -- Update time elapsed
    if startTime then
        local elapsed = os.time() - startTime
        local ok3, _ = pcall(function()
            local label = winRef:FindChild(WIDGET_IDS.timeLabel)
            if label then
                label.Text = string.format("Time elapsed: %ds", elapsed)
            end
        end)
        if not ok3 then
            local ok4, _ = pcall(function()
                if winRef[WIDGET_IDS.timeLabel] then
                    winRef[WIDGET_IDS.timeLabel].Text = string.format("Time elapsed: %ds", elapsed)
                end
            end)
            if not ok4 then
                print("RoughCut: Warning - Could not update time label")
            end
        end
        
    -- Update ETA
    if percent and percent > 0 then
        local totalEstimated = elapsed / (percent / 100)
        local remaining = math.max(0, totalEstimated - elapsed)
        local ok5, _ = pcall(function()
            local label = winRef:FindChild(WIDGET_IDS.etaLabel)
            if label then
                if remaining > 60 then
                    label.Text = string.format("Estimated time remaining: ~%dm", math.ceil(remaining / 60))
                else
                    label.Text = string.format("Estimated time remaining: ~%ds", math.ceil(remaining))
                end
            end
        end)
        if not ok5 then
            local ok6, _ = pcall(function()
                if winRef[WIDGET_IDS.etaLabel] then
                    if remaining > 60 then
                        winRef[WIDGET_IDS.etaLabel].Text = string.format("Estimated time remaining: ~%dm", math.ceil(remaining / 60))
                    else
                        winRef[WIDGET_IDS.etaLabel].Text = string.format("Estimated time remaining: ~%ds", math.ceil(remaining))
                    end
                end
            end)
            if not ok6 then
                print("RoughCut: Warning - Could not update ETA label")
            end
        end
    else
        -- percent is 0 or nil, show calculating message
        local ok5, _ = pcall(function()
            local label = winRef:FindChild(WIDGET_IDS.etaLabel)
            if label then
                label.Text = "Estimated time remaining: calculating..."
            end
        end)
        if not ok5 then
            local ok6, _ = pcall(function()
                if winRef[WIDGET_IDS.etaLabel] then
                    winRef[WIDGET_IDS.etaLabel].Text = "Estimated time remaining: calculating..."
                end
            end)
            if not ok6 then
                print("RoughCut: Warning - Could not update ETA label")
            end
        end
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
    if not winRef then
        return
    end
    
    local ok, _ = pcall(function()
        local btn = winRef:FindChild(WIDGET_IDS.cancelButton)
        if btn then
            btn.Enabled = enabled
        end
    end)
    
    if not ok then
        local ok2, _ = pcall(function()
            if winRef[WIDGET_IDS.cancelButton] then
                winRef[WIDGET_IDS.cancelButton].Enabled = enabled
            end
        end)
        if not ok2 then
            print("RoughCut: Warning - Could not update cancel button state")
        end
    end
end

-- Update dialog text to show completion
function installDialog.showCompletion()
    if not winRef then
        return
    end
    
    -- Update status label
    local ok, _ = pcall(function()
        local label = winRef:FindChild(WIDGET_IDS.statusLabel)
        if label then
            label.Text = "Installation complete!"
        end
    end)
    if not ok then
        local ok2, _ = pcall(function()
            if winRef[WIDGET_IDS.statusLabel] then
                winRef[WIDGET_IDS.statusLabel].Text = "Installation complete!"
            end
        end)
        if not ok2 then
            print("RoughCut: Warning - Could not update completion status")
        end
    end
    
    -- Update header
    local ok, _ = pcall(function()
        local label = winRef:FindChild(WIDGET_IDS.headerLabel)
        if label then
            label.Text = "RoughCut Setup Complete"
        end
    end)
    if not ok then
        local ok2, _ = pcall(function()
            if winRef[WIDGET_IDS.headerLabel] then
                winRef[WIDGET_IDS.headerLabel].Text = "RoughCut Setup Complete"
            end
        end)
        if not ok2 then
            print("RoughCut: Warning - Could not update header")
        end
    end
    
    -- Update progress to 100%
    local ok, _ = pcall(function()
        local slider = winRef:FindChild(WIDGET_IDS.progressSlider)
        if slider then
            slider.Value = 100
        end
    end)
    if not ok then
        local ok2, _ = pcall(function()
            if winRef[WIDGET_IDS.progressSlider] then
                winRef[WIDGET_IDS.progressSlider].Value = 100
            end
        end)
        if not ok2 then
            print("RoughCut: Warning - Could not set final progress")
        end
    end
    
    -- Disable cancel button
    installDialog.setCancelEnabled(false)
    
    -- Update button text to "Close"
    local ok, _ = pcall(function()
        local btn = winRef:FindChild(WIDGET_IDS.cancelButton)
        if btn then
            btn.Text = "Close"
        end
    end)
    if not ok then
        local ok2, _ = pcall(function()
            if winRef[WIDGET_IDS.cancelButton] then
                winRef[WIDGET_IDS.cancelButton].Text = "Close"
            end
        end)
        if not ok2 then
            print("RoughCut: Warning - Could not update button text")
        end
    end
end

-- Update dialog to show error state
-- @param errorMessage Error message to display
function installDialog.showError(errorMessage)
    if not winRef then
        return
    end
    
    -- Update status label
    local ok, _ = pcall(function()
        local label = winRef:FindChild(WIDGET_IDS.statusLabel)
        if label then
            label.Text = "Error: " .. (errorMessage or "Installation failed")
        end
    end)
    if not ok then
        local ok2, _ = pcall(function()
            if winRef[WIDGET_IDS.statusLabel] then
                winRef[WIDGET_IDS.statusLabel].Text = "Error: " .. (errorMessage or "Installation failed")
            end
        end)
        if not ok2 then
            print("RoughCut: Warning - Could not update error status")
        end
    end
    
    -- Update header
    local ok, _ = pcall(function()
        local label = winRef:FindChild(WIDGET_IDS.headerLabel)
        if label then
            label.Text = "RoughCut Setup Failed"
        end
    end)
    if not ok then
        local ok2, _ = pcall(function()
            if winRef[WIDGET_IDS.headerLabel] then
                winRef[WIDGET_IDS.headerLabel].Text = "RoughCut Setup Failed"
            end
        end)
        if not ok2 then
            print("RoughCut: Warning - Could not update header")
        end
    end
    
    -- Change button text to "Close"
    local ok, _ = pcall(function()
        local btn = winRef:FindChild(WIDGET_IDS.cancelButton)
        if btn then
            btn.Text = "Close"
        end
    end)
    if not ok then
        local ok2, _ = pcall(function()
            if winRef[WIDGET_IDS.cancelButton] then
                winRef[WIDGET_IDS.cancelButton].Text = "Close"
            end
        end)
        if not ok2 then
            print("RoughCut: Warning - Could not update cancel button text")
        end
    end
end

return installDialog
