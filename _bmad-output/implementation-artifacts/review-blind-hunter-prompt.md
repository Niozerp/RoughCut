# Blind Hunter Review Prompt

## Role
You are a Blind Hunter code reviewer. You have NO project context, NO spec file, and NO access to the codebase. You review ONLY the diff provided.

## Your Task
Find issues in this code diff without any context. Look for:
- Obvious bugs, logic errors, or anti-patterns
- Security vulnerabilities
- Performance issues
- Code smells and maintainability problems
- Style inconsistencies
- Missing error handling
- Race conditions
- Resource leaks

## Diff to Review

```diff
diff --git a/roughcut/src/roughcut/backend/timeline/__init__.py b/roughcut/src/roughcut/backend/timeline/__init__.py
index d164455..88bc754 100644
--- a/roughcut/src/roughcut/backend/timeline/__init__.py
+++ b/roughcut/src/roughcut/backend/timeline/__init__.py
@@ -1,7 +1,7 @@
 """Timeline module for Resolve timeline operations.
 
 Provides timeline creation, track management, media importing, segment cutting,
-music placement, SFX placement, and Resolve API integration for the rough cut workflow.
+music placement, SFX placement, VFX placement, and Resolve API integration for the rough cut workflow.
 """
 
 from .builder import TimelineBuilder, TimelineCreationResult
@@ -9,6 +9,7 @@ from .cutter import FootageCutter, CutResult, SegmentPlacement
 from .importer import MediaImporter, ImportResult, MediaPoolReference
 from .music_placer import MusicPlacer, MusicPlacerResult, MusicPlacement
 from .sfx_placer import SfxPlacer, SfxPlacerResult, SfxPlacement
+from .vfx_placer import VfxPlacer, VfxPlacerResult, VfxPlacement, TrackAllocationError
 from .track_manager import TrackManager
 from .resolve_api import ResolveApi
 
@@ -27,6 +28,10 @@ __all__ = [
     "SfxPlacer",
     "SfxPlacerResult",
     "SfxPlacement",
+    "VfxPlacer",
+    "VfxPlacerResult",
+    "VfxPlacement",
+    "TrackAllocationError",
     "TrackManager",
     "ResolveApi"
 ]
diff --git a/roughcut/src/roughcut/protocols/handlers/timeline.py b/roughcut/src/roughcut/protocols/handlers/timeline.py
index 0f61af1..743648a 100644
--- a/roughcut/src/roughcut/protocols/handlers/timeline.py
+++ b/roughcut/src/roughcut/protocols/handlers/timeline.py
@@ -12,6 +12,7 @@ from ...backend.timeline.cutter import FootageCutter, CutResult
 from ...backend.timeline.importer import MediaImporter, ImportResult
 from ...backend.timeline.music_placer import MusicPlacer, MusicPlacerResult
 from ...backend.timeline.sfx_placer import SfxPlacer, SfxPlacerResult
+from ...backend.timeline.vfx_placer import VfxPlacer, VfxPlacerResult
 from ...backend.workflows.session import get_session_manager
 
 logger = logging.getLogger(__name__)
@@ -36,7 +37,9 @@ ERROR_CODES = {
     "MISSING_MUSIC_SEGMENTS": "MISSING_MUSIC_SEGMENTS",
     "SFX_PLACEMENT_FAILED": "SFX_PLACEMENT_FAILED",
     "MISSING_SFX_SEGMENTS": "MISSING_SFX_SEGMENTS",
-    "TRACK_ALLOCATION_FAILED": "TRACK_ALLOCATION_FAILED"
+    "TRACK_ALLOCATION_FAILED": "TRACK_ALLOCATION_FAILED",
+    "VFX_PLACEMENT_FAILED": "VFX_PLACEMENT_FAILED",
+    "MISSING_VFX_SEGMENTS": "MISSING_VFX_SEGMENTS"
 }
 
 
@@ -767,6 +770,137 @@ def place_sfx_on_timeline(params: Dict[str, Any] | None) -> Dict[str, Any]:
         )
 
 
+def place_vfx_on_timeline(params: Dict[str, Any] | None) -> Dict[str, Any]:
+    """Place AI-suggested VFX templates on the timeline.
+    
+    This handler is called from the Lua GUI after SFX placement to place
+    VFX templates on the timeline's dedicated VFX tracks (Tracks 11-14).
+    
+    Args:
+        params: Request parameters containing:
+            - timeline_id: Target timeline ID (required)
+            - vfx_segments: List of VFX segment dictionaries (required)
+            
+    Returns:
+        Dictionary with VFX placement result or error
+    """
+    if params is None:
+        params = {}
+    
+    # Validate required parameters
+    timeline_id = params.get("timeline_id")
+    if not timeline_id:
+        logger.error("Missing timeline_id parameter")
+        return _error_response(
+            ERROR_CODES["TIMELINE_NOT_FOUND"],
+            "validation",
+            "Timeline ID is required",
+            "Ensure timeline was created successfully before placing VFX",
+            recoverable=True
+        )
+    
+    vfx_segments = params.get("vfx_segments")
+    if vfx_segments is None:
+        logger.error("Missing vfx_segments parameter")
+        return _error_response(
+            ERROR_CODES["MISSING_VFX_SEGMENTS"],
+            "validation",
+            "No vfx_segments parameter provided",
+            "Generate a rough cut with AI VFX suggestions first",
+            recoverable=True
+        )
+    
+    if not isinstance(vfx_segments, list):
+        return _error_response(
+            ERROR_CODES["INVALID_PARAMS"],
+            "validation",
+            "vfx_segments must be a list",
+            "Provide a list of VFX segment dictionaries with file paths and timing",
+            recoverable=True
+        )
+    
+    if len(vfx_segments) == 0:
+        logger.info("Empty vfx_segments list - nothing to place")
+        return {
+            "clips_placed": 0,
+            "tracks_used": [],
+            "total_duration_frames": 0,
+            "total_duration_timecode": "0:00:00",
+            "timeline_positions": [],
+            "success": True,
+            "warning": "No VFX segments to place"
+        }
+    
+    logger.info(f"Placing {len(vfx_segments)} VFX templates on timeline {timeline_id}")
+    
+    try:
+        # Create placer and perform placement
+        placer = VfxPlacer()
+        
+        # Progress callback that emits JSON-RPC progress messages
+        def progress_callback(current: int, total: int, message: str):
+            logger.info(f"Progress: {message} ({current}/{total})")
+        
+        result = placer.place_vfx_templates(
+            timeline_id=timeline_id,
+            vfx_segments=vfx_segments,
+            progress_callback=progress_callback
+        )
+        
+        if result.success:
+            # Convert placements to serializable format
+            timeline_positions = []
+            for placement in result.timeline_positions:
+                timeline_positions.append({
+                    "segment_index": placement.segment_index,
+                    "track_number": placement.track_number,
+                    "timeline_start_frame": placement.timeline_start_frame,
+                    "timeline_end_frame": placement.timeline_end_frame,
+                    "vfx_file_path": placement.vfx_file_path,
+                    "clip_id": placement.clip_id,
+                    "fade_in_frames": placement.fade_in_frames,
+                    "fade_out_frames": placement.fade_out_frames,
+                    "template_type": placement.template_type,
+                    "template_params_applied": placement.template_params,
+                    "vfx_type": placement.vfx_type
+                })
+            
+            logger.info(
+                f"VFX placement complete: {result.clips_placed} clips, "
+                f"tracks used: {result.tracks_used}, "
+                f"duration: {result.total_duration_timecode}"
+            )
+            
+            return {
+                "clips_placed": result.clips_placed,
+                "tracks_used": result.tracks_used,
+                "total_duration_frames": result.total_duration_frames,
+                "total_duration_timecode": result.total_duration_timecode,
+                "timeline_positions": timeline_positions,
+                success": True
+            }
+        else:
+            # Return error from placer
+            error = result.error or {}
+            return _error_response(
+                error.get("code", ERROR_CODES["VFX_PLACEMENT_FAILED"]),
+                error.get("category", "internal"),
+                error.get("message", "VFX placement failed"),
+                error.get("suggestion", "Check Resolve is running and VFX files are accessible"),
+                error.get("recoverable", True)
+            )
+            
+    except Exception as e:
+        logger.exception(f"Error placing VFX on timeline: {e}")
+        return _error_response(
+            ERROR_CODES["INTERNAL_ERROR"],
+            "internal",
+            f"Unexpected error during VFX placement: {str(e)}",
+            "Check application logs and retry the operation",
+            recoverable=True
+        )
+
+
 # Handler registry for the dispatcher
 TIMELINE_HANDLERS: Dict[str, Callable] = {
     "create_timeline_from_document": create_timeline_from_document,
     "create_timeline": create_timeline,
     "import_suggested_media": import_suggested_media,
     "cut_footage_to_segments": cut_footage_to_segments,
     "place_music_on_timeline": place_music_on_timeline,
-    "place_sfx_on_timeline": place_sfx_on_timeline
+    "place_sfx_on_timeline": place_sfx_on_timeline,
+    "place_vfx_on_timeline": place_vfx_on_timeline
 }
```

## New Files (Review These Too)

The implementation also includes these new files that must be reviewed:

1. **roughcut/src/roughcut/backend/timeline/vfx_placer.py** (1065+ lines)
   - Main VfxPlacer class implementation
   - Track allocation logic
   - Conflict detection
   - Template parameter handling
   - VFX type detection (Fusion vs generator)

2. **roughcut/tests/unit/backend/timeline/test_vfx_placer.py** (600+ lines)
   - Comprehensive unit tests
   - 14 test classes
   - 50+ individual test methods

## Output Format

Provide your findings as a Markdown list. For each finding:
- **One-line title** describing the issue
- **Category**: bug, security, performance, style, maintainability, or other
- **Evidence**: Quote the problematic code or describe the location
- **Explanation**: Briefly explain why this is an issue

If you find no issues, state "No issues found from blind review perspective."

## Begin Review

Review the diff and new files now. Focus on what you can detect without any context.
