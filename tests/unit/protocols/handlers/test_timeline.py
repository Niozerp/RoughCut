"""Unit tests for timeline protocol handlers."""

from __future__ import annotations

import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from roughcut.protocols.handlers.timeline import (
    handle_import_suggested_media,
    handle_check_resolve_availability,
    error_response,
    success_response,
    ERROR_CODES,
)


class TestTimelineHandlers(unittest.TestCase):
    """Test cases for timeline protocol handlers."""

    # =========================================================================
    # Parameter Validation Tests
    # =========================================================================

    def test_import_missing_timeline_id(self) -> None:
        """Test error when timeline_id is missing."""
        params = {
            "suggested_media": [{"file_path": "/path/file.mp3", "media_type": "music"}]
        }
        
        result = handle_import_suggested_media(params)
        
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])
        self.assertIn("timeline_id", result["error"]["message"].lower())

    def test_import_invalid_suggested_media_type(self) -> None:
        """Test error when suggested_media is not a list."""
        params = {
            "timeline_id": "timeline_123",
            "suggested_media": "not_a_list"
        }
        
        result = handle_import_suggested_media(params)
        
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])

    def test_import_empty_suggested_media(self) -> None:
        """Test handling of empty suggested_media list."""
        params = {
            "timeline_id": "timeline_123",
            "suggested_media": []
        }
        
        result = handle_import_suggested_media(params)
        
        self.assertIsNone(result["error"])
        self.assertEqual(result["result"]["imported_count"], 0)
        self.assertEqual(result["result"]["skipped_count"], 0)

    def test_import_invalid_media_item(self) -> None:
        """Test error when media item is not a dict."""
        params = {
            "timeline_id": "timeline_123",
            "suggested_media": ["not_a_dict"]
        }
        
        result = handle_import_suggested_media(params)
        
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])

    def test_import_missing_file_path(self) -> None:
        """Test error when media item lacks file_path."""
        params = {
            "timeline_id": "timeline_123",
            "suggested_media": [{"media_type": "music"}]  # Missing file_path
        }
        
        result = handle_import_suggested_media(params)
        
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])
        self.assertIn("file_path", result["error"]["message"].lower())

    def test_import_missing_media_type(self) -> None:
        """Test error when media item lacks media_type."""
        params = {
            "timeline_id": "timeline_123",
            "suggested_media": [{"file_path": "/path/file.mp3"}]  # Missing media_type
        }
        
        result = handle_import_suggested_media(params)
        
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])
        self.assertIn("media_type", result["error"]["message"].lower())

    # =========================================================================
    # Resolve Availability Tests
    # =========================================================================

    @patch("roughcut.protocols.handlers.timeline.ResolveApi")
    def test_import_resolve_not_available(self, mock_resolve_class: Any) -> None:
        """Test error when Resolve is not available."""
        mock_resolve = MagicMock()
        mock_resolve.is_available.return_value = False
        mock_resolve_class.return_value = mock_resolve
        
        params = {
            "timeline_id": "timeline_123",
            "suggested_media": [{"file_path": "/path/file.mp3", "media_type": "music"}]
        }
        
        result = handle_import_suggested_media(params)
        
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["error"]["code"], ERROR_CODES["RESOLVE_NOT_AVAILABLE"])

    @patch("roughcut.protocols.handlers.timeline.ResolveApi")
    def test_check_resolve_availability_true(self, mock_resolve_class: Any) -> None:
        """Test availability check when Resolve is available."""
        mock_resolve = MagicMock()
        mock_resolve.is_available.return_value = True
        mock_resolve_class.return_value = mock_resolve
        
        result = handle_check_resolve_availability({})
        
        self.assertIsNone(result["error"])
        self.assertTrue(result["result"]["available"])

    @patch("roughcut.protocols.handlers.timeline.ResolveApi")
    def test_check_resolve_availability_false(self, mock_resolve_class: Any) -> None:
        """Test availability check when Resolve is not available."""
        mock_resolve = MagicMock()
        mock_resolve.is_available.return_value = False
        mock_resolve_class.return_value = mock_resolve
        
        result = handle_check_resolve_availability({})
        
        self.assertIsNone(result["error"])
        self.assertFalse(result["result"]["available"])

    # =========================================================================
    # Success Case Tests
    # =========================================================================

    @patch("roughcut.protocols.handlers.timeline.ResolveApi")
    @patch("roughcut.protocols.handlers.timeline.MediaImporter")
    def test_import_success(self, mock_importer_class: Any, mock_resolve_class: Any) -> None:
        """Test successful media import."""
        # Mock Resolve availability
        mock_resolve = MagicMock()
        mock_resolve.is_available.return_value = True
        mock_resolve_class.return_value = mock_resolve
        
        # Mock importer result
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "imported_count": 2,
            "skipped_count": 0,
            "media_pool_refs": [
                {"file_path": "/path/file1.mp3", "media_pool_id": "id1", "media_type": "music"},
                {"file_path": "/path/file2.wav", "media_pool_id": "id2", "media_type": "sfx"},
            ],
            "skipped_files": [],
        }
        
        mock_importer = MagicMock()
        mock_importer.import_suggested_media.return_value = mock_result
        mock_importer_class.return_value = mock_importer
        
        params = {
            "timeline_id": "timeline_123",
            "suggested_media": [
                {"file_path": "/path/file1.mp3", "media_type": "music"},
                {"file_path": "/path/file2.wav", "media_type": "sfx"},
            ]
        }
        
        result = handle_import_suggested_media(params)
        
        self.assertIsNone(result["error"])
        self.assertEqual(result["result"]["imported_count"], 2)
        self.assertEqual(len(result["result"]["media_pool_refs"]), 2)

    @patch("roughcut.protocols.handlers.timeline.ResolveApi")
    @patch("roughcut.protocols.handlers.timeline.MediaImporter")
    def test_import_with_skipped_files(self, mock_importer_class: Any, mock_resolve_class: Any) -> None:
        """Test import with some skipped files."""
        mock_resolve = MagicMock()
        mock_resolve.is_available.return_value = True
        mock_resolve_class.return_value = mock_resolve
        
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "imported_count": 1,
            "skipped_count": 1,
            "media_pool_refs": [
                {"file_path": "/path/file1.mp3", "media_pool_id": "id1", "media_type": "music"},
            ],
            "skipped_files": [
                {"file_path": "/missing/file.wav", "reason": "file_not_found", "message": "File not found"},
            ],
        }
        
        mock_importer = MagicMock()
        mock_importer.import_suggested_media.return_value = mock_result
        mock_importer_class.return_value = mock_importer
        
        params = {
            "timeline_id": "timeline_123",
            "suggested_media": [
                {"file_path": "/path/file1.mp3", "media_type": "music"},
                {"file_path": "/missing/file.wav", "media_type": "sfx"},
            ]
        }
        
        result = handle_import_suggested_media(params)
        
        self.assertIsNone(result["error"])
        self.assertEqual(result["result"]["imported_count"], 1)
        self.assertEqual(result["result"]["skipped_count"], 1)
        self.assertEqual(len(result["result"]["skipped_files"]), 1)

    # =========================================================================
    # Error Response Tests
    # =========================================================================

    def test_error_response_structure(self) -> None:
        """Test error response has correct structure."""
        response = error_response(
            code="TEST_CODE",
            message="Test message",
            category="test_category",
            recoverable=True,
            suggestion="Test suggestion"
        )
        
        self.assertIsNotNone(response["error"])
        self.assertEqual(response["error"]["code"], "TEST_CODE")
        self.assertEqual(response["error"]["message"], "Test message")
        self.assertEqual(response["error"]["category"], "test_category")
        self.assertTrue(response["error"]["recoverable"])
        self.assertEqual(response["error"]["suggestion"], "Test suggestion")
        self.assertIsNone(response["result"])

    def test_success_response_structure(self) -> None:
        """Test success response has correct structure."""
        test_result = {"key": "value"}
        response = success_response(test_result)
        
        self.assertIsNone(response["error"])
        self.assertEqual(response["result"], test_result)

    # =========================================================================
    # Exception Handling Tests
    # =========================================================================

    @patch("roughcut.protocols.handlers.timeline.ResolveApi")
    def test_import_handles_exception(self, mock_resolve_class: Any) -> None:
        """Test that exceptions are handled gracefully."""
        mock_resolve_class.side_effect = Exception("Unexpected error")
        
        params = {
            "timeline_id": "timeline_123",
            "suggested_media": [{"file_path": "/path/file.mp3", "media_type": "music"}]
        }
        
        result = handle_import_suggested_media(params)
        
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["error"]["code"], ERROR_CODES["INTERNAL_ERROR"])
        self.assertIn("internal error", result["error"]["message"].lower())

    def test_check_availability_handles_exception(self) -> None:
        """Test that availability check handles exceptions."""
        with patch("roughcut.protocols.handlers.timeline.ResolveApi") as mock_class:
            mock_class.side_effect = Exception("API error")
            
            result = handle_check_resolve_availability({})
            
            self.assertIsNotNone(result["error"])
            self.assertEqual(result["error"]["code"], ERROR_CODES["INTERNAL_ERROR"])


class TestErrorCodes(unittest.TestCase):
    """Test error codes are correctly defined."""

    def test_all_error_codes_defined(self) -> None:
        """Verify all expected error codes exist."""
        expected_codes = [
            "INVALID_PARAMS",
            "RESOLVE_NOT_AVAILABLE",
            "IMPORT_FAILED",
            "FILE_NOT_FOUND",
            "FILE_ACCESS_DENIED",
            "UNSUPPORTED_FORMAT",
            "INTERNAL_ERROR",
        ]
        
        for code in expected_codes:
            self.assertIn(code, ERROR_CODES)
            self.assertEqual(ERROR_CODES[code], code)


if __name__ == "__main__":
    unittest.main()
