# Fusion/Resolve UI Manager Research Report

## Executive Summary

This report documents the proper way to access UI capabilities in DaVinci Resolve/Fusion Lua scripts, with a focus on the differences between Resolve and Fusion scripting contexts, particularly for scripts running in the Utility folder.

---

## 1. Understanding the Scripting Contexts

### Two Different Scripting Environments

DaVinci Resolve/Fusion has two distinct scripting contexts:

| Context | Location | Primary Object | Use Case |
|---------|----------|----------------|----------|
| **Resolve** | Edit/Color/Fairlight/Deliver pages | `resolve` | Timeline operations, media management |
| **Fusion** | Fusion page, Utility folder | `fu` / `fusion` | Compositing, VFX, general utilities |

### Global Objects Available

#### In Resolve Context (Edit/Color/etc pages):
```lua
local resolve = Resolve()  -- Returns Resolve application object
local projectManager = resolve:GetProjectManager()
-- resolve:GetUIManager() -- Available in Resolve 16+ with UI scripting support
```

#### In Fusion Context (Fusion page, Utility scripts):
```lua
local fu = fu  -- Global fu object (available automatically)
local fusion = fusion  -- Alternative reference to same object
-- fu.UIManager -- UI Manager for creating windows/dialogs
```

---

## 2. Key Differences: resolve:GetUIManager() vs fu.UIManager

### resolve:GetUIManager()
- **Availability**: DaVinci Resolve 16+ (Studio and Free versions)
- **Context**: Works in Resolve page scripts (Edit, Color, etc.)
- **Returns**: UIManager object for creating UI in Resolve context
- **Limitation**: NOT available in Fusion/Utility folder scripts

### fu.UIManager
- **Availability**: All Fusion/Resolve versions with Lua scripting
- **Context**: Works in Fusion page scripts and Utility folder scripts
- **Returns**: UIManager object for creating UI in Fusion context
- **Advantage**: Universally available in Fusion scripting environment

---

## 3. The Global `fu` Object

### What `fu` Provides

The global `fu` object is the Fusion application object that provides:

| Property/Method | Description |
|-----------------|-------------|
| `fu.UIManager` | UI Manager for creating windows, dialogs, and UI elements |
| `fu.Version` | Fusion version information |
| `fu.MapPath()` | Path mapping utilities |
| `fu.CreateTool()` | Create Fusion tools/nodes |
| `fu:GetCurrentComp()` | Get current composition |
| `fu:LoadComp()` | Load a composition file |
| `fu:SaveComp()` | Save a composition file |
| `fu:QueueAction()` | Queue actions for execution |
| `fu:ShowUI()` | Display UI elements |

### Example: Accessing fu in Utility Scripts

```lua
-- In Utility folder scripts, 'fu' is automatically available as a global
-- No need to call Resolve() or Fusion()

-- Access the UI Manager
local ui = fu.UIManager

-- Get version info
print("Fusion Version: " .. tostring(fu.Version))

-- Get current composition (may be nil in Utility context)
local comp = fu:GetCurrentComp()
if comp then
    print("Current comp: " .. tostring(comp:GetAttrs().COMPS_Name))
end
```

---

## 4. Checking UIManager Availability (Defensive Coding)

### Recommended Defensive Pattern

```lua
-- Safe UI Manager initialization
local ui = nil
local disp = nil

-- Try different methods to get UIManager
try
    -- Method 1: Check if fu.UIManager exists (Fusion/Utility context)
    if fu and fu.UIManager then
        ui = fu.UIManager
        disp = bmd.UIDispatcher(ui)
        print("UI Manager accessed via fu.UIManager")
    else
        -- Method 2: Try Resolve context (if in Resolve page)
        local resolve = Resolve()
        if resolve and resolve.GetUIManager then
            ui = resolve:GetUIManager()
            disp = bmd.UIDispatcher(ui)
            print("UI Manager accessed via resolve:GetUIManager()")
        end
    end
    
    if not ui then
        error("UIManager not available - cannot create UI")
    end
catch err
    print("Error initializing UI: " .. tostring(err))
    -- Handle gracefully - perhaps use console-only output
end
```

### Simplified Defensive Check

```lua
-- Quick check for UI availability
if not fu or not fu.UIManager then
    print("ERROR: UIManager not available. This script requires UI support.")
    return
end

local ui = fu.UIManager
local disp = bmd.UIDispatcher(ui)
```

