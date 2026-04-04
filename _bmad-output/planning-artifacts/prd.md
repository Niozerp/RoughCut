---
stepsCompleted: ["step-01-init", "step-02-discovery", "step-02b-vision", "step-02c-executive-summary", "step-03-success", "step-04-journeys", "step-05-domain", "step-06-innovation", "step-07-project-type", "step-08-scoping", "step-09-functional", "step-10-nonfunctional", "step-11-polish"]
inputDocuments: []
documentCounts:
  briefCount: 0
  researchCount: 0
  brainstormingCount: 0
  projectDocsCount: 0
classification:
  projectType: developer_tool
  domain: media_production
  complexity: medium
  projectContext: greenfield
  formFactor: hybrid_lua_python
workflowType: 'prd'
status: 'complete'
---

# Product Requirements Document - RoughCut

**Author:** Niozerp
**Date:** 2026-04-03

## Executive Summary

RoughCut is an AI-powered DaVinci Resolve plugin that transforms dormant media asset libraries into an intelligent creative partner. Targeting video editors and content creators who maintain large collections of purchased SFX, music, and templates, RoughCut eliminates the friction between owning assets and actually using them.

**Core Problem:** Content creators invest thousands of dollars in media assets (sound effects, music libraries, templates) that sit unused on storage servers because manual indexing and searching at scale is impractical. Additionally, valuable raw footage goes unedited because matching content to script templates requires tedious manual work.

**Solution:** A hybrid Lua/Python plugin that integrates directly into DaVinci Resolve's workflow. RoughCut automatically indexes local media folders with AI-powered tagging, matches assets contextually to script templates using AI analysis of transcripts, and generates rough-cut timelines populated with appropriate music, SFX, and template elements — all within Resolve's native interface.

**Target Users:** Video editors, content creators, and production teams who maintain organized asset libraries but lack practical mechanisms to leverage their full collection in daily editing workflows.

### What Makes This Special

**Unlocks Hidden Value:** RoughCut doesn't just organize assets — it understands them. By analyzing file names, folder paths, and leveraging AI context matching, the system suggests assets editors didn't even remember they owned, transforming a passive collection into an active creative resource.

**Contextual Intelligence:** Unlike simple search tools, RoughCut understands the emotional tone and pacing of script templates, matching appropriate SFX and music that enhance the narrative rather than just filling space.

**Seamless Integration:** Operates entirely within DaVinci Resolve's native workflow using a Lua GUI interface. No external applications, no context switching — editors receive intelligent suggestions and populate timelines without leaving their creative environment.

**Dual-Mode Operation:** Functions both as a standalone local tool for individual editors and optionally syncs asset databases to Notion for team collaboration and shared creative resources.

## Project Classification

- **Project Type:** Developer Tool (DaVinci Resolve Plugin/Script Hybrid)
- **Domain:** Media Production / Video Editing Workflow Automation  
- **Complexity:** Medium — Multiple API integrations (Notion, AI transcription, AI content analysis), file system indexing, timeline manipulation via Resolve API, hybrid Lua/Python architecture
- **Project Context:** Greenfield — New product development with no existing codebase dependencies
- **Technical Form Factor:** Hybrid Lua/Python architecture — Lua handles Resolve GUI and timeline operations, Python manages external API communications and AI processing

## Success Criteria

### User Success

**Primary Success Scenario:** Editor opens DaVinci Resolve, selects a transcribable video from the media pool, runs RoughCut, and receives an AI-generated rough cut with suggested music, SFX, and VFX — all placed on a new timeline ready for refinement.

**Emotional Success Moment:** Editor discovers and uses a previously forgotten purchased asset that perfectly matches the scene — realizing their asset library investment is finally paying off.

**Workflow Success:** Media indexing occurs only when new assets are added to folders, not as a constant background process. Editor maintains control over when the database updates.

**Completion Criteria:** Timeline contains imported suggested media, cut footage aligned to transcript sections per format template, layered sound effects for optimal timing, and background music with defined start/stop points.

### Business Success

**Phase 1 (Personal Validation):** Tool solves the creator's own asset utilization problem and rough cut workflow bottlenecks. ROI measured in time saved and dormant assets activated.

**Phase 2 (Commercial Potential):** If personal validation succeeds, evaluate market fit for distribution to other video editors facing similar asset management and rough cut automation challenges.

**Key Business Assumption:** The pain of unused asset libraries and manual rough cutting is widespread enough among Resolve users to support a commercial offering.

### Technical Success

