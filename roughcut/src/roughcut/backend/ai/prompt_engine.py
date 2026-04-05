"""Prompt builder for AI rough cut generation.

Provides PromptBuilder class for constructing structured AI prompts
with system messages, transcript context, and media index.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .data_bundle import DataBundle, MediaAssetMetadata

logger = logging.getLogger(__name__)


@dataclass
class PromptConfig:
    """Configuration for AI prompt generation."""
    system_prompt: str
    temperature: float = 0.3
    max_tokens: int = 4000
    model: str = "gpt-4"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": self.system_prompt}
            ]
        }


class PromptBuilder:
    """Builder for constructing AI prompts for rough cut generation.
    
    Creates structured prompts with:
    - System instructions with format requirements
    - Transcript context with segment boundaries
    - Filtered media index with contextual tags
    - Output format specifications
    
    Example:
        builder = PromptBuilder()
        prompt = builder.build(
            data_bundle=bundle,
            format_instructions={...}
        )
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert video editor AI specializing in rough cut generation.

Your task is to analyze transcripts and create rough cut recommendations that match format templates.

STRICT RULES:
1. Cut transcripts into segments matching the format structure
2. Preserve ALL original words exactly - NEVER summarize or paraphrase
3. Match music from the provided index based on context and emotional tone
4. Layer SFX for emotional beats and transitions
5. Position VFX templates at appropriate moments

OUTPUT FORMAT:
Return ONLY a JSON object with this structure:
{
    "segments": [
        {
            "name": "segment name",
            "start_time": "0:00",
            "end_time": "1:30",
            "transcript_text": "original transcript words...",
            "tone": "emotional tone",
            "music_suggestion": "filename.wav",
            "sfx_suggestions": ["filename.wav"],
            "vfx_suggestions": ["template_name"]
        }
    ]
}

IMPORTANT:
- All timestamps must be in MM:SS or HH:MM:SS format
- Music suggestions should reference files from the provided index only
- Preserve narrative flow and emotional arc"""
    
    def __init__(self, system_prompt: str | None = None, model: str = "gpt-4"):
        """Initialize the prompt builder.
        
        Args:
            system_prompt: Optional custom system prompt
            model: Model to use for AI requests (default: gpt-4)
        """
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.model = model
    
    def build(self, data_bundle: DataBundle) -> dict[str, Any]:
        """Build complete AI prompt from data bundle.
        
        Args:
            data_bundle: Complete data bundle with transcript, format, and media
            
        Returns:
            Dictionary ready for OpenAI API call
        """
        logger.info(f"Building AI prompt for session {data_bundle.session_id}")
        
        # Build user content
        user_content = self._build_user_content(data_bundle)
        
        # Construct API request
        prompt = {
            "model": self.model,
            "temperature": 0.3,  # Low temperature for consistent formatting
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ]
        }
        
        logger.info(f"AI prompt built successfully (model: {self.model})")
        return prompt
    
    def build_with_chunking(
        self,
        data_bundle: DataBundle,
        chunk_index: int,
        total_chunks: int,
        chunk_text: str
    ) -> dict[str, Any]:
        """Build AI prompt for a specific chunk.
        
        Used when transcript exceeds context window and needs chunking.
        
        Args:
            data_bundle: Complete data bundle
            chunk_index: Current chunk index (0-based)
            total_chunks: Total number of chunks
            chunk_text: Text for this specific chunk
            
        Returns:
            Dictionary ready for OpenAI API call
        """
        logger.info(f"Building chunked prompt {chunk_index + 1}/{total_chunks}")
        
        # Build user content with chunk context
        user_content = self._build_chunked_user_content(
            data_bundle,
            chunk_index,
            total_chunks,
            chunk_text
        )
        
        # Add chunk-specific system instructions
        chunk_system_prompt = self.system_prompt + f"""

