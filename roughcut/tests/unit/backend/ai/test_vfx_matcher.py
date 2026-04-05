"""Unit tests for VFX matcher and related data structures.

Tests the VFX matching engine including:
- VFXRequirement dataclass validation
- VFXMatch and VFXPlacement calculations
- VFXMatcher requirement identification
- Tag scoring and matching algorithms
- Placement conflict detection
- Template asset group priority
"""

from __future__ import annotations

import pytest
from roughcut.backend.ai.vfx_requirement import (
    VFXRequirement,
    VFXRequirementList,
    VFX_REQUIREMENT_MAPPINGS,
    REQUIREMENT_TYPE_PREFERENCES,
    DEFAULT_DURATION_REQUIREMENTS
)
from roughcut.backend.ai.vfx_match import (
    VFXMatch,
    VFXAsset,
    VFXPlacement,
    VFXMatchingResult,
    RequirementVFXMatches,
    HIGH_CONFIDENCE_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD
)
from roughcut.backend.ai.vfx_matcher import (
    VFXMatcher,
    DEFAULT_MAX_SUGGESTIONS,
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_TEMPLATE_GROUP_BONUS
)


class TestVFXRequirement:
    """Tests for VFXRequirement dataclass."""
    
    def test_valid_requirement_creation(self):
        """Test creating a valid VFX requirement."""
        req = VFXRequirement(
            timestamp=10.0,
            type="lower_third",
            context="speaker introduction",
            duration=3.0,
            format_section="intro",
            speaker_name="CEO"
        )
        
        assert req.timestamp == 10.0
        assert req.type == "lower_third"
        assert req.context == "speaker introduction"
        assert req.duration == 3.0
        assert req.format_section == "intro"
        assert req.speaker_name == "CEO"
    
    def test_requirement_without_speaker(self):
        """Test creating a requirement without speaker name."""
        req = VFXRequirement(
            timestamp=5.0,
            type="transition",
            context="section change",
            duration=1.0,
            format_section="main"
        )
        
        assert req.speaker_name is None
    
    def test_invalid_timestamp_raises_error(self):
        """Test that negative timestamp raises ValueError."""
        with pytest.raises(ValueError, match="timestamp cannot be negative"):
            VFXRequirement(
                timestamp=-1.0,
                type="lower_third",
                context="test",
                duration=3.0,
                format_section="intro"
            )
    
    def test_invalid_type_raises_error(self):
        """Test that invalid requirement type raises ValueError."""
        with pytest.raises(ValueError, match="type must be one of"):
            VFXRequirement(
                timestamp=10.0,
                type="invalid_type",
                context="test",
                duration=3.0,
                format_section="intro"
            )
    
    def test_invalid_duration_raises_error(self):
        """Test that non-positive duration raises ValueError."""
        with pytest.raises(ValueError, match="duration must be positive"):
            VFXRequirement(
                timestamp=10.0,
                type="lower_third",
                context="test",
                duration=0.0,
                format_section="intro"
            )
    
    def test_empty_context_raises_error(self):
        """Test that empty context raises ValueError."""
        with pytest.raises(ValueError, match="context cannot be empty"):
            VFXRequirement(
                timestamp=10.0,
                type="lower_third",
                context="",
                duration=3.0,
                format_section="intro"
            )
    
    def test_to_tag_query(self):
        """Test tag query generation from requirement type."""
        req = VFXRequirement(
            timestamp=10.0,
            type="lower_third",
            context="test",
            duration=3.0,
            format_section="intro"
        )
        
        tags = req.to_tag_query()
        assert "lower_third" in tags
        assert "nameplate" in tags
        assert "speaker" in tags
    
    def test_get_preferred_template_types(self):
        """Test getting preferred template types."""
        req = VFXRequirement(
            timestamp=10.0,
            type="lower_third",
            context="test",
            duration=3.0,
            format_section="intro"
        )
        
        types = req.get_preferred_template_types()
        assert "fusion_composition" in types
        assert "generator" in types
    
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        req = VFXRequirement(
            timestamp=125.5,
            type="lower_third",
            context="test",
            duration=3.0,
            format_section="intro"
        )
        
        assert req.format_timestamp() == "2:05"
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        req = VFXRequirement(
            timestamp=10.0,
            type="lower_third",
            context="test",
            duration=3.0,
            format_section="intro",
            speaker_name="CEO"
        )
        
        data = req.to_dict()
        assert data["timestamp"] == 10.0
        assert data["type"] == "lower_third"
        assert data["speaker_name"] == "CEO"
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "timestamp": 15.0,
            "type": "transition",
            "context": "section change",
            "duration": 1.0,
            "format_section": "main",
            "speaker_name": None
        }
        
        req = VFXRequirement.from_dict(data)
        assert req.timestamp == 15.0
        assert req.type == "transition"
        assert req.context == "section change"


