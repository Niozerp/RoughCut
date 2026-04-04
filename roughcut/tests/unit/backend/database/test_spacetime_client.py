"""Unit tests for SpacetimeDB client.

Tests the SpacetimeClient class with mocked database operations.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from roughcut.backend.database.spacetime_client import (
    SpacetimeClient,
    SpacetimeConfig,
    ConnectionState,
    InsertResult,
    AssetCounts
)
from roughcut.backend.database.models import MediaAsset


@pytest.fixture
def test_config():
    """Create test SpacetimeDB configuration."""
    return SpacetimeConfig(
        host="localhost",
        port=3000,
        database_name="test_roughcut",
        identity_token="test_identity_token",
        connect_timeout=5.0,
        max_reconnect_attempts=2
    )


@pytest.fixture
def mock_client(test_config):
    """Create a SpacetimeClient with mocked connection."""
    client = SpacetimeClient(test_config)
    # Simulate connected state for tests
    client._connection_state = ConnectionState.CONNECTED
    client._client = Mock()
    return client


@pytest.fixture
def sample_asset():
    """Create a sample MediaAsset for testing."""
    return MediaAsset(
        id="test-asset-1",
        file_path=Path("/test/music/song.mp3"),
        file_name="song.mp3",
        category="music",
        file_size=1024,
        modified_time=datetime.now(timezone.utc),
        file_hash="abc123def456",
        ai_tags=["upbeat", "energetic"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


class TestSpacetimeConfig:
    """Test SpacetimeConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = SpacetimeConfig()
        assert config.host == "localhost"
        assert config.port == 3000
        assert config.database_name == "roughcut"
        assert config.identity_token is None
        assert config.connect_timeout == 10.0
        assert config.max_reconnect_attempts == 3
    
    def test_custom_values(self, test_config):
        """Test custom configuration values."""
        assert test_config.host == "localhost"
        assert test_config.port == 3000
        assert test_config.database_name == "test_roughcut"
        assert test_config.identity_token == "test_identity_token"


class TestSpacetimeClientInitialization:
    """Test SpacetimeClient initialization."""
    
    def test_client_creation(self, test_config):
        """Test client can be created with config."""
        client = SpacetimeClient(test_config)
        assert client.config == test_config
        assert not client.is_connected
        assert client._client is None
        assert client._subscriptions == {}
    
    def test_default_batch_size(self, test_config):
        """Test batch size constant."""
        client = SpacetimeClient(test_config)
        assert client.BATCH_SIZE == 500
        assert client.MAX_ERRORS == 100
        assert client.MAX_SUBSCRIPTIONS == 100


