"""Unit tests for AssetMatcher."""

import unittest
from typing import Any, Dict, List

from roughcut.backend.formats.matcher import AssetMatcher, MatchedAsset
from roughcut.backend.formats.models import AssetGroup, AssetGroupCategory


class MockDatabaseClient:
    """Mock database client for testing."""

    def __init__(self, assets: List[Dict[str, Any]]) -> None:
        self.assets = assets

    def get_assets_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Return assets matching the category."""
        return [a for a in self.assets if a.get("category") == category]


class TestMatchedAsset(unittest.TestCase):
    """Test MatchedAsset dataclass."""

    def test_to_dict(self) -> None:
        """Test serialization."""
        asset = MatchedAsset(
            asset_id="asset_001",
            file_path="/music/upbeat.wav",
            file_name="upbeat.wav",
            tags=["upbeat", "corporate"],
            score=0.95,
            category="music",
        )
        result = asset.to_dict()
        self.assertEqual(result["asset_id"], "asset_001")
        self.assertEqual(result["file_path"], "/music/upbeat.wav")
        self.assertEqual(result["file_name"], "upbeat.wav")
        self.assertEqual(result["tags"], ["upbeat", "corporate"])
        self.assertEqual(result["score"], 0.95)
        self.assertEqual(result["category"], "music")


class TestAssetMatcher(unittest.TestCase):
    """Test AssetMatcher functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_assets: List[Dict[str, Any]] = [
            {
                "id": "asset_001",
                "file_path": "/music/corporate_bright.wav",
                "file_name": "corporate_bright.wav",
                "ai_tags": ["corporate", "upbeat", "bright"],
                "category": "music",
            },
            {
                "id": "asset_002",
                "file_name": "corporate_subtle.wav",
                "file_path": "/music/corporate_subtle.wav",
                "ai_tags": ["corporate", "subtle"],
                "category": "music",
            },
            {
                "id": "asset_003",
                "file_name": "upbeat_fun.wav",
                "file_path": "/music/upbeat_fun.wav",
                "ai_tags": ["upbeat", "fun"],
                "category": "music",
            },
            {
                "id": "asset_004",
                "file_name": "whoosh.wav",
                "file_path": "/sfx/whoosh.wav",
                "ai_tags": ["whoosh", "transition"],
                "category": "sfx",
            },
        ]
        self.db = MockDatabaseClient(self.mock_assets)
        self.matcher = AssetMatcher(self.db)

    def test_match_assets_for_group_basic(self) -> None:
        """Test basic asset matching."""
        group = AssetGroup(
            name="intro_music",
            description="Corporate intro music",
            category=AssetGroupCategory.MUSIC,
            required_tags=["corporate"],
        )
        matches = self.matcher.match_assets_for_group(group, limit=5, min_score=0.5)

        self.assertEqual(len(matches), 2)
        # corporate_bright should score higher due to more tags
        self.assertEqual(matches[0].file_name, "corporate_bright.wav")
        self.assertEqual(matches[1].file_name, "corporate_subtle.wav")

    def test_match_respects_category(self) -> None:
        """Test that matching respects asset category."""
        group = AssetGroup(
            name="sfx_group",
            description="Sound effects",
            category=AssetGroupCategory.SFX,
            required_tags=["whoosh"],
        )
        matches = self.matcher.match_assets_for_group(group, limit=5, min_score=0.5)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].file_name, "whoosh.wav")

    def test_match_limit(self) -> None:
        """Test that limit parameter is respected."""
        group = AssetGroup(
            name="music_group",
            description="Any music",
            category=AssetGroupCategory.MUSIC,
            required_tags=["upbeat"],
        )
        matches = self.matcher.match_assets_for_group(group, limit=1, min_score=0.5)

        self.assertEqual(len(matches), 1)

    def test_match_min_score(self) -> None:
        """Test that min_score filters low matches."""
        group = AssetGroup(
            name="strict_group",
            description="Strict matching",
            category=AssetGroupCategory.MUSIC,
            required_tags=["upbeat", "corporate", "bright"],
        )
        matches = self.matcher.match_assets_for_group(group, limit=5, min_score=0.9)

        # Only corporate_bright.wav matches all required + optional
        self.assertEqual(len(matches), 1)

    def test_match_no_results(self) -> None:
        """Test matching when no assets match."""
        group = AssetGroup(
            name="no_match_group",
            description="Non-existent tags",
            category=AssetGroupCategory.MUSIC,
            required_tags=["nonexistent"],
        )
        matches = self.matcher.match_assets_for_group(group, limit=5, min_score=0.5)

        self.assertEqual(len(matches), 0)

    def test_match_all_groups(self) -> None:
        """Test matching for multiple groups."""
        groups = [
            AssetGroup(
                name="music_group",
                description="Music",
                category=AssetGroupCategory.MUSIC,
                required_tags=["upbeat"],
            ),
            AssetGroup(
                name="sfx_group",
                description="SFX",
                category=AssetGroupCategory.SFX,
                required_tags=["whoosh"],
            ),
        ]
        results = self.matcher.match_all_groups(groups, limit_per_group=5)

        self.assertEqual(len(results), 2)
        self.assertIn("music_group", results)
        self.assertIn("sfx_group", results)
        self.assertEqual(len(results["music_group"]), 2)
        self.assertEqual(len(results["sfx_group"]), 1)

    def test_get_best_match(self) -> None:
        """Test getting single best match."""
        group = AssetGroup(
            name="intro_music",
            description="Corporate intro music",
            category=AssetGroupCategory.MUSIC,
            required_tags=["corporate"],
            optional_tags=["bright"],
        )
        best = self.matcher.get_best_match(group)

        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.file_name, "corporate_bright.wav")
        self.assertGreater(best.score, 0.9)

    def test_get_best_match_no_results(self) -> None:
        """Test getting best match when none exist."""
        group = AssetGroup(
            name="no_match_group",
            description="Non-existent tags",
            category=AssetGroupCategory.MUSIC,
            required_tags=["nonexistent"],
        )
        best = self.matcher.get_best_match(group)

        self.assertIsNone(best)

    def test_match_with_fallback(self) -> None:
        """Test matching with fallback groups."""
        # Create a group that won't match, with a fallback that will
        primary_group = AssetGroup(
            name="primary",
            description="Primary group",
            category=AssetGroupCategory.MUSIC,
            required_tags=["nonexistent"],
            fallback_groups=["fallback"],
        )
        fallback_group = AssetGroup(
            name="fallback",
            description="Fallback group",
            category=AssetGroupCategory.MUSIC,
            required_tags=["upbeat"],
        )

        all_groups = {"primary": primary_group, "fallback": fallback_group}
        matches = self.matcher.match_with_fallback(
            primary_group, all_groups, limit=5, min_score=0.5
        )

        # Should get matches from fallback group
        self.assertGreater(len(matches), 0)

    def test_match_results_sorted_by_score(self) -> None:
        """Test that results are sorted by score descending."""
        group = AssetGroup(
            name="intro_music",
            description="Corporate intro music",
            category=AssetGroupCategory.MUSIC,
            required_tags=["corporate"],
            optional_tags=["bright"],
        )
        matches = self.matcher.match_assets_for_group(group, limit=5, min_score=0.5)

        # Verify descending order
        for i in range(len(matches) - 1):
            self.assertGreaterEqual(matches[i].score, matches[i + 1].score)


