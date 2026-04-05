"""Music matching engine for AI-powered asset selection.

Provides the MusicMatcher class for analyzing transcript segment tones
and matching appropriate music assets from the indexed library based
on contextual and emotional relevance.
"""

from __future__ import annotations

import logging
from typing import Any

from .music_match import (
    HIGH_CONFIDENCE_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
    MusicAsset,
    MusicMatch,
    MusicMatchingResult,
    SegmentMusicMatches
)
from .segment_tone import SegmentTone, TONE_TAG_MAPPINGS

logger = logging.getLogger(__name__)

# Default configuration constants
DEFAULT_MAX_SUGGESTIONS = 3
DEFAULT_MIN_CONFIDENCE = 0.60
DEFAULT_FUZZY_MATCH_WEIGHT = 0.7
DEFAULT_FOLDER_CONTEXT_WEIGHT = 0.15
DEFAULT_MULTIPLE_TAG_BONUS = 1.1
DEFAULT_FUZZY_MATCH_THRESHOLD = 3

# Maximum number of duplicate music IDs to track
MAX_USAGE_HISTORY_SIZE = 1000

# Minimum number of tags for multiple tag bonus
MIN_TAGS_FOR_BONUS = 3

# Folder context match cap to prevent score inflation
MAX_FOLDER_CONTEXT_MATCHES = 2


