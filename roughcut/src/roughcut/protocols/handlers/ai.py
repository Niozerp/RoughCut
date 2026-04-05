"""Protocol handlers for AI-powered rough cut generation.

Handles JSON-RPC requests for initiating and managing rough cut
AI processing, including progress reporting and error handling.
"""

import asyncio
import logging
import uuid
from typing import Any, Callable, Dict, Generator, Optional

from ...backend.ai.data_bundle import DataBundleBuilder
from ...backend.ai.music_matcher import MusicMatcher
from ...backend.ai.music_match import MusicMatch, MusicMatchingResult, SegmentMusicMatches
from ...backend.ai.sfx_matcher import SFXMatcher
from ...backend.ai.sfx_match import SFXMatch, SFXMatchingResult, MomentSFXMatches
from ...backend.ai.vfx_matcher import VFXMatcher
from ...backend.ai.vfx_match import VFXMatch, VFXMatchingResult, RequirementVFXMatches
from ...backend.ai.openai_client import OpenAIClient
from ...backend.ai.prompt_engine import PromptBuilder
from ...backend.ai.rough_cut_orchestrator import RoughCutOrchestrator
from ...backend.ai.segment_tone import SegmentTone
from ...backend.ai.transcript_cutter import TranscriptCutter
from ...backend.ai.transcript_segment import TranscriptSegment
from ...backend.workflows.session import get_session_manager
from ...config.settings import get_settings

logger = logging.getLogger(__name__)

# Error codes for consistent error handling
ERROR_CODES = {
    "INVALID_PARAMS": "INVALID_PARAMS",
    "SESSION_NOT_FOUND": "SESSION_NOT_FOUND",
    "INVALID_STATE": "INVALID_STATE",
    "AI_INITIATE_ERROR": "AI_INITIATE_ERROR",
    "AI_CONFIG_ERROR": "AI_CONFIG_ERROR",
    "AI_TIMEOUT": "AI_TIMEOUT",
    "EMPTY_TRANSCRIPT": "EMPTY_TRANSCRIPT",
    "FORMAT_SECTION_MISMATCH": "FORMAT_SECTION_MISMATCH",
    "WORD_MODIFICATION_DETECTED": "WORD_MODIFICATION_DETECTED",
    "INVALID_SEGMENT_BOUNDARIES": "INVALID_SEGMENT_BOUNDARIES",
    "NARRATIVE_BEAT_MISMATCH": "NARRATIVE_BEAT_MISMATCH",
    "OVERLAPPING_SEGMENTS": "OVERLAPPING_SEGMENTS",
    "EMPTY_MUSIC_LIBRARY": "EMPTY_MUSIC_LIBRARY",
    "NO_MUSIC_MATCHES": "NO_MUSIC_MATCHES",
    "LOW_CONFIDENCE_MATCHES": "LOW_CONFIDENCE_MATCHES",
    "INVALID_SEGMENT_DATA": "INVALID_SEGMENT_DATA",
    "EMPTY_SFX_LIBRARY": "EMPTY_SFX_LIBRARY",
    "NO_SFX_MATCHES": "NO_SFX_MATCHES",
    "NO_MOMENTS_IDENTIFIED": "NO_MOMENTS_IDENTIFIED",
    "EMPTY_VFX_LIBRARY": "EMPTY_VFX_LIBRARY",
    "NO_VFX_MATCHES": "NO_VFX_MATCHES",
    "NO_REQUIREMENTS_IDENTIFIED": "NO_REQUIREMENTS_IDENTIFIED",
    "PLACEMENT_CONFLICTS": "PLACEMENT_CONFLICTS",
}

# Type alias for progress callback
ProgressCallback = Callable[[str, int, int], None]


def initiate_rough_cut(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Handler for initiate_rough_cut method.
    
    Initiates AI-powered rough cut generation with the prepared data.
    This is the entry point for Story 5.1 - Initiate Rough Cut Generation.
    
    Args:
        params: Request parameters containing:
            - session_id: Session UUID (required)
            - rough_cut_data: Prepared data bundle from prepare_rough_cut_for_generation (required)
    
    Returns:
        Dictionary with rough_cut_id and initial status
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Invalid parameters: expected object",
            "Check request format"
        )
    
    session_id = params.get("session_id")
    rough_cut_data = params.get("rough_cut_data")
    
    if not session_id or not isinstance(session_id, str):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: session_id",
            "Provide a session_id string"
        )
    
    if not rough_cut_data or not isinstance(rough_cut_data, dict):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: rough_cut_data",
            "Call prepare_rough_cut_for_generation first"
        )
    
    try:
        # Get session
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if session is None:
            return _error_response(
                ERROR_CODES["SESSION_NOT_FOUND"],
                "not_found",
                f"Session '{session_id}' not found",
                "Create a new session or check the session ID"
            )
        
        # Validate session is in correct state
        if session.status != "format_selected":
            return _error_response(
                ERROR_CODES["INVALID_STATE"],
                "validation",
                f"Cannot initiate generation from status: {session.status}",
                "Complete all workflow steps: select media, review transcription, select format template"
            )
        
        # Get AI configuration
        settings = get_settings()
        api_key = settings.get("openai_api_key")
        
        if not api_key:
            return _error_response(
                ERROR_CODES["AI_CONFIG_ERROR"],
                "config",
                "OpenAI API key not configured",
                "Configure API key in settings before generating rough cuts"
            )
        
        # Initialize orchestrator
        try:
            client = OpenAIClient(api_key=api_key)
            orchestrator = RoughCutOrchestrator(client)
        except Exception as e:
            logger.exception(f"Failed to initialize AI orchestrator: {e}")
            return _error_response(
                ERROR_CODES["AI_CONFIG_ERROR"],
                "config",
                f"Failed to initialize AI client: {str(e)}",
                "Check API key configuration"
            )
        
        # Generate rough cut ID
        rough_cut_id = f"rc_{uuid.uuid4().hex[:8]}"
        
        # Update session status
        session.start_generation()
        session_manager.update_session(session)
        
        logger.info(f"Initiated rough cut generation: {rough_cut_id} for session {session_id}")
        
        # Return immediately with rough cut ID
        # Actual processing happens asynchronously via progress updates
        return {
            "result": {
                "rough_cut_id": rough_cut_id,
                "session_id": session_id,
                "status": "initiated",
                "message": "Rough cut generation initiated. Progress updates will follow."
            }
        }
        
    except Exception as e:
        logger.exception(f"Failed to initiate rough cut: {e}")
        return _error_response(
            ERROR_CODES["AI_INITIATE_ERROR"],
            "internal",
            f"Failed to initiate rough cut: {str(e)}",
            "Try again or restart the workflow"
        )


