--[[
    Media Pool Browser UI
    
    Provides a dialog for browsing and selecting clips from Resolve's Media Pool.
    This is the entry point for the rough cut creation workflow.
    
    Usage:
        local MediaBrowser = require("media_browser")
        MediaBrowser.show()
--]]

local MediaBrowser = {}

-- UI state
MediaBrowser.selectedClip = nil
MediaBrowser.clips = {}
MediaBrowser.filteredClips = {}
MediaBrowser.searchText = ""
MediaBrowser.isValidating = false
MediaBrowser.validationResult = nil

-- Error code constants for validation errors
MediaBrowser.ERROR_CODES = {
    NO_AUDIO_TRACK = "NO_AUDIO_TRACK",
    UNSUPPORTED_CODEC = "UNSUPPORTED_CODEC",
    MEDIA_OFFLINE = "MEDIA_OFFLINE",
    CLIP_NOT_FOUND = "CLIP_NOT_FOUND",
    VALIDATION_FAILED = "VALIDATION_FAILED",
    UNKNOWN = "UNKNOWN"
}

-- Validation timeout in seconds
MediaBrowser.VALIDATION_TIMEOUT = 30

-- Session state for validation caching
local _session = {
    validatedClips = {}
}

--[[
    Show the Media Pool browser dialog.
    
    This creates a modal dialog that allows the user to browse clips,
    search/filter the list, and select a source clip for rough cut generation.
--]]
function MediaBrowser.show()
    -- Reset state
    MediaBrowser.selectedClip = nil
    MediaBrowser.searchText = ""
    
    -- Check if Resolve is available
    local ResolveAPI = require("resolve_api")
    local available, err = ResolveAPI.isAvailable()
    
    if not available then
        local msg = ResolveAPI.getErrorMessage(err)
        MediaBrowser.showErrorDialog(msg)
        return
    end
    
    -- Load clips from Media Pool
    local clips, loadErr = ResolveAPI.getVideoClips()
    if loadErr then
        local msg = ResolveAPI.getErrorMessage(loadErr)
        MediaBrowser.showErrorDialog(msg)
        return
    end
    
    MediaBrowser.clips = clips
    MediaBrowser.filteredClips = clips
    
    -- Create and show the dialog
    local dialog = MediaBrowser.createDialog()
    if dialog then
        -- In Resolve's Lua environment, we would call dialog:Show()
        -- For now, this function sets up the dialog structure
        MediaBrowser.currentDialog = dialog
        MediaBrowser.populateClipList()
    end
end

