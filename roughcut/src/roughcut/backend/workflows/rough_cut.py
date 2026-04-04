"""Rough cut data preparation for AI processing.

Prepares and formats all data needed for rough cut generation,
including transcript, format template rules, and media index.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from roughcut.backend.workflows.session import RoughCutSession


class RoughCutDataPreparer:
    """Prepares data for rough cut generation.
    
    Collects and formats all necessary data from a rough cut session
    for sending to the AI service. Validates that all required
    data is present before generation.
    
    Example:
        session = session_manager.get_session(session_id)
        preparer = RoughCutDataPreparer(session)
        data = preparer.prepare()
    """
    
    def __init__(self, session: "RoughCutSession"):
        """Initialize with rough cut session.
        
        Args:
            session: RoughCutSession with workflow data
        """
        self.session = session
    
    def validate(self) -> tuple[bool, List[str]]:
        """Validate that all required data is present.
        
        Checks for:
        - Media clip selected
        - Transcription data available
        - Format template selected
        - Session in correct state
        
        Returns:
            Tuple of (is_valid, list of missing fields)
        """
        missing = []
        
        if not self.session.media_clip_id:
            missing.append("media_clip_id")
        
        if not self.session.media_clip_name:
            missing.append("media_clip_name")
        
        if not self.session.transcription_data:
            missing.append("transcription_data")
        
        if not self.session.format_template_id:
            missing.append("format_template_id")
        
        if not self.session.format_template:
            missing.append("format_template")
        
        if self.session.status != "format_selected":
            missing.append(f"session status (expected 'format_selected', got '{self.session.status}')")
        
        return (len(missing) == 0, missing)
    
    def prepare(self) -> Dict[str, Any]:
        """Prepare complete data payload for AI generation.
        
        Returns:
            Dictionary with all data needed for AI processing
            
        Raises:
            ValueError: If validation fails or required data missing
        """
        is_valid, missing = self.validate()
        
        if not is_valid:
            raise ValueError(f"Missing required data: {', '.join(missing)}")
        
        template = self.session.format_template
        
        # Build the complete payload
        return {
            "session_id": self.session.session_id,
            "media": {
                "clip_id": self.session.media_clip_id,
                "clip_name": self.session.media_clip_name
            },
            "transcription": self.session.transcription_data,
            "format": {
                "slug": template.slug,
                "name": template.name,
                "description": template.description,
                "structure": template.structure,
                "segments": [self._format_segment(s) for s in template.segments],
                "asset_groups": [self._format_asset_group(a) for a in template.asset_groups]
            }
        }
    
    def _format_segment(self, segment) -> Dict[str, Any]:
        """Format a template segment for AI payload.
        
        Args:
            segment: TemplateSegment instance
            
        Returns:
            Formatted segment dictionary
        """
        return {
            "name": segment.name,
            "start_time": segment.start_time,
            "end_time": segment.end_time,
            "duration": segment.duration,
            "purpose": segment.purpose
        }
    
    def _format_asset_group(self, asset_group) -> Dict[str, Any]:
        """Format an asset group for AI payload.
        
        Args:
            asset_group: AssetGroup instance
            
        Returns:
            Formatted asset group dictionary
        """
        return {
            "category": asset_group.category,
            "name": asset_group.name,
            "description": asset_group.description,
            "search_tags": asset_group.search_tags
        }
    
    def get_summary(self) -> str:
        """Generate human-readable summary of prepared data.
        
        Returns:
            Multi-line string summary
        """
        template = self.session.format_template
        
        lines = [
            "Rough Cut Data Summary:",
            f"  Media: {self.session.media_clip_name}",
            f"  Format: {template.name if template else 'Not selected'}",
            f"  Segments: {len(template.segments) if template else 0}",
            f"  Asset Groups: {len(template.asset_groups) if template else 0}",
            f"  Has Transcription: {self.session.transcription_data is not None}"
        ]
        
        return "\n".join(lines)


def prepare_rough_cut_data(session: "RoughCutSession") -> Dict[str, Any]:
    """Convenience function to prepare rough cut data.
    
    Args:
        session: RoughCutSession with workflow data
        
    Returns:
        Dictionary with all data needed for AI processing
        
    Raises:
        ValueError: If validation fails or required data missing
    """
    preparer = RoughCutDataPreparer(session)
    return preparer.prepare()
