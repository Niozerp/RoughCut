"""Tests for Transcript data models."""

import pytest
from datetime import datetime

from roughcut.backend.database.models import Transcript, TranscriptSegment


class TestTranscriptSegment:
    """Tests for TranscriptSegment dataclass."""
    
    def test_basic_creation(self):
        """Test creating a transcript segment."""
        segment = TranscriptSegment(
            start_time=0.0,
            end_time=5.5,
            text="Hello world",
            speaker="Speaker 1"
        )
        
        assert segment.start_time == 0.0
        assert segment.end_time == 5.5
        assert segment.text == "Hello world"
        assert segment.speaker == "Speaker 1"
    
    def test_optional_speaker(self):
        """Test creating a segment without speaker label."""
        segment = TranscriptSegment(
            start_time=10.0,
            end_time=15.0,
            text="No speaker label here"
        )
        
        assert segment.speaker is None
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        segment = TranscriptSegment(
            start_time=1.5,
            end_time=3.0,
            text="Test text",
            speaker="John"
        )
        
        data = segment.to_dict()
        
        assert data['start_time'] == 1.5
        assert data['end_time'] == 3.0
        assert data['text'] == "Test text"
        assert data['speaker'] == "John"
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            'start_time': 2.0,
            'end_time': 4.5,
            'text': "From dict",
            'speaker': "Speaker 2"
        }
        
        segment = TranscriptSegment.from_dict(data)
        
        assert segment.start_time == 2.0
        assert segment.end_time == 4.5
        assert segment.text == "From dict"
        assert segment.speaker == "Speaker 2"
    
    def test_from_dict_no_speaker(self):
        """Test deserialization without speaker field."""
        data = {
            'start_time': 0.0,
            'end_time': 1.0,
            'text': "No speaker"
        }
        
        segment = TranscriptSegment.from_dict(data)
        
        assert segment.speaker is None


