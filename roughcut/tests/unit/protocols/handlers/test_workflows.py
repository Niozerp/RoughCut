"""Unit tests for workflow protocol handlers.

Tests the JSON-RPC handlers in workflows.py.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock

from roughcut.protocols.handlers.workflows import (
    create_rough_cut_session,
    get_session_status,
    select_media_for_session,
    review_transcription_for_session,
    prepare_rough_cut_for_generation,
    ERROR_CODES
)
from roughcut.backend.workflows.session import get_session_manager, reset_session_manager


class TestCreateRoughCutSession(unittest.TestCase):
    """Test cases for create_rough_cut_session handler."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_session_manager()
    
    def tearDown(self):
        """Clean up after tests."""
        reset_session_manager()
    
    def test_create_session_success(self):
        """Test successful session creation."""
        result = create_rough_cut_session({})
        
        self.assertIn("result", result)
        self.assertIsNone(result.get("error"))
        
        result_data = result["result"]
        self.assertIn("session_id", result_data)
        self.assertEqual(result_data["status"], "created")
        self.assertIn("created_at", result_data)
    
    def test_create_session_with_none_params(self):
        """Test session creation with None params."""
        result = create_rough_cut_session(None)
        
        self.assertIn("result", result)
        self.assertIsNone(result.get("error"))
    
    @patch('roughcut.protocols.handlers.workflows.get_session_manager')
    def test_create_session_failure(self, mock_get_manager):
        """Test session creation failure handling."""
        mock_manager = MagicMock()
        mock_manager.create_session.side_effect = Exception("Test error")
        mock_get_manager.return_value = mock_manager
        
        result = create_rough_cut_session({})
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["SESSION_CREATE_ERROR"])


class TestGetSessionStatus(unittest.TestCase):
    """Test cases for get_session_status handler."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_session_manager()
        self.manager = get_session_manager()
        self.session = self.manager.create_session()
    
    def tearDown(self):
        """Clean up after tests."""
        reset_session_manager()
    
    def test_get_status_success(self):
        """Test successful status retrieval."""
        result = get_session_status({"session_id": self.session.session_id})
        
        self.assertIn("result", result)
        self.assertIsNone(result.get("error"))
        
        result_data = result["result"]
        self.assertEqual(result_data["session_id"], self.session.session_id)
        self.assertEqual(result_data["status"], "created")
    
    def test_get_status_missing_params(self):
        """Test error when params is None."""
        result = get_session_status(None)
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])
    
    def test_get_status_invalid_params_type(self):
        """Test error when params is not a dict."""
        result = get_session_status("invalid")
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])
    
    def test_get_status_missing_session_id(self):
        """Test error when session_id missing."""
        result = get_session_status({})
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])
    
    def test_get_status_session_not_found(self):
        """Test error when session doesn't exist."""
        result = get_session_status({"session_id": "non-existent"})
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["SESSION_NOT_FOUND"])


class TestSelectMediaForSession(unittest.TestCase):
    """Test cases for select_media_for_session handler."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_session_manager()
        self.manager = get_session_manager()
        self.session = self.manager.create_session()
    
    def tearDown(self):
        """Clean up after tests."""
        reset_session_manager()
    
    def test_select_media_success(self):
        """Test successful media selection."""
        result = select_media_for_session({
            "session_id": self.session.session_id,
            "clip_id": "clip_001",
            "clip_name": "Test Clip"
        })
        
        self.assertIn("result", result)
        self.assertIsNone(result.get("error"))
        
        result_data = result["result"]
        self.assertEqual(result_data["media_clip_id"], "clip_001")
        self.assertEqual(result_data["media_clip_name"], "Test Clip")
        self.assertEqual(result_data["status"], "media_selected")
    
    def test_select_media_missing_params(self):
        """Test error when params is None."""
        result = select_media_for_session(None)
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])
    
    def test_select_media_missing_session_id(self):
        """Test error when session_id missing."""
        result = select_media_for_session({
            "clip_id": "clip_001",
            "clip_name": "Test Clip"
        })
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])
    
    def test_select_media_missing_clip_id(self):
        """Test error when clip_id missing."""
        result = select_media_for_session({
            "session_id": self.session.session_id,
            "clip_name": "Test Clip"
        })
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])
    
    def test_select_media_session_not_found(self):
        """Test error when session doesn't exist."""
        result = select_media_for_session({
            "session_id": "non-existent",
            "clip_id": "clip_001",
            "clip_name": "Test Clip"
        })
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["SESSION_NOT_FOUND"])


