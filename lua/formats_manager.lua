-- formats_manager.lua
-- Format template management UI for RoughCut
-- Includes asset groups display and preview matches functionality

local formats_manager = {}

-- Build asset groups display section for template preview
function formats_manager.buildAssetGroupsSection(parent, templateId)
    -- Query asset groups for this template
    local result = Protocol.request({
        method = "get_template_preview",
        params = { template_id = templateId }
    })
    
    if not result.result or not result.result.asset_groups then
        return nil  -- No asset groups defined
    end
    
    local groups = result.result.asset_groups
    
    -- Create section container
    local section = CreateGroupBox(parent, "Asset Groups")
    
    -- Group by category
    local byCategory = {
        music = {},
        sfx = {},
        vfx = {},
        transition = {}
    }
    
    for _, group in ipairs(groups) do
        local cat = group.category
        if byCategory[cat] then
            table.insert(byCategory[cat], group)
        end
    end
    
    -- Display each category
    for category, categoryGroups in pairs(byCategory) do
        if #categoryGroups > 0 then
            local catLabel = CreateLabel(section, string.upper(category))
            catLabel:SetStyleSheet("font-weight: bold; font-size: 14px;")
            
            for _, group in ipairs(categoryGroups) do
                local groupRow = CreateHorizontalLayout()
                
                -- Group info
                local nameLabel = CreateLabel(groupRow, group.name)
                nameLabel:SetStyleSheet("font-weight: bold;")
                
                local descLabel = CreateLabel(groupRow, group.description)
                descLabel:SetWordWrap(true)
                
                -- Tags display
                local tagsText = "Tags: " .. table.concat(group.required_tags, ", ")
                if #group.optional_tags > 0 then
                    tagsText = tagsText .. " (optional: " .. table.concat(group.optional_tags, ", ") .. ")"
                end
                local tagsLabel = CreateLabel(groupRow, tagsText)
                tagsLabel:SetStyleSheet("color: gray; font-size: 11px;")
                
                -- Duration hint if available
                if group.duration_hint and group.duration_hint.exact then
                    local durationText = "Duration: " .. group.duration_hint.exact .. "s"
                    local durationLabel = CreateLabel(groupRow, durationText)
                    durationLabel:SetStyleSheet("color: #666; font-size: 11px;")
                end
                
                -- "Preview Matches" button
                local previewBtn = CreateButton(groupRow, "Preview Matches")
                previewBtn.clicked = function()
                    formats_manager.showAssetMatchesDialog(templateId, group.name)
                end
                
                section:AddLayout(groupRow)
            end
        end
    end
    
    return section
end

