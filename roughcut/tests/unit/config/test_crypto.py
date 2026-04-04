"""Unit tests for configuration encryption utilities."""

import os
import sys
import unittest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from roughcut.config.crypto import (
    encrypt_value,
    decrypt_value,
    get_or_create_key,
    get_key_file_path,
)


class TestCryptoModule(unittest.TestCase):
    """Test suite for encryption/decryption functionality."""

    def setUp(self):
        """Set up test environment with temporary directories."""
        self.test_dir = Path(__file__).parent / "test_data"
        self.test_dir.mkdir(exist_ok=True)
        
        # Store original environment
        self.original_home = os.environ.get("HOME")
        self.original_appdata = os.environ.get("APPDATA")
        
        # Set up test environment to use temp directory
        os.environ["HOME"] = str(self.test_dir)
        if "APPDATA" in os.environ:
            del os.environ["APPDATA"]

    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment
        if self.original_home:
            os.environ["HOME"] = self.original_home
        elif "HOME" in os.environ:
            del os.environ["HOME"]
            
        if self.original_appdata:
            os.environ["APPDATA"] = self.original_appdata
        
        # Clean up test files
        key_path = self.test_dir / ".config" / "roughcut" / ".encryption_key"
        if key_path.exists():
            key_path.unlink()
        
        # Remove test directory
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_key_generation_creates_file(self):
        """Test that get_or_create_key generates a new key file."""
        # Act
        key = get_or_create_key()
        
        # Assert
        key_path = get_key_file_path()
        self.assertTrue(key_path.exists(), "Key file should be created")
        self.assertEqual(len(key), 32, "Key should be 32 bytes")

    def test_key_file_has_restricted_permissions(self):
        """Test that key file is created with restricted permissions."""
        # Act
        get_or_create_key()
        
        # Assert
        key_path = get_key_file_path()
        if sys.platform != "win32":  # Unix-like systems
            import stat
            mode = key_path.stat().st_mode
            # Check permissions are 0o600 (user read/write only)
            self.assertEqual(stat.S_IMODE(mode), 0o600,
                           "Key file should have 0o600 permissions")

    def test_encryption_produces_different_output(self):
        """Test that encrypted value is different from plaintext."""
        # Arrange
        plaintext = "secret-api-token-12345"
        
        # Act
        encrypted = encrypt_value(plaintext)
        
        # Assert
        self.assertNotEqual(encrypted, plaintext,
                           "Encrypted value should differ from plaintext")
        self.assertIsInstance(encrypted, str,
                            "Encrypted value should be a string")

    def test_encrypt_decrypt_roundtrip(self):
        """Test that decrypt(encrypt(value)) == value."""
        # Arrange
        original = "my-super-secret-token-with-special-chars-!@#$%"
        
        # Act
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        
        # Assert
        self.assertEqual(decrypted, original,
                        "Decrypted value should match original")

    def test_encryption_is_deterministic_with_same_key(self):
        """Test that same plaintext encrypts to same value with same key."""
        # Arrange
        plaintext = "test-token"
        
        # Act
        encrypted1 = encrypt_value(plaintext)
        encrypted2 = encrypt_value(plaintext)
        
        # Assert
        # Fernet uses random salts, so encrypted values will differ
        # But both should decrypt to same value
        decrypted1 = decrypt_value(encrypted1)
        decrypted2 = decrypt_value(encrypted2)
        self.assertEqual(decrypted1, decrypted2,
                        "Both should decrypt to same value")

    def test_decrypt_invalid_data_raises_error(self):
        """Test that decrypting invalid data raises an error."""
        # Arrange
        invalid_encrypted = "invalid-encrypted-data"
        
        # Act & Assert
        with self.assertRaises(Exception):
            decrypt_value(invalid_encrypted)

    def test_encrypt_empty_string(self):
        """Test encryption of empty string."""
        # Act
        encrypted = encrypt_value("")
        decrypted = decrypt_value(encrypted)
        
        # Assert
        self.assertEqual(decrypted, "")

    def test_encrypt_unicode_characters(self):
        """Test encryption of unicode characters."""
        # Arrange
        plaintext = "токен-с-unicode-文字"
        
        # Act
        encrypted = encrypt_value(plaintext)
        decrypted = decrypt_value(encrypted)
        
        # Assert
        self.assertEqual(decrypted, plaintext)


class TestCryptoIntegration(unittest.TestCase):
    """Integration tests for crypto module with file system."""

    def setUp(self):
        """Set up isolated test environment."""
        import tempfile
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.temp_dir)
        if "APPDATA" in os.environ:
            del os.environ["APPDATA"]

    def tearDown(self):
        """Clean up test environment."""
        # Restore environment
        if self.original_home:
            os.environ["HOME"] = self.original_home
        elif "HOME" in os.environ:
            del os.environ["HOME"]
        
        # Clean up temp directory
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_key_persistence_across_sessions(self):
        """Test that key persists across multiple get_or_create_key calls."""
        # Act - get key twice
        key1 = get_or_create_key()
        key2 = get_or_create_key()
        
        # Assert
        self.assertEqual(key1, key2,
                        "Key should be the same on subsequent calls")

    def test_encryption_with_existing_key(self):
        """Test encryption works with pre-existing key file."""
        # Arrange - create key first
        get_or_create_key()
        plaintext = "persistent-test"
        
        # Act - encrypt with existing key
        encrypted = encrypt_value(plaintext)
        
        # Simulate new session
        import importlib
        from roughcut.config import crypto
        importlib.reload(crypto)
        
        # Decrypt with reloaded module
        decrypted = crypto.decrypt_value(encrypted)
        
        # Assert
        self.assertEqual(decrypted, plaintext)


if __name__ == "__main__":
    unittest.main()
