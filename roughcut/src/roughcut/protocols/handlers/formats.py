"""Protocol handlers for format template operations.

Handles JSON-RPC requests for format template discovery and retrieval.
"""

from pathlib import Path
from typing import Any, Dict, List

from ...backend.formats import TemplateScanner


def get_available_formats(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for get_available_formats method.
    
    Scans the templates/formats/ directory and returns list of
    available format templates with metadata.
    
    Args:
        params: Request parameters (currently unused)
        
    Returns:
        Dictionary with "formats" key containing list of template metadata
        or error response if scanning fails
    """
    try:
        # Determine templates directory path
        # Look relative to project root (where pyproject.toml exists)
        templates_dir = _find_templates_directory()
        
        # Create scanner and scan for templates
        scanner = TemplateScanner(templates_dir)
        templates = scanner.scan()
        
        # Convert templates to list of dictionaries
        formats_list = [t.to_dict() for t in templates]
        
        return {
            "formats": formats_list
        }
        
    except Exception as e:
        return {
            "error": {
                "code": "FORMAT_SCAN_ERROR",
                "category": "internal",
                "message": f"Failed to scan format templates: {str(e)}",
                "suggestion": "Check that templates/formats/ directory exists and is readable"
            }
        }


def _find_templates_directory() -> Path:
    """Find the templates/formats/ directory.
    
    Searches for the directory relative to project root.
    
    Returns:
        Path to templates/formats/ directory
        
    Raises:
        FileNotFoundError: If directory cannot be found
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
                templates_dir.mkdir(parents=True, exist_ok=True)
            return templates_dir
        
        # Move up one directory
        parent = search_dir.parent
        if parent == search_dir:
            break
        search_dir = parent
    
    # Fallback: create in current working directory
    fallback_dir = Path("templates/formats").resolve()
    fallback_dir.mkdir(parents=True, exist_ok=True)
    return fallback_dir


# Handler registry
FORMAT_HANDLERS = {
    "get_available_formats": get_available_formats,
}
