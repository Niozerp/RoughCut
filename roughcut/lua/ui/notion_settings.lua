-- RoughCut Notion Settings Component
-- Configuration window for Notion integration settings
-- Compatible with DaVinci Resolve's Lua scripting environment

local notionSettings = {}

-- Configuration constants
local VERSION = "0.4.0"
local WINDOW_CONFIG = {
    id = "RoughCutNotionSettings",
    title = "RoughCut - Notion Settings",
    width = 500,
    height = 450
}

-- UI element references
local windowRef = nil
local uiManagerRef = nil
local parentWindowRef = nil
local statusLabelRef = nil
local tokenInputRef = nil
local urlInputRef = nil
local errorLabelRef = nil
local testConnectionBtnRef = nil
local connectionStatusLabelRef = nil
local lastValidatedLabelRef = nil
local testSyncBtnRef = nil
local validatingIndicatorRef = nil

-- Current configuration state
local currentConfig = {
    configured = false,
    pageUrl = "",
    enabled = false,
    lastUpdated = nil,
    connectionStatus = "NOT_CONFIGURED",  -- NOT_CONFIGURED, CONNECTED, DISCONNECTED, ERROR
    lastValidated = nil
}

-- Create the Notion settings window
-- @param uiManager Resolve UI Manager instance
-- @return window table or nil on error
function notionSettings.create(uiManager)
    if not uiManager then
        print("RoughCut: Error - UI Manager required for settings window")
        return nil
    end
    
    uiManagerRef = uiManager
    
    -- Create window with pcall for error handling
    local success, window = pcall(function()
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
    
    if not success or not window then
        print("RoughCut: Error - Failed to create settings window")
        return nil
    end
    
    windowRef = window
    
    -- Add header
    local okHeader = pcall(function()
        window:Add({
            type = "Label",
            text = "Notion Integration Settings",
            font = { size = 18, bold = true },
            alignment = { alignHCenter = true }
        })
    end)
    
    if not okHeader then
        print("RoughCut: Warning - Could not add header")
    end
    
    -- Add subtitle/description
    local okSubtitle = pcall(function()
        window:Add({
            type = "Label",
            text = "Configure your Notion workspace for media database sync",
            font = { size = 10, italic = true },
            alignment = { alignHCenter = true }
        })
    end)
    
    -- Add spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 10
        })
    end)
    
    -- Status indicator
    local okStatus = pcall(function()
        statusLabelRef = window:Add({
            type = "Label",
            id = "statusLabel",
            text = "Status: Not configured",
            font = { size = 12, bold = true },
            alignment = { alignHCenter = true }
        })
    end)
    
    if not okStatus then
        print("RoughCut: Warning - Could not add status label")
    end
    
    -- Add spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 15
        })
    end)
    
    -- API Token label
    local okTokenLabel = pcall(function()
        window:Add({
            type = "Label",
            text = "Notion API Token:",
            font = { size = 12, bold = true },
            alignment = { alignLeft = true }
        })
    end)
    
    -- API Token help text
    pcall(function()
        window:Add({
            type = "Label",
            text = "Get your token from notion.so/my-integrations",
            font = { size = 9, italic = true },
            alignment = { alignLeft = true }
        })
    end)
    
    -- API Token input (masked for security)
    local okTokenInput = pcall(function()
        tokenInputRef = window:Add({
            type = "LineEdit",
            id = "tokenInput",
            placeholder = "secret_xxxxxxxxxxxx",
            echoMode = "Password",  -- Mask the input for security
            height = 30
        })
    end)
    
    if not okTokenInput then
        print("RoughCut: Warning - Could not add token input")
        -- Try without echoMode as fallback
        pcall(function()
            tokenInputRef = window:Add({
                type = "LineEdit",
                id = "tokenInput",
                placeholder = "secret_xxxxxxxxxxxx",
                height = 30
            })
        end)
    end
    
    -- Add spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 15
        })
    end)
    
    -- Page URL label
    local okUrlLabel = pcall(function()
        window:Add({
            type = "Label",
            text = "Notion Page URL:",
            font = { size = 12, bold = true },
            alignment = { alignLeft = true }
        })
    end)
    
    -- Page URL help text
    pcall(function()
        window:Add({
            type = "Label",
            text = "The Notion page where media database will be synced",
            font = { size = 9, italic = true },
            alignment = { alignLeft = true }
        })
    end)
    
    -- Page URL input
    local okUrlInput = pcall(function()
        urlInputRef = window:Add({
            type = "LineEdit",
            id = "urlInput",
            placeholder = "https://www.notion.so/workspace/page-id",
            height = 30
        })
    end)
    
    if not okUrlInput then
        print("RoughCut: Warning - Could not add URL input")
    end
    
    -- Add spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 10
        })
    end)
    
    -- Error message label (hidden by default)
    local okError = pcall(function()
        errorLabelRef = window:Add({
            type = "Label",
            id = "errorLabel",
            text = "",
            font = { size = 10, color = { r = 1, g = 0, b = 0 } },
            alignment = { alignHCenter = true },
            visible = false
        })
    end)
    
    -- Add spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 15
        })
    end)
    
    -- Save button
    local okSaveBtn = pcall(function()
        local saveBtn = window:Add({
            type = "Button",
            id = "saveButton",
            text = "Save Configuration",
            height = 45,
            style = {
                background = { r = 0.2, g = 0.6, b = 0.3 },
                hoverBackground = { r = 0.25, g = 0.7, b = 0.35 }
            }
        })
        
        -- Attach click handler
        saveBtn.Clicked = function()
            notionSettings.handleSave()
        end
        
        return saveBtn
    end)
    
    if not okSaveBtn then
        print("RoughCut: Warning - Could not add save button")
    end
    
    -- Small spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 10
        })
    end)
    
    -- Clear button
    local okClearBtn = pcall(function()
        local clearBtn = window:Add({
            type = "Button",
            id = "clearButton",
            text = "Clear Configuration",
            height = 35,
            style = {
                background = { r = 0.6, g = 0.2, b = 0.2 },
                hoverBackground = { r = 0.7, g = 0.25, b = 0.25 }
            }
        })
        
        -- Attach click handler
        clearBtn.Clicked = function()
            notionSettings.handleClear()
        end
        
        return clearBtn
    end)
    
    if not okClearBtn then
        print("RoughCut: Warning - Could not add clear button")
    end
    
    -- Spacer before test connection section
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 15
        })
    end)
    
    -- Separator line
    pcall(function()
        window:Add({
            type = "Label",
            text = "───────────────────────────────",
            alignment = { alignHCenter = true },
            font = { size = 10, color = { r = 0.5, g = 0.5, b = 0.5 } }
        })
    end)
    
    -- Connection Status Section Header
    pcall(function()
        window:Add({
            type = "Label",
            text = "Connection Status",
            font = { size = 12, bold = true },
            alignment = { alignHCenter = true }
        })
    end)
    
    -- Connection status indicator
    local okConnectionStatus = pcall(function()
        connectionStatusLabelRef = window:Add({
            type = "Label",
            id = "connectionStatusLabel",
            text = "Status: Not Configured",
            font = { size = 11, bold = true },
            alignment = { alignHCenter = true }
        })
    end)
    
    if not okConnectionStatus then
        print("RoughCut: Warning - Could not add connection status label")
    end
    
    -- Last validated timestamp
    local okLastValidated = pcall(function()
        lastValidatedLabelRef = window:Add({
            type = "Label",
            id = "lastValidatedLabel",
            text = "",
            font = { size = 9, italic = true, color = { r = 0.5, g = 0.5, b = 0.5 } },
            alignment = { alignHCenter = true }
        })
    end)
    
    if not okLastValidated then
        print("RoughCut: Warning - Could not add last validated label")
    end
    
    -- Validating indicator (hidden by default)
    local okValidatingIndicator = pcall(function()
        validatingIndicatorRef = window:Add({
            type = "Label",
            id = "validatingIndicator",
            text = "Testing connection...",
            font = { size = 10, italic = true, color = { r = 0.3, g = 0.3, b = 0.8 } },
            alignment = { alignHCenter = true },
            visible = false
        })
    end)
    
    if not okValidatingIndicator then
        print("RoughCut: Warning - Could not add validating indicator")
    end
    
    -- Small spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 10
        })
    end)
    
    -- Test Connection button
    local okTestBtn = pcall(function()
        local testBtn = window:Add({
            type = "Button",
            id = "testConnectionButton",
            text = "Test Connection",
            height = 40,
            style = {
                background = { r = 0.2, g = 0.5, b = 0.8 },
                hoverBackground = { r = 0.25, g = 0.6, b = 0.9 }
            }
        })
        
        -- Attach click handler
        testBtn.Clicked = function()
            notionSettings.handleTestConnection()
        end
        
        testConnectionBtnRef = testBtn
        return testBtn
    end)
    
    if not okTestBtn then
        print("RoughCut: Warning - Could not add test connection button")
    end
    
    -- Small spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 8
        })
    end)
    
    -- Test Sync button (placeholder for Epic 2)
    local okTestSyncBtn = pcall(function()
        local testSyncBtn = window:Add({
            type = "Button",
            id = "testSyncButton",
            text = "Test Sync (Preview)",
            height = 35,
            style = {
                background = { r = 0.4, g = 0.4, b = 0.6 },
                hoverBackground = { r = 0.5, g = 0.5, b = 0.7 }
            }
        })
        
        -- Attach click handler
        testSyncBtn.Clicked = function()
            notionSettings.handleTestSync()
        end
        
        testSyncBtnRef = testSyncBtn
        return testSyncBtn
    end)
    
    if not okTestSyncBtn then
        print("RoughCut: Warning - Could not add test sync button")
    end
    
    -- Add spacer before back button
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 20
        })
    end)
    
    -- Back button
    local okBackBtn = pcall(function()
        local backBtn = window:Add({
            type = "Button",
            id = "backButton",
            text = "← Back to Main Menu",
            height = 40,
            style = {
                background = { r = 0.4, g = 0.4, b = 0.4 },
                hoverBackground = { r = 0.5, g = 0.5, b = 0.5 }
            }
        })
        
        -- Attach click handler
        backBtn.Clicked = function()
            notionSettings.closeAndReturn()
        end
        
        return backBtn
    end)
    
    if not okBackBtn then
        print("RoughCut: Warning - Could not add back button")
    end
    
    return window
