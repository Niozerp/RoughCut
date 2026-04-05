"""Unit tests for the MediaImporter class.

Tests file validation, media pool import, progress reporting, and error handling.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from roughcut.backend.timeline.importer import (
    ImportResult,
    MediaImporter,
    MediaPoolReference,
    SUPPORTED_AUDIO_FORMATS,
    SUPPORTED_VFX_FORMATS,
)


class TestImportResult:
    """Test the ImportResult dataclass."""
    
    def test_import_result_creation(self):
        """Test creating an ImportResult instance."""
        result = ImportResult(
            imported_count=2,
            skipped_count=1,
            media_pool_refs=[
                MediaPoolReference(
                    file_path="/path/to/file.mp3",
                    media_pool_id="media_001",
                    media_type="music"
                )
            ],
            skipped_files=[
                {
                    "file_path": "/path/to/missing.wav",
                    "reason": "file_not_found",
                    "message": "File not found"
                }
            ]
        )
        
        assert result.imported_count == 2
        assert result.skipped_count == 1
        assert len(result.media_pool_refs) == 1
        assert len(result.skipped_files) == 1
        assert result.success is True
        assert result.error is None
    
    def test_import_result_with_error(self):
        """Test ImportResult with error state."""
        result = ImportResult(
            imported_count=0,
            skipped_count=0,
            media_pool_refs=[],
            skipped_files=[],
            success=False,
            error={
                "code": "FILE_ACCESS_DENIED",
                "message": "Permission denied"
            }
        )
        
        assert result.success is False
        assert result.error is not None
        assert result.error["code"] == "FILE_ACCESS_DENIED"


class TestMediaImporterValidation:
    """Test file validation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.importer = MediaImporter()
    
    def test_validate_file_exists_readable(self):
        """Test validating an existing readable file."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake mp3 content")
            temp_path = f.name
        
        try:
            is_valid, error = self.importer.validate_file_accessibility(temp_path)
            assert is_valid is True
            assert error is None
        finally:
            os.unlink(temp_path)
    
    def test_validate_file_not_found(self):
        """Test validating a non-existent file."""
        is_valid, error = self.importer.validate_file_accessibility("/nonexistent/path/file.mp3")
        
        assert is_valid is False
        assert error is not None
        assert error["code"] == "FILE_NOT_FOUND"
        assert "not found" in error["message"].lower()
    
    def test_validate_file_not_readable(self):
        """Test validating a file without read permissions."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake mp3 content")
            temp_path = f.name
        
        try:
            # Remove read permissions
            os.chmod(temp_path, 0o000)
            
            is_valid, error = self.importer.validate_file_accessibility(temp_path)
            
            assert is_valid is False
            assert error is not None
            assert error["code"] == "FILE_ACCESS_DENIED"
        finally:
            # Restore permissions for cleanup
            os.chmod(temp_path, 0o644)
            os.unlink(temp_path)
    
    def test_validate_supported_audio_formats(self):
        """Test that audio formats are recognized."""
        supported = SUPPORTED_AUDIO_FORMATS
        
        assert ".mp3" in supported
        assert ".wav" in supported
        assert ".aiff" in supported
        assert ".m4a" in supported
    
    def test_validate_supported_vfx_formats(self):
        """Test that VFX formats are recognized."""
        supported = SUPPORTED_VFX_FORMATS
        
        assert ".comp" in supported
        assert ".settings" in supported
        assert ".drfx" in supported
    
    def test_is_supported_format_audio(self):
        """Test checking supported audio formats."""
        assert self.importer._is_supported_format("/path/to/song.mp3") is True
        assert self.importer._is_supported_format("/path/to/effect.wav") is True
        assert self.importer._is_supported_format("/path/to/music.aiff") is True
    
    def test_is_supported_format_vfx(self):
        """Test checking supported VFX formats."""
        assert self.importer._is_supported_format("/path/to/template.comp") is True
        assert self.importer._is_supported_format("/path/to/effect.drfx") is True
        assert self.importer._is_supported_format("/path/to/settings.settings") is True
    
    def test_is_supported_format_unsupported(self):
        """Test checking unsupported formats."""
        assert self.importer._is_supported_format("/path/to/file.txt") is False
        assert self.importer._is_supported_format("/path/to/video.mp4") is False
        assert self.importer._is_supported_format("/path/to/doc.pdf") is False


