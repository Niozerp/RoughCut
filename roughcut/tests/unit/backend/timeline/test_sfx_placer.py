"""Unit tests for the SfxPlacer class.

Tests cover:
- SFX segment validation
- Track allocation (3-10 range, conflict detection)
- Timecode/frame conversions for fades and handles
- Volume level management
- SFX placement logic
- Error handling scenarios
"""

import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os
import tempfile

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from roughcut.backend.timeline.sfx_placer import (
    SfxPlacer,
    SfxPlacerResult,
    SfxPlacement,
    validate_sfx_segments,
    TrackAllocationError,
    DEFAULT_SFX_FADE_IN_SECONDS,
    DEFAULT_SFX_FADE_OUT_SECONDS,
    DEFAULT_SFX_VOLUME_DB,
    SFX_TRACK_START,
    SFX_TRACK_END,
    MAX_SFX_TRACKS,
    DEFAULT_HANDLE_SECONDS
)


class TestValidateSfxSegments(unittest.TestCase):
    """Tests for SFX segment validation function."""
    
    def setUp(self):
        """Create temporary files for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test_sfx.wav")
        # Create an empty file to simulate existing SFX file
        with open(self.test_file, 'w') as f:
            f.write("")
    
    def tearDown(self):
        """Clean up temporary files."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        os.rmdir(self.temp_dir)
    
    def test_valid_segments_pass(self):
        """Test that valid segments pass validation."""
        segments = [
            {
                "segment_index": 1,
                "sfx_file_path": self.test_file,
                "start_frames": 0,
                "end_frames": 90,
                "fade_in_seconds": 1.0,
                "fade_out_seconds": 1.0,
                "volume_db": -12.0
            }
        ]
        
        is_valid, error = validate_sfx_segments(segments)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_empty_segments_fails(self):
        """Test that empty segments list fails validation."""
        segments = []
        
        is_valid, error = validate_sfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "NO_SFX_SEGMENTS")
    
    def test_missing_segment_index_fails(self):
        """Test that missing segment_index fails validation."""
        segments = [
            {
                "sfx_file_path": self.test_file,
                "start_frames": 0,
                "end_frames": 90
            }
        ]
        
        is_valid, error = validate_sfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "MISSING_SEGMENT_INDEX")
    
    def test_missing_file_path_fails(self):
        """Test that missing sfx_file_path fails validation."""
        segments = [
            {
                "segment_index": 1,
                "start_frames": 0,
                "end_frames": 90
            }
        ]
        
        is_valid, error = validate_sfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "MISSING_SFX_FILE_PATH")
    
    def test_file_not_found_fails(self):
        """Test that non-existent file fails validation."""
        segments = [
            {
                "segment_index": 1,
                "sfx_file_path": "/nonexistent/path/sfx.wav",
                "start_frames": 0,
                "end_frames": 90
            }
        ]
        
        is_valid, error = validate_sfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "SFX_FILE_NOT_FOUND")
    
    def test_relative_path_fails(self):
        """Test that relative path fails validation."""
        segments = [
            {
                "segment_index": 1,
                "sfx_file_path": "relative/path/sfx.wav",
                "start_frames": 0,
                "end_frames": 90
            }
        ]
        
        is_valid, error = validate_sfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "RELATIVE_FILE_PATH")
    
    def test_invalid_track_number_fails(self):
        """Test that invalid track number (outside 3-10) fails validation."""
        segments = [
            {
                "segment_index": 1,
                "sfx_file_path": self.test_file,
                "start_frames": 0,
                "end_frames": 90,
                "track_number": 2  # Invalid - should be 3-10
            }
        ]
        
        is_valid, error = validate_sfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "INVALID_TRACK_NUMBER")
    
    def test_track_number_3_to_10_valid(self):
        """Test that track numbers 3-10 are valid."""
        for track in range(3, 11):
            segments = [
                {
                    "segment_index": 1,
                    "sfx_file_path": self.test_file,
                    "start_frames": 0,
                    "end_frames": 90,
                    "track_number": track
                }
            ]
            
            is_valid, error = validate_sfx_segments(segments)
            self.assertTrue(is_valid, f"Track {track} should be valid")
    
    def test_invalid_volume_type_fails(self):
        """Test that non-numeric volume fails validation."""
        segments = [
            {
                "segment_index": 1,
                "sfx_file_path": self.test_file,
                "start_frames": 0,
                "end_frames": 90,
                "volume_db": "invalid"
            }
        ]
        
        is_valid, error = validate_sfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "INVALID_VOLUME_TYPE")
    
    def test_invalid_fade_in_fails(self):
        """Test that negative fade_in_seconds fails validation."""
        segments = [
            {
                "segment_index": 1,
                "sfx_file_path": self.test_file,
                "start_frames": 0,
                "end_frames": 90,
                "fade_in_seconds": -1.0
            }
        ]
        
        is_valid, error = validate_sfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "INVALID_FADE_IN")
    
    def test_invalid_segment_range_fails(self):
        """Test that start >= end frames fails validation."""
        segments = [
            {
                "segment_index": 1,
                "sfx_file_path": self.test_file,
                "start_frames": 100,
                "end_frames": 50
            }
        ]
        
        is_valid, error = validate_sfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "INVALID_SEGMENT_RANGE")
    
    def test_duplicate_segment_index_fails(self):
        """Test that duplicate segment_index fails validation."""
        segments = [
            {
                "segment_index": 1,
                "sfx_file_path": self.test_file,
                "start_frames": 0,
                "end_frames": 90
            },
            {
                "segment_index": 1,  # Duplicate
                "sfx_file_path": self.test_file,
                "start_frames": 100,
                "end_frames": 190
            }
        ]
        
        is_valid, error = validate_sfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "DUPLICATE_INDEX")


