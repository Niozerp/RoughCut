"""Configuration data models.

Defines dataclasses for configuration sections with validation,
serialization, and encryption support.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class NotionConfig:
    """Configuration for Notion integration.
    
    Attributes:
        api_token: Notion API integration token (stored encrypted in file)
        page_url: URL of the Notion page for media database sync
        enabled: Whether Notion integration is enabled
        last_updated: Timestamp of last configuration update
        last_validation_result: Last validation result (optional)
        connection_status: Connection status from last validation
    """
    api_token: Optional[str] = None
    page_url: Optional[str] = None
    enabled: bool = False
    last_updated: datetime = field(default_factory=datetime.now)
    last_validation_result: Optional['ValidationResult'] = None
    connection_status: Optional[str] = None
    
    def validate(self) -> tuple[bool, str]:
        """Validate configuration fields.
        
        Returns:
            Tuple of (is_valid, error_message)
            is_valid is True if configuration is valid, False otherwise
            error_message is empty string if valid, otherwise contains error details
        """
        # Validate API token if provided
        if self.api_token is not None:
            # Check maximum length to prevent memory exhaustion attacks
            if len(self.api_token) > 512:
                return False, "API token is too long (maximum 512 characters)"
            
            if len(self.api_token) < 10:
                return False, "API token appears invalid (too short, should be at least 10 characters)"
            
            # Notion tokens typically start with "secret_"
            if not self.api_token.startswith("secret_") and len(self.api_token) < 20:
                return False, "API token format appears invalid (Notion tokens usually start with 'secret_')"
        
        # Validate page URL if provided
        if self.page_url:
            # Check maximum length to prevent memory exhaustion attacks
            if len(self.page_url) > 2048:
                return False, "Page URL is too long (maximum 2048 characters)"
            
            notion_url_pattern = r'^https://([a-zA-Z0-9_-]+\.)?notion\.so/.*$'
            if not re.match(notion_url_pattern, self.page_url):
                return False, "Invalid Notion page URL format (must be https://*.notion.so/...)"
            
            # Additional validation: URL should contain a page identifier
            # Notion URLs typically have a long alphanumeric string at the end
            if "-" not in self.page_url and len(self.page_url) < 40:
                return False, "Notion URL appears incomplete (should contain page ID)"
        
        return True, ""
    
    def is_configured(self) -> bool:
        """Check if Notion is properly configured.
        
        Returns:
            True if both API token and page URL are set and non-empty
        """
        return (
            self.enabled and
            self.api_token is not None and
            len(self.api_token) > 0 and
            self.page_url is not None and
            len(self.page_url) > 0
        )
    
    def to_dict(self, encrypt_token: bool = True) -> dict:
        """Convert to dictionary for JSON serialization.
        
        Args:
            encrypt_token: Whether to encrypt the API token
            
        Returns:
            Dictionary representation of the configuration
        """
        from .crypto import encrypt_value
        
        result = {
            'page_url': self.page_url,
            'enabled': self.enabled,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'connection_status': self.connection_status
        }
        
        # Include last validation result if present
        if self.last_validation_result:
            result['last_validation_result'] = self.last_validation_result.to_dict()
        else:
            result['last_validation_result'] = None
        
        # Encrypt API token if requested and present
        if self.api_token:
            if encrypt_token:
                try:
                    result['api_token'] = encrypt_value(self.api_token)
                except Exception:
                    # If encryption fails, don't include the token
                    result['api_token'] = None
            else:
                result['api_token'] = self.api_token
        else:
            result['api_token'] = None
        
        return result
    
    @classmethod
    def from_dict(cls, data: dict, decrypt_token: bool = True) -> 'NotionConfig':
        """Create NotionConfig from dictionary.
        
        Args:
            data: Dictionary containing configuration data
            decrypt_token: Whether to decrypt the API token
            
        Returns:
            NotionConfig instance
        """
        from .crypto import decrypt_value
        
        token = data.get('api_token')
        if decrypt_token and token:
            try:
                token = decrypt_value(token)
            except Exception:
                # If decryption fails, treat as unconfigured
                token = None
        
        # Parse last_updated
        last_updated_str = data.get('last_updated')
        last_updated = None
        if last_updated_str:
            try:
                last_updated = datetime.fromisoformat(last_updated_str)
            except ValueError:
                last_updated = datetime.now()
        
        if last_updated is None:
            last_updated = datetime.now()
        
        # Parse last validation result if present
        last_validation_result = None
        validation_data = data.get('last_validation_result')
        if validation_data:
            try:
                from ..backend.notion.models import ValidationResult
                last_validation_result = ValidationResult.from_dict(validation_data)
            except Exception:
                # If parsing fails, ignore the validation result
                last_validation_result = None
        
        return cls(
            api_token=token,
            page_url=data.get('page_url'),
            enabled=data.get('enabled', False),
            last_updated=last_updated,
            last_validation_result=last_validation_result,
            connection_status=data.get('connection_status')
        )
    
    def mask_token(self) -> str:
        """Return a masked representation of the API token for display.
        
        Returns:
            Masked token string (e.g., "sec***1234")
        """
        if not self.api_token:
            return ""
        
        if len(self.api_token) <= 8:
            return "***"
        
        # Show first 3 and last 4 characters, mask the rest
        return self.api_token[:3] + "***" + self.api_token[-4:]


@dataclass
class AIConfig:
    """Configuration for AI services (OpenAI).
    
    Attributes:
        api_key: OpenAI API key (stored encrypted in file)
        model: Model to use for tag generation (default: gpt-3.5-turbo)
        enabled: Whether AI tagging is enabled
        timeout: API timeout in seconds (default: 30)
        max_retries: Max retry attempts for rate limits (default: 3)
    """
    api_key: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    enabled: bool = False
    timeout: float = 30.0
    max_retries: int = 3
    
    def validate(self) -> tuple[bool, str]:
        """Validate configuration fields.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.enabled:
            return True, ""
        
        if not self.api_key:
            return False, "API key is required when AI is enabled"
        
        if len(self.api_key) < 20:
            return False, "API key appears invalid (too short)"
        
        # OpenAI keys typically start with "sk-"
        if not self.api_key.startswith("sk-"):
            return False, "API key format appears invalid (OpenAI keys start with 'sk-')"
        
        if self.timeout < 5 or self.timeout > 300:
            return False, "Timeout must be between 5 and 300 seconds"
        
        if self.max_retries < 0 or self.max_retries > 10:
            return False, "Max retries must be between 0 and 10"
        
        return True, ""
    
    def is_configured(self) -> bool:
        """Check if AI is properly configured.
        
        Returns:
            True if AI service is enabled and has API key
        """
        return self.enabled and self.api_key is not None and len(self.api_key) > 0
    
    def to_dict(self, encrypt_token: bool = True) -> dict:
        """Convert to dictionary for JSON serialization.
        
        Args:
            encrypt_token: Whether to encrypt the API key
            
        Returns:
            Dictionary representation of the configuration
        """
        from .crypto import encrypt_value
        
        result = {
            'model': self.model,
            'enabled': self.enabled,
            'timeout': self.timeout,
            'max_retries': self.max_retries
        }
        
        # Encrypt API key if requested and present
        if self.api_key:
            if encrypt_token:
                try:
                    result['api_key'] = encrypt_value(self.api_key)
                except Exception:
                    result['api_key'] = None
            else:
                result['api_key'] = self.api_key
        else:
            result['api_key'] = None
        
        return result
    
    @classmethod
    def from_dict(cls, data: dict, decrypt_token: bool = True) -> 'AIConfig':
        """Create AIConfig from dictionary.
        
        Args:
            data: Dictionary containing configuration data
            decrypt_token: Whether to decrypt the API key
            
        Returns:
            AIConfig instance
        """
        from .crypto import decrypt_value
        
        key = data.get('api_key')
        if decrypt_token and key:
            try:
                key = decrypt_value(key)
            except Exception:
                key = None
        
        return cls(
            api_key=key,
            model=data.get('model', 'gpt-3.5-turbo'),
            enabled=data.get('enabled', False),
            timeout=data.get('timeout', 30.0),
            max_retries=data.get('max_retries', 3)
        )
    
    def mask_key(self) -> str:
        """Return a masked representation of the API key for display.
        
        Returns:
            Masked key string (e.g., "sk-***1234")
        """
        if not self.api_key:
            return ""
        
        if len(self.api_key) <= 12:
            return "***"
        
        # Show first 5 and last 4 characters, mask the rest
        return self.api_key[:5] + "***" + self.api_key[-4:]


@dataclass
class AppConfig:
    """Root application configuration container.
    
    Attributes:
        notion: Notion integration configuration
        ai: AI service configuration
        version: Configuration format version
    """
    notion: NotionConfig = field(default_factory=NotionConfig)
    ai: 'AIConfig' = field(default_factory=lambda: AIConfig())
    version: str = "1.0"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'version': self.version,
            'notion': self.notion.to_dict(encrypt_token=True),
            'ai': self.ai.to_dict(encrypt_token=True)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AppConfig':
        """Create AppConfig from dictionary."""
        notion_data = data.get('notion', {})
        notion_config = NotionConfig.from_dict(notion_data, decrypt_token=True)
        
        ai_data = data.get('ai', {})
        ai_config = AIConfig.from_dict(ai_data, decrypt_token=True)
        
        return cls(
            notion=notion_config,
            ai=ai_config,
            version=data.get('version', '1.0')
        )