end

-- Show the settings window
-- @param uiManager Resolve UI Manager instance
-- @param parentWindow Parent window to return to (optional)
function notionSettings.show(uiManager, parentWindow)
    if not uiManager then
        print("RoughCut: Error - UI Manager required")
        return false
    end
    
    uiManagerRef = uiManager
    parentWindowRef = parentWindow
    
    -- Create window if it doesn't exist
    if not windowRef then
        notionSettings.create(uiManager)
    end
    
    if not windowRef then
        print("RoughCut: Error - Failed to create settings window")
        return false
    end
    
    -- Load current configuration
    notionSettings.loadConfig()
    
    -- Show window and hide parent
    local success = pcall(function()
        windowRef:Show()
        if parentWindow then
            parentWindow:Hide()
        end
    end)
    
    if not success then
        print("RoughCut: Error - Failed to show settings window")
        return false
    end
    
    return true
end

-- Hide the settings window
function notionSettings.hide()
    if windowRef then
        pcall(function()
            windowRef:Hide()
        end)
    end
end

-- Close and destroy the settings window
function notionSettings.close()
    if windowRef then
        pcall(function()
            windowRef:Close()
        end)
        windowRef = nil
    end
    
    -- Clear references
    uiManagerRef = nil
    parentWindowRef = nil
    statusLabelRef = nil
    tokenInputRef = nil
    urlInputRef = nil
    errorLabelRef = nil
    testConnectionBtnRef = nil
    connectionStatusLabelRef = nil
    lastValidatedLabelRef = nil
    testSyncBtnRef = nil
    validatingIndicatorRef = nil
