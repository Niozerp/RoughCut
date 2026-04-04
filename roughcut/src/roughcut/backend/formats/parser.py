"""Markdown template parser for format templates.

Parses markdown template files and extracts structured data from both
frontmatter (YAML) and body sections (Structure, Timing, Asset Groups).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .models import FormatTemplate, TemplateSegment, AssetGroup

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
                import yaml
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
        # Look for "## Structure Overview" or "# Structure Overview" section
        # Normalize line endings first for consistent parsing
        body = body.replace('\r\n', '\n')
        
        patterns = [
            r'## Structure Overview\s*\n(.*?)(?=\n## |\n# |$)',
            r'# Structure Overview\s*\n(.*?)(?=\n## |\n# |$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)
            if match:
                # Extract and clean the content
                content = match.group(1).strip()
                # Remove subsections (lines starting with ## or ###)
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
        
        # Parse individual segments (### Segment Name (start - end))
        segment_pattern = r'###\s*([^\(]+)\s*\(([^)]+)\)\s*\n(.*?)(?=###|\Z)'
        segment_matches = re.findall(segment_pattern, timing_section, re.DOTALL)
        
        for name_time, time_range, content in segment_matches:
            name = name_time.strip()
            
            # Parse time range (e.g., "0:00 - 0:15" or "0:00 – 0:15" or "0:00 — 0:15")
            # Support hyphen (-), en-dash (–), em-dash (—), and minus sign
            time_match = re.match(r'([^-\u2013\u2014\u2212]+)\s*[-\u2013\u2014\u2212]\s*([^-\u2013\u2014\u2212]+)', time_range.strip())
            if time_match:
                start_time = time_match.group(1).strip()
                end_time = time_match.group(2).strip()
            else:
                start_time = time_range.strip()
                end_time = ""
            
            # Extract duration, purpose, content from segment body
            duration = self._extract_field(content, r'\*\*Duration\*\*:\s*([^\n]+)')
            purpose = self._extract_field(content, r'\*\*Purpose\*\*:\s*([^\n]+)')
            
            # If duration not explicitly stated, try to calculate from time range
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
        
        # Parse categories (### Music, ### SFX, ### VFX, ### Sound Effects)
        # Allow word characters, spaces, and hyphens in category names
        category_pattern = r'###\s*([\w\s-]+?)\s*\n(.*?)(?=###|\Z)'
        category_matches = re.findall(category_pattern, asset_section, re.DOTALL)
        
        for category_name, category_content in category_matches:
            category = category_name.strip()
            
            # Parse individual assets within category
            # Format: - **name**: description
            asset_pattern = r'-\s*\*\*([^*]+)\*\*:\s*([^\n]+(?:\n(?=\s*-\s*\*\*)|$))'
            asset_matches = re.findall(asset_pattern, category_content)
            
            for asset_name, asset_description in asset_matches:
                # Clean up the description (remove trailing newlines)
                description = asset_description.strip()
                
                # Extract search tags from description if present (e.g., "(upbeat, professional, fast-paced)")
                # Allow hyphens in tag names for compound descriptors
                tags: List[str] = []
                tags_match = re.search(r'\(([\w,\s-]+)\)', description)
                if tags_match:
                    tags_str = tags_match.group(1)
                    tags = [t.strip() for t in tags_str.split(',') if t.strip()]
                    # Remove tags from description - only remove if at the end of description
                    description = re.sub(r'\s*\([\w,\s-]+\)$', '', description).strip()
                
                asset_group = AssetGroup(
                    category=category,
                    name=asset_name.strip(),
                    description=description,
                    search_tags=tags
                )
                asset_groups.append(asset_group)
        
        return asset_groups
    
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
        except (ValueError, IndexError):
            return None


class TemplateParserError(Exception):
    """Exception raised for template parser errors."""
    pass