### Version-Aware Check

```lua
-- Check if we're in the right environment
local function checkUIEnvironment()
    -- Check for fu object (Fusion/Utility context)
    if type(fu) == "userdata" and fu.UIManager then
        return true, "fu.UIManager"
    end
    
    -- Check for Resolve with UI support
    local resolve = Resolve()
    if resolve and type(resolve.GetUIManager) == "function" then
        return true, "resolve:GetUIManager()"
    end
    
    return false, "No UI manager available"
end

local hasUI, uiMethod = checkUIEnvironment()
if not hasUI then
    print("Warning: " .. uiMethod)
    -- Continue with non-UI operation or exit
    return
end

print("Using UI method: " .. uiMethod)
```

---

## 5. Working UI Examples for Utility Scripts

### Basic Window Creation

```lua
-- Place in: C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility

-- Get UI Manager (always use fu.UIManager in Utility scripts)
local ui = fu.UIManager
local disp = bmd.UIDispatcher(ui)

-- Check if UI is available
if not ui or not disp then
    print("ERROR: UI Manager not available")
    return
end

-- Create a simple window
local win = disp:AddWindow({
    ID = "MyUtilityWindow",
    WindowTitle = "Fusion Utility Tool",
    Geometry = { 100, 100, 400, 300 },
    
    ui:VGroup{
        ID = "root",
        ui:Label{
            ID = "title",
            Text = "Welcome to Fusion Utility Script",
            Weight = 0,
        },
        ui:TextEdit{
            ID = "info",
            Text = "This is a sample UI in the Utility folder.",
            ReadOnly = true,
            Weight = 1,
        },
        ui:Button{
            ID = "closeBtn",
            Text = "Close",
            Weight = 0,
        },
    },
})

-- Show the window
win:Show()

-- Keep script running (required for UI to remain visible)
disp:RunLoop()

-- Cleanup
win:Hide()
```

### Complete Working Example with Error Handling

```lua
--[[
    Utility Script: Sample UI Tool
    Location: .../Fusion/Scripts/Utility/SampleUI.lua
    
    Demonstrates proper UI Manager access in Utility folder scripts.
--]]

--==============================================================================
-- SECTION 1: Environment Check
--==============================================================================

-- Verify we're in a Fusion-compatible environment
if type(fu) ~= "userdata" then
    print("ERROR: This script must run in Fusion/Resolve with UI support")
    print("Current environment doesn't have 'fu' object")
    return
end

-- Check for UIManager
if not fu.UIManager then
    print("ERROR: UIManager not available in this Fusion version")
    return
end

-- Get version for compatibility checking
local fusionVersion = tonumber(fu.Version) or 0
print("Fusion Version: " .. tostring(fu.Version))

--==============================================================================
-- SECTION 2: UI Initialization
--==============================================================================

local ui = fu.UIManager
local disp = bmd.UIDispatcher(ui)

-- Verify UIDispatcher is available
if not disp then
    print("ERROR: UIDispatcher not available")
    return
end

--==============================================================================
-- SECTION 3: Window Creation
--==============================================================================

-- Define window layout
local windowLayout = {
    ID = "SampleUtilityTool",
    WindowTitle = "Fusion Utility - Sample Tool",
    Geometry = { 100, 100, 500, 400 },
    MinimumSize = { 400, 300 },
    
    ui:VGroup{
        ID = "mainLayout",
        Spacing = 10,
        Margins = { 10, 10, 10, 10 },
        
        -- Header
        ui:Label{
            ID = "header",
            Text = "Fusion Utility Script",
            Font = ui:Font{
                Family = "Arial",
                PixelSize = 16,
                Bold = true,
            },
            Alignment = {
                AlignHCenter = true,
                AlignVCenter = true,
            },
            Weight = 0,
        },
        
        -- Info text
        ui:TextEdit{
            ID = "infoText",
            Text = "This script demonstrates proper UI creation in the Utility folder.\n\n" ..
                   "Environment:\n" ..
                   "  - fu object: Available\n" ..
                   "  - fu.UIManager: " .. tostring(fu.UIManager ~= nil) .. "\n" ..
                   "  - Version: " .. tostring(fu.Version) .. "\n\n" ..
                   "The UI Manager was accessed via fu.UIManager",
            ReadOnly = true,
            Weight = 1,
        },
        
        -- Buttons
        ui:HGroup{
            ID = "buttonRow",
            Weight = 0,
            Spacing = 10,
            
            ui:Button{
                ID = "testBtn",
                Text = "Run Test",
                Weight = 1,
            },
            ui:Button{
                ID = "closeBtn",
                Text = "Close",
                Weight = 1,
            },
        },
    },
}

-- Create window
local win = disp:AddWindow(windowLayout)

if not win then
    print("ERROR: Failed to create window")
    return
end

--==============================================================================
-- SECTION 4: Event Handlers
--==============================================================================

-- Get references to UI elements
local testBtn = win:GetItems().testBtn
local closeBtn = win:GetItems().closeBtn
local infoText = win:GetItems().infoText

-- Test button handler
testBtn.Clicked = function()
    infoText:SetText(infoText:GetText() .. "\n\nTest button clicked at " .. os.date("%H:%M:%S"))
    print("Test button clicked")
end

-- Close button handler
closeBtn.Clicked = function()
    print("Closing window...")
    win:Hide()
    disp:Quit()
end

-- Window close handler
win.CloseRequested = function()
    win:Hide()
    disp:Quit()
end

--==============================================================================
-- SECTION 5: Display and Run
--==============================================================================

print("Showing UI window...")
win:Show()

-- Run the event loop (keeps window open)
disp:RunLoop()

print("Script completed")
```

