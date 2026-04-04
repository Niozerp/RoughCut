# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

#!/usr/bin/env python3
"""Tag storage and search module for SpacetimeDB integration.

Provides TagStorage class for persisting and querying AI-generated tags
for media assets in SpacetimeDB.
"""

from pathlib import Path
from typing import List, Optional, Dict, Set
from dataclasses import dataclass, field
from datetime import datetime

from ...utils.exceptions import AIError


@dataclass
class TaggedAsset:
    """Represents a media asset with AI-generated tags."""
    asset_id: str
    file_path: Path
    file_name: str
    category: str
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class TagStorage:
    """Storage layer for AI-generated tags with SpacetimeDB integration.
    
    Manages persistence and querying of tagged media assets.
    In-memory storage is used when SpacetimeDB is not available.
    """
    
    def __init__(self):
        """Initialize the tag storage."""
        # In-memory storage (to be replaced with SpacetimeDB)
        self._assets: Dict[str, TaggedAsset] = {}
        self._tag_index: Dict[str, Set[str]] = {}  # tag -> set of asset_ids
    
    def store_tags(
        self,
        asset_id: str,
        file_path: Path,
        category: str,
        tags: List[str],
        confidence: float = 0.0
    ) -> bool:
        """Store AI-generated tags for a media asset.
        
        Args:
            asset_id: Unique identifier for the asset
            file_path: Path to the media file
            category: Media category ("music", "sfx", "vfx")
            tags: List of AI-generated tags
            confidence: Confidence score for the tags
            
        Returns:
            True if storage succeeded, False otherwise
        """
        try:
            # Remove old tags from index if updating
            if asset_id in self._assets:
                old_asset = self._assets[asset_id]
                for tag in old_asset.tags:
                    if tag in self._tag_index and asset_id in self._tag_index[tag]:
                        self._tag_index[tag].discard(asset_id)
            
            # Create/update the tagged asset
            asset = TaggedAsset(
                asset_id=asset_id,
                file_path=file_path,
                file_name=file_path.name,
                category=category,
                tags=tags,
                confidence=confidence,
                updated_at=datetime.now()
            )
            
            self._assets[asset_id] = asset
            
            # Update tag index
            for tag in tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(asset_id)
            
            return True
            
        except Exception as e:
            raise AIError(
                code="TAG_STORAGE_ERROR",
                category="storage",
                message=f"Failed to store tags: {str(e)}",
                recoverable=True,
                suggestion="Check storage configuration and retry"
            )
    
    def search_by_tags(
        self,
        tags: List[str],
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[TaggedAsset]:
        """Search for assets matching the given tags.
        
        Returns assets that match ANY of the provided tags,
        ordered by number of matching tags (most relevant first).
        
        Args:
            tags: List of tags to search for
            category: Optional category filter ("music", "sfx", "vfx")
            limit: Maximum number of results to return
            
        Returns:
            List of TaggedAsset objects ordered by relevance
        """
        if not tags:
            return []
        
        # Find all asset IDs that match any tag
        matching_assets: Dict[str, int] = {}  # asset_id -> match count
        
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in self._tag_index:
                for asset_id in self._tag_index[tag_lower]:
                    matching_assets[asset_id] = matching_assets.get(asset_id, 0) + 1
        
        # Get the actual assets and apply category filter
        results = []
        for asset_id, match_count in matching_assets.items():
            asset = self._assets.get(asset_id)
            if asset:
                if category is None or asset.category == category:
                    # Store match count for sorting
                    results.append((match_count, asset))
        
        # Sort by match count (relevance) descending
        results.sort(key=lambda x: x[0], reverse=True)
        
        # Return limited results
        return [asset for _, asset in results[:limit]]
    
    def get_asset_tags(self, asset_id: str) -> Optional[List[str]]:
        """Get tags for a specific asset.
        
        Args:
            asset_id: Unique identifier for the asset
            
        Returns:
            List of tags or None if asset not found
        """
        asset = self._assets.get(asset_id)
        return asset.tags if asset else None
    
    def get_all_tags(self, category: Optional[str] = None) -> List[str]:
        """Get all unique tags in the system.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of unique tag strings
        """
        if category:
            # Filter tags by category
            tags = set()
            for asset in self._assets.values():
                if asset.category == category:
                    tags.update(asset.tags)
            return sorted(list(tags))
        else:
            # Return all tags
            return sorted(list(self._tag_index.keys()))
    
    def delete_asset(self, asset_id: str) -> bool:
        """Remove an asset and its tags from storage.
        
        Args:
            asset_id: Unique identifier for the asset
            
        Returns:
            True if asset was found and removed, False otherwise
        """
        if asset_id not in self._assets:
            return False
        
        asset = self._assets[asset_id]
        
        # Remove from tag index
        for tag in asset.tags:
            if tag in self._tag_index and asset_id in self._tag_index[tag]:
                self._tag_index[tag].discard(asset_id)
                # Clean up empty tag entries
                if not self._tag_index[tag]:
                    del self._tag_index[tag]
        
        # Remove from assets
        del self._assets[asset_id]
        
        return True
    
    def clear(self) -> None:
        """Clear all stored assets and tags (mainly for testing)."""
        self._assets.clear()
        self._tag_index.clear()
