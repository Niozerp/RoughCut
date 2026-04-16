"""Integration tests for re-indexing workflow.

Tests the complete re-indexing flow from full scan through
database updates with real file system and database operations.
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

from roughcut.backend.indexing.change_detector import ChangeDetector, FileMetadata
from roughcut.backend.indexing.indexer import MediaIndexer
from roughcut.backend.database.models import MediaAsset
from roughcut.config.models import MediaFolderConfig


@pytest.fixture
def temp_media_folder():
    """Create a temporary folder with media files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some dummy media files
        music_dir = Path(tmpdir) / "Music"
        music_dir.mkdir()
        
        # Create dummy music files
        (music_dir / "track1.mp3").write_text("dummy music content 1")
        (music_dir / "track2.mp3").write_text("dummy music content 2")
        (music_dir / "track3.wav").write_text("dummy music content 3")
        
        sfx_dir = Path(tmpdir) / "SFX"
        sfx_dir.mkdir()
        
        # Create dummy sfx files
        (sfx_dir / "whoosh.wav").write_text("dummy sfx content 1")
        (sfx_dir / "bang.wav").write_text("dummy sfx content 2")
        
        yield tmpdir


@pytest.fixture
def indexer():
    """Create a MediaIndexer instance."""
    return MediaIndexer()


@pytest.fixture
def folder_config(temp_media_folder):
    """Create a MediaFolderConfig for testing."""
    config = MediaFolderConfig()
    config.music_folder = str(Path(temp_media_folder) / "Music")
    config.sfx_folder = str(Path(temp_media_folder) / "SFX")
    config.vfx_folder = None
    return config


