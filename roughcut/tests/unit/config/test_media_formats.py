"""Unit tests for media formats configuration.

Tests codec definitions and format utilities for Story 4.5.
"""

from __future__ import annotations

import unittest

from roughcut.src.roughcut.config.media_formats import (
    SUPPORTED_AUDIO_CODECS,
    PROBLEMATIC_AUDIO_CODECS,
    get_supported_codecs,
    get_problematic_codecs,
    get_codec_info,
    is_codec_supported,
    get_format_conversion_guide
)


class TestSupportedCodecs(unittest.TestCase):
    """Test supported codec definitions."""
    
    def test_pcm_defined(self):
        """Test that PCM codec is defined."""
        self.assertIn('PCM', SUPPORTED_AUDIO_CODECS)
        info = SUPPORTED_AUDIO_CODECS['PCM']
        self.assertTrue(info.supported)
        self.assertEqual(info.name, 'PCM')
    
    def test_aac_defined(self):
        """Test that AAC codec is defined."""
        self.assertIn('AAC', SUPPORTED_AUDIO_CODECS)
        info = SUPPORTED_AUDIO_CODECS['AAC']
        self.assertTrue(info.supported)
    
    def test_wav_defined(self):
        """Test that WAV codec is defined."""
        self.assertIn('WAV', SUPPORTED_AUDIO_CODECS)
        info = SUPPORTED_AUDIO_CODECS['WAV']
        self.assertTrue(info.supported)
    
    def test_mp3_defined(self):
        """Test that MP3 codec is defined."""
        self.assertIn('MP3', SUPPORTED_AUDIO_CODECS)
        info = SUPPORTED_AUDIO_CODECS['MP3']
        self.assertTrue(info.supported)
    
    def test_all_supported_have_extensions(self):
        """Test that all supported codecs have file extensions."""
        for name, info in SUPPORTED_AUDIO_CODECS.items():
            self.assertGreater(len(info.common_extensions), 0, 
                             f"{name} should have common extensions")
    
    def test_codec_info_serialization(self):
        """Test that AudioCodecInfo can be serialized."""
        info = SUPPORTED_AUDIO_CODECS['PCM']
        result = info.to_dict()
        
        self.assertEqual(result['name'], 'PCM')
        self.assertTrue(result['supported'])
        self.assertIn('full_name', result)
        self.assertIn('description', result)


class TestProblematicCodecs(unittest.TestCase):
    """Test problematic codec definitions."""
    
    def test_dolby_defined(self):
        """Test that Dolby codecs are defined."""
        self.assertIn('DOLBY_DIGITAL', PROBLEMATIC_AUDIO_CODECS)
        info = PROBLEMATIC_AUDIO_CODECS['DOLBY_DIGITAL']
        self.assertFalse(info.supported)
    
    def test_dts_defined(self):
        """Test that DTS codec is defined."""
        self.assertIn('DTS', PROBLEMATIC_AUDIO_CODECS)
        info = PROBLEMATIC_AUDIO_CODECS['DTS']
        self.assertFalse(info.supported)
    
    def test_flac_defined(self):
        """Test that FLAC is marked as problematic."""
        self.assertIn('FLAC', PROBLEMATIC_AUDIO_CODECS)
        info = PROBLEMATIC_AUDIO_CODECS['FLAC']
        self.assertFalse(info.supported)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""
    
    def test_get_supported_codecs_returns_set(self):
        """Test that get_supported_codecs returns a set."""
        result = get_supported_codecs()
        
        self.assertIsInstance(result, set)
        self.assertGreater(len(result), 0)
        self.assertIn('PCM', result)
    
    def test_get_problematic_codecs_returns_set(self):
        """Test that get_problematic_codecs returns a set."""
        result = get_problematic_codecs()
        
        self.assertIsInstance(result, set)
        self.assertGreater(len(result), 0)
        self.assertIn('DOLBY_E', result)
    
    def test_get_codec_info_supported(self):
        """Test getting info for supported codec."""
        info = get_codec_info('PCM')
        
        self.assertIsNotNone(info)
        self.assertEqual(info.name, 'PCM')
        self.assertTrue(info.supported)
    
    def test_get_codec_info_problematic(self):
        """Test getting info for problematic codec."""
        info = get_codec_info('DTS')
        
        self.assertIsNotNone(info)
        self.assertFalse(info.supported)
    
    def test_get_codec_info_unknown(self):
        """Test getting info for unknown codec."""
        info = get_codec_info('UNKNOWN_CODEC_XYZ')
        
        self.assertIsNone(info)
    
    def test_get_codec_info_case_insensitive(self):
        """Test that codec lookup is case insensitive."""
        info_lower = get_codec_info('pcm')
        info_upper = get_codec_info('PCM')
        
        self.assertIsNotNone(info_lower)
        self.assertIsNotNone(info_upper)
    
    def test_get_codec_info_partial_match(self):
        """Test that partial matching works."""
        # AAC_LC should match AAC
        info = get_codec_info('AAC_LC')
        
        self.assertIsNotNone(info)
        self.assertIn(info.name, ['AAC', 'AAC_LC'])
    
    def test_is_codec_supported_true(self):
        """Test checking supported codec."""
        result = is_codec_supported('PCM')
        
        self.assertTrue(result)
    
    def test_is_codec_supported_false(self):
        """Test checking problematic codec."""
        result = is_codec_supported('DOLBY_DIGITAL')
        
        self.assertFalse(result)
    
    def test_is_codec_supported_unknown(self):
        """Test checking unknown codec (permissive for MVP)."""
        result = is_codec_supported('MY_UNKNOWN_CODEC')
        
        # For MVP, unknown codecs return True
        self.assertTrue(result)
    
    def test_is_codec_supported_case_insensitive(self):
        """Test that codec support check is case insensitive."""
        result_lower = is_codec_supported('aac')
        result_upper = is_codec_supported('AAC')
        
        self.assertTrue(result_lower)
        self.assertTrue(result_upper)
    
    def test_is_codec_supported_substring_matching(self):
        """Test substring matching for codec detection."""
        # Anything containing PCM should be supported
        result = is_codec_supported('PCM_S16LE')
        
        self.assertTrue(result)
    
    def test_get_format_conversion_guide(self):
        """Test getting format conversion guide."""
        guide = get_format_conversion_guide()
        
        self.assertIsInstance(guide, str)
        self.assertGreater(len(guide), 0)
        self.assertIn('Format Conversion Guide', guide)
        self.assertIn('YouTube 1080p', guide)


if __name__ == '__main__':
    unittest.main()
