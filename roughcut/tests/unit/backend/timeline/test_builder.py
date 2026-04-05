"""Unit tests for the timeline builder module.

Tests TimelineBuilder functionality including:
- Timeline name generation
- Non-destructive creation
- Error handling
"""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from roughcut.backend.timeline.builder import TimelineBuilder, TimelineCreationResult
from roughcut.backend.timeline.resolve_api import ResolveApi


class TestTimelineBuilder(unittest.TestCase):
    """Test cases for TimelineBuilder."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_resolve_api = MagicMock(spec=ResolveApi)
        self.builder = TimelineBuilder(resolve_api=self.mock_resolve_api)
    
    def test_generate_timeline_name_basic(self):
        """Test basic timeline name generation."""
        name = self.builder._generate_timeline_name(
            source_clip_name="interview_001",
            format_template="youtube-interview"
        )
        
        # Should start with prefix
        self.assertTrue(name.startswith("RoughCut_"))
        # Should contain source clip
        self.assertIn("interview_001", name)
        # Should contain format
        self.assertIn("youtube-interview", name)
        # Should contain timestamp
        self.assertRegex(name, r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")
    
    def test_generate_timeline_name_with_timestamp(self):
        """Test timeline name generation with explicit timestamp."""
        name = self.builder._generate_timeline_name(
            source_clip_name="clip",
            format_template="format",
            timestamp="2026-04-04T12:30:00"
        )
        
        self.assertIn("2026-04-04_12-30-00", name)
    
    def test_generate_timeline_name_with_extension(self):
        """Test that file extensions are removed from source clip."""
        name = self.builder._generate_timeline_name(
            source_clip_name="video.mp4",
            format_template="format"
        )
        
        # Should not contain the extension
        self.assertNotIn(".mp4", name)
        self.assertIn("video", name)
    
    def test_generate_timeline_name_sanitization(self):
        """Test special character sanitization in names."""
        name = self.builder._generate_timeline_name(
            source_clip_name="my clip @ #1",
            format_template="test format!"
        )
        
        # Should not contain special characters (converted to underscores)
        self.assertNotIn("@", name)
        self.assertNotIn("!", name)
        # Multiple spaces/special chars should be collapsed
        self.assertNotIn("__", name)
    
    def test_generate_timeline_name_length_limit(self):
        """Test that very long names are truncated."""
        long_name = "a" * 100
        name = self.builder._generate_timeline_name(
            source_clip_name=long_name,
            format_template=long_name
        )
        
        # Should be under the max length
        self.assertLessEqual(len(name), self.builder.MAX_NAME_LENGTH)
    
    def test_sanitize_name_empty(self):
        """Test sanitization of empty name."""
        result = self.builder._sanitize_name("")
        self.assertEqual(result, "Untitled")
    
    def test_sanitize_name_none(self):
        """Test sanitization of None name."""
        result = self.builder._sanitize_name(None)
        self.assertEqual(result, "Untitled")
    
    def test_sanitize_name_special_chars(self):
        """Test removal of special characters."""
        result = self.builder._sanitize_name("test@#$%^&*()file")
        self.assertEqual(result, "test_file")
    
    def test_sanitize_name_multiple_underscores(self):
        """Test collapsing multiple underscores."""
        result = self.builder._sanitize_name("test___file")
        self.assertEqual(result, "test_file")
    
    def test_generate_unique_timeline_name(self):
        """Test unique name generation when conflicts exist."""
        # Mock that timeline already exists
        self.mock_resolve_api.find_timeline_by_name.side_effect = [
            True,   # "Test" exists
            True,   # "Test_001" exists
            False   # "Test_002" doesn't exist
        ]
        
        result = self.builder._generate_unique_timeline_name("Test")
        
        self.assertEqual(result, "Test_002")
    
    def test_create_timeline_resolve_unavailable(self):
        """Test creation when Resolve API is unavailable."""
        self.mock_resolve_api.is_available.return_value = False
        
        result = self.builder.create_timeline(
            source_clip_name="test",
            format_template="format"
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "RESOLVE_API_UNAVAILABLE")
        self.assertTrue(result.error["recoverable"])
    
    def test_create_timeline_success(self):
        """Test successful timeline creation."""
        # Setup mocks
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = None
        
        mock_timeline = MagicMock()
        mock_timeline.GetUniqueId.return_value = "timeline_123"
        self.mock_resolve_api.create_timeline.return_value = mock_timeline
        self.mock_resolve_api.set_current_timeline.return_value = True
        
        # Mock track manager
        with patch.object(self.builder.track_manager, 'create_standard_tracks') as mock_tracks:
            mock_tracks.return_value = {"video": 2, "audio": 3}
            
            with patch.object(self.builder.track_manager, 'verify_track_setup') as mock_verify:
                mock_verify.return_value = True
                
                result = self.builder.create_timeline(
                    source_clip_name="test",
                    format_template="format"
                )
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.timeline_name)
        self.assertEqual(result.timeline_id, "timeline_123")
        self.assertEqual(result.tracks_created, {"video": 2, "audio": 3})
    
    def test_create_timeline_existing_name(self):
        """Test creation when timeline name already exists."""
        self.mock_resolve_api.is_available.return_value = True
        # First call finds existing, subsequent calls don't
        self.mock_resolve_api.find_timeline_by_name.side_effect = [
            True,   # First name exists
            None    # Unique name doesn't exist
        ]
        
        mock_timeline = MagicMock()
        self.mock_resolve_api.create_timeline.return_value = mock_timeline
        self.mock_resolve_api.set_current_timeline.return_value = True
        
        with patch.object(self.builder.track_manager, 'create_standard_tracks'):
            with patch.object(self.builder.track_manager, 'verify_track_setup'):
                result = self.builder.create_timeline(
                    source_clip_name="test",
                    format_template="format"
                )
        
        self.assertTrue(result.success)
        # Name should be modified to be unique
        self.assertRegex(result.timeline_name, r"_\d{3}_")
    
    def test_create_timeline_creation_failure(self):
        """Test when timeline creation fails."""
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = None
        self.mock_resolve_api.create_timeline.return_value = None
        
        result = self.builder.create_timeline(
            source_clip_name="test",
            format_template="format"
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "TIMELINE_CREATION_FAILED")
    
    def test_create_timeline_exception_handling(self):
        """Test handling of unexpected exceptions."""
        self.mock_resolve_api.is_available.side_effect = Exception("Unexpected error")
        
        result = self.builder.create_timeline(
            source_clip_name="test",
            format_template="format"
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "INTERNAL_ERROR")


class TestTimelineCreationResult(unittest.TestCase):
    """Test cases for TimelineCreationResult dataclass."""
    
    def test_default_values(self):
        """Test default values of result."""
        result = TimelineCreationResult(timeline_name="Test")
        
        self.assertEqual(result.timeline_name, "Test")
        self.assertIsNone(result.timeline_id)
        self.assertEqual(result.tracks_created, {})
        self.assertTrue(result.success)
        self.assertIsNone(result.error)
    
    def test_error_result(self):
        """Test error result."""
        result = TimelineCreationResult(
            timeline_name="Test",
            success=False,
            error={
                "code": "ERROR",
                "message": "Test error"
            }
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "ERROR")


if __name__ == "__main__":
    unittest.main()
