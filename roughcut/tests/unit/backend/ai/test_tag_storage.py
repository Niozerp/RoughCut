# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest", "pytest-asyncio"]
# ///

#!/usr/bin/env python3
"""Unit tests for TagStorage."""

import pytest
from pathlib import Path

from roughcut.backend.ai.tag_storage import TagStorage, TaggedAsset


class TestTagStorage:
    """Test cases for TagStorage class."""
    
    @pytest.fixture
    def storage(self):
        """Create a fresh TagStorage instance for each test."""
        storage = TagStorage()
        yield storage
        storage.clear()  # Cleanup after test
    
    def test_store_tags_basic(self, storage):
        """Test storing tags for a single asset."""
        result = storage.store_tags(
            asset_id="test-001",
            file_path=Path("/Music/Corporate/Upbeat/track.wav"),
            category="music",
            tags=["corporate", "upbeat", "bright"],
            confidence=0.95
        )
        
        assert result is True
        
        # Verify stored
        tags = storage.get_asset_tags("test-001")
        assert tags == ["corporate", "upbeat", "bright"]
    
    def test_store_tags_update_existing(self, storage):
        """Test updating tags for an existing asset."""
        # Store initial tags
        storage.store_tags(
            asset_id="test-002",
            file_path=Path("/Music/Sad/track.wav"),
            category="music",
            tags=["sad", "slow"],
            confidence=0.8
        )
        
        # Update with new tags
        storage.store_tags(
            asset_id="test-002",
            file_path=Path("/Music/Sad/track.wav"),
            category="music",
            tags=["melancholy", "emotional"],
            confidence=0.9
        )
        
        # Verify new tags
        tags = storage.get_asset_tags("test-002")
        assert tags == ["melancholy", "emotional"]
        
        # Verify old tags removed from index
        results = storage.search_by_tags(["sad"])
        assert len(results) == 0
    
    def test_search_by_tags_single_tag(self, storage):
        """Test searching by a single tag."""
        # Store some assets
        storage.store_tags("a1", Path("/a.wav"), "music", ["happy", "upbeat"], 0.9)
        storage.store_tags("a2", Path("/b.wav"), "music", ["sad", "slow"], 0.8)
        storage.store_tags("a3", Path("/c.wav"), "sfx", ["happy", "bright"], 0.85)
        
        # Search
        results = storage.search_by_tags(["happy"])
        
        assert len(results) == 2
        assert all(r.asset_id in ["a1", "a3"] for r in results)
    
    def test_search_by_tags_multiple_tags(self, storage):
        """Test searching by multiple tags with relevance ranking."""
        # Store assets with different tag overlaps
        storage.store_tags("a1", Path("/a.wav"), "music", ["corporate", "upbeat"], 0.9)
        storage.store_tags("a2", Path("/b.wav"), "music", ["corporate", "upbeat", "bright"], 0.95)
        storage.store_tags("a3", Path("/c.wav"), "music", ["corporate"], 0.8)
        
        # Search with multiple tags
        results = storage.search_by_tags(["corporate", "upbeat"])
        
        assert len(results) == 3
        # a2 should be first (matches 2 tags)
        assert results[0].asset_id == "a2"
        assert results[0].tags == ["corporate", "upbeat", "bright"]
    
    def test_search_by_tags_with_category_filter(self, storage):
        """Test searching with category filter."""
        storage.store_tags("a1", Path("/a.wav"), "music", ["happy"], 0.9)
        storage.store_tags("a2", Path("/b.wav"), "sfx", ["happy"], 0.8)
        storage.store_tags("a3", Path("/c.wav"), "vfx", ["happy"], 0.85)
        
        # Search with category filter
        results = storage.search_by_tags(["happy"], category="music")
        
        assert len(results) == 1
        assert results[0].asset_id == "a1"
    
    def test_search_by_tags_empty(self, storage):
        """Test searching with empty tag list."""
        storage.store_tags("a1", Path("/a.wav"), "music", ["happy"], 0.9)
        
        results = storage.search_by_tags([])
        assert results == []
    
    def test_search_by_tags_limit(self, storage):
        """Test search result limit."""
        # Store many assets
        for i in range(10):
            storage.store_tags(
                f"a{i}",
                Path(f"/{i}.wav"),
                "music",
                ["common"],
                0.9
            )
        
        # Search with limit
        results = storage.search_by_tags(["common"], limit=5)
        
        assert len(results) == 5
    
    def test_get_all_tags(self, storage):
        """Test getting all unique tags."""
        storage.store_tags("a1", Path("/a.wav"), "music", ["happy", "upbeat"], 0.9)
        storage.store_tags("a2", Path("/b.wav"), "sfx", ["explosion", "loud"], 0.8)
        storage.store_tags("a3", Path("/c.wav"), "music", ["sad", "slow"], 0.85)
        
        all_tags = storage.get_all_tags()
        
        assert sorted(all_tags) == ["explosion", "happy", "loud", "sad", "slow", "upbeat"]
    
    def test_get_all_tags_by_category(self, storage):
        """Test getting tags filtered by category."""
        storage.store_tags("a1", Path("/a.wav"), "music", ["happy", "upbeat"], 0.9)
        storage.store_tags("a2", Path("/b.wav"), "sfx", ["explosion", "loud"], 0.8)
        storage.store_tags("a3", Path("/c.wav"), "music", ["sad", "slow"], 0.85)
        
        music_tags = storage.get_all_tags(category="music")
        
        assert sorted(music_tags) == ["happy", "sad", "slow", "upbeat"]
    
    def test_delete_asset(self, storage):
        """Test deleting an asset."""
        storage.store_tags("a1", Path("/a.wav"), "music", ["happy"], 0.9)
        
        result = storage.delete_asset("a1")
        
        assert result is True
        assert storage.get_asset_tags("a1") is None
        
        # Verify tag index updated
        results = storage.search_by_tags(["happy"])
        assert len(results) == 0
    
    def test_delete_asset_not_found(self, storage):
        """Test deleting a non-existent asset."""
        result = storage.delete_asset("nonexistent")
        
        assert result is False
    
    def test_get_asset_tags_not_found(self, storage):
        """Test getting tags for non-existent asset."""
        tags = storage.get_asset_tags("nonexistent")
        
        assert tags is None
    
    def test_store_tags_empty_list(self, storage):
        """Test storing empty tag list."""
        result = storage.store_tags(
            "a1",
            Path("/a.wav"),
            "music",
            [],
            0.0
        )
        
        assert result is True
        tags = storage.get_asset_tags("a1")
        assert tags == []
