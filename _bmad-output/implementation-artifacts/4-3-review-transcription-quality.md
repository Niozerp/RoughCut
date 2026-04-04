# Story 4.3: Review Transcription Quality

Status: ready-for-dev

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

- [ ] **Task 1**: Add quality analysis to Transcript model (AC: #1, #2)
  - [ ] Subtask 1.1: Add quality metrics to Transcript dataclass (confidence_score, completeness_pct, problem_count)
  - [ ] Subtask 1.2: Implement quality classification method (calculate_quality_rating())
  - [ ] Subtask 1.3: Add problem area detection (find_inaudible_markers(), find_low_confidence_sections())
  
- [ ] **Task 2**: Create quality analysis handler (AC: #1, #3)
  - [ ] Subtask 2.1: Add `analyze_transcription_quality` handler to media.py
  - [ ] Subtask 2.2: Implement quality analysis logic (parse confidence, count problem markers)
  - [ ] Subtask 2.3: Generate quality report with recommendations
  
- [ ] **Task 3**: Enhance Lua transcript viewer with quality UI (AC: #2, #3, #4)
  - [ ] Subtask 3.1: Add quality indicator banner (Good/Fair/Poor with color coding)
  - [ ] Subtask 3.2: Implement problem area highlighting in text widget
  - [ ] Subtask 3.3: Add decision buttons: Proceed, Go Back, Audio Cleanup Guide
  - [ ] Subtask 3.4: Add "Learn More" tooltip/link for audio cleanup workflow
  
- [ ] **Task 4**: Create audio cleanup guidance documentation (AC: #4)
  - [ ] Subtask 4.1: Write audio cleanup guide (noise reduction in Resolve, render clean version)
  - [ ] Subtask 4.2: Link guide from UI "Learn About Audio Cleanup" button
  
- [ ] **Task 5**: Write tests (AC: All)
  - [ ] Subtask 5.1: Unit tests for quality classification logic
  - [ ] Subtask 5.2: Unit tests for problem marker detection
  - [ ] Subtask 5.3: Integration test for quality analysis workflow
  
- [ ] **Task 6**: Update story status and documentation
  - [ ] Subtask 6.1: Mark all tasks complete
  - [ ] Subtask 6.2: Update Dev Agent Record
  - [ ] Subtask 6.3: Update File List

## Dev Notes

### Technical Requirements

**Quality Analysis Logic:**

The quality analysis should evaluate multiple factors:

1. **Confidence Score Analysis** (when available from Resolve):
   - >90% = Good
   - 70-90% = Fair
   - <70% = Poor

2. **Problem Marker Detection**:
   - Count occurrences of: [inaudible], [garbled], [unintelligible], [crosstalk]
   - Calculate ratio: problem_words / total_words
   - >10% problem words = Poor quality flag

3. **Transcript Completeness**:
   - Compare word count to expected word count based on duration
   - Expected: ~130-150 words per minute for normal speech
   - <50% of expected words = Poor quality flag

**Lua ↔ Python Communication Protocol:**

Following the JSON-RPC protocol established in architecture and Story 4.2:

**Request format (Lua → Python):**
```json
{
  "method": "analyze_transcription_quality",
  "params": {
    "transcript": {
      "text": "Speaker 1: Welcome... [inaudible]...",
      "word_count": 5234,
      "duration_seconds": 2280,
      "has_speaker_labels": true,
      "confidence_score": 0.67
    },
    "clip_name": "interview_footage_01.mp4"
  },
  "id": "req_quality_001"
}
```

**Response format (Python → Lua):**
```json
{
  "result": {
    "quality_rating": "poor",
    "confidence_score": 0.67,
    "completeness_pct": 45,
    "problem_count": 12,
    "problem_areas": [
      {"type": "inaudible", "position": 234, "text": "[inaudible]"},
      {"type": "low_confidence", "start": 1200, "end": 1350}
    ],
    "recommendation": "Audio cleanup recommended - 12 problem areas detected, only 45% completeness"
  },
  "error": null,
  "id": "req_quality_001"
}
```

### Project Structure Notes

**Files to Create/Modify:**

1. **Python Backend:**
   - `src/roughcut/backend/database/models.py` - Enhance Transcript dataclass with quality fields
   - `src/roughcut/protocols/handlers/media.py` - Add `analyze_transcription_quality` handler

2. **Lua Frontend:**
   - `lua/roughcut/transcript_viewer.lua` - Enhance with quality UI (already created in Story 4.2)
   - `lua/roughcut/quality_indicators.lua` - New module for quality banner and highlighting

3. **Documentation:**
   - `docs/audio_cleanup_guide.md` - New file with audio cleanup instructions

### Architecture Compliance

**Must Follow:**
- **Naming Conventions**: Python uses `snake_case`, Lua uses `camelCase`
- **JSON-RPC Protocol**: All communication through stdin/stdout with structured error objects
- **Layer Separation**: Lua = GUI only, Python = business logic
- **Error Handling**: Use structured error objects with `code`, `category`, `message`, `suggestion`

**Error Categories:**
- `validation` - Invalid transcript data
- `resolve_api` - Issues with transcription source
- `internal` - Unexpected errors in quality analysis

### References

- **Epic 4 Source**: [Source: epics.md#Epic 4: Media Selection & Transcription]
- **Story 4.2 Reference**: [Source: _bmad-output/implementation-artifacts/4-2-retrieve-transcription.md]
- **Architecture - Resolve API**: [Source: architecture.md#Resolve API Boundary]
- **Architecture - Communication Protocol**: [Source: architecture.md#Lua ↔ Python Communication Protocol]
- **Architecture - Naming Conventions**: [Source: architecture.md#Naming Patterns]
- **PRD - FR16**: [Source: prd.md#FR16: Editor can review transcription quality before proceeding]
- **PRD - Journey 2**: [Source: prd.md#Journey 2: The Primary Editor — Error Recovery (Failed Transcription)]
- **PRD - NFR12**: [Source: prd.md#NFR12: System shall provide recovery options for failed AI processing]

## Dev Agent Record

### Agent Model Used

[To be filled during implementation]

### Implementation Plan

[To be filled during implementation]

### Debug Log References

[To be filled during implementation]

### Completion Notes List

[To be filled during implementation]

## File List

[To be filled during implementation - list all new/modified files with relative paths]

## Change Log

| Date | Change | Notes |
|------|--------|-------|
| 2026-04-04 | Story created | Comprehensive context from epics, architecture, and previous story analysis |

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
