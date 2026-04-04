"""Protocol handlers for format template operations including asset matching."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Protocol

from roughcut.backend.formats.matcher import AssetMatcher
from roughcut.backend.formats.models import AssetGroup

logger = logging.getLogger(__name__)


class TemplateCache(Protocol):
    """Protocol for template cache interface."""

    def get(self, template_id: str) -> Optional[Any]:
        """Get template by ID from cache."""
        ...


class DatabaseClient(Protocol):
    """Protocol for database client."""

    def get_assets_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Query assets by category."""
        ...


# Global cache and database client references (to be initialized)
_template_cache: Optional[TemplateCache] = None
_database_client: Optional[DatabaseClient] = None


def initialize_handlers(cache: TemplateCache, db: DatabaseClient) -> None:
    """Initialize handlers with cache and database references."""
    global _template_cache, _database_client
    _template_cache = cache
    _database_client = db


def get_template_cache() -> TemplateCache:
    """Get the template cache, raising if not initialized."""
    if _template_cache is None:
        raise RuntimeError("Template cache not initialized. Call initialize_handlers() first.")
    return _template_cache


def get_database_client() -> DatabaseClient:
    """Get the database client, raising if not initialized."""
    if _database_client is None:
        raise RuntimeError("Database client not initialized. Call initialize_handlers() first.")
    return _database_client


def error_response(code: str, message: str) -> Dict[str, Any]:
    """Create a standardized error response."""
    return {"error": {"code": code, "message": message}, "result": None}


def success_response(result: Any) -> Dict[str, Any]:
    """Create a standardized success response."""
    return {"error": None, "result": result}


def handle_match_assets_for_group(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Match indexed assets to an asset group.

    Request format:
    {
        "method": "match_assets_for_group",
        "params": {
            "template_id": "youtube-interview",
            "group_name": "intro_music",
            "limit": 5,
            "min_score": 0.5
        },
        "id": "req_001"
    }

    Response format:
    {
        "result": {
            "group_name": "intro_music",
            "matches": [...],
            "total_matches": 12,
            "returned": 5
        },
        "error": null,
        "id": "req_001"
    }
    """
    try:
        template_id = params.get("template_id")
        group_name = params.get("group_name")
        limit = params.get("limit", 5)
        min_score = params.get("min_score", 0.5)

        if not template_id or not group_name:
            return error_response(
                "INVALID_PARAMS", "template_id and group_name are required"
            )
        
        # Validate limit parameter
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            return error_response(
                "INVALID_PARAMS", "limit must be an integer between 1 and 100"
            )
        
        # Validate min_score parameter  
        if not isinstance(min_score, (int, float)) or min_score < 0.0 or min_score > 1.0:
            return error_response(
                "INVALID_PARAMS", "min_score must be a number between 0.0 and 1.0"
            )

        # Load template and find asset group
        cache = get_template_cache()
        template = cache.get(template_id)

        if not template:
            return error_response(
                "TEMPLATE_NOT_FOUND", f"Template {template_id} not found"
            )

        # Get asset_groups from template
        asset_groups = getattr(template, "asset_groups", [])
        if not asset_groups:
            return error_response(
                "NO_ASSET_GROUPS", f"Template {template_id} has no asset groups defined"
            )

        asset_group = next(
            (g for g in asset_groups if isinstance(g, AssetGroup) and g.name == group_name),
            None,
        )

        if not asset_group:
            return error_response(
                "GROUP_NOT_FOUND",
                f"Asset group {group_name} not found in template",
            )

        # Perform matching
        matcher = AssetMatcher(get_database_client())
        matches = matcher.match_assets_for_group(
            asset_group, limit=limit, min_score=min_score
        )

        return success_response(
            {
                "group_name": group_name,
                "matches": [m.to_dict() for m in matches],
                "total_matches": len(matches),
                "returned": len(matches),
            }
        )

    except Exception as e:
        logger.exception("Error matching assets for group")
        return error_response("MATCHING_FAILED", str(e))


def handle_match_all_groups(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Match assets for all groups in a template.

    Request format:
    {
        "method": "match_all_groups",
        "params": {
            "template_id": "youtube-interview",
            "limit_per_group": 3
        }
    }
    """
    try:
        template_id = params.get("template_id")
        limit_per_group = params.get("limit_per_group", 3)

        if not template_id:
            return error_response("INVALID_PARAMS", "template_id is required")
        
        # Validate limit_per_group parameter
        if not isinstance(limit_per_group, int) or limit_per_group < 1 or limit_per_group > 100:
            return error_response(
                "INVALID_PARAMS", "limit_per_group must be an integer between 1 and 100"
            )

        cache = get_template_cache()
        template = cache.get(template_id)

        if not template:
            return error_response(
                "TEMPLATE_NOT_FOUND", f"Template {template_id} not found"
            )

        # Get asset_groups from template
        asset_groups = getattr(template, "asset_groups", [])
        if not asset_groups:
            return error_response(
                "NO_ASSET_GROUPS", f"Template {template_id} has no asset groups defined"
            )

        matcher = AssetMatcher(get_database_client())
        all_matches = matcher.match_all_groups(
            [g for g in asset_groups if isinstance(g, AssetGroup)],
            limit_per_group=limit_per_group,
        )

        # Convert to serializable format
        result: Dict[str, List[Dict[str, Any]]] = {}
        for group_name, matches in all_matches.items():
            result[group_name] = [m.to_dict() for m in matches]

        return success_response(
            {
                "template_id": template_id,
                "groups": result,
                "total_groups": len(result),
            }
        )

    except Exception as e:
        logger.exception("Error matching all groups")
        return error_response("MATCHING_FAILED", str(e))


def handle_get_template_preview(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get template preview including asset groups.

    Request format:
    {
        "method": "get_template_preview",
        "params": {
            "template_id": "youtube-interview"
        }
    }
    """
    try:
        template_id = params.get("template_id")

        if not template_id:
            return error_response("INVALID_PARAMS", "template_id is required")

        cache = get_template_cache()
        template = cache.get(template_id)

        if not template:
            return error_response(
                "TEMPLATE_NOT_FOUND", f"Template {template_id} not found"
            )

        # Build preview response
        preview = {
            "template_id": template_id,
            "name": getattr(template, "name", template_id),
            "description": getattr(template, "description", ""),
        }

        # Add asset groups if available
        asset_groups = getattr(template, "asset_groups", [])
        if asset_groups:
            preview["asset_groups"] = [
                g.to_dict() for g in asset_groups if isinstance(g, AssetGroup)
            ]

        return success_response(preview)

    except Exception as e:
        logger.exception("Error getting template preview")
        return error_response("PREVIEW_FAILED", str(e))
