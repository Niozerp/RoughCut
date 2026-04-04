# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest"]
# ///

#!/usr/bin/env python3
"""Unit tests for AIConfig recovery mode."""

import pytest

from roughcut.config.models import AIConfig


class TestAIConfigRecoveryMode:
    """Test cases for AIConfig recovery mode functionality."""
    
    def test_default_recovery_mode(self):
        """Test that default recovery mode is 'automatic'."""
        config = AIConfig()
        assert config.recovery_mode == "automatic"
    
    def test_valid_recovery_modes(self):
        """Test that both valid recovery modes pass validation."""
        for mode in ["automatic", "manual"]:
            config = AIConfig(
                api_key="sk-test12345678901234567890",
                enabled=True,
                recovery_mode=mode
            )
            is_valid, error = config.validate()
            assert is_valid, f"Mode '{mode}' should be valid"
            assert error == ""
    
    def test_invalid_recovery_mode(self):
        """Test that invalid recovery mode fails validation."""
        config = AIConfig(
            api_key="sk-test12345678901234567890",
            enabled=True,
            recovery_mode="invalid"
        )
        is_valid, error = config.validate()
        assert not is_valid
        assert "recovery_mode" in error.lower()
    
    def test_recovery_mode_serialization(self):
        """Test that recovery mode is properly serialized."""
        config = AIConfig(
            api_key="sk-test12345678901234567890",
            enabled=True,
            recovery_mode="manual"
        )
        
        data = config.to_dict(encrypt_token=False)
        
        assert data['recovery_mode'] == "manual"
    
    def test_recovery_mode_deserialization(self):
        """Test that recovery mode is properly deserialized."""
        data = {
            'api_key': 'sk-test12345678901234567890',
            'model': 'gpt-3.5-turbo',
            'enabled': True,
            'timeout': 30.0,
            'max_retries': 3,
            'recovery_mode': 'manual'
        }
        
        config = AIConfig.from_dict(data, decrypt_token=False)
        
        assert config.recovery_mode == "manual"
    
    def test_recovery_mode_default_deserialization(self):
        """Test that missing recovery mode defaults to 'automatic'."""
        data = {
            'api_key': 'sk-test12345678901234567890',
            'model': 'gpt-3.5-turbo',
            'enabled': True,
            'timeout': 30.0,
            'max_retries': 3
        }
        
        config = AIConfig.from_dict(data, decrypt_token=False)
        
        assert config.recovery_mode == "automatic"
    
    def test_recovery_mode_disabled_ai(self):
        """Test that recovery mode validation is skipped when AI is disabled."""
        config = AIConfig(
            api_key=None,
            enabled=False,
            recovery_mode="invalid"  # Should be ignored when disabled
        )
        is_valid, error = config.validate()
        assert is_valid  # Should pass because AI is disabled
