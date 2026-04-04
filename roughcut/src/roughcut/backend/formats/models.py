"""Data models for format templates.

Defines the FormatTemplate dataclass and related structures for
template metadata management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional


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
        raw_markdown: Full markdown content for display (optional)
    """
    
    slug: str
    name: str
    description: str
    file_path: Path
    structure: str = ""
    segments: List[TemplateSegment] = field(default_factory=list)
    asset_groups: List[AssetGroup] = field(default_factory=list)
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
            # Group by category
            by_category: Dict[str, List[AssetGroup]] = {}
            for ag in self.asset_groups:
                if ag.category not in by_category:
                    by_category[ag.category] = []
                by_category[ag.category].append(ag)
            
            for category in sorted(by_category.keys()):
                lines.append(f"{category}:")
                for ag in by_category[category]:
                    lines.append(f"  - {ag.name}: {ag.description}")
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
        
        return (len(errors) == 0, errors)
    
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
        # Get stem and sanitize - remove any path traversal characters
        stem = file_path.stem
        # Replace any potentially dangerous characters
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
