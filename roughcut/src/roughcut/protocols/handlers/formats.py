"""Protocol handlers for format template operations.

Handles JSON-RPC requests for format template discovery and retrieval.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List

from ...backend.formats import TemplateScanner
from ...backend.formats.parser import TemplateParser

logger = logging.getLogger(__name__)

# Error codes for consistent error handling
ERROR_CODES = {
    "FORMAT_SCAN_ERROR": "FORMAT_SCAN_ERROR",
    "INVALID_PARAMS": "INVALID_PARAMS",
    "DIRECTORY_NOT_FOUND": "DIRECTORY_NOT_FOUND",
    "PERMISSION_DENIED": "PERMISSION_DENIED",
    "TEMPLATE_NOT_FOUND": "TEMPLATE_NOT_FOUND",
    "TEMPLATE_PARSE_ERROR": "TEMPLATE_PARSE_ERROR"
}


def get_available_formats(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Handler for get_available_formats method.
    
    Scans the templates/formats/ directory and returns list of
    available format templates with metadata.
    
    Args:
        params: Request parameters (currently unused, validated for safety)
        
    Returns:
        Dictionary with "formats" key containing list of template metadata
        or error response if scanning fails
    """
    # Validate params
    if params is None:
        params = {}
    
    # Check for unexpected params that might indicate misuse
    if not isinstance(params, dict):
        logger.warning(f"Invalid params type: {type(params)}")
        return {
            "error": {
                "code": ERROR_CODES["INVALID_PARAMS"],
                "category": "validation",
                "message": "Invalid parameters: expected object",
                "suggestion": "Check request format"
            }
        }
    
    try:
        # Determine templates directory path
        templates_dir = _find_templates_directory()
        
        # Create scanner and scan for templates
        scanner = TemplateScanner(templates_dir)
        templates = scanner.scan()
        
        # Convert templates to list of dictionaries
        formats_list = []
        for t in templates:
            try:
                formats_list.append(t.to_dict())
            except Exception as e:
                logger.warning(f"Failed to convert template to dict: {e}")
                continue
        
        return {
            "formats": formats_list
        }
        
    except PermissionError as e:
        logger.error(f"Permission denied accessing templates: {e}")
        return {
            "error": {
                "code": ERROR_CODES["PERMISSION_DENIED"],
                "category": "filesystem",
                "message": f"Permission denied: {str(e)}",
                "suggestion": "Check directory permissions for templates/formats/"
            }
        }
    except FileNotFoundError as e:
        logger.error(f"Templates directory not found: {e}")
        return {
            "error": {
                "code": ERROR_CODES["DIRECTORY_NOT_FOUND"],
                "category": "filesystem",
                "message": f"Templates directory not found: {str(e)}",
                "suggestion": "Ensure templates/formats/ directory exists"
            }
        }
    except Exception as e:
        logger.exception(f"Unexpected error scanning format templates: {e}")
        return {
            "error": {
                "code": ERROR_CODES["FORMAT_SCAN_ERROR"],
                "category": "internal",
                "message": f"Failed to scan format templates: {str(e)}",
                "suggestion": "Check that templates/formats/ directory exists and is readable"
            }
        }


