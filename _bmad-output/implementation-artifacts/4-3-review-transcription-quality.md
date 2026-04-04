# Story 4.3: Review Transcription Quality

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a video editor,
I want to review transcription quality before proceeding,
So that I don't waste AI processing on poor-quality audio.

## Context

This story is part of **Epic 4: Media Selection & Transcription**. The previous story (4.2 - Retrieve Transcription) enabled RoughCut to retrieve and display Resolve's native transcription for selected clips. This story adds quality analysis and visual indicators so editors can make informed decisions about whether to proceed with AI processing or clean up the audio first.

**Key Points:**
- Transcription quality directly impacts AI rough cut accuracy (garbage in, garbage out)
- Resolve provides confidence scores when available - we should surface these
- Poor audio quality (HVAC noise, echo, distant mics) produces unusable transcripts
- User needs clear visual cues to identify problem areas without reading entire transcript
- This is a gatekeeping step before Story 4.4 (Error Recovery Workflow) and 4.5 (Validate Transcribable Media)
- Per PRD Journey 2: Editor should see clear warning for "Um, so, like... [inaudible]..." type transcripts

## Acceptance Criteria

### AC1: Display Quality Indicators

**Given** Transcription has been retrieved (Story 4.2 completed)
**When** It displays in RoughCut
**Then** Quality indicators are visible (confidence scores, completeness metrics)
**And** Overall quality is rated as: Good / Fair / Poor

### AC2: Highlight Problem Areas

**Given** The transcript has obvious quality issues
**When** I view it
**Then** The UI clearly marks problem areas: "[inaudible]", "[garbled]", low-confidence sections
**And** Problem areas are visually distinct (red highlighting, warning icons)

### AC3: Quality Assessment Summary

**Given** The transcript is high quality (>90% confidence, no problem markers)
**When** Review completes
**Then** I see a "Quality: Good ✓" indicator
**And** I can proceed confidently to format selection

**Given** The transcript is poor quality (<50% confidence or many problem markers)
**When** Review completes
**Then** I see a "Quality: Poor ⚠" warning
**And** Guidance appears: "Audio cleanup recommended before AI processing"

### AC4: User Decision Point

**Given** I am reviewing transcription
**When** I see quality warnings
**Then** I understand whether to proceed or fix audio issues first
**And** I have clear actions: [Proceed Anyway] [Go Back] [Learn About Audio Cleanup]

## Tasks / Subtasks

