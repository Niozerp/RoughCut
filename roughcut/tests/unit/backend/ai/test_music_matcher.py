"""Unit tests for music matching functionality.

Tests the MusicMatcher class, SegmentTone dataclass, MusicMatch dataclass,
and all related music matching operations including tone analysis,
scoring, and edge cases.
"""

import pytest
from roughcut.backend.ai.music_matcher import MusicMatcher
from roughcut.backend.ai.music_match import (
    HIGH_CONFIDENCE_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
    MusicAsset,
    MusicMatch,
    MusicMatchingResult,
    SegmentMusicMatches
)
from roughcut.backend.ai.segment_tone import SegmentTone, TONE_TAG_MAPPINGS


class TestSegmentTone:
    """Test cases for SegmentTone dataclass."""
    
    def test_valid_segment_tone_creation(self):
        """Test creating a valid SegmentTone instance."""
        tone = SegmentTone(
            energy="high",
            mood="upbeat",
            genre_hint="corporate",
            keywords=["intro", "opening"],
            secondary_moods=["confident"]
        )
        
        assert tone.energy == "high"
        assert tone.mood == "upbeat"
        assert tone.genre_hint == "corporate"
        assert tone.keywords == ["intro", "opening"]
        assert tone.secondary_moods == ["confident"]
    
    def test_invalid_energy_level(self):
        """Test that invalid energy level raises ValueError."""
        with pytest.raises(ValueError, match="energy must be one of"):
            SegmentTone(
                energy="very_high",  # Invalid
                mood="upbeat",
                genre_hint="corporate"
            )
    
    def test_empty_mood_raises_error(self):
        """Test that empty mood raises ValueError."""
        with pytest.raises(ValueError, match="mood cannot be empty"):
            SegmentTone(
                energy="high",
                mood="",
                genre_hint="corporate"
            )
    
    def test_empty_genre_hint_raises_error(self):
        """Test that empty genre_hint raises ValueError."""
        with pytest.raises(ValueError, match="genre_hint cannot be empty"):
            SegmentTone(
                energy="high",
                mood="upbeat",
                genre_hint=""
            )
    
    def test_to_tag_query_basic(self):
        """Test basic tag query generation."""
        tone = SegmentTone(
            energy="high",
            mood="upbeat",
            genre_hint="corporate",
            keywords=["intro"]
        )
        
        tags = tone.to_tag_query()
        
        assert "upbeat" in tags
        assert "corporate" in tags
        assert "intro" in tags
        # Check mapped tags from TONE_TAG_MAPPINGS
        assert any(tag in tags for tag in TONE_TAG_MAPPINGS["corporate upbeat"])
    
    def test_to_tag_query_with_secondary_moods(self):
        """Test tag query includes secondary moods."""
        tone = SegmentTone(
            energy="medium",
            mood="contemplative",
            genre_hint="ambient",
            keywords=["narrative"],
            secondary_moods=["thoughtful", "reflective"]
        )
        
        tags = tone.to_tag_query()
        
        assert "contemplative" in tags
        assert "ambient" in tags
        assert "thoughtful" in tags
        assert "reflective" in tags
    
    def test_get_confidence_weight(self):
        """Test confidence weight calculation."""
        tone_with_keywords = SegmentTone(
            energy="high",
            mood="upbeat",
            genre_hint="corporate",
            keywords=["intro", "opening", "hook", "exciting"]
        )
        
        weight = tone_with_keywords.get_confidence_weight()
        assert 0.7 <= weight <= 1.0
    
    def test_to_dict_roundtrip(self):
        """Test to_dict and from_dict roundtrip conversion."""
        original = SegmentTone(
            energy="medium",
            mood="contemplative",
            genre_hint="ambient",
            keywords=["piano", "soft"],
            secondary_moods=["thoughtful"]
        )
        
        data = original.to_dict()
        restored = SegmentTone.from_dict(data)
        
        assert restored.energy == original.energy
        assert restored.mood == original.mood
        assert restored.genre_hint == original.genre_hint
        assert restored.keywords == original.keywords
        assert restored.secondary_moods == original.secondary_moods
    
    def test_from_dict_invalid_data(self):
        """Test from_dict with invalid data types."""
        with pytest.raises(ValueError, match="data cannot be None"):
            SegmentTone.from_dict(None)
        
        with pytest.raises(ValueError, match="data must be a dictionary"):
            SegmentTone.from_dict("not a dict")
        
        with pytest.raises(ValueError, match="keywords must be a list"):
            SegmentTone.from_dict({
                "energy": "high",
                "mood": "upbeat",
                "genre_hint": "corporate",
                "keywords": "not_a_list"
            })


