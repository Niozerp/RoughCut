"""VFX requirement identification data structures for AI asset matching.

Provides dataclasses for representing VFX requirements - specific visual effect
needs identified from format templates that must be matched to template assets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


#: VFX requirement type to tag mapping.
#: Maps requirement types to relevant VFX tag keywords for library searching.
VFX_REQUIREMENT_MAPPINGS = {
    "lower_third": ["lower_third", "nameplate", "speaker", "title", "corporate"],
    "transition": ["transition", "wipe", "fade", "dissolve", "cut"],
    "title_card": ["title", "card", "intro", "opening", "header"],
    "outro_cta": ["outro", "cta", "ending", "close", "call_to_action"],
    "logo_anim": ["logo", "brand", "anim", "animation", "intro"],
    "broll_placeholder": ["placeholder", "broll", "b_roll", "cutaway"],
}

#: Template type preferences by requirement type.
#: Specifies preferred template types for each requirement category.
REQUIREMENT_TYPE_PREFERENCES = {
    "lower_third": ["fusion_composition", "generator"],
    "transition": ["transition", "fusion_composition"],
    "title_card": ["fusion_composition", "generator"],
    "outro_cta": ["fusion_composition"],
    "logo_anim": ["fusion_composition"],
    "broll_placeholder": ["fusion_composition", "generator"],
}

#: Default duration requirements for VFX types (in seconds)
DEFAULT_DURATION_REQUIREMENTS = {
    "lower_third": 3.0,
    "transition": 1.0,
    "title_card": 5.0,
    "outro_cta": 5.0,
    "logo_anim": 3.0,
    "broll_placeholder": 2.0,
}


@dataclass
class VFXRequirement:
    """A VFX requirement identified from format template.
    
    Represents a specific need for a visual effect at a particular
    timestamp, such as lower thirds for speaker introductions or
    transitions between segments.
    
    Attributes:
        timestamp: Position in seconds where VFX should be placed
        type: Requirement type (lower_third, transition, title_card, etc.)
        context: Description of why VFX is needed (e.g., "speaker introduction")
        duration: Required duration in seconds
        format_section: Which format section this belongs to
        speaker_name: Optional speaker name for lower thirds
    """
    timestamp: float
    type: str
    context: str
    duration: float
    format_section: str
    speaker_name: Optional[str] = None
    
    def __post_init__(self):
        """Validate requirement fields after initialization."""
        if self.timestamp < 0:
            raise ValueError(f"timestamp cannot be negative: {self.timestamp}")
        
        valid_types = list(VFX_REQUIREMENT_MAPPINGS.keys())
        if self.type not in valid_types:
            raise ValueError(
                f"type must be one of {valid_types}, got: {self.type}"
            )
        
        if self.duration <= 0:
            raise ValueError(f"duration must be positive: {self.duration}")
        
        if not self.context:
            raise ValueError("context cannot be empty")
        if not self.format_section:
            raise ValueError("format_section cannot be empty")
    
    def to_tag_query(self) -> list[str]:
        """Convert requirement type to tag search terms.
        
        Returns the list of VFX tags relevant for this requirement type,
        which can be used to search the VFX template library.
        
        Returns:
            List of tag strings for VFX library searching
        """
        return VFX_REQUIREMENT_MAPPINGS.get(self.type, [])
    
    def get_preferred_template_types(self) -> list[str]:
        """Get preferred template types for this requirement.
        
        Returns:
            List of preferred template type strings
        """
        return REQUIREMENT_TYPE_PREFERENCES.get(self.type, ["fusion_composition"])
    
    def format_timestamp(self) -> str:
        """Format timestamp as MM:SS string.
        
        Returns:
            Formatted timestamp string (e.g., "2:30")
        """
        minutes = int(self.timestamp // 60)
        seconds = int(self.timestamp % 60)
        return f"{minutes}:{seconds:02d}"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of VFX requirement
        """
        return {
            "timestamp": self.timestamp,
            "type": self.type,
            "context": self.context,
            "duration": self.duration,
            "format_section": self.format_section,
            "speaker_name": self.speaker_name
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VFXRequirement":
        """Create from dictionary.
        
        Args:
            data: Dictionary with requirement data
            
        Returns:
            VFXRequirement instance
            
        Raises:
            ValueError: If data is None, not a dict, or has invalid field types
        """
        if data is None:
            raise ValueError("data cannot be None")
        if not isinstance(data, dict):
            raise ValueError(f"data must be a dictionary, got {type(data).__name__}")
        
        # Validate timestamp
        try:
            timestamp = float(data.get("timestamp", 0.0))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid timestamp value: {e}")
        
        # Validate duration
        try:
            duration = float(data.get("duration", 0.0))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid duration value: {e}")
        
        return cls(
            timestamp=timestamp,
            type=data.get("type", ""),
            context=data.get("context", ""),
            duration=duration,
            format_section=data.get("format_section", ""),
            speaker_name=data.get("speaker_name")
        )


@dataclass
class VFXRequirementList:
    """A collection of VFX requirements for a format template.
    
    Groups all identified VFX requirements across a format,
    providing utilities for requirement management and validation.
    
    Attributes:
        requirements: List of VFXRequirement instances
        source_template: Name of the source format template
    """
    requirements: list[VFXRequirement] = field(default_factory=list)
    source_template: str = ""
    
    def __post_init__(self):
        """Validate requirement list after initialization."""
        if self.requirements is None:
            self.requirements = []
    
    def get_requirements_by_type(self, req_type: str) -> list[VFXRequirement]:
        """Get all requirements of a specific type.
        
        Args:
            req_type: Type of requirement to filter by
            
        Returns:
            List of matching VFXRequirement instances
        """
        return [r for r in self.requirements if r.type == req_type]
    
    def get_requirements_by_section(self, section_name: str) -> list[VFXRequirement]:
        """Get all requirements for a specific format section.
        
        Args:
            section_name: Name of format section to filter by
            
        Returns:
            List of matching VFXRequirement instances
        """
        return [r for r in self.requirements if r.format_section == section_name]
    
    def has_requirement_at_timestamp(self, timestamp: float, tolerance: float = 1.0) -> bool:
        """Check if a requirement exists near a given timestamp.
        
        Args:
            timestamp: Timestamp to check (in seconds)
            tolerance: Time tolerance in seconds (default: 1.0)
            
        Returns:
            True if a requirement exists within tolerance
        """
        for req in self.requirements:
            if abs(req.timestamp - timestamp) <= tolerance:
                return True
        return False
    
    def get_conflicting_requirements(self) -> list[tuple[VFXRequirement, VFXRequirement]]:
        """Find requirements that overlap in time.
        
        Returns:
            List of tuples containing overlapping requirement pairs
        """
        conflicts = []
        sorted_reqs = sorted(self.requirements, key=lambda r: r.timestamp)
        
        for i, req1 in enumerate(sorted_reqs):
            req1_end = req1.timestamp + req1.duration
            for req2 in sorted_reqs[i + 1:]:
                req2_end = req2.timestamp + req2.duration
                
                # Check for overlap
                if req1.timestamp < req2_end and req2.timestamp < req1_end:
                    conflicts.append((req1, req2))
        
        return conflicts
    
    def sort_by_timestamp(self) -> None:
        """Sort requirements by timestamp (ascending)."""
        self.requirements.sort(key=lambda r: r.timestamp)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of requirement list
        """
        return {
            "requirements": [r.to_dict() for r in self.requirements],
            "source_template": self.source_template,
            "total_requirements": len(self.requirements)
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VFXRequirementList":
        """Create from dictionary.
        
        Args:
            data: Dictionary with requirement list data
            
        Returns:
            VFXRequirementList instance
        """
        if data is None:
            return cls()
        
        reqs_data = data.get("requirements", [])
        requirements = []
        for r_data in reqs_data:
            try:
                requirements.append(VFXRequirement.from_dict(r_data))
            except ValueError as e:
                # Skip invalid requirements
                continue
        
        return cls(
            requirements=requirements,
            source_template=data.get("source_template", "")
        )
