# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest", "pytest-asyncio"]
# ///

#!/usr/bin/env python3
"""Unit tests for MediaTagger class."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from roughcut.backend.ai.tagger import MediaTagger
from roughcut.backend.ai.openai_client import TagResult
from roughcut.utils.exceptions import AIError


class TestMediaTaggerInitialization:
    """Test MediaTagger initialization."""
    
    def test_init_with_client(self):
        """Test initialization with client."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI'):
            from roughcut.backend.ai.openai_client import OpenAIClient
            client = OpenAIClient(api_key="sk-test123456789")
            tagger = MediaTagger(client)
            
            assert tagger.ai_client is client


class TestTagCleaning:
    """Test tag cleaning functionality."""
    
    def test_clean_tags_basic(self):
        """Test basic tag cleaning."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI'):
            from roughcut.backend.ai.openai_client import OpenAIClient
            client = OpenAIClient(api_key="sk-test")
            tagger = MediaTagger(client)
            
            result = tagger._clean_tags(["corporate", "  UPBEAT  ", "Bright"])
            
            assert result == ["corporate", "upbeat", "bright"]
    
    def test_clean_tags_removes_punctuation(self):
        """Test that punctuation is removed."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI'):
            from roughcut.backend.ai.openai_client import OpenAIClient
            client = OpenAIClient(api_key="sk-test")
            tagger = MediaTagger(client)
            
            result = tagger._clean_tags(["corporate!", "upbeat.", "bright?, theme"])
            
            assert "corporate" in result
            assert "upbeat" in result
            assert "bright" in result
            assert "theme" in result
            assert "corporate!" not in result
    
    def test_clean_tags_removes_duplicates(self):
        """Test that duplicates are removed."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI'):
            from roughcut.backend.ai.openai_client import OpenAIClient
            client = OpenAIClient(api_key="sk-test")
            tagger = MediaTagger(client)
            
            result = tagger._clean_tags(["corporate", "CORPORATE", "corporate!", "upbeat"])
            
            assert result == ["corporate", "upbeat"]
    
    def test_clean_tags_removes_short_tags(self):
        """Test that empty tags are removed but single chars are kept."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI'):
            from roughcut.backend.ai.openai_client import OpenAIClient
            client = OpenAIClient(api_key="sk-test")
            tagger = MediaTagger(client)
            
            result = tagger._clean_tags(["", "a", "ab", "corporate"])
            
            assert "" not in result
            assert "a" in result  # Single char tags are kept
            assert "ab" in result
            assert "corporate" in result
    
    def test_clean_tags_preserves_order(self):
        """Test that tag order is preserved (minus duplicates)."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI'):
            from roughcut.backend.ai.openai_client import OpenAIClient
            client = OpenAIClient(api_key="sk-test")
            tagger = MediaTagger(client)
            
            result = tagger._clean_tags(["z", "a", "b", "a", "c"])
            
            assert result == ["z", "a", "b", "c"]


class TestTagMedia:
    """Test single file tagging."""
    
    @pytest.mark.asyncio
    async def test_tag_media_success(self):
        """Test successful media tagging."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "corporate, upbeat, bright, theme"
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            from roughcut.backend.ai.openai_client import OpenAIClient
            client = OpenAIClient(api_key="sk-test")
            tagger = MediaTagger(client)
            
            result = await tagger.tag_media(
                Path("/Music/Corporate/Upbeat/bright_corporate_theme.wav"),
                "music"
            )
            
            assert isinstance(result, TagResult)
            assert "corporate" in result.tags
            assert "upbeat" in result.tags
            assert "bright" in result.tags
            assert "theme" in result.tags
    
    @pytest.mark.asyncio
    async def test_tag_media_accepts_path_object(self):
        """Test that Path objects are accepted."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "test, tags"
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            from roughcut.backend.ai.openai_client import OpenAIClient
            client = OpenAIClient(api_key="sk-test")
            tagger = MediaTagger(client)
            
            result = await tagger.tag_media(
                Path("/Music/test.wav"),
                "music"
            )
            
            assert result.tags == ["test", "tags"]


class TestTagBatch:
    """Test batch tagging functionality."""
    
    @pytest.mark.asyncio
    async def test_tag_batch_success(self):
        """Test successful batch tagging."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            
            # Return different responses for different files
            responses = [
                MagicMock(choices=[MagicMock(message=MagicMock(content="corporate, upbeat"))]),
                MagicMock(choices=[MagicMock(message=MagicMock(content="dark, moody"))]),
            ]
            mock_client.chat.completions.create = AsyncMock(side_effect=responses)
            mock_client_class.return_value = mock_client
            
            from roughcut.backend.ai.openai_client import OpenAIClient
            client = OpenAIClient(api_key="sk-test")
            tagger = MediaTagger(client)
            
            files = [
                (Path("/Music/file1.wav"), "music"),
                (Path("/Music/file2.wav"), "music"),
            ]
            
            results = await tagger.tag_batch(files)
            
            assert len(results) == 2
            assert Path("/Music/file1.wav") in results
            assert Path("/Music/file2.wav") in results
    
    @pytest.mark.asyncio
    async def test_tag_batch_with_progress_callback(self):
        """Test batch tagging with progress callback."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "test, tag"
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            from roughcut.backend.ai.openai_client import OpenAIClient
            client = OpenAIClient(api_key="sk-test")
            tagger = MediaTagger(client)
            
            progress_calls = []
            
            def progress_callback(current, total, filename):
                progress_calls.append((current, total, filename))
            
            files = [
                (Path("/Music/file1.wav"), "music"),
                (Path("/Music/file2.wav"), "music"),
            ]
            
            await tagger.tag_batch(files, progress_callback)
            
            assert len(progress_calls) == 2
            assert progress_calls[0][0] == 1
            assert progress_calls[1][0] == 2
            assert progress_calls[0][1] == 2  # total
    
    @pytest.mark.asyncio
    async def test_tag_batch_handles_errors(self):
        """Test that batch tagging continues despite individual errors."""
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            
            # First call succeeds, second fails
            import openai
            responses = [
                MagicMock(choices=[MagicMock(message=MagicMock(content="success"))]),
                openai.RateLimitError("Rate limit", response=MagicMock(), body={}),
            ]
            mock_client.chat.completions.create = AsyncMock(side_effect=responses)
            mock_client_class.return_value = mock_client
            
            from roughcut.backend.ai.openai_client import OpenAIClient
            client = OpenAIClient(api_key="sk-test")
            tagger = MediaTagger(client)
            
            files = [
                (Path("/Music/file1.wav"), "music"),
                (Path("/Music/file2.wav"), "music"),
            ]
            
            with patch('asyncio.sleep', new=AsyncMock()):
                results = await tagger.tag_batch(files)
            
            # Both files should have results
            assert len(results) == 2
            # First succeeded
            assert results[Path("/Music/file1.wav")].tags == ["success"]
            # Second had error but returned empty tags
            assert results[Path("/Music/file2.wav")].tags == []


class TestAcceptanceCriteria:
    """Test acceptance criteria from story."""
    
    @pytest.mark.asyncio
    async def test_ac2_example_file(self):
        """Test AC#2 example: bright_corporate_theme.wav.
        
        File: "Music/Corporate/Upbeat/bright_corporate_theme.wav"
        Expected tags: "corporate", "upbeat", "bright", "theme"
        """
        with patch('roughcut.backend.ai.openai_client.openai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "corporate, upbeat, bright, theme, electronic"
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            from roughcut.backend.ai.openai_client import OpenAIClient
            client = OpenAIClient(api_key="sk-test")
            tagger = MediaTagger(client)
            
            result = await tagger.tag_media(
                Path("Music/Corporate/Upbeat/bright_corporate_theme.wav"),
                "music"
            )
            
            # AC#2 requires these specific tags
            assert "corporate" in result.tags
            assert "upbeat" in result.tags
            assert "bright" in result.tags
            assert "theme" in result.tags