CHUNK CONTEXT:
This is chunk {chunk_index + 1} of {total_chunks}.
- Process this chunk independently but maintain continuity with adjacent chunks
- Focus on complete segments within this chunk
- Note any segments that span chunk boundaries for later assembly
"""
        
        prompt = {
            "model": self.model,
            "temperature": 0.3,
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "system",
                    "content": chunk_system_prompt
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ]
        }
        
        return prompt
    
    def _build_user_content(self, data_bundle: DataBundle) -> str:
        """Build user content section of the prompt.
        
        Args:
            data_bundle: Data bundle with all context
            
        Returns:
            Formatted user content string
        """
        sections = []
        
        # Format template section
        format_section = self._build_format_section(data_bundle.format_template)
        sections.append(format_section)
        
        # Transcript section
        transcript_section = self._build_transcript_section(data_bundle.transcript)
        sections.append(transcript_section)
        
        # Media index section
        media_section = self._build_media_section(data_bundle.media_index)
        sections.append(media_section)
        
        # Instructions
        sections.append(self._build_instructions())
        
        return "\n\n---\n\n".join(sections)
    
    def _build_chunked_user_content(
        self,
        data_bundle: DataBundle,
        chunk_index: int,
        total_chunks: int,
        chunk_text: str
    ) -> str:
        """Build user content for a specific chunk.
        
        Args:
            data_bundle: Complete data bundle
            chunk_index: Current chunk index
            total_chunks: Total chunks
            chunk_text: Text for this chunk
            
        Returns:
            Formatted user content string
        """
        sections = []
        
        # Format template section (full context)
        format_section = self._build_format_section(data_bundle.format_template)
        sections.append(format_section)
        
        # Chunked transcript
        transcript_section = f"""## TRANSCRIPT (Chunk {chunk_index + 1}/{total_chunks})

{chunk_text}

Note: Process this segment independently while maintaining narrative continuity."""
        sections.append(transcript_section)
        
        # Media index
        media_section = self._build_media_section(data_bundle.media_index)
        sections.append(media_section)
        
        # Instructions
        sections.append(self._build_instructions())
        
        return "\n\n---\n\n".join(sections)
    
    def _build_format_section(self, format_template) -> str:
        """Build format template section.
        
        Args:
            format_template: Format rules
            
        Returns:
            Formatted format section
        """
        lines = [
            f"## FORMAT TEMPLATE: {format_template.name}",
            f"Slug: {format_template.slug}",
            ""
        ]
        
        # Add segments
        if format_template.segments:
            lines.append("### TIMING STRUCTURE:")
            for i, seg in enumerate(format_template.segments, 1):
                name = seg.get("name", f"Segment {i}")
                duration = seg.get("duration", "")
                purpose = seg.get("purpose", "")
                
                line = f"{i}. {name}"
                if duration:
                    line += f" ({duration})"
                if purpose:
                    line += f" - {purpose}"
                lines.append(line)
            lines.append("")
        
        # Add asset groups
        if format_template.asset_groups:
            lines.append("### ASSET GROUPS TO MATCH:")
            for ag in format_template.asset_groups:
                category = ag.get("category", "unknown")
                name = ag.get("name", "Unnamed")
                search_tags = ag.get("search_tags", [])
                
                line = f"- [{category}] {name}"
                if search_tags:
                    line += f" (tags: {', '.join(search_tags)})"
                lines.append(line)
            lines.append("")
        
        # Add rules
        if format_template.rules:
            lines.append("### RULES:")
            for key, value in format_template.rules.items():
                lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)
    
    def _build_transcript_section(self, transcript) -> str:
        """Build transcript section.
        
        Args:
            transcript: Transcript data
            
        Returns:
            Formatted transcript section
        """
        lines = ["## TRANSCRIPT"]
        
        # Add segment markers if available
        if transcript.segments:
            lines.append("\nSegment boundaries:")
            for seg in transcript.segments:
                start = seg.get("start", 0)
                end = seg.get("end", 0)
                text = seg.get("text", "")
                lines.append(f"[{start}s - {end}s]: {text[:50]}...")
            lines.append("")
        
        # Add full transcript
        lines.append("Full text:")
        lines.append(transcript.text)
        
        return "\n".join(lines)
    
    def _build_media_section(self, media_index) -> str:
        """Build media index section.
        
        Args:
            media_index: Media index subset
            
        Returns:
            Formatted media section
        """
        lines = ["## AVAILABLE MEDIA ASSETS"]
        lines.append("(Use ONLY these assets for suggestions)\n")
        
        # Music assets
        if media_index.music:
            lines.append("### MUSIC:")
            for asset in media_index.music[:20]:  # Limit for token efficiency
                lines.append(self._format_asset(asset))
            if len(media_index.music) > 20:
                lines.append(f"... and {len(media_index.music) - 20} more")
            lines.append("")
        
        # SFX assets
        if media_index.sfx:
            lines.append("### SFX:")
            for asset in media_index.sfx[:20]:  # Limit for token efficiency
                lines.append(self._format_asset(asset))
            if len(media_index.sfx) > 20:
                lines.append(f"... and {len(media_index.sfx) - 20} more")
            lines.append("")
        
        # VFX assets
        if media_index.vfx:
            lines.append("### VFX/TEMPLATES:")
            for asset in media_index.vfx[:20]:  # Limit for token efficiency
                lines.append(self._format_asset(asset))
            if len(media_index.vfx) > 20:
                lines.append(f"... and {len(media_index.vfx) - 20} more")
            lines.append("")
        
        # Summary
        total = len(media_index.get_all_assets())
        lines.append(f"Total available assets: {total}")
        
        return "\n".join(lines)
    
    def _format_asset(self, asset: MediaAssetMetadata) -> str:
        """Format a single asset for the prompt.
        
        Args:
            asset: Media asset metadata
            
        Returns:
            Formatted asset string
        """
        line = f"- {asset.filename}"
        if asset.tags:
            tags_str = ", ".join(asset.tags[:5])  # Limit tags shown
            line += f" [tags: {tags_str}]"
        return line
    
    def _build_instructions(self) -> str:
        """Build final instructions section.
        
        Returns:
            Instructions string
        """
        return """## INSTRUCTIONS

