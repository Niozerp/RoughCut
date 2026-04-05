"""SFX placer for placing sound effects on timeline tracks.

Handles the placement of AI-suggested SFX clips on the timeline's dedicated
SFX tracks (Tracks 3-10) with proper timing, fade handles, volume levels,
and track allocation for multiple effects.
"""

import hashlib
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .resolve_api import ResolveApi
from .cutter import timecode_to_frames, frames_to_timecode

logger = logging.getLogger(__name__)


# Default fade durations in seconds (shorter than music's 2s)
DEFAULT_SFX_FADE_IN_SECONDS = 1.0
DEFAULT_SFX_FADE_OUT_SECONDS = 1.0

# Default volume levels in dB
DEFAULT_SFX_VOLUME_DB = -12.0
INTRO_WHOOSH_VOLUME_DB = -10.0
PIVOT_EMPHASIS_VOLUME_DB = -15.0
OUTRO_CHIME_VOLUME_DB = -10.0

# Handle/extension room in seconds (±2 seconds)
DEFAULT_HANDLE_SECONDS = 2.0

# SFX track range (Track 3 to Track 10 = 8 tracks)
SFX_TRACK_START = 3
SFX_TRACK_END = 10
MAX_SFX_TRACKS = 8


def validate_sfx_segments(segments: List[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate a list of SFX segments for placement.
    
    Checks:
    - Segments list is not empty
    - Each segment has required fields (segment_index, sfx_file_path, start_frames, end_frames)
    - SFX file paths are valid absolute paths
    - Start frame < end frame for each segment
    - No negative frame values
    - Track numbers are valid (3-10)
    - Volume levels are valid (if provided)
    - Fade durations are valid (if provided)
    
    Args:
        segments: List of SFX segment dictionaries
        
    Returns:
        Tuple of (is_valid, error_dict)
        - is_valid: True if all validations pass
        - error_dict: None if valid, or error details if invalid
    """
    if not segments:
        return False, {
            "code": "NO_SFX_SEGMENTS",
            "category": "validation",
            "message": "No SFX segments provided for placement",
            "recoverable": True,
            "suggestion": "Ensure AI rough cut generation produced SFX suggestions"
        }
    
    seen_indexes = set()
    
    for i, segment in enumerate(segments):
        # Check segment is a dict
        if not isinstance(segment, dict):
            return False, {
                "code": "INVALID_SEGMENT_TYPE",
                "category": "validation",
                "message": f"SFX segment {i} is not a dictionary",
                "recoverable": True,
                "suggestion": "Each SFX segment must be a dictionary with file path and timing data"
            }
        
        # Check required fields
        required_fields = ["segment_index", "sfx_file_path", "start_frames", "end_frames"]
        for field_name in required_fields:
            if field_name not in segment:
                return False, {
                    "code": f"MISSING_{field_name.upper()}",
                    "category": "validation",
                    "message": f"SFX segment {i} missing {field_name} field",
                    "recoverable": True,
                    "suggestion": f"Verify segment data includes {field_name} field"
                }
        
        segment_index = segment["segment_index"]
        
        # Validate segment_index type and value
        if not isinstance(segment_index, int):
            return False, {
                "code": "INVALID_INDEX_TYPE",
                "category": "validation",
                "message": f"SFX segment {i}: segment_index must be an integer, got {type(segment_index).__name__}",
                "recoverable": True,
                "suggestion": "segment_index must be a positive integer"
            }
        
        if segment_index < 1:
            return False, {
                "code": "INVALID_INDEX_VALUE",
                "category": "validation",
                "message": f"SFX segment {i}: segment_index must be >= 1, got {segment_index}",
                "recoverable": True,
                "suggestion": "segment_index must be a positive integer starting from 1"
            }
        
        # Check for duplicate segment_index values
        if segment_index in seen_indexes:
            return False, {
                "code": "DUPLICATE_INDEX",
                "category": "validation",
                "message": f"Duplicate SFX segment_index: {segment_index}",
                "recoverable": True,
                "suggestion": "Each SFX segment must have a unique segment_index"
            }
        seen_indexes.add(segment_index)
        
        # Validate SFX file path
        file_path = segment["sfx_file_path"]
        if not isinstance(file_path, str):
            return False, {
                "code": "INVALID_FILE_PATH_TYPE",
                "category": "validation",
                "message": f"SFX segment {i}: sfx_file_path must be a string",
                "recoverable": True,
                "suggestion": "File path must be a string"
            }
        
        if not file_path:
            return False, {
                "code": "EMPTY_FILE_PATH",
                "category": "validation",
                "message": f"SFX segment {i}: sfx_file_path is empty",
                "recoverable": True,
                "suggestion": "Provide a valid SFX file path"
            }
        
        # Check if absolute path
        if not os.path.isabs(file_path):
            return False, {
                "code": "RELATIVE_FILE_PATH",
                "category": "validation",
                "message": f"SFX segment {i}: sfx_file_path must be absolute, got: {file_path}",
                "recoverable": True,
                "suggestion": "Use absolute file paths for SFX files"
            }
        
        # Normalize path and check for path traversal attempts
        normalized_path = os.path.normpath(file_path)
        if '..' in normalized_path.split(os.sep):
            return False, {
                "code": "PATH_TRAVERSAL_DETECTED",
                "category": "validation",
                "message": f"SFX segment {i}: path contains parent directory references",
                "recoverable": True,
                "suggestion": "Provide a clean absolute path without '..' components"
            }
        
        # Check if file exists and is readable (TOCTOU-safe)
        # Use try/except to avoid race condition between exists() and access()
        try:
            if not os.path.exists(file_path):
                return False, {
                    "code": "SFX_FILE_NOT_FOUND",
                    "category": "file_system",
                    "message": f"SFX segment {i}: file not found at path: {file_path}",
                    "recoverable": True,
                    "suggestion": "Verify the SFX file exists and the path is correct"
                }
            
            # Check readability by attempting to open the file
            with open(file_path, 'rb') as f:
                f.read(1)  # Read one byte to verify access
        except FileNotFoundError:
            return False, {
                "code": "SFX_FILE_NOT_FOUND",
                "category": "file_system",
                "message": f"SFX segment {i}: file not found at path: {file_path}",
                "recoverable": True,
                "suggestion": "Verify the SFX file exists and the path is correct"
            }
        except PermissionError:
            return False, {
                "code": "SFX_FILE_NOT_READABLE",
                "category": "file_system",
                "message": f"SFX segment {i}: file not readable: {file_path}",
                "recoverable": True,
                "suggestion": "Check file permissions and ensure the file is accessible"
            }
        except OSError as e:
            return False, {
                "code": "SFX_FILE_ACCESS_ERROR",
                "category": "file_system",
                "message": f"SFX segment {i}: cannot access file: {file_path} - {str(e)}",
                "recoverable": True,
                "suggestion": "Check file permissions and ensure the file is accessible"
            }
        
        # Validate frame values
        start_frames = segment["start_frames"]
        end_frames = segment["end_frames"]
        
        if not isinstance(start_frames, int) or not isinstance(end_frames, int):
            return False, {
                "code": "NON_INTEGER_FRAMES",
                "category": "validation",
                "message": f"SFX segment {i}: start_frames and end_frames must be integers",
                "recoverable": True,
                "suggestion": "Frame values must be integer frame counts"
            }
        
        # Check for negative values
        if start_frames < 0:
            return False, {
                "code": "NEGATIVE_START_FRAME",
                "category": "validation",
                "message": f"SFX segment {i} has negative start frame: {start_frames}",
                "recoverable": True,
                "suggestion": "Start frame must be non-negative"
            }
        
        if end_frames < 0:
            return False, {
                "code": "NEGATIVE_END_FRAME",
                "category": "validation",
                "message": f"SFX segment {i} has negative end frame: {end_frames}",
                "recoverable": True,
                "suggestion": "End frame must be non-negative"
            }
        
        # Check start < end
        if start_frames >= end_frames:
            return False, {
                "code": "INVALID_SEGMENT_RANGE",
                "category": "validation",
                "message": f"SFX segment {i}: start frame ({start_frames}) >= end frame ({end_frames})",
                "recoverable": True,
                "suggestion": "Segment start must be less than segment end"
            }
        
        # Check for unreasonably large frame counts (prevents integer overflow)
        # Maximum: ~92 hours at 30fps (10 million frames)
        MAX_REASONABLE_FRAMES = 10_000_000
        if start_frames > MAX_REASONABLE_FRAMES or end_frames > MAX_REASONABLE_FRAMES:
            return False, {
                "code": "FRAME_COUNT_TOO_LARGE",
                "category": "validation",
                "message": f"SFX segment {i}: frame count exceeds maximum reasonable value ({MAX_REASONABLE_FRAMES})",
                "recoverable": True,
                "suggestion": "Check timeline duration - maximum supported is approximately 92 hours at 30fps"
            }
        
        # Validate track number if provided (must be 3-10 for SFX)
        track_number = segment.get("track_number", SFX_TRACK_START)
        if not isinstance(track_number, int) or track_number < SFX_TRACK_START or track_number > SFX_TRACK_END:
            return False, {
                "code": "INVALID_TRACK_NUMBER",
                "category": "validation",
                "message": f"SFX segment {i}: track_number must be an integer between {SFX_TRACK_START} and {SFX_TRACK_END}, got {track_number}",
                "recoverable": True,
                "suggestion": f"SFX tracks must be in range {SFX_TRACK_START}-{SFX_TRACK_END}"
            }
        
        # Validate volume_db if provided
        volume_db = segment.get("volume_db", DEFAULT_SFX_VOLUME_DB)
        if not isinstance(volume_db, (int, float)):
            return False, {
                "code": "INVALID_VOLUME_TYPE",
                "category": "validation",
                "message": f"SFX segment {i}: volume_db must be a number",
                "recoverable": True,
                "suggestion": "Volume must be a numeric value in dB"
            }
        
        # Validate fade durations if provided
        fade_in = segment.get("fade_in_seconds", DEFAULT_SFX_FADE_IN_SECONDS)
        fade_out = segment.get("fade_out_seconds", DEFAULT_SFX_FADE_OUT_SECONDS)
        
        if not isinstance(fade_in, (int, float)) or fade_in < 0:
            return False, {
                "code": "INVALID_FADE_IN",
                "category": "validation",
                "message": f"SFX segment {i}: fade_in_seconds must be a non-negative number",
                "recoverable": True,
                "suggestion": "Fade duration must be >= 0 seconds"
            }
        
        if not isinstance(fade_out, (int, float)) or fade_out < 0:
            return False, {
                "code": "INVALID_FADE_OUT",
                "category": "validation",
                "message": f"SFX segment {i}: fade_out_seconds must be a non-negative number",
                "recoverable": True,
                "suggestion": "Fade duration must be >= 0 seconds"
            }
    
    return True, None


@dataclass
class SfxPlacement:
    """Placement of an SFX clip on the timeline.
    
    Attributes:
        segment_index: 1-based segment number from AI
        track_number: Track number (3-10 for SFX tracks)
        timeline_start_frame: Start position on timeline
        timeline_end_frame: End position on timeline
        sfx_file_path: Absolute path to the SFX file
        clip_id: Resolve's clip reference (set after creation)
        fade_in_frames: Fade in duration in frames
        fade_out_frames: Fade out duration in frames
        volume_db: Volume level in dB
        moment_type: Type of moment (intro_whoosh, pivot_emphasis, outro_chime, etc.)
        handle_frames: Adjustment handle room on each side in frames (±2 seconds)
    """
    segment_index: int
    track_number: int
    timeline_start_frame: int
    timeline_end_frame: int
    sfx_file_path: str
    clip_id: Optional[str] = None
    fade_in_frames: int = 0
    fade_out_frames: int = 0
    volume_db: float = DEFAULT_SFX_VOLUME_DB
    moment_type: str = "generic"
    handle_frames: int = 0


@dataclass
class SfxPlacerResult:
    """Result of an SFX placement operation.
    
    Attributes:
        clips_placed: Number of successfully placed SFX clips
        tracks_used: List of track numbers that were used
        total_duration_frames: Total duration of all SFX clips on timeline
        timeline_positions: List of SFX placements with timeline positions
        success: Whether the operation succeeded
        error: Error details if operation failed
        fps: Frames per second for timecode conversion
    """
    clips_placed: int
    tracks_used: List[int]
    total_duration_frames: int
    timeline_positions: List[SfxPlacement]
    success: bool = True
    error: Optional[Dict[str, Any]] = None
    fps: int = 30  # Frames per second for timecode conversion
    
    def get_total_duration_timecode(self, fps: Optional[int] = None) -> str:
        """Get total duration as timecode string.
        
        Args:
            fps: Frames per second (defaults to self.fps or 30)
            
        Returns:
            Timecode string in format "H:MM:SS"
        """
        use_fps = fps or self.fps or 30
        return frames_to_timecode(self.total_duration_frames, fps=use_fps)
    
    @property
    def total_duration_timecode(self) -> str:
        """Get total duration as timecode string (uses default fps)."""
        return self.get_total_duration_timecode()


class SfxPlacer:
    """Places AI-suggested SFX clips on the timeline.
    
    This class handles:
    - SFX clip placement on dedicated SFX tracks (Tracks 3-10)
    - Track allocation for multiple SFX (conflict detection)
    - Fade in/out handles for audio transitions (1-second default)
    - Volume level management (default -12 dB, configurable per SFX)
    - Adjustment handles (±2 seconds) for easy editor adjustment
    - Progress reporting during placement operations
    - Integration with Resolve's timeline API
    
    Usage:
        placer = SfxPlacer()
        result = placer.place_sfx_clips(
            timeline_id="RoughCut_interview_001_youtube_2026-04-04",
            sfx_segments=[
                {
                    "segment_index": 1,
                    "sfx_file_path": "/path/to/whoosh.wav",
                    "start_frames": 0,
                    "end_frames": 90,
                    "fade_in_seconds": 0.5,
                    "fade_out_seconds": 0.5,
                    "volume_db": -10.0,
                    "moment_type": "intro_whoosh"
                }
            ]
        )
    """
    
    def __init__(self, resolve_api: Optional[ResolveApi] = None):
        """Initialize the SFX placer.
        
        Args:
            resolve_api: Optional ResolveApi instance for testing/mocking.
                        If not provided, a new instance will be created.
        """
        self.resolve_api = resolve_api or ResolveApi()
        logger.info("SfxPlacer initialized")
    
    def _seconds_to_frames(self, seconds: float, fps: int = 30) -> int:
        """Convert seconds to frame count.
        
        Args:
            seconds: Duration in seconds
            fps: Frames per second (default 30)
            
        Returns:
            Frame count as integer
            
        Raises:
            ValueError: If fps is not a positive number
        """
        if fps <= 0:
            raise ValueError(f"FPS must be a positive number, got {fps}")
        return int(seconds * fps)
    
    def _get_default_volume_for_moment_type(self, moment_type: str) -> float:
        """Get default volume level based on moment type.
        
        Args:
            moment_type: Type of SFX moment (intro_whoosh, pivot_emphasis, etc.)
            
        Returns:
            Volume level in dB
        """
        volume_map = {
            "intro_whoosh": INTRO_WHOOSH_VOLUME_DB,
            "pivot_emphasis": PIVOT_EMPHASIS_VOLUME_DB,
            "outro_chime": OUTRO_CHIME_VOLUME_DB,
            "transition": -12.0,
            "accent": -10.0,
            "underscore": -18.0,
            "generic": DEFAULT_SFX_VOLUME_DB
        }
        return volume_map.get(moment_type, DEFAULT_SFX_VOLUME_DB)
    
    def _check_track_conflict(
        self,
        track_number: int,
        start_frame: int,
        end_frame: int,
        existing_placements: List[SfxPlacement]
    ) -> bool:
        """Check if an SFX segment conflicts with existing placements on a track.
        
        Args:
            track_number: Track to check
            start_frame: Proposed start frame
            end_frame: Proposed end frame
            existing_placements: List of already placed SFX segments
            
        Returns:
            True if there's a conflict (overlap), False if the track is clear
        """
        # Zero-duration clips don't conflict with anything
        if start_frame >= end_frame:
            return False
        
        for placement in existing_placements:
            if placement.track_number != track_number:
                continue
            
            # Check for overlap
            # No overlap if: new segment ends before existing starts
            #                OR new segment starts after existing ends
            if not (end_frame <= placement.timeline_start_frame or 
                    start_frame >= placement.timeline_end_frame):
                return True
        
        return False
    
    def _allocate_sfx_track(
        self,
        preferred_track: int,
        start_frame: int,
        end_frame: int,
        existing_placements: List[SfxPlacement]
    ) -> int:
        """Allocate the best available track for an SFX segment.
        
        First tries the preferred track, then searches for available tracks
        in the SFX track range (3-10). If the preferred track has a time 
        conflict (overlap), searches upward from preferred+1 to SFX_TRACK_END,
        then downward from SFX_TRACK_START to preferred-1.
        
        Args:
            preferred_track: Preferred track number (usually 3 for first SFX)
            start_frame: Start frame of the SFX segment on timeline
            end_frame: End frame of the SFX segment on timeline
            existing_placements: Already placed SFX segments to check for conflicts
            
        Returns:
            Track number to use for this segment (3-10)
            
        Raises:
            TrackAllocationError: If all SFX tracks (3-10) have time conflicts
            
        Examples:
            # No conflicts - returns preferred track
            >>> allocate_sfx_track(3, 0, 90, [])
            3
            
            # Track 3 occupied at 0-90, no conflict at 100-190
            >>> existing = [SfxPlacement(1, 3, 0, 90, "/path.wav")]
            >>> allocate_sfx_track(3, 100, 190, existing)
            3  # Same track, different time - no conflict
            
            # Track 3 occupied at same time, allocates track 4
            >>> existing = [SfxPlacement(1, 3, 0, 90, "/path.wav")]
            >>> allocate_sfx_track(3, 0, 90, existing)
            4  # Conflict on 3, allocated 4
            
            # All tracks full - raises exception
            >>> existing = [SfxPlacement(i, track, 0, 90, f"/{i}.wav") 
            ...             for i, track in enumerate(range(3, 11), 1)]
            >>> allocate_sfx_track(3, 0, 90, existing)
            TrackAllocationError: All SFX tracks (3-10) are full
        """
        # Ensure preferred track is in valid range
        if preferred_track < SFX_TRACK_START:
            preferred_track = SFX_TRACK_START
        if preferred_track > SFX_TRACK_END:
            preferred_track = SFX_TRACK_END
        
        # Check preferred track first
        if not self._check_track_conflict(preferred_track, start_frame, end_frame, existing_placements):
            return preferred_track
        
        # Try additional tracks in range (4, 5, 6, etc.)
        for track in range(preferred_track + 1, SFX_TRACK_END + 1):
            if not self._check_track_conflict(track, start_frame, end_frame, existing_placements):
                logger.debug(f"Allocated track {track} for SFX segment (track {preferred_track} occupied)")
                return track
        
        # Try tracks before preferred (in case preferred was > 3)
        for track in range(SFX_TRACK_START, preferred_track):
            if not self._check_track_conflict(track, start_frame, end_frame, existing_placements):
                logger.debug(f"Allocated track {track} for SFX segment (lower track available)")
                return track
        
        # All SFX tracks full - raise error
        raise TrackAllocationError(
            f"All SFX tracks ({SFX_TRACK_START}-{SFX_TRACK_END}) are full. "
            f"Cannot place SFX at frames {start_frame}-{end_frame}."
        )
    
    def _find_sfx_in_media_pool(self, file_path: str) -> Optional[Any]:
        """Find an SFX file in Resolve's Media Pool.
        
        Args:
            file_path: Absolute path to the SFX file
            
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
            
            # Look for a clip matching our file path
            for clip in clips:
                try:
                    clip_props = clip.GetClipProperty()
                    if clip_props:
                        clip_path = clip_props.get("File Path") or clip_props.get("FilePath")
                        if clip_path and os.path.normpath(clip_path) == os.path.normpath(file_path):
                            logger.debug(f"Found SFX in media pool: {file_path}")
                            return clip
                except Exception as e:
                    logger.debug(f"Error checking clip properties: {e}")
                    continue
            
            logger.debug(f"SFX not found in media pool: {file_path}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching media pool for SFX: {e}")
            return None
    
    def _import_sfx_to_pool(self, file_path: str) -> Optional[Any]:
        """Import an SFX file into Resolve's Media Pool.
        
        Args:
            file_path: Absolute path to the SFX file
            
        Returns:
            Media Pool clip object if successful, None otherwise
        """
        media_pool = self.resolve_api.get_media_pool()
        if not media_pool:
            logger.error("Cannot import SFX - Media Pool not available")
            return None
        
        try:
            # Check if already in pool
            existing = self._find_sfx_in_media_pool(file_path)
            if existing:
                logger.info(f"SFX already in pool, using existing: {file_path}")
                return existing
            
            # Import the SFX file
            root_folder = media_pool.GetRootFolder()
            if not root_folder:
                logger.error("Could not get media pool root folder for import")
                return None
            
            imported_items = media_pool.ImportMedia([file_path])
            
            if imported_items and len(imported_items) > 0:
                logger.info(f"Successfully imported SFX: {file_path}")
                return imported_items[0]
            else:
                logger.warning(f"ImportMedia returned empty result for: {file_path}")
                return None
                
        except Exception as e:
            logger.exception(f"Error importing SFX to pool: {file_path}")
            return None
    
    def _create_timeline_sfx_clip(
        self,
        timeline: Any,
        sfx_clip: Any,
        track_index: int,
        timeline_position: int,
        source_in: int,
        source_out: int
    ) -> Optional[str]:
        """Create a timeline clip for SFX with specified in/out points.
        
        Args:
            timeline: Resolve timeline object
            sfx_clip: Media Pool SFX clip object
            track_index: Target track number (3+ for SFX)
            timeline_position: Frame position on timeline
            source_in: In point frame on source SFX clip
            source_out: Out point frame on source SFX clip
            
        Returns:
            Clip ID if successful, None otherwise
        """
        try:
            # Check source clip duration if possible
            source_duration = None
            if hasattr(sfx_clip, 'GetDuration'):
                try:
                    source_duration = sfx_clip.GetDuration()
                except Exception:
                    pass
            
            requested_duration = source_out - source_in
            
            # Warn if source is shorter than requested duration
            if source_duration is not None and requested_duration > source_duration:
                logger.warning(
                    f"Requested SFX duration ({requested_duration} frames) exceeds "
                    f"source clip duration ({source_duration} frames). "
                    f"Resolve may extend with silence or loop."
                )
            
            # Use AddClip on timeline for SFX placement
            if hasattr(timeline, 'AddClip'):
                result = timeline.AddClip(
                    sfx_clip,
                    track_index,
                    timeline_position,
                    requested_duration
                )
                
                if result:
                    # Generate a stable clip ID
                    try:
                        if hasattr(result, 'GetName'):
                            clip_id = result.GetName()
                        else:
                            clip_id = self._generate_stable_clip_id(
                                sfx_clip, timeline_position, source_in, source_out
                            )
                        
                        logger.debug(
                            f"Created SFX clip: {clip_id} at track {track_index}, "
                            f"position {timeline_position}, duration {requested_duration}"
                        )
                        return clip_id
                    except Exception as e:
                        logger.debug(f"Could not get clip ID from result: {e}")
                        return self._generate_stable_clip_id(
                            sfx_clip, timeline_position, source_in, source_out
                        )
            
            logger.error("No suitable API method available for creating SFX clip")
            return None
            
        except Exception as e:
            logger.exception(f"Error creating SFX timeline clip: {e}")
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
        # Use UTF-8 encoding with replacement to handle non-ASCII filenames
        id_string = f"sfx_{source_name}_{timeline_position}_{source_in}_{source_out}"
        return hashlib.md5(id_string.encode('utf-8', errors='replace')).hexdigest()[:16]
    
    def _apply_fade_handles(
        self,
        timeline: Any,
        clip_id: str,
        fade_in_frames: int,
        fade_out_frames: int
    ) -> bool:
        """Apply fade in/out handles to an SFX clip.
        
        Note: This is a placeholder implementation. The actual Resolve API
        for setting fade handles varies by version and may require different
        approaches (Fusion composition, keyframes, or clip properties).
        
        Args:
            timeline: Resolve timeline object
            clip_id: ID of the clip to apply fades to
            fade_in_frames: Fade in duration in frames
            fade_out_frames: Fade out duration in frames
            
        Returns:
            True if fades were applied, False otherwise
        """
        # Currently, Resolve's API for setting fade handles is limited.
        # This is documented for future implementation when API support improves.
        # For now, fades are documented in the placement result for manual adjustment.
        
        logger.debug(
            f"Fade handles documented for SFX clip {clip_id}: "
            f"fade_in={fade_in_frames} frames, fade_out={fade_out_frames} frames"
        )
        return True
    
    def place_sfx_clips(
        self,
        timeline_id: str,
        sfx_segments: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> SfxPlacerResult:
        """Place SFX clips on the timeline.
        
        This is the main entry point for SFX placement. It performs
        all operations non-destructively - placing SFX on dedicated
        tracks (3-10) without affecting existing content on tracks 1-2.
        
        Args:
            timeline_id: ID of the target timeline
            sfx_segments: List of SFX segment dictionaries with timing info
            progress_callback: Optional callback for progress updates.
                             Called as progress_callback(current, total, message)
            
        Returns:
            SfxPlacerResult with details of placed clips
            
        Note:
            No exceptions raised - all errors are captured in result.error
        """
        logger.info(
            f"Starting SFX placement: {len(sfx_segments)} SFX clips for timeline {timeline_id}"
        )
        
        # Validate timeline_id
        if not timeline_id or not isinstance(timeline_id, str):
            logger.error(f"Invalid timeline_id: {timeline_id}")
            return SfxPlacerResult(
                clips_placed=0,
                tracks_used=[],
                total_duration_frames=0,
                timeline_positions=[],
                success=False,
                error={
                    "code": "INVALID_TIMELINE_ID",
                    "category": "validation",
                    "message": "Timeline ID must be a non-empty string",
                    "recoverable": True,
                    "suggestion": "Provide a valid timeline ID from the rough cut workflow"
                }
            )
        
        # Validate segments
        is_valid, error = validate_sfx_segments(sfx_segments)
        if not is_valid:
            logger.error(f"SFX segment validation failed: {error}")
            return SfxPlacerResult(
                clips_placed=0,
                tracks_used=[],
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
            return SfxPlacerResult(
                clips_placed=0,
                tracks_used=[],
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
            return SfxPlacerResult(
                clips_placed=0,
                tracks_used=[],
                total_duration_frames=0,
                timeline_positions=[],
                success=False,
                error=error
            )
        
        # Verify timeline has sufficient tracks for SFX (at least track 3 should exist)
        try:
            # Check if timeline supports track count query
            if hasattr(timeline, 'GetTrackCount'):
                track_count = timeline.GetTrackCount()
                if track_count < SFX_TRACK_START:
                    logger.warning(f"Timeline has only {track_count} tracks, but SFX requires track {SFX_TRACK_START}")
                    # Continue anyway - Resolve may auto-create tracks
        except Exception as e:
            logger.debug(f"Could not verify track count: {e}")
            # Continue - not all Resolve versions support this
        
        # Initialize result tracking
        successful_placements: List[SfxPlacement] = []
        tracks_used: set = set()
        total_duration = 0
        
        try:
            # Process each SFX segment
            for i, segment in enumerate(sfx_segments):
                segment_index = segment["segment_index"]
                file_path = segment["sfx_file_path"]
                start_frames = segment["start_frames"]
                end_frames = segment["end_frames"]
                preferred_track = segment.get("track_number", SFX_TRACK_START)
                moment_type = segment.get("moment_type", "generic")
                
                # Calculate fade durations in frames
                fade_in_seconds = segment.get("fade_in_seconds", DEFAULT_SFX_FADE_IN_SECONDS)
                fade_out_seconds = segment.get("fade_out_seconds", DEFAULT_SFX_FADE_OUT_SECONDS)
                fade_in_frames = self._seconds_to_frames(fade_in_seconds)
                fade_out_frames = self._seconds_to_frames(fade_out_seconds)
                
                # Calculate handle frames (±2 seconds)
                handle_frames = self._seconds_to_frames(DEFAULT_HANDLE_SECONDS)
                
                # Get volume level (use provided or default based on moment type)
                volume_db = segment.get("volume_db")
                if volume_db is None:
                    volume_db = self._get_default_volume_for_moment_type(moment_type)
                
                # Report progress
                progress_msg = f"Placing SFX: {os.path.basename(file_path)}"
                logger.info(f"Progress: {progress_msg} ({i + 1}/{len(sfx_segments)})")
                
                if progress_callback:
                    try:
                        progress_callback(i + 1, len(sfx_segments), progress_msg)
                    except Exception:
                        logger.exception(f"Progress callback failed for segment {segment_index}")
                        # Continue with placement - callback failure shouldn't abort operation
                
                # Import SFX to Media Pool if not already there
                sfx_clip = self._import_sfx_to_pool(file_path)
                if not sfx_clip:
                    logger.warning(f"Failed to import SFX: {file_path}")
                    # Continue with other segments (don't fail entire operation)
                    continue
                
                # Allocate track (handle overlapping)
                try:
                    actual_track = self._allocate_sfx_track(
                        preferred_track,
                        start_frames,
                        end_frames,
                        successful_placements
                    )
                except TrackAllocationError as e:
                    logger.error(f"Track allocation failed for SFX segment {segment_index}: {e}")
                    # Continue with other segments
                    continue
                
                # Create timeline clip
                clip_id = self._create_timeline_sfx_clip(
                    timeline=timeline,
                    sfx_clip=sfx_clip,
                    track_index=actual_track,
                    timeline_position=start_frames,
                    source_in=0,  # Use full SFX clip from start
                    source_out=end_frames - start_frames  # Duration needed
                )
                
                if clip_id:
                    # Create placement record
                    placement = SfxPlacement(
                        segment_index=segment_index,
                        track_number=actual_track,
                        timeline_start_frame=start_frames,
                        timeline_end_frame=end_frames,
                        sfx_file_path=file_path,
                        clip_id=clip_id,
                        fade_in_frames=fade_in_frames,
                        fade_out_frames=fade_out_frames,
                        volume_db=volume_db,
                        moment_type=moment_type,
                        handle_frames=handle_frames
                    )
                    
                    successful_placements.append(placement)
                    tracks_used.add(actual_track)
                    total_duration += (end_frames - start_frames)
                    
                    # Apply fade handles (documented even if API limited)
                    self._apply_fade_handles(timeline, clip_id, fade_in_frames, fade_out_frames)
                    
                    logger.debug(f"SFX segment {segment_index} placed successfully on track {actual_track}")
                else:
                    logger.warning(f"Failed to place SFX segment {segment_index}")
                    # Continue with other segments
            
            # Log completion
            logger.info(
                f"SFX placement complete: {len(successful_placements)}/{len(sfx_segments)} "
                f"clips placed, tracks used: {sorted(tracks_used)}, "
                f"total duration: {total_duration} frames"
            )
            
            return SfxPlacerResult(
                clips_placed=len(successful_placements),
                tracks_used=sorted(list(tracks_used)),
                total_duration_frames=total_duration,
                timeline_positions=successful_placements,
                success=len(successful_placements) > 0
            )
            
        except Exception as e:
            logger.exception(f"Unexpected error during SFX placement: {e}")
            return SfxPlacerResult(
                clips_placed=len(successful_placements),
                tracks_used=sorted(list(tracks_used)),
                total_duration_frames=total_duration,
                timeline_positions=successful_placements,
                success=False,
                error={
                    "code": "INTERNAL_ERROR",
                    "category": "internal",
                    "message": f"Unexpected error during SFX placement: {str(e)}",
                    "recoverable": True,
                    "suggestion": "Check application logs and retry the operation"
                }
            )


class TrackAllocationError(Exception):
    """Raised when all SFX tracks are full and no allocation is possible."""
    pass
