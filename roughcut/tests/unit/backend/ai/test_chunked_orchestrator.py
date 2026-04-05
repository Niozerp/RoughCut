"""Unit tests for chunked orchestrator module.

Tests cover ChunkedOrchestrator, ChunkProgressTracker, and related
functionality for processing transcripts in chunks.
"""

from __future__ import annotations

import pytest

from roughcut.backend.ai.chunked_orchestrator import (
    ChunkedOrchestrator,
    ChunkProgressTracker,
    MAX_CONTINUITY_GAP,
    MIN_PACING_CONSISTENCY,
    CHUNK_TIMEOUT_SECONDS,
)
from roughcut.backend.ai.chunk import (
    ChunkConfig,
    ChunkContext,
    ChunkResult,
    ChunkBoundary,
    TranscriptChunk,
)


class TestChunkedOrchestratorInitialization:
    """Tests for ChunkedOrchestrator initialization."""
    
    def test_default_initialization(self):
        """Test ChunkedOrchestrator with default config."""
        orchestrator = ChunkedOrchestrator()
        assert orchestrator.config is not None
        assert orchestrator.config.max_tokens_per_chunk == 4000
        assert orchestrator.chunker is not None
        assert orchestrator.chunk_results == []
    
    def test_custom_config_initialization(self):
        """Test ChunkedOrchestrator with custom config."""
        config = ChunkConfig(max_tokens_per_chunk=8000)
        orchestrator = ChunkedOrchestrator(config)
        assert orchestrator.config.max_tokens_per_chunk == 8000


class TestChunkedOrchestratorDetermineSection:
    """Tests for section determination."""
    
    def test_determine_section_for_chunk(self):
        """Test determining section for a chunk."""
        orchestrator = ChunkedOrchestrator()
        
        chunk = TranscriptChunk(
            index=0,
            text="Test",
            start_time=10.0,
            end_time=20.0,
            segments=[],
            overlap_with_previous="",
            overlap_with_next="",
            estimated_tokens=10
        )
        
        format_template = {
            "sections": [
                {"name": "intro", "duration": 30},
                {"name": "narrative", "duration": 120},
            ]
        }
        
        section = orchestrator._determine_section_for_chunk(chunk, format_template)
        # 15s midpoint falls within intro (0-30s)
        assert section == "intro"


class TestChunkedOrchestratorBuildContext:
    """Tests for chunk context building."""
    
    def test_build_chunk_context(self):
        """Test building context for a chunk."""
        orchestrator = ChunkedOrchestrator()
        
        chunk = TranscriptChunk(
            index=0,
            text="Test",
            start_time=0.0,
            end_time=60.0,
            segments=[],
            overlap_with_previous="",
            overlap_with_next="",
            estimated_tokens=20
        )
        
        format_template = {
            "sections": [
                {
                    "name": "intro",
                    "duration": 60,
                    "asset_categories": ["intro_music"]
                }
            ]
        }
        
        context = orchestrator._build_chunk_context(chunk, "intro", format_template)
        
        assert context.section_type == "intro"
        assert "intro_music" in context.required_categories
        assert context.time_range == (0.0, 60.0)


class TestChunkedOrchestratorContinuityContext:
    """Tests for continuity context."""
    
    def test_get_continuity_context_first_chunk(self):
        """Test getting context for first chunk."""
        orchestrator = ChunkedOrchestrator()
        context = orchestrator._get_continuity_context(0)
        
        assert context["has_previous"] is False
    
    def test_get_continuity_context_subsequent_chunk(self):
        """Test getting context for chunk after first."""
        orchestrator = ChunkedOrchestrator()
        
        # Add a mock previous result
        orchestrator.chunk_results = [
            ChunkResult(
                chunk_index=0,
                transcript_cuts=[{"speaker": "Alice"}],
                music_matches=[],
                sfx_matches=[],
                vfx_matches=[],
                continuity_markers=[
                    ChunkBoundary(0, "sentence", 30.0, "Alice finishes")
                ],
                tokens_used=100,
                processing_time_ms=1000,
                status="success",
                warnings=[]
            )
        ]
        
        context = orchestrator._get_continuity_context(1)
        
        assert context["has_previous"] is True
        assert context["previous_chunk_index"] == 0


class TestChunkedOrchestratorValidateContinuity:
    """Tests for continuity validation."""
    
    def test_validate_continuity_single_chunk(self):
        """Test validation with single chunk."""
        orchestrator = ChunkedOrchestrator()
        
        results = [
            ChunkResult(
                chunk_index=0,
                transcript_cuts=[{"start": 0.0, "end": 10.0}],
                music_matches=[],
                sfx_matches=[],
                vfx_matches=[],
                continuity_markers=[],
                tokens_used=100,
                processing_time_ms=1000,
                status="success",
                warnings=[]
            )
        ]
        
        validation = orchestrator._validate_continuity(results)
        
        assert validation["valid"] is True
        assert validation["gaps"] == []
    
    def test_validate_continuity_gap_detection(self):
        """Test detection of gaps between chunks."""
        orchestrator = ChunkedOrchestrator()
        
        results = [
            ChunkResult(
                chunk_index=0,
                transcript_cuts=[{"start": 0.0, "end": 10.0}],
                music_matches=[],
                sfx_matches=[],
                vfx_matches=[],
                continuity_markers=[],
                tokens_used=100,
                processing_time_ms=1000,
                status="success",
                warnings=[]
            ),
            ChunkResult(
                chunk_index=1,
                transcript_cuts=[{"start": 20.0, "end": 30.0}],  # 10s gap
                music_matches=[],
                sfx_matches=[],
                vfx_matches=[],
                continuity_markers=[],
                tokens_used=100,
                processing_time_ms=1000,
                status="success",
                warnings=[]
            ),
        ]
        
        validation = orchestrator._validate_continuity(results)
        
        # Gap of 10s exceeds MAX_CONTINUITY_GAP (5s)
        assert validation["valid"] is False
        assert len(validation["gaps"]) > 0


