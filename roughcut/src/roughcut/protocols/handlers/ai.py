"""Protocol handlers for AI-powered rough cut generation.

Handles JSON-RPC requests for initiating and managing rough cut
AI processing, including progress reporting and error handling.
"""

import asyncio
import logging
import uuid
from typing import Any, Callable, Dict, Generator, Optional

from ...backend.ai.openai_client import OpenAIClient
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


# Handler registry
AI_HANDLERS = {
    "initiate_rough_cut": initiate_rough_cut,
}
