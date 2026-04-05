# Story 4.5: Validate Transcribable Media

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a video editor,
I want the system to validate that selected media is transcribable by Resolve,
So that I get immediate feedback if a clip cannot be processed.

## Context

This story is the final validation gate in **Epic 4: Media Selection & Transcription**, completing the media selection and validation workflow before proceeding to AI rough cut generation.

**Workflow Position:**
- Story 4.1: Browse Media Pool → User selects clip
- Story 4.2: Retrieve Transcription → System fetches transcript
- Story 4.3: Review Transcription Quality → Quality analysis
- Story 4.4: Error Recovery Workflow → Handle poor quality audio
- **Story 4.5: Validate Transcribable Media** → Final transcribability check before AI processing

**Key Points:**
- This is the FINAL validation before proceeding to Epic 5 (AI Rough Cut Generation)
- Validation must happen BEFORE attempting transcription (prevent wasted API calls)
- This complements Story 4.3 (quality review) — 4.3 checks audio quality, 4.5 checks transcribability
- Must detect: no audio track, unsupported codecs, corrupted files
- Error messages must be actionable (per NFR13)
- Workflow should gracefully degrade — user can select different clip

**Technical Context:**
- Uses Resolve's native API to inspect clip properties
- Must work with Story 4.1's media pool browsing
- Should reuse patterns from Story 4.2's transcription retrieval
- Must follow Story 4.4's error recovery patterns

## Acceptance Criteria

### AC1: Validate Clip Has Audio Track

**Given** I have selected a video clip from the Media Pool
**When** RoughCut initiates the transcription workflow
**Then** It first validates that the clip contains at least one audio track

**Given** A clip has video but no audio tracks
**When** Validation runs
**Then** RoughCut displays: "Cannot transcribe - no audio detected"
**And** The error includes: "Selected clip has no audio. Please choose a clip with audio content."
**And** A [Select Different Clip] button is presented

### AC2: Validate Supported Audio Codecs

**Given** A clip has an audio track
**When** Validation runs
**Then** RoughCut checks that the audio codec is supported by Resolve's transcription engine

**Given** A clip uses an unsupported audio codec (e.g., some proprietary formats, corrupted audio streams)
**When** Validation runs
**Then** RoughCut displays: "Cannot transcribe - unsupported audio format"
**And** The error includes: "Audio codec not supported for transcription. Try rendering to a standard format first."
**And** A [Render to Standard Format] guidance button is shown

### AC3: Validate Clip Accessibility

**Given** A clip is selected in the Media Pool
**When** Validation runs
**Then** RoughCut verifies the source media file is accessible (file exists, not offline)

**Given** A clip's source file is offline or moved
**When** Validation runs
**Then** RoughCut displays: "Cannot transcribe - media offline"
**And** The error includes: "Source media file not found at [path]. Reconnect media in Resolve Media Pool."
**And** A [Reconnect in Resolve] guidance button is shown

### AC4: Provide Actionable Recovery Options

**Given** Media fails transcribability validation for any reason
**When** The error displays
**Then** The error message includes actionable guidance specific to the failure type

**Given** I see a validation error
**When** I want to try a different clip
**Then** Clicking [Select Different Clip] returns me to Story 4.1's Media Pool browser
**And** The previously selected clip is not pre-selected

**Given** I see a "unsupported format" error
**When** I click [Render to Standard Format]
**Then** RoughCut displays guidance: "Deliver page → YouTube 1080p preset → Render in-place → Replace clip in Media Pool"

## Tasks / Subtasks

