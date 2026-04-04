# Story 2.2: Incremental Media Indexing

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a video editor,
I want to trigger incremental indexing when new assets are added,
so that my media database stays current without constant background processing.

## Acceptance Criteria

1. **Given** I have configured media folders
   **When** I trigger manual indexing
   **Then** The system scans only new or changed files since last index

2. **Given** Media indexing is in progress
   **When** The operation exceeds 5 seconds
   **Then** A blocking UI with progress indicator displays
   **And** I see clear status messages (e.g., "Indexing: epic_whoosh.wav")

3. **Given** Indexing is running
   **When** Progress updates occur
   **Then** Updates display every N items or every M seconds (never >5 seconds without update)

4. **Given** 100 new assets are being indexed
   **When** The process completes
   **Then** It finishes within 2 minutes on standard consumer hardware

## Tasks / Subtasks

- [ ] Implement file system scanning with change detection (AC: #1)
  - [ ] Create file scanner that walks configured folders
  - [ ] Implement file hash caching for change detection
  - [ ] Store last index timestamp for incremental scanning
- [ ] Create incremental indexing algorithm (AC: #1, #4)
  - [ ] Compare current files against cached index
  - [ ] Detect new files, modified files, and deleted files
  - [ ] Process only changed files (incremental approach)
- [ ] Implement progress reporting system (AC: #2, #3)
  - [ ] Create progress update mechanism in Python
  - [ ] Stream progress updates via JSON-RPC protocol
  - [ ] Ensure updates sent every N items or M seconds (max 5s gap)
- [ ] Build blocking UI with progress dialog (AC: #2)
  - [ ] Create Lua progress dialog component
  - [ ] Display current file being processed
  - [ ] Show progress bar with percentage/ETA
  - [ ] Allow cancellation (optional for MVP)
- [ ] Store indexed metadata in SpacetimeDB (AC: #1)
  - [ ] Create media asset data model
  - [ ] Implement database operations for insert/update/delete
  - [ ] Handle incremental updates efficiently
- [ ] Performance optimization (AC: #4)
  - [ ] Implement async file scanning
  - [ ] Optimize database batch operations
  - [ ] Benchmark and verify <2min for 100 assets
- [ ] Integration testing (AC: #1, #2, #3, #4)
  - [ ] Test incremental detection accuracy
  - [ ] Test progress reporting timing
  - [ ] Test performance requirements
  - [ ] Test database consistency

## Dev Notes

### Architecture Context

This story builds on Story 2.1 (Media Folder Configuration) to implement the **media indexing engine**. It scans configured folders, detects changes, and maintains an up-to-date asset database in SpacetimeDB.

**Key Architectural Requirements:**
- **Lua/Python Split**: GUI in Lua (`lua/roughcut/progress_dialog.lua`), logic in Python (`src/roughcut/backend/indexing/`)
- **JSON-RPC Protocol**: Progress updates streamed via JSON-RPC [Source: Architecture.md#Format Patterns]
- **Async Processing**: Python uses `async/await` for I/O operations [Source: Architecture.md#Additional Requirements]
- **Progress Reporting**: Updates every N items or M seconds, never >5 seconds without update [Source: epics.md Story 2.2]
- **Performance**: <2 minutes for 100 new assets on standard hardware (NFR1)

**Performance Constraints:**
- Must complete within 2 minutes for 100 assets
- Must send progress updates every N items or every M seconds
- Never hang without updates for more than 5 seconds

### Project Structure Notes

**Files to Create/Modify:**

```
src/roughcut/
├── backend/
│   ├── indexing/
│   │   ├── __init__.py
│   │   ├── scanner.py          # NEW: File system scanning
│   │   ├── incremental.py      # NEW: Change detection logic
│   │   ├── hash_cache.py       # NEW: File hash caching
│   │   └── indexer.py          # NEW: Main indexing orchestrator
│   ├── database/
│   │   ├── models.py           # MODIFY: Add MediaAsset dataclass
│   │   └── queries.py          # NEW: Database queries for assets
│   └── utils/
│       └── validators.py       # MODIFY: Add media file validation
├── protocols/
│   └── handlers/
│       └── media.py            # MODIFY: Add indexing handlers
└── config/
    └── settings.py             # MODIFY: Add indexing settings

lua/roughcut/
├── progress_dialog.lua         # NEW: Progress UI component
└── media_browser.lua           # MODIFY: Add indexing trigger button
```

**Integration Points:**
- Reads folder configuration from Story 2.1 (`MediaFolderConfig`)
- Uses SpacetimeDB client (`spacetime_client.py`) for asset storage
- Streams progress via JSON-RPC protocol (`protocols/json_rpc.py`)
- Displays progress in Lua GUI (`progress_dialog.lua`)

### Technical Requirements

**Data Model:**
```python
# src/roughcut/backend/database/models.py
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import List, Optional

@dataclass
class MediaAsset:
    """Represents an indexed media asset."""
    id: str  # UUID or hash-based ID
    file_path: Path
    file_name: str
    category: str  # "music", "sfx", "vfx"
    file_size: int
    modified_time: datetime
    file_hash: str  # For change detection
    ai_tags: List[str] = None  # Populated in Story 2.3
    created_at: datetime = None
    updated_at: datetime = None

@dataclass
class IndexState:
    """Tracks indexing state for incremental scans."""
    last_index_time: datetime
    folder_configs: dict  # category -> folder path
    total_assets_indexed: int
```

**File Hash Caching:**
```python
# src/roughcut/backend/indexing/hash_cache.py
import hashlib
from pathlib import Path
from typing import Dict

class HashCache:
    """Caches file hashes for efficient change detection."""
    
    def compute_hash(self, file_path: Path) -> str:
        """Compute MD5 hash of file content (fast enough for change detection)."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def has_changed(self, file_path: Path, cached_hash: str) -> bool:
        """Check if file has changed since last index."""
        current_hash = self.compute_hash(file_path)
        return current_hash != cached_hash
```

**Incremental Scanning Algorithm:**
```python
# src/roughcut/backend/indexing/incremental.py
from pathlib import Path
from typing import List, Set, Tuple
from dataclasses import dataclass

@dataclass
class ScanResult:
    new_files: List[Path]
    modified_files: List[Path]
    deleted_files: List[str]  # IDs of deleted assets

class IncrementalScanner:
    """Detects changes between current filesystem and cached index."""
    
    async def scan_for_changes(
        self,
        folder_paths: List[Path],
        cached_assets: List[MediaAsset]
    ) -> ScanResult:
        """
        Compare current folders against cached index.
        Returns lists of new, modified, and deleted files.
        """
        # Build lookup of cached assets by path
        cached_by_path = {str(a.file_path): a for a in cached_assets}
        
        new_files = []
        modified_files = []
        current_paths = set()
        
        # Scan all configured folders
        for folder in folder_paths:
            for file_path in self._scan_folder(folder):
                current_paths.add(str(file_path))
                
                if str(file_path) not in cached_by_path:
                    new_files.append(file_path)
                elif self._hash_cache.has_changed(
                    file_path, 
                    cached_by_path[str(file_path)].file_hash
                ):
                    modified_files.append(file_path)
        
        # Find deleted files
        deleted_files = [
            a.id for a in cached_assets 
            if str(a.file_path) not in current_paths
        ]
        
        return ScanResult(new_files, modified_files, deleted_files)
```

**Progress Reporting:**
```python
# src/roughcut/backend/indexing/indexer.py
import asyncio
from typing import Callable

class MediaIndexer:
    """Orchestrates media indexing with progress reporting."""
    
    def __init__(self, progress_callback: Callable[[dict], None]):
        self.progress_callback = progress_callback
        self.last_update_time = 0
        self.update_interval = 5  # seconds (NFR: never >5s without update)
    
    async def index_media(
        self,
        folder_configs: MediaFolderConfig
    ) -> IndexResult:
        """Index media folders with progress updates."""
        # 1. Scan for changes
        changes = await self._scan_for_changes(folder_configs)
        total_files = len(changes.new_files) + len(changes.modified_files)
        
        processed = 0
        for file_path in changes.new_files + changes.modified_files:
            # Index the file
            asset = await self._index_file(file_path)
            
            # Store in database
            await self._store_asset(asset)
            
            processed += 1
            
            # Send progress update every N items or M seconds
            await self._maybe_send_progress(
                current=processed,
                total=total_files,
                current_file=str(file_path.name)
            )
        
        # Clean up deleted files
        for asset_id in changes.deleted_files:
            await self._delete_asset(asset_id)
        
        return IndexResult(processed_count=processed)
    
    async def _maybe_send_progress(
        self, 
        current: int, 
        total: int, 
        current_file: str
    ):
        """Send progress update if enough time has passed or items processed."""
        now = asyncio.get_event_loop().time()
        items_since_update = current - self._last_update_count
        
        if (now - self.last_update_time >= self.update_interval or 
            items_since_update >= 10):  # Every 10 items or 5 seconds
            
            self.progress_callback({
                "type": "progress",
                "operation": "index_media",
                "current": current,
                "total": total,
                "message": f"Indexing: {current_file}"
            })
            
            self.last_update_time = now
            self._last_update_count = current
```

**JSON-RPC Protocol:**

Request (Lua → Python):
```json
{
  "method": "index_media",
  "params": {
    "incremental": true,
    "categories": ["music", "sfx", "vfx"]
  },
  "id": "req_001"
}
```

Progress Updates (Python → Lua):
```json
{
  "type": "progress",
  "operation": "index_media",
  "current": 23,
  "total": 100,
  "message": "Indexing: epic_whoosh.wav"
}
```

Final Response:
```json
{
  "result": {
    "indexed_count": 47,
    "new_count": 12,
    "modified_count": 3,
    "deleted_count": 2,
    "duration_ms": 45000
  },
  "error": null,
  "id": "req_001"
}
```

**SpacetimeDB Schema:**
```rust
// src/roughcut/backend/database/rust_modules/asset_module.rs
#[spacetimedb(table)]
pub struct MediaAsset {
    #[primary_key]
    pub id: String,
    pub user_id: String,
    pub file_path: String,
    pub file_name: String,
    pub category: String,  // "music", "sfx", "vfx"
    pub file_size: i64,
    pub file_hash: String,
    pub ai_tags: Vec<String>,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb(table)]
pub struct IndexState {
    #[primary_key]
    pub user_id: String,
    pub last_index_time: u64,
    pub total_assets_indexed: i64,
}
```

**Lua Progress Dialog:**
```lua
-- lua/roughcut/progress_dialog.lua
local function showIndexingProgress(dialog)
    -- Create blocking dialog with progress bar
    local win = ffi.new("UiDlg[1]")
    
    -- Set dialog properties
    win[0].WindowTitle = "Indexing Media Assets"
    win[0].Width = 500
    win[0].Height = 150
    
    -- Add progress bar
    local progressBar = dialog:AddControl({
        ID = "progressBar",
        Type = "ProgressBar",
        Width = 450,
        Height = 20
    })
    
    -- Add status label
    local statusLabel = dialog:AddControl({
        ID = "statusLabel",
        Type = "Label",
        Text = "Preparing to index..."
    })
    
    -- Show dialog (blocking)
    dialog:Show()
    
    return {
        updateProgress = function(current, total, message)
            local percent = math.floor((current / total) * 100)
            progressBar:SetValue(percent)
            statusLabel:SetText(message or string.format("Indexing: %d of %d", current, total))
        end,
        close = function()
            dialog:Hide()
        end
    }
end
```

### Dependencies on Previous Stories

**Story 2.1 Provides:**
- `MediaFolderConfig` with configured folder paths
- JSON-RPC protocol infrastructure
- Database connection and models
- Configuration persistence

**This Story Enables:**
- Story 2.3 (AI Tag Generation) — operates on indexed assets
- Story 2.4 (Asset Count Dashboard) — queries indexed assets
- Story 2.6 (Re-indexing Capability) — uses same scanning engine

### Implementation Guidelines

**Do:**
- Use `async/await` for file I/O operations
- Compute file hashes for change detection (MD5 is fast enough)
- Send progress updates via JSON-RPC (never >5s gap)
- Store absolute paths in database
- Use batch database operations for performance
- Handle file permission errors gracefully

**Don't:**
- Block the main thread during scanning
- Send binary file data through JSON-RPC (only metadata)
- Use relative paths for storage
- Index files without category validation
- Forget to handle deleted files (orphaned database entries)

**Performance Optimization:**
- Use `aiofiles` for async file operations if needed
- Batch database inserts (e.g., every 10-20 assets)
- Use file modification time as quick check before hashing
- Cache folder listings to avoid redundant scans

### Testing Strategy

**Unit Tests:**
```python
# tests/unit/backend/indexing/test_scanner.py
def test_scanner_finds_media_files():
    """Test scanner finds all supported media files."""

def test_incremental_detection():
    """Test change detection identifies new/modified/deleted files."""

def test_hash_caching():
    """Test hash cache correctly identifies unchanged files."""
```

**Integration Tests:**
```python
# tests/integration/test_indexing.py
def test_full_indexing_workflow():
    """Test end-to-end indexing with progress updates."""

def test_incremental_indexing():
    """Test only new/changed files are processed."""

def test_performance_requirement():
    """Verify 100 assets indexed in <2 minutes."""
```

**Performance Benchmark:**
```python
# tests/performance/test_indexing_perf.py
import time

def test_indexing_performance():
    """Benchmark indexing 100 assets completes within 2 minutes."""
    start = time.time()
    # ... index 100 test assets ...
    elapsed = time.time() - start
    assert elapsed < 120, f"Indexing took {elapsed}s, expected <120s"
```

### References

- **Epic Definition**: `/Users/niozerp/Documents/AI_context_stuff/repos/RoughCut/_bmad-output/planning-artifacts/epics.md` — Lines 347-370 (Story 2.2)
- **Architecture Decisions**: `/Users/niozerp/Documents/AI_context_stuff/repos/RoughCut/_bmad-output/planning-artifacts/architecture.md` — Lines 124-193 (Project Structure)
- **NFR Performance Requirements**: `/Users/niozerp/Documents/AI_context_stuff/repos/RoughCut/_bmad-output/planning-artifacts/epics.md` — Lines 68-71 (NFR1-5)
- **Story 2.1 Dependencies**: `/Users/niozerp/Documents/AI_context_stuff/repos/RoughCut/_bmad-output/implementation-artifacts/2-1-media-folder-configuration.md`
- **JSON-RPC Protocol**: `/Users/niozerp/Documents/AI_context_stuff/repos/RoughCut/_bmad-output/planning-artifacts/architecture.md` — Lines 341-400

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
