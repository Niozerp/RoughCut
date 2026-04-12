"""Unit tests for configuration settings manager."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from roughcut.config.settings import ConfigManager


class TestConfigManager(unittest.TestCase):
    """Test suite for ConfigManager class."""

    def setUp(self):
        """Set up test environment with temporary config directory."""
        # Create temp directory
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Store original environment
        self.original_home = os.environ.get("HOME")
        self.original_appdata = os.environ.get("APPDATA")
        self.original_userprofile = os.environ.get("USERPROFILE")
        
        # Set environment to use temp directory
        os.environ["HOME"] = str(self.temp_dir)
        os.environ["USERPROFILE"] = str(self.temp_dir)
        if "APPDATA" in os.environ:
            del os.environ["APPDATA"]
        
        # Reset singleton before each test
        ConfigManager.reset_instance()

    def tearDown(self):
        """Clean up test environment."""
        # Restore environment
        if self.original_home:
            os.environ["HOME"] = self.original_home
        elif "HOME" in os.environ:
            del os.environ["HOME"]
        
        if self.original_appdata:
            os.environ["APPDATA"] = self.original_appdata
        elif "APPDATA" in os.environ:
            del os.environ["APPDATA"]

        if self.original_userprofile:
            os.environ["USERPROFILE"] = self.original_userprofile
        elif "USERPROFILE" in os.environ:
            del os.environ["USERPROFILE"]
        
        # Clean up temp directory
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Reset singleton after each test
        ConfigManager.reset_instance()

    def test_singleton_pattern(self):
        """Test that ConfigManager is a singleton."""
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        
        self.assertIs(manager1, manager2)

    def test_is_notion_configured_false_initially(self):
        """Test that Notion is not configured initially."""
        manager = ConfigManager()
        
        self.assertFalse(manager.is_notion_configured())

    def test_save_notion_config_success(self):
        """Test saving valid Notion configuration."""
        manager = ConfigManager()
        
        success, message = manager.save_notion_config(
            api_token="secret_test_token_123456789012345678901234567890",
            page_url="https://www.notion.so/workspace/page-id-123456789"
        )
        
        self.assertTrue(success)
        self.assertIn("saved successfully", message)

    def test_save_notion_config_empty_token(self):
        """Test saving with empty API token fails."""
        manager = ConfigManager()
        
        success, message = manager.save_notion_config(
            api_token="",
            page_url="https://notion.so/page"
        )
        
        self.assertFalse(success)
        self.assertIn("required", message)

    def test_save_notion_config_empty_url(self):
        """Test saving with empty URL fails."""
        manager = ConfigManager()
        
        success, message = manager.save_notion_config(
            api_token="secret_valid_token_here",
            page_url=""
        )
        
        self.assertFalse(success)
        self.assertIn("required", message)

    def test_save_notion_config_invalid_token(self):
        """Test saving with invalid token format fails."""
        manager = ConfigManager()
        
        success, message = manager.save_notion_config(
            api_token="short",
            page_url="https://www.notion.so/workspace/page-id-123456789"
        )
        
        self.assertFalse(success)
        self.assertIn("too short", message)

    def test_save_notion_config_invalid_url(self):
        """Test saving with invalid URL format fails."""
        manager = ConfigManager()
        
        success, message = manager.save_notion_config(
            api_token="secret_valid_token_here",
            page_url="http://example.com/page"
        )
        
        self.assertFalse(success)
        self.assertIn("Invalid Notion page URL", message)

    def test_is_notion_configured_after_save(self):
        """Test that Notion is configured after successful save."""
        manager = ConfigManager()
        
        manager.save_notion_config(
            api_token="secret_test_token_123456789012345678901234567890",
            page_url="https://www.notion.so/workspace/page-id-123456789"
        )
        
        self.assertTrue(manager.is_notion_configured())

    def test_get_notion_config_after_save(self):
        """Test retrieving Notion config after saving."""
        manager = ConfigManager()
        
        manager.save_notion_config(
            api_token="secret_test_token_123456789012345678901234567890",
            page_url="https://www.notion.so/workspace/page-id-123456789"
        )
        
        config = manager.get_notion_config()
        
        self.assertEqual(config.page_url, "https://www.notion.so/workspace/page-id-123456789")
        self.assertTrue(config.enabled)

    def test_clear_notion_config(self):
        """Test clearing Notion configuration."""
        manager = ConfigManager()
        
        # First save config
        manager.save_notion_config(
            api_token="secret_test_token_123456789012345678901234567890",
            page_url="https://www.notion.so/workspace/page-id-123456789"
        )
        
        # Then clear it
        success, message = manager.clear_notion_config()
        
        self.assertTrue(success)
        self.assertFalse(manager.is_notion_configured())

    def test_persistence_across_instances(self):
        """Test that configuration persists across ConfigManager instances."""
        # Create and save with first instance
        manager1 = ConfigManager()
        manager1.save_notion_config(
            api_token="secret_test_token_123456789012345678901234567890",
            page_url="https://www.notion.so/workspace/page-id-123456789"
        )
        
        # Reset singleton to simulate new session
        ConfigManager.reset_instance()
        
        # Create new instance (should load from disk)
        manager2 = ConfigManager()
        
        # Verify configuration persisted
        self.assertTrue(manager2.is_notion_configured())
        config = manager2.get_notion_config()
        self.assertEqual(
            config.api_token,
            "secret_test_token_123456789012345678901234567890"
        )

    def test_config_file_permissions(self):
        """Test that config file has restrictive permissions."""
        manager = ConfigManager()
        manager.save_notion_config(
            api_token="secret_test_token_123456789012345678901234567890",
            page_url="https://www.notion.so/workspace/page-id-123456789"
        )
        
        from roughcut.config.paths import get_config_file_path
        config_path = get_config_file_path()
        
        if os.name != "nt":  # Unix-like systems
            import stat
            mode = config_path.stat().st_mode
            # Check that file permissions are 0o600
            self.assertEqual(stat.S_IMODE(mode), 0o600)

    def test_encrypted_token_in_config_file(self):
        """Test that API token is encrypted in config file."""
        manager = ConfigManager()
        
        token = "secret_test_token_123456789012345678901234567890"
        manager.save_notion_config(
            api_token=token,
            page_url="https://www.notion.so/workspace/page-id-123456789"
        )
        
        from roughcut.config.paths import get_config_file_path
        import json
        
        # Read config file directly
        config_path = get_config_file_path()
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        # Token should be encrypted (different from plaintext)
        stored_token = data['notion']['api_token']
        self.assertNotEqual(stored_token, token)
        # Encrypted token should be non-empty
        self.assertGreater(len(stored_token), 0)

    def test_reload_config(self):
        """Test reloading configuration from disk."""
        manager = ConfigManager()
        
        # Save config
        manager.save_notion_config(
            api_token="secret_test_token_123456789012345678901234567890",
            page_url="https://www.notion.so/workspace/page-id-123456789"
        )
        
        # Manually clear internal state (simulate corruption)
        manager._config_data = {}
        
        # Reload from disk
        manager.reload()
        
        # Should have loaded the saved config
        self.assertTrue(manager.is_notion_configured())

    def test_onboarding_defaults_to_incomplete(self):
        """Test onboarding is incomplete by default."""
        manager = ConfigManager()

        self.assertFalse(manager.is_onboarding_complete())
        state = manager.get_onboarding_state()
        self.assertFalse(state["completed"])
        self.assertEqual(state["configured_count"], 0)

    def test_set_onboarding_complete_persists(self):
        """Test onboarding completion persists across instances."""
        manager = ConfigManager()

        success, message = manager.set_onboarding_complete(True)

        self.assertTrue(success)
        self.assertIn("complete", message.lower())
        self.assertTrue(manager.is_onboarding_complete())

        ConfigManager.reset_instance()
        manager = ConfigManager()
        self.assertTrue(manager.is_onboarding_complete())

    def test_get_onboarding_state_reflects_configured_categories(self):
        """Test onboarding state includes configured folder coverage."""
        manager = ConfigManager()
        music_dir = self.temp_dir / "music"
        music_dir.mkdir()
        sfx_dir = self.temp_dir / "sfx"
        sfx_dir.mkdir()

        manager.save_media_folders_config(
            music_folder=str(music_dir),
            sfx_folder=str(sfx_dir),
        )

        state = manager.get_onboarding_state()

        self.assertFalse(state["completed"])
        self.assertEqual(state["configured_count"], 2)
        self.assertTrue(state["folders"]["music"])
        self.assertTrue(state["folders"]["sfx"])
        self.assertFalse(state["folders"]["vfx"])
        self.assertFalse(state["has_invalid_folders"])
        self.assertEqual(state["invalid_folders"], {})

    def test_get_onboarding_state_ignores_missing_saved_folder_paths(self):
        """Test missing saved folder paths are not counted as configured."""
        manager = ConfigManager()
        missing_music = self.temp_dir / "missing-music"

        success, message, errors = manager.save_media_folders_config(
            music_folder=str(missing_music),
        )

        self.assertFalse(success)
        self.assertIn("Validation failed", message)
        self.assertIn("music", errors)

        manager._config_data["media_folders"] = {
            "music_folder": str(missing_music),
            "sfx_folder": None,
            "vfx_folder": None,
        }

        state = manager.get_onboarding_state()

        self.assertEqual(state["configured_count"], 0)
        self.assertFalse(state["folders"]["music"])
        self.assertTrue(state["has_invalid_folders"])

    def test_get_onboarding_state_marks_completed_false_when_saved_paths_invalid(self):
        """Test invalid saved paths force onboarding back into incomplete state."""
        manager = ConfigManager()
        missing_music = self.temp_dir / "missing-music"

        manager._config_data["media_folders"] = {
            "music_folder": str(missing_music),
            "sfx_folder": None,
            "vfx_folder": None,
        }
        manager._config_data["onboarding_completed"] = True

        state = manager.get_onboarding_state()

        self.assertFalse(state["completed"])
        self.assertTrue(manager.is_onboarding_complete())
        self.assertTrue(state["has_invalid_folders"])
        self.assertIn("music", state["invalid_folders"])

    def test_get_onboarding_state_preserves_completed_true_for_valid_partial_setup(self):
        """Test valid partial setup remains complete after onboarding is finished."""
        manager = ConfigManager()
        music_dir = self.temp_dir / "music"
        sfx_dir = self.temp_dir / "sfx"
        music_dir.mkdir()
        sfx_dir.mkdir()

        success, _, errors = manager.save_media_folders_config(
            music_folder=str(music_dir),
            sfx_folder=str(sfx_dir),
            vfx_folder=None,
        )
        self.assertTrue(success)
        self.assertEqual(errors, {})

        manager.set_onboarding_complete(True)
        state = manager.get_onboarding_state()

        self.assertTrue(state["completed"])
        self.assertEqual(state["configured_count"], 2)
        self.assertFalse(state["has_invalid_folders"])
        self.assertEqual(state["invalid_folders"], {})

    def test_get_onboarding_state_returns_invalid_folder_errors(self):
        """Test onboarding state surfaces per-category invalid folder errors."""
        manager = ConfigManager()
        missing_music = self.temp_dir / "missing-music"
        missing_sfx = self.temp_dir / "missing-sfx"

        manager._config_data["media_folders"] = {
            "music_folder": str(missing_music),
            "sfx_folder": str(missing_sfx),
            "vfx_folder": None,
        }

        state = manager.get_onboarding_state()

        self.assertTrue(state["has_invalid_folders"])
        self.assertIn("music", state["invalid_folders"])
        self.assertIn("sfx", state["invalid_folders"])
        self.assertNotIn("vfx", state["invalid_folders"])

    def test_spacetime_runtime_state_updates_without_overwriting_token(self):
        """Test runtime metadata updates preserve existing encrypted token."""
        manager = ConfigManager()

        success, _ = manager.save_spacetime_config(
            host="localhost",
            port=3000,
            database_name="roughcut",
            identity_token="runtime-token",
            module_path="/module/path",
        )
        self.assertTrue(success)

        success, _ = manager.update_spacetime_runtime_state(
            data_dir="/data/path",
            binary_path="/bin/spacetime",
            binary_version="2.0.0",
            module_published=True,
            module_fingerprint="source-123",
            published_fingerprint="source-123",
            last_ready_at="2026-04-11T12:00:00Z",
            last_health_check_at="2026-04-11T12:00:05Z",
        )
        self.assertTrue(success)

        config = manager.get_spacetime_config()
        self.assertEqual(config["identity_token"], "runtime-token")
        self.assertEqual(config["data_dir"], "/data/path")
        self.assertEqual(config["binary_path"], "/bin/spacetime")
        self.assertEqual(config["binary_version"], "2.0.0")
        self.assertTrue(config["module_published"])
        self.assertEqual(config["module_fingerprint"], "source-123")
        self.assertEqual(config["published_fingerprint"], "source-123")
        self.assertEqual(config["last_ready_at"], "2026-04-11T12:00:00Z")
        self.assertEqual(config["last_health_check_at"], "2026-04-11T12:00:05Z")


class TestConfigManagerGracefulDegradation(unittest.TestCase):
    """Test graceful degradation when config is missing or invalid."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_home = os.environ.get("HOME")
        self.original_userprofile = os.environ.get("USERPROFILE")
        os.environ["HOME"] = str(self.temp_dir)
        os.environ["USERPROFILE"] = str(self.temp_dir)
        if "APPDATA" in os.environ:
            del os.environ["APPDATA"]
        
        ConfigManager.reset_instance()

    def tearDown(self):
        """Clean up."""
        if self.original_home:
            os.environ["HOME"] = self.original_home
        elif "HOME" in os.environ:
            del os.environ["HOME"]

        if self.original_userprofile:
            os.environ["USERPROFILE"] = self.original_userprofile
        elif "USERPROFILE" in os.environ:
            del os.environ["USERPROFILE"]
        
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        ConfigManager.reset_instance()

    def test_graceful_handling_no_config_file(self):
        """Test graceful handling when no config file exists."""
        manager = ConfigManager()
        
        # Should not raise error
        self.assertFalse(manager.is_notion_configured())
        config = manager.get_notion_config()
        self.assertIsNotNone(config)
        self.assertFalse(config.enabled)

    def test_graceful_handling_corrupted_config(self):
        """Test graceful handling of corrupted config file."""
        # Create corrupted config file
        config_dir = self.temp_dir / ".config" / "roughcut"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text("{invalid json")
        
        manager = ConfigManager()
        
        # Should not raise error, should return empty config
        self.assertFalse(manager.is_notion_configured())


if __name__ == "__main__":
    unittest.main()
