"""Unit tests for chunk data structures and chunker module.

Tests cover ChunkConfig, TranscriptChunk, ChunkBoundary, ChunkContext,
ChunkResult, AssembledRoughCut, and ChunkProgress dataclasses, as well as
ContextChunker functionality.
"""

from __future__ import annotations

import pytest

from roughcut.backend.ai.chunk import (
    ChunkConfig,
    ChunkContext,
    ChunkBoundary,
    ChunkProgress,
    ChunkResult,
    AssembledRoughCut,
    TranscriptChunk,
)
from roughcut.backend.ai.chunker import (
    ContextChunker,
    PROVIDER_TOKEN_LIMITS,
    TOKEN_SAFETY_MARGIN,
    BOUNDARY_PRIORITY,
    estimate_token_count,
)


class TestChunkConfig:
    """Tests for ChunkConfig dataclass."""
    
    def test_default_initialization(self):
        """Test ChunkConfig with default values."""
        config = ChunkConfig()
        assert config.max_tokens_per_chunk == 4000
        assert config.overlap_percentage == 0.1
        assert config.overlap_tokens == 400  # 10% of 4000
        assert config.respect_sentence_boundaries is True
        assert config.respect_paragraph_boundaries is True
        assert config.provider_name == "openai"
    
    def test_custom_initialization(self):
        """Test ChunkConfig with custom values."""
        config = ChunkConfig(
            max_tokens_per_chunk=8000,
            overlap_percentage=0.15,
            respect_sentence_boundaries=False,
            provider_name="claude"
        )
        assert config.max_tokens_per_chunk == 8000
        assert config.overlap_percentage == 0.15
        assert config.overlap_tokens == 1200  # 15% of 8000
        assert config.respect_sentence_boundaries is False
        assert config.provider_name == "claude"
    
    def test_overlap_tokens_calculation(self):
        """Test that overlap_tokens is calculated correctly."""
        config = ChunkConfig(max_tokens_per_chunk=10000, overlap_percentage=0.2)
        assert config.overlap_tokens == 2000


class TestTranscriptChunk:
    """Tests for TranscriptChunk dataclass."""
    
    def test_initialization(self):
        """Test basic TranscriptChunk initialization."""
        chunk = TranscriptChunk(
            index=0,
            text="Hello world. This is a test.",
            start_time=0.0,
            end_time=5.0,
            segments=[{"start": 0.0, "end": 5.0, "text": "Hello world."}],
            overlap_with_previous="",
            overlap_with_next="This is a test.",
            estimated_tokens=10
        )
        assert chunk.index == 0
        assert chunk.text == "Hello world. This is a test."
        assert chunk.start_time == 0.0
        assert chunk.end_time == 5.0
        assert chunk.estimated_tokens == 10
    
    def test_get_continuity_context(self):
        """Test continuity context generation."""
        chunk = TranscriptChunk(
            index=1,
            text="Second chunk content here.",
            start_time=10.0,
            end_time=20.0,
            segments=[],
            overlap_with_previous="Previous context",
            overlap_with_next="Next context",
            estimated_tokens=5
        )
        context = chunk.get_continuity_context()
        assert "chunk 1" in context.casefold()
        assert "10.0s to 20.0s" in context


class TestChunkBoundary:
    """Tests for ChunkBoundary dataclass."""
    
    def test_initialization(self):
        """Test ChunkBoundary initialization."""
        boundary = ChunkBoundary(
            chunk_index=0,
            boundary_type="sentence",
            timestamp=15.5,
            narrative_context="Speaker finishes introduction"
        )
        assert boundary.chunk_index == 0
        assert boundary.boundary_type == "sentence"
        assert boundary.timestamp == 15.5
        assert boundary.narrative_context == "Speaker finishes introduction"


class TestChunkContext:
    """Tests for ChunkContext dataclass."""
    
    def test_initialization(self):
        """Test ChunkContext initialization."""
        context = ChunkContext(
            section_type="intro",
            tone="upbeat",
            required_categories=["intro_music", "title_vfx"],
            time_range=(0.0, 60.0),
            relevant_tags=["intro", "upbeat", "corporate"]
        )
        assert context.section_type == "intro"
        assert context.tone == "upbeat"
        assert context.required_categories == ["intro_music", "title_vfx"]
        assert context.time_range == (0.0, 60.0)
        assert context.relevant_tags == ["intro", "upbeat", "corporate"]


class TestChunkResult:
    """Tests for ChunkResult dataclass."""
    
    def test_initialization(self):
        """Test ChunkResult initialization."""
        result = ChunkResult(
            chunk_index=0,
            transcript_cuts=[{"start": 0.0, "end": 10.0}],
            music_matches=[{"id": "mus_001"}],
            sfx_matches=[],
            vfx_matches=[],
            continuity_markers=[],
            tokens_used=3500,
            processing_time_ms=2500,
            status="success",
            warnings=[]
        )
        assert result.chunk_index == 0
        assert result.status == "success"
        assert result.tokens_used == 3500


