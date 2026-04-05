"""VFX matching engine for AI-powered template asset selection.

Provides the VFXMatcher class for identifying VFX requirements from format
templates and matching appropriate VFX templates from the indexed library
based on template asset groups, tag relevance, and placement constraints.
"""

from __future__ import annotations

import logging
from typing import Any

from .vfx_match import (
    HIGH_CONFIDENCE_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
    MIN_CONFIDENCE_THRESHOLD,
    VFXAsset,
    VFXMatch,
    VFXMatchingResult,
    VFXPlacement,
    RequirementVFXMatches
)
from .vfx_requirement import (
    VFXRequirement,
    VFX_REQUIREMENT_MAPPINGS,
    REQUIREMENT_TYPE_PREFERENCES,
    DEFAULT_DURATION_REQUIREMENTS
)

logger = logging.getLogger(__name__)

# Default configuration constants
DEFAULT_MAX_SUGGESTIONS = 3
DEFAULT_MIN_CONFIDENCE = 0.60
DEFAULT_FUZZY_MATCH_WEIGHT = 0.7
DEFAULT_FOLDER_CONTEXT_WEIGHT = 0.20
DEFAULT_MULTIPLE_TAG_BONUS = 1.1
DEFAULT_TEMPLATE_GROUP_BONUS = 1.15
DEFAULT_FUZZY_MATCH_THRESHOLD = 3
DEFAULT_DURATION_TOLERANCE = 0.5  # seconds of tolerance for duration matching

# Overlap tolerance for conflict detection (in seconds)
OVERLAP_TOLERANCE = 0.1

# Minimum number of tags for multiple tag bonus
MIN_TAGS_FOR_BONUS = 3

# Folder context match cap to prevent score inflation
MAX_FOLDER_CONTEXT_MATCHES = 2


