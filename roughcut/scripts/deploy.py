# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

#!/usr/bin/env python3
"""Deploy RoughCut into DaVinci Resolve's Utility Scripts folder."""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

LAUNCHER_FILENAME = "RoughCut.lua"
PACKAGE_DIRNAME = "roughcut"
REQUIRED_PACKAGE_FILES = [
    Path("pyproject.toml"),
    Path("lua") / "roughcut_main.lua",
    Path("lua") / "ui" / "main_window.lua",
    Path("lua") / "ui" / "install_dialog.lua",
    Path("lua") / "utils" / "config.lua",
    Path("scripts") / "deploy.py",
]


def get_resolve_scripts_path() -> Path | None:
    """Return Resolve's Utility Scripts directory if it exists."""
    if sys.platform == "win32":
        resolve_paths = [
            Path.home()
            / "AppData"
            / "Roaming"
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Support"
            / "Fusion"
            / "Scripts"
            / "Utility",
            Path("C:/ProgramData")
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Support"
            / "Fusion"
            / "Scripts"
            / "Utility",
        ]
    elif sys.platform == "darwin":
        resolve_paths = [
            Path.home()
            / "Library"
            / "Application Support"
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Support"
            / "Fusion"
            / "Scripts"
            / "Utility",
            Path("/")
            / "Library"
            / "Application Support"
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Support"
            / "Fusion"
            / "Scripts"
            / "Utility",
        ]
    else:
        resolve_paths = [
            Path.home() / ".local" / "share" / "DaVinciResolve" / "Fusion" / "Scripts" / "Utility",
            Path("/opt/resolve/Fusion/Scripts/Utility"),
            Path("/home/resolve/Fusion/Scripts/Utility"),
        ]

    for path in resolve_paths:
        if path.exists():
            return path

    return None


def find_source_layout(project_root: Path) -> tuple[Path, Path] | None:
    """Find the launcher and deployable package directory."""
    for package_root in (project_root / PACKAGE_DIRNAME, project_root):
        launcher_path = package_root / LAUNCHER_FILENAME
        if not launcher_path.is_file():
            continue

        if all((package_root / relative_path).exists() for relative_path in REQUIRED_PACKAGE_FILES):
            return launcher_path, package_root

    return None


def verify_installation(scripts_path: Path) -> dict[str, object]:
    """Verify the deployed RoughCut launcher and package structure."""
    package_root = scripts_path / PACKAGE_DIRNAME
    checks = {
        "launcher": (scripts_path / LAUNCHER_FILENAME).is_file(),
        "package_root": package_root.is_dir(),
        "main_module": (package_root / "lua" / "roughcut_main.lua").is_file(),
        "main_window": (package_root / "lua" / "ui" / "main_window.lua").is_file(),
        "install_dialog": (package_root / "lua" / "ui" / "install_dialog.lua").is_file(),
        "config": (package_root / "lua" / "utils" / "config.lua").is_file(),
        "pyproject": (package_root / "pyproject.toml").is_file(),
        "deploy_script": (package_root / "scripts" / "deploy.py").is_file(),
    }
    return {
        "success": all(checks.values()),
        "checks": checks,
        "error": None,
    }


def deploy_package(project_root: Path, force: bool = False) -> dict[str, object]:
    """Deploy the launcher and package folder into Resolve."""
    result: dict[str, object] = {
        "success": False,
        "error": None,
        "installed_path": None,
        "files_copied": [],
        "backup_path": None,
        "skipped": False,
    }

    scripts_path = get_resolve_scripts_path()
    if scripts_path is None:
        result["error"] = "Could not find DaVinci Resolve Utility Scripts folder"
        return result

    project_root = project_root.resolve()
    if not project_root.is_dir():
        result["error"] = f"Project path is not a directory: {project_root}"
        return result

    source_layout = find_source_layout(project_root)
    if source_layout is None:
        result["error"] = (
            "Could not find RoughCut source layout. Expected either "
            "`<root>/roughcut/RoughCut.lua` or `<root>/RoughCut.lua` with the full package tree."
        )
        return result

    launcher_source, package_source = source_layout
    launcher_target = scripts_path / LAUNCHER_FILENAME
    package_target = scripts_path / PACKAGE_DIRNAME

    if package_source == package_target:
        result["success"] = True
        result["skipped"] = True
        result["installed_path"] = str(package_target)
        result["message"] = "Already deployed in Resolve's Scripts folder"
        return result

    if launcher_target.exists() or package_target.exists():
        if not force:
            result["error"] = (
                f"RoughCut already appears to be installed at {scripts_path}. "
                "Use --force to overwrite."
            )
            return result

        backup_root = scripts_path / f"{PACKAGE_DIRNAME}_backup_{int(time.time())}"
        backup_root.mkdir(parents=True, exist_ok=True)

        if launcher_target.exists():
            shutil.move(str(launcher_target), str(backup_root / LAUNCHER_FILENAME))
        if package_target.exists():
            shutil.move(str(package_target), str(backup_root / PACKAGE_DIRNAME))

        result["backup_path"] = str(backup_root)

    shutil.copy2(launcher_source, launcher_target)
    shutil.copytree(package_source, package_target)

    copied_files = [LAUNCHER_FILENAME]
    copied_files.extend(
        str(path.relative_to(scripts_path))
        for path in package_target.rglob("*")
        if path.is_file()
    )

    result["success"] = True
    result["installed_path"] = str(scripts_path)
    result["files_copied"] = copied_files
    return result


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Deploy RoughCut into DaVinci Resolve")
    parser.add_argument(
        "--project-path",
        required=True,
        help="Repo root or packaged RoughCut directory to deploy",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing Resolve installation",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify the existing Resolve installation without deploying",
    )
    args = parser.parse_args()

    scripts_path = get_resolve_scripts_path()
    if scripts_path is None:
        print("Error: Could not find DaVinci Resolve Utility Scripts folder", file=sys.stderr)
        return 1

    if args.verify_only:
        result = verify_installation(scripts_path)
        print("Verification Results:")
        for check_name, passed in result["checks"].items():
            status = "OK" if passed else "FAIL"
            print(f"  [{status}] {check_name}")
        return 0 if result["success"] else 1

    result = deploy_package(Path(args.project_path), force=args.force)
    if not result["success"]:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    verify_result = verify_installation(scripts_path)
    if not verify_result["success"]:
        print("Deployment finished, but verification failed:", file=sys.stderr)
        for check_name, passed in verify_result["checks"].items():
            if not passed:
                print(f"  - {check_name}", file=sys.stderr)
        return 1

    if result["skipped"]:
        print(f"Deployment skipped: {result.get('message', 'already installed')}")
        return 0

    print(f"Installed RoughCut to: {result['installed_path']}")
    if result["backup_path"]:
        print(f"Backup created at: {result['backup_path']}")
    print("Copied files:")
    for relative_path in result["files_copied"]:
        print(f"  - {relative_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
