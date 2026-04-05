"""Unit tests for transcript_cutter module.

Tests TranscriptCutter, TranscriptSegment, and related classes.
"""

import pytest
from roughcut.backend.ai.transcript_segment import (
    FormatCompliance,
    TranscriptCutResult,
    TranscriptSegment,
)
from roughcut.backend.ai.transcript_cutter import TranscriptCutter


class TestTranscriptSegment:
    """Tests for TranscriptSegment dataclass."""
    
    def test_basic_creation(self):
        """Test basic TranscriptSegment creation."""
        segment = TranscriptSegment(
            section_name="intro",
            start_time=0.0,
            end_time=14.8,
            text="Welcome to the show",
            word_count=4,
            source_words_preserved=True
        )
        
        assert segment.section_name == "intro"
        assert segment.start_time == 0.0
        assert segment.end_time == 14.8
        assert segment.text == "Welcome to the show"
        assert segment.word_count == 4
        assert segment.source_words_preserved is True
    
    def test_validate_word_preservation_exact_match(self):
        """Test word preservation validation with exact match."""
        segment = TranscriptSegment(
            section_name="narrative_1",
            start_time=10.0,
            end_time=20.0,
            text="This is a test",
            word_count=4,
            source_words_preserved=False
        )
        
        source_text = "This is a test of the system"
        result = segment.validate_word_preservation(source_text)
        
        assert result is True
    
    def test_validate_word_preservation_partial_match(self):
        """Test word preservation with partial match."""
        segment = TranscriptSegment(
            section_name="outro",
            start_time=100.0,
            end_time=110.0,
            text="Thanks for watching",
            word_count=3,
            source_words_preserved=False
        )
        
        source_text = "Thanks for watching this video"
        result = segment.validate_word_preservation(source_text)
        
        assert result is True
    
    def test_validate_word_preservation_no_match(self):
        """Test word preservation validation with no match."""
        segment = TranscriptSegment(
            section_name="intro",
            start_time=0.0,
            end_time=10.0,
            text="This text is not in source",
            word_count=5,
            source_words_preserved=False
        )
        
        source_text = "Different text entirely"
        result = segment.validate_word_preservation(source_text)
        
        assert result is False
    
    def test_validate_word_preservation_modified_words(self):
        """Test that modified/paraphrased text fails validation."""
        segment = TranscriptSegment(
            section_name="narrative_1",
            start_time=20.0,
            end_time=30.0,
            text="This is a summary",
            word_count=4,
            source_words_preserved=False
        )
        
        # AI paraphrased instead of verbatim
        source_text = "This represents a comprehensive overview"
        result = segment.validate_word_preservation(source_text)
        
        assert result is False
    
    def test_to_dict(self):
        """Test serialization to dict."""
        segment = TranscriptSegment(
            section_name="intro",
            start_time=0.0,
            end_time=15.0,
            text="Test text",
            word_count=2,
            source_words_preserved=True
        )
        
        result = segment.to_dict()
        assert result["section_name"] == "intro"
        assert result["start_time"] == 0.0
        assert result["end_time"] == 15.0
        assert result["text"] == "Test text"
        assert result["word_count"] == 2
        assert result["source_words_preserved"] is True
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "section_name": "outro",
            "start_time": 100.0,
            "end_time": 110.0,
            "text": "Goodbye",
            "word_count": 1,
            "source_words_preserved": True
        }
        
        segment = TranscriptSegment.from_dict(data)
        assert segment.section_name == "outro"
        assert segment.start_time == 100.0
        assert segment.text == "Goodbye"


class TestFormatCompliance:
    """Tests for FormatCompliance dataclass."""
    
    def test_compliant_result(self):
        """Test compliant format result."""
        compliance = FormatCompliance(
            required_sections=3,
            extracted_sections=3,
            compliant=True
        )
        
        assert compliance.required_sections == 3
        assert compliance.extracted_sections == 3
        assert compliance.compliant is True
    
    def test_non_compliant_result(self):
        """Test non-compliant format result."""
        compliance = FormatCompliance(
            required_sections=5,
            extracted_sections=3,
            compliant=False
        )
        
        assert compliance.required_sections == 5
        assert compliance.extracted_sections == 3
        assert compliance.compliant is False


class TestTranscriptCutResult:
    """Tests for TranscriptCutResult dataclass."""
    
    def test_basic_creation(self):
        """Test basic TranscriptCutResult creation."""
        segments = [
            TranscriptSegment(
                section_name="intro",
                start_time=0.0,
                end_time=15.0,
                text="Intro text",
                word_count=2,
                source_words_preserved=True
            )
        ]
        
        compliance = FormatCompliance(
            required_sections=1,
            extracted_sections=1,
            compliant=True
        )
        
        result = TranscriptCutResult(
            segments=segments,
            total_duration=15.0,
            format_compliance=compliance,
            warnings=[]
        )
        
        assert len(result.segments) == 1
        assert result.total_duration == 15.0
        assert result.format_compliance.compliant is True
        assert len(result.warnings) == 0
    
    def test_with_warnings(self):
        """Test result with warnings."""
        segments = []
        compliance = FormatCompliance(
            required_sections=3,
            extracted_sections=2,
            compliant=False
        )
        
        result = TranscriptCutResult(
            segments=segments,
            total_duration=0.0,
            format_compliance=compliance,
            warnings=["Section count mismatch", "Short segments detected"]
        )
        
        assert len(result.warnings) == 2
        assert "Section count mismatch" in result.warnings


