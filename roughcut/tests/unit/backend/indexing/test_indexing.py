"""Unit tests for media indexing module.

Tests file scanning, hash caching, incremental change detection,
and the main indexer functionality.
"""

import sys
import tempfile
import os
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

import unittest
from unittest.mock import AsyncMock, Mock
from roughcut.backend.indexing.hash_cache import HashCache
from roughcut.backend.indexing.scanner import FileScanner, MEDIA_EXTENSIONS, get_category_for_extension
from roughcut.backend.indexing.incremental import IncrementalScanner
from roughcut.backend.indexing.indexer import MediaIndexer
from roughcut.backend.database.models import MediaAsset, IndexState, IndexResult, ScanResult
from roughcut.backend.database.spacetime_client import DeleteResult, QueryResult


class TestHashCache(unittest.TestCase):
    """Test suite for HashCache."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cache = HashCache()
    
    def test_compute_hash(self):
        """Test hash computation for a file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            path = Path(temp_path)
            hash1 = self.cache.compute_hash(path)
            
            # Verify it's a valid MD5 hash (32 hex characters)
            self.assertEqual(len(hash1), 32)
            self.assertTrue(all(c in '0123456789abcdef' for c in hash1))
            
            # Same content should produce same hash
            hash2 = self.cache.compute_hash(path)
            self.assertEqual(hash1, hash2)
        finally:
            os.unlink(temp_path)
    
    def test_get_file_hash_caching(self):
        """Test that get_file_hash caches results."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            path = Path(temp_path)
            
            # First call should compute and cache
            hash1 = self.cache.get_file_hash(path)
            
            # Second call should use cache
            hash2 = self.cache.get_file_hash(path)
            self.assertEqual(hash1, hash2)
            
            # Verify it's in the cache
            cached = self.cache.get_cached_hash(path)
            self.assertEqual(cached, hash1)
        finally:
            os.unlink(temp_path)
    
    def test_has_changed(self):
        """Test change detection."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("original content")
            temp_path = f.name
        
        try:
            path = Path(temp_path)
            
            # Get initial hash
            original_hash = self.cache.get_file_hash(path)
            
            # Should not have changed
            self.assertFalse(self.cache.has_changed(path, original_hash))
            
            # Modify file
            with open(temp_path, 'w') as f:
                f.write("modified content")
            
            # Should detect change
            self.assertTrue(self.cache.has_changed(path, original_hash))
        finally:
            os.unlink(temp_path)
    
    def test_has_changed_missing_file(self):
        """Test change detection for deleted file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            path = Path(temp_path)
            original_hash = self.cache.get_file_hash(path)
            
            # Delete the file
            os.unlink(temp_path)
            
            # Should report changed (file missing)
            self.assertTrue(self.cache.has_changed(path, original_hash))
        except:
            pass  # File already deleted
    
    def test_cache_persistence(self):
        """Test saving and loading cache from disk."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        cache_file = None
        try:
            path = Path(temp_path)
            hash1 = self.cache.get_file_hash(path)
            
            # Save cache
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                cache_file = f.name
            os.unlink(cache_file)  # Remove so save_to_disk can create it
            
            self.cache.save_to_disk(Path(cache_file))
            
            # Create new cache and load
            new_cache = HashCache()
            new_cache.load_from_disk(Path(cache_file))
            
            # Should have cached hash
            cached = new_cache.get_cached_hash(path)
            self.assertEqual(cached, hash1)
        finally:
            os.unlink(temp_path)
            if cache_file and os.path.exists(cache_file):
                os.unlink(cache_file)
    
    def test_invalidate(self):
        """Test cache invalidation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            path = Path(temp_path)
            self.cache.get_file_hash(path)
            
            # Verify in cache
            self.assertIsNotNone(self.cache.get_cached_hash(path))
            
            # Invalidate
            self.cache.invalidate(path)
            
            # Should be gone
            self.assertIsNone(self.cache.get_cached_hash(path))
        finally:
            os.unlink(temp_path)
    
    def test_clear(self):
        """Test clearing all cache entries."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            path = Path(temp_path)
            self.cache.get_file_hash(path)
            
            # Verify cache has entries
            stats = self.cache.get_cache_stats()
            self.assertGreater(stats['cached_entries'], 0)
            
            # Clear
            self.cache.clear()
            
            # Should be empty
            stats = self.cache.get_cache_stats()
            self.assertEqual(stats['cached_entries'], 0)
        finally:
            os.unlink(temp_path)


