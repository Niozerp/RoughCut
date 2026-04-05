# Blind Hunter Review - Story 5.6: AI VFX/Template Matching

## Role: Blind Hunter
**Task:** Review the diff adversarially without any project context, spec, or background. Find issues purely from the code changes.

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

## Your Mission

Review the code changes with fresh eyes. Look for:

### Code Quality Issues
- Bugs or logical errors
- Security vulnerabilities
- Performance problems
- Race conditions
- Error handling gaps
- Resource leaks
- Input validation failures

### Design Issues
- Overly complex logic
- Tight coupling
- Poor abstraction
- Reinvented wheels
- Inconsistent patterns

### Maintainability Issues
- Hardcoded values
- Magic numbers
- Unclear naming
- Missing docstrings
- Complex nested conditionals

## Output Format

Provide findings as a Markdown list:

```markdown
### Finding 1: [Title]
- **Severity:** High/Medium/Low
- **Location:** file.py:line_number
- **Issue:** Brief description
- **Evidence:** Code snippet showing the problem
- **Impact:** What could go wrong

### Finding 2: [Title]
...
```

## Critical Rules
- NO access to spec files
- NO access to project context  
- Review ONLY the provided diff
- Be adversarial - assume the worst
- Focus on code that looks suspicious or wrong
