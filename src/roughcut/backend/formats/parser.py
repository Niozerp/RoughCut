"""Asset group parsing from template YAML definitions."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Union

import yaml

from .models import AssetGroup, AssetGroupCategory, AssetGroupParseError, AssetGroupPriority, DurationHint
from .validators import AssetGroupValidator

logger = logging.getLogger(__name__)


class AssetGroupParser:
    """Parses asset group definitions from template YAML."""

    REQUIRED_FIELDS = ["description", "tags"]

    def __init__(self) -> None:
        self.validator = AssetGroupValidator()

    def parse_yaml_block(self, yaml_content: str) -> List[AssetGroup]:
        """
        Parse asset groups from YAML code block content.

        Args:
            yaml_content: Raw YAML string from template markdown

        Returns:
            List of AssetGroup objects

        Raises:
            AssetGroupParseError: If YAML is invalid
        """
        try:
            data = yaml.safe_load(yaml_content)

            if not isinstance(data, dict):
                raise AssetGroupParseError("Asset groups must be a YAML dictionary")

            groups: List[AssetGroup] = []
            for group_name, group_def in data.items():
                try:
                    if not isinstance(group_def, dict):
                        logger.warning(
                            f"Skipping invalid asset group '{group_name}': "
                            "definition must be a dictionary"
                        )
                        continue
                    group = self._parse_single_group(group_name, group_def)
                    groups.append(group)
                except (ValueError, KeyError) as e:
                    # Log error but continue with other groups
                    logger.warning(
                        f"Skipping invalid asset group '{group_name}': {e}"
                    )
                    continue

            return groups

        except yaml.YAMLError as e:
            raise AssetGroupParseError(f"Invalid YAML in asset groups: {e}")

    def _parse_single_group(self, name: str, definition: Dict[str, Any]) -> AssetGroup:
        """Parse a single asset group definition."""
        # Handle None name gracefully
        if name is None:
            raise ValueError("Group name cannot be None")
        
        # Validate required fields present
        self.validator.validate_definition(name, definition)

        # Parse category with error handling
        category_str = definition.get("category", self._infer_category(name))
        if category_str is None:
            category_str = "music"
        try:
            category = AssetGroupCategory(category_str.lower())
        except ValueError:
            valid_categories = [c.value for c in AssetGroupCategory]
            raise ValueError(
                f"Invalid category '{category_str}' for group '{name}'. "
                f"Valid categories: {valid_categories}"
            )

        # Parse tags (can be string or list)
        tags = definition.get("tags", [])
        if isinstance(tags, str):
            # Handle comma-separated string with robust whitespace handling
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        elif not isinstance(tags, list):
            tags = []

        # Split into required and optional
        required_tags = definition.get("required_tags", tags)
        if isinstance(required_tags, str):
            required_tags = [t.strip() for t in required_tags.split(",") if t.strip()]
        elif not isinstance(required_tags, list):
            required_tags = []
            
        optional_tags = definition.get("optional_tags", [])
        if isinstance(optional_tags, str):
            optional_tags = [t.strip() for t in optional_tags.split(",") if t.strip()]
        elif not isinstance(optional_tags, list):
            optional_tags = []
        
        # Validate we have at least one tag
        if not required_tags and not optional_tags:
            raise ValueError(f"Asset group '{name}' must have at least one tag (required or optional)")

        # Parse duration hint
        duration_hint = None
        if "duration" in definition:
            duration_hint = self._parse_duration(definition["duration"])
        elif "duration_hint" in definition:
            duration_hint = self._parse_duration(definition["duration_hint"])
        
        # Parse priority
        priority = definition.get("priority", "medium")
        if isinstance(priority, str):
            try:
                priority = AssetGroupPriority(priority.lower())
            except ValueError:
                logger.warning(f"Invalid priority '{priority}' for group '{name}', defaulting to 'medium'")
                priority = AssetGroupPriority.MEDIUM

        return AssetGroup(
            name=name,
            description=definition["description"],
            category=category,
            required_tags=required_tags,
            optional_tags=optional_tags,
            duration_hint=duration_hint,
            priority=priority,
            fallback_groups=definition.get("fallback_groups", []),
        )

    def _infer_category(self, name: str) -> str:
        """Infer category from group name heuristics."""
        if name is None:
            return "music"
        
        name_lower = str(name).lower()
        if "music" in name_lower or "track" in name_lower or "bed" in name_lower:
            return "music"
        elif "sfx" in name_lower or "sound" in name_lower or "chime" in name_lower:
            return "sfx"
        elif "vfx" in name_lower or "effect" in name_lower or "lower_third" in name_lower:
            return "vfx"
        elif "transition" in name_lower or "wipe" in name_lower:
            return "transition"
        return "music"  # Default

    def _parse_duration(self, duration_def: Union[str, Dict[str, Any]]) -> DurationHint:
        """Parse duration specification."""
        if isinstance(duration_def, str):
            # Single duration string: "0:15" or "15"
            return DurationHint(exact=duration_def)
        elif isinstance(duration_def, dict):
            # Dictionary with exact/min/max/flexible
            return DurationHint(
                exact=duration_def.get("exact"),
                min_duration=duration_def.get("min"),
                max_duration=duration_def.get("max"),
                flexible=duration_def.get("flexible", True),
            )
        else:
            raise AssetGroupParseError(f"Invalid duration format: {duration_def}")
