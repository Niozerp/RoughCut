"""Session management for rough cut workflow.

Defines the RoughCutSession dataclass and SessionManager for tracking
multi-step rough cut creation workflow state.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from roughcut.backend.formats.models import FormatTemplate


class SessionStatus(Enum):
    """Enumeration of valid session workflow statuses.
    
    Defines the state machine for rough cut creation workflow:
    CREATED → MEDIA_SELECTED → TRANSCRIPTION_REVIEWED → FORMAT_SELECTED → GENERATING → COMPLETE
    """
    CREATED = "created"
    MEDIA_SELECTED = "media_selected"
    TRANSCRIPTION_REVIEWED = "transcription_reviewed"
    FORMAT_SELECTED = "format_selected"
    GENERATING = "generating"
    COMPLETE = "complete"


# Maximum number of sessions allowed (prevents memory exhaustion)
MAX_SESSIONS = 1000


@dataclass
class RoughCutSession:
    """Represents a rough cut creation session.
    
    Tracks workflow progress through multi-step rough cut creation:
    1. Media selection
    2. Transcription review
    3. Format template selection
    4. Rough cut generation
    
    Attributes:
        session_id: Unique identifier (UUID) for session identification
        created_at: Session creation timestamp
        status: Current workflow status (SessionStatus enum value)
        media_clip_id: Resolve Media Pool clip ID (optional)
        media_clip_name: Human-readable clip name (optional)
        transcription_data: Resolve transcription output (optional)
        format_template_id: Selected template slug (optional)
        format_template: Full template object cached after selection (optional)
        last_accessed: Last activity timestamp for session management
    """
    
    session_id: str
    created_at: datetime
    status: str = "created"
    
    # Workflow data (populated progressively)
    media_clip_id: Optional[str] = None
    media_clip_name: Optional[str] = None
    transcription_data: Optional[Dict[str, Any]] = None
    format_template_id: Optional[str] = None
    format_template: Optional[FormatTemplate] = None
    rough_cut_document: Optional[Any] = None
    
    # Session management
    last_accessed: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize last_accessed timestamp and validate status."""
        if self.last_accessed is None:
            self.last_accessed = self.created_at
        
        # Validate session_id is non-empty
        if not self.session_id or not isinstance(self.session_id, str):
            raise ValueError("session_id must be a non-empty string")
        
        # Validate status is a valid SessionStatus
        try:
            SessionStatus(self.status)
        except ValueError:
            raise ValueError(f"Invalid status: {self.status}. Must be one of: {[s.value for s in SessionStatus]}")
    
    def _get_status_enum(self) -> SessionStatus:
        """Get SessionStatus enum from status string."""
        return SessionStatus(self.status)
    
    def _update_status(self, new_status: SessionStatus) -> None:
        """Update status with proper validation."""
        self.status = new_status.value
        self.last_accessed = datetime.now()
    
    def can_select_format(self) -> bool:
        """Validate that format selection is allowed at current state.
        
        Format selection requires that transcription has been reviewed.
        Can only select format FROM transcription_reviewed state.
        
        Returns:
            True if format selection is allowed, False otherwise
        """
        return self._get_status_enum() == SessionStatus.TRANSCRIPTION_REVIEWED
    
    def can_generate(self) -> bool:
        """Validate that rough cut generation is allowed.
        
        Generation requires:
        - Status is format_selected
        - Media selected (media_clip_id present)
        - Transcription reviewed (transcription_data present)
        - Format template selected (format_template_id and format_template present)
        
        Returns:
            True if generation is allowed, False otherwise
        """
        return (
            self._get_status_enum() == SessionStatus.FORMAT_SELECTED
            and self.media_clip_id is not None
            and self.format_template_id is not None
            and self.transcription_data is not None
            and self.format_template is not None
        )
    
    def select_media(self, clip_id: str, clip_name: str) -> None:
        """Update session with selected media clip.
        
        Args:
            clip_id: Resolve Media Pool clip ID
            clip_name: Human-readable clip name
            
        Raises:
            ValueError: If clip_id or clip_name is empty, or if session not in valid state
        """
        # Validate state - media can only be selected from CREATED state
        current_status = self._get_status_enum()
        if current_status != SessionStatus.CREATED:
            raise ValueError(
                f"Cannot select media from status: {self.status}. "
                f"Must be in '{SessionStatus.CREATED.value}' state."
            )
        
        # Validate inputs
        if not clip_id or not isinstance(clip_id, str) or not clip_id.strip():
            raise ValueError("clip_id must be a non-empty string")
        
        if not clip_name or not isinstance(clip_name, str) or not clip_name.strip():
            raise ValueError("clip_name must be a non-empty string")
        
        self.media_clip_id = clip_id
        self.media_clip_name = clip_name
        self._update_status(SessionStatus.MEDIA_SELECTED)
    
    def review_transcription(self, transcription_data: Dict[str, Any]) -> None:
        """Update session with transcription data after review.
        
        Args:
            transcription_data: Resolve transcription output
            
        Raises:
            ValueError: If transcription_data is None/empty, or if session not in valid state
        """
        # Validate state - transcription can only be reviewed after media selected
        current_status = self._get_status_enum()
        if current_status != SessionStatus.MEDIA_SELECTED:
            raise ValueError(
                f"Cannot review transcription from status: {self.status}. "
                f"Must be in '{SessionStatus.MEDIA_SELECTED.value}' state."
            )
        
        # Validate transcription data
        if not transcription_data or not isinstance(transcription_data, dict):
            raise ValueError("transcription_data must be a non-empty dictionary")
        
        self.transcription_data = transcription_data
        self._update_status(SessionStatus.TRANSCRIPTION_REVIEWED)
    
    def select_format(self, template: FormatTemplate) -> None:
        """Update session with selected format template.
        
        Args:
            template: FormatTemplate instance
            
        Raises:
            ValueError: If template is invalid or session not in correct state
        """
        if not template or not template.slug:
            raise ValueError("Invalid template: must have slug")
        
        if not self.can_select_format():
            raise ValueError(
                f"Cannot select format from status: {self.status}. "
                f"Must be in '{SessionStatus.TRANSCRIPTION_REVIEWED.value}' state."
            )
        
        self.format_template_id = template.slug
        self.format_template = template
        self._update_status(SessionStatus.FORMAT_SELECTED)
    
    def start_generation(self) -> None:
        """Mark session as entering generation phase.
        
        Raises:
            ValueError: If session not ready for generation, or generation already in progress
        """
        current_status = self._get_status_enum()
        
        # Check if already generating
        if current_status == SessionStatus.GENERATING:
            raise ValueError("Generation already in progress for this session")
        
        # Validate all requirements for generation
        if current_status != SessionStatus.FORMAT_SELECTED:
            raise ValueError(
                f"Cannot start generation from status: {self.status}. "
                f"Must be in '{SessionStatus.FORMAT_SELECTED.value}' state."
            )
        
        if not self.media_clip_id:
            raise ValueError("Cannot start generation: media_clip_id is missing")
        
        if not self.transcription_data:
            raise ValueError("Cannot start generation: transcription_data is missing")
        
        if not self.format_template_id or not self.format_template:
            raise ValueError("Cannot start generation: format_template is missing")
        
        # Atomic state transition
        self._update_status(SessionStatus.GENERATING)
    
    def complete(self) -> None:
        """Mark session as complete.
        
        Raises:
            ValueError: If session not in valid state to complete
        """
        current_status = self._get_status_enum()
        
        # Can only complete from GENERATING state
        if current_status != SessionStatus.GENERATING:
            raise ValueError(
                f"Cannot complete from status: {self.status}. "
                f"Must be in '{SessionStatus.GENERATING.value}' state."
            )
        
        self._update_status(SessionStatus.COMPLETE)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of session state
        """
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "status": self.status,
            "media_clip_id": self.media_clip_id,
            "media_clip_name": self.media_clip_name,
            "has_transcription": self.transcription_data is not None,
            "format_template_id": self.format_template_id,
            "format_template_name": self.format_template.name if self.format_template else None,
            "can_generate": self.can_generate(),
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None
        }
    
    def get_generation_data(self) -> Dict[str, Any]:
        """Get all data needed for rough cut generation.
        
        Returns:
            Dictionary with transcript, template rules, and metadata
            
        Raises:
            ValueError: If required data is missing
        """
        # Validate all required fields are present
        if self._get_status_enum() != SessionStatus.FORMAT_SELECTED:
            raise ValueError(f"Session not ready for generation. Status: {self.status}")
        
        if not self.media_clip_id:
            raise ValueError("Missing media_clip_id")
        
        if not self.media_clip_name:
            raise ValueError("Missing media_clip_name")
        
        if not self.transcription_data:
            raise ValueError("Missing transcription data")
        
        if not self.format_template:
            raise ValueError("Missing format template")
        
        return {
            "session_id": self.session_id,
            "media_clip_id": self.media_clip_id,
            "media_clip_name": self.media_clip_name,
            "transcription": self.transcription_data,
            "format_template": {
                "slug": self.format_template.slug,
                "name": self.format_template.name,
                "description": self.format_template.description,
                "segments": [s.to_dict() for s in self.format_template.segments],
                "asset_groups": [a.to_dict() for a in self.format_template.asset_groups]
            }
        }


class SessionManager:
    """Manages rough cut sessions in memory.
    
    Provides in-memory session storage (MVP - no persistence required).
    Sessions are created, retrieved, and updated during the rough cut
    workflow lifecycle.
    
    Example:
        manager = SessionManager()
        session = manager.create_session()
        session.select_media("clip_001", "Interview_Segment_1")
        manager.update_session(session)
    """
    
    def __init__(self):
        """Initialize session storage."""
        self._sessions: Dict[str, RoughCutSession] = {}
    
    def create_session(self) -> RoughCutSession:
        """Create new rough cut session.
        
        Returns:
            New RoughCutSession with generated UUID
            
        Raises:
            RuntimeError: If session limit exceeded
        """
        # Check session limit to prevent memory exhaustion
        if len(self._sessions) >= MAX_SESSIONS:
            raise RuntimeError(
                f"Session limit exceeded: {MAX_SESSIONS}. "
                "Please cleanup expired sessions or increase limit."
            )
        
        session_id = str(uuid.uuid4())
        
        # Handle extremely unlikely UUID collision
        while session_id in self._sessions:
            session_id = str(uuid.uuid4())
        
        now = datetime.now()
        
        session = RoughCutSession(
            session_id=session_id,
            created_at=now,
            status=SessionStatus.CREATED.value,
            last_accessed=now
        )
        
        self._sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[RoughCutSession]:
        """Retrieve session by ID.
        
        Args:
            session_id: Session UUID to retrieve
            
        Returns:
            RoughCutSession if found, None otherwise
        """
        return self._sessions.get(session_id)
    
    def update_session(self, session: RoughCutSession) -> None:
        """Update session state.
        
        Args:
            session: Updated RoughCutSession instance
            
        Raises:
            ValueError: If session is invalid or session_id not found
        """
        if not session or not session.session_id:
            raise ValueError("Invalid session: must have session_id")
        
        # Prevent creating ghost sessions - session must exist
        if session.session_id not in self._sessions:
            raise ValueError(
                f"Session not found: {session.session_id}. "
                "Cannot update non-existent session."
            )
        
        self._sessions[session.session_id] = session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session.
        
        Args:
            session_id: Session UUID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists.
        
        Args:
            session_id: Session UUID to check
            
        Returns:
            True if session exists, False otherwise
        """
        return session_id in self._sessions
    
    def list_sessions(self) -> List[str]:
        """List all active session IDs.
        
        Returns:
            List of session UUIDs
        """
        return list(self._sessions.keys())
    
    def cleanup_expired(self, max_age_minutes: int = 60) -> int:
        """Remove sessions older than max_age_minutes.
        
        Args:
            max_age_minutes: Maximum age in minutes before session is considered expired.
                Must be a positive number.
            
        Returns:
            Number of sessions cleaned up
            
        Raises:
            ValueError: If max_age_minutes is not positive
        """
        if not isinstance(max_age_minutes, (int, float)):
            raise ValueError("max_age_minutes must be a number")
        
        if max_age_minutes <= 0:
            raise ValueError("max_age_minutes must be positive")
        
        now = datetime.now()
        expired = []
        
        # Use list() to avoid "dictionary changed size during iteration" error
        for session_id, session in list(self._sessions.items()):
            if session.last_accessed:
                age = (now - session.last_accessed).total_seconds() / 60
                if age > max_age_minutes:
                    expired.append(session_id)
            else:
                # Sessions without last_accessed are considered expired
                expired.append(session_id)
        
        for session_id in expired:
            if session_id in self._sessions:
                del self._sessions[session_id]
        
        return len(expired)
    
    def clear_all_sessions(self) -> int:
        """Clear all sessions. Useful for testing and shutdown.
        
        Returns:
            Number of sessions cleared
        """
        count = len(self._sessions)
        self._sessions.clear()
        return count


# Global session manager instance
_session_manager: Optional[SessionManager] = None

# Lock for thread-safe singleton initialization
_session_manager_lock = threading.Lock()


def get_session_manager() -> SessionManager:
    """Get the global session manager instance.
    
    Creates the singleton if it doesn't exist.
    Thread-safe implementation using double-checked locking pattern.
    
    Returns:
        Global SessionManager instance
    """
    global _session_manager
    
    # First check without lock (fast path)
    if _session_manager is None:
        # Acquire lock and check again (slow path)
        with _session_manager_lock:
            if _session_manager is None:
                _session_manager = SessionManager()
    
    return _session_manager


def reset_session_manager() -> None:
    """Reset the global session manager (for testing).
    
    Clears all sessions and resets the singleton.
    """
    global _session_manager
    
    with _session_manager_lock:
        if _session_manager is not None:
            _session_manager.clear_all_sessions()
            _session_manager = None
