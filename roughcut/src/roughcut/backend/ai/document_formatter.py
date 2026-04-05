"""Document formatter for rough cut display and visualization.

Provides formatting utilities for converting rough cut documents into
human-readable formats suitable for UI display.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from .document_models import (
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
    AssetSuggestion,
    AssetType,
    ConfidenceLevel,
    DocumentValidationResult,
    MusicSuggestion,
    RoughCutDocument,
    RoughCutSection,
    SFXSuggestion,
    TranscriptSegment,
    VFXSuggestion,
)


# Gap threshold in seconds for detecting large gaps between sections
GAP_THRESHOLD_SECONDS = 5.0


class DocumentFormatter:
    """Formatter for rough cut documents.
    
    Provides methods to format rough cut documents for display,
    including ASCII timeline visualization and section summaries.
    """
    
    def __init__(self, document: RoughCutDocument):
        """Initialize formatter with document.
        
        Args:
            document: The rough cut document to format
        """
        self.document = document
    
    def format_document_summary(self) -> str:
        """Format document summary for display.
        
        Returns:
            Multi-line string with document summary
        """
        lines = [
            f"Rough Cut: {self.document.title}",
            f"Source: {self.document.source_clip}",
            f"Format: {self.document.format_template}",
            f"Duration: {self.document.format_total_duration()}",
            "",
            "Sections:",
            f"  {self.document.section_count} format sections",
            f"  {self.document.total_transcript_segments} transcript segments",
            "",
            "Asset Suggestions:",
            f"  Music: {self.document.total_music_suggestions} suggestions",
            f"  SFX: {self.document.total_sfx_suggestions} suggestions",
            f"  VFX: {self.document.total_vfx_suggestions} suggestions",
        ]
        
        if self.document.assembly_metadata:
            lines.extend([
                "",
                "Assembly Info:",
                f"  Confidence: {self.document.assembly_metadata.get('pacing_consistency_score', 'N/A')}"
            ])
        
        return "\n".join(lines)
    
    def format_section(self, section: RoughCutSection, index: int) -> str:
        """Format a single section for display.
        
        Args:
            section: The section to format
            index: Section index (0-based)
            
        Returns:
            Multi-line string with section details
        """
        lines = [
            f"\n{'=' * 60}",
            f"Section {index + 1}: {section.name.upper()}",
            f"Time: {section.format_time_range()} (Duration: {self._format_duration(section.duration)})",
            "",
        ]
        
        # Transcript
        if section.transcript_segments:
            lines.append("TRANSCRIPT:")
            for seg in section.transcript_segments:
                lines.extend(self._format_transcript_segment(seg))
            lines.append("")
        
        # Music
        if section.music:
            lines.append("MUSIC:")
            lines.extend(self._format_music_suggestion(section.music))
            lines.append("")
        
        # SFX
        if section.sfx:
            lines.append("SFX:")
            for sfx in section.sfx:
                lines.extend(self._format_sfx_suggestion(sfx))
            lines.append("")
        
        # VFX
        if section.vfx:
            lines.append("VFX:")
            for vfx in section.vfx:
                lines.extend(self._format_vfx_suggestion(vfx))
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_transcript_segment(self, segment: TranscriptSegment) -> list[str]:
        """Format a transcript segment.
        
        Args:
            segment: The transcript segment
            
        Returns:
            List of formatted lines
        """
        time_str = f"[{segment.format_timestamp()}]"
        speaker_str = f"<{segment.speaker}> " if segment.speaker else ""
        
        # Wrap text at 70 characters
        wrapped_text = self._wrap_text(f"{speaker_str}{segment.text}", 70, len(time_str) + 1)
        
        lines = [f"  {time_str} {wrapped_text[0]}"]
        for line in wrapped_text[1:]:
            lines.append(f"  {' ' * len(time_str)} {line}")
        
        return lines
    
    def _format_music_suggestion(self, music: MusicSuggestion) -> list[str]:
        """Format a music suggestion.
        
        Args:
            music: The music suggestion
            
        Returns:
            List of formatted lines
        """
        lines = [
            f"  Track: {music.name}",
            f"  Source: {music.source_folder}",
            f"  Position: {music.format_position()}",
            f"  Confidence: {self._format_confidence(music.confidence)} ({music.confidence:.0%})",
            f"  Reasoning: {music.reasoning}",
        ]
        
        if music.fade_in:
            lines.append(f"  Fade In: {music.fade_in}s")
        if music.fade_out:
            lines.append(f"  Fade Out: {music.fade_out}s")
        if music.volume_adjustment != 0.0:
            lines.append(f"  Volume: {music.volume_adjustment:+.1f} dB")
        
        return lines
    
    def _format_sfx_suggestion(self, sfx: SFXSuggestion) -> list[str]:
        """Format an SFX suggestion.
        
        Args:
            sfx: The SFX suggestion
            
        Returns:
            List of formatted lines
        """
        lines = [
            f"  • {sfx.name}",
            f"    Position: {sfx.format_position()}",
            f"    Track: SFX {sfx.track_number}",
            f"    Confidence: {self._format_confidence(sfx.confidence)} ({sfx.confidence:.0%})",
        ]
        
        if sfx.intended_moment:
            lines.append(f"    Moment: {sfx.intended_moment}")
        
        return lines
    
    def _format_vfx_suggestion(self, vfx: VFXSuggestion) -> list[str]:
        """Format a VFX suggestion.
        
        Args:
            vfx: The VFX suggestion
            
        Returns:
            List of formatted lines
        """
        lines = [
            f"  • {vfx.template_name or vfx.name}",
            f"    Position: {vfx.format_position()}",
            f"    Confidence: {self._format_confidence(vfx.confidence)} ({vfx.confidence:.0%})",
        ]
        
        if vfx.duration:
            lines.append(f"    Duration: {self._format_duration(vfx.duration)}")
        
        if vfx.configurable_params:
            lines.append("    Parameters:")
            for key, value in vfx.configurable_params.items():
                lines.append(f"      {key}: {value}")
        
        return lines
    
    def format_timeline_ascii(self, width: int = 80) -> str:
        """Create ASCII timeline visualization.
        
        Args:
            width: Width of timeline in characters
            
        Returns:
            ASCII art timeline string
        """
        if not self.document.sections:
            return "No sections to display"
        
        total_duration = self.document.total_duration
        if total_duration == 0:
            return "Zero duration document"
        
        lines = [
            "Timeline Overview:",
            "",
            self._create_timeline_ruler(width, total_duration),
            "",
        ]
        
        # Section bars
        for i, section in enumerate(self.document.sections):
            lines.append(self._create_section_bar(section, i, width, total_duration))
        
        lines.extend([
            "",
            "Legend: [==Section Name==]  •SFX  ▼VFX  ♫Music",
        ])
        
        return "\n".join(lines)
    
    def _create_timeline_ruler(self, width: int, total_duration: float) -> str:
        """Create timeline ruler with time markers.
        
        Args:
            width: Width of ruler
            total_duration: Total duration in seconds
            
        Returns:
            Formatted ruler string
        """
        # Create main timeline bar
        ruler = "0:00 " + "-" * (width - 10) + " " + self._format_duration(total_duration)
        
        # Add intermediate markers
        markers = []
        for i in range(1, 5):  # Add 4 intermediate markers
            position = (total_duration * i) / 5
            markers.append(self._format_duration(position))
        
        # Build marker line
        marker_line = "     "
        marker_positions = [width // 5 * i for i in range(1, 5)]
        current_pos = 5
        
        for pos, marker in zip(marker_positions, markers):
            spaces = pos - current_pos - len(marker)
            if spaces > 0:
                marker_line += " " * spaces + marker
                current_pos = pos
        
        return ruler + "\n" + marker_line
    
    def _create_section_bar(
        self, 
        section: RoughCutSection, 
        index: int, 
        width: int, 
        total_duration: float
    ) -> str:
        """Create a visual bar for a section.
        
        Args:
            section: The section to represent
            index: Section index
            width: Total width available
            total_duration: Total document duration
            
        Returns:
            ASCII bar string
        """
        # Calculate positions
        start_pct = section.start_time / total_duration
        end_pct = section.end_time / total_duration
        
        start_pos = int(start_pct * (width - 10)) + 5
        end_pos = int(end_pct * (width - 10)) + 5
        
        # Build the bar
        bar_width = max(3, end_pos - start_pos)
        section_name = section.name[:bar_width - 2].center(bar_width - 2)
        bar = f"[{section_name}]"
        
        # Add asset markers
        if section.sfx:
            bar = self._add_markers_to_bar(bar, section.sfx, width, total_duration, "•")
        if section.vfx:
            bar = self._add_markers_to_bar(bar, section.vfx, width, total_duration, "▼")
        
        # Assemble full line
        prefix = "     "
        line = prefix
        line += " " * (start_pos - len(prefix))
        line += bar
        
        return line
    
    def _add_markers_to_bar(
        self, 
        bar: str, 
        assets: list[AssetSuggestion], 
        width: int, 
        total_duration: float,
        marker: str
    ) -> str:
        """Add asset markers to section bar.
        
        Args:
            bar: Current bar string
            assets: List of assets to mark
            width: Total width
            total_duration: Document duration
            marker: Marker character
            
        Returns:
            Bar with markers added
        """
        # For simplicity, just append indicator to bar
        if assets:
            return bar[:-1] + marker + "]"
        return bar
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration as MM:SS.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        mins, secs = divmod(int(seconds), 60)
        return f"{mins}:{secs:02d}"
    
    def _format_confidence(self, confidence: float) -> str:
        """Format confidence as text indicator.
        
        Args:
            confidence: Confidence score 0.0-1.0
            
        Returns:
            Text representation (e.g., "HIGH ✓")
        """
        if confidence >= HIGH_CONFIDENCE_THRESHOLD:
            return "HIGH ✓"
        elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            return "MEDIUM ~"
        return "LOW ✗"
    
    def _wrap_text(self, text: str, width: int, indent: int = 0) -> list[str]:
        """Wrap text to specified width.
        
        Args:
            text: Text to wrap
            width: Maximum line width
            indent: Number of spaces to indent continuation lines
            
        Returns:
            List of wrapped lines
        """
        # Handle empty or whitespace-only input
        if not text or not text.strip():
            return [""] if not text else [text]
        
        text = text.strip()
        
        if len(text) <= width:
            return [text]
        
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            if len(current_line) + len(word) + 1 <= width:
                current_line += " " + word if current_line else word
            else:
                lines.append(current_line)
                current_line = " " * indent + word
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [text]
    
    def format_for_json(self) -> dict[str, Any]:
        """Format document for JSON serialization.
        
        Returns:
            Dictionary suitable for JSON serialization
        """
        return self.document.to_dict()
    
    def format_section_summary(self, section: RoughCutSection, index: int) -> str:
        """Format brief section summary.
        
        Args:
            section: Section to summarize
            index: Section index
            
        Returns:
            Single-line summary string
        """
        parts = [
            f"{index + 1}. {section.name}",
            f"({section.format_time_range()})",
        ]
        
        # Add asset counts
        assets = []
        if section.music:
            assets.append("♫")
        if section.sfx:
            assets.append(f"{len(section.sfx)}•")
        if section.vfx:
            assets.append(f"{len(section.vfx)}▼")
        
        if assets:
            parts.append("[" + " ".join(assets) + "]")
        
        parts.append(f"{len(section.transcript_segments)} segments")
        
        return " ".join(parts)
    
    def get_all_formatted_sections(self) -> list[str]:
        """Get all sections formatted for display.
        
        Returns:
            List of formatted section strings
        """
        return [
            self.format_section(section, i) 
            for i, section in enumerate(self.document.sections)
        ]


def format_rough_cut_document(document: RoughCutDocument, format_type: str = "full") -> str:
    """Convenience function to format a rough cut document.
    
    Args:
        document: Document to format
        format_type: Output format - "full", "summary", "timeline"
        
    Returns:
        Formatted string
        
    Raises:
        ValueError: If format_type is invalid
    """
    formatter = DocumentFormatter(document)
    
    if format_type == "full":
        parts = [
            formatter.format_document_summary(),
            formatter.format_timeline_ascii(),
        ]
        parts.extend(formatter.get_all_formatted_sections())
        return "\n".join(parts)
    
    elif format_type == "summary":
        lines = [
            formatter.format_document_summary(),
            "",
            "Sections:",
        ]
        for i, section in enumerate(document.sections):
            lines.append(formatter.format_section_summary(section, i))
        return "\n".join(lines)
    
    elif format_type == "timeline":
        return formatter.format_timeline_ascii()
    
    else:
        raise ValueError(f"Unknown format_type: {format_type}. Use 'full', 'summary', or 'timeline'")


class DocumentValidator:
    """Validator for rough cut documents.
    
    Provides validation of document completeness and asset availability.
    """
    
    def __init__(self, document: RoughCutDocument):
        """Initialize validator.
        
        Args:
            document: Document to validate
        """
        self.document = document
    
    def validate(self, check_assets: bool = False) -> DocumentValidationResult:
        """Validate the document.
        
        Args:
            check_assets: Whether to check if asset files exist
            
        Returns:
            DocumentValidationResult with validation details
        """
        errors = []
        warnings = []
        missing_assets = []
        
        # Check document has sections
        if not self.document.sections:
            errors.append("Document has no sections")
        
        # Check each section
        for i, section in enumerate(self.document.sections):
            section_prefix = f"Section {i + 1} ({section.name}): "
            
            # Check section has transcript segments
            if not section.transcript_segments:
                warnings.append(f"{section_prefix}No transcript segments")
            
            # Check section timing
            if section.start_time >= section.end_time:
                errors.append(f"{section_prefix}Invalid timing (start >= end)")
            
            # Check for gaps between sections
            if i > 0:
                prev_section = self.document.sections[i - 1]
                gap = section.start_time - prev_section.end_time
                if gap > GAP_THRESHOLD_SECONDS:
                    warnings.append(f"{section_prefix}Large gap from previous section ({gap:.1f}s)")
        
        # Check total duration consistency
        if self.document.sections:
            last_section = self.document.sections[-1]
            expected_duration = last_section.end_time
            if abs(self.document.total_duration - expected_duration) > 1.0:
                warnings.append(
                    f"Total duration mismatch: document={self.document.total_duration:.1f}s, "
                    f"calculated={expected_duration:.1f}s"
                )
        
        # Check assets if requested
        if check_assets:
            missing_assets = self._check_asset_paths()
            if missing_assets:
                errors.append(f"Missing assets: {len(missing_assets)} files not found")
        
        # Check for duplicate assets
        asset_paths = self.document.get_all_asset_paths()
        seen_paths = set()
        duplicates = []
        for path in asset_paths:
            if path in seen_paths:
                duplicates.append(path)
            seen_paths.add(path)
        
        if duplicates:
            warnings.append(f"Duplicate assets found: {len(duplicates)} files used multiple times")
        
        # Determine validity
        is_valid = len(errors) == 0
        
        return DocumentValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            missing_assets=missing_assets
        )
    
    def _check_asset_paths(self) -> list[str]:
        """Check if all asset paths exist.
        
        Returns:
            List of missing asset paths
        """
        missing = []
        asset_paths = self.document.get_all_asset_paths()
        
        for path in asset_paths:
            if not os.path.exists(path):
                missing.append(path)
        
        return missing
    
    def is_empty(self) -> bool:
        """Check if document is empty (no suggestions).
        
        Returns:
            True if document has no asset suggestions
        """
        return (
            self.document.total_music_suggestions == 0
            and self.document.total_sfx_suggestions == 0
            and self.document.total_vfx_suggestions == 0
        )
    
    def has_low_confidence_matches(self, threshold: float = 0.6) -> list[tuple[str, str, float]]:
        """Find all matches below confidence threshold.
        
        Args:
            threshold: Confidence threshold (default 0.6)
            
        Returns:
            List of (section_name, asset_name, confidence) tuples
        """
        low_confidence = []
        
        for section in self.document.sections:
            if section.music and section.music.confidence < threshold:
                low_confidence.append((section.name, section.music.name, section.music.confidence))
            
            for sfx in section.sfx:
                if sfx.confidence < threshold:
                    low_confidence.append((section.name, sfx.name, sfx.confidence))
            
            for vfx in section.vfx:
                if vfx.confidence < threshold:
                    low_confidence.append((section.name, vfx.name, vfx.confidence))
        
        return low_confidence
