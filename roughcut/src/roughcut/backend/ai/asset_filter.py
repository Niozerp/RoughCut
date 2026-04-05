"""Asset filtering for chunk-based AI processing.

Provides the AssetFilter class for filtering large asset libraries based on
chunk context, reducing token usage while maintaining relevant asset coverage.
"""

from __future__ import annotations

import heapq
from typing import Optional

from .chunk import ChunkContext


#: Minimum number of assets required after filtering
MIN_FILTERED_ASSETS = 10

#: Default minimum threshold for tag-based pre-filtering
PREFILTER_THRESHOLD = 1000

#: Section type to category mapping for asset filtering
SECTION_CATEGORY_MAP = {
    "intro": ["intro_music", "intro_sfx", "title_vfx", "logo_vfx"],
    "hook": ["hook_music", "hook_sfx", "attention_vfx"],
    "narrative": ["narrative_music", "ambient_sfx", "broll_vfx"],
    "act_1": ["narrative_music", "ambient_sfx", "character_vfx"],
    "act_2": ["tension_music", "dramatic_sfx", "transition_vfx"],
    "act_3": ["climax_music", "intense_sfx", "action_vfx"],
    "outro": ["outro_music", "ending_sfx", "cta_vfx", "credit_vfx"],
    "transition": ["transition_sfx", "wipe_vfx", "fade_vfx"],
    "montage": ["montage_music", "upbeat_sfx", "quick_vfx"],
}

#: Tone to tag mapping for relevance filtering
TONE_TAG_MAP = {
    "upbeat": ["upbeat", "energetic", "happy", "positive", "bright"],
    "contemplative": ["contemplative", "thoughtful", "reflective", "calm"],
    "tense": ["tense", "suspense", "dramatic", "intense", "dark"],
    "triumphant": ["triumphant", "victory", "success", "epic", "grand"],
    "somber": ["somber", "sad", "melancholy", "emotional", "dramatic"],
    "corporate": ["corporate", "professional", "business", "clean"],
    "casual": ["casual", "conversational", "light", "relaxed"],
    "epic": ["epic", "cinematic", "grand", "large", "monumental"],
    "minimal": ["minimal", "simple", "clean", "sparse", "subtle"],
}

#: Category to default tags mapping
CATEGORY_DEFAULT_TAGS = {
    "intro_music": ["intro", "opening", "start"],
    "narrative_music": ["background", "bed", "ambient"],
    "outro_music": ["outro", "ending", "close"],
    "intro_sfx": ["intro", "whoosh", "swish"],
    "ambient_sfx": ["ambient", "background", "atmosphere"],
    "ending_sfx": ["ending", "outro", "finish"],
    "title_vfx": ["title", "intro", "opening"],
    "logo_vfx": ["logo", "brand", "identity"],
    "cta_vfx": ["cta", "call_to_action", "button"],
}


