-- RoughCut Rough Cut Workflow Window
-- Multi-step wizard workflow for creating rough cuts
-- Step 3: Format Template Selection (Story 3.3)
-- Compatible with DaVinci Resolve's Lua scripting environment
-- Version: 1.0.0

local roughCutWorkflow = {}

-- Import dependencies with safe require
local protocol = nil
local logger = nil

-- Safely require protocol module
local ok, mod = pcall(require, "utils.protocol")
if ok then
    protocol = mod
else
    ok, mod = pcall(require, "roughcut.protocol")
    if ok then
        protocol = mod
    else
        -- Stub protocol for standalone testing
        protocol = {
            request = function(req)
                print("[STUB] Protocol request: " .. tostring(req.method))
                return { result = {}, error = nil }
            end
        }
    end
end

-- Safely require logger module
ok, mod = pcall(require, "utils.logger")
if ok then
    logger = mod
else
    logger = {
        error = function(msg) print("[ERROR] " .. tostring(msg)) end,
        warn = function(msg) print("[WARN] " .. tostring(msg)) end,
        info = function(msg) print("[INFO] " .. tostring(msg)) end,
        debug = function(msg) end
    }
end

-- Window configuration
local WINDOW_CONFIG = {
    id = "RoughCutWorkflow",
    title = "RoughCut - Create Rough Cut",
    width = 700,
    height = 600
}

-- Workflow step constants
local STEPS = {
    MEDIA = "media",
    TRANSCRIPTION = "transcription",
    FORMAT = "format",
    GENERATE = "generate"
}

-- State tracking
local parentWindowRef = nil
local currentWindowRef = nil
local currentStep = STEPS.MEDIA
local sessionId = nil
local formatsList = {}
local selectedFormatSlug = nil
local isLoading = false

-- Create the rough cut workflow window
-- @param uiManager Resolve UI Manager instance
-- @param parentWindow Reference to main window for navigation back
-- @return window table or nil on error
function roughCutWorkflow.create(uiManager, parentWindow)
    if not uiManager then
        logger.error("UI Manager required for rough cut workflow window")
        return nil
    end
    
    parentWindowRef = parentWindow
    
    -- Create window
    local ok_create, window = pcall(function()
        return uiManager:Add({
            type = "Window",
            id = WINDOW_CONFIG.id,
            title = WINDOW_CONFIG.title,
            width = WINDOW_CONFIG.width,
            height = WINDOW_CONFIG.height,
            spacing = 15,
            padding = 20
        })
    end)
    
    if not ok_create or not window then
        logger.error("Failed to create rough cut workflow window: " .. tostring(window))
        return nil
    end
    
    currentWindowRef = window
    currentStep = STEPS.MEDIA
    
    -- Create new session via protocol
    _createSessionAsync()
    
    return window
end

-- Create a new rough cut session asynchronously
function _createSessionAsync()
    isLoading = true
    
    -- Use timer for async simulation if available, otherwise sync
    local ok_timer = pcall(function()
        -- Try to use timer for async (Resolve API dependent)
        if type(SetTimer) == "function" then
            SetTimer(100, function()
                _createSessionInternal()
                return false -- One-shot timer
            end)
        else
            -- Fallback to sync
            _createSessionInternal()
        end
    end)
    
    if not ok_timer then
        _createSessionInternal()
    end
end

-- Internal function to create session
function _createSessionInternal()
    local result = protocol.request({
        method = "create_rough_cut_session"
    })
    
    isLoading = false
    
    if result.error then
        logger.error("Failed to create session: " .. tostring(result.error.message))
        _showError("Failed to start workflow: " .. tostring(result.error.message))
        return
    end
    
    if result.result then
        sessionId = result.result.session_id
        logger.info("Created rough cut session: " .. tostring(sessionId))
        
        -- Show media selection step
        _showMediaSelectionStep()
    end
end