**Core Integration:** Lua GUI seamlessly operates within Resolve's scripting environment. Python backend handles AI API communications, file system operations, and Notion synchronization.

**Performance Targets:** 
- Media indexing: <2 minutes for 100 new assets
- Rough cut generation: <5 minutes for 15-minute source video
- AI matching accuracy: 60%+ of suggested media usable without replacement

**Reliability Requirements:**
- Resolve transcription API integration stable
- Timeline creation and media import without crashes
- Notion sync functional for personal use, gracefully degrades when disabled

### Measurable Outcomes

| Metric | Current State | Target (3 months) | Target (12 months) |
|--------|--------------|-------------------|-------------------|
| Time: Raw footage → rough cut | 4-6 hours | 30 minutes | 20 minutes |
| Asset utilization rate | <5% of library | 25% of library | 40% of library |
| Projects per month | 2-3 rough cuts | 6-8 rough cuts | 10-12 rough cuts |
| AI suggestion acceptance | N/A | 60% usable | 75% usable |

**Success Validation:** If the creator uses RoughCut for 80% of rough cut projects within 3 months and asset utilization improves measurably, the tool validates its core value proposition.

## Product Scope

### MVP - Minimum Viable Product

**Core Workflow (Must Work):**
1. **Media Indexing:** Incremental folder scanning triggered manually when new assets added. Creates local database with file paths, names, and AI-generated tags.
2. **Resolve Integration:** Lua GUI prompts user to select video from media pool. Reads Resolve's native transcription data.
3. **Format Management:** User-managed video format documents (script templates) define cutting rules and media matching criteria.
4. **AI Processing:** Python backend sends transcript + format doc + media index to AI service. Returns cut segments with suggested music, SFX, VFX per segment.
5. **Timeline Generation:** Creates new Resolve timeline, imports suggested media from local folders, cuts footage per AI recommendations, layers sound effects for timing flexibility.
6. **Notion Sync:** Personal requirement — syncs media database to Notion page via API token. Optional in execution (can be disabled).

**Out of Scope for MVP:**
- Real-time AI matching as footage is captured
- Advanced audio mixing (levels, EQ, compression)
- Collaboration features for teams
- Cloud-based media storage
- Automatic asset purchasing/recommendations
- Mobile or web interface

**MVP Quality Threshold:** AI suggestions don't need to be perfect — 50-60% usability proves the concept. Editor is still required to review, replace, and refine. Tool's value is eliminating the blank-page problem and asset discovery, not final-edit automation.

### Growth Features (Post-MVP)

**Enhanced AI Matching:**
- Fine-tuned models trained on user's accepted/rejected suggestions
- Emotional tone analysis for better music/SFX matching
- Scene context understanding (intros, transitions, B-roll)

**Format Template System:**
- Template marketplace or sharing
- Custom template builder UI
- A/B testing different format approaches

**Workflow Improvements:**
- Batch processing multiple videos
- Integration with additional cloud storage (Dropbox, Google Drive)
- Resolve project template management
- Version control for rough cut iterations

**Team Features:**
- Shared Notion databases for production teams
- Comment and approval workflows
- Role-based access (editor vs reviewer)

### Vision (Future)

**Commercial Distribution:**
- Resolve plugin marketplace listing
- SaaS model with cloud-based AI processing
- Enterprise licensing for production houses

**Advanced Intelligence:**
- Automatic rough cut quality scoring
- Learning from editor's final cuts to improve future suggestions
- Predictive asset recommendations ("editors who used X also used Y")
- Integration with stock media APIs for gap filling

**Ecosystem Expansion:**
- Resolve plugin marketplace listing
- SaaS model with cloud-based AI processing
- Enterprise licensing for production houses
- Integration with Resolve Studio advanced features

## User Journeys

### Journey 1: The Primary Editor — Standard Rough Cut Creation

**Persona:** Niozerp, video editor and content creator with extensive purchased asset library

**Opening Scene:** It's 2:47 PM. You've got a raw interview from yesterday's shoot — 38 minutes of a CEO explaining their company pivot. You know there's a solid 4-minute story in there. Normally, you'd spend 3 hours: transcribing, scrubbing for soundbites, hunting through folders for the right music. Instead, you open DaVinci Resolve and launch RoughCut from the Scripts menu.

**The Home Screen:** No setup. No configuration. Your media folders are already indexed — 12,437 music tracks, 8,291 sound effects, 3,102 VFX templates. Your Notion sync is running silently in the background. The interface shows three clear options: Manage Media, Manage Formats, or Create Rough Cut. You click "Create."

