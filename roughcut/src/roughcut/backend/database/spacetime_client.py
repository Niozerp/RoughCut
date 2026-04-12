"""SpacetimeDB client for RoughCut media asset storage.

Provides async client for SpacetimeDB operations with real-time
synchronization, row-level security, and batch processing support.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import quote

# Configure logger first (before any code that might use it)
logger = logging.getLogger(__name__)

TIMESTAMP_FIELD = "__timestamp_micros_since_unix_epoch__"
LOCAL_SPACETIMEDB_HOSTS = {"localhost", "127.0.0.1", "::1"}

# Import WebSocket client for SpacetimeDB communication
try:
    from .websocket_client import (
        SpacetimeWebSocketClient,
        ConnectionConfig as WSConnectionConfig,
        ReducerResult,
        TableUpdate,
        connect_to_spacetime_db
    )
    HAS_WEBSOCKET_CLIENT = True
except ImportError as e:
    HAS_WEBSOCKET_CLIENT = False
    # Define placeholder types for when websockets is not available
    SpacetimeWebSocketClient = Any
    WSConnectionConfig = Any
    ReducerResult = Any
    TableUpdate = Any
    logger.warning(f"WebSocket client not available: {e}")

# Define custom exceptions
class SpacetimeDBError(Exception):
    """Base exception for SpacetimeDB errors."""
    pass

class STDBConnectionError(SpacetimeDBError):
    """Connection-related errors."""
    pass

from ...backend.database.models import MediaAsset


class ConnectionState(Enum):
    """Connection state machine states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class SpacetimeConfig:
    """Configuration for SpacetimeDB connection.
    
    Attributes:
        host: SpacetimeDB server hostname
        port: SpacetimeDB server port
        database_name: Name of the database/module
        identity_token: Authentication token for row-level security (encrypted)
        module_path: Path to the compiled Rust module
        connect_timeout: Connection timeout in seconds
        max_reconnect_attempts: Maximum reconnection attempts
        request_timeout: Default timeout for requests in seconds
        pool_min_size: Minimum connections in pool (default: 2)
        pool_max_size: Maximum connections in pool (default: 10)
    """
    host: str = "localhost"
    port: int = 3000
    database_name: str = "roughcut"
    identity_token: Optional[str] = None
    module_path: Optional[str] = None
    connect_timeout: float = 10.0
    max_reconnect_attempts: int = 3
    request_timeout: float = 30.0
    pool_min_size: int = 2  # Minimum connections per spec
    pool_max_size: int = 10  # Maximum connections per spec
    
    def __post_init__(self):
        """Validate configuration."""
        if not isinstance(self.host, str) or not self.host:
            raise ValueError("host must be a non-empty string")
        if not isinstance(self.port, int) or not (1 <= self.port <= 65535):
            raise ValueError("port must be an integer between 1 and 65535")
        if not isinstance(self.database_name, str) or not self.database_name:
            raise ValueError("database_name must be a non-empty string")
        if not isinstance(self.pool_min_size, int) or self.pool_min_size < 1:
            raise ValueError("pool_min_size must be a positive integer")
        if not isinstance(self.pool_max_size, int) or self.pool_max_size < self.pool_min_size:
            raise ValueError("pool_max_size must be >= pool_min_size")


@dataclass
class InsertResult:
    """Result of a batch insert operation."""
    inserted_count: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: float = 0.0
    partial_success: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'inserted_count': self.inserted_count,
            'error_count': len(self.errors),
            'errors': self.errors[:10],  # Limit error detail
            'duration_ms': self.duration_ms,
            'partial_success': self.partial_success
        }


@dataclass
class UpdateResult:
    """Result of an update operation."""
    success: bool = False
    asset_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'asset_id': self.asset_id,
            'error': self.error_message if not self.success else None
        }


@dataclass
class DeleteResult:
    """Result of a delete operation."""
    deleted_count: int = 0
    failed_ids: List[str] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'deleted_count': self.deleted_count,
            'failed_count': len(self.failed_ids),
            'errors': self.errors[:5]
        }