class TestVFXPlacement:
    """Tests for VFXPlacement dataclass."""
    
    def test_valid_placement_creation(self):
        """Test creating a valid placement."""
        placement = VFXPlacement(
            start_time=10.0,
            end_time=13.0,
            duration_ms=3000
        )
        
        assert placement.start_time == 10.0
        assert placement.end_time == 13.0
        assert placement.duration_ms == 3000
    
    def test_invalid_start_time_raises_error(self):
        """Test that negative start time raises ValueError."""
        with pytest.raises(ValueError, match="start_time cannot be negative"):
            VFXPlacement(
                start_time=-1.0,
                end_time=10.0,
                duration_ms=1000
            )
    
    def test_end_time_before_start_raises_error(self):
        """Test that end_time < start_time raises ValueError."""
        with pytest.raises(ValueError, match="end_time .* must be >= start_time"):
            VFXPlacement(
                start_time=10.0,
                end_time=5.0,
                duration_ms=1000
            )
    
    def test_overlaps_with(self):
        """Test overlap detection between placements."""
        p1 = VFXPlacement(start_time=10.0, end_time=13.0, duration_ms=3000)
        p2 = VFXPlacement(start_time=12.0, end_time=15.0, duration_ms=3000)
        p3 = VFXPlacement(start_time=15.0, end_time=18.0, duration_ms=3000)
        
        assert p1.overlaps_with(p2) is True  # Overlapping
        assert p1.overlaps_with(p3) is False  # Not overlapping
        assert p2.overlaps_with(p3) is False  # Adjacent (not overlapping with tolerance)
    
    def test_get_overlap_duration(self):
        """Test calculating overlap duration."""
        p1 = VFXPlacement(start_time=10.0, end_time=13.0, duration_ms=3000)
        p2 = VFXPlacement(start_time=12.0, end_time=15.0, duration_ms=3000)
        p3 = VFXPlacement(start_time=15.0, end_time=18.0, duration_ms=3000)
        
        assert p1.get_overlap_duration(p2) == 1.0  # 1 second overlap
        assert p1.get_overlap_duration(p3) == 0.0  # No overlap
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        placement = VFXPlacement(
            start_time=10.0,
            end_time=13.0,
            duration_ms=3000
        )
        
        data = placement.to_dict()
        assert data["start_time"] == 10.0
        assert data["end_time"] == 13.0
        assert data["duration_ms"] == 3000
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "start_time": 5.0,
            "end_time": 8.0,
            "duration_ms": 3000
        }
        
        placement = VFXPlacement.from_dict(data)
        assert placement.start_time == 5.0
        assert placement.end_time == 8.0


class TestVFXAsset:
    """Tests for VFXAsset dataclass."""
    
    def test_valid_asset_creation(self):
        """Test creating a valid VFX asset."""
        asset = VFXAsset(
            vfx_id="vfx_001",
            file_path="/assets/vfx/LowerThirds/test.drp",
            tags=["lower_third", "corporate"],
            folder_context="LowerThirds",
            duration_ms=3000,
            template_type="fusion_composition"
        )
        
        assert asset.vfx_id == "vfx_001"
        assert asset.category == "vfx"
        assert asset.template_type == "fusion_composition"
    
    def test_default_values(self):
        """Test default values for optional fields."""
        asset = VFXAsset(
            vfx_id="vfx_001",
            file_path="/assets/vfx/test.drp",
            tags=["test"]
        )
        
        assert asset.category == "vfx"
        assert asset.folder_context == ""
        assert asset.duration_ms == 0
        assert asset.template_type == "fusion_composition"
    
    def test_get_file_name(self):
        """Test extracting filename from path."""
        asset = VFXAsset(
            vfx_id="vfx_001",
            file_path="/assets/vfx/LowerThirds/corporate_lower_third.drp",
            tags=["test"]
        )
        
        assert asset.get_file_name() == "corporate_lower_third.drp"
    
    def test_matches_template_type_preference(self):
        """Test template type preference matching."""
        asset = VFXAsset(
            vfx_id="vfx_001",
            file_path="/assets/vfx/test.drp",
            tags=["test"],
            template_type="fusion_composition"
        )
        
        assert asset.matches_template_type_preference(["fusion_composition", "generator"]) is True
        assert asset.matches_template_type_preference(["transition"]) is False
    
    def test_has_tag(self):
        """Test tag checking with case insensitivity."""
        asset = VFXAsset(
            vfx_id="vfx_001",
            file_path="/assets/vfx/test.drp",
            tags=["Lower_Third", "CORPORATE"]
        )
        
        assert asset.has_tag("lower_third") is True
        assert asset.has_tag("corporate") is True
        assert asset.has_tag("transition") is False