class TestMediaImporterBatchValidation:
    """Test batch validation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.importer = MediaImporter()
    
    def test_validate_media_batch_all_valid(self):
        """Test batch validation with all valid files."""
        # Create temporary files
        temp_files = []
        try:
            for ext in [".mp3", ".wav"]:
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                    f.write(b"fake content")
                    temp_files.append(f.name)
            
            suggested_media = [
                {"file_path": temp_files[0], "media_type": "music"},
                {"file_path": temp_files[1], "media_type": "sfx"}
            ]
            
            valid, skipped = self.importer.validate_media_batch(suggested_media)
            
            assert len(valid) == 2
            assert len(skipped) == 0
        finally:
            for f in temp_files:
                if os.path.exists(f):
                    os.unlink(f)
    
    def test_validate_media_batch_with_missing(self):
        """Test batch validation with missing files."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake content")
            temp_path = f.name
        
        try:
            suggested_media = [
                {"file_path": temp_path, "media_type": "music"},
                {"file_path": "/nonexistent/file.wav", "media_type": "sfx"}
            ]
            
            valid, skipped = self.importer.validate_media_batch(suggested_media)
            
            assert len(valid) == 1
            assert len(skipped) == 1
            assert skipped[0]["file_path"] == "/nonexistent/file.wav"
            assert skipped[0]["reason"] == "file_not_found_or_inaccessible"
        finally:
            os.unlink(temp_path)
    
    def test_validate_media_batch_empty_list(self):
        """Test batch validation with empty list."""
        valid, skipped = self.importer.validate_media_batch([])
        
        assert len(valid) == 0
        assert len(skipped) == 0


class TestMediaImporterImport:
    """Test media import functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        mock_resolve_api = MagicMock()
        self.importer = MediaImporter(resolve_api=mock_resolve_api)
    
    def test_import_single_media_success(self):
        """Test importing a single media file successfully."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake mp3 content")
            temp_path = f.name
        
        try:
            # Mock the Resolve API to return a media pool reference
            self.importer.resolve_api.import_media_to_pool.return_value = "media_123"
            
            result = self.importer.import_single_media(
                file_path=temp_path,
                media_type="music"
            )
            
            assert result is not None
            assert result.file_path == temp_path
            assert result.media_pool_id == "media_123"
            assert result.media_type == "music"
        finally:
            os.unlink(temp_path)
    
    def test_import_single_media_not_found(self):
        """Test importing a non-existent file."""
        result = self.importer.import_single_media(
            file_path="/nonexistent/file.mp3",
            media_type="music"
        )
        
        assert result is None
    
    def test_import_single_media_unsupported_format(self):
        """Test importing a file with unsupported format."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"text content")
            temp_path = f.name
        
        try:
            result = self.importer.import_single_media(
                file_path=temp_path,
                media_type="music"
            )
            
            assert result is None
        finally:
            os.unlink(temp_path)
    
    def test_check_duplicate_in_media_pool_exists(self):
        """Test checking for duplicates when media exists."""
        self.importer.resolve_api.find_media_in_pool.return_value = "existing_media_123"
        
        duplicate_id = self.importer._check_duplicate_in_media_pool("/path/to/file.mp3")
        
        assert duplicate_id == "existing_media_123"
    
    def test_check_duplicate_in_media_pool_not_found(self):
        """Test checking for duplicates when media doesn't exist."""
        self.importer.resolve_api.find_media_in_pool.return_value = None
        
        duplicate_id = self.importer._check_duplicate_in_media_pool("/path/to/new_file.mp3")
        
        assert duplicate_id is None


