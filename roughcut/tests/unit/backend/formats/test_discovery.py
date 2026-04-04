# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""Tests for template discovery system."""

import unittest
import tempfile
import os
from pathlib import Path
from datetime import datetime

from roughcut.backend.formats.discovery import (
    TemplateDiscovery,
    DiscoveredTemplate,
    DiscoveryError
)


class TestDiscoveredTemplate(unittest.TestCase):
    """Test DiscoveredTemplate dataclass."""
    
    def test_dataclass_creation(self):
        """Test creating a DiscoveredTemplate instance."""
        dt = DiscoveredTemplate(
            file_path=Path("/templates/formats/test.md"),
            filename="test.md",
            modified_time=1234567890.0,
            relative_path="test.md"
        )
        
        self.assertEqual(dt.file_path, Path("/templates/formats/test.md"))
        self.assertEqual(dt.filename, "test.md")
        self.assertEqual(dt.modified_time, 1234567890.0)
        self.assertEqual(dt.relative_path, "test.md")


class TestTemplateDiscovery(unittest.TestCase):
    """Test TemplateDiscovery class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.temp_dir) / "templates" / "formats"
        self.templates_dir.mkdir(parents=True)
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_creates_directory(self):
        """Test that init creates templates directory if it doesn't exist."""
        nonexistent_dir = Path(self.temp_dir) / "nonexistent" / "templates"
        
        discovery = TemplateDiscovery(templates_dir=nonexistent_dir)
        
        self.assertTrue(nonexistent_dir.exists())
        self.assertTrue(nonexistent_dir.is_dir())
    
    def test_scan_empty_directory(self):
        """Test scanning empty directory returns empty list."""
        discovery = TemplateDiscovery(templates_dir=self.templates_dir)
        
        result = discovery.scan()
        
        self.assertEqual(result, [])
    
    def test_scan_finds_md_files(self):
        """Test scanning finds .md files."""
        # Create test files
        (self.templates_dir / "template1.md").write_text("# Template 1")
        (self.templates_dir / "template2.md").write_text("# Template 2")
        
        discovery = TemplateDiscovery(templates_dir=self.templates_dir)
        
        result = discovery.scan()
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].filename, "template1.md")
        self.assertEqual(result[1].filename, "template2.md")
    
    def test_scan_ignores_non_md_files(self):
        """Test scanning ignores non-.md files."""
        (self.templates_dir / "template.md").write_text("# Template")
        (self.templates_dir / "readme.txt").write_text("Not a template")
        (self.templates_dir / "script.py").write_text("# Python script")
        
        discovery = TemplateDiscovery(templates_dir=self.templates_dir)
        
        result = discovery.scan()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].filename, "template.md")
    
    def test_scan_includes_nested_directories(self):
        """Test scanning includes files in nested subdirectories."""
        nested = self.templates_dir / "corporate"
        nested.mkdir()
        (nested / "interview.md").write_text("# Interview")
        (self.templates_dir / "root.md").write_text("# Root")
        
        discovery = TemplateDiscovery(templates_dir=self.templates_dir)
        
        result = discovery.scan()
        
        self.assertEqual(len(result), 2)
        filenames = [r.filename for r in result]
        self.assertIn("interview.md", filenames)
        self.assertIn("root.md", filenames)
    
    def test_scan_returns_sorted_by_filename(self):
        """Test results are sorted by filename."""
        (self.templates_dir / "zebra.md").write_text("# Zebra")
        (self.templates_dir / "alpha.md").write_text("# Alpha")
        (self.templates_dir / "beta.md").write_text("# Beta")
        
        discovery = TemplateDiscovery(templates_dir=self.templates_dir)
        
        result = discovery.scan()
        
        self.assertEqual(result[0].filename, "alpha.md")
        self.assertEqual(result[1].filename, "beta.md")
        self.assertEqual(result[2].filename, "zebra.md")
    
    def test_scan_captures_modification_time(self):
        """Test scan captures file modification time."""
        template_file = self.templates_dir / "test.md"
        template_file.write_text("# Test")
        
        expected_mtime = template_file.stat().st_mtime
        
        discovery = TemplateDiscovery(templates_dir=self.templates_dir)
        result = discovery.scan()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].modified_time, expected_mtime)
    
    def test_scan_captures_relative_path(self):
        """Test scan captures relative path from templates directory."""
        nested = self.templates_dir / "subdir"
        nested.mkdir()
        (nested / "nested.md").write_text("# Nested")
        
        discovery = TemplateDiscovery(templates_dir=self.templates_dir)
        result = discovery.scan()
        
        nested_result = [r for r in result if r.filename == "nested.md"][0]
        self.assertEqual(nested_result.relative_path, "subdir/nested.md")
    
    def test_default_templates_dir(self):
        """Test default templates directory is 'templates/formats/'."""
        discovery = TemplateDiscovery()
        
        self.assertEqual(discovery.templates_dir, Path("templates/formats/"))
    
    def test_scan_handles_missing_directory(self):
        """Test scan handles missing directory gracefully."""
        missing_dir = Path(self.temp_dir) / "missing"
        # Don't create the directory
        
        discovery = TemplateDiscovery(templates_dir=missing_dir)
        
        # Should not raise, just return empty
        result = discovery.scan()
        self.assertEqual(result, [])


class TestTemplateDiscoverySecurity(unittest.TestCase):
    """Test security aspects of template discovery."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.temp_dir) / "templates" / "formats"
        self.templates_dir.mkdir(parents=True)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_safe_path_validation(self):
        """Test that paths are validated to be within templates directory."""
        discovery = TemplateDiscovery(templates_dir=self.templates_dir)
        
        # Valid path within directory
        valid_path = self.templates_dir / "test.md"
        self.assertTrue(discovery._is_safe_path(valid_path))
        
        # Invalid path outside directory
        outside_path = Path(self.temp_dir) / "outside.md"
        self.assertFalse(discovery._is_safe_path(outside_path))
    
    def test_scan_with_symlinks(self):
        """Test scanning handles symlinks appropriately."""
        # Create a file
        real_file = self.templates_dir / "real.md"
        real_file.write_text("# Real")
        
        # Create a symlink
        link_file = self.templates_dir / "link.md"
        try:
            link_file.symlink_to(real_file)
            
            discovery = TemplateDiscovery(templates_dir=self.templates_dir)
            result = discovery.scan()
            
            # Should handle symlinks (either include or exclude, not crash)
            # The important thing is it doesn't crash
            self.assertIsInstance(result, list)
        except (OSError, NotImplementedError):
            # Symlinks not supported on this platform, skip test
            self.skipTest("Symlinks not supported on this platform")


if __name__ == "__main__":
    unittest.main()
