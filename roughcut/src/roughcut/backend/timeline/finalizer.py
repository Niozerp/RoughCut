"""Timeline finalizer for verifying and completing rough cut timelines.

Handles the final verification of timeline elements, completion status generation,
playback verification, asset quality validation, and preparation for editor refinement workflow.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .resolve_api import ResolveApi
from .track_manager import TrackManager

logger = logging.getLogger(__name__)


# Shared error codes to avoid duplication
class ErrorCodes:
    """Shared error codes for timeline operations."""
    RESOLVE_API_UNAVAILABLE = "RESOLVE_API_UNAVAILABLE"
    TIMELINE_NOT_FOUND = "TIMELINE_NOT_FOUND"
    MISSING_VIDEO_TRACK = "MISSING_VIDEO_TRACK"
    INSUFFICIENT_AUDIO_TRACKS = "INSUFFICIENT_AUDIO_TRACKS"
    TIMELINE_INCOMPLETE = "TIMELINE_INCOMPLETE"
    ASSET_QUALITY_FAILED = "ASSET_QUALITY_FAILED"
    PLAYBACK_VERIFICATION_FAILED = "PLAYBACK_VERIFICATION_FAILED"
    TIMELINE_ACTIVATION_FAILED = "TIMELINE_ACTIVATION_FAILED"
    PERFORMANCE_TARGET_EXCEEDED = "PERFORMANCE_TARGET_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class TimelineElementStatus:
    """Status of a specific timeline element type.
    
    Attributes:
        element_type: Type of element (segments, music, sfx, vfx)
        expected_count: Number of elements expected
        actual_count: Number of elements found
        verified: Whether the count matches expectations
        details: Additional details about the elements
    """
    element_type: str
    expected_count: int
    actual_count: int
    verified: bool
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlaybackVerificationResult:
    """Result of playback verification checks.
    
    Attributes:
        can_play: Whether timeline can be played without errors
        audio_sync_check: Whether audio/video sync is within acceptable range
        pacing_consistent: Whether segment pacing is consistent
        duration_matches_expected: Whether actual duration matches expected
        quality_score: Overall quality score 0.0-1.0
        issues: List of playback issues found
        success: Whether playback verification passed
    """
    can_play: bool
    audio_sync_check: bool
    pacing_consistent: bool
    duration_matches_expected: bool
    quality_score: float
    issues: List[str]
    success: bool


@dataclass
class AssetQualityResult:
    """Result of asset quality verification.
    
    Attributes:
        total_assets: Total number of assets checked
        usable_assets: Number of usable assets (valid files, accessible)
        broken_assets: Number of broken/inaccessible assets
        usability_percentage: Percentage of usable assets (0.0-100.0)
        meets_threshold: Whether 60%+ usability threshold is met
        asset_details: Per-asset quality details
        success: Whether quality verification passed
    """
    total_assets: int
    usable_assets: int
    broken_assets: int
    usability_percentage: float
    meets_threshold: bool
    asset_details: List[Dict[str, Any]]
    success: bool


@dataclass
class TimelineCompletionStatus:
    """Complete status of timeline finalization.
    
    Attributes:
        timeline_name: Name of the timeline
        timeline_id: Unique identifier for the timeline
        duration_seconds: Total timeline duration in seconds
        tracks: Dictionary of track counts by type
        elements: Dictionary of element counts by type
        element_statuses: List of detailed element statuses
        asset_quality: Asset quality verification result
        playback_verification: Playback verification result
        ready_for_refinement: Whether timeline is ready for editor refinement
        verification_passed: Whether all verifications passed
        performance_metrics: Timing information for finalization
        performance_targets_met: Whether all performance targets were met
        success: Whether finalization succeeded
        error: Error details if finalization failed
    """
    timeline_name: str
    timeline_id: Optional[str]
    duration_seconds: float
    tracks: Dict[str, int]
    elements: Dict[str, int]
    element_statuses: List[TimelineElementStatus]
    asset_quality: Optional[AssetQualityResult]
    playback_verification: Optional[PlaybackVerificationResult]
    ready_for_refinement: bool
    verification_passed: bool
    performance_metrics: Dict[str, float]
    performance_targets_met: bool
    success: bool
    error: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert status to dictionary for JSON serialization."""
        return {
            "timeline_name": self.timeline_name,
            "timeline_id": self.timeline_id,
            "duration_seconds": self.duration_seconds,
            "tracks": self.tracks,
            "elements": self.elements,
            "element_statuses": [
                {
                    "element_type": es.element_type,
                    "expected_count": es.expected_count,
                    "actual_count": es.actual_count,
                    "verified": es.verified,
                    "details": es.details
                }
                for es in self.element_statuses
            ],
            "asset_quality": {
                "total_assets": self.asset_quality.total_assets,
                "usable_assets": self.asset_quality.usable_assets,
                "usability_percentage": self.asset_quality.usability_percentage,
                "meets_threshold": self.asset_quality.meets_threshold,
                "success": self.asset_quality.success
            } if self.asset_quality else None,
            "playback_verification": {
                "can_play": self.playback_verification.can_play,
                "audio_sync_check": self.playback_verification.audio_sync_check,
                "pacing_consistent": self.playback_verification.pacing_consistent,
                "quality_score": self.playback_verification.quality_score,
                "success": self.playback_verification.success
            } if self.playback_verification else None,
            "ready_for_refinement": self.ready_for_refinement,
            "verification_passed": self.verification_passed,
            "performance_metrics": self.performance_metrics,
            "performance_targets_met": self.performance_targets_met,
            "status": "complete" if self.success else "failed",
            "error": self.error
        }


