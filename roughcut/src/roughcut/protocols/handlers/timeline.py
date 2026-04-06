"""Protocol handlers for timeline operations.

Handles JSON-RPC requests for creating and managing Resolve timelines.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict

from ...backend.timeline.builder import TimelineBuilder
from ...backend.timeline.cutter import FootageCutter, CutResult
from ...backend.timeline.importer import MediaImporter, ImportResult
from ...backend.timeline.music_placer import MusicPlacer, MusicPlacerResult
from ...backend.timeline.sfx_placer import SfxPlacer, SfxPlacerResult
from ...backend.timeline.vfx_placer import VfxPlacer, VfxPlacerResult, TrackAllocationError
from ...backend.workflows.session import get_session_manager

logger = logging.getLogger(__name__)

# Error codes for timeline operations
ERROR_CODES = {
    "INVALID_PARAMS": "INVALID_PARAMS",
    "SESSION_NOT_FOUND": "SESSION_NOT_FOUND",
    "MISSING_SOURCE_CLIP": "MISSING_SOURCE_CLIP",
    "MISSING_FORMAT_TEMPLATE": "MISSING_FORMAT_TEMPLATE",
    "TIMELINE_CREATION_FAILED": "TIMELINE_CREATION_FAILED",
    "RESOLVE_API_UNAVAILABLE": "RESOLVE_API_UNAVAILABLE",
    "INTERNAL_ERROR": "INTERNAL_ERROR",
    "IMPORT_FAILED": "IMPORT_FAILED",
    "MISSING_SUGGESTED_MEDIA": "MISSING_SUGGESTED_MEDIA",
    "CUTTING_FAILED": "CUTTING_FAILED",
    "MISSING_SEGMENTS": "MISSING_SEGMENTS",
    "TIMELINE_NOT_FOUND": "TIMELINE_NOT_FOUND",
    "SOURCE_CLIP_NOT_FOUND": "SOURCE_CLIP_NOT_FOUND",
    "SEGMENT_VALIDATION_FAILED": "SEGMENT_VALIDATION_FAILED",
    "MUSIC_PLACEMENT_FAILED": "MUSIC_PLACEMENT_FAILED",
    "MISSING_MUSIC_SEGMENTS": "MISSING_MUSIC_SEGMENTS",
    "SFX_PLACEMENT_FAILED": "SFX_PLACEMENT_FAILED",
    "MISSING_SFX_SEGMENTS": "MISSING_SFX_SEGMENTS",
    "TRACK_ALLOCATION_FAILED": "TRACK_ALLOCATION_FAILED",
    "VFX_PLACEMENT_FAILED": "VFX_PLACEMENT_FAILED",
    "MISSING_VFX_SEGMENTS": "MISSING_VFX_SEGMENTS"
}


def _error_response(
    code: str,
    category: str,
    message: str,
    suggestion: str,
    recoverable: bool = True
) -> Dict[str, Any]:
    """Create a standardized error response.
    
    Args:
        code: Error code
        category: Error category (resolve_api, internal, validation)
        message: Human-readable error message
        suggestion: Actionable suggestion for user
        recoverable: Whether the error is recoverable
        
    Returns:
        Error response dictionary
    """
    return {
        "error": {
            "code": code,
            "category": category,
            "message": message,
            "recoverable": recoverable,
            "suggestion": suggestion
        }
    }


def create_timeline_from_document(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Create a new Resolve timeline from a rough cut document.
    
    This handler is called from the Lua GUI when the user clicks
    "Create Timeline" after reviewing the AI-generated rough cut.
    
    Args:
        params: Request parameters containing:
            - session_id: Session UUID (required)
            - timeline_name: Optional custom timeline name
            
    Returns:
        Dictionary with timeline creation result or error
    """
    if params is None:
        params = {}
    
    # Validate required parameters
    session_id = params.get("session_id")
    if not session_id:
        logger.error("Missing session_id parameter")
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Session ID is required to create timeline",
            "Ensure the rough cut review session is active",
            recoverable=True
        )
    
    logger.info(f"Creating timeline for session: {session_id}")
    
    # Get session data
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    
    if not session:
        logger.error(f"Session not found: {session_id}")
        return _error_response(
            ERROR_CODES["SESSION_NOT_FOUND"],
            "validation",
            f"Session {session_id} not found or expired",
            "Generate a rough cut first before creating timeline",
            recoverable=True
        )
    
    # Extract required data from session
    source_clip = session.get("source_clip")
    format_template = session.get("format_template")
    
    if not source_clip:
        logger.error("Source clip not found in session")
        return _error_response(
            ERROR_CODES["MISSING_SOURCE_CLIP"],
            "validation",
            "Source clip information not found in session",
            "Select a source clip before generating rough cut",
            recoverable=True
        )
    
    if not format_template:
        logger.error("Format template not found in session")
        return _error_response(
            ERROR_CODES["MISSING_FORMAT_TEMPLATE"],
            "validation",
            "Format template information not found in session",
            "Select a format template before generating rough cut",
            recoverable=True
        )
    
    # Get rough cut document for additional metadata
    rough_cut_doc = session.get("rough_cut_document", {})
    
    # Determine source clip name
    source_clip_name = source_clip.get("name", "Untitled")
    if not source_clip_name or source_clip_name == "Untitled":
        # Try to get from rough cut document
        source_clip_name = rough_cut_doc.get("source_clip", "Untitled")
    
    # Determine format template name
    format_template_name = format_template.get("name", "Default")
    if not format_template_name or format_template_name == "Default":
        format_template_name = rough_cut_doc.get("format_template", "Default")
    
    # Use custom name if provided, otherwise generate
    custom_name = params.get("timeline_name")
    
    try:
        # Create the timeline
        builder = TimelineBuilder()
        
        result = builder.create_timeline(
            source_clip_name=source_clip_name,
            format_template=format_template_name,
            timestamp=None  # Let builder generate current timestamp
        )
        
        if result.success:
            logger.info(f"Timeline created successfully: {result.timeline_name}")
            
            # Update session with timeline info
            session["timeline_created"] = {
                "name": result.timeline_name,
                "id": result.timeline_id,
                "tracks": result.tracks_created
            }
            session_manager.update_session(session_id, session)
            
            return {
                "timeline_name": result.timeline_name,
                "timeline_id": result.timeline_id,
                "tracks_created": result.tracks_created,
                "success": True
            }
        else:
            logger.error(f"Timeline creation failed: {result.error}")
            return _error_response(
                result.error.get("code", ERROR_CODES["TIMELINE_CREATION_FAILED"]),
                result.error.get("category", "internal"),
                result.error.get("message", "Timeline creation failed"),
                result.error.get("suggestion", "Check Resolve is running and retry"),
                result.error.get("recoverable", True)
            )
            
    except Exception as e:
        logger.exception(f"Unexpected error in create_timeline_from_document: {e}")
        return _error_response(
            ERROR_CODES["INTERNAL_ERROR"],
            "internal",
            f"Unexpected error: {str(e)}",
            "Check application logs and report the issue",
            recoverable=False
        )


