"""Asset group validation utilities."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Tuple

from .models import AssetGroupCategory, AssetGroupParseError

logger = logging.getLogger(__name__)


class AssetGroupValidator:
    """Validates asset group definitions."""

    # Valid tag pattern: lowercase, no spaces, underscores allowed
    TAG_PATTERN = re.compile(r"^[a-z0-9_]+$")

    # Valid duration pattern: mm:ss or seconds
    DURATION_PATTERN = re.compile(r"^(\d+:)?\d+$")

    # Valid priority values
    VALID_PRIORITIES = {"high", "medium", "low"}

    def validate_definition(self, name: str, definition: Dict[str, Any]) -> None:
        """
        Validate an asset group definition.

        Args:
            name: The group name
            definition: The group definition dictionary

        Raises:
            KeyError: If required fields are missing
            ValueError: If field values are invalid
        """
        # Check required fields
        if "description" not in definition:
            raise KeyError(f"Missing required field 'description' for group '{name}'")

        if "tags" not in definition and "required_tags" not in definition:
            raise KeyError(
                f"Missing required field 'tags' or 'required_tags' for group '{name}'"
            )

        # Validate description
        description = definition.get("description", "")
        if not description or not str(description).strip():
            raise ValueError(f"Description cannot be empty for group '{name}'")

        # Validate category if provided
        if "category" in definition:
            category = definition["category"]
            try:
                AssetGroupCategory(category.lower())
            except ValueError:
                valid_categories = [c.value for c in AssetGroupCategory]
                raise ValueError(
                    f"Invalid category '{category}' for group '{name}'. "
                    f"Valid categories: {valid_categories}"
                )

        # Validate tags
        self._validate_tags(name, definition)

        # Validate duration if provided
        if "duration" in definition or "duration_hint" in definition:
            duration = definition.get("duration") or definition.get("duration_hint")
            self._validate_duration(name, duration)

        # Validate priority if provided
        if "priority" in definition:
            priority = definition["priority"]
            if priority not in self.VALID_PRIORITIES:
                raise ValueError(
                    f"Invalid priority '{priority}' for group '{name}'. "
                    f"Valid values: {self.VALID_PRIORITIES}"
                )

    def _validate_tags(self, group_name: str, definition: Dict[str, Any]) -> None:
        """Validate tag format for all tag fields."""
        tag_fields = ["tags", "required_tags", "optional_tags"]

        for field in tag_fields:
            if field not in definition:
                continue

            tags = definition[field]
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]

            if not isinstance(tags, list):
                raise ValueError(
                    f"Field '{field}' for group '{group_name}' must be a list or comma-separated string"
                )

            for tag in tags:
                tag_str = str(tag).lower().strip()
                if not tag_str:
                    continue

                if not self.TAG_PATTERN.match(tag_str):
                    raise ValueError(
                        f"Invalid tag format '{tag}' in field '{field}' for group '{group_name}'. "
                        f"Tags must be lowercase, alphanumeric with underscores only."
                    )

    def _validate_duration(self, group_name: str, duration: Any) -> None:
        """Validate duration format."""
        if isinstance(duration, str):
            if not self.DURATION_PATTERN.match(duration):
                raise ValueError(
                    f"Invalid duration format '{duration}' for group '{group_name}'. "
                    f"Use 'mm:ss' format (e.g., '0:15') or seconds (e.g., '15')."
                )
        elif isinstance(duration, dict):
            # Validate dict format with exact/min/max keys
            valid_keys = {"exact", "min", "max", "flexible"}
            for key in duration.keys():
                if key not in valid_keys:
                    raise ValueError(
                        f"Invalid duration key '{key}' for group '{group_name}'. "
                        f"Valid keys: {valid_keys}"
                    )

            for key in ["exact", "min", "max"]:
                if key in duration and duration[key]:
                    if not self.DURATION_PATTERN.match(str(duration[key])):
                        raise ValueError(
                            f"Invalid duration format '{duration[key]}' for key '{key}' "
                            f"in group '{group_name}'. Use 'mm:ss' or seconds."
                        )
        else:
            raise ValueError(
                f"Duration for group '{group_name}' must be a string or dictionary"
            )

    def validate_complete(self, groups: List[Any]) -> Tuple[bool, List[str]]:
        """
        Validate a complete list of asset groups.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors: List[str] = []

        # Check for duplicate names
        names = []
        for group in groups:
            if hasattr(group, "name"):
                names.append(group.name)

        seen = set()
        for name in names:
            if name in seen:
                errors.append(f"Duplicate asset group name: '{name}'")
            seen.add(name)

        # Validate each group
        for group in groups:
            if hasattr(group, "validate"):
                try:
                    group.validate()
                except ValueError as e:
                    errors.append(str(e))

        return len(errors) == 0, errors
