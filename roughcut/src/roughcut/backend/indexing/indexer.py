"""Main media indexing orchestrator with progress reporting.

Coordinates file scanning, change detection, and database storage
with support for progress updates and performance optimization.
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, TYPE_CHECKING
from dataclasses import dataclass, field

from ...config.models import MediaFolderConfig
from ...config.settings import get_config_manager
from ..database.models import MediaAsset, IndexState, IndexResult, ScanResult
from ..database.spacetime_client import SpacetimeClient, SpacetimeConfig
from ..notion.sync import queue_asset_for_sync, queue_assets_batch
from .hash_cache import HashCache
from .scanner import FileScanner
from .incremental import IncrementalScanner
from .change_detector import FileMetadata

if TYPE_CHECKING:
    from .counter import AssetCounter
    from .change_detector import FileChangeSet


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
        _assets: In-memory storage for indexed assets (until SpacetimeDB integration)
    """
    
    progress_callback: Optional[ProgressCallback] = None
    hash_cache: HashCache = field(default_factory=HashCache)
    file_scanner: FileScanner = field(default_factory=FileScanner)
    incremental_scanner: IncrementalScanner = field(init=False)
    index_state: IndexState = field(default_factory=IndexState)
    update_interval: float = 5.0  # NFR: never >5s without update
    items_per_update: int = 10
    _assets: Dict[str, MediaAsset] = field(default_factory=dict)
    _counter: Any = field(init=False)  # AssetCounter, initialized in __post_init__
    
    # Cache management for _assets to prevent unbounded memory growth
    _max_assets_cache: int = 50000  # Maximum assets to keep in memory
    _assets_access_time: Dict[str, float] = field(default_factory=dict)  # LRU tracking
    
    _db_client: Optional[SpacetimeClient] = field(init=False)
    _db_lock: asyncio.Lock = field(init=False)
    
    def __post_init__(self):
        """Initialize the incremental scanner, asset counter, and database client."""
        self.incremental_scanner = IncrementalScanner(
            hash_cache=self.hash_cache,
            file_scanner=self.file_scanner
        )
        self._last_update_time = 0.0
        self._last_update_count = 0
        self._current_operation = ""
        self._cancelled = False
        
        # Initialize asset counter for dashboard counts
        from .counter import AssetCounter
        self._counter = AssetCounter()
        
        # Async lock for thread-safe asset operations
        self._assets_lock = asyncio.Lock()
        
        # Initialize SpacetimeDB client (connection deferred to connect_database())
        self._db_client = None
        self._db_lock = asyncio.Lock()
    
    async def connect_database(self) -> bool:
        """Connect to SpacetimeDB for persistent storage.
        
        This should be called before indexing operations that require
        database persistence. Safe to call multiple times (idempotent).
        
        Returns:
            True if connected successfully or already connected
        """
        # Already connected - check using the client's is_connected property
        if self._db_client and self._db_client.is_connected:
            return True
        
        try:
            # Load configuration
            config_manager = get_config_manager()
            spacetime_cfg = config_manager.get_spacetime_config()
            
            # Create client config
            db_config = SpacetimeConfig(
                host=spacetime_cfg.get('host', 'localhost'),
                port=spacetime_cfg.get('port', 3000),
                database_name=spacetime_cfg.get('database_name', 'roughcut'),
                identity_token=spacetime_cfg.get('identity_token'),
                module_path=spacetime_cfg.get('module_path')
            )
            
            # Create and connect client
            self._db_client = SpacetimeClient(db_config)
            connected = await self._db_client.connect()
            
            if connected:
                # Subscribe to remote changes for real-time sync
                await self._subscribe_to_remote_changes()
            
            return connected
            
        except Exception as e:
            # Log error but don't fail - indexing can continue with in-memory only
            import logging
            logging.getLogger(__name__).warning(
                f"Failed to connect to SpacetimeDB: {e}. Continuing with in-memory storage only."
            )
            return False
    
    async def disconnect_database(self):
        """Disconnect from SpacetimeDB."""
        if self._db_client:
            await self._db_client.disconnect()
            self._db_client = None
    
    async def _subscribe_to_remote_changes(self):
        """Subscribe to real-time changes from other clients."""
        if not self._db_client:
            return
        
        def on_change(action: str, asset: MediaAsset):
            """Handle remote asset changes."""
            import logging
            logger = logging.getLogger(__name__)
            
            try:
                if action == "INSERT":
                    self._assets[asset.id] = asset
                    logger.debug(f"Remote insert: {asset.id}")
                elif action == "UPDATE":
                    self._assets[asset.id] = asset
                    logger.debug(f"Remote update: {asset.id}")
                elif action == "DELETE":
                    self._assets.pop(asset.id, None)
                    logger.debug(f"Remote delete: {asset.id}")
                
                # Invalidate counter cache when remote changes occur
                if hasattr(self, '_counter') and self._counter is not None:
                    self._counter.invalidate_cache()
                    
            except Exception as e:
                logger.warning(f"Error handling remote change: {e}")
        
        # Subscribe via database client - must await the async method
        await self._db_client.subscribe_to_changes(on_change)
    
    def cancel(self) -> None:
        """Request cancellation of the current indexing operation."""
        self._cancelled = True
    
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancelled
    
    def reset_cancellation(self) -> None:
        """Reset the cancellation flag for a new operation."""
        self._cancelled = False
    
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
                # Check for cancellation request
                if self._cancelled:
                    result.errors.append("Indexing cancelled by user")
                    break
                
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
        """Store assets in memory and persist to SpacetimeDB.
        
        This stores assets in memory for the current session and
        persists to SpacetimeDB for durable storage with real-time sync.
        
        Note: This operation is atomic and thread-safe. All assets are 
        stored before cache invalidation, or none are stored if an error occurs.
        Database failures are logged but don't prevent in-memory storage.
        
        Args:
            assets: List of assets to store
        """
        if not assets:
            return
        
        # Prepare all assets first (validation step)
        new_assets: Dict[str, MediaAsset] = {}
        for asset in assets:
            new_assets[asset.id] = asset
        
        # Atomic update with lock: store all assets then invalidate cache
        # This prevents race conditions where cache is stale but assets aren't stored
        async with self._assets_lock:
            try:
                # Update assets and track access time for LRU
                current_time = time.time()
                self._assets.update(new_assets)
                for asset_id in new_assets:
                    self._assets_access_time[asset_id] = current_time
                
                # Evict oldest assets if cache exceeds max size
                self._evict_oldest_assets_if_needed()
                
                # Invalidate counter cache since assets changed
                if hasattr(self, '_counter') and self._counter is not None:
                    self._counter.invalidate_cache()
            except Exception:
                # Attempt to rollback on error (best effort)
                for asset_id in new_assets:
                    self._assets.pop(asset_id, None)
                    self._assets_access_time.pop(asset_id, None)
                raise
        
        # Persist to SpacetimeDB (outside lock to avoid blocking)
        # Database failures are logged but don't prevent in-memory storage
        if self._db_client:
            try:
                async with self._db_lock:
                    result = await self._db_client.insert_assets(
                        assets,
                        batch_size=500  # Optimal batch size per story requirements
                    )
                    if result.errors:
                        import logging
                        logging.getLogger(__name__).warning(
                            f"Database insert errors: {result.errors}"
                        )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"Failed to persist assets to SpacetimeDB: {e}"
                )
                # Continue - assets are still in memory
        
        # Queue assets for Notion sync (non-blocking, debounced)
        # This runs independently of SpacetimeDB operations
        try:
            queue_assets_batch(assets, operation='create')
        except Exception as e:
            # Log but don't fail - Notion sync is optional
            import logging
            logging.getLogger(__name__).debug(
                f"Failed to queue assets for Notion sync: {e}"
            )
    
    async def _delete_assets(self, asset_ids: List[str]) -> None:
        """Delete assets from memory and SpacetimeDB.
        
        This removes assets from the in-memory index and
        persists deletion to SpacetimeDB for real-time sync.
        
        Note: This operation is thread-safe and tracks deleted count, 
        invalidating cache only if deletions actually occurred.
        Database failures are logged but don't prevent in-memory deletion.
        
        Args:
            asset_ids: List of asset IDs to delete
        """
        deleted_ids: List[str] = []
        
        async with self._assets_lock:
            for asset_id in asset_ids:
                if asset_id in self._assets:
                    del self._assets[asset_id]
                    deleted_ids.append(asset_id)
            
            # Invalidate counter cache only if deletions occurred
            if deleted_ids:
                if hasattr(self, '_counter') and self._counter is not None:
                    self._counter.invalidate_cache()
        
        # Delete from SpacetimeDB (outside lock to avoid blocking)
        # Database failures are logged but don't prevent in-memory deletion
        if self._db_client and deleted_ids:
            try:
                async with self._db_lock:
                    deleted_count = await self._db_client.delete_assets(deleted_ids)
                    import logging
                    logging.getLogger(__name__).info(
                        f"Deleted {deleted_count} assets from SpacetimeDB"
                    )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"Failed to delete assets from SpacetimeDB: {e}"
                )
                # Continue - assets are already deleted from memory
        
        # Queue deleted assets for Notion sync (non-blocking, debounced)
        # This runs independently of SpacetimeDB operations
        if deleted_ids:
            try:
                # Create placeholder assets for deletion sync
                # We only need the asset IDs for deletion
                for asset_id in deleted_ids:
                    from ..database.models import MediaAsset
                    placeholder = MediaAsset(
                        id=asset_id,
                        file_path=Path("/deleted"),
                        file_name="",
                        category="",
                        file_size=0,
                        modified_time=datetime.now(),
                        file_hash=""
                    )
                    queue_asset_for_sync(placeholder, operation='delete')
            except Exception as e:
                # Log but don't fail - Notion sync is optional
                import logging
                logging.getLogger(__name__).debug(
                    f"Failed to queue deleted assets for Notion sync: {e}"
                )
    
    async def reindex_folders(
        self,
        folder_configs: MediaFolderConfig,
        progress_callback: Optional[ProgressCallback] = None
    ) -> IndexResult:
        """Perform full re-indexing of all configured media folders.
        
        Unlike incremental indexing, this scans all files regardless
        of modification time and reconciles database state with filesystem.
        Detects new, modified, moved, and deleted files.
        
        Args:
            folder_configs: Configuration with folder paths by category
            progress_callback: Called with progress updates (replaces self.progress_callback)
            
        Returns:
            IndexResult with counts including moved and deleted assets
        """
        start_time = time.time()
        result = IndexResult()
        
        # Use provided callback or instance callback
        callback = progress_callback or self.progress_callback
        
        # Temporarily set callback for _send_progress to use
        original_callback = self.progress_callback
        self.progress_callback = callback
        
        # Get configured folders as dict
        folders_dict = folder_configs.get_configured_folders()
        
        if not any(folders_dict.values()):
            result.errors.append("No media folders configured")
            self.progress_callback = original_callback
            return result
        
        try:
            # Step 1: Full scan of all configured folders
            self._send_progress(
                current=0,
                total=0,
                message="Re-indexing: scanning folders...",
                operation="scan"
            )
            
            scanned_files: Dict[Path, FileMetadata] = {}
            for category, folder_path in folders_dict.items():
                if not folder_path or not Path(folder_path).exists():
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Skipping missing folder: {category}={folder_path}"
                    )
                    continue
                
                # Scan folder for all files (no incremental filtering)
                files_metadata = await self._scan_folder_full(folder_path, category)
                scanned_files.update(files_metadata)
                
                self._send_progress(
                    current=len(scanned_files),
                    total=len(scanned_files),
                    message=f"Re-indexing: scanned {category} ({len(files_metadata)} files)",
                    operation="scan"
                )
            
            result.total_scanned = len(scanned_files)
            
            # Step 2: Retrieve current database state
            self._send_progress(
                current=0,
                total=0,
                message="Re-indexing: detecting changes...",
                operation="detect"
            )
            
            # Get existing assets from database or memory
            db_assets: List[MediaAsset] = []
            if self._db_client:
                try:
                    db_assets = await self._db_client.query_assets(limit=100000)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Failed to query database: {e}. Using in-memory assets only."
                    )
                    db_assets = list(self._assets.values())
            else:
                db_assets = list(self._assets.values())
            
            # Step 3: Detect changes
            from .change_detector import ChangeDetector, FileMetadata
            detector = ChangeDetector()
            changes = detector.detect_changes(scanned_files, db_assets)
            
            # Step 4: Process changes
            total_changes = len(changes.new_files) + len(changes.modified_files) + len(changes.moved_files) + len(changes.deleted_files)
            processed = 0
            
            self._send_progress(
                current=0,
                total=total_changes,
                message=f"Processing {len(changes.new_files)} new, {len(changes.modified_files)} modified, "
                        f"{len(changes.moved_files)} moved, {len(changes.deleted_files)} deleted...",
                operation="process"
            )
            
            # Handle new files
            if changes.new_files:
                new_assets = await self._process_new_files(
                    changes.new_files, folders_dict, processed, total_changes
                )
                await self._store_assets_batch(new_assets)
                result.new_count = len(new_assets)
                processed += len(changes.new_files)
            
            # Handle modified files
            if changes.modified_files:
                await self._process_modified_files(
                    changes.modified_files, folders_dict, processed, total_changes
                )
                result.modified_count = len(changes.modified_files)
                processed += len(changes.modified_files)
            
            # Handle moved files (update paths only)
            if changes.moved_files:
                await self._process_moved_files(changes.moved_files)
                result.moved_count = len(changes.moved_files)
                processed += len(changes.moved_files)
            
            # Handle deleted/orphaned files
            if changes.deleted_files:
                await self._delete_assets(changes.deleted_files)
                result.deleted_count = len(changes.deleted_files)
                processed += len(changes.deleted_files)
            
            # Update total count
            result.indexed_count = result.new_count + result.modified_count
            
            # Update index state
            self.index_state.total_assets_indexed = len(db_assets) + result.new_count - result.deleted_count
            self.index_state.update_last_index_time()
            
            self._send_progress(
                current=total_changes,
                total=total_changes,
                message=f"Re-indexing complete: {result.new_count} new, "
                        f"{result.modified_count} modified, {result.moved_count} moved, "
                        f"{result.deleted_count} deleted",
                operation="complete"
            )
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Re-indexing error: {e}")
            result.errors.append(f"Re-indexing error: {e}")
        
        finally:
            # Restore original callback
            self.progress_callback = original_callback
        
        result.duration_ms = int((time.time() - start_time) * 1000)
        return result
    
    async def _scan_folder_full(
        self,
        folder_path: str,
        category: str
    ) -> Dict[Path, 'FileMetadata']:
        """Full scan of folder - no incremental timestamp filtering.
        
        Args:
            folder_path: Root folder to scan
            category: Asset category (music, sfx, vfx)
            
        Returns:
            Dict mapping file paths to FileMetadata
        """
        from .change_detector import FileMetadata
        from datetime import datetime
        
        files: Dict[Path, FileMetadata] = {}
        folder = Path(folder_path)
        
        # Scan for all supported extensions for this category
        for file_path in self.file_scanner.scan_folder(folder):
            try:
                stat = file_path.stat()
                file_hash = self.hash_cache.get_file_hash(file_path)
                
                metadata = FileMetadata(
                    file_hash=file_hash,
                    modified_time=datetime.fromtimestamp(stat.st_mtime),
                    file_size=stat.st_size,
                    category=category
                )
                files[file_path] = metadata
            except (OSError, IOError) as e:
                import logging
                logging.getLogger(__name__).warning(
                    f"Failed to get metadata for {file_path}: {e}"
                )
                continue
        
        return files
    
    async def _process_new_files(
        self,
        new_files: List[Path],
        folder_configs: Dict[str, Optional[str]],
        current: int,
        total: int
    ) -> List[MediaAsset]:
        """Process new files and create MediaAsset objects.
        
        Args:
            new_files: List of new file paths
            folder_configs: Dictionary mapping category to folder path
            current: Current progress count
            total: Total items to process
            
        Returns:
            List of created MediaAsset objects
        """
        new_assets: List[MediaAsset] = []
        processed = current
        
        for file_path in new_files:
            if self._cancelled:
                break
            
            try:
                category = self._get_file_category(file_path, folder_configs)
                if not category:
                    continue
                
                asset = MediaAsset.from_file_path(
                    file_path=file_path,
                    category=category,
                    file_hash=self.hash_cache.get_file_hash(file_path)
                )
                
                new_assets.append(asset)
                processed += 1
                
                await self._maybe_send_progress(
                    current=processed,
                    total=total,
                    message=f"Processing new: {file_path.name}",
                    operation="process"
                )
                
            except (FileNotFoundError, PermissionError, OSError) as e:
                import logging
                logging.getLogger(__name__).warning(
                    f"Error processing new file {file_path}: {e}"
                )
                continue
        
        return new_assets
    
    async def _process_modified_files(
        self,
        modified_files: List[Path],
        folder_configs: Dict[str, Optional[str]],
        current: int,
        total: int
    ) -> None:
        """Process modified files by updating their metadata.
        
        Args:
            modified_files: List of modified file paths
            folder_configs: Dictionary mapping category to folder path
            current: Current progress count
            total: Total items to process
        """
        processed = current
        
        for file_path in modified_files:
            if self._cancelled:
                break
            
            try:
                # Find existing asset by path
                path_str = str(file_path)
                existing_asset = None
                for asset in self._assets.values():
                    if asset.file_path == path_str:
                        existing_asset = asset
                        break
                
                if existing_asset:
                    # Update hash and modified time
                    existing_asset.file_hash = self.hash_cache.get_file_hash(file_path)
                    existing_asset.modified_time = datetime.now()
                    
                    # Update in database
                    if self._db_client:
                        await self._db_client.update_asset(existing_asset.id, {
                            'file_hash': existing_asset.file_hash,
                            'modified_time': existing_asset.modified_time.isoformat()
                        })
                
                processed += 1
                await self._maybe_send_progress(
                    current=processed,
                    total=total,
                    message=f"Processing modified: {file_path.name}",
                    operation="process"
                )
                
            except (FileNotFoundError, PermissionError, OSError) as e:
                import logging
                logging.getLogger(__name__).warning(
                    f"Error processing modified file {file_path}: {e}"
                )
                continue
    
    async def _process_moved_files(
        self,
        moved_files: List[Tuple[Path, Path]]
    ) -> None:
        """Update database records for moved files (path change only).
        
        Args:
            moved_files: List of (old_path, new_path) tuples
        """
        for old_path, new_path in moved_files:
            try:
                path_str = str(old_path)
                
                # Find existing asset by old path
                existing_asset = None
                for asset in self._assets.values():
                    if asset.file_path == path_str:
                        existing_asset = asset
                        break
                
                if existing_asset:
                    # Update path and name
                    existing_asset.file_path = str(new_path)
                    existing_asset.file_name = new_path.name
                    
                    # Update in database
                    if self._db_client:
                        await self._db_client.update_asset(existing_asset.id, {
                            'file_path': existing_asset.file_path,
                            'file_name': existing_asset.file_name
                        })
                    
                    import logging
                    logging.getLogger(__name__).info(
                        f"Updated moved file: {old_path} -> {new_path}"
                    )
                    
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    f"Error updating moved file {old_path}: {e}"
                )
                continue
    
    def get_index_state(self) -> IndexState:
        """Get the current index state.
        
        Returns:
            Current IndexState
        """
        return self.index_state
    
    def reset(self) -> None:
        """Reset the indexer state.
        
        Clears all cached data, index state, disconnects from database,
        and invalidates the counter cache.
        """
        self.hash_cache.clear()
        self.index_state = IndexState()
        self._last_update_time = 0.0
        self._last_update_count = 0
        self._assets.clear()
        self._assets_access_time.clear()
        
        # Disconnect from database if connected
        if self._db_client:
            import asyncio
            try:
                # Use existing event loop or create new one for cleanup
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule disconnect as a task if loop is running
                    asyncio.create_task(self.disconnect_database())
                else:
                    loop.run_until_complete(self.disconnect_database())
            except RuntimeError:
                # No event loop running, skip async cleanup
                self._db_client = None
        
        # Invalidate counter cache since all assets were cleared
        if hasattr(self, '_counter') and self._counter is not None:
            self._counter.invalidate_cache()
    
    def _evict_oldest_assets_if_needed(self) -> int:
        """Evict oldest assets if cache exceeds max size.
        
        Uses LRU (Least Recently Used) eviction policy based on access time.
        
        Returns:
            Number of assets evicted
        """
        if len(self._assets) <= self._max_assets_cache:
            return 0
        
        # Calculate how many to evict (evict 10% of max when over limit)
        excess = len(self._assets) - self._max_assets_cache
        to_evict = max(excess, self._max_assets_cache // 10)
        
        # Sort by access time (oldest first) and evict
        sorted_assets = sorted(
            self._assets_access_time.items(),
            key=lambda x: x[1]  # Sort by access timestamp
        )
        
        evicted = 0
        for asset_id, _ in sorted_assets[:to_evict]:
            self._assets.pop(asset_id, None)
            self._assets_access_time.pop(asset_id, None)
            evicted += 1
        
        if evicted > 0:
            import logging
            logging.getLogger(__name__).info(
                f"Evicted {evicted} oldest assets from cache to maintain "
                f"max size of {self._max_assets_cache}"
            )
        
        return evicted
