--[[
    Transcript Viewer UI
    
    Provides a dialog for viewing Resolve's native transcription for a selected clip.
    This module displays the transcript text with speaker labels and provides
    navigation to proceed to transcription quality review.
    
    Usage:
        local TranscriptViewer = require("transcript_viewer")
        TranscriptViewer.show(clipData)
--]]

local TranscriptViewer = {}

-- UI state
TranscriptViewer.currentClip = nil
TranscriptViewer.transcriptData = nil
TranscriptViewer.isLoading = false

--[[
    Show the transcript viewer dialog.
    
    Args:
        clipData: Table containing clip information from Media Browser
            {
                id = "resolve_clip_001",
                name = "interview_take1",
                path = "/path/to/clip.mov",
                duration = 2280.5
            }
--]]
function TranscriptViewer.show(clipData)
    -- Reset state
    TranscriptViewer.currentClip = clipData
    TranscriptViewer.transcriptData = nil
    TranscriptViewer.isLoading = true
    
    -- Check if Resolve is available
    local ResolveAPI = require("resolve_api")
    local available, err = ResolveAPI.isAvailable()
    
    if not available then
        local msg = ResolveAPI.getErrorMessage(err)
        TranscriptViewer.showErrorDialog(msg)
        return
    end
    
    -- Create and show the dialog
    local dialog = TranscriptViewer.createDialog()
    if dialog then
        TranscriptViewer.currentDialog = dialog
        
        -- Update header with clip name
        TranscriptViewer.updateHeader(clipData.name)
        
        -- Show loading state
        TranscriptViewer.showLoadingState()
        
        -- Request transcription from Python backend
        TranscriptViewer.retrieveTranscription(clipData)
    end
end

--[[
    Create the transcript viewer dialog structure.
    
    Returns:
        dialog: Table describing the dialog structure (Resolve UI compatible)
--]]
function TranscriptViewer.createDialog()
    local dialog = {
        title = "Transcript - RoughCut",
        width = 900,
        height = 700,
        
        -- Window style - modal dialog
        modal = true,
        
        -- UI Components
        components = {
            -- Header with clip name
            {
                type = "Label",
                id = "headerLabel",
                text = "Transcript",
                alignment = { AlignHCenter = true },
                styleSheet = "font-weight: bold; font-size: 14px; padding: 10px;"
            },
            
            -- Clip info label
            {
                type = "Label",
                id = "clipInfoLabel",
                text = "",
                alignment = { AlignHCenter = true },
                styleSheet = "color: gray; font-size: 11px; padding-bottom: 5px;"
            },
            
            -- Status label
            {
                type = "Label",
                id = "statusLabel",
                text = "Retrieving transcription...",
                alignment = { AlignHCenter = true },
                styleSheet = "color: blue; font-size: 11px; padding: 5px;"
            },
            
            -- Transcript text area (scrollable)
            {
                type = "TextEdit",
                id = "transcriptText",
                readOnly = true,
                minimumSize = { width = 850, height = 450 },
                font = { family = "Consolas", size = 11 },  -- Monospace for consistent formatting
                wordWrap = true,
                placeholderText = "Transcript will appear here..."
            },
            
            -- Transcript metadata area
            {
                type = "Layout",
                layout = "Horizontal",
                styleSheet = "padding: 5px;",
                components = {
                    {
                        type = "Label",
                        id = "wordCountLabel",
                        text = "",
                        styleSheet = "color: gray; font-size: 10px;"
                    },
                    {
                        type = "Stretch"
                    },
                    {
                        type = "Label",
                        id = "speakerLabel",
                        text = "",
                        styleSheet = "color: gray; font-size: 10px;"
                    }
                }
            },
            
            -- Error label (hidden by default)
            {
                type = "Label",
                id = "errorLabel",
                text = "",
                visible = false,
                alignment = { AlignHCenter = true },
                styleSheet = "color: red; font-size: 12px; padding: 10px;"
            },
            
            -- Button row
            {
                type = "Layout",
                layout = "Horizontal",
                styleSheet = "padding-top: 10px;",
                components = {
                    {
                        type = "Button",
                        id = "backButton",
                        text = "Back to Media Pool",
                        onClicked = function()
                            TranscriptViewer.goBackToMediaPool()
                        end
                    },
                    {
                        type = "Stretch"
                    },
                    {
                        type = "Button",
                        id = "proceedButton",
                        text = "Review Quality →",
                        enabled = false,  -- Enabled when transcript loaded
                        default = true,
                        onClicked = function()
                            TranscriptViewer.proceedToQualityReview()
                        end
                    }
                }
            }
        }
    }
    
    return dialog
