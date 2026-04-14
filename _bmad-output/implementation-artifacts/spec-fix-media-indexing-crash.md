---
title: 'Fix Media Indexing Crash - Core Diagnostics'
type: 'bugfix'
created: '2026-04-12'
status: 'done'
baseline_commit: '0fb1c892de90057f33bd0b24b52ea387d8cb1075'
context: []
---

## Intent

**Problem:** The Python indexing process crashes with exit code null during startup indexing, preventing users from populating their media libraries. The crash provides no diagnostic information about which phase failed or why.

**Approach:** Add phase-specific error handling and diagnostic logging to identify and gracefully handle failures during the 4-phase indexing workflow.

## Boundaries & Constraints

**Always:**
- Preserve all existing indexing functionality
- Maintain existing IPC pattern between Electron and Python
- Keep SpacetimeDB integration intact
- Use existing error handling patterns in PythonBridge.ts

**Ask First:**
- Changing timeout values from current 5/10 minute settings
- Reducing batch sizes below 500 assets

**Never:**
- Modify the fundamental indexing workflow
- Remove progress reporting
- Skip file hashing entirely
- Add new dependencies

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | Valid media folders | Indexing completes, assets appear | N/A |
| ERROR_CASE | Python process OOM killed | "Indexing failed: Out of memory" | Graceful degradation |
| ERROR_CASE | Phase 0 (DB) fails | "Database connection failed" | Show phase in error |
| ERROR_CASE | Phase 1 (Discovery) fails | "File scanning failed: [error]" | Show phase in error |
| ERROR_CASE | Phase 2 (Catalogue) fails | "Change detection failed: [error]" | Show phase in error |
| ERROR_CASE | Phase 3 (Datawrite) fails | "Database write failed: [error]" | Show phase in error |
| EDGE_CASE | 5-minute timeout | "Indexing timed out" | Partial results preserved |

## Code Map

- `roughcut/electron/electron/pythonBridge.ts` -- Spawns Python, handles exit codes
- `roughcut/src/roughcut/backend/indexing/indexer.py` -- 4-phase orchestrator
- `roughcut/src/roughcut/backend/database/spacetime_client.py` -- DB connection

## Tasks & Acceptance

**Execution:**
- [x] `roughcut/electron/electron/pythonBridge.ts` -- Add exit code null detection with OOM hint -- Help users understand the crash
- [x] `roughcut/electron/electron/pythonBridge.ts` -- Capture last [INDEXING_LOG] before process death -- Get diagnostic context
- [x] `roughcut/src/roughcut/backend/indexing/indexer.py` -- Wrap each phase in try/except with phase ID -- Identify which phase crashes
- [x] `roughcut/src/roughcut/backend/indexing/indexer.py` -- Add phase-specific error messages -- Easier debugging
- [x] `roughcut/src/roughcut/backend/database/spacetime_client.py` -- Log connection attempts with attempt number -- Debug DB connection issues

**Acceptance Criteria:**
- Given Python crashes with exit code null, when caught, then user sees "Out of memory" message
- Given any phase fails, when error occurs, then [INDEXING_LOG] shows "PHASE X FAILED" with error
- Given SpacetimeDB is unreachable, when connecting, then error shows "PHASE 0: Database connection failed"
- Given timeout occurs, when 5min passes, then process terminates with "Indexing timed out" message

## Spec Change Log

## Verification

**Commands:**
- `cd roughcut/electron && npm run build` -- expected: No TypeScript errors
- `cd roughcut && poetry run python -m py_compile src/roughcut/backend/indexing/indexer.py` -- expected: No Python syntax errors

**Manual checks:**
- Check DevTools console -- verify [INDEXING_LOG] shows phase numbers
- Stop SpacetimeDB -- verify PHASE 0 error is clear
