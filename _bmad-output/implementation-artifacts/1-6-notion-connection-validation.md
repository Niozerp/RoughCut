# Story 1.6: Notion Connection Validation

Status: done
Story ID: 1.6
Story Key: 1-6-notion-connection-validation
Epic: 1 - Foundation & Installation

---

## Story

As a video editor,
I want to validate my Notion connection and handle errors gracefully,
So that I know if my cloud sync is working or if I need to troubleshoot.

---

## Acceptance Criteria

### AC 1: Connection Validation Test
**Given** I have configured Notion integration
**When** I request connection validation
**Then** The system tests the connection to Notion API using the stored credentials
**And** The test validates both API token authentication and page accessibility

### AC 2: Successful Connection Feedback
**Given** The Notion connection is valid
**When** Validation completes
**Then** I see a success message indicating connection is working
**And** A test sync option is available to verify data flow
**And** The last successful validation timestamp is displayed

### AC 3: Failed Connection Error Handling
**Given** The Notion connection fails
**When** Validation completes
**Then** I see a clear error message with specific failure reason (e.g., "Invalid API token", "Page not found", "Network error")
**And** Actionable guidance is provided (e.g., "Check your API token in Notion integrations", "Verify the page URL is correct and accessible")
**And** The system continues to operate without Notion (graceful degradation)

### AC 4: Graceful Degradation Without Notion
**Given** Notion is not configured
**When** I use RoughCut
**Then** All core functionality works normally
**And** No errors related to missing Notion configuration appear
**And** The validation option is either hidden or shows "Notion not configured" message

### AC 5: Validation UI Integration
**Given** I am in the Notion settings screen
**When** I look at my configuration
**Then** I see a "Test Connection" button
**And** I see the current connection status indicator (Connected / Disconnected / Not Configured)
**And** I can trigger validation on demand

---

## Tasks / Subtasks

**Task Dependencies:**
- All tasks depend on Story 1.5 (Notion Configuration) - requires existing configuration system
- Task 1 must complete before Tasks 2-3 (backend validation must work before UI)
- Task 4 depends on Tasks 1-3 (status persistence requires both backend and UI)
- Task 5 can be done in parallel with Tasks 2-4

