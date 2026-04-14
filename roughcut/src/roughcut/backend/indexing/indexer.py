"""Main media indexing orchestrator with progress reporting.

Coordinates file scanning, change detection, and database storage
with support for progress updates and performance optimization.
"""

import asyncio
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, TYPE_CHECKING, Set, Tuple, AsyncIterator
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
    streaming_callback: Optional[ProgressCallback] = None  # Real-time asset streaming to GUI
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

    @staticmethod
    def _normalize_path(file_path: Path | str) -> str:
        """Normalize a filesystem path for stable comparisons."""
        resolved = Path(file_path).resolve()
        return os.path.normcase(str(resolved))
    
    async def connect_database(self) -> bool:
        """Connect to SpacetimeDB for persistent storage.
        
        This should be called before indexing operations that require
        database persistence. Safe to call multiple times (idempotent).
        
        Returns:
            True if connected successfully or already connected
        """
        import logging as _db_logger
        _db_log = _db_logger.getLogger(__name__)
        _db_log.info("[INDEXING_LOG] PHASE 0: Connecting to SpacetimeDB...")

        # Already connected - check using the client's is_connected property
        if self._db_client and self._db_client.is_connected:
            _db_log.info("[INDEXING_LOG] PHASE 0: Already connected to SpacetimeDB")
            return True
        
        try:
            # Load configuration
            _db_log.info("[INDEXING_LOG] PHASE 0: Loading configuration...")
            config_manager = get_config_manager()
            spacetime_cfg = config_manager.get_spacetime_config()
            _db_log.info(f"[INDEXING_LOG] PHASE 0: Config loaded - host: {spacetime_cfg.get('host', 'localhost')}, port: {spacetime_cfg.get('port', 3000)}")
            
            # Create client config
            db_config = SpacetimeConfig(
                host=spacetime_cfg.get('host', 'localhost'),
                port=spacetime_cfg.get('port', 3000),
                database_name=spacetime_cfg.get('database_name', 'roughcut'),
                identity_token=spacetime_cfg.get('identity_token'),
                module_path=spacetime_cfg.get('module_path')
            )
            
            # Create and connect client
            _db_log.info("[INDEXING_LOG] PHASE 0: Creating SpacetimeClient...")
            self._db_client = SpacetimeClient(db_config)
            _db_log.info("[INDEXING_LOG] PHASE 0: Connecting to database...")
            connected = await self._db_client.connect()
            _db_log.info(f"[INDEXING_LOG] PHASE 0: Connection result: {connected}")
            
            if connected:
                # Subscribe to remote changes for real-time sync
                _db_log.info("[INDEXING_LOG] PHASE 0: Subscribing to remote changes...")
                await self._subscribe_to_remote_changes()
                _db_log.info("[INDEXING_LOG] PHASE 0: Subscribed to remote changes")
            
            return connected
            
        except Exception as e:
            _db_log.error(f"[INDEXING_LOG] PHASE 0 ERROR: Failed to connect to SpacetimeDB: {e}")
            import traceback
            _db_log.error(f"[INDEXING_LOG] PHASE 0 Traceback: {traceback.format_exc()}")
            import logging
            logging.getLogger(__name__).warning(
                f"Failed to connect to SpacetimeDB: {e}"
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
        _ = cached_assets, incremental
        return await self._reconcile_folders(folder_configs, operation_name="index")
    
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
            
            # scan_folder now returns a generator - convert to list for this use case
            files = list(self.file_scanner.scan_folder(folder_path))
            new_files.extend(files)
            total_scanned += len(files)
        
        return ScanResult(
            new_files=new_files,
            modified_files=[],
            deleted_files=[],
            total_scanned=total_scanned
        )

    async def _load_category_assets(
        self,
        category: str,
    ) -> List[MediaAsset]:
        """Load all assets for a category from durable storage or memory."""
        if self._db_client:
            # Use max allowed limit of 10000 and paginate if needed
            all_assets: List[MediaAsset] = []
            offset = 0
            batch_size = 10000
            
            while True:
                query_result = await self._db_client.query_assets(
                    category=category,
                    limit=batch_size,
                )
                if query_result.error:
                    raise RuntimeError(query_result.error)
                
                all_assets.extend(query_result.assets)
                
                # If we got less than batch_size, we've fetched all
                if len(query_result.assets) < batch_size:
                    break
                
                # Otherwise continue fetching next batch
                offset += batch_size
            
            return all_assets

        return [asset for asset in self._assets.values() if asset.category == category]

    async def _hydrate_assets_cache(self, assets: List[MediaAsset]) -> None:
        """Refresh the in-memory cache from authoritative assets."""
        async with self._assets_lock:
            current_time = time.time()
            for asset in assets:
                self._assets[asset.id] = asset
                self._assets_access_time[asset.id] = current_time
            self._evict_oldest_assets_if_needed()
            if hasattr(self, '_counter') and self._counter is not None:
                self._counter.invalidate_cache()

    async def _deduplicate_assets(
        self,
        assets: List[MediaAsset],
    ) -> Tuple[List[MediaAsset], List[str]]:
        """Collapse duplicate records by normalized file path."""
        survivors: Dict[str, MediaAsset] = {}
        duplicate_ids: List[str] = []

        for asset in assets:
            normalized_path = self._normalize_path(asset.file_path)
            existing = survivors.get(normalized_path)
            if existing is None:
                survivors[normalized_path] = asset
                continue

            existing_created = existing.created_at or datetime.min
            candidate_created = asset.created_at or datetime.min
            keep_existing = (
                existing_created < candidate_created or
                (existing_created == candidate_created and existing.id <= asset.id)
            )

            survivor = existing if keep_existing else asset
            duplicate = asset if keep_existing else existing
            merged_tags = list(dict.fromkeys((existing.ai_tags or []) + (asset.ai_tags or [])))
            survivor.ai_tags = merged_tags
            survivors[normalized_path] = survivor
            duplicate_ids.append(duplicate.id)

        if duplicate_ids and self._db_client:
            await self._delete_assets(duplicate_ids)

        deduplicated_assets = list(survivors.values())
        await self._hydrate_assets_cache(deduplicated_assets)
        return deduplicated_assets, duplicate_ids

    async def _load_reconciliation_assets(
        self,
        folders_dict: Dict[str, Optional[str]],
    ) -> Tuple[List[MediaAsset], List[str]]:
        """Load and scope DB assets for reconciliation."""
        target_categories = [category for category, folder in folders_dict.items() if folder]
        all_assets: List[MediaAsset] = []
        for category in target_categories:
            all_assets.extend(await self._load_category_assets(category))

        deduplicated_assets, duplicate_ids = await self._deduplicate_assets(all_assets)

        in_scope_assets: List[MediaAsset] = []
        out_of_scope_ids: List[str] = []
        for asset in deduplicated_assets:
            folder_path = folders_dict.get(asset.category)
            if not folder_path:
                out_of_scope_ids.append(asset.id)
                continue

            if self.incremental_scanner.get_asset_category(asset.file_path, folders_dict) != asset.category:
                out_of_scope_ids.append(asset.id)
                continue

            in_scope_assets.append(asset)

        stale_ids = list(dict.fromkeys(out_of_scope_ids + duplicate_ids))
        return in_scope_assets, stale_ids

    async def _reconcile_folders(
        self,
        folder_configs: MediaFolderConfig,
        operation_name: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> IndexResult:
        """Reconcile configured folders with SpacetimeDB and cache."""
        start_time = time.time()
        result = IndexResult()

        original_callback = self.progress_callback
        if progress_callback is not None:
            self.progress_callback = progress_callback

        folders_dict = folder_configs.get_configured_folders()
        if not any(folders_dict.values()):
            result.errors.append("No media folders configured")
            if progress_callback is not None:
                self.progress_callback = original_callback
            return result

        self.index_state.folder_configs = folders_dict

        import logging as _indexing_logger
        _logger = _indexing_logger.getLogger(__name__)
        _logger.info(f"[INDEXING_LOG] Starting {operation_name} operation")

        try:
            # TRUE STREAMING MODE - No 3-phase accumulation
            # Scan file -> Hash -> Tags -> Write to DB -> Free memory -> Next file
            _logger.info(f"[INDEXING_LOG] === TRUE STREAMING MODE === One file at a time to DB")
            _logger.info(f"[INDEXING_LOG] [VERBOSE] ========================================")
            _logger.info(f"[INDEXING_LOG] [VERBOSE] STREAMING: Scan -> Hash -> Tags -> DB -> Free")
            _logger.info(f"[INDEXING_LOG] [VERBOSE] ========================================")

            self._send_progress(
                current=0,
                total=0,
                message=f"{operation_name.capitalize()}: streaming files to database...",
                operation="streaming",
            )

            try:
                # Process each category with true streaming - no accumulation
                for category, folder_path in folders_dict.items():
                    if not folder_path or not Path(folder_path).exists():
                        continue

                    try:
                        _logger.info(f"[INDEXING_LOG] STREAMING: Starting {category.upper()} from {folder_path}")
                        
                        # TRUE STREAMING: Process files one at a time
                        # No dict accumulation - write immediately to DB
                        await self._true_streaming_index(folder_path, category, result)
                        
                    except Exception as streaming_error:
                        _logger.error(f"[INDEXING_LOG] STREAMING ERROR: Failed {category}: {streaming_error}")
                        result.errors.append(f"Failed streaming {category}: {streaming_error}")
                        # Continue with other categories

                result.indexed_count = result.new_count + result.modified_count
                _logger.info(f"[INDEXING_LOG] STREAMING COMPLETE: {result.new_count} new, {result.modified_count} modified")
            except Exception as e:
                _logger.error(f"[INDEXING_LOG] STREAMING FAILED: {e}")
                import traceback
                _logger.error(f"[INDEXING_LOG] STREAMING Traceback: {traceback.format_exc()}")
                result.errors.append(f"Streaming failed: {e}")
                raise RuntimeError(f"Streaming failed: {e}") from e
            
            _logger.info(f"[INDEXING_LOG] INDEXING COMPLETE: {result.new_count} new, {result.modified_count} modified, {result.moved_count} moved, {result.deleted_count} cleaned up")

            total_indexed = result.new_count + result.modified_count
            self._send_progress(
                current=total_indexed,
                total=total_indexed,
                message=(
                    f"Indexing complete: {result.new_count} new, "
                    f"{result.modified_count} modified, {result.moved_count} moved, "
                    f"{result.deleted_count} cleaned up"
                ),
                operation="complete",
            )
        except Exception as e:
            # Only log if not already logged by phase-specific handler
            if "PHASE" not in str(e):
                _logger.error(f"[INDEXING_LOG] ERROR during {operation_name}: {str(e)}")
                import traceback
                _logger.error(f"[INDEXING_LOG] Traceback: {traceback.format_exc()}")
            if str(e) not in result.errors:
                result.errors.append(f"{operation_name.capitalize()} error: {e}")
        finally:
            if progress_callback is not None:
                self.progress_callback = original_callback

        result.duration_ms = int((time.time() - start_time) * 1000)
        return result

    async def _streaming_index_folder(
        self,
        folder_path: str,
        category: str,
        result: IndexResult,
    ) -> None:
        """Stream-process a single folder one file at a time for memory efficiency.
        
        For each file:
        1. Scan file from disk
        2. Compute hash (or placeholder)
        3. Create MediaAsset with tags from filename/path
        4. Check if exists in DB (by path)
        5. Insert or update immediately
        6. Free memory
        7. Move to next file
        
        Args:
            folder_path: Path to folder to index
            category: Category name (music, sfx, vfx)
            result: IndexResult to update with counts
        """
        import logging
        import gc
        from datetime import datetime
        _stream_logger = logging.getLogger(__name__)
        category_upper = category.upper()
        
        _stream_logger.info(f"[INDEXING_LOG] STREAMING: Starting {category_upper} folder: {folder_path}")
        
        if not self._db_client:
            _stream_logger.error(f"[INDEXING_LOG] STREAMING: No database client available")
            raise RuntimeError("Database not connected")
        
        # Load existing assets for this category into memory-efficient lookup
        # Store just path -> asset_id mapping to save memory
        existing_assets = await self._db_client.get_category_assets(category)
        path_to_id: Dict[str, str] = {}
        path_to_hash: Dict[str, str] = {}
        for asset in existing_assets:
            path_key = self._normalize_path(asset.file_path)
            path_to_id[path_key] = asset.id
            path_to_hash[path_key] = asset.file_hash
        
        _stream_logger.info(f"[INDEXING_LOG] STREAMING: Loaded {len(existing_assets)} existing {category_upper} assets from DB")
        
        processed = 0
        new_count = 0
        modified_count = 0
        error_count = 0
        
        # Stream files one at a time
        async for file_path, metadata in self._scan_folder_streaming(folder_path, category):
            if self._cancelled:
                _stream_logger.info(f"[INDEXING_LOG] STREAMING: Cancelled after {processed} files")
                break
            
            try:
                # Normalize path for lookup
                path_key = self._normalize_path(file_path)
                
                # Check if file already exists in DB
                existing_id = path_to_id.get(path_key)
                existing_hash = path_to_hash.get(path_key)
                
                # Derive tags from filename and path
                ai_tags = self._derive_tags_from_path(file_path, category)
                
                # Create asset object
                asset = MediaAsset.from_file_path(
                    file_path=file_path,
                    category=category,
                    file_hash=metadata.file_hash
                )
                asset.ai_tags = ai_tags
                
                if existing_id:
                    # File exists - check if modified
                    if existing_hash != metadata.file_hash:
                        # Modified - update
                        _stream_logger.info(f"[INDEXING_LOG] [VERBOSE] [{category_upper}] Updating: {file_path.name}")
                        asset.id = existing_id
                        await self._db_client.update_asset(existing_id, {
                            'file_hash': metadata.file_hash,
                            'file_size': metadata.file_size,
                            'modified_time': metadata.modified_time.isoformat(),
                            'ai_tags': ai_tags,
                            'updated_at': datetime.now().isoformat(),
                        })
                        modified_count += 1
                        result.modified_count += 1
                    else:
                        # Unchanged - skip
                        _stream_logger.info(f"[INDEXING_LOG] [VERBOSE] [{category_upper}] Unchanged: {file_path.name}")
                else:
                    # New file - insert
                    _stream_logger.info(f"[INDEXING_LOG] [VERBOSE] [{category_upper}] Inserting: {file_path.name}")
                    await self._db_client.insert_asset(asset)
                    new_count += 1
                    result.new_count += 1
                    # Add to lookup for potential duplicates in same batch
                    path_to_id[path_key] = asset.id
                    path_to_hash[path_key] = metadata.file_hash
                
                processed += 1
                result.indexed_count += 1
                
                # Send progress every file for streaming visibility
                if processed % 10 == 0:
                    self._send_progress(
                        current=processed,
                        total=0,  # Unknown total in streaming
                        message=f"Indexed {processed} {category_upper} files ({new_count} new, {modified_count} modified)",
                        operation="streaming",
                    )
                
                # Explicitly delete asset to free memory
                del asset
                
                # Force garbage collection every 50 files
                if processed % 50 == 0:
                    gc.collect()
                    _stream_logger.info(f"[INDEXING_LOG] STREAMING: GC at {processed} files")
                    
            except Exception as e:
                error_count += 1
                result.errors.append(f"Error processing {file_path}: {e}")
                _stream_logger.error(f"[INDEXING_LOG] STREAMING: Error processing {file_path}: {e}")
                continue
        
        _stream_logger.info(f"[INDEXING_LOG] STREAMING: Complete for {category_upper}. {processed} processed, {new_count} new, {modified_count} modified, {error_count} errors")

    def _derive_tags_from_path(self, file_path: Path, category: str) -> List[str]:
        """Derive tags from filename and folder path.
        
        Args:
            file_path: Path to the file
            category: Category (music, sfx, vfx)
            
        Returns:
            List of tags derived from filename and path
        """
        tags = []
        
        # Add category as tag
        tags.append(category.lower())
        
        # Extract from filename (remove extension, split by common delimiters)
        file_name = file_path.stem  # Name without extension
        # Split by common delimiters
        name_parts = re.split(r'[-_\s\.]+', file_name)
        for part in name_parts:
            part = part.strip().lower()
            if part and len(part) > 2:  # Skip short words
                tags.append(part)
        
        # Extract from parent folder names (useful for organization)
        for parent in file_path.parents:
            folder_name = parent.name.strip().lower()
            if folder_name and len(folder_name) > 2:
                # Skip generic folder names
                if folder_name not in ['sfx', 'music', 'vfx', 'audio', 'video', 'assets']:
                    tags.append(folder_name)
            # Only use first 2 parent folders to avoid too many tags
            if len(tags) > 10:
                break
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        
        return unique_tags[:15]  # Limit to 15 tags
    
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
        operation: str,
        database_writing: bool = False,
        batch_current: Optional[int] = None,
        batch_total: Optional[int] = None,
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
                'phase': operation,
                'current': current,
                'total': total,
                'message': message,
                'databaseWriting': database_writing,
                'batchCurrent': batch_current,
                'batchTotal': batch_total,
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
        import logging as _store_logger
        _store_log = _store_logger.getLogger(__name__)

        if not assets:
            _store_log.info("[INDEXING_LOG] _store_assets_batch: No assets to store")
            return
        
        _store_log.info(f"[INDEXING_LOG] _store_assets_batch: Storing {len(assets)} assets")
        
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
            _store_log.info(f"[INDEXING_LOG] _store_assets_batch: Persisting {len(assets)} assets to SpacetimeDB...")
            try:
                async with self._db_lock:
                    _store_log.info(f"[INDEXING_LOG] _store_assets_batch: Calling insert_assets with batch_size=500")
                    result = await self._db_client.insert_assets(
                        assets,
                        batch_size=500,  # Optimal batch size per story requirements
                        progress_callback=self._handle_store_batch_progress,
                    )
                    _store_log.info(f"[INDEXING_LOG] _store_assets_batch: insert_assets complete. Inserted: {result.inserted_count}, Errors: {len(result.errors)}")
                    if result.errors:
                        import logging
                        logging.getLogger(__name__).warning(
                            f"Database insert errors: {result.errors}"
                        )
            except Exception as e:
                _store_log.error(f"[INDEXING_LOG] _store_assets_batch ERROR: Failed to persist assets to SpacetimeDB: {e}")
                import traceback
                _store_log.error(f"[INDEXING_LOG] _store_assets_batch Traceback: {traceback.format_exc()}")
                import logging
                logging.getLogger(__name__).error(
                    f"Failed to persist assets to SpacetimeDB: {e}"
                )
                # Continue - assets are still in memory
        else:
            _store_log.warning("[INDEXING_LOG] _store_assets_batch: No database client available, assets stored in memory only")
        
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

    def _handle_store_batch_progress(self, progress: Dict[str, Any]) -> None:
        """Forward Spacetime batch writes through the main progress callback."""
        current = int(progress.get('current', 0))
        total = int(progress.get('total', 0))
        batch_current = progress.get('batch_current')
        batch_total = progress.get('batch_total')
        message = f"Writing {current}/{total} assets to SpacetimeDB"
        if batch_total:
            message += f" (batch {batch_current}/{batch_total})"

        self._send_progress(
            current=current,
            total=total,
            message=message,
            operation="writing",
            database_writing=True,
            batch_current=batch_current,
            batch_total=batch_total,
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
        deleted_ids = list(dict.fromkeys(asset_ids))

        async with self._assets_lock:
            for asset_id in deleted_ids:
                self._assets.pop(asset_id, None)
                self._assets_access_time.pop(asset_id, None)

            if deleted_ids and hasattr(self, '_counter') and self._counter is not None:
                self._counter.invalidate_cache()
        
        # Delete from SpacetimeDB (outside lock to avoid blocking)
        # Database failures are logged but don't prevent in-memory deletion
        if self._db_client and deleted_ids:
            try:
                async with self._db_lock:
                    delete_result = await self._db_client.delete_assets(deleted_ids)
                    deleted_count = (
                        delete_result.deleted_count
                        if hasattr(delete_result, 'deleted_count')
                        else int(delete_result)
                    )
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
        return await self._reconcile_folders(
            folder_configs,
            operation_name="reindex",
            progress_callback=progress_callback,
        )
    
    async def _scan_folder_streaming(
        self,
        folder_path: str,
        category: str
    ) -> AsyncIterator[tuple[Path, 'FileMetadata']]:
        """Stream files one at a time for memory-efficient processing.
        
        Yields each file immediately after processing instead of building
        a complete dictionary in memory first.
        
        Args:
            folder_path: Root folder to scan
            category: Asset category (music, sfx, vfx)
            
        Yields:
            Tuples of (file_path, FileMetadata) for each media file
        """
        from .change_detector import FileMetadata
        from datetime import datetime
        import logging
        import gc  # Garbage collector for memory management
        _scan_logger = logging.getLogger(__name__)
        
        category_upper = category.upper()
        _scan_logger.info(f"[INDEXING_LOG] STREAMING SCAN: Starting {category_upper} scan of {folder_path}")
        
        folder = Path(folder_path)
        
        if not folder.exists():
            _scan_logger.error(f"[INDEXING_LOG] STREAMING SCAN: Folder does not exist: {folder_path}")
            return
            
        if not folder.is_dir():
            _scan_logger.error(f"[INDEXING_LOG] STREAMING SCAN: Path is not a directory: {folder_path}")
            return
        
        scanner = FileScanner(categories=[category])
        _scan_logger.info(f"[INDEXING_LOG] STREAMING SCAN: Created scanner for {category_upper}")

        # TRUE STREAMING: Iterate over generator directly - no list accumulation
        processed_count = 0
        error_count = 0
        hash_failures = 0
        files_found = 0
        
        try:
            for file_path in scanner.scan_folder(folder, category):
                files_found += 1
                # Check for cancellation
                if self._cancelled:
                    _scan_logger.info(f"[INDEXING_LOG] STREAMING SCAN: Cancelled after {processed_count} files")
                    return
                
                try:
                    # VERBOSE: Show file being processed
                    _scan_logger.info(f"[INDEXING_LOG] [VERBOSE] [{category_upper}] Processing: {file_path}")
                    
                    stat = file_path.stat()
                    
                    # Try to get hash, but handle failures gracefully
                    try:
                        file_hash = self.hash_cache.get_file_hash(file_path, category)
                    except (OSError, IOError, PermissionError, ValueError) as hash_err:
                        hash_failures += 1
                        _scan_logger.warning(f"[INDEXING_LOG] STREAMING SCAN: Hash failed for {file_path.name}, using placeholder")
                        # Generate placeholder hash
                        import hashlib
                        placeholder_input = f"{file_path}|{stat.st_size}|{stat.st_mtime}|UNREADABLE"
                        file_hash = hashlib.md5(placeholder_input.encode()).hexdigest()
                    
                    metadata = FileMetadata(
                        file_hash=file_hash,
                        modified_time=datetime.fromtimestamp(stat.st_mtime),
                        file_size=stat.st_size,
                        category=category
                    )
                    
                    # YIELD immediately - don't store in dict
                    yield (file_path, metadata)
                    processed_count += 1
                    
                    # VERBOSE: Show completion
                    _scan_logger.info(f"[INDEXING_LOG] [VERBOSE] [{category_upper}] Yielded: {file_path.name}")
                    
                    # Log progress every 10 files (more frequent for streaming visibility)
                    if processed_count % 10 == 0:
                        _scan_logger.info(f"[INDEXING_LOG] STREAMING SCAN: Processed {processed_count}/{files_found} {category_upper} files ({error_count} errors, {hash_failures} hash failures)")
                        # Force garbage collection every 10 files to free memory
                        gc.collect()
                        
                except (OSError, IOError) as e:
                    error_count += 1
                    _scan_logger.warning(f"[INDEXING_LOG] STREAMING SCAN: Failed to process {file_path}: {e}")
                    continue
                except Exception as e:
                    error_count += 1
                    _scan_logger.error(f"[INDEXING_LOG] STREAMING SCAN: Unexpected error for {file_path}: {e}")
                    continue
        except Exception as e:
            _scan_logger.error(f"[INDEXING_LOG] STREAMING SCAN: Scanner failed: {e}")
            return
            
        _scan_logger.info(f"[INDEXING_LOG] STREAMING SCAN: Complete for {category_upper}. {processed_count} files yielded, {error_count} errors, {hash_failures} hash failures")
    
    async def _true_streaming_index(
        self,
        folder_path: str,
        category: str,
        result: IndexResult,
    ) -> None:
        """TRUE STREAMING: Scan one file, write to DB immediately, free memory, repeat.
        
        No accumulation - each file is processed and written to database individually.
        This prevents OOM on large folders.
        
        Flow per file:
        1. Scan from disk
        2. Compute hash (or placeholder on error)
        3. Derive tags from filename/path
        4. Create MediaAsset
        5. Check if exists in DB by path
        6. INSERT (new) or UPDATE (modified) immediately
        7. Log to console (so user sees DB populating)
        8. Delete asset object
        9. Force GC every 50 files
        10. Move to next file
        
        Args:
            folder_path: Path to folder to index
            category: Category name (music, sfx, vfx)
            result: IndexResult to update with counts
        """
        import logging
        import gc
        from datetime import datetime
        _stream_logger = logging.getLogger(__name__)
        category_upper = category.upper()
        
        _stream_logger.info(f"[INDEXING_LOG] TRUE STREAMING: Starting {category_upper} from {folder_path}")
        _stream_logger.info(f"[INDEXING_LOG] TRUE STREAMING: Loading existing asset paths from DB...")
        
        if not self._db_client:
            _stream_logger.error(f"[INDEXING_LOG] TRUE STREAMING: No database client!")
            raise RuntimeError("Database not connected")
        
        # Load just path->hash lookup from DB (not full objects)
        existing_assets = await self._db_client.get_category_assets(category)
        path_to_hash: Dict[str, str] = {}
        for asset in existing_assets:
            path_key = self._normalize_path(asset.file_path)
            path_to_hash[path_key] = asset.file_hash
        
        _stream_logger.info(f"[INDEXING_LOG] TRUE STREAMING: Loaded {len(existing_assets)} existing {category_upper} assets")
        
        # Clear list to free memory
        del existing_assets
        gc.collect()
        
        processed = 0
        new_count = 0
        modified_count = 0
        error_count = 0
        db_writes = 0
        
        # Stream files from disk one at a time
        scanner = FileScanner(categories=[category])
        folder = Path(folder_path)
        
        if not folder.exists() or not folder.is_dir():
            _stream_logger.error(f"[INDEXING_LOG] TRUE STREAMING: Invalid folder: {folder_path}")
            return
        
        _stream_logger.info(f"[INDEXING_LOG] TRUE STREAMING: Scanning {folder_path} for {category_upper} files...")
        
        # TRUE STREAMING: Iterate over generator directly - process as we discover
        total_files = 0
        for file_path in scanner.scan_folder(folder, category):
            total_files += 1
            if self._cancelled:
                _stream_logger.info(f"[INDEXING_LOG] TRUE STREAMING: Cancelled after {processed} files")
                break
            
            try:
                # VERBOSE: Show file being processed
                _stream_logger.info(f"[INDEXING_LOG] [VERBOSE] [{category_upper}] Processing: {file_path}")
                
                # 1. Get file stats
                stat = file_path.stat()
                
                # 2. Compute hash (with error handling)
                try:
                    file_hash = self.hash_cache.get_file_hash(file_path, category)
                except (OSError, IOError, PermissionError, ValueError) as hash_err:
                    # Use placeholder hash - file will still be indexed
                    import hashlib
                    placeholder_input = f"{file_path}|{stat.st_size}|{stat.st_mtime}|UNREADABLE"
                    file_hash = hashlib.md5(placeholder_input.encode()).hexdigest()
                    _stream_logger.info(f"[INDEXING_LOG] [VERBOSE] [{category_upper}] Using placeholder hash: {file_path.name}")
                
                # 3. Derive tags from filename and path
                ai_tags = self._derive_tags_from_path(file_path, category)
                
                # 4. Create asset
                asset = MediaAsset.from_file_path(
                    file_path=file_path,
                    category=category,
                    file_hash=file_hash
                )
                asset.ai_tags = ai_tags
                
                # 5. Check if exists in DB
                path_key = self._normalize_path(file_path)
                existing_hash = path_to_hash.get(path_key)
                
                # 6. Write to DB immediately
                if existing_hash:
                    # File exists - check if modified
                    if existing_hash != file_hash:
                        # Modified - update in DB
                        _stream_logger.info(f"[INDEXING_LOG] [VERBOSE] [{category_upper}] UPDATING DB: {file_path.name}")
                        await self._db_client.update_asset_by_path(str(file_path), {
                            'file_hash': file_hash,
                            'file_size': stat.st_size,
                            'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'ai_tags': ai_tags,
                            'updated_at': datetime.now().isoformat(),
                        })
                        modified_count += 1
                        result.modified_count += 1
                        db_writes += 1
                    else:
                        # Unchanged - skip
                        _stream_logger.info(f"[INDEXING_LOG] [VERBOSE] [{category_upper}] UNCHANGED (skipping): {file_path.name}")
                else:
                    # New file - INSERT to DB immediately
                    _stream_logger.info(f"[INDEXING_LOG] [VERBOSE] [{category_upper}] INSERTING TO DB: {file_path.name}")
                    await self._db_client.insert_asset(asset)
                    new_count += 1
                    result.new_count += 1
                    db_writes += 1
                    # Add to lookup
                    path_to_hash[path_key] = file_hash
                
                # STREAM TO GUI: Send asset immediately after DB write
                if self.streaming_callback:
                    try:
                        asset_dict = {
                            'id': asset.id,
                            'file_name': asset.file_name,
                            'file_path': str(asset.file_path),
                            'category': asset.category,
                            'file_size': asset.file_size,
                            'file_hash': asset.file_hash,
                            'ai_tags': asset.ai_tags or [],
                            'duration': getattr(asset, 'duration', '0:00'),
                            'used': getattr(asset, 'used', False),
                            'modified_time': asset.modified_time.isoformat() if asset.modified_time else None,
                            'created_at': asset.created_at.isoformat() if asset.created_at else None,
                        }
                        await self.streaming_callback(asset_dict)
                        _stream_logger.info(f"[INDEXING_LOG] [VERBOSE] [{category_upper}] STREAMED to GUI: {file_path.name}")
                    except Exception as stream_err:
                        _stream_logger.warning(f"[INDEXING_LOG] Streaming callback failed: {stream_err}")
                
                processed += 1
                result.indexed_count += 1
                
                # 7. Progress update every file (user sees DB populating in real-time)
                if processed % 10 == 0:
                    self._send_progress(
                        current=processed,
                        total=total_files,
                        message=f"[{category_upper}] {processed}/{total_files} files - DB writes: {db_writes}",
                        operation="streaming",
                    )
                    _stream_logger.info(f"[INDEXING_LOG] TRUE STREAMING: [{category_upper}] Progress {processed}/{total_files} ({new_count} new, {modified_count} modified, {db_writes} DB writes)")
                
                # 8. Delete asset object to free memory
                del asset
                
                # 9. Force garbage collection every 50 files
                if processed % 50 == 0:
                    gc.collect()
                    _stream_logger.info(f"[INDEXING_LOG] TRUE STREAMING: [{category_upper}] GC at {processed} files")
                    
            except Exception as e:
                error_count += 1
                result.errors.append(f"Error processing {file_path}: {e}")
                _stream_logger.error(f"[INDEXING_LOG] TRUE STREAMING: [{category_upper}] Error {file_path}: {e}")
                continue
        
        # Final GC
        gc.collect()
        _stream_logger.info(f"[INDEXING_LOG] TRUE STREAMING: [{category_upper}] COMPLETE. Processed: {processed}, New: {new_count}, Modified: {modified_count}, DB Writes: {db_writes}, Errors: {error_count}")
    
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
        import logging
        _process_logger = logging.getLogger(__name__)
        
        new_assets: List[MediaAsset] = []
        processed = current
        hash_failure_count = 0
        
        _process_logger.info(f"[INDEXING_LOG] _process_new_files: Processing {len(new_files)} new files")
        
        for file_path in new_files:
            if self._cancelled:
                _process_logger.info(f"[INDEXING_LOG] _process_new_files: Cancelled, stopping at {processed} files")
                break
            
            try:
                # VERBOSE: Show file being catalogued
                _process_logger.info(f"[INDEXING_LOG] [VERBOSE] Cataloguing: {file_path}")
                
                category = self._get_file_category(file_path, folder_configs)
                if not category:
                    _process_logger.warning(f"[INDEXING_LOG] _process_new_files: Could not determine category for {file_path}")
                    continue
                
                # Get file hash (from cache or compute) with error handling
                try:
                    file_hash = self.hash_cache.get_file_hash(file_path)
                    _process_logger.info(f"[INDEXING_LOG] _process_new_files: Got hash for {file_path.name}")
                except (OSError, IOError, PermissionError, ValueError) as hash_err:
                    hash_failure_count += 1
                    _process_logger.warning(f"[INDEXING_LOG] _process_new_files: Hash failed for {file_path.name}, using placeholder: {hash_err}")
                    # VERBOSE: Show hash failure
                    _process_logger.info(f"[INDEXING_LOG] [VERBOSE] Hash failed for: {file_path}")
                    # Generate placeholder hash
                    import hashlib
                    import os
                    try:
                        stat = file_path.stat()
                        placeholder_input = f"{file_path}|{stat.st_size}|{stat.st_mtime}|UNREADABLE"
                    except (OSError, IOError):
                        # If we can't even stat the file, use path-only hash
                        placeholder_input = f"{file_path}|UNKNOWN|UNKNOWN|UNREADABLE"
                    file_hash = hashlib.md5(placeholder_input.encode()).hexdigest()
                    _process_logger.info(f"[INDEXING_LOG] _process_new_files: Using placeholder hash for {file_path.name}")
                
                asset = MediaAsset.from_file_path(
                    file_path=file_path,
                    category=category,
                    file_hash=file_hash
                )
                
                new_assets.append(asset)
                processed += 1
                
                # VERBOSE: Show successful catalogue
                _process_logger.info(f"[INDEXING_LOG] [VERBOSE] Catalogued OK: {file_path}")
                
                # Log progress every 50 files
                if processed % 50 == 0:
                    _process_logger.info(f"[INDEXING_LOG] _process_new_files: Created {processed}/{total} assets ({hash_failure_count} hash failures)")
                
                await self._maybe_send_progress(
                    current=processed,
                    total=total,
                    message=f"Cataloguing new: {file_path.name}",
                    operation="cataloguing"
                )
                
            except (FileNotFoundError, PermissionError, OSError) as e:
                _process_logger.warning(f"[INDEXING_LOG] _process_new_files: Error processing new file {file_path}: {e}")
                continue
            except Exception as e:
                _process_logger.error(f"[INDEXING_LOG] _process_new_files: Unexpected error for {file_path}: {e}")
                import traceback
                _process_logger.error(f"[INDEXING_LOG] _process_new_files: Traceback: {traceback.format_exc()}")
                continue
        
        _process_logger.info(f"[INDEXING_LOG] _process_new_files: Complete. Created {len(new_assets)} assets ({hash_failure_count} hash failures)")
        return new_assets
    
    async def _process_modified_files(
        self,
        modified_files: List[Path],
        folder_configs: Dict[str, Optional[str]],
        current: int,
        total: int,
        path_lookup: Dict[str, MediaAsset],
    ) -> None:
        """Process modified files by updating their metadata.
        
        Args:
            modified_files: List of modified file paths
            folder_configs: Dictionary mapping category to folder path
            current: Current progress count
            total: Total items to process
        """
        import logging
        _mod_logger = logging.getLogger(__name__)
        
        processed = current
        hash_failure_count = 0
        
        for file_path in modified_files:
            if self._cancelled:
                break
            
            try:
                normalized_path = self._normalize_path(file_path)
                existing_asset = path_lookup.get(normalized_path)
                
                if existing_asset:
                    stat = file_path.stat()
                    
                    # Try to get hash, handle failures gracefully
                    try:
                        file_hash = self.hash_cache.get_file_hash(file_path)
                        _mod_logger.info(f"[INDEXING_LOG] _process_modified_files: Got hash for {file_path.name}")
                    except (OSError, IOError, PermissionError, ValueError) as hash_err:
                        hash_failure_count += 1
                        _mod_logger.warning(f"[INDEXING_LOG] _process_modified_files: Hash failed for {file_path.name}, using placeholder: {hash_err}")
                        import hashlib
                        placeholder_input = f"{file_path}|{stat.st_size}|{stat.st_mtime}|UNREADABLE"
                        file_hash = hashlib.md5(placeholder_input.encode()).hexdigest()
                    
                    existing_asset.file_hash = file_hash
                    existing_asset.modified_time = datetime.fromtimestamp(stat.st_mtime)
                    existing_asset.file_size = stat.st_size
                    existing_asset.file_name = file_path.name
                    existing_asset.file_path = file_path.resolve()
                    existing_asset.category = self._get_file_category(file_path, folder_configs) or existing_asset.category
                    existing_asset.updated_at = datetime.now()
                    path_lookup[normalized_path] = existing_asset
                    await self._hydrate_assets_cache([existing_asset])
                    
                    if self._db_client:
                        await self._db_client.update_asset(existing_asset.id, {
                            'file_path': str(existing_asset.file_path),
                            'file_name': existing_asset.file_name,
                            'category': existing_asset.category,
                            'file_size': existing_asset.file_size,
                            'file_hash': existing_asset.file_hash,
                            'modified_time': existing_asset.modified_time.isoformat(),
                            'updated_at': existing_asset.updated_at.isoformat(),
                        })
                
                processed += 1
                await self._maybe_send_progress(
                    current=processed,
                    total=total,
                    message=f"Cataloguing modified: {file_path.name}",
                    operation="cataloguing"
                )
                
            except (FileNotFoundError, PermissionError, OSError) as e:
                import logging
                logging.getLogger(__name__).warning(
                    f"Error processing modified file {file_path}: {e}"
                )
                continue
    
    async def _process_moved_files(
        self,
        moved_files: List[Tuple[Path, Path]],
        path_lookup: Dict[str, MediaAsset],
    ) -> None:
        """Update database records for moved files (path change only).
        
        Args:
            moved_files: List of (old_path, new_path) tuples
        """
        for old_path, new_path in moved_files:
            try:
                old_path_normalized = self._normalize_path(old_path)
                new_path_normalized = self._normalize_path(new_path)
                existing_asset = path_lookup.pop(old_path_normalized, None)
                
                if existing_asset:
                    # Update path and name
                    existing_asset.file_path = new_path.resolve()
                    existing_asset.file_name = new_path.name
                    existing_asset.updated_at = datetime.now()
                    path_lookup[new_path_normalized] = existing_asset
                    await self._hydrate_assets_cache([existing_asset])
                    
                    # Update in database
                    if self._db_client:
                        await self._db_client.update_asset(existing_asset.id, {
                            'file_path': str(existing_asset.file_path),
                            'file_name': existing_asset.file_name,
                            'updated_at': existing_asset.updated_at.isoformat(),
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
