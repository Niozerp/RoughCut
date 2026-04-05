"""Protocol handlers for timeline operations."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from roughcut.backend.timeline.importer import MediaImporter, ImportResult
from roughcut.backend.timeline.resolve_api import ResolveApi

logger = logging.getLogger(__name__)

# Error codes for structured error responses
ERROR_CODES = {
    "INVALID_PARAMS": "INVALID_PARAMS",
    "RESOLVE_NOT_AVAILABLE": "RESOLVE_NOT_AVAILABLE",
    "IMPORT_FAILED": "IMPORT_FAILED",
    "FILE_NOT_FOUND": "FILE_NOT_FOUND",
    "FILE_ACCESS_DENIED": "FILE_ACCESS_DENIED",
    "UNSUPPORTED_FORMAT": "UNSUPPORTED_FORMAT",
    "INTERNAL_ERROR": "INTERNAL_ERROR",
}

# Maximum batch size to prevent DoS
MAX_BATCH_SIZE = 10000

# Chunk size for GUI responsiveness (D1 fix)
# Process imports in chunks to keep UI responsive
CHUNK_SIZE = 50

# Supported file extensions by DaVinci Resolve (D3 fix)
# Based on Resolve's documented supported formats
RESOLVE_SUPPORTED_FORMATS = {
    # Video
    ".mov", ".mp4", ".m4v", ".mkv", ".avi", ".wmv", ".flv", ".webm",
    ".mxf", ".mts", ".m2ts", ".ts", ".vob", ".mpg", ".mpeg", ".m2v",
    ".dv", ".qt", ".ogv", ".3gp", ".3g2", ".asf", ".f4v", ".swf",
    ".y4m", ".ivf", ".nut", ".roq", ".rm", ".rmvb", ".viv", ".vp8", ".vp9",
    ".av1", ".hevc", ".h265", ".h264", ".avc", ".prores", ".dnxhd", ".cineform",
    # Audio
    ".mp3", ".wav", ".aiff", ".aif", ".m4a", ".aac", ".flac", ".ogg",
    ".wma", ".ac3", ".eac3", ".dts", ".dtshd", ".truehd", ".opus",
    ".w64", ".rf64", ".au", ".snd", ".pcm", ".raw", ".gsm", ".ircam",
    # Image
    ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".tga", ".bmp", ".gif",
    ".exr", ".dpx", ".cin", ".sgi", ".rgb", ".rgba", ".pict", ".pct",
    ".icns", ".ico", ".cur", ".xbm", ".xpm", ".ppm", ".pgm", ".pbm",
    ".pnm", ".pam", ".iff", ".lbm", ".ilbm", ".eps", ".ps", ".pdf",
    ".svg", ".webp", ".j2k", ".jp2", ".jpf", ".jpx", ".jpm", ".mj2",
    # Fusion/VFX
    ".comp", ".settings", ".drfx", ".fbx", ".obj", ".3ds", ".dae", ".abc",
    ".usd", ".usda", ".usdc", ".vdb", ".fur", ".bgeo", ".geo", ".hclassic",
    ".json", ".rawmesh", ".pts", ".csv", ".xml", ".ply", ".stl", ".wrl",
    ".vrml", ".x3d", ".x3dv", ".x3db", ".cob", ".scn", ".lwo", ".lws",
    ".lwob", ".ms3d", ".mdl", ".iqm", ".smd", ".vta", ".vvd", ".phy",
    ".ani", ".psk", ".pskx", ".psa", ".gltf", ".glb",
}


def error_response(
    code: str, message: str, category: str = "general", recoverable: bool = True, suggestion: str = "", request_id: str = ""
) -> Dict[str, Any]:
    """Create a standardized error response."""
    response = {
        "error": {
            "code": code,
            "category": category,
            "message": message,
            "recoverable": recoverable,
            "suggestion": suggestion,
        },
        "result": None,
    }
    if request_id:
        response["id"] = request_id
    return response


def success_response(result: Any, request_id: str = "") -> Dict[str, Any]:
    """Create a standardized success response."""
    response = {"error": None, "result": result}
    if request_id:
        response["id"] = request_id
    return response


def progress_message(operation: str, current: int, total: int, message: str) -> Dict[str, Any]:
    """Create a progress message for streaming to Lua."""
    return {
        "type": "progress",
        "operation": operation,
        "current": current,
        "total": total,
        "message": message,
    }


def handle_import_suggested_media(params: Dict[str, Any], request_id: str = "") -> Dict[str, Any]:
    """Handle import_suggested_media JSON-RPC request.
    
    Request format:
    {
        "method": "import_suggested_media",
        "params": {
            "timeline_id": "timeline_12345",
            "suggested_media": [
                {
                    "file_path": "/absolute/path/to/media.mp3",
                    "media_type": "music",
                    "usage": "intro_bed"
                }
            ]
        },
        "id": "req_001"
    }
    
    Response format:
    {
        "result": {
            "imported_count": 2,
            "skipped_count": 1,
            "media_pool_refs": [...],
            "skipped_files": [...]
        },
        "error": null,
        "id": "req_001"
    }
    
    Args:
        params: Request parameters containing timeline_id and suggested_media list.
        request_id: Optional request ID to include in response.
        
    Returns:
        JSON-RPC response with import results or error.
    """
    try:
        # Validate required parameters
        timeline_id = params.get("timeline_id")
        suggested_media = params.get("suggested_media", [])
        
        if not timeline_id:
            return error_response(
                code=ERROR_CODES["INVALID_PARAMS"],
                message="timeline_id is required",
                category="validation",
                recoverable=True,
                suggestion="Provide a valid timeline_id from the create_timeline response",
                request_id=request_id,
            )
        
        if not isinstance(suggested_media, list):
            return error_response(
                code=ERROR_CODES["INVALID_PARAMS"],
                message="suggested_media must be a list",
                category="validation",
                recoverable=True,
                suggestion="Provide a list of media items with file_path and media_type",
                request_id=request_id,
            )
        
        # Check batch size limit (P8 fix)
        if len(suggested_media) > MAX_BATCH_SIZE:
            return error_response(
                code=ERROR_CODES["INVALID_PARAMS"],
                message=f"Batch too large: {len(suggested_media)} items (max: {MAX_BATCH_SIZE})",
                category="validation",
                recoverable=True,
                suggestion=f"Split into batches of {MAX_BATCH_SIZE} or fewer items",
                request_id=request_id,
            )
        
        if not suggested_media:
            # Empty list is valid but warn
            logger.warning("Empty suggested_media list provided")
            return success_response({
                "imported_count": 0,
                "skipped_count": 0,
                "media_pool_refs": [],
                "skipped_files": [],
            }, request_id=request_id)
        
        # Validate each media item
        for i, media in enumerate(suggested_media):
            if not isinstance(media, dict):
                return error_response(
                    code=ERROR_CODES["INVALID_PARAMS"],
                    message=f"suggested_media[{i}] must be an object",
                    category="validation",
                    recoverable=True,
                    suggestion="Each media item must be an object with file_path and media_type",
                )
            
            if not media.get("file_path"):
                return error_response(
                    code=ERROR_CODES["INVALID_PARAMS"],
                    message=f"suggested_media[{i}] missing file_path",
                    category="validation",
                    recoverable=True,
                    suggestion="Each media item must have a valid file_path",
                )
            
            if not media.get("media_type"):
                return error_response(
                    code=ERROR_CODES["INVALID_PARAMS"],
                    message=f"suggested_media[{i}] missing media_type",
                    category="validation",
                    recoverable=True,
                    suggestion="Each media item must have a media_type (music, sfx, or vfx)",
                    request_id=request_id,
                )
            
            # D3 FIX: Validate file extension against Resolve-supported formats
            file_path = media.get("file_path", "")
            ext = Path(file_path).suffix.lower()
            if ext not in RESOLVE_SUPPORTED_FORMATS:
                return error_response(
                    code=ERROR_CODES["UNSUPPORTED_FORMAT"],
                    message=f"File format {ext} not supported by DaVinci Resolve: {file_path}",
                    category="validation",
                    recoverable=True,
                    suggestion=f"Supported formats include: .mov, .mp4, .mp3, .wav, etc. See documentation for full list.",
                    request_id=request_id,
                )
        
        # Check Resolve availability
        resolve_api = ResolveApi()
        if not resolve_api.is_available():
            return error_response(
                code=ERROR_CODES["RESOLVE_NOT_AVAILABLE"],
                message="DaVinci Resolve is not available",
                category="external_dependency",
                recoverable=True,
                suggestion="Ensure DaVinci Resolve is running and the script has access to its API",
                request_id=request_id,
            )
        
        # Create importer with progress callback that streams to stdout (P2 fix)
        importer = MediaImporter()
        
        def emit_progress(message: str, current: int, total: int) -> None:
            """Emit progress message to stdout for Lua to receive."""
            progress_msg = progress_message("import_media", current, total, message)
            sys.stdout.write(json.dumps(progress_msg) + "\n")
            sys.stdout.flush()
        
        # D1 FIX: Chunked processing for GUI responsiveness
        # Process imports in chunks to prevent UI freezing on large batches
        total_items = len(suggested_media)
        final_result = ImportResult()
        
        if total_items <= CHUNK_SIZE:
            # Small batch - process normally with per-file progress
            def progress_callback(message: str, current: int, total: int) -> None:
                emit_progress(message, current, total_items)
            
            importer.set_progress_callback(progress_callback)
            final_result = importer.import_suggested_media(suggested_media)
        else:
            # Large batch - process in chunks with chunk-level progress
            logger.info(f"Processing {total_items} items in chunks of {CHUNK_SIZE}")
            
            for chunk_start in range(0, total_items, CHUNK_SIZE):
                chunk_end = min(chunk_start + CHUNK_SIZE, total_items)
                chunk = suggested_media[chunk_start:chunk_end]
                
                # Emit chunk progress
                emit_progress(
                    f"Processing batch {chunk_start//CHUNK_SIZE + 1} of {(total_items + CHUNK_SIZE - 1)//CHUNK_SIZE}",
                    chunk_end,
                    total_items
                )
                
                # Process chunk without per-file callbacks (to reduce overhead)
                importer.set_progress_callback(None)
                chunk_result = importer.import_suggested_media(chunk)
                
                # Merge results
                final_result.imported_count += chunk_result.imported_count
                final_result.skipped_count += chunk_result.skipped_count
                final_result.media_pool_refs.extend(chunk_result.media_pool_refs)
                final_result.skipped_files.extend(chunk_result.skipped_files)
            
            # Emit final progress
            emit_progress("Import complete", total_items, total_items)
        
        # Convert result to response
        return success_response(final_result.to_dict(), request_id=request_id)
        
    except Exception as e:
        logger.exception("Error importing suggested media")
        return error_response(
            code=ERROR_CODES["INTERNAL_ERROR"],
            message=f"Internal error during import: {str(e)}",
            category="internal",
            recoverable=True,
            suggestion="Try again or contact support if the error persists",
            request_id=request_id,
        )


def handle_check_resolve_availability(params: Dict[str, Any], request_id: str = "") -> Dict[str, Any]:
    """Check if DaVinci Resolve API is available.
    
    Request format:
    {
        "method": "check_resolve_availability",
        "params": {},
        "id": "req_001"
    }
    """
    try:
        resolve_api = ResolveApi()
        available = resolve_api.is_available()
        
        return success_response({
            "available": available,
            "message": "DaVinci Resolve API is available" if available else "DaVinci Resolve API is not available",
        }, request_id=request_id)
        
    except Exception as e:
        logger.exception("Error checking Resolve availability")
        return error_response(
            code=ERROR_CODES["INTERNAL_ERROR"],
            message=f"Error checking availability: {str(e)}",
            category="internal",
            recoverable=True,
            suggestion="Try again",
            request_id=request_id,
        )
