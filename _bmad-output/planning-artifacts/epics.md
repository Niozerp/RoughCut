---
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics", "step-03-create-stories", "step-04-final-validation"]
inputDocuments: [
  "/Users/niozerp/Documents/AI_context_stuff/repos/RoughCut/_bmad-output/planning-artifacts/prd.md",
  "/Users/niozerp/Documents/AI_context_stuff/repos/RoughCut/_bmad-output/planning-artifacts/architecture.md"
]
status: "ready-for-development"
---

# RoughCut - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for RoughCut, decomposing the requirements from the PRD, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: Editor can configure parent folders for Music, SFX, and VFX media categories
FR2: Editor can trigger incremental indexing of media folders when new assets are added
FR3: System can generate AI-powered tags for indexed media based on filenames and folder paths
FR4: Editor can view indexed asset counts by category (Music, SFX, VFX)
FR5: Editor can re-index media folders to update the asset database
FR6: System can store asset metadata including file paths, names, and generated tags in SpacetimeDB
FR7: Editor can optionally sync media database to Notion for cloud access
FR8: Editor can view available video format templates
FR9: Editor can preview format template structure and timing specifications
FR10: Editor can select a format template for rough cut generation
FR11: System can load format templates from markdown files
FR12: Format templates can define template asset groups for common scene elements
FR13: System can parse format template cutting rules and media matching criteria
FR14: Editor can browse Resolve Media Pool and select a video clip
FR15: System can retrieve and display Resolve's native transcription for selected clips
FR16: Editor can review transcription quality before proceeding
FR17: Editor can abort and retry with cleaned audio if transcription quality is poor
FR18: System can validate that selected media is transcribable by Resolve
FR19: Editor can initiate rough cut generation with selected media and format template
FR20: System can send transcript, format rules, and media index to AI service
FR21: AI can cut transcript text into segments matching format structure without changing words
FR22: AI can match music assets to transcript segments based on context and emotional tone
FR23: AI can match SFX assets to appropriate moments in the transcript
FR24: AI can match VFX/template assets to format requirements
FR25: System can process long videos and large asset libraries in context-aware chunks
FR26: Editor can review AI-generated rough cut document showing transcript cuts and asset placements
FR27: System can create new Resolve timeline for the rough cut
FR28: System can import suggested media from local storage to the timeline
FR29: System can cut video footage according to AI-recommended transcript segments
FR30: System can place music on timeline with defined start and stop points
FR31: System can layer SFX on separate tracks for timing and volume adjustment flexibility
FR32: System can position VFX templates at specified timeline locations
FR33: Editor can receive rough cut output for refinement and creative adjustment
FR34: Editor can access RoughCut via Resolve Scripts menu
FR35: Editor can view RoughCut main window with clear navigation options
FR36: Editor can access media management functions from the main interface
FR37: Editor can access format template management from the main interface
FR38: Editor can access rough cut creation workflow from the main interface
FR39: System can display blocking UI with progress indication during media indexing
FR40: System can display clear status messages during processing operations
FR41: Editor can install RoughCut by dragging Lua script to Resolve Scripts folder
FR42: System can auto-install Python backend dependencies on first run
FR43: Editor can configure optional Notion integration with API token and page URL
FR44: System can validate Notion connection when configured
FR45: System can operate without Notion integration if not configured

### Non-Functional Requirements

NFR1: Media indexing shall complete within 2 minutes for 100 new assets on standard consumer hardware
NFR2: Rough cut generation shall complete within 5 minutes for 15-minute source video
NFR3: AI service API calls shall timeout after 30 seconds with clear error messaging
NFR4: System shall display progress indicators for operations exceeding 5 seconds
NFR5: Lua GUI shall remain responsive during Python backend processing operations
NFR6: API keys (Notion, AI services) shall be stored encrypted in local configuration files
NFR7: System shall not transmit media file contents to external services (only metadata and transcripts)
NFR8: SpacetimeDB data shall be secured with row-level security policies and identity-based access control
NFR9: System shall create timelines non-destructively (new timelines only, never modify existing)
NFR10: System shall validate all file paths before attempting media import operations
NFR11: System shall gracefully handle Resolve API unavailability with clear error messages
NFR12: System shall provide recovery options for failed AI processing (retry, skip, or abort)
NFR13: All user-facing errors shall include actionable recovery guidance
NFR14: GUI shall follow Resolve UI conventions for consistency with host application
NFR15: Format template syntax shall be human-readable and editable without specialized tools

### Additional Requirements

