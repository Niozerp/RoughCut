"""Media importer for importing suggested assets into Resolve's Media Pool.

Handles file validation, duplicate detection, and Media Pool integration
for the rough cut workflow.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .resolve_api import ResolveApi

logger = logging.getLogger(__name__)

# Supported file formats
SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".aiff", ".m4a", ".flac"}
SUPPORTED_VFX_FORMATS = {".comp", ".settings", ".drfx"}
SUPPORTED_MEDIA_FORMATS = SUPPORTED_AUDIO_FORMATS | SUPPORTED_VFX_FORMATS


@dataclass
class MediaPoolReference:
    """Reference to a media item in Resolve's Media Pool.
    
    Attributes:
        file_path: Absolute path to the media file
        media_pool_id: Unique identifier in Resolve's Media Pool
        media_type: Type of media (music, sfx, vfx)
    """
    file_path: str
    media_pool_id: str
    media_type: str


@dataclass
class ImportResult:
    """Result of a media import operation.
    
    Attributes:
        imported_count: Number of successfully imported media files
        skipped_count: Number of files skipped (missing, invalid, etc.)
        media_pool_refs: List of Media Pool references for imported items
        skipped_files: List of skipped files with reasons
        success: Whether the operation succeeded (can be True even with skips)
        error: Error details if the entire operation failed
    """
    imported_count: int
    skipped_count: int
    media_pool_refs: List[MediaPoolReference] = field(default_factory=list)
    skipped_files: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = True
    error: Optional[Dict[str, Any]] = None


class MediaImporter:
    """Imports suggested media into Resolve's Media Pool.
    
    This class handles:
    - File path validation and accessibility checks (NFR10)
    - Duplicate detection to avoid re-importing existing media
    - Media Pool integration via Resolve API
    - Progress reporting during import operations
    - Graceful handling of missing or inaccessible files
    
    Usage:
        importer = MediaImporter()
        result = importer.import_suggested_media([
            {"file_path": "/path/to/music.mp3", "media_type": "music"},
            {"file_path": "/path/to/sfx.wav", "media_type": "sfx"}
        ])
    """
    
    def __init__(self, resolve_api: Optional[ResolveApi] = None):
        """Initialize the media importer.
        
        Args:
            resolve_api: Optional ResolveApi instance for testing/mocking.
                        If not provided, a new instance will be created.
        """
        self.resolve_api = resolve_api or ResolveApi()
        logger.info("MediaImporter initialized")
    
    def validate_file_accessibility(self, file_path: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate that a file exists and is accessible.
        
        Performs comprehensive validation per NFR10:
        - File must exist at specified path
        - File must be readable (permission check)
        - File format must be supported
        
        Args:
            file_path: Absolute path to the media file
            
        Returns:
            Tuple of (is_valid, error_dict)
            - is_valid: True if file is accessible and valid
            - error_dict: None if valid, or error details if invalid
        """
        # Check file exists
        if not os.path.exists(file_path):
            error = {
                "code": "FILE_NOT_FOUND",
                "category": "file_system",
                "message": f"File not found: {file_path}",
                "recoverable": True,
                "suggestion": "Verify the file path is correct and the file exists"
            }
            logger.warning(f"File not found: {file_path}")
            return False, error
        
        # Check file is readable (permission check)
        if not os.access(file_path, os.R_OK):
            error = {
                "code": "FILE_ACCESS_DENIED",
                "category": "file_system",
                "message": f"Cannot access file (permission denied): {file_path}",
                "recoverable": True,
                "suggestion": "Check file permissions and ensure Resolve has access to the media folder"
            }
            logger.warning(f"File access denied: {file_path}")
            return False, error
        
        # Check file format is supported
        if not self._is_supported_format(file_path):
            file_ext = Path(file_path).suffix.lower()
            error = {
                "code": "UNSUPPORTED_FORMAT",
                "category": "validation",
                "message": f"Unsupported file format: {file_ext}",
                "recoverable": True,
                "suggestion": f"Supported formats: audio {SUPPORTED_AUDIO_FORMATS}, VFX {SUPPORTED_VFX_FORMATS}"
            }
            logger.warning(f"Unsupported file format: {file_path}")
            return False, error
        
        return True, None
    
    def _is_supported_format(self, file_path: str) -> bool:
        """Check if a file format is supported for import.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            True if the file extension is in supported formats
        """
        file_ext = Path(file_path).suffix.lower()
        return file_ext in SUPPORTED_MEDIA_FORMATS
    
    def validate_media_batch(
        self,
        suggested_media: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Validate a batch of suggested media files.
        
        Separates valid files from invalid/missing ones before import.
        This allows the import to continue even if some files are missing.
        
        Args:
            suggested_media: List of media dictionaries with 'file_path' and 'media_type'
            
        Returns:
            Tuple of (valid_files, skipped_files)
            - valid_files: List of media dicts that passed validation
            - skipped_files: List of dicts with file_path, reason, and message
        """
        valid_files = []
        skipped_files = []
        
        for media in suggested_media:
            file_path = media.get("file_path", "")
            
            is_valid, error = self.validate_file_accessibility(file_path)
            
            if is_valid:
                valid_files.append(media)
            else:
                skipped_files.append({
                    "file_path": file_path,
                    "reason": error["code"].lower() if error else "unknown",
                    "message": error["message"] if error else "File validation failed"
                })
                logger.info(f"Skipping file due to validation failure: {file_path}")
        
        logger.info(f"Batch validation complete: {len(valid_files)} valid, {len(skipped_files)} skipped")
        return valid_files, skipped_files
    
    def _check_duplicate_in_media_pool(self, file_path: str) -> Optional[str]:
        """Check if a file already exists in Resolve's Media Pool.
        
        Uses the Resolve API to search for media by file path.
        
        Args:
            file_path: Absolute path to the media file
            
        Returns:
            Media Pool ID if found, None if not in pool
        """
        try:
            # Use Resolve API to find media in pool
            media_id = self.resolve_api.find_media_in_pool(file_path)
            if media_id:
                logger.debug(f"Found existing media in pool: {file_path} -> {media_id}")
            return media_id
        except Exception as e:
            logger.warning(f"Error checking for duplicate in media pool: {e}")
            return None
    
    def import_single_media(
        self,
        file_path: str,
        media_type: str
    ) -> Optional[MediaPoolReference]:
        """Import a single media file into Resolve's Media Pool.
        
        Performs duplicate detection and only imports if not already in pool.
        
        Args:
            file_path: Absolute path to the media file
            media_type: Type of media (music, sfx, vfx)
            
        Returns:
            MediaPoolReference if successful, None if failed
        """
        # Validate file first
        is_valid, error = self.validate_file_accessibility(file_path)
        if not is_valid:
            logger.warning(f"Cannot import invalid file: {file_path}")
            return None
        
        # Check for duplicates
        existing_id = self._check_duplicate_in_media_pool(file_path)
        if existing_id:
            logger.info(f"Using existing media pool entry: {file_path}")
            return MediaPoolReference(
                file_path=file_path,
                media_pool_id=existing_id,
                media_type=media_type
            )
        
        # Import to media pool
        try:
            media_pool_id = self.resolve_api.import_media_to_pool(file_path)
            if media_pool_id:
                logger.info(f"Successfully imported to media pool: {file_path} -> {media_pool_id}")
                return MediaPoolReference(
                    file_path=file_path,
                    media_pool_id=media_pool_id,
                    media_type=media_type
                )
            else:
                logger.error(f"Import returned no media pool ID: {file_path}")
                return None
        except Exception as e:
            logger.exception(f"Error importing media to pool: {file_path}")
            return None
    
    def import_suggested_media(
        self,
        suggested_media: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> ImportResult:
        """Import a batch of suggested media files into Resolve's Media Pool.
        
        This is the main entry point for importing AI-suggested media assets.
        It validates all files first, then imports valid ones with progress reporting.
        
        Args:
            suggested_media: List of media dictionaries with keys:
                - file_path: Absolute path to media file
                - media_type: Type of media (music, sfx, vfx)
                - usage: Optional usage context (intro, transition, etc.)
            progress_callback: Optional callback function(current, total, message)
                Called after each file import with progress updates.
                
        Returns:
            ImportResult with import counts, references, and any skipped files
        """
        if not suggested_media:
            logger.info("No suggested media to import")
            return ImportResult(
                imported_count=0,
                skipped_count=0,
                media_pool_refs=[],
                skipped_files=[]
            )
        
        # First, validate all files
        valid_files, skipped_files = self.validate_media_batch(suggested_media)
        
        imported_refs = []
        total_files = len(valid_files)
        
        # Import valid files with progress reporting
        for idx, media in enumerate(valid_files, 1):
            file_path = media.get("file_path", "")
            media_type = media.get("media_type", "unknown")
            
            # Report progress
            filename = Path(file_path).name
            progress_message = f"Importing: {filename}"
            if progress_callback:
                progress_callback(idx, total_files, progress_message)
            logger.info(progress_message)
            
            # Import the file
            ref = self.import_single_media(file_path, media_type)
            
            if ref:
                imported_refs.append(ref)
            else:
                # Import failed - add to skipped
                skipped_files.append({
                    "file_path": file_path,
                    "reason": "import_failed",
                    "message": "Failed to import to Media Pool"
                })
        
        # Build result
        result = ImportResult(
            imported_count=len(imported_refs),
            skipped_count=len(skipped_files),
            media_pool_refs=imported_refs,
            skipped_files=skipped_files,
            success=True  # Success even if some files were skipped
        )
        
        logger.info(
            f"Import complete: {result.imported_count} imported, "
            f"{result.skipped_count} skipped"
        )
        
        return result
