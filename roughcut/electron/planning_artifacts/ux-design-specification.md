---
stepsCompleted: [1, 2, 3]
inputDocuments: []
date: "2026-04-09"
---

# UX Design Specification: RoughCut Media Management

**Author:** Niozerp
**Date:** 2026-04-09

---

<!-- UX design content will be appended sequentially through collaborative workflow steps -->

## Core User Experience

### Defining Experience

**Primary User Flow:** Configure → Index → Browse

The media management experience centers on a simple three-stage mental model:
1. **Configure** — Tell RoughCut where your media lives (folder selection)
2. **Index** — Background process catalogs assets (with progress feedback)
3. **Browse** — Search and use real assets in the Music/SFX/VFX tabs

**Critical Success Interaction:** The transition from empty state to populated library must feel magical — one moment there's guidance, the next moment real files appear.

### Platform Strategy

- **Desktop-first (Electron)** — Native OS file dialogs via `dialog.showOpenDialog`
- **Compact sidebar UI** — All experiences must work within the 320px MediaBrowser width
- **Keyboard shortcuts** — ⌘K command palette integration already exists for "Configure Media Folders"
- **Dark theme consistency** — Use existing CSS custom properties (`--background`, `--primary`, `--muted`)

### Effortless Interactions

1. **Discoverable Empty States** — Each tab (Music/SFX/VFX) shows category-specific guidance with a clear "Manage Media" CTA
2. **One-Click Folder Addition** — Native folder picker with immediate visual confirmation
3. **Visual Indexing Feedback** — Subtle progress indicators during indexing, not blocking modals
4. **Persistent Configuration** — Folders remembered across sessions, assets load instantly on restart

### Critical Success Moments

| Moment | Success Criteria |
|--------|----------------|
| **First Open** | User sees clear empty state, not confusion |
| **First Folder Added** | Immediate visual confirmation + indexing status |
| **Assets Appear** | Real files populate the list, no placeholders |
| **Return Usage** | Previously configured folders persist and load instantly |

### Experience Principles

1. **Seamless Integration** — Media management feels native to the existing three-panel layout and shadcn/ui design system
2. **Contextual CTAs** — Empty states guide users with category-specific language ("Add your music library" vs generic "Manage media")
3. **Non-Blocking Progress** — Indexing happens in background; UI remains responsive
4. **Reversible Actions** — Users can add, remove, and re-index without fear of data loss
5. **Zero Placeholder Data** — No fake assets; only real content or purposeful empty states

---

## Executive Summary

### Project Vision

**RoughCut** is an Electron-based companion app for DaVinci Resolve that helps video editors manage and organize their media assets (Music, SFX, VFX) more efficiently. The immediate need is to replace placeholder/mock data with a real, functional media library system that allows users to **select parent folders** containing their media assets, which will then be indexed and made available in the appropriate panels.

### Target Users

Video editors and content creators who use DaVinci Resolve and need a streamlined way to:
- Access their existing media libraries (Music, Sound Effects, Visual Effects/Templates)
- Quickly find and preview assets during the editing process
- Maintain organized, categorized media collections

### Key Design Challenges

1. **Folder Selection UX** — Users need to select parent folders (not individual files) that contain categorized media. The UI must make it clear which folders are being indexed and what types of media they contain.

2. **Indexing State Communication** — Once folders are selected, an indexing process needs to run. Users need clear feedback on:
   - What's being indexed
   - Progress/completion status
   - Any errors or issues

3. **Empty State to Populated State Transition** — The transition from "no folders configured" (empty panels) to "actively indexed and showing real assets" needs to be smooth and informative.

4. **Multi-Category Management** — Music, SFX, and VFX may come from different folder structures. The management interface needs to handle all three categories clearly.

### Design Opportunities

1. **Intelligent Empty States** — Instead of blank panels or fake data, show helpful empty states that guide users to set up their media sources with clear CTAs.

2. **Visual Folder Mapping** — Show users exactly which folders are indexed for each category, making the mental model clear.

3. **Incremental Value** — Allow users to add/remove folders individually, seeing their library grow organically rather than an all-or-nothing setup.

4. **Seamless Integration** — The "Manage Media" flow should feel like a natural extension of the existing app, not a bolted-on settings panel.