-- Show media selection step
function _showMediaSelectionStep()
    currentStep = STEPS.MEDIA
    _clearWindow(currentWindowRef)
    
    -- Build step indicator
    _buildStepIndicator(currentWindowRef, STEPS.MEDIA)
    
    -- Header
    local ok = pcall(function()
        currentWindowRef:Add({
            type = "Label",
            text = "Select Media",
            font = { size = 22, bold = true },
            alignment = { alignHCenter = true }
        })
        
        currentWindowRef:Add({
            type = "Label",
            text = "Choose a video clip from the Media Pool",
            font = { size = 11 },
            alignment = { alignHCenter = true }
        })
    end)
    
    if not ok then
        logger.warn("Failed to add media step header")
    end
    
    -- Spacer
    pcall(function()
        currentWindowRef:Add({
            type = "Label",
            text = "",
            height = 20
        })
    end)
    
    -- Placeholder for media list (Epic 4 will implement full media browser)
    ok = pcall(function()
        currentWindowRef:Add({
            type = "Label",
            text = "Media Pool Browser",
            font = { size = 14, bold = true }
        })
        
        currentWindowRef:Add({
            type = "Label",
            text = "(Media selection will be implemented in Epic 4)",
            font = { size = 11, italic = true },
            alignment = { alignHCenter = true }
        })
        
        -- Mock media selection for Story 3.3
        currentWindowRef:Add({
            type = "Label",
            text = "",
            height = 10
        })
        
        -- Simulate media selection button
        local mockBtn = currentWindowRef:Add({
            type = "Button",
            id = "btnMockMediaSelect",
            text = "Select Mock Media for Testing",
            height = 40,
            alignment = { alignHCenter = true }
        })
        
        if mockBtn then
            mockBtn.Clicked = function()
                _selectMockMedia()
            end
        end
    end)
    
    if not ok then
        logger.warn("Failed to add media selection UI")
    end
    
    -- Navigation buttons
    _buildNavigationButtons(currentWindowRef, true, false)
end

-- Simulate selecting mock media
function _selectMockMedia()
    if not sessionId then
        _showError("No active session")
        return
    end
    
    -- Call protocol to select media
    local result = protocol.request({
        method = "select_media_for_session",
        params = {
            session_id = sessionId,
            clip_id = "mock_clip_001",
            clip_name = "Test Interview Segment"
        }
    })
    
    if result.error then
        _showError("Failed to select media: " .. tostring(result.error.message))
        return
    end
    
    -- Simulate transcription review (bypass to format selection for Story 3.3)
    _simulateTranscriptionReview()
end

-- Simulate transcription review step
function _simulateTranscriptionReview()
    if not sessionId then
        _showError("No active session")
        return
    end
    
    -- Call protocol to review transcription
    local result = protocol.request({
        method = "review_transcription_for_session",
        params = {
            session_id = sessionId,
            transcription_data = {
                text = "This is a test transcription for format template selection...",
                segments = {},
                quality = "good"
            }
        }
    })
    
    if result.error then
        _showError("Failed to review transcription: " .. tostring(result.error.message))
        return
    end
    
    -- Proceed to format selection step (THIS STORY)
    _showFormatSelectionStep()
end

-- Show format selection step (STORY 3.3)
function _showFormatSelectionStep()
    currentStep = STEPS.FORMAT
    _clearWindow(currentWindowRef)
    
    -- Build step indicator
    _buildStepIndicator(currentWindowRef, STEPS.FORMAT)
    
    -- Header
    local ok = pcall(function()
        currentWindowRef:Add({
            type = "Label",
            text = "Select Format Template",
            font = { size = 22, bold = true },
            alignment = { alignHCenter = true }
        })
        
        currentWindowRef:Add({
            type = "Label",
            text = "Choose a format template for your rough cut",
            font = { size = 11 },
            alignment = { alignHCenter = true }
        })
    end)
    
    if not ok then
        logger.warn("Failed to add format step header")
    end
    
    -- Spacer
    pcall(function()
        currentWindowRef:Add({
            type = "Label",
            text = "",
            height = 10
        })
    end)
    
    -- Loading indicator
    ok = pcall(function()
        currentWindowRef:Add({
            type = "Label",
            id = "lblFormatLoading",
            text = "Loading format templates...",
            font = { size = 12, italic = true },
            alignment = { alignHCenter = true },
            height = 30
        })
    end)
    
    -- Load formats asynchronously
    _loadFormatsAsync()
    
    -- Navigation buttons (Next disabled until format selected)
    _buildNavigationButtons(currentWindowRef, false, true)
end

