"""Configuration management for RoughCut.

Provides ConfigManager class for loading, saving, and managing
application configuration with secure credential storage.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Tuple

from .models import NotionConfig, AppConfig, AIConfig, MediaFolderConfig
from .paths import get_config_file_path, ensure_config_dir

# Conditional import for file locking
if os.name != 'nt':
    import fcntl
else:
    fcntl = None
    import msvcrt
    import ctypes
    from ctypes import wintypes
    
    # Define OVERLAPPED structure for Windows file locking
    class _OVERLAPPED(ctypes.Structure):
        _fields_ = [
            ('Internal', ctypes.c_ulonglong),
            ('InternalHigh', ctypes.c_ulonglong),
            ('Offset', wintypes.DWORD),
            ('OffsetHigh', wintypes.DWORD),
            ('hEvent', wintypes.HANDLE)
        ]
    
    def _lock_file_windows(handle, exclusive=True):
        """Lock file on Windows using LockFileEx.
        
        Args:
            handle: File handle
            exclusive: True for exclusive lock, False for shared
        """
        LOCKFILE_EXCLUSIVE_LOCK = 0x00000002
        LOCKFILE_FAIL_IMMEDIATELY = 0x00000001
        
        overlapped = _OVERLAPPED()
        flags = LOCKFILE_FAIL_IMMEDIATELY
        if exclusive:
            flags |= LOCKFILE_EXCLUSIVE_LOCK
        
        # Lock the entire file (max range)
        kernel32 = ctypes.windll.kernel32
        success = kernel32.LockFileEx(
            handle,
            flags,
            0, 0, 0xFFFFFFFF, 0xFFFFFFFF,
            ctypes.byref(overlapped)
        )
        return success != 0
    
    def _unlock_file_windows(handle):
        """Unlock file on Windows."""
        overlapped = _OVERLAPPED()
        kernel32 = ctypes.windll.kernel32
        success = kernel32.UnlockFileEx(
            handle, 0, 0xFFFFFFFF, 0xFFFFFFFF,
            ctypes.byref(overlapped)
        )
        return success != 0


class ConfigManager:
    """Manages application configuration with encryption support.
    
    This class handles loading and saving configuration to disk,
    with automatic encryption of sensitive fields like API tokens.
    
    Usage:
        config = ConfigManager()
        
        # Save Notion configuration
        success, message = config.save_notion_config(
            api_token="secret_xxx",
            page_url="https://notion.so/..."
        )
        
        # Check if configured
        if config.is_notion_configured():
            notion_config = config.get_notion_config()
    """
    
    _instance: Optional['ConfigManager'] = None
    
    def __new__(cls):
        """Singleton pattern to ensure single ConfigManager instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the configuration manager."""
        if self._initialized:
            return
        
        self._config_path = get_config_file_path()
        self._config_data = self._load()
        self._initialized = True
    
    def _load(self) -> dict:
        """Load configuration from disk with file locking.
        
        Returns:
            Dictionary containing configuration data
        """
        if not self._config_path.exists():
            return {}
        
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                # Acquire shared lock BEFORE reading on Unix
                if fcntl:
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                    except (IOError, OSError):
                        # If lock cannot be acquired immediately, wait for it
                        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                elif os.name == 'nt':
                    # Windows: acquire shared lock using Windows API
                    try:
                        _lock_file_windows(msvcrt.get_osfhandle(f.fileno()), exclusive=False)
                    except Exception:
                        # If locking fails, continue without lock
                        pass
                
                try:
                    content = f.read().strip()
                    if not content:
                        return {}
                    return json.loads(content)
                finally:
                    # Release lock on Unix
                    if fcntl:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    elif os.name == 'nt':
                        # Windows: release lock
                        try:
                            _unlock_file_windows(msvcrt.get_osfhandle(f.fileno()))
                        except Exception:
                            pass
                        
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load config file: {e}")
            return {}
    
    def _save(self) -> bool:
        """Save configuration to disk with file locking and backup.
        
        Returns:
            True if save was successful, False otherwise
        """
        try:
            # Ensure directory exists
            ensure_config_dir()
            
            # Create backup of existing config if it exists
            backup_created = False
            if self._config_path.exists():
                backup_path = self._config_path.with_suffix('.json.backup')
                try:
                    import shutil
                    shutil.copy2(self._config_path, backup_path)
                    backup_created = True
                except Exception as e:
                    print(f"Warning: Could not create config backup: {e}")
                    # Continue without backup - don't block automation with interactive prompts
                    # In production environments, backups may not be possible (e.g., read-only filesystems)
            
            # Write configuration with exclusive lock
            with open(self._config_path, 'w', encoding='utf-8') as f:
                # Acquire exclusive lock for writing (non-blocking) on Unix
                if fcntl:
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except (IOError, OSError):
                        # If lock cannot be acquired immediately, wait for it
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                elif os.name == 'nt':
                    # Windows: acquire exclusive lock using Windows API
                    try:
                        _lock_file_windows(msvcrt.get_osfhandle(f.fileno()), exclusive=True)
                    except Exception:
                        # If locking fails, continue without lock
                        pass
                
                try:
                    json.dump(self._config_data, f, indent=2, default=str)
                finally:
                    # Release lock on Unix
                    if fcntl:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    elif os.name == 'nt':
                        # Windows: release lock
                        try:
                            _unlock_file_windows(msvcrt.get_osfhandle(f.fileno()))
                        except Exception:
                            pass
            
            # Set restrictive permissions (user read/write only) on Unix
            if os.name != "nt":
                os.chmod(self._config_path, 0o600)
            
            return True
        except (IOError, OSError) as e:
            print(f"Error: Failed to save config file: {e}")
            return False
    
    def get_notion_config(self) -> NotionConfig:
        """Get current Notion configuration.
        
        Returns:
            NotionConfig instance with current settings
        """
        notion_data = self._config_data.get('notion', {})
        return NotionConfig.from_dict(notion_data) if notion_data else NotionConfig()
    
    def save_notion_config(
        self, 
        api_token: str, 
        page_url: str
    ) -> Tuple[bool, str]:
        """Save Notion configuration.
        
        Args:
            api_token: Notion API integration token
            page_url: Notion page URL for media database
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Validate inputs
        if not api_token or not api_token.strip():
            return False, "API token is required"
        
        if not page_url or not page_url.strip():
            return False, "Page URL is required"
        
        # Create config object for validation
        config = NotionConfig(
            api_token=api_token.strip(),
            page_url=page_url.strip(),
            enabled=True
        )
        
        # Validate configuration
        is_valid, error = config.validate()
        if not is_valid:
            return False, error
        
        # Save to config data
        self._config_data['notion'] = config.to_dict(encrypt_token=True)
        
        # Persist to disk
        if self._save():
            return True, "Configuration saved successfully"
        else:
            return False, "Failed to save configuration to disk"
    
    def clear_notion_config(self) -> Tuple[bool, str]:
        """Clear Notion configuration.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if 'notion' in self._config_data:
            del self._config_data['notion']
        
        if self._save():
            return True, "Configuration cleared successfully"
        else:
            return False, "Failed to clear configuration"
    
    def is_notion_configured(self) -> bool:
        """Check if Notion is properly configured.
        
        Returns:
            True if Notion integration is configured and enabled
        """
        notion_config = self.get_notion_config()
        return notion_config.is_configured()
    
    def get_ai_config(self):
        """Get current AI configuration.
        
        Returns:
            AIConfig instance with current settings
        """
        ai_data = self._config_data.get('ai', {})
        return AIConfig.from_dict(ai_data) if ai_data else AIConfig()
    
    def save_ai_config(
        self,
        api_key: Optional[str],
        enabled: bool = True,
        model: str = "gpt-3.5-turbo",
        timeout: float = 30.0,
        max_retries: int = 3,
        recovery_mode: str = "automatic"
    ) -> tuple[bool, str]:
        """Save AI configuration.
        
        Args:
            api_key: OpenAI API key
            enabled: Whether AI tagging is enabled
            model: Model to use for tag generation
            timeout: API timeout in seconds
            max_retries: Max retry attempts
            recovery_mode: Error recovery mode ("automatic" or "manual")
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Validate api_key is string type
        if api_key is not None and not isinstance(api_key, str):
            return False, "API key must be a string"
        
        # Create config object for validation
        config = AIConfig(
            api_key=api_key.strip() if api_key else None,
            model=model,
            enabled=enabled,
            timeout=timeout,
            max_retries=max_retries,
            recovery_mode=recovery_mode
        )
        
        # Validate configuration
        is_valid, error = config.validate()
        if not is_valid:
            return False, error
        
        # Save to config data
        self._config_data['ai'] = config.to_dict(encrypt_token=True)
        
        # Persist to disk
        if self._save():
            return True, "AI configuration saved successfully"
        else:
            return False, "Failed to save AI configuration to disk"
    
    def clear_ai_config(self) -> tuple[bool, str]:
        """Clear AI configuration.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if 'ai' in self._config_data:
            del self._config_data['ai']
        
        if self._save():
            return True, "AI configuration cleared successfully"
        else:
            return False, "Failed to clear AI configuration"
    
    def is_ai_configured(self) -> bool:
        """Check if AI is properly configured.
        
        Returns:
            True if AI service is configured and enabled
        """
        ai_config = self.get_ai_config()
        return ai_config.is_configured()
    
    def get_media_folders_config(self) -> MediaFolderConfig:
        """Get current media folders configuration.
        
        Returns:
            MediaFolderConfig instance with current settings
        """
        media_data = self._config_data.get('media_folders', {})
        return MediaFolderConfig.from_dict(media_data) if media_data else MediaFolderConfig()
    
    def save_media_folders_config(
        self,
        music_folder: Optional[str] = None,
        sfx_folder: Optional[str] = None,
        vfx_folder: Optional[str] = None
    ) -> tuple[bool, str, dict[str, str]]:
        """Save media folders configuration.
        
        Args:
            music_folder: Absolute path to Music assets folder (optional)
            sfx_folder: Absolute path to SFX assets folder (optional)
            vfx_folder: Absolute path to VFX assets folder (optional)
            
        Returns:
            Tuple of (success: bool, message: str, errors: dict)
            errors contains validation errors by category (empty if all valid)
        """
        # Create config object for validation
        # Normalize empty/whitespace-only strings to None
        def normalize_path(path: Optional[str]) -> Optional[str]:
            if path is None:
                return None
            if not isinstance(path, str):
                return None
            stripped = path.strip()
            return stripped if stripped else None
        
        config = MediaFolderConfig(
            music_folder=normalize_path(music_folder),
            sfx_folder=normalize_path(sfx_folder),
            vfx_folder=normalize_path(vfx_folder)
        )
        
        # Validate configuration
        errors = config.validate()
        if errors:
            error_msg = "; ".join([f"{k}: {v}" for k, v in errors.items()])
            return False, f"Validation failed: {error_msg}", errors
        
        # Save to config data
        self._config_data['media_folders'] = config.to_dict()
        
        # Persist to disk
        if self._save():
            return True, "Media folder configuration saved successfully", {}
        else:
            return False, "Failed to save media folder configuration to disk", {}
    
    def clear_media_folders_config(self) -> tuple[bool, str]:
        """Clear media folders configuration.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if 'media_folders' in self._config_data:
            del self._config_data['media_folders']
        
        if self._save():
            return True, "Media folder configuration cleared successfully"
        else:
            return False, "Failed to clear media folder configuration"
    
    def is_media_folders_configured(self) -> bool:
        """Check if media folders are configured.
        
        Returns:
            True if at least one media folder is configured
        """
        media_config = self.get_media_folders_config()
        return media_config.is_configured()
    
    def get_spacetime_config(self) -> dict:
        """Get SpacetimeDB configuration.
        
        Returns:
            Dictionary with SpacetimeDB settings. Identity token is decrypted.
        """
        from .crypto import decrypt_value
        
        config = self._config_data.get('spacetime', {
            'host': 'localhost',
            'port': 3000,
            'database_name': 'roughcut',
            'identity_token': None,
            'module_path': None
        }).copy()
        
        # Decrypt identity token if present
        encrypted_token = config.get('identity_token')
        if encrypted_token:
            try:
                config['identity_token'] = decrypt_value(encrypted_token)
                config['_token_decryption_failed'] = False
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to decrypt SpacetimeDB identity token: {e}")
                # Keep the encrypted token so caller can distinguish "decryption failed" 
                # from "no token configured". Caller can check _token_decryption_failed flag.
                config['_token_decryption_failed'] = True
                config['_token_decryption_error'] = str(e)
        
        return config
    
    def save_spacetime_config(
        self,
        host: str = 'localhost',
        port: int = 3000,
        database_name: str = 'roughcut',
        identity_token: Optional[str] = None,
        module_path: Optional[str] = None
    ) -> tuple[bool, str]:
        """Save SpacetimeDB configuration.
        
        Args:
            host: SpacetimeDB server hostname
            port: SpacetimeDB server port
            database_name: Database/module name
            identity_token: Authentication token for RLS (will be encrypted)
            module_path: Path to compiled Rust module
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        import logging
        from .crypto import encrypt_value
        
        logger = logging.getLogger(__name__)
        
        # Validate inputs
        if not isinstance(host, str) or not host:
            return False, "Host must be a non-empty string"
        if not isinstance(port, int) or not (1 <= port <= 65535):
            return False, "Port must be an integer between 1 and 65535"
        if not isinstance(database_name, str) or not database_name:
            return False, "Database name must be a non-empty string"
        
        # Encrypt identity token if provided
        encrypted_token = None
        if identity_token:
            if not isinstance(identity_token, str):
                return False, "Identity token must be a string"
            try:
                encrypted_token = encrypt_value(identity_token)
            except Exception as e:
                logger.error(f"Failed to encrypt identity token: {e}")
                return False, f"Failed to encrypt identity token: {e}"
        
        # Store configuration with encrypted token
        self._config_data['spacetime'] = {
            'host': host,
            'port': port,
            'database_name': database_name,
            'identity_token': encrypted_token,  # Now encrypted per NFR6
            'module_path': module_path
        }
        
        if self._save():
            logger.info("SpacetimeDB configuration saved successfully with encrypted token")
            return True, "SpacetimeDB configuration saved successfully"
        else:
            return False, "Failed to save SpacetimeDB configuration"
    
    def clear_spacetime_config(self) -> tuple[bool, str]:
        """Clear SpacetimeDB configuration.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if 'spacetime' in self._config_data:
            del self._config_data['spacetime']
        
        if self._save():
            return True, "SpacetimeDB configuration cleared successfully"
        else:
            return False, "Failed to clear SpacetimeDB configuration"
    
    def is_spacetime_configured(self) -> bool:
        """Check if SpacetimeDB is configured.
        
        Returns:
            True if SpacetimeDB has minimal configuration
        """
        config = self.get_spacetime_config()
        return bool(config.get('host')) and bool(config.get('database_name'))
    
    def save_validation_result(self, validation_result) -> bool:
        """Save the last validation result to configuration.
        
        Args:
            validation_result: ValidationResult instance to save
            
        Returns:
            True if save was successful, False otherwise
        """
        from .models import NotionConfig
        
        # Handle None validation_result
        if validation_result is None:
            return False
        
        # Get current notion config
        notion_config = self.get_notion_config()
        
        # Update with validation result
        notion_config.last_validation_result = validation_result
        if validation_result.status:
            notion_config.connection_status = validation_result.status.name
        
        # Save back to config data
        self._config_data['notion'] = notion_config.to_dict(encrypt_token=True)
        
        # Persist to disk
        return self._save()
    
    def get_last_validation_result(self):
        """Get the last validation result.
        
        Returns:
            ValidationResult instance or None if not available
        """
        from ..backend.notion.models import ValidationResult
        
        notion_config = self.get_notion_config()
        return notion_config.last_validation_result
    
    def get_full_config(self) -> AppConfig:
        """Get complete application configuration.
        
        Returns:
            AppConfig instance with all settings
        """
        return AppConfig.from_dict(self._config_data)
    
    def reload(self):
        """Reload configuration from disk.
        
        Useful for picking up external changes to the config file.
        """
        self._config_data = self._load()
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None