def create_timeline(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Create a timeline with explicit parameters.
    
    Alternative handler for direct timeline creation without
    requiring a session.
    
    Args:
        params: Request parameters containing:
            - source_clip_name: Name of source clip
            - format_template: Name of format template
            - timestamp: Optional timestamp
            
    Returns:
        Dictionary with timeline creation result or error
    """
    if params is None:
        params = {}
    
    # Validate required parameters
    source_clip_name = params.get("source_clip_name")
    format_template = params.get("format_template")
    
    if not source_clip_name:
        return _error_response(
            ERROR_CODES["MISSING_SOURCE_CLIP"],
            "validation",
            "source_clip_name is required",
            "Provide the source clip name for timeline naming",
            recoverable=True
        )
    
    if not format_template:
        return _error_response(
            ERROR_CODES["MISSING_FORMAT_TEMPLATE"],
            "validation",
            "format_template is required",
            "Provide the format template name for timeline naming",
            recoverable=True
        )
    
    timestamp = params.get("timestamp")
    
    try:
        builder = TimelineBuilder()
        result = builder.create_timeline(
            source_clip_name=source_clip_name,
            format_template=format_template,
            timestamp=timestamp
        )
        
        if result.success:
            return {
                "timeline_name": result.timeline_name,
                "timeline_id": result.timeline_id,
                "tracks_created": result.tracks_created,
                "success": True
            }
        else:
            return _error_response(
                result.error.get("code", ERROR_CODES["TIMELINE_CREATION_FAILED"]),
                result.error.get("category", "internal"),
                result.error.get("message", "Timeline creation failed"),
                result.error.get("suggestion", "Check Resolve is running and retry"),
                result.error.get("recoverable", True)
            )
            
    except Exception as e:
        logger.exception(f"Error in create_timeline: {e}")
        return _error_response(
            ERROR_CODES["INTERNAL_ERROR"],
            "internal",
            f"Unexpected error: {str(e)}",
            "Check application logs and report the issue",
            recoverable=False
        )


def import_suggested_media(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Import suggested media files into Resolve's Media Pool.
    
    This handler is called from the Lua GUI after timeline creation to import
    AI-suggested media assets (music, SFX, VFX) into the Media Pool.
    
    Args:
        params: Request parameters containing:
            - timeline_id: Timeline ID (optional, for context)
            - suggested_media: List of media items with file_path and media_type
            
    Returns:
        Dictionary with import results or error
    """
    if params is None:
        params = {}
    
    # Validate required parameters
    suggested_media = params.get("suggested_media")
    if not suggested_media:
        logger.error("Missing suggested_media parameter")
        return _error_response(
            ERROR_CODES["MISSING_SUGGESTED_MEDIA"],
            "validation",
            "No suggested media provided for import",
            "Ensure AI suggestions are available before importing",
            recoverable=True
        )
    
    if not isinstance(suggested_media, list):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "suggested_media must be a list",
            "Provide a list of media items with file_path and media_type",
            recoverable=True
        )
    
    logger.info(f"Importing {len(suggested_media)} suggested media files")
    
    try:
        # Create importer and import media
        importer = MediaImporter()
        result = importer.import_suggested_media(suggested_media)
        
        # Convert ImportResult to response format
        media_pool_refs = []
        for ref in result.media_pool_refs:
            media_pool_refs.append({
                "file_path": ref.file_path,
                "media_pool_id": ref.media_pool_id,
                "media_type": ref.media_type
            })
        
        response = {
            "imported_count": result.imported_count,
            "skipped_count": result.skipped_count,
            "media_pool_refs": media_pool_refs,
            "skipped_files": result.skipped_files,
            "success": result.success
        }
        
        # Add warnings if files were skipped
        if result.skipped_count > 0:
            skipped_names = [Path(s["file_path"]).name for s in result.skipped_files]
            response["warning"] = (
                f"Skipped {result.skipped_count} file(s): {', '.join(skipped_names)}. "
                "Timeline creation will continue with available assets."
            )
        
        logger.info(
            f"Import complete: {result.imported_count} imported, "
            f"{result.skipped_count} skipped"
        )
        
        return response
        
    except Exception as e:
        logger.exception(f"Error importing suggested media: {e}")
        return _error_response(
            ERROR_CODES["IMPORT_FAILED"],
            "internal",
            f"Failed to import suggested media: {str(e)}",
            "Check Resolve is running and media files are accessible",
            recoverable=True
        )


