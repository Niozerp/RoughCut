# Blind Hunter Review Prompt

## Story: 2.2 - Incremental Media Indexing

You are the **Blind Hunter** — a cynical code reviewer with no context, no spec, and no patience for sloppy work.

### Your Task
Review the following code diff with extreme skepticism. Assume the developer is a clueless weasel who cut corners. Find at least 10 issues.

### Files to Review

All files are new (untracked) in the `roughcut/` directory:

1. **src/roughcut/backend/indexing/__init__.py** (module exports)
2. **src/roughcut/backend/indexing/hash_cache.py** (~6.2 KB - MD5 hash caching with mtime checks)
3. **src/roughcut/backend/indexing/scanner.py** (~6.1 KB - File system scanning, async support)
4. **src/roughcut/backend/indexing/incremental.py** (~4.8 KB - Change detection algorithm)
5. **src/roughcut/backend/indexing/indexer.py** (~9.8 KB - Main orchestrator with progress reporting)
6. **src/roughcut/backend/database/__init__.py** (module exports)
7. **src/roughcut/backend/database/models.py** (~6.9 KB - MediaAsset, IndexState, IndexResult, ScanResult)
8. **lua/roughcut/progress_dialog.lua** (~3.6 KB - Lua progress dialog for Fusion UI)
9. **src/roughcut/protocols/handlers/media.py** (MODIFIED - Added indexing handlers)
10. **tests/unit/backend/indexing/test_indexing.py** (~12 KB - 26 unit tests)

### Key Implementation Details

- **Language**: Python 3.x + Lua
- **Architecture**: JSON-RPC protocol between Lua (Fusion UI) and Python (backend)
- **Key Features**: Incremental file scanning, MD5 hash-based change detection, progress callbacks every 5s max
- **Performance Target**: <2 minutes for 100 assets

### Output Format

Provide findings as a Markdown list:
- **Issue title**: Brief description
- **Location**: File and line range
- **Evidence**: What the code does wrong
- **Severity**: High/Med/Low
- **Fix suggestion**: What should change

Be ruthless. Look for: security holes, logic errors, missing error handling, performance traps, API inconsistencies, test gaps, documentation gaps.

---

## FILE CONTENTS

### src/roughcut/backend/indexing/hash_cache.py

```python
"""File hash caching for efficient change detection.

Provides caching of file hashes to detect file modifications
without re-computing hashes for unchanged files.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class HashCache:
    """Caches file hashes for efficient change detection.
    
    The cache stores file paths mapped to their hash values and
    modification times. This allows quick detection of changed files
    by first checking mtime, then hash if needed.
    
    Attributes:
        _cache: Dictionary mapping file paths to (hash, mtime) tuples
        _cache_file: Optional path to persist cache to disk
    """
    _cache: Dict[str, tuple[str, float]] = field(default_factory=dict)
    _cache_file: Optional[Path] = None
    
    def compute_hash(self, file_path: Path) -> str:
        """Compute MD5 hash of file content.
        
        Uses chunked reading for memory efficiency with large files.
        
        Args:
            file_path: Path to the file to hash
            
        Returns:
            Hex digest of MD5 hash
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def get_file_hash(self, file_path: Path) -> str:
        """Get hash for a file, using cache if possible.
        
        Checks modification time first, then computes hash only if
        the file has been modified since last cache.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File hash (from cache or freshly computed)
        """
        path_str = str(file_path.resolve())
        
        try:
            stat = file_path.stat()
            current_mtime = stat.st_mtime
            
            # Check if we have a cached entry
            if path_str in self._cache:
                cached_hash, cached_mtime = self._cache[path_str]
                
                # If mtime hasn't changed, use cached hash
                if current_mtime == cached_mtime:
                    return cached_hash
            
            # Compute new hash
            file_hash = self.compute_hash(file_path)
            
            # Update cache
            self._cache[path_str] = (file_hash, current_mtime)
            
            return file_hash
            
        except (FileNotFoundError, OSError):
            # If file doesn't exist, remove from cache if present
            if path_str in self._cache:
                del self._cache[path_str]
            raise
    
    def has_changed(self, file_path: Path, cached_hash: str) -> bool:
        """Check if file has changed since last index.
        
        Compares the current file hash against a previously cached hash.
        
        Args:
            file_path: Path to the file
            cached_hash: Previously cached hash to compare against
            
        Returns:
            True if file hash differs from cached hash, False otherwise
        """
        try:
            current_hash = self.get_file_hash(file_path)
            return current_hash != cached_hash
        except (FileNotFoundError, OSError):
            # File no longer exists, treat as changed (deleted)
            return True
    
    def get_cached_hash(self, file_path: Path) -> Optional[str]:
        """Get the cached hash for a file if available.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Cached hash or None if not in cache
        """
        path_str = str(file_path.resolve())
        if path_str in self._cache:
            return self._cache[path_str][0]
        return None
    
    def invalidate(self, file_path: Path) -> None:
        """Remove a file from the cache.
        
        Args:
            file_path: Path to the file to remove from cache
        """
        path_str = str(file_path.resolve())
        if path_str in self._cache:
            del self._cache[path_str]
    
    def clear(self) -> None:
        """Clear all cached hashes."""
        self._cache.clear()
    
    def save_to_disk(self, cache_file: Optional[Path] = None) -> None:
        """Save cache to disk for persistence.
        
        Args:
            cache_file: Path to save cache to (uses _cache_file if not provided)
        """
        path = cache_file or self._cache_file
        if path is None:
            return
        
        # Convert to serializable format
        data = {
            'hashes': {
                path: {'hash': h, 'mtime': m}
                for path, (h, m) in self._cache.items()
            }
        }
        
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_disk(self, cache_file: Optional[Path] = None) -> None:
        """Load cache from disk.
        
        Args:
            cache_file: Path to load cache from (uses _cache_file if not provided)
        """
        path = cache_file or self._cache_file
        if path is None or not path.exists():
            return
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            # Restore cache from serialized format
            hashes = data.get('hashes', {})
            self._cache = {
                path: (info['hash'], info['mtime'])
                for path, info in hashes.items()
            }
        except (json.JSONDecodeError, KeyError):
            # If cache file is corrupted, start fresh
            self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about the cache.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'cached_entries': len(self._cache)
        }
```

