"""Unit tests for Notion sync error handling.

Tests the custom exception classes and error classification logic.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from roughcut.backend.notion.errors import (
    NotionSyncError,
    NotionSyncErrorCategory,
    NotionAPIError,
    NotionAuthError,
    NotionRateLimitError,
    NotionConfigError,
    NotionNetworkError,
    NotionTimeoutError,
    NotionValidationError,
    classify_notion_error,
)


class TestNotionSyncError:
    """Test suite for NotionSyncError base class."""

    def test_error_creation(self):
        """Test creating a NotionSyncError with all attributes."""
        error = NotionSyncError(
            code="TEST_ERROR",
            category=NotionSyncErrorCategory.API_ERROR,
            message="Test error message",
            suggestion="Try this to fix",
            retryable=True
        )
        
        assert error.code == "TEST_ERROR"
        assert error.category == NotionSyncErrorCategory.API_ERROR
        assert error.message == "Test error message"
        assert error.suggestion == "Try this to fix"
        assert error.retryable is True
    
    def test_error_to_dict(self):
        """Test converting error to dictionary."""
        error = NotionSyncError(
            code="TEST_001",
            category=NotionSyncErrorCategory.NETWORK_ERROR,
            message="Network failed",
            suggestion="Check connection"
        )
        
        result = error.to_dict()
        
        assert result['code'] == "TEST_001"
        assert result['category'] == "NETWORK_ERROR"
        assert result['message'] == "Network failed"
        assert result['suggestion'] == "Check connection"
        assert result['retryable'] is False
    
    def test_error_string_representation(self):
        """Test string representation of error."""
        error = NotionSyncError(
            code="ERR_001",
            category=NotionSyncErrorCategory.UNKNOWN,
            message="Something went wrong",
            suggestion="Contact support"
        )
        
        str_repr = str(error)
        
        assert "ERR_001" in str_repr
        assert "Something went wrong" in str_repr
        assert "Contact support" in str_repr


class TestNotionAPIError:
    """Test suite for NotionAPIError."""

    def test_api_error_with_status_code(self):
        """Test creating API error with status code."""
        error = NotionAPIError(
            message="Bad request",
            status_code=400,
            suggestion="Check your request format"
        )
        
        assert error.code == "NOTION_API_400"
        assert error.status_code == 400
        assert error.category == NotionSyncErrorCategory.API_ERROR
    
    def test_api_error_without_status_code(self):
        """Test creating API error without status code."""
        error = NotionAPIError(message="Unknown API error")
        
        assert error.code == "NOTION_API_ERROR"
        assert error.status_code is None


class TestNotionAuthError:
    """Test suite for NotionAuthError."""

    def test_auth_error_default_message(self):
        """Test auth error with default message."""
        error = NotionAuthError()
        
        assert error.code == "NOTION_AUTH_FAILED"
        assert error.category == NotionSyncErrorCategory.AUTH_ERROR
        assert "Authentication failed" in error.message
        assert error.retryable is False
    
    def test_auth_error_custom_message(self):
        """Test auth error with custom message."""
        error = NotionAuthError(
            message="Token expired",
            suggestion="Generate a new token"
        )
        
        assert error.message == "Token expired"
        assert error.suggestion == "Generate a new token"


class TestNotionRateLimitError:
    """Test suite for NotionRateLimitError."""

    def test_rate_limit_without_retry_after(self):
        """Test rate limit error without retry_after."""
        error = NotionRateLimitError()
        
        assert error.code == "NOTION_RATE_LIMIT"
        assert error.category == NotionSyncErrorCategory.RATE_LIMIT
        assert error.retryable is True
        assert error.retry_after is None
    
    def test_rate_limit_with_retry_after(self):
        """Test rate limit error with retry_after."""
        error = NotionRateLimitError(
            message="Rate limit hit",
            retry_after=60
        )
        
        assert error.retry_after == 60
        assert "60 seconds" in error.suggestion


class TestNotionConfigError:
    """Test suite for NotionConfigError."""

    def test_config_error(self):
        """Test config error creation."""
        error = NotionConfigError("Invalid database ID")
        
        assert error.code == "NOTION_CONFIG_ERROR"
        assert error.category == NotionSyncErrorCategory.CONFIG_ERROR
        assert error.message == "Invalid database ID"
        assert error.retryable is False


class TestNotionNetworkError:
    """Test suite for NotionNetworkError."""

    def test_network_error(self):
        """Test network error creation."""
        error = NotionNetworkError("Connection refused")
        
        assert error.code == "NOTION_NETWORK_ERROR"
        assert error.category == NotionSyncErrorCategory.NETWORK_ERROR
        assert error.message == "Connection refused"
        assert error.retryable is True


class TestNotionTimeoutError:
    """Test suite for NotionTimeoutError."""

    def test_timeout_error(self):
        """Test timeout error creation."""
        error = NotionTimeoutError("Request took too long")
        
        assert error.code == "NOTION_TIMEOUT"
        assert error.category == NotionSyncErrorCategory.TIMEOUT_ERROR
        assert error.message == "Request took too long"
        assert error.retryable is True


class TestNotionValidationError:
    """Test suite for NotionValidationError."""

    def test_validation_error_with_field(self):
        """Test validation error with field specified."""
        error = NotionValidationError(
            message="Invalid value",
            field="category",
            suggestion="Use Music, SFX, or VFX"
        )
        
        assert error.code == "NOTION_VALIDATION_ERROR"
        assert error.field == "category"
        assert error.retryable is False
    
    def test_validation_error_without_field(self):
        """Test validation error without field."""
        error = NotionValidationError("Data format invalid")
        
        assert error.field is None


class TestErrorClassification:
    """Test suite for error classification function."""

    def test_classify_rate_limit_error(self):
        """Test classifying rate limit errors."""
        original = Exception("Rate limit exceeded, try again later (429)")
        classified = classify_notion_error(original)
        
        assert isinstance(classified, NotionRateLimitError)
        assert classified.code == "NOTION_RATE_LIMIT"
    
    def test_classify_auth_error(self):
        """Test classifying authentication errors."""
        original = Exception("Unauthorized: invalid token provided")
        classified = classify_notion_error(original)
        
        assert isinstance(classified, NotionAuthError)
        assert classified.code == "NOTION_AUTH_FAILED"
    
    def test_classify_not_found_error(self):
        """Test classifying not found errors."""
        original = Exception("Page not found (404)")
        classified = classify_notion_error(original)
        
        assert isinstance(classified, NotionAPIError)
        assert classified.status_code == 404
    
    def test_classify_network_error(self):
        """Test classifying network errors."""
        original = Exception("Network unreachable")
        classified = classify_notion_error(original)
        
        assert isinstance(classified, NotionNetworkError)
    
    def test_classify_timeout_error(self):
        """Test classifying timeout errors."""
        original = Exception("Connection timeout")
        classified = classify_notion_error(original)
        
        assert isinstance(classified, NotionTimeoutError)
    
    def test_classify_with_status_attribute(self):
        """Test classifying error with status attribute."""
        original = MagicMock()
        original.status = 500
        original.__str__ = MagicMock(return_value="Server error")
        
        classified = classify_notion_error(original)
        
        assert isinstance(classified, NotionAPIError)
        assert classified.status_code == 500
    
    def test_classify_unknown_error(self):
        """Test classifying unknown errors."""
        original = Exception("Something unexpected happened")
        classified = classify_notion_error(original)
        
        assert isinstance(classified, NotionAPIError)
        assert classified.code == "NOTION_API_ERROR"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
