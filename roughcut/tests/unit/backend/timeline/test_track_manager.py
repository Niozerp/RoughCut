"""Unit tests for the track manager module.

Tests TrackManager functionality including:
- Standard track creation
- Track configuration
- Track verification
"""

import unittest
from unittest.mock import MagicMock

from roughcut.backend.timeline.track_manager import TrackManager
from roughcut.backend.timeline.resolve_api import ResolveApi


class TestTrackManager(unittest.TestCase):
    """Test cases for TrackManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_resolve_api = MagicMock(spec=ResolveApi)
        self.track_manager = TrackManager(self.mock_resolve_api)
        self.mock_timeline = MagicMock()
        self.mock_timeline.GetName.return_value = "TestTimeline"
    
    def test_create_standard_tracks(self):
        """Test creating the standard track layout."""
        # Setup mocks
        self.mock_resolve_api.add_track.return_value = True
        self.mock_resolve_api.get_timeline_track_count.return_value = 3
        
        result = self.track_manager.create_standard_tracks(self.mock_timeline)
        
        # Should return track counts
        self.assertIn("video", result)
        self.assertIn("audio", result)
        # Video track count (1 default + 1 vfx added)
        self.assertEqual(result["video"], 3)
        # Audio track count (1 default + 2 additional added)
        self.assertEqual(result["audio"], 3)
    
    def test_create_standard_tracks_custom_config(self):
        """Test creating tracks with custom configuration."""
        self.mock_resolve_api.add_track.return_value = True
        self.mock_resolve_api.get_timeline_track_count.return_value = 5
        
        custom_config = {
            "video": 2,
            "music": 2,
            "sfx": 3,
            "vfx": 2
        }
        
        result = self.track_manager.create_standard_tracks(
            self.mock_timeline,
            track_config=custom_config
        )
        
        # Should have created additional tracks based on config
        self.assertGreaterEqual(result["video"], 1)
        self.assertGreaterEqual(result["audio"], 1)
    
    def test_create_standard_tracks_no_additional_needed(self):
        """Test when no additional tracks need to be added."""
        self.mock_resolve_api.get_timeline_track_count.return_value = 1
        
        # Config with only 1 of each track (which Resolve creates by default)
        minimal_config = {
            "video": 1,
            "music": 1,
            "sfx": 0,
            "vfx": 0
        }
        
        result = self.track_manager.create_standard_tracks(
            self.mock_timeline,
            track_config=minimal_config
        )
        
        # add_track should not be called for video (default exists)
        # but may be called for audio depending on implementation
        self.assertIn("video", result)
    
    def test_add_video_tracks_success(self):
        """Test successful addition of video tracks."""
        self.mock_resolve_api.add_track.return_value = True
        self.mock_resolve_api.get_timeline_track_count.return_value = 3
        
        result = self.track_manager._add_video_tracks(self.mock_timeline, 2)
        
        # Should have called add_track twice
        self.assertEqual(self.mock_resolve_api.add_track.call_count, 2)
        self.assertEqual(result, 3)
    
    def test_add_video_tracks_partial_failure(self):
        """Test when some video track additions fail."""
        self.mock_resolve_api.add_track.side_effect = [True, False, True]
        self.mock_resolve_api.get_timeline_track_count.return_value = 2
        
        result = self.track_manager._add_video_tracks(self.mock_timeline, 3)
        
        # Should still return the count
        self.assertEqual(result, 2)
    
    def test_add_video_tracks_zero_count(self):
        """Test adding zero video tracks."""
        self.mock_resolve_api.get_timeline_track_count.return_value = 1
        
        result = self.track_manager._add_video_tracks(self.mock_timeline, 0)
        
        # add_track should not be called
        self.mock_resolve_api.add_track.assert_not_called()
        self.assertEqual(result, 1)
    
    def test_add_audio_tracks_success(self):
        """Test successful addition of audio tracks."""
        self.mock_resolve_api.add_track.return_value = True
        self.mock_resolve_api.get_timeline_track_count.return_value = 4
        
        result = self.track_manager._add_audio_tracks(self.mock_timeline, 3)
        
        # Should have called add_track three times
        self.assertEqual(self.mock_resolve_api.add_track.call_count, 3)
        self.assertEqual(result, 4)
    
    def test_get_track_info(self):
        """Test getting track information."""
        self.mock_resolve_api.get_timeline_track_count.side_effect = [2, 3, 1]
        
        result = self.track_manager.get_track_info(self.mock_timeline)
        
        self.assertEqual(result["video"], 2)
        self.assertEqual(result["audio"], 3)
        self.assertEqual(result["subtitle"], 1)
    
    def test_get_track_info_none_timeline(self):
        """Test getting track info with None timeline."""
        result = self.track_manager.get_track_info(None)
        
        self.assertEqual(result["video"], 0)
        self.assertEqual(result["audio"], 0)
        self.assertEqual(result["subtitle"], 0)
    
    def test_configure_track_names(self):
        """Test track name configuration (informational)."""
        result = self.track_manager.configure_track_names(self.mock_timeline)
        
        # Should return True (informational only)
        self.assertTrue(result)
    
    def test_verify_track_setup_success(self):
        """Test successful track setup verification."""
        # Standard config needs 2 video, 3 audio
        self.mock_resolve_api.get_timeline_track_count.side_effect = [2, 3]
        
        result = self.track_manager.verify_track_setup(self.mock_timeline)
        
        self.assertTrue(result)
    
    def test_verify_track_setup_video_shortfall(self):
        """Test verification when video tracks are insufficient."""
        # Want 2 video but only have 1
        self.mock_resolve_api.get_timeline_track_count.side_effect = [1, 3]
        
        result = self.track_manager.verify_track_setup(self.mock_timeline)
        
        self.assertFalse(result)
    
    def test_verify_track_setup_audio_shortfall(self):
        """Test verification when audio tracks are insufficient."""
        # Want 3 audio but only have 2
        self.mock_resolve_api.get_timeline_track_count.side_effect = [2, 2]
        
        result = self.track_manager.verify_track_setup(self.mock_timeline)
        
        self.assertFalse(result)
    
    def test_standard_tracks_constant(self):
        """Test the standard track configuration constant."""
        standard = TrackManager.STANDARD_TRACKS
        
        self.assertEqual(standard["video"], 1)
        self.assertEqual(standard["music"], 1)
        self.assertEqual(standard["sfx"], 2)
        self.assertEqual(standard["vfx"], 1)
    
    def test_track_type_constants(self):
        """Test track type constants."""
        self.assertEqual(TrackManager.TRACK_VIDEO, "video")
        self.assertEqual(TrackManager.TRACK_AUDIO, "audio")
        self.assertEqual(TrackManager.TRACK_SUBTITLE, "subtitle")


if __name__ == "__main__":
    unittest.main()
