"""Tests for format template markdown parser.

Tests TemplateParser class and parsing functionality.
"""

import tempfile
from pathlib import Path
from unittest import TestCase

from roughcut.backend.formats.parser import TemplateParser
from roughcut.backend.formats.models import TemplateSegment, AssetGroup


class TestTemplateParser(TestCase):
    """Test cases for TemplateParser."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = TemplateParser()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parse_simple_template(self):
        """Test parsing a simple template with frontmatter only."""
        # Arrange
        content = """---
name: "Test Template"
description: "A test template"
version: "1.0"
---

# Test Template

This is a simple test template.
"""
        file_path = Path(self.temp_dir) / "test.md"
        file_path.write_text(content)
        
        # Act
        template = self.parser.parse_file(file_path)
        
        # Assert
        self.assertIsNotNone(template)
        self.assertEqual(template.slug, "test")
        self.assertEqual(template.name, "Test Template")
        self.assertEqual(template.description, "A test template")
        self.assertEqual(template.structure, "")
        self.assertEqual(len(template.segments), 0)
        self.assertEqual(len(template.asset_groups), 0)
    
    def test_parse_template_with_structure(self):
        """Test parsing template with structure overview."""
        # Arrange
        content = """---
name: "YouTube Interview"
description: "Corporate interview format"
---

# YouTube Interview

## Structure Overview

This format creates engaging interview content.

## Timing Specifications

### Segment 1: Hook (0:00 - 0:15)
- **Duration**: 15 seconds
- **Purpose**: Grab attention immediately

## Asset Groups

### Music
- **intro_music**: High-energy intro (upbeat, professional)
"""
        file_path = Path(self.temp_dir) / "youtube-interview.md"
        file_path.write_text(content)
        
        # Act
        template = self.parser.parse_file(file_path)
        
        # Assert
        self.assertIsNotNone(template)
        self.assertEqual(template.slug, "youtube-interview")
        self.assertIn("This format creates engaging", template.structure)
        self.assertEqual(len(template.segments), 1)
        self.assertEqual(template.segments[0].name, "Hook")
        self.assertEqual(template.segments[0].start_time, "0:00")
        self.assertEqual(template.segments[0].end_time, "0:15")
        self.assertEqual(len(template.asset_groups), 1)
        self.assertEqual(template.asset_groups[0].category, "Music")
        self.assertEqual(template.asset_groups[0].name, "intro_music")
    
    def test_parse_multiple_segments(self):
        """Test parsing template with multiple timing segments."""
        # Arrange
        content = """---
name: "Multi-Segment"
description: "Multiple segments test"
---

## Timing Specifications

### Segment 1: Hook (0:00 - 0:15)
- **Duration**: 15 seconds
- **Purpose**: Hook the viewer

### Segment 2: Main (0:15 - 3:00)
- **Duration**: 2 minutes 45 seconds
- **Purpose**: Main content

### Segment 3: Outro (3:00 - 3:30)
- **Duration**: 30 seconds
- **Purpose**: Call to action
"""
        file_path = Path(self.temp_dir) / "multi-segment.md"
        file_path.write_text(content)
        
        # Act
        template = self.parser.parse_file(file_path)
        
        # Assert
        self.assertIsNotNone(template)
        self.assertEqual(len(template.segments), 3)
        
        # Check first segment
        self.assertEqual(template.segments[0].name, "Hook")
        self.assertEqual(template.segments[0].duration, "15 seconds")
        
        # Check second segment
        self.assertEqual(template.segments[1].name, "Main")
        self.assertEqual(template.segments[1].start_time, "0:15")
        self.assertEqual(template.segments[1].end_time, "3:00")
    
    def test_parse_asset_groups_by_category(self):
        """Test parsing asset groups categorized by type."""
        # Arrange
        content = """---
name: "Asset Test"
description: "Asset groups test"
---

## Asset Groups

### Music
- **intro_music**: Upbeat intro (energetic, corporate)
- **outro_music**: Branded sting (professional)

### SFX
- **whoosh**: Transition sound (swish)
- **chime**: Success sound (bright)

### VFX
- **lower_third**: Name graphic (clean, modern)
"""
        file_path = Path(self.temp_dir) / "asset-test.md"
        file_path.write_text(content)
        
        # Act
        template = self.parser.parse_file(file_path)
        
        # Assert
        self.assertIsNotNone(template)
        self.assertEqual(len(template.asset_groups), 5)
        
        # Check categories
        categories = set(a.category for a in template.asset_groups)
        self.assertEqual(categories, {"Music", "SFX", "VFX"})
        
        # Check search tags
        intro_music = next(a for a in template.asset_groups if a.name == "intro_music")
        self.assertEqual(intro_music.search_tags, ["energetic", "corporate"])
    
    def test_parse_missing_optional_sections(self):
        """Test parsing template without optional sections."""
        # Arrange
        content = """---
name: "Minimal"
description: "Minimal template"
---

# Minimal Template

