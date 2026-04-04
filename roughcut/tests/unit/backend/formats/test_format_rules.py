"""Unit tests for format rules and media matching models.

Tests the FormatRule, MediaMatchingCriteria, and related classes
introduced in Story 3.6.
"""

import pytest
from pathlib import Path

from roughcut.backend.formats.models import (
    FormatRule, RuleType, TimingConstraint, SegmentStructure, TransitionRule,
    MediaMatchingCriteria, MatchingCriteriaType, MatchingRule,
    FormatTemplate, AssetGroup
)
from roughcut.backend.formats.prompt_formatter import FormatRulePromptFormatter


class TestTimingConstraint:
    """Tests for TimingConstraint class."""
    
    def test_exact_duration(self):
        """Test exact duration parsing."""
        tc = TimingConstraint(exact_duration=15, flexible=False)
        assert tc.exact_duration == 15
        assert tc.min_duration == 15
        assert tc.max_duration == 15
        assert not tc.flexible
    
    def test_min_max_duration(self):
        """Test min/max duration."""
        tc = TimingConstraint(min_duration=120, max_duration=300, flexible=True)
        assert tc.min_duration == 120
        assert tc.max_duration == 300
        assert tc.flexible
    
    def test_from_string_single(self):
        """Test parsing single duration string."""
        tc = TimingConstraint.from_string("0:15")
        assert tc.exact_duration == 15
        assert not tc.flexible
    
    def test_from_string_seconds_only(self):
        """Test parsing seconds only string."""
        tc = TimingConstraint.from_string("15")
        assert tc.exact_duration == 15
    
    def test_from_string_range(self):
        """Test parsing duration range string."""
        tc = TimingConstraint.from_string("2:30-5:00")
        assert tc.min_duration == 150  # 2:30 = 150s
        assert tc.max_duration == 300  # 5:00 = 300s
        assert tc.flexible
    
    def test_validation_min_greater_than_max(self):
        """Test validation catches min > max."""
        with pytest.raises(ValueError, match="min_duration.*>.*max_duration"):
            TimingConstraint(min_duration=300, max_duration=120)
    
    def test_validation_negative_duration(self):
        """Test validation catches negative duration."""
        with pytest.raises(ValueError, match="exact_duration must be >= 0"):
            TimingConstraint(exact_duration=-10)
    
    def test_format_for_display_exact(self):
        """Test display formatting for exact duration."""
        tc = TimingConstraint(exact_duration=255)  # 4:15
        assert tc.format_for_display() == "exactly 4:15"
    
    def test_format_for_display_range(self):
        """Test display formatting for range."""
        tc = TimingConstraint(min_duration=150, max_duration=300)
        assert tc.format_for_display() == "2:30-5:00"


class TestSegmentStructure:
    """Tests for SegmentStructure class."""
    
    def test_basic_creation(self):
        """Test basic segment structure creation."""
        ss = SegmentStructure(segment_count=3)
        assert ss.segment_count == 3
        assert ss.segment_order == "sequential"
    
    def test_with_descriptions(self):
        """Test segment structure with descriptions."""
        ss = SegmentStructure(
            segment_count=3,
            segment_descriptions=["Intro", "Body", "Outro"],
            segment_order="priority_based"
        )
        assert ss.segment_count == 3
        assert len(ss.segment_descriptions) == 3
        assert ss.segment_order == "priority_based"
    
    def test_validation_zero_segments(self):
        """Test validation catches zero segments."""
        with pytest.raises(ValueError, match="segment_count must be > 0"):
            SegmentStructure(segment_count=0)
    
    def test_validation_too_many_descriptions(self):
        """Test validation catches too many descriptions."""
        with pytest.raises(ValueError, match="More descriptions.*than segments"):
            SegmentStructure(segment_count=2, segment_descriptions=["A", "B", "C"])
    
    def test_validation_invalid_order(self):
        """Test validation catches invalid order."""
        with pytest.raises(ValueError, match="Invalid segment_order"):
            SegmentStructure(segment_count=1, segment_order="invalid")


