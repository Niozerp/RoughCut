"""Unit tests for the MusicPlacer class.

Tests cover:
- Music segment validation
- Track allocation (same track vs. new track for overlapping)
- Timecode/frame conversions for fades
- Music placement logic
- Error handling scenarios
"""

import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from roughcut.backend.timeline.music_placer import (
    MusicPlacer,
    MusicPlacerResult,
    MusicPlacement,
    validate_music_segments,
    DEFAULT_FADE_IN_SECONDS,
    DEFAULT_FADE_OUT_SECONDS,
    DEFAULT_MUSIC_TRACK,
    MAX_MUSIC_TRACKS
)


class TestValidateMusicSegments(unittest.TestCase):
    """Tests for music segment validation function."""
    
    def test_valid_segments_pass(self):
        """Test that valid segments pass validation."""
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "/path/to/music.wav",
                "start_frames": 0,
                "end_frames": 900,
                "fade_in_seconds": 2.0,
                "fade_out_seconds": 2.0
            }
        ]
        
        is_valid, error = validate_music_segments(segments)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_empty_segments_fails(self):
        """Test that empty segments list fails validation."""
        segments = []
        
        is_valid, error = validate_music_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "NO_MUSIC_SEGMENTS")
    
    def test_none_segments_fails(self):
        """Test that None segments fails validation."""
        segments = None
        
        is_valid, error = validate_music_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "NO_MUSIC_SEGMENTS")
    
    def test_missing_segment_index_fails(self):
        """Test that missing segment_index fails validation."""
        segments = [
            {
                "music_file_path": "/path/to/music.wav",
                "start_frames": 0,
                "end_frames": 900
            }
        ]
        
        is_valid, error = validate_music_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "MISSING_SEGMENT_INDEX")
    
    def test_missing_file_path_fails(self):
        """Test that missing music_file_path fails validation."""
        segments = [
            {
                "segment_index": 1,
                "start_frames": 0,
                "end_frames": 900
            }
        ]
        
        is_valid, error = validate_music_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "MISSING_MUSIC_FILE_PATH")
    
    def test_missing_frame_data_fails(self):
        """Test that missing frame data fails validation."""
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "/path/to/music.wav"
            }
        ]
        
        is_valid, error = validate_music_segments(segments)
        self.assertFalse(is_valid)
        self.assertIn("MISSING", error["code"])
    
    def test_negative_start_frame_fails(self):
        """Test that negative start frame fails validation."""
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "/path/to/music.wav",
                "start_frames": -100,
                "end_frames": 900
            }
        ]
        
        is_valid, error = validate_music_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "NEGATIVE_START_FRAME")
    
    def test_start_greater_than_end_fails(self):
        """Test that start >= end fails validation."""
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "/path/to/music.wav",
                "start_frames": 900,
                "end_frames": 100
            }
        ]
        
        is_valid, error = validate_music_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "INVALID_SEGMENT_RANGE")
    
    def test_duplicate_segment_index_fails(self):
        """Test that duplicate segment_index fails validation."""
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "/path/to/music1.wav",
                "start_frames": 0,
                "end_frames": 900
            },
            {
                "segment_index": 1,  # Duplicate
                "music_file_path": "/path/to/music2.wav",
                "start_frames": 900,
                "end_frames": 1800
            }
        ]
        
        is_valid, error = validate_music_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "DUPLICATE_INDEX")
    
    def test_relative_path_fails(self):
        """Test that relative file paths fail validation."""
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "relative/path/to/music.wav",
                "start_frames": 0,
                "end_frames": 900
            }
        ]
        
        is_valid, error = validate_music_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "RELATIVE_FILE_PATH")
    
    def test_empty_file_path_fails(self):
        """Test that empty file path fails validation."""
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "",
                "start_frames": 0,
                "end_frames": 900
            }
        ]
        
        is_valid, error = validate_music_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "EMPTY_FILE_PATH")
    
    def test_invalid_track_number_fails(self):
        """Test that track number < 2 fails validation."""
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "/path/to/music.wav",
                "start_frames": 0,
                "end_frames": 900,
                "track_number": 1  # Invalid - should be >= 2
            }
        ]
        
        is_valid, error = validate_music_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "INVALID_TRACK_NUMBER")
    
    def test_invalid_fade_in_fails(self):
        """Test that negative fade_in_seconds fails validation."""
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "/path/to/music.wav",
                "start_frames": 0,
                "end_frames": 900,
                "fade_in_seconds": -1.0
            }
        ]
        
        is_valid, error = validate_music_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "INVALID_FADE_IN")
    
    def test_non_integer_frames_fails(self):
        """Test that non-integer frames fail validation."""
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "/path/to/music.wav",
                "start_frames": 0.5,  # Float instead of int
                "end_frames": 900
            }
        ]
        
        is_valid, error = validate_music_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "NON_INTEGER_FRAMES")
    
    def test_segment_not_dict_fails(self):
        """Test that non-dictionary segments fail validation."""
        segments = ["not a dict"]
        
        is_valid, error = validate_music_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "INVALID_SEGMENT_TYPE")
    
    def test_multiple_valid_segments_pass(self):
        """Test that multiple valid segments pass validation."""
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "/path/to/intro.wav",
                "start_frames": 0,
                "end_frames": 900,
                "section_type": "intro"
            },
            {
                "segment_index": 2,
                "music_file_path": "/path/to/bed.wav",
                "start_frames": 900,
                "end_frames": 8100,
                "section_type": "bed"
            },
            {
                "segment_index": 3,
                "music_file_path": "/path/to/outro.wav",
                "start_frames": 8100,
                "end_frames": 9450,
                "section_type": "outro"
            }
        ]
        
        is_valid, error = validate_music_segments(segments)
        self.assertTrue(is_valid)
        self.assertIsNone(error)


