"""Unit tests for SFX matching components.

Tests the SFXMatcher class, SFXMoment dataclass, SFXMatch dataclass,
and related data structures for sound effect matching functionality.
"""

from __future__ import annotations

import pytest
from typing import Any

from roughcut.backend.ai.sfx_matcher import SFXMatcher
from roughcut.backend.ai.sfx_match import (
    SFXAsset,
    SFXMatch,
    SFXMatchingResult,
    MomentSFXMatches,
    HIGH_CONFIDENCE_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
    HIGH_SUBTLETY_THRESHOLD
)
from roughcut.backend.ai.sfx_moment import (
    SFXMoment,
    SFXMomentList,
    SFX_MOMENT_MAPPINGS,
    INTENSITY_SUBTLETY_PREFERENCE
)


class TestSFXMoment:
    """Test cases for SFXMoment dataclass."""
    
    def test_create_valid_moment(self):
        """Test creating a valid SFXMoment."""
        moment = SFXMoment(
            timestamp=10.5,
            type="intro",
            context="opening transition",
            intensity="medium",
            segment_name="intro_segment"
        )
        
        assert moment.timestamp == 10.5
        assert moment.type == "intro"
        assert moment.context == "opening transition"
        assert moment.intensity == "medium"
        assert moment.segment_name == "intro_segment"
    
    def test_moment_validation_negative_timestamp(self):
        """Test that negative timestamp raises ValueError."""
        with pytest.raises(ValueError, match="timestamp cannot be negative"):
            SFXMoment(
                timestamp=-1.0,
                type="intro",
                context="opening",
                intensity="medium",
                segment_name="test"
            )
    
    def test_moment_validation_invalid_type(self):
        """Test that invalid moment type raises ValueError."""
        with pytest.raises(ValueError, match="type must be one of"):
            SFXMoment(
                timestamp=10.0,
                type="invalid_type",
                context="opening",
                intensity="medium",
                segment_name="test"
            )
    
    def test_moment_validation_invalid_intensity(self):
        """Test that invalid intensity raises ValueError."""
        with pytest.raises(ValueError, match="intensity must be one of"):
            SFXMoment(
                timestamp=10.0,
                type="intro",
                context="opening",
                intensity="extreme",
                segment_name="test"
            )
    
    def test_moment_validation_empty_context(self):
        """Test that empty context raises ValueError."""
        with pytest.raises(ValueError, match="context cannot be empty"):
            SFXMoment(
                timestamp=10.0,
                type="intro",
                context="",
                intensity="medium",
                segment_name="test"
            )
    
    def test_moment_validation_empty_segment_name(self):
        """Test that empty segment name raises ValueError."""
        with pytest.raises(ValueError, match="segment_name cannot be empty"):
            SFXMoment(
                timestamp=10.0,
                type="intro",
                context="opening",
                intensity="medium",
                segment_name=""
            )
    
    def test_to_tag_query(self):
        """Test tag query generation from moment type."""
        moment = SFXMoment(
            timestamp=10.0,
            type="transition",
            context="scene change",
            intensity="medium",
            segment_name="test"
        )
        
        tags = moment.to_tag_query()
        assert "transition" in tags
        assert "whoosh" in tags
        assert isinstance(tags, list)
    
    def test_get_subtlety_preference(self):
        """Test subtlety preference based on intensity."""
        low_moment = SFXMoment(
            timestamp=10.0,
            type="underscore",
            context="background",
            intensity="low",
            segment_name="test"
        )
        assert low_moment.get_subtlety_preference() == 0.85
        
        high_moment = SFXMoment(
            timestamp=10.0,
            type="emphasis",
            context="impact",
            intensity="high",
            segment_name="test"
        )
        assert high_moment.get_subtlety_preference() == 0.50
    
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        moment = SFXMoment(
            timestamp=150.5,  # 2:30.5
            type="intro",
            context="opening",
            intensity="medium",
            segment_name="test"
        )
        assert moment.format_timestamp() == "2:30"
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        moment = SFXMoment(
            timestamp=10.0,
            type="intro",
            context="opening",
            intensity="medium",
            segment_name="test"
        )
        
        data = moment.to_dict()
        assert data["timestamp"] == 10.0
        assert data["type"] == "intro"
        assert data["context"] == "opening"
        assert data["intensity"] == "medium"
        assert data["segment_name"] == "test"
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "timestamp": 10.0,
            "type": "intro",
            "context": "opening",
            "intensity": "medium",
            "segment_name": "test"
        }
        
        moment = SFXMoment.from_dict(data)
        assert moment.timestamp == 10.0
        assert moment.type == "intro"
    
    def test_from_dict_invalid_data(self):
        """Test from_dict with invalid data."""
        with pytest.raises(ValueError, match="data cannot be None"):
            SFXMoment.from_dict(None)
        
        with pytest.raises(ValueError, match="data must be a dictionary"):
            SFXMoment.from_dict("invalid")


