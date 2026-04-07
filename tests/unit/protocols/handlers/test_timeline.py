"""Compatibility tests for the packaged RoughCut timeline handlers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


PACKAGE_SRC = Path(__file__).resolve().parents[4] / "roughcut" / "src"
PACKAGE_ROOT = PACKAGE_SRC / "roughcut"

if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

roughcut_package = sys.modules.get("roughcut")
if roughcut_package is not None and hasattr(roughcut_package, "__path__"):
    roughcut_paths = [str(path) for path in roughcut_package.__path__]
    if str(PACKAGE_ROOT) not in roughcut_paths:
        roughcut_package.__path__.append(str(PACKAGE_ROOT))

from roughcut.protocols.handlers.timeline import (  # noqa: E402
    ERROR_CODES,
    _error_response,
    create_timeline,
    create_timeline_from_document,
    import_suggested_media,
)


class TestErrorResponse(unittest.TestCase):
    """Test the packaged error response helper."""

    def test_error_response_structure(self) -> None:
        result = _error_response(
            code="TEST_ERROR",
            category="test",
            message="Test message",
            suggestion="Test suggestion",
            recoverable=True,
        )

        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], "TEST_ERROR")
        self.assertEqual(result["error"]["category"], "test")
        self.assertTrue(result["error"]["recoverable"])


class TestCreateTimeline(unittest.TestCase):
    """Test the packaged timeline creation handlers."""

    @patch("roughcut.protocols.handlers.timeline.TimelineBuilder")
    def test_create_timeline_success(self, mock_builder_class: MagicMock) -> None:
        mock_builder = MagicMock()
        mock_builder_class.return_value = mock_builder

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.timeline_name = "Test_Timeline"
        mock_result.timeline_id = "timeline_123"
        mock_result.tracks_created = {"video": 1, "audio": 2}
        mock_builder.create_timeline.return_value = mock_result

        result = create_timeline({"source_clip_name": "clip", "format_template": "format"})

        self.assertTrue(result["success"])
        self.assertEqual(result["timeline_name"], "Test_Timeline")
        self.assertEqual(result["timeline_id"], "timeline_123")

    def test_create_timeline_missing_source_clip(self) -> None:
        result = create_timeline({"format_template": "format"})

        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["MISSING_SOURCE_CLIP"])

    @patch("roughcut.protocols.handlers.timeline.get_session_manager")
    @patch("roughcut.protocols.handlers.timeline.TimelineBuilder")
    def test_create_timeline_from_document_success(
        self,
        mock_builder_class: MagicMock,
        mock_get_session_manager: MagicMock,
    ) -> None:
        mock_session_manager = MagicMock()
        mock_get_session_manager.return_value = mock_session_manager
        mock_session_manager.get_session.return_value = {
            "source_clip": {"name": "source"},
            "format_template": {"name": "format"},
        }

        mock_builder = MagicMock()
        mock_builder_class.return_value = mock_builder

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.timeline_name = "Timeline"
        mock_result.timeline_id = "timeline_123"
        mock_result.tracks_created = {}
        mock_builder.create_timeline.return_value = mock_result

        result = create_timeline_from_document({"session_id": "session_123"})

        self.assertTrue(result["success"])
        mock_session_manager.update_session.assert_called_once()


class TestImportSuggestedMedia(unittest.TestCase):
    """Test the packaged media import handler."""

    @patch("roughcut.protocols.handlers.timeline.MediaImporter")
    def test_import_suggested_media_success(self, mock_importer_class: MagicMock) -> None:
        mock_importer = MagicMock()
        mock_importer_class.return_value = mock_importer

        mock_result = MagicMock()
        mock_result.imported_count = 1
        mock_result.skipped_count = 0
        mock_result.media_pool_refs = [
            MagicMock(file_path="/path/to/music.mp3", media_pool_id="media_001", media_type="music")
        ]
        mock_result.skipped_files = []
        mock_result.success = True
        mock_importer.import_suggested_media.return_value = mock_result

        result = import_suggested_media(
            {"suggested_media": [{"file_path": "/path/to/music.mp3", "media_type": "music"}]}
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["imported_count"], 1)

    def test_import_suggested_media_missing_params(self) -> None:
        result = import_suggested_media({"timeline_id": "timeline_123"})

        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ERROR_CODES["MISSING_SUGGESTED_MEDIA"])


if __name__ == "__main__":
    unittest.main()
