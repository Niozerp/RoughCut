# Research Report: DaVinci Resolve UIManager Access in Fusion/Utility Scripts

**Date:** 2026-04-05
**Research Type:** Technical Investigation
**Topic:** Correct method to access UIManager in DaVinci Resolve Lua scripting

---

## Executive Summary

The error "Could not access UI Manager" when using `resolve:GetUIManager()` occurs because **this is not the correct API method** for accessing the UI Manager in Fusion/Utility scripts. The correct approach is to use **`fu.UIManager`** (or alternatively `app.UIManager` or `fusion.UIManager`), which is the standard pattern used across all working Resolve Lua scripts.

---

## Key Findings

### 1. The Correct Method: `fu.UIManager`

Based on analysis of multiple working scripts from the Resolve community, the correct way to access the UIManager in Fusion/Utility scripts is:

```lua
local ui = fu.UIManager
local disp = bmd.UIDispatcher(ui)
```

### 2. Why `resolve:GetUIManager()` Fails

- **No evidence of this API existing**: Extensive searches of community scripts and documentation found **zero instances** of `resolve:GetUIManager()` being used successfully
- **Resolve object scope**: The `resolve` object (obtained via `Resolve()`) is primarily for project/timeline management, not UI operations in the Fusion context
- **Context mismatch**: The `resolve` object methods are focused on Edit/Color/Fairlight/Deliver page operations, not Fusion/Utility script UI

### 3. Alternative Valid Approaches

All three of these approaches work and are used in production scripts:

| Method | Usage Context | Availability |
|--------|--------------|--------------|
| `fu.UIManager` | Most common in Utility/Comp scripts | ✅ Fusion/Utility context |
| `app.UIManager` | Cross-platform (Fusion + Resolve) | ✅ All contexts |
| `fusion.UIManager` | Long form of `fu.UIManager` | ✅ All contexts |

### 4. Script Context Differences

| Script Location | UIManager Access | Notes |
|-----------------|-----------------|-------|
| `Fusion/Scripts/Utility` | `fu.UIManager` or `app.UIManager` | ✅ Works correctly |
| `Fusion/Scripts/Comp` | `fu.UIManager` or `app.UIManager` | ✅ Works correctly |
| Fusion page console | `fu.UIManager` | ✅ Works correctly |
| External Python/Lua via API | May use different patterns | Context-dependent |

---

## Working Code Examples

### Example 1: Basic UI Window (Utility Script Pattern)

From production scripts in the community:

```lua
-- Get the UIManager from the fu (fusion) object
local ui = fu.UIManager

-- Create a UIDispatcher for event handling
local disp = bmd.UIDispatcher(ui)

-- Create a window
local win = disp:AddWindow({
    ID = "MyDialog",
    WindowTitle = "My Resolve Script",
    Geometry = {100, 100, 400, 200},
    
    ui:VGroup{
        ID = "root",
        ui:Label{
            ID = "Label",
            Text = "Hello from Resolve Utility Script!",
        },
        ui:Button{
            ID = "CloseButton",
            Text = "Close",
        },
    },
})

-- Handle button click
function win.On.CloseButton.Clicked(ev)
    disp:ExitLoop()
end

-- Handle window close
function win.On.MyDialog.Close(ev)
    disp:ExitLoop()
end

-- Show window and run event loop
win:Show()
disp:RunLoop()
win:Hide()
```

### Example 2: Tree with Checkboxes (Comp Script)

From GitHub gist by 34j (working Comp script):

```lua
--Licensed under CC0 1.0 https://creativecommons.org/publicdomain/zero/1.0/
--Add this file to C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Comp

local ui = fu.UIManager
local disp = bmd.UIDispatcher(ui)

-- create a new window
local win = disp:AddWindow({
    ID = "Dialog",
    WindowTitle = "Generate Comp",
    ui:Tree {
        ID = "Tree",
        RootIsDecorated = false,
        Events = { CurrentItemChanged = true, ItemChanged = true, },
    }
})

local winItems = win:GetItems()
local tree = winItems.Tree

-- add TreeItems to the Tree
for i = 1, 50 do
    local treeItem = tree:NewItem()
    treeItem.Text[0] = "Item " .. i
    treeItem.CheckState[0] = "Checked"
    treeItem.Flags = {
        ItemIsSelectable = true,
        ItemIsEnabled = true,
        ItemIsUserCheckable = true,
    }
    treeItem:SetData(0, "UserRole", tostring(i))
    tree:AddTopLevelItem(treeItem)
end

-- print message when the checkboxes are clicked
function win.On.Tree.ItemChanged(ev)
    if ev.item then
        local id = ev.item:GetData(0, "UserRole")
        print("Item " .. id .. " " .. ev.item.CheckState[0])
    end
end

-- close the window
function win.On.Dialog.Close(ev)
    disp:ExitLoop()
end

-- show the window
win:Show()
disp:RunLoop()
win:Hide()
```

