"""Tests for AI protocol handlers.

Tests JSON-RPC handlers for rough cut AI generation initiation.
"""

import json
import pytest
from unittest.mock import Mock, patch

from roughcut.protocols.handlers.ai import (
    initiate_rough_cut,
    initiate_rough_cut_with_progress,
    AI_HANDLERS,
    ERROR_CODES
)
from roughcut.backend.workflows.session import RoughCutSession, SessionManager, reset_session_manager


class TestInitiateRoughCut:
    """Tests for initiate_rough_cut handler."""
    
    @pytest.fixture(autouse=True)
    def reset_sessions(self):
        """Reset session manager before each test."""
        reset_session_manager()
        yield
        reset_session_manager()
    
    @pytest.fixture
    def valid_session(self):
        """Create a valid session with all required data."""
        from roughcut.backend.workflows.session import get_session_manager
        
        session_manager = get_session_manager()
        session = session_manager.create_session()
        
        # Simulate workflow steps to reach format_selected state
        session.select_media("clip_001", "Test_Interview.mp4")
        session.transcription_data = {
            "text": "This is a test transcript for rough cut generation.",
            "segments": [],
            "quality": "good"
        }
        session.status = "transcription_reviewed"
        
        # Mock format template
        from roughcut.backend.formats.models import FormatTemplate, TemplateSegment, AssetGroup
        template = FormatTemplate(
            slug="test-format",
            name="Test Format",
            description="A test format template",
            structure={},
            segments=[
                TemplateSegment(
                    name="Intro",
                    start_time="0:00",
                    end_time="0:15",
                    duration="15s",
                    purpose="Hook"
                )
            ],
            asset_groups=[
                AssetGroup(
                    category="music",
                    name="intro_music",
                    description="Intro music",
                    search_tags=["upbeat", "corporate"]
                )
            ]
        )
        session.select_format(template)
        session_manager.update_session(session)
        
        return session
    
    def test_initiate_with_valid_data(self, valid_session):
        """Test initiating rough cut with valid session and data."""
        # Mock settings
        with patch('roughcut.protocols.handlers.ai.get_settings') as mock_settings:
            mock_settings.return_value = {"openai_api_key": "test-key"}
            
            # Mock OpenAIClient
            with patch('roughcut.protocols.handlers.ai.OpenAIClient') as mock_client:
                mock_client_instance = Mock()
                mock_client.return_value = mock_client_instance
                
                # Mock RoughCutOrchestrator
                with patch('roughcut.protocols.handlers.ai.RoughCutOrchestrator') as mock_orch:
                    mock_orch_instance = Mock()
                    mock_orch.return_value = mock_orch_instance
                    
                    params = {
                        "session_id": valid_session.session_id,
                        "rough_cut_data": {
                            "session_id": valid_session.session_id,
                            "media": {"clip_id": "clip_001", "clip_name": "Test_Interview.mp4"},
                            "transcription": {"text": "Test transcript"},
                            "format": {"slug": "test-format", "name": "Test Format"}
                        }
                    }
                    
                    result = initiate_rough_cut(params)
                    
                    assert "result" in result
                    assert result["result"]["session_id"] == valid_session.session_id
                    assert result["result"]["status"] == "initiated"
                    assert "rough_cut_id" in result["result"]
    
    def test_initiate_missing_params(self):
        """Test initiating without required parameters."""
        result = initiate_rough_cut(None)
        
        assert "error" in result
        assert result["error"]["code"] == ERROR_CODES["INVALID_PARAMS"]
    
    def test_initiate_missing_session_id(self):
        """Test initiating without session_id."""
        params = {
            "rough_cut_data": {"transcription": {"text": "test"}}
        }
        
        result = initiate_rough_cut(params)
        
        assert "error" in result
        assert result["error"]["code"] == ERROR_CODES["INVALID_PARAMS"]
        assert "session_id" in result["error"]["message"]
    
    def test_initiate_missing_rough_cut_data(self):
        """Test initiating without rough_cut_data."""
        params = {
            "session_id": "test-session-id"
        }
        
        result = initiate_rough_cut(params)
        
        assert "error" in result
        assert result["error"]["code"] == ERROR_CODES["INVALID_PARAMS"]
        assert "rough_cut_data" in result["error"]["message"]
    
    def test_initiate_invalid_session_state(self, valid_session):
        """Test initiating when session is not in correct state."""
        # Change session to wrong state
        from roughcut.backend.workflows.session import get_session_manager
        session_manager = get_session_manager()
        valid_session.status = "created"  # Wrong state
        session_manager.update_session(valid_session)
        
        params = {
            "session_id": valid_session.session_id,
            "rough_cut_data": {"transcription": {"text": "test"}}
        }
        
        with patch('roughcut.protocols.handlers.ai.get_settings') as mock_settings:
            mock_settings.return_value = {"openai_api_key": "test-key"}
            
            result = initiate_rough_cut(params)
            
            assert "error" in result
            assert result["error"]["code"] == ERROR_CODES["INVALID_STATE"]
    
    def test_initiate_session_not_found(self):
        """Test initiating with non-existent session."""
        params = {
            "session_id": "non-existent-session",
            "rough_cut_data": {"transcription": {"text": "test"}}
        }
        
        result = initiate_rough_cut(params)
        
        assert "error" in result
        assert result["error"]["code"] == ERROR_CODES["SESSION_NOT_FOUND"]
    
    def test_initiate_missing_api_key(self, valid_session):
        """Test initiating when AI is not configured."""
        params = {
            "session_id": valid_session.session_id,
            "rough_cut_data": {"transcription": {"text": "test"}}
        }
        
        with patch('roughcut.protocols.handlers.ai.get_settings') as mock_settings:
            mock_settings.return_value = {}  # No API key
            
            result = initiate_rough_cut(params)
            
            assert "error" in result
            assert result["error"]["code"] == ERROR_CODES["AI_CONFIG_ERROR"]
            assert "API key" in result["error"]["message"]


