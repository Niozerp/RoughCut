"""VFX placer for placing visual effects templates on timeline tracks.

Handles the placement of AI-suggested VFX templates on the timeline's dedicated
VFX tracks (Tracks 11-14) with proper timing, fade transitions, template parameters,
and track allocation for multiple effects.
"""

import hashlib
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .resolve_api import ResolveApi
from .cutter import timecode_to_frames, frames_to_timecode

logger = logging.getLogger(__name__)


# Default fade durations in seconds (shorter than music/SFX)
DEFAULT_VFX_FADE_IN_SECONDS = 0.5
DEFAULT_VFX_FADE_OUT_SECONDS = 0.5

# VFX track range (Track 11 to Track 14 = 4 tracks)
VFX_TRACK_START = 11
VFX_TRACK_END = 14
MAX_VFX_TRACKS = 4

# Default VFX template parameters by type
VFX_TEMPLATE_DEFAULTS = {
    "lower_third": {
        "speaker_name": "",
        "title": "",
        "company": "",
        "duration_seconds": 5.0,
        "animation_in": "fade_slide",
        "animation_out": "fade_out"
    },
    "outro_cta": {
        "cta_text": "Subscribe",
        "sub_text": "For more content",
        "duration_seconds": 5.0,
        "animation_style": "pop_in"
    },
    "intro_title": {
        "title_text": "",
        "subtitle_text": "",
        "duration_seconds": 3.0,
        "animation_style": "reveal"
    },
    "transition": {
        "duration_seconds": 1.0,
        "animation_style": "wipe"
    },
    "generic": {
        "duration_seconds": 3.0,
        "animation_style": "fade"
    }
}