### Example 3: Utility Script with Dialog (Cross-Platform)

From Dmitriy Salnikov's "Copy Timecodes by Markers" script:

```lua
-- Location: %AppData%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility

local ui = fu.UIManager
local disp = bmd.UIDispatcher(ui)
local width, height = 550, 600

local win = disp:AddWindow({
    ID = 'CopyDialog',
    WindowTitle = 'Copy Timecodes by Markers',
    Geometry = {100, 100, width, height},
    Spacing = 0,
    Margin = 0,
    ui:VGroup{
        ID = 'root',
        ui:TextEdit{
            ID = 'TE',
            Weight = 0.5,
            HTML = [[<h1>Copy Timecodes by Markers</h1>]],
            ReadOnly = true
        }
    }
})

function win.On.CopyDialog.Close(ev) 
    disp:ExitLoop() 
end

win:Show()
disp:RunLoop()
win:Hide()
```

### Example 4: Using app.UIManager (Fusion + Resolve Compatible)

From Reactor Installer script (works in both Fusion and Resolve):

```lua
-- This script works in both Fusion Standalone and Resolve
function Main()
    -- Detect platform
    local platform = (FuPLATFORM_WINDOWS and "Windows") or 
                     (FuPLATFORM_MAC and "Mac") or 
                     (FuPLATFORM_LINUX and "Linux")
    
    -- Use app.UIManager for cross-compatibility
    ui = app.UIManager
    disp = bmd.UIDispatcher(ui)
    
    -- Create installer window
    InstallReactorWin()
end
```

---

## Reference: Standard UI Script Pattern

Every working UI script in Fusion/Utility context follows this pattern:

```lua
-- Step 1: Get the UI Manager
local ui = fu.UIManager  -- or app.UIManager, or fusion.UIManager

-- Step 2: Create a UIDispatcher
local disp = bmd.UIDispatcher(ui)

-- Step 3: Define your window
local win = disp:AddWindow({
    ID = "YourWindowID",
    WindowTitle = "Your Window Title",
    Geometry = {x, y, width, height},
    -- UI elements here
})

-- Step 4: Set up event handlers
function win.On.YourWindowID.Close(ev)
    disp:ExitLoop()
end

-- Step 5: Show and run
win:Show()
disp:RunLoop()
win:Hide()
```

---

## Common Pitfalls to Avoid

1. **❌ Don't use `resolve:GetUIManager()`** - This method doesn't exist in the documented API
2. **✅ Do use `fu.UIManager`** - The standard, proven approach
3. **✅ Always create a `bmd.UIDispatcher(ui)`** - Required for event handling
4. **✅ Always call `disp:RunLoop()`** - Required to process UI events
5. **✅ Always call `win:Hide()` after `RunLoop()`** - Clean up the window

---

## Source References

### Working Examples Found

1. **34j - "Tree With CheckBoxes.lua"** (GitHub Gist)
   - Location: Fusion/Scripts/Comp
   - Method: `fu.UIManager`
   - URL: https://gist.github.com/34j/48dc3590bc0b467b066dff76d2d4230f

2. **Dmitriy Salnikov - "Copy Timecodes by Markers.lua"** (GitHub Gist)
   - Location: Fusion/Scripts/Utility
   - Method: `fu.UIManager`
   - URL: https://gist.github.com/DmitriySalnikov/016648a478f668c48a0322e1051147ca

3. **TKSpectro - "renderCSStretched.lua"** (GitHub Gist)
   - Location: General Resolve scripting
   - Method: `app.UIManager`
   - URL: https://gist.github.com/TKSpectro/a1a212151a5116e2b8031848d460e53d

4. **G33kman - "Reactor-Installer.lua"** (GitHub Gist)
   - Location: Fusion/Resolve cross-platform
   - Method: `app.UIManager`
   - URL: https://gist.github.com/G33kman/7187c0669e8d4a3d3761da57b055c537

---

## Conclusion

**For Fusion/Utility scripts in DaVinci Resolve, use `fu.UIManager` (or `app.UIManager`) instead of `resolve:GetUIManager()`.**

The `resolve` object is designed for project and timeline manipulation, while the `fu` (fusion) or `app` objects provide access to the UI subsystem. All working community scripts consistently use `fu.UIManager` with `bmd.UIDispatcher()` for UI operations.

---

## Quick Fix for Your Script

If your current code looks like this:
```lua
-- ❌ WRONG
local resolve = Resolve()
local ui = resolve:GetUIManager()  -- This fails!
```

Change it to:
```lua
-- ✅ CORRECT
local ui = fu.UIManager
local disp = bmd.UIDispatcher(ui)
```

No need to call `Resolve()` for UI operations in Fusion/Utility scripts - the `fu` object is already available in the global context.