class TestInitiateRoughCutWithProgress:
    """Tests for initiate_rough_cut_with_progress streaming handler."""
    
    @pytest.fixture(autouse=True)
    def reset_sessions(self):
        """Reset session manager before each test."""
        reset_session_manager()
        yield
        reset_session_manager()
    
    @pytest.fixture
    def valid_session(self):
        """Create a valid session with all required data."""
        from roughcut.backend.workflows.session import get_session_manager
        
        session_manager = get_session_manager()
        session = session_manager.create_session()
        
        # Simulate workflow steps
        session.select_media("clip_001", "Test_Interview.mp4")
        session.transcription_data = {
            "text": "Test transcript",
            "segments": [],
            "quality": "good"
        }
        session.status = "transcription_reviewed"
        
        from roughcut.backend.formats.models import FormatTemplate
        template = FormatTemplate(
            slug="test-format",
            name="Test Format",
            description="Test",
            structure={},
            segments=[],
            asset_groups=[]
        )
        session.select_format(template)
        session_manager.update_session(session)
        
        return session
    
    def test_progress_updates_structure(self, valid_session):
        """Test that progress updates have correct structure."""
        params = {
            "session_id": valid_session.session_id,
            "rough_cut_data": {
                "session_id": valid_session.session_id,
                "media": {"clip_id": "clip_001", "clip_name": "Test.mp4"},
                "transcription": {"text": "Test"},
                "format": {"slug": "test", "name": "Test"}
            }
        }
        
        with patch('roughcut.protocols.handlers.ai.get_settings') as mock_settings:
            mock_settings.return_value = {"openai_api_key": "test-key"}
            
            with patch('roughcut.protocols.handlers.ai.OpenAIClient'):
                with patch('roughcut.protocols.handlers.ai.RoughCutOrchestrator'):
                    updates = list(initiate_rough_cut_with_progress(params))
                    
                    # Check that we get progress updates
                    progress_updates = [u for u in updates if u.get("type") == "progress"]
                    assert len(progress_updates) >= 3
                    
                    # Check progress structure
                    for update in progress_updates:
                        assert "operation" in update
                        assert "current" in update
                        assert "total" in update
                        assert "message" in update
                    
                    # Check final result
                    final_result = updates[-1]
                    assert "result" in final_result
    
    def test_progress_invalid_params(self):
        """Test progress handler with invalid parameters."""
        updates = list(initiate_rough_cut_with_progress(None))
        
        assert len(updates) == 1
        assert "error" in updates[0]
        assert updates[0]["error"]["code"] == ERROR_CODES["INVALID_PARAMS"]


class TestAIHandlersRegistry:
    """Tests for AI handler registry."""
    
    def test_handlers_registry_contains_initiate(self):
        """Test that AI_HANDLERS contains initiate_rough_cut."""
        assert "initiate_rough_cut" in AI_HANDLERS
        assert AI_HANDLERS["initiate_rough_cut"] == initiate_rough_cut
    
    def test_error_codes_defined(self):
        """Test that all expected error codes are defined."""
        expected_codes = [
            "INVALID_PARAMS",
            "SESSION_NOT_FOUND",
            "INVALID_STATE",
            "AI_INITIATE_ERROR",
            "AI_CONFIG_ERROR",
            "AI_TIMEOUT"
        ]
        
        for code in expected_codes:
            assert code in ERROR_CODES
            assert ERROR_CODES[code] == code
