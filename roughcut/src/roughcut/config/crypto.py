"""Cryptographic utilities for secure configuration storage.

Provides Fernet symmetric encryption for sensitive data like API tokens.
Follows NFR6 security requirements for encrypted storage.
"""

import base64
import os
import platform
from pathlib import Path

try:
    from cryptography.fernet import Fernet
except ImportError:
    # Handle missing cryptography gracefully
    Fernet = None


def get_config_dir() -> Path:
    """Get the configuration directory for the current platform."""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        config_dir = Path.home() / "Library" / "Application Support" / "RoughCut"
    elif system == "Windows":
        app_data = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
        config_dir = Path(app_data) / "RoughCut"
    else:  # Linux and other Unix
        config_dir = Path.home() / ".config" / "roughcut"
    
    return config_dir


def get_key_file_path() -> Path:
    """Get the full path to the encryption key file."""
    return get_config_dir() / ".encryption_key"


def get_or_create_key() -> bytes:
    """Get existing encryption key or generate a new one.
    
    Returns:
        32-byte encryption key
    
    Raises:
        RuntimeError: If cryptography library is not available
    """
    if Fernet is None:
        raise RuntimeError(
            "cryptography library is required for encryption. "
            "Install with: pip install cryptography"
        )
    
    key_path = get_key_file_path()
    
    if key_path.exists():
        # Read existing key
        with open(key_path, "rb") as f:
            encoded_key = f.read()
            return base64.urlsafe_b64decode(encoded_key)
    else:
        # Generate new key
        key = Fernet.generate_key()
        decoded_key = base64.urlsafe_b64decode(key)
        
        # Ensure directory exists with proper permissions
        key_path.parent.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":  # Unix-like systems
            os.chmod(key_path.parent, 0o700)
        
        # Store key with restricted permissions
        encoded_key = base64.urlsafe_b64encode(decoded_key)
        with open(key_path, "wb") as f:
            f.write(encoded_key)
        
        # Set file permissions (user read/write only)
        if os.name != "nt":  # Unix-like systems
            os.chmod(key_path, 0o600)
        else:  # Windows
            try:
                import ctypes
                from ctypes import wintypes
                
                # Make file hidden on Windows
                FILE_ATTRIBUTE_HIDDEN = 0x02
                kernel32 = ctypes.windll.kernel32
                kernel32.SetFileAttributesW(str(key_path), FILE_ATTRIBUTE_HIDDEN)
            except Exception:
                # If setting hidden attribute fails, continue anyway
                pass
        
        return decoded_key


def encrypt_value(value: str) -> str:
    """Encrypt a string value using Fernet symmetric encryption.
    
    Args:
        value: The plaintext string to encrypt
    
    Returns:
        URL-safe base64 encoded encrypted string
    
    Raises:
        RuntimeError: If cryptography library is not available
        ValueError: If encryption fails
    """
    if Fernet is None:
        raise RuntimeError(
            "cryptography library is required for encryption. "
            "Install with: pip install cryptography"
        )
    
    if not isinstance(value, str):
        raise TypeError("Value must be a string")
    
    key = get_or_create_key()
    # Fernet expects URL-safe base64-encoded 32-byte key
    fernet_key = base64.urlsafe_b64encode(key)
    f = Fernet(fernet_key)
    
    encrypted = f.encrypt(value.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_value(encrypted: str) -> str:
    """Decrypt an encrypted string value.
    
    Args:
        encrypted: The encrypted string (URL-safe base64 encoded)
    
    Returns:
        The decrypted plaintext string
    
    Raises:
        RuntimeError: If cryptography library is not available
        ValueError: If decryption fails or data is invalid
    """
    if Fernet is None:
        raise RuntimeError(
            "cryptography library is required for decryption. "
            "Install with: pip install cryptography"
        )
    
    if not isinstance(encrypted, str):
        raise TypeError("Encrypted value must be a string")
    
    key = get_or_create_key()
    # Fernet expects URL-safe base64-encoded 32-byte key
    fernet_key = base64.urlsafe_b64encode(key)
    f = Fernet(fernet_key)
    
    try:
        decrypted = f.decrypt(encrypted.encode("utf-8"))
        return decrypted.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to decrypt value: {e}") from e
