"""Unit tests for VFX placer module.

Tests VfxPlacer, VfxPlacement, VfxPlacerResult, validation functions,
track allocation, conflict detection, and template parameter handling.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from roughcut.backend.timeline.vfx_placer import (
    VfxPlacer,
    VfxPlacement,
    VfxPlacerResult,
    TrackAllocationError,
    validate_vfx_segments,
    detect_vfx_type,
    apply_template_params,
    VFX_TEMPLATE_DEFAULTS,
    VFX_TRACK_START,
    VFX_TRACK_END,
    DEFAULT_VFX_FADE_IN_SECONDS,
    DEFAULT_VFX_FADE_OUT_SECONDS,
)


class TestValidateVfxSegments(unittest.TestCase):
    """Tests for VFX segment validation."""
    
    def setUp(self):
        """Create temporary VFX files for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.vfx_file = os.path.join(self.temp_dir, "test_template.comp")
        with open(self.vfx_file, 'w') as f:
            f.write("test vfx content")
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_valid_single_segment(self):
        """Test validation of a valid single segment."""
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file,
                "start_frames": 450,
                "end_frames": 600,
                "track_number": 11,
                "template_type": "lower_third",
                "template_params": {"speaker_name": "John"}
            }
        ]
        
        is_valid, error = validate_vfx_segments(segments)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_valid_multiple_segments(self):
        """Test validation of multiple valid segments."""
        vfx_file2 = os.path.join(self.temp_dir, "test2.comp")
        with open(vfx_file2, 'w') as f:
            f.write("test2")
        
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file,
                "start_frames": 450,
                "end_frames": 600
            },
            {
                "segment_index": 2,
                "vfx_file_path": vfx_file2,
                "start_frames": 6750,
                "end_frames": 7200
            }
        ]
        
        is_valid, error = validate_vfx_segments(segments)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_empty_segments(self):
        """Test validation fails with empty segments."""
        is_valid, error = validate_vfx_segments([])
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "NO_VFX_SEGMENTS")
    
    def test_none_segments(self):
        """Test validation fails with None segments."""
        is_valid, error = validate_vfx_segments(None)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "NO_VFX_SEGMENTS")
    
    def test_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file
                # Missing start_frames, end_frames
            }
        ]
        
        is_valid, error = validate_vfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "MISSING_START_FRAMES")
    
    def test_relative_file_path(self):
        """Test validation fails with relative file path."""
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": "relative/path.comp",
                "start_frames": 450,
                "end_frames": 600
            }
        ]
        
        is_valid, error = validate_vfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "RELATIVE_FILE_PATH")
    
    def test_nonexistent_file(self):
        """Test validation fails when file doesn't exist."""
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": "/nonexistent/path/template.comp",
                "start_frames": 450,
                "end_frames": 600
            }
        ]
        
        is_valid, error = validate_vfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "VFX_FILE_NOT_FOUND")
    
    def test_invalid_track_number(self):
        """Test validation fails with invalid track number."""
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file,
                "start_frames": 450,
                "end_frames": 600,
                "track_number": 5  # Invalid - should be 11-14
            }
        ]
        
        is_valid, error = validate_vfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "INVALID_TRACK_NUMBER")
    
    def test_invalid_template_type(self):
        """Test validation fails with unknown template type."""
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file,
                "start_frames": 450,
                "end_frames": 600,
                "template_type": "unknown_type"
            }
        ]
        
        is_valid, error = validate_vfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "INVALID_TEMPLATE_TYPE")
    
    def test_negative_frames(self):
        """Test validation fails with negative frames."""
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file,
                "start_frames": -100,
                "end_frames": 600
            }
        ]
        
        is_valid, error = validate_vfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "NEGATIVE_START_FRAME")
    
    def test_invalid_segment_range(self):
        """Test validation fails when start >= end."""
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file,
                "start_frames": 600,
                "end_frames": 450
            }
        ]
        
        is_valid, error = validate_vfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "INVALID_SEGMENT_RANGE")
    
    def test_duplicate_segment_index(self):
        """Test validation fails with duplicate segment indices."""
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file,
                "start_frames": 450,
                "end_frames": 600
            },
            {
                "segment_index": 1,  # Duplicate
                "vfx_file_path": self.vfx_file,
                "start_frames": 1000,
                "end_frames": 1200
            }
        ]
        
        is_valid, error = validate_vfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "DUPLICATE_INDEX")
    
    def test_path_traversal_detection(self):
        """Test validation detects path traversal attempts."""
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": "/safe/path/../../../etc/passwd",
                "start_frames": 450,
                "end_frames": 600
            }
        ]
        
        is_valid, error = validate_vfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "PATH_TRAVERSAL_DETECTED")
    
    def test_invalid_fade_durations(self):
        """Test validation fails with negative fade durations."""
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file,
                "start_frames": 450,
                "end_frames": 600,
                "fade_in_seconds": -1.0
            }
        ]
        
        is_valid, error = validate_vfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "INVALID_FADE_IN")
    
    def test_invalid_template_params_type(self):
        """Test validation fails when template_params is not a dict."""
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file,
                "start_frames": 450,
                "end_frames": 600,
                "template_params": "not_a_dict"
            }
        ]
        
        is_valid, error = validate_vfx_segments(segments)
        self.assertFalse(is_valid)
        self.assertEqual(error["code"], "INVALID_TEMPLATE_PARAMS")


