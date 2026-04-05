"""Document data structures for AI-generated rough cut review.

Provides dataclasses for representing rough cut documents, transcript segments,
and asset suggestions (music, SFX, VFX) for user review.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class AssetType(Enum):
    """Type of media asset suggestion."""
    MUSIC = "music"
    SFX = "sfx"
    VFX = "vfx"


class ConfidenceLevel(Enum):
    """Confidence level for AI suggestions."""
    HIGH = "high"      # >= HIGH_CONFIDENCE_THRESHOLD
    MEDIUM = "medium"  # MEDIUM_CONFIDENCE_THRESHOLD - HIGH_CONFIDENCE_THRESHOLD
    LOW = "low"        # < MEDIUM_CONFIDENCE_THRESHOLD


# Confidence score thresholds for classification
HIGH_CONFIDENCE_THRESHOLD = 0.80
MEDIUM_CONFIDENCE_THRESHOLD = 0.60


@dataclass
class TranscriptSegment:
    """A single transcript segment with timing.
    
    Attributes:
        start_time: Start timestamp in seconds
        end_time: End timestamp in seconds
        text: Transcript text content
        speaker: Optional speaker name/identifier
        segment_id: Unique identifier for this segment
    """
    start_time: float
    end_time: float
    text: str
    speaker: Optional[str] = None
    segment_id: str = field(default_factory=lambda: f"seg_{uuid.uuid4().hex[:8]}")
    
    def __post_init__(self):
        """Validate timestamp fields."""
        if self.start_time < 0:
            raise ValueError(f"start_time cannot be negative: {self.start_time}")
        if self.end_time <= self.start_time:
            raise ValueError(
                f"end_time ({self.end_time}) must be greater than start_time ({self.start_time})"
            )
    
    @property
    def duration(self) -> float:
        """Calculate segment duration in seconds."""
        return self.end_time - self.start_time
    
    def format_timestamp(self, time_seconds: Optional[float] = None) -> str:
        """Format time as MM:SS.
        
        Args:
            time_seconds: Time to format (defaults to start_time)
            
        Returns:
            Formatted timestamp string (e.g., "3:45")
        """
        time_to_format = time_seconds if time_seconds is not None else self.start_time
        mins, secs = divmod(int(time_to_format), 60)
        return f"{mins}:{secs:02d}"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text,
            "speaker": self.speaker,
            "segment_id": self.segment_id
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TranscriptSegment":
        """Create from dictionary."""
        return cls(
            start_time=data["start_time"],
            end_time=data["end_time"],
            text=data["text"],
            speaker=data.get("speaker"),
            segment_id=data.get("segment_id", f"seg_{uuid.uuid4().hex[:8]}")
        )


@dataclass
class AssetSuggestion:
    """Base class for AI-suggested assets.
    
    Attributes:
        asset_id: Unique asset identifier
        name: Asset filename
        file_path: Absolute path to asset file
        source_folder: Folder path where asset was found
        confidence: Match confidence score (0.0 - 1.0)
        reasoning: Explanation of why this asset was matched
        position: Timeline position in seconds
        duration: Optional asset duration in seconds
    """
    asset_id: str
    name: str
    file_path: str
    source_folder: str
    confidence: float
    reasoning: str
    position: float
    duration: Optional[float] = None
    
    def __post_init__(self):
        """Validate confidence score."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got {self.confidence}"
            )
        if self.position < 0:
            raise ValueError(f"position cannot be negative: {self.position}")
    
    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get confidence level based on score."""
        if self.confidence >= HIGH_CONFIDENCE_THRESHOLD:
            return ConfidenceLevel.HIGH
        elif self.confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW
    
    def format_position(self) -> str:
        """Format position as MM:SS."""
        mins, secs = divmod(int(self.position), 60)
        return f"{mins}:{secs:02d}"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "file_path": self.file_path,
            "source_folder": self.source_folder,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "position": self.position,
            "duration": self.duration
        }


@dataclass
class MusicSuggestion(AssetSuggestion):
    """AI-suggested music track.
    
    Attributes:
        asset_type: Fixed as AssetType.MUSIC
        fade_in: Optional fade in duration in seconds
        fade_out: Optional fade out duration in seconds
        volume_adjustment: Volume adjustment in dB
    """
    asset_type: AssetType = field(default=AssetType.MUSIC, init=False)
    fade_in: Optional[float] = None
    fade_out: Optional[float] = None
    volume_adjustment: float = 0.0  # dB adjustment
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        base = super().to_dict()
        base.update({
            "asset_type": self.asset_type.value,
            "fade_in": self.fade_in,
            "fade_out": self.fade_out,
            "volume_adjustment": self.volume_adjustment
        })
        return base
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MusicSuggestion":
        """Create from dictionary."""
        return cls(
            asset_id=data["asset_id"],
            name=data["name"],
            file_path=data["file_path"],
            source_folder=data["source_folder"],
            confidence=data["confidence"],
            reasoning=data["reasoning"],
            position=data["position"],
            duration=data.get("duration"),
            fade_in=data.get("fade_in"),
            fade_out=data.get("fade_out"),
            volume_adjustment=data.get("volume_adjustment", 0.0)
        )


@dataclass
class SFXSuggestion(AssetSuggestion):
    """AI-suggested sound effect.
    
    Attributes:
        asset_type: Fixed as AssetType.SFX
        track_number: Which SFX track to place on
        intended_moment: Description of why this SFX is placed here
    """
    asset_type: AssetType = field(default=AssetType.SFX, init=False)
    track_number: int = 1
    intended_moment: str = ""
    
    def __post_init__(self):
        """Validate track number."""
        super().__post_init__()
        if self.track_number < 1:
            raise ValueError(f"track_number must be >= 1, got {self.track_number}")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        base = super().to_dict()
        base.update({
            "asset_type": self.asset_type.value,
            "track_number": self.track_number,
            "intended_moment": self.intended_moment
        })
        return base
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SFXSuggestion":
        """Create from dictionary."""
        return cls(
            asset_id=data["asset_id"],
            name=data["name"],
            file_path=data["file_path"],
            source_folder=data["source_folder"],
            confidence=data["confidence"],
            reasoning=data["reasoning"],
            position=data["position"],
            duration=data.get("duration"),
            track_number=data.get("track_number", 1),
            intended_moment=data.get("intended_moment", "")
        )


@dataclass
class VFXSuggestion(AssetSuggestion):
    """AI-suggested VFX/template.
    
    Attributes:
        asset_type: Fixed as AssetType.VFX
        template_name: Name of the template/effect
        configurable_params: Optional configurable parameters
    """
    asset_type: AssetType = field(default=AssetType.VFX, init=False)
    template_name: str = ""
    configurable_params: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        base = super().to_dict()
        base.update({
            "asset_type": self.asset_type.value,
            "template_name": self.template_name,
            "configurable_params": self.configurable_params
        })
        return base
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VFXSuggestion":
        """Create from dictionary."""
        return cls(
            asset_id=data["asset_id"],
            name=data["name"],
            file_path=data["file_path"],
            source_folder=data["source_folder"],
            confidence=data["confidence"],
            reasoning=data["reasoning"],
            position=data["position"],
            duration=data.get("duration"),
            template_name=data.get("template_name", ""),
            configurable_params=data.get("configurable_params", {})
        )


@dataclass
class RoughCutSection:
    """A section of the rough cut matching format template structure.
    
    Attributes:
        name: Section name (e.g., "intro", "act_1", "outro")
        start_time: Section start time in seconds
        end_time: Section end time in seconds
        transcript_segments: List of transcript segments in this section
        music: Optional music suggestion for this section
        sfx: List of SFX suggestions for this section
        vfx: List of VFX suggestions for this section
    """
    name: str
    start_time: float
    end_time: float
    transcript_segments: list[TranscriptSegment] = field(default_factory=list)
    music: Optional[MusicSuggestion] = None
    sfx: list[SFXSuggestion] = field(default_factory=list)
    vfx: list[VFXSuggestion] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate timing fields."""
        if self.start_time < 0:
            raise ValueError(f"start_time cannot be negative: {self.start_time}")
        if self.end_time <= self.start_time:
            raise ValueError(
                f"end_time ({self.end_time}) must be greater than start_time ({self.start_time})"
            )
    
    @property
    def duration(self) -> float:
        """Calculate section duration in seconds."""
        return self.end_time - self.start_time
    
    def format_time_range(self) -> str:
        """Format time range as "MM:SS - MM:SS"."""
        start_mins, start_secs = divmod(int(self.start_time), 60)
        end_mins, end_secs = divmod(int(self.end_time), 60)
        return f"{start_mins}:{start_secs:02d} - {end_mins}:{end_secs:02d}"
    
    @property
    def transcript_text(self) -> str:
        """Get full transcript text for this section."""
        return " ".join(seg.text for seg in self.transcript_segments)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "transcript_segments": [seg.to_dict() for seg in self.transcript_segments],
            "music": self.music.to_dict() if self.music else None,
            "sfx": [sfx.to_dict() for sfx in self.sfx],
            "vfx": [vfx.to_dict() for vfx in self.vfx]
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoughCutSection":
        """Create from dictionary."""
        music = None
        if data.get("music"):
            music = MusicSuggestion.from_dict(data["music"])
        
        return cls(
            name=data["name"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            transcript_segments=[
                TranscriptSegment.from_dict(seg) 
                for seg in data.get("transcript_segments", [])
            ],
            music=music,
            sfx=[SFXSuggestion.from_dict(sfx) for sfx in data.get("sfx", [])],
            vfx=[VFXSuggestion.from_dict(vfx) for vfx in data.get("vfx", [])]
        )


@dataclass
class RoughCutDocument:
    """Complete AI-generated rough cut document for review.
    
    Attributes:
        title: Document title
        source_clip: Source video clip name/path
        format_template: Format template name used
        total_duration: Total duration in seconds
        sections: List of rough cut sections
        assembly_metadata: Metadata about AI assembly process
        created_at: ISO timestamp when document was created
    """
    title: str
    source_clip: str
    format_template: str
    total_duration: float
    sections: list[RoughCutSection] = field(default_factory=list)
    assembly_metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        """Validate duration."""
        if self.total_duration < 0:
            raise ValueError(f"total_duration cannot be negative: {self.total_duration}")
    
    @property
    def section_count(self) -> int:
        """Get number of sections."""
        return len(self.sections)
    
    @property
    def total_music_suggestions(self) -> int:
        """Count total music suggestions."""
        return sum(1 for s in self.sections if s.music)
    
    @property
    def total_sfx_suggestions(self) -> int:
        """Count total SFX suggestions."""
        return sum(len(s.sfx) for s in self.sections)
    
    @property
    def total_vfx_suggestions(self) -> int:
        """Count total VFX suggestions."""
        return sum(len(s.vfx) for s in self.sections)
    
    @property
    def total_transcript_segments(self) -> int:
        """Count total transcript segments."""
        return sum(len(s.transcript_segments) for s in self.sections)
    
    def get_all_asset_paths(self) -> list[str]:
        """Get all file paths for validation.
        
        Returns:
            List of absolute file paths for all suggested assets
        """
        paths = []
        for section in self.sections:
            if section.music:
                paths.append(section.music.file_path)
            for sfx in section.sfx:
                paths.append(sfx.file_path)
            for vfx in section.vfx:
                paths.append(vfx.file_path)
        return paths
    
    def get_all_asset_suggestions(self) -> list[AssetSuggestion]:
        """Get all asset suggestions across all sections.
        
        Returns:
            List of all music, SFX, and VFX suggestions
        """
        assets: list[AssetSuggestion] = []
        for section in self.sections:
            if section.music:
                assets.append(section.music)
            assets.extend(section.sfx)
            assets.extend(section.vfx)
        return assets
    
    def format_total_duration(self) -> str:
        """Format total duration as MM:SS."""
        mins, secs = divmod(int(self.total_duration), 60)
        return f"{mins}:{secs:02d}"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "source_clip": self.source_clip,
            "format_template": self.format_template,
            "total_duration": self.total_duration,
            "sections": [sec.to_dict() for sec in self.sections],
            "assembly_metadata": self.assembly_metadata,
            "created_at": self.created_at,
            "summary": {
                "section_count": self.section_count,
                "total_music_suggestions": self.total_music_suggestions,
                "total_sfx_suggestions": self.total_sfx_suggestions,
                "total_vfx_suggestions": self.total_vfx_suggestions,
                "total_transcript_segments": self.total_transcript_segments
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoughCutDocument":
        """Create from dictionary."""
        return cls(
            title=data["title"],
            source_clip=data["source_clip"],
            format_template=data["format_template"],
            total_duration=data["total_duration"],
            sections=[
                RoughCutSection.from_dict(sec) 
                for sec in data.get("sections", [])
            ],
            assembly_metadata=data.get("assembly_metadata", {}),
            created_at=data.get("created_at", datetime.now().isoformat())
        )


@dataclass
class DocumentValidationResult:
    """Result of validating a rough cut document.
    
    Attributes:
        is_valid: Whether document passed validation
        errors: List of validation error messages
        warnings: List of validation warnings
        missing_assets: List of asset paths that don't exist
    """
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_assets: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "missing_assets": self.missing_assets
        }