---

## 6. Alternative Approaches When UI Isn't Available

### Fallback to Console Output

```lua
-- Check for UI, fall back to console if not available
local hasUI = fu and fu.UIManager

if hasUI then
    -- Create full UI
    createFullUI()
else
    -- Console-only mode
    print("========================================")
    print("UTILITY SCRIPT - Console Mode")
    print("========================================")
    print("UI Manager not available.")
    print("Operations will run in console mode.")
    print()
    
    -- Perform operations without UI
    performConsoleOperations()
end
```

### Using Native Dialogs (if available)

```lua
-- Some Fusion versions support native message boxes
local function showMessage(title, message)
    if fu and fu.ShowMessage then
        -- Use Fusion native dialog
        fu:ShowMessage(title, message)
    elseif fu and fu.UIManager then
        -- Create custom dialog with UIManager
        local ui = fu.UIManager
        local disp = bmd.UIDispatcher(ui)
        -- ... create and show dialog ...
    else
        -- Fall back to print
        print("[" .. title .. "] " .. message)
    end
end
```

### Conditional Feature Loading

```lua
-- Load UI features only if available
local uiFeatures = {}

if fu and fu.UIManager then
    uiFeatures.createDialog = function(config)
        -- Full UI implementation
        local ui = fu.UIManager
        local disp = bmd.UIDispatcher(ui)
        return disp:AddWindow(config)
    end
    
    uiFeatures.showMessage = function(title, msg)
        -- Show modal dialog
    end
else
    -- Stub implementations
    uiFeatures.createDialog = function(config)
        print("UI not available - cannot create dialog")
        return nil
    end
    
    uiFeatures.showMessage = function(title, msg)
        print("[" .. title .. "] " .. msg)
    end
end

-- Use uiFeatures throughout script
uiFeatures.showMessage("Info", "Script started")
```

---

## 7. Environment-Specific Considerations

### Folder-Specific Behavior

| Script Location | Context | UI Access Method |
|-----------------|---------|------------------|
| `Fusion/Scripts/Utility/` | Fusion | `fu.UIManager` |
| `Fusion/Scripts/Comp/` | Fusion (with active comp) | `fu.UIManager` |
| `Fusion/Scripts/Tool/` | Fusion (tool-specific) | `fu.UIManager` |
| `Fusion/Scripts/Edit/` | Resolve Edit page | `resolve:GetUIManager()` or `fu.UIManager` |
| `Fusion/Scripts/Color/` | Resolve Color page | `resolve:GetUIManager()` or `fu.UIManager` |
| Workspace Scripts | Varies | Check both methods |

### Platform Differences

```lua
-- Platform detection (Windows, Mac, Linux)
local function getPlatform()
    local pathSeparator = package.config:sub(1,1)
    if pathSeparator == "\\" then
        return "Windows"
    elseif pathSeparator == "/" then
        -- Could be Mac or Linux, check further
        local handle = io.popen("uname -s")
        if handle then
            local result = handle:read("*a")
            handle:close()
            if result:match("Darwin") then
                return "Mac"
            else
                return "Linux"
            end
        end
    end
    return "Unknown"
end

-- Platform-specific UI considerations
local platform = getPlatform()
print("Platform: " .. platform)

-- Some UI features may behave differently on different platforms
-- (e.g., font rendering, path separators, file dialogs)
```