class TestVfxPlacementDataclass(unittest.TestCase):
    """Tests for VfxPlacement dataclass."""
    
    def test_default_values(self):
        """Test VfxPlacement with default values."""
        placement = VfxPlacement(
            segment_index=1,
            track_number=11,
            timeline_start_frame=450,
            timeline_end_frame=600,
            vfx_file_path="/path/to/template.comp"
        )
        
        self.assertEqual(placement.segment_index, 1)
        self.assertEqual(placement.track_number, 11)
        self.assertEqual(placement.timeline_start_frame, 450)
        self.assertEqual(placement.timeline_end_frame, 600)
        self.assertEqual(placement.vfx_file_path, "/path/to/template.comp")
        self.assertIsNone(placement.clip_id)
        self.assertEqual(placement.fade_in_frames, 0)
        self.assertEqual(placement.fade_out_frames, 0)
        self.assertEqual(placement.template_type, "generic")
        self.assertEqual(placement.template_params, {})
        self.assertEqual(placement.vfx_type, "generator_effect")
    
    def test_custom_values(self):
        """Test VfxPlacement with custom values."""
        placement = VfxPlacement(
            segment_index=2,
            track_number=12,
            timeline_start_frame=6750,
            timeline_end_frame=7200,
            vfx_file_path="/path/to/cta.comp",
            clip_id="vfx_clip_002",
            fade_in_frames=15,
            fade_out_frames=15,
            template_type="outro_cta",
            template_params={"cta_text": "Subscribe"},
            vfx_type="fusion_composition"
        )
        
        self.assertEqual(placement.clip_id, "vfx_clip_002")
        self.assertEqual(placement.fade_in_frames, 15)
        self.assertEqual(placement.template_type, "outro_cta")
        self.assertEqual(placement.template_params["cta_text"], "Subscribe")
        self.assertEqual(placement.vfx_type, "fusion_composition")


