"""Media indexing module.

Provides components for incremental media indexing including:
- File scanning and discovery
- Hash-based change detection
- Progress reporting
- Database integration
- Full re-indexing with change detection
"""

from .hash_cache import HashCache
from .scanner import FileScanner, MEDIA_EXTENSIONS
from .incremental import IncrementalScanner
from .indexer import MediaIndexer, ProgressCallback
from .change_detector import ChangeDetector, FileMetadata, FileChangeSet

__all__ = [
    'HashCache',
    'FileScanner',
    'MEDIA_EXTENSIONS',
    'IncrementalScanner',
    'MediaIndexer',
    'ProgressCallback',
    'ChangeDetector',
    'FileMetadata',
    'FileChangeSet',
]
