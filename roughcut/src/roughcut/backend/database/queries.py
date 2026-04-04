"""Query operations for SpacetimeDB.

Provides high-level query builders and optimized queries for
common media asset retrieval patterns.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Union

from .models import MediaAsset
from .spacetime_client import SpacetimeClient, QueryResult

logger = logging.getLogger(__name__)


class AssetQueryBuilder:
    """Builder for constructing asset queries.
    
    Provides a fluent interface for building complex queries
    with multiple filters and sorting options.
    
    Example:
        >>> query = AssetQueryBuilder(client)
        ...     .category("music")
        ...     .tags(["upbeat", "energetic"])
        ...     .limit(100)
        >>> result = await query.execute()
        >>> if result:
        ...     assets = result.assets
    """
    
    # Valid categories per specification
    VALID_CATEGORIES: Set[str] = {"music", "sfx", "vfx"}
    DEFAULT_LIMIT: int = 1000
    MAX_LIMIT: int = 10000
    
    def __init__(self, client: SpacetimeClient) -> None:
        """Initialize query builder.
        
        Args:
            client: SpacetimeDB client instance
            
        Raises:
            TypeError: If client is not a SpacetimeClient instance
        """
        if not isinstance(client, SpacetimeClient):
            raise TypeError(f"client must be SpacetimeClient, got {type(client).__name__}")
        
        self.client: SpacetimeClient = client
        self._category: Optional[str] = None
        self._tags: List[str] = []
        self._limit: int = self.DEFAULT_LIMIT
        self._file_hash: Optional[str] = None
    
    def category(self, category: str) -> 'AssetQueryBuilder':
        """Filter by asset category.
        
        Args:
            category: One of "music", "sfx", "vfx" (case-insensitive)
            
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If category is invalid
            TypeError: If category is not a string
        """
        if not isinstance(category, str):
            raise TypeError(f"category must be string, got {type(category).__name__}")
        
        normalized = category.lower().strip()
        
        if normalized not in self.VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. Must be one of: "
                f"{', '.join(sorted(self.VALID_CATEGORIES))}"
            )
        
        self._category = normalized
        return self
    
    def tags(self, tags: List[str]) -> 'AssetQueryBuilder':
        """Filter by AI-generated tags.
        
        Args:
            tags: List of tag names to match (case-insensitive)
            
        Returns:
            Self for method chaining
            
        Raises:
            TypeError: If tags is not a list
            ValueError: If any tag is invalid
        """
        if not isinstance(tags, list):
            raise TypeError(f"tags must be a list, got {type(tags).__name__}")
        
        normalized_tags: List[str] = []
        for tag in tags:
            if not isinstance(tag, str):
                raise TypeError(f"All tags must be strings, got {type(tag).__name__}")
            
            stripped = tag.lower().strip()
            if stripped:  # Skip empty tags
                normalized_tags.append(stripped)
        
        # Remove duplicates while preserving order
        seen: Set[str] = set()
        self._tags = []
        for tag in normalized_tags:
            if tag not in seen:
                seen.add(tag)
                self._tags.append(tag)
        
        return self
    
    def limit(self, limit: Union[int, str]) -> 'AssetQueryBuilder':
        """Set maximum results.
        
        Args:
            limit: Maximum number of assets to return (1-10000)
            
        Returns:
            Self for method chaining
            
        Raises:
            TypeError: If limit is not an integer
            ValueError: If limit is not in valid range
        """
        # Convert string to int if needed
        if isinstance(limit, str):
            try:
                limit = int(limit)
            except ValueError:
                raise TypeError(f"limit must be an integer, got string '{limit}'")
        
        if not isinstance(limit, int):
            raise TypeError(f"limit must be an integer, got {type(limit).__name__}")
        
        if limit < 1:
            raise ValueError(f"limit must be positive, got {limit}")
        
        if limit > self.MAX_LIMIT:
            raise ValueError(
                f"limit {limit} exceeds maximum {self.MAX_LIMIT}. "
                "Use pagination for large result sets."
            )
        
        self._limit = limit
        return self
    
    def file_hash(self, file_hash: str) -> 'AssetQueryBuilder':
        """Filter by exact file hash.
        
        Note: This filter is applied client-side after fetching from DB.
        For large datasets, consider using a database index instead.
        
        Args:
            file_hash: MD5 hash to match (32 hex characters)
            
        Returns:
            Self for method chaining
            
        Raises:
            TypeError: If file_hash is not a string
            ValueError: If file_hash format is invalid
        """
        if not isinstance(file_hash, str):
            raise TypeError(f"file_hash must be a string, got {type(file_hash).__name__}")
        
        # Validate MD5 format (32 hex characters)
        cleaned = file_hash.strip().lower()
        if len(cleaned) != 32 or not all(c in '0123456789abcdef' for c in cleaned):
            raise ValueError(
                f"Invalid MD5 hash format: '{file_hash}'. "
                "Expected 32 hexadecimal characters."
            )
        
        self._file_hash = cleaned
        return self
    
    async def execute(self) -> QueryResult:
        """Execute the built query.
        
        Returns:
            QueryResult containing assets or error information
        """
        try:
            result = await self.client.query_assets(
                category=self._category,
                tags=self._tags if self._tags else None,
                limit=self._limit
            )
            
            # Apply client-side file hash filter if specified
            if self._file_hash and result.assets:
                result.assets = [
                    a for a in result.assets
                    if a.file_hash.lower() == self._file_hash
                ]
                result.total_count = len(result.assets)
            
            return result
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return QueryResult(assets=[], error=str(e))
    
    async def count(self) -> int:
        """Get count of matching assets without retrieving all data.
        
        This is more efficient than execute() when you only need the count.
        
        Returns:
            Number of matching assets (0 if error)
        """
        try:
            counts = await self.client.get_asset_counts()
            
            if self._category:
                return getattr(counts, self._category, 0)
            return counts.total
            
        except Exception as e:
            logger.error(f"Count query failed: {e}")
            return 0
    
    def reset(self) -> 'AssetQueryBuilder':
        """Reset all filters to defaults.
        
        Returns:
            Self for method chaining
        """
        self._category = None
        self._tags = []
        self._limit = self.DEFAULT_LIMIT
        self._file_hash = None
        return self


async def get_assets_by_category(
    client: SpacetimeClient,
    category: str,
    limit: int = 1000
) -> QueryResult:
    """Convenience function to get assets by category.
    
    Args:
        client: SpacetimeDB client
        category: Asset category (music, sfx, vfx)
        limit: Maximum results (1-10000)
        
    Returns:
        QueryResult with matching assets
    """
    try:
        builder = AssetQueryBuilder(client)
        return await builder.category(category).limit(limit).execute()
    except (TypeError, ValueError) as e:
        return QueryResult(assets=[], error=str(e))
    except Exception as e:
        logger.error(f"get_assets_by_category failed: {e}")
        return QueryResult(assets=[], error=str(e))


async def get_assets_by_tags(
    client: SpacetimeClient,
    tags: List[str],
    match_all: bool = False,
    limit: int = 1000
) -> List[MediaAsset]:
    """Get assets matching specified tags.
    
    Note: When match_all=True, filtering is done client-side which may
    be inefficient for large datasets. Consider using the database directly.
    
    Args:
        client: SpacetimeDB client
        tags: Tags to search for (case-insensitive)
        match_all: If True, asset must have ALL tags; if False, ANY tag
        limit: Maximum results (1-10000)
        
    Returns:
        List of matching MediaAsset objects (empty list if error)
    """
    if not tags:
        return []
    
    try:
        # Query with first tag (database filter)
        result = await client.query_assets(
            tags=[tags[0]],  # Primary filter in DB
            limit=limit
        )
        
        if not result or not result.assets:
            return []
        
        if match_all and len(tags) > 1:
            # Client-side filtering for remaining tags
            required_tags: Set[str] = set(t.lower().strip() for t in tags if t)
            
            filtered = []
            for asset in result.assets:
                asset_tags: Set[str] = set(t.lower() for t in asset.ai_tags)
                if required_tags.issubset(asset_tags):
                    filtered.append(asset)
            
            return filtered
        
        return result.assets
        
    except Exception as e:
        logger.error(f"get_assets_by_tags failed: {e}")
        return []


async def asset_exists(
    client: SpacetimeClient,
    file_hash: str
) -> Optional[MediaAsset]:
    """Check if an asset with given hash exists.
    
    Warning: This queries up to 10000 assets and does a linear search.
    For production use, add a database index on file_hash.
    
    Args:
        client: SpacetimeDB client
        file_hash: MD5 hash to check (32 hex characters)
        
    Returns:
        Existing asset if found, None otherwise or on error
    """
    # Validate hash format
    if not isinstance(file_hash, str):
        logger.error(f"Invalid file_hash type: {type(file_hash)}")
        return None
    
    cleaned = file_hash.strip().lower()
    if len(cleaned) != 32:
        logger.error(f"Invalid MD5 hash length: {len(cleaned)}")
        return None
    
    try:
        # Query all assets with limit (inefficient for large datasets)
        # TODO: Add database index for efficient hash lookup
        result = await client.query_assets(limit=10000)
        
        if not result or result.error:
            return None
        
        for asset in result.assets:
            if asset.file_hash.lower() == cleaned:
                return asset
        
        return None
        
    except Exception as e:
        logger.error(f"asset_exists query failed: {e}")
        return None


async def get_duplicate_assets(
    client: SpacetimeClient,
    limit: int = 10000
) -> Dict[str, List[MediaAsset]]:
    """Find assets with duplicate file hashes.
    
    Warning: This loads up to `limit` assets into memory.
    For large datasets, implement server-side aggregation.
    
    Args:
        client: SpacetimeDB client
        limit: Maximum assets to check (1-10000)
        
    Returns:
        Dictionary mapping file_hash to list of duplicate assets
    """
    if not (1 <= limit <= 10000):
        logger.warning(f"Invalid limit {limit}, using 10000")
        limit = 10000
    
    try:
        result = await client.query_assets(limit=limit)
        
        if not result or result.error or not result.assets:
            return {}
        
        # Group by hash
        hash_map: Dict[str, List[MediaAsset]] = {}
        for asset in result.assets:
            h = asset.file_hash.lower()
            if h not in hash_map:
                hash_map[h] = []
            hash_map[h].append(asset)
        
        # Filter to only duplicates
        duplicates = {
            h: assets for h, assets in hash_map.items()
            if len(assets) > 1
        }
        
        if duplicates:
            logger.info(f"Found {len(duplicates)} duplicate hashes")
        
        return duplicates
        
    except Exception as e:
        logger.error(f"get_duplicate_assets failed: {e}")
        return {}


__all__ = [
    'AssetQueryBuilder',
    'get_assets_by_category',
    'get_assets_by_tags',
    'asset_exists',
    'get_duplicate_assets'
]
