"""Tests for document formatter module.

Tests the DocumentFormatter and DocumentValidator classes for rough cut
formatting and validation.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from roughcut.backend.ai.document_formatter import DocumentFormatter, DocumentValidator, format_rough_cut_document
from roughcut.backend.ai.document_models import (
    MusicSuggestion,
    RoughCutDocument,
    RoughCutSection,
    SFXSuggestion,
    TranscriptSegment,
    VFXSuggestion,
)


class TestDocumentFormatter(unittest.TestCase):
    """Test cases for DocumentFormatter."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a simple document for testing
        seg1 = TranscriptSegment(start_time=0.0, end_time=10.0, text="Welcome to the show", speaker="Host")
        seg2 = TranscriptSegment(start_time=10.0, end_time=20.0, text="Today we discuss AI")
        
        music = MusicSuggestion(
            asset_id="m1",
            name="intro_theme.wav",
            file_path="/music/intro_theme.wav",
            source_folder="music/corporate",
            confidence=0.85,
            reasoning="Upbeat intro music",
            position=0.0,
            fade_in=2.0
        )
        
        sfx = SFXSuggestion(
            asset_id="s1",
            name="whoosh.wav",
            file_path="/sfx/whoosh.wav",
            source_folder="sfx/transitions",
            confidence=0.75,
            reasoning="Transition sound",
            position=10.0,
            track_number=1,
            intended_moment="Scene transition"
        )
        
        vfx = VFXSuggestion(
            asset_id="v1",
            name="lower_third",
            file_path="/templates/lower_third.drp",
            source_folder="templates/lower_thirds",
            confidence=0.90,
            reasoning="Standard lower third",
            position=2.0,
            template_name="Corporate_Lower_Third",
            configurable_params={"title": "Host Name"}
        )
        
        section = RoughCutSection(
            name="intro",
            start_time=0.0,
            end_time=20.0,
            transcript_segments=[seg1, seg2],
            music=music,
            sfx=[sfx],
            vfx=[vfx]
        )
        
        self.document = RoughCutDocument(
            title="Test Interview",
            source_clip="interview.mov",
            format_template="YouTube Interview",
            total_duration=20.0,
            sections=[section],
            assembly_metadata={"pacing_consistency_score": 0.92}
        )
        
        self.formatter = DocumentFormatter(self.document)
    
    def test_format_document_summary(self):
        """Test document summary formatting."""
        summary = self.formatter.format_document_summary()
        
        self.assertIn("Test Interview", summary)
        self.assertIn("interview.mov", summary)
        self.assertIn("YouTube Interview", summary)
        self.assertIn("0:20", summary)  # Duration
        self.assertIn("Music: 1 suggestions", summary)
        self.assertIn("SFX: 1 suggestions", summary)
        self.assertIn("VFX: 1 suggestions", summary)
    
    def test_format_section(self):
        """Test section formatting."""
        section = self.document.sections[0]
        formatted = self.formatter.format_section(section, 0)
        
        self.assertIn("Section 1: INTRO", formatted)
        self.assertIn("Welcome to the show", formatted)
        self.assertIn("Today we discuss AI", formatted)
        self.assertIn("intro_theme.wav", formatted)
        self.assertIn("whoosh.wav", formatted)
    
    def test_format_timeline_ascii(self):
        """Test ASCII timeline formatting."""
        timeline = self.formatter.format_timeline_ascii()
        
        self.assertIn("Timeline Overview", timeline)
        self.assertIn("0:20", timeline)  # Total duration
        self.assertIn("intro", timeline)
    
    def test_format_timeline_empty_document(self):
        """Test timeline formatting with empty document."""
        empty_doc = RoughCutDocument(
            title="Empty",
            source_clip="empty.mov",
            format_template="Standard",
            total_duration=0.0,
            sections=[]
        )
        
        formatter = DocumentFormatter(empty_doc)
        timeline = formatter.format_timeline_ascii()
        
        self.assertIn("No sections", timeline)
    
    def test_format_section_summary(self):
        """Test section summary formatting."""
        section = self.document.sections[0]
        summary = self.formatter.format_section_summary(section, 0)
        
        self.assertIn("1. intro", summary)
        self.assertIn("0:00 - 0:20", summary)
        self.assertIn("♫", summary)  # Music icon
        self.assertIn("2 segments", summary)
    
    def test_format_for_json(self):
        """Test JSON formatting."""
        json_data = self.formatter.format_for_json()
        
        self.assertEqual(json_data["title"], "Test Interview")
        self.assertEqual(json_data["section_count"], 1)
        self.assertIn("summary", json_data)
    
    def test_get_all_formatted_sections(self):
        """Test getting all formatted sections."""
        sections = self.formatter.get_all_formatted_sections()
        
        self.assertEqual(len(sections), 1)
        self.assertIn("INTRO", sections[0])