class TestChunkedOrchestratorAssembly:
    """Tests for result assembly."""
    
    def test_assemble_empty_results(self):
        """Test assembly with empty results."""
        orchestrator = ChunkedOrchestrator()
        
        assembled = orchestrator.assemble_chunk_results([])
        
        assert assembled.continuity_validation["valid"] is False
        assert assembled.assembly_metadata.get("error") is not None
    
    def test_assemble_single_result(self):
        """Test assembly with single chunk result."""
        orchestrator = ChunkedOrchestrator()
        
        results = [
            ChunkResult(
                chunk_index=0,
                transcript_cuts=[
                    {"start": 0.0, "end": 5.0, "text": "Hello"},
                    {"start": 5.0, "end": 10.0, "text": "World"},
                ],
                music_matches=[{"id": "mus_001"}],
                sfx_matches=[],
                vfx_matches=[],
                continuity_markers=[],
                tokens_used=100,
                processing_time_ms=1000,
                status="success",
                warnings=[]
            )
        ]
        
        assembled = orchestrator.assemble_chunk_results(results)
        
        assert len(assembled.transcript_segments) == 2
        assert assembled.assembly_metadata["total_chunks"] == 1


class TestChunkProgressTracker:
    """Tests for ChunkProgressTracker."""
    
    def test_initialization(self):
        """Test tracker initialization."""
        tracker = ChunkProgressTracker(total_chunks=5)
        assert tracker.total_chunks == 5
        assert tracker.current_chunk == 0
        assert tracker.phase == "initializing"
    
    def test_start_and_end_chunk(self):
        """Test chunk start and end tracking."""
        tracker = ChunkProgressTracker(total_chunks=5)
        
        tracker.start_chunk(1)
        assert tracker.current_chunk == 1
        assert tracker.phase == "processing"
        
        tracker.end_chunk(1, 2.5)
        assert len(tracker.chunk_times) == 1
        assert tracker.chunk_times[0] == 2.5
    
    def test_get_progress(self):
        """Test progress calculation."""
        tracker = ChunkProgressTracker(total_chunks=5)
        
        tracker.start_chunk(2)
        tracker.chunk_times = [1.0, 1.5]  # Previous chunks took 1.0s and 1.5s
        
        progress = tracker.get_progress()
        
        assert progress.current_chunk == 2
        assert progress.total_chunks == 5
        assert progress.chunk_phase == "processing"
        # ETA should be calculated from average of previous chunks
        assert progress.eta_seconds > 0


class TestChunkedOrchestratorProcessChunks:
    """Tests for chunk processing."""
    
    def test_process_single_chunk(self):
        """Test processing transcript that fits in single chunk."""
        orchestrator = ChunkedOrchestrator()
        
        segments = [
            {"start": 0.0, "end": 5.0, "text": "Hello world."},
            {"start": 5.0, "end": 10.0, "text": "How are you?"},
        ]
        
        format_template = {"sections": [{"name": "intro", "duration": 60}]}
        asset_index = {"music": [], "sfx": [], "vfx": []}
        
        results = orchestrator.process_chunks_sequentially(
            segments, format_template, asset_index
        )
        
        # Short transcript should be single chunk
        assert len(results) == 1
        assert results[0].chunk_index == 0
    
    def test_process_multiple_chunks(self):
        """Test processing long transcript that requires multiple chunks."""
        # Create many segments to force chunking
        segments = []
        for i in range(100):
            segments.append({
                "start": float(i * 10),
                "end": float((i + 1) * 10),
                "text": f"This is segment {i} with a lot of content. " * 20,
            })
        
        config = ChunkConfig(max_tokens_per_chunk=2000)
        orchestrator = ChunkedOrchestrator(config)
        
        format_template = {"sections": [{"name": "narrative", "duration": 1000}]}
        asset_index = {"music": [], "sfx": [], "vfx": []}
        
        results = orchestrator.process_chunks_sequentially(
            segments, format_template, asset_index
        )
        
        # Long transcript should be multiple chunks
        assert len(results) > 1


class TestConstants:
    """Tests for module constants."""
    
    def test_max_continuity_gap_value(self):
        """Test that max continuity gap is reasonable."""
        assert MAX_CONTINUITY_GAP > 0
        assert MAX_CONTINUITY_GAP < 60  # Should be less than 1 minute
    
    def test_min_pacing_consistency_value(self):
        """Test that min pacing consistency threshold is reasonable."""
        assert 0.0 < MIN_PACING_CONSISTENCY <= 1.0
    
    def test_chunk_timeout_value(self):
        """Test that chunk timeout matches NFR3."""
        assert CHUNK_TIMEOUT_SECONDS == 30
