# Story 5.5: AI SFX Matching

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a video editor,
I want the AI to match SFX assets to appropriate moments in the transcript,
So that sound effects add emotional emphasis without disrupting the flow.

## Acceptance Criteria

1. **SFX Moment Identification** (AC: #1)
   - **Given** the AI has cut transcript segments
   - **When** it analyzes for emotional beats and transitions
   - **Then** it identifies moments suitable for SFX (e.g., intro whoosh, pivot emphasis, outro chime)
   - **And** moments are mapped to specific timestamps within segments

2. **SFX Context Matching** (AC: #2)
   - **Given** an emotional pivot in the transcript
   - **When** AI determines SFX is appropriate
   - **Then** it searches SFX library for matching context (e.g., "success", "transition", "underscore")
   - **And** matches consider both AI-generated tags and folder path context

3. **Subtle SFX Selection** (AC: #3)
   - **Given** multiple SFX options exist
   - **When** AI makes selection
   - **Then** it suggests subtle, non-distracting sounds that enhance without overwhelming
   - **And** returns top 3 matches with confidence scores

4. **SFX Presentation with Layer Guidance** (AC: #4)
   - **Given** SFX are matched to moments
   - **When** suggestions are presented
   - **Then** editor sees: "SFX: gentle_whoosh (0:00), underscore_tone (2:30), outro_chime (3:45)"
   - **And** layer information shows: "Place on separate track for volume flexibility"
   - **And** each suggestion includes: file path, match reason, confidence score

5. **Editor Override Support** (AC: #5)
   - **Given** a suggested SFX might not fit the emotional context
   - **When** the editor reviews
   - **Then** they can easily note: "SFX: tension_sound suggested at pivot, but story is about triumph — swap to success_sound"
   - **And** the rough cut document indicates which suggestions are high-confidence vs. review-recommended

## Tasks / Subtasks

- [x] **Task 1:** Create SFX moment identification system (AC: #1)
  - [x] Create `SFXMatcher` class in `backend/ai/sfx_matcher.py`
  - [x] Implement `identify_sfx_moments()` method
  - [x] Create moment type taxonomy (intro, transition, emphasis, outro, etc.)
  - [x] Define `SFXMoment` dataclass (timestamp, type, context, intensity)
  - [x] Add moment detection from transcript text and segment boundaries

- [x] **Task 2:** Build SFX asset matching engine (AC: #2, #3)
  - [x] Implement `match_sfx_to_moments()` method
  - [x] Create tag scoring algorithm with weights for SFX categories
  - [x] Query SpacetimeDB for SFX assets by tags
  - [x] Add folder path context matching (e.g., "Transitions", "Impacts", "Ambience")
  - [x] Implement subtlety scoring (prefer shorter, less jarring sounds)

- [x] **Task 3:** Implement match scoring & ranking (AC: #3)
  - [x] Create `SFXMatch` dataclass with confidence scoring
  - [x] Implement tag relevance scoring (exact > partial > related)
  - [x] Add subtlety indicators (duration, intensity level)
  - [x] Create usage history tracking (optional preference)
  - [x] Return top N matches sorted by score

- [x] **Task 4:** Create AI prompt for SFX matching (AC: #1, #2)
  - [x] Create `match_sfx_system.txt` prompt template in `backend/ai/prompt_templates/`
  - [x] Include transcript segments with moment analysis
  - [x] Add available SFX library metadata (tags, paths)
  - [x] Specify JSON output format for SFX matches
  - [x] Define subtlety and non-distracting requirements

- [x] **Task 5:** Add JSON-RPC handler (AC: #4)
  - [x] Create `match_sfx()` handler in `protocols/handlers/ai.py`
  - [x] Create `match_sfx_with_progress()` streaming handler
  - [x] Add request validation (segments, SFX index)
  - [x] Return structured SFX suggestions with layer guidance
  - [x] Register in `AI_HANDLERS`

- [x] **Task 6:** Handle edge cases and errors (AC: #3, #4, #5)
  - [x] Implement empty SFX library handling
  - [x] Add no-match scenarios with fallback suggestions
  - [x] Create low-confidence match warnings with review recommendations
  - [x] Add duplicate SFX prevention across moments
  - [x] Handle missing metadata gracefully

## Dev Notes

### Architecture Context

This story builds on Story 5.4's music matching to suggest appropriate sound effects at key moments. The SFX matcher must identify emotional beats and transitions that need audio emphasis, then match subtle, non-distracting sounds from the indexed library.

**Key Components to Create/Touch:**
- `src/roughcut/backend/ai/sfx_matcher.py` - **NEW** SFX matching logic
- `src/roughcut/backend/ai/sfx_match.py` - **NEW** SFX match data structures
- `src/roughcut/backend/ai/sfx_moment.py` - **NEW** SFX moment identification structures
- `src/roughcut/backend/ai/prompt_templates/match_sfx_system.txt` - **NEW** AI prompt template
- `src/roughcut/protocols/handlers/ai.py` - **EXTEND** Add match_sfx handler
- `src/roughcut/backend/ai/rough_cut_orchestrator.py` - **MODIFY** Integrate SFX matching into workflow

**Communication Protocol:**
All Lua ↔ Python communication uses JSON-RPC over stdin/stdout:

```json
// Request (Lua → Python)
{
  "method": "match_sfx",
  "params": {
    "session_id": "session_123",
    "segments": [
      {
        "section_name": "intro",
        "start_time": 0.0,
        "end_time": 14.8,
        "text": "Welcome to our corporate overview...",
        "tone": {"energy": "high", "mood": "upbeat"}
      },
      {
        "section_name": "narrative_1",
        "start_time": 120.5,
        "end_time": 215.3,
        "text": "The challenges we faced were significant, but we persevered...",
        "tone": {"energy": "medium", "mood": "triumphant"}
      }
    ],
    "sfx_index": [
      {
        "id": "sfx_001",
        "file_path": "/assets/sfx/Transitions/Whoosh/gentle_whoosh.wav",
        "tags": ["transition", "whoosh", "gentle", "intro"],
        "category": "sfx",
        "folder_context": "Transitions/Whoosh",
        "duration_ms": 1500
      },
      {
        "id": "sfx_042",
        "file_path": "/assets/sfx/Impacts/Success/success_chime.wav",
        "tags": ["success", "chime", "impact", "triumphant"],
        "category": "sfx",
        "folder_context": "Impacts/Success",
        "duration_ms": 800
      }
    ],
    "max_suggestions_per_moment": 3
  },
  "id": "req_sfx_001"
}

// Progress Update (Python → Lua)
{
  "type": "progress",
  "operation": "match_sfx",
  "current": 2,
  "total": 5,
  "message": "Matching SFX for transition moments..."
}

// Response (Python → Lua)
{
  "result": {
    "moment_matches": [
      {
        "moment": {
          "timestamp": 0.0,
          "type": "intro",
          "context": "opening transition",
          "intensity": "medium"
        },
        "matches": [
          {
            "sfx_id": "sfx_001",
            "file_path": "/assets/sfx/Transitions/Whoosh/gentle_whoosh.wav",
            "file_name": "gentle_whoosh.wav",
            "folder_context": "Transitions/Whoosh",
            "match_reason": "Tags 'transition' + 'intro' match moment type; duration 1.5s suitable for intro",
            "confidence_score": 0.88,
            "matched_tags": ["transition", "intro"],
            "suggested_at": 0.0,
            "duration_ms": 1500,
            "subtlety_score": 0.85
          }
        ]
      },
      {
        "moment": {
          "timestamp": 165.0,
          "type": "emphasis",
          "context": "pivot moment - triumph over challenges",
          "intensity": "medium"
        },
        "matches": [
          {
            "sfx_id": "sfx_042",
            "file_path": "/assets/sfx/Impacts/Success/success_chime.wav",
            "file_name": "success_chime.wav",
            "folder_context": "Impacts/Success",
            "match_reason": "Tags 'success' + 'triumphant' match pivot context; subtle impact suitable",
            "confidence_score": 0.91,
            "matched_tags": ["success", "triumphant"],
            "suggested_at": 165.0,
            "duration_ms": 800,
            "subtlety_score": 0.90
          }
        ]
      }
    ],
    "total_matches": 4,
    "average_confidence": 0.87,
    "fallback_used": false,
    "layer_guidance": "Place each SFX on separate track for volume flexibility"
  },
  "error": null,
  "id": "req_sfx_001"
}
```

### Technical Requirements

**Naming Conventions:**
- Python: `snake_case` functions/variables (e.g., `match_sfx_to_moments()`, `confidence_score`)
- Classes: `PascalCase` (e.g., `SFXMatcher`, `SFXMatch`, `SFXMoment`)
- JSON fields: `snake_case` (e.g., `"match_reason"`, `"confidence_score"`)

**Data Structures:**

```python
@dataclass
class SFXMoment:
    """A moment in the transcript suitable for SFX placement."""
    timestamp: float  # Position in seconds
    type: str  # "intro", "transition", "emphasis", "outro", "underscore"
    context: str  # Description of why SFX fits (emotional beat, transition point)
    intensity: str  # "low", "medium", "high" - indicates subtlety needed
    segment_name: str  # Which transcript segment this moment belongs to
    
    def to_tag_query(self) -> list[str]:
        """Convert moment type to tag search terms."""
        pass

@dataclass
class SFXMatch:
    """An SFX asset matched to a moment."""
    sfx_id: str
    file_path: str
    file_name: str
    folder_context: str
    match_reason: str
    confidence_score: float  # 0.0 to 1.0
    matched_tags: list[str]
    suggested_at: float  # Timestamp where SFX should be placed
    duration_ms: int  # Duration in milliseconds for subtlety assessment
    subtlety_score: float  # 0.0 to 1.0 (higher = more subtle)
    
    def is_high_confidence(self) -> bool:
        """Returns True if confidence >= 0.80"""
        return self.confidence_score >= 0.80

@dataclass
class MomentSFXMatches:
    """All SFX matches for a single moment."""
    moment: SFXMoment
    matches: list[SFXMatch]
    fallback_suggestion: Optional[SFXMatch]  # If no good matches
    
    def top_match(self) -> Optional[SFXMatch]:
        """Return highest confidence match."""
        pass

@dataclass
class SFXMatchingResult:
    """Result of AI SFX matching operation."""
    moment_matches: list[MomentSFXMatches]
    total_matches: int
    average_confidence: float
    average_subtlety: float
    fallback_used: bool  # True if any moment used fallback
    layer_guidance: str  # Guidance for timeline placement
    warnings: list[str]
```

**Moment Type to Tag Mapping:**

```python
SFX_MOMENT_MAPPINGS = {
    "intro": ["intro", "whoosh", "transition", "opening", "start"],
    "transition": ["transition", "whoosh", "swoosh", "change", "shift"],
    "emphasis": ["impact", "accent", "hit", "emphasis", "punch"],
    "triumph": ["success", "triumphant", "win", "positive", "celebration"],
    "tension": ["tension", "suspense", "build", "anticipation"],
    "outro": ["outro", "ending", "close", "finish", "chime"],
    "underscore": ["underscore", "bed", "ambient", "background"],
}

# Intensity-based subtlety guidance
INTENSITY_SUBTLETY_PREFERENCE = {
    "low": 0.85,  # Very subtle sounds (ambient, underscore)
    "medium": 0.70,  # Moderate impact (transitions, light emphasis)
    "high": 0.50,  # More prominent (strong impacts, dramatic moments)
}
```

**AI Prompt Design:**
The system prompt must guide moment identification and subtle matching:

```
You are an expert video editor AI tasked with matching sound effects to key moments in video content.

CRITICAL RULES:
1. Identify moments that benefit from SFX: intro, transitions, emotional pivots, outro
2. Match SFX tags to moment context (e.g., "transition" + "whoosh" for intro)
3. PRIORITIZE SUBTLETY - sounds should enhance, not distract from dialogue
4. Consider duration: shorter sounds (<2s) preferred for subtle moments
5. Never suggest harsh or jarring sounds for delicate emotional moments

Your task:
- Analyze transcript segments for emotional beats and transition points
- Identify specific timestamps where SFX would add value
- Match moments to available SFX library using tag similarity
- Return top 3 matches per moment with confidence scores
- Include match reasoning and subtlety assessment

Output format:
{
  "moment_matches": [
    {
      "moment": {
        "timestamp": <float>,
        "type": "intro|transition|emphasis|outro|underscore",
        "context": "<why this moment needs SFX>",
        "intensity": "low|medium|high"
      },
      "matches": [
        {
          "sfx_id": "...",
          "confidence_score": 0.85,
          "match_reason": "...",
          "matched_tags": ["..."],
          "subtlety_score": 0.80
        }
      ]
    }
  ],
  "fallback_used": false
}
```

**Error Handling:**
Use structured error objects at protocol boundary:

```json
{
  "result": null,
  "error": {
    "code": "NO_SFX_MATCHES",
    "category": "ai_matching",
    "message": "No SFX assets matched moment criteria",
    "recoverable": true,
    "suggestion": "Check SFX library tags or add more SFX assets"
  },
  "id": "req_sfx_001"
}
```

**Error Codes:**
- `EMPTY_SFX_LIBRARY` - No SFX assets indexed
- `NO_SFX_MATCHES` - No matches found for moment criteria
- `LOW_CONFIDENCE_MATCHES` - All matches below threshold (0.60)
- `AI_TIMEOUT` - AI processing exceeded 30 seconds (NFR3)
- `INVALID_SEGMENT_DATA` - Missing or malformed segment input
- `NO_MOMENTS_IDENTIFIED` - AI found no suitable SFX moments

**Performance Requirements:**
- Processing time: Within AI service timeout (30s per NFR3)
- Database query: <500ms for SFX asset retrieval
- Retry logic: 3 attempts with exponential backoff (reuse 5.2 pattern)
- Progress updates: Every major processing step

### Data Flow

1. **From Story 5.3 (Transcript Cutting):**
   - Transcript segments with timestamps and text
   - Segment structure and format compliance data

2. **From Story 5.4 (Music Matching):**
   - Segment tone analysis (energy, mood descriptors)
   - Music matches already determined for segments

3. **From SpacetimeDB:**
   - Indexed SFX assets with AI-generated tags
   - Asset metadata (file paths, categories, duration if available)

4. **This Story (5.5):**
   - Analyze segments for SFX-appropriate moments
   - Query SFX library for matching tags
   - Score matches by relevance and subtlety
   - Return structured SFX suggestions with layer guidance

5. **To Next Stories (5.6, 5.8):**
   - SFX matches feed into rough cut document (5.8)
   - Used for timeline SFX placement (Epic 6)

### Previous Story Intelligence

**Story 5.4 Learnings:**
- `MusicMatcher` class with tone analysis and tag matching patterns
- `MusicMatch` dataclass with confidence scoring structure
- `SegmentTone` dataclass for emotional analysis
- `TONE_TAG_MAPPINGS` dictionary for tag queries
- Generator-based progress streaming with `*_with_progress()` functions
- `PromptBuilder` extension pattern for new prompts
- JSON-RPC handler registration in `AI_HANDLERS`
- Duplicate match prevention with `prevent_duplicate_matches()`
- Usage history tracking with `_apply_usage_penalty()`
- Thematic consistency checking with `check_thematic_consistency()`

**Established Patterns:**
- Use dataclasses with type hints for all data structures
- Generator-based progress streaming for long operations
- Comprehensive input validation with early returns
- Error codes as module-level constants
- Handler registration in central `AI_HANDLERS` registry
- Tag-based matching with weighted relevance scoring
- Folder context matching for additional signals
- Confidence thresholds: HIGH (>=0.80), MEDIUM (0.60-0.80), LOW (<0.60)

**Code Review Learnings from 5.4:**
- Add `from __future__ import annotations` for forward compatibility
- Optimize O(n²) operations with set-based detection
- Add comprehensive module-level docstrings to constants
- Standardize type hints to Python 3.10+ syntax (list[dict] vs List[Dict])
- Move imports to module level (not inside functions)
- Extract hardcoded magic numbers to named constants
- Replace `.lower()` with `.casefold()` for Turkish/Unicode safety
- Add usage history tracking with memory management limits
- Add subtlety/intensity scoring for SFX appropriateness
- Implement moment type taxonomy for consistent identification

### Security Requirements

- **NFR7 Compliance:** Only SFX metadata (tags, paths, duration) sent to AI, never file contents
- **Input Validation:** Verify sfx_index entries have required fields (id, path, tags)
- **Path Validation:** Ensure all file paths are absolute and within configured media folders
- **Query Safety:** Use parameterized queries for SpacetimeDB tag searches

### Integration Points

**Inputs From Story 5.3:**
- `TranscriptSegment` objects with text and timestamps
- Format template section structure

**Inputs From Story 5.4:**
- Segment tone analysis (energy, mood descriptors)
- Established patterns for tag-based matching

**Inputs From SpacetimeDB:**
- SFX asset index with tags and metadata
- Query via `spacetime_client.py`

**Outputs To Stories 5.6, 5.8:**
- `SFXMatch` objects per moment
- Match reasoning for review document
- Layer guidance for timeline placement
- Confidence scores for quality assessment

**Files to Create:**
```
src/roughcut/
├── backend/
│   └── ai/
│       ├── sfx_matcher.py              # SFXMatcher class
│       ├── sfx_match.py                # SFXMatch dataclass
│       ├── sfx_moment.py               # SFXMoment dataclass
│       └── prompt_templates/
│           └── match_sfx_system.txt      # AI prompt template
```

**Files to Extend:**
```
src/roughcut/
├── backend/
│   └── ai/
│       ├── prompt_engine.py           # Add build_sfx_matching_prompt()
│       └── rough_cut_orchestrator.py    # Integrate SFX matching step
└── protocols/
    └── handlers/
        └── ai.py                      # Add match_sfx handlers
```

### Testing Requirements

**Unit Tests:**
- Test `SFXMatcher` moment identification (`tests/unit/backend/ai/test_sfx_matcher.py`)
- Test tag scoring algorithm for SFX categories
- Test subtlety scoring calculation
- Test confidence calculation
- Test fallback suggestion logic
- Test duplicate SFX prevention

**Integration Tests:**
- Test end-to-end SFX matching with mock AI response
- Test SpacetimeDB query integration
- Test error scenarios: empty library, no matches, low confidence
- Test progress streaming

**Test Fixtures:**
- Sample transcript segments with various emotional beats
- Mock SFX library with diverse tags (transitions, impacts, ambience)
- AI response JSON samples (valid, no moments, low confidence)

### References

- **Epic Context:** [Source: _bmad-output/planning-artifacts/epics.md#Story 5.5: AI SFX Matching]
- **Architecture - AI Layer:** [Source: _bmad-output/planning-artifacts/architecture.md#Core Architectural Decisions]
- **Architecture - Database Layer:** [Source: _bmad-output/planning-artifacts/architecture.md#Database & Persistence Layer]
- **Architecture - Naming Conventions:** [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns]
- **PRD - FR23:** [Source: _bmad-output/planning-artifacts/prd.md#AI-Powered Rough Cut Generation]
- **PRD - NFR3 (Timeout):** [Source: _bmad-output/planning-artifacts/prd.md#Performance]
- **Previous Story (5.4):** [Source: _bmad-output/implementation-artifacts/5-4-ai-music-matching.md]

## Dev Agent Record

### Agent Model Used

accounts/fireworks/routers/kimi-k2p5-turbo (fireworks-ai/accounts/fireworks/routers/kimi-k2p5-turbo)

### Debug Log References

### Completion Notes List

**Implementation Complete - Story 5.5: AI SFX Matching**

**Task 1 - SFX Moment Identification System (COMPLETED):**
- Created `SFXMoment` dataclass in `backend/ai/sfx_moment.py` with timestamp, type, context, intensity, segment_name fields
- Created `SFXMomentList` dataclass for managing collections of moments
- Defined `SFX_MOMENT_MAPPINGS` dictionary mapping moment types to relevant tags
- Defined `INTENSITY_SUBTLETY_PREFERENCE` for subtlety guidance
- Implemented moment detection in `SFXMatcher.identify_sfx_moments()` with support for:
  - intro moments at segment start
  - outro moments near segment end
  - triumph moments based on success keywords
  - emphasis moments based on challenge/transition keywords
  - tension moments based on suspense keywords
  - underscore moments for longer segments (>30s)

**Task 2 - SFX Asset Matching Engine (COMPLETED):**
- Created `SFXMatcher` class in `backend/ai/sfx_matcher.py` with:
  - `identify_sfx_moments()` - Analyzes segments for SFX-appropriate moments
  - `match_sfx_to_moments()` - Matches SFX assets to identified moments
  - Tag scoring algorithm with exact/partial matching
  - Folder context matching with capped scoring
  - `_calculate_subtlety_score()` - Duration-based and tag-based subtlety scoring
  - Short (<2s), medium (2-5s), long (>5s) duration classifications

**Task 3 - Match Scoring & Ranking (COMPLETED):**
- Created `SFXMatch` dataclass with confidence_score, subtlety_score, matched_tags
- Created `MomentSFXMatches` dataclass for moment-level results
- Created `SFXMatchingResult` dataclass with statistics and layer_guidance
- Implemented tag relevance scoring (exact > partial > related)
- Added usage history tracking with `_apply_usage_penalty()` (15% penalty for recent assets)
- Return top N matches sorted by confidence
- Confidence thresholds: HIGH (>=0.80), MEDIUM (0.60-0.80), LOW (<0.60)

**Task 4 - AI Prompt Template (COMPLETED):**
- Created `match_sfx_system.txt` in `backend/ai/prompt_templates/`
- Comprehensive prompt with moment type guidelines, subtlety scoring rules
- JSON output format specification
- Matching guidelines with confidence score ranges
- Subtlety scoring guidelines (0.85-1.0 = very subtle, 0.50-0.69 = noticeable)
- Added `build_sfx_matching_prompt()` method to `PromptBuilder` class

**Task 5 - JSON-RPC Handler (COMPLETED):**
- Created `match_sfx()` handler in `protocols/handlers/ai.py`
- Created `match_sfx_with_progress()` streaming generator handler
- Added request validation for session_id, segments, sfx_index
- Returns structured SFX suggestions with layer_guidance: "Place each SFX on separate track for volume flexibility"
- Progress updates for: initialization, moment identification, matching, optimization, completion
- Registered both handlers in `AI_HANDLERS` registry

**Task 6 - Edge Cases & Error Handling (COMPLETED):**
- Error codes added: EMPTY_SFX_LIBRARY, NO_SFX_MATCHES, NO_MOMENTS_IDENTIFIED
- Empty SFX library handling with clear error messages
- No-match scenarios with fallback suggestions
- Low-confidence match warnings in result.warnings
- Duplicate SFX prevention with `prevent_duplicate_matches()`
- Missing metadata gracefully handled in from_dict() methods
- Comprehensive validation in all dataclasses with `__post_init__`

**Key Technical Decisions:**
- Used dataclasses for all data structures with `__post_init__` validation
- Implemented duration-based subtlety scoring (shorter = more subtle)
- Tag-based subtlety boost for keywords like "gentle", "soft", "subtle"
- Folder context matching with capped scores to prevent inflation
- Usage history tracking to encourage variety in SFX selection
- Generator pattern for progress streaming (consistent with Stories 5.2-5.4)

**Error Codes Added:**
- EMPTY_SFX_LIBRARY - No SFX assets indexed
- NO_SFX_MATCHES - No matches found for moment criteria
- LOW_CONFIDENCE_MATCHES - All matches below threshold (0.60)
- NO_MOMENTS_IDENTIFIED - AI found no suitable SFX moments

**Files Created:**
1. `roughcut/src/roughcut/backend/ai/sfx_moment.py` - SFXMoment, SFXMomentList dataclasses
2. `roughcut/src/roughcut/backend/ai/sfx_match.py` - SFXAsset, SFXMatch, MomentSFXMatches, SFXMatchingResult dataclasses
3. `roughcut/src/roughcut/backend/ai/sfx_matcher.py` - SFXMatcher class with moment identification and matching
4. `roughcut/src/roughcut/backend/ai/prompt_templates/match_sfx_system.txt` - AI prompt template
5. `roughcut/tests/unit/backend/ai/test_sfx_matcher.py` - Comprehensive unit tests

**Files Modified:**
1. `roughcut/src/roughcut/backend/ai/prompt_engine.py` - Added `build_sfx_matching_prompt()` and `_get_default_sfx_matching_prompt()`
2. `roughcut/src/roughcut/protocols/handlers/ai.py` - Added `match_sfx` and `match_sfx_with_progress` handlers, added SFX error codes, **RESTORED missing MusicMatch imports (critical fix)**

### File List

**New Files:**
- `roughcut/src/roughcut/backend/ai/sfx_moment.py`
- `roughcut/src/roughcut/backend/ai/sfx_match.py`
- `roughcut/src/roughcut/backend/ai/sfx_matcher.py`
- `roughcut/src/roughcut/backend/ai/prompt_templates/match_sfx_system.txt`
- `roughcut/tests/unit/backend/ai/test_sfx_matcher.py`

**Modified Files:**
- `roughcut/src/roughcut/backend/ai/prompt_engine.py`
- `roughcut/src/roughcut/protocols/handlers/ai.py`

## Project Context Reference

- **Project:** RoughCut - AI-powered DaVinci Resolve plugin
- **Epic:** 5 - AI-Powered Rough Cut Generation
- **Story:** 5.5 - AI SFX Matching
- **Prerequisites:** Stories 5.3 (Transcript Cutting) and 5.4 (Music Matching) complete
- **Next Story:** 5.6 - AI VFX/Template Matching

**Related Documents:**
- PRD: `_bmad-output/planning-artifacts/prd.md`
- Architecture: `_bmad-output/planning-artifacts/architecture.md`
- Epics: `_bmad-output/planning-artifacts/epics.md`
- Previous Story 5.4: `_bmad-output/implementation-artifacts/5-4-ai-music-matching.md`

---

**Story created:** 2026-04-04
**Status:** ready-for-dev
**Ultimate context engine analysis completed - comprehensive developer guide created**

## Change Log

### 2026-04-04 - Story Created
- Initial story context created with comprehensive developer guidance
- Based on learnings from Stories 5.3 and 5.4 implementation
- References architecture decisions on AI layer, database layer, and JSON-RPC protocol
- Emphasizes moment identification and tag-based matching approach
- Includes SFX-specific moment type taxonomy (intro, transition, emphasis, outro, underscore)
- Addresses subtlety requirements and non-distracting sound selection

### 2026-04-04 - Implementation Complete
- All 6 tasks completed with acceptance criteria satisfied
- Created sfx_moment.py with SFXMoment, SFXMomentList, SFX_MOMENT_MAPPINGS
- Created sfx_match.py with SFXAsset, SFXMatch, MomentSFXMatches, SFXMatchingResult
- Created sfx_matcher.py with SFXMatcher class and comprehensive matching logic
- Created AI prompt template for SFX matching with subtlety guidelines
- Extended PromptBuilder with build_sfx_matching_prompt() method
- Added match_sfx and match_sfx_with_progress handlers to protocols/handlers/ai.py
- Implemented duration-based and tag-based subtlety scoring
- Added usage history tracking with penalty system
- Created comprehensive unit tests covering all functionality
- Story marked ready for code review (status: review)

### 2026-04-04 - Code Review Complete
- **Critical Issue Fixed:** Restored missing MusicMatch imports in protocols/handlers/ai.py
  - Added: `from ...backend.ai.music_match import MusicMatch, MusicMatchingResult, SegmentMusicMatches`
  - This fixes a regression that would have broken the match_music handler
- Review approved with patch applied
- Status updated to done