class TestVFXMatch:
    """Tests for VFXMatch dataclass."""
    
    def test_valid_match_creation(self):
        """Test creating a valid VFX match."""
        placement = VFXPlacement(start_time=10.0, end_time=13.0, duration_ms=3000)
        
        match = VFXMatch(
            vfx_id="vfx_001",
            file_path="/assets/vfx/test.drp",
            file_name="test.drp",
            folder_context="LowerThirds",
            match_reason="Tags match requirement",
            confidence_score=0.85,
            matched_tags=["lower_third"],
            template_type="fusion_composition",
            placement=placement,
            from_template_group=True,
            group_name="lower_thirds"
        )
        
        assert match.vfx_id == "vfx_001"
        assert match.confidence_score == 0.85
        assert match.from_template_group is True
        assert match.group_name == "lower_thirds"
    
    def test_is_high_confidence(self):
        """Test high confidence check."""
        placement = VFXPlacement(start_time=10.0, end_time=13.0, duration_ms=3000)
        
        high_match = VFXMatch(
            vfx_id="vfx_001",
            file_path="/assets/vfx/test.drp",
            file_name="test.drp",
            folder_context="test",
            match_reason="test",
            confidence_score=0.90,
            matched_tags=["test"],
            template_type="fusion_composition",
            placement=placement
        )
        
        low_match = VFXMatch(
            vfx_id="vfx_002",
            file_path="/assets/vfx/test2.drp",
            file_name="test2.drp",
            folder_context="test",
            match_reason="test",
            confidence_score=0.50,
            matched_tags=["test"],
            template_type="fusion_composition",
            placement=placement
        )
        
        assert high_match.is_high_confidence() is True
        assert low_match.is_high_confidence() is False
    
    def test_is_viable(self):
        """Test viability check."""
        placement = VFXPlacement(start_time=10.0, end_time=13.0, duration_ms=3000)
        
        viable_match = VFXMatch(
            vfx_id="vfx_001",
            file_path="/assets/vfx/test.drp",
            file_name="test.drp",
            folder_context="test",
            match_reason="test",
            confidence_score=0.60,
            matched_tags=["test"],
            template_type="fusion_composition",
            placement=placement
        )
        
        assert viable_match.is_viable() is True
    
    def test_format_suggestion(self):
        """Test suggestion formatting."""
        placement = VFXPlacement(start_time=65.0, end_time=68.0, duration_ms=3000)
        
        match = VFXMatch(
            vfx_id="vfx_001",
            file_path="/assets/vfx/test.drp",
            file_name="corporate_lower_third.drp",
            folder_context="test",
            match_reason="test",
            confidence_score=0.85,
            matched_tags=["test"],
            template_type="fusion_composition",
            placement=placement
        )
        
        suggestion = match.format_suggestion()
        assert "corporate_lower_third.drp" in suggestion
        assert "1:05" in suggestion


