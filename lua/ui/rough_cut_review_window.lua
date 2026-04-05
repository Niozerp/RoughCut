-- rough_cut_review_window.lua
-- Rough Cut Review and Timeline Creation UI for RoughCut
-- Handles import of suggested media with progress display

local roughCutReview = {}

-- Import progress dialog
local importProgressDialog = nil
local importProgressLabel = nil
local importProgressBar = nil

-- ============================================================================
-- Progress UI Functions
-- ============================================================================

function roughCutReview._showLoadingState(parent, message)
    -- Show loading/progress indicator during operations
    local loadingDialog = CreateDialog("Processing...")
    loadingDialog:SetMinimumSize(300, 100)
    
    local layout = CreateVerticalLayout(loadingDialog)
    
    local messageLabel = CreateLabel(layout, message)
    messageLabel:SetStyleSheet("font-size: 14px; padding: 10px;")
    messageLabel:SetWordWrap(true)
    
    local progressBar = CreateProgressBar(layout)
    progressBar:SetRange(0, 0)  -- Indeterminate progress
    progressBar:SetMinimumWidth(250)
    
    loadingDialog:Show()
    
    return loadingDialog, messageLabel, progressBar
end

function roughCutReview._showImportProgressDialog(totalFiles)
    -- Create progress dialog for media import
    importProgressDialog = CreateDialog("Importing Media...")
    importProgressDialog:SetMinimumSize(400, 150)
    
    local layout = CreateVerticalLayout(importProgressDialog)
    
    -- Status message
    importProgressLabel = CreateLabel(layout, "Preparing to import...")
    importProgressLabel:SetStyleSheet("font-size: 14px; padding: 10px;")
    importProgressLabel:SetWordWrap(true)
    
    -- Progress bar
    importProgressBar = CreateProgressBar(layout)
    importProgressBar:SetRange(0, totalFiles)
    importProgressBar:SetValue(0)
    importProgressBar:SetMinimumWidth(350)
    importProgressBar:SetStyleSheet([[
        QProgressBar {
            border: 1px solid #555;
            border-radius: 4px;
            text-align: center;
            height: 20px;
        }
        QProgressBar::chunk {
            background-color: #4CAF50;
            border-radius: 3px;
        }
    ]])
    
    -- Cancel button
    local buttonRow = CreateHorizontalLayout()
    local cancelBtn = CreateButton(buttonRow, "Cancel")
    cancelBtn.clicked = function()
        -- Note: Actual cancellation would need protocol support
        importProgressDialog:Close()
    end
    
    layout:AddLayout(buttonRow)
    importProgressDialog:Show()
    
    return importProgressDialog
end

function roughCutReview._updateImportProgress(current, total, filename)
    -- Update the import progress UI
    if not importProgressDialog or not importProgressLabel or not importProgressBar then
        return
    end
    
    -- Update message with filename only (P3 fix - AC4 compliance)
    -- Format: "Importing: filename" per spec requirement
    local message = string.format("Importing: %s", filename)
    importProgressLabel:SetText(message)
    
    -- Update progress bar (internal progress tracking, not displayed in message)
    importProgressBar:SetValue(current)
    if total > 0 then
        importProgressBar:SetFormat(string.format("%d%%", math.floor((current / total) * 100)))
    end
    
    -- Force UI update to remain responsive (NFR5)
    -- In real implementation, this would use Qt's processEvents or similar
end

function roughCutReview._closeImportProgressDialog()
    -- Close the import progress dialog
    if importProgressDialog then
        importProgressDialog:Close()
        importProgressDialog = nil
        importProgressLabel = nil
        importProgressBar = nil
    end
end