class TestMusicAsset:
    """Test cases for MusicAsset dataclass."""
    
    def test_valid_music_asset_creation(self):
        """Test creating a valid MusicAsset instance."""
        asset = MusicAsset(
            music_id="music_001",
            file_path="/assets/music/Corporate/Upbeat/theme.wav",
            tags=["corporate", "upbeat"],
            folder_context="Corporate/Upbeat"
        )
        
        assert asset.music_id == "music_001"
        assert asset.file_path == "/assets/music/Corporate/Upbeat/theme.wav"
        assert asset.tags == ["corporate", "upbeat"]
        assert asset.category == "music"
        assert asset.folder_context == "Corporate/Upbeat"
    
    def test_empty_music_id_raises_error(self):
        """Test that empty music_id raises ValueError."""
        with pytest.raises(ValueError, match="music_id cannot be empty"):
            MusicAsset(
                music_id="",
                file_path="/path/to/file.wav",
                tags=["tag"]
            )
    
    def test_empty_file_path_raises_error(self):
        """Test that empty file_path raises ValueError."""
        with pytest.raises(ValueError, match="file_path cannot be empty"):
            MusicAsset(
                music_id="music_001",
                file_path="",
                tags=["tag"]
            )
    
    def test_invalid_tags_type(self):
        """Test that non-list tags raises ValueError."""
        with pytest.raises(ValueError, match="tags must be a list"):
            MusicAsset(
                music_id="music_001",
                file_path="/path/to/file.wav",
                tags="not_a_list"
            )
    
    def test_get_file_name(self):
        """Test extracting filename from path."""
        asset = MusicAsset(
            music_id="music_001",
            file_path="/assets/music/Corporate/theme.wav",
            tags=["corporate"]
        )
        
        assert asset.get_file_name() == "theme.wav"
    
    def test_from_dict_conversion(self):
        """Test from_dict class method."""
        data = {
            "id": "music_002",
            "file_path": "/assets/music/Ambient/soft.wav",
            "tags": ["ambient", "soft"],
            "category": "music",
            "folder_context": "Ambient"
        }
        
        asset = MusicAsset.from_dict(data)
        
        assert asset.music_id == "music_002"
        assert asset.file_path == "/assets/music/Ambient/soft.wav"
        assert asset.tags == ["ambient", "soft"]