- System shall use Poetry 2.0+ for Python dependency management with lock files
- System shall initialize project structure with Poetry using `poetry new roughcut --src` as first implementation step
- System shall use Python 3.10+ with type hints throughout the codebase
- System shall use SpacetimeDB for database layer, providing real-time collaborative data storage with automatic synchronization
- System shall implement SpacetimeDB Rust client bindings for Python backend integration
- System shall use SpacetimeDB module system for data schema definition and business logic
- System shall implement JSON-RPC protocol over stdin/stdout for Lua ↔ Python communication
- System shall follow strict layer separation: Lua handles GUI only, Python handles all business logic
- System shall use absolute file paths in all cross-layer communication
- System shall use OpenAI SDK directly initially, abstract to LiteLLM only when second provider needed
- System shall store API keys in config file initially, enhance to keyring library post-MVP
- System shall use snake_case for Python functions/variables, PascalCase for classes
- System shall use camelCase for Lua functions/variables, PascalCase for GUI components
- System shall use snake_case plural for database tables (e.g., media_assets, format_templates)
- System shall implement structured error objects with code, category, message, and suggestion fields
- System shall use JSON Lines (newline-delimited) for all inter-process communication
- System shall provide progress updates every N items or every M seconds during long operations
- System shall never hang without updates for more than 5 seconds during processing
- System shall implement async/await patterns in Python for I/O operations
- System shall use dataclasses with type hints for data models
- System shall organize code with clear boundaries: backend/, lua/, protocols/, templates/, tests/
- System shall place format templates in templates/formats/ as markdown files
- System shall implement chunked processing strategy for AI context window limitations
- System shall ensure non-destructive operations by creating new timelines only
- System shall validate all file paths before media import operations
- System shall handle AI failure recovery with retry, skip, or abort options

### UX Design Requirements

No UX Design Specification document exists. UX requirements are embedded within PRD Functional Requirements (FR34-FR40) covering UI/Workflow aspects.

### FR Coverage Map

FR1: Epic 2 - Configure parent folders for media categories
FR2: Epic 2 - Trigger incremental indexing of media folders
FR3: Epic 2 - Generate AI-powered tags for indexed media
FR4: Epic 2 - View indexed asset counts by category
FR5: Epic 2 - Re-index media folders to update database
FR6: Epic 2 - Store asset metadata in SpacetimeDB
FR7: Epic 2 - Optionally sync media database to Notion
FR8: Epic 3 - View available video format templates
FR9: Epic 3 - Preview format template structure and timing
FR10: Epic 3 - Select format template for rough cut generation
FR11: Epic 3 - Load format templates from markdown files
FR12: Epic 3 - Define template asset groups for scene elements
FR13: Epic 3 - Parse format template cutting rules
FR14: Epic 4 - Browse Resolve Media Pool and select clip
FR15: Epic 4 - Retrieve and display Resolve transcription
FR16: Epic 4 - Review transcription quality before proceeding
FR17: Epic 4 - Abort and retry with cleaned audio
FR18: Epic 4 - Validate media is transcribable by Resolve
FR19: Epic 5 - Initiate rough cut generation
FR20: Epic 5 - Send transcript, format rules, and media index to AI
FR21: Epic 5 - AI cuts transcript into segments
FR22: Epic 5 - AI matches music assets to segments
FR23: Epic 5 - AI matches SFX assets to moments
FR24: Epic 5 - AI matches VFX/template assets
FR25: Epic 5 - Process long videos in context-aware chunks
FR26: Epic 5 - Review AI-generated rough cut document
FR27: Epic 6 - Create new Resolve timeline for rough cut
FR28: Epic 6 - Import suggested media to timeline
FR29: Epic 6 - Cut footage per AI-recommended segments
FR30: Epic 6 - Place music on timeline with start/stop points
FR31: Epic 6 - Layer SFX on separate tracks
FR32: Epic 6 - Position VFX templates at timeline locations
FR33: Epic 6 - Receive rough cut output for refinement
FR34: Epic 1 - Access RoughCut via Resolve Scripts menu
FR35: Epic 1 - View RoughCut main window with navigation
FR36: Epic 2 - Access media management from main interface
FR37: Epic 3 - Access format template management from main interface
FR38: Epic 5 - Access rough cut creation workflow from main interface
FR39: Epic 2 - Display blocking UI with progress during indexing
FR40: Epic 2/5 - Display status messages during processing
FR41: Epic 1 - Install RoughCut by dragging Lua script to Resolve
FR42: Epic 1 - Auto-install Python backend on first run
FR43: Epic 1 - Configure optional Notion integration
FR44: Epic 1 - Validate Notion connection
FR45: Epic 1 - Operate without Notion integration

## Epic List

### Epic 1: Foundation & Installation
Editor can install, configure, and access RoughCut from Resolve with optional cloud sync
**FRs covered:** FR34, FR35, FR41, FR42, FR43, FR44, FR45

### Epic 2: Media Asset Management
Editor can index, tag, and manage their media asset library with AI assistance
**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR36, FR39, FR40

### Epic 3: Format Template System
Editor can define, view, and select video format templates for rough cuts
**FRs covered:** FR8, FR9, FR10, FR11, FR12, FR13, FR37

### Epic 4: Media Selection & Transcription
Editor can select source media and validate transcription quality
**FRs covered:** FR14, FR15, FR16, FR17, FR18

### Epic 5: AI-Powered Rough Cut Generation
Editor can generate AI-driven rough cuts with suggested media placements
**FRs covered:** FR19, FR20, FR21, FR22, FR23, FR24, FR25, FR26, FR38

### Epic 6: Timeline Creation & Media Placement
Editor can export the rough cut to Resolve timeline with all media positioned
**FRs covered:** FR27, FR28, FR29, FR30, FR31, FR32, FR33

---

## Epic 1: Foundation & Installation

Editor can install, configure, and access RoughCut from Resolve with optional cloud sync

### Story 1.1: Drag-and-Drop Installation

As a video editor,
I want to install RoughCut by dragging the Lua script to Resolve's Scripts folder,
So that I can get the tool running without complex setup procedures.

**Acceptance Criteria:**

