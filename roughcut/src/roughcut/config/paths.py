"""Path resolution utilities for cross-platform configuration storage.

Provides platform-appropriate paths for configuration files following
XDG and OS-specific conventions.
"""

import os
import platform
from pathlib import Path


def get_config_dir() -> Path:
    """Get the configuration directory for the current platform.
    
    Returns:
        Path to the platform-appropriate configuration directory
        
    Platform paths:
        - macOS: ~/Library/Application Support/RoughCut/
        - Windows: %APPDATA%/RoughCut/
        - Linux/Unix: ~/.config/roughcut/
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        config_dir = Path.home() / "Library" / "Application Support" / "RoughCut"
    elif system == "Windows":
        app_data = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
        config_dir = Path(app_data) / "RoughCut"
    else:  # Linux and other Unix
        # Check XDG_CONFIG_HOME first
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            config_dir = Path(xdg_config) / "roughcut"
        else:
            config_dir = Path.home() / ".config" / "roughcut"
    
    return config_dir


def get_config_file_path() -> Path:
    """Get the full path to the main configuration file.
    
    Returns:
        Path to config.json in the configuration directory
    """
    return get_config_dir() / "config.json"


def get_key_file_path() -> Path:
    """Get the full path to the encryption key file.
    
    Returns:
        Path to .encryption_key in the configuration directory
    """
    return get_config_dir() / ".encryption_key"


def ensure_config_dir() -> Path:
    """Ensure the configuration directory exists with proper permissions.
    
    Returns:
        Path to the configuration directory
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Set restrictive permissions on Unix-like systems
    if os.name != "nt":
        import stat
        config_dir.chmod(stat.S_IRWXU)  # 0o700 - user read/write/execute only
    
    return config_dir
