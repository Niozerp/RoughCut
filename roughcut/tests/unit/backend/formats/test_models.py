"""Tests for format template data models.

Tests FormatTemplate dataclass and related models.
"""

from pathlib import Path
from unittest import TestCase

from roughcut.backend.formats.models import FormatTemplate


class TestFormatTemplate(TestCase):
    """Test cases for FormatTemplate dataclass."""
    
    def test_format_template_creation(self):
        """Test creating a FormatTemplate instance."""
        # Arrange & Act
        template = FormatTemplate(
            id="test-template",
            name="Test Template",
            description="A test template",
            file_path=Path("/test/template.md")
        )
        
        # Assert
        self.assertEqual(template.id, "test-template")
        self.assertEqual(template.name, "Test Template")
        self.assertEqual(template.description, "A test template")
        self.assertEqual(template.file_path, Path("/test/template.md"))
    
    def test_format_template_to_dict(self):
        """Test converting FormatTemplate to dictionary."""
        # Arrange
        template = FormatTemplate(
            id="youtube-interview",
            name="YouTube Interview",
            description="Corporate interview format",
            file_path=Path("/templates/youtube-interview.md")
        )
        
        # Act
        result = template.to_dict()
        
        # Assert
        self.assertEqual(result["id"], "youtube-interview")
        self.assertEqual(result["name"], "YouTube Interview")
        self.assertEqual(result["description"], "Corporate interview format")
        self.assertNotIn("file_path", result)  # file_path should not be in dict output
    
    def test_format_template_validation_valid(self):
        """Test validation with valid template."""
        # Arrange
        template = FormatTemplate(
            id="valid",
            name="Valid Template",
            description="Has all required fields",
            file_path=Path("/test.md")
        )
        
        # Act
        is_valid, errors = template.validate()
        
        # Assert
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])
    
    def test_format_template_validation_missing_name(self):
        """Test validation catches missing name."""
        # Arrange
        template = FormatTemplate(
            id="invalid",
            name="",
            description="Has description but no name",
            file_path=Path("/test.md")
        )
        
        # Act
        is_valid, errors = template.validate()
        
        # Assert
        self.assertFalse(is_valid)
        self.assertIn("name", str(errors))
    
    def test_format_template_validation_missing_description(self):
        """Test validation catches missing description."""
        # Arrange
        template = FormatTemplate(
            id="invalid",
            name="Invalid Template",
            description="",
            file_path=Path("/test.md")
        )
        
        # Act
        is_valid, errors = template.validate()
        
        # Assert
        self.assertFalse(is_valid)
        self.assertIn("description", str(errors))
    
    def test_format_template_from_file_path_slug(self):
        """Test ID generation from file path."""
        # Arrange
        path = Path("/templates/youtube-interview-corporate.md")
        
        # Act
        template_id = FormatTemplate.id_from_path(path)
        
        # Assert
        self.assertEqual(template_id, "youtube-interview-corporate")