**Given** I have downloaded the RoughCut release package
**When** I drag `RoughCut.lua` into DaVinci Resolve's Scripts folder
**Then** Resolve recognizes and registers the script
**And** The script appears in the Scripts menu

**Given** I am installing on a fresh system
**When** I place the Lua script in the Scripts folder
**Then** No additional manual steps are required for basic functionality

### Story 1.2: Scripts Menu Integration

As a video editor,
I want to access RoughCut from the DaVinci Resolve Scripts menu,
So that I can launch the tool without leaving my editing environment.

**Acceptance Criteria:**

**Given** RoughCut is installed in the Scripts folder
**When** I open the Scripts menu in DaVinci Resolve
**Then** I see "RoughCut" as an available script option

**Given** I click on RoughCut in the Scripts menu
**When** The script launches
**Then** The main window opens without errors
**And** The UI follows Resolve's visual conventions

### Story 1.3: Python Backend Auto-Installation

As a video editor,
I want the Python backend to auto-install on first run,
So that I don't need to manually manage Python dependencies.

**Acceptance Criteria:**

**Given** I launch RoughCut for the first time
**When** The Lua script initializes
**Then** It detects if Python backend is installed

**Given** Python backend is not installed
**When** First run initialization occurs
**Then** The system automatically installs required Python dependencies
**And** A progress indicator shows installation status

**Given** Python dependencies are being installed
**When** Installation completes successfully
**Then** The main interface becomes available
**And** No restart of Resolve is required

### Story 1.4: Main Window Navigation

As a video editor,
I want to view RoughCut's main window with clear navigation options,
So that I can easily access all the tool's features.

**Acceptance Criteria:**

**Given** RoughCut is running
**When** The main window displays
**Then** I see three clear navigation options: Manage Media, Manage Formats, Create Rough Cut

**Given** I am on the main window
**When** I hover over navigation options
**Then** Each option is clearly labeled with descriptive text

**Given** I select any navigation option
**When** The corresponding interface loads
**Then** I can return to the main window easily

### Story 1.5: Optional Notion Configuration

As a video editor,
I want to configure optional Notion integration with API token and page URL,
So that I can sync my media database to the cloud for accessibility.

**Acceptance Criteria:**

**Given** I navigate to settings/configuration
**When** I choose to configure Notion integration
**Then** I can enter my Notion API token

**Given** I have entered the API token
**When** I provide a Notion page URL
**Then** The system stores these credentials securely (encrypted)

**Given** I have saved Notion configuration
**When** I return to settings later
**Then** My configuration persists between sessions

### Story 1.6: Notion Connection Validation

As a video editor,
I want to validate my Notion connection and handle errors gracefully,
So that I know if my cloud sync is working or if I need to troubleshoot.

**Acceptance Criteria:**

**Given** I have configured Notion integration
**When** I request connection validation
**Then** The system tests the connection to Notion API

**Given** The Notion connection is valid
**When** Validation completes
**Then** I see a success message
**And** A test sync can be performed

**Given** The Notion connection fails
**When** Validation completes
**Then** I see a clear error message with actionable guidance
**And** The system continues to operate without Notion (graceful degradation)

**Given** Notion is not configured
**When** I use RoughCut
**Then** All core functionality works normally
**And** No errors related to missing Notion configuration appear

---

## Epic 2: Media Asset Management

Editor can index, tag, and manage their media asset library with AI assistance

### Story 2.1: Media Folder Configuration

As a video editor,
I want to configure parent folders for Music, SFX, and VFX media categories,
So that RoughCut knows where to look for my asset libraries.

**Acceptance Criteria:**

**Given** I navigate to "Manage Media" from the main window
**When** I access folder configuration
**Then** I can select parent folders for Music, SFX, and VFX categories separately

**Given** I am configuring media folders
**When** I select a folder path
**Then** The system displays the absolute path for confirmation
**And** Validates that the folder exists and is accessible

**Given** I have configured media folders
**When** I return to media management later
**Then** My folder paths persist between sessions

### Story 2.2: Incremental Media Indexing

As a video editor,
I want to trigger incremental indexing when new assets are added,
So that my media database stays current without constant background processing.

**Acceptance Criteria:**

**Given** I have configured media folders
**When** I trigger manual indexing
**Then** The system scans only new or changed files since last index

**Given** Media indexing is in progress
**When** The operation exceeds 5 seconds
**Then** A blocking UI with progress indicator displays
**And** I see clear status messages (e.g., "Indexing: epic_whoosh.wav")

**Given** Indexing is running
**When** Progress updates occur
**Then** Updates display every N items or every M seconds (never >5 seconds without update)

**Given** 100 new assets are being indexed
**When** The process completes
**Then** It finishes within 2 minutes on standard consumer hardware

### Story 2.3: AI-Powered Tag Generation

As a video editor,
I want the system to generate AI-powered tags for indexed media based on filenames and folder paths,
So that I can search and match assets contextually.

**Acceptance Criteria:**

**Given** A media file is being indexed
**When** The file has metadata (filename, folder path)
**Then** The AI analyzes and generates relevant tags

**Given** A music file at path "Music/Corporate/Upbeat/bright_corporate_theme.wav"
**When** AI tagging occurs
**Then** Generated tags include: "corporate", "upbeat", "bright", "theme"

**Given** Tags are generated
**When** They are stored in SpacetimeDB
**Then** Each media asset has an associated tag list
**And** Tags are searchable for future matching

