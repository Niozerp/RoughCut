"""Notion API data models.

Defines dataclasses for Notion API operations including validation
results, connection status, and data transfer objects.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional


class ConnectionStatus(Enum):
    """Connection status enum for Notion integration.
    
    Values:
        CONNECTED: Connection validated successfully
        DISCONNECTED: Connection failed validation
        NOT_CONFIGURED: Notion integration not configured
        ERROR: Unexpected error during validation
    """
    CONNECTED = auto()
    DISCONNECTED = auto()
    NOT_CONFIGURED = auto()
    ERROR = auto()
    
    def __str__(self) -> str:
        """Return human-readable status string."""
        status_map = {
            ConnectionStatus.CONNECTED: "Connected",
            ConnectionStatus.DISCONNECTED: "Disconnected",
            ConnectionStatus.NOT_CONFIGURED: "Not Configured",
            ConnectionStatus.ERROR: "Error"
        }
        return status_map.get(self, "Unknown")


class ErrorType(Enum):
    """Error type classification for Notion validation failures.
    
    Values:
        AUTHENTICATION: Invalid API token or authentication failed
        PAGE_NOT_FOUND: Page URL is invalid or not accessible
        NETWORK: Network connectivity issues
        TIMEOUT: Connection timed out
        UNKNOWN: Unclassified error
    """
    AUTHENTICATION = auto()
    PAGE_NOT_FOUND = auto()
    NETWORK = auto()
    TIMEOUT = auto()
    UNKNOWN = auto()
    
    def __str__(self) -> str:
        """Return human-readable error type string."""
        error_map = {
            ErrorType.AUTHENTICATION: "Authentication Error",
            ErrorType.PAGE_NOT_FOUND: "Page Not Found",
            ErrorType.NETWORK: "Network Error",
            ErrorType.TIMEOUT: "Connection Timeout",
            ErrorType.UNKNOWN: "Unknown Error"
        }
        return error_map.get(self, "Unknown Error")


@dataclass
class ValidationResult:
    """Result of Notion connection validation.
    
    Attributes:
        valid: Whether the connection is valid
        status: Connection status enum value
        error_type: Type of error (if validation failed)
        error_message: Human-readable error message
        suggestion: Actionable guidance for user
        timestamp: When validation was performed
        last_successful: Timestamp of last successful validation (if any)
    """
    valid: bool = False
    status: ConnectionStatus = ConnectionStatus.NOT_CONFIGURED
    error_type: Optional[ErrorType] = None
    error_message: str = ""
    suggestion: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    last_successful: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the validation result
        """
        return {
            'valid': self.valid,
            'status': self.status.name if self.status else None,
            'error_type': self.error_type.name if self.error_type else None,
            'error_message': self.error_message,
            'suggestion': self.suggestion,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'last_successful': self.last_successful.isoformat() if self.last_successful else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ValidationResult':
        """Create ValidationResult from dictionary.
        
        Args:
            data: Dictionary containing validation result data
            
        Returns:
            ValidationResult instance
        """
        # Parse status
        status_name = data.get('status')
        status = None
        if status_name:
            try:
                status = ConnectionStatus[status_name]
            except KeyError:
                status = ConnectionStatus.ERROR
        
        # Parse error type
        error_type_name = data.get('error_type')
        error_type = None
        if error_type_name:
            try:
                error_type = ErrorType[error_type_name]
            except KeyError:
                error_type = ErrorType.UNKNOWN
        
        # Parse timestamps
        timestamp = None
        timestamp_str = data.get('timestamp')
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError:
                timestamp = datetime.now()
        
        last_successful = None
        last_successful_str = data.get('last_successful')
        if last_successful_str:
            try:
                last_successful = datetime.fromisoformat(last_successful_str)
            except ValueError:
                last_successful = None
        
        return cls(
            valid=data.get('valid', False),
            status=status or ConnectionStatus.ERROR,
            error_type=error_type,
            error_message=data.get('error_message', ''),
            suggestion=data.get('suggestion', ''),
            timestamp=timestamp or datetime.now(),
            last_successful=last_successful
        )
    
    def is_success(self) -> bool:
        """Check if validation was successful.
        
        Returns:
            True if connection is valid
        """
        return self.valid and self.status == ConnectionStatus.CONNECTED


@dataclass
class NotionPage:
    """Represents a Notion page for sync operations.
    
    Attributes:
        id: Notion page ID
        url: Full Notion page URL
        title: Page title (if available)
        last_edited: Last edited timestamp
    """
    id: str
    url: str
    title: Optional[str] = None
    last_edited: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'last_edited': self.last_edited.isoformat() if self.last_edited else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NotionPage':
        """Create NotionPage from dictionary."""
        last_edited = None
        last_edited_str = data.get('last_edited')
        if last_edited_str:
            try:
                last_edited = datetime.fromisoformat(last_edited_str)
            except ValueError:
                last_edited = None
        
        return cls(
            id=data.get('id', ''),
            url=data.get('url', ''),
            title=data.get('title'),
            last_edited=last_edited
        )


@dataclass
class SyncResult:
    """Result of a Notion sync operation.
    
    Attributes:
        success: Whether sync was successful
        synced_count: Number of items synced
        error_message: Error message if sync failed
        timestamp: When sync was performed
    """
    success: bool = False
    synced_count: int = 0
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'success': self.success,
            'synced_count': self.synced_count,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
