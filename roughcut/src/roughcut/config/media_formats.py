"""Media format configuration and codec definitions.

Provides centralized definitions for supported audio/video codecs,
validation rules, and format-specific settings for RoughCut.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Set


@dataclass
class AudioCodecInfo:
    """Information about an audio codec.
    
    Attributes:
        name: Codec identifier
        full_name: Human-readable name
        supported: Whether Resolve can transcribe this codec
        description: Brief description
        common_extensions: File extensions commonly using this codec
    """
    name: str
    full_name: str
    supported: bool
    description: str
    common_extensions: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'name': self.name,
            'full_name': self.full_name,
            'supported': self.supported,
            'description': self.description,
            'common_extensions': self.common_extensions
        }


# Audio codecs supported by Resolve's transcription engine
# Based on Resolve's documented capabilities and common formats
SUPPORTED_AUDIO_CODECS: dict[str, AudioCodecInfo] = {
    'PCM': AudioCodecInfo(
        name='PCM',
        full_name='Pulse Code Modulation',
        supported=True,
        description='Uncompressed raw audio, highest quality',
        common_extensions=['.wav', '.aiff', '.pcm']
    ),
    'LPCM': AudioCodecInfo(
        name='LPCM',
        full_name='Linear Pulse Code Modulation',
        supported=True,
        description='Standard uncompressed audio in video containers',
        common_extensions=['.mov', '.mp4', '.mxf']
    ),
    'AAC': AudioCodecInfo(
        name='AAC',
        full_name='Advanced Audio Coding',
        supported=True,
        description='Compressed audio, common in MP4/MOV files',
        common_extensions=['.mp4', '.m4a', '.mov']
    ),
    'AAC_LC': AudioCodecInfo(
        name='AAC_LC',
        full_name='AAC Low Complexity',
        supported=True,
        description='Standard AAC profile, widely compatible',
        common_extensions=['.mp4', '.m4a', '.mov']
    ),
    'WAV': AudioCodecInfo(
        name='WAV',
        full_name='Waveform Audio File Format',
        supported=True,
        description='Container for PCM audio, industry standard',
        common_extensions=['.wav']
    ),
    'MP3': AudioCodecInfo(
        name='MP3',
        full_name='MPEG-1 Audio Layer III',
        supported=True,
        description='Compressed audio, very common format',
        common_extensions=['.mp3']
    ),
    'MP3_MPEG': AudioCodecInfo(
        name='MP3_MPEG',
        full_name='MPEG Audio',
        supported=True,
        description='MPEG audio codec variants',
        common_extensions=['.mp3', '.mp2']
    ),
}


# Codecs known to cause transcription issues
PROBLEMATIC_AUDIO_CODECS: dict[str, AudioCodecInfo] = {
    'DOLBY_E': AudioCodecInfo(
        name='DOLBY_E',
        full_name='Dolby E',
        supported=False,
        description='Professional broadcast codec, not supported for transcription',
        common_extensions=['.mxf', '.mov']
    ),
    'DOLBY_DIGITAL': AudioCodecInfo(
        name='DOLBY_DIGITAL',
        full_name='Dolby Digital (AC-3)',
        supported=False,
        description='Surround sound codec, requires decoding',
        common_extensions=['.ac3', '.mov', '.mp4']
    ),
    'AC3': AudioCodecInfo(
        name='AC3',
        full_name='AC-3 (Dolby Digital)',
        supported=False,
        description='Compressed surround format, may not transcribe',
        common_extensions=['.ac3']
    ),
    'EAC3': AudioCodecInfo(
        name='EAC3',
        full_name='Enhanced AC-3 (Dolby Digital Plus)',
        supported=False,
        description='Advanced surround codec, not supported',
        common_extensions=['.ec3', '.mov', '.mp4']
    ),
    'DTS': AudioCodecInfo(
        name='DTS',
        full_name='Digital Theater Systems',
        supported=False,
        description='Surround sound codec, requires specific decoding',
        common_extensions=['.dts', '.mov']
    ),
    'OPUS': AudioCodecInfo(
        name='OPUS',
        full_name='Opus Audio',
        supported=False,
        description='Modern compressed format, may not be supported',
        common_extensions=['.opus', '.webm', '.mkv']
    ),
    'VORBIS': AudioCodecInfo(
        name='VORBIS',
        full_name='Ogg Vorbis',
        supported=False,
        description='Open source compressed audio',
        common_extensions=['.ogg', '.oga']
    ),
    'FLAC': AudioCodecInfo(
        name='FLAC',
        full_name='Free Lossless Audio Codec',
        supported=False,
        description='Lossless compression, support varies',
        common_extensions=['.flac']
    ),
    'WMA': AudioCodecInfo(
        name='WMA',
        full_name='Windows Media Audio',
        supported=False,
        description='Microsoft proprietary format',
        common_extensions=['.wma']
    ),
    'RA': AudioCodecInfo(
        name='RA',
        full_name='RealAudio',
        supported=False,
        description='Legacy streaming format',
        common_extensions=['.ra', '.ram']
    ),
    'AMR': AudioCodecInfo(
        name='AMR',
        full_name='Adaptive Multi-Rate',
        supported=False,
        description='Mobile audio format, low quality',
        common_extensions=['.amr']
    ),
}


def get_supported_codecs() -> set[str]:
    """Return set of supported codec identifiers.
    
    Returns:
        Set of supported codec names
    """
    return set(SUPPORTED_AUDIO_CODECS.keys())


def get_problematic_codecs() -> set[str]:
    """Return set of problematic codec identifiers.
    
    Returns:
        Set of problematic codec names
    """
    return set(PROBLEMATIC_AUDIO_CODECS.keys())


def get_codec_info(codec_name: str) -> AudioCodecInfo | None:
    """Get information about a specific codec.
    
    Args:
        codec_name: Name of the codec to look up
        
    Returns:
        AudioCodecInfo if found, None otherwise
    """
    # Normalize codec name
    normalized = codec_name.upper().replace('-', '_').replace(' ', '_')
    
    # Check supported codecs
    if normalized in SUPPORTED_AUDIO_CODECS:
        return SUPPORTED_AUDIO_CODECS[normalized]
    
    # Check problematic codecs
    if normalized in PROBLEMATIC_AUDIO_CODECS:
        return PROBLEMATIC_AUDIO_CODECS[normalized]
    
    # Try partial matching for supported
    for key, info in SUPPORTED_AUDIO_CODECS.items():
        if key in normalized or normalized in key:
            return info
    
    # Try partial matching for problematic
    for key, info in PROBLEMATIC_AUDIO_CODECS.items():
        if key in normalized or normalized in key:
            return info
    
    return None


def is_codec_supported(codec_name: str) -> bool:
    """Check if a codec is supported for transcription.
    
    Args:
        codec_name: Name of the codec to check
        
    Returns:
        True if supported, False otherwise
    """
    # Normalize codec name
    normalized = codec_name.upper().replace('-', '_').replace(' ', '_')
    
    # Check explicit supported list
    if normalized in SUPPORTED_AUDIO_CODECS:
        return True
    
    # Check problematic list
    if normalized in PROBLEMATIC_AUDIO_CODECS:
        return False
    
    # Check substrings for known good codecs
    for supported in ['PCM', 'AAC', 'WAV']:
        if supported in normalized:
            return True
    
    # Check substrings for known bad codecs
    for problematic in ['DOLBY', 'AC3', 'DTS', 'OPUS', 'VORBIS']:
        if problematic in normalized:
            return False
    
    # Unknown codec - permissive for MVP
    return True


def get_format_conversion_guide() -> str:
    """Return guide for converting unsupported formats.
    
    Returns:
        Multi-line string with format conversion instructions
    """
    return """
Format Conversion Guide for RoughCut
====================================

If your clip uses an unsupported audio codec, follow these steps:

1. Select the clip in Resolve's Edit page
2. Go to the Deliver (Export) page
3. Choose "YouTube 1080p" preset (or similar)
4. Enable "In/Out Points" if you only need a portion
5. Render to a new file
6. Import the rendered file back to Media Pool
7. Select the new clip in RoughCut

Recommended settings:
- Format: MP4 or MOV
- Codec: H.264 + AAC (default)
- Audio: Stereo, 48kHz

This will ensure your clip has a supported audio format for transcription.
"""
