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
    
    def build_sfx_matching_prompt(
        self,
        segments: list[dict[str, Any]],
        sfx_index: list[dict[str, Any]],
        system_prompt_path: str | None = None
    ) -> dict[str, Any]:
        """Build prompt for SFX matching operation.
        
        Constructs a prompt for matching sound effects to key moments
        in transcript segments based on context and subtlety requirements.
        
        Args:
            segments: List of transcript segment dictionaries with tone data
            sfx_index: List of SFX asset dictionaries from indexed library
            system_prompt_path: Optional path to custom system prompt template
            
        Returns:
            Dictionary ready for OpenAI API call
            
        Raises:
            ValueError: If segments or sfx_index is empty
        """
        logger.info("Building SFX matching prompt")
        
        # Validate inputs
        if not segments:
            raise ValueError("segments cannot be empty")
        if not sfx_index:
            raise ValueError("sfx_index cannot be empty")
        
        # Load system prompt template
        if system_prompt_path and Path(system_prompt_path).exists():
            system_prompt = Path(system_prompt_path).read_text()
        else:
            # Use default template from prompt_templates directory
            default_path = Path(__file__).parent / "prompt_templates" / "match_sfx_system.txt"
            if default_path.exists():
                system_prompt = default_path.read_text()
            else:
                # Fallback inline prompt
                system_prompt = self._get_default_sfx_matching_prompt()
        
        # Format segments for prompt
        segments_json = json.dumps(segments, indent=2)
        
        # Format SFX index for prompt (limit to first 50 assets for token efficiency)
        limited_index = sfx_index[:50] if len(sfx_index) > 50 else sfx_index
        sfx_index_json = json.dumps(limited_index, indent=2)
        
        # Fill in template placeholders
        system_prompt = system_prompt.replace("{segments}", segments_json)
        system_prompt = system_prompt.replace("{sfx_index}", sfx_index_json)
        
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
                    "content": "Match the most appropriate sound effects to each moment based on context and subtlety."
                }
            ]
        }
        
        logger.info(
            f"SFX matching prompt built successfully ({len(segments)} segments, "
            f"{len(sfx_index)} SFX assets)"
        )
        return prompt
    
    def build_vfx_matching_prompt(
        self,
        segments: list[dict[str, Any]],
        format_template: dict[str, Any],
        vfx_index: list[dict[str, Any]],
        system_prompt_path: str | None = None
    ) -> dict[str, Any]:
        """Build prompt for VFX matching operation.
        
        Constructs a prompt for matching VFX templates to format requirements
        based on template asset groups, tag relevance, and placement constraints.
        
        Args:
            segments: List of transcript segment dictionaries with speaker data
            format_template: Format template with vfx_requirements and template_asset_groups
            vfx_index: List of VFX asset dictionaries from indexed library
            system_prompt_path: Optional path to custom system prompt template
            
        Returns:
            Dictionary ready for OpenAI API call
            
        Raises:
            ValueError: If segments or vfx_index is empty
        """
        logger.info("Building VFX matching prompt")
        
        # Validate inputs
        if not segments:
            raise ValueError("segments cannot be empty")
        if not vfx_index:
            raise ValueError("vfx_index cannot be empty")
        
        # Load system prompt template
        if system_prompt_path and Path(system_prompt_path).exists():
            system_prompt = Path(system_prompt_path).read_text()
        else:
            # Use default template from prompt_templates directory
            default_path = Path(__file__).parent / "prompt_templates" / "match_vfx_system.txt"
            if default_path.exists():
                system_prompt = default_path.read_text()
            else:
                # Fallback inline prompt
                system_prompt = self._get_default_vfx_matching_prompt()
        
        # Format segments for prompt
        segments_json = json.dumps(segments, indent=2)
        
        # Format format template for prompt
        format_json = json.dumps(format_template, indent=2)
        
        # Format VFX index for prompt (limit to first 50 assets for token efficiency)
        limited_index = vfx_index[:50] if len(vfx_index) > 50 else vfx_index
        vfx_index_json = json.dumps(limited_index, indent=2)
        
        # Fill in template placeholders
        system_prompt = system_prompt.replace("{segments}", segments_json)
        system_prompt = system_prompt.replace("{format_template}", format_json)
        system_prompt = system_prompt.replace("{vfx_index}", vfx_index_json)
        
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
                    "content": "Match the most appropriate VFX templates to each requirement based on type, context, and template asset groups."
                }
            ]
        }
        
        logger.info(
            f"VFX matching prompt built successfully ({len(segments)} segments, "
            f"{len(vfx_index)} VFX assets)"
        )
        return prompt
    
    def _get_default_vfx_matching_prompt(self) -> str:
        """Get default VFX matching system prompt.
        
        Returns:
            Default system prompt for VFX matching
        """
        return """You are an expert video editor AI tasked with matching VFX templates to format requirements.

CRITICAL RULES:
1. Parse format template VFX specifications (lower_thirds, transitions, outro_cta, etc.)
2. Identify speaker changes and introduction moments for lower third placement
3. Match VFX tags to requirement context (e.g., "lower_third" + "corporate" for speaker intros)
4. Respect template durations - never suggest templates that exceed required duration
5. Prioritize templates from predefined asset groups when available
6. Calculate precise timestamps aligning with transcript segment boundaries

TEMPLATE ASSET GROUPS:
Format templates may define predefined asset groups that specify preferred assets:
- lower_thirds: Templates for speaker name displays
- transitions: Templates for section transitions  
- titles: Templates for title cards and headers
- outros: Templates for ending sequences and CTAs
- logos: Templates for logo animations

Always prioritize assets from these groups when available and appropriate.

PLACEMENT CONSTRAINTS:
- Lower thirds should appear at speaker introduction moments
- Transitions should bridge between segments
- Title cards should mark major section beginnings
- Outro CTAs should appear near segment ends
- Avoid overlapping placements when possible

MATCH SCORING:
Confidence score (0.0-1.0) based on:
- Tag relevance: Exact tag matches score highest
- Template type match: Preferred types for requirement score higher
- Template group membership: Assets from predefined groups get bonus
- Folder context: Assets in relevant folders score higher

Output format (JSON only):
{
  "requirement_matches": [
    {
      "requirement": {
        "timestamp": <float>,
        "type": "lower_third|transition|title_card|outro_cta|logo_anim",
        "context": "<why this VFX is needed>",
        "duration": <float>,
        "format_section": "<section name>"
      },
      "matches": [
        {
          "vfx_id": "<asset id>",
          "confidence_score": <0.0-1.0>,
          "match_reason": "<clear explanation>",
          "matched_tags": ["<tag1>", "<tag2>"],
          "template_type": "fusion_composition|generator|transition",
          "placement": {
            "start_time": <float>,
            "end_time": <float>,
            "duration_ms": <int>
          },
          "from_template_group": true|false
        }
      ]
    }
  ],
  "fallback_used": false,
  "placement_conflicts": []
}

MATCHING GUIDELINES:
- Confidence 0.85-1.0: Excellent match (use with confidence)
- Confidence 0.60-0.84: Good match (acceptable quality)
- Confidence 0.50-0.59: Marginal match (review recommended)
- Confidence < 0.50: Poor match (consider alternatives)

REMEMBER:
- Prioritize template asset group membership for consistency
- Match template type to requirement (fusion_composition for lower thirds, etc.)
- Consider placement timing to avoid overlaps
- Match reasoning should explain WHY this template fits this requirement"""

    def build_chunked_processing_prompt(
        self,
        chunk: Any,
        chunk_context: Any,
        continuity_context: dict[str, Any],
        asset_index: dict[str, list[dict]],
        format_template: dict[str, Any],
        total_chunks: int = 1
    ) -> dict[str, Any]:
        """Build AI prompt for chunked processing.
        
        Creates a comprehensive prompt for processing a single chunk with
        continuity context from previous chunks.
        
        Args:
            chunk: TranscriptChunk to process
            chunk_context: ChunkContext with filtering info
            continuity_context: Dict with continuity from previous chunk
            asset_index: Filtered asset index for this chunk
            format_template: Format template dictionary
            total_chunks: Total number of chunks (default: 1)
            
        Returns:
            Dictionary ready for OpenAI API call
        """
        # Load system prompt template
        system_prompt = self._get_default_chunked_processing_prompt()
        
        # Build continuity context string
        if continuity_context.get("has_previous", False):
            prev_context = continuity_context.get("previous_ending_context", "")
            continuity_str = f"Previous chunk ended with: {prev_context}"
        else:
            continuity_str = "This is the first chunk. Establish a strong opening."
        
        # Format the system prompt
        duration = chunk.end_time - chunk.start_time
        formatted_system = system_prompt.format(
            chunk_index=chunk.index + 1,  # 1-indexed for display
            total_chunks=total_chunks,
            start_time=f"{chunk.start_time:.1f}",
            end_time=f"{chunk.end_time:.1f}",
            section_type=chunk_context.section_type,
            tone=chunk_context.tone,
            duration=f"{duration:.1f}",
            continuity_context=continuity_str,
            overlap_from_previous=chunk.overlap_with_previous[:200] if chunk.overlap_with_previous else "",
            transcript_segments=self._format_chunk_segments(chunk.segments),
            format_rules=self._format_format_template(format_template),
            music_assets=self._format_assets(asset_index.get("music", [])),
            sfx_assets=self._format_assets(asset_index.get("sfx", [])),
            vfx_assets=self._format_assets(asset_index.get("vfx", []))
        )
        
        # Build user content
        user_content = f"""## CHUNK PROCESSING REQUEST

Process this transcript chunk ({chunk.index + 1}) according to the format rules above.

Chunk Time Range: {chunk.start_time:.1f}s to {chunk.end_time:.1f}s
Section Type: {chunk_context.section_type}
Tone: {chunk_context.tone}

Provide output in the specified JSON format with all matches and continuity markers.
"""
        
        prompt = {
            "model": self.model,
            "temperature": 0.3,
            "max_tokens": 4000,
            "messages": [
                {"role": "system", "content": formatted_system},
                {"role": "user", "content": user_content}
            ]
        }
        
        return prompt
    
    def _get_default_chunked_processing_prompt(self) -> str:
        """Get default chunked processing system prompt.
        
        Returns:
            Default system prompt template
        """
        # Load from file if available
        template_path = Path(__file__).parent / "prompt_templates" / "chunked_processing_system.txt"
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        
        # Fallback default
        return """You are processing chunk {chunk_index} of {total_chunks} for rough cut generation.

## CHUNK CONTEXT
- **Time Range**: {start_time}s to {end_time}s
- **Section Type**: {section_type}
- **Tone**: {tone}

## CRITICAL RULES FOR CHUNKED PROCESSING
1. Process only within your assigned time range
2. Maintain narrative continuity with adjacent chunks
3. Use context from previous chunk: {overlap_from_previous}
4. Cut transcript WITHOUT changing words
5. Match assets from the provided filtered list

## OUTPUT FORMAT
Return a JSON object with:
- transcript_cuts: List of segment cuts
- music_matches: Matched music assets
- sfx_matches: Matched SFX assets
- vfx_matches: Matched VFX assets
- continuity_markers: Context for next chunk"""
    
    def _format_chunk_segments(self, segments: list[dict]) -> str:
        """Format chunk segments for prompt.
        
        Args:
            segments: List of segment dictionaries
            
        Returns:
            Formatted segments string
        """
        lines = []
        for seg in segments:
            start = seg.get("start", 0.0)
            end = seg.get("end", 0.0)
            text = seg.get("text", "")
            speaker = seg.get("speaker", "Unknown")
            lines.append(f"[{start:.1f}s - {end:.1f}s] {speaker}: {text}")
        return "\n".join(lines)
    
    def _format_format_template(self, format_template: dict[str, Any]) -> str:
        """Format format template for prompt.
        
        Args:
            format_template: Format template dictionary
            
        Returns:
            Formatted template string
        """
        lines = []
        lines.append(f"Template: {format_template.get('name', 'Unknown')}")
        
        sections = format_template.get("sections", [])
        if sections:
            lines.append("\nSections:")
            for section in sections:
                name = section.get("name", "Unknown")
                duration = section.get("duration", 0)
                lines.append(f"- {name}: {duration}s")
                categories = section.get("asset_categories", [])
                if categories:
                    lines.append(f"  Assets: {', '.join(categories)}")
        
        return "\n".join(lines)
    
    def _format_assets(self, assets: list[dict]) -> str:
        """Format assets for prompt.
        
        Args:
            assets: List of asset dictionaries
            
        Returns:
            Formatted assets string
        """
        if not assets:
            return "None available"
        
        lines = []
        for asset in assets[:20]:  # Limit to 20 assets for token efficiency
            asset_id = asset.get("id", "unknown")
            tags = asset.get("tags", [])
            tags_str = ", ".join(tags[:5]) if tags else "no tags"
            lines.append(f"- {asset_id} [{tags_str}]")
        
        if len(assets) > 20:
            lines.append(f"... and {len(assets) - 20} more")
        
        return "\n".join(lines)