class TestTransitionRule:
    """Tests for TransitionRule class."""
    
    def test_basic_creation(self):
        """Test basic transition rule creation."""
        tr = TransitionRule(transition_type="fade", duration=0.5)
        assert tr.transition_type == "fade"
        assert tr.duration == 0.5
    
    def test_with_segments(self):
        """Test transition between specific segments."""
        tr = TransitionRule(
            from_segment=0,
            to_segment=1,
            transition_type="dissolve",
            duration=1.0,
            style="smooth"
        )
        assert tr.from_segment == 0
        assert tr.to_segment == 1
        assert tr.style == "smooth"
    
    def test_validation_invalid_type(self):
        """Test validation catches invalid transition type."""
        with pytest.raises(ValueError, match="Invalid transition_type"):
            TransitionRule(transition_type="invalid")
    
    def test_validation_negative_duration(self):
        """Test validation catches negative duration."""
        with pytest.raises(ValueError, match="duration must be >= 0"):
            TransitionRule(duration=-0.5)


class TestFormatRule:
    """Tests for FormatRule class."""
    
    def test_basic_cutting_rule(self):
        """Test basic cutting rule creation."""
        fr = FormatRule(
            rule_type=RuleType.CUTTING,
            description="Cut to 3 narrative beats",
            segment_structure=SegmentStructure(segment_count=3)
        )
        assert fr.rule_type == RuleType.CUTTING
        assert fr.description == "Cut to 3 narrative beats"
        assert fr.segment_structure.segment_count == 3
    
    def test_timing_rule(self):
        """Test timing rule creation."""
        fr = FormatRule(
            rule_type=RuleType.TIMING,
            description="Keep under 5 minutes",
            timing_constraint=TimingConstraint(max_duration=300),
            strict_mode=False
        )
        assert fr.rule_type == RuleType.TIMING
        assert not fr.strict_mode
    
    def test_full_cutting_rule(self):
        """Test cutting rule with all features."""
        fr = FormatRule(
            rule_type=RuleType.CUTTING,
            description="Cut to intro hook",
            timing_constraint=TimingConstraint(max_duration=15),
            segment_structure=SegmentStructure(
                segment_count=1,
                segment_descriptions=["Attention-grabbing opening"]
            ),
            transitions=[
                TransitionRule(transition_type="fade", duration=0.5)
            ],
            strict_mode=True,
            priority=3,
            fallback_rules=["alternative_hook"]
        )
        assert len(fr.transitions) == 1
        assert fr.priority == 3
    
    def test_validation_missing_segment_structure(self):
        """Test validation catches missing segment structure for cutting rule."""
        with pytest.raises(ValueError, match="CUTTING rules require segment_structure"):
            FormatRule(
                rule_type=RuleType.CUTTING,
                description="Cut without structure"
            )
    
    def test_validation_invalid_priority(self):
        """Test validation catches invalid priority."""
        with pytest.raises(ValueError, match="priority must be >= 1"):
            FormatRule(
                rule_type=RuleType.TIMING,
                description="Test",
                priority=0
            )
    
    def test_validation_missing_description(self):
        """Test validation catches missing description."""
        with pytest.raises(ValueError, match="description is required"):
            FormatRule(
                rule_type=RuleType.TIMING,
                description=""
            )
    
    def test_format_for_ai(self):
        """Test AI formatting output."""
        fr = FormatRule(
            rule_type=RuleType.CUTTING,
            description="Cut to 3 beats",
            segment_structure=SegmentStructure(segment_count=3)
        )
        ai_text = fr.format_for_ai()
        assert "Cut to 3 beats" in ai_text
        assert "cutting" in ai_text
        assert "Segments: 3" in ai_text


class TestMatchingRule:
    """Tests for MatchingRule class."""
    
    def test_basic_creation(self):
        """Test basic matching rule creation."""
        mr = MatchingRule(
            attribute="emotion",
            condition="equals",
            value="upbeat",
            weight=0.8
        )
        assert mr.attribute == "emotion"
        assert mr.condition == "equals"
        assert mr.value == "upbeat"
        assert mr.weight == 0.8
    
    def test_validation_invalid_condition(self):
        """Test validation catches invalid condition."""
        with pytest.raises(ValueError, match="Invalid condition"):
            MatchingRule(
                attribute="tags",
                condition="invalid",
                value="test"
            )
    
    def test_validation_weight_out_of_range(self):
        """Test validation catches out-of-range weight."""
        with pytest.raises(ValueError, match="weight must be between 0.0 and 1.0"):
            MatchingRule(
                attribute="tempo",
                condition="greater_than",
                value=120,
                weight=1.5
            )
    
    def test_evaluate_equals(self):
        """Test equals evaluation."""
        mr = MatchingRule(attribute="emotion", condition="equals", value="upbeat")
        assert mr.evaluate("upbeat")
        assert not mr.evaluate("sad")
    
    def test_evaluate_contains_list(self):
        """Test contains evaluation with list."""
        mr = MatchingRule(attribute="tags", condition="contains", value="corporate")
        assert mr.evaluate(["corporate", "upbeat"])
        assert not mr.evaluate(["sad", "slow"])
    
    def test_evaluate_contains_string(self):
        """Test contains evaluation with string."""
        mr = MatchingRule(attribute="description", condition="contains", value="bright")
        assert mr.evaluate("A bright and cheerful theme")
        assert not mr.evaluate("A dark and moody theme")


