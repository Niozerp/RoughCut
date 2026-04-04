"""Protocol handlers for Notion connection validation.

Provides JSON-RPC handlers for Lua-Python communication
to validate Notion API connection and retrieve status.
"""

from ...backend.notion.client import NotionClient
from ...backend.notion.models import ConnectionStatus


def validate_notion_connection(params: dict) -> dict:
    """Handle validate_notion_connection request.
    
    Validates the complete Notion connection including API token
    and page accessibility.
    
    Request format: {"method": "validate_notion_connection", "params": {}, "id": "..."}
    
    Response format: {
        "valid": bool,
        "status": "CONNECTED" | "DISCONNECTED" | "NOT_CONFIGURED" | "ERROR",
        "error_type": str or None,
        "error_message": str or None,
        "suggestion": str or None,
        "timestamp": str (ISO format)
    }
    
    Args:
        params: Request parameters (unused)
        
    Returns:
        Response dictionary with validation result
    """
    try:
        client = NotionClient()
        result = client.validate_connection()
        
        return {
            'valid': result.valid,
            'status': result.status.name if result.status else 'ERROR',
            'error_type': result.error_type.name if result.error_type else None,
            'error_message': result.error_message if result.error_message else None,
            'suggestion': result.suggestion if result.suggestion else None,
            'timestamp': result.timestamp.isoformat() if result.timestamp else None
        }
    except Exception as e:
        return {
            'valid': False,
            'status': 'ERROR',
            'error_type': 'UNKNOWN',
            'error_message': f'Validation failed: {str(e)}',
            'suggestion': 'Please try again or check the logs for more details.',
            'timestamp': None
        }


def get_connection_status(params: dict) -> dict:
    """Handle get_connection_status request.
    
    Returns current connection status including last validation result
    if available (uses cached/last known status).
    
    Request format: {"method": "get_connection_status", "params": {}, "id": "..."}
    
    Response format: {
        "configured": bool,
        "status": "CONNECTED" | "DISCONNECTED" | "NOT_CONFIGURED" | "ERROR",
        "last_validated": str or None (ISO format),
        "validation_result": { ... } or None
    }
    
    Args:
        params: Request parameters (unused)
        
    Returns:
        Response dictionary with connection status
    """
    try:
        client = NotionClient()
        
        # Check if configured
        is_configured = client.is_configured()
        
        if not is_configured:
            return {
                'configured': False,
                'status': 'NOT_CONFIGURED',
                'last_validated': None,
                'validation_result': None
            }
        
        # Try to get last validation result from config
        from ...config.settings import ConfigManager
        config_manager = ConfigManager()
        last_validation = config_manager.get_last_validation_result()
        
        if last_validation:
            return {
                'configured': True,
                'status': last_validation.status.name if last_validation.status else 'ERROR',
                'last_validated': last_validation.timestamp.isoformat() if last_validation.timestamp else None,
                'validation_result': last_validation.to_dict()
            }
        
        # No cached validation, return generic configured status
        return {
            'configured': True,
            'status': 'CONNECTED',  # Assume connected if configured but not validated yet
            'last_validated': None,
            'validation_result': None
        }
    except Exception as e:
        return {
            'configured': False,
            'status': 'ERROR',
            'last_validated': None,
            'validation_result': None,
            'error': {
                'code': 'STATUS_CHECK_ERROR',
                'category': 'internal',
                'message': str(e),
                'suggestion': 'Failed to check connection status'
            }
        }


def test_notion_sync(params: dict) -> dict:
    """Handle test_notion_sync request.
    
    Performs a test sync operation to verify data flow.
    This is a placeholder for Epic 2 full sync implementation.
    
    Request format: {"method": "test_notion_sync", "params": {}, "id": "..."}
    
    Response format: {
        "success": bool,
        "message": str,
        "connection_valid": bool
    }
    
    Args:
        params: Request parameters (unused)
        
    Returns:
        Response dictionary with test sync result
    """
    try:
        client = NotionClient()
        
        # First validate connection
        validation = client.validate_connection()
        
        if not validation.is_success():
            return {
                'success': False,
                'message': f'Connection validation failed: {validation.error_message}',
                'connection_valid': False,
                'suggestion': validation.suggestion
            }
        
        # Test sync with empty list (placeholder for Epic 2)
        sync_result = client.sync_media_database([])
        
        return {
            'success': sync_result.get('success', False),
            'message': sync_result.get('message', 'Test sync completed'),
            'connection_valid': True,
            'note': sync_result.get('note', 'Full sync coming in Epic 2')
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Test sync failed: {str(e)}',
            'connection_valid': False,
            'suggestion': 'Check your Notion configuration and try again.'
        }


# Registry of Notion handlers
NOTION_HANDLERS = {
    'validate_notion_connection': validate_notion_connection,
    'get_connection_status': get_connection_status,
    'test_notion_sync': test_notion_sync,
}
