"""Database models for media assets and indexing state.

Defines dataclasses for media asset metadata and index state tracking
with validation, serialization, and database operations support.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import hashlib
import uuid


@dataclass
class MediaAsset:
    """Represents an indexed media asset.
    
    Attributes:
        id: Unique identifier (UUID or hash-based)
        file_path: Absolute path to the media file
        file_name: Name of the file
        category: Asset category ("music", "sfx", "vfx")
        file_size: File size in bytes
        modified_time: Last modification timestamp
        file_hash: MD5 hash for change detection
        ai_tags: List of AI-generated tags (populated in Story 2.3)
        created_at: Timestamp when asset was first indexed
        updated_at: Timestamp when asset was last updated
    """
    id: str
    file_path: Path
    file_name: str
    category: str
    file_size: int
    modified_time: datetime
    file_hash: str
    ai_tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        now = datetime.now()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
    
    @classmethod
    def from_file_path(
        cls,
        file_path: Path,
        category: str,
        file_hash: Optional[str] = None
    ) -> 'MediaAsset':
        """Create a MediaAsset from a file path.
        
        Args:
            file_path: Path to the media file
            category: Asset category (music, sfx, vfx)
            file_hash: Optional pre-computed file hash
            
        Returns:
            MediaAsset instance populated from file metadata
        """
        # Validate path is safe (no traversal outside intended directory)
        resolved_path = file_path.resolve()
        if not cls._is_path_safe(resolved_path):
            raise ValueError(f"Path traversal detected: {file_path}")
        
        stat = file_path.stat()
        
        # Compute hash if not provided
        if file_hash is None:
            file_hash = cls._compute_file_hash(file_path)
        
        return cls(
            id=str(uuid.uuid4()),
            file_path=resolved_path,
            file_name=file_path.name,
            category=category,
            file_size=stat.st_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime),
            file_hash=file_hash
        )
    
    @staticmethod
    def _is_path_safe(resolved_path: Path) -> bool:
        """Check if resolved path is safe (no traversal attempts).
        
        This is a basic check. Full validation should be done at the 
        folder configuration level to ensure path stays within media folders.
        
        Args:
            resolved_path: Absolute resolved path to check
            
        Returns:
            True if path appears safe, False otherwise
        """
        path_str = str(resolved_path)
        
        # Check for null bytes
        if '\x00' in path_str:
            return False
        
        # Check for common traversal patterns in the original path components
        # This catches attempts like ../../../etc/passwd
        for part in resolved_path.parts:
            if part == '..':
                return False
        
        return True
    
    @staticmethod
    def _compute_file_hash(file_path: Path) -> str:
        """Compute MD5 hash of file content.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hex digest of MD5 hash
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of the asset
        """
        return {
            'id': self.id,
            'file_path': str(self.file_path),
            'file_name': self.file_name,
            'category': self.category,
            'file_size': self.file_size,
            'modified_time': self.modified_time.isoformat(),
            'file_hash': self.file_hash,
            'ai_tags': self.ai_tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MediaAsset':
        """Create MediaAsset from dictionary.
        
        Args:
            data: Dictionary containing asset data
            
        Returns:
            MediaAsset instance
        """
        return cls(
            id=data['id'],
            file_path=Path(data['file_path']),
            file_name=data['file_name'],
            category=data['category'],
            file_size=data['file_size'],
            modified_time=datetime.fromisoformat(data['modified_time']),
            file_hash=data['file_hash'],
            ai_tags=data.get('ai_tags', []),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )
    
    def has_changed(self) -> bool:
        """Check if the file has been modified since last index.
        
        Returns:
            True if file has been modified, False otherwise
        """
        try:
            current_mtime = datetime.fromtimestamp(self.file_path.stat().st_mtime)
            if current_mtime != self.modified_time:
                # File timestamp changed, verify with hash
                current_hash = self._compute_file_hash(self.file_path)
                return current_hash != self.file_hash
            return False
        except (FileNotFoundError, OSError):
            # File no longer exists
            return True


@dataclass
class IndexState:
    """Tracks indexing state for incremental scans.
    
    Attributes:
        last_index_time: Timestamp of last successful index
        folder_configs: Dictionary mapping category to folder path
        total_assets_indexed: Total count of indexed assets
        index_version: Version string for index format
    """
    last_index_time: Optional[datetime] = None
    folder_configs: Dict[str, Optional[str]] = field(default_factory=dict)
    total_assets_indexed: int = 0
    index_version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of the index state
        """
        return {
            'last_index_time': self.last_index_time.isoformat() if self.last_index_time else None,
            'folder_configs': self.folder_configs,
            'total_assets_indexed': self.total_assets_indexed,
            'index_version': self.index_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IndexState':
        """Create IndexState from dictionary.
        
        Args:
            data: Dictionary containing index state data
            
        Returns:
            IndexState instance
        """
        last_index_time = None
        if data.get('last_index_time'):
            try:
                last_index_time = datetime.fromisoformat(data['last_index_time'])
            except ValueError:
                last_index_time = None
        
        return cls(
            last_index_time=last_index_time,
            folder_configs=data.get('folder_configs', {}),
            total_assets_indexed=data.get('total_assets_indexed', 0),
            index_version=data.get('index_version', '1.0')
        )
    
    def update_last_index_time(self):
        """Update the last index time to now."""
        self.last_index_time = datetime.now()


@dataclass
class IndexResult:
    """Result of an indexing operation.
    
    Attributes:
        indexed_count: Number of assets indexed in this operation
        new_count: Number of new assets added
        modified_count: Number of modified assets updated
        moved_count: Number of moved assets updated (re-indexing only)
        deleted_count: Number of deleted assets removed
        total_scanned: Total files scanned (re-indexing only)
        duration_ms: Operation duration in milliseconds
        errors: List of error messages encountered
    """
    indexed_count: int = 0
    new_count: int = 0
    modified_count: int = 0
    moved_count: int = 0
    deleted_count: int = 0
    total_scanned: int = 0
    duration_ms: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON-RPC responses."""
        return {
            'indexed_count': self.indexed_count,
            'new_count': self.new_count,
            'modified_count': self.modified_count,
            'moved_count': self.moved_count,
            'deleted_count': self.deleted_count,
            'total_scanned': self.total_scanned,
            'duration_ms': self.duration_ms,
            'errors': self.errors
        }


@dataclass
class ScanResult:
    """Result of a filesystem scan for changes.
    
    Attributes:
        new_files: List of new file paths detected
        modified_files: List of modified file paths
        deleted_files: List of asset IDs for deleted files
        total_scanned: Total number of files scanned
    """
    new_files: List[Path] = field(default_factory=list)
    modified_files: List[Path] = field(default_factory=list)
    deleted_files: List[str] = field(default_factory=list)
    total_scanned: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'new_files': [str(p) for p in self.new_files],
            'modified_files': [str(p) for p in self.modified_files],
            'deleted_files': self.deleted_files,
            'total_scanned': self.total_scanned
        }


@dataclass
class TranscriptSegment:
    """Represents a single segment of a transcript with timecodes.
    
    Attributes:
        start_time: Start time in seconds
        end_time: End time in seconds
        text: Text content for this segment
        speaker: Optional speaker label (e.g., "Speaker 1", "John")
    """
    start_time: float
    end_time: float
    text: str
    speaker: Optional[str] = None
    
    def __post_init__(self):
        """Validate segment timing."""
        if self.start_time < 0:
            raise ValueError(f"start_time must be >= 0, got {self.start_time}")
        if self.end_time < 0:
            raise ValueError(f"end_time must be >= 0, got {self.end_time}")
        if self.start_time >= self.end_time:
            raise ValueError(f"start_time ({self.start_time}) must be < end_time ({self.end_time})")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'start_time': self.start_time,
            'end_time': self.end_time,
            'text': self.text,
            'speaker': self.speaker
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranscriptSegment':
        """Create TranscriptSegment from dictionary."""
        try:
            start_time = float(data.get('start_time', 0))
        except (ValueError, TypeError):
            start_time = 0.0
        
        try:
            end_time = float(data.get('end_time', 0))
        except (ValueError, TypeError):
            end_time = 0.0
        
        return cls(
            start_time=start_time,
            end_time=end_time,
            text=data.get('text', ''),
            speaker=data.get('speaker')
        )


@dataclass
class Transcript:
    """Represents a complete transcript with metadata.
    
    Attributes:
        text: Full transcript text
        word_count: Total word count
        duration_seconds: Clip duration in seconds
        has_speaker_labels: Whether speaker separation exists
        confidence_score: Optional quality metric (0.0-1.0)
        segments: Optional list of time-coded segments
    """
    text: str
    word_count: int
    duration_seconds: float
    has_speaker_labels: bool = False
    confidence_score: Optional[float] = None
    segments: Optional[List[TranscriptSegment]] = None
    
    def __post_init__(self):
        """Validate transcript data on creation."""
        if self.word_count < 0:
            raise ValueError(f"word_count must be >= 0, got {self.word_count}")
        
        if self.duration_seconds <= 0:
            raise ValueError(f"duration_seconds must be > 0, got {self.duration_seconds}")
        
        if self.confidence_score is not None:
            import math
            if math.isnan(self.confidence_score):
                raise ValueError("confidence_score cannot be NaN")
            if not 0.0 <= self.confidence_score <= 1.0:
                raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {self.confidence_score}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON-RPC responses."""
        result = {
            'text': self.text,
            'word_count': self.word_count,
            'duration_seconds': self.duration_seconds,
            'has_speaker_labels': self.has_speaker_labels,
            'confidence_score': self.confidence_score,
            'segments': None
        }
        
        if self.segments is not None:
            result['segments'] = [s.to_dict() for s in self.segments]
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transcript':
        """Create Transcript from dictionary.
        
        Args:
            data: Dictionary containing transcript data
            
        Returns:
            Transcript instance
        """
        segments = None
        raw_segments = data.get('segments')
        if raw_segments is not None and isinstance(raw_segments, list):
            segments = [TranscriptSegment.from_dict(s) for s in raw_segments]
        
        # Safely convert numeric values
        try:
            word_count = int(data.get('word_count', 0))
        except (ValueError, TypeError):
            word_count = 0
        
        try:
            duration_seconds = float(data.get('duration_seconds', 0))
        except (ValueError, TypeError):
            duration_seconds = 0.0
        
        return cls(
            text=data.get('text', ''),
            word_count=word_count,
            duration_seconds=duration_seconds,
            has_speaker_labels=bool(data.get('has_speaker_labels', False)),
            confidence_score=data.get('confidence_score'),
            segments=segments
        )
    
    def get_formatted_text(self) -> str:
        """Get transcript text formatted with speaker labels.
        
        Returns:
            Formatted transcript text with speaker labels if available
        """
        if not self.segments:
            return self.text
        
        lines = []
        for segment in self.segments:
            if segment.speaker:
                lines.append(f"{segment.speaker}: {segment.text}")
            else:
                lines.append(segment.text)
        
        return '\n'.join(lines)
