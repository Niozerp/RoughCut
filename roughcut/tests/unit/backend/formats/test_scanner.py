"""Tests for format template scanner.

Tests file discovery and metadata extraction from markdown templates.
"""

import tempfile
from pathlib import Path
from unittest import TestCase

from roughcut.backend.formats.scanner import TemplateScanner


class TestTemplateScanner(TestCase):
    """Test cases for TemplateScanner."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.scanner = TemplateScanner(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_scan_empty_directory(self):
        """Test scanning empty directory returns empty list."""
        # Act
        templates = self.scanner.scan()
        
        # Assert
        self.assertEqual(templates, [])
    
    def test_scan_single_template(self):
        """Test scanning directory with single template file."""
        # Arrange
        template_content = """---
name: "YouTube Interview"
description: "Corporate interview format"
---

# YouTube Interview Format
"""
        template_path = Path(self.temp_dir) / "youtube-interview.md"
        template_path.write_text(template_content)
        
        # Act
        templates = self.scanner.scan()
        
        # Assert
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0].slug, "youtube-interview")
        self.assertEqual(templates[0].name, "YouTube Interview")
        self.assertEqual(templates[0].description, "Corporate interview format")
    
    def test_scan_multiple_templates(self):
        """Test scanning directory with multiple template files."""
        # Arrange
        templates_data = [
            ("youtube-interview.md", "YouTube Interview", "Corporate interview format"),
            ("documentary-scene.md", "Documentary Scene", "Documentary storytelling"),
            ("social-media-short.md", "Social Media Short", "Short form content"),
        ]
        
        for filename, name, description in templates_data:
            content = f"""---
name: "{name}"
description: "{description}"
---

# {name}
"""
            (Path(self.temp_dir) / filename).write_text(content)
        
        # Act
        templates = self.scanner.scan()
        
        # Assert
        self.assertEqual(len(templates), 3)
        names = [t.name for t in templates]
        self.assertIn("YouTube Interview", names)
        self.assertIn("Documentary Scene", names)
        self.assertIn("Social Media Short", names)
    
    def test_scan_skips_non_markdown_files(self):
        """Test that non-markdown files are skipped."""
        # Arrange
        template_content = """---
name: "Valid Template"
description: "Should be found"
---

# Valid
"""
        (Path(self.temp_dir) / "valid.md").write_text(template_content)
        (Path(self.temp_dir) / "ignore.txt").write_text("not a template")
        (Path(self.temp_dir) / "ignore.py").write_text("# python file")
        
        # Act
        templates = self.scanner.scan()
        
        # Assert
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0].name, "Valid Template")
    
    def test_scan_handles_missing_name_in_frontmatter(self):
        """Test graceful handling of malformed frontmatter."""
        # Arrange
        template_content = """---
description: "Missing name field"
---

# Template
"""
        (Path(self.temp_dir) / "incomplete.md").write_text(template_content)
        
        # Act
        templates = self.scanner.scan()
        
        # Assert
        self.assertEqual(len(templates), 0)  # Should skip incomplete templates
    
    def test_scan_handles_missing_description_in_frontmatter(self):
        """Test graceful handling of frontmatter missing description."""
        # Arrange
        template_content = """---
name: "Missing Description"
---

# Template
"""
        (Path(self.temp_dir) / "incomplete.md").write_text(template_content)
        
        # Act
        templates = self.scanner.scan()
        
        # Assert
        self.assertEqual(len(templates), 0)  # Should skip incomplete templates
    
    def test_scan_caching(self):
        """Test that scan results are cached."""
        # Arrange
        template_content = """---
name: "Cached Template"
description: "Should be cached"
---

# Template
"""
        (Path(self.temp_dir) / "cached.md").write_text(template_content)
        
        # Act - First scan
        templates1 = self.scanner.scan()
        
        # Modify file (but shouldn't affect cached result)
        (Path(self.temp_dir) / "new.md").write_text(template_content.replace("Cached", "New"))
        
        # Act - Second scan (should use cache)
        templates2 = self.scanner.scan()
        
        # Assert - Should still have only 1 template from cache
        self.assertEqual(len(templates2), 1)
        self.assertEqual(templates2[0].name, "Cached Template")
    
    def test_scan_cache_invalidation(self):
        """Test cache invalidation when directory changes."""
        # Arrange
        template_content = """---
name: "Original"
description: "Original template"
---

# Original
"""
        template_path = Path(self.temp_dir) / "original.md"
        template_path.write_text(template_content)
        
        # Act - First scan
        self.scanner.scan()
        
        # Modify existing file
        import time
        time.sleep(0.1)  # Small delay to ensure mtime changes
        template_path.write_text(template_content.replace("Original", "Modified"))
        
        # Force cache clear and rescan
        self.scanner.clear_cache()
        templates = self.scanner.scan()
        
        # Assert
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0].name, "Modified")
