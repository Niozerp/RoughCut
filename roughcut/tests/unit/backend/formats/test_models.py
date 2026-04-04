"""Tests for format template data models.

Tests FormatTemplate dataclass and related models.
"""

from pathlib import Path
from unittest import TestCase

from roughcut.backend.formats.models import FormatTemplate, FormatTemplateCollection


class TestFormatTemplate(TestCase):
    """Test cases for FormatTemplate dataclass."""
    
    def test_format_template_creation(self):
        """Test creating a FormatTemplate instance."""
        # Arrange & Act
        template = FormatTemplate(
            slug="test-template",
            name="Test Template",
            description="A test template",
            file_path=Path("/test/template.md")
        )
        
        # Assert
        self.assertEqual(template.slug, "test-template")
        self.assertEqual(template.name, "Test Template")
        self.assertEqual(template.description, "A test template")
        self.assertEqual(template.file_path, Path("/test/template.md"))
    
    def test_format_template_to_dict(self):
        """Test converting FormatTemplate to dictionary."""
        # Arrange
        template = FormatTemplate(
            slug="youtube-interview",
            name="YouTube Interview",
            description="Corporate interview format",
            file_path=Path("/templates/youtube-interview.md")
        )
        
        # Act
        result = template.to_dict()
        
        # Assert
        self.assertEqual(result["slug"], "youtube-interview")
        self.assertEqual(result["name"], "YouTube Interview")
        self.assertEqual(result["description"], "Corporate interview format")
        self.assertNotIn("file_path", result)  # file_path should not be in dict output
    
    def test_format_template_validation_valid(self):
        """Test validation with valid template."""
        # Arrange
        template = FormatTemplate(
            slug="valid",
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
            slug="invalid",
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
            slug="invalid",
            name="Invalid Template",
            description="",
            file_path=Path("/test.md")
        )
        
        # Act
        is_valid, errors = template.validate()
        
        # Assert
        self.assertFalse(is_valid)
        self.assertIn("description", str(errors))
    
    def test_format_template_validation_missing_slug(self):
        """Test validation catches missing slug."""
        # Arrange
        template = FormatTemplate(
            slug="",
            name="Template Name",
            description="Has name and description but no slug",
            file_path=Path("/test.md")
        )
        
        # Act
        is_valid, errors = template.validate()
        
        # Assert
        self.assertFalse(is_valid)
        self.assertIn("slug", str(errors))
    
    def test_format_template_slug_from_file_path(self):
        """Test slug generation from file path."""
        # Arrange
        path = Path("/templates/youtube-interview-corporate.md")
        
        # Act
        slug = FormatTemplate.slug_from_path(path)
        
        # Assert
        self.assertEqual(slug, "youtube-interview-corporate")
    
    def test_format_template_slug_from_path_sanitizes_traversal(self):
        """Test that slug generation sanitizes path traversal characters."""
        # Arrange
        path = Path("/../../../etc/passwd.md")
        
        # Act
        slug = FormatTemplate.slug_from_path(path)
        
        # Assert - should strip the dangerous characters
        self.assertNotIn("..", slug)
        self.assertNotIn("/", slug)


class TestFormatTemplateCollection(TestCase):
    """Test cases for FormatTemplateCollection."""
    
    def test_add_template(self):
        """Test adding a template to collection."""
        # Arrange
        collection = FormatTemplateCollection()
        template = FormatTemplate(
            slug="test",
            name="Test",
            description="Test template",
            file_path=Path("/test.md")
        )
        
        # Act
        result = collection.add(template)
        
        # Assert
        self.assertTrue(result)
        self.assertEqual(len(collection), 1)
    
    def test_add_duplicate_slug_rejected(self):
        """Test that duplicate slugs are rejected."""
        # Arrange
        collection = FormatTemplateCollection()
        template1 = FormatTemplate(
            slug="test",
            name="Test 1",
            description="First template",
            file_path=Path("/test1.md")
        )
        template2 = FormatTemplate(
            slug="test",
            name="Test 2",
            description="Second template with same slug",
            file_path=Path("/test2.md")
        )
        
        # Act
        result1 = collection.add(template1)
        result2 = collection.add(template2)
        
        # Assert
        self.assertTrue(result1)
        self.assertFalse(result2)  # Duplicate rejected
        self.assertEqual(len(collection), 1)
    
    def test_get_by_slug_found(self):
        """Test finding template by slug when it exists."""
        # Arrange
        collection = FormatTemplateCollection()
        template = FormatTemplate(
            slug="find-me",
            name="Find Me",
            description="Template to find",
            file_path=Path("/find.md")
        )
        collection.add(template)
        
        # Act
        result = collection.get_by_slug("find-me")
        
        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.slug, "find-me")
    
    def test_get_by_slug_not_found(self):
        """Test finding template by slug when it doesn't exist."""
        # Arrange
        collection = FormatTemplateCollection()
        
        # Act
        result = collection.get_by_slug("nonexistent")
        
        # Assert
        self.assertIsNone(result)
    
    def test_get_all_returns_copy(self):
        """Test that get_all returns a copy of the list."""
        # Arrange
        collection = FormatTemplateCollection()
        template = FormatTemplate(
            slug="test",
            name="Test",
            description="Test template",
            file_path=Path("/test.md")
        )
        collection.add(template)
        
        # Act
        all_templates = collection.get_all()
        all_templates.clear()  # Modify the returned list
        
        # Assert - original collection should be unchanged
        self.assertEqual(len(collection), 1)
    
    def test_to_dict_list(self):
        """Test converting collection to list of dicts."""
        # Arrange
        collection = FormatTemplateCollection()
        template = FormatTemplate(
            slug="test",
            name="Test",
            description="Test template",
            file_path=Path("/test.md")
        )
        collection.add(template)
        
        # Act
        result = collection.to_dict_list()
        
        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["slug"], "test")
        self.assertEqual(result[0]["name"], "Test")
        self.assertEqual(result[0]["description"], "Test template")
    
    def test_iteration(self):
        """Test that collection is iterable."""
        # Arrange
        collection = FormatTemplateCollection()
        template = FormatTemplate(
            slug="test",
            name="Test",
            description="Test template",
            file_path=Path("/test.md")
        )
        collection.add(template)
        
        # Act
        slugs = [t.slug for t in collection]
        
        # Assert
        self.assertEqual(slugs, ["test"])
