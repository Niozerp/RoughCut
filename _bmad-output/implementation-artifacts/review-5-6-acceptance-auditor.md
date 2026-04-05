# Acceptance Auditor Review - Story 5.6: AI VFX/Template Matching

## Role: Acceptance Auditor
**Task:** Review the diff against the story spec. Check for violations of acceptance criteria, missing implementation, and deviations from spec intent.

## Story Spec Summary

### Story Statement
As a video editor, I want the AI to match VFX and template assets to format requirements, so that lower thirds, transitions, and effects are positioned appropriately.

### Acceptance Criteria

**AC #1: VFX Requirement Identification**
- Given format template specifies VFX requirements
- When AI processes the rough cut
- Then it identifies template moments needing VFX
- And moments are mapped to specific timestamps and format sections

**AC #2: Lower Third Matching**
- Given lower thirds are needed for speaker introductions
- When AI searches VFX template library
- Then it matches appropriate templates
- And matches consider both AI-generated tags and folder path context

**AC #3: Template Placement Calculation**
- Given template placements are determined
- When positions are calculated
- Then they align with transcript segment boundaries and format timing rules
- And placements respect template duration specifications

**AC #4: VFX Presentation in Review Document**
- Given VFX suggestions are generated
- When editor reviews the rough cut document
- Then they see: "VFX: lower_third_template at 0:15 (intro speaker), outro_cta at 3:45"
- And each entry includes: file path, template type, placement timestamp, duration

**AC #5: Template Asset Group Priority**
- Given a format has specific template asset groups defined
- When AI processes
- Then it prioritizes assets from those predefined groups
- And falls back to general VFX library if group assets unavailable

### Key Technical Requirements

**Data Structures:**
- VFXRequirement (timestamp, type, context, duration, format_section, speaker_name)
- VFXMatch (vfx_id, file_path, confidence_score, template_type, placement, from_template_group)
- VFXPlacement (start_time, end_time, duration_ms)

**Key Methods:**
- identify_vfx_requirements() - parses format templates, detects speaker changes
- match_vfx_to_requirements() - matches templates with group priority
- calculate_placement() - aligns timestamps with duration constraints
- placement conflict detection and resolution

**Error Codes:**
- EMPTY_VFX_LIBRARY
- NO_VFX_MATCHES
- NO_REQUIREMENTS_IDENTIFIED
- PLACEMENT_CONFLICTS

## Your Mission

Compare the implementation against the spec. Look for:

### Acceptance Criteria Violations
- AC #1: Does it identify VFX requirements from format templates?
- AC #2: Does it match lower thirds for speaker intros with tag/folder context?
- AC #3: Does placement align with segment boundaries and duration specs?
- AC #4: Does output include file path, template type, timestamp, duration?
- AC #5: Does it prioritize template asset groups with fallback?

### Spec Deviations
- Requirements not fully implemented
- Behavior that contradicts spec intent
- Missing constraints or validations
- Different approaches than specified

### Missing Implementation
- Methods mentioned in spec but not implemented
- Error handling not added
- Data fields missing
- JSON-RPC handlers not registered

## Output Format

Provide findings as a Markdown list:

```markdown
### Violation 1: [AC # or Requirement]
- **Type:** Missing/Incorrect/Partial
- **Location:** file.py:line_number
- **Spec Requirement:** What the spec says
- **Actual Implementation:** What the code does
- **Gap:** What's missing or wrong
- **Evidence:** Code snippet or diff excerpt

### Violation 2: [AC # or Requirement]
...
```

## Review Checklist

### AC #1 Check
- [ ] identify_vfx_requirements() implemented
- [ ] Parses format_template.vfx_requirements
- [ ] Detects speaker changes for lower thirds
- [ ] Maps moments to timestamps
- [ ] Maps to format sections

### AC #2 Check
- [ ] Tag-based matching implemented
- [ ] Folder context matching implemented
- [ ] Lower third detection for speaker intros

### AC #3 Check
- [ ] calculate_placement() aligns with segment boundaries
- [ ] Duration constraints respected
- [ ] Overlap detection exists

### AC #4 Check
- [ ] VFXMatch includes file_path
- [ ] VFXMatch includes template_type
- [ ] VFXMatch includes placement with timestamp
- [ ] VFXMatch includes placement with duration

### AC #5 Check
- [ ] Template asset groups parsed from format_template
- [ ] Group assets get priority in matching
- [ ] Fallback to general library when group assets unavailable

### Handlers Check
- [ ] match_vfx() handler implemented
- [ ] match_vfx_with_progress() handler implemented
- [ ] Both registered in AI_HANDLERS
- [ ] Error codes added

## Critical Rules
- Review WITH spec access
- Focus on COMPLIANCE with acceptance criteria
- Note any PARTIAL implementations
- Flag SPEC DEVIATIONS