class TestMusicPlacementDataclass(unittest.TestCase):
    """Tests for MusicPlacement dataclass."""
    
    def test_music_placement_creation(self):
        """Test creating a MusicPlacement instance."""
        placement = MusicPlacement(
            segment_index=1,
            track_number=2,
            timeline_start_frame=0,
            timeline_end_frame=900,
            music_file_path="/path/to/music.wav",
            clip_id="clip_001",
            fade_in_frames=60,
            fade_out_frames=60,
            section_type="intro"
        )
        
        self.assertEqual(placement.segment_index, 1)
        self.assertEqual(placement.track_number, 2)
        self.assertEqual(placement.timeline_start_frame, 0)
        self.assertEqual(placement.timeline_end_frame, 900)
        self.assertEqual(placement.music_file_path, "/path/to/music.wav")
        self.assertEqual(placement.clip_id, "clip_001")
        self.assertEqual(placement.fade_in_frames, 60)
        self.assertEqual(placement.fade_out_frames, 60)
        self.assertEqual(placement.section_type, "intro")
    
    def test_music_placement_defaults(self):
        """Test MusicPlacement default values."""
        placement = MusicPlacement(
            segment_index=1,
            track_number=2,
            timeline_start_frame=0,
            timeline_end_frame=900,
            music_file_path="/path/to/music.wav"
        )
        
        self.assertIsNone(placement.clip_id)
        self.assertEqual(placement.fade_in_frames, 0)
        self.assertEqual(placement.fade_out_frames, 0)
        self.assertEqual(placement.section_type, "bed")