end

--[[
    Update the header with clip name.
    
    Args:
        clipName: Name of the selected clip
--]]
function TranscriptViewer.updateHeader(clipName)
    local headerLabel = TranscriptViewer.getComponent("headerLabel")
    if headerLabel then
        headerLabel:SetText("Transcript: " .. (clipName or "Unknown"))
    end
    
    local clipInfoLabel = TranscriptViewer.getComponent("clipInfoLabel")
    if clipInfoLabel then
        clipInfoLabel:SetText("Resolve Native Transcription")
    end
end

--[[
    Show loading state in the UI.
--]]
function TranscriptViewer.showLoadingState()
    local statusLabel = TranscriptViewer.getComponent("statusLabel")
    if statusLabel then
        statusLabel:SetText("Retrieving transcription from Resolve...")
        statusLabel:SetVisible(true)
    end
    
    local transcriptText = TranscriptViewer.getComponent("transcriptText")
    if transcriptText then
        transcriptText:SetText("")
        transcriptText:SetEnabled(false)
    end
    
    local proceedButton = TranscriptViewer.getComponent("proceedButton")
    if proceedButton then
        proceedButton:SetEnabled(false)
    end
end

--[[
    Retrieve transcription from Resolve or Python backend.
    
    First tries to get transcription directly from Resolve via Lua API.
    If not available, falls back to Python backend which may use alternative methods.
    
    Args:
        clipData: Table containing clip information
--]]
function TranscriptViewer.retrieveTranscription(clipData)
    -- First, try to get transcription directly from Resolve
    local ResolveAPI = require("resolve_api")
    local transcription, err = ResolveAPI.getTranscription(clipData.id)
    
    if transcription then
        -- Got transcription directly from Resolve - display it
        TranscriptViewer.handleTranscriptionResponse({
            transcript = transcription
        })
        return
    end
    
    -- No transcription available from Resolve - inform user
    if err == "TRANSCRIPTION_NOT_AVAILABLE" then
        TranscriptViewer.handleTranscriptionResponse({
            error = {
                code = "TRANSCRIPTION_NOT_AVAILABLE",
                message = "Selected clip has not been transcribed by Resolve",
                suggestion = "Transcribe the clip in Resolve's Edit page before using RoughCut"
            }
        })
        return
    end
    
    -- Get current project name for context
    local projectName = "Unknown"
    local proj, _ = ResolveAPI.getCurrentProjectName()
    if proj then
        projectName = proj
    end
    
    -- Fall back to Python backend for alternative retrieval methods
    local request = {
        method = "retrieve_transcription",
        params = {
            clip_id = clipData.id,
            clip_name = clipData.name,
            project_name = projectName
        },
        id = TranscriptViewer.generateRequestId()
    }
    
    -- Set up timeout (5 seconds per AC4 performance requirement)
    local timeoutSeconds = 5
    local requestId = request.id
    
    -- Store request with timestamp for timeout tracking
    TranscriptViewer._pendingRequests = TranscriptViewer._pendingRequests or {}
    TranscriptViewer._pendingRequests[requestId] = {
        timestamp = os.time(),
        timeout = timeoutSeconds,
        callback = nil  -- Will be set below
    }
    
    -- Create callback that clears timeout
    local callback = function(response)
        -- Clear pending request
        if TranscriptViewer._pendingRequests then
            TranscriptViewer._pendingRequests[requestId] = nil
        end
        TranscriptViewer.handleTranscriptionResponse(response)
    end
    
    TranscriptViewer._pendingRequests[requestId].callback = callback
    
    -- Start timeout timer
    TranscriptViewer.startTimeoutTimer(requestId, timeoutSeconds)
    
    -- Send to Python backend
    TranscriptViewer.sendToPython(request, callback)
end

