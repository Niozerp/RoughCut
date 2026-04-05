"""SFX matching engine for AI-powered asset selection.

Provides the SFXMatcher class for identifying key moments in transcript
segments and matching appropriate sound effects from the indexed library
based on contextual and emotional relevance with subtlety scoring.
"""

from __future__ import annotations

import logging
from typing import Any

from .sfx_match import (
    HIGH_CONFIDENCE_THRESHOLD,
    HIGH_SUBTLETY_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
    SFXAsset,
    SFXMatch,
    SFXMatchingResult,
    MomentSFXMatches
)
from .sfx_moment import SFXMoment, SFX_MOMENT_MAPPINGS, INTENSITY_SUBTLETY_PREFERENCE

logger = logging.getLogger(__name__)

# Default configuration constants
DEFAULT_MAX_SUGGESTIONS = 3
DEFAULT_MIN_CONFIDENCE = 0.60
DEFAULT_FUZZY_MATCH_WEIGHT = 0.7
DEFAULT_FOLDER_CONTEXT_WEIGHT = 0.15
DEFAULT_MULTIPLE_TAG_BONUS = 1.1
DEFAULT_FUZZY_MATCH_THRESHOLD = 3
DEFAULT_DURATION_SUBTLETY_WEIGHT = 0.3

# Duration thresholds for subtlety (in milliseconds)
SHORT_DURATION_MS = 2000  # < 2s considered subtle
MEDIUM_DURATION_MS = 5000  # 2-5s moderate
LONG_DURATION_MS = 10000  # > 10s considered long

# Maximum number of duplicate SFX IDs to track
MAX_USAGE_HISTORY_SIZE = 1000

# Minimum number of tags for multiple tag bonus
MIN_TAGS_FOR_BONUS = 3

# Folder context match cap to prevent score inflation
MAX_FOLDER_CONTEXT_MATCHES = 2