1. Analyze the format template structure and timing requirements
2. Cut the transcript into segments matching the format structure
3. Preserve ALL original words - do not summarize or paraphrase
4. For each segment, identify the emotional tone and context
5. Match appropriate music from the available assets based on:
   - Segment tone (upbeat, contemplative, dramatic, etc.)
   - Format asset group requirements
   - Available tags in the music files
6. Identify moments for SFX (transitions, emphasis, emotional beats)
7. Note where VFX/templates should be positioned
8. Return the result as JSON per the output format specified in your system instructions

Remember: Only suggest assets from the provided index. Do not invent filenames."""
    
    def build_transcript_cutting_prompt(
        self,
        transcript_text: str,
        format_structure: str,
        system_prompt_path: str | None = None
    ) -> dict[str, Any]:
        """Build prompt for transcript cutting operation.
        
        Constructs a prompt specifically for cutting transcripts into segments
        matching format structure, with strict word preservation requirements.
        
        Args:
            transcript_text: Full source transcript text
            format_structure: Format structure description (JSON or formatted text)
            system_prompt_path: Optional path to custom system prompt template
            
        Returns:
            Dictionary ready for OpenAI API call
        """
        from pathlib import Path
        
        logger.info("Building transcript cutting prompt")
        
        # Load system prompt template
        if system_prompt_path and Path(system_prompt_path).exists():
            system_prompt = Path(system_prompt_path).read_text()
        else:
            # Use default template from prompt_templates directory
            default_path = Path(__file__).parent / "prompt_templates" / "cut_transcript_system.txt"
            if default_path.exists():
                system_prompt = default_path.read_text()
            else:
                # Fallback inline prompt
                system_prompt = self._get_default_cutting_prompt()
        
        # Fill in template placeholders
        system_prompt = system_prompt.replace("{format_structure}", format_structure)
        system_prompt = system_prompt.replace("{transcript_text}", transcript_text)
        
        # Construct API request
        # Note: transcript included in system prompt only, not duplicated in user message
        prompt = {
            "model": self.model,
            "temperature": 0.1,  # Very low temperature for strict adherence
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": "Cut the transcript according to the format structure provided above."
                }
            ]
        }
        
        logger.info("Transcript cutting prompt built successfully")
        return prompt
    
    def _get_default_cutting_prompt(self) -> str:
        """Get default transcript cutting system prompt.
        
        Returns:
            Default system prompt for transcript cutting
        """
        return """You are an expert video editor AI tasked with cutting transcripts for rough cut generation.

CRITICAL RULES:
1. NEVER change, paraphrase, summarize, or modify ANY words
2. ONLY adjust start and end timestamps to select segments
3. Extract EXACTLY the number of sections specified in the format
4. Each segment text must exist VERBATIM in the source transcript
5. Map each segment to the correct format section name

Your task:
- Identify narrative beats that align with the format structure
- Select segments that tell a coherent story within each section
- Preserve the exact words from the source transcript - no modifications
- Return JSON with segment boundaries and verbatim text

Output format (JSON only):
{
  "segments": [
    {
      "section_name": "<section name from format>",
      "start_time": <float in seconds>,
      "end_time": <float in seconds>,
      "text": "<exact verbatim text from transcript>"
    }
  ]
}