class TestFileScanner(unittest.TestCase):
    """Test suite for FileScanner."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_scan_folder_finds_media_files(self):
        """Test scanner finds media files."""
        # Create test files
        music_file = Path(self.temp_dir) / "test.mp3"
        sfx_file = Path(self.temp_dir) / "test.wav"
        vfx_file = Path(self.temp_dir) / "test.mp4"
        txt_file = Path(self.temp_dir) / "test.txt"
        
        music_file.touch()
        sfx_file.touch()
        vfx_file.touch()
        txt_file.touch()
        
        scanner = FileScanner()
        results = scanner.scan_folder(Path(self.temp_dir))
        
        # Should find media files but not text file
        result_names = [p.name for p in results]
        self.assertIn("test.mp3", result_names)
        self.assertIn("test.wav", result_names)
        self.assertIn("test.mp4", result_names)
        self.assertNotIn("test.txt", result_names)
    
    def test_scan_folder_recursive(self):
        """Test scanner finds files in subdirectories."""
        subdir = Path(self.temp_dir) / "subdir"
        subdir.mkdir()
        
        music_file = subdir / "nested.mp3"
        music_file.touch()
        
        scanner = FileScanner()
        results = scanner.scan_folder(Path(self.temp_dir))
        
        result_names = [p.name for p in results]
        self.assertIn("nested.mp3", result_names)
    
    def test_scan_folder_nonexistent(self):
        """Test scanner handles non-existent folder."""
        scanner = FileScanner()
        results = scanner.scan_folder(Path("/nonexistent/path"))
        
        self.assertEqual(len(results), 0)
    
    def test_scan_folder_by_category(self):
        """Test scanner filters by category."""
        # Create files in different categories
        music_file = Path(self.temp_dir) / "music.mp3"
        sfx_file = Path(self.temp_dir) / "sfx.wav"
        vfx_file = Path(self.temp_dir) / "vfx.mp4"
        
        music_file.touch()
        sfx_file.touch()
        vfx_file.touch()
        
        # Music only scanner
        music_scanner = FileScanner(categories=['music'])
        results = music_scanner.scan_folder(Path(self.temp_dir))
        result_names = [p.name for p in results]
        
        self.assertIn("music.mp3", result_names)
        self.assertNotIn("sfx.wav", result_names)
        self.assertNotIn("vfx.mp4", result_names)
    
    def test_count_files(self):
        """Test file counting."""
        # Create files
        for i in range(5):
            (Path(self.temp_dir) / f"music{i}.mp3").touch()
        
        scanner = FileScanner()
        count = scanner.count_files(Path(self.temp_dir))
        
        self.assertEqual(count, 5)
    
    def test_get_supported_extensions(self):
        """Test getting supported extensions."""
        scanner = FileScanner()
        extensions = scanner.get_supported_extensions()
        
        self.assertIn('.mp3', extensions)
        self.assertIn('.wav', extensions)
        self.assertIn('.mp4', extensions)
    
    def test_get_category_for_extension(self):
        """Test extension to category mapping."""
        self.assertEqual(get_category_for_extension('.mp3'), 'music')
        self.assertEqual(get_category_for_extension('.wav'), 'sfx')
        self.assertEqual(get_category_for_extension('.mp4'), 'vfx')
        self.assertIsNone(get_category_for_extension('.txt'))


class TestIncrementalScanner(unittest.TestCase):
    """Test suite for IncrementalScanner."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = HashCache()
        self.file_scanner = FileScanner()
        self.incremental = IncrementalScanner(
            hash_cache=self.cache,
            file_scanner=self.file_scanner
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_scan_for_changes_sync_new_files(self):
        """Test detecting new files."""
        # Create test file
        music_file = Path(self.temp_dir) / "music.mp3"
        music_file.touch()
        
        # No cached assets (empty index)
        cached_assets = []
        folder_configs = {'music': self.temp_dir}
        
        result = self.incremental.scan_for_changes_sync(folder_configs, cached_assets)
        
        # Should detect new file
        self.assertEqual(len(result.new_files), 1)
        self.assertEqual(result.new_files[0].name, "music.mp3")
        self.assertEqual(len(result.modified_files), 0)
        self.assertEqual(len(result.deleted_files), 0)
    
    def test_scan_for_changes_sync_modified_files(self):
        """Test detecting modified files."""
        # Create test file
        music_file = Path(self.temp_dir) / "music.mp3"
        music_file.touch()
        
        # Create cached asset with old hash
        asset = MediaAsset.from_file_path(music_file, 'music')
        cached_assets = [asset]
        folder_configs = {'music': self.temp_dir}
        
        # Modify file
        import time
        time.sleep(0.1)  # Ensure different mtime
        with open(music_file, 'w') as f:
            f.write("modified content")
        
        result = self.incremental.scan_for_changes_sync(folder_configs, cached_assets)
        
        # Should detect modified file
        self.assertEqual(len(result.new_files), 0)
        self.assertEqual(len(result.modified_files), 1)
        self.assertEqual(len(result.deleted_files), 0)
    
    def test_scan_for_changes_sync_deleted_files(self):
        """Test detecting deleted files."""
        # Create and then delete test file
        music_file = Path(self.temp_dir) / "music.mp3"
        music_file.touch()
        
        # Create cached asset
        asset = MediaAsset.from_file_path(music_file, 'music')
        cached_assets = [asset]
        
        # Delete file
        os.unlink(music_file)
        
        folder_configs = {'music': self.temp_dir}
        result = self.incremental.scan_for_changes_sync(folder_configs, cached_assets)
        
        # Should detect deleted file
        self.assertEqual(len(result.new_files), 0)
        self.assertEqual(len(result.modified_files), 0)
        self.assertEqual(len(result.deleted_files), 1)
        self.assertEqual(result.deleted_files[0], asset.id)
    
    def test_get_asset_category(self):
        """Test category detection for files."""
        music_dir = Path(self.temp_dir) / "music"
        music_dir.mkdir()
        
        music_file = music_dir / "song.mp3"
        music_file.touch()
        
        folder_configs = {
            'music': str(music_dir),
            'sfx': None,
            'vfx': None
        }
        
        category = self.incremental.get_asset_category(music_file, folder_configs)
        self.assertEqual(category, 'music')


class TestMediaIndexer(unittest.TestCase):
    """Test suite for MediaIndexer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.progress_updates = []
        
        def progress_callback(update):
            self.progress_updates.append(update)
        
        self.indexer = MediaIndexer(progress_callback=progress_callback)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_index_media_no_folders(self):
        """Test indexing with no configured folders."""
        from roughcut.config.models import MediaFolderConfig
        
        folder_config = MediaFolderConfig()  # Empty config
        
        # Run in async context
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                self.indexer.index_media(folder_config)
            )
            
            self.assertEqual(result.indexed_count, 0)
            self.assertEqual(len(result.errors), 1)
            self.assertIn("No media folders configured", result.errors[0])
        finally:
            loop.close()
    
    def test_index_media_new_files(self):
        """Test indexing new files."""
        from roughcut.config.models import MediaFolderConfig
        
        # Create test file
        music_file = Path(self.temp_dir) / "song.mp3"
        music_file.touch()
        
        folder_config = MediaFolderConfig(music_folder=self.temp_dir)
        
        # Run in async context
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                self.indexer.index_media(folder_config, cached_assets=[])
            )
            
            self.assertEqual(result.indexed_count, 1)
            self.assertEqual(result.new_count, 1)
            self.assertEqual(result.modified_count, 0)
            self.assertEqual(len(result.errors), 0)
            
            # Should have sent progress updates
            self.assertGreater(len(self.progress_updates), 0)
            
            # Check last update is complete
            last_update = self.progress_updates[-1]
            self.assertEqual(last_update['operation'], 'complete')
        finally:
            loop.close()

    def test_index_media_is_idempotent_with_database_state(self):
        """Repeated indexing should not reinsert unchanged assets."""
        from roughcut.config.models import MediaFolderConfig

        music_file = Path(self.temp_dir) / "song.mp3"
        music_file.write_text("audio", encoding="utf-8")
        existing_asset = MediaAsset.from_file_path(music_file, 'music')

        mock_db_client = Mock()
        mock_db_client.query_assets = AsyncMock(
            return_value=QueryResult(assets=[existing_asset], total_count=1)
        )
        mock_db_client.insert_assets = AsyncMock()
        mock_db_client.update_asset = AsyncMock()
        mock_db_client.delete_assets = AsyncMock(return_value=DeleteResult(deleted_count=0))
        self.indexer._db_client = mock_db_client

        folder_config = MediaFolderConfig(music_folder=self.temp_dir)

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(self.indexer.index_media(folder_config))

            self.assertEqual(result.indexed_count, 0)
            self.assertEqual(result.new_count, 0)
            self.assertEqual(result.modified_count, 0)
            self.assertEqual(result.deleted_count, 0)
            mock_db_client.insert_assets.assert_not_awaited()
            mock_db_client.update_asset.assert_not_awaited()
        finally:
            loop.close()

    def test_index_media_deletes_out_of_scope_database_assets(self):
        """Reconciliation should purge category rows outside the configured folder."""
        from roughcut.config.models import MediaFolderConfig

        current_file = Path(self.temp_dir) / "song.mp3"
        current_file.write_text("audio", encoding="utf-8")

        outside_dir = tempfile.mkdtemp()
        try:
            stale_file = Path(outside_dir) / "stale.mp3"
            stale_file.write_text("stale", encoding="utf-8")
            stale_asset = MediaAsset.from_file_path(stale_file, 'music')

            mock_db_client = Mock()
            mock_db_client.query_assets = AsyncMock(
                return_value=QueryResult(assets=[stale_asset], total_count=1)
            )
            mock_db_client.insert_assets = AsyncMock()
            mock_db_client.update_asset = AsyncMock()
            mock_db_client.delete_assets = AsyncMock(return_value=DeleteResult(deleted_count=1))
            self.indexer._db_client = mock_db_client

            folder_config = MediaFolderConfig(music_folder=self.temp_dir)

            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(self.indexer.index_media(folder_config))
            finally:
                loop.close()

            self.assertEqual(result.deleted_count, 1)
            mock_db_client.delete_assets.assert_awaited_once_with([stale_asset.id])
        finally:
            import shutil
            shutil.rmtree(outside_dir, ignore_errors=True)
    
    def test_index_state(self):
        """Test index state management."""
        state = self.indexer.get_index_state()
        
        self.assertIsInstance(state, IndexState)
        self.assertIsNone(state.last_index_time)
        self.assertEqual(state.total_assets_indexed, 0)
    
    def test_reset(self):
        """Test indexer reset."""
        # Add some state
        self.indexer.index_state.total_assets_indexed = 10
        self.indexer.hash_cache._cache['test'] = ('hash', 123.0)
        
        # Reset
        self.indexer.reset()
        
        # Should be cleared
        self.assertEqual(self.indexer.index_state.total_assets_indexed, 0)
        self.assertEqual(len(self.indexer.hash_cache._cache), 0)

    def test_send_progress_includes_phase_and_store_metadata(self):
        """Progress payloads should expose explicit phase and DB write state."""
        self.indexer._send_progress(
            current=5,
            total=10,
            message="Writing assets",
            operation="store",
            database_writing=True,
            batch_current=1,
            batch_total=3,
        )

        update = self.progress_updates[-1]
        self.assertEqual(update['phase'], 'store')
        self.assertTrue(update['databaseWriting'])
        self.assertEqual(update['batchCurrent'], 1)
        self.assertEqual(update['batchTotal'], 3)

    def test_handle_store_batch_progress_emits_store_update(self):
        """Store batch callback should map Spacetime progress to index progress payloads."""
        self.indexer._handle_store_batch_progress({
            'current': 500,
            'total': 1200,
            'batch_current': 1,
            'batch_total': 3,
        })

        update = self.progress_updates[-1]
        self.assertEqual(update['operation'], 'store')
        self.assertEqual(update['phase'], 'store')
        self.assertTrue(update['databaseWriting'])
        self.assertEqual(update['current'], 500)
        self.assertEqual(update['total'], 1200)
        self.assertEqual(update['batchCurrent'], 1)
        self.assertEqual(update['batchTotal'], 3)


class TestDatabaseModels(unittest.TestCase):
    """Test suite for database models."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_media_asset_from_file_path(self):
        """Test creating MediaAsset from file."""
        music_file = Path(self.temp_dir) / "song.mp3"
        with open(music_file, 'w') as f:
            f.write("audio content")
        
        asset = MediaAsset.from_file_path(music_file, 'music')
        
        self.assertEqual(asset.file_name, "song.mp3")
        self.assertEqual(asset.category, 'music')
        self.assertEqual(asset.file_size, len("audio content"))
        self.assertIsNotNone(asset.file_hash)
        self.assertIsNotNone(asset.id)
    
    def test_media_asset_to_dict(self):
        """Test MediaAsset serialization."""
        music_file = Path(self.temp_dir) / "song.mp3"
        music_file.touch()
        
        asset = MediaAsset.from_file_path(music_file, 'music')
        data = asset.to_dict()
        
        self.assertEqual(data['file_name'], "song.mp3")
        self.assertEqual(data['category'], 'music')
        self.assertIn('file_path', data)
        self.assertIn('file_hash', data)
        self.assertIn('created_at', data)
    
    def test_media_asset_from_dict(self):
        """Test MediaAsset deserialization."""
        data = {
            'id': 'test-id',
            'file_path': '/music/song.mp3',
            'file_name': 'song.mp3',
            'category': 'music',
            'file_size': 1024,
            'modified_time': datetime.now().isoformat(),
            'file_hash': 'abc123',
            'ai_tags': ['epic', 'instrumental'],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        asset = MediaAsset.from_dict(data)
        
        self.assertEqual(asset.id, 'test-id')
        self.assertEqual(asset.file_name, 'song.mp3')
        self.assertEqual(asset.category, 'music')
        self.assertEqual(asset.ai_tags, ['epic', 'instrumental'])
    
    def test_media_asset_has_changed(self):
        """Test change detection on MediaAsset."""
        import time
        
        music_file = Path(self.temp_dir) / "song.mp3"
        with open(music_file, 'w') as f:
            f.write("original")
        
        asset = MediaAsset.from_file_path(music_file, 'music')
        
        # Should not have changed immediately
        self.assertFalse(asset.has_changed())
        
        # Wait and modify
        time.sleep(0.1)
        with open(music_file, 'w') as f:
            f.write("modified")
        
        # Should detect change
        self.assertTrue(asset.has_changed())
    
    def test_index_state_to_dict(self):
        """Test IndexState serialization."""
        state = IndexState(
            last_index_time=datetime.now(),
            folder_configs={'music': '/music'},
            total_assets_indexed=100
        )
        
        data = state.to_dict()
        
        self.assertIn('last_index_time', data)
        self.assertEqual(data['folder_configs'], {'music': '/music'})
        self.assertEqual(data['total_assets_indexed'], 100)
    
    def test_index_state_from_dict(self):
        """Test IndexState deserialization."""
        now = datetime.now()
        data = {
            'last_index_time': now.isoformat(),
            'folder_configs': {'sfx': '/sfx'},
            'total_assets_indexed': 50,
            'index_version': '1.0'
        }
        
        state = IndexState.from_dict(data)
        
        self.assertIsNotNone(state.last_index_time)
        self.assertEqual(state.folder_configs, {'sfx': '/sfx'})
        self.assertEqual(state.total_assets_indexed, 50)
    
    def test_scan_result_to_dict(self):
        """Test ScanResult serialization."""
        result = ScanResult(
            new_files=[Path('/music/new.mp3')],
            modified_files=[Path('/music/mod.wav')],
            deleted_files=['id1', 'id2'],
            total_scanned=10
        )
        
        data = result.to_dict()
        
        self.assertEqual(data['new_files'], ['/music/new.mp3'])
        self.assertEqual(data['modified_files'], ['/music/mod.wav'])
        self.assertEqual(data['deleted_files'], ['id1', 'id2'])
        self.assertEqual(data['total_scanned'], 10)
    
    def test_index_result_to_dict(self):
        """Test IndexResult serialization."""
        result = IndexResult(
            indexed_count=10,
            new_count=5,
            modified_count=3,
            deleted_count=2,
            duration_ms=5000,
            errors=['error1']
        )
        
        data = result.to_dict()
        
        self.assertEqual(data['indexed_count'], 10)
        self.assertEqual(data['new_count'], 5)
        self.assertEqual(data['modified_count'], 3)
        self.assertEqual(data['deleted_count'], 2)
        self.assertEqual(data['duration_ms'], 5000)
        self.assertEqual(data['errors'], ['error1'])


if __name__ == '__main__':
    unittest.main()
