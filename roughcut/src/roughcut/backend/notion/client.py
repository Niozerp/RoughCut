"""Notion API client for RoughCut.

Provides Notion API integration for media database synchronization
with connection validation, error handling, and graceful degradation.
"""

import re
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from ...config.settings import get_config_manager
from .models import ConnectionStatus, ErrorType, ValidationResult


# Maximum number of retries for transient failures
MAX_RETRIES = 3
# Initial retry delay in seconds
RETRY_DELAY = 1
# Maximum connection timeout in seconds
CONNECTION_TIMEOUT = 10


class NotionClient:
    """Client for Notion API integration.
    
    Provides methods for:
    - Connection validation
    - Media database synchronization
    - Graceful degradation when Notion is not configured
    
    Usage:
        client = NotionClient()
        
        # Check if configured
        if client.is_configured():
            # Validate connection
            result = client.validate_connection()
            if result.is_success():
                # Safe to use Notion operations
                pass
    """
    
    def __init__(self):
        """Initialize the Notion client."""
        self._config_manager = get_config_manager()
        self._client = None
    
    def is_configured(self) -> bool:
        """Check if Notion is properly configured.
        
        Returns:
            True if API token and page URL are set
        """
        return self._config_manager.is_notion_configured()
    
    def get_page_url(self) -> Optional[str]:
        """Get the configured Notion page URL.
        
        Returns:
            Page URL if configured, None otherwise
        """
        config = self._config_manager.get_notion_config()
        return config.page_url if config.is_configured() else None
    
    def _get_api_client(self):
        """Get or create Notion API client instance.
        
        Returns:
            Notion API client instance or None if not configured
        """
        if self._client is not None:
            return self._client
        
        if not self.is_configured():
            return None
        
        try:
            from notion_client import Client
            config = self._config_manager.get_notion_config()
            # Decrypt and get the actual token
            token = config.api_token
            
            if not token:
                return None
            
            self._client = Client(auth=token)
            return self._client
        except ImportError:
            # notion-client library not installed
            return None
        except Exception:
            # Any other error creating client
            return None
    
    def _extract_page_id(self, url: str) -> Optional[str]:
        """Extract Notion page ID from URL.
        
        Notion URLs have the format: https://www.notion.so/workspace/page-id
        or https://www.notion.so/page-id
        
        The page ID is a 32-character alphanumeric string at the end.
        
        Args:
            url: Notion page URL
            
        Returns:
            Page ID if found, None otherwise
        """
        if not url:
            return None
        
        # Remove query parameters and fragments
        parsed = urlparse(url)
        path = parsed.path
        
        # Extract the last component of the path
        parts = path.strip('/').split('/')
        if not parts:
            return None
        
        last_part = parts[-1]
        
        # Handle URL format with page title: "page-title-32charid"
        # Extract just the 32-character ID
        if '-' in last_part:
            # Split by hyphen and get the last segment
            segments = last_part.split('-')
            for segment in reversed(segments):
                # Page ID is 32 characters, alphanumeric with hyphens removed
                cleaned = segment.replace('-', '')
                if len(cleaned) == 32 and cleaned.isalnum():
                    return cleaned
        
        # Handle direct page ID format
        cleaned = last_part.replace('-', '')
        if len(cleaned) == 32 and cleaned.isalnum():
            return cleaned
        
        return None
    
    def _classify_error(self, error: Exception) -> tuple[ErrorType, str, str]:
        """Classify an error and generate user-friendly message.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Tuple of (error_type, error_message, suggestion)
        """
        error_str = str(error).lower()
        error_type = ErrorType.UNKNOWN
        error_message = str(error)
        suggestion = "Please try again or contact support if the issue persists."
        
        # Authentication errors
        if any(keyword in error_str for keyword in ['unauthorized', 'invalid token', 'api token', 'authentication', 'auth']):
            error_type = ErrorType.AUTHENTICATION
            error_message = "Invalid API token. The token may be expired or incorrect."
            suggestion = "Check your API token in Notion (notion.so/my-integrations) and ensure it has the correct permissions."
        
        # Page not found errors
        elif any(keyword in error_str for keyword in ['not found', 'page not found', 'could not find', 'invalid page']):
            error_type = ErrorType.PAGE_NOT_FOUND
            error_message = "Notion page not found or not accessible."
            suggestion = "Verify the page URL is correct and that the integration has access to this page."
        
        # Timeout errors
        elif any(keyword in error_str for keyword in ['timeout', 'timed out']):
            error_type = ErrorType.TIMEOUT
            error_message = "Connection timed out. Notion API is not responding."
            suggestion = "Check your internet connection and try again. Notion API may be temporarily unavailable."
        
        # Network errors
        elif any(keyword in error_str for keyword in ['network', 'connection', 'internet', 'unreachable', 'dns', 'ssl']):
            error_type = ErrorType.NETWORK
            error_message = "Network error. Unable to reach Notion API."
            suggestion = "Check your internet connection and ensure you can access notion.so in your browser."
        
        # Rate limiting
        elif any(keyword in error_str for keyword in ['rate limit', 'too many requests', '429']):
            error_type = ErrorType.NETWORK
            error_message = "Rate limit exceeded. Too many requests to Notion API."
            suggestion = "Wait a few minutes and try again. Notion API has rate limits."
        
        return error_type, error_message, suggestion
    
    def _make_request_with_retry(self, operation, *args, **kwargs) -> tuple[bool, any, Optional[Exception]]:
        """Execute an operation with exponential backoff retry.
        
        Args:
            operation: Callable to execute
            *args, **kwargs: Arguments to pass to operation
            
        Returns:
            Tuple of (success, result, error)
        """
        last_error = None
        delay = RETRY_DELAY
        
        for attempt in range(MAX_RETRIES):
            try:
                result = operation(*args, **kwargs)
                return True, result, None
            except Exception as e:
                last_error = e
                
                # Check if error is retryable
                error_str = str(e).lower()
                is_retryable = any(keyword in error_str for keyword in [
                    'timeout', 'network', 'connection', 'unreachable', 'rate limit', 'too many requests'
                ])
                
                if not is_retryable or attempt == MAX_RETRIES - 1:
                    # Don't retry non-retryable errors or on last attempt
                    break
                
                # Wait before retry with exponential backoff
                time.sleep(delay)
                delay *= 2  # Exponential backoff
        
        return False, None, last_error
    
    def validate_token(self) -> tuple[bool, Optional[ErrorType], str, str]:
        """Validate the API token by making a test API call.
        
        Returns:
            Tuple of (is_valid, error_type, error_message, suggestion)
        """
        if not self.is_configured():
            return False, ErrorType.AUTHENTICATION, "Notion integration not configured", "Configure Notion settings first."
        
        client = self._get_api_client()
        if client is None:
            return False, ErrorType.AUTHENTICATION, "Failed to create Notion API client", "Check that notion-client library is installed."
        
        # Test token by fetching current user
        success, result, error = self._make_request_with_retry(
            lambda: client.users.me()
        )
        
        if success:
            return True, None, "", ""
        
        if error:
            error_type, message, suggestion = self._classify_error(error)
            return False, error_type, message, suggestion
        
        return False, ErrorType.UNKNOWN, "Unknown error validating token", "Please try again."
    
    def validate_page_access(self) -> tuple[bool, Optional[ErrorType], str, str]:
        """Validate page access by attempting to fetch the configured page.
        
        Returns:
            Tuple of (is_valid, error_type, error_message, suggestion)
        """
        if not self.is_configured():
            return False, ErrorType.PAGE_NOT_FOUND, "Notion integration not configured", "Configure Notion settings first."
        
        page_url = self.get_page_url()
        if not page_url:
            return False, ErrorType.PAGE_NOT_FOUND, "No page URL configured", "Enter a valid Notion page URL."
        
        page_id = self._extract_page_id(page_url)
        if not page_id:
            return False, ErrorType.PAGE_NOT_FOUND, "Could not extract page ID from URL", "Verify the Notion page URL is in the correct format (https://www.notion.so/...)."
        
        client = self._get_api_client()
        if client is None:
            return False, ErrorType.PAGE_NOT_FOUND, "Failed to create Notion API client", "Check that notion-client library is installed."
        
        # Test page access by fetching the page
        success, result, error = self._make_request_with_retry(
            lambda: client.pages.retrieve(page_id=page_id)
        )
        
        if success:
            return True, None, "", ""
        
        if error:
            error_type, message, suggestion = self._classify_error(error)
            return False, error_type, message, suggestion
        
        return False, ErrorType.UNKNOWN, "Unknown error validating page access", "Please try again."
    
    def validate_connection(self) -> ValidationResult:
        """Validate the complete Notion connection (token + page).
        
        This method performs a full validation:
        1. Check if Notion is configured
        2. Validate API token authentication
        3. Validate page accessibility
        4. Persist the validation result to configuration
        
        Returns:
            ValidationResult with detailed status and error information
        """
        # Check if configured
        if not self.is_configured():
            result = ValidationResult(
                valid=False,
                status=ConnectionStatus.NOT_CONFIGURED,
                error_type=None,
                error_message="Notion integration is not configured",
                suggestion="Go to Settings > Notion Integration to configure your API token and page URL.",
                timestamp=datetime.now()
            )
            # Persist the result
            try:
                self._config_manager.save_validation_result(result)
            except Exception:
                # Ignore persistence errors - validation still works
                pass
            return result
        
        # First validate token
        token_valid, token_error, token_message, token_suggestion = self.validate_token()
        
        if not token_valid:
            result = ValidationResult(
                valid=False,
                status=ConnectionStatus.DISCONNECTED,
                error_type=token_error or ErrorType.AUTHENTICATION,
                error_message=token_message,
                suggestion=token_suggestion,
                timestamp=datetime.now()
            )
            # Persist the result
            try:
                self._config_manager.save_validation_result(result)
            except Exception:
                pass
            return result
        
        # Then validate page access
        page_valid, page_error, page_message, page_suggestion = self.validate_page_access()
        
        if not page_valid:
            result = ValidationResult(
                valid=False,
                status=ConnectionStatus.DISCONNECTED,
                error_type=page_error or ErrorType.PAGE_NOT_FOUND,
                error_message=page_message,
                suggestion=page_suggestion,
                timestamp=datetime.now()
            )
            # Persist the result
            try:
                self._config_manager.save_validation_result(result)
            except Exception:
                pass
            return result
        
        # Both validations passed
        result = ValidationResult(
            valid=True,
            status=ConnectionStatus.CONNECTED,
            error_type=None,
            error_message="",
            suggestion="Connection is working properly. You can now sync your media database to Notion.",
            timestamp=datetime.now()
        )
        # Persist the result
        try:
            self._config_manager.save_validation_result(result)
        except Exception:
            pass
        return result
    
    def sync_media_database(self, media_items: list) -> dict:
        """Sync media database to Notion.
        
        Args:
            media_items: List of media items to sync
            
        Returns:
            Result dictionary with sync status
        """
        if not self.is_configured():
            return {
                'success': False,
                'skipped': True,
                'message': 'Notion integration not configured',
                'suggestion': 'Configure Notion settings to enable sync',
                'synced_count': 0
            }
        
        # Validate connection before attempting sync
        validation = self.validate_connection()
        if not validation.is_success():
            return {
                'success': False,
                'skipped': False,
                'message': f'Connection validation failed: {validation.error_message}',
                'suggestion': validation.suggestion,
                'synced_count': 0
            }
        
        # Use sync orchestrator for full sync
        from .sync import NotionSyncOrchestrator
        orchestrator = NotionSyncOrchestrator()
        
        try:
            result = orchestrator.sync_all_assets(media_items)
            
            return {
                'success': result.success,
                'message': 'Media database sync completed' if result.success else result.error_message,
                'synced_count': result.synced_count,
                'timestamp': result.timestamp.isoformat() if result.timestamp else None
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Sync failed: {str(e)}',
                'synced_count': 0,
                'suggestion': 'Check logs for details and try again'
            }


def is_notion_available() -> bool:
    """Check if Notion integration is available and configured.
    
    Convenience function for quick checks before Notion operations.
    
    Returns:
        True if Notion is configured and ready to use
    """
    client = NotionClient()
    return client.is_configured()

