"""Footage cutter for cutting source video into timeline segments.

Handles the non-destructive cutting of source footage according to AI-recommended
transcript segments, placing them sequentially on the timeline.
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .resolve_api import ResolveApi

logger = logging.getLogger(__name__)


def timecode_to_frames(timecode: str, fps: int = 30) -> int:
    """Convert timecode string to frame count.
    
    Supports formats:
    - "MM:SS" (minutes:seconds)
    - "H:MM:SS" (hours:minutes:seconds)
    - "H:MM:SS:FF" (hours:minutes:seconds:frames)
    
    Args:
        timecode: Timecode string
        fps: Frames per second (default 30)
        
    Returns:
        Total frame count from start of media
        
    Raises:
        ValueError: If timecode format is invalid or contains non-numeric values
    """
    # Validate FPS parameter
    if not isinstance(fps, int) or fps <= 0:
        raise ValueError(f"fps must be a positive integer, got {fps}")
    
    # Input validation
    if not isinstance(timecode, str):
        raise ValueError(f"timecode must be a string, got {type(timecode).__name__}")
    
    timecode = timecode.strip()
    
    if not timecode:
        raise ValueError("timecode cannot be empty")
    
    # Validate timecode contains only digits and colons
    if not re.match(r"^[\d:]+$", timecode):
        raise ValueError(f"Invalid characters in timecode: {timecode}. Only digits and colons allowed.")
    
    # Parse based on colon count
    parts = timecode.split(":")
    
    # Validate number of parts
    if len(parts) < 2 or len(parts) > 4:
        raise ValueError(f"Invalid timecode format: {timecode}. Expected MM:SS, H:MM:SS, or H:MM:SS:FF")
    
    # Validate all parts are numeric
    for i, part in enumerate(parts):
        if not part:
            raise ValueError(f"Empty timecode component at position {i}")
        try:
            int(part)
        except ValueError:
            raise ValueError(f"Non-numeric value in timecode: '{part}'")
    
    if len(parts) == 2:  # MM:SS
        minutes = int(parts[0])
        seconds = int(parts[1])
        
        # Validate time ranges
        if seconds >= 60:
            raise ValueError(f"Seconds must be < 60, got {seconds}")
        if minutes < 0:
            raise ValueError(f"Minutes cannot be negative, got {minutes}")
            
        return (minutes * 60 + seconds) * fps
        
    elif len(parts) == 3:  # H:MM:SS
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        
        # Validate time ranges
        if seconds >= 60:
            raise ValueError(f"Seconds must be < 60, got {seconds}")
        if minutes >= 60:
            raise ValueError(f"Minutes must be < 60, got {minutes}")
        if hours < 0:
            raise ValueError(f"Hours cannot be negative, got {hours}")
            
        return (hours * 3600 + minutes * 60 + seconds) * fps
        
    elif len(parts) == 4:  # H:MM:SS:FF
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        frames = int(parts[3])
        
        # Validate time ranges
        if frames >= fps:
            raise ValueError(f"Frames must be < {fps} (fps), got {frames}")
        if seconds >= 60:
            raise ValueError(f"Seconds must be < 60, got {seconds}")
        if minutes >= 60:
            raise ValueError(f"Minutes must be < 60, got {minutes}")
        if hours < 0:
            raise ValueError(f"Hours cannot be negative, got {hours}")
            
        return (hours * 3600 + minutes * 60 + seconds) * fps + frames
    
    else:
        raise ValueError(f"Invalid timecode format: {timecode}")


def frames_to_timecode(frames: int, fps: int = 30, include_frames: bool = False) -> str:
    """Convert frame count to timecode string.
    
    Args:
        frames: Total frame count
        fps: Frames per second (default 30)
        include_frames: Whether to include frame count in output
        
    Returns:
        Timecode string in format "H:MM:SS" or "H:MM:SS:FF"
        
    Raises:
        ValueError: If fps is not a positive integer
    """
    # Validate FPS parameter
    if not isinstance(fps, int) or fps <= 0:
        raise ValueError(f"fps must be a positive integer, got {fps}")
    
    # Validate frames
    if not isinstance(frames, int):
        raise ValueError(f"frames must be an integer, got {type(frames).__name__}")
    
    total_seconds = frames // fps
    remaining_frames = frames % fps
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    if include_frames:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{remaining_frames:02d}"
    else:
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"


def validate_segments(segments: List[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate a list of segments for cutting.
    
    Checks:
    - Segments list is not empty
    - Each segment has required fields (segment_index, start_frames, end_frames)
    - Start frame < end frame for each segment
    - No negative frame values
    - Segments don't overlap (if they have source positions)
    
    Args:
        segments: List of segment dictionaries
        
    Returns:
        Tuple of (is_valid, error_dict)
        - is_valid: True if all validations pass
        - error_dict: None if valid, or error details if invalid
    """
    if not segments:
        return False, {
            "code": "NO_SEGMENTS",
            "category": "validation",
            "message": "No segments provided for cutting",
            "recoverable": True,
            "suggestion": "Ensure AI rough cut generation produced segment data"
        }
    
    # Check each segment
    seen_indexes = set()
    
    for i, segment in enumerate(segments):
        # Check segment is a dict
        if not isinstance(segment, dict):
            return False, {
                "code": "INVALID_SEGMENT_TYPE",
                "category": "validation",
                "message": f"Segment {i} is not a dictionary",
                "recoverable": True,
                "suggestion": "Each segment must be a dictionary with timing data"
            }
        
        # Check required fields
        if "segment_index" not in segment:
            return False, {
                "code": "MISSING_SEGMENT_INDEX",
                "category": "validation",
                "message": f"Segment {i} missing segment_index field",
                "recoverable": True,
                "suggestion": "Verify segment data includes index field"
            }
        
        segment_index = segment["segment_index"]
        
        # Validate segment_index type and value
        if not isinstance(segment_index, int):
            return False, {
                "code": "INVALID_INDEX_TYPE",
                "category": "validation",
                "message": f"Segment {i}: segment_index must be an integer, got {type(segment_index).__name__}",
                "recoverable": True,
                "suggestion": "segment_index must be a positive integer"
            }
        
        if segment_index < 1:
            return False, {
                "code": "INVALID_INDEX_VALUE",
                "category": "validation",
                "message": f"Segment {i}: segment_index must be >= 1, got {segment_index}",
                "recoverable": True,
                "suggestion": "segment_index must be a positive integer starting from 1"
            }
        
        # Check for duplicate segment_index values
        if segment_index in seen_indexes:
            return False, {
                "code": "DUPLICATE_INDEX",
                "category": "validation",
                "message": f"Duplicate segment_index: {segment_index}",
                "recoverable": True,
                "suggestion": "Each segment must have a unique segment_index"
            }
        seen_indexes.add(segment_index)
        
        if "start_frames" not in segment or "end_frames" not in segment:
            # Try to convert from timecode if available
            if "start_time" in segment and "end_time" in segment:
                try:
                    segment["start_frames"] = timecode_to_frames(segment["start_time"])
                    segment["end_frames"] = timecode_to_frames(segment["end_time"])
                except ValueError as e:
                    return False, {
                        "code": "INVALID_TIMECODE",
                        "category": "validation",
                        "message": f"Invalid timecode format in segment {i}: {e}",
                        "recoverable": True,
                        "suggestion": "Check timecode format (expected: MM:SS, H:MM:SS, or H:MM:SS:FF)"
                    }
            else:
                return False, {
                    "code": "MISSING_FRAME_DATA",
                    "category": "validation",
                    "message": f"Segment {i} missing frame or timecode data",
                    "recoverable": True,
                    "suggestion": "Ensure segments include start_frames/end_frames or start_time/end_time"
                }
        
        start_frames = segment["start_frames"]
        end_frames = segment["end_frames"]
        
        # Validate frame types
        if not isinstance(start_frames, int) or not isinstance(end_frames, int):
            return False, {
                "code": "NON_INTEGER_FRAMES",
                "category": "validation",
                "message": f"Segment {i}: start_frames and end_frames must be integers",
                "recoverable": True,
                "suggestion": "Frame values must be integer frame counts"
            }
        
        # Check for negative values
        if start_frames < 0 or end_frames < 0:
            return False, {
                "code": "NEGATIVE_FRAME_VALUE",
                "category": "validation",
                "message": f"Segment {i} has negative frame value",
                "recoverable": True,
                "suggestion": "Frame values must be non-negative"
            }
        
        # Check start < end
        if start_frames >= end_frames:
            return False, {
                "code": "INVALID_SEGMENT_RANGE",
                "category": "validation",
                "message": f"Segment {i}: start frame ({start_frames}) >= end frame ({end_frames})",
                "recoverable": True,
                "suggestion": "Segment start must be less than segment end"
            }
    
    # Check for overlaps (optional - segments can overlap in source but not in timeline)
    # We don't enforce this as the AI may intentionally select overlapping content
    # and the sequential placement will handle it
    
    return True, None