class TestVFXMatcher:
    """Tests for VFXMatcher class."""
    
    def test_matcher_initialization(self):
        """Test VFX matcher initialization."""
        matcher = VFXMatcher()
        
        assert matcher.max_suggestions == DEFAULT_MAX_SUGGESTIONS
        assert matcher.min_confidence_threshold == DEFAULT_MIN_CONFIDENCE
        assert matcher.track_template_groups is True
    
    def test_matcher_custom_settings(self):
        """Test VFX matcher with custom settings."""
        matcher = VFXMatcher(
            max_suggestions=5,
            min_confidence_threshold=0.70,
            track_template_groups=False
        )
        
        assert matcher.max_suggestions == 5
        assert matcher.min_confidence_threshold == 0.70
        assert matcher.track_template_groups is False
    
    def test_identify_vfx_requirements_basic(self):
        """Test basic requirement identification."""
        matcher = VFXMatcher()
        
        segments = [
            {
                "section_name": "intro",
                "start_time": 0.0,
                "end_time": 15.0,
                "text": "Welcome to our presentation",
                "speaker": "CEO",
                "speaker_change": False
            }
        ]
        
        format_template = {
            "vfx_requirements": [
                {"type": "lower_third", "at": "segment_start", "duration": 3.0}
            ]
        }
        
        requirements = matcher.identify_vfx_requirements(segments, format_template)
        
        assert len(requirements) == 1
        assert requirements[0].type == "lower_third"
        assert requirements[0].timestamp == 0.0
    
    def test_identify_vfx_requirements_empty_segments(self):
        """Test requirement identification with empty segments."""
        matcher = VFXMatcher()
        
        with pytest.raises(ValueError, match="segments cannot be empty"):
            matcher.identify_vfx_requirements([], {"vfx_requirements": []})
    
    def test_identify_vfx_requirements_speaker_change(self):
        """Test requirement identification with speaker changes."""
        matcher = VFXMatcher()
        
        segments = [
            {
                "section_name": "narrative",
                "start_time": 30.0,
                "end_time": 60.0,
                "text": "Let me introduce our team",
                "speaker": "Manager",
                "speaker_change": True
            }
        ]
        
        format_template = {"vfx_requirements": []}  # No template requirements
        
        requirements = matcher.identify_vfx_requirements(segments, format_template)
        
        # Should detect speaker change and add lower third
        assert len(requirements) == 1
        assert requirements[0].type == "lower_third"
        assert requirements[0].speaker_name == "Manager"
    
    def test_match_vfx_to_requirements_basic(self):
        """Test basic VFX matching."""
        matcher = VFXMatcher()
        
        requirements = [
            VFXRequirement(
                timestamp=10.0,
                type="lower_third",
                context="speaker introduction",
                duration=3.0,
                format_section="intro"
            )
        ]
        
        vfx_index = [
            {
                "id": "vfx_001",
                "file_path": "/assets/vfx/LowerThirds/corporate.drp",
                "tags": ["lower_third", "corporate", "nameplate"],
                "folder_context": "LowerThirds",
                "duration_ms": 3000,
                "template_type": "fusion_composition"
            }
        ]
        
        result = matcher.match_vfx_to_requirements(requirements, vfx_index)
        
        assert result.total_matches > 0
        assert len(result.requirement_matches) == 1
        assert result.requirement_matches[0].matches[0].confidence_score > 0.5
    
    def test_match_vfx_to_requirements_empty_library(self):
        """Test matching with empty VFX library."""
        matcher = VFXMatcher()
        
        requirements = [
            VFXRequirement(
                timestamp=10.0,
                type="lower_third",
                context="test",
                duration=3.0,
                format_section="intro"
            )
        ]
        
        with pytest.raises(ValueError, match="vfx_index cannot be empty"):
            matcher.match_vfx_to_requirements(requirements, [])
    
    def test_template_group_priority(self):
        """Test that template asset groups are prioritized."""
        matcher = VFXMatcher()
        
        requirements = [
            VFXRequirement(
                timestamp=10.0,
                type="lower_third",
                context="speaker introduction",
                duration=3.0,
                format_section="intro"
            )
        ]
        
        vfx_index = [
            {
                "id": "vfx_001",
                "file_path": "/assets/vfx/LowerThirds/group_asset.drp",
                "tags": ["lower_third"],
                "folder_context": "LowerThirds",
                "duration_ms": 3000,
                "template_type": "fusion_composition"
            },
            {
                "id": "vfx_002",
                "file_path": "/assets/vfx/LowerThirds/regular_asset.drp",
                "tags": ["lower_third"],
                "folder_context": "LowerThirds",
                "duration_ms": 3000,
                "template_type": "fusion_composition"
            }
        ]
        
        # vfx_001 is in the group
        template_asset_groups = {
            "lower_thirds": ["vfx_001"]
        }
        
        result = matcher.match_vfx_to_requirements(
            requirements, vfx_index, template_asset_groups
        )
        
        # The group asset should have higher confidence
        matches = result.requirement_matches[0].matches
        if len(matches) >= 2:
            # Check that group member has higher or equal confidence
            group_match = next((m for m in matches if m.vfx_id == "vfx_001"), None)
            regular_match = next((m for m in matches if m.vfx_id == "vfx_002"), None)
            
            if group_match and regular_match:
                assert group_match.confidence_score >= regular_match.confidence_score
    
    def test_placement_conflict_detection(self):
        """Test detection of overlapping placements."""
        matcher = VFXMatcher()
        
        # Create requirements that would overlap
        req1 = VFXRequirement(
            timestamp=10.0,
            type="lower_third",
            context="test1",
            duration=5.0,  # 10-15 seconds
            format_section="intro"
        )
        
        req2 = VFXRequirement(
            timestamp=12.0,
            type="title_card",
            context="test2",
            duration=5.0,  # 12-17 seconds - overlaps with req1
            format_section="intro"
        )
        
        # Create matches with placements
        placement1 = VFXPlacement(start_time=10.0, end_time=15.0, duration_ms=5000)
        placement2 = VFXPlacement(start_time=12.0, end_time=17.0, duration_ms=5000)
        
        match1 = VFXMatch(
            vfx_id="vfx_001",
            file_path="/assets/test1.drp",
            file_name="test1.drp",
            folder_context="test",
            match_reason="test",
            confidence_score=0.90,
            matched_tags=["test"],
            template_type="fusion_composition",
            placement=placement1
        )
        
        match2 = VFXMatch(
            vfx_id="vfx_002",
            file_path="/assets/test2.drp",
            file_name="test2.drp",
            folder_context="test",
            match_reason="test",
            confidence_score=0.85,
            matched_tags=["test"],
            template_type="fusion_composition",
            placement=placement2
        )
        
        req_matches = [
            RequirementVFXMatches(requirement=req1, matches=[match1]),
            RequirementVFXMatches(requirement=req2, matches=[match2])
        ]
        
        result = VFXMatchingResult(
            requirement_matches=req_matches,
            total_matches=2,
            average_confidence=0.875,
            fallback_used=False,
            placement_conflicts=[],
            template_group_coverage=0.0
        )
        
        # Detect conflicts
        conflicts = matcher._detect_placement_conflicts(req_matches)
        
        assert len(conflicts) > 0  # Should detect overlap
    
    def test_calculate_match_score(self):
        """Test match score calculation."""
        matcher = VFXMatcher()
        
        req = VFXRequirement(
            timestamp=10.0,
            type="lower_third",
            context="test",
            duration=3.0,
            format_section="intro"
        )
        
        asset = VFXAsset(
            vfx_id="vfx_001",
            file_path="/assets/vfx/LowerThirds/corporate.drp",
            tags=["lower_third", "corporate", "nameplate"],
            folder_context="LowerThirds",
            template_type="fusion_composition"
        )
        
        search_tags = req.to_tag_query()
        score, matched_tags = matcher._calculate_match_score(req, asset, search_tags)
        
        assert score > 0.5  # Should have good score with matching tags
        assert "lower_third" in matched_tags
        assert "corporate" in matched_tags
    
    def test_calculate_placement(self):
        """Test placement calculation."""
        matcher = VFXMatcher()
        
        req = VFXRequirement(
            timestamp=10.0,
            type="lower_third",
            context="test",
            duration=3.0,
            format_section="intro"
        )
        
        asset = VFXAsset(
            vfx_id="vfx_001",
            file_path="/assets/test.drp",
            tags=["test"],
            duration_ms=2500
        )
        
        placement = matcher._calculate_placement(req, asset)
        
        assert placement.start_time == 10.0
        assert placement.duration_ms == 2500  # Uses asset duration
        assert placement.end_time == 12.5  # 10 + 2.5 seconds
    
    def test_identify_vfx_requirements_invalid_segment_type(self):
        """Test that non-dict segments raise ValueError."""
        matcher = VFXMatcher()
        
        segments = ["not a dict", 123, None]
        
        with pytest.raises(ValueError, match="must be a dictionary"):
            matcher.identify_vfx_requirements(segments, {"vfx_requirements": []})
    
    def test_identify_vfx_requirements_invalid_timestamp_types(self):
        """Test that non-numeric timestamps raise ValueError."""
        matcher = VFXMatcher()
        
        segments = [
            {
                "section_name": "intro",
                "start_time": "invalid",  # String instead of number
                "end_time": 15.0,
                "speaker": "CEO",
                "speaker_change": False
            }
        ]
        
        with pytest.raises(ValueError, match="start_time must be numeric"):
            matcher.identify_vfx_requirements(segments, {"vfx_requirements": []})
    
    def test_identify_vfx_requirements_negative_start_time(self):
        """Test that negative start_time raises ValueError."""
        matcher = VFXMatcher()
        
        segments = [
            {
                "section_name": "intro",
                "start_time": -5.0,
                "end_time": 15.0,
                "speaker": "CEO",
                "speaker_change": False
            }
        ]
        
        with pytest.raises(ValueError, match="start_time cannot be negative"):
            matcher.identify_vfx_requirements(segments, {"vfx_requirements": []})
    
    def test_identify_vfx_requirements_inverted_timestamps(self):
        """Test that end_time < start_time raises ValueError."""
        matcher = VFXMatcher()
        
        segments = [
            {
                "section_name": "intro",
                "start_time": 20.0,
                "end_time": 10.0,  # Inverted!
                "speaker": "CEO",
                "speaker_change": False
            }
        ]
        
        with pytest.raises(ValueError, match="end_time .* must be >= start_time"):
            matcher.identify_vfx_requirements(segments, {"vfx_requirements": []})
    
    def test_resolve_timestamp_negative_offset_clamped(self):
        """Test that negative relative offset is clamped to 0."""
        matcher = VFXMatcher()
        
        # Offset of -100 from segment_start=10 should clamp to 0, not -90
        result = matcher._resolve_timestamp("-100", 10.0, 30.0)
        assert result == 0.0
    
    def test_vfx_asset_tags_none_handled(self):
        """Test that VFXAsset handles tags=None gracefully."""
        # Should not raise error, should default to empty list
        asset = VFXAsset(
            vfx_id="vfx_001",
            file_path="/assets/test.drp",
            tags=None  # Explicitly None
        )
        
        assert asset.tags == []
        assert asset.tags is not None


