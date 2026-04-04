"""Notion sync specific exceptions.

Provides custom exception classes for Notion sync operations with
categorized error types for proper handling and recovery.
"""

from enum import Enum, auto
from typing import Optional


class NotionSyncErrorCategory(Enum):
    """Categories of Notion sync errors for targeted handling.
    
    Values:
        API_ERROR: Notion API returned an error response
        AUTH_ERROR: Authentication or authorization failure
        CONFIG_ERROR: Configuration-related issues
        NETWORK_ERROR: Network connectivity issues
        RATE_LIMIT: API rate limiting (429 errors)
        VALIDATION_ERROR: Data validation failures
        TIMEOUT_ERROR: Request timeout
        UNKNOWN: Unclassified errors
    """
    API_ERROR = auto()
    AUTH_ERROR = auto()
    CONFIG_ERROR = auto()
    NETWORK_ERROR = auto()
    RATE_LIMIT = auto()
    VALIDATION_ERROR = auto()
    TIMEOUT_ERROR = auto()
    UNKNOWN = auto()


class NotionSyncError(Exception):
    """Notion sync specific errors with categorization.
    
    Attributes:
        code: Error code string (e.g., "NOTION_API_429")
        category: Error category for handling strategy
        message: Human-readable error message
        suggestion: Actionable guidance for user
        retryable: Whether this error can be retried
    """
    
    def __init__(
        self,
        code: str,
        category: NotionSyncErrorCategory,
        message: str,
        suggestion: str,
        retryable: bool = False,
        original_error: Optional[Exception] = None
    ):
        """Initialize Notion sync error.
        
        Args:
            code: Error code string
            category: Error category enum
            message: Human-readable message
            suggestion: Actionable suggestion for user
            retryable: Whether operation can be retried
            original_error: Original exception if wrapped
        """
        super().__init__(message)
        self.code = code
        self.category = category
        self.message = message
        self.suggestion = suggestion
        self.retryable = retryable
        self.original_error = original_error
    
    def to_dict(self) -> dict:
        """Convert error to dictionary for serialization.
        
        Returns:
            Dictionary representation of the error
        """
        return {
            'code': self.code,
            'category': self.category.name,
            'message': self.message,
            'suggestion': self.suggestion,
            'retryable': self.retryable
        }
    
    def __str__(self) -> str:
        """Return formatted error string."""
        return f"[{self.code}] {self.message} ({self.suggestion})"


class NotionAPIError(NotionSyncError):
    """Notion API returned an error response."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        suggestion: str = "Check Notion API documentation and try again.",
        retryable: bool = False
    ):
        """Initialize API error.
        
        Args:
            message: Error message from API
            status_code: HTTP status code if available
            suggestion: Recovery suggestion
            retryable: Whether to retry
        """
        code = f"NOTION_API_{status_code}" if status_code else "NOTION_API_ERROR"
        super().__init__(
            code=code,
            category=NotionSyncErrorCategory.API_ERROR,
            message=message,
            suggestion=suggestion,
            retryable=retryable
        )
        self.status_code = status_code


class NotionAuthError(NotionSyncError):
    """Authentication or authorization failure."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        suggestion: str = "Verify your API token in Notion settings."
    ):
        """Initialize auth error."""
        super().__init__(
            code="NOTION_AUTH_FAILED",
            category=NotionSyncErrorCategory.AUTH_ERROR,
            message=message,
            suggestion=suggestion,
            retryable=False
        )


