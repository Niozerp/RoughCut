# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest", "pytest-asyncio"]
# ///

#!/usr/bin/env python3
"""Unit tests for OpenAI client wrapper."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from roughcut.backend.ai.openai_client import OpenAIClient, TagResult
from roughcut.utils.exceptions import AIError, AIConfigError, AIRateLimitError


class TestOpenAIClientInitialization:
    """Test OpenAI client initialization."""
    
    def test_init_with_valid_key(self):
        """Test initialization with valid API key."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI') as mock_client:
            client = OpenAIClient(api_key="sk-test123456789")
            
            assert client.timeout == 30.0
            assert client.max_retries == 3
            assert client.model == "gpt-3.5-turbo"
            assert client.base_url is None
            mock_client.assert_called_once_with(api_key="sk-test123456789")
    
    def test_init_with_base_url(self):
        """Test initialization with custom base URL (e.g., OpenRouter)."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI') as mock_client:
            client = OpenAIClient(
                api_key="sk-or-test123456789",
                base_url="https://openrouter.ai/api/v1",
                model="anthropic/claude-3.5-sonnet"
            )
            
            assert client.timeout == 30.0
            assert client.max_retries == 3
            assert client.model == "anthropic/claude-3.5-sonnet"
            assert client.base_url == "https://openrouter.ai/api/v1"
            mock_client.assert_called_once_with(
                api_key="sk-or-test123456789",
                base_url="https://openrouter.ai/api/v1"
            )
    
    def test_init_with_custom_settings(self):
        """Test initialization with custom settings."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI'):
            client = OpenAIClient(
                api_key="sk-test",
                timeout=60.0,
                max_retries=5,
                model="gpt-4"
            )
            
            assert client.timeout == 60.0
            assert client.max_retries == 5
            assert client.model == "gpt-4"
    
    def test_init_with_empty_key_raises_error(self):
        """Test that empty API key raises AIError."""
        with pytest.raises(AIError) as exc_info:
            OpenAIClient(api_key="")
        
        assert exc_info.value.code == "AI_CONFIG_ERROR"
        assert "API key is required" in exc_info.value.message
    
    def test_init_with_none_key_raises_error(self):
        """Test that None API key raises AIError."""
        with pytest.raises(AIError) as exc_info:
            OpenAIClient(api_key=None)
        
        assert exc_info.value.code == "AI_CONFIG_ERROR"


class TestOpenAIClientTagGeneration:
    """Test tag generation functionality."""
    
    @pytest.mark.asyncio
    async def test_generate_tags_success(self):
        """Test successful tag generation."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI') as mock_client_class:
            # Setup mock
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "corporate, upbeat, bright, theme"
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            # Create client and generate tags
            client = OpenAIClient(api_key="sk-test123456789")
            result = await client.generate_tags(
                file_name="bright_corporate_theme.wav",
                folder_path="/Music/Corporate/Upbeat",
                category="music"
            )
            
            assert isinstance(result, TagResult)
            assert result.tags == ["corporate", "upbeat", "bright", "theme"]
            # Confidence is 0.95 for 4 comma-separated tags (per _calculate_confidence logic)
            assert result.confidence == 0.95
            assert result.raw_response == "corporate, upbeat, bright, theme"
    
    @pytest.mark.asyncio
    async def test_generate_tags_timeout(self):
        """Test timeout handling."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_client_class.return_value = mock_client
            
            client = OpenAIClient(api_key="sk-test123456789", timeout=5.0)
            
            with pytest.raises(AIError) as exc_info:
                await client.generate_tags(
                    file_name="test.wav",
                    folder_path="/Music",
                    category="music"
                )
            
            assert exc_info.value.code == "AI_TIMEOUT"
            assert "5.0s" in exc_info.value.message
    
    @pytest.mark.asyncio
    async def test_generate_tags_rate_limit_retry(self):
        """Test rate limit with retry logic."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI') as mock_client_class:
            import openai
            
            mock_client = MagicMock()
            # First two calls fail with rate limit, third succeeds
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "test, tags"
            mock_response.choices = [mock_choice]
            
            mock_client.chat.completions.create = AsyncMock(side_effect=[
                openai.RateLimitError("Rate limit exceeded", response=MagicMock(), body={}),
                openai.RateLimitError("Rate limit exceeded", response=MagicMock(), body={}),
                mock_response
            ])
            mock_client_class.return_value = mock_client
            
            client = OpenAIClient(api_key="sk-test123456789", max_retries=3)
            
            with patch('asyncio.sleep', new=AsyncMock()):  # Mock sleep to speed up test
                result = await client.generate_tags(
                    file_name="test.wav",
                    folder_path="/Music",
                    category="music"
                )
            
            assert result.tags == ["test", "tags"]
            assert mock_client.chat.completions.create.call_count == 3
    
    @pytest.mark.asyncio
    async def test_generate_tags_rate_limit_exhausted(self):
        """Test rate limit when all retries exhausted."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI') as mock_client_class:
            import openai
            
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=openai.RateLimitError("Rate limit exceeded", response=MagicMock(), body={})
            )
            mock_client_class.return_value = mock_client
            
            client = OpenAIClient(api_key="sk-test123456789", max_retries=2)
            
            with patch('asyncio.sleep', new=AsyncMock()):
                with pytest.raises(AIRateLimitError) as exc_info:
                    await client.generate_tags(
                        file_name="test.wav",
                        folder_path="/Music",
                        category="music"
                    )
            
            assert "2 retries" in exc_info.value.message
    
    @pytest.mark.asyncio
    async def test_generate_tags_authentication_error(self):
        """Test authentication error handling."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI') as mock_client_class:
            import openai
            
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=openai.AuthenticationError("Invalid API key", response=MagicMock(), body={})
            )
            mock_client_class.return_value = mock_client
            
            client = OpenAIClient(api_key="sk-invalid")
            
            with pytest.raises(AIError) as exc_info:
                await client.generate_tags(
                    file_name="test.wav",
                    folder_path="/Music",
                    category="music"
                )
            
            assert exc_info.value.code == "AI_AUTH_ERROR"
            assert "Invalid API key" in exc_info.value.message


class TestTagParsing:
    """Test tag parsing from AI responses."""
    
    @pytest.mark.asyncio
    async def test_parse_simple_tags(self):
        """Test parsing simple comma-separated tags."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "corporate, upbeat, bright, theme, electronic"
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            client = OpenAIClient(api_key="sk-test")
            result = await client.generate_tags("test.wav", "/Music", "music")
            
            assert len(result.tags) == 5
            assert "corporate" in result.tags
            assert "electronic" in result.tags
    
    @pytest.mark.asyncio
    async def test_parse_tags_with_whitespace(self):
        """Test parsing tags with extra whitespace."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "  corporate  ,  UPBEAT  ,  Bright  "
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            client = OpenAIClient(api_key="sk-test")
            result = await client.generate_tags("test.wav", "/Music", "music")
            
            assert result.tags == ["corporate", "upbeat", "bright"]
    
    @pytest.mark.asyncio
    async def test_parse_tags_with_punctuation(self):
        """Test parsing tags with punctuation."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "corporate!, upbeat., bright?, theme"
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            client = OpenAIClient(api_key="sk-test")
            result = await client.generate_tags("test.wav", "/Music", "music")
            
            assert "corporate!" not in result.tags
            assert "corporate" in result.tags
            assert "upbeat." not in result.tags
            assert "upbeat" in result.tags
