"""Unit tests for workflow session management.

Tests the RoughCutSession and SessionManager classes.
"""

from __future__ import annotations

import threading
import unittest
from datetime import datetime, timedelta

from roughcut.backend.workflows.session import (
    MAX_SESSIONS,
    RoughCutSession,
    SessionManager,
    SessionStatus,
    get_session_manager,
    reset_session_manager
)
from roughcut.backend.formats.models import FormatTemplate, TemplateSegment, AssetGroup
from pathlib import Path


class TestSessionStatus(unittest.TestCase):
    """Test cases for SessionStatus enum."""
    
    def test_session_status_values(self):
        """Test that all expected status values exist."""
        self.assertEqual(SessionStatus.CREATED.value, "created")
        self.assertEqual(SessionStatus.MEDIA_SELECTED.value, "media_selected")
        self.assertEqual(SessionStatus.TRANSCRIPTION_REVIEWED.value, "transcription_reviewed")
        self.assertEqual(SessionStatus.FORMAT_SELECTED.value, "format_selected")
        self.assertEqual(SessionStatus.GENERATING.value, "generating")
        self.assertEqual(SessionStatus.COMPLETE.value, "complete")
    
    def test_session_status_from_string(self):
        """Test creating status from string."""
        status = SessionStatus("created")
        self.assertEqual(status, SessionStatus.CREATED)