-- Show dialog with matching assets for a group
function formats_manager.showAssetMatchesDialog(templateId, groupName)
    local dlg = CreateDialog("Matching Assets - " .. groupName)
    dlg:SetMinimumSize(600, 400)
    
    -- Query matches
    local result = Protocol.request({
        method = "match_assets_for_group",
        params = {
            template_id = templateId,
            group_name = groupName,
            limit = 5
        }
    })
    
    if result.error then
        ShowErrorDialog("Failed to load matches: " .. (result.error.message or "Unknown error"))
        return
    end
    
    local matches = result.result.matches
    
    if #matches == 0 then
        local msg = CreateLabel(dlg, "No matching assets found.\n\nConsider adding assets with these tags to your library.")
        msg:SetWordWrap(true)
    else
        -- Create scrollable list
        local scroll = CreateScrollArea(dlg)
        local container = CreateVerticalLayout(scroll)
        
        -- Display matches
        for i, match in ipairs(matches) do
            local matchRow = CreateHorizontalLayout()
            
            -- Rank number
            local rankLabel = CreateLabel(matchRow, tostring(i) .. ".")
            rankLabel:SetStyleSheet("font-weight: bold; font-size: 14px; width: 30px;")
            
            -- File name
            local nameLabel = CreateLabel(matchRow, match.file_name)
            nameLabel:SetStyleSheet("font-weight: bold;")
            
            -- Score with color coding
            local scorePercent = math.floor(match.score * 100)
            local scoreColor = scorePercent >= 80 and "green" or (scorePercent >= 60 and "orange" or "red")
            local scoreLabel = CreateLabel(matchRow, scorePercent .. "%")
            scoreLabel:SetStyleSheet("color: " .. scoreColor .. "; font-weight: bold;")
            
            -- Tags
            local tagsLabel = CreateLabel(matchRow, table.concat(match.tags, ", "))
            tagsLabel:SetStyleSheet("color: gray; font-size: 11px;")
            tagsLabel:SetWordWrap(true)
            
            -- Path (truncated)
            local pathLabel = CreateLabel(matchRow, match.file_path)
            pathLabel:SetStyleSheet("color: #666; font-size: 10px;")
            pathLabel:SetWordWrap(true)
            
            container:AddLayout(matchRow)
            
            -- Separator line
            if i < #matches then
                local separator = CreateFrame(container)
                separator:SetStyleSheet("background-color: #ddd; height: 1px;")
                separator:SetMinimumHeight(1)
                separator:SetMaximumHeight(1)
            end
        end
        
        -- Summary
        local summaryText = string.format("Showing %d of %d matches", #matches, result.result.total_matches)
        local summaryLabel = CreateLabel(dlg, summaryText)
        summaryLabel:SetStyleSheet("color: gray; font-size: 11px; padding: 10px;")
    end
    
    -- Close button
    local buttonRow = CreateHorizontalLayout()
    local closeBtn = CreateButton(buttonRow, "Close")
    closeBtn.clicked = function()
        dlg:Close()
    end
    
    dlg:AddLayout(buttonRow)
    dlg:Show()
end

-- Preview all asset groups matches for a template
function formats_manager.showAllMatchesDialog(templateId)
    local dlg = CreateDialog("Asset Matching Preview - All Groups")
    dlg:SetMinimumSize(700, 500)
    
    -- Query all matches
    local result = Protocol.request({
        method = "match_all_groups",
        params = {
            template_id = templateId,
            limit_per_group = 3
        }
    })
    
    if result.error then
        ShowErrorDialog("Failed to load matches: " .. (result.error.message or "Unknown error"))
        return
    end
    
    local groups = result.result.groups
    local totalGroups = result.result.total_groups
    
    if totalGroups == 0 then
        local msg = CreateLabel(dlg, "No asset groups defined for this template.")
        msg:SetWordWrap(true)
        dlg:Show()
        return
    end
    
    -- Create scrollable area
    local scroll = CreateScrollArea(dlg)
    local container = CreateVerticalLayout(scroll)
    
    -- Display each group's matches
    for groupName, matches in pairs(groups) do
        -- Group header
        local header = CreateLabel(container, groupName)
        header:SetStyleSheet("font-weight: bold; font-size: 16px; padding-top: 15px;")
        
        if #matches == 0 then
            local noMatchMsg = CreateLabel(container, "  No matching assets found")
            noMatchMsg:SetStyleSheet("color: orange; font-style: italic;")
        else
            -- Show top matches
            for i, match in ipairs(matches) do
                local matchText = string.format(
                    "  %d. %s (%d%%) - %s",
                    i,
                    match.file_name,
                    math.floor(match.score * 100),
                    table.concat(match.tags, ", ")
                )
                local matchLabel = CreateLabel(container, matchText)
                matchLabel:SetStyleSheet("font-size: 12px; padding-left: 20px;")
            end
        end
        
        -- Separator
        local separator = CreateFrame(container)
        separator:SetStyleSheet("background-color: #ddd; height: 1px;")
        separator:SetMinimumHeight(1)
        separator:SetMaximumHeight(1)
    end
    
    -- Summary
    local summaryLabel = CreateLabel(dlg, string.format("Total groups: %d", totalGroups))
    summaryLabel:SetStyleSheet("color: gray; font-size: 11px; padding: 10px;")
    
    -- Close button
    local buttonRow = CreateHorizontalLayout()
    local closeBtn = CreateButton(buttonRow, "Close")
    closeBtn.clicked = function()
        dlg:Close()
    end
    
    dlg:AddLayout(buttonRow)
    dlg:Show()
end

-- Enhanced template preview dialog with asset groups
function formats_manager.showEnhancedTemplatePreview(templateId)
    local dlg = CreateDialog("Template Preview")
    dlg:SetMinimumSize(800, 600)
    
    local mainLayout = CreateVerticalLayout(dlg)
    
    -- Get template preview
    local result = Protocol.request({
        method = "get_template_preview",
        params = { template_id = templateId }
    })
    
    if result.error then
        ShowErrorDialog("Failed to load template: " .. (result.error.message or "Unknown error"))
        return
    end
    
    local template = result.result
    
    -- Template header
    local headerLabel = CreateLabel(mainLayout, template.name or templateId)
    headerLabel:SetStyleSheet("font-weight: bold; font-size: 18px; padding-bottom: 10px;")
    
    -- Description
    if template.description and template.description ~= "" then
        local descLabel = CreateLabel(mainLayout, template.description)
        descLabel:SetWordWrap(true)
        descLabel:SetStyleSheet("padding-bottom: 15px;")
    end
    
    -- Asset groups section
    local groupsSection = formats_manager.buildAssetGroupsSection(mainLayout, templateId)
    if groupsSection then
        mainLayout:AddWidget(groupsSection)
    else
        local noGroupsLabel = CreateLabel(mainLayout, "No asset groups defined for this template.")
        noGroupsLabel:SetStyleSheet("color: gray; font-style: italic; padding: 20px;")
    end
    
    -- Preview all matches button
    local previewAllBtn = CreateButton(mainLayout, "Preview All Matches")
    previewAllBtn:SetStyleSheet("margin-top: 20px;")
    previewAllBtn.clicked = function()
        formats_manager.showAllMatchesDialog(templateId)
    end
    
    -- Close button
    local buttonRow = CreateHorizontalLayout()
    local closeBtn = CreateButton(buttonRow, "Close")
    closeBtn.clicked = function()
        dlg:Close()
    end
    
    mainLayout:AddLayout(buttonRow)
    dlg:Show()
end

return formats_manager
