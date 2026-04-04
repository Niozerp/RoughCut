"""Data models for format templates.

Defines the FormatTemplate dataclass and related structures for
template metadata management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional, Union


class RuleType(Enum):
    """Type of format rule for cutting behavior."""
    CUTTING = "cutting"           # How to cut transcript
    TRANSITION = "transition"     # Transition rules between segments
    TIMING = "timing"            # Overall timing constraints
    PACING = "pacing"            # Pacing guidelines


class MatchingCriteriaType(Enum):
    """Type of media matching criteria."""
    EMOTION_MATCH = "emotion_match"      # Match asset emotion to transcript tone
    CONTEXT_MATCH = "context_match"      # Match asset context to segment context
    TONE_MATCH = "tone_match"            # Match tone (music tempo, SFX intensity)
    TEMPO_MATCH = "tempo_match"          # Match tempo to pacing
    KEYWORD_MATCH = "keyword_match"      # Match specific keywords/tags


@dataclass
class TemplateSegment:
    """Represents a timing segment in a format template.
    
    Attributes:
        name: Segment name (e.g., "Hook", "Narrative", "Outro")
        start_time: Start time in format "M:SS" or "H:MM:SS"
        end_time: End time in format "M:SS" or "H:MM:SS"
        duration: Human-readable duration (e.g., "15 seconds", "3 minutes")
        purpose: Description of the segment's purpose
    """
    
    name: str
    start_time: str
    end_time: str
    duration: str
    purpose: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert segment to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "purpose": self.purpose
        }


@dataclass
class AssetGroup:
    """Represents an asset group definition in a format template.
    
    Attributes:
        category: Asset category (e.g., "Music", "SFX", "VFX")
        name: Asset identifier (e.g., "intro_music", "outro_chime")
        description: Description of the asset and its use
        search_tags: Optional list of search tags for finding matching assets
    """
    
    category: str
    name: str
    description: str
    search_tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert asset group to dictionary for JSON serialization."""
        return {
            "category": self.category,
            "name": self.name,
            "description": self.description,
            "search_tags": self.search_tags
        }


@dataclass
class TimingConstraint:
    """Flexible timing specification for format rules.
    
    Attributes:
        min_duration: Minimum duration in seconds
        max_duration: Maximum duration in seconds
        exact_duration: Exact duration in seconds (overrides min/max)
        flexible: Whether timing is flexible
    """
    
    min_duration: Optional[int] = None
    max_duration: Optional[int] = None
    exact_duration: Optional[int] = None
    flexible: bool = True
    
    def __post_init__(self):
        """Validate timing constraints are logical."""
        if self.exact_duration is not None:
            if self.exact_duration < 0:
                raise ValueError("exact_duration must be >= 0")
            self.min_duration = self.max_duration = self.exact_duration
            self.flexible = False
        
        if self.min_duration is not None and self.min_duration < 0:
            raise ValueError("min_duration must be >= 0")
        
        if self.max_duration is not None and self.max_duration < 0:
            raise ValueError("max_duration must be >= 0")
        
        if (self.min_duration is not None and 
            self.max_duration is not None and 
            self.min_duration > self.max_duration):
            raise ValueError(
                f"min_duration ({self.min_duration}) > max_duration ({self.max_duration})"
            )
    
    @classmethod
    def from_string(cls, duration_str: str) -> "TimingConstraint":
        """Parse duration string like '0:15', '15', '4:00', '2:30-5:00'."""
        if not duration_str or not isinstance(duration_str, str):
            return cls(flexible=True)
        
        duration_str = duration_str.strip()
        
        if "-" in duration_str:
            parts = duration_str.split("-")
            return cls(
                min_duration=cls._parse_single(parts[0].strip()),
                max_duration=cls._parse_single(parts[1].strip()),
                flexible=True
            )
        
        seconds = cls._parse_single(duration_str)
        return cls(exact_duration=seconds, flexible=False)
    
    @staticmethod
    def _parse_single(dur: str) -> int:
        """Parse mm:ss or seconds to total seconds."""
        dur = dur.strip()
        
        # Reject non-numeric characters except colon
        if not all(c.isdigit() or c == ':' for c in dur):
            raise ValueError(f"Duration must be numeric (e.g., '15' or '2:30'), got: {dur}")
        
        if ":" in dur:
            parts = dur.split(":")
            if len(parts) != 2:
                raise ValueError(f"Invalid duration format: {dur}. Use mm:ss")
            try:
                minutes = int(parts[0])
                seconds = int(parts[1])
            except ValueError:
                raise ValueError(f"Duration parts must be integers, got: {dur}")
            
            # Validate seconds < 60 in mm:ss format
            if seconds >= 60:
                raise ValueError(f"Seconds must be < 60 in mm:ss format: {dur}")
            
            return minutes * 60 + seconds
        
        # Simple seconds format
        try:
            return int(dur)
        except ValueError:
            raise ValueError(f"Duration must be an integer, got: {dur}")
    
    def to_dict(self) -> dict:
        """Serialize for protocol responses."""
        return {
            'min_duration': self.min_duration,
            'max_duration': self.max_duration,
            'exact_duration': self.exact_duration,
            'flexible': self.flexible,
            'formatted': self.format_for_display()
        }
    
    def format_for_display(self) -> str:
        """Human-readable format: '15 seconds', '2:30-5:00', 'exactly 4:00'."""
        if self.exact_duration is not None:
            return f"exactly {self._format_seconds(self.exact_duration)}"
        elif self.min_duration is not None and self.max_duration is not None:
            return f"{self._format_seconds(self.min_duration)}-{self._format_seconds(self.max_duration)}"
        elif self.min_duration is not None:
            return f"at least {self._format_seconds(self.min_duration)}"
        elif self.max_duration is not None:
            return f"at most {self._format_seconds(self.max_duration)}"
        return "flexible"
    
    @staticmethod
    def _format_seconds(seconds: int) -> str:
        """Format seconds as mm:ss or just seconds."""
        if seconds < 60:
            return f"{seconds}s"
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"


