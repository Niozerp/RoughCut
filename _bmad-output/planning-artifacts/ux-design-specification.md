---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8, 9]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - docs/audio_cleanup_workflow.md
  - docs/audio_cleanup_guide.md
partyModeInsights:
  shadcnComponents:
    - Command (spotlight search for asset discovery)
    - Card (media browser with hover states)
    - Tabs (Music/SFX/VFX switching)
    - ScrollArea (large asset lists)
    - Dialog (template selection)
    - Sonner (completion toasts)
    - Skeleton (loading states)
    - Table (asset browser with virtualization)
    - Tooltip (contextual help)
  implementationNotes:
    - Use virtualization for 10k+ assets (react-window)
    - Three-panel layout: Media | Timeline | Templates
    - shadcn for UI chrome, custom canvas for timeline
    - Dark mode with zinc color scale
    - Toast notifications for dopamine hits
    - IPC wrapper for Python/Resolve communication
  emotionalComponents:
    - Command search creates joy of discovery
    - Card hover states whisper 'pick me'
    - Toast notifications deliver pride in productivity
    - Skeleton loading turns waiting into anticipation
    - Dark mode lets media breathe and shine
  - _bmad-output/planning-artifacts/prd.md
  - docs/audio_cleanup_workflow.md
  - docs/audio_cleanup_guide.md
---

# UX Design Specification - RoughCut Electron Redesign

**Author:** Niozerp
**Date:** 2026-04-07

---

## Executive Summary

### Project Vision

Transform RoughCut from a constrained Lua-based plugin UI trapped inside DaVinci Resolve into a modern, powerful Electron desktop application. The new UI will provide video editors with an intuitive, visually-rich interface for managing massive media asset libraries and generating AI-powered rough cuts—breaking free from the 400x500px window limitations and gated features of the current implementation.

The Electron redesign preserves the core value proposition (AI-powered asset matching and rough cut generation) while delivering a user experience that matches the creative potential of the underlying technology.

### Target Users

**Primary Persona:** Niozerp — Video editor and content creator with extensive purchased asset libraries

**User Characteristics:**
- Maintains organized media libraries (10,000+ assets across Music, SFX, VFX)
- Has invested thousands in assets that sit unused due to discovery friction
- Uses DaVinci Resolve as primary editing environment
- Values workflow efficiency and creative control
- Tech-savvy enough to install and configure desktop applications

**User Pain Points (Current Lua UI):**
- Tiny windows (400x500px) with limited visual information
- Media browser "gated until legacy dialog migrated"
- Format preview "gated while legacy window stack retired"
- Rough cut generation "intentionally gated"
- No visual asset discovery—just cycling through 3 hardcoded templates
- API instability requiring heavy defensive coding
- No drag-and-drop, limited interactivity

**User Goals:**
- Discover and use forgotten assets that perfectly match current projects
- Generate rough cuts from raw footage in minutes instead of hours
- Browse, search, and preview media assets at scale
- Visualize format templates and their structure before applying
- Seamlessly transfer AI-generated rough cuts to Resolve for refinement

### Key Design Challenges

1. **Bridging Two Worlds**
   - Electron app must communicate with DaVinci Resolve via Python backend
   - Users will context-switch between Resolve (editing) and Electron (asset management)
   - Need to maintain workflow continuity while providing richer UI capabilities

2. **Media Browser at Scale**
   - Handle 10,000+ assets (12,437 music, 8,291 SFX, 3,102 VFX in current libraries)
   - Smooth scrolling, filtering, searching without performance degradation
   - Support thumbnail previews, waveform visualization, video previews
   - Tag-based organization and AI-generated metadata display

3. **Progressive AI Workflow Visualization**
   - Rough cut generation involves multiple steps (transcript analysis → format matching → asset selection → timeline generation)
   - Users need clear progress indication and preview-before-commit capabilities
   - AI suggestions require review interface with accept/replace options

### Design Opportunities

1. **Visual Asset Discovery**
   - Transform "file browsing" into "creative exploration" with rich media previews
   - Grid layouts with thumbnail/waveform previews for instant recognition
   - Smart search with AI-powered tagging and filtering
   - "Forgotten gems" highlights—surfacing unused assets that match current context