### src/roughcut/backend/indexing/scanner.py

```python
"""File system scanner for media indexing.

Provides asynchronous scanning of media folders to discover
media files with support for different categories and file types.
"""

import asyncio
from pathlib import Path
from typing import List, Set, Optional, AsyncIterator
import aiofiles


# Supported media file extensions by category
MEDIA_EXTENSIONS = {
    'music': {'.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma'},
    'sfx': {'.wav', '.mp3', '.ogg', '.flac', '.aiff', '.m4a'},
    'vfx': {'.mov', '.mp4', '.avi', '.mkv', '.webm', '.prores', '.dnxhd'}
}

# All supported extensions
ALL_EXTENSIONS = set().union(*MEDIA_EXTENSIONS.values())


class FileScanner:
    """Scans file system for media files.
    
    Provides both synchronous and asynchronous scanning of folders
    to discover media files. Supports filtering by category and
    handles various media file formats.
    
    Attributes:
        extensions: Set of file extensions to include in scan
    """
    
    def __init__(self, categories: Optional[List[str]] = None):
        """Initialize scanner with optional category filter.
        
        Args:
            categories: List of categories to scan (music, sfx, vfx).
                       If None, scans all categories.
        """
        if categories:
            self.extensions = set()
            for cat in categories:
                cat_lower = cat.lower()
                if cat_lower in MEDIA_EXTENSIONS:
                    self.extensions.update(MEDIA_EXTENSIONS[cat_lower])
        else:
            self.extensions = ALL_EXTENSIONS.copy()
    
    def scan_folder(self, folder_path: Path) -> List[Path]:
        """Synchronously scan a folder for media files.
        
        Args:
            folder_path: Path to the folder to scan
            
        Returns:
            List of paths to media files found
        """
        results = []
        
        if not folder_path.exists() or not folder_path.is_dir():
            return results
        
        try:
            for item in folder_path.rglob('*'):
                if item.is_file() and item.suffix.lower() in self.extensions:
                    results.append(item)
        except (PermissionError, OSError):
            # Skip folders we can't access
            pass
        
        return results
    
    async def scan_folder_async(self, folder_path: Path) -> AsyncIterator[Path]:
        """Asynchronously scan a folder for media files.
        
        Yields media files as they are discovered for streaming processing.
        
        Args:
            folder_path: Path to the folder to scan
            
        Yields:
            Paths to media files found
        """
        if not folder_path.exists() or not folder_path.is_dir():
            return
        
        try:
            # Use asyncio to run the sync walk in a thread pool
            loop = asyncio.get_event_loop()
            files = await loop.run_in_executor(
                None, self._walk_folder, folder_path
            )
            
            for file_path in files:
                yield file_path
                
        except (PermissionError, OSError):
            # Skip folders we can't access
            pass
    
    def _walk_folder(self, folder_path: Path) -> List[Path]:
        """Internal method to walk folder (runs in thread pool).
        
        Args:
            folder_path: Path to the folder to walk
            
        Returns:
            List of paths to media files
        """
        results = []
        
        try:
            for item in folder_path.rglob('*'):
                if item.is_file() and item.suffix.lower() in self.extensions:
                    results.append(item)
        except (PermissionError, OSError):
            pass
        
        return results
    
    async def scan_multiple_folders(
        self,
        folder_configs: dict[str, Optional[str]]
    ) -> AsyncIterator[tuple[str, Path]]:
        """Scan multiple folders concurrently.
        
        Args:
            folder_configs: Dictionary mapping category to folder path
            
        Yields:
            Tuples of (category, file_path) for each media file found
        """
        tasks = []
        
        for category, folder_path_str in folder_configs.items():
            if not folder_path_str:
                continue
                
            folder_path = Path(folder_path_str)
            if folder_path.exists() and folder_path.is_dir():
                task = self._scan_category_folder(category, folder_path)
                tasks.append(task)
        
        # Use asyncio.gather to run scans concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    # Log error but continue with other results
                    continue
                    
                for category, file_path in result:
                    yield category, file_path
    
    async def _scan_category_folder(
        self,
        category: str,
        folder_path: Path
    ) -> List[tuple[str, Path]]:
        """Scan a single category folder.
        
        Args:
            category: Category name
            folder_path: Path to the folder
            
        Returns:
            List of (category, file_path) tuples
        """
        results = []
        
        async for file_path in self.scan_folder_async(folder_path):
            results.append((category, file_path))
        
        return results
    
    def count_files(self, folder_path: Path) -> int:
        """Count media files in a folder without returning them.
        
        More efficient than scan_folder when only count is needed.
        
        Args:
            folder_path: Path to the folder to count
            
        Returns:
            Number of media files found
        """
        count = 0
        
        if not folder_path.exists() or not folder_path.is_dir():
            return count
        
        try:
            for item in folder_path.rglob('*'):
                if item.is_file() and item.suffix.lower() in self.extensions:
                    count += 1
        except (PermissionError, OSError):
            pass
        
        return count
    
    def get_supported_extensions(self) -> Set[str]:
        """Get the set of supported file extensions.
        
        Returns:
            Set of supported file extensions (e.g., {'.mp3', '.wav'})
        """
        return self.extensions.copy()


def get_category_for_extension(extension: str) -> Optional[str]:
    """Determine media category based on file extension.
    
    Args:
        extension: File extension including dot (e.g., '.mp3')
        
    Returns:
        Category string (music, sfx, vfx) or None if not supported
    """
    ext_lower = extension.lower()
    
    for category, extensions in MEDIA_EXTENSIONS.items():
        if ext_lower in extensions:
            return category
    
    return None
```