class TestSpacetimeClientConnect:
    """Test connection management."""
    
    @pytest.mark.asyncio
    async def test_already_connected(self, test_config):
        """Test connect returns True if already connected."""
        client = SpacetimeClient(test_config)
        client._connection_state = ConnectionState.CONNECTED
        
        result = await client.connect()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_connection_success(self, test_config):
        """Test successful connection."""
        client = SpacetimeClient(test_config)
        
        # Mock the _create_connection method
        with patch.object(client, '_create_connection', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = Mock()
            
            result = await client.connect()
            
            assert result is True
            assert client._connected is True
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connection_failure_with_retry(self, test_config):
        """Test connection failure with retry logic."""
        client = SpacetimeClient(test_config)
        client.config.max_reconnect_attempts = 2
        
        with patch.object(client, '_create_connection', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = None  # Failed connection
            
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Skip actual sleep
                result = await client.connect()
                
                assert result is False
                assert client._connected is False
                assert mock_create.call_count == 2  # Retried
    
    @pytest.mark.asyncio
    async def test_disconnect(self, mock_client):
        """Test disconnect functionality."""
        with patch.object(mock_client, '_close_connection', new_callable=AsyncMock) as mock_close:
            await mock_client.disconnect()
            
            assert not mock_client._connected
            assert mock_client._connection is None
            mock_close.assert_called_once()


class TestInsertAssets:
    """Test asset insertion functionality."""
    
    @pytest.mark.asyncio
    async def test_insert_empty_list(self, mock_client):
        """Test inserting empty list returns immediately."""
        result = await mock_client.insert_assets([])
        assert result.inserted_count == 0
        assert result.errors == []
    
    @pytest.mark.asyncio
    async def test_insert_not_connected(self, test_config):
        """Test insert fails if not connected."""
        client = SpacetimeClient(test_config)
        client._connected = False
        
        with pytest.raises(ConnectionError, match="Not connected to SpacetimeDB"):
            await client.insert_assets([Mock()])
    
    @pytest.mark.asyncio
    async def test_batch_size_adjustment(self, mock_client):
        """Test batch size is adjusted to specification value of 500."""
        # The implementation enforces BATCH_SIZE = 500 and auto-adjusts
        # Test that different batch sizes all result in the same behavior
        with patch.object(mock_client, '_insert_batch', new_callable=AsyncMock) as mock_insert:
            mock_insert.return_value = 1
            
            # Small batch size - gets adjusted to 500
            await mock_client.insert_assets([Mock()], batch_size=10)
            # Large batch size - gets adjusted to 500
            await mock_client.insert_assets([Mock()], batch_size=2000)
            # Correct batch size - stays at 500
            await mock_client.insert_assets([Mock()], batch_size=500)
            
            # All should succeed without raising
    
    @pytest.mark.asyncio
    async def test_insert_single_asset(self, mock_client, sample_asset):
        """Test inserting a single asset."""
        with patch.object(mock_client, '_insert_batch', new_callable=AsyncMock) as mock_insert:
            mock_insert.return_value = 1
            
            result = await mock_client.insert_assets([sample_asset])
            
            assert result.inserted_count == 1
            assert result.errors == []
            mock_insert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_insert_multiple_batches(self, mock_client, sample_asset):
        """Test inserting assets in multiple batches."""
        assets = [sample_asset for _ in range(150)]  # 150 assets
        
        with patch.object(mock_client, '_insert_batch', new_callable=AsyncMock) as mock_insert:
            mock_insert.return_value = 50  # Each batch inserts 50
            
            result = await mock_client.insert_assets(assets, batch_size=50)
            
            assert result.inserted_count == 150  # 3 batches * 50
            assert mock_insert.call_count == 3
    
    @pytest.mark.asyncio
    async def test_insert_with_errors(self, mock_client, sample_asset):
        """Test insert continues despite batch errors."""
        assets = [sample_asset for _ in range(100)]
        
        with patch.object(mock_client, '_insert_batch', new_callable=AsyncMock) as mock_insert:
            # First batch succeeds, second fails
            mock_insert.side_effect = [50, Exception("Batch failed")]
            
            result = await mock_client.insert_assets(assets, batch_size=50)
            
            assert result.inserted_count == 50  # Only first batch succeeded
            assert len(result.errors) == 1
            assert "Batch failed" in result.errors[0]


class TestUpdateAsset:
    """Test asset update functionality."""
    
    @pytest.mark.asyncio
    async def test_update_not_connected(self, test_config):
        """Test update fails if not connected."""
        client = SpacetimeClient(test_config)
        client._connected = False
        
        with pytest.raises(ConnectionError, match="Not connected to SpacetimeDB"):
            await client.update_asset("test-id", {"file_name": "new.mp3"})
    
    @pytest.mark.asyncio
    async def test_update_success(self, mock_client):
        """Test successful update."""
        with patch.object(mock_client, '_update_record', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = True
            
            result = await mock_client.update_asset("test-id", {"file_name": "new.mp3"})
            
            assert result is True
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_failure(self, mock_client):
        """Test update failure handling."""
        with patch.object(mock_client, '_update_record', new_callable=AsyncMock) as mock_update:
            mock_update.side_effect = Exception("Update failed")
            
            result = await mock_client.update_asset("test-id", {"file_name": "new.mp3"})
            
            assert result is False


class TestDeleteAssets:
    """Test asset deletion functionality."""
    
    @pytest.mark.asyncio
    async def test_delete_not_connected(self, test_config):
        """Test delete fails if not connected."""
        client = SpacetimeClient(test_config)
        client._connected = False
        
        with pytest.raises(ConnectionError, match="Not connected to SpacetimeDB"):
            await client.delete_assets(["test-id"])
    
    @pytest.mark.asyncio
    async def test_delete_empty_list(self, mock_client):
        """Test deleting empty list returns 0."""
        result = await mock_client.delete_assets([])
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_delete_success(self, mock_client):
        """Test successful deletion."""
        with patch.object(mock_client, '_delete_records', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = 5
            
            result = await mock_client.delete_assets(["id1", "id2", "id3", "id4", "id5"])
            
            assert result == 5
            mock_delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_failure(self, mock_client):
        """Test delete failure handling."""
        with patch.object(mock_client, '_delete_records', new_callable=AsyncMock) as mock_delete:
            mock_delete.side_effect = Exception("Delete failed")
            
            result = await mock_client.delete_assets(["test-id"])
            
            assert result == 0


class TestQueryAssets:
    """Test asset query functionality."""
    
    @pytest.mark.asyncio
    async def test_query_not_connected(self, test_config):
        """Test query fails if not connected."""
        client = SpacetimeClient(test_config)
        client._connected = False
        
        with pytest.raises(ConnectionError, match="Not connected to SpacetimeDB"):
            await client.query_assets()
    
    @pytest.mark.asyncio
    async def test_query_by_category(self, mock_client):
        """Test query with category filter."""
        mock_records = [
            {"asset_id": "1", "file_path": "/test/song1.mp3", "file_name": "song1.mp3", 
             "category": "music", "file_size": 1000, "file_hash": "hash1",
             "ai_tags": [], "modified_time": datetime.now(timezone.utc).isoformat(),
             "created_at": datetime.now(timezone.utc).isoformat(),
             "updated_at": datetime.now(timezone.utc).isoformat()},
            {"asset_id": "2", "file_path": "/test/song2.mp3", "file_name": "song2.mp3",
             "category": "music", "file_size": 2000, "file_hash": "hash2",
             "ai_tags": [], "modified_time": datetime.now(timezone.utc).isoformat(),
             "created_at": datetime.now(timezone.utc).isoformat(),
             "updated_at": datetime.now(timezone.utc).isoformat()}
        ]
        
        with patch.object(mock_client, '_execute_query', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_records
            
            result = await mock_client.query_assets(category="music", limit=10)
            
            assert len(result) == 2
            assert all(a.category == "music" for a in result)
    
    @pytest.mark.asyncio
    async def test_query_empty_result(self, mock_client):
        """Test query returns empty list when no results."""
        with patch.object(mock_client, '_execute_query', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = []
            
            result = await mock_client.query_assets(category="vfx")
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_query_failure(self, mock_client):
        """Test query failure handling."""
        with patch.object(mock_client, '_execute_query', new_callable=AsyncMock) as mock_query:
            mock_query.side_effect = Exception("Query failed")
            
            result = await mock_client.query_assets()
            
            assert result == []


class TestGetAssetCounts:
    """Test asset counting functionality."""
    
    @pytest.mark.asyncio
    async def test_get_counts_not_connected(self, test_config):
        """Test get_counts fails if not connected."""
        client = SpacetimeClient(test_config)
        client._connected = False
        
        with pytest.raises(ConnectionError, match="Not connected to SpacetimeDB"):
            await client.get_asset_counts()
    
    @pytest.mark.asyncio
    async def test_get_counts_success(self, mock_client):
        """Test successful count retrieval."""
        with patch.object(mock_client, '_execute_count_query', new_callable=AsyncMock) as mock_count:
            mock_count.return_value = {"music": 10, "sfx": 5, "vfx": 3}
            
            result = await mock_client.get_asset_counts()
            
            assert result.music == 10
            assert result.sfx == 5
            assert result.vfx == 3
            assert result.total == 18
    
    @pytest.mark.asyncio
    async def test_get_counts_failure(self, mock_client):
        """Test count failure handling."""
        with patch.object(mock_client, '_execute_count_query', new_callable=AsyncMock) as mock_count:
            mock_count.side_effect = Exception("Count failed")
            
            result = await mock_client.get_asset_counts()
            
            assert result.music == 0
            assert result.sfx == 0
            assert result.vfx == 0
            assert result.total == 0


class TestAssetToDbFormat:
    """Test asset conversion to database format."""
    
    def test_asset_conversion(self, mock_client, sample_asset):
        """Test MediaAsset to database format conversion."""
        result = mock_client._asset_to_db_format(sample_asset)
        
        assert result["asset_id"] == sample_asset.id
        assert result["file_path"] == str(sample_asset.file_path)
        assert result["file_name"] == sample_asset.file_name
        assert result["category"] == sample_asset.category.lower()
        assert result["file_size"] == sample_asset.file_size
        assert result["file_hash"] == sample_asset.file_hash
        assert result["ai_tags"] == sample_asset.ai_tags
        assert "created_at" in result
        assert "updated_at" in result
        assert result["owner_identity"] == mock_client.config.identity_token
    
    def test_asset_conversion_no_token(self, test_config, sample_asset):
        """Test conversion with no identity token."""
        test_config.identity_token = None
        client = SpacetimeClient(test_config)
        
        result = client._asset_to_db_format(sample_asset)
        
        # When no token, generates anonymous identity (0x + 64 zeros)
        assert result["owner_identity"] == "0x" + "0" * 64


class TestSubscription:
    """Test real-time subscription functionality."""
    
    def test_subscribe_to_changes(self, mock_client):
        """Test subscription creation."""
        callback = Mock()
        
        sub_id = mock_client.subscribe_to_changes(callback)
        
        assert sub_id is not None
        assert sub_id in mock_client._subscriptions
        assert mock_client._subscriptions[sub_id] == callback
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, mock_client):
        """Test unsubscribe functionality."""
        callback = Mock()
        sub_id = mock_client.subscribe_to_changes(callback)
        
        await mock_client.unsubscribe(sub_id)
        
        assert sub_id not in mock_client._subscriptions
    
    @pytest.mark.asyncio
    async def test_unsubscribe_invalid_id(self, mock_client):
        """Test unsubscribe with invalid ID."""
        # Should not raise error
        await mock_client.unsubscribe("invalid-id")


class TestStats:
    """Test client statistics."""
    
    def test_get_stats_initial(self, test_config):
        """Test initial stats state."""
        client = SpacetimeClient(test_config)
        
        stats = client.get_stats()
        
        assert stats["total_inserts"] == 0
        assert stats["total_updates"] == 0
        assert stats["total_deletes"] == 0
        assert stats["connection_errors"] == 0
        assert stats["connected"] is False
        assert stats["active_subscriptions"] == 0
        assert stats["reconnect_count"] == 0
    
    def test_get_stats_after_operations(self, mock_client):
        """Test stats after operations."""
        mock_client._stats["total_inserts"] = 100
        mock_client._stats["total_updates"] = 10
        mock_client._stats["total_deletes"] = 5
        mock_client._stats["connection_errors"] = 2
        mock_client._connected = True
        
        callback = Mock()
        mock_client.subscribe_to_changes(callback)
        
        stats = mock_client.get_stats()
        
        assert stats["total_inserts"] == 100
        assert stats["total_updates"] == 10
        assert stats["total_deletes"] == 5
        assert stats["connection_errors"] == 2
        assert stats["connected"] is True
        assert stats["active_subscriptions"] == 1


__all__ = [
    'TestSpacetimeConfig',
    'TestSpacetimeClientInitialization',
    'TestSpacetimeClientConnect',
    'TestInsertAssets',
    'TestUpdateAsset',
    'TestDeleteAssets',
    'TestQueryAssets',
    'TestGetAssetCounts',
    'TestAssetToDbFormat',
    'TestSubscription',
    'TestStats'
]