class TestMediaImporterSuggestedMedia:
    """Test importing suggested media batch."""
    
    def setup_method(self):
        """Set up test fixtures."""
        mock_resolve_api = MagicMock()
        self.importer = MediaImporter(resolve_api=mock_resolve_api)
    
    def test_import_suggested_media_success(self):
        """Test importing a batch of suggested media."""
        temp_files = []
        try:
            # Create temporary media files
            for ext in [".mp3", ".wav"]:
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                    f.write(b"fake content")
                    temp_files.append(f.name)
            
            suggested_media = [
                {"file_path": temp_files[0], "media_type": "music", "usage": "intro"},
                {"file_path": temp_files[1], "media_type": "sfx", "usage": "transition"}
            ]
            
            # Mock the Resolve API
            self.importer.resolve_api.import_media_to_pool.side_effect = ["media_001", "media_002"]
            self.importer.resolve_api.find_media_in_pool.return_value = None
            
            result = self.importer.import_suggested_media(suggested_media)
            
            assert result.imported_count == 2
            assert result.skipped_count == 0
            assert len(result.media_pool_refs) == 2
            assert result.success is True
        finally:
            for f in temp_files:
                if os.path.exists(f):
                    os.unlink(f)
    
    def test_import_suggested_media_with_skipped(self):
        """Test importing with some files missing."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake content")
            temp_path = f.name
        
        try:
            suggested_media = [
                {"file_path": temp_path, "media_type": "music"},
                {"file_path": "/nonexistent/file.wav", "media_type": "sfx"},
                {"file_path": "/another/missing.comp", "media_type": "vfx"}
            ]
            
            # Mock the Resolve API
            self.importer.resolve_api.import_media_to_pool.return_value = "media_001"
            self.importer.resolve_api.find_media_in_pool.return_value = None
            
            result = self.importer.import_suggested_media(suggested_media)
            
            assert result.imported_count == 1
            assert result.skipped_count == 2
            assert len(result.media_pool_refs) == 1
            assert len(result.skipped_files) == 2
            assert result.success is True  # Should still succeed even with skips
        finally:
            os.unlink(temp_path)
    
    def test_import_suggested_media_empty_list(self):
        """Test importing empty list."""
        result = self.importer.import_suggested_media([])
        
        assert result.imported_count == 0
        assert result.skipped_count == 0
        assert len(result.media_pool_refs) == 0
        assert result.success is True


class TestMediaImporterProgressCallback:
    """Test progress callback functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        mock_resolve_api = MagicMock()
        self.importer = MediaImporter(resolve_api=mock_resolve_api)
    
    def test_progress_callback_called(self):
        """Test that progress callback is invoked during import."""
        temp_files = []
        try:
            # Create temporary media files
            for i in range(3):
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    f.write(b"fake content")
                    temp_files.append(f.name)
            
            suggested_media = [
                {"file_path": temp_files[0], "media_type": "music"},
                {"file_path": temp_files[1], "media_type": "music"},
                {"file_path": temp_files[2], "media_type": "sfx"}
            ]
            
            # Mock the Resolve API
            self.importer.resolve_api.import_media_to_pool.side_effect = ["m1", "m2", "m3"]
            self.importer.resolve_api.find_media_in_pool.return_value = None
            
            # Track progress calls
            progress_calls = []
            def progress_callback(current, total, message):
                progress_calls.append((current, total, message))
            
            self.importer.import_suggested_media(suggested_media, progress_callback=progress_callback)
            
            # Should have 3 progress calls (one per file)
            assert len(progress_calls) == 3
            assert progress_calls[0] == (1, 3, f"Importing: {Path(temp_files[0]).name}")
            assert progress_calls[1] == (2, 3, f"Importing: {Path(temp_files[1]).name}")
            assert progress_calls[2] == (3, 3, f"Importing: {Path(temp_files[2]).name}")
        finally:
            for f in temp_files:
                if os.path.exists(f):
                    os.unlink(f)
    
    def test_no_callback_no_error(self):
        """Test that import works without callback."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake content")
            temp_path = f.name
        
        try:
            suggested_media = [{"file_path": temp_path, "media_type": "music"}]
            
            self.importer.resolve_api.import_media_to_pool.return_value = "media_001"
            self.importer.resolve_api.find_media_in_pool.return_value = None
            
            # Should not raise error without callback
            result = self.importer.import_suggested_media(suggested_media)
            
            assert result.imported_count == 1
        finally:
            os.unlink(temp_path)


class TestMediaImporterErrorHandling:
    """Test error handling scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        mock_resolve_api = MagicMock()
        self.importer = MediaImporter(resolve_api=mock_resolve_api)
    
    def test_import_media_pool_api_error(self):
        """Test handling Resolve API errors during import."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake content")
            temp_path = f.name
        
        try:
            suggested_media = [{"file_path": temp_path, "media_type": "music"}]
            
            # Mock API to raise exception
            self.importer.resolve_api.import_media_to_pool.side_effect = Exception("API Error")
            self.importer.resolve_api.find_media_in_pool.return_value = None
            
            result = self.importer.import_suggested_media(suggested_media)
            
            # Should record as skipped when API fails
            assert result.imported_count == 0
            assert result.skipped_count == 1
            assert len(result.skipped_files) == 1
        finally:
            os.unlink(temp_path)
    
    def test_network_path_timeout(self):
        """Test handling network path timeouts."""
        # Simulate a network path that times out
        with patch('os.path.exists', side_effect=OSError("Network path timeout")):
            is_valid, error = self.importer.validate_file_accessibility("//nas/media/file.mp3")
            
            assert is_valid is False
            assert error is not None
    
    def test_duplicate_detection_prevents_reimport(self):
        """Test that duplicates are not re-imported."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake content")
            temp_path = f.name
        
        try:
            suggested_media = [{"file_path": temp_path, "media_type": "music"}]
            
            # Mock to indicate media already exists
            self.importer.resolve_api.find_media_in_pool.return_value = "existing_media_123"
            
            result = self.importer.import_suggested_media(suggested_media)
            
            # Should use existing reference, not call import
            assert result.imported_count == 1
            assert result.media_pool_refs[0].media_pool_id == "existing_media_123"
            # import_media_to_pool should NOT be called
            self.importer.resolve_api.import_media_to_pool.assert_not_called()
        finally:
            os.unlink(temp_path)


