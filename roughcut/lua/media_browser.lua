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
    Confirm clip selection and proceed.
--]]
function MediaBrowser.confirmSelection()
    if not MediaBrowser.selectedClip then
        return
    end
    
    -- Send selection to Python backend via protocol
    local request = {
        method = "select_clip",
        params = {
            clip_id = MediaBrowser.selectedClip.id,
            file_path = MediaBrowser.selectedClip.path,
            clip_name = MediaBrowser.selectedClip.name
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
