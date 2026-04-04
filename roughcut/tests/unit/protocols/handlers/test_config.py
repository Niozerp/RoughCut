"""Unit tests for configuration protocol handlers."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from roughcut.protocols.handlers.config import (
    get_notion_config,
    save_notion_config,
    clear_notion_config,
    check_notion_configured,
    CONFIG_HANDLERS
)
from roughcut.protocols.dispatcher import ProtocolDispatcher, get_dispatcher


class TestConfigProtocolHandlers(unittest.TestCase):
    """Test suite for config protocol handlers."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.temp_dir)
        if "APPDATA" in os.environ:
            del os.environ["APPDATA"]
        
        # Reset ConfigManager singleton
        from roughcut.config.settings import ConfigManager
        ConfigManager.reset_instance()

    def tearDown(self):
        """Clean up test environment."""
        if self.original_home:
            os.environ["HOME"] = self.original_home
        
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Reset singleton
        from roughcut.config.settings import ConfigManager
        ConfigManager.reset_instance()

    def test_get_notion_config_unconfigured(self):
        """Test getting config when not configured."""
        result = get_notion_config({})
        
        self.assertIn('configured', result)
        self.assertFalse(result['configured'])
        self.assertIn('page_url', result)
        self.assertIsNone(result['page_url'])

    def test_save_notion_config_success(self):
        """Test saving valid configuration."""
        params = {
            'api_token': 'secret_test_token_123456789012345678901234567890',
            'page_url': 'https://www.notion.so/workspace/page-id-123456789'
        }
        
        result = save_notion_config(params)
        
        self.assertIn('success', result)
        self.assertTrue(result['success'])
        self.assertIn('configured', result)
        self.assertTrue(result['configured'])

    def test_save_notion_config_missing_fields(self):
        """Test saving with missing required fields."""
        params = {
            'api_token': '',
            'page_url': 'https://notion.so/page'
        }
        
        result = save_notion_config(params)
        
        self.assertIn('error', result)
        self.assertEqual(result['error']['code'], 'MISSING_REQUIRED_FIELDS')

    def test_save_notion_config_invalid_url(self):
        """Test saving with invalid URL format."""
        params = {
            'api_token': 'secret_valid_token_here',
            'page_url': 'http://example.com/page'
        }
        
        result = save_notion_config(params)
        
        self.assertIn('error', result)
        self.assertEqual(result['error']['code'], 'VALIDATION_ERROR')

    def test_clear_notion_config(self):
        """Test clearing configuration."""
        # First save a config
        save_notion_config({
            'api_token': 'secret_test_token_123456789012345678901234567890',
            'page_url': 'https://www.notion.so/workspace/page-id-123456789'
        })
        
        # Then clear it
        result = clear_notion_config({})
        
        self.assertIn('success', result)
        self.assertTrue(result['success'])
        self.assertFalse(result['configured'])

    def test_check_notion_configured_false(self):
        """Test checking configuration when not configured."""
        result = check_notion_configured({})
        
        self.assertIn('configured', result)
        self.assertFalse(result['configured'])

    def test_check_notion_configured_true(self):
        """Test checking configuration when configured."""
        # First save a config
        save_notion_config({
            'api_token': 'secret_test_token_123456789012345678901234567890',
            'page_url': 'https://www.notion.so/workspace/page-id-123456789'
        })
        
        result = check_notion_configured({})
        
        self.assertIn('configured', result)
        self.assertTrue(result['configured'])

    def test_config_handlers_registry(self):
        """Test that all handlers are registered."""
        self.assertIn('get_notion_config', CONFIG_HANDLERS)
        self.assertIn('save_notion_config', CONFIG_HANDLERS)
        self.assertIn('clear_notion_config', CONFIG_HANDLERS)
        self.assertIn('check_notion_configured', CONFIG_HANDLERS)

    def test_api_token_not_exposed_in_get_config(self):
        """Test that API token is not exposed in get_notion_config response."""
        # Save config with token
        save_notion_config({
            'api_token': 'secret_super_sensitive_token',
            'page_url': 'https://www.notion.so/page'
        })
        
        # Get config
        result = get_notion_config({})
        
        # Should NOT contain the API token
        self.assertNotIn('api_token', result)


