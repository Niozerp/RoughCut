"""VFX matching data structures for AI asset matching.

Provides dataclasses for representing VFX matches, including match scoring,
confidence levels, placement data, and template group membership for visual
effect template selection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .vfx_requirement import VFXRequirement


#: Confidence threshold for high-confidence VFX matches
HIGH_CONFIDENCE_THRESHOLD = 0.85
#: Confidence threshold for low-confidence VFX matches
LOW_CONFIDENCE_THRESHOLD = 0.60
#: Minimum acceptable confidence for viable matches
MIN_CONFIDENCE_THRESHOLD = 0.50


@dataclass
class VFXPlacement:
    """Calculated placement for a VFX template on timeline.
    
    Represents the exact timing where a VFX template should be positioned,
    including start time, end time, and duration in milliseconds.
    
    Attributes:
        start_time: Start timestamp in seconds
        end_time: End timestamp in seconds
        duration_ms: Duration in milliseconds
    """
    start_time: float
    end_time: float
    duration_ms: int
    
    def __post_init__(self):
        """Validate placement fields after initialization."""
        if self.start_time < 0:
            raise ValueError(f"start_time cannot be negative: {self.start_time}")
        if self.end_time < self.start_time:
            raise ValueError(
                f"end_time ({self.end_time}) must be >= start_time ({self.start_time})"
            )
        if self.duration_ms < 0:
            raise ValueError(f"duration_ms cannot be negative: {self.duration_ms}")
    
    def overlaps_with(self, other: VFXPlacement, tolerance: float = 0.1) -> bool:
        """Check if this placement overlaps with another.
        
        Args:
            other: Another VFXPlacement to check against
            tolerance: Time tolerance in seconds for overlap detection
            
        Returns:
            True if placements overlap within tolerance
        """
        # Check for overlap: intervals overlap if they share any time period
        # Two intervals [a, b] and [c, d] overlap if max(a,c) < min(b,d)
        # This means they actually share time, not just touch at boundaries
        
        # Check if there's an actual time overlap (not just adjacency)
        latest_start = max(self.start_time, other.start_time)
        earliest_end = min(self.end_time, other.end_time)
        
        # Overlap exists if latest_start < earliest_end (strict inequality)
        # Equal values mean adjacent, not overlapping
        if latest_start < earliest_end:
            return True
        
        # Check if within tolerance for near-overlap detection
        gap = latest_start - earliest_end  # Positive if there's a gap
        return 0 < gap <= tolerance
    
    def get_overlap_duration(self, other: VFXPlacement) -> float:
        """Calculate overlap duration with another placement.
        
        Args:
            other: Another VFXPlacement to calculate overlap with
            
        Returns:
            Overlap duration in seconds (0 if no overlap)
        """
        if not self.overlaps_with(other):
            return 0.0
        
        overlap_start = max(self.start_time, other.start_time)
        overlap_end = min(self.end_time, other.end_time)
        return max(0.0, overlap_end - overlap_start)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of placement
        """
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VFXPlacement":
        """Create from dictionary.
        
        Args:
            data: Dictionary with placement data
            
        Returns:
            VFXPlacement instance
            
        Raises:
            ValueError: If data is None, not a dict, or has invalid field types
        """
        if data is None:
            raise ValueError("data cannot be None")
        if not isinstance(data, dict):
            raise ValueError(f"data must be a dictionary, got {type(data).__name__}")
        
        # Validate timestamps
        try:
            start_time = float(data.get("start_time", 0.0))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid start_time value: {e}")
        
        try:
            end_time = float(data.get("end_time", 0.0))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid end_time value: {e}")
        
        try:
            duration_ms = int(data.get("duration_ms", 0))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid duration_ms value: {e}")
        
        return cls(
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms
        )


