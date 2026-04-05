-- RoughCut Rough Cut Review Window
-- Displays AI-generated rough cut document for user review
-- Story 5.8: Review AI-Generated Rough Cut Document
-- Compatible with DaVinci Resolve's Lua scripting environment
-- Version: 1.0.0

local roughCutReview = {}

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
    id = "RoughCutReview",
    title = "RoughCut - Review AI-Generated Rough Cut",
    width = 900,
    height = 700
}

-- State tracking
local parentWindowRef = nil
local currentWindowRef = nil
local sessionId = nil
local roughCutDocument = nil
local isLoading = false
local currentSectionIndex = 1

-- Asset type icons for display
local ASSET_ICONS = {
    music = "♫",
    sfx = "•",
    vfx = "▼"
}

-- Confidence level indicators
local CONFIDENCE_INDICATORS = {
    high = "✓ HIGH",
    medium = "~ MEDIUM",
    low = "✗ LOW"
}

-- Create the rough cut review window
-- @param uiManager Resolve UI Manager instance
-- @param parentWindow Reference to parent window for navigation back
-- @param roughCutSessionId Session ID from rough cut generation
-- @return window table or nil on error
function roughCutReview.create(uiManager, parentWindow, roughCutSessionId)
    if not uiManager then
        logger.error("UI Manager required for rough cut review window")
        return nil
    end
    
    parentWindowRef = parentWindow
    sessionId = roughCutSessionId
    
    -- Create window
    local ok_create, window = pcall(function()
        return uiManager:Add({
            type = "Window",
            id = WINDOW_CONFIG.id,
            title = WINDOW_CONFIG.title,
            width = WINDOW_CONFIG.width,
            height = WINDOW_CONFIG.height,
            spacing = 10,
            padding = 15
        })
    end)
    
    if not ok_create or not window then
        logger.error("Failed to create rough cut review window: " .. tostring(window))
        return nil
    end
    
    currentWindowRef = window
    currentSectionIndex = 1
    
    -- Load and display the rough cut document
    _loadDocumentAsync()
    
    return window
end

-- Load rough cut document asynchronously
function _loadDocumentAsync()
    isLoading = true
    _showLoadingState()
    
    -- Use timer for async if available
    local ok_timer = pcall(function()
        if type(SetTimer) == "function" then
            SetTimer(100, function()
                _loadDocumentInternal()
                return false
            end)
        else
            _loadDocumentInternal()
        end
    end)
    
    if not ok_timer then
        _loadDocumentInternal()
    end
end

-- Internal function to load document
function _loadDocumentInternal()
    if not sessionId then
        logger.error("No session ID available for document loading")
        _showError("No session available. Please generate a rough cut first.")
        isLoading = false
        return
    end
    
    local result = protocol.request({
        method = "get_rough_cut_document",
        params = {
            session_id = sessionId,
            format = "detailed"
        }
    })
    
    isLoading = false
    
    if result.error then
        logger.error("Failed to load document: " .. tostring(result.error.message))
        _showError("Failed to load rough cut: " .. tostring(result.error.message))
        return
    end
    
    if result.result and result.result.rough_cut_document then
        roughCutDocument = result.result.rough_cut_document
        logger.info("Loaded rough cut document: " .. tostring(roughCutDocument.title))
        _renderDocument()
    else
        logger.error("No document data in response")
        _showError("No rough cut document available")
    end
end

-- Show loading state in window
function _showLoadingState(message)
    if not currentWindowRef then return end
    
    -- Use custom message or default
    local loadingMessage = message or "Loading AI-generated rough cut document..."
    local subMessage = "Please wait while we retrieve the document."
    
    if message then
        subMessage = "Processing..."
    end
    
    -- Clear existing content
    _clearWindow()
    
    -- Add loading indicator
    local ok = pcall(function()
        currentWindowRef:Add({
            type = "Label",
            text = loadingMessage,
            alignment = { AlignHCenter = true, AlignVCenter = true }
        })
        
        currentWindowRef:Add({
            type = "Label",
            text = subMessage,
            alignment = { AlignHCenter = true }
        })
    end)
    
    if not ok then
        logger.error("Failed to show loading state")
    end
end