### Story 2.4: Asset Count Dashboard

As a video editor,
I want to view indexed asset counts by category (Music, SFX, VFX),
So that I know the scope of my available creative resources.

**Acceptance Criteria:**

**Given** I navigate to "Manage Media"
**When** The media management interface loads
**Then** I see indexed asset counts for Music, SFX, and VFX categories

**Given** The count dashboard displays
**When** I view the numbers
**Then** They update in real-time as indexing completes

**Given** I have 12,437 music tracks, 8,291 sound effects, and 3,102 VFX templates
**When** The dashboard renders
**Then** Counts display clearly: "Music: 12,437 | SFX: 8,291 | VFX: 3,102"

### Story 2.5: SpacetimeDB Storage

As a video editor,
I want asset metadata stored in SpacetimeDB,
So that my data benefits from real-time synchronization and collaborative features.

**Acceptance Criteria:**

**Given** Media assets are indexed
**When** Metadata is captured (file paths, names, AI tags)
**Then** Data is stored in SpacetimeDB via Rust client bindings

**Given** Data is stored in SpacetimeDB
**When** I access the media database from RoughCut
**Then** Retrieval is fast and consistent

**Given** SpacetimeDB is configured
**When** Row-level security policies are applied
**Then** Only my user identity can access my asset data

**Given** I have assets stored
**When** Data changes occur (new tags, updated paths)
**Then** Changes sync in real-time across connected clients

### Story 2.6: Re-indexing Capability

As a video editor,
I want to re-index media folders to update the asset database,
So that changes in my file system (moved files, new folders) are reflected.

**Acceptance Criteria:**

**Given** I have previously indexed media folders
**When** I trigger re-indexing
**Then** The system performs a full scan (not just incremental)

**Given** Files have been moved, renamed, or deleted
**When** Re-indexing completes
**Then** The database reflects the current state of the file system

**Given** Re-indexing is in progress
**When** Progress displays
**Then** Clear status shows "Re-indexing: detecting changes..."

**Given** Re-indexing finds orphaned database entries
**When** Processing completes
**Then** Invalid entries are cleaned up automatically

### Story 2.7: Notion Sync

As a video editor,
I want to optionally sync my media database to Notion,
So that I can access my asset library from anywhere and collaborate with team members.

**Acceptance Criteria:**

**Given** Notion integration is configured and enabled
**When** Media database changes (new assets, tags updated)
**Then** Changes sync to the configured Notion page

**Given** A sync operation is triggered
**When** It completes successfully
**Then** Asset metadata appears in Notion with file paths and tags

**Given** Notion sync is enabled
**When** Sync fails due to API issues
**Then** The error is logged but RoughCut continues operating normally
**And** Sync retries automatically on next database change

**Given** I view my Notion page
**When** The sync is complete
**Then** I see a table or database view of my media assets
**And** Each entry includes: filename, category, path, AI tags

---

## Epic 3: Format Template System

Editor can define, view, and select video format templates for rough cuts

### Story 3.1: View Format Templates

As a video editor,
I want to view available video format templates,
So that I can see what editing patterns are available for my projects.

**Acceptance Criteria:**

**Given** I navigate to "Manage Formats" from the main window
**When** The format management interface loads
**Then** I see a list of available format templates

**Given** The format list displays
**When** I view the templates
**Then** Each template shows its name and brief description
**And** Examples include: "YouTube Interview — Corporate", "Documentary Scene", "Social Media Short"

**Given** Format templates exist in the templates/formats/ directory
**When** The interface loads
**Then** All markdown format files are discovered and listed

### Story 3.2: Preview Template Structure

As a video editor,
I want to preview format template structure and timing specifications,
So that I can understand how the rough cut will be structured before generating it.

**Acceptance Criteria:**

**Given** I select a format template from the list
**When** I choose to preview it
**Then** The template structure displays clearly

**Given** I preview "YouTube Interview — Corporate" template
**When** Details display
**Then** I see timing specifications: "15-second hook with upbeat music, 3-minute narrative section, 30-second outro"

**Given** A template has asset group definitions
**When** Preview shows
**Then** Template assets are listed (e.g., "standard corporate music bed", "success chime SFX")

**Given** The preview displays
**When** I review the information
**Then** Structure is human-readable without specialized tools (markdown-based)

### Story 3.3: Select Template for Rough Cut

As a video editor,
I want to select a format template for rough cut generation,
So that the AI knows what structure to follow when creating my edit.

**Acceptance Criteria:**

**Given** I have selected source media and reviewed transcription
**When** I proceed to format selection
**Then** Available templates are presented in a selectable list

**Given** I select a format template
**When** Selection is confirmed
**Then** The system remembers my choice for the current rough cut session

**Given** I have selected a template
**When** I proceed to generate rough cut
**Then** The selected template's rules are passed to the AI service

**Given** Format selection is part of the rough cut workflow
**When** I access it from the main window
**Then** "Create Rough Cut" path naturally includes format selection step

### Story 3.4: Load Templates from Markdown

As a video editor,
I want the system to load format templates from markdown files,
So that templates are easy to author, version control, and extend.

**Acceptance Criteria:**

**Given** Format templates are stored in templates/formats/ directory
**When** RoughCut initializes
**Then** It discovers and loads all .md files from that directory

