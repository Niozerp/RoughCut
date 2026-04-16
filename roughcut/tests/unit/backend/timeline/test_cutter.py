"""Unit tests for the FootageCutter class.

Tests cover segment cutting, sequential placement, timecode precision,
and error handling scenarios.
"""

import unittest
from unittest.mock import MagicMock, patch
from dataclasses import asdict

from roughcut.backend.timeline.cutter import (
    FootageCutter,
    SegmentPlacement,
    CutResult,
    timecode_to_frames,
    frames_to_timecode,
    validate_segments
)


class TestTimecodeConversion(unittest.TestCase):
    """Test timecode to frames conversion and vice versa."""
    
    def test_timecode_to_frames_minutes_seconds(self):
        """Test converting MM:SS timecode to frames."""
        # 1:30 at 30fps = (1*60 + 30) * 30 = 2700 frames
        result = timecode_to_frames("1:30", fps=30)
        self.assertEqual(result, 2700)
    
    def test_timecode_to_frames_hours_minutes_seconds(self):
        """Test converting H:MM:SS timecode to frames."""
        # 1:30:00 at 30fps = (1*3600 + 30*60) * 30 = 162000 frames
        result = timecode_to_frames("1:30:00", fps=30)
        self.assertEqual(result, 162000)
    
    def test_timecode_to_frames_with_frames(self):
        """Test converting H:MM:SS:FF timecode to frames."""
        # 0:15:30:15 at 30fps = (0*3600 + 15*60 + 30) * 30 + 15 = 27900 + 15 = 27915 frames
        result = timecode_to_frames("0:15:30:15", fps=30)
        self.assertEqual(result, 27915)
    
    def test_timecode_to_frames_different_fps(self):
        """Test conversion with different frame rates."""
        # 1:00 at 24fps = 60 * 24 = 1440 frames
        result_24 = timecode_to_frames("1:00", fps=24)
        self.assertEqual(result_24, 1440)
        
        # 1:00 at 60fps = 60 * 60 = 3600 frames
        result_60 = timecode_to_frames("1:00", fps=60)
        self.assertEqual(result_60, 3600)
    
    def test_frames_to_timecode_minutes(self):
        """Test converting frames to MM:SS timecode."""
        # 2700 frames at 30fps = 90 seconds = 1:30
        result = frames_to_timecode(2700, fps=30)
        self.assertEqual(result, "1:30")
    
    def test_frames_to_timecode_hours(self):
        """Test converting frames to H:MM:SS timecode."""
        # 5400 frames at 30fps = 180 seconds = 3:00
        result = frames_to_timecode(5400, fps=30)
        self.assertEqual(result, "3:00")
    
    def test_frames_to_timecode_with_frames(self):
        """Test converting frames to H:MM:SS:FF timecode."""
        # 27945 frames at 30fps = 931.5 seconds = 00:15:31:15 (15 min, 31 sec, 15 frames)
        result = frames_to_timecode(27945, fps=30, include_frames=True)
        self.assertEqual(result, "00:15:31:15")
    
    def test_roundtrip_conversion(self):
        """Test that timecode -> frames -> timecode is consistent."""
        original = "5:30:15"
        frames = timecode_to_frames(original, fps=30)
        result = frames_to_timecode(frames, fps=30)
        self.assertEqual(original, result)


class TestSegmentValidation(unittest.TestCase):
    """Test segment validation functions."""
    
    def test_valid_segments(self):
        """Test validation of valid segments."""
        segments = [
            {"segment_index": 1, "start_frames": 0, "end_frames": 100},
            {"segment_index": 2, "start_frames": 200, "end_frames": 300}
        ]
        is_valid, error = validate_segments(segments)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_invalid_start_greater_than_end(self):
        """Test detection of invalid segment where start > end."""
        segments = [
            {"segment_index": 1, "start_frames": 100, "end_frames": 50}
        ]
        is_valid, error = validate_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "INVALID_SEGMENT_RANGE")
    
    def test_negative_frames(self):
        """Test detection of negative frame values."""
        segments = [
            {"segment_index": 1, "start_frames": -10, "end_frames": 100}
        ]
        is_valid, error = validate_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "NEGATIVE_FRAME_VALUE")
    
    def test_empty_segments(self):
        """Test validation with empty segment list."""
        is_valid, error = validate_segments([])
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "NO_SEGMENTS")
    
    def test_overlapping_segments(self):
        """Test detection of overlapping segments."""
        segments = [
            {"segment_index": 1, "start_frames": 0, "end_frames": 100},
            {"segment_index": 2, "start_frames": 50, "end_frames": 150}  # Overlaps with first
        ]
        is_valid, error = validate_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "OVERLAPPING_SEGMENTS")