--[[
    Start a timeout timer for a request.
    
    Args:
        requestId: Request ID to track
        timeoutSeconds: Timeout duration
--]]
function TranscriptViewer.startTimeoutTimer(requestId, timeoutSeconds)
    -- In a real Resolve environment, we'd use QTimer or similar
    -- For now, we'll check timeout in the response handler
    -- This is a simplified implementation - production would use proper async
    
    -- Store expected timeout time
    if TranscriptViewer._pendingRequests and TranscriptViewer._pendingRequests[requestId] then
        TranscriptViewer._pendingRequests[requestId].timeoutTime = os.time() + timeoutSeconds
    end
end

--[[
    Check if a request has timed out.
    
    Args:
        requestId: Request ID to check
        
    Returns:
        hasTimedOut: Boolean indicating if request timed out
--]]
function TranscriptViewer.hasRequestTimedOut(requestId)
    if not TranscriptViewer._pendingRequests or not TranscriptViewer._pendingRequests[requestId] then
        return false
    end
    
    local requestInfo = TranscriptViewer._pendingRequests[requestId]
    if requestInfo.timeoutTime and os.time() > requestInfo.timeoutTime then
        return true
    end
    
    return false
end

--[[
    Handle the transcription retrieval response.
    
    Args:
        response: Response from Python backend containing transcript or error
--]]
function TranscriptViewer.handleTranscriptionResponse(response)
    TranscriptViewer.isLoading = false
    
    -- Handle JSON-RPC error
    if response.error then
        TranscriptViewer.showError(response.error)
        return
    end
    
    -- Extract transcript from result wrapper (JSON-RPC standard format)
    local transcript = nil
    if response.result and response.result.transcript then
        transcript = response.result.transcript
    elseif response.transcript then
        -- Fallback for backward compatibility (direct response)
        transcript = response.transcript
    end
    
    if transcript then
        -- Store transcript data
        TranscriptViewer.transcriptData = transcript
        
        -- Display transcript
        TranscriptViewer.displayTranscript(transcript)
        
        -- Update status
        TranscriptViewer.showSuccessState()
    else
        -- No transcript data
        TranscriptViewer.showError({
            message = "No transcription data received",
            suggestion = "Try selecting a different clip"
        })
    end
end

--[[
    Display the transcript text in the UI.
    
    Args:
        transcript: Table containing transcript data
            {
                text = "...",
                word_count = 5234,
                has_speaker_labels = true,
                segments = [...]
            }
--]]
function TranscriptViewer.displayTranscript(transcript)
    local transcriptText = TranscriptViewer.getComponent("transcriptText")
    if not transcriptText then
        return
    end
    
    -- Get formatted text with speaker labels
    local displayText = ""
    
    if transcript.segments and #transcript.segments > 0 then
        -- Use segments with speaker labels
        local lines = {}
        for _, segment in ipairs(transcript.segments) do
            local line = segment.text
            if segment.speaker and segment.speaker ~= "" then
                line = segment.speaker .. ": " .. line
            end
            table.insert(lines, line)
        end
        displayText = table.concat(lines, "\n\n")
    else
        -- Use full text
        displayText = transcript.text or ""
    end
    
    -- Set text in widget
    transcriptText:SetText(displayText)
    transcriptText:SetEnabled(true)
    
    -- Update metadata labels
    local wordCountLabel = TranscriptViewer.getComponent("wordCountLabel")
    if wordCountLabel then
        local wordCount = transcript.word_count or 0
        wordCountLabel:SetText(string.format("Words: %d", wordCount))
    end
    
    local speakerLabel = TranscriptViewer.getComponent("speakerLabel")
    if speakerLabel then
        if transcript.has_speaker_labels then
            speakerLabel:SetText("Speaker labels: Yes")
        else
            speakerLabel:SetText("Speaker labels: No")
        end
    end
end

--[[
    Show success state after transcript loaded.
--]]
function TranscriptViewer.showSuccessState()
    local statusLabel = TranscriptViewer.getComponent("statusLabel")
    if statusLabel then
        statusLabel:SetText("Transcription loaded successfully")
        statusLabel:SetStyleSheet("color: green; font-size: 11px; padding: 5px;")
    end
    
    local proceedButton = TranscriptViewer.getComponent("proceedButton")
    if proceedButton then
        proceedButton:SetEnabled(true)
    end
    
    local errorLabel = TranscriptViewer.getComponent("errorLabel")
    if errorLabel then
        errorLabel:SetVisible(false)
    end
