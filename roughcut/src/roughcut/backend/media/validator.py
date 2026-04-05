"""Media validation module for transcribability checks.

Provides validation logic to ensure media can be transcribed by Resolve
before attempting transcription. Checks for audio tracks, supported codecs,
and file accessibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ValidationErrorCode(Enum):
    """Error codes for media validation failures."""
    NO_AUDIO_TRACK = "NO_AUDIO_TRACK"
    UNSUPPORTED_CODEC = "UNSUPPORTED_CODEC"
    MEDIA_OFFLINE = "MEDIA_OFFLINE"
    CLIP_NOT_FOUND = "CLIP_NOT_FOUND"
    VALIDATION_FAILED = "VALIDATION_FAILED"


# Maximum allowed path length (common filesystem limit)
MAX_PATH_LENGTH = 4096


@dataclass
class ValidationCheck:
    """Result of a single validation check.
    
    Attributes:
        name: Name of the check (e.g., "has_audio", "codec_supported")
        passed: Whether the check passed
        details: Optional details about the check result
    """
    name: str
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'name': self.name,
            'passed': self.passed,
            'details': self.details
        }


@dataclass
class ValidationResult:
    """Complete result of media validation.
    
    Attributes:
        valid: True if all checks passed
        checks: Dictionary of all checks performed
        failed_check: Name of the first failed check, or None
        error_code: Error code for the failure, or None
        error_message: Human-readable error message
        suggestion: Actionable suggestion for recovery
    """
    valid: bool
    checks: dict[str, ValidationCheck]
    failed_check: Optional[str] = None
    error_code: Optional[ValidationErrorCode] = None
    error_message: str = ""
    suggestion: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON-RPC response."""
        return {
            'valid': self.valid,
            'checks': {k: v.to_dict() for k, v in self.checks.items()},
            'failed_check': self.failed_check,
            'error_code': self.error_code.value if self.error_code else None,
            'error_message': self.error_message,
            'suggestion': self.suggestion
        }


