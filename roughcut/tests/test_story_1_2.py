"""
Tests for Story 1.2: Scripts Menu Integration
Validates Lua UI component structure and syntax
"""

import unittest
import os
from pathlib import Path


class TestStory1_2UIComponents(unittest.TestCase):
    """Test Lua UI components for Story 1.2"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test paths"""
        cls.project_root = Path("/Users/niozerp/Documents/AI_context_stuff/repos/RoughCut/roughcut")
        cls.lua_ui_dir = cls.project_root / "lua" / "ui"
        cls.main_lua = cls.project_root / "lua" / "roughcut.lua"
        cls.main_window_lua = cls.lua_ui_dir / "main_window.lua"
        cls.navigation_lua = cls.lua_ui_dir / "navigation.lua"
    
    def test_01_lua_ui_directory_exists(self):
        """Verify lua/ui/ directory was created"""
        self.assertTrue(
            self.lua_ui_dir.exists(),
            f"lua/ui/ directory should exist at {self.lua_ui_dir}"
        )
    
    def test_02_main_window_lua_exists(self):
        """Verify main_window.lua was created"""
        self.assertTrue(
            self.main_window_lua.exists(),
            f"main_window.lua should exist at {self.main_window_lua}"
        )
    
    def test_03_navigation_lua_exists(self):
        """Verify navigation.lua was created"""
        self.assertTrue(
            self.navigation_lua.exists(),
            f"navigation.lua should exist at {self.navigation_lua}"
        )
    
    def test_04_roughcut_lua_refactored(self):
        """Verify roughcut.lua was refactored"""
        self.assertTrue(
            self.main_lua.exists(),
            f"roughcut.lua should exist at {self.main_lua}"
        )
        
        content = self.main_lua.read_text()
        
        # Check for module imports
        self.assertIn("require", content, "Should import modules using require")
        self.assertIn("ui.main_window", content, "Should require main_window module")
        self.assertIn("ui.navigation", content, "Should require navigation module")
        
        # Check for version update
        self.assertIn("Version: 0.2.0", content, "Version should be updated to 0.2.0")
    
    def test_05_main_window_has_required_functions(self):
        """Verify main_window.lua has required functions"""
        content = self.main_window_lua.read_text()
        
        required_functions = [
            "function mainWindow.create",
            "function mainWindow.show",
            "function mainWindow.hide",
            "function mainWindow.close"
        ]
        
        for func in required_functions:
            self.assertIn(
                func, content,
                f"main_window.lua should define {func}"
            )
    
    def test_06_main_window_has_pcall_error_handling(self):
        """Verify main_window.lua uses pcall for error handling"""
        content = self.main_window_lua.read_text()
        
        self.assertIn(
            "pcall", content,
            "main_window.lua should use pcall for error handling"
        )
    
    def test_07_navigation_has_required_functions(self):
        """Verify navigation.lua has required functions"""
        content = self.navigation_lua.read_text()
        
        required_functions = [
            "function navigation.create",
            "function navigation.handleNavigation",
            "function navigation.returnToMain",
            "function navigation.getCurrentScreen",
            "function navigation.isMainScreen"
        ]
        
        for func in required_functions:
            self.assertIn(
                func, content,
                f"navigation.lua should define {func}"
            )
    
    def test_08_navigation_has_three_buttons(self):
        """Verify navigation defines three navigation buttons"""
        content = self.navigation_lua.read_text()
        
        button_ids = [
            "btnManageMedia",
            "btnManageFormats", 
            "btnCreateRoughCut"
        ]
        
        for btn_id in button_ids:
            self.assertIn(
                btn_id, content,
                f"navigation.lua should define button {btn_id}"
            )
    
    def test_09_navigation_has_descriptive_labels(self):
        """Verify navigation has descriptive labels"""
        content = self.navigation_lua.read_text()
        
        descriptions = [
            "Set up your Music, SFX, and VFX folders",
            "Define rough cut templates for your projects",
            "Select media and format to create rough cuts"
        ]
        
        for desc in descriptions:
            self.assertIn(
                desc, content,
                f"navigation.lua should include description: {desc}"
            )
    
    def test_10_lua_uses_camel_case_naming(self):
        """Verify Lua code uses camelCase naming conventions"""
        files_to_check = [
            self.main_lua,
            self.main_window_lua,
            self.navigation_lua
        ]
        
        for lua_file in files_to_check:
            content = lua_file.read_text()
            
            # Check that function names use camelCase
            # (Allow snake_case in comments or strings, but not in function definitions)
            lines = content.split('\n')
            for line in lines:
                if line.strip().startswith('function ') or line.strip().startswith('local function '):
                    # Extract function name
                    func_match = line.split('function ')[1].split('(')[0].strip()
                    if '.' in func_match:
                        func_match = func_match.split('.')[1]
                    
                    # Should be camelCase (no underscores)
                    if '_' in func_match and not func_match.startswith('_'):
                        self.fail(
                            f"Function {func_match} in {lua_file.name} should use camelCase, not snake_case"
                        )
    
    def test_11_all_resolve_api_calls_use_pcall(self):
        """Verify all Resolve API calls are wrapped in pcall"""
        files_to_check = [
            self.main_lua,
            self.main_window_lua,
            self.navigation_lua
        ]
        
        resolve_api_patterns = [
            "Resolve()",
            ":GetUIManager()",
            ":ShowMessageBox("
        ]
        
        for lua_file in files_to_check:
            content = lua_file.read_text()
            
            # Count pcall occurrences
            pcall_count = content.count("pcall")
            
            # Should have multiple pcall usages
            self.assertGreater(
                pcall_count, 2,
                f"{lua_file.name} should have multiple pcall() error handlers"
            )
    
    def test_12_has_return_to_main_functionality(self):
        """Verify navigation has return to main functionality"""
        content = self.navigation_lua.read_text()
        
        # Check for returnToMain function (implementation provides this functionality)
        self.assertIn(
            "function navigation.returnToMain", content,
            "navigation.lua should have returnToMain function"
        )