def initiate_rough_cut_with_progress(
    params: Dict[str, Any] | None,
    progress_callback: Optional[ProgressCallback] = None
) -> Generator[Dict[str, Any], None, None]:
    """Generator-based handler for initiate_rough_cut with progress updates.
    
    Yields progress updates and final result for streaming protocols.
    
    Args:
        params: Request parameters (same as initiate_rough_cut)
        progress_callback: Optional callback for progress updates
    
    Yields:
        Progress update dictionaries or final result
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Invalid parameters: expected object",
            "Check request format"
        )
        return
    
    session_id = params.get("session_id")
    rough_cut_data = params.get("rough_cut_data")
    
    if not session_id or not isinstance(session_id, str):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: session_id",
            "Provide a session_id string"
        )
        return
    
    if not rough_cut_data or not isinstance(rough_cut_data, dict):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: rough_cut_data",
            "Call prepare_rough_cut_for_generation first"
        )
        return
    
    try:
        # Get session
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if session is None:
            yield _error_response(
                ERROR_CODES["SESSION_NOT_FOUND"],
                "not_found",
                f"Session '{session_id}' not found",
                "Create a new session or check the session ID"
            )
            return
        
        # Validate session is in correct state
        if session.status != "format_selected":
            yield _error_response(
                ERROR_CODES["INVALID_STATE"],
                "validation",
                f"Cannot initiate generation from status: {session.status}",
                "Complete all workflow steps: select media, review transcription, select format template"
            )
            return
        
        # Yield initial progress
        yield _progress_response("initiate_rough_cut", 1, 5, "Initializing AI processing...")
        
        # Get AI configuration
        settings = get_settings()
        api_key = settings.get("openai_api_key")
        
        if not api_key:
            yield _error_response(
                ERROR_CODES["AI_CONFIG_ERROR"],
                "config",
                "OpenAI API key not configured",
                "Configure API key in settings before generating rough cuts"
            )
            return
        
        # Initialize orchestrator
        try:
            client = OpenAIClient(api_key=api_key)
            orchestrator = RoughCutOrchestrator(client)
        except Exception as e:
            logger.exception(f"Failed to initialize AI orchestrator: {e}")
            yield _error_response(
                ERROR_CODES["AI_CONFIG_ERROR"],
                "config",
                f"Failed to initialize AI client: {str(e)}",
                "Check API key configuration"
            )
            return
        
        yield _progress_response("initiate_rough_cut", 2, 5, "Preparing data for AI...")
        
        # Generate rough cut ID
        rough_cut_id = f"rc_{uuid.uuid4().hex[:8]}"
        
        # Update session status
        session.start_generation()
        session_manager.update_session(session)
        
        yield _progress_response("initiate_rough_cut", 3, 5, "Analyzing transcript and matching assets...")
        
        # TODO: Implement actual AI processing in Story 5.2+
        # For now, this initiates the workflow and returns a placeholder
        
        yield _progress_response("initiate_rough_cut", 4, 5, "Processing format rules...")
        
        # Final progress
        yield _progress_response("initiate_rough_cut", 5, 5, "Generation initiated successfully")
        
        # Return final result
        yield {
            "result": {
                "rough_cut_id": rough_cut_id,
                "session_id": session_id,
                "status": "initiated",
                "message": "Rough cut generation initiated. Progress updates will follow via stream."
            }
        }
        
    except Exception as e:
        logger.exception(f"Failed to initiate rough cut: {e}")
        yield _error_response(
            ERROR_CODES["AI_INITIATE_ERROR"],
            "internal",
            f"Failed to initiate rough cut: {str(e)}",
            "Try again or restart the workflow"
        )


def _error_response(code: str, category: str, message: str, suggestion: str) -> Dict[str, Any]:
    """Create a standardized error response.
    
    Args:
        code: Error code
        category: Error category
        message: Error message
        suggestion: Actionable suggestion
        
    Returns:
        Error response dictionary
    """
    return {
        "error": {
            "code": code,
            "category": category,
            "message": message,
            "suggestion": suggestion
        }
    }


def _progress_response(operation: str, current: int, total: int, message: str) -> Dict[str, Any]:
    """Create a progress update response.
    
    Args:
        operation: Operation name
        current: Current step number
        total: Total steps
        message: Progress message
        
    Returns:
        Progress response dictionary
    """
    return {
        "type": "progress",
        "operation": operation,
        "current": current,
        "total": total,
        "message": message
    }


def send_data_to_ai(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Handler for send_data_to_ai method.
    
    Sends transcript, format rules, and media index to AI service.
    This implements Story 5.2 - Send Data to AI Service.
    
    Args:
        params: Request parameters containing:
            - session_id: Session UUID (required)
            - transcript: Transcription data with text and segments (required)
            - format_template: Format template with rules and asset groups (required)
            - media_index: Indexed media metadata (required)
    
    Returns:
        Dictionary with AI request ID and status
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Invalid parameters: expected object",
            "Check request format"
        )
    
    session_id = params.get("session_id")
    transcript = params.get("transcript")
    format_template = params.get("format_template")
    media_index = params.get("media_index")
    
    if not session_id or not isinstance(session_id, str):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: session_id",
            "Provide a session_id string"
        )
    
    if not transcript or not isinstance(transcript, dict):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: transcript",
            "Provide transcript data with text and segments"
        )
    
    if not format_template or not isinstance(format_template, dict):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: format_template",
            "Provide format template with rules and asset groups"
        )
    
    if not media_index or not isinstance(media_index, list):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: media_index",
            "Provide indexed media metadata list"
        )
    
    # Validate media_index is not empty
    if len(media_index) == 0:
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "media_index cannot be empty",
            "Add media assets before sending to AI"
        )
    
    try:
        # Get session
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if session is None:
            return _error_response(
                ERROR_CODES["SESSION_NOT_FOUND"],
                "not_found",
                f"Session '{session_id}' not found",
                "Create a new session or check the session ID"
            )
        
        # Get AI configuration
        settings = get_settings()
        api_key = settings.get("openai_api_key")
        
        if not api_key:
            return _error_response(
                ERROR_CODES["AI_CONFIG_ERROR"],
                "config",
                "OpenAI API key not configured",
                "Configure API key in settings before sending data to AI"
            )
        
        # Initialize builder and build data bundle
        bundle_builder = DataBundleBuilder()
        
        # Guard against None in asset_groups
        format_asset_groups = format_template.get("asset_groups") or []
        
        data_bundle = bundle_builder.build(
            session_id=session_id,
            transcript_data=transcript,
            format_template=format_template,
            media_index=media_index,
            format_asset_groups=format_asset_groups
        )
        
        # Validate bundle was created successfully
        if data_bundle is None:
            return _error_response(
                ERROR_CODES["AI_INITIATE_ERROR"],
                "internal",
                "Failed to build data bundle",
                "Check input data format"
            )
        
        # Validate media_index exists
        if data_bundle.media_index is None:
            return _error_response(
                ERROR_CODES["AI_INITIATE_ERROR"],
                "internal",
                "Data bundle media_index is None",
                "Check media index data"
            )
        
        logger.info(f"Data bundle built for session {session_id}: "
                   f"{len(data_bundle.media_index.get_all_assets())} assets")
        
        # Build AI prompt
        prompt_builder = PromptBuilder()
        ai_prompt = prompt_builder.build(data_bundle)
        
        logger.info(f"AI prompt built for session {session_id}")
        
        # Generate AI request ID
        ai_request_id = f"ai_req_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Data ready for AI service: {ai_request_id}")
        
        return {
            "result": {
                "ai_request_id": ai_request_id,
                "session_id": session_id,
                "status": "data_prepared",
                "message": "Data bundle prepared and ready for AI service",
                "estimated_tokens": data_bundle.estimate_total_tokens(),
                "asset_count": len(data_bundle.media_index.get_all_assets())
            }
        }
        
    except Exception as e:
        logger.exception(f"Failed to prepare data for AI: {e}")
        return _error_response(
            ERROR_CODES["AI_INITIATE_ERROR"],
            "internal",
            f"Failed to prepare data for AI: {str(e)}",
            "Check transcript, format template, and media index data"
        )


def send_data_to_ai_with_progress(
    params: Dict[str, Any] | None,
    progress_callback: Optional[ProgressCallback] = None
) -> Generator[Dict[str, Any], None, None]:
    """Generator-based handler for send_data_to_ai with progress updates.
    
    Yields progress updates during data preparation and bundling.
    
    Args:
        params: Request parameters (same as send_data_to_ai)
        progress_callback: Optional callback for progress updates
    
    Yields:
        Progress update dictionaries or final result
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Invalid parameters: expected object",
            "Check request format"
        )
        return
    
    session_id = params.get("session_id")
    transcript = params.get("transcript")
    format_template = params.get("format_template")
    media_index = params.get("media_index")
    
    if not session_id or not isinstance(session_id, str):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: session_id",
            "Provide a session_id string"
        )
        return
    
    if not transcript or not isinstance(transcript, dict):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: transcript",
            "Provide transcript data with text and segments"
        )
        return
    
    if not format_template or not isinstance(format_template, dict):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: format_template",
            "Provide format template with rules and asset groups"
        )
        return
    
    if not media_index or not isinstance(media_index, list):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: media_index",
            "Provide indexed media metadata list"
        )
        return
    
    # Validate media_index is not empty
    if len(media_index) == 0:
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "media_index cannot be empty",
            "Add media assets before sending to AI"
        )
        return
    
    try:
        # Get session
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if session is None:
            yield _error_response(
                ERROR_CODES["SESSION_NOT_FOUND"],
                "not_found",
                f"Session '{session_id}' not found",
                "Create a new session or check the session ID"
            )
            return
        
        yield _progress_response("send_data_to_ai", 1, 5, "Initializing data preparation...")
        
        # Get AI configuration
        settings = get_settings()
        api_key = settings.get("openai_api_key")
        
        if not api_key:
            yield _error_response(
                ERROR_CODES["AI_CONFIG_ERROR"],
                "config",
                "OpenAI API key not configured",
                "Configure API key in settings before sending data to AI"
            )
            return
        
        yield _progress_response("send_data_to_ai", 2, 5, "Building data bundle...")
        
        # Initialize builder and build data bundle
        bundle_builder = DataBundleBuilder()
        
        # Guard against None in asset_groups
        format_asset_groups = format_template.get("asset_groups") or []
        
        data_bundle = bundle_builder.build(
            session_id=session_id,
            transcript_data=transcript,
            format_template=format_template,
            media_index=media_index,
            format_asset_groups=format_asset_groups
        )
        
        yield _progress_response("send_data_to_ai", 3, 5, "Validating metadata-only compliance...")
        
        # Validate metadata-only (NFR7) with explicit error handling
        try:
            data_bundle.validate_metadata_only()
        except ValueError as e:
            yield _error_response(
                ERROR_CODES["INVALID_PARAMS"],
                "validation",
                f"Data bundle validation failed: {str(e)}",
                "Check media paths for traversal attempts or binary data"
            )
            return
        
        yield _progress_response("send_data_to_ai", 4, 5, "Building AI prompt...")
        
        # Build AI prompt
        prompt_builder = PromptBuilder()
        ai_prompt = prompt_builder.build(data_bundle)
        
        # Generate AI request ID
        ai_request_id = f"ai_req_{uuid.uuid4().hex[:8]}"
        
        yield _progress_response("send_data_to_ai", 5, 5, "Data prepared successfully")
        
        logger.info(f"Data prepared for AI: {ai_request_id} for session {session_id}")
        
        # Return final result
        yield {
            "result": {
                "ai_request_id": ai_request_id,
                "session_id": session_id,
                "status": "data_prepared",
                "message": "Data bundle prepared and ready for AI service",
                "estimated_tokens": data_bundle.estimate_total_tokens(),
                "asset_count": len(data_bundle.media_index.get_all_assets()),
                "ai_prompt": ai_prompt  # Include full prompt for debugging
            }
        }
        
    except Exception as e:
        logger.exception(f"Failed to prepare data for AI: {e}")
        yield _error_response(
            ERROR_CODES["AI_INITIATE_ERROR"],
            "internal",
            f"Failed to prepare data for AI: {str(e)}",
            "Check transcript, format template, and media index data"
        )