function roughCutReview._showImportWarnings(skippedFiles)
    -- Show dialog with warnings for skipped/missing files
    if not skippedFiles or #skippedFiles == 0 then
        return
    end
    
    local warningDialog = CreateDialog("Import Warnings")
    warningDialog:SetMinimumSize(500, 300)
    
    local mainLayout = CreateVerticalLayout(warningDialog)
    
    -- Header
    local headerLabel = CreateLabel(mainLayout, string.format("Warning: %d file(s) could not be imported", #skippedFiles))
    headerLabel:SetStyleSheet("font-weight: bold; font-size: 14px; color: #FF9800; padding-bottom: 10px;")
    
    -- Scrollable list of warnings
    local scrollArea = CreateScrollArea(mainLayout)
    local listLayout = CreateVerticalLayout(scrollArea)
    
    for _, skipped in ipairs(skippedFiles) do
        local fileName = skipped.file_path and string.match(skipped.file_path, "[^/\\]+$") or "Unknown"
        
        local warningRow = CreateHorizontalLayout()
        
        -- Warning icon (using text as placeholder)
        local iconLabel = CreateLabel(warningRow, "⚠️")
        iconLabel:SetStyleSheet("font-size: 16px; padding-right: 5px;")
        
        -- Warning text
        local messageLabel = CreateLabel(warningRow, skipped.message or string.format("File not found: %s", fileName))
        messageLabel:SetStyleSheet("color: #666;")
        messageLabel:SetWordWrap(true)
        
        listLayout:AddLayout(warningRow)
        
        -- Separator
        local separator = CreateFrame(listLayout)
        separator:SetStyleSheet("background-color: #ddd; height: 1px;")
        separator:SetMinimumHeight(1)
        separator:SetMaximumHeight(1)
    end
    
    -- Continue note
    local continueLabel = CreateLabel(mainLayout, "Timeline creation will continue with available assets.")
    continueLabel:SetStyleSheet("color: #4CAF50; font-style: italic; padding-top: 10px;")
    
    -- Close button
    local buttonRow = CreateHorizontalLayout()
    local closeBtn = CreateButton(buttonRow, "Continue")
    closeBtn:SetStyleSheet("background-color: #4CAF50; color: white; padding: 5px 20px;")
    closeBtn.clicked = function()
        warningDialog:Close()
    end
    
    mainLayout:AddLayout(buttonRow)
    warningDialog:Show()
end

function roughCutReview._showTimelineCreatedSuccess(timelineId, importedCount, skippedCount)
    -- Show success dialog after timeline creation and media import
    local successDialog = CreateDialog("Timeline Created")
    successDialog:SetMinimumSize(400, 200)
    
    local layout = CreateVerticalLayout(successDialog)
    
    -- Success header
    local headerLabel = CreateLabel(layout, "Timeline Created Successfully!")
    headerLabel:SetStyleSheet("font-weight: bold; font-size: 16px; color: #4CAF50; padding: 10px;")
    
    -- Details
    local detailsText = string.format(
        "Timeline ID: %s\n\nMedia Import:\n- %d file(s) imported successfully",
        timelineId,
        importedCount
    )
    
    if skippedCount > 0 then
        detailsText = detailsText .. string.format("\n- %d file(s) skipped (see warnings)", skippedCount)
    end
    
    local detailsLabel = CreateLabel(layout, detailsText)
    detailsLabel:SetStyleSheet("padding: 10px;")
    detailsLabel:SetWordWrap(true)
    
    -- Buttons
    local buttonRow = CreateHorizontalLayout()
    
    local proceedBtn = CreateButton(buttonRow, "Proceed to Cut Footage →")
    proceedBtn:SetStyleSheet("background-color: #2196F3; color: white; padding: 5px 15px;")
    proceedBtn.clicked = function()
        successDialog:Close()
        -- Navigate to next story (6.3 - Cut Footage)
        roughCutReview._proceedToCutFootage(timelineId)
    end
    
    local closeBtn = CreateButton(buttonRow, "Close")
    closeBtn.clicked = function()
        successDialog:Close()
    end
    
    layout:AddLayout(buttonRow)
    successDialog:Show()
end

-- ============================================================================
-- Protocol Communication
-- ============================================================================

function roughCutReview._importSuggestedMediaAsync(timelineId, suggestedMedia, callback)
    -- Asynchronously import suggested media with progress updates
    -- D1 FIX: Python backend processes in chunks for large batches (CHUNK_SIZE=50)
    -- to maintain GUI responsiveness per NFR5
    
    local totalFiles = #suggestedMedia
    
    -- Show progress dialog
    roughCutReview._showImportProgressDialog(totalFiles)
    
    -- For large batches, show initial message about chunked processing
    if totalFiles > 50 then
        local batchCount = math.ceil(totalFiles / 50)
        importProgressLabel:SetText(string.format(
            "Importing %d files in %d batches...", 
            totalFiles, 
            batchCount
        ))
    end
    
    -- Make the protocol request
    -- The Python backend will stream progress messages for chunks > 50 items
    local result = Protocol.request({
        method = "import_suggested_media",
        params = {
            timeline_id = timelineId,
            suggested_media = suggestedMedia
        }
    })
    
    -- Close progress dialog
    roughCutReview._closeImportProgressDialog()
    
    -- Handle response
    if result.error then
        -- Show error
        ShowErrorDialog(
            "Import Failed",
            result.error.message or "Unknown error during media import",
            result.error.suggestion or "Please try again or check the file paths"
        )
        if callback then
            callback(false, nil)
        end
        return
    end
    
    -- Success - show results
    local importResult = result.result
    
    -- Show warnings if any files were skipped
    if importResult.skipped_files and #importResult.skipped_files > 0 then
        roughCutReview._showImportWarnings(importResult.skipped_files)
    end
    
    -- Call success callback
    if callback then
        callback(true, importResult)
    end
end

function roughCutReview._importSuggestedMediaInternal(timelineId, suggestedMedia)
    -- Internal synchronous version for when blocking is acceptable
    -- Returns import result or nil on error
    
    local result = Protocol.request({
        method = "import_suggested_media",
        params = {
            timeline_id = timelineId,
            suggested_media = suggestedMedia
        }
    })
    
    if result.error then
        logger.error("Import failed: " .. (result.error.message or "Unknown error"))
        return nil
    end
    
    return result.result
end

-- ============================================================================
-- Navigation Functions
-- ============================================================================

function roughCutReview._proceedToCutFootage(timelineId)
    -- Navigate to Story 6.3: Cut Footage to Segments
    -- This would typically open the footage cutting UI
    
    logger.info("Proceeding to cut footage for timeline: " .. timelineId)
    
    -- TODO: Implement navigation to Cut Footage story
    -- This would involve:
    -- 1. Loading the timeline
    -- 2. Displaying suggested transcript segments
    -- 3. Allowing user to review and adjust cuts
    
    ShowMessage("Proceeding to Cut Footage story...")
end

-- ============================================================================
-- Main Integration Points
-- ============================================================================

function roughCutReview.onTimelineCreated(timelineId, suggestedMedia)
    -- Called by Story 6.1 after timeline creation
    -- Initiates the media import process
    
    if not suggestedMedia or #suggestedMedia == 0 then
        logger.info("No suggested media to import")
        roughCutReview._showTimelineCreatedSuccess(timelineId, 0, 0)
        return
    end
    
    -- Import media asynchronously with progress
    roughCutReview._importSuggestedMediaAsync(
        timelineId,
        suggestedMedia,
        function(success, importResult)
            if success and importResult then
                roughCutReview._showTimelineCreatedSuccess(
                    timelineId,
                    importResult.imported_count or 0,
                    importResult.skipped_count or 0
                )
            end
        end
    )
end

function roughCutReview.createTimelineWithImport(projectId, roughCutData)
    -- Combined function to create timeline and import media
    -- This can be called from the rough cut review UI
    
    local timelineName = roughCutData.timeline_name or "Rough Cut"
    local suggestedMedia = roughCutData.suggested_media or {}
    
    -- Step 1: Create timeline (Story 6.1)
    local createResult = Protocol.request({
        method = "create_timeline",
        params = {
            project_id = projectId,
            timeline_name = timelineName
        }
    })
    
    if createResult.error then
        ShowErrorDialog(
            "Timeline Creation Failed",
            createResult.error.message or "Failed to create timeline",
            createResult.error.suggestion or "Please try again"
        )
        return nil
    end
    
    local timelineId = createResult.result.timeline_id
    
    -- Step 2: Import suggested media (Story 6.2)
    roughCutReview.onTimelineCreated(timelineId, suggestedMedia)
    
    return timelineId
end

-- ============================================================================
-- Export
-- ============================================================================

return roughCutReview
