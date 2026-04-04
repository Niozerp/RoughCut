"""Protocol handlers for media folder configuration and indexing.

Provides JSON-RPC handlers for Lua-Python communication
for media folder configuration operations and incremental indexing.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path

from ...config.settings import ConfigManager
from ...config.models import MediaFolderConfig
from ...backend.indexing import MediaIndexer, FileScanner
from ...backend.database.models import MediaAsset, IndexResult

# Valid media categories
VALID_CATEGORIES = {'music', 'sfx', 'vfx', 'folder'}

# Maximum allowed path length (common filesystem limit)
MAX_PATH_LENGTH = 4096

# Global indexer instance
_indexer: Optional[MediaIndexer] = None
_event_loop: Optional[asyncio.AbstractEventLoop] = None


# Set up logger
logger = logging.getLogger(__name__)

# Valid media categories
VALID_CATEGORIES = {'music', 'sfx', 'vfx', 'folder'}

# Maximum allowed path length (common filesystem limit)
MAX_PATH_LENGTH = 4096

# Global indexer instance
_indexer: Optional[MediaIndexer] = None
_event_loop: Optional[asyncio.AbstractEventLoop] = None


def _get_indexer() -> MediaIndexer:
    """Get or create the global indexer instance."""
    global _indexer
    if _indexer is None:
        _indexer = MediaIndexer()
    return _indexer


def _get_event_loop() -> asyncio.AbstractEventLoop:
    """Get or create the global event loop for async operations."""
    global _event_loop
    if _event_loop is None or _event_loop.is_closed():
        _event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_event_loop)
    return _event_loop


def _validate_params_type(params) -> tuple[bool, dict]:
    """Validate that params is a dictionary.
    
    Args:
        params: The params value from the request
        
    Returns:
        Tuple of (is_valid, error_response). When is_valid is True, 
        error_response is an empty dict. When is_valid is False, 
        error_response contains the error details.
    """
    if not isinstance(params, dict):
        return False, {
            'error': {
                'code': 'INVALID_PARAMS',
                'category': 'validation',
                'message': 'Params must be a JSON object',
                'suggestion': 'Provide a JSON object with folder paths as keys'
            }
        }
    return True, {}


def get_media_folders(params: dict) -> dict:
    """Handle get_media_folders request.
    
    Returns current media folders configuration.
    
    Request format: {"method": "get_media_folders", "params": {}, "id": "..."}
    Response format: {
        "music_folder": str or None,
        "sfx_folder": str or None,
        "vfx_folder": str or None,
        "configured": bool,
        "last_updated": str or None
    }
    
    Args:
        params: Request parameters (unused)
        
    Returns:
        Response dictionary with folder configuration
    """
    # Validate params type
    is_valid, error_response = _validate_params_type(params)
    if not is_valid:
        return error_response
    
    try:
        config_manager = ConfigManager()
        config = config_manager.get_media_folders_config()
        
        return {
            'music_folder': config.music_folder,
            'sfx_folder': config.sfx_folder,
            'vfx_folder': config.vfx_folder,
            'configured': config.is_configured(),
            'last_updated': config.last_updated.isoformat() if config.last_updated else None
        }
    except Exception as e:
        return {
            'error': {
                'code': 'CONFIG_LOAD_ERROR',
                'category': 'internal',
                'message': str(e),
                'suggestion': 'Check configuration file permissions'
            }
        }


def save_media_folders(params: dict) -> dict:
    """Handle save_media_folders request.
    
    Saves media folders configuration after validation.
    
    Request format: {
        "method": "save_media_folders",
        "params": {
            "music_folder": "/path/to/music",
            "sfx_folder": "/path/to/sfx",
            "vfx_folder": "/path/to/vfx"
        },
        "id": "..."
    }
    
    Args:
        params: Request parameters containing:
            - music_folder: Path to Music assets folder (optional)
            - sfx_folder: Path to SFX assets folder (optional)
            - vfx_folder: Path to VFX assets folder (optional)
            
    Returns:
        Response dictionary with success status
    """
    # Validate params type
    is_valid, error_response = _validate_params_type(params)
    if not is_valid:
        return error_response
    
    try:
        music_folder = params.get('music_folder')
        sfx_folder = params.get('sfx_folder')
        vfx_folder = params.get('vfx_folder')
        
        config_manager = ConfigManager()
        success, message, errors = config_manager.save_media_folders_config(
            music_folder=music_folder,
            sfx_folder=sfx_folder,
            vfx_folder=vfx_folder
        )
        
        if success:
            return {
                'success': True,
                'message': message,
                'configured': True
            }
        else:
            # Build error response with optional validation details
            error_response: dict = {
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'category': 'validation',
                    'message': message,
                    'suggestion': 'Check that all folder paths exist and are absolute paths'
                }
            }
            
            # Include per-category errors if available
            if errors:
                error_response['error']['details'] = errors
            
            return error_response
            
    except Exception as e:
        return {
            'error': {
                'code': 'CONFIG_SAVE_ERROR',
                'category': 'internal',
                'message': str(e),
                'suggestion': 'Ensure configuration directory is writable'
            }
        }


def clear_media_folders(params: dict) -> dict:
    """Handle clear_media_folders request.
    
    Removes media folders configuration from storage.
    
    Request format: {"method": "clear_media_folders", "params": {}, "id": "..."}
    
    Args:
        params: Request parameters (unused)
        
    Returns:
        Response dictionary with success status
    """
    # Validate params type (accepts empty dict)
    is_valid, error_response = _validate_params_type(params)
    if not is_valid:
        return error_response
    
    try:
        config_manager = ConfigManager()
        success, message = config_manager.clear_media_folders_config()
        
        if success:
            return {
                'success': True,
                'message': message,
                'configured': False
            }
        else:
            return {
                'error': {
                    'code': 'CONFIG_CLEAR_ERROR',
                    'category': 'internal',
                    'message': message,
                    'suggestion': 'Check file permissions'
                }
            }
    except Exception as e:
        return {
            'error': {
                'code': 'CONFIG_CLEAR_ERROR',
                'category': 'internal',
                'message': str(e),
                'suggestion': 'Check file permissions'
            }
        }


def check_media_folders_configured(params: dict) -> dict:
    """Handle check_media_folders_configured request.
    
    Quick check to determine if media folders are configured.
    Used for graceful degradation and UI state management.
    
    Request format: {"method": "check_media_folders_configured", "params": {}, "id": "..."}
    
    Args:
        params: Request parameters (unused)
        
    Returns:
        Response dictionary with configured status
    """
    # Validate params type (accepts empty dict)
    is_valid, error_response = _validate_params_type(params)
    if not is_valid:
        return error_response
    
    try:
        config_manager = ConfigManager()
        is_configured = config_manager.is_media_folders_configured()
        
        # Also return which folders are configured
        config = config_manager.get_media_folders_config()
        
        return {
            'configured': is_configured,
            'folders': {
                'music': config.music_folder is not None and len(config.music_folder) > 0,
                'sfx': config.sfx_folder is not None and len(config.sfx_folder) > 0,
                'vfx': config.vfx_folder is not None and len(config.vfx_folder) > 0
            }
        }
    except Exception as e:
        return {
            'configured': False,
            'error': {
                'code': 'CONFIG_CHECK_ERROR',
                'category': 'internal',
                'message': str(e),
                'suggestion': 'Configuration check failed, assuming not configured'
            }
        }


def validate_folder_path(params: dict) -> dict:
    """Handle validate_folder_path request.
    
    Validates a single folder path without saving.
    Used for real-time validation in the UI.
    
    Request format: {
        "method": "validate_folder_path",
        "params": {
            "path": "/path/to/folder",
            "category": "music"
        },
        "id": "..."
    }
    
    Args:
        params: Request parameters containing:
            - path: Folder path to validate
            - category: Category name (for error messages)
            
    Returns:
        Response dictionary with validation result
    """
    # Validate params type
    is_valid, error_response = _validate_params_type(params)
    if not is_valid:
        return error_response
    
    try:
        from pathlib import Path
        
        path_str = params.get('path', '')
        category = params.get('category', 'folder')
        
        # Validate category is one of the allowed values
        category_lower = category.lower()
        if category_lower not in VALID_CATEGORIES:
            return {
                'valid': False,
                'error': f'Invalid category: {category}',
                'suggestion': f'Use one of: {", ".join(sorted(VALID_CATEGORIES))}'
            }
        
        # Validate path length
        if len(path_str) > MAX_PATH_LENGTH:
            return {
                'valid': False,
                'error': f'Path is too long ({len(path_str)} characters, max {MAX_PATH_LENGTH})',
                'suggestion': 'Use a shorter path or create a symbolic link'
            }
        
        # Check for null bytes
        if '\x00' in path_str:
            return {
                'valid': False,
                'error': 'Path contains invalid null characters',
                'suggestion': 'Remove null bytes from the path'
            }
        
        if not path_str or not path_str.strip():
            return {
                'valid': False,
                'error': f'{category.capitalize()} path is required',
                'suggestion': 'Please select a folder path'
            }
        
        try:
            path = Path(path_str.strip())
            
            if not path.exists():
                return {
                    'valid': False,
                    'error': f'Path does not exist: {path}',
                    'suggestion': 'Please select an existing directory'
                }
            
            if not path.is_dir():
                return {
                    'valid': False,
                    'error': f'Path is not a directory: {path}',
                    'suggestion': 'Please select a directory, not a file'
                }
            
            if not path.is_absolute():
                return {
                    'valid': False,
                    'error': f'Path must be absolute: {path}',
                    'suggestion': 'Please use the folder browser to select an absolute path'
                }
            
            # All validations passed
            return {
                'valid': True,
                'absolute_path': str(path.resolve()),
                'message': f'{category.capitalize()} folder is valid'
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Invalid path format: {str(e)}',
                'suggestion': 'Please enter a valid folder path'
            }
            
    except Exception as e:
        return {
            'valid': False,
            'error': str(e),
            'suggestion': 'An unexpected error occurred during validation'
        }


def index_media(params: dict) -> dict:
    """Handle index_media request.
    
    Initiates incremental media indexing with progress streaming.
    
    Request format: {
        "method": "index_media",
        "params": {
            "incremental": true,
            "categories": ["music", "sfx", "vfx"]
        },
        "id": "..."
    }
    
    Args:
        params: Request parameters containing:
            - incremental: Whether to do incremental scan (default: true)
            - categories: List of categories to index (optional)
            
    Returns:
        Response dictionary with indexing result
    """
    # Validate params type
    is_valid, error_response = _validate_params_type(params)
    if not is_valid:
        return error_response
    
    config_manager = ConfigManager()
    
    # Check if media folders are configured
    if not config_manager.is_media_folders_configured():
        return {
            'error': {
                'code': 'NOT_CONFIGURED',
                'category': 'configuration',
                'message': 'Media folders are not configured',
                'suggestion': 'Configure media folders before indexing'
            }
        }
    
    folder_config = config_manager.get_media_folders_config()
    incremental = params.get('incremental', True)
    categories = params.get('categories', ['music', 'sfx', 'vfx'])
    
    # Get the indexer instance
    indexer = _get_indexer()
    
    # Create a scanner filtered by categories if specified
    if categories:
        indexer.file_scanner = FileScanner(categories=categories)
    
    # Run indexing (async operation in sync context)
    loop = _get_event_loop()
    
    try:
        # Reset cancellation state before starting
        indexer.reset_cancellation()
        
        # Load cached assets from in-memory storage (Story 2.5: will load from SpacetimeDB)
        cached_assets: List[MediaAsset] = list(indexer._assets.values())
        
        result = loop.run_until_complete(
            indexer.index_media(
                folder_configs=folder_config,
                cached_assets=cached_assets,
                incremental=incremental
            )
        )
        
        return {
            'success': True,
            'result': result.to_dict()
        }
    except Exception as e:
        return {
            'error': {
                'code': 'INDEXING_ERROR',
                'category': 'internal',
                'message': str(e),
                'suggestion': 'Check folder permissions and disk space'
            }
        }


def get_index_status(params: dict) -> dict:
    """Handle get_index_status request.
    
    Returns the current indexing state and statistics.
    
    Request format: {"method": "get_index_status", "params": {}, "id": "..."}
    
    Args:
        params: Request parameters (unused)
        
    Returns:
        Response dictionary with index status
    """
    # Validate params type
    is_valid, error_response = _validate_params_type(params)
    if not is_valid:
        return error_response
    
    try:
        indexer = _get_indexer()
        index_state = indexer.get_index_state()
        
        return {
            'last_index_time': index_state.last_index_time.isoformat() if index_state.last_index_time else None,
            'total_assets_indexed': index_state.total_assets_indexed,
            'folder_configs': index_state.folder_configs,
            'index_version': index_state.index_version
        }
    except Exception as e:
        return {
            'error': {
                'code': 'STATUS_ERROR',
                'category': 'internal',
                'message': str(e),
                'suggestion': 'Try resetting the indexer'
            }
        }


def cancel_indexing(params: dict) -> dict:
    """Handle cancel_indexing request.
    
    Cancels an in-progress indexing operation.
    
    Request format: {"method": "cancel_indexing", "params": {}, "id": "..."}
    
    Args:
        params: Request parameters (unused)
        
    Returns:
        Response dictionary with cancellation result
    """
    # Validate params type
    is_valid, error_response = _validate_params_type(params)
    if not is_valid:
        return error_response
    
    try:
        indexer = _get_indexer()
        indexer.cancel()
        
        return {
            'success': True,
            'message': 'Indexing cancellation requested'
        }
    except Exception as e:
        return {
            'success': False,
            'error': {
                'code': 'CANCEL_ERROR',
                'category': 'internal',
                'message': str(e),
                'suggestion': 'Indexing may not be in progress'
            }
        }


def _coerce_bool(value: Any, default: bool = True) -> bool:
    """Coerce a value to boolean, handling string representations.
    
    Args:
        value: Value to coerce
        default: Default if value is None
        
    Returns:
        Boolean representation of the value
        
    Examples:
        >>> _coerce_bool(True)
        True
        >>> _coerce_bool(False)
        False
        >>> _coerce_bool("false")
        False
        >>> _coerce_bool("False")
        False
        >>> _coerce_bool("0")
        False
        >>> _coerce_bool(0)
        False
        >>> _coerce_bool(None, default=True)
        True
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() not in ('false', '0', 'no', 'off', '')
    # For integers and other types, use standard truthiness
    return bool(value)


