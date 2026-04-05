"""Music matching data structures for AI asset matching.

Provides dataclasses for representing music matches, including match scoring,
confidence levels, and match reasoning for context-aware music selection.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .segment_tone import SegmentTone


# Confidence threshold for high-confidence matches
HIGH_CONFIDENCE_THRESHOLD = 0.80
LOW_CONFIDENCE_THRESHOLD = 0.60


@dataclass
class MusicAsset:
    """Represents a music asset from the indexed library.
    
    Simplified representation of a music asset for matching purposes.
    Contains only metadata needed for matching, not full file data.
    
    Attributes:
        music_id: Unique identifier for the asset
        file_path: Absolute path to the music file
        tags: AI-generated tags for the asset
        category: Asset category (always "music" for this class)
        folder_context: Parent folder path for context matching
    """
    music_id: str
    file_path: str
    tags: List[str]
    category: str = "music"
    folder_context: str = ""
    
    def __post_init__(self):
        """Validate asset fields after initialization."""
        if not self.music_id:
            raise ValueError("music_id cannot be empty")
        if not self.file_path:
            raise ValueError("file_path cannot be empty")
        if not isinstance(self.tags, list):
            raise ValueError(f"tags must be a list, got {type(self.tags).__name__}")
        if self.tags is None:
            self.tags = []
    
    def get_file_name(self) -> str:
        """Extract filename from file path.
        
        Returns:
            Filename without directory path
        """
        import os
        return os.path.basename(self.file_path)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MusicAsset":
        """Create from dictionary.
        
        Args:
            data: Dictionary with asset data
            
        Returns:
            MusicAsset instance
            
        Raises:
            ValueError: If data is None, not a dict, or has invalid field types
        """
        if data is None:
            raise ValueError("data cannot be None")
        if not isinstance(data, dict):
            raise ValueError(f"data must be a dictionary, got {type(data).__name__}")
        
        # Validate tags is a list
        tags = data.get("tags", [])
        if not isinstance(tags, list):
            raise ValueError(f"tags must be a list, got {type(tags).__name__}")
        
        return cls(
            music_id=data.get("id", ""),
            file_path=data.get("file_path", ""),
            tags=tags,
            category=data.get("category", "music"),
            folder_context=data.get("folder_context", "")
        )


@dataclass
class MusicMatch:
    """A music asset matched to a segment.
    
    Represents a successful match between a transcript segment's tone
    and a music asset from the indexed library. Includes confidence
    scoring and match reasoning.
    
    Attributes:
        music_id: Unique identifier for the matched asset
        file_path: Absolute path to the music file
        file_name: Filename without directory path
        folder_context: Parent folder path for context
        match_reason: Human-readable explanation of why this match was selected
        confidence_score: Match confidence from 0.0 to 1.0
        matched_tags: List of tags that contributed to the match
        suggested_start: Recommended start time on timeline (seconds)
        suggested_end: Recommended end time on timeline (seconds)
        quality_indicators: Optional file quality metadata (bitrate, sample_rate)
    """
    music_id: str
    file_path: str
    file_name: str
    folder_context: str
    match_reason: str
    confidence_score: float
    matched_tags: List[str]
    suggested_start: float = 0.0
    suggested_end: float = 0.0
    quality_indicators: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate match fields after initialization."""
        if not self.music_id:
            raise ValueError("music_id cannot be empty")
        if not self.file_path:
            raise ValueError("file_path cannot be empty")
        if not self.file_name:
            raise ValueError("file_name cannot be empty")
        if self.matched_tags is None:
            self.matched_tags = []
        if self.quality_indicators is None:
            self.quality_indicators = {}
        
        # Validate confidence score range
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(
                f"confidence_score must be between 0.0 and 1.0, got {self.confidence_score}"
            )
        
        # Validate timestamps
        if self.suggested_start < 0:
            raise ValueError(f"suggested_start cannot be negative: {self.suggested_start}")
        if self.suggested_end < 0:
            raise ValueError(f"suggested_end cannot be negative: {self.suggested_end}")
    
    def is_high_confidence(self) -> bool:
        """Returns True if confidence >= HIGH_CONFIDENCE_THRESHOLD.
        
        Returns:
            True if this is a high-confidence match
        """
        return self.confidence_score >= HIGH_CONFIDENCE_THRESHOLD
    
    def is_low_confidence(self) -> bool:
        """Returns True if confidence < LOW_CONFIDENCE_THRESHOLD.
        
        Returns:
            True if this is a low-confidence match
        """
        return self.confidence_score < LOW_CONFIDENCE_THRESHOLD
    
    def format_suggestion(self) -> str:
        """Format as human-readable suggestion string.
        
        Returns formatted string like:
        "Music: corporate_bright_theme.wav (from 'corporate/upbeat' folder)"
        
        Returns:
            Formatted suggestion string
        """
        return f"Music: {self.file_name} (from '{self.folder_context}' folder)"
    
    def format_match_details(self) -> str:
        """Format detailed match information.
        
        Returns formatted string with match details:
        "Found: corporate_bright_theme.wav - Match: 92% (corporate, upbeat)"
        
        Returns:
            Formatted match details string
        """
        confidence_pct = int(self.confidence_score * 100)
        tags_str = ", ".join(self.matched_tags[:3])  # Show top 3 tags
        return f"Found: {self.file_name} - Match: {confidence_pct}% ({tags_str})"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of match
        """
        return {
            "music_id": self.music_id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "folder_context": self.folder_context,
            "match_reason": self.match_reason,
            "confidence_score": self.confidence_score,
            "matched_tags": self.matched_tags,
            "suggested_start": self.suggested_start,
            "suggested_end": self.suggested_end,
            "quality_indicators": self.quality_indicators
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MusicMatch":
        """Create from dictionary.
        
        Args:
            data: Dictionary with match data
            
        Returns:
            MusicMatch instance
            
        Raises:
            ValueError: If data is None, not a dict, or has invalid field types
        """
        if data is None:
            raise ValueError("data cannot be None")
        if not isinstance(data, dict):
            raise ValueError(f"data must be a dictionary, got {type(data).__name__}")
        
        # Validate confidence_score
        try:
            confidence_score = float(data.get("confidence_score", 0.0))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid confidence_score value: {e}")
        
        # Validate timestamps
        try:
            suggested_start = float(data.get("suggested_start", 0.0))
            suggested_end = float(data.get("suggested_end", 0.0))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid timestamp value in data: {e}")
        
        # Validate matched_tags
        matched_tags = data.get("matched_tags", [])
        if not isinstance(matched_tags, list):
            raise ValueError(f"matched_tags must be a list, got {type(matched_tags).__name__}")
        
        # Validate quality_indicators
        quality_indicators = data.get("quality_indicators", {})
        if not isinstance(quality_indicators, dict):
            raise ValueError(
                f"quality_indicators must be a dict, got {type(quality_indicators).__name__}"
            )
        
        return cls(
            music_id=data.get("music_id", ""),
            file_path=data.get("file_path", ""),
            file_name=data.get("file_name", ""),
            folder_context=data.get("folder_context", ""),
            match_reason=data.get("match_reason", ""),
            confidence_score=confidence_score,
            matched_tags=matched_tags,
            suggested_start=suggested_start,
            suggested_end=suggested_end,
            quality_indicators=quality_indicators
        )


@dataclass
class SegmentMusicMatches:
    """All music matches for a single segment.
    
    Groups all music match candidates for a single transcript segment,
    including the segment's tone analysis and fallback options.
    
    Attributes:
        segment_name: Name of the transcript segment
        segment_tone: Tone analysis for this segment
        matches: List of music match candidates (sorted by confidence)
        fallback_suggestion: Optional fallback if no good matches
    """
    segment_name: str
    segment_tone: SegmentTone
    matches: List[MusicMatch]
    fallback_suggestion: Optional[MusicMatch] = None
    
    def __post_init__(self):
        """Validate segment matches after initialization."""
        if not self.segment_name:
            raise ValueError("segment_name cannot be empty")
        if self.matches is None:
            self.matches = []
        
        # Sort matches by confidence score (highest first)
        self.matches.sort(key=lambda m: m.confidence_score, reverse=True)
    
    def top_match(self) -> Optional[MusicMatch]:
        """Return highest confidence match.
        
        Returns:
            The MusicMatch with highest confidence, or None if no matches
        """
        if self.matches:
            return self.matches[0]
        return self.fallback_suggestion
    
    def get_high_confidence_matches(self) -> List[MusicMatch]:
        """Return matches with high confidence.
        
        Returns:
            List of matches with confidence >= HIGH_CONFIDENCE_THRESHOLD
        """
        return [m for m in self.matches if m.is_high_confidence()]
    
    def has_good_matches(self) -> bool:
        """Check if there are any viable matches.
        
        Returns:
            True if there's at least one match with confidence >= LOW_CONFIDENCE_THRESHOLD
        """
        if not self.matches:
            return False
        return any(m.confidence_score >= LOW_CONFIDENCE_THRESHOLD for m in self.matches)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of segment matches
        """
        result = {
            "segment_name": self.segment_name,
            "segment_tone": self.segment_tone.to_dict(),
            "matches": [m.to_dict() for m in self.matches],
            "fallback_suggestion": None
        }
        
        if self.fallback_suggestion:
            result["fallback_suggestion"] = self.fallback_suggestion.to_dict()
        
        return result