class TestMusicPlacerResult(unittest.TestCase):
    """Tests for MusicPlacerResult dataclass."""
    
    def test_result_creation(self):
        """Test creating a MusicPlacerResult instance."""
        placements = [
            MusicPlacement(
                segment_index=1,
                track_number=2,
                timeline_start_frame=0,
                timeline_end_frame=900,
                music_file_path="/path/to/music.wav"
            )
        ]
        
        result = MusicPlacerResult(
            clips_placed=1,
            tracks_used=[2],
            total_duration_frames=900,
            timeline_positions=placements
        )
        
        self.assertEqual(result.clips_placed, 1)
        self.assertEqual(result.tracks_used, [2])
        self.assertEqual(result.total_duration_frames, 900)
        self.assertEqual(len(result.timeline_positions), 1)
        self.assertTrue(result.success)
        self.assertIsNone(result.error)
    
    def test_total_duration_timecode_property(self):
        """Test the total_duration_timecode property."""
        result = MusicPlacerResult(
            clips_placed=1,
            tracks_used=[2],
            total_duration_frames=900,  # 30 seconds at 30fps
            timeline_positions=[]
        )
        
        # 900 frames at 30fps = 30 seconds = 0:30
        self.assertEqual(result.total_duration_timecode, "0:30")
    
    def test_get_total_duration_timecode_with_custom_fps(self):
        """Test get_total_duration_timecode with custom fps."""
        result = MusicPlacerResult(
            clips_placed=1,
            tracks_used=[2],
            total_duration_frames=720,  # 24 seconds at 30fps, but using 24fps
            timeline_positions=[],
            fps=24
        )
        
        # 720 frames at 24fps = 30 seconds = 0:30
        self.assertEqual(result.get_total_duration_timecode(), "0:30")
        
        # Test with explicit fps parameter
        self.assertEqual(result.get_total_duration_timecode(fps=30), "0:24")  # 720/30 = 24 seconds
    
    def test_result_with_error(self):
        """Test creating a result with an error."""
        result = MusicPlacerResult(
            clips_placed=0,
            tracks_used=[],
            total_duration_frames=0,
            timeline_positions=[],
            success=False,
            error={
                "code": "TEST_ERROR",
                "message": "Test error message"
            }
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "TEST_ERROR")


class TestMusicPlacerInit(unittest.TestCase):
    """Tests for MusicPlacer initialization."""
    
    def test_default_init(self):
        """Test default initialization creates ResolveApi."""
        placer = MusicPlacer()
        self.assertIsNotNone(placer.resolve_api)
    
    def test_init_with_custom_api(self):
        """Test initialization with custom ResolveApi."""
        mock_api = MagicMock()
        placer = MusicPlacer(resolve_api=mock_api)
        self.assertEqual(placer.resolve_api, mock_api)


class TestSecondsToFrames(unittest.TestCase):
    """Tests for seconds to frames conversion."""
    
    def test_seconds_to_frames_default_fps(self):
        """Test conversion with default 30fps."""
        placer = MusicPlacer()
        frames = placer._seconds_to_frames(2.0)
        self.assertEqual(frames, 60)  # 2 seconds * 30fps
    
    def test_seconds_to_frames_custom_fps(self):
        """Test conversion with custom fps."""
        placer = MusicPlacer()
        frames = placer._seconds_to_frames(2.0, fps=24)
        self.assertEqual(frames, 48)  # 2 seconds * 24fps
    
    def test_seconds_to_frames_zero(self):
        """Test conversion of zero seconds."""
        placer = MusicPlacer()
        frames = placer._seconds_to_frames(0.0)
        self.assertEqual(frames, 0)
    
    def test_seconds_to_frames_fractional(self):
        """Test conversion of fractional seconds."""
        placer = MusicPlacer()
        frames = placer._seconds_to_frames(1.5)  # 1.5 seconds
        self.assertEqual(frames, 45)  # 1.5 * 30 = 45


class TestTrackConflict(unittest.TestCase):
    """Tests for track conflict detection."""
    
    def test_no_conflict_empty_placements(self):
        """Test no conflict with empty placements."""
        placer = MusicPlacer()
        existing = []
        
        conflict = placer._check_track_conflict(2, 0, 900, existing)
        self.assertFalse(conflict)
    
    def test_no_conflict_different_track(self):
        """Test no conflict when placements are on different tracks."""
        placer = MusicPlacer()
        existing = [
            MusicPlacement(
                segment_index=1,
                track_number=3,  # Different track
                timeline_start_frame=0,
                timeline_end_frame=900,
                music_file_path="/path/to/music.wav"
            )
        ]
        
        conflict = placer._check_track_conflict(2, 0, 900, existing)
        self.assertFalse(conflict)
    
    def test_no_conflict_non_overlapping(self):
        """Test no conflict with non-overlapping segments."""
        placer = MusicPlacer()
        existing = [
            MusicPlacement(
                segment_index=1,
                track_number=2,
                timeline_start_frame=0,
                timeline_end_frame=900,
                music_file_path="/path/to/music1.wav"
            )
        ]
        
        # New segment starts after existing ends
        conflict = placer._check_track_conflict(2, 900, 1800, existing)
        self.assertFalse(conflict)
    
    def test_conflict_overlapping(self):
        """Test conflict with overlapping segments."""
        placer = MusicPlacer()
        existing = [
            MusicPlacement(
                segment_index=1,
                track_number=2,
                timeline_start_frame=0,
                timeline_end_frame=900,
                music_file_path="/path/to/music1.wav"
            )
        ]
        
        # New segment overlaps with existing
        conflict = placer._check_track_conflict(2, 450, 1350, existing)
        self.assertTrue(conflict)
    
    def test_conflict_exact_overlap(self):
        """Test conflict with exact same position."""
        placer = MusicPlacer()
        existing = [
            MusicPlacement(
                segment_index=1,
                track_number=2,
                timeline_start_frame=0,
                timeline_end_frame=900,
                music_file_path="/path/to/music1.wav"
            )
        ]
        
        conflict = placer._check_track_conflict(2, 0, 900, existing)
        self.assertTrue(conflict)


