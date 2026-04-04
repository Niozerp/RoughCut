"""Media pool models for Resolve integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class MediaType(Enum):
    """Type of media item in Resolve Media Pool."""
    VIDEO = "video"
    AUDIO = "audio"
    STILL_IMAGE = "still_image"


@dataclass
class MediaPoolItem:
    """
    Represents a single item from Resolve's Media Pool.
    
    Captures clip metadata needed for selection and processing.
    
    Attributes:
        clip_name: Display name of the clip
        file_path: Absolute path to the media file
        duration_seconds: Duration in seconds
        clip_id: Resolve's unique identifier for the clip
        media_type: Type of media (video, audio, still_image)
        thumbnail_path: Optional path to thumbnail preview
    
    Example:
        >>> item = MediaPoolItem(
        ...     clip_name="interview_take1",
        ...     file_path="/projects/interview.mov",
        ...     duration_seconds=2280.5,
        ...     clip_id="resolve_clip_001"
        ... )
        >>> item.is_transcribable()
        True
    """
    clip_name: str
    file_path: str
    duration_seconds: float
    clip_id: str
    media_type: MediaType = MediaType.VIDEO
    thumbnail_path: Optional[str] = None
    
    def __post_init__(self):
        """Validate media pool item on creation."""
        if not self.clip_name or not self.clip_name.strip():
            raise ValueError("clip_name is required")
        
        if not self.file_path or not self.file_path.strip():
            raise ValueError("file_path is required")
        
        if self.duration_seconds <= 0:
            raise ValueError(f"duration_seconds must be > 0, got {self.duration_seconds}")
        
        if not isinstance(self.media_type, MediaType):
            raise ValueError(f"media_type must be MediaType enum, got {type(self.media_type)}")
    
    def is_transcribable(self) -> bool:
        """
        Check if this media can be transcribed by Resolve.
        
        Must be video with audio track (represented by VIDEO type
        with positive duration).
        
        Returns:
            True if the media is transcribable, False otherwise.
        """
        return self.media_type == MediaType.VIDEO and self.duration_seconds > 0
    
    def to_dict(self) -> dict[str, Any]:
        """
        Serialize for protocol responses.
        
        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return {
            'clip_name': self.clip_name,
            'file_path': self.file_path,
            'duration_seconds': self.duration_seconds,
            'clip_id': self.clip_id,
            'media_type': self.media_type.value,
            'thumbnail_path': self.thumbnail_path,
            'is_transcribable': self.is_transcribable()
        }
    
    @classmethod
    def from_resolve_clip(cls, clip_data: dict[str, Any]) -> MediaPoolItem:
        """
        Create MediaPoolItem from Resolve API clip data.
        
        Args:
            clip_data: Dictionary containing Resolve clip metadata.
                Expected keys: 'name', 'path', 'duration', 'id', 'type' (optional),
                'thumbnail' (optional)
        
        Returns:
            MediaPoolItem instance populated from Resolve data.
        
        Example:
            >>> clip_data = {
            ...     'name': 'interview_take1',
            ...     'path': '/projects/interview.mov',
            ...     'duration': 2280.5,
            ...     'id': 'resolve_001',
            ...     'type': 'video'
            ... }
            >>> item = MediaPoolItem.from_resolve_clip(clip_data)
        """
        # Map Resolve's media type to our enum
        resolve_type = clip_data.get('type', '').lower()
        
        # ECH-03 fix: More robust type detection with explicit ordering
        # Check for exact matches first, then substring matches
        if resolve_type in ('video', 'videoclip', 'movie'):
            media_type = MediaType.VIDEO
        elif 'video' in resolve_type or 'movie' in resolve_type:
            # Substring match for variations like 'my_video_file', 'videofile', etc.
            media_type = MediaType.VIDEO
        elif resolve_type in ('audio', 'sound', 'audioclip'):
            media_type = MediaType.AUDIO
        elif 'audio' in resolve_type or 'sound' in resolve_type:
            media_type = MediaType.AUDIO
        else:
            media_type = MediaType.STILL_IMAGE
        
        return cls(
            clip_name=clip_data.get('name', ''),
            file_path=clip_data.get('path', ''),
            duration_seconds=float(clip_data.get('duration', 0)),
            clip_id=clip_data.get('id', ''),
            media_type=media_type,
            thumbnail_path=clip_data.get('thumbnail')
        )
