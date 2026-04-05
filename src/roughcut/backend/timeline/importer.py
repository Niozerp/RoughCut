"""Media importer for importing suggested media to Resolve's Media Pool."""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)

# Supported audio formats for music and SFX
SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".aiff", ".aif", ".m4a"}

# Supported VFX template formats
SUPPORTED_VFX_FORMATS = {".comp", ".settings", ".drfx"}

# All supported formats
SUPPORTED_FORMATS = SUPPORTED_AUDIO_FORMATS | SUPPORTED_VFX_FORMATS


@dataclass
class MediaPoolReference:
    """Reference to a media item in Resolve's Media Pool."""

    file_path: str
    media_pool_id: str
    media_type: str  # "music", "sfx", "vfx"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_path": self.file_path,
            "media_pool_id": self.media_pool_id,
            "media_type": self.media_type,
        }


@dataclass
class SkippedFile:
    """Information about a file that was skipped during import."""

    file_path: str
    reason: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_path": self.file_path,
            "reason": self.reason,
            "message": self.message,
        }


@dataclass
class ImportResult:
    """Result of a media import operation."""

    imported_count: int = 0
    skipped_count: int = 0
    media_pool_refs: List[MediaPoolReference] = field(default_factory=list)
    skipped_files: List[SkippedFile] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "imported_count": self.imported_count,
            "skipped_count": self.skipped_count,
            "media_pool_refs": [ref.to_dict() for ref in self.media_pool_refs],
            "skipped_files": [sf.to_dict() for sf in self.skipped_files],
        }


