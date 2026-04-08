-- RoughCut shared UI runtime
-- Creates one dispatcher-backed runtime for the post-install UI phase.

local runtime = {}

local function printError(message)
    print("RoughCut: Error - " .. tostring(message))
end

function runtime.isValid(context)
    return type(context) == "table" and context.ui ~= nil and context.disp ~= nil
end

function runtime.create(uiManager)
    if not uiManager then
        printError("UI Manager required for shared runtime")
        return nil
    end

    if not bmd or type(bmd.UIDispatcher) ~= "function" then
        printError("bmd.UIDispatcher not available for shared runtime")
        return nil
    end

    local ok, dispatcher = pcall(function()
        return bmd.UIDispatcher(uiManager)
    end)

    if not ok or not dispatcher then
        printError("Failed to create shared dispatcher: " .. tostring(dispatcher))
        return nil
    end

    return {
        ui = uiManager,
        disp = dispatcher
    }
end

function runtime.showMessage(context, title, message)
    if not runtime.isValid(context) then
        return false
    end

    local ok = pcall(function()
        if type(context.ui.ShowMessageBox) == "function" then
            context.ui:ShowMessageBox(tostring(message), tostring(title), "OK")
        end
    end)

    return ok
end

return runtime