**Media Selection:** RoughCut lists your Resolve Media Pool. You select yesterday's interview clip. The tool immediately pulls Resolve's native transcription. You see the transcript displayed clearly: clean, accurate, every word captured.

**Format Selection:** You select "YouTube Interview — Corporate" from your format list. The template details appear: 15-second hook with upbeat music, 3-minute narrative section with B-roll placeholders, 30-second outro with call-to-action. Template assets are listed — your standard corporate music bed, success chime SFX, lower third templates. This is exactly what you need.

**The AI Processing:** You click "Generate Rough Cut." RoughCut sends transcript + format template to the AI with strict instructions: cut transcript to match format structure, match music from indexed library, layer SFX for emotional beats, position VFX templates. The AI works through your 38 minutes in context-aware chunks.

**The Review:** 4 minutes later, RoughCut presents the rough cut document. The AI found three strong narrative beats and mapped them to your format's structure. It suggested a music track from your "corporate upbeat" folder — one you forgot you had, purchased 18 months ago. SFX list shows subtle audio cues: gentle whoosh for intro, underscore tone for the pivot challenge mention, standard outro chime. VFX placements show lower thirds at right timestamps.

**The Creation:** You review the AI's choices. The music is perfect. One SFX choice is slightly off — the AI suggested "tension" sound for the pivot moment, but this story is about triumph. You mentally note to swap it. You click "Create Timeline."

**The Resolution:** RoughCut imports suggested media from your server. Creates new timeline in Resolve. Interview is cut to format structure — three key beats flow naturally. Music fades in at 0:00, beds under narrative at 0:15, swells for outro at 3:45. SFX layered on separate tracks for easy volume adjustment. VFX templates positioned and ready. You hit play. Rough cut runs 4 minutes 12 seconds. Structure is there. Pacing works. The AI found and used assets you haven't touched in a year.

**The Outcome:** You glance at the clock: 3:09 PM. 22 minutes since you opened Resolve. You spend 10 minutes tweaking — swapping one SFX, adjusting music levels, refining outro timing. By 3:20, you have a client-ready rough cut that would have taken 3 hours manually. You used four assets from your forgotten collection. Your $15,000 investment just paid for another month of software subscriptions. This is your third rough cut this week.

---

### Journey 2: The Primary Editor — Error Recovery (Failed Transcription)

**Persona:** Niozerp, handling problematic audio footage

**The Scenario:** You select a clip from yesterday's location shoot — warehouse interview with a founder. RoughCut pulls the Resolve transcription and displays it: "Um, so, like... [inaudible]... the thing is... [garbled]... basically..." The transcript is 40% usable at best. Audio was recorded on lav mic with warehouse HVAC noise bleeding through.

**The Detection:** RoughCut clearly displays the garbage transcript with obvious quality issues. You're not left wondering why AI results would be nonsense.

**The Recovery Path:** You close RoughCut. Apply Resolve's audio noise reduction to the clip, render clean version, replace clip in Media Pool. Re-open RoughCut, select cleaned clip. This time transcription is crisp and accurate.

**The Lesson:** RoughCut's clear transcript preview saved you from wasting AI processing time and API credits on garbage input. You now know to always check warehouse footage audio quality before running the tool.

### Journey Requirements Summary

**Capabilities Required by Journeys:**

**Core Rough Cut Workflow:**
- Lua GUI integration with DaVinci Resolve scripting environment
- Resolve Media Pool browser and clip selection
- Resolve native transcription API access and display
- Local media database with indexed tags (music, SFX, VFX)
- Video format template system (markdown-based definitions)
- AI service integration for transcript cutting and media matching
- Timeline creation via Resolve API
- Media import and placement on timeline
- Multi-track audio layering (dialogue, music, SFX)
- VFX template positioning

**Setup & Configuration:**
- Parent folder selection UI for each media category
- File path display and validation
- Notion integration optional configuration (API token, page URL)
- Notion connection validation
- Incremental indexing with progress indication
- Blocking UI during indexing with status messaging