end

-- Close settings window and return to parent
function notionSettings.closeAndReturn()
    -- Hide settings window
    notionSettings.hide()
    
    -- Show parent window
    if parentWindowRef then
        pcall(function()
            parentWindowRef:Show()
        end)
    end
    
    -- Clear parent reference
    parentWindowRef = nil
end

-- Load current configuration from backend
function notionSettings.loadConfig()
    -- Call Python backend via protocol to get current configuration
    local success, result = pcall(function()
        -- Prepare JSON-RPC request
        local request = {
            method = "get_notion_config",
            params = {},
            id = "load_" .. tostring(os.time())
        }
        
        -- Send request to Python backend via stdout/stdin protocol
        -- The response will come back through the protocol handler
        local requestJson = json.encode(request)
        print("RC_JSONRPC:" .. requestJson)
        
        -- For now, read response from a global that the protocol handler sets
        -- This is set by the RoughCut protocol response handler
        if _G._notion_config_response then
            local response = _G._notion_config_response
            _G._notion_config_response = nil  -- Clear after reading
            
            if response.error then
                print("RoughCut: Error loading config: " .. tostring(response.error.message))
                return nil
            end
            
            return response.result
        end
        
        return nil
    end)
    
    if success and result then
        currentConfig = {
            configured = result.configured or false,
            pageUrl = result.page_url or "",
            enabled = result.enabled or false,
            lastUpdated = result.last_updated
        }
    else
        -- Default to not configured if load fails
        currentConfig = {
            configured = false,
            pageUrl = "",
            enabled = false,
            lastUpdated = nil
        }
    end
    
    notionSettings.updateStatusDisplay()