class TestSfxPlacementDataclass(unittest.TestCase):
    """Tests for SfxPlacement dataclass."""
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        placement = SfxPlacement(
            segment_index=1,
            track_number=3,
            timeline_start_frame=0,
            timeline_end_frame=90,
            sfx_file_path="/path/to/sfx.wav"
        )
        
        self.assertEqual(placement.segment_index, 1)
        self.assertEqual(placement.track_number, 3)
        self.assertEqual(placement.timeline_start_frame, 0)
        self.assertEqual(placement.timeline_end_frame, 90)
        self.assertEqual(placement.sfx_file_path, "/path/to/sfx.wav")
        self.assertIsNone(placement.clip_id)
        self.assertEqual(placement.fade_in_frames, 0)
        self.assertEqual(placement.fade_out_frames, 0)
        self.assertEqual(placement.volume_db, DEFAULT_SFX_VOLUME_DB)
        self.assertEqual(placement.moment_type, "generic")
        self.assertEqual(placement.handle_frames, 0)
    
    def test_custom_values(self):
        """Test that custom values can be set."""
        placement = SfxPlacement(
            segment_index=2,
            track_number=4,
            timeline_start_frame=100,
            timeline_end_frame=200,
            sfx_file_path="/path/to/whoosh.wav",
            clip_id="sfx_123",
            fade_in_frames=15,
            fade_out_frames=30,
            volume_db=-10.0,
            moment_type="intro_whoosh",
            handle_frames=60
        )
        
        self.assertEqual(placement.clip_id, "sfx_123")
        self.assertEqual(placement.fade_in_frames, 15)
        self.assertEqual(placement.volume_db, -10.0)
        self.assertEqual(placement.moment_type, "intro_whoosh")


class TestSfxPlacerResult(unittest.TestCase):
    """Tests for SfxPlacerResult dataclass."""
    
    def test_default_fps(self):
        """Test that default FPS is 30."""
        result = SfxPlacerResult(
            clips_placed=3,
            tracks_used=[3, 4],
            total_duration_frames=900,
            timeline_positions=[]
        )
        
        self.assertEqual(result.fps, 30)
    
    def test_total_duration_timecode(self):
        """Test timecode conversion for total duration."""
        # 900 frames at 30fps = 30 seconds = 0:00:30
        result = SfxPlacerResult(
            clips_placed=1,
            tracks_used=[3],
            total_duration_frames=900,
            timeline_positions=[],
            fps=30
        )
        
        self.assertEqual(result.total_duration_timecode, "0:00:30")
    
    def test_custom_fps_timecode(self):
        """Test timecode conversion with custom FPS."""
        # 60 frames at 24fps = 2.5 seconds = 0:00:02 (truncated)
        result = SfxPlacerResult(
            clips_placed=1,
            tracks_used=[3],
            total_duration_frames=60,
            timeline_positions=[],
            fps=24
        )
        
        self.assertEqual(result.get_total_duration_timecode(fps=24), "0:00:02")