class TestFormatRoughCutDocument(unittest.TestCase):
    """Test cases for format_rough_cut_document convenience function."""
    
    def setUp(self):
        """Set up test fixtures."""
        section = RoughCutSection(
            name="intro",
            start_time=0.0,
            end_time=15.0,
            transcript_segments=[
                TranscriptSegment(start_time=0.0, end_time=15.0, text="Hello world")
            ]
        )
        
        self.document = RoughCutDocument(
            title="Test",
            source_clip="test.mov",
            format_template="Standard",
            total_duration=15.0,
            sections=[section]
        )
    
    def test_format_full(self):
        """Test full format output."""
        output = format_rough_cut_document(self.document, "full")
        
        self.assertIn("Test", output)
        self.assertIn("test.mov", output)
        self.assertIn("Timeline Overview", output)
        self.assertIn("INTRO", output)
    
    def test_format_summary(self):
        """Test summary format output."""
        output = format_rough_cut_document(self.document, "summary")
        
        self.assertIn("Test", output)
        self.assertIn("Sections:", output)
        self.assertIn("intro", output)
    
    def test_format_timeline(self):
        """Test timeline format output."""
        output = format_rough_cut_document(self.document, "timeline")
        
        self.assertIn("Timeline Overview", output)
        self.assertIn("0:15", output)
    
    def test_format_invalid(self):
        """Test invalid format raises error."""
        with self.assertRaises(ValueError) as ctx:
            format_rough_cut_document(self.document, "invalid")
        
        self.assertIn("Unknown format_type", str(ctx.exception))


class TestDocumentValidator(unittest.TestCase):
    """Test cases for DocumentValidator."""
    
    def test_validate_valid_document(self):
        """Test validating a valid document."""
        section = RoughCutSection(
            name="intro",
            start_time=0.0,
            end_time=15.0,
            transcript_segments=[
                TranscriptSegment(start_time=0.0, end_time=15.0, text="Hello")
            ]
        )
        
        doc = RoughCutDocument(
            title="Valid",
            source_clip="valid.mov",
            format_template="Standard",
            total_duration=15.0,
            sections=[section]
        )
        
        validator = DocumentValidator(doc)
        result = validator.validate()
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_validate_empty_sections(self):
        """Test validating document with no sections."""
        doc = RoughCutDocument(
            title="Empty",
            source_clip="empty.mov",
            format_template="Standard",
            total_duration=0.0,
            sections=[]
        )
        
        validator = DocumentValidator(doc)
        result = validator.validate()
        
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("no sections", result.errors[0].lower())
    
    def test_validate_section_without_transcript(self):
        """Test validating section without transcript."""
        section = RoughCutSection(
            name="empty",
            start_time=0.0,
            end_time=15.0,
            transcript_segments=[]
        )
        
        doc = RoughCutDocument(
            title="Test",
            source_clip="test.mov",
            format_template="Standard",
            total_duration=15.0,
            sections=[section]
        )
        
        validator = DocumentValidator(doc)
        result = validator.validate()
        
        self.assertTrue(result.is_valid)  # Still valid, just warning
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("No transcript", result.warnings[0])
    
    def test_validate_gap_between_sections(self):
        """Test detecting gaps between sections."""
        section1 = RoughCutSection(name="part1", start_time=0.0, end_time=10.0)
        section2 = RoughCutSection(name="part2", start_time=20.0, end_time=30.0)  # 10s gap
        
        doc = RoughCutDocument(
            title="Gaps",
            source_clip="gaps.mov",
            format_template="Standard",
            total_duration=30.0,
            sections=[section1, section2]
        )
        
        validator = DocumentValidator(doc)
        result = validator.validate()
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("gap", result.warnings[0].lower())
    
    def test_is_empty(self):
        """Test checking if document is empty."""
        section = RoughCutSection(name="intro", start_time=0.0, end_time=15.0)
        
        doc_with_nothing = RoughCutDocument(
            title="Empty",
            source_clip="empty.mov",
            format_template="Standard",
            total_duration=15.0,
            sections=[section]
        )
        
        validator = DocumentValidator(doc_with_nothing)
        self.assertTrue(validator.is_empty())
    
    def test_is_not_empty(self):
        """Test checking if document has content."""
        music = MusicSuggestion(
            asset_id="m1", name="music.wav", file_path="/a", source_folder="/b",
            confidence=0.80, reasoning="test", position=0.0
        )
        
        section = RoughCutSection(
            name="intro",
            start_time=0.0,
            end_time=15.0,
            music=music
        )
        
        doc = RoughCutDocument(
            title="Not Empty",
            source_clip="not_empty.mov",
            format_template="Standard",
            total_duration=15.0,
            sections=[section]
        )
        
        validator = DocumentValidator(doc)
        self.assertFalse(validator.is_empty())
    
    def test_has_low_confidence_matches(self):
        """Test finding low confidence matches."""
        low_music = MusicSuggestion(
            asset_id="m1", name="low.wav", file_path="/a", source_folder="/b",
            confidence=0.50, reasoning="low confidence", position=0.0
        )
        
        high_sfx = SFXSuggestion(
            asset_id="s1", name="high.wav", file_path="/a", source_folder="/b",
            confidence=0.90, reasoning="high confidence", position=5.0
        )
        
        section = RoughCutSection(
            name="test",
            start_time=0.0,
            end_time=20.0,
            music=low_music,
            sfx=[high_sfx]
        )
        
        doc = RoughCutDocument(
            title="Mixed",
            source_clip="mixed.mov",
            format_template="Standard",
            total_duration=20.0,
            sections=[section]
        )
        
        validator = DocumentValidator(doc)
        low_matches = validator.has_low_confidence_matches(threshold=0.6)
        
        self.assertEqual(len(low_matches), 1)
        self.assertEqual(low_matches[0][0], "test")  # section name
        self.assertEqual(low_matches[0][1], "low.wav")  # asset name
        self.assertEqual(low_matches[0][2], 0.50)  # confidence


if __name__ == "__main__":
    unittest.main()
