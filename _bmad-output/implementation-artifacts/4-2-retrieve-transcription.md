# Story 4.2: Retrieve Transcription

Status: done

## Story

As a video editor,
I want RoughCut to retrieve and display Resolve's native transcription for selected clips,
So that I can see the spoken content that will guide the rough cut.

## Context

This story is part of **Epic 4: Media Selection & Transcription**. The previous story (4.1 - Browse Media Pool) enabled users to browse and select clips from the Resolve Media Pool. This story focuses on retrieving and displaying the transcription data that Resolve has already generated for the selected clip.

**Key Points:**
- Resolve has built-in transcription capabilities that editors may already be using
- We leverage Resolve's native transcription rather than implementing our own
- The transcription must display clearly for the editor to review before AI processing
- This is a prerequisite for Story 4.3 (Review Transcription Quality) and 4.5 (Validate Transcribable Media)

## Acceptance Criteria

### AC1: Request Transcription from Resolve

**Given** I have selected a video clip from the Media Pool
**When** RoughCut initializes the rough cut process
**Then** It requests transcription from Resolve's native API
**And** The request includes the clip reference obtained in Story 4.1

### AC2: Display Retrieved Transcription

**Given** Resolve returns transcription data
**When** RoughCut receives it
**Then** The transcript displays clearly: clean, accurate, every word captured
**And** The UI shows a scrollable text area with the full transcript

### AC3: Speaker Labels Support

**Given** The transcript displays
**When** I review it
**Then** I can read the full text content with speaker labels if available
**And** Speaker labels are formatted as "Speaker 1:", "Speaker 2:", etc. or actual names if Resolve provides them

### AC4: Performance Requirement

**Given** A 38-minute interview clip
**When** Transcription retrieval completes
**Then** Full transcript is available for AI processing within seconds
**And** The retrieval process does not block the UI for more than 5 seconds

## Technical Requirements

### Resolve API Integration

The transcription retrieval requires accessing Resolve's transcription data through the Lua API:

1. **Lua Layer** (`lua/roughcut/media_browser.lua` or new module):
   - Use Resolve's `MediaPool` and `MediaStorage` APIs to access clip metadata
   - Check if transcription exists for the selected clip
   - Retrieve transcription text data via Resolve's API

2. **API Methods to Investigate**:
   - `project:GetMediaPool():GetClipList()` - access selected clip
   - Check for Resolve's transcription metadata on clips
   - May need to trigger transcription generation if not already done

3. **Important Notes**:
   - Resolve 18+ has native transcription features
   - Transcription may be stored as metadata on the clip
   - If Resolve hasn't transcribed the clip yet, we may need to trigger it or warn the user

### Lua ↔ Python Communication

Following the JSON-RPC protocol established in the architecture:

**Request format (Lua → Python):**
```json
{
  "method": "retrieve_transcription",
  "params": {
    "clip_id": "clip_reference_from_media_pool",
    "clip_name": "interview_footage_01.mp4",
    "project_name": "Current_Project"
  },
  "id": "req_transcription_001"
}
```

**Response format (Python → Lua):**
```json
{
  "result": {
    "transcript": "Speaker 1: Welcome to the show...",
    "word_count": 5234,
    "duration_seconds": 2280,
    "has_speaker_labels": true,
    "confidence_score": 0.94
  },
  "error": null,
  "id": "req_transcription_001"
}
```

**Error format:**
```json
{
  "result": null,
  "error": {
    "code": "TRANSCRIPTION_NOT_AVAILABLE",
    "category": "resolve_api",
    "message": "Selected clip has not been transcribed by Resolve",
    "recoverable": true,
    "suggestion": "Transcribe the clip in Resolve's Edit page before using RoughCut"
  },
  "id": "req_transcription_001"
}
```

### UI Requirements

