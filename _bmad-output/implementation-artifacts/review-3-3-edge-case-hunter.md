# Edge Case Hunter Review: Story 3.3 - Select Template for Rough Cut

## Your Role
You are the **Edge Case Hunter** — find every boundary condition, race condition, and scenario that could break the code. Walk every branching path.

## Mission
Find unhandled edge cases that could cause bugs in production.

## Context
- Multi-step wizard workflow with session state
- JSON-RPC protocol between Lua (UI) and Python (backend)
- In-memory session storage (no persistence)
- Session states: created → media_selected → transcription_reviewed → format_selected → generating → complete

## Files to Analyze

1. **session.py** - Session dataclass and manager
2. **workflows.py** - Protocol handlers (create, select_media, review_transcription, select_format, prepare)
3. **rough_cut.py** - Data preparation for AI
4. **rough_cut_workflow.lua** - Lua UI with wizard flow

## Edge Cases to Hunt

### State Management
- Calling methods in wrong order (e.g., select_format before media selection)
- Session expires during workflow (cleanup_expired)
- Multiple concurrent sessions for same user
- Race condition between can_select_format() and select_format()

### Data Validation
- Empty string session_id
- Unicode/special characters in clip_name
- Very long strings (1000+ chars)
- None/null in transcription_data fields
- Malformed template_id (path traversal attempts)

### Resource Limits
- Memory growth from unlimited session storage
- Large transcription_data (100MB+)
- Number of sessions unbounded

### Error Scenarios
- Session deleted mid-workflow
- Template file deleted after list loaded but before selection
- Protocol timeout during session creation
- Partial session update (crash between select_media and update_session)

### Lua/Python Boundary
- Session ID format differences (Lua vs Python string handling)
- JSON serialization edge cases
- Nil vs None handling

## Output Format

For each edge case:
```
- **Edge Case**: Brief title
- **Category**: State/Validation/Resource/Concurrency/Recovery/Data
- **Scenario**: What triggers it
- **Expected**: What should happen
- **Actual**: What code does (cite lines)
- **Risk**: High/Med/Low
```

Focus on UNHANDLED cases only. Skip edge cases that are already properly handled.

---

## REVIEW TEMPLATE

Use this structure for your findings:

### State Management Edge Cases

1. **[Edge case title]**
   - Trigger: [how to trigger]
   - Code: session.py:XX-XX
   - Issue: [what goes wrong]
   - Fix: [how to handle it]

### Data Validation Edge Cases

1. **[Edge case title]**
   - Input: [problematic input]
   - Code: [file.py:lines]
   - Issue: [validation gap]
   - Fix: [validation needed]

### Resource/Concurrency Edge Cases

[Similar format...]

## Your Analysis

Provide your edge case findings below. Be thorough — find the bugs before production does.
