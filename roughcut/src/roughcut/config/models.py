"""Configuration data models.

Defines dataclasses for configuration sections with validation,
serialization, and encryption support.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class NotionConfig:
    """Configuration for Notion integration.
    
    Attributes:
        api_token: Notion API integration token (stored encrypted in file)
        page_url: URL of the Notion page for media database sync
        enabled: Whether Notion integration is enabled
        sync_enabled: Whether automatic sync to Notion is enabled
        database_id: Notion database ID for media assets (created automatically)
        last_updated: Timestamp of last configuration update
        last_validation_result: Last validation result (optional)
        connection_status: Connection status from last validation
    """
    api_token: Optional[str] = None
    page_url: Optional[str] = None
    enabled: bool = False
    sync_enabled: bool = True  # Default to True when Notion is configured
    database_id: Optional[str] = None
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
        # Validate API token type and content if provided
        if self.api_token is not None:
            if not isinstance(self.api_token, str):
                return False, "API token must be a string"
            
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
            'sync_enabled': self.sync_enabled,
            'database_id': self.database_id,
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
                except Exception as e:
                    # Log warning and set to None if encryption fails
                    logger.warning(f"Failed to encrypt API token: {e}")
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
            sync_enabled=data.get('sync_enabled', True),
            database_id=data.get('database_id'),
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
class MediaFolderConfig:
    """Configuration for media category folders.
    
    Attributes:
        music_folder: Absolute path to Music assets parent folder
        sfx_folder: Absolute path to SFX assets parent folder
        vfx_folder: Absolute path to VFX assets parent folder
        last_updated: Timestamp of last configuration update
    """
    music_folder: Optional[str] = None
    sfx_folder: Optional[str] = None
    vfx_folder: Optional[str] = None
    last_updated: datetime = field(default_factory=datetime.now)
    
    def validate(self) -> dict[str, str]:
        """Validate all configured paths.
        
        Returns:
            Dictionary of errors by category (empty if all valid)
        """
        errors = {}
        from pathlib import Path
        
        # System directories that should not be used as media folders
        DANGEROUS_PATHS = {
            '/', '/bin', '/sbin', '/usr', '/etc', 
            '/sys', '/proc', '/dev', '/boot',
            'C:\\Windows', 'C:\\Program Files', 'C:\\Program Files (x86)',
            'C:\\System32', 'C:\\Users\\All Users'
        }
        
        for category, path_str in [
            ("music", self.music_folder),
            ("sfx", self.sfx_folder),
            ("vfx", self.vfx_folder)
        ]:
            if path_str is not None and path_str.strip():
                try:
                    # Check for path traversal sequences
                    if '..' in path_str:
                        errors[category] = "Path contains directory traversal sequences (..) which are not allowed"
                        continue
                    
                    # Check for null bytes
                    if '\x00' in path_str:
                        errors[category] = "Path contains invalid null characters"
                        continue
                    
                    path = Path(path_str)
                    resolved_path = path.resolve()
                    
                    # Check against dangerous system paths
                    path_str_normalized = str(resolved_path).rstrip('\\/')
                    for dangerous in DANGEROUS_PATHS:
                        if path_str_normalized.lower() == dangerous.lower().rstrip('\\/'):
                            errors[category] = f"System directory not allowed: {dangerous}"
                            break
                    else:
                        # No dangerous path match, continue validation
                        if not path.exists():
                            errors[category] = f"Path does not exist: {path}"
                        elif not path.is_dir():
                            errors[category] = f"Path is not a directory: {path}"
                        elif not path.is_absolute():
                            errors[category] = f"Path must be absolute: {path}"
                except Exception as e:
                    errors[category] = f"Invalid path format: {str(e)}"
        
        return errors
    
    def is_configured(self) -> bool:
        """Check if any media folders are configured.
        
        Returns:
            True if at least one folder path is set
        """
        return any([
            self.music_folder is not None and len(self.music_folder) > 0,
            self.sfx_folder is not None and len(self.sfx_folder) > 0,
            self.vfx_folder is not None and len(self.vfx_folder) > 0
        ])
    
    def get_configured_folders(self) -> dict[str, Optional[str]]:
        """Get dictionary of configured folder paths.
        
        Returns:
            Dictionary mapping category to path (or None if not set)
        """
        return {
            "music": self.music_folder,
            "sfx": self.sfx_folder,
            "vfx": self.vfx_folder
        }
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the configuration
        """
        return {
            'music_folder': self.music_folder,
            'sfx_folder': self.sfx_folder,
            'vfx_folder': self.vfx_folder,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MediaFolderConfig':
        """Create MediaFolderConfig from dictionary.
        
        Args:
            data: Dictionary containing configuration data
            
        Returns:
            MediaFolderConfig instance
        """
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
        
        return cls(
            music_folder=data.get('music_folder'),
            sfx_folder=data.get('sfx_folder'),
            vfx_folder=data.get('vfx_folder'),
            last_updated=last_updated
        )


@dataclass
class AIConfig:
    """Configuration for AI services (OpenAI, OpenRouter, etc.).
    
    Attributes:
        api_key: API key for the selected provider (stored encrypted in file)
        provider: AI provider to use - "openai" or "openrouter" (default: openai)
        base_url: Custom base URL for API calls (optional, mainly for OpenRouter)
        model: Model to use for AI requests (default: gpt-3.5-turbo for OpenAI)
        enabled: Whether AI tagging is enabled
        timeout: API timeout in seconds (default: 30)
        max_retries: Max retry attempts for rate limits (default: 3)
        recovery_mode: Error recovery mode - "automatic" or "manual" (default: automatic)
    """
    api_key: Optional[str] = None
    provider: str = "openai"  # "openai" or "openrouter"
    base_url: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    enabled: bool = False
    timeout: float = 30.0
    max_retries: int = 3
    recovery_mode: str = "automatic"  # "automatic" or "manual"
    
    # Default models by provider
    DEFAULT_OPENAI_MODEL = "gpt-3.5-turbo"
    DEFAULT_OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"
    
    # Provider base URLs
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    def __post_init__(self):
        """Post-initialization to set defaults based on provider."""
        if self.provider == "openrouter" and not self.base_url:
            self.base_url = self.OPENROUTER_BASE_URL
        
        # Set default model if not specified or incompatible with provider
        if self.provider == "openrouter" and "/" not in self.model:
            # Model doesn't have provider prefix, use default
            self.model = self.DEFAULT_OPENROUTER_MODEL
        elif self.provider == "openai" and "/" in self.model:
            # OpenRouter-style model for OpenAI provider, reset to default
            self.model = self.DEFAULT_OPENAI_MODEL
    
    def validate(self) -> tuple[bool, str]:
        """Validate configuration fields.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.enabled:
            return True, ""
        
        # Type check for api_key
        if self.api_key is not None and not isinstance(self.api_key, str):
            return False, "API key must be a string"
        
        if not self.api_key:
            return False, "API key is required when AI is enabled"
        
        if len(self.api_key) < 20:
            return False, "API key appears invalid (too short)"
        
        # Validate provider
        if self.provider not in ("openai", "openrouter"):
            return False, "Provider must be 'openai' or 'openrouter'"
        
        # Provider-specific API key validation
        if self.provider == "openai":
            # OpenAI keys typically start with "sk-"
            if not self.api_key.startswith("sk-"):
                return False, "API key format appears invalid (OpenAI keys start with 'sk-')"
        elif self.provider == "openrouter":
            # OpenRouter keys typically start with "sk-or-"
            if not self.api_key.startswith("sk-or-"):
                return False, "API key format appears invalid (OpenRouter keys start with 'sk-or-')"
        
        if self.timeout < 5 or self.timeout > 300:
            return False, "Timeout must be between 5 and 300 seconds"
        
        if self.max_retries < 0 or self.max_retries > 10:
            return False, "Max retries must be between 0 and 10"
        
        # Validate recovery_mode
        if self.recovery_mode not in ("automatic", "manual"):
            return False, "recovery_mode must be 'automatic' or 'manual'"
        
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
            'provider': self.provider,
            'base_url': self.base_url,
            'model': self.model,
            'enabled': self.enabled,
            'timeout': self.timeout,
            'max_retries': self.max_retries,
            'recovery_mode': self.recovery_mode
        }
        
        # Encrypt API key if requested and present
        if self.api_key:
            if encrypt_token:
                try:
                    result['api_key'] = encrypt_value(self.api_key)
                except Exception as e:
                    # Log warning if encryption fails
                    logger.warning(f"Failed to encrypt API key: {e}")
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
            provider=data.get('provider', 'openai'),
            base_url=data.get('base_url'),
            model=data.get('model', 'gpt-3.5-turbo'),
            enabled=data.get('enabled', False),
            timeout=data.get('timeout', 30.0),
            max_retries=data.get('max_retries', 3),
            recovery_mode=data.get('recovery_mode', 'automatic')
        )
    
    def mask_key(self) -> str:
        """Return a masked representation of the API key for display.
        
        Returns:
            Masked key string (e.g., "sk-***1234" or "sk-or-***1234")
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
        media_folders: Media folder configuration
        onboarding_completed: Whether first-run media setup is finished
        version: Configuration format version
    """
    notion: NotionConfig = field(default_factory=NotionConfig)
    ai: 'AIConfig' = field(default_factory=lambda: AIConfig())
    media_folders: MediaFolderConfig = field(default_factory=MediaFolderConfig)
    onboarding_completed: bool = False
    version: str = "1.0"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'version': self.version,
            'notion': self.notion.to_dict(encrypt_token=True),
            'ai': self.ai.to_dict(encrypt_token=True),
            'media_folders': self.media_folders.to_dict(),
            'onboarding_completed': self.onboarding_completed,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AppConfig':
        """Create AppConfig from dictionary."""
        notion_data = data.get('notion', {})
        notion_config = NotionConfig.from_dict(notion_data, decrypt_token=True)
        
        ai_data = data.get('ai', {})
        ai_config = AIConfig.from_dict(ai_data, decrypt_token=True)
        
        media_folders_data = data.get('media_folders', {})
        media_folders_config = MediaFolderConfig.from_dict(media_folders_data)
        
        return cls(
            notion=notion_config,
            ai=ai_config,
            media_folders=media_folders_config,
            onboarding_completed=data.get('onboarding_completed', False),
            version=data.get('version', '1.0')
        )
