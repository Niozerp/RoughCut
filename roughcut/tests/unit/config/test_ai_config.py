# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest"]
# ///

#!/usr/bin/env python3
"""Unit tests for AI configuration models and settings."""

import pytest
from roughcut.config.models import AIConfig, AppConfig


class TestAIConfigValidation:
    """Test AIConfig validation."""
    
    def test_valid_config_when_disabled(self):
        """Test that disabled config passes validation."""
        config = AIConfig(enabled=False)
        is_valid, error = config.validate()
        
        assert is_valid is True
        assert error == ""
    
    def test_valid_config_when_enabled(self):
        """Test valid enabled configuration."""
        config = AIConfig(
            enabled=True,
            api_key="sk-test12345678901234567890",
            model="gpt-3.5-turbo",
            timeout=30.0,
            max_retries=3
        )
        is_valid, error = config.validate()
        
        assert is_valid is True
        assert error == ""
    
    def test_invalid_missing_api_key(self):
        """Test validation fails without API key."""
        config = AIConfig(enabled=True, api_key=None)
        is_valid, error = config.validate()
        
        assert is_valid is False
        assert "API key is required" in error
    
    def test_invalid_short_api_key(self):
        """Test validation fails with short API key."""
        config = AIConfig(enabled=True, api_key="sk-short")
        is_valid, error = config.validate()
        
        assert is_valid is False
        assert "too short" in error
    
    def test_invalid_api_key_format(self):
        """Test validation fails with wrong API key format."""
        config = AIConfig(enabled=True, api_key="not-sk-prefix-1234567890")
        is_valid, error = config.validate()
        
        assert is_valid is False
        assert "start with 'sk-'" in error
    
    def test_invalid_timeout(self):
        """Test validation fails with invalid timeout."""
        config = AIConfig(
            enabled=True,
            api_key="sk-test12345678901234567890",
            timeout=1.0  # Too short
        )
        is_valid, error = config.validate()
        
        assert is_valid is False
        assert "between 5 and 300" in error
    
    def test_invalid_retries(self):
        """Test validation fails with invalid retries."""
        config = AIConfig(
            enabled=True,
            api_key="sk-test12345678901234567890",
            max_retries=20  # Too high
        )
        is_valid, error = config.validate()
        
        assert is_valid is False
        assert "between 0 and 10" in error


class TestAIConfigSerialization:
    """Test AIConfig serialization."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = AIConfig(
            api_key="sk-test123",
            model="gpt-4",
            enabled=True,
            timeout=60.0,
            max_retries=5
        )
        
        result = config.to_dict(encrypt_token=False)
        
        assert result['api_key'] == "sk-test123"
        assert result['model'] == "gpt-4"
        assert result['enabled'] is True
        assert result['timeout'] == 60.0
        assert result['max_retries'] == 5
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            'api_key': 'sk-test123',
            'model': 'gpt-4',
            'enabled': True,
            'timeout': 60.0,
            'max_retries': 5
        }
        
        config = AIConfig.from_dict(data, decrypt_token=False)
        
        assert config.api_key == "sk-test123"
        assert config.model == "gpt-4"
        assert config.enabled is True
        assert config.timeout == 60.0
        assert config.max_retries == 5
    
    def test_from_dict_with_defaults(self):
        """Test creation from dictionary with defaults."""
        data = {'api_key': 'sk-test'}
        
        config = AIConfig.from_dict(data, decrypt_token=False)
        
        assert config.api_key == "sk-test"
        assert config.model == "gpt-3.5-turbo"  # default
        assert config.enabled is False  # default
        assert config.timeout == 30.0  # default
        assert config.max_retries == 3  # default


class TestAIConfigStatus:
    """Test AIConfig status checks."""
    
    def test_is_configured_when_enabled_with_key(self):
        """Test is_configured returns True when enabled with key."""
        config = AIConfig(enabled=True, api_key="sk-test12345678901234567890")
        
        assert config.is_configured() is True
    
    def test_is_configured_when_disabled(self):
        """Test is_configured returns False when disabled."""
        config = AIConfig(enabled=False, api_key="sk-test12345678901234567890")
        
        assert config.is_configured() is False
    
    def test_is_configured_when_no_key(self):
        """Test is_configured returns False without key."""
        config = AIConfig(enabled=True, api_key=None)
        
        assert config.is_configured() is False
    
    def test_mask_key(self):
        """Test API key masking."""
        config = AIConfig(api_key="sk-abc123xyz789")
        masked = config.mask_key()
        
        assert "***" in masked
        assert masked.startswith("sk-")
        assert masked.endswith("789")
    
    def test_mask_key_empty(self):
        """Test masking empty key."""
        config = AIConfig(api_key=None)
        
        assert config.mask_key() == ""
    
    def test_mask_key_short(self):
        """Test masking short key."""
        config = AIConfig(api_key="sk-1234")
        
        assert config.mask_key() == "***"


class TestAppConfigWithAI:
    """Test AppConfig with AI configuration."""
    
    def test_app_config_includes_ai(self):
        """Test that AppConfig includes AI configuration."""
        config = AppConfig()
        
        assert hasattr(config, 'ai')
        assert isinstance(config.ai, AIConfig)
    
    def test_app_config_to_dict_includes_ai(self):
        """Test that to_dict includes AI config."""
        config = AppConfig()
        config.ai.enabled = True
        config.ai.api_key = "sk-test"
        
        result = config.to_dict()
        
        assert 'ai' in result
        assert result['ai']['enabled'] is True
    
    def test_app_config_from_dict_includes_ai(self):
        """Test that from_dict includes AI config."""
        # Note: AppConfig.from_dict calls AIConfig.from_dict with decrypt_token=True
        # Since we're passing unencrypted key, it will fail to decrypt and return None
        # We need to test with an encrypted key or handle this differently
        from roughcut.config.crypto import encrypt_value
        
        encrypted_key = encrypt_value("sk-test")
        
        data = {
            'version': '1.0',
            'notion': {},
            'ai': {
                'enabled': True,
                'api_key': encrypted_key,
                'model': 'gpt-4'
            }
        }
        
        config = AppConfig.from_dict(data)
        
        assert config.ai.enabled is True
        assert config.ai.api_key == "sk-test"
        assert config.ai.model == "gpt-4"
