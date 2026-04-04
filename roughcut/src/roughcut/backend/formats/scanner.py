"""Format template scanner for discovering and loading markdown templates.

Scans the templates/formats/ directory for markdown files and extracts
metadata from YAML frontmatter.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

from .models import FormatTemplate, FormatTemplateCollection


class TemplateScanner:
    """Scans for format templates in a directory.
    
    Discovers markdown files, parses frontmatter, and creates
    FormatTemplate instances with caching support.
    """
    
    def __init__(self, templates_dir: str | Path):
        """Initialize the scanner.
        
        Args:
            templates_dir: Path to the templates/formats/ directory
        """
        self._templates_dir = Path(templates_dir)
        self._cache: Optional[FormatTemplateCollection] = None
        self._cache_mtime: float = 0
    
    def scan(self) -> List[FormatTemplate]:
        """Scan for templates and return list of valid templates.
        
        Uses caching to avoid repeated disk reads. Cache is invalidated
        when directory modification time changes.
        
        Returns:
            List of valid FormatTemplate instances
        """
        # Check if cache is still valid
        current_mtime = self._get_directory_mtime()
        if self._cache is not None and current_mtime <= self._cache_mtime:
            return self._cache.get_all()
        
        # Scan directory for templates
        templates = self._perform_scan()
        
        # Update cache
        self._cache = FormatTemplateCollection(templates)
        self._cache_mtime = current_mtime
        
        return templates
    
    def clear_cache(self) -> None:
        """Clear the template cache.
        
        Forces fresh scan on next call to scan().
        """
        self._cache = None
        self._cache_mtime = 0
    
    def _get_directory_mtime(self) -> float:
        """Get the latest modification time of the templates directory.
        
        Returns:
            Most recent mtime of directory or any .md file within it
        """
        if not self._templates_dir.exists():
            return 0
        
        max_mtime = self._templates_dir.stat().st_mtime
        
        # Check all markdown files
        for md_file in self._templates_dir.glob("*.md"):
            file_mtime = md_file.stat().st_mtime
            if file_mtime > max_mtime:
                max_mtime = file_mtime
        
        return max_mtime
    
    def _perform_scan(self) -> List[FormatTemplate]:
        """Perform actual directory scan.
        
        Returns:
            List of valid FormatTemplate instances
        """
        templates: List[FormatTemplate] = []
        
        if not self._templates_dir.exists():
            return templates
        
        # Find all markdown files
        for md_file in sorted(self._templates_dir.glob("*.md")):
            template = self._parse_template_file(md_file)
            if template is not None:
                templates.append(template)
        
        return templates
    
    def _parse_template_file(self, file_path: Path) -> Optional[FormatTemplate]:
        """Parse a single markdown template file.
        
        Extracts frontmatter metadata and creates FormatTemplate.
        Skips files with missing required fields.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            FormatTemplate if valid, None otherwise
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Parse frontmatter
            frontmatter = self._extract_frontmatter(content)
            if frontmatter is None:
                return None
            
            # Extract required fields
            name = frontmatter.get("name", "").strip()
            description = frontmatter.get("description", "").strip()
            
            # Validate required fields
            if not name or not description:
                return None
            
            # Generate ID from filename
            template_id = FormatTemplate.id_from_path(file_path)
            
            return FormatTemplate(
                id=template_id,
                name=name,
                description=description,
                file_path=file_path
            )
            
        except Exception:
            # Skip files that can't be read or parsed
            return None
    
    def _extract_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract YAML frontmatter from markdown content.
        
        Frontmatter format:
            ---
            name: "Template Name"
            description: "Template description"
            ---
        
        Args:
            content: Full markdown file content
            
        Returns:
            Dictionary of frontmatter data or None if invalid
        """
        if not content.startswith("---"):
            return None
        
        # Find the end of frontmatter
        end_marker = content.find("\n---", 3)
        if end_marker == -1:
            return None
        
        # Extract YAML content
        yaml_content = content[3:end_marker].strip()
        
        try:
            return yaml.safe_load(yaml_content) or {}
        except yaml.YAMLError:
            return None


class TemplateScannerError(Exception):
    """Exception raised for template scanner errors."""
    pass
