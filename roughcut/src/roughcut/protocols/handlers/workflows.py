"""Protocol handlers for rough cut workflow operations.

Handles JSON-RPC requests for session management and rough cut
data preparation.
"""

import logging
from typing import Any, Dict

from ...backend.workflows.session import get_session_manager, RoughCutSession
from ...backend.workflows.rough_cut import prepare_rough_cut_data

logger = logging.getLogger(__name__)

# Error codes for consistent error handling
ERROR_CODES = {
    "INVALID_PARAMS": "INVALID_PARAMS",
    "SESSION_NOT_FOUND": "SESSION_NOT_FOUND",
    "SESSION_CREATE_ERROR": "SESSION_CREATE_ERROR",
    "INVALID_STATE": "INVALID_STATE",
    "INCOMPLETE_DATA": "INCOMPLETE_DATA",
    "PREPARE_ERROR": "PREPARE_ERROR"
}


def create_rough_cut_session(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Handler for create_rough_cut_session method.
    
    Creates a new rough cut session for tracking multi-step workflow state.
    
    Args:
        params: Request parameters (optional, for future extensions)
    
    Returns:
        Dictionary with session_id and initial status
    """
    try:
        session_manager = get_session_manager()
        session = session_manager.create_session()
        
        logger.info(f"Created rough cut session: {session.session_id}")
        
        return {
            "result": {
                "session_id": session.session_id,
                "status": session.status,
                "created_at": session.created_at.isoformat() if session.created_at else None
            }
        }
        
    except Exception as e:
        logger.exception(f"Failed to create rough cut session: {e}")
        return {
            "error": {
                "code": ERROR_CODES["SESSION_CREATE_ERROR"],
                "category": "internal",
                "message": f"Failed to create session: {str(e)}",
                "suggestion": "Try again or restart the application"
            }
        }


def get_session_status(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Handler for get_session_status method.
    
    Retrieves current status and progress of a rough cut session.
    
    Args:
        params: Request parameters containing:
            - session_id: Session UUID (required)
    
    Returns:
        Dictionary with session status and workflow progress
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        return {
            "error": {
                "code": ERROR_CODES["INVALID_PARAMS"],
                "category": "validation",
                "message": "Invalid parameters: expected object",
                "suggestion": "Check request format"
            }
        }
    
    session_id = params.get("session_id")
    if not session_id or not isinstance(session_id, str):
        return {
            "error": {
                "code": ERROR_CODES["INVALID_PARAMS"],
                "category": "validation",
                "message": "Missing required parameter: session_id",
                "suggestion": "Provide a session_id string in the params object"
            }
        }
    
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if session is None:
            return {
                "error": {
                    "code": ERROR_CODES["SESSION_NOT_FOUND"],
                    "category": "not_found",
                    "message": f"Session '{session_id}' not found",
                    "suggestion": "Create a new session or check the session ID"
                }
            }
        
        return {
            "result": session.to_dict()
        }
        
    except Exception as e:
        logger.exception(f"Failed to get session status: {e}")
        return {
            "error": {
                "code": ERROR_CODES["SESSION_NOT_FOUND"],
                "category": "internal",
                "message": f"Failed to retrieve session: {str(e)}",
                "suggestion": "Try again or create a new session"
            }
        }


def select_media_for_session(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Handler for select_media_for_session method.
    
    Updates session with selected media clip information.
    
    Args:
        params: Request parameters containing:
            - session_id: Session UUID (required)
            - clip_id: Resolve Media Pool clip ID (required)
            - clip_name: Human-readable clip name (required)
    
    Returns:
        Dictionary with updated session status
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        return {
            "error": {
                "code": ERROR_CODES["INVALID_PARAMS"],
                "category": "validation",
                "message": "Invalid parameters: expected object",
                "suggestion": "Check request format"
            }
        }
    
    session_id = params.get("session_id")
    clip_id = params.get("clip_id")
    clip_name = params.get("clip_name")
    
    if not session_id or not isinstance(session_id, str):
        return {
            "error": {
                "code": ERROR_CODES["INVALID_PARAMS"],
                "category": "validation",
                "message": "Missing required parameter: session_id",
                "suggestion": "Provide a session_id string"
            }
        }
    
    if not clip_id or not isinstance(clip_id, str):
        return {
            "error": {
                "code": ERROR_CODES["INVALID_PARAMS"],
                "category": "validation",
                "message": "Missing required parameter: clip_id",
                "suggestion": "Provide a clip_id string"
            }
        }
    
    if not clip_name or not isinstance(clip_name, str):
        return {
            "error": {
                "code": ERROR_CODES["INVALID_PARAMS"],
                "category": "validation",
                "message": "Missing required parameter: clip_name",
                "suggestion": "Provide a clip_name string"
            }
        }
    
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if session is None:
            return {
                "error": {
                    "code": ERROR_CODES["SESSION_NOT_FOUND"],
                    "category": "not_found",
                    "message": f"Session '{session_id}' not found",
                    "suggestion": "Create a new session or check the session ID"
                }
            }
        
        # Update session with media selection
        session.select_media(clip_id, clip_name)
        session_manager.update_session(session)
        
        logger.info(f"Selected media for session {session_id}: {clip_name}")
        
        return {
            "result": {
                "session_id": session.session_id,
                "status": session.status,
                "media_clip_id": session.media_clip_id,
                "media_clip_name": session.media_clip_name
            }
        }
        
    except Exception as e:
        logger.exception(f"Failed to select media: {e}")
        return {
            "error": {
                "code": ERROR_CODES["INVALID_STATE"],
                "category": "internal",
                "message": f"Failed to select media: {str(e)}",
                "suggestion": "Try again or restart the workflow"
            }
        }


def review_transcription_for_session(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Handler for review_transcription_for_session method.
    
    Updates session with transcription data after review.
    
    Args:
        params: Request parameters containing:
            - session_id: Session UUID (required)
            - transcription_data: Resolve transcription output (required)
    
    Returns:
        Dictionary with updated session status
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        return {
            "error": {
                "code": ERROR_CODES["INVALID_PARAMS"],
                "category": "validation",
                "message": "Invalid parameters: expected object",
                "suggestion": "Check request format"
            }
        }
    
    session_id = params.get("session_id")
    transcription_data = params.get("transcription_data")
    
    if not session_id or not isinstance(session_id, str):
        return {
            "error": {
                "code": ERROR_CODES["INVALID_PARAMS"],
                "category": "validation",
                "message": "Missing required parameter: session_id",
                "suggestion": "Provide a session_id string"
            }
        }
    
    if not transcription_data or not isinstance(transcription_data, dict):
        return {
            "error": {
                "code": ERROR_CODES["INVALID_PARAMS"],
                "category": "validation",
                "message": "Missing or invalid parameter: transcription_data",
                "suggestion": "Provide a transcription_data object"
            }
        }
    
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if session is None:
            return {
                "error": {
                    "code": ERROR_CODES["SESSION_NOT_FOUND"],
                    "category": "not_found",
                    "message": f"Session '{session_id}' not found",
                    "suggestion": "Create a new session or check the session ID"
                }
            }
        
        # Validate session state
        if session.status != "media_selected":
            return {
                "error": {
                    "code": ERROR_CODES["INVALID_STATE"],
                    "category": "validation",
                    "message": f"Cannot review transcription from state: {session.status}",
                    "suggestion": "Select media before reviewing transcription"
                }
            }
        
        # Update session with transcription data
        session.review_transcription(transcription_data)
        session_manager.update_session(session)
        
        logger.info(f"Reviewed transcription for session {session_id}")
        
        return {
            "result": {
                "session_id": session.session_id,
                "status": session.status,
                "can_select_format": session.can_select_format()
            }
        }
        
    except Exception as e:
        logger.exception(f"Failed to review transcription: {e}")
        return {
            "error": {
                "code": ERROR_CODES["INVALID_STATE"],
                "category": "internal",
                "message": f"Failed to review transcription: {str(e)}",
                "suggestion": "Try again or restart the workflow"
            }
        }


def prepare_rough_cut_for_generation(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Handler for prepare_rough_cut_for_generation method.
    
    Prepares and returns all data needed for rough cut generation.
    
    Args:
        params: Request parameters containing:
            - session_id: Session UUID (required)
    
    Returns:
        Dictionary with complete data payload for AI processing
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        return {
            "error": {
                "code": ERROR_CODES["INVALID_PARAMS"],
                "category": "validation",
                "message": "Invalid parameters: expected object",
                "suggestion": "Check request format"
            }
        }
    
    session_id = params.get("session_id")
    if not session_id or not isinstance(session_id, str):
        return {
            "error": {
                "code": ERROR_CODES["INVALID_PARAMS"],
                "category": "validation",
                "message": "Missing required parameter: session_id",
                "suggestion": "Provide a session_id string"
            }
        }
    
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if session is None:
            return {
                "error": {
                    "code": ERROR_CODES["SESSION_NOT_FOUND"],
                    "category": "not_found",
                    "message": f"Session '{session_id}' not found",
                    "suggestion": "Create a new session or check the session ID"
                }
            }
        
        # Validate that session is ready for generation
        if not session.can_generate():
            return {
                "error": {
                    "code": ERROR_CODES["INCOMPLETE_DATA"],
                    "category": "validation",
                    "message": f"Session not ready for generation. Status: {session.status}",
                    "suggestion": "Complete all workflow steps: select media, review transcription, select format template"
                }
            }
        
        # Prepare rough cut data
        try:
            data = prepare_rough_cut_data(session)
            
            # Mark session as generating
            session.start_generation()
            session_manager.update_session(session)
            
            logger.info(f"Prepared rough cut data for session {session_id}")
            
            return {
                "result": {
                    "session_id": session.session_id,
                    "status": session.status,
                    "data": data
                }
            }
            
        except ValueError as e:
            logger.error(f"Data preparation failed: {e}")
            return {
                "error": {
                    "code": ERROR_CODES["INCOMPLETE_DATA"],
                    "category": "validation",
                    "message": f"Missing required data: {str(e)}",
                    "suggestion": "Ensure all workflow steps are completed"
                }
            }
        
    except Exception as e:
        logger.exception(f"Failed to prepare rough cut: {e}")
        return {
            "error": {
                "code": ERROR_CODES["PREPARE_ERROR"],
                "category": "internal",
                "message": f"Failed to prepare rough cut: {str(e)}",
                "suggestion": "Try again or restart the workflow"
            }
        }


# Handler registry
WORKFLOW_HANDLERS = {
    "create_rough_cut_session": create_rough_cut_session,
    "get_session_status": get_session_status,
    "select_media_for_session": select_media_for_session,
    "review_transcription_for_session": review_transcription_for_session,
    "prepare_rough_cut_for_generation": prepare_rough_cut_for_generation,
}