end

--[[
    Show error message in the UI.
    
    Args:
        errorData: Table containing error information
            {
                message = "...",
                suggestion = "..." (optional)
            }
--]]
function TranscriptViewer.showError(errorData)
    local statusLabel = TranscriptViewer.getComponent("statusLabel")
    if statusLabel then
        statusLabel:SetVisible(false)
    end
    
    local transcriptText = TranscriptViewer.getComponent("transcriptText")
    if transcriptText then
        transcriptText:SetText("")
        transcriptText:SetEnabled(false)
    end
    
    local errorLabel = TranscriptViewer.getComponent("errorLabel")
    if errorLabel then
        local errorMsg = errorData.message or "Unknown error"
        if errorData.suggestion then
            errorMsg = errorMsg .. "\n\n" .. errorData.suggestion
        end
        errorLabel:SetText(errorMsg)
        errorLabel:SetVisible(true)
    end
    
    local proceedButton = TranscriptViewer.getComponent("proceedButton")
    if proceedButton then
        proceedButton:SetEnabled(false)
    end
end

--[[
    Go back to media pool browser.
--]]
function TranscriptViewer.goBackToMediaPool()
    TranscriptViewer.close()
    
    -- Open media browser
    local MediaBrowser = require("media_browser")
    MediaBrowser.show()
end

--[[
    Proceed to transcription quality review (Story 4.3).
--]]
function TranscriptViewer.proceedToQualityReview()
    if not TranscriptViewer.transcriptData then
        return
    end
    
    TranscriptViewer.close()
    
    -- Trigger next workflow step (Story 4.3)
    -- This would open the quality review UI
    if TranscriptViewer.onQualityReviewRequested then
        TranscriptViewer.onQualityReviewRequested(
            TranscriptViewer.currentClip,
            TranscriptViewer.transcriptData
        )
    end
end

--[[
    Close the transcript viewer dialog.
--]]
function TranscriptViewer.close()
    if TranscriptViewer.currentDialog then
        TranscriptViewer.currentDialog = nil
    end
    
    TranscriptViewer.currentClip = nil
    TranscriptViewer.transcriptData = nil
    TranscriptViewer.isLoading = false
end

--[[
    Get a component from the current dialog.
    
    Args:
        id: Component ID string
        
    Returns:
        component: The UI component, or nil if not found
--]]
function TranscriptViewer.getComponent(id)
    if not TranscriptViewer.currentDialog then
        return nil
    end
    
    return TranscriptViewer.currentDialog.components[id]
end

--[[
    Generate unique request ID for protocol calls.
    
    Returns:
        id: Unique request ID string
--]]
function TranscriptViewer.generateRequestId()
    return string.format("req_%d_%d", os.time(), math.random(1000, 9999))
end

--[[
    Send request to Python backend.
    
    Args:
        request: Table containing method, params, and id
        callback: Function(response) to call when response received
--]]
function TranscriptViewer.sendToPython(request, callback)
    -- Store callback for when response comes back
    TranscriptViewer._pendingCallbacks = TranscriptViewer._pendingCallbacks or {}
    TranscriptViewer._pendingCallbacks[request.id] = callback
    
    -- Convert to JSON and send via stdout
    local json = require("utils.json")  -- Assume json utility exists
    local message = json.encode(request)
    io.write(message .. "\n")
    io.flush()
end

--[[
    Handle incoming response from Python backend.
    
    Args:
        response: Table containing response data
--]]
function TranscriptViewer.handleResponse(response)
    if not response.id then
        return
    end
    
    local callback = TranscriptViewer._pendingCallbacks and TranscriptViewer._pendingCallbacks[response.id]
    if callback then
        callback(response)
        TranscriptViewer._pendingCallbacks[response.id] = nil
    end
end

--[[
    Show error dialog.
    
    Args:
        message: Error message to display
--]]
function TranscriptViewer.showErrorDialog(message)
    print("[RoughCut Error] " .. message)
end

--[[
    Set callback for when quality review is requested.
    
    Args:
        callback: Function(clipData, transcriptData) to call when proceeding
--]]
function TranscriptViewer.setOnQualityReviewRequested(callback)
    TranscriptViewer.onQualityReviewRequested = callback
end

return TranscriptViewer
