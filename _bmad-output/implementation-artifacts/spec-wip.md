---
title: 'Media Management Modal'
type: 'feature'
created: '2026-04-09'
status: 'draft'
context: []
---

<!-- Target: 900–1300 tokens. Above 1600 = high risk of context rot.
     Never over-specify "how" — use boundaries + examples instead.
     Cohesive cross-layer stories (DB+BE+UI) stay in ONE file.
     IMPORTANT: Remove all HTML comments when filling this template. -->

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Media Browser panels (Music, SFX, VFX) currently display placeholder/mock data instead of real assets. Users cannot select their actual media folders or trigger indexing of their content.

**Approach:** Add a "Manage Media" button that opens a modal dialog for selecting parent folders per category (Music/SFX/VFX). Selected folders trigger an indexing process that populates the panels with real assets. Remove all placeholder data and replace with contextual empty states.

## Boundaries & Constraints

**Always:**
- Use native Electron `dialog.showOpenDialog` for folder selection
- Maintain existing dark theme styling (CSS custom properties)
- Keep changes within the 320px MediaBrowser sidebar width
- Use existing shadcn/ui components (Dialog, Button, Tabs)
- Follow existing IPC pattern: main.ts handler → preload.ts expose → window.electronAPI

**Ask First:**
- Adding external dependencies (database, state management library)
- Changing the three-panel layout dimensions
- Implementing automatic file watching/real-time updates
- Adding audio/video preview capabilities

**Never:**
- Modify files outside the media management scope (timeline, templates, header)
- Implement actual media file parsing/metadata extraction (mock indexing for now)
- Change existing Resolve connection functionality
- Add authentication or cloud sync features

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | User clicks "Manage Media" in empty state | Modal opens with category tabs and "Add Folder" buttons | N/A |
| HAPPY_PATH | User selects folder via native dialog | Folder path appears in list with category label | N/A |
| HAPPY_PATH | Folder added + index triggered | Modal closes, panel shows indexing progress then assets | N/A |
| ERROR_CASE | User cancels folder dialog | No change, modal remains open | Silent ignore |
| ERROR_CASE | Invalid/non-existent folder path | Error toast: "Folder not accessible" | Display error in modal |
| EDGE_CASE | Same folder added twice | Show warning: "Folder already indexed" | Prevent duplicate |
| EDGE_CASE | Folder with no media files | Show "0 assets found" with option to remove | Allow removal |

</frozen-after-approval>

## Code Map

- `electron/main.ts` -- Add IPC handler for folder selection dialog
- `electron/preload.ts` -- Expose selectFolder method to renderer via contextBridge
- `src/features/media-browser/MediaBrowser.tsx` -- Remove placeholder assets, add Manage Media button, integrate real data
- `src/components/ui/dialog.tsx` -- Use for media management modal (already exists)
- `src/main.tsx` -- TypeScript global declarations for window.electronAPI

## Tasks & Acceptance

**Execution:**
- [ ] `electron/main.ts` -- Add `media:select-folder` IPC handler using dialog.showOpenDialog -- Enable native folder selection from renderer
- [ ] `electron/preload.ts` -- Expose `selectFolder` method in electronAPI context bridge -- Secure IPC communication to main process
- [ ] `src/main.tsx` -- Update Window interface to include selectFolder type -- TypeScript support for new IPC method
- [ ] `src/features/media-browser/MediaBrowser.tsx` -- Remove placeholderAssets array, replace with empty state showing "Manage Media" CTA -- Eliminate mock data per user requirement
- [ ] `src/features/media-browser/MediaBrowser.tsx` -- Add "Manage Media" button visible when no folders configured -- Primary entry point for folder configuration
- [ ] `src/features/media-browser/MediaBrowser.tsx` -- Implement media management modal with Music/SFX/VFX tabs -- Organized folder management per category
- [ ] `src/features/media-browser/MediaBrowser.tsx` -- Add folder list display with remove buttons -- Allow users to see and manage indexed folders
- [ ] `src/features/media-browser/MediaBrowser.tsx` -- Integrate IPC call to selectFolder and handle response -- Connect UI to native dialog
- [ ] `src/features/media-browser/MediaBrowser.tsx` -- Add indexing state feedback (progress/success) -- User visibility into background process

**Acceptance Criteria:**
- Given Music/SFX/VFX panels with no configured folders, when user opens app, then panels show "Manage Media" button with contextual empty state (no placeholder assets)
- Given user clicks "Manage Media", when modal opens, then it displays three tabs (Music, SFX, VFX) with "Add Folder" buttons
- Given user clicks "Add Folder", when native dialog opens, then user can select a folder and path appears in the list
- Given folder is added, when user clicks "Start Indexing" or closes modal, then panel shows indexing progress and transitions to asset list
- Given placeholder assets existed before, when implementation completes, then no mock data remains in codebase
- Given user adds same folder twice, when duplicate detected, then UI prevents addition with clear feedback

## Spec Change Log

<!-- Append-only. Populated by step-04 during review loops. Do not modify or delete existing entries.
     Each entry records: what finding triggered the change, what was amended, what known-bad state
     the amendment avoids, and any KEEP instructions (what worked well and must survive re-derivation).
     Empty until the first bad_spec loopback. -->

## Design Notes

Empty state pattern:
```
[Icon: Music/FolderOpen]
No music library configured
[Button: Manage Media]
```

Modal layout:
```
[Header: Manage Media Folders]
[Tabs: Music | SFX | VFX]
[Folder List or Empty State]
[Button: + Add Folder]
[Footer: Index Status + Close]
```

## Verification

**Commands:**
- `cd roughcut/electron && npm run build` -- expected: No TypeScript errors
- `cd roughcut/electron && npm run dev` -- expected: App launches, UI renders correctly

**Manual checks:**
- Open Media Browser panel — verify no placeholder assets visible
- Click "Manage Media" — verify modal opens with three tabs
- Click "Add Folder" — verify native OS folder picker opens
- Select folder — verify path appears in list with correct category
- Verify indexing state displays (can be mocked progress for now)
- Close modal — verify panel shows appropriate state based on configuration