class NotionRateLimitError(NotionSyncError):
    """API rate limit exceeded (429 error)."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None
    ):
        """Initialize rate limit error.
        
        Args:
            message: Error message
            retry_after: Seconds to wait before retry
        """
        suggestion = "Wait a moment before retrying."
        if retry_after:
            suggestion = f"Wait {retry_after} seconds before retrying."
        
        super().__init__(
            code="NOTION_RATE_LIMIT",
            category=NotionSyncErrorCategory.RATE_LIMIT,
            message=message,
            suggestion=suggestion,
            retryable=True
        )
        self.retry_after = retry_after


class NotionConfigError(NotionSyncError):
    """Configuration error for Notion sync."""
    
    def __init__(
        self,
        message: str,
        suggestion: str = "Check Notion configuration settings."
    ):
        """Initialize config error."""
        super().__init__(
            code="NOTION_CONFIG_ERROR",
            category=NotionSyncErrorCategory.CONFIG_ERROR,
            message=message,
            suggestion=suggestion,
            retryable=False
        )


class NotionNetworkError(NotionSyncError):
    """Network connectivity error."""
    
    def __init__(
        self,
        message: str = "Network error occurred",
        suggestion: str = "Check your internet connection and try again."
    ):
        """Initialize network error."""
        super().__init__(
            code="NOTION_NETWORK_ERROR",
            category=NotionSyncErrorCategory.NETWORK_ERROR,
            message=message,
            suggestion=suggestion,
            retryable=True
        )


class NotionTimeoutError(NotionSyncError):
    """Request timeout error."""
    
    def __init__(
        self,
        message: str = "Request timed out",
        suggestion: str = "Try again later. If the issue persists, check Notion API status."
    ):
        """Initialize timeout error."""
        super().__init__(
            code="NOTION_TIMEOUT",
            category=NotionSyncErrorCategory.TIMEOUT_ERROR,
            message=message,
            suggestion=suggestion,
            retryable=True
        )


class NotionValidationError(NotionSyncError):
    """Data validation error for Notion operations."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        suggestion: str = "Check data format and try again."
    ):
        """Initialize validation error.
        
        Args:
            message: Error message
            field: Field that failed validation
            suggestion: Recovery suggestion
        """
        super().__init__(
            code="NOTION_VALIDATION_ERROR",
            category=NotionSyncErrorCategory.VALIDATION_ERROR,
            message=message,
            suggestion=suggestion,
            retryable=False
        )
        self.field = field


def classify_notion_error(error: Exception) -> NotionSyncError:
    """Classify a raw exception into appropriate NotionSyncError.
    
    Args:
        error: The exception to classify
        
    Returns:
        Classified NotionSyncError
    """
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()
    
    # Rate limiting
    if any(k in error_str for k in ['rate limit', 'too many requests', '429']):
        retry_after = None
        # Try to extract retry_after if available
        if hasattr(error, 'retry_after'):
            retry_after = error.retry_after
        return NotionRateLimitError(retry_after=retry_after)
    
    # Authentication errors
    if any(k in error_str for k in ['unauthorized', 'invalid token', 'auth', 'authentication', '401']):
        return NotionAuthError(message=str(error))
    
    # Page not found / permissions
    if any(k in error_str for k in ['not found', '404', 'forbidden', '403', 'permission']):
        return NotionAPIError(
            message=str(error),
            status_code=404 if 'not found' in error_str else 403,
            suggestion="Verify the page URL and integration permissions.",
            retryable=False
        )
    
    # Network errors
    if any(k in error_str for k in ['network', 'connection', 'unreachable', 'dns', 'ssl', 'timeout']):
        if 'timeout' in error_str:
            return NotionTimeoutError(message=str(error))
        return NotionNetworkError(message=str(error))
    
    # API errors with status codes
    if hasattr(error, 'status'):
        status = error.status
        if status == 400:
            return NotionAPIError(
                message=str(error),
                status_code=400,
                suggestion="Check request format and parameters.",
                retryable=False
            )
        elif status == 500:
            return NotionAPIError(
                message=str(error),
                status_code=500,
                suggestion="Notion API server error. Try again later.",
                retryable=True
            )
        elif status == 503:
            return NotionAPIError(
                message=str(error),
                status_code=503,
                suggestion="Notion service temporarily unavailable. Try again later.",
                retryable=True
            )
    
    # Default to generic API error
    return NotionAPIError(
        message=str(error),
        suggestion="An unexpected error occurred. Check logs for details.",
        retryable=False
    )
