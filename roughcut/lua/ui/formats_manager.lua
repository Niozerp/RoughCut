-- RoughCut Format Management Window
-- Displays list of available video format templates
-- Compatible with DaVinci Resolve's Lua scripting environment
-- Version: 1.1.0

local formatManagement = {}

-- Import dependencies
-- Note: utils.protocol may need to be implemented if not available
-- For now, we use a safe require with fallback
local protocol = nil
local logger = nil

-- Safely require modules with fallbacks
local ok, mod = pcall(require, "utils.protocol")
if ok then
    protocol = mod
else
    -- Fallback: try roughcut.protocol or define stub
    ok, mod = pcall(require, "roughcut.protocol")
    if ok then
        protocol = mod
    else
        -- Stub protocol for compatibility
        protocol = {
            sendRequest = function(req, callback)
                -- Async callback simulation
                if callback then
                    callback({
                        result = { formats = {} },
                        error = nil
                    })
                end
            end
        }
    end
end

ok, mod = pcall(require, "utils.logger")
if ok then
    logger = mod
else
    -- Fallback logger
    logger = {
        error = function(msg) print("[ERROR] " .. tostring(msg)) end,
        warn = function(msg) print("[WARN] " .. tostring(msg)) end,
        info = function(msg) print("[INFO] " .. tostring(msg)) end,
        debug = function(msg) end
    }
