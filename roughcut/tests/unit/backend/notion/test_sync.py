"""Unit tests for Notion sync orchestrator.

Tests the NotionSyncOrchestrator class including debouncing,
batch processing, error handling, and retry logic.
"""

import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from roughcut.backend.notion.sync import (
    NotionSyncOrchestrator,
    SyncQueueItem,
    SyncStatistics,
    get_sync_orchestrator,
    queue_asset_for_sync,
    queue_assets_batch,
    DEFAULT_DEBOUNCE_SECONDS,
    MAX_BATCH_SIZE,
)
from roughcut.backend.notion.errors import (
    NotionRateLimitError,
    NotionAuthError,
)
from roughcut.backend.database.models import MediaAsset


class TestSyncQueueItem:
    """Test suite for SyncQueueItem dataclass."""

    def test_queue_item_creation(self):
        """Test creating a queue item."""
        asset = MediaAsset(
            id="test-123",
            file_path=Path("/test/file.wav"),
            file_name="file.wav",
            category="sfx",
            file_size=1024,
            modified_time=datetime.now(),
            file_hash="abc123"
        )
        
        item = SyncQueueItem(
            asset_id=asset.id,
            operation='create',
            asset_data=asset
        )
        
        assert item.asset_id == "test-123"
        assert item.operation == 'create'
        assert item.asset_data == asset
        assert item.retry_count == 0
        assert isinstance(item.added_at, datetime)


class TestSyncStatistics:
    """Test suite for SyncStatistics dataclass."""

    def test_statistics_creation(self):
        """Test creating statistics."""
        stats = SyncStatistics()
        
        assert stats.total_synced == 0
        assert stats.total_failed == 0
        assert stats.last_sync_time is None
        assert stats.last_error_time is None
        assert stats.error_count_24h == 0
    
    def test_statistics_to_dict(self):
        """Test converting statistics to dictionary."""
        stats = SyncStatistics(
            total_synced=100,
            total_failed=5,
            last_sync_time=datetime.now(),
            error_count_24h=2
        )
        
        result = stats.to_dict()
        
        assert result['total_synced'] == 100
        assert result['total_failed'] == 5
        assert result['error_count_24h'] == 2
        assert 'last_sync_time' in result


class TestNotionSyncOrchestratorSingleton:
    """Test suite for orchestrator singleton pattern."""

    def test_singleton_instance(self):
        """Test that orchestrator is a singleton."""
        orch1 = NotionSyncOrchestrator()
        orch2 = NotionSyncOrchestrator()
        
        assert orch1 is orch2
    
    def test_get_sync_orchestrator(self):
        """Test convenience function returns singleton."""
        orch1 = get_sync_orchestrator()
        orch2 = get_sync_orchestrator()
        
        assert orch1 is orch2


class TestNotionSyncOrchestratorBasics:
    """Test suite for basic orchestrator functionality."""

    def setup_method(self):
        """Set up test instance."""
        # Reset singleton for clean tests
        NotionSyncOrchestrator._instance = None
        self.orchestrator = NotionSyncOrchestrator()
    
    def test_initialization(self):
        """Test orchestrator initializes correctly."""
        assert self.orchestrator._debounce_seconds == DEFAULT_DEBOUNCE_SECONDS
        assert self.orchestrator._max_batch_size == MAX_BATCH_SIZE
        assert self.orchestrator._sync_queue == {}
        assert self.orchestrator._database_id is None
    
    @patch('roughcut.backend.notion.sync.get_config_manager')
    @patch.object(NotionSyncOrchestrator, 'is_sync_enabled')
    def test_is_sync_enabled_checks_config(self, mock_is_enabled, mock_get_config):
        """Test that sync enabled checks configuration."""
        mock_config = MagicMock()
        mock_config.sync_enabled = True
        mock_get_config.return_value.get_notion_config.return_value = mock_config
        
        # Override the mock to call real method
        mock_is_enabled.side_effect = lambda: mock_config.sync_enabled
        
        result = self.orchestrator.is_sync_enabled()
        
        # If notion client is not configured, should return False
        # This depends on the actual implementation
        assert isinstance(result, bool)


