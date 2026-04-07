# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

#!/usr/bin/env python3
"""Deployment script for RoughCut plugin.

Copies Lua files to DaVinci Resolve's Scripts folder for menu integration.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def get_resolve_scripts_path() -> Path | None:
    """Get the DaVinci Resolve Utility Scripts path.
    
    Returns:
        Path to Resolve's Utility Scripts folder or None if not found
    """
    # Standard Resolve paths by platform
    if sys.platform == "win32":
        resolve_paths = [
            Path.home() / "AppData" / "Roaming" / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts" / "Utility",
            Path("C:") / "ProgramData" / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts" / "Utility",
        ]
    elif sys.platform == "darwin":  # macOS
        resolve_paths = [
            Path.home() / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts" / "Utility",
        ]
    else:  # Linux
        resolve_paths = [
            Path.home() / ".local" / "share" / "DaVinciResolve" / "Fusion" / "Scripts" / "Utility",
            Path("/opt") / "resolve" / "Fusion" / "Scripts" / "Utility",
        ]
    
    for path in resolve_paths:
        if path.exists():
            return path
    
    return None


def deploy_lua_plugin(project_root: Path, force: bool = False) -> dict:
    """Deploy RoughCut Lua plugin to DaVinci Resolve Scripts folder.
    
    Args:
        project_root: Path to project root containing roughcut/lua/
        force: If True, overwrite existing installation
        
    Returns:
        Dict with deployment status and details
    """
    result = {
        "success": False,
        "error": None,
        "installed_path": None,
        "files_copied": [],
        "backup_path": None,
    }
    
    # Find Resolve scripts path
    scripts_path = get_resolve_scripts_path()
    if not scripts_path:
        result["error"] = "Could not find DaVinci Resolve Scripts folder"
        return result
    
    # Source and destination paths
    lua_source = project_root / "roughcut" / "lua"
    if not lua_source.exists():
        result["error"] = f"Lua source directory not found: {lua_source}"
        return result
    
    # Create roughcut folder in Scripts/Utility (this is the plugin folder)
    deploy_target = scripts_path / "roughcut"
    
    # Backup existing installation if present
    if deploy_target.exists():
        if not force:
            result["error"] = f"RoughCut already installed at {deploy_target}. Use --force to overwrite."
            return result
        
        # Create backup
        backup_path = scripts_path / f"roughcut_backup_{int(__import__('time').time())}"
        try:
            shutil.move(str(deploy_target), str(backup_path))
            result["backup_path"] = str(backup_path)
        except Exception as e:
            result["error"] = f"Failed to backup existing installation: {e}"
            return result
    
    # Copy lua directory to target
    try:
        shutil.copytree(lua_source, deploy_target)
        result["installed_path"] = str(deploy_target)
        result["success"] = True
        
        # List copied files
        for item in deploy_target.rglob("*"):
            if item.is_file():
                result["files_copied"].append(str(item.relative_to(deploy_target)))
        
    except Exception as e:
        result["error"] = f"Failed to copy files: {e}"
        return result
    
    return result


def verify_installation(project_root: Path, install_path: Path) -> dict:
    """Verify the installation is working.
    
    Args:
        project_root: Path to project root
        install_path: Path where plugin was installed
        
    Returns:
        Dict with verification results
    """
    result = {
        "success": False,
        "checks": {},
        "error": None,
    }
    
    # Check main entry point exists
    main_script = install_path / "roughcut.lua"
    result["checks"]["main_script"] = main_script.exists()
    
    # Check ui modules exist
    ui_dir = install_path / "ui"
    result["checks"]["ui_directory"] = ui_dir.exists()
    
    if ui_dir.exists():
        required_ui_files = ["main_window.lua", "navigation.lua", "install_dialog.lua"]
        for ui_file in required_ui_files:
            result["checks"][f"ui_{ui_file}"] = (ui_dir / ui_file).exists()
    
    # Check utils modules exist
    utils_dir = install_path / "utils"
    result["checks"]["utils_directory"] = utils_dir.exists()
    
    if utils_dir.exists():
        required_utils = ["config.lua", "logger.lua", "process.lua"]
        for util_file in required_utils:
            result["checks"][f"utils_{util_file}"] = (utils_dir / util_file).exists()
    
    # Overall success
    result["success"] = all(result["checks"].values())
    
    return result


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Deploy RoughCut plugin to DaVinci Resolve"
    )
    parser.add_argument(
        "--project-path",
        type=str,
        required=True,
        help="Absolute path to project directory containing roughcut/lua/",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing installation",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing installation, don't deploy",
    )
    args = parser.parse_args()
    
    project_root = Path(args.project_path).resolve()
    
    if not project_root.exists():
        print(f"Error: Project path does not exist: {project_root}", file=sys.stderr)
        return 1
    
    if args.verify_only:
        # Just verify existing installation
        scripts_path = get_resolve_scripts_path()
        if not scripts_path:
            print("Error: Could not find DaVinci Resolve Scripts folder", file=sys.stderr)
            return 1
        
        install_path = scripts_path / "roughcut"
        if not install_path.exists():
            print("Error: RoughCut not installed", file=sys.stderr)
            return 1
        
        result = verify_installation(project_root, install_path)
        
        print("Verification Results:")
        for check, passed in result["checks"].items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")
        
        return 0 if result["success"] else 1
    
    # Deploy the plugin
    print(f"Deploying RoughCut from {project_root}...")
    result = deploy_lua_plugin(project_root, force=args.force)
    
    if not result["success"]:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1
    
    print(f"[OK] RoughCut deployed successfully to: {result['installed_path']}")
    print(f"  Files copied: {len(result['files_copied'])}")
    
    if result["backup_path"]:
        print(f"  Backup created at: {result['backup_path']}")
    
    # Verify the installation
    print("\nVerifying installation...")
    verify_result = verify_installation(project_root, Path(result["installed_path"]))
    
    for check, passed in verify_result["checks"].items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {check}")
    
    if verify_result["success"]:
        print("\n[OK] Installation verified successfully!")
        print("\nYou can now access RoughCut from DaVinci Resolve's Workspace > Scripts menu.")
        return 0
    else:
        print("\n[FAIL] Installation verification failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