class TestSFXAsset:
    """Test cases for SFXAsset dataclass."""
    
    def test_create_valid_asset(self):
        """Test creating a valid SFXAsset."""
        asset = SFXAsset(
            sfx_id="sfx_001",
            file_path="/assets/sfx/intro/whoosh.wav",
            tags=["intro", "whoosh"],
            folder_context="sfx/intro",
            duration_ms=1500
        )
        
        assert asset.sfx_id == "sfx_001"
        assert asset.file_path == "/assets/sfx/intro/whoosh.wav"
        assert asset.tags == ["intro", "whoosh"]
        assert asset.category == "sfx"
        assert asset.folder_context == "sfx/intro"
        assert asset.duration_ms == 1500
    
    def test_asset_validation_empty_sfx_id(self):
        """Test that empty sfx_id raises ValueError."""
        with pytest.raises(ValueError, match="sfx_id cannot be empty"):
            SFXAsset(
                sfx_id="",
                file_path="/path/to/file.wav",
                tags=["tag"]
            )
    
    def test_asset_validation_empty_file_path(self):
        """Test that empty file_path raises ValueError."""
        with pytest.raises(ValueError, match="file_path cannot be empty"):
            SFXAsset(
                sfx_id="sfx_001",
                file_path="",
                tags=["tag"]
            )
    
    def test_asset_validation_invalid_duration(self):
        """Test that negative duration raises ValueError."""
        with pytest.raises(ValueError, match="duration_ms cannot be negative"):
            SFXAsset(
                sfx_id="sfx_001",
                file_path="/path/to/file.wav",
                tags=["tag"],
                duration_ms=-100
            )
    
    def test_get_file_name(self):
        """Test filename extraction from path."""
        asset = SFXAsset(
            sfx_id="sfx_001",
            file_path="/assets/sfx/intro/whoosh.wav",
            tags=["intro"]
        )
        assert asset.get_file_name() == "whoosh.wav"
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "id": "sfx_001",
            "file_path": "/assets/sfx/intro/whoosh.wav",
            "tags": ["intro", "whoosh"],
            "category": "sfx",
            "folder_context": "sfx/intro",
            "duration_ms": 1500
        }
        
        asset = SFXAsset.from_dict(data)
        assert asset.sfx_id == "sfx_001"
        assert asset.duration_ms == 1500


class TestSFXMatch:
    """Test cases for SFXMatch dataclass."""
    
    def test_create_valid_match(self):
        """Test creating a valid SFXMatch."""
        match = SFXMatch(
            sfx_id="sfx_001",
            file_path="/assets/sfx/intro/whoosh.wav",
            file_name="whoosh.wav",
            folder_context="sfx/intro",
            match_reason="Tags match moment type",
            confidence_score=0.85,
            matched_tags=["intro", "whoosh"],
            suggested_at=10.0,
            duration_ms=1500,
            subtlety_score=0.80
        )
        
        assert match.sfx_id == "sfx_001"
        assert match.confidence_score == 0.85
        assert match.is_high_confidence()
        assert match.is_subtle()
    
    def test_match_validation_confidence_range(self):
        """Test confidence score range validation."""
        with pytest.raises(ValueError, match="confidence_score must be between"):
            SFXMatch(
                sfx_id="sfx_001",
                file_path="/path/file.wav",
                file_name="file.wav",
                folder_context="sfx",
                match_reason="test",
                confidence_score=1.5,  # Invalid
                matched_tags=["tag"]
            )
    
    def test_match_validation_subtlety_range(self):
        """Test subtlety score range validation."""
        with pytest.raises(ValueError, match="subtlety_score must be between"):
            SFXMatch(
                sfx_id="sfx_001",
                file_path="/path/file.wav",
                file_name="file.wav",
                folder_context="sfx",
                match_reason="test",
                confidence_score=0.5,
                matched_tags=["tag"],
                subtlety_score=-0.1  # Invalid
            )
    
    def test_is_low_confidence(self):
        """Test low confidence detection."""
        match = SFXMatch(
            sfx_id="sfx_001",
            file_path="/path/file.wav",
            file_name="file.wav",
            folder_context="sfx",
            match_reason="test",
            confidence_score=0.50,  # Below threshold
            matched_tags=["tag"]
        )
        assert match.is_low_confidence()
        assert not match.is_high_confidence()
    
    def test_format_suggestion(self):
        """Test suggestion formatting."""
        match = SFXMatch(
            sfx_id="sfx_001",
            file_path="/path/whoosh.wav",
            file_name="whoosh.wav",
            folder_context="sfx",
            match_reason="test",
            confidence_score=0.85,
            matched_tags=["intro"],
            suggested_at=65.0  # 1:05
        )
        
        suggestion = match.format_suggestion()
        assert "whoosh.wav" in suggestion
        assert "1:05" in suggestion
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        match = SFXMatch(
            sfx_id="sfx_001",
            file_path="/path/file.wav",
            file_name="file.wav",
            folder_context="sfx",
            match_reason="test",
            confidence_score=0.85,
            matched_tags=["tag"]
        )
        
        data = match.to_dict()
        assert data["sfx_id"] == "sfx_001"
        assert data["confidence_score"] == 0.85


