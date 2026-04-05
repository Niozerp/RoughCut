"""Track manager for Resolve timeline track operations.

Handles creation and management of timeline tracks including
video, audio (music/SFX), and VFX tracks.
"""

import logging
from typing import Any, Dict, List, Optional

from .resolve_api import ResolveApi

logger = logging.getLogger(__name__)


class TrackManager:
    """Manages track creation and configuration for timelines.
    
    This class handles the creation of the standard track layout:
    - Video/Dialogue track for source footage
    - Music track(s) for background audio
    - SFX tracks (separate for volume flexibility)
    - VFX/Fusion track for templates and effects
    
    Usage:
        api = ResolveApi()
        manager = TrackManager(api)
        timeline = api.create_timeline("MyTimeline")
        manager.create_standard_tracks(timeline)
    """
    
    # Track type constants
    TRACK_VIDEO = "video"
    TRACK_AUDIO = "audio"
    TRACK_SUBTITLE = "subtitle"
    
    # Standard track configuration
    STANDARD_TRACKS = {
        "video": 1,    # Dialogue/source footage
        "music": 1,    # Background music (audio track 1)
        "sfx": 2,      # Sound effects (audio tracks 2-3)
        "vfx": 1       # VFX/Fusion (video track 2 for overlays)
    }
    
    def __init__(self, resolve_api: ResolveApi):
        """Initialize the track manager.
        
        Args:
            resolve_api: ResolveApi instance for API operations
        """
        self.resolve_api = resolve_api
        logger.debug("TrackManager initialized")
    
    def create_standard_tracks(
        self,
        timeline: Any,
        track_config: Optional[Dict[str, int]] = None
    ) -> Dict[str, int]:
        """Create the standard track layout for a timeline.
        
        Creates tracks in the proper order:
        1. Video/Dialogue track
        2. Music track (audio)
        3. SFX tracks (audio)
        4. VFX track (video for overlays)
        
        Args:
            timeline: Timeline object to add tracks to
            track_config: Optional custom track configuration
            
        Returns:
            Dictionary with track counts by type
        """
        config = track_config or self.STANDARD_TRACKS
        tracks_created = {}
        
        logger.info(f"Creating standard tracks for timeline: {timeline.GetName()}")
        
        # Track 1: Video/Dialogue track (Resolve creates this by default)
        # We'll add an additional video track for VFX if needed
        video_count = config.get("video", 1) + config.get("vfx", 0) - 1
        if video_count > 0:
            tracks_created["video"] = self._add_video_tracks(timeline, video_count)
        else:
            tracks_created["video"] = 1  # Default track always exists
        
        # Audio tracks: Music + SFX
        music_count = config.get("music", 1)
        sfx_count = config.get("sfx", 2)
        total_audio = music_count + sfx_count
        
        if total_audio > 1:  # Resolve creates first audio track by default
            audio_to_add = total_audio - 1
            tracks_created["audio"] = self._add_audio_tracks(timeline, audio_to_add)
        else:
            tracks_created["audio"] = 1  # Default track always exists
        
        logger.info(
            f"Track creation complete: {tracks_created['video']} video, "
            f"{tracks_created['audio']} audio"
        )
        
        return tracks_created
    
    def _add_video_tracks(self, timeline: Any, count: int) -> int:
        """Add video tracks to timeline.
        
        Args:
            timeline: Timeline object
            count: Number of additional video tracks to add
            
        Returns:
            Total number of video tracks after operation
        """
        if count <= 0:
            return self.resolve_api.get_timeline_track_count(timeline, "video")
        
        logger.debug(f"Adding {count} video tracks")
        added = 0
        
        for i in range(count):
            if self.resolve_api.add_track(timeline, self.TRACK_VIDEO):
                added += 1
                logger.debug(f"Added video track {i + 1}")
            else:
                logger.warning(f"Failed to add video track {i + 1}")
        
        total = self.resolve_api.get_timeline_track_count(timeline, "video")
        logger.info(f"Video tracks: {total} total ({added} added)")
        
        return total
    
    def _add_audio_tracks(self, timeline: Any, count: int) -> int:
        """Add audio tracks to timeline.
        
        Args:
            timeline: Timeline object
            count: Number of additional audio tracks to add
            
        Returns:
            Total number of audio tracks after operation
        """
        if count <= 0:
            return self.resolve_api.get_timeline_track_count(timeline, "audio")
        
        logger.debug(f"Adding {count} audio tracks")
        added = 0
        
        for i in range(count):
            if self.resolve_api.add_track(timeline, self.TRACK_AUDIO):
                added += 1
                logger.debug(f"Added audio track {i + 1}")
            else:
                logger.warning(f"Failed to add audio track {i + 1}")
        
        total = self.resolve_api.get_timeline_track_count(timeline, "audio")
        logger.info(f"Audio tracks: {total} total ({added} added)")
        
        return total
    
    def get_track_info(self, timeline: Any) -> Dict[str, Any]:
        """Get information about all tracks in a timeline.
        
        Args:
            timeline: Timeline object
            
        Returns:
            Dictionary with track counts and details
        """
        if not timeline:
            return {"video": 0, "audio": 0, "subtitle": 0}
        
        return {
            "video": self.resolve_api.get_timeline_track_count(timeline, "video"),
            "audio": self.resolve_api.get_timeline_track_count(timeline, "audio"),
            "subtitle": self.resolve_api.get_timeline_track_count(timeline, "subtitle")
        }
    
    def configure_track_names(self, timeline: Any, track_config: Optional[Dict[str, int]] = None) -> bool:
        """Configure track names for better organization.
        
        Note: Resolve's API has limited support for track naming.
        This method documents the intended track layout.
        
        Args:
            timeline: Timeline object
            track_config: Track configuration used
            
        Returns:
            True (naming is informational)
        """
        config = track_config or self.STANDARD_TRACKS
        
        # Log the track layout for documentation
        logger.info("Track layout configuration:")
        logger.info(f"  Video Track 1: Dialogue/Source Footage")
        
        if config.get("vfx", 0) > 0:
            logger.info(f"  Video Track 2: VFX/Templates")
        
        logger.info(f"  Audio Track 1: Music")
        
        for i in range(1, config.get("sfx", 2) + 1):
            logger.info(f"  Audio Track {i + 1}: SFX {i}")
        
        return True
    
    def verify_track_setup(
        self,
        timeline: Any,
        expected_config: Optional[Dict[str, int]] = None
    ) -> bool:
        """Verify that the timeline has the expected track configuration.
        
        Args:
            timeline: Timeline object
            expected_config: Expected track configuration
            
        Returns:
            True if track setup matches expectations
        """
        config = expected_config or self.STANDARD_TRACKS
        
        # Calculate expected totals
        expected_video = config.get("video", 1) + config.get("vfx", 0)
        expected_audio = config.get("music", 1) + config.get("sfx", 2)
        
        # Get actual counts
        actual_video = self.resolve_api.get_timeline_track_count(timeline, "video")
        actual_audio = self.resolve_api.get_timeline_track_count(timeline, "audio")
        
        # Verify
        video_ok = actual_video >= expected_video
        audio_ok = actual_audio >= expected_audio
        
        if not video_ok:
            logger.warning(
                f"Video track mismatch: expected {expected_video}, got {actual_video}"
            )
        
        if not audio_ok:
            logger.warning(
                f"Audio track mismatch: expected {expected_audio}, got {actual_audio}"
            )
        
        return video_ok and audio_ok
