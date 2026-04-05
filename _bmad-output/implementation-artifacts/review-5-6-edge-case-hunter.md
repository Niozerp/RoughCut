# Edge Case Hunter Review - Story 5.6: AI VFX/Template Matching

## Role: Edge Case Hunter
**Task:** Review the diff with project context. Find edge cases, boundary conditions, and scenarios the code doesn't handle.

## Diff to Review

### Modified Files:
1. roughcut/src/roughcut/backend/ai/prompt_engine.py
2. roughcut/src/roughcut/protocols/handlers/ai.py
3. _bmad-output/implementation-artifacts/sprint-status.yaml

### New Files:
4. roughcut/src/roughcut/backend/ai/vfx_requirement.py
5. roughcut/src/roughcut/backend/ai/vfx_match.py
6. roughcut/src/roughcut/backend/ai/vfx_matcher.py
7. roughcut/src/roughcut/backend/ai/prompt_templates/match_vfx_system.txt
8. roughcut/tests/unit/backend/ai/test_vfx_matcher.py

## Project Context

This is part of RoughCut, an AI-powered DaVinci Resolve plugin. The VFX matching system:
- Matches VFX templates to format requirements
- Handles template asset groups with priority matching
- Calculates placement timing with conflict detection
- Integrates with JSON-RPC protocol over stdin/stdout

## Your Mission

Walk every branching path and boundary condition. Look for:

### Edge Cases
- Empty inputs (empty lists, None values)
- Boundary values (max/min timestamps, durations)
- Invalid data formats
- Malformed JSON/dictionaries
- Missing required fields
- Type mismatches
- Division by zero
- Negative values where positive expected

### Boundary Conditions
- Single item lists vs empty lists
- Exactly at threshold values
- Maximum and minimum possible values
- Concurrent/overlapping operations
- Resource exhaustion scenarios

### Unhandled Scenarios
- What if the VFX library has 1 item? 0 items? 10,000 items?
- What if all requirements overlap completely?
- What if template asset groups reference non-existent assets?
- What if timestamps are negative or extremely large?
- What if durations don't match between requirement and asset?

## Output Format

Provide findings as a Markdown list:

```markdown
### Edge Case 1: [Scenario]
- **Location:** file.py:line_number (function_name)
- **Condition:** What edge case is not handled
- **Current Behavior:** What the code does
- **Expected Behavior:** What should happen
- **Risk:** What could go wrong
- **Evidence:** Code snippet

### Edge Case 2: [Scenario]
...
```

## Review Focus Areas

1. **vfx_matcher.py** - The core matching engine
   - Tag scoring algorithm edge cases
   - Template group bonus calculation
   - Placement conflict detection
   - Speaker change detection

2. **vfx_match.py** - Data structures
   - Dataclass validation edge cases
   - Overlap detection edge cases
   - Serialization/deserialization

3. **vfx_requirement.py** - Requirements
   - Timestamp validation edge cases
   - Duration constraint edge cases
   - Conflict detection with tolerance

4. **protocols/handlers/ai.py** - JSON-RPC handlers
   - Parameter validation edge cases
   - Progress streaming edge cases
   - Error handling edge cases

## Critical Rules
- Review WITH project context access
- Focus on WHAT COULD GO WRONG
- Test mental scenarios at boundaries
- Look for gaps in validation
