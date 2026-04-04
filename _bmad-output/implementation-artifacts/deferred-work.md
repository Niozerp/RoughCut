# Deferred Work Log

## Deferred from: code review of 1-2-scripts-menu-integration (2026-04-03)

### Global state pollution
- **Reason:** Pre-existing pattern in Lua modules, defer to comprehensive refactoring
- **Context:** Module-level variables (windowRef, uiManagerRef, childWindows) persist across launches. Need lifecycle management story to address properly.

### No cleanup on script exit
- **Reason:** Pre-existing pattern, defer to lifecycle management story
- **Context:** Windows may remain open if Resolve crashes or script errors. Proper cleanup requires architectural changes across all stories.

### Missing tooltip test coverage
- **Reason:** Low priority, defer to comprehensive test suite
- **Context:** Tooltips defined in navigation.lua but no automated tests verify display. Manual testing sufficient for now.

### Mock UI Manager simplification
- **Reason:** Test infrastructure limitation, dismiss for now
- **Context:** Tests use simplistic mock that doesn't fully simulate Resolve API. Would require Resolve integration test framework.

### No automated test for AC 1 (Scripts Menu Visibility)
- **Reason:** Requires Resolve environment integration testing
- **Context:** Cannot automate testing that script appears in Resolve's Scripts menu without Resolve integration test framework.

### Hardcoded "Ready" status
- **Reason:** From later story implementation (Story 1.3), defer
- **Context:** Status always shows "Ready" regardless of actual backend state. Will be addressed when backend integration complete.

## Deferred from: code review of 1-1-drag-and-drop-installation (2026-04-03)

### Incomplete AC 1 verification
- **Reason:** Full menu integration will be implemented in Story 1.2
- **Context:** Current implementation only shows verification dialog, doesn't demonstrate registration mechanism

### Python version upper bound decision
- **Reason:** User deferred - no change needed at this time
- **Context:** `requires-python = ">=3.10"` with no upper bound. May need to cap at `<4.0` in future

### Automated versioning strategy
- **Reason:** User confirmed automated versioning for future implementation
- **Context:** Currently hardcoded "0.1.0". Need to implement automated version bumping in CI/CD or build process
