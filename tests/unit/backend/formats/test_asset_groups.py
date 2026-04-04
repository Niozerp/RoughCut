"""Unit tests for AssetGroup dataclass."""

import unittest
from typing import List

from roughcut.backend.formats.models import (
    AssetGroup,
    AssetGroupCategory,
    AssetGroupParseError,
    AssetGroupPriority,
    DurationHint,
)


class TestDurationHint(unittest.TestCase):
    """Test DurationHint parsing and behavior."""

    def test_parse_seconds(self) -> None:
        """Test parsing seconds-only duration."""
        hint = DurationHint(exact="15")
        self.assertEqual(hint.exact, 15)

    def test_parse_mm_ss(self) -> None:
        """Test parsing mm:ss format."""
        hint = DurationHint(exact="0:15")
        self.assertEqual(hint.exact, 15)

        hint2 = DurationHint(exact="2:30")
        self.assertEqual(hint2.exact, 150)

    def test_parse_min_max(self) -> None:
        """Test parsing min and max durations."""
        hint = DurationHint(min_duration="0:10", max_duration="0:30")
        self.assertEqual(hint.min, 10)
        self.assertEqual(hint.max, 30)
        self.assertIsNone(hint.exact)

    def test_flexible_default(self) -> None:
        """Test flexible default is True."""
        hint = DurationHint()
        self.assertTrue(hint.flexible)

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        hint = DurationHint(exact="0:15", flexible=False)
        result = hint.to_dict()
        self.assertEqual(result["exact"], 15)
        self.assertEqual(result["min"], None)
        self.assertEqual(result["max"], None)
        self.assertFalse(result["flexible"])

    def test_parse_duration_validation_empty_string(self) -> None:
        """Test that empty duration string raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            DurationHint(exact="")
        self.assertIn("non-empty string", str(ctx.exception))

    def test_parse_duration_validation_invalid_format(self) -> None:
        """Test that invalid duration format raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            DurationHint(exact="abc")
        self.assertIn("Invalid duration format", str(ctx.exception))

    def test_parse_duration_validation_too_many_parts(self) -> None:
        """Test that hh:mm:ss format raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            DurationHint(exact="1:2:3")
        self.assertIn("Invalid duration format", str(ctx.exception))

    def test_parse_duration_validation_negative(self) -> None:
        """Test that negative duration raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            DurationHint(exact="-30")
        self.assertIn("cannot be negative", str(ctx.exception))