class MusicMatcher:
    """Matches music assets to transcript segments based on tone analysis.
    
    Analyzes the emotional tone of transcript segments and searches the
    indexed music library for contextually appropriate matches. Uses a
    scoring algorithm that considers tag relevance, folder context, and
    match quality. Tracks usage history to deprioritize recently used assets.
    
    Attributes:
        max_suggestions: Maximum number of suggestions per segment
        min_confidence_threshold: Minimum confidence for viable matches
        usage_history: Set of recently used music IDs to avoid repetition
        quality_indicators_enabled: Whether to populate file quality metadata
    """
    
    def __init__(
        self,
        max_suggestions: int = DEFAULT_MAX_SUGGESTIONS,
        min_confidence_threshold: float = DEFAULT_MIN_CONFIDENCE,
        track_usage_history: bool = True,
        quality_indicators_enabled: bool = False
    ):
        """Initialize the music matcher.
        
        Args:
            max_suggestions: Maximum matches to return per segment
            min_confidence_threshold: Minimum confidence for viable matches
            track_usage_history: Whether to track and deprioritize recently used assets
            quality_indicators_enabled: Whether to populate file quality metadata
        """
        self.max_suggestions = max_suggestions
        self.min_confidence_threshold = min_confidence_threshold
        self.track_usage_history = track_usage_history
        self.quality_indicators_enabled = quality_indicators_enabled
        self.usage_history: set[str] = set()  # Recently used music IDs
    
    def analyze_segment_tone(
        self,
        segment_text: str,
        segment_name: str,
        ai_tone_data: dict[str, Any] | None = None
    ) -> SegmentTone:
        """Analyze emotional tone of a transcript segment.
        
        Determines the energy level, mood, and genre hint for a segment
        based on its text content. Can use AI-provided tone data or
        infer from text analysis.
        
        Args:
            segment_text: The transcript segment text
            segment_name: Name of the segment (e.g., "intro", "narrative_1")
            ai_tone_data: Optional tone data from AI analysis
            
        Returns:
            SegmentTone with emotional analysis
            
        Raises:
            ValueError: If segment_text is empty or None
        """
        if not segment_text:
            raise ValueError("segment_text cannot be empty")
        
        # If AI provided tone data, use it
        if ai_tone_data and isinstance(ai_tone_data, dict):
            try:
                return SegmentTone.from_dict(ai_tone_data)
            except ValueError as e:
                logger.warning(f"Invalid AI tone data: {e}, inferring from text")
        
        # Infer tone from segment name and text
        return self._infer_tone_from_context(segment_text, segment_name)
    
    def _infer_tone_from_context(
        self,
        segment_text: str,
        segment_name: str
    ) -> SegmentTone:
        """Infer tone from segment name and text content.
        
        Uses heuristics based on segment naming conventions and
        keyword analysis to determine appropriate tone.
        
        Args:
            segment_text: The transcript segment text
            segment_name: Name of the segment
            
        Returns:
            Inferred SegmentTone
        """
        segment_lower = segment_name.lower()
        text_lower = segment_text.lower()
        
        # Default values
        energy = "medium"
        mood = "neutral"
        genre_hint = "ambient"
        keywords = []
        
        # Analyze by segment type
        if "intro" in segment_lower or "hook" in segment_lower:
            energy = "high"
            mood = "upbeat"
            genre_hint = "corporate"
            keywords = ["intro", "opening", "hook"]
        
        elif "outro" in segment_lower or "cta" in segment_lower:
            energy = "high"
            mood = "triumphant"
            genre_hint = "corporate"
            keywords = ["outro", "closing", "cta", "finale"]
        
        elif "narrative" in segment_lower or "main" in segment_lower:
            # Analyze text for mood
            if any(word in text_lower for word in ["challenge", "difficult", "struggle", "problem"]):
                energy = "medium"
                mood = "contemplative"
                genre_hint = "ambient"
                keywords = ["challenge", "contemplative", "thoughtful"]
            
            elif any(word in text_lower for word in ["success", "achieve", "win", "victory", "great"]):
                energy = "high"
                mood = "triumphant"
                genre_hint = "orchestral"
                keywords = ["triumphant", "victory", "success"]
            
            elif any(word in text_lower for word in ["explain", "discuss", "overview", "about"]):
                energy = "medium"
                mood = "neutral"
                genre_hint = "corporate"
                keywords = ["informative", "neutral", "business"]
            
            else:
                energy = "medium"
                mood = "contemplative"
                genre_hint = "ambient"
                keywords = ["narrative", "story"]
        
        # Text-based keyword extraction
        emotion_keywords = self._extract_emotion_keywords(text_lower)
        keywords.extend(emotion_keywords)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for k in keywords:
            if k.lower() not in seen:
                seen.add(k.lower())
                unique_keywords.append(k)
        
        return SegmentTone(
            energy=energy,
            mood=mood,
            genre_hint=genre_hint,
            keywords=unique_keywords[:10]  # Limit to 10 keywords
        )
    
    def _extract_emotion_keywords(self, text: str) -> list[str]:
        """Extract emotional keywords from text.
        
        Args:
            text: Lowercase text to analyze
            
        Returns:
            List of emotional keywords found
        """
        emotion_map = {
            "happy": ["happy", "joy", "delighted", "pleased", "excited"],
            "sad": ["sad", "unhappy", "disappointed", "regret", "sorry"],
            "angry": ["angry", "frustrated", "annoyed", "upset", "mad"],
            "fear": ["afraid", "scared", "worried", "anxious", "concern"],
            "surprise": ["surprised", "amazed", "shocked", "astonished"],
            "trust": ["trust", "confident", "believe", "sure", "certain"],
            "anticipation": ["expect", "hope", "looking forward", "await"],
        }
        
        found_keywords = []
        for emotion, words in emotion_map.items():
            if any(word in text for word in words):
                found_keywords.append(emotion)
        
        return found_keywords
    
    def match_music_to_segments(
        self,
        segments: list[dict[str, Any]],
        music_index: list[dict[str, Any]],
        segment_tones: list[SegmentTone] | None = None
    ) -> MusicMatchingResult:
        """Match music assets to transcript segments.
        
        Analyzes each segment's tone and searches the music library for
        appropriate matches based on tag relevance and context.
        
        Args:
            segments: List of transcript segment dictionaries
            music_index: List of music asset dictionaries from indexed library
            segment_tones: Optional pre-computed tone analyses
            
        Returns:
            MusicMatchingResult with all segment matches
            
        Raises:
            ValueError: If segments or music_index is empty
        """
        if not segments:
            raise ValueError("segments cannot be empty")
        if not music_index:
            raise ValueError("music_index cannot be empty")
        
        # Convert music index to MusicAsset objects
        music_assets = []
        for asset_data in music_index:
            try:
                asset = MusicAsset.from_dict(asset_data)
                music_assets.append(asset)
            except ValueError as e:
                logger.warning(f"Skipping invalid music asset: {e}")
        
        if not music_assets:
            raise ValueError("No valid music assets found in index")
        
        # Match music for each segment
        segment_matches_list = []
        warnings = []
        fallback_used = False
        
        for i, segment in enumerate(segments):
            segment_name = segment.get("section_name", f"segment_{i}")
            segment_text = segment.get("text", "")
            
            # Get or compute tone
            if segment_tones and i < len(segment_tones):
                tone = segment_tones[i]
            else:
                # Use AI tone data if available in segment
                ai_tone = segment.get("tone")
                tone = self.analyze_segment_tone(segment_text, segment_name, ai_tone)
            
            # Find matches for this segment
            matches, fallback = self._find_matches_for_segment(
                tone, music_assets, segment
            )
            
            # Track fallback usage
            if fallback:
                fallback_used = True
                warnings.append(
                    f"Segment '{segment_name}' used fallback music suggestion"
                )
            
            # Check for low confidence
            if not matches or all(m.confidence_score < LOW_CONFIDENCE_THRESHOLD for m in matches):
                warnings.append(
                    f"Low confidence matches for segment '{segment_name}'"
                )
            
            # Create segment matches object
            segment_matches = SegmentMusicMatches(
                segment_name=segment_name,
                segment_tone=tone,
                matches=matches[:self.max_suggestions],  # Limit to max_suggestions
                fallback_suggestion=fallback
            )
            
            segment_matches_list.append(segment_matches)
        
        # Calculate statistics
        total_matches = sum(len(sm.matches) for sm in segment_matches_list)
        all_confidences = [
            m.confidence_score 
            for sm in segment_matches_list 
            for m in sm.matches
        ]
        average_confidence = (
            sum(all_confidences) / len(all_confidences) 
            if all_confidences else 0.0
        )
        
        return MusicMatchingResult(
            segment_matches=segment_matches_list,
            total_matches=total_matches,
            average_confidence=average_confidence,
            fallback_used=fallback_used,
            warnings=warnings
        )
    
    def _find_matches_for_segment(
        self,
        tone: SegmentTone,
        music_assets: list[MusicAsset],
        segment: dict[str, Any]
    ) -> tuple[list[MusicMatch], MusicMatch | None]:
        """Find music matches for a single segment.
        
        Args:
            tone: Tone analysis for the segment
            music_assets: Available music assets
            segment: Segment data with timing info
            
        Returns:
            Tuple of (matches list, fallback suggestion or None)
        """
        # Get search tags from tone
        search_tags = tone.to_tag_query()
        
        # Score all assets
        scored_assets = []
        for asset in music_assets:
            base_score, matched_tags = self._calculate_match_score(tone, asset, search_tags)
            # Apply usage penalty if asset was recently used
            adjusted_score = self._apply_usage_penalty(asset.music_id, base_score)
            scored_assets.append((asset, adjusted_score, matched_tags))
        
        # Sort by score
        scored_assets.sort(key=lambda x: x[1], reverse=True)
        
        # Create MusicMatch objects
        matches = []
        segment_start = segment.get("start_time", 0.0)
        segment_end = segment.get("end_time", 0.0)
        
        for asset, score, matched_tags in scored_assets:
            if score >= self.min_confidence_threshold:
                match_reason = self._generate_match_reason(tone, asset, matched_tags, score)
                
                music_match = MusicMatch(
                    music_id=asset.music_id,
                    file_path=asset.file_path,
                    file_name=asset.get_file_name(),
                    folder_context=asset.folder_context,
                    match_reason=match_reason,
                    confidence_score=score,
                    matched_tags=matched_tags,
                    suggested_start=segment_start,
                    suggested_end=segment_end
                )
                
                matches.append(music_match)
        
        # Determine fallback if no good matches
        fallback = None
        if not matches or all(m.confidence_score < LOW_CONFIDENCE_THRESHOLD for m in matches):
            if scored_assets:
                # Use highest scored asset as fallback
                best_asset, score, matched_tags = scored_assets[0]
                match_reason = f"Fallback: Best available match (score: {score:.2f})"
                
                fallback = MusicMatch(
                    music_id=best_asset.music_id,
                    file_path=best_asset.file_path,
                    file_name=best_asset.get_file_name(),
                    folder_context=best_asset.folder_context,
                    match_reason=match_reason,
                    confidence_score=max(score * 0.8, 0.4),  # Reduce confidence for fallback
                    matched_tags=matched_tags,
                    suggested_start=segment_start,
                    suggested_end=segment_end
                )
        
        return matches, fallback
    
    def _calculate_match_score(
        self,
        tone: SegmentTone,
        asset: MusicAsset,
        search_tags: list[str]
    ) -> tuple[float, list[str]]:
        """Calculate match score between tone and asset.
        
        Args:
            tone: Segment tone analysis
            asset: Music asset to score
            search_tags: Tags to match against
            
        Returns:
            Tuple of (confidence_score, matched_tags)
        """
        if not search_tags or not asset.tags:
            return 0.0, []
        
        asset_tags_lower = [t.casefold() for t in asset.tags]
        matched_tags = []
        total_weight = 0.0
        max_possible = 0.0
        
        # Score each search tag
        for i, tag in enumerate(search_tags):
            tag_lower = tag.casefold()
            # Weight decreases by position (first tags are higher priority)
            weight = 1.0 - (i * 0.1) if i < 10 else 0.1
            max_possible += weight
            
            # Check for exact match
            if tag_lower in asset_tags_lower:
                matched_tags.append(tag)
                total_weight += weight
            else:
                # Check for partial match (tag contains search term or vice versa)
                for asset_tag in asset_tags_lower:
                    if tag_lower in asset_tag or asset_tag in tag_lower:
                        matched_tags.append(tag)
                        total_weight += weight * DEFAULT_FUZZY_MATCH_WEIGHT  # Partial match weight
                        break
        
        # Folder context bonus (capped to prevent score inflation)
        if asset.folder_context:
            folder_lower = asset.folder_context.casefold()
            context_matches = min(
                sum(1 for tag in search_tags if tag.casefold() in folder_lower),
                MAX_FOLDER_CONTEXT_MATCHES
            )
            if context_matches > 0:
                total_weight += context_matches * DEFAULT_FOLDER_CONTEXT_WEIGHT
                max_possible += context_matches * DEFAULT_FOLDER_CONTEXT_WEIGHT
        
        # Calculate confidence score
        if max_possible > 0:
            confidence = total_weight / max_possible
        else:
            confidence = 0.0
        
        # Boost based on number of matches (encourages multi-tag matches)
        if len(matched_tags) >= MIN_TAGS_FOR_BONUS:
            confidence = min(confidence * DEFAULT_MULTIPLE_TAG_BONUS, 1.0)
        
        # Remove duplicate matched tags
        seen = set()
        unique_matched = []
        for tag in matched_tags:
            if tag.lower() not in seen:
                seen.add(tag.lower())
                unique_matched.append(tag)
        
        return confidence, unique_matched
    
    def _generate_match_reason(
        self,
        tone: SegmentTone,
        asset: MusicAsset,
        matched_tags: list[str],
        score: float
    ) -> str:
        """Generate human-readable match reason.
        
        Args:
            tone: Segment tone
            asset: Matched asset
            matched_tags: Tags that contributed to match
            score: Confidence score
            
        Returns:
            Human-readable match explanation
        """
        tags_str = "'" + "', '".join(matched_tags[:3]) + "'" if matched_tags else "context"
        
        if score >= HIGH_CONFIDENCE_THRESHOLD:
            return (
                f"Tags {tags_str} strongly match segment tone "
                f"({tone.energy} energy, {tone.mood} mood)"
            )
        elif score >= LOW_CONFIDENCE_THRESHOLD:
            return (
                f"Tags {tags_str} moderately match segment tone "
                f"({tone.energy} energy, {tone.mood} mood)"
            )
        else:
            return (
                f"Limited match: tags {tags_str} partially align with "
                f"segment {tone.mood} mood"
            )
    
    def get_used_music_ids(self, result: MusicMatchingResult) -> set[str]:
        """Get set of all music IDs used in matches.
        
        Useful for preventing duplicate suggestions across segments
        and tracking asset usage.
        
        Args:
            result: Music matching result
            
        Returns:
            Set of music_id strings
        """
        used_ids = set()
        for sm in result.segment_matches:
            for match in sm.matches:
                used_ids.add(match.music_id)
            if sm.fallback_suggestion:
                used_ids.add(sm.fallback_suggestion.music_id)
        return used_ids
    
    def prevent_duplicate_matches(
        self,
        result: MusicMatchingResult,
        prefer_high_confidence: bool = True
    ) -> MusicMatchingResult:
        """Remove duplicate music suggestions across segments.
        
        When the same music asset is suggested for multiple segments,
        this method keeps it only for the segment where it's most
        appropriate (highest confidence or first occurrence).
        
        Args:
            result: Original matching result
            prefer_high_confidence: If True, keep for highest confidence segment
            
        Returns:
            Modified result with duplicates removed
        """
        seen_ids = {}  # music_id -> (segment_index, confidence)
        
        for i, sm in enumerate(result.segment_matches):
            for match in sm.matches:
                mid = match.music_id
                if mid in seen_ids:
                    existing_conf = seen_ids[mid][1]
                    if prefer_high_confidence and match.confidence_score > existing_conf:
                        seen_ids[mid] = (i, match.confidence_score)
                else:
                    seen_ids[mid] = (i, match.confidence_score)
        
        # Filter matches
        for i, sm in enumerate(result.segment_matches):
            sm.matches = [
                m for m in sm.matches 
                if seen_ids.get(m.music_id, (None, 0))[0] == i
            ]
        
        # Recalculate statistics
        result.total_matches = sum(len(sm.matches) for sm in result.segment_matches)
        all_confidences = [
            m.confidence_score 
            for sm in result.segment_matches 
            for m in sm.matches
        ]
        if all_confidences:
            result.average_confidence = sum(all_confidences) / len(all_confidences)
        else:
            result.average_confidence = 0.0
        
        return result
    
    def record_usage(self, music_id: str) -> None:
        """Record that a music asset was used.
        
        Adds the music ID to usage history to deprioritize it in future
        matches. Maintains a maximum history size to prevent memory bloat.
        
        Args:
            music_id: ID of the music asset that was used
        """
        if not self.track_usage_history or not music_id:
            return
        
        self.usage_history.add(music_id)
        
        # Trim history if it exceeds max size
        if len(self.usage_history) > MAX_USAGE_HISTORY_SIZE:
            # Remove oldest entries (arbitrary since set is unordered)
            excess = len(self.usage_history) - MAX_USAGE_HISTORY_SIZE
            for _ in range(excess):
                if self.usage_history:
                    self.usage_history.pop()
    
    def is_recently_used(self, music_id: str) -> bool:
        """Check if a music asset was recently used.
        
        Args:
            music_id: ID of the music asset to check
            
        Returns:
            True if the asset is in usage history
        """
        return music_id in self.usage_history if self.track_usage_history else False
    
    def clear_usage_history(self) -> None:
        """Clear the usage history.
        
        Useful when starting a new project or when user wants to
        reset the "recently used" tracking.
        """
        self.usage_history.clear()
    
    def _apply_usage_penalty(self, music_id: str, base_score: float) -> float:
        """Apply penalty to score for recently used assets.
        
        Reduces the confidence score for assets that have been recently
        used, encouraging variety in music selection.
        
        Args:
            music_id: ID of the music asset
            base_score: Original confidence score
            
        Returns:
            Adjusted confidence score with penalty applied
        """
        if not self.track_usage_history or not self.is_recently_used(music_id):
            return base_score
        
        # Apply 15% penalty for recently used assets
        return base_score * 0.85
    
    def populate_quality_indicators(self, file_path: str) -> dict[str, Any]:
        """Populate file quality indicators for a music asset.
        
        Analyzes the audio file to extract quality metadata like
        bitrate, sample rate, and duration. Currently returns empty
        dict as placeholder - implement with audio analysis library
        for production use.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary with quality indicators (bitrate, sample_rate, etc.)
        """
        if not self.quality_indicators_enabled:
            return {}
        
        # TODO: Implement actual audio file analysis
        # This would use a library like pydub, soundfile, or mutagen
        # to extract actual file metadata
        
        # Placeholder implementation - return empty dict
        # Production implementation should extract:
        # - bitrate (kbps)
        # - sample_rate (Hz)
        # - channels (mono/stereo)
        # - duration (seconds)
        # - file_format (wav, mp3, etc.)
        
        return {}
    
    def check_thematic_consistency(
        self,
        result: MusicMatchingResult
    ) -> list[str]:
        """Check thematic consistency across segments.
        
        Analyzes the selected music matches to ensure cohesive
        musical themes across related segments (e.g., intro/outro
        should have similar energy levels).
        
        Args:
            result: Music matching result to analyze
            
        Returns:
            List of consistency warnings or empty list if consistent
        """
        warnings: list[str] = []
        
        if not result.segment_matches:
            return warnings
        
        # Get top matches for each segment
        top_matches: dict[str, MusicMatch | None] = {}
        for sm in result.segment_matches:
            top_matches[sm.segment_name] = sm.top_match()
        
        # Check intro/outro energy consistency
        intro_match = top_matches.get("intro")
        outro_match = top_matches.get("outro") or top_matches.get("cta")
        
        if intro_match and outro_match:
            # Check if energies are compatible
            # Both should be high energy for cohesive bookends
            # or both should be calm for gentle framing
            intro_conf = intro_match.confidence_score
            outro_conf = outro_match.confidence_score
            
            # Large confidence gap suggests thematic inconsistency
            if abs(intro_conf - outro_conf) > 0.3:
                warnings.append(
                    "Intro and outro music have significantly different match confidence levels"
                )
        
        # Check for abrupt mood transitions between adjacent segments
        segment_order = [sm.segment_name for sm in result.segment_matches]
        for i in range(len(segment_order) - 1):
            curr_name = segment_order[i]
            next_name = segment_order[i + 1]
            
            curr_match = top_matches.get(curr_name)
            next_match = top_matches.get(next_name)
            
            if curr_match and next_match:
                # Check if same music is used for multiple segments
                # This could be good (continuity) or bad (repetitive)
                if curr_match.music_id == next_match.music_id:
                    # Check if segments are far apart in timeline
                    if abs(curr_match.suggested_end - next_match.suggested_start) > 60:
                        # Gap of > 60 seconds suggests intentional reuse
                        pass  # This is acceptable - music bed approach
                    else:
                        warnings.append(
                            f"Same music used for adjacent segments '{curr_name}' and '{next_name}'"
                        )
        
        return warnings
