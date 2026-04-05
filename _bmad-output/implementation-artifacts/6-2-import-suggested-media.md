# Story 6.2: Import Suggested Media

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a video editor,
I want the system to import suggested media from local storage to the timeline,
So that all AI-recommended assets are available in the edit without manual importing.

## Acceptance Criteria

**AC1: File path resolution**
- **Given** AI has suggested specific music, SFX, and VFX assets
- **When** Timeline creation begins
- **Then** RoughCut locates each file using stored absolute paths

**AC2: File existence validation (NFR10)**
- **Given** File paths are validated
- **When** Media import starts
- **Then** System checks each file exists and is accessible before import (per NFR10)

**AC3: Media Pool integration**
- **Given** All suggested media files exist
- **When** Import proceeds
- **Then** They are added to Resolve's Media Pool if not already present

**AC4: Progress indication**
- **Given** Media is being imported
- **When** Progress displays
- **Then** Status shows: "Importing: epic_whoosh.wav", "Importing: corporate_theme.mp3", etc.

**AC5: Missing file handling**
- **Given** A suggested media file is missing
- **When** Validation occurs
- **Then** RoughCut displays: "Warning: [filename] not found at [path] - will be skipped"
- **And** Timeline creation continues with available assets

## Tasks / Subtasks

- [x] Task 1 (AC: #1, #2) - Implement file path resolution and validation
  - [x] Subtask 1.1 - Create `importer.py` in `src/roughcut/backend/timeline/` with `MediaImporter` class
  - [x] Subtask 1.2 - Implement `resolve_file_paths()` method to locate media using stored absolute paths from SpacetimeDB
  - [x] Subtask 1.3 - Implement `validate_file_accessibility()` method to check file exists and is readable (NFR10)
  - [x] Subtask 1.4 - Handle path resolution errors gracefully with structured error responses

- [x] Task 2 (AC: #3) - Implement Media Pool import
  - [x] Subtask 2.1 - Implement `import_to_media_pool()` method using Resolve API
  - [x] Subtask 2.2 - Check for duplicate media in Media Pool to avoid re-importing
  - [x] Subtask 2.3 - Support importing music files (.mp3, .wav, .aiff)
  - [x] Subtask 2.4 - Support importing SFX files (.wav, .mp3)
  - [x] Subtask 2.5 - Support importing VFX templates (.comp, .settings, .drfx)
  - [x] Subtask 2.6 - Return media pool references for use by subsequent stories

- [x] Task 3 (AC: #4) - Add progress reporting
  - [x] Subtask 3.1 - Send progress updates for each file being imported via JSON protocol
  - [x] Subtask 3.2 - Format: "Importing: {filename}" for each media file
  - [x] Subtask 3.3 - Report total progress: "Imported X of Y media files"
  - [x] Subtask 3.4 - Ensure progress updates never exceed 5 seconds apart (NFR4)

- [x] Task 4 (AC: #5) - Implement missing file handling
  - [x] Subtask 4.1 - Create `validate_media_batch()` method to check all suggested media before import
  - [x] Subtask 4.2 - Generate warnings for missing files: "Warning: [filename] not found at [path] - will be skipped"
  - [x] Subtask 4.3 - Continue timeline creation with available assets (don't fail on missing files)
  - [x] Subtask 4.4 - Return list of skipped files in response for Lua GUI to display

- [x] Task 5 - Create JSON-RPC protocol handlers
  - [x] Subtask 5.1 - Add `import_suggested_media` method handler in `src/roughcut/protocols/handlers/timeline.py`
  - [x] Subtask 5.2 - Accept parameters: `timeline_id`, `suggested_media` list with file paths
  - [x] Subtask 5.3 - Return result with: `imported_count`, `skipped_files`, `media_pool_refs`
  - [x] Subtask 5.4 - Implement error responses with structured error objects per architecture spec

- [x] Task 6 - Implement Lua GUI integration
  - [x] Subtask 6.1 - Modify `rough_cut_review_window.lua` to call `import_suggested_media` after timeline creation
  - [x] Subtask 6.2 - Display progress dialog showing "Importing: [filename]" updates
  - [x] Subtask 6.3 - Display warnings for any skipped/missing files
  - [x] Subtask 6.4 - Handle completion and proceed to next story (6.3 - Cut Footage)

- [x] Task 7 - Error handling and recovery
  - [x] Subtask 7.1 - Handle file permission errors (file exists but not accessible)
  - [x] Subtask 7.2 - Handle network path unavailability (assets on NAS/server)
  - [x] Subtask 7.3 - Handle unsupported file formats gracefully
  - [x] Subtask 7.4 - Provide actionable error messages per NFR13

## Technical Context

### Architecture Compliance

**Layer Separation (CRITICAL - MUST FOLLOW):**
- **Lua Layer (`lua/`):** GUI only - display progress, show import status, display warnings
- **Python Layer (`src/roughcut/backend/timeline/`):** All media import business logic
- **Communication:** JSON-RPC protocol over stdin/stdout ONLY - never direct imports between layers

**Key Files to Create/Modify:**
- `src/roughcut/backend/timeline/importer.py` - MediaImporter class (NEW)
- `src/roughcut/backend/timeline/builder.py` - May need to integrate importer (MODIFY)
- `src/roughcut/protocols/handlers/timeline.py` - Add `import_suggested_media` handler (MODIFY)
- `lua/ui/rough_cut_review_window.lua` - Add import progress display (MODIFY)

### Technical Requirements

**From PRD (Functional Requirements):**
- FR28: System can import suggested media from local storage to the timeline
- FR27: Foundation established in Story 6.1 (timeline exists to import into)

**From PRD (Non-Functional Requirements - MUST FOLLOW):**
- NFR4: System shall display progress indicators for operations exceeding 5 seconds
- NFR5: Lua GUI shall remain responsive during Python backend processing operations
- NFR9: System shall create timelines non-destructively (media import is non-destructive to source)
- NFR10: System shall validate file paths before operations and provide clear error messages
- NFR11: System shall gracefully handle Resolve API unavailability with clear error messages
- NFR13: All user-facing errors shall include actionable recovery guidance
- NFR14: GUI shall follow Resolve UI conventions for consistency with host application

**API Integration Requirements:**
- Must use Resolve's Lua API for Media Pool operations
- Must handle file system operations via Python (Lua is sandboxed)
- Must support media types: Music (audio), SFX (audio), VFX (templates)
- Must check file existence before attempting import (NFR10)

### Naming Conventions (STRICT - FOLLOW EXACTLY)

**Python Layer:**
- Functions/variables: `snake_case` - e.g., `import_media()`, `file_path`
- Classes: `PascalCase` - e.g., `MediaImporter`, `ImportResult`
- Constants: `SCREAMING_SNAKE_CASE` - e.g., `SUPPORTED_AUDIO_FORMATS`, `MAX_FILE_SIZE_MB`

**Lua Layer:**
- Functions/variables: `camelCase` - e.g., `importMedia()`, `filePath`
- GUI components: `PascalCase` - e.g., `ImportProgressDialog`, `MediaImportStatus`

**JSON Protocol:**
- Field names: `snake_case` - e.g., `"file_path"`, `"media_type"`

### JSON-RPC Communication Protocol (MUST IMPLEMENT CORRECTLY)

**Request format (Lua → Python):**
```json
{
  "method": "import_suggested_media",
  "params": {
    "timeline_id": "timeline_12345",
    "suggested_media": [
      {
        "file_path": "/absolute/path/to/corporate_theme.mp3",
        "media_type": "music",
        "usage": "intro_bed"
      },
      {
        "file_path": "/absolute/path/to/epic_whoosh.wav",
        "media_type": "sfx",
        "usage": "intro_transition"
      },
      {
        "file_path": "/absolute/path/to/lower_third.comp",
        "media_type": "vfx",
        "usage": "title_card"
      }
    ]
  },
  "id": "req_import_001"
}
```

**Response format (Python → Lua):**
```json
{
  "result": {
    "imported_count": 2,
    "skipped_count": 1,
    "media_pool_refs": [
      {
        "file_path": "/absolute/path/to/corporate_theme.mp3",
        "media_pool_id": "media_001",
        "media_type": "music"
      },
      {
        "file_path": "/absolute/path/to/epic_whoosh.wav",
        "media_pool_id": "media_002",
        "media_type": "sfx"
      }
    ],
    "skipped_files": [
      {
        "file_path": "/absolute/path/to/lower_third.comp",
        "reason": "file_not_found",
        "message": "File not found at specified path"
      }
    ]
  },
  "error": null,
  "id": "req_import_001"
}
```

**Error format:**
```json
{
  "result": null,
  "error": {
    "code": "FILE_ACCESS_DENIED",
    "category": "file_system",
    "message": "Cannot access file: permission denied",
    "recoverable": true,
    "suggestion": "Check file permissions and ensure Resolve has access to the media folder"
  },
  "id": "req_import_001"
}
```

**Progress format:**
```json
{
  "type": "progress",
  "operation": "import_media",
  "current": 1,
  "total": 3,
  "message": "Importing: corporate_theme.mp3"
}
```

### Media Type Support

**Supported Audio Formats (Music & SFX):**
- `.mp3` - MPEG Layer-3 Audio
- `.wav` - Waveform Audio (uncompressed)
- `.aiff` - Audio Interchange File Format
- `.m4a` - MPEG-4 Audio (optional support)

**Supported VFX Template Formats:**
- `.comp` - Fusion composition files
- `.settings` - Resolve/Fusion settings files
- `.drfx` - DaVinci Resolve effects files

**File Validation Requirements (NFR10):**
1. File must exist at specified absolute path
2. File must be readable (permission check)
3. File extension must be in supported formats list
4. File size should be reasonable (>0 bytes, < reasonable max)

## Dev Notes

### Critical Implementation Notes

**1. Path Validation (NFR10) - CRITICAL:**
- ALWAYS validate file exists before attempting import
- ALWAYS use absolute paths (never relative)
- Check file is readable, not just exists
- Handle network paths (NAS/server) gracefully with timeouts
- Return structured error with specific file that failed

**2. Media Pool Duplicate Detection:**
- Check if media already exists in Resolve Media Pool before importing
- Use file path and size/modification time for comparison
- If duplicate found, return existing Media Pool reference
- Avoid creating duplicate entries in Media Pool

**3. Non-Destructive Import (NFR9):**
- Importing to Media Pool is non-destructive (read-only on source)
- Never modify source files during import
- Media Pool creates references, doesn't move/copy files

**4. Batch Validation Pattern:**
```python
# Recommended approach from Story 6.1 learnings:
def validate_media_batch(suggested_media):
    valid_files = []
    skipped_files = []
    
    for media in suggested_media:
        if validate_file_accessibility(media['file_path']):
            valid_files.append(media)
        else:
            skipped_files.append({
                'file_path': media['file_path'],
                'reason': 'file_not_found_or_inaccessible'
            })
    
    return valid_files, skipped_files
```

**5. Error Recovery Patterns (from Story 6.1 learnings):**
- Missing individual files should NOT fail entire operation
- Continue with available assets, report skipped files
- Provide specific error messages per file
- Include actionable suggestions in error responses

**6. Progress Reporting Requirements:**
- Send progress for EACH file being imported
- Never go >5 seconds without progress update (NFR4)
- Include filename in progress message for user clarity
- Report completion count vs total

### Dependencies on Previous Stories

**Direct Dependencies:**
- **Story 6.1 (Create New Timeline)** - MUST be completed first
  - Timeline must exist before media can be imported
  - Media Pool belongs to a project/timeline context
  - Returns `timeline_id` needed for media import context

**Code Dependencies from Story 6.1:**
- `src/roughcut/backend/timeline/builder.py` - TimelineBuilder class
- `src/roughcut/backend/timeline/resolve_api.py` - ResolveApi wrapper
- `src/roughcut/protocols/handlers/timeline.py` - Existing handler structure
- Timeline track structure already established (music, SFX, VFX tracks)

**Foundation for Next Stories:**
- Story 6.3: Cut Footage to Segments - needs Media Pool references from this story
- Story 6.4: Place Music on Timeline - needs music Media Pool references
- Story 6.5: Layer SFX on Timeline - needs SFX Media Pool references
- Story 6.6: Position VFX Templates - needs VFX Media Pool references

### Data Source for Media Paths

**SpacetimeDB Media Asset Storage:**
Media paths come from the AI rough cut generation (Story 5.x series):
- Stored in SpacetimeDB during asset indexing (Epic 2)
- Retrieved by AI matching process (Epic 5)
- Passed to this story as `suggested_media` list with absolute paths

**Expected Data Structure:**
```python
suggested_media = [
    {
        "file_path": "/Users/editor/Music/Corporate/upbeat_theme.mp3",
        "media_type": "music",
        "ai_matched": True,
        "confidence_score": 0.85,
        "usage_context": "intro_bed"
    },
    # ... more media items
]
```

### Project Structure Notes

**Directory Structure:**
```
src/roughcut/backend/timeline/
├── __init__.py
├── builder.py          # EXISTS from Story 6.1
├── track_manager.py    # EXISTS from Story 6.1
├── resolve_api.py      # EXISTS from Story 6.1
└── importer.py         # NEW - MediaImporter class

src/roughcut/protocols/handlers/
├── __init__.py
├── media.py            # EXISTS
├── ai.py               # EXISTS
└── timeline.py         # MODIFY - add import_suggested_media handler

lua/ui/
└── rough_cut_review_window.lua  # MODIFY - add import progress UI
```

### Testing Notes

**Manual Testing Scenarios:**
1. Import valid music file - verify appears in Media Pool
2. Import valid SFX file - verify appears in Media Pool
3. Import valid VFX template - verify appears in Media Pool
4. Test duplicate detection - import same file twice, verify no duplicate
5. Test missing file handling - provide non-existent path, verify warning displayed
6. Test permission error - use unreadable file, verify actionable error
7. Test progress reporting - verify "Importing: filename" messages
8. Test batch import - import 5+ files, verify all handled correctly

**Integration Test Points:**
- Lua → Python protocol communication for import method
- Python file system validation
- Resolve Media Pool API integration
- Error handling and message propagation
- Progress reporting accuracy

**Unit Test Requirements:**
- Test MediaImporter class methods
- Test file validation logic (exists, readable, format support)
- Test duplicate detection logic
- Test error response generation
- Mock Resolve API for testing

## Dev Agent Record

### Agent Model Used

OpenCode Agent (accounts/fireworks/routers/kimi-k2p5-turbo)

### Debug Log References

No critical issues encountered during implementation.

### Completion Notes List

**Implementation Summary:**
- Created comprehensive `MediaImporter` class in `src/roughcut/backend/timeline/importer.py`
- All 5 acceptance criteria satisfied (AC1-AC5)
- File path validation with NFR10 compliance (exists, readable, format support)
- Media Pool duplicate detection prevents re-importing existing media
- Progress reporting with "Importing: filename" format per NFR4
- Graceful missing file handling - continues with available assets
- Error responses include actionable guidance per NFR13

**Technical Decisions:**
1. **MediaImporter** - Central class handling all media import logic
2. **ImportResult** - Dataclass for structured import results with skipped file tracking
3. **MediaPoolReference** - Dataclass for Media Pool reference tracking
4. **Batch validation pattern** - Validates all files before import, separates valid from invalid
5. **Duplicate detection** - Uses `find_media_in_pool()` to check for existing media before import
6. **Progress callback** - Optional callback for real-time progress updates
7. **Error resilience** - Individual file failures don't fail entire operation

**Architecture Compliance:**
- Python layer: All business logic in `importer.py`
- JSON-RPC protocol: Structured error responses per architecture spec
- Lua layer: GUI integration in `rough_cut_review_window.lua`
- Naming conventions: snake_case for Python, camelCase for Lua
- Layer separation: No direct Python/Lua imports, only protocol communication

**Testing:**
- Comprehensive unit tests created in `tests/unit/backend/timeline/test_importer.py`
- Tests cover: validation, batch processing, duplicate detection, progress callbacks, error handling
- Handler tests added to `tests/unit/protocols/handlers/test_timeline.py`
- Mock-based testing for Resolve API interactions

**Files Created/Modified:**
- NEW: `src/roughcut/backend/timeline/importer.py` (346 lines)
- NEW: `tests/unit/backend/timeline/test_importer.py` (437 lines)
- MODIFY: `src/roughcut/backend/timeline/__init__.py` - Added exports
- MODIFY: `src/roughcut/backend/timeline/resolve_api.py` - Added `find_media_in_pool()` and `import_media_to_pool()`
- MODIFY: `src/roughcut/protocols/handlers/timeline.py` - Added `import_suggested_media` handler
- MODIFY: `tests/unit/protocols/handlers/test_timeline.py` - Added handler tests
- MODIFY: `lua/ui/rough_cut_review_window.lua` - Added import integration and progress UI

### File List

**New Files Created:**
1. `src/roughcut/backend/timeline/importer.py` - MediaImporter class (346 lines) with ImportResult and MediaPoolReference dataclasses
2. `tests/unit/backend/timeline/test_importer.py` - Comprehensive unit tests (437 lines) covering all importer functionality

**Modified Files:**
1. `src/roughcut/backend/timeline/__init__.py` - Added MediaImporter, ImportResult, MediaPoolReference exports
2. `src/roughcut/backend/timeline/resolve_api.py` - Added `find_media_in_pool()` and `import_media_to_pool()` methods
3. `src/roughcut/protocols/handlers/timeline.py` - Added `import_suggested_media` handler and ERROR_CODES
4. `tests/unit/protocols/handlers/test_timeline.py` - Added import_suggested_media handler tests (8 new test methods)
5. `lua/ui/rough_cut_review_window.lua` - Added `_importSuggestedMediaAsync()`, `_importSuggestedMediaInternal()`, updated `_showLoadingState()`, updated `_showTimelineCreatedSuccess()`

## References

**Epic Context:**
- Epic 6: Timeline Creation & Media Placement [Source: _bmad-output/planning-artifacts/epics.md#Epic 6]
- Story 6.1: Create New Timeline - MUST be completed first [Source: _bmad-output/implementation-artifacts/6-1-create-new-timeline.md]
- Story 6.2 detailed requirements [Source: _bmad-output/planning-artifacts/epics.md#Story 6.2]

**PRD Requirements:**
- FR28: Import suggested media [Source: _bmad-output/planning-artifacts/prd.md#Timeline Creation & Media Placement]
- NFR4: Progress indicators [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements]
- NFR5: Responsive GUI [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements]
- NFR9: Non-destructive operations [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements]
- NFR10: File path validation [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements]
- NFR11: Graceful API unavailability handling [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements]
- NFR13: Actionable error messages [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements]

**Architecture Decisions:**
- Media importer pattern [Source: _bmad-output/planning-artifacts/architecture.md#Timeline Creation]
- Timeline module structure [Source: _bmad-output/planning-artifacts/architecture.md#Requirements to Structure Mapping]
- Lua/Python layer separation [Source: _bmad-output/planning-artifacts/architecture.md#Lua ↔ Python Communication Protocol]
- Naming conventions [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns]
- JSON-RPC protocol format [Source: _bmad-output/planning-artifacts/architecture.md#Format Patterns]

**Previous Story Intelligence:**
- Story 6.1 code review fixes [Source: _bmad-output/implementation-artifacts/6-1-create-new-timeline.md]
  - Validation patterns: empty config handling, input length limits
  - Error handling: specific exceptions, cleanup on failure
  - API patterns: AddTrack fallback handling
- Story 6.1 file structure [Source: git commit 8821868]
  - Timeline module established: builder.py, track_manager.py, resolve_api.py
  - Protocol handlers in timeline.py
  - Test structure mirroring source

**Related Stories:**
- Story 6.1: Create New Timeline - prerequisite, provides timeline_id [Source: _bmad-output/implementation-artifacts/6-1-create-new-timeline.md]
- Story 6.3: Cut Footage to Segments - next story, uses Media Pool refs from this story [Source: _bmad-output/planning-artifacts/epics.md#Story 6.3]

---

**Story Key:** 6-2-import-suggested-media  
**Epic:** 6 - Timeline Creation & Media Placement  
**Created:** 2026-04-04  
**Status:** ready-for-dev  
**Notes:** Second story in Epic 6. Depends on Story 6.1 timeline creation. Foundation for media placement stories (6.3-6.6).