@dataclass
class MusicMatchingResult:
    """Result of AI music matching operation.
    
    Contains all music match results for all segments, including
    statistics and warnings about the matching process.
    
    Attributes:
        segment_matches: List of segment match results
        total_matches: Total number of music matches across all segments
        average_confidence: Average confidence score across all matches
        fallback_used: True if any segment used fallback suggestion
        warnings: List of non-fatal issues (e.g., low confidence, no matches)
    """
    segment_matches: List[SegmentMusicMatches]
    total_matches: int
    average_confidence: float
    fallback_used: bool
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate result after initialization."""
        if self.segment_matches is None:
            self.segment_matches = []
        if self.warnings is None:
            self.warnings = []
        
        # Recalculate total_matches if not provided correctly
        expected_total = sum(len(sm.matches) for sm in self.segment_matches)
        if self.total_matches != expected_total:
            self.total_matches = expected_total
        
        # Recalculate average confidence if not provided correctly
        all_confidences = [
            m.confidence_score 
            for sm in self.segment_matches 
            for m in sm.matches
        ]
        if all_confidences:
            self.average_confidence = sum(all_confidences) / len(all_confidences)
        else:
            self.average_confidence = 0.0
    
    def get_all_matches(self) -> List[MusicMatch]:
        """Get all music matches across all segments.
        
        Returns:
            Flat list of all MusicMatch instances
        """
        return [
            match 
            for sm in self.segment_matches 
            for match in sm.matches
        ]
    
    def get_low_confidence_warnings(self) -> List[str]:
        """Get warnings for low-confidence segments.
        
        Returns:
            List of warning strings for segments with poor matches
        """
        warnings = []
        for sm in self.segment_matches:
            if not sm.has_good_matches() and sm.segment_name:
                warnings.append(
                    f"Low confidence matches for segment '{sm.segment_name}'"
                )
        return warnings
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of result
        """
        return {
            "segment_matches": [sm.to_dict() for sm in self.segment_matches],
            "total_matches": self.total_matches,
            "average_confidence": self.average_confidence,
            "fallback_used": self.fallback_used,
            "warnings": self.warnings
        }