class TestMusicMatch:
    """Test cases for MusicMatch dataclass."""
    
    def test_valid_music_match_creation(self):
        """Test creating a valid MusicMatch instance."""
        match = MusicMatch(
            music_id="music_001",
            file_path="/assets/theme.wav",
            file_name="theme.wav",
            folder_context="Corporate",
            match_reason="Tags match segment tone",
            confidence_score=0.92,
            matched_tags=["corporate", "upbeat"],
            suggested_start=0.0,
            suggested_end=14.8
        )
        
        assert match.music_id == "music_001"
        assert match.confidence_score == 0.92
        assert match.is_high_confidence() is True
    
    def test_confidence_score_validation(self):
        """Test that invalid confidence scores raise ValueError."""
        with pytest.raises(ValueError, match="confidence_score must be between"):
            MusicMatch(
                music_id="music_001",
                file_path="/path.wav",
                file_name="file.wav",
                folder_context="",
                match_reason="test",
                confidence_score=1.5,  # Invalid: > 1.0
                matched_tags=[]
            )
        
        with pytest.raises(ValueError, match="confidence_score must be between"):
            MusicMatch(
                music_id="music_001",
                file_path="/path.wav",
                file_name="file.wav",
                folder_context="",
                match_reason="test",
                confidence_score=-0.1,  # Invalid: < 0.0
                matched_tags=[]
            )
    
    def test_timestamp_validation(self):
        """Test that negative timestamps raise ValueError."""
        with pytest.raises(ValueError, match="suggested_start cannot be negative"):
            MusicMatch(
                music_id="music_001",
                file_path="/path.wav",
                file_name="file.wav",
                folder_context="",
                match_reason="test",
                confidence_score=0.8,
                matched_tags=[],
                suggested_start=-1.0
            )
    
    def test_is_high_confidence(self):
        """Test high confidence detection."""
        high_match = MusicMatch(
            music_id="music_001",
            file_path="/path.wav",
            file_name="file.wav",
            folder_context="",
            match_reason="test",
            confidence_score=HIGH_CONFIDENCE_THRESHOLD,
            matched_tags=[]
        )
        assert high_match.is_high_confidence() is True
        
        low_match = MusicMatch(
            music_id="music_002",
            file_path="/path.wav",
            file_name="file.wav",
            folder_context="",
            match_reason="test",
            confidence_score=LOW_CONFIDENCE_THRESHOLD - 0.1,
            matched_tags=[]
        )
        assert low_match.is_high_confidence() is False
        assert low_match.is_low_confidence() is True
    
    def test_format_suggestion(self):
        """Test formatting match as suggestion string."""
        match = MusicMatch(
            music_id="music_001",
            file_path="/assets/Corporate/theme.wav",
            file_name="theme.wav",
            folder_context="Corporate",
            match_reason="Good match",
            confidence_score=0.92,
            matched_tags=["corporate"]
        )
        
        suggestion = match.format_suggestion()
        assert "theme.wav" in suggestion
        assert "Corporate" in suggestion
    
    def test_format_match_details(self):
        """Test formatting match details."""
        match = MusicMatch(
            music_id="music_001",
            file_path="/assets/theme.wav",
            file_name="theme.wav",
            folder_context="",
            match_reason="test",
            confidence_score=0.92,
            matched_tags=["corporate", "upbeat", "bright"]
        )
        
        details = match.format_match_details()
        assert "92%" in details
        assert "corporate" in details
        assert "upbeat" in details