@dataclass
class SegmentStructure:
    """Defines how transcript should be segmented.
    
    Attributes:
        segment_count: Number of segments to create
        segment_descriptions: Descriptions for each segment
        segment_order: Order of segments (sequential, parallel, priority_based)
    """
    
    segment_count: int
    segment_descriptions: List[str] = field(default_factory=list)
    segment_order: str = "sequential"
    
    def __post_init__(self):
        """Validate segment structure."""
        if self.segment_count <= 0:
            raise ValueError("segment_count must be > 0")
        
        if len(self.segment_descriptions) > self.segment_count:
            raise ValueError(
                f"More descriptions ({len(self.segment_descriptions)}) "
                f"than segments ({self.segment_count})"
            )
        
        valid_orders = ["sequential", "parallel", "priority_based"]
        if self.segment_order not in valid_orders:
            raise ValueError(
                f"Invalid segment_order: {self.segment_order}. "
                f"Must be one of: {valid_orders}"
            )
    
    def to_dict(self) -> dict:
        return {
            'segment_count': self.segment_count,
            'segment_descriptions': self.segment_descriptions,
            'segment_order': self.segment_order
        }


@dataclass
class TransitionRule:
    """Defines transitions between segments.
    
    Attributes:
        from_segment: Source segment index (None = from start)
        to_segment: Target segment index (None = to end)
        transition_type: Type of transition (cut, dissolve, fade, wipe)
        duration: Duration in seconds
        style: Style of transition
    """
    
    from_segment: Optional[int] = None
    to_segment: Optional[int] = None
    transition_type: str = "cut"
    duration: Optional[float] = None
    style: str = "standard"
    
    def __post_init__(self):
        """Validate transition rule."""
        valid_types = ["cut", "dissolve", "fade", "wipe"]
        if self.transition_type not in valid_types:
            raise ValueError(
                f"Invalid transition_type: {self.transition_type}. "
                f"Must be one of: {valid_types}"
            )
        
        if self.duration is not None and self.duration < 0:
            raise ValueError("duration must be >= 0")
    
    def to_dict(self) -> dict:
        return {
            'from_segment': self.from_segment,
            'to_segment': self.to_segment,
            'transition_type': self.transition_type,
            'duration': self.duration,
            'style': self.style
        }


