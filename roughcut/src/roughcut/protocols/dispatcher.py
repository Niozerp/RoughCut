"""Protocol request dispatcher for JSON-RPC handlers.

Routes incoming JSON-RPC requests to appropriate handlers
and returns formatted responses.
"""

import json
from typing import Any, Callable, Dict, Optional

from .handlers.config import CONFIG_HANDLERS
from .handlers.notion import NOTION_HANDLERS
from .handlers.media import MEDIA_HANDLERS
from .handlers.formats import FORMAT_HANDLERS
from .handlers.workflows import WORKFLOW_HANDLERS
from .handlers.ai import AI_HANDLERS
from .handlers.timeline import TIMELINE_HANDLERS


class ProtocolDispatcher:
    """Dispatches JSON-RPC requests to appropriate handlers.
    
    Usage:
        dispatcher = ProtocolDispatcher()
        dispatcher.register_handlers(CONFIG_HANDLERS)
        
        # Dispatch a request
        request = {"method": "get_notion_config", "params": {}, "id": "1"}
        response = dispatcher.dispatch(request)
    """
    
    def __init__(self):
        """Initialize the dispatcher with empty handler registry."""
        self._handlers: Dict[str, Callable] = {}
        
        # Register built-in handlers
        self.register_handlers(CONFIG_HANDLERS)
        self.register_handlers(NOTION_HANDLERS)
        self.register_handlers(MEDIA_HANDLERS)
        self.register_handlers(FORMAT_HANDLERS)
        self.register_handlers(WORKFLOW_HANDLERS)
        self.register_handlers(AI_HANDLERS)
        self.register_handlers(TIMELINE_HANDLERS)
    
    def register_handler(self, method: str, handler: Callable) -> None:
        """Register a single handler for a method.
        
        Args:
            method: Method name (e.g., "get_notion_config")
            handler: Handler function that accepts (params: dict) -> dict
        """
        self._handlers[method] = handler
    
    def register_handlers(self, handlers: Dict[str, Callable]) -> None:
        """Register multiple handlers at once.
        
        Args:
            handlers: Dictionary mapping method names to handler functions
        """
        self._handlers.update(handlers)
    
    def dispatch(self, request: dict) -> dict:
        """Dispatch a request to the appropriate handler.
        
        Args:
            request: JSON-RPC request dictionary with:
                - method: Method name to invoke
                - params: Method parameters (dict)
                - id: Request ID for response correlation
                
        Returns:
            JSON-RPC response dictionary with:
                - result: Handler result (if success)
                - error: Error details (if failure)
                - id: Request ID from request
        """
        method = request.get('method')
        params = request.get('params', {})
        request_id = request.get('id')
        
        if not method:
            return self._error_response(
                request_id,
                'INVALID_REQUEST',
                'validation',
                'Method name is required',
                'Include "method" field in request'
            )
        
        handler = self._handlers.get(method)
        
        if not handler:
            return self._error_response(
                request_id,
                'METHOD_NOT_FOUND',
                'validation',
                f'Unknown method: {method}',
                f'Available methods: {list(self._handlers.keys())}'
            )
        
        try:
            result = handler(params)
            
            # Check if handler returned an error
            if isinstance(result, dict) and 'error' in result:
                return {
                    'error': result['error'],
                    'id': request_id
                }
            
            return {
                'result': result,
                'error': None,
                'id': request_id
            }
            
        except Exception as e:
            return self._error_response(
                request_id,
                'INTERNAL_ERROR',
                'internal',
                str(e),
                'An unexpected error occurred'
            )
    
    def _error_response(
        self,
        request_id: Any,
        code: str,
        category: str,
        message: str,
        suggestion: str
    ) -> dict:
        """Create a standardized error response.
        
        Args:
            request_id: Original request ID
            code: Error code (e.g., "METHOD_NOT_FOUND")
            category: Error category (validation, internal, etc.)
            message: Human-readable error message
            suggestion: Actionable suggestion for user
            
        Returns:
            JSON-RPC error response dictionary
        """
        return {
            'error': {
                'code': code,
                'category': category,
                'message': message,
                'suggestion': suggestion
            },
            'id': request_id
        }
    
    def get_available_methods(self) -> list:
        """Get list of available method names.
        
        Returns:
            List of registered method names
        """
        return list(self._handlers.keys())


# Global dispatcher instance
_dispatcher: Optional[ProtocolDispatcher] = None


def get_dispatcher() -> ProtocolDispatcher:
    """Get the global protocol dispatcher instance.
    
    Returns:
        Singleton ProtocolDispatcher instance
    """
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = ProtocolDispatcher()
    return _dispatcher


def dispatch_request(request_json: str) -> str:
    """Dispatch a JSON-RPC request and return JSON response.
    
    Convenience function for stdin/stdout protocol.
    
    Args:
        request_json: JSON string containing the request
        
    Returns:
        JSON string containing the response
    """
    try:
        request = json.loads(request_json)
    except json.JSONDecodeError as e:
        return json.dumps({
            'error': {
                'code': 'PARSE_ERROR',
                'category': 'validation',
                'message': f'Invalid JSON: {e}',
                'suggestion': 'Ensure request is valid JSON'
            },
            'id': None
        })
    
    dispatcher = get_dispatcher()
    response = dispatcher.dispatch(request)
    
    return json.dumps(response)