**Given** A markdown template exists (e.g., youtube-interview.md)
**When** The system parses it
**Then** It extracts: title, description, timing structure, cutting rules, asset group definitions

**Given** Template files are updated
**When** RoughCut reloads templates
**Then** Changes are reflected without requiring application restart

**Given** New templates are added to the directory
**When** RoughCut scans for templates
**Then** New templates appear in the available formats list

### Story 3.5: Template Asset Groups

As a video editor,
I want format templates to define template asset groups for common scene elements,
So that the AI knows what types of assets to suggest for specific moments.

**Acceptance Criteria:**

**Given** A format template defines asset groups
**When** The template is loaded
**Then** Groups are parsed (e.g., "intro_music", "narrative_bed", "outro_chime")

**Given** Asset groups are defined
**When** AI processes the rough cut
**Then** It matches assets from the appropriate categories to template moments

**Given** Template specifies "corporate upbeat" music for intro
**When** AI suggests music
**Then** It searches indexed assets with "corporate" and "upbeat" tags

**Given** A format has multiple asset group types
**When** RoughCut displays template details
**Then** All groups are listed with their intended use cases

### Story 3.6: Parse Format Rules

As a video editor,
I want the system to parse format template cutting rules and media matching criteria,
So that the AI understands exactly how to structure the rough cut.

**Acceptance Criteria:**

**Given** A format template includes cutting rules
**When** The system parses the template
**Then** It extracts timing constraints, segment structure, and transition rules

**Given** Format defines "cut transcript to 3 key narrative beats"
**When** AI processes the transcript
**Then** It attempts to identify and preserve 3 strongest narrative moments

**Given** Media matching criteria are defined
**When** AI suggests assets
**Then** It follows the criteria (e.g., "match music emotion to transcript tone")

**Given** Format rules are parsed
**When** They are sent to AI service
**Then** They are included in the prompt with clear instructions
**And** The AI operates within these constraints

---

## Epic 4: Media Selection & Transcription

Editor can select source media and validate transcription quality

### Story 4.1: Browse Media Pool

As a video editor,
I want to browse the Resolve Media Pool and select a video clip,
So that RoughCut knows which footage to analyze for the rough cut.

**Acceptance Criteria:**

**Given** I start the rough cut creation workflow
**When** The media selection step appears
**Then** RoughCut lists my Resolve Media Pool contents

**Given** The Media Pool browser displays
**When** I view my clips
**Then** I see clip names, durations, and thumbnails

**Given** I select a video clip from the list
**When** Selection is confirmed
**Then** RoughCut captures the clip reference for processing
**And** The selected clip is highlighted in the interface

### Story 4.2: Retrieve Transcription

As a video editor,
I want RoughCut to retrieve and display Resolve's native transcription for selected clips,
So that I can see the spoken content that will guide the rough cut.

**Acceptance Criteria:**

**Given** I have selected a video clip
**When** RoughCut initializes the rough cut process
**Then** It requests transcription from Resolve's native API

**Given** Resolve returns transcription data
**When** RoughCut receives it
**Then** The transcript displays clearly: clean, accurate, every word captured

**Given** The transcript displays
**When** I review it
**Then** I can read the full text content with speaker labels if available

**Given** A 38-minute interview clip
**When** Transcription completes
**Then** Full transcript is available for AI processing within seconds

### Story 4.3: Review Transcription Quality

As a video editor,
I want to review transcription quality before proceeding,
So that I don't waste AI processing on poor-quality audio.

**Acceptance Criteria:**

**Given** Transcription has been retrieved
**When** It displays in RoughCut
**Then** Quality indicators are visible (e.g., confidence scores, completeness metrics)

**Given** The transcript has obvious quality issues
**When** I view it
**Then** The UI clearly marks problem areas: "[inaudible]", "[garbled]", low-confidence sections

**Given** The transcript is high quality
**When** Review completes
**Then** I see a "Quality: Good" indicator and can proceed confidently

**Given** I am reviewing transcription
**When** I see quality warnings
**Then** I understand whether to proceed or fix audio issues first

### Story 4.4: Error Recovery Workflow

As a video editor,
I want to abort and retry with cleaned audio if transcription quality is poor,
So that I can salvage footage with fixable audio issues.

**Acceptance Criteria:**

**Given** Transcription quality is poor (e.g., 40% usable, HVAC noise)
**When** RoughCut displays the transcript
**Then** A clear warning shows: "Transcription quality low - audio cleanup recommended"

**Given** I see the quality warning
**When** I choose to abort
**Then** RoughCut exits gracefully without creating timelines or processing AI

**Given** I have aborted due to poor transcription
**When** I follow the recovery workflow
**Then** I can: 1) Apply Resolve's noise reduction, 2) Render clean version, 3) Replace clip in Media Pool

**Given** I have cleaned the audio
**When** I re-open RoughCut and select the cleaned clip
**Then** Transcription is re-retrieved
**And** Quality is now acceptable for AI processing

**Given** I attempt to use RoughCut with cleaned audio
**When** The new transcription displays
**Then** It is crisp and accurate (e.g., "The thing is... basically..." becomes clear dialogue)

### Story 4.5: Validate Transcribable Media

As a video editor,
I want the system to validate that selected media is transcribable by Resolve,
So that I get immediate feedback if a clip cannot be processed.

**Acceptance Criteria:**