class TestReviewTranscriptionForSession(unittest.TestCase):
    """Test cases for review_transcription_for_session handler."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_session_manager()
        self.manager = get_session_manager()
        self.session = self.manager.create_session()
        # First select media
        self.session.select_media("clip_001", "Test Clip")
        self.manager.update_session(self.session)
    
    def tearDown(self):
        """Clean up after tests."""
        reset_session_manager()
    
    def test_review_transcription_success(self):
        """Test successful transcription review."""
        transcription_data = {
            "text": "Test transcription",
            "segments": [{"start": 0, "end": 10}]
        }
        
        result = review_transcription_for_session({
            "session_id": self.session.session_id,
            "transcription_data": transcription_data
        })
        
        self.assertIn("result", result)
        self.assertIsNone(result.get("error"))
        
        result_data = result["result"]
        self.assertEqual(result_data["status"], "transcription_reviewed")
        self.assertTrue(result_data["can_select_format"])
    
    def test_review_transcription_invalid_state(self):
        """Test error when session not in correct state."""
        # Create new session without media selection
        new_session = self.manager.create_session()
        
        result = review_transcription_for_session({
            "session_id": new_session.session_id,
            "transcription_data": {"text": "test"}
        })
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_STATE"])
    
    def test_review_transcription_missing_params(self):
        """Test error when params is None."""
        result = review_transcription_for_session(None)
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])
    
    def test_review_transcription_missing_transcription_data(self):
        """Test error when transcription_data missing."""
        result = review_transcription_for_session({
            "session_id": self.session.session_id
        })
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])


class TestPrepareRoughCutForGeneration(unittest.TestCase):
    """Test cases for prepare_rough_cut_for_generation handler."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_session_manager()
        self.manager = get_session_manager()
        self.session = self.manager.create_session()
        
        # Complete all prerequisite steps
        self.session.select_media("clip_001", "Test Clip")
        self.session.review_transcription({"text": "test transcription"})
        
        # Create a test template and select it
        from roughcut.backend.formats.models import FormatTemplate
        from pathlib import Path
        
        template = FormatTemplate(
            slug="test-template",
            name="Test Template",
            description="Test",
            file_path=Path("/test.md")
        )
        self.session.select_format(template)
        self.manager.update_session(self.session)
    
    def tearDown(self):
        """Clean up after tests."""
        reset_session_manager()
    
    def test_prepare_success(self):
        """Test successful preparation for generation."""
        result = prepare_rough_cut_for_generation({
            "session_id": self.session.session_id
        })
        
        self.assertIn("result", result)
        self.assertIsNone(result.get("error"))
        
        result_data = result["result"]
        self.assertEqual(result_data["status"], "generating")
        self.assertIn("data", result_data)
        
        # Verify data structure
        data = result_data["data"]
        self.assertIn("session_id", data)
        self.assertIn("media", data)
        self.assertIn("transcription", data)
        self.assertIn("format_template", data)
    
    def test_prepare_missing_params(self):
        """Test error when params is None."""
        result = prepare_rough_cut_for_generation(None)
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])
    
    def test_prepare_missing_session_id(self):
        """Test error when session_id missing."""
        result = prepare_rough_cut_for_generation({})
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["INVALID_PARAMS"])
    
    def test_prepare_session_not_found(self):
        """Test error when session doesn't exist."""
        result = prepare_rough_cut_for_generation({
            "session_id": "non-existent"
        })
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["SESSION_NOT_FOUND"])
    
    def test_prepare_incomplete_data(self):
        """Test error when session not ready for generation."""
        # Create incomplete session
        incomplete_session = self.manager.create_session()
        
        result = prepare_rough_cut_for_generation({
            "session_id": incomplete_session.session_id
        })
        
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["INCOMPLETE_DATA"])


if __name__ == "__main__":
    unittest.main()
