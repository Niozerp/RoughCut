"""Chunk data structures for context-aware transcript processing.

Provides dataclasses for managing transcript chunks, chunk configuration,
boundary tracking, and chunk processing results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ChunkConfig:
    """Configuration for transcript chunking.
    
    Attributes:
        max_tokens_per_chunk: Maximum tokens allowed per chunk
        overlap_percentage: Percentage of overlap between chunks (0.0-1.0)
        overlap_tokens: Calculated overlap in tokens (computed from percentage)
        respect_sentence_boundaries: Whether to prefer sentence boundaries
        respect_paragraph_boundaries: Whether to prefer paragraph boundaries
        provider_name: AI provider name for token limit lookup
    """
    max_tokens_per_chunk: int = 4000  # Conservative default
    overlap_percentage: float = 0.1  # 10% overlap
    overlap_tokens: int = field(init=False)  # Calculated from percentage
    respect_sentence_boundaries: bool = True
    respect_paragraph_boundaries: bool = True
    provider_name: str = "openai"
    
    def __post_init__(self):
        """Calculate overlap_tokens from percentage with validation."""
        # Validate overlap_percentage bounds
        if not 0.0 < self.overlap_percentage <= 0.5:
            raise ValueError(
                f"overlap_percentage must be between 0.0 and 0.5, got {self.overlap_percentage}"
            )
        # Validate max_tokens_per_chunk
        if self.max_tokens_per_chunk < 100:
            raise ValueError(
                f"max_tokens_per_chunk must be at least 100, got {self.max_tokens_per_chunk}"
            )
        self.overlap_tokens = int(self.max_tokens_per_chunk * self.overlap_percentage)


@dataclass
class TranscriptChunk:
    """A single chunk of transcript for processing.
    
    Attributes:
        index: 0-based chunk index
        text: Chunk text content
        start_time: Start timestamp in seconds
        end_time: End timestamp in seconds
        segments: Original segment references
        overlap_with_previous: Text overlap from previous chunk
        overlap_with_next: Text overlap for next chunk (empty until processed)
        estimated_tokens: Estimated token count
    """
    index: int
    text: str
    start_time: float
    end_time: float
    segments: list[dict]
    overlap_with_previous: str
    overlap_with_next: str
    estimated_tokens: int
    
    def __post_init__(self):
        """Validate timestamp fields."""
        if self.start_time < 0:
            raise ValueError(f"start_time cannot be negative: {self.start_time}")
        if self.end_time <= self.start_time:
            raise ValueError(
                f"end_time ({self.end_time}) must be greater than start_time ({self.start_time})"
            )
    
    def get_continuity_context(self) -> str:
        """Return context string for continuity preservation.
        
        Returns:
            String describing chunk position and context
        """
        return (
            f"Chunk {self.index}: {self.start_time:.1f}s to {self.end_time:.1f}s. "
            f"Previous context: {self.overlap_with_previous[:100]}..."
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of chunk
        """
        return {
            "index": self.index,
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "segments": self.segments,
            "overlap_with_previous": self.overlap_with_previous,
            "overlap_with_next": self.overlap_with_next,
            "estimated_tokens": self.estimated_tokens
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TranscriptChunk":
        """Create from dictionary.
        
        Args:
            data: Dictionary with chunk data
            
        Returns:
            TranscriptChunk instance
        """
        return cls(
            index=data["index"],
            text=data["text"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            segments=data.get("segments", []),
            overlap_with_previous=data.get("overlap_with_previous", ""),
            overlap_with_next=data.get("overlap_with_next", ""),
            estimated_tokens=data.get("estimated_tokens", 0)
        )


@dataclass
class ChunkBoundary:
    """Marker for chunk boundaries and continuity.
    
    Attributes:
        chunk_index: Index of chunk this boundary belongs to
        boundary_type: Type of boundary (sentence, paragraph, speaker_change, forced)
        timestamp: Timestamp in seconds where boundary occurs
        narrative_context: Brief summary of ending context for continuity
    """
    chunk_index: int
    boundary_type: str
    timestamp: float
    narrative_context: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "chunk_index": self.chunk_index,
            "boundary_type": self.boundary_type,
            "timestamp": self.timestamp,
            "narrative_context": self.narrative_context
        }


@dataclass
class ChunkContext:
    """Context for asset filtering per chunk.
    
    Attributes:
        section_type: Type of section (intro, narrative, outro, etc.)
        tone: Emotional tone (upbeat, contemplative, tense, etc.)
        required_categories: List of required asset category IDs
        time_range: Tuple of (start, end) in seconds
        relevant_tags: Tags to filter assets by
    """
    section_type: str
    tone: str
    required_categories: list[str]
    time_range: tuple[float, float]
    relevant_tags: list[str]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "section_type": self.section_type,
            "tone": self.tone,
            "required_categories": self.required_categories,
            "time_range": list(self.time_range),
            "relevant_tags": self.relevant_tags
        }


