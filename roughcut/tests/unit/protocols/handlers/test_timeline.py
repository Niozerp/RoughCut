"""Unit tests for timeline protocol handlers.

Tests JSON-RPC handlers for timeline operations.
"""

import unittest
from unittest.mock import MagicMock, patch

from roughcut.protocols.handlers.timeline import (
    create_timeline,
    create_timeline_from_document,
    _error_response,
    ERROR_CODES
)


class TestErrorResponse(unittest.TestCase):
    """Test error response helper."""
    
    def test_error_response_structure(self):
        """Test error response has correct structure."""
        result = _error_response(
            code="TEST_ERROR",
            category="test",
            message="Test message",
            suggestion="Test suggestion",
            recoverable=True
        )
        
        self.assertIn("error", result)
        error = result["error"]
        self.assertEqual(error["code"], "TEST_ERROR")
        self.assertEqual(error["category"], "test")
        self.assertEqual(error["message"], "Test message")
        self.assertEqual(error["suggestion"], "Test suggestion")
        self.assertTrue(error["recoverable"])
    
    def test_error_response_default_recoverable(self):
        """Test default recoverable value."""
        result = _error_response(
            code="TEST",
            category="test",
            message="Test",
            suggestion="Test"
        )
        
        self.assertTrue(result["error"]["recoverable"])


class TestCreateTimeline(unittest.TestCase):
    """Test cases for create_timeline handler."""
    
    @patch('roughcut.protocols.handlers.timeline.TimelineBuilder')
    def test_create_timeline_success(self, mock_builder_class):
        """Test successful timeline creation."""
        # Setup mock
        mock_builder = MagicMock()
        mock_builder_class.return_value = mock_builder
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.timeline_name = "Test_Timeline"
        mock_result.timeline_id = "timeline_123"
        mock_result.tracks_created = {"video": 1, "audio": 2}
        mock_builder.create_timeline.return_value = mock_result
        
        # Call handler
        params = {
            "source_clip_name": "clip",
            "format_template": "format"
        }
        result = create_timeline(params)
        
        # Verify
        self.assertTrue(result["success"])
        self.assertEqual(result["timeline_name"], "Test_Timeline")
        self.assertEqual(result["timeline_id"], "timeline_123")
        self.assertEqual(result["tracks_created"], {"video": 1, "audio": 2})
    
    def test_create_timeline_missing_source_clip(self):
        """Test error when source clip is missing."""
        params = {"format_template": "format"}
        result = create_timeline(params)
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["MISSING_SOURCE_CLIP"])
    
    def test_create_timeline_missing_format_template(self):
        """Test error when format template is missing."""
        params = {"source_clip_name": "clip"}
        result = create_timeline(params)
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["MISSING_FORMAT_TEMPLATE"])
    
    def test_create_timeline_none_params(self):
        """Test handling of None params."""
        result = create_timeline(None)
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["MISSING_SOURCE_CLIP"])
    
    @patch('roughcut.protocols.handlers.timeline.TimelineBuilder')
    def test_create_timeline_failure(self, mock_builder_class):
        """Test handling of builder failure."""
        mock_builder = MagicMock()
        mock_builder_class.return_value = mock_builder
        
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = {
            "code": "TIMELINE_CREATION_FAILED",
            "category": "resolve_api",
            "message": "Creation failed",
            "suggestion": "Check Resolve",
            "recoverable": True
        }
        mock_builder.create_timeline.return_value = mock_result
        
        params = {
            "source_clip_name": "clip",
            "format_template": "format"
        }
        result = create_timeline(params)
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], "TIMELINE_CREATION_FAILED")
    
    @patch('roughcut.protocols.handlers.timeline.TimelineBuilder')
    def test_create_timeline_exception(self, mock_builder_class):
        """Test handling of unexpected exception."""
        mock_builder_class.side_effect = Exception("Unexpected error")
        
        params = {
            "source_clip_name": "clip",
            "format_template": "format"
        }
        result = create_timeline(params)
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["INTERNAL_ERROR"])


