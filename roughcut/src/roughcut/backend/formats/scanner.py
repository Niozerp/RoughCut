"""Format template scanner for discovering and loading markdown templates.

Scans the templates/formats/ directory for markdown files and extracts
metadata from YAML frontmatter.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

from .models import FormatTemplate, FormatTemplateCollection

logger = logging.getLogger(__name__)

# Maximum file size to read (10MB) to prevent DoS
MAX_FILE_SIZE = 10 * 1024 * 1024
# Maximum number of templates to load to prevent DoS
MAX_TEMPLATES = 1000


class TemplateScanner:
    """Scans for format templates in a directory.
    
    Discovers markdown files, parses frontmatter, and creates
    FormatTemplate instances with caching support.
    """
    
    def __init__(self, templates_dir: str | Path):
        """Initialize the scanner.
        
        Args:
            templates_dir: Path to the templates/formats/ directory
            
        Raises:
            ValueError: If templates_dir is empty or None
        """
        if not templates_dir:
            raise ValueError("templates_dir is required")
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
        # Check if cache is still valid (use strict < to avoid stale cache)
        try:
            current_mtime = self._get_directory_mtime()
        except (OSError, FileNotFoundError, PermissionError) as e:
            logger.warning(f"Failed to get directory mtime: {e}")
            return []
        
        if self._cache is not None and current_mtime < self._cache_mtime:
            return self._cache.get_all()
        
        # Scan directory for templates
        try:
            templates = self._perform_scan()
        except Exception as e:
            logger.error(f"Failed to perform scan: {e}")
            self._cache = None
            return []
        
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
            
        Raises:
            OSError: If directory operations fail
            FileNotFoundError: If directory doesn't exist
            PermissionError: If permission denied
        """
        try:
            if not self._templates_dir.exists():
                return 0
            
            max_mtime = self._templates_dir.stat().st_mtime
        except (OSError, FileNotFoundError, PermissionError) as e:
            logger.warning(f"Failed to stat directory {self._templates_dir}: {e}")
            return 0
        
        # Check all markdown files
        try:
            md_files = list(self._templates_dir.glob("*.md"))
            # Limit number of files to prevent DoS
            if len(md_files) > MAX_TEMPLATES:
                logger.warning(f"Too many template files ({len(md_files)}), limiting to {MAX_TEMPLATES}")
                md_files = md_files[:MAX_TEMPLATES]
            
            for md_file in md_files:
                # Skip symlinks to prevent path traversal
                if md_file.is_symlink():
                    logger.debug(f"Skipping symlink: {md_file}")
                    continue
                
                try:
                    file_mtime = md_file.stat().st_mtime
                    if file_mtime > max_mtime:
                        max_mtime = file_mtime
                except (OSError, PermissionError) as e:
                    logger.debug(f"Failed to stat file {md_file}: {e}")
                    continue
        except OSError as e:
            logger.warning(f"Failed to glob markdown files: {e}")
        
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
        try:
            md_files = list(self._templates_dir.glob("*.md"))
            # Limit number of files to prevent DoS
            if len(md_files) > MAX_TEMPLATES:
                logger.warning(f"Too many template files ({len(md_files)}), limiting to {MAX_TEMPLATES}")
                md_files = md_files[:MAX_TEMPLATES]
        except OSError as e:
            logger.error(f"Failed to glob directory: {e}")
            return templates
        
        for md_file in sorted(md_files):
            # Skip symlinks to prevent path traversal
            if md_file.is_symlink():
                logger.debug(f"Skipping symlink: {md_file}")
                continue
            
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
            # Check file size before reading
            try:
                file_size = file_path.stat().st_size
                if file_size > MAX_FILE_SIZE:
                    logger.warning(f"Skipping large file {file_path}: {file_size} bytes > {MAX_FILE_SIZE}")
                    return None
            except (OSError, FileNotFoundError, PermissionError) as e:
                logger.warning(f"Failed to stat file {file_path}: {e}")
                return None
            
            content = file_path.read_text(encoding="utf-8")
            
            # Parse frontmatter
            frontmatter = self._extract_frontmatter(content)
            if frontmatter is None:
                logger.debug(f"No frontmatter found in {file_path}")
                return None
            
            # Validate frontmatter is a dict
            if not isinstance(frontmatter, dict):
                logger.warning(f"Invalid frontmatter type in {file_path}: {type(frontmatter)}")
                return None
            
            # Extract required fields and convert to string
            name = str(frontmatter.get("name", "")).strip()
            description = str(frontmatter.get("description", "")).strip()
            
            # Validate required fields
            if not name or not description:
                logger.debug(f"Missing required fields in {file_path}")
                return None
            
            # Generate slug from filename with sanitization
            try:
                slug = FormatTemplate.slug_from_path(file_path)
            except Exception as e:
                logger.warning(f"Failed to generate slug for {file_path}: {e}")
                return None
            
            return FormatTemplate(
                slug=slug,
                name=name,
                description=description,
                file_path=file_path
            )
            
        except UnicodeDecodeError as e:
            logger.warning(f"Unicode decode error in {file_path}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to parse template file {file_path}: {e}")
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
        
        # Normalize Windows line endings (CRLF) to Unix (LF) for consistent parsing
        content = content.replace('\r\n', '\n')
        
        # Find the end of frontmatter (first --- on its own line after start)
        # Use regex-like approach to handle --- inside YAML values
        lines = content.split('\n')
        if len(lines) < 2:
            return None
        
        # Find the closing --- (must be on its own line)
        end_idx = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                end_idx = i
                break
        
        if end_idx == -1:
            return None
        
        # Extract YAML content
        yaml_lines = lines[1:end_idx]
        yaml_content = '\n'.join(yaml_lines)
        
        if not yaml_content.strip():
            # Empty frontmatter is valid, return empty dict
            return {}
        
        try:
            result = yaml.safe_load(yaml_content)
            # yaml.safe_load returns None for empty string, convert to dict
            return result if result is not None else {}
        except yaml.YAMLError as e:
            logger.debug(f"YAML parse error: {e}")
            return None
    
    def scan_with_discovery(
        self,
        discovery,
        parser,
        validator
    ) -> List[FormatTemplate]:
        """
        Scan using TemplateDiscovery integration.
        
        This method integrates Story 3.4's discovery system with the
        existing scanner, using namespaced slugs for duplicate handling.
        
        Args:
            discovery: TemplateDiscovery instance
            parser: TemplateParser for parsing files
            validator: TemplateValidator for validation
            
        Returns:
            List of valid FormatTemplate instances
        """
        templates: List[FormatTemplate] = []
        
        try:
            discovered = discovery.scan()
        except Exception as e:
            logger.error(f"Discovery scan failed: {e}")
            return templates
        
        for disc in discovered:
            try:
                # Validate file
                is_valid, errors = validator.validate_template_file(disc.file_path)
                if not is_valid:
                    logger.warning(f"Invalid template file {disc.filename}: {errors}")
                    continue
                
                # Parse template
                template = parser.parse_file(disc.file_path)
                if template is None:
                    logger.debug(f"Failed to parse {disc.filename}")
                    continue
                
                # Use namespaced slug from discovery (handles duplicates)
                template.slug = discovery.get_slug_from_path(disc.file_path)
                
                # Validate template content
                is_valid, validation_errors = validator.validate_template(template)
                if not is_valid:
                    logger.warning(f"Template validation failed for {disc.filename}: {validation_errors}")
                    continue
                
                templates.append(template)
                
            except Exception as e:
                logger.error(f"Error processing {disc.filename}: {e}")
                continue
        
        return templates


class TemplateScannerError(Exception):
    """Exception raised for template scanner errors."""
    pass