class TestTranscriptCutter:
    """Tests for TranscriptCutter class."""
    
    def test_cut_transcript_to_format_basic(self):
        """Test basic transcript cutting."""
        cutter = TranscriptCutter()
        
        transcript = {
            "text": "Welcome to our interview. Today we discuss AI. Thanks for watching.",
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "Welcome to our interview."},
                {"start": 5.0, "end": 15.0, "text": "Today we discuss AI."},
                {"start": 15.0, "end": 20.0, "text": "Thanks for watching."}
            ]
        }
        
        format_template = {
            "slug": "test-format",
            "name": "Test Format",
            "segments": [
                {"name": "intro", "duration": 5, "type": "hook"},
                {"name": "narrative_1", "duration": 10, "type": "main"},
                {"name": "outro", "duration": 5, "type": "cta"}
            ]
        }
        
        ai_response = {
            "segments": [
                {
                    "section_name": "intro",
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "text": "Welcome to our interview."
                },
                {
                    "section_name": "narrative_1",
                    "start_time": 5.0,
                    "end_time": 15.0,
                    "text": "Today we discuss AI."
                },
                {
                    "section_name": "outro",
                    "start_time": 15.0,
                    "end_time": 20.0,
                    "text": "Thanks for watching."
                }
            ]
        }
        
        result = cutter.cut_transcript_to_format(
            transcript=transcript,
            format_template=format_template,
            ai_response=ai_response
        )
        
        assert len(result.segments) == 3
        assert result.format_compliance.compliant is True
        assert result.segments[0].section_name == "intro"
        assert result.segments[0].source_words_preserved is True
    
    def test_word_preservation_validation(self):
        """Test that word modifications are detected."""
        cutter = TranscriptCutter()
        
        transcript = {
            "text": "Original text here",
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "Original text here"}
            ]
        }
        
        format_template = {
            "slug": "test",
            "name": "Test",
            "segments": [
                {"name": "intro", "duration": 5, "type": "hook"}
            ]
        }
        
        # AI modified the words
        ai_response = {
            "segments": [
                {
                    "section_name": "intro",
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "text": "Modified text here"  # Different from source
                }
            ]
        }
        
        result = cutter.cut_transcript_to_format(
            transcript=transcript,
            format_template=format_template,
            ai_response=ai_response
        )
        
        # Should detect word modification
        assert result.segments[0].source_words_preserved is False
        # Should have warning
        assert any("word modification" in w.lower() for w in result.warnings)
    
    def test_section_count_mismatch(self):
        """Test handling of section count mismatch."""
        cutter = TranscriptCutter()
        
        transcript = {
            "text": "Short transcript",
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "Short transcript"}
            ]
        }
        
        format_template = {
            "slug": "test",
            "name": "Test",
            "segments": [
                {"name": "intro", "duration": 5, "type": "hook"},
                {"name": "narrative_1", "duration": 10, "type": "main"},
                {"name": "narrative_2", "duration": 10, "type": "main"}
            ]
        }
        
        # AI only returned 1 segment instead of 3
        ai_response = {
            "segments": [
                {
                    "section_name": "intro",
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "text": "Short transcript"
                }
            ]
        }
        
        result = cutter.cut_transcript_to_format(
            transcript=transcript,
            format_template=format_template,
            ai_response=ai_response
        )
        
        assert result.format_compliance.compliant is False
        assert result.format_compliance.required_sections == 3
        assert result.format_compliance.extracted_sections == 1
    
    def test_empty_transcript_handling(self):
        """Test handling of empty transcript."""
        cutter = TranscriptCutter()
        
        transcript = {
            "text": "",
            "segments": []
        }
        
        format_template = {
            "slug": "test",
            "name": "Test",
            "segments": [
                {"name": "intro", "duration": 5, "type": "hook"}
            ]
        }
        
        ai_response = {
            "segments": []
        }
        
        result = cutter.cut_transcript_to_format(
            transcript=transcript,
            format_template=format_template,
            ai_response=ai_response
        )
        
        assert len(result.segments) == 0
        assert "empty transcript" in " ".join(result.warnings).lower()
    
    def test_segment_boundary_validation(self):
        """Test validation of segment boundaries."""
        cutter = TranscriptCutter()
        
        transcript = {
            "text": "Test transcript with timestamps",
            "segments": [
                {"start": 0.0, "end": 10.0, "text": "Test transcript"}
            ]
        }
        
        format_template = {
            "slug": "test",
            "name": "Test",
            "segments": [
                {"name": "intro", "duration": 10, "type": "hook"}
            ]
        }
        
        # AI returned invalid boundaries (end before start)
        ai_response = {
            "segments": [
                {
                    "section_name": "intro",
                    "start_time": 10.0,
                    "end_time": 5.0,  # Invalid: end before start
                    "text": "Test transcript"
                }
            ]
        }
        
        result = cutter.cut_transcript_to_format(
            transcript=transcript,
            format_template=format_template,
            ai_response=ai_response
        )
        
        # Should detect invalid boundaries
        assert any("invalid" in w.lower() for w in result.warnings)
    
    def test_word_count_calculation(self):
        """Test automatic word count calculation."""
        cutter = TranscriptCutter()
        
        transcript = {
            "text": "One two three four five",
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "One two three four five"}
            ]
        }
        
        format_template = {
            "slug": "test",
            "name": "Test",
            "segments": [
                {"name": "intro", "duration": 5, "type": "hook"}
            ]
        }
        
        ai_response = {
            "segments": [
                {
                    "section_name": "intro",
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "text": "One two three four five"
                }
            ]
        }
        
        result = cutter.cut_transcript_to_format(
            transcript=transcript,
            format_template=format_template,
            ai_response=ai_response
        )
        
        assert result.segments[0].word_count == 5
