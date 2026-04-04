"""Asset counting service for media library dashboard.

Provides efficient counting and caching of media assets by category
(Music, SFX, VFX) with support for real-time updates.
"""

from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict
import threading

from ..database.models import MediaAsset
from ...utils.formatters import format_number


__all__ = ['CategoryCount', 'AssetCounts', 'AssetCounter']


@dataclass
class CategoryCount:
    """Count for a single category.
    
    Attributes:
        category: Asset category (music, sfx, vfx)
        count: Number of assets in this category
        formatted: Human-readable formatted count (e.g., "12,437")
    """
    category: str
    count: int
    formatted: str


@dataclass 
class AssetCounts:
    """Complete asset count snapshot for dashboard.
    
    Attributes:
        music: Number of music assets
        sfx: Number of SFX assets
        vfx: Number of VFX assets
        total: Total number of all assets
        last_updated: Timestamp when counts were calculated (UTC)
    """
    music: int
    sfx: int
    vfx: int
    total: int
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON-RPC response.
        
        Returns:
            Dictionary with raw counts and formatted strings
        """
        return {
            'music': self.music,
            'sfx': self.sfx,
            'vfx': self.vfx,
            'total': self.total,
            'formatted': {
                'music': format_number(self.music),
                'sfx': format_number(self.sfx),
                'vfx': format_number(self.vfx),
                'total': format_number(self.total)
            },
            'last_updated': self.last_updated.isoformat()
        }
    
    def get_category_count(self, category: str) -> int:
        """Get count for a specific category.
        
        Args:
            category: Category name (music, sfx, vfx)
            
        Returns:
            Count for the category, or 0 if invalid category
        """
        category_map = {
            'music': self.music,
            'sfx': self.sfx,
            'vfx': self.vfx
        }
        return category_map.get(category, 0)


class AssetCounter:
    """Aggregates and caches asset counts by category.
    
    Provides efficient O(n) counting of assets with short-TTL caching
    to balance performance with real-time accuracy. Cache is automatically
    invalidated when asset changes are detected.
    
    Attributes:
        VALID_CATEGORIES: Set of valid asset category names (lowercase)
    """
    
    VALID_CATEGORIES = {'music', 'sfx', 'vfx'}
    
    def __init__(self, cache_ttl_seconds: float = 5.0):
        """Initialize the asset counter.
        
        Args:
            cache_ttl_seconds: Time-to-live for count cache in seconds
                              (default: 5.0 for real-time feel)
                              Must be non-negative; 0 disables caching
                              
        Raises:
            ValueError: If cache_ttl_seconds is negative
        """
        if cache_ttl_seconds < 0:
            raise ValueError(f"cache_ttl_seconds must be non-negative, got {cache_ttl_seconds}")
        
        # Minimum 1ms TTL to prevent immediate invalidation issues
        self._cache_ttl_seconds = max(0.001, cache_ttl_seconds)
        
        self._cache: Optional[AssetCounts] = None
        self._cache_time: Optional[datetime] = None
        
        # Thread lock for cache operations
        self._cache_lock = threading.RLock()
    
    def count_by_category(
        self, 
        assets: Dict[str, MediaAsset],
        use_cache: bool = True
    ) -> AssetCounts:
        """Count assets by category.
        
        Performs O(n) aggregation of assets by category with optional
        caching for performance. Cache is checked before aggregation
        if use_cache=True and cache is still fresh.
        
        Thread-safe: Uses internal lock for cache access.
        
        Args:
            assets: Dictionary mapping asset_id -> MediaAsset
            use_cache: Whether to use cached results if fresh
            
        Returns:
            AssetCounts with totals by category
            
        Example:
            >>> counter = AssetCounter()
            >>> counts = counter.count_by_category(indexer._assets)
            >>> print(f"Music: {counts.music:,}")
            Music: 12,437
        """
        # Check cache if enabled and still fresh (thread-safe)
        if use_cache:
            cached = self.get_cached_counts()
            if cached is not None:
                return cached
        
        # Aggregate counts by category (case-insensitive)
        counts = defaultdict(int)
        for asset in assets.values():
            if asset.category is None:
                continue  # Skip assets with no category
            
            # Case-insensitive category matching
            category_lower = asset.category.lower()
            if category_lower in self.VALID_CATEGORIES:
                counts[category_lower] += 1
        
        # Validate counts are non-negative (defensive)
        for category in self.VALID_CATEGORIES:
            if counts[category] < 0:
                counts[category] = 0
        
        # Create result
        result = AssetCounts(
            music=counts.get('music', 0),
            sfx=counts.get('sfx', 0),
            vfx=counts.get('vfx', 0),
            total=sum(counts.values()),
            last_updated=datetime.now(timezone.utc)
        )
        
        # Update cache (thread-safe)
        with self._cache_lock:
            self._cache = result
            self._cache_time = result.last_updated
        
        return result
    
    def _is_cache_valid(self) -> bool:
        """Check if cached counts are still fresh.
        
        Note: Must be called with _cache_lock held for thread safety.
        
        Returns:
            True if cache exists and hasn't expired, False otherwise
        """
        if self._cache is None or self._cache_time is None:
            return False
        
        # Use timezone-aware comparison
        now = datetime.now(timezone.utc)
        elapsed = (now - self._cache_time).total_seconds()
        return elapsed < self._cache_ttl_seconds
    
    def invalidate_cache(self):
        """Invalidate the count cache.
        
        Should be called when assets are added, removed, or modified
        to ensure counts reflect current state.
        
        Thread-safe: Uses internal lock.
        """
        with self._cache_lock:
            self._cache = None
            self._cache_time = None
    
    def get_cached_counts(self) -> Optional[AssetCounts]:
        """Get cached counts if available and valid.
        
        Thread-safe: Uses internal lock.
        
        Returns:
            Cached AssetCounts if cache is valid, None otherwise
        """
        with self._cache_lock:
            if self._is_cache_valid():
                return self._cache
        return None
    
    def is_cache_valid(self) -> bool:
        """Public check for cache validity.
        
        Thread-safe: Uses internal lock.
        
        Returns:
            True if cache is valid and can be used
        """
        with self._cache_lock:
            is_valid = self._is_cache_valid()
        return is_valid
    
    def get_cache_ttl(self) -> float:
        """Get the current cache TTL setting.
        
        Returns:
            Cache TTL in seconds
        """
        return self._cache_ttl_seconds
