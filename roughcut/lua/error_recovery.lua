--[[
    Error Recovery Workflow UI (Story 4.4)
    
    Provides dialogs and workflow management for the error recovery process
    when transcription quality is poor. Allows users to:
    1. Abort and clean audio
    2. Retry with different clip
    3. Proceed anyway
    4. View and follow audio cleanup guide
    
    Usage:
        local ErrorRecovery = require("error_recovery")
        ErrorRecovery.showErrorRecoveryDialog(qualityData, clipData)
--]]

local ErrorRecovery = {}

-- UI state
ErrorRecovery.currentClip = nil
ErrorRecovery.originalClip = nil
ErrorRecovery.qualityData = nil
ErrorRecovery.cleanupGuide = nil
ErrorRecovery.isInRecoveryMode = false
ErrorRecovery.currentDialog = nil
ErrorRecovery.guideDialog = nil

-- Callbacks
ErrorRecovery.onAbortCompleted = nil  -- Called after successful abort to navigate to main window

--[[
    Show the error recovery dialog.
    
    This is the main entry point for Story 4.4 error recovery workflow.
    Called when transcription quality is poor and user clicks [Learn About Audio Cleanup].
    
    Args:
        qualityData: Table containing quality analysis results
            {
                quality_rating = "poor",
                confidence_score = 0.67,
                completeness_pct = 45,
                problem_count = 12,
                recommendation = "Audio cleanup recommended..."
            }
        clipData: Table containing current clip information
            {
                id = "resolve_clip_001",
                name = "interview_take1",
                path = "/path/to/clip.mov"
            }
--]]
function ErrorRecovery.showErrorRecoveryDialog(qualityData, clipData)
    -- Validate inputs
    if not qualityData then
        ErrorRecovery.showErrorDialog("No quality data provided for recovery")
        return
    end
    
    if not clipData then
        ErrorRecovery.showErrorDialog("No clip data provided for recovery")
        return
    end
    
    -- Store data
    ErrorRecovery.qualityData = qualityData
    ErrorRecovery.currentClip = clipData
    ErrorRecovery.isInRecoveryMode = true
    
    -- Enter recovery mode in Python backend (with error handling)
    local status, err = pcall(function()
        ErrorRecovery.enterRecoveryMode(clipData)
    end)
    
    if not status then
        print("[RoughCut Warning] Failed to enter recovery mode: " .. tostring(err))
        ErrorRecovery.showErrorDialog(
            "Failed to initialize recovery mode. Please check that RoughCut backend is running and try again."
        )
        return
    end
    
    -- Create and show the recovery dialog
    local dialog = ErrorRecovery.createRecoveryDialog()
    if dialog then
        ErrorRecovery.currentDialog = dialog
        ErrorRecovery.updateRecoveryHeader(clipData.name, qualityData)
    end
end


