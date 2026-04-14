"""File hash caching for efficient change detection.

Provides caching of file hashes to detect file modifications
without re-computing hashes for unchanged files.
"""

import hashlib
import json
from collections import OrderedDict
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class HashCache:
    """Caches file hashes for efficient change detection.
    
    The cache stores file paths mapped to their hash values and
    modification times. This allows quick detection of changed files
    by first checking mtime, then hash if needed.
    
    Uses LRU eviction to prevent unbounded memory growth when indexing
    large media libraries.
    
    Attributes:
        _cache: OrderedDict mapping file paths to (hash, mtime) tuples (LRU order)
        _cache_file: Optional path to persist cache to disk
        max_file_size: Maximum file size to hash (bytes), larger files are skipped
        max_cache_entries: Maximum number of entries to keep in cache (LRU eviction)
    """
    _cache: OrderedDict = field(default_factory=OrderedDict)
    _cache_file: Optional[Path] = None
    max_file_size: int = 1024 * 1024 * 1024  # 1GB default limit
    max_cache_entries: int = 50000  # LRU limit: evict oldest when exceeded
    
    def compute_hash(self, file_path: Path, category: str = "unknown") -> str:
        """Compute MD5 hash of file content.
        
        Uses chunked reading for memory efficiency with large files.
        Includes defensive error handling for corrupted or locked files.
        
        Args:
            file_path: Path to the file to hash
            category: Category name (music, sfx, vfx) for verbose logging
            
        Returns:
            Hex digest of MD5 hash
            
        Raises:
            FileTooLargeError: If file exceeds max_file_size limit
        """
        import logging
        _hash_logger = logging.getLogger(__name__)
        category_upper = category.upper()
        
        # VERBOSE: Show start of hashing with category
        _hash_logger.info(f"[INDEXING_LOG] [VERBOSE] [{category_upper}] Hash START: {file_path}")
        
        try:
            # Check file exists and is accessible
            if not file_path.exists():
                _hash_logger.error(f"[INDEXING_LOG] Hash: File does not exist: {file_path}")
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if not file_path.is_file():
                _hash_logger.error(f"[INDEXING_LOG] Hash: Path is not a file: {file_path}")
                raise ValueError(f"Path is not a file: {file_path}")
            
            # Check file size limit
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                _hash_logger.warning(f"[INDEXING_LOG] File too large to hash: {file_path} ({file_size} bytes)")
                raise ValueError(
                    f"File too large to hash: {file_path} ({file_size} bytes, "
                    f"limit: {self.max_file_size} bytes)"
                )
            
            _hash_logger.info(f"[INDEXING_LOG] Hashing file: {file_path} ({file_size} bytes)")
            hash_md5 = hashlib.md5()
            bytes_read = 0
            chunk_count = 0
            
            # Open file with explicit error handling
            try:
                f = open(file_path, "rb")
                _hash_logger.info(f"[INDEXING_LOG] Hash: File opened successfully: {file_path.name}")
            except (OSError, IOError, PermissionError) as open_err:
                _hash_logger.error(f"[INDEXING_LOG] Hash: Failed to open file {file_path}: {open_err}")
                # VERBOSE: Show open failure with category
                _hash_logger.info(f"[INDEXING_LOG] [VERBOSE] [{category_upper}] Hash OPEN FAILED: {file_path} - {open_err}")
                raise
            
            try:
                while True:
                    try:
                        chunk = f.read(4096)
                        chunk_count += 1
                    except (OSError, IOError, PermissionError) as read_err:
                        _hash_logger.error(f"[INDEXING_LOG] Hash: Read error at chunk {chunk_count} for {file_path}: {read_err}")
                        # VERBOSE: Show read failure with category
                        _hash_logger.info(f"[INDEXING_LOG] [VERBOSE] [{category_upper}] Hash READ FAILED: {file_path} at chunk {chunk_count} - {read_err}")
                        raise
                    
                    if not chunk:
                        break
                    
                    try:
                        hash_md5.update(chunk)
                        bytes_read += len(chunk)
                    except Exception as update_err:
                        _hash_logger.error(f"[INDEXING_LOG] Hash: MD5 update error for {file_path}: {update_err}")
                        raise
                    
                    # Log progress for very large files (>100MB) every 10MB
                    if file_size > 100 * 1024 * 1024 and bytes_read % (10 * 1024 * 1024) == 0:
                        _hash_logger.info(f"[INDEXING_LOG] Hashing progress: {bytes_read}/{file_size} bytes ({chunk_count} chunks)")
            finally:
                try:
                    f.close()
                    _hash_logger.info(f"[INDEXING_LOG] Hash: File closed: {file_path.name}")
                except Exception as close_err:
                    _hash_logger.warning(f"[INDEXING_LOG] Hash: Error closing file {file_path}: {close_err}")
            
            # VERBOSE: Show completion with category
            _hash_logger.info(f"[INDEXING_LOG] [VERBOSE] [{category_upper}] Hash COMPLETE: {file_path} ({chunk_count} chunks, {bytes_read} bytes)")
            _hash_logger.info(f"[INDEXING_LOG] Hash complete: {file_path} ({chunk_count} chunks, {bytes_read} bytes)")
            return hash_md5.hexdigest()
            
        except (OSError, IOError, PermissionError) as e:
            _hash_logger.error(f"[INDEXING_LOG] Hash failed for {file_path}: {e}")
            raise
        except Exception as e:
            _hash_logger.error(f"[INDEXING_LOG] Hash unexpected error for {file_path}: {e}")
            import traceback
            _hash_logger.error(f"[INDEXING_LOG] Hash traceback: {traceback.format_exc()}")
            raise
    
    def get_file_hash(self, file_path: Path, category: str = "unknown") -> str:
        """Get hash for a file, using cache if possible.
        
        Checks modification time first, then computes hash only if
        the file has been modified since last cache.
        
        Uses LRU eviction to keep cache bounded.
        
        Args:
            file_path: Path to the file
            category: Category name (music, sfx, vfx) for verbose logging
            
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
                    # Mark as recently used (LRU)
                    self._cache.move_to_end(path_str)
                    return cached_hash
            
            # Compute new hash (pass category for verbose logging)
            file_hash = self.compute_hash(file_path, category)
            
            # Update cache and mark as recently used
            self._cache[path_str] = (file_hash, current_mtime)
            self._cache.move_to_end(path_str)
            
            # Evict oldest entries if over limit
            self._evict_if_needed()
            
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
    
    def _evict_if_needed(self) -> None:
        """Evict oldest entries if cache exceeds max_cache_entries.
        
        Uses LRU eviction - removes oldest accessed entries first.
        """
        while len(self._cache) > self.max_cache_entries:
            # Pop the oldest item (first item in OrderedDict)
            self._cache.popitem(last=False)
    
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
            
            # Restore cache from serialized format as OrderedDict
            hashes = data.get('hashes', {})
            self._cache = OrderedDict(
                (path, (info['hash'], info['mtime']))
                for path, info in hashes.items()
            )
            # Enforce limit after loading
            self._evict_if_needed()
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
