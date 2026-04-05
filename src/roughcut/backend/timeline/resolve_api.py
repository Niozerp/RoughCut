"""Resolve API wrapper for timeline operations."""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _generate_stable_id(file_path: str) -> str:
    """Generate a stable ID for a file path using hashlib."""
    return hashlib.md5(file_path.encode('utf-8')).hexdigest()[:12]


class ResolveApi:
    """Wrapper for DaVinci Resolve API interactions.
    
    Provides a simplified interface for:
    - Media Pool operations
    - Timeline creation and management
    - Track operations
    """

    def __init__(self) -> None:
        """Initialize the Resolve API wrapper."""
        self._resolve = None
        self._project_manager = None
        self._current_project = None
        self._media_pool = None

    def _get_resolve(self) -> Optional[Any]:
        """Get the Resolve application instance.
        
        Returns:
            Resolve application object or None if not available.
        """
        if self._resolve is None:
            try:
                import DaVinciResolveScript as dvr
                self._resolve = dvr.scriptapp("Resolve")
            except ImportError:
                logger.debug("DaVinciResolveScript not available")
            except Exception as e:
                logger.warning(f"Error accessing Resolve: {e}")
        return self._resolve

    def _get_project_manager(self) -> Optional[Any]:
        """Get the project manager."""
        if self._project_manager is None:
            resolve = self._get_resolve()
            if resolve:
                self._project_manager = resolve.GetProjectManager()
        return self._project_manager

    def _get_current_project(self) -> Optional[Any]:
        """Get the current project."""
        if self._current_project is None:
            pm = self._get_project_manager()
            if pm:
                self._current_project = pm.GetCurrentProject()
        return self._current_project

    def _get_media_pool(self) -> Optional[Any]:
        """Get the media pool for the current project."""
        if self._media_pool is None:
            project = self._get_current_project()
            if project:
                self._media_pool = project.GetMediaPool()
        return self._media_pool

    def is_available(self) -> bool:
        """Check if Resolve API is available.
        
        Returns:
            True if Resolve is accessible, False otherwise.
        """
        return self._get_resolve() is not None

    def find_media_in_pool(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Find media in the Media Pool by file path.
        
        Checks if a media file already exists in the pool to avoid duplicates.
        
        Args:
            file_path: Absolute path to the media file.
            
        Returns:
            Media info dict if found, None otherwise.
        """
        try:
            pool = self._get_media_pool()
            if not pool:
                return None
            
            # Get root folder and search recursively with depth limit
            root_folder = pool.GetRootFolder()
            if not root_folder:
                return None
            
            # P5 fix: Track visited folders and depth to prevent stack overflow
            result = self._search_folder_for_media(root_folder, file_path, visited=set(), depth=0)
            return result
            
        except Exception as e:
            logger.warning(f"Error searching Media Pool: {e}")
            return None

    def _search_folder_for_media(
        self, folder: Any, file_path: str, visited: set, depth: int
    ) -> Optional[Dict[str, Any]]:
        """Recursively search a folder for media by path.
        
        Args:
            folder: Folder to search
            file_path: Path to find
            visited: Set of visited folder IDs (prevents circular references)
            depth: Current recursion depth
            
        Returns:
            Media info dict if found, None otherwise.
        """
        MAX_DEPTH = 100  # P5 fix: Prevent stack overflow from deep nesting
        
        # Check depth limit
        if depth > MAX_DEPTH:
            logger.warning(f"Max folder depth ({MAX_DEPTH}) exceeded in Media Pool search")
            return None
        
        # Check for circular reference using folder id
        folder_id = id(folder)
        if folder_id in visited:
            logger.debug(f"Circular folder reference detected, skipping")
            return None
        visited.add(folder_id)
        
        try:
            # Check clips in current folder
            clips = folder.GetClips() or {}
            for clip_id, clip in clips.items():
                if hasattr(clip, 'GetClipProperty'):
                    clip_path = clip.GetClipProperty("File Path")
                    if clip_path == file_path:
                        return {
                            "media_pool_id": str(clip_id),
                            "file_path": file_path,
                            "clip": clip,
                        }
            
            # Recursively search subfolders with incremented depth
            subfolders = folder.GetSubFolders() or {}
            for _, subfolder in subfolders.items():
                result = self._search_folder_for_media(subfolder, file_path, visited, depth + 1)
                if result:
                    return result
                    
        except Exception as e:
            logger.debug(f"Error searching folder: {e}")
        
        return None

    def import_media_to_pool(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Import a media file into the Media Pool.
        
        Args:
            file_path: Absolute path to the media file.
            
        Returns:
            Media info dict with media_pool_id if successful, None otherwise.
        """
        try:
            pool = self._get_media_pool()
            if not pool:
                logger.error("Media Pool not available")
                return None
            
            # Import media file
            # Note: The actual Resolve API for importing may vary
            # This is a common pattern but may need adjustment
            new_clips = pool.ImportMedia([file_path])
            
            if new_clips and len(new_clips) > 0:
                clip = new_clips[0]
                clip_id = _generate_stable_id(file_path)
                
                logger.info(f"Successfully imported: {file_path}")
                return {
                    "media_pool_id": clip_id,
                    "file_path": file_path,
                    "clip": clip,
                }
            else:
                logger.error(f"Import returned no clips for: {file_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error importing media: {e}")
            return None

    def create_timeline(self, name: str) -> Optional[Dict[str, Any]]:
        """Create a new timeline in the current project.
        
        Args:
            name: Name for the new timeline.
            
        Returns:
            Timeline info dict if successful, None otherwise.
        """
        try:
            pool = self._get_media_pool()
            if not pool:
                logger.error("Media Pool not available")
                return None
            
            timeline = pool.CreateEmptyTimeline(name)
            if timeline:
                timeline_id = str(hash(name + str(id(timeline))))
                return {
                    "timeline_id": timeline_id,
                    "name": name,
                    "timeline": timeline,
                }
            else:
                logger.error(f"Failed to create timeline: {name}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating timeline: {e}")
            return None

    def get_timeline_count(self) -> int:
        """Get the number of timelines in the current project.
        
        Returns:
            Number of timelines.
        """
        try:
            project = self._get_current_project()
            if not project:
                return 0
            return project.GetTimelineCount() or 0
        except Exception as e:
            logger.warning(f"Error getting timeline count: {e}")
            return 0