class TestAssetGroupCreation(unittest.TestCase):
    """Test AssetGroup creation and validation."""

    def test_create_minimal(self) -> None:
        """Test creating minimal valid AssetGroup."""
        group = AssetGroup(
            name="intro_music",
            description="Upbeat intro music",
            category=AssetGroupCategory.MUSIC,
            required_tags=["upbeat", "intro"],
        )
        self.assertEqual(group.name, "intro_music")
        self.assertEqual(group.description, "Upbeat intro music")
        self.assertEqual(group.category, AssetGroupCategory.MUSIC)
        self.assertEqual(group.required_tags, ["upbeat", "intro"])
        self.assertEqual(group.optional_tags, [])
        self.assertEqual(group.priority, AssetGroupPriority.MEDIUM)

    def test_create_full(self) -> None:
        """Test creating AssetGroup with all fields."""
        duration = DurationHint(exact="0:15")
        group = AssetGroup(
            name="outro_chime",
            description="Subtle outro sound",
            category=AssetGroupCategory.SFX,
            required_tags=["chime"],
            optional_tags=["subtle", "short"],
            duration_hint=duration,
            priority=AssetGroupPriority.HIGH,
            fallback_groups=["intro_music"],
        )
        self.assertEqual(group.name, "outro_chime")
        self.assertEqual(group.required_tags, ["chime"])
        self.assertEqual(group.optional_tags, ["subtle", "short"])
        self.assertEqual(group.duration_hint, duration)
        self.assertEqual(group.priority, AssetGroupPriority.HIGH)
        self.assertEqual(group.fallback_groups, ["intro_music"])

    def test_create_with_string_priority(self) -> None:
        """Test creating AssetGroup with string priority (auto-converted to enum)."""
        group = AssetGroup(
            name="test_group",
            description="Test description",
            category=AssetGroupCategory.MUSIC,
            required_tags=["test"],
            priority="high",  # String should be converted to enum
        )
        self.assertEqual(group.priority, AssetGroupPriority.HIGH)

    def test_missing_name_raises(self) -> None:
        """Test that empty name raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            AssetGroup(
                name="",
                description="Test description",
                category=AssetGroupCategory.MUSIC,
                required_tags=["test"],
            )
        self.assertIn("name is required", str(ctx.exception).lower())

    def test_missing_description_raises(self) -> None:
        """Test that empty description raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            AssetGroup(
                name="test_group",
                description="",
                category=AssetGroupCategory.MUSIC,
                required_tags=["test"],
            )
        self.assertIn("description is required", str(ctx.exception).lower())

    def test_missing_tags_raises(self) -> None:
        """Test that missing both required and optional tags raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            AssetGroup(
                name="test_group",
                description="Test description",
                category=AssetGroupCategory.MUSIC,
            )
        self.assertIn("at least one tag", str(ctx.exception).lower())

    def test_invalid_category_raises(self) -> None:
        """Test that invalid category raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            AssetGroup(
                name="test_group",
                description="Test description",
                category="invalid_category",  # type: ignore
                required_tags=["test"],
            )
        self.assertIn("invalid category", str(ctx.exception).lower())

    def test_invalid_priority_raises(self) -> None:
        """Test that invalid priority string raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            AssetGroup(
                name="test_group",
                description="Test description",
                category=AssetGroupCategory.MUSIC,
                required_tags=["test"],
                priority="invalid_priority",
            )
        self.assertIn("invalid priority", str(ctx.exception).lower())

    def test_tag_normalization(self) -> None:
        """Test that tags are normalized to lowercase."""
        group = AssetGroup(
            name="test_group",
            description="Test description",
            category=AssetGroupCategory.MUSIC,
            required_tags=["UPBEAT", "Intro"],
            optional_tags=["CORPORATE"],
        )
        self.assertEqual(group.required_tags, ["upbeat", "intro"])
        self.assertEqual(group.optional_tags, ["corporate"])

    def test_optional_tags_only(self) -> None:
        """Test that optional tags alone are sufficient."""
        group = AssetGroup(
            name="test_group",
            description="Test description",
            category=AssetGroupCategory.MUSIC,
            optional_tags=["ambient"],
        )
        self.assertEqual(group.optional_tags, ["ambient"])

    def test_none_input_raises(self) -> None:
        """Test that None name raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            AssetGroup(
                name=None,  # type: ignore
                description="Test description",
                category=AssetGroupCategory.MUSIC,
                required_tags=["test"],
            )
        self.assertIn("name is required", str(ctx.exception).lower())

    def test_empty_tags_filtered(self) -> None:
        """Test that empty/whitespace-only tags are filtered out."""
        with self.assertRaises(ValueError) as ctx:
            AssetGroup(
                name="test_group",
                description="Test description",
                category=AssetGroupCategory.MUSIC,
                required_tags=["", "  ", "   "],
            )
        self.assertIn("at least one non-empty tag", str(ctx.exception).lower())