class TestFootageCutterInitialization(unittest.TestCase):
    """Test FootageCutter class initialization."""
    
    def test_init_with_default_resolve_api(self):
        """Test initialization creates default ResolveApi."""
        cutter = FootageCutter()
        self.assertIsNotNone(cutter.resolve_api)
    
    def test_init_with_custom_resolve_api(self):
        """Test initialization with custom ResolveApi."""
        mock_api = MagicMock()
        cutter = FootageCutter(resolve_api=mock_api)
        self.assertEqual(cutter.resolve_api, mock_api)


class TestCalculateSequentialPlacements(unittest.TestCase):
    """Test sequential placement calculation."""
    
    def setUp(self):
        self.cutter = FootageCutter()
    
    def test_single_segment_placement(self):
        """Test placement of single segment at timeline start."""
        segments = [
            {"segment_index": 1, "start_frames": 900, "end_frames": 6300}
        ]
        placements = self.cutter._calculate_sequential_placements(segments)
        
        self.assertEqual(len(placements), 1)
        self.assertEqual(placements[0].timeline_start_frame, 0)
        self.assertEqual(placements[0].timeline_end_frame, 5400)  # 6300 - 900 = 5400
        self.assertEqual(placements[0].source_in_frame, 900)
        self.assertEqual(placements[0].source_out_frame, 6300)
    
    def test_multiple_segments_sequential(self):
        """Test sequential placement of multiple segments."""
        segments = [
            {"segment_index": 1, "start_frames": 900, "end_frames": 2700},   # 1800 frames
            {"segment_index": 2, "start_frames": 9000, "end_frames": 11700},  # 2700 frames
            {"segment_index": 3, "start_frames": 37800, "end_frames": 43200}  # 5400 frames
        ]
        placements = self.cutter._calculate_sequential_placements(segments)
        
        self.assertEqual(len(placements), 3)
        
        # First segment at position 0
        self.assertEqual(placements[0].timeline_start_frame, 0)
        self.assertEqual(placements[0].timeline_end_frame, 1800)
        
        # Second segment starts at end of first
        self.assertEqual(placements[1].timeline_start_frame, 1800)
        self.assertEqual(placements[1].timeline_end_frame, 4500)  # 1800 + 2700
        
        # Third segment starts at end of second
        self.assertEqual(placements[2].timeline_start_frame, 4500)
        self.assertEqual(placements[2].timeline_end_frame, 9900)  # 4500 + 5400
    
    def test_gap_removal(self):
        """Test that gaps between source segments are removed in timeline."""
        # Source: segment at 0-100, next segment at 1000-1100 (900 frame gap)
        # Timeline: segment at 0-100, next segment at 100-200 (gap removed)
        segments = [
            {"segment_index": 1, "start_frames": 0, "end_frames": 100},
            {"segment_index": 2, "start_frames": 1000, "end_frames": 1100}
        ]
        placements = self.cutter._calculate_sequential_placements(segments)
        
        # Gap of 900 frames should be removed
        self.assertEqual(placements[0].timeline_end_frame, 100)
        self.assertEqual(placements[1].timeline_start_frame, 100)
        self.assertEqual(placements[1].timeline_end_frame, 200)


