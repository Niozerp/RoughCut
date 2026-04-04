"""Unit tests for configuration data models."""

import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

import unittest
from roughcut.config.models import NotionConfig, AppConfig


class TestNotionConfig(unittest.TestCase):
    """Test suite for NotionConfig dataclass."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = NotionConfig()
        
        self.assertIsNone(config.api_token)
        self.assertIsNone(config.page_url)
        self.assertFalse(config.enabled)
        self.assertIsNotNone(config.last_updated)

    def test_validation_valid_config(self):
        """Test validation with valid configuration."""
        config = NotionConfig(
            api_token="secret_test_token_123456789",
            page_url="https://www.notion.so/workspace/page-id-12345",
            enabled=True
        )
        
        is_valid, error = config.validate()
        
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_validation_short_token(self):
        """Test validation rejects short API token."""
        config = NotionConfig(
            api_token="short",
            page_url="https://www.notion.so/page-id"
        )
        
        is_valid, error = config.validate()
        
        self.assertFalse(is_valid)
        self.assertIn("too short", error)

    def test_validation_invalid_url_format(self):
        """Test validation rejects invalid URL format."""
        config = NotionConfig(
            api_token="secret_valid_token_here",
            page_url="http://example.com/page"
        )
        
        is_valid, error = config.validate()
        
        self.assertFalse(is_valid)
        self.assertIn("Invalid Notion page URL format", error)

    def test_validation_incomplete_notion_url(self):
        """Test validation rejects incomplete Notion URL."""
        config = NotionConfig(
            api_token="secret_valid_token_here",
            page_url="https://notion.so/"
        )
        
        is_valid, error = config.validate()
        
        self.assertFalse(is_valid)
        self.assertIn("incomplete", error)

    def test_is_configured_true(self):
        """Test is_configured returns True when properly configured."""
        config = NotionConfig(
            api_token="secret_test_token",
            page_url="https://notion.so/page-id-12345",
            enabled=True
        )
        
        self.assertTrue(config.is_configured())

    def test_is_configured_false_when_disabled(self):
        """Test is_configured returns False when disabled."""
        config = NotionConfig(
            api_token="secret_test_token",
            page_url="https://notion.so/page-id-12345",
            enabled=False
        )
        
        self.assertFalse(config.is_configured())

    def test_is_configured_false_when_empty_token(self):
        """Test is_configured returns False with empty token."""
        config = NotionConfig(
            api_token="",
            page_url="https://notion.so/page-id-12345",
            enabled=True
        )
        
        self.assertFalse(config.is_configured())

    def test_is_configured_false_when_empty_url(self):
        """Test is_configured returns False with empty URL."""
        config = NotionConfig(
            api_token="secret_test_token",
            page_url="",
            enabled=True
        )
        
        self.assertFalse(config.is_configured())

    def test_to_dict(self):
        """Test serialization to dictionary."""
        config = NotionConfig(
            api_token="secret_test_token",
            page_url="https://notion.so/page-id",
            enabled=True
        )
        
        data = config.to_dict(encrypt_token=False)
        
        self.assertEqual(data['page_url'], "https://notion.so/page-id")
        self.assertEqual(data['enabled'], True)
        self.assertEqual(data['api_token'], "secret_test_token")
        self.assertIsNotNone(data['last_updated'])

    def test_to_dict_with_encryption(self):
        """Test serialization with token encryption."""
        config = NotionConfig(
            api_token="secret_test_token",
            page_url="https://notion.so/page-id",
            enabled=True
        )
        
        data = config.to_dict(encrypt_token=True)
        
        # Encrypted token should be different from original
        self.assertNotEqual(data['api_token'], "secret_test_token")
        # Encrypted token should be a non-empty string
        self.assertIsInstance(data['api_token'], str)
        self.assertGreater(len(data['api_token']), 0)

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            'api_token': 'secret_test_token',
            'page_url': 'https://notion.so/page-id',
            'enabled': True,
            'last_updated': datetime.now().isoformat()
        }
        
        config = NotionConfig.from_dict(data, decrypt_token=False)
        
        self.assertEqual(config.api_token, "secret_test_token")
        self.assertEqual(config.page_url, "https://notion.so/page-id")
        self.assertTrue(config.enabled)

    def test_from_dict_with_decryption(self):
        """Test deserialization with token decryption."""
        from roughcut.config.crypto import encrypt_value
        
        original_token = "secret_test_token"
        encrypted_token = encrypt_value(original_token)
        
        data = {
            'api_token': encrypted_token,
            'page_url': 'https://notion.so/page-id',
            'enabled': True,
            'last_updated': datetime.now().isoformat()
        }
        
        config = NotionConfig.from_dict(data, decrypt_token=True)
        
        self.assertEqual(config.api_token, original_token)

    def test_from_dict_handles_invalid_last_updated(self):
        """Test deserialization handles invalid last_updated."""
        data = {
            'api_token': 'secret_test',
            'page_url': 'https://notion.so/page',
            'enabled': True,
            'last_updated': 'invalid-date'
        }
        
        config = NotionConfig.from_dict(data)
        
        # Should have a valid datetime (defaulted to now)
        self.assertIsInstance(config.last_updated, datetime)

    def test_mask_token(self):
        """Test token masking for display."""
        config = NotionConfig(api_token="secret_abc123def456")
        
        masked = config.mask_token()
        
        self.assertIn("***", masked)
        self.assertTrue(masked.startswith("sec"))

    def test_mask_token_short(self):
        """Test token masking with short token."""
        config = NotionConfig(api_token="abc123")
        
        masked = config.mask_token()
        
        self.assertEqual(masked, "***")

    def test_mask_token_empty(self):
        """Test token masking with empty token."""
        config = NotionConfig(api_token=None)
        
        masked = config.mask_token()
        
        self.assertEqual(masked, "")


class TestAppConfig(unittest.TestCase):
    """Test suite for AppConfig dataclass."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = AppConfig()
        
        self.assertIsNotNone(config.notion)
        self.assertIsInstance(config.notion, NotionConfig)
        self.assertEqual(config.version, "1.0")

    def test_to_dict(self):
        """Test serialization to dictionary."""
        config = AppConfig(
            notion=NotionConfig(
                api_token="secret_test",
                page_url="https://notion.so/page",
                enabled=True
            ),
            version="1.0"
        )
        
        data = config.to_dict()
        
        self.assertEqual(data['version'], "1.0")
        self.assertIn('notion', data)
        self.assertEqual(data['notion']['page_url'], "https://notion.so/page")

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            'version': '1.0',
            'notion': {
                'api_token': 'secret_test',
                'page_url': 'https://notion.so/page',
                'enabled': True,
                'last_updated': datetime.now().isoformat()
            }
        }
        
        config = AppConfig.from_dict(data)
        
        self.assertEqual(config.version, "1.0")
        self.assertEqual(config.notion.page_url, "https://notion.so/page")

    def test_from_dict_missing_notion(self):
        """Test deserialization with missing notion section."""
        data = {
            'version': '1.0'
        }
        
        config = AppConfig.from_dict(data)
        
        self.assertIsNotNone(config.notion)
        self.assertIsInstance(config.notion, NotionConfig)


if __name__ == "__main__":
    unittest.main()