class TestVfxPlacerResult(unittest.TestCase):
    """Tests for VfxPlacerResult dataclass."""
    
    def test_default_values(self):
        """Test VfxPlacerResult with default values."""
        result = VfxPlacerResult(
            clips_placed=2,
            tracks_used=[11, 12],
            total_duration_frames=1500,
            timeline_positions=[]
        )
        
        self.assertEqual(result.clips_placed, 2)
        self.assertEqual(result.tracks_used, [11, 12])
        self.assertEqual(result.total_duration_frames, 1500)
        self.assertTrue(result.success)
        self.assertIsNone(result.error)
        self.assertEqual(result.fps, 30)
    
    def test_timecode_conversion(self):
        """Test timecode conversion methods."""
        result = VfxPlacerResult(
            clips_placed=1,
            tracks_used=[11],
            total_duration_frames=450,  # 15 seconds at 30fps
            timeline_positions=[],
            fps=30
        )
        
        timecode = result.get_total_duration_timecode()
        self.assertEqual(timecode, "0:00:15")  # 15 seconds
        
        # Test with different FPS
        timecode_24fps = result.get_total_duration_timecode(fps=24)
        self.assertEqual(timecode_24fps, "0:00:18")  # 450/24 = 18.75 -> 18
    
    def test_timecode_property(self):
        """Test total_duration_timecode property."""
        result = VfxPlacerResult(
            clips_placed=1,
            tracks_used=[11],
            total_duration_frames=7200,  # 4 minutes at 30fps
            timeline_positions=[]
        )
        
        self.assertEqual(result.total_duration_timecode, "0:04:00")


class TestVfxPlacerSecondsToFrames(unittest.TestCase):
    """Tests for seconds to frames conversion."""
    
    def setUp(self):
        """Set up VfxPlacer instance."""
        self.placer = VfxPlacer()
    
    def test_basic_conversion(self):
        """Test basic seconds to frames conversion."""
        frames = self.placer._seconds_to_frames(1.0, fps=30)
        self.assertEqual(frames, 30)
    
    def test_half_second(self):
        """Test half second conversion."""
        frames = self.placer._seconds_to_frames(0.5, fps=30)
        self.assertEqual(frames, 15)
    
    def test_different_fps(self):
        """Test conversion with different FPS."""
        frames = self.placer._seconds_to_frames(1.0, fps=24)
        self.assertEqual(frames, 24)
        
        frames = self.placer._seconds_to_frames(1.0, fps=60)
        self.assertEqual(frames, 60)
    
    def test_zero_seconds(self):
        """Test zero seconds returns zero frames."""
        frames = self.placer._seconds_to_frames(0.0, fps=30)
        self.assertEqual(frames, 0)
    
    def test_invalid_fps_zero(self):
        """Test that zero FPS raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.placer._seconds_to_frames(1.0, fps=0)
        self.assertIn("FPS must be a positive number", str(context.exception))
    
    def test_invalid_fps_negative(self):
        """Test that negative FPS raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.placer._seconds_to_frames(1.0, fps=-30)
        self.assertIn("FPS must be a positive number", str(context.exception))


class TestDetectVfxType(unittest.TestCase):
    """Tests for VFX type detection."""
    
    def test_fusion_composition(self):
        """Test detection of Fusion composition (.comp)."""
        vfx_type = detect_vfx_type("/path/to/lower_third.comp")
        self.assertEqual(vfx_type, "fusion_composition")
    
    def test_generator_effect(self):
        """Test detection of generator effect (.setting)."""
        vfx_type = detect_vfx_type("/path/to/effect.setting")
        self.assertEqual(vfx_type, "generator_effect")
    
    def test_unknown_type_defaults_to_generator(self):
        """Test unknown types default to generator_effect."""
        vfx_type = detect_vfx_type("/path/to/template.unknown")
        self.assertEqual(vfx_type, "generator_effect")