class SFXMatcher:
    """Matches SFX assets to key moments in transcript segments.
    
    Identifies emotional beats and transitions suitable for SFX placement,
    then searches the indexed SFX library for contextually appropriate
    matches. Uses a scoring algorithm that considers tag relevance,
    folder context, match quality, and subtlety preferences.
    
    Attributes:
        max_suggestions: Maximum number of suggestions per moment
        min_confidence_threshold: Minimum confidence for viable matches
        track_usage_history: Whether to track recently used SFX
        usage_history: Set of recently used SFX IDs to avoid repetition
    """
    
    def __init__(
        self,
        max_suggestions: int = DEFAULT_MAX_SUGGESTIONS,
        min_confidence_threshold: float = DEFAULT_MIN_CONFIDENCE,
        track_usage_history: bool = True
    ):
        """Initialize the SFX matcher.
        
        Args:
            max_suggestions: Maximum matches to return per moment
            min_confidence_threshold: Minimum confidence for viable matches
            track_usage_history: Whether to track and deprioritize recently used assets
        """
        self.max_suggestions = max_suggestions
        self.min_confidence_threshold = min_confidence_threshold
        self.track_usage_history = track_usage_history
        self.usage_history: set[str] = set()
    
    def identify_sfx_moments(
        self,
        segments: list[dict[str, Any]]
    ) -> list[SFXMoment]:
        """Identify moments suitable for SFX placement.
        
        Analyzes transcript segments for emotional beats, transitions,
        and emphasis points where sound effects would enhance the narrative.
        
        Args:
            segments: List of transcript segment dictionaries with:
                - section_name: Segment name (e.g., "intro", "narrative_1")
                - start_time: Start timestamp in seconds
                - end_time: End timestamp in seconds
                - text: Segment transcript text
                - tone: Optional tone data (energy, mood descriptors)
        
        Returns:
            List of SFXMoment instances representing identified moments
            
        Raises:
            ValueError: If segments is empty or invalid
        """
        if not segments:
            raise ValueError("segments cannot be empty")
        
        moments: list[SFXMoment] = []
        
        for i, segment in enumerate(segments):
            segment_name = segment.get("section_name", f"segment_{i}")
            segment_start = segment.get("start_time", 0.0)
            segment_end = segment.get("end_time", 0.0)
            segment_text = segment.get("text", "")
            segment_tone = segment.get("tone", {})
            
            # Identify moments based on segment characteristics
            segment_moments = self._identify_moments_for_segment(
                segment_name=segment_name,
                segment_start=segment_start,
                segment_end=segment_end,
                segment_text=segment_text,
                segment_tone=segment_tone
            )
            
            moments.extend(segment_moments)
        
        # Sort by timestamp
        moments.sort(key=lambda m: m.timestamp)
        
        return moments
    
    def _identify_moments_for_segment(
        self,
        segment_name: str,
        segment_start: float,
        segment_end: float,
        segment_text: str,
        segment_tone: dict[str, Any]
    ) -> list[SFXMoment]:
        """Identify SFX moments within a single segment.
        
        Args:
            segment_name: Name of the segment
            segment_start: Start timestamp in seconds
            segment_end: End timestamp in seconds
            segment_text: Segment transcript text
            segment_tone: Segment tone data
            
        Returns:
            List of SFXMoment instances for this segment
        """
        moments: list[SFXMoment] = []
        segment_name_lower = segment_name.lower()
        text_lower = segment_text.lower()
        
        # Determine segment energy/mood from tone data
        energy = segment_tone.get("energy", "medium")
        mood = segment_tone.get("mood", "neutral")
        
        # Identify intro moment
        if "intro" in segment_name_lower or "hook" in segment_name_lower:
            moments.append(SFXMoment(
                timestamp=segment_start,
                type="intro",
                context="opening transition to establish scene",
                intensity="medium",
                segment_name=segment_name
            ))
        
        # Identify outro moment
        elif "outro" in segment_name_lower or "cta" in segment_name_lower or "ending" in segment_name_lower:
            moments.append(SFXMoment(
                timestamp=segment_end - 2.0,  # 2 seconds before end
                type="outro",
                context="closing transition and call-to-action",
                intensity="medium",
                segment_name=segment_name
            ))
        
        # Identify narrative moments based on emotional content
        elif "narrative" in segment_name_lower or "main" in segment_name_lower:
            # Check for triumph moments
            if any(word in text_lower for word in ["success", "achieve", "win", "victory", "triumph", "great", "amazing"]):
                # Find approximate position of triumph keyword
                timestamp = self._estimate_emphasis_timestamp(
                    text_lower, segment_start, segment_end,
                    ["success", "achieve", "win", "victory", "triumph", "great", "amazing"]
                )
                moments.append(SFXMoment(
                    timestamp=timestamp,
                    type="triumph",
                    context="emotional high point - victory or success",
                    intensity="medium",
                    segment_name=segment_name
                ))
            
            # Check for challenge/pivot moments
            elif any(word in text_lower for word in ["challenge", "difficult", "struggle", "problem", "but", "however"]):
                timestamp = self._estimate_emphasis_timestamp(
                    text_lower, segment_start, segment_end,
                    ["challenge", "difficult", "struggle", "problem", "but", "however"]
                )
                moments.append(SFXMoment(
                    timestamp=timestamp,
                    type="emphasis",
                    context="pivot moment - turning point or challenge",
                    intensity="medium",
                    segment_name=segment_name
                ))
            
            # Check for tension moments
            elif any(word in text_lower for word in ["tension", "suspense", "danger", "risk", "critical"]):
                timestamp = self._estimate_emphasis_timestamp(
                    text_lower, segment_start, segment_end,
                    ["tension", "suspense", "danger", "risk", "critical"]
                )
                moments.append(SFXMoment(
                    timestamp=timestamp,
                    type="tension",
                    context="tense moment - suspense or anticipation",
                    intensity="high",
                    segment_name=segment_name
                ))
            
            # Add underscore moment for longer segments (> 30s)
            segment_duration = segment_end - segment_start
            if segment_duration > 30.0:
                # Add underscore at 1/3 through segment
                underscore_time = segment_start + (segment_duration * 0.33)
                moments.append(SFXMoment(
                    timestamp=underscore_time,
                    type="underscore",
                    context="background texture to support narrative",
                    intensity="low",
                    segment_name=segment_name
                ))
        
        return moments
    
    def _estimate_emphasis_timestamp(
        self,
        text: str,
        start_time: float,
        end_time: float,
        keywords: list[str]
    ) -> float:
        """Estimate timestamp for an emphasis moment based on keyword position.
        
        Args:
            text: Lowercase segment text
            start_time: Segment start timestamp
            end_time: Segment end timestamp
            keywords: Keywords to find
            
        Returns:
            Estimated timestamp for emphasis moment
        """
        segment_duration = end_time - start_time
        
        # Find first keyword occurrence
        for keyword in keywords:
            pos = text.find(keyword)
            if pos != -1:
                # Estimate position as ratio through text
                ratio = pos / len(text) if len(text) > 0 else 0.5
                return start_time + (segment_duration * ratio)
        
        # Default to middle of segment
        return start_time + (segment_duration * 0.5)
    
    def match_sfx_to_moments(
        self,
        moments: list[SFXMoment],
        sfx_index: list[dict[str, Any]]
    ) -> SFXMatchingResult:
        """Match SFX assets to identified moments.
        
        Analyzes each moment's context and searches the SFX library for
        appropriate matches based on tag relevance and subtlety preferences.
        
        Args:
            moments: List of SFXMoment instances
            sfx_index: List of SFX asset dictionaries from indexed library
            
        Returns:
            SFXMatchingResult with all moment matches
            
        Raises:
            ValueError: If moments or sfx_index is empty
        """
        if not moments:
            raise ValueError("moments cannot be empty")
        if not sfx_index:
            raise ValueError("sfx_index cannot be empty")
        
        # Convert SFX index to SFXAsset objects
        sfx_assets = []
        for asset_data in sfx_index:
            try:
                asset = SFXAsset.from_dict(asset_data)
                sfx_assets.append(asset)
            except ValueError as e:
                logger.warning(f"Skipping invalid SFX asset: {e}")
        
        if not sfx_assets:
            raise ValueError("No valid SFX assets found in index")
        
        # Match SFX for each moment
        moment_matches_list = []
        warnings = []
        fallback_used = False
        
        for moment in moments:
            # Find matches for this moment
            matches, fallback = self._find_matches_for_moment(
                moment, sfx_assets
            )
            
            # Track fallback usage
            if fallback:
                fallback_used = True
                warnings.append(
                    f"Moment at {moment.format_timestamp()} used fallback SFX suggestion"
                )
            
            # Check for low confidence
            if not matches or all(m.confidence_score < LOW_CONFIDENCE_THRESHOLD for m in matches):
                warnings.append(
                    f"Low confidence matches for moment at {moment.format_timestamp()}"
                )
            
            # Create moment matches object
            moment_matches = MomentSFXMatches(
                moment=moment,
                matches=matches[:self.max_suggestions],
                fallback_suggestion=fallback
            )
            
            moment_matches_list.append(moment_matches)
        
        # Calculate statistics
        total_matches = sum(len(mm.matches) for mm in moment_matches_list)
        all_confidences = [
            m.confidence_score 
            for mm in moment_matches_list 
            for m in mm.matches
        ]
        average_confidence = (
            sum(all_confidences) / len(all_confidences) 
            if all_confidences else 0.0
        )
        
        all_subtleties = [
            m.subtlety_score 
            for mm in moment_matches_list 
            for m in mm.matches
        ]
        average_subtlety = (
            sum(all_subtleties) / len(all_subtleties)
            if all_subtleties else 0.0
        )
        
        return SFXMatchingResult(
            moment_matches=moment_matches_list,
            total_matches=total_matches,
            average_confidence=average_confidence,
            average_subtlety=average_subtlety,
            fallback_used=fallback_used,
            layer_guidance="Place each SFX on separate track for volume flexibility",
            warnings=warnings
        )
    
    def _find_matches_for_moment(
        self,
        moment: SFXMoment,
        sfx_assets: list[SFXAsset]
    ) -> tuple[list[SFXMatch], SFXMatch | None]:
        """Find SFX matches for a single moment.
        
        Args:
            moment: SFXMoment to match
            sfx_assets: Available SFX assets
            
        Returns:
            Tuple of (matches list, fallback suggestion or None)
        """
        # Get search tags from moment type
        search_tags = moment.to_tag_query()
        
        # Get preferred subtlety for this moment
        preferred_subtlety = moment.get_subtlety_preference()
        
        # Score all assets
        scored_assets = []
        for asset in sfx_assets:
            base_score, matched_tags = self._calculate_match_score(moment, asset, search_tags)
            # Apply usage penalty if asset was recently used
            adjusted_score = self._apply_usage_penalty(asset.sfx_id, base_score)
            # Calculate subtlety score
            subtlety_score = self._calculate_subtlety_score(asset, preferred_subtlety)
            scored_assets.append((asset, adjusted_score, matched_tags, subtlety_score))
        
        # Sort by score
        scored_assets.sort(key=lambda x: x[1], reverse=True)
        
        # Create SFXMatch objects
        matches = []
        
        for asset, score, matched_tags, subtlety_score in scored_assets:
            if score >= self.min_confidence_threshold:
                match_reason = self._generate_match_reason(moment, asset, matched_tags, score, subtlety_score)
                
                sfx_match = SFXMatch(
                    sfx_id=asset.sfx_id,
                    file_path=asset.file_path,
                    file_name=asset.get_file_name(),
                    folder_context=asset.folder_context,
                    match_reason=match_reason,
                    confidence_score=score,
                    matched_tags=matched_tags,
                    suggested_at=moment.timestamp,
                    duration_ms=asset.duration_ms,
                    subtlety_score=subtlety_score
                )
                
                matches.append(sfx_match)
        
        # Determine fallback if no good matches
        fallback = None
        if not matches or all(m.confidence_score < LOW_CONFIDENCE_THRESHOLD for m in matches):
            if scored_assets:
                # Use highest scored asset as fallback
                best_asset, score, matched_tags, subtlety_score = scored_assets[0]
                match_reason = f"Fallback: Best available match (score: {score:.2f})"
                
                fallback = SFXMatch(
                    sfx_id=best_asset.sfx_id,
                    file_path=best_asset.file_path,
                    file_name=best_asset.get_file_name(),
                    folder_context=best_asset.folder_context,
                    match_reason=match_reason,
                    confidence_score=max(score * 0.8, 0.4),
                    matched_tags=matched_tags,
                    suggested_at=moment.timestamp,
                    duration_ms=best_asset.duration_ms,
                    subtlety_score=subtlety_score
                )
        
        return matches, fallback
    
    def _calculate_match_score(
        self,
        moment: SFXMoment,
        asset: SFXAsset,
        search_tags: list[str]
    ) -> tuple[float, list[str]]:
        """Calculate match score between moment and SFX asset.
        
        Args:
            moment: SFXMoment to match
            asset: SFX asset to score
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
            # Weight decreases by position
            weight = 1.0 - (i * 0.1) if i < 10 else 0.1
            max_possible += weight
            
            # Check for exact match
            if tag_lower in asset_tags_lower:
                matched_tags.append(tag)
                total_weight += weight
            else:
                # Check for partial match
                for asset_tag in asset_tags_lower:
                    if tag_lower in asset_tag or asset_tag in tag_lower:
                        matched_tags.append(tag)
                        total_weight += weight * DEFAULT_FUZZY_MATCH_WEIGHT
                        break
        
        # Folder context bonus (capped)
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
        
        # Boost based on number of matches
        if len(matched_tags) >= MIN_TAGS_FOR_BONUS:
            confidence = min(confidence * DEFAULT_MULTIPLE_TAG_BONUS, 1.0)
        
        # Remove duplicate matched tags
        seen = set()
        unique_matched = []
        for tag in matched_tags:
            if tag.casefold() not in seen:
                seen.add(tag.casefold())
                unique_matched.append(tag)
        
        return confidence, unique_matched
    
    def _calculate_subtlety_score(
        self,
        asset: SFXAsset,
        preferred_subtlety: float
    ) -> float:
        """Calculate subtlety score for an SFX asset.
        
        Args:
            asset: SFX asset to score
            preferred_subtlety: Preferred subtlety level (0.0-1.0)
            
        Returns:
            Subtlety score (0.0-1.0)
        """
        duration_ms = asset.duration_ms
        
        # Base subtlety on duration
        if duration_ms == 0:
            # Unknown duration - assume moderate
            duration_subtlety = 0.6
        elif duration_ms < SHORT_DURATION_MS:
            # Short sounds are more subtle
            duration_subtlety = 0.85
        elif duration_ms < MEDIUM_DURATION_MS:
            # Medium duration
            duration_subtlety = 0.65
        elif duration_ms < LONG_DURATION_MS:
            # Longer sounds
            duration_subtlety = 0.45
        else:
            # Very long sounds
            duration_subtlety = 0.25
        
        # Check for subtlety-indicating tags
        subtle_tags = ["gentle", "soft", "subtle", "quiet", "light", "ambient"]
        has_subtle_tag = any(
            tag.casefold() in [t.casefold() for t in asset.tags]
            for tag in subtle_tags
        )
        
        if has_subtle_tag:
            duration_subtlety = min(duration_subtlety + 0.15, 1.0)
        
        # Combine with preference
        final_subtlety = (
            duration_subtlety * (1 - DEFAULT_DURATION_SUBTLETY_WEIGHT) +
            preferred_subtlety * DEFAULT_DURATION_SUBTLETY_WEIGHT
        )
        
        return min(max(final_subtlety, 0.0), 1.0)
    
    def _generate_match_reason(
        self,
        moment: SFXMoment,
        asset: SFXAsset,
        matched_tags: list[str],
        score: float,
        subtlety_score: float
    ) -> str:
        """Generate human-readable match reason.
        
        Args:
            moment: SFXMoment
            asset: Matched asset
            matched_tags: Tags that contributed to match
            score: Confidence score
            subtlety_score: Subtlety score
            
        Returns:
            Human-readable match explanation
        """
        tags_str = "'" + "', '".join(matched_tags[:3]) + "'" if matched_tags else "context"
        
        subtlety_desc = "subtle" if subtlety_score >= HIGH_SUBTLETY_THRESHOLD else "moderate"
        if asset.duration_ms > 0:
            duration_sec = asset.duration_ms / 1000
            duration_desc = f"{duration_sec:.1f}s duration"
        else:
            duration_desc = ""
        
        if score >= HIGH_CONFIDENCE_THRESHOLD:
            reason = (
                f"Tags {tags_str} strongly match moment type ({moment.type}); "
                f"{subtlety_desc} sound suitable for {moment.intensity} intensity"
            )
        elif score >= LOW_CONFIDENCE_THRESHOLD:
            reason = (
                f"Tags {tags_str} moderately match {moment.type} context; "
                f"{subtlety_desc} impact appropriate"
            )
        else:
            reason = (
                f"Limited match: tags {tags_str} partially align with "
                f"{moment.type} moment requirements"
            )
        
        if duration_desc:
            reason += f"; {duration_desc}"
        
        return reason
    
    def prevent_duplicate_matches(
        self,
        result: SFXMatchingResult,
        prefer_high_confidence: bool = True
    ) -> SFXMatchingResult:
        """Remove duplicate SFX suggestions across moments.
        
        When the same SFX asset is suggested for multiple moments,
        keeps it only for the moment where it's most appropriate.
        
        Args:
            result: Original matching result
            prefer_high_confidence: If True, keep for highest confidence moment
            
        Returns:
            Modified result with duplicates removed
        """
        seen_ids = {}  # sfx_id -> (moment_index, confidence)
        
        for i, mm in enumerate(result.moment_matches):
            for match in mm.matches:
                sid = match.sfx_id
                if sid in seen_ids:
                    existing_conf = seen_ids[sid][1]
                    if prefer_high_confidence and match.confidence_score > existing_conf:
                        seen_ids[sid] = (i, match.confidence_score)
                else:
                    seen_ids[sid] = (i, match.confidence_score)
        
        # Filter matches
        for i, mm in enumerate(result.moment_matches):
            mm.matches = [
                m for m in mm.matches 
                if seen_ids.get(m.sfx_id, (None, 0))[0] == i
            ]
        
        # Recalculate statistics
        result.total_matches = sum(len(mm.matches) for mm in result.moment_matches)
        all_confidences = [
            m.confidence_score 
            for mm in result.moment_matches 
            for m in mm.matches
        ]
        if all_confidences:
            result.average_confidence = sum(all_confidences) / len(all_confidences)
        else:
            result.average_confidence = 0.0
        
        return result
    
    def record_usage(self, sfx_id: str) -> None:
        """Record that an SFX asset was used.
        
        Args:
            sfx_id: ID of the SFX asset that was used
        """
        if not self.track_usage_history or not sfx_id:
            return
        
        self.usage_history.add(sfx_id)
        
        # Trim history if it exceeds max size
        if len(self.usage_history) > MAX_USAGE_HISTORY_SIZE:
            excess = len(self.usage_history) - MAX_USAGE_HISTORY_SIZE
            for _ in range(excess):
                if self.usage_history:
                    self.usage_history.pop()
    
    def is_recently_used(self, sfx_id: str) -> bool:
        """Check if an SFX asset was recently used.
        
        Args:
            sfx_id: ID of the SFX asset to check
            
        Returns:
            True if the asset is in usage history
        """
        return sfx_id in self.usage_history if self.track_usage_history else False
    
    def clear_usage_history(self) -> None:
        """Clear the usage history."""
        self.usage_history.clear()
    
    def _apply_usage_penalty(self, sfx_id: str, base_score: float) -> float:
        """Apply penalty to score for recently used assets.
        
        Args:
            sfx_id: ID of the SFX asset
            base_score: Original confidence score
            
        Returns:
            Adjusted confidence score with penalty applied
        """
        if not self.track_usage_history or not self.is_recently_used(sfx_id):
            return base_score
        
        # Apply 15% penalty for recently used assets
        return base_score * 0.85
