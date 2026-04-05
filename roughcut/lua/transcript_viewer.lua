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
    ============================================================================
    STORY 4.3: TRANSCRIPTION QUALITY REVIEW UI
    ============================================================================
    The following functions implement the quality review interface for Story 4.3.
    This adds quality indicators, problem highlighting, and user decision points.
--]]

-- UI state for quality review
TranscriptViewer.qualityData = nil
TranscriptViewer.isQualityReviewMode = false

--[[
    Show the quality review dialog.
    
    This is the main entry point for Story 4.3 quality review.
    
    Args:
        clipData: Table containing clip information
        transcriptData: Table containing transcript data
--]]
function TranscriptViewer.showQualityReview(clipData, transcriptData)
    -- Validate transcript data
    if not transcriptData then
        TranscriptViewer.showErrorDialog("No transcript data provided for quality review")
        return
    end
    
    if type(transcriptData) ~= "table" then
        TranscriptViewer.showErrorDialog("Invalid transcript data format")
        return
    end
    
    -- Store data
    TranscriptViewer.currentClip = clipData
    TranscriptViewer.transcriptData = transcriptData
    TranscriptViewer.isQualityReviewMode = true
    
    -- Check if Resolve is available
    local ResolveAPI = require("resolve_api")
    local available, err = ResolveAPI.isAvailable()
    
    if not available then
        local msg = ResolveAPI.getErrorMessage(err)
        TranscriptViewer.showErrorDialog(msg)
        return
    end
    
    -- Create and show the quality review dialog
    local dialog = TranscriptViewer.createQualityReviewDialog()
    if dialog then
        TranscriptViewer.currentDialog = dialog
        
        -- Update header
        TranscriptViewer.updateQualityHeader(clipData.name)
        
        -- Show loading state
        TranscriptViewer.showQualityLoadingState()
        
        -- Analyze quality
        TranscriptViewer.analyzeQuality(transcriptData)
    end
end

--[[
    Create the quality review dialog structure.
    
    Returns:
        dialog: Table describing the dialog structure
--]]
function TranscriptViewer.createQualityReviewDialog()
    local dialog = {
        title = "Review Transcription Quality - RoughCut",
        width = 900,
        height = 750,
        
        -- Window style - modal dialog
        modal = true,
        
        -- UI Components
        components = {
            -- Header
            {
                type = "Label",
                id = "headerLabel",
                text = "Review Transcription Quality",
                alignment = { AlignHCenter = true },
                styleSheet = "font-weight: bold; font-size: 16px; padding: 10px;"
            },
            
            -- Clip info label
            {
                type = "Label",
                id = "clipInfoLabel",
                text = "",
                alignment = { AlignHCenter = true },
                styleSheet = "color: gray; font-size: 11px; padding-bottom: 5px;"
            },
            
            -- Quality Banner (good/fair/poor)
            {
                type = "Frame",
                id = "qualityBanner",
                styleSheet = "background-color: #e8f5e9; border: 2px solid #4caf50; border-radius: 5px; padding: 10px; margin: 5px;",
                visible = false,
                components = {
                    {
                        type = "Layout",
                        layout = "Horizontal",
                        components = {
                            {
                                type = "Label",
                                id = "qualityIconLabel",
                                text = "✓",
                                styleSheet = "font-size: 20px; color: #4caf50;"
                            },
                            {
                                type = "Label",
                                id = "qualityTextLabel",
                                text = "Quality: Good",
                                styleSheet = "font-weight: bold; font-size: 14px; color: #2e7d32; padding-left: 10px;"
                            }
                        }
                    },
                    {
                        type = "Label",
                        id = "qualityDetailLabel",
                        text = "",
                        styleSheet = "color: #555; font-size: 11px; padding-top: 5px;"
                    }
                }
            },
            
            -- Recommendation label
            {
                type = "Label",
                id = "recommendationLabel",
                text = "",
                alignment = { AlignHCenter = true },
                styleSheet = "color: #333; font-size: 12px; padding: 10px; font-style: italic;"
            },
            
            -- Status label
            {
                type = "Label",
                id = "statusLabel",
                text = "Analyzing transcription quality...",
                alignment = { AlignHCenter = true },
                styleSheet = "color: blue; font-size: 11px; padding: 5px;"
            },
            
            -- Transcript text area with problem highlighting
            {
                type = "TextEdit",
                id = "transcriptText",
                readOnly = true,
                minimumSize = { width = 850, height = 400 },
                font = { family = "Consolas", size = 11 },
                wordWrap = true,
                placeholderText = "Transcript with quality analysis will appear here..."
            },
            
            -- Problem areas summary
            {
                type = "Frame",
                id = "problemSummaryFrame",
                styleSheet = "background-color: #ffebee; border: 1px solid #ef5350; border-radius: 3px; padding: 8px; margin: 5px;",
                visible = false,
                components = {
                    {
                        type = "Label",
                        id = "problemSummaryLabel",
                        text = "",
                        styleSheet = "color: #c62828; font-size: 11px;"
                    }
                }
            },
            
            -- Button row
            {
                type = "Layout",
                layout = "Horizontal",
                styleSheet = "padding-top: 15px;",
                components = {
                    {
                        type = "Button",
                        id = "backButton",
                        text = "← Go Back",
                        visible = false,  -- Hidden by default, shown for non-good quality per AC4
                        onClicked = function()
                            TranscriptViewer.goBackToTranscript()
                        end
                    },
                    {
                        type = "Stretch"
                    },
                    {
                        type = "Button",
                        id = "audioCleanupButton",
                        text = "Learn: Audio Cleanup",
                        visible = false,
                        onClicked = function()
                            TranscriptViewer.showAudioCleanupGuide()
                        end
                    },
                    {
                        type = "Stretch"
                    },
                    {
                        type = "Button",
                        id = "proceedAnywayButton",
                        text = "Proceed Anyway →",
                        visible = false,
                        onClicked = function()
                            TranscriptViewer.proceedAnyway()
                        end
                    },
                    {
                        type = "Button",
                        id = "proceedButton",
                        text = "Proceed to Format Selection →",
                        enabled = false,
                        default = true,
                        visible = true,
                        onClicked = function()
                            TranscriptViewer.proceedToFormatSelection()
                        end
                    }
                }
            }
        }
    }
    
    return dialog
