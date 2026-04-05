"""SFX matching data structures for AI asset matching.

Provides dataclasses for representing SFX matches, including match scoring,
confidence levels, subtlety scores, and match reasoning for context-aware
sound effect selection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .sfx_moment import SFXMoment


#: Confidence threshold for high-confidence SFX matches
HIGH_CONFIDENCE_THRESHOLD = 0.80
#: Confidence threshold for low-confidence SFX matches
LOW_CONFIDENCE_THRESHOLD = 0.60
#: Subtlety threshold for subtle (non-distracting) sounds
HIGH_SUBTLETY_THRESHOLD = 0.80


@dataclass
class SFXAsset:
    """Represents an SFX asset from the indexed library.
    
    Simplified representation of a sound effect asset for matching purposes.
    Contains only metadata needed for matching, not full file data.
    
    Attributes:
        sfx_id: Unique identifier for the asset
        file_path: Absolute path to the SFX file
        tags: AI-generated tags for the asset
        category: Asset category (always "sfx" for this class)
        folder_context: Parent folder path for context matching
        duration_ms: Duration in milliseconds (optional)
    """
    sfx_id: str
    file_path: str
    tags: list[str]
    category: str = "sfx"
    folder_context: str = ""
    duration_ms: int = 0
    
    def __post_init__(self):
        """Validate asset fields after initialization."""
        if not self.sfx_id:
            raise ValueError("sfx_id cannot be empty")
        if not self.file_path:
            raise ValueError("file_path cannot be empty")
        if not isinstance(self.tags, list):
            raise ValueError(f"tags must be a list, got {type(self.tags).__name__}")
        if self.tags is None:
            self.tags = []
        if self.duration_ms < 0:
            raise ValueError(f"duration_ms cannot be negative: {self.duration_ms}")
    
    def get_file_name(self) -> str:
        """Extract filename from file path.
        
        Returns:
            Filename without directory path
        """
        import os
        return os.path.basename(self.file_path)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SFXAsset":
        """Create from dictionary.
        
        Args:
            data: Dictionary with asset data
            
        Returns:
            SFXAsset instance
            
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
        
        # Validate duration_ms
        try:
            duration_ms = int(data.get("duration_ms", 0))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid duration_ms value: {e}")
        
        return cls(
            sfx_id=data.get("id", ""),
            file_path=data.get("file_path", ""),
            tags=tags,
            category=data.get("category", "sfx"),
            folder_context=data.get("folder_context", ""),
            duration_ms=duration_ms
        )