class TestMediaMatchingCriteria:
    """Tests for MediaMatchingCriteria class."""
    
    def test_basic_creation(self):
        """Test basic criteria creation."""
        mmc = MediaMatchingCriteria(
            criteria_type=MatchingCriteriaType.EMOTION_MATCH,
            target_asset_group="intro_music",
            description="Match music emotion to intro tone"
        )
        assert mmc.criteria_type == MatchingCriteriaType.EMOTION_MATCH
        assert mmc.target_asset_group == "intro_music"
        assert mmc.required
    
    def test_with_matching_rules(self):
        """Test criteria with matching rules."""
        mmc = MediaMatchingCriteria(
            criteria_type=MatchingCriteriaType.CONTEXT_MATCH,
            target_asset_group="narrative_sfx",
            description="Match SFX to context",
            matching_rules=[
                MatchingRule(attribute="tags", condition="contains", value="emphasis"),
                MatchingRule(attribute="intensity", condition="greater_than", value=0.7)
            ],
            ai_guidance="Select subtle SFX",
            priority=2,
            required=False
        )
        assert len(mmc.matching_rules) == 2
        assert not mmc.required
        assert mmc.ai_guidance == "Select subtle SFX"
    
    def test_validation_missing_target(self):
        """Test validation catches missing target asset group."""
        with pytest.raises(ValueError, match="target_asset_group is required"):
            MediaMatchingCriteria(
                criteria_type=MatchingCriteriaType.TONE_MATCH,
                target_asset_group="",
                description="Test"
            )
    
    def test_format_for_ai(self):
        """Test AI formatting output."""
        mmc = MediaMatchingCriteria(
            criteria_type=MatchingCriteriaType.EMOTION_MATCH,
            target_asset_group="intro_music",
            description="Match emotion to tone",
            matching_rules=[
                MatchingRule(attribute="emotion", condition="equals", value="upbeat")
            ]
        )
        ai_text = mmc.format_for_ai()
        assert "Match emotion to tone" in ai_text
        assert "intro_music" in ai_text
        assert "emotion_match" in ai_text
        assert "Required: Must find matching asset" in ai_text


