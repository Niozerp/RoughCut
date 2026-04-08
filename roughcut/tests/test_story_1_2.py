"""Layout and module smoke tests for the Story 1.2 Lua UI assets."""

from __future__ import annotations

import unittest
from pathlib import Path


class TestStory1_2UIComponents(unittest.TestCase):
    """Verify the current launcher and UI module layout."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[1]
        cls.launcher_lua = cls.project_root / "RoughCut.lua"
        cls.main_module_lua = cls.project_root / "lua" / "roughcut_main.lua"
        cls.lua_ui_dir = cls.project_root / "lua" / "ui"
        cls.main_window_lua = cls.lua_ui_dir / "main_window.lua"
        cls.navigation_lua = cls.lua_ui_dir / "navigation.lua"
        cls.install_dialog_lua = cls.lua_ui_dir / "install_dialog.lua"
        cls.install_orchestrator_lua = cls.project_root / "lua" / "install_orchestrator.lua"

    def test_launcher_exists(self) -> None:
        self.assertTrue(self.launcher_lua.exists(), f"Launcher missing: {self.launcher_lua}")

    def test_lua_ui_directory_exists(self) -> None:
        self.assertTrue(self.lua_ui_dir.exists(), f"UI directory missing: {self.lua_ui_dir}")

    def test_core_ui_modules_exist(self) -> None:
        for path in (
            self.main_module_lua,
            self.main_window_lua,
            self.navigation_lua,
            self.install_dialog_lua,
        ):
            with self.subTest(path=path.name):
                self.assertTrue(path.exists(), f"Expected file missing: {path}")

    def test_launcher_loads_main_module(self) -> None:
        content = self.launcher_lua.read_text(encoding="utf-8")
        self.assertIn('require("roughcut_main")', content)
        self.assertIn("roughcut/lua/roughcut_main.lua", content)

    def test_main_module_imports_current_components(self) -> None:
        content = self.main_module_lua.read_text(encoding="utf-8")
        self.assertIn('require("ui.main_window")', content)
        self.assertIn('require("install_orchestrator")', content)
        self.assertIn("launchMainWindow", content)

    def test_main_module_uses_backend_state_detection(self) -> None:
        content = self.main_module_lua.read_text(encoding="utf-8")
        self.assertIn("local function getBackendState()", content)
        self.assertIn("installOrchestrator.getBackendState(projectPath)", content)
        self.assertIn("backendState.global_installed", content)
        self.assertIn("config.markInstalled()", content)
        self.assertIn(
            "local installResult = installOrchestrator.startInstallation(uiManager, projectPath)",
            content,
        )
        self.assertIn("if installResult.cancelled then", content)
        self.assertNotIn("function(status)", content)
        self.assertNotIn("function(error)", content)

    def test_main_window_has_required_functions(self) -> None:
        content = self.main_window_lua.read_text(encoding="utf-8")
        for func in (
            "function mainWindow.create",
            "function mainWindow.show",
            "function mainWindow.hide",
            "function mainWindow.close",
        ):
            with self.subTest(func=func):
                self.assertIn(func, content)

    def test_navigation_has_required_functions(self) -> None:
        content = self.navigation_lua.read_text(encoding="utf-8")
        for func in (
            "function navigation.create",
            "function navigation.handleNavigation",
            "function navigation.returnToMain",
            "function navigation.getCurrentScreen",
            "function navigation.isMainScreen",
        ):
            with self.subTest(func=func):
                self.assertIn(func, content)

    def test_navigation_defines_three_buttons(self) -> None:
        content = self.navigation_lua.read_text(encoding="utf-8")
        for button_id in ("btnManageMedia", "btnManageFormats", "btnCreateRoughCut"):
            with self.subTest(button_id=button_id):
                self.assertIn(button_id, content)

    def test_navigation_has_descriptive_labels(self) -> None:
        content = self.navigation_lua.read_text(encoding="utf-8")
        for description in (
            "Set up your Music, SFX, and VFX folders",
            "Define rough cut templates for your projects",
            "Select media and format to create rough cuts",
        ):
            with self.subTest(description=description):
                self.assertIn(description, content)

    def test_main_window_uses_dispatcher_lifecycle(self) -> None:
        content = self.main_window_lua.read_text(encoding="utf-8")
        self.assertIn("function win.On.RoughCutMainWindow.Close", content)
        self.assertIn("function win.On.CloseButton.Clicked", content)
        self.assertIn("RunLoop", content)
        self.assertNotIn("win.CloseRequested =", content)

    def test_install_dialog_tracks_loop_state(self) -> None:
        content = self.install_dialog_lua.read_text(encoding="utf-8")
        self.assertIn("local isRunLoopActive = false", content)
        self.assertIn("local supportsStepLoop = nil", content)
        self.assertIn("function installDialog.pumpEvents(waitForEvent)", content)
        self.assertIn("dispRef:StepLoop(waitForEvent == true)", content)
        self.assertIn("if dispRef and isRunLoopActive then", content)
        self.assertIn("function win.On.RoughCutInstallDialog.Close", content)

    def test_install_orchestrator_returns_synchronous_result(self) -> None:
        content = self.install_orchestrator_lua.read_text(encoding="utf-8")
        self.assertIn("function installOrchestrator.getBackendState(projectDir)", content)
        self.assertIn("function installOrchestrator.startInstallation(uiManager, projectDir)", content)
        self.assertIn("local finalResult = nil", content)
        self.assertIn("local function finalize(success, error, extra)", content)
        self.assertIn("return buildResult(true, nil, { skipped_install = true })", content)
        self.assertIn('finalize(false, "Installation cancelled", { cancelled = true })', content)
        self.assertIn("return finalResult", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