class TestMusicMatcher:
    """Test cases for MusicMatcher class."""
    
    def test_matcher_initialization(self):
        """Test MusicMatcher initialization with defaults."""
        matcher = MusicMatcher()
        
        assert matcher.max_suggestions == 3
        assert matcher.min_confidence_threshold == 0.60
    
    def test_matcher_custom_settings(self):
        """Test MusicMatcher with custom settings."""
        matcher = MusicMatcher(max_suggestions=5, min_confidence_threshold=0.70)
        
        assert matcher.max_suggestions == 5
        assert matcher.min_confidence_threshold == 0.70
    
    def test_analyze_segment_tone_basic(self):
        """Test basic segment tone analysis."""
        matcher = MusicMatcher()
        
        tone = matcher.analyze_segment_tone(
            segment_text="Welcome to our corporate overview today.",
            segment_name="intro"
        )
        
        assert tone.energy == "high"
        assert tone.mood == "upbeat"
        assert tone.genre_hint == "corporate"
    
    def test_analyze_segment_tone_narrative(self):
        """Test tone analysis for narrative segments."""
        matcher = MusicMatcher()
        
        tone = matcher.analyze_segment_tone(
            segment_text="The challenges we faced were significant and difficult.",
            segment_name="narrative_1"
        )
        
        assert tone.mood == "contemplative"
        assert tone.genre_hint == "ambient"
    
    def test_analyze_segment_tone_with_ai_data(self):
        """Test tone analysis using AI-provided tone data."""
        matcher = MusicMatcher()
        
        ai_tone_data = {
            "energy": "medium",
            "mood": "triumphant",
            "genre_hint": "orchestral",
            "keywords": ["victory", "success"]
        }
        
        tone = matcher.analyze_segment_tone(
            segment_text="Some text here.",
            segment_name="outro",
            ai_tone_data=ai_tone_data
        )
        
        assert tone.energy == "medium"
        assert tone.mood == "triumphant"
        assert tone.genre_hint == "orchestral"
    
    def test_analyze_segment_tone_empty_text_raises(self):
        """Test that empty segment text raises ValueError."""
        matcher = MusicMatcher()
        
        with pytest.raises(ValueError, match="segment_text cannot be empty"):
            matcher.analyze_segment_tone("", "intro")
    
    def test_match_music_to_segments_basic(self):
        """Test basic music matching to segments."""
        matcher = MusicMatcher(max_suggestions=2, min_confidence_threshold=0.3)
        
        segments = [
            {
                "section_name": "intro",
                "start_time": 0.0,
                "end_time": 15.0,
                "text": "Welcome to our corporate overview."
            }
        ]
        
        music_index = [
            {
                "id": "music_001",
                "file_path": "/assets/Corporate/theme.wav",
                "tags": ["corporate", "upbeat"],
                "folder_context": "Corporate"
            },
            {
                "id": "music_002",
                "file_path": "/assets/Ambient/soft.wav",
                "tags": ["ambient", "soft"],
                "folder_context": "Ambient"
            }
        ]
        
        result = matcher.match_music_to_segments(segments, music_index)
        
        assert isinstance(result, MusicMatchingResult)
        assert len(result.segment_matches) == 1
        assert result.total_matches > 0
        assert result.average_confidence > 0
    
    def test_match_music_to_segments_empty_segments_raises(self):
        """Test that empty segments raises ValueError."""
        matcher = MusicMatcher()
        
        with pytest.raises(ValueError, match="segments cannot be empty"):
            matcher.match_music_to_segments([], [])
    
    def test_match_music_to_segments_empty_music_raises(self):
        """Test that empty music index raises ValueError."""
        matcher = MusicMatcher()
        
        segments = [{"section_name": "intro", "text": "Welcome"}]
        
        with pytest.raises(ValueError, match="music_index cannot be empty"):
            matcher.match_music_to_segments(segments, [])
    
    def test_match_music_to_segments_invalid_assets_skipped(self):
        """Test that invalid music assets are skipped gracefully."""
        matcher = MusicMatcher()
        
        segments = [
            {
                "section_name": "intro",
                "text": "Welcome",
                "start_time": 0.0,
                "end_time": 10.0
            }
        ]
        
        # Mix of valid and invalid assets
        music_index = [
            {
                "id": "valid_001",
                "file_path": "/valid/path.wav",
                "tags": ["corporate"]
            },
            {
                # Invalid - missing id
                "file_path": "/invalid/path.wav",
                "tags": ["ambient"]
            },
            {
                # Invalid - missing file_path
                "id": "invalid_002",
                "tags": ["soft"]
            }
        ]
        
        result = matcher.match_music_to_segments(segments, music_index)
        
        # Should still work with only valid assets
        assert isinstance(result, MusicMatchingResult)
    
    def test_calculate_match_score_exact_match(self):
        """Test scoring with exact tag match."""
        matcher = MusicMatcher()
        
        tone = SegmentTone(
            energy="high",
            mood="upbeat",
            genre_hint="corporate",
            keywords=["intro"]
        )
        
        asset = MusicAsset(
            music_id="music_001",
            file_path="/path.wav",
            tags=["corporate", "upbeat", "intro"],
            folder_context="Corporate"
        )
        
        search_tags = tone.to_tag_query()
        score, matched_tags = matcher._calculate_match_score(tone, asset, search_tags)
        
        assert score > 0.6  # Good score for exact matches (scoring accounts for tag expansion)
        assert "corporate" in matched_tags
        assert "upbeat" in matched_tags
    
    def test_calculate_match_score_no_match(self):
        """Test scoring with no matching tags."""
        matcher = MusicMatcher()
        
        tone = SegmentTone(
            energy="high",
            mood="upbeat",
            genre_hint="corporate"
        )
        
        asset = MusicAsset(
            music_id="music_001",
            file_path="/path.wav",
            tags=["tension", "dark", "suspense"]  # No overlap
        )
        
        search_tags = tone.to_tag_query()
        score, matched_tags = matcher._calculate_match_score(tone, asset, search_tags)
        
        assert score == 0.0
        assert len(matched_tags) == 0
    
    def test_prevent_duplicate_matches(self):
        """Test duplicate match prevention across segments."""
        matcher = MusicMatcher()
        
        # Create result with duplicate matches
        tone1 = SegmentTone(energy="high", mood="upbeat", genre_hint="corporate")
        tone2 = SegmentTone(energy="medium", mood="neutral", genre_hint="corporate")
        
        match1 = MusicMatch(
            music_id="same_id",
            file_path="/path.wav",
            file_name="file.wav",
            folder_context="",
            match_reason="test",
            confidence_score=0.90,
            matched_tags=["corporate"]
        )
        
        match2 = MusicMatch(
            music_id="same_id",  # Duplicate
            file_path="/path.wav",
            file_name="file.wav",
            folder_context="",
            match_reason="test",
            confidence_score=0.70,
            matched_tags=["corporate"]
        )
        
        segment_matches = [
            SegmentMusicMatches(
                segment_name="segment_1",
                segment_tone=tone1,
                matches=[match1]
            ),
            SegmentMusicMatches(
                segment_name="segment_2",
                segment_tone=tone2,
                matches=[match2]
            )
        ]
        
        result = MusicMatchingResult(
            segment_matches=segment_matches,
            total_matches=2,
            average_confidence=0.80,
            fallback_used=False
        )
        
        # Prevent duplicates
        result = matcher.prevent_duplicate_matches(result)
        
        # One of the duplicates should be removed
        total_matches_after = sum(len(sm.matches) for sm in result.segment_matches)
        assert total_matches_after == 1
    
    def test_generate_match_reason(self):
        """Test match reason generation."""
        matcher = MusicMatcher()
        
        tone = SegmentTone(
            energy="high",
            mood="upbeat",
            genre_hint="corporate"
        )
        
        asset = MusicAsset(
            music_id="music_001",
            file_path="/corporate/theme.wav",
            tags=["corporate", "upbeat"],
            folder_context="Corporate"
        )
        
        reason = matcher._generate_match_reason(tone, asset, ["corporate", "upbeat"], 0.92)
        
        assert "corporate" in reason or "upbeat" in reason
        assert "high" in reason or "energy" in reason
    
    def test_get_used_music_ids(self):
        """Test extracting used music IDs from result."""
        matcher = MusicMatcher()
        
        tone = SegmentTone(energy="high", mood="upbeat", genre_hint="corporate")
        
        match1 = MusicMatch(
            music_id="id_001",
            file_path="/path1.wav",
            file_name="file1.wav",
            folder_context="",
            match_reason="test",
            confidence_score=0.90,
            matched_tags=[]
        )
        
        match2 = MusicMatch(
            music_id="id_002",
            file_path="/path2.wav",
            file_name="file2.wav",
            folder_context="",
            match_reason="test",
            confidence_score=0.80,
            matched_tags=[]
        )
        
        segment_matches = [
            SegmentMusicMatches(
                segment_name="seg1",
                segment_tone=tone,
                matches=[match1, match2]
            )
        ]
        
        result = MusicMatchingResult(
            segment_matches=segment_matches,
            total_matches=2,
            average_confidence=0.85,
            fallback_used=False
        )
        
        used_ids = matcher.get_used_music_ids(result)
        
        assert "id_001" in used_ids
        assert "id_002" in used_ids


