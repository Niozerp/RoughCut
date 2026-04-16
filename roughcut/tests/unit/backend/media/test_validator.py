"""Unit tests for media validation module.

Tests the MediaValidator class and validation logic for Story 4.5.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from roughcut.backend.media.validator import (
    MediaValidator,
    ValidationResult,
    ValidationCheck,
    ValidationErrorCode
)


class TestValidationCheck(unittest.TestCase):
    """Test ValidationCheck dataclass."""
    
    def test_basic_creation(self):
        """Test basic ValidationCheck creation."""
        check = ValidationCheck(
            name='test_check',
            passed=True,
            details={'info': 'test'}
        )
        
        self.assertEqual(check.name, 'test_check')
        self.assertTrue(check.passed)
        self.assertEqual(check.details, {'info': 'test'})
    
    def test_to_dict(self):
        """Test serialization to dict."""
        check = ValidationCheck(
            name='has_audio',
            passed=True,
            details={'track_count': 2}
        )
        
        result = check.to_dict()
        
        self.assertEqual(result['name'], 'has_audio')
        self.assertTrue(result['passed'])
        self.assertEqual(result['details']['track_count'], 2)


class TestValidationResult(unittest.TestCase):
    """Test ValidationResult dataclass."""
    
    def test_success_result(self):
        """Test successful validation result."""
        checks = {
            'has_audio': ValidationCheck('has_audio', True, {'track_count': 2}),
            'codec_supported': ValidationCheck('codec_supported', True, {'codec': 'PCM'}),
            'file_accessible': ValidationCheck('file_accessible', True, {'exists': True})
        }
        
        result = ValidationResult(
            valid=True,
            checks=checks,
            failed_check=None,
            error_code=None,
            error_message='',
            suggestion=''
        )
        
        self.assertTrue(result.valid)
        self.assertIsNone(result.failed_check)
        self.assertIsNone(result.error_code)
        
        # Test serialization
        dict_result = result.to_dict()
        self.assertTrue(dict_result['valid'])
        self.assertIsNone(dict_result['failed_check'])
        self.assertIsNone(dict_result['error_code'])
    
    def test_failure_result(self):
        """Test failed validation result."""
        checks = {
            'has_audio': ValidationCheck('has_audio', False, {'track_count': 0}),
        }
        
        result = ValidationResult(
            valid=False,
            checks=checks,
            failed_check='has_audio',
            error_code=ValidationErrorCode.NO_AUDIO_TRACK,
            error_message='No audio track',
            suggestion='Select clip with audio'
        )
        
        self.assertFalse(result.valid)
        self.assertEqual(result.failed_check, 'has_audio')
        self.assertEqual(result.error_code, ValidationErrorCode.NO_AUDIO_TRACK)
        
        # Test serialization includes error code as string
        dict_result = result.to_dict()
        self.assertFalse(dict_result['valid'])
        self.assertEqual(dict_result['error_code'], 'NO_AUDIO_TRACK')


class TestMediaValidatorAudioTrack(unittest.TestCase):
    """Test audio track validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = MediaValidator()
    
    def test_clip_with_audio_passes(self):
        """Test that clips with audio tracks pass validation."""
        clip_data = {
            'audio_tracks': 2,
            'codec': 'PCM',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_audio_track(clip_data)
        
        self.assertTrue(result.passed)
        self.assertEqual(result.details['track_count'], 2)
    
    def test_clip_with_no_audio_fails(self):
        """Test that clips with no audio tracks fail validation."""
        clip_data = {
            'audio_tracks': 0,
            'codec': None,
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_audio_track(clip_data)
        
        self.assertFalse(result.passed)
    
    def test_clip_without_audio_field_fails(self):
        """Test that clips without audio_tracks field fail."""
        clip_data = {
            'codec': 'PCM',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_audio_track(clip_data)
        
        self.assertFalse(result.passed)
    
    def test_string_audio_tracks_converted(self):
        """Test that string audio_tracks values are converted."""
        clip_data = {
            'audio_tracks': '2',
            'codec': 'PCM',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_audio_track(clip_data)
        
        self.assertTrue(result.passed)
    
    def test_invalid_string_audio_tracks_fails(self):
        """Test that invalid string audio_tracks values fail."""
        clip_data = {
            'audio_tracks': 'invalid',
            'codec': 'PCM',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_audio_track(clip_data)
        
        self.assertFalse(result.passed)
    
    def test_negative_audio_tracks_fails(self):
        """Test that negative audio_tracks values fail."""
        clip_data = {
            'audio_tracks': -1,
            'codec': 'PCM',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_audio_track(clip_data)
        
        self.assertFalse(result.passed)
        self.assertEqual(result.details['reason'], 'negative_value')


class TestMediaValidatorCodec(unittest.TestCase):
    """Test codec validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = MediaValidator()
    
    def test_supported_pcm_codec_passes(self):
        """Test that PCM codec passes."""
        clip_data = {
            'audio_tracks': 2,
            'codec': 'PCM',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_codec(clip_data)
        
        self.assertTrue(result.passed)
        self.assertEqual(result.details['codec'], 'PCM')
    
    def test_supported_aac_codec_passes(self):
        """Test that AAC codec passes."""
        clip_data = {
            'audio_tracks': 2,
            'codec': 'AAC',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_codec(clip_data)
        
        self.assertTrue(result.passed)
    
    def test_supported_mp3_codec_passes(self):
        """Test that MP3 codec passes."""
        clip_data = {
            'audio_tracks': 2,
            'codec': 'MP3',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_codec(clip_data)
        
        self.assertTrue(result.passed)
    
    def test_supported_wav_codec_passes(self):
        """Test that WAV codec passes."""
        clip_data = {
            'audio_tracks': 2,
            'codec': 'WAV',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_codec(clip_data)
        
        self.assertTrue(result.passed)
    
    def test_problematic_dolby_fails(self):
        """Test that Dolby codecs fail."""
        clip_data = {
            'audio_tracks': 2,
            'codec': 'DOLBY_DIGITAL',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_codec(clip_data)
        
        self.assertFalse(result.passed)
        self.assertEqual(result.details['reason'], 'known_problematic_codec')
    
    def test_problematic_dts_fails(self):
        """Test that DTS codec fails."""
        clip_data = {
            'audio_tracks': 2,
            'codec': 'DTS',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_codec(clip_data)
        
        self.assertFalse(result.passed)
    
    def test_no_codec_info_fails(self):
        """Test that missing codec info fails."""
        clip_data = {
            'audio_tracks': 2,
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_codec(clip_data)
        
        self.assertFalse(result.passed)
        self.assertEqual(result.details['reason'], 'no_codec_info')
    
    def test_codec_case_insensitive(self):
        """Test that codec names are case insensitive."""
        clip_data = {
            'audio_tracks': 2,
            'codec': 'pcm',  # lowercase
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_codec(clip_data)
        
        self.assertTrue(result.passed)
    
    def test_unknown_codec_permissive_for_mvp(self):
        """Test that unknown codecs are permissive for MVP."""
        clip_data = {
            'audio_tracks': 2,
            'codec': 'MY_UNKNOWN_CODEC',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_codec(clip_data)
        
        # For MVP, unknown codecs pass with a warning
        self.assertTrue(result.passed)
        self.assertEqual(result.details['reason'], 'unknown_codec_assumed_supported')


class TestMediaValidatorFileAccessibility(unittest.TestCase):
    """Test file accessibility validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = MediaValidator()
    
    def test_existing_file_passes(self):
        """Test that existing files pass validation."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b'test content')
            tmp_path = tmp.name
        
        try:
            clip_data = {
                'audio_tracks': 2,
                'codec': 'PCM',
                'file_path': tmp_path
            }
            
            result = self.validator._check_file_accessible(clip_data)
            
            self.assertTrue(result.passed)
            self.assertEqual(result.details['exists'], True)
            self.assertGreater(result.details['size_bytes'], 0)
        finally:
            os.unlink(tmp_path)
    
    def test_nonexistent_file_fails(self):
        """Test that nonexistent files fail."""
        clip_data = {
            'audio_tracks': 2,
            'codec': 'PCM',
            'file_path': '/nonexistent/path/clip.mov'
        }
        
        result = self.validator._check_file_accessible(clip_data)
        
        self.assertFalse(result.passed)
        self.assertEqual(result.details['reason'], 'file_not_found')
    
    def test_directory_fails(self):
        """Test that directories fail (must be file)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            clip_data = {
                'audio_tracks': 2,
                'codec': 'PCM',
                'file_path': tmp_dir
            }
            
            result = self.validator._check_file_accessible(clip_data)
            
            self.assertFalse(result.passed)
            self.assertEqual(result.details['reason'], 'not_a_file')
    
    def test_long_path_fails(self):
        """Test that excessively long paths fail."""
        # Create a path longer than MAX_PATH_LENGTH (4096)
        long_path = '/test/' + ('a' * 5000)
        
        clip_data = {
            'audio_tracks': 2,
            'codec': 'PCM',
            'file_path': long_path
        }
        
        result = self.validator._check_file_accessible(clip_data)
        
        self.assertFalse(result.passed)
        self.assertEqual(result.details['reason'], 'path_too_long')
        self.assertIn('path_length', result.details)
    
    def test_no_path_fails(self):
        """Test that missing file_path fails."""
        clip_data = {
            'audio_tracks': 2,
            'codec': 'PCM'
        }
        
        result = self.validator._check_file_accessible(clip_data)
        
        self.assertFalse(result.passed)
        self.assertEqual(result.details['reason'], 'no_path_provided')


class TestMediaValidatorFullValidation(unittest.TestCase):
    """Test full validation flow with all checks."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = MediaValidator()
    
    def test_valid_media_passes_all_checks(self):
        """Test that valid media passes all validation checks."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            clip_data = {
                'audio_tracks': 2,
                'codec': 'PCM',
                'file_path': tmp_path
            }
            
            result = self.validator.validate(clip_data)
            
            self.assertTrue(result.valid)
            self.assertIsNone(result.failed_check)
            self.assertIsNone(result.error_code)
            self.assertEqual(len(result.checks), 3)
        finally:
            os.unlink(tmp_path)
    
    def test_no_audio_fails_with_correct_error(self):
        """Test that no audio fails with correct error code."""
        clip_data = {
            'audio_tracks': 0,
            'codec': 'PCM',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator.validate(clip_data)
        
        self.assertFalse(result.valid)
        self.assertEqual(result.failed_check, 'has_audio')
        self.assertEqual(result.error_code, ValidationErrorCode.NO_AUDIO_TRACK)
        self.assertIn('audio', result.error_message.lower())
    
    def test_unsupported_codec_fails_with_correct_error(self):
        """Test that unsupported codec fails with correct error code."""
        clip_data = {
            'audio_tracks': 2,
            'codec': 'DOLBY_DIGITAL',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator.validate(clip_data)
        
        self.assertFalse(result.valid)
        self.assertEqual(result.failed_check, 'codec_supported')
        self.assertEqual(result.error_code, ValidationErrorCode.UNSUPPORTED_CODEC)
        self.assertIn('codec', result.error_message.lower())
    
    def test_missing_file_fails_with_correct_error(self):
        """Test that missing file fails with correct error code."""
        clip_data = {
            'audio_tracks': 2,
            'codec': 'PCM',
            'file_path': '/nonexistent/clip.mov'
        }
        
        result = self.validator.validate(clip_data)
        
        self.assertFalse(result.valid)
        self.assertEqual(result.failed_check, 'file_accessible')
        self.assertEqual(result.error_code, ValidationErrorCode.MEDIA_OFFLINE)
    
    def test_error_message_is_actionable(self):
        """Test that error messages are actionable per NFR13."""
        # Test no audio error
        result = self.validator.validate({
            'audio_tracks': 0,
            'codec': 'PCM',
            'file_path': '/test/clip.mov'
        })
        
        self.assertGreater(len(result.suggestion), 0)
        self.assertNotEqual(result.suggestion, result.error_message)
    
    def test_only_first_failure_reported(self):
        """Test that only the first failure is reported (fail-fast behavior)."""
        # This clip fails audio check first, so codec check shouldn't run
        clip_data = {
            'audio_tracks': 0,
            'codec': 'DOLBY_DIGITAL',  # Would also fail
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator.validate(clip_data)
        
        self.assertEqual(result.failed_check, 'has_audio')
        # Only has_audio check should be in results
        self.assertIn('has_audio', result.checks)


class TestMediaValidatorCodecLists(unittest.TestCase):
    """Test codec list methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = MediaValidator()
    
    def test_get_supported_codecs_returns_set(self):
        """Test that supported codecs returns a set."""
        codecs = self.validator.get_supported_codecs()
        
        self.assertIsInstance(codecs, set)
        self.assertGreater(len(codecs), 0)
        self.assertIn('PCM', codecs)
        self.assertIn('AAC', codecs)
    
    def test_get_problematic_codecs_returns_set(self):
        """Test that problematic codecs returns a set."""
        codecs = self.validator.get_problematic_codecs()
        
        self.assertIsInstance(codecs, set)
        self.assertGreater(len(codecs), 0)
        self.assertIn('DOLBY_E', codecs)
        self.assertIn('DTS', codecs)


class TestMediaValidatorEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = MediaValidator()
    
    def test_empty_clip_data_fails_gracefully(self):
        """Test that empty clip data fails gracefully."""
        result = self.validator.validate({})
        
        self.assertFalse(result.valid)
        self.assertIsNotNone(result.failed_check)
    
    def test_none_values_handled(self):
        """Test that None values are handled gracefully."""
        clip_data = {
            'audio_tracks': None,
            'codec': None,
            'file_path': None
        }
        
        result = self.validator.validate(clip_data)
        
        self.assertFalse(result.valid)
    
    def test_multi_track_audio_passes(self):
        """Test that multiple audio tracks pass."""
        clip_data = {
            'audio_tracks': 8,  # 8-track audio
            'codec': 'PCM',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_audio_track(clip_data)
        
        self.assertTrue(result.passed)
        self.assertEqual(result.details['track_count'], 8)
    
    def test_codec_with_dashes_normalized(self):
        """Test that codec names with dashes are normalized."""
        clip_data = {
            'audio_tracks': 2,
            'codec': 'PCM-S16LE',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_codec(clip_data)
        
        # Should normalize PCM-S16LE to PCM_S16LE
        self.assertTrue(result.passed)
    
    def test_partial_codec_matching(self):
        """Test that partial codec matching works for substrings."""
        # AAC_LC contains AAC
        clip_data = {
            'audio_tracks': 2,
            'codec': 'AAC_LC',
            'file_path': '/test/clip.mov'
        }
        
        result = self.validator._check_codec(clip_data)
        
        self.assertTrue(result.passed)
        self.assertEqual(result.details['detected_subtype'], 'AAC')


if __name__ == '__main__':
    unittest.main()
