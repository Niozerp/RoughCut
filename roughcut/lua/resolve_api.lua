--[[
    Resolve API Wrapper
    
    Provides a clean Lua interface to DaVinci Resolve's Media Pool API.
    This module handles all Resolve-specific operations and error handling.
    
    Usage:
        local ResolveAPI = require("resolve_api")
        local clips, err = ResolveAPI.getAllClips()
        if err then
            print("Error: " .. err)
        else
            for _, clip in ipairs(clips) do
                print(clip.name)
            end
        end
--]]

local ResolveAPI = {}

-- Error codes for consistent error handling
ResolveAPI.ERROR_CODES = {
    RESOLVE_NOT_RUNNING = "RESOLVE_NOT_RUNNING",
    NO_PROJECT_OPEN = "NO_PROJECT_OPEN",
    MEDIA_POOL_UNAVAILABLE = "MEDIA_POOL_UNAVAILABLE",
    FOLDER_ACCESS_FAILED = "FOLDER_ACCESS_FAILED"
}

--[[
    Get the Resolve application object.
    
    Returns:
        resolve: The Resolve application object, or nil if Resolve is not running
        error: Error message if Resolve is not available
--]]
function ResolveAPI.getResolve()
    local resolve = Resolve()
    if not resolve then
        return nil, ResolveAPI.ERROR_CODES.RESOLVE_NOT_RUNNING
    end
    return resolve, nil
end

--[[
    Get the current project from Resolve.
    
    Returns:
        project: The current Resolve project, or nil if no project is open
        error: Error message if project is not available
--]]
function ResolveAPI.getCurrentProject()
    local resolve, err = ResolveAPI.getResolve()
    if not resolve then
        return nil, err
    end
    
    local projectManager = resolve:GetProjectManager()
    if not projectManager then
        return nil, ResolveAPI.ERROR_CODES.NO_PROJECT_OPEN
    end
    
    local project = projectManager:GetCurrentProject()
    if not project then
        return nil, ResolveAPI.ERROR_CODES.NO_PROJECT_OPEN
    end
    
    return project, nil
end

--[[
    Get the name of the current project.
    
    Returns:
        projectName: String name of the current project, or nil if no project is open
        error: Error message if project is not available
--]]
function ResolveAPI.getCurrentProjectName()
    local project, err = ResolveAPI.getCurrentProject()
    if not project then
        return nil, err
    end
    
    local projectName = project:GetName()
    return projectName, nil
end

--[[
    Get the Media Pool from the current project.
    
    Returns:
        mediaPool: The MediaPool object, or nil if unavailable
        error: Error message if Media Pool cannot be accessed
--]]
function ResolveAPI.getMediaPool()
    local project, err = ResolveAPI.getCurrentProject()
    if not project then
        return nil, err
    end
    
    local mediaPool = project:GetMediaPool()
    if not mediaPool then
        return nil, ResolveAPI.ERROR_CODES.MEDIA_POOL_UNAVAILABLE
    end
    
    return mediaPool, nil
end

--[[
    Get the root folder of the Media Pool.
    
    Returns:
        rootFolder: The root MediaPoolFolder, or nil if unavailable
        error: Error message if folder cannot be accessed
--]]
function ResolveAPI.getRootFolder()
    local mediaPool, err = ResolveAPI.getMediaPool()
    if not mediaPool then
        return nil, err
    end
    
    local rootFolder = mediaPool:GetRootFolder()
    if not rootFolder then
        return nil, ResolveAPI.ERROR_CODES.FOLDER_ACCESS_FAILED
    end
    
    return rootFolder, nil
end

--[[
    Extract clip data from a Resolve MediaPool clip object.
    
    Args:
        clip: A Resolve MediaPool clip object
        
    Returns:
        table: Clip data containing name, path, duration, id, and type
--]]
function ResolveAPI._extractClipData(clip)
    if not clip then
        return nil
    end
    
    -- Resolve clip methods may return nil if property is unavailable
    local name = clip:GetName() or "Unknown"
    local path = clip:GetFilePath() or ""
    local duration = clip:GetDuration() or 0
    local id = clip:GetUniqueID() or ""
    local clipType = clip:GetType() or "unknown"
    
    -- Skip clips with invalid/empty paths (ECH-01 fix)
    if not path or path == "" then
        return nil
    end
    
    return {
        name = name,
        path = path,
        duration = duration,
        id = id,
        type = clipType
        -- Note: thumbnail not available in standard Resolve API
    }
end

--[[
    Recursively get all clips from a folder and its subfolders.
    
    Args:
        folder: A MediaPoolFolder object
        clips: (optional) Table to accumulate clips into
        
    Returns:
        clips: Table of clip data tables
--]]
function ResolveAPI._getClipsInFolderRecursive(folder, clips)
    clips = clips or {}
    
    if not folder then
        return clips
    end
    
    -- Get clips in current folder
    local folderClips = folder:GetClipList()
    if folderClips then
        for _, clip in ipairs(folderClips) do
            local clipData = ResolveAPI._extractClipData(clip)
            if clipData then
                table.insert(clips, clipData)
            end
        end
    end
    
    -- Recurse into subfolders (bins)
    local subfolders = folder:GetSubFolderList()
    if subfolders then
        for _, subfolder in ipairs(subfolders) do
            ResolveAPI._getClipsInFolderRecursive(subfolder, clips)
        end
    end
    
    return clips