class TestSfxPlacerSecondsToFrames(unittest.TestCase):
    """Tests for _seconds_to_frames conversion."""
    
    def test_default_fps(self):
        """Test conversion with default 30fps."""
        placer = SfxPlacer()
        
        # 1 second at 30fps = 30 frames
        self.assertEqual(placer._seconds_to_frames(1.0), 30)
        
        # 2 seconds at 30fps = 60 frames
        self.assertEqual(placer._seconds_to_frames(2.0), 60)
        
        # 0.5 seconds at 30fps = 15 frames
        self.assertEqual(placer._seconds_to_frames(0.5), 15)
    
    def test_custom_fps(self):
        """Test conversion with custom FPS."""
        placer = SfxPlacer()
        
        # 1 second at 24fps = 24 frames
        self.assertEqual(placer._seconds_to_frames(1.0, fps=24), 24)
        
        # 1 second at 60fps = 60 frames
        self.assertEqual(placer._seconds_to_frames(1.0, fps=60), 60)


class TestSfxPlacerGetDefaultVolume(unittest.TestCase):
    """Tests for _get_default_volume_for_moment_type."""
    
    def test_moment_type_volumes(self):
        """Test that correct volumes are returned for each moment type."""
        placer = SfxPlacer()
        
        self.assertEqual(placer._get_default_volume_for_moment_type("intro_whoosh"), -10.0)
        self.assertEqual(placer._get_default_volume_for_moment_type("pivot_emphasis"), -15.0)
        self.assertEqual(placer._get_default_volume_for_moment_type("outro_chime"), -10.0)
        self.assertEqual(placer._get_default_volume_for_moment_type("transition"), -12.0)
        self.assertEqual(placer._get_default_volume_for_moment_type("accent"), -10.0)
        self.assertEqual(placer._get_default_volume_for_moment_type("underscore"), -18.0)
        self.assertEqual(placer._get_default_volume_for_moment_type("generic"), DEFAULT_SFX_VOLUME_DB)
    
    def test_unknown_moment_type(self):
        """Test that unknown moment type returns default volume."""
        placer = SfxPlacer()
        
        self.assertEqual(placer._get_default_volume_for_moment_type("unknown_type"), DEFAULT_SFX_VOLUME_DB)


class TestSfxPlacerTrackConflict(unittest.TestCase):
    """Tests for _check_track_conflict method."""
    
    def test_no_conflict_empty_placements(self):
        """Test that empty placements means no conflict."""
        placer = SfxPlacer()
        
        has_conflict = placer._check_track_conflict(3, 0, 90, [])
        self.assertFalse(has_conflict)
    
    def test_no_conflict_different_track(self):
        """Test that different track means no conflict."""
        placer = SfxPlacer()
        
        existing = [
            SfxPlacement(
                segment_index=1,
                track_number=4,  # Different track
                timeline_start_frame=0,
                timeline_end_frame=90,
                sfx_file_path="/path/to/sfx1.wav"
            )
        ]
        
        has_conflict = placer._check_track_conflict(3, 0, 90, existing)
        self.assertFalse(has_conflict)
    
    def test_conflict_same_track_overlap(self):
        """Test that overlapping on same track creates conflict."""
        placer = SfxPlacer()
        
        existing = [
            SfxPlacement(
                segment_index=1,
                track_number=3,
                timeline_start_frame=0,
                timeline_end_frame=90,
                sfx_file_path="/path/to/sfx1.wav"
            )
        ]
        
        # New segment overlaps with existing (0-60 overlaps with 0-90)
        has_conflict = placer._check_track_conflict(3, 0, 60, existing)
        self.assertTrue(has_conflict)
    
    def test_no_conflict_non_overlapping(self):
        """Test that non-overlapping segments on same track have no conflict."""
        placer = SfxPlacer()
        
        existing = [
            SfxPlacement(
                segment_index=1,
                track_number=3,
                timeline_start_frame=0,
                timeline_end_frame=90,
                sfx_file_path="/path/to/sfx1.wav"
            )
        ]
        
        # New segment starts after existing ends (100-150 vs 0-90)
        has_conflict = placer._check_track_conflict(3, 100, 150, existing)
        self.assertFalse(has_conflict)
    
    def test_conflict_edge_touching(self):
        """Test that touching edges don't conflict (end == start)."""
        placer = SfxPlacer()
        
        existing = [
            SfxPlacement(
                segment_index=1,
                track_number=3,
                timeline_start_frame=0,
                timeline_end_frame=90,
                sfx_file_path="/path/to/sfx1.wav"
            )
        ]
        
        # New segment starts exactly where existing ends (90-150 vs 0-90)
        # This should NOT be a conflict (no overlap)
        has_conflict = placer._check_track_conflict(3, 90, 150, existing)
        self.assertFalse(has_conflict)


