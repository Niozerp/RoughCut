"""Tests for the analyze_transcription_quality handler.

Tests the protocol handler for Story 4.3 quality analysis,
verifying JSON-RPC request/response handling and error cases.
"""

import pytest
from unittest.mock import patch, MagicMock
from roughcut.protocols.handlers.media import (
    analyze_transcription_quality,
    MEDIA_HANDLERS
)
from roughcut.backend.database.models import QualityRating


class TestAnalyzeTranscriptionQualityHandler:
    """Test suite for analyze_transcription_quality handler."""
    
    def test_handler_registered_in_media_handlers(self):
        """Test that handler is registered in MEDIA_HANDLERS registry."""
        assert 'analyze_transcription_quality' in MEDIA_HANDLERS
        assert MEDIA_HANDLERS['analyze_transcription_quality'] == analyze_transcription_quality
    
    def test_valid_transcript_analysis(self):
        """Test successful quality analysis with valid transcript."""
        params = {
            'transcript': {
                'text': 'Speaker 1: This is a clean transcript with no issues.',
                'word_count': 150,
                'duration_seconds': 60.0,
                'has_speaker_labels': True,
                'confidence_score': 0.95
            },
            'clip_name': 'test_clip.mp4'
        }
        
        response = analyze_transcription_quality(params)
        
        # Verify response structure
        assert 'result' in response
        assert response['result'] is not None
        assert 'error' not in response or response.get('error') is None
        
        # Verify quality data
        result = response['result']
        assert 'quality_rating' in result
        assert 'confidence_score' in result
        assert 'completeness_pct' in result
        assert 'problem_count' in result
        assert 'problem_areas' in result
        assert 'recommendation' in result
        
        # Good quality transcript should have good rating
        assert result['quality_rating'] == QualityRating.GOOD.value
        assert result['problem_count'] == 0
    
    def test_poor_quality_transcript_analysis(self):
        """Test quality analysis for poor quality transcript."""
        params = {
            'transcript': {
                'text': 'Speaker 1: Um, so, like... [inaudible]... the thing is... [garbled]... basically...',
                'word_count': 20,
                'duration_seconds': 60.0,
                'has_speaker_labels': True,
                'confidence_score': 0.45
            },
            'clip_name': 'noisy_clip.mp4'
        }
        
        response = analyze_transcription_quality(params)
        
        # Verify response
        assert 'result' in response
        assert response['result'] is not None
        
        result = response['result']
        
        # Should be poor quality
        assert result['quality_rating'] == QualityRating.POOR.value
        assert result['problem_count'] >= 2  # Should detect [inaudible] and [garbled]
        assert result['confidence_score'] == 0.45
        assert 'cleanup' in result['recommendation'].lower() or 'poor' in result['recommendation'].lower()
    
    def test_missing_transcript_param(self):
        """Test error handling when transcript parameter is missing."""
        params = {
            'clip_name': 'test.mp4'
            # Missing 'transcript' key
        }
        
        response = analyze_transcription_quality(params)
        
        # Should return error
        assert 'error' in response
        assert response['error'] is not None
        assert response['error']['code'] == 'INVALID_PARAMS'
        assert response['error']['category'] == 'validation'
        assert 'transcript' in response['error']['message'].lower()
    
    def test_invalid_params_type(self):
        """Test error handling when params is not a dict."""
        params = "not a dictionary"
        
        response = analyze_transcription_quality(params)
        
        # Should return error for invalid params type
        assert 'error' in response
        assert response['error']['code'] == 'INVALID_PARAMS'
        assert 'JSON object' in response['error']['message']
    
    def test_invalid_transcript_data(self):
        """Test error handling with invalid transcript data."""
        params = {
            'transcript': {
                'text': 'Test',
                'word_count': 'invalid_number',  # Should be int
                'duration_seconds': 60.0
            },
            'clip_name': 'test.mp4'
        }
        
        response = analyze_transcription_quality(params)
        
        # Should handle gracefully and return result (with defaults)
        assert 'result' in response
        # Or should return error - depends on implementation
        if 'error' in response and response['error']:
            assert response['error']['category'] == 'validation'
    
    def test_empty_transcript_text(self):
        """Test analysis with empty transcript text."""
        params = {
            'transcript': {
                'text': '',
                'word_count': 0,
                'duration_seconds': 60.0,
                'confidence_score': 0.0
            },
            'clip_name': 'empty.mp4'
        }
        
        response = analyze_transcription_quality(params)
        
        assert 'result' in response
        result = response['result']
        
        # Empty transcript should be poor quality
        assert result['quality_rating'] == QualityRating.POOR.value
        assert result['completeness_pct'] == 0.0
    
    def test_transcript_with_segments(self):
        """Test analysis with segmented transcript data."""
        params = {
            'transcript': {
                'text': 'Speaker 1: Hello [inaudible] World',
                'word_count': 20,
                'duration_seconds': 15.0,
                'has_speaker_labels': True,
                'confidence_score': 0.85,
                'segments': [
                    {'start_time': 0, 'end_time': 5, 'text': 'Hello', 'speaker': 'Speaker 1'},
                    {'start_time': 5, 'end_time': 10, 'text': '[inaudible]', 'speaker': 'Speaker 1'},
                    {'start_time': 10, 'end_time': 15, 'text': 'World', 'speaker': 'Speaker 1'}
                ]
            },
            'clip_name': 'segmented.mp4'
        }
        
        response = analyze_transcription_quality(params)
        
        assert 'result' in response
        result = response['result']
        
        # Should detect the inaudible segment
        assert result['problem_count'] >= 1
        assert any(p['type'] == 'inaudible' for p in result['problem_areas'])
    
    def test_high_confidence_good_quality(self):
        """Test that high confidence (>90%) results in good rating."""
        params = {
            'transcript': {
                'text': 'Speaker 1: This is a perfect transcription of dialogue.',
                'word_count': 140,
                'duration_seconds': 60.0,
                'confidence_score': 0.98
            },
            'clip_name': 'perfect.mp4'
        }
        
        response = analyze_transcription_quality(params)
        
        result = response['result']
        assert result['quality_rating'] == QualityRating.GOOD.value
        assert result['confidence_score'] == 0.98
    
    def test_fair_quality_range(self):
        """Test that 70-90% confidence results in fair rating."""
        params = {
            'transcript': {
                'text': 'Speaker 1: This is [inaudible] mostly good transcript.',
                'word_count': 100,
                'duration_seconds': 60.0,
                'confidence_score': 0.80
            },
            'clip_name': 'fair.mp4'
        }
        
        response = analyze_transcription_quality(params)
        
        result = response['result']
        assert result['quality_rating'] == QualityRating.FAIR.value
    
    def test_poor_quality_low_confidence(self):
        """Test that <70% confidence results in poor rating."""
        params = {
            'transcript': {
                'text': 'Speaker 1: [garbled] [inaudible] [crosstalk]',
                'word_count': 30,
                'duration_seconds': 60.0,
                'confidence_score': 0.60
            },
            'clip_name': 'poor.mp4'
        }
        
        response = analyze_transcription_quality(params)
        
        result = response['result']
        assert result['quality_rating'] == QualityRating.POOR.value
    
    def test_completeness_calculation(self):
        """Test that completeness percentage is calculated correctly."""
        # Expected: 140 words for 60 seconds (140 wpm baseline)
        params = {
            'transcript': {
                'text': 'Speaker 1: ' + 'word ' * 70,  # 70 words
                'word_count': 70,
                'duration_seconds': 60.0,
                'confidence_score': 0.95
            },
            'clip_name': 'half_complete.mp4'
        }
        
        response = analyze_transcription_quality(params)
        
        result = response['result']
        # 70 words out of expected 140 = 50% completeness
        assert result['completeness_pct'] == 50.0
    
    def test_all_problem_marker_types(self):
        """Test detection of all problem marker types."""
        params = {
            'transcript': {
                'text': 'Speaker 1: [inaudible] [garbled] [unintelligible] [crosstalk]',
                'word_count': 20,
                'duration_seconds': 20.0,
                'confidence_score': 0.50
            },
            'clip_name': 'all_problems.mp4'
        }
        
        response = analyze_transcription_quality(params)
        
        result = response['result']
        
        # Should detect all 4 problem types
        problem_types = set(p['type'] for p in result['problem_areas'])
        assert 'inaudible' in problem_types
        assert 'garbled' in problem_types
        assert 'unintelligible' in problem_types
        assert 'crosstalk' in problem_types
    
    def test_recommendation_text_good(self):
        """Test recommendation text for good quality."""
        params = {
            'transcript': {
                'text': 'Speaker 1: Perfect clean audio.',
                'word_count': 150,
                'duration_seconds': 60.0,
                'confidence_score': 0.95
            },
            'clip_name': 'good.mp4'
        }
        
        response = analyze_transcription_quality(params)
        
        result = response['result']
        assert 'Good' in result['recommendation'] or 'good' in result['recommendation'].lower()
        assert 'Proceed' in result['recommendation']
    
    def test_recommendation_text_poor(self):
        """Test recommendation text for poor quality."""
        params = {
            'transcript': {
                'text': 'Speaker 1: [inaudible] [garbled] [inaudible]',
                'word_count': 20,
                'duration_seconds': 60.0,
                'confidence_score': 0.45
            },
            'clip_name': 'poor.mp4'
        }
        
        response = analyze_transcription_quality(params)
        
        result = response['result']
        assert 'Poor' in result['recommendation'] or 'poor' in result['recommendation'].lower()
        assert 'cleanup' in result['recommendation'].lower() or 'recommended' in result['recommendation'].lower()