--[[
    Create the error recovery dialog structure.
    
    Returns:
        dialog: Table describing the dialog structure (Resolve UI compatible)
--]]
function ErrorRecovery.createRecoveryDialog()
    local dialog = {
        title = "Audio Quality Issue - RoughCut",
        width = 700,
        height = 600,
        
        -- Window style - modal dialog
        modal = true,
        
        -- UI Components
        components = {
            -- Header
            {
                type = "Label",
                id = "recoveryHeaderLabel",
                text = "⚠ Transcription Quality Issue",
                alignment = { AlignHCenter = true },
                styleSheet = "font-weight: bold; font-size: 18px; color: #ef6c00; padding: 15px;"
            },
            
            -- Clip name
            {
                type = "Label",
                id = "clipNameLabel",
                text = "",
                alignment = { AlignHCenter = true },
                styleSheet = "font-size: 14px; color: #333; padding-bottom: 5px;"
            },
            
            -- Quality summary frame
            {
                type = "Frame",
                id = "qualitySummaryFrame",
                styleSheet = "background-color: #ffebee; border: 2px solid #ef5350; border-radius: 5px; padding: 15px; margin: 10px;",
                components = {
                    {
                        type = "Label",
                        id = "qualitySummaryLabel",
                        text = "",
                        alignment = { AlignHCenter = true },
                        styleSheet = "font-size: 13px; color: #c62828; font-weight: bold;"
                    },
                    {
                        type = "Label",
                        id = "qualityDetailsLabel",
                        text = "",
                        alignment = { AlignHCenter = true },
                        styleSheet = "font-size: 11px; color: #666; padding-top: 5px;"
                    }
                }
            },
            
            -- Recommendation label
            {
                type = "Label",
                id = "recommendationLabel",
                text = "Audio cleanup is recommended for best results.",
                alignment = { AlignHCenter = true },
                styleSheet = "font-size: 12px; color: #333; font-style: italic; padding: 10px;"
            },
            
            -- Separator line
            {
                type = "Frame",
                styleSheet = "background-color: #ddd; height: 2px; margin: 10px 20px;"
            },
            
            -- Options section header
            {
                type = "Label",
                id = "optionsHeaderLabel",
                text = "What would you like to do?",
                alignment = { AlignHCenter = true },
                styleSheet = "font-weight: bold; font-size: 13px; color: #333; padding: 10px;"
            },
            
            -- Option 1: Abort & Clean Audio (Primary)
            {
                type = "Frame",
                id = "abortOptionFrame",
                styleSheet = "background-color: #e3f2fd; border: 1px solid #64b5f6; border-radius: 5px; padding: 15px; margin: 8px 15px;",
                components = {
                    {
                        type = "Layout",
                        layout = "Horizontal",
                        components = {
                            {
                                type = "Label",
                                text = "🧹",
                                styleSheet = "font-size: 24px; padding-right: 10px;"
                            },
                            {
                                type = "Layout",
                                layout = "Vertical",
                                components = {
                                    {
                                        type = "Label",
                                        text = "Abort & Clean Audio",
                                        styleSheet = "font-weight: bold; font-size: 13px; color: #1565c0;"
                                    },
                                    {
                                        type = "Label",
                                        text = "Apply noise reduction in Resolve, then retry",
                                        styleSheet = "font-size: 11px; color: #555; padding-top: 3px;"
                                    }
                                }
                            },
                            {
                                type = "Stretch"
                            },
                            {
                                type = "Button",
                                id = "abortCleanButton",
                                text = "Start Cleanup →",
                                styleSheet = "background-color: #1976d2; color: white; font-weight: bold; padding: 8px 15px;",
                                onClicked = function()
                                    ErrorRecovery.onAbortAndCleanClicked()
                                end
                            }
                        }
                    }
                }
            },
            
            -- Option 2: Retry with Different Clip
            {
                type = "Frame",
                id = "retryOptionFrame",
                styleSheet = "background-color: #f3e5f5; border: 1px solid #ba68c8; border-radius: 5px; padding: 15px; margin: 8px 15px;",
                components = {
                    {
                        type = "Layout",
                        layout = "Horizontal",
                        components = {
                            {
                                type = "Label",
                                text = "🔄",
                                styleSheet = "font-size: 24px; padding-right: 10px;"
                            },
                            {
                                type = "Layout",
                                layout = "Vertical",
                                components = {
                                    {
                                        type = "Label",
                                        text = "Retry with Different Clip",
                                        styleSheet = "font-weight: bold; font-size: 13px; color: #7b1fa2;"
                                    },
                                    {
                                        type = "Label",
                                        text = "Select an alternative take or version",
                                        styleSheet = "font-size: 11px; color: #555; padding-top: 3px;"
                                    }
                                }
                            },
                            {
                                type = "Stretch"
                            },
                            {
                                type = "Button",
                                id = "retryDifferentButton",
                                text = "Choose Different Clip →",
                                styleSheet = "background-color: #8e24aa; color: white; font-weight: bold; padding: 8px 15px;",
                                onClicked = function()
                                    ErrorRecovery.onRetryDifferentClicked()
                                end
                            }
                        }
                    }
                }
            },
            
            -- Option 3: Proceed Anyway
            {
                type = "Frame",
                id = "proceedOptionFrame",
                styleSheet = "background-color: #fff3e0; border: 1px solid #ffb74d; border-radius: 5px; padding: 15px; margin: 8px 15px;",
                components = {
                    {
                        type = "Layout",
                        layout = "Horizontal",
                        components = {
                            {
                                type = "Label",
                                text = "⚡",
                                styleSheet = "font-size: 24px; padding-right: 10px;"
                            },
                            {
                                type = "Layout",
                                layout = "Vertical",
                                components = {
                                    {
                                        type = "Label",
                                        text = "Proceed Anyway",
                                        styleSheet = "font-weight: bold; font-size: 13px; color: #e65100;"
                                    },
                                    {
                                        type = "Label",
                                        text = "Continue with current quality (not recommended)",
                                        styleSheet = "font-size: 11px; color: #555; padding-top: 3px;"
                                    }
                                }
                            },
                            {
                                type = "Stretch"
                            },
                            {
                                type = "Button",
                                id = "proceedAnywayButton",
                                text = "Continue →",
                                styleSheet = "background-color: #f57c00; color: white; padding: 8px 15px;",
                                onClicked = function()
                                    ErrorRecovery.onProceedAnywayClicked()
                                end
                            }
                        }
                    }
                }
            },
            
            -- Separator before cancel
            {
                type = "Stretch"
            },
            
            -- Cancel button (bottom left)
            {
                type = "Layout",
                layout = "Horizontal",
                styleSheet = "padding: 15px;",
                components = {
                    {
                        type = "Button",
                        id = "cancelButton",
                        text = "← Cancel / Go Back",
                        onClicked = function()
                            ErrorRecovery.onCancelClicked()
                        end
                    },
                    {
                        type = "Stretch"
                    },
                    {
                        type = "Label",
                        id = "helpLabel",
                        text = "Your original clip is preserved",
                        styleSheet = "font-size: 10px; color: #999; font-style: italic;"
                    }
                }
            }
        }
    }
    
    return dialog
end


--[[
    Update the recovery dialog header with clip information.
    
    Args:
        clipName: Name of the clip
        qualityData: Quality analysis data
--]]
function ErrorRecovery.updateRecoveryHeader(clipName, qualityData)
    local clipLabel = ErrorRecovery.getComponent("clipNameLabel")
    if clipLabel then
        clipLabel:SetText("Clip: " .. (clipName or "Unknown"))
    end
    
    local qualitySummaryLabel = ErrorRecovery.getComponent("qualitySummaryLabel")
    if qualitySummaryLabel and qualityData then
        local rating = qualityData.quality_rating or "unknown"
        local confidence = math.floor((qualityData.confidence_score or 0) * 100)
        local problems = qualityData.problem_count or 0
        
        if rating == "poor" then
            qualitySummaryLabel:SetText(string.format(
                "⚠ Quality: POOR (%d%% confidence, %d problem areas)",
                confidence, problems
            ))
        elseif rating == "fair" then
            qualitySummaryLabel:SetText(string.format(
                "⚠ Quality: FAIR (%d%% confidence, %d problem areas)",
                confidence, problems
            ))
        end
    end
    
    local qualityDetailsLabel = ErrorRecovery.getComponent("qualityDetailsLabel")
    if qualityDetailsLabel and qualityData then
        local completeness = math.floor(qualityData.completeness_pct or 0)
        qualityDetailsLabel:SetText(
            "Transcript completeness: " .. completeness .. "% | Audio cleanup recommended"
        )
    end
