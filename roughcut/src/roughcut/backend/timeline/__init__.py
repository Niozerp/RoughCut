"""Timeline module for Resolve timeline operations.

Provides timeline creation, track management, media importing, segment cutting,
and Resolve API integration for the rough cut workflow.
"""

from .builder import TimelineBuilder, TimelineCreationResult
from .cutter import FootageCutter, CutResult, SegmentPlacement
from .importer import MediaImporter, ImportResult, MediaPoolReference
from .track_manager import TrackManager
from .resolve_api import ResolveApi

__all__ = [
    "TimelineBuilder",
    "TimelineCreationResult",
    "FootageCutter",
    "CutResult",
    "SegmentPlacement",
    "MediaImporter",
    "ImportResult",
    "MediaPoolReference",
    "TrackManager",
    "ResolveApi"
]