class TestAllocateMusicTrack(unittest.TestCase):
    """Tests for track allocation logic."""
    
    def test_allocate_preferred_track_when_clear(self):
        """Test allocation of preferred track when it's clear."""
        placer = MusicPlacer()
        existing = []
        
        track = placer._allocate_music_track(2, 0, 900, existing)
        self.assertEqual(track, 2)
    
    def test_allocate_alternate_track_when_preferred_occupied(self):
        """Test allocation of alternate track when preferred is occupied."""
        placer = MusicPlacer()
        existing = [
            MusicPlacement(
                segment_index=1,
                track_number=2,
                timeline_start_frame=0,
                timeline_end_frame=900,
                music_file_path="/path/to/music1.wav"
            )
        ]
        
        # Overlapping segment should get track 3
        track = placer._allocate_music_track(2, 100, 500, existing)
        self.assertEqual(track, 3)
    
    def test_allocate_higher_track_when_multiple_occupied(self):
        """Test allocation finds first available track."""
        placer = MusicPlacer()
        existing = [
            MusicPlacement(
                segment_index=1,
                track_number=2,
                timeline_start_frame=0,
                timeline_end_frame=900,
                music_file_path="/path/to/music1.wav"
            ),
            MusicPlacement(
                segment_index=2,
                track_number=3,
                timeline_start_frame=0,
                timeline_end_frame=900,
                music_file_path="/path/to/music2.wav"
            )
        ]
        
        # Should get track 4
        track = placer._allocate_music_track(2, 100, 500, existing)
        self.assertEqual(track, 4)
    
    def test_same_track_non_overlapping(self):
        """Test same track can be reused for non-overlapping segments."""
        placer = MusicPlacer()
        existing = [
            MusicPlacement(
                segment_index=1,
                track_number=2,
                timeline_start_frame=0,
                timeline_end_frame=900,
                music_file_path="/path/to/music1.wav"
            )
        ]
        
        # Non-overlapping can reuse track 2
        track = placer._allocate_music_track(2, 900, 1800, existing)
        self.assertEqual(track, 2)


class TestGenerateStableClipId(unittest.TestCase):
    """Tests for stable clip ID generation."""
    
    def test_deterministic_id(self):
        """Test that IDs are deterministic (same inputs = same output)."""
        placer = MusicPlacer()
        mock_clip = MagicMock()
        mock_clip.GetName.return_value = "test_music.wav"
        
        id1 = placer._generate_stable_clip_id(mock_clip, 100, 0, 900)
        id2 = placer._generate_stable_clip_id(mock_clip, 100, 0, 900)
        
        self.assertEqual(id1, id2)
    
    def test_different_inputs_different_ids(self):
        """Test that different inputs produce different IDs."""
        placer = MusicPlacer()
        mock_clip = MagicMock()
        mock_clip.GetName.return_value = "test_music.wav"
        
        id1 = placer._generate_stable_clip_id(mock_clip, 100, 0, 900)
        id2 = placer._generate_stable_clip_id(mock_clip, 100, 0, 1000)  # Different source_out
        
        self.assertNotEqual(id1, id2)
    
    def test_id_length(self):
        """Test that ID is truncated to 16 characters."""
        placer = MusicPlacer()
        mock_clip = MagicMock()
        mock_clip.GetName.return_value = "a_very_long_music_file_name_that_is_definitely_longer.wav"
        
        clip_id = placer._generate_stable_clip_id(mock_clip, 100, 0, 900)
        self.assertEqual(len(clip_id), 16)