class TestApplyTemplateParams(unittest.TestCase):
    """Tests for template parameter application."""
    
    def test_lower_third_defaults(self):
        """Test lower_third template defaults."""
        params = apply_template_params("lower_third", None)
        self.assertEqual(params["speaker_name"], "")
        self.assertEqual(params["title"], "")
        self.assertEqual(params["duration_seconds"], 5.0)
    
    def test_lower_third_override(self):
        """Test lower_third with AI overrides."""
        ai_params = {"speaker_name": "John Doe", "title": "CEO"}
        params = apply_template_params("lower_third", ai_params)
        
        self.assertEqual(params["speaker_name"], "John Doe")
        self.assertEqual(params["title"], "CEO")
        # Defaults preserved for unspecified params
        self.assertEqual(params["company"], "")
        self.assertEqual(params["duration_seconds"], 5.0)
    
    def test_outro_cta_defaults(self):
        """Test outro_cta template defaults."""
        params = apply_template_params("outro_cta", None)
        self.assertEqual(params["cta_text"], "Subscribe")
        self.assertEqual(params["duration_seconds"], 5.0)
    
    def test_outro_cta_override(self):
        """Test outro_cta with AI overrides."""
        ai_params = {"cta_text": "Watch More", "sub_text": "New videos weekly"}
        params = apply_template_params("outro_cta", ai_params)
        
        self.assertEqual(params["cta_text"], "Watch More")
        self.assertEqual(params["sub_text"], "New videos weekly")
        self.assertEqual(params["duration_seconds"], 5.0)  # Default preserved
    
    def test_generic_defaults(self):
        """Test generic template defaults."""
        params = apply_template_params("generic", None)
        self.assertEqual(params["duration_seconds"], 3.0)
        self.assertEqual(params["animation_style"], "fade")
    
    def test_unknown_type_uses_generic(self):
        """Test unknown types use generic defaults."""
        # Note: This shouldn't happen in practice since validation catches unknown types
        params = apply_template_params("unknown_type", None)
        self.assertEqual(params["duration_seconds"], 3.0)


class TestVfxPlacerTrackConflict(unittest.TestCase):
    """Tests for track conflict detection."""
    
    def setUp(self):
        """Set up VfxPlacer instance."""
        self.placer = VfxPlacer()
    
    def test_no_conflict_empty_placements(self):
        """Test no conflict with empty placements."""
        conflict = self.placer._check_track_conflict(
            11, 450, 600, []
        )
        self.assertFalse(conflict)
    
    def test_no_conflict_different_track(self):
        """Test no conflict when placements are on different tracks."""
        existing = [
            VfxPlacement(1, 12, 450, 600, "/path.comp")
        ]
        conflict = self.placer._check_track_conflict(
            11, 450, 600, existing
        )
        self.assertFalse(conflict)
    
    def test_conflict_same_track_overlap(self):
        """Test conflict when placements overlap on same track."""
        existing = [
            VfxPlacement(1, 11, 450, 600, "/path.comp")
        ]
        # New segment overlaps (500-650 overlaps 450-600)
        conflict = self.placer._check_track_conflict(
            11, 500, 650, existing
        )
        self.assertTrue(conflict)
    
    def test_no_conflict_same_track_separate(self):
        """Test no conflict when placements don't overlap on same track."""
        existing = [
            VfxPlacement(1, 11, 450, 600, "/path.comp")
        ]
        # New segment is after existing (700-800 doesn't overlap 450-600)
        conflict = self.placer._check_track_conflict(
            11, 700, 800, existing
        )
        self.assertFalse(conflict)
    
    def test_conflict_exact_match(self):
        """Test conflict when placements match exactly."""
        existing = [
            VfxPlacement(1, 11, 450, 600, "/path.comp")
        ]
        conflict = self.placer._check_track_conflict(
            11, 450, 600, existing
        )
        self.assertTrue(conflict)
    
    def test_conflict_contained(self):
        """Test conflict when new segment is contained within existing."""
        existing = [
            VfxPlacement(1, 11, 400, 700, "/path.comp")
        ]
        # New segment (450-550) is contained within (400-700)
        conflict = self.placer._check_track_conflict(
            11, 450, 550, existing
        )
        self.assertTrue(conflict)
    
    def test_zero_duration_no_conflict(self):
        """Test zero duration clips don't conflict."""
        existing = [
            VfxPlacement(1, 11, 450, 600, "/path.comp")
        ]
        # Zero duration at boundary (600-600)
        conflict = self.placer._check_track_conflict(
            11, 600, 600, existing
        )
        self.assertFalse(conflict)


