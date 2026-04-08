---
status: done
created: 2026-04-07
completed: 2026-04-08
baseline_commit: HEAD
---

## Implementation Summary

✅ **All acceptance criteria completed:**

- **AC1:** Project structure with Electron + React + TypeScript established
- **AC2:** Three-panel layout implemented (Media Browser 320px, Timeline flex, Format Templates 280px)
- **AC3:** Visual design system applied with zinc dark theme, amber primary, violet secondary
- **AC4:** Media Browser panel with category tabs (Music/SFX/VFX), search, filter options
- **AC5:** Format Templates panel with three templates and Generate button
- **AC6:** Resolve connection status with green/amber/red indicators in header

✅ **DaVinci Resolve Integration:**

- **Lua Bridge:** Created `electron_bridge.lua` to launch Electron from Resolve Scripts
- **UI Detection:** `roughcut_main.lua` auto-detects Electron availability with fallback to native UI
- **Process Management:** Uses existing `process.lua` utilities to spawn Electron as subprocess
- **Launch Flow:** Resolve → RoughCut.lua → roughcut_main.lua → Electron app

**Additional Features:**
- Command palette (⌘K) with asset search and action shortcuts
- ScrollArea components for smooth scrolling
- Tooltip components for filter buttons
- IPC bridge set up for Python/Resolve backend integration
- Integration documentation (`INTEGRATION.md`)

# Spec: RoughCut Electron UI Implementation

## Overview

Implement the RoughCut Electron desktop application UI based on the UX Design Specification (`_bmad-output/planning-artifacts/ux-design-specification.md`). Build a three-panel dark interface with shadcn/ui components that enables video editors to browse 10,000+ media assets and generate AI-powered rough cuts.

## User Story

As a DaVinci Resolve editor, I want to browse my media library in a modern Electron app with instant search, visual previews, and one-click rough cut generation — so that I can finally use the 10,000+ assets I've purchased instead of letting them sit dormant.

## Acceptance Criteria

### AC1: Project Setup
**Given** a fresh development environment  
**When** I run the setup commands  
**Then** I have:
- Electron + React + TypeScript project structure
- shadcn/ui initialized with zinc base color
- Tailwind CSS configured with dark mode
- Development server running without errors

### AC2: Three-Panel Layout Shell
**Given** the Electron app is running  
**When** I open the main window  
**Then** I see:
- Left sidebar (320px): Placeholder for Media Browser
- Center area (flex): Placeholder for Timeline Workspace  
- Right sidebar (280px): Placeholder for Format Templates
- Header with app title and Resolve connection status indicator
- Dark mode UI with zinc color scale