end

--[[
    Get all clips from the Media Pool recursively.
    
    This traverses all folders (bins) in the Media Pool and returns
    all clips found.
    
    Returns:
        clips: Table of clip data tables, or empty table if none found
        error: Error message if operation failed
        
    Example clip data:
        {
            name = "interview_take1",
            path = "/projects/interview.mov",
            duration = 2280.5,
            id = "resolve_clip_001",
            type = "video"
        }
--]]
function ResolveAPI.getAllClips()
    local rootFolder, err = ResolveAPI.getRootFolder()
    if not rootFolder then
        return {}, err
    end
    
    local clips = ResolveAPI._getClipsInFolderRecursive(rootFolder, {})
    return clips, nil
end

--[[
    Get only video clips from the Media Pool.
    
    Filters out audio-only clips and still images.
    
    Returns:
        clips: Table of video clip data tables
        error: Error message if operation failed
--]]
function ResolveAPI.getVideoClips()
    local allClips, err = ResolveAPI.getAllClips()
    if err then
        return {}, err
    end
    
    local videoClips = {}
    for _, clip in ipairs(allClips) do
        local clipType = (clip.type or ""):lower()
        -- Check if it's a video type (includes "video" in type string)
        if clipType:find("video") then
            table.insert(videoClips, clip)
        end
    end
    
    return videoClips, nil
end

--[[
    Check if Resolve is running and a project is open.
    
    Returns:
        available: Boolean indicating if Resolve is ready
        error: Error message if not available
--]]
function ResolveAPI.isAvailable()
    local mediaPool, err = ResolveAPI.getMediaPool()
    return mediaPool ~= nil, err
end

--[[
    Get error message for error code.
    
    Args:
        errorCode: The error code string
        
    Returns:
        message: Human-readable error message
--]]
function ResolveAPI.getErrorMessage(errorCode)
    local messages = {
        [ResolveAPI.ERROR_CODES.RESOLVE_NOT_RUNNING] = "DaVinci Resolve is not running",
        [ResolveAPI.ERROR_CODES.NO_PROJECT_OPEN] = "No project is currently open in Resolve",
        [ResolveAPI.ERROR_CODES.MEDIA_POOL_UNAVAILABLE] = "Cannot access Media Pool",
        [ResolveAPI.ERROR_CODES.FOLDER_ACCESS_FAILED] = "Cannot access Media Pool folders"
    }
    
    return messages[errorCode] or "Unknown error: " .. tostring(errorCode)
end

--[[
    Get transcription data for a specific clip.
    
    Resolve 18+ stores transcription data as:
    1. Clip metadata (for clips transcribed in the Media Pool)
    2. Subtitle track data on timelines (for clips in timelines)
    
    Args:
        clipId: The unique clip ID from Resolve
        
    Returns:
        transcriptionData: Table containing:
            {
                text = "full transcript text",
                word_count = 5234,
                duration_seconds = 2280.5,
                has_speaker_labels = true,
                segments = {
                    {start_time=0.0, end_time=3.5, text="Hello", speaker="Speaker 1"},
                    ...
                }
            }
        error: Error message if transcription cannot be retrieved
--]]
function ResolveAPI.getTranscription(clipId)
    if not clipId or clipId == "" then
        return nil, "CLIP_ID_REQUIRED"
    end
    
    local mediaPool, err = ResolveAPI.getMediaPool()
    if not mediaPool then
        return nil, err
    end
    
    -- Try to find the clip by ID in the Media Pool
    local clip = ResolveAPI._findClipById(mediaPool:GetRootFolder(), clipId)
    if not clip then
        return nil, "CLIP_NOT_FOUND"
    end
    
    -- Method 1: Check clip metadata for transcription
    local metadata = clip:GetMetadata()
    if metadata and metadata["Transcription"] then
        -- Transcription stored in metadata
        return ResolveAPI._parseTranscriptionFromMetadata(metadata["Transcription"], clip:GetDuration())
    end
    
    -- Method 2: Check for transcription via timeline/subtitle tracks
    -- This requires the clip to be in a timeline with subtitle data
    local transcription = ResolveAPI._getTranscriptionFromTimeline(clip)
    if transcription then
        return transcription, nil
    end
    
    -- No transcription available
    return nil, "TRANSCRIPTION_NOT_AVAILABLE"
end

--[[
    Find a clip by ID recursively in the Media Pool.
    
    Args:
        folder: MediaPoolFolder to search
        clipId: Clip ID to find
        
    Returns:
        clip: The MediaPoolItem if found, nil otherwise
--]]
function ResolveAPI._findClipById(folder, clipId)
    if not folder or not clipId then
        return nil
    end
    
    -- Check clips in current folder
    local clips = folder:GetClipList()
    if clips then
        for _, clip in ipairs(clips) do
            if clip:GetUniqueID() == clipId then
                return clip
            end
        end
    end
    
    -- Recurse into subfolders
    local subfolders = folder:GetSubFolderList()
    if subfolders then
        for _, subfolder in ipairs(subfolders) do
            local found = ResolveAPI._findClipById(subfolder, clipId)
            if found then
                return found
            end
        end
    end
    
    return nil