class TestMusicMatchingResult:
    """Test cases for MusicMatchingResult dataclass."""
    
    def test_result_creation(self):
        """Test creating a MusicMatchingResult."""
        tone = SegmentTone(energy="high", mood="upbeat", genre_hint="corporate")
        
        match = MusicMatch(
            music_id="music_001",
            file_path="/path.wav",
            file_name="file.wav",
            folder_context="",
            match_reason="test",
            confidence_score=0.90,
            matched_tags=["corporate"]
        )
        
        segment_matches = [
            SegmentMusicMatches(
                segment_name="intro",
                segment_tone=tone,
                matches=[match]
            )
        ]
        
        result = MusicMatchingResult(
            segment_matches=segment_matches,
            total_matches=1,
            average_confidence=0.90,
            fallback_used=False,
            warnings=[]
        )
        
        assert result.total_matches == 1
        assert result.average_confidence == 0.90
        assert result.fallback_used is False
    
    def test_result_recalculates_statistics(self):
        """Test that result recalculates statistics on init."""
        tone = SegmentTone(energy="high", mood="upbeat", genre_hint="corporate")
        
        match1 = MusicMatch(
            music_id="music_001",
            file_path="/path1.wav",
            file_name="file1.wav",
            folder_context="",
            match_reason="test",
            confidence_score=0.90,
            matched_tags=[]
        )
        
        match2 = MusicMatch(
            music_id="music_002",
            file_path="/path2.wav",
            file_name="file2.wav",
            folder_context="",
            match_reason="test",
            confidence_score=0.70,
            matched_tags=[]
        )
        
        segment_matches = [
            SegmentMusicMatches(
                segment_name="intro",
                segment_tone=tone,
                matches=[match1, match2]
            )
        ]
        
        # Pass wrong statistics - should be recalculated
        result = MusicMatchingResult(
            segment_matches=segment_matches,
            total_matches=999,  # Wrong
            average_confidence=0.50,  # Wrong
            fallback_used=False
        )
        
        # Should be recalculated to correct values
        assert result.total_matches == 2
        assert result.average_confidence == 0.80  # (0.90 + 0.70) / 2
    
    def test_get_all_matches(self):
        """Test getting all matches across segments."""
        tone = SegmentTone(energy="high", mood="upbeat", genre_hint="corporate")
        
        match = MusicMatch(
            music_id="music_001",
            file_path="/path.wav",
            file_name="file.wav",
            folder_context="",
            match_reason="test",
            confidence_score=0.90,
            matched_tags=[]
        )
        
        segment_matches = [
            SegmentMusicMatches(
                segment_name="intro",
                segment_tone=tone,
                matches=[match]
            )
        ]
        
        result = MusicMatchingResult(
            segment_matches=segment_matches,
            total_matches=1,
            average_confidence=0.90,
            fallback_used=False
        )
        
        all_matches = result.get_all_matches()
        assert len(all_matches) == 1
        assert all_matches[0].music_id == "music_001"
    
    def test_get_low_confidence_warnings(self):
        """Test extracting low confidence warnings."""
        tone = SegmentTone(energy="high", mood="upbeat", genre_hint="corporate")
        
        # Create a match below threshold
        low_match = MusicMatch(
            music_id="music_001",
            file_path="/path.wav",
            file_name="file.wav",
            folder_context="",
            match_reason="test",
            confidence_score=0.50,  # Below threshold
            matched_tags=[]
        )
        
        segment_matches = [
            SegmentMusicMatches(
                segment_name="intro",
                segment_tone=tone,
                matches=[low_match]
            )
        ]
        
        result = MusicMatchingResult(
            segment_matches=segment_matches,
            total_matches=1,
            average_confidence=0.50,
            fallback_used=False
        )
        
        warnings = result.get_low_confidence_warnings()
        assert len(warnings) == 1
        assert "intro" in warnings[0]