class TestVFXRequirementList:
    """Tests for VFXRequirementList dataclass."""
    
    def test_requirement_list_creation(self):
        """Test creating a requirement list."""
        req1 = VFXRequirement(
            timestamp=10.0, type="lower_third", context="test1",
            duration=3.0, format_section="intro"
        )
        req2 = VFXRequirement(
            timestamp=20.0, type="transition", context="test2",
            duration=1.0, format_section="main"
        )
        
        req_list = VFXRequirementList(
            requirements=[req1, req2],
            source_template="YouTube Interview"
        )
        
        assert len(req_list.requirements) == 2
        assert req_list.source_template == "YouTube Interview"
    
    def test_get_requirements_by_type(self):
        """Test filtering requirements by type."""
        req1 = VFXRequirement(
            timestamp=10.0, type="lower_third", context="test1",
            duration=3.0, format_section="intro"
        )
        req2 = VFXRequirement(
            timestamp=20.0, type="lower_third", context="test2",
            duration=3.0, format_section="main"
        )
        req3 = VFXRequirement(
            timestamp=30.0, type="transition", context="test3",
            duration=1.0, format_section="outro"
        )
        
        req_list = VFXRequirementList(requirements=[req1, req2, req3])
        
        lower_thirds = req_list.get_requirements_by_type("lower_third")
        assert len(lower_thirds) == 2
        
        transitions = req_list.get_requirements_by_type("transition")
        assert len(transitions) == 1
    
    def test_get_conflicting_requirements(self):
        """Test finding overlapping requirements."""
        req1 = VFXRequirement(
            timestamp=10.0, type="lower_third", context="test1",
            duration=5.0, format_section="intro"  # 10-15
        )
        req2 = VFXRequirement(
            timestamp=12.0, type="title_card", context="test2",
            duration=5.0, format_section="intro"  # 12-17 - overlaps
        )
        req3 = VFXRequirement(
            timestamp=20.0, type="transition", context="test3",
            duration=1.0, format_section="main"  # 20-21 - no overlap
        )
        
        req_list = VFXRequirementList(requirements=[req1, req2, req3])
        conflicts = req_list.get_conflicting_requirements()
        
        assert len(conflicts) == 1
        assert conflicts[0][0].type == "lower_third"
        assert conflicts[0][1].type == "title_card"


