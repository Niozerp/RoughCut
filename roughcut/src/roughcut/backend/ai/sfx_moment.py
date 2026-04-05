"""SFX moment identification data structures for AI asset matching.

Provides dataclasses for representing SFX moments - specific timestamps
in transcript segments where sound effects would enhance the narrative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


#: SFX moment type to tag mapping.
#: Maps moment types to relevant SFX tag keywords for library searching.
SFX_MOMENT_MAPPINGS = {
    "intro": ["intro", "whoosh", "transition", "opening", "start", "fade_in"],
    "transition": ["transition", "whoosh", "swoosh", "change", "shift", "crossfade"],
    "emphasis": ["impact", "accent", "hit", "emphasis", "punch", "sting"],
    "triumph": ["success", "triumphant", "win", "positive", "celebration", "victory"],
    "tension": ["tension", "suspense", "build", "anticipation", "dramatic"],
    "outro": ["outro", "ending", "close", "finish", "chime", "fade_out"],
    "underscore": ["underscore", "bed", "ambient", "background", "texture"],
}

#: Intensity-based subtlety preference mapping.
#: Maps intensity levels to preferred subtlety scores (higher = more subtle).
INTENSITY_SUBTLETY_PREFERENCE = {
    "low": 0.85,  # Very subtle sounds (ambient, underscore)
    "medium": 0.70,  # Moderate impact (transitions, light emphasis)
    "high": 0.50,  # More prominent (strong impacts, dramatic moments)
}


@dataclass
class SFXMoment:
    """A moment in the transcript suitable for SFX placement.
    
    Represents a specific timestamp where a sound effect would add value
    to the narrative, such as transitions, emotional beats, or emphasis points.
    
    Attributes:
        timestamp: Position in seconds where SFX should be placed
        type: Moment type (intro, transition, emphasis, triumph, etc.)
        context: Description of why SFX fits this moment
        intensity: Intensity level (low, medium, high) indicating subtlety needs
        segment_name: Which transcript segment this moment belongs to
    """
    timestamp: float
    type: str
    context: str
    intensity: str
    segment_name: str
    
    def __post_init__(self):
        """Validate moment fields after initialization."""
        if self.timestamp < 0:
            raise ValueError(f"timestamp cannot be negative: {self.timestamp}")
        
        valid_types = list(SFX_MOMENT_MAPPINGS.keys())
        if self.type not in valid_types:
            raise ValueError(
                f"type must be one of {valid_types}, got: {self.type}"
            )
        
        valid_intensity = ["low", "medium", "high"]
        if self.intensity not in valid_intensity:
            raise ValueError(
                f"intensity must be one of {valid_intensity}, got: {self.intensity}"
            )
        
        if not self.context:
            raise ValueError("context cannot be empty")
        if not self.segment_name:
            raise ValueError("segment_name cannot be empty")
    
    def to_tag_query(self) -> list[str]:
        """Convert moment type to tag search terms.
        
        Returns the list of SFX tags relevant for this moment type,
        which can be used to search the SFX library.
        
        Returns:
            List of tag strings for SFX library searching
        """
        return SFX_MOMENT_MAPPINGS.get(self.type, [])
    
    def get_subtlety_preference(self) -> float:
        """Get the preferred subtlety score for this moment.
        
        Returns the ideal subtlety score based on moment intensity.
        Higher values indicate more subtle (quieter/less jarring) sounds.
        
        Returns:
            Preferred subtlety score (0.0 to 1.0)
        """
        return INTENSITY_SUBTLETY_PREFERENCE.get(self.intensity, 0.70)
    
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
            Dictionary representation of SFX moment
        """
        return {
            "timestamp": self.timestamp,
            "type": self.type,
            "context": self.context,
            "intensity": self.intensity,
            "segment_name": self.segment_name
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SFXMoment":
        """Create from dictionary.
        
        Args:
            data: Dictionary with moment data
            
        Returns:
            SFXMoment instance
            
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
        
        return cls(
            timestamp=timestamp,
            type=data.get("type", ""),
            context=data.get("context", ""),
            intensity=data.get("intensity", "medium"),
            segment_name=data.get("segment_name", "")
        )


@dataclass
class SFXMomentList:
    """A collection of SFX moments for a transcript.
    
    Groups all identified SFX moments across segments,
    providing utilities for moment management and validation.
    
    Attributes:
        moments: List of SFXMoment instances
        source_segments: Number of source transcript segments
    """
    moments: list[SFXMoment] = field(default_factory=list)
    source_segments: int = 0
    
    def __post_init__(self):
        """Validate moment list after initialization."""
        if self.moments is None:
            self.moments = []
    
    def get_moments_by_type(self, moment_type: str) -> list[SFXMoment]:
        """Get all moments of a specific type.
        
        Args:
            moment_type: Type of moment to filter by
            
        Returns:
            List of matching SFXMoment instances
        """
        return [m for m in self.moments if m.type == moment_type]
    
    def get_moments_by_segment(self, segment_name: str) -> list[SFXMoment]:
        """Get all moments for a specific segment.
        
        Args:
            segment_name: Name of segment to filter by
            
        Returns:
            List of matching SFXMoment instances
        """
        return [m for m in self.moments if m.segment_name == segment_name]
    
    def has_moment_at_timestamp(self, timestamp: float, tolerance: float = 1.0) -> bool:
        """Check if a moment exists near a given timestamp.
        
        Args:
            timestamp: Timestamp to check (in seconds)
            tolerance: Time tolerance in seconds (default: 1.0)
            
        Returns:
            True if a moment exists within tolerance
        """
        for moment in self.moments:
            if abs(moment.timestamp - timestamp) <= tolerance:
                return True
        return False
    
    def sort_by_timestamp(self) -> None:
        """Sort moments by timestamp (ascending)."""
        self.moments.sort(key=lambda m: m.timestamp)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of moment list
        """
        return {
            "moments": [m.to_dict() for m in self.moments],
            "source_segments": self.source_segments,
            "total_moments": len(self.moments)
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SFXMomentList":
        """Create from dictionary.
        
        Args:
            data: Dictionary with moment list data
            
        Returns:
            SFXMomentList instance
        """
        if data is None:
            return cls()
        
        moments_data = data.get("moments", [])
        moments = []
        for m_data in moments_data:
            try:
                moments.append(SFXMoment.from_dict(m_data))
            except ValueError as e:
                # Skip invalid moments
                continue
        
        return cls(
            moments=moments,
            source_segments=data.get("source_segments", 0)
        )
