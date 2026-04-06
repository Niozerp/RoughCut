"""Context chunker for managing AI context window limitations.

Provides the ContextChunker class for splitting long transcripts into
overlapping, context-aware chunks while preserving narrative continuity.
"""

from __future__ import annotations

import re
from typing import Optional

from .chunk import (
    ChunkConfig,
    ChunkBoundary,
    TranscriptChunk,
)


#: Provider-specific token limits for different AI models
PROVIDER_TOKEN_LIMITS = {
    "openai": {
        "gpt-4": 8192,
        "gpt-4-turbo": 128000,
        "gpt-4o": 128000,
        "gpt-3.5-turbo": 16385,
    },
    "claude": {
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000,
    },
    "openrouter": {
        # Anthropic models via OpenRouter
        "anthropic/claude-3.5-sonnet": 200000,
        "anthropic/claude-3.5-sonnet-beta": 200000,
        "anthropic/claude-3-opus": 200000,
        "anthropic/claude-3-sonnet": 200000,
        "anthropic/claude-3-haiku": 200000,
        # OpenAI models via OpenRouter
        "openai/gpt-4o": 128000,
        "openai/gpt-4o-mini": 128000,
        "openai/gpt-4-turbo": 128000,
        "openai/gpt-4": 8192,
        "openai/gpt-3.5-turbo": 16385,
        # Meta models via OpenRouter
        "meta-llama/llama-3.1-70b-instruct": 131072,
        "meta-llama/llama-3.1-405b-instruct": 131072,
        # Google models via OpenRouter
        "google/gemini-pro": 128000,
        "google/gemini-pro-1.5": 1000000,
        # Mistral models via OpenRouter
        "mistralai/mistral-large": 128000,
    },
    "default": 4000  # Conservative fallback
}

#: Safety margin for prompt overhead (30% reserved for system prompts, etc.)
TOKEN_SAFETY_MARGIN = 0.7

#: Semantic boundary detection priority (highest to lowest)
BOUNDARY_PRIORITY = [
    "speaker_change",      # Highest priority - natural break
    "paragraph_break",     # Major content break
    "sentence_end",        # Standard break
    "pause_3sec_plus",     # Long pause in transcript
    "forced",             # Last resort - mid-sentence split
]

#: Approximate characters per token for estimation
CHARS_PER_TOKEN = 4