@dataclass
class SFXMatch:
    """An SFX asset matched to a moment.
    
    Represents a successful match between a transcript moment and
    a sound effect from the indexed library. Includes confidence
    scoring, subtlety assessment, and match reasoning.
    
    Attributes:
        sfx_id: Unique identifier for the matched asset
        file_path: Absolute path to the SFX file
        file_name: Filename without directory path
        folder_context: Parent folder path for context
        match_reason: Human-readable explanation of why this match was selected
        confidence_score: Match confidence from 0.0 to 1.0
        matched_tags: List of tags that contributed to the match
        suggested_at: Timestamp where SFX should be placed (in seconds)
        duration_ms: Duration in milliseconds for subtlety assessment
        subtlety_score: Subtlety rating from 0.0 to 1.0 (higher = more subtle)
    """
    sfx_id: str
    file_path: str
    file_name: str
    folder_context: str
    match_reason: str
    confidence_score: float
    matched_tags: list[str]
    suggested_at: float = 0.0
    duration_ms: int = 0
    subtlety_score: float = 0.5
    
    def __post_init__(self):
        """Validate match fields after initialization."""
        if not self.sfx_id:
            raise ValueError("sfx_id cannot be empty")
        if not self.file_path:
            raise ValueError("file_path cannot be empty")
        if not self.file_name:
            raise ValueError("file_name cannot be empty")
        if self.matched_tags is None:
            self.matched_tags = []
        
        # Validate confidence score range
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(
                f"confidence_score must be between 0.0 and 1.0, got {self.confidence_score}"
            )
        
        # Validate subtlety score range
        if not 0.0 <= self.subtlety_score <= 1.0:
            raise ValueError(
                f"subtlety_score must be between 0.0 and 1.0, got {self.subtlety_score}"
            )
        
        # Validate timestamp
        if self.suggested_at < 0:
            raise ValueError(f"suggested_at cannot be negative: {self.suggested_at}")
        
        # Validate duration
        if self.duration_ms < 0:
            raise ValueError(f"duration_ms cannot be negative: {self.duration_ms}")
    
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
    
    def is_subtle(self) -> bool:
        """Returns True if subtlety_score >= HIGH_SUBTLETY_THRESHOLD.
        
        Returns:
            True if this is a subtle (non-distracting) sound
        """
        return self.subtlety_score >= HIGH_SUBTLETY_THRESHOLD
    
    def format_suggestion(self) -> str:
        """Format as human-readable suggestion string.
        
        Returns formatted string like:
        "SFX: gentle_whoosh.wav at 0:00"
        
        Returns:
            Formatted suggestion string
        """
        minutes = int(self.suggested_at // 60)
        seconds = int(self.suggested_at % 60)
        return f"SFX: {self.file_name} ({minutes}:{seconds:02d})"
    
    def format_match_details(self) -> str:
        """Format detailed match information.
        
        Returns formatted string with match details:
        "Found: gentle_whoosh.wav - Match: 88% (transition, intro)"
        
        Returns:
            Formatted match details string
        """
        confidence_pct = int(self.confidence_score * 100)
        tags_str = ", ".join(self.matched_tags[:3])  # Show top 3 tags
        return f"Found: {self.file_name} - Match: {confidence_pct}% ({tags_str})"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of match
        """
        return {
            "sfx_id": self.sfx_id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "folder_context": self.folder_context,
            "match_reason": self.match_reason,
            "confidence_score": self.confidence_score,
            "matched_tags": self.matched_tags,
            "suggested_at": self.suggested_at,
            "duration_ms": self.duration_ms,
            "subtlety_score": self.subtlety_score
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SFXMatch":
        """Create from dictionary.
        
        Args:
            data: Dictionary with match data
            
        Returns:
            SFXMatch instance
            
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
        
        # Validate timestamp
        try:
            suggested_at = float(data.get("suggested_at", 0.0))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid suggested_at value: {e}")
        
        # Validate duration_ms
        try:
            duration_ms = int(data.get("duration_ms", 0))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid duration_ms value: {e}")
        
        # Validate subtlety_score
        try:
            subtlety_score = float(data.get("subtlety_score", 0.5))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid subtlety_score value: {e}")
        
        # Validate matched_tags
        matched_tags = data.get("matched_tags", [])
        if not isinstance(matched_tags, list):
            raise ValueError(f"matched_tags must be a list, got {type(matched_tags).__name__}")
        
        return cls(
            sfx_id=data.get("sfx_id", ""),
            file_path=data.get("file_path", ""),
            file_name=data.get("file_name", ""),
            folder_context=data.get("folder_context", ""),
            match_reason=data.get("match_reason", ""),
            confidence_score=confidence_score,
            matched_tags=matched_tags,
            suggested_at=suggested_at,
            duration_ms=duration_ms,
            subtlety_score=subtlety_score
        )


@dataclass
class MomentSFXMatches:
    """All SFX matches for a single moment.
    
    Groups all SFX match candidates for a single transcript moment,
    including the moment details and fallback options.
    
    Attributes:
        moment: The SFXMoment this matches belong to
        matches: List of SFX match candidates (sorted by confidence)
        fallback_suggestion: Optional fallback if no good matches
    """
    moment: SFXMoment
    matches: list[SFXMatch]
    fallback_suggestion: SFXMatch | None = None
    
    def __post_init__(self):
        """Validate moment matches after initialization."""
        if self.matches is None:
            self.matches = []
        
        # Sort matches by confidence score (highest first)
        self.matches.sort(key=lambda m: m.confidence_score, reverse=True)
    
    def top_match(self) -> SFXMatch | None:
        """Return highest confidence match.
        
        Returns:
            The SFXMatch with highest confidence, or None if no matches
        """
        if self.matches:
            return self.matches[0]
        return self.fallback_suggestion
    
    def get_high_confidence_matches(self) -> list[SFXMatch]:
        """Return matches with high confidence.
        
        Returns:
            List of matches with confidence >= HIGH_CONFIDENCE_THRESHOLD
        """
        return [m for m in self.matches if m.is_high_confidence()]
    
    def get_subtle_matches(self) -> list[SFXMatch]:
        """Return matches that are subtle/non-distracting.
        
        Returns:
            List of matches with subtlety_score >= HIGH_SUBTLETY_THRESHOLD
        """
        return [m for m in self.matches if m.is_subtle()]
    
    def has_good_matches(self) -> bool:
        """Check if there are any viable matches.
        
        Returns:
            True if there's at least one match with confidence >= LOW_CONFIDENCE_THRESHOLD
        """
        if not self.matches:
            return False
        return any(m.confidence_score >= LOW_CONFIDENCE_THRESHOLD for m in self.matches)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of moment matches
        """
        result = {
            "moment": self.moment.to_dict(),
            "matches": [m.to_dict() for m in self.matches],
            "fallback_suggestion": None
        }
        
        if self.fallback_suggestion:
            result["fallback_suggestion"] = self.fallback_suggestion.to_dict()
        
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MomentSFXMatches":
        """Create from dictionary.
        
        Args:
            data: Dictionary with moment matches data
            
        Returns:
            MomentSFXMatches instance
        """
        if data is None:
            raise ValueError("data cannot be None")
        
        moment = SFXMoment.from_dict(data.get("moment", {}))
        
        matches_data = data.get("matches", [])
        matches = []
        for m_data in matches_data:
            try:
                matches.append(SFXMatch.from_dict(m_data))
            except ValueError:
                continue
        
        fallback = None
        if data.get("fallback_suggestion"):
            try:
                fallback = SFXMatch.from_dict(data["fallback_suggestion"])
            except ValueError:
                pass
        
        return cls(moment=moment, matches=matches, fallback_suggestion=fallback)


@dataclass
class SFXMatchingResult:
    """Result of AI SFX matching operation.
    
    Contains all SFX match results for all moments, including
    statistics, layer guidance, and warnings about the matching process.
    
    Attributes:
        moment_matches: List of moment match results
        total_matches: Total number of SFX matches across all moments
        average_confidence: Average confidence score across all matches
        average_subtlety: Average subtlety score across all matches
        fallback_used: True if any moment used fallback suggestion
        layer_guidance: Guidance for timeline placement
        warnings: List of non-fatal issues (e.g., low confidence, no matches)
    """
    moment_matches: list[MomentSFXMatches]
    total_matches: int
    average_confidence: float
    average_subtlety: float
    fallback_used: bool
    layer_guidance: str
    warnings: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate result after initialization."""
        if self.moment_matches is None:
            self.moment_matches = []
        if self.warnings is None:
            self.warnings = []
        
        # Recalculate total_matches if not provided correctly
        expected_total = sum(len(mm.matches) for mm in self.moment_matches)
        if self.total_matches != expected_total:
            self.total_matches = expected_total
        
        # Recalculate averages if not provided correctly
        all_confidences = [
            m.confidence_score 
            for mm in self.moment_matches 
            for m in mm.matches
        ]
        all_subtleties = [
            m.subtlety_score 
            for mm in self.moment_matches 
            for m in mm.matches
        ]
        
        if all_confidences:
            self.average_confidence = sum(all_confidences) / len(all_confidences)
        else:
            self.average_confidence = 0.0
        
        if all_subtleties:
            self.average_subtlety = sum(all_subtleties) / len(all_subtleties)
        else:
            self.average_subtlety = 0.0
    
    def get_all_matches(self) -> list[SFXMatch]:
        """Get all SFX matches across all moments.
        
        Returns:
            Flat list of all SFXMatch instances
        """
        return [
            match 
            for mm in self.moment_matches 
            for match in mm.matches
        ]
    
    def get_low_confidence_warnings(self) -> list[str]:
        """Get warnings for low-confidence moments.
        
        Returns:
            List of warning strings for moments with poor matches
        """
        warnings = []
        for mm in self.moment_matches:
            if not mm.has_good_matches() and mm.moment.segment_name:
                warnings.append(
                    f"Low confidence matches for moment at {mm.moment.format_timestamp()}"
                )
        return warnings
    
    def get_used_sfx_ids(self) -> set[str]:
        """Get set of all SFX IDs used in matches.
        
        Useful for preventing duplicate suggestions across moments
        and tracking asset usage.
        
        Returns:
            Set of sfx_id strings
        """
        used_ids = set()
        for mm in self.moment_matches:
            for match in mm.matches:
                used_ids.add(match.sfx_id)
            if mm.fallback_suggestion:
                used_ids.add(mm.fallback_suggestion.sfx_id)
        return used_ids
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of result
        """
        return {
            "moment_matches": [mm.to_dict() for mm in self.moment_matches],
            "total_matches": self.total_matches,
            "average_confidence": self.average_confidence,
            "average_subtlety": self.average_subtlety,
            "fallback_used": self.fallback_used,
            "layer_guidance": self.layer_guidance,
            "warnings": self.warnings
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SFXMatchingResult":
        """Create from dictionary.
        
        Args:
            data: Dictionary with result data
            
        Returns:
            SFXMatchingResult instance
        """
        if data is None:
            return cls(
                moment_matches=[],
                total_matches=0,
                average_confidence=0.0,
                average_subtlety=0.0,
                fallback_used=False,
                layer_guidance=""
            )
        
        moments_data = data.get("moment_matches", [])
        moment_matches = []
        for mm_data in moments_data:
            try:
                moment_matches.append(MomentSFXMatches.from_dict(mm_data))
            except ValueError:
                continue
        
        return cls(
            moment_matches=moment_matches,
            total_matches=data.get("total_matches", 0),
            average_confidence=data.get("average_confidence", 0.0),
            average_subtlety=data.get("average_subtlety", 0.0),
            fallback_used=data.get("fallback_used", False),
            layer_guidance=data.get("layer_guidance", ""),
            warnings=data.get("warnings", [])
        )
