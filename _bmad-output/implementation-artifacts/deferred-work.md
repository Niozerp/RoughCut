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

## Deferred from: code review of 2-2-incremental-media-indexing (2026-04-03)

### SpacetimeDB integration incomplete
- **Reason:** Deferred to Story 2.5 per architecture plan
- **Context:** Database operations are placeholders. Full SpacetimeDB integration scheduled for Story 2.5: SpacetimeDB Storage. Models are ready but storage layer needs implementation.

### No error logging framework integration
- **Reason:** Pre-existing infrastructure pattern
- **Context:** Errors collected in lists but not logged to file. Project has `lua/utils/logger.lua` but Python backend doesn't use unified logging. Architectural decision needed.

### FFI duplicate declaration risk
- **Reason:** Pre-existing pattern in codebase
- **Context:** `ffi.cdef` in Lua files may error if called multiple times. Existing codebase uses this pattern, needs comprehensive fix across all Lua modules.

## Deferred from: code review of 2-1-media-folder-configuration (2026-04-03)

### Test flakiness on Windows for relative paths
- **Reason:** Pre-existing test infrastructure behavior, not blocking
- **Context:** Test expectation already accounts for platform differences between Windows and Unix path validation. The test passes with a flexible assertion that accepts either "does not exist" or "must be absolute" errors. This is acceptable behavior given platform differences.

### Missing `__init__.py` files in test directories
- **Reason:** Pre-existing structure issue, not caused by this change
- **Context:** The test files use various import patterns including `sys.path.insert()` hacks, suggesting the test package structure is incomplete and may cause import failures in certain test runners. This is a pre-existing infrastructure issue not introduced by Story 2.3.

## Deferred from: code review of 2-5-spacetimedb-storage (2026-04-04)

### Double hasattr check pattern
- **Reason:** Pre-existing pattern, not introduced by this change
- **Context:** Repeated `hasattr(self, '_counter')` checks in indexer.py lines 464, 516, 572 are unnecessary since `_counter` is always set in `__post_init__`. These checks existed in similar patterns in previous stories. Architectural cleanup needed.

### Eager singleton initialization
- **Reason:** Pre-existing ConfigManager pattern
- **Context:** `get_config_manager()` returns `ConfigManager()` which eagerly loads config from disk in `__init__`. Import-time side effects from ConfigManager singleton pattern used across all stories. Architectural refactoring required.

## Deferred from: code review of 3-2-preview-template-structure (2026-04-04)

### TOCTOU race condition in get_template_preview
- **Reason:** Pre-existing pattern in codebase
- **Context:** File existence is checked before parsing, creating a race condition window. Same pattern exists in scanner.py and other file operations. Architectural cleanup needed.

### YAML parses to non-dict type
- **Reason:** Warning exists, acceptable behavior
- **Context:** Frontmatter that parses to list or scalar is silently discarded with a warning. This is graceful degradation, not an error.

### Fractional seconds not handled in time parsing
- **Reason:** Not in requirements, edge case
- **Context:** Time formats like "1:30.5" are not supported. Current templates use whole seconds only.

### Single number time format not handled
- **Reason:** Not in requirements, edge case
- **Context:** Simple second counts like "15" for 15 seconds are not parsed. All templates use MM:SS format.

### Case-sensitive .MD extension
- **Reason:** Rare edge case
- **Context:** Uppercase .MD files not recognized on case-sensitive filesystems. All templates use lowercase .md.

### Hard link path traversal
- **Reason:** Platform-specific, edge case
- **Reason:** Hard links to files outside templates directory not blocked. Symlinks are blocked but hard links are not. Low risk scenario.

### Frontmatter with --- inside quoted YAML value
- **Reason:** Complex edge case
- **Context:** YAML values containing "---" may truncate parsing. No templates currently use this pattern.

### Unsorted files sliced arbitrarily
- **Reason:** Already using sorted()
- **Context:** File ordering is deterministic with sorted(). First 1000 templates by filename is acceptable behavior.

## Deferred from: code review of 2-7-notion-sync (2026-04-04)

### Import cycle risk in client.py
- **Reason:** Pre-existing architectural pattern, not blocking
- **Context:** `sync_media_database()` imports `NotionSyncOrchestrator` inside method to avoid circular import. This is a workaround indicating potential architectural coupling. Should refactor to proper dependency injection or module restructuring.

## Deferred from: code review of 3-5-template-asset-groups (2026-04-04)

### Parser Not Integrated with Template Loading
- **Reason:** Integration requires coordination with Story 3.4 and Story 3.6
- **Context:** AssetGroupParser exists as standalone class but no integration with FormatTemplate loading workflow from Story 3.4. FormatTemplate dataclass doesn't have asset_groups field yet. Integration should be done as part of Story 3.6 (Parse Format Rules) which extends FormatTemplate.