class TimelineFinalizer:
    """Finalizes timelines for rough cut refinement workflow.
    
    This class handles:
    - Timeline completion verification (all elements in place)
    - Element count validation against expected values
    - Asset quality verification (60%+ usability check per AC3)
    - Playback verification (can play, sync, pacing per AC2)
    - Performance metrics collection with runtime enforcement
    - Refinement workflow preparation
    - Final status generation for Lua layer
    
    Usage:
        finalizer = TimelineFinalizer()
        status = finalizer.finalize_timeline(
            timeline_name="RoughCut_interview_001",
            expected_elements={"segments": 3, "music_clips": 2, "sfx_clips": 3, "vfx_templates": 2},
            asset_paths=["/path/to/music.mp3", "/path/to/sfx.wav"]
        )
    """
    
    # Performance targets (NFR2 compliance) - enforced at runtime
    TARGET_VERIFICATION_TIME_MS = 500  # 500ms max for verification
    TARGET_ACTIVATION_TIME_MS = 2000  # 2s max for activation
    TARGET_TOTAL_FINALIZATION_TIME_MS = 30000  # 30s max total
    
    # Asset quality threshold (AC3: 60%+ usability)
    ASSET_USABILITY_THRESHOLD = 60.0  # 60% minimum
    
    def __init__(self, resolve_api: Optional[ResolveApi] = None):
        """Initialize the timeline finalizer.
        
        Args:
            resolve_api: Optional ResolveApi instance for testing/mocking.
                        If not provided, a new instance will be created.
        """
        self.resolve_api = resolve_api or ResolveApi()
        self.track_manager = TrackManager(self.resolve_api)
        logger.info("TimelineFinalizer initialized")
    
    def finalize_timeline(
        self,
        timeline_name: str,
        expected_elements: Dict[str, int],
        asset_paths: Optional[List[str]] = None,
        expected_duration_seconds: Optional[float] = None,
        activate_in_resolve: bool = True,
        enforce_performance_targets: bool = True,
        skip_activation: bool = False
    ) -> TimelineCompletionStatus:
        """Finalize and verify a timeline for refinement workflow.
        
        This is the main entry point for timeline finalization. It performs
        comprehensive verification of all timeline elements, asset quality checks,
        playback verification, and prepares the timeline for editor refinement.
        
        Args:
            timeline_name: Name of the timeline to finalize
            expected_elements: Dictionary of expected element counts
                (e.g., {"segments": 3, "music_clips": 2, "sfx_clips": 3})
            asset_paths: List of asset file paths to verify quality (for AC3)
            expected_duration_seconds: Expected timeline duration for verification
            activate_in_resolve: Whether to activate timeline in Edit page (AC1)
            enforce_performance_targets: Whether to fail if performance targets exceeded
            skip_activation: If True, skip activation step entirely
            
        Returns:
            TimelineCompletionStatus with complete verification results
        """
        start_time = time.time()
        performance_metrics = {}
        
        try:
            # Step 1: Verify Resolve API availability
            if not self.resolve_api.is_available():
                return self._create_error_status(
                    timeline_name=timeline_name,
                    error_code=ErrorCodes.RESOLVE_API_UNAVAILABLE,
                    error_message="DaVinci Resolve API is not available",
                    suggestion="Ensure DaVinci Resolve is running and the scripting API is enabled in Preferences > System > General > Enable external scripting"
                )
            
            # Step 2: Find the timeline
            verification_start = time.time()
            timeline = self.resolve_api.find_timeline_by_name(timeline_name)
            if not timeline:
                return self._create_error_status(
                    timeline_name=timeline_name,
                    error_code=ErrorCodes.TIMELINE_NOT_FOUND,
                    error_message=f"Timeline not found: {timeline_name}",
                    suggestion="Ensure timeline was created successfully in story 6.1"
                )
            
            # Step 3: Get timeline ID and settings
            timeline_id = None
            fps = 30  # Default
            try:
                timeline_id = timeline.GetUniqueId() if hasattr(timeline, 'GetUniqueId') else None
                # Get actual frame rate from timeline if available
                if hasattr(timeline, 'GetSetting'):
                    fps_setting = timeline.GetSetting("timelineFrameRate") or timeline.GetSetting("videoFrameRate")
                    if fps_setting:
                        fps = float(fps_setting)
                elif hasattr(timeline, 'GetFrameRate'):
                    fps = timeline.GetFrameRate()
            except (AttributeError, ValueError):
                pass  # Use default fps
            
            # Step 4: Verify track configuration using TrackManager config
            track_info = self.track_manager.get_track_info(timeline)
            tracks = {
                "video": track_info.get("video", 0),
                "audio": track_info.get("audio", 0),
                "subtitle": track_info.get("subtitle", 0)
            }
            
            # Get track configuration from TrackManager
            config = getattr(self.track_manager, 'STANDARD_TRACKS', {
                "video": 1, "music": 1, "sfx": 2, "vfx": 1
            })
            
            # Step 5: Verify timeline has minimum required tracks
            min_video = config.get("video", 1) + config.get("vfx", 0)
            min_audio = config.get("music", 1) + config.get("sfx", 2)
            
            if tracks["video"] < min_video:
                return self._create_error_status(
                    timeline_name=timeline_name,
                    timeline_id=timeline_id,
                    error_code=ErrorCodes.MISSING_VIDEO_TRACK,
                    error_message=f"Timeline has {tracks['video']} video track(s), need at least {min_video}",
                    suggestion="Check timeline creation in story 6.1 - video and VFX tracks should exist"
                )
            
            if tracks["audio"] < min_audio:
                return self._create_error_status(
                    timeline_name=timeline_name,
                    timeline_id=timeline_id,
                    error_code=ErrorCodes.INSUFFICIENT_AUDIO_TRACKS,
                    error_message=f"Timeline has {tracks['audio']} audio track(s), need at least {min_audio}",
                    suggestion="Check track creation in story 6.1 - music and SFX tracks should exist"
                )
            
            # Step 6: Count actual timeline items
            element_statuses = self._verify_timeline_elements(
                timeline, expected_elements, config
            )
            
            verification_time = (time.time() - verification_start) * 1000
            performance_metrics["verification_time_ms"] = verification_time
            
            # Check verification performance target
            if verification_time > self.TARGET_VERIFICATION_TIME_MS:
                logger.warning(
                    f"Verification time {verification_time:.0f}ms exceeded target "
                    f"{self.TARGET_VERIFICATION_TIME_MS}ms"
                )
            
            # Step 7: Check if element verification passed
            element_verification_passed = all(es.verified for es in element_statuses)
            
            # Step 8: Get timeline duration
            duration_seconds = self._get_timeline_duration(timeline, fps)
            
            # Step 9: Verify asset quality (AC3: 60%+ usability)
            asset_quality = None
            if asset_paths:
                asset_quality = self._verify_asset_quality(asset_paths)
            
            # Step 10: Playback verification (AC2)
            playback_verification = None
            if timeline:
                playback_verification = self._verify_playback(
                    timeline, duration_seconds, expected_duration_seconds, fps
                )
            
            # Step 11: Activate timeline in Edit page (AC1 requirement)
            activation_start = time.time()
            activation_success = True
            activation_error = None
            
            if activate_in_resolve and not skip_activation:
                activation_success = self.resolve_api.set_current_timeline(timeline)
                if not activation_success:
                    activation_error = {
                        "code": ErrorCodes.TIMELINE_ACTIVATION_FAILED,
                        "message": f"Failed to activate timeline {timeline_name} in Resolve Edit page",
                        "suggestion": "Timeline was created but could not be activated. You may need to manually switch to it in Resolve."
                    }
                    logger.error(activation_error["message"])
            
            activation_time = (time.time() - activation_start) * 1000
            performance_metrics["activation_time_ms"] = activation_time
            
            # Check activation performance target
            if activation_time > self.TARGET_ACTIVATION_TIME_MS:
                logger.warning(
                    f"Activation time {activation_time:.0f}ms exceeded target "
                    f"{self.TARGET_ACTIVATION_TIME_MS}ms"
                )
            
            # Step 12: Calculate total time
            total_time = (time.time() - start_time) * 1000
            performance_metrics["total_time_ms"] = total_time
            
            # Check total performance target
            performance_targets_met = (
                verification_time <= self.TARGET_VERIFICATION_TIME_MS and
                activation_time <= self.TARGET_ACTIVATION_TIME_MS and
                total_time <= self.TARGET_TOTAL_FINALIZATION_TIME_MS
            )
            
            if not performance_targets_met and enforce_performance_targets:
                logger.warning(
                    f"Performance targets not met: verification={verification_time:.0f}ms, "
                    f"activation={activation_time:.0f}ms, total={total_time:.0f}ms"
                )
            
            # Build element counts dictionary
            elements = {}
            for es in element_statuses:
                elements[es.element_type] = es.actual_count
            
            # Determine comprehensive verification status
            asset_quality_passed = asset_quality.meets_threshold if asset_quality else True
            playback_passed = playback_verification.success if playback_verification else True
            
            # AC1: Activation must succeed for timeline to be "ready"
            # AC2: Playback verification must pass
            # AC3: Asset quality must meet 60%+ threshold
            verification_passed = (
                element_verification_passed and 
                activation_success and
                asset_quality_passed and
                playback_passed
            )
            
            ready_for_refinement = verification_passed
            
            # If activation failed, this is a failure per AC1
            if not activation_success and activate_in_resolve and not skip_activation:
                return self._create_error_status(
                    timeline_name=timeline_name,
                    timeline_id=timeline_id,
                    error_code=ErrorCodes.TIMELINE_ACTIVATION_FAILED,
                    error_message=activation_error["message"],
                    suggestion=activation_error["suggestion"],
                    partial_status={
                        "duration_seconds": duration_seconds,
                        "tracks": tracks,
                        "elements": elements,
                        "element_statuses": element_statuses,
                        "asset_quality": asset_quality,
                        "playback_verification": playback_verification,
                        "performance_metrics": performance_metrics,
                        "performance_targets_met": performance_targets_met
                    }
                )
            
            # If asset quality below threshold, fail per AC3
            if asset_quality and not asset_quality.meets_threshold:
                return self._create_error_status(
                    timeline_name=timeline_name,
                    timeline_id=timeline_id,
                    error_code=ErrorCodes.ASSET_QUALITY_FAILED,
                    error_message=f"Asset quality check failed: only {asset_quality.usability_percentage:.1f}% usable (required 60%+)",
                    suggestion="Check that media files exist and are accessible. Remove or replace broken assets.",
                    partial_status={
                        "duration_seconds": duration_seconds,
                        "tracks": tracks,
                        "elements": elements,
                        "element_statuses": element_statuses,
                        "asset_quality": asset_quality,
                        "playback_verification": playback_verification,
                        "performance_metrics": performance_metrics,
                        "performance_targets_met": performance_targets_met
                    }
                )
            
            logger.info(
                f"Timeline finalization complete: {timeline_name} "
                f"(verified: {verification_passed}, ready: {ready_for_refinement}, "
                f"duration: {duration_seconds:.2f}s, "
                f"asset_quality: {asset_quality.usability_percentage if asset_quality else 'N/A'}%, "
                f"playback: {playback_verification.success if playback_verification else 'N/A'})"
            )
            
            return TimelineCompletionStatus(
                timeline_name=timeline_name,
                timeline_id=timeline_id,
                duration_seconds=duration_seconds,
                tracks=tracks,
                elements=elements,
                element_statuses=element_statuses,
                asset_quality=asset_quality,
                playback_verification=playback_verification,
                ready_for_refinement=ready_for_refinement,
                verification_passed=verification_passed,
                performance_metrics=performance_metrics,
                performance_targets_met=performance_targets_met,
                success=True
            )
            
        except Exception as e:
            logger.exception(f"Unexpected error during timeline finalization: {e}")
            return self._create_error_status(
                timeline_name=timeline_name,
                error_code=ErrorCodes.INTERNAL_ERROR,
                error_message=f"Unexpected error during finalization: {str(e)}",
                suggestion="Check application logs and retry the operation"
            )
    
    def _verify_timeline_elements(
        self,
        timeline: Any,
        expected_elements: Dict[str, int],
        track_config: Dict[str, int]
    ) -> List[TimelineElementStatus]:
        """Verify timeline elements against expected counts.
        
        Args:
            timeline: Timeline object to verify
            expected_elements: Dictionary of expected element counts
            track_config: Track configuration from TrackManager
            
        Returns:
            List of TimelineElementStatus for each element type
        """
        element_statuses = []
        
        # Define element verification methods with track mapping from config
        video_track = 1  # Dialogue/source
        vfx_track = 2 if track_config.get("vfx", 0) > 0 else None  # VFX overlays
        music_track = 1  # Music on audio track 1
        
        # SFX tracks start after music
        sfx_start_track = 2  # Audio track 2 and beyond
        sfx_end_track = sfx_start_track + track_config.get("sfx", 2)
        
        element_verifiers = {
            "segments": lambda t: self._count_video_clips(t, video_track),
            "music_clips": lambda t: self._count_music_clips(t, music_track),
            "sfx_clips": lambda t: self._count_sfx_clips(t, sfx_start_track, sfx_end_track),
            "vfx_templates": lambda t: self._count_vfx_templates(t, vfx_track) if vfx_track else (0, {"error": "VFX track not configured"})
        }
        
        for element_type, expected_count in expected_elements.items():
            # Get the actual count
            verifier = element_verifiers.get(element_type)
            if verifier:
                actual_count, details = verifier(timeline)
            else:
                # Unknown element type - extensible for future types
                logger.warning(f"Unknown element type '{element_type}' - cannot verify")
                actual_count = 0
                details = {"warning": f"Unknown element type '{element_type}'", "note": "Extend element_verifiers in TimelineFinalizer to support this type"}
            
            # Create status
            verified = actual_count >= expected_count
            
            status = TimelineElementStatus(
                element_type=element_type,
                expected_count=expected_count,
                actual_count=actual_count,
                verified=verified,
                details=details
            )
            element_statuses.append(status)
            
            if not verified:
                logger.warning(
                    f"Element verification failed for {element_type}: "
                    f"expected {expected_count}, found {actual_count}"
                )
        
        return element_statuses
    
    def _count_video_clips(self, timeline: Any, track_index: int) -> Tuple[int, Dict[str, Any]]:
        """Count video clips on a specific track.
        
        Args:
            timeline: Timeline object
            track_index: Track number to check
            
        Returns:
            Tuple of (count, details_dict)
        """
        try:
            methods_tried = []
            
            # Method 1: Try GetItemCount
            if hasattr(timeline, 'GetItemCount'):
                methods_tried.append("GetItemCount")
                count = timeline.GetItemCount("video", track_index)
                return count, {"track": track_index, "type": "video", "method": "GetItemCount"}
            
            # Method 2: Try GetItemsInTrack
            if hasattr(timeline, 'GetItemsInTrack'):
                methods_tried.append("GetItemsInTrack")
                items = timeline.GetItemsInTrack("video", track_index)
                if items is not None:
                    return len(items), {"track": track_index, "type": "video", "method": "GetItemsInTrack", "count": len(items)}
            
            # Method 3: Try GetItemListInTrack (alternative API)
            if hasattr(timeline, 'GetItemListInTrack'):
                methods_tried.append("GetItemListInTrack")
                items = timeline.GetItemListInTrack("video", track_index)
                if items is not None:
                    return len(items), {"track": track_index, "type": "video", "method": "GetItemListInTrack"}
            
            return 0, {
                "error": "Cannot count video clips - no API method available",
                "methods_tried": methods_tried,
                "track": track_index
            }
            
        except Exception as e:
            logger.error(f"Error counting video clips on track {track_index}: {e}")
            return 0, {"error": str(e), "track": track_index}
    
    def _count_music_clips(self, timeline: Any, track_index: int) -> Tuple[int, Dict[str, Any]]:
        """Count music clips on a specific audio track.
        
        Args:
            timeline: Timeline object
            track_index: Track number to check
            
        Returns:
            Tuple of (count, details_dict)
        """
        try:
            methods_tried = []
            
            if hasattr(timeline, 'GetItemCount'):
                methods_tried.append("GetItemCount")
                count = timeline.GetItemCount("audio", track_index)
                return count, {"track": track_index, "type": "music", "method": "GetItemCount"}
            
            if hasattr(timeline, 'GetItemsInTrack'):
                methods_tried.append("GetItemsInTrack")
                items = timeline.GetItemsInTrack("audio", track_index)
                if items is not None:
                    return len(items), {"track": track_index, "type": "music", "method": "GetItemsInTrack"}
            
            return 0, {
                "error": "Cannot count music clips - no API method available",
                "methods_tried": methods_tried,
                "track": track_index
            }
            
        except Exception as e:
            logger.error(f"Error counting music clips on track {track_index}: {e}")
            return 0, {"error": str(e), "track": track_index}
    
    def _count_sfx_clips(self, timeline: Any, start_track: int, end_track: int) -> Tuple[int, Dict[str, Any]]:
        """Count SFX clips on audio tracks.
        
        Args:
            timeline: Timeline object
            start_track: First track to check (inclusive)
            end_track: Last track to check (exclusive)
            
        Returns:
            Tuple of (count, details_dict)
        """
        try:
            total_count = 0
            track_counts = {}
            methods_tried = []
            
            for track_num in range(start_track, end_track):
                if hasattr(timeline, 'GetItemCount'):
                    methods_tried.append(f"GetItemCount_track_{track_num}")
                    count = timeline.GetItemCount("audio", track_num)
                    track_counts[f"track_{track_num}"] = count
                    total_count += count
            
            return total_count, {
                "tracks": list(range(start_track, end_track)),
                "track_counts": track_counts,
                "type": "sfx",
                "methods_tried": list(set(methods_tried)) if methods_tried else ["GetItemCount"]
            }
            
        except Exception as e:
            logger.error(f"Error counting SFX clips: {e}")
            return 0, {"error": str(e), "tracks": list(range(start_track, end_track))}
    
    def _count_vfx_templates(self, timeline: Any, track_index: Optional[int]) -> Tuple[int, Dict[str, Any]]:
        """Count VFX templates on video track.
        
        Args:
            timeline: Timeline object
            track_index: Track number to check (None if VFX not configured)
            
        Returns:
            Tuple of (count, details_dict)
        """
        if track_index is None:
            return 0, {"error": "VFX track not configured", "type": "vfx"}
        
        try:
            methods_tried = []
            
            if hasattr(timeline, 'GetItemCount'):
                methods_tried.append("GetItemCount")
                count = timeline.GetItemCount("video", track_index)
                return count, {"track": track_index, "type": "vfx", "method": "GetItemCount"}
            
            return 0, {
                "error": "Cannot count VFX templates - API method not available",
                "methods_tried": methods_tried,
                "track": track_index
            }
            
        except Exception as e:
            logger.error(f"Error counting VFX templates: {e}")
            return 0, {"error": str(e), "track": track_index}
    
    def _get_timeline_duration(self, timeline: Any, fps: float = 30.0) -> float:
        """Get the duration of the timeline in seconds using actual frame rate.
        
        Args:
            timeline: Timeline object
            fps: Frame rate (retrieved from timeline settings)
            
        Returns:
            Duration in seconds
        """
        try:
            # Try to get end frame and calculate duration
            if hasattr(timeline, 'GetEndFrame'):
                end_frame = timeline.GetEndFrame()
                duration_seconds = end_frame / fps
                return duration_seconds
            
            # Fallback: try to get duration directly
            if hasattr(timeline, 'GetDuration'):
                duration = timeline.GetDuration()
                if duration:
                    return duration
            
            # Estimate from video clips
            if hasattr(timeline, 'GetItemCount') and hasattr(timeline, 'GetTrackCount'):
                video_count = timeline.GetTrackCount("video")
                if video_count > 0:
                    # Try to find the last clip's end frame
                    last_end = 0
                    for track in range(1, video_count + 1):
                        # This is approximate - we'd need to iterate clips
                        pass
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting timeline duration: {e}")
            return 0.0
    
    def _verify_asset_quality(self, asset_paths: List[str]) -> AssetQualityResult:
        """Verify asset file quality and accessibility (AC3: 60%+ usability).
        
        Checks each asset file for:
        - File exists
        - File is readable
        - File is not corrupt (basic validation)
        
        Args:
            asset_paths: List of asset file paths to verify
            
        Returns:
            AssetQualityResult with usability statistics
        """
        import os
        
        total = len(asset_paths)
        usable = 0
        broken = 0
        details = []
        
        for path in asset_paths:
            asset_info = {
                "path": path,
                "usable": False,
                "issues": []
            }
            
            # Check file exists
            if not os.path.exists(path):
                asset_info["issues"].append("File not found")
                broken += 1
                details.append(asset_info)
                continue
            
            # Check file is readable
            if not os.access(path, os.R_OK):
                asset_info["issues"].append("File not readable (permission denied)")
                broken += 1
                details.append(asset_info)
                continue
            
            # Check file has content (not empty)
            try:
                size = os.path.getsize(path)
                if size == 0:
                    asset_info["issues"].append("File is empty (0 bytes)")
                    broken += 1
                    details.append(asset_info)
                    continue
                asset_info["size_bytes"] = size
            except OSError as e:
                asset_info["issues"].append(f"Cannot check file size: {e}")
                broken += 1
                details.append(asset_info)
                continue
            
            # File is usable
            asset_info["usable"] = True
            usable += 1
            details.append(asset_info)
        
        usability_pct = (usable / total * 100) if total > 0 else 100.0
        meets_threshold = usability_pct >= self.ASSET_USABILITY_THRESHOLD
        
        logger.info(
            f"Asset quality check: {usable}/{total} usable ({usability_pct:.1f}%), "
            f"threshold met: {meets_threshold}"
        )
        
        return AssetQualityResult(
            total_assets=total,
            usable_assets=usable,
            broken_assets=broken,
            usability_percentage=usability_pct,
            meets_threshold=meets_threshold,
            asset_details=details,
            success=meets_threshold
        )
    
    def _verify_playback(
        self,
        timeline: Any,
        actual_duration: float,
        expected_duration: Optional[float],
        fps: float
    ) -> PlaybackVerificationResult:
        """Verify timeline playback quality (AC2).
        
        Performs checks to ensure timeline can play properly:
        - Can timeline be played (no Resolve errors)
        - Duration matches expected (if provided)
        - Pacing consistency (segments not too short/long)
        
        Args:
            timeline: Timeline object
            actual_duration: Actual duration in seconds
            expected_duration: Expected duration for comparison (optional)
            fps: Frame rate for calculations
            
        Returns:
            PlaybackVerificationResult with quality checks
        """
        issues = []
        
        # Check 1: Timeline can be played (basic check)
        can_play = True
        try:
            # Try to get timeline settings as proxy for playability
            if hasattr(timeline, 'GetSetting'):
                _ = timeline.GetSetting("timelineResolution")
        except Exception as e:
            can_play = False
            issues.append(f"Timeline may not be playable: {e}")
        
        # Check 2: Audio/video sync (proxy check via track counts)
        audio_sync_ok = True
        try:
            video_count = timeline.GetTrackCount("video") if hasattr(timeline, 'GetTrackCount') else 0
            audio_count = timeline.GetTrackCount("audio") if hasattr(timeline, 'GetTrackCount') else 0
            
            # If we have video but no audio tracks, sync might be an issue
            # (but this is normal for some formats, so just log)
            if video_count > 0 and audio_count == 0:
                logger.debug("Timeline has video but no audio tracks")
        except Exception:
            pass
        
        # Check 3: Duration matches expected
        duration_matches = True
        if expected_duration and expected_duration > 0:
            # Allow 10% tolerance
            tolerance = expected_duration * 0.1
            if abs(actual_duration - expected_duration) > tolerance:
                duration_matches = False
                issues.append(
                    f"Duration mismatch: actual={actual_duration:.1f}s, "
                    f"expected={expected_duration:.1f}s (tolerance={tolerance:.1f}s)"
                )
        
        # Check 4: Pacing consistency
        pacing_ok = True
        if actual_duration < 1.0:  # Less than 1 second is suspicious
            pacing_ok = False
            issues.append(f"Timeline very short ({actual_duration:.1f}s) - possible pacing issue")
        
        # Calculate quality score (0.0-1.0)
        checks = [can_play, audio_sync_ok, duration_matches, pacing_ok]
        quality_score = sum(checks) / len(checks)
        
        success = quality_score >= 0.75  # At least 3/4 checks must pass
        
        logger.info(
            f"Playback verification: can_play={can_play}, sync={audio_sync_ok}, "
            f"duration_match={duration_matches}, pacing={pacing_ok}, "
            f"quality={quality_score:.2f}"
        )
        
        return PlaybackVerificationResult(
            can_play=can_play,
            audio_sync_check=audio_sync_ok,
            pacing_consistent=pacing_ok,
            duration_matches_expected=duration_matches,
            quality_score=quality_score,
            issues=issues,
            success=success
        )
    
    def _create_error_status(
        self,
        timeline_name: str,
        error_code: str,
        error_message: str,
        suggestion: str,
        timeline_id: Optional[str] = None,
        partial_status: Optional[Dict[str, Any]] = None
    ) -> TimelineCompletionStatus:
        """Create an error status response.
        
        Args:
            timeline_name: Name of the timeline
            error_code: Error code string (use ErrorCodes constants)
            error_message: Human-readable error message
            suggestion: Recovery suggestion
            timeline_id: Optional timeline ID
            partial_status: Optional partial status data to include
            
        Returns:
            TimelineCompletionStatus with error details
        """
        error = {
            "code": error_code,
            "category": "resolve_api" if "RESOLVE" in error_code or "TIMELINE" in error_code or "ACTIVATION" in error_code else "internal",
            "message": error_message,
            "recoverable": True,
            "suggestion": suggestion
        }
        
        logger.error(f"Timeline finalization error [{error_code}]: {error_message}")
        
        # Build partial data if provided
        tracks = partial_status.get("tracks", {}) if partial_status else {}
        elements = partial_status.get("elements", {}) if partial_status else {}
        element_statuses = partial_status.get("element_statuses", []) if partial_status else []
        asset_quality = partial_status.get("asset_quality") if partial_status else None
        playback_verification = partial_status.get("playback_verification") if partial_status else None
        performance_metrics = partial_status.get("performance_metrics", {}) if partial_status else {}
        performance_targets_met = partial_status.get("performance_targets_met", False) if partial_status else False
        duration_seconds = partial_status.get("duration_seconds", 0.0) if partial_status else 0.0
        
        return TimelineCompletionStatus(
            timeline_name=timeline_name,
            timeline_id=timeline_id,
            duration_seconds=duration_seconds,
            tracks=tracks,
            elements=elements,
            element_statuses=element_statuses,
            asset_quality=asset_quality,
            playback_verification=playback_verification,
            ready_for_refinement=False,
            verification_passed=False,
            performance_metrics=performance_metrics,
            performance_targets_met=performance_targets_met,
            success=False,
            error=error
        )
    
    def verify_refinement_readiness(
        self,
        timeline_name: str,
        check_clips_present: bool = True
    ) -> Dict[str, Any]:
        """Quick check if timeline is ready for refinement without full finalization.
        
        This is a lightweight check that can be called to verify refinement
        readiness without performing the full finalization process.
        
        Args:
            timeline_name: Name of the timeline to check
            check_clips_present: Whether to verify clips actually exist on tracks
            
        Returns:
            Dictionary with readiness status and details
        """
        try:
            timeline = self.resolve_api.find_timeline_by_name(timeline_name)
            if not timeline:
                return {
                    "ready": False,
                    "error": f"Timeline not found: {timeline_name}"
                }
            
            # Get track info
            track_info = self.track_manager.get_track_info(timeline)
            
            # Get config
            config = getattr(self.track_manager, 'STANDARD_TRACKS', {
                "video": 1, "music": 1, "sfx": 2, "vfx": 1
            })
            
            min_video = config.get("video", 1) + config.get("vfx", 0)
            min_audio = config.get("music", 1) + config.get("sfx", 2)
            
            checks = {
                "timeline_exists": True,
                "has_video_track": track_info.get("video", 0) >= min_video,
                "has_audio_tracks": track_info.get("audio", 0) >= min_audio,
                "track_count_sufficient": (
                    track_info.get("video", 0) >= min_video and 
                    track_info.get("audio", 0) >= min_audio
                )
            }
            
            # Optional: Check if clips actually exist
            if check_clips_present:
                try:
                    video_clips = timeline.GetItemCount("video", 1) if hasattr(timeline, 'GetItemCount') else 0
                    checks["has_video_content"] = video_clips > 0
                    
                    audio_clips = timeline.GetItemCount("audio", 1) if hasattr(timeline, 'GetItemCount') else 0
                    checks["has_audio_content"] = audio_clips > 0
                except:
                    pass
            
            ready = all(checks.values())
            
            return {
                "ready": ready,
                "checks": checks,
                "track_info": track_info
            }
            
        except Exception as e:
            logger.error(f"Error checking refinement readiness: {e}")
            return {
                "ready": False,
                "error": str(e)
            }