class TestChangeDetectorIntegration:
    """Integration tests for change detection with real files."""
    
    def test_full_scan_finds_all_files(self, temp_media_folder, indexer):
        """Test that full scan finds all files in configured folders."""
        config = MediaFolderConfig()
        config.music_folder = str(Path(temp_media_folder) / "Music")
        config.sfx_folder = str(Path(temp_media_folder) / "SFX")
        config.vfx_folder = None
        
        # Run full scan
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        scanned = loop.run_until_complete(
            indexer._scan_folder_full(config.music_folder, "music")
        )
        
        # Should find 3 music files
        assert len(scanned) == 3
        
        scanned = loop.run_until_complete(
            indexer._scan_folder_full(config.sfx_folder, "sfx")
        )
        
        # Should find 2 sfx files
        assert len(scanned) == 2
    
    def test_detect_changes_with_real_files(self, temp_media_folder):
        """Test change detection with actual file system changes."""
        detector = ChangeDetector()
        
        # Initial scan
        music_dir = Path(temp_media_folder) / "Music"
        scanned = {}
        
        for file_path in music_dir.glob("*.mp3"):
            if file_path.is_file():
                import hashlib
                content = file_path.read_bytes()
                file_hash = hashlib.sha256(content).hexdigest()
                stat = file_path.stat()
                
                scanned[file_path] = FileMetadata(
                    file_hash=file_hash,
                    modified_time=datetime.fromtimestamp(stat.st_mtime),
                    file_size=stat.st_size,
                    category="music"
                )
        
        # Simulate empty database
        db_assets = []
        
        changes = detector.detect_changes(scanned, db_assets)
        
        # All 2 MP3 files should be new
        assert len(changes.new_files) == 2
        assert len(changes.deleted_files) == 0
    
    def test_detect_modified_file(self, temp_media_folder):
        """Test detecting a modified file."""
        detector = ChangeDetector()
        
        music_dir = Path(temp_media_folder) / "Music"
        track1_path = music_dir / "track1.mp3"
        
        # Get original hash
        import hashlib
        content = track1_path.read_bytes()
        original_hash = hashlib.sha256(content).hexdigest()
        stat = track1_path.stat()
        
        # Simulate database record
        db_assets = [
            MediaAsset(
                id="asset-1",
                file_path=str(track1_path),
                file_name="track1.mp3",
                file_hash=original_hash,
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                category="music"
            )
        ]
        
        # Modify the file
        track1_path.write_text("modified content - this is different")
        
        # Scan again
        new_content = track1_path.read_bytes()
        new_hash = hashlib.sha256(new_content).hexdigest()
        new_stat = track1_path.stat()
        
        scanned = {
            track1_path: FileMetadata(
                file_hash=new_hash,
                modified_time=datetime.fromtimestamp(new_stat.st_mtime),
                file_size=new_stat.st_size,
                category="music"
            )
        }
        
        changes = detector.detect_changes(scanned, db_assets)
        
        # Should detect modification
        assert len(changes.modified_files) == 1
        assert changes.modified_files[0] == track1_path
    
    def test_detect_moved_file(self, temp_media_folder):
        """Test detecting a moved file by hash matching."""
        detector = ChangeDetector()
        
        music_dir = Path(temp_media_folder) / "Music"
        track1_path = music_dir / "track1.mp3"
        
        # Get file hash
        import hashlib
        content = track1_path.read_bytes()
        file_hash = hashlib.sha256(content).hexdigest()
        stat = track1_path.stat()
        
        # Simulate old location in database
        old_path = str(music_dir / "old_name.mp3")
        db_assets = [
            MediaAsset(
                id="asset-1",
                file_path=old_path,
                file_name="old_name.mp3",
                file_hash=file_hash,  # Same hash!
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                category="music"
            )
        ]
        
        # Scan at new location
        scanned = {
            track1_path: FileMetadata(
                file_hash=file_hash,
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                file_size=stat.st_size,
                category="music"
            )
        }
        
        changes = detector.detect_changes(scanned, db_assets)
        
        # Should detect as moved
        assert len(changes.moved_files) == 1
        old, new = changes.moved_files[0]
        assert str(old) == old_path
        assert new == track1_path
    
    def test_detect_deleted_file(self, temp_media_folder):
        """Test detecting a deleted/orphaned file."""
        detector = ChangeDetector()
        
        music_dir = Path(temp_media_folder) / "Music"
        
        # Delete one file
        (music_dir / "track1.mp3").unlink()
        
        # Scan (now missing track1.mp3)
        scanned = {}
        for file_path in music_dir.glob("*.mp3"):
            if file_path.is_file():
                import hashlib
                content = file_path.read_bytes()
                file_hash = hashlib.sha256(content).hexdigest()
                stat = file_path.stat()
                
                scanned[file_path] = FileMetadata(
                    file_hash=file_hash,
                    modified_time=datetime.fromtimestamp(stat.st_mtime),
                    file_size=stat.st_size,
                    category="music"
                )
        
        # Simulate database with deleted file still present
        db_assets = [
            MediaAsset(
                id="asset-1",
                file_path=str(music_dir / "track1.mp3"),
                file_name="track1.mp3",
                file_hash="somehash",
                category="music"
            ),
            MediaAsset(
                id="asset-2",
                file_path=str(music_dir / "track2.mp3"),
                file_name="track2.mp3",
                file_hash="somehash2",
                category="music"
            ),
        ]
        
        changes = detector.detect_changes(scanned, db_assets)
        
        # Should detect one deleted file
        assert len(changes.deleted_files) == 1
        assert "asset-1" in changes.deleted_files