@dataclass
class AssetCounts:
    """Asset counts by category."""
    music: int = 0
    sfx: int = 0
    vfx: int = 0
    total: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with formatted counts."""
        return {
            'music': self.music,
            'sfx': self.sfx,
            'vfx': self.vfx,
            'total': self.total,
            'formatted': {
                'music': f"{self.music:,}",
                'sfx': f"{self.sfx:,}",
                'vfx': f"{self.vfx:,}",
                'total': f"{self.total:,}"
            }
        }


@dataclass
class QueryResult:
    """Result of a query operation."""
    assets: List[MediaAsset] = field(default_factory=list)
    total_count: int = 0
    error: Optional[str] = None
    
    def __bool__(self):
        """QueryResult is truthy if no error occurred."""
        return self.error is None


class CircuitBreaker:
    """Circuit breaker for database operations that actually breaks the circuit."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        """Initialize circuit breaker with validation.
        
        Args:
            failure_threshold: Number of failures before opening circuit (must be > 0)
            recovery_timeout: Seconds before attempting recovery (must be > 0)
            
        Raises:
            ValueError: If failure_threshold <= 0 or recovery_timeout <= 0
        """
        if not isinstance(failure_threshold, int) or failure_threshold <= 0:
            raise ValueError(
                f"failure_threshold must be a positive integer, got {failure_threshold}"
            )
        if not isinstance(recovery_timeout, (int, float)) or recovery_timeout <= 0:
            raise ValueError(
                f"recovery_timeout must be positive, got {recovery_timeout}"
            )
        
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures = 0
        self._successes = 0
        self._last_failure_time: Optional[float] = None
        self._state = "closed"  # closed, open, half-open
        self._lock = asyncio.Lock()
    
    async def call(self, operation: Callable, *args, **kwargs):
        """Execute operation with circuit breaker protection.
        
        Raises:
            SpacetimeDBError: If circuit is open
            Exception: Original exception if operation fails
        """
        async with self._lock:
            if self._state == "open":
                # Check if we should try half-open
                if time.monotonic() - (self._last_failure_time or 0) > self.recovery_timeout:
                    self._state = "half-open"
                    logger.info("Circuit breaker entering half-open state")
                else:
                    # Circuit is open - fail fast
                    raise SpacetimeDBError(
                        f"Circuit breaker is OPEN - too many failures ({self._failures}). "
                        f"Retry after {self.recovery_timeout}s"
                    )
        
        try:
            result = await operation(*args, **kwargs)
            
            # Success - reset circuit if in half-open
            async with self._lock:
                if self._state == "half-open":
                    self._state = "closed"
                    self._failures = 0
                    self._successes = 0
                    logger.info("Circuit breaker closed - operation succeeded")
                else:
                    self._successes += 1
                    # Reset failures after enough successes
                    if self._successes >= self.failure_threshold:
                        self._failures = 0
                        self._successes = 0
            
            return result
            
        except Exception as e:
            async with self._lock:
                self._failures += 1
                self._successes = 0
                self._last_failure_time = time.monotonic()
                
                if self._failures >= self.failure_threshold:
                    if self._state != "open":
                        self._state = "open"
                        logger.error(
                            f"Circuit breaker OPENED after {self._failures} failures"
                        )
            
            # Re-raise the original exception
            raise


class SpacetimeClient:
    """Client for SpacetimeDB operations with real-time sync.
    
    Handles connection management, CRUD operations, batch processing,
    and real-time subscriptions for asset changes.
    
    All operations enforce row-level security through identity tokens.
    
    Example:
        >>> config = SpacetimeConfig(
        ...     host="localhost",
        ...     database_name="roughcut",
        ...     identity_token="encrypted_token"
        ... )
        >>> async with SpacetimeClient(config) as client:
        ...     result = await client.insert_assets(assets, batch_size=500)
        ...     print(f"Inserted {result.inserted_count} assets")
    """
    
    # Fixed batch size per specification
    BATCH_SIZE = 500
    MAX_ERRORS = 100  # Cap error list to prevent memory issues
    MAX_SUBSCRIPTIONS = 100  # Prevent resource exhaustion
    
    VALID_CATEGORIES = {'music', 'sfx', 'vfx'}
    
    def __init__(self, config: SpacetimeConfig):
        """Initialize SpacetimeDB client.
        
        Args:
            config: Connection and authentication configuration
        """
        self.config = config
        self._client: Optional[Any] = None
        self._connection_state = ConnectionState.DISCONNECTED
        self._state_lock = asyncio.Lock()
        self._subscriptions: Dict[str, Callable] = {}
        self._subscription_lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()
        self._identity: Optional[Any] = None
        self._reconnect_count = 0
        self._circuit_breaker = CircuitBreaker()
        
        # Statistics tracking - thread safe
        self._stats = {
            'total_inserts': 0,
            'total_updates': 0,
            'total_deletes': 0,
            'connection_errors': 0,
            'last_operation_time': None
        }
        
        # Background tasks for cleanup
        self._background_tasks: List[asyncio.Task] = []
        
        logger.info(
            f"SpacetimeClient initialized for {config.host}:{config.port}/"
            f"{config.database_name}"
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - ensures cleanup.
        
        Returns None to allow exceptions to propagate normally.
        """
        await self.disconnect()
        return None  # Allow exceptions to propagate
    
    @property
    def is_connected(self) -> bool:
        """Thread-safe check if connected."""
        # Use state_lock for consistent reads
        # In async context, we can't use async with in a property
        # So we return the volatile read, but it's consistent enough for checks
        return self._connection_state == ConnectionState.CONNECTED
    
    async def _set_state(self, state: ConnectionState):
        """Thread-safe state transition."""
        async with self._state_lock:
            old_state = self._connection_state
            self._connection_state = state
            logger.debug(f"Connection state: {old_state.value} -> {state.value}")
    
    async def connect(self) -> bool:
        """Establish connection to SpacetimeDB.
        
        Attempts to connect with automatic retry logic and circuit breaker.
        
        Returns:
            True if connection successful, False otherwise
        """
        while True:
            async with self._state_lock:
                if self._connection_state == ConnectionState.CONNECTED:
                    return True
                if self._connection_state != ConnectionState.CONNECTING:
                    old_state = self._connection_state
                    self._connection_state = ConnectionState.CONNECTING
                    logger.debug(
                        f"Connection state: {old_state.value} -> "
                        f"{ConnectionState.CONNECTING.value}"
                    )
                    break

            # Another task is already connecting. Yield until it finishes.
            await asyncio.sleep(0.1)

        if self._connection_state == ConnectionState.CONNECTED:
            return True
        
        for attempt in range(self.config.max_reconnect_attempts):
            try:
                logger.info(
                    f"Connecting to SpacetimeDB (attempt {attempt + 1}/"
                    f"{self.config.max_reconnect_attempts})..."
                )
                
                # Create connection with timeout
                self._client = await asyncio.wait_for(
                    self._create_connection(),
                    timeout=self.config.connect_timeout
                )
                
                if self._client:
                    await self._set_state(ConnectionState.CONNECTED)
                    self._reconnect_count = 0
                    logger.info("Successfully connected to SpacetimeDB")
                    return True
                
            except asyncio.TimeoutError:
                logger.warning(f"Connection attempt {attempt + 1} timed out")
                async with self._stats_lock:
                    self._stats['connection_errors'] += 1
            except Exception as e:
                async with self._stats_lock:
                    self._stats['connection_errors'] += 1
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                
                if attempt < self.config.max_reconnect_attempts - 1:
                    wait_time = min(2 ** attempt, 10)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
        
        await self._set_state(ConnectionState.ERROR)
        logger.error(
            f"Failed to connect after {self.config.max_reconnect_attempts} attempts"
        )
        return False
    
    async def disconnect(self):
        """Close connection to SpacetimeDB and cleanup resources."""
        async with self._state_lock:
            if self._connection_state == ConnectionState.DISCONNECTED:
                return

            old_state = self._connection_state
            self._connection_state = ConnectionState.DISCONNECTED
            logger.debug(
                f"Connection state: {old_state.value} -> "
                f"{ConnectionState.DISCONNECTED.value}"
            )
        
        # Cancel all subscriptions first
        async with self._subscription_lock:
            subscription_ids = list(self._subscriptions.keys())
        
        for sub_id in subscription_ids:
            try:
                await self.unsubscribe(sub_id)
            except Exception as e:
                logger.warning(f"Error unsubscribing {sub_id}: {e}")
        
        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self._background_tasks.clear()
        
        # Close connection
        if self._client:
            try:
                await self._close_connection()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
                self._client = None
        
        logger.info("Disconnected from SpacetimeDB")
    
    async def _create_connection(self) -> Optional[Any]:
        """Create a database connection by probing the SpacetimeDB HTTP API."""
        try:
            await self._execute_sql("SELECT COUNT(*) AS total FROM media_assets")
            return {
                "transport": "http",
                "server_url": self._server_url(),
            }
        except Exception as e:
            logger.error(f"Failed to create SpacetimeDB HTTP connection: {e}")
            raise
    
    async def _close_connection(self):
        """Close database connection."""
        if self._client and hasattr(self._client, 'close'):
            await self._client.close()
    
    def _validate_category(self, category: str) -> str:
        """Validate and normalize category.
        
        Args:
            category: Category string to validate
            
            Returns:
                Normalized lowercase category
                
            Raises:
                ValueError: If category is invalid
        """
        if not category:
            raise ValueError("Category cannot be empty")
        
        normalized = category.lower().strip()
        
        if normalized not in self.VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. Must be one of: "
                f"{', '.join(self.VALID_CATEGORIES)}"
            )
        
        return normalized

    @staticmethod
    def _normalize_path(file_path: Path | str) -> str:
        """Normalize a filesystem path for stable filtering."""
        return os.path.normcase(str(Path(file_path).resolve()))

    def _matches_scope(self, asset_path: Path, scope_folders: Optional[List[str]]) -> bool:
        """Return True when an asset path is inside one of the scope folders."""
        if not scope_folders:
            return True

        normalized_asset_path = self._normalize_path(asset_path)
        for folder in scope_folders:
            if not folder:
                continue

            folder_path = Path(folder).resolve()
            normalized_folder = self._normalize_path(folder_path)
            if normalized_asset_path == normalized_folder:
                return True

            folder_prefix = normalized_folder + os.sep
            if normalized_asset_path.startswith(folder_prefix):
                return True

        return False
    
    def _build_safe_query(
        self,
        category: Optional[str],
        tags: Optional[List[str]],
        limit: int
    ) -> str:
        """Build a safe query string with strict validation.
        
        MVP implementation - production should use parameterized queries.
        
        Args:
            category: Optional category filter (validated against whitelist)
            tags: Optional tags filter (sanitized)
            limit: Result limit (validated as integer)
            
        Returns:
            Safe query string
        """
        # Validate and cap limit
        safe_limit = max(1, min(int(limit), 10000))
        
        if category:
            # Validate category against strict whitelist
            safe_category = self._validate_category(category)
            # Only allow alphanumeric and underscores in identifiers
            if not all(c.isalnum() or c == '_' for c in safe_category):
                raise ValueError(f"Category contains invalid characters: {safe_category}")
            return f"SELECT * FROM media_assets WHERE category = '{safe_category}' LIMIT {safe_limit}"
        
        elif tags and len(tags) > 0:
            # Sanitize tag - only allow alphanumeric, spaces, and common punctuation
            tag = tags[0]
            if not isinstance(tag, str):
                raise ValueError(f"Tag must be string, got {type(tag)}")
            # Remove any potentially dangerous characters
            safe_tag = ''.join(c for c in tag if c.isalnum() or c in ' _-')
            if not safe_tag:
                return f"SELECT * FROM media_assets LIMIT {safe_limit}"
            return f"SELECT * FROM media_assets WHERE ai_tags CONTAINS '{safe_tag}' LIMIT {safe_limit}"
        
        else:
            return f"SELECT * FROM media_assets LIMIT {safe_limit}"
    
    def _validate_asset(self, asset: MediaAsset) -> List[str]:
        """Validate asset data before database operations.
        
        Args:
            asset: Asset to validate
            
            Returns:
                List of validation error messages (empty if valid)
        """
        errors = []
        
        if not asset.id or not isinstance(asset.id, str):
            errors.append(f"Invalid asset ID: {asset.id}")
        
        if not asset.file_path:
            errors.append("File path cannot be empty")
        elif '..' in str(asset.file_path):
            errors.append("File path contains path traversal pattern")
        
        if asset.file_size < 0:
            errors.append(f"File size cannot be negative: {asset.file_size}")
        
        if not asset.file_hash:
            errors.append("File hash cannot be empty")
        
        try:
            self._validate_category(asset.category)
        except ValueError as e:
            errors.append(str(e))
        
        # Deduplicate tags
        if asset.ai_tags and len(asset.ai_tags) != len(set(asset.ai_tags)):
            asset.ai_tags = list(dict.fromkeys(asset.ai_tags))  # Preserve order, remove dups
        
        return errors
    
    async def insert_assets(
        self,
        assets: List[MediaAsset],
        batch_size: Optional[int] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> InsertResult:
        """Insert multiple assets into SpacetimeDB with batching.
        
        Args:
            assets: List of MediaAsset objects to store
            batch_size: Number of assets per batch (must be 500 per spec)
            
            Returns:
                InsertResult with count and structured errors
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to SpacetimeDB")
        
        # Enforce specification batch size
        effective_batch_size = batch_size or self.BATCH_SIZE
        if effective_batch_size != self.BATCH_SIZE:
            logger.warning(
                f"Batch size {effective_batch_size} overridden to {self.BATCH_SIZE} per specification"
            )
            effective_batch_size = self.BATCH_SIZE
        
        if not assets:
            return InsertResult(inserted_count=0, errors=[], duration_ms=0.0)
        
        # Validate all assets first
        validation_errors: List[Dict[str, Any]] = []
        valid_assets = []
        
        for asset in assets:
            asset_errors: List[str] = self._validate_asset(asset)
            if asset_errors:
                validation_errors.append({
                    'asset_id': asset.id,
                    'errors': asset_errors,
                    'stage': 'validation'
                })
            else:
                valid_assets.append(asset)
        
        if not valid_assets:
            return InsertResult(
                inserted_count=0,
                errors=validation_errors[:self.MAX_ERRORS],
                duration_ms=0.0,
                partial_success=False
            )
        
        start_time = time.monotonic()
        total_inserted = 0
        errors: List[Dict[str, Any]] = validation_errors
        total_batches = (len(valid_assets) + effective_batch_size - 1) // effective_batch_size

        if progress_callback:
            progress_callback({
                'current': 0,
                'total': len(valid_assets),
                'batch_current': 0,
                'batch_total': total_batches,
            })

        # Process in batches
        for i in range(0, len(valid_assets), effective_batch_size):
            batch = valid_assets[i:i + effective_batch_size]
            batch_num = i // effective_batch_size + 1
            
            try:
                # Convert and validate batch
                db_assets = []
                for asset in batch:
                    try:
                        db_asset = self._asset_to_db_format(asset)
                        db_assets.append(db_asset)
                    except Exception as e:
                        errors.append({
                            'asset_id': asset.id,
                            'error': f"Conversion failed: {str(e)}",
                            'batch': batch_num,
                            'stage': 'conversion'
                        })
                
                if not db_assets:
                    continue
                
                # Insert batch with circuit breaker
                batch_inserted = await self._circuit_breaker.call(
                    self._insert_batch, db_assets
                )
                
                total_inserted += batch_inserted
                
                # Check for partial batch failure
                if batch_inserted < len(db_assets):
                    errors.append({
                        'batch': batch_num,
                        'expected': len(db_assets),
                        'actual': batch_inserted,
                        'error': 'Partial batch insertion',
                        'stage': 'database'
                    })
                
                logger.debug(f"Inserted batch {batch_num}: {batch_inserted}/{len(db_assets)} assets")
                if progress_callback:
                    progress_callback({
                        'current': min(i + len(batch), len(valid_assets)),
                        'total': len(valid_assets),
                        'batch_current': batch_num,
                        'batch_total': total_batches,
                    })
                
            except SpacetimeDBError as e:
                error_info = {
                    'batch': batch_num,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'stage': 'database'
                }
                errors.append(error_info)
                logger.error(f"Batch {batch_num} failed: {e}")
                if progress_callback:
                    progress_callback({
                        'current': min(i + len(batch), len(valid_assets)),
                        'total': len(valid_assets),
                        'batch_current': batch_num,
                        'batch_total': total_batches,
                    })
                # Continue with next batch - don't fail entire operation
                
            except Exception as e:
                error_info = {
                    'batch': batch_num,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'stage': 'unknown'
                }
                errors.append(error_info)
                logger.error(f"Unexpected error in batch {batch_num}: {e}")
                if progress_callback:
                    progress_callback({
                        'current': min(i + len(batch), len(valid_assets)),
                        'total': len(valid_assets),
                        'batch_current': batch_num,
                        'batch_total': total_batches,
                    })
        
        duration = (time.monotonic() - start_time) * 1000
        
        async with self._stats_lock:
            self._stats['total_inserts'] += total_inserted
            self._stats['last_operation_time'] = datetime.now(timezone.utc)
        
        # Cap errors to prevent memory issues
        if len(errors) > self.MAX_ERRORS:
            logger.warning(f"Truncating error list from {len(errors)} to {self.MAX_ERRORS}")
            errors = errors[:self.MAX_ERRORS]
        
        partial = total_inserted > 0 and total_inserted < len(assets)
        
        logger.info(
            f"Inserted {total_inserted}/{len(assets)} assets in {duration:.0f}ms "
            f"({len(errors)} errors, partial={partial})"
        )
        
        return InsertResult(
            inserted_count=total_inserted,
            errors=errors,
            duration_ms=duration,
            partial_success=partial
        )
    
    async def update_asset(
        self,
        asset_id: str,
        updates: Dict[str, Any]
    ) -> UpdateResult:
        """Update specific fields of an asset.
        
        Args:
            asset_id: Unique identifier of the asset
            updates: Dict of field names to new values
            
            Returns:
                UpdateResult with success status and error details
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to SpacetimeDB")
        
        if not asset_id:
            return UpdateResult(
                success=False,
                error_code="INVALID_ID",
                error_message="Asset ID cannot be empty"
            )
        
        # Validate updates
        if 'category' in updates:
            try:
                updates['category'] = self._validate_category(updates['category'])
            except ValueError as e:
                return UpdateResult(
                    success=False,
                    asset_id=asset_id,
                    error_code="INVALID_CATEGORY",
                    error_message=str(e)
                )
        
        if 'file_size' in updates and updates['file_size'] < 0:
            return UpdateResult(
                success=False,
                asset_id=asset_id,
                error_code="INVALID_SIZE",
                error_message="File size cannot be negative"
            )
        
        # Don't modify caller's dict - create copy with timestamp
        updates_copy = updates.copy()
        updates_copy['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        try:
            success = await self._update_record(asset_id, updates_copy)
            
            if success:
                async with self._stats_lock:
                    self._stats['total_updates'] += 1
                logger.debug(f"Updated asset {asset_id}")
                return UpdateResult(success=True, asset_id=asset_id)
            else:
                return UpdateResult(
                    success=False,
                    asset_id=asset_id,
                    error_code="NOT_FOUND",
                    error_message=f"Asset {asset_id} not found or no changes made"
                )
            
        except SpacetimeDBError as e:
            logger.error(f"Failed to update asset {asset_id}: {e}")
            return UpdateResult(
                success=False,
                asset_id=asset_id,
                error_code="DB_ERROR",
                error_message=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error updating asset {asset_id}: {e}")
            return UpdateResult(
                success=False,
                asset_id=asset_id,
                error_code="UNKNOWN_ERROR",
                error_message=str(e)
            )
    
    async def delete_assets(self, asset_ids: List[str]) -> DeleteResult:
        """Delete assets from SpacetimeDB.
        
        Args:
            asset_ids: List of asset IDs to delete
            
            Returns:
                DeleteResult with count and failed IDs
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to SpacetimeDB")
        
        if not asset_ids:
            return DeleteResult(deleted_count=0)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_ids = []
        for aid in asset_ids:
            if aid and aid not in seen:
                seen.add(aid)
                unique_ids.append(aid)
        
        result = DeleteResult()
        
        try:
            deleted_count = await self._delete_records(unique_ids)
            
            async with self._stats_lock:
                self._stats['total_deletes'] += deleted_count
            
            # Calculate failed IDs
            if deleted_count < len(unique_ids):
                # Some deletions failed - we don't know which ones
                # This is a limitation we document
                result.failed_ids = []  # We can't determine which failed
                result.errors.append({
                    'error': f'Partial deletion: {deleted_count}/{len(unique_ids)} succeeded',
                    'hint': 'Some assets may not exist or permission denied'
                })
            
            result.deleted_count = deleted_count
            
            logger.info(f"Deleted {deleted_count} assets from database")
            return result
            
        except SpacetimeDBError as e:
            logger.error(f"Failed to delete assets: {e}")
            result.errors.append({'error': str(e), 'code': 'DB_ERROR'})
            return result
        except Exception as e:
            logger.error(f"Unexpected error deleting assets: {e}")
            result.errors.append({'error': str(e), 'code': 'UNKNOWN_ERROR'})
            return result
    
    async def delete_assets_batch(
        self,
        asset_ids: List[str],
        batch_size: int = 100
    ) -> DeleteResult:
        """Delete multiple assets in batches.
        
        Processes deletions in smaller batches to avoid overwhelming
        the database with large delete operations. Continues processing
        even if individual batches fail.
        
        Args:
            asset_ids: List of asset IDs to delete
            batch_size: Number of assets per batch (default: 100)
            
        Returns:
            DeleteResult with total deleted count and any errors
            
        Example:
            >>> result = await client.delete_assets_batch(
            ...     ['id1', 'id2', 'id3', ...],
            ...     batch_size=50
            ... )
            >>> print(f"Deleted {result.deleted_count} orphaned assets")
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to SpacetimeDB")
        
        if not asset_ids:
            return DeleteResult(deleted_count=0)
        
        total_deleted = 0
        all_errors: List[Dict[str, Any]] = []
        all_failed_ids: List[str] = []
        
        # Process in batches
        for i in range(0, len(asset_ids), batch_size):
            batch = asset_ids[i:i + batch_size]
            
            try:
                result = await self.delete_assets(batch)
                total_deleted += result.deleted_count
                all_errors.extend(result.errors)
                all_failed_ids.extend(result.failed_ids)
                
                logger.debug(f"Batch delete {i//batch_size + 1}: "
                            f"{result.deleted_count}/{len(batch)} deleted")
                
            except Exception as e:
                logger.error(f"Batch delete failed for batch {i//batch_size + 1}: {e}")
                all_errors.append({
                    'error': f'Batch {i//batch_size + 1} failed: {str(e)}',
                    'batch_start': i,
                    'batch_size': len(batch)
                })
                all_failed_ids.extend(batch)  # Assume all in batch failed
                # Continue with next batch - don't fail entire operation
        
        logger.info(f"Batch delete complete: {total_deleted}/{len(asset_ids)} assets deleted")
        
        return DeleteResult(
            deleted_count=total_deleted,
            failed_ids=all_failed_ids,
            errors=all_errors
        )
    
    async def query_assets(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 1000,
        scope_folders: Optional[List[str]] = None,
        verify_on_disk: bool = False,
    ) -> QueryResult:
        """Query assets with optional filters.
        
        Args:
            category: Filter by asset category (music, sfx, vfx)
            tags: Filter by AI-generated tags
            limit: Maximum results to return (1-10000)
            
            Returns:
                QueryResult with assets or error
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to SpacetimeDB")
        
        # Validate limit
        if not (1 <= limit <= 10000):
            return QueryResult(
                assets=[],
                error=f"Invalid limit {limit}. Must be between 1 and 10000"
            )
        
        try:
            # Validate category if provided
            query_category = None
            if category:
                try:
                    query_category = self._validate_category(category)
                except ValueError as e:
                    return QueryResult(assets=[], error=str(e))
            
            # Build query parameters
            query_params: Dict[str, Any] = {'limit': limit}
            
            if query_category:
                query_params['category'] = query_category
            
            if tags:
                # Validate and deduplicate tags
                query_params['tags'] = list(dict.fromkeys(t.lower().strip() for t in tags if t))
            
            # Execute query with timeout
            results = await asyncio.wait_for(
                self._execute_query(query_params),
                timeout=self.config.request_timeout
            )
            
            # Convert to MediaAsset objects
            assets = []
            conversion_errors = 0
            for record in results:
                try:
                    asset = self._db_record_to_asset(record)
                    assets.append(asset)
                except Exception as e:
                    conversion_errors += 1
                    logger.warning(f"Failed to convert record to asset: {e}")
                    continue

            if scope_folders:
                assets = [
                    asset for asset in assets
                    if self._matches_scope(asset.file_path, scope_folders)
                ]

            stale_ids: List[str] = []
            if verify_on_disk:
                verified_assets: List[MediaAsset] = []
                for asset in assets:
                    try:
                        if asset.file_path.exists() and asset.file_path.is_file():
                            verified_assets.append(asset)
                        else:
                            stale_ids.append(asset.id)
                    except OSError:
                        stale_ids.append(asset.id)
                assets = verified_assets

                if stale_ids:
                    try:
                        await self.delete_assets(stale_ids)
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to delete stale assets during query cleanup: {cleanup_error}")
            
            if conversion_errors > 0:
                logger.warning(
                    f"Query returned {len(results)} records but {conversion_errors} "
                    f"failed conversion. {len(assets)} assets returned."
                    )
            
            if query_params.get('tags'):
                required_tags = {tag.lower() for tag in query_params['tags']}
                assets = [
                    asset for asset in assets
                    if required_tags.issubset({tag.lower() for tag in asset.ai_tags})
                ]

            if len(assets) > limit:
                assets = assets[:limit]

            logger.debug(f"Query returned {len(assets)} assets")
            return QueryResult(assets=assets, total_count=len(assets))
            
        except asyncio.TimeoutError:
            logger.error("Query timed out")
            return QueryResult(assets=[], error="Query timed out")
        except SpacetimeDBError as e:
            logger.error(f"Query failed: {e}")
            return QueryResult(assets=[], error=str(e))
        except Exception as e:
            logger.error(f"Unexpected query error: {e}")
            return QueryResult(assets=[], error=f"Unexpected error: {str(e)}")
    
    async def get_asset_counts(self) -> AssetCounts:
        """Get asset counts by category for current user.
        
            Returns:
                AssetCounts with music, sfx, vfx totals
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to SpacetimeDB")
        
        try:
            counts = await asyncio.wait_for(
                self._execute_count_query(),
                timeout=self.config.request_timeout
            )
            
            return AssetCounts(
                music=counts.get('music', 0),
                sfx=counts.get('sfx', 0),
                vfx=counts.get('vfx', 0),
                total=sum(counts.values())
            )
            
        except asyncio.TimeoutError:
            logger.error("Count query timed out")
            return AssetCounts()  # Return zeros on timeout
        except Exception as e:
            logger.error(f"Failed to get asset counts: {e}")
            return AssetCounts()
    
    async def subscribe_to_changes(
        self,
        callback: Callable[[str, MediaAsset], None]
    ) -> str:
        """Subscribe to real-time asset changes.
        
        Args:
            callback: Function called on change. Receives (action, asset)
                     where action is "INSERT", "UPDATE", or "DELETE"
        
        Returns:
            Subscription ID for later unsubscribe
        """
        # Check subscription limit
        if len(self._subscriptions) >= self.MAX_SUBSCRIPTIONS:
            raise RuntimeError(
                f"Maximum subscription limit ({self.MAX_SUBSCRIPTIONS}) reached"
            )
        
        subscription_id = str(uuid.uuid4())
        
        async with self._subscription_lock:
            # Store as tuple (callback, ws_subscription_id) - ws_id filled in by handler
            self._subscriptions[subscription_id] = (callback, None)
        
        # Start subscription task and track it
        task = asyncio.create_task(
            self._handle_subscription(subscription_id, callback)
        )
        self._background_tasks.append(task)
        
        # Clean up task reference when done
        def cleanup_task(t):
            try:
                self._background_tasks.remove(t)
            except ValueError:
                pass
        
        task.add_done_callback(cleanup_task)
        
        logger.info(f"Subscribed to changes with ID {subscription_id}")
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str):
        """Remove a subscription.
        
        Args:
            subscription_id: ID returned from subscribe_to_changes
        """
        async with self._subscription_lock:
            if subscription_id in self._subscriptions:
                # Get the WebSocket subscription ID if available
                sub_data = self._subscriptions[subscription_id]
                if isinstance(sub_data, tuple) and len(sub_data) > 1:
                    ws_subscription_id = sub_data[1]
                    # Try to unsubscribe from WebSocket if we have the ID
                    if ws_subscription_id and self._client and hasattr(self._client, 'unsubscribe'):
                        try:
                            await self._client.unsubscribe(ws_subscription_id)
                        except Exception as e:
                            logger.warning(f"Error unsubscribing from WebSocket: {e}")
                
                del self._subscriptions[subscription_id]
                logger.info(f"Unsubscribed from changes: {subscription_id}")
        
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics.
        
            Returns:
                Dictionary with operation counts and connection status
        """
        return {
            **self._stats,
            'connected': self.is_connected,
            'active_subscriptions': len(self._subscriptions),
            'reconnect_count': self._reconnect_count,
            'connection_state': self._connection_state.value
        }
    
    # Private helper methods for database operations
    
    def _server_url(self) -> str:
        """Return the HTTP base URL for the configured SpacetimeDB runtime."""
        host = self.config.host.strip()
        connect_host = "127.0.0.1" if host == "localhost" else host
        return f"http://{connect_host}:{self.config.port}"

    def _is_local_runtime(self) -> bool:
        """Return True when the configured runtime is on the local machine."""
        return self.config.host.strip().lower() in LOCAL_SPACETIMEDB_HOSTS

    def _build_http_headers(self, content_type: Optional[str] = None) -> Dict[str, str]:
        """Build headers for SpacetimeDB HTTP requests.

        Local standalone runtimes intentionally avoid bearer auth because RoughCut
        does not currently refresh a matching identity token for the managed local
        server. Remote runtimes still use the configured token when one is present.
        """
        headers = {"Accept": "application/json"}
        if content_type:
            headers["Content-Type"] = content_type

        token = (self.config.identity_token or "").strip()
        if token and not self._is_local_runtime():
            headers["Authorization"] = f"Bearer {token}"

        return headers

    def _escape_sql_literal(self, value: str) -> str:
        """Escape a string for use inside a single-quoted SQL literal."""
        return value.replace("'", "''")

    def _coerce_datetime(self, value: Any) -> datetime:
        """Normalize supported timestamp encodings to a timezone-aware datetime."""
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

        if isinstance(value, (dict, list, int, float)):
            return self._decode_timestamp_value(value)

        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                raise ValueError("Timestamp value cannot be empty")
            if normalized.endswith("Z"):
                normalized = f"{normalized[:-1]}+00:00"
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)

        raise ValueError(f"Unsupported timestamp value: {value!r}")

    def _encode_timestamp_value(self, value: Any) -> Dict[str, int]:
        """Encode a datetime into the SATS JSON timestamp product format."""
        dt_value = self._coerce_datetime(value)
        micros = int(dt_value.timestamp() * 1_000_000)
        return {TIMESTAMP_FIELD: micros}

    def _decode_timestamp_value(self, value: Any) -> datetime:
        """Decode SpacetimeDB timestamp representations into UTC datetimes."""
        raw_value: Any = value
        if isinstance(value, dict):
            raw_value = value.get(TIMESTAMP_FIELD)
        elif isinstance(value, list) and len(value) == 1:
            raw_value = value[0]

        if isinstance(raw_value, datetime):
            return raw_value if raw_value.tzinfo is not None else raw_value.replace(tzinfo=timezone.utc)

        if isinstance(raw_value, str):
            normalized = raw_value[:-1] + "+00:00" if raw_value.endswith("Z") else raw_value
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)

        if not isinstance(raw_value, (int, float)):
            raise ValueError(f"Unsupported SpacetimeDB timestamp value: {value!r}")

        return datetime.fromtimestamp(raw_value / 1_000_000, tz=timezone.utc)

    def _is_timestamp_algebraic_type(self, algebraic_type: Any) -> bool:
        """Return True when a SQL schema type represents SpacetimeDB Timestamp."""
        if not isinstance(algebraic_type, dict):
            return False

        product = algebraic_type.get("Product")
        if not isinstance(product, dict):
            return False

        elements = product.get("elements")
        if not isinstance(elements, list) or len(elements) != 1:
            return False

        element = elements[0]
        if not isinstance(element, dict):
            return False

        name = element.get("name")
        if not isinstance(name, dict) or name.get("some") != TIMESTAMP_FIELD:
            return False

        nested_type = element.get("algebraic_type")
        return isinstance(nested_type, dict) and "I64" in nested_type

    def _decode_sql_value(self, value: Any, algebraic_type: Any) -> Any:
        """Decode a SQL row value using the schema-provided algebraic type."""
        if self._is_timestamp_algebraic_type(algebraic_type):
            return self._decode_timestamp_value(value)
        return value

    def _statement_rows_to_dicts(self, statement: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert a single SQL statement payload into row dictionaries."""
        if not isinstance(statement, dict):
            return []

        schema = statement.get("schema", {})
        schema_elements = schema.get("elements", []) if isinstance(schema, dict) else []
        rows = statement.get("rows", [])
        if not isinstance(rows, list):
            return []

        columns: List[Tuple[str, Any]] = []
        for index, element in enumerate(schema_elements):
            if not isinstance(element, dict):
                columns.append((f"column_{index}", None))
                continue
            name = element.get("name")
            column_name = name.get("some") if isinstance(name, dict) else None
            columns.append((column_name or f"column_{index}", element.get("algebraic_type")))

        records: List[Dict[str, Any]] = []
        for row in rows:
            if isinstance(row, dict):
                records.append(row)
                continue

            if not isinstance(row, list):
                continue

            record: Dict[str, Any] = {}
            for index, raw_value in enumerate(row):
                column_name, algebraic_type = (
                    columns[index] if index < len(columns) else (f"column_{index}", None)
                )
                record[column_name] = self._decode_sql_value(raw_value, algebraic_type)
            records.append(record)

        return records

    def _parse_sql_response(self, payload: Any) -> List[Dict[str, Any]]:
        """Parse the SpacetimeDB SQL response payload into dictionaries."""
        if isinstance(payload, dict):
            return self._statement_rows_to_dicts(payload)

        if not isinstance(payload, list):
            raise SpacetimeDBError("SpacetimeDB SQL response did not contain statement rows.")

        records: List[Dict[str, Any]] = []
        for statement in payload:
            records.extend(self._statement_rows_to_dicts(statement))
        return records

    def _http_error_message(self, method: str, path: str, exc: urllib_error.HTTPError) -> str:
        """Build a readable error from a failed HTTP request."""
        response_body = ""
        try:
            response_body = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:
            response_body = ""

        detail = response_body or exc.reason or f"HTTP {exc.code}"
        return f"{method.upper()} {path} failed with HTTP {exc.code}: {detail}"

    def _http_request_sync(
        self,
        method: str,
        path: str,
        body: Optional[Any] = None,
        content_type: Optional[str] = None,
        expect_json: bool = True,
    ) -> Any:
        """Execute a blocking HTTP request against the SpacetimeDB HTTP API."""
        normalized_path = path if path.startswith("/") else f"/{path}"
        url = f"{self._server_url()}{normalized_path}"

        request_body: Optional[bytes]
        if body is None:
            request_body = None
        elif isinstance(body, (dict, list)):
            request_body = json.dumps(body).encode("utf-8")
            content_type = content_type or "application/json"
        elif isinstance(body, str):
            request_body = body.encode("utf-8")
        else:
            raise TypeError(f"Unsupported HTTP body type: {type(body).__name__}")

        headers = self._build_http_headers(content_type)
        request = urllib_request.Request(
            url,
            data=request_body,
            headers=headers,
            method=method.upper(),
        )

        try:
            with urllib_request.urlopen(request, timeout=self.config.request_timeout) as response:
                response_text = response.read().decode("utf-8", errors="replace").strip()
                if not response_text:
                    return None

                if expect_json or response_text.startswith(("{", "[")):
                    return json.loads(response_text)
                return response_text
        except urllib_error.HTTPError as exc:
            raise SpacetimeDBError(self._http_error_message(method, normalized_path, exc)) from exc
        except urllib_error.URLError as exc:
            raise STDBConnectionError(
                f"{method.upper()} {normalized_path} failed to reach SpacetimeDB: {exc.reason}"
            ) from exc

    async def _http_request(
        self,
        method: str,
        path: str,
        body: Optional[Any] = None,
        content_type: Optional[str] = None,
        expect_json: bool = True,
    ) -> Any:
        """Execute an HTTP request in a worker thread."""
        return await asyncio.to_thread(
            self._http_request_sync,
            method,
            path,
            body,
            content_type,
            expect_json,
        )

    async def _execute_sql(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SQL query against the SpacetimeDB HTTP API."""
        database_name = quote(self.config.database_name, safe="")
        payload = await self._http_request(
            "POST",
            f"/v1/database/{database_name}/sql",
            body=query,
            content_type="text/plain",
            expect_json=True,
        )
        return self._parse_sql_response(payload)

    async def _call_reducer(self, reducer_name: str, args: List[Any]) -> Any:
        """Call a reducer through the SpacetimeDB HTTP API."""
        database_name = quote(self.config.database_name, safe="")
        reducer_path = quote(reducer_name, safe="")
        return await self._http_request(
            "POST",
            f"/v1/database/{database_name}/call/{reducer_path}",
            body=args,
            content_type="application/json",
            expect_json=False,
        )

    def _apply_updates_to_asset(self, asset: MediaAsset, updates: Dict[str, Any]) -> None:
        """Apply validated update fields onto an existing MediaAsset instance."""
        for field_name, value in updates.items():
            if field_name in {"asset_id", "id"}:
                continue

            if field_name == "file_path":
                asset.file_path = Path(value)
            elif field_name in {"modified_time", "created_at", "updated_at"}:
                setattr(asset, field_name, self._coerce_datetime(value))
            elif field_name == "file_size":
                asset.file_size = int(value)
            elif field_name == "ai_tags":
                asset.ai_tags = list(dict.fromkeys(str(tag) for tag in value or [] if tag))
            elif hasattr(asset, field_name):
                setattr(asset, field_name, value)

    async def _count_for_query(self, query: str) -> int:
        """Execute a count query and return the integer result."""
        rows = await self._execute_sql(query)
        if not rows:
            return 0

        total = rows[0].get("total", 0)
        return int(total or 0)

    def _asset_to_db_format(self, asset: MediaAsset) -> Dict[str, Any]:
        """Convert MediaAsset to SpacetimeDB record format.
        
        The Rust module now derives ownership from the active SpacetimeDB
        connection instead of trusting a client-supplied identity value.
        """
        now = datetime.now(timezone.utc)

        return {
            'asset_id': asset.id,
            'owner_identity': '',
            'file_path': str(asset.file_path),
            'file_name': asset.file_name,
            'category': asset.category.lower(),
            'file_size': int(asset.file_size),
            'file_hash': asset.file_hash,
            'ai_tags': list(dict.fromkeys(asset.ai_tags or [])),  # Deduplicate
            'modified_time': self._encode_timestamp_value(asset.modified_time),
            'created_at': self._encode_timestamp_value(asset.created_at or now),
            'updated_at': self._encode_timestamp_value(asset.updated_at or now),
        }
    
    def _db_record_to_asset(self, record: Dict[str, Any]) -> MediaAsset:
        """Convert SpacetimeDB record to MediaAsset."""
        try:
            return MediaAsset(
                id=record['asset_id'],
                file_path=Path(record['file_path']),
                file_name=record['file_name'],
                category=record['category'],
                file_size=record['file_size'],
                modified_time=self._coerce_datetime(record['modified_time']),
                file_hash=record['file_hash'],
                ai_tags=list(dict.fromkeys(record.get('ai_tags', []))),
                created_at=self._coerce_datetime(record['created_at']),
                updated_at=self._coerce_datetime(record['updated_at'])
            )
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Invalid database record: {e}") from e
    
    async def _insert_batch(self, assets: List[Dict[str, Any]]) -> int:
        """Insert a batch of assets into SpacetimeDB.
        
        Args:
            assets: List of asset dictionaries
            
            Returns:
                Number of assets actually inserted
                
            Raises:
                SpacetimeDBError: If the reducer call fails
        """
        if not assets:
            return 0
        
        try:
            await self._call_reducer("insert_assets_batch", [assets])
            return len(assets)
        except Exception as e:
            logger.error(f"Database insert failed: {e}")
            raise SpacetimeDBError(f"Insert failed: {e}") from e
    
    async def _update_record(
        self,
        asset_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update a record in SpacetimeDB via the HTTP reducer API."""
        try:
            query_asset_id = self._escape_sql_literal(asset_id)
            rows = await self._execute_sql(
                f"SELECT * FROM media_assets WHERE asset_id = '{query_asset_id}' LIMIT 1"
            )
            if not rows:
                return False

            existing_asset = self._db_record_to_asset(rows[0])
            self._apply_updates_to_asset(existing_asset, updates)
            await self._call_reducer(
                "update_asset",
                [asset_id, self._asset_to_db_format(existing_asset)],
            )
            return True
        except Exception as e:
            logger.error(f"Database update failed: {e}")
            raise SpacetimeDBError(f"Update failed: {e}") from e
    
    async def _delete_records(self, asset_ids: List[str]) -> int:
        """Delete records from SpacetimeDB via the HTTP reducer API."""
        if not asset_ids:
            return 0
        
        try:
            await self._call_reducer("delete_assets_batch", [asset_ids])
            return len(asset_ids)
        except Exception as e:
            logger.error(f"Database delete failed: {e}")
            raise SpacetimeDBError(f"Delete failed: {e}") from e
    
    async def _execute_query(
        self,
        params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute a database query via the SpacetimeDB SQL HTTP API."""
        try:
            category = params.get('category')
            tags = params.get('tags')
            limit = params.get('limit', 1000)
            query_limit = 10000 if tags else limit
            query = self._build_safe_query(category, None, query_limit)
            return await self._execute_sql(query)
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            raise SpacetimeDBError(f"Query failed: {e}") from e
    
    async def _execute_count_query(self) -> Dict[str, int]:
        """Execute category count queries via the SpacetimeDB SQL HTTP API."""
        try:
            return {
                'music': await self._count_for_query(
                    "SELECT COUNT(*) AS total FROM media_assets WHERE category = 'music'"
                ),
                'sfx': await self._count_for_query(
                    "SELECT COUNT(*) AS total FROM media_assets WHERE category = 'sfx'"
                ),
                'vfx': await self._count_for_query(
                    "SELECT COUNT(*) AS total FROM media_assets WHERE category = 'vfx'"
                ),
            }
        except Exception as e:
            logger.error(f"Database count query failed: {e}")
            raise SpacetimeDBError(f"Count query failed: {e}") from e
    
    async def _handle_subscription(
        self,
        subscription_id: str,
        callback: Callable[[str, MediaAsset], None]
    ):
        """Handle subscription to change events with real WebSocket support.
        
        Stores the WebSocket subscription ID for proper cleanup on unsubscribe.
        """
        logger.info(f"Starting subscription handler: {subscription_id}")
        
        ws_subscription_id: Optional[str] = None
        
        try:
            if HAS_WEBSOCKET_CLIENT and self._client and hasattr(self._client, 'subscribe'):
                # Real WebSocket subscription via client's subscription handler
                def on_table_update(update: TableUpdate):
                    # Check if still subscribed
                    if subscription_id not in self._subscriptions:
                        return
                    
                    try:
                        if update.row:
                            asset = self._db_record_to_asset(update.row)
                            callback(update.operation.upper(), asset)
                    except Exception as e:
                        logger.warning(f"Error handling subscription event: {e}")
                
                # Subscribe to media_assets table and store the WS subscription ID
                ws_subscription_id = await self._client.subscribe(
                    "SELECT * FROM media_assets",
                    on_table_update
                )
                
                # Store the mapping from our subscription_id to ws_subscription_id
                async with self._subscription_lock:
                    if subscription_id in self._subscriptions:
                        # Store as tuple (callback, ws_subscription_id)
                        self._subscriptions[subscription_id] = (callback, ws_subscription_id)
                
                # Keep handler alive until unsubscribed
                while subscription_id in self._subscriptions:
                    await asyncio.sleep(1)
                    
            else:
                # WebSocket unavailable - just wait until unsubscribed
                while subscription_id in self._subscriptions:
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            logger.info(f"Subscription {subscription_id} cancelled")
        except Exception as e:
            logger.error(f"Subscription {subscription_id} error: {e}")
        finally:
            # Cleanup WebSocket subscription if we have one
            if ws_subscription_id and self._client and hasattr(self._client, 'unsubscribe'):
                try:
                    await self._client.unsubscribe(ws_subscription_id)
                except Exception as e:
                    logger.warning(f"Error cleaning up WebSocket subscription: {e}")
# Module exports
__all__ = [
    'SpacetimeClient',
    'SpacetimeConfig',
    'InsertResult',
    'UpdateResult',
    'DeleteResult',
    'AssetCounts',
    'QueryResult',
    'ConnectionState',
    'CircuitBreaker'
]
