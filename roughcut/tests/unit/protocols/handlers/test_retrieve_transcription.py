"""Tests for retrieve_transcription protocol handler."""

import pytest
from unittest.mock import patch, MagicMock

from roughcut.protocols.handlers.media import (
    retrieve_transcription,
    _workflow_state,
    _resolve_get_transcription
)
from roughcut.backend.database.models import Transcript, TranscriptSegment


class TestRetrieveTranscription:
    """Tests for retrieve_transcription handler."""
    
    def setup_method(self):
        """Reset workflow state before each test."""
        _workflow_state['selected_clip'] = None
        _workflow_state['mock_transcription'] = None
    
    def test_missing_clip_id(self):
        """Test error when clip_id is missing."""
        result = retrieve_transcription({
            'clip_name': 'test.mp4'
        })
        
        assert 'error' in result
        assert result['error']['code'] == 'INVALID_PARAMS'
        assert 'clip_id is required' in result['error']['message']
    
    def test_no_clip_selected(self):
        """Test error when no clip is selected."""
        result = retrieve_transcription({
            'clip_id': 'clip_001',
            'clip_name': 'test.mp4'
        })
        
        assert 'error' in result
        assert result['error']['code'] == 'CLIP_NOT_SELECTED'
    
    def test_clip_mismatch(self):
        """Test error when clip_id doesn't match selected clip."""
        _workflow_state['selected_clip'] = {
            'clip_id': 'different_clip',
            'file_path': '/path/to/different.mp4',
            'clip_name': 'different.mp4'
        }
        
        result = retrieve_transcription({
            'clip_id': 'clip_001',
            'clip_name': 'test.mp4'
        })
        
        assert 'error' in result
        assert result['error']['code'] == 'CLIP_NOT_SELECTED'
    
    def test_transcription_not_available(self):
        """Test error when transcription is not available in Resolve."""
        _workflow_state['selected_clip'] = {
            'clip_id': 'clip_001',
            'file_path': '/path/to/test.mp4',
            'clip_name': 'test.mp4'
        }
        
        # Ensure no mock transcription is set
        _workflow_state['mock_transcription'] = None
        
        result = retrieve_transcription({
            'clip_id': 'clip_001',
            'clip_name': 'test.mp4'
        })
        
        assert 'error' in result
        assert result['error']['code'] == 'TRANSCRIPTION_NOT_AVAILABLE'
        assert result['error']['recoverable'] is True
        assert 'Resolve' in result['error']['suggestion']
    
    def test_successful_retrieval(self):
        """Test successful transcription retrieval."""
        _workflow_state['selected_clip'] = {
            'clip_id': 'clip_001',
            'file_path': '/path/to/test.mp4',
            'clip_name': 'test.mp4'
        }
        
        # Set up mock transcription data
        mock_transcript = {
            'text': 'Speaker 1: Hello world\nSpeaker 2: Hi there',
            'word_count': 6,
            'duration_seconds': 10.0,
            'has_speaker_labels': True,
            'confidence_score': 0.95,
            'segments': [
                {
                    'start_time': 0.0,
                    'end_time': 3.0,
                    'text': 'Hello world',
                    'speaker': 'Speaker 1'
                },
                {
                    'start_time': 3.0,
                    'end_time': 6.0,
                    'text': 'Hi there',
                    'speaker': 'Speaker 2'
                }
            ]
        }
        _workflow_state['mock_transcription'] = mock_transcript
        
        result = retrieve_transcription({
            'clip_id': 'clip_001',
            'clip_name': 'test.mp4'
        })
        
        assert 'error' not in result
        assert 'result' in result
        assert 'transcript' in result['result']
        assert result['result']['transcript']['word_count'] == 6
        assert result['result']['transcript']['has_speaker_labels'] is True
        assert len(result['result']['transcript']['segments']) == 2
    
    def test_invalid_params_type(self):
        """Test error when params is not a dict."""
        result = retrieve_transcription("not a dict")
        
        assert 'error' in result
        assert result['error']['code'] == 'INVALID_PARAMS'
    
    def test_success_without_segments(self):
        """Test successful retrieval without segment data."""
        _workflow_state['selected_clip'] = {
            'clip_id': 'clip_002',
            'file_path': '/path/to/simple.mp4',
            'clip_name': 'simple.mp4'
        }
        
        mock_transcript = {
            'text': 'Simple transcript text',
            'word_count': 3,
            'duration_seconds': 5.0,
            'has_speaker_labels': False,
            'confidence_score': 0.88,
            'segments': None
        }
        _workflow_state['mock_transcription'] = mock_transcript
        
        result = retrieve_transcription({
            'clip_id': 'clip_002',
            'clip_name': 'simple.mp4'
        })
        
        assert 'error' not in result
        assert 'result' in result
        assert result['result']['transcript']['text'] == 'Simple transcript text'
        assert result['result']['transcript']['has_speaker_labels'] is False
        assert result['result']['transcript']['segments'] is None