class TestSfxPlacerTrackAllocation(unittest.TestCase):
    """Tests for _allocate_sfx_track method."""
    
    def test_preferred_track_available(self):
        """Test that preferred track is used when available."""
        placer = SfxPlacer()
        
        track = placer._allocate_sfx_track(3, 0, 90, [])
        self.assertEqual(track, 3)
    
    def test_next_track_when_preferred_occupied(self):
        """Test that next track is used when preferred is occupied."""
        placer = SfxPlacer()
        
        existing = [
            SfxPlacement(
                segment_index=1,
                track_number=3,
                timeline_start_frame=0,
                timeline_end_frame=90,
                sfx_file_path="/path/to/sfx1.wav"
            )
        ]
        
        track = placer._allocate_sfx_track(3, 0, 90, existing)
        self.assertEqual(track, 4)
    
    def test_fills_tracks_sequentially(self):
        """Test that tracks are filled sequentially when occupied."""
        placer = SfxPlacer()
        
        existing = [
            SfxPlacement(segment_index=1, track_number=3, timeline_start_frame=0, timeline_end_frame=90, sfx_file_path="/a.wav"),
            SfxPlacement(segment_index=2, track_number=4, timeline_start_frame=0, timeline_end_frame=90, sfx_file_path="/b.wav"),
            SfxPlacement(segment_index=3, track_number=5, timeline_start_frame=0, timeline_end_frame=90, sfx_file_path="/c.wav"),
        ]
        
        track = placer._allocate_sfx_track(3, 0, 90, existing)
        self.assertEqual(track, 6)
    
    def test_raises_error_when_all_tracks_full(self):
        """Test that error is raised when all SFX tracks (3-10) are full."""
        placer = SfxPlacer()
        
        # Fill all 8 SFX tracks (3-10)
        existing = [
            SfxPlacement(segment_index=i, track_number=track, timeline_start_frame=0, timeline_end_frame=90, sfx_file_path=f"/{i}.wav")
            for i, track in enumerate(range(3, 11), 1)
        ]
        
        with self.assertRaises(TrackAllocationError) as context:
            placer._allocate_sfx_track(3, 0, 90, existing)
        
        self.assertIn("All SFX tracks", str(context.exception))
    
    def test_adjusts_out_of_range_preferred(self):
        """Test that out-of-range preferred track is adjusted to valid range."""
        placer = SfxPlacer()
        
        # Preferred track 2 is invalid, should be adjusted to 3
        track = placer._allocate_sfx_track(2, 0, 90, [])
        self.assertEqual(track, 3)
        
        # Preferred track 15 is too high, should be adjusted to 10
        existing = [SfxPlacement(segment_index=1, track_number=track, timeline_start_frame=0, timeline_end_frame=90, sfx_file_path=f"/{track}.wav") for track in range(3, 11)]
        with self.assertRaises(TrackAllocationError):
            placer._allocate_sfx_track(15, 0, 90, existing)


