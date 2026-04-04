"""Integration tests for database persistence with MediaIndexer.

Tests the full flow from indexing to database persistence.
"""

import asyncio
import pytest
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from roughcut.backend.indexing.indexer import MediaIndexer
from roughcut.backend.database.models import MediaAsset
from roughcut.backend.database.spacetime_client import SpacetimeConfig
from roughcut.config.models import MediaFolderConfig


@pytest.fixture
def temp_media_folder():
    """Create a temporary folder with sample media files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        music_dir = Path(tmpdir) / "music"
        music_dir.mkdir()
        
        # Create dummy music files
        (music_dir / "song1.mp3").write_text("dummy audio 1")
        (music_dir / "song2.mp3").write_text("dummy audio 2")
        
        yield music_dir


@pytest.fixture
def mock_spacetime_client():
    """Create a mock SpacetimeClient."""
    client = Mock()
    client.connect = AsyncMock(return_value=True)
    client.disconnect = AsyncMock()
    client.insert_assets = AsyncMock(return_value=Mock(
        inserted_count=2,
        errors=[],
        duration_ms=100.0
    ))
    client.delete_assets = AsyncMock(return_value=0)
    client.query_assets = AsyncMock(return_value=[])
    client.get_asset_counts = AsyncMock(return_value=Mock(
        music=2, sfx=0, vfx=0, total=2
    ))
    client.subscribe_to_changes = Mock(return_value="sub-123")
    client._connected = True
    return client


class TestIndexerDatabaseIntegration:
    """Test MediaIndexer integration with SpacetimeDB."""
    
    @pytest.mark.asyncio
    async def test_connect_database_success(self, mock_spacetime_client):
        """Test successful database connection."""
        indexer = MediaIndexer()
        
        with patch('roughcut.backend.indexing.indexer.get_config_manager') as mock_get_config:
            mock_config_manager = Mock()
            mock_config_manager.get_spacetime_config.return_value = {
                'host': 'localhost',
                'port': 3000,
                'database_name': 'roughcut',
                'identity_token': 'test_token'
            }
            mock_get_config.return_value = mock_config_manager
            
            with patch('roughcut.backend.indexing.indexer.SpacetimeClient') as mock_client_class:
                mock_client_class.return_value = mock_spacetime_client
                
                result = await indexer.connect_database()
                
                assert result is True
                assert indexer._db_client is not None
                mock_spacetime_client.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_database_failure(self):
        """Test database connection failure handling."""
        indexer = MediaIndexer()
        
        with patch('roughcut.backend.indexing.indexer.get_config_manager') as mock_get_config:
            mock_config_manager = Mock()
            mock_config_manager.get_spacetime_config.return_value = {
                'host': 'localhost',
                'port': 3000
            }
            mock_get_config.return_value = mock_config_manager
            
            with patch('roughcut.backend.indexing.indexer.SpacetimeClient') as mock_client_class:
                mock_client = Mock()
                mock_client.connect = AsyncMock(return_value=False)
                mock_client_class.return_value = mock_client
                
                result = await indexer.connect_database()
                
                assert result is False
    
    @pytest.mark.asyncio
    async def test_store_assets_persists_to_database(self, mock_spacetime_client):
        """Test that assets are stored to both memory and database."""
        indexer = MediaIndexer()
        indexer._db_client = mock_spacetime_client
        
        # Create test assets
        assets = [
            MediaAsset.from_file_path(
                Path("/test/music/song1.mp3"),
                category="music"
            ),
            MediaAsset.from_file_path(
                Path("/test/music/song2.mp3"),
                category="music"
            )
        ]
        
        # Store assets
        await indexer._store_assets_batch(assets)
        
        # Verify in-memory storage
        assert len(indexer._assets) == 2
        
        # Verify database persistence
        mock_spacetime_client.insert_assets.assert_called_once()
        call_args = mock_spacetime_client.insert_assets.call_args
        assert call_args[1]['batch_size'] == 500
    
    @pytest.mark.asyncio
    async def test_delete_assets_removes_from_database(self, mock_spacetime_client):
        """Test that asset deletion propagates to database."""
        indexer = MediaIndexer()
        indexer._db_client = mock_spacetime_client
        
        # Add assets to memory first
        asset1 = MediaAsset.from_file_path(
            Path("/test/music/song1.mp3"),
            category="music"
        )
        asset2 = MediaAsset.from_file_path(
            Path("/test/music/song2.mp3"),
            category="music"
        )
        indexer._assets[asset1.id] = asset1
        indexer._assets[asset2.id] = asset2
        
        # Delete assets
        await indexer._delete_assets([asset1.id, asset2.id])
        
        # Verify in-memory deletion
        assert len(indexer._assets) == 0
        
        # Verify database deletion
        mock_spacetime_client.delete_assets.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_error_does_not_block_indexing(self, mock_spacetime_client):
        """Test that database errors don't prevent in-memory indexing."""
        indexer = MediaIndexer()
        indexer._db_client = mock_spacetime_client
        
        # Make database insert fail
        mock_spacetime_client.insert_assets = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        # Create test asset
        asset = MediaAsset.from_file_path(
            Path("/test/music/song1.mp3"),
            category="music"
        )
        
        # Store asset - should not raise
        await indexer._store_assets_batch([asset])
        
        # Verify in-memory storage succeeded
        assert len(indexer._assets) == 1
    
    @pytest.mark.asyncio
    async def test_subscribe_to_remote_changes(self, mock_spacetime_client):
        """Test subscription to remote asset changes."""
        indexer = MediaIndexer()
        indexer._db_client = mock_spacetime_client
        
        # Subscribe to changes
        await indexer._subscribe_to_remote_changes()
        
        # Verify subscription was created
        mock_spacetime_client.subscribe_to_changes.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_remote_insert_updates_local_cache(self, mock_spacetime_client):
        """Test that remote inserts update local cache."""
        indexer = MediaIndexer()
        indexer._db_client = mock_spacetime_client
        
        # Capture the callback function
        callback = None
        def capture_callback(*args, **kwargs):
            nonlocal callback
            callback = kwargs.get('callback') or args[0]
        
        mock_spacetime_client.subscribe_to_changes.side_effect = capture_callback
        
        # Subscribe
        await indexer._subscribe_to_remote_changes()
        
        # Simulate remote insert via callback
        remote_asset = MediaAsset.from_file_path(
            Path("/remote/song.mp3"),
            category="music"
        )
        callback("INSERT", remote_asset)
        
        # Verify asset was added to local cache
        assert remote_asset.id in indexer._assets
    
    @pytest.mark.asyncio
    async def test_remote_delete_removes_from_local_cache(self, mock_spacetime_client):
        """Test that remote deletes remove from local cache."""
        indexer = MediaIndexer()
        indexer._db_client = mock_spacetime_client
        
        # Add asset to local cache
        local_asset = MediaAsset.from_file_path(
            Path("/test/song.mp3"),
            category="music"
        )
        indexer._assets[local_asset.id] = local_asset
        
        # Capture callback
        callback = None
        def capture_callback(*args, **kwargs):
            nonlocal callback
            callback = kwargs.get('callback') or args[0]
        
        mock_spacetime_client.subscribe_to_changes.side_effect = capture_callback
        
        # Subscribe
        await indexer._subscribe_to_remote_changes()
        
        # Simulate remote delete
        callback("DELETE", local_asset)
        
        # Verify asset was removed from local cache
        assert local_asset.id not in indexer._assets


class TestIndexerDatabaseReset:
    """Test database cleanup on indexer reset."""
    
    def test_reset_disconnects_database(self):
        """Test that reset disconnects from database."""
        indexer = MediaIndexer()
        
        # Mock the disconnect method
        indexer.disconnect_database = AsyncMock()
        
        # Create a mock event loop that is not running
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            indexer.reset()
        
        # Verify disconnect was called via run_until_complete
        mock_loop.run_until_complete.assert_called_once()
    
    def test_reset_with_running_loop(self):
        """Test reset when event loop is already running."""
        indexer = MediaIndexer()
        
        # Mock the disconnect method
        indexer.disconnect_database = AsyncMock()
        
        # Create a mock event loop that IS running
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            with patch('asyncio.create_task') as mock_create_task:
                indexer.reset()
                
                # Verify create_task was used for disconnect
                mock_create_task.assert_called_once()


__all__ = [
    'TestIndexerDatabaseIntegration',
    'TestIndexerDatabaseReset'
]