class TestSFXMatcher:
    """Test cases for SFXMatcher class."""
    
    def test_create_matcher(self):
        """Test creating SFXMatcher with defaults."""
        matcher = SFXMatcher()
        assert matcher.max_suggestions == 3
        assert matcher.min_confidence_threshold == 0.60
        assert matcher.track_usage_history is True
    
    def test_create_matcher_custom_params(self):
        """Test creating SFXMatcher with custom parameters."""
        matcher = SFXMatcher(
            max_suggestions=5,
            min_confidence_threshold=0.70,
            track_usage_history=False
        )
        assert matcher.max_suggestions == 5
        assert matcher.min_confidence_threshold == 0.70
        assert matcher.track_usage_history is False
    
    def test_identify_sfx_moments_empty_segments(self):
        """Test that empty segments raises ValueError."""
        matcher = SFXMatcher()
        with pytest.raises(ValueError, match="segments cannot be empty"):
            matcher.identify_sfx_moments([])
    
    def test_identify_sfx_moments_intro(self):
        """Test identifying intro moment."""
        matcher = SFXMatcher()
        segments = [
            {
                "section_name": "intro",
                "start_time": 0.0,
                "end_time": 15.0,
                "text": "Welcome to our presentation",
                "tone": {"energy": "high", "mood": "upbeat"}
            }
        ]
        
        moments = matcher.identify_sfx_moments(segments)
        assert len(moments) == 1
        assert moments[0].type == "intro"
        assert moments[0].timestamp == 0.0
    
    def test_identify_sfx_moments_outro(self):
        """Test identifying outro moment."""
        matcher = SFXMatcher()
        segments = [
            {
                "section_name": "outro",
                "start_time": 120.0,
                "end_time": 150.0,
                "text": "Thank you for watching",
                "tone": {"energy": "high", "mood": "triumphant"}
            }
        ]
        
        moments = matcher.identify_sfx_moments(segments)
        assert len(moments) == 1
        assert moments[0].type == "outro"
        assert moments[0].timestamp == 148.0  # end_time - 2.0
    
    def test_identify_sfx_moments_triumph(self):
        """Test identifying triumph moment."""
        matcher = SFXMatcher()
        segments = [
            {
                "section_name": "narrative_1",
                "start_time": 30.0,
                "end_time": 90.0,
                "text": "We achieved great success in this project",
                "tone": {"energy": "high", "mood": "triumphant"}
            }
        ]
        
        moments = matcher.identify_sfx_moments(segments)
        triumph_moments = [m for m in moments if m.type == "triumph"]
        assert len(triumph_moments) == 1
    
    def test_identify_sfx_moments_emphasis(self):
        """Test identifying emphasis moment."""
        matcher = SFXMatcher()
        segments = [
            {
                "section_name": "narrative_1",
                "start_time": 30.0,
                "end_time": 90.0,
                "text": "However, we faced a significant challenge",
                "tone": {"energy": "medium", "mood": "contemplative"}
            }
        ]
        
        moments = matcher.identify_sfx_moments(segments)
        emphasis_moments = [m for m in moments if m.type == "emphasis"]
        assert len(emphasis_moments) == 1
    
    def test_identify_sfx_moments_underscore(self):
        """Test identifying underscore moment for long segments."""
        matcher = SFXMatcher()
        segments = [
            {
                "section_name": "narrative_1",
                "start_time": 0.0,
                "end_time": 60.0,  # > 30 seconds
                "text": "This is a long narrative section with various content",
                "tone": {"energy": "medium", "mood": "neutral"}
            }
        ]
        
        moments = matcher.identify_sfx_moments(segments)
        underscore_moments = [m for m in moments if m.type == "underscore"]
        assert len(underscore_moments) == 1
    
    def test_match_sfx_to_moments_empty_moments(self):
        """Test that empty moments raises ValueError."""
        matcher = SFXMatcher()
        with pytest.raises(ValueError, match="moments cannot be empty"):
            matcher.match_sfx_to_moments([], [])
    
    def test_match_sfx_to_moments_empty_index(self):
        """Test that empty SFX index raises ValueError."""
        matcher = SFXMatcher()
        moments = [SFXMoment(10.0, "intro", "opening", "medium", "seg1")]
        with pytest.raises(ValueError, match="sfx_index cannot be empty"):
            matcher.match_sfx_to_moments(moments, [])
    
    def test_match_sfx_to_moments_success(self):
        """Test successful SFX matching."""
        matcher = SFXMatcher()
        
        moments = [
            SFXMoment(0.0, "intro", "opening", "medium", "seg1"),
            SFXMoment(60.0, "outro", "closing", "medium", "seg2")
        ]
        
        sfx_index = [
            {
                "id": "sfx_001",
                "file_path": "/sfx/intro/whoosh.wav",
                "tags": ["intro", "whoosh", "transition"],
                "folder_context": "sfx/intro",
                "duration_ms": 1500
            },
            {
                "id": "sfx_002",
                "file_path": "/sfx/outro/chime.wav",
                "tags": ["outro", "chime", "ending"],
                "folder_context": "sfx/outro",
                "duration_ms": 2000
            }
        ]
        
        result = matcher.match_sfx_to_moments(moments, sfx_index)
        
        assert isinstance(result, SFXMatchingResult)
        assert len(result.moment_matches) == 2
        assert result.total_matches > 0
        assert result.layer_guidance is not None
    
    def test_match_sfx_with_confidence(self):
        """Test SFX matching produces confidence scores."""
        matcher = SFXMatcher()
        
        moments = [SFXMoment(0.0, "intro", "opening", "medium", "seg1")]
        
        sfx_index = [
            {
                "id": "sfx_001",
                "file_path": "/sfx/intro/whoosh.wav",
                "tags": ["intro", "whoosh", "transition", "opening", "start"],
                "folder_context": "sfx/intro",
                "duration_ms": 1500
            }
        ]
        
        result = matcher.match_sfx_to_moments(moments, sfx_index)
        
        # Should have high confidence matches
        assert result.average_confidence > 0.0
        assert len(result.moment_matches[0].matches) > 0
        assert result.moment_matches[0].matches[0].confidence_score > 0.0
    
    def test_prevent_duplicate_matches(self):
        """Test duplicate SFX prevention."""
        matcher = SFXMatcher()
        
        # Create result with duplicate matches
        moment1 = SFXMoment(0.0, "intro", "opening", "medium", "seg1")
        moment2 = SFXMoment(10.0, "transition", "change", "medium", "seg2")
        
        match1 = SFXMatch(
            sfx_id="sfx_001",
            file_path="/sfx/whoosh.wav",
            file_name="whoosh.wav",
            folder_context="sfx",
            match_reason="Good match",
            confidence_score=0.90,
            matched_tags=["intro"],
            suggested_at=0.0
        )
        
        match2 = SFXMatch(
            sfx_id="sfx_001",  # Same ID - duplicate
            file_path="/sfx/whoosh.wav",
            file_name="whoosh.wav",
            folder_context="sfx",
            match_reason="Also good",
            confidence_score=0.70,
            matched_tags=["transition"],
            suggested_at=10.0
        )
        
        result = SFXMatchingResult(
            moment_matches=[
                MomentSFXMatches(moment1, [match1]),
                MomentSFXMatches(moment2, [match2])
            ],
            total_matches=2,
            average_confidence=0.80,
            average_subtlety=0.70,
            fallback_used=False,
            layer_guidance="test"
        )
        
        # Prevent duplicates - should keep higher confidence
        filtered_result = matcher.prevent_duplicate_matches(result)
        
        # One match should be removed
        total_after = sum(len(mm.matches) for mm in filtered_result.moment_matches)
        assert total_after == 1
    
    def test_usage_history(self):
        """Test usage history tracking."""
        matcher = SFXMatcher()
        
        # Record usage
        matcher.record_usage("sfx_001")
        assert matcher.is_recently_used("sfx_001")
        assert not matcher.is_recently_used("sfx_002")
        
        # Clear history
        matcher.clear_usage_history()
        assert not matcher.is_recently_used("sfx_001")
    
    def test_usage_penalty(self):
        """Test that recently used assets get score penalty."""
        matcher = SFXMatcher()
        
        # Record usage
        matcher.record_usage("sfx_001")
        
        # Check penalty is applied
        base_score = 0.90
        adjusted_score = matcher._apply_usage_penalty("sfx_001", base_score)
        assert adjusted_score == base_score * 0.85  # 15% penalty
        
        # Check no penalty for unused
        adjusted_score2 = matcher._apply_usage_penalty("sfx_002", base_score)
        assert adjusted_score2 == base_score


