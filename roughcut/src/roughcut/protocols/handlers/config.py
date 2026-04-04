"""Protocol handlers for configuration management.

Provides JSON-RPC handlers for Lua-Python communication
for Notion configuration operations.
"""

from ...config.settings import ConfigManager


def get_notion_config(params: dict) -> dict:
    """Handle get_notion_config request.
    
    Returns current Notion configuration without exposing
    the decrypted API token to Lua.
    
    Request format: {"method": "get_notion_config", "params": {}, "id": "..."}
    Response format: {
        "configured": bool,
        "page_url": str or None,
        "enabled": bool,
        "last_updated": str or None
    }
    
    Args:
        params: Request parameters (unused)
        
    Returns:
        Response dictionary with configuration status
    """
    try:
        config_manager = ConfigManager()
        config = config_manager.get_notion_config()
        
        # Return decrypted token only to trusted internal layer
        # but do NOT expose it to Lua for security
        return {
            'configured': config_manager.is_notion_configured(),
            'page_url': config.page_url,
            'enabled': config.enabled,
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


def save_notion_config(params: dict) -> dict:
    """Handle save_notion_config request.
    
    Saves Notion configuration with encrypted API token.
    
    Request format: {
        "method": "save_notion_config",
        "params": {
            "api_token": "secret_...",
            "page_url": "https://..."
        },
        "id": "..."
    }
    
    Args:
        params: Request parameters containing:
            - api_token: Notion API integration token
            - page_url: Notion page URL
            
    Returns:
        Response dictionary with success status
    """
    try:
        api_token = params.get('api_token')
        page_url = params.get('page_url')
        
        if not api_token or not page_url:
            return {
                'error': {
                    'code': 'MISSING_REQUIRED_FIELDS',
                    'category': 'validation',
                    'message': 'API token and page URL are required',
                    'suggestion': 'Enter both the Notion API token and page URL'
                }
            }
        
        config_manager = ConfigManager()
        success, message = config_manager.save_notion_config(api_token, page_url)
        
        if success:
            return {
                'success': True,
                'message': message,
                'configured': True
            }
        else:
            return {
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'category': 'validation',
                    'message': message,
                    'suggestion': 'Check that the API token and URL are correct'
                }
            }
    except Exception as e:
        return {
            'error': {
                'code': 'CONFIG_SAVE_ERROR',
                'category': 'internal',
                'message': str(e),
                'suggestion': 'Ensure configuration directory is writable'
            }
        }


def clear_notion_config(params: dict) -> dict:
    """Handle clear_notion_config request.
    
    Removes Notion configuration from storage.
    
    Request format: {"method": "clear_notion_config", "params": {}, "id": "..."}
    
    Args:
        params: Request parameters (unused)
        
    Returns:
        Response dictionary with success status
    """
    try:
        config_manager = ConfigManager()
        success, message = config_manager.clear_notion_config()
        
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


def check_notion_configured(params: dict) -> dict:
    """Handle check_notion_configured request.
    
    Quick check to determine if Notion is configured.
    Used for graceful degradation and UI state management.
    
    Request format: {"method": "check_notion_configured", "params": {}, "id": "..."}
    
    Args:
        params: Request parameters (unused)
        
    Returns:
        Response dictionary with configured status
    """
    try:
        config_manager = ConfigManager()
        is_configured = config_manager.is_notion_configured()
        
        return {
            'configured': is_configured
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


# Registry of config handlers
CONFIG_HANDLERS = {
    'get_notion_config': get_notion_config,
    'save_notion_config': save_notion_config,
    'clear_notion_config': clear_notion_config,
    'check_notion_configured': check_notion_configured,
}