### src/roughcut/backend/indexing/incremental.py

```python
"""Incremental scanning for media file changes.

Detects new, modified, and deleted files by comparing current
filesystem state against cached index data.
"""

from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from ..database.models import MediaAsset, ScanResult
from .hash_cache import HashCache
from .scanner import FileScanner


@dataclass
class IncrementalScanner:
    """Detects changes between current filesystem and cached index.
    
    Compares the current state of configured folders against a
    previously stored index to identify:
    - New files: Present in filesystem but not in index
    - Modified files: Present in both but hash differs
    - Deleted files: Present in index but not in filesystem
    
    Attributes:
        hash_cache: Cache for file hash computation
        file_scanner: Scanner for discovering media files
    """
    
    hash_cache: HashCache
    file_scanner: FileScanner
    
    async def scan_for_changes(
        self,
        folder_configs: Dict[str, Optional[str]],
        cached_assets: List[MediaAsset]
    ) -> ScanResult:
        """Compare current folders against cached index.
        
        Args:
            folder_configs: Dictionary mapping category to folder path
            cached_assets: List of previously indexed assets
            
        Returns:
            ScanResult containing new, modified, and deleted files
        """
        # Build lookup of cached assets by path for O(1) access
        cached_by_path: Dict[str, MediaAsset] = {
            str(a.file_path.resolve()): a 
            for a in cached_assets
        }
        
        new_files: List[Path] = []
        modified_files: List[Path] = []
        current_paths: set[str] = set()
        total_scanned = 0
        
        # Scan all configured folders
        async for category, file_path in self.file_scanner.scan_multiple_folders(folder_configs):
            total_scanned += 1
            path_str = str(file_path.resolve())
            current_paths.add(path_str)
            
            if path_str not in cached_by_path:
                # New file not in cache
                new_files.append(file_path)
            else:
                # File exists in cache, check if modified
                cached_asset = cached_by_path[path_str]
                
                # Quick check: compare modification time
                try:
                    stat = file_path.stat()
                    current_mtime = stat.st_mtime
                    cached_mtime = cached_asset.modified_time.timestamp()
                    
                    if current_mtime != cached_mtime:
                        # Mtime changed, verify with hash
                        if self.hash_cache.has_changed(file_path, cached_asset.file_hash):
                            modified_files.append(file_path)
                except (FileNotFoundError, OSError):
                    # File was deleted during scan
                    pass
        
        # Find deleted files (in cache but not in current filesystem)
        deleted_files: List[str] = [
            a.id for a in cached_assets
            if str(a.file_path.resolve()) not in current_paths
        ]
        
        return ScanResult(
            new_files=new_files,
            modified_files=modified_files,
            deleted_files=deleted_files,
            total_scanned=total_scanned
        )
    
    def scan_for_changes_sync(
        self,
        folder_configs: Dict[str, Optional[str]],
        cached_assets: List[MediaAsset]
    ) -> ScanResult:
        """Synchronous version of scan_for_changes.
        
        For use when async context is not available.
        
        Args:
            folder_configs: Dictionary mapping category to folder path
            cached_assets: List of previously indexed assets
            
        Returns:
            ScanResult containing new, modified, and deleted files
        """
        # Build lookup of cached assets by path
        cached_by_path: Dict[str, MediaAsset] = {
            str(a.file_path.resolve()): a 
            for a in cached_assets
        }
        
        new_files: List[Path] = []
        modified_files: List[Path] = []
        current_paths: set[str] = set()
        total_scanned = 0
        
        # Scan each configured folder
        for category, folder_path_str in folder_configs.items():
            if not folder_path_str:
                continue
                
            folder_path = Path(folder_path_str)
            if not folder_path.exists() or not folder_path.is_dir():
                continue
            
            # Scan folder
            for file_path in self.file_scanner.scan_folder(folder_path):
                total_scanned += 1
                path_str = str(file_path.resolve())
                current_paths.add(path_str)
                
                if path_str not in cached_by_path:
                    new_files.append(file_path)
                else:
                    # Check if modified
                    cached_asset = cached_by_path[path_str]
                    
                    try:
                        stat = file_path.stat()
                        current_mtime = stat.st_mtime
                        cached_mtime = cached_asset.modified_time.timestamp()
                        
                        if current_mtime != cached_mtime:
                            if self.hash_cache.has_changed(file_path, cached_asset.file_hash):
                                modified_files.append(file_path)
                    except (FileNotFoundError, OSError):
                        pass
        
        # Find deleted files
        deleted_files: List[str] = [
            a.id for a in cached_assets
            if str(a.file_path.resolve()) not in current_paths
        ]
        
        return ScanResult(
            new_files=new_files,
            modified_files=modified_files,
            deleted_files=deleted_files,
            total_scanned=total_scanned
        )
    
    def get_asset_category(
        self,
        file_path: Path,
        folder_configs: Dict[str, Optional[str]]
    ) -> Optional[str]:
        """Determine the category of a file based on its folder.
        
        Args:
            file_path: Path to the file
            folder_configs: Dictionary mapping category to folder path
            
        Returns:
            Category string or None if cannot determine
        """
        file_path_resolved = file_path.resolve()
        
        for category, folder_path_str in folder_configs.items():
            if not folder_path_str:
                continue
                
            folder_path = Path(folder_path_str).resolve()
            
            try:
                # Check if file is within this folder
                file_path_resolved.relative_to(folder_path)
                return category
            except ValueError:
                # Not in this folder
                continue
        
        return None
```