end

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
local selectedFormatSlug = nil
local requestCounter = 0
local loadingStartTime = 0

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
    local ok_create, window = pcall(function()
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
    
    if not ok_create or not window then
        logger.error("Failed to create format management window: " .. tostring(window))
        return nil
    end
    
    currentWindowRef = window
    
    -- Build the UI
    local ok_build, err = pcall(function()
        _buildUI(window)
    end)
    
    if not ok_build then
        logger.error("Failed to build UI: " .. tostring(err))
        pcall(function() window:Close() end)
        currentWindowRef = nil
        return nil
    end
    
    -- Load formats on creation
    _loadFormatsAsync()
    
    return window
end

-- Build the UI elements
-- @param window The window to add elements to
function _buildUI(window)
    -- Header
    local ok = pcall(function()
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
    
    if not ok then
        logger.warn("Failed to add header labels")
    end
    
    -- Loading indicator
    ok = pcall(function()
        window:Add({
            type = "Label",
            id = "lblLoading",
            text = "Loading templates...",
            font = { size = 12, italic = true },
            alignment = { alignHCenter = true },
            height = 30
        })
    end)
    
    if not ok then
        logger.warn("Failed to add loading indicator")
    end
    
    -- Status message (for errors/empty state)
    ok = pcall(function()
        window:Add({
            type = "Label",
            id = "lblStatus",
            text = "",
            font = { size = 11 },
            alignment = { alignHCenter = true },
            height = 0  -- Hidden by default
        })
    end)
    
    if not ok then
        logger.warn("Failed to add status label")
    end
    
    -- Formats list container
    ok = pcall(function()
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
    
    if not ok then
        logger.warn("Failed to add list container")
    end
    
    -- Spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 20
        })
    end)
    
    -- Back button
    ok = pcall(function()
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
    
    if not ok then
        logger.warn("Failed to add back button")
    end
end

-- Load formats asynchronously from Python backend
function _loadFormatsAsync()
    -- Prevent concurrent loading
    if isLoading then
        logger.debug("Already loading formats, skipping duplicate request")
        return
    end
    
    isLoading = true
    loadingStartTime = os.time()
    _updateLoadingState(true)
    _showStatus("")  -- Clear any previous status
    
    -- Generate unique request ID using counter + time
    requestCounter = requestCounter + 1
    local requestId = string.format("formats_%d_%d_%d", os.time(), requestCounter, math.random(10000))
    
    -- Make protocol request
    local request = {
        method = "get_available_formats",
        params = {},
        id = requestId
    }
    
    -- Set up timeout timer (10 seconds)
    local timeoutTimer = nil
    local timeoutOk, timeoutMod = pcall(require, "utils.timer")
    if timeoutOk and timeoutMod and timeoutMod.start then
        timeoutTimer = timeoutMod.start(10000, function()
            if isLoading then
                isLoading = false
                _updateLoadingState(false)
                _showStatus("Request timed out. Please try again.")
                logger.error("Format loading timed out after 10 seconds")
            end
        end)
    end
    
    -- Send request with callback
    local sendOk, sendErr = pcall(function()
        protocol.sendRequest(request, function(response)
            -- Cancel timeout timer if it exists
            if timeoutTimer and timeoutTimer.cancel then
                pcall(function() timeoutTimer.cancel() end)
            end
            
            -- Handle response (called asynchronously)
            _handleLoadResponse(response)
        end)
    end)
    
    if not sendOk then
        isLoading = false
        _updateLoadingState(false)
        _showStatus("Failed to send request: " .. tostring(sendErr))
        logger.error("Failed to send protocol request: " .. tostring(sendErr))
    end
end

-- Handle the load formats response
-- @param response The response table from protocol
function _handleLoadResponse(response)
    isLoading = false
    _updateLoadingState(false)
    
    -- Validate response is a table
    if type(response) ~= "table" then
        local errMsg = "Invalid response: expected table, got " .. type(response)
        logger.error(errMsg)
        _showStatus("Error: " .. errMsg)
        return
    end
    
    -- Check for error in response
    if response.error then
        local errorMsg = "Unknown error"
        if type(response.error) == "table" then
            errorMsg = tostring(response.error.message or response.error.code or "Unknown error")
        elseif type(response.error) == "string" then
            errorMsg = response.error
        end
        logger.error("Failed to load formats: " .. errorMsg)
        _showStatus("Error loading templates: " .. errorMsg)
        return
    end
    
    -- Validate result structure
    if type(response.result) ~= "table" then
        local errMsg = "Invalid result: expected table, got " .. type(response.result)
        logger.error(errMsg)
        _showStatus("Error: " .. errMsg)
        return
    end
    
    if response.result.formats == nil then
        local errMsg = "Invalid response: missing 'formats' field"
        logger.error(errMsg)
        _showStatus("Error: " .. errMsg)
        return
    end
    
    if type(response.result.formats) ~= "table" then
        local errMsg = "Invalid formats: expected table, got " .. type(response.result.formats)
        logger.error(errMsg)
        _showStatus("Error: " .. errMsg)
        return
    end
    
    -- Success - store formats and populate list
    formatsList = response.result.formats
    
    local populateOk, populateErr = pcall(function()
        _populateFormatsList()
    end)
    
    if not populateOk then
        logger.error("Failed to populate formats list: " .. tostring(populateErr))
        _showStatus("Error displaying templates")
        return
    end
    
    -- Show empty state message if no formats
    if #formatsList == 0 then
        _showStatus("No format templates found. Add .md files to templates/formats/")
    end
end

-- Populate the formats list in the UI
function _populateFormatsList()
    local window = currentWindowRef
    if not window then
        logger.error("Cannot populate formats: no window reference")
        return
    end
    
    -- Find the list container
    local listContainer = nil
    local findOk = pcall(function()
        for _, child in ipairs(window:GetItems() or {}) do
            if child and child.id == "grpFormatsList" then
                listContainer = child
                break
            end
        end
    end)
    
    if not findOk then
        logger.error("Failed to enumerate window items")
        return
    end
    
    if not listContainer then
        logger.error("Could not find formats list container")
        return
    end
    
    -- Clear existing items
    local clearOk = pcall(function()
        local items = listContainer:GetItems()
        if items then
            for i = #items, 1, -1 do
                if items[i] then
                    listContainer:Remove(items[i])
                end
            end
        end
    end)
    
    if not clearOk then
        logger.warn("Failed to clear list container")
    end
    
    -- Check if we have formats
    if #formatsList == 0 then
        local addOk = pcall(function()
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
        
        if not addOk then
            logger.warn("Failed to add empty state message")
        end
        return
    end
    
    -- Add each format as a clickable item
    for i, format in ipairs(formatsList) do
        local itemOk, itemErr = pcall(function()
            _addFormatItem(listContainer, format, i)
        end)
        
        if not itemOk then
            logger.warn("Failed to add format item " .. tostring(i) .. ": " .. tostring(itemErr))
        end
    end
end

-- Add a single format item to the list
-- @param container The list container
-- @param format The format data table
-- @param index The index of this format in the list
function _addFormatItem(container, format, index)
    -- Validate format data
    if type(format) ~= "table" then
        logger.warn("Invalid format data at index " .. tostring(index) .. ": expected table")
        return
    end
    
    local slug = format.slug or format.id or "unknown_" .. tostring(index)
    local name = format.name or "Unnamed Template"
    local description = format.description or "No description available"
    
    -- Create a group for this format item
    local itemGroup = container:Add({
        type = "VGroup",
        id = "fmt_" .. tostring(slug),
        spacing = 2,
        padding = 10
    })
    
    if not itemGroup then
        logger.warn("Failed to create item group for " .. tostring(slug))
        return
    end
    
    -- Format name (bold, clickable)
    local nameLabel = itemGroup:Add({
        type = "Label",
        text = name,
        font = { size = 14, bold = true },
        alignment = { alignLeft = true }
    })
    
    -- Format description
    itemGroup:Add({
        type = "Label",
        text = description,
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
    
    -- Make the item clickable if possible
    if nameLabel then
        -- Store format slug for selection
        nameLabel.formatSlug = slug
        
        -- Try to set up click handler
        if nameLabel.Clicked then
            nameLabel.Clicked = function()
                _selectFormat(slug)
            end
        end
        
        -- Visual feedback on hover if supported
        if nameLabel.MouseEnter then
            nameLabel.MouseEnter = function()
                nameLabel.font = { size = 14, bold = true, underline = true }
            end
        end
        
        if nameLabel.MouseLeave then
            nameLabel.MouseLeave = function()
                nameLabel.font = { size = 14, bold = true, underline = false }
            end
        end
    end
end

-- Select a format
-- @param slug The slug of the selected format
function _selectFormat(slug)
    selectedFormatSlug = slug
    logger.info("Selected format: " .. tostring(slug))
    
    -- Update visual selection state
    local window = currentWindowRef
    if not window then
        return
    end
    
    pcall(function()
        for _, child in ipairs(window:GetItems() or {}) do
            if child and child.id == "grpFormatsList" then
                for _, item in ipairs(child:GetItems() or {}) do
                    if item and item.id == "fmt_" .. tostring(slug) then
                        -- Highlight selected item
                        item.styleSheet = [[
                            background-color: #e0e0e0;
                            border: 1px solid #666;
                        ]]
                    else
                        -- Reset other items
                        item.styleSheet = ""
                    end
                end
                break
            end
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
    
    local ok = pcall(function()
        for _, child in ipairs(window:GetItems() or {}) do
            if child and child.id == "lblLoading" then
                child.Height = loading and 30 or 0
                child.Visible = loading
            end
        end
    end)
    
    if not ok then
        logger.debug("Failed to update loading state")
    end
end

-- Show status message
-- @param message The message to display (empty to hide)
function _showStatus(message)
    local window = currentWindowRef
    if not window then
        return
    end
    
    local ok = pcall(function()
        for _, child in ipairs(window:GetItems() or {}) do
            if child and child.id == "lblStatus" then
                child.Text = message or ""
                child.Height = (message and #message > 0) and 30 or 0
                child.Visible = (message and #message > 0)
            end
        end
    end)
    
    if not ok then
        logger.debug("Failed to update status message")
    end
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
    -- Use delayed load to avoid UI blocking
    pcall(function()
        if not isLoading then
            _loadFormatsAsync()
        end
    end)
    
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
    
    local ok, err = pcall(function()
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
        logger.error("Failed to close format management window properly: " .. tostring(err))
    end
    
    return ok
end

-- Clean up resources
function formatManagement.destroy()
    local ok = pcall(function()
        if currentWindowRef then
            currentWindowRef:Close()
        end
    end)
    
    if not ok then
        logger.warn("Error during window destruction")
    end
    
    currentWindowRef = nil
    parentWindowRef = nil
    formatsList = {}
    selectedFormatSlug = nil
    isLoading = false
end

-- Get currently selected format
-- @return string format slug or nil
function formatManagement.getSelectedFormat()
    return selectedFormatSlug
end

-- Get all loaded formats
-- @return table list of format data
function formatManagement.getFormats()
    return formatsList
end

-- Get a specific format by slug
-- @param slug The format slug to look up
-- @return table format data or nil
function formatManagement.getFormatBySlug(slug)
    if not slug then
        return nil
    end
    
    for _, format in ipairs(formatsList) do
        if format.slug == slug or format.id == slug then
            return format
        end
    end
    
    return nil
end

return formatManagement