**Given** I select a video clip
**When** RoughCut attempts to retrieve transcription
**Then** It first validates that the clip has audio and is transcribable

**Given** A clip has no audio track
**When** Validation runs
**Then** RoughCut displays: "Cannot transcribe - no audio detected"

**Given** A clip is in an unsupported format
**When** Validation runs
**Then** RoughCut displays: "Cannot transcribe - unsupported format"

**Given** Media fails transcribability validation
**When** Error displays
**Then** The error message includes actionable guidance (e.g., "Check clip has audio", "Verify format compatibility")

---

## Epic 5: AI-Powered Rough Cut Generation

Editor can generate AI-driven rough cuts with suggested media placements

### Story 5.1: Initiate Rough Cut Generation

As a video editor,
I want to initiate rough cut generation with selected media and format template,
So that I can start the AI processing that will create my rough cut.

**Acceptance Criteria:**

**Given** I have selected source media, validated transcription, and chosen a format template
**When** I click "Generate Rough Cut"
**Then** RoughCut confirms my selections and prepares to send data to AI

**Given** I access rough cut creation from the main interface
**When** I follow the workflow path
**Then** The natural progression is: Select Media → Validate Transcription → Select Format → Generate

**Given** I click "Generate Rough Cut"
**When** The process starts
**Then** A blocking UI appears showing "Preparing data for AI processing..."

**Given** I have initiated generation
**When** The AI processing begins
**Then** I see clear status: "Analyzing transcript and matching assets..."

### Story 5.2: Send Data to AI Service

As a video editor,
I want the system to send transcript, format rules, and media index to the AI service,
So that the AI has all the context needed to generate recommendations.

**Acceptance Criteria:**

**Given** I have initiated rough cut generation
**When** RoughCut prepares the AI request
**Then** It bundles: transcript text, selected format template rules, indexed media metadata

**Given** The request is being prepared
**When** Media index is included
**Then** It contains file paths, AI-generated tags, and categories (Music/SFX/VFX)
**And** Only metadata is sent, not actual media file contents (per NFR7)

**Given** The AI request is ready
**When** It is sent to the AI service
**Then** It includes strict instructions: "Cut transcript to match format structure, match music from indexed library, layer SFX for emotional beats"

**Given** AI service API calls are made
**When** Requests exceed 30 seconds
**Then** They timeout with clear error messaging (per NFR3)

### Story 5.3: AI Transcript Cutting

As a video editor,
I want the AI to cut transcript text into segments matching the format structure without changing words,
So that the rough cut follows the template while preserving the original dialogue exactly.

**Acceptance Criteria:**

**Given** The AI receives transcript and format template
**When** It processes the cutting request
**Then** It identifies narrative beats that align with format structure

**Given** A "YouTube Interview" format requires 3 narrative sections
**When** AI cuts a 38-minute transcript
**Then** It extracts exactly 3 key narrative segments preserving all original words

**Given** The AI cuts the transcript
**When** Segments are determined
**Then** Source words are never changed, paraphrased, or summarized
**And** Only start/end timestamps are adjusted

**Given** The transcript cutting completes
**When** Results are returned
**Then** I see segment markers: "Section 1: 0:15-1:45", "Section 2: 2:30-4:15", etc.

### Story 5.4: AI Music Matching

As a video editor,
I want the AI to match music assets to transcript segments based on context and emotional tone,
So that appropriate background music enhances the narrative without manual searching.

**Acceptance Criteria:**

**Given** The AI has cut the transcript into segments
**When** It analyzes segment content
**Then** It determines emotional tone for each segment (e.g., "corporate upbeat", "contemplative", "triumphant")

**Given** Segment tone is identified
**When** AI searches indexed music library
**Then** It matches assets with complementary tags (e.g., "corporate" + "upbeat" for intro)

**Given** Multiple music assets match a segment
**When** AI selects the best match
**Then** It prioritizes: tag relevance, file quality indicators, recently used assets (optional preference)

**Given** The AI finds a perfect music match
**When** It was suggested
**Then** The editor sees: "Music: corporate_bright_theme.wav (from 'corporate/upbeat' folder)"
**And** May discover forgotten assets: "Found: corporate_bright_theme.wav (purchased 18 months ago)"

### Story 5.5: AI SFX Matching

As a video editor,
I want the AI to match SFX assets to appropriate moments in the transcript,
So that sound effects add emotional emphasis without disrupting the flow.

**Acceptance Criteria:**

**Given** The AI has cut transcript segments
**When** It analyzes for emotional beats and transitions
**Then** It identifies moments suitable for SFX (e.g., intro whoosh, pivot emphasis, outro chime)

**Given** An emotional pivot in the transcript
**When** AI determines SFX is appropriate
**Then** It searches SFX library for matching context (e.g., "success", "transition", "underscore")

**Given** Multiple SFX options exist
**When** AI makes selection
**Then** It suggests subtle, non-distracting sounds that enhance without overwhelming

**Given** SFX are matched to moments
**When** Suggestions are presented
**Then** Editor sees: "SFX: gentle_whoosh (0:00), underscore_tone (2:30), outro_chime (3:45)"
**And** Layer information shows: "Place on separate track for volume flexibility"

**Given** A suggested SFX might not fit the emotional context
**When** The editor reviews
**Then** They can easily note: "SFX: tension_sound suggested at pivot, but story is about triumph — swap to success_sound"

