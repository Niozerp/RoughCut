"""Template caching system with file modification tracking."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .models import FormatTemplate


@dataclass
class CachedTemplate:
    """Template with cache metadata."""
    template: FormatTemplate
    file_mtime: float
    cached_at: datetime
    source_path: Path


class TemplateCache:
    """
    Caches parsed templates with file modification tracking.
    
    This cache enables hot-reload functionality by tracking file
    modification times and detecting when templates need re-parsing.
    
    Thread-safe implementation using RLock for concurrent access.
    
    Example:
        >>> cache = TemplateCache()
        >>> cache.store(template, mtime=1234567890.0, path=template_path)
        >>> cached = cache.get("youtube-interview")
        >>> if cache.is_stale("youtube-interview", new_mtime):
        ...     # Re-parse needed
    """
    
    def __init__(self):
        """Initialize empty cache with thread lock."""
        self._cache: Dict[str, CachedTemplate] = {}
        self._lock = threading.RLock()
    
    def get(self, slug: str) -> Optional[FormatTemplate]:
        """
        Retrieve template from cache by slug.
        
        Args:
            slug: Template slug identifier
            
        Returns:
            FormatTemplate if found in cache, None otherwise
        """
        with self._lock:
            cached = self._cache.get(slug)
            return cached.template if cached else None
    
    def get_all(self) -> List[FormatTemplate]:
        """
        Retrieve all cached templates.
        
        Returns:
            List of all cached FormatTemplate instances
        """
        with self._lock:
            return [ct.template for ct in self._cache.values()]
    
    def get_slugs(self) -> List[str]:
        """
        Get list of all cached template slugs.
        
        Returns:
            List of template slugs in cache
        """
        with self._lock:
            return list(self._cache.keys())
    
    def store(
        self, 
        template: FormatTemplate, 
        file_mtime: float, 
        source_path: Path
    ) -> None:
        """
        Store template in cache with metadata.
        
        Args:
            template: FormatTemplate to cache
            file_mtime: File modification timestamp
            source_path: Path to source file
        """
        with self._lock:
            self._cache[template.slug] = CachedTemplate(
                template=template,
                file_mtime=file_mtime,
                cached_at=datetime.now(),
                source_path=source_path
            )
    
    def is_stale(self, slug: str, current_mtime: float) -> bool:
        """
        Check if cached template is stale based on file modification time.
        
        Uses epsilon comparison to handle floating-point precision differences
        between file systems.
        
        Args:
            slug: Template slug to check
            current_mtime: Current file modification time
            
        Returns:
            True if cache entry is stale or doesn't exist, False if fresh
        """
        with self._lock:
            cached = self._cache.get(slug)
            if not cached:
                return True
            # Use epsilon comparison for floating-point mtime precision
            return abs(cached.file_mtime - current_mtime) > 0.001
    
    def reload_templates(
        self,
        discovery,
        parser,
        validator
    ) -> Dict[str, Any]:
        """
        Reload all templates from disk, updating cache as needed.
        
        This method implements the hot-reload capability, checking each
        template file for changes and updating the cache accordingly.
        
        Args:
            discovery: TemplateDiscovery instance
            parser: TemplateParser instance
            validator: TemplateValidator instance
            
        Returns:
            Dictionary with reload statistics:
            - total_templates: Total templates found
            - new_templates: Newly added templates
            - updated_templates: Templates that were stale and reloaded
            - invalid_templates: Templates that failed validation
            - errors: List of error messages
        """
        import logging
        logger = logging.getLogger(__name__)
        
        stats = {
            'total_templates': 0,
            'new_templates': 0,
            'updated_templates': 0,
            'invalid_templates': 0,
            'errors': []
        }
        
        try:
            # Scan for all template files
            discovered = discovery.scan()
            current_slugs = set()
            
            for disc in discovered:
                stats['total_templates'] += 1
                
                # Generate slug using namespacing
                slug = discovery.get_slug_from_path(disc.file_path)
                current_slugs.add(slug)
                
                # Check if template needs reloading
                if not self.is_stale(slug, disc.modified_time):
                    continue  # Template is fresh, skip
                
                try:
                    # Validate file before parsing
                    is_valid, errors = validator.validate_template_file(disc.file_path)
                    if not is_valid:
                        stats['invalid_templates'] += 1
                        stats['errors'].append({
                            'file': disc.filename,
                            'error': '; '.join(errors)
                        })
                        self.remove(slug)
                        continue
                    
                    # Parse the template
                    template = parser.parse_file(disc.file_path)
                    if template is None:
                        stats['invalid_templates'] += 1
                        stats['errors'].append({
                            'file': disc.filename,
                            'error': 'Failed to parse template'
                        })
                        self.remove(slug)
                        continue
                    
                    # Update slug to use namespacing
                    template.slug = slug
                    
                    # Validate the parsed template
                    is_valid, validation_errors = validator.validate_template(template)
                    if not is_valid:
                        stats['invalid_templates'] += 1
                        stats['errors'].append({
                            'file': disc.filename,
                            'error': '; '.join(validation_errors)
                        })
                        self.remove(slug)
                        continue
                    
                    # Store in cache
                    was_cached = self.get(slug) is not None
                    self.store(template, disc.modified_time, disc.file_path)
                    
                    if was_cached:
                        stats['updated_templates'] += 1
                        logger.info(f"Updated template: {slug}")
                    else:
                        stats['new_templates'] += 1
                        logger.info(f"Added new template: {slug}")
                        
                except Exception as e:
                    stats['invalid_templates'] += 1
                    stats['errors'].append({
                        'file': disc.filename,
                        'error': str(e)
                    })
                    self.remove(slug)
                    logger.error(f"Error processing {disc.filename}: {e}")
            
            # Remove deleted templates from cache
            cached_slugs = set(self.get_slugs())
            for deleted_slug in cached_slugs - current_slugs:
                self.remove(deleted_slug)
                logger.info(f"Removed deleted template: {deleted_slug}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to reload templates: {e}")
            stats['errors'].append({'file': 'N/A', 'error': f"Reload failed: {e}"})
            return stats
    
    def clear(self) -> None:
        """Clear all cached templates."""
        with self._lock:
            self._cache.clear()
    
    def remove(self, slug: str) -> bool:
        """
        Remove specific template from cache.
        
        Args:
            slug: Template slug to remove
            
        Returns:
            True if template was removed, False if not found
        """
        with self._lock:
            if slug in self._cache:
                del self._cache[slug]
                return True
            return False
    
    def get_metadata(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Get cache metadata for a template.
        
        Args:
            slug: Template slug
            
        Returns:
            Dictionary with cache metadata or None if not found
        """
        with self._lock:
            cached = self._cache.get(slug)
            if not cached:
                return None
            return {
                'file_mtime': cached.file_mtime,
                'cached_at': cached.cached_at.isoformat(),
                'source_path': str(cached.source_path)
            }
    
    def size(self) -> int:
        """
        Get number of templates in cache.
        
        Returns:
            Count of cached templates
        """
        with self._lock:
            return len(self._cache)
    
    def is_empty(self) -> bool:
        """
        Check if cache is empty.
        
        Returns:
            True if cache has no templates, False otherwise
        """
        with self._lock:
            return len(self._cache) == 0


# Global cache instance for singleton pattern
_global_cache: Optional[TemplateCache] = None
_cache_lock = threading.Lock()


def get_template_cache() -> TemplateCache:
    """
    Get global template cache instance.
    
    Returns:
        TemplateCache instance (creates if doesn't exist)
    """
    global _global_cache
    
    if _global_cache is None:
        with _cache_lock:
            # Double-checked locking
            if _global_cache is None:
                _global_cache = TemplateCache()
    
    return _global_cache


def reset_template_cache() -> None:
    """
    Reset global template cache.
    
    Clears the cache and resets the singleton instance.
    Useful for testing or when complete reload is needed.
    """
    global _global_cache
    
    with _cache_lock:
        if _global_cache is not None:
            _global_cache.clear()
        _global_cache = None
