"""Tests for format template data models.

Tests FormatTemplate dataclass and related models.
"""

from pathlib import Path
from unittest import TestCase

from roughcut.backend.formats.models import FormatTemplate, FormatTemplateCollection, TemplateSegment, AssetGroup


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
    
    def test_format_template_with_structure_data(self):
        """Test creating FormatTemplate with structure data."""
        # Arrange
        segments = [
            TemplateSegment("Hook", "0:00", "0:15", "15 seconds", "Grab attention"),
            TemplateSegment("Outro", "3:15", "3:45", "30 seconds", "Call to action")
        ]
        assets = [
            AssetGroup("Music", "intro_music", "Upbeat intro", ["upbeat", "corporate"])
        ]
        
        # Act
        template = FormatTemplate(
            slug="structured",
            name="Structured Template",
            description="Has structure data",
            file_path=Path("/test.md"),
            structure="Three act format",
            segments=segments,
            asset_groups=assets,
            raw_markdown="# Full content"
        )
        
        # Assert
        self.assertEqual(template.structure, "Three act format")
        self.assertEqual(len(template.segments), 2)
        self.assertEqual(len(template.asset_groups), 1)
        self.assertEqual(template.raw_markdown, "# Full content")
    
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
    
    def test_format_template_to_preview_dict(self):
        """Test converting FormatTemplate to preview dictionary."""
        # Arrange
        segments = [
            TemplateSegment("Hook", "0:00", "0:15", "15s", "Grab attention")
        ]
        assets = [
            AssetGroup("Music", "intro", "Intro music", ["upbeat"])
        ]
        template = FormatTemplate(
            slug="preview-test",
            name="Preview Test",
            description="Test preview",
            file_path=Path("/test.md"),
            structure="Test structure",
            segments=segments,
            asset_groups=assets
        )
        
        # Act
        result = template.to_preview_dict()
        
        # Assert
        self.assertEqual(result["slug"], "preview-test")
        self.assertEqual(result["name"], "Preview Test")
        self.assertEqual(result["structure"], "Test structure")
        self.assertEqual(len(result["segments"]), 1)
        self.assertEqual(len(result["asset_groups"]), 1)
        self.assertIn("formatted_display", result)
    
    def test_format_template_formatted_display(self):
        """Test formatted display text generation."""
        # Arrange
        segments = [
            TemplateSegment("Hook", "0:00", "0:15", "15 seconds", "Grab attention"),
            TemplateSegment("Main", "0:15", "3:15", "3 minutes", "Core content")
        ]
        assets = [
            AssetGroup("Music", "intro_music", "Upbeat intro", ["upbeat"]),
            AssetGroup("Music", "outro_music", "Outro sting", []),
            AssetGroup("SFX", "whoosh", "Transition", ["swish"])
        ]
        template = FormatTemplate(
            slug="display-test",
            name="Display Test",
            description="Test",
            file_path=Path("/test.md"),
            segments=segments,
            asset_groups=assets
        )
        
        # Act
        display = template._format_display_text()
        
        # Assert
        self.assertIn("=== TIMING ===", display)
        self.assertIn("Hook: 0:00-0:15 (15 seconds)", display)
        self.assertIn("Main: 0:15-3:15 (3 minutes)", display)
        self.assertIn("=== ASSETS ===", display)
        self.assertIn("Music:", display)
        self.assertIn("SFX:", display)
        self.assertIn("intro_music:", display)
    
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


class TestTemplateSegment(TestCase):
    """Test cases for TemplateSegment dataclass."""
    
    def test_template_segment_creation(self):
        """Test creating TemplateSegment."""
        # Arrange & Act
        segment = TemplateSegment(
            name="Hook",
            start_time="0:00",
            end_time="0:15",
            duration="15 seconds",
            purpose="Grab attention"
        )
        
        # Assert
        self.assertEqual(segment.name, "Hook")
        self.assertEqual(segment.start_time, "0:00")
        self.assertEqual(segment.end_time, "0:15")
        self.assertEqual(segment.duration, "15 seconds")
        self.assertEqual(segment.purpose, "Grab attention")
    
    def test_template_segment_to_dict(self):
        """Test converting TemplateSegment to dict."""
        # Arrange
        segment = TemplateSegment(
            name="Narrative",
            start_time="0:15",
            end_time="3:15",
            duration="3 minutes",
            purpose="Main content"
        )
        
        # Act
        result = segment.to_dict()
        
        # Assert
        self.assertEqual(result["name"], "Narrative")
        self.assertEqual(result["start_time"], "0:15")
        self.assertEqual(result["end_time"], "3:15")
        self.assertEqual(result["duration"], "3 minutes")
        self.assertEqual(result["purpose"], "Main content")


class TestAssetGroup(TestCase):
    """Test cases for AssetGroup dataclass."""
    
    def test_asset_group_creation(self):
        """Test creating AssetGroup."""
        # Arrange & Act
        asset = AssetGroup(
            category="Music",
            name="intro_music",
            description="Upbeat corporate intro",
            search_tags=["upbeat", "corporate"]
        )
        
        # Assert
        self.assertEqual(asset.category, "Music")
        self.assertEqual(asset.name, "intro_music")
        self.assertEqual(asset.description, "Upbeat corporate intro")
        self.assertEqual(asset.search_tags, ["upbeat", "corporate"])
    
    def test_asset_group_default_search_tags(self):
        """Test AssetGroup with default empty search_tags."""
        # Arrange & Act
        asset = AssetGroup(
            category="SFX",
            name="whoosh",
            description="Transition sound"
        )
        
        # Assert
        self.assertEqual(asset.search_tags, [])
    
    def test_asset_group_to_dict(self):
        """Test converting AssetGroup to dict."""
        # Arrange
        asset = AssetGroup(
            category="VFX",
            name="lower_third",
            description="Name graphic",
            search_tags=["clean", "modern"]
        )
        
        # Act
        result = asset.to_dict()
        
        # Assert
        self.assertEqual(result["category"], "VFX")
        self.assertEqual(result["name"], "lower_third")
        self.assertEqual(result["description"], "Name graphic")
        self.assertEqual(result["search_tags"], ["clean", "modern"])
