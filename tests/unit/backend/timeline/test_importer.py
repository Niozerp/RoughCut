"""Unit tests for the MediaImporter class."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

from roughcut.backend.timeline.importer import (
    ImportResult,
    MediaImporter,
    MediaPoolReference,
    SkippedFile,
    SUPPORTED_AUDIO_FORMATS,
    SUPPORTED_VFX_FORMATS,
)


class MockMediaPool:
    """Mock Media Pool for testing."""

    def __init__(self) -> None:
        self._media: Dict[str, Dict[str, Any]] = {}

    def find_media(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Find media in the mock pool."""
        return self._media.get(file_path)

    def import_media(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Import media to the mock pool."""
        if file_path not in self._media:
            self._media[file_path] = {
                "media_pool_id": f"mock_{hash(file_path)}",
                "file_path": file_path,
            }
        return self._media[file_path]

    def add_existing(self, file_path: str, media_id: str) -> None:
        """Add existing media for duplicate detection testing."""
        self._media[file_path] = {
            "media_pool_id": media_id,
            "file_path": file_path,
        }


class TestMediaImporter(unittest.TestCase):
    """Test cases for MediaImporter class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_pool = MockMediaPool()
        self.importer = MediaImporter(self.mock_pool)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        pass

    # =========================================================================
    # File Path Resolution Tests
    # =========================================================================

    def test_resolve_file_paths_converts_to_absolute(self) -> None:
        """Test that relative paths are converted to absolute."""
        media = [{"file_path": "relative/path/file.mp3", "media_type": "music"}]
        
        result = self.importer.resolve_file_paths(media)
        
        self.assertEqual(len(result), 1)
        self.assertTrue(Path(result[0]["file_path"]).is_absolute())

    def test_resolve_file_paths_preserves_absolute_paths(self) -> None:
        """Test that absolute paths are preserved."""
        abs_path = "/absolute/path/file.mp3"
        media = [{"file_path": abs_path, "media_type": "music"}]
        
        result = self.importer.resolve_file_paths(media)
        
        self.assertEqual(result[0]["file_path"], abs_path)

    def test_resolve_file_paths_handles_missing_paths(self) -> None:
        """Test handling of media items without file paths."""
        media = [{"media_type": "music"}]  # Missing file_path
        
        result = self.importer.resolve_file_paths(media)
        
        # Should still return the item but with empty path
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].get("file_path", ""), "")

    # =========================================================================
    # File Accessibility Validation Tests
    # =========================================================================

    def test_validate_file_accessibility_missing_file(self) -> None:
        """Test validation of non-existent file."""
        is_valid, error = self.importer.validate_file_accessibility("/nonexistent/file.mp3")
        
        self.assertFalse(is_valid)
        self.assertIn("not found", error.lower())

    def test_validate_file_accessibility_unsupported_format(self) -> None:
        """Test validation of unsupported file format."""
        with tempfile.NamedTemporaryFile(suffix=".unsupported", delete=False) as f:
            f.write(b"test")
            temp_path = f.name
        
        try:
            is_valid, error = self.importer.validate_file_accessibility(temp_path)
            
            self.assertFalse(is_valid)
            self.assertIn("unsupported", error.lower())
        finally:
            os.unlink(temp_path)

    def test_validate_file_accessibility_empty_file(self) -> None:
        """Test validation of empty file."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            # Write nothing - file is empty
            temp_path = f.name
        
        try:
            is_valid, error = self.importer.validate_file_accessibility(temp_path)
            
            self.assertFalse(is_valid)
            self.assertIn("empty", error.lower())
        finally:
            os.unlink(temp_path)

    def test_validate_file_accessibility_valid_file(self) -> None:
        """Test validation of valid file."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF....WAVE")  # Some content
            temp_path = f.name
        
        try:
            is_valid, error = self.importer.validate_file_accessibility(temp_path)
            
            self.assertTrue(is_valid)
            self.assertIsNone(error)
        finally:
            os.unlink(temp_path)

    def test_validate_file_accessibility_supported_formats(self) -> None:
        """Test that all supported formats are accepted."""
        for ext in SUPPORTED_AUDIO_FORMATS | SUPPORTED_VFX_FORMATS:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                f.write(b"some content")
                temp_path = f.name
            
            try:
                is_valid, error = self.importer.validate_file_accessibility(temp_path)
                self.assertTrue(is_valid, f"Format {ext} should be valid")
                self.assertIsNone(error)
            finally:
                os.unlink(temp_path)

    # =========================================================================
    # Batch Validation Tests
    # =========================================================================

    def test_validate_media_batch_separates_valid_and_invalid(self) -> None:
        """Test batch validation separates valid and invalid files."""
        # Create one valid file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"audio data")
            valid_path = f.name
        
        try:
            media = [
                {"file_path": valid_path, "media_type": "music"},
                {"file_path": "/nonexistent/file.wav", "media_type": "sfx"},
                {"media_type": "vfx"},  # Missing file_path
            ]
            
            valid, skipped = self.importer.validate_media_batch(media)
            
            self.assertEqual(len(valid), 1)
            self.assertEqual(len(skipped), 2)
            self.assertEqual(valid[0]["file_path"], valid_path)
        finally:
            os.unlink(valid_path)

    def test_validate_media_batch_creates_proper_skip_reasons(self) -> None:
        """Test that skipped files have proper reasons."""
        media = [{"file_path": "/nonexistent/file.wav", "media_type": "sfx"}]
        
        valid, skipped = self.importer.validate_media_batch(media)
        
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0].reason, "validation_failed")
        self.assertIn("not found", skipped[0].message.lower())

    # =========================================================================
    # Import Tests
    # =========================================================================

    def test_import_to_media_pool_imports_valid_files(self) -> None:
        """Test importing valid media files."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"audio data")
            temp_path = f.name
        
        try:
            media = [{"file_path": temp_path, "media_type": "music"}]
            
            result = self.importer.import_to_media_pool(media)
            
            self.assertEqual(result.imported_count, 1)
            self.assertEqual(result.skipped_count, 0)
            self.assertEqual(len(result.media_pool_refs), 1)
            self.assertEqual(result.media_pool_refs[0].file_path, temp_path)
        finally:
            os.unlink(temp_path)

    def test_import_detects_duplicates(self) -> None:
        """Test that duplicate media is detected and not re-imported."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"audio data")
            temp_path = f.name
        
        try:
            # Add file as existing in pool
            self.mock_pool.add_existing(temp_path, "existing_123")
            
            media = [{"file_path": temp_path, "media_type": "music"}]
            
            result = self.importer.import_to_media_pool(media)
            
            # Should count as imported even though it was already in pool
            self.assertEqual(result.imported_count, 1)
            self.assertEqual(result.media_pool_refs[0].media_pool_id, "existing_123")
        finally:
            os.unlink(temp_path)

    def test_import_tracks_progress(self) -> None:
        """Test that progress callback is called during import."""
        progress_calls: List[tuple] = []
        
        def progress_callback(message: str, current: int, total: int) -> None:
            progress_calls.append((message, current, total))
        
        self.importer.set_progress_callback(progress_callback)
        
        # Create two temp files
        files = []
        try:
            for i in range(2):
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    f.write(b"audio data")
                    files.append(f.name)
            
            media = [
                {"file_path": files[0], "media_type": "music"},
                {"file_path": files[1], "media_type": "sfx"},
            ]
            
            self.importer.import_to_media_pool(media)
            
            # Progress should be called for each file
            self.assertEqual(len(progress_calls), 2)
            self.assertIn("Importing", progress_calls[0][0])
            self.assertEqual(progress_calls[0][1], 1)  # current
            self.assertEqual(progress_calls[0][2], 2)   # total
        finally:
            for f in files:
                os.unlink(f)

    # =========================================================================
    # Full Import Flow Tests
    # =========================================================================

    def test_import_suggested_media_full_flow(self) -> None:
        """Test the complete import flow with mixed valid/invalid files."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"audio data")
            valid_path = f.name
        
        try:
            suggested_media = [
                {"file_path": valid_path, "media_type": "music", "usage": "intro"},
                {"file_path": "/nonexistent/file.wav", "media_type": "sfx", "usage": "effect"},
            ]
            
            result = self.importer.import_suggested_media(suggested_media)
            
            self.assertEqual(result.imported_count, 1)
            self.assertEqual(result.skipped_count, 1)
            self.assertEqual(len(result.media_pool_refs), 1)
            self.assertEqual(len(result.skipped_files), 1)
        finally:
            os.unlink(valid_path)

    def test_import_empty_list(self) -> None:
        """Test importing empty list."""
        result = self.importer.import_suggested_media([])
        
        self.assertEqual(result.imported_count, 0)
        self.assertEqual(result.skipped_count, 0)

    # =========================================================================
    # Data Class Tests
    # =========================================================================

    def test_import_result_to_dict(self) -> None:
        """Test ImportResult serialization."""
        result = ImportResult(
            imported_count=2,
            skipped_count=1,
            media_pool_refs=[
                MediaPoolReference("/path/file.mp3", "id1", "music"),
            ],
            skipped_files=[
                SkippedFile("/missing.wav", "not_found", "File not found"),
            ],
        )
        
        data = result.to_dict()
        
        self.assertEqual(data["imported_count"], 2)
        self.assertEqual(data["skipped_count"], 1)
        self.assertEqual(len(data["media_pool_refs"]), 1)
        self.assertEqual(len(data["skipped_files"]), 1)

    def test_media_pool_reference_to_dict(self) -> None:
        """Test MediaPoolReference serialization."""
        ref = MediaPoolReference("/path/file.mp3", "id123", "music")
        
        data = ref.to_dict()
        
        self.assertEqual(data["file_path"], "/path/file.mp3")
        self.assertEqual(data["media_pool_id"], "id123")
        self.assertEqual(data["media_type"], "music")

    def test_skipped_file_to_dict(self) -> None:
        """Test SkippedFile serialization."""
        skipped = SkippedFile("/missing.wav", "not_found", "File not found")
        
        data = skipped.to_dict()
        
        self.assertEqual(data["file_path"], "/missing.wav")
        self.assertEqual(data["reason"], "not_found")
        self.assertEqual(data["message"], "File not found")


class TestMediaImporterErrorHandling(unittest.TestCase):
    """Test error handling scenarios."""

    def test_handles_permission_error(self) -> None:
        """Test handling of file permission errors."""
        # On Windows, we can't easily test permission errors
        # But we can verify the validation returns correct format
        importer = MediaImporter()
        
        # Test with a directory instead of file (should fail readability check differently)
        with tempfile.TemporaryDirectory() as tmpdir:
            is_valid, error = importer.validate_file_accessibility(tmpdir)
            self.assertFalse(is_valid)
            self.assertIsNotNone(error)

    def test_handles_callback_exception(self) -> None:
        """Test that progress callback exceptions don't break import."""
        mock_pool = MockMediaPool()
        importer = MediaImporter(mock_pool)
        
        def bad_callback(message: str, current: int, total: int) -> None:
            raise RuntimeError("Callback error")
        
        importer.set_progress_callback(bad_callback)
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"audio data")
            temp_path = f.name
        
        try:
            media = [{"file_path": temp_path, "media_type": "music"}]
            
            # Should complete despite callback error
            result = importer.import_to_media_pool(media)
            
            self.assertEqual(result.imported_count, 1)
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()
