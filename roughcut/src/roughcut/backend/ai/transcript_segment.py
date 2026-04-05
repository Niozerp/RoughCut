"""Transcript segment data structures for AI cutting operations.

Provides dataclasses for representing transcript segments, format compliance,
and cutting results with validation for word preservation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TranscriptSegment:
    """A segment of transcript cut by AI.
    
    Represents a single segment of transcript that has been cut by the AI
    to match a specific format section. Includes validation for ensuring
    words are preserved verbatim from the source transcript.
    
    Attributes:
        section_name: Maps to format section (intro, narrative_1, etc.)
        start_time: Start timestamp in seconds
        end_time: End timestamp in seconds
        text: Verbatim text from source transcript
        word_count: Number of words in segment
        source_words_preserved: True if no modifications detected
        narrative_tone: Optional tone descriptor (e.g., "upbeat", "contemplative")
        narrative_purpose: Optional purpose (e.g., "hook", "main_content", "cta")
    """
    section_name: str
    start_time: float
    end_time: float
    text: str
    word_count: int
    source_words_preserved: bool = False
    narrative_tone: str = ""
    narrative_purpose: str = ""
    
    def __post_init__(self):
        """Validate segment fields after initialization."""
        if self.start_time < 0:
            raise ValueError(f"start_time cannot be negative: {self.start_time}")
        if self.end_time < 0:
            raise ValueError(f"end_time cannot be negative: {self.end_time}")
        if self.end_time <= self.start_time:
            raise ValueError(
                f"end_time ({self.end_time}) must be greater than start_time ({self.start_time}) "
                f"- zero-duration segments are not allowed"
            )
        if self.word_count < 0:
            raise ValueError(f"word_count cannot be negative: {self.word_count}")
        if self.text is None:
            raise ValueError("text cannot be None")
    
    def validate_word_preservation(self, source_text: str) -> bool:
        """Verify segment text exists verbatim in source.
        
        Checks that the segment text appears exactly as-is in the source
        transcript, ensuring no AI modification or paraphrasing occurred.
        Uses exact character matching (case-sensitive).
        
        Args:
            source_text: Full source transcript text
            
        Returns:
            True if segment text found verbatim in source, False otherwise
        """
        if not source_text or not self.text:
            return False
        
        # Normalize whitespace only (preserve case for exact matching)
        # This ensures we detect case changes, word insertions, and deletions
        normalized_segment = " ".join(self.text.split())
        normalized_source = " ".join(source_text.split())
        
        # Check if segment text appears verbatim in source
        # Case-sensitive exact substring match
        return normalized_segment in normalized_source
    
    def format_timestamp(self, seconds: float) -> str:
        """Format seconds as MM:SS or HH:MM:SS.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        if seconds < 0:
            return "0:00"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    def format_marker(self, section_number: int) -> str:
        """Format segment as human-readable marker string.
        
        Args:
            section_number: Section index (1-based)
            
        Returns:
            Formatted marker like "Section 1: 0:15-1:45 (45 words)"
        """
        start_formatted = self.format_timestamp(self.start_time)
        end_formatted = self.format_timestamp(self.end_time)
        return f"Section {section_number}: {start_formatted}-{end_formatted} ({self.word_count} words)"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of segment
        """
        return {
            "section_name": self.section_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text,
            "word_count": self.word_count,
            "source_words_preserved": self.source_words_preserved,
            "narrative_tone": self.narrative_tone,
            "narrative_purpose": self.narrative_purpose
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptSegment":
        """Create from dictionary.
        
        Args:
            data: Dictionary with segment data
            
        Returns:
            TranscriptSegment instance
            
        Raises:
            ValueError: If data is None, not a dict, or has invalid field types
        """
        if data is None:
            raise ValueError("data cannot be None")
        if not isinstance(data, dict):
            raise ValueError(f"data must be a dictionary, got {type(data).__name__}")
        
        try:
            start_time = float(data.get("start_time", 0.0))
            end_time = float(data.get("end_time", 0.0))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid timestamp value in data: {e}")
        
        try:
            word_count = int(data.get("word_count", 0))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid word_count value in data: {e}")
        
        return cls(
            section_name=data.get("section_name", ""),
            start_time=start_time,
            end_time=end_time,
            text=data.get("text", ""),
            word_count=word_count,
            source_words_preserved=bool(data.get("source_words_preserved", False)),
            narrative_tone=data.get("narrative_tone", ""),
            narrative_purpose=data.get("narrative_purpose", "")
        )


@dataclass
class FormatCompliance:
    """Format compliance result for transcript cutting.
    
    Tracks whether the AI-extracted segments match the required
    format structure and section count.
    
    Attributes:
        required_sections: Number of sections required by format
        extracted_sections: Number of sections actually extracted by AI
        compliant: True if counts match and requirements satisfied
    """
    required_sections: int
    extracted_sections: int
    compliant: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            "required_sections": self.required_sections,
            "extracted_sections": self.extracted_sections,
            "compliant": self.compliant
        }


@dataclass
class TranscriptCutResult:
    """Result of AI transcript cutting operation.
    
    Contains all extracted segments, compliance information,
    and any warnings generated during processing.
    
    Attributes:
        segments: List of extracted transcript segments
        total_duration: Total duration of all segments in seconds
        format_compliance: Compliance information for format requirements
        warnings: List of non-fatal issues (e.g., short segments, modifications)
    """
    segments: List[TranscriptSegment]
    total_duration: float
    format_compliance: FormatCompliance
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            "segments": [s.to_dict() for s in self.segments],
            "total_duration": self.total_duration,
            "format_compliance": self.format_compliance.to_dict(),
            "warnings": self.warnings
        }