class TestAssembledRoughCut:
    """Tests for AssembledRoughCut dataclass."""
    
    def test_initialization(self):
        """Test AssembledRoughCut initialization."""
        assembled = AssembledRoughCut(
            transcript_segments=[{"chunk_index": 0, "section": "intro"}],
            music_matches=[{"chunk_index": 0}],
            sfx_matches=[],
            vfx_matches=[],
            assembly_metadata={"total_chunks": 3},
            continuity_validation={"valid": True}
        )
        assert len(assembled.transcript_segments) == 1
        assert assembled.assembly_metadata["total_chunks"] == 3


class TestChunkProgress:
    """Tests for ChunkProgress dataclass."""
    
    def test_initialization(self):
        """Test ChunkProgress initialization."""
        progress = ChunkProgress(
            current_chunk=2,
            total_chunks=5,
            chunk_phase="processing",
            message="Processing chunk 2 of 5...",
            eta_seconds=30,
            overall_progress_percent=40
        )
        assert progress.current_chunk == 2
        assert progress.total_chunks == 5
        assert progress.chunk_phase == "processing"
        assert progress.overall_progress_percent == 40


class TestEstimateTokenCount:
    """Tests for token estimation function."""
    
    def test_empty_string(self):
        """Test token estimation for empty string."""
        assert estimate_token_count("") == 0
    
    def test_simple_text(self):
        """Test token estimation for simple text."""
        # Roughly 4 characters per token
        text = "Hello world"
        expected = len(text) // 4 + (1 if len(text) % 4 > 0 else 0)
        assert estimate_token_count(text) == expected
    
    def test_longer_text(self):
        """Test token estimation for longer text."""
        text = "This is a longer piece of text for testing."
        tokens = estimate_token_count(text)
        assert tokens > 0
        # Should be approximately length / 4
        assert abs(tokens - len(text) / 4) < 2


class TestContextChunker:
    """Tests for ContextChunker class."""
    
    def test_initialization(self):
        """Test ContextChunker initialization."""
        chunker = ContextChunker()
        assert chunker.config is not None
        assert chunker.config.max_tokens_per_chunk == 4000
    
    def test_initialization_with_custom_config(self):
        """Test ContextChunker with custom config."""
        config = ChunkConfig(max_tokens_per_chunk=8000)
        chunker = ContextChunker(config)
        assert chunker.config.max_tokens_per_chunk == 8000
    
    def test_calculate_optimal_chunk_size_openai(self):
        """Test chunk size calculation for OpenAI provider."""
        chunker = ContextChunker(ChunkConfig(provider_name="openai"))
        
        # For small transcript within limits
        size, needs_chunking = chunker.calculate_optimal_chunk_size("Short text")
        assert needs_chunking is False
        
        # For large transcript exceeding limits
        large_text = "word " * 50000  # ~250k characters, ~62k tokens
        size, needs_chunking = chunker.calculate_optimal_chunk_size(large_text)
        assert needs_chunking is True
        assert size > 0
    
    def test_calculate_optimal_chunk_size_claude(self):
        """Test chunk size calculation for Claude provider."""
        chunker = ContextChunker(ChunkConfig(provider_name="claude"))
        size, needs_chunking = chunker.calculate_optimal_chunk_size("Short text")
        # Claude has higher limits, so short text should not need chunking
        assert needs_chunking is False
    
    def test_calculate_optimal_chunk_size_unknown_provider(self):
        """Test chunk size calculation for unknown provider."""
        chunker = ContextChunker(ChunkConfig(provider_name="unknown"))
        size, needs_chunking = chunker.calculate_optimal_chunk_size("Some text")
        # Should use default fallback
        assert size > 0
    
    def test_chunk_transcript_single_chunk(self):
        """Test chunking short transcript (single chunk)."""
        chunker = ContextChunker()
        segments = [
            {"start": 0.0, "end": 5.0, "text": "Hello world.", "speaker": "A"},
            {"start": 5.0, "end": 10.0, "text": "How are you?", "speaker": "B"},
        ]
        
        chunks = chunker.chunk_transcript(segments)
        assert len(chunks) == 1
        assert chunks[0].index == 0
        assert chunks[0].start_time == 0.0
        assert chunks[0].end_time == 10.0
    
    def test_chunk_transcript_multiple_chunks(self):
        """Test chunking long transcript (multiple chunks)."""
        # Create many segments to force chunking
        segments = []
        for i in range(100):
            segments.append({
                "start": float(i * 10),
                "end": float((i + 1) * 10),
                "text": f"This is segment {i} with some content. " * 50,  # Make it long
                "speaker": "A" if i % 2 == 0 else "B"
            })
        
        chunker = ContextChunker(ChunkConfig(max_tokens_per_chunk=2000))
        chunks = chunker.chunk_transcript(segments)
        
        assert len(chunks) > 1
        # Check that chunks have proper overlap
        for i in range(len(chunks) - 1):
            assert chunks[i].overlap_with_next != ""
            assert chunks[i + 1].overlap_with_previous != ""
    
    def test_chunk_transcript_with_speaker_changes(self):
        """Test that speaker changes are respected as boundaries."""
        segments = [
            {"start": 0.0, "end": 5.0, "text": "First speaker talking here.", "speaker": "A"},
            {"start": 5.0, "end": 10.0, "text": "Second speaker responds now.", "speaker": "B"},
            {"start": 10.0, "end": 15.0, "text": "Third speaker joins in here.", "speaker": "C"},
        ]
        
        chunker = ContextChunker()
        chunks = chunker.chunk_transcript(segments)
        
        # With short transcript, should be single chunk
        assert len(chunks) == 1
    
    def test_chunk_transcript_empty(self):
        """Test chunking empty transcript."""
        chunker = ContextChunker()
        chunks = chunker.chunk_transcript([])
        assert len(chunks) == 0
    
    def test_find_boundary_at_sentence_end(self):
        """Test finding boundary at sentence end."""
        chunker = ContextChunker()
        text = "First sentence. Second sentence. Third sentence."
        segments = [{"start": 0.0, "end": 10.0, "text": text}]
        
        # Should find a sentence boundary
        boundary = chunker._find_boundary(text, 25, segments)
        assert boundary is not None
    
    def test_get_provider_token_limit(self):
        """Test getting provider token limits."""
        chunker = ContextChunker()
        
        # Known providers
        assert chunker._get_provider_token_limit("openai") > 0
        assert chunker._get_provider_token_limit("claude") > 0
        
        # Unknown provider should return default
        default_limit = chunker._get_provider_token_limit("unknown")
        assert default_limit == 4000