- [x] **Task 1**: Add quality analysis to Transcript model (AC: #1, #2)
  - [x] Subtask 1.1: Add quality metrics to Transcript dataclass (confidence_score, completeness_pct, problem_count)
  - [x] Subtask 1.2: Implement quality classification method (calculate_quality_rating())
  - [x] Subtask 1.3: Add problem area detection (find_inaudible_markers(), find_low_confidence_sections())
  
- [x] **Task 2**: Create quality analysis handler (AC: #1, #3)
  - [x] Subtask 2.1: Add `analyze_transcription_quality` handler to media.py
  - [x] Subtask 2.2: Implement quality analysis logic (parse confidence, count problem markers)
  - [x] Subtask 2.3: Generate quality report with recommendations
  
- [x] **Task 3**: Enhance Lua transcript viewer with quality UI (AC: #2, #3, #4)
  - [x] Subtask 3.1: Add quality indicator banner (Good/Fair/Poor with color coding)
  - [x] Subtask 3.2: Implement problem area highlighting in text widget
  - [x] Subtask 3.3: Add decision buttons: Proceed, Go Back, Audio Cleanup Guide
  - [x] Subtask 3.4: Add "Learn More" tooltip/link for audio cleanup workflow
  
- [x] **Task 4**: Create audio cleanup guidance documentation (AC: #4)
  - [x] Subtask 4.1: Write audio cleanup guide (noise reduction in Resolve, render clean version)
  - [x] Subtask 4.2: Link guide from UI "Learn About Audio Cleanup" button
  
- [x] **Task 5**: Write tests (AC: All)
  - [x] Subtask 5.1: Unit tests for quality classification logic
  - [x] Subtask 5.2: Unit tests for problem marker detection
  - [x] Subtask 5.3: Integration test for quality analysis workflow
  
- [x] **Task 6**: Update story status and documentation
  - [x] Subtask 6.1: Mark all tasks complete
  - [x] Subtask 6.2: Update Dev Agent Record
- [x] Subtask 6.3: Update File List

### Review Findings

**Code review complete.** 0 `decision-needed`, 8 `patch`, 0 `defer`, 2 dismissed as noise.

#### 🔴 Patch Required (Fixable Without Input)

- [x] [Review][Patch] `TranscriptQuality.from_dict()` missing return statement [models.py:107] — The classmethod parses data but never returns an instance. Missing `return cls(...)` statement. **FIXED**: Return statement exists at lines 105-112, was false positive.

- [x] [Review][Patch] None/NaN text causes AttributeError in regex [models.py:_find_problem_markers()] — `re.finditer()` called on `self.text` without checking for None. Add guard: `if not self.text: return []` **FIXED**: Added None guard at beginning of method.

- [x] [Review][Patch] NaN confidence score not handled in quality rating [models.py:_determine_quality_rating()] — NaN comparisons return False, may misclassify as GOOD. Add `math.isnan()` check. **FIXED**: Added NaN check at beginning of method.

- [x] [Review][Patch] Missing "Go Back" button in quality dialog [transcript_viewer.lua:677-727] — AC4 requires [Proceed Anyway] [Go Back] [Learn About Audio Cleanup]. Currently missing the Go Back button for the quality review step. **FIXED**: Updated button visibility logic to show all 3 buttons for non-good quality per AC4.

- [x] [Review][Patch] Empty/nil transcript data not validated in Lua [transcript_viewer.lua:showQualityReview()] — No validation that transcriptData is non-nil/non-empty before processing. Add nil/empty check at entry. **FIXED**: Added nil and type validation at function entry.

- [x] [Review][Patch] Nil safety violations in Lua math operations [transcript_viewer.lua:updateQualityBanner()] — `math.floor(confidence * 100)` can error if confidence is nil. Use `(confidence or 0)` pattern. **FIXED**: Already correct - uses `or 0` pattern for all values.

- [x] [Review][Patch] Problem areas not visually highlighted [transcript_viewer.lua:displayTranscriptWithProblems()] — AC2 requires visual highlighting. Currently shows plain text with TODO comment. Implement bracket coloring or rich text if supported. **FIXED**: Added visual indicators (► ◄) around problem markers for visibility until rich text is available.

- [x] [Review][Patch] Negative completeness percentage not guarded [models.py:_determine_quality_rating()] — Negative values don't trigger POOR rating properly. Add explicit check for `<= 0`. **FIXED**: Added `or <= 0` check to completeness validation.

## Change Log

| Date | Change | Notes |
|------|--------|-------|
| 2026-04-04 | Story created | Comprehensive context from epics, architecture, and previous story analysis |
| 2026-04-04 | Task 1 complete | Added QualityRating enum, TranscriptQuality dataclass, and analysis methods to models.py |
| 2026-04-04 | Task 2 complete | Created analyze_transcription_quality handler in media.py with full error handling |
| 2026-04-04 | Task 3 complete | Enhanced Lua transcript viewer with quality banner, problem highlighting, decision buttons |
| 2026-04-04 | Task 4 complete | Created comprehensive audio cleanup guide in docs/audio_cleanup_guide.md |
| 2026-04-04 | Task 5 complete | Wrote unit tests for quality models and handler functionality |
| 2026-04-04 | Task 6 complete | Updated all documentation, marked story complete for review |
| 2026-04-04 | Code review complete | 8 patch findings identified and fixed automatically |

---

## Previous Story Intelligence

### From Story 4.2 (Retrieve Transcription) - Learnings for This Story

**What Worked Well:**
1. The JSON-RPC protocol over stdin/stdout proved reliable for Lua ↔ Python communication
2. Dataclass-based models with `to_dict()`/`from_dict()` serialization worked well
3. Error handling with structured error objects provided actionable guidance to users

**Patterns to Follow:**
1. Use `@dataclass` with type hints for all data models
2. Include `__post_init__` validation for data integrity
3. Return standard JSON-RPC format with `result` wrapper
4. Use absolute paths in all cross-layer communication
5. Handle NaN values explicitly (e.g., `math.isnan()` checks)

**Issues Encountered (Now Fixed):**
1. Missing timeout mechanism - Fixed with 5-second timeout tracking
2. Race condition on global state - Fixed with threading locks
3. Type conversion validation - Fixed with try/except in `from_dict()`

**Code Patterns Established:**
```python
# Data model pattern
def from_dict(cls, data: dict) -> "Transcript":
    try:
        return cls(
            text=str(data.get("text", "")),
            word_count=int(data.get("word_count", 0)),
            # ...
        )
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid transcript data: {e}")

# Handler pattern
class MediaHandlers:
    def handle_retrieve_transcription(self, params: dict) -> dict:
        try:
            # Implementation
            return {"result": result_data, "error": None}
        except SomeException as e:
            return {
                "result": None,
                "error": {
                    "code": "ERROR_CODE",
                    "category": "category",
                    "message": str(e),
                    "recoverable": True,
                    "suggestion": "Actionable guidance"
                }
            }
```

**UI Patterns Established (Lua):**
```lua
-- UI component pattern with error handling
function showTranscript(text)
    local status, err = pcall(function()
        -- UI code
    end)
    if not status then
        showError("Failed to display transcript: " .. tostring(err))
    end
end
```

**Testing Approach That Worked:**
- Unit tests for model serialization/deserialization
- Unit tests for handler logic with mocked dependencies
- Integration tests for full Lua ↔ Python ↔ Resolve workflow

**Files Created in Story 4.2 (Reference for Structure):**
- `src/roughcut/backend/database/models.py` - Transcript dataclass
- `src/roughcut/protocols/handlers/media.py` - Transcription retrieval handler
- `lua/roughcut/transcript_viewer.lua` - Transcript display UI
- `lua/roughcut/resolve_api.lua` - Resolve API wrapper
- `tests/unit/backend/database/test_models.py` - Model tests
- `tests/unit/protocols/handlers/test_media.py` - Handler tests

### Git Intelligence (Recent Commits Pattern)

Based on the completed Story 4.2, the implementation approach should:
1. Start with Python data models and handlers
2. Then implement Lua UI components
3. Add tests for both layers
4. Verify integration end-to-end

### Critical Implementation Notes

1. **Quality Thresholds**: Per PRD MVP requirements, 50-60% AI suggestion usability is acceptable. However, transcription quality should be higher threshold since it's the foundation for AI processing. Aim for clear Poor/Good distinction rather than nuanced grading.

2. **UI Responsiveness**: Per NFR5, Lua GUI must remain responsive. Quality analysis happens in Python backend, but UI updates should not block. Use the established pattern of progress callbacks.

3. **Error Recovery Path**: This story sets up Story 4.4 (Error Recovery Workflow). The "Learn About Audio Cleanup" button should link to documentation that will be implemented in 4.4.

4. **Visual Design**: Follow Resolve UI conventions (per NFR14). Use Resolve's standard warning colors and icons. The quality banner should be prominent but not intrusive.

5. **Non-Destructive**: Per NFR9, this is a review step only - no timelines created, no media imported, no changes to Resolve project.