class TestSFXMatchingResult:
    """Test cases for SFXMatchingResult dataclass."""
    
    def test_create_result(self):
        """Test creating a valid result."""
        result = SFXMatchingResult(
            moment_matches=[],
            total_matches=0,
            average_confidence=0.0,
            average_subtlety=0.0,
            fallback_used=False,
            layer_guidance="Place each SFX on separate track"
        )
        
        assert result.total_matches == 0
        assert result.layer_guidance == "Place each SFX on separate track"
    
    def test_get_all_matches(self):
        """Test getting all matches across moments."""
        moment = SFXMoment(0.0, "intro", "opening", "medium", "seg1")
        match = SFXMatch(
            sfx_id="sfx_001",
            file_path="/path/file.wav",
            file_name="file.wav",
            folder_context="sfx",
            match_reason="test",
            confidence_score=0.85,
            matched_tags=["intro"]
        )
        
        result = SFXMatchingResult(
            moment_matches=[MomentSFXMatches(moment, [match])],
            total_matches=1,
            average_confidence=0.85,
            average_subtlety=0.70,
            fallback_used=False,
            layer_guidance="test"
        )
        
        all_matches = result.get_all_matches()
        assert len(all_matches) == 1
        assert all_matches[0].sfx_id == "sfx_001"
    
    def test_get_used_sfx_ids(self):
        """Test getting set of used SFX IDs."""
        moment = SFXMoment(0.0, "intro", "opening", "medium", "seg1")
        match = SFXMatch(
            sfx_id="sfx_001",
            file_path="/path/file.wav",
            file_name="file.wav",
            folder_context="sfx",
            match_reason="test",
            confidence_score=0.85,
            matched_tags=["intro"]
        )
        
        result = SFXMatchingResult(
            moment_matches=[MomentSFXMatches(moment, [match])],
            total_matches=1,
            average_confidence=0.85,
            average_subtlety=0.70,
            fallback_used=False,
            layer_guidance="test"
        )
        
        used_ids = result.get_used_sfx_ids()
        assert "sfx_001" in used_ids