end

-- Update the status label based on current config
function notionSettings.updateStatusDisplay()
    if not statusLabelRef then
        return
    end
    
    local success = pcall(function()
        if currentConfig.configured then
            statusLabelRef.Text = "Status: ✓ Configured"
            statusLabelRef.Font = { size = 12, bold = true, color = { r = 0, g = 0.7, b = 0 } }
            
            -- Pre-populate URL if available
            if urlInputRef and currentConfig.pageUrl then
                urlInputRef.Text = currentConfig.pageUrl
            end
        else
            statusLabelRef.Text = "Status: Not configured"
            statusLabelRef.Font = { size = 12, bold = true, color = { r = 0.7, g = 0.5, b = 0 } }
        end
    end)
    
    if not success then
        print("RoughCut: Warning - Could not update status display")
    end
    
    -- Also update connection status
    notionSettings.updateConnectionStatusDisplay()
end

-- Update connection status display
function notionSettings.updateConnectionStatusDisplay()
    if not connectionStatusLabelRef then
        return
    end
    
    local success = pcall(function()
        local status = currentConfig.connectionStatus or "NOT_CONFIGURED"
        
        if status == "CONNECTED" then
            connectionStatusLabelRef.Text = "Connection: ✓ Connected"
            connectionStatusLabelRef.Font = { size = 11, bold = true, color = { r = 0, g = 0.7, b = 0 } }
        elseif status == "DISCONNECTED" then
            connectionStatusLabelRef.Text = "Connection: ✗ Disconnected"
            connectionStatusLabelRef.Font = { size = 11, bold = true, color = { r = 0.8, g = 0.2, b = 0.2 } }
        elseif status == "ERROR" then
            connectionStatusLabelRef.Text = "Connection: ⚠ Error"
            connectionStatusLabelRef.Font = { size = 11, bold = true, color = { r = 0.8, g = 0.5, b = 0 } }
        else
            connectionStatusLabelRef.Text = "Connection: Not Configured"
            connectionStatusLabelRef.Font = { size = 11, bold = true, color = { r = 0.5, g = 0.5, b = 0.5 } }
        end
    end)
    
    if not success then
        print("RoughCut: Warning - Could not update connection status display")
    end
    
    -- Update last validated timestamp
    if lastValidatedLabelRef and currentConfig.lastValidated then
        pcall(function()
            local dateStr = os.date("%Y-%m-%d %H:%M", os.time(currentConfig.lastValidated))
            lastValidatedLabelRef.Text = "Last validated: " .. dateStr
        end)
    elseif lastValidatedLabelRef then
        pcall(function()
            lastValidatedLabelRef.Text = ""
        end)
    end
end

-- Show validating indicator
function notionSettings.showValidatingIndicator(show)
    if not validatingIndicatorRef then
        return
    end
    
    pcall(function()
        validatingIndicatorRef.Visible = show
    end)
end

