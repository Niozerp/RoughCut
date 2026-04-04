"""Configuration management for RoughCut.

Provides ConfigManager class for loading, saving, and managing
application configuration with secure credential storage.
"""

import fcntl
import json
import os
from pathlib import Path
from typing import Optional, Tuple

from .models import NotionConfig, AppConfig, AIConfig
from .paths import get_config_file_path, ensure_config_dir


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
                # Acquire shared lock for reading (non-blocking)
                if os.name != 'nt':  # Unix-like systems
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                    except (IOError, OSError):
                        # If lock cannot be acquired immediately, wait for it
                        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                
                try:
                    return json.load(f)
                finally:
                    # Release lock
                    if os.name != 'nt':
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                        
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
            if self._config_path.exists():
                backup_path = self._config_path.with_suffix('.json.backup')
                try:
                    import shutil
                    shutil.copy2(self._config_path, backup_path)
                except Exception as e:
                    print(f"Warning: Could not create config backup: {e}")
            
            # Write configuration with exclusive lock
            with open(self._config_path, 'w', encoding='utf-8') as f:
                # Acquire exclusive lock for writing (non-blocking)
                if os.name != 'nt':  # Unix-like systems
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except (IOError, OSError):
                        # If lock cannot be acquired immediately, wait for it
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                
                try:
                    json.dump(self._config_data, f, indent=2)
                finally:
                    # Release lock
                    if os.name != 'nt':
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # Set restrictive permissions (user read/write only)
            if os.name != "nt":  # Unix-like systems
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
        api_key: str,
        enabled: bool = True,
        model: str = "gpt-3.5-turbo",
        timeout: float = 30.0,
        max_retries: int = 3
    ) -> tuple[bool, str]:
        """Save AI configuration.
        
        Args:
            api_key: OpenAI API key
            enabled: Whether AI tagging is enabled
            model: Model to use for tag generation
            timeout: API timeout in seconds
            max_retries: Max retry attempts
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Create config object for validation
        config = AIConfig(
            api_key=api_key.strip() if api_key else None,
            model=model,
            enabled=enabled,
            timeout=timeout,
            max_retries=max_retries
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
    
    def save_validation_result(self, validation_result) -> bool:
        """Save the last validation result to configuration.
        
        Args:
            validation_result: ValidationResult instance to save
            
        Returns:
            True if save was successful, False otherwise
        """
        from .models import NotionConfig
        
        # Get current notion config
        notion_config = self.get_notion_config()
        
        # Update with validation result
        notion_config.last_validation_result = validation_result
        if validation_result and validation_result.status:
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