### AC3: Visual Design System Implementation
**Given** the app is running  
**When** I view any UI element  
**Then** all elements use:
- Colors from the zinc scale (#0a0a0f background, #fafafa foreground)
- Amber (#f59e0b) for primary actions
- Violet (#8b5cf6) for secondary/AI elements
- Resolve status colors (green/amber/red)
- Typography: Inter font family with defined type scale
- Spacing: 4px base grid system

### AC4: Media Browser Panel
**Given** the Media Browser panel is visible  
**When** I interact with it  
**Then** I see:
- Category tabs (Music, SFX, VFX) with shadcn Tabs component
- Search input with Command palette capability (⌘K shortcut)
- Filter options for Used/Unused/Favorites
- Virtualized grid placeholder for asset thumbnails
- ScrollArea for smooth scrolling with 10k+ items

### AC5: Format Templates Panel
**Given** the Format Templates panel is visible  
**When** I view it  
**Then** I see:
- Template cards with the three default templates (9:16 Social, 16:9 Story, 1:1 Highlight)
- Template preview placeholders showing structure
- Generate button (functional, not gated)

### AC6: Resolve Connection Status
**Given** the app is running  
**When** I look at the header  
**Then** I see:
- Resolve connection indicator showing current status
- Visual states: green (connected), amber (connecting), red (disconnected)
- Status updates without page refresh

## Technical Context

### Stack
- **Framework:** Electron + React + TypeScript
- **UI Library:** shadcn/ui (Radix UI + Tailwind CSS)
- **State Management:** React hooks (useState, useEffect)
- **Icons:** Lucide React (comes with shadcn)
- **Virtualization:** react-window (for 10k+ asset lists)

### Project Structure
```
roughcut-electron/
├── electron/
│   ├── main.ts              # Main process
│   └── preload.ts           # IPC preload script
├── src/
│   ├── components/
│   │   └── ui/              # shadcn components
│   ├── features/
│   │   ├── media-browser/
│   │   ├── timeline/
│   │   └── format-templates/
│   ├── lib/
│   │   └── utils.ts         # cn() utility
│   ├── App.tsx
│   └── index.css
├── index.html
├── package.json
├── tailwind.config.js
└── tsconfig.json
```

### Key Dependencies
- `electron`
- `react`, `react-dom`
- `typescript`
- `tailwindcss`
- `@radix-ui/*` (via shadcn)
- `lucide-react`
- `class-variance-authority`
- `clsx`, `tailwind-merge`

## Dependencies

### Files to Read
- `_bmad-output/planning-artifacts/ux-design-specification.md` - Complete UX design reference
- `roughcut/lua/ui/main_window.lua` - Current Lua UI reference

### Files to Create/Modify
1. `roughcut-electron/package.json` - Project configuration
2. `roughcut-electron/electron/main.ts` - Electron main process
3. `roughcut-electron/electron/preload.ts` - IPC bridge
4. `roughcut-electron/src/App.tsx` - Main React app
5. `roughcut-electron/src/index.css` - Tailwind + custom styles
6. `roughcut-electron/tailwind.config.js` - Theme configuration
7. `roughcut-electron/tsconfig.json` - TypeScript config
8. `roughcut-electron/index.html` - Entry HTML
9. `roughcut-electron/src/components/ui/*` - shadcn components
10. `roughcut-electron/src/features/media-browser/MediaBrowser.tsx`
11. `roughcut-electron/src/features/timeline/TimelineWorkspace.tsx`
12. `roughcut-electron/src/features/format-templates/FormatTemplates.tsx`

## Implementation Steps

1. **Setup Phase:**
   - Initialize npm project with Electron + React + TypeScript
   - Install and configure shadcn/ui with zinc theme
   - Set up Tailwind with dark mode
   - Create Electron main and renderer processes

2. **Layout Phase:**
   - Build three-panel layout shell
   - Implement header with Resolve status
   - Create responsive behavior (collapsible sidebars)

3. **Components Phase:**
   - Install required shadcn components (Button, Card, Tabs, ScrollArea, Input, Badge, Tooltip, Skeleton)
   - Build Media Browser panel with tabs and search
   - Build Format Templates panel with cards
   - Create Timeline Workspace placeholder

4. **Styling Phase:**
   - Apply visual design system (colors, typography, spacing)
   - Implement dark mode as default
   - Add Resolve connection status indicators

## Testing Notes

- Verify app launches without console errors
- Confirm dark mode is active by default
- Test three-panel layout at various window sizes
- Verify ⌘K shortcut for Command palette
- Check Resolve status indicator color changes
- Ensure all shadcn components render correctly

## Deferred Work (Post-MVP)

- Backend integration (Python/Resolve communication)
- Actual media asset loading and indexing
- Real AI generation workflow
- Timeline canvas implementation (custom component)
- Virtualization for large asset lists
- Drag-and-drop functionality
- Settings and configuration UI

## Suggested Review Order

**DaVinci Resolve Integration**

- Electron bridge module launches Electron from Lua
  [`electron_bridge.lua:1`](../../roughcut/lua/ui/electron_bridge.lua#L1)

- Electron main window abstraction for Resolve integration
  [`electron_main_window.lua:1`](../../roughcut/lua/ui/electron_main_window.lua#L1)

- Main entry point with auto UI mode detection
  [`roughcut_main.lua:6`](../../roughcut/lua/roughcut_main.lua#L6)

- Integration documentation
  [`INTEGRATION.md:1`](../../roughcut-electron/INTEGRATION.md#L1)

**Command Palette Integration**

- Keyboard shortcut handler for ⌘K toggles palette visibility
  [`App.tsx:21`](../../roughcut-electron/src/App.tsx#L21)

- Search button in header opens command palette with keyboard hint
  [`App.tsx:74`](../../roughcut-electron/src/App.tsx#L74)

- CommandDialog with grouped items for Assets, Actions, and Settings
  [`App.tsx:99`](../../roughcut-electron/src/App.tsx#L99)

**UI Components**

- Command palette component using cmdk primitive
  [`command.tsx:1`](../../roughcut-electron/src/components/ui/command.tsx#L1)

- Dialog wrapper for modal presentation
  [`dialog.tsx:1`](../../roughcut-electron/src/components/ui/dialog.tsx#L1)

**Dependencies**

- Added cmdk for command palette functionality
  [`package.json:25`](../../roughcut-electron/package.json#L25)