2. **Format Template Visualization**
   - Replace text-based cycling with visual template previews
   - Timeline diagrams showing structure (intro → segments → outro)
   - Timing specifications with visual indicators
   - Suggested asset placements overlaid on template diagrams

3. **Modern Desktop Experience**
   - Responsive, resizable windows (no more 400x500px constraints!)
   - Dark mode aesthetic matching Resolve's environment
   - Keyboard shortcuts for power users
   - Drag-and-drop asset selection and ordering
   - Multi-window support for side-by-side asset comparison

4. **Seamless Resolve Integration**
   - One-click "Send to Resolve" for generated rough cuts
   - Real-time sync status indicators
   - Clear visual feedback on backend communication
   - Graceful handling of Resolve not running or API unavailable

---

## Core User Experience

### Defining Experience

RoughCut Electron is a **media asset command center** that lives alongside DaVinci Resolve. Users browse, search, and preview their massive media libraries in a rich visual interface, configure rough cut formats, and generate AI-powered timelines — then seamlessly transfer results to Resolve with one click.

The experience centers on **visual asset discovery at scale**: transforming the current pain of cycling through 3 hardcoded templates in a 400x500px window into an intuitive exploration of 10,000+ assets with instant search, filtering, and rich previews.

### Platform Strategy

**Platform:** Desktop application via Electron
- **Cross-platform:** macOS and Windows (matching DaVinci Resolve's platform support)
- **Primary Input:** Mouse and keyboard (desktop editing workflow)
- **Windowing:** Multi-window support for side-by-side asset comparison
- **Offline Support:** Full functionality for local asset management; cloud features (Notion sync, AI services) gracefully degrade when offline
- **Integration:** Persistent background connection to Python backend that communicates with Resolve

**Key Platform Decisions:**
- Electron provides modern web-tech UI capabilities while maintaining desktop-native feel
- Dark mode default to match Resolve's aesthetic and reduce eye strain during long editing sessions
- Keyboard shortcuts for power users (search, navigation, quick actions)
- Drag-and-drop throughout for intuitive asset manipulation

### Effortless Interactions

**Completely Effortless:**

1. **Instant Asset Search** — Type and see results immediately across 10,000+ files; no waiting, no loading spinners for basic queries
2. **Visual Browsing** — Scroll through media grids with thumbnails (video), waveforms (audio), and preview on hover; no clicking required to identify assets
3. **One-Click Resolve Handoff** — Generated rough cut appears in Resolve's Media Pool instantly; no export/import, no file management
4. **Automatic Sync Status** — App always knows if Resolve is connected, backend is responding, and sync is working; clear visual indicators, no guesswork

**Nearly Effortless:**

5. **Smart Filtering** — Click a tag, see related assets; AI-generated categories ("Upbeat Corporate", "Tension Building", "Fast-Paced") feel like magic
6. **Format Preview** — See template structure visually with timeline diagrams; understand pacing and placement before generating
7. **AI Generation Review** — Preview rough cut structure, asset placements, and timing before committing to timeline creation

### Critical Success Moments

**The First Open:**
User launches RoughCut Electron for the first time and sees their entire indexed media library displayed beautifully — organized, searchable, and immediately usable. The shock of "I had all this?!" followed by delight at how accessible it now is.

**The Discovery Moment:**
Searching for "corporate upbeat" and finding a music track purchased 18 months ago that's perfect for the current project. The emotional realization that their $15,000 asset investment is finally paying dividends.

**The Generation Moment:**
Clicking "Generate Rough Cut" and watching AI work through the transcript, match assets from THEIR library (not generic stock), and build a timeline structure in minutes. The transition from blank-page anxiety to "this is 80% done" relief.

**The Handoff Moment:**
Clicking "Send to Resolve" and seeing the rough cut appear instantly in Resolve's Media Pool, timeline populated with cut footage, layered audio, and positioned templates. Zero friction, zero file management.

**The Recovery Moment:**
When transcription quality is poor, clear visual indicators and a direct path to audio cleanup — no confusion about next steps, no hunting through documentation.

### Experience Principles

1. **Scale with Grace**
   — 10,000 assets should feel as browsable and responsive as 100. No lag, no stuttering, no "loading..." states for core interactions.

2. **Visual First**
   — Show, don't tell. Thumbnails, waveforms, timeline diagrams, and preview-on-hover eliminate the cognitive load of reading filenames and guessing content.

3. **Resolve-Aware**
   — The app always knows Resolve's state: connected/disconnected, which project is open, what media is in the pool. Display this context prominently and use it to guide actions.

4. **Progressive Disclosure**
   — Simple by default, powerful when needed. Basic users see clean asset grids and one-click actions; advanced users can access AI confidence scores, detailed format editing, and batch operations.

5. **Your Assets, Front and Center**
   — Every interaction reinforces that these are the user's own assets being intelligently organized. AI enhances, never replaces, the personal media library investment.

---

## Desired Emotional Response

### Primary Emotional Goals

RoughCut Electron should evoke **Creative Empowerment** as the dominant emotional experience. Users should feel their media library has transformed from a burdensome archive into an active creative partner that multiplies their productivity and rediscovers forgotten value.

**Core Emotions to Cultivate:**

1. **Joy of Discovery** — The delight of finding forgotten assets that perfectly match current projects
2. **Pride in Productivity** — Satisfaction in creating 3x more rough cuts per month with AI assistance
3. **Trust in AI Partnership** — Confidence that AI suggestions genuinely match (60%+ hit rate)
4. **Seamless Satisfaction** — Resolve handoff that just works, zero friction

### Emotional Journey Mapping

**First Discovery → First Open:**
Curiosity → Intrigue → Surprise (seeing all assets) → Delight (it's organized!) → Excitement (browsing is fun)

**Core Usage → Asset Browsing:**
Engagement → Discovery ("I forgot I had this!") → Confidence (finding perfect matches quickly)

**Generation Process:**
Anticipation → Fascination (watching AI work through transcript) → Satisfaction (results appear)

**Review & Refine:**
Critical analysis → Approval (80% there!) → Creative energy (time to polish)

**Handoff to Resolve:**
Seamless satisfaction → Pride (look what I made) → Readiness (let's finish this!)

**After Regular Use:**
Habitual confidence → Dependence (can't imagine workflow without it) → Evangelism (telling other editors)

### Micro-Emotions

**Positive States to Amplify:**

✅ **Confidence** — Fast search, clear results, reliable sync status indicators
✅ **Delight** — "Forgotten gems" highlights, smooth animations, visual polish
✅ **Trust** — AI confidence scores, explainable suggestions, preview-before-commit
✅ **Accomplishment** — Progress indicators, completion stats, "rough cut ready!" moments

**Negative States to Prevent:**

❌ **Confusion** — Unclear status, ambiguous icons, hidden functionality
❌ **Anxiety** — Long waits without feedback, fear of losing work, sync uncertainty
❌ **Frustration** — Slow performance at scale, failed handoffs, broken workflows
❌ **Overwhelm** — Cluttered UI, too many options, cognitive overload

### Design Implications

**shadcn/ui Component Emotional Connections:**

| Component | Emotional Role | UX Implementation |
|-----------|----------------|-------------------|
| **Command** | Joy of Discovery | Spotlight search that fades everything else into soft focus; instant results bloom onto screen |
| **Card** | Invitation | Hover states that gently lift and glow, whispering "pick me, use me" |
| **Sonner** | Pride & Delight | Toast notifications that deliver dopamine hits: "✨ Template applied" or "🎬 Rough cut generated" |
| **Skeleton** | Anticipation | Rhythmic pulsing that turns waiting into anticipation rather than frustration |
| **Dialog** | Control | Sleek, non-blocking but substantial; progressive disclosure via Accordion sections |
| **Tabs** | Organization | Smooth transitions between Music/SFX/VFX that feel like flipping through a portfolio |
| **Tooltip** | Guidance | Contextual help appearing precisely when needed, never patronizing |

**Dark Mode Emotional Foundation:**

- **Muted backgrounds** (#0a0a0f, zinc-950) let media *breathe* and *shine*
- **Zinc color scale** creates depth without harsh contrast—gentle on eyes during 3-hour editing sessions
- **Warm amber or electric violet accents** on interactive elements feel like spotlights guiding the creative journey
- **Button variants** tell interaction stories: `default` for "move forward", `outline` for "no pressure", `ghost` for "I'm here when you need me"

**Critical Success Moment Design:**

*The Discovery Moment:*
User searches "corporate upbeat" in Command palette. Results appear with Card previews—each hovering slightly, beckoning. They select a music track purchased 18 months ago that's perfect. Sonner notification: "🎵 Found: Corporate Upbeat — purchased 18 months ago." The emotional realization that their $15,000 asset investment is finally paying dividends.

### Emotional Design Principles

1. **Every Component is an Emotional Tool**
   — shadcn/ui components aren't just functional—they're emotional instruments. Command creates discovery joy, Cards create invitation, Toasts create pride.

2. **Visual Feedback is Emotional Feedback**
   — Skeleton states don't just indicate loading—they create anticipation. Hover states don't just show interactivity—they create desire.

3. **Dark Mode is Empowerment**
   — In creative tools, dark mode reduces eye strain during long sessions and creates a canvas where colorful media assets become the stars.

4. **Micro-Moments Matter**
   — The 200ms hover transition, the slide-in toast, the pulsing skeleton—these micro-interactions accumulate into macro-emotional experiences.

5. **Your Assets, Front and Center**
   — Every interaction reinforces that these are the user's own assets being intelligently organized. AI enhances, never replaces, the personal investment.

### Technical Implementation Notes (from Party Mode)

**shadcn/ui Architecture:**
- Use `npx shadcn@latest init --yes --template next --base-color zinc`
- Set `darkMode: 'class'` in tailwind.config.js
- Three-panel layout: Media Browser (320px) | Timeline (flex) | Templates (280px)
- Virtualization required for 10k+ assets (react-window with shadcn Table)
- IPC wrapper for Python/Resolve communication

**Performance-Emotion Connection:**
- Virtualization prevents frustration from lag
- Skeleton states prevent anxiety from blank screens
- Optimistic UI prevents doubt from slow operations

---

## Design System Foundation

### 1.1 Design System Choice

**shadcn/ui** — A collection of reusable, accessible, and composable React components built on top of Radix UI primitives and styled with Tailwind CSS.

### Rationale for Selection

**1. Aligns with Technology Stack**
- RoughCut Electron uses React in the renderer process
- shadcn/ui is React-native and works perfectly in Electron's Chromium environment
- Tailwind CSS integration matches modern frontend development patterns

**2. Supports Emotional Design Goals**
From Party Mode insights:
- **Command** component enables spotlight search for "Joy of Discovery"
- **Card** components with hover states create "Invitation" emotional response
- **Sonner** toasts deliver "Pride in Productivity" dopamine hits
- **Skeleton** states turn waiting into anticipation
- Dark mode with zinc color scale supports creative tool aesthetic

**3. Handles Scale Requirements**
- Components are lightweight and performant
- Virtualization-friendly (react-window works with shadcn Table)
- No vendor lock-in — components live in your codebase

**4. Matches Resolve's Aesthetic**
- Dark mode by default (zinc color scale)
- Professional, minimal UI that doesn't compete with colorful media assets
- Accessibility built-in (Radix UI primitives)

### Implementation Approach

**Setup:**
```bash
npx shadcn@latest init --yes --template next --base-color zinc
```

**Key Components for RoughCut:**
- `Command` — Spotlight search for asset discovery
- `Card` — Media browser items with hover states
- `Tabs` — Music/SFX/VFX category switching
- `ScrollArea` — Large asset lists with smooth scrolling
- `Dialog` — Template selection and configuration
- `Sonner` — Toast notifications for user feedback
- `Skeleton` — Loading states during indexing/generation
- `Table` — Asset browser with virtualization
- `Tooltip` — Contextual help without clutter
- `Button` — Action triggers with variants (default/outline/ghost)
- `Select`, `Input` — Form elements for configuration

**Architecture:**
- Three-panel layout: Media Browser (320px) | Timeline (flex) | Templates (280px)
- shadcn for UI chrome, custom canvas for timeline visualization
- IPC wrapper for Python/Resolve communication
- Virtualization for 10k+ asset handling

### Customization Strategy

**Theme Configuration:**
- `darkMode: 'class'` in tailwind.config.js
- Zinc color scale as foundation (#0a0a0f backgrounds)
- Amber or violet accents for interactive elements
- Custom color tokens for Resolve connection status

**Component Customization:**
- Barrel export from `components/ui/index.ts`
- Wrapper components for domain-specific behavior (AssetCard, ActionButton)
- Compound component patterns for toolbars and navigation

**Animation & Micro-interactions:**
- 200ms hover transitions on Cards
- Slide-in toasts with Sonner
- Rhythmic Skeleton pulsing
- Smooth Tab transitions

---

## 2. Core User Experience

### 2.1 Defining Experience

**Every button does exactly what it says when clicked.**

This is the fundamental promise of the Electron redesign. Unlike the current Lua UI where buttons are "gated" and show status text instead of performing actions, every interactive element in RoughCut Electron must execute its stated function immediately and reliably.

**Core Principle: Functional Integrity**
- If a button says "Browse Media" — it opens a working media browser
- If a button says "Generate Rough Cut" — it actually generates the rough cut
- If a button says "Send to Resolve" — the timeline appears in Resolve
- No "gated" features, no placeholder status messages, no broken workflows

### 2.2 User Mental Model

DaVinci Resolve editors have been burned by the current Lua UI:
- Click "Browse Media Pool" → see status text "Media Pool browser gated until its legacy dialog is migrated"
- Click "Generate" → see "Rough cut generation is intentionally gated"
- Click buttons expecting action → get disappointment

**Their new expectation with Electron:**
- Click = Action
- Click = Result
- Click = No surprises

Users expect desktop application reliability: buttons work, menus open, dialogs appear, and operations complete.

### 2.3 Success Criteria

**Button Functionality Success:**
1. **100% of buttons perform their stated function** — zero gated or non-functional UI elements
2. **Click-to-action time < 100ms** for local operations (opening dialogs, switching tabs)
3. **Clear progress indication** for async operations (indexing, generation, Resolve handoff)
4. **Graceful error handling** with recovery paths when operations fail
5. **No placeholder UI** — every element is fully implemented and functional

**Critical Success Indicators:**
- User clicks "Manage Media" → Media Management interface opens immediately
- User clicks "Re-index" → Indexing starts with progress feedback
- User clicks "Generate Rough Cut" → AI generation begins, status visible
- User clicks "Send to Resolve" → Timeline appears in Resolve's Media Pool

### 2.4 Novel vs. Established Patterns

**Established Patterns (What Users Expect):**
- Desktop application reliability — buttons work
- Standard Electron/React UI patterns — menus, dialogs, toolbars
- shadcn/ui component behavior — consistent, accessible interactions

**Novel Aspects (RoughCut-Specific):**
- Resolve integration — one-click handoff to external application
- AI-assisted asset matching — intelligent suggestions from user's own library
- Progressive generation workflow — real-time AI progress visualization

**Pattern Strategy:**
- Use established desktop UI patterns for all standard interactions
- Innovate only in the Resolve integration and AI generation workflows
- Users should feel "this is a real app" not "this is a prototype"

### 2.5 Experience Mechanics

**Button Click Mechanics:**

**1. Initiation:**
- User sees clearly labeled button with descriptive text
- Button is enabled (not disabled/gated)
- Hover state provides visual feedback (cursor change, slight lift)

**2. Interaction:**
- Click triggers immediate visual feedback (active state, ripple effect)
- For instant operations: UI updates immediately
- For async operations: Progress indicator appears within 100ms

**3. Feedback:**
- Success: Toast notification or UI state change confirms completion
- Progress: Skeleton, spinner, or progress bar shows ongoing work
- Error: Clear error message with recovery action, not silent failure

**4. Completion:**
- Operation completes and UI reflects new state
- For Resolve handoff: Visual confirmation that Resolve received data
- For generation: Preview available, ready for user review

**Example: "Generate Rough Cut" Button Flow**
```
User Clicks → Active state shown → Progress dialog opens → 
AI processing visible → Completion toast → Rough cut preview ready →
"Send to Resolve" button enabled
```

**Anti-Patterns to Avoid:**
- Buttons that show "coming soon" or "gated" messages
- Buttons that do nothing (silent failures)
- Buttons that open placeholder UIs
- Async operations without progress indication

---

## Visual Design Foundation

### Color System

**Base Theme: shadcn/ui Zinc with Custom Accents**

```css
/* Background hierarchy - Dark creative tool aesthetic */
--background: #0a0a0f      /* Deepest background - Resolve-like dark */
--foreground: #fafafa      /* Primary text - high contrast white */
--card: #18181b           /* Card backgrounds - subtle elevation */
--card-foreground: #fafafa
--popover: #18181b
--border: #27272a        /* Subtle borders - barely visible separators */
--input: #27272a         /* Input fields */
--ring: #f59e0b          /* Focus rings - amber accent */

/* Accent colors - Creative tool personality */
--primary: #f59e0b       /* Amber - warmth, creativity, golden hour vibes */
--primary-foreground: #0a0a0f  /* Dark text on amber */
--secondary: #8b5cf6     /* Violet - innovation, AI, premium feel */
--secondary-foreground: #fafafa /* White text on violet */

/* Semantic colors - Intuitive status indicators */
--destructive: #ef4444   /* Error - urgent attention needed */
--destructive-foreground: #fafafa
--success: #22c55e       /* Success - operation completed */
--success-foreground: #0a0a0f
--warning: #f97316       /* Warning - attention but not critical */
--warning-foreground: #0a0a0f
--info: #3b82f6          /* Info - neutral status */
--info-foreground: #fafafa

/* Resolve connection status - Traffic light system */
--resolve-connected: #22c55e     /* Green - ready to sync */
--resolve-connecting: #f59e0b    /* Amber - establishing connection */
--resolve-disconnected: #ef4444  /* Red - Resolve not running/API unavailable */

/* Muted variants for secondary information */
--muted: #27272a
--muted-foreground: #a1a1aa      /* Zinc-400 for secondary text */
--accent: #27272a
--accent-foreground: #fafafa
```

**Color Rationale:**
- **Zinc scale (#0a0a0f to #fafafa)** provides depth without harsh contrast - gentle on eyes during long editing sessions
- **Amber (#f59e0b)** as primary accent feels warm and creative, avoiding cold enterprise vibes
- **Violet (#8b5cf6)** represents AI/innovation, differentiating RoughCut from generic tools
- **Resolve status colors** follow traffic light convention (green/yellow/red) for immediate recognition

### Typography System

**Font Stack:**

```css
/* Primary: Inter - Clean, modern, highly readable */
--font-sans: 'Inter', system-ui, -apple-system, sans-serif;

/* Monospace: JetBrains Mono - Technical values, timestamps */
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
```

**Type Scale:**

```css
/* Size scale - 4px base grid */
--font-size-xs: 0.75rem;      /* 12px - timestamps, metadata, tags */
--font-size-sm: 0.875rem;     /* 14px - secondary text, labels, captions */
--font-size-base: 1rem;       /* 16px - body text, buttons, inputs */
--font-size-lg: 1.125rem;     /* 18px - emphasis, lead paragraphs */
--font-size-xl: 1.25rem;      /* 20px - section headers, card titles */
--font-size-2xl: 1.5rem;      /* 24px - dialog titles, major headers */
--font-size-3xl: 1.875rem;    /* 30px - page titles */
--font-size-4xl: 2.25rem;     /* 36px - hero text */

/* Weight scale */
--font-weight-normal: 400;    /* Body text */
--font-weight-medium: 500;    /* Buttons, labels, navigation */
--font-weight-semibold: 600;  /* Headers, emphasis */
--font-weight-bold: 700;      /* Major emphasis, stats */

/* Line height */
--leading-none: 1;            /* Headlines - tight */
--leading-tight: 1.25;        /* Headlines, buttons */
--leading-snug: 1.375;        /* Compact UI text */
--leading-normal: 1.5;        /* Body text - default */
--leading-relaxed: 1.625;     /* Long-form reading */
```

**Typography Usage Patterns:**

| Element | Size | Weight | Line Height | Usage |
|---------|------|--------|-------------|-------|
| Page Title | 3xl (30px) | Bold (700) | Tight (1.25) | App name, major sections |
| Dialog Title | 2xl (24px) | Semibold (600) | Tight (1.25) | Modal headers |
| Card Title | xl (20px) | Semibold (600) | Snug (1.375) | Asset names, template titles |
| Section Header | lg (18px) | Medium (500) | Snug (1.375) | Category labels, group headers |
| Body | base (16px) | Normal (400) | Normal (1.5) | Descriptions, content |
| Label | sm (14px) | Medium (500) | Snug (1.375) | Form labels, button text |
| Metadata | xs (12px) | Normal (400) | Snug (1.375) | Timestamps, file sizes, tags |
| Monospace | base (16px) | Normal (400) | Normal (1.5) | Timecodes, technical values |

### Spacing & Layout Foundation

**Base Spacing Unit: 4px**

```css
/* Spacing scale */
--space-0: 0;
--space-1: 0.25rem;    /* 4px  - icon padding, tight gaps */
--space-2: 0.5rem;     /* 8px  - compact spacing, icon+text */
--space-3: 0.75rem;    /* 12px - default small, tight cards */
--space-4: 1rem;       /* 16px - default, standard gaps */
--space-5: 1.25rem;    /* 20px - relaxed spacing */
--space-6: 1.5rem;     /* 24px - section gaps, card padding */
--space-8: 2rem;       /* 32px - major sections */
--space-10: 2.5rem;    /* 40px - large gaps */
--space-12: 3rem;      /* 48px - panels, major divisions */
--space-16: 4rem;       /* 64px - hero sections */
--space-20: 5rem;       /* 80px - page-level spacing */
--space-24: 6rem;       /* 96px - major page sections */
```

**Layout Dimensions:**

```css
/* Panel widths - Three-column layout */
--sidebar-width: 20rem;           /* 320px - Media Browser panel */
--templates-width: 17.5rem;       /* 280px - Format Templates panel */
--timeline-min-width: 40rem;      /* 640px - Minimum workspace area */
--timeline-max-width: none;       /* Flexible center column */

/* Heights */
--header-height: 3rem;            /* 48px - Top application bar */
--toolbar-height: 2.5rem;       /* 40px - Section toolbars */
--breadcrumb-height: 2rem;      /* 32px - Navigation breadcrumbs */
--footer-height: 2rem;          /* 32px - Status bar */

/* Component dimensions */
--button-height-sm: 2rem;       /* 32px - Small buttons */
--button-height-default: 2.5rem; /* 40px - Standard buttons */
--button-height-lg: 3rem;       /* 48px - Large/prominent buttons */
--input-height: 2.5rem;       /* 40px - Form inputs */
--card-padding: 1.5rem;         /* 24px - Card internal padding */
--dialog-padding: 1.5rem;       /* 24px - Dialog internal padding */
```

**Layout Principles:**

1. **Three-Panel Layout**
   - Left: Media Browser (320px fixed) - asset discovery
   - Center: Timeline Workspace (flex) - rough cut preview and editing
   - Right: Format Templates (280px fixed) - structure and generation

2. **Responsive Behavior**
   - Minimum window size: 1200x700px (supports all three panels)
   - Below 1200px: Collapse right panel to drawer/sheet
   - Below 900px: Collapse left panel, focus on workspace

3. **Spacing Philosophy**
   - Dense but breathable: Creative tools need information density
   - Consistent 4px base grid ensures alignment
   - White space reserved for media content, not UI chrome

### Accessibility Considerations

**Color Contrast:**
- Primary text (#fafafa) on background (#0a0a0f): **18.5:1** ✅ (WCAG AAA)
- Secondary text (#a1a1aa) on background: **8.2:1** ✅ (WCAG AA)
- Primary button (amber #f59e0b) on background: **10.1:1** ✅ (WCAG AAA)

**Focus Indicators:**
- All interactive elements have visible focus rings
- Focus ring color: --ring (#f59e0b) with 2px offset
- Keyboard navigation fully supported

**Touch Targets:**
- Minimum touch target: 44x44px (exceeds WCAG 2.1 AA)
- Buttons default to 40px height with padding
- Icon buttons use 32x32px containers

**Typography:**
- Minimum body text: 16px (base)
- Line height: 1.5 for comfortable reading
- No text smaller than 12px (xs) for UI elements

**Motion & Animation:**
- Respect `prefers-reduced-motion` media query
- Animations are subtle and purposeful (200ms transitions)
- No flashing or rapid color changes

---

## Design Direction Decision

### Design Directions Explored

Based on project requirements and previous decisions, the design direction is anchored in the **"Creative Command Center"** concept — a dense but breathable three-panel interface that puts the user's massive media library front and center while maintaining immediate access to format templates and rough cut generation workflows.

### Chosen Direction: Three-Panel Dark Interface

**Layout Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo] RoughCut              [Resolve Status]    [⚙️] [?] │ ← Header (48px)
├──────────┬───────────────────────────────┬────────────────┤
│          │                               │                │
│  MEDIA   │                               │   FORMAT       │
│  BROWSER │      TIMELINE WORKSPACE       │   TEMPLATES    │
│  (320px) │         (Flexible)            │   (280px)      │
│          │                               │                │
│  ┌────┐  │  ┌─────────────────────────┐  │  ┌──────────┐  │
│  │🔍  │  │  │                         │  │  │ 9:16     │  │
│  ├────┤  │  │    Rough Cut Preview    │  │  │ Social   │  │
│  │💿  │  │  │    + AI Suggestions     │  │  │ Vertical │  │
│  │🎵  │  │  │                         │  │  ├──────────┤  │
│  │🎬  │  │  │  [Play] [Scrubber]      │  │  │ 16:9     │  │
│  └────┘  │  │                         │  │  │ Story    │  │
│          │  └─────────────────────────┘  │  │ Cut      │  │
│ [Tabs]   │                               │  ├──────────┤  │
│ • Music  │  ┌─────────────────────────┐  │  │ 1:1      │  │
│ • SFX    │  │  Asset Suggestions      │  │  │ Highlight│  │
│ • VFX    │  │  ─────────────────────  │  │  └──────────┘  │
│          │  │ 🎵 Corporate Upbeat     │  │                │
│ [Filters]│  │ 🎵 Tension Building     │  │  [Generate]    │
│ • Used   │  │ 🔊 Whoosh Impact        │  │                │
│ • Unused │  │ 🎬 Lower Third Title    │  │                │
│ • Favs   │  └─────────────────────────┘  │                │
│          │                               │                │
└──────────┴───────────────────────────────┴────────────────┘
     ↑             ↑ (Main Focus)              ↑
   Browse      Preview & Generate            Structure
```

### Design Rationale

**1. Three-Panel Layout**
- **Left (Media Browser - 320px):** Asset discovery at scale — the core "Joy of Discovery" experience with virtualized grid, Command palette search, and AI-generated tag filtering
- **Center (Timeline Workspace - Flexible):** Preview rough cuts, review AI suggestions, main creative focus area with custom canvas and playback controls
- **Right (Format Templates - 280px):** Structure and generation controls — always accessible template gallery with timeline diagrams

**2. Dark Mode as Default**
- Matches DaVinci Resolve's aesthetic for seamless context switching between apps
- Media assets (thumbnails, waveforms, video previews) pop against dark zinc backgrounds (#0a0a0f)
- Reduced eye strain during long editing sessions (3+ hours typical)

**3. Dense but Breathable**
- Creative tools need information density — users have 10,000+ assets to browse efficiently
- 4px spacing grid ensures alignment without clutter
- Visual hierarchy through color (amber primary #f59e0b, violet secondary #8b5cf6) not just size

**4. Functional Button Guarantee**
- Every button performs its stated function (core requirement from Step 7)
- Clear visual states: enabled/disabled/loading/complete with immediate feedback
- Click-to-action time < 100ms for local operations

**5. shadcn/ui Component System**
- Professional, accessible components without vendor lock-in — components live in codebase
- Consistent interaction patterns across the app (Command, Card, Tabs, Dialog, Sonner, etc.)
- Easy to customize for RoughCut's specific creative tool needs

### Implementation Approach

**Phase 1: Layout Shell**
1. Three-panel responsive layout with collapsible sidebars
2. Header with Resolve connection status indicator (green/amber/red)
3. Navigation between main sections (Media, Formats, Generate)

**Phase 2: Media Browser**
1. Virtualized grid with thumbnails (video), waveforms (audio), icons (VFX)
2. Command palette search (⌘K) for instant asset discovery across 10k+ files
3. Filter sidebar with AI-generated tags ("Upbeat Corporate", "Tension Building", etc.)

**Phase 3: Timeline Workspace**
1. Custom canvas component for rough cut preview (not shadcn — specialized timeline view)
2. AI suggestions panel with accept/replace controls
3. Playback controls, scrubber, and timeline ruler

**Phase 4: Format Templates**
1. Template gallery with Card components showing visual previews
2. Timeline diagram showing structure (intro → segments → outro)
3. Generate button with progress feedback (Skeleton loading → completion toast)

**Phase 5: Resolve Integration**
1. Real-time connection status indicator in header
2. "Send to Resolve" button with immediate handoff to Media Pool
3. Error handling with retry options and clear status messages

---

<!-- UX design content continues in subsequent steps -->