class TestTranscript:
    """Tests for Transcript dataclass."""
    
    def test_basic_creation(self):
        """Test creating a transcript."""
        transcript = Transcript(
            text="Hello world this is a test",
            word_count=6,
            duration_seconds=10.5,
            has_speaker_labels=False,
            confidence_score=0.95
        )
        
        assert transcript.text == "Hello world this is a test"
        assert transcript.word_count == 6
        assert transcript.duration_seconds == 10.5
        assert transcript.has_speaker_labels is False
        assert transcript.confidence_score == 0.95
        assert transcript.segments is None
    
    def test_creation_with_segments(self):
        """Test creating a transcript with segments."""
        segments = [
            TranscriptSegment(
                start_time=0.0,
                end_time=5.0,
                text="First segment",
                speaker="Speaker 1"
            ),
            TranscriptSegment(
                start_time=5.0,
                end_time=10.0,
                text="Second segment",
                speaker="Speaker 2"
            )
        ]
        
        transcript = Transcript(
            text="First segment Second segment",
            word_count=4,
            duration_seconds=10.0,
            has_speaker_labels=True,
            segments=segments
        )
        
        assert transcript.has_speaker_labels is True
        assert len(transcript.segments) == 2
        assert transcript.segments[0].speaker == "Speaker 1"
        assert transcript.segments[1].speaker == "Speaker 2"
    
    def test_validation_negative_word_count(self):
        """Test that negative word count raises ValueError."""
        with pytest.raises(ValueError, match="word_count must be >= 0"):
            Transcript(
                text="Test",
                word_count=-1,
                duration_seconds=5.0
            )
    
    def test_validation_zero_duration(self):
        """Test that zero duration raises ValueError."""
        with pytest.raises(ValueError, match="duration_seconds must be > 0"):
            Transcript(
                text="Test",
                word_count=1,
                duration_seconds=0.0
            )
    
    def test_validation_negative_duration(self):
        """Test that negative duration raises ValueError."""
        with pytest.raises(ValueError, match="duration_seconds must be > 0"):
            Transcript(
                text="Test",
                word_count=1,
                duration_seconds=-5.0
            )
    
    def test_validation_confidence_score_out_of_range(self):
        """Test that confidence score out of 0-1 range raises ValueError."""
        with pytest.raises(ValueError, match="confidence_score must be between 0.0 and 1.0"):
            Transcript(
                text="Test",
                word_count=1,
                duration_seconds=5.0,
                confidence_score=1.5
            )
    
    def test_validation_confidence_score_negative(self):
        """Test that negative confidence score raises ValueError."""
        with pytest.raises(ValueError, match="confidence_score must be between 0.0 and 1.0"):
            Transcript(
                text="Test",
                word_count=1,
                duration_seconds=5.0,
                confidence_score=-0.1
            )
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        transcript = Transcript(
            text="Test transcript",
            word_count=2,
            duration_seconds=3.0,
            has_speaker_labels=False,
            confidence_score=0.88
        )
        
        data = transcript.to_dict()
        
        assert data['text'] == "Test transcript"
        assert data['word_count'] == 2
        assert data['duration_seconds'] == 3.0
        assert data['has_speaker_labels'] is False
        assert data['confidence_score'] == 0.88
        assert data['segments'] is None
    
    def test_to_dict_with_segments(self):
        """Test serialization with segments."""
        segments = [
            TranscriptSegment(
                start_time=0.0,
                end_time=2.0,
                text="Hello",
                speaker="A"
            )
        ]
        
        transcript = Transcript(
            text="Hello",
            word_count=1,
            duration_seconds=2.0,
            has_speaker_labels=True,
            segments=segments
        )
        
        data = transcript.to_dict()
        
        assert data['segments'] is not None
        assert len(data['segments']) == 1
        assert data['segments'][0]['text'] == "Hello"
        assert data['segments'][0]['speaker'] == "A"
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            'text': 'From dictionary',
            'word_count': 3,
            'duration_seconds': 5.5,
            'has_speaker_labels': False,
            'confidence_score': 0.92,
            'segments': None
        }
        
        transcript = Transcript.from_dict(data)
        
        assert transcript.text == "From dictionary"
        assert transcript.word_count == 3
        assert transcript.duration_seconds == 5.5
        assert transcript.has_speaker_labels is False
        assert transcript.confidence_score == 0.92
        assert transcript.segments is None
    
    def test_from_dict_with_segments(self):
        """Test deserialization with segments."""
        data = {
            'text': 'With segments',
            'word_count': 2,
            'duration_seconds': 4.0,
            'has_speaker_labels': True,
            'segments': [
                {
                    'start_time': 0.0,
                    'end_time': 2.0,
                    'text': 'First',
                    'speaker': 'Speaker 1'
                },
                {
                    'start_time': 2.0,
                    'end_time': 4.0,
                    'text': 'Second',
                    'speaker': 'Speaker 2'
                }
            ]
        }
        
        transcript = Transcript.from_dict(data)
        
        assert transcript.segments is not None
        assert len(transcript.segments) == 2
        assert transcript.segments[0].text == "First"
        assert transcript.segments[1].speaker == "Speaker 2"
    
    def test_get_formatted_text_without_segments(self):
        """Test getting formatted text when no segments."""
        transcript = Transcript(
            text="Plain text",
            word_count=2,
            duration_seconds=5.0
        )
        
        formatted = transcript.get_formatted_text()
        assert formatted == "Plain text"
    
    def test_get_formatted_text_with_speakers(self):
        """Test getting formatted text with speaker labels."""
        segments = [
            TranscriptSegment(
                start_time=0.0,
                end_time=3.0,
                text="Hello",
                speaker="Speaker 1"
            ),
            TranscriptSegment(
                start_time=3.0,
                end_time=6.0,
                text="Hi there",
                speaker="Speaker 2"
            )
        ]
        
        transcript = Transcript(
            text="Hello Hi there",
            word_count=3,
            duration_seconds=6.0,
            segments=segments
        )
        
        formatted = transcript.get_formatted_text()
        expected = "Speaker 1: Hello\n\nSpeaker 2: Hi there"
        assert formatted == expected
    
    def test_get_formatted_text_without_speakers(self):
        """Test getting formatted text with segments but no speakers."""
        segments = [
            TranscriptSegment(
                start_time=0.0,
                end_time=3.0,
                text="First part"
            ),
            TranscriptSegment(
                start_time=3.0,
                end_time=6.0,
                text="Second part"
            )
        ]
        
        transcript = Transcript(
            text="First part Second part",
            word_count=4,
            duration_seconds=6.0,
            segments=segments
        )
        
        formatted = transcript.get_formatted_text()
        expected = "First part\n\nSecond part"
        assert formatted == expected
