"""Protocol handlers for AI-powered rough cut generation.

Handles JSON-RPC requests for initiating and managing rough cut
AI processing, including progress reporting and error handling.
"""

import asyncio
import logging
import uuid
from typing import Any, Callable, Dict, Generator, Optional

from ...backend.ai.data_bundle import DataBundleBuilder
from ...backend.ai.openai_client import OpenAIClient
from ...backend.ai.prompt_engine import PromptBuilder
from ...backend.ai.rough_cut_orchestrator import RoughCutOrchestrator
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


# Handler registry
AI_HANDLERS = {
    "initiate_rough_cut": initiate_rough_cut,
    "send_data_to_ai": send_data_to_ai,
    "send_data_to_ai_with_progress": send_data_to_ai_with_progress,
}
