"""Chunked processing orchestrator for long-form content.

Provides the ChunkedOrchestrator class for managing sequential chunk
processing, continuity preservation, and result assembly.
"""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, Generator, Optional

from .chunk import (
    AssembledRoughCut,
    ChunkConfig,
    ChunkContext,
    ChunkProgress,
    ChunkResult,
    TranscriptChunk,
)
from .chunker import ContextChunker, estimate_token_count


logger = logging.getLogger(__name__)

#: Maximum allowed gap between chunks in seconds
MAX_CONTINUITY_GAP = 5.0

#: Minimum pacing consistency score (0.0-1.0)
MIN_PACING_CONSISTENCY = 0.6

#: Timeout per chunk in seconds (per NFR3)
CHUNK_TIMEOUT_SECONDS = 30

#: Default retry attempts for failed chunks
DEFAULT_RETRY_ATTEMPTS = 3

#: Base delay for exponential backoff (seconds)
RETRY_BASE_DELAY = 1.0


def with_retry(max_attempts: int = DEFAULT_RETRY_ATTEMPTS, base_delay: float = RETRY_BASE_DELAY):
    """Decorator for retrying chunk processing with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))  # Exponential backoff
                        logger.warning(
                            f"{func.__name__} failed on attempt {attempt}/{max_attempts}. "
                            f"Retrying in {delay:.1f}s... Error: {e}"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts. "
                            f"Final error: {e}"
                        )
            raise last_exception
        return wrapper
    return decorator


class ChunkedOrchestrator:
    """Orchestrates chunked processing of long transcripts.
    
    Manages sequential processing of transcript chunks, passing continuity
    context between chunks and assembling final results.
    
    Attributes:
        config: ChunkConfig for chunking parameters
        chunker: ContextChunker instance
        chunk_results: List of ChunkResult objects
    """
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        """Initialize orchestrator.
        
        Args:
            config: ChunkConfig instance. If None, uses default.
        """
        self.config = config or ChunkConfig()
        self.chunker = ContextChunker(self.config)
        self.chunk_results: list[ChunkResult] = []
    
    def process_chunks_sequentially(
        self,
        transcript_segments: list[dict],
        format_template: dict,
        asset_index: dict[str, list[dict]],
        process_callback: Optional[Callable[..., Any]] = None
    ) -> list[ChunkResult]:
        """Process transcript chunks sequentially with continuity.
        
        Args:
            transcript_segments: List of transcript segments
            format_template: Format template dictionary
            asset_index: Asset index dictionary
            process_callback: Optional callback for processing each chunk
            
        Returns:
            List of ChunkResult objects
        """
        # First, chunk the transcript
        chunks = self.chunker.chunk_transcript(transcript_segments)
        
        if not chunks:
            return []
        
        # Process each chunk
        self.chunk_results = []
        
        for i, chunk in enumerate(chunks):
            # Get format section for this chunk
            section_name = self._determine_section_for_chunk(
                chunk,
                format_template
            )
            
            # Build chunk context
            chunk_context = self._build_chunk_context(
                chunk,
                section_name,
                format_template
            )
            
            # Get continuity context from previous chunk
            continuity_context = self._get_continuity_context(i)
            
            # Process chunk
            if process_callback:
                result = process_callback(
                    chunk,
                    chunk_context,
                    continuity_context,
                    asset_index
                )
            else:
                # Default processing
                result = self._default_chunk_process(
                    chunk,
                    chunk_context,
                    continuity_context,
                    asset_index
                )
            
            self.chunk_results.append(result)
        
        return self.chunk_results
    
    def process_chunks_with_progress(
        self,
        transcript_segments: list[dict],
        format_template: dict,
        asset_index: dict[str, list[dict]],
        process_callback: Optional[Callable[..., Any]] = None
    ) -> Generator[ChunkProgress | list[ChunkResult], None, None]:
        """Process chunks with progress reporting.
        
        Yields progress updates and final results.
        
        Args:
            transcript_segments: List of transcript segments
            format_template: Format template dictionary
            asset_index: Asset index dictionary
            process_callback: Optional callback for processing each chunk
            
        Yields:
            ChunkProgress updates during processing
            Final list[ChunkResult] when complete
        """
        # Initialize
        chunks = self.chunker.chunk_transcript(transcript_segments)
        total_chunks = len(chunks)
        
        if not chunks:
            yield []
            return
        
        # Yield initialization progress
        yield ChunkProgress(
            current_chunk=0,
            total_chunks=total_chunks,
            chunk_phase="initializing",
            message=f"Initializing chunked processing: {total_chunks} chunks",
            eta_seconds=total_chunks * CHUNK_TIMEOUT_SECONDS,
            overall_progress_percent=0
        )
        
        # Process each chunk
        self.chunk_results = []
        start_time = time.time()
        
        for i, chunk in enumerate(chunks):
            chunk_start = time.time()
            
            # Yield processing start
            yield ChunkProgress(
                current_chunk=i + 1,
                total_chunks=total_chunks,
                chunk_phase="processing",
                message=f"Processing chunk {i + 1} of {total_chunks}: "
                        f"{chunk.start_time:.1f}s to {chunk.end_time:.1f}s",
                eta_seconds=int((total_chunks - i) * CHUNK_TIMEOUT_SECONDS),
                overall_progress_percent=int((i / total_chunks) * 80)
            )
            
            # Get format section and context
            section_name = self._determine_section_for_chunk(chunk, format_template)
            chunk_context = self._build_chunk_context(chunk, section_name, format_template)
            continuity_context = self._get_continuity_context(i)
            
            # Process chunk
            if process_callback:
                result = process_callback(
                    chunk,
                    chunk_context,
                    continuity_context,
                    asset_index
                )
            else:
                result = self._default_chunk_process(
                    chunk,
                    chunk_context,
                    continuity_context,
                    asset_index
                )
            
            self.chunk_results.append(result)
        
        # Yield assembly progress
        yield ChunkProgress(
            current_chunk=total_chunks,
            total_chunks=total_chunks,
            chunk_phase="assembling",
            message="Assembling chunk results...",
            eta_seconds=5,
            overall_progress_percent=90
        )
        
        # Final yield with results
        yield ChunkProgress(
            current_chunk=total_chunks,
            total_chunks=total_chunks,
            chunk_phase="complete",
            message=f"Processing complete: {total_chunks} chunks processed",
            eta_seconds=0,
            overall_progress_percent=100
        )
        
        yield self.chunk_results
    
    def assemble_chunk_results(
        self,
        chunk_results: Optional[list[ChunkResult]] = None
    ) -> AssembledRoughCut:
        """Assemble all chunk results into final rough cut.
        
        Args:
            chunk_results: List of ChunkResult objects. If None, uses stored results.
            
        Returns:
            AssembledRoughCut instance
        """
        results = chunk_results or self.chunk_results
        
        if not results:
            return AssembledRoughCut(
                transcript_segments=[],
                music_matches=[],
                sfx_matches=[],
                vfx_matches=[],
                assembly_metadata={"error": "No chunk results to assemble"},
                continuity_validation={"valid": False, "reason": "no_results"}
            )
        
        # Collect all matches from chunks
        transcript_segments = []
        music_matches = []
        sfx_matches = []
        vfx_matches = []
        
        for result in results:
            # Add chunk index to each match for tracking
            for cut in result.transcript_cuts:
                cut["chunk_index"] = result.chunk_index
                transcript_segments.append(cut)
            
            for match in result.music_matches:
                match["chunk_index"] = result.chunk_index
                music_matches.append(match)
            
            for match in result.sfx_matches:
                match["chunk_index"] = result.chunk_index
                sfx_matches.append(match)
            
            for match in result.vfx_matches:
                match["chunk_index"] = result.chunk_index
                vfx_matches.append(match)
        
        # Build assembly metadata
        total_tokens = sum(r.tokens_used for r in results)
        total_time = sum(r.processing_time_ms for r in results)
        failed_chunks = sum(1 for r in results if r.status == "failed")
        
        assembly_metadata = {
            "total_chunks": len(results),
            "chunks_processed": len(results) - failed_chunks,
            "chunks_failed": failed_chunks,
            "total_tokens_used": total_tokens,
            "total_processing_time_ms": total_time,
        }
        
        # Perform continuity validation
        continuity_validation = self._validate_continuity(results)
        assembly_metadata["continuity_valid"] = continuity_validation["valid"]
        assembly_metadata["pacing_consistency_score"] = continuity_validation.get(
            "pacing_score", 0.0
        )
        
        return AssembledRoughCut(
            transcript_segments=transcript_segments,
            music_matches=music_matches,
            sfx_matches=sfx_matches,
            vfx_matches=vfx_matches,
            assembly_metadata=assembly_metadata,
            continuity_validation=continuity_validation
        )
    
    def _determine_section_for_chunk(
        self,
        chunk: TranscriptChunk,
        format_template: dict
    ) -> str:
        """Determine which format section a chunk belongs to.
        
        Args:
            chunk: TranscriptChunk instance
            format_template: Format template dictionary
            
        Returns:
            Section name
        """
        sections = format_template.get("sections", [])
        
        # Find section containing this chunk's time range
        chunk_midpoint = (chunk.start_time + chunk.end_time) / 2
        
        current_time = 0.0
        for section in sections:
            section_duration = section.get("duration", 0)
            section_end = current_time + section_duration
            
            if current_time <= chunk_midpoint < section_end:
                return section.get("name", "narrative")
            
            current_time = section_end
        
        # Default to last section or "narrative"
        if sections:
            return sections[-1].get("name", "narrative")
        return "narrative"
    
    def _build_chunk_context(
        self,
        chunk: TranscriptChunk,
        section_name: str,
        format_template: dict
    ) -> ChunkContext:
        """Build context for a chunk.
        
        Args:
            chunk: TranscriptChunk instance
            section_name: Name of section
            format_template: Format template dictionary
            
        Returns:
            ChunkContext instance
        """
        # Get section data
        sections = format_template.get("sections", [])
        section_data = next(
            (s for s in sections if s.get("name") == section_name),
            {}
        )
        
        required_categories = section_data.get("asset_categories", [])
        
        # Infer tone from section
        tone_map = {
            "intro": "upbeat",
            "hook": "upbeat",
            "outro": "triumphant",
            "act_1": "contemplative",
            "act_2": "tense",
            "act_3": "epic",
        }
        tone = tone_map.get(section_name, "corporate")
        
        # Build relevant tags
        tags = [section_name, tone]
        tags.extend(required_categories)
        
        return ChunkContext(
            section_type=section_name,
            tone=tone,
            required_categories=required_categories,
            time_range=(chunk.start_time, chunk.end_time),
            relevant_tags=list(set(tags))
        )
    
    def _get_continuity_context(self, chunk_index: int) -> dict[str, Any]:
        """Get continuity context from previous chunk.
        
        Args:
            chunk_index: Current chunk index
            
        Returns:
            Continuity context dictionary
        """
        if chunk_index == 0 or not self.chunk_results:
            return {"has_previous": False}
        
        prev_result = self.chunk_results[chunk_index - 1]
        
        return {
            "has_previous": True,
            "previous_chunk_index": chunk_index - 1,
            "previous_ending_context": (
                prev_result.continuity_markers[-1].narrative_context
                if prev_result.continuity_markers else ""
            ),
            "previous_last_speaker": (
                prev_result.transcript_cuts[-1].get("speaker", "")
                if prev_result.transcript_cuts else ""
            ),
        }
    
    def _validate_continuity(
        self,
        chunk_results: list[ChunkResult]
    ) -> dict[str, Any]:
        """Validate continuity across chunk results.
        
        Args:
            chunk_results: List of ChunkResult objects
            
        Returns:
            Validation results dictionary
        """
        validation = {
            "valid": True,
            "gaps": [],
            "pacing_score": 1.0,
            "warnings": []
        }
        
        if len(chunk_results) <= 1:
            return validation
        
        # Check for gaps between chunks
        for i in range(len(chunk_results) - 1):
            current = chunk_results[i]
            next_chunk = chunk_results[i + 1]
            
            # Get end of current chunk
            if current.transcript_cuts:
                current_end = max(
                    cut.get("end", 0) for cut in current.transcript_cuts
                )
            else:
                current_end = 0
            
            # Get start of next chunk
            if next_chunk.transcript_cuts:
                next_start = min(
                    cut.get("start", float('inf')) for cut in next_chunk.transcript_cuts
                )
            else:
                next_start = 999999.0  # Use large number instead of inf for JSON safety
            
            # Check for gap
            gap = next_start - current_end
            if gap > MAX_CONTINUITY_GAP:
                validation["valid"] = False
                validation["gaps"].append({
                    "between_chunks": [i, i + 1],
                    "gap_seconds": gap
                })
                validation["warnings"].append(
                    f"Gap detected between chunks {i} and {i + 1}: {gap:.1f}s"
                )
        
        # Calculate pacing consistency score
        if len(chunk_results) >= 2:
            pacing_scores = []
            for result in chunk_results:
                if result.transcript_cuts:
                    # Calculate average segment duration
                    durations = [
                        cut.get("end", 0) - cut.get("start", 0)
                        for cut in result.transcript_cuts
                    ]
                    avg_duration = sum(durations) / len(durations)
                    pacing_scores.append(avg_duration)
            
            if len(pacing_scores) >= 2:
                # Calculate variance (lower is more consistent)
                mean_pacing = sum(pacing_scores) / len(pacing_scores)
                variance = sum(
                    (p - mean_pacing) ** 2 for p in pacing_scores
                ) / len(pacing_scores)
                
                # Convert to score (1.0 = perfect consistency)
                validation["pacing_score"] = max(
                    0.0,
                    1.0 - (variance / (mean_pacing ** 2)) if mean_pacing > 0 else 0.0
                )
        
        # Check minimum pacing consistency
        if validation["pacing_score"] < MIN_PACING_CONSISTENCY:
            validation["warnings"].append(
                f"Pacing consistency score {validation['pacing_score']:.2f} "
                f"below threshold {MIN_PACING_CONSISTENCY}"
            )
        
        return validation
    
    def _default_chunk_process(
        self,
        chunk: TranscriptChunk,
        chunk_context: ChunkContext,
        continuity_context: dict[str, Any],
        asset_index: dict[str, list[dict]]
    ) -> ChunkResult:
        """Default processing for a chunk (placeholder for actual AI processing).
        
        Args:
            chunk: TranscriptChunk instance
            chunk_context: ChunkContext instance
            continuity_context: Continuity context from previous chunk
            asset_index: Asset index dictionary
            
        Returns:
            ChunkResult instance
        """
        # This is a placeholder that would be replaced with actual AI processing
        start_time = time.time()
        
        # Simulate processing
        tokens_used = estimate_token_count(chunk.text)
        processing_time = int((time.time() - start_time) * 1000)
        
        return ChunkResult(
            chunk_index=chunk.index,
            transcript_cuts=[],
            music_matches=[],
            sfx_matches=[],
            vfx_matches=[],
            continuity_markers=[],
            tokens_used=tokens_used,
            processing_time_ms=processing_time,
            status="success",
            warnings=[]
        )


class ChunkProgressTracker:
    """Tracks progress for chunked processing operations.
    
    Provides detailed progress tracking for multi-chunk operations
    with ETA calculation and phase reporting.
    """
    
    def __init__(self, total_chunks: int):
        """Initialize tracker.
        
        Args:
            total_chunks: Total number of chunks to process
        """
        self.total_chunks = total_chunks
        self.current_chunk = 0
        self.chunk_times: list[float] = []
        self.phase = "initializing"
    
    def start_chunk(self, chunk_index: int):
        """Mark start of chunk processing.
        
        Args:
            chunk_index: Index of chunk starting
        """
        self.current_chunk = chunk_index
        self.phase = "processing"
    
    def end_chunk(self, chunk_index: int, duration_seconds: float):
        """Mark end of chunk processing.
        
        Args:
            chunk_index: Index of chunk completed
            duration_seconds: Processing duration
        """
        self.chunk_times.append(duration_seconds)
    
    def get_progress(self) -> ChunkProgress:
        """Get current progress.
        
        Returns:
            ChunkProgress instance
        """
        # Calculate ETA based on average chunk time
        if self.chunk_times:
            avg_time = sum(self.chunk_times) / len(self.chunk_times)
            remaining_chunks = self.total_chunks - self.current_chunk
            eta = int(avg_time * remaining_chunks)
        else:
            eta = self.total_chunks * CHUNK_TIMEOUT_SECONDS
        
        # Calculate overall percentage
        if self.phase == "complete":
            percent = 100
        elif self.phase == "assembling":
            percent = 90 + int((self.current_chunk / self.total_chunks) * 10)
        else:
            percent = int((self.current_chunk / self.total_chunks) * 80)
        
        return ChunkProgress(
            current_chunk=self.current_chunk,
            total_chunks=self.total_chunks,
            chunk_phase=self.phase,
            message=f"Processing chunk {self.current_chunk} of {self.total_chunks}",
            eta_seconds=eta,
            overall_progress_percent=percent
        )
    
    def set_phase(self, phase: str):
        """Set current phase.
        
        Args:
            phase: Phase name (initializing, processing, assembling, complete)
        """
        self.phase = phase
