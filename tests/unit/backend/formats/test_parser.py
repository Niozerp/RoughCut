"""Unit tests for AssetGroupParser."""

import unittest
from typing import List

from roughcut.backend.formats.models import AssetGroup, AssetGroupCategory, AssetGroupParseError
from roughcut.backend.formats.parser import AssetGroupParser


class TestAssetGroupParser(unittest.TestCase):
    """Test AssetGroupParser functionality."""

    def setUp(self) -> None:
        """Set up test fixture."""
        self.parser = AssetGroupParser()

    def test_parse_simple_group(self) -> None:
        """Test parsing a simple YAML group definition."""
        yaml_content = """
intro_music:
    description: Upbeat attention grabber
    tags: [upbeat, corporate]
"""
        groups: List[AssetGroup] = self.parser.parse_yaml_block(yaml_content)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].name, "intro_music")
        self.assertEqual(groups[0].description, "Upbeat attention grabber")
        self.assertEqual(groups[0].required_tags, ["upbeat", "corporate"])

    def test_parse_multiple_groups(self) -> None:
        """Test parsing multiple groups."""
        yaml_content = """
intro_music:
    description: Upbeat intro
    tags: [upbeat, corporate]

outro_chime:
    description: Subtle outro sound
    tags: [subtle, chime]
    category: sfx
"""
        groups: List[AssetGroup] = self.parser.parse_yaml_block(yaml_content)
        self.assertEqual(len(groups), 2)

        intro = next(g for g in groups if g.name == "intro_music")
        self.assertEqual(intro.category, AssetGroupCategory.MUSIC)

        outro = next(g for g in groups if g.name == "outro_chime")
        self.assertEqual(outro.category, AssetGroupCategory.SFX)

    def test_parse_category_inference(self) -> None:
        """Test category inference from group name."""
        yaml_content = """
intro_music:
    description: Music for intro
    tags: [upbeat]

whoosh_sfx:
    description: Whoosh sound
    tags: [whoosh]

lower_third_vfx:
    description: Lower third graphic
    tags: [graphic]

wipe_transition:
    description: Transition effect
    tags: [transition]
"""
        groups: List[AssetGroup] = self.parser.parse_yaml_block(yaml_content)

        music_group = next(g for g in groups if g.name == "intro_music")
        self.assertEqual(music_group.category, AssetGroupCategory.MUSIC)

        sfx_group = next(g for g in groups if g.name == "whoosh_sfx")
        self.assertEqual(sfx_group.category, AssetGroupCategory.SFX)

        vfx_group = next(g for g in groups if g.name == "lower_third_vfx")
        self.assertEqual(vfx_group.category, AssetGroupCategory.VFX)

        trans_group = next(g for g in groups if g.name == "wipe_transition")
        self.assertEqual(trans_group.category, AssetGroupCategory.TRANSITION)

    def test_parse_required_vs_optional_tags(self) -> None:
        """Test parsing separate required and optional tags."""
        yaml_content = """
intro_music:
    description: Corporate intro
    required_tags: [corporate, upbeat]
    optional_tags: [bright, short]
"""
        groups: List[AssetGroup] = self.parser.parse_yaml_block(yaml_content)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].required_tags, ["corporate", "upbeat"])
        self.assertEqual(groups[0].optional_tags, ["bright", "short"])

    def test_parse_duration_string(self) -> None:
        """Test parsing duration as string."""
        yaml_content = """
intro_music:
    description: Short intro
    tags: [upbeat]
    duration: 0:15
"""
        groups: List[AssetGroup] = self.parser.parse_yaml_block(yaml_content)
        self.assertIsNotNone(groups[0].duration_hint)
        assert groups[0].duration_hint is not None
        self.assertEqual(groups[0].duration_hint.exact, 15)

    def test_parse_duration_dict(self) -> None:
        """Test parsing duration as dictionary."""
        yaml_content = """
intro_music:
    description: Variable intro
    tags: [upbeat]
    duration:
        min: 0:10
        max: 0:30
        flexible: true
"""
        groups: List[AssetGroup] = self.parser.parse_yaml_block(yaml_content)
        self.assertIsNotNone(groups[0].duration_hint)
        assert groups[0].duration_hint is not None
        self.assertEqual(groups[0].duration_hint.min, 10)
        self.assertEqual(groups[0].duration_hint.max, 30)
        self.assertTrue(groups[0].duration_hint.flexible)

    def test_parse_priority(self) -> None:
        """Test parsing priority field."""
        yaml_content = """
intro_music:
    description: High priority intro
    tags: [upbeat]
    priority: high
"""
        groups: List[AssetGroup] = self.parser.parse_yaml_block(yaml_content)
        self.assertEqual(groups[0].priority, "high")

    def test_parse_fallback_groups(self) -> None:
        """Test parsing fallback_groups."""
        yaml_content = """
primary_music:
    description: Primary music
    tags: [upbeat]
    fallback_groups: [backup_music, generic_music]
"""
        groups: List[AssetGroup] = self.parser.parse_yaml_block(yaml_content)
        self.assertEqual(groups[0].fallback_groups, ["backup_music", "generic_music"])

    def test_parse_comma_separated_tags(self) -> None:
        """Test parsing comma-separated tags string."""
        yaml_content = """
intro_music:
    description: Intro music
    tags: "upbeat, corporate, bright"
"""
        groups: List[AssetGroup] = self.parser.parse_yaml_block(yaml_content)
        self.assertEqual(groups[0].required_tags, ["upbeat", "corporate", "bright"])

    def test_invalid_yaml_raises(self) -> None:
        """Test that invalid YAML raises AssetGroupParseError."""
        yaml_content = "invalid: [unclosed"
        with self.assertRaises(AssetGroupParseError):
            self.parser.parse_yaml_block(yaml_content)

    def test_non_dict_yaml_raises(self) -> None:
        """Test that non-dictionary YAML raises AssetGroupParseError."""
        yaml_content = "[list, not, dict]"
        with self.assertRaises(AssetGroupParseError):
            self.parser.parse_yaml_block(yaml_content)

    def test_missing_required_field_skips(self) -> None:
        """Test that groups with missing required fields are skipped."""
        yaml_content = """
valid_group:
    description: Valid group
    tags: [upbeat]

invalid_group:
    description: Missing tags
"""
        # Should only parse the valid group
        groups: List[AssetGroup] = self.parser.parse_yaml_block(yaml_content)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].name, "valid_group")

    def test_invalid_group_definition_skips(self) -> None:
        """Test that invalid group definitions are skipped."""
        yaml_content = """
valid_group:
    description: Valid group
    tags: [upbeat]

invalid_group: "just a string, not a dict"
"""
        groups: List[AssetGroup] = self.parser.parse_yaml_block(yaml_content)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].name, "valid_group")

    def test_invalid_category_skips(self) -> None:
        """Test that groups with invalid category are skipped."""
        yaml_content = """
invalid_group:
    description: Invalid category
    tags: [upbeat]
    category: invalid_category
"""
        groups: List[AssetGroup] = self.parser.parse_yaml_block(yaml_content)
        self.assertEqual(len(groups), 0)