def get_template_preview(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Handler for get_template_preview method.
    
    Loads a specific template file and returns full preview details
    including structure, timing segments, and asset groups.
    
    Args:
        params: Request parameters containing:
            - template_id: The template slug to preview (required)
        
    Returns:
        Dictionary with "preview" key containing full template details
        or error response if loading fails
    """
    # Validate params
    if params is None:
        params = {}
    
    if not isinstance(params, dict):
        logger.warning(f"Invalid params type: {type(params)}")
        return {
            "error": {
                "code": ERROR_CODES["INVALID_PARAMS"],
                "category": "validation",
                "message": "Invalid parameters: expected object",
                "suggestion": "Check request format"
            }
        }
    
    # Extract template_id
    template_id = params.get("template_id")
    if not template_id or not isinstance(template_id, str):
        return {
            "error": {
                "code": ERROR_CODES["INVALID_PARAMS"],
                "category": "validation",
                "message": "Missing required parameter: template_id",
                "suggestion": "Provide a template_id string in the params object"
            }
        }
    
    try:
        # Sanitize template_id to prevent path traversal
        sanitized_id = _sanitize_template_id(template_id)
        if not sanitized_id:
            return {
                "error": {
                    "code": ERROR_CODES["INVALID_PARAMS"],
                    "category": "validation",
                    "message": f"Invalid template_id: '{template_id}'",
                    "suggestion": "Template ID should be alphanumeric with dashes"
                }
            }
        
        # Find templates directory
        templates_dir = _find_templates_directory()
        
        # Construct template file path
        template_file = templates_dir / f"{sanitized_id}.md"
        
        # Check if file exists
        if not template_file.exists():
            logger.warning(f"Template not found: {template_file}")
            return {
                "error": {
                    "code": ERROR_CODES["TEMPLATE_NOT_FOUND"],
                    "category": "not_found",
                    "message": f"Template '{template_id}' not found",
                    "suggestion": "Check that the template file exists in templates/formats/"
                }
            }
        
        # Parse the template file with full structure
        parser = TemplateParser()
        template = parser.parse_file(template_file)
        
        if template is None:
            return {
                "error": {
                    "code": ERROR_CODES["TEMPLATE_PARSE_ERROR"],
                    "category": "parse_error",
                    "message": f"Failed to parse template '{template_id}'",
                    "suggestion": "Template file may be malformed or missing required fields"
                }
            }
        
        # Return preview data
        return {
            "preview": template.to_preview_dict()
        }
        
    except PermissionError as e:
        logger.error(f"Permission denied accessing template: {e}")
        return {
            "error": {
                "code": ERROR_CODES["PERMISSION_DENIED"],
                "category": "filesystem",
                "message": f"Permission denied: {str(e)}",
                "suggestion": "Check file permissions for the template"
            }
        }
    except Exception as e:
        logger.exception(f"Unexpected error loading template preview: {e}")
        return {
            "error": {
                "code": ERROR_CODES["TEMPLATE_PARSE_ERROR"],
                "category": "internal",
                "message": f"Failed to load template preview: {str(e)}",
                "suggestion": "Check that the template file is readable and properly formatted"
            }
        }


def _sanitize_template_id(template_id: str) -> str:
    """Sanitize template ID to prevent path traversal attacks.
    
    Args:
        template_id: Raw template ID from request
        
    Returns:
        Sanitized template ID or empty string if invalid
    """
    if not template_id:
        return ""
    
    # Enforce maximum length (255 chars for most filesystems)
    if len(template_id) > 255:
        return ""
    
    # Block single dot (hidden files) and double dots (path traversal)
    if template_id == "." or template_id == "..":
        return ""
    
    # Use allowlist approach: only allow alphanumeric, dashes, and underscores
    # This is more secure than sequential replace which can be bypassed
    if not re.match(r'^[\w\-]+$', template_id):
        return ""
    
    # Additional check: reject if result is all dots or empty after basic filtering
    sanitized = template_id.strip()
    if not sanitized or all(c == '.' for c in sanitized):
        return ""
    
    return sanitized


def _find_templates_directory() -> Path:
    """Find the templates/formats/ directory.
    
    Searches for the directory relative to project root.
    
    Returns:
        Path to templates/formats/ directory
        
    Raises:
        FileNotFoundError: If directory cannot be found or created
        PermissionError: If directory creation fails due to permissions
    """
    # Start from current file location and work up
    current_file = Path(__file__).resolve()
    
    # Navigate up to find project root (where src/roughcut exists)
    search_dir = current_file.parent
    for _ in range(5):  # Limit search depth
        # Check for templates/formats/ at this level
        templates_dir = search_dir / "templates" / "formats"
        if templates_dir.exists():
            return templates_dir
        
        # Check if we're at project root (has pyproject.toml or similar)
        if (search_dir / "pyproject.toml").exists():
            # Found project root, check for templates
            templates_dir = search_dir / "templates" / "formats"
            if not templates_dir.exists():
                # Create if missing
                try:
                    templates_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created templates directory: {templates_dir}")
                except PermissionError as e:
                    logger.error(f"Permission denied creating templates directory: {e}")
                    raise PermissionError(f"Cannot create templates directory: {e}")
            return templates_dir
        
        # Move up one directory
        parent = search_dir.parent
        if parent == search_dir:
            break
        search_dir = parent
    
    # Fallback: create in current working directory
    fallback_dir = Path("templates/formats").resolve()
    try:
        fallback_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using fallback templates directory: {fallback_dir}")
    except PermissionError as e:
        logger.error(f"Permission denied creating fallback templates directory: {e}")
        raise PermissionError(f"Cannot create fallback templates directory: {e}")
    
    if not fallback_dir.exists():
        raise FileNotFoundError(f"Failed to create templates directory: {fallback_dir}")
    
    return fallback_dir


# Handler registry
FORMAT_HANDLERS = {
    "get_available_formats": get_available_formats,
    "get_template_preview": get_template_preview,
}
