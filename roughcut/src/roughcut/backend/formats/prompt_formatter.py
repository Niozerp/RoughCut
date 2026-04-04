"""Format rule prompt formatter for AI service integration.

Converts format rules and media matching criteria into AI-readable
prompt sections for rough cut generation.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional

from .models import FormatRule, MediaMatchingCriteria, RuleType


class FormatRulePromptFormatter:
    """Formats format rules and matching criteria for AI prompts."""
    
    def __init__(self):
        """Initialize the formatter."""
        pass
    
    def format_rules_for_ai(
        self,
        format_rules: List[FormatRule],
        matching_criteria: List[MediaMatchingCriteria]
    ) -> str:
        """
        Format all rules and criteria as comprehensive AI instructions.
        
        Args:
            format_rules: List of format rules to format
            matching_criteria: List of media matching criteria to format
            
        Returns:
            Formatted string ready to include in AI prompt
        """
        sections = []
        
        # Format Rules Section
        if format_rules:
            sections.append("=" * 50)
            sections.append("FORMAT RULES - Cut the transcript according to these rules:")
            sections.append("=" * 50)
            
            for i, rule in enumerate(format_rules, 1):
                sections.append(f"\n{i}. {rule.format_for_ai()}")
        
        # Media Matching Section
        if matching_criteria:
            sections.append("\n" + "=" * 50)
            sections.append("MEDIA MATCHING CRITERIA - Match assets using these criteria:")
            sections.append("=" * 50)
            
            # Group by target asset group
            by_group: Dict[str, List[MediaMatchingCriteria]] = {}
            for criteria in matching_criteria:
                if criteria.target_asset_group not in by_group:
                    by_group[criteria.target_asset_group] = []
                by_group[criteria.target_asset_group].append(criteria)
            
            for group_name, criteria_list in by_group.items():
                sections.append(f"\n{group_name}:")
                for criteria in criteria_list:
                    sections.append(criteria.format_for_ai())
        
        # Instructions footer
        sections.append("\n" + "=" * 50)
        sections.append("INSTRUCTIONS:")
        sections.append("- Follow all strict_mode rules exactly")
        sections.append("- Preserve original transcript words exactly (do not paraphrase)")
        sections.append("- Match assets based on criteria priority")
        sections.append("- Create exactly the number of segments specified")
        sections.append("=" * 50)
        
        return "\n".join(sections)
    
    def format_for_transcript_cutting(
        self,
        format_rules: List[FormatRule],
        transcript_length_seconds: int
    ) -> str:
        """Format rules specifically for transcript cutting step.
        
        Args:
            format_rules: List of format rules
            transcript_length_seconds: Length of source transcript in seconds
            
        Returns:
            Formatted instructions for transcript cutting
        """
        cutting_rules = [r for r in format_rules if r.rule_type == RuleType.CUTTING]
        timing_rules = [r for r in format_rules if r.rule_type == RuleType.TIMING]
        
        lines = ["TRANSCRIPT CUTTING INSTRUCTIONS:"]
        
        # Total timing context
        total_min = None
        total_max = None
        for rule in timing_rules:
            if rule.timing_constraint:
                if rule.timing_constraint.min_duration:
                    total_min = rule.timing_constraint.min_duration
                if rule.timing_constraint.max_duration:
                    total_max = rule.timing_constraint.max_duration
        
        if total_min or total_max:
            lines.append(f"Target Duration: {total_min or 'flexible'} - {total_max or 'flexible'} seconds")
            lines.append(f"Source Transcript: {transcript_length_seconds} seconds")
        
        # Cutting instructions
        for rule in cutting_rules:
            lines.append(f"\n{rule.format_for_ai()}")
        
        return "\n".join(lines)
    
    def format_for_asset_matching(
        self,
        matching_criteria: List[MediaMatchingCriteria],
        segment_name: Optional[str] = None
    ) -> str:
        """Format matching criteria for asset selection step.
        
        Args:
            matching_criteria: List of media matching criteria
            segment_name: Optional segment context for matching
            
        Returns:
            Formatted instructions for asset matching
        """
        lines = ["ASSET MATCHING INSTRUCTIONS:"]
        
        if segment_name:
            lines.append(f"Context: {segment_name}")
        
        # Separate required vs optional
        required = [c for c in matching_criteria if c.required]
        optional = [c for c in matching_criteria if not c.required]
        
        if required:
            lines.append("\nRequired Matches:")
            for criteria in required:
                lines.append(criteria.format_for_ai())
        
        if optional:
            lines.append("\nOptional Matches (use if suitable):")
            for criteria in optional:
                lines.append(criteria.format_for_ai())
        
        return "\n".join(lines)
    
    def format_summary(
        self,
        format_rules: List[FormatRule],
        matching_criteria: List[MediaMatchingCriteria]
    ) -> str:
        """Create a human-readable summary of format rules.
        
        Args:
            format_rules: List of format rules
            matching_criteria: List of media matching criteria
            
        Returns:
            Human-readable summary
        """
        lines = ["Format Summary:"]
        
        # Count rules by type
        cutting_count = len([r for r in format_rules if r.rule_type == RuleType.CUTTING])
        timing_count = len([r for r in format_rules if r.rule_type == RuleType.TIMING])
        transition_count = len([r for r in format_rules if r.rule_type == RuleType.TRANSITION])
        
        if cutting_count:
            lines.append(f"- {cutting_count} cutting rule(s)")
        if timing_count:
            lines.append(f"- {timing_count} timing constraint(s)")
        if transition_count:
            lines.append(f"- {transition_count} transition rule(s)")
        
        # Total duration estimate
        total_min = None
        total_max = None
        for rule in format_rules:
            if rule.timing_constraint:
                if rule.timing_constraint.min_duration:
                    total_min = rule.timing_constraint.min_duration
                if rule.timing_constraint.max_duration:
                    total_max = rule.timing_constraint.max_duration
        
        if total_min or total_max:
            if total_min == total_max:
                lines.append(f"- Target duration: exactly {self._format_duration(total_min)}")
            else:
                min_str = self._format_duration(total_min) if total_min else "flexible"
                max_str = self._format_duration(total_max) if total_max else "flexible"
                lines.append(f"- Target duration: {min_str} to {max_str}")
        
        # Matching criteria summary
        if matching_criteria:
            lines.append(f"- {len(matching_criteria)} asset matching criteria")
            required_count = len([c for c in matching_criteria if c.required])
            if required_count:
                lines.append(f"  ({required_count} required, {len(matching_criteria) - required_count} optional)")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_duration(seconds: Optional[int]) -> str:
        """Format duration in seconds to readable string.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if seconds is None:
            return "unknown"
        
        if seconds < 60:
            return f"{seconds}s"
        
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        
        if remaining_seconds == 0:
            return f"{minutes}m"
        
        return f"{minutes}:{remaining_seconds:02d}"
