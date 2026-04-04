"""Unit tests for the change detection module.

Tests the ChangeDetector class and FileChangeSet dataclass for
identifying file system changes during re-indexing operations.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from roughcut.backend.indexing.change_detector import (
    ChangeDetector,
    FileMetadata,
    FileChangeSet
)
from roughcut.backend.database.models import MediaAsset


class TestFileMetadata:
    """Test FileMetadata dataclass."""
    
    def test_file_metadata_creation(self):
        """Test creating FileMetadata instance."""
        metadata = FileMetadata(
            file_hash="abc123",
            modified_time=datetime.now(),
            file_size=1024,
            category="music"
        )
        
        assert metadata.file_hash == "abc123"
        assert metadata.file_size == 1024
        assert metadata.category == "music"


class TestFileChangeSet:
    """Test FileChangeSet dataclass."""
    
    def test_changeset_creation(self):
        """Test creating FileChangeSet with empty lists."""
        changes = FileChangeSet(
            new_files=[],
            modified_files=[],
            moved_files=[],
            deleted_files=[],
            total_scanned=0
        )
        
        assert changes.new_files == []
        assert changes.modified_files == []
        assert changes.moved_files == []
        assert changes.deleted_files == []
        assert changes.total_scanned == 0
    
    def test_changeset_with_data(self):
        """Test FileChangeSet with actual data."""
        new_file = Path("/music/new.mp3")
        old_path = Path("/sfx/old.wav")
        new_path = Path("/music/moved.wav")
        
        changes = FileChangeSet(
            new_files=[new_file],
            modified_files=[],
            moved_files=[(old_path, new_path)],
            deleted_files=["asset-123"],
            total_scanned=100
        )
        
        assert len(changes.new_files) == 1
        assert len(changes.moved_files) == 1
        assert len(changes.deleted_files) == 1
        assert changes.total_scanned == 100


class TestChangeDetector:
    """Test ChangeDetector change detection logic."""
    
    @pytest.fixture
    def detector(self):
        """Create a ChangeDetector instance."""
        return ChangeDetector()
    
    def test_detect_new_files_empty_db(self, detector):
        """Test detecting new files when database is empty."""
        scanned = {
            Path('/music/new1.mp3'): FileMetadata(
                file_hash='hash1',
                modified_time=datetime.now(),
                file_size=1000,
                category='music'
            ),
            Path('/music/new2.mp3'): FileMetadata(
                file_hash='hash2',
                modified_time=datetime.now(),
                file_size=2000,
                category='music'
            ),
        }
        
        db_assets = []
        
        changes = detector.detect_changes(scanned, db_assets)
        
        assert len(changes.new_files) == 2
        assert len(changes.modified_files) == 0
        assert len(changes.moved_files) == 0
        assert len(changes.deleted_files) == 0
        assert changes.total_scanned == 2
    
    def test_detect_no_changes(self, detector):
        """Test detecting no changes when files match."""
        now = datetime.now()
        
        scanned = {
            Path('/music/existing.mp3'): FileMetadata(
                file_hash='same_hash',
                modified_time=now,
                file_size=1000,
                category='music'
            ),
        }
        
        db_assets = [
            MediaAsset(
                id='asset-1',
                file_path='/music/existing.mp3',
                file_name='existing.mp3',
                file_hash='same_hash',
                modified_time=now,
                category='music'
            )
        ]
        
        changes = detector.detect_changes(scanned, db_assets)
        
        assert len(changes.new_files) == 0
        assert len(changes.modified_files) == 0
        assert len(changes.moved_files) == 0
        assert len(changes.deleted_files) == 0
    
    def test_detect_modified_files(self, detector):
        """Test detecting modified files by hash difference."""
        now = datetime.now()
        
        scanned = {
            Path('/music/changed.mp3'): FileMetadata(
                file_hash='new_hash',
                modified_time=now,
                file_size=1000,
                category='music'
            ),
        }
        
        db_assets = [
            MediaAsset(
                id='asset-1',
                file_path='/music/changed.mp3',
                file_name='changed.mp3',
                file_hash='old_hash',
                modified_time=now - timedelta(hours=1),
                category='music'
            )
        ]
        
        changes = detector.detect_changes(scanned, db_assets)
        
        assert len(changes.new_files) == 0
        assert len(changes.modified_files) == 1
        assert len(changes.moved_files) == 0
        assert len(changes.deleted_files) == 0
        assert changes.modified_files[0] == Path('/music/changed.mp3')
    
    def test_detect_modified_by_time(self, detector):
        """Test detecting modified files by modification time."""
        old_time = datetime.now() - timedelta(days=1)
        new_time = datetime.now()
        
        scanned = {
            Path('/music/updated.mp3'): FileMetadata(
                file_hash='same_hash',
                modified_time=new_time,
                file_size=1000,
                category='music'
            ),
        }
        
        db_assets = [
            MediaAsset(
                id='asset-1',
                file_path='/music/updated.mp3',
                file_name='updated.mp3',
                file_hash='same_hash',
                modified_time=old_time,
                category='music'
            )
        ]
        
        changes = detector.detect_changes(scanned, db_assets)
        
        assert len(changes.new_files) == 0
        assert len(changes.modified_files) == 1
        assert changes.modified_files[0] == Path('/music/updated.mp3')
    
    def test_detect_moved_files(self, detector):
        """Test detecting moved files by hash matching."""
        scanned = {
            Path('/music/moved.wav'): FileMetadata(
                file_hash='abc123',
                modified_time=datetime.now(),
                file_size=1000,
                category='music'
            ),
        }
        
        db_assets = [
            MediaAsset(
                id='asset-1',
                file_path='/sfx/old_location.wav',
                file_name='old_location.wav',
                file_hash='abc123',
                modified_time=datetime.now(),
                category='sfx'
            )
        ]
        
        changes = detector.detect_changes(scanned, db_assets)
        
        assert len(changes.new_files) == 0
        assert len(changes.modified_files) == 0
        assert len(changes.moved_files) == 1
        assert len(changes.deleted_files) == 0
        
        old_path, new_path = changes.moved_files[0]
        assert old_path == Path('/sfx/old_location.wav')
        assert new_path == Path('/music/moved.wav')
    
    def test_detect_deleted_files(self, detector):
        """Test detecting orphaned database entries."""
        scanned = {}  # Empty - no files on disk
        
        db_assets = [
            MediaAsset(
                id='asset-1',
                file_path='/music/deleted.mp3',
                file_name='deleted.mp3',
                file_hash='hash1',
                category='music'
            ),
            MediaAsset(
                id='asset-2',
                file_path='/sfx/gone.wav',
                file_name='gone.wav',
                file_hash='hash2',
                category='sfx'
            ),
        ]
        
        changes = detector.detect_changes(scanned, db_assets)
        
        assert len(changes.new_files) == 0
        assert len(changes.modified_files) == 0
        assert len(changes.moved_files) == 0
        assert len(changes.deleted_files) == 2
        assert 'asset-1' in changes.deleted_files
        assert 'asset-2' in changes.deleted_files
    
    def test_detect_all_change_types(self, detector):
        """Test detecting all types of changes simultaneously."""
        now = datetime.now()
        
        scanned = {
            # New file
            Path('/music/new.mp3'): FileMetadata(
                file_hash='new_hash',
                modified_time=now,
                file_size=1000,
                category='music'
            ),
            # Modified file (hash changed)
            Path('/music/modified.mp3'): FileMetadata(
                file_hash='new_modified_hash',
                modified_time=now,
                file_size=1500,
                category='music'
            ),
            # Moved file (same hash, different path)
            Path('/music/moved.wav'): FileMetadata(
                file_hash='move_hash',
                modified_time=now,
                file_size=2000,
                category='music'
            ),
            # Unchanged file
            Path('/music/unchanged.mp3'): FileMetadata(
                file_hash='unchanged_hash',
                modified_time=now,
                file_size=3000,
                category='music'
            ),
        }
        
        db_assets = [
            # Modified file in DB (old hash)
            MediaAsset(
                id='asset-modified',
                file_path='/music/modified.mp3',
                file_name='modified.mp3',
                file_hash='old_modified_hash',  # Different!
                modified_time=now - timedelta(hours=1),
                category='music'
            ),
            # Moved file in DB (old path)
            MediaAsset(
                id='asset-moved',
                file_path='/sfx/old_path.wav',
                file_name='old_path.wav',
                file_hash='move_hash',  # Same hash!
                modified_time=now,
                category='sfx'
            ),
            # Unchanged file
            MediaAsset(
                id='asset-unchanged',
                file_path='/music/unchanged.mp3',
                file_name='unchanged.mp3',
                file_hash='unchanged_hash',
                modified_time=now,
                category='music'
            ),
            # Deleted file (in DB but not on disk)
            MediaAsset(
                id='asset-deleted',
                file_path='/music/deleted.mp3',
                file_name='deleted.mp3',
                file_hash='deleted_hash',
                category='music'
            ),
        ]
        
        changes = detector.detect_changes(scanned, db_assets)
        
        assert len(changes.new_files) == 1
        assert Path('/music/new.mp3') in changes.new_files
        
        assert len(changes.modified_files) == 1
        assert Path('/music/modified.mp3') in changes.modified_files
        
        assert len(changes.moved_files) == 1
        old_path, new_path = changes.moved_files[0]
        assert old_path == Path('/sfx/old_path.wav')
        assert new_path == Path('/music/moved.wav')
        
        assert len(changes.deleted_files) == 1
        assert 'asset-deleted' in changes.deleted_files
    
    def test_detect_changes_simple(self, detector):
        """Test simplified change detection."""
        scanned_paths = {
            '/music/file1.mp3',
            '/music/file2.mp3'
        }
        
        db_assets = [
            MediaAsset(
                id='asset-1',
                file_path='/music/file1.mp3',
                file_name='file1.mp3',
                category='music'
            ),
            MediaAsset(
                id='asset-2',
                file_path='/music/gone.mp3',
                file_name='gone.mp3',
                category='music'
            ),
        ]
        
        orphaned, new_paths = detector.detect_changes_simple(scanned_paths, db_assets)
        
        assert len(orphaned) == 1
        assert 'asset-2' in orphaned
        
        assert len(new_paths) == 1
        assert new_paths[0] == Path('/music/file2.mp3')
    
    def test_duplicate_hashes_in_db(self, detector):
        """Test handling duplicate hashes in database."""
        scanned = {
            Path('/music/new.wav'): FileMetadata(
                file_hash='duplicate_hash',
                modified_time=datetime.now(),
                file_size=1000,
                category='music'
            ),
        }
        
        # Two assets with same hash (edge case)
        db_assets = [
            MediaAsset(
                id='asset-1',
                file_path='/sfx/file1.wav',
                file_name='file1.wav',
                file_hash='duplicate_hash',
                category='sfx'
            ),
            MediaAsset(
                id='asset-2',
                file_path='/sfx/file2.wav',
                file_name='file2.wav',
                file_hash='duplicate_hash',
                category='sfx'
            ),
        ]
        
        changes = detector.detect_changes(scanned, db_assets)
        
        # Should be detected as moved (matching first asset with hash)
        assert len(changes.moved_files) == 1
        
        # Second asset with same hash should be orphaned
        assert len(changes.deleted_files) == 1
    
    def test_empty_scan(self, detector):
        """Test detecting changes when scan is empty."""
        scanned = {}
        
        db_assets = [
            MediaAsset(
                id='asset-1',
                file_path='/music/file.mp3',
                file_name='file.mp3',
                category='music'
            ),
        ]
        
        changes = detector.detect_changes(scanned, db_assets)
        
        assert len(changes.new_files) == 0
        assert len(changes.deleted_files) == 1
    
    def test_empty_db(self, detector):
        """Test detecting changes when database is empty."""
        scanned = {
            Path('/music/file.mp3'): FileMetadata(
                file_hash='hash1',
                modified_time=datetime.now(),
                file_size=1000,
                category='music'
            ),
        }
        
        db_assets = []
        
        changes = detector.detect_changes(scanned, db_assets)
        
        assert len(changes.new_files) == 1
        assert len(changes.deleted_files) == 0
