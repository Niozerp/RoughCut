# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""Template discovery system for scanning and locating template files."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class DiscoveryError(Exception):
    """Exception raised for template discovery errors."""
    pass


@dataclass
class DiscoveredTemplate:
    """
    Represents a discovered template file on disk.
    
    Attributes:
        file_path: Absolute path to the template file
        filename: Name of the file (e.g., 'template.md')
        modified_time: File modification timestamp (st_mtime)
        relative_path: Path relative to templates/formats/ directory
    """
    file_path: Path
    filename: str
    modified_time: float
    relative_path: str


class TemplateDiscovery:
    """
    Discovers template files in the templates/formats/ directory.
    
    This class handles scanning for markdown template files, supporting
    nested subdirectories and filtering by file type.
    
    Attributes:
        templates_dir: Path to the templates directory (default: templates/formats/)
    
    Example:
        >>> discovery = TemplateDiscovery()
        >>> templates = discovery.scan()
        >>> for template in templates:
        ...     print(f"Found: {template.filename}")
    """
    
    DEFAULT_TEMPLATES_DIR = Path("templates/formats/")
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize the template discovery system.
        
        Args:
            templates_dir: Path to templates directory. If None, uses default.
        
        The templates directory is created if it doesn't exist.
        """
        self.templates_dir = templates_dir or self.DEFAULT_TEMPLATES_DIR
        self._ensure_directory_exists()
    
    def scan(self) -> List[DiscoveredTemplate]:
        """
        Scan for all .md template files in the templates directory.
        
        Recursively searches through subdirectories for markdown files.
        Results are sorted by filename for consistent ordering.
        
        Returns:
            List of DiscoveredTemplate objects, sorted by filename.
            Returns empty list if directory doesn't exist or is empty.
        
        Raises:
            DiscoveryError: If an error occurs during file system access.
        """
        if not self.templates_dir.exists():
            return []
        
        discovered: List[DiscoveredTemplate] = []
        
        try:
            # Use rglob to recursively find all .md files
            for md_file in self.templates_dir.rglob("*.md"):
                # Validate file is safe (within templates directory)
                if not self._is_safe_path(md_file):
                    logger.warning(f"Skipping unsafe path: {md_file}")
                    continue
                
                try:
                    stat = md_file.stat()
                    discovered.append(DiscoveredTemplate(
                        file_path=md_file,
                        filename=md_file.name,
                        modified_time=stat.st_mtime,
                        relative_path=str(md_file.relative_to(self.templates_dir))
                    ))
                except (OSError, ValueError) as e:
                    logger.warning(f"Could not stat file {md_file}: {e}")
                    continue
        
        except OSError as e:
            raise DiscoveryError(f"Failed to scan templates directory: {e}") from e
        
        # Sort by filename for consistent ordering
        return sorted(discovered, key=lambda x: x.filename)
    
    def _ensure_directory_exists(self) -> None:
        """
        Create templates directory if it doesn't exist.
        
        Creates parent directories as needed (mkdir -p behavior).
        """
        self.templates_dir.mkdir(parents=True, exist_ok=True)
    
    def _is_safe_path(self, path: Path) -> bool:
        """
        Validate that a path is within the allowed templates directory.
        
        Prevents path traversal attacks by ensuring the path
        is actually within the templates directory and not a symlink
        pointing outside.
        
        Args:
            path: The path to validate
            
        Returns:
            True if path is safe (within templates_dir), False otherwise
        """
        try:
            # Check if path is a symlink - reject symlinks for security
            if path.is_symlink():
                logger.warning(f"Rejected symlink: {path}")
                return False
            
            # Use absolute() instead of resolve() to avoid following symlinks
            abs_path = path.absolute()
            abs_templates_dir = self.templates_dir.absolute()
            
            # Check path is within templates directory
            try:
                abs_path.relative_to(abs_templates_dir)
            except ValueError:
                return False
            
            return True
        except (OSError, RuntimeError):
            # RuntimeError: resolution failed (e.g., too many symlinks)
            return False
    
    def get_template_path(self, slug: str) -> Path:
        """
        Get the expected file path for a template by slug.
        
        Args:
            slug: Template identifier (e.g., 'youtube-interview')
            
        Returns:
            Path to the template file (may not exist)
            
        Raises:
            ValueError: If slug is empty or contains path separators
        """
        if not slug or not slug.strip():
            raise ValueError("Slug cannot be empty")
        
        # Security: reject slugs with path separators
        if '/' in slug or '\\' in slug or '..' in slug:
            raise ValueError(f"Invalid slug (contains path separators): {slug}")
        
        return self.templates_dir / f"{slug}.md"
    
    def template_exists(self, slug: str) -> bool:
        """
        Check if a template file exists for the given slug.
        
        Args:
            slug: Template identifier
            
        Returns:
            True if template file exists, False otherwise
        """
        try:
            return self.get_template_path(slug).exists()
        except ValueError:
            return False
    
    def get_slug_from_path(self, file_path: Path) -> str:
        """
        Generate a unique slug from a template file path.
        
        Uses relative path for namespacing to handle duplicate filenames
        in different directories (e.g., "corporate/interview.md" becomes
        "corporate-interview").
        
        Args:
            file_path: Path to the template file (should be within templates_dir)
            
        Returns:
            Unique slug string
        """
        try:
            # Get relative path from templates directory
            rel_path = file_path.relative_to(self.templates_dir)
            
            # Convert path to slug: replace separators with dashes
            # e.g., "corporate/interview.md" -> "corporate-interview"
            stem = rel_path.with_suffix('')  # Remove .md
            slug = str(stem).replace('/', '-').replace('\\', '-')
            
            return slug
        except ValueError:
            # File not in templates directory, use filename only
            return file_path.stem
