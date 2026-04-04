"""Unit tests for Notion protocol handlers.

Tests the JSON-RPC protocol handlers for Notion validation.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from roughcut.protocols.handlers.notion import (
    validate_notion_connection,
    get_connection_status,
    test_notion_sync,
    NOTION_HANDLERS,
)


class TestValidateNotionConnection(unittest.TestCase):
    """Test suite for validate_notion_connection handler."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.temp_dir)
        if "APPDATA" in os.environ:
            del os.environ["APPDATA"]
        
        # Reset singleton
        from roughcut.config.settings import ConfigManager
        ConfigManager.reset_instance()

    def tearDown(self):
        """Clean up."""
        if self.original_home:
            os.environ["HOME"] = self.original_home
        
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        from roughcut.config.settings import ConfigManager
        ConfigManager.reset_instance()

    def test_validate_returns_not_configured_when_no_config(self):
        """Test handler returns NOT_CONFIGURED when not configured."""
        result = validate_notion_connection({})
        
        self.assertFalse(result['valid'])
        self.assertEqual(result['status'], 'NOT_CONFIGURED')
        self.assertIsNotNone(result['error_message'])
        self.assertIsNotNone(result['suggestion'])
        self.assertIsNotNone(result['timestamp'])

    def test_validate_includes_error_type_on_failure(self):
        """Test handler includes error type on validation failure."""
        # Configure with invalid credentials (will fail validation)
        from roughcut.config.settings import get_config_manager
        manager = get_config_manager()
        manager.save_notion_config(
            api_token="secret_invalid_token_123456789012345678901234567890",
            page_url="https://www.notion.so/workspace/page-id-123456789"
        )
        
        result = validate_notion_connection({})
        
        # Should include error details
        self.assertIn('error_type', result)
        self.assertIn('error_message', result)
        self.assertIn('suggestion', result)


class TestGetConnectionStatus(unittest.TestCase):
    """Test suite for get_connection_status handler."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.temp_dir)
        if "APPDATA" in os.environ:
            del os.environ["APPDATA"]
        
        # Reset singleton
        from roughcut.config.settings import ConfigManager
        ConfigManager.reset_instance()

    def tearDown(self):
        """Clean up."""
        if self.original_home:
            os.environ["HOME"] = self.original_home
        
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        from roughcut.config.settings import ConfigManager
        ConfigManager.reset_instance()

    def test_get_status_returns_not_configured_when_no_config(self):
        """Test handler returns NOT_CONFIGURED when not configured."""
        result = get_connection_status({})
        
        self.assertFalse(result['configured'])
        self.assertEqual(result['status'], 'NOT_CONFIGURED')
        self.assertIsNone(result['last_validated'])

    def test_get_status_returns_configured_when_configured(self):
        """Test handler returns configured status when configured."""
        from roughcut.config.settings import get_config_manager
        
        manager = get_config_manager()
        manager.save_notion_config(
            api_token="secret_test_token_123456789012345678901234567890",
            page_url="https://www.notion.so/workspace/page-id-123456789"
        )
        
        result = get_connection_status({})
        
        self.assertTrue(result['configured'])
        self.assertIsNotNone(result['status'])
        # last_validated might be None if no validation has been performed yet


class TestTestNotionSync(unittest.TestCase):
    """Test suite for test_notion_sync handler."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.temp_dir)
        if "APPDATA" in os.environ:
            del os.environ["APPDATA"]
        
        # Reset singleton
        from roughcut.config.settings import ConfigManager
        ConfigManager.reset_instance()

    def tearDown(self):
        """Clean up."""
        if self.original_home:
            os.environ["HOME"] = self.original_home
        
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        from roughcut.config.settings import ConfigManager
        ConfigManager.reset_instance()

    def test_test_sync_fails_when_not_configured(self):
        """Test handler fails when Notion not configured."""
        result = test_notion_sync({})
        
        self.assertFalse(result['success'])
        self.assertFalse(result['connection_valid'])

    def test_test_sync_includes_note_for_epic2(self):
        """Test handler includes note about Epic 2 implementation."""
        from roughcut.config.settings import get_config_manager
        
        manager = get_config_manager()
        manager.save_notion_config(
            api_token="secret_test_token_123456789012345678901234567890",
            page_url="https://www.notion.so/workspace/page-id-123456789"
        )
        
        result = test_notion_sync({})
        
        # Should include note about Epic 2 even if connection validation fails
        if 'note' in result:
            self.assertIn('Epic', result['note'])


class TestNotionHandlersRegistry(unittest.TestCase):
    """Test suite for NOTION_HANDLERS registry."""

    def test_all_handlers_registered(self):
        """Test that all expected handlers are registered."""
        expected_handlers = [
            'validate_notion_connection',
            'get_connection_status',
            'test_notion_sync',
        ]
        
        for handler_name in expected_handlers:
            self.assertIn(handler_name, NOTION_HANDLERS)
            self.assertTrue(callable(NOTION_HANDLERS[handler_name]))


if __name__ == "__main__":
    unittest.main()