class MediaValidator:
    """Validates media transcribability for Resolve transcription.
    
    Performs three main checks:
    1. Has audio track(s)
    2. Audio codec is supported
    3. Source media file is accessible
    
    Example:
        >>> validator = MediaValidator()
        >>> result = validator.validate({
        ...     'audio_tracks': 2,
        ...     'codec': 'PCM',
        ...     'file_path': '/path/to/clip.mov'
        ... })
        >>> result.valid
        True
    """
    
    # Audio codecs supported by Resolve's transcription engine
    # These are commonly supported formats
    SUPPORTED_CODECS = {
        'PCM', 'AAC', 'MP3', 'WAV', 'LPCM', 'FLOAT',
        'PCM_S16LE', 'PCM_S24LE', 'PCM_F32LE',
        'AAC_LC', 'MP3_MPEG', 'WAV_PCM'
    }
    
    # Codecs known to be problematic
    PROBLEMATIC_CODECS = {
        'DOLBY_E', 'DOLBY_DIGITAL', 'AC3', 'EAC3', 'DTS',
        'OPUS', 'VORBIS', 'FLAC', 'WMA', 'RA', 'AMR'
    }
    
    def validate(self, clip_data: dict[str, Any]) -> ValidationResult:
        """Run all validation checks on media.
        
        Args:
            clip_data: Dictionary containing clip metadata:
                - audio_tracks: Number of audio tracks (int)
                - codec: Audio codec name (str)
                - file_path: Absolute path to media file (str)
                - clip_name: Name of the clip (str, optional)
                
        Returns:
            ValidationResult with all checks and overall validity
        """
        # Initialize checks
        checks: dict[str, ValidationCheck] = {}
        
        # Check 1: Has audio track
        checks['has_audio'] = self._check_audio_track(clip_data)
        if not checks['has_audio'].passed:
            return ValidationResult(
                valid=False,
                checks=checks,
                failed_check='has_audio',
                error_code=ValidationErrorCode.NO_AUDIO_TRACK,
                error_message="Selected clip has no audio track",
                suggestion="Select a clip with audio content"
            )
        
        # Check 2: Codec is supported
        checks['codec_supported'] = self._check_codec(clip_data)
        if not checks['codec_supported'].passed:
            return ValidationResult(
                valid=False,
                checks=checks,
                failed_check='codec_supported',
                error_code=ValidationErrorCode.UNSUPPORTED_CODEC,
                error_message="Audio codec not supported for transcription",
                suggestion="Deliver page → YouTube 1080p preset → Render in-place → Replace clip in Media Pool"
            )
        
        # Check 3: File is accessible
        checks['file_accessible'] = self._check_file_accessible(clip_data)
        if not checks['file_accessible'].passed:
            file_path = clip_data.get('file_path', 'unknown')
            return ValidationResult(
                valid=False,
                checks=checks,
                failed_check='file_accessible',
                error_code=ValidationErrorCode.MEDIA_OFFLINE,
                error_message=f"Source media file not found at {file_path}",
                suggestion="Reconnect media in Resolve Media Pool"
            )
        
        # All checks passed
        return ValidationResult(
            valid=True,
            checks=checks,
            failed_check=None,
            error_code=None,
            error_message="",
            suggestion=""
        )
    
    def _check_audio_track(self, clip_data: dict[str, Any]) -> ValidationCheck:
        """Check if clip has at least one audio track.
        
        Args:
            clip_data: Clip metadata dictionary
            
        Returns:
            ValidationCheck with pass/fail status
        """
        audio_tracks = clip_data.get('audio_tracks', 0)
        
        # Handle various input types
        if isinstance(audio_tracks, str):
            try:
                audio_tracks = int(audio_tracks)
            except ValueError:
                audio_tracks = 0
        elif audio_tracks is None:
            audio_tracks = 0
        
        # Validate non-negative
        if isinstance(audio_tracks, int) and audio_tracks < 0:
            return ValidationCheck(
                name='has_audio',
                passed=False,
                details={
                    'audio_tracks': audio_tracks,
                    'track_count': 0,
                    'reason': 'negative_value'
                }
            )
        
        passed = isinstance(audio_tracks, int) and audio_tracks > 0
        
        return ValidationCheck(
            name='has_audio',
            passed=passed,
            details={
                'audio_tracks': audio_tracks,
                'track_count': audio_tracks if passed else 0
            }
        )
    
    def _check_codec(self, clip_data: dict[str, Any]) -> ValidationCheck:
        """Check if audio codec is supported for transcription.
        
        Args:
            clip_data: Clip metadata dictionary
            
        Returns:
            ValidationCheck with pass/fail status
        """
        codec = clip_data.get('codec', '')
        
        if not codec:
            # No codec info - assume it's problematic
            # In production, we might want to be more permissive
            return ValidationCheck(
                name='codec_supported',
                passed=False,
                details={'codec': None, 'reason': 'no_codec_info'}
            )
        
        # Normalize codec name
        codec_normalized = codec.upper().replace('-', '_').replace(' ', '_')
        
        # Check if codec is explicitly supported
        if codec_normalized in self.SUPPORTED_CODECS:
            return ValidationCheck(
                name='codec_supported',
                passed=True,
                details={'codec': codec, 'normalized': codec_normalized}
            )
        
        # Check if codec is known problematic
        if codec_normalized in self.PROBLEMATIC_CODECS:
            return ValidationCheck(
                name='codec_supported',
                passed=False,
                details={
                    'codec': codec,
                    'normalized': codec_normalized,
                    'reason': 'known_problematic_codec'
                }
            )
        
        # For unknown codecs, check if it contains supported codec substrings
        # This is a heuristic for MVP
        for supported in ['PCM', 'AAC', 'WAV', 'MP3']:
            if supported in codec_normalized:
                return ValidationCheck(
                    name='codec_supported',
                    passed=True,
                    details={
                        'codec': codec,
                        'normalized': codec_normalized,
                        'detected_subtype': supported
                    }
                )
        
        # Unknown codec - be permissive for MVP but flag it
        # In production, this might be a failure
        return ValidationCheck(
            name='codec_supported',
            passed=True,  # Permissive for MVP
            details={
                'codec': codec,
                'normalized': codec_normalized,
                'reason': 'unknown_codec_assumed_supported',
                'warning': 'Unknown codec, proceeding with caution'
            }
        )
    
    def _check_file_accessible(self, clip_data: dict[str, Any]) -> ValidationCheck:
        """Check if source media file exists and is accessible.
        
        Args:
            clip_data: Clip metadata dictionary
            
        Returns:
            ValidationCheck with pass/fail status
        """
        file_path = clip_data.get('file_path', '')
        
        if not file_path:
            return ValidationCheck(
                name='file_accessible',
                passed=False,
                details={'path': None, 'reason': 'no_path_provided'}
            )
        
        # Check path length
        if len(file_path) > MAX_PATH_LENGTH:
            return ValidationCheck(
                name='file_accessible',
                passed=False,
                details={
                    'path': file_path[:100] + '...' if len(file_path) > 100 else file_path,
                    'path_length': len(file_path),
                    'max_length': MAX_PATH_LENGTH,
                    'reason': 'path_too_long'
                }
            )
        
        try:
            path = Path(file_path)
            
            # Check if file exists
            if not path.exists():
                return ValidationCheck(
                    name='file_accessible',
                    passed=False,
                    details={
                        'path': file_path,
                        'exists': False,
                        'reason': 'file_not_found'
                    }
                )
            
            # Check if it's a file (not a directory)
            if not path.is_file():
                return ValidationCheck(
                    name='file_accessible',
                    passed=False,
                    details={
                        'path': file_path,
                        'is_file': False,
                        'reason': 'not_a_file'
                    }
                )
            
            # Check if file is readable (we can stat it)
            try:
                path.stat()
                return ValidationCheck(
                    name='file_accessible',
                    passed=True,
                    details={
                        'path': file_path,
                        'exists': True,
                        'size_bytes': path.stat().st_size
                    }
                )
            except (OSError, IOError) as e:
                return ValidationCheck(
                    name='file_accessible',
                    passed=False,
                    details={
                        'path': file_path,
                        'exists': True,
                        'readable': False,
                        'error': str(e)
                    }
                )
        
        except Exception as e:
            return ValidationCheck(
                name='file_accessible',
                passed=False,
                details={
                    'path': file_path,
                    'error': str(e),
                    'reason': 'path_error'
                }
            )
                        'path': file_path,
                        'is_file': False,
                        'reason': 'not_a_file'
                    }
                )
            
            # Check if file is readable (we can stat it)
            try:
                path.stat()
                return ValidationCheck(
                    name='file_accessible',
                    passed=True,
                    details={
                        'path': file_path,
                        'exists': True,
                        'size_bytes': path.stat().st_size
                    }
                )
            except (OSError, IOError) as e:
                return ValidationCheck(
                    name='file_accessible',
                    passed=False,
                    details={
                        'path': file_path,
                        'exists': True,
                        'readable': False,
                        'error': str(e)
                    }
                )
        
        except Exception as e:
            return ValidationCheck(
                name='file_accessible',
                passed=False,
                details={
                    'path': file_path,
                    'error': str(e),
                    'reason': 'path_error'
                }
            )
    
    def get_supported_codecs(self) -> set[str]:
        """Return set of supported codec names.
        
        Returns:
            Set of supported codec names
        """
        return self.SUPPORTED_CODECS.copy()
    
    def get_problematic_codecs(self) -> set[str]:
        """Return set of known problematic codec names.
        
        Returns:
            Set of problematic codec names
        """
        return self.PROBLEMATIC_CODECS.copy()
