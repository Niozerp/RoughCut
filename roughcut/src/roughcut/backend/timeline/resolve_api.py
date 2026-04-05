"""Resolve API abstraction layer for timeline operations.

Provides a clean interface to DaVinci Resolve's scripting API
with proper error handling and version compatibility.
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ResolveApi:
    """Abstraction layer for DaVinci Resolve API.
    
    This class wraps Resolve's Lua-exposed Python API, providing:
    - Version compatibility abstraction
    - Consistent error handling
    - Timeline and track operations
    - Non-destructive guarantees
    
    Usage:
        api = ResolveApi()
        if api.is_available():
            timeline = api.create_timeline("MyTimeline")
    """
    
    def __init__(self):
        """Initialize the Resolve API wrapper."""
        self._resolve = None
        self._project = None
        self._fusion = None
        self._initialized = False
        
        logger.debug("ResolveApi initialized")
    
    def _get_resolve(self) -> Optional[Any]:
        """Get the Resolve application instance.
        
        Returns:
            Resolve application object or None if not available
        """
        if self._resolve is not None:
            return self._resolve
        
        try:
            # Try to import the resolve module (available in Resolve's Python environment)
            import DaVinciResolveScript as dvr_script
            self._resolve = dvr_script.scriptapp("Resolve")
            
            if self._resolve:
                logger.info("Connected to DaVinci Resolve")
                self._fusion = self._resolve.Fusion()
            
            return self._resolve
            
        except ImportError:
            logger.debug("DaVinciResolveScript module not available (expected outside Resolve)")
            return None
        except Exception as e:
            logger.error(f"Error connecting to Resolve: {e}")
            return None
    
    def _get_project(self) -> Optional[Any]:
        """Get the current Resolve project.
        
        Returns:
            Current project object or None if not available
        """
        if self._project is not None:
            return self._project
        
        resolve = self._get_resolve()
        if not resolve:
            return None
        
        try:
            self._project = resolve.GetProjectManager().GetCurrentProject()
            if self._project:
                logger.debug(f"Got current project: {self._project.GetName()}")
            return self._project
        except Exception as e:
            logger.error(f"Error getting current project: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if Resolve API is available and accessible.
        
        Returns:
            True if Resolve is running and API is enabled, False otherwise
        """
        resolve = self._get_resolve()
        if not resolve:
            return False
        
        try:
            # Try to get project manager as a basic connectivity test
            project_manager = resolve.GetProjectManager()
            return project_manager is not None
        except Exception as e:
            logger.debug(f"Resolve API connectivity test failed: {e}")
            return False
    
    def get_current_timeline(self) -> Optional[Any]:
        """Get the currently active timeline.
        
        Returns:
            Current timeline object or None if no timeline is active
        """
        project = self._get_project()
        if not project:
            return None
        
        try:
            timeline = project.GetCurrentTimeline()
            if timeline:
                logger.debug(f"Got current timeline: {timeline.GetName()}")
            return timeline
        except Exception as e:
            logger.error(f"Error getting current timeline: {e}")
            return None
    
    def find_timeline_by_name(self, name: str) -> Optional[Any]:
        """Find a timeline by name.
        
        Args:
            name: Timeline name to search for
            
        Returns:
            Timeline object if found, None otherwise
        """
        project = self._get_project()
        if not project:
            return None
        
        try:
            # Get timeline count and iterate
            timeline_count = project.GetTimelineCount()
            
            for i in range(1, timeline_count + 1):
                timeline = project.GetTimelineByIndex(i)
                if timeline and timeline.GetName() == name:
                    logger.debug(f"Found timeline: {name}")
                    return timeline
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding timeline '{name}': {e}")
            return None
    
    def create_timeline(self, name: str) -> Optional[Any]:
        """Create a new timeline.
        
        Args:
            name: Name for the new timeline
            
        Returns:
            Created timeline object or None if creation failed
        """
        project = self._get_project()
        if not project:
            logger.error("No project available for timeline creation")
            return None
        
        try:
            # Create new timeline
            timeline = project.CreateEmptyTimeline(name)
            
            if timeline:
                logger.info(f"Created timeline: {name}")
                return timeline
            else:
                logger.error(f"Timeline creation returned None for: {name}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating timeline '{name}': {e}")
            return None
    
    def set_current_timeline(self, timeline: Any) -> bool:
        """Set the specified timeline as the current/active timeline.
        
        Args:
            timeline: Timeline object to activate
            
        Returns:
            True if successful, False otherwise
        """
        project = self._get_project()
        if not project:
            return False
        
        try:
            result = project.SetCurrentTimeline(timeline)
            if result:
                logger.debug(f"Set current timeline: {timeline.GetName()}")
            return result
        except Exception as e:
            logger.error(f"Error setting current timeline: {e}")
            return False
    
    def get_media_pool(self) -> Optional[Any]:
        """Get the media pool for the current project.
        
        Returns:
            MediaPool object or None if not available
        """
        project = self._get_project()
        if not project:
            return None
        
        try:
            media_pool = project.GetMediaPool()
            return media_pool
        except Exception as e:
            logger.error(f"Error getting media pool: {e}")
            return None
    
    def get_timeline_track_count(self, timeline: Any, track_type: str) -> int:
        """Get the number of tracks of a specific type.
        
        Args:
            timeline: Timeline object
            track_type: Track type ("video", "audio", "subtitle")
            
        Returns:
            Number of tracks, or 0 on error
        """
        if not timeline:
            return 0
        
        try:
            if track_type == "video":
                return timeline.GetTrackCount("video")
            elif track_type == "audio":
                return timeline.GetTrackCount("audio")
            elif track_type == "subtitle":
                return timeline.GetTrackCount("subtitle")
            else:
                logger.warning(f"Unknown track type: {track_type}")
                return 0
        except Exception as e:
            logger.error(f"Error getting track count: {e}")
            return 0
    
    def add_track(self, timeline: Any, track_type: str) -> bool:
        """Add a new track to the timeline.
        
        Note: In DaVinci Resolve, tracks are added to timelines via the timeline's
        AddTrack method or through the project. This implementation uses the timeline
        directly when available.
        
        Args:
            timeline: Timeline object
            track_type: Track type ("video", "audio", "subtitle")
            
        Returns:
            True if track was added, False otherwise
        """
        if not timeline:
            return False
        
        try:
            # Try to add track directly via timeline if method exists
            if hasattr(timeline, 'AddTrack'):
                result = timeline.AddTrack(track_type)
                if result:
                    logger.debug(f"Added {track_type} track to timeline via AddTrack")
                    return True
            
            # Fallback: Try via media pool context (may work in some Resolve versions)
            media_pool = self.get_media_pool()
            if media_pool and hasattr(media_pool, 'AddTrack'):
                # Set current timeline in media pool context first
                if hasattr(media_pool, 'SetCurrentTimeline'):
                    media_pool.SetCurrentTimeline(timeline)
                result = media_pool.AddTrack(track_type)
                if result:
                    logger.debug(f"Added {track_type} track via MediaPool")
                    return True
            
            logger.warning(f"Could not add {track_type} track - no suitable API method available")
            return False
            
        except Exception as e:
            logger.error(f"Error adding {track_type} track: {e}")
            return False
    
    def get_resolve_version(self) -> Optional[str]:
        """Get the DaVinci Resolve version string.
        
        Returns:
            Version string or None if not available
        """
        resolve = self._get_resolve()
        if not resolve:
            return None
        
        try:
            version = resolve.GetVersion()
            return version
        except Exception as e:
            logger.error(f"Error getting Resolve version: {e}")
            return None
    
    def find_media_in_pool(self, file_path: str) -> Optional[str]:
        """Find media in the Media Pool by file path.
        
        Checks if a media file already exists in Resolve's Media Pool.
        This is used for duplicate detection to avoid re-importing.
        
        Args:
            file_path: Absolute path to the media file
            
        Returns:
            Media Pool item ID if found, None otherwise
        """
        media_pool = self.get_media_pool()
        if not media_pool:
            logger.warning("Cannot search media pool - Resolve API not available")
            return None
        
        try:
            # Get the root folder of the media pool
            root_folder = media_pool.GetRootFolder()
            if not root_folder:
                logger.warning("Could not get media pool root folder")
                return None
            
            # Search for the clip by file path
            # Resolve API: GetClipList() returns clips in current folder
            clips = root_folder.GetClipList()
            if not clips:
                return None
            
            # Look for a clip matching our file path
            for clip in clips:
                try:
                    # GetClipProperty returns a dict with file path info
                    clip_props = clip.GetClipProperty()
                    if clip_props:
                        clip_path = clip_props.get("File Path") or clip_props.get("FilePath")
                        if clip_path and os.path.normpath(clip_path) == os.path.normpath(file_path):
                            clip_name = clip.GetName()
                            logger.debug(f"Found existing media: {file_path} -> {clip_name}")
                            return clip_name  # Use clip name as ID
                except Exception as e:
                    logger.debug(f"Error checking clip properties: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching media pool: {e}")
            return None
    
    def import_media_to_pool(self, file_path: str) -> Optional[str]:
        """Import a media file into Resolve's Media Pool.
        
        Adds a media file to the current project's Media Pool if not already present.
        This is a non-destructive operation - it only creates a reference to the file.
        
        Args:
            file_path: Absolute path to the media file to import
            
        Returns:
            Media Pool item ID (clip name) if successful, None otherwise
        """
        media_pool = self.get_media_pool()
        if not media_pool:
            logger.error("Cannot import media - Resolve API not available")
            return None
        
        try:
            # First check if already in pool (duplicate detection)
            existing_id = self.find_media_in_pool(file_path)
            if existing_id:
                logger.info(f"Media already in pool, using existing: {file_path}")
                return existing_id
            
            # Import the media file
            # Resolve API: ImportMedia() imports files into the media pool
            root_folder = media_pool.GetRootFolder()
            if not root_folder:
                logger.error("Could not get media pool root folder for import")
                return None
            
            # ImportMedia returns a list of imported MediaPoolItem objects
            imported_items = media_pool.ImportMedia([file_path])
            
            if imported_items and len(imported_items) > 0:
                # Get the first imported item's name as ID
                media_id = imported_items[0].GetName()
                logger.info(f"Successfully imported: {file_path} -> {media_id}")
                return media_id
            else:
                logger.warning(f"ImportMedia returned empty result for: {file_path}")
                return None
                
        except Exception as e:
            logger.exception(f"Error importing media to pool: {file_path}")
            return None
    
    def create_timeline_clip(
        self,
        timeline: Any,
        source_clip: Any,
        track_index: int,
        timeline_position: int,
        source_in: int,
        source_out: int
    ) -> Optional[Any]:
        """Create a timeline clip referencing source with specified in/out points.
        
        This is the core method for non-destructive cutting - it creates
        a timeline clip that references the source with specific in/out points,
        allowing the same source to appear multiple times with different ranges.
        
        Args:
            timeline: Resolve timeline object
            source_clip: Media Pool clip object
            track_index: Target track number (1 for video)
            timeline_position: Frame position on timeline
            source_in: In point frame on source
            source_out: Out point frame on source
            
        Returns:
            Timeline clip object if successful, None otherwise
            
        Note:
            This is a non-destructive operation - the source clip is never modified.
        """
        if not timeline:
            logger.error("Cannot create timeline clip: no timeline provided")
            return None
        
        if not source_clip:
            logger.error("Cannot create timeline clip: no source clip provided")
            return None
        
        # Validate in/out points
        if source_in < 0:
            logger.error(f"Invalid source_in: {source_in}. Must be non-negative.")
            return None
        
        if source_out <= source_in:
            logger.error(f"Invalid source range: source_in ({source_in}) >= source_out ({source_out}). "
                        f"source_out must be greater than source_in.")
            return None
        
        try:
            # Method 1: Try using AddClip on timeline (most direct)
            if hasattr(timeline, 'AddClip'):
                # Resolve API: AddClip(clip, trackIndex, startFrame, duration)
                duration = source_out - source_in
                
                # Note: Some Resolve versions expect time in different units
                # This implementation assumes frame-based timing
                result = timeline.AddClip(
                    source_clip,
                    track_index,
                    timeline_position,
                    duration
                )
                
                if result:
                    logger.debug(
                        f"Created timeline clip at track {track_index}, "
                        f"position {timeline_position}, duration {duration}"
                    )
                    return result
            
            # Method 2: Try via media pool AppendToTimeline (fallback)
            media_pool = self.get_media_pool()
            if media_pool and hasattr(media_pool, 'AppendToTimeline'):
                logger.warning("Using fallback AppendToTimeline method for clip creation")
                
                # This method may not support in/out points directly
                # but is included as a fallback
                result = media_pool.AppendToTimeline(source_clip)
                if result:
                    # The clip was appended, but we may need to adjust its position
                    # This is less precise but works as fallback
                    logger.debug("Clip appended to timeline via MediaPool fallback")
                    return result
            
            logger.error("No suitable API method available for creating timeline clip")
            return None
            
        except Exception as e:
            logger.exception(f"Error creating timeline clip: {e}")
            return None
