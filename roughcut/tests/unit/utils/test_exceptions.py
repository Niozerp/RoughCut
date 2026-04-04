# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest"]
# ///

#!/usr/bin/env python3
"""Unit tests for AI exception classes."""

import pytest
from roughcut.utils.exceptions import AIError, AIConfigError, AIRateLimitError


class TestAIError:
    """Test AIError base class."""
    
    def test_basic_creation(self):
        """Test creating a basic AIError."""
        error = AIError(
            code="AI_TEST",
            category="test",
            message="Test error message",
            recoverable=True,
            suggestion="Try again"
        )
        
        assert error.code == "AI_TEST"
        assert error.category == "test"
        assert error.message == "Test error message"
        assert error.recoverable is True
        assert error.suggestion == "Try again"
        assert str(error) == "Test error message"
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        error = AIError(
            code="AI_TIMEOUT",
            category="external_api",
            message="Timeout occurred",
            recoverable=True,
            suggestion="Check connection"
        )
        
        result = error.to_dict()
        
        assert result["code"] == "AI_TIMEOUT"
        assert result["category"] == "external_api"
        assert result["message"] == "Timeout occurred"
        assert result["recoverable"] is True
        assert result["suggestion"] == "Check connection"
    
    def test_non_recoverable_error(self):
        """Test non-recoverable error."""
        error = AIError(
            code="AI_FATAL",
            category="internal",
            message="Fatal error",
            recoverable=False,
            suggestion="Contact support"
        )
        
        assert error.recoverable is False


class TestAIConfigError:
    """Test AIConfigError class."""
    
    def test_config_error_creation(self):
        """Test creating AIConfigError."""
        error = AIConfigError(
            message="Invalid API key",
            suggestion="Check your configuration"
        )
        
        assert error.code == "AI_CONFIG_ERROR"
        assert error.category == "config"
        assert error.message == "Invalid API key"
        assert error.recoverable is True
        assert error.suggestion == "Check your configuration"


class TestAIRateLimitError:
    """Test AIRateLimitError class."""
    
    def test_rate_limit_error_basic(self):
        """Test creating basic rate limit error."""
        error = AIRateLimitError()
        
        assert error.code == "AI_RATE_LIMIT"
        assert error.category == "external_api"
        assert "Rate limit" in error.message
        assert error.recoverable is True
        assert error.retry_after is None
    
    def test_rate_limit_error_with_retry(self):
        """Test rate limit error with retry time."""
        error = AIRateLimitError(
            message="Rate limit exceeded after retries",
            retry_after=60
        )
        
        assert error.retry_after == 60
        assert "Wait 60s" in error.suggestion
    
    def test_rate_limit_error_custom_message(self):
        """Test rate limit error with custom message."""
        error = AIRateLimitError(message="Too many requests")
        
        assert error.message == "Too many requests"
