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

return ResolveAPI
