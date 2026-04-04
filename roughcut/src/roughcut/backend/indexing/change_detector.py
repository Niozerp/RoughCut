"""File change detection for re-indexing operations.

Provides change detection algorithms to identify new, modified,
moved, and deleted files during full re-indexing scans.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from ..database.models import MediaAsset


@dataclass
class FileMetadata:
    """Metadata for a scanned file.
    
    Used during change detection to compare with database records.
    
    Attributes:
        file_hash: SHA256 hash of file content
        modified_time: Last modification timestamp
        file_size: File size in bytes
        category: Asset category (music, sfx, vfx)
    """
    file_hash: str
    modified_time: datetime
    file_size: int
    category: str


@dataclass
class FileChangeSet:
    """Container for detected file system changes.
    
    Organizes changes into categories for processing during
    re-indexing operations.
    
    Attributes:
        new_files: List of file paths not in database
        modified_files: List of file paths with changed content
        moved_files: List of (old_path, new_path) tuples for moved files
        deleted_files: List of asset IDs for orphaned database entries
        total_scanned: Total number of files scanned
    """
    new_files: List[Path]
    modified_files: List[Path]
    moved_files: List[Tuple[Path, Path]]
    deleted_files: List[str]
    total_scanned: int = 0


class ChangeDetector:
    """Detects changes between filesystem and database state.
    
    Uses file hash and modified time for change detection.
    Handles moves by matching hash when path changes.
    
    Detection Logic:
        1. New files: Path exists in scan but not in DB
        2. Modified: Path in both, but hash or mtime differs
        3. Moved: Hash matches, but path differs (old path in DB, new in scan)
        4. Deleted: Path in DB but not in scan (orphaned)
    """
    
    def detect_changes(
        self,
        scanned_files: Dict[Path, FileMetadata],
        db_assets: List[MediaAsset]
    ) -> FileChangeSet:
        """Compare scanned filesystem state against database records.
        
        Args:
            scanned_files: Dict mapping file paths to metadata (from full scan)
            db_assets: List of existing MediaAsset records from SpacetimeDB
            
        Returns:
            FileChangeSet with categorized changes
        """
        # Build lookup indexes for efficient comparison
        # Note: For duplicate hashes in DB, we only track the first occurrence.
        # This is intentional - if multiple assets share a hash, only one can be
        # "moved" to the new location; others will be marked as orphaned.
        db_by_path: Dict[str, MediaAsset] = {}
        db_by_hash: Dict[str, MediaAsset] = {}
        
        for asset in db_assets:
            db_by_path[asset.file_path] = asset
            # Handle potential duplicate hashes (rare but possible)
            # We only store the first asset with a given hash to avoid
            # ambiguity in move detection. Duplicate-hash assets that aren't
            # the first will be handled as orphaned if their paths don't match.
            if asset.file_hash not in db_by_hash:
                db_by_hash[asset.file_hash] = asset
        
        new_files: List[Path] = []
        modified_files: List[Path] = []
        moved_files: List[Tuple[Path, Path]] = []
        deleted_asset_ids: List[str] = []
        
        # Track processed hashes to handle moves correctly
        processed_hashes: set = set()
        
        for path, metadata in scanned_files.items():
            path_str = str(path)
            
            if path_str in db_by_path:
                # Path exists - check for modification
                db_asset = db_by_path[path_str]
                if (metadata.file_hash != db_asset.file_hash or
                    metadata.modified_time > db_asset.modified_time):
                    modified_files.append(path)
            else:
                # New path - check if it's a move (hash match)
                if (metadata.file_hash in db_by_hash and
                    metadata.file_hash not in processed_hashes):
                    old_asset = db_by_hash[metadata.file_hash]
                    # Only treat as move if old path is different and exists in DB
                    if old_asset.file_path != path_str:
                        moved_files.append((Path(old_asset.file_path), path))
                        processed_hashes.add(metadata.file_hash)
                    else:
                        # Same hash, same path - no change
                        pass
                else:
                    # Truly new file
                    new_files.append(path)
        
        # Find orphaned entries (in DB but not on disk)
        scanned_paths = {str(p) for p in scanned_files.keys()}
        for db_asset in db_assets:
            if db_asset.file_path not in scanned_paths:
                # Check if this asset was "moved" - if hash is in scanned files
                # under a different path, it's a move (already handled above)
                if db_asset.file_hash not in processed_hashes:
                    deleted_asset_ids.append(db_asset.id)
        
        return FileChangeSet(
            new_files=new_files,
            modified_files=modified_files,
            moved_files=moved_files,
            deleted_files=deleted_asset_ids,
            total_scanned=len(scanned_files)
        )
    
    def detect_changes_simple(
        self,
        scanned_paths: set,
        db_assets: List[MediaAsset]
    ) -> Tuple[List[str], List[Path]]:
        """Simplified change detection for basic orphan detection.
        
        Args:
            scanned_paths: Set of absolute file paths from scan
            db_assets: List of existing MediaAsset records
            
        Returns:
            Tuple of (orphaned_asset_ids, new_paths)
        """
        db_paths = {asset.file_path for asset in db_assets}
        
        # Orphaned: in DB but not on disk
        orphaned = [
            asset.id for asset in db_assets
            if asset.file_path not in scanned_paths
        ]
        
        # New: on disk but not in DB
        new_paths = [
            Path(p) for p in scanned_paths
            if p not in db_paths
        ]
        
        return orphaned, new_paths