def validate_vfx_segments(segments: List[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate a list of VFX segments for placement.
    
    Checks:
    - Segments list is not empty
    - Each segment has required fields (segment_index, vfx_file_path, start_frames, end_frames)
    - VFX file paths are valid absolute paths
    - Start frame < end frame for each segment
    - No negative frame values
    - Track numbers are valid (11-14)
    - Template type is valid (if provided)
    - Fade durations are valid (if provided)
    
    Args:
        segments: List of VFX segment dictionaries
        
    Returns:
        Tuple of (is_valid, error_dict)
        - is_valid: True if all validations pass
        - error_dict: None if valid, or error details if invalid
    """
    if not segments:
        return False, {
            "code": "NO_VFX_SEGMENTS",
            "category": "validation",
            "message": "No VFX segments provided for placement",
            "recoverable": True,
            "suggestion": "Ensure AI rough cut generation produced VFX suggestions"
        }
    
    seen_indexes = set()
    
    for i, segment in enumerate(segments):
        # Check segment is a dict
        if not isinstance(segment, dict):
            return False, {
                "code": "INVALID_SEGMENT_TYPE",
                "category": "validation",
                "message": f"VFX segment {i} is not a dictionary",
                "recoverable": True,
                "suggestion": "Each VFX segment must be a dictionary with file path and timing data"
            }
        
        # Check required fields
        required_fields = ["segment_index", "vfx_file_path", "start_frames", "end_frames"]
        for field_name in required_fields:
            if field_name not in segment:
                return False, {
                    "code": f"MISSING_{field_name.upper()}",
                    "category": "validation",
                    "message": f"VFX segment {i} missing {field_name} field",
                    "recoverable": True,
                    "suggestion": f"Verify segment data includes {field_name} field"
                }
        
        segment_index = segment["segment_index"]
        
        # Validate segment_index type and value
        if not isinstance(segment_index, int):
            return False, {
                "code": "INVALID_INDEX_TYPE",
                "category": "validation",
                "message": f"VFX segment {i}: segment_index must be an integer, got {type(segment_index).__name__}",
                "recoverable": True,
                "suggestion": "segment_index must be a positive integer"
            }
        
        if segment_index < 1:
            return False, {
                "code": "INVALID_INDEX_VALUE",
                "category": "validation",
                "message": f"VFX segment {i}: segment_index must be >= 1, got {segment_index}",
                "recoverable": True,
                "suggestion": "segment_index must be a positive integer starting from 1"
            }
        
        # Check for duplicate segment_index values
        if segment_index in seen_indexes:
            return False, {
                "code": "DUPLICATE_INDEX",
                "category": "validation",
                "message": f"Duplicate VFX segment_index: {segment_index}",
                "recoverable": True,
                "suggestion": "Each VFX segment must have a unique segment_index"
            }
        seen_indexes.add(segment_index)
        
        # Validate VFX file path
        file_path = segment["vfx_file_path"]
        if not isinstance(file_path, str):
            return False, {
                "code": "INVALID_FILE_PATH_TYPE",
                "category": "validation",
                "message": f"VFX segment {i}: vfx_file_path must be a string",
                "recoverable": True,
                "suggestion": "File path must be a string"
            }
        
        if not file_path:
            return False, {
                "code": "EMPTY_FILE_PATH",
                "category": "validation",
                "message": f"VFX segment {i}: vfx_file_path is empty",
                "recoverable": True,
                "suggestion": "Provide a valid VFX file path"
            }
        
        # Check if absolute path
        if not os.path.isabs(file_path):
            return False, {
                "code": "RELATIVE_FILE_PATH",
                "category": "validation",
                "message": f"VFX segment {i}: vfx_file_path must be absolute, got: {file_path}",
                "recoverable": True,
                "suggestion": "Use absolute file paths for VFX files"
            }
        
        # Check for path traversal attempts before normalization
        # Check for '..' in both forward slash and backslash paths (cross-platform)
        if '..' in file_path.replace('\\', '/').split('/'):
            return False, {
                "code": "PATH_TRAVERSAL_DETECTED",
                "category": "validation",
                "message": f"VFX segment {i}: path contains parent directory references",
                "recoverable": True,
                "suggestion": "Provide a clean absolute path without '..' components"
            }
        
        # Normalize path for further validation
        normalized_path = os.path.normpath(file_path)
        
        # Check if file exists and is readable (TOCTOU-safe)
        # Use try/except to avoid race condition between exists() and access()
        try:
            if not os.path.exists(file_path):
                return False, {
                    "code": "VFX_FILE_NOT_FOUND",
                    "category": "file_system",
                    "message": f"VFX segment {i}: file not found at path: {file_path}",
                    "recoverable": True,
                    "suggestion": "Verify the VFX file exists and the path is correct"
                }
            
            # Check readability by attempting to open the file
            with open(file_path, 'rb') as f:
                f.read(1)  # Read one byte to verify access
        except FileNotFoundError:
            return False, {
                "code": "VFX_FILE_NOT_FOUND",
                "category": "file_system",
                "message": f"VFX segment {i}: file not found at path: {file_path}",
                "recoverable": True,
                "suggestion": "Verify the VFX file exists and the path is correct"
            }
        except PermissionError:
            return False, {
                "code": "VFX_FILE_NOT_READABLE",
                "category": "file_system",
                "message": f"VFX segment {i}: file not readable: {file_path}",
                "recoverable": True,
                "suggestion": "Check file permissions and ensure the file is accessible"
            }
        except OSError as e:
            return False, {
                "code": "VFX_FILE_ACCESS_ERROR",
                "category": "file_system",
                "message": f"VFX segment {i}: cannot access file: {file_path} - {str(e)}",
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
                "message": f"VFX segment {i}: start_frames and end_frames must be integers",
                "recoverable": True,
                "suggestion": "Frame values must be integer frame counts"
            }
        
        # Check for negative values
        if start_frames < 0:
            return False, {
                "code": "NEGATIVE_START_FRAME",
                "category": "validation",
                "message": f"VFX segment {i} has negative start frame: {start_frames}",
                "recoverable": True,
                "suggestion": "Start frame must be non-negative"
            }
        
        if end_frames < 0:
            return False, {
                "code": "NEGATIVE_END_FRAME",
                "category": "validation",
                "message": f"VFX segment {i} has negative end frame: {end_frames}",
                "recoverable": True,
                "suggestion": "End frame must be non-negative"
            }
        
        # Check start < end
        if start_frames >= end_frames:
            return False, {
                "code": "INVALID_SEGMENT_RANGE",
                "category": "validation",
                "message": f"VFX segment {i}: start frame ({start_frames}) >= end frame ({end_frames})",
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
                "message": f"VFX segment {i}: frame count exceeds maximum reasonable value ({MAX_REASONABLE_FRAMES})",
                "recoverable": True,
                "suggestion": "Check timeline duration - maximum supported is approximately 92 hours at 30fps"
            }
        
        # Validate track number if provided (must be 11-14 for VFX)
        track_number = segment.get("track_number", VFX_TRACK_START)
        if not isinstance(track_number, int) or track_number < VFX_TRACK_START or track_number > VFX_TRACK_END:
            return False, {
                "code": "INVALID_TRACK_NUMBER",
                "category": "validation",
                "message": f"VFX segment {i}: track_number must be an integer between {VFX_TRACK_START} and {VFX_TRACK_END}, got {track_number}",
                "recoverable": True,
                "suggestion": f"VFX tracks must be in range {VFX_TRACK_START}-{VFX_TRACK_END}"
            }
        
        # Validate template type if provided
        template_type = segment.get("template_type", "generic")
        if template_type not in VFX_TEMPLATE_DEFAULTS:
            return False, {
                "code": "INVALID_TEMPLATE_TYPE",
                "category": "validation",
                "message": f"VFX segment {i}: unknown template_type '{template_type}'",
                "recoverable": True,
                "suggestion": f"Valid template types: {', '.join(VFX_TEMPLATE_DEFAULTS.keys())}"
            }
        
        # Validate fade durations if provided
        fade_in = segment.get("fade_in_seconds", DEFAULT_VFX_FADE_IN_SECONDS)
        fade_out = segment.get("fade_out_seconds", DEFAULT_VFX_FADE_OUT_SECONDS)
        
        # Check type is numeric but NOT boolean (bool is subclass of int in Python)
        if not isinstance(fade_in, (int, float)) or isinstance(fade_in, bool) or fade_in < 0:
            return False, {
                "code": "INVALID_FADE_IN",
                "category": "validation",
                "message": f"VFX segment {i}: fade_in_seconds must be a non-negative number (not boolean)",
                "recoverable": True,
                "suggestion": "Fade duration must be a numeric value >= 0 seconds"
            }
        
        if not isinstance(fade_out, (int, float)) or isinstance(fade_out, bool) or fade_out < 0:
            return False, {
                "code": "INVALID_FADE_OUT",
                "category": "validation",
                "message": f"VFX segment {i}: fade_out_seconds must be a non-negative number (not boolean)",
                "recoverable": True,
                "suggestion": "Fade duration must be a numeric value >= 0 seconds"
            }
        
        # Validate template_params is a dict if provided
        template_params = segment.get("template_params")
        if template_params is not None:
            if not isinstance(template_params, dict):
                return False, {
                    "code": "INVALID_TEMPLATE_PARAMS",
                    "category": "validation",
                    "message": f"VFX segment {i}: template_params must be a dictionary",
                    "recoverable": True,
                    "suggestion": "template_params should be a dictionary of parameter names and values"
                }
            
            # Validate template_params keys are strings and values are simple types
            for key, value in template_params.items():
                if not isinstance(key, str):
                    return False, {
                        "code": "INVALID_TEMPLATE_PARAMS_KEY",
                        "category": "validation",
                        "message": f"VFX segment {i}: template_params keys must be strings, got {type(key).__name__}",
                        "recoverable": True,
                        "suggestion": "All template parameter names should be strings"
                    }
                # Values should be simple JSON-serializable types
                if not isinstance(value, (str, int, float, bool, type(None))):
                    return False, {
                        "code": "INVALID_TEMPLATE_PARAMS_VALUE",
                        "category": "validation",
                        "message": f"VFX segment {i}: template_params['{key}'] has invalid type {type(value).__name__}",
                        "recoverable": True,
                        "suggestion": "Template parameter values should be strings, numbers, booleans, or null"
                    }
    
    return True, None


def detect_vfx_type(file_path: str) -> str:
    """Detect if VFX is Fusion composition or generator effect.
    
    Args:
        file_path: Path to the VFX file
        
    Returns:
        String indicating VFX type: "fusion_composition", "generator_effect", or "unknown"
    """
    file_path_lower = file_path.lower()
    if file_path_lower.endswith('.comp'):
        return "fusion_composition"
    elif file_path_lower.endswith('.setting'):
        return "generator_effect"
    else:
        # Default to generator for unknown types
        return "generator_effect"


def apply_template_params(template_type: str, ai_params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply default template parameters and override with AI-provided values.
    
    Args:
        template_type: Type of VFX template (lower_third, outro_cta, etc.)
        ai_params: Parameters provided by AI (may be None)
        
    Returns:
        Dictionary with merged default and AI parameters
    """
    defaults = VFX_TEMPLATE_DEFAULTS.get(template_type, VFX_TEMPLATE_DEFAULTS["generic"])
    if ai_params:
        return {**defaults, **ai_params}
    return defaults.copy()


@dataclass
class VfxPlacement:
    """Placement of a VFX template on the timeline.
    
    Attributes:
        segment_index: 1-based segment number from AI
        track_number: Track number (11-14 for VFX tracks)
        timeline_start_frame: Start position on timeline
        timeline_end_frame: End position on timeline
        vfx_file_path: Absolute path to the VFX file
        clip_id: Resolve's clip reference (set after creation)
        fade_in_frames: Fade in duration in frames
        fade_out_frames: Fade out duration in frames
        template_type: Type of VFX template (lower_third, outro_cta, etc.)
        template_params: Applied template parameters
        vfx_type: Detected VFX type (fusion_composition or generator_effect)
    """
    segment_index: int
    track_number: int
    timeline_start_frame: int
    timeline_end_frame: int
    vfx_file_path: str
    clip_id: Optional[str] = None
    fade_in_frames: int = 0
    fade_out_frames: int = 0
    template_type: str = "generic"
    template_params: Dict[str, Any] = field(default_factory=dict)
    vfx_type: str = "generator_effect"


@dataclass
class VfxPlacerResult:
    """Result of a VFX placement operation.
    
    Attributes:
        clips_placed: Number of successfully placed VFX clips
        tracks_used: List of track numbers that were used
        total_duration_frames: Total duration of all VFX clips on timeline
        timeline_positions: List of VFX placements with timeline positions
        failed_segments: List of segment indices that failed to place (if any)
        success: Whether the operation succeeded
        error: Error details if operation failed
        fps: Frames per second for timecode conversion
    """
    clips_placed: int
    tracks_used: List[int]
    total_duration_frames: int
    timeline_positions: List[VfxPlacement]
    failed_segments: List[int] = field(default_factory=list)
    success: bool = True
    error: Optional[Dict[str, Any]] = None
    fps: int = 30  # Frames per second for timecode conversion
    
    def get_total_duration_timecode(self, fps: Optional[int] = None) -> str:
        """Get total duration as timecode string.
        
        Args:
            fps: Frames per second (defaults to self.fps or 30)
            
        Returns:
            Timecode string in format "H:MM:SS"
            
        Raises:
            ValueError: If fps is not a positive integer within reasonable bounds
        """
        use_fps = fps or self.fps or 30
        
        # Validate fps is within reasonable bounds (1-1000)
        if not isinstance(use_fps, (int, float)) or use_fps <= 0 or use_fps > 1000:
            raise ValueError(f"FPS must be a positive number between 1 and 1000, got {use_fps}")
        
        return frames_to_timecode(self.total_duration_frames, fps=int(use_fps))
    
    @property
    def total_duration_timecode(self) -> str:
        """Get total duration as timecode string (uses default fps)."""
        return self.get_total_duration_timecode()


class VfxPlacer:
    """Places AI-suggested VFX templates on the timeline.
    
    This class handles:
    - VFX template placement on dedicated VFX tracks (Tracks 11-14)
    - Track allocation for multiple VFX (conflict detection)
    - Fade in/out transitions (0.5-second default)
    - Template parameter management (defaults + AI overrides)
    - Fusion composition vs generator effect detection
    - Progress reporting during placement operations
    - Integration with Resolve's timeline API
    
    Usage:
        placer = VfxPlacer()
        result = placer.place_vfx_templates(
            timeline_id="RoughCut_interview_001_youtube_2026-04-04",
            vfx_segments=[
                {
                    "segment_index": 1,
                    "vfx_file_path": "/path/to/lower_third.comp",
                    "start_frames": 450,
                    "end_frames": 600,
                    "fade_in_seconds": 0.5,
                    "fade_out_seconds": 0.5,
                    "template_type": "lower_third",
                    "template_params": {"speaker_name": "John Doe", "title": "CEO"}
                }
            ]
        )
    """
    
    def __init__(self, resolve_api: Optional[ResolveApi] = None):
        """Initialize the VFX placer.
        
        Args:
            resolve_api: Optional ResolveApi instance for testing/mocking.
                        If not provided, a new instance will be created.
        """
        self.resolve_api = resolve_api or ResolveApi()
        logger.info("VfxPlacer initialized")
    
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
        # Use round() instead of int() to avoid truncation errors with floating point
        return round(seconds * fps)
    
    def _check_track_conflict(
        self,
        track_number: int,
        start_frame: int,
        end_frame: int,
        existing_placements: List[VfxPlacement]
    ) -> bool:
        """Check if a VFX segment conflicts with existing placements on a track.
        
        Args:
            track_number: Track to check
            start_frame: Proposed start frame
            end_frame: Proposed end frame
            existing_placements: List of already placed VFX segments
            
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
    
    def _allocate_vfx_track(
        self,
        preferred_track: int,
        start_frame: int,
        end_frame: int,
        existing_placements: List[VfxPlacement]
    ) -> int:
        """Allocate the best available track for a VFX segment.
        
        First tries the preferred track, then searches for available tracks
        in the VFX track range (11-14). If the preferred track has a time 
        conflict (overlap), searches upward from preferred+1 to VFX_TRACK_END,
        then downward from VFX_TRACK_START to preferred-1.
        
        Args:
            preferred_track: Preferred track number (usually 11 for first VFX)
            start_frame: Start frame of the VFX segment on timeline
            end_frame: End frame of the VFX segment on timeline
            existing_placements: Already placed VFX segments to check for conflicts
            
        Returns:
            Track number to use for this segment (11-14)
            
        Raises:
            TrackAllocationError: If all VFX tracks (11-14) have time conflicts
        """
        # Ensure preferred track is in valid range
        if preferred_track < VFX_TRACK_START:
            preferred_track = VFX_TRACK_START
        if preferred_track > VFX_TRACK_END:
            preferred_track = VFX_TRACK_END
        
        # Check preferred track first
        if not self._check_track_conflict(preferred_track, start_frame, end_frame, existing_placements):
            return preferred_track
        
        # Try additional tracks in range (12, 13, 14)
        for track in range(preferred_track + 1, VFX_TRACK_END + 1):
            if not self._check_track_conflict(track, start_frame, end_frame, existing_placements):
                logger.debug(f"Allocated track {track} for VFX segment (track {preferred_track} occupied)")
                return track
        
        # Try tracks before preferred (in case preferred was > 11)
        for track in range(VFX_TRACK_START, preferred_track):
            if not self._check_track_conflict(track, start_frame, end_frame, existing_placements):
                logger.debug(f"Allocated track {track} for VFX segment (lower track available)")
                return track
        
        # All VFX tracks full - raise error
        raise TrackAllocationError(
            f"All VFX tracks ({VFX_TRACK_START}-{VFX_TRACK_END}) are full. "
            f"Cannot place VFX at frames {start_frame}-{end_frame}."
        )
    
    def _find_vfx_in_media_pool(self, file_path: str) -> Optional[Any]:
        """Find a VFX file in Resolve's Media Pool.
        
        Args:
            file_path: Absolute path to the VFX file
            
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
                            logger.debug(f"Found VFX in media pool: {file_path}")
                            return clip
                except Exception as e:
                    logger.debug(f"Error checking clip properties: {e}")
                    continue
            
            logger.debug(f"VFX not found in media pool: {file_path}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching media pool for VFX: {e}")
            return None
    
    def _import_vfx_to_pool(self, file_path: str) -> Optional[Any]:
        """Import a VFX file into Resolve's Media Pool.
        
        Args:
            file_path: Absolute path to the VFX file
            
        Returns:
            Media Pool clip object if successful, None otherwise
        """
        media_pool = self.resolve_api.get_media_pool()
        if not media_pool:
            logger.error("Cannot import VFX - Media Pool not available")
            return None
        
        try:
            # Check if already in pool
            existing = self._find_vfx_in_media_pool(file_path)
            if existing:
                logger.info(f"VFX already in pool, using existing: {file_path}")
                return existing
            
            # Import the VFX file
            root_folder = media_pool.GetRootFolder()
            if not root_folder:
                logger.error("Could not get media pool root folder for import")
                return None
            
            imported_items = media_pool.ImportMedia([file_path])
            
            if imported_items and len(imported_items) > 0:
                logger.info(f"Successfully imported VFX: {file_path}")
                return imported_items[0]
            else:
                logger.warning(f"ImportMedia returned empty result for: {file_path}")
                return None
                
        except Exception as e:
            logger.exception(f"Error importing VFX to pool: {file_path}")
            return None
    
    def _create_timeline_vfx_clip(
        self,
        timeline: Any,
        vfx_clip: Any,
        track_index: int,
        timeline_position: int,
        source_in: int,
        source_out: int,
        vfx_type: str
    ) -> Optional[str]:
        """Create a timeline clip for VFX with specified in/out points.
        
        Args:
            timeline: Resolve timeline object
            vfx_clip: Media Pool VFX clip object
            track_index: Target track number (11+ for VFX)
            timeline_position: Frame position on timeline
            source_in: In point frame on source VFX clip
            source_out: Out point frame on source VFX clip
            vfx_type: Type of VFX (fusion_composition or generator_effect)
            
        Returns:
            Clip ID if successful, None otherwise
        """
        try:
            # Check source clip duration if possible
            source_duration = None
            if hasattr(vfx_clip, 'GetDuration'):
                try:
                    source_duration = vfx_clip.GetDuration()
                except Exception:
                    pass
            
            requested_duration = source_out - source_in
            
            # Warn if source is shorter than requested duration
            if source_duration is not None and requested_duration > source_duration:
                logger.warning(
                    f"Requested VFX duration ({requested_duration} frames) exceeds "
                    f"source clip duration ({source_duration} frames). "
                    f"Resolve may extend with blank frames or loop."
                )
            
            # Use AddClip on timeline for VFX placement
            if hasattr(timeline, 'AddClip'):
                result = timeline.AddClip(
                    vfx_clip,
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
                                vfx_clip, timeline_position, source_in, source_out
                            )
                        
                        logger.debug(
                            f"Created VFX clip: {clip_id} at track {track_index}, "
                            f"position {timeline_position}, duration {requested_duration}, "
                            f"type {vfx_type}"
                        )
                        return clip_id
                    except Exception as e:
                        logger.debug(f"Could not get clip ID from result: {e}")
                        return self._generate_stable_clip_id(
                            vfx_clip, timeline_position, source_in, source_out
                        )
            
            logger.error("No suitable API method available for creating VFX clip")
            return None
            
        except Exception as e:
            logger.exception(f"Error creating VFX timeline clip: {e}")
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
        id_string = f"vfx_{source_name}_{timeline_position}_{source_in}_{source_out}"
        return hashlib.md5(id_string.encode('utf-8', errors='replace')).hexdigest()[:16]
    
    def _apply_fade_transitions(
        self,
        timeline: Any,
        clip_id: str,
        fade_in_frames: int,
        fade_out_frames: int
    ) -> bool:
        """Apply fade in/out transitions to a VFX clip.
        
        Note: This is a placeholder implementation. The actual Resolve API
        for setting fade transitions varies by version and may require different
        approaches (Fusion composition parameters, keyframes, or clip properties).
        
        Args:
            timeline: Resolve timeline object
            clip_id: ID of the clip to apply fades to
            fade_in_frames: Fade in duration in frames
            fade_out_frames: Fade out duration in frames
            
        Returns:
            False - fades are not actually applied via API (documented only)
        """
        # Currently, Resolve's API for setting fade transitions on VFX is limited.
        # This is documented for future implementation when API support improves.
        # For now, fades are documented in the placement result for manual adjustment.
        # Returns False to indicate fades were not actually applied via API.
        
        logger.debug(
            f"Fade transitions documented for VFX clip {clip_id}: "
            f"fade_in={fade_in_frames} frames, fade_out={fade_out_frames} frames "
            f"(manual adjustment required - Resolve API limitation)"
        )
        return False
    
    def place_vfx_templates(
        self,
        timeline_id: str,
        vfx_segments: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> VfxPlacerResult:
        """Place VFX templates on the timeline.
        
        This is the main entry point for VFX placement. It performs
        all operations non-destructively - placing VFX on dedicated
        tracks (11-14) without affecting existing content on tracks 1-10.
        
        Args:
            timeline_id: ID of the target timeline
            vfx_segments: List of VFX segment dictionaries with timing info
            progress_callback: Optional callback for progress updates.
                             Called as progress_callback(current, total, message)
            
        Returns:
            VfxPlacerResult with details of placed clips
            
        Note:
            No exceptions raised - all errors are captured in result.error
        """
        logger.info(
            f"Starting VFX placement: {len(vfx_segments)} VFX templates for timeline {timeline_id}"
        )
        
        # Validate timeline_id
        if not timeline_id or not isinstance(timeline_id, str):
            logger.error(f"Invalid timeline_id: {timeline_id}")
            return VfxPlacerResult(
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
        is_valid, error = validate_vfx_segments(vfx_segments)
        if not is_valid:
            logger.error(f"VFX segment validation failed: {error}")
            return VfxPlacerResult(
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
            return VfxPlacerResult(
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
            return VfxPlacerResult(
                clips_placed=0,
                tracks_used=[],
                total_duration_frames=0,
                timeline_positions=[],
                success=False,
                error=error
            )
        
        # Verify timeline has sufficient tracks for VFX (at least track 11 should exist)
        try:
            # Check if timeline supports track count query
            if hasattr(timeline, 'GetTrackCount'):
                track_count = timeline.GetTrackCount()
                if track_count < VFX_TRACK_START:
                    logger.warning(f"Timeline has only {track_count} tracks, but VFX requires track {VFX_TRACK_START}")
                    # Continue anyway - Resolve may auto-create tracks
        except Exception as e:
            logger.debug(f"Could not verify track count: {e}")
            # Continue - not all Resolve versions support this
        
        # Initialize result tracking
        successful_placements: List[VfxPlacement] = []
        failed_segments: List[int] = []  # Track which segments failed
        tracks_used: set = set()
        total_duration = 0
        
        try:
            # Process each VFX segment
            for i, segment in enumerate(vfx_segments):
                segment_index = segment["segment_index"]
                file_path = segment["vfx_file_path"]
                start_frames = segment["start_frames"]
                end_frames = segment["end_frames"]
                preferred_track = segment.get("track_number", VFX_TRACK_START)
                template_type = segment.get("template_type", "generic")
                ai_template_params = segment.get("template_params", {})
                
                # Detect VFX type
                vfx_type = detect_vfx_type(file_path)
                
                # Apply template parameters (defaults + AI overrides)
                template_params = apply_template_params(template_type, ai_template_params)
                
                # Calculate fade durations in frames
                fade_in_seconds = segment.get("fade_in_seconds", DEFAULT_VFX_FADE_IN_SECONDS)
                fade_out_seconds = segment.get("fade_out_seconds", DEFAULT_VFX_FADE_OUT_SECONDS)
                fade_in_frames = self._seconds_to_frames(fade_in_seconds)
                fade_out_frames = self._seconds_to_frames(fade_out_seconds)
                
                # Report progress
                progress_msg = f"Placing VFX: {os.path.basename(file_path)} at {frames_to_timecode(start_frames)}"
                logger.info(f"Progress: {progress_msg} ({i + 1}/{len(vfx_segments)})")
                
                if progress_callback:
                    try:
                        progress_callback(i + 1, len(vfx_segments), progress_msg)
                    except Exception as callback_err:
                        logger.exception(
                            f"Progress callback failed for segment {segment_index}: "
                            f"{type(callback_err).__name__}: {callback_err}"
                        )
                        # Continue with placement - callback failure shouldn't abort operation
                
                # Import VFX to Media Pool if not already there
                vfx_clip = self._import_vfx_to_pool(file_path)
                if not vfx_clip:
                    logger.warning(f"Failed to import VFX for segment {segment_index}: {file_path}")
                    failed_segments.append(segment_index)
                    # Continue with other segments (don't fail entire operation)
                    continue
                
                # Allocate track (handle overlapping)
                try:
                    actual_track = self._allocate_vfx_track(
                        preferred_track,
                        start_frames,
                        end_frames,
                        successful_placements
                    )
                except TrackAllocationError as e:
                    logger.error(f"Track allocation failed for VFX segment {segment_index}: {e}")
                    failed_segments.append(segment_index)
                    # Continue with other segments
                    continue
                
                # Create timeline clip
                clip_id = self._create_timeline_vfx_clip(
                    timeline=timeline,
                    vfx_clip=vfx_clip,
                    track_index=actual_track,
                    timeline_position=start_frames,
                    source_in=0,  # Use full VFX clip from start
                    source_out=end_frames - start_frames,  # Duration needed
                    vfx_type=vfx_type
                )
                
                if clip_id:
                    # Create placement record
                    placement = VfxPlacement(
                        segment_index=segment_index,
                        track_number=actual_track,
                        timeline_start_frame=start_frames,
                        timeline_end_frame=end_frames,
                        vfx_file_path=file_path,
                        clip_id=clip_id,
                        fade_in_frames=fade_in_frames,
                        fade_out_frames=fade_out_frames,
                        template_type=template_type,
                        template_params=template_params,
                        vfx_type=vfx_type
                    )
                    
                    successful_placements.append(placement)
                    tracks_used.add(actual_track)
                    total_duration += (end_frames - start_frames)
                    
                    # Apply fade transitions (documented even if API limited)
                    self._apply_fade_transitions(timeline, clip_id, fade_in_frames, fade_out_frames)
                    
                    logger.debug(f"VFX segment {segment_index} placed successfully on track {actual_track}")
                else:
                    logger.warning(f"Failed to create timeline clip for VFX segment {segment_index}")
                    failed_segments.append(segment_index)
                    # Continue with other segments
            
            # Log completion
            logger.info(
                f"VFX placement complete: {len(successful_placements)}/{len(vfx_segments)} "
                f"clips placed, {len(failed_segments)} failed, tracks used: {sorted(tracks_used)}, "
                f"total duration: {total_duration} frames"
            )
            
            return VfxPlacerResult(
                clips_placed=len(successful_placements),
                tracks_used=sorted(list(tracks_used)),
                total_duration_frames=total_duration,
                timeline_positions=successful_placements,
                failed_segments=failed_segments,
                success=len(successful_placements) > 0
            )
            
        except Exception as e:
            logger.exception(f"Unexpected error during VFX placement: {e}")
            return VfxPlacerResult(
                clips_placed=len(successful_placements),
                tracks_used=sorted(list(tracks_used)),
                total_duration_frames=total_duration,
                timeline_positions=successful_placements,
                failed_segments=failed_segments,
                success=False,
                error={
                    "code": "INTERNAL_ERROR",
                    "category": "internal",
                    "message": f"Unexpected error during VFX placement: {str(e)}",
                    "recoverable": True,
                    "suggestion": "Check application logs and retry the operation"
                }
            )


class TrackAllocationError(Exception):
    """Raised when all VFX tracks are full and no allocation is possible."""
    pass
