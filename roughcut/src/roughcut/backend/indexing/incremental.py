"""Incremental scanning for media file changes.

Detects new, modified, and deleted files by comparing current
filesystem state against cached index data.
"""

from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from ..database.models import MediaAsset, ScanResult
from .hash_cache import HashCache
from .scanner import FileScanner


@dataclass
class IncrementalScanner:
    """Detects changes between current filesystem and cached index.
    
    Compares the current state of configured folders against a
    previously stored index to identify:
    - New files: Present in filesystem but not in index
    - Modified files: Present in both but hash differs
    - Deleted files: Present in index but not in filesystem
    
    Attributes:
        hash_cache: Cache for file hash computation
        file_scanner: Scanner for discovering media files
    """
    
    hash_cache: HashCache
    file_scanner: FileScanner
    
    async def scan_for_changes(
        self,
        folder_configs: Dict[str, Optional[str]],
        cached_assets: List[MediaAsset]
    ) -> ScanResult:
        """Compare current folders against cached index.
        
        Args:
            folder_configs: Dictionary mapping category to folder path
            cached_assets: List of previously indexed assets
            
        Returns:
            ScanResult containing new, modified, and deleted files
        """
        # Build lookup of cached assets by path for O(1) access
        cached_by_path: Dict[str, MediaAsset] = {
            str(a.file_path.resolve()): a 
            for a in cached_assets
        }
        
        new_files: List[Path] = []
        modified_files: List[Path] = []
        current_paths: set[str] = set()
        total_scanned = 0
        
        # Scan all configured folders
        async for category, file_path in self.file_scanner.scan_multiple_folders(folder_configs):
            total_scanned += 1
            path_str = str(file_path.resolve())
            current_paths.add(path_str)
            
            if path_str not in cached_by_path:
                # New file not in cache
                new_files.append(file_path)
            else:
                # File exists in cache, check if modified
                cached_asset = cached_by_path[path_str]
                
                # Quick check: compare modification time
                try:
                    stat = file_path.stat()
                    current_mtime = stat.st_mtime
                    cached_mtime = cached_asset.modified_time.timestamp()
                    
                    if current_mtime != cached_mtime:
                        # Mtime changed, verify with hash
                        if self.hash_cache.has_changed(file_path, cached_asset.file_hash):
                            modified_files.append(file_path)
                except (FileNotFoundError, OSError):
                    # File was deleted during scan
                    pass
        
        # Find deleted files (in cache but not in current filesystem)
        deleted_files: List[str] = [
            a.id for a in cached_assets
            if str(a.file_path.resolve()) not in current_paths
        ]
        
        return ScanResult(
            new_files=new_files,
            modified_files=modified_files,
            deleted_files=deleted_files,
            total_scanned=total_scanned
        )
    
    def scan_for_changes_sync(
        self,
        folder_configs: Dict[str, Optional[str]],
        cached_assets: List[MediaAsset]
    ) -> ScanResult:
        """Synchronous version of scan_for_changes.
        
        For use when async context is not available.
        
        Args:
            folder_configs: Dictionary mapping category to folder path
            cached_assets: List of previously indexed assets
            
        Returns:
            ScanResult containing new, modified, and deleted files
        """
        # Build lookup of cached assets by path
        cached_by_path: Dict[str, MediaAsset] = {
            str(a.file_path.resolve()): a 
            for a in cached_assets
        }
        
        new_files: List[Path] = []
        modified_files: List[Path] = []
        current_paths: set[str] = set()
        total_scanned = 0
        
        # Scan each configured folder
        for category, folder_path_str in folder_configs.items():
            if not folder_path_str:
                continue
                
            folder_path = Path(folder_path_str)
            if not folder_path.exists() or not folder_path.is_dir():
                continue
            
            # Scan folder
            for file_path in self.file_scanner.scan_folder(folder_path):
                total_scanned += 1
                path_str = str(file_path.resolve())
                current_paths.add(path_str)
                
                if path_str not in cached_by_path:
                    new_files.append(file_path)
                else:
                    # Check if modified
                    cached_asset = cached_by_path[path_str]
                    
                    try:
                        stat = file_path.stat()
                        current_mtime = stat.st_mtime
                        cached_mtime = cached_asset.modified_time.timestamp()
                        
                        if current_mtime != cached_mtime:
                            if self.hash_cache.has_changed(file_path, cached_asset.file_hash):
                                modified_files.append(file_path)
                    except (FileNotFoundError, OSError):
                        pass
        
        # Find deleted files
        deleted_files: List[str] = [
            a.id for a in cached_assets
            if str(a.file_path.resolve()) not in current_paths
        ]
        
        return ScanResult(
            new_files=new_files,
            modified_files=modified_files,
            deleted_files=deleted_files,
            total_scanned=total_scanned
        )
    
    def get_asset_category(
        self,
        file_path: Path,
        folder_configs: Dict[str, Optional[str]]
    ) -> Optional[str]:
        """Determine the category of a file based on its folder.
        
        Args:
            file_path: Path to the file
            folder_configs: Dictionary mapping category to folder path
            
        Returns:
            Category string or None if cannot determine
        """
        file_path_resolved = file_path.resolve()
        
        for category, folder_path_str in folder_configs.items():
            if not folder_path_str:
                continue
                
            folder_path = Path(folder_path_str).resolve()
            
            try:
                # Check if file is within this folder
                file_path_resolved.relative_to(folder_path)
                return category
            except ValueError:
                # Not in this folder
                continue
        
        return None
