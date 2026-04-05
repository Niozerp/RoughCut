"""Timeline module for Resolve timeline operations.

Provides timeline creation, track management, media importing, segment cutting,
music placement, SFX placement, and Resolve API integration for the rough cut workflow.
"""

from .builder import TimelineBuilder, TimelineCreationResult
from .cutter import FootageCutter, CutResult, SegmentPlacement
from .importer import MediaImporter, ImportResult, MediaPoolReference
from .music_placer import MusicPlacer, MusicPlacerResult, MusicPlacement
from .sfx_placer import SfxPlacer, SfxPlacerResult, SfxPlacement
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
    "MusicPlacer",
    "MusicPlacerResult",
    "MusicPlacement",
    "SfxPlacer",
    "SfxPlacerResult",
    "SfxPlacement",
    "TrackManager",
    "ResolveApi"
]