class TestProtocolDispatcher(unittest.TestCase):
    """Test suite for ProtocolDispatcher."""

    def setUp(self):
        """Set up test dispatcher."""
        self.dispatcher = ProtocolDispatcher()
        
        # Mock handler
        self.mock_called = False
        self.mock_params = None
        
        def mock_handler(params):
            self.mock_called = True
            self.mock_params = params
            return {'success': True}
        
        self.dispatcher.register_handler('test_method', mock_handler)

    def test_register_handler(self):
        """Test registering a handler."""
        methods = self.dispatcher.get_available_methods()
        
        self.assertIn('test_method', methods)

    def test_dispatch_success(self):
        """Test successful dispatch."""
        request = {
            'method': 'test_method',
            'params': {'key': 'value'},
            'id': '123'
        }
        
        response = self.dispatcher.dispatch(request)
        
        self.assertTrue(self.mock_called)
        self.assertEqual(self.mock_params, {'key': 'value'})
        self.assertIn('result', response)
        self.assertEqual(response['id'], '123')
        self.assertIsNone(response['error'])

    def test_dispatch_missing_method(self):
        """Test dispatch with missing method field."""
        request = {
            'params': {},
            'id': '123'
        }
        
        response = self.dispatcher.dispatch(request)
        
        self.assertIn('error', response)
        self.assertEqual(response['error']['code'], 'INVALID_REQUEST')

    def test_dispatch_unknown_method(self):
        """Test dispatch with unknown method."""
        request = {
            'method': 'unknown_method',
            'params': {},
            'id': '123'
        }
        
        response = self.dispatcher.dispatch(request)
        
        self.assertIn('error', response)
        self.assertEqual(response['error']['code'], 'METHOD_NOT_FOUND')

    def test_dispatch_handler_returns_error(self):
        """Test dispatch when handler returns error."""
        def error_handler(params):
            return {
                'error': {
                    'code': 'CUSTOM_ERROR',
                    'category': 'test',
                    'message': 'Test error',
                    'suggestion': 'Test suggestion'
                }
            }
        
        self.dispatcher.register_handler('error_method', error_handler)
        
        request = {
            'method': 'error_method',
            'params': {},
            'id': '123'
        }
        
        response = self.dispatcher.dispatch(request)
        
        self.assertIn('error', response)
        self.assertEqual(response['error']['code'], 'CUSTOM_ERROR')

    def test_dispatch_handler_exception(self):
        """Test dispatch when handler raises exception."""
        def bad_handler(params):
            raise ValueError("Something went wrong")
        
        self.dispatcher.register_handler('bad_method', bad_handler)
        
        request = {
            'method': 'bad_method',
            'params': {},
            'id': '123'
        }
        
        response = self.dispatcher.dispatch(request)
        
        self.assertIn('error', response)
        self.assertEqual(response['error']['code'], 'INTERNAL_ERROR')


class TestDispatchRequest(unittest.TestCase):
    """Test suite for dispatch_request convenience function."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.temp_dir)
        if "APPDATA" in os.environ:
            del os.environ["APPDATA"]

    def tearDown(self):
        """Clean up."""
        if self.original_home:
            os.environ["HOME"] = self.original_home
        
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_dispatch_request_valid_json(self):
        """Test dispatch with valid JSON request."""
        from roughcut.protocols.dispatcher import dispatch_request
        
        request = {
            'method': 'check_notion_configured',
            'params': {},
            'id': 'test-1'
        }
        
        response_json = dispatch_request(json.dumps(request))
        response = json.loads(response_json)
        
        self.assertIn('result', response)
        self.assertIn('configured', response['result'])

    def test_dispatch_request_invalid_json(self):
        """Test dispatch with invalid JSON."""
        from roughcut.protocols.dispatcher import dispatch_request
        
        response_json = dispatch_request("not valid json")
        response = json.loads(response_json)
        
        self.assertIn('error', response)
        self.assertEqual(response['error']['code'], 'PARSE_ERROR')


if __name__ == "__main__":
    unittest.main()