class TestFormatRulePromptFormatter:
    """Tests for FormatRulePromptFormatter class."""
    
    def test_format_rules_for_ai(self):
        """Test formatting rules for AI prompt."""
        formatter = FormatRulePromptFormatter()
        
        rules = [
            FormatRule(
                rule_type=RuleType.CUTTING,
                description="Cut to 3 beats",
                segment_structure=SegmentStructure(segment_count=3)
            )
        ]
        
        criteria = [
            MediaMatchingCriteria(
                criteria_type=MatchingCriteriaType.EMOTION_MATCH,
                target_asset_group="intro_music",
                description="Match emotion"
            )
        ]
        
        result = formatter.format_rules_for_ai(rules, criteria)
        assert "FORMAT RULES" in result
        assert "MEDIA MATCHING CRITERIA" in result
        assert "Cut to 3 beats" in result
        assert "intro_music" in result
        assert "INSTRUCTIONS:" in result
    
    def test_format_for_transcript_cutting(self):
        """Test formatting for transcript cutting."""
        formatter = FormatRulePromptFormatter()
        
        rules = [
            FormatRule(
                rule_type=RuleType.CUTTING,
                description="Cut to 3 beats",
                segment_structure=SegmentStructure(segment_count=3)
            ),
            FormatRule(
                rule_type=RuleType.TIMING,
                description="Total duration",
                timing_constraint=TimingConstraint(max_duration=300)
            )
        ]
        
        result = formatter.format_for_transcript_cutting(rules, 600)
        assert "TRANSCRIPT CUTTING INSTRUCTIONS:" in result
        assert "Target Duration: flexible - 300" in result
        assert "Source Transcript: 600" in result
    
    def test_format_summary(self):
        """Test summary formatting."""
        formatter = FormatRulePromptFormatter()
        
        rules = [
            FormatRule(
                rule_type=RuleType.CUTTING,
                description="Cut",
                segment_structure=SegmentStructure(segment_count=2)
            ),
            FormatRule(
                rule_type=RuleType.TIMING,
                description="Timing",
                timing_constraint=TimingConstraint(min_duration=120, max_duration=300)
            )
        ]
        
        criteria = [
            MediaMatchingCriteria(
                criteria_type=MatchingCriteriaType.EMOTION_MATCH,
                target_asset_group="music",
                description="Match",
                required=True
            ),
            MediaMatchingCriteria(
                criteria_type=MatchingCriteriaType.CONTEXT_MATCH,
                target_asset_group="sfx",
                description="Match SFX",
                required=False
            )
        ]
        
        result = formatter.format_summary(rules, criteria)
        assert "Format Summary:" in result
        assert "1 cutting rule(s)" in result
        assert "1 timing constraint(s)" in result
        assert "2 asset matching criteria" in result
        assert "(1 required, 1 optional)" in result


class TestFormatTemplateIntegration:
    """Integration tests for FormatTemplate with new fields."""
    
    def test_template_with_format_rules(self):
        """Test template with format rules."""
        template = FormatTemplate(
            slug="test-template",
            name="Test Template",
            description="A test template",
            file_path=Path("/test.md"),
            format_rules=[
                FormatRule(
                    rule_type=RuleType.CUTTING,
                    description="Cut to intro",
                    segment_structure=SegmentStructure(segment_count=1)
                )
            ]
        )
        
        assert len(template.format_rules) == 1
        cutting_rules = template.get_cutting_rules()
        assert len(cutting_rules) == 1
    
    def test_template_with_matching_criteria(self):
        """Test template with matching criteria."""
        template = FormatTemplate(
            slug="test-template",
            name="Test Template",
            description="A test template",
            file_path=Path("/test.md"),
            asset_groups=[
                AssetGroup(category="Music", name="intro_music", description="Intro")
            ],
            matching_criteria=[
                MediaMatchingCriteria(
                    criteria_type=MatchingCriteriaType.EMOTION_MATCH,
                    target_asset_group="intro_music",
                    description="Match emotion"
                )
            ]
        )
        
        criteria = template.get_matching_criteria_for_group("intro_music")
        assert len(criteria) == 1
    
    def test_template_validation(self):
        """Test template validation with format rules and criteria."""
        template = FormatTemplate(
            slug="test",
            name="Test",
            description="Test template",
            file_path=Path("/test.md"),
            asset_groups=[
                AssetGroup(category="Music", name="valid_group", description="Valid")
            ],
            matching_criteria=[
                MediaMatchingCriteria(
                    criteria_type=MatchingCriteriaType.EMOTION_MATCH,
                    target_asset_group="invalid_group",  # Not in asset_groups
                    description="Invalid reference"
                )
            ]
        )
        
        is_valid, errors = template.validate()
        assert not is_valid
        assert any("unknown asset group" in e.lower() for e in errors)
    
    def test_template_ai_prompt_section(self):
        """Test generating AI prompt section from template."""
        template = FormatTemplate(
            slug="test",
            name="Test",
            description="Test template",
            file_path=Path("/test.md"),
            format_rules=[
                FormatRule(
                    rule_type=RuleType.CUTTING,
                    description="Cut to 3 beats",
                    segment_structure=SegmentStructure(segment_count=3)
                )
            ],
            matching_criteria=[
                MediaMatchingCriteria(
                    criteria_type=MatchingCriteriaType.EMOTION_MATCH,
                    target_asset_group="music",
                    description="Match emotion"
                )
            ]
        )
        
        prompt = template.get_ai_prompt_section()
        assert "FORMAT RULES" in prompt
        assert "MEDIA MATCHING CRITERIA" in prompt
