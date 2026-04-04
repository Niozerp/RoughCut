-- RoughCut Format Management Window
-- Displays list of available video format templates
-- Compatible with DaVinci Resolve's Lua scripting environment
-- Version: 1.0.0

local formatManagement = {}

-- Import dependencies
local protocol = require("utils.protocol")
local logger = require("utils.logger")

-- Window configuration
local WINDOW_CONFIG = {
    id = "RoughCutFormatManagement",
    title = "RoughCut - Format Management",
    width = 600,
    height = 500
}

-- State tracking
local parentWindowRef = nil
local currentWindowRef = nil
local formatsList = {}
local isLoading = false
local selectedFormatId = nil

-- Create the format management window
-- @param uiManager Resolve UI Manager instance
-- @param parentWindow Reference to main window for navigation back
-- @return window table or nil on error
function formatManagement.create(uiManager, parentWindow)
    if not uiManager then
        logger.error("UI Manager required for format management window")
        return nil
    end
    
    -- Store reference to parent for back navigation
    parentWindowRef = parentWindow
    
    -- Create window
    local ok, window = pcall(function()
        return uiManager:Add({
            type = "Window",
            id = WINDOW_CONFIG.id,
            title = WINDOW_CONFIG.title,
            width = WINDOW_CONFIG.width,
            height = WINDOW_CONFIG.height,
            spacing = 10,
            padding = 20
        })
    end)
    
    if not ok or not window then
        logger.error("Failed to create format management window")
        return nil
    end
    
    currentWindowRef = window
    
    -- Build the UI
    _buildUI(window)
    
    -- Load formats on creation
    _loadFormatsAsync()
    
    return window
end

-- Build the UI elements
-- @param window The window to add elements to
function _buildUI(window)
    -- Header
    pcall(function()
        window:Add({
            type = "Label",
            text = "Format Templates",
            font = { size = 22, bold = true },
            alignment = { alignHCenter = true }
        })
        
        window:Add({
            type = "Label",
            text = "Select a format template for rough cut generation",
            font = { size = 11 },
            alignment = { alignHCenter = true }
        })
    end)
    
    -- Loading indicator
    pcall(function()
        window:Add({
            type = "Label",
            id = "lblLoading",
            text = "Loading templates...",
            font = { size = 12, italic = true },
            alignment = { alignHCenter = true },
            height = 30
        })
    end)
    
    -- Status message (for errors/empty state)
    pcall(function()
        window:Add({
            type = "Label",
            id = "lblStatus",
            text = "",
            font = { size = 11 },
            alignment = { alignHCenter = true },
            height = 0  -- Hidden by default
        })
    end)
    
    -- Formats list container
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 10
        })
        
        -- Scrollable list area
        local listContainer = window:Add({
            type = "VGroup",
            id = "grpFormatsList",
            spacing = 5
        })
        
        -- Placeholder for format items (will be populated dynamically)
        listContainer:Add({
            type = "Label",
            id = "lblPlaceholder",
            text = "No templates available",
            font = { size = 12, italic = true },
            alignment = { alignHCenter = true }
        })
    end)
    
    -- Spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 20
        })
    end)
    
    -- Back button
    pcall(function()
        local backBtn = window:Add({
            type = "Button",
            id = "btnBackToMain",
            text = "← Back to Main Menu",
            height = 35,
            alignment = { alignLeft = true }
        })
        
        if backBtn then
            backBtn.Clicked = function()
                formatManagement.close()
            end
        end
    end)
end

-- Load formats asynchronously from Python backend
function _loadFormatsAsync()
    isLoading = true
    _updateLoadingState(true)
    
    -- Make protocol request
    local request = {
        method = "get_available_formats",
        params = {},
        id = "formats_" .. tostring(os.time())
    }
    
    protocol.sendRequest(request, function(response)
        -- Handle response (called asynchronously)
        isLoading = false
        
        if response.error then
            logger.error("Failed to load formats: " .. tostring(response.error.message))
            _showStatus("Error loading templates: " .. tostring(response.error.message))
            _updateLoadingState(false)
            return
        end
        
        if response.result and response.result.formats then
            formatsList = response.result.formats
            _populateFormatsList()
        else
            formatsList = {}
            _showStatus("No format templates found")
        end
        
        _updateLoadingState(false)
    end)
end

