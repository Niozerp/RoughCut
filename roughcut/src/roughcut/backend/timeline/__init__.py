"""Timeline module for Resolve timeline operations.

Provides timeline creation, track management, and Resolve API integration
for the rough cut workflow.
"""

from .builder import TimelineBuilder, TimelineCreationResult
from .track_manager import TrackManager
from .resolve_api import ResolveApi

__all__ = [
    "TimelineBuilder",
    "TimelineCreationResult", 
    "TrackManager",
    "ResolveApi"
]