class TestVfxPlacerTrackAllocation(unittest.TestCase):
    """Tests for track allocation logic."""
    
    def setUp(self):
        """Set up VfxPlacer instance."""
        self.placer = VfxPlacer()
    
    def test_allocate_preferred_track_available(self):
        """Test allocation returns preferred track when available."""
        track = self.placer._allocate_vfx_track(11, 450, 600, [])
        self.assertEqual(track, 11)
    
    def test_allocate_next_track_when_preferred_occupied(self):
        """Test allocation finds next available track when preferred is occupied."""
        existing = [
            VfxPlacement(1, 11, 450, 600, "/path.comp")
        ]
        track = self.placer._allocate_vfx_track(11, 450, 600, existing)
        self.assertEqual(track, 12)  # Next track
    
    def test_allocate_tracks_up_to_max(self):
        """Test allocation works up to max VFX tracks."""
        existing = [
            VfxPlacement(1, 11, 450, 600, "/path1.comp"),
            VfxPlacement(2, 12, 450, 600, "/path2.comp"),
            VfxPlacement(3, 13, 450, 600, "/path3.comp"),
        ]
        track = self.placer._allocate_vfx_track(11, 450, 600, existing)
        self.assertEqual(track, 14)  # Last available track
    
    def test_allocate_raises_when_all_tracks_full(self):
        """Test allocation raises error when all tracks are full."""
        existing = [
            VfxPlacement(1, 11, 450, 600, "/path1.comp"),
            VfxPlacement(2, 12, 450, 600, "/path2.comp"),
            VfxPlacement(3, 13, 450, 600, "/path3.comp"),
            VfxPlacement(4, 14, 450, 600, "/path4.comp"),
        ]
        
        with self.assertRaises(TrackAllocationError) as context:
            self.placer._allocate_vfx_track(11, 450, 600, existing)
        
        self.assertIn("All VFX tracks", str(context.exception))
    
    def test_allocate_different_time_same_track(self):
        """Test same track can be used for non-overlapping times."""
        existing = [
            VfxPlacement(1, 11, 450, 600, "/path.comp")
        ]
        # Different time (700-800) on same track 11
        track = self.placer._allocate_vfx_track(11, 700, 800, existing)
        self.assertEqual(track, 11)  # Same track is fine
    
    def test_allocate_clamps_preferred_below_min(self):
        """Test preferred track below min gets clamped."""
        track = self.placer._allocate_vfx_track(5, 450, 600, [])
        self.assertEqual(track, 11)  # Clamped to min
    
    def test_allocate_clamps_preferred_above_max(self):
        """Test preferred track above max gets clamped."""
        track = self.placer._allocate_vfx_track(20, 450, 600, [])
        self.assertEqual(track, 14)  # Clamped to max
    
    def test_allocate_searches_lower_tracks_when_preferred_high(self):
        """Test allocation searches lower tracks when preferred is high."""
        existing = [
            VfxPlacement(1, 14, 450, 600, "/path.comp")
        ]
        # Preferred 14 is occupied, should find 11, 12, or 13
        track = self.placer._allocate_vfx_track(14, 450, 600, existing)
        self.assertIn(track, [11, 12, 13])