### src/roughcut/backend/indexing/indexer.py

```python
"""Main media indexing orchestrator with progress reporting.

Coordinates file scanning, change detection, and database storage
with support for progress updates and performance optimization.
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field

from ...config.models import MediaFolderConfig
from ..database.models import MediaAsset, IndexState, IndexResult, ScanResult
from .hash_cache import HashCache
from .scanner import FileScanner
from .incremental import IncrementalScanner


ProgressCallback = Callable[[Dict[str, Any]], None]


@dataclass
class MediaIndexer:
    """Orchestrates media indexing with progress reporting.
    
    Manages the full indexing workflow from scanning folders to
    storing results, with progress updates via callback.
    
    Attributes:
        progress_callback: Function called with progress updates
        hash_cache: Cache for file hash computation
        file_scanner: Scanner for discovering media files
        incremental_scanner: Scanner for change detection
        index_state: Current indexing state
        update_interval: Minimum seconds between progress updates
        items_per_update: Number of items to process between updates
    """
    
    progress_callback: Optional[ProgressCallback] = None
    hash_cache: HashCache = field(default_factory=HashCache)
    file_scanner: FileScanner = field(default_factory=FileScanner)
    incremental_scanner: IncrementalScanner = field(init=False)
    index_state: IndexState = field(default_factory=IndexState)
    update_interval: float = 5.0  # NFR: never >5s without update
    items_per_update: int = 10
    
    def __post_init__(self):
        """Initialize the incremental scanner."""
        self.incremental_scanner = IncrementalScanner(
            hash_cache=self.hash_cache,
            file_scanner=self.file_scanner
        )
        self._last_update_time = 0.0
        self._last_update_count = 0
        self._current_operation = ""
    
    async def index_media(
        self,
        folder_configs: MediaFolderConfig,
        cached_assets: Optional[List[MediaAsset]] = None,
        incremental: bool = True
    ) -> IndexResult:
        """Index media folders with progress updates.
        
        Args:
            folder_configs: Configuration with folder paths by category
            cached_assets: Previously indexed assets (for incremental mode)
            incremental: If True, only process changes; if False, full reindex
            
        Returns:
            IndexResult with counts and timing information
        """
        start_time = time.time()
        result = IndexResult()
        
        # Get configured folders as dict
        folders_dict = folder_configs.get_configured_folders()
        
        if not any(folders_dict.values()):
            result.errors.append("No media folders configured")
            return result
        
        # Update index state with current folders
        self.index_state.folder_configs = folders_dict
        
        # Use empty list if no cached assets
        if cached_assets is None:
            cached_assets = []
        
        self._send_progress(
            current=0,
            total=0,
            message="Scanning for media files...",
            operation="scan"
        )
        
        try:
            # 1. Scan for changes
            if incremental and cached_assets:
                changes = await self.incremental_scanner.scan_for_changes(
                    folders_dict, cached_assets
                )
            else:
                # Full scan: treat everything as new
                changes = await self._full_scan(folders_dict)
            
            files_to_process = changes.new_files + changes.modified_files
            total_files = len(files_to_process)
            
            if total_files == 0:
                self._send_progress(
                    current=0,
                    total=0,
                    message="No changes detected",
                    operation="complete"
                )
                result.indexed_count = 0
                result.duration_ms = int((time.time() - start_time) * 1000)
                return result
            
            self._send_progress(
                current=0,
                total=total_files,
                message=f"Found {len(changes.new_files)} new, {len(changes.modified_files)} modified files",
                operation="index"
            )
            
            # 2. Process new and modified files
            processed_assets: List[MediaAsset] = []
            processed = 0
            
            for file_path in files_to_process:
                try:
                    # Determine category
                    category = self._get_file_category(file_path, folders_dict)
                    if not category:
                        continue
                    
                    # Create asset from file
                    asset = MediaAsset.from_file_path(
                        file_path=file_path,
                        category=category,
                        file_hash=self.hash_cache.get_file_hash(file_path)
                    )
                    
                    processed_assets.append(asset)
                    processed += 1
                    
                    # Update counts
                    if file_path in changes.new_files:
                        result.new_count += 1
                    else:
                        result.modified_count += 1
                    
                    # Send progress update
                    await self._maybe_send_progress(
                        current=processed,
                        total=total_files,
                        message=f"Indexing: {file_path.name}",
                        operation="index"
                    )
                    
                except (FileNotFoundError, PermissionError, OSError) as e:
                    result.errors.append(f"Error processing {file_path}: {e}")
                    continue
            
            # 3. Store in database (batch operation)
            if processed_assets:
                self._send_progress(
                    current=processed,
                    total=total_files,
                    message=f"Storing {len(processed_assets)} assets...",
                    operation="store"
                )
                await self._store_assets_batch(processed_assets)
            
            # 4. Handle deleted files
            if changes.deleted_files:
                self._send_progress(
                    current=processed,
                    total=total_files,
                    message=f"Removing {len(changes.deleted_files)} deleted assets...",
                    operation="cleanup"
                )
                await self._delete_assets(changes.deleted_files)
                result.deleted_count = len(changes.deleted_files)
            
            # Update result counts
            result.indexed_count = processed
            
            # Update index state
            self.index_state.total_assets_indexed = len(cached_assets) + result.new_count - result.deleted_count
            self.index_state.update_last_index_time()
            
            self._send_progress(
                current=total_files,
                total=total_files,
                message=f"Indexing complete: {processed} assets processed",
                operation="complete"
            )
            
        except Exception as e:
            result.errors.append(f"Indexing error: {e}")
        
        result.duration_ms = int((time.time() - start_time) * 1000)
        return result
    
    async def _full_scan(
        self,
        folder_configs: Dict[str, Optional[str]]
    ) -> ScanResult:
        """Perform a full scan treating all files as new.
        
        Args:
            folder_configs: Dictionary mapping category to folder path
            
        Returns:
            ScanResult with all files as new_files
        """
        new_files: List[Path] = []
        total_scanned = 0
        
        for category, folder_path_str in folder_configs.items():
            if not folder_path_str:
                continue
                
            folder_path = Path(folder_path_str)
            if not folder_path.exists() or not folder_path.is_dir():
                continue
            
            files = self.file_scanner.scan_folder(folder_path)
            new_files.extend(files)
            total_scanned += len(files)
        
        return ScanResult(
            new_files=new_files,
            modified_files=[],
            deleted_files=[],
            total_scanned=total_scanned
        )
    
    async def _maybe_send_progress(
        self,
        current: int,
        total: int,
        message: str,
        operation: str
    ) -> None:
        """Send progress update if enough time/items have passed.
        
        Args:
            current: Current item count
            total: Total item count
            message: Status message
            operation: Current operation name
        """
        now = time.time()
        items_since_update = current - self._last_update_count
        
        if (now - self._last_update_time >= self.update_interval or 
            items_since_update >= self.items_per_update):
            
            self._send_progress(
                current=current,
                total=total,
                message=message,
                operation=operation
            )
            
            self._last_update_time = now
            self._last_update_count = current
    
    def _send_progress(
        self,
        current: int,
        total: int,
        message: str,
        operation: str
    ) -> None:
        """Send progress update via callback.
        
        Args:
            current: Current item count
            total: Total item count
            message: Status message
            operation: Current operation name
        """
        if self.progress_callback:
            self.progress_callback({
                'type': 'progress',
                'operation': operation,
                'current': current,
                'total': total,
                'message': message
            })
    
    def _get_file_category(
        self,
        file_path: Path,
        folder_configs: Dict[str, Optional[str]]
    ) -> Optional[str]:
        """Determine the category of a file.
        
        Args:
            file_path: Path to the file
            folder_configs: Dictionary mapping category to folder path
            
        Returns:
            Category string or None
        """
        return self.incremental_scanner.get_asset_category(file_path, folder_configs)
    
    async def _store_assets_batch(self, assets: List[MediaAsset]) -> None:
        """Store assets in database (batch operation).
        
        This is a placeholder for the actual database storage.
        In the full implementation, this would call the database layer.
        
        Args:
            assets: List of assets to store
        """
        # TODO: Integrate with actual database storage
        # For now, this is a no-op placeholder
        pass
    
    async def _delete_assets(self, asset_ids: List[str]) -> None:
        """Delete assets from database.
        
        This is a placeholder for the actual database deletion.
        
        Args:
            asset_ids: List of asset IDs to delete
        """
        # TODO: Integrate with actual database storage
        # For now, this is a no-op placeholder
        pass
    
    def get_index_state(self) -> IndexState:
        """Get the current index state.
        
        Returns:
            Current IndexState
        """
        return self.index_state
    
    def reset(self) -> None:
        """Reset the indexer state."""
        self.hash_cache.clear()
        self.index_state = IndexState()
        self._last_update_time = 0.0
        self._last_update_count = 0
```