def cut_transcript(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Handler for cut_transcript method.
    
    Cuts transcript into segments matching format structure.
    This implements Story 5.3 - AI Transcript Cutting.
    
    Args:
        params: Request parameters containing:
            - session_id: Session UUID (required)
            - transcript: Transcription data with text and segments (required)
            - format_template: Format template with section requirements (required)
            - ai_response: AI response with segment recommendations (required)
    
    Returns:
        Dictionary with segment markers and compliance info
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Invalid parameters: expected object",
            "Check request format"
        )
    
    session_id = params.get("session_id")
    transcript = params.get("transcript")
    format_template = params.get("format_template")
    ai_response = params.get("ai_response")
    
    if not session_id or not isinstance(session_id, str):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: session_id",
            "Provide a session_id string"
        )
    
    if not transcript or not isinstance(transcript, dict):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: transcript",
            "Provide transcript data with text and segments"
        )
    
    if not format_template or not isinstance(format_template, dict):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: format_template",
            "Provide format template with section requirements"
        )
    
    # Validate transcript has text
    if not transcript.get("text") or not transcript["text"].strip():
        return _error_response(
            ERROR_CODES["EMPTY_TRANSCRIPT"],
            "validation",
            "Transcript text is empty",
            "Provide a non-empty transcript"
        )
    
    # Validate ai_response is a dict
    if not ai_response or not isinstance(ai_response, dict):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing or invalid ai_response",
            "Provide ai_response as a dictionary from AI service"
        )
    
    # Validate ai_response has segments list
    ai_segments = ai_response.get("segments")
    if ai_segments is not None and not isinstance(ai_segments, list):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            f"ai_response['segments'] must be a list, got {type(ai_segments).__name__}",
            "Ensure AI returns segments as a list"
        )
    
    try:
        # Get session
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if session is None:
            return _error_response(
                ERROR_CODES["SESSION_NOT_FOUND"],
                "not_found",
                f"Session '{session_id}' not found",
                "Create a new session or check the session ID"
            )
        
        # Initialize cutter and process
        cutter = TranscriptCutter()
        
        result = cutter.cut_transcript_to_format(
            transcript=transcript,
            format_template=format_template,
            ai_response=ai_response
        )
        
        logger.info(
            f"Transcript cutting complete: {len(result.segments)} segments, "
            f"{'compliant' if result.format_compliance.compliant else 'non-compliant'}"
        )
        
        # Check for critical errors and return error response
        critical_errors = [w for w in result.warnings if any(
            code in w for code in [
                "WORD_MODIFICATION_DETECTED", 
                "INVALID_SEGMENT_BOUNDARIES", 
                "FORMAT_SECTION_MISMATCH",
                "NARRATIVE_BEAT_MISMATCH",
                "OVERLAPPING_SEGMENTS"
            ]
        )]
        
        if critical_errors:
            # Return first critical error
            first_error = critical_errors[0]
            if "WORD_MODIFICATION_DETECTED" in first_error:
                return _error_response(
                    ERROR_CODES["WORD_MODIFICATION_DETECTED"],
                    "ai_validation",
                    first_error,
                    "Re-prompt AI with stricter word preservation instructions"
                )
            elif "INVALID_SEGMENT_BOUNDARIES" in first_error:
                return _error_response(
                    ERROR_CODES["INVALID_SEGMENT_BOUNDARIES"],
                    "validation",
                    first_error,
                    "AI returned invalid segment timestamps"
                )
            elif "FORMAT_SECTION_MISMATCH" in first_error:
                return _error_response(
                    ERROR_CODES["FORMAT_SECTION_MISMATCH"],
                    "validation",
                    first_error,
                    "AI returned wrong number of sections"
                )
            elif "NARRATIVE_BEAT_MISMATCH" in first_error:
                return _error_response(
                    ERROR_CODES["NARRATIVE_BEAT_MISMATCH"],
                    "ai_validation",
                    first_error,
                    "Re-prompt AI with correct narrative beat purposes for each section"
                )
            elif "OVERLAPPING_SEGMENTS" in first_error:
                return _error_response(
                    ERROR_CODES["OVERLAPPING_SEGMENTS"],
                    "validation",
                    first_error,
                    "Re-prompt AI to ensure non-overlapping segment timestamps"
                )
        
        # Build formatted markers
        markers = []
        for i, segment in enumerate(result.segments, 1):
            markers.append(segment.format_marker(i))
        
        return {
            "result": {
                "segments": [s.to_dict() for s in result.segments],
                "markers": markers,
                "total_duration": result.total_duration,
                "format_compliance": result.format_compliance.to_dict(),
                "warnings": result.warnings,
                "session_id": session_id
            }
        }
        
    except ValueError as e:
        logger.exception(f"Validation error cutting transcript: {e}")
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            f"Invalid data: {str(e)}",
            "Check transcript, format template, and AI response format"
        )
    except Exception as e:
        logger.exception(f"Failed to cut transcript: {e}")
        return _error_response(
            ERROR_CODES["AI_INITIATE_ERROR"],
            "internal",
            f"Failed to cut transcript: {str(e)}",
            "Check transcript, format template, and AI response data"
        )