-- Handle test connection button click
function notionSettings.handleTestConnection()
    -- Show validating indicator
    notionSettings.showValidatingIndicator(true)
    notionSettings.showError("")
    
    -- Disable test button during validation
    if testConnectionBtnRef then
        pcall(function()
            testConnectionBtnRef.Enabled = false
            testConnectionBtnRef.Text = "Testing..."
        end)
    end
    
    -- Call Python backend via protocol to validate connection
    local success, result = pcall(function()
        local request = {
            method = "validate_notion_connection",
            params = {},
            id = "validate_" .. tostring(os.time())
        }
        
        local requestJson = json.encode(request)
        print("RC_JSONRPC:" .. requestJson)
        
        -- Wait for response (set by protocol handler)
        if _G._notion_validation_response then
            local response = _G._notion_validation_response
            _G._notion_validation_response = nil
            
            if response.error then
                return {
                    valid = false,
                    status = "ERROR",
                    error_message = response.error.message or "Validation failed",
                    suggestion = "Please try again."
                }
            end
            
            return response.result
        end
        
        return nil
    end)
    
    -- Hide validating indicator
    notionSettings.showValidatingIndicator(false)
    
    -- Re-enable test button
    if testConnectionBtnRef then
        pcall(function()
            testConnectionBtnRef.Enabled = true
            testConnectionBtnRef.Text = "Test Connection"
        end)
    end
    
    if success and result then
        -- Update current config with validation result
        currentConfig.connectionStatus = result.status or "ERROR"
        if result.timestamp then
            currentConfig.lastValidated = result.timestamp
        end
        
        -- Update display
        notionSettings.updateConnectionStatusDisplay()
        
        -- Show result dialog
        if result.valid then
            notionSettings.showValidationSuccess(result)
        else
            notionSettings.showValidationError(result)
        end
    else
        -- Validation call failed
        notionSettings.showError("Failed to test connection: " .. tostring(result))
    end
end

-- Show validation success dialog
function notionSettings.showValidationSuccess(result)
    local message = result.suggestion or "Connection is working properly!"
    
    -- Show success in main error/success label
    notionSettings.showError("✓ " .. message, true)
    
    -- Show dialog if UI manager supports it
    if uiManagerRef then
        pcall(function()
            uiManagerRef:ShowMessageDialog(
                "Connection Validated",
                "✓ Successfully connected to Notion!\n\n" .. message,
                "OK"
            )
        end)
    end
end

-- Show validation error dialog
function notionSettings.showValidationError(result)
    local errorMsg = result.error_message or "Connection failed"
    local suggestion = result.suggestion or "Please check your configuration and try again."
    
    -- Show error in main label
    notionSettings.showError("✗ " .. errorMsg)
    
    -- Show dialog if UI manager supports it
    if uiManagerRef then
        pcall(function()
            local fullMessage = errorMsg .. "\n\n" .. suggestion
            uiManagerRef:ShowMessageDialog(
                "Connection Failed",
                fullMessage,
                "OK"
            )
        end)
    end
end

-- Handle test sync button click
function notionSettings.handleTestSync()
    -- Check if connected first
    if currentConfig.connectionStatus ~= "CONNECTED" then
        notionSettings.showError("Please validate connection first before testing sync")
        return
    end
    
    notionSettings.showError("Testing sync...")
    
    -- Call Python backend via protocol to test sync
    local success, result = pcall(function()
        local request = {
            method = "test_notion_sync",
            params = {},
            id = "test_sync_" .. tostring(os.time())
        }
        
        local requestJson = json.encode(request)
        print("RC_JSONRPC:" .. requestJson)
        
        -- Wait for response (set by protocol handler)
        if _G._notion_test_sync_response then
            local response = _G._notion_test_sync_response
            _G._notion_test_sync_response = nil
            
            if response.error then
                return {
                    success = false,
                    message = response.error.message or "Test sync failed"
                }
            end
            
            return response.result
        end
        
        return nil
    end)
    
    if success and result then
        if result.success then
            local message = result.message or "Test sync successful"
            local note = result.note or ""
            notionSettings.showError("✓ " .. message .. " " .. note, true)
            
            if uiManagerRef then
                pcall(function()
                    uiManagerRef:ShowMessageDialog(
                        "Test Sync",
                        message .. "\n\n" .. note,
                        "OK"
                    )
                end)
            end
        else
            notionSettings.showError("✗ " .. (result.message or "Test sync failed"))
        end
    else
        notionSettings.showError("Failed to test sync: " .. tostring(result))
    end
end