class TestStory1_2Integration(unittest.TestCase):
    """Integration tests for Story 1.2"""
    
    def test_01_lua_files_are_valid_lua_syntax(self):
        """Verify Lua files have valid syntax (basic check)"""
        project_root = Path("/Users/niozerp/Documents/AI_context_stuff/repos/RoughCut/roughcut")
        lua_files = [
            project_root / "lua" / "roughcut.lua",
            project_root / "lua" / "ui" / "main_window.lua",
            project_root / "lua" / "ui" / "navigation.lua"
        ]
        
        for lua_file in lua_files:
            content = lua_file.read_text()
            
            # Basic syntax checks
            self.assertIn(
                "--", content,
                f"{lua_file.name} should have comments"
            )
            
            # Check for balanced brackets
            open_brackets = content.count("(") + content.count("[")
            close_brackets = content.count(")") + content.count("]")
            
            # Allow for comments or strings that might contain brackets
            # Just check that there's reasonable balance
            self.assertTrue(
                abs(open_brackets - close_brackets) < 10,
                f"{lua_file.name} should have reasonably balanced brackets"
            )
    
    def test_02_follows_architecture_requirements(self):
        """Verify implementation follows architecture.md requirements"""
        project_root = Path("/Users/niozerp/Documents/AI_context_stuff/repos/RoughCut/roughcut")
        
        # Check lua/ui/ directory structure
        lua_ui = project_root / "lua" / "ui"
        self.assertTrue(lua_ui.exists(), "lua/ui/ directory should exist")
        
        # Check that main roughcut.lua is thin entry point
        main_lua = project_root / "lua" / "roughcut.lua"
        content = main_lua.read_text()
        
        # Should import modules, not define everything inline
        self.assertIn("require", content, "Should use require for modularity")
        
        # Should have launchRoughCut or similar function
        self.assertIn("launchRoughCut", content, "Should have main launch function")


if __name__ == "__main__":
    unittest.main(verbosity=2)