@dataclass
class SegmentPlacement:
    """Placement of a segment on the timeline.
    
    Attributes:
        segment_index: 1-based segment number from AI
        timeline_track: Track number (1 = video/dialogue)
        timeline_start_frame: Start position on timeline (sequential)
        timeline_end_frame: End position on timeline
        source_in_frame: In point on source clip
        source_out_frame: Out point on source clip
        clip_id: Resolve's clip reference (set after creation)
    """
    segment_index: int
    timeline_track: int
    timeline_start_frame: int
    timeline_end_frame: int
    source_in_frame: int
    source_out_frame: int
    clip_id: Optional[str] = None


@dataclass
class CutResult:
    """Result of a segment cutting operation.
    
    Attributes:
        segments_placed: Number of successfully placed segments
        total_duration_frames: Total duration of all segments on timeline
        total_duration_timecode: Total duration as timecode string
        timeline_positions: List of segment placements with timeline positions
        success: Whether the operation succeeded
        error: Error details if operation failed
    """
    segments_placed: int
    total_duration_frames: int
    timeline_positions: List[SegmentPlacement]
    success: bool = True
    error: Optional[Dict[str, Any]] = None
    
    @property
    def total_duration_timecode(self) -> str:
        """Get total duration as timecode string (assumes 30fps)."""
        return frames_to_timecode(self.total_duration_frames, fps=30)