@dataclass
class FormatRule:
    """Defines a cutting rule for the format template.
    
    Example: Cut transcript to 3 key narrative beats, ~4 minutes total
    
    Attributes:
        rule_type: Type of rule (CUTTING, TRANSITION, TIMING, PACING)
        description: Human-readable description
        timing_constraint: Optional timing constraints
        segment_structure: Optional segment structure (for cutting rules)
        transitions: List of transition rules
        strict_mode: Whether AI must follow exactly
        priority: Priority for conflict resolution (higher = more important)
        fallback_rules: Names of fallback rules if this fails
    """
    
    rule_type: RuleType
    description: str
    timing_constraint: Optional[TimingConstraint] = None
    segment_structure: Optional[SegmentStructure] = None
    transitions: List[TransitionRule] = field(default_factory=list)
    strict_mode: bool = True
    priority: int = 1
    fallback_rules: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate format rule on creation."""
        if not isinstance(self.rule_type, RuleType):
            raise ValueError(
                f"rule_type must be RuleType enum, got {type(self.rule_type)}"
            )
        
        if not self.description or not self.description.strip():
            raise ValueError("description is required")
        
        # Validate rule_type-specific requirements
        if self.rule_type == RuleType.CUTTING and self.segment_structure is None:
            raise ValueError("CUTTING rules require segment_structure")
        
        if self.priority < 1:
            raise ValueError("priority must be >= 1")
    
    def to_dict(self) -> dict:
        """Serialize for protocol responses."""
        return {
            'rule_type': self.rule_type.value,
            'description': self.description,
            'timing_constraint': (
                self.timing_constraint.to_dict() if self.timing_constraint else None
            ),
            'segment_structure': (
                self.segment_structure.to_dict() if self.segment_structure else None
            ),
            'transitions': [t.to_dict() for t in self.transitions],
            'strict_mode': self.strict_mode,
            'priority': self.priority,
            'fallback_rules': self.fallback_rules
        }
    
    def format_for_ai(self) -> str:
        """Format this rule as AI-readable instruction."""
        lines = [f"Rule: {self.description}"]
        lines.append(f"Type: {self.rule_type.value}")
        
        if self.timing_constraint:
            lines.append(f"Timing: {self.timing_constraint.format_for_display()}")
        
        if self.segment_structure:
            lines.append(f"Segments: {self.segment_structure.segment_count}")
            for i, desc in enumerate(self.segment_structure.segment_descriptions, 1):
                lines.append(f"  Segment {i}: {desc}")
        
        if self.transitions:
            for t in self.transitions:
                trans_desc = f"Transition: {t.transition_type}"
                if t.duration:
                    trans_desc += f" ({t.duration}s)"
                lines.append(trans_desc)
        
        if self.strict_mode:
            lines.append("Note: This rule must be followed strictly.")
        
        return "\n".join(lines)


@dataclass
class MatchingRule:
    """A single matching condition for media selection.
    
    Attributes:
        attribute: What to match on (emotion, tags, tempo, intensity)
        condition: How to match (equals, contains, greater_than, less_than, matches)
        value: What to match against
        weight: Importance (0.0-1.0) for scoring
    """
    
    attribute: str
    condition: str
    value: Any
    weight: float = 1.0
    
    def __post_init__(self):
        """Validate matching rule."""
        valid_conditions = ["equals", "contains", "greater_than", "less_than", "matches"]
        if self.condition not in valid_conditions:
            raise ValueError(
                f"Invalid condition: {self.condition}. "
                f"Must be one of: {valid_conditions}"
            )
        
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"weight must be between 0.0 and 1.0, got {self.weight}")
    
    def evaluate(self, asset_value: Any) -> bool:
        """Check if asset value matches this rule."""
        if self.condition == "equals":
            return asset_value == self.value
        elif self.condition == "contains":
            if isinstance(asset_value, (list, str)):
                return self.value in asset_value
            return False
        elif self.condition == "greater_than":
            return asset_value > self.value
        elif self.condition == "less_than":
            return asset_value < self.value
        elif self.condition == "matches":
            import re
            return bool(re.search(self.value, str(asset_value)))
        return False
    
    def to_dict(self) -> dict:
        return {
            'attribute': self.attribute,
            'condition': self.condition,
            'value': self.value,
            'weight': self.weight
        }


@dataclass
class MediaMatchingCriteria:
    """Defines criteria for matching media assets to template moments.
    
    Example: Match music emotion to transcript segment tone
    
    Attributes:
        criteria_type: Type of matching (EMOTION_MATCH, CONTEXT_MATCH, etc.)
        target_asset_group: Name of asset group to match against
        description: Human-readable description
        matching_rules: List of matching rules
        ai_guidance: Additional guidance for AI
        priority: Priority for conflict resolution
        required: Whether a match is required
    """
    
    criteria_type: MatchingCriteriaType
    target_asset_group: str
    description: str
    matching_rules: List[MatchingRule] = field(default_factory=list)
    ai_guidance: str = ""
    priority: int = 1
    required: bool = True
    
    def __post_init__(self):
        """Validate media matching criteria."""
        if not isinstance(self.criteria_type, MatchingCriteriaType):
            raise ValueError(
                f"criteria_type must be MatchingCriteriaType enum, "
                f"got {type(self.criteria_type)}"
            )
        
        if not self.target_asset_group or not self.target_asset_group.strip():
            raise ValueError("target_asset_group is required")
        
        if not self.description or not self.description.strip():
            raise ValueError("description is required")
    
    def to_dict(self) -> dict:
        return {
            'criteria_type': self.criteria_type.value,
            'target_asset_group': self.target_asset_group,
            'description': self.description,
            'matching_rules': [r.to_dict() for r in self.matching_rules],
            'ai_guidance': self.ai_guidance,
            'priority': self.priority,
            'required': self.required
        }
    
    def format_for_ai(self) -> str:
        """Format as AI-readable matching instruction."""
        lines = [f"Matching Criteria: {self.description}"]
        lines.append(f"Target: {self.target_asset_group}")
        lines.append(f"Type: {self.criteria_type.value}")
        
        if self.ai_guidance:
            lines.append(f"Guidance: {self.ai_guidance}")
        
        if self.matching_rules:
            lines.append("Rules:")
            for rule in self.matching_rules:
                lines.append(
                    f"  - {rule.attribute} {rule.condition} {rule.value} "
                    f"(weight: {rule.weight})"
                )
        
        if self.required:
            lines.append("Required: Must find matching asset")
        else:
            lines.append("Optional: Use if suitable asset found")
        
        return "\n".join(lines)


@dataclass
class FormatTemplate:
    """Represents a video format template.
    
    Attributes:
        slug: Unique identifier derived from filename (e.g., "youtube-interview")
        name: Display name from frontmatter (e.g., "YouTube Interview — Corporate")
        description: Brief description from frontmatter
        file_path: Absolute path to the markdown template file
        structure: Full structure description text (optional)
        segments: List of timing segments (optional)
        asset_groups: List of asset group definitions (optional)
        format_rules: List of format cutting rules (optional)
        matching_criteria: List of media matching criteria (optional)
        raw_markdown: Full markdown content for display (optional)
    """
    
    slug: str
    name: str
    description: str
    file_path: Path
    structure: str = ""
    segments: List[TemplateSegment] = field(default_factory=list)
    asset_groups: List[AssetGroup] = field(default_factory=list)
    format_rules: List[FormatRule] = field(default_factory=list)
    matching_criteria: List[MediaMatchingCriteria] = field(default_factory=list)
    raw_markdown: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary for JSON serialization.
        
        Returns:
            Dictionary with slug, name, description (excludes file_path)
        """
        return {
            "slug": self.slug,
            "name": self.name,
            "description": self.description
        }
    
    def to_preview_dict(self) -> Dict[str, Any]:
        """Convert template to preview dictionary with full details.
        
        Returns:
            Dictionary with all template details for preview display
        """
        return {
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "structure": self.structure,
            "segments": [s.to_dict() for s in self.segments],
            "asset_groups": [a.to_dict() for a in self.asset_groups],
            "format_rules": [r.to_dict() for r in self.format_rules],
            "matching_criteria": [c.to_dict() for c in self.matching_criteria],
            "formatted_display": self._format_display_text()
        }
    
    def _format_display_text(self) -> str:
        """Generate formatted display text for UI rendering.
        
        Returns:
            Formatted multi-line string with timing and asset information
        """
        lines = []
        
        # Add segments summary
        if self.segments:
            lines.append("=== TIMING ===")
            for seg in self.segments:
                lines.append(f"{seg.name}: {seg.start_time}-{seg.end_time} ({seg.duration})")
            lines.append("")
        
        # Add asset groups summary
        if self.asset_groups:
            lines.append("=== ASSETS ===")
            by_category: Dict[str, List[AssetGroup]] = {}
            for ag in self.asset_groups:
                if not ag.category or not ag.category.strip():
                    continue
                if ag.category not in by_category:
                    by_category[ag.category] = []
                by_category[ag.category].append(ag)
            
            for category in sorted(by_category.keys()):
                lines.append(f"{category}:")
                for ag in by_category[category]:
                    lines.append(f"  - {ag.name}: {ag.description}")
            lines.append("")
        
        # Add format rules summary
        if self.format_rules:
            lines.append("=== FORMAT RULES ===")
            for rule in self.format_rules:
                lines.append(f"{rule.rule_type.value}: {rule.description}")
                if rule.timing_constraint:
                    lines.append(f"  Timing: {rule.timing_constraint.format_for_display()}")
            lines.append("")
        
        return "\n".join(lines)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate template has all required fields.
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        if not self.name or not self.name.strip():
            errors.append("name is required")
        
        if not self.description or not self.description.strip():
            errors.append("description is required")
        
        if not self.slug or not self.slug.strip():
            errors.append("slug is required")
        
        # Validate format rules
        for rule in self.format_rules:
            try:
                FormatRule(**rule.__dict__)
            except ValueError as e:
                errors.append(f"Format rule '{rule.description}': {e}")
        
        # Validate matching criteria reference valid asset groups
        valid_group_names = {g.name for g in self.asset_groups}
        for criteria in self.matching_criteria:
            if criteria.target_asset_group not in valid_group_names:
                errors.append(
                    f"Matching criteria references unknown asset group: "
                    f"{criteria.target_asset_group}"
                )
        
        return (len(errors) == 0, errors)
    
    def get_rules_by_type(self, rule_type: RuleType) -> List[FormatRule]:
        """Get all rules of a specific type."""
        return [r for r in self.format_rules if r.rule_type == rule_type]
    
    def get_cutting_rules(self) -> List[FormatRule]:
        """Get cutting rules specifically."""
        return self.get_rules_by_type(RuleType.CUTTING)
    
    def get_matching_criteria_for_group(self, group_name: str) -> List[MediaMatchingCriteria]:
        """Get matching criteria targeting a specific asset group."""
        return [c for c in self.matching_criteria if c.target_asset_group == group_name]
    
    def get_ai_prompt_section(self, transcript_length_seconds: int = 0) -> str:
        """Generate AI prompt section with rules and criteria."""
        from .prompt_formatter import FormatRulePromptFormatter
        formatter = FormatRulePromptFormatter()
        return formatter.format_rules_for_ai(
            self.format_rules,
            self.matching_criteria
        )
    
    @staticmethod
    def slug_from_path(file_path: Path) -> str:
        """Generate template slug from file path.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            Slug string (filename without extension, sanitized)
            
        Example:
            Path("/templates/youtube-interview.md") -> "youtube-interview"
        """
        stem = file_path.stem
        sanitized = stem.replace("..", "").replace("/", "").replace("\\", "")
        return sanitized