class TestSFXMomentList:
    """Test cases for SFXMomentList dataclass."""
    
    def test_create_list(self):
        """Test creating a moment list."""
        moment1 = SFXMoment(0.0, "intro", "opening", "medium", "seg1")
        moment2 = SFXMoment(10.0, "outro", "closing", "medium", "seg2")
        
        moment_list = SFXMomentList(
            moments=[moment1, moment2],
            source_segments=2
        )
        
        assert len(moment_list.moments) == 2
        assert moment_list.source_segments == 2
    
    def test_get_moments_by_type(self):
        """Test filtering moments by type."""
        moment1 = SFXMoment(0.0, "intro", "opening", "medium", "seg1")
        moment2 = SFXMoment(10.0, "outro", "closing", "medium", "seg2")
        
        moment_list = SFXMomentList(moments=[moment1, moment2])
        
        intro_moments = moment_list.get_moments_by_type("intro")
        assert len(intro_moments) == 1
        assert intro_moments[0].type == "intro"
    
    def test_sort_by_timestamp(self):
        """Test sorting moments by timestamp."""
        moment1 = SFXMoment(30.0, "outro", "closing", "medium", "seg2")
        moment2 = SFXMoment(0.0, "intro", "opening", "medium", "seg1")
        
        moment_list = SFXMomentList(moments=[moment1, moment2])
        moment_list.sort_by_timestamp()
        
        assert moment_list.moments[0].timestamp == 0.0
        assert moment_list.moments[1].timestamp == 30.0
    
    def test_has_moment_at_timestamp(self):
        """Test checking for moment near timestamp."""
        moment = SFXMoment(10.0, "intro", "opening", "medium", "seg1")
        moment_list = SFXMomentList(moments=[moment])
        
        assert moment_list.has_moment_at_timestamp(10.5, tolerance=1.0)
        assert not moment_list.has_moment_at_timestamp(20.0, tolerance=1.0)