def cut_transcript_with_progress(
    params: Dict[str, Any] | None,
    progress_callback: Optional[ProgressCallback] = None
) -> Generator[Dict[str, Any], None, None]:
    """Generator-based handler for cut_transcript with progress updates.
    
    Yields progress updates during transcript cutting and validation.
    
    Args:
        params: Request parameters (same as cut_transcript)
        progress_callback: Optional callback for progress updates
    
    Yields:
        Progress update dictionaries or final result
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Invalid parameters: expected object",
            "Check request format"
        )
        return
    
    session_id = params.get("session_id")
    transcript = params.get("transcript")
    format_template = params.get("format_template")
    ai_response = params.get("ai_response")
    
    if not session_id or not isinstance(session_id, str):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: session_id",
            "Provide a session_id string"
        )
        return
    
    if not transcript or not isinstance(transcript, dict):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: transcript",
            "Provide transcript data"
        )
        return
    
    if not format_template or not isinstance(format_template, dict):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: format_template",
            "Provide format template"
        )
        return
    
    if not transcript.get("text") or not transcript["text"].strip():
        yield _error_response(
            ERROR_CODES["EMPTY_TRANSCRIPT"],
            "validation",
            "Transcript text is empty",
            "Provide a non-empty transcript"
        )
        return
    
    # Validate ai_response is a dict
    if not ai_response or not isinstance(ai_response, dict):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing or invalid ai_response",
            "Provide ai_response as a dictionary from AI service"
        )
        return
    
    try:
        # Get session
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if session is None:
            yield _error_response(
                ERROR_CODES["SESSION_NOT_FOUND"],
                "not_found",
                f"Session '{session_id}' not found",
                "Create a new session or check the session ID"
            )
            return
        
        yield _progress_response("cut_transcript", 1, 4, "Initializing transcript cutting...")
        
        yield _progress_response("cut_transcript", 2, 4, "Processing AI segment recommendations...")
        
        # Initialize cutter and process
        cutter = TranscriptCutter()
        
        result = cutter.cut_transcript_to_format(
            transcript=transcript,
            format_template=format_template,
            ai_response=ai_response
        )
        
        yield _progress_response("cut_transcript", 3, 4, "Validating word preservation...")
        
        # Check for critical issues
        critical_issues = [s for s in result.segments if not s.source_words_preserved]
        
        if critical_issues:
            logger.warning(
                f"Word preservation issues detected in {len(critical_issues)} segments"
            )
        
        yield _progress_response("cut_transcript", 4, 4, "Transcript cutting complete")
        
        logger.info(
            f"Transcript cutting complete: {len(result.segments)} segments "
            f"for session {session_id}"
        )
        
        # Build formatted markers
        markers = []
        for i, segment in enumerate(result.segments, 1):
            markers.append(segment.format_marker(i))
        
        # Return final result
        yield {
            "result": {
                "segments": [s.to_dict() for s in result.segments],
                "markers": markers,
                "total_duration": result.total_duration,
                "format_compliance": result.format_compliance.to_dict(),
                "warnings": result.warnings,
                "session_id": session_id
            }
        }
        
    except ValueError as e:
        logger.exception(f"Validation error cutting transcript: {e}")
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            f"Invalid data: {str(e)}",
            "Check transcript, format template, and AI response format"
        )
    except Exception as e:
        logger.exception(f"Failed to cut transcript: {e}")
        yield _error_response(
            ERROR_CODES["AI_INITIATE_ERROR"],
            "internal",
            f"Failed to cut transcript: {str(e)}",
            "Check input data and retry"
        )


def match_music(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Handler for match_music method.
    
    Matches music assets to transcript segments based on emotional tone
    and contextual relevance. Returns structured match suggestions.
    
    This is the entry point for Story 5.4 - AI Music Matching.
    
    Args:
        params: Request parameters containing:
            - session_id: Session UUID (required)
            - segments: List of transcript segment dictionaries (required)
            - music_index: List of music asset dictionaries (required)
            - max_suggestions: Maximum matches per segment (optional, default: 3)
    
    Returns:
        Dictionary with segment_matches and match statistics
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Invalid parameters: expected object",
            "Check request format"
        )
    
    session_id = params.get("session_id")
    segments = params.get("segments")
    music_index = params.get("music_index")
    max_suggestions = params.get("max_suggestions", 3)
    
    if not session_id or not isinstance(session_id, str):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: session_id",
            "Provide a session_id string"
        )
    
    if not segments or not isinstance(segments, list):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: segments",
            "Provide a list of transcript segments"
        )
    
    if not music_index or not isinstance(music_index, list):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: music_index",
            "Provide a list of music assets"
        )
    
    # Check for empty music library
    if len(music_index) == 0:
        return _error_response(
            ERROR_CODES["EMPTY_MUSIC_LIBRARY"],
            "validation",
            "Music library is empty",
            "Index music assets before matching"
        )
    
    try:
        # Get session
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if session is None:
            return _error_response(
                ERROR_CODES["SESSION_NOT_FOUND"],
                "not_found",
                f"Session '{session_id}' not found",
                "Create a new session or check the session ID"
            )
        
        # Initialize music matcher
        matcher = MusicMatcher(max_suggestions=max_suggestions)
        
        logger.info(
            f"Matching music for {len(segments)} segments "
            f"with {len(music_index)} assets (session: {session_id})"
        )
        
        # Perform matching
        result = matcher.match_music_to_segments(
            segments=segments,
            music_index=music_index
        )
        
        # Check for low confidence warnings
        if result.warnings:
            logger.warning(f"Music matching warnings: {result.warnings}")
        
        # Prevent duplicate matches across segments
        result = matcher.prevent_duplicate_matches(result)
        
        logger.info(
            f"Music matching complete: {result.total_matches} matches "
            f"with avg confidence {result.average_confidence:.2f} "
            f"(session: {session_id})"
        )
        
        # Return result
        return {
            "result": result.to_dict(),
            "session_id": session_id
        }
        
    except ValueError as e:
        logger.exception(f"Validation error matching music: {e}")
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            f"Invalid data: {str(e)}",
            "Check segment and music index format"
        )
    except Exception as e:
        logger.exception(f"Failed to match music: {e}")
        return _error_response(
            ERROR_CODES["AI_INITIATE_ERROR"],
            "internal",
            f"Failed to match music: {str(e)}",
            "Check input data and retry"
        )


def match_music_with_progress(
    params: Dict[str, Any] | None
) -> Generator[Dict[str, Any], None, None]:
    """Streaming handler for match_music method with progress updates.
    
    Yields progress updates during music matching, then final result.
    
    Args:
        params: Request parameters (same as match_music)
    
    Yields:
        Progress updates and final result
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Invalid parameters: expected object",
            "Check request format"
        )
        return
    
    session_id = params.get("session_id")
    segments = params.get("segments")
    music_index = params.get("music_index")
    max_suggestions = params.get("max_suggestions", 3)
    
    if not session_id or not isinstance(session_id, str):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: session_id",
            "Provide a session_id string"
        )
        return
    
    if not segments or not isinstance(segments, list):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: segments",
            "Provide a list of transcript segments"
        )
        return
    
    if not music_index or not isinstance(music_index, list):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: music_index",
            "Provide a list of music assets"
        )
        return
    
    if len(music_index) == 0:
        yield _error_response(
            ERROR_CODES["EMPTY_MUSIC_LIBRARY"],
            "validation",
            "Music library is empty",
            "Index music assets before matching"
        )
        return
    
    try:
        # Get session
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if session is None:
            yield _error_response(
                ERROR_CODES["SESSION_NOT_FOUND"],
                "not_found",
                f"Session '{session_id}' not found",
                "Create a new session or check the session ID"
            )
            return
        
        yield _progress_response("match_music", 1, 4, "Initializing music matcher...")
        
        # Initialize music matcher
        matcher = MusicMatcher(max_suggestions=max_suggestions)
        
        yield _progress_response(
            "match_music", 
            2, 
            4, 
            f"Analyzing {len(segments)} segments and {len(music_index)} music assets..."
        )
        
        # Perform matching
        result = matcher.match_music_to_segments(
            segments=segments,
            music_index=music_index
        )
        
        yield _progress_response("match_music", 3, 4, "Optimizing matches and removing duplicates...")
        
        # Prevent duplicate matches
        result = matcher.prevent_duplicate_matches(result)
        
        yield _progress_response("match_music", 4, 4, "Music matching complete")
        
        logger.info(
            f"Music matching with progress complete: {result.total_matches} matches "
            f"(session: {session_id})"
        )
        
        # Return final result
        yield {
            "result": result.to_dict(),
            "session_id": session_id
        }
        
    except ValueError as e:
        logger.exception(f"Validation error matching music: {e}")
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            f"Invalid data: {str(e)}",
            "Check segment and music index format"
        )
    except Exception as e:
        logger.exception(f"Failed to match music: {e}")
        yield _error_response(
            ERROR_CODES["AI_INITIATE_ERROR"],
            "internal",
            f"Failed to match music: {str(e)}",
            "Check input data and retry"
        )


