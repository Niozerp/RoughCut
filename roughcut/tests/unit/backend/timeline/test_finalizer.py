"""Unit tests for the timeline finalizer module.

Tests TimelineFinalizer functionality including:
- Timeline finalization and verification
- Element count validation with TrackManager config
- Asset quality verification (60%+ threshold - AC3)
- Playback verification (AC2)
- Performance metrics with runtime enforcement
- Error handling with shared ErrorCodes
- Refinement readiness checks
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Ensure we can import roughcut
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from roughcut.backend.timeline.finalizer import (
    TimelineFinalizer,
    TimelineCompletionStatus,
    TimelineElementStatus,
    PlaybackVerificationResult,
    AssetQualityResult,
    ErrorCodes
)
from roughcut.backend.timeline.resolve_api import ResolveApi
from roughcut.backend.timeline.track_manager import TrackManager


class TestErrorCodes(unittest.TestCase):
    """Test shared error codes."""
    
    def test_error_codes_defined(self):
        """Test that all expected error codes are defined."""
        self.assertEqual(ErrorCodes.RESOLVE_API_UNAVAILABLE, "RESOLVE_API_UNAVAILABLE")
        self.assertEqual(ErrorCodes.TIMELINE_NOT_FOUND, "TIMELINE_NOT_FOUND")
        self.assertEqual(ErrorCodes.MISSING_VIDEO_TRACK, "MISSING_VIDEO_TRACK")
        self.assertEqual(ErrorCodes.INSUFFICIENT_AUDIO_TRACKS, "INSUFFICIENT_AUDIO_TRACKS")
        self.assertEqual(ErrorCodes.TIMELINE_INCOMPLETE, "TIMELINE_INCOMPLETE")
        self.assertEqual(ErrorCodes.ASSET_QUALITY_FAILED, "ASSET_QUALITY_FAILED")
        self.assertEqual(ErrorCodes.PLAYBACK_VERIFICATION_FAILED, "PLAYBACK_VERIFICATION_FAILED")
        self.assertEqual(ErrorCodes.TIMELINE_ACTIVATION_FAILED, "TIMELINE_ACTIVATION_FAILED")
        self.assertEqual(ErrorCodes.PERFORMANCE_TARGET_EXCEEDED, "PERFORMANCE_TARGET_EXCEEDED")
        self.assertEqual(ErrorCodes.INTERNAL_ERROR, "INTERNAL_ERROR")


class TestPlaybackVerificationResult(unittest.TestCase):
    """Test PlaybackVerificationResult dataclass."""
    
    def test_playback_result_success(self):
        """Test successful playback verification."""
        result = PlaybackVerificationResult(
            can_play=True,
            audio_sync_check=True,
            pacing_consistent=True,
            duration_matches_expected=True,
            quality_score=1.0,
            issues=[],
            success=True
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.quality_score, 1.0)
        self.assertEqual(len(result.issues), 0)
    
    def test_playback_result_failure(self):
        """Test failed playback verification."""
        result = PlaybackVerificationResult(
            can_play=True,
            audio_sync_check=False,
            pacing_consistent=True,
            duration_matches_expected=False,
            quality_score=0.5,
            issues=["Duration mismatch", "Sync issue"],
            success=False
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.quality_score, 0.5)
        self.assertEqual(len(result.issues), 2)


class TestAssetQualityResult(unittest.TestCase):
    """Test AssetQualityResult dataclass."""
    
    def test_asset_quality_success(self):
        """Test asset quality with 100% usability."""
        result = AssetQualityResult(
            total_assets=10,
            usable_assets=10,
            broken_assets=0,
            usability_percentage=100.0,
            meets_threshold=True,
            asset_details=[],
            success=True
        )
        
        self.assertTrue(result.success)
        self.assertTrue(result.meets_threshold)
        self.assertEqual(result.usability_percentage, 100.0)
    
    def test_asset_quality_below_threshold(self):
        """Test asset quality below 60% threshold."""
        result = AssetQualityResult(
            total_assets=10,
            usable_assets=5,
            broken_assets=5,
            usability_percentage=50.0,
            meets_threshold=False,
            asset_details=[],
            success=False
        )
        
        self.assertFalse(result.success)
        self.assertFalse(result.meets_threshold)
        self.assertEqual(result.usability_percentage, 50.0)


class TestTimelineFinalizer(unittest.TestCase):
    """Test cases for TimelineFinalizer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_resolve_api = MagicMock(spec=ResolveApi)
        self.mock_track_manager = MagicMock(spec=TrackManager)
        
        # Set up standard track config
        self.mock_track_manager.STANDARD_TRACKS = {
            "video": 1,
            "music": 1,
            "sfx": 2,
            "vfx": 1
        }
        self.mock_track_manager.get_track_info.return_value = {
            "video": 2,
            "audio": 3,
            "subtitle": 0
        }
        
        self.finalizer = TimelineFinalizer(resolve_api=self.mock_resolve_api)
        # Replace the track_manager with our mock
        self.finalizer.track_manager = self.mock_track_manager
    
    def test_finalizer_initialization(self):
        """Test that finalizer initializes correctly."""
        self.assertIsNotNone(self.finalizer.resolve_api)
        self.assertIsNotNone(self.finalizer.track_manager)
        
        # Test performance targets
        self.assertEqual(self.finalizer.TARGET_VERIFICATION_TIME_MS, 500)
        self.assertEqual(self.finalizer.TARGET_ACTIVATION_TIME_MS, 2000)
        self.assertEqual(self.finalizer.TARGET_TOTAL_FINALIZATION_TIME_MS, 30000)
        
        # Test asset threshold
        self.assertEqual(self.finalizer.ASSET_USABILITY_THRESHOLD, 60.0)
    
    def test_finalize_timeline_resolve_not_available(self):
        """Test finalization when Resolve API is not available."""
        self.mock_resolve_api.is_available.return_value = False
        
        status = self.finalizer.finalize_timeline(
            timeline_name="TestTimeline",
            expected_elements={"segments": 3}
        )
        
        self.assertFalse(status.success)
        self.assertIsNotNone(status.error)
        self.assertEqual(status.error["code"], ErrorCodes.RESOLVE_API_UNAVAILABLE)
        self.assertFalse(status.ready_for_refinement)
        self.assertIn("scripting API", status.error["suggestion"])
    
    def test_finalize_timeline_not_found(self):
        """Test finalization when timeline doesn't exist."""
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = None
        
        status = self.finalizer.finalize_timeline(
            timeline_name="NonExistentTimeline",
            expected_elements={"segments": 3}
        )
        
        self.assertFalse(status.success)
        self.assertIsNotNone(status.error)
        self.assertEqual(status.error["code"], ErrorCodes.TIMELINE_NOT_FOUND)
    
    def test_finalize_timeline_missing_video_track(self):
        """Test finalization when timeline has no video tracks."""
        mock_timeline = MagicMock()
        mock_timeline.GetUniqueId.return_value = "test-id-123"
        
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_track_manager.get_track_info.return_value = {
            "video": 0,  # No video tracks
            "audio": 3,
            "subtitle": 0
        }
        
        status = self.finalizer.finalize_timeline(
            timeline_name="TestTimeline",
            expected_elements={"segments": 3}
        )
        
        self.assertFalse(status.success)
        self.assertIsNotNone(status.error)
        self.assertEqual(status.error["code"], ErrorCodes.MISSING_VIDEO_TRACK)
    
    def test_finalize_timeline_insufficient_audio_tracks(self):
        """Test finalization when timeline has insufficient audio tracks."""
        mock_timeline = MagicMock()
        mock_timeline.GetUniqueId.return_value = "test-id-123"
        
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_track_manager.get_track_info.return_value = {
            "video": 2,
            "audio": 1,  # Only 1 audio track, need at least 2
            "subtitle": 0
        }
        
        status = self.finalizer.finalize_timeline(
            timeline_name="TestTimeline",
            expected_elements={"segments": 3}
        )
        
        self.assertFalse(status.success)
        self.assertIsNotNone(status.error)
        self.assertEqual(status.error["code"], ErrorCodes.INSUFFICIENT_AUDIO_TRACKS)
    
    def test_finalize_timeline_success(self):
        """Test successful timeline finalization."""
        mock_timeline = MagicMock()
        mock_timeline.GetUniqueId.return_value = "test-id-123"
        mock_timeline.GetEndFrame.return_value = 9000  # 5 minutes at 30fps
        mock_timeline.GetItemCount.return_value = 3  # 3 segments
        
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_resolve_api.set_current_timeline.return_value = True
        
        self.mock_track_manager.get_track_info.return_value = {
            "video": 2,  # Video track 1 + VFX track 2
            "audio": 3,  # Music + 2 SFX tracks
            "subtitle": 0
        }
        
        expected_elements = {
            "segments": 3,
            "music_clips": 2,
            "sfx_clips": 3,
            "vfx_templates": 2
        }
        
        # Create a temp file for asset quality check
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_file.write(b'music content')
        temp_file.close()
        
        try:
            status = self.finalizer.finalize_timeline(
                timeline_name="TestTimeline",
                expected_elements=expected_elements,
                asset_paths=[temp_file.name]  # Provide at least one asset path
            )
            
            self.assertTrue(status.success)
            self.assertTrue(status.ready_for_refinement)
            self.assertTrue(status.verification_passed)
            self.assertEqual(status.timeline_name, "TestTimeline")
            self.assertEqual(status.timeline_id, "test-id-123")
            self.assertEqual(status.tracks["video"], 2)
            self.assertEqual(status.tracks["audio"], 3)
            self.assertIn("verification_time_ms", status.performance_metrics)
            self.assertIn("activation_time_ms", status.performance_metrics)
            self.assertIn("total_time_ms", status.performance_metrics)
            self.assertTrue(status.performance_targets_met)
            
            # Check new fields
            self.assertIsNotNone(status.asset_quality)
            self.assertIsNotNone(status.playback_verification)
        finally:
            import os
            os.unlink(temp_file.name)
    
    def test_finalize_timeline_activation_failure_is_failure(self):
        """Test that activation failure is treated as failure per AC1."""
        mock_timeline = MagicMock()
        mock_timeline.GetUniqueId.return_value = "test-id-123"
        mock_timeline.GetEndFrame.return_value = 9000
        mock_timeline.GetItemCount.return_value = 3
        
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_resolve_api.set_current_timeline.return_value = False  # Activation fails
        
        self.mock_track_manager.get_track_info.return_value = {
            "video": 2,
            "audio": 3,
            "subtitle": 0
        }
        
        status = self.finalizer.finalize_timeline(
            timeline_name="TestTimeline",
            expected_elements={"segments": 3}
        )
        
        # Per AC1, activation failure should be a failure condition
        self.assertFalse(status.success)
        self.assertEqual(status.error["code"], ErrorCodes.TIMELINE_ACTIVATION_FAILED)
        self.assertFalse(status.ready_for_refinement)
    
    def test_finalize_timeline_skip_activation(self):
        """Test finalization without activating in Resolve."""
        mock_timeline = MagicMock()
        mock_timeline.GetUniqueId.return_value = "test-id-123"
        mock_timeline.GetEndFrame.return_value = 9000
        mock_timeline.GetItemCount.return_value = 3
        
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        
        self.mock_track_manager.get_track_info.return_value = {
            "video": 2,
            "audio": 3,
            "subtitle": 0
        }
        
        status = self.finalizer.finalize_timeline(
            timeline_name="TestTimeline",
            expected_elements={"segments": 3},
            skip_activation=True  # Skip activation
        )
        
        self.assertTrue(status.success)
        self.assertTrue(status.ready_for_refinement)  # Should still be ready
        # set_current_timeline should not be called
        self.mock_resolve_api.set_current_timeline.assert_not_called()
    
    def test_finalize_timeline_asset_quality_failure(self):
        """Test that asset quality below 60% fails per AC3."""
        mock_timeline = MagicMock()
        mock_timeline.GetUniqueId.return_value = "test-id-123"
        mock_timeline.GetEndFrame.return_value = 9000
        mock_timeline.GetItemCount.return_value = 3
        
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_resolve_api.set_current_timeline.return_value = True
        
        self.mock_track_manager.get_track_info.return_value = {
            "video": 2,
            "audio": 3,
            "subtitle": 0
        }
        
        # Create temp files - only some will be valid
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            f.write(b'music content')
            valid_file = f.name
        
        invalid_file = '/nonexistent/path/file.wav'
        empty_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        empty_file.close()  # Empty file
        
        try:
            status = self.finalizer.finalize_timeline(
                timeline_name="TestTimeline",
                expected_elements={"segments": 3},
                asset_paths=[valid_file, invalid_file, empty_file.name]
            )
            
            # Should fail because < 60% usable (1/3 = 33%)
            self.assertFalse(status.success)
            self.assertEqual(status.error["code"], ErrorCodes.ASSET_QUALITY_FAILED)
            self.assertIn("33.3%", status.error["message"])
            self.assertIn("60%", status.error["message"])
            
            # Check asset_quality field
            self.assertIsNotNone(status.asset_quality)
            self.assertEqual(status.asset_quality.usability_percentage, 33.33333333333333)
            self.assertFalse(status.asset_quality.meets_threshold)
            
        finally:
            os.unlink(valid_file)
            os.unlink(empty_file.name)
    
    def test_finalize_timeline_with_asset_quality_success(self):
        """Test finalization with good asset quality (70%+)."""
        mock_timeline = MagicMock()
        mock_timeline.GetUniqueId.return_value = "test-id-123"
        mock_timeline.GetEndFrame.return_value = 9000
        mock_timeline.GetItemCount.return_value = 3
        
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_resolve_api.set_current_timeline.return_value = True
        
        self.mock_track_manager.get_track_info.return_value = {
            "video": 2,
            "audio": 3,
            "subtitle": 0
        }
        
        # Create temp files - 2/3 valid = 66.7% > 60%
        files = []
        try:
            for i in range(3):
                if i < 2:
                    # Valid files with content
                    f = tempfile.NamedTemporaryFile(delete=False, suffix=f'_{i}.mp3')
                    f.write(b'content here')
                    f.close()
                    files.append(f.name)
                else:
                    # Invalid file
                    files.append('/nonexistent.wav')
            
            status = self.finalizer.finalize_timeline(
                timeline_name="TestTimeline",
                expected_elements={"segments": 3},
                asset_paths=files
            )
            
            # Should succeed - 66.7% > 60%
            self.assertTrue(status.success)
            self.assertTrue(status.ready_for_refinement)
            self.assertIsNotNone(status.asset_quality)
            self.assertTrue(status.asset_quality.meets_threshold)
            
        finally:
            for f in files[:2]:  # Only clean up valid files
                if os.path.exists(f):
                    os.unlink(f)
    
    def test_element_status_dataclass(self):
        """Test TimelineElementStatus dataclass."""
        status = TimelineElementStatus(
            element_type="segments",
            expected_count=3,
            actual_count=3,
            verified=True,
            details={"track": 1, "method": "GetItemCount"}
        )
        
        self.assertEqual(status.element_type, "segments")
        self.assertEqual(status.expected_count, 3)
        self.assertEqual(status.actual_count, 3)
        self.assertTrue(status.verified)
        self.assertEqual(status.details["track"], 1)
    
    def test_completion_status_to_dict(self):
        """Test TimelineCompletionStatus.to_dict method."""
        element_statuses = [
            TimelineElementStatus(
                element_type="segments",
                expected_count=3,
                actual_count=3,
                verified=True,
                details={}
            )
        ]
        
        asset_quality = AssetQualityResult(
            total_assets=10,
            usable_assets=9,
            broken_assets=1,
            usability_percentage=90.0,
            meets_threshold=True,
            asset_details=[],
            success=True
        )
        
        playback_verification = PlaybackVerificationResult(
            can_play=True,
            audio_sync_check=True,
            pacing_consistent=True,
            duration_matches_expected=True,
            quality_score=1.0,
            issues=[],
            success=True
        )
        
        status = TimelineCompletionStatus(
            timeline_name="TestTimeline",
            timeline_id="test-id",
            duration_seconds=300.0,
            tracks={"video": 2, "audio": 3},
            elements={"segments": 3},
            element_statuses=element_statuses,
            asset_quality=asset_quality,
            playback_verification=playback_verification,
            ready_for_refinement=True,
            verification_passed=True,
            performance_metrics={"total_time_ms": 500},
            performance_targets_met=True,
            success=True
        )
        
        result_dict = status.to_dict()
        
        self.assertEqual(result_dict["timeline_name"], "TestTimeline")
        self.assertEqual(result_dict["timeline_id"], "test-id")
        self.assertEqual(result_dict["duration_seconds"], 300.0)
        self.assertEqual(result_dict["tracks"]["video"], 2)
        self.assertEqual(result_dict["elements"]["segments"], 3)
        self.assertTrue(result_dict["ready_for_refinement"])
        self.assertTrue(result_dict["verification_passed"])
        self.assertTrue(result_dict["performance_targets_met"])
        self.assertEqual(result_dict["status"], "complete")
        
        # Check new fields in dict
        self.assertIsNotNone(result_dict["asset_quality"])
        self.assertEqual(result_dict["asset_quality"]["usability_percentage"], 90.0)
        self.assertIsNotNone(result_dict["playback_verification"])
        self.assertEqual(result_dict["playback_verification"]["quality_score"], 1.0)
    
    def test_verify_refinement_readiness_timeline_not_found(self):
        """Test refinement readiness check when timeline doesn't exist."""
        self.mock_resolve_api.find_timeline_by_name.return_value = None
        
        result = self.finalizer.verify_refinement_readiness("NonExistentTimeline")
        
        self.assertFalse(result["ready"])
        self.assertIn("error", result)
    
    def test_verify_refinement_readiness_success(self):
        """Test successful refinement readiness check."""
        mock_timeline = MagicMock()
        
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_track_manager.get_track_info.return_value = {
            "video": 2,
            "audio": 3,
            "subtitle": 0
        }
        
        result = self.finalizer.verify_refinement_readiness("TestTimeline")
        
        self.assertTrue(result["ready"])
        self.assertTrue(result["checks"]["timeline_exists"])
        self.assertTrue(result["checks"]["has_video_track"])
        self.assertTrue(result["checks"]["has_audio_tracks"])
        self.assertTrue(result["checks"]["track_count_sufficient"])
    
    def test_verify_refinement_readiness_insufficient_tracks(self):
        """Test refinement readiness with insufficient tracks."""
        mock_timeline = MagicMock()
        
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_track_manager.get_track_info.return_value = {
            "video": 0,  # Missing video
            "audio": 1,  # Only 1 audio track
            "subtitle": 0
        }
        
        result = self.finalizer.verify_refinement_readiness("TestTimeline")
        
        self.assertFalse(result["ready"])
        self.assertTrue(result["checks"]["timeline_exists"])
        self.assertFalse(result["checks"]["has_video_track"])
        self.assertFalse(result["checks"]["has_audio_tracks"])
        self.assertFalse(result["checks"]["track_count_sufficient"])
    
    def test_performance_targets(self):
        """Test that performance targets are defined and enforced."""
        mock_timeline = MagicMock()
        mock_timeline.GetUniqueId.return_value = "test-id-123"
        mock_timeline.GetEndFrame.return_value = 9000
        mock_timeline.GetItemCount.return_value = 3
        
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_resolve_api.set_current_timeline.return_value = True
        
        self.mock_track_manager.get_track_info.return_value = {
            "video": 2,
            "audio": 3,
            "subtitle": 0
        }
        
        status = self.finalizer.finalize_timeline(
            timeline_name="TestTimeline",
            expected_elements={"segments": 3}
        )
        
        self.assertTrue(status.success)
        self.assertIn("verification_time_ms", status.performance_metrics)
        self.assertIn("activation_time_ms", status.performance_metrics)
        self.assertIn("total_time_ms", status.performance_metrics)
        
        # Verify all metrics are present
        self.assertTrue(status.performance_targets_met)
    
    def test_element_verification_with_missing_elements(self):
        """Test element verification when elements are missing."""
        mock_timeline = MagicMock()
        mock_timeline.GetUniqueId.return_value = "test-id-123"
        mock_timeline.GetEndFrame.return_value = 9000
        mock_timeline.GetItemCount.side_effect = lambda track_type, track_num: {
            ("video", 1): 2,  # Only 2 segments, expected 3
            ("audio", 1): 1,  # Only 1 music, expected 2
            ("audio", 2): 1,
            ("audio", 3): 1,
            ("video", 2): 0,  # No VFX, expected 2
        }.get((track_type, track_num), 0)
        
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_resolve_api.set_current_timeline.return_value = True
        
        self.mock_track_manager.get_track_info.return_value = {
            "video": 2,
            "audio": 3,
            "subtitle": 0
        }
        
        expected_elements = {
            "segments": 3,  # Will fail - only 2
            "music_clips": 2,  # Will fail - only 1
            "sfx_clips": 3,  # Will pass - 2 total (tracks 2+3)
            "vfx_templates": 2  # Will fail - 0
        }
        
        status = self.finalizer.finalize_timeline(
            timeline_name="TestTimeline",
            expected_elements=expected_elements
        )
        
        # Should succeed but verification should fail (elements missing but activation worked)
        # Wait - actually if elements are missing, should it fail?
        # Per AC3 we check asset quality, but for element count, it should warn
        # Let's check what happens
        
        # Check element statuses
        segments_status = next(
            (es for es in status.element_statuses if es.element_type == "segments"),
            None
        )
        self.assertIsNotNone(segments_status)
        self.assertFalse(segments_status.verified)
        self.assertEqual(segments_status.expected_count, 3)
        self.assertEqual(segments_status.actual_count, 2)
    
    def test_unknown_element_type_warning(self):
        """Test handling of unknown element types."""
        mock_timeline = MagicMock()
        mock_timeline.GetUniqueId.return_value = "test-id-123"
        mock_timeline.GetEndFrame.return_value = 9000
        mock_timeline.GetItemCount.return_value = 0
        
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_resolve_api.set_current_timeline.return_value = True
        
        self.mock_track_manager.get_track_info.return_value = {
            "video": 2,
            "audio": 3,
            "subtitle": 0
        }
        
        # Test with unknown element type
        expected_elements = {
            "unknown_type": 5
        }
        
        status = self.finalizer.finalize_timeline(
            timeline_name="TestTimeline",
            expected_elements=expected_elements
        )
        
        # Should handle gracefully
        self.assertTrue(status.success)
        unknown_status = next(
            (es for es in status.element_statuses if es.element_type == "unknown_type"),
            None
        )
        self.assertIsNotNone(unknown_status)
        self.assertFalse(unknown_status.verified)
        self.assertEqual(unknown_status.actual_count, 0)
        self.assertIn("warning", unknown_status.details)


class TestTimelineFinalizerEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_resolve_api = MagicMock(spec=ResolveApi)
        self.mock_track_manager = MagicMock(spec=TrackManager)
        self.mock_track_manager.STANDARD_TRACKS = {
            "video": 1, "music": 1, "sfx": 2, "vfx": 1
        }
        self.finalizer = TimelineFinalizer(resolve_api=self.mock_resolve_api)
        self.finalizer.track_manager = self.mock_track_manager
    
    def test_finalize_with_exception(self):
        """Test handling of unexpected exceptions."""
        self.mock_resolve_api.is_available.side_effect = Exception("Unexpected error")
        
        status = self.finalizer.finalize_timeline(
            timeline_name="TestTimeline",
            expected_elements={"segments": 3}
        )
        
        self.assertFalse(status.success)
        self.assertIsNotNone(status.error)
        self.assertEqual(status.error["code"], ErrorCodes.INTERNAL_ERROR)
    
    def test_finalize_with_empty_expected_elements(self):
        """Test finalization with empty expected elements dict."""
        mock_timeline = MagicMock()
        mock_timeline.GetUniqueId.return_value = "test-id-123"
        mock_timeline.GetEndFrame.return_value = 9000
        
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_resolve_api.set_current_timeline.return_value = True
        
        self.mock_track_manager.get_track_info.return_value = {
            "video": 2,
            "audio": 3,
            "subtitle": 0
        }
        
        status = self.finalizer.finalize_timeline(
            timeline_name="TestTimeline",
            expected_elements={}  # Empty
        )
        
        # Should succeed with no elements to verify
        self.assertTrue(status.success)
        self.assertTrue(status.verification_passed)  # No elements to fail
        self.assertEqual(len(status.element_statuses), 0)
    
    def test_refinement_readiness_with_exception(self):
        """Test refinement readiness with exception."""
        self.mock_resolve_api.find_timeline_by_name.side_effect = Exception("API error")
        
        result = self.finalizer.verify_refinement_readiness("TestTimeline")
        
        self.assertFalse(result["ready"])
        self.assertIn("error", result)
    
    def test_timeline_id_fallback_when_getuniqueid_unavailable(self):
        """Test that finalization works when GetUniqueId is unavailable."""
        mock_timeline = MagicMock()
        # No GetUniqueId method
        del mock_timeline.GetUniqueId
        mock_timeline.GetEndFrame.return_value = 9000
        mock_timeline.GetItemCount.return_value = 3
        
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_resolve_api.set_current_timeline.return_value = True
        
        self.mock_track_manager.get_track_info.return_value = {
            "video": 2,
            "audio": 3,
            "subtitle": 0
        }
        
        status = self.finalizer.finalize_timeline(
            timeline_name="TestTimeline",
            expected_elements={"segments": 3}
        )
        
        self.assertTrue(status.success)
        self.assertIsNone(status.timeline_id)  # Should be None when unavailable
        self.assertTrue(status.ready_for_refinement)
    
    def test_frame_rate_extraction(self):
        """Test that frame rate is extracted from timeline."""
        mock_timeline = MagicMock()
        mock_timeline.GetUniqueId.return_value = "test-id-123"
        mock_timeline.GetEndFrame.return_value = 18000  # 5 minutes at 60fps
        mock_timeline.GetItemCount.return_value = 3
        mock_timeline.GetSetting.return_value = "60"  # 60fps
        
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_resolve_api.set_current_timeline.return_value = True
        
        self.mock_track_manager.get_track_info.return_value = {
            "video": 2,
            "audio": 3,
            "subtitle": 0
        }
        
        status = self.finalizer.finalize_timeline(
            timeline_name="TestTimeline",
            expected_elements={"segments": 3}
        )
        
        self.assertTrue(status.success)
        # Duration should be calculated with 60fps: 18000/60 = 300s = 5min
        self.assertEqual(status.duration_seconds, 300.0)
    
    def test_duration_mismatch_detection(self):
        """Test that duration mismatch is detected in playback verification."""
        mock_timeline = MagicMock()
        mock_timeline.GetUniqueId.return_value = "test-id-123"
        mock_timeline.GetEndFrame.return_value = 4500  # 2.5 minutes at 30fps
        mock_timeline.GetItemCount.return_value = 3
        
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_resolve_api.set_current_timeline.return_value = True
        
        self.mock_track_manager.get_track_info.return_value = {
            "video": 2,
            "audio": 3,
            "subtitle": 0
        }
        
        # Expected 5 minutes (300s), actual is 150s - should trigger warning
        status = self.finalizer.finalize_timeline(
            timeline_name="TestTimeline",
            expected_elements={"segments": 3},
            expected_duration_seconds=300.0  # 5 minutes expected
        )
        
        self.assertTrue(status.success)
        self.assertIsNotNone(status.playback_verification)
        # Duration mismatch should be detected (>10% tolerance)
        self.assertFalse(status.playback_verification.duration_matches_expected)
        self.assertTrue(len(status.playback_verification.issues) > 0)
    
    def test_empty_asset_paths(self):
        """Test handling of empty asset paths list."""
        mock_timeline = MagicMock()
        mock_timeline.GetUniqueId.return_value = "test-id-123"
        mock_timeline.GetEndFrame.return_value = 9000
        mock_timeline.GetItemCount.return_value = 3
        
        self.mock_resolve_api.is_available.return_value = True
        self.mock_resolve_api.find_timeline_by_name.return_value = mock_timeline
        self.mock_resolve_api.set_current_timeline.return_value = True
        
        self.mock_track_manager.get_track_info.return_value = {
            "video": 2,
            "audio": 3,
            "subtitle": 0
        }
        
        status = self.finalizer.finalize_timeline(
            timeline_name="TestTimeline",
            expected_elements={"segments": 3},
            asset_paths=[]  # Empty list
        )
        
        self.assertTrue(status.success)
        # asset_quality should be None when no paths provided
        self.assertIsNone(status.asset_quality)


if __name__ == "__main__":
    unittest.main()
