# Edge Case Hunter Review Prompt

## Role
You are an Edge Case Hunter code reviewer. You have the diff AND read access to the project codebase. Your job is to find edge cases, boundary conditions, and overlooked scenarios.

## Your Task
Find edge cases and boundary conditions in this code. Look for:
- Off-by-one errors and boundary issues
- Empty inputs, null/None handling
- Race conditions and timing issues
- Resource exhaustion scenarios
- Invalid state transitions
- Concurrency problems
- Input validation gaps
- Exception handling gaps
- Scale/performance limits
- State consistency issues
- Integration edge cases

## Diff to Review

```diff
[Same diff as Blind Hunter - see review-blind-hunter-prompt.md]
```

## Full Source Files to Review

You have access to read the complete implementation:

1. **roughcut/src/roughcut/backend/timeline/vfx_placer.py** (1065+ lines)
   - `validate_vfx_segments()` - Comprehensive validation function
   - `detect_vfx_type()` - File extension-based detection
   - `apply_template_params()` - Template default merging
   - `VFX_TEMPLATE_DEFAULTS` - Constant dictionary
   - `VfxPlacement` dataclass
   - `VfxPlacerResult` dataclass
   - `VfxPlacer` class - Main implementation
     - `__init__()`
     - `_seconds_to_frames()`
     - `_check_track_conflict()`
     - `_allocate_vfx_track()`
     - `_find_vfx_in_media_pool()`
     - `_import_vfx_to_pool()`
     - `_create_timeline_vfx_clip()`
     - `_generate_stable_clip_id()`
     - `_apply_fade_transitions()`
     - `place_vfx_templates()` - Main entry point

2. **roughcut/tests/unit/backend/timeline/test_vfx_placer.py** (600+ lines)
   - TestValidateVfxSegments
   - TestVfxPlacementDataclass
   - TestVfxPlacerResult
   - TestVfxPlacerSecondsToFrames
   - TestDetectVfxType
   - TestApplyTemplateParams
   - TestVfxPlacerTrackConflict
   - TestVfxPlacerTrackAllocation
   - TestVfxPlacerDefaultsAndConstants
   - TestVfxPlacerPlaceVfxClips

3. **roughcut/src/roughcut/protocols/handlers/timeline.py**
   - `place_vfx_on_timeline()` handler function
   - Error codes: VFX_PLACEMENT_FAILED, MISSING_VFX_SEGMENTS

4. **roughcut/src/roughcut/backend/timeline/__init__.py**
   - VFX exports

## Context from Existing Code (Patterns to Follow)

Review these existing files to understand patterns and consistency:

1. **roughcut/src/roughcut/backend/timeline/sfx_placer.py**
   - Similar implementation pattern for SFX
   - Track allocation algorithm (adapted for Tracks 3-10)
   - Conflict detection logic
   - Code review fixes already applied: stable IDs, TOCTOU protection, FPS validation

2. **roughcut/src/roughcut/backend/timeline/music_placer.py**
   - Music placement pattern

3. **roughcut/src/roughcut/backend/timeline/cutter.py**
   - Timecode/frame conversion patterns

## Key Implementation Details

### VFX Track Structure
- Track 1: Video/Dialogue (from Story 6.3)
- Track 2: Music (from Story 6.4)
- Tracks 3-10: SFX (from Story 6.5)
- **Tracks 11-14: VFX (THIS STORY)** - 4 tracks max

### Constants
- `VFX_TRACK_START = 11`
- `VFX_TRACK_END = 14`
- `DEFAULT_VFX_FADE_IN_SECONDS = 0.5`
- `DEFAULT_VFX_FADE_OUT_SECONDS = 0.5`

### VFX Types
- `.comp` files → `fusion_composition`
- `.setting` files → `generator_effect`
- Unknown → defaults to `generator_effect`

### Template Defaults
```python
VFX_TEMPLATE_DEFAULTS = {
    "lower_third": {
        "speaker_name": "",
        "title": "",
        "company": "",
        "duration_seconds": 5.0,
        "animation_in": "fade_slide",
        "animation_out": "fade_out"
    },
    "outro_cta": {
        "cta_text": "Subscribe",
        "sub_text": "For more content",
        "duration_seconds": 5.0,
        "animation_style": "pop_in"
    },
    "intro_title": {
        "title_text": "",
        "subtitle_text": "",
        "duration_seconds": 3.0,
        "animation_style": "reveal"
    },
    "transition": {
        "duration_seconds": 1.0,
        "animation_style": "wipe"
    },
    "generic": {
        "duration_seconds": 3.0,
        "animation_style": "fade"
    }
}
```

## Output Format

Provide your findings as a Markdown list. For each finding:
- **One-line title** describing the edge case
- **Category**: boundary, null-handling, race-condition, scale, validation, or other
- **Location**: File and function/method where issue exists
- **Scenario**: Describe the edge case condition
- **Risk**: What could go wrong

If you find no edge cases, state "No edge cases found beyond normal operational bounds."

## Begin Review

Search for edge cases in the diff and full source files. Focus on boundary conditions, race conditions, and overlooked scenarios.
