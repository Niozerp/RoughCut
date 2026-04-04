"""Unit tests for asset counting service.

Tests the AssetCounter class and related functionality for counting
media assets by category with caching support.
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from roughcut.backend.indexing.counter import AssetCounter, AssetCounts, CategoryCount
from roughcut.backend.database.models import MediaAsset


class TestAssetCounter:
    """Test suite for AssetCounter class."""
    
    def test_count_by_category_empty(self):
        """Test counting with no assets returns zeros."""
        counter = AssetCounter()
        result = counter.count_by_category({}, use_cache=False)
        
        assert result.music == 0
        assert result.sfx == 0
        assert result.vfx == 0
        assert result.total == 0
        assert isinstance(result.last_updated, datetime)
        assert result.last_updated.tzinfo is not None  # Timezone-aware
    
    def test_count_by_category_music_only(self):
        """Test counting with only music assets."""
        counter = AssetCounter()
        assets = {
            '1': self._create_asset('1', 'music'),
            '2': self._create_asset('2', 'music'),
            '3': self._create_asset('3', 'music'),
        }
        
        result = counter.count_by_category(assets, use_cache=False)
        
        assert result.music == 3
        assert result.sfx == 0
        assert result.vfx == 0
        assert result.total == 3
    
    def test_count_by_category_sfx_only(self):
        """Test counting with only SFX assets."""
        counter = AssetCounter()
        assets = {
            '1': self._create_asset('1', 'sfx'),
            '2': self._create_asset('2', 'sfx'),
        }
        
        result = counter.count_by_category(assets, use_cache=False)
        
        assert result.music == 0
        assert result.sfx == 2
        assert result.vfx == 0
        assert result.total == 2
    
    def test_count_by_category_vfx_only(self):
        """Test counting with only VFX assets."""
        counter = AssetCounter()
        assets = {
            '1': self._create_asset('1', 'vfx'),
            '2': self._create_asset('2', 'vfx'),
            '3': self._create_asset('3', 'vfx'),
            '4': self._create_asset('4', 'vfx'),
        }
        
        result = counter.count_by_category(assets, use_cache=False)
        
        assert result.music == 0
        assert result.sfx == 0
        assert result.vfx == 4
        assert result.total == 4
    
    def test_count_by_category_mixed(self):
        """Test counting with mixed categories."""
        counter = AssetCounter()
        assets = {
            '1': self._create_asset('1', 'music'),
            '2': self._create_asset('2', 'music'),
            '3': self._create_asset('3', 'sfx'),
            '4': self._create_asset('4', 'vfx'),
            '5': self._create_asset('5', 'music'),
            '6': self._create_asset('6', 'sfx'),
        }
        
        result = counter.count_by_category(assets, use_cache=False)
        
        assert result.music == 3
        assert result.sfx == 2
        assert result.vfx == 1
        assert result.total == 6
    
    def test_count_ignores_invalid_categories(self):
        """Test that assets with invalid categories are ignored."""
        counter = AssetCounter()
        assets = {
            '1': self._create_asset('1', 'music'),
            '2': self._create_asset('2', 'invalid_category'),
            '3': self._create_asset('3', 'sfx'),
            '4': self._create_asset('4', 'another_invalid'),
        }
        
        result = counter.count_by_category(assets, use_cache=False)
        
        assert result.music == 1
        assert result.sfx == 1
        assert result.vfx == 0
        assert result.total == 2
    
    def test_count_ignores_none_category(self):
        """Test that assets with None category are skipped."""
        counter = AssetCounter()
        assets = {
            '1': self._create_asset('1', 'music'),
            '2': self._create_asset_with_none_category('2'),
        }
        
        result = counter.count_by_category(assets, use_cache=False)
        
        assert result.music == 1
        assert result.total == 1
    
    def test_count_case_insensitive_categories(self):
        """Test that categories are matched case-insensitively."""
        counter = AssetCounter()
        assets = {
            '1': self._create_asset('1', 'MUSIC'),  # Uppercase
            '2': self._create_asset('2', 'Music'),  # Mixed case
            '3': self._create_asset('3', 'SFX'),    # Uppercase
            '4': self._create_asset('4', 'VFX'),    # Uppercase
        }
        
        result = counter.count_by_category(assets, use_cache=False)
        
        assert result.music == 2
        assert result.sfx == 1
        assert result.vfx == 1
        assert result.total == 4
    
    def test_cache_populated_on_first_call(self):
        """Test that cache is populated after first count."""
        counter = AssetCounter()
        assets = {'1': self._create_asset('1', 'music')}
        
        assert counter.get_cached_counts() is None
        
        result = counter.count_by_category(assets, use_cache=True)
        
        cached = counter.get_cached_counts()
        assert cached is not None
        assert cached.music == 1
    
    def test_cache_used_on_subsequent_calls(self):
        """Test that cached result is used on subsequent calls."""
        counter = AssetCounter()
        assets = {'1': self._create_asset('1', 'music')}
        
        # First call populates cache
        result1 = counter.count_by_category(assets, use_cache=True)
        
        # Second call should use cache
        result2 = counter.count_by_category(assets, use_cache=True)
        
        assert result2.last_updated == result1.last_updated
    
    def test_cache_bypassed_when_use_cache_false(self):
        """Test that cache is bypassed when use_cache=False."""
        counter = AssetCounter()
        assets = {'1': self._create_asset('1', 'music')}
        
        # First call populates cache
        result1 = counter.count_by_category(assets, use_cache=True)
        
        # Second call with use_cache=False should recalculate
        result2 = counter.count_by_category(assets, use_cache=False)
        
        assert result2.last_updated > result1.last_updated
    
    def test_cache_invalidated_after_ttl(self):
        """Test that cache expires after TTL."""
        counter = AssetCounter()
        assets = {'1': self._create_asset('1', 'music')}
        
        # Set very short TTL for testing
        counter._cache_ttl_seconds = 0.01
        
        # First call populates cache
        result1 = counter.count_by_category(assets, use_cache=True)
        
        # Wait for cache to expire
        import time
        time.sleep(0.02)
        
        # Second call should recalculate
        result2 = counter.count_by_category(assets, use_cache=True)
        
        assert result2.last_updated > result1.last_updated
    
    def test_invalidate_cache_clears_cache(self):
        """Test that invalidate_cache clears the cache."""
        counter = AssetCounter()
        assets = {'1': self._create_asset('1', 'music')}
        
        # Populate cache
        counter.count_by_category(assets, use_cache=True)
        assert counter.get_cached_counts() is not None
        
        # Invalidate cache
        counter.invalidate_cache()
        
        assert counter.get_cached_counts() is None
    
    def test_negative_cache_ttl_raises_error(self):
        """Test that negative TTL raises ValueError."""
        with pytest.raises(ValueError, match="cache_ttl_seconds must be non-negative"):
            AssetCounter(cache_ttl_seconds=-1.0)
    
    def test_zero_cache_ttl_uses_minimum(self):
        """Test that zero TTL uses minimum value."""
        counter = AssetCounter(cache_ttl_seconds=0)
        assert counter.get_cache_ttl() >= 0.001
    
    def test_large_asset_counts(self):
        """Test counting with large number of assets (AC #3 scenario)."""
        counter = AssetCounter()
        
        # Create 12,437 music assets
        assets = {}
        for i in range(12437):
            assets[f'music_{i}'] = self._create_asset(f'music_{i}', 'music')
        
        # Create 8,291 sfx assets
        for i in range(8291):
            assets[f'sfx_{i}'] = self._create_asset(f'sfx_{i}', 'sfx')
        
        # Create 3,102 vfx assets
        for i in range(3102):
            assets[f'vfx_{i}'] = self._create_asset(f'vfx_{i}', 'vfx')
        
        result = counter.count_by_category(assets, use_cache=False)
        
        assert result.music == 12437
        assert result.sfx == 8291
        assert result.vfx == 3102
        assert result.total == 23830
    
    def test_asset_counts_to_dict(self):
        """Test AssetCounts.to_dict() produces correct format."""
        counts = AssetCounts(
            music=12437,
            sfx=8291,
            vfx=3102,
            total=23830,
            last_updated=datetime(2026, 4, 3, 12, 34, 56, tzinfo=timezone.utc)
        )
        
        result = counts.to_dict()
        
        assert result['music'] == 12437
        assert result['sfx'] == 8291
        assert result['vfx'] == 3102
        assert result['total'] == 23830
        assert result['formatted']['music'] == '12,437'
        assert result['formatted']['sfx'] == '8,291'
        assert result['formatted']['vfx'] == '3,102'
        assert result['formatted']['total'] == '23,830'
        assert '2026-04-03T12:34:56' in result['last_updated']
    
    def test_valid_categories_constant(self):
        """Test that VALID_CATEGORIES contains expected values."""
        counter = AssetCounter()
        
        assert 'music' in counter.VALID_CATEGORIES
        assert 'sfx' in counter.VALID_CATEGORIES
        assert 'vfx' in counter.VALID_CATEGORIES
        assert len(counter.VALID_CATEGORIES) == 3
    
    def test_cache_ttl_default(self):
        """Test default cache TTL is 5 seconds."""
        counter = AssetCounter()
        
        assert counter.get_cache_ttl() == 5.0
    
    def test_get_category_count(self):
        """Test AssetCounts.get_category_count helper."""
        counts = AssetCounts(
            music=10,
            sfx=5,
            vfx=3,
            total=18,
            last_updated=datetime.now(timezone.utc)
        )
        
        assert counts.get_category_count('music') == 10
        assert counts.get_category_count('sfx') == 5
        assert counts.get_category_count('vfx') == 3
        assert counts.get_category_count('invalid') == 0
    
    def _create_asset(self, asset_id: str, category: str) -> MediaAsset:
        """Helper to create a MediaAsset for testing."""
        return MediaAsset(
            id=asset_id,
            file_path=Path(f"/test/{category}/file_{asset_id}.wav"),
            file_name=f"file_{asset_id}.wav",
            category=category,
            file_size=1000,
            modified_time=datetime.now(),
            file_hash="abc123"
        )
    
    def _create_asset_with_none_category(self, asset_id: str) -> MediaAsset:
        """Helper to create a MediaAsset with None category."""
        asset = MediaAsset(
            id=asset_id,
            file_path=Path(f"/test/none/file_{asset_id}.wav"),
            file_name=f"file_{asset_id}.wav",
            category=None,  # type: ignore
            file_size=1000,
            modified_time=datetime.now(),
            file_hash="abc123"
        )
        return asset


class TestAssetCounterPerformance:
    """Performance tests for AssetCounter."""
    
    def test_counting_performance_large_dataset(self):
        """Test that counting 20,000 assets completes in reasonable time."""
        import time
        
        counter = AssetCounter()
        assets = {}
        
        # Create 20,000 assets
        for i in range(20000):
            category = ['music', 'sfx', 'vfx'][i % 3]
            assets[f'asset_{i}'] = MediaAsset(
                id=f'asset_{i}',
                file_path=Path(f"/test/{category}/file_{i}.wav"),
                file_name=f"file_{i}.wav",
                category=category,
                file_size=1000,
                modified_time=datetime.now(),
                file_hash="abc123"
            )
        
        start_time = time.time()
        result = counter.count_by_category(assets, use_cache=False)
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Should complete in under 100ms (per NFR consideration)
        assert elapsed_ms < 100, f"Counting took {elapsed_ms}ms, expected <100ms"
        assert result.total == 20000


class TestAssetCounterThreadSafety:
    """Thread safety tests for AssetCounter."""
    
    def test_thread_safe_cache_operations(self):
        """Test that cache operations are thread-safe."""
        import threading
        import time
        
        counter = AssetCounter()
        assets = {'1': MediaAsset(
            id='1',
            file_path=Path('/test/music/file1.wav'),
            file_name='file1.wav',
            category='music',
            file_size=1000,
            modified_time=datetime.now(),
            file_hash='abc123'
        )}
        
        results = []
        errors = []
        
        def count_and_cache():
            try:
                result = counter.count_by_category(assets, use_cache=True)
                results.append(result)
                time.sleep(0.01)  # Small delay to increase contention
                counter.invalidate_cache()
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads concurrently
        threads = [threading.Thread(target=count_and_cache) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should complete without errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 10
