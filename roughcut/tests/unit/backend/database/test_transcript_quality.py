"""Tests for transcript quality analysis functionality.

Tests the quality metrics, classification, and problem area detection
added in Story 4.3 (Review Transcription Quality).
"""

import math
import pytest
from roughcut.backend.database.models import (
    Transcript, 
    TranscriptSegment, 
    TranscriptQuality,
    QualityRating
)


class TestTranscriptQuality:
    """Test suite for transcript quality analysis."""
    
    def test_quality_rating_enum_values(self):
        """Test QualityRating enum has correct values."""
        assert QualityRating.GOOD.value == "good"
        assert QualityRating.FAIR.value == "fair"
        assert QualityRating.POOR.value == "poor"
    
    def test_transcript_quality_defaults(self):
        """Test TranscriptQuality dataclass with default values."""
        quality = TranscriptQuality()
        assert quality.quality_rating == QualityRating.GOOD
        assert quality.confidence_score == 1.0
        assert quality.completeness_pct == 100.0
        assert quality.problem_count == 0
        assert quality.problem_areas == []
        assert quality.recommendation == ""
    
    def test_transcript_quality_custom_values(self):
        """Test TranscriptQuality with custom values."""
        problem_areas = [
            {"type": "inaudible", "position": 100, "text": "[inaudible]"}
        ]
        quality = TranscriptQuality(
            quality_rating=QualityRating.POOR,
            confidence_score=0.45,
            completeness_pct=50.0,
            problem_count=12,
            problem_areas=problem_areas,
            recommendation="Audio cleanup recommended"
        )
        assert quality.quality_rating == QualityRating.POOR
        assert quality.confidence_score == 0.45
        assert quality.completeness_pct == 50.0
        assert quality.problem_count == 12
        assert quality.problem_areas == problem_areas
        assert quality.recommendation == "Audio cleanup recommended"
    
    def test_transcript_quality_to_dict(self):
        """Test TranscriptQuality serialization to dict."""
        problem_areas = [
            {"type": "inaudible", "position": 100, "text": "[inaudible]"}
        ]
        quality = TranscriptQuality(
            quality_rating=QualityRating.FAIR,
            confidence_score=0.75,
            completeness_pct=85.0,
            problem_count=3,
            problem_areas=problem_areas,
            recommendation="Minor issues detected"
        )
        
        result = quality.to_dict()
        
        assert result["quality_rating"] == "fair"
        assert result["confidence_score"] == 0.75
        assert result["completeness_pct"] == 85.0
        assert result["problem_count"] == 3
        assert result["problem_areas"] == problem_areas
        assert result["recommendation"] == "Minor issues detected"
    
    def test_transcript_quality_from_dict(self):
        """Test TranscriptQuality deserialization from dict."""
        data = {
            "quality_rating": "poor",
            "confidence_score": 0.45,
            "completeness_pct": 50.0,
            "problem_count": 12,
            "problem_areas": [
                {"type": "inaudible", "position": 100, "text": "[inaudible]"}
            ],
            "recommendation": "Audio cleanup recommended"
        }
        
        quality = TranscriptQuality.from_dict(data)
        
        assert quality.quality_rating == QualityRating.POOR
        assert quality.confidence_score == 0.45
        assert quality.completeness_pct == 50.0
        assert quality.problem_count == 12
        assert len(quality.problem_areas) == 1
        assert quality.recommendation == "Audio cleanup recommended"
    
    def test_transcript_quality_from_dict_defaults(self):
        """Test TranscriptQuality from_dict with missing fields."""
        data = {}
        
        quality = TranscriptQuality.from_dict(data)
        
        assert quality.quality_rating == QualityRating.GOOD
        assert quality.confidence_score == 1.0
        assert quality.completeness_pct == 100.0
        assert quality.problem_count == 0
        assert quality.problem_areas == []
        assert quality.recommendation == ""
    
    def test_transcript_quality_invalid_rating_string(self):
        """Test from_dict handles invalid rating string gracefully."""
        data = {"quality_rating": "invalid_rating"}
        
        quality = TranscriptQuality.from_dict(data)
        
        # Should default to GOOD when invalid
        assert quality.quality_rating == QualityRating.GOOD