class TestReindexingWorkflowIntegration:
    """Integration tests for the full reindexing workflow."""
    
    def test_reindex_folders_finds_all_files(self, temp_media_folder, indexer, folder_config):
        """Test that reindex_folders finds all files in configured folders."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            indexer.reindex_folders(folder_configs=folder_config)
        )
        
        # Should find 3 music + 2 sfx = 5 new files
        assert result.new_count == 5
        assert result.modified_count == 0
        assert result.moved_count == 0
        assert result.deleted_count == 0
        assert result.total_scanned >= 5
    
    def test_reindex_folders_detects_modifications(self, temp_media_folder, indexer, folder_config):
        """Test reindexing detects modified files."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # First, index all files
        result = loop.run_until_complete(
            indexer.reindex_folders(folder_configs=folder_config)
        )
        
        assert result.new_count == 5
        
        # Modify a file
        music_dir = Path(temp_media_folder) / "Music"
        (music_dir / "track1.mp3").write_text("modified content")
        
        # Re-index
        result = loop.run_until_complete(
            indexer.reindex_folders(folder_configs=folder_config)
        )
        
        # Should detect one modification
        assert result.modified_count == 1
        assert result.new_count == 0
    
    def test_reindex_folders_detects_deletions(self, temp_media_folder, indexer, folder_config):
        """Test reindexing detects deleted files."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # First, index all files
        result = loop.run_until_complete(
            indexer.reindex_folders(folder_configs=folder_config)
        )
        
        assert result.new_count == 5
        
        # Delete a file
        music_dir = Path(temp_media_folder) / "Music"
        (music_dir / "track1.mp3").unlink()
        
        # Re-index
        result = loop.run_until_complete(
            indexer.reindex_folders(folder_configs=folder_config)
        )
        
        # Should detect one deletion
        assert result.deleted_count == 1
        assert result.new_count == 0
    
    def test_reindex_folders_detects_new_files(self, temp_media_folder, indexer, folder_config):
        """Test reindexing detects new files."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # First, index all files
        result = loop.run_until_complete(
            indexer.reindex_folders(folder_configs=folder_config)
        )
        
        assert result.new_count == 5
        
        # Add a new file
        music_dir = Path(temp_media_folder) / "Music"
        (music_dir / "new_track.mp3").write_text("new track content")
        
        # Re-index
        result = loop.run_until_complete(
            indexer.reindex_folders(folder_configs=folder_config)
        )
        
        # Should detect one new file
        assert result.new_count == 1
    
    def test_reindex_folders_detects_moves(self, temp_media_folder, indexer, folder_config):
        """Test reindexing detects moved files."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # First, index all files
        result = loop.run_until_complete(
            indexer.reindex_folders(folder_configs=folder_config)
        )
        
        assert result.new_count == 5
        
        # Move a file within the music folder (rename)
        music_dir = Path(temp_media_folder) / "Music"
        old_path = music_dir / "track1.mp3"
        new_path = music_dir / "renamed_track.mp3"
        old_path.rename(new_path)
        
        # Re-index
        result = loop.run_until_complete(
            indexer.reindex_folders(folder_configs=folder_config)
        )
        
        # Should detect one move (not new + deleted)
        assert result.moved_count == 1
        assert result.new_count == 0
        assert result.deleted_count == 0
    
    def test_reindex_folders_handles_missing_folders(self, temp_media_folder, indexer):
        """Test reindexing gracefully handles missing folders."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Configure with non-existent folder
        config = MediaFolderConfig()
        config.music_folder = str(Path(temp_media_folder) / "NonExistent")
        config.sfx_folder = str(Path(temp_media_folder) / "SFX")  # Exists
        config.vfx_folder = None
        
        result = loop.run_until_complete(
            indexer.reindex_folders(folder_configs=config)
        )
        
        # Should still work, just skip missing folder
        assert result.new_count == 2  # Only SFX files
        assert "No media folders configured" not in result.errors
    
    def test_reindex_folders_with_progress_callback(self, temp_media_folder, indexer, folder_config):
        """Test that progress callback is called during reindexing."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        progress_updates = []
        
        def progress_callback(update):
            progress_updates.append(update)
        
        result = loop.run_until_complete(
            indexer.reindex_folders(
                folder_configs=folder_config,
                progress_callback=progress_callback
            )
        )
        
        # Should have received progress updates
        assert len(progress_updates) > 0
        
        # Check for expected operations
        operations = [u.get('operation') for u in progress_updates]
        assert 'scan' in operations
        assert 'complete' in operations