def cut_footage_to_segments(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Cut source footage into timeline segments according to AI recommendations.
    
    This handler is called from the Lua GUI after media import to cut the
    source video into segments based on the AI-generated transcript cuts.
    
    Args:
        params: Request parameters containing:
            - timeline_id: Target timeline ID (required)
            - source_clip_id: Source clip in Media Pool (required)
            - segments: List of segment dictionaries with timing info (required)
            
    Returns:
        Dictionary with cutting result or error
    """
    if params is None:
        params = {}
    
    # Validate required parameters
    timeline_id = params.get("timeline_id")
    if not timeline_id:
        logger.error("Missing timeline_id parameter")
        return _error_response(
            ERROR_CODES["TIMELINE_NOT_FOUND"],
            "validation",
            "Timeline ID is required",
            "Ensure timeline was created successfully before cutting",
            recoverable=True
        )
    
    source_clip_id = params.get("source_clip_id")
    if not source_clip_id:
        logger.error("Missing source_clip_id parameter")
        return _error_response(
            ERROR_CODES["SOURCE_CLIP_NOT_FOUND"],
            "validation",
            "Source clip ID is required",
            "Ensure source media was imported successfully before cutting",
            recoverable=True
        )
    
    segments = params.get("segments")
    if segments is None:
        logger.error("Missing segments parameter")
        return _error_response(
            ERROR_CODES["MISSING_SEGMENTS"],
            "validation",
            "No segments parameter provided",
            "Generate a rough cut with AI segment recommendations first",
            recoverable=True
        )
    
    if not isinstance(segments, list):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "segments must be a list",
            "Provide a list of segment dictionaries with timing info",
            recoverable=True
        )
    
    if len(segments) == 0:
        logger.error("Empty segments list provided")
        return _error_response(
            ERROR_CODES["MISSING_SEGMENTS"],
            "validation",
            "Segments list is empty",
            "Generate a rough cut with AI segment recommendations first",
            recoverable=True
        )
    
    logger.info(f"Cutting {len(segments)} segments for timeline {timeline_id}")
    
    try:
        # Create cutter and perform cutting
        cutter = FootageCutter()
        
        # Progress callback that emits JSON-RPC progress messages
        def progress_callback(current: int, total: int, message: str):
            # In a real implementation, this would emit to stdout
            # For now, we just log it
            logger.info(f"Progress: {message} ({current}/{total})")
        
        result = cutter.cut_segments(
            timeline_id=timeline_id,
            source_clip_id=source_clip_id,
            segments=segments,
            progress_callback=progress_callback
        )
        
        if result.success:
            # Convert placements to serializable format
            timeline_positions = []
            for placement in result.timeline_positions:
                timeline_positions.append({
                    "segment_index": placement.segment_index,
                    "timeline_track": placement.timeline_track,
                    "timeline_start_frame": placement.timeline_start_frame,
                    "timeline_end_frame": placement.timeline_end_frame,
                    "source_in_frame": placement.source_in_frame,
                    "source_out_frame": placement.source_out_frame,
                    "clip_id": placement.clip_id
                })
            
            logger.info(
                f"Cutting complete: {result.segments_placed} segments, "
                f"duration: {result.total_duration_timecode}"
            )
            
            return {
                "segments_placed": result.segments_placed,
                "total_duration_frames": result.total_duration_frames,
                "total_duration_timecode": result.total_duration_timecode,
                "timeline_positions": timeline_positions,
                "success": True
            }
        else:
            # Return error from cutter
            error = result.error or {}
            return _error_response(
                error.get("code", ERROR_CODES["CUTTING_FAILED"]),
                error.get("category", "internal"),
                error.get("message", "Segment cutting failed"),
                error.get("suggestion", "Check Resolve is running and retry"),
                error.get("recoverable", True)
            )
            
    except Exception as e:
        logger.exception(f"Error cutting footage to segments: {e}")
        return _error_response(
            ERROR_CODES["INTERNAL_ERROR"],
            "internal",
            f"Unexpected error during cutting: {str(e)}",
            "Check application logs and retry the operation",
            recoverable=True
        )


def place_music_on_timeline(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Place AI-suggested music clips on the timeline.
    
    This handler is called from the Lua GUI after footage cutting to place
    music clips on the timeline's dedicated music track(s).
    
    Args:
        params: Request parameters containing:
            - timeline_id: Target timeline ID (required)
            - music_segments: List of music segment dictionaries (required)
            
    Returns:
        Dictionary with music placement result or error
    """
    if params is None:
        params = {}
    
    # Validate required parameters
    timeline_id = params.get("timeline_id")
    if not timeline_id:
        logger.error("Missing timeline_id parameter")
        return _error_response(
            ERROR_CODES["TIMELINE_NOT_FOUND"],
            "validation",
            "Timeline ID is required",
            "Ensure timeline was created successfully before placing music",
            recoverable=True
        )
    
    music_segments = params.get("music_segments")
    if music_segments is None:
        logger.error("Missing music_segments parameter")
        return _error_response(
            ERROR_CODES["MISSING_MUSIC_SEGMENTS"],
            "validation",
            "No music_segments parameter provided",
            "Generate a rough cut with AI music suggestions first",
            recoverable=True
        )
    
    if not isinstance(music_segments, list):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "music_segments must be a list",
            "Provide a list of music segment dictionaries with file paths and timing",
            recoverable=True
        )
    
    if len(music_segments) == 0:
        logger.info("Empty music_segments list - nothing to place")
        return {
            "clips_placed": 0,
            "tracks_used": [],
            "total_duration_frames": 0,
            "total_duration_timecode": "0:00:00",
            "timeline_positions": [],
            "success": True,
            "warning": "No music segments to place"
        }
    
    logger.info(f"Placing {len(music_segments)} music clips on timeline {timeline_id}")
    
    try:
        # Create placer and perform placement
        placer = MusicPlacer()
        
        # Progress callback that emits JSON-RPC progress messages
        def progress_callback(current: int, total: int, message: str):
            logger.info(f"Progress: {message} ({current}/{total})")
        
        result = placer.place_music_clips(
            timeline_id=timeline_id,
            music_segments=music_segments,
            progress_callback=progress_callback
        )
        
        if result.success:
            # Convert placements to serializable format
            timeline_positions = []
            for placement in result.timeline_positions:
                timeline_positions.append({
                    "segment_index": placement.segment_index,
                    "track_number": placement.track_number,
                    "timeline_start_frame": placement.timeline_start_frame,
                    "timeline_end_frame": placement.timeline_end_frame,
                    "music_file_path": placement.music_file_path,
                    "clip_id": placement.clip_id,
                    "fade_in_frames": placement.fade_in_frames,
                    "fade_out_frames": placement.fade_out_frames,
                    "section_type": placement.section_type
                })
            
            logger.info(
                f"Music placement complete: {result.clips_placed} clips, "
                f"tracks used: {result.tracks_used}, "
                f"duration: {result.total_duration_timecode}"
            )
            
            return {
                "clips_placed": result.clips_placed,
                "tracks_used": result.tracks_used,
                "total_duration_frames": result.total_duration_frames,
                "total_duration_timecode": result.total_duration_timecode,
                "timeline_positions": timeline_positions,
                "success": True
            }
        else:
            # Return error from placer
            error = result.error or {}
            return _error_response(
                error.get("code", ERROR_CODES["MUSIC_PLACEMENT_FAILED"]),
                error.get("category", "internal"),
                error.get("message", "Music placement failed"),
                error.get("suggestion", "Check Resolve is running and music files are accessible"),
                error.get("recoverable", True)
            )
            
    except Exception as e:
        logger.exception(f"Error placing music on timeline: {e}")
        return _error_response(
            ERROR_CODES["INTERNAL_ERROR"],
            "internal",
            f"Unexpected error during music placement: {str(e)}",
            "Check application logs and retry the operation",
            recoverable=True
        )