### Resolve vs Fusion Studio Differences

```lua
-- Check if running in Resolve or Fusion Studio
local function getApplication()
    if fu and fu.Resolve then
        -- In Resolve
        return "Resolve"
    elseif fu then
        -- In Fusion Studio
        return "Fusion"
    end
    return "Unknown"
end

local app = getApplication()
print("Running in: " .. app)

-- Resolve may have different UI capabilities than Fusion
-- Always use defensive checks
```

---

## 8. Best Practices Summary

### DO:

1. ✅ Always check if `fu` object exists before using it
2. ✅ Use `fu.UIManager` in Utility/Comp/Tool scripts
3. ✅ Implement defensive coding with fallback behavior
4. ✅ Use `bmd.UIDispatcher()` to wrap the UI Manager
5. ✅ Call `disp:RunLoop()` to keep UI responsive
6. ✅ Handle window close events properly
7. ✅ Test in both Resolve and Fusion environments

### DON'T:

1. ❌ Don't use `resolve:GetUIManager()` in Fusion/Utility scripts
2. ❌ Don't assume UI is always available
3. ❌ Don't forget to call `disp:RunLoop()` or window won't show
4. ❌ Don't use UI operations in headless/render-only environments
5. ❌ Don't mix Resolve and Fusion UI contexts carelessly

---

## 9. Troubleshooting Common Issues

### Issue: "attempt to index a nil value (global 'fu')"

**Cause**: Script is running outside Fusion/Resolve context.

**Solution**:
```lua
if type(fu) ~= "userdata" then
    print("This script requires Fusion/Resolve")
    return
end
```

### Issue: "attempt to index field 'UIManager' (a nil value)"

**Cause**: UIManager not available in this environment.

**Solution**:
```lua
if not fu.UIManager then
    print("UI not available - using console mode")
    -- Implement console fallback
    return
end
```

### Issue: Window appears briefly then closes

**Cause**: Missing `disp:RunLoop()` or script ends too quickly.

**Solution**:
```lua
win:Show()
disp:RunLoop()  -- Required!
win:Hide()
```

### Issue: "resolve:GetUIManager() returns nil"

**Cause**: Using Resolve method in Fusion context, or Resolve version doesn't support UI.

**Solution**: Use `fu.UIManager` instead for Fusion/Utility scripts.

---

## 10. Quick Reference Card

```lua
-- Quick template for Utility folder scripts with UI

-- 1. Environment check
if not fu or not fu.UIManager then
    print("UI not available")
    return
end

-- 2. Initialize UI
local ui = fu.UIManager
local disp = bmd.UIDispatcher(ui)

-- 3. Create window
local win = disp:AddWindow({
    ID = "MyTool",
    WindowTitle = "My Tool",
    Geometry = { 100, 100, 400, 300 },
    
    ui:VGroup{
        ui:Label{ Text = "Hello from Utility!" },
        ui:Button{ ID = "btn", Text = "Click Me" },
    },
})

-- 4. Add handlers
win:GetItems().btn.Clicked = function()
    print("Button clicked!")
end

win.CloseRequested = function()
    disp:Quit()
end

-- 5. Show and run
win:Show()
disp:RunLoop()
win:Hide()
```

---

## Conclusion

For scripts running in the **Utility folder** (and other Fusion contexts):

1. **Always use `fu.UIManager`** - This is the correct and reliable method
2. **Don't use `resolve:GetUIManager()`** - This is for Resolve page scripts only
3. **The global `fu` object** provides all Fusion functionality including UI management
4. **Implement defensive checks** to handle environments where UI may not be available
5. **Use `bmd.UIDispatcher(ui)`** to properly wrap the UI Manager for event handling

The key insight is that Fusion/Utility scripts run in a different context than Resolve page scripts, and they have access to the global `fu` object which provides the `UIManager` directly.

---

*Report generated for: RoughCut - Resolve/Fusion Lua Scripting*
*Date: April 2026*
*Sources: Fusion 8 Scripting Guide, We Suck Less forum, GitHub community examples*