class TestProviderTokenLimits:
    """Tests for PROVIDER_TOKEN_LIMITS constant."""
    
    def test_openai_limits_exist(self):
        """Test that OpenAI token limits are defined."""
        assert "openai" in PROVIDER_TOKEN_LIMITS
        assert "gpt-4" in PROVIDER_TOKEN_LIMITS["openai"]
        assert "gpt-4-turbo" in PROVIDER_TOKEN_LIMITS["openai"]
        assert "gpt-4o" in PROVIDER_TOKEN_LIMITS["openai"]
        assert "gpt-3.5-turbo" in PROVIDER_TOKEN_LIMITS["openai"]
    
    def test_claude_limits_exist(self):
        """Test that Claude token limits are defined."""
        assert "claude" in PROVIDER_TOKEN_LIMITS
        assert "claude-3-opus" in PROVIDER_TOKEN_LIMITS["claude"]
        assert "claude-3-sonnet" in PROVIDER_TOKEN_LIMITS["claude"]
        assert "claude-3-haiku" in PROVIDER_TOKEN_LIMITS["claude"]
    
    def test_openrouter_limits_exist(self):
        """Test that OpenRouter token limits are defined."""
        assert "openrouter" in PROVIDER_TOKEN_LIMITS
        # Anthropic models via OpenRouter
        assert "anthropic/claude-3.5-sonnet" in PROVIDER_TOKEN_LIMITS["openrouter"]
        assert "anthropic/claude-3-opus" in PROVIDER_TOKEN_LIMITS["openrouter"]
        # OpenAI models via OpenRouter
        assert "openai/gpt-4o" in PROVIDER_TOKEN_LIMITS["openrouter"]
        assert "openai/gpt-4" in PROVIDER_TOKEN_LIMITS["openrouter"]
        # Meta models via OpenRouter
        assert "meta-llama/llama-3.1-70b-instruct" in PROVIDER_TOKEN_LIMITS["openrouter"]
        # Google models via OpenRouter
        assert "google/gemini-pro" in PROVIDER_TOKEN_LIMITS["openrouter"]
    
    def test_openrouter_limits_are_reasonable(self):
        """Test that OpenRouter model limits are reasonable values."""
        openrouter_limits = PROVIDER_TOKEN_LIMITS["openrouter"]
        
        # Claude models should have 200k limit
        assert openrouter_limits["anthropic/claude-3.5-sonnet"] == 200000
        
        # GPT-4o should have 128k limit
        assert openrouter_limits["openai/gpt-4o"] == 128000
        
        # Gemini Pro 1.5 should have 1M limit
        assert openrouter_limits["google/gemini-pro-1.5"] == 1000000
    
    def test_default_limit_exists(self):
        """Test that default token limit is defined."""
        assert "default" in PROVIDER_TOKEN_LIMITS


class TestBoundaryPriority:
    """Tests for BOUNDARY_PRIORITY constant."""
    
    def test_boundary_priority_order(self):
        """Test that boundary priority is in correct order."""
        assert BOUNDARY_PRIORITY[0] == "speaker_change"
        assert BOUNDARY_PRIORITY[-1] == "forced"
        assert "sentence_end" in BOUNDARY_PRIORITY


class TestTokenSafetyMargin:
    """Tests for TOKEN_SAFETY_MARGIN constant."""
    
    def test_safety_margin_value(self):
        """Test that safety margin is reasonable (around 0.7)."""
        assert 0.5 < TOKEN_SAFETY_MARGIN < 0.9