class TestTranscriptQualityAnalysis:
    """Test suite for Transcript quality analysis methods."""
    
    def test_analyze_quality_good_transcript(self):
        """Test quality analysis for a good transcript."""
        transcript = Transcript(
            text="Speaker 1: This is a clean transcript with no issues.",
            word_count=150,
            duration_seconds=60.0,
            has_speaker_labels=True,
            confidence_score=0.95
        )
        
        quality = transcript.analyze_quality()
        
        assert quality.quality_rating == QualityRating.GOOD
        assert quality.confidence_score == 0.95
        assert quality.problem_count == 0
        assert "Good" in quality.recommendation or "good" in quality.recommendation.lower()
    
    def test_analyze_quality_poor_transcript(self):
        """Test quality analysis for a poor transcript with problems."""
        transcript = Transcript(
            text="Speaker 1: Um, so, like... [inaudible]... the thing is... [garbled]... basically...",
            word_count=20,
            duration_seconds=60.0,
            has_speaker_labels=True,
            confidence_score=0.45
        )
        
        quality = transcript.analyze_quality()
        
        assert quality.quality_rating == QualityRating.POOR
        assert quality.confidence_score == 0.45
        assert quality.problem_count >= 2  # Should detect [inaudible] and [garbled]
        assert "cleanup" in quality.recommendation.lower() or "poor" in quality.recommendation.lower()
    
    def test_analyze_quality_fair_transcript(self):
        """Test quality analysis for a fair transcript."""
        transcript = Transcript(
            text="Speaker 1: This is mostly good [inaudible] but has one issue.",
            word_count=100,
            duration_seconds=60.0,
            has_speaker_labels=True,
            confidence_score=0.80
        )
        
        quality = transcript.analyze_quality()
        
        assert quality.quality_rating == QualityRating.FAIR
        assert quality.confidence_score == 0.80
        assert quality.problem_count >= 1
    
    def test_analyze_quality_low_completeness(self):
        """Test quality analysis flags low completeness."""
        # 10 words in 60 seconds = very low word rate
        transcript = Transcript(
            text="Speaker 1: [inaudible] [inaudible] [inaudible]",
            word_count=10,
            duration_seconds=60.0,
            has_speaker_labels=True,
            confidence_score=0.90  # High confidence but low completeness
        )
        
        quality = transcript.analyze_quality()
        
        # Should be POOR due to low completeness despite good confidence
        assert quality.quality_rating == QualityRating.POOR
        assert quality.completeness_pct < 50  # Should calculate low completeness
    
    def test_analyze_quality_no_confidence_score(self):
        """Test quality analysis when confidence score is None."""
        transcript = Transcript(
            text="Speaker 1: Clean transcript without confidence data.",
            word_count=150,
            duration_seconds=60.0,
            has_speaker_labels=True,
            confidence_score=None
        )
        
        quality = transcript.analyze_quality()
        
        # Should analyze based on problem markers only
        assert quality.confidence_score == 0.0  # Default when None
        assert quality.problem_count == 0
    
    def test_find_inaudible_markers(self):
        """Test detection of [inaudible] markers."""
        transcript = Transcript(
            text="Speaker 1: Hello [inaudible] world [inaudible] test.",
            word_count=10,
            duration_seconds=10.0,
            has_speaker_labels=False
        )
        
        markers = transcript._find_inaudible_markers()
        
        assert len(markers) == 2
        assert all(m["type"] == "inaudible" for m in markers)
    
    def test_find_garbled_markers(self):
        """Test detection of [garbled] markers."""
        transcript = Transcript(
            text="Speaker 1: Hello [garbled] world.",
            word_count=5,
            duration_seconds=10.0,
            has_speaker_labels=False
        )
        
        markers = transcript._find_problem_markers()
        
        garbled_markers = [m for m in markers if m["type"] == "garbled"]
        assert len(garbled_markers) == 1
    
    def test_find_multiple_problem_types(self):
        """Test detection of multiple problem marker types."""
        text = """Speaker 1: Hello [inaudible] world [garbled] test 
        [unintelligible] more [crosstalk] end."""
        
        transcript = Transcript(
            text=text,
            word_count=20,
            duration_seconds=20.0,
            has_speaker_labels=False
        )
        
        markers = transcript._find_problem_markers()
        
        types_found = set(m["type"] for m in markers)
        assert "inaudible" in types_found
        assert "garbled" in types_found
        assert "unintelligible" in types_found
        assert "crosstalk" in types_found
    
    def test_calculate_completeness_normal(self):
        """Test completeness calculation for normal transcript."""
        # 150 words in 60 seconds = 150 wpm (normal)
        transcript = Transcript(
            text="Speaker 1: " + "word " * 149,
            word_count=150,
            duration_seconds=60.0,
            has_speaker_labels=False
        )
        
        completeness = transcript._calculate_completeness()
        
        assert 90 <= completeness <= 110  # Should be around 100%
    
    def test_calculate_completeness_low(self):
        """Test completeness calculation for incomplete transcript."""
        # 30 words in 60 seconds = 30 wpm (way too low)
        transcript = Transcript(
            text="Speaker 1: few words here",
            word_count=30,
            duration_seconds=60.0,
            has_speaker_labels=False
        )
        
        completeness = transcript._calculate_completeness()
        
        assert completeness < 50  # Should be flagged as low
    
    def test_calculate_completeness_high(self):
        """Test completeness calculation for very dense transcript."""
        # 300 words in 60 seconds = 300 wpm (auctioneer speed)
        transcript = Transcript(
            text="Speaker 1: " + "word " * 299,
            word_count=300,
            duration_seconds=60.0,
            has_speaker_labels=False
        )
        
        completeness = transcript._calculate_completeness()
        
        assert completeness > 100  # Should be over 100%
    
    def test_quality_rating_from_confidence(self):
        """Test rating classification based on confidence score."""
        transcript = Transcript(
            text="test",
            word_count=10,
            duration_seconds=10.0
        )
        
        # Good: >90%
        assert transcript._quality_rating_from_confidence(0.95) == QualityRating.GOOD
        assert transcript._quality_rating_from_confidence(0.91) == QualityRating.GOOD
        
        # Fair: 70-90%
        assert transcript._quality_rating_from_confidence(0.75) == QualityRating.FAIR
        assert transcript._quality_rating_from_confidence(0.90) == QualityRating.FAIR
        
        # Poor: <70%
        assert transcript._quality_rating_from_confidence(0.69) == QualityRating.POOR
        assert transcript._quality_rating_from_confidence(0.45) == QualityRating.POOR
        assert transcript._quality_rating_from_confidence(0.0) == QualityRating.POOR