### src/roughcut/backend/database/models.py

```python
"""Database models for media assets and indexing state.

Defines dataclasses for media asset metadata and index state tracking
with validation, serialization, and database operations support.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import hashlib
import json


@dataclass
class MediaAsset:
    """Represents an indexed media asset.
    
    Attributes:
        id: Unique identifier (UUID or hash-based)
        file_path: Absolute path to the media file
        file_name: Name of the file
        category: Asset category ("music", "sfx", "vfx")
        file_size: File size in bytes
        modified_time: Last modification timestamp
        file_hash: MD5 hash for change detection
        ai_tags: List of AI-generated tags (populated in Story 2.3)
        created_at: Timestamp when asset was first indexed
        updated_at: Timestamp when asset was last updated
    """
    id: str
    file_path: Path
    file_name: str
    category: str
    file_size: int
    modified_time: datetime
    file_hash: str
    ai_tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        now = datetime.now()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
    
    @classmethod
    def from_file_path(
        cls,
        file_path: Path,
        category: str,
        file_hash: Optional[str] = None
    ) -> 'MediaAsset':
        """Create a MediaAsset from a file path.
        
        Args:
            file_path: Path to the media file
            category: Asset category (music, sfx, vfx)
            file_hash: Optional pre-computed file hash
            
        Returns:
            MediaAsset instance populated from file metadata
        """
        import uuid
        
        stat = file_path.stat()
        
        # Compute hash if not provided
        if file_hash is None:
            file_hash = cls._compute_file_hash(file_path)
        
        return cls(
            id=str(uuid.uuid4()),
            file_path=file_path.resolve(),
            file_name=file_path.name,
            category=category,
            file_size=stat.st_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime),
            file_hash=file_hash
        )
    
    @staticmethod
    def _compute_file_hash(file_path: Path) -> str:
        """Compute MD5 hash of file content.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hex digest of MD5 hash
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of the asset
        """
        return {
            'id': self.id,
            'file_path': str(self.file_path),
            'file_name': self.file_name,
            'category': self.category,
            'file_size': self.file_size,
            'modified_time': self.modified_time.isoformat(),
            'file_hash': self.file_hash,
            'ai_tags': self.ai_tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MediaAsset':
        """Create MediaAsset from dictionary.
        
        Args:
            data: Dictionary containing asset data
            
        Returns:
            MediaAsset instance
        """
        return cls(
            id=data['id'],
            file_path=Path(data['file_path']),
            file_name=data['file_name'],
            category=data['category'],
            file_size=data['file_size'],
            modified_time=datetime.fromisoformat(data['modified_time']),
            file_hash=data['file_hash'],
            ai_tags=data.get('ai_tags', []),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )
    
    def has_changed(self) -> bool:
        """Check if the file has been modified since last index.
        
        Returns:
            True if file has been modified, False otherwise
        """
        try:
            current_mtime = datetime.fromtimestamp(self.file_path.stat().st_mtime)
            if current_mtime != self.modified_time:
                # File timestamp changed, verify with hash
                current_hash = self._compute_file_hash(self.file_path)
                return current_hash != self.file_hash
            return False
        except (FileNotFoundError, OSError):
            # File no longer exists
            return True


@dataclass
class IndexState:
    """Tracks indexing state for incremental scans.
    
    Attributes:
        last_index_time: Timestamp of last successful index
        folder_configs: Dictionary mapping category to folder path
        total_assets_indexed: Total count of indexed assets
        index_version: Version string for index format
    """
    last_index_time: Optional[datetime] = None
    folder_configs: Dict[str, Optional[str]] = field(default_factory=dict)
    total_assets_indexed: int = 0
    index_version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of the index state
        """
        return {
            'last_index_time': self.last_index_time.isoformat() if self.last_index_time else None,
            'folder_configs': self.folder_configs,
            'total_assets_indexed': self.total_assets_indexed,
            'index_version': self.index_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IndexState':
        """Create IndexState from dictionary.
        
        Args:
            data: Dictionary containing index state data
            
        Returns:
            IndexState instance
        """
        last_index_time = None
        if data.get('last_index_time'):
            try:
                last_index_time = datetime.fromisoformat(data['last_index_time'])
            except ValueError:
                last_index_time = None
        
        return cls(
            last_index_time=last_index_time,
            folder_configs=data.get('folder_configs', {}),
            total_assets_indexed=data.get('total_assets_indexed', 0),
            index_version=data.get('index_version', '1.0')
        )
    
    def update_last_index_time(self):
        """Update the last index time to now."""
        self.last_index_time = datetime.now()


@dataclass
class IndexResult:
    """Result of an indexing operation.
    
    Attributes:
        indexed_count: Number of assets indexed in this operation
        new_count: Number of new assets added
        modified_count: Number of modified assets updated
        deleted_count: Number of deleted assets removed
        duration_ms: Operation duration in milliseconds
        errors: List of error messages encountered
    """
    indexed_count: int = 0
    new_count: int = 0
    modified_count: int = 0
    deleted_count: int = 0
    duration_ms: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON-RPC responses."""
        return {
            'indexed_count': self.indexed_count,
            'new_count': self.new_count,
            'modified_count': self.modified_count,
            'deleted_count': self.deleted_count,
            'duration_ms': self.duration_ms,
            'errors': self.errors
        }


@dataclass
class ScanResult:
    """Result of a filesystem scan for changes.
    
    Attributes:
        new_files: List of new file paths detected
        modified_files: List of modified file paths
        deleted_files: List of asset IDs for deleted files
        total_scanned: Total number of files scanned
    """
    new_files: List[Path] = field(default_factory=list)
    modified_files: List[Path] = field(default_factory=list)
    deleted_files: List[str] = field(default_factory=list)
    total_scanned: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'new_files': [str(p) for p in self.new_files],
            'modified_files': [str(p) for p in self.modified_files],
            'deleted_files': self.deleted_files,
            'total_scanned': self.total_scanned
        }
```