class TestMediaImporterEdgeCases:
    """Test edge cases and special scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        mock_resolve_api = MagicMock()
        self.importer = MediaImporter(resolve_api=mock_resolve_api)
    
    def test_empty_file(self):
        """Test handling empty files."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            # Write nothing - empty file
            pass
        
        temp_path = f.name
        
        try:
            # Empty file should still be considered valid for import
            is_valid, error = self.importer.validate_file_accessibility(temp_path)
            
            assert is_valid is True
            assert error is None
        finally:
            os.unlink(temp_path)
    
    def test_very_long_filename(self):
        """Test handling very long filenames."""
        # Create a filename close to typical filesystem limits
        long_name = "a" * 200 + ".mp3"
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake content")
            temp_path = f.name
        
        try:
            is_valid, error = self.importer.validate_file_accessibility(temp_path)
            
            # Should still validate successfully
            assert is_valid is True
            assert error is None
        finally:
            os.unlink(temp_path)
    
    def test_special_characters_in_path(self):
        """Test handling special characters in paths."""
        # Note: This test may fail on some filesystems
        # Create a file with spaces and special chars
        with tempfile.NamedTemporaryFile(
            suffix="test file with spaces & symbols.mp3",
            delete=False
        ) as f:
            f.write(b"fake content")
            temp_path = f.name
        
        try:
            is_valid, error = self.importer.validate_file_accessibility(temp_path)
            
            assert is_valid is True
            assert error is None
        finally:
            os.unlink(temp_path)
    
    def test_case_insensitive_extensions(self):
        """Test case insensitive file extension matching."""
        assert self.importer._is_supported_format("/path/to/file.MP3") is True
        assert self.importer._is_supported_format("/path/to/file.Wav") is True
        assert self.importer._is_supported_format("/path/to/file.COMP") is True