-- Handle save button click
function notionSettings.handleSave()
    -- Clear any previous error
    notionSettings.showError("")
    
    -- Get input values
    local token = ""
    local url = ""
    
    if tokenInputRef then
        local success, value = pcall(function()
            return tokenInputRef.Text or ""
        end)
        if success then
            token = value
        end
    end
    
    if urlInputRef then
        local success, value = pcall(function()
            return urlInputRef.Text or ""
        end)
        if success then
            url = value
        end
    end
    
    -- Validate inputs
    if not token or token:match("^%s*$") then
        notionSettings.showError("API token is required")
        return
    end
    
    if not url or url:match("^%s*$") then
        notionSettings.showError("Page URL is required")
        return
    end
    
    -- Basic URL format validation
    if not url:match("^https://.*notion%.so/.*$") then
        notionSettings.showError("Invalid Notion URL format (must be https://*.notion.so/...)")
        return
    end
    
    -- Call Python backend via protocol to save configuration
    local success, result = pcall(function()
        local request = {
            method = "save_notion_config",
            params = {
                api_token = token,
                page_url = url
            },
            id = "save_" .. tostring(os.time())
        }
        
        local requestJson = json.encode(request)
        print("RC_JSONRPC:" .. requestJson)
        
        -- Wait for response (set by protocol handler)
        if _G._notion_save_response then
            local response = _G._notion_save_response
            _G._notion_save_response = nil
            
            if response.error then
                return false, response.error.message or "Unknown error"
            end
            
            return true, response.result and response.result.message or "Configuration saved"
        end
        
        return false, "No response from backend"
    end)
    
    if success and result then
        local ok, message = result
        if ok then
            -- Update local config on success
            currentConfig.configured = true
            currentConfig.pageUrl = url
            currentConfig.enabled = true
            notionSettings.updateStatusDisplay()
            
            -- Clear token input for security
            if tokenInputRef then
                pcall(function()
                    tokenInputRef.Text = ""
                end)
            end
            
            notionSettings.showError("Configuration saved successfully", true)
        else
            notionSettings.showError("Failed to save: " .. tostring(message))
        end
    else
        notionSettings.showError("Failed to communicate with backend: " .. tostring(result))
    end
end

-- Handle clear button click
function notionSettings.handleClear()
    -- Call Python backend via protocol to clear configuration
    local success, result = pcall(function()
        local request = {
            method = "clear_notion_config",
            params = {},
            id = "clear_" .. tostring(os.time())
        }
        
        local requestJson = json.encode(request)
        print("RC_JSONRPC:" .. requestJson)
        
        -- Wait for response (set by protocol handler)
        if _G._notion_clear_response then
            local response = _G._notion_clear_response
            _G._notion_clear_response = nil
            
            if response.error then
                return false, response.error.message or "Unknown error"
            end
            
            return true, response.result and response.result.message or "Configuration cleared"
        end
        
        return false, "No response from backend"
    end)
    
    if success and result then
        local ok, message = result
        if ok then
            -- Reset current config
            currentConfig = {
                configured = false,
                pageUrl = "",
                enabled = false,
                lastUpdated = nil
            }
            
            -- Clear input fields
            if tokenInputRef then
                pcall(function()
                    tokenInputRef.Text = ""
                end)
            end
            
            if urlInputRef then
                pcall(function()
                    urlInputRef.Text = ""
                end)
            end
            
            notionSettings.updateStatusDisplay()
            notionSettings.showError("Configuration cleared", true)
        else
            notionSettings.showError("Failed to clear: " .. tostring(message))
        end
    else
        notionSettings.showError("Failed to communicate with backend: " .. tostring(result))
    end
end

-- Show error or success message
-- @param message Message to display (empty to hide)
-- @param isSuccess If true, show as success (green), else error (red)
function notionSettings.showError(message, isSuccess)
    if not errorLabelRef then
        return
    end
    
    local success = pcall(function()
        if not message or message == "" then
            errorLabelRef.Visible = false
            errorLabelRef.Text = ""
        else
            errorLabelRef.Visible = true
            errorLabelRef.Text = message
            
            if isSuccess then
                errorLabelRef.Font = { size = 10, color = { r = 0, g = 0.7, b = 0 } }
            else
                errorLabelRef.Font = { size = 10, color = { r = 1, g = 0, b = 0 } }
            end
        end
    end)
    
    if not success then
        print("RoughCut: Warning - Could not show error message")
    end
end

-- Get current window reference
function notionSettings.getWindow()
    return windowRef
end

-- Check if Notion is configured (for external use)
function notionSettings.isConfigured()
    return currentConfig.configured
end

return notionSettings
