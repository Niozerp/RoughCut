"""Unit tests for Notion API client.

Tests the NotionClient class including validation, retry logic,
and error handling.
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from roughcut.backend.notion.client import (
    NotionClient,
    is_notion_available,
    MAX_RETRIES,
    RETRY_DELAY,
    CONNECTION_TIMEOUT,
)
from roughcut.backend.notion.models import (
    ConnectionStatus,
    ErrorType,
    ValidationResult,
)


class TestNotionClientGracefulDegradation(unittest.TestCase):
    """Test suite for Notion client graceful degradation (AC4)."""

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

    def test_is_configured_false_initially(self):
        """Test that client reports not configured initially."""
        client = NotionClient()
        
        self.assertFalse(client.is_configured())

    def test_is_configured_true_after_save(self):
        """Test that client reports configured after saving settings."""
        from roughcut.config.settings import get_config_manager
        
        manager = get_config_manager()
        manager.save_notion_config(
            api_token="secret_test_token_123456789012345678901234567890",
            page_url="https://www.notion.so/workspace/page-id-123456789"
        )
        
        client = NotionClient()
        
        self.assertTrue(client.is_configured())

    def test_get_page_url_none_when_unconfigured(self):
        """Test that get_page_url returns None when not configured."""
        client = NotionClient()
        
        url = client.get_page_url()
        
        self.assertIsNone(url)

    def test_get_page_url_when_configured(self):
        """Test that get_page_url returns URL when configured."""
        from roughcut.config.settings import get_config_manager
        
        manager = get_config_manager()
        manager.save_notion_config(
            api_token="secret_test_token_123456789012345678901234567890",
            page_url="https://www.notion.so/workspace/page-id-123456789"
        )
        
        client = NotionClient()
        
        url = client.get_page_url()
        
        self.assertEqual(url, "https://www.notion.so/workspace/page-id-123456789")

    def test_sync_media_database_skipped_when_unconfigured(self):
        """Test that sync is skipped gracefully when not configured (AC4)."""
        client = NotionClient()
        
        result = client.sync_media_database([])
        
        self.assertFalse(result['success'])
        self.assertTrue(result['skipped'])
        self.assertIn('not configured', result['message'].lower())

    def test_validate_connection_fails_when_unconfigured(self):
        """Test that validation returns NOT_CONFIGURED when not configured (AC4)."""
        client = NotionClient()
        
        result = client.validate_connection()
        
        self.assertFalse(result.valid)
        self.assertEqual(result.status, ConnectionStatus.NOT_CONFIGURED)
        self.assertIn('not configured', result.error_message.lower())


class TestNotionClientValidation(unittest.TestCase):
    """Test suite for Notion API validation (AC1, AC2, AC3)."""

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

    def test_extract_page_id_from_standard_notion_url(self):
        """Test page ID extraction from standard Notion URLs."""
        client = NotionClient()
        
        # Test standard URL format with page name
        url = "https://www.notion.so/workspace/My-Page-1234567890abcdef1234567890abcdef"
        page_id = client._extract_page_id(url)
        self.assertEqual(page_id, "1234567890abcdef1234567890abcdef")
        
        # Test URL without workspace
        url = "https://www.notion.so/Another-Page-fedcba0987654321fedcba0987654321"
        page_id = client._extract_page_id(url)
        self.assertEqual(page_id, "fedcba0987654321fedcba0987654321")
    
    def test_extract_page_id_returns_none_for_invalid_url(self):
        """Test page ID extraction returns None for invalid URLs."""
        client = NotionClient()
        
        # Invalid URLs
        self.assertIsNone(client._extract_page_id(""))
        self.assertIsNone(client._extract_page_id("https://example.com"))
        self.assertIsNone(client._extract_page_id("notion.so/page"))
    
    def test_classify_error_identifies_authentication_errors(self):
        """Test error classification for authentication errors (AC3)."""
        client = NotionClient()
        
        # Test various authentication error messages
        auth_errors = [
            Exception("Unauthorized"),
            Exception("Invalid token"),
            Exception("API token expired"),
            Exception("Authentication failed"),
        ]
        
        for error in auth_errors:
            error_type, message, suggestion = client._classify_error(error)
            self.assertEqual(error_type, ErrorType.AUTHENTICATION)
            self.assertIn("token", message.lower())
            self.assertTrue(len(suggestion) > 0)  # Should have actionable guidance
    
    def test_classify_error_identifies_page_not_found(self):
        """Test error classification for page not found errors (AC3)."""
        client = NotionClient()
        
        page_errors = [
            Exception("Page not found"),
            Exception("Could not find page"),
            Exception("Invalid page ID"),
        ]
        
        for error in page_errors:
            error_type, message, suggestion = client._classify_error(error)
            self.assertEqual(error_type, ErrorType.PAGE_NOT_FOUND)
            self.assertTrue(len(suggestion) > 0)  # Should have actionable guidance
    
    def test_classify_error_identifies_network_errors(self):
        """Test error classification for network errors (AC3)."""
        client = NotionClient()
        
        network_errors = [
            Exception("Network unreachable"),
            Exception("Connection refused"),
            Exception("DNS resolution failed"),
        ]
        
        for error in network_errors:
            error_type, message, suggestion = client._classify_error(error)
            self.assertEqual(error_type, ErrorType.NETWORK)
            self.assertTrue(len(suggestion) > 0)  # Should have actionable guidance
    
    def test_classify_error_identifies_timeout_errors(self):
        """Test error classification for timeout errors (AC3)."""
        client = NotionClient()
        
        timeout_errors = [
            Exception("Request timeout"),
            Exception("Connection timed out"),
        ]
        
        for error in timeout_errors:
            error_type, message, suggestion = client._classify_error(error)
            self.assertEqual(error_type, ErrorType.TIMEOUT)
    
    def test_classify_error_returns_unknown_for_unrecognized_errors(self):
        """Test error classification returns UNKNOWN for unrecognized errors."""
        client = NotionClient()
        
        unknown_error = Exception("Something unexpected happened")
        error_type, message, suggestion = client._classify_error(unknown_error)
        self.assertEqual(error_type, ErrorType.UNKNOWN)
    
    def test_make_request_with_retry_succeeds_on_first_try(self):
        """Test retry logic succeeds on first attempt (1.6)."""
        client = NotionClient()
        
        # Mock operation that succeeds
        mock_operation = MagicMock(return_value="success")
        
        success, result, error = client._make_request_with_retry(mock_operation)
        
        self.assertTrue(success)
        self.assertEqual(result, "success")
        self.assertIsNone(error)
        mock_operation.assert_called_once()
    
    @patch('time.sleep')
    def test_make_request_with_retry_retries_on_network_error(self, mock_sleep):
        """Test retry logic retries on network errors (1.6)."""
        client = NotionClient()
        
        # Mock operation that fails with network error then succeeds
        mock_operation = MagicMock(side_effect=[
            Exception("Network error"),
            Exception("Network error"),
            "success"
        ])
        
        success, result, error = client._make_request_with_retry(mock_operation)
        
        self.assertTrue(success)
        self.assertEqual(result, "success")
        self.assertEqual(mock_operation.call_count, 3)  # Should retry
    
    def test_make_request_with_retry_does_not_retry_on_auth_error(self):
        """Test retry logic does not retry on authentication errors."""
        client = NotionClient()
        
        # Mock operation that fails with auth error (not retryable)
        mock_operation = MagicMock(side_effect=Exception("Unauthorized"))
        
        success, result, error = client._make_request_with_retry(mock_operation)
        
        self.assertFalse(success)
        self.assertIsNone(result)
        self.assertIsNotNone(error)
        mock_operation.assert_called_once()  # Should not retry
    
    def test_validate_token_returns_not_configured_when_not_configured(self):
        """Test validate_token returns error when not configured."""
        client = NotionClient()
        
        is_valid, error_type, message, suggestion = client.validate_token()
        
        self.assertFalse(is_valid)
        self.assertEqual(error_type, ErrorType.AUTHENTICATION)
        self.assertTrue(len(suggestion) > 0)
    
    def test_validate_page_access_returns_error_when_no_page_url(self):
        """Test validate_page_access returns error when no page URL."""
        from roughcut.config.settings import get_config_manager
        
        # Configure without proper URL
        manager = get_config_manager()
        manager.save_notion_config(
            api_token="secret_test_token_123456789012345678901234567890",
            page_url="https://www.notion.so/test-page"
        )
        
        client = NotionClient()
        
        is_valid, error_type, message, suggestion = client.validate_page_access()
        
        self.assertFalse(is_valid)
        # Should fail because page ID extraction will fail for invalid URL


class TestNotionModels(unittest.TestCase):
    """Test suite for Notion data models."""

    def test_validation_result_defaults(self):
        """Test ValidationResult default values."""
        result = ValidationResult()
        
        self.assertFalse(result.valid)
        self.assertEqual(result.status, ConnectionStatus.NOT_CONFIGURED)
        self.assertIsNone(result.error_type)
        self.assertEqual(result.error_message, "")
        self.assertEqual(result.suggestion, "")
        self.assertIsNotNone(result.timestamp)
    
    def test_validation_result_is_success(self):
        """Test ValidationResult.is_success() method."""
        # Failed validation
        failed = ValidationResult(valid=False, status=ConnectionStatus.DISCONNECTED)
        self.assertFalse(failed.is_success())
        
        # Successful validation
        success = ValidationResult(valid=True, status=ConnectionStatus.CONNECTED)
        self.assertTrue(success.is_success())
        
        # Not configured
        not_config = ValidationResult(valid=False, status=ConnectionStatus.NOT_CONFIGURED)
        self.assertFalse(not_config.is_success())
    
    def test_validation_result_to_dict(self):
        """Test ValidationResult serialization."""
        result = ValidationResult(
            valid=True,
            status=ConnectionStatus.CONNECTED,
            error_type=None,
            error_message="",
            suggestion="All good",
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            last_successful=datetime(2024, 1, 14, 9, 0, 0)
        )
        
        data = result.to_dict()
        
        self.assertEqual(data['valid'], True)
        self.assertEqual(data['status'], 'CONNECTED')
        self.assertIsNone(data['error_type'])
        self.assertEqual(data['timestamp'], '2024-01-15T10:30:00')
        self.assertEqual(data['last_successful'], '2024-01-14T09:00:00')
    
    def test_validation_result_from_dict(self):
        """Test ValidationResult deserialization."""
        data = {
            'valid': False,
            'status': 'DISCONNECTED',
            'error_type': 'AUTHENTICATION',
            'error_message': 'Invalid token',
            'suggestion': 'Check your token',
            'timestamp': '2024-01-15T10:30:00',
            'last_successful': None
        }
        
        result = ValidationResult.from_dict(data)
        
        self.assertFalse(result.valid)
        self.assertEqual(result.status, ConnectionStatus.DISCONNECTED)
        self.assertEqual(result.error_type, ErrorType.AUTHENTICATION)
        self.assertEqual(result.error_message, 'Invalid token')
    
    def test_connection_status_str(self):
        """Test ConnectionStatus string representation."""
        self.assertEqual(str(ConnectionStatus.CONNECTED), "Connected")
        self.assertEqual(str(ConnectionStatus.DISCONNECTED), "Disconnected")
        self.assertEqual(str(ConnectionStatus.NOT_CONFIGURED), "Not Configured")
        self.assertEqual(str(ConnectionStatus.ERROR), "Error")
    
    def test_error_type_str(self):
        """Test ErrorType string representation."""
        self.assertEqual(str(ErrorType.AUTHENTICATION), "Authentication Error")
        self.assertEqual(str(ErrorType.PAGE_NOT_FOUND), "Page Not Found")
        self.assertEqual(str(ErrorType.NETWORK), "Network Error")
        self.assertEqual(str(ErrorType.TIMEOUT), "Connection Timeout")
        self.assertEqual(str(ErrorType.UNKNOWN), "Unknown Error")


class TestIsNotionAvailable(unittest.TestCase):
    """Test suite for is_notion_available convenience function."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.temp_dir)
        if "APPDATA" in os.environ:
            del os.environ["APPDATA"]
        
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

    def test_is_notion_available_false_initially(self):
        """Test that is_notion_available returns False initially."""
        self.assertFalse(is_notion_available())

    def test_is_notion_available_true_after_config(self):
        """Test that is_notion_available returns True after configuration."""
        from roughcut.config.settings import get_config_manager
        
        manager = get_config_manager()
        manager.save_notion_config(
            api_token="secret_test_token_123456789012345678901234567890",
            page_url="https://www.notion.so/workspace/page-id-123456789"
        )
        
        self.assertTrue(is_notion_available())


if __name__ == "__main__":
    unittest.main()
