"""File system scanner for media indexing.

Provides asynchronous scanning of media folders to discover
media files with support for different categories and file types.
"""

import asyncio
from pathlib import Path
from typing import List, Set, Optional, AsyncIterator
import aiofiles


# Supported media file extensions by category
MEDIA_EXTENSIONS = {
    'music': {'.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma'},
    'sfx': {'.wav', '.mp3', '.ogg', '.flac', '.aiff', '.m4a'},
    'vfx': {'.mov', '.mp4', '.avi', '.mkv', '.webm', '.prores', '.dnxhd'}
}

# All supported extensions
ALL_EXTENSIONS = set().union(*MEDIA_EXTENSIONS.values())


class FileScanner:
    """Scans file system for media files.
    
    Provides both synchronous and asynchronous scanning of folders
    to discover media files. Supports filtering by category and
    handles various media file formats.
    
    Attributes:
        extensions: Set of file extensions to include in scan
    """
    
    def __init__(self, categories: Optional[List[str]] = None):
        """Initialize scanner with optional category filter.
        
        Args:
            categories: List of categories to scan (music, sfx, vfx).
                       If None, scans all categories.
        """
        if categories:
            self.extensions = set()
            for cat in categories:
                cat_lower = cat.lower()
                if cat_lower in MEDIA_EXTENSIONS:
                    self.extensions.update(MEDIA_EXTENSIONS[cat_lower])
        else:
            self.extensions = ALL_EXTENSIONS.copy()
    
    def scan_folder(self, folder_path: Path) -> List[Path]:
        """Synchronously scan a folder for media files.
        
        Args:
            folder_path: Path to the folder to scan
            
        Returns:
            List of paths to media files found
        """
        results = []
        
        if not folder_path.exists() or not folder_path.is_dir():
            return results
        
        try:
            for item in folder_path.rglob('*'):
                if item.is_file() and item.suffix.lower() in self.extensions:
                    results.append(item)
        except (PermissionError, OSError):
            # Skip folders we can't access
            pass
        
        return results
    
    async def scan_folder_async(self, folder_path: Path) -> AsyncIterator[Path]:
        """Asynchronously scan a folder for media files.
        
        Yields media files as they are discovered for streaming processing.
        
        Args:
            folder_path: Path to the folder to scan
            
        Yields:
            Paths to media files found
        """
        if not folder_path.exists() or not folder_path.is_dir():
            return
        
        try:
            # Use asyncio to run the sync walk in a thread pool
            loop = asyncio.get_event_loop()
            files = await loop.run_in_executor(
                None, self._walk_folder, folder_path
            )
            
            for file_path in files:
                yield file_path
                
        except (PermissionError, OSError):
            # Skip folders we can't access
            pass
    
    def _walk_folder(self, folder_path: Path) -> List[Path]:
        """Internal method to walk folder (runs in thread pool).
        
        Args:
            folder_path: Path to the folder to walk
            
        Returns:
            List of paths to media files
        """
        results = []
        
        try:
            for item in folder_path.rglob('*'):
                if item.is_file() and item.suffix.lower() in self.extensions:
                    results.append(item)
        except (PermissionError, OSError):
            pass
        
        return results
    
    async def scan_multiple_folders(
        self,
        folder_configs: dict[str, Optional[str]]
    ) -> AsyncIterator[tuple[str, Path]]:
        """Scan multiple folders concurrently.
        
        Args:
            folder_configs: Dictionary mapping category to folder path
            
        Yields:
            Tuples of (category, file_path) for each media file found
        """
        tasks = []
        
        for category, folder_path_str in folder_configs.items():
            if not folder_path_str:
                continue
                
            folder_path = Path(folder_path_str)
            if folder_path.exists() and folder_path.is_dir():
                task = self._scan_category_folder(category, folder_path)
                tasks.append(task)
        
        # Use asyncio.gather to run scans concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    # Log error but continue with other results
                    continue
                    
                for category, file_path in result:
                    yield category, file_path
    
    async def _scan_category_folder(
        self,
        category: str,
        folder_path: Path
    ) -> List[tuple[str, Path]]:
        """Scan a single category folder.
        
        Args:
            category: Category name
            folder_path: Path to the folder
            
        Returns:
            List of (category, file_path) tuples
        """
        results = []
        
        async for file_path in self.scan_folder_async(folder_path):
            results.append((category, file_path))
        
        return results
    
    def count_files(self, folder_path: Path) -> int:
        """Count media files in a folder without returning them.
        
        More efficient than scan_folder when only count is needed.
        
        Args:
            folder_path: Path to the folder to count
            
        Returns:
            Number of media files found
        """
        count = 0
        
        if not folder_path.exists() or not folder_path.is_dir():
            return count
        
        try:
            for item in folder_path.rglob('*'):
                if item.is_file() and item.suffix.lower() in self.extensions:
                    count += 1
        except (PermissionError, OSError):
            pass
        
        return count
    
    def get_supported_extensions(self) -> Set[str]:
        """Get the set of supported file extensions.
        
        Returns:
            Set of supported file extensions (e.g., {'.mp3', '.wav'})
        """
        return self.extensions.copy()


def get_category_for_extension(extension: str) -> Optional[str]:
    """Determine media category based on file extension.
    
    Args:
        extension: File extension including dot (e.g., '.mp3')
        
    Returns:
        Category string (music, sfx, vfx) or None if not supported
    """
    ext_lower = extension.lower()
    
    for category, extensions in MEDIA_EXTENSIONS.items():
        if ext_lower in extensions:
            return category
    
    return None