@dataclass
class ChunkResult:
    """Result from processing a single chunk.
    
    Attributes:
        chunk_index: Index of chunk this result is for
        transcript_cuts: List of transcript cuts from this chunk
        music_matches: List of music matches from this chunk
        sfx_matches: List of SFX matches from this chunk
        vfx_matches: List of VFX matches from this chunk
        continuity_markers: List of chunk boundary markers
        tokens_used: Number of tokens used for this chunk
        processing_time_ms: Processing time in milliseconds
        status: Status of chunk processing (success, failed, partial)
        warnings: List of warning messages
    """
    chunk_index: int
    transcript_cuts: list[dict]
    music_matches: list[dict]
    sfx_matches: list[dict]
    vfx_matches: list[dict]
    continuity_markers: list[ChunkBoundary]
    tokens_used: int
    processing_time_ms: int
    status: str  # "success", "failed", "partial"
    warnings: list[str]
    
    def __post_init__(self):
        """Validate status field."""
        valid_statuses = ["success", "failed", "partial"]
        if self.status not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}, got {self.status}")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "chunk_index": self.chunk_index,
            "transcript_cuts": self.transcript_cuts,
            "music_matches": self.music_matches,
            "sfx_matches": self.sfx_matches,
            "vfx_matches": self.vfx_matches,
            "continuity_markers": [m.to_dict() for m in self.continuity_markers],
            "tokens_used": self.tokens_used,
            "processing_time_ms": self.processing_time_ms,
            "status": self.status,
            "warnings": self.warnings
        }


@dataclass
class AssembledRoughCut:
    """Final assembled rough cut from all chunks.
    
    Attributes:
        transcript_segments: List of transcript segments from all chunks
        music_matches: List of music matches from all chunks
        sfx_matches: List of SFX matches from all chunks
        vfx_matches: List of VFX matches from all chunks
        assembly_metadata: Metadata about the assembly process
        continuity_validation: Results of continuity validation
    """
    transcript_segments: list[dict]
    music_matches: list[dict]
    sfx_matches: list[dict]
    vfx_matches: list[dict]
    assembly_metadata: dict[str, Any]
    continuity_validation: dict[str, Any]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "transcript_segments": self.transcript_segments,
            "music_matches": self.music_matches,
            "sfx_matches": self.sfx_matches,
            "vfx_matches": self.vfx_matches,
            "assembly_metadata": self.assembly_metadata,
            "continuity_validation": self.continuity_validation
        }


@dataclass
class ChunkProgress:
    """Progress information for chunked processing.
    
    Attributes:
        current_chunk: Current chunk being processed (1-indexed for display)
        total_chunks: Total number of chunks
        chunk_phase: Current phase (initializing, processing, assembling)
        message: Human-readable progress message
        eta_seconds: Estimated time remaining in seconds
        overall_progress_percent: Overall progress percentage (0-100)
    """
    current_chunk: int
    total_chunks: int
    chunk_phase: str
    message: str
    eta_seconds: int
    overall_progress_percent: int
    
    def __post_init__(self):
        """Validate chunk_phase field."""
        valid_phases = ["initializing", "processing", "assembling", "complete"]
        if self.chunk_phase not in valid_phases:
            raise ValueError(f"chunk_phase must be one of {valid_phases}, got {self.chunk_phase}")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "current_chunk": self.current_chunk,
            "total_chunks": self.total_chunks,
            "chunk_phase": self.chunk_phase,
            "message": self.message,
            "eta_seconds": self.eta_seconds,
            "overall_progress_percent": self.overall_progress_percent
        }