end


--[[
    Callback when "Abort & Clean Audio" button is clicked.
    Shows confirmation and then displays the cleanup guide.
--]]
function ErrorRecovery.onAbortAndCleanClicked()
    -- Confirm with user before aborting
    local confirmMessage = [[
You are about to abort this RoughCut session to clean the audio.

This will:
✓ Exit the current workflow gracefully
✓ Return you to Resolve
✓ Preserve your original clip
✓ NOT create any timelines

After cleaning the audio in Resolve's Fairlight page, return to RoughCut and use "Retry with Cleaned Clip".

Continue with audio cleanup?]]
    
    -- Show confirmation dialog
    local confirmed = ErrorRecovery.showConfirmationDialog(
        "Confirm Audio Cleanup",
        confirmMessage
    )
    
    if confirmed then
        -- Abort the session
        ErrorRecovery.abortSession(function(success)
            if success then
                -- Close recovery dialog
                ErrorRecovery.close()
                
                -- Navigate to main window (AC2 compliance)
                if ErrorRecovery.onAbortCompleted then
                    ErrorRecovery.onAbortCompleted()
                end
                
                -- Show the cleanup guide
                ErrorRecovery.showCleanupGuide()
            else
                ErrorRecovery.showErrorDialog("Failed to abort session. Please try again.")
            end
        end)
    end
end


--[[
    Callback when "Retry with Different Clip" button is clicked.
    Aborts current session and returns to Media Pool browser.
--]]
function ErrorRecovery.onRetryDifferentClicked()
    local confirmMessage = [[
You are about to try a different clip.

This will:
✓ Cancel the current selection
✓ Return you to the Media Pool browser
✓ Let you select an alternative take

Continue?]]
    
    local confirmed = ErrorRecovery.showConfirmationDialog(
        "Try Different Clip",
        confirmMessage
    )
    
    if confirmed then
        -- Abort without preserving selection
        ErrorRecovery.abortSession(function(success)
            if success then
                -- Close recovery dialog
                ErrorRecovery.close()
                
                -- Open Media Browser
                local MediaBrowser = require("media_browser")
                MediaBrowser.show()
            else
                ErrorRecovery.showErrorDialog("Failed to switch clips. Please try again.")
            end
        end, false)  -- false = don't preserve clip selection
    end
end


--[[
    Callback when "Proceed Anyway" button is clicked.
    Proceeds to format selection despite quality warnings.
--]]
function ErrorRecovery.onProceedAnywayClicked()
    local confirmMessage = [[
Warning: Proceeding with poor transcription quality.

The AI rough cut generation may produce inaccurate results with:
• Missing or garbled dialogue
• Incorrect segment boundaries
• Suboptimal media matching

This is not recommended. Consider cleaning the audio first for best results.

Proceed anyway?]]
    
    local confirmed = ErrorRecovery.showConfirmationDialog(
        "⚠ Proceed with Poor Quality",
        confirmMessage,
        true  -- isWarning
    )
    
    if confirmed then
        -- Exit recovery mode
        ErrorRecovery.exitRecoveryMode(true)
        
        -- Close recovery dialog
        ErrorRecovery.close()
        
        -- Proceed to format selection
        if ErrorRecovery.onProceedToFormatSelection then
            ErrorRecovery.onProceedToFormatSelection(
                ErrorRecovery.currentClip,
                nil,  -- No transcript data (we never got good quality)
                ErrorRecovery.qualityData
            )
        end
    end
end


--[[
    Callback when "Cancel" button is clicked.
    Returns to the quality review screen.
--]]
function ErrorRecovery.onCancelClicked()
    -- Store current state
    local clipData = ErrorRecovery.currentClip
    local qualityData = ErrorRecovery.qualityData
    
    -- Close recovery dialog
    ErrorRecovery.close()
    
    -- Return to quality review
    local TranscriptViewer = require("transcript_viewer")
    TranscriptViewer.showQualityReview(clipData, TranscriptViewer.transcriptData)
end


--[[
    Show the audio cleanup guide dialog.
    Displays step-by-step instructions for Resolve noise reduction.
--]]
function ErrorRecovery.showCleanupGuide()
    -- Fetch guide content from Python backend
    ErrorRecovery.fetchCleanupGuide(function(guideData)
        if guideData then
            ErrorRecovery.cleanupGuide = guideData
            ErrorRecovery.createAndShowGuideDialog()
        else
            ErrorRecovery.showErrorDialog("Failed to load cleanup guide. Please try again.")
        end
    end)
end


