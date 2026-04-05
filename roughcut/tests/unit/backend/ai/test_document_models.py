"""Tests for document models module.

Tests the data structures for rough cut documents, including
TranscriptSegment, AssetSuggestion, and RoughCutDocument.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from roughcut.backend.ai.document_models import (
    AssetSuggestion,
    AssetType,
    ConfidenceLevel,
    DocumentValidationResult,
    MusicSuggestion,
    RoughCutDocument,
    RoughCutSection,
    SFXSuggestion,
    TranscriptSegment,
    VFXSuggestion,
)


class TestTranscriptSegment(unittest.TestCase):
    """Test cases for TranscriptSegment."""
    
    def test_create_basic(self):
        """Test basic segment creation."""
        seg = TranscriptSegment(
            start_time=0.0,
            end_time=15.0,
            text="Hello world"
        )
        
        self.assertEqual(seg.start_time, 0.0)
        self.assertEqual(seg.end_time, 15.0)
        self.assertEqual(seg.text, "Hello world")
        self.assertIsNone(seg.speaker)
        self.assertTrue(seg.segment_id.startswith("seg_"))
    
    def test_create_with_speaker(self):
        """Test segment with speaker."""
        seg = TranscriptSegment(
            start_time=10.0,
            end_time=25.0,
            text="Test transcript",
            speaker="John"
        )
        
        self.assertEqual(seg.speaker, "John")
    
    def test_duration_property(self):
        """Test duration calculation."""
        seg = TranscriptSegment(
            start_time=5.0,
            end_time=20.0,
            text="Test"
        )
        
        self.assertEqual(seg.duration, 15.0)
    
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        seg = TranscriptSegment(
            start_time=125.0,  # 2:05
            end_time=130.0,
            text="Test"
        )
        
        self.assertEqual(seg.format_timestamp(), "2:05")
        self.assertEqual(seg.format_timestamp(65.0), "1:05")
    
    def test_validation_negative_start(self):
        """Test validation of negative start time."""
        with self.assertRaises(ValueError) as ctx:
            TranscriptSegment(
                start_time=-1.0,
                end_time=10.0,
                text="Test"
            )
        
        self.assertIn("negative", str(ctx.exception).lower())
    
    def test_validation_end_before_start(self):
        """Test validation of end before start."""
        with self.assertRaises(ValueError) as ctx:
            TranscriptSegment(
                start_time=10.0,
                end_time=5.0,
                text="Test"
            )
        
        self.assertIn("greater than", str(ctx.exception).lower())
    
    def test_serialization_roundtrip(self):
        """Test serialization/deserialization."""
        original = TranscriptSegment(
            start_time=10.0,
            end_time=20.0,
            text="Test text",
            speaker="Speaker1"
        )
        
        data = original.to_dict()
        restored = TranscriptSegment.from_dict(data)
        
        self.assertEqual(restored.start_time, original.start_time)
        self.assertEqual(restored.end_time, original.end_time)
        self.assertEqual(restored.text, original.text)
        self.assertEqual(restored.speaker, original.speaker)


class TestMusicSuggestion(unittest.TestCase):
    """Test cases for MusicSuggestion."""
    
    def test_create_basic(self):
        """Test basic music suggestion creation."""
        music = MusicSuggestion(
            asset_id="mus_001",
            name="upbeat_theme.wav",
            file_path="/assets/music/upbeat_theme.wav",
            source_folder="music/corporate",
            confidence=0.85,
            reasoning="Matches corporate intro tone",
            position=0.0
        )
        
        self.assertEqual(music.name, "upbeat_theme.wav")
        self.assertEqual(music.asset_type, AssetType.MUSIC)
        self.assertEqual(music.confidence_level, ConfidenceLevel.HIGH)
    
    def test_confidence_levels(self):
        """Test confidence level calculations."""
        high = MusicSuggestion(
            asset_id="1", name="high.wav", file_path="/a", source_folder="/b",
            confidence=0.85, reasoning="test", position=0.0
        )
        medium = MusicSuggestion(
            asset_id="2", name="med.wav", file_path="/a", source_folder="/b",
            confidence=0.70, reasoning="test", position=0.0
        )
        low = MusicSuggestion(
            asset_id="3", name="low.wav", file_path="/a", source_folder="/b",
            confidence=0.50, reasoning="test", position=0.0
        )
        
        self.assertEqual(high.confidence_level, ConfidenceLevel.HIGH)
        self.assertEqual(medium.confidence_level, ConfidenceLevel.MEDIUM)
        self.assertEqual(low.confidence_level, ConfidenceLevel.LOW)
    
    def test_validation_invalid_confidence(self):
        """Test validation of invalid confidence."""
        with self.assertRaises(ValueError):
            MusicSuggestion(
                asset_id="1",
                name="test.wav",
                file_path="/a",
                source_folder="/b",
                confidence=1.5,  # Invalid
                reasoning="test",
                position=0.0
            )
    
    def test_with_fade(self):
        """Test music with fade in/out."""
        music = MusicSuggestion(
            asset_id="mus_001",
            name="theme.wav",
            file_path="/assets/theme.wav",
            source_folder="music",
            confidence=0.80,
            reasoning="test",
            position=0.0,
            fade_in=2.0,
            fade_out=3.0,
            volume_adjustment=-3.0
        )
        
        self.assertEqual(music.fade_in, 2.0)
        self.assertEqual(music.fade_out, 3.0)
        self.assertEqual(music.volume_adjustment, -3.0)
    
    def test_serialization_roundtrip(self):
        """Test serialization/deserialization."""
        original = MusicSuggestion(
            asset_id="mus_001",
            name="theme.wav",
            file_path="/assets/theme.wav",
            source_folder="music",
            confidence=0.85,
            reasoning="Great match",
            position=15.0,
            fade_in=2.0
        )
        
        data = original.to_dict()
        restored = MusicSuggestion.from_dict(data)
        
        self.assertEqual(restored.name, original.name)
        self.assertEqual(restored.confidence, original.confidence)
        self.assertEqual(restored.fade_in, original.fade_in)


class TestSFXSuggestion(unittest.TestCase):
    """Test cases for SFXSuggestion."""
    
    def test_create_basic(self):
        """Test basic SFX suggestion creation."""
        sfx = SFXSuggestion(
            asset_id="sfx_001",
            name="whoosh.wav",
            file_path="/assets/sfx/whoosh.wav",
            source_folder="sfx/transitions",
            confidence=0.75,
            reasoning="Good for intro",
            position=0.0,
            track_number=1
        )
        
        self.assertEqual(sfx.name, "whoosh.wav")
        self.assertEqual(sfx.asset_type, AssetType.SFX)
        self.assertEqual(sfx.track_number, 1)
    
    def test_with_intended_moment(self):
        """Test SFX with intended moment description."""
        sfx = SFXSuggestion(
            asset_id="sfx_001",
            name="chime.wav",
            file_path="/a",
            source_folder="sfx",
            confidence=0.80,
            reasoning="test",
            position=5.0,
            intended_moment="Transition point after hook"
        )
        
        self.assertEqual(sfx.intended_moment, "Transition point after hook")
    
    def test_validation_invalid_track(self):
        """Test validation of invalid track number."""
        with self.assertRaises(ValueError):
            SFXSuggestion(
                asset_id="1",
                name="test.wav",
                file_path="/a",
                source_folder="/b",
                confidence=0.80,
                reasoning="test",
                position=0.0,
                track_number=0  # Invalid
            )


class TestVFXSuggestion(unittest.TestCase):
    """Test cases for VFXSuggestion."""
    
    def test_create_basic(self):
        """Test basic VFX suggestion creation."""
        vfx = VFXSuggestion(
            asset_id="vfx_001",
            name="lower_third",
            file_path="/templates/lower_third.drp",
            source_folder="templates/lower_thirds",
            confidence=0.90,
            reasoning="Standard corporate lower third",
            position=5.0,
            template_name="Corporate_Lower_Third_v1"
        )
        
        self.assertEqual(vfx.template_name, "Corporate_Lower_Third_v1")
        self.assertEqual(vfx.asset_type, AssetType.VFX)
    
    def test_with_configurable_params(self):
        """Test VFX with configurable parameters."""
        vfx = VFXSuggestion(
            asset_id="vfx_001",
            name="title_card",
            file_path="/a",
            source_folder="templates",
            confidence=0.85,
            reasoning="test",
            position=0.0,
            template_name="Title_Card",
            configurable_params={
                "title_text": "Introduction",
                "subtitle_text": "Episode 1",
                "color_scheme": "blue"
            }
        )
        
        self.assertEqual(vfx.configurable_params["title_text"], "Introduction")


class TestRoughCutSection(unittest.TestCase):
    """Test cases for RoughCutSection."""
    
    def test_create_basic(self):
        """Test basic section creation."""
        section = RoughCutSection(
            name="intro",
            start_time=0.0,
            end_time=15.0
        )
        
        self.assertEqual(section.name, "intro")
        self.assertEqual(section.duration, 15.0)
        self.assertEqual(len(section.transcript_segments), 0)
    
    def test_create_with_content(self):
        """Test section with all content types."""
        seg = TranscriptSegment(start_time=0.0, end_time=10.0, text="Hello")
        music = MusicSuggestion(
            asset_id="m1", name="music.wav", file_path="/a", source_folder="/b",
            confidence=0.80, reasoning="test", position=0.0
        )
        sfx = SFXSuggestion(
            asset_id="s1", name="sfx.wav", file_path="/a", source_folder="/b",
            confidence=0.75, reasoning="test", position=5.0
        )
        vfx = VFXSuggestion(
            asset_id="v1", name="vfx", file_path="/a", source_folder="/b",
            confidence=0.90, reasoning="test", position=2.0
        )
        
        section = RoughCutSection(
            name="intro",
            start_time=0.0,
            end_time=15.0,
            transcript_segments=[seg],
            music=music,
            sfx=[sfx],
            vfx=[vfx]
        )
        
        self.assertEqual(len(section.transcript_segments), 1)
        self.assertIsNotNone(section.music)
        self.assertEqual(len(section.sfx), 1)
        self.assertEqual(len(section.vfx), 1)
    
    def test_format_time_range(self):
        """Test time range formatting."""
        section = RoughCutSection(
            name="intro",
            start_time=0.0,
            end_time=75.0  # 1:15
        )
        
        self.assertEqual(section.format_time_range(), "0:00 - 1:15")
    
    def test_transcript_text_property(self):
        """Test full transcript text property."""
        section = RoughCutSection(
            name="intro",
            start_time=0.0,
            end_time=30.0,
            transcript_segments=[
                TranscriptSegment(start_time=0.0, end_time=10.0, text="Hello"),
                TranscriptSegment(start_time=10.0, end_time=20.0, text="world")
            ]
        )
        
        self.assertEqual(section.transcript_text, "Hello world")
    
    def test_validation_invalid_timing(self):
        """Test validation of invalid section timing."""
        with self.assertRaises(ValueError):
            RoughCutSection(
                name="invalid",
                start_time=20.0,
                end_time=10.0  # End before start
            )


class TestRoughCutDocument(unittest.TestCase):
    """Test cases for RoughCutDocument."""
    
    def test_create_basic(self):
        """Test basic document creation."""
        doc = RoughCutDocument(
            title="Test Rough Cut",
            source_clip="interview.mov",
            format_template="YouTube Interview",
            total_duration=240.0
        )
        
        self.assertEqual(doc.title, "Test Rough Cut")
        self.assertEqual(doc.source_clip, "interview.mov")
        self.assertEqual(doc.section_count, 0)
        self.assertTrue(doc.created_at)  # Should have timestamp
    
    def test_create_with_sections(self):
        """Test document with sections."""
        section1 = RoughCutSection(name="intro", start_time=0.0, end_time=15.0)
        section2 = RoughCutSection(name="content", start_time=15.0, end_time=240.0)
        
        doc = RoughCutDocument(
            title="Test",
            source_clip="test.mov",
            format_template="Standard",
            total_duration=240.0,
            sections=[section1, section2]
        )
        
        self.assertEqual(doc.section_count, 2)
    
    def test_suggestion_counts(self):
        """Test suggestion count properties."""
        music = MusicSuggestion(
            asset_id="m1", name="m.wav", file_path="/a", source_folder="/b",
            confidence=0.80, reasoning="test", position=0.0
        )
        sfx1 = SFXSuggestion(
            asset_id="s1", name="s1.wav", file_path="/a", source_folder="/b",
            confidence=0.75, reasoning="test", position=5.0
        )
        sfx2 = SFXSuggestion(
            asset_id="s2", name="s2.wav", file_path="/a", source_folder="/b",
            confidence=0.70, reasoning="test", position=10.0
        )
        
        section = RoughCutSection(
            name="intro",
            start_time=0.0,
            end_time=15.0,
            music=music,
            sfx=[sfx1, sfx2]
        )
        
        doc = RoughCutDocument(
            title="Test",
            source_clip="test.mov",
            format_template="Standard",
            total_duration=15.0,
            sections=[section]
        )
        
        self.assertEqual(doc.total_music_suggestions, 1)
        self.assertEqual(doc.total_sfx_suggestions, 2)
        self.assertEqual(doc.total_vfx_suggestions, 0)
    
    def test_get_all_asset_paths(self):
        """Test getting all asset paths."""
        music = MusicSuggestion(
            asset_id="m1", name="m.wav", file_path="/music/m.wav", source_folder="/music",
            confidence=0.80, reasoning="test", position=0.0
        )
        sfx = SFXSuggestion(
            asset_id="s1", name="s.wav", file_path="/sfx/s.wav", source_folder="/sfx",
            confidence=0.75, reasoning="test", position=5.0
        )
        
        section = RoughCutSection(
            name="intro",
            start_time=0.0,
            end_time=15.0,
            music=music,
            sfx=[sfx]
        )
        
        doc = RoughCutDocument(
            title="Test",
            source_clip="test.mov",
            format_template="Standard",
            total_duration=15.0,
            sections=[section]
        )
        
        paths = doc.get_all_asset_paths()
        self.assertEqual(len(paths), 2)
        self.assertIn("/music/m.wav", paths)
        self.assertIn("/sfx/s.wav", paths)
    
    def test_format_total_duration(self):
        """Test duration formatting."""
        doc = RoughCutDocument(
            title="Test",
            source_clip="test.mov",
            format_template="Standard",
            total_duration=185.0  # 3:05
        )
        
        self.assertEqual(doc.format_total_duration(), "3:05")
    
    def test_serialization_roundtrip(self):
        """Test full document serialization/deserialization."""
        seg = TranscriptSegment(start_time=0.0, end_time=10.0, text="Hello")
        music = MusicSuggestion(
            asset_id="m1", name="music.wav", file_path="/a", source_folder="/b",
            confidence=0.85, reasoning="Great match", position=0.0
        )
        
        section = RoughCutSection(
            name="intro",
            start_time=0.0,
            end_time=15.0,
            transcript_segments=[seg],
            music=music
        )
        
        original = RoughCutDocument(
            title="Test Document",
            source_clip="test.mov",
            format_template="YouTube",
            total_duration=15.0,
            sections=[section],
            assembly_metadata={"confidence": 0.95}
        )
        
        data = original.to_dict()
        restored = RoughCutDocument.from_dict(data)
        
        self.assertEqual(restored.title, original.title)
        self.assertEqual(restored.section_count, original.section_count)
        self.assertEqual(
            restored.sections[0].music.confidence,
            original.sections[0].music.confidence
        )


class TestDocumentValidationResult(unittest.TestCase):
    """Test cases for DocumentValidationResult."""
    
    def test_create_valid(self):
        """Test creating valid result."""
        result = DocumentValidationResult(is_valid=True)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 0)
    
    def test_create_with_issues(self):
        """Test creating result with issues."""
        result = DocumentValidationResult(
            is_valid=False,
            errors=["Missing sections"],
            warnings=["Low confidence match"],
            missing_assets=["/path/to/missing.wav"]
        )
        
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(len(result.missing_assets), 1)
    
    def test_serialization(self):
        """Test serialization."""
        result = DocumentValidationResult(
            is_valid=False,
            errors=["Error 1"],
            warnings=["Warning 1"],
            missing_assets=["/a", "/b"]
        )
        
        data = result.to_dict()
        
        self.assertEqual(data["is_valid"], False)
        self.assertEqual(len(data["errors"]), 1)
        self.assertEqual(len(data["missing_assets"]), 2)


if __name__ == "__main__":
    unittest.main()