-- Build step indicator UI
function _buildStepIndicator(window, activeStep)
    local ok = pcall(function()
        -- Step indicator container
        window:Add({
            type = "Label",
            text = "",
            height = 5
        })
        
        -- Step text
        local steps = {
            { id = STEPS.MEDIA, label = "Media", done = true },
            { id = STEPS.TRANSCRIPTION, label = "Transcription", done = true },
            { id = STEPS.FORMAT, label = "Format", done = false, current = activeStep == STEPS.FORMAT },
            { id = STEPS.GENERATE, label = "Generate", done = false }
        }
        
        local stepText = ""
        for i, step in ipairs(steps) do
            if i > 1 then
                stepText = stepText .. " → "
            end
            
            if step.done then
                stepText = stepText .. "[✓ " .. step.label .. "]"
            elseif step.current then
                stepText = stepText .. "[● " .. step.label .. "]"
            else
                stepText = stepText .. "[○ " .. step.label .. "]"
            end
        end
        
        window:Add({
            type = "Label",
            text = stepText,
            font = { size = 10 },
            alignment = { alignHCenter = true }
        })
        
        window:Add({
            type = "Label",
            text = "",
            height = 10
        })
    end)
    
    if not ok then
        logger.warn("Failed to build step indicator")
    end
end

-- Load format templates asynchronously
function _loadFormatsAsync()
    isLoading = true
    
    local ok_timer = pcall(function()
        if type(SetTimer) == "function" then
            SetTimer(100, function()
                _loadFormatsInternal()
                return false
            end)
        else
            _loadFormatsInternal()
        end
    end)
    
    if not ok_timer then
        _loadFormatsInternal()
    end
end