end

--[[
    Update the quality review header with clip name.
    
    Args:
        clipName: Name of the selected clip
--]]
function TranscriptViewer.updateQualityHeader(clipName)
    local clipInfoLabel = TranscriptViewer.getComponent("clipInfoLabel")
    if clipInfoLabel then
        clipInfoLabel:SetText("Analyzing: " .. (clipName or "Unknown"))
    end
end

--[[
    Show loading state during quality analysis.
--]]
function TranscriptViewer.showQualityLoadingState()
    local statusLabel = TranscriptViewer.getComponent("statusLabel")
    if statusLabel then
        statusLabel:SetText("Analyzing transcription quality...")
        statusLabel:SetVisible(true)
    end
    
    local qualityBanner = TranscriptViewer.getComponent("qualityBanner")
    if qualityBanner then
        qualityBanner:SetVisible(false)
    end
    
    local proceedButton = TranscriptViewer.getComponent("proceedButton")
    if proceedButton then
        proceedButton:SetEnabled(false)
    end
end

--[[
    Analyze transcription quality via Python backend.
    
    Args:
        transcriptData: Table containing transcript data
--]]
function TranscriptViewer.analyzeQuality(transcriptData)
    local request = {
        method = "analyze_transcription_quality",
        params = {
            transcript = transcriptData,
            clip_name = TranscriptViewer.currentClip and TranscriptViewer.currentClip.name or "Unknown"
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
        callback = nil
    }
    
    -- Create callback
    local callback = function(response)
        -- Clear pending request
        if TranscriptViewer._pendingRequests then
            TranscriptViewer._pendingRequests[requestId] = nil
        end
        TranscriptViewer.handleQualityAnalysisResponse(response)
    end
    
    TranscriptViewer._pendingRequests[requestId].callback = callback
    
    -- Start timeout timer
    TranscriptViewer.startTimeoutTimer(requestId, timeoutSeconds)
    
    -- Send to Python backend
    TranscriptViewer.sendToPython(request, callback)
end

--[[
    Handle the quality analysis response.
    
    Args:
        response: Response from Python backend
--]]
function TranscriptViewer.handleQualityAnalysisResponse(response)
    -- Handle JSON-RPC error
    if response.error then
        TranscriptViewer.showQualityError(response.error)
        return
    end
    
    -- Extract quality data from result
    local quality = nil
    if response.result then
        quality = response.result
    end
    
    if quality then
        -- Store quality data
        TranscriptViewer.qualityData = quality
        
        -- Display quality results
        TranscriptViewer.displayQualityResults(quality)
    else
        -- No quality data
        TranscriptViewer.showQualityError({
            message = "No quality analysis data received",
            suggestion = "Try analyzing again"
        })
    end
end

--[[
    Display quality analysis results in the UI.
    
    Args:
        quality: Table containing quality analysis results
--]]
function TranscriptViewer.displayQualityResults(quality)
    -- Hide loading status
    local statusLabel = TranscriptViewer.getComponent("statusLabel")
    if statusLabel then
        statusLabel:SetVisible(false)
    end
    
    -- Update quality banner
    TranscriptViewer.updateQualityBanner(quality)
    
    -- Display transcript with problem highlighting
    TranscriptViewer.displayTranscriptWithProblems(quality)
    
    -- Show problem summary if there are problems
    if quality.problem_count and quality.problem_count > 0 then
        TranscriptViewer.showProblemSummary(quality)
    end
    
    -- Update recommendation
    local recommendationLabel = TranscriptViewer.getComponent("recommendationLabel")
    if recommendationLabel and quality.recommendation then
        recommendationLabel:SetText(quality.recommendation)
    end
    
    -- Configure buttons based on quality
    TranscriptViewer.configureDecisionButtons(quality)
end

--[[
    Update the quality banner based on quality rating.
    
    Args:
        quality: Table containing quality data
--]]
function TranscriptViewer.updateQualityBanner(quality)
    local banner = TranscriptViewer.getComponent("qualityBanner")
    if not banner then
        return
    end
    
    local iconLabel = TranscriptViewer.getComponent("qualityIconLabel")
    local textLabel = TranscriptViewer.getComponent("qualityTextLabel")
    local detailLabel = TranscriptViewer.getComponent("qualityDetailLabel")
    
    local rating = quality.quality_rating or "good"
    local confidence = quality.confidence_score or 0
    local completeness = quality.completeness_pct or 100
    local problems = quality.problem_count or 0
    
    -- Set colors and icon based on rating
    if rating == "good" then
        -- Good quality - green
        banner:SetStyleSheet("background-color: #e8f5e9; border: 2px solid #4caf50; border-radius: 5px; padding: 10px; margin: 5px;")
        if iconLabel then
            iconLabel:SetText("✓")
            iconLabel:SetStyleSheet("font-size: 20px; color: #4caf50;")
        end
        if textLabel then
            textLabel:SetText("Quality: Good ✓")
            textLabel:SetStyleSheet("font-weight: bold; font-size: 14px; color: #2e7d32; padding-left: 10px;")
        end
    elseif rating == "fair" then
        -- Fair quality - yellow/orange
        banner:SetStyleSheet("background-color: #fff8e1; border: 2px solid #ffa726; border-radius: 5px; padding: 10px; margin: 5px;")
        if iconLabel then
            iconLabel:SetText("⚠")
            iconLabel:SetStyleSheet("font-size: 20px; color: #ffa726;")
        end
        if textLabel then
            textLabel:SetText("Quality: Fair ⚠")
            textLabel:SetStyleSheet("font-weight: bold; font-size: 14px; color: #ef6c00; padding-left: 10px;")
        end
    else
        -- Poor quality - red
        banner:SetStyleSheet("background-color: #ffebee; border: 2px solid #ef5350; border-radius: 5px; padding: 10px; margin: 5px;")
        if iconLabel then
            iconLabel:SetText("✗")
            iconLabel:SetStyleSheet("font-size: 20px; color: #ef5350;")
        end
        if textLabel then
            textLabel:SetText("Quality: Poor ✗")
            textLabel:SetStyleSheet("font-weight: bold; font-size: 14px; color: #c62828; padding-left: 10px;")
        end
    end
    
    -- Set detail text
    if detailLabel then
        local detailText = string.format(
            "Confidence: %d%% | Completeness: %d%% | Problems: %d",
            math.floor(confidence * 100),
            math.floor(completeness),
            problems
        )
        detailLabel:SetText(detailText)
    end
    
    banner:SetVisible(true)
end

--[[
    Display transcript with problem areas highlighted.
    
    Args:
        quality: Table containing quality data with problem_areas
--]]
function TranscriptViewer.displayTranscriptWithProblems(quality)
    local transcriptText = TranscriptViewer.getComponent("transcriptText")
    if not transcriptText then
        return
    end
    
    -- Get the original transcript text
    local text = ""
    if TranscriptViewer.transcriptData then
        if TranscriptViewer.transcriptData.segments and #TranscriptViewer.transcriptData.segments > 0 then
            -- Format with speaker labels
            local lines = {}
            for _, segment in ipairs(TranscriptViewer.transcriptData.segments) do
                local line = segment.text
                if segment.speaker and segment.speaker ~= "" then
                    line = segment.speaker .. ": " .. line
                end
                table.insert(lines, line)
            end
            text = table.concat(lines, "\n\n")
        else
            text = TranscriptViewer.transcriptData.text or ""
        end
    end
    
    -- For now, display text with visual indicators around problem markers.
    -- Since Resolve UI may not support rich text, we add visual markers (► ◄)
    -- around problem areas to make them stand out.
    if quality and quality.problem_areas then
        for _, problem in ipairs(quality.problem_areas) do
            local marker = problem.text
            if marker then
                -- Add visual indicators around problem markers
                text = text:gsub(
                    "%[" .. marker:match("%[([^%]]+)") .. "%]",
                    "►[" .. marker:match("%[([^%]]+)") .. "]◄"
                )
            end
        end
    end
    
    -- TODO: When Resolve UI supports rich text, implement proper color highlighting
    -- For now, the ► ◄ markers provide visual distinction per AC2
    
    transcriptText:SetText(text)
    transcriptText:SetEnabled(true)
end

--[[
    Show problem summary section.
    
    Args:
        quality: Table containing quality data
--]]
function TranscriptViewer.showProblemSummary(quality)
    local frame = TranscriptViewer.getComponent("problemSummaryFrame")
    local label = TranscriptViewer.getComponent("problemSummaryLabel")
    
    if not frame or not label then
        return
    end
    
    local problems = quality.problem_areas or {}
    local problemCount = quality.problem_count or 0
    
    -- Count by type
    local typeCounts = {}
    for _, problem in ipairs(problems) do
        local ptype = problem.type or "unknown"
        typeCounts[ptype] = (typeCounts[ptype] or 0) + 1
    end
    
    -- Build summary text
    local summaryParts = {}
    for ptype, count in pairs(typeCounts) do
        table.insert(summaryParts, string.format("%s: %d", ptype, count))
    end
    
    local summaryText = "Problem areas detected: " .. table.concat(summaryParts, ", ")
    if problemCount > 10 then
        summaryText = summaryText .. " - Audio cleanup strongly recommended"
    end
    
    label:SetText(summaryText)
    frame:SetVisible(true)
end

--[[
    Configure decision buttons based on quality.
    
    Args:
        quality: Table containing quality data
--]]
function TranscriptViewer.configureDecisionButtons(quality)
    local rating = quality.quality_rating or "good"
    local proceedButton = TranscriptViewer.getComponent("proceedButton")
    local proceedAnywayButton = TranscriptViewer.getComponent("proceedAnywayButton")
    local audioCleanupButton = TranscriptViewer.getComponent("audioCleanupButton")
    local backButton = TranscriptViewer.getComponent("backButton")
    
    if rating == "good" then
        -- Good quality - standard proceed button only, hide others
        if proceedButton then
            proceedButton:SetEnabled(true)
            proceedButton:SetVisible(true)
        end
        if proceedAnywayButton then
            proceedAnywayButton:SetVisible(false)
        end
        if audioCleanupButton then
            audioCleanupButton:SetVisible(false)
        end
        if backButton then
            backButton:SetVisible(false)  -- Hide back button for good quality
        end
    else
        -- Fair or poor quality - show all three action buttons per AC4
        -- [Proceed Anyway] [Go Back] [Learn About Audio Cleanup]
        if proceedButton then
            proceedButton:SetEnabled(true)
            proceedButton:SetVisible(false)  -- Hide standard proceed
        end
        if proceedAnywayButton then
            proceedAnywayButton:SetEnabled(true)
            proceedAnywayButton:SetVisible(true)
        end
        if audioCleanupButton then
            audioCleanupButton:SetVisible(true)
        end
        if backButton then
            backButton:SetVisible(true)  -- Show back button for non-good quality
        end
    end
end

--[[
    Show audio cleanup guide (launches Story 4.4 Error Recovery Workflow).
--]]
function TranscriptViewer.showAudioCleanupGuide()
    print("[RoughCut] Opening Audio Cleanup Guide...")
    
    -- Close quality review dialog
    TranscriptViewer.close()
    
    -- Launch the Error Recovery Workflow (Story 4.4)
    local ErrorRecovery = require("error_recovery")
    ErrorRecovery.showErrorRecoveryDialog(
        TranscriptViewer.qualityData,
        TranscriptViewer.currentClip
    )
end

--[[
    Proceed to format selection despite quality warnings.
--]]
function TranscriptViewer.proceedAnyway()
    TranscriptViewer.close()
    
    -- Trigger format selection workflow
    if TranscriptViewer.onFormatSelectionRequested then
        TranscriptViewer.onFormatSelectionRequested(
            TranscriptViewer.currentClip,
            TranscriptViewer.transcriptData,
            TranscriptViewer.qualityData
        )
    end
end

--[[
    Proceed to format selection (normal flow).
--]]
function TranscriptViewer.proceedToFormatSelection()
    TranscriptViewer.close()
    
    -- Trigger format selection workflow
    if TranscriptViewer.onFormatSelectionRequested then
        TranscriptViewer.onFormatSelectionRequested(
            TranscriptViewer.currentClip,
            TranscriptViewer.transcriptData,
            TranscriptViewer.qualityData
        )
    end
end

--[[
    Go back to transcript view.
--]]
function TranscriptViewer.goBackToTranscript()
    local clipData = TranscriptViewer.currentClip
    local transcriptData = TranscriptViewer.transcriptData
    
    TranscriptViewer.close()
    
    -- Re-show transcript viewer
    if clipData and transcriptData then
        TranscriptViewer.show(clipData)
        -- Note: We'd need to modify show() to accept pre-loaded transcript data
    end
end

--[[
    Show quality analysis error.
    
    Args:
        errorData: Table containing error information
--]]
function TranscriptViewer.showQualityError(errorData)
    local statusLabel = TranscriptViewer.getComponent("statusLabel")
    if statusLabel then
        local errorMsg = errorData.message or "Quality analysis failed"
        if errorData.suggestion then
            errorMsg = errorMsg .. " - " .. errorData.suggestion
        end
        statusLabel:SetText(errorMsg)
        statusLabel:SetStyleSheet("color: red; font-size: 11px; padding: 5px;")
        statusLabel:SetVisible(true)
    end
    
    local proceedButton = TranscriptViewer.getComponent("proceedButton")
    if proceedButton then
        proceedButton:SetEnabled(false)
    end
end

--[[
    Set callback for when format selection is requested.
    
    Args:
        callback: Function(clipData, transcriptData, qualityData) to call
--]]
function TranscriptViewer.setOnFormatSelectionRequested(callback)
    TranscriptViewer.onFormatSelectionRequested = callback
end


--[[
    ============================================================================
    END OF STORY 4.3 QUALITY REVIEW UI
    ============================================================================
--]]

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
    
    -- Close current transcript view and open quality review
    local clipData = TranscriptViewer.currentClip
    local transcriptData = TranscriptViewer.transcriptData
    
    TranscriptViewer.close()
    
    -- Open quality review UI (Story 4.3)
    TranscriptViewer.showQualityReview(clipData, transcriptData)
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