- [x] Task 1: Implement Notion API Connection Validation Backend (AC: #1)
  - [x] Subtask 1.1: Add `notion-client` dependency to pyproject.toml
  - [x] Subtask 1.2: Implement `validate_connection()` method in `src/roughcut/backend/notion/client.py` using actual Notion API
  - [x] Subtask 1.3: Create `validate_token()` helper to test API token authentication
  - [x] Subtask 1.4: Create `validate_page_access()` helper to test page URL accessibility
  - [x] Subtask 1.5: Implement error classification (auth errors, network errors, page errors)
  - [x] Subtask 1.6: Add retry logic with exponential backoff for transient failures (max 3 retries)
  - [x] Subtask 1.7: Implement connection timeout handling (10 seconds max)

- [x] Task 2: Create Validation Result Data Models (AC: #1, #2, #3)
  - [x] Subtask 2.1: Create `ValidationResult` dataclass in `src/roughcut/backend/notion/models.py`
  - [x] Subtask 2.2: Define fields: `valid` (bool), `error_type` (enum), `error_message` (str), `suggestion` (str), `timestamp` (datetime)
  - [x] Subtask 2.3: Create `ConnectionStatus` enum: CONNECTED, DISCONNECTED, NOT_CONFIGURED, ERROR
  - [x] Subtask 2.4: Implement `to_dict()` and `from_dict()` methods for serialization
  - [x] Subtask 2.5: Add `last_validated` timestamp tracking in configuration

- [x] Task 3: Implement Validation Protocol Handlers (AC: #1, #5)
  - [x] Subtask 3.1: Create `validate_notion_connection()` handler in `src/roughcut/protocols/handlers/notion.py`
  - [x] Subtask 3.2: Implement `get_connection_status()` handler to retrieve current status
  - [x] Subtask 3.3: Register handlers in `src/roughcut/protocols/dispatcher.py`
  - [x] Subtask 3.4: Add error handling with user-friendly error messages in protocol layer
  - [x] Subtask 3.5: Implement `test_notion_sync()` handler (placeholder for Epic 2)
  - [x] Subtask 3.6: Add retry logic and timeout handling in backend client

- [x] Task 4: Create Connection Validation UI (AC: #2, #3, #5)
  - [x] Subtask 4.1: Update `lua/ui/notion_settings.lua` to add "Test Connection" button
  - [x] Subtask 4.2: Implement connection status indicator (green/red/grey icon or text)
  - [x] Subtask 4.3: Create validation result dialog showing success or detailed error
  - [x] Subtask 4.4: Add actionable guidance text in error dialogs with links/help
  - [x] Subtask 4.5: Implement "Last validated: [timestamp]" display
  - [x] Subtask 4.6: Add "Test Sync" button when connection is valid (placeholder for Epic 2)
  - [x] Subtask 4.7: Handle validation in-progress state (disable button, show spinner)

- [x] Task 5: Implement Graceful Degradation (AC: #4)
  - [x] Subtask 5.1: Update `NotionClient.validate_connection()` to return NOT_CONFIGURED status when no config
  - [x] Subtask 5.2: Ensure all Notion operations check `is_configured()` before API calls
  - [x] Subtask 5.3: Verify core functionality works without Notion (regression test Stories 1.1-1.5)
  - [x] Subtask 5.4: Add "Notion not configured" message in settings when appropriate
  - [x] Subtask 5.5: Ensure no error dialogs appear for missing Notion during normal usage

- [x] Task 6: Add Connection Status Persistence (AC: #2)
  - [x] Subtask 6.1: Extend `NotionConfig` model to include `last_validation_result` field
  - [x] Subtask 6.2: Update `ConfigManager` to save/load validation results
  - [x] Subtask 6.3: Persist validation status across application restarts
  - [x] Subtask 6.4: Add `connection_status` field to configuration schema

- [x] Task 7: Testing and Validation
  - [x] Subtask 7.1: Unit tests for Notion API validation with mocked responses
  - [x] Subtask 7.2: Unit tests for error classification and message generation
  - [x] Subtask 7.3: Unit tests for retry logic and timeout handling
  - [x] Subtask 7.4: Integration tests for Lua-Python protocol handlers
  - [x] Subtask 7.5: Test AC 1: Verify validation tests actual API connection
  - [x] Subtask 7.6: Test AC 2: Verify success message displays with timestamp
  - [x] Subtask 7.7: Test AC 3: Verify error messages are clear and actionable
  - [x] Subtask 7.8: Test AC 4: Verify no errors when Notion not configured
  - [x] Subtask 7.9: Test AC 5: Verify UI has Test Connection button and status indicator
  - [x] Subtask 7.10: Regression test: Stories 1.1-1.5 all work correctly

---

## Dev Notes

### Relevant Architecture Patterns and Constraints

**Notion Integration Architecture:**
From [Source: architecture.md#External APIs]:
- Notion API client location: `src/roughcut/backend/notion/client.py`
- Uses `notion-client` library (official Notion Python SDK)
- All Notion operations must be optional - graceful degradation required

**Error Handling Patterns:**
From [Source: architecture.md#Reliability]:
- NFR9-12: Graceful API unavailability handling, comprehensive error handling
- Error messages must be actionable and user-friendly
- Implement retry logic with exponential backoff for transient failures

**Security Requirements:**
From [Source: architecture.md#Security]:
- NFR6: API keys stored encrypted (already implemented in Story 1.5)
- Config module at `src/roughcut/config/` with encryption utilities
- Decrypt credentials only when making API calls

**Naming Conventions:**
From [Source: architecture.md#Naming Patterns]:
- **Python Layer**: `snake_case` functions/variables, `PascalCase` classes
- **Lua Layer**: `camelCase` functions/variables, `PascalCase` GUI components
- **Error Types**: `SCREAMING_SNAKE_CASE` enum values

**Lua-Python Communication:**
From [Source: architecture.md#Lua ↔ Python Communication Protocol]:
- JSON-RPC protocol over stdin/stdout
- Handlers registered in `src/roughcut/protocols/dispatcher.py`
- Async operations should show progress in UI

### Source Tree Components to Touch

**Backend (Python):**
- `src/roughcut/backend/notion/client.py` - Implement actual validation logic
- `src/roughcut/backend/notion/models.py` - Add ValidationResult model
- `src/roughcut/protocols/handlers/notion.py` - Create validation handlers
- `src/roughcut/protocols/dispatcher.py` - Register new handlers
- `src/roughcut/config/models.py` - Extend NotionConfig with validation fields
- `pyproject.toml` - Add `notion-client` dependency

**Frontend (Lua):**
- `lua/ui/notion_settings.lua` - Add Test Connection button and status UI
- `lua/ui/components/status_indicator.lua` (create if doesn't exist) - Reusable status component

**Tests:**
- `tests/unit/notion/test_client.py` - Unit tests for validation logic
- `tests/unit/notion/test_models.py` - Tests for data models
- `tests/integration/test_notion_protocol.py` - Protocol handler tests

### Testing Standards Summary

**Unit Tests:**
- Mock Notion API responses for reliable testing
- Test all error classification scenarios
- Verify retry logic with mocked time

**Integration Tests:**
- Test Lua-Python protocol communication
- Test UI state transitions
- Test configuration persistence

**Manual Testing:**
- Test with valid Notion credentials
- Test with invalid token
- Test with valid token but invalid page URL
- Test without Notion configured
- Verify graceful degradation across all features

### Project Structure Notes

**Alignment with Unified Structure:**
- Follows `src/roughcut/backend/notion/` pattern established in Story 1.5
- Extends existing `NotionClient` class rather than creating new one
- Uses existing `ConfigManager` from `src/roughcut/config/`
- Protocol handlers follow established pattern in `src/roughcut/protocols/handlers/`

**Dependencies:**
- Story 1.5 must be complete (provides configuration system)
- `notion-client` library must be added to project dependencies
- Existing encryption system from `src/roughcut/config/crypto.py` for credential handling

### References

**Architecture:**
- [Source: architecture.md#External APIs] - Notion API integration patterns
- [Source: architecture.md#Lua ↔ Python Communication Protocol] - Protocol handler patterns
- [Source: architecture.md#Security] - Encryption requirements
- [Source: architecture.md#Naming Patterns] - Code naming conventions

**Previous Story:**
- [Source: 1-5-optional-notion-configuration.md] - Configuration system implementation
- [Source: roughcut/src/roughcut/backend/notion/client.py] - Existing placeholder client
- [Source: roughcut/src/roughcut/config/] - Configuration and encryption modules

**Notion API:**
- Official Python SDK: `notion-client` library
- API Documentation: https://developers.notion.com/
- Key endpoints: `users/me` (token validation), `pages/{page_id}` (page access)

---

## Dev Agent Record

### Agent Model Used

fireworks-ai/accounts/fireworks/routers/kimi-k2p5-turbo

### Debug Log References

No errors encountered during implementation.

### Completion Notes List

**Task 1 - Notion API Validation Backend (COMPLETED)**
- Added `notion-client` (2.2.0) dependency to pyproject.toml
- Implemented full validation logic in `NotionClient.validate_connection()`
- Created `validate_token()` to test API authentication using `users/me` endpoint
- Created `validate_page_access()` to test page accessibility using `pages.retrieve()`
- Implemented comprehensive error classification with 5 error types: AUTHENTICATION, PAGE_NOT_FOUND, NETWORK, TIMEOUT, UNKNOWN
- Added retry logic with exponential backoff (max 3 retries, 1s initial delay)
- Added connection timeout handling (10s max)

**Task 2 - Validation Result Data Models (COMPLETED)**
- Created `ValidationResult` dataclass with all required fields: valid, status, error_type, error_message, suggestion, timestamp, last_successful
- Created `ConnectionStatus` enum: CONNECTED, DISCONNECTED, NOT_CONFIGURED, ERROR
- Created `ErrorType` enum: AUTHENTICATION, PAGE_NOT_FOUND, NETWORK, TIMEOUT, UNKNOWN
- Implemented `to_dict()` and `from_dict()` methods for JSON serialization
- Added `NotionPage` and `SyncResult` models for future Epic 2 work

**Task 3 - Protocol Handlers (COMPLETED)**
- Created `validate_notion_connection()` handler for full connection validation
- Created `get_connection_status()` handler for cached status retrieval
- Created `test_notion_sync()` handler for Epic 2 preview
- Registered all handlers in dispatcher.py
- Added comprehensive error handling with user-friendly messages

**Task 4 - Connection Validation UI (COMPLETED)**
- Added "Test Connection" button to notion_settings.lua
- Added connection status indicator (color-coded: green/red/grey)
- Added "Last validated" timestamp display
- Added "Test Sync (Preview)" button for Epic 2
- Added validation in-progress indicator with spinner text
- Created validation result dialogs with success/error messages
- Implemented actionable guidance in error dialogs

**Task 5 - Graceful Degradation (COMPLETED)**
- `validate_connection()` returns NOT_CONFIGURED status when no config
- All Notion operations check `is_configured()` before API calls
- No error dialogs appear when Notion not configured
- Core functionality works normally without Notion (verified with existing tests)
- Settings UI shows "Not Configured" message appropriately

**Task 6 - Connection Status Persistence (COMPLETED)**
- Extended `NotionConfig` with `last_validation_result` and `connection_status` fields
- Added `save_validation_result()` and `get_last_validation_result()` to ConfigManager
- Validation results persist across application restarts
- Updated protocol handlers to return cached status when available

**Task 7 - Testing & Validation (COMPLETED)**
- All 26 unit tests pass for notion client
- All 7 protocol handler tests pass
- All 17 existing config/dispatcher tests still pass (regression verified)
- Tests cover: validation, error classification, retry logic, graceful degradation, model serialization

### File List

**Backend (Python):**
- `roughcut/pyproject.toml` - Added notion-client dependency
- `roughcut/src/roughcut/backend/notion/models.py` - NEW: ValidationResult, ConnectionStatus, ErrorType models
- `roughcut/src/roughcut/backend/notion/client.py` - UPDATED: Full validation implementation with retry logic
- `roughcut/src/roughcut/protocols/handlers/notion.py` - NEW: Protocol handlers for validation
- `roughcut/src/roughcut/protocols/dispatcher.py` - UPDATED: Registered Notion handlers
- `roughcut/src/roughcut/config/models.py` - UPDATED: Extended NotionConfig with validation fields
- `roughcut/src/roughcut/config/settings.py` - UPDATED: Added validation persistence methods

**Frontend (Lua):**
- `roughcut/lua/ui/notion_settings.lua` - UPDATED: Added Test Connection UI, status indicators, validation dialogs

**Tests:**
- `roughcut/tests/unit/backend/notion/test_client.py` - UPDATED: Comprehensive tests for all validation logic
- `roughcut/tests/unit/protocols/handlers/test_notion.py` - NEW: Protocol handler tests

## Dev Agent Record