class TestVfxPlacerDefaultsAndConstants(unittest.TestCase):
    """Tests for default values and constants."""
    
    def test_vfx_track_range(self):
        """Test VFX track constants."""
        self.assertEqual(VFX_TRACK_START, 11)
        self.assertEqual(VFX_TRACK_END, 14)
        self.assertEqual(VFX_TRACK_END - VFX_TRACK_START + 1, 4)
    
    def test_default_fade_durations(self):
        """Test default fade durations."""
        self.assertEqual(DEFAULT_VFX_FADE_IN_SECONDS, 0.5)
        self.assertEqual(DEFAULT_VFX_FADE_OUT_SECONDS, 0.5)
    
    def test_template_defaults_exist(self):
        """Test that template defaults are defined."""
        self.assertIn("lower_third", VFX_TEMPLATE_DEFAULTS)
        self.assertIn("outro_cta", VFX_TEMPLATE_DEFAULTS)
        self.assertIn("intro_title", VFX_TEMPLATE_DEFAULTS)
        self.assertIn("generic", VFX_TEMPLATE_DEFAULTS)
    
    def test_lower_third_default_structure(self):
        """Test lower_third default structure."""
        defaults = VFX_TEMPLATE_DEFAULTS["lower_third"]
        self.assertIn("speaker_name", defaults)
        self.assertIn("title", defaults)
        self.assertIn("duration_seconds", defaults)
        self.assertEqual(defaults["duration_seconds"], 5.0)


