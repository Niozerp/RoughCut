# Blind Hunter Review: Story 3.3 - Select Template for Rough Cut

## Your Role
You are the **Blind Hunter** — a cynical code reviewer with NO context, NO spec, and NO patience for sloppy work. You see only the code diff.

## Mission
Find at least 10 issues. Assume the developer is a corner-cutting weasel. Be ruthless.

## Files to Review (New/Modified)

1. **src/roughcut/backend/workflows/session.py** (~8.5 KB) - NEW - Session management
2. **src/roughcut/backend/workflows/rough_cut.py** (~4.2 KB) - NEW - Data preparation
3. **src/roughcut/backend/workflows/__init__.py** - NEW - Module exports
4. **src/roughcut/protocols/handlers/workflows.py** (~8.8 KB) - NEW - Protocol handlers
5. **src/roughcut/protocols/handlers/formats.py** (~12 KB) - MODIFIED - Added select_format_template
6. **src/roughcut/protocols/dispatcher.py** - MODIFIED - Registered handlers
7. **lua/ui/rough_cut_workflow.lua** (~16 KB) - MODIFIED - Full workflow UI
8. **tests/unit/backend/workflows/test_session.py** (~8.2 KB) - NEW - Unit tests
9. **tests/unit/protocols/handlers/test_workflows.py** (~6.1 KB) - NEW - Handler tests

## Output Format

For each finding:
```
- **Issue**: Brief title
- **Location**: file.py:line-range
- **Evidence**: What the code does
- **Severity**: Critical/High/Med/Low
- **Fix**: What should change
```

Look for:
- Security holes (injection, traversal, exposure)
- Logic errors (race conditions, null checks, state bugs)
- Missing error handling
- Type safety issues
- Resource leaks
- API design flaws

If truly no issues found, say: "No issues found - this code is suspiciously clean."

---

## FILE: session.py

```python
"""Session management for rough cut workflow."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from roughcut.backend.formats.models import FormatTemplate


@dataclass
class RoughCutSession:
    """Represents a rough cut creation session."""
    
    session_id: str
    created_at: datetime
    status: str = "created"
    
    media_clip_id: Optional[str] = None
    media_clip_name: Optional[str] = None
    transcription_data: Optional[Dict[str, Any]] = None
    format_template_id: Optional[str] = None
    format_template: Optional[FormatTemplate] = None
    last_accessed: Optional[datetime] = None
    
    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = self.created_at
    
    def can_select_format(self) -> bool:
        return self.status in ["transcription_reviewed", "format_selected"]
    
    def can_generate(self) -> bool:
        return (
            self.status == "format_selected"
            and self.media_clip_id is not None
            and self.format_template_id is not None
        )
    
    def select_media(self, clip_id: str, clip_name: str) -> None:
        self.media_clip_id = clip_id
        self.media_clip_name = clip_name
        self.status = "media_selected"
        self.last_accessed = datetime.now()
    
    def review_transcription(self, transcription_data: Dict[str, Any]) -> None:
        self.transcription_data = transcription_data
        self.status = "transcription_reviewed"
        self.last_accessed = datetime.now()
    
    def select_format(self, template: FormatTemplate) -> None:
        if not template or not template.slug:
            raise ValueError("Invalid template: must have slug")
        
        if not self.can_select_format():
            raise ValueError(
                f"Cannot select format from status: {self.status}. "
                "Must complete transcription review first."
            )
        
        self.format_template_id = template.slug
        self.format_template = template
        self.status = "format_selected"
        self.last_accessed = datetime.now()
    
    def start_generation(self) -> None:
        if not self.can_generate():
            raise ValueError(
                f"Cannot start generation from status: {self.status}. "
                "Must select media, transcription, and format template first."
            )
        
        self.status = "generating"
        self.last_accessed = datetime.now()
    
    def complete(self) -> None:
        self.status = "complete"
        self.last_accessed = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
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
        if not self.can_generate():
            raise ValueError("Session not ready for generation")
        
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
    """Manages rough cut sessions in memory."""
    
    def __init__(self):
        self._sessions: Dict[str, RoughCutSession] = {}
    
    def create_session(self) -> RoughCutSession:
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        session = RoughCutSession(
            session_id=session_id,
            created_at=now,
            status="created",
            last_accessed=now
        )
        
        self._sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[RoughCutSession]:
        return self._sessions.get(session_id)
    
    def update_session(self, session: RoughCutSession) -> None:
        if not session or not session.session_id:
            raise ValueError("Invalid session: must have session_id")
        
        self._sessions[session.session_id] = session
    
    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def session_exists(self, session_id: str) -> bool:
        return session_id in self._sessions
    
    def list_sessions(self) -> List[str]:
        return list(self._sessions.keys())
    
    def cleanup_expired(self, max_age_minutes: int = 60) -> int:
        now = datetime.now()
        expired = []
        
        for session_id, session in self._sessions.items():
            if session.last_accessed:
                age = (now - session.last_accessed).total_seconds() / 60
                if age > max_age_minutes:
                    expired.append(session_id)
        
        for session_id in expired:
            del self._sessions[session_id]
        
        return len(expired)


_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def reset_session_manager() -> None:
    global _session_manager
    _session_manager = None
```

## FILE: workflows.py (protocol handlers excerpt)

```python
def select_format_template(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Handler for select_format_template method."""
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
    template_id = params.get("template_id")
    
    if not session_id or not isinstance(session_id, str):
        return {...}  # error response
    
    if not template_id or not isinstance(template_id, str):
        return {...}  # error response
    
    # Get session manager and retrieve session
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    
    if session is None:
        return {...}  # SESSION_NOT_FOUND error
    
    # Sanitize template_id
    sanitized_id = _sanitize_template_id(template_id)
    if not sanitized_id:
        return {...}  # INVALID_PARAMS error
    
    # Find templates directory
    templates_dir = _find_templates_directory()
    template_file = templates_dir / f"{sanitized_id}.md"
    
    if not template_file.exists():
        return {...}  # TEMPLATE_NOT_FOUND error
    
    # Parse the template
    parser = TemplateParser()
    template = parser.parse_file(template_file)
    
    if template is None:
        return {...}  # TEMPLATE_PARSE_ERROR
    
    # Validate session state
    if not session.can_select_format():
        return {...}  # INVALID_STATE error
    
    # Update session
    try:
        session.select_format(template)
        session_manager.update_session(session)
    except ValueError as e:
        return {...}  # error response
    
    return {
        "result": {
            "session_id": session.session_id,
            "template_id": template.slug,
            "template_name": template.name,
            "status": session.status,
            "can_generate": session.can_generate()
        }
    }
```

## Your Review

Provide your findings below. Be specific, cite line numbers, and suggest fixes.