class TestTranscriptWithQualityIntegration:
    """Integration tests for Transcript with quality analysis."""
    
    def test_transcript_to_dict_with_quality(self):
        """Test that transcript can include quality in to_dict."""
        transcript = Transcript(
            text="Speaker 1: Test transcript.",
            word_count=10,
            duration_seconds=10.0,
            confidence_score=0.95
        )
        
        # Analyze quality first
        quality = transcript.analyze_quality()
        
        # Convert to dict
        data = transcript.to_dict()
        
        # Verify basic fields
        assert data["text"] == "Speaker 1: Test transcript."
        assert data["confidence_score"] == 0.95
    
    def test_transcript_from_dict_preserves_quality_fields(self):
        """Test that from_dict preserves fields needed for quality analysis."""
        data = {
            "text": "Speaker 1: [inaudible] test [garbled].",
            "word_count": 50,
            "duration_seconds": 30.0,
            "has_speaker_labels": True,
            "confidence_score": 0.65,
            "segments": None
        }
        
        transcript = Transcript.from_dict(data)
        
        # Verify fields needed for quality analysis
        assert transcript.text == "Speaker 1: [inaudible] test [garbled]."
        assert transcript.word_count == 50
        assert transcript.duration_seconds == 30.0
        assert transcript.confidence_score == 0.65
        
        # Should be able to analyze quality
        quality = transcript.analyze_quality()
        assert quality.problem_count >= 2  # Should detect inaudible and garbled
    
    def test_quality_analysis_with_segments(self):
        """Test quality analysis with segmented transcript."""
        segments = [
            TranscriptSegment(start_time=0, end_time=5, text="Hello", speaker="Speaker 1"),
            TranscriptSegment(start_time=5, end_time=10, text="[inaudible]", speaker="Speaker 1"),
            TranscriptSegment(start_time=10, end_time=15, text="World", speaker="Speaker 1"),
        ]
        
        transcript = Transcript(
            text="Speaker 1: Hello [inaudible] World",
            word_count=20,
            duration_seconds=15.0,
            has_speaker_labels=True,
            segments=segments
        )
        
        quality = transcript.analyze_quality()
        
        assert quality.problem_count >= 1  # Should detect the inaudible segment


class TestTranscriptQualityEdgeCases:
    """Edge case tests for quality analysis."""
    
    def test_empty_transcript(self):
        """Test quality analysis with empty transcript."""
        transcript = Transcript(
            text="",
            word_count=0,
            duration_seconds=10.0
        )
        
        quality = transcript.analyze_quality()
        
        assert quality.quality_rating == QualityRating.POOR
        assert quality.completeness_pct == 0.0
    
    def test_very_short_transcript(self):
        """Test quality analysis with very short transcript."""
        transcript = Transcript(
            text="Hi.",
            word_count=1,
            duration_seconds=60.0
        )
        
        quality = transcript.analyze_quality()
        
        assert quality.completeness_pct < 10  # Very low completeness
    
    def test_transcript_with_nan_confidence(self):
        """Test quality analysis handles NaN confidence score."""
        # Should raise ValueError in __post_init__
        with pytest.raises(ValueError, match="NaN"):
            Transcript(
                text="Test",
                word_count=10,
                duration_seconds=10.0,
                confidence_score=float("nan")
            )
    
    def test_transcript_with_invalid_confidence_range(self):
        """Test quality analysis handles out-of-range confidence."""
        # Should raise ValueError in __post_init__
        with pytest.raises(ValueError, match="0.0 and 1.0"):
            Transcript(
                text="Test",
                word_count=10,
                duration_seconds=10.0,
                confidence_score=1.5
            )
    
    def test_problem_markers_case_insensitive(self):
        """Test that problem markers are detected case-insensitively."""
        transcript = Transcript(
            text="Speaker 1: [INAUDIBLE] [Inaudible] [inaudIBLE]",
            word_count=10,
            duration_seconds=10.0
        )
        
        markers = transcript._find_inaudible_markers()
        
        # Should detect all three variations
        assert len(markers) == 3