def place_sfx_on_timeline(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Place AI-suggested SFX clips on the timeline.
    
    This handler is called from the Lua GUI after music placement to place
    SFX clips on the timeline's dedicated SFX tracks (Tracks 3-10).
    
    Args:
        params: Request parameters containing:
            - timeline_id: Target timeline ID (required)
            - sfx_segments: List of SFX segment dictionaries (required)
            
    Returns:
        Dictionary with SFX placement result or error
    """
    if params is None:
        params = {}
    
    # Validate required parameters
    timeline_id = params.get("timeline_id")
    if not timeline_id:
        logger.error("Missing timeline_id parameter")
        return _error_response(
            ERROR_CODES["TIMELINE_NOT_FOUND"],
            "validation",
            "Timeline ID is required",
            "Ensure timeline was created successfully before placing SFX",
            recoverable=True
        )
    
    sfx_segments = params.get("sfx_segments")
    if sfx_segments is None:
        logger.error("Missing sfx_segments parameter")
        return _error_response(
            ERROR_CODES["MISSING_SFX_SEGMENTS"],
            "validation",
            "No sfx_segments parameter provided",
            "Generate a rough cut with AI SFX suggestions first",
            recoverable=True
        )
    
    if not isinstance(sfx_segments, list):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "sfx_segments must be a list",
            "Provide a list of SFX segment dictionaries with file paths and timing",
            recoverable=True
        )
    
    if len(sfx_segments) == 0:
        logger.info("Empty sfx_segments list - nothing to place")
        return {
            "clips_placed": 0,
            "tracks_used": [],
            "total_duration_frames": 0,
            "total_duration_timecode": "0:00:00",
            "timeline_positions": [],
            "success": True,
            "warning": "No SFX segments to place"
        }
    
    logger.info(f"Placing {len(sfx_segments)} SFX clips on timeline {timeline_id}")
    
    try:
        # Create placer and perform placement
        placer = SfxPlacer()
        
        # Progress callback that emits JSON-RPC progress messages
        def progress_callback(current: int, total: int, message: str):
            logger.info(f"Progress: {message} ({current}/{total})")
        
        result = placer.place_sfx_clips(
            timeline_id=timeline_id,
            sfx_segments=sfx_segments,
            progress_callback=progress_callback
        )
        
        if result.success:
            # Convert placements to serializable format
            timeline_positions = []
            for placement in result.timeline_positions:
                timeline_positions.append({
                    "segment_index": placement.segment_index,
                    "track_number": placement.track_number,
                    "timeline_start_frame": placement.timeline_start_frame,
                    "timeline_end_frame": placement.timeline_end_frame,
                    "sfx_file_path": placement.sfx_file_path,
                    "clip_id": placement.clip_id,
                    "fade_in_frames": placement.fade_in_frames,
                    "fade_out_frames": placement.fade_out_frames,
                    "volume_db": placement.volume_db,
                    "moment_type": placement.moment_type,
                    "handle_frames": placement.handle_frames
                })
            
            logger.info(
                f"SFX placement complete: {result.clips_placed} clips, "
                f"tracks used: {result.tracks_used}, "
                f"duration: {result.total_duration_timecode}"
            )
            
            return {
                "clips_placed": result.clips_placed,
                "tracks_used": result.tracks_used,
                "total_duration_frames": result.total_duration_frames,
                "total_duration_timecode": result.total_duration_timecode,
                "timeline_positions": timeline_positions,
                "success": True
            }
        else:
            # Return error from placer
            error = result.error or {}
            return _error_response(
                error.get("code", ERROR_CODES["SFX_PLACEMENT_FAILED"]),
                error.get("category", "internal"),
                error.get("message", "SFX placement failed"),
                error.get("suggestion", "Check Resolve is running and SFX files are accessible"),
                error.get("recoverable", True)
            )
            
    except TrackAllocationError as e:
        logger.error(f"Track allocation failed: {e}")
        return _error_response(
            ERROR_CODES["TRACK_ALLOCATION_FAILED"],
            "resolve_api",
            str(e),
            "All SFX tracks (3-10) are occupied. Consider removing some SFX or staggering placement times.",
            recoverable=True
        )
            
    except Exception as e:
        logger.exception(f"Error placing SFX on timeline: {e}")
        return _error_response(
            ERROR_CODES["INTERNAL_ERROR"],
            "internal",
            f"Unexpected error during SFX placement: {str(e)}",
            "Check application logs and retry the operation",
            recoverable=True
        )


def place_vfx_on_timeline(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Place AI-suggested VFX templates on the timeline.
    
    This handler is called from the Lua GUI after SFX placement to place
    VFX templates on the timeline's dedicated VFX tracks (Tracks 11-14).
    
    Args:
        params: Request parameters containing:
            - timeline_id: Target timeline ID (required)
            - vfx_segments: List of VFX segment dictionaries (required)
            
    Returns:
        Dictionary with VFX placement result or error
    """
    if params is None:
        params = {}
    
    # Validate required parameters
    timeline_id = params.get("timeline_id")
    if not timeline_id:
        logger.error("Missing timeline_id parameter")
        return _error_response(
            ERROR_CODES["TIMELINE_NOT_FOUND"],
            "validation",
            "Timeline ID is required",
            "Ensure timeline was created successfully before placing VFX",
            recoverable=True
        )
    
    vfx_segments = params.get("vfx_segments")
    if vfx_segments is None:
        logger.error("Missing vfx_segments parameter")
        return _error_response(
            ERROR_CODES["MISSING_VFX_SEGMENTS"],
            "validation",
            "No vfx_segments parameter provided",
            "Generate a rough cut with AI VFX suggestions first",
            recoverable=True
        )
    
    if not isinstance(vfx_segments, list):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "vfx_segments must be a list",
            "Provide a list of VFX segment dictionaries with file paths and timing",
            recoverable=True
        )
    
    if len(vfx_segments) == 0:
        logger.info("Empty vfx_segments list - nothing to place")
        return {
            "clips_placed": 0,
            "tracks_used": [],
            "total_duration_frames": 0,
            "total_duration_timecode": "0:00:00",
            "timeline_positions": [],
            "success": True,
            "warning": "No VFX segments to place"
        }
    
    logger.info(f"Placing {len(vfx_segments)} VFX templates on timeline {timeline_id}")
    
    try:
        # Create placer and perform placement
        placer = VfxPlacer()
        
        # Progress callback that emits JSON-RPC progress messages
        def progress_callback(current: int, total: int, message: str):
            logger.info(f"Progress: {message} ({current}/{total})")
        
        result = placer.place_vfx_templates(
            timeline_id=timeline_id,
            vfx_segments=vfx_segments,
            progress_callback=progress_callback
        )
        
        if result.success:
            # Convert placements to serializable format
            timeline_positions = []
            for placement in result.timeline_positions:
                timeline_positions.append({
                    "segment_index": placement.segment_index,
                    "track_number": placement.track_number,
                    "timeline_start_frame": placement.timeline_start_frame,
                    "timeline_end_frame": placement.timeline_end_frame,
                    "vfx_file_path": placement.vfx_file_path,
                    "clip_id": placement.clip_id,
                    "fade_in_frames": placement.fade_in_frames,
                    "fade_out_frames": placement.fade_out_frames,
                    "template_type": placement.template_type,
                    "template_params_applied": placement.template_params,
                    "vfx_type": placement.vfx_type
                })
            
            logger.info(
                f"VFX placement complete: {result.clips_placed} clips, "
                f"tracks used: {result.tracks_used}, "
                f"duration: {result.total_duration_timecode}"
            )
            
            return {
                "clips_placed": result.clips_placed,
                "tracks_used": result.tracks_used,
                "total_duration_frames": result.total_duration_frames,
                "total_duration_timecode": result.total_duration_timecode,
                "timeline_positions": timeline_positions,
                "success": True
            }
        else:
            # Return error from placer
            error = result.error or {}
            return _error_response(
                error.get("code", ERROR_CODES["VFX_PLACEMENT_FAILED"]),
                error.get("category", "internal"),
                error.get("message", "VFX placement failed"),
                error.get("suggestion", "Check Resolve is running and VFX files are accessible"),
                error.get("recoverable", True)
            )
            
    except TrackAllocationError as e:
        logger.error(f"Track allocation failed: {e}")
        return _error_response(
            ERROR_CODES["TRACK_ALLOCATION_FAILED"],
            "resolve_api",
            str(e),
            "All VFX tracks (11-14) are occupied. Consider removing some VFX or staggering placement times.",
            recoverable=True
        )
            
    except Exception as e:
        logger.exception(f"Error placing VFX on timeline: {e}")
        return _error_response(
            ERROR_CODES["INTERNAL_ERROR"],
            "internal",
            f"Unexpected error during VFX placement: {str(e)}",
            "Check application logs and retry the operation",
            recoverable=True
        )


# Handler registry for the dispatcher
TIMELINE_HANDLERS: Dict[str, Callable] = {
    "create_timeline_from_document": create_timeline_from_document,
    "create_timeline": create_timeline,
    "import_suggested_media": import_suggested_media,
    "cut_footage_to_segments": cut_footage_to_segments,
    "place_music_on_timeline": place_music_on_timeline,
    "place_sfx_on_timeline": place_sfx_on_timeline,
    "place_vfx_on_timeline": place_vfx_on_timeline
}