class TestRoughCutSession(unittest.TestCase):
    """Test cases for RoughCutSession dataclass."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.session_id = "test-session-123"
        self.created_at = datetime.now()
        self.session = RoughCutSession(
            session_id=self.session_id,
            created_at=self.created_at,
            status=SessionStatus.CREATED.value
        )
        
        # Create a test format template
        self.test_template = FormatTemplate(
            slug="test-template",
            name="Test Template",
            description="A test template for unit tests",
            file_path=Path("/test/template.md"),
            structure="Test structure",
            segments=[
                TemplateSegment(
                    name="Hook",
                    start_time="0:00",
                    end_time="0:15",
                    duration="15 seconds",
                    purpose="Grab attention"
                )
            ],
            asset_groups=[
                AssetGroup(
                    category="Music",
                    name="intro_music",
                    description="Intro music track",
                    search_tags=["upbeat", "corporate"]
                )
            ]
        )
    
    def test_session_creation(self):
        """Test session initialization."""
        self.assertEqual(self.session.session_id, self.session_id)
        self.assertEqual(self.session.status, SessionStatus.CREATED.value)
        self.assertIsNone(self.session.media_clip_id)
        self.assertIsNone(self.session.format_template_id)
        self.assertIsNotNone(self.session.last_accessed)
    
    def test_session_creation_invalid_status(self):
        """Test that invalid status raises ValueError."""
        with self.assertRaises(ValueError) as context:
            RoughCutSession(
                session_id="test",
                created_at=datetime.now(),
                status="invalid_status"
            )
        self.assertIn("Invalid status", str(context.exception))
    
    def test_session_creation_empty_session_id(self):
        """Test that empty session_id raises ValueError."""
        with self.assertRaises(ValueError) as context:
            RoughCutSession(
                session_id="",
                created_at=datetime.now(),
                status=SessionStatus.CREATED.value
            )
        self.assertIn("session_id must be a non-empty string", str(context.exception))
    
    def test_post_init_sets_last_accessed(self):
        """Test that __post_init__ sets last_accessed if not provided."""
        session = RoughCutSession(
            session_id="test-123",
            created_at=datetime.now()
        )
        self.assertIsNotNone(session.last_accessed)
        self.assertIsInstance(session.last_accessed, datetime)
    
    def test_select_media_success(self):
        """Test successful media selection."""
        self.session.select_media("clip_001", "Test Clip")
        
        self.assertEqual(self.session.media_clip_id, "clip_001")
        self.assertEqual(self.session.media_clip_name, "Test Clip")
        self.assertEqual(self.session.status, SessionStatus.MEDIA_SELECTED.value)
    
    def test_select_media_empty_clip_id(self):
        """Test that empty clip_id raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.session.select_media("", "Test Clip")
        self.assertIn("clip_id must be a non-empty string", str(context.exception))
    
    def test_select_media_empty_clip_name(self):
        """Test that empty clip_name raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.session.select_media("clip_001", "")
        self.assertIn("clip_name must be a non-empty string", str(context.exception))
    
    def test_select_media_from_wrong_state(self):
        """Test that selecting media from wrong state raises ValueError."""
        self.session.select_media("clip_001", "Test Clip")
        
        with self.assertRaises(ValueError) as context:
            self.session.select_media("clip_002", "Another Clip")
        
        self.assertIn("Cannot select media from status", str(context.exception))
    
    def test_review_transcription_success(self):
        """Test successful transcription review."""
        # First select media
        self.session.select_media("clip_001", "Test Clip")
        
        # Then review transcription
        transcription_data = {
            "text": "Test transcription",
            "segments": [{"start": 0, "end": 10}]
        }
        self.session.review_transcription(transcription_data)
        
        self.assertEqual(self.session.transcription_data, transcription_data)
        self.assertEqual(self.session.status, SessionStatus.TRANSCRIPTION_REVIEWED.value)
    
    def test_review_transcription_from_wrong_state(self):
        """Test that reviewing transcription from wrong state raises ValueError."""
        # Try to review transcription without selecting media first
        with self.assertRaises(ValueError) as context:
            self.session.review_transcription({"text": "test"})
        
        self.assertIn("Cannot review transcription from status", str(context.exception))
    
    def test_review_transcription_invalid_data(self):
        """Test that invalid transcription_data raises ValueError."""
        self.session.select_media("clip_001", "Test Clip")
        
        with self.assertRaises(ValueError) as context:
            self.session.review_transcription(None)
        
        self.assertIn("transcription_data must be a non-empty dictionary", str(context.exception))
    
    def test_select_format_success(self):
        """Test successful format selection."""
        # First go through prerequisite steps
        self.session.select_media("clip_001", "Test Clip")
        self.session.review_transcription({"text": "test"})
        
        # Now select format
        self.session.select_format(self.test_template)
        
        self.assertEqual(self.session.format_template_id, "test-template")
        self.assertEqual(self.session.format_template, self.test_template)
        self.assertEqual(self.session.status, SessionStatus.FORMAT_SELECTED.value)
    
    def test_select_format_from_wrong_state(self):
        """Test that selecting format from wrong state raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.session.select_format(self.test_template)
        
        self.assertIn("Cannot select format from status", str(context.exception))
    
    def test_select_format_invalid_template(self):
        """Test that selecting invalid template raises ValueError."""
        # First go to correct state
        self.session.select_media("clip_001", "Test Clip")
        self.session.review_transcription({"text": "test"})
        
        # Try to select invalid template
        invalid_template = FormatTemplate(
            slug="",
            name="Invalid",
            description="Invalid template",
            file_path=Path("/test.md")
        )
        
        with self.assertRaises(ValueError) as context:
            self.session.select_format(invalid_template)
        
        self.assertIn("Invalid template: must have slug", str(context.exception))
    
    def test_can_select_format(self):
        """Test can_select_format logic."""
        # Initially cannot select format
        self.assertFalse(self.session.can_select_format())
        
        # After transcription review, can select format
        self.session.select_media("clip_001", "Test Clip")
        self.session.review_transcription({"text": "test"})
        self.assertTrue(self.session.can_select_format())
        
        # After format selected, CANNOT select again (must be from TRANSCRIPTION_REVIEWED)
        self.session.select_format(self.test_template)
        self.assertFalse(self.session.can_select_format())
    
    def test_can_generate(self):
        """Test can_generate logic."""
        # Initially cannot generate
        self.assertFalse(self.session.can_generate())
        
        # After media only, cannot generate
        self.session.select_media("clip_001", "Test Clip")
        self.assertFalse(self.session.can_generate())
        
        # After transcription, still cannot generate
        self.session.review_transcription({"text": "test"})
        self.assertFalse(self.session.can_generate())
        
        # After format selected, can generate
        self.session.select_format(self.test_template)
        self.assertTrue(self.session.can_generate())
    
    def test_start_generation_success(self):
        """Test successful generation start."""
        # Complete all prerequisite steps
        self.session.select_media("clip_001", "Test Clip")
        self.session.review_transcription({"text": "test"})
        self.session.select_format(self.test_template)
        
        # Start generation
        self.session.start_generation()
        
        self.assertEqual(self.session.status, SessionStatus.GENERATING.value)
    
    def test_start_generation_from_wrong_state(self):
        """Test that starting generation from wrong state raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.session.start_generation()
        
        self.assertIn("Must be in 'format_selected' state", str(context.exception))
    
    def test_start_generation_already_generating(self):
        """Test that starting generation when already generating raises ValueError."""
        # Complete all prerequisite steps
        self.session.select_media("clip_001", "Test Clip")
        self.session.review_transcription({"text": "test"})
        self.session.select_format(self.test_template)
        self.session.start_generation()
        
        # Try to start again
        with self.assertRaises(ValueError) as context:
            self.session.start_generation()
        
        self.assertIn("Generation already in progress", str(context.exception))
    
    def test_start_generation_missing_data(self):
        """Test that starting generation with missing data raises ValueError."""
        # Force status to format_selected without proper data
        self.session.status = SessionStatus.FORMAT_SELECTED.value
        
        with self.assertRaises(ValueError) as context:
            self.session.start_generation()
        
        self.assertIn("media_clip_id is missing", str(context.exception))
    
    def test_complete_success(self):
        """Test successful completion."""
        # Complete all steps
        self.session.select_media("clip_001", "Test Clip")
        self.session.review_transcription({"text": "test"})
        self.session.select_format(self.test_template)
        self.session.start_generation()
        
        # Complete
        self.session.complete()
        
        self.assertEqual(self.session.status, SessionStatus.COMPLETE.value)
    
    def test_complete_from_wrong_state(self):
        """Test that completing from wrong state raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.session.complete()
        
        self.assertIn("Cannot complete from status", str(context.exception))
    
    def test_to_dict(self):
        """Test session serialization to dict."""
        self.session.select_media("clip_001", "Test Clip")
        
        result = self.session.to_dict()
        
        self.assertEqual(result["session_id"], self.session_id)
        self.assertEqual(result["status"], SessionStatus.MEDIA_SELECTED.value)
        self.assertEqual(result["media_clip_id"], "clip_001")
        self.assertEqual(result["media_clip_name"], "Test Clip")
        self.assertIn("can_generate", result)
        self.assertFalse(result["can_generate"])
    
    def test_get_generation_data(self):
        """Test getting data for generation."""
        # Complete all steps
        self.session.select_media("clip_001", "Test Clip")
        self.session.review_transcription({"text": "test transcription"})
        self.session.select_format(self.test_template)
        
        data = self.session.get_generation_data()
        
        self.assertEqual(data["session_id"], self.session_id)
        self.assertEqual(data["media_clip_id"], "clip_001")
        self.assertEqual(data["transcription"]["text"], "test transcription")
        self.assertEqual(data["format_template"]["slug"], "test-template")
        self.assertEqual(len(data["format_template"]["segments"]), 1)
        self.assertEqual(len(data["format_template"]["asset_groups"]), 1)
    
    def test_get_generation_data_from_wrong_state(self):
        """Test that getting generation data from wrong state raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.session.get_generation_data()
        
        self.assertIn("Session not ready for generation", str(context.exception))
    
    def test_last_accessed_updated(self):
        """Test that last_accessed is updated on each operation."""
        initial_time = self.session.last_accessed
        
        # Wait a tiny bit and perform operation
        import time
        time.sleep(0.01)
        
        self.session.select_media("clip_001", "Test Clip")
        
        self.assertGreater(self.session.last_accessed, initial_time)


class TestSessionManager(unittest.TestCase):
    """Test cases for SessionManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_session_manager()
        self.manager = get_session_manager()
    
    def tearDown(self):
        """Clean up after tests."""
        reset_session_manager()
    
    def test_create_session(self):
        """Test creating a new session."""
        session = self.manager.create_session()
        
        self.assertIsNotNone(session.session_id)
        self.assertEqual(session.status, SessionStatus.CREATED.value)
        self.assertIsNotNone(session.created_at)
        
        # Verify session is stored
        self.assertTrue(self.manager.session_exists(session.session_id))
    
    def test_create_session_limit(self):
        """Test that session limit is enforced."""
        # Create sessions up to limit
        for i in range(MAX_SESSIONS):
            self.manager.create_session()
        
        # Next creation should fail
        with self.assertRaises(RuntimeError) as context:
            self.manager.create_session()
        
        self.assertIn("Session limit exceeded", str(context.exception))
    
    def test_get_session(self):
        """Test retrieving a session."""
        session = self.manager.create_session()
        retrieved = self.manager.get_session(session.session_id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.session_id, session.session_id)
    
    def test_get_session_not_found(self):
        """Test retrieving non-existent session returns None."""
        retrieved = self.manager.get_session("non-existent-id")
        self.assertIsNone(retrieved)
    
    def test_update_session(self):
        """Test updating a session."""
        session = self.manager.create_session()
        
        # Modify session
        session.select_media("clip_001", "Test Clip")
        
        # Update in manager
        self.manager.update_session(session)
        
        # Retrieve and verify
        retrieved = self.manager.get_session(session.session_id)
        self.assertEqual(retrieved.status, SessionStatus.MEDIA_SELECTED.value)
        self.assertEqual(retrieved.media_clip_id, "clip_001")
    
    def test_update_session_not_found(self):
        """Test that updating non-existent session raises ValueError."""
        # Create session without adding to manager
        session = RoughCutSession(
            session_id="ghost-session",
            created_at=datetime.now(),
            status=SessionStatus.CREATED.value
        )
        
        with self.assertRaises(ValueError) as context:
            self.manager.update_session(session)
        
        self.assertIn("Session not found", str(context.exception))
    
    def test_delete_session(self):
        """Test deleting a session."""
        session = self.manager.create_session()
        session_id = session.session_id
        
        result = self.manager.delete_session(session_id)
        
        self.assertTrue(result)
        self.assertFalse(self.manager.session_exists(session_id))
    
    def test_delete_session_not_found(self):
        """Test deleting non-existent session returns False."""
        result = self.manager.delete_session("non-existent")
        self.assertFalse(result)
    
    def test_session_exists(self):
        """Test session existence check."""
        session = self.manager.create_session()
        
        self.assertTrue(self.manager.session_exists(session.session_id))
        self.assertFalse(self.manager.session_exists("non-existent"))
    
    def test_list_sessions(self):
        """Test listing all sessions."""
        # Create multiple sessions
        session1 = self.manager.create_session()
        session2 = self.manager.create_session()
        session3 = self.manager.create_session()
        
        sessions = self.manager.list_sessions()
        
        self.assertEqual(len(sessions), 3)
        self.assertIn(session1.session_id, sessions)
        self.assertIn(session2.session_id, sessions)
        self.assertIn(session3.session_id, sessions)
    
    def test_cleanup_expired(self):
        """Test cleaning up expired sessions."""
        # Create session
        session = self.manager.create_session()
        
        # Manually set last_accessed to be old
        session.last_accessed = datetime.now() - timedelta(minutes=90)
        self.manager.update_session(session)
        
        # Clean up sessions older than 60 minutes
        cleaned = self.manager.cleanup_expired(60)
        
        self.assertEqual(cleaned, 1)
        self.assertFalse(self.manager.session_exists(session.session_id))
    
    def test_cleanup_expired_invalid_input(self):
        """Test that invalid max_age_minutes raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.manager.cleanup_expired(-10)
        
        self.assertIn("max_age_minutes must be positive", str(context.exception))
    
    def test_cleanup_expired_zero_input(self):
        """Test that zero max_age_minutes raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.manager.cleanup_expired(0)
        
        self.assertIn("max_age_minutes must be positive", str(context.exception))
    
    def test_cleanup_expired_not_expired(self):
        """Test that non-expired sessions are not cleaned up."""
        session = self.manager.create_session()
        
        # Clean up sessions older than 60 minutes (session is fresh)
        cleaned = self.manager.cleanup_expired(60)
        
        self.assertEqual(cleaned, 0)
        self.assertTrue(self.manager.session_exists(session.session_id))
    
    def test_clear_all_sessions(self):
        """Test clearing all sessions."""
        # Create some sessions
        self.manager.create_session()
        self.manager.create_session()
        self.manager.create_session()
        
        # Clear all
        count = self.manager.clear_all_sessions()
        
        self.assertEqual(count, 3)
        self.assertEqual(len(self.manager.list_sessions()), 0)
    
    def test_get_session_manager_singleton(self):
        """Test that get_session_manager returns singleton."""
        manager1 = get_session_manager()
        manager2 = get_session_manager()
        
        self.assertIs(manager1, manager2)
    
    def test_reset_session_manager(self):
        """Test that reset creates new manager instance and clears sessions."""
        manager1 = get_session_manager()
        
        # Create a session
        session = manager1.create_session()
        
        # Reset
        reset_session_manager()
        
        # Get new manager
        manager2 = get_session_manager()
        
        # Should be different instance
        self.assertIsNot(manager1, manager2)
        
        # Session should not exist in new manager
        self.assertFalse(manager2.session_exists(session.session_id))
    
    def test_thread_safe_singleton(self):
        """Test that singleton initialization is thread-safe."""
        reset_session_manager()
        
        managers = []
        errors = []
        
        def get_manager():
            try:
                manager = get_session_manager()
                managers.append(manager)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads trying to get the manager simultaneously
        threads = [threading.Thread(target=get_manager) for _ in range(10)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # All threads should get the same manager instance
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(set(id(m) for m in managers)), 1)


if __name__ == "__main__":
    unittest.main()