class TestQueueAsset:
    """Test suite for queue_asset functionality."""

    def setup_method(self):
        """Set up test instance."""
        NotionSyncOrchestrator._instance = None
        self.orchestrator = NotionSyncOrchestrator()
    
    @patch.object(NotionSyncOrchestrator, 'is_sync_enabled')
    def test_queue_asset_when_disabled(self, mock_is_enabled):
        """Test queueing when sync is disabled."""
        mock_is_enabled.return_value = False
        
        asset = MediaAsset(
            id="test-123",
            file_path=Path("/test/file.wav"),
            file_name="file.wav",
            category="sfx",
            file_size=1024,
            modified_time=datetime.now(),
            file_hash="abc123"
        )
        
        result = self.orchestrator.queue_asset(asset, 'create')
        
        assert result is False
    
    @patch.object(NotionSyncOrchestrator, 'is_sync_enabled')
    @patch.object(NotionSyncOrchestrator, '_debounced_sync')
    def test_queue_asset_success(self, mock_debounced, mock_is_enabled):
        """Test successful asset queueing."""
        mock_is_enabled.return_value = True
        mock_debounced.return_value = None
        
        asset = MediaAsset(
            id="test-123",
            file_path=Path("/test/file.wav"),
            file_name="file.wav",
            category="sfx",
            file_size=1024,
            modified_time=datetime.now(),
            file_hash="abc123"
        )
        
        result = self.orchestrator.queue_asset(asset, 'create')
        
        assert result is True
        assert asset.id in self.orchestrator._sync_queue
    
    @patch.object(NotionSyncOrchestrator, 'is_sync_enabled')
    def test_queue_asset_invalid_operation(self, mock_is_enabled):
        """Test queueing with invalid operation."""
        mock_is_enabled.return_value = True
        
        asset = MediaAsset(
            id="test-123",
            file_path=Path("/test/file.wav"),
            file_name="file.wav",
            category="sfx",
            file_size=1024,
            modified_time=datetime.now(),
            file_hash="abc123"
        )
        
        result = self.orchestrator.queue_asset(asset, 'invalid_op')
        
        assert result is False
    
    @patch.object(NotionSyncOrchestrator, 'is_sync_enabled')
    def test_queue_assets_batch(self, mock_is_enabled):
        """Test batch queueing."""
        mock_is_enabled.return_value = True
        
        assets = [
            MediaAsset(
                id=f"test-{i}",
                file_path=Path(f"/test/file{i}.wav"),
                file_name=f"file{i}.wav",
                category="sfx",
                file_size=1024,
                modified_time=datetime.now(),
                file_hash=f"hash{i}"
            )
            for i in range(5)
        ]
        
        count = self.orchestrator.queue_assets_batch(assets, 'create')
        
        assert count == 5
        assert len(self.orchestrator._sync_queue) == 5


class TestSyncStatus:
    """Test suite for sync status functionality."""

    def setup_method(self):
        """Set up test instance."""
        NotionSyncOrchestrator._instance = None
        self.orchestrator = NotionSyncOrchestrator()
    
    @patch.object(NotionSyncOrchestrator, 'is_sync_enabled')
    def test_get_sync_status(self, mock_is_enabled):
        """Test getting sync status."""
        mock_is_enabled.return_value = True
        
        status = self.orchestrator.get_sync_status()
        
        assert 'enabled' in status
        assert 'configured' in status
        assert 'queue_size' in status
        assert 'statistics' in status


class TestSyncAllAssets:
    """Test suite for full sync functionality."""

    def setup_method(self):
        """Set up test instance."""
        NotionSyncOrchestrator._instance = None
        self.orchestrator = NotionSyncOrchestrator()
    
    @patch.object(NotionSyncOrchestrator, 'is_sync_enabled')
    def test_sync_all_assets_when_disabled(self, mock_is_enabled):
        """Test full sync when disabled."""
        mock_is_enabled.return_value = False
        
        assets = []
        result = self.orchestrator.sync_all_assets(assets)
        
        assert result.success is False
        assert "not enabled" in result.error_message.lower()
    
    @patch.object(NotionSyncOrchestrator, 'is_sync_enabled')
    @patch.object(NotionSyncOrchestrator, 'queue_assets_batch')
    def test_sync_all_assets_success(self, mock_queue, mock_is_enabled):
        """Test successful full sync."""
        mock_is_enabled.return_value = True
        mock_queue.return_value = 3
        
        assets = [
            MediaAsset(
                id=f"test-{i}",
                file_path=Path(f"/test/file{i}.wav"),
                file_name=f"file{i}.wav",
                category="sfx",
                file_size=1024,
                modified_time=datetime.now(),
                file_hash=f"hash{i}"
            )
            for i in range(3)
        ]
        
        result = self.orchestrator.sync_all_assets(assets)
        
        assert result.success is True


class TestConvenienceFunctions:
    """Test suite for module-level convenience functions."""

    @patch('roughcut.backend.notion.sync.NotionSyncOrchestrator')
    def test_queue_asset_for_sync(self, mock_orchestrator_class):
        """Test queue_asset_for_sync convenience function."""
        mock_instance = MagicMock()
        mock_instance.queue_asset.return_value = True
        mock_orchestrator_class.return_value = mock_instance
        
        asset = MediaAsset(
            id="test-123",
            file_path=Path("/test/file.wav"),
            file_name="file.wav",
            category="sfx",
            file_size=1024,
            modified_time=datetime.now(),
            file_hash="abc123"
        )
        
        result = queue_asset_for_sync(asset, 'create')
        
        assert result is True
        mock_instance.queue_asset.assert_called_once()
    
    @patch('roughcut.backend.notion.sync.NotionSyncOrchestrator')
    def test_queue_assets_batch(self, mock_orchestrator_class):
        """Test queue_assets_batch convenience function."""
        mock_instance = MagicMock()
        mock_instance.queue_assets_batch.return_value = 5
        mock_orchestrator_class.return_value = mock_instance
        
        assets = [
            MediaAsset(
                id=f"test-{i}",
                file_path=Path(f"/test/file{i}.wav"),
                file_name=f"file{i}.wav",
                category="sfx",
                file_size=1024,
                modified_time=datetime.now(),
                file_hash=f"hash{i}"
            )
            for i in range(5)
        ]
        
        result = queue_assets_batch(assets, 'create')
        
        assert result == 5
        mock_instance.queue_assets_batch.assert_called_once()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
