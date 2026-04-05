"""Transcript cutting logic for AI-powered rough cut generation.

Provides TranscriptCutter class for parsing AI responses and validating
transcript segment extraction with word preservation guarantees.
"""

import logging
from typing import Any, Dict, List

from .transcript_segment import (
    FormatCompliance,
    TranscriptCutResult,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)


class TranscriptCutter:
    """Transcript cutting and validation logic.
    
    Processes AI responses containing transcript segment recommendations,
    validates word preservation, calculates segment markers, and ensures
    format compliance.
    
    Key features:
    - Word preservation validation (no AI modifications allowed)
    - Section count enforcement
    - Segment boundary validation
    - Format compliance checking
    
    Example:
        cutter = TranscriptCutter()
        result = cutter.cut_transcript_to_format(
            transcript={"text": "...", "segments": [...]},
            format_template={"slug": "...", "segments": [...]},
            ai_response={"segments": [...]}
        )
    """
    
    def cut_transcript_to_format(
        self,
        transcript: Dict[str, Any],
        format_template: Dict[str, Any],
        ai_response: Dict[str, Any]
    ) -> TranscriptCutResult:
        """Cut transcript into segments based on AI response.
        
        Processes AI-generated segment recommendations, validates word
        preservation for each segment, and checks format compliance.
        
        Args:
            transcript: Transcript data with text and segments
            format_template: Format template with section requirements
            ai_response: AI response with segment recommendations
            
        Returns:
            TranscriptCutResult with validated segments and compliance info
            
        Raises:
            ValueError: If required parameters are None or invalid
        """
        # Null parameter validation
        if transcript is None:
            raise ValueError("transcript cannot be None")
        if format_template is None:
            raise ValueError("format_template cannot be None")
        if ai_response is None:
            raise ValueError("ai_response cannot be None")
        
        logger.info("Processing transcript cutting request")
        
        warnings: List[str] = []
        errors: List[str] = []
        segments: List[TranscriptSegment] = []
        
        # Extract source transcript text
        source_text = transcript.get("text", "")
        
        # Validate transcript text is a string
        if source_text is not None and not isinstance(source_text, str):
            raise ValueError(
                f"transcript['text'] must be a string, got {type(source_text).__name__}"
            )
        
        # Early return on empty transcript
        if not source_text or not source_text.strip():
            logger.error("Empty transcript provided - cannot process")
            return TranscriptCutResult(
                segments=[],
                total_duration=0.0,
                format_compliance=FormatCompliance(
                    required_sections=0,
                    extracted_sections=0,
                    compliant=False
                ),
                warnings=["Empty transcript provided - no segments extracted"]
            )
        
        # Extract format sections
        format_sections = format_template.get("segments", [])
        if format_sections is None:
            format_sections = []
        required_sections = len(format_sections)
        
        # Extract AI segments
        ai_segments = ai_response.get("segments", [])
        if ai_segments is None:
            ai_segments = []
        if not isinstance(ai_segments, list):
            raise ValueError(f"ai_response['segments'] must be a list, got {type(ai_segments).__name__}")
        extracted_sections = len(ai_segments)
        
        logger.info(f"Processing {extracted_sections} AI segments "
                   f"(required: {required_sections})")
        
        # Build format section purpose map for validation
        section_purposes = {}
        for section in format_sections:
            section_name = section.get("name", "")
            section_purpose = section.get("type", section.get("purpose", ""))
            if section_name:
                section_purposes[section_name] = section_purpose
        
        # Process each AI segment
        narrative_purpose_errors = []
        for ai_segment in ai_segments:
            try:
                segment = self._process_segment(ai_segment, source_text, section_purposes)
                
                if segment is not None:
                    # Check for word preservation issues
                    if not segment.source_words_preserved:
                        errors.append(
                            f"WORD_MODIFICATION_DETECTED: Segment '{segment.section_name}' "
                            f"contains modified text - re-prompt AI with stricter word preservation instructions"
                        )
                        logger.error(
                            f"Word preservation failed for segment {segment.section_name}"
                        )
                    
                    # Check narrative purpose alignment (affects compliance)
                    expected_purpose = section_purposes.get(segment.section_name, "")
                    if expected_purpose and segment.narrative_purpose and segment.narrative_purpose != expected_purpose:
                        narrative_purpose_errors.append(segment.section_name)
                        errors.append(
                            f"NARRATIVE_BEAT_MISMATCH: Segment '{segment.section_name}' purpose "
                            f"'{segment.narrative_purpose}' doesn't match format section purpose "
                            f"'{expected_purpose}' - re-prompt AI with correct section purposes"
                        )
                        logger.error(
                            f"Narrative beat mismatch for segment {segment.section_name}: "
                            f"expected '{expected_purpose}', got '{segment.narrative_purpose}'"
                        )
                    
                    segments.append(segment)
                    
            except ValueError as e:
                errors.append(f"Segment validation error: {str(e)}")
                logger.error(f"Segment validation failed: {e}")
        
        # Detect overlapping segments
        if len(segments) > 1:
            sorted_segments = sorted(segments, key=lambda s: s.start_time)
            for i in range(len(sorted_segments) - 1):
                current = sorted_segments[i]
                next_seg = sorted_segments[i + 1]
                if current.end_time > next_seg.start_time:
                    errors.append(
                        f"OVERLAPPING_SEGMENTS: Segments '{current.section_name}' "
                        f"({current.start_time}s-{current.end_time}s) and '{next_seg.section_name}' "
                        f"({next_seg.start_time}s-{next_seg.end_time}s) overlap - "
                        f"re-prompt AI to ensure non-overlapping segments"
                    )
                    logger.error(
                        f"Overlapping segments detected: {current.section_name} and {next_seg.section_name}"
                    )
        
        # Calculate total duration (union of non-overlapping segments)
        total_duration = sum(s.end_time - s.start_time for s in segments)
        
        # Check format compliance
        if extracted_sections != required_sections:
            errors.append(
                f"FORMAT_SECTION_MISMATCH: AI extracted {extracted_sections} "
                f"but format requires {required_sections}"
            )
            logger.error(
                f"Section count mismatch: {extracted_sections} vs {required_sections}"
            )
        
        # Determine compliance (no errors = compliant)
        compliant = len(errors) == 0
        
        format_compliance = FormatCompliance(
            required_sections=required_sections,
            extracted_sections=extracted_sections,
            compliant=compliant
        )
        
        logger.info(
            f"Transcript cutting complete: {len(segments)} segments, "
            f"{total_duration:.1f}s duration, "
            f"{'compliant' if compliant else 'non-compliant'}, "
            f"{len(errors)} errors, {len(warnings)} warnings"
        )
        
        # Combine errors and warnings
        all_warnings = errors + warnings
        
        return TranscriptCutResult(
            segments=segments,
            total_duration=total_duration,
            format_compliance=format_compliance,
            warnings=all_warnings
        )
    
    def _process_segment(
        self,
        ai_segment: Dict[str, Any],
        source_text: str,
        section_purposes: Dict[str, str]
    ) -> TranscriptSegment:
        """Process a single AI segment and validate word preservation.
        
        Args:
            ai_segment: AI-generated segment data
            source_text: Full source transcript text
            section_purposes: Map of section names to their purposes
            
        Returns:
            Validated TranscriptSegment
            
        Raises:
            ValueError: If ai_segment is None or missing required fields
        """
        if ai_segment is None:
            raise ValueError("ai_segment cannot be None")
        
        section_name = ai_segment.get("section_name", "")
        
        # Validate timestamps with error handling
        try:
            start_time = float(ai_segment.get("start_time", 0.0))
            end_time = float(ai_segment.get("end_time", 0.0))
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Invalid timestamp in segment '{section_name}': {e}"
            )
        
        # Extract and validate text
        text = ai_segment.get("text")
        if text is None:
            raise ValueError(f"text cannot be None in segment '{section_name}'")
        if not isinstance(text, str):
            raise ValueError(
                f"text must be a string in segment '{section_name}', got {type(text).__name__}"
            )
        
        # Extract narrative metadata
        narrative_tone = ai_segment.get("narrative_tone", "")
        narrative_purpose = ai_segment.get("narrative_purpose", "")
        
        # Use expected purpose if AI didn't provide one
        expected_purpose = section_purposes.get(section_name, "")
        if not narrative_purpose and expected_purpose:
            narrative_purpose = expected_purpose
        
        # Calculate word count
        word_count = len(text.split()) if text else 0
        
        # Create segment (validation happens in __post_init__)
        segment = TranscriptSegment(
            section_name=section_name,
            start_time=start_time,
            end_time=end_time,
            text=text,
            word_count=word_count,
            source_words_preserved=False,
            narrative_tone=narrative_tone,
            narrative_purpose=narrative_purpose
        )
        
        # Check if segment text exists verbatim in source
        segment.source_words_preserved = segment.validate_word_preservation(source_text)
        
        return segment