end

--[[
    Parse transcription data from clip metadata string.
    
    Args:
        metadataStr: JSON or formatted string containing transcription
        duration: Total clip duration in seconds
        
    Returns:
        transcriptionData: Parsed transcription table
--]]
function ResolveAPI._parseTranscriptionFromMetadata(metadataStr, duration)
    -- Try to parse as JSON first
    local json = require("utils.json")
    local ok, data = pcall(json.decode, metadataStr)
    
    if ok and data then
        -- JSON format
        return {
            text = data.text or "",
            word_count = data.word_count or 0,
            duration_seconds = duration or 0,
            has_speaker_labels = data.has_speaker_labels or false,
            segments = data.segments or nil
        }
    end
    
    -- Plain text format - count words and create single segment
    local text = tostring(metadataStr)
    local wordCount = 0
    for _ in text:gmatch("%S+") do
        wordCount = wordCount + 1
    end
    
    return {
        text = text,
        word_count = wordCount,
        duration_seconds = duration or 0,
        has_speaker_labels = false,
        segments = nil
    }
end

--[[
    Get transcription from timeline subtitle tracks.
    
    This searches all timelines for instances of the clip and
    extracts subtitle track data if available.
    
    Args:
        clip: MediaPoolItem to find transcription for
        
    Returns:
        transcriptionData: Table with transcription data, or nil if not found
--]]
function ResolveAPI._getTranscriptionFromTimeline(clip)
    local project, err = ResolveAPI.getCurrentProject()
    if not project then
        return nil
    end
    
    local timelineCount = project:GetTimelineCount()
    if timelineCount == 0 then
        return nil
    end
    
    -- Search through all timelines
    for i = 1, timelineCount do
        local timeline = project:GetTimelineByIndex(i)
        if timeline then
            -- Check if this timeline contains the clip
            local transcription = ResolveAPI._extractSubtitlesFromTimeline(timeline, clip)
            if transcription then
                return transcription
            end
        end
    end
    
    return nil
end

--[[
    Extract subtitle data from a timeline for a specific clip.
    
    Args:
        timeline: Timeline object
        targetClip: MediaPoolItem to find subtitles for
        
    Returns:
        transcriptionData: Table with subtitle data, or nil
--]]
function ResolveAPI._extractSubtitlesFromTimeline(timeline, targetClip)
    if not timeline or not targetClip then
        return nil
    end
    
    local trackCount = timeline:GetTrackCount("subtitle")
    if trackCount == 0 then
        return nil
    end
    
    local targetClipName = targetClip:GetName()
    local allSegments = {}
    local fullText = {}
    local hasSpeakers = false
    
    -- Iterate through subtitle tracks
    for trackIndex = 1, trackCount do
        local itemCount = timeline:GetItemCountInTrack("subtitle", trackIndex)
        
        for itemIndex = 1, itemCount do
            local item = timeline:GetItemOnTrack("subtitle", trackIndex, itemIndex)
            if item then
                -- Check if this subtitle belongs to our target clip
                -- by comparing names or checking source clip reference
                local subtitleText = item:GetName() or ""
                local startFrame = item:GetStart()
                local endFrame = item:GetEnd()
                
                -- Convert frames to seconds (assuming 24fps as default)
                local fps = timeline:GetSetting("timelineFrameRate") or 24
                local startTime = startFrame / fps
                local endTime = endFrame / fps
                
                -- Check for speaker label in text
                local speaker = nil
                local text = subtitleText
                
                -- Pattern: "Speaker Name: Text" or "Speaker 1: Text"
                local speakerMatch = subtitleText:match("^([^:]+):%s*(.+)$")
                if speakerMatch then
                    speaker = speakerMatch:gsub("^%s*", ""):gsub("%s*$", "")
                    text = subtitleText:match(":%s*(.+)$")
                    hasSpeakers = true
                end
                
                table.insert(allSegments, {
                    start_time = startTime,
                    end_time = endTime,
                    text = text,
                    speaker = speaker
                })
                
                if speaker then
                    table.insert(fullText, speaker .. ": " .. text)
                else
                    table.insert(fullText, text)
                end
            end
        end
    end
    
    if #allSegments == 0 then
        return nil
    end
    
    -- Calculate word count
    local fullTextStr = table.concat(fullText, " ")
    local wordCount = 0
    for _ in fullTextStr:gmatch("%S+") do
        wordCount = wordCount + 1
    end
    
    -- Get total duration from last segment
    local totalDuration = 0
    if #allSegments > 0 then
        totalDuration = allSegments[#allSegments].end_time
    end
    
    return {
        text = fullTextStr,
        word_count = wordCount,
        duration_seconds = totalDuration,
        has_speaker_labels = hasSpeakers,
        segments = allSegments
    }
end

return ResolveAPI
