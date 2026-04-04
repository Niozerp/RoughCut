"""Data models for format templates.

Defines the FormatTemplate dataclass and related structures for
template metadata management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass
class FormatTemplate:
    """Represents a video format template.
    
    Attributes:
        id: Unique identifier derived from filename (e.g., "youtube-interview")
        name: Display name from frontmatter (e.g., "YouTube Interview — Corporate")
        description: Brief description from frontmatter
        file_path: Absolute path to the markdown template file
    """
    
    id: str
    name: str
    description: str
    file_path: Path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary for JSON serialization.
        
        Returns:
            Dictionary with id, name, and description (excludes file_path)
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description
        }
    
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
        
        if not self.id or not self.id.strip():
            errors.append("id is required")
        
        return (len(errors) == 0, errors)
    
    @staticmethod
    def id_from_path(file_path: Path) -> str:
        """Generate template ID from file path.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            ID string (filename without extension)
            
        Example:
            Path("/templates/youtube-interview.md") -> "youtube-interview"
        """
        return file_path.stem


@dataclass
class FormatTemplateCollection:
    """Collection of format templates with lookup capabilities.
    
    Attributes:
        templates: List of FormatTemplate instances
    """
    
    templates: List[FormatTemplate] = field(default_factory=list)
    
    def add(self, template: FormatTemplate) -> None:
        """Add a template to the collection.
        
        Args:
            template: FormatTemplate to add
        """
        self.templates.append(template)
    
    def get_by_id(self, template_id: str) -> FormatTemplate | None:
        """Find template by ID.
        
        Args:
            template_id: Template identifier to search for
            
        Returns:
            FormatTemplate if found, None otherwise
        """
        for template in self.templates:
            if template.id == template_id:
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
