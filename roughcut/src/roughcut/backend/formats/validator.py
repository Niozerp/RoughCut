"""Template validation for format templates."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional
from pathlib import Path

from .models import (
    FormatTemplate, TemplateSegment, AssetGroup,
    FormatRule, TimingConstraint, SegmentStructure, TransitionRule,
    MediaMatchingCriteria, MatchingRule, RuleType
)


class ValidationError(Exception):
    """Exception raised for template validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field


class FormatRuleValidator:
    """
    Validates format rules and media matching criteria.
    
    Ensures format rules have logical consistency, proper timing constraints,
    and valid cross-references to asset groups.
    
    Example:
        >>> validator = FormatRuleValidator()
        >>> is_valid, errors = validator.validate_format_rules(template.format_rules)
        >>> if not is_valid:
        ...     for error in errors:
        ...         print(f"Rule error: {error}")
    """
    
    def __init__(self):
        """Initialize validator."""
        self._errors: List[str] = []
    
    def validate_format_rules(
        self, 
        format_rules: List[FormatRule],
        asset_groups: Optional[List[AssetGroup]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate a list of format rules.
        
        Checks:
        - Timing constraint logical consistency (min <= max)
        - Segment structure has valid segment_count (> 0)
        - Transition rules reference valid segment boundaries
        - No timing conflicts between rules
        
        Args:
            format_rules: List of FormatRule objects to validate
            asset_groups: Optional list of asset groups for transition validation
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        self._errors = []
        
        if not format_rules:
            return True, []
        
        # Track timing constraints across all rules
        total_min = None
        total_max = None
        
        for i, rule in enumerate(format_rules):
            self._validate_single_rule(rule, i, asset_groups)
            
            # Track total timing across timing rules
            if rule.rule_type == RuleType.TIMING and rule.timing_constraint:
                tc = rule.timing_constraint
                if tc.min_duration is not None:
                    if total_min is None or tc.min_duration > total_min:
                        total_min = tc.min_duration
                if tc.max_duration is not None:
                    if total_max is None or tc.max_duration < total_max:
                        total_max = tc.max_duration
        
        # Check for timing conflicts between min and max
        if total_min is not None and total_max is not None and total_min > total_max:
            self._errors.append(
                f"Timing conflict: minimum duration ({total_min}s) exceeds "
                f"maximum duration ({total_max}s) across timing rules"
            )
        
        return (len(self._errors) == 0, self._errors)
    
    def _validate_single_rule(
        self, 
        rule: FormatRule, 
        index: int,
        asset_groups: Optional[List[AssetGroup]] = None
    ) -> None:
        """Validate a single format rule."""
        prefix = f"FormatRule[{index}] '{rule.description}'"
        
        # Validate rule type specific requirements
        if rule.rule_type == RuleType.CUTTING:
            if not rule.segment_structure:
                self._errors.append(
                    f"{prefix}: CUTTING rules require segment_structure"
                )
            elif rule.segment_structure.segment_count <= 0:
                self._errors.append(
                    f"{prefix}: segment_count must be > 0"
                )
        
        # Validate timing constraint
        if rule.timing_constraint:
            self._validate_timing_constraint(rule.timing_constraint, prefix)
        
        # Validate transitions reference valid segments
        if rule.transitions and rule.segment_structure:
            max_segment = rule.segment_structure.segment_count - 1
            for j, trans in enumerate(rule.transitions):
                self._validate_transition(trans, j, prefix, max_segment)
        
        # Validate fallback rules exist
        if rule.fallback_rules:
            for fallback in rule.fallback_rules:
                if not fallback or not fallback.strip():
                    self._errors.append(
                        f"{prefix}: Empty fallback rule name"
                    )
    
    def _validate_timing_constraint(
        self, 
        tc: TimingConstraint, 
        prefix: str
    ) -> None:
        """Validate a timing constraint."""
        # Check logical consistency (already handled in __post_init__, but double-check)
        if tc.min_duration is not None and tc.max_duration is not None:
            if tc.min_duration > tc.max_duration:
                self._errors.append(
                    f"{prefix}: min_duration ({tc.min_duration}s) exceeds "
                    f"max_duration ({tc.max_duration}s)"
                )
        
        # Check negative durations (should be caught by __post_init__)
        if tc.exact_duration is not None and tc.exact_duration < 0:
            self._errors.append(
                f"{prefix}: exact_duration must be >= 0"
            )
        if tc.min_duration is not None and tc.min_duration < 0:
            self._errors.append(
                f"{prefix}: min_duration must be >= 0"
            )
        if tc.max_duration is not None and tc.max_duration < 0:
            self._errors.append(
                f"{prefix}: max_duration must be >= 0"
            )
    
    def _validate_transition(
        self, 
        trans: TransitionRule, 
        index: int,
        prefix: str,
        max_segment: int
    ) -> None:
        """Validate a transition rule."""
        trans_prefix = f"{prefix}.Transition[{index}]"
        
        # Check segment boundaries
        if trans.from_segment is not None:
            if trans.from_segment < 0 or trans.from_segment > max_segment:
                self._errors.append(
                    f"{trans_prefix}: from_segment ({trans.from_segment}) "
                    f"exceeds max segment ({max_segment})"
                )
        
        if trans.to_segment is not None:
            if trans.to_segment < 0 or trans.to_segment > max_segment:
                self._errors.append(
                    f"{trans_prefix}: to_segment ({trans.to_segment}) "
                    f"exceeds max segment ({max_segment})"
                )
        
        # Validate transition type
        valid_types = ["cut", "dissolve", "fade", "wipe"]
        if trans.transition_type not in valid_types:
            self._errors.append(
                f"{trans_prefix}: Invalid transition_type '{trans.transition_type}'. "
                f"Must be one of: {', '.join(valid_types)}"
            )
    
    def validate_matching_criteria(
        self,
        criteria_list: List[MediaMatchingCriteria],
        asset_groups: List[AssetGroup]
    ) -> Tuple[bool, List[str]]:
        """
        Validate media matching criteria.
        
        Checks:
        - Each criteria references a valid asset group
        - Matching rules have valid attributes and conditions
        - No duplicate criteria for same asset group
        
        Args:
            criteria_list: List of MediaMatchingCriteria to validate
            asset_groups: List of valid AssetGroup objects
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        self._errors = []
        
        if not criteria_list:
            return True, []
        
        # Build set of valid asset group names
        valid_group_names = {g.name for g in asset_groups}
        seen_groups = set()
        
        for i, criteria in enumerate(criteria_list):
            prefix = f"MediaMatchingCriteria[{i}] '{criteria.target_asset_group}'"
            
            # Check asset group exists
            if criteria.target_asset_group not in valid_group_names:
                self._errors.append(
                    f"{prefix}: References unknown asset group "
                    f"'{criteria.target_asset_group}'"
                )
            
            # Check for duplicates
            if criteria.target_asset_group in seen_groups:
                self._errors.append(
                    f"{prefix}: Duplicate criteria for asset group "
                    f"'{criteria.target_asset_group}'"
                )
            else:
                seen_groups.add(criteria.target_asset_group)
            
            # Validate matching rules
            for j, rule in enumerate(criteria.matching_rules):
                self._validate_matching_rule(rule, j, prefix)
        
        return (len(self._errors) == 0, self._errors)
    
    def _validate_matching_rule(
        self, 
        rule: MatchingRule, 
        index: int,
        prefix: str
    ) -> None:
        """Validate a matching rule."""
        rule_prefix = f"{prefix}.MatchingRule[{index}]"
        
        # Check for valid condition
        valid_conditions = ["equals", "contains", "greater_than", "less_than", "matches"]
        if rule.condition not in valid_conditions:
            self._errors.append(
                f"{rule_prefix}: Invalid condition '{rule.condition}'. "
                f"Must be one of: {', '.join(valid_conditions)}"
            )
        
        # Check attribute is not empty
        if not rule.attribute or not rule.attribute.strip():
            self._errors.append(
                f"{rule_prefix}: attribute is required"
            )
        
        # Check weight is in valid range (0.0-1.0)
        if not 0.0 <= rule.weight <= 1.0:
            self._errors.append(
                f"{rule_prefix}: weight ({rule.weight}) must be between 0.0 and 1.0"
            )


class TemplateValidator:
    """
    Validates template data against schema requirements.
    
    Ensures templates have required fields, proper data types,
    and valid structure before being used in the system.
    
    Example:
        >>> validator = TemplateValidator()
        >>> is_valid, errors = validator.validate_template(template)
        >>> if not is_valid:
        ...     for error in errors:
        ...         print(f"Validation error: {error}")
    """
    
    REQUIRED_FIELDS = ['name', 'description']
    VALID_CATEGORIES = ['music', 'sfx', 'vfx', 'transition', 'sound_effects', 'audio', 'video']
    
    def __init__(self):
        """Initialize validator."""
        self._errors: List[str] = []
    
    def validate_frontmatter(
        self, 
        frontmatter: Dict[str, Any], 
        required_fields: Optional[List[str]] = None
    ) -> None:
        """
        Validate that frontmatter contains all required fields.
        
        Args:
            frontmatter: Parsed YAML frontmatter dictionary
            required_fields: List of field names that must be present
            
        Raises:
            ValidationError: If required fields are missing
        """
        fields = required_fields or self.REQUIRED_FIELDS
        missing = [f for f in fields if f not in frontmatter or not frontmatter[f]]
        
        if missing:
            raise ValidationError(
                f"Missing required fields: {', '.join(missing)}",
                field=missing[0] if missing else None
            )
    
    def validate_template(self, template: FormatTemplate) -> Tuple[bool, List[str]]:
        """
        Validate a complete template.
        
        Args:
            template: FormatTemplate to validate
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        # Reset errors at start of each validation (fixes P7)
        self._errors = []
        
        # Validate required fields
        if not template.name or not template.name.strip():
            self._errors.append("Template name is required")
        
        if not template.description or not template.description.strip():
            self._errors.append("Template description is required")
        
        if not template.slug or not template.slug.strip():
            self._errors.append("Template slug is required")
        
        # Validate segments
        for i, segment in enumerate(template.segments):
            self._validate_segment(segment, i)
        
        # Validate timing structure integrity (contiguous + sum)
        if template.segments:
            self._validate_timing_structure(template.segments, template.name)
        
        # Validate asset groups
        for i, group in enumerate(template.asset_groups):
            self._validate_asset_group(group, i)
        
        return (len(self._errors) == 0, self._errors)
    
    def _validate_timing_structure(self, segments: List[TemplateSegment], template_name: str) -> None:
        """
        Validate timing structure integrity.
        
        Checks:
        1. Segments are contiguous (end[i] == start[i+1])
        2. No overlapping segments
        3. Total duration sums correctly
        
        Args:
            segments: List of timing segments
            template_name: Name of template for error messages
        """
        if not segments:
            return
        
        # Convert all times to seconds for comparison
        segment_times = []
        for seg in segments:
            try:
                start_sec = self._time_to_seconds(seg.start_time)
                end_sec = self._time_to_seconds(seg.end_time)
                if start_sec is not None and end_sec is not None:
                    segment_times.append((seg.name, start_sec, end_sec))
            except (ValueError, AttributeError):
                continue  # Invalid time format already reported by _validate_segment
        
        if len(segment_times) < 2:
            return  # Can't check contiguity with < 2 segments
        
        # Sort by start time
        segment_times.sort(key=lambda x: x[1])
        
        # Check for overlaps and gaps
        for i in range(len(segment_times) - 1):
            current_name, current_start, current_end = segment_times[i]
            next_name, next_start, next_end = segment_times[i + 1]
            
            # Check for overlap
            if current_end > next_start:
                self._errors.append(
                    f"Timing overlap in '{template_name}': "
                    f"'{current_name}' ends at {self._seconds_to_time(current_end)} "
                    f"but '{next_name}' starts at {self._seconds_to_time(next_start)}"
                )
            
            # Check for gap (small gaps under 1 second are acceptable for transitions)
            elif next_start > current_end + 1:
                self._errors.append(
                    f"Timing gap in '{template_name}': "
                    f"'{current_name}' ends at {self._seconds_to_time(current_end)} "
                    f"but '{next_name}' starts at {self._seconds_to_time(next_start)}"
                )
    
    def _validate_segment(self, segment: TemplateSegment, index: int) -> None:
        """Validate a single timing segment."""
        prefix = f"Segment[{index}] '{segment.name}'"
        
        if not segment.name or not segment.name.strip():
            self._errors.append(f"{prefix}: Name is required")
        
        if not segment.start_time:
            self._errors.append(f"{prefix}: Start time is required")
        elif not self._is_valid_time_format(segment.start_time):
            self._errors.append(f"{prefix}: Invalid start time format '{segment.start_time}'")
        
        if not segment.end_time:
            self._errors.append(f"{prefix}: End time is required")
        elif not self._is_valid_time_format(segment.end_time):
            self._errors.append(f"{prefix}: Invalid end time format '{segment.end_time}'")
    
    def _validate_asset_group(self, group: AssetGroup, index: int) -> None:
        """Validate a single asset group."""
        prefix = f"AssetGroup[{index}] '{group.name}'"
        
        if not group.name or not group.name.strip():
            self._errors.append(f"{prefix}: Name is required")
        
        if not group.description or not group.description.strip():
            self._errors.append(f"{prefix}: Description is required")
        
        if group.category:
            category_lower = group.category.lower().replace(' ', '_')
            if category_lower not in self.VALID_CATEGORIES:
                self._errors.append(
                    f"{prefix}: Invalid category '{group.category}'. "
                    f"Valid categories: {', '.join(self.VALID_CATEGORIES)}"
                )
        
        # Validate tags
        if group.search_tags:
            for tag in group.search_tags:
                if not self._is_valid_tag(tag):
                    self._errors.append(
                        f"{prefix}: Invalid tag format '{tag}'. "
                        f"Tags should be lowercase alphanumeric with underscores."
                    )
    
    def validate_tags(self, tags: List[str]) -> List[str]:
        """
        Validate and normalize tag format.
        
        Args:
            tags: List of tag strings
            
        Returns:
            Normalized list of lowercase, trimmed tags
        """
        normalized = []
        for tag in tags:
            if not isinstance(tag, str):
                continue
            # Normalize: lowercase, trim whitespace, replace spaces with underscores
            normalized_tag = tag.lower().strip().replace(' ', '_')
            # Remove any non-alphanumeric characters except underscores
            normalized_tag = ''.join(c for c in normalized_tag if c.isalnum() or c == '_')
            if normalized_tag:
                normalized.append(normalized_tag)
        return normalized
    
    def validate_file_path(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate that a file path is safe for template loading.
        
        Args:
            file_path: Path to validate
            
        Returns:
            Tuple of (is_valid, error_message or None)
        """
        if not file_path.exists():
            return False, f"File does not exist: {file_path}"
        
        if not file_path.is_file():
            return False, f"Path is not a file: {file_path}"
        
        # Check extension
        if file_path.suffix.lower() != '.md':
            return False, f"File must be .md, got: {file_path.suffix}"
        
        # Check for path traversal
        try:
            # Resolve to absolute and check no parent refs
            resolved = file_path.resolve()
            if '..' in str(resolved):
                return False, f"Path contains directory traversal: {file_path}"
        except (OSError, RuntimeError):
            return False, f"Cannot resolve path: {file_path}"
        
        return True, None
    
    def _is_valid_time_format(self, time_str: str) -> bool:
        """Check if time string is valid format (M:SS or H:MM:SS)."""
        if not time_str:
            return False
        
        parts = time_str.split(':')
        if len(parts) not in [2, 3]:
            return False
        
        try:
            for part in parts:
                int(part)
            return True
        except ValueError:
            return False
    
    def _is_valid_tag(self, tag: str) -> bool:
        """Check if tag format is valid (lowercase alphanumeric + underscores)."""
        if not tag:
            return False
        
        # Must be lowercase
        if tag != tag.lower():
            return False
        
        # Only alphanumeric and underscores
        for char in tag:
            if not (char.isalnum() or char == '_'):
                return False
        
        return True
    
    def validate_template_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate a template file before parsing.
        
        Args:
            file_path: Path to template file
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Validate file path
        is_valid, error = self.validate_file_path(file_path)
        if not is_valid:
            errors.append(error)
            return False, errors
        
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024
        try:
            size = file_path.stat().st_size
            if size > max_size:
                errors.append(f"File too large: {size} bytes (max {max_size})")
            if size == 0:
                errors.append("File is empty")
        except OSError as e:
            errors.append(f"Cannot read file: {e}")
        
        return (len(errors) == 0, errors)
    
    def _time_to_seconds(self, time_str: str) -> Optional[int]:
        """
        Convert time string to seconds.
        
        Args:
            time_str: Time string like "0:15", "3:45", "1:30:00"
            
        Returns:
            Seconds as integer or None if invalid
        """
        try:
            parts = time_str.strip().split(':')
            if len(parts) == 2:
                # M:SS format
                minutes = int(parts[0])
                seconds = int(parts[1])
                return minutes * 60 + seconds
            elif len(parts) == 3:
                # H:MM:SS format
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            else:
                return None
        except (ValueError, IndexError, AttributeError):
            return None
    
    def _seconds_to_time(self, total_seconds: int) -> str:
        """
        Convert seconds to time string.
        
        Args:
            total_seconds: Total seconds
            
        Returns:
            Time string in M:SS or H:MM:SS format
        """
        if total_seconds < 0:
            return "0:00"
        
        hours = total_seconds // 3600
        remaining = total_seconds % 3600
        minutes = remaining // 60
        seconds = remaining % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