-- Show error message
function _showError(message)
    if not currentWindowRef then return end
    
    _clearWindow()
    
    local ok = pcall(function()
        currentWindowRef:Add({
            type = "Label",
            text = "Error",
            styleSheet = "font-weight: bold; color: red; font-size: 16px;"
        })
        
        currentWindowRef:Add({
            type = "Label",
            text = message or "An unknown error occurred",
            wordWrap = true
        })
        
        currentWindowRef:Add({
            type = "Button",
            text = "Go Back",
            clicked = function()
                _navigateBack()
            end
        })
    end)
    
    if not ok then
        print("[ERROR] Failed to show error: " .. tostring(message))
    end
end

-- Clear window content
function _clearWindow()
    if not currentWindowRef then return end
    
    pcall(function()
        -- Remove all children by iterating
        while currentWindowRef:GetItems() and #currentWindowRef:GetItems() > 0 do
            local items = currentWindowRef:GetItems()
            if items and #items > 0 then
                currentWindowRef:RemoveItem(items[1])
            else
                break
            end
        end
    end)
end

-- Render the rough cut document
function _renderDocument()
    if not currentWindowRef or not roughCutDocument then return end
    
    _clearWindow()
    
    local ok = pcall(function()
        -- Header section
        _renderHeader()
        
        -- Summary section
        _renderSummary()
        
        -- Navigation for sections
        _renderSectionNavigation()
        
        -- Current section details
        _renderCurrentSection()
        
        -- Action buttons
        _renderActionButtons()
    end)
    
    if not ok then
        logger.error("Failed to render document")
        _showError("Failed to display rough cut document")
    end
end

-- Render document header
function _renderHeader()
    local doc = roughCutDocument
    
    currentWindowRef:Add({
        type = "Label",
        text = doc.title or "Untitled Rough Cut",
        styleSheet = "font-weight: bold; font-size: 18px;"
    })
    
    currentWindowRef:Add({
        type = "Label",
        text = "Source: " .. tostring(doc.source_clip) .. " | Format: " .. tostring(doc.format_template),
        styleSheet = "color: gray;"
    })
    
    -- Duration badge
    local durationStr = _formatDuration(doc.total_duration)
    currentWindowRef:Add({
        type = "Label",
        text = "Duration: " .. durationStr,
        styleSheet = "font-weight: bold; color: #0066cc;"
    })
    
    -- Separator
    currentWindowRef:Add({
        type = "Label",
        text = string.rep("—", 80),
        styleSheet = "color: lightgray;"
    })
end

-- Render document summary
function _renderSummary()
    local doc = roughCutDocument
    local summary = doc.summary or {}
    
    currentWindowRef:Add({
        type = "Label",
        text = "Overview:",
        styleSheet = "font-weight: bold; font-size: 14px;"
    })
    
    local summaryText = string.format(
        "Sections: %d | Segments: %d | Music: %d | SFX: %d | VFX: %d",
        summary.section_count or 0,
        summary.total_transcript_segments or 0,
        summary.total_music_suggestions or 0,
        summary.total_sfx_suggestions or 0,
        summary.total_vfx_suggestions or 0
    )
    
    currentWindowRef:Add({
        type = "Label",
        text = summaryText
    })
    
    -- Assembly confidence if available
    local metadata = doc.assembly_metadata or {}
    if metadata.pacing_consistency_score then
        local score = metadata.pacing_consistency_score
        local confidenceText = string.format("Assembly Confidence: %.0f%%", score * 100)
        local color = score >= 0.8 and "green" or (score >= 0.6 and "orange" or "red")
        
        currentWindowRef:Add({
            type = "Label",
            text = confidenceText,
            styleSheet = "color: " .. color .. "; font-weight: bold;"
        })
    end
    
    -- Spacing
    currentWindowRef:Add({ type = "Label", text = "" })
end