class TestVfxPlacerPlaceVfxClips(unittest.TestCase):
    """Integration tests for place_vfx_templates method."""
    
    def setUp(self):
        """Set up VfxPlacer with mocked Resolve API."""
        self.mock_resolve_api = MagicMock()
        self.mock_resolve_api.is_available.return_value = True
        self.placer = VfxPlacer(resolve_api=self.mock_resolve_api)
        
        # Create temp VFX files
        self.temp_dir = tempfile.mkdtemp()
        self.vfx_file1 = os.path.join(self.temp_dir, "lower_third.comp")
        self.vfx_file2 = os.path.join(self.temp_dir, "outro_cta.comp")
        with open(self.vfx_file1, 'w') as f:
            f.write("fusion comp")
        with open(self.vfx_file2, 'w') as f:
            f.write("fusion comp 2")
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_place_vfx_invalid_timeline_id(self):
        """Test error handling for invalid timeline_id."""
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file1,
                "start_frames": 450,
                "end_frames": 600
            }
        ]
        
        result = self.placer.place_vfx_templates(None, segments)
        
        self.assertFalse(result.success)
        self.assertEqual(result.clips_placed, 0)
        self.assertEqual(result.error["code"], "INVALID_TIMELINE_ID")
    
    def test_place_vfx_resolve_api_unavailable(self):
        """Test error handling when Resolve API is unavailable."""
        self.mock_resolve_api.is_available.return_value = False
        
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file1,
                "start_frames": 450,
                "end_frames": 600
            }
        ]
        
        result = self.placer.place_vfx_templates("timeline_123", segments)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "RESOLVE_API_UNAVAILABLE")
    
    def test_place_vfx_timeline_not_found(self):
        """Test error handling when timeline is not found."""
        self.mock_resolve_api.find_timeline_by_name.return_value = None
        
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file1,
                "start_frames": 450,
                "end_frames": 600
            }
        ]
        
        result = self.placer.place_vfx_templates("timeline_123", segments)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "TIMELINE_NOT_FOUND")
    
    @patch.object(VfxPlacer, '_import_vfx_to_pool')
    @patch.object(VfxPlacer, '_create_timeline_vfx_clip')
    def test_place_single_vfx_success(self, mock_create_clip, mock_import):
        """Test successful placement of single VFX."""
        # Setup mocks
        mock_timeline = MagicMock()
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        mock_import.return_value = MagicMock()
        mock_create_clip.return_value = "vfx_clip_001"
        
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file1,
                "start_frames": 450,
                "end_frames": 600,
                "template_type": "lower_third",
                "template_params": {"speaker_name": "John"}
            }
        ]
        
        result = self.placer.place_vfx_templates("timeline_123", segments)
        
        self.assertTrue(result.success)
        self.assertEqual(result.clips_placed, 1)
        self.assertEqual(result.tracks_used, [11])
        self.assertEqual(len(result.timeline_positions), 1)
        
        placement = result.timeline_positions[0]
        self.assertEqual(placement.segment_index, 1)
        self.assertEqual(placement.track_number, 11)
        self.assertEqual(placement.template_type, "lower_third")
        self.assertEqual(placement.template_params["speaker_name"], "John")
    
    @patch.object(VfxPlacer, '_import_vfx_to_pool')
    @patch.object(VfxPlacer, '_create_timeline_vfx_clip')
    def test_place_multiple_vfx_success(self, mock_create_clip, mock_import):
        """Test successful placement of multiple VFX."""
        # Setup mocks
        mock_timeline = MagicMock()
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        mock_import.return_value = MagicMock()
        mock_create_clip.side_effect = ["vfx_clip_001", "vfx_clip_002"]
        
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file1,
                "start_frames": 450,
                "end_frames": 600,
                "template_type": "lower_third"
            },
            {
                "segment_index": 2,
                "vfx_file_path": self.vfx_file2,
                "start_frames": 6750,
                "end_frames": 7200,
                "template_type": "outro_cta"
            }
        ]
        
        result = self.placer.place_vfx_templates("timeline_123", segments)
        
        self.assertTrue(result.success)
        self.assertEqual(result.clips_placed, 2)
        self.assertEqual(result.tracks_used, [11])  # Same track, different times
    
    @patch.object(VfxPlacer, '_import_vfx_to_pool')
    @patch.object(VfxPlacer, '_create_timeline_vfx_clip')
    def test_place_vfx_with_track_allocation(self, mock_create_clip, mock_import):
        """Test track allocation when placing overlapping VFX."""
        # Setup mocks
        mock_timeline = MagicMock()
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        mock_import.return_value = MagicMock()
        mock_create_clip.side_effect = ["vfx_clip_001", "vfx_clip_002"]
        
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file1,
                "start_frames": 450,
                "end_frames": 600
            },
            {
                "segment_index": 2,
                "vfx_file_path": self.vfx_file2,
                "start_frames": 500,  # Overlaps with segment 1
                "end_frames": 700
            }
        ]
        
        result = self.placer.place_vfx_templates("timeline_123", segments)
        
        self.assertTrue(result.success)
        self.assertEqual(result.clips_placed, 2)
        self.assertEqual(sorted(result.tracks_used), [11, 12])  # Different tracks for overlap
    
    @patch.object(VfxPlacer, '_import_vfx_to_pool')
    def test_place_vfx_import_failure_continue(self, mock_import):
        """Test that import failure for one VFX doesn't stop others."""
        # Setup mocks
        mock_timeline = MagicMock()
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        mock_import.side_effect = [None, MagicMock()]  # First fails, second succeeds
        
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file1,
                "start_frames": 450,
                "end_frames": 600
            },
            {
                "segment_index": 2,
                "vfx_file_path": self.vfx_file2,
                "start_frames": 700,
                "end_frames": 800
            }
        ]
        
        with patch.object(self.placer, '_create_timeline_vfx_clip', return_value="vfx_clip_002"):
            result = self.placer.place_vfx_templates("timeline_123", segments)
        
        self.assertTrue(result.success)  # Partial success still counts
        self.assertEqual(result.clips_placed, 1)  # Only second one placed
    
    def test_progress_callback_invoked(self):
        """Test that progress callback is called during placement."""
        # Setup mocks
        mock_timeline = MagicMock()
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        
        progress_calls = []
        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))
        
        segments = [
            {
                "segment_index": 1,
                "vfx_file_path": self.vfx_file1,
                "start_frames": 450,
                "end_frames": 600
            }
        ]
        
        with patch.object(self.placer, '_import_vfx_to_pool', return_value=MagicMock()):
            with patch.object(self.placer, '_create_timeline_vfx_clip', return_value="vfx_clip_001"):
                result = self.placer.place_vfx_templates(
                    "timeline_123", 
                    segments, 
                    progress_callback=progress_callback
                )
        
        self.assertTrue(result.success)
        self.assertEqual(len(progress_calls), 1)
        self.assertEqual(progress_calls[0][0], 1)  # Current
        self.assertEqual(progress_calls[0][1], 1)  # Total


if __name__ == "__main__":
    unittest.main()