def match_sfx(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Handler for match_sfx method.
    
    Matches SFX assets to key moments in transcript segments based on
    context and subtlety requirements. Returns structured match suggestions.
    
    This is the entry point for Story 5.5 - AI SFX Matching.
    
    Args:
        params: Request parameters containing:
            - session_id: Session UUID (required)
            - segments: List of transcript segment dictionaries (required)
            - sfx_index: List of SFX asset dictionaries (required)
            - max_suggestions: Maximum matches per moment (optional, default: 3)
    
    Returns:
        Dictionary with moment_matches and match statistics
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Invalid parameters: expected object",
            "Check request format"
        )
    
    session_id = params.get("session_id")
    segments = params.get("segments")
    sfx_index = params.get("sfx_index")
    max_suggestions = params.get("max_suggestions", 3)
    
    if not session_id or not isinstance(session_id, str):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: session_id",
            "Provide a session_id string"
        )
    
    if not segments or not isinstance(segments, list):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: segments",
            "Provide a list of transcript segments"
        )
    
    if not sfx_index or not isinstance(sfx_index, list):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: sfx_index",
            "Provide a list of SFX assets"
        )
    
    # Check for empty SFX library
    if len(sfx_index) == 0:
        return _error_response(
            ERROR_CODES["EMPTY_SFX_LIBRARY"],
            "validation",
            "SFX library is empty",
            "Index SFX assets before matching"
        )
    
    try:
        # Get session
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if session is None:
            return _error_response(
                ERROR_CODES["SESSION_NOT_FOUND"],
                "not_found",
                f"Session '{session_id}' not found",
                "Create a new session or check the session ID"
            )
        
        # Initialize SFX matcher
        matcher = SFXMatcher(max_suggestions=max_suggestions)
        
        logger.info(
            f"Matching SFX for {len(segments)} segments "
            f"with {len(sfx_index)} assets (session: {session_id})"
        )
        
        # Step 1: Identify SFX moments
        moments = matcher.identify_sfx_moments(segments)
        
        if not moments:
            logger.warning(f"No SFX moments identified for session {session_id}")
            return {
                "result": {
                    "moment_matches": [],
                    "total_matches": 0,
                    "average_confidence": 0.0,
                    "average_subtlety": 0.0,
                    "fallback_used": False,
                    "layer_guidance": "Place each SFX on separate track for volume flexibility",
                    "warnings": ["No SFX moments identified in transcript segments"]
                },
                "session_id": session_id
            }
        
        # Step 2: Match SFX to moments
        result = matcher.match_sfx_to_moments(
            moments=moments,
            sfx_index=sfx_index
        )
        
        # Check for low confidence warnings
        if result.warnings:
            logger.warning(f"SFX matching warnings: {result.warnings}")
        
        # Prevent duplicate matches across moments
        result = matcher.prevent_duplicate_matches(result)
        
        logger.info(
            f"SFX matching complete: {result.total_matches} matches "
            f"({len(moments)} moments, avg confidence: {result.average_confidence:.2f}, "
            f"avg subtlety: {result.average_subtlety:.2f}) "
            f"(session: {session_id})"
        )
        
        # Return result
        return {
            "result": result.to_dict(),
            "session_id": session_id
        }
        
    except ValueError as e:
        logger.exception(f"Validation error matching SFX: {e}")
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            f"Invalid data: {str(e)}",
            "Check segment and SFX index format"
        )
    except Exception as e:
        logger.exception(f"Failed to match SFX: {e}")
        return _error_response(
            ERROR_CODES["AI_INITIATE_ERROR"],
            "internal",
            f"Failed to match SFX: {str(e)}",
            "Check input data and retry"
        )