-- Render section navigation
function _renderSectionNavigation()
    local sections = roughCutDocument.sections or {}
    local totalSections = #sections
    
    if totalSections == 0 then return end
    
    currentWindowRef:Add({
        type = "Label",
        text = "Sections:",
        styleSheet = "font-weight: bold;"
    })
    
    -- Create horizontal layout for section buttons
    local sectionRow = currentWindowRef:Add({
        type = "HorizontalLayout",
        spacing = 5
    })
    
    for i, section in ipairs(sections) do
        local isActive = (i == currentSectionIndex)
        local sectionName = section.name or ("Section " .. i)
        
        -- Build asset indicators
        local indicators = {}
        if section.music then table.insert(indicators, ASSET_ICONS.music) end
        if section.sfx and #section.sfx > 0 then
            table.insert(indicators, ASSET_ICONS.sfx .. #section.sfx)
        end
        if section.vfx and #section.vfx > 0 then
            table.insert(indicators, ASSET_ICONS.vfx .. #section.vfx)
        end
        
        local btnText = sectionName
        if #indicators > 0 then
            btnText = btnText .. " [" .. table.concat(indicators, " ") .. "]"
        end
        
        local btn = sectionRow:Add({
            type = "Button",
            text = btnText,
            styleSheet = isActive and "background-color: #0066cc; color: white;" or ""
        })
        
        -- Capture index in closure
        local sectionIdx = i
        btn.clicked = function()
            currentSectionIndex = sectionIdx
            _renderDocument()
        end
    end
    
    -- Spacing
    currentWindowRef:Add({ type = "Label", text = "" })
end

-- Render current section details
function _renderCurrentSection()
    local sections = roughCutDocument.sections or {}
    
    if #sections == 0 then
        currentWindowRef:Add({
            type = "Label",
            text = "No sections available",
            styleSheet = "color: red;"
        })
        return
    end
    
    local section = sections[currentSectionIndex]
    if not section then return end
    
    -- Section header
    local sectionTitle = string.format(
        "Section %d: %s (%s - %s)",
        currentSectionIndex,
        section.name or "Unnamed",
        _formatDuration(section.start_time or 0),
        _formatDuration(section.end_time or 0)
    )
    
    currentWindowRef:Add({
        type = "Label",
        text = sectionTitle,
        styleSheet = "font-weight: bold; font-size: 14px; background-color: #f0f0f0; padding: 5px;"
    })
    
    -- Transcript segments
    _renderTranscriptSegments(section)
    
    -- Music suggestion
    if section.music then
        _renderMusicSuggestion(section.music)
    end
    
    -- SFX suggestions
    if section.sfx and #section.sfx > 0 then
        _renderSFXSuggestions(section.sfx)
    end
    
    -- VFX suggestions
    if section.vfx and #section.vfx > 0 then
        _renderVFXSuggestions(section.vfx)
    end
end

-- Render transcript segments
function _renderTranscriptSegments(section)
    local segments = section.transcript_segments or {}
    
    if #segments == 0 then return end
    
    currentWindowRef:Add({
        type = "Label",
        text = "Transcript Segments:",
        styleSheet = "font-weight: bold; margin-top: 10px;"
    })
    
    for i, seg in ipairs(segments) do
        local timeStr = _formatDuration(seg.start_time or 0)
        local speakerStr = seg.speaker and ("<" .. seg.speaker .. "> ") or ""
        local text = seg.text or ""
        
        -- Truncate long text
        if #text > 100 then
            text = text:sub(1, 97) .. "..."
        end
        
        local lineText = string.format("[%s] %s%s", timeStr, speakerStr, text)
        
        currentWindowRef:Add({
            type = "Label",
            text = lineText,
            wordWrap = true,
            styleSheet = "margin-left: 10px;"
        })
    end
end

-- Render music suggestion
function _renderMusicSuggestion(music)
    currentWindowRef:Add({
        type = "Label",
        text = "Music Suggestion:",
        styleSheet = "font-weight: bold; margin-top: 10px;"
    })
    
    local confidenceLevel = music.confidence and _getConfidenceLevel(music.confidence) or "N/A"
    
    local details = {
        "Track: " .. tostring(music.name),
        "Source: " .. tostring(music.source_folder),
        "Position: " .. _formatDuration(music.position or 0),
        "Confidence: " .. confidenceLevel .. " (" .. math.floor((music.confidence or 0) * 100) .. "%)",
        "Reasoning: " .. tostring(music.reasoning)
    }
    
    if music.fade_in then
        table.insert(details, "Fade In: " .. music.fade_in .. "s")
    end
    
    if music.fade_out then
        table.insert(details, "Fade Out: " .. music.fade_out .. "s")
    end
    
    if music.volume_adjustment then
        table.insert(details, "Volume: " .. music.volume_adjustment .. " dB")
    end
    
    for _, detail in ipairs(details) do
        currentWindowRef:Add({
            type = "Label",
            text = "  " .. ASSET_ICONS.music .. " " .. detail,
            styleSheet = "margin-left: 10px;"
        })
    end
end

-- Render SFX suggestions
function _renderSFXSuggestions(sfxList)
    currentWindowRef:Add({
        type = "Label",
        text = "Sound Effects:",
        styleSheet = "font-weight: bold; margin-top: 10px;"
    })
    
    for i, sfx in ipairs(sfxList) do
        local confidenceLevel = sfx.confidence and _getConfidenceLevel(sfx.confidence) or "N/A"
        
        local lineText = string.format(
            "%s %s at %s (Track %d) - %s",
            ASSET_ICONS.sfx,
            tostring(sfx.name),
            _formatDuration(sfx.position or 0),
            sfx.track_number or 1,
            confidenceLevel
        )
        
        currentWindowRef:Add({
            type = "Label",
            text = "  " .. lineText,
            styleSheet = "margin-left: 10px;"
        })
        
        if sfx.intended_moment and sfx.intended_moment ~= "" then
            currentWindowRef:Add({
                type = "Label",
                text = "    Moment: " .. sfx.intended_moment,
                styleSheet = "margin-left: 15px; color: gray; font-style: italic;"
            })
        end
    end
end

-- Render VFX suggestions
function _renderVFXSuggestions(vfxList)
    currentWindowRef:Add({
        type = "Label",
        text = "VFX/Templates:",
        styleSheet = "font-weight: bold; margin-top: 10px;"
    })
    
    for i, vfx in ipairs(vfxList) do
        local confidenceLevel = vfx.confidence and _getConfidenceLevel(vfx.confidence) or "N/A"
        local templateName = vfx.template_name or vfx.name or "Unknown"
        
        local lineText = string.format(
            "%s %s at %s - %s",
            ASSET_ICONS.vfx,
            templateName,
            _formatDuration(vfx.position or 0),
            confidenceLevel
        )
        
        currentWindowRef:Add({
            type = "Label",
            text = "  " .. lineText,
            styleSheet = "margin-left: 10px;"
        })
        
        if vfx.duration then
            currentWindowRef:Add({
                type = "Label",
                text = "    Duration: " .. _formatDuration(vfx.duration),
                styleSheet = "margin-left: 15px; color: gray;"
            })
        end
        
        -- Display configurable parameters if present
        if vfx.configurable_params and type(vfx.configurable_params) == "table" then
            local paramsText = {}
            for key, value in pairs(vfx.configurable_params) do
                table.insert(paramsText, key .. "=" .. tostring(value))
            end
            
            if #paramsText > 0 then
                currentWindowRef:Add({
                    type = "Label",
                    text = "    Settings: " .. table.concat(paramsText, ", "),
                    styleSheet = "margin-left: 15px; color: gray; font-style: italic;"
                })
            end
        end
    end
end

-- Render action buttons
function _renderActionButtons()
    -- Separator
    currentWindowRef:Add({
        type = "Label",
        text = string.rep("—", 80),
        styleSheet = "color: lightgray; margin-top: 20px;"
    })
    
    -- Button row
    local buttonRow = currentWindowRef:Add({
        type = "HorizontalLayout",
        spacing = 10
    })
    
    -- Create Timeline button
    local createBtn = buttonRow:Add({
        type = "Button",
        text = "Create Timeline",
        styleSheet = "background-color: #28a745; color: white; font-weight: bold; padding: 10px 20px;"
    })
    
    createBtn.clicked = function()
        _showCreateTimelineConfirmation()
    end
    
    -- Back button
    local backBtn = buttonRow:Add({
        type = "Button",
        text = "Go Back"
    })
    
    backBtn.clicked = function()
        _navigateBack()
    end
end

-- Show create timeline confirmation dialog
function _showCreateTimelineConfirmation()
    if not currentWindowRef then return end
    
    -- Use simple dialog via protocol call directly
    -- In a full implementation, this would show a custom dialog
    local ok_confirm = pcall(function()
        -- Simple confirm using window message or direct call
        _createTimelineAsync()
    end)
    
    if not ok_confirm then
        logger.error("Failed to show confirmation")
        _createTimelineAsync()
    end
end

-- Create timeline asynchronously
function _createTimelineAsync()
    if not sessionId then
        _showError("No session available for timeline creation")
        return
    end
    
    isLoading = true
    _showLoadingState("Creating timeline structure...")
    
    local ok_timer = pcall(function()
        if type(SetTimer) == "function" then
            SetTimer(100, function()
                _createTimelineInternal()
                return false
            end)
        else
            _createTimelineInternal()
        end
    end)
    
    if not ok_timer then
        _createTimelineInternal()
    end
end

-- Internal function to create timeline
function _createTimelineInternal()
    local result = protocol.request({
        method = "create_timeline_from_document",
        params = {
            session_id = sessionId,
            timeline_name = _generateTimelineName()
        }
    })
    
    isLoading = false
    
    if result.error then
        logger.error("Failed to create timeline: " .. tostring(result.error.message))
        _showError("Failed to create timeline: " .. tostring(result.error.message))
        return
    end
    
    if result.result then
        logger.info("Timeline created successfully")
        
        -- Now import suggested media
        local timelineId = result.result.timeline_id
        if timelineId then
            _importSuggestedMediaAsync(timelineId)
        else
        _showTimelineCreatedSuccess(result.result)
    else
        _showError("Timeline creation returned no result")
    end
end

-- Import suggested media asynchronously
function _importSuggestedMediaAsync(timelineId)
    isLoading = true
    _showLoadingState("Importing suggested media...")
    
    local ok_timer = pcall(function()
        if type(SetTimer) == "function" then
            SetTimer(100, function()
                _importSuggestedMediaInternal(timelineId)
                return false
            end)
        else
            _importSuggestedMediaInternal(timelineId)
        end
    end)
    
    if not ok_timer then
        _importSuggestedMediaInternal(timelineId)
    end
end

-- Internal function to import suggested media
function _importSuggestedMediaInternal(timelineId)
    -- Build suggested media list from rough cut document
    local suggestedMedia = {}
    
    if roughCutDocument then
        -- Add music suggestions
        if roughCutDocument.music_suggestions and type(roughCutDocument.music_suggestions) == "table" then
            for _, music in ipairs(roughCutDocument.music_suggestions) do
                if music.file_path then
                    table.insert(suggestedMedia, {
                        file_path = music.file_path,
                        media_type = "music",
                        usage = music.usage or "background"
                    })
                end
            end
        end
        
        -- Add SFX suggestions
        if roughCutDocument.sfx_suggestions and type(roughCutDocument.sfx_suggestions) == "table" then
            for _, sfx in ipairs(roughCutDocument.sfx_suggestions) do
                if sfx.file_path then
                    table.insert(suggestedMedia, {
                        file_path = sfx.file_path,
                        media_type = "sfx",
                        usage = sfx.usage or "effect"
                    })
                end
            end
        end
        
        -- Add VFX suggestions
        if roughCutDocument.vfx_suggestions and type(roughCutDocument.vfx_suggestions) == "table" then
            for _, vfx in ipairs(roughCutDocument.vfx_suggestions) do
                if vfx.file_path then
                    table.insert(suggestedMedia, {
                        file_path = vfx.file_path,
                        media_type = "vfx",
                        usage = vfx.usage or "template"
                    })
                end
            end
        end
    end
    
    -- Call import method
    local result = protocol.request({
        method = "import_suggested_media",
        params = {
            timeline_id = timelineId,
            suggested_media = suggestedMedia
        }
    })
    
    isLoading = false
    
    -- Build result with import info
    local finalResult = {
        timeline_id = timelineId,
        timeline_name = _generateTimelineName()
    }
    
    if result.result then
        finalResult.imported_count = result.result.imported_count or 0
        finalResult.skipped_count = result.result.skipped_count or 0
        
        if result.result.warning then
            logger.warning("Import warnings: " .. tostring(result.result.warning))
        end
        
        logger.info(string.format(
            "Media import complete: %d imported, %d skipped",
            finalResult.imported_count,
            finalResult.skipped_count
        ))
    else
        logger.warning("Media import returned no result")
        finalResult.imported_count = 0
        finalResult.skipped_count = 0
    end
    
    if result.error then
        logger.error("Failed to import media: " .. tostring(result.error.message))
        -- Still show success for timeline creation, but note the import issue
        finalResult.import_warning = result.error.message
    end
    
    _showTimelineCreatedSuccess(finalResult)
end
end

-- Generate timeline name
function _generateTimelineName()
    local doc = roughCutDocument
    if not doc then return "RoughCut_Untitled" end
    
    local sourceName = doc.source_clip or "Untitled"
    -- Remove extension
    sourceName = sourceName:gsub("%..*$", "")
    -- Remove special characters
    sourceName = sourceName:gsub("[^%w_-]", "_")
    
    local formatName = doc.format_template or "Default"
    formatName = formatName:gsub("[^%w_-]", "_")
    
    local timestamp = os.date("%Y-%m-%d_%H-%M")
    
    return string.format("RoughCut_%s_%s_%s", sourceName, formatName, timestamp)
end

-- Show timeline created success
function _showTimelineCreatedSuccess(result)
    if not currentWindowRef then return end
    
    _clearWindow()
    
    local ok = pcall(function()
        currentWindowRef:Add({
            type = "Label",
            text = "✓ Timeline Created Successfully!",
            styleSheet = "font-weight: bold; font-size: 18px; color: green;"
        })
        
        if result.timeline_name then
            currentWindowRef:Add({
                type = "Label",
                text = "Timeline: " .. result.timeline_name
            })
        end
        
        -- Show media import info if available
        if result.imported_count ~= nil then
            currentWindowRef:Add({
                type = "Label",
                text = string.format("Media imported: %d file(s)", result.imported_count),
                styleSheet = "margin-top: 10px; color: #28a745;"
            })
            
            if result.skipped_count and result.skipped_count > 0 then
                currentWindowRef:Add({
                    type = "Label",
                    text = string.format("Note: %d file(s) skipped (not found)", result.skipped_count),
                    styleSheet = "color: orange;"
                })
            end
        end
        
        -- Show import warning if present
        if result.import_warning then
            currentWindowRef:Add({
                type = "Label",
                text = "Import warning: " .. tostring(result.import_warning),
                styleSheet = "color: orange; margin-top: 5px;"
            })
        end
        
        currentWindowRef:Add({
            type = "Label",
            text = "The rough cut has been created in DaVinci Resolve with suggested media imported. You can now refine and adjust the edit.",
            wordWrap = true,
            styleSheet = "margin-top: 10px;"
        })
        
        currentWindowRef:Add({
            type = "Button",
            text = "Close",
            clicked = function()
                _closeWindow()
            end
        })
    end)
    
    if not ok then
        logger.info("Timeline created: " .. tostring(result.timeline_name))
        _closeWindow()
    end
end

-- Navigate back to parent window
function _navigateBack()
    _closeWindow()
    
    if parentWindowRef then
        pcall(function()
            parentWindowRef:Show()
        end)
    end
end

-- Close current window
function _closeWindow()
    if currentWindowRef then
        pcall(function()
            currentWindowRef:Close()
        end)
        currentWindowRef = nil
    end
end

-- Format duration (seconds to MM:SS)
function _formatDuration(seconds)
    if not seconds then return "0:00" end
    
    local mins = math.floor(seconds / 60)
    local secs = math.floor(seconds % 60)
    return string.format("%d:%02d", mins, secs)
end

-- Get confidence level text
function _getConfidenceLevel(confidence)
    if not confidence then return "N/A" end
    
    if confidence >= 0.80 then
        return CONFIDENCE_INDICATORS.high
    elseif confidence >= 0.60 then
        return CONFIDENCE_INDICATORS.medium
    else
        return CONFIDENCE_INDICATORS.low
    end
end

-- Public API
return roughCutReview