class AssetFilter:
    """Filters asset libraries based on chunk context.
    
    Reduces token usage for large asset libraries by pre-filtering
    to only include assets relevant to the current chunk's section
    type, tone, and required categories.
    
    Attributes:
        min_filtered_assets: Minimum number of assets to return
        prefilter_threshold: Threshold for triggering tag-based pre-filtering
    """
    
    def __init__(
        self,
        min_filtered_assets: int = MIN_FILTERED_ASSETS,
        prefilter_threshold: int = PREFILTER_THRESHOLD
    ):
        """Initialize asset filter.
        
        Args:
            min_filtered_assets: Minimum number of assets required after filtering
            prefilter_threshold: Library size threshold for pre-filtering
        """
        self.min_filtered_assets = min_filtered_assets
        self.prefilter_threshold = prefilter_threshold
    
    def filter_assets_by_chunk_context(
        self,
        asset_index: dict[str, list[dict]],
        chunk_context: ChunkContext
    ) -> dict[str, list[dict]]:
        """Filter asset index based on chunk context.
        
        Args:
            asset_index: Dictionary mapping categories to asset lists
            chunk_context: ChunkContext with filtering criteria
            
        Returns:
            Filtered asset index dictionary
        """
        filtered_index = {}
        
        for category, assets in asset_index.items():
            # Check if category is relevant for this section type
            if not self._is_category_relevant(category, chunk_context):
                continue
            
            # Apply filtering based on library size
            if len(assets) > self.prefilter_threshold:
                filtered_assets = self._filter_by_tags(
                    assets,
                    chunk_context.relevant_tags,
                    chunk_context.tone
                )
            else:
                filtered_assets = assets
            
            # Ensure minimum threshold
            if len(filtered_assets) < self.min_filtered_assets:
                # Fall back to top assets by relevance score
                filtered_assets = self._get_fallback_assets(
                    assets,
                    chunk_context,
                    self.min_filtered_assets
                )
            
            if filtered_assets:
                filtered_index[category] = filtered_assets
        
        return filtered_index
    
    def _is_category_relevant(
        self,
        category: str,
        chunk_context: ChunkContext
    ) -> bool:
        """Check if a category is relevant for the chunk context.
        
        Args:
            category: Asset category name
            chunk_context: Chunk context with filtering criteria
            
        Returns:
            True if category is relevant
        """
        # If required_categories is specified, only include those
        if chunk_context.required_categories:
            return category in chunk_context.required_categories
        
        # Otherwise use section type mapping
        section_categories = SECTION_CATEGORY_MAP.get(
            chunk_context.section_type,
            []
        )
        
        # Category is relevant if it matches section mapping
        # or if it's a generic category
        return (
            category in section_categories
            or category in ["music", "sfx", "vfx"]  # Generic categories always relevant
        )
    
    def _filter_by_tags(
        self,
        assets: list[dict],
        relevant_tags: list[str],
        tone: str
    ) -> list[dict]:
        """Filter assets by relevance to tags and tone.
        
        Args:
            assets: List of asset dictionaries
            relevant_tags: List of relevant tags
            tone: Tone descriptor
            
        Returns:
            Filtered list of assets
        """
        # Build search tags list
        search_tags = set(tag.casefold() for tag in relevant_tags)
        
        # Add tone-specific tags
        tone_tags = TONE_TAG_MAP.get(tone, [])
        search_tags.update(tag.casefold() for tag in tone_tags)
        
        # Score and filter assets
        scored_assets = []
        for asset in assets:
            score = self._calculate_tag_relevance(asset, search_tags)
            if score > 0:
                scored_assets.append((score, asset))
        
        # For large libraries, use heapq for efficient top-N selection
        # O(n log k) vs O(n log n) for full sort where k = threshold
        if len(scored_assets) > self.prefilter_threshold * 2:
            # Use heapq.nlargest for better performance on large datasets
            top_assets = heapq.nlargest(
                self.prefilter_threshold,
                scored_assets,
                key=lambda x: x[0]
            )
            return [asset for _, asset in top_assets]
        else:
            # Sort by score (highest first) and return
            scored_assets.sort(key=lambda x: x[0], reverse=True)
            # Return top assets (up to prefilter_threshold)
            return [asset for _, asset in scored_assets[:self.prefilter_threshold]]
    
    def _calculate_tag_relevance(
        self,
        asset: dict,
        search_tags: set[str]
    ) -> float:
        """Calculate relevance score for an asset.
        
        Args:
            asset: Asset dictionary with tags
            search_tags: Set of tags to search for
            
        Returns:
            Relevance score (0.0 to 1.0+)
        """
        asset_tags = asset.get("tags", [])
        if not asset_tags:
            return 0.0
        
        # Normalize asset tags
        asset_tags_lower = set(tag.casefold() for tag in asset_tags if tag)
        
        # Calculate overlap
        matches = search_tags & asset_tags_lower
        
        if not matches:
            return 0.0
        
        # Score based on number of matches and asset tag coverage
        match_score = len(matches) / len(search_tags) if search_tags else 0
        coverage_score = len(matches) / len(asset_tags_lower) if asset_tags_lower else 0
        
        # Combined score (weighted toward match quality)
        return match_score * 0.7 + coverage_score * 0.3
    
    def _get_fallback_assets(
        self,
        assets: list[dict],
        chunk_context: ChunkContext,
        min_count: int
    ) -> list[dict]:
        """Get fallback assets when filtered results are below minimum.
        
        Args:
            assets: Full list of assets
            chunk_context: Chunk context for relevance scoring
            min_count: Minimum number of assets to return
            
        Returns:
            List of fallback assets
        """
        # Score all assets
        relevant_tags = set(tag.casefold() for tag in chunk_context.relevant_tags)
        tone_tags = TONE_TAG_MAP.get(chunk_context.tone, [])
        relevant_tags.update(tag.casefold() for tag in tone_tags)
        
        scored_assets = []
        for asset in assets:
            score = self._calculate_tag_relevance(asset, relevant_tags)
            scored_assets.append((score, asset))
        
        # Sort by score and return top min_count
        scored_assets.sort(key=lambda x: x[0], reverse=True)
        return [asset for _, asset in scored_assets[:min_count]]
    
    def build_chunk_context(
        self,
        section_name: str,
        section_duration: float,
        start_time: float,
        format_template: dict,
        tone: Optional[str] = None
    ) -> ChunkContext:
        """Build chunk context from format template section.
        
        Args:
            section_name: Name of section (intro, narrative, etc.)
            section_duration: Duration of section in seconds
            start_time: Start time of section
            format_template: Format template dictionary
            tone: Optional tone override
            
        Returns:
            ChunkContext instance
        """
        # Get required categories from format template
        sections = format_template.get("sections", [])
        section_data = next(
            (s for s in sections if s.get("name") == section_name),
            {}
        )
        
        required_categories = section_data.get("asset_categories", [])
        
        # Get default categories for section type if not specified
        if not required_categories:
            required_categories = SECTION_CATEGORY_MAP.get(section_name, [])
        
        # Determine tone
        if tone is None:
            # Infer tone from section type
            tone = self._infer_tone_from_section(section_name)
        
        # Build relevant tags
        relevant_tags = self._build_relevant_tags(
            section_name,
            tone,
            required_categories
        )
        
        return ChunkContext(
            section_type=section_name,
            tone=tone,
            required_categories=required_categories,
            time_range=(start_time, start_time + section_duration),
            relevant_tags=relevant_tags
        )
    
    def _infer_tone_from_section(self, section_name: str) -> str:
        """Infer emotional tone from section name.
        
        Args:
            section_name: Name of section
            
        Returns:
            Inferred tone
        """
        tone_map = {
            "intro": "upbeat",
            "hook": "upbeat",
            "outro": "triumphant",
            "act_1": "contemplative",
            "act_2": "tense",
            "act_3": "epic",
            "climax": "epic",
            "montage": "upbeat",
            "transition": "minimal",
        }
        return tone_map.get(section_name, "corporate")
    
    def _build_relevant_tags(
        self,
        section_name: str,
        tone: str,
        categories: list[str]
    ) -> list[str]:
        """Build list of relevant tags for filtering.
        
        Args:
            section_name: Section name
            tone: Tone descriptor
            categories: List of category IDs
            
        Returns:
            List of relevant tags
        """
        tags = [section_name]
        
        # Add tone tags
        tone_tags = TONE_TAG_MAP.get(tone, [])
        tags.extend(tone_tags)
        
        # Add category default tags
        for category in categories:
            default_tags = CATEGORY_DEFAULT_TAGS.get(category, [])
            tags.extend(default_tags)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            tag_lower = tag.casefold()
            if tag_lower not in seen:
                seen.add(tag_lower)
                unique_tags.append(tag)
        
        return unique_tags
