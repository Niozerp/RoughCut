"""Notion API integration module.

Provides Notion API client for media database synchronization.
"""

from .client import NotionClient, is_notion_available
from .sync import NotionSyncOrchestrator, get_sync_orchestrator, queue_asset_for_sync, queue_assets_batch
from .errors import (
    NotionSyncError,
    NotionSyncErrorCategory,
    NotionAPIError,
    NotionAuthError,
    NotionRateLimitError,
    NotionConfigError,
    NotionNetworkError,
    NotionTimeoutError,
    NotionValidationError,
    classify_notion_error
)
from .models import (
    ConnectionStatus,
    ErrorType,
    ValidationResult,
    NotionPage,
    SyncResult,
    SyncStatus,
    MediaAssetNotionMapping
)

__all__ = [
    'NotionClient',
    'is_notion_available',
    'NotionSyncOrchestrator',
    'get_sync_orchestrator',
    'queue_asset_for_sync',
    'queue_assets_batch',
    'NotionSyncError',
    'NotionSyncErrorCategory',
    'NotionAPIError',
    'NotionAuthError',
    'NotionRateLimitError',
    'NotionConfigError',
    'NotionNetworkError',
    'NotionTimeoutError',
    'NotionValidationError',
    'classify_notion_error',
    'ConnectionStatus',
    'ErrorType',
    'ValidationResult',
    'NotionPage',
    'SyncResult',
    'SyncStatus',
    'MediaAssetNotionMapping'
]