class TestAssetGroupParserFullTemplate(unittest.TestCase):
    """Test parsing from full template markdown format."""

    def setUp(self) -> None:
        """Set up test fixture."""
        self.parser = AssetGroupParser()

    def test_parse_from_markdown_yaml_block(self) -> None:
        """Test parsing YAML content extracted from markdown code block."""
        # Simulating YAML content extracted from markdown
        yaml_content = """
intro_music:
    description: Upbeat attention-grabbing music for the intro
    tags: [corporate, upbeat, bright]
    duration: 0:15
    priority: high

narrative_bed:
    description: Subtle background music during narration
    tags: [subtle, background]
    required_tags: [background]
    optional_tags: [subtle, calm, corporate]
    category: music
    duration:
        min: 0:30
        max: 2:00
        flexible: true

outro_chime:
    description: Subtle sound to close the video
    tags: [chime, subtle]
    category: sfx
    duration: 0:03
    priority: medium
    fallback_groups: [intro_music]
"""
        groups: List[AssetGroup] = self.parser.parse_yaml_block(yaml_content)

        self.assertEqual(len(groups), 3)

        intro = next(g for g in groups if g.name == "intro_music")
        self.assertEqual(intro.category, AssetGroupCategory.MUSIC)
        self.assertEqual(intro.required_tags, ["corporate", "upbeat", "bright"])
        assert intro.duration_hint is not None
        self.assertEqual(intro.duration_hint.exact, 15)

        narrative = next(g for g in groups if g.name == "narrative_bed")
        self.assertEqual(narrative.required_tags, ["background"])
        self.assertEqual(narrative.optional_tags, ["subtle", "calm", "corporate"])

        outro = next(g for g in groups if g.name == "outro_chime")
        self.assertEqual(outro.category, AssetGroupCategory.SFX)
        self.assertEqual(outro.fallback_groups, ["intro_music"])


if __name__ == "__main__":
    unittest.main()
