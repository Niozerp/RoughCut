"""Music placer for placing audio clips on timeline tracks.

Handles the placement of AI-suggested music clips on the timeline's dedicated
music track (Track 2) with proper timing, fade handles, and format compliance.
"""

import hashlib
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .resolve_api import ResolveApi
from .cutter import timecode_to_frames, frames_to_timecode

logger = logging.getLogger(__name__)


# Default fade durations in seconds
DEFAULT_FADE_IN_SECONDS = 2.0
DEFAULT_FADE_OUT_SECONDS = 2.0

# Default music track
DEFAULT_MUSIC_TRACK = 2

# Maximum number of music tracks to support overlapping
MAX_MUSIC_TRACKS = 8


def validate_music_segments(segments: List[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate a list of music segments for placement.
    
    Checks:
    - Segments list is not empty
    - Each segment has required fields (segment_index, music_file_path, start_frames, end_frames)
    - Music file paths are valid absolute paths
    - Start frame < end frame for each segment
    - No negative frame values
    - Track numbers are valid (2+)
    
    Args:
        segments: List of music segment dictionaries
        
    Returns:
        Tuple of (is_valid, error_dict)
        - is_valid: True if all validations pass
        - error_dict: None if valid, or error details if invalid
    """
    if not segments:
        return False, {
            "code": "NO_MUSIC_SEGMENTS",
            "category": "validation",
            "message": "No music segments provided for placement",
            "recoverable": True,
            "suggestion": "Ensure AI rough cut generation produced music suggestions"
        }
    
    seen_indexes = set()
    
    for i, segment in enumerate(segments):
        # Check segment is a dict
        if not isinstance(segment, dict):
            return False, {
                "code": "INVALID_SEGMENT_TYPE",
                "category": "validation",
                "message": f"Music segment {i} is not a dictionary",
                "recoverable": True,
                "suggestion": "Each music segment must be a dictionary with file path and timing data"
            }
        
        # Check required fields
        required_fields = ["segment_index", "music_file_path", "start_frames", "end_frames"]
        for field_name in required_fields:
            if field_name not in segment:
                return False, {
                    "code": f"MISSING_{field_name.upper()}",
                    "category": "validation",
                    "message": f"Music segment {i} missing {field_name} field",
                    "recoverable": True,
                    "suggestion": f"Verify segment data includes {field_name} field"
                }
        
        segment_index = segment["segment_index"]
        
        # Validate segment_index type and value
        if not isinstance(segment_index, int):
            return False, {
                "code": "INVALID_INDEX_TYPE",
                "category": "validation",
                "message": f"Music segment {i}: segment_index must be an integer, got {type(segment_index).__name__}",
                "recoverable": True,
                "suggestion": "segment_index must be a positive integer"
            }
        
        if segment_index < 1:
            return False, {
                "code": "INVALID_INDEX_VALUE",
                "category": "validation",
                "message": f"Music segment {i}: segment_index must be >= 1, got {segment_index}",
                "recoverable": True,
                "suggestion": "segment_index must be a positive integer starting from 1"
            }
        
        # Check for duplicate segment_index values
        if segment_index in seen_indexes:
            return False, {
                "code": "DUPLICATE_INDEX",
                "category": "validation",
                "message": f"Duplicate music segment_index: {segment_index}",
                "recoverable": True,
                "suggestion": "Each music segment must have a unique segment_index"
            }
        seen_indexes.add(segment_index)
        
        # Validate music file path
        file_path = segment["music_file_path"]
        if not isinstance(file_path, str):
            return False, {
                "code": "INVALID_FILE_PATH_TYPE",
                "category": "validation",
                "message": f"Music segment {i}: music_file_path must be a string",
                "recoverable": True,
                "suggestion": "File path must be a string"
            }
        
        if not file_path:
            return False, {
                "code": "EMPTY_FILE_PATH",
                "category": "validation",
                "message": f"Music segment {i}: music_file_path is empty",
                "recoverable": True,
                "suggestion": "Provide a valid music file path"
            }
        
        # Check if absolute path
        if not os.path.isabs(file_path):
            return False, {
                "code": "RELATIVE_FILE_PATH",
                "category": "validation",
                "message": f"Music segment {i}: music_file_path must be absolute, got: {file_path}",
                "recoverable": True,
                "suggestion": "Use absolute file paths for music files"
            }
        
        # Check if file exists and is readable
        if not os.path.exists(file_path):
            return False, {
                "code": "MUSIC_FILE_NOT_FOUND",
                "category": "file_system",
                "message": f"Music segment {i}: file not found at path: {file_path}",
                "recoverable": True,
                "suggestion": "Verify the music file exists and the path is correct"
            }
        
        if not os.access(file_path, os.R_OK):
            return False, {
                "code": "MUSIC_FILE_NOT_READABLE",
                "category": "file_system",
                "message": f"Music segment {i}: file not readable: {file_path}",
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
                "message": f"Music segment {i}: start_frames and end_frames must be integers",
                "recoverable": True,
                "suggestion": "Frame values must be integer frame counts"
            }
        
        # Check for negative values
        if start_frames < 0:
            return False, {
                "code": "NEGATIVE_START_FRAME",
                "category": "validation",
                "message": f"Music segment {i} has negative start frame: {start_frames}",
                "recoverable": True,
                "suggestion": "Start frame must be non-negative"
            }
        
        if end_frames < 0:
            return False, {
                "code": "NEGATIVE_END_FRAME",
                "category": "validation",
                "message": f"Music segment {i} has negative end frame: {end_frames}",
                "recoverable": True,
                "suggestion": "End frame must be non-negative"
            }
        
        # Check start < end
        if start_frames >= end_frames:
            return False, {
                "code": "INVALID_SEGMENT_RANGE",
                "category": "validation",
                "message": f"Music segment {i}: start frame ({start_frames}) >= end frame ({end_frames})",
                "recoverable": True,
                "suggestion": "Segment start must be less than segment end"
            }
        
        # Validate track number if provided
        track_number = segment.get("track_number", DEFAULT_MUSIC_TRACK)
        if not isinstance(track_number, int) or track_number < DEFAULT_MUSIC_TRACK:
            return False, {
                "code": "INVALID_TRACK_NUMBER",
                "category": "validation",
                "message": f"Music segment {i}: track_number must be an integer >= {DEFAULT_MUSIC_TRACK}, got {track_number}",
                "recoverable": True,
                "suggestion": f"Music tracks start at {DEFAULT_MUSIC_TRACK}"
            }
        
        # Validate fade durations if provided
        fade_in = segment.get("fade_in_seconds", DEFAULT_FADE_IN_SECONDS)
        fade_out = segment.get("fade_out_seconds", DEFAULT_FADE_OUT_SECONDS)
        
        if not isinstance(fade_in, (int, float)) or fade_in < 0:
            return False, {
                "code": "INVALID_FADE_IN",
                "category": "validation",
                "message": f"Music segment {i}: fade_in_seconds must be a non-negative number",
                "recoverable": True,
                "suggestion": "Fade duration must be >= 0 seconds"
            }
        
        if not isinstance(fade_out, (int, float)) or fade_out < 0:
            return False, {
                "code": "INVALID_FADE_OUT",
                "category": "validation",
                "message": f"Music segment {i}: fade_out_seconds must be a non-negative number",
                "recoverable": True,
                "suggestion": "Fade duration must be >= 0 seconds"
            }
    
    return True, None


@dataclass
class MusicPlacement:
    """Placement of a music clip on the timeline.
    
    Attributes:
        segment_index: 1-based segment number from AI
        track_number: Track number (2 = primary music track)
        timeline_start_frame: Start position on timeline
        timeline_end_frame: End position on timeline
        music_file_path: Absolute path to the music file
        clip_id: Resolve's clip reference (set after creation)
        fade_in_frames: Fade in duration in frames
        fade_out_frames: Fade out duration in frames
        section_type: Type of section (intro, bed, outro, transition)
    """
    segment_index: int
    track_number: int
    timeline_start_frame: int
    timeline_end_frame: int
    music_file_path: str
    clip_id: Optional[str] = None
    fade_in_frames: int = 0
    fade_out_frames: int = 0
    section_type: str = "bed"


@dataclass
class MusicPlacerResult:
    """Result of a music placement operation.
    
    Attributes:
        clips_placed: Number of successfully placed music clips
        tracks_used: List of track numbers that were used
        total_duration_frames: Total duration of all music clips on timeline
        total_duration_timecode: Total duration as timecode string
        timeline_positions: List of music placements with timeline positions
        success: Whether the operation succeeded
        error: Error details if operation failed
    """
    clips_placed: int
    tracks_used: List[int]
    total_duration_frames: int
    timeline_positions: List[MusicPlacement]
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


class MusicPlacer:
    """Places AI-suggested music clips on the timeline.
    
    This class handles:
    - Music clip placement on dedicated music track(s)
    - Format timing compliance (intro at 0:00, bed at X, etc.)
    - Fade in/out handles for audio transitions
    - Multiple/overlapping music piece handling
    - Progress reporting during placement operations
    - Integration with Resolve's timeline API
    
    Usage:
        placer = MusicPlacer()
        result = placer.place_music_clips(
            timeline_id="RoughCut_interview_001_youtube_2026-04-04",
            music_segments=[
                {
                    "segment_index": 1,
                    "music_file_path": "/path/to/intro.wav",
                    "start_frames": 0,
                    "end_frames": 900,
                    "fade_in_seconds": 2.0,
                    "fade_out_seconds": 2.0,
                    "section_type": "intro"
                }
            ]
        )
    """
    
    # Default track for music
    DEFAULT_MUSIC_TRACK = 2
    
    # Maximum batch size for processing
    MAX_BATCH_SIZE = 100
    
    def __init__(self, resolve_api: Optional[ResolveApi] = None):
        """Initialize the music placer.
        
        Args:
            resolve_api: Optional ResolveApi instance for testing/mocking.
                        If not provided, a new instance will be created.
        """
        self.resolve_api = resolve_api or ResolveApi()
        logger.info("MusicPlacer initialized")
    
    def _seconds_to_frames(self, seconds: float, fps: int = 30) -> int:
        """Convert seconds to frame count.
        
        Args:
            seconds: Duration in seconds
            fps: Frames per second (default 30)
            
        Returns:
            Frame count as integer
        """
        return int(seconds * fps)
    
    def _check_track_conflict(
        self,
        track_number: int,
        start_frame: int,
        end_frame: int,
        existing_placements: List[MusicPlacement]
    ) -> bool:
        """Check if a music segment conflicts with existing placements on a track.
        
        Args:
            track_number: Track to check
            start_frame: Proposed start frame
            end_frame: Proposed end frame
            existing_placements: List of already placed music segments
            
        Returns:
            True if there's a conflict (overlap), False if the track is clear
        """
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
    
    def _allocate_music_track(
        self,
        preferred_track: int,
        start_frame: int,
        end_frame: int,
        existing_placements: List[MusicPlacement]
    ) -> int:
        """Allocate the best available track for a music segment.
        
        First tries the preferred track, then searches for available tracks,
        finally creating new tracks if needed.
        
        Args:
            preferred_track: Preferred track number (usually 2)
            start_frame: Start frame of the music segment
            end_frame: End frame of the music segment
            existing_placements: Already placed music segments
            
        Returns:
            Track number to use for this segment
        """
        # Check preferred track first
        if not self._check_track_conflict(preferred_track, start_frame, end_frame, existing_placements):
            return preferred_track
        
        # Try additional tracks (3, 4, 5, etc.)
        max_track = preferred_track + MAX_MUSIC_TRACKS
        for track in range(preferred_track + 1, max_track + 1):
            if not self._check_track_conflict(track, start_frame, end_frame, existing_placements):
                logger.debug(f"Allocated track {track} for music segment (track {preferred_track} occupied)")
                return track
        
        # If all tracks full, return the last track with a warning
        # Note: This will overlap - caller should handle this case
        logger.warning(f"All music tracks full (2-{max_track}), using track {max_track} (will overlap)")
        return max_track
    
    def _find_music_in_media_pool(self, file_path: str) -> Optional[Any]:
        """Find a music file in Resolve's Media Pool.
        
        Args:
            file_path: Absolute path to the music file
            
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
                            logger.debug(f"Found music in media pool: {file_path}")
                            return clip
                except Exception as e:
                    logger.debug(f"Error checking clip properties: {e}")
                    continue
            
            logger.debug(f"Music not found in media pool: {file_path}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching media pool for music: {e}")
            return None
    
    def _import_music_to_pool(self, file_path: str) -> Optional[Any]:
        """Import a music file into Resolve's Media Pool.
        
        Args:
            file_path: Absolute path to the music file
            
        Returns:
            Media Pool clip object if successful, None otherwise
        """
        media_pool = self.resolve_api.get_media_pool()
        if not media_pool:
            logger.error("Cannot import music - Media Pool not available")
            return None
        
        try:
            # Check if already in pool
            existing = self._find_music_in_media_pool(file_path)
            if existing:
                logger.info(f"Music already in pool, using existing: {file_path}")
                return existing
            
            # Import the music file
            root_folder = media_pool.GetRootFolder()
            if not root_folder:
                logger.error("Could not get media pool root folder for import")
                return None
            
            imported_items = media_pool.ImportMedia([file_path])
            
            if imported_items and len(imported_items) > 0:
                logger.info(f"Successfully imported music: {file_path}")
                return imported_items[0]
            else:
                logger.warning(f"ImportMedia returned empty result for: {file_path}")
                return None
                
        except Exception as e:
            logger.exception(f"Error importing music to pool: {file_path}")
            return None
    
    def _create_timeline_music_clip(
        self,
        timeline: Any,
        music_clip: Any,
        track_index: int,
        timeline_position: int,
        source_in: int,
        source_out: int
    ) -> Optional[str]:
        """Create a timeline clip for music with specified in/out points.
        
        Args:
            timeline: Resolve timeline object
            music_clip: Media Pool music clip object
            track_index: Target track number (2+ for music)
            timeline_position: Frame position on timeline
            source_in: In point frame on source music clip
            source_out: Out point frame on source music clip
            
        Returns:
            Clip ID if successful, None otherwise
        """
        try:
            # Use AddClip on timeline for music placement
            if hasattr(timeline, 'AddClip'):
                duration = source_out - source_in
                
                result = timeline.AddClip(
                    music_clip,
                    track_index,
                    timeline_position,
                    duration
                )
                
                if result:
                    # Generate a stable clip ID
                    try:
                        if hasattr(result, 'GetName'):
                            clip_id = result.GetName()
                        else:
                            clip_id = self._generate_stable_clip_id(
                                music_clip, timeline_position, source_in, source_out
                            )
                        
                        logger.debug(
                            f"Created music clip: {clip_id} at track {track_index}, "
                            f"position {timeline_position}, duration {duration}"
                        )
                        return clip_id
                    except Exception as e:
                        logger.debug(f"Could not get clip ID from result: {e}")
                        return self._generate_stable_clip_id(
                            music_clip, timeline_position, source_in, source_out
                        )
            
            logger.error("No suitable API method available for creating music clip")
            return None
            
        except Exception as e:
            logger.exception(f"Error creating music timeline clip: {e}")
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
        id_string = f"music_{source_name}_{timeline_position}_{source_in}_{source_out}"
        return hashlib.md5(id_string.encode()).hexdigest()[:16]
    
    def _apply_fade_handles(
        self,
        timeline: Any,
        clip_id: str,
        fade_in_frames: int,
        fade_out_frames: int
    ) -> bool:
        """Apply fade in/out handles to a music clip.
        
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
            f"Fade handles documented for clip {clip_id}: "
            f"fade_in={fade_in_frames} frames, fade_out={fade_out_frames} frames"
        )
        return True
    
    def place_music_clips(
        self,
        timeline_id: str,
        music_segments: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> MusicPlacerResult:
        """Place music clips on the timeline.
        
        This is the main entry point for music placement. It performs
        all operations non-destructively - placing music on dedicated
        tracks without affecting existing content.
        
        Args:
            timeline_id: ID of the target timeline
            music_segments: List of music segment dictionaries with timing info
            progress_callback: Optional callback for progress updates.
                             Called as progress_callback(current, total, message)
            
        Returns:
            MusicPlacerResult with details of placed clips
            
        Note:
            No exceptions raised - all errors are captured in result.error
        """
        logger.info(
            f"Starting music placement: {len(music_segments)} music clips for timeline {timeline_id}"
        )
        
        # Validate timeline_id
        if not timeline_id or not isinstance(timeline_id, str):
            logger.error(f"Invalid timeline_id: {timeline_id}")
            return MusicPlacerResult(
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
        is_valid, error = validate_music_segments(music_segments)
        if not is_valid:
            logger.error(f"Music segment validation failed: {error}")
            return MusicPlacerResult(
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
            return MusicPlacerResult(
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
            return MusicPlacerResult(
                clips_placed=0,
                tracks_used=[],
                total_duration_frames=0,
                timeline_positions=[],
                success=False,
                error=error
            )
        
        # Initialize result tracking
        successful_placements: List[MusicPlacement] = []
        tracks_used: set = set()
        total_duration = 0
        
        try:
            # Process each music segment
            for i, segment in enumerate(music_segments):
                segment_index = segment["segment_index"]
                file_path = segment["music_file_path"]
                start_frames = segment["start_frames"]
                end_frames = segment["end_frames"]
                preferred_track = segment.get("track_number", self.DEFAULT_MUSIC_TRACK)
                section_type = segment.get("section_type", "bed")
                
                # Calculate fade durations in frames
                fade_in_seconds = segment.get("fade_in_seconds", DEFAULT_FADE_IN_SECONDS)
                fade_out_seconds = segment.get("fade_out_seconds", DEFAULT_FADE_OUT_SECONDS)
                fade_in_frames = self._seconds_to_frames(fade_in_seconds)
                fade_out_frames = self._seconds_to_frames(fade_out_seconds)
                
                # Report progress
                progress_msg = f"Placing music: {os.path.basename(file_path)}"
                logger.info(f"Progress: {progress_msg} ({i + 1}/{len(music_segments)})")
                
                if progress_callback:
                    try:
                        progress_callback(i + 1, len(music_segments), progress_msg)
                    except Exception as e:
                        logger.warning(f"Progress callback failed: {e}")
                        # Continue with placement - callback failure shouldn't abort operation
                
                # Import music to Media Pool if not already there
                music_clip = self._import_music_to_pool(file_path)
                if not music_clip:
                    logger.warning(f"Failed to import music: {file_path}")
                    # Continue with other segments (don't fail entire operation)
                    continue
                
                # Allocate track (handle overlapping)
                actual_track = self._allocate_music_track(
                    preferred_track,
                    start_frames,
                    end_frames,
                    successful_placements
                )
                
                # Create timeline clip
                clip_id = self._create_timeline_music_clip(
                    timeline=timeline,
                    music_clip=music_clip,
                    track_index=actual_track,
                    timeline_position=start_frames,
                    source_in=0,  # Use full music clip from start
                    source_out=end_frames - start_frames  # Duration needed
                )
                
                if clip_id:
                    # Create placement record
                    placement = MusicPlacement(
                        segment_index=segment_index,
                        track_number=actual_track,
                        timeline_start_frame=start_frames,
                        timeline_end_frame=end_frames,
                        music_file_path=file_path,
                        clip_id=clip_id,
                        fade_in_frames=fade_in_frames,
                        fade_out_frames=fade_out_frames,
                        section_type=section_type
                    )
                    
                    successful_placements.append(placement)
                    tracks_used.add(actual_track)
                    total_duration += (end_frames - start_frames)
                    
                    # Apply fade handles (documented even if API limited)
                    self._apply_fade_handles(timeline, clip_id, fade_in_frames, fade_out_frames)
                    
                    logger.debug(f"Music segment {segment_index} placed successfully on track {actual_track}")
                else:
                    logger.warning(f"Failed to place music segment {segment_index}")
                    # Continue with other segments
            
            # Log completion
            logger.info(
                f"Music placement complete: {len(successful_placements)}/{len(music_segments)} "
                f"clips placed, tracks used: {sorted(tracks_used)}, "
                f"total duration: {total_duration} frames"
            )
            
            return MusicPlacerResult(
                clips_placed=len(successful_placements),
                tracks_used=sorted(list(tracks_used)),
                total_duration_frames=total_duration,
                timeline_positions=successful_placements,
                success=len(successful_placements) > 0
            )
            
        except Exception as e:
            logger.exception(f"Unexpected error during music placement: {e}")
            return MusicPlacerResult(
                clips_placed=len(successful_placements),
                tracks_used=sorted(list(tracks_used)),
                total_duration_frames=total_duration,
                timeline_positions=successful_placements,
                success=False,
                error={
                    "code": "INTERNAL_ERROR",
                    "category": "internal",
                    "message": f"Unexpected error during music placement: {str(e)}",
                    "recoverable": True,
                    "suggestion": "Check application logs and retry the operation"
                }
            )