This has no timing or asset sections.
"""
        file_path = Path(self.temp_dir) / "minimal.md"
        file_path.write_text(content)
        
        # Act
        template = self.parser.parse_file(file_path)
        
        # Assert
        self.assertIsNotNone(template)
        self.assertEqual(template.structure, "")
        self.assertEqual(len(template.segments), 0)
        self.assertEqual(len(template.asset_groups), 0)
    
    def test_parse_missing_required_fields(self):
        """Test that template without required fields returns None."""
        # Arrange
        content = """---
name: ""
description: ""
---

# Empty Template
"""
        file_path = Path(self.temp_dir) / "empty.md"
        file_path.write_text(content)
        
        # Act
        template = self.parser.parse_file(file_path)
        
        # Assert
        self.assertIsNone(template)
    
    def test_parse_no_frontmatter(self):
        """Test parsing file without frontmatter returns None."""
        # Arrange
        content = """# No Frontmatter

This file has no YAML frontmatter.
"""
        file_path = Path(self.temp_dir) / "no-frontmatter.md"
        file_path.write_text(content)
        
        # Act
        template = self.parser.parse_file(file_path)
        
        # Assert
        self.assertIsNone(template)
    
    def test_parse_malformed_frontmatter(self):
        """Test parsing file with malformed frontmatter."""
        # Arrange
        content = """---
name: "Test"
description: Missing closing quote
---

# Test
"""
        file_path = Path(self.temp_dir) / "malformed.md"
        file_path.write_text(content)
        
        # Act
        template = self.parser.parse_file(file_path)
        
        # Assert
        self.assertIsNone(template)  # Should fail due to YAML parse error
    
    def test_parse_nonexistent_file(self):
        """Test parsing non-existent file returns None."""
        # Act
        template = self.parser.parse_file(Path("/nonexistent/file.md"))
        
        # Assert
        self.assertIsNone(template)
    
    def test_calculate_duration(self):
        """Test duration calculation from time range."""
        # Test cases for _calculate_duration
        test_cases = [
            ("0:00", "0:15", "15 seconds"),
            ("0:15", "3:15", "3 minutes"),
            ("0:00", "1:00", "1 minute"),
            ("0:00", "0:30", "30 seconds"),
            ("0:00", "1:30", "1 minute 30 seconds"),
            ("0:00", "1:00:00", "1 hour"),
        ]
        
        for start, end, expected in test_cases:
            result = self.parser._calculate_duration(start, end)
            self.assertEqual(result, expected, f"Duration from {start} to {end}")
    
    def test_time_to_seconds(self):
        """Test time string to seconds conversion."""
        # Test MM:SS format
        self.assertEqual(self.parser._time_to_seconds("0:15"), 15)
        self.assertEqual(self.parser._time_to_seconds("3:15"), 195)
        self.assertEqual(self.parser._time_to_seconds("1:00"), 60)
        
        # Test HH:MM:SS format
        self.assertEqual(self.parser._time_to_seconds("1:00:00"), 3600)
        self.assertEqual(self.parser._time_to_seconds("1:30:00"), 5400)
        
        # Test invalid formats
        self.assertIsNone(self.parser._time_to_seconds("invalid"))
        self.assertIsNone(self.parser._time_to_seconds("0"))
    
    def test_extract_field(self):
        """Test field extraction from content."""
        content = """**Duration**: 15 seconds
**Purpose**: Hook the viewer
**Other**: Some value"""
        
        self.assertEqual(
            self.parser._extract_field(content, r'\*\*Duration\*\*:\s*([^\n]+)'),
            "15 seconds"
        )
        self.assertEqual(
            self.parser._extract_field(content, r'\*\*Purpose\*\*:\s*([^\n]+)'),
            "Hook the viewer"
        )
        self.assertEqual(
            self.parser._extract_field(content, r'\*\*Missing\*\*:\s*([^\n]+)'),
            ""
        )
    
    def test_raw_markdown_preserved(self):
        """Test that raw markdown content is preserved."""
        # Arrange
        content = """---
name: "Raw Test"
description: "Testing raw markdown"
---

# Raw Test

Some content here.
"""
        file_path = Path(self.temp_dir) / "raw-test.md"
        file_path.write_text(content)
        
        # Act
        template = self.parser.parse_file(file_path)
        
        # Assert
        self.assertIsNotNone(template)
        self.assertEqual(template.raw_markdown, content)


class TestTemplateSegment(TestCase):
    """Test cases for TemplateSegment dataclass."""
    
    def test_segment_creation(self):
        """Test creating a TemplateSegment."""
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
    
    def test_segment_to_dict(self):
        """Test converting segment to dictionary."""
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
        """Test creating an AssetGroup."""
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
    
    def test_asset_group_default_tags(self):
        """Test AssetGroup with default empty tags."""
        # Arrange & Act
        asset = AssetGroup(
            category="SFX",
            name="whoosh",
            description="Transition sound"
        )
        
        # Assert
        self.assertEqual(asset.search_tags, [])
    
    def test_asset_group_to_dict(self):
        """Test converting asset group to dictionary."""
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