class TestPlaceMusicClips(unittest.TestCase):
    """Integration tests for place_music_clips method."""
    
    @patch('roughcut.backend.timeline.music_placer.ResolveApi')
    def test_place_music_success(self, mock_resolve_api_class):
        """Test successful music placement."""
        # Setup mocks
        mock_api = MagicMock()
        mock_api.is_available.return_value = True
        
        mock_timeline = MagicMock()
        mock_timeline.AddClip.return_value = MagicMock(GetName=lambda: "music_clip_001")
        mock_api.find_timeline_by_name.return_value = mock_timeline
        
        mock_media_pool = MagicMock()
        mock_root_folder = MagicMock()
        mock_root_folder.GetClipList.return_value = []
        mock_media_pool.GetRootFolder.return_value = mock_root_folder
        mock_media_pool.ImportMedia.return_value = [MagicMock(GetName=lambda: "test_music.wav")]
        mock_api.get_media_pool.return_value = mock_media_pool
        
        mock_resolve_api_class.return_value = mock_api
        
        # Create placer with mocked API
        placer = MusicPlacer(resolve_api=mock_api)
        
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "/path/to/test_music.wav",
                "start_frames": 0,
                "end_frames": 900,
                "fade_in_seconds": 2.0,
                "fade_out_seconds": 2.0,
                "section_type": "intro"
            }
        ]
        
        result = placer.place_music_clips("timeline_001", segments)
        
        self.assertTrue(result.success)
        self.assertEqual(result.clips_placed, 1)
        self.assertEqual(result.total_duration_frames, 900)
        self.assertEqual(result.tracks_used, [2])
    
    @patch('roughcut.backend.timeline.music_placer.ResolveApi')
    def test_place_music_resolve_not_available(self, mock_resolve_api_class):
        """Test error when Resolve API is not available."""
        mock_api = MagicMock()
        mock_api.is_available.return_value = False
        mock_resolve_api_class.return_value = mock_api
        
        placer = MusicPlacer(resolve_api=mock_api)
        
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "/path/to/test_music.wav",
                "start_frames": 0,
                "end_frames": 900
            }
        ]
        
        result = placer.place_music_clips("timeline_001", segments)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "RESOLVE_API_UNAVAILABLE")
    
    @patch('roughcut.backend.timeline.music_placer.ResolveApi')
    def test_place_music_timeline_not_found(self, mock_resolve_api_class):
        """Test error when timeline is not found."""
        mock_api = MagicMock()
        mock_api.is_available.return_value = True
        mock_api.find_timeline_by_name.return_value = None
        mock_resolve_api_class.return_value = mock_api
        
        placer = MusicPlacer(resolve_api=mock_api)
        
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "/path/to/test_music.wav",
                "start_frames": 0,
                "end_frames": 900
            }
        ]
        
        result = placer.place_music_clips("timeline_001", segments)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "TIMELINE_NOT_FOUND")
    
    @patch('roughcut.backend.timeline.music_placer.ResolveApi')
    def test_place_music_import_failure(self, mock_resolve_api_class):
        """Test handling when music import fails (continues with other segments)."""
        mock_api = MagicMock()
        mock_api.is_available.return_value = True
        
        mock_timeline = MagicMock()
        mock_api.find_timeline_by_name.return_value = mock_timeline
        
        # Import returns None (failure)
        mock_media_pool = MagicMock()
        mock_root_folder = MagicMock()
        mock_root_folder.GetClipList.return_value = []
        mock_media_pool.GetRootFolder.return_value = mock_root_folder
        mock_media_pool.ImportMedia.return_value = None
        mock_api.get_media_pool.return_value = mock_media_pool
        
        mock_resolve_api_class.return_value = mock_api
        
        placer = MusicPlacer(resolve_api=mock_api)
        
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "/path/to/test_music.wav",
                "start_frames": 0,
                "end_frames": 900
            }
        ]
        
        result = placer.place_music_clips("timeline_001", segments)
        
        # Should not fail entirely, but place 0 clips
        self.assertFalse(result.success)
        self.assertEqual(result.clips_placed, 0)
    
    @patch('roughcut.backend.timeline.music_placer.ResolveApi')
    def test_place_multiple_clips(self, mock_resolve_api_class):
        """Test placing multiple music clips."""
        mock_api = MagicMock()
        mock_api.is_available.return_value = True
        
        mock_timeline = MagicMock()
        mock_timeline.AddClip.return_value = MagicMock(GetName=lambda: "music_clip")
        mock_api.find_timeline_by_name.return_value = mock_timeline
        
        mock_media_pool = MagicMock()
        mock_root_folder = MagicMock()
        mock_root_folder.GetClipList.return_value = []
        mock_media_pool.GetRootFolder.return_value = mock_root_folder
        mock_media_pool.ImportMedia.return_value = [MagicMock(GetName=lambda: "music.wav")]
        mock_api.get_media_pool.return_value = mock_media_pool
        
        mock_resolve_api_class.return_value = mock_api
        
        placer = MusicPlacer(resolve_api=mock_api)
        
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "/path/to/intro.wav",
                "start_frames": 0,
                "end_frames": 900,
                "section_type": "intro"
            },
            {
                "segment_index": 2,
                "music_file_path": "/path/to/bed.wav",
                "start_frames": 900,
                "end_frames": 8100,
                "section_type": "bed"
            },
            {
                "segment_index": 3,
                "music_file_path": "/path/to/outro.wav",
                "start_frames": 8100,
                "end_frames": 9450,
                "section_type": "outro"
            }
        ]
        
        result = placer.place_music_clips("timeline_001", segments)
        
        self.assertTrue(result.success)
        self.assertEqual(result.clips_placed, 3)
        self.assertEqual(result.total_duration_frames, 9450)
    
    def test_place_music_empty_segments(self):
        """Test handling empty segments list."""
        mock_api = MagicMock()
        placer = MusicPlacer(resolve_api=mock_api)
        
        result = placer.place_music_clips("timeline_001", [])
        
        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "NO_MUSIC_SEGMENTS")