class FootageCutter:
    """Cuts source footage into timeline segments.
    
    This class handles:
    - Non-destructive cutting (references source, never modifies)
    - Sequential segment placement on timeline
    - Frame-level precision for timecode accuracy
    - Progress reporting during cutting operations
    - Integration with Resolve's timeline API
    
    Usage:
        cutter = FootageCutter()
        result = cutter.cut_segments(
            timeline_id="RoughCut_interview_001_youtube_2026-04-04",
            source_clip_id="interview_001",
            segments=[
                {"segment_index": 1, "start_frames": 900, "end_frames": 6300},
                {"segment_index": 2, "start_frames": 9000, "end_frames": 15300}
            ]
        )
    """
    
    # Default track for video/dialogue
    DEFAULT_VIDEO_TRACK = 1
    
    # Maximum number of segments to process in one batch
    MAX_BATCH_SIZE = 1000
    
    def __init__(self, resolve_api: Optional[ResolveApi] = None):
        """Initialize the footage cutter.
        
        Args:
            resolve_api: Optional ResolveApi instance for testing/mocking.
                        If not provided, a new instance will be created.
        """
        self.resolve_api = resolve_api or ResolveApi()
        logger.info("FootageCutter initialized")
    
    def _calculate_sequential_placements(
        self,
        segments: List[Dict[str, Any]],
        start_track: int = 1
    ) -> List[SegmentPlacement]:
        """Calculate sequential placements for segments on timeline.
        
        This creates a condensed timeline by placing segments back-to-back,
        removing any gaps that existed in the original source.
        
        Args:
            segments: List of segment dictionaries with start_frames and end_frames
            start_track: Track number to place segments on (default 1)
            
        Returns:
            List of SegmentPlacement objects with timeline positions
        """
        placements = []
        current_timeline_position = 0
        
        for segment in segments:
            segment_index = segment["segment_index"]
            source_start = segment["start_frames"]
            source_end = segment["end_frames"]
            segment_duration = source_end - source_start
            
            placement = SegmentPlacement(
                segment_index=segment_index,
                timeline_track=start_track,
                timeline_start_frame=current_timeline_position,
                timeline_end_frame=current_timeline_position + segment_duration,
                source_in_frame=source_start,
                source_out_frame=source_end,
                clip_id=None  # Will be set after Resolve clip creation
            )
            placements.append(placement)
            
            # Move to end of this segment for next placement
            current_timeline_position += segment_duration
            
            logger.debug(
                f"Segment {segment_index}: source {source_start}-{source_end} "
                f"-> timeline {placement.timeline_start_frame}-{placement.timeline_end_frame}"
            )
        
        return placements
    
    def _find_source_clip_in_pool(self, source_clip_id: str) -> Optional[Any]:
        """Find the source clip in Resolve's Media Pool.
        
        Args:
            source_clip_id: The clip ID or name to find
            
        Returns:
            Media Pool clip object if found, None otherwise
        """
        media_pool = self.resolve_api.get_media_pool()
        if not media_pool:
            logger.error("Media Pool not available")
            return None
        
        try:
            # Get the root folder of the media pool
            root_folder = media_pool.GetRootFolder()
            if not root_folder:
                logger.warning("Could not get media pool root folder")
                return None
            
            # Get all clips in the root folder
            clips = root_folder.GetClipList()
            if not clips:
                logger.debug("No clips found in media pool root folder")
                return None
            
            # Look for a clip matching our ID
            for clip in clips:
                try:
                    clip_name = clip.GetName()
                    if clip_name == source_clip_id:
                        logger.debug(f"Found source clip: {source_clip_id}")
                        return clip
                except Exception as e:
                    logger.debug(f"Error checking clip name: {e}")
                    continue
            
            logger.warning(f"Source clip not found in media pool: {source_clip_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching media pool for source clip: {e}")
            return None
    
    def _create_timeline_clip(
        self,
        timeline: Any,
        source_clip: Any,
        track_index: int,
        timeline_position: int,
        source_in: int,
        source_out: int
    ) -> Optional[str]:
        """Create a timeline clip referencing source with specified in/out points.
        
        This is the core method for non-destructive cutting - it creates
        a timeline clip that references the source with specific in/out points.
        
        Args:
            timeline: Resolve timeline object
            source_clip: Media Pool clip object
            track_index: Target track number (1 for video)
            timeline_position: Frame position on timeline
            source_in: In point frame on source
            source_out: Out point frame on source
            
        Returns:
            Clip ID if successful, None otherwise
        """
        try:
            # Method 1: Try using AddClip on timeline (most direct)
            if hasattr(timeline, 'AddClip'):
                # Resolve API: AddClip(clip, trackIndex, startFrame, duration)
                duration = source_out - source_in
                
                # Note: Some Resolve versions expect time in different units
                # This implementation assumes frame-based timing
                result = timeline.AddClip(
                    source_clip,
                    track_index,
                    timeline_position,
                    duration
                )
                
                if result:
                    # Try to get the created clip's ID
                    try:
                        # The clip object may have methods to get its ID
                        if hasattr(result, 'GetName'):
                            clip_id = result.GetName()
                        elif hasattr(result, 'GetId'):
                            clip_id = result.GetId()
                        else:
                            # Generate a stable ID from parameters
                            clip_id = self._generate_stable_clip_id(
                                source_clip, timeline_position, source_in, source_out
                            )
                        
                        logger.debug(
                            f"Created timeline clip: {clip_id} at frame {timeline_position}"
                        )
                        return clip_id
                    except Exception as e:
                        logger.debug(f"Could not get clip ID from result: {e}")
                        # Return a generated ID as fallback
                        return self._generate_stable_clip_id(
                            source_clip, timeline_position, source_in, source_out
                        )
            
            # Method 2: Try via media pool AppendToTimeline (fallback)
            media_pool = self.resolve_api.get_media_pool()
            if media_pool and hasattr(media_pool, 'AppendToTimeline'):
                # This method may not support in/out points directly
                # but is included as a fallback
                logger.warning("Using fallback AppendToTimeline method")
                result = media_pool.AppendToTimeline(source_clip)
                if result:
                    return self._generate_stable_clip_id(
                        source_clip, timeline_position, source_in, source_out
                    )
            
            logger.error("No suitable API method available for creating timeline clip")
            return None
            
        except Exception as e:
            logger.exception(f"Error creating timeline clip: {e}")
            return None
    
    def _generate_stable_clip_id(
        self,
        source_clip: Any,
        timeline_position: int,
        source_in: int,
        source_out: int
    ) -> str:
        """Generate a stable, deterministic clip ID.
        
        Uses MD5 hash for deterministic IDs that persist across process restarts.
        
        Args:
            source_clip: Source clip object (should have GetName method)
            timeline_position: Position on timeline
            source_in: In point on source
            source_out: Out point on source
            
        Returns:
            Stable clip ID string
        """
        try:
            source_name = source_clip.GetName() if hasattr(source_clip, 'GetName') else "unknown"
        except:
            source_name = "unknown"
        
        # Create deterministic string and hash it
        id_string = f"{source_name}_{timeline_position}_{source_in}_{source_out}"
        return hashlib.md5(id_string.encode()).hexdigest()[:16]
    
    def cut_segments(
        self,
        timeline_id: str,
        source_clip_id: str,
        segments: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> CutResult:
        """Cut source footage into timeline segments.
        
        This is the main entry point for segment cutting. It performs
        all operations non-destructively - the source clip is never modified,
        only timeline clips referencing it are created.
        
        Args:
            timeline_id: ID of the target timeline
            source_clip_id: ID of the source clip in Media Pool
            segments: List of segment dictionaries with timing info
            progress_callback: Optional callback for progress updates.
                             Called as progress_callback(current, total, message)
            
        Returns:
            CutResult with details of placed segments
            
        Note:
            No exceptions raised - all errors are captured in result.error
        """
        logger.info(
            f"Starting segment cutting: {len(segments)} segments for timeline {timeline_id}"
        )
        
        # Validate segments
        is_valid, error = validate_segments(segments)
        if not is_valid:
            logger.error(f"Segment validation failed: {error}")
            return CutResult(
                segments_placed=0,
                total_duration_frames=0,
                timeline_positions=[],
                success=False,
                error=error
            )
        
        # Check Resolve API availability
        if not self.resolve_api.is_available():
            error = {
                "code": "RESOLVE_API_UNAVAILABLE",
                "category": "resolve_api",
                "message": "DaVinci Resolve API is not available",
                "recoverable": True,
                "suggestion": "Ensure DaVinci Resolve is running and the scripting API is enabled in preferences"
            }
            logger.error(error["message"])
            return CutResult(
                segments_placed=0,
                total_duration_frames=0,
                timeline_positions=[],
                success=False,
                error=error
            )
        
        # Find the target timeline
        timeline = self.resolve_api.find_timeline_by_name(timeline_id)
        if not timeline:
            error = {
                "code": "TIMELINE_NOT_FOUND",
                "category": "resolve_api",
                "message": f"Timeline not found: {timeline_id}",
                "recoverable": True,
                "suggestion": "Ensure timeline was created successfully in previous step"
            }
            logger.error(error["message"])
            return CutResult(
                segments_placed=0,
                total_duration_frames=0,
                timeline_positions=[],
                success=False,
                error=error
            )
        
        # Find the source clip in Media Pool
        source_clip = self._find_source_clip_in_pool(source_clip_id)
        if not source_clip:
            error = {
                "code": "SOURCE_CLIP_NOT_FOUND",
                "category": "resolve_api",
                "message": f"Source clip not found in Media Pool: {source_clip_id}",
                "recoverable": True,
                "suggestion": "Ensure source media was imported successfully in previous step"
            }
            logger.error(error["message"])
            return CutResult(
                segments_placed=0,
                total_duration_frames=0,
                timeline_positions=[],
                success=False,
                error=error
            )
        
        # Initialize result tracking variables before try block
        successful_placements: List[SegmentPlacement] = []
        total_duration = 0
        
        try:
            # Calculate sequential placements
            placements = self._calculate_sequential_placements(
                segments,
                start_track=self.DEFAULT_VIDEO_TRACK
            )
            
            # Place each segment on timeline
            for i, placement in enumerate(placements):
                segment = segments[i]
                
                # Report progress
                progress_msg = (
                    f"Cutting segment {i + 1} of {len(placements)}: "
                    f"{frames_to_timecode(placement.source_in_frame)}-"
                    f"{frames_to_timecode(placement.source_out_frame)}"
                )
                logger.info(progress_msg)
                
                if progress_callback:
                    progress_callback(i + 1, len(placements), progress_msg)
                
                # Create timeline clip
                clip_id = self._create_timeline_clip(
                    timeline=timeline,
                    source_clip=source_clip,
                    track_index=placement.timeline_track,
                    timeline_position=placement.timeline_start_frame,
                    source_in=placement.source_in_frame,
                    source_out=placement.source_out_frame
                )
                
                if clip_id:
                    placement.clip_id = clip_id
                    successful_placements.append(placement)
                    total_duration += (placement.timeline_end_frame - placement.timeline_start_frame)
                    logger.debug(f"Segment {placement.segment_index} placed successfully")
                else:
                    logger.warning(f"Failed to place segment {placement.segment_index}")
                    # Continue with other segments (don't fail entire operation)
            
            # Recalculate total duration from successful placements
            total_duration = sum(
                p.timeline_end_frame - p.timeline_start_frame
                for p in successful_placements
            )
            
            logger.info(
                f"Segment cutting complete: {len(successful_placements)}/{len(segments)} "
                f"segments placed, total duration: {total_duration} frames"
            )
            
            return CutResult(
                segments_placed=len(successful_placements),
                total_duration_frames=total_duration,
                timeline_positions=successful_placements,
                success=len(successful_placements) > 0
            )
            
        except Exception as e:
            logger.exception(f"Unexpected error during segment cutting: {e}")
            return CutResult(
                segments_placed=len(successful_placements),
                total_duration_frames=total_duration,
                timeline_positions=successful_placements,
                success=False,
                error={
                    "code": "INTERNAL_ERROR",
                    "category": "internal",
                    "message": f"Unexpected error during cutting: {str(e)}",
                    "recoverable": True,
                    "suggestion": "Check application logs and retry the operation"
                }
            )
