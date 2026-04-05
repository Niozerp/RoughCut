"""Segment tone analysis data structures for music matching.

Provides dataclasses for representing emotional tone analysis of transcript
segments to enable context-aware music matching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


#: Tone-to-tag mapping for music matching.
#: Maps common emotional tone descriptions to relevant music tag keywords.
#: These mappings are used to expand tone descriptors into searchable tag terms.
#: Add new mappings here to support additional emotional categories.
TONE_TAG_MAPPINGS = {
    "corporate upbeat": ["corporate", "upbeat", "business", "professional", "confident"],
    "contemplative": ["ambient", "soft", "thoughtful", "piano", "acoustic", "reflective"],
    "triumphant": ["epic", "orchestral", "victory", "uplifting", "heroic", "inspiring"],
    "tense": ["tension", "suspense", "dark", "dramatic", "thriller", "intense"],
    "emotional": ["emotional", "sad", "moving", "touching", "heartfelt", "sentimental"],
    "energetic": ["energetic", "fast", "driving", "rock", "electronic", "upbeat", "dynamic"],
    "calm": ["calm", "peaceful", "relaxing", "meditation", "serene", "gentle"],
    "romantic": ["romantic", "love", "tender", "passionate", "sweet"],
    "mysterious": ["mysterious", "enigmatic", "intriguing", "atmospheric"],
    "playful": ["playful", "fun", "light", "cheerful", "whimsical"],
}


@dataclass
class SegmentTone:
    """Emotional tone analysis for a transcript segment.
    
    Represents the emotional characteristics of a transcript segment
    to enable context-aware music matching. Includes energy level,
    mood descriptors, and genre hints.
    
    Attributes:
        energy: Energy level - "high", "medium", or "low"
        mood: Primary mood descriptor (e.g., "upbeat", "contemplative", "triumphant")
        genre_hint: Suggested genre category (e.g., "corporate", "ambient", "orchestral")
        keywords: Extracted emotional keywords for tag matching
        secondary_moods: Additional mood descriptors (optional)
    """
    energy: str
    mood: str
    genre_hint: str
    keywords: list[str] = field(default_factory=list)
    secondary_moods: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate tone fields after initialization."""
        valid_energy = ["high", "medium", "low"]
        if self.energy not in valid_energy:
            raise ValueError(
                f"energy must be one of {valid_energy}, got: {self.energy}"
            )
        if not self.mood:
            raise ValueError("mood cannot be empty")
        if not self.genre_hint:
            raise ValueError("genre_hint cannot be empty")
        if self.keywords is None:
            self.keywords = []
        if self.secondary_moods is None:
            self.secondary_moods = []
    
    def to_tag_query(self) -> list[str]:
        """Convert tone to tag search terms.
        
        Combines mood, genre_hint, and keywords into a prioritized
        list of search tags for music matching.
        
        Returns:
            List of tag strings in priority order
        """
        tags: list[str] = []
        tag_set: set[str] = set()  # For O(1) duplicate checking
        
        # Primary mood is highest priority
        if self.mood:
            mood_lower = self.mood.casefold()
            tags.append(mood_lower)
            tag_set.add(mood_lower)
        
        # Genre hint is second priority
        if self.genre_hint:
            genre_lower = self.genre_hint.casefold()
            if genre_lower not in tag_set:
                tags.append(genre_lower)
                tag_set.add(genre_lower)
        
        # Look up mapped tags for the mood
        mood_key = f"{self.genre_hint} {self.mood}".strip().casefold()
        if mood_key in TONE_TAG_MAPPINGS:
            for tag in TONE_TAG_MAPPINGS[mood_key]:
                tag_cf = tag.casefold()
                if tag_cf not in tag_set:
                    tags.append(tag_cf)
                    tag_set.add(tag_cf)
        
        # Also try just the mood
        if self.mood.casefold() in TONE_TAG_MAPPINGS:
            for tag in TONE_TAG_MAPPINGS[self.mood.casefold()]:
                tag_cf = tag.casefold()
                if tag_cf not in tag_set:
                    tags.append(tag_cf)
                    tag_set.add(tag_cf)
        
        # Add keywords
        for keyword in self.keywords:
            if keyword:
                kw_cf = keyword.casefold()
                if kw_cf not in tag_set:
                    tags.append(kw_cf)
                    tag_set.add(kw_cf)
        
        # Add secondary moods
        for mood in self.secondary_moods:
            if mood:
                mood_cf = mood.casefold()
                if mood_cf not in tag_set:
                    tags.append(mood_cf)
                    tag_set.add(mood_cf)
        
        return tags
    
    def get_confidence_weight(self) -> float:
        """Calculate confidence weight for this tone analysis.
        
        Returns higher weight for tones with more specific descriptors.
        
        Returns:
            Confidence weight between 0.5 and 1.0
        """
        weight = 0.7  # Base weight
        
        # Boost for having keywords
        if self.keywords:
            weight += 0.1 * min(len(self.keywords) / 5, 0.2)
        
        # Boost for secondary moods
        if self.secondary_moods:
            weight += 0.1 * min(len(self.secondary_moods) / 3, 0.1)
        
        return min(weight, 1.0)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of tone analysis
        """
        return {
            "energy": self.energy,
            "mood": self.mood,
            "genre_hint": self.genre_hint,
            "keywords": self.keywords,
            "secondary_moods": self.secondary_moods
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SegmentTone":
        """Create from dictionary.
        
        Args:
            data: Dictionary with tone data
            
        Returns:
            SegmentTone instance
            
        Raises:
            ValueError: If data is None, not a dict, or has invalid field types
        """
        if data is None:
            raise ValueError("data cannot be None")
        if not isinstance(data, dict):
            raise ValueError(f"data must be a dictionary, got {type(data).__name__}")
        
        # Validate keywords is a list
        keywords = data.get("keywords", [])
        if not isinstance(keywords, list):
            raise ValueError(f"keywords must be a list, got {type(keywords).__name__}")
        
        # Validate secondary_moods is a list
        secondary_moods = data.get("secondary_moods", [])
        if not isinstance(secondary_moods, list):
            raise ValueError(
                f"secondary_moods must be a list, got {type(secondary_moods).__name__}"
            )
        
        return cls(
            energy=data.get("energy", "medium"),
            mood=data.get("mood", ""),
            genre_hint=data.get("genre_hint", ""),
            keywords=keywords,
            secondary_moods=secondary_moods
        )