class TestVFXMatchingResult:
    """Tests for VFXMatchingResult dataclass."""
    
    def test_result_creation(self):
        """Test creating a matching result."""
        req = VFXRequirement(
            timestamp=10.0, type="lower_third", context="test",
            duration=3.0, format_section="intro"
        )
        
        placement = VFXPlacement(start_time=10.0, end_time=13.0, duration_ms=3000)
        
        match = VFXMatch(
            vfx_id="vfx_001",
            file_path="/assets/test.drp",
            file_name="test.drp",
            folder_context="test",
            match_reason="test",
            confidence_score=0.85,
            matched_tags=["test"],
            template_type="fusion_composition",
            placement=placement
        )
        
        req_matches = RequirementVFXMatches(
            requirement=req,
            matches=[match]
        )
        
        result = VFXMatchingResult(
            requirement_matches=[req_matches],
            total_matches=1,
            average_confidence=0.85,
            fallback_used=False,
            placement_conflicts=[],
            template_group_coverage=0.5
        )
        
        assert result.total_matches == 1
        assert result.average_confidence == 0.85
        assert result.template_group_coverage == 0.5
    
    def test_get_all_matches(self):
        """Test getting all matches from result."""
        # Create two requirement matches with multiple matches each
        req1 = VFXRequirement(
            timestamp=10.0, type="lower_third", context="test1",
            duration=3.0, format_section="intro"
        )
        req2 = VFXRequirement(
            timestamp=20.0, type="transition", context="test2",
            duration=1.0, format_section="main"
        )
        
        placement = VFXPlacement(start_time=10.0, end_time=13.0, duration_ms=3000)
        
        match1 = VFXMatch(
            vfx_id="vfx_001", file_path="/a.drp", file_name="a.drp",
            folder_context="test", match_reason="test",
            confidence_score=0.90, matched_tags=["test"],
            template_type="fusion_composition", placement=placement
        )
        match2 = VFXMatch(
            vfx_id="vfx_002", file_path="/b.drp", file_name="b.drp",
            folder_context="test", match_reason="test",
            confidence_score=0.80, matched_tags=["test"],
            template_type="fusion_composition", placement=placement
        )
        
        req_matches = [
            RequirementVFXMatches(requirement=req1, matches=[match1]),
            RequirementVFXMatches(requirement=req2, matches=[match2])
        ]
        
        result = VFXMatchingResult(
            requirement_matches=req_matches,
            total_matches=2,
            average_confidence=0.85,
            fallback_used=False,
            placement_conflicts=[],
            template_group_coverage=0.0
        )
        
        all_matches = result.get_all_matches()
        assert len(all_matches) == 2
        assert all_matches[0].vfx_id == "vfx_001"
        assert all_matches[1].vfx_id == "vfx_002"
    
    def test_get_matches_by_type(self):
        """Test filtering matches by requirement type."""
        req1 = VFXRequirement(
            timestamp=10.0, type="lower_third", context="test1",
            duration=3.0, format_section="intro"
        )
        req2 = VFXRequirement(
            timestamp=20.0, type="transition", context="test2",
            duration=1.0, format_section="main"
        )
        
        placement = VFXPlacement(start_time=10.0, end_time=13.0, duration_ms=3000)
        
        match1 = VFXMatch(
            vfx_id="vfx_001", file_path="/a.drp", file_name="a.drp",
            folder_context="test", match_reason="test",
            confidence_score=0.90, matched_tags=["test"],
            template_type="fusion_composition", placement=placement
        )
        match2 = VFXMatch(
            vfx_id="vfx_002", file_path="/b.drp", file_name="b.drp",
            folder_context="test", match_reason="test",
            confidence_score=0.80, matched_tags=["test"],
            template_type="transition", placement=placement
        )
        
        req_matches = [
            RequirementVFXMatches(requirement=req1, matches=[match1]),
            RequirementVFXMatches(requirement=req2, matches=[match2])
        ]
        
        result = VFXMatchingResult(
            requirement_matches=req_matches,
            total_matches=2,
            average_confidence=0.85,
            fallback_used=False,
            placement_conflicts=[],
            template_group_coverage=0.0
        )
        
        lower_third_matches = result.get_matches_by_type("lower_third")
        assert len(lower_third_matches) == 1
        assert lower_third_matches[0].vfx_id == "vfx_001"
