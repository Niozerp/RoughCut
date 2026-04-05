"""Unit tests for asset filter module.

Tests cover AssetFilter, ChunkContext, and related filtering functionality.
"""

from __future__ import annotations

import pytest

from roughcut.backend.ai.asset_filter import (
    AssetFilter,
    ChunkContext,
    SECTION_CATEGORY_MAP,
    TONE_TAG_MAP,
    CATEGORY_DEFAULT_TAGS,
    MIN_FILTERED_ASSETS,
    PREFILTER_THRESHOLD,
)


class TestChunkContext:
    """Tests for ChunkContext dataclass."""
    
    def test_initialization(self):
        """Test ChunkContext initialization."""
        context = ChunkContext(
            section_type="intro",
            tone="upbeat",
            required_categories=["intro_music", "title_vfx"],
            time_range=(0.0, 60.0),
            relevant_tags=["intro", "upbeat", "corporate"]
        )
        assert context.section_type == "intro"
        assert context.tone == "upbeat"
        assert context.required_categories == ["intro_music", "title_vfx"]
        assert context.time_range == (0.0, 60.0)
        assert context.relevant_tags == ["intro", "upbeat", "corporate"]


class TestAssetFilterInitialization:
    """Tests for AssetFilter initialization."""
    
    def test_default_initialization(self):
        """Test AssetFilter with default values."""
        filter_obj = AssetFilter()
        assert filter_obj.min_filtered_assets == MIN_FILTERED_ASSETS
        assert filter_obj.prefilter_threshold == PREFILTER_THRESHOLD
    
    def test_custom_initialization(self):
        """Test AssetFilter with custom values."""
        filter_obj = AssetFilter(min_filtered_assets=20, prefilter_threshold=500)
        assert filter_obj.min_filtered_assets == 20
        assert filter_obj.prefilter_threshold == 500


class TestAssetFilterCategoryRelevance:
    """Tests for category relevance checking."""
    
    def test_required_categories_filtering(self):
        """Test that only required categories are included."""
        filter_obj = AssetFilter()
        context = ChunkContext(
            section_type="intro",
            tone="upbeat",
            required_categories=["intro_music"],
            time_range=(0.0, 60.0),
            relevant_tags=["intro"]
        )
        
        assert filter_obj._is_category_relevant("intro_music", context) is True
        assert filter_obj._is_category_relevant("outro_music", context) is False
    
    def test_section_type_mapping(self):
        """Test section type to category mapping."""
        filter_obj = AssetFilter()
        context = ChunkContext(
            section_type="intro",
            tone="upbeat",
            required_categories=[],  # Empty, so uses section mapping
            time_range=(0.0, 60.0),
            relevant_tags=["intro"]
        )
        
        assert filter_obj._is_category_relevant("intro_music", context) is True
        assert filter_obj._is_category_relevant("title_vfx", context) is True


class TestAssetFilterTagFiltering:
    """Tests for tag-based asset filtering."""
    
    def test_filter_by_relevant_tags(self):
        """Test filtering by relevant tags."""
        filter_obj = AssetFilter()
        
        assets = [
            {"id": "mus_001", "tags": ["intro", "upbeat"]},
            {"id": "mus_002", "tags": ["outro", "calm"]},
            {"id": "mus_003", "tags": ["intro", "corporate"]},
        ]
        
        filtered = filter_obj._filter_by_tags(
            assets,
            ["intro"],
            "upbeat"
        )
        
        # Should return assets matching intro/upbeat
        assert len(filtered) >= 1
        assert any(a["id"] == "mus_001" for a in filtered)
    
    def test_tag_relevance_scoring(self):
        """Test tag relevance scoring."""
        filter_obj = AssetFilter()
        
        asset = {"id": "mus_001", "tags": ["intro", "upbeat", "corporate"]}
        search_tags = {"intro", "upbeat"}
        
        score = filter_obj._calculate_tag_relevance(asset, search_tags)
        assert score > 0.0
        # Should have good score since 2 of 3 tags match
        assert score >= 0.5


