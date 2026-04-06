# Acceptance Auditor Review Prompt

## Role
You are an Acceptance Auditor code reviewer. You have the diff, the spec/story file, and project context. Your job is to verify the implementation matches the specification and acceptance criteria.

## Your Task
Review the diff against the spec and context docs. Check for:
- Violations of acceptance criteria
- Deviations from spec intent
- Missing implementation of specified behavior
- Contradictions between spec constraints and actual code
- Inconsistencies with architecture patterns
- Non-compliance with naming conventions
- Missing error handling specified in requirements

## Story Spec File

**File**: `_bmad-output/implementation-artifacts/6-6-position-vfx-templates.md`

### Story
As a video editor, I want the system to position VFX templates at specified timeline locations, so that lower thirds and effects appear at the right moments automatically.

### Acceptance Criteria

**AC1: Position VFX at specified timestamps**
- Given AI has suggested VFX placements (lower third at 0:15, outro CTA at 3:45)
- When Timeline is created
- Then VFX templates are positioned at those exact timestamps on the timeline

**AC2: VFX appear as Fusion compositions or generator effects**
- Given VFX templates are positioned
- When I review the timeline
- Then They appear on the timeline as Fusion compositions or generator effects that can be edited

**AC3: Align lower thirds with dialogue segments**
- Given Lower thirds are suggested for speaker introductions
- When They are placed
- Then They align with the start of dialogue segments (matching transcript boundaries)

**AC4: Apply default configurable parameters**
- Given A template has configurable parameters (text, colors, animation speed)
- When It is placed on timeline
- Then Default values are applied (editable by editor later in Fusion)

**AC5: Effects appear at specified moments with transitions**
- Given VFX placement completes
- When I play the timeline
- Then Effects appear at the specified moments with default transitions (fade in/out)

**AC6: Handle multiple VFX without inappropriate overlap**
- Given Multiple VFX are suggested (intro lower third, outro CTA)
- When They are positioned
- Then They don't overlap inappropriately (if they do, AI staggers them per format rules)

### Architecture Requirements from Spec

**Layer Separation (CRITICAL):**
- Lua Layer (`lua/ui/`): GUI only - display progress, show VFX summary
- Python Layer (`src/roughcut/backend/timeline/`): All VFX placement business logic
- Communication: JSON-RPC protocol over stdin/stdout ONLY

**Timeline Track Structure:**
- Track 1: Video/Dialogue (from Story 6.3) - DO NOT TOUCH
- Track 2: Music (from Story 6.4) - DO NOT TOUCH
- Track 3-10: SFX (from Story 6.5) - DO NOT TOUCH
- Track 11: VFX 1 ← THIS STORY
- Track 12: VFX 2 ← THIS STORY
- Track 13: VFX 3 ← THIS STORY
- Track 14: VFX 4 ← THIS STORY

**Naming Conventions:**
- Python: snake_case (place_vfx, vfx_track)
- Classes: PascalCase (VfxPlacer, VfxPlacement)
- Constants: SCREAMING_SNAKE_CASE (DEFAULT_VFX_FADE_DURATION)
- Lua: camelCase (placeVfx, vfxStart)
- JSON: snake_case ("vfx_file", "fade_in_duration")

**Non-Functional Requirements:**
- NFR4: Progress indicators for operations > 5 seconds
- NFR5: Lua GUI remains responsive during Python processing
- NFR9: Non-destructive operations (adds to timeline, never removes)
- NFR10: Validate all file paths and timecodes before operations
- NFR11: Graceful Resolve API unavailability handling
- NFR13: Actionable error messages

## Diff to Review

```diff
[Same diff as Blind Hunter - see review-blind-hunter-prompt.md]
```

## Full Implementation Files

Review these files completely:

1. **roughcut/src/roughcut/backend/timeline/vfx_placer.py** (1065+ lines)
2. **roughcut/tests/unit/backend/timeline/test_vfx_placer.py** (600+ lines)
3. **roughcut/src/roughcut/protocols/handlers/timeline.py** (modifications)
4. **roughcut/src/roughcut/backend/timeline/__init__.py** (modifications)

## Context from Previous Stories (Prerequisites)

### Story 6.1: Timeline Structure
- Timeline naming: "RoughCut_[source]_[format]_[timestamp]"
- Track structure: 1 video, 1 music, 2+ SFX, 1+ VFX
- VFX tracks start at Track 11

### Story 6.3: Cut Footage
- Provides `FootageCutter` pattern for timecode precision
- Frame-level accuracy with `timecode_to_frames()` and `frames_to_timecode()`
- Video segments establish timing context

### Story 6.5: SFX Placement (CRITICAL REFERENCE)
- `SfxPlacer` pattern for track allocation and conflict detection
- Track allocation algorithm (adapted from Tracks 3-10 to Tracks 11-14)
- Conflict detection with frame-level precision
- Code review patterns applied: stable IDs, TOCTOU protection, path traversal detection

## Expected Implementation Patterns

Based on SfxPlacer pattern from Story 6.5:

1. **Validation Function** - `validate_vfx_segments()` - checks all inputs before processing
2. **Dataclasses** - `VfxPlacement` and `VfxPlacerResult` for structured data
3. **Main Class** - `VfxPlacer` with `place_vfx_templates()` method
4. **Track Allocation** - Smart algorithm: prefer Track 11, find first available 11-14 for overlaps
5. **Conflict Detection** - Frame-level comparison prevents overlapping VFX
6. **Error Handling** - Structured error objects with code, category, message, suggestion
7. **Progress Reporting** - Callback-based with message format
8. **Protocol Handler** - JSON-RPC handler in timeline.py

## Output Format

Provide your findings as a Markdown list. For each finding:
- **One-line title** describing the issue
- **AC/Requirement**: Which acceptance criterion or requirement is violated
- **Spec Section**: Reference to story spec section
- **Evidence**: Quote the problematic code or describe location
- **Deviation**: How the implementation deviates from spec

If you find no issues, state "Implementation matches spec and acceptance criteria."

## Begin Review

Compare the implementation against the story specification. Verify all acceptance criteria are met and architecture requirements are followed.