class TestResolveGetTranscription:
    """Tests for _resolve_get_transcription helper."""
    
    def setup_method(self):
        """Reset workflow state before each test."""
        _workflow_state['mock_transcription'] = None
    
    def test_returns_mock_when_set(self):
        """Test that mock transcription is returned when set."""
        mock_data = {
            'text': 'Mock transcript',
            'word_count': 2,
            'duration_seconds': 3.0,
            'has_speaker_labels': False,
            'confidence_score': 0.90,
            'segments': None
        }
        _workflow_state['mock_transcription'] = mock_data
        
        result = _resolve_get_transcription('clip_001', '/path/to/clip.mp4')
        
        assert result is not None
        assert result['text'] == 'Mock transcript'
    
    def test_returns_none_when_no_mock(self):
        """Test that None is returned when no mock is set."""
        _workflow_state['mock_transcription'] = None
        
        result = _resolve_get_transcription('clip_001', '/path/to/clip.mp4')
        
        assert result is None


class TestTranscriptIntegration:
    """Integration tests for transcript workflow."""
    
    def setup_method(self):
        """Reset workflow state before each test."""
        _workflow_state['selected_clip'] = None
        _workflow_state['mock_transcription'] = None
    
    def test_full_workflow_with_segments(self):
        """Test complete workflow from selection to retrieval with segments."""
        from roughcut.protocols.handlers.media import select_clip
        
        # Step 1: Select a clip
        select_result = select_clip({
            'clip_id': 'interview_001',
            'file_path': '/projects/interview.mov',
            'clip_name': 'interview_take1'
        })
        
        assert 'error' not in select_result
        assert select_result['selected_clip']['clip_id'] == 'interview_001'
        
        # Step 2: Set up mock transcription
        mock_transcript = Transcript(
            text='Speaker 1: Welcome to the show',
            word_count=5,
            duration_seconds=3.5,
            has_speaker_labels=True,
            confidence_score=0.94,
            segments=[
                TranscriptSegment(
                    start_time=0.0,
                    end_time=3.5,
                    text='Welcome to the show',
                    speaker='Speaker 1'
                )
            ]
        )
        _workflow_state['mock_transcription'] = mock_transcript.to_dict()
        
        # Step 3: Retrieve transcription
        result = retrieve_transcription({
            'clip_id': 'interview_001',
            'clip_name': 'interview_take1'
        })
        
        assert 'error' not in result
        assert 'result' in result
        assert 'transcript' in result['result']
        assert result['result']['transcript']['word_count'] == 5
        assert result['result']['transcript']['has_speaker_labels'] is True
    
    def test_error_recovery_suggestion(self):
        """Test that error response includes actionable suggestion."""
        _workflow_state['selected_clip'] = {
            'clip_id': 'clip_with_no_transcript',
            'file_path': '/path/to/clip.mp4',
            'clip_name': 'untranscribed.mp4'
        }
        
        result = retrieve_transcription({
            'clip_id': 'clip_with_no_transcript',
            'clip_name': 'untranscribed.mp4'
        })
        
        assert 'error' in result
        error = result['error']
        
        # Verify error structure
        assert 'code' in error
        assert 'category' in error
        assert 'message' in error
        assert 'suggestion' in error
        assert 'recoverable' in error
        
        # Verify actionable suggestion
        assert len(error['suggestion']) > 0
        assert 'Transcribe' in error['suggestion'] or 'Resolve' in error['suggestion']