class TestAssetFilterByChunkContext:
    """Tests for full chunk context filtering."""
    
    def test_filter_assets_by_chunk_context(self):
        """Test complete chunk context filtering."""
        filter_obj = AssetFilter()
        
        asset_index = {
            "intro_music": [
                {"id": "mus_001", "tags": ["intro", "upbeat"]},
                {"id": "mus_002", "tags": ["intro", "epic"]},
            ],
            "outro_music": [
                {"id": "mus_003", "tags": ["outro", "calm"]},
            ],
        }
        
        context = ChunkContext(
            section_type="intro",
            tone="upbeat",
            required_categories=["intro_music"],
            time_range=(0.0, 60.0),
            relevant_tags=["intro", "upbeat"]
        )
        
        filtered = filter_obj.filter_assets_by_chunk_context(asset_index, context)
        
        # Should only include intro_music
        assert "intro_music" in filtered
        assert "outro_music" not in filtered
    
    def test_fallback_when_filtered_below_minimum(self):
        """Test fallback when filtering returns too few results."""
        filter_obj = AssetFilter(min_filtered_assets=5)
        
        # Create large asset library
        assets = [
            {"id": f"mus_{i:03d}", "tags": ["intro" if i % 2 == 0 else "outro"]}
            for i in range(20)
        ]
        
        asset_index = {"intro_music": assets}
        
        context = ChunkContext(
            section_type="intro",
            tone="upbeat",
            required_categories=["intro_music"],
            time_range=(0.0, 60.0),
            relevant_tags=["nonexistent_tag"]  # Tag that won't match
        )
        
        # Filtering by nonexistent tag should fallback to top assets
        filtered = filter_obj.filter_assets_by_chunk_context(asset_index, context)
        
        assert "intro_music" in filtered
        assert len(filtered["intro_music"]) >= filter_obj.min_filtered_assets


class TestBuildChunkContext:
    """Tests for building chunk context from format template."""
    
    def test_build_chunk_context_basic(self):
        """Test basic chunk context building."""
        filter_obj = AssetFilter()
        
        format_template = {
            "name": "Test Template",
            "sections": [
                {
                    "name": "intro",
                    "duration": 60,
                    "asset_categories": ["intro_music", "title_vfx"]
                }
            ]
        }
        
        context = filter_obj.build_chunk_context(
            section_name="intro",
            section_duration=60.0,
            start_time=0.0,
            format_template=format_template
        )
        
        assert context.section_type == "intro"
        assert "intro_music" in context.required_categories
        assert context.time_range == (0.0, 60.0)
    
    def test_infer_tone_from_section(self):
        """Test tone inference from section name."""
        filter_obj = AssetFilter()
        
        assert filter_obj._infer_tone_from_section("intro") == "upbeat"
        assert filter_obj._infer_tone_from_section("outro") == "triumphant"
        assert filter_obj._infer_tone_from_section("act_2") == "tense"
        assert filter_obj._infer_tone_from_section("unknown") == "corporate"


class TestBuildRelevantTags:
    """Tests for building relevant tags list."""
    
    def test_build_relevant_tags(self):
        """Test tag building from section, tone, and categories."""
        filter_obj = AssetFilter()
        
        tags = filter_obj._build_relevant_tags(
            section_name="intro",
            tone="upbeat",
            categories=["intro_music"]
        )
        
        # Should include section, tone, and category tags
        assert "intro" in [t.casefold() for t in tags]
        # Should include tone tags from TONE_TAG_MAP
        assert any(t.casefold() in ["upbeat", "energetic"] for t in tags)


class TestConstants:
    """Tests for module constants."""
    
    def test_section_category_map_exists(self):
        """Test that section category map is defined."""
        assert "intro" in SECTION_CATEGORY_MAP
        assert "outro" in SECTION_CATEGORY_MAP
        assert "narrative" in SECTION_CATEGORY_MAP
    
    def test_tone_tag_map_exists(self):
        """Test that tone tag map is defined."""
        assert "upbeat" in TONE_TAG_MAP
        assert "tense" in TONE_TAG_MAP
        assert "triumphant" in TONE_TAG_MAP
    
    def test_category_default_tags_exists(self):
        """Test that category default tags are defined."""
        assert "intro_music" in CATEGORY_DEFAULT_TAGS
        assert "narrative_music" in CATEGORY_DEFAULT_TAGS