class VFXMatcher:
    """Matches VFX templates to requirements from format templates.
    
    Identifies VFX requirements from format template specifications,
    then searches the indexed VFX library for appropriate matches.
    Uses a scoring algorithm that considers template asset group membership,
    tag relevance, folder context, and placement constraints.
    
    Attributes:
        max_suggestions: Maximum number of suggestions per requirement
        min_confidence_threshold: Minimum confidence for viable matches
        track_template_groups: Whether to prioritize template asset groups
    """
    
    def __init__(
        self,
        max_suggestions: int = DEFAULT_MAX_SUGGESTIONS,
        min_confidence_threshold: float = DEFAULT_MIN_CONFIDENCE,
        track_template_groups: bool = True
    ):
        """Initialize the VFX matcher.
        
        Args:
            max_suggestions: Maximum matches to return per requirement
            min_confidence_threshold: Minimum confidence for viable matches
            track_template_groups: Whether to track and prioritize template asset groups
        """
        self.max_suggestions = max_suggestions
        self.min_confidence_threshold = min_confidence_threshold
        self.track_template_groups = track_template_groups
    
    def identify_vfx_requirements(
        self,
        segments: list[dict[str, Any]],
        format_template: dict[str, Any]
    ) -> list[VFXRequirement]:
        """Identify VFX requirements from format template and segments.
        
        Parses format template VFX specifications and identifies
        specific timestamps where VFX are needed based on segment
        boundaries and speaker changes.
        
        Args:
            segments: List of transcript segment dictionaries with:
                - section_name: Segment name (e.g., "intro", "narrative_1")
                - start_time: Start timestamp in seconds
                - end_time: End timestamp in seconds
                - text: Segment transcript text
                - speaker: Optional speaker name
                - speaker_change: Boolean indicating speaker change
            format_template: Format template dictionary with:
                - vfx_requirements: List of VFX requirement specifications
                - template_asset_groups: Optional predefined asset groups
        
        Returns:
            List of VFXRequirement instances representing identified requirements
            
        Raises:
            ValueError: If segments is empty or format_template is invalid
        """
        if not segments:
            raise ValueError("segments cannot be empty")
        if not format_template:
            raise ValueError("format_template cannot be empty")
        
        requirements: list[VFXRequirement] = []
        
        # Get VFX requirements from format template
        template_reqs = format_template.get("vfx_requirements", [])
        
        # Process each segment to identify requirements
        for i, segment in enumerate(segments):
            # Validate segment structure
            if not isinstance(segment, dict):
                raise ValueError(f"Segment {i} must be a dictionary, got {type(segment).__name__}")
            
            segment_name = segment.get("section_name", f"segment_{i}")
            
            # Validate and extract timestamps with type checking
            segment_start = segment.get("start_time", 0.0)
            segment_end = segment.get("end_time", 0.0)
            
            if not isinstance(segment_start, (int, float)):
                raise ValueError(
                    f"Segment '{segment_name}' start_time must be numeric, got {type(segment_start).__name__}"
                )
            if not isinstance(segment_end, (int, float)):
                raise ValueError(
                    f"Segment '{segment_name}' end_time must be numeric, got {type(segment_end).__name__}"
                )
            if segment_start < 0:
                raise ValueError(
                    f"Segment '{segment_name}' start_time cannot be negative: {segment_start}"
                )
            if segment_end < segment_start:
                raise ValueError(
                    f"Segment '{segment_name}' end_time ({segment_end}) must be >= start_time ({segment_start})"
                )
            
            speaker = segment.get("speaker", "")
            speaker_change = segment.get("speaker_change", False)
            
            # Validate speaker_change is boolean-like
            if not isinstance(speaker_change, bool):
                speaker_change = bool(speaker_change)  # Convert truthy/falsy values
            
            # Identify requirements for this segment
            segment_reqs = self._identify_requirements_for_segment(
                segment_name=segment_name,
                segment_start=float(segment_start),
                segment_end=float(segment_end),
                speaker=speaker,
                speaker_change=speaker_change,
                template_requirements=template_reqs
            )
            
            requirements.extend(segment_reqs)
        
        # Sort by timestamp
        requirements.sort(key=lambda r: r.timestamp)
        
        return requirements
    
    def _identify_requirements_for_segment(
        self,
        segment_name: str,
        segment_start: float,
        segment_end: float,
        speaker: str,
        speaker_change: bool,
        template_requirements: list[dict[str, Any]]
    ) -> list[VFXRequirement]:
        """Identify VFX requirements within a single segment.
        
        Args:
            segment_name: Name of the segment
            segment_start: Start timestamp in seconds
            segment_end: End timestamp in seconds
            speaker: Speaker name (if any)
            speaker_change: Whether this segment has a speaker change
            template_requirements: VFX requirements from format template
            
        Returns:
            List of VFXRequirement instances for this segment
        """
        requirements: list[VFXRequirement] = []
        segment_name_lower = segment_name.lower()
        
        for req_spec in template_requirements:
            req_type = req_spec.get("type", "")
            at_position = req_spec.get("at", "")
            duration = req_spec.get("duration", DEFAULT_DURATION_REQUIREMENTS.get(req_type, 3.0))
            
            # Determine timestamp based on "at" specification
            timestamp = self._resolve_timestamp(
                at_position=at_position,
                segment_start=segment_start,
                segment_end=segment_end
            )
            
            # Skip if we couldn't resolve a valid timestamp
            if timestamp is None:
                continue
            
            # Generate context based on requirement type
            context = self._generate_requirement_context(
                req_type=req_type,
                segment_name=segment_name,
                speaker=speaker,
                speaker_change=speaker_change
            )
            
            # Create requirement
            requirement = VFXRequirement(
                timestamp=timestamp,
                type=req_type,
                context=context,
                duration=duration,
                format_section=segment_name,
                speaker_name=speaker if req_type == "lower_third" and speaker else None
            )
            
            requirements.append(requirement)
        
        # Add lower third requirement on speaker changes
        if speaker_change and speaker:
            # Check if we already have a lower third at this position
            has_lower_third = any(
                r.type == "lower_third" and abs(r.timestamp - segment_start) < 1.0
                for r in requirements
            )
            
            if not has_lower_third:
                requirements.append(VFXRequirement(
                    timestamp=segment_start,
                    type="lower_third",
                    context=f"speaker introduction - {speaker}",
                    duration=DEFAULT_DURATION_REQUIREMENTS.get("lower_third", 3.0),
                    format_section=segment_name,
                    speaker_name=speaker
                ))
        
        return requirements
    
    def _resolve_timestamp(
        self,
        at_position: str,
        segment_start: float,
        segment_end: float
    ) -> float | None:
        """Resolve timestamp from "at" specification.
        
        Args:
            at_position: Position specification (e.g., "segment_start", "section_end")
            segment_start: Segment start timestamp
            segment_end: Segment end timestamp
            
        Returns:
            Resolved timestamp or None if cannot resolve
        """
        at_lower = at_position.lower() if at_position else ""
        
        if at_lower in ["segment_start", "start", "beginning", "intro"]:
            return segment_start
        elif at_lower in ["segment_end", "end", "section_end", "outro"]:
            return segment_end
        elif at_lower in ["middle", "center"]:
            return (segment_start + segment_end) / 2
        elif at_position.startswith("+") or at_position.startswith("-"):
            # Relative offset from start
            try:
                offset = float(at_position)
                resolved_time = segment_start + offset
                # Ensure non-negative timestamp
                if resolved_time < 0:
                    logger.warning(
                        f"Relative offset {at_position} results in negative timestamp "
                        f"({resolved_time}), clamping to 0.0"
                    )
                    return 0.0
                return resolved_time
            except ValueError:
                logger.warning(f"Invalid relative offset '{at_position}', using segment_start")
                return segment_start
        else:
            # Try to parse as absolute timestamp
            try:
                return float(at_position)
            except (ValueError, TypeError):
                # Default to segment start
                return segment_start
    
    def _generate_requirement_context(
        self,
        req_type: str,
        segment_name: str,
        speaker: str,
        speaker_change: bool
    ) -> str:
        """Generate human-readable context for a requirement.
        
        Args:
            req_type: Requirement type
            segment_name: Segment name
            speaker: Speaker name
            speaker_change: Whether there's a speaker change
            
        Returns:
            Human-readable context string
        """
        contexts = {
            "lower_third": f"speaker introduction{f' - {speaker}' if speaker else ''}",
            "transition": f"section transition - {segment_name}",
            "title_card": f"title display - {segment_name}",
            "outro_cta": f"section ending - call to action",
            "logo_anim": f"brand introduction - {segment_name}",
            "broll_placeholder": f"B-roll placeholder - {segment_name}",
        }
        
        return contexts.get(req_type, f"VFX requirement - {segment_name}")
    
    def match_vfx_to_requirements(
        self,
        requirements: list[VFXRequirement],
        vfx_index: list[dict[str, Any]],
        template_asset_groups: dict[str, list[str]] | None = None
    ) -> VFXMatchingResult:
        """Match VFX templates to identified requirements.
        
        Analyzes each requirement's context and searches the VFX library for
        appropriate matches based on template asset groups and tag relevance.
        
        Args:
            requirements: List of VFXRequirement instances
            vfx_index: List of VFX asset dictionaries from indexed library
            template_asset_groups: Optional predefined asset groups from format template
            
        Returns:
            VFXMatchingResult with all requirement matches
            
        Raises:
            ValueError: If requirements or vfx_index is empty
        """
        if not requirements:
            raise ValueError("requirements cannot be empty")
        if not vfx_index:
            raise ValueError("vfx_index cannot be empty")
        
        # Convert VFX index to VFXAsset objects
        vfx_assets = []
        for asset_data in vfx_index:
            try:
                asset = VFXAsset.from_dict(asset_data)
                vfx_assets.append(asset)
            except ValueError as e:
                logger.warning(f"Skipping invalid VFX asset: {e}")
        
        if not vfx_assets:
            raise ValueError("No valid VFX assets found in index")
        
        # Match VFX for each requirement
        requirement_matches_list = []
        warnings = []
        fallback_used = False
        group_matches_count = 0
        
        for requirement in requirements:
            # Find matches for this requirement
            matches, fallback = self._find_matches_for_requirement(
                requirement=requirement,
                vfx_assets=vfx_assets,
                template_asset_groups=template_asset_groups
            )
            
            # Track fallback usage
            if fallback:
                fallback_used = True
                warnings.append(
                    f"Requirement at {requirement.format_timestamp()} used fallback VFX suggestion"
                )
            
            # Track template group coverage
            for match in matches:
                if match.from_template_group:
                    group_matches_count += 1
            
            # Check for low confidence
            if not matches or all(m.confidence_score < LOW_CONFIDENCE_THRESHOLD for m in matches):
                warnings.append(
                    f"Low confidence matches for requirement at {requirement.format_timestamp()}"
                )
            
            # Create requirement matches object
            req_matches = RequirementVFXMatches(
                requirement=requirement,
                matches=matches[:self.max_suggestions],
                fallback_suggestion=fallback
            )
            
            requirement_matches_list.append(req_matches)
        
        # Calculate statistics
        total_matches = sum(len(rm.matches) for rm in requirement_matches_list)
        all_confidences = [
            m.confidence_score 
            for rm in requirement_matches_list 
            for m in rm.matches
        ]
        average_confidence = (
            sum(all_confidences) / len(all_confidences) 
            if all_confidences else 0.0
        )
        
        # Calculate template group coverage
        template_group_coverage = (
            group_matches_count / total_matches if total_matches > 0 else 0.0
        )
        
        # Detect placement conflicts
        placement_conflicts = self._detect_placement_conflicts(requirement_matches_list)
        
        return VFXMatchingResult(
            requirement_matches=requirement_matches_list,
            total_matches=total_matches,
            average_confidence=average_confidence,
            fallback_used=fallback_used,
            placement_conflicts=placement_conflicts,
            template_group_coverage=template_group_coverage,
            warnings=warnings
        )
    
    def _find_matches_for_requirement(
        self,
        requirement: VFXRequirement,
        vfx_assets: list[VFXAsset],
        template_asset_groups: dict[str, list[str]] | None
    ) -> tuple[list[VFXMatch], VFXMatch | None]:
        """Find VFX matches for a single requirement.
        
        Args:
            requirement: VFXRequirement to match
            vfx_assets: Available VFX assets
            template_asset_groups: Optional predefined asset groups
            
        Returns:
            Tuple of (matches list, fallback suggestion or None)
        """
        # Get search tags from requirement type
        search_tags = requirement.to_tag_query()
        
        # Get preferred template types for this requirement
        preferred_types = requirement.get_preferred_template_types()
        
        # Find assets in template asset groups
        group_asset_ids = self._get_group_asset_ids(
            requirement.type, template_asset_groups
        )
        
        # Score all assets
        scored_assets = []
        for asset in vfx_assets:
            # Check if asset is in preferred template types
            type_match = asset.matches_template_type_preference(preferred_types)
            
            # Check if asset is in template group
            in_group = asset.vfx_id in group_asset_ids or self._asset_in_group_by_name(
                asset, group_asset_ids, template_asset_groups
            )
            
            # Calculate base score
            base_score, matched_tags = self._calculate_match_score(
                requirement, asset, search_tags
            )
            
            # Apply template group bonus
            if in_group and self.track_template_groups:
                base_score = min(base_score * DEFAULT_TEMPLATE_GROUP_BONUS, 1.0)
            
            scored_assets.append((asset, base_score, matched_tags, in_group, type_match))
        
        # Sort by score
        scored_assets.sort(key=lambda x: x[1], reverse=True)
        
        # Create VFXMatch objects with placement
        matches = []
        group_name = self._get_group_name_for_requirement(
            requirement.type, template_asset_groups
        )
        
        for asset, score, matched_tags, in_group, type_match in scored_assets:
            if score >= self.min_confidence_threshold:
                # Calculate placement
                placement = self._calculate_placement(requirement, asset)
                
                match_reason = self._generate_match_reason(
                    requirement, asset, matched_tags, score, in_group
                )
                
                vfx_match = VFXMatch(
                    vfx_id=asset.vfx_id,
                    file_path=asset.file_path,
                    file_name=asset.get_file_name(),
                    folder_context=asset.folder_context,
                    match_reason=match_reason,
                    confidence_score=score,
                    matched_tags=matched_tags,
                    template_type=asset.template_type,
                    placement=placement,
                    from_template_group=in_group,
                    group_name=group_name if in_group else None
                )
                
                matches.append(vfx_match)
        
        # Determine fallback if no good matches
        fallback = None
        if not matches or all(m.confidence_score < LOW_CONFIDENCE_THRESHOLD for m in matches):
            if scored_assets:
                # Use highest scored asset as fallback
                best_asset, score, matched_tags, in_group, type_match = scored_assets[0]
                placement = self._calculate_placement(requirement, best_asset)
                
                match_reason = f"Fallback: Best available match (score: {score:.2f})"
                
                fallback = VFXMatch(
                    vfx_id=best_asset.vfx_id,
                    file_path=best_asset.file_path,
                    file_name=best_asset.get_file_name(),
                    folder_context=best_asset.folder_context,
                    match_reason=match_reason,
                    confidence_score=max(score * 0.8, 0.4),
                    matched_tags=matched_tags,
                    template_type=best_asset.template_type,
                    placement=placement,
                    from_template_group=in_group,
                    group_name=group_name if in_group else None
                )
        
        return matches, fallback
    
    def _get_group_asset_ids(
        self,
        req_type: str,
        template_asset_groups: dict[str, list[str]] | None
    ) -> set[str]:
        """Get VFX asset IDs from template asset groups for a requirement type.
        
        Args:
            req_type: Requirement type
            template_asset_groups: Predefined asset groups from format template
            
        Returns:
            Set of VFX asset IDs in relevant groups
        """
        if not template_asset_groups:
            return set()
        
        # Map requirement types to likely group names
        group_name_mappings = {
            "lower_third": ["lower_thirds", "lower_third", "titles"],
            "transition": ["transitions", "transition"],
            "title_card": ["titles", "title_cards", "title_card"],
            "outro_cta": ["outros", "outro", "cta"],
            "logo_anim": ["logos", "logo", "intro_graphics"],
            "broll_placeholder": ["placeholders", "broll"],
        }
        
        group_names = group_name_mappings.get(req_type, [req_type])
        asset_ids = set()
        
        for group_name in group_names:
            if group_name in template_asset_groups:
                # These could be asset IDs or asset names
                for asset_ref in template_asset_groups[group_name]:
                    asset_ids.add(asset_ref)
        
        return asset_ids
    
    def _asset_in_group_by_name(
        self,
        asset: VFXAsset,
        group_asset_ids: set[str],
        template_asset_groups: dict[str, list[str]] | None
    ) -> bool:
        """Check if asset is in a template group by name matching.
        
        Args:
            asset: VFX asset to check
            group_asset_ids: Set of asset IDs in groups
            template_asset_groups: Template asset groups
            
        Returns:
            True if asset is in a group
        """
        # Check by ID
        if asset.vfx_id in group_asset_ids:
            return True
        
        # Check by filename (without extension)
        asset_name = asset.get_file_name().rsplit(".", 1)[0].lower()
        for ref in group_asset_ids:
            ref_lower = ref.lower()
            if ref_lower == asset_name or ref_lower in asset_name or asset_name in ref_lower:
                return True
        
        return False
    
    def _get_group_name_for_requirement(
        self,
        req_type: str,
        template_asset_groups: dict[str, list[str]] | None
    ) -> str | None:
        """Get the group name for a requirement type.
        
        Args:
            req_type: Requirement type
            template_asset_groups: Template asset groups
            
        Returns:
            Group name if found, None otherwise
        """
        if not template_asset_groups:
            return None
        
        group_name_mappings = {
            "lower_third": ["lower_thirds", "lower_third"],
            "transition": ["transitions", "transition"],
            "title_card": ["titles", "title_cards"],
            "outro_cta": ["outros", "outro", "cta"],
            "logo_anim": ["logos", "logo"],
            "broll_placeholder": ["placeholders", "broll"],
        }
        
        possible_names = group_name_mappings.get(req_type, [])
        for name in possible_names:
            if name in template_asset_groups:
                return name
        
        return None
    
    def _calculate_match_score(
        self,
        requirement: VFXRequirement,
        asset: VFXAsset,
        search_tags: list[str]
    ) -> tuple[float, list[str]]:
        """Calculate match score between requirement and VFX asset.
        
        Args:
            requirement: VFXRequirement to match
            asset: VFX asset to score
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
        
        # Template type preference bonus
        preferred_types = requirement.get_preferred_template_types()
        if asset.template_type in preferred_types:
            total_weight += 0.1
            max_possible += 0.1
        
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
    
    def _calculate_placement(
        self,
        requirement: VFXRequirement,
        asset: VFXAsset
    ) -> VFXPlacement:
        """Calculate VFX placement for timeline.
        
        Args:
            requirement: VFX requirement with desired timing
            asset: VFX asset with actual duration
            
        Returns:
            Calculated VFXPlacement
        """
        # Use requirement timestamp as start
        start_time = requirement.timestamp
        
        # Determine duration
        if asset.duration_ms > 0:
            # Use asset's actual duration
            duration_ms = asset.duration_ms
        else:
            # Use requirement's duration
            duration_ms = int(requirement.duration * 1000)
        
        # Calculate end time
        duration_sec = duration_ms / 1000.0
        end_time = start_time + duration_sec
        
        return VFXPlacement(
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms
        )
    
    def _generate_match_reason(
        self,
        requirement: VFXRequirement,
        asset: VFXAsset,
        matched_tags: list[str],
        score: float,
        from_group: bool
    ) -> str:
        """Generate human-readable match reason.
        
        Args:
            requirement: VFXRequirement
            asset: Matched asset
            matched_tags: Tags that contributed to match
            score: Confidence score
            from_group: Whether asset is from template asset group
            
        Returns:
            Human-readable match explanation
        """
        tags_str = "'" + "', '".join(matched_tags[:3]) + "'" if matched_tags else "context"
        
        group_info = "in predefined asset group; " if from_group else ""
        
        if score >= HIGH_CONFIDENCE_THRESHOLD:
            reason = (
                f"Tags {tags_str} strongly match requirement type ({requirement.type}); "
                f"{group_info}template type '{asset.template_type}' appropriate"
            )
        elif score >= LOW_CONFIDENCE_THRESHOLD:
            reason = (
                f"Tags {tags_str} moderately match {requirement.type} context; "
                f"{group_info}suitable for {requirement.context}"
            )
        else:
            reason = (
                f"Limited match: tags {tags_str} partially align with "
                f"{requirement.type} requirements"
            )
        
        return reason
    
    def _detect_placement_conflicts(
        self,
        requirement_matches: list[RequirementVFXMatches]
    ) -> list[dict[str, Any]]:
        """Detect overlapping VFX placements.
        
        Args:
            requirement_matches: List of requirement matches with placements
            
        Returns:
            List of conflict dictionaries describing overlaps
        """
        conflicts = []
        
        # Get all matches with their placements
        all_matches = []
        for rm in requirement_matches:
            for match in rm.matches:
                all_matches.append((rm.requirement, match))
        
        # Check each pair for overlap
        for i, (req1, match1) in enumerate(all_matches):
            for req2, match2 in all_matches[i + 1:]:
                if match1.placement.overlaps_with(match2.placement, OVERLAP_TOLERANCE):
                    overlap_duration = match1.placement.get_overlap_duration(match2.placement)
                    
                    conflict = {
                        "match1": {
                            "vfx_id": match1.vfx_id,
                            "requirement_type": req1.type,
                            "start_time": match1.placement.start_time,
                            "end_time": match1.placement.end_time
                        },
                        "match2": {
                            "vfx_id": match2.vfx_id,
                            "requirement_type": req2.type,
                            "start_time": match2.placement.start_time,
                            "end_time": match2.placement.end_time
                        },
                        "overlap_seconds": overlap_duration,
                        "recommendation": "Consider staggering placements or removing one VFX"
                    }
                    
                    conflicts.append(conflict)
        
        return conflicts
    
    def resolve_placement_conflicts(
        self,
        result: VFXMatchingResult,
        prefer_high_confidence: bool = True
    ) -> VFXMatchingResult:
        """Resolve overlapping VFX placements by removing lower priority matches.
        
        When two VFX templates would overlap on the timeline, keeps only the
        higher priority one (based on confidence or template group membership).
        
        Args:
            result: Original matching result with conflicts
            prefer_high_confidence: If True, keep highest confidence match; 
                                  else keep matches from template groups
            
        Returns:
            Modified result with conflicts resolved
        """
        if not result.placement_conflicts:
            return result
        
        # Build map of match priorities
        match_priorities = {}
        for rm in result.requirement_matches:
            for match in rm.matches:
                priority = match.confidence_score
                if not prefer_high_confidence and match.from_template_group:
                    priority += 0.2  # Boost group matches
                match_priorities[match.vfx_id] = priority
        
        # Identify which matches to keep for each conflict
        matches_to_remove = set()
        
        for conflict in result.placement_conflicts:
            id1 = conflict["match1"]["vfx_id"]
            id2 = conflict["match2"]["vfx_id"]
            
            if id1 in match_priorities and id2 in match_priorities:
                if match_priorities[id1] >= match_priorities[id2]:
                    matches_to_remove.add(id2)
                else:
                    matches_to_remove.add(id1)
        
        # Remove lower priority matches
        for rm in result.requirement_matches:
            rm.matches = [m for m in rm.matches if m.vfx_id not in matches_to_remove]
        
        # Recalculate statistics
        result.total_matches = sum(len(rm.matches) for rm in result.requirement_matches)
        all_confidences = [
            m.confidence_score 
            for rm in result.requirement_matches 
            for m in rm.matches
        ]
        if all_confidences:
            result.average_confidence = sum(all_confidences) / len(all_confidences)
        else:
            result.average_confidence = 0.0
        
        # Clear conflicts since we resolved them
        result.placement_conflicts = []
        
        return result