### Story 5.6: AI VFX/Template Matching

As a video editor,
I want the AI to match VFX and template assets to format requirements,
So that lower thirds, transitions, and effects are positioned appropriately.

**Acceptance Criteria:**

**Given** The format template specifies VFX requirements (e.g., "lower thirds for speaker names")
**When** AI processes the rough cut
**Then** It identifies template moments needing VFX

**Given** Lower thirds are needed
**When** AI searches VFX template library
**Then** It matches appropriate templates (e.g., "standard_lower_third", "corporate_nameplate")

**Given** Template placements are determined
**When** Positions are calculated
**Then** They align with transcript segment boundaries and format timing rules

**Given** VFX suggestions are generated
**When** Editor reviews the rough cut document
**Then** They see: "VFX: lower_third_template at 0:15 (intro speaker), outro_cta at 3:45"

**Given** A format has specific template asset groups defined
**When** AI processes
**Then** It prioritizes assets from those predefined groups

### Story 5.7: Chunked Context Processing

As a video editor,
I want the system to process long videos and large asset libraries in context-aware chunks,
So that I can work with feature-length content and extensive libraries without hitting AI token limits.

**Acceptance Criteria:**

**Given** A video exceeds AI context window limits
**When** RoughCut sends data to AI
**Then** It automatically chunks the transcript into overlapping segments

**Given** Chunking occurs
**When** Segments are processed
**Then** Narrative continuity is preserved across chunk boundaries
**And** Context from previous chunks informs current processing

**Given** Asset libraries are large (20,000+ assets)
**When** AI matching occurs
**Then** Only relevant asset categories are included per chunk (e.g., chunk 1: intro assets, chunk 2: narrative assets)

**Given** A 60-minute documentary is processed
**When** Chunked processing completes
**Then** The full rough cut is assembled from chunk results with consistent pacing

**Given** Chunking is active
**When** Progress updates are sent
**Then** Editor sees: "Processing chunk 3 of 8..." with ETA

### Story 5.8: Review AI-Generated Rough Cut Document

As a video editor,
I want to review an AI-generated rough cut document showing transcript cuts and asset placements,
So that I can validate the AI's work before creating the timeline.

**Acceptance Criteria:**

**Given** AI processing completes
**When** The rough cut document displays
**Then** I see a structured overview: transcript segments, music suggestions, SFX list, VFX placements

**Given** The document displays
**When** I review transcript cuts
**Then** I see the three narrative beats mapped to format structure with timestamps

**Given** Music suggestions are shown
**When** I review them
**Then** I see the suggested track with source folder info (e.g., "Music: corporate_upbeat_track.wav from 'corporate/upbeat' folder")
**And** I may discover forgotten assets I haven't used in months

**Given** SFX are listed
**When** I review the list
**Then** Each SFX shows: name, intended moment, placement track recommendation

**Given** VFX placements are shown
**When** I review them
**Then** Each shows: template name, timeline position, duration

**Given** I have reviewed the document
**When** I am satisfied with the AI's suggestions
**Then** I can click "Create Timeline" to proceed
**And** If I want changes, I can note them mentally and adjust after timeline creation

---

## Epic 6: Timeline Creation & Media Placement

Editor can export the rough cut to Resolve timeline with all media positioned

### Story 6.1: Create New Timeline

As a video editor,
I want the system to create a new Resolve timeline for the rough cut,
So that my existing timelines remain untouched and I get a fresh edit to work with.

**Acceptance Criteria:**

**Given** I click "Create Timeline" after reviewing AI suggestions
**When** RoughCut initiates timeline creation
**Then** It creates a NEW timeline (non-destructive operation, per NFR9)

**Given** A new timeline is created
**When** It appears in Resolve
**Then** It has a descriptive name: "RoughCut_[source_clip_name]_[format]_[timestamp]"

**Given** Timeline creation starts
**When** The process runs
**Then** Original source clip in Media Pool is never modified

**Given** Timeline creation is in progress
**When** Progress is displayed
**Then** Status shows: "Creating timeline structure..."

**Given** Timeline creation completes successfully
**When** It finishes
**Then** The new timeline is active in Resolve's Edit page
**And** It contains the correct number of tracks (dialogue, music, SFX, VFX)

### Story 6.2: Import Suggested Media

As a video editor,
I want the system to import suggested media from local storage to the timeline,
So that all AI-recommended assets are available in the edit without manual importing.

**Acceptance Criteria:**

**Given** AI has suggested specific music, SFX, and VFX assets
**When** Timeline creation begins
**Then** RoughCut locates each file using stored absolute paths

**Given** File paths are validated
**When** Media import starts
**Then** System checks each file exists and is accessible before import (per NFR10)

**Given** All suggested media files exist
**When** Import proceeds
**Then** They are added to Resolve's Media Pool if not already present

**Given** Media is being imported
**When** Progress displays
**Then** Status shows: "Importing: epic_whoosh.wav", "Importing: corporate_theme.mp3", etc.

**Given** A suggested media file is missing
**When** Validation occurs
**Then** RoughCut displays: "Warning: [filename] not found at [path] - will be skipped"
**And** Timeline creation continues with available assets

### Story 6.3: Cut Footage to Segments

As a video editor,
I want the system to cut video footage according to AI-recommended transcript segments,
So that the dialogue follows the format structure without manual cutting.

