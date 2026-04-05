"""AI orchestrator for rough cut generation.

Coordinates AI processing for rough cut generation, including:
- Context chunking for long transcripts
- AI service communication
- Progress reporting
- Error handling and recovery
"""

import logging
from typing import Any, Callable, Dict, Generator, List, Optional

from .openai_client import OpenAIClient

logger = logging.getLogger(__name__)

# Type alias for progress callback
ProgressCallback = Callable[[str, int, int], None]


class RoughCutOrchestrator:
    """Orchestrates AI-powered rough cut generation.
    
    Manages the end-to-end AI processing for rough cut generation,
    including context chunking, progress reporting, and error handling.
    
    Example:
        client = OpenAIClient(api_key="...")
        orchestrator = RoughCutOrchestrator(client)
        
        result = orchestrator.generate_rough_cut(
            transcript_data,
            format_template,
            media_index,
            progress_callback=on_progress
        )
    """
    
    DEFAULT_CHUNK_SIZE = 4000  # Tokens per chunk (conservative for GPT-3.5)
    DEFAULT_CHUNK_OVERLAP = 200  # Tokens of overlap between chunks
    
    def __init__(
        self,
        client: OpenAIClient,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ):
        """Initialize the orchestrator.
        
        Args:
            client: OpenAIClient instance for AI API calls
            chunk_size: Maximum tokens per transcript chunk
            chunk_overlap: Overlap tokens between chunks for continuity
        """
        self.client = client
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def initiate_generation(
        self,
        rough_cut_data: Dict[str, Any],
        progress_callback: Optional[ProgressCallback] = None
    ) -> Dict[str, Any]:
        """Initiate rough cut generation.
        
        This is the entry point for Story 5.1 - validates data,
        chunks if necessary, and prepares for AI processing.
        
        Args:
            rough_cut_data: Complete data bundle from RoughCutDataPreparer
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with generation status and rough_cut_id
        """
        # Report progress
        if progress_callback:
            progress_callback("initiate_rough_cut", 1, 5)
        
        # Validate data structure
        self._validate_rough_cut_data(rough_cut_data)
        
        if progress_callback:
            progress_callback("initiate_rough_cut", 2, 5)
        
        # Extract components
        transcription = rough_cut_data.get("transcription", {})
        format_template = rough_cut_data.get("format", {})
        media = rough_cut_data.get("media", {})
        
        # Calculate chunks needed
        transcript_text = transcription.get("text", "")
        num_chunks = self._calculate_chunks_needed(transcript_text)
        
        logger.info(
            f"Initiating rough cut generation: "
            f"transcript_length={len(transcript_text)}, "
            f"estimated_chunks={num_chunks}"
        )
        
        if progress_callback:
            progress_callback("initiate_rough_cut", 3, 5)
        
        # Prepare AI prompt
        prompt = self._build_generation_prompt(
            transcription,
            format_template,
            rough_cut_data.get("media_index", {})
        )
        
        if progress_callback:
            progress_callback("initiate_rough_cut", 4, 5)
        
        # TODO: In Story 5.2+, implement actual AI processing
        # For now, return initiated status
        
        if progress_callback:
            progress_callback("initiate_rough_cut", 5, 5)
        
        return {
            "status": "initiated",
            "message": "Rough cut generation prepared and ready for AI processing",
            "chunks_estimated": num_chunks,
            "transcript_length": len(transcript_text),
            "format_name": format_template.get("name", "Unknown")
        }
    
    def generate_rough_cut_streaming(
        self,
        rough_cut_data: Dict[str, Any]
    ) -> Generator[Dict[str, Any], None, None]:
        """Generate rough cut with streaming progress updates.
        
        Yields progress updates during generation, then final result.
        
        Args:
            rough_cut_data: Complete data bundle
            
        Yields:
            Progress update dictionaries or final result
        """
        yield {
            "type": "progress",
            "operation": "generate_rough_cut",
            "current": 1,
            "total": 5,
            "message": "Analyzing transcript structure..."
        }
        
        # Validate
        self._validate_rough_cut_data(rough_cut_data)
        
        yield {
            "type": "progress",
            "operation": "generate_rough_cut",
            "current": 2,
            "total": 5,
            "message": "Chunking transcript for context window..."
        }
        
        # Chunk transcript if needed
        transcription = rough_cut_data.get("transcription", {})
        chunks = self._chunk_transcript(transcription.get("text", ""))
        
        yield {
            "type": "progress",
            "operation": "generate_rough_cut",
            "current": 3,
            "total": 5,
            "message": f"Processing {len(chunks)} transcript segment(s)..."
        }
        
        # TODO: Implement actual AI processing in Story 5.2+
        # This is a placeholder for the streaming API
        
        yield {
            "type": "progress",
            "operation": "generate_rough_cut",
            "current": 4,
            "total": 5,
            "message": "Matching assets to segments..."
        }
        
        # Final result placeholder
        yield {
            "type": "progress",
            "operation": "generate_rough_cut",
            "current": 5,
            "total": 5,
            "message": "Generation complete"
        }
        
        # Return result structure
        yield {
            "result": {
                "status": "initiated",
                "segments": [],  # TODO: Populate in Story 5.2+
                "music_suggestions": [],
                "sfx_suggestions": [],
                "vfx_suggestions": []
            }
        }
    
    def _validate_rough_cut_data(self, data: Dict[str, Any]) -> None:
        """Validate rough cut data bundle.
        
        Args:
            data: Data bundle to validate
            
        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ["session_id", "media", "transcription", "format"]
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate nested structure
        media = data.get("media", {})
        if not media.get("clip_id"):
            raise ValueError("Missing required field: media.clip_id")
        
        transcription = data.get("transcription", {})
        if not transcription.get("text"):
            raise ValueError("Missing required field: transcription.text")
        
        format_template = data.get("format", {})
        if not format_template.get("slug"):
            raise ValueError("Missing required field: format.slug")
    
    def _calculate_chunks_needed(self, transcript_text: str) -> int:
        """Calculate number of chunks needed for transcript.
        
        Rough estimate: 1 token ≈ 4 characters for English text.
        
        Args:
            transcript_text: Full transcript text
            
        Returns:
            Estimated number of chunks
        """
        if not transcript_text:
            return 0
        
        # Rough token estimate (4 chars per token)
        estimated_tokens = len(transcript_text) // 4
        
        if estimated_tokens <= self.chunk_size:
            return 1
        
        # Calculate chunks with overlap
        effective_chunk_size = self.chunk_size - self.chunk_overlap
        if effective_chunk_size <= 0:
            # Guard against zero/negative chunk size
            effective_chunk_size = self.chunk_size // 2
        
        num_chunks = (estimated_tokens - self.chunk_overlap + effective_chunk_size - 1) // effective_chunk_size
        
        return max(1, num_chunks)
    
    def _chunk_transcript(self, transcript_text: str) -> List[str]:
        """Chunk transcript into overlapping segments.
        
        Preserves narrative continuity by including overlap context
        between chunks.
        
        Args:
            transcript_text: Full transcript text
            
        Returns:
            List of transcript chunks
        """
        if not transcript_text:
            return []
        
        # If short enough, return as single chunk
        estimated_tokens = len(transcript_text) // 4
        if estimated_tokens <= self.chunk_size:
            return [transcript_text]
        
        chunks = []
        
        # Character-based chunking (4 chars ≈ 1 token)
        char_chunk_size = self.chunk_size * 4
        char_overlap = self.chunk_overlap * 4
        
        # Try to chunk at sentence boundaries
        sentences = self._split_into_sentences(transcript_text)
        
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # Handle extremely long single sentences - split them
            if sentence_length > char_chunk_size:
                # First save any accumulated sentences as a chunk
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    overlap_sentences = self._get_overlap_sentences(current_chunk, char_overlap)
                    current_chunk = overlap_sentences
                    current_length = sum(len(s) for s in current_chunk)
                
                # Split the long sentence into smaller pieces
                words = sentence.split()
                current_piece = []
                current_piece_length = 0
                
                for word in words:
                    word_len = len(word) + 1  # +1 for space
                    if current_piece_length + word_len > char_chunk_size and current_piece:
                        # Save current piece as its own chunk
                        chunks.append(" ".join(current_piece))
                        # Start new piece with overlap from end of previous
                        overlap_words = self._get_overlap_words(current_piece, char_overlap)
                        current_piece = overlap_words + [word]
                        current_piece_length = sum(len(w) + 1 for w in current_piece)
                    else:
                        current_piece.append(word)
                        current_piece_length += word_len
                
                # Add remaining piece to current_chunk
                if current_piece:
                    current_chunk.append(" ".join(current_piece))
                    current_length = sum(len(s) for s in current_chunk)
            elif current_length + sentence_length > char_chunk_size and current_chunk:
                # Save current chunk
                chunks.append(" ".join(current_chunk))
                
                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(current_chunk, char_overlap)
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks if chunks else [transcript_text]
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences.
        
        Simple sentence boundary detection.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        import re
        
        # Simple regex for sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Clean and filter empty sentences
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_words(self, words: List[str], target_overlap_chars: int) -> List[str]:
        """Get words for overlap from previous piece.
        
        Args:
            words: Previous piece words
            target_overlap_chars: Target overlap in characters
            
        Returns:
            Words to include as overlap
        """
        overlap = []
        current_length = 0
        
        # Work backwards from end of words
        for word in reversed(words):
            word_len = len(word) + 1  # +1 for space
            if current_length + word_len <= target_overlap_chars:
                overlap.insert(0, word)
                current_length += word_len
            else:
                break
        
        return overlap
    
    def _get_overlap_sentences(self, sentences: List[str], target_overlap_chars: int) -> List[str]:
        """Get sentences for overlap from previous chunk.
        
        Args:
            sentences: Previous chunk sentences
            target_overlap_chars: Target overlap in characters
            
        Returns:
            Sentences to include as overlap
        """
        overlap = []
        current_length = 0
        
        # Work backwards from end of sentences
        for sentence in reversed(sentences):
            if current_length + len(sentence) <= target_overlap_chars:
                overlap.insert(0, sentence)
                current_length += len(sentence)
            else:
                break
        
        return overlap
    
    def _truncate_at_word_boundary(self, text: str, max_length: int) -> str:
        """Truncate text at word boundary.
        
        Args:
            text: Text to truncate
            max_length: Maximum length before truncation
            
        Returns:
            Truncated text with ellipsis if truncated
        """
        if len(text) <= max_length:
            return text
        
        # Find last space before max_length
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > 0:
            truncated = truncated[:last_space]
        
        return truncated + "..."

    def _build_generation_prompt(
        self,
        transcription: Dict[str, Any],
        format_template: Dict[str, Any],
        media_index: Dict[str, Any]
    ) -> str:
        """Build AI prompt for rough cut generation.
        
        Args:
            transcription: Transcription data
            format_template: Format template rules
            media_index: Indexed media assets
            
        Returns:
            Formatted prompt string
        """
        transcript_text = transcription.get("text", "")
        format_name = format_template.get("name", "Unknown Format")
        segments = format_template.get("segments", [])
        asset_groups = format_template.get("asset_groups", [])
        
        # Build segment structure description
        segment_descriptions = []
        for i, seg in enumerate(segments, 1):
            desc = f"Segment {i}: {seg.get('name', 'Unnamed')}"
            if seg.get('duration'):
                desc += f" ({seg.get('duration')})"
            if seg.get('purpose'):
                desc += f" - {seg.get('purpose')}"
            segment_descriptions.append(desc)
        
        # Build asset group descriptions
        asset_group_descriptions = []
        for ag in asset_groups:
            desc = f"- {ag.get('category', 'unknown')}: {ag.get('name', 'Unnamed')}"
            if ag.get('search_tags'):
                desc += f" (tags: {', '.join(ag.get('search_tags', []))})"
            asset_group_descriptions.append(desc)
        
        prompt = f"""You are an expert video editor creating a rough cut based on a transcript and format template.

## Format Template: {format_name}

### Timing Structure:
{chr(10).join(segment_descriptions) if segment_descriptions else "No specific segments defined"}

### Asset Groups to Match:
{chr(10).join(asset_group_descriptions) if asset_group_descriptions else "No asset groups defined"}

## Transcript:

{self._truncate_at_word_boundary(transcript_text, 4000)}

## Instructions:

1. Cut the transcript into segments that match the format structure above
2. Preserve ALL original words exactly - do not summarize or paraphrase
3. Identify emotional tone and context for each segment
4. Suggest appropriate music from asset groups for each segment
5. Identify moments for SFX (transitions, emphasis points)
6. Note where VFX/templates should be positioned

## Output Format:

Return a JSON structure with:
- segments: array of {{
    name: string,
    start_time: string,
    end_time: string,
    transcript_text: string,
    tone: string,
    music_suggestion: string,
    sfx_suggestions: array of strings,
    vfx_suggestions: array of strings
  }}

Focus on matching the format structure while preserving the narrative flow.
"""
        
        return prompt
