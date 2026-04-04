"""File hash caching for efficient change detection.

Provides caching of file hashes to detect file modifications
without re-computing hashes for unchanged files.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class HashCache:
    """Caches file hashes for efficient change detection.
    
    The cache stores file paths mapped to their hash values and
    modification times. This allows quick detection of changed files
    by first checking mtime, then hash if needed.
    
    Attributes:
        _cache: Dictionary mapping file paths to (hash, mtime) tuples
        _cache_file: Optional path to persist cache to disk
        max_file_size: Maximum file size to hash (bytes), larger files are skipped
    """
    _cache: Dict[str, tuple[str, float]] = field(default_factory=dict)
    _cache_file: Optional[Path] = None
    max_file_size: int = 1024 * 1024 * 1024  # 1GB default limit
    
    def compute_hash(self, file_path: Path) -> str:
        """Compute MD5 hash of file content.
        
        Uses chunked reading for memory efficiency with large files.
        
        Args:
            file_path: Path to the file to hash
            
        Returns:
            Hex digest of MD5 hash
            
        Raises:
            FileTooLargeError: If file exceeds max_file_size limit
        """
        # Check file size limit
        file_size = file_path.stat().st_size
        if file_size > self.max_file_size:
            raise ValueError(
                f"File too large to hash: {file_path} ({file_size} bytes, "
                f"limit: {self.max_file_size} bytes)"
            )
        
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def get_file_hash(self, file_path: Path) -> str:
        """Get hash for a file, using cache if possible.
        
        Checks modification time first, then computes hash only if
        the file has been modified since last cache.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File hash (from cache or freshly computed)
        """
        path_str = str(file_path.resolve())
        
        try:
            stat = file_path.stat()
            current_mtime = stat.st_mtime
            
            # Check if we have a cached entry
            if path_str in self._cache:
                cached_hash, cached_mtime = self._cache[path_str]
                
                # If mtime hasn't changed, use cached hash
                if current_mtime == cached_mtime:
                    return cached_hash
            
            # Compute new hash
            file_hash = self.compute_hash(file_path)
            
            # Update cache
            self._cache[path_str] = (file_hash, current_mtime)
            
            return file_hash
            
        except (FileNotFoundError, OSError):
            # If file doesn't exist, remove from cache if present
            if path_str in self._cache:
                del self._cache[path_str]
            raise
    
    def has_changed(self, file_path: Path, cached_hash: str) -> bool:
        """Check if file has changed since last index.
        
        Compares the current file hash against a previously cached hash.
        
        Args:
            file_path: Path to the file
            cached_hash: Previously cached hash to compare against
            
        Returns:
            True if file hash differs from cached hash, False otherwise
        """
        try:
            current_hash = self.get_file_hash(file_path)
            return current_hash != cached_hash
        except (FileNotFoundError, OSError):
            # File no longer exists, treat as changed (deleted)
            return True
    
    def get_cached_hash(self, file_path: Path) -> Optional[str]:
        """Get the cached hash for a file if available.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Cached hash or None if not in cache
        """
        path_str = str(file_path.resolve())
        if path_str in self._cache:
            return self._cache[path_str][0]
        return None
    
    def invalidate(self, file_path: Path) -> None:
        """Remove a file from the cache.
        
        Args:
            file_path: Path to the file to remove from cache
        """
        path_str = str(file_path.resolve())
        if path_str in self._cache:
            del self._cache[path_str]
    
    def clear(self) -> None:
        """Clear all cached hashes."""
        self._cache.clear()
    
    def save_to_disk(self, cache_file: Optional[Path] = None) -> None:
        """Save cache to disk for persistence.
        
        Args:
            cache_file: Path to save cache to (uses _cache_file if not provided)
        """
        path = cache_file or self._cache_file
        if path is None:
            return
        
        # Convert to serializable format
        data = {
            'hashes': {
                path: {'hash': h, 'mtime': m}
                for path, (h, m) in self._cache.items()
            }
        }
        
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_disk(self, cache_file: Optional[Path] = None) -> None:
        """Load cache from disk.
        
        Args:
            cache_file: Path to load cache from (uses _cache_file if not provided)
        """
        path = cache_file or self._cache_file
        if path is None or not path.exists():
            return
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            # Restore cache from serialized format
            hashes = data.get('hashes', {})
            self._cache = {
                path: (info['hash'], info['mtime'])
                for path, info in hashes.items()
            }
        except (json.JSONDecodeError, KeyError):
            # If cache file is corrupted, start fresh
            self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about the cache.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'cached_entries': len(self._cache)
        }
