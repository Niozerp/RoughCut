# Story 2.1: Media Folder Configuration

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a video editor,
I want to configure parent folders for Music, SFX, and VFX media categories,
so that RoughCut knows where to look for my asset libraries.

## Acceptance Criteria

1. **Given** I navigate to "Manage Media" from the main window
   **When** I access folder configuration
   **Then** I can select parent folders for Music, SFX, and VFX categories separately

2. **Given** I am configuring media folders
   **When** I select a folder path
   **Then** The system displays the absolute path for confirmation
   **And** Validates that the folder exists and is accessible

3. **Given** I have configured media folders
   **When** I return to media management later
   **Then** My folder paths persist between sessions

## Tasks / Subtasks

- [ ] Create configuration system for media folder paths (AC: #1, #2, #3)
  - [ ] Define data model for media folder configuration
  - [ ] Implement folder path validation (exists, accessible, absolute)
  - [ ] Create settings persistence mechanism
- [ ] Implement Lua GUI for folder configuration (AC: #1)
  - [ ] Create folder selection dialog
  - [ ] Display configured paths with category labels
  - [ ] Handle user interactions for folder selection
- [ ] Implement Python backend configuration handlers (AC: #2, #3)
  - [ ] Create JSON-RPC protocol handlers for configuration operations
  - [ ] Implement configuration storage in SpacetimeDB
  - [ ] Add validation logic for folder paths
- [ ] Integration testing (AC: #1, #2, #3)
  - [ ] Test folder selection flow end-to-end
  - [ ] Verify path validation catches invalid paths
  - [ ] Verify persistence across sessions

## Dev Notes

### Architecture Context

This story establishes the **Media Asset Management** foundation for Epic 2. It creates the configuration layer that all subsequent indexing and tagging stories depend on.

**Key Architectural Requirements:**
- **Lua/Python Split**: GUI in Lua (`lua/roughcut/media_browser.lua`), logic in Python (`src/roughcut/backend/indexing/`)
- **JSON-RPC Protocol**: All communication uses JSON-RPC over stdin/stdout [Source: Architecture.md#Format Patterns]
- **SpacetimeDB Storage**: Configuration persisted in SpacetimeDB for real-time sync [Source: Architecture.md#Decision 2]
- **Naming Conventions**: 
  - Python: `snake_case` functions/variables, `PascalCase` classes
  - Lua: `camelCase` functions/variables, `PascalCase` GUI components
  - Database: `snake_case` plural tables [Source: Architecture.md#Naming Patterns]

### Project Structure Notes

**Files to Create/Modify:**

```
src/roughcut/
├── backend/
│   ├── indexing/
│   │   ├── __init__.py
│   │   ├── config.py          # NEW: Media folder configuration models & storage
│   │   └── validator.py       # NEW: Path validation utilities
│   └── database/
│       └── models.py          # MODIFY: Add MediaFolderConfig dataclass
├── config/
│   ├── settings.py            # MODIFY: Add media folder settings schema
│   └── schema.py              # MODIFY: Add validation schemas
└── protocols/
    └── handlers/
        └── media.py           # NEW: JSON-RPC handlers for media operations

lua/roughcut/
├── media_browser.lua          # NEW: Main media management window
└── folder_dialog.lua          # NEW: Folder selection dialog component
```

**Integration Points:**
- Protocol handlers in `src/roughcut/protocols/handlers/media.py` receive requests from Lua
- Database operations go through `src/roughcut/backend/database/spacetime_client.py`
- Configuration validation uses `src/roughcut/config/schema.py` (Pydantic)

### Technical Requirements

**Data Model:**
```python
# src/roughcut/backend/database/models.py
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

@dataclass
class MediaFolderConfig:
    """Configuration for media category folders."""
    music_folder: Optional[Path] = None
    sfx_folder: Optional[Path] = None
    vfx_folder: Optional[Path] = None
    
    def validate(self) -> dict[str, str]:
        """Validate all configured paths. Returns dict of errors by category."""
        errors = {}
        for category, path in [
            ("music", self.music_folder),
            ("sfx", self.sfx_folder),
            ("vfx", self.vfx_folder)
        ]:
            if path is not None:
                if not path.exists():
                    errors[category] = f"Path does not exist: {path}"
                elif not path.is_dir():
                    errors[category] = f"Path is not a directory: {path}"
                elif not path.is_absolute():
                    errors[category] = f"Path must be absolute: {path}"
        return errors
```

**JSON-RPC Protocol:**

Request format (Lua → Python):
```json
{
  "method": "get_media_folders",
  "params": {},
  "id": "req_001"
}
```

Response format (Python → Lua):
```json
{
  "result": {
    "music_folder": "/Users/editor/Music",
    "sfx_folder": "/Users/editor/SFX",
    "vfx_folder": null
  },
  "error": null,
  "id": "req_001"
}
```

Error format:
```json
{
  "result": null,
  "error": {
    "code": "INVALID_PATH",
    "category": "validation",
    "message": "Music folder path does not exist: /invalid/path",
    "recoverable": true,
    "suggestion": "Please select a valid directory path"
  },
  "id": "req_001"
}
```

**SpacetimeDB Schema:**
```rust
// src/roughcut/backend/database/rust_modules/asset_module.rs
use spacetimedb::{table, ReducerContext};
use spacetimedb::spacetimedb;

#[spacetimedb(table)]
pub struct MediaFolderConfig {
    #[primary_key]
    pub id: u64,
    pub user_id: String,
    pub music_folder: Option<String>,
    pub sfx_folder: Option<String>,
    pub vfx_folder: Option<String>,
    pub updated_at: u64, // timestamp
}
```

### Dependencies on Previous Stories

**Epic 1 Completion Provides:**
- JSON-RPC protocol infrastructure (`src/roughcut/protocols/`)
- SpacetimeDB client connection (`src/roughcut/backend/database/spacetime_client.py`)
- Configuration management system (`src/roughcut/config/`)
- Lua main window structure (`lua/roughcut/main_window.lua`)
- Error handling patterns and structured error objects

**This Story Enables:**
- Story 2.2 (Incremental Media Indexing) — needs folder paths to scan
- Story 2.3 (AI Tag Generation) — operates on indexed media from these folders
- Story 2.4 (Asset Count Dashboard) — displays counts for configured folders

### Implementation Guidelines

**Do:**
- Use `pathlib.Path` for all path operations (not raw strings)
- Validate paths are absolute before storage
- Store paths as strings in SpacetimeDB (Path objects don't serialize)
- Return errors with actionable suggestions for users
- Use Pydantic for configuration schema validation
- Follow Python `snake_case` and Lua `camelCase` naming conventions

**Don't:**
- Accept relative paths from Lua layer
- Store paths without validation
- Mix naming conventions within a layer
- Use Lua global variables for configuration state
- Import Python modules from Lua directory or vice versa

### Testing Strategy

**Unit Tests:**
```python
# tests/unit/backend/indexing/test_config.py
def test_media_folder_config_validation():
    """Test path validation catches invalid paths."""
    
def test_media_folder_persistence():
    """Test configuration saves and loads correctly."""
    
def test_json_rpc_handlers():
    """Test protocol handlers return correct responses."""
```

**Integration Tests:**
```python
# tests/integration/test_media_folder_config.py
def test_folder_selection_flow():
    """Test end-to-end folder selection via Lua → Python → SpacetimeDB."""
    
def test_path_validation_integration():
    """Test that invalid paths are rejected before storage."""
```

### References

- **Epic Definition**: `/Users/niozerp/Documents/AI_context_stuff/repos/RoughCut/_bmad-output/planning-artifacts/epics.md` — Lines 322-346 (Story 2.1)
- **Architecture Decisions**: `/Users/niozerp/Documents/AI_context_stuff/repos/RoughCut/_bmad-output/planning-artifacts/architecture.md` — Lines 124-193 (Project Structure), Lines 298-389 (Naming/Format Patterns)
- **Lua/Python Protocol**: `/Users/niozerp/Documents/AI_context_stuff/repos/RoughCut/_bmad-output/planning-artifacts/architecture.md` — Lines 341-400 (JSON-RPC specification)
- **Database Layer**: `/Users/niozerp/Documents/AI_context_stuff/repos/RoughCut/_bmad-output/planning-artifacts/architecture.md` — Lines 509-515 (SpacetimeDB models)
- **Story 1.x Patterns**: `/Users/niozerp/Documents/AI_context_stuff/repos/RoughCut/_bmad-output/implementation-artifacts/1-*.md` — JSON-RPC implementation patterns, error handling conventions

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
