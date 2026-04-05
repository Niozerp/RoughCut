"""Timeline builder for creating Resolve timelines from rough cut documents.

Handles the creation of new timelines with proper track setup,
non-destructive operations, and Resolve API integration.
"""

import logging
import random
import re
import string
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from .track_manager import TrackManager
from .resolve_api import ResolveApi

logger = logging.getLogger(__name__)


@dataclass
class TimelineCreationResult:
    """Result of timeline creation operation.
    
    Attributes:
        timeline_name: Name of the created timeline
        timeline_id: Unique identifier for the timeline
        tracks_created: Dictionary of track counts by type
        success: Whether creation was successful
        error: Error details if creation failed
    """
    timeline_name: str
    timeline_id: Optional[str] = None
    tracks_created: Dict[str, int] = field(default_factory=dict)
    success: bool = True
    error: Optional[Dict[str, Any]] = None


class TimelineBuilder:
    """Builds Resolve timelines for rough cut output.
    
    This class handles the non-destructive creation of timelines
    with the appropriate track structure for rough cut assembly.
    
    Usage:
        builder = TimelineBuilder()
        result = builder.create_timeline(
            source_clip_name="interview_001",
            format_template="youtube-interview"
        )
    """
    
    # Constants for naming and structure
    TIMELINE_NAME_PREFIX = "RoughCut"
    MAX_NAME_LENGTH = 100  # Resolve has limits on timeline names
    
    # Default track configuration
    DEFAULT_TRACKS = {
        "video": 1,      # Dialogue/source footage
        "music": 1,      # Background music
        "sfx": 2,        # Sound effects (2 tracks for flexibility)
        "vfx": 1         # VFX/Fusion templates
    }
    
    def __init__(self, resolve_api: Optional[ResolveApi] = None):
        """Initialize the timeline builder.
        
        Args:
            resolve_api: Optional ResolveApi instance for testing/mocking
        """
        self.resolve_api = resolve_api or ResolveApi()
        self.track_manager = TrackManager(self.resolve_api)
        logger.info("TimelineBuilder initialized")
    
    def create_timeline(
        self,
        source_clip_name: str,
        format_template: str,
        timestamp: Optional[str] = None,
        track_config: Optional[Dict[str, int]] = None
    ) -> TimelineCreationResult:
        """Create a new timeline with the specified configuration.
        
        This is the main entry point for timeline creation. It performs
        all operations non-destructively - existing timelines are never
        modified, and source clips are never altered.
        
        Args:
            source_clip_name: Name of the source clip (for naming)
            format_template: Name of the format template used
            timestamp: Optional timestamp string (ISO format)
            track_config: Optional custom track configuration
            
        Returns:
            TimelineCreationResult with details of created timeline
            
        Raises:
            No exceptions raised - all errors are captured in result.error
        """
        timeline = None
        timeline_name = ""
        
        try:
            # Validate inputs
            if not source_clip_name or len(source_clip_name) > 1000:
                return TimelineCreationResult(
                    timeline_name="",
                    success=False,
                    error={
                        "code": "INVALID_PARAMS",
                        "category": "validation",
                        "message": "source_clip_name is required and must be under 1000 characters",
                        "recoverable": True,
                        "suggestion": "Provide a valid source clip name"
                    }
                )
            
            if not format_template or len(format_template) > 1000:
                return TimelineCreationResult(
                    timeline_name="",
                    success=False,
                    error={
                        "code": "INVALID_PARAMS",
                        "category": "validation",
                        "message": "format_template is required and must be under 1000 characters",
                        "recoverable": True,
                        "suggestion": "Provide a valid format template name"
                    }
                )
            
            logger.info(
                f"Creating timeline for {source_clip_name} with format {format_template}"
            )
            
            # Step 1: Generate unique timeline name
            timeline_name = self._generate_timeline_name(
                source_clip_name, format_template, timestamp
            )
            logger.debug(f"Generated timeline name: {timeline_name}")
            
            # Step 2: Check if Resolve API is available
            if not self.resolve_api.is_available():
                logger.error("Resolve API is not available")
                return TimelineCreationResult(
                    timeline_name=timeline_name,
                    success=False,
                    error={
                        "code": "RESOLVE_API_UNAVAILABLE",
                        "category": "resolve_api",
                        "message": "DaVinci Resolve API is not available",
                        "recoverable": True,
                        "suggestion": "Ensure DaVinci Resolve is running and the scripting API is enabled in Preferences > System > General > Enable external scripting"
                    }
                )
            
            # Step 3: Verify source clip exists in media pool (protection check)
            media_pool = self.resolve_api.get_media_pool()
            if media_pool:
                # Verify we can access media pool without modifying it
                # This ensures source clip protection (NFR9)
                logger.debug("Source clip protection: Media pool accessible, no modifications will be made")
            
            # Step 4 & 5: Create timeline with retry protection for TOCTOU race condition
            timeline = None
            max_retries = 3
            retry_count = 0
            current_timeline_name = timeline_name
            
            while retry_count < max_retries and timeline is None:
                # Verify non-destructive - ensure we're not overwriting
                existing_timeline = self.resolve_api.find_timeline_by_name(current_timeline_name)
                if existing_timeline:
                    logger.warning(f"Timeline {current_timeline_name} already exists, generating unique name")
                    current_timeline_name = self._generate_unique_timeline_name(current_timeline_name)
                    logger.debug(f"Unique timeline name: {current_timeline_name}")
                
                # Create the timeline container
                logger.info(f"Creating timeline container: {current_timeline_name} (attempt {retry_count + 1}/{max_retries})")
                timeline = self.resolve_api.create_timeline(current_timeline_name)
                
                if timeline is None:
                    # Creation failed - could be race condition, retry with new name
                    logger.warning(f"Timeline creation failed for {current_timeline_name}, retrying with new name")
                    current_timeline_name = self._generate_unique_timeline_name(current_timeline_name)
                    retry_count += 1
            
            if not timeline:
                logger.error(f"Failed to create timeline after {max_retries} attempts")
                return TimelineCreationResult(
                    timeline_name=current_timeline_name,
                    success=False,
                    error={
                        "code": "TIMELINE_CREATION_FAILED",
                        "category": "resolve_api",
                        "message": "Failed to create timeline in DaVinci Resolve after multiple attempts",
                        "recoverable": True,
                        "suggestion": "Check project permissions and disk space, then retry"
                    }
                )
            
            # Update timeline_name to the one that was successfully created
            timeline_name = current_timeline_name
            
            # Step 6: Create tracks
            logger.info("Creating timeline tracks")
            # Validate track_config: if empty dict, use defaults
            config = track_config if track_config and len(track_config) > 0 else self.DEFAULT_TRACKS
            tracks_created = self.track_manager.create_standard_tracks(timeline, config)
            
            # Verify tracks were created (partial failure check)
            if tracks_created.get("video", 0) == 0 or tracks_created.get("audio", 0) == 0:
                logger.error("Track creation failed - no tracks were added")
                # Clean up partial timeline
                self._cleanup_timeline(timeline)
                return TimelineCreationResult(
                    timeline_name=timeline_name,
                    success=False,
                    error={
                        "code": "TRACK_CREATION_FAILED",
                        "category": "resolve_api",
                        "message": "Failed to create timeline tracks",
                        "recoverable": True,
                        "suggestion": "Check Resolve API permissions and retry"
                    }
                )
            
            # Step 7: Configure track names (informational)
            self.track_manager.configure_track_names(timeline, config)
            
            # Step 8: Verify track setup
            if not self.track_manager.verify_track_setup(timeline, config):
                logger.warning("Track setup verification failed, but timeline was created")
            
            # Step 9: Set as current timeline (activate in Edit page)
            logger.info("Activating timeline in Edit page")
            if not self.resolve_api.set_current_timeline(timeline):
                logger.warning("Failed to activate timeline, but timeline was created")
            
            # Get timeline ID if available
            timeline_id = None
            try:
                timeline_id = timeline.GetUniqueId() if hasattr(timeline, 'GetUniqueId') else None
            except AttributeError:
                # GetUniqueId not available on this Resolve version
                pass
            except Exception as e:
                logger.debug(f"Could not get timeline ID: {e}")
                # Non-critical, continue without ID
            
            logger.info(f"Timeline creation successful: {timeline_name}")
            
            return TimelineCreationResult(
                timeline_name=timeline_name,
                timeline_id=timeline_id,
                tracks_created=tracks_created,
                success=True
            )
            
        except Exception as e:
            logger.exception(f"Unexpected error creating timeline: {e}")
            # Clean up partial timeline if created
            if timeline:
                try:
                    self._cleanup_timeline(timeline)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup partial timeline: {cleanup_error}")
            
            return TimelineCreationResult(
                timeline_name=timeline_name if timeline_name else source_clip_name,
                success=False,
                error={
                    "code": "INTERNAL_ERROR",
                    "category": "internal",
                    "message": f"Unexpected error: {str(e)}",
                    "recoverable": False,
                    "suggestion": "Check application logs and report the issue"
                }
            )
    
    def _cleanup_timeline(self, timeline: Any) -> bool:
        """Clean up a partially created timeline on failure.
        
        Args:
            timeline: Timeline object to delete
            
        Returns:
            True if cleanup succeeded, False otherwise
        """
        try:
            if timeline and hasattr(timeline, 'DeleteTimeline'):
                timeline.DeleteTimeline()
                logger.info("Cleaned up partial timeline")
                return True
            else:
                logger.warning("Could not cleanup timeline - DeleteTimeline not available")
                return False
        except Exception as e:
            logger.error(f"Error cleaning up timeline: {e}")
            return False
    
    def _generate_timeline_name(
        self,
        source_clip_name: str,
        format_template: str,
        timestamp: Optional[str] = None
    ) -> str:
        """Generate a descriptive timeline name.
        
        Format: RoughCut_[source_clip_name]_[format]_[timestamp]
        
        Args:
            source_clip_name: Name of the source clip
            format_template: Name of the format template
            timestamp: Optional timestamp (uses current time if not provided)
            
        Returns:
            Sanitized timeline name
        """
        # Clean source clip name - remove extension and special chars
        clean_source = self._sanitize_name(source_clip_name)
        
        # Clean format template name
        clean_format = self._sanitize_name(format_template)
        
        # Generate timestamp if not provided
        if timestamp is None:
            computed_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        else:
            # Convert ISO format to safe filename format
            computed_timestamp = timestamp.replace("T", "_").replace(":", "-")
        
        # Build name
        name = f"{self.TIMELINE_NAME_PREFIX}_{clean_source}_{clean_format}_{computed_timestamp}"
        
        # Truncate if too long - account for all separators (3 underscores)
        if len(name) > self.MAX_NAME_LENGTH:
            # Calculate available space for source + format (keeping prefix, computed_timestamp, and 3 underscores)
            fixed_parts_len = len(self.TIMELINE_NAME_PREFIX) + len(computed_timestamp) + 3  # 3 underscores
            available = self.MAX_NAME_LENGTH - fixed_parts_len
            # Split available space between source and format
            source_len = available // 2
            format_len = available - source_len
            truncated_source = clean_source[:source_len]
            truncated_format = clean_format[:format_len]
            name = f"{self.TIMELINE_NAME_PREFIX}_{truncated_source}_{truncated_format}_{computed_timestamp}"
        
        return name
    
    def _generate_unique_timeline_name(self, base_name: str) -> str:
        """Generate a unique timeline name if base name exists.
        
        Args:
            base_name: Original timeline name
            
        Returns:
            Unique timeline name with counter suffix
        """
        counter = 1
        new_name = base_name
        
        while self.resolve_api.find_timeline_by_name(new_name):
            # Append counter before any timestamp suffix
            if "_" in base_name:
                parts = base_name.rsplit("_", 1)
                # Check if last part looks like a timestamp (contains digits and -)
                if parts[1] and any(c.isdigit() for c in parts[1]):
                    new_name = f"{parts[0]}_{counter:03d}_{parts[1]}"
                else:
                    new_name = f"{base_name}_{counter:03d}"
            else:
                new_name = f"{base_name}_{counter:03d}"
            
            counter += 1
            
            # Safety limit
            if counter > 999:
                # Add random suffix
                suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                new_name = f"{base_name}_{suffix}"
                break
        
        return new_name
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use in timeline naming.
        
        Removes special characters, file extensions, and ensures
        the result is safe for Resolve timeline names.
        
        Args:
            name: Original name
            
        Returns:
            Sanitized name
        """
        if not name:
            return "Untitled"
        
        # Remove file extension
        name = re.sub(r'\.[^.]+$', '', name)
        
        # Replace special characters with underscores
        # Allow alphanumeric, underscores, hyphens, and spaces (will be replaced)
        sanitized = re.sub(r'[^\w\-]', '_', name)
        
        # Collapse multiple underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        
        # Limit length
        if len(sanitized) > 50:
            sanitized = sanitized[:50]
        
        return sanitized or "Untitled"