def match_sfx_with_progress(
    params: Dict[str, Any] | None
) -> Generator[Dict[str, Any], None, None]:
    """Streaming handler for match_sfx method with progress updates.
    
    Yields progress updates during SFX moment identification and matching.
    
    Args:
        params: Request parameters (same as match_sfx)
    
    Yields:
        Progress updates and final result
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Invalid parameters: expected object",
            "Check request format"
        )
        return
    
    session_id = params.get("session_id")
    segments = params.get("segments")
    sfx_index = params.get("sfx_index")
    max_suggestions = params.get("max_suggestions", 3)
    
    if not session_id or not isinstance(session_id, str):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: session_id",
            "Provide a session_id string"
        )
        return
    
    if not segments or not isinstance(segments, list):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: segments",
            "Provide a list of transcript segments"
        )
        return
    
    if not sfx_index or not isinstance(sfx_index, list):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: sfx_index",
            "Provide a list of SFX assets"
        )
        return
    
    if len(sfx_index) == 0:
        yield _error_response(
            ERROR_CODES["EMPTY_SFX_LIBRARY"],
            "validation",
            "SFX library is empty",
            "Index SFX assets before matching"
        )
        return
    
    try:
        # Get session
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if session is None:
            yield _error_response(
                ERROR_CODES["SESSION_NOT_FOUND"],
                "not_found",
                f"Session '{session_id}' not found",
                "Create a new session or check the session ID"
            )
            return
        
        yield _progress_response("match_sfx", 1, 5, "Initializing SFX matcher...")
        
        # Initialize SFX matcher
        matcher = SFXMatcher(max_suggestions=max_suggestions)
        
        yield _progress_response(
            "match_sfx",
            2,
            5,
            f"Analyzing {len(segments)} segments for SFX moments..."
        )
        
        # Step 1: Identify SFX moments
        moments = matcher.identify_sfx_moments(segments)
        
        if not moments:
            yield _progress_response("match_sfx", 5, 5, "No SFX moments identified")
            logger.warning(f"No SFX moments identified for session {session_id}")
            yield {
                "result": {
                    "moment_matches": [],
                    "total_matches": 0,
                    "average_confidence": 0.0,
                    "average_subtlety": 0.0,
                    "fallback_used": False,
                    "layer_guidance": "Place each SFX on separate track for volume flexibility",
                    "warnings": ["No SFX moments identified in transcript segments"]
                },
                "session_id": session_id
            }
            return
        
        yield _progress_response(
            "match_sfx",
            3,
            5,
            f"Found {len(moments)} moments, matching against {len(sfx_index)} SFX assets..."
        )
        
        # Step 2: Match SFX to moments
        result = matcher.match_sfx_to_moments(
            moments=moments,
            sfx_index=sfx_index
        )
        
        yield _progress_response("match_sfx", 4, 5, "Optimizing matches and removing duplicates...")
        
        # Prevent duplicate matches
        result = matcher.prevent_duplicate_matches(result)
        
        yield _progress_response("match_sfx", 5, 5, "SFX matching complete")
        
        logger.info(
            f"SFX matching with progress complete: {result.total_matches} matches "
            f"({len(moments)} moments) (session: {session_id})"
        )
        
        # Return final result
        yield {
            "result": result.to_dict(),
            "session_id": session_id
        }
        
    except ValueError as e:
        logger.exception(f"Validation error matching SFX: {e}")
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            f"Invalid data: {str(e)}",
            "Check segment and SFX index format"
        )
    except Exception as e:
        logger.exception(f"Failed to match SFX: {e}")
        yield _error_response(
            ERROR_CODES["AI_INITIATE_ERROR"],
            "internal",
            f"Failed to match SFX: {str(e)}",
            "Check input data and retry"
        )


def match_vfx(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Handler for match_vfx method.
    
    Matches VFX templates to format requirements based on template asset groups,
    tag relevance, and placement constraints. Returns structured match suggestions.
    
    This is the entry point for Story 5.6 - AI VFX/Template Matching.
    
    Args:
        params: Request parameters containing:
            - session_id: Session UUID (required)
            - segments: List of transcript segment dictionaries (required)
            - format_template: Format template with vfx_requirements (required)
            - vfx_index: List of VFX asset dictionaries (required)
            - max_suggestions: Maximum matches per requirement (optional, default: 3)
    
    Returns:
        Dictionary with requirement_matches and match statistics
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Invalid parameters: expected object",
            "Check request format"
        )
    
    session_id = params.get("session_id")
    segments = params.get("segments")
    format_template = params.get("format_template")
    vfx_index = params.get("vfx_index")
    max_suggestions = params.get("max_suggestions", 3)
    
    if not session_id or not isinstance(session_id, str):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: session_id",
            "Provide a session_id string"
        )
    
    if not segments or not isinstance(segments, list):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: segments",
            "Provide a list of transcript segments"
        )
    
    if not format_template or not isinstance(format_template, dict):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: format_template",
            "Provide a format template with vfx_requirements"
        )
    
    if not vfx_index or not isinstance(vfx_index, list):
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: vfx_index",
            "Provide a list of VFX assets"
        )
    
    # Check for empty VFX library
    if len(vfx_index) == 0:
        return _error_response(
            ERROR_CODES["EMPTY_VFX_LIBRARY"],
            "validation",
            "VFX library is empty",
            "Index VFX assets before matching"
        )
    
    try:
        # Get session
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if session is None:
            return _error_response(
                ERROR_CODES["SESSION_NOT_FOUND"],
                "not_found",
                f"Session '{session_id}' not found",
                "Create a new session or check the session ID"
            )
        
        # Initialize VFX matcher
        matcher = VFXMatcher(max_suggestions=max_suggestions)
        
        # Get template asset groups if defined
        template_asset_groups = format_template.get("template_asset_groups", {})
        
        logger.info(
            f"Matching VFX for {len(segments)} segments "
            f"with {len(vfx_index)} assets (session: {session_id})"
        )
        
        # Step 1: Identify VFX requirements
        requirements = matcher.identify_vfx_requirements(segments, format_template)
        
        if not requirements:
            logger.warning(f"No VFX requirements identified for session {session_id}")
            return {
                "result": {
                    "requirement_matches": [],
                    "total_matches": 0,
                    "average_confidence": 0.0,
                    "fallback_used": False,
                    "placement_conflicts": [],
                    "template_group_coverage": 0.0,
                    "warnings": ["No VFX requirements identified in format template"]
                },
                "session_id": session_id
            }
        
        # Step 2: Match VFX to requirements
        result = matcher.match_vfx_to_requirements(
            requirements=requirements,
            vfx_index=vfx_index,
            template_asset_groups=template_asset_groups
        )
        
        # Check for placement conflicts and resolve them
        if result.placement_conflicts:
            logger.warning(
                f"Detected {len(result.placement_conflicts)} placement conflicts "
                f"for session {session_id}, resolving..."
            )
            result = matcher.resolve_placement_conflicts(result)
        
        # Check for low confidence warnings
        if result.warnings:
            logger.warning(f"VFX matching warnings: {result.warnings}")
        
        logger.info(
            f"VFX matching complete: {result.total_matches} matches "
            f"({len(requirements)} requirements, avg confidence: {result.average_confidence:.2f}, "
            f"group coverage: {result.template_group_coverage:.2%}) "
            f"(session: {session_id})"
        )
        
        # Return result
        return {
            "result": result.to_dict(),
            "session_id": session_id
        }
        
    except ValueError as e:
        logger.exception(f"Validation error matching VFX: {e}")
        return _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            f"Invalid data: {str(e)}",
            "Check segment, format template, and VFX index format"
        )
    except Exception as e:
        logger.exception(f"Failed to match VFX: {e}")
        return _error_response(
            ERROR_CODES["AI_INITIATE_ERROR"],
            "internal",
            f"Failed to match VFX: {str(e)}",
            "Check input data and retry"
        )


def match_vfx_with_progress(
    params: Dict[str, Any] | None
) -> Generator[Dict[str, Any], None, None]:
    """Streaming handler for match_vfx method with progress updates.
    
    Yields progress updates during VFX requirement identification and matching.
    
    Args:
        params: Request parameters (same as match_vfx)
    
    Yields:
        Progress updates and final result
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Invalid parameters: expected object",
            "Check request format"
        )
        return
    
    session_id = params.get("session_id")
    segments = params.get("segments")
    format_template = params.get("format_template")
    vfx_index = params.get("vfx_index")
    max_suggestions = params.get("max_suggestions", 3)
    
    if not session_id or not isinstance(session_id, str):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: session_id",
            "Provide a session_id string"
        )
        return
    
    if not segments or not isinstance(segments, list):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: segments",
            "Provide a list of transcript segments"
        )
        return
    
    if not format_template or not isinstance(format_template, dict):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: format_template",
            "Provide a format template with vfx_requirements"
        )
        return
    
    if not vfx_index or not isinstance(vfx_index, list):
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            "Missing required parameter: vfx_index",
            "Provide a list of VFX assets"
        )
        return
    
    if len(vfx_index) == 0:
        yield _error_response(
            ERROR_CODES["EMPTY_VFX_LIBRARY"],
            "validation",
            "VFX library is empty",
            "Index VFX assets before matching"
        )
        return
    
    try:
        # Get session
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if session is None:
            yield _error_response(
                ERROR_CODES["SESSION_NOT_FOUND"],
                "not_found",
                f"Session '{session_id}' not found",
                "Create a new session or check the session ID"
            )
            return
        
        yield _progress_response("match_vfx", 1, 5, "Initializing VFX matcher...")
        
        # Initialize VFX matcher
        matcher = VFXMatcher(max_suggestions=max_suggestions)
        
        # Get template asset groups if defined
        template_asset_groups = format_template.get("template_asset_groups", {})
        
        yield _progress_response(
            "match_vfx",
            2,
            5,
            f"Analyzing {len(segments)} segments for VFX requirements..."
        )
        
        # Step 1: Identify VFX requirements
        requirements = matcher.identify_vfx_requirements(segments, format_template)
        
        if not requirements:
            yield _progress_response("match_vfx", 5, 5, "No VFX requirements identified")
            logger.warning(f"No VFX requirements identified for session {session_id}")
            yield {
                "result": {
                    "requirement_matches": [],
                    "total_matches": 0,
                    "average_confidence": 0.0,
                    "fallback_used": False,
                    "placement_conflicts": [],
                    "template_group_coverage": 0.0,
                    "warnings": ["No VFX requirements identified in format template"]
                },
                "session_id": session_id
            }
            return
        
        yield _progress_response(
            "match_vfx",
            3,
            5,
            f"Found {len(requirements)} requirements, matching against {len(vfx_index)} VFX assets..."
        )
        
        # Step 2: Match VFX to requirements
        result = matcher.match_vfx_to_requirements(
            requirements=requirements,
            vfx_index=vfx_index,
            template_asset_groups=template_asset_groups
        )
        
        yield _progress_response("match_vfx", 4, 5, "Detecting and resolving placement conflicts...")
        
        # Resolve placement conflicts
        if result.placement_conflicts:
            result = matcher.resolve_placement_conflicts(result)
        
        yield _progress_response("match_vfx", 5, 5, "VFX matching complete")
        
        logger.info(
            f"VFX matching with progress complete: {result.total_matches} matches "
            f"({len(requirements)} requirements) (session: {session_id})"
        )
        
        # Return final result
        yield {
            "result": result.to_dict(),
            "session_id": session_id
        }
        
    except ValueError as e:
        logger.exception(f"Validation error matching VFX: {e}")
        yield _error_response(
            ERROR_CODES["INVALID_PARAMS"],
            "validation",
            f"Invalid data: {str(e)}",
            "Check segment, format template, and VFX index format"
        )
    except Exception as e:
        logger.exception(f"Failed to match VFX: {e}")
        yield _error_response(
            ERROR_CODES["AI_INITIATE_ERROR"],
            "internal",
            f"Failed to match VFX: {str(e)}",
            "Check input data and retry"
        )


# Handler registry
AI_HANDLERS = {
    "initiate_rough_cut": initiate_rough_cut,
    "send_data_to_ai": send_data_to_ai,
    "send_data_to_ai_with_progress": send_data_to_ai_with_progress,
    "cut_transcript": cut_transcript,
    "cut_transcript_with_progress": cut_transcript_with_progress,
    "match_music": match_music,
    "match_music_with_progress": match_music_with_progress,
    "match_sfx": match_sfx,
    "match_sfx_with_progress": match_sfx_with_progress,
    "match_vfx": match_vfx,
    "match_vfx_with_progress": match_vfx_with_progress,
}
