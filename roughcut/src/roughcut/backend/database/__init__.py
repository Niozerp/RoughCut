"""Database module for RoughCut.

Provides data models, SpacetimeDB client, and query operations
for media asset persistence and real-time synchronization.
"""

from .models import MediaAsset, IndexState, IndexResult, ScanResult
from .spacetime_client import (
    SpacetimeClient,
    SpacetimeConfig,
    InsertResult,
    UpdateResult,
    DeleteResult,
    AssetCounts,
    QueryResult,
    ConnectionState,
    CircuitBreaker
)
from .websocket_client import (
    SpacetimeWebSocketClient,
    ConnectionConfig,
    SpacetimeIdentity,
    ReducerResult,
    TableUpdate,
    MessageType,
    connect_to_spacetime_db
)
from .queries import (
    AssetQueryBuilder,
    get_assets_by_category,
    get_assets_by_tags,
    asset_exists,
    get_duplicate_assets
)

__all__ = [
    # Models
    'MediaAsset',
    'IndexState',
    'IndexResult',
    'ScanResult',
    # SpacetimeDB Client (High-level)
    'SpacetimeClient',
    'SpacetimeConfig',
    'InsertResult',
    'UpdateResult',
    'DeleteResult',
    'AssetCounts',
    'QueryResult',
    'ConnectionState',
    'CircuitBreaker',
    # WebSocket Client (Low-level)
    'SpacetimeWebSocketClient',
    'ConnectionConfig',
    'SpacetimeIdentity',
    'ReducerResult',
    'TableUpdate',
    'MessageType',
    'connect_to_spacetime_db',
    # Query Builder
    'AssetQueryBuilder',
    'get_assets_by_category',
    'get_assets_by_tags',
    'asset_exists',
    'get_duplicate_assets'
]