class TestAssetMatcherEdgeCases(unittest.TestCase):
    """Test edge cases for AssetMatcher."""

    def test_empty_database(self) -> None:
        """Test matching against empty database."""
        db = MockDatabaseClient([])
        matcher = AssetMatcher(db)
        group = AssetGroup(
            name="test_group",
            description="Test",
            category=AssetGroupCategory.MUSIC,
            required_tags=["upbeat"],
        )
        matches = matcher.match_assets_for_group(group)
        self.assertEqual(len(matches), 0)

    def test_assets_without_ai_tags(self) -> None:
        """Test handling assets without ai_tags field."""
        assets = [
            {
                "id": "asset_001",
                "file_name": "no_tags.wav",
                "file_path": "/music/no_tags.wav",
                "category": "music",
                # No ai_tags key
            }
        ]
        db = MockDatabaseClient(assets)
        matcher = AssetMatcher(db)
        group = AssetGroup(
            name="test_group",
            description="Test",
            category=AssetGroupCategory.MUSIC,
            required_tags=["upbeat"],
        )
        matches = matcher.match_assets_for_group(group)
        self.assertEqual(len(matches), 0)

    def test_assets_with_empty_tags(self) -> None:
        """Test handling assets with empty ai_tags."""
        assets = [
            {
                "id": "asset_001",
                "file_name": "empty_tags.wav",
                "file_path": "/music/empty_tags.wav",
                "category": "music",
                "ai_tags": [],
            }
        ]
        db = MockDatabaseClient(assets)
        matcher = AssetMatcher(db)
        group = AssetGroup(
            name="test_group",
            description="Test",
            category=AssetGroupCategory.MUSIC,
            required_tags=["upbeat"],
        )
        matches = matcher.match_assets_for_group(group)
        self.assertEqual(len(matches), 0)


if __name__ == "__main__":
    unittest.main()
