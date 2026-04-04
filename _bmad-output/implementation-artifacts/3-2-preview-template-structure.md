# Story 3.2: Preview Template Structure

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a video editor,
I want to preview format template structure and timing specifications,
So that I can understand how the rough cut will be structured before generating it.

## Acceptance Criteria

1. **Given** I select a format template from the list
   **When** I choose to preview it
   **Then** The template structure displays clearly

2. **Given** I preview "YouTube Interview — Corporate" template
   **When** Details display
   **Then** I see timing specifications: "15-second hook with upbeat music, 3-minute narrative section, 30-second outro"

3. **Given** A template has asset group definitions
   **When** Preview shows
   **Then** Template assets are listed (e.g., "standard corporate music bed", "success chime SFX")

4. **Given** The preview displays
   **When** I review the information
   **Then** Structure is human-readable without specialized tools (markdown-based)

## Tasks / Subtasks

- [ ] Extend format template data model (AC: #2, #3, #4)
  - [ ] Add `structure` field to `FormatTemplate` dataclass
  - [ ] Add `timing_specs` field for segment durations
  - [ ] Add `asset_groups` field for template asset definitions
  - [ ] Add `segments` list with timing and purpose for each section
  - [ ] Update `parser.py` to extract body content from markdown

- [ ] Implement markdown template body parser (AC: #4)
  - [ ] Parse markdown sections (Structure, Timing, Asset Groups)
  - [ ] Extract structured data from human-readable markdown
  - [ ] Handle templates with varying section formats gracefully
  - [ ] Support both structured data and free-form description

- [ ] Create template preview protocol method (AC: #1, #2, #3)
  - [ ] Implement `get_template_preview(template_id)` protocol handler
  - [ ] Return full template details: name, description, structure, timing, asset_groups
  - [ ] Include formatted display text for UI rendering
  - [ ] Handle template not found errors gracefully

- [ ] Implement Lua GUI template preview interface (AC: #1, #2, #3, #4)
  - [ ] Create preview view in `formats_manager.lua`
  - [ ] Design layout: Template name (header), Description, Structure sections
  - [ ] Display timing specifications in readable format (e.g., "15s hook", "3m narrative")
  - [ ] Display asset groups as categorized lists (Music, SFX, VFX)
  - [ ] Add "Back to List" and "Use This Template" action buttons
  - [ ] Ensure scrollable view for long templates
  - [ ] Follow Resolve UI conventions for layout and typography

- [ ] Enhance sample format templates (AC: #2, #3, #4)
  - [ ] Update `youtube-interview.md` with structure sections:
    - Structure overview with 3 segments (Hook, Narrative, Outro)
    - Timing specifications (0:00-0:15, 0:15-3:15, 3:15-3:45)
    - Asset groups (intro_music, narrative_bed, outro_chime)
  - [ ] Update `documentary-scene.md` with documentary-specific structure
  - [ ] Update `social-media-short.md` with short-form structure (0-60 seconds)
  - [ ] Ensure all templates follow consistent markdown structure

- [ ] Implement navigation flow (AC: #1)
  - [ ] Click template in list → opens preview view
  - [ ] Preview view shows full details with scroll capability
  - [ ] "Back" button returns to template list
  - [ ] "Use This Template" button available (for Story 3.3 integration)

- [ ] Testing and validation (AC: #1, #2, #3, #4)
  - [ ] Unit tests for markdown body parser (test_parser.py)
  - [ ] Unit tests for preview data model (test_models.py)
  - [ ] Test template with missing sections (graceful degradation)
  - [ ] Test template with extra/malformed sections
  - [ ] Manual test: Verify preview displays correctly in Lua GUI
  - [ ] Test scroll behavior for long templates

## Dev Notes

### Architecture Context

This story **builds upon Story 3.1** and adds the template preview/detail view capability. It establishes the detailed template structure parsing that will be essential for Stories 3.3-3.6.

**Key Architectural Requirements:**
- **Human-Readable Templates**: Templates must remain editable markdown while extracting structured data [Source: prd.md#NFR15]
- **Dual-Purpose Markdown**: Same file serves human editing AND machine parsing [Source: epics.md#Story 3.2]
- **Lua/Python Split**: Lua renders preview UI, Python parses markdown structure [Source: architecture.md#Technical Constraints]
- **Progressive Enhancement**: Templates work with basic or detailed structure definitions [Source: epics.md#Story 3.4]

**Data Flow:**
```
Editor selects template from list in Lua GUI (Story 3.1)
    ↓
Lua sends `get_template_preview(template_id)` via protocol
    ↓
Python parser loads markdown file from `templates/formats/`
    ↓
Parser extracts frontmatter (basic metadata) + body sections (structure)
    ↓
Returns `FormatTemplate` with all fields populated
    ↓
Lua renders preview: name, description, timing specs, asset groups
    ↓
Editor reviews structure before deciding to use template
```

**Dependency on Story 3.1:**
- Uses `FormatTemplate` dataclass created in Story 3.1
- Uses `scanner.py` from Story 3.1 to locate template files
- Uses `formats_manager.lua` UI framework from Story 3.1
- Extends protocol handlers started in Story 3.1

### Project Structure Notes

**Building on Story 3.1 Structure:**
```
src/roughcut/backend/formats/
├── __init__.py
├── scanner.py          # From Story 3.1 - file discovery
├── parser.py           # UPDATED: Parse frontmatter + body sections
├── models.py           # UPDATED: Extended FormatTemplate dataclass
└── preview.py          # NEW: Preview generation and formatting

templates/formats/
├── youtube-interview.md      # UPDATED: Enhanced with structure sections
├── documentary-scene.md     # UPDATED: Enhanced with structure sections
└── social-media-short.md     # UPDATED: Enhanced with structure sections

lua/
├── roughcut.lua
├── formats_manager.lua       # UPDATED: Add preview view
└── protocol.lua
```

**Alignment with Existing Structure:**
- Extends patterns from `src/roughcut/backend/formats/` (created in Story 3.1)
- Follows same Lua GUI patterns as Story 3.1 list view
- Uses same protocol patterns as Stories 1.4-2.7

### Technical Requirements

**Enhanced Markdown Template Structure:**
```markdown
---
name: "YouTube Interview — Corporate"
description: "15-second hook, 3-minute narrative, 30-second outro with music and SFX"
version: "1.0"
---

# YouTube Interview — Corporate Format

## Structure Overview
This format creates engaging interview content optimized for YouTube retention.

## Timing Specifications

### Segment 1: Hook (0:00 - 0:15)
- **Duration**: 15 seconds
- **Purpose**: Grab attention with dynamic music and visual energy
- **Content**: Strong opening statement or compelling question

### Segment 2: Narrative (0:15 - 3:15)  
- **Duration**: 3 minutes
- **Purpose**: Core interview content with supporting B-roll
- **Content**: Main story arc with natural conversation flow

### Segment 3: Outro (3:15 - 3:45)
- **Duration**: 30 seconds
- **Purpose**: Call-to-action with branded music sting
- **Content**: Summary, subscribe prompt, end screen

## Asset Groups

### Music
- **intro_music**: High-energy corporate music (upbeat, professional)
- **narrative_bed**: Subtle background music (corporate, neutral)
- **outro_music**: Branded outro sting with swell

### SFX
- **intro_whoosh**: Subtle entrance sound for title card
- **outro_chime**: Success/triumph sound for call-to-action

### VFX
- **lower_third_intro**: Speaker name and title at 0:15
- **subscribe_animation**: End screen CTA graphics at 3:30
```

**Parser Implementation Strategy:**

1. **Frontmatter Parsing** (from Story 3.1):
   - Already implemented: `name`, `description`
   - Use `python-frontmatter` library

2. **Body Section Parsing** (new in this story):
   - Parse markdown headers (##, ###) to identify sections
   - Extract "Timing Specifications" section into structured segments
   - Extract "Asset Groups" section into categorized lists
   - Support flexible formatting (tables, lists, paragraphs)

3. **Data Model Extension:**
   ```python
   @dataclass
   class TemplateSegment:
       name: str           # "Hook", "Narrative", "Outro"
       start_time: str     # "0:00"
       end_time: str       # "0:15"
       duration: str        # "15 seconds"
       purpose: str        # "Grab attention..."
   
   @dataclass
   class AssetGroup:
       category: str       # "Music", "SFX", "VFX"
       name: str           # "intro_music"
       description: str    # "High-energy corporate..."
       search_tags: List[str]  # ["upbeat", "professional"]
   
   @dataclass
   class FormatTemplate:
       # From Story 3.1:
       id: str
       name: str
       description: str
       file_path: Path
       
       # New in Story 3.2:
       structure: str           # Full structure description
       segments: List[TemplateSegment]
       asset_groups: List[AssetGroup]
       raw_markdown: str        # Full content for display
   ```

**Key Implementation Details:**

1. **Graceful Degradation**:
   - Templates without detailed sections still work
   - Missing timing specs → show "No timing details specified"
   - Missing asset groups → show "No asset groups defined"
   - Parser logs warnings but doesn't fail

2. **Preview Formatting** (Python side):
   - Convert duration strings to readable format
   - Format asset groups by category
   - Generate summary text for Lua display
   - Include formatted timing line: "Hook → 0:00-0:15 (15s)"

3. **Lua UI Layout:**
   ```lua
   -- Preview View Structure
   Header: Template Name (large, bold)
   Section: Description (wrapped text)
   Section: Structure Overview
   Section: Timing Specifications (table-like)
     - Hook: 0:00-0:15 (15 seconds)
     - Narrative: 0:15-3:15 (3 minutes)
     - Outro: 3:15-3:45 (30 seconds)
   Section: Asset Groups (categorized)
     - Music: intro_music, narrative_bed, outro_music
     - SFX: intro_whoosh, outro_chime
   Footer: [Back to List] [Use This Template]
   ```

4. **Protocol Response Format:**
   ```json
   {
     "preview": {
       "id": "youtube-interview",
       "name": "YouTube Interview — Corporate",
       "description": "15-second hook, 3-minute narrative...",
       "structure": "This format creates engaging interview...",
       "segments": [
         {
           "name": "Hook",
           "start_time": "0:00",
           "end_time": "0:15",
           "duration": "15 seconds",
           "purpose": "Grab attention with dynamic music..."
         }
       ],
       "asset_groups": [
         {
           "category": "Music",
           "name": "intro_music",
           "description": "High-energy corporate music"
         }
       ],
       "formatted_display": "Hook → 0:00-0:15 (15s)\nNarrative → 0:15-3:15 (3m)..."
     }
   }
   ```

### Dependencies

**Python Libraries:**
- `python-frontmatter` - Already added in Story 3.1
- `markdown` or `mistune` - Optional: for rendering markdown to display text
- Standard library: `re` for parsing timing patterns

**No New Lua Dependencies** - Use existing UI framework from Story 3.1

### Error Handling Strategy

Following patterns from Stories 3.1, 2.2-2.7:

1. **Template Not Found**:
   - Return structured error: `{"error": {"code": "TEMPLATE_NOT_FOUND", "message": "..."}}`
   - Lua shows error dialog with "Back to List" option

2. **Malformed Template Sections**:
   - Log warning: "Template 'youtube-interview.md' has malformed timing section"
   - Still return preview with available data
   - Show "[Incomplete Template]" notice in UI

3. **Parser Errors**:
   - Return fallback preview with just name/description
   - Include error field: `"parse_error": "Could not extract timing specifications"`
   - UI shows basic info with error notice

### Performance Considerations

From Story 3.1 patterns:
- Templates are parsed on preview request (not cached)
- Expect <50KB per template file (markdown is small)
- Parsing is fast (<100ms for typical template)
- No pagination needed

### Previous Story Intelligence

**Lessons from Story 3.1 (View Format Templates):**
- Scanner pattern using `pathlib.Path` works well
- `python-frontmatter` library is reliable
- Lua/Python protocol is stable for this data size
- Resolve UI conventions: headers bold, body text regular, buttons at bottom

**Patterns to Continue:**
- Same `formats/` module structure
- Same protocol handler pattern
- Same error handling philosophy (graceful degradation)
- Same UI layout conventions

### References

- [Source: epics.md#Story 3.2] - Story requirements and acceptance criteria
- [Source: _bmad-output/implementation-artifacts/3-1-view-format-templates.md] - Previous story patterns
- [Source: architecture.md#Naming Patterns] - Naming conventions
- [Source: architecture.md#Technical Constraints] - Lua/Python split constraints
- [Source: prd.md#NFR15] - Human-readable template syntax requirement
- [Source: epics.md#Story 3.4] - Template loading requirements (markdown parsing)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

## Story Completion Status

**Status:** ready-for-dev

**Completion Note:** Ultimate context engine analysis completed - comprehensive developer guide created

**Next Steps:**
1. Review story with development team
2. Run `dev-story` for implementation
3. Run `code-review` when complete