--[[
    Create and show the cleanup guide dialog with step-by-step instructions.
--]]
function ErrorRecovery.createAndShowGuideDialog()
    local guide = ErrorRecovery.cleanupGuide
    if not guide then
        return
    end
    
    -- Build steps UI
    local stepsComponents = {}
    
    -- Header
    table.insert(stepsComponents, {
        type = "Label",
        id = "guideHeaderLabel",
        text = "🧹 " .. (guide.title or "Audio Cleanup Guide"),
        alignment = { AlignHCenter = true },
        styleSheet = "font-weight: bold; font-size: 16px; color: #1565c0; padding: 15px;"
    })
    
    -- Description
    table.insert(stepsComponents, {
        type = "Label",
        id = "guideDescriptionLabel",
        text = guide.description or "Follow these steps to clean your audio in Resolve.",
        alignment = { AlignHCenter = true },
        styleSheet = "font-size: 12px; color: #555; padding: 10px; font-style: italic;"
    })
    
    -- Progress bar
    table.insert(stepsComponents, {
        type = "ProgressBar",
        id = "guideProgressBar",
        value = 0,
        maximum = #(guide.steps or {}),
        styleSheet = "margin: 10px 20px;"
    })
    
    -- Steps
    local steps = guide.steps or {}
    for i, step in ipairs(steps) do
        local stepFrame = {
            type = "Frame",
            id = "step" .. i .. "Frame",
            styleSheet = "background-color: #f5f5f5; border: 1px solid #ddd; border-radius: 5px; padding: 12px; margin: 8px 15px;",
            components = {
                {
                    type = "Layout",
                    layout = "Horizontal",
                    components = {
                        -- Step number circle
                        {
                            type = "Label",
                            text = tostring(step.number or i),
                            styleSheet = "font-weight: bold; font-size: 16px; color: #1976d2; background-color: #e3f2fd; border-radius: 12px; padding: 5px 10px; min-width: 24px; text-align: center;"
                        },
                        {
                            type = "Layout",
                            layout = "Vertical",
                            styleSheet = "padding-left: 12px;",
                            components = {
                                -- Step title
                                {
                                    type = "Label",
                                    text = step.title or ("Step " .. i),
                                    styleSheet = "font-weight: bold; font-size: 13px; color: #333;"
                                },
                                -- Step description
                                {
                                    type = "Label",
                                    text = step.description or "",
                                    styleSheet = "font-size: 11px; color: #555; padding-top: 4px;"
                                },
                                -- Action
                                {
                                    type = "Label",
                                    text = "Action: " .. (step.action or ""),
                                    styleSheet = "font-size: 10px; color: #1976d2; padding-top: 4px; font-style: italic;"
                                },
                                -- Resolve location
                                {
                                    type = "Label",
                                    text = "Location: " .. (step.resolve_location or ""),
                                    styleSheet = "font-size: 10px; color: #666; padding-top: 2px;"
                                },
                                -- Tips (if any)
                                {
                                    type = "Label",
                                    id = "step" .. i .. "TipsLabel",
                                    text = "",
                                    visible = false,
                                    styleSheet = "font-size: 10px; color: #f57c00; padding-top: 4px;"
                                }
                            }
                        },
                        {
                            type = "Stretch"
                        },
                        -- Checkbox for completion
                        {
                            type = "CheckBox",
                            id = "step" .. i .. "CheckBox",
                            text = "Done",
                            onClicked = function()
                                ErrorRecovery.onStepChecked(i)
                            end
                        }
                    }
                }
            }
        }
        
        -- Add tips if present
        if step.tips and #step.tips > 0 then
            local tipsText = "💡 Tips: " .. table.concat(step.tips, " | ")
            -- Update the tips label in the frame
            for _, comp in ipairs(stepFrame.components[1].components) do
                if comp.type == "Layout" then
                    for _, subcomp in ipairs(comp.components) do
                        if subcomp.id == "step" .. i .. "TipsLabel" then
                            subcomp.text = tipsText
                            subcomp.visible = true
                        end
                    end
                end
            end
        end
        
        -- Add settings if present
        if step.settings then
            local settingsText = "Settings: "
            local settingsParts = {}
            for key, value in pairs(step.settings) do
                table.insert(settingsParts, key .. "=" .. value)
            end
            settingsText = settingsText .. table.concat(settingsParts, ", ")
            
            table.insert(stepFrame.components[1].components[3].components, {
                type = "Label",
                text = settingsText,
                styleSheet = "font-size: 10px; color: #388e3c; padding-top: 2px; font-family: monospace;"
            })
        end
        
        -- Add naming convention for step 4 (AC3 Patch 11)
        if i == 4 and step.naming_convention then
            table.insert(stepFrame.components[1].components[3].components, {
                type = "Label",
                text = "🏷️ " .. step.naming_convention,
                styleSheet = "font-size: 10px; color: #1565c0; padding-top: 6px; font-weight: bold; background-color: #e3f2fd; padding: 4px; border-radius: 3px;"
            })
        end
        
        table.insert(stepsComponents, stepFrame)
    end
    
    -- Add separator
    table.insert(stepsComponents, {
        type = "Frame",
        styleSheet = "background-color: #ddd; height: 1px; margin: 10px 20px;"
    })
    
    -- Best practices section
    local bestPractices = guide.best_practices or {}
    if #bestPractices > 0 then
        local practicesText = "📋 Best Practices:\n• " .. table.concat(bestPractices, "\n• ")
        table.insert(stepsComponents, {
            type = "Frame",
            styleSheet = "background-color: #e8f5e9; border: 1px solid #81c784; border-radius: 3px; padding: 10px; margin: 8px 15px;",
            components = {
                {
                    type = "Label",
                    text = practicesText,
                    styleSheet = "font-size: 10px; color: #2e7d32;"
                }
            }
        })
    end
    
    -- Action buttons
    table.insert(stepsComponents, {
        type = "Layout",
        layout = "Horizontal",
        styleSheet = "padding: 15px;",
        components = {
            {
                type = "Button",
                id = "closeGuideButton",
                text = "← Back to Options",
                onClicked = function()
                    ErrorRecovery.closeGuideDialog()
                    ErrorRecovery.showErrorRecoveryDialog(ErrorRecovery.qualityData, ErrorRecovery.currentClip)
                end
            },
            {
                type = "Stretch"
            },
            {
                type = "Button",
                id = "retryCleanedButton",
                text = "✓ I've Cleaned Audio - Retry →",
                styleSheet = "background-color: #4caf50; color: white; font-weight: bold; padding: 10px 20px;",
                onClicked = function()
                    ErrorRecovery.onRetryWithCleanedClipClicked()
                end
            }
        }
    })
    
    -- Create dialog
    local guideDialog = {
        title = "Audio Cleanup Guide - RoughCut",
        width = 800,
        height = 700,
        modal = true,
        components = stepsComponents
    }
    
    ErrorRecovery.guideDialog = guideDialog
    
    -- Load previous progress (if any)
    ErrorRecovery.loadGuideProgress()
    
    -- Show dialog (Resolve-specific implementation would go here)
    print("[RoughCut] Showing audio cleanup guide with " .. #steps .. " steps")
end


--[[
    Called when a step checkbox is clicked.
    Updates progress and visual indicators, and persists state.
    
    Args:
        stepNumber: The step number that was checked
--]]
function ErrorRecovery.onStepChecked(stepNumber)
    print("[RoughCut] Step " .. stepNumber .. " marked as complete")
    
    -- Persist checkbox state
    local progress = {}
    local totalSteps = #(ErrorRecovery.cleanupGuide.steps or {})
    
    for i = 1, totalSteps do
        local checkbox = ErrorRecovery.getGuideComponent("step" .. i .. "CheckBox")
        if checkbox then
            progress[i] = checkbox:IsChecked()
        end
    end
    
    -- Save progress to backend
    ErrorRecovery.saveGuideProgress(progress)
    
    -- Update progress bar
    local progressBar = ErrorRecovery.getGuideComponent("guideProgressBar")
    if progressBar then
        -- Count checked boxes
        local completedSteps = 0
        
        for i = 1, totalSteps do
            if progress[i] then
                completedSteps = completedSteps + 1
            end
        end
        
        progressBar:SetValue(completedSteps)
        
        -- Visual feedback when all steps complete
        if completedSteps == totalSteps then
            print("[RoughCut] All cleanup steps completed!")
            local retryButton = ErrorRecovery.getGuideComponent("retryCleanedButton")
            if retryButton then
                retryButton:SetStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 10px 20px;")
            end
        end
    end
end


--[[
    Save guide progress to backend.
    
    Args:
        progress: Table with step number as key and boolean (checked state) as value
--]]
function ErrorRecovery.saveGuideProgress(progress)
    local request = {
        method = "save_cleanup_guide_progress",
        params = {
            progress = progress,
            clip_id = ErrorRecovery.currentClip and ErrorRecovery.currentClip.id or nil
        },
        id = ErrorRecovery.generateRequestId()
    }
    
    ErrorRecovery.sendToPython(request, function(response)
        if response.error then
            print("[RoughCut Warning] Failed to save guide progress: " .. tostring(response.error.message))
        else
            print("[RoughCut] Guide progress saved")
        end
    end)
end


--[[
    Load guide progress from backend and restore checkbox states.
--]]
function ErrorRecovery.loadGuideProgress()
    local request = {
        method = "get_cleanup_guide_progress",
        params = {
            clip_id = ErrorRecovery.currentClip and ErrorRecovery.currentClip.id or nil
        },
        id = ErrorRecovery.generateRequestId()
    }
    
    ErrorRecovery.sendToPython(request, function(response)
        if response.error then
            print("[RoughCut Warning] Failed to load guide progress: " .. tostring(response.error.message))
            return
        end
        
        local progress = response.result and response.result.progress
        if not progress then
            return
        end
        
        -- Restore checkbox states
        for stepNumber, isChecked in pairs(progress) do
            local checkbox = ErrorRecovery.getGuideComponent("step" .. stepNumber .. "CheckBox")
            if checkbox and isChecked then
                checkbox:SetChecked(true)
            end
        end
        
        -- Update progress bar
        local progressBar = ErrorRecovery.getGuideComponent("guideProgressBar")
        if progressBar then
            local completedSteps = 0
            for _, isChecked in pairs(progress) do
                if isChecked then
                    completedSteps = completedSteps + 1
                end
            end
            progressBar:SetValue(completedSteps)
            
            -- Visual feedback when all steps complete
            local totalSteps = #(ErrorRecovery.cleanupGuide.steps or {})
            if completedSteps == totalSteps then
                local retryButton = ErrorRecovery.getGuideComponent("retryCleanedButton")
                if retryButton then
                    retryButton:SetStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 10px 20px;")
                end
            end
        end
        
        print("[RoughCut] Guide progress restored")
    end)
end


--[[
    Called when "Retry with Cleaned Clip" button is clicked.
    Lists available cleaned clips and lets user select one.
--]]
function ErrorRecovery.onRetryWithCleanedClipClicked()
    -- First, close the guide dialog
    ErrorRecovery.closeGuideDialog()
    
    -- Find cleaned clips
    ErrorRecovery.findCleanedClips(function(cleanedClips)
        if cleanedClips and #cleanedClips > 0 then
            -- Show clip selection dialog
            ErrorRecovery.showCleanedClipSelectionDialog(cleanedClips)
        else
            -- No cleaned clips found - show error and alternative options
            local message = [[
No cleaned clips found in the Media Pool.

Possible reasons:
• Audio cleanup hasn't been performed yet
• Cleaned clip uses a different naming convention
• Cleaned clip hasn't been imported to Media Pool

Try:
1. Perform the cleanup steps first
2. Use "Render in Place" to automatically add to Media Pool
3. Manually import the cleaned clip to Media Pool

Or try "Retry with Different Clip" to select an alternative.]]
            
            ErrorRecovery.showMessageDialog("No Cleaned Clips Found", message)
        end
    end)
end


--[[
    Show dialog for selecting a cleaned clip from the list.
    
    Args:
        cleanedClips: Array of cleaned clip data
--]]
function ErrorRecovery.showCleanedClipSelectionDialog(cleanedClips)
    -- Build clip selection UI
    local clipItems = {}
    local allClips = {}
    
    -- Add original clip as first option (AC4 Patch 12)
    if ErrorRecovery.currentClip then
        table.insert(allClips, {
            clip_id = ErrorRecovery.currentClip.id,
            clip_name = ErrorRecovery.currentClip.name .. " (Original)",
            file_path = ErrorRecovery.currentClip.path,
            isOriginal = true
        })
    end
    
    -- Add cleaned clips
    for _, clip in ipairs(cleanedClips) do
        table.insert(allClips, clip)
    end
    
    for i, clip in ipairs(allClips) do
        local displayName = clip.clip_name or ("Clip " .. i)
        local radioStyle = ""
        
        -- Highlight original clip differently
        if clip.isOriginal then
            displayName = "🔸 " .. displayName .. " [Original]"
            radioStyle = "font-weight: bold;"
        end
        
        table.insert(clipItems, {
            type = "RadioButton",
            id = "clipRadio" .. i,
            text = displayName,
            group = "cleanedClipsGroup",
            styleSheet = radioStyle
        })
        
        table.insert(clipItems, {
            type = "Label",
            text = "   Path: " .. (clip.file_path or "Unknown"),
            styleSheet = "font-size: 10px; color: #666; padding-left: 20px;"
        })
        
        -- Add note for original clip
        if clip.isOriginal then
            table.insert(clipItems, {
                type = "Label",
                text = "   ⚠ Use original if cleanup didn't help",
                styleSheet = "font-size: 9px; color: #ff9800; padding-left: 20px; font-style: italic;"
            })
        end
    end
    
    local dialog = {
        title = "Select Cleaned Clip - RoughCut",
        width = 600,
        height = 450,
        modal = true,
        components = {
            {
                type = "Label",
                text = "Select a clip to retry transcription:",
                styleSheet = "font-weight: bold; font-size: 13px; padding: 15px;"
            },
            {
                type = "Frame",
                styleSheet = "border: 1px solid #ddd; border-radius: 5px; padding: 10px; margin: 10px;",
                components = clipItems
            },
            {
                type = "Layout",
                layout = "Horizontal",
                styleSheet = "padding: 15px;",
                components = {
                    {
                        type = "Button",
                        text = "← Back",
                        onClicked = function()
                            ErrorRecovery.closeClipSelectionDialog()
                            ErrorRecovery.showCleanupGuide()
                        end
                    },
                    {
                        type = "Stretch"
                    },
                    {
                        type = "Button",
                        id = "confirmClipButton",
                        text = "Select & Retry →",
                        styleSheet = "background-color: #4caf50; color: white; font-weight: bold;",
                        onClicked = function()
                            -- Find selected clip
                            local selectedClip = nil
                            for i, clip in ipairs(allClips) do
                                local radio = ErrorRecovery.getClipSelectionComponent("clipRadio" .. i)
                                if radio and radio:IsChecked() then
                                    selectedClip = clip
                                    break
                                end
                            end
                            
                            if selectedClip then
                                ErrorRecovery.retryWithSelectedClip(selectedClip)
                            else
                                ErrorRecovery.showErrorDialog("Please select a clip first")
                            end
                        end
                    }
                }
            }
        }
    }
    
    ErrorRecovery.clipSelectionDialog = dialog
    print("[RoughCut] Showing clip selection with " .. #cleanedClips .. " cleaned clips")
end


--[[
    Retry transcription with the selected cleaned clip.
    
    Args:
        selectedClip: The cleaned clip data to use
--]]
function ErrorRecovery.retryWithSelectedClip(selectedClip)
    if not selectedClip then
        ErrorRecovery.showErrorDialog("No clip selected")
        return
    end
    
    print("[RoughCut] Retrying with cleaned clip: " .. selectedClip.clip_name)
    
    -- Update current clip to the cleaned version
    ErrorRecovery.currentClip = {
        id = selectedClip.clip_id,
        name = selectedClip.clip_name,
        path = selectedClip.file_path
    }
    
    -- Exit recovery mode successfully
    ErrorRecovery.exitRecoveryMode(true)
    
    -- Close dialogs
    ErrorRecovery.closeClipSelectionDialog()
    
    -- Trigger transcription retrieval for new clip
    -- This will flow back through the normal workflow:
    -- retrieve_transcription → analyze_quality → quality_review
    local TranscriptViewer = require("transcript_viewer")
    TranscriptViewer.show(ErrorRecovery.currentClip)
end


-- ============================================================================
-- Backend Communication Functions
-- ============================================================================

--[[
    Enter recovery mode in Python backend.
    
    Args:
        clipData: Original clip data to store
--]]
function ErrorRecovery.enterRecoveryMode(clipData)
    local request = {
        method = "enter_recovery_mode",
        params = {
            original_clip = {
                clip_id = clipData.id,
                clip_name = clipData.name,
                file_path = clipData.path
            }
        },
        id = ErrorRecovery.generateRequestId()
    }
    
    ErrorRecovery.sendToPython(request, function(response)
        if response.error then
            print("[RoughCut Warning] Failed to enter recovery mode: " .. tostring(response.error.message))
        else
            ErrorRecovery.originalClip = clipData
            print("[RoughCut] Entered recovery mode for clip: " .. clipData.name)
        end
    end)
end


--[[
    Exit recovery mode in Python backend.
    
    Args:
        success: Whether the retry was successful
--]]
function ErrorRecovery.exitRecoveryMode(success)
    local request = {
        method = "exit_recovery_mode",
        params = {
            success = success or false
        },
        id = ErrorRecovery.generateRequestId()
    }
    
    ErrorRecovery.sendToPython(request, function(response)
        if response.error then
            print("[RoughCut Warning] Failed to exit recovery mode: " .. tostring(response.error.message))
        else
            ErrorRecovery.isInRecoveryMode = false
            print("[RoughCut] Exited recovery mode. Success: " .. tostring(success))
        end
    end)
end


--[[
    Abort the current session via Python backend.
    
    Args:
        callback: Function(success) called when abort completes
        preserveSelection: Whether to preserve clip selection (default: true)
--]]
function ErrorRecovery.abortSession(callback, preserveSelection)
    preserveSelection = preserveSelection ~= false  -- default true
    
    local request = {
        method = "abort_session",
        params = {
            preserve_clip_selection = preserveSelection
        },
        id = ErrorRecovery.generateRequestId()
    }
    
    ErrorRecovery.sendToPython(request, function(response)
        if response.error then
            print("[RoughCut Error] Abort failed: " .. tostring(response.error.message))
            if callback then callback(false) end
        else
            local success = response.result and response.result.aborted
            print("[RoughCut] Session aborted. Cleanup completed: " .. tostring(success))
            if callback then callback(success) end
        end
    end)
end


--[[
    Fetch cleanup guide content from Python backend.
    
    Args:
        callback: Function(guideData) called with guide content
--]]
function ErrorRecovery.fetchCleanupGuide(callback)
    local request = {
        method = "get_cleanup_guide",
        params = {},
        id = ErrorRecovery.generateRequestId()
    }
    
    ErrorRecovery.sendToPython(request, function(response)
        if response.error then
            print("[RoughCut Error] Failed to fetch guide: " .. tostring(response.error.message))
            if callback then callback(nil) end
        else
            local guide = response.result and response.result.guide
            if callback then callback(guide) end
        end
    end)
end


--[[
    Find cleaned clips matching the original in Python backend.
    
    Args:
        callback: Function(cleanedClips) called with array of cleaned clips
--]]
function ErrorRecovery.findCleanedClips(callback)
    if not ErrorRecovery.currentClip then
        if callback then callback({}) end
        return
    end
    
    local request = {
        method = "find_cleaned_clips",
        params = {
            original_clip_name = ErrorRecovery.currentClip.name,
            original_file_path = ErrorRecovery.currentClip.path,
            -- In production, Lua would fetch Media Pool clips and pass them here
            media_pool_clips = {}  -- Would be populated from Resolve API
        },
        id = ErrorRecovery.generateRequestId()
    }
    
    ErrorRecovery.sendToPython(request, function(response)
        if response.error then
            print("[RoughCut Error] Failed to find cleaned clips: " .. tostring(response.error.message))
            if callback then callback({}) end
        else
            local clips = response.result and response.result.cleaned_clips
            if callback then callback(clips or {}) end
        end
    end)
end


-- ============================================================================
-- Utility Functions
-- ============================================================================

-- Timeout configuration (seconds)
ErrorRecovery.REQUEST_TIMEOUT = 10  -- 10 second timeout for Python requests

--[[
    Send request to Python backend with timeout support.
    
    Args:
        request: Table containing method, params, and id
        callback: Function(response) to call when response received
        timeoutSeconds: Optional timeout override (defaults to REQUEST_TIMEOUT)
--]]
function ErrorRecovery.sendToPython(request, callback, timeoutSeconds)
    -- Store callback with timestamp for timeout tracking
    ErrorRecovery._pendingCallbacks = ErrorRecovery._pendingCallbacks or {}
    local timeout = timeoutSeconds or ErrorRecovery.REQUEST_TIMEOUT
    
    ErrorRecovery._pendingCallbacks[request.id] = {
        callback = callback,
        timestamp = os.time(),
        timeout = timeout
    }
    
    -- Start timeout timer
    ErrorRecovery.startTimeoutTimer(request.id, timeout)
    
    -- Convert to JSON and send via stdout
    local json = require("utils.json")
    local message = json.encode(request)
    io.write(message .. "\n")
    io.flush()
end


--[[
    Start a timeout timer for a request.
    
    Args:
        requestId: Request ID to track
        timeoutSeconds: Timeout duration
--]]
function ErrorRecovery.startTimeoutTimer(requestId, timeoutSeconds)
    -- In a real Resolve environment, we'd use QTimer or similar
    -- For now, store expected timeout time for later checking
    if ErrorRecovery._pendingCallbacks and ErrorRecovery._pendingCallbacks[requestId] then
        ErrorRecovery._pendingCallbacks[requestId].timeoutTime = os.time() + timeoutSeconds
    end
end


--[[
    Check for and handle timed out requests.
    Should be called periodically from the main loop.
--]]
function ErrorRecovery.checkTimeouts()
    if not ErrorRecovery._pendingCallbacks then
        return
    end
    
    local now = os.time()
    local timedOut = {}
    
    -- Find timed out requests
    for requestId, requestInfo in pairs(ErrorRecovery._pendingCallbacks) do
        if requestInfo.timeoutTime and now > requestInfo.timeoutTime then
            table.insert(timedOut, requestId)
        end
    end
    
    -- Handle timeouts
    for _, requestId in ipairs(timedOut) do
        local requestInfo = ErrorRecovery._pendingCallbacks[requestId]
        if requestInfo and requestInfo.callback then
            -- Call callback with timeout error
            requestInfo.callback({
                error = {
                    code = 'REQUEST_TIMEOUT',
                    message = 'Request timed out waiting for Python backend',
                    recoverable = true,
                    suggestion = 'Check that RoughCut backend is running'
                }
            })
        end
        ErrorRecovery._pendingCallbacks[requestId] = nil
    end
end


--[[
    Handle incoming response from Python backend.
    
    Args:
        response: Table containing response data
--]]
function ErrorRecovery.handleResponse(response)
    if not response.id then
        return
    end
    
    local requestInfo = ErrorRecovery._pendingCallbacks and ErrorRecovery._pendingCallbacks[response.id]
    if requestInfo and requestInfo.callback then
        requestInfo.callback(response)
        ErrorRecovery._pendingCallbacks[response.id] = nil
    end
end


--[[
    Generate unique request ID.
    
    Returns:
        id: Unique request ID string
--]]
function ErrorRecovery.generateRequestId()
    return string.format("err_rec_%d_%d", os.time(), math.random(1000, 9999))
end


--[[
    Get component from current dialog.
    
    Args:
        id: Component ID string
        
    Returns:
        component: UI component or nil
--]]
function ErrorRecovery.getComponent(id)
    if not ErrorRecovery.currentDialog then
        return nil
    end
    return ErrorRecovery.currentDialog.components[id]
end


--[[
    Get component from guide dialog.
    
    Args:
        id: Component ID string
        
    Returns:
        component: UI component or nil
--]]
function ErrorRecovery.getGuideComponent(id)
    if not ErrorRecovery.guideDialog then
        return nil
    end
    return ErrorRecovery.guideDialog.components[id]
end


--[[
    Get component from clip selection dialog.
    
    Args:
        id: Component ID string
        
    Returns:
        component: UI component or nil
--]]
function ErrorRecovery.getClipSelectionComponent(id)
    if not ErrorRecovery.clipSelectionDialog then
        return nil
    end
    return ErrorRecovery.clipSelectionDialog.components[id]
end


--[[
    Close the recovery dialog.
--]]
function ErrorRecovery.close()
    ErrorRecovery.currentDialog = nil
    ErrorRecovery.currentClip = nil
    ErrorRecovery.qualityData = nil
end


--[[
    Close the guide dialog.
--]]
function ErrorRecovery.closeGuideDialog()
    ErrorRecovery.guideDialog = nil
end


--[[
    Close the clip selection dialog.
--]]
function ErrorRecovery.closeClipSelectionDialog()
    ErrorRecovery.clipSelectionDialog = nil
end


--[[
    Show error dialog.
    
    Args:
        message: Error message to display
--]]
function ErrorRecovery.showErrorDialog(message)
    print("[RoughCut Error] " .. message)
end


--[[
    Show confirmation dialog.
    
    Args:
        title: Dialog title
        message: Message to display
        isWarning: Whether this is a warning dialog
        
    Returns:
        confirmed: Boolean indicating user confirmed
--]]
function ErrorRecovery.showConfirmationDialog(title, message, isWarning)
    -- In production, this would show a native confirmation dialog
    -- For now, simulate confirmation
    print("[RoughCut] Confirmation: " .. title)
    print(message)
    -- Return true for now - in production would wait for user response
    return true
end


--[[
    Show message dialog.
    
    Args:
        title: Dialog title
        message: Message to display
--]]
function ErrorRecovery.showMessageDialog(title, message)
    print("[RoughCut] " .. title .. ": " .. message)
end


--[[
    Set callback for proceeding to format selection.
    
    Args:
        callback: Function(clipData, transcriptData, qualityData)
--]]
function ErrorRecovery.setOnProceedToFormatSelection(callback)
    ErrorRecovery.onProceedToFormatSelection = callback
end


--[[
    Set callback for when abort is completed and navigation to main window is needed.
    
    Args:
        callback: Function() called after successful abort to return to main window
--]]
function ErrorRecovery.setOnAbortCompleted(callback)
    ErrorRecovery.onAbortCompleted = callback
end


return ErrorRecovery
