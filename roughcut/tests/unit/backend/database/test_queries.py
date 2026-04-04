"""Unit tests for database query operations.

Tests the AssetQueryBuilder and query helper functions.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from roughcut.backend.database.queries import (
    AssetQueryBuilder,
    get_assets_by_category,
    get_assets_by_tags,
    asset_exists,
    get_duplicate_assets
)
from roughcut.backend.database.models import MediaAsset


@pytest.fixture
def mock_client():
    """Create a mock SpacetimeClient."""
    client = Mock()
    client.query_assets = AsyncMock()
    return client


@pytest.fixture
def sample_assets():
    """Create sample assets for testing."""
    return [
        MediaAsset(
            id="asset-1",
            file_path=Path("/test/music/song1.mp3"),
            file_name="song1.mp3",
            category="music",
            file_size=1000,
            modified_time=datetime.now(timezone.utc),
            file_hash="hash1",
            ai_tags=["upbeat", "pop"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        ),
        MediaAsset(
            id="asset-2",
            file_path=Path("/test/music/song2.mp3"),
            file_name="song2.mp3",
            category="music",
            file_size=2000,
            modified_time=datetime.now(timezone.utc),
            file_hash="hash2",
            ai_tags=["calm", "acoustic"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        ),
        MediaAsset(
            id="asset-3",
            file_path=Path("/test/sfx/explosion.wav"),
            file_name="explosion.wav",
            category="sfx",
            file_size=500,
            modified_time=datetime.now(timezone.utc),
            file_hash="hash3",
            ai_tags=["loud", "impact"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        ),
    ]


class TestAssetQueryBuilder:
    """Test AssetQueryBuilder class."""
    
    def test_query_builder_creation(self, mock_client):
        """Test query builder can be created."""
        builder = AssetQueryBuilder(mock_client)
        assert builder.client == mock_client
        assert builder._category is None
        assert builder._tags == []
        assert builder._limit == 1000
    
    def test_category_filter(self, mock_client):
        """Test category filter method."""
        builder = AssetQueryBuilder(mock_client)
        result = builder.category("music")
        
        assert result == builder  # Returns self for chaining
        assert builder._category == "music"
    
    def test_category_filter_lowercase(self, mock_client):
        """Test category is lowercased."""
        builder = AssetQueryBuilder(mock_client)
        builder.category("MUSIC")
        
        assert builder._category == "music"
    
    def test_tags_filter(self, mock_client):
        """Test tags filter method."""
        builder = AssetQueryBuilder(mock_client)
        result = builder.tags(["upbeat", "Pop"])  # Mixed case
        
        assert result == builder
        assert builder._tags == ["upbeat", "pop"]  # Lowercased
    
    def test_limit_validation(self, mock_client):
        """Test limit validation."""
        builder = AssetQueryBuilder(mock_client)
        
        with pytest.raises(ValueError, match="Limit must be positive"):
            builder.limit(0)
        
        with pytest.raises(ValueError, match="Limit must be positive"):
            builder.limit(-1)
    
    def test_limit_valid(self, mock_client):
        """Test valid limit setting."""
        builder = AssetQueryBuilder(mock_client)
        builder.limit(500)
        
        assert builder._limit == 500
    
    def test_file_hash_filter(self, mock_client):
        """Test file hash filter."""
        builder = AssetQueryBuilder(mock_client)
        result = builder.file_hash("abc123")
        
        assert result == builder
        assert builder._file_hash == "abc123"
    
    @pytest.mark.asyncio
    async def test_execute_query(self, mock_client, sample_assets):
        """Test query execution."""
        mock_client.query_assets.return_value = sample_assets[:2]  # Music assets
        
        builder = AssetQueryBuilder(mock_client)
        builder.category("music").limit(100)
        
        result = await builder.execute()
        
        assert len(result) == 2
        mock_client.query_assets.assert_called_once_with(
            category="music",
            tags=None,
            limit=100
        )
    
    @pytest.mark.asyncio
    async def test_count_method(self, mock_client):
        """Test count method."""
        # Mock get_asset_counts response
        mock_counts = Mock()
        mock_counts.music = 10
        mock_counts.sfx = 5
        mock_counts.vfx = 3
        mock_counts.total = 18
        
        mock_client.get_asset_counts = AsyncMock(return_value=mock_counts)
        mock_client.query_assets = AsyncMock(return_value=[])  # Empty for count
        
        builder = AssetQueryBuilder(mock_client)
        builder.category("music")
        
        result = await builder.count()
        
        assert result == 10


class TestGetAssetsByCategory:
    """Test get_assets_by_category helper."""
    
    @pytest.mark.asyncio
    async def test_get_by_category(self, mock_client, sample_assets):
        """Test getting assets by category."""
        mock_client.query_assets.return_value = [a for a in sample_assets if a.category == "music"]
        
        result = await get_assets_by_category(mock_client, "music", limit=100)
        
        assert len(result) == 2
        assert all(a.category == "music" for a in result)
        mock_client.query_assets.assert_called_once_with(
            category="music",
            limit=100
        )


class TestGetAssetsByTags:
    """Test get_assets_by_tags helper."""
    
    @pytest.mark.asyncio
    async def test_get_by_tags_any(self, mock_client, sample_assets):
        """Test getting assets matching any tag."""
        mock_client.query_assets.return_value = sample_assets
        
        result = await get_assets_by_tags(mock_client, ["upbeat"], match_all=False)
        
        assert len(result) == 3  # All returned (mock returns all)
        mock_client.query_assets.assert_called_once_with(
            tags=["upbeat"],
            limit=1000
        )
    
    @pytest.mark.asyncio
    async def test_get_by_tags_all(self, mock_client):
        """Test getting assets matching all tags."""
        # Create asset with multiple tags
        asset = Mock()
        asset.ai_tags = ["upbeat", "Pop", "Energetic"]
        mock_client.query_assets.return_value = [asset]
        
        result = await get_assets_by_tags(mock_client, ["upbeat", "pop"], match_all=True)
        
        assert len(result) == 1


class TestAssetExists:
    """Test asset_exists helper."""
    
    @pytest.mark.asyncio
    async def test_asset_exists_found(self, mock_client, sample_assets):
        """Test finding existing asset by hash."""
        mock_client.query_assets.return_value = sample_assets
        
        result = await asset_exists(mock_client, "hash1")
        
        assert result is not None
        assert result.id == "asset-1"
    
    @pytest.mark.asyncio
    async def test_asset_exists_not_found(self, mock_client, sample_assets):
        """Test when asset is not found."""
        mock_client.query_assets.return_value = sample_assets
        
        result = await asset_exists(mock_client, "nonexistent_hash")
        
        assert result is None


class TestGetDuplicateAssets:
    """Test get_duplicate_assets helper."""
    
    @pytest.mark.asyncio
    async def test_find_duplicates(self, mock_client):
        """Test finding duplicate assets by hash."""
        # Create assets with duplicate hashes
        assets = [
            Mock(id="a1", file_hash="hash1"),
            Mock(id="a2", file_hash="hash1"),  # Duplicate of a1
            Mock(id="a3", file_hash="hash2"),
            Mock(id="a4", file_hash="hash2"),  # Duplicate of a3
            Mock(id="a5", file_hash="hash3"),  # Unique
        ]
        mock_client.query_assets.return_value = assets
        
        result = await get_duplicate_assets(mock_client)
        
        assert len(result) == 2  # hash1 and hash2 have duplicates
        assert "hash1" in result
        assert "hash2" in result
        assert len(result["hash1"]) == 2
        assert len(result["hash2"]) == 2
    
    @pytest.mark.asyncio
    async def test_no_duplicates(self, mock_client):
        """Test when no duplicates exist."""
        assets = [
            Mock(id="a1", file_hash="hash1"),
            Mock(id="a2", file_hash="hash2"),
            Mock(id="a3", file_hash="hash3"),
        ]
        mock_client.query_assets.return_value = assets
        
        result = await get_duplicate_assets(mock_client)
        
        assert len(result) == 0


__all__ = [
    'TestAssetQueryBuilder',
    'TestGetAssetsByCategory',
    'TestGetAssetsByTags',
    'TestAssetExists',
    'TestGetDuplicateAssets'
]
