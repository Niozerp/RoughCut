# Story 6.3: Cut Footage to Segments

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a video editor,
I want the system to cut video footage according to AI-recommended transcript segments,
So that the dialogue follows the format structure without manual cutting.

## Acceptance Criteria

**AC1: Cut source footage to AI-recommended segments**
- **Given** AI has determined transcript segments (e.g., 0:15-1:45, 2:30-4:15)
- **When** Timeline is created
- **Then** Source clip is cut and placed on the timeline according to these segments

**AC2: Sequential segment placement on timeline**
- **Given** Segments are placed
- **When** Timeline displays
- **Then** They appear sequentially on the dialogue/video track
- **And** Transitions between segments are clean cuts (no effects by default)

**AC3: Timeline duration reduction**
- **Given** The 38-minute interview is cut
- **When** Timeline is complete
- **Then** It contains ~4 minutes of selected footage in 3 narrative segments

**AC4: Precise segment boundary alignment**
- **Given** Segment boundaries are calculated
- **When** They are applied
- **Then** They align precisely with the AI's recommendations (no drift or offset errors)

**AC5: Timeline structure preservation**
- **Given** Segments are placed on timeline
- **When** I review in Resolve Edit page
- **Then** They appear on the video/dialogue track with proper timecode positions
- **And** Gaps between segments are handled per format rules (cut out or bridged)

## Tasks / Subtasks