class ResolveMediaPool(Protocol):
    """Protocol for Resolve Media Pool interface."""

    def find_media(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Find media in the pool by file path."""
        ...

    def import_media(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Import media file to the pool."""
        ...


class MediaImporter:
    """Handles importing suggested media to Resolve's Media Pool.
    
    This class provides functionality to:
    - Validate file paths and accessibility (NFR10)
    - Import media to Resolve's Media Pool
    - Detect and avoid duplicate imports
    - Report progress during import operations (NFR4)
    - Handle missing files gracefully (NFR9, NFR13)
    """

    def __init__(self, media_pool: Optional[ResolveMediaPool] = None):
        """Initialize the MediaImporter.
        
        Args:
            media_pool: Optional Resolve Media Pool interface for testing.
                       If None, will attempt to use actual Resolve API.
        """
        self._media_pool = media_pool
        self._progress_callback: Optional[Callable[[str, int, int], None]] = None

    def set_progress_callback(
        self, callback: Optional[Callable[[str, int, int], None]]
    ) -> None:
        """Set a callback for progress updates.
        
        Args:
            callback: Function called with (message, current, total) during import.
        """
        self._progress_callback = callback

    def _notify_progress(self, message: str, current: int, total: int) -> None:
        """Notify progress via callback if set."""
        if self._progress_callback:
            try:
                self._progress_callback(message, current, total)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    def _generate_stable_id(self, file_path: str, prefix: str = "id") -> str:
        """Generate a stable ID for a file path using hashlib.
        
        Unlike Python's hash(), this is deterministic across process restarts.
        """
        hash_value = hashlib.md5(file_path.encode('utf-8')).hexdigest()[:12]
        return f"{prefix}_{hash_value}"

    def resolve_file_paths(self, suggested_media: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve and normalize file paths from suggested media list.
        
        Converts relative paths to absolute paths where possible.
        
        Args:
            suggested_media: List of media items with 'file_path' keys.
            
        Returns:
            List of media items with normalized absolute paths.
        """
        resolved = []
        for media in suggested_media:
            file_path = media.get("file_path", "")
            if file_path:
                # Normalize to absolute path
                path = Path(file_path).resolve()
                media_copy = media.copy()
                media_copy["file_path"] = str(path)
                resolved.append(media_copy)
            else:
                logger.warning(f"Media item missing file_path: {media}")
                resolved.append(media)
        return resolved

    def validate_file_accessibility(self, file_path: str) -> tuple[bool, Optional[str]]:
        """Validate that a file exists and is accessible.
        
        Performs comprehensive validation per NFR10:
        - File must exist at specified path
        - File must be readable (permission check)
        - File extension must be supported
        - File size must be reasonable (>0 bytes)
        
        Uses defensive try/except to handle TOCTOU race conditions (P4 fix).
        
        Args:
            file_path: Absolute path to the file to validate.
            
        Returns:
            Tuple of (is_valid, error_message).
            error_message is None if valid, otherwise contains reason.
        """
        path = Path(file_path)
        
        # Check file extension first (static check, no race condition)
        ext = path.suffix.lower()
        if ext not in SUPPORTED_FORMATS:
            return False, f"Unsupported file format: {ext}. Supported: {', '.join(SUPPORTED_FORMATS)}"
        
        # Use try/except around actual file operations to handle race conditions
        # File could be deleted, changed to directory, or permissions changed between checks
        try:
            # Check existence and file type together
            if not path.exists():
                return False, f"File not found at specified path"
            
            if not path.is_file():
                return False, f"Path is not a file (may be a directory or special file)"
            
            # Check file is readable
            if not os.access(str(path), os.R_OK):
                return False, f"File exists but is not readable (permission denied)"
            
            # Check file size
            size = path.stat().st_size
            if size == 0:
                return False, f"File is empty (0 bytes)"
            # Max 10GB sanity check
            if size > 10 * 1024 * 1024 * 1024:
                return False, f"File exceeds maximum size (10GB)"
                
        except FileNotFoundError:
            return False, f"File disappeared during validation (race condition)"
        except PermissionError:
            return False, f"Permission denied accessing file"
        except OSError as e:
            return False, f"Cannot access file: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
        
        return True, None

    def validate_media_batch(
        self, suggested_media: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[SkippedFile]]:
        """Validate a batch of media files before import.
        
        Separates valid files from invalid ones, collecting skip reasons.
        
        Args:
            suggested_media: List of media items to validate.
            
        Returns:
            Tuple of (valid_files, skipped_files).
        """
        valid_files = []
        skipped_files = []
        
        for media in suggested_media:
            file_path = media.get("file_path", "")
            
            if not file_path:
                skipped_files.append(
                    SkippedFile(
                        file_path="",
                        reason="missing_path",
                        message="Media item missing file path",
                    )
                )
                continue
            
            is_valid, error_msg = self.validate_file_accessibility(file_path)
            
            if is_valid:
                valid_files.append(media)
            else:
                filename = Path(file_path).name if file_path else "unknown"
                skipped_files.append(
                    SkippedFile(
                        file_path=file_path,
                        reason="validation_failed",
                        message=f"Warning: {filename} not found at {file_path} - will be skipped",
                    )
                )
                logger.warning(f"Skipping file {file_path}: {error_msg}")
        
        return valid_files, skipped_files

    def _find_media_in_pool(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Check if media already exists in the Media Pool.
        
        Args:
            file_path: Absolute path to check.
            
        Returns:
            Media pool reference if found, None otherwise.
        """
        if self._media_pool:
            return self._media_pool.find_media(file_path)
        
        # Real Resolve API integration would go here
        # For now, return None to indicate "not found, needs import"
        # This would use DaVinci Resolve's Python API
        try:
            import DaVinciResolveScript as dvr
            resolve = dvr.scriptapp("Resolve")
            if resolve:
                project_manager = resolve.GetProjectManager()
                current_project = project_manager.GetCurrentProject()
                if current_project:
                    media_pool = current_project.GetMediaPool()
                    # Search for media by path
                    # Note: Actual Resolve API may differ
                    return None  # Placeholder
        except ImportError:
            logger.debug("DaVinciResolveScript not available")
        except Exception as e:
            logger.warning(f"Error checking Media Pool: {e}")
        
        return None

    def _import_media_to_pool(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Import a media file to Resolve's Media Pool.
        
        Args:
            file_path: Absolute path to the media file.
            
        Returns:
            Media pool reference if successful, None otherwise.
        """
        if self._media_pool:
            return self._media_pool.import_media(file_path)
        
        # Real Resolve API integration would go here
        try:
            import DaVinciResolveScript as dvr
            resolve = dvr.scriptapp("Resolve")
            if resolve:
                project_manager = resolve.GetProjectManager()
                current_project = project_manager.GetCurrentProject()
                if current_project:
                    media_pool = current_project.GetMediaPool()
                    # Import media file
                    # Note: Actual Resolve API may differ
                    # D2 FIX: Return None when Resolve unavailable (no fake success)
                    logger.error(f"Resolve API unavailable - cannot import: {file_path}")
                    return None
        except ImportError:
            logger.debug("DaVinciResolveScript not available")
        except Exception as e:
            logger.error(f"Error importing to Media Pool: {e}")
        
        return None

    def import_to_media_pool(
        self, media_items: List[Dict[str, Any]]
    ) -> ImportResult:
        """Import media files to Resolve's Media Pool.
        
        Handles duplicate detection and provides progress updates.
        
        Args:
            media_items: List of validated media items to import.
            
        Returns:
            ImportResult with success/failure details for each file.
        """
        result = ImportResult()
        total = len(media_items)
        
        for i, media in enumerate(media_items, 1):
            file_path = media.get("file_path", "")
            media_type = media.get("media_type", "unknown")
            filename = Path(file_path).name if file_path else "unknown"
            
            # Report progress
            self._notify_progress(f"Importing: {filename}", i, total)
            
            # Check for duplicate in Media Pool
            existing = self._find_media_in_pool(file_path)
            if existing:
                logger.info(f"Media already in pool: {filename}")
                ref = MediaPoolReference(
                    file_path=file_path,
                    media_pool_id=existing.get("media_pool_id", self._generate_stable_id(file_path, "existing")),
                    media_type=media_type,
                )
                result.media_pool_refs.append(ref)
                result.imported_count += 1
                continue
            
            # Import to Media Pool
            imported = self._import_media_to_pool(file_path)
            
            if imported:
                ref = MediaPoolReference(
                    file_path=file_path,
                    media_pool_id=imported.get("media_pool_id", self._generate_stable_id(file_path, "imported")),
                    media_type=media_type,
                )
                result.media_pool_refs.append(ref)
                result.imported_count += 1
                logger.info(f"Successfully imported: {filename}")
            else:
                # Import failed
                result.skipped_files.append(
                    SkippedFile(
                        file_path=file_path,
                        reason="import_failed",
                        message=f"Failed to import {filename} to Media Pool",
                    )
                )
                result.skipped_count += 1
                logger.error(f"Failed to import: {filename}")
        
        return result

    def import_suggested_media(
        self, suggested_media: List[Dict[str, Any]]
    ) -> ImportResult:
        """Main entry point for importing suggested media.
        
        Performs batch validation followed by import with progress reporting.
        
        Args:
            suggested_media: List of media items suggested by AI.
                Each item should have: file_path, media_type, [usage, ...]
                
        Returns:
            ImportResult with all import results and any skipped files.
        """
        logger.info(f"Starting import of {len(suggested_media)} media files")
        
        # Resolve file paths to absolute paths
        resolved_media = self.resolve_file_paths(suggested_media)
        
        # Validate batch - separate valid from invalid
        valid_media, skipped = self.validate_media_batch(resolved_media)
        
        # Import valid media
        result = self.import_to_media_pool(valid_media)
        
        # Merge pre-validation skips with import skips
        result.skipped_files.extend(skipped)
        result.skipped_count += len(skipped)
        
        logger.info(
            f"Import complete: {result.imported_count} imported, "
            f"{result.skipped_count} skipped"
        )
        
        return result
