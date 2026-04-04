"""Notion sync orchestrator with debouncing and batch processing.

Provides automatic synchronization of media assets to Notion with:
- Debounced sync triggers (batch rapid changes)
- Batched updates (respect Notion API limits)
- Error handling with automatic retry
- Queue management for failed operations
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Callable, Any
from threading import Lock, Timer

from .client import NotionClient
from .errors import (
    NotionSyncError,
    NotionRateLimitError,
    NotionAuthError,
    classify_notion_error
)
from .models import SyncResult, SyncStatus, MediaAssetNotionMapping
from ..database.models import MediaAsset
from ...config.settings import get_config_manager

# Configure logger
logger = logging.getLogger(__name__)

# Constants
DEFAULT_DEBOUNCE_SECONDS = 5.0  # Wait 5 seconds to batch changes
MAX_BATCH_SIZE = 100  # Notion API limit for batch operations
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2.0  # Base delay for exponential backoff


@dataclass
class SyncQueueItem:
    """Item in the sync queue.
    
    Attributes:
        asset_id: SpacetimeDB asset ID
        operation: Type of operation (create, update, delete)
        asset_data: Asset data to sync (None for delete)
        retry_count: Number of retry attempts
        added_at: Timestamp when item was added
    """
    asset_id: str
    operation: str  # 'create', 'update', 'delete'
    asset_data: Optional[MediaAsset] = None
    retry_count: int = 0
    added_at: datetime = field(default_factory=datetime.now)


@dataclass
class SyncStatistics:
    """Statistics for sync operations.
    
    Attributes:
        total_synced: Total number of assets synced successfully
        total_failed: Total number of failed sync operations
        last_sync_time: Timestamp of last successful sync
        last_error_time: Timestamp of last error
        error_count_24h: Number of errors in last 24 hours
    """
    total_synced: int = 0
    total_failed: int = 0
    last_sync_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    error_count_24h: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'total_synced': self.total_synced,
            'total_failed': self.total_failed,
            'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None,
            'error_count_24h': self.error_count_24h
        }


class NotionSyncOrchestrator:
    """Orchestrates automatic sync of media assets to Notion.
    
    This class manages:
    - Debounced sync triggers (batches rapid changes)
    - Sync queue management
    - Batch processing (respects Notion API limits)
    - Error handling and retry logic
    - Statistics tracking
    
    Usage:
        orchestrator = NotionSyncOrchestrator()
        
        # Queue an asset for sync
        orchestrator.queue_asset(asset, operation='create')
        
        # Manual full sync
        result = orchestrator.sync_all_assets(assets)
        
        # Get sync status
        status = orchestrator.get_sync_status()
    """
    
    _instance: Optional['NotionSyncOrchestrator'] = None
    _lock = Lock()
    
    def __new__(cls):
        """Singleton pattern for single orchestrator instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
        max_batch_size: int = MAX_BATCH_SIZE
    ):
        """Initialize the sync orchestrator.
        
        Args:
            debounce_seconds: Seconds to wait before triggering sync
            max_batch_size: Maximum assets per batch (Notion API limit)
        """
        if self._initialized:
            return
        
        self._debounce_seconds = debounce_seconds
        self._max_batch_size = max_batch_size
        self._config_manager = get_config_manager()
        self._notion_client = NotionClient()
        
        # Sync queue (asset_id -> queue item)
        self._sync_queue: Dict[str, SyncQueueItem] = {}
        self._queue_lock = Lock()
        
        # Statistics
        self._statistics = SyncStatistics()
        self._stats_lock = Lock()
        
        # Debounce timer
        self._debounce_timer: Optional[Timer] = None
        self._timer_lock = Lock()
        
        # Notion page ID (cached after first use)
        self._page_id: Optional[str] = None
        self._database_id: Optional[str] = None
        
        self._initialized = True
        logger.info("NotionSyncOrchestrator initialized")
    
    def is_sync_enabled(self) -> bool:
        """Check if Notion sync is enabled and configured.
        
        Returns:
            True if sync is enabled and Notion is configured
        """
        if not self._notion_client.is_configured():
            return False
        
        # Check if sync is enabled in settings
        notion_config = self._config_manager.get_notion_config()
        return getattr(notion_config, 'sync_enabled', True)
    
    def queue_asset(
        self,
        asset: MediaAsset,
        operation: str = 'update',
        immediate: bool = False
    ) -> bool:
        """Queue an asset for sync to Notion.
        
        Args:
            asset: Media asset to sync
            operation: Operation type ('create', 'update', 'delete')
            immediate: If True, sync immediately without debouncing
            
        Returns:
            True if queued successfully
        """
        if not self.is_sync_enabled():
            logger.debug("Notion sync disabled, skipping queue")
            return False
        
        # Validate operation
        if operation not in ('create', 'update', 'delete'):
            logger.error(f"Invalid operation: {operation}")
            return False
        
        # Add to queue
        with self._queue_lock:
            # For delete operations, we don't need asset data
            asset_data = asset if operation != 'delete' else None
            
            # Create or update queue item
            self._sync_queue[asset.id] = SyncQueueItem(
                asset_id=asset.id,
                operation=operation,
                asset_data=asset_data,
                retry_count=0,
                added_at=datetime.now()
            )
            queue_size = len(self._sync_queue)
        
        logger.debug(f"Asset {asset.id} queued for {operation}. Queue size: {queue_size}")
        
        # Trigger sync (debounced or immediate)
        if immediate:
            self._trigger_sync()
        else:
            self._debounced_sync()
        
        return True
    
    def queue_assets_batch(
        self,
        assets: List[MediaAsset],
        operation: str = 'update'
    ) -> int:
        """Queue multiple assets for sync.
        
        Args:
            assets: List of assets to sync
            operation: Operation type for all assets
            
        Returns:
            Number of assets queued
        """
        if not self.is_sync_enabled():
            return 0
        
        count = 0
        for asset in assets:
            if self.queue_asset(asset, operation, immediate=False):
                count += 1
        
        logger.info(f"Queued {count} assets for batch sync")
        return count
    
    def _debounced_sync(self):
        """Trigger debounced sync (resets timer on each call)."""
        with self._timer_lock:
            # Cancel existing timer if any
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
            
            # Create new timer
            self._debounce_timer = Timer(
                self._debounce_seconds,
                self._trigger_sync
            )
            self._debounce_timer.daemon = True
            self._debounce_timer.start()
        
        logger.debug(f"Sync debounced: will trigger in {self._debounce_seconds}s")
    
    def _trigger_sync(self):
        """Execute sync for all queued items."""
        logger.info("Triggering Notion sync...")
        
        # Get copy of queue and clear it
        with self._queue_lock:
            queue_copy = list(self._sync_queue.values())
            self._sync_queue.clear()
        
        if not queue_copy:
            logger.debug("No items to sync")
            return
        
        logger.info(f"Syncing {len(queue_copy)} items to Notion")
        
        # Process in batches
        total_synced = 0
        total_failed = 0
        
        for i in range(0, len(queue_copy), self._max_batch_size):
            batch = queue_copy[i:i + self._max_batch_size]
            
            try:
                synced, failed = self._process_batch(batch)
                total_synced += synced
                total_failed += failed
            except Exception as e:
                logger.error(f"Batch sync failed: {e}")
                total_failed += len(batch)
                # Re-queue failed items for retry
                self._requeue_failed_items(batch)
        
        # Update statistics
        with self._stats_lock:
            self._statistics.total_synced += total_synced
            self._statistics.total_failed += total_failed
            if total_synced > 0:
                self._statistics.last_sync_time = datetime.now()
            if total_failed > 0:
                self._statistics.last_error_time = datetime.now()
                self._statistics.error_count_24h += total_failed
        
        logger.info(f"Sync complete: {total_synced} synced, {total_failed} failed")
    
    def _process_batch(self, batch: List[SyncQueueItem]) -> tuple[int, int]:
        """Process a batch of sync items.
        
        Args:
            batch: List of queue items to process
            
        Returns:
            Tuple of (synced_count, failed_count)
        """
        synced = 0
        failed = 0
        
        for item in batch:
            try:
                self._sync_single_item(item)
                synced += 1
            except NotionSyncError as e:
                logger.error(f"Sync failed for {item.asset_id}: {e}")
                failed += 1
                
                # Re-queue if retryable and under max retries
                if e.retryable and item.retry_count < MAX_RETRIES:
                    self._requeue_item(item)
            except Exception as e:
                logger.exception(f"Unexpected error syncing {item.asset_id}")
                failed += 1
        
        return synced, failed
    
    def _sync_single_item(self, item: SyncQueueItem):
        """Sync a single asset to Notion.
        
        Args:
            item: Queue item to sync
            
        Raises:
            NotionSyncError: If sync fails
        """
        # Get or create database
        database_id = self._get_or_create_database()
        
        if item.operation == 'delete':
            # Find and delete the Notion page for this asset
            self._delete_asset_from_notion(item.asset_id, database_id)
        else:
            # Create or update
            if item.asset_data is None:
                raise ValueError(f"Asset data required for {item.operation}")
            
            # Check if asset already exists in Notion
            existing_page_id = self._find_asset_page(item.asset_id, database_id)
            
            if existing_page_id and item.operation == 'update':
                # Update existing
                self._update_asset_in_notion(item.asset_data, existing_page_id)
            else:
                # Create new
                self._create_asset_in_notion(item.asset_data, database_id)
    
    def _get_or_create_database(self) -> str:
        """Get existing database ID or create new database.
        
        Returns:
            Database ID
            
        Raises:
            NotionSyncError: If database cannot be created
        """
        if self._database_id:
            return self._database_id
        
        # Try to get from config
        notion_config = self._config_manager.get_notion_config()
        database_id = getattr(notion_config, 'database_id', None)
        
        if database_id:
            self._database_id = database_id
            return database_id
        
        # Need to create database
        page_id = self._get_page_id()
        
        try:
            client = self._notion_client._get_api_client()
            if not client:
                raise NotionAuthError("Cannot create Notion API client")
            
            # Create database with schema
            database = client.databases.create(
                parent={"page_id": page_id},
                title=[{"type": "text", "text": {"content": "RoughCut Media Assets"}}],
                properties={
                    "Asset ID": {
                        "title": {}  # Use Asset ID as the title property
                    },
                    "Filename": {
                        "rich_text": {}
                    },
                    "Category": {
                        "select": {
                            "options": [
                                {"name": "Music", "color": "blue"},
                                {"name": "SFX", "color": "green"},
                                {"name": "VFX", "color": "purple"}
                            ]
                        }
                    },
                    "File Path": {
                        "url": {}
                    },
                    "AI Tags": {
                        "multi_select": {
                            "options": []  # Will be populated dynamically
                        }
                    },
                    "File Size": {
                        "number": {
                            "format": "bytes"
                        }
                    },
                    "Last Synced": {
                        "date": {}
                    }
                }
            )
            
            self._database_id = database["id"]
            
            # Save to config
            notion_config.database_id = self._database_id
            self._config_manager._config_data['notion'] = notion_config.to_dict(encrypt_token=True)
            self._config_manager._save()
            
            logger.info(f"Created Notion database: {self._database_id}")
            return self._database_id
            
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            raise classify_notion_error(e)
    
    def _get_page_id(self) -> str:
        """Get Notion page ID from configuration.
        
        Returns:
            Page ID
            
        Raises:
            NotionConfigError: If page ID cannot be extracted
        """
        if self._page_id:
            return self._page_id
        
        page_url = self._notion_client.get_page_url()
        if not page_url:
            raise NotionConfigError("No Notion page URL configured")
        
        page_id = self._notion_client._extract_page_id(page_url)
        if not page_id:
            raise NotionConfigError("Could not extract page ID from URL")
        
        self._page_id = page_id
        return page_id
    
    def _find_asset_page(self, asset_id: str, database_id: str) -> Optional[str]:
        """Find existing Notion page for an asset with pagination support.
        
        Handles large databases by paginating through all results.
        
        Args:
            asset_id: SpacetimeDB asset ID
            database_id: Notion database ID
            
        Returns:
            Page ID if found, None otherwise
        """
        try:
            client = self._notion_client._get_api_client()
            if not client:
                return None
            
            # Query database for asset with pagination
            has_more = True
            next_cursor = None
            
            while has_more:
                # Build query parameters
                query_params = {
                    "database_id": database_id,
                    "filter": {
                        "property": "Asset ID",
                        "title": {
                            "equals": asset_id
                        }
                    }
                }
                
                # Add pagination cursor if present
                if next_cursor:
                    query_params["start_cursor"] = next_cursor
                
                results = client.databases.query(**query_params)
                
                # Check if asset found in this page
                if results["results"]:
                    return results["results"][0]["id"]
                
                # Check for more pages
                has_more = results.get("has_more", False)
                next_cursor = results.get("next_cursor")
            
            return None
        except Exception as e:
            logger.warning(f"Failed to find asset page: {e}")
            return None
    
    def _create_asset_in_notion(self, asset: MediaAsset, database_id: str):
        """Create a new asset entry in Notion.
        
        Args:
            asset: Media asset to create
            database_id: Notion database ID
            
        Raises:
            NotionSyncError: If creation fails
        """
        try:
            client = self._notion_client._get_api_client()
            if not client:
                raise NotionAuthError("Cannot create Notion API client")
            
            # Build multi-select options for tags
            tag_options = [{"name": tag} for tag in asset.ai_tags[:100]]  # Limit to 100 tags
            
            client.pages.create(
                parent={"database_id": database_id},
                properties={
                    "Asset ID": {
                        "title": [{"text": {"content": asset.id}}]
                    },
                    "Filename": {
                        "rich_text": [{"text": {"content": asset.file_name}}]
                    },
                    "Category": {
                        "select": {"name": asset.category.capitalize()}
                    },
                    "File Path": {
                        "url": str(asset.file_path)
                    },
                    "AI Tags": {
                        "multi_select": tag_options
                    },
                    "File Size": {
                        "number": asset.file_size
                    },
                    "Last Synced": {
                        "date": {"start": datetime.now().isoformat()}
                    }
                }
            )
            
            logger.debug(f"Created Notion page for asset {asset.id}")
        except Exception as e:
            raise classify_notion_error(e)
    
    def _update_asset_in_notion(self, asset: MediaAsset, page_id: str):
        """Update an existing asset entry in Notion.
        
        Args:
            asset: Media asset to update
            page_id: Notion page ID
            
        Raises:
            NotionSyncError: If update fails
        """
        try:
            client = self._notion_client._get_api_client()
            if not client:
                raise NotionAuthError("Cannot create Notion API client")
            
            # Build multi-select options for tags
            tag_options = [{"name": tag} for tag in asset.ai_tags[:100]]
            
            client.pages.update(
                page_id=page_id,
                properties={
                    "Filename": {
                        "rich_text": [{"text": {"content": asset.file_name}}]
                    },
                    "Category": {
                        "select": {"name": asset.category.capitalize()}
                    },
                    "File Path": {
                        "url": str(asset.file_path)
                    },
                    "AI Tags": {
                        "multi_select": tag_options
                    },
                    "File Size": {
                        "number": asset.file_size
                    },
                    "Last Synced": {
                        "date": {"start": datetime.now().isoformat()}
                    }
                }
            )
            
            logger.debug(f"Updated Notion page for asset {asset.id}")
        except Exception as e:
            raise classify_notion_error(e)
    
    def _delete_asset_from_notion(self, asset_id: str, database_id: str):
        """Delete an asset entry from Notion.
        
        Args:
            asset_id: SpacetimeDB asset ID
            database_id: Notion database ID
            
        Raises:
            NotionSyncError: If deletion fails
        """
        try:
            page_id = self._find_asset_page(asset_id, database_id)
            
            if not page_id:
                logger.debug(f"Asset {asset_id} not found in Notion, nothing to delete")
                return
            
            client = self._notion_client._get_api_client()
            if not client:
                raise NotionAuthError("Cannot create Notion API client")
            
            # Archive the page (Notion's soft delete)
            client.pages.update(
                page_id=page_id,
                archived=True
            )
            
            logger.debug(f"Archived Notion page for asset {asset_id}")
        except Exception as e:
            raise classify_notion_error(e)
    
    def _requeue_item(self, item: SyncQueueItem):
        """Re-queue a single item with incremented retry count.
        
        Args:
            item: Item to re-queue
        """
        with self._queue_lock:
            # Only re-queue if not already in queue
            if item.asset_id not in self._sync_queue:
                self._sync_queue[item.asset_id] = SyncQueueItem(
                    asset_id=item.asset_id,
                    operation=item.operation,
                    asset_data=item.asset_data,
                    retry_count=item.retry_count + 1,
                    added_at=datetime.now()
                )
                logger.debug(f"Re-queued asset {item.asset_id} (retry {item.retry_count + 1})")
    
    def _requeue_failed_items(self, items: List[SyncQueueItem]):
        """Re-queue failed items for retry.
        
        Args:
            items: Items to re-queue
        """
        for item in items:
            if item.retry_count < MAX_RETRIES:
                self._requeue_item(item)
    
    def sync_all_assets(
        self,
        assets: List[MediaAsset],
        force_full: bool = False
    ) -> SyncResult:
        """Perform a full sync of all assets to Notion.
        
        Args:
            assets: List of all assets to sync
            force_full: If True, re-sync all assets even if unchanged
            
        Returns:
            SyncResult with operation status
        """
        if not self.is_sync_enabled():
            return SyncResult(
                success=False,
                error_message="Notion sync is not enabled or configured"
            )
        
        logger.info(f"Starting full sync of {len(assets)} assets")
        
        try:
            # Queue all assets
            queued = self.queue_assets_batch(assets, 'update')
            
            # Trigger immediate sync
            self._trigger_sync()
            
            with self._stats_lock:
                return SyncResult(
                    success=True,
                    synced_count=self._statistics.total_synced,
                    timestamp=datetime.now()
                )
        except Exception as e:
            logger.exception("Full sync failed")
            return SyncResult(
                success=False,
                error_message=str(e)
            )
    
    def get_sync_status(self) -> dict:
        """Get current sync status and statistics.
        
        Returns:
            Dictionary with sync status information
        """
        with self._stats_lock:
            stats = self._statistics.to_dict()
        
        with self._queue_lock:
            queue_size = len(self._sync_queue)
        
        return {
            'enabled': self.is_sync_enabled(),
            'configured': self._notion_client.is_configured(),
            'queue_size': queue_size,
            'statistics': stats
        }
    
    def clear_statistics(self):
        """Clear sync statistics."""
        with self._stats_lock:
            self._statistics = SyncStatistics()
        logger.info("Sync statistics cleared")
    
    def get_database_url(self) -> Optional[str]:
        """Get Notion database URL for UI display.
        
        Returns:
            Database URL if database exists, None otherwise
        """
        if self._database_id:
            page_url = self._notion_client.get_page_url()
            if page_url:
                return f"{page_url}?v={self._database_id}"
        
        # Try to get from config
        notion_config = self._config_manager.get_notion_config()
        if hasattr(notion_config, 'database_id') and notion_config.database_id:
            page_url = self._notion_client.get_page_url()
            if page_url:
                return f"{page_url}?v={notion_config.database_id}"
        
        return None


# Convenience functions for module-level access

def get_sync_orchestrator() -> NotionSyncOrchestrator:
    """Get the singleton sync orchestrator instance.
    
    Returns:
        NotionSyncOrchestrator singleton
    """
    return NotionSyncOrchestrator()


def queue_asset_for_sync(asset: MediaAsset, operation: str = 'update') -> bool:
    """Queue a single asset for sync (convenience function).
    
    Args:
        asset: Asset to sync
        operation: Operation type
        
    Returns:
        True if queued successfully
    """
    orchestrator = get_sync_orchestrator()
    return orchestrator.queue_asset(asset, operation)


def queue_assets_batch(assets: List[MediaAsset], operation: str = 'update') -> int:
    """Queue multiple assets for sync (convenience function).
    
    Args:
        assets: Assets to sync
        operation: Operation type
        
    Returns:
        Number of assets queued
    """
    orchestrator = get_sync_orchestrator()
    return orchestrator.queue_assets_batch(assets, operation)