- [x] Task 1 (AC: #1, #4) - Implement segment cutting engine
  - [x] Subtask 1.1 - Create `cutter.py` in `src/roughcut/backend/timeline/` with `FootageCutter` class
  - [x] Subtask 1.2 - Implement `cut_segments()` method accepting segment list with start/end timestamps
  - [x] Subtask 1.3 - Implement `place_segments_on_timeline()` using Resolve API to position clips
  - [x] Subtask 1.4 - Handle timecode precision (frame-level accuracy, no drift)
   
- [x] Task 2 (AC: #2) - Implement sequential placement
  - [x] Subtask 2.1 - Place segments sequentially on the timeline (no overlapping)
  - [x] Subtask 2.2 - Add clean cuts between segments (no transition effects by default)
  - [x] Subtask 2.3 - Handle gap management (remove dead space or insert transitions per format)
  - [x] Subtask 2.4 - Maintain source audio sync with video segments

- [x] Task 3 (AC: #3) - Implement progress reporting
  - [x] Subtask 3.1 - Send progress updates: "Cutting segment 1 of 3: 0:15-1:45"
  - [x] Subtask 3.2 - Report total progress: "Placed X of Y segments"
  - [x] Subtask 3.3 - Ensure progress updates never exceed 5 seconds apart (NFR4)

- [x] Task 4 (AC: #5) - Implement Resolve timeline integration
  - [x] Subtask 4.1 - Use existing timeline from Story 6.1 (via `timeline_id`)
  - [x] Subtask 4.2 - Place segments on the video/dialogue track created in 6.1
  - [x] Subtask 4.3 - Ensure source clip is in Media Pool (from Story 6.2 or native Resolve)
  - [x] Subtask 4.4 - Create timeline clips referencing source clip with in/out points

- [x] Task 5 - Create JSON-RPC protocol handlers
  - [x] Subtask 5.1 - Add `cut_footage_to_segments` method handler in `src/roughcut/protocols/handlers/timeline.py`
  - [x] Subtask 5.2 - Accept parameters: `timeline_id`, `source_clip_id`, `segments` list with timestamps
  - [x] Subtask 5.3 - Return result with: `segments_placed`, `total_duration`, `timeline_positions`
  - [x] Subtask 5.4 - Implement error responses with structured error objects per architecture spec

- [x] Task 6 - Implement Lua GUI integration
  - [x] Subtask 6.1 - Add "Cut Footage" step in Lua rough cut workflow (after media import)
  - [x] Subtask 6.2 - Display progress dialog showing "Cutting segment X of Y" updates
  - [x] Subtask 6.3 - Handle completion and display segment summary
  - [x] Subtask 6.4 - Wire "Next" button to proceed to Story 6.4 (Place Music)

- [x] Task 7 - Error handling and recovery
  - [x] Subtask 7.1 - Handle source clip not found in Media Pool
  - [x] Subtask 7.2 - Handle invalid timecode ranges (start >= end, out of bounds)
  - [x] Subtask 7.3 - Handle Resolve timeline track unavailable
  - [x] Subtask 7.4 - Provide actionable error messages per NFR13

### Review Findings (2026-04-04)

**Code review complete.** 0 `decision-needed`, **9** `patch`, 28 `defer`, 8 dismissed as noise.

#### patch (Fixable Issues) - COMPLETED
- [x] [Review][Patch] **Unvalidated integer conversions in timecode parser** [cutter.py:18] — Fixed: Added comprehensive input validation including type checking, regex validation for characters, empty part detection, and explicit int() conversion with proper error messages.
- [x] [Review][Patch] **Negative duration calculation if source_in > source_out** [resolve_api.py:415] — Fixed: Added validation in `create_timeline_clip()` to check `source_out > source_in` and return None with error logging if invalid.
- [x] [Review][Patch] **No FPS validation (ZeroDivisionError at fps=0)** [cutter.py:18,114] — Fixed: Added FPS validation at start of both `timecode_to_frames()` and `frames_to_timecode()` functions to ensure fps is a positive integer.
- [x] [Review][Patch] **Empty segments list not explicitly validated** [timeline.py:407] — Fixed: Added explicit `len(segments) == 0` check with specific error message after type validation.
- [x] [Review][Patch] **Timecode formatting inconsistency** [cutter.py:133] — Fixed: Hours now zero-padded in `include_frames=True` branch: `f"{hours:02d}:{minutes:02d}:..."` for consistency.
- [x] [Review][Patch] **Missing input type validation** [cutter.py:184] — Fixed: Added segment type validation to ensure each segment is a dictionary before accessing keys.
- [x] [Review][Patch] **Frame value type validation** [cutter.py:262] — Fixed: Added explicit type checking for `start_frames` and `end_frames` to ensure they are integers.
- [x] [Review][Patch] **Segment index uniqueness not validated** [cutter.py:184] — Fixed: Added `seen_indexes` set to track and detect duplicate segment_index values.
- [x] [Review][Patch] **Missing guards for timecode format edge cases** [cutter.py:18] — Fixed: Added validation for time ranges (seconds < 60, minutes < 60, frames < fps) and character validation.

#### defer (Pre-existing/Minor)
- [x] [Review][Defer] **Overflow checks for frame calculations** — deferred, extremely unlikely in video editing context (would require >500 hour videos)
- [x] [Review][Defer] **Fractional seconds in timecode** — deferred, not in spec, use H:MM:SS:FF format instead
- [x] [Review][Defer] **Unicode timecode handling** — deferred, rare in practice, regex handles most cases
- [x] [Review][Defer] **Extra key detection in segments** — deferred, defensive, non-critical
- [x] [Review][Defer] **Multiple edge case variations** — deferred, covered by existing validation

## Technical Context

### Architecture Compliance

**Layer Separation (CRITICAL - MUST FOLLOW):**
- **Lua Layer (`lua/ui/`):** GUI only - display progress, show segment summary, handle workflow navigation
- **Python Layer (`src/roughcut/backend/timeline/`):** All segment cutting business logic
- **Communication:** JSON-RPC protocol over stdin/stdout ONLY - never direct imports between layers

**Key Files to Create/Modify:**
- `src/roughcut/backend/timeline/cutter.py` - FootageCutter class (NEW)
- `src/roughcut/backend/timeline/resolve_api.py` - Add `create_timeline_clip()` method (MODIFY - exists from 6.1)
- `src/roughcut/protocols/handlers/timeline.py` - Add `cut_footage_to_segments` handler (MODIFY - exists from 6.1)
- `lua/ui/rough_cut_review_window.lua` - Add cutting progress UI (MODIFY - exists from 6.2)

### Technical Requirements

**From PRD (Functional Requirements):**
- FR29: System can cut video footage according to AI-recommended transcript segments
- FR27: Foundation from Story 6.1 (timeline structure with video/dialogue track)
- FR28: Foundation from Story 6.2 (source clip in Media Pool)

**From PRD (Non-Functional Requirements - MUST FOLLOW):**
- NFR4: System shall display progress indicators for operations exceeding 5 seconds
- NFR5: Lua GUI shall remain responsive during Python backend processing operations
- NFR9: System shall create timelines non-destructively (cutting references source, doesn't modify it)
- NFR10: System shall validate all file paths and timecodes before operations
- NFR11: System shall gracefully handle Resolve API unavailability with clear error messages
- NFR13: All user-facing errors shall include actionable recovery guidance
- NFR14: GUI shall follow Resolve UI conventions for consistency with host application

**API Integration Requirements:**
- Must use Resolve's Lua API for timeline clip operations (AddClip, SetIn/Out points)
- Must reference source clips already in Media Pool (from 6.2 or native Resolve)
- Must handle timecode calculations in frames for precision
- Must support segment gaps (jump cuts) where transcript was removed

### Naming Conventions (STRICT - FOLLOW EXACTLY)

**Python Layer:**
- Functions/variables: `snake_case` - e.g., `cut_segments()`, `segment_start`
- Classes: `PascalCase` - e.g., `FootageCutter`, `SegmentPlacement`
- Constants: `SCREAMING_SNAKE_CASE` - e.g., `MAX_SEGMENTS`, `TIMECODE_FPS`

**Lua Layer:**
- Functions/variables: `camelCase` - e.g., `cutSegments()`, `segmentStart`
- GUI components: `PascalCase` - e.g., `CutProgressDialog`, `SegmentSummary`

**JSON Protocol:**
- Field names: `snake_case` - e.g., `"segment_start"`, `"timeline_position"`

### JSON-RPC Communication Protocol (MUST IMPLEMENT CORRECTLY)

**Request format (Lua → Python):**
```json
{
  "method": "cut_footage_to_segments",
  "params": {
    "timeline_id": "timeline_12345",
    "source_clip_id": "media_pool_ref_001",
    "segments": [
      {
        "segment_index": 1,
        "start_time": "0:15:00",
        "end_time": "1:45:00",
        "start_frames": 900,
        "end_frames": 6300,
        "dialogue_preview": "The key insight is..."
      },
      {
        "segment_index": 2,
        "start_time": "2:30:00",
        "end_time": "4:15:00",
        "start_frames": 9000,
        "end_frames": 15300,
        "dialogue_preview": "Moving forward..."
      },
      {
        "segment_index": 3,
        "start_time": "10:30:00",
        "end_time": "12:00:00",
        "start_frames": 37800,
        "end_frames": 43200,
        "dialogue_preview": "In conclusion..."
      }
    ]
  },
  "id": "req_cut_001"
}
```

**Response format (Python → Lua):**
```json
{
  "result": {
    "segments_placed": 3,
    "total_duration_frames": 42300,
    "total_duration_timecode": "0:04:42:00",
    "timeline_positions": [
      {
        "segment_index": 1,
        "timeline_start_frame": 0,
        "timeline_end_frame": 5400,
        "source_in_frame": 900,
        "source_out_frame": 6300
      },
      {
        "segment_index": 2,
        "timeline_start_frame": 5400,
        "timeline_end_frame": 11700,
        "source_in_frame": 9000,
        "source_out_frame": 15300
      },
      {
        "segment_index": 3,
        "timeline_start_frame": 11700,
        "timeline_end_frame": 17100,
        "source_in_frame": 37800,
        "source_out_frame": 43200
      }
    ]
  },
  "error": null,
  "id": "req_cut_001"
}
```

**Error format:**
```json
{
  "result": null,
  "error": {
    "code": "SOURCE_CLIP_NOT_FOUND",
    "category": "resolve_api",
    "message": "Source clip not found in Media Pool",
    "recoverable": true,
    "suggestion": "Ensure source media was imported successfully in previous step"
  },
  "id": "req_cut_001"
}
```

**Progress format:**
```json
{
  "type": "progress",
  "operation": "cut_footage",
  "current": 1,
  "total": 3,
  "message": "Cutting segment 1 of 3: 0:15-1:45"
}
```

### Segment Data Structure

**Input Segment Format (from AI rough cut):**
```python
segment = {
    "segment_index": int,        # 1-based segment number
    "start_time": str,           # Timecode string "H:MM:SS:FF" or "M:SS"
    "end_time": str,             # Timecode string
    "start_frames": int,         # Absolute frame count from source start
    "end_frames": int,           # Absolute frame count
    "dialogue_preview": str,     # First 50 chars of dialogue (for UI display)
    "ai_reasoning": str            # Optional: why this segment was selected
}
```

**Output Timeline Clip Format:**
```python
timeline_clip = {
    "segment_index": int,
    "timeline_track": int,       # Track number (1 = video/dialogue)
    "timeline_start_frame": int, # Position on timeline (sequential)
    "timeline_end_frame": int,   # End position on timeline
    "source_in_frame": int,      # In point on source clip
    "source_out_frame": int,     # Out point on source clip
    "clip_id": str               # Resolve's clip reference
}
```

## Dev Notes

### Critical Implementation Notes

**1. Timecode Precision (CRITICAL - NO DRIFT ALLOWED):**
- All calculations MUST be in frames for precision
- Convert timecode strings to frames immediately on input
- Use project FPS settings from Resolve (default 24, 25, 30, 60)
- Frame-level accuracy required - no floating point drift
- Example: 1:45:00 at 30fps = (1*60 + 45)*30 = 3150 frames exactly

**2. Non-Destructive Guarantee (NFR9) - CRITICAL:**
- NEVER modify the source clip in Media Pool
- ALWAYS create timeline clips that REFERENCE source with in/out points
- Timeline clips are lightweight references, not copies
- Source remains untouched, only timeline view changes

**3. Sequential Placement Pattern:**
```python
# Recommended approach from Story 6.1 learnings:
def place_segments_sequentially(segments, start_track=1):
    current_timeline_position = 0
    placements = []
    
    for segment in segments:
        segment_duration = segment['end_frames'] - segment['start_frames']
        
        placement = {
            'timeline_start_frame': current_timeline_position,
            'timeline_end_frame': current_timeline_position + segment_duration,
            'source_in_frame': segment['start_frames'],
            'source_out_frame': segment['end_frames']
        }
        placements.append(placement)
        
        # Move to end of this segment for next placement
        current_timeline_position += segment_duration
    
    return placements
```

**4. Resolve API Clip Creation Pattern:**
```python
# From Story 6.1 resolve_api.py patterns:
def create_timeline_clip(self, timeline, source_clip, track_index, 
                         timeline_position, source_in, source_out):
    """
    Create a timeline clip referencing source with specified in/out points.
    
    Args:
        timeline: Resolve timeline object
        source_clip: Media Pool clip reference
        track_index: Target track number (1 for video)
        timeline_position: Frame position on timeline
        source_in: In point frame on source
        source_out: Out point frame on source
    """
    # Implementation uses Resolve's AddClip or similar API
    # Must set both timeline position and source in/out
```

**5. Gap Management:**
- Segments with gaps between them result in jump cuts (intentional)
- Gaps are REMOVED from timeline (not left as empty space)
- This creates the condensed rough cut from long source
- Example: 38-min source with 3 segments → ~4-min timeline

**6. Progress Reporting Requirements:**
- Send progress for EACH segment being cut
- Format: "Cutting segment X of Y: start-end"
- Never go >5 seconds without progress update (NFR4)
- Include segment index in message for clarity

### Dependencies on Previous Stories

**Direct Dependencies:**
- **Story 6.1 (Create New Timeline)** - MUST be completed first
  - Timeline must exist with video/dialogue track
  - Returns `timeline_id` needed for this story
  - Track structure established (Track 1 = video/dialogue)
  
- **Story 6.2 (Import Suggested Media)** - SHOULD be completed first
  - Source clip must be in Media Pool
  - Returns `media_pool_refs` containing `source_clip_id`
  - Provides validated file paths for source media

**Code Dependencies from Previous Stories:**
- `src/roughcut/backend/timeline/builder.py` - Timeline structure from 6.1
- `src/roughcut/backend/timeline/resolve_api.py` - ResolveApi wrapper (add `create_timeline_clip`)
- `src/roughcut/backend/timeline/track_manager.py` - Track structure from 6.1
- `src/roughcut/protocols/handlers/timeline.py` - Existing handler structure (add new method)
- `src/roughcut/backend/timeline/importer.py` - MediaPoolReference pattern from 6.2

**Foundation for Next Stories:**
- Story 6.4: Place Music on Timeline - needs timeline with video segments already placed
- Story 6.5: Layer SFX on Timeline - needs video segments to time SFX against
- Story 6.6: Position VFX Templates - needs video segments to position VFX at
- Story 6.7: Rough Cut Output - needs complete timeline with all segments

### Data Source for Segments

**AI Rough Cut Generation (Story 5.x series):**
- Segments come from AI transcript cutting (Story 5.3)
- AI analyzes transcript and format template
- Returns optimal cut points preserving narrative beats
- Passed to this story as `segments` list with timestamps

**Expected Data Flow:**
```
Story 5.3 (AI Cutting) 
  ↓
Rough Cut Document (segments with timestamps)
  ↓
Story 6.3 (this story) - receives segments via JSON-RPC
  ↓
Timeline with cut segments placed sequentially
```

### Project Structure Notes

**Directory Structure:**
```
src/roughcut/backend/timeline/
├── __init__.py
├── builder.py          # EXISTS from Story 6.1
├── track_manager.py    # EXISTS from Story 6.1
├── resolve_api.py      # MODIFY - add create_timeline_clip method
├── importer.py         # EXISTS from Story 6.2
└── cutter.py           # NEW - FootageCutter class

src/roughcut/protocols/handlers/
├── __init__.py
├── media.py            # EXISTS
├── ai.py               # EXISTS
└── timeline.py         # MODIFY - add cut_footage_to_segments handler

lua/ui/
└── rough_cut_review_window.lua  # MODIFY - add cutting progress UI
```

### Testing Notes

**Manual Testing Scenarios:**
1. Cut single segment - verify appears on timeline at position 0
2. Cut multiple segments - verify sequential placement (no gaps)
3. Test timecode precision - verify frame-level accuracy
4. Test source clip not found - verify actionable error
5. Test invalid timecodes - verify validation catches errors
6. Test progress reporting - verify "Cutting segment X of Y" messages
7. Test 38-min → 4-min reduction - verify correct segment selection
8. Test Resolve API unavailable - verify graceful error

**Integration Test Points:**
- Lua → Python protocol communication for cutting method
- Timecode conversion accuracy (frames ↔ timecode)
- Resolve timeline clip creation with in/out points
- Sequential placement calculation
- Error handling and message propagation
- Progress reporting accuracy

**Unit Test Requirements:**
- Test FootageCutter class methods
- Test timecode/frame conversion functions
- Test sequential placement calculation
- Test segment validation (start < end, within bounds)
- Test error response generation
- Mock Resolve API for testing

**Code Review Learnings from 6.1/6.2 to Apply:**
1. **Stable ID Generation** - Use hashlib.md5, not Python hash(), for deterministic IDs
2. **Streaming Progress** - Wire up progress callback to emit JSON-RPC progress messages
3. **TOCTOU Protection** - Validate conditions right before use with try/except
4. **Error Response Structure** - Always include code, category, message, recoverable, suggestion
5. **Input Validation** - Validate segment count, timecode formats, frame ranges
6. **Chunked Processing** - For many segments, process in chunks with progress updates

## Dev Agent Record

### Agent Model Used

OpenCode Agent (accounts/fireworks/routers/kimi-k2p5-turbo)

### Debug Log References

No critical issues encountered during implementation.

### Completion Notes List

**Implementation Summary (2026-04-04):**
- Created comprehensive `FootageCutter` class in `src/roughcut/backend/timeline/cutter.py` (418 lines)
- All 5 acceptance criteria satisfied (AC1-AC5)
- Frame-level timecode precision with `timecode_to_frames()` and `frames_to_timecode()` functions
- Non-destructive cutting - references source clips with in/out points, never modifies source
- Sequential segment placement removes gaps (38-min source → ~4-min timeline)
- Progress reporting with "Cutting segment X of Y: start-end" format per NFR4
- Comprehensive error handling with actionable guidance per NFR13

**Technical Decisions:**
1. **FootageCutter** - Central class handling all segment cutting logic with protocol-based Resolve API
2. **SegmentPlacement** - Dataclass tracking timeline position, source in/out, and clip references
3. **CutResult** - Dataclass with segments_placed, total_duration, and timeline_positions
4. **Timecode precision** - All calculations in frames using 30fps default, with format detection
5. **Stable ID generation** - MD5-based clip IDs for deterministic identification
6. **Gap removal** - Sequential placement removes source gaps, creating condensed rough cut
7. **Error resilience** - Individual segment failures don't fail entire operation

**Architecture Compliance:**
- Python layer: All business logic in `cutter.py` and `resolve_api.py`
- JSON-RPC protocol: Structured error responses per architecture spec in `timeline.py` handler
- Lua layer: GUI integration in `rough_cut_review_window.lua` with cutting progress step
- Naming conventions: snake_case for Python, camelCase for Lua
- Layer separation: No direct Python/Lua imports, only protocol communication

**Testing:**
- Comprehensive unit tests created in `tests/unit/backend/timeline/test_cutter.py` (372 lines)
- Tests cover: timecode conversion, segment validation, sequential placement, cutting logic
- Mock-based testing for Resolve API interactions without requiring actual Resolve

**Code Review Fixes Applied (2026-04-04):**
- **HIGH**: Comprehensive timecode validation with regex, range checks, and type safety
- **HIGH**: Source clip in/out point validation in create_timeline_clip()
- **MEDIUM**: FPS parameter validation (positive integer required)
- **MEDIUM**: Explicit empty segments list validation
- **MEDIUM**: Segment type validation (must be dict) and uniqueness checks
- **LOW**: Timecode formatting consistency (hours zero-padded)
- **LOW**: Frame value type validation (must be integers)

### File List

**New Files Created:**
1. `src/roughcut/backend/timeline/cutter.py` - FootageCutter class with segment cutting logic (418 lines)
2. `tests/unit/backend/timeline/test_cutter.py` - Comprehensive unit tests (372 lines)

**Modified Files:**
1. `src/roughcut/backend/timeline/__init__.py` - Export FootageCutter, CutResult, SegmentPlacement
2. `src/roughcut/backend/timeline/resolve_api.py` - Add `create_timeline_clip()` method
3. `src/roughcut/protocols/handlers/timeline.py` - Add `cut_footage_to_segments` handler
4. `lua/ui/rough_cut_review_window.lua` - Add cutting workflow step between import and success

## Change Log

| Date | Change | Description |
|------|--------|-------------|
| 2026-04-04 | Story Creation | Initial comprehensive story file created with all technical context from epics, architecture, and previous stories |
| 2026-04-04 | Implementation | Story 6.3 fully implemented. Created FootageCutter class (418 lines), ResolveApi additions, protocol handlers, Lua GUI integration, and comprehensive unit tests. All 5 acceptance criteria satisfied. |
| 2026-04-04 | Code Review Fixes | All 9 patch items fixed. Key fixes: comprehensive timecode validation with regex and range checks, FPS parameter validation, segment type and uniqueness validation, source_in/source_out validation in create_timeline_clip(), explicit empty segments check. 28 items deferred as pre-existing/minor. |

## References

**Epic Context:**
- Epic 6: Timeline Creation & Media Placement [Source: _bmad-output/planning-artifacts/epics.md#Epic 6]
- Story 6.3 detailed requirements [Source: _bmad-output/planning-artifacts/epics.md#Story 6.3]

**PRD Requirements:**
- FR29: Cut video footage to AI-recommended segments [Source: _bmad-output/planning-artifacts/prd.md#Timeline Creation & Media Placement]
- NFR4: Progress indicators [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements]
- NFR5: Responsive GUI [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements]
- NFR9: Non-destructive operations [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements]
- NFR10: Path/timecode validation [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements]
- NFR11: Graceful API unavailability handling [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements]
- NFR13: Actionable error messages [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements]

**Architecture Decisions:**
- Timeline cutter pattern [Source: _bmad-output/planning-artifacts/architecture.md#Timeline Creation]
- Track management structure [Source: _bmad-output/planning-artifacts/architecture.md#Requirements to Structure Mapping]
- Lua/Python layer separation [Source: _bmad-output/planning-artifacts/architecture.md#Lua ↔ Python Communication Protocol]
- Naming conventions [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns]
- JSON-RPC protocol format [Source: _bmad-output/planning-artifacts/architecture.md#Format Patterns]

**Previous Story Intelligence:**
- Story 6.1: Create New Timeline - prerequisite, provides timeline_id and track structure [Source: _bmad-output/implementation-artifacts/6-1-create-new-timeline.md]
  - Timeline naming: "RoughCut_[source]_[format]_[timestamp]"
  - Track structure: 1 video, 1 music, 2 SFX, 1 VFX
  - Code review fixes: stable ID generation, progress streaming, TOCTOU protection
  - Non-destructive creation with name collision handling
  
- Story 6.2: Import Suggested Media - prerequisite, provides source_clip_id [Source: _bmad-output/implementation-artifacts/6-2-import-suggested-media.md]
  - MediaImporter pattern with batch validation
  - ResolveApi wrapper for Media Pool operations
  - Progress callback pattern for streaming updates
  - Error resilience: individual file failures don't fail entire operation
  - Code review fixes: chunked processing, stable IDs, format validation

**Related Stories:**
- Story 5.3: AI Transcript Cutting - provides segment data [Source: _bmad-output/planning-artifacts/epics.md#Story 5.3]
- Story 6.1: Create New Timeline - prerequisite, provides timeline_id [Source: _bmad-output/implementation-artifacts/6-1-create-new-timeline.md]
- Story 6.2: Import Suggested Media - prerequisite, provides source_clip_id [Source: _bmad-output/implementation-artifacts/6-2-import-suggested-media.md]
- Story 6.4: Place Music on Timeline - next story, uses timeline with cut segments [Source: _bmad-output/planning-artifacts/epics.md#Story 6.4]

---

**Story Key:** 6-3-cut-footage-to-segments  
**Epic:** 6 - Timeline Creation & Media Placement  
**Created:** 2026-04-04  
**Status:** done  
**Notes:** Third story in Epic 6 - COMPLETED. Code review passed with 9 patches fixed. All acceptance criteria satisfied. Frame-level timecode precision, non-destructive cutting, sequential segment placement all verified. Ready for integration with Story 6.4 (Place Music on Timeline).
