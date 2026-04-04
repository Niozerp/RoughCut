"""Asset matching engine for matching indexed assets to template asset groups."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, Set

if TYPE_CHECKING:
    from .models import AssetGroup


class DatabaseClient(Protocol):
    """Protocol for database client used by AssetMatcher."""

    def get_assets_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get assets by category from database."""
        ...


@dataclass
class MatchedAsset:
    """Result of matching an asset to an asset group."""

    asset_id: str
    file_path: str
    file_name: str
    tags: List[str]
    score: float  # 0.0-1.0 match score
    category: str  # music, sfx, vfx

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "asset_id": self.asset_id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "tags": self.tags,
            "score": self.score,
            "category": self.category,
        }


class AssetMatcher:
    """
    Matches indexed media assets to template asset groups.

    Used by AI in Epic 5 for contextual asset suggestions.
    """

    def __init__(self, database_client: DatabaseClient) -> None:
        self.db = database_client

    def match_assets_for_group(
        self,
        asset_group: "AssetGroup",
        limit: int = 5,
        min_score: float = 0.5,
    ) -> List[MatchedAsset]:
        """
        Find matching assets for an asset group.

        Args:
            asset_group: The asset group to match against
            limit: Maximum number of results to return (must be >= 1)
            min_score: Minimum match score to include (0.0-1.0)

        Returns:
            List of MatchedAsset objects, sorted by score descending
        """
        # Validate inputs
        if not isinstance(limit, int) or limit < 1:
            raise ValueError(f"limit must be a positive integer, got {limit}")
        if not isinstance(min_score, (int, float)) or min_score < 0.0 or min_score > 1.0:
            raise ValueError(f"min_score must be between 0.0 and 1.0, got {min_score}")
        
        # Query database for assets in matching category
        category_filter = asset_group.category.value
        assets = self.db.get_assets_by_category(category_filter)
        
        # Handle None return from database
        if assets is None:
            return []

        # Score each asset
        scored_matches: List[MatchedAsset] = []
        for asset in assets:
            # Handle None ai_tags (use or [] pattern)
            ai_tags_raw = asset.get("ai_tags")
            ai_tags: List[str] = ai_tags_raw if isinstance(ai_tags_raw, list) else []
            score = asset_group.matches_asset(ai_tags)
            if score >= min_score:
                scored_matches.append(
                    MatchedAsset(
                        asset_id=str(asset.get("id", "")),
                        file_path=str(asset.get("file_path", "")),
                        file_name=str(asset.get("file_name", "")),
                        tags=ai_tags,
                        score=score,
                        category=str(asset.get("category", category_filter)),
                    )
                )

        # Sort by score descending and return top matches
        scored_matches.sort(key=lambda x: (x.score, x.file_name), reverse=True)
        return scored_matches[:limit]

    def match_all_groups(
        self,
        asset_groups: List["AssetGroup"],
        limit_per_group: int = 3,
    ) -> Dict[str, List[MatchedAsset]]:
        """
        Match assets for multiple asset groups.

        Returns:
            Dictionary mapping group name to list of matched assets
        """
        results: Dict[str, List[MatchedAsset]] = {}
        for group in asset_groups:
            results[group.name] = self.match_assets_for_group(
                group, limit=limit_per_group
            )
        return results

    def get_best_match(
        self, asset_group: "AssetGroup"
    ) -> Optional[MatchedAsset]:
        """
        Get single best matching asset for a group.

        Returns:
            Best matched asset or None if no matches
        """
        matches = self.match_assets_for_group(asset_group, limit=1)
        return matches[0] if matches else None

    def match_with_fallback(
        self,
        asset_group: "AssetGroup",
        all_groups: Dict[str, "AssetGroup"],
        limit: int = 5,
        min_score: float = 0.5,
        _visited: Optional[Set[str]] = None,
    ) -> List[MatchedAsset]:
        """
        Match assets with fallback to other groups if no matches found.

        Args:
            asset_group: Primary asset group to match
            all_groups: Dictionary of all available asset groups
            limit: Maximum number of results
            min_score: Minimum match score
            _visited: Internal set to track visited groups (prevents infinite recursion)

        Returns:
            List of matched assets, potentially from fallback groups
        """
        # Initialize visited set on first call
        if _visited is None:
            _visited = set()
        
        # Check for circular reference
        if asset_group.name in _visited:
            return []  # Already visited this group in fallback chain
        _visited.add(asset_group.name)
        
        # Validate inputs
        if not isinstance(limit, int) or limit < 1:
            raise ValueError(f"limit must be a positive integer, got {limit}")
        if not isinstance(min_score, (int, float)) or min_score < 0.0 or min_score > 1.0:
            raise ValueError(f"min_score must be between 0.0 and 1.0, got {min_score}")
        
        # Try primary group first
        matches = self.match_assets_for_group(asset_group, limit=limit, min_score=min_score)
        if matches:
            return matches

        # If no matches and fallback groups specified, try them
        if asset_group.fallback_groups:
            for fallback_name in asset_group.fallback_groups:
                if fallback_name in all_groups and fallback_name not in _visited:
                    fallback_group = all_groups[fallback_name]
                    matches = self.match_with_fallback(
                        fallback_group, all_groups, limit=limit, min_score=min_score, _visited=_visited
                    )
                    if matches:
                        return matches

        return []
