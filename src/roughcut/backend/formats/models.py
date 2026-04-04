"""Format template data models including AssetGroup definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional


class AssetGroupCategory(Enum):
    """Category of assets for type-appropriate matching."""

    MUSIC = "music"
    SFX = "sfx"
    VFX = "vfx"
    TRANSITION = "transition"


class AssetGroupPriority(Enum):
    """Priority levels for asset group matching."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DurationHint:
    """Flexible duration specification for asset groups."""

    def __init__(
        self,
        exact: Optional[str] = None,
        min_duration: Optional[str] = None,
        max_duration: Optional[str] = None,
        flexible: bool = True,
    ):
        self.exact = self._parse_duration(exact) if exact else None
        self.min = self._parse_duration(min_duration) if min_duration else None
        self.max = self._parse_duration(max_duration) if max_duration else None
        self.flexible = flexible

    @staticmethod
    def _parse_duration(dur: str) -> int:
        """Parse mm:ss or seconds to total seconds."""
        if not dur or not isinstance(dur, str):
            raise ValueError("Duration must be a non-empty string")
        
        dur = dur.strip()
        
        if ":" in dur:
            parts = dur.split(":")
            if len(parts) != 2:
                raise ValueError(f"Invalid duration format '{dur}'. Use 'mm:ss' format.")
            try:
                minutes = int(parts[0])
                seconds = int(parts[1])
            except ValueError:
                raise ValueError(f"Invalid duration format '{dur}'. Minutes and seconds must be numeric.")
            if minutes < 0 or seconds < 0 or seconds >= 60:
                raise ValueError(f"Invalid duration '{dur}'. Minutes and seconds must be non-negative, seconds < 60.")
            return minutes * 60 + seconds
        
        # Seconds only format
        try:
            seconds = int(dur)
        except ValueError:
            raise ValueError(f"Invalid duration format '{dur}'. Use seconds or 'mm:ss' format.")
        if seconds < 0:
            raise ValueError(f"Duration cannot be negative: {dur}")
        return seconds

    def to_dict(self) -> dict[str, Any]:
        """Serialize duration hint to dictionary."""
        return {
            "exact": self.exact,
            "min": self.min,
            "max": self.max,
            "flexible": self.flexible,
        }


@dataclass
class AssetGroup:
    """
    Defines a group of assets needed for a specific template moment.

    Example: intro_music needs upbeat corporate music for 15 seconds
    """

    name: str  # Unique identifier: "intro_music"
    description: str  # Human-readable: "Upbeat attention grabber"
    category: AssetGroupCategory  # MUSIC, SFX, VFX, TRANSITION

    # Tag matching criteria
    required_tags: List[str] = field(default_factory=list)  # Must have ALL
    optional_tags: List[str] = field(default_factory=list)  # Nice to have ANY

    # Duration constraints
    duration_hint: Optional[DurationHint] = None

    # Matching preferences
    priority: AssetGroupPriority = field(default=AssetGroupPriority.MEDIUM)
    fallback_groups: List[str] = field(default_factory=list)  # If no matches

    def __post_init__(self) -> None:
        """Validate asset group on creation."""
        if not self.name or not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Asset group name is required and must be a string")

        if not self.description or not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("Asset group description is required and must be a string")

        if not isinstance(self.category, AssetGroupCategory):
            raise ValueError(f"Invalid category: {self.category}. Must be AssetGroupCategory enum.")
        
        # Convert string priority to enum if needed
        if isinstance(self.priority, str):
            try:
                self.priority = AssetGroupPriority(self.priority.lower())
            except ValueError:
                valid = [p.value for p in AssetGroupPriority]
                raise ValueError(f"Invalid priority '{self.priority}'. Valid values: {valid}")
        elif not isinstance(self.priority, AssetGroupPriority):
            raise ValueError(f"Invalid priority type: {type(self.priority)}. Must be str or AssetGroupPriority.")

        if not self.required_tags and not self.optional_tags:
            raise ValueError("At least one tag required (required or optional)")

        # Normalize tags to lowercase and filter empty
        self.required_tags = [str(t).lower().strip() for t in self.required_tags if t is not None and str(t).strip()]
        self.optional_tags = [str(t).lower().strip() for t in self.optional_tags if t is not None and str(t).strip()]
        
        # Validate we still have at least one tag after filtering
        if not self.required_tags and not self.optional_tags:
            raise ValueError("At least one non-empty tag required (required or optional)")

    def matches_asset(self, asset_tags: List[str]) -> float:
        """
        Calculate match score for this group against asset tags.
        
        Scoring algorithm per spec:
        - Exact match (all required tags present): 100% = 1.0
        - Partial match (some required tags present): 50% = 0.5
        - No match (no required tags present): 0% = 0.0
        
        Optional tags are considered only when calculating partial match score
        within the 50% band (no optional = 0.5, all optional = 1.0).

        Returns:
            Score 0.0-1.0 where 1.0 = perfect match
        """
        # Handle None input gracefully
        if asset_tags is None:
            return 0.0
            
        asset_tags_set = {str(t).lower() for t in asset_tags if t is not None}
        
        if not self.required_tags:
            # No required tags means any asset is a candidate
            # Score based only on optional tags (0.5 to 1.0 range)
            if not self.optional_tags:
                return 1.0  # No criteria = perfect match
            optional_matches = sum(1 for o in self.optional_tags if o in asset_tags_set)
            optional_ratio = optional_matches / len(self.optional_tags)
            return 0.5 + (0.5 * optional_ratio)
        
        # Count required tag matches
        required_matches = sum(1 for r in self.required_tags if r in asset_tags_set)
        required_ratio = required_matches / len(self.required_tags)
        
        if required_ratio == 1.0:
            # All required tags match - exact match (100% base)
            # Optional tags can boost within the upper 50% band (0.5 to 1.0)
            if not self.optional_tags:
                return 1.0
            optional_matches = sum(1 for o in self.optional_tags if o in asset_tags_set)
            optional_ratio = optional_matches / len(self.optional_tags)
            return 0.5 + (0.5 * optional_ratio)
        elif required_ratio > 0:
            # Some required tags match - partial match (50% base)
            # Scale within lower 50% band based on required tag coverage
            return 0.5 * required_ratio
        else:
            # No required tags match - no match (0%)
            return 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize for protocol responses."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "required_tags": self.required_tags,
            "optional_tags": self.optional_tags,
            "duration_hint": self.duration_hint.to_dict() if self.duration_hint else None,
            "priority": self.priority.value if isinstance(self.priority, AssetGroupPriority) else str(self.priority),
            "fallback_groups": self.fallback_groups,
        }


class AssetGroupParseError(Exception):
    """Exception raised when parsing asset group YAML fails."""

    pass
