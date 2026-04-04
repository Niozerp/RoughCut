# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

#!/usr/bin/env python3
"""Structured error handling for AI services.

Provides AIError exception class with detailed error information
for handling AI service failures gracefully.
"""

from typing import Optional


class AIError(Exception):
    """Structured error for AI service failures.
    
    Attributes:
        code: Error code for programmatic handling
        category: Error category (e.g., "external_api", "timeout", "config")
        message: Human-readable error message
        recoverable: Whether the error can be recovered from
        suggestion: Actionable suggestion for resolving the error
    """
    
    def __init__(
        self,
        code: str,
        category: str,
        message: str,
        recoverable: bool,
        suggestion: str
    ):
        self.code = code
        self.category = category
        self.message = message
        self.recoverable = recoverable
        self.suggestion = suggestion
        super().__init__(message)
    
    def to_dict(self) -> dict:
        """Convert to dictionary format for JSON-RPC responses."""
        return {
            "code": self.code,
            "category": self.category,
            "message": self.message,
            "recoverable": self.recoverable,
            "suggestion": self.suggestion
        }
    
    def __repr__(self) -> str:
        return f"AIError(code={self.code}, category={self.category}, message={self.message})"


class AIConfigError(AIError):
    """Error for AI configuration issues."""
    
    def __init__(self, message: str, suggestion: str):
        super().__init__(
            code="AI_CONFIG_ERROR",
            category="config",
            message=message,
            recoverable=True,
            suggestion=suggestion
        )


class AIRateLimitError(AIError):
    """Error for AI API rate limiting."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        suggestion = f"Wait {retry_after}s before retrying" if retry_after else "Retry after a short delay"
        super().__init__(
            code="AI_RATE_LIMIT",
            category="external_api",
            message=message,
            recoverable=True,
            suggestion=suggestion
        )
        self.retry_after = retry_after