class TestAssetGroupMatching(unittest.TestCase):
    """Test AssetGroup asset matching algorithm (exact/partial/none)."""

    def setUp(self) -> None:
        """Set up test fixture."""
        self.group = AssetGroup(
            name="intro_music",
            description="Upbeat corporate intro",
            category=AssetGroupCategory.MUSIC,
            required_tags=["upbeat", "corporate"],
            optional_tags=["bright", "short"],
        )

    def test_perfect_match_all_required_and_optional(self) -> None:
        """Test exact match (100%) with all required and all optional tags."""
        asset_tags: List[str] = ["upbeat", "corporate", "bright", "short"]
        score = self.group.matches_asset(asset_tags)
        self.assertAlmostEqual(score, 1.0, places=2)

    def test_exact_match_all_required_only(self) -> None:
        """Test exact match (100%) base with all required but no optional tags."""
        asset_tags: List[str] = ["upbeat", "corporate"]
        score = self.group.matches_asset(asset_tags)
        # All required match, no optional = 0.5 + 0 = 0.5 base
        # Wait, with required tags present, exact match is 0.5 + 0.5*optional_ratio
        # No optional = 0.5 + 0 = 0.5
        self.assertAlmostEqual(score, 0.5, places=2)

    def test_partial_match_half_required(self) -> None:
        """Test partial match when half of required tags match (50% band)."""
        asset_tags: List[str] = ["upbeat", "bright", "short"]
        score = self.group.matches_asset(asset_tags)
        # 1 of 2 required tags = 50% of required = 0.5 * 0.5 = 0.25
        self.assertAlmostEqual(score, 0.25, places=2)

    def test_partial_match_quarter_required(self) -> None:
        """Test partial match with more required tags."""
        group = AssetGroup(
            name="test",
            description="Test",
            category=AssetGroupCategory.MUSIC,
            required_tags=["a", "b", "c", "d"],
        )
        asset_tags: List[str] = ["a", "b"]  # 2 of 4 required
        score = group.matches_asset(asset_tags)
        # 2 of 4 = 50% of required = 0.5 * 0.5 = 0.25
        self.assertAlmostEqual(score, 0.25, places=2)

    def test_no_match_missing_all_required(self) -> None:
        """Test no match (0%) when no required tags present."""
        asset_tags: List[str] = ["bright", "short"]
        score = self.group.matches_asset(asset_tags)
        self.assertEqual(score, 0.0)

    def test_no_match_empty_asset_tags(self) -> None:
        """Test that empty asset tags returns 0.0."""
        asset_tags: List[str] = []
        score = self.group.matches_asset(asset_tags)
        self.assertEqual(score, 0.0)

    def test_no_match_none_asset_tags(self) -> None:
        """Test that None asset tags returns 0.0 (no crash)."""
        score = self.group.matches_asset(None)  # type: ignore
        self.assertEqual(score, 0.0)

    def test_no_required_tags_optional_only_scoring(self) -> None:
        """Test scoring when no required tags defined (uses optional)."""
        group_no_required = AssetGroup(
            name="sfx_group",
            description="Sound effects",
            category=AssetGroupCategory.SFX,
            optional_tags=["whoosh", "fast"],
        )
        # All optional match = 0.5 + 0.5*1.0 = 1.0
        asset_tags: List[str] = ["whoosh", "fast"]
        score = group_no_required.matches_asset(asset_tags)
        self.assertAlmostEqual(score, 1.0, places=2)

    def test_partial_optional_when_no_required(self) -> None:
        """Test scoring when no required tags and partial optional match."""
        group_no_required = AssetGroup(
            name="sfx_group",
            description="Sound effects",
            category=AssetGroupCategory.SFX,
            optional_tags=["whoosh", "fast", "loud"],
        )
        # 1 of 3 optional = 0.5 + 0.5*(1/3) = 0.5 + 0.167 = 0.667
        asset_tags: List[str] = ["whoosh"]
        score = group_no_required.matches_asset(asset_tags)
        self.assertAlmostEqual(score, 0.5 + (0.5 / 3), places=2)

    def test_case_insensitive_matching(self) -> None:
        """Test that matching is case-insensitive."""
        asset_tags: List[str] = ["UPBEAT", "Corporate", "BRIGHT"]
        score = self.group.matches_asset(asset_tags)
        self.assertAlmostEqual(score, 1.0, places=2)

    def test_none_in_asset_tags_filtered(self) -> None:
        """Test that None values in asset tags are filtered out."""
        asset_tags = ["upbeat", None, "corporate"]  # type: ignore
        score = self.group.matches_asset(asset_tags)
        self.assertAlmostEqual(score, 0.5, places=2)  # All required match


class TestAssetGroupSerialization(unittest.TestCase):
    """Test AssetGroup serialization."""

    def test_to_dict_basic(self) -> None:
        """Test basic serialization."""
        group = AssetGroup(
            name="test_group",
            description="Test description",
            category=AssetGroupCategory.MUSIC,
            required_tags=["test"],
        )
        result = group.to_dict()
        self.assertEqual(result["name"], "test_group")
        self.assertEqual(result["description"], "Test description")
        self.assertEqual(result["category"], "music")
        self.assertEqual(result["required_tags"], ["test"])
        self.assertEqual(result["optional_tags"], [])
        self.assertEqual(result["priority"], "medium")
        self.assertEqual(result["fallback_groups"], [])
        self.assertIsNone(result["duration_hint"])

    def test_to_dict_with_duration(self) -> None:
        """Test serialization with duration hint."""
        duration = DurationHint(exact="0:15", min_duration="0:10", max_duration="0:20")
        group = AssetGroup(
            name="test_group",
            description="Test description",
            category=AssetGroupCategory.SFX,
            required_tags=["sfx"],
            duration_hint=duration,
        )
        result = group.to_dict()
        self.assertIsNotNone(result["duration_hint"])
        self.assertEqual(result["duration_hint"]["exact"], 15)
        self.assertEqual(result["duration_hint"]["min"], 10)
        self.assertEqual(result["duration_hint"]["max"], 20)


if __name__ == "__main__":
    unittest.main()