class TestCutSegments(unittest.TestCase):
    """Test the main cut_segments method."""
    
    def setUp(self):
        self.mock_resolve_api = MagicMock()
        self.cutter = FootageCutter(resolve_api=self.mock_resolve_api)
    
    def test_cut_segments_success(self):
        """Test successful segment cutting."""
        segments = [
            {"segment_index": 1, "start_frames": 900, "end_frames": 6300}
        ]
        
        # Mock Resolve API responses
        mock_timeline = MagicMock()
        mock_source_clip = MagicMock()
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_resolve_api.get_media_pool.return_value.GetRootFolder.return_value.GetClipList.return_value = [mock_source_clip]
        mock_source_clip.GetName.return_value = "source_clip_001"
        
        # Mock successful clip creation
        mock_timeline_item = MagicMock()
        mock_timeline.AddClip.return_value = mock_timeline_item
        
        result = self.cutter.cut_segments(
            timeline_id="timeline_123",
            source_clip_id="source_clip_001",
            segments=segments
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.segments_placed, 1)
    
    def test_cut_segments_invalid_timeline(self):
        """Test cutting with invalid timeline ID."""
        self.mock_resolve_api.find_timeline_by_name.return_value = None
        
        segments = [{"segment_index": 1, "start_frames": 0, "end_frames": 100}]
        
        result = self.cutter.cut_segments(
            timeline_id="nonexistent_timeline",
            source_clip_id="source_001",
            segments=segments
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "TIMELINE_NOT_FOUND")
    
    def test_cut_segments_source_not_found(self):
        """Test cutting when source clip not in media pool."""
        mock_timeline = MagicMock()
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_resolve_api.get_media_pool.return_value.GetRootFolder.return_value.GetClipList.return_value = []
        
        segments = [{"segment_index": 1, "start_frames": 0, "end_frames": 100}]
        
        result = self.cutter.cut_segments(
            timeline_id="timeline_123",
            source_clip_id="nonexistent_source",
            segments=segments
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "SOURCE_CLIP_NOT_FOUND")


class TestCutResultDataclass(unittest.TestCase):
    """Test CutResult dataclass."""
    
    def test_cut_result_success(self):
        """Test successful result creation."""
        placements = [
            SegmentPlacement(
                segment_index=1,
                timeline_track=1,
                timeline_start_frame=0,
                timeline_end_frame=5400,
                source_in_frame=900,
                source_out_frame=6300,
                clip_id="clip_001"
            )
        ]
        
        result = CutResult(
            segments_placed=1,
            total_duration_frames=5400,
            timeline_positions=placements,
            success=True
        )
        
        self.assertEqual(result.segments_placed, 1)
        self.assertEqual(result.total_duration_frames, 5400)
        self.assertEqual(len(result.timeline_positions), 1)
    
    def test_cut_result_error(self):
        """Test error result creation."""
        error = {
            "code": "TEST_ERROR",
            "category": "test",
            "message": "Test error message",
            "recoverable": True,
            "suggestion": "Test suggestion"
        }
        
        result = CutResult(
            segments_placed=0,
            total_duration_frames=0,
            timeline_positions=[],
            success=False,
            error=error
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "TEST_ERROR")


class TestProgressCallback(unittest.TestCase):
    """Test progress reporting functionality."""
    
    def setUp(self):
        self.mock_resolve_api = MagicMock()
        self.cutter = FootageCutter(resolve_api=self.mock_resolve_api)
    
    def test_progress_callback_invoked(self):
        """Test that progress callback is called during cutting."""
        progress_calls = []
        
        def progress_callback(current, total, message):
            progress_calls.append({"current": current, "total": total, "message": message})
        
        segments = [
            {"segment_index": 1, "start_frames": 0, "end_frames": 100},
            {"segment_index": 2, "start_frames": 200, "end_frames": 300}
        ]
        
        # Mock Resolve API
        mock_timeline = MagicMock()
        mock_source_clip = MagicMock()
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_resolve_api.get_media_pool.return_value.GetRootFolder.return_value.GetClipList.return_value = [mock_source_clip]
        mock_source_clip.GetName.return_value = "source_001"
        mock_timeline.AddClip.return_value = MagicMock()
        
        self.cutter.cut_segments(
            timeline_id="timeline_123",
            source_clip_id="source_001",
            segments=segments,
            progress_callback=progress_callback
        )
        
        # Should have 2 progress calls (one for each segment)
        self.assertEqual(len(progress_calls), 2)
        self.assertEqual(progress_calls[0]["current"], 1)
        self.assertEqual(progress_calls[0]["total"], 2)


if __name__ == "__main__":
    unittest.main()