class TestSfxPlacerPlaceSfxClips(unittest.TestCase):
    """Integration tests for place_sfx_clips method."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test_sfx.wav")
        with open(self.test_file, 'w') as f:
            f.write("")
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        os.rmdir(self.temp_dir)
    
    @patch.object(SfxPlacer, '_import_sfx_to_pool')
    @patch.object(SfxPlacer, '_create_timeline_sfx_clip')
    def test_place_single_sfx_success(self, mock_create_clip, mock_import):
        """Test successful placement of a single SFX clip."""
        # Setup mocks
        mock_sfx_clip = MagicMock()
        mock_import.return_value = mock_sfx_clip
        mock_create_clip.return_value = "sfx_clip_001"
        
        # Create placer with mocked ResolveApi
        mock_resolve = MagicMock()
        mock_resolve.is_available.return_value = True
        mock_timeline = MagicMock()
        mock_resolve.find_timeline_by_name.return_value = mock_timeline
        
        placer = SfxPlacer(resolve_api=mock_resolve)
        
        segments = [
            {
                "segment_index": 1,
                "sfx_file_path": self.test_file,
                "start_frames": 0,
                "end_frames": 90,
                "fade_in_seconds": 1.0,
                "fade_out_seconds": 1.0,
                "volume_db": -12.0,
                "moment_type": "intro_whoosh"
            }
        ]
        
        result = placer.place_sfx_clips("timeline_001", segments)
        
        self.assertTrue(result.success)
        self.assertEqual(result.clips_placed, 1)
        self.assertEqual(result.tracks_used, [3])
        self.assertEqual(len(result.timeline_positions), 1)
        
        placement = result.timeline_positions[0]
        self.assertEqual(placement.segment_index, 1)
        self.assertEqual(placement.track_number, 3)
        self.assertEqual(placement.volume_db, -12.0)
        self.assertEqual(placement.moment_type, "intro_whoosh")
    
    @patch.object(SfxPlacer, '_import_sfx_to_pool')
    @patch.object(SfxPlacer, '_create_timeline_sfx_clip')
    def test_place_multiple_sfx_different_times(self, mock_create_clip, mock_import):
        """Test placing multiple SFX at different times on same track."""
        mock_sfx_clip = MagicMock()
        mock_import.return_value = mock_sfx_clip
        mock_create_clip.return_value = "sfx_clip_001"
        
        mock_resolve = MagicMock()
        mock_resolve.is_available.return_value = True
        mock_timeline = MagicMock()
        mock_resolve.find_timeline_by_name.return_value = mock_timeline
        
        placer = SfxPlacer(resolve_api=mock_resolve)
        
        segments = [
            {
                "segment_index": 1,
                "sfx_file_path": self.test_file,
                "start_frames": 0,
                "end_frames": 30,
                "moment_type": "intro_whoosh"
            },
            {
                "segment_index": 2,
                "sfx_file_path": self.test_file,
                "start_frames": 100,
                "end_frames": 130,
                "moment_type": "pivot_emphasis"
            }
        ]
        
        result = placer.place_sfx_clips("timeline_001", segments)
        
        self.assertTrue(result.success)
        self.assertEqual(result.clips_placed, 2)
        # Both should be on track 3 since they don't overlap
        self.assertEqual(result.tracks_used, [3])
    
    @patch.object(SfxPlacer, '_import_sfx_to_pool')
    @patch.object(SfxPlacer, '_create_timeline_sfx_clip')
    def test_place_overlapping_sfx_different_tracks(self, mock_create_clip, mock_import):
        """Test that overlapping SFX are placed on different tracks."""
        mock_sfx_clip = MagicMock()
        mock_import.return_value = mock_sfx_clip
        mock_create_clip.return_value = "sfx_clip_001"
        
        mock_resolve = MagicMock()
        mock_resolve.is_available.return_value = True
        mock_timeline = MagicMock()
        mock_resolve.find_timeline_by_name.return_value = mock_timeline
        
        placer = SfxPlacer(resolve_api=mock_resolve)
        
        # Two SFX at the same time (overlapping)
        segments = [
            {
                "segment_index": 1,
                "sfx_file_path": self.test_file,
                "start_frames": 0,
                "end_frames": 90,
                "moment_type": "intro_whoosh"
            },
            {
                "segment_index": 2,
                "sfx_file_path": self.test_file,
                "start_frames": 0,
                "end_frames": 90,
                "moment_type": "accent"
            }
        ]
        
        result = placer.place_sfx_clips("timeline_001", segments)
        
        self.assertTrue(result.success)
        self.assertEqual(result.clips_placed, 2)
        # Should use tracks 3 and 4
        self.assertEqual(set(result.tracks_used), {3, 4})
    
    def test_invalid_timeline_id(self):
        """Test error handling for invalid timeline ID."""
        placer = SfxPlacer()
        
        result = placer.place_sfx_clips("", [])
        
        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "INVALID_TIMELINE_ID")
    
    def test_resolve_api_unavailable(self):
        """Test error handling when Resolve API is unavailable."""
        mock_resolve = MagicMock()
        mock_resolve.is_available.return_value = False
        
        placer = SfxPlacer(resolve_api=mock_resolve)
        
        result = placer.place_sfx_clips("timeline_001", [])
        
        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "RESOLVE_API_UNAVAILABLE")
    
    def test_timeline_not_found(self):
        """Test error handling when timeline is not found."""
        mock_resolve = MagicMock()
        mock_resolve.is_available.return_value = True
        mock_resolve.find_timeline_by_name.return_value = None
        
        placer = SfxPlacer(resolve_api=mock_resolve)
        
        result = placer.place_sfx_clips("timeline_001", [])
        
        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "TIMELINE_NOT_FOUND")
    
    @patch.object(SfxPlacer, '_import_sfx_to_pool')
    def test_continues_on_import_failure(self, mock_import):
        """Test that placement continues even if one SFX fails to import."""
        mock_import.return_value = None  # Import fails
        
        mock_resolve = MagicMock()
        mock_resolve.is_available.return_value = True
        mock_timeline = MagicMock()
        mock_resolve.find_timeline_by_name.return_value = mock_timeline
        
        placer = SfxPlacer(resolve_api=mock_resolve)
        
        segments = [
            {
                "segment_index": 1,
                "sfx_file_path": self.test_file,
                "start_frames": 0,
                "end_frames": 90,
            }
        ]
        
        result = placer.place_sfx_clips("timeline_001", segments)
        
        # Should succeed but with 0 clips placed
        self.assertFalse(result.success)
        self.assertEqual(result.clips_placed, 0)
    
    def test_progress_callback(self):
        """Test that progress callback is called during placement."""
        mock_resolve = MagicMock()
        mock_resolve.is_available.return_value = True
        mock_timeline = MagicMock()
        mock_resolve.find_timeline_by_name.return_value = mock_timeline
        
        with patch.object(SfxPlacer, '_import_sfx_to_pool') as mock_import, \
             patch.object(SfxPlacer, '_create_timeline_sfx_clip') as mock_create:
            
            mock_import.return_value = MagicMock()
            mock_create.return_value = "sfx_001"
            
            placer = SfxPlacer(resolve_api=mock_resolve)
            
            progress_calls = []
            def progress_callback(current, total, message):
                progress_calls.append((current, total, message))
            
            segments = [
                {
                    "segment_index": 1,
                    "sfx_file_path": self.test_file,
                    "start_frames": 0,
                    "end_frames": 90,
                },
                {
                    "segment_index": 2,
                    "sfx_file_path": self.test_file,
                    "start_frames": 100,
                    "end_frames": 190,
                }
            ]
            
            placer.place_sfx_clips("timeline_001", segments, progress_callback=progress_callback)
            
            self.assertEqual(len(progress_calls), 2)
            self.assertEqual(progress_calls[0], (1, 2, "Placing SFX: test_sfx.wav"))
            self.assertEqual(progress_calls[1], (2, 2, "Placing SFX: test_sfx.wav"))


class TestSfxPlacerDefaultsAndConstants(unittest.TestCase):
    """Tests for default values and constants."""
    
    def test_sfx_specific_defaults(self):
        """Test that SFX has different defaults than music."""
        # SFX fades should be shorter than music (1s vs 2s)
        self.assertEqual(DEFAULT_SFX_FADE_IN_SECONDS, 1.0)
        self.assertEqual(DEFAULT_SFX_FADE_OUT_SECONDS, 1.0)
        
        # SFX track range should be 3-10
        self.assertEqual(SFX_TRACK_START, 3)
        self.assertEqual(SFX_TRACK_END, 10)
        self.assertEqual(MAX_SFX_TRACKS, 8)
        
        # Default volume should be reasonable for accent sounds
        self.assertEqual(DEFAULT_SFX_VOLUME_DB, -12.0)
        
        # Handle room should be ±2 seconds
        self.assertEqual(DEFAULT_HANDLE_SECONDS, 2.0)


if __name__ == "__main__":
    unittest.main()