-- Populate the formats list in the UI
function _populateFormatsList()
    local window = currentWindowRef
    if not window then
        return
    end
    
    -- Find the list container
    local listContainer = nil
    pcall(function()
        for _, child in ipairs(window:GetItems() or {}) do
            if child.id == "grpFormatsList" then
                listContainer = child
                break
            end
        end
    end)
    
    if not listContainer then
        logger.error("Could not find formats list container")
        return
    end
    
    -- Clear existing items
    pcall(function()
        local items = listContainer:GetItems()
        if items then
            for i = #items, 1, -1 do
                listContainer:Remove(items[i])
            end
        end
    end)
    
    -- Check if we have formats
    if #formatsList == 0 then
        pcall(function()
            listContainer:Add({
                type = "Label",
                text = "No templates found in templates/formats/",
                font = { size = 12, italic = true },
                alignment = { alignHCenter = true }
            })
            
            listContainer:Add({
                type = "Label",
                text = "Add .md template files to get started",
                font = { size = 11 },
                alignment = { alignHCenter = true }
            })
        end)
        return
    end
    
    -- Add each format as a clickable item
    for _, format in ipairs(formatsList) do
        _addFormatItem(listContainer, format)
    end
end

-- Add a single format item to the list
-- @param container The list container
-- @param format The format data table
function _addFormatItem(container, format)
    pcall(function()
        -- Create a group for this format item
        local itemGroup = container:Add({
            type = "VGroup",
            id = "fmt_" .. tostring(format.id),
            spacing = 2,
            padding = 10
        })
        
        -- Format name (bold, clickable)
        local nameLabel = itemGroup:Add({
            type = "Label",
            text = format.name or "Unnamed Template",
            font = { size = 14, bold = true },
            alignment = { alignLeft = true }
        })
        
        -- Format description
        itemGroup:Add({
            type = "Label",
            text = format.description or "No description available",
            font = { size = 11 },
            alignment = { alignLeft = true },
            wrap = true
        })
        
        -- Separator line
        itemGroup:Add({
            type = "Label",
            text = "",
            height = 1,
            styleSheet = [[
                background-color: #cccccc;
            ]]
        })
        
        -- Make the item clickable
        if nameLabel then
            -- Store format ID for selection
            nameLabel.formatId = format.id
            
            -- Note: Clicked event depends on Resolve's UI capabilities
            -- Fallback: Show visual feedback on hover
        end
    end)
end

-- Update loading state visibility
-- @param loading Whether loading is in progress
function _updateLoadingState(loading)
    local window = currentWindowRef
    if not window then
        return
    end
    
    pcall(function()
        for _, child in ipairs(window:GetItems() or {}) do
            if child.id == "lblLoading" then
                child.Height = loading and 30 or 0
                child.Visible = loading
            end
        end
    end)
end

-- Show status message
-- @param message The message to display (empty to hide)
function _showStatus(message)
    local window = currentWindowRef
    if not window then
        return
    end
    
    pcall(function()
        for _, child in ipairs(window:GetItems() or {}) do
            if child.id == "lblStatus" then
                child.Text = message or ""
                child.Height = (message and #message > 0) and 30 or 0
                child.Visible = (message and #message > 0)
            end
        end
    end)
end

-- Show the format management window
-- @return boolean success
function formatManagement.show()
    if not currentWindowRef then
        logger.error("No format management window to show")
        return false
    end
    
    local ok = pcall(function()
        currentWindowRef:Show()
    end)
    
    if not ok then
        logger.error("Failed to show format management window")
        return false
    end
    
    -- Reload formats when showing (in case they changed)
    _loadFormatsAsync()
    
    return true
end

-- Hide the format management window
-- @return boolean success
function formatManagement.hide()
    if not currentWindowRef then
        return false
    end
    
    local ok = pcall(function()
        currentWindowRef:Hide()
    end)
    
    return ok
end

-- Close the format management window and return to main
-- @return boolean success
function formatManagement.close()
    logger.info("Closing format management window")
    
    local ok = pcall(function()
        -- Hide current window
        if currentWindowRef then
            currentWindowRef:Hide()
        end
        
        -- Show parent window if available
        if parentWindowRef and parentWindowRef.Show then
            parentWindowRef:Show()
        end
        
        -- Clear reference
        currentWindowRef = nil
    end)
    
    if not ok then
        logger.error("Failed to close format management window properly")
    end
    
    return ok
end

-- Clean up resources
function formatManagement.destroy()
    if currentWindowRef then
        pcall(function()
            currentWindowRef:Close()
        end)
        currentWindowRef = nil
    end
    parentWindowRef = nil
    formatsList = {}
end

-- Get currently selected format
-- @return string format ID or nil
function formatManagement.getSelectedFormat()
    return selectedFormatId
end

return formatManagement