def get_asset_counts(params: dict) -> dict:
    """Handle get_asset_counts request.
    
    Returns current asset counts by category for the dashboard.
    
    Request format: {
        "method": "get_asset_counts",
        "params": {
            "use_cache": true  # optional, default true
        },
        "id": "..."
    }
    
    Response format: {
        "music": 12437,
        "sfx": 8291,
        "vfx": 3102,
        "total": 23830,
        "formatted": {
            "music": "12,437",
            "sfx": "8,291",
            "vfx": "3,102",
            "total": "23,830"
        },
        "last_updated": "2026-04-03T12:34:56"
    }
    
    Args:
        params: Request parameters containing:
            - use_cache: Whether to use cached counts (default: true)
            
    Returns:
        Response dictionary with asset counts by category
    """
    # Validate params type
    is_valid, error_response = _validate_params_type(params)
    if not is_valid:
        return error_response
    
    try:
        indexer = _get_indexer()
        
        # Check if indexer assets are available
        if not hasattr(indexer, '_assets') or indexer._assets is None:
            # Return empty counts if assets not initialized
            return {
                'music': 0,
                'sfx': 0,
                'vfx': 0,
                'total': 0,
                'formatted': {
                    'music': '0',
                    'sfx': '0',
                    'vfx': '0',
                    'total': '0'
                },
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
        
        # Coerce use_cache parameter to boolean (handles string values)
        use_cache = _coerce_bool(params.get('use_cache'), default=True)
        
        # Get counts from the counter (public API via get_asset_counts method if available)
        if hasattr(indexer, '_counter') and indexer._counter is not None:
            counts = indexer._counter.count_by_category(indexer._assets, use_cache=use_cache)
            return counts.to_dict()
        else:
            # Fallback: return empty counts if counter not initialized
            return {
                'music': 0,
                'sfx': 0,
                'vfx': 0,
                'total': 0,
                'formatted': {
                    'music': '0',
                    'sfx': '0',
                    'vfx': '0',
                    'total': '0'
                },
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
        
    except TypeError as e:
        # Handle type errors specifically (e.g., invalid parameter types)
        logger.warning(f"Type error in get_asset_counts: {e}")
        return {
            'error': {
                'code': 'INVALID_PARAMS',
                'category': 'validation',
                'message': str(e),
                'recoverable': True,
                'suggestion': 'Check parameter types - use_cache must be boolean'
            }
        }
    except AttributeError as e:
        # Handle attribute errors (missing indexer components)
        logger.error(f"Attribute error in get_asset_counts: {e}")
        return {
            'error': {
                'code': 'INDEXER_NOT_READY',
                'category': 'internal',
                'message': 'Indexer not fully initialized',
                'recoverable': True,
                'suggestion': 'Wait for indexer initialization to complete'
            }
        }
    except Exception as e:
        # Log full stack trace for debugging
        logger.exception("Unexpected error getting asset counts")
        return {
            'error': {
                'code': 'COUNT_ERROR',
                'category': 'internal',
                'message': f"Failed to get asset counts: {str(e)}",
                'recoverable': True,
                'suggestion': 'Try refreshing the dashboard or check logs'
            }
        }


def trigger_reindex(params: dict) -> dict:
    """Handle trigger_reindex request.
    
    Initiates full re-indexing of all configured media folders.
    Unlike incremental indexing, this scans all files regardless of
    modification time and detects moved/deleted files.
    
    Request format: {
        "method": "trigger_reindex",
        "params": {},
        "id": "..."
    }
    
    Response format: {
        "success": true,
        "result": {
            "new_count": 15,
            "modified_count": 3,
            "moved_count": 2,
            "deleted_count": 7,
            "indexed_count": 18,
            "total_scanned": 24531,
            "duration_ms": 45230
        }
    }
    
    Args:
        params: Request parameters (unused, accepts empty dict)
        
    Returns:
        Response dictionary with re-indexing statistics
    """
    # Validate params type (accepts empty dict)
    is_valid, error_response = _validate_params_type(params)
    if not is_valid:
        return error_response
    
    config_manager = ConfigManager()
    
    # Check if media folders are configured
    if not config_manager.is_media_folders_configured():
        return {
            'error': {
                'code': 'NOT_CONFIGURED',
                'category': 'configuration',
                'message': 'Media folders are not configured',
                'suggestion': 'Configure media folders before re-indexing'
            }
        }
    
    folder_config = config_manager.get_media_folders_config()
    
    # Get the indexer instance
    indexer = _get_indexer()
    
    # Connect to database for full re-indexing
    loop = _get_event_loop()
    
    try:
        # Connect to SpacetimeDB if not already connected
        connected = loop.run_until_complete(indexer.connect_database())
        if not connected:
            logger.warning("Failed to connect to SpacetimeDB, continuing with in-memory only")
    except Exception as e:
        logger.warning(f"Database connection error: {e}, continuing with in-memory only")
    
    # Run re-indexing (async operation in sync context)
    try:
        # Reset cancellation state before starting
        indexer.reset_cancellation()
        
        # Note: Re-indexing always does full scan (incremental=False behavior)
        result = loop.run_until_complete(
            indexer.reindex_folders(folder_configs=folder_config)
        )
        
        return {
            'success': True,
            'result': {
                'new_count': result.new_count,
                'modified_count': result.modified_count,
                'moved_count': getattr(result, 'moved_count', 0),
                'deleted_count': result.deleted_count,
                'indexed_count': result.indexed_count,
                'total_scanned': getattr(result, 'total_scanned', 0),
                'duration_ms': result.duration_ms
            }
        }
    except Exception as e:
        logger.exception("Re-indexing failed")
        return {
            'error': {
                'code': 'REINDEX_ERROR',
                'category': 'internal',
                'message': str(e),
                'suggestion': 'Check folder permissions, disk space, and database connection'
            }
        }
    finally:
        # Disconnect from database
        try:
            loop.run_until_complete(indexer.disconnect_database())
        except Exception as e:
            logger.warning(f"Error disconnecting from database: {e}")


# Registry of media handlers
MEDIA_HANDLERS = {
    'get_media_folders': get_media_folders,
    'save_media_folders': save_media_folders,
    'clear_media_folders': clear_media_folders,
    'check_media_folders_configured': check_media_folders_configured,
    'validate_folder_path': validate_folder_path,
    'index_media': index_media,
    'get_index_status': get_index_status,
    'cancel_indexing': cancel_indexing,
    'get_asset_counts': get_asset_counts,
    'trigger_reindex': trigger_reindex,
}
