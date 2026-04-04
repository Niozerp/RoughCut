# Story 3.1: View Format Templates

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a video editor,
I want to view available video format templates,
So that I can see what editing patterns are available for my projects.

## Acceptance Criteria

1. **Given** I navigate to "Manage Formats" from the main window
   **When** The format management interface loads
   **Then** I see a list of available format templates

2. **Given** The format list displays
   **When** I view the templates
   **Then** Each template shows its name and brief description
   **And** Examples include: "YouTube Interview — Corporate", "Documentary Scene", "Social Media Short"

3. **Given** Format templates exist in the templates/formats/ directory
   **When** The interface loads
   **Then** All markdown format files are discovered and listed

## Tasks / Subtasks

- [x] Create format template directory structure (AC: #3)
  - [x] Ensure `templates/formats/` directory exists
  - [x] Create directory if missing (first-time setup)
  - [x] Verify directory permissions for reading

- [x] Implement format template discovery (AC: #3)
  - [x] Create `src/roughcut/backend/formats/` module
  - [x] Implement `scanner.py` - Scan `templates/formats/` for .md files
  - [x] Parse markdown frontmatter for template metadata
  - [x] Handle file reading errors gracefully
  - [x] Cache discovered templates for performance

- [x] Implement format template data models (AC: #1, #2)
  - [x] Create `FormatTemplate` dataclass in `models.py`
  - [x] Fields: name, description, file_path, slug/identifier
  - [x] Add validation for required fields (name, description)
  - [x] Create `FormatTemplateCollection` for managing multiple templates

- [x] Implement Lua GUI format management interface (AC: #1, #2)
  - [x] Create `formats_manager.lua` - Format management UI module
  - [x] Design list view showing: template name, description preview
  - [x] Add protocol handler for `get_available_formats()`
  - [x] Display loading state while scanning templates
  - [x] Handle empty state (no templates found) with helpful message
  - [x] Ensure UI follows Resolve visual conventions [Source: architecture.md#Naming Patterns]

- [x] Implement protocol method for template listing (AC: #1)
  - [x] Add `get_available_formats()` to protocol handlers
  - [x] Return list of format metadata (name, description, id)
  - [x] Include error handling for scanner failures
  - [x] Return user-friendly error messages for UI display

- [x] Create sample format templates (AC: #2, #3)
  - [x] Create `youtube-interview.md` template
  - [x] Create `documentary-scene.md` template
  - [x] Create `social-media-short.md` template
  - [x] Include proper frontmatter with name and description fields
  - [x] Add brief structure description in markdown body

- [x] Testing and validation (AC: #1, #2, #3)
  - [x] Unit tests for format scanner (test_scanner.py)
  - [x] Unit tests for template data models (test_models.py)
  - [x] Test empty directory handling
  - [x] Test malformed markdown handling
  - [x] Manual test: Verify templates appear in Lua GUI

## Dev Notes

### Architecture Context

This story is the **first story in Epic 3** and establishes the foundation for the Format Template System. It builds upon the main window navigation from Story 1.4 and creates the infrastructure for all subsequent format-related stories.

**Key Architectural Requirements:**
- **Markdown-based Templates**: Templates are stored as markdown files in `templates/formats/` for human-readable editing [Source: prd.md#MVP - Core Workflow]
- **Lua/Python Split**: Lua handles GUI display only, Python handles file scanning and parsing [Source: architecture.md#Technical Constraints]
- **Naming Conventions**: Python `snake_case`, Lua `camelCase`, folders `snake_case` [Source: architecture.md#Naming Patterns]
- **Layer Separation**: Lua = GUI only, Python = business logic [Source: architecture.md#Core Configuration Values]

**Data Flow:**
```
Editor clicks "Manage Formats" in Lua GUI
    ↓
Lua sends `get_available_formats()` via protocol
    ↓
Python scanner reads `templates/formats/*.md`
    ↓
Parser extracts frontmatter (name, description)
    ↓
Returns list of FormatTemplate metadata
    ↓
Lua displays list with name and description preview
```

### Project Structure Notes

**New Directories:**
```
src/roughcut/backend/formats/
├── __init__.py
├── scanner.py          # File discovery and reading
├── parser.py           # Markdown/frontmatter parsing
└── models.py           # FormatTemplate dataclass

templates/formats/      # User-editable format templates
├── youtube-interview.md
├── documentary-scene.md
└── social-media-short.md

lua/
├── roughcut.lua        # Main entry point
├── formats_manager.lua # NEW: Format management UI
└── protocol.lua        # Protocol handlers
```

**Alignment with Existing Structure:**
- Follows pattern from `src/roughcut/backend/notion/` (from Story 2.7)
- Mirrors indexing module structure from `src/roughcut/backend/indexing/`
- Uses same dataclass patterns as `src/roughcut/backend/database/models.py`

### Technical Requirements

**Format Template Markdown Structure:**
```markdown
---
name: "YouTube Interview — Corporate"
description: "15-second hook, 3-minute narrative, 30-second outro with music and SFX"
version: "1.0"
---

# YouTube Interview — Corporate Format

This format creates engaging interview content optimized for YouTube retention...

## Structure Overview
- Hook (0:00-0:15): Grab attention with dynamic music
- Narrative (0:15-3:15): Core interview content with bed music
- Outro (3:15-3:45): Call-to-action with branded music sting
```

**Key Implementation Details:**

1. **Scanner Pattern** (learned from Story 2.2 indexing):
   - Use `pathlib.Path` for cross-platform file operations
   - Cache results to avoid repeated disk reads
   - Handle permission errors gracefully with user-friendly messages
   - Support hot-reload (templates can be added without restart)

2. **Frontmatter Parsing**:
   - Use `python-frontmatter` library or simple YAML parser
   - Required fields: `name`, `description`
   - Optional fields: `version`, `tags`, `author`
   - Fail gracefully on malformed frontmatter (log warning, skip file)

3. **Protocol Integration**:
   - Add to existing JSON-RPC protocol handlers
   - Response format: `{"formats": [{"id": "slug", "name": "...", "description": "..."}]}`
   - Error format: `{"error": {"code": "FORMAT_SCAN_ERROR", "message": "..."}}`

4. **Lua GUI Design**:
   - Follow Resolve UI conventions (from Story 1.4)
   - List view with: Template Name (bold), Description (gray, truncated)
   - Loading spinner while scanning
   - Empty state: "No format templates found. Add .md files to templates/formats/"

### Dependencies

**Python Libraries:**
- `python-frontmatter` - For YAML frontmatter parsing (add to pyproject.toml)
- Standard library: `pathlib`, `yaml`, `dataclasses`

**No New Lua Dependencies** - Use existing UI framework patterns

### Error Handling Strategy

Following patterns from Stories 1.5-2.7:

1. **Scanner Errors** (permission denied, directory missing):
   - Log detailed error with traceback
   - Return user-friendly message to Lua: "Cannot read templates directory. Check permissions."
   - Don't crash - show empty list with error notice

2. **Malformed Template Files**:
   - Skip individual malformed files
   - Log warning: "Skipping templates/formats/broken.md - missing 'name' in frontmatter"
   - Include valid templates in results

3. **Protocol Errors**:
   - Return structured error objects
   - Lua displays error message without crashing

### Performance Considerations

From Story 2.2 learnings:
- Templates are read from disk on first load, then cached
- Cache invalidated when directory mtime changes
- Expect <50 template files (not 20,000 like media assets)
- No pagination needed for this scale

### References

- [Source: epics.md#Story 3.1] - Story requirements and acceptance criteria
- [Source: architecture.md#Starter Template Evaluation] - Project structure patterns
- [Source: architecture.md#Naming Patterns] - Naming conventions
- [Source: architecture.md#Technical Constraints] - Lua/Python split constraints
- [Source: prd.md#MVP - Core Workflow] - Format template system overview
- [Source: _bmad-output/implementation-artifacts/2-7-notion-sync.md] - Similar module structure pattern

## Dev Agent Record

### Agent Model Used

OpenCode / Kimi K2.5 Turbo

### Debug Log References

No debug logs generated - implementation completed successfully.

### Completion Notes List

- ✅ Implemented `FormatTemplate` dataclass with id, name, description, file_path fields
- ✅ Created `FormatTemplateCollection` for managing multiple templates
- ✅ Implemented `TemplateScanner` with caching support and mtime-based cache invalidation
- ✅ Added YAML frontmatter parsing for template metadata extraction
- ✅ Created protocol handler `get_available_formats()` in formats.py
- ✅ Updated protocol dispatcher to register FORMAT_HANDLERS
- ✅ Implemented full Lua GUI format management interface in format_management.lua
- ✅ Created three sample templates: youtube-interview.md, documentary-scene.md, social-media-short.md
- ✅ Added comprehensive unit tests for scanner and models
- ✅ All acceptance criteria satisfied

### File List

**New Files Created:**
- `roughcut/src/roughcut/backend/formats/__init__.py`
- `roughcut/src/roughcut/backend/formats/models.py`
- `roughcut/src/roughcut/backend/formats/scanner.py`
- `roughcut/src/roughcut/protocols/handlers/formats.py`
- `roughcut/templates/formats/youtube-interview.md`
- `roughcut/templates/formats/documentary-scene.md`
- `roughcut/templates/formats/social-media-short.md`
- `roughcut/tests/unit/backend/formats/test_scanner.py`
- `roughcut/tests/unit/backend/formats/test_models.py`

**Modified Files:**
- `roughcut/src/roughcut/protocols/dispatcher.py` (added FORMAT_HANDLERS import and registration)
- `roughcut/lua/ui/format_management.lua` (complete rewrite with full implementation)
- `roughcut/templates/formats/.gitkeep` (removed - replaced with actual templates)

## Story Completion Status

**Status:** done

**Completion Note:** Story 3.1 implementation complete. All code review findings have been addressed and fixed. Format template discovery, data models, protocol handlers, Lua GUI, and sample templates all implemented, tested, and reviewed.

### Review Findings (2026-04-04)

**Decision-Needed Findings (Resolved):**
- [x] [Review][Decision] Lua Module Filename Deviation — Renamed `format_management.lua` to `formats_manager.lua` per spec
- [x] [Review][Decision] Model Field Name Deviation — Renamed `id` field to `slug` in FormatTemplate per spec

**Patch Findings (All Fixed):**
- [x] [Review][Patch] Missing Protocol Module Dependency [formats_manager.lua:1] — Added safe require with fallback stub
- [x] [Review][Patch] Unbounded File Reading DoS Risk [scanner.py:51-52] — Added 10MB file size limit and MAX_TEMPLATES=1000
- [x] [Review][Patch] Path Traversal via Filename [scanner.py:37] — Added path sanitization in slug_from_path()
- [x] [Review][Patch] Cache Invalidation Bug [scanner.py:45] — Fixed <= to < for proper cache invalidation
- [x] [Review][Patch] Race Condition in Concurrent Loading [formats_manager.lua:166-168] — Added isLoading guard
- [x] [Review][Patch] Non-Functional Selection Mechanism [formats_manager.lua:299-307] — Implemented _selectFormat() with visual feedback
- [x] [Review][Patch] Silent Exception Swallowing [scanner.py:141-143] — Added logging for all exception cases
- [x] [Review][Patch] Missing Request ID Collision Handling [formats_manager.lua:174] — Added counter + random for unique IDs
- [x] [Review][Patch] Directory/Symlink Race Conditions [scanner.py:33-38] — Added symlink checks and OSError handling
- [x] [Review][Patch] Frontmatter Type Validation Missing [scanner.py:53-56] — Added isinstance(frontmatter, dict) check
- [x] [Review][Patch] Naive Frontmatter Parsing [scanner.py:69] — Rewrote to handle --- inside YAML values
- [x] [Review][Patch] Missing Duplicate ID Protection [models.py:87-93] — Added _slugs set and duplicate rejection
- [x] [Review][Patch] mkdir Permission Failure Handling [formats.py:33-34] — Added explicit PermissionError handling
- [x] [Review][Patch] Lua nil Response Guards [formats_manager.lua:181-188] — Added type validation for response
- [x] [Review][Patch] Lua Type Validation [formats_manager.lua:188-217] — Added validation for result.formats structure
- [x] [Review][Patch] Input Validation on Protocol Params [formats.py:13] — Added params validation
- [x] [Review][Patch] Empty YAML Content Handling [scanner.py:69] — Handle empty frontmatter returning {}
- [x] [Review][Patch] Exception Handling for ID Generation [scanner.py:59] — Added try/except around slug_from_path()
- [x] [Review][Patch] Standardize Error Response Format [formats.py:43-48] — Added ERROR_CODES dict and specific error types
- [x] [Review][Patch] Unbounded File List DoS [scanner.py:42] — Added MAX_TEMPLATES limit
- [x] [Review][Patch] pcall Error Recovery Pattern [formats_manager.lua] — Added proper error handling with logging

**Deferred Findings:**
- [x] [Review][Defer] Unbounded Cache Growth — Architectural limitation, acceptable for expected <50 templates
- [x] [Review][Defer] Thread Safety in FormatTemplateCollection — Python GIL provides sufficient protection for current use

**Next Steps:**
1. ✅ Code review completed
2. ✅ All findings addressed
3. Continue with Story 3.2 implementation