- [x] **Task 1**: Create media validation module in Python (AC: #1, #2, #3)
  - [x] Subtask 1.1: Add `validate_transcribable_media` handler to media.py
  - [x] Subtask 1.2: Implement `MediaValidator` class with audio track detection
  - [x] Subtask 1.3: Add codec validation (check against supported list)
  - [x] Subtask 1.4: Add file accessibility check (verify source path exists)
  - [x] Subtask 1.5: Return structured validation result with specific error codes

- [x] **Task 2**: Update Lua media browser to trigger validation (AC: #1)
  - [x] Subtask 2.1: Add validation call before transcription retrieval
  - [x] Subtask 2.2: Display validation loading state: "Checking media compatibility..."
  - [x] Subtask 2.3: Pass validation result to transcription workflow
  - [x] Subtask 2.4: Skip transcription retrieval if validation fails

- [x] **Task 3**: Create validation error UI in Lua (AC: #4)
  - [x] Subtask 3.1: Create `showValidationError()` function in media_browser.lua
  - [x] Subtask 3.2: Display error-specific messages based on failure type
  - [x] Subtask 3.3: Add [Select Different Clip] button returning to browser
  - [x] Subtask 3.4: Add format-specific guidance for codec issues
  - [x] Subtask 3.5: Add reconnection guidance for offline media

- [x] **Task 4**: Integrate with existing transcription workflow (AC: #1, #2, #3)
  - [x] Subtask 4.1: Call validation before `retrieve_transcription` in workflow
  - [x] Subtask 4.2: Store validation result in session state
  - [x] Subtask 4.3: Re-validate if user switches clips (don't cache across different clips)
  - [x] Subtask 4.4: Skip re-validation if re-trying same clip (within same session)

- [x] **Task 5**: Define supported codec list and validation rules
  - [x] Subtask 5.1: Document Resolve-supported audio codecs for transcription
  - [x] Subtask 5.2: Create codec whitelist/blacklist configuration
  - [x] Subtask 5.3: Handle edge cases (multi-track audio, mixed formats)
  - [x] Subtask 5.4: Add codec detection from Resolve clip properties

- [x] **Task 6**: Write tests (AC: All)
  - [x] Subtask 6.1: Unit tests for `MediaValidator` class
  - [x] Subtask 6.2: Unit tests for validation handler
  - [x] Subtask 6.3: Integration tests for full validation workflow
  - [x] Subtask 6.4: Test edge cases: no audio, offline media, unsupported codec

- [x] **Task 7**: Update story status and documentation
  - [x] Subtask 7.1: Mark all tasks complete
  - [x] Subtask 7.2: Update Dev Agent Record
  - [x] Subtask 7.3: Update File List

## Dev Notes

### Architecture Compliance

**Layer Separation (CRITICAL):**
- **Python Backend** (`src/roughcut/backend/`): Media validation logic, codec detection, file checks
- **Lua Frontend** (`lua/roughcut/`): Validation trigger, error UI, user interaction
- **Protocol**: JSON-RPC over stdin/stdout for all communication

**Files to Modify/Create:**
- `src/roughcut/backend/media/validator.py` — NEW FILE: Media validation logic
- `src/roughcut/protocols/handlers/media.py` — Add `validate_transcribable_media` handler
- `lua/roughcut/media_browser.lua` — Add validation trigger and error display
- `src/roughcut/config/media_formats.py` — NEW FILE: Supported codec definitions

**Integration Points:**
- Called from Story 4.1's media selection flow (before Story 4.2's transcription)
- Uses same Resolve API wrapper as Story 4.2
- Error UI follows Story 4.4's error recovery patterns

### Technical Requirements

**Python Validation Handler Pattern:**
```python
def handle_validate_transcribable_media(self, params: dict) -> dict:
    """
    Validate that media can be transcribed by Resolve.
    
    Args:
        params: {"clip_name": str, "clip_id": str (optional)}
    
    Returns:
        {
            "result": {
                "valid": True,
                "checks": {
                    "has_audio": True,
                    "codec_supported": True,
                    "file_accessible": True
                }
            },
            "error": None
        }
    
    Or on failure:
        {
            "result": {"valid": False, "failed_check": "no_audio"},
            "error": {
                "code": "NO_AUDIO_TRACK",
                "category": "validation",
                "message": "Selected clip has no audio track",
                "recoverable": True,
                "suggestion": "Select a clip with audio content"
            }
        }
    """
```

**MediaValidator Class Structure:**
```python
class MediaValidator:
    """Validates media transcribability for Resolve transcription."""
    
    # Supported codecs for Resolve transcription
    SUPPORTED_CODECS = ["PCM", "AAC", "MP3", "WAV"]
    
    def validate(self, clip_data: dict) -> ValidationResult:
        """Run all validation checks."""
        checks = {
            "has_audio": self._check_audio_track(clip_data),
            "codec_supported": self._check_codec(clip_data),
            "file_accessible": self._check_file_accessible(clip_data)
        }
        
        failed = [k for k, v in checks.items() if not v]
        
        return ValidationResult(
            valid=len(failed) == 0,
            checks=checks,
            failed_check=failed[0] if failed else None
        )
```

**Lua Validation UI Pattern:**
```lua
function onClipSelected(clipName, clipId)
    -- Show validation in progress
    showValidationSpinner("Checking media compatibility...")
    
    -- Call Python backend
    local response = sendJsonRpcRequest("validate_transcribable_media", {
        clip_name = clipName,
        clip_id = clipId
    })
    
    hideValidationSpinner()
    
    if response.error then
        showValidationError(response.error)
        return false
    end
    
    if not response.result.valid then
        showValidationErrorForCode(response.result.failed_check)
        return false
    end
    
    -- Proceed to transcription retrieval
    return retrieveTranscription(clipName, clipId)
end

function showValidationError(errorData)
    local dialog = resolve.Window({
        title = "Media Validation Failed",
        size = {width = 500, height = 300}
    })
    
    -- Error icon + message
    -- Specific guidance based on error.code
    -- [Select Different Clip] button
    -- [Cancel] button
    
    dialog:Show()
end
```

### Library/Framework Requirements

**No New Dependencies:**
- Uses existing Resolve API wrapper from Story 4.2
- Uses existing JSON-RPC protocol
- Uses existing error handling patterns

**Resolve API Integration:**
```python
# Get clip properties from Resolve
clip = project:GetMediaPool():GetRootFolder():GetClip(clip_name)
clip_info = clip:GetClipProperty()

# Check audio tracks
audio_tracks = clip_info.get("Audio Tracks", 0)

# Check codec
codec = clip_info.get("Codec", "Unknown")
```

### File Structure Requirements

Per architecture document:
```
src/roughcut/backend/media/               # NEW DIRECTORY
    ├── __init__.py
    └── validator.py                      # MediaValidator class

src/roughcut/config/
    └── media_formats.py                  # Supported codec definitions

src/roughcut/protocols/handlers/media.py  # Add validation handler
lua/roughcut/media_browser.lua            # Add validation UI
```

### Testing Requirements

**Test Coverage:**
1. Validation passes for valid media (has audio, supported codec, accessible)
2. Validation fails for no audio track
3. Validation fails for unsupported codec
4. Validation fails for offline/missing file
5. Error messages are specific and actionable
6. UI flow: validation → error → select different clip → re-validate

**Testing Pattern:**
```python
# Unit test
class TestMediaValidator:
    def test_valid_media_passes_all_checks(self):
        validator = MediaValidator()
        result = validator.validate({
            "audio_tracks": 2,
            "codec": "PCM",
            "file_path": "/valid/path.mp4"
        })
        assert result.valid is True
    
    def test_no_audio_fails_validation(self):
        validator = MediaValidator()
        result = validator.validate({
            "audio_tracks": 0,
            "codec": None,
            "file_path": "/valid/path.mp4"
        })
        assert result.valid is False
        assert result.failed_check == "has_audio"

# Integration test
def test_validation_workflow():
    # Select clip without audio
    # Trigger validation
    # Verify NO_AUDIO error returned
    # Verify UI shows error dialog
    # Click "Select Different Clip"
    # Verify returned to browser
```

### Critical Implementation Notes

1. **Validate BEFORE Transcription (NFR4):** Never waste API calls or user time on media that can't be transcribed. Run validation before attempting to retrieve transcription.

2. **Specific Error Codes:** Use distinct error codes for each failure type:
   - `NO_AUDIO_TRACK` — Clip has no audio
   - `UNSUPPORTED_CODEC` — Audio codec not supported
   - `MEDIA_OFFLINE` — Source file missing
   - `CLIP_NOT_FOUND` — Clip not in Media Pool

3. **Actionable Guidance (NFR13):** Every error must include specific recovery steps:
   - No audio → "Select a clip with audio content"
   - Unsupported codec → "Deliver page → YouTube 1080p preset → Render in-place"
   - Media offline → "Reconnect media in Resolve Media Pool"

4. **UI Responsiveness (NFR5):** Validation happens in Python backend — Lua shows spinner. Keep validation fast (< 2 seconds).

5. **Resolve UI Conventions (NFR14):** Error dialogs use Resolve standard styling. Warning icon (⚠) for validation failures.

6. **Non-Destructive (NFR9):** Validation never modifies clips, timelines, or files. It's a read-only check.

7. **Session State:** Store validation result in session to avoid re-validating same clip multiple times:
   ```lua
   _session.validated_clips[clip_id] = validation_result
   ```

### Reference Documents

**Architecture:**
- [Architecture: Project Structure](../../planning-artifacts/architecture.md#project-structure--boundaries) — File placement rules
- [Architecture: Lua ↔ Python Communication](../../planning-artifacts/architecture.md#lua--python-communication-protocol) — Protocol format
- [Architecture: Error Handling](../../planning-artifacts/architecture.md#process-patterns) — Error object structure

**Previous Stories:**
- [Story 4.1: Browse Media Pool](./4-1-browse-media-pool.md) — Media pool browsing, clip selection
- [Story 4.2: Retrieve Transcription](./4-2-retrieve-transcription.md) — Transcription retrieval, handler patterns
- [Story 4.3: Review Transcription Quality](./4-3-review-transcription-quality.md) — Quality analysis, UI patterns
- [Story 4.4: Error Recovery Workflow](./4-4-error-recovery-workflow.md) — Error UI patterns, recovery workflows

**PRD:**
- [PRD: FR18](../../planning-artifacts/prd.md) — Validate transcribable media requirement
- [PRD: NFR4](../../planning-artifacts/prd.md) — Progress indicators requirement
- [PRD: NFR9](../../planning-artifacts/prd.md) — Non-destructive operations requirement
- [PRD: NFR13](../../planning-artifacts/prd.md) — Actionable error messages requirement

**Epics:**
- [Epics: Epic 4](../../planning-artifacts/epics.md#epic-4-media-selection--transcription) — Story 4.5 context within epic

## Dev Agent Record

### Agent Model Used

fireworks-ai/accounts/fireworks/routers/kimi-k2p5-turbo

### Debug Log References

- No critical errors encountered during implementation
- All handlers implemented following Story 4.2/4.3/4.4 patterns
- Lua UI follows established conventions from previous stories

### Completion Notes List

✅ **Task 1: Media Validation Module (Python)**
- Created `MediaValidator` class with three main checks:
  1. Audio track detection (`_check_audio_track`)
  2. Codec validation against supported/prohibited lists (`_check_codec`)
  3. File accessibility check (`_check_file_accessible`)
- Implemented fail-fast validation that returns on first failure
- Added proper error codes: NO_AUDIO_TRACK, UNSUPPORTED_CODEC, MEDIA_OFFLINE
- Structured validation results with actionable suggestions per NFR13

✅ **Task 2 & 3: Lua Media Browser Integration**
- Added `validateAndProceed()` function to media_browser.lua
- Implemented validation spinner UI: "Checking media compatibility..."
- Added session-based validation caching to avoid re-validating same clip
- Created `showValidationError()` with error-specific UI:
  - Warning icon and clear error messaging
  - Error-specific buttons (Format Guide for codec issues)
  - [Select Different Clip] button to return to browser
  - [Cancel] button to abort workflow
- Added `showFormatConversionGuide()` for unsupported codec guidance

✅ **Task 4: Workflow Integration**
- Validation runs BEFORE transcription retrieval (prevent wasted API calls)
- Session state `_session.validatedClips` caches validation results
- Re-validation triggered when user switches to different clip
- Skip re-validation when re-trying same clip within session

✅ **Task 5: Codec Configuration**
- Created `media_formats.py` with comprehensive codec definitions:
  - Supported: PCM, AAC, MP3, WAV, LPCM (with AudioCodecInfo metadata)
  - Problematic: DOLBY_E, DOLBY_DIGITAL, DTS, OPUS, FLAC, WMA
- Added utility functions: `get_codec_info()`, `is_codec_supported()`, `get_format_conversion_guide()`
- Codec matching is case-insensitive with substring support

✅ **Task 6: Comprehensive Tests**
- Created `test_validator.py` with 12 test classes:
  - TestValidationCheck: Dataclass serialization
  - TestValidationResult: Success/failure result handling
  - TestMediaValidatorAudioTrack: Audio track detection (5 test methods)
  - TestMediaValidatorCodec: Codec validation (10 test methods)
  - TestMediaValidatorFileAccessibility: File checks (5 test methods)
  - TestMediaValidatorFullValidation: End-to-end validation (7 test methods)
  - TestMediaValidatorCodecLists: Codec list methods
  - TestMediaValidatorEdgeCases: Edge cases (6 test methods)
- Created `test_media_formats.py` with 4 test classes:
  - TestSupportedCodecs: Supported codec definitions
  - TestProblematicCodecs: Problematic codec definitions
  - TestUtilityFunctions: Codec lookup and support checking (12 test methods)

### File List

**New Files:**
- `roughcut/src/roughcut/backend/media/validator.py` — MediaValidator class with transcribability checks
- `roughcut/src/roughcut/config/media_formats.py` — Supported codec definitions and utilities
- `roughcut/tests/unit/backend/media/test_validator.py` — Unit tests for validation logic (12 test classes, 40+ test methods)
- `roughcut/tests/unit/config/test_media_formats.py` — Unit tests for codec configuration (4 test classes, 20+ test methods)

**Modified Files:**
- `roughcut/src/roughcut/protocols/handlers/media.py` — Added `validate_transcribable_media` handler and import
- `roughcut/lua/media_browser.lua` — Added validation trigger (`validateAndProceed`), error UI (`showValidationError`), format guide (`showFormatConversionGuide`), and session caching

**Total File Count:** 4 new files, 2 modified files

---

## Change Log

| Date | Change | Notes |
|------|--------|-------|
| 2026-04-04 | Story created | Loaded context from Stories 4.1-4.4, Architecture, Epics |
| 2026-04-04 | Task 1 complete | Created MediaValidator class with 3 validation checks |
| 2026-04-04 | Task 2-3 complete | Added Lua validation trigger and error UI |
| 2026-04-04 | Task 4 complete | Integrated validation into transcription workflow |
| 2026-04-04 | Task 5 complete | Created media_formats.py codec configuration |
| 2026-04-04 | Task 6 complete | Added comprehensive unit tests (60+ test methods) |
| 2026-04-04 | Story complete | All ACs satisfied, ready for review |
| 2026-04-04 | Code review | 2 decision-needed, 8 patch, 2 defer, 2 dismissed |
| 2026-04-04 | Patches applied | All 8 patch findings resolved automatically |
| 2026-04-04 | Decisions resolved | 1B: Keep Format Guide button, 2A: Add Reconnect button |
| 2026-04-04 | Story done | All review findings resolved, story complete |

---

## Previous Story Intelligence

### From Story 4.4 (Error Recovery Workflow)

**What Worked Well:**
1. Error recovery dialog with multiple options gave users control
2. Actionable guidance specific to error type (audio cleanup steps)
3. State management for recovery workflow was clean and effective
4. "Select Different Clip" pattern from 4.4 should be reused here

**Patterns to Follow:**
1. Error dialogs use `resolve.Window()` with consistent sizing (500-600px width)
2. Structured error objects with `code`, `category`, `message`, `recoverable`, `suggestion`
3. Use error codes for conditional UI (e.g., show different guidance for different failures)
4. Session state pattern: `_session.state_name = value` with lock if needed
5. Always wrap Lua UI operations in `pcall()` for error safety

**Code Patterns Established (from 4.2-4.4):**

```python
# Handler pattern with specific error codes
def handle_validate(self, params: dict) -> dict:
    try:
        result = self._validate(params)
        if not result.valid:
            return {
                "result": result.to_dict(),
                "error": {
                    "code": self._get_error_code(result.failed_check),
                    "category": "validation",
                    "message": self._get_error_message(result.failed_check),
                    "recoverable": True,
                    "suggestion": self._get_suggestion(result.failed_check)
                }
            }
        return {"result": result.to_dict(), "error": None}
    except Exception as e:
        return {
            "result": None,
            "error": {
                "code": "VALIDATION_FAILED",
                "category": "internal",
                "message": str(e),
                "recoverable": False,
                "suggestion": "Try selecting a different clip"
            }
        }
```

```lua
-- UI error display pattern
function showSpecificError(errorData)
    local status, result = pcall(function()
        local dialog = resolve.Window({...})
        
        -- Conditional UI based on error code
        if errorData.code == "NO_AUDIO_TRACK" then
            dialog:AddLabel("This clip has no audio content.")
            dialog:AddLabel("Please select a clip with audio.")
        elseif errorData.code == "UNSUPPORTED_CODEC" then
            dialog:AddLabel("Audio format not supported.")
            dialog:AddButton("Show Format Guide", onShowFormatGuide)
        end
        
        dialog:AddButton("Select Different Clip", onSelectDifferentClip)
        dialog:Show()
    end)
    
    if not status then
        showGenericError("Failed to show error dialog")
    end
end
```

**Files Referenced from 4.2-4.4:**
- `src/roughcut/protocols/handlers/media.py` — Handler patterns, error structures
- `lua/roughcut/media_browser.lua` — Media pool browsing, clip selection
- `src/roughcut/backend/timeline/resolve_api.py` — Resolve API wrapper

**Issues Encountered (Fixed in 4.3/4.4 Code Review):**
1. Always return explicit result in handlers — don't rely on implicit returns
2. Use `pcall()` for all Resolve API calls — API can be unavailable
3. Nil-check all values from Resolve before using in conditionals
4. Error codes must be consistent between Python and Lua

### Git Intelligence

**Recent Commit Pattern:**
```
8e6054c 4.4 story
1c5754f 4.2 story
a938c4e Story 4.1: Browse Media Pool - Complete
```

**Development Pattern Established:**
1. Start with Python validation logic and data models
2. Add handler to media.py protocol
3. Implement Lua UI components with error handling
4. Wire validation into existing workflow (before transcription)
5. Add tests covering all validation scenarios
6. Run code review with blind hunter, edge case hunter, acceptance auditor

**Naming Conventions (from Architecture):**
- Python handlers: `snake_case` — `validate_transcribable_media`, `handle_validation_error`
- Python classes: `PascalCase` — `MediaValidator`, `ValidationResult`
- Lua functions: `camelCase` — `onClipSelected`, `showValidationError`
- Lua GUI components: `PascalCase` — `ValidationErrorDialog`
- Error codes: `SCREAMING_SNAKE_CASE` — `NO_AUDIO_TRACK`, `UNSUPPORTED_CODEC`

### Critical Implementation Notes

1. **Validation Timing:** This validation must run BEFORE transcription retrieval (Story 4.2). The workflow flow should be:
   ```
   Select Clip (4.1)
   → Validate Transcribable (4.5) [NEW]
   → Retrieve Transcription (4.2)
   → Review Quality (4.3)
   → Error Recovery if needed (4.4)
   → Proceed to Format Selection (5.x)
   ```

2. **Integration with Existing Flow:** The validation should be inserted into the existing transcript workflow in `lua/roughcut/transcript_workflow.lua` (or similar) that orchestrates 4.1 → 4.2 → 4.3 → 4.4. Add the validation step at the beginning.

3. **Resolve API Limitations:** Resolve's API for checking clip properties is limited. You may need to:
   - Use `GetClipProperty()` to get audio track count
   - Check codec from clip metadata (may not always be available)
   - For codec detection, might need to use `GetMediaPoolItem()` and inspect properties
   - If direct codec check isn't possible, consider attempting transcription and catching specific errors (fallback approach)

4. **Error Code Consistency:** Define error codes in ONE place and reuse:
   ```python
   # In config or constants module
   class ValidationErrorCodes:
       NO_AUDIO = "NO_AUDIO_TRACK"
       UNSUPPORTED_CODEC = "UNSUPPORTED_CODEC"
       MEDIA_OFFLINE = "MEDIA_OFFLINE"
       CLIP_NOT_FOUND = "CLIP_NOT_FOUND"
   ```

5. **MVP Scope:** Per PRD, target 50-60% AI suggestion usability. Validation doesn't need to catch every edge case — just the common ones (no audio, obvious codec issues, offline media). It's okay to fall back to transcription attempt + error handling for rare cases.

6. **Performance:** Validation should be fast. If checking codec requires expensive operations, consider caching or skipping detailed checks in MVP.

## Project Context Reference

**RoughCut Architecture Summary:**
- Hybrid Lua/Python plugin for DaVinci Resolve
- Lua: GUI only, no filesystem/network access
- Python: All business logic, AI processing, external APIs
- Communication: JSON-RPC over stdin/stdout
- Database: SpacetimeDB for asset metadata
- AI: OpenAI SDK direct (abstraction deferred)

**Non-Functional Requirements (Relevant to This Story):**
- NFR4: Progress indicators for operations > 5 seconds — Show "Checking media compatibility..."
- NFR5: Lua GUI must remain responsive — validation runs in Python backend
- NFR9: Non-destructive operations — validation is read-only
- NFR13: Actionable error messages — all validation errors include specific guidance
- NFR14: Resolve UI conventions — use standard dialog styling

**Naming Conventions:**
- Python: `snake_case` functions, `PascalCase` classes
- Lua: `camelCase` functions, `PascalCase` GUI components
- Database: `snake_case` plural tables
- Protocol: `snake_case` JSON field names
- Error codes: `SCREAMING_SNAKE_CASE`

**Story Completion Status**

Status: ready-for-dev

Ultimate context engine analysis completed - comprehensive developer guide created

**Next Steps After Completion:**
1. Run `dev-story` to implement this story
2. Run `code-review` when implementation complete
3. Story 5.1 (Initiate Rough Cut Generation) is next in Epic 5

---

### Review Findings

**Code review complete.** 2 `decision-needed`, 8 `patch`, 2 `defer`, 2 dismissed as noise.

#### 🔴 Decision Needed (Need User Input) — **ALL RESOLVED**

- [x] **[Review][Decision-Resolved]** AC4 Button Implementation — **DECISION: 1B** — Keep `[Show Format Guide]` button as-is. The format guide provides detailed, actionable steps that are more helpful than a button that can't auto-perform the action. Applied: No code changes needed.
- [x] **[Review][Decision-Resolved]** `[Reconnect in Resolve]` Button — **DECISION: 2A** — Added `[Reconnect in Resolve]` button for MEDIA_OFFLINE errors that opens detailed reconnection guidance dialog. Applied: Added `showReconnectGuidance()` function and button handler.

#### 🔴 Patch Required (Fixable Issues) — **ALL FIXED**

- [x] **[Review][Patch]** Lua error code constants [media_browser.lua] — Added `MediaBrowser.ERROR_CODES` constants table and updated string literals to use constants
- [x] **[Review][Patch]** Add nil guards for clip data access [media_browser.lua:370-380] — Added nil checks and default value initialization for all clip fields
- [x] **[Review][Patch]** File path length validation [validator.py:94-104] — Added MAX_PATH_LENGTH constant and path length validation in `_check_file_accessible`
- [x] **[Review][Patch]** Validate audio_tracks is non-negative [validator.py:193-203] — Added check for negative audio_tracks values with 'negative_value' reason
- [x] **[Review][Patch]** Interpolate path in MEDIA_OFFLINE error [validator.py:157] — Error message now includes actual file path using f-string interpolation
- [x] **[Review][Patch]** Add timeout to validation spinner [media_browser.lua:616-680] — Added `VALIDATION_TIMEOUT` constant, `validationStartTime` tracking, and `checkValidationTimeout()` function
- [x] **[Review][Patch]** Empty clip name handling [media_browser.lua:373] — Clip name defaults to clip.id if empty or nil
- [x] **[Review][Patch]** Test file path portability — Tests already use tempfile; added test for negative audio_tracks and long paths

#### 🟡 Deferred (Pre-existing or Complex)

- [x] **[Review][Defer]** Thread-safe session state access [media_browser.lua:335-345] — `_session.validatedClips` not thread-safe. Consider concurrent validation requests. **Deferred:** Requires broader session state refactoring across all stories.
- [x] **[Review][Defer]** Unicode file path handling [validator.py:200-220] — File accessibility check may fail on Unicode paths on some Windows configurations. **Deferred:** Requires testing across multiple OS configurations.

#### 🟢 Dismissed (Noise/False Positive)

- [x] **[Review][Dismiss]** Missing duration validation — Duration not critical for transcribability check. Transcription workflow will handle invalid durations.
- [x] **[Review][Dismiss]** Test count excessive — 60+ test methods is thorough, not excessive for validation logic.

---

### Previous Stories File List Reference

**Files from Story 4.1 (Browse Media Pool):**
- `src/roughcut/protocols/handlers/media.py` — MediaHandlers with browse functionality
- `lua/roughcut/media_browser.lua` — Media Pool browser UI

**Files from Story 4.2 (Retrieve Transcription):**
- `src/roughcut/backend/database/models.py` — Transcript dataclass
- `src/roughcut/protocols/handlers/media.py` — Extended with transcription handlers
- `lua/roughcut/transcript_viewer.lua` — Transcript display UI

**Files from Story 4.3 (Review Transcription Quality):**
- `src/roughcut/backend/media/quality_analyzer.py` — Quality analysis logic
- `lua/roughcut/transcript_viewer.lua` — Quality banner and problem highlighting

**Files from Story 4.4 (Error Recovery Workflow):**
- `src/roughcut/protocols/handlers/media.py` — Abort and retry handlers
- `lua/roughcut/error_recovery.lua` — Error recovery UI
- `docs/audio_cleanup_workflow.md` — Audio cleanup guide

**Files This Story Should Modify/Create:**
- `src/roughcut/backend/media/validator.py` — NEW
- `src/roughcut/config/media_formats.py` — NEW
- `src/roughcut/protocols/handlers/media.py` — Add handler
- `lua/roughcut/media_browser.lua` — Add validation trigger and error UI