REMEMBER:
- The "text" field must be copied EXACTLY from the source transcript
- Do not paraphrase, summarize, or modify any words
- Ensure the number of segments matches the format requirements
- Each segment should fit the section's purpose (intro hook, main narrative, outro call-to-action)"""
    
    def estimate_tokens(self, data_bundle: DataBundle) -> int:
        """Estimate token count for the prompt.
        
        Rough estimate for planning API calls.
        
        Args:
            data_bundle: Data bundle to estimate
            
        Returns:
            Estimated token count
        """
        # System prompt tokens
        system_tokens = len(self.system_prompt) // 4
        
        # User content tokens
        user_content = self._build_user_content(data_bundle)
        user_tokens = len(user_content) // 4
        
        # Output overhead
        output_tokens = 1000  # Conservative estimate for JSON response
        
        return system_tokens + user_tokens + output_tokens
    
    def build_music_matching_prompt(
        self,
        segments: list[dict[str, Any]],
        music_index: list[dict[str, Any]],
        system_prompt_path: str | None = None
    ) -> dict[str, Any]:
        """Build prompt for music matching operation.
        
        Constructs a prompt for matching music assets to transcript segments
        based on emotional tone and contextual relevance.
        
        Args:
            segments: List of transcript segment dictionaries with tone data
            music_index: List of music asset dictionaries from indexed library
            system_prompt_path: Optional path to custom system prompt template
            
        Returns:
            Dictionary ready for OpenAI API call
            
        Raises:
            ValueError: If segments or music_index is empty
        """
        logger.info("Building music matching prompt")
        
        # Validate inputs
        if not segments:
            raise ValueError("segments cannot be empty")
        if not music_index:
            raise ValueError("music_index cannot be empty")
        
        # Load system prompt template
        if system_prompt_path and Path(system_prompt_path).exists():
            system_prompt = Path(system_prompt_path).read_text()
        else:
            # Use default template from prompt_templates directory
            default_path = Path(__file__).parent / "prompt_templates" / "match_music_system.txt"
            if default_path.exists():
                system_prompt = default_path.read_text()
            else:
                # Fallback inline prompt
                system_prompt = self._get_default_music_matching_prompt()
        
        # Format segments for prompt
        segments_json = json.dumps(segments, indent=2)
        
        # Format music index for prompt (limit to first 50 assets for token efficiency)
        limited_index = music_index[:50] if len(music_index) > 50 else music_index
        music_index_json = json.dumps(limited_index, indent=2)
        
        # Fill in template placeholders
        system_prompt = system_prompt.replace("{segments}", segments_json)
        system_prompt = system_prompt.replace("{music_index}", music_index_json)
        
        # Construct API request
        prompt = {
            "model": self.model,
            "temperature": 0.3,  # Moderate temperature for creative but consistent matching
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": "Match the most appropriate music to each segment based on tone and context."
                }
            ]
        }
        
        logger.info(
            f"Music matching prompt built successfully ({len(segments)} segments, "
            f"{len(music_index)} music assets)"
        )
        return prompt
    
    def _get_default_music_matching_prompt(self) -> str:
        """Get default music matching system prompt.
        
        Returns:
            Default system prompt for music matching
        """
        return """You are an expert video editor AI tasked with matching background music to video segments.

CRITICAL RULES:
1. Analyze each segment's emotional tone and energy level
2. Match music tags to segment tone descriptors for contextual relevance
3. Prioritize exact tag matches over partial matches
4. Consider folder context as additional matching signal
5. Suggest music that enhances the narrative without overwhelming dialogue
6. Return top 3 matches per segment with confidence scores and reasoning

Your task:
- For each segment, determine: energy (high/medium/low), mood (upbeat/contemplative/triumphant/tense), genre hint
- Search the available music library using tag similarity to segment tone
- Score matches based on: tag relevance, folder context, musical appropriateness
- Return top 3 matches per segment with confidence scores (0.0-1.0)
- Include clear match reasoning for each suggestion

Output format (JSON only):
{
  "segment_matches": [
    {
      "segment_name": "<section name>",
      "tone": {
        "energy": "<high|medium|low>",
        "mood": "<upbeat|contemplative|triumphant|tense>",
        "genre_hint": "<corporate|ambient|orchestral|electronic>"
      },
      "matches": [
        {
          "music_id": "<asset id>",
          "confidence_score": <0.0-1.0>,
          "match_reason": "<clear explanation>",
          "matched_tags": ["<tag1>", "<tag2>"],
          "suggested_start": <start_time>,
          "suggested_end": <end_time>
        }
      ]
    }
  ],
  "fallback_used": false,
  "consistency_notes": "<notes on musical consistency>"
}

MATCHING GUIDELINES:
- Confidence 0.90-1.0: Perfect match - tags align perfectly with tone
- Confidence 0.80-0.89: Strong match - multiple relevant tags match
- Confidence 0.60-0.79: Moderate match - some tag overlap
- Confidence < 0.60: Weak match - limited relevance

REMEMBER:
- The goal is contextual enhancement - music should support the narrative
- Consider segment transitions - intros and outros should have cohesive energy
- Match reasoning should explain WHY this music fits this segment's tone"""