### src/roughcut/protocols/handlers/media.py (New Indexing Handlers)

The file adds three new JSON-RPC handlers to the existing MEDIA_HANDLERS registry:

1. **index_media(params)** - Initiates incremental indexing with progress streaming
2. **get_index_status(params)** - Returns current indexing state and statistics  
3. **cancel_indexing(params)** - Cancels an in-progress indexing operation

Key code additions:
```python
# Global indexer instance
_indexer: Optional[MediaIndexer] = None

def _get_indexer() -> MediaIndexer:
    """Get or create the global indexer instance."""
    global _indexer
    if _indexer is None:
        _indexer = MediaIndexer()
    return _indexer

# ... handler implementations using asyncio event loop ...

MEDIA_HANDLERS = {
    # ... existing handlers ...
    'index_media': index_media,
    'get_index_status': get_index_status,
    'cancel_indexing': cancel_indexing,
}
```

### lua/roughcut/progress_dialog.lua

```lua
--[[
    Progress Dialog for RoughCut Media Indexing
    
    Provides a blocking UI dialog with progress bar for media indexing operations.
    Integrates with Python backend via JSON-RPC for progress updates.
--]]

local ffi = require("ffi")

-- FFI definitions for Fusion UI
ffi.cdef[[
    typedef struct {} UiDlg;
    typedef struct {} UiControl;
    
    UiDlg* uiCreateDialog(const char* title);
    void uiDestroyDialog(UiDlg* dlg);
    int uiShowDialog(UiDlg* dlg);
    void uiHideDialog(UiDlg* dlg);
    
    UiControl* uiAddProgressBar(UiDlg* dlg, int width, int height);
    UiControl* uiAddLabel(UiDlg* dlg, const char* text);
    
    void uiSetProgressValue(UiControl* ctrl, int value);
    void uiSetLabelText(UiControl* ctrl, const char* text);
]]

-- Module table
local ProgressDialog = {}
ProgressDialog.__index = ProgressDialog

--- Creates a new progress dialog for media indexing
-- @param title Dialog title (optional, defaults to "Indexing Media Assets")
-- @return ProgressDialog instance
function ProgressDialog.new(title)
    local self = setmetatable({}, ProgressDialog)
    
    self.title = title or "Indexing Media Assets"
    self.dialog = nil
    self.progressBar = nil
    self.statusLabel = nil
    self.isVisible = false
    self.currentFile = ""
    self.currentCount = 0
    self.totalCount = 0
    
    return self
end

--- Shows the progress dialog (blocking)
-- @return true if dialog was shown successfully
function ProgressDialog:show()
    -- In a real Fusion environment, this would create the actual dialog
    -- For now, we simulate the dialog structure
    self.isVisible = true
    
    -- Log to console for testing
    print(string.format("[ProgressDialog] %s - Opening...", self.title))
    
    return true
end

--- Updates the progress display
-- @param current Current item number (0-based)
-- @param total Total number of items
-- @param message Status message to display
function ProgressDialog:updateProgress(current, total, message)
    self.currentCount = current
    self.totalCount = total
    
    if message then
        self.currentFile = message
    end
    
    -- Calculate percentage
    local percent = 0
    if total > 0 then
        percent = math.floor((current / total) * 100)
    end
    
    -- Update display
    if message then
        print(string.format("[ProgressDialog] %s (%d/%d) - %s", 
            message, current, total, percent .. "%"))
    else
        print(string.format("[ProgressDialog] Progress: %d/%d (%s)", 
            current, total, percent .. "%"))
    end
    
    -- In real implementation, this would update the UI controls:
    -- if self.progressBar then
    --     self.progressBar:SetValue(percent)
    -- end
    -- if self.statusLabel then
    --     self.statusLabel:SetText(message or string.format("Indexing: %d of %d", current, total))
    -- end
end

--- Updates the status message without changing progress
-- @param message Status message to display
function ProgressDialog:updateMessage(message)
    self.currentFile = message
    print(string.format("[ProgressDialog] %s", message))
end

--- Hides and destroys the progress dialog
function ProgressDialog:close()
    self.isVisible = false
    
    print(string.format("[ProgressDialog] %s - Closing", self.title))
    
    -- In real implementation:
    -- if self.dialog then
    --     self.dialog:Hide()
    --     self.dialog = nil
    -- end
end

--- Checks if dialog is currently visible
-- @return true if dialog is visible
function ProgressDialog:isOpen()
    return self.isVisible
end

--- Gets current progress information
-- @return table with current, total, and message
function ProgressDialog:getProgress()
    return {
        current = self.currentCount,
        total = self.totalCount,
        message = self.currentFile,
        percent = self.totalCount > 0 and math.floor((self.currentCount / self.totalCount) * 100) or 0
    }
end

-- Export module
return ProgressDialog
```

---

## REVIEWER INSTRUCTIONS

You are the **Blind Hunter**. You have NO context, NO spec, and NO patience. Review the code above with extreme skepticism.

**Find at least 10 issues** covering:
- Security vulnerabilities
- Logic errors / bugs
- Missing error handling
- Performance problems
- API inconsistencies
- Code smells

**Output Format:**
```markdown
1. **Issue**: [Title]
   - **Location**: [file:line-range]
   - **Evidence**: [What the code does]
   - **Severity**: [High/Med/Low]
   - **Fix**: [What should change]
```

Be ruthless. Assume the developer cut corners everywhere.