**Acceptance Criteria:**

**Given** AI has determined transcript segments (e.g., 0:15-1:45, 2:30-4:15)
**When** Timeline is created
**Then** Source clip is cut and placed on the timeline according to these segments

**Given** Segments are placed
**When** Timeline displays
**Then** They appear sequentially on the dialogue/video track
**And** Transitions between segments are clean cuts (no effects by default)

**Given** The 38-minute interview is cut
**When** Timeline is complete
**Then** It contains ~4 minutes of selected footage in 3 narrative segments

**Given** Segment boundaries are calculated
**When** They are applied
**Then** They align precisely with the AI's recommendations (no drift or offset errors)

### Story 6.4: Place Music on Timeline

As a video editor,
I want the system to place music on the timeline with defined start and stop points,
So that background music follows the format timing (fade in at 0:00, bed under narrative, swell for outro).

**Acceptance Criteria:**

**Given** AI has suggested music for intro, narrative, and outro sections
**When** Timeline is created
**Then** Music clips are placed on a dedicated music track

**Given** Music placements are determined
**When** They are applied to timeline
**Then** Start/stop points match format specifications: intro music at 0:00, bed music at 0:15, swell at 3:45

**Given** Music is placed on timeline
**When** I review the timeline
**Then** I see the music clips positioned with handles for fade adjustments

**Given** Multiple music pieces are suggested
**When** They are placed
**Then** They are on the same track (or separate tracks if overlapping) with proper spacing

**Given** Music placement completes
**When** I play the timeline
**Then** Music flows continuously following the format structure

### Story 6.5: Layer SFX on Separate Tracks

As a video editor,
I want the system to layer SFX on separate tracks for timing and volume adjustment flexibility,
So that I can fine-tune audio levels without affecting other elements.

**Acceptance Criteria:**

**Given** AI has suggested SFX for intro whoosh, pivot emphasis, and outro chime
**When** Timeline is created
**Then** SFX are placed on dedicated SFX tracks (separate from dialogue and music)

**Given** Multiple SFX are suggested
**When** They are placed
**Then** Each SFX gets its own track or shares a track with proper spacing

**Given** SFX are on separate tracks
**When** I review the timeline
**Then** I can independently adjust volume, timing, and fade for each SFX

**Given** The gentle_whoosh is placed at 0:00
**When** I examine the timeline
**Then** It is on SFX Track 1 with room to adjust ±2 seconds from AI suggestion

**Given** SFX placement completes
**When** I play the timeline
**Then** Sound effects enhance emotional moments without overwhelming dialogue

**Given** An SFX is slightly off
**When** I want to adjust it
**Then** I can easily move it ±2 seconds or swap it entirely without complex track management

### Story 6.6: Position VFX Templates

As a video editor,
I want the system to position VFX templates at specified timeline locations,
So that lower thirds and effects appear at the right moments automatically.

**Acceptance Criteria:**

**Given** AI has suggested VFX placements (lower third at 0:15, outro CTA at 3:45)
**When** Timeline is created
**Then** VFX templates are positioned at those exact timestamps

**Given** VFX templates are positioned
**When** I review the timeline
**Then** They appear on the timeline as Fusion compositions or generator effects

**Given** Lower thirds are suggested for speaker introductions
**When** They are placed
**Then** They align with the start of dialogue segments

**Given** A template has configurable parameters
**When** It is placed on timeline
**Then** Default values are applied (editable by editor later)

**Given** VFX placement completes
**When** I play the timeline
**Then** Effects appear at the specified moments with default transitions

**Given** Multiple VFX are suggested
**When** They are positioned
**Then** They don't overlap inappropriately (if they do, AI staggers them per format rules)

### Story 6.7: Rough Cut Output for Refinement

As a video editor,
I want to receive the rough cut output for refinement and creative adjustment,
So that I can review the AI's work and make final adjustments before delivery.

**Acceptance Criteria:**

**Given** Timeline creation completes successfully
**When** RoughCut finishes
**Then** The timeline is ready in Resolve with all elements: cut dialogue, music, SFX, VFX

**Given** I review the finished rough cut
**When** I play the timeline
**Then** It runs smoothly showing the 4-minute rough cut with proper pacing

**Given** The rough cut is complete
**When** I assess the AI's work
**Then** Structure is present, pacing works, and 60%+ of suggested assets are usable with minor adjustments

**Given** I discover the perfect music track
**When** It plays during review
**Then** I recognize it as an asset I haven't used in 18 months (per PRD journey)

**Given** I need to make adjustments
**When** I enter refinement mode
**Then** I can: swap one SFX, adjust music levels, refine timing, replace any suggested asset

**Given** I start with raw footage at 2:47 PM
**When** I finish refinement by 3:20 PM
**Then** I have a client-ready rough cut that would have taken 3 hours manually
**And** I've used 4 assets from my previously underutilized collection

<!-- Repeat for each story (M = 1, 2, 3...) within epic N -->

### Story {{N}}.{{M}}: {{story_title_N_M}}

As a {{user_type}},
I want {{capability}},
So that {{value_benefit}}.

**Acceptance Criteria:**

<!-- for each AC on this story -->

**Given** {{precondition}}
**When** {{action}}
**Then** {{expected_outcome}}
**And** {{additional_criteria}}

<!-- End story repeat -->