class TestSegmentMusicMatches:
    """Test cases for SegmentMusicMatches dataclass."""
    
    def test_top_match_selection(self):
        """Test selecting top match from sorted list."""
        tone = SegmentTone(energy="high", mood="upbeat", genre_hint="corporate")
        
        match1 = MusicMatch(
            music_id="music_001",
            file_path="/path1.wav",
            file_name="file1.wav",
            folder_context="",
            match_reason="test",
            confidence_score=0.70,
            matched_tags=[]
        )
        
        match2 = MusicMatch(
            music_id="music_002",
            file_path="/path2.wav",
            file_name="file2.wav",
            folder_context="",
            match_reason="test",
            confidence_score=0.90,
            matched_tags=[]
        )
        
        segment_matches = SegmentMusicMatches(
            segment_name="intro",
            segment_tone=tone,
            matches=[match1, match2]  # Intentionally out of order
        )
        
        top = segment_matches.top_match()
        assert top.music_id == "music_002"  # Higher confidence should be first
        assert top.confidence_score == 0.90
    
    def test_get_high_confidence_matches(self):
        """Test filtering high confidence matches."""
        tone = SegmentTone(energy="high", mood="upbeat", genre_hint="corporate")
        
        high_match = MusicMatch(
            music_id="music_001",
            file_path="/path1.wav",
            file_name="file1.wav",
            folder_context="",
            match_reason="test",
            confidence_score=0.90,  # High
            matched_tags=[]
        )
        
        low_match = MusicMatch(
            music_id="music_002",
            file_path="/path2.wav",
            file_name="file2.wav",
            folder_context="",
            match_reason="test",
            confidence_score=0.50,  # Low
            matched_tags=[]
        )
        
        segment_matches = SegmentMusicMatches(
            segment_name="intro",
            segment_tone=tone,
            matches=[high_match, low_match]
        )
        
        high_confidence = segment_matches.get_high_confidence_matches()
        assert len(high_confidence) == 1
        assert high_confidence[0].music_id == "music_001"
    
    def test_has_good_matches(self):
        """Test checking for viable matches."""
        tone = SegmentTone(energy="high", mood="upbeat", genre_hint="corporate")
        
        # Good match
        good_match = MusicMatch(
            music_id="music_001",
            file_path="/path1.wav",
            file_name="file1.wav",
            folder_context="",
            match_reason="test",
            confidence_score=0.80,
            matched_tags=[]
        )
        
        segment_matches = SegmentMusicMatches(
            segment_name="intro",
            segment_tone=tone,
            matches=[good_match]
        )
        
        assert segment_matches.has_good_matches() is True
        
        # No good matches
        bad_match = MusicMatch(
            music_id="music_002",
            file_path="/path2.wav",
            file_name="file2.wav",
            folder_context="",
            match_reason="test",
            confidence_score=0.50,
            matched_tags=[]
        )
        
        segment_matches_bad = SegmentMusicMatches(
            segment_name="intro",
            segment_tone=tone,
            matches=[bad_match]
        )
        
        assert segment_matches_bad.has_good_matches() is False


class TestToneTagMappings:
    """Test cases for tone-to-tag mappings."""
    
    def test_tone_tag_mappings_exist(self):
        """Test that required tone mappings exist."""
        required_mappings = [
            "corporate upbeat",
            "contemplative",
            "triumphant",
            "tense",
            "emotional",
            "energetic",
            "calm"
        ]
        
        for mapping in required_mappings:
            assert mapping in TONE_TAG_MAPPINGS, f"Missing mapping: {mapping}"
    
    def test_tone_tag_mappings_have_values(self):
        """Test that all mappings have non-empty tag lists."""
        for tone, tags in TONE_TAG_MAPPINGS.items():
            assert len(tags) > 0, f"Empty tag list for: {tone}"
            assert all(isinstance(tag, str) for tag in tags)