@dataclass
class FormatTemplateCollection:
    """Collection of format templates with lookup capabilities.
    
    Attributes:
        templates: List of FormatTemplate instances
    """
    
    templates: List[FormatTemplate] = field(default_factory=list)
    _slugs: set = field(default_factory=set, repr=False)
    
    def add(self, template: FormatTemplate) -> bool:
        """Add a template to the collection.
        
        Args:
            template: FormatTemplate to add
            
        Returns:
            True if added, False if duplicate slug
        """
        if template.slug in self._slugs:
            return False
        
        self.templates.append(template)
        self._slugs.add(template.slug)
        return True
    
    def get_by_slug(self, slug: str) -> FormatTemplate | None:
        """Find template by slug.
        
        Args:
            slug: Template slug to search for
            
        Returns:
            FormatTemplate if found, None otherwise
        """
        for template in self.templates:
            if template.slug == slug:
                return template
        return None
    
    def get_all(self) -> List[FormatTemplate]:
        """Get all templates in the collection.
        
        Returns:
            List of all FormatTemplate instances
        """
        return self.templates.copy()
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert all templates to list of dictionaries.
        
        Returns:
            List of template dictionaries
        """
        return [t.to_dict() for t in self.templates]
    
    def __len__(self) -> int:
        """Return number of templates in collection."""
        return len(self.templates)
    
    def __iter__(self):
        """Allow iteration over templates."""
        return iter(self.templates)
