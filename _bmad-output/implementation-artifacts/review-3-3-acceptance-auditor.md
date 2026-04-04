# Acceptance Auditor Review: Story 3.3 - Select Template for Rough Cut

## Your Role
You are the **Acceptance Auditor** — verify implementation matches requirements exactly.

## Mission
Check for AC violations, spec deviations, and missing functionality.

## Spec Source
**File:** `_bmad-output/implementation-artifacts/3-3-select-template-for-rough-cut.md`

## Acceptance Criteria

### AC1: Format Selection Presented
> Given I have selected source media and reviewed transcription, When I proceed to format selection, Then Available templates are presented in a selectable list

**Verify:**
- [ ] Workflow reaches format selection step after transcription review
- [ ] `get_available_formats()` called to load templates
- [ ] Format list displayed in UI with selectable items
- [ ] Each item shows name and description

**Implementation Location:** 
- Lua: rough_cut_workflow.lua `_showFormatSelectionStep()`
- Lua: `_loadFormatsAsync()` and `_populateFormatsList()`
- Protocol: formats.py `get_available_formats()`

---

### AC2: Session Remembers Choice
> Given I select a format template, When Selection is confirmed, Then The system remembers my choice for the current rough cut session

**Verify:**
- [ ] `select_format_template()` protocol handler exists
- [ ] Session updated with format_template_id
- [ ] Session updated with format_template object
- [ ] Status changes to "format_selected"
- [ ] Session can be retrieved with format choice intact

**Implementation Location:**
- Protocol: formats.py `select_format_template()`
- Python: session.py `select_format()` method
- Python: session.py `SessionManager.update_session()`

---

### AC3: Template Rules Passed to AI
> Given I have selected a template, When I proceed to generate rough cut, Then The selected template's rules are passed to the AI service

**Verify:**
- [ ] `prepare_rough_cut_for_generation()` handler exists
- [ ] Returns transcript data
- [ ] Returns template rules (segments, asset_groups)
- [ ] Returns timing specifications
- [ ] Data formatted for AI service consumption

**Implementation Location:**
- Protocol: workflows.py `prepare_rough_cut_for_generation()`
- Python: rough_cut.py `RoughCutDataPreparer.prepare()`
- Python: session.py `get_generation_data()`

---

### AC4: Create Rough Cut Path Includes Format Selection
> Given Format selection is part of the rough cut workflow, When I access it from the main window, Then "Create Rough Cut" path naturally includes format selection step

**Verify:**
- [ ] "Create Rough Cut" button opens workflow
- [ ] Workflow has step indicator (Media → Transcription → Format → Generate)
- [ ] Format selection is 3rd step
- [ ] Navigation flows naturally to format step

**Implementation Location:**
- Lua: navigation.lua "btnCreateRoughCut" handler
- Lua: rough_cut_workflow.lua step indicator
- Lua: `_buildStepIndicator()` function

---

## Task Checklist Verification

### Task 1: Session State Management ✅
- [x] RoughCutSession dataclass implemented
- [x] All required fields present (media_clip_id, format_template_id, transcription_data, status)
- [x] Session lifecycle methods implemented
- [x] In-memory storage (SessionManager)

### Task 2: Template Selection Protocol ✅
- [x] select_format_template handler in formats.py
- [x] Template validation using TemplateScanner
- [x] Session state update
- [x] Error handling for invalid cases

### Task 3 & 4: Workflow UI ✅
- [x] Create Rough Cut workflow entry point
- [x] Format selection view
- [x] Template list display
- [x] Preview integration
- [x] Navigation buttons

### Task 5: Generation Preparation ✅
- [x] prepare_rough_cut_data handler
- [x] Collects transcript, template rules
- [x] Formats for AI service
- [x] Validation before generation

### Task 6: Workflow Navigation ✅
- [x] Step indicator implemented
- [x] Session validation at steps
- [x] Cancel handling
- [x] State persistence

### Task 7: Testing ✅
- [x] Unit tests for session management
- [x] Unit tests for protocol handlers
- [x] Test files created

---

## Your Audit

Check each AC against the implementation. For any deviation:

```
- **AC Violation**: AC# - description
- **Spec Requires**: [what story says]
- **Code Does**: [what code actually does]
- **Location**: [file:lines]
- **Severity**: Critical/Med/Low
- **Fix**: [what needs to change]
```

If all ACs pass:
> "All acceptance criteria satisfied. Implementation matches spec."

## Final Determination

Provide your audit findings below.