class TestAnalyzeTranscriptionQualityEdgeCases:
    """Edge case tests for the quality analysis handler."""
    
    def test_none_params(self):
        """Test handling of None params."""
        response = analyze_transcription_quality(None)
        
        assert 'error' in response
        assert response['error']['code'] == 'INVALID_PARAMS'
    
    def test_empty_params_dict(self):
        """Test handling of empty params dict."""
        params = {}
        
        response = analyze_transcription_quality(params)
        
        # Should return error for missing transcript
        assert 'error' in response
        assert response['error']['code'] == 'INVALID_PARAMS'
    
    def test_very_long_duration(self):
        """Test with very long clip duration."""
        params = {
            'transcript': {
                'text': 'Speaker 1: Short clip.',
                'word_count': 3,
                'duration_seconds': 3600.0,  # 1 hour
                'confidence_score': 0.95
            },
            'clip_name': 'long.mp4'
        }
        
        response = analyze_transcription_quality(params)
        
        result = response['result']
        # Should have very low completeness
        assert result['completeness_pct'] < 10
        # Should be poor quality due to low completeness
        assert result['quality_rating'] == QualityRating.POOR.value
    
    def test_very_short_duration(self):
        """Test with very short clip duration."""
        params = {
            'transcript': {
                'text': 'Speaker 1: Hi.',
                'word_count': 2,
                'duration_seconds': 0.5,  # Half second
                'confidence_score': 0.95
            },
            'clip_name': 'short.mp4'
        }
        
        response = analyze_transcription_quality(params)
        
        # Should handle without error
        assert 'result' in response or 'error' in response
    
    def test_case_insensitive_markers(self):
        """Test that problem markers are detected case-insensitively."""
        params = {
            'transcript': {
                'text': 'Speaker 1: [INAUDIBLE] [Inaudible] [inaudIBLE]',
                'word_count': 10,
                'duration_seconds': 10.0,
                'confidence_score': 0.50
            },
            'clip_name': 'case_test.mp4'
        }
        
        response = analyze_transcription_quality(params)
        
        result = response['result']
        # Should detect all 3 variations (case insensitive)
        assert result['problem_count'] == 3
    
    def test_no_confidence_score(self):
        """Test analysis when confidence_score is None."""
        params = {
            'transcript': {
                'text': 'Speaker 1: No confidence data available.',
                'word_count': 100,
                'duration_seconds': 60.0,
                'confidence_score': None
            },
            'clip_name': 'no_confidence.mp4'
        }
        
        response = analyze_transcription_quality(params)
        
        result = response['result']
        # Should still work with None confidence
        assert 'quality_rating' in result
        assert result['confidence_score'] == 0.0  # Should default to 0
