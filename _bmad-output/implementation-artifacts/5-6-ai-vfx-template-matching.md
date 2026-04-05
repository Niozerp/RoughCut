# Story 5.6: AI VFX/Template Matching

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a video editor,
I want the AI to match VFX and template assets to format requirements,
So that lower thirds, transitions, and effects are positioned appropriately.

## Acceptance Criteria

1. **VFX Requirement Identification** (AC: #1)
   - **Given** the format template specifies VFX requirements (e.g., "lower thirds for speaker names")
   - **When** AI processes the rough cut
   - **Then** it identifies template moments needing VFX
   - **And** moments are mapped to specific timestamps and format sections

2. **Lower Third Matching** (AC: #2)
   - **Given** lower thirds are needed for speaker introductions
   - **When** AI searches VFX template library
   - **Then** it matches appropriate templates (e.g., "standard_lower_third", "corporate_nameplate")
   - **And** matches consider both AI-generated tags and folder path context

3. **Template Placement Calculation** (AC: #3)
   - **Given** template placements are determined
   - **When** positions are calculated
   - **Then** they align with transcript segment boundaries and format timing rules
   - **And** placements respect template duration specifications

4. **VFX Presentation in Review Document** (AC: #4)
   - **Given** VFX suggestions are generated
   - **When** editor reviews the rough cut document
   - **Then** they see: "VFX: lower_third_template at 0:15 (intro speaker), outro_cta at 3:45"
   - **And** each entry includes: file path, template type, placement timestamp, duration

5. **Template Asset Group Priority** (AC: #5)
   - **Given** a format has specific template asset groups defined
   - **When** AI processes
   - **Then** it prioritizes assets from those predefined groups
   - **And** falls back to general VFX library if group assets unavailable

## Tasks / Subtasks

- [x] **Task 1:** Create VFX requirement identification system (AC: #1)
  - [x] Create `VFXMatcher` class in `backend/ai/vfx_matcher.py`
  - [x] Implement `identify_vfx_requirements()` method
  - [x] Create VFX requirement type taxonomy (lower_third, transition, outro_cta, title_card, etc.)
  - [x] Define `VFXRequirement` dataclass (timestamp, type, context, duration, format_section)
  - [x] Parse format template VFX specifications

- [x] **Task 2:** Build VFX template matching engine (AC: #2, #3)
  - [x] Implement `match_vfx_to_requirements()` method
  - [x] Create tag scoring algorithm with weights for VFX categories
  - [x] Query SpacetimeDB for VFX/template assets by tags
  - [x] Add folder path context matching (e.g., "LowerThirds", "Transitions", "Titles")
  - [x] Implement template duration validation

- [x] **Task 3:** Implement placement calculation & timing (AC: #3)
  - [x] Create `VFXMatch` dataclass with placement data
  - [x] Implement `calculate_placement()` for timestamp alignment
  - [x] Add duration overlap detection and resolution
  - [x] Create format timing rule compliance checks
  - [x] Handle multi-template sequencing (e.g., intro → main → outro)

- [x] **Task 4:** Create AI prompt for VFX matching (AC: #1, #2)
  - [x] Create `match_vfx_system.txt` prompt template in `backend/ai/prompt_templates/`
  - [x] Include format template VFX specifications
  - [x] Add transcript segments with speaker change detection
  - [x] Add available VFX library metadata (tags, paths, durations)
  - [x] Specify JSON output format for VFX matches

- [x] **Task 5:** Add JSON-RPC handler (AC: #4)
  - [x] Create `match_vfx()` handler in `protocols/handlers/ai.py`
  - [x] Create `match_vfx_with_progress()` streaming handler
  - [x] Add request validation (requirements, VFX index, format rules)
  - [x] Return structured VFX suggestions with placement data
  - [x] Register in `AI_HANDLERS`

- [x] **Task 6:** Handle edge cases and errors (AC: #2, #4, #5)
  - [x] Implement empty VFX library handling
  - [x] Add no-match scenarios with fallback suggestions
  - [x] Create placement conflict resolution (overlapping templates)
  - [x] Handle missing template metadata gracefully
  - [x] Add template asset group validation

## Dev Notes

### Architecture Context

This story extends the AI matching system from Stories 5.4 (Music) and 5.5 (SFX) to handle VFX and template assets. Unlike audio assets, VFX templates have visual timing constraints and placement requirements that must align with video segments.

**Key Components to Create/Touch:**
- `src/roughcut/backend/ai/vfx_matcher.py` - **NEW** VFX matching logic
- `src/roughcut/backend/ai/vfx_match.py` - **NEW** VFX match data structures
- `src/roughcut/backend/ai/vfx_requirement.py` - **NEW** VFX requirement identification structures
- `src/roughcut/backend/ai/prompt_templates/match_vfx_system.txt` - **NEW** AI prompt template
- `src/roughcut/protocols/handlers/ai.py` - **EXTEND** Add match_vfx handler
- `src/roughcut/backend/ai/rough_cut_orchestrator.py` - **MODIFY** Integrate VFX matching into workflow

**Communication Protocol:**
All Lua ↔ Python communication uses JSON-RPC over stdin/stdout:

```json
// Request (Lua → Python)
{
  "method": "match_vfx",
  "params": {
    "session_id": "session_123",
    "segments": [
      {
        "section_name": "intro",
        "start_time": 0.0,
        "end_time": 14.8,
        "text": "Welcome to our corporate overview...",
        "speaker": "CEO",
        "speaker_change": false
      },
      {
        "section_name": "narrative_1",
        "start_time": 120.5,
        "end_time": 215.3,
        "text": "Let me introduce our team...",
        "speaker": "CEO",
        "speaker_change": false
      }
    ],
    "format_template": {
      "name": "YouTube Interview - Corporate",
      "vfx_requirements": [
        {"type": "lower_third", "at": "speaker_intro", "duration": 3.0},
        {"type": "outro_cta", "at": "section_end", "duration": 5.0}
      ],
      "template_asset_groups": {
        "intro_graphics": ["corporate_logo_anim", "title_fade"],
        "lower_thirds": ["standard_lower_third", "corporate_nameplate"]
      }
    },
    "vfx_index": [
      {
        "id": "vfx_001",
        "file_path": "/assets/vfx/LowerThirds/Corporate/standard_lower_third.drp",
        "tags": ["lower_third", "corporate", "nameplate", "speaker"],
        "category": "vfx",
        "folder_context": "LowerThirds/Corporate",
        "duration_ms": 3000,
        "template_type": "fusion_composition"
      },
      {
        "id": "vfx_042",
        "file_path": "/assets/vfx/Outro/CTA/corporate_outro_cta.drp",
        "tags": ["outro", "cta", "corporate", "ending"],
        "category": "vfx",
        "folder_context": "Outro/CTA",
        "duration_ms": 5000,
        "template_type": "fusion_composition"
      }
    ],
    "max_suggestions_per_requirement": 3
  },
  "id": "req_vfx_001"
}

// Progress Update (Python → Lua)
{
  "type": "progress",
  "operation": "match_vfx",
  "current": 2,
  "total": 4,
  "message": "Matching lower third templates..."
}

// Response (Python → Lua)
{
  "result": {
    "requirement_matches": [
      {
        "requirement": {
          "timestamp": 120.5,
          "type": "lower_third",
          "context": "speaker introduction - CEO",
          "duration": 3.0,
          "format_section": "narrative_1"
        },
        "matches": [
          {
            "vfx_id": "vfx_001",
            "file_path": "/assets/vfx/LowerThirds/Corporate/standard_lower_third.drp",
            "file_name": "standard_lower_third.drp",
            "folder_context": "LowerThirds/Corporate",
            "match_reason": "Tags 'lower_third' + 'corporate' match requirement; in predefined asset group",
            "confidence_score": 0.92,
            "matched_tags": ["lower_third", "corporate", "speaker"],
            "template_type": "fusion_composition",
            "placement": {
              "start_time": 120.5,
              "end_time": 123.5,
              "duration_ms": 3000
            },
            "from_template_group": true,
            "group_name": "lower_thirds"
          }
        ]
      },
      {
        "requirement": {
          "timestamp": 210.3,
          "type": "outro_cta",
          "context": "section ending - call to action",
          "duration": 5.0,
          "format_section": "narrative_1"
        },
        "matches": [
          {
            "vfx_id": "vfx_042",
            "file_path": "/assets/vfx/Outro/CTA/corporate_outro_cta.drp",
            "file_name": "corporate_outro_cta.drp",
            "folder_context": "Outro/CTA",
            "match_reason": "Tags 'outro' + 'cta' + 'corporate' match requirement type",
            "confidence_score": 0.89,
            "matched_tags": ["outro", "cta", "corporate"],
            "template_type": "fusion_composition",
            "placement": {
              "start_time": 210.3,
              "end_time": 215.3,
              "duration_ms": 5000
            },
            "from_template_group": false,
            "group_name": null
          }
        ]
      }
    ],
    "total_matches": 3,
    "average_confidence": 0.88,
    "fallback_used": false,
    "placement_conflicts": [],
    "template_group_coverage": 0.67
  },
  "error": null,
  "id": "req_vfx_001"
}
```

### Technical Requirements

**Naming Conventions:**
- Python: `snake_case` functions/variables (e.g., `match_vfx_to_requirements()`, `confidence_score`)
- Classes: `PascalCase` (e.g., `VFXMatcher`, `VFXMatch`, `VFXRequirement`)
- JSON fields: `snake_case` (e.g., `"match_reason"`, `"template_type"`)

**Data Structures:**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class VFXRequirement:
    """A VFX requirement identified from format template."""
    timestamp: float  # Position in seconds
    type: str  # "lower_third", "transition", "title_card", "outro_cta", "logo_anim"
    context: str  # Description (e.g., "speaker introduction", "section transition")
    duration: float  # Required duration in seconds
    format_section: str  # Which format section this belongs to
    speaker_name: Optional[str] = None  # For lower thirds
    
    def to_tag_query(self) -> list[str]:
        """Convert requirement type to tag search terms."""
        pass

@dataclass
class VFXPlacement:
    """Calculated placement for a VFX template on timeline."""
    start_time: float
    end_time: float
    duration_ms: int
    
    def overlaps_with(self, other: VFXPlacement) -> bool:
        """Check if this placement overlaps with another."""
        pass

@dataclass
class VFXMatch:
    """A VFX/template asset matched to a requirement."""
    vfx_id: str
    file_path: str
    file_name: str
    folder_context: str
    match_reason: str
    confidence_score: float  # 0.0 to 1.0
    matched_tags: list[str]
    template_type: str  # "fusion_composition", "generator", "transition"
    placement: VFXPlacement
    from_template_group: bool  # True if from predefined asset group
    group_name: Optional[str]  # Name of template asset group if applicable
    
    def is_high_confidence(self) -> bool:
        """Returns True if confidence >= 0.85"""
        return self.confidence_score >= 0.85

@dataclass
class RequirementVFXMatches:
    """All VFX matches for a single requirement."""
    requirement: VFXRequirement
    matches: list[VFXMatch]
    fallback_suggestion: Optional[VFXMatch]  # If no good matches
    
    def top_match(self) -> Optional[VFXMatch]:
        """Return highest confidence match."""
        pass

@dataclass
class VFXMatchingResult:
    """Result of AI VFX matching operation."""
    requirement_matches: list[RequirementVFXMatches]
    total_matches: int
    average_confidence: float
    fallback_used: bool  # True if any requirement used fallback
    placement_conflicts: list[dict]  # Overlapping placements detected
    template_group_coverage: float  # % of matches from predefined groups
    warnings: list[str]
```

**VFX Requirement Type to Tag Mapping:**

```python
VFX_REQUIREMENT_MAPPINGS = {
    "lower_third": ["lower_third", "nameplate", "speaker", "title", "corporate"],
    "transition": ["transition", "wipe", "fade", "dissolve", "cut"],
    "title_card": ["title", "card", "intro", "opening", "header"],
    "outro_cta": ["outro", "cta", "ending", "close", "call_to_action"],
    "logo_anim": ["logo", "brand", "anim", "animation", "intro"],
    "broll_placeholder": ["placeholder", "broll", "b_roll", "cutaway"],
}

# Template type preferences by requirement
REQUIREMENT_TYPE_PREFERENCES = {
    "lower_third": ["fusion_composition", "generator"],
    "transition": ["transition", "fusion_composition"],
    "title_card": ["fusion_composition", "generator"],
    "outro_cta": ["fusion_composition"],
    "logo_anim": ["fusion_composition"],
}
```

**AI Prompt Design:**
The system prompt must guide VFX requirement identification and template matching:

```
You are an expert video editor AI tasked with matching VFX templates to format requirements.

CRITICAL RULES:
1. Parse format template VFX specifications (lower_thirds, transitions, outro_cta, etc.)
2. Identify speaker changes and introduction moments for lower third placement
3. Match VFX tags to requirement context (e.g., "lower_third" + "corporate" for speaker intros)
4. Respect template durations - never suggest templates that exceed required duration
5. Prioritize templates from predefined asset groups when available
6. Calculate precise timestamps aligning with transcript segment boundaries

Your task:
- Analyze format template VFX requirements
- Review transcript segments for speaker changes and key moments
- Match requirements to available VFX library using tag similarity
- Return top 3 matches per requirement with confidence scores
- Include placement timing and match reasoning

Output format:
{
  "requirement_matches": [
    {
      "requirement": {
        "timestamp": <float>,
        "type": "lower_third|transition|title_card|outro_cta|logo_anim",
        "context": "<why this VFX is needed>",
        "duration": <float>,
        "format_section": "<section name>"
      },
      "matches": [
        {
          "vfx_id": "...",
          "confidence_score": 0.92,
          "match_reason": "...",
          "matched_tags": ["..."],
          "template_type": "fusion_composition|generator|transition",
          "placement": {
            "start_time": <float>,
            "end_time": <float>,
            "duration_ms": <int>
          },
          "from_template_group": true|false
        }
      ]
    }
  ],
  "fallback_used": false,
  "placement_conflicts": []
}
```

**Error Handling:**
Use structured error objects at protocol boundary:

```json
{
  "result": null,
  "error": {
    "code": "NO_VFX_MATCHES",
    "category": "ai_matching",
    "message": "No VFX assets matched requirement criteria",
    "recoverable": true,
    "suggestion": "Check VFX library tags or add more templates"
  },
  "id": "req_vfx_001"
}
```

**Error Codes:**
- `EMPTY_VFX_LIBRARY` - No VFX assets indexed
- `NO_VFX_MATCHES` - No matches found for requirement criteria
- `PLACEMENT_CONFLICTS` - Overlapping template placements detected
- `DURATION_MISMATCH` - Template duration doesn't fit requirement
- `AI_TIMEOUT` - AI processing exceeded 30 seconds (NFR3)
- `INVALID_REQUIREMENT_DATA` - Missing or malformed requirement input
- `NO_REQUIREMENTS_IDENTIFIED` - AI found no VFX requirements in format

**Performance Requirements:**
- Processing time: Within AI service timeout (30s per NFR3)
- Database query: <500ms for VFX asset retrieval
- Retry logic: 3 attempts with exponential backoff (reuse 5.2-5.5 pattern)
- Progress updates: Every major processing step

### Data Flow

1. **From Story 5.3 (Transcript Cutting):**
   - Transcript segments with timestamps and text
   - Segment structure and format compliance data
   - Speaker labels and change detection

2. **From Story 5.4 (Music Matching):**
   - Segment tone analysis (energy, mood descriptors)
   - Music matches already determined for segments

3. **From Story 5.5 (SFX Matching):**
   - SFX moments and matches already determined
   - Audio layer planning information

4. **This Story (5.6):**
   - Parse format template VFX requirements
   - Identify speaker introduction moments for lower thirds
   - Query VFX library for matching templates
   - Calculate precise placement timestamps
   - Detect and resolve placement conflicts
   - Return structured VFX suggestions with placement data

5. **To Next Stories (5.7, 5.8):**
   - VFX matches feed into rough cut document (5.8)
   - Used for timeline VFX track placement (Epic 6)

### Previous Story Intelligence

**Story 5.5 Learnings (AI SFX Matching):**
- `SFXMatcher` class with moment identification and tag matching patterns
- `SFXMatch` dataclass with confidence scoring and subtlety assessment
- `SFXMoment` dataclass for identifying key moments in content
- `TONE_TAG_MAPPINGS` dictionary for mapping contexts to tag queries
- Generator-based progress streaming with `*_with_progress()` functions
- `PromptBuilder` extension pattern for new prompt templates
- JSON-RPC handler registration in `AI_HANDLERS`
- Duplicate match prevention with `prevent_duplicate_matches()`
- Usage history tracking with `_apply_usage_penalty()`
- Error codes as module-level constants with structured error objects
- Duration-based scoring (shorter sounds preferred for subtlety)
- Folder context matching for additional relevance signals

**Story 5.4 Learnings (AI Music Matching):**
- `MusicMatcher` class with tone analysis and tag matching
- `SegmentTone` dataclass for emotional analysis per segment
- Tag-based matching with weighted relevance scoring
- Confidence thresholds: HIGH (>=0.80), MEDIUM (0.60-0.80), LOW (<0.60)
- Pattern for checking thematic consistency across matches

**Established Patterns:**
- Use dataclasses with type hints for all data structures
- Include `from __future__ import annotations` for forward compatibility
- Generator-based progress streaming for long operations
- Comprehensive input validation with early returns
- Use `list[dict]` Python 3.10+ syntax (not `List[Dict]`)
- Move imports to module level (not inside functions)
- Extract hardcoded magic numbers to named constants
- Use `.casefold()` instead of `.lower()` for Unicode safety
- Handler registration in central `AI_HANDLERS` registry
- Tag-based matching with exact > partial > related scoring tiers

**VFX-Specific Adaptations from SFX/Music Patterns:**
- VFX templates have duration constraints (unlike audio loops)
- Visual placement must avoid overlap (unlike layered audio)
- Template asset groups take priority (format-defined presets)
- Speaker change detection needed for lower thirds
- Fusion composition vs generator vs transition type distinctions

### Integration Points

**Inputs From Story 5.3:**
- `TranscriptSegment` objects with text, timestamps, speaker labels
- Format template section structure

**Inputs From Story 5.4:**
- Segment tone analysis (energy, mood descriptors)
- Established patterns for tag-based matching

**Inputs From Story 5.5:**
- SFX moments already identified (avoid visual/audio conflict)
- Patterns for moment identification and matching

**Inputs From SpacetimeDB:**
- VFX/template asset index with tags and metadata
- Asset duration information (critical for placement)
- Query via `spacetime_client.py`

**Inputs From Format Template:**
- VFX requirements specification
- Template asset group definitions
- Timing rules for placement alignment

**Outputs To Stories 5.7, 5.8:**
- `VFXMatch` objects per requirement
- Placement timing data for timeline
- Match reasoning for review document
- Template group coverage statistics
- Confidence scores for quality assessment

**Files to Create:**
```
src/roughcut/
├── backend/
│   └── ai/
│       ├── vfx_matcher.py              # VFXMatcher class
│       ├── vfx_match.py                # VFXMatch, VFXPlacement dataclasses
│       ├── vfx_requirement.py          # VFXRequirement dataclass
│       └── prompt_templates/
│           └── match_vfx_system.txt      # AI prompt template
```

**Files to Extend:**
```
src/roughcut/
├── backend/
│   └── ai/
│       ├── prompt_engine.py           # Add build_vfx_matching_prompt()
│       └── rough_cut_orchestrator.py    # Integrate VFX matching step
└── protocols/
    └── handlers/
        └── ai.py                      # Add match_vfx handlers
```

### Testing Requirements

**Unit Tests:**
- Test `VFXMatcher` requirement identification (`tests/unit/backend/ai/test_vfx_matcher.py`)
- Test tag scoring algorithm for VFX categories
- Test placement calculation and overlap detection
- Test confidence calculation with template group priority
- Test fallback suggestion logic
- Test placement conflict resolution
- Test speaker change detection for lower thirds

**Integration Tests:**
- Test end-to-end VFX matching with mock AI response
- Test SpacetimeDB query integration for VFX assets
- Test error scenarios: empty library, no matches, placement conflicts
- Test progress streaming for long operations
- Test template asset group priority matching

**Test Fixtures:**
- Sample transcript segments with speaker labels and changes
- Mock VFX library with diverse tags (lower thirds, transitions, titles)
- Format templates with VFX requirements and asset groups
- AI response JSON samples (valid, no requirements, placement conflicts)

### References

- **Epic Context:** [Source: _bmad-output/planning-artifacts/epics.md#Story 5.6: AI VFX/Template Matching]
- **Architecture - AI Layer:** [Source: _bmad-output/planning-artifacts/architecture.md#Core Architectural Decisions]
- **Architecture - Database Layer:** [Source: _bmad-output/planning-artifacts/architecture.md#Database & Persistence Layer]
- **Architecture - Naming Conventions:** [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns]
- **PRD - FR24:** [Source: _bmad-output/planning-artifacts/prd.md#AI-Powered Rough Cut Generation]
- **PRD - NFR3 (Timeout):** [Source: _bmad-output/planning-artifacts/prd.md#Performance]
- **Previous Story (5.5):** [Source: _bmad-output/implementation-artifacts/5-5-ai-sfx-matching.md]
- **Previous Story (5.4):** [Source: _bmad-output/implementation-artifacts/5-4-ai-music-matching.md]

## Dev Agent Record

### Agent Model Used

accounts/fireworks/routers/kimi-k2p5-turbo (fireworks-ai/accounts/fireworks/routers/kimi-k2p5-turbo)

### Debug Log References

(No critical issues encountered during implementation)

### Completion Notes List

**Implementation Complete - Story 5.6: AI VFX/Template Matching**

**Task 1 - VFX Requirement Identification System (COMPLETED):**
- Created `VFXRequirement` dataclass in `backend/ai/vfx_requirement.py` with timestamp, type, context, duration, format_section, speaker_name fields
- Created `VFXRequirementList` dataclass for managing collections of requirements with conflict detection
- Defined `VFX_REQUIREMENT_MAPPINGS` dictionary mapping requirement types to relevant tags
- Defined `REQUIREMENT_TYPE_PREFERENCES` for template type preferences per requirement type
- Defined `DEFAULT_DURATION_REQUIREMENTS` for default duration requirements per VFX type
- Implemented `identify_vfx_requirements()` in `VFXMatcher` class with format template parsing
- Implemented speaker change detection for automatic lower third requirements
- Implemented timestamp resolution from "at" specifications (segment_start, segment_end, etc.)

**Task 2 - VFX Template Matching Engine (COMPLETED):**
- Created `VFXMatcher` class in `backend/ai/vfx_matcher.py` with comprehensive matching logic
- Implemented `match_vfx_to_requirements()` method with template asset group prioritization
- Created tag scoring algorithm with exact match, partial match, and folder context bonuses
- Implemented `_calculate_match_score()` with weighted tag relevance scoring
- Added template type preference matching with type compatibility scoring
- Implemented `_get_group_asset_ids()` and `_asset_in_group_by_name()` for group membership detection
- Added confidence score calculation with multiple tag bonus and group membership bonus

**Task 3 - Placement Calculation & Timing (COMPLETED):**
- Created `VFXPlacement` dataclass with start_time, end_time, duration_ms fields
- Implemented `overlaps_with()` method with configurable tolerance for conflict detection
- Implemented `get_overlap_duration()` for calculating exact overlap duration
- Created `calculate_placement()` method in `VFXMatcher` for timestamp alignment
- Implemented `_detect_placement_conflicts()` for detecting overlapping VFX placements
- Implemented `resolve_placement_conflicts()` for automatic conflict resolution
- Added format timing rule compliance through requirement timestamp alignment

**Task 4 - AI Prompt for VFX Matching (COMPLETED):**
- Created `match_vfx_system.txt` in `backend/ai/prompt_templates/` with comprehensive guidelines
- Prompt includes: VFX requirement type taxonomy, template asset group guidelines, placement constraints
- Added match scoring guidelines with confidence score ranges
- Added output format specification with JSON structure for requirement_matches
- Extended `PromptBuilder` class with `build_vfx_matching_prompt()` method
- Added `_get_default_vfx_matching_prompt()` for fallback prompt template

**Task 5 - JSON-RPC Handler (COMPLETED):**
- Created `match_vfx()` handler in `protocols/handlers/ai.py` with full request validation
- Created `match_vfx_with_progress()` streaming generator handler with 5 progress stages:
  1. Initializing VFX matcher
  2. Analyzing segments for VFX requirements
  3. Matching VFX to requirements
  4. Detecting and resolving placement conflicts
  5. VFX matching complete
- Added request validation for session_id, segments, format_template, vfx_index
- Added error codes: EMPTY_VFX_LIBRARY, NO_VFX_MATCHES, NO_REQUIREMENTS_IDENTIFIED, PLACEMENT_CONFLICTS
- Registered both handlers in `AI_HANDLERS` registry

**Task 6 - Edge Cases & Error Handling (COMPLETED):**
- Implemented empty VFX library handling with structured error responses
- Added no-match scenarios with fallback suggestion generation
- Created placement conflict detection and resolution algorithms
- Implemented graceful handling of missing template metadata in dataclass from_dict methods
- Added template asset group validation with fallback to general library
- Added comprehensive input validation with early returns and clear error messages
- Implemented overlap detection with configurable tolerance
- Added warning generation for low-confidence matches

**Key Technical Decisions:**
- Used dataclasses with `__post_init__` validation for all data structures
- Implemented template asset group priority with 15% confidence bonus
- Used duration-based placement calculation respecting both requirement and asset durations
- Implemented placement conflict resolution preferring higher confidence or template group matches
- Added speaker change detection for automatic lower third requirement generation
- Followed established patterns from SFX/Music matching for consistency

**Error Codes Added:**
- EMPTY_VFX_LIBRARY - No VFX assets indexed
- NO_VFX_MATCHES - No matches found for requirement criteria
- NO_REQUIREMENTS_IDENTIFIED - No VFX requirements found in format template
- PLACEMENT_CONFLICTS - Overlapping template placements detected

**Code Review Fixes Applied (2026-04-04):**

After parallel adversarial code review (Blind Hunter, Edge Case Hunter, Acceptance Auditor), the following critical fixes were applied:

**Fix 1: Conflict Resolution Consistency [HIGH]**
- **Issue:** `match_vfx()` handler detected but didn't resolve placement conflicts, while `match_vfx_with_progress()` did
- **Impact:** API inconsistency - different results from sync vs async endpoints
- **Fix:** Added `result = matcher.resolve_placement_conflicts(result)` to `match_vfx()` handler
- **Location:** `protocols/handlers/ai.py` line ~1770

**Fix 2: VFXAsset Tags Validation Order [MEDIUM]**
- **Issue:** `isinstance(tags, list)` check happened before `None` check, causing false positives
- **Impact:** Valid assets with `tags: null` rejected instead of defaulting to empty list
- **Fix:** Reordered validation: check `None` first, then `isinstance`
- **Location:** `vfx_match.py` lines 169-172

**Fix 3: Segment Field Type Validation [MEDIUM]**
- **Issue:** Segment dictionary fields accessed without type validation
- **Impact:** String timestamps could cause errors downstream
- **Fix:** Added comprehensive type checking for segment dict fields
- **Location:** `vfx_matcher.py` identify_vfx_requirements() method

**Fix 4: Negative Timestamp From Relative Offsets [MEDIUM]**
- **Issue:** Relative offset like "-100" could create negative timestamps
- **Impact:** VFXPlacement validation would fail downstream
- **Fix:** Added validation to clamp negative results to 0.0 with warning log
- **Location:** `vfx_matcher.py` _resolve_timestamp() method

**New Unit Tests Added:**
- `test_identify_vfx_requirements_invalid_segment_type`
- `test_identify_vfx_requirements_invalid_timestamp_types`
- `test_identify_vfx_requirements_negative_start_time`
- `test_identify_vfx_requirements_inverted_timestamps`
- `test_resolve_timestamp_negative_offset_clamped`
- `test_vfx_asset_tags_none_handled`

**Files Created:**
1. `roughcut/src/roughcut/backend/ai/vfx_requirement.py` - VFXRequirement, VFXRequirementList dataclasses
2. `roughcut/src/roughcut/backend/ai/vfx_match.py` - VFXAsset, VFXMatch, VFXPlacement, VFXMatchingResult dataclasses
3. `roughcut/src/roughcut/backend/ai/vfx_matcher.py` - VFXMatcher class with comprehensive matching logic
4. `roughcut/src/roughcut/backend/ai/prompt_templates/match_vfx_system.txt` - AI prompt template
5. `roughcut/tests/unit/backend/ai/test_vfx_matcher.py` - Comprehensive unit tests

**Files Modified:**
1. `roughcut/src/roughcut/backend/ai/prompt_engine.py` - Added `build_vfx_matching_prompt()` and `_get_default_vfx_matching_prompt()`
2. `roughcut/src/roughcut/protocols/handlers/ai.py` - Added `match_vfx` and `match_vfx_with_progress` handlers, added VFX error codes

### File List

**New Files:**
- `roughcut/src/roughcut/backend/ai/vfx_requirement.py`
- `roughcut/src/roughcut/backend/ai/vfx_match.py`
- `roughcut/src/roughcut/backend/ai/vfx_matcher.py`
- `roughcut/src/roughcut/backend/ai/prompt_templates/match_vfx_system.txt`
- `roughcut/tests/unit/backend/ai/test_vfx_matcher.py`

**Modified Files:**
- `roughcut/src/roughcut/backend/ai/prompt_engine.py`
- `roughcut/src/roughcut/protocols/handlers/ai.py`

## Project Context Reference

- **Project:** RoughCut - AI-powered DaVinci Resolve plugin
- **Epic:** 5 - AI-Powered Rough Cut Generation
- **Story:** 5.6 - AI VFX/Template Matching
- **Prerequisites:** Stories 5.3 (Transcript Cutting), 5.4 (Music Matching), 5.5 (SFX Matching) complete
- **Next Story:** 5.7 - Chunked Context Processing

**Related Documents:**
- PRD: `_bmad-output/planning-artifacts/prd.md`
- Architecture: `_bmad-output/planning-artifacts/architecture.md`
- Epics: `_bmad-output/planning-artifacts/epics.md`
- Previous Story 5.5: `_bmad-output/implementation-artifacts/5-5-ai-sfx-matching.md`
- Previous Story 5.4: `_bmad-output/implementation-artifacts/5-4-ai-music-matching.md`

---

**Story created:** 2026-04-04
**Status:** ready-for-dev
**Ultimate context engine analysis completed - comprehensive developer guide created**

## Change Log

### 2026-04-04 - Story Created
- Initial story context created with comprehensive developer guidance
- Based on learnings from Stories 5.3, 5.4, and 5.5 implementation
- References architecture decisions on AI layer, database layer, and JSON-RPC protocol
- Emphasizes VFX requirement identification and template placement calculation
- Includes VFX-specific requirement type taxonomy (lower_third, transition, title_card, outro_cta, logo_anim)
- Addresses template asset group priority and placement conflict resolution
- Extends patterns from SFX/Music matching with VFX-specific adaptations (duration constraints, overlap detection)

### 2026-04-04 - Code Review Fixes Applied
- **Fix 1:** Added conflict resolution to `match_vfx()` handler (was only in `match_vfx_with_progress()`)
- **Fix 2:** Fixed VFXAsset tags validation order - None check before isinstance check
- **Fix 3:** Added comprehensive segment field validation (type checking for timestamps)
- **Fix 4:** Added start_time < end_time validation for segments
- **Fix 5:** Added non-negative timestamp validation for relative offsets (clamps to 0.0)
- **Fix 6:** Added 6 new unit tests for validation edge cases
- **Status:** review → done
- Created vfx_requirement.py with VFXRequirement, VFXRequirementList, VFX_REQUIREMENT_MAPPINGS
- Created vfx_match.py with VFXAsset, VFXMatch, VFXPlacement, VFXMatchingResult dataclasses
- Created vfx_matcher.py with VFXMatcher class and comprehensive matching logic
- Created AI prompt template for VFX matching with template asset group guidelines
- Extended PromptBuilder with build_vfx_matching_prompt() method
- Added match_vfx and match_vfx_with_progress handlers to protocols/handlers/ai.py
- Implemented placement calculation with overlap detection and conflict resolution
- Added template asset group priority matching with bonus scoring
- Created comprehensive unit tests covering all functionality
- Story marked ready for code review (status: review)