class TestProgressCallback(unittest.TestCase):
    """Tests for progress callback functionality."""
    
    @patch('roughcut.backend.timeline.music_placer.ResolveApi')
    def test_progress_callback_called(self, mock_resolve_api_class):
        """Test that progress callback is called for each segment."""
        mock_api = MagicMock()
        mock_api.is_available.return_value = True
        
        mock_timeline = MagicMock()
        mock_timeline.AddClip.return_value = MagicMock(GetName=lambda: "clip")
        mock_api.find_timeline_by_name.return_value = mock_timeline
        
        mock_media_pool = MagicMock()
        mock_root_folder = MagicMock()
        mock_root_folder.GetClipList.return_value = []
        mock_media_pool.GetRootFolder.return_value = mock_root_folder
        mock_media_pool.ImportMedia.return_value = [MagicMock(GetName=lambda: "music.wav")]
        mock_api.get_media_pool.return_value = mock_media_pool
        
        mock_resolve_api_class.return_value = mock_api
        
        placer = MusicPlacer(resolve_api=mock_api)
        
        progress_calls = []
        
        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))
        
        segments = [
            {
                "segment_index": 1,
                "music_file_path": "/path/to/music1.wav",
                "start_frames": 0,
                "end_frames": 900
            },
            {
                "segment_index": 2,
                "music_file_path": "/path/to/music2.wav",
                "start_frames": 900,
                "end_frames": 1800
            }
        ]
        
        placer.place_music_clips("timeline_001", segments, progress_callback)
        
        self.assertEqual(len(progress_calls), 2)
        self.assertEqual(progress_calls[0][0], 1)  # First call: current=1
        self.assertEqual(progress_calls[0][1], 2)  # First call: total=2
        self.assertEqual(progress_calls[1][0], 2)  # Second call: current=2


if __name__ == '__main__':
    unittest.main()