class TestCreateTimelineFromDocument(unittest.TestCase):
    """Test cases for create_timeline_from_document handler."""
    
    @patch('roughcut.protocols.handlers.timeline.get_session_manager')
    @patch('roughcut.protocols.handlers.timeline.TimelineBuilder')
    def test_create_timeline_from_document_success(
        self, mock_builder_class, mock_get_session_manager
    ):
        """Test successful creation from document."""
        # Setup session manager mock
        mock_session_manager = MagicMock()
        mock_get_session_manager.return_value = mock_session_manager
        
        mock_session = {
            "source_clip": {"name": "test_clip"},
            "format_template": {"name": "test_format"}
        }
        mock_session_manager.get_session.return_value = mock_session
        
        # Setup builder mock
        mock_builder = MagicMock()
        mock_builder_class.return_value = mock_builder
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.timeline_name = "RoughCut_test"
        mock_result.timeline_id = "timeline_123"
        mock_result.tracks_created = {"video": 2, "audio": 3}
        mock_builder.create_timeline.return_value = mock_result
        
        # Call handler
        params = {"session_id": "session_123"}
        result = create_timeline_from_document(params)
        
        # Verify
        self.assertTrue(result["success"])
        self.assertEqual(result["timeline_name"], "RoughCut_test")
        
        # Verify session was updated
        mock_session_manager.update_session.assert_called_once()
    
    def test_create_timeline_from_document_missing_session_id(self):
        """Test error when session ID is missing."""
        params = {}
        result = create_timeline_from_document(params)
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])
    
    def test_create_timeline_from_document_none_params(self):
        """Test handling of None params."""
        result = create_timeline_from_document(None)
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])
    
    @patch('roughcut.protocols.handlers.timeline.get_session_manager')
    def test_create_timeline_from_document_session_not_found(
        self, mock_get_session_manager
    ):
        """Test error when session is not found."""
        mock_session_manager = MagicMock()
        mock_get_session_manager.return_value = mock_session_manager
        mock_session_manager.get_session.return_value = None
        
        params = {"session_id": "nonexistent"}
        result = create_timeline_from_document(params)
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["SESSION_NOT_FOUND"])
    
    @patch('roughcut.protocols.handlers.timeline.get_session_manager')
    def test_create_timeline_from_document_missing_source_clip(
        self, mock_get_session_manager
    ):
        """Test error when source clip is missing from session."""
        mock_session_manager = MagicMock()
        mock_get_session_manager.return_value = mock_session_manager
        
        mock_session = {
            "format_template": {"name": "test_format"}
            # Missing source_clip
        }
        mock_session_manager.get_session.return_value = mock_session
        
        params = {"session_id": "session_123"}
        result = create_timeline_from_document(params)
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["MISSING_SOURCE_CLIP"])
    
    @patch('roughcut.protocols.handlers.timeline.get_session_manager')
    def test_create_timeline_from_document_missing_format_template(
        self, mock_get_session_manager
    ):
        """Test error when format template is missing from session."""
        mock_session_manager = MagicMock()
        mock_get_session_manager.return_value = mock_session_manager
        
        mock_session = {
            "source_clip": {"name": "test_clip"}
            # Missing format_template
        }
        mock_session_manager.get_session.return_value = mock_session
        
        params = {"session_id": "session_123"}
        result = create_timeline_from_document(params)
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["MISSING_FORMAT_TEMPLATE"])
    
    @patch('roughcut.protocols.handlers.timeline.get_session_manager')
    @patch('roughcut.protocols.handlers.timeline.TimelineBuilder')
    def test_create_timeline_from_document_uses_document_fallback(
        self, mock_builder_class, mock_get_session_manager
    ):
        """Test that it falls back to rough cut document for names."""
        # Setup session with rough_cut_document fallback
        mock_session_manager = MagicMock()
        mock_get_session_manager.return_value = mock_session_manager
        
        mock_session = {
            "source_clip": {},  # Empty, will use fallback
            "format_template": {},  # Empty, will use fallback
            "rough_cut_document": {
                "source_clip": "doc_source",
                "format_template": "doc_format"
            }
        }
        mock_session_manager.get_session.return_value = mock_session
        
        # Setup builder
        mock_builder = MagicMock()
        mock_builder_class.return_value = mock_builder
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.timeline_name = "Timeline"
        mock_result.timeline_id = "id"
        mock_result.tracks_created = {}
        mock_builder.create_timeline.return_value = mock_result
        
        params = {"session_id": "session_123"}
        result = create_timeline_from_document(params)
        
        # Verify it used fallback values
        call_args = mock_builder.create_timeline.call_args
        self.assertEqual(call_args[1]["source_clip_name"], "doc_source")
        self.assertEqual(call_args[1]["format_template"], "doc_format")


class TestErrorCodes(unittest.TestCase):
    """Test error codes constants."""
    
    def test_error_codes_defined(self):
        """Test that all expected error codes are defined."""
        expected_codes = [
            "INVALID_PARAMS",
            "SESSION_NOT_FOUND",
            "MISSING_SOURCE_CLIP",
            "MISSING_FORMAT_TEMPLATE",
            "TIMELINE_CREATION_FAILED",
            "RESOLVE_API_UNAVAILABLE",
            "INTERNAL_ERROR"
        ]
        
        for code in expected_codes:
            self.assertIn(code, ERROR_CODES)


if __name__ == "__main__":
    unittest.main()