**Error Handling & Recovery:**
- Transcript quality display with clear visual indication
- User decision point for transcript acceptance/rejection
- Graceful exit for audio cleanup workflow
- Non-destructive operation (creates new timeline, doesn't modify source)

**Management Functions:**
- Media folder management (view paths, trigger re-index)
- Video format template management (view, select, preview structure)
- Default format templates loaded from markdown files
- Template asset group definitions (predefined assets for specific format moments)

## Innovation & Novel Patterns

### Detected Innovation Areas

**Context-Aware Asset Intelligence**
The core innovation is AI-driven contextual asset matching that goes far beyond keyword search. Unlike existing asset managers that rely on manual tagging or simple filename matching, RoughCut's AI understands narrative context — emotional tone, pacing, scene type — and matches assets from the indexed library accordingly. The innovation isn't perfect matching; it's "good enough" matching that places appropriate assets on the timeline where editors only need minor retiming and volume adjustments, eliminating the discovery and placement work while preserving creative control.

**Format-Driven AI Orchestration**
Novel approach to AI content generation using structured format templates as guardrails. Rather than open-ended AI cutting (which produces inconsistent results), RoughCut constrains the AI with user-defined format documents that specify structure, timing, and asset categories. The AI operates within these bounds, cutting transcripts to match formats while preserving exact source words and matching pre-approved template assets.

**Chunked Context Processing**
Innovative solution to AI context window limitations for long-form content. Instead of single massive prompts that lose coherence, RoughCut processes longer videos and larger asset datasets in context-aware chunks. This maintains narrative continuity while enabling the tool to handle feature-length content and extensive asset libraries without hitting token limits or losing context.

**Hybrid Architecture Seaming**
Strategic split between Lua (Resolve-native GUI and timeline operations) and Python (external AI processing, API management). This architecture choice is uncommon in Resolve plugins — most are either limited pure-Lua scripts or clunky external applications. RoughCut's approach provides native Resolve integration without sacrificing computational power or external API access.

### Validation Approach

**Core Success Metric:** Asset placement quality is validated by the "minimal adjustment" standard — when AI-suggested assets land on the timeline, editors should only need retiming (±2 seconds) and volume adjustment (±6dB) to make them work. No hunting for replacement assets, no "this is completely wrong" moments.

**Validation Process:**
1. **MVP Testing:** Run 20-30 rough cuts through the system, manually scoring each asset suggestion: "use as-is," "minor adjustment," or "replace"
2. **Success Threshold:** 60%+ "use as-is" or "minor adjustment" = validation passed
3. **Iterative Tuning:** If below threshold, adjust AI prompts, context chunking strategy, or format template structure before declaring failure
4. **Qualitative Feedback:** Track emotional response — does the editor feel "this got me 80% there" or "this is worse than starting from scratch"?

**Fallback Position:** If contextual matching underperforms, the tool remains valuable as a "fast rough cut generator" that cuts transcripts to format and lays down placeholder tracks. Even with mediocre asset suggestions, the structural work (cutting, timing, layering) saves significant time. The innovation becomes "fast rough cutting" rather than "intelligent asset matching" — still useful, just different.

### Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| AI matching accuracy below 60% | Fallback to "structural cut only" mode; focus on transcript cutting and timeline layout, let editor manually select assets |
| Resolve API limitations | Lua/Python architecture allows Python to handle heavy lifting; Lua remains thin GUI layer that can be adapted if Resolve API changes |
| AI service rate limits/costs | Chunked processing allows cost control; local caching of AI responses for similar content; ability to switch AI providers |
| Transcription quality issues | Clear visual feedback in UI; user workflow for audio cleanup before processing; non-destructive operation |
| Notion API changes | Notion integration is optional; core functionality works without it; graceful degradation if sync fails |
| Asset indexing performance | Incremental indexing (not full rescans); background processing; progress indication; ability to pause/resume |

## Developer Tool Specific Requirements

### Project-Type Overview

RoughCut is a hybrid developer tool combining a Lua-based DaVinci Resolve plugin/script with a Python backend. The tool follows the "simple install, powerful capabilities" philosophy — editors install via drag-and-drop while developers can extend the open-source codebase.

### Technical Architecture Considerations

**Language Support Matrix**

| Component | Language | Purpose | Rationale |
|-----------|----------|---------|-----------|
| Resolve GUI & Timeline Operations | Lua | Native Resolve scripting interface | Required for Resolve integration; runs in Resolve's Lua environment |
| AI Processing & External APIs | Python | Heavy computation, API management, file operations | Resolve's Lua is sandboxed; Python provides full system access and rich ecosystem |
| Format Templates | Markdown | Human-readable format definitions | Easy to author, version control friendly, extensible |
| Configuration | YAML/JSON | Settings and database storage | Standard formats, easy to edit manually if needed |

**Installation Methods**

**Primary Method: Drag-and-Drop**
1. User downloads RoughCut release package
2. Extracts to temporary location
3. Drags `RoughCut.lua` into DaVinci Resolve's Scripts folder (or Console workspace)
4. Resolve recognizes and registers the script
5. Python backend auto-installs on first run via embedded pip/pipx (if not present)
6. Optional: User configures Notion integration via GUI

**Developer/Advanced Installation:**
- Clone repository from GitHub
- Install Python dependencies via `pip install -r requirements.txt`
- Symlink or copy Lua script to Resolve Scripts folder
- Run from source for development

**API Surface**

**Public Interface (Lua):**
- `RoughCut:ShowMainWindow()` — Display main GUI
- `RoughCut:IndexMediaFolders()` — Trigger media indexing workflow
- `RoughCut:CreateRoughCut()` — Execute rough cut generation
- `RoughCut:ManageFormats()` — Open format template manager

**Internal Integration Points (Python):**
- `AssetDatabase` class — File indexing, tagging, search
- `TranscriptProcessor` class — Parse Resolve transcription output
- `FormatEngine` class — Load and apply format templates
- `AIMatcher` class — Interface to AI services for cutting and matching
- `TimelineBuilder` class — Generate Resolve timeline via API
- `NotionSync` class — Optional cloud synchronization

**Note:** Since RoughCut is open source, the Python backend API is fully visible and extensible. Developers can fork and modify any component.

### Implementation Considerations

**Documentation & Examples**

**Required Documentation:**
- `README.md` — Installation, quick start, basic usage
- `API.md` — Lua function reference and integration guide
- `DEVELOPMENT.md` — Setup for contributors, architecture overview
- `examples/` directory with sample format templates:
  - `youtube-interview.md` — Standard talking head interview format
  - `documentary-scene.md` — Narrative documentary scene structure
  - `social-media-short.md` — TikTok/Reels format template

**Code Examples for Extension:**
- Adding a new AI provider (OpenAI, Claude, local LLM)
- Creating custom format template parsers
- Extending the timeline builder for custom track layouts
- Adding new asset types beyond music/SFX/VFX

**Development Workflow**

**Local Development:**
- Lua: Edit → Drop into Resolve Scripts folder → Test immediately
- Python: Edit → Restart RoughCut from Resolve → Test changes
- Format Templates: Edit markdown → Reload via GUI → Test immediately

**Version Control:**
- Lua and Python source in Git repository
- Format templates as separate markdown files (easy to version)
- Database as SpacetimeDB (real-time synchronization with automatic state management, no manual migration needed)

**Distribution:**
- GitHub releases with packaged `.zip` containing Lua script + Python package
- Optional: Homebrew formula for macOS users who prefer command-line install
- Optional: Windows installer for less technical users (future consideration)

**Testing Approach (MVP)**
- Manual testing via Resolve for core workflows
- Python unit tests for backend logic (asset indexing, AI matching algorithms)
- Example format templates serve as integration tests

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Experience MVP — Full working tool that integrates smoothly into daily Resolve workflow, not just a proof-of-concept. Since the creator is the primary user, the MVP must be polished enough for actual production use.

**Resource Requirements:** Solo developer (you) with Resolve scripting knowledge, Python experience, and access to AI APIs (OpenAI/Claude/etc.). Estimated 4-6 weeks for MVP if working evenings/weekends.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Primary Editor — Standard Rough Cut Creation
- Primary Editor — Error Recovery (Failed Transcription)

**Must-Have Capabilities:**
1. **Media Indexing:** Incremental folder scanning for Music/SFX/VFX with AI-generated tags
2. **Resolve Integration:** Lua GUI in Scripts menu, Media Pool browser, transcription reading
3. **Format Management:** Markdown-based video format templates with template asset groups
4. **AI Processing:** Transcript cutting + media matching via chunked context processing
5. **Timeline Generation:** New timeline creation, media import, multi-track audio layering
6. **Notion Sync:** Optional cloud sync for media database (personal requirement)

**MVP Quality Threshold:** 50-60% AI suggestion usability acceptable. Editor reviews and refines. Value is eliminating blank-page problem and asset discovery, not automation.

### Post-MVP Features

**Phase 2 (Growth):**
- Enhanced AI matching (fine-tuned models, emotional tone analysis)
- In-app format template builder with "building blocks" system
- Batch processing multiple videos within Resolve
- Template marketplace/sharing within the community
- Better error handling and recovery workflows

**Phase 3 (Expansion):**
- Advanced Resolve Studio integration
- Cloud-based AI processing option for faster generation
- Learning from editor's final cuts
- Predictive asset recommendations
- Stock media API integration

All within Resolve. No external interfaces.

## Functional Requirements

### Media Asset Management

- FR1: Editor can configure parent folders for Music, SFX, and VFX media categories
- FR2: Editor can trigger incremental indexing of media folders when new assets are added
- FR3: System can generate AI-powered tags for indexed media based on filenames and folder paths
- FR4: Editor can view indexed asset counts by category (Music, SFX, VFX)
- FR5: Editor can re-index media folders to update the asset database
- FR6: System can store asset metadata including file paths, names, and generated tags in a local database
- FR7: Editor can optionally sync media database to Notion for cloud access

### Video Format Template Management

- FR8: Editor can view available video format templates
- FR9: Editor can preview format template structure and timing specifications
- FR10: Editor can select a format template for rough cut generation
- FR11: System can load format templates from markdown files
- FR12: Format templates can define template asset groups for common scene elements
- FR13: System can parse format template cutting rules and media matching criteria

### Transcription & Media Selection

- FR14: Editor can browse Resolve Media Pool and select a video clip
- FR15: System can retrieve and display Resolve's native transcription for selected clips
- FR16: Editor can review transcription quality before proceeding
- FR17: Editor can abort and retry with cleaned audio if transcription quality is poor
- FR18: System can validate that selected media is transcribable by Resolve

### AI-Powered Rough Cut Generation

- FR19: Editor can initiate rough cut generation with selected media and format template
- FR20: System can send transcript, format rules, and media index to AI service
- FR21: AI can cut transcript text into segments matching format structure without changing words
- FR22: AI can match music assets to transcript segments based on context and emotional tone
- FR23: AI can match SFX assets to appropriate moments in the transcript
- FR24: AI can match VFX/template assets to format requirements
- FR25: System can process long videos and large asset libraries in context-aware chunks
- FR26: Editor can review AI-generated rough cut document showing transcript cuts and asset placements

### Timeline Creation & Media Placement

- FR27: System can create new Resolve timeline for the rough cut
- FR28: System can import suggested media from local storage to the timeline
- FR29: System can cut video footage according to AI-recommended transcript segments
- FR30: System can place music on timeline with defined start and stop points
- FR31: System can layer SFX on separate tracks for timing and volume adjustment flexibility
- FR32: System can position VFX templates at specified timeline locations
- FR33: Editor can receive rough cut output for refinement and creative adjustment

### User Interface & Workflow

- FR34: Editor can access RoughCut via Resolve Scripts menu
- FR35: Editor can view RoughCut main window with clear navigation options
- FR36: Editor can access media management functions from the main interface
- FR37: Editor can access format template management from the main interface
- FR38: Editor can access rough cut creation workflow from the main interface
- FR39: System can display blocking UI with progress indication during media indexing
- FR40: System can display clear status messages during processing operations

### Installation & Configuration

- FR41: Editor can install RoughCut by dragging Lua script to Resolve Scripts folder
- FR42: System can auto-install Python backend dependencies on first run
- FR43: Editor can configure optional Notion integration with API token and page URL
- FR44: System can validate Notion connection when configured
- FR45: System can operate without Notion integration if not configured

## Non-Functional Requirements

### Performance

- NFR1: Media indexing shall complete within 2 minutes for 100 new assets on standard consumer hardware
- NFR2: Rough cut generation shall complete within 5 minutes for 15-minute source video
- NFR3: AI service API calls shall timeout after 30 seconds with clear error messaging
- NFR4: System shall display progress indicators for operations exceeding 5 seconds
- NFR5: Lua GUI shall remain responsive during Python backend processing operations

### Security

- NFR6: API keys (Notion, AI services) shall be stored encrypted in local configuration files
- NFR7: System shall not transmit media file contents to external services (only metadata and transcripts)
- NFR8: Local asset database shall be stored with filesystem permissions restricting access to current user only

### Reliability

- NFR9: System shall create timelines non-destructively (new timelines only, never modify existing)
- NFR10: System shall validate all file paths before attempting media import operations
- NFR11: System shall gracefully handle Resolve API unavailability with clear error messages
- NFR12: System shall provide recovery options for failed AI processing (retry, skip, or abort)

### Usability

- NFR13: All user-facing errors shall include actionable recovery guidance
- NFR14: GUI shall follow Resolve UI conventions for consistency with host application
- NFR15: Format template syntax shall be human-readable and editable without specialized tools