def estimate_token_count(text: str) -> int:
    """Estimate token count for text.
    
    Uses a simple approximation of 4 characters per token.
    
    Args:
        text: Text to estimate tokens for
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    return (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


class ContextChunker:
    """Chunks transcripts into overlapping segments for AI processing.
    
    Handles context window limitations by intelligently splitting long
    transcripts while preserving narrative continuity through overlap
    and boundary detection.
    
    Attributes:
        config: ChunkConfig instance with chunking parameters
    """
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        """Initialize chunker with configuration.
        
        Args:
            config: ChunkConfig instance. If None, uses default config.
        """
        self.config = config or ChunkConfig()
    
    def calculate_optimal_chunk_size(
        self,
        transcript_text: str,
        model_name: Optional[str] = None
    ) -> tuple[int, bool]:
        """Calculate optimal chunk size and determine if chunking is needed.
        
        Args:
            transcript_text: Full transcript text
            model_name: Specific model name (e.g., "gpt-4-turbo"). If None,
                       uses the provider's default model.
            
        Returns:
            Tuple of (chunk_size_in_tokens, needs_chunking)
        """
        total_tokens = estimate_token_count(transcript_text)
        
        # Get provider limit
        provider_limit = self._get_provider_token_limit(
            self.config.provider_name,
            model_name
        )
        
        # Apply safety margin
        effective_limit = int(provider_limit * TOKEN_SAFETY_MARGIN)
        
        # Check if chunking is needed
        needs_chunking = total_tokens > effective_limit
        
        if needs_chunking:
            # Calculate how many chunks needed
            num_chunks = (total_tokens + effective_limit - 1) // effective_limit
            # Add margin for overlap
            chunk_size = (total_tokens // num_chunks) + self.config.overlap_tokens
            return chunk_size, True
        else:
            # No chunking needed, return total as chunk size
            return total_tokens, False
    
    def _get_provider_token_limit(
        self,
        provider_name: str,
        model_name: Optional[str] = None
    ) -> int:
        """Get token limit for provider and model.
        
        Args:
            provider_name: Provider name ("openai", "claude", etc.)
            model_name: Specific model name. If None, uses provider's first model.
            
        Returns:
            Token limit for the provider/model
        """
        provider_limits = PROVIDER_TOKEN_LIMITS.get(provider_name, {})
        
        if isinstance(provider_limits, dict):
            # Provider has multiple models
            if model_name and model_name in provider_limits:
                return provider_limits[model_name]
            elif provider_limits:
                # Return the first (highest) limit
                return max(provider_limits.values())
            else:
                return PROVIDER_TOKEN_LIMITS["default"]
        else:
            # Provider has single limit
            return provider_limits or PROVIDER_TOKEN_LIMITS["default"]
    
    def chunk_transcript(
        self,
        segments: list[dict],
        full_text: Optional[str] = None
    ) -> list[TranscriptChunk]:
        """Split transcript segments into overlapping chunks.
        
        Args:
            segments: List of transcript segment dictionaries with
                     keys: start, end, text, speaker (optional)
            full_text: Optional pre-computed full transcript text
            
        Returns:
            List of TranscriptChunk instances
        """
        if not segments:
            return []
        
        # Compute full text if not provided
        if full_text is None:
            full_text = " ".join(s.get("text") or "" for s in segments)
        
        # Check if chunking is needed
        chunk_size, needs_chunking = self.calculate_optimal_chunk_size(full_text)
        
        if not needs_chunking:
            # Return single chunk with all segments
            return [self._create_single_chunk(segments)]
        
        # Perform chunking
        return self._perform_chunking(segments, chunk_size)
    
    def _create_single_chunk(self, segments: list[dict]) -> TranscriptChunk:
        """Create a single chunk from all segments.
        
        Args:
            segments: List of transcript segments
            
        Returns:
            TranscriptChunk containing all segments
        """
        full_text = " ".join(s.get("text") or "" for s in segments)
        start_time = segments[0].get("start", 0.0) if segments else 0.0
        end_time = segments[-1].get("end", 0.0) if segments else 0.0
        
        return TranscriptChunk(
            index=0,
            text=full_text,
            start_time=start_time,
            end_time=end_time,
            segments=segments,
            overlap_with_previous="",
            overlap_with_next="",
            estimated_tokens=estimate_token_count(full_text)
        )
    
    def _perform_chunking(
        self,
        segments: list[dict],
        target_chunk_size: int
    ) -> list[TranscriptChunk]:
        """Perform intelligent chunking of segments.
        
        Args:
            segments: List of transcript segments
            target_chunk_size: Target size in tokens per chunk
            
        Returns:
            List of TranscriptChunk instances
        """
        chunks = []
        current_chunk_segments = []
        current_chunk_tokens = 0
        chunk_index = 0
        
        for i, segment in enumerate(segments):
            segment_text = segment.get("text", "")
            segment_tokens = estimate_token_count(segment_text)
            
            # Check if adding this segment would exceed target size
            if current_chunk_tokens + segment_tokens > target_chunk_size and current_chunk_segments:
                # Find optimal boundary for ending this chunk
                boundary = self._find_boundary(
                    current_chunk_segments,
                    target_chunk_size,
                    segments[i:],
                    chunk_index
                )
                
                # Create chunk
                chunk = self._create_chunk_from_segments(
                    chunk_index,
                    current_chunk_segments,
                    boundary,
                    segments[i:]
                )
                chunks.append(chunk)
                chunk_index += 1
                
                # Start new chunk with overlap
                overlap_segments = self._calculate_overlap(
                    current_chunk_segments,
                    self.config.overlap_tokens
                )
                current_chunk_segments = overlap_segments + [segment]
                current_chunk_tokens = sum(
                    estimate_token_count(s.get("text", ""))
                    for s in current_chunk_segments
                )
            else:
                current_chunk_segments.append(segment)
                current_chunk_tokens += segment_tokens
        
        # Create final chunk if there are remaining segments
        if current_chunk_segments:
            chunk = self._create_chunk_from_segments(
                chunk_index,
                current_chunk_segments,
                None,
                []
            )
            chunks.append(chunk)
        
        # Set up overlaps between chunks
        return self._setup_chunk_overlaps(chunks)
    
    def _find_boundary(
        self,
        current_segments: list[dict],
        target_size: int,
        next_segments: list[dict],
        chunk_index: int = 0
    ) -> Optional[ChunkBoundary]:
        """Find optimal boundary for chunk ending.
        
        Args:
            current_segments: Segments in current chunk
            target_size: Target chunk size in tokens
            next_segments: Segments that will be in next chunk
            chunk_index: Index of the current chunk
            
        Returns:
            ChunkBoundary or None
        """
        if not current_segments:
            return None
        
        last_segment = current_segments[-1]
        end_time = last_segment.get("end", 0.0)
        
        # Check for speaker change
        if next_segments and len(current_segments) >= 2:
            current_speaker = last_segment.get("speaker")
            next_speaker = next_segments[0].get("speaker")
            if current_speaker and next_speaker and current_speaker != next_speaker:
                return ChunkBoundary(
                    chunk_index=chunk_index,
                    boundary_type="speaker_change",
                    timestamp=end_time,
                    narrative_context=f"Speaker changes from {current_speaker} to {next_speaker}"
                )
        
        # Check for sentence end in last segment
        last_text = last_segment.get("text", "")
        if last_text.rstrip().endswith((".", "!", "?")):
            return ChunkBoundary(
                chunk_index=chunk_index,
                boundary_type="sentence_end",
                timestamp=end_time,
                narrative_context=last_text[-50:] if len(last_text) > 50 else last_text
            )
        
        # Check for paragraph break (double newline)
        if "\n\n" in last_text[-100:]:
            return ChunkBoundary(
                chunk_index=chunk_index,
                boundary_type="paragraph_break",
                timestamp=end_time,
                narrative_context="Paragraph break"
            )
        
        # Check for long pause
        if next_segments:
            pause_duration = next_segments[0].get("start", end_time) - end_time
            if pause_duration >= 3.0:
                return ChunkBoundary(
                    chunk_index=chunk_index,
                    boundary_type="pause_3sec_plus",
                    timestamp=end_time,
                    narrative_context=f"{pause_duration:.1f}s pause"
                )
        
        # Forced boundary
        return ChunkBoundary(
            chunk_index=chunk_index,
            boundary_type="forced",
            timestamp=end_time,
            narrative_context="Mid-sentence split (forced)"
        )
    
    def _create_chunk_from_segments(
        self,
        index: int,
        segments: list[dict],
        boundary: Optional[ChunkBoundary],
        next_segments: list[dict]
    ) -> TranscriptChunk:
        """Create a TranscriptChunk from segments.
        
        Args:
            index: Chunk index
            segments: List of segments for this chunk
            boundary: Optional boundary information
            next_segments: Segments that follow (for context)
            
        Returns:
            TranscriptChunk instance
        """
        text = " ".join(s.get("text", "") for s in segments)
        start_time = segments[0].get("start", 0.0) if segments else 0.0
        end_time = segments[-1].get("end", 0.0) if segments else 0.0
        
        # Calculate overlap text (last portion for next chunk context)
        overlap_text = ""
        if segments and self.config.overlap_tokens > 0:
            overlap_chars = self.config.overlap_tokens * CHARS_PER_TOKEN
            overlap_text = text[-overlap_chars:] if len(text) > overlap_chars else text
        
        return TranscriptChunk(
            index=index,
            text=text,
            start_time=start_time,
            end_time=end_time,
            segments=segments,
            overlap_with_previous="",  # Set later by _setup_chunk_overlaps
            overlap_with_next=overlap_text,
            estimated_tokens=estimate_token_count(text)
        )
    
    def _calculate_overlap(
        self,
        segments: list[dict],
        overlap_tokens: int
    ) -> list[dict]:
        """Calculate which segments should overlap to next chunk.
        
        Args:
            segments: Current chunk segments
            overlap_tokens: Number of tokens to overlap
            
        Returns:
            List of segments to include in overlap
        """
        if not segments or overlap_tokens <= 0:
            return []
        
        overlap_segments = []
        current_tokens = 0
        
        # Work backwards from end
        for segment in reversed(segments):
            segment_tokens = estimate_token_count(segment.get("text", ""))
            if current_tokens + segment_tokens <= overlap_tokens:
                overlap_segments.insert(0, segment)
                current_tokens += segment_tokens
            else:
                break
        
        return overlap_segments
    
    def _setup_chunk_overlaps(
        self,
        chunks: list[TranscriptChunk]
    ) -> list[TranscriptChunk]:
        """Set up overlap references between chunks.
        
        Args:
            chunks: List of chunks to connect
            
        Returns:
            List of chunks with overlaps set
        """
        if len(chunks) <= 1:
            return chunks
        
        for i, chunk in enumerate(chunks):
            if i > 0:
                # Set overlap from previous chunk
                prev_chunk = chunks[i - 1]
                chunk.overlap_with_previous = prev_chunk.overlap_with_next
        
        return chunks
