"""Markdown template parser for format templates.

Parses markdown template files and extracts structured data from both
frontmatter (YAML) and body sections (Structure, Timing, Asset Groups, Format Rules).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

from .models import (
    FormatTemplate, TemplateSegment, AssetGroup,
    FormatRule, RuleType, TimingConstraint, SegmentStructure, TransitionRule,
    MediaMatchingCriteria, MatchingCriteriaType, MatchingRule
)

logger = logging.getLogger(__name__)

# Maximum file size to read (10MB) to prevent DoS
MAX_FILE_SIZE = 10 * 1024 * 1024


class TemplateParser:
    """Parses format template markdown files.
    
    Extracts both frontmatter metadata and body structure sections
    to create fully populated FormatTemplate instances.
    """
    
    def __init__(self):
        """Initialize the parser."""
        self._warnings: List[str] = []
    
    def parse_file(self, file_path: Path) -> Optional[FormatTemplate]:
        """Parse a markdown template file.
        
        Extracts frontmatter and body sections to create a complete
        FormatTemplate with all available structure data.
        
        Args:
            file_path: Path to the markdown template file
            
        Returns:
            FormatTemplate if parsing succeeds, None otherwise
        """
        self._warnings = []
        
        try:
            # Check file size
            try:
                file_size = file_path.stat().st_size
                if file_size == 0:
                    logger.warning(f"Skipping empty file {file_path}")
                    return None
                if file_size > MAX_FILE_SIZE:
                    logger.warning(f"Skipping large file {file_path}: {file_size} bytes")
                    return None
            except (OSError, FileNotFoundError, PermissionError, IsADirectoryError, NotADirectoryError) as e:
                logger.warning(f"Failed to stat file {file_path}: {e}")
                return None
            
            # Read file content
            content = file_path.read_text(encoding="utf-8")
            
            # Parse frontmatter and body
            frontmatter, body = self._split_frontmatter(content)
            
            # Extract basic metadata from frontmatter
            slug = FormatTemplate.slug_from_path(file_path)
            name = str(frontmatter.get("name", "")).strip()
            description = str(frontmatter.get("description", "")).strip()
            
            if not name or not description:
                logger.debug(f"Missing required fields in {file_path}")
                return None
            
            # Parse body sections
            structure = self._extract_structure_overview(body)
            segments = self._extract_timing_segments(body)
            asset_groups = self._extract_asset_groups(body)
            
            # Parse format rules and matching criteria (Story 3.6)
            format_rules = self._extract_format_rules(body)
            matching_criteria = self._extract_matching_criteria(body, asset_groups)
            
            # Log warnings if sections are missing
            if not segments:
                self._warnings.append("No timing segments found")
            if not asset_groups:
                self._warnings.append("No asset groups found")
            
            if self._warnings:
                logger.debug(f"Template '{slug}' warnings: {', '.join(self._warnings)}")
            
            return FormatTemplate(
                slug=slug,
                name=name,
                description=description,
                file_path=file_path,
                structure=structure,
                segments=segments,
                asset_groups=asset_groups,
                format_rules=format_rules,
                matching_criteria=matching_criteria,
                raw_markdown=content
            )
            
        except UnicodeDecodeError as e:
            logger.warning(f"Unicode decode error in {file_path}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to parse template file {file_path}: {e}")
            return None
    
    def _split_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Split content into frontmatter and body.
        
        Args:
            content: Full markdown file content
            
        Returns:
            Tuple of (frontmatter dict, body string)
        """
        if not content.startswith("---"):
            return {}, content
        
        # Normalize Windows line endings (CRLF) to Unix (LF) for consistent parsing
        content = content.replace('\r\n', '\n')
        
        # Find the end of frontmatter
        lines = content.split('\n')
        if len(lines) < 2:
            return {}, content
        
        end_idx = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                end_idx = i
                break
        
        if end_idx == -1:
            return {}, content
        
        # Parse frontmatter YAML
        yaml_lines = lines[1:end_idx]
        yaml_content = '\n'.join(yaml_lines)
        
        frontmatter: Dict[str, Any] = {}
        if yaml_content.strip():
            try:
                if yaml:
                    result = yaml.safe_load(yaml_content)
                    if isinstance(result, dict):
                        frontmatter = result
            except Exception as e:
                logger.debug(f"YAML parse error: {e}")
        
        # Body is everything after frontmatter
        body_lines = lines[end_idx + 1:]
        body = '\n'.join(body_lines).strip()
        
        return frontmatter, body
    
    def _extract_structure_overview(self, body: str) -> str:
        """Extract the structure overview section from body.
        
        Args:
            body: Markdown body content (without frontmatter)
            
        Returns:
            Structure overview text or empty string
        """
        # Normalize line endings first for consistent parsing
        body = body.replace('\r\n', '\n')
        
        patterns = [
            r'## Structure Overview\s*\n(.*?)(?=\n## |\n# |$)',
            r'# Structure Overview\s*\n(.*?)(?=\n## |\n# |$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                lines = content.split('\n')
                overview_lines = []
                for line in lines:
                    if line.strip().startswith('##') or line.strip().startswith('###'):
                        break
                    overview_lines.append(line)
                return '\n'.join(overview_lines).strip()
        
        return ""
    
    def _extract_timing_segments(self, body: str) -> List[TemplateSegment]:
        """Extract timing segments from the Timing Specifications section.
        
        Args:
            body: Markdown body content (without frontmatter)
            
        Returns:
            List of TemplateSegment instances
        """
        segments: List[TemplateSegment] = []
        
        # Find the Timing Specifications section
        timing_patterns = [
            r'## Timing Specifications\s*\n(.*?)(?=\n## |\n# |$)',
            r'### Timing\s*\n(.*?)(?=\n## |\n# |$)',
        ]
        
        timing_section = ""
        for pattern in timing_patterns:
            match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)
            if match:
                timing_section = match.group(1)
                break
        
        if not timing_section:
            return segments
        
        # Parse individual segments
        segment_pattern = r'###\s*([^\(]+)\s*\(([^)]+)\)\s*\n(.*?)(?=###|\Z)'
        segment_matches = re.findall(segment_pattern, timing_section, re.DOTALL)
        
        for name_time, time_range, content in segment_matches:
            name = name_time.strip()
            
            # Parse time range
            time_match = re.match(r'([^-\u2013\u2014\u2212]+)\s*[-\u2013\u2014\u2212]\s*([^-\u2013\u2014\u2212]+)', time_range.strip())
            if time_match:
                start_time = time_match.group(1).strip()
                end_time = time_match.group(2).strip()
            else:
                start_time = time_range.strip()
                end_time = ""
            
            duration = self._extract_field(content, r'\*\*Duration\*\*:\s*([^\n]+)')
            purpose = self._extract_field(content, r'\*\*Purpose\*\*:\s*([^\n]+)')
            
            if not duration and start_time and end_time:
                duration = self._calculate_duration(start_time, end_time)
            
            segment = TemplateSegment(
                name=name,
                start_time=start_time,
                end_time=end_time,
                duration=duration or "Unknown",
                purpose=purpose or ""
            )
            segments.append(segment)
        
        return segments
    
    def _extract_asset_groups(self, body: str) -> List[AssetGroup]:
        """Extract asset group definitions from the Asset Groups section.
        
        Args:
            body: Markdown body content (without frontmatter)
            
        Returns:
            List of AssetGroup instances
        """
        asset_groups: List[AssetGroup] = []
        
        # Find the Asset Groups section
        asset_patterns = [
            r'## Asset Groups\s*\n(.*?)(?=\n## |\n# |$)',
            r'### Asset Groups\s*\n(.*?)(?=\n## |\n# |$)',
        ]
        
        asset_section = ""
        for pattern in asset_patterns:
            match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)
            if match:
                asset_section = match.group(1)
                break
        
        if not asset_section:
            return asset_groups
        
        # Parse categories
        category_pattern = r'###\s*([\w\s-]+?)\s*\n(.*?)(?=###|\Z)'
        category_matches = re.findall(category_pattern, asset_section, re.DOTALL)
        
        for category_name, category_content in category_matches:
            category = category_name.strip()
            
            # Parse individual assets
            asset_pattern = r'-\s*\*\*([^*]+)\*\*:\s*([^\n]+(?:\n(?=\s*-\s*\*\*)|$))'
            asset_matches = re.findall(asset_pattern, category_content)
            
            for asset_name, asset_description in asset_matches:
                description = asset_description.strip()
                
                # Extract search tags from description
                tags: List[str] = []
                tags_match = re.search(r'\(([\w,\s-]+)\)', description)
                if tags_match:
                    tags_str = tags_match.group(1)
                    tags = [t.strip() for t in tags_str.split(',') if t.strip()]
                    description = re.sub(r'\s*\([\w,\s-]+\)$', '', description).strip()
                
                asset_group = AssetGroup(
                    category=category,
                    name=asset_name.strip(),
                    description=description,
                    search_tags=tags
                )
                asset_groups.append(asset_group)
        
        return asset_groups
    
    def _extract_format_rules(self, body: str) -> List[FormatRule]:
        """Extract format rules from YAML code blocks in the markdown.
        
        Args:
            body: Markdown body content (without frontmatter)
            
        Returns:
            List of FormatRule instances
        """
        format_rules: List[FormatRule] = []
        
        # Find YAML code blocks containing format_rules or cutting_rules
        yaml_pattern = r'```yaml\s*\n(.*?)\n```'
        yaml_blocks = re.findall(yaml_pattern, body, re.DOTALL)
        
        for yaml_content in yaml_blocks:
            try:
                if not yaml:
                    continue
                data = yaml.safe_load(yaml_content)
                
                if not isinstance(data, dict):
                    continue
                
                # Check for format_rules or cutting_rules
                rules_data = data.get('format_rules') or data.get('cutting_rules')
                if not rules_data or not isinstance(rules_data, dict):
                    continue
                
                # Parse each rule
                for rule_name, rule_def in rules_data.items():
                    try:
                        if not isinstance(rule_def, dict):
                            continue
                        
                        rule = self._parse_format_rule(rule_name, rule_def)
                        if rule:
                            format_rules.append(rule)
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Skipping invalid format rule '{rule_name}': {e}")
                        continue
                        
            except Exception as e:
                # Handle YAML parsing errors or other exceptions
                logger.debug(f"Error parsing format rules: {e}")
                continue
        
        # Sort by priority (higher first)
        format_rules.sort(key=lambda r: r.priority, reverse=True)
        return format_rules
    
    def _parse_format_rule(self, name: str, definition: Dict[str, Any]) -> Optional[FormatRule]:
        """Parse a single format rule definition."""
        # Parse rule type
        rule_type_str = definition.get('rule_type', 'cutting')
        try:
            rule_type = RuleType(rule_type_str.lower())
        except ValueError:
            logger.warning(f"Unknown rule_type '{rule_type_str}', defaulting to CUTTING")
            rule_type = RuleType.CUTTING
        
        # Parse timing constraint
        timing_constraint = None
        if 'timing_constraint' in definition:
            timing_constraint = self._parse_timing_constraint(definition['timing_constraint'])
        elif 'timing' in definition:
            timing_constraint = self._parse_timing_constraint(definition['timing'])
        
        # Parse segment structure
        segment_structure = None
        if 'segment_structure' in definition:
            segment_structure = self._parse_segment_structure(definition['segment_structure'])
        elif 'segments' in definition:
            segment_structure = self._parse_segment_structure(definition['segments'])
        
        # Parse transitions
        transitions = []
        if 'transitions' in definition and isinstance(definition['transitions'], list):
            for trans_def in definition['transitions']:
                if isinstance(trans_def, dict):
                    transitions.append(self._parse_transition_rule(trans_def))
        
        # Parse priority with None guard
        priority = definition.get('priority', 1)
        if priority is None:
            priority = 1
        elif not isinstance(priority, int):
            try:
                priority = int(priority)
            except (ValueError, TypeError):
                logger.warning(f"Invalid priority value '{priority}', defaulting to 1")
                priority = 1
        
        return FormatRule(
            rule_type=rule_type,
            description=definition.get('description', name.replace('_', ' ').title()),
            timing_constraint=timing_constraint,
            segment_structure=segment_structure,
            transitions=transitions,
            strict_mode=definition.get('strict_mode', True),
            priority=priority,
            fallback_rules=definition.get('fallback_rules', [])
        )
    
    def _parse_timing_constraint(self, timing_def: Any) -> Optional[TimingConstraint]:
        """Parse timing constraint from various formats."""
        if timing_def is None:
            return None
        
        if isinstance(timing_def, str):
            return TimingConstraint.from_string(timing_def)
        elif isinstance(timing_def, dict):
            return TimingConstraint(
                min_duration=timing_def.get('min'),
                max_duration=timing_def.get('max'),
                exact_duration=timing_def.get('exact'),
                flexible=timing_def.get('flexible', True)
            )
        return None
    
    def _parse_segment_structure(self, struct_def: Any) -> Optional[SegmentStructure]:
        """Parse segment structure definition."""
        if not isinstance(struct_def, dict):
            return None
        
        return SegmentStructure(
            segment_count=struct_def.get('segment_count', 1),
            segment_descriptions=struct_def.get('descriptions', []),
            segment_order=struct_def.get('order', 'sequential')
        )
    
    def _parse_transition_rule(self, trans_def: Dict) -> TransitionRule:
        """Parse a single transition rule."""
        return TransitionRule(
            from_segment=trans_def.get('from'),
            to_segment=trans_def.get('to'),
            transition_type=trans_def.get('type', 'cut'),
            duration=trans_def.get('duration'),
            style=trans_def.get('style', 'standard')
        )
    
    def _extract_matching_criteria(
        self, body: str, asset_groups: List[AssetGroup]
    ) -> List[MediaMatchingCriteria]:
        """Extract media matching criteria from YAML code blocks.
        
        Args:
            body: Markdown body content (without frontmatter)
            asset_groups: List of asset groups for validation
            
        Returns:
            List of MediaMatchingCriteria instances
        """
        criteria_list: List[MediaMatchingCriteria] = []
        
        # Get valid asset group names for validation
        valid_group_names = {g.name for g in asset_groups}
        
        # Find YAML code blocks containing media_matching
        yaml_pattern = r'```yaml\s*\n(.*?)\n```'
        yaml_blocks = re.findall(yaml_pattern, body, re.DOTALL)
        
        for yaml_content in yaml_blocks:
            try:
                if not yaml:
                    continue
                data = yaml.safe_load(yaml_content)
                
                if not isinstance(data, dict):
                    continue
                
                matching_data = data.get('media_matching')
                if not matching_data or not isinstance(matching_data, dict):
                    continue
                
                # Parse each matching criteria
                for target_group, criteria_def in matching_data.items():
                    try:
                        # Validate target group exists
                        if target_group not in valid_group_names:
                            logger.warning(
                                f"Media matching references unknown asset group: {target_group}"
                            )
                            continue
                        
                        if not isinstance(criteria_def, dict):
                            continue
                        
                        criteria = self._parse_matching_criteria(target_group, criteria_def)
                        if criteria:
                            criteria_list.append(criteria)
                    except (ValueError, KeyError) as e:
                        logger.warning(
                            f"Skipping invalid matching criteria for '{target_group}': {e}"
                        )
                        continue
                        
            except Exception as e:
                # Handle YAML parsing errors or other exceptions
                logger.debug(f"Error parsing media matching: {e}")
                continue
        
        return criteria_list
    
    def _parse_matching_criteria(
        self, target_group: str, definition: Dict[str, Any]
    ) -> Optional[MediaMatchingCriteria]:
        """Parse a single media matching criteria definition."""
        # Parse criteria type
        criteria_type_str = definition.get('criteria_type', 'context_match')
        try:
            criteria_type = MatchingCriteriaType(criteria_type_str.lower())
        except ValueError:
            logger.warning(f"Unknown criteria_type '{criteria_type_str}', defaulting to CONTEXT_MATCH")
            criteria_type = MatchingCriteriaType.CONTEXT_MATCH
        
        # Parse matching rules
        matching_rules = []
        if 'matching_rules' in definition and isinstance(definition['matching_rules'], list):
            for rule_def in definition['matching_rules']:
                if isinstance(rule_def, dict):
                    try:
                        rule = MatchingRule(
                            attribute=rule_def.get('attribute', ''),
                            condition=rule_def.get('condition', 'equals'),
                            value=rule_def.get('value'),
                            weight=rule_def.get('weight', 1.0)
                        )
                        matching_rules.append(rule)
                    except ValueError as e:
                        logger.warning(f"Skipping invalid matching rule: {e}")
        
        # Parse priority with None guard
        priority = definition.get('priority', 1)
        if priority is None:
            priority = 1
        elif not isinstance(priority, int):
            try:
                priority = int(priority)
            except (ValueError, TypeError):
                logger.warning(f"Invalid priority value '{priority}', defaulting to 1")
                priority = 1
        
        return MediaMatchingCriteria(
            criteria_type=criteria_type,
            target_asset_group=target_group,
            description=definition.get('description', f"Match assets for {target_group}"),
            matching_rules=matching_rules,
            ai_guidance=definition.get('ai_guidance', ''),
            priority=priority,
            required=definition.get('required', True)
        )
    
    def _extract_field(self, content: str, pattern: str) -> str:
        """Extract a field value using regex pattern.
        
        Args:
            content: Text content to search
            pattern: Regex pattern with capture group
            
        Returns:
            Extracted value or empty string
        """
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()
        return ""
    
    def _calculate_duration(self, start_time: str, end_time: str) -> str:
        """Calculate human-readable duration from time range.
        
        Args:
            start_time: Start time in format "M:SS" or "H:MM:SS"
            end_time: End time in format "M:SS" or "H:MM:SS"
            
        Returns:
            Human-readable duration string
        """
        try:
            start_seconds = self._time_to_seconds(start_time)
            end_seconds = self._time_to_seconds(end_time)
            
            if start_seconds is None or end_seconds is None:
                return ""
            
            duration_seconds = end_seconds - start_seconds
            
            if duration_seconds < 0:
                return ""
            
            if duration_seconds < 60:
                return f"{duration_seconds} seconds"
            elif duration_seconds < 3600:
                minutes = duration_seconds // 60
                seconds = duration_seconds % 60
                if seconds == 0:
                    return f"{minutes} minute{'s' if minutes != 1 else ''}"
                else:
                    return f"{minutes} minute{'s' if minutes != 1 else ''} {seconds} seconds"
            else:
                hours = duration_seconds // 3600
                remaining = duration_seconds % 3600
                minutes = remaining // 60
                if minutes == 0:
                    return f"{hours} hour{'s' if hours != 1 else ''}"
                else:
                    return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minutes"
        except Exception:
            return ""
    
    def _time_to_seconds(self, time_str: str) -> Optional[int]:
        """Convert time string to seconds.
        
        Args:
            time_str: Time string like "0:15", "3:15", "1:30:00"
            
        Returns:
            Seconds as integer or None if invalid
        """
        try:
            parts = time_str.strip().split(':')
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = int(parts[1])
                return minutes * 60 + seconds
            elif len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            else:
                return None
        except (ValueError, IndexError):
            return None


class TemplateParserError(Exception):
    """Exception raised for template parser errors."""
    pass


class FormatRuleParseError(Exception):
    """Exception raised for format rule parsing errors."""
    
    def __init__(self, message: str, rule_name: Optional[str] = None):
        super().__init__(message)
        self.rule_name = rule_name