@dataclass
class VFXAsset:
    """Represents a VFX/template asset from the indexed library.
    
    Simplified representation of a visual effect template for matching purposes.
    Contains only metadata needed for matching, not full file data.
    
    Attributes:
        vfx_id: Unique identifier for the asset
        file_path: Absolute path to the VFX template file
        tags: AI-generated tags for the asset
        category: Asset category (always "vfx" for this class)
        folder_context: Parent folder path for context matching
        duration_ms: Duration in milliseconds (0 if unknown)
        template_type: Type of template (fusion_composition, generator, transition)
    """
    vfx_id: str
    file_path: str
    tags: list[str]
    category: str = "vfx"
    folder_context: str = ""
    duration_ms: int = 0
    template_type: str = "fusion_composition"
    
    def __post_init__(self):
        """Validate asset fields after initialization."""
        if not self.vfx_id:
            raise ValueError("vfx_id cannot be empty")
        if not self.file_path:
            raise ValueError("file_path cannot be empty")
        # Check for None first, then validate type
        if self.tags is None:
            self.tags = []
        if not isinstance(self.tags, list):
            raise ValueError(f"tags must be a list, got {type(self.tags).__name__}")
        if self.duration_ms < 0:
            raise ValueError(f"duration_ms cannot be negative: {self.duration_ms}")
        
        valid_template_types = ["fusion_composition", "generator", "transition"]
        if self.template_type not in valid_template_types:
            raise ValueError(
                f"template_type must be one of {valid_template_types}, got: {self.template_type}"
            )
    
    def get_file_name(self) -> str:
        """Extract filename from file path.
        
        Returns:
            Filename without directory path
        """
        import os
        return os.path.basename(self.file_path)
    
    def matches_template_type_preference(self, preferred_types: list[str]) -> bool:
        """Check if this asset matches preferred template types.
        
        Args:
            preferred_types: List of preferred template type strings
            
        Returns:
            True if this asset's template_type is in preferred_types
        """
        return self.template_type in preferred_types
    
    def has_tag(self, tag: str) -> bool:
        """Check if asset has a specific tag (case-insensitive).
        
        Args:
            tag: Tag to check for
            
        Returns:
            True if asset has the tag
        """
        tag_lower = tag.casefold()
        return any(t.casefold() == tag_lower for t in self.tags)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VFXAsset":
        """Create from dictionary.
        
        Args:
            data: Dictionary with asset data
            
        Returns:
            VFXAsset instance
            
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
            vfx_id=data.get("id", ""),
            file_path=data.get("file_path", ""),
            tags=tags,
            category=data.get("category", "vfx"),
            folder_context=data.get("folder_context", ""),
            duration_ms=duration_ms,
            template_type=data.get("template_type", "fusion_composition")
        )


@dataclass
class VFXMatch:
    """A VFX/template asset matched to a requirement.
    
    Represents a successful match between a VFX requirement and
    a template from the indexed library. Includes confidence
    scoring, placement data, and template group membership.
    
    Attributes:
        vfx_id: Unique identifier for the matched asset
        file_path: Absolute path to the VFX template file
        file_name: Filename without directory path
        folder_context: Parent folder path for context
        match_reason: Human-readable explanation of why this match was selected
        confidence_score: Match confidence from 0.0 to 1.0
        matched_tags: List of tags that contributed to the match
        template_type: Type of template (fusion_composition, generator, transition)
        placement: Calculated VFXPlacement for timeline positioning
        from_template_group: True if from predefined asset group
        group_name: Name of template asset group if applicable
    """
    vfx_id: str
    file_path: str
    file_name: str
    folder_context: str
    match_reason: str
    confidence_score: float
    matched_tags: list[str]
    template_type: str
    placement: VFXPlacement
    from_template_group: bool = False
    group_name: Optional[str] = None
    
    def __post_init__(self):
        """Validate match fields after initialization."""
        if not self.vfx_id:
            raise ValueError("vfx_id cannot be empty")
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
        
        # Validate template type
        valid_template_types = ["fusion_composition", "generator", "transition"]
        if self.template_type not in valid_template_types:
            raise ValueError(
                f"template_type must be one of {valid_template_types}, got: {self.template_type}"
            )
    
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
    
    def is_viable(self) -> bool:
        """Returns True if confidence >= MIN_CONFIDENCE_THRESHOLD.
        
        Returns:
            True if this match is viable for use
        """
        return self.confidence_score >= MIN_CONFIDENCE_THRESHOLD
    
    def format_suggestion(self) -> str:
        """Format as human-readable suggestion string.
        
        Returns formatted string like:
        "VFX: standard_lower_third.drp at 2:00"
        
        Returns:
            Formatted suggestion string
        """
        minutes = int(self.placement.start_time // 60)
        seconds = int(self.placement.start_time % 60)
        return f"VFX: {self.file_name} ({minutes}:{seconds:02d})"
    
    def format_match_details(self) -> str:
        """Format detailed match information.
        
        Returns formatted string with match details:
        "Found: standard_lower_third.drp - Match: 92% (lower_third, corporate)"
        
        Returns:
            Formatted match details string
        """
        confidence_pct = int(self.confidence_score * 100)
        tags_str = ", ".join(self.matched_tags[:3])  # Show top 3 tags
        group_info = f" [{self.group_name}]" if self.from_template_group and self.group_name else ""
        return f"Found: {self.file_name}{group_info} - Match: {confidence_pct}% ({tags_str})"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of match
        """
        return {
            "vfx_id": self.vfx_id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "folder_context": self.folder_context,
            "match_reason": self.match_reason,
            "confidence_score": self.confidence_score,
            "matched_tags": self.matched_tags,
            "template_type": self.template_type,
            "placement": self.placement.to_dict(),
            "from_template_group": self.from_template_group,
            "group_name": self.group_name
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VFXMatch":
        """Create from dictionary.
        
        Args:
            data: Dictionary with match data
            
        Returns:
            VFXMatch instance
            
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
        
        # Validate matched_tags
        matched_tags = data.get("matched_tags", [])
        if not isinstance(matched_tags, list):
            raise ValueError(f"matched_tags must be a list, got {type(matched_tags).__name__}")
        
        # Parse placement
        placement_data = data.get("placement", {})
        try:
            placement = VFXPlacement.from_dict(placement_data)
        except ValueError as e:
            raise ValueError(f"Invalid placement data: {e}")
        
        return cls(
            vfx_id=data.get("vfx_id", ""),
            file_path=data.get("file_path", ""),
            file_name=data.get("file_name", ""),
            folder_context=data.get("folder_context", ""),
            match_reason=data.get("match_reason", ""),
            confidence_score=confidence_score,
            matched_tags=matched_tags,
            template_type=data.get("template_type", "fusion_composition"),
            placement=placement,
            from_template_group=data.get("from_template_group", False),
            group_name=data.get("group_name")
        )


@dataclass
class RequirementVFXMatches:
    """All VFX matches for a single requirement.
    
    Groups all VFX match candidates for a single requirement,
    including the requirement details and fallback options.
    
    Attributes:
        requirement: The VFXRequirement this matches belong to
        matches: List of VFX match candidates (sorted by confidence)
        fallback_suggestion: Optional fallback if no good matches
    """
    requirement: VFXRequirement
    matches: list[VFXMatch]
    fallback_suggestion: Optional[VFXMatch] = None
    
    def __post_init__(self):
        """Validate requirement matches after initialization."""
        if self.matches is None:
            self.matches = []
        
        # Sort matches by confidence score (highest first)
        self.matches.sort(key=lambda m: m.confidence_score, reverse=True)
    
    def top_match(self) -> Optional[VFXMatch]:
        """Return highest confidence match.
        
        Returns:
            The VFXMatch with highest confidence, or None if no matches
        """
        if self.matches:
            return self.matches[0]
        return self.fallback_suggestion
    
    def get_high_confidence_matches(self) -> list[VFXMatch]:
        """Return matches with high confidence.
        
        Returns:
            List of matches with confidence >= HIGH_CONFIDENCE_THRESHOLD
        """
        return [m for m in self.matches if m.is_high_confidence()]
    
    def get_viable_matches(self) -> list[VFXMatch]:
        """Return matches that are viable for use.
        
        Returns:
            List of matches with confidence >= MIN_CONFIDENCE_THRESHOLD
        """
        return [m for m in self.matches if m.is_viable()]
    
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
            Dictionary representation of requirement matches
        """
        result = {
            "requirement": self.requirement.to_dict(),
            "matches": [m.to_dict() for m in self.matches],
            "fallback_suggestion": None
        }
        
        if self.fallback_suggestion:
            result["fallback_suggestion"] = self.fallback_suggestion.to_dict()
        
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RequirementVFXMatches":
        """Create from dictionary.
        
        Args:
            data: Dictionary with requirement matches data
            
        Returns:
            RequirementVFXMatches instance
            
        Raises:
            ValueError: If data is None or requirement cannot be parsed
        """
        if data is None:
            raise ValueError("data cannot be None")
        
        # Parse requirement
        req_data = data.get("requirement", {})
        try:
            requirement = VFXRequirement.from_dict(req_data)
        except ValueError as e:
            raise ValueError(f"Invalid requirement data: {e}")
        
        # Parse matches
        matches_data = data.get("matches", [])
        matches = []
        for m_data in matches_data:
            try:
                matches.append(VFXMatch.from_dict(m_data))
            except ValueError:
                continue
        
        # Parse fallback
        fallback = None
        if data.get("fallback_suggestion"):
            try:
                fallback = VFXMatch.from_dict(data["fallback_suggestion"])
            except ValueError:
                pass
        
        return cls(requirement=requirement, matches=matches, fallback_suggestion=fallback)


@dataclass
class VFXMatchingResult:
    """Result of AI VFX matching operation.
    
    Contains all VFX match results for all requirements, including
    statistics, placement conflicts, template group coverage, and warnings.
    
    Attributes:
        requirement_matches: List of requirement match results
        total_matches: Total number of VFX matches across all requirements
        average_confidence: Average confidence score across all matches
        fallback_used: True if any requirement used fallback suggestion
        placement_conflicts: List of overlapping placement conflicts detected
        template_group_coverage: Percentage of matches from predefined groups (0.0 to 1.0)
        warnings: List of non-fatal issues (e.g., low confidence, no matches)
    """
    requirement_matches: list[RequirementVFXMatches]
    total_matches: int
    average_confidence: float
    fallback_used: bool
    placement_conflicts: list[dict[str, Any]]
    template_group_coverage: float
    warnings: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate result after initialization."""
        if self.requirement_matches is None:
            self.requirement_matches = []
        if self.placement_conflicts is None:
            self.placement_conflicts = []
        if self.warnings is None:
            self.warnings = []
        
        # Recalculate total_matches if not provided correctly
        expected_total = sum(len(rm.matches) for rm in self.requirement_matches)
        if self.total_matches != expected_total:
            self.total_matches = expected_total
        
        # Recalculate average confidence if not provided correctly
        all_confidences = [
            m.confidence_score 
            for rm in self.requirement_matches 
            for m in rm.matches
        ]
        
        if all_confidences:
            self.average_confidence = sum(all_confidences) / len(all_confidences)
        else:
            self.average_confidence = 0.0
    
    def get_all_matches(self) -> list[VFXMatch]:
        """Get all VFX matches across all requirements.
        
        Returns:
            Flat list of all VFXMatch instances
        """
        return [
            match 
            for rm in self.requirement_matches 
            for match in rm.matches
        ]
    
    def get_low_confidence_warnings(self) -> list[str]:
        """Get warnings for low-confidence requirements.
        
        Returns:
            List of warning strings for requirements with poor matches
        """
        warnings = []
        for rm in self.requirement_matches:
            if not rm.has_good_matches() and rm.requirement.format_section:
                warnings.append(
                    f"Low confidence matches for requirement at {rm.requirement.format_timestamp()}"
                )
        return warnings
    
    def get_used_vfx_ids(self) -> set[str]:
        """Get set of all VFX IDs used in matches.
        
        Useful for preventing duplicate suggestions across requirements
        and tracking asset usage.
        
        Returns:
            Set of vfx_id strings
        """
        used_ids = set()
        for rm in self.requirement_matches:
            for match in rm.matches:
                used_ids.add(match.vfx_id)
            if rm.fallback_suggestion:
                used_ids.add(rm.fallback_suggestion.vfx_id)
        return used_ids
    
    def get_matches_by_type(self, req_type: str) -> list[VFXMatch]:
        """Get all matches for a specific requirement type.
        
        Args:
            req_type: Requirement type to filter by (e.g., "lower_third")
            
        Returns:
            List of VFXMatch instances for that requirement type
        """
        matches = []
        for rm in self.requirement_matches:
            if rm.requirement.type == req_type:
                matches.extend(rm.matches)
        return matches
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of result
        """
        return {
            "requirement_matches": [rm.to_dict() for rm in self.requirement_matches],
            "total_matches": self.total_matches,
            "average_confidence": self.average_confidence,
            "fallback_used": self.fallback_used,
            "placement_conflicts": self.placement_conflicts,
            "template_group_coverage": self.template_group_coverage,
            "warnings": self.warnings
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VFXMatchingResult":
        """Create from dictionary.
        
        Args:
            data: Dictionary with result data
            
        Returns:
            VFXMatchingResult instance
        """
        if data is None:
            return cls(
                requirement_matches=[],
                total_matches=0,
                average_confidence=0.0,
                fallback_used=False,
                placement_conflicts=[],
                template_group_coverage=0.0,
                warnings=[]
            )
        
        reqs_data = data.get("requirement_matches", [])
        requirement_matches = []
        for rm_data in reqs_data:
            try:
                requirement_matches.append(RequirementVFXMatches.from_dict(rm_data))
            except ValueError:
                continue
        
        return cls(
            requirement_matches=requirement_matches,
            total_matches=data.get("total_matches", 0),
            average_confidence=data.get("average_confidence", 0.0),
            fallback_used=data.get("fallback_used", False),
            placement_conflicts=data.get("placement_conflicts", []),
            template_group_coverage=data.get("template_group_coverage", 0.0),
            warnings=data.get("warnings", [])
        )