def get_config_manager() -> ConfigManager:
    """Get the singleton ConfigManager instance.
    
    Returns:
        ConfigManager singleton instance
    """
    return ConfigManager()


def get_settings() -> dict:
    """Get application settings as a simple dictionary.
    
    Convenience function for accessing configuration in a dict-like format.
    
    Returns:
        Dictionary with configuration values
    """
    config_manager = get_config_manager()
    
    settings = {}
    
    # Get AI config
    ai_config = config_manager.get_ai_config()
    if ai_config:
        settings["openai_api_key"] = ai_config.api_key
        settings["ai_enabled"] = ai_config.enabled
        settings["ai_model"] = ai_config.model
        settings["ai_timeout"] = ai_config.timeout
        settings["ai_max_retries"] = ai_config.max_retries
    
    # Get Notion config
    notion_config = config_manager.get_notion_config()
    if notion_config:
        settings["notion_api_token"] = notion_config.api_token
        settings["notion_page_url"] = notion_config.page_url
        settings["notion_enabled"] = notion_config.enabled
    
    # Get media folders config
    media_config = config_manager.get_media_folders_config()
    if media_config:
        settings["music_folder"] = media_config.music_folder
        settings["sfx_folder"] = media_config.sfx_folder
        settings["vfx_folder"] = media_config.vfx_folder
    
    return settings
