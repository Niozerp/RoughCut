"""Resolve API abstraction layer for timeline operations.

Provides a clean interface to DaVinci Resolve's scripting API
with proper error handling and version compatibility.
"""

import logging
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
