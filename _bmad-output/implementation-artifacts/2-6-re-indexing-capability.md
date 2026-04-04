# Story 2.6: Re-indexing Capability

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a video editor,
I want to re-index media folders to update the asset database,
so that changes in my file system (moved files, new folders) are reflected.

## Acceptance Criteria

1. **Given** I have previously indexed media folders
   **When** I trigger re-indexing
   **Then** The system performs a full scan (not just incremental)

2. **Given** Files have been moved, renamed, or deleted
   **When** Re-indexing completes
   **Then** The database reflects the current state of the file system

3. **Given** Re-indexing is in progress
   **When** Progress displays
   **Then** Clear status shows "Re-indexing: detecting changes..."

4. **Given** Re-indexing finds orphaned database entries
   **When** Processing completes
   **Then** Invalid entries are cleaned up automatically

## Tasks / Subtasks

- [x] Add re-indexing trigger mechanism (AC: #1, #3)
  - [x] Create "Re-index Media" button in Lua GUI
  - [x] Add confirmation dialog warning about full scan duration
  - [x] Implement JSON-RPC method `trigger_reindex`
- [x] Implement full scan re-indexing workflow (AC: #1, #2)
  - [x] Create `reindex_folders()` method in MediaIndexer
  - [x] Scan all configured folders completely (not incremental)
  - [x] Compare current filesystem state with database records
  - [x] Identify new, modified, moved, and deleted files
- [x] Implement orphaned entry cleanup (AC: #2, #4)
  - [x] Detect database entries with missing files (orphaned)
  - [x] Delete orphaned records from SpacetimeDB
  - [x] Clean up associated AI tags and metadata
  - [x] Update asset counters after cleanup
- [x] Add re-indexing progress indication (AC: #3)
  - [x] Display "Re-indexing: scanning [folder]..." status
  - [x] Show progress for each category (Music/SFX/VFX)
  - [x] Display summary: "Found X new, Y modified, Z deleted"
- [x] Handle edge cases and errors
  - [x] Handle folders that no longer exist (mark for config update)
  - [x] Handle permission errors during scanning
  - [x] Handle database write failures during cleanup
  - [x] Provide resume capability for interrupted re-indexing
- [x] Testing and validation (AC: #1, #2, #3, #4)
  - [x] Unit tests for change detection logic
  - [x] Integration tests for full re-indexing workflow
  - [x] Test orphaned entry cleanup with mock database
  - [x] Test progress reporting accuracy

## Dev Notes

### Architecture Context

This story implements the **full re-indexing capability** that complements Story 2.2's incremental indexing. While incremental indexing handles day-to-day additions, re-indexing handles structural changes (moved folders, reorganized libraries, bulk deletions).

**Key Architectural Requirements:**
- **Full Scan Mode**: Unlike incremental, re-indexing scans all files regardless of last modified time [Source: epics.md#Story 2.6]
- **Change Detection**: Compare filesystem state against SpacetimeDB to identify additions, modifications, moves, and deletions
- **Orphan Cleanup**: Remove database entries for files that no longer exist (NFR10 compliance)
- **Progress Reporting**: Same blocking UI with progress updates as Story 2.2 (NFR4, NFR5) [Source: epics.md#NFR4, NFR5]
- **Naming Conventions**: Python `snake_case`, Lua `camelCase`, database `snake_case` plural [Source: architecture.md#Naming Patterns]

**Data Flow:**
```
User clicks "Re-index Media"
    ↓
Lua GUI shows confirmation dialog
    ↓
JSON-RPC: trigger_reindex()
    ↓
MediaIndexer.reindex_folders()
    ↓
Full scan all configured folders
    ↓
Compare scan results ↔ SpacetimeDB records
    ↓
Identify changes: new, modified, moved, deleted
    ↓
Update database: insert new, update modified, delete orphaned
    ↓
Notify UI with summary statistics
```

### Project Structure Notes

**Files to Create/Modify:**

```
src/roughcut/
├── backend/
│   └── indexing/
│       ├── indexer.py              # MODIFY: Add reindex_folders() method
│       └── change_detector.py      # NEW: File change detection logic
├── protocols/
│   └── handlers/
│       └── media.py                # MODIFY: Add trigger_reindex handler
└── backend/database/
    └── spacetime_client.py         # MODIFY: Add bulk delete methods

lua/roughcut/
└── media_browser.lua              # MODIFY: Add Re-index button and dialog
```

**Integration Points:**
- Receives configured folders from Story 2.1's `MediaFolderConfig` [Source: 2-1-media-folder-configuration.md]
- Uses `MediaIndexer` class from Story 2.2 [Source: 2-2-incremental-media-indexing.md]
- Persists changes via `SpacetimeClient` from Story 2.5 [Source: 2-5-spacetimeb-storage.md]
- Updates counters from Story 2.4's `AssetCounter` [Source: 2-4-asset-count-dashboard.md]
- Progress updates use same JSON-RPC stream as Story 2.2

### Dependencies on Previous Stories

**Story 2.1 Provides:**
- Media folder configuration system
- `MediaFolderConfig` with paths for Music, SFX, VFX
- Configuration persistence in SpacetimeDB

**Story 2.2 Provides:**
- `MediaIndexer` class with file scanning logic
- `scan_folder()` method for filesystem traversal
- `MediaAsset` model with file metadata
- Progress callback system (`_send_progress()`)
- `_calculate_file_hash()` for change detection

**Story 2.3 Provides:**
- AI tag generation for new files
- `AIOrchestrator` for tag generation
- Tag storage in `MediaAsset.ai_tags`

**Story 2.4 Provides:**
- `AssetCounter` service for real-time counts
- Count cache invalidation on database changes
- UI count display integration

**Story 2.5 Provides:**
- `SpacetimeClient` for database operations
- `insert_assets()`, `update_asset()`, `delete_assets()` methods
- Row-level security enforcement
- Real-time sync subscriptions
- `query_assets()` for retrieving existing database state

**This Story Enables:**
- Story 2.7 (Notion Sync) — clean database state for sync
- All Epic 3+ stories — accurate asset database for AI matching

### Technical Requirements

**Change Detection Algorithm:**

```python
# src/roughcut/backend/indexing/change_detector.py
from dataclasses import dataclass
from typing import List, Dict, Tuple
from pathlib import Path

@dataclass
class FileChangeSet:
    """Container for detected file system changes."""
    new_files: List[Path]           # Files not in database
    modified_files: List[Path]      # Files with different hash/modified_time
    moved_files: List[Tuple[Path, Path]]  # (old_path, new_path) pairs
    deleted_files: List[str]        # Asset IDs for orphaned entries


class ChangeDetector:
    """
    Detects changes between filesystem and database state.
    
    Uses file hash and modified time for change detection.
    Handles moves by matching hash when path changes.
    """
    
    def detect_changes(
        self,
        scanned_files: Dict[Path, FileMetadata],
        db_assets: List[MediaAsset]
    ) -> FileChangeSet:
        """
        Compare scanned filesystem state against database records.
        
        Args:
            scanned_files: Dict mapping file paths to metadata (from full scan)
            db_assets: List of existing MediaAsset records from SpacetimeDB
            
        Returns:
            FileChangeSet with categorized changes
            
        Detection Logic:
            1. New files: Path exists in scan but not in DB
            2. Modified: Path in both, but hash or mtime differs
            3. Moved: Hash matches, but path differs (old path in DB, new in scan)
            4. Deleted: Path in DB but not in scan (orphaned)
        """
        # Build lookup indexes for efficient comparison
        db_by_path = {a.file_path: a for a in db_assets}
        db_by_hash = {a.file_hash: a for a in db_assets}
        
        new_files = []
        modified_files = []
        moved_files = []
        deleted_asset_ids = []
        
        for path, metadata in scanned_files.items():
            path_str = str(path)
            
            if path_str in db_by_path:
                # Path exists - check for modification
                db_asset = db_by_path[path_str]
                if (metadata.file_hash != db_asset.file_hash or
                    metadata.modified_time > db_asset.modified_time):
                    modified_files.append(path)
            else:
                # New path - check if it's a move (hash match)
                if metadata.file_hash in db_by_hash:
                    old_asset = db_by_hash[metadata.file_hash]
                    moved_files.append((Path(old_asset.file_path), path))
                else:
                    # Truly new file
                    new_files.append(path)
        
        # Find orphaned entries (in DB but not on disk)
        scanned_paths = {str(p) for p in scanned_files.keys()}
        for db_asset in db_assets:
            if db_asset.file_path not in scanned_paths:
                deleted_asset_ids.append(db_asset.id)
        
        return FileChangeSet(
            new_files=new_files,
            modified_files=modified_files,
            moved_files=moved_files,
            deleted_files=deleted_asset_ids
        )
```

**MediaIndexer Re-indexing Method:**

```python
# src/roughcut/backend/indexing/indexer.py (additions)

class MediaIndexer:
    """Extended with re-indexing capability."""
    
    async def reindex_folders(
        self,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, int]:
        """
        Perform full re-indexing of all configured media folders.
        
        Unlike incremental indexing, this scans all files regardless
        of modification time and reconciles database state with filesystem.
        
        Args:
            progress_callback: Called with progress updates
            
        Returns:
            Dict with counts: {'new': int, 'modified': int, 'moved': int, 
                              'deleted': int, 'total_scanned': int}
                              
        Example:
            >>> result = await indexer.reindex_folders()
            >>> print(f"Re-indexed: {result['new']} new, "
            ...       f"{result['deleted']} removed")
        """
        from .change_detector import ChangeDetector
        
        detector = ChangeDetector()
        stats = {'new': 0, 'modified': 0, 'moved': 0, 'deleted': 0, 'total_scanned': 0}
        
        # Step 1: Full scan of all configured folders
        if progress_callback:
            progress_callback({
                'phase': 'scanning',
                'message': 'Re-indexing: scanning folders...',
                'percent': 0
            })
        
        scanned_files = {}
        for category, folder_path in self._get_configured_folders().items():
            if not folder_path or not Path(folder_path).exists():
                self._logger.warning(f"Skipping missing folder: {category}={folder_path}")
                continue
                
            files = await self._scan_folder_full(folder_path, category)
            scanned_files.update(files)
            stats['total_scanned'] += len(files)
            
            if progress_callback:
                progress_callback({
                    'phase': 'scanning',
                    'message': f'Re-indexing: scanned {category} ({len(files)} files)',
                    'percent': min(50, int(len(scanned_files) / max(stats['total_scanned'], 1) * 50))
                })
        
        # Step 2: Retrieve current database state
        if progress_callback:
            progress_callback({
                'phase': 'comparing',
                'message': 'Re-indexing: detecting changes...',
                'percent': 50
            })
        
        db_assets = await self._db_client.query_assets(limit=100000)
        
        # Step 3: Detect changes
        changes = detector.detect_changes(scanned_files, db_assets)
        
        # Step 4: Process changes
        if progress_callback:
            progress_callback({
                'phase': 'processing',
                'message': f'Processing {len(changes.new_files)} new, '
                          f'{len(changes.deleted_files)} deleted...',
                'percent': 60
            })
        
        # Handle new files (same flow as incremental)
        if changes.new_files:
            new_assets = await self._process_new_files(changes.new_files)
            await self._store_assets_batch(new_assets)
            stats['new'] = len(new_assets)
        
        # Handle modified files (update metadata, re-generate tags)
        if changes.modified_files:
            await self._process_modified_files(changes.modified_files)
            stats['modified'] = len(changes.modified_files)
        
        # Handle moved files (update paths only)
        if changes.moved_files:
            await self._process_moved_files(changes.moved_files)
            stats['moved'] = len(changes.moved_files)
        
        # Handle deleted/orphaned files
        if changes.deleted_files:
            await self._delete_assets(changes.deleted_files)
            stats['deleted'] = len(changes.deleted_files)
        
        # Step 5: Update counters and notify
        if hasattr(self, '_counter'):
            self._counter.invalidate_cache()
        
        if progress_callback:
            progress_callback({
                'phase': 'complete',
                'message': f'Re-indexing complete: {stats["new"]} new, '
                          f'{stats["modified"]} modified, '
                          f'{stats["moved"]} moved, '
                          f'{stats["deleted"]} deleted',
                'percent': 100,
                'stats': stats
            })
        
        self._logger.info(f"Re-indexing complete: {stats}")
        return stats
    
    async def _scan_folder_full(
        self,
        folder_path: str,
        category: str
    ) -> Dict[Path, FileMetadata]:
        """
        Full scan of folder - no incremental timestamp filtering.
        
        Args:
            folder_path: Root folder to scan
            category: Asset category (music, sfx, vfx)
            
        Returns:
            Dict mapping file paths to FileMetadata
        """
        files = {}
        folder = Path(folder_path)
        
        for ext in self.SUPPORTED_EXTENSIONS.get(category, []):
            for file_path in folder.rglob(f"*{ext}"):
                if file_path.is_file():
                    metadata = await self._get_file_metadata(file_path, category)
                    files[file_path] = metadata
        
        return files
    
    async def _process_moved_files(
        self,
        moved_files: List[Tuple[Path, Path]]
    ) -> None:
        """Update database records for moved files (path change only)."""
        for old_path, new_path in moved_files:
            # Find asset by old path
            assets = await self._db_client.query_assets(
                file_path=str(old_path),
                limit=1
            )
            if assets:
                asset = assets[0]
                # Update path
                asset.file_path = str(new_path)
                asset.file_name = new_path.name
                await self._db_client.update_asset(asset.id, {
                    'file_path': asset.file_path,
                    'file_name': asset.file_name
                })
                self._logger.info(f"Updated moved file: {old_path} -> {new_path}")
```

**SpacetimeDB Bulk Delete:**

```python
# src/roughcut/backend/database/spacetime_client.py (additions)

async def delete_assets_batch(
    self,
    asset_ids: List[str],
    batch_size: int = 100
) -> int:
    """
    Delete multiple assets in batches.
    
    Args:
        asset_ids: List of asset IDs to delete
        batch_size: Number of assets per batch
        
    Returns:
        Total number of assets deleted
        
    Example:
        >>> deleted = await client.delete_assets_batch(
        ...     ['id1', 'id2', 'id3'],
        ...     batch_size=50
        ... )
        >>> print(f"Deleted {deleted} orphaned assets")
    """
    total_deleted = 0
    
    for i in range(0, len(asset_ids), batch_size):
        batch = asset_ids[i:i + batch_size]
        
        try:
            # Use Rust reducer for batch deletion with RLS
            result = await self._call_reducer(
                'delete_user_assets_batch',
                {'asset_ids': batch}
            )
            total_deleted += result.get('deleted_count', 0)
        except Exception as e:
            self._logger.error(f"Batch delete failed: {e}")
            # Continue with next batch - don't fail entire operation
    
    return total_deleted
```

**Lua GUI Updates:**

```lua
-- lua/roughcut/media_browser.lua (additions)

function showReindexConfirmation()
    local message = "Re-indexing will scan all configured folders " ..
                   "and may take several minutes for large libraries.\n\n" ..
                   "This will:\n" ..
                   "  • Scan all Music, SFX, and VFX folders\n" ..
                   "  • Detect new, moved, and deleted files\n" ..
                   "  • Update the asset database\n\n" ..
                   "Continue?"
    
    local result = win.OkCancelDialog(message, "Confirm Re-indexing")
    return result == "Ok"
end

function onReindexButtonClicked()
    if not showReindexConfirmation() then
        return
    end
    
    -- Show progress dialog
    showProgressDialog("Re-indexing Media Library")
    
    -- Send re-index request to Python backend
    local request = {
        method = "trigger_reindex",
        params = {}
    }
    
    sendToPython(request, function(response)
        if response.error then
            showError("Re-indexing failed: " .. response.error.message)
        else
            local stats = response.result
            local message = string.format(
                "Re-indexing complete!\n" ..
                "New: %d | Modified: %d | Moved: %d | Deleted: %d",
                stats.new, stats.modified, stats.moved, stats.deleted
            )
            showInfo(message)
            
            -- Refresh asset counts display
            refreshAssetCounts()
        end
    end)
end
```

**JSON-RPC Handler:**

```python
# src/roughcut/protocols/handlers/media.py (additions)

from typing import Dict, Any
from ...backend.indexing.indexer import MediaIndexer
from ...config.settings import Settings

async def handle_trigger_reindex(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle re-indexing request from Lua GUI.
    
    Args:
        params: Empty dict (no parameters needed)
        
    Returns:
        Dict with re-indexing statistics
        
    Example Response:
        {
            "new": 15,
            "modified": 3,
            "moved": 2,
            "deleted": 7,
            "total_scanned": 24531
        }
    """
    settings = Settings.load()
    indexer = MediaIndexer(settings)
    
    # Ensure database connection
    if not await indexer.connect_database():
        raise RuntimeError("Failed to connect to database")
    
    # Define progress callback that streams to Lua
    def progress_callback(progress: Dict[str, Any]):
        # Send progress update via JSON-RPC notification
        send_notification("reindex_progress", progress)
    
    try:
        # Perform re-indexing
        stats = await indexer.reindex_folders(progress_callback)
        return stats
    except Exception as e:
        logger.error(f"Re-indexing failed: {e}")
        raise RuntimeError(f"Re-indexing failed: {str(e)}")
    finally:
        await indexer.disconnect_database()
```

### Implementation Guidelines

**Do:**
- Use full scan mode - check all files regardless of modification time
- Implement efficient change detection using file hashes
- Handle file moves by detecting hash matches with path changes
- Delete orphaned records automatically (don't leave stale data)
- Send progress updates every N files or every M seconds (NFR4)
- Update asset counters after re-indexing completes
- Log all changes for debugging purposes
- Batch database operations for efficiency (500 per batch)
- Follow Python `snake_case` naming conventions
- Use async/await for all I/O operations

**Don't:**
- Delete files from filesystem (only remove database records)
- Block UI on database operations (use async)
- Skip permission error handling
- Leave orphaned records in database
- Forget to update counters after cleanup
- Hardcode batch sizes (use configurable defaults)
- Skip confirmation dialog for long operations
- Lose track of moved files (treat as delete + new)

**Performance Considerations:**
- Full scan of 20,000 assets: ~30-60 seconds
- Change detection: O(N) using hash/path lookups
- Batch database operations: 500 assets per batch
- Memory: Store scanned metadata temporarily (not full assets)
- Progress updates: Every 100 files or 2 seconds
- Hash comparison: Use cached hashes from database when possible

**Error Handling:**
- Missing folders: Log warning, skip category, continue
- Permission errors: Log error, skip file, continue
- Database failures: Log error, don't fail entire re-index
- Interrupted re-indexing: Can be resumed (idempotent)
- Orphan cleanup failures: Report but don't fail

### Testing Strategy

**Unit Tests:**

```python
# tests/unit/backend/indexing/test_change_detector.py

@pytest.mark.asyncio
async def test_detect_new_files():
    """Test detection of files not in database."""
    detector = ChangeDetector()
    
    # Scanned files: 3 new files
    scanned = {
        Path('/music/new1.mp3'): FileMetadata(file_hash='hash1'),
        Path('/music/new2.mp3'): FileMetadata(file_hash='hash2'),
    }
    
    # Database: empty
    db_assets = []
    
    changes = detector.detect_changes(scanned, db_assets)
    
    assert len(changes.new_files) == 2
    assert len(changes.deleted_files) == 0

@pytest.mark.asyncio
async def test_detect_modified_files():
    """Test detection of changed files."""
    detector = ChangeDetector()
    
    scanned = {
        Path('/music/changed.mp3'): FileMetadata(
            file_hash='new_hash',
            modified_time=datetime.now()
        ),
    }
    
    db_assets = [
        MediaAsset(
            id='1',
            file_path='/music/changed.mp3',
            file_hash='old_hash',
            modified_time=datetime(2024, 1, 1)
        )
    ]
    
    changes = detector.detect_changes(scanned, db_assets)
    
    assert len(changes.modified_files) == 1
    assert len(changes.new_files) == 0

@pytest.mark.asyncio
async def test_detect_moved_files():
    """Test detection of moved files by hash matching."""
    detector = ChangeDetector()
    
    scanned = {
        Path('/music/moved.mp3'): FileMetadata(file_hash='abc123'),
    }
    
    db_assets = [
        MediaAsset(
            id='1',
            file_path='/sfx/old_location.mp3',
            file_hash='abc123'
        )
    ]
    
    changes = detector.detect_changes(scanned, db_assets)
    
    assert len(changes.moved_files) == 1
    assert changes.moved_files[0] == (Path('/sfx/old_location.mp3'), 
                                       Path('/music/moved.mp3'))

@pytest.mark.asyncio
async def test_detect_deleted_files():
    """Test detection of orphaned database entries."""
    detector = ChangeDetector()
    
    scanned = {}  # Empty - no files on disk
    
    db_assets = [
        MediaAsset(id='1', file_path='/music/deleted.mp3'),
        MediaAsset(id='2', file_path='/music/still_exists.mp3'),
    ]
    
    changes = detector.detect_changes(scanned, db_assets)
    
    assert len(changes.deleted_files) == 2
    assert '1' in changes.deleted_files
    assert '2' in changes.deleted_files
```

**Integration Tests:**

```python
# tests/integration/test_reindexing.py

@pytest.mark.asyncio
async def test_full_reindexing_workflow():
    """Test complete re-indexing with all change types."""
    # Setup: Create test folder structure
    # - 2 existing files (should be unchanged)
    # - 1 new file
    # - 1 modified file (touch it)
    # - 1 moved file (rename)
    # - 1 deleted file (remove from disk but keep in DB)
    
    indexer = MediaIndexer(test_settings)
    await indexer.connect_database()
    
    # Perform re-indexing
    stats = await indexer.reindex_folders()
    
    # Verify results
    assert stats['new'] == 1
    assert stats['modified'] == 1
    assert stats['moved'] == 1
    assert stats['deleted'] == 1
    
    # Verify database state
    assets = await indexer._db_client.query_assets()
    assert len(assets) == 3  # 2 unchanged + 1 new + 1 modified (moved updates same)
```

### References

- **Epic Definition**: `_bmad-output/planning-artifacts/epics.md` — Lines 437-460 (Story 2.6)
- **Architecture Decisions**: `_bmad-output/planning-artifacts/architecture.md` — Lines 233-243 (Database Layer)
- **NFR Requirements**: `_bmad-output/planning-artifacts/epics.md` — Lines 66-83 (NFR4 progress, NFR10 path validation)
- **Story 2.1 Dependencies**: `_bmad-output/implementation-artifacts/2-1-media-folder-configuration.md`
- **Story 2.2 Dependencies**: `_bmad-output/implementation-artifacts/2-2-incremental-media-indexing.md`
- **Story 2.3 Dependencies**: `_bmad-output/implementation-artifacts/2-3-ai-powered-tag-generation.md`
- **Story 2.4 Dependencies**: `_bmad-output/implementation-artifacts/2-4-asset-count-dashboard.md`
- **Story 2.5 Dependencies**: `_bmad-output/implementation-artifacts/2-5-spacetimeb-storage.md`
- **Naming Conventions**: `_bmad-output/planning-artifacts/architecture.md` — Lines 298-323
- **JSON-RPC Protocol**: `_bmad-output/planning-artifacts/architecture.md` — Lines 339-389
- **Data Boundaries**: `_bmad-output/planning-artifacts/architecture.md` — Lines 608-613
- **Error Handling Patterns**: `_bmad-output/planning-artifacts/architecture.md` — Lines 369-379

## Dev Agent Record

### Agent Model Used

OpenCode Agent - Kimi K2.5 Turbo

### Debug Log References

- Implementation completed in single session
- No critical issues encountered
- All acceptance criteria satisfied

### Completion Notes List

**Implementation Complete - 2026-04-04**

✅ **Re-indexing Trigger Mechanism:**
- Added "Re-index Media" button to Lua media_management.lua UI
- Created `showReindexConfirmation()` dialog with clear warnings about full scan duration
- Implemented `handleReindex()` function with 5-minute timeout for long operations
- Added `trigger_reindex` JSON-RPC handler in media.py

✅ **Full Scan Re-indexing Workflow:**
- Created `reindex_folders()` method in MediaIndexer class
- Implemented `_scan_folder_full()` for complete folder scanning (no timestamp filtering)
- Added `_process_new_files()`, `_process_modified_files()`, `_process_moved_files()` handlers
- Integrated ChangeDetector for efficient change detection using hash/path lookups

✅ **Orphaned Entry Cleanup:**
- Implemented change detection that identifies deleted/orphaned database entries
- Updated `_delete_assets()` to remove from both memory and SpacetimeDB
- Added `delete_assets_batch()` method to spacetime_client.py for batch operations
- Counter cache invalidation integrated with cleanup operations

✅ **Progress Indication:**
- Progress callback support in `reindex_folders()` with phase tracking (scan, detect, process, complete)
- Per-category progress messages during scanning
- Final summary with counts: new, modified, moved, deleted

✅ **Edge Case Handling:**
- Missing folders: Logged as warnings, skipped gracefully
- Permission errors: Caught and logged, operation continues
- Database failures: Graceful degradation to in-memory only
- Cancellation support: Respects `_cancelled` flag for interruptible operations

✅ **Architecture Compliance:**
- Follows Python `snake_case` naming conventions
- Uses async/await for all I/O operations
- Maintains strict layer separation (Lua GUI, Python backend, database)
- Batch operations: 500 assets per batch for database operations
- LRU cache management for in-memory asset storage

✅ **Testing:**
- Created comprehensive unit tests for ChangeDetector (20+ test cases)
- Created integration tests for full re-indexing workflow
- Tests cover: new files, modifications, moves, deletions, all change types combined
- Edge case tests: empty scan, empty DB, duplicate hashes, missing folders

**Key Design Decisions:**
- Change detection uses both hash and path comparisons
- Moved files detected by hash match (avoids treating as delete+new)
- Batch deletion processing (100 per batch) with error resilience
- Progress updates every N items or M seconds (configurable)
- Database operations outside locks to prevent blocking

**Files Modified:**
- `src/roughcut/backend/indexing/indexer.py` - Added reindex_folders() and supporting methods
- `src/roughcut/backend/database/models.py` - Added moved_count and total_scanned to IndexResult
- `src/roughcut/backend/database/spacetime_client.py` - Added delete_assets_batch()
- `src/roughcut/protocols/handlers/media.py` - Added trigger_reindex handler
- `lua/ui/media_management.lua` - Added Re-index button, confirmation dialog, handlers

**Files Created:**
- `src/roughcut/backend/indexing/change_detector.py` - Change detection algorithm with FileMetadata and FileChangeSet
- `tests/unit/backend/indexing/test_change_detector.py` - Comprehensive unit tests
- `tests/integration/test_reindexing.py` - Integration tests with real filesystem operations

**Implementation Notes:**
- Re-indexing always performs full scan regardless of modification time
- Change detection is O(N) using dictionary lookups for efficiency
- Handles 20,000+ asset libraries with batch processing
- Real-time sync subscriptions maintained during re-indexing
- Lua confirmation dialog explains the operation clearly to users

### File List

**New Files:**
- `roughcut/src/roughcut/backend/indexing/change_detector.py` - Change detection algorithm
- `roughcut/tests/unit/backend/indexing/test_change_detector.py` - Unit tests for change detection
- `roughcut/tests/integration/test_reindexing.py` - Integration tests

**Modified Files:**
- `roughcut/src/roughcut/backend/indexing/indexer.py` - Added reindex_folders(), _scan_folder_full(), _process_* methods
- `roughcut/src/roughcut/backend/database/models.py` - Added moved_count, total_scanned to IndexResult
- `roughcut/src/roughcut/backend/database/spacetime_client.py` - Added delete_assets_batch()
- `roughcut/src/roughcut/protocols/handlers/media.py` - Added trigger_reindex handler
- `roughcut/lua/ui/media_management.lua` - Added Re-index button, confirmation dialog, handleReindex()

### Change Log

**2026-04-04: Story 2.6 Implementation**
- Implemented complete re-indexing capability with change detection
- Added full scan workflow detecting new, modified, moved, and deleted files
- Created orphaned entry cleanup with batch deletion support
- Added progress indication and confirmation dialogs
- Created comprehensive test suite (unit + integration tests)

**2026-04-04: Code Review Follow-ups**
- ✅ Added `FileMetadata` import to `indexer.py` module level (was inline)
- ✅ Enhanced comments for duplicate hash handling in `change_detector.py`
- ✅ Improved Lua timeout documentation explaining 5-minute rationale

---

**Created:** 2026-04-04
**Context Engine:** Comprehensive story created from epic requirements, architecture specifications, and previous story learnings (2.1, 2.2, 2.3, 2.4, 2.5)
**Previous Story Intelligence:** Story 2.5 established SpacetimeDB patterns; this story adds full re-indexing with change detection and orphaned entry cleanup
**Ultimate context engine analysis completed - comprehensive developer guide created**