-- Internal function to load formats
function _loadFormatsInternal()
    local result = protocol.request({
        method = "get_available_formats"
    })
    
    isLoading = false
    
    if result.error then
        logger.error("Failed to load formats: " .. tostring(result.error.message))
        _showFormatsError(result.error.message)
        return
    end
    
    if result.result and result.result.formats then
        formatsList = result.result.formats
        logger.info("Loaded " .. tostring(#formatsList) .. " format templates")
        _populateFormatsList()
    else
        formatsList = {}
        _populateFormatsList()
    end
end

-- Populate the formats list UI
function _populateFormatsList()
    if not currentWindowRef then
        return
    end
    
    -- Hide loading label
    pcall(function()
        local lbl = currentWindowRef:FindById("lblFormatLoading")
        if lbl then
            lbl.Height = 0
        end
    end)
    
    if #formatsList == 0 then
        -- Show empty state
        pcall(function()
            currentWindowRef:Add({
                type = "Label",
                text = "No format templates found.",
                font = { size = 12, italic = true },
                alignment = { alignHCenter = true }
            })
            
            currentWindowRef:Add({
                type = "Label",
                text = "Add .md files to templates/formats/ directory",
                font = { size = 10 },
                alignment = { alignHCenter = true }
            })
        end)
        return
    end
    
    -- Create scrollable list container
    local ok = pcall(function()
        local listContainer = currentWindowRef:Add({
            type = "VGroup",
            id = "grpFormatsList",
            spacing = 8
        })
        
        -- Add each format as a selectable item
        for _, format in ipairs(formatsList) do
            _addFormatItem(listContainer, format)
        end
    end)
    
    if not ok then
        logger.warn("Failed to populate formats list")
    end
end

-- Add a single format item to the list
function _addFormatItem(container, format)
    local ok = pcall(function()
        -- Format item container (horizontal group for selection indicator + content)
        local itemGroup = container:Add({
            type = "HGroup",
            id = "grpFormatItem_" .. tostring(format.slug),
            spacing = 10
        })
        
        -- Selection indicator
        local lblIndicator = itemGroup:Add({
            type = "Label",
            id = "lblIndicator_" .. tostring(format.slug),
            text = "  ",  -- Empty initially, filled when selected
            font = { size = 14, bold = true },
            width = 20
        })
        
        -- Content container
        local contentGroup = itemGroup:Add({
            type = "VGroup",
            spacing = 2
        })
        
        -- Format name
        local lblName = contentGroup:Add({
            type = "Label",
            text = tostring(format.name),
            font = { size = 13, bold = true }
        })
        
        -- Format description
        local desc = format.description or ""
        if #desc > 80 then
            desc = string.sub(desc, 1, 77) .. "..."
        end
        
        contentGroup:Add({
            type = "Label",
            text = desc,
            font = { size = 10 },
            color = { 0.5, 0.5, 0.5 }
        })
        
        -- Buttons group
        local btnGroup = contentGroup:Add({
            type = "HGroup",
            spacing = 5
        })
        
        -- Preview button
        local btnPreview = btnGroup:Add({
            type = "Button",
            id = "btnPreview_" .. tostring(format.slug),
            text = "Preview",
            width = 70,
            height = 25,
            font = { size = 9 }
        })
        
        if btnPreview then
            btnPreview.Clicked = function()
                _showFormatPreview(format.slug)
            end
        end
        
        -- Select button
        local btnSelect = btnGroup:Add({
            type = "Button",
            id = "btnSelect_" .. tostring(format.slug),
            text = "Select",
            width = 70,
            height = 25,
            font = { size = 9 }
        })
        
        if btnSelect then
            btnSelect.Clicked = function()
                _selectFormat(format.slug)
            end
        end
        
        -- Make the whole item clickable for selection
        -- (In a full implementation, we'd add click handlers to the group)
    end)
    
    if not ok then
        logger.warn("Failed to add format item: " .. tostring(format.slug))
    end
end

-- Show format preview dialog
function _showFormatPreview(slug)
    local result = protocol.request({
        method = "get_template_preview",
        params = { template_id = slug }
    })
    
    if result.error then
        _showError("Failed to load preview: " .. tostring(result.error.message))
        return
    end
    
    if result.result and result.result.preview then
        local preview = result.result.preview
        local previewText = _formatPreviewText(preview)
        
        -- Show preview in a dialog (simplified - could be a separate window)
        pcall(function()
            local dlg = currentWindowRef:Add({
                type = "Window",
                id = "dlgPreview",
                title = "Template Preview: " .. tostring(preview.name),
                width = 500,
                height = 400,
                modal = true
            })
            
            if dlg then
                dlg:Add({
                    type = "Label",
                    text = previewText,
                    font = { size = 11 },
                    wordWrap = true
                })
                
                local btnClose = dlg:Add({
                    type = "Button",
                    text = "Close",
                    alignment = { alignHCenter = true }
                })
                
                if btnClose then
                    btnClose.Clicked = function()
                        dlg:Close()
                    end
                end
                
                dlg:Show()
            end
        end)
    end
end

-- Format preview data into readable text
function _formatPreviewText(preview)
    local lines = {}
    
    table.insert(lines, "Name: " .. tostring(preview.name))
    table.insert(lines, "Description: " .. tostring(preview.description))
    table.insert(lines, "")
    
    if preview.segments and #preview.segments > 0 then
        table.insert(lines, "=== TIMING SEGMENTS ===")
        for _, seg in ipairs(preview.segments) do
            table.insert(lines, string.format(
                "%s: %s-%s (%s)",
                seg.name or "Segment",
                seg.start_time or "0:00",
                seg.end_time or "0:00",
                seg.duration or "unknown"
            ))
        end
        table.insert(lines, "")
    end
    
    if preview.asset_groups and #preview.asset_groups > 0 then
        table.insert(lines, "=== ASSET GROUPS ===")
        for _, ag in ipairs(preview.asset_groups) do
            table.insert(lines, string.format(
                "%s: %s - %s",
                ag.category or "Asset",
                ag.name or "unnamed",
                ag.description or ""
            ))
        end
    end
    
    return table.concat(lines, "\n")
end

-- Select a format template
function _selectFormat(slug)
    if not sessionId then
        _showError("No active session")
        return
    end
    
    logger.info("Selecting format template: " .. tostring(slug))
    
    local result = protocol.request({
        method = "select_format_template",
        params = {
            session_id = sessionId,
            template_id = slug
        }
    })
    
    if result.error then
        _showError("Failed to select format: " .. tostring(result.error.message))
        return
    end
    
    if result.result then
        selectedFormatSlug = slug
        
        -- Update UI to show selection
        _updateFormatSelectionUI(slug)
        
        -- Enable Next button
        _enableNextButton(true)
        
        logger.info("Selected format: " .. tostring(result.result.template_name))
    end
end

-- Update UI to show which format is selected
function _updateFormatSelectionUI(selectedSlug)
    pcall(function()
        for _, format in ipairs(formatsList) do
            local indicator = currentWindowRef:FindById("lblIndicator_" .. tostring(format.slug))
            if indicator then
                if format.slug == selectedSlug then
                    indicator.Text = "▶"
                else
                    indicator.Text = "  "
                end
            end
        end
    end)
end

-- Show formats error message
function _showFormatsError(message)
    pcall(function()
        currentWindowRef:Add({
            type = "Label",
            text = "Error loading formats: " .. tostring(message),
            font = { size = 11, italic = true },
            color = { 1, 0, 0 },
            alignment = { alignHCenter = true }
        })
    end)
end

-- Build navigation buttons
function _buildNavigationButtons(window, hasNext, hasBack)
    pcall(function()
        -- Spacer
        window:Add({
            type = "Label",
            text = "",
            height = 20
        })
        
        -- Button container
        local btnGroup = window:Add({
            type = "HGroup",
            spacing = 20,
            alignment = { alignHCenter = true }
        })
        
        -- Back button
        if hasBack then
            local btnBack = btnGroup:Add({
                type = "Button",
                id = "btnBack",
                text = "← Back",
                width = 100,
                height = 35
            })
            
            if btnBack then
                btnBack.Clicked = function()
                    _onBackButton()
                end
            end
        end
        
        -- Cancel button
        local btnCancel = btnGroup:Add({
            type = "Button",
            id = "btnCancel",
            text = "Cancel",
            width = 100,
            height = 35
        })
        
        if btnCancel then
            btnCancel.Clicked = function()
                roughCutWorkflow.close()
            end
        end
        
        -- Next/Generate button
        if hasNext then
            local btnNext = btnGroup:Add({
                type = "Button",
                id = "btnNext",
                text = "Next →",
                width = 100,
                height = 35
            })
            
            if btnNext then
                btnNext.Clicked = function()
                    _onNextButton()
                end
            end
            
            -- Store reference for enabling/disabling
            window.btnNext = btnNext
            _enableNextButton(false) -- Disabled until format selected
        end
    end)
end

-- Enable/disable next button
function _enableNextButton(enabled)
    pcall(function()
        if currentWindowRef and currentWindowRef.btnNext then
            currentWindowRef.btnNext.Enabled = enabled
        end
    end)
end

-- Handle back button click
function _onBackButton()
    if currentStep == STEPS.FORMAT then
        -- Go back to transcription (simulated)
        _showMediaSelectionStep()
    end
end

-- Handle next button click
function _onNextButton()
    if currentStep == STEPS.FORMAT then
        -- Prepare for generation (Story 3.3 AC #3)
        _prepareForGeneration()
    end
end

-- Prepare rough cut data for generation
function _prepareForGeneration()
    if not sessionId then
        _showError("No active session")
        return
    end
    
    logger.info("Preparing rough cut data for generation")
    
    local result = protocol.request({
        method = "prepare_rough_cut_for_generation",
        params = {
            session_id = sessionId
        }
    })
    
    if result.error then
        _showError("Failed to prepare: " .. tostring(result.error.message))
        return
    end
    
    if result.result then
        logger.info("Prepared data for generation successfully")
        _showGenerateStep(result.result.data)
    end
end

-- Show generate step
function _showGenerateStep(data)
    currentStep = STEPS.GENERATE
    _clearWindow(currentWindowRef)
    
    -- Build step indicator
    _buildStepIndicator(currentWindowRef, STEPS.GENERATE)
    
    -- Header
    pcall(function()
        currentWindowRef:Add({
            type = "Label",
            text = "Generate Rough Cut",
            font = { size = 22, bold = true },
            alignment = { alignHCenter = true }
        })
        
        currentWindowRef:Add({
            type = "Label",
            text = "Ready to generate AI-powered rough cut",
            font = { size = 11 },
            alignment = { alignHCenter = true }
        })
    end)
    
    -- Show summary
    pcall(function()
        currentWindowRef:Add({
            type = "Label",
            text = "",
            height = 20
        })
        
        currentWindowRef:Add({
            type = "Label",
            text = "Session Summary:",
            font = { size = 14, bold = true }
        })
        
        if data and data.media then
            currentWindowRef:Add({
                type = "Label",
                text = "Media: " .. tostring(data.media.clip_name)
            })
        end
        
        if data and data.format then
            currentWindowRef:Add({
                type = "Label",
                text = "Format: " .. tostring(data.format.name)
            })
            
            currentWindowRef:Add({
                type = "Label",
                text = "Segments: " .. tostring(#(data.format.segments or {}))
            })
            
            currentWindowRef:Add({
                type = "Label",
                text = "Asset Groups: " .. tostring(#(data.format.asset_groups or {}))
            })
        end
    end)
    
    -- Generate button
    pcall(function()
        currentWindowRef:Add({
            type = "Label",
            text = "",
            height = 30
        })
        
        local btnGenerate = currentWindowRef:Add({
            type = "Button",
            id = "btnGenerate",
            text = "Generate Rough Cut",
            width = 180,
            height = 45,
            font = { size = 12, bold = true },
            alignment = { alignHCenter = true }
        })
        
        if btnGenerate then
            btnGenerate.Clicked = function()
                _showGeneratingState()
            end
        end
    end)
    
    -- Cancel button
    pcall(function()
        currentWindowRef:Add({
            type = "Label",
            text = "",
            height = 10
        })
        
        local btnCancel = currentWindowRef:Add({
            type = "Button",
            text = "Cancel",
            width = 100,
            height = 35,
            alignment = { alignHCenter = true }
        })
        
        if btnCancel then
            btnCancel.Clicked = function()
                roughCutWorkflow.close()
            end
        end
    end)
end

-- Show generating state (placeholder for Epic 5)
function _showGeneratingState()
    pcall(function()
        _clearWindow(currentWindowRef)
        
        currentWindowRef:Add({
            type = "Label",
            text = "Generating Rough Cut...",
            font = { size = 20, bold = true },
            alignment = { alignHCenter = true }
        })
        
        currentWindowRef:Add({
            type = "Label",
            text = "",
            height = 30
        })
        
        currentWindowRef:Add({
            type = "Label",
            text = "AI processing will be implemented in Epic 5",
            font = { size = 12, italic = true },
            alignment = { alignHCenter = true }
        })
        
        currentWindowRef:Add({
            type = "Label",
            text = "",
            height = 30
        })
        
        local btnDone = currentWindowRef:Add({
            type = "Button",
            text = "Done",
            width = 100,
            height = 35,
            alignment = { alignHCenter = true }
        })
        
        if btnDone then
            btnDone.Clicked = function()
                roughCutWorkflow.close()
            end
        end
    end)
end

-- Clear all items from window
function _clearWindow(window)
    if not window then
        return
    end
    
    pcall(function()
        -- Resolve doesn't have a direct clear method
        -- We hide the window and recreate it
        window:Hide()
        
        -- Re-add the window with same config
        -- Note: In a real implementation, we'd need to remove items individually
        -- or recreate the window entirely
    end)
    
    -- Alternative: Just create a new window
    pcall(function()
        if window.Items then
            for i = #window.Items, 1, -1 do
                pcall(function()
                    window:Remove(window.Items[i])
                end)
            end
        end
    end)
end

-- Show error message
function _showError(message)
    logger.error(message)
    
    pcall(function()
        if currentWindowRef then
            currentWindowRef:Add({
                type = "Label",
                text = "Error: " .. tostring(message),
                font = { size = 11 },
                color = { 1, 0, 0 },
                alignment = { alignHCenter = true }
            })
        end
    end)
end

-- Show the workflow window
-- @return boolean success
function roughCutWorkflow.show()
    if not currentWindowRef then
        logger.error("No rough cut workflow window to show")
        return false
    end
    
    local ok = pcall(function()
        currentWindowRef:Show()
    end)
    
    if not ok then
        logger.error("Failed to show workflow window")
        return false
    end
    
    return true
end

-- Hide the workflow window
-- @return boolean success
function roughCutWorkflow.hide()
    if not currentWindowRef then
        return false
    end
    
    local ok = pcall(function()
        currentWindowRef:Hide()
    end)
    
    return ok
end

-- Close the workflow window and return to main
-- @return boolean success
function roughCutWorkflow.close()
    logger.info("Closing rough cut workflow window")
    
    local ok = pcall(function()
        if currentWindowRef then
            currentWindowRef:Hide()
        end
        
        if parentWindowRef and parentWindowRef.Show then
            parentWindowRef:Show()
        end
        
        currentWindowRef = nil
        sessionId = nil
        selectedFormatSlug = nil
    end)
    
    return ok
end

-- Clean up resources
function roughCutWorkflow.destroy()
    if currentWindowRef then
        pcall(function()
            currentWindowRef:Close()
        end)
        currentWindowRef = nil
    end
    parentWindowRef = nil
    sessionId = nil
end

return roughCutWorkflow