--[[
    Create the browser dialog structure.
    
    Returns:
        dialog: Table describing the dialog structure (Resolve UI compatible)
--]]
function MediaBrowser.createDialog()
    local dialog = {
        title = "Select Source Clip - RoughCut",
        width = 800,
        height = 600,
        
        -- Window style - modal dialog
        modal = true,
        
        -- UI Components
        components = {
            -- Header/instructions
            {
                type = "Label",
                id = "headerLabel",
                text = "Select a video clip from your Media Pool to analyze for the rough cut.",
                alignment = { AlignHCenter = true },
                styleSheet = "font-weight: bold; padding: 10px;"
            },
            
            -- Search box
            {
                type = "LineEdit",
                id = "searchBox",
                placeholderText = "Search clips...",
                clearButtonEnabled = true,
                onTextChanged = function(text)
                    MediaBrowser.onSearchTextChanged(text)
                end
            },
            
            -- Clip list (main content area)
            {
                type = "TreeWidget",
                id = "clipList",
                columnCount = 3,
                headerLabels = {"Name", "Duration", "Type"},
                selectionMode = "SingleSelection",
                onItemSelectionChanged = function()
                    MediaBrowser.onClipSelectionChanged()
                end,
                onItemDoubleClicked = function(item)
                    MediaBrowser.onClipDoubleClicked(item)
                end
            },
            
            -- Empty state label (shown when no clips)
            {
                type = "Label",
                id = "emptyLabel",
                text = "No video clips found in Media Pool.\n\nAdd clips to your project and click Refresh.",
                visible = (#MediaBrowser.clips == 0),
                alignment = { AlignHCenter = true, AlignVCenter = true }
            },
            
            -- Status label
            {
                type = "Label",
                id = "statusLabel",
                text = MediaBrowser.getStatusText(),
                styleSheet = "color: gray; font-size: 10px;"
            },
            
            -- Button row
            {
                type = "Layout",
                layout = "Horizontal",
                components = {
                    {
                        type = "Button",
                        id = "refreshButton",
                        text = "Refresh",
                        onClicked = function()
                            MediaBrowser.refreshMediaPool()
                        end
                    },
                    {
                        type = "Stretch"
                    },
                    {
                        type = "Button",
                        id = "selectButton",
                        text = "Select Clip",
                        enabled = false,  -- Enabled when clip selected
                        default = true,
                        onClicked = function()
                            MediaBrowser.confirmSelection()
                        end
                    },
                    {
                        type = "Button",
                        id = "cancelButton",
                        text = "Cancel",
                        onClicked = function()
                            MediaBrowser.close()
                        end
                    }
                }
            }
        }
    }
    
    return dialog
end

--[[
    Get status text showing clip counts.
    
    Returns:
        text: String like "Showing 5 of 12 clips"
--]]
function MediaBrowser.getStatusText()
    local total = #MediaBrowser.clips
    local showing = #MediaBrowser.filteredClips
    
    if total == 0 then
        return "No clips in Media Pool"
    elseif showing == total then
        return string.format("Showing all %d clip(s)", total)
    else
        return string.format("Showing %d of %d clip(s)", showing, total)
    end
end

--[[
    Populate the clip list widget with filtered clips.
--]]
function MediaBrowser.populateClipList()
    local clipList = MediaBrowser.getComponent("clipList")
    if not clipList then
        return
    end
    
    -- Clear existing items
    clipList:Clear()
    
    -- Add clips to list
    for _, clip in ipairs(MediaBrowser.filteredClips) do
        local item = clipList:AddTopLevelItem({"", "", ""})
        item:SetText(0, clip.name)
        
        -- Format duration as mm:ss
        local durationText = MediaBrowser.formatDuration(clip.duration)
        item:SetText(1, durationText)
        
        -- Show type
        local typeText = clip.type or "Unknown"
        item:SetText(2, typeText)
        
        -- Store clip data with item
        item.clipData = clip
    end
    
    -- Update status
    MediaBrowser.updateStatusLabel()
    
    -- Show/hide empty state
    local emptyLabel = MediaBrowser.getComponent("emptyLabel")
    if emptyLabel then
        emptyLabel:SetVisible(#MediaBrowser.filteredClips == 0)
    end
end

--[[
    Format duration in seconds to mm:ss display.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        formatted: String like "38:00" or "2:30"
--]]
function MediaBrowser.formatDuration(seconds)
    seconds = tonumber(seconds) or 0
    local mins = math.floor(seconds / 60)
    local secs = math.floor(seconds % 60)
    return string.format("%d:%02d", mins, secs)
end

--[[
    Handle search text changes.
    
    Args:
        text: The new search text
--]]
function MediaBrowser.onSearchTextChanged(text)
    MediaBrowser.searchText = text:lower()
    
    -- Filter clips based on search text
    if MediaBrowser.searchText == "" then
        MediaBrowser.filteredClips = MediaBrowser.clips
    else
        MediaBrowser.filteredClips = {}
        for _, clip in ipairs(MediaBrowser.clips) do
            local name = (clip.name or ""):lower()
            if name:find(MediaBrowser.searchText, 1, true) then
                table.insert(MediaBrowser.filteredClips, clip)
            end
        end
    end
    
    -- Repopulate list
    MediaBrowser.populateClipList()
end

--[[
    Handle clip selection change.
--]]
function MediaBrowser.onClipSelectionChanged()
    local clipList = MediaBrowser.getComponent("clipList")
    if not clipList then
        return
    end
    
    local selectedItems = clipList:SelectedItems()
    if #selectedItems > 0 then
        local selectedItem = selectedItems[1]
        MediaBrowser.selectedClip = selectedItem.clipData
        
        -- Enable select button
        local selectButton = MediaBrowser.getComponent("selectButton")
        if selectButton then
            selectButton:SetEnabled(true)
        end
    else
        MediaBrowser.selectedClip = nil
        
        -- Disable select button
        local selectButton = MediaBrowser.getComponent("selectButton")
        if selectButton then
            selectButton:SetEnabled(false)
        end
    end
end

--[[
    Handle clip double-click (quick select).
    
    Args:
        item: The double-clicked tree item
--]]
function MediaBrowser.onClipDoubleClicked(item)
    if item and item.clipData then
        MediaBrowser.selectedClip = item.clipData
        MediaBrowser.confirmSelection()
    end
end

--[[
    Refresh the Media Pool list from Resolve.
--]]
function MediaBrowser.refreshMediaPool()
    local ResolveAPI = require("resolve_api")
    
    local clips, err = ResolveAPI.getVideoClips()
    if err then
        local msg = ResolveAPI.getErrorMessage(err)
        MediaBrowser.showErrorDialog(msg)
        return
    end
    
    MediaBrowser.clips = clips
    
    -- Re-apply search filter
    if MediaBrowser.searchText ~= "" then
        MediaBrowser.onSearchTextChanged(MediaBrowser.searchText)
    else
        MediaBrowser.filteredClips = clips
        MediaBrowser.populateClipList()
    end
end

--[[
    Confirm clip selection and proceed with validation.
--]]
function MediaBrowser.confirmSelection()
    if not MediaBrowser.selectedClip then
        return
    end
    
    -- Validate media before proceeding (Story 4.5)
    MediaBrowser.validateAndProceed(MediaBrowser.selectedClip)
end

--[[
    Validate media transcribability before proceeding to transcription.
    
    Args:
        clip: The selected clip data
--]]
function MediaBrowser.validateAndProceed(clip)
    -- Validate clip parameter
    if not clip then
        MediaBrowser.showErrorDialog("No clip selected")
        return
    end
    
    -- Ensure clip has minimum required fields with defaults
    clip.id = clip.id or "unknown_clip"
    clip.name = clip.name or clip.id
    clip.path = clip.path or ""
    clip.audio_tracks = clip.audio_tracks or 0
    clip.codec = clip.codec or ""
    clip.duration = clip.duration or 0
    
    -- Check if already validated in this session
    if _session.validatedClips[clip.id] then
        local cached = _session.validatedClips[clip.id]
        if cached.valid then
            -- Use cached result, proceed directly
            MediaBrowser.proceedWithSelection(clip)
            return
        else
            -- Show cached error
            MediaBrowser.showValidationError(cached)
            return
        end
    end
    
    -- Show validation in progress
    MediaBrowser.showValidationSpinner("Checking media compatibility...")
    MediaBrowser.isValidating = true
    
    -- Send validation request to Python backend
    local request = {
        method = "validate_transcribable_media",
        params = {
            clip_id = clip.id,
            clip_name = clip.name,
            file_path = clip.path,
            audio_tracks = clip.audio_tracks,
            codec = clip.codec,
            duration_seconds = clip.duration
        },
        id = MediaBrowser.generateRequestId()
    }
    
    -- Send to Python (actual implementation depends on protocol layer)
    MediaBrowser.sendToPython(request)
    
    -- Response will be handled by handleValidationResponse
end

--[[
    Handle validation response from Python backend.
    
    Args:
        response: The JSON-RPC response from validate_transcribable_media
--]]
function MediaBrowser.handleValidationResponse(response)
    MediaBrowser.isValidating = false
    MediaBrowser.hideValidationSpinner()
    
    -- Handle transport/protocol errors
    if response.error then
        -- System error during validation
        MediaBrowser.showErrorDialog(
            "Validation failed: " .. (response.error.message or "Unknown error")
        )
        return
    end
    
    local result = response.result
    MediaBrowser.validationResult = result
    
    -- Cache validation result
    if result and MediaBrowser.selectedClip then
        _session.validatedClips[MediaBrowser.selectedClip.id] = result
    end
    
    if result.valid then
        -- Validation passed, proceed with selection
        MediaBrowser.proceedWithSelection(MediaBrowser.selectedClip)
    else
        -- Validation failed, show error
        MediaBrowser.showValidationError(result)
    end
end

--[[
    Show validation error dialog with actionable options.
    
    Args:
        result: Validation result with error details
--]]
function MediaBrowser.showValidationError(result)
    local errorCode = result.error_code or "UNKNOWN"
    local errorMessage = result.error_message or "Validation failed"
    local suggestion = result.suggestion or "Try a different clip"
    
    -- Build error dialog based on error code
    local dialog = {
        title = "Media Validation Failed",
        width = 550,
        height = 400,
        modal = true,
        
        components = {
            {
                type = "Label",
                id = "errorIcon",
                text = "⚠",
                alignment = { AlignHCenter = true },
                styleSheet = "font-size: 48px; color: #FFA500;"
            },
            {
                type = "Label",
                id = "errorTitle",
                text = "Cannot Transcribe Media",
                alignment = { AlignHCenter = true },
                styleSheet = "font-weight: bold; font-size: 16px; padding: 10px;"
            },
            {
                type = "Label",
                id = "errorMessage",
                text = errorMessage,
                alignment = { AlignHCenter = true, AlignTop = true },
                styleSheet = "color: #666; padding: 10px;"
            },
            {
                type = "Label",
                id = "suggestionLabel",
                text = "Suggestion: " .. suggestion,
                alignment = { AlignHCenter = true, AlignTop = true },
                styleSheet = "color: #333; font-style: italic; padding: 10px; background-color: #f5f5f5;"
            }
        }
    }
    
    -- Add error-specific buttons
    if errorCode == MediaBrowser.ERROR_CODES.UNSUPPORTED_CODEC then
        -- Show format guide button
        table.insert(dialog.components, {
            type = "Button",
            id = "formatGuideButton",
            text = "Show Format Guide",
            onClicked = function()
                MediaBrowser.showFormatConversionGuide()
            end
        })
    elseif errorCode == MediaBrowser.ERROR_CODES.MEDIA_OFFLINE then
        -- Show reconnect button with guidance
        table.insert(dialog.components, {
            type = "Label",
            id = "reconnectInfo",
            text = "To reconnect: Right-click clip in Media Pool → 'Reconnect Media'",
            styleSheet = "color: #666; font-size: 11px; padding: 5px;"
        })
        table.insert(dialog.components, {
            type = "Button",
            id = "reconnectButton",
            text = "Reconnect in Resolve",
            onClicked = function()
                MediaBrowser.showReconnectGuidance()
            end
        })
    end
    
    -- Always add Select Different Clip button
    table.insert(dialog.components, {
        type = "Layout",
        layout = "Horizontal",
        components = {
            {
                type = "Stretch"
            },
            {
                type = "Button",
                id = "selectDifferentButton",
                text = "Select Different Clip",
                default = true,
                onClicked = function()
                    -- Clear selection and return to browser
                    MediaBrowser.selectedClip = nil
                    MediaBrowser.closeErrorDialog()
                end
            },
            {
                type = "Button",
                id = "cancelButton",
                text = "Cancel",
                onClicked = function()
                    MediaBrowser.close()
                end
            }
        }
    })
    
    -- Show the dialog
    MediaBrowser.currentErrorDialog = dialog
    -- In Resolve: dialog:Show()
end

--[[
    Show format conversion guide for unsupported codecs.
--]]
function MediaBrowser.showFormatConversionGuide()
    local guide = [[
Format Conversion Guide

If your clip uses an unsupported audio codec:

1. Select the clip in Resolve's Edit page
2. Go to the Deliver (Export) page  
3. Choose "YouTube 1080p" preset
4. Render to a new file
5. Import the rendered file back to Media Pool
6. Select the new clip in RoughCut

Recommended settings:
- Format: MP4 or MOV
- Audio: AAC (stereo, 48kHz)

This ensures your clip has a supported audio format.
]]

    local dialog = {
        title = "Format Conversion Guide",
        width = 500,
        height = 450,
        modal = true,
        components = {
            {
                type = "TextEdit",
                id = "guideText",
                text = guide,
                readOnly = true,
                styleSheet = "font-family: monospace; font-size: 11px;"
            },
            {
                type = "Button",
                id = "closeButton",
                text = "Close",
                onClicked = function()
                    MediaBrowser.closeFormatGuide()
                end
            }
        }
    }
    
    MediaBrowser.currentFormatGuideDialog = dialog
    -- In Resolve: dialog:Show()
end

--[[
    Show reconnection guidance for offline media.
--]]
function MediaBrowser.showReconnectGuidance()
    local guidance = [[
Reconnect Media in DaVinci Resolve

To reconnect offline media:

1. Go to the Media Pool (Media page)
2. Find the offline clip (shown with a question mark icon)
3. Right-click on the clip
4. Select "Reconnect Media..."
5. Navigate to the new location of the media file
6. Select the file and click "Open"

Alternatively:
- Use "Relink Media for Selected Clips" if you have multiple offline clips
- Check that your media drives are connected and mounted

After reconnecting, return to RoughCut and try again.
]]

    local dialog = {
        title = "Reconnect Media in Resolve",
        width = 500,
        height = 400,
        modal = true,
        components = {
            {
                type = "TextEdit",
                id = "guidanceText",
                text = guidance,
                readOnly = true,
                styleSheet = "font-family: monospace; font-size: 11px;"
            },
            {
                type = "Button",
                id = "closeButton",
                text = "Close",
                onClicked = function()
                    if MediaBrowser.currentReconnectDialog then
                        MediaBrowser.currentReconnectDialog = nil
                    end
                end
            }
        }
    }
    
    MediaBrowser.currentReconnectDialog = dialog
    -- In Resolve: dialog:Show()
end

--[[
    Show validation spinner/progress indicator with timeout.
    
    Args:
        message: Progress message to display
--]]
function MediaBrowser.showValidationSpinner(message)
    -- Store validation start time for timeout tracking
    MediaBrowser.validationStartTime = os.time()
    
    -- In Resolve, this would show a modal progress dialog
    -- For now, update status label
    local statusLabel = MediaBrowser.getComponent("statusLabel")
    if statusLabel then
        statusLabel:SetText(message .. " (please wait)")
    end
    
    -- Disable select button during validation
    local selectButton = MediaBrowser.getComponent("selectButton")
    if selectButton then
        selectButton:SetEnabled(false)
    end
    
    -- Start timeout timer (if Resolve timer API available)
    MediaBrowser.startValidationTimeoutTimer()
end

--[[
    Start validation timeout timer.
    Automatically cancels validation if it takes too long.
--]]
function MediaBrowser.startValidationTimeoutTimer()
    -- Check if Resolve timer API is available
    if resolve and resolve.GetResolve and resolve:GetResolve() then
        local resolveApp = resolve:GetResolve()
        if resolveApp and resolveApp.RunScript then
            -- Schedule timeout check
            -- Note: Actual implementation depends on Resolve's timer capabilities
            MediaBrowser.timeoutScheduled = true
        end
    end
end

--[[
    Check if validation has timed out.
    
    Returns:
        timedOut: True if validation exceeded timeout limit
--]]
function MediaBrowser.checkValidationTimeout()
    if not MediaBrowser.validationStartTime then
        return false
    end
    
    local elapsed = os.time() - MediaBrowser.validationStartTime
    return elapsed > MediaBrowser.VALIDATION_TIMEOUT
end

--[[
    Handle validation timeout.
--]]
function MediaBrowser.handleValidationTimeout()
    MediaBrowser.isValidating = false
    MediaBrowser.hideValidationSpinner()
    
    -- Show timeout error
    MediaBrowser.showErrorDialog(
        "Validation timed out after " .. MediaBrowser.VALIDATION_TIMEOUT .. " seconds. " ..
        "Please try again or select a different clip."
    )
end

--[[
    Hide validation spinner and clear timeout state.
--]]
function MediaBrowser.hideValidationSpinner()
    MediaBrowser.validationStartTime = nil
    MediaBrowser.timeoutScheduled = false
    MediaBrowser.updateStatusLabel()
    
    -- Re-enable select button if clip selected
    if MediaBrowser.selectedClip then
        local selectButton = MediaBrowser.getComponent("selectButton")
        if selectButton then
            selectButton:SetEnabled(true)
        end
    end
end

--[[
    Close error dialog.
--]]
function MediaBrowser.closeErrorDialog()
    if MediaBrowser.currentErrorDialog then
        MediaBrowser.currentErrorDialog = nil
    end
end

--[[
    Close format guide dialog.
--]]
function MediaBrowser.closeFormatGuide()
    if MediaBrowser.currentFormatGuideDialog then
        MediaBrowser.currentFormatGuideDialog = nil
    end
end

--[[
    Proceed with clip selection after validation passes.
    
    Args:
        clip: The validated clip
--]]
function MediaBrowser.proceedWithSelection(clip)
    -- Send selection to Python backend via protocol
    local request = {
        method = "select_clip",
        params = {
            clip_id = clip.id,
            file_path = clip.path,
            clip_name = clip.name
        },
        id = MediaBrowser.generateRequestId()
    }
    
    -- Send to Python (actual implementation depends on protocol layer)
    MediaBrowser.sendToPython(request)
    
    -- Close browser
    MediaBrowser.close()
    
    -- Trigger next workflow step
    MediaBrowser.proceedToTranscription()
end

--[[
    Proceed to transcription retrieval step.
--]]
function MediaBrowser.proceedToTranscription()
    -- This would trigger the next UI step (Story 4.2)
    -- For now, we can emit a signal or call a workflow function
    if MediaBrowser.onSelectionConfirmed then
        MediaBrowser.onSelectionConfirmed(MediaBrowser.selectedClip)
    end
end

--[[
    Generate unique request ID for protocol calls.
    
    Returns:
        id: Unique request ID string
--]]
function MediaBrowser.generateRequestId()
    return string.format("req_%d_%d", os.time(), math.random(1000, 9999))
end

--[[
    Send request to Python backend.
    
    Args:
        request: Table containing method, params, and id
--]]
function MediaBrowser.sendToPython(request)
    -- Convert to JSON and send via stdout
    -- This is handled by the communication layer
    local json = require("utils.json")  -- Assume json utility exists
    local message = json.encode(request)
    io.write(message .. "\n")
    io.flush()
end

--[[
    Proceed to transcription retrieval step.
--]]
function MediaBrowser.proceedToTranscription()
    -- This would trigger the next UI step (Story 4.2)
    -- For now, we can emit a signal or call a workflow function
    if MediaBrowser.onSelectionConfirmed then
        MediaBrowser.onSelectionConfirmed(MediaBrowser.selectedClip)
    end
end

--[[
    Close the browser dialog.
--]]
function MediaBrowser.close()
    if MediaBrowser.currentDialog then
        -- In Resolve environment: MediaBrowser.currentDialog:Hide()
        -- or MediaBrowser.currentDialog:Delete()
        MediaBrowser.currentDialog = nil
    end
    
    MediaBrowser.selectedClip = nil
    MediaBrowser.clips = {}
    MediaBrowser.filteredClips = {}
end

--[[
    Show error dialog.
    
    Args:
        message: Error message to display
--]]
function MediaBrowser.showErrorDialog(message)
    -- In Resolve environment, use message box
    -- local resolve = Resolve()
    -- if resolve then
    --     resolve:ShowMessage("RoughCut Error", message)
    -- end
    
    -- Fallback to print for now
    print("[RoughCut Error] " .. message)
end

--[[
    Get a component from the current dialog.
    
    Args:
        id: Component ID string
        
    Returns:
        component: The UI component, or nil if not found
--]]
function MediaBrowser.getComponent(id)
    if not MediaBrowser.currentDialog then
        return nil
    end
    
    -- In actual Resolve environment, this would lookup the component
    -- For now, return a placeholder that the real implementation will replace
    return MediaBrowser.currentDialog.components[id]
end

--[[
    Update the status label with current counts.
--]]
function MediaBrowser.updateStatusLabel()
    local statusLabel = MediaBrowser.getComponent("statusLabel")
    if statusLabel then
        statusLabel:SetText(MediaBrowser.getStatusText())
    end
end

--[[
    Set callback for when selection is confirmed.
    
    Args:
        callback: Function(clipData) to call when selection confirmed
--]]
function MediaBrowser.setOnSelectionConfirmed(callback)
    MediaBrowser.onSelectionConfirmed = callback
end

return MediaBrowser