1. **Transcript Display Area**:
   - Scrollable text widget (Lua's `TextEdit` or similar)
   - Monospace font for consistent formatting
   - Minimum display size: 80 characters wide, 20 lines tall
   - Support for horizontal scrolling if needed

2. **Status Indicators**:
   - "Retrieving transcription..." during fetch
   - "Transcription loaded" on success
   - Error display with actionable guidance

3. **Navigation**:
   - Button to proceed to quality review (Story 4.3)
   - Button to go back to media selection (Story 4.1)

### Data Structure

Transcript data model:
```python
@dataclass
class Transcript:
    text: str                           # Full transcript text
    word_count: int                     # Total word count
    duration_seconds: float             # Clip duration
    has_speaker_labels: bool            # Whether speaker separation exists
    confidence_score: Optional[float] # Quality metric if available
    segments: Optional[List[Segment]]   # Time-coded segments if available

@dataclass
class Segment:
    start_time: float    # Start time in seconds
    end_time: float      # End time in seconds
    text: str            # Text for this segment
    speaker: Optional[str] # Speaker label if available
```

## Tasks / Subtasks

- [x] **Task 1**: Add Transcript data model classes (AC: #1, #3)
  - [x] Subtask 1.1: Create `TranscriptSegment` dataclass with timecodes and speaker
  - [x] Subtask 1.2: Create `Transcript` dataclass with full text, word count, and metadata
  - [x] Subtask 1.3: Add serialization methods (to_dict, from_dict)
  
- [x] **Task 2**: Implement Resolve transcription retrieval handler (AC: #1, #4)
  - [x] Subtask 2.1: Add `retrieve_transcription` handler to media.py
  - [x] Subtask 2.2: Implement transcription retrieval from Resolve metadata
  - [x] Subtask 2.3: Handle errors (no transcription, API unavailable)
  
- [x] **Task 3**: Create Lua transcript viewer UI (AC: #2, #3)
  - [x] Subtask 3.1: Create `transcript_viewer.lua` module
  - [x] Subtask 3.2: Implement scrollable text display widget
  - [x] Subtask 3.3: Add status indicators and navigation buttons
  
- [x] **Task 4**: Add protocol handler registration (AC: #1)
  - [x] Subtask 4.1: Register handler in MEDIA_HANDLERS registry
  - [x] Subtask 4.2: Update dispatcher if needed
  
- [x] **Task 5**: Write tests (AC: All)
  - [x] Subtask 5.1: Unit tests for Transcript model serialization
  - [x] Subtask 5.2: Unit tests for retrieve_transcription handler
  - [x] Subtask 5.3: Integration test for full workflow
  
- [x] **Task 6**: Update story status and documentation
  - [x] Subtask 6.1: Mark all tasks complete
  - [x] Subtask 6.2: Update Dev Agent Record
- [x] Subtask 6.3: Update File List

### Review Findings

**Code review complete.** 3 `decision-needed`, 7 `patch`, 8 `defer`, 3 dismissed as noise.

#### 🔴 Decision Needed (Requires Your Input)

- [x] [Review][Decision] Missing `project_name` Parameter — **FIXED**: Added project name retrieval via ResolveAPI and included in request params
- [x] [Review][Decision] Resolve API Not Implemented — **FIXED**: Implemented full Resolve transcription API in resolve_api.lua with:
  - `getTranscription(clipId)` - Main API to retrieve transcription from clip metadata or timeline subtitles
  - `_findClipById()` - Recursive clip lookup in Media Pool
  - `_parseTranscriptionFromMetadata()` - Parse JSON or plain text transcription data
  - `_getTranscriptionFromTimeline()` - Extract subtitles from timeline tracks
  - `_extractSubtitlesFromTimeline()` - Parse subtitle items with speaker detection
- [x] [Review][Decision] Response Format Deviation — **FIXED**: Updated handler to return standard JSON-RPC format with `result` wrapper and updated Lua client to handle both formats for backward compatibility

#### 🟡 Patch Required (Fixable Without Input)

- [x] [Review][Patch] NaN Handling Bug in Confidence Score — **FIXED**: Added explicit `math.isnan()` check in `Transcript.__post_init__`
- [x] [Review][Patch] Unvalidated Type Conversions — **FIXED**: Added try/except blocks in `from_dict()` methods for safe type conversion
- [x] [Review][Patch] Race Condition on Global State — **FIXED**: Added `_workflow_state_lock` threading.Lock() and wrapped all state access with lock
- [x] [Review][Patch] Missing Time Validation in TranscriptSegment — **FIXED**: Added `__post_init__` validation to ensure `start_time < end_time` and both are >= 0
- [x] [Review][Patch] Unchecked List Comprehension Input — **FIXED**: Added `isinstance(raw_segments, list)` check before iterating
- [x] [Review][Patch] No Timeout Mechanism — **FIXED**: Added 5-second timeout tracking with `startTimeoutTimer()`, `hasRequestTimedOut()`, and pending request management

#### 🟢 Deferred (Pre-existing Issues)

- [x] [Review][Defer] Lua component lookup issues — Pre-existing in media_browser.lua; not introduced by Story 4.2
- [x] [Review][Defer] Deep recursion without depth limit — Pre-existing in resolve_api.lua; not introduced by Story 4.2  
- [x] [Review][Defer] Type coercion issues in media models — Pre-existing; not introduced by Story 4.2

## References

- **Epic 4 Source**: [Source: epics.md#Epic 4: Media Selection & Transcription]
- **Story 4.1 Reference**: [Source: _bmad-output/implementation-artifacts/4-1-browse-media-pool.md]
- **Architecture - Resolve API**: [Source: architecture.md#Resolve API Boundary]
- **Architecture - Communication Protocol**: [Source: architecture.md#Lua ↔ Python Communication Protocol]
- **PRD - FR15**: [Source: prd.md#FR15: System can retrieve and display Resolve's native transcription for selected clips]
- **PRD - Journey 1**: [Source: prd.md#Journey 1: The Primary Editor — Standard Rough Cut Creation]
- **Resolve Scripting Guide**: DaVinci Resolve scripting API documentation for transcription access
